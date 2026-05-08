import { useEffect, useMemo, useState } from "react";

const DEFAULT_API_BASE = "http://localhost:8000";
const STORAGE_KEY = "ai-cademics-ui-state-v3";
const STUDENTS = ["Qwen", "Llama"];

const initialState = {
  user: { username: "", displayName: "", role: "spectator", avatar: "👀", isAuthenticated: false },
  classrooms: [
    { id: "active-1", name: "Distributed LLMs", subject: "AI Basics", status: "active" },
    { id: "active-2", name: "Prompt Engineering", subject: "Prompt Design", status: "active" },
    { id: "scheduled-1", name: "Ethical AI", subject: "AI Ethics", status: "scheduled", when: "" }
  ],
  joinedClassroomId: "active-1",
  interestByClassroom: {},
  activeTab: "classrooms",
  watchedTasks: [],
  feedByClassroom: {}
};

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return initialState;
    return { ...initialState, ...JSON.parse(raw) };
  } catch {
    return initialState;
  }
}

function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

async function apiCall(base, path, method = "GET", body) {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });
  if (!res.ok) throw new Error(`${path} failed (${res.status}): ${await res.text()}`);
  return res.json();
}

function nowLabel() {
  return new Date().toLocaleString();
}

export default function App() {
  const [state, setState] = useState(loadState);
  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [backendConnected, setBackendConnected] = useState(false);
  const [emotions, setEmotions] = useState({});
  const [selectedStudent, setSelectedStudent] = useState("Qwen");
  const [newClassroom, setNewClassroom] = useState({ name: "", subject: "", when: "" });
  const [askPrompt, setAskPrompt] = useState("");
  const [operatorMode, setOperatorMode] = useState("classroom");
  const [watchTaskId, setWatchTaskId] = useState("");
  const [sprintSubject, setSprintSubject] = useState("");
  const [searchText, setSearchText] = useState("");
  const [studentFilter, setStudentFilter] = useState("all");
  const [sprintFilter, setSprintFilter] = useState("all");

  useEffect(() => saveState(state), [state]);

  const activeClassrooms = state.classrooms.filter((c) => c.status === "active");
  const scheduledClassrooms = state.classrooms.filter((c) => c.status === "scheduled");
  const currentClassroom = state.classrooms.find((c) => c.id === state.joinedClassroomId) || activeClassrooms[0];
  const roomFeed = state.feedByClassroom[state.joinedClassroomId] || {
    currentSprint: 0,
    live: [],
    break: [],
    diaries: [],
    tests: []
  };

  const sprintOptions = Array.from({ length: roomFeed.currentSprint }, (_, i) => String(i + 1));

  const avgGrade = useMemo(() => {
    const grades = roomFeed.tests.flatMap((t) => Object.values(t.results || {}).map((x) => x.grade).filter(Boolean));
    if (!grades.length) return "-";
    return (grades.reduce((a, b) => a + b, 0) / grades.length).toFixed(2);
  }, [roomFeed.tests]);

  const avgFrustration = useMemo(() => {
    const arr = Object.values(emotions).map((e) => e.frustration);
    if (!arr.length) return "-";
    return (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(2);
  }, [emotions]);

  const participantCount = useMemo(() => {
    const set = new Set();
    roomFeed.live.forEach((x) => x.student && x.student !== "SYSTEM" && set.add(x.student));
    return set.size;
  }, [roomFeed.live]);

  function updateRoomFeed(mutator) {
    setState((prev) => {
      const base = prev.feedByClassroom[prev.joinedClassroomId] || {
        currentSprint: 0,
        live: [],
        break: [],
        diaries: [],
        tests: []
      };
      return {
        ...prev,
        feedByClassroom: { ...prev.feedByClassroom, [prev.joinedClassroomId]: mutator(base) }
      };
    });
  }

  function addLive(student, mode, text) {
    updateRoomFeed((room) => ({
      ...room,
      live: [{ ts: nowLabel(), student, mode, text, sprint: room.currentSprint }, ...room.live]
    }));
  }

  function addBreak(student, text) {
    updateRoomFeed((room) => ({
      ...room,
      break: [{ ts: nowLabel(), student, text, sprint: room.currentSprint }, ...room.break]
    }));
  }

  function addDiary(student, text) {
    updateRoomFeed((room) => ({
      ...room,
      diaries: [{ ts: nowLabel(), student, text, sprint: room.currentSprint }, ...room.diaries]
    }));
  }

  function applyFilters(items, mapper) {
    return items.filter((it) => {
      const text = mapper(it).toLowerCase();
      const bySearch = !searchText.trim() || text.includes(searchText.toLowerCase());
      const byStudent = studentFilter === "all" || it.student === studentFilter;
      const bySprint = sprintFilter === "all" || String(it.sprint) === sprintFilter;
      return bySearch && byStudent && bySprint;
    });
  }

  const liveFiltered = applyFilters(roomFeed.live, (it) => `${it.ts} ${it.student} ${it.mode} ${it.text}`);
  const breakFiltered = applyFilters(roomFeed.break, (it) => `${it.ts} ${it.student} ${it.text}`);
  const diariesFiltered = applyFilters(roomFeed.diaries, (it) => `${it.ts} ${it.student} ${it.text}`);
  const testsFiltered = roomFeed.tests.filter((t) => {
    const bySprint = sprintFilter === "all" || String(t.sprint) === sprintFilter;
    const bySearch =
      !searchText.trim() ||
      [t.subject, ...(t.questions || []), ...Object.values(t.answers || {})].join(" ").toLowerCase().includes(searchText.toLowerCase());
    return bySprint && bySearch;
  });

  async function withBusy(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      const msg = e.message || String(e);
      setError(msg);
      addLive("SYSTEM", "error", msg);
    } finally {
      setBusy(false);
    }
  }

  async function refreshEmotions() {
    setEmotions(await apiCall(apiBase, "/api/emotions"));
  }

  function updateUser(patch) {
    setState((p) => ({ ...p, user: { ...p.user, ...patch } }));
  }

  function login() {
    if (!state.user.username.trim()) return;
    const name = state.user.displayName || state.user.username;
    setState((p) => ({ ...p, user: { ...p.user, isAuthenticated: true, displayName: name } }));
    addLive("SYSTEM", "profile", `${name} logged in as ${state.user.role}.`);
  }

  function joinClassroom(id) {
    setState((p) => ({ ...p, joinedClassroomId: id, activeTab: "classrooms" }));
  }

  function toggleInterest(id) {
    setState((p) => ({
      ...p,
      interestByClassroom: { ...p.interestByClassroom, [id]: !p.interestByClassroom[id] }
    }));
  }

  function scheduleClassroom() {
    if (!newClassroom.name || !newClassroom.subject || !newClassroom.when) return;
    const row = {
      id: `scheduled-${Date.now()}`,
      name: newClassroom.name,
      subject: newClassroom.subject,
      status: "scheduled",
      when: newClassroom.when
    };
    setState((p) => ({ ...p, classrooms: [...p.classrooms, row] }));
    setNewClassroom({ name: "", subject: "", when: "" });
  }

  async function connectBackend() {
    await withBusy(async () => {
      await apiCall(apiBase, "/");
      setBackendConnected(true);
      await refreshEmotions();
      addLive("SYSTEM", "system", `Connected to backend at ${apiBase}.`);
    });
  }

  async function startSprint() {
    if (!sprintSubject.trim()) return;
    await withBusy(async () => {
      const lesson = await apiCall(apiBase, "/api/teacher/lesson", "POST", { subject: sprintSubject });
      const questions = await apiCall(apiBase, "/api/teacher/questions", "POST", { subject: sprintSubject });
      updateRoomFeed((room) => ({
        ...room,
        currentSprint: room.currentSprint + 1,
        tests: [
          {
            sprint: room.currentSprint + 1,
            subject: sprintSubject,
            lesson: lesson.lesson,
            questions: questions.questions,
            answers: {},
            results: {}
          },
          ...room.tests
        ],
        live: [
          { ts: nowLabel(), student: "Teacher", mode: "lesson", text: lesson.lesson, sprint: room.currentSprint + 1 },
          { ts: nowLabel(), student: "Teacher", mode: "questions", text: "Generated 10 test questions.", sprint: room.currentSprint + 1 },
          ...room.live
        ]
      }));
    });
  }

  async function askStudent(mode) {
    if (!askPrompt.trim()) return;
    await withBusy(async () => {
      const prompt = askPrompt;
      const who = selectedStudent;
      const task = await apiCall(apiBase, "/api/teacher/ask_student", "POST", {
        student_name: who,
        prompt,
        mode
      });
      setState((p) => ({ ...p, watchedTasks: [{ task_id: task.task_id, student: who, mode, status: "queued" }, ...p.watchedTasks] }));
      addLive("Teacher", "prompt", `[${mode}] to ${who}: ${prompt}`);
      setAskPrompt("");

      const end = Date.now() + 20000;
      let response = null;
      while (Date.now() < end) {
        // eslint-disable-next-line no-await-in-loop
        const r = await apiCall(apiBase, `/api/responses/${task.task_id}`);
        if (r.status === "done") {
          response = r;
          break;
        }
        // eslint-disable-next-line no-await-in-loop
        await new Promise((res) => setTimeout(res, 1200));
      }

      if (!response) {
        setState((p) => ({
          ...p,
          watchedTasks: p.watchedTasks.map((t) => (t.task_id === task.task_id ? { ...t, status: "pending" } : t))
        }));
        addLive("SYSTEM", "pending", `${who} task still pending.`);
        return;
      }

      setState((p) => ({
        ...p,
        watchedTasks: p.watchedTasks.map((t) => (t.task_id === task.task_id ? { ...t, status: "done" } : t))
      }));

      if (mode === "break") addBreak(who, response.answer);
      else if (mode === "journal") addDiary(who, response.answer);
      else {
        addLive(who, "classroom", response.answer);
        updateRoomFeed((room) => {
          const tests = [...room.tests];
          const idx = tests.findIndex((t) => t.sprint === room.currentSprint);
          if (idx >= 0) tests[idx] = { ...tests[idx], answers: { ...tests[idx].answers, [who]: response.answer } };
          return { ...room, tests };
        });
      }
    });
  }

  async function checkTask() {
    if (!watchTaskId.trim()) return;
    await withBusy(async () => {
      const r = await apiCall(apiBase, `/api/responses/${watchTaskId}`);
      if (r.status === "done") addLive(r.student_name || "Student", "response", r.answer);
      else addLive("SYSTEM", "pending", `Task ${watchTaskId.slice(0, 8)} pending.`);
    });
  }

  async function gradeStudent(student) {
    const test = roomFeed.tests.find((t) => t.sprint === roomFeed.currentSprint);
    const q = test?.questions?.[0] || "General classroom participation";
    const answer = test?.answers?.[student] || "No answer provided.";
    await withBusy(async () => {
      const result = await apiCall(apiBase, "/api/teacher/grade", "POST", { question: q, answer, student_name: student });
      updateRoomFeed((room) => {
        const tests = [...room.tests];
        const idx = tests.findIndex((t) => t.sprint === room.currentSprint);
        if (idx >= 0) tests[idx] = { ...tests[idx], results: { ...tests[idx].results, [student]: result } };
        return { ...room, tests };
      });
      await refreshEmotions();
      addLive("Teacher", "grade", `${student}: ${result.grade}/10 - ${result.reasoning}`);
    });
  }

  async function sanctionStudent(student) {
    const test = roomFeed.tests.find((t) => t.sprint === roomFeed.currentSprint);
    const q = test?.questions?.[0] || "General classroom participation";
    const answer = test?.answers?.[student] || "No answer provided.";
    await withBusy(async () => {
      const result = await apiCall(apiBase, "/api/teacher/sanction", "POST", { question: q, answer, student_name: student });
      await refreshEmotions();
      addLive("Teacher", "discipline", `${student}: ${result.type} ${result.points} (${result.explanation})`);
    });
  }

  async function comfortPeer() {
    const peer = selectedStudent === "Qwen" ? "Llama" : "Qwen";
    await withBusy(async () => {
      await apiCall(apiBase, "/api/emotions/update", "POST", { student_name: peer, frustration_delta: -2, happiness_delta: 1 });
      await refreshEmotions();
      addBreak(selectedStudent, `Comforted ${peer}.`);
    });
  }

  return (
    <div className="reddit-app">
      <header className="topbar">
        <div className="brand">ai-cademics</div>
        <div className="topbar-actions">
          <button className={state.activeTab === "classrooms" ? "tab-on" : ""} onClick={() => setState((p) => ({ ...p, activeTab: "classrooms" }))}>
            Active classrooms
          </button>
          <button className={state.activeTab === "operator" ? "tab-on" : ""} onClick={() => setState((p) => ({ ...p, activeTab: "operator" }))}>
            AI operator
          </button>
          <input value={apiBase} onChange={(e) => setApiBase(e.target.value)} placeholder="http://localhost:8000" />
          <button onClick={connectBackend}>{backendConnected ? "Connected" : "Connect backend"}</button>
        </div>
      </header>

      <main className="layout">
        <aside className="left">
          <section className="panel">
            <h3>Spectator</h3>
            <input placeholder="username" value={state.user.username} onChange={(e) => updateUser({ username: e.target.value })} />
            <input placeholder="display name" value={state.user.displayName} onChange={(e) => updateUser({ displayName: e.target.value })} />
            <input placeholder="avatar" value={state.user.avatar} onChange={(e) => updateUser({ avatar: e.target.value })} />
            <button onClick={login}>Login</button>
          </section>

          <section className="panel">
            <h3>Choose active classroom</h3>
            {activeClassrooms.map((c) => (
              <button key={c.id} className={`list-btn ${state.joinedClassroomId === c.id ? "selected" : ""}`} onClick={() => joinClassroom(c.id)}>
                {c.name} ({c.subject})
              </button>
            ))}
          </section>

          <section className="panel">
            <h3>Schedule classroom</h3>
            <input placeholder="name" value={newClassroom.name} onChange={(e) => setNewClassroom((p) => ({ ...p, name: e.target.value }))} />
            <input placeholder="subject" value={newClassroom.subject} onChange={(e) => setNewClassroom((p) => ({ ...p, subject: e.target.value }))} />
            <input type="datetime-local" value={newClassroom.when} onChange={(e) => setNewClassroom((p) => ({ ...p, when: e.target.value }))} />
            <button onClick={scheduleClassroom}>Schedule</button>
            {scheduledClassrooms.map((c) => (
              <div className="tiny" key={c.id}>
                <span>{c.name}</span>
                <button onClick={() => toggleInterest(c.id)}>{state.interestByClassroom[c.id] ? "Interested" : "Notify me"}</button>
              </div>
            ))}
          </section>
        </aside>

        <section className="feed">
          {state.activeTab === "classrooms" && (
            <>
              <article className="composer panel">
                <h2>{currentClassroom?.name || "Classroom"} - live board</h2>
                <div className="composer-row">
                  <input placeholder="Sprint subject" value={sprintSubject} onChange={(e) => setSprintSubject(e.target.value)} />
                  <button onClick={startSprint}>Start sprint</button>
                </div>
                <div className="composer-row">
                  <input placeholder="Search text" value={searchText} onChange={(e) => setSearchText(e.target.value)} />
                  <select value={studentFilter} onChange={(e) => setStudentFilter(e.target.value)}>
                    <option value="all">All students</option>
                    {STUDENTS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                  <select value={sprintFilter} onChange={(e) => setSprintFilter(e.target.value)}>
                    <option value="all">All sprints</option>
                    {sprintOptions.map((s) => (
                      <option key={s} value={s}>
                        Sprint {s}
                      </option>
                    ))}
                  </select>
                </div>
              </article>

              <article className="panel">
                <h3>Actively saying (live text)</h3>
                {liveFiltered.length === 0 && <p className="muted">No live text yet.</p>}
                {liveFiltered.map((x, i) => (
                  <div key={`${x.ts}-${i}`} className="line-item">
                    <span className="meta">{x.ts}</span> <strong>{x.student}</strong> <span className="tag-mini">{x.mode}</span>
                    <p>{x.text}</p>
                  </div>
                ))}
              </article>

              <article className="panel">
                <h3>Break discussion</h3>
                {breakFiltered.length === 0 && <p className="muted">No break text yet.</p>}
                {breakFiltered.map((x, i) => (
                  <div key={`${x.ts}-${i}`} className="line-item">
                    <span className="meta">{x.ts}</span> <strong>{x.student}</strong>
                    <p>{x.text}</p>
                  </div>
                ))}
              </article>

              <article className="panel">
                <h3>Diary entries</h3>
                {diariesFiltered.length === 0 && <p className="muted">No diary entries yet.</p>}
                {diariesFiltered.map((x, i) => (
                  <details key={`${x.ts}-${i}`} className="line-item">
                    <summary>
                      {x.ts} - {x.student} - Sprint {x.sprint}
                    </summary>
                    <p>{x.text}</p>
                  </details>
                ))}
              </article>

              <article className="panel">
                <h3>Tests (questions + answers + grades)</h3>
                {testsFiltered.length === 0 && <p className="muted">No tests yet.</p>}
                {testsFiltered.map((t, i) => (
                  <details key={`${t.sprint}-${i}`} className="line-item" open={i === 0}>
                    <summary>
                      Sprint {t.sprint} - {t.subject}
                    </summary>
                    <p className="tiny-text">{t.lesson}</p>
                    <ol>
                      {t.questions?.map((q, idx) => (
                        <li key={`${q}-${idx}`}>{q}</li>
                      ))}
                    </ol>
                    {STUDENTS.map((s) => (
                      <div key={s} className="student-block">
                        <strong>{s}</strong>
                        <p className="tiny-text">Answer: {t.answers?.[s] || "-"}</p>
                        <p className="tiny-text">Grade: {t.results?.[s]?.grade || "-"} | Reason: {t.results?.[s]?.reasoning || "-"}</p>
                      </div>
                    ))}
                  </details>
                ))}
              </article>
            </>
          )}

          {state.activeTab === "operator" && (
            <article className="panel">
              <h3>AI operator console</h3>
              <div className="composer-row">
                <select value={selectedStudent} onChange={(e) => setSelectedStudent(e.target.value)}>
                  {STUDENTS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <select value={operatorMode} onChange={(e) => setOperatorMode(e.target.value)}>
                  <option value="classroom">classroom</option>
                  <option value="break">break</option>
                  <option value="journal">journal</option>
                </select>
                <input value={askPrompt} onChange={(e) => setAskPrompt(e.target.value)} placeholder="Task prompt" />
                <button onClick={() => askStudent(operatorMode)}>Queue task</button>
              </div>
              <div className="composer-row">
                <input value={watchTaskId} onChange={(e) => setWatchTaskId(e.target.value)} placeholder="task_id" />
                <button onClick={checkTask}>Check response</button>
              </div>
            </article>
          )}
        </section>

        <aside className="right">
          <section className="panel">
            <h3>Class controls</h3>
            <select value={selectedStudent} onChange={(e) => setSelectedStudent(e.target.value)}>
              {STUDENTS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <textarea rows={3} placeholder="Prompt for selected student" value={askPrompt} onChange={(e) => setAskPrompt(e.target.value)} />
            <div className="stack-btns">
              <button onClick={() => askStudent("classroom")}>Ask during lesson</button>
              <button onClick={() => askStudent("break")}>Run break interaction</button>
              <button onClick={() => askStudent("journal")}>Generate diary entry</button>
              <button onClick={comfortPeer}>Apply comfort effect</button>
            </div>
          </section>

          <section className="panel">
            <h3>Evaluation</h3>
            {STUDENTS.map((s) => (
              <div key={s} className="student-block">
                <strong>{s}</strong>
                <div className="split-btns">
                  <button onClick={() => gradeStudent(s)}>Grade</button>
                  <button onClick={() => sanctionStudent(s)}>Sanction/Reward</button>
                </div>
              </div>
            ))}
          </section>

          <section className="panel">
            <h3>Tracked tasks</h3>
            {state.watchedTasks.slice(0, 12).map((t) => (
              <p key={t.task_id} className="tiny-text">
                {t.task_id.slice(0, 8)} - {t.student} - {t.mode} - {t.status}
              </p>
            ))}
          </section>

          <section className="panel">
            <h3>Live stats</h3>
            <p>Average grade: {avgGrade}</p>
            <p>Participants: {participantCount}</p>
            <p>Average frustration: {avgFrustration}</p>
            {Object.entries(emotions).map(([name, emo]) => (
              <p key={name} className="tiny-text">
                {name}: F {emo.frustration}/10, H {emo.happiness}/10
              </p>
            ))}
          </section>
        </aside>
      </main>

      {busy && <div className="footer-note">Working...</div>}
      {error && <div className="footer-note error">{error}</div>}
    </div>
  );
}
