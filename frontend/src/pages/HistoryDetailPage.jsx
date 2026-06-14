import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import { Loading, Empty } from "../components/ui.jsx";
import { Transcript, Grades, Journals, Evals } from "../components/Panels.jsx";

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
  const evals = adaptEvals(s.evals);
  const chat = s.observer_chat || [];
  const sanctions = s.sanctions || [];

  const counts = {
    discussion: messages.length,
    grades: grades.length,
    journals: journals.length,
    evals: evals.length,
    chat: chat.length,
  };
  const tabs = [
    ["discussion", "Discussion"],
    ["grades", "Grades"],
    ["journals", "Journals"],
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
          <span className="badge finished">Archived</span>
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
        {tab === "journals" && <Journals journals={journals} />}
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
