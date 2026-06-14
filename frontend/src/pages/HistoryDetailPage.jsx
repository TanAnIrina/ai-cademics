import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import { Loading, Empty } from "../components/ui.jsx";
import { Transcript, Grades, Journals, TeacherJournal, Evals } from "../components/Panels.jsx";
import StatsView from "../components/Stats.jsx";

// The archive stores compact field names; map them onto the shapes the live
// panels already know how to render (adding a synthetic id per row).
function adaptTranscript(rows = []) {
  return rows.map((r, i) => ({
    id: i,
    sprint_index: r.sprint,
    phase: r.phase,
    sender: r.sender,
    sender_role: r.role,
    content: r.content,
  }));
}
function adaptGrades(rows = []) {
  return rows.map((r, i) => ({
    id: i,
    sprint_index: r.sprint,
    student_name: r.student,
    grade: r.grade,
    reasoning: r.reasoning,
  }));
}
function adaptJournals(rows = []) {
  return rows.map((r, i) => ({
    id: i,
    sprint_index: r.sprint,
    student_name: r.student,
    author_role: r.author_role || "student",
    content: r.content,
    word_count: r.word_count,
  }));
}
function adaptEvals(rows = []) {
  return rows.map((r, i) => ({
    id: i,
    scope: r.scope,
    check_name: r.check,
    passed: r.passed,
    score: r.score,
    detail: r.detail,
  }));
}
// Archive uses compact keys; map the emotion timeline / grades / sanctions onto
// the shape StatsView expects (so archived sessions get the same charts as live).
function adaptEmotionTimeline(rows = []) {
  return rows.map((r) => ({
    sprint_index: r.sprint,
    slot: r.slot,
    agent_name: r.agent_name,
    happiness: r.happiness,
    frustration: r.frustration,
    confidence: r.confidence,
    curiosity: r.curiosity,
    boredom: r.boredom,
    anxiety: r.anxiety,
  }));
}
function adaptGradePoints(rows = []) {
  return rows.map((r) => ({
    sprint_index: r.sprint,
    student_name: r.student,
    grade: r.grade,
  }));
}
function tallySanctions(rows = []) {
  const by = {};
  rows.forEach((s) => {
    const t = (by[s.student] ||= { student_name: s.student, sanctions: 0, rewards: 0, net_points: 0 });
    if (s.type === "sanction") t.sanctions += 1;
    else t.rewards += 1;
    t.net_points += s.points;
  });
  return Object.values(by);
}

export default function HistoryDetailPage() {
  const { id } = useParams();
  const [archive, setArchive] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("discussion");

  useEffect(() => {
    let active = true;
    api
      .getArchive(Number(id))
      .then((a) => active && setArchive(a))
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [id]);

  if (error)
    return (
      <div className="page">
        <div className="container">
          <Empty icon="⚠" title="Archive not found" hint={error} />
          <div className="center">
            <Link to="/history" className="btn ghost">
              ← Back to history
            </Link>
          </div>
        </div>
      </div>
    );
  if (!archive)
    return (
      <div className="page">
        <div className="container">
          <Loading label="Opening the archive…" />
        </div>
      </div>
    );

  const s = archive.session;
  const messages = adaptTranscript(s.transcript);
  const grades = adaptGrades(s.grades);
  const journals = adaptJournals(s.journals);
  const studentJournals = journals.filter((j) => j.author_role !== "teacher");
  const teacherJournals = journals.filter((j) => j.author_role === "teacher");
  const evals = adaptEvals(s.evals);
  const chat = s.observer_chat || [];
  const sanctions = s.sanctions || [];
  const ratings = s.ratings || [];
  const ratingAvg = ratings.length
    ? Math.round((ratings.reduce((a, r) => a + r.stars, 0) / ratings.length) * 10) / 10
    : 0;
  const statEmotions = adaptEmotionTimeline(s.emotion_timeline);
  const statGrades = adaptGradePoints(s.grades);
  const statSanctions = tallySanctions(sanctions);

  const counts = {
    discussion: messages.length,
    grades: grades.length,
    student_journals: studentJournals.length,
    teacher_journal: teacherJournals.length,
    statistics: statEmotions.length,
    evals: evals.length,
    chat: chat.length,
  };
  const tabs = [
    ["discussion", "Discussion"],
    ["grades", "Grades"],
    ["student_journals", "Student Journals"],
    ["teacher_journal", "Teacher Journal"],
    ["statistics", "Statistics"],
    ["evals", "Evals"],
    ["chat", "Observer chat"],
  ];

  const passedEvals = evals.filter((e) => e.passed).length;

  return (
    <div className="page">
      <div className="container">
        <Link to="/history" className="faint" style={{ fontSize: 14 }}>
          ← All sessions
        </Link>

        <div className="spread reveal" style={{ margin: "12px 0 6px", alignItems: "flex-start" }}>
          <div>
            <h1 className="h-page">{archive.name}</h1>
            <div className="row wrap" style={{ gap: 10, marginTop: 8 }}>
              <span className="room-subject">{archive.subject || "no subject"}</span>
              <span className="tag">{archive.num_sprints} sprints</span>
            </div>
          </div>
          <div className="row" style={{ gap: 10, alignItems: "center" }}>
            <a
              className="btn ghost sm"
              href={api.archivePdfUrl(archive.id)}
              target="_blank"
              rel="noopener noreferrer"
            >
              ⬇ Download PDF
            </a>
            <span className="badge finished">Archived</span>
          </div>
        </div>

        {/* summary stats */}
        <div className="stat-grid reveal" style={{ margin: "18px 0" }}>
          <div className="card stat">
            <div className="stat-num">{messages.length}</div>
            <div className="stat-label">Messages</div>
          </div>
          <div className="card stat">
            <div className="stat-num">{grades.length}</div>
            <div className="stat-label">Grades</div>
          </div>
          <div className="card stat">
            <div className="stat-num">{journals.length}</div>
            <div className="stat-label">Journals</div>
          </div>
          <div className="card stat">
            <div className="stat-num" style={{ color: passedEvals === evals.length ? "var(--green)" : "var(--amber)" }}>
              {passedEvals}/{evals.length}
            </div>
            <div className="stat-label">Evals passed</div>
          </div>
        </div>

        {sanctions.length > 0 && (
          <div className="card card-pad reveal" style={{ marginBottom: 18 }}>
            <span className="eyebrow">Sanctions &amp; rewards</span>
            <div className="stack" style={{ gap: 8, marginTop: 10 }}>
              {sanctions.map((sc, i) => (
                <div className="row" key={i} style={{ gap: 10 }}>
                  <span
                    className="tag"
                    style={{ color: sc.points >= 0 ? "var(--green)" : "var(--red)" }}
                  >
                    {sc.points >= 0 ? `+${sc.points}` : sc.points}
                  </span>
                  <strong style={{ color: "var(--cyan)" }}>{sc.student}</strong>
                  <span className="muted" style={{ fontSize: 14 }}>
                    {sc.explanation}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {ratings.length > 0 && (
          <div className="card card-pad reveal" style={{ marginBottom: 18 }}>
            <div className="spread">
              <span className="eyebrow">Lesson ratings</span>
              <span className="mono" style={{ color: "var(--amber)" }}>
                {"★".repeat(Math.round(ratingAvg))}
                <span className="faint"> {ratingAvg}/5 · {ratings.length}</span>
              </span>
            </div>
            <div className="stack" style={{ gap: 8, marginTop: 10 }}>
              {ratings.map((r, i) => (
                <div className="row" key={i} style={{ gap: 10 }}>
                  <span className="tag" style={{ color: "var(--amber)" }}>
                    {"★".repeat(r.stars)} {r.stars}/5
                  </span>
                  <strong style={{ color: "var(--cyan)" }}>{r.nickname}</strong>
                  {r.comment && (
                    <span className="muted" style={{ fontSize: 14 }}>{r.comment}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <hr className="chalk-rule" style={{ margin: "20px 0" }} />

        <div className="tabs">
          {tabs.map(([key, label]) => (
            <button key={key} className={`tab ${tab === key ? "on" : ""}`} onClick={() => setTab(key)}>
              {label}
              <span className="count">{counts[key]}</span>
            </button>
          ))}
        </div>

        {tab === "discussion" && <Transcript messages={messages} />}
        {tab === "grades" && <Grades grades={grades} />}
        {tab === "student_journals" && <Journals journals={studentJournals} />}
        {tab === "teacher_journal" && <TeacherJournal journals={teacherJournals} />}
        {tab === "statistics" && (
          <StatsView emotions={statEmotions} grades={statGrades} sanctions={statSanctions} />
        )}
        {tab === "evals" && <Evals evals={evals} />}
        {tab === "chat" &&
          (chat.length === 0 ? (
            <Empty icon="💬" title="No observer chat" hint="No one chatted during this session." />
          ) : (
            <div className="feed">
              {chat.map((m, i) => (
                <div className="chat-msg" key={i}>
                  <span className="who">{m.nickname}</span>
                  {m.content}
                </div>
              ))}
            </div>
          ))}
      </div>
    </div>
  );
}
