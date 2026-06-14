import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import { usePolling } from "../usePolling";
import { Loading, Empty, StatusBadge, ProgressBar } from "../components/ui.jsx";
import { Transcript, Grades, Journals, Evals } from "../components/Panels.jsx";
import SessionTimeChart from "../components/SessionTimeChart.jsx";
import Chat from "../components/Chat.jsx";

const SLOT_LABEL = { teacher: "Teacher", student_a: "Student A", student_b: "Student B" };

function Members({ members }) {
  if (!members.length) return <p className="faint">No one has joined yet.</p>;
  return (
    <div className="stack" style={{ gap: 10 }}>
      {members.map((m) => (
        <div className="row spread" key={m.slot} style={{ gap: 10 }}>
          <div className="row" style={{ gap: 9 }}>
            <span className={`dot ${m.role === "teacher" ? "amber" : "cyan"}`} />
            <div>
              <div style={{ fontWeight: 600, fontSize: 14.5 }}>{m.display_name}</div>
              <div className="faint mono" style={{ fontSize: 11 }}>
                {SLOT_LABEL[m.slot]}
              </div>
            </div>
          </div>
          <div className="stack" style={{ gap: 4, alignItems: "flex-end" }}>
            <div className="emo">
              <span className="faint">😊</span>
              <span className="emo-bar happy">
                <span style={{ width: `${m.happiness * 10}%` }} />
              </span>
            </div>
            <div className="emo">
              <span className="faint">😣</span>
              <span className="emo-bar frust">
                <span style={{ width: `${m.frustration * 10}%` }} />
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Teacher's subject + timing form, with the live "time vs sessions" chart.
function TeacherConfig({ initial, onSubmit, submitLabel, busy }) {
  const [subject, setSubject] = useState(initial?.subject || "");
  const [sprintMinutes, setSprintMinutes] = useState(initial?.sprint_minutes ?? 20);
  const [breakMinutes, setBreakMinutes] = useState(initial?.break_minutes ?? 10);
  const [numSprints, setNumSprints] = useState(initial?.num_sprints ?? 2);
  const [estimate, setEstimate] = useState(null);
  const [err, setErr] = useState(null);

  const maxSprints = Math.max(8, Math.min(24, Number(numSprints) || 1));

  useEffect(() => {
    let active = true;
    const sm = Math.min(180, Math.max(1, Number(sprintMinutes) || 1));
    const bm = Math.min(120, Math.max(0, Number(breakMinutes) || 0));
    api
      .estimate(sm, bm, maxSprints)
      .then((e) => active && setEstimate(e))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [sprintMinutes, breakMinutes, maxSprints]);

  const chosen = estimate?.points.find((p) => p.num_sprints === Number(numSprints));
  const totalMin = chosen?.total_minutes;

  function submit() {
    if (!subject.trim()) {
      setErr("Please choose a subject to teach.");
      return;
    }
    setErr(null);
    onSubmit({
      subject: subject.trim(),
      sprint_minutes: Math.min(180, Math.max(1, Number(sprintMinutes) || 1)),
      break_minutes: Math.min(120, Math.max(0, Number(breakMinutes) || 0)),
      num_sprints: Math.min(12, Math.max(1, Number(numSprints) || 1)),
    });
  }

  return (
    <div className="stack" style={{ gap: 14 }}>
      <div className="field">
        <label className="label">Subject</label>
        <input
          className="input"
          placeholder="e.g. Graph Theory"
          value={subject}
          maxLength={120}
          onChange={(e) => setSubject(e.target.value)}
        />
      </div>

      <div className="row" style={{ gap: 12 }}>
        <div className="field grow">
          <label className="label">Sprint mins</label>
          <input
            className="input mono"
            type="number"
            min={1}
            max={180}
            value={sprintMinutes}
            onChange={(e) => setSprintMinutes(e.target.value)}
          />
        </div>
        <div className="field grow">
          <label className="label">Break mins</label>
          <input
            className="input mono"
            type="number"
            min={0}
            max={120}
            value={breakMinutes}
            onChange={(e) => setBreakMinutes(e.target.value)}
          />
        </div>
        <div className="field grow">
          <label className="label">Sprints</label>
          <input
            className="input mono"
            type="number"
            min={1}
            max={12}
            value={numSprints}
            onChange={(e) => setNumSprints(e.target.value)}
          />
        </div>
      </div>

      <div className="panel card-pad">
        <div className="spread" style={{ marginBottom: 6 }}>
          <span className="eyebrow">Total time vs sprints</span>
          {totalMin != null && (
            <span className="mono" style={{ color: "var(--cyan)", fontSize: 13 }}>
              {numSprints} sprints ≈{" "}
              {totalMin < 60 ? `${totalMin} min` : `${Math.floor(totalMin / 60)}h ${totalMin % 60}m`}
            </span>
          )}
        </div>
        <SessionTimeChart points={estimate?.points} active={Number(numSprints)} />
        <p className="faint" style={{ fontSize: 12.5, margin: "8px 0 0" }}>
          Each added sprint adds one lesson plus a break, so total wall-clock time grows
          linearly: <span className="mono">n·sprint + (n−1)·break</span>.
        </p>
      </div>

      {err && <p style={{ color: "var(--red)", margin: 0 }}>{err}</p>}
      <button className="btn primary block" disabled={busy} onClick={submit}>
        {busy ? "Working…" : submitLabel}
      </button>
    </div>
  );
}

function JoinControls({ live, refresh }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const room = live.classroom;
  const mine = user ? room.members.find((m) => m.display_name === user.display_name) : null;

  async function act(fn) {
    setBusy(true);
    setErr(null);
    try {
      await fn();
      refresh();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return (
      <div className="stack" style={{ gap: 12 }}>
        <Empty icon="👁" title="You're observing" hint="Sign in to take a seat in this room." />
        <button className="btn primary block" onClick={() => navigate("/login")}>
          Sign in to join
        </button>
      </div>
    );
  }

  if (room.status !== "waiting") {
    return mine ? (
      <p className="muted">
        You're seated as <strong>{SLOT_LABEL[mine.slot]}</strong>. The session is underway.
      </p>
    ) : (
      <p className="muted">This session has already started. You can watch and chat below.</p>
    );
  }

  // waiting room
  if (mine) {
    return (
      <div className="stack" style={{ gap: 14 }}>
        <div className="panel card-pad">
          You've claimed <strong>{SLOT_LABEL[mine.slot]}</strong>. The session starts automatically
          once all three seats are filled.
        </div>
        {mine.slot === "teacher" && (
          <>
            <div className="divider" />
            <span className="eyebrow">Adjust before start</span>
            <TeacherConfig
              initial={room}
              submitLabel="Save configuration"
              busy={busy}
              onSubmit={(cfg) => act(() => api.configureClassroom(room.id, cfg))}
            />
          </>
        )}
        <button
          className="btn danger block"
          disabled={busy}
          onClick={() => act(() => api.leaveClassroom(room.id))}
        >
          Leave seat
        </button>
        {err && <p style={{ color: "var(--red)", margin: 0 }}>{err}</p>}
      </div>
    );
  }

  // not yet a member
  const teacherTaken = room.members.some((m) => m.slot === "teacher");
  const studentsTaken = room.members.filter((m) => m.role === "student").length >= 2;

  if (user.role === "teacher") {
    if (teacherTaken)
      return <p className="muted">The teacher seat is already taken in this room.</p>;
    return (
      <div className="stack" style={{ gap: 12 }}>
        <span className="eyebrow">Claim the teacher seat</span>
        <TeacherConfig
          submitLabel="Join & set subject"
          busy={busy}
          onSubmit={(cfg) => act(() => api.joinClassroom(room.id, cfg))}
        />
        {err && <p style={{ color: "var(--red)", margin: 0 }}>{err}</p>}
      </div>
    );
  }

  // student
  if (studentsTaken) return <p className="muted">Both student seats are taken.</p>;
  return (
    <div className="stack" style={{ gap: 12 }}>
      <p className="muted" style={{ margin: 0 }}>
        Take an open student seat. {room.subject ? (
          <>
            The teacher is covering <strong style={{ color: "var(--amber)" }}>{room.subject}</strong>.
          </>
        ) : (
          "Waiting for a teacher to set the subject."
        )}
      </p>
      <button
        className="btn primary block"
        disabled={busy}
        onClick={() => act(() => api.joinClassroom(room.id, null))}
      >
        Join as student
      </button>
      {err && <p style={{ color: "var(--red)", margin: 0 }}>{err}</p>}
    </div>
  );
}

export default function ClassroomDetailPage() {
  const { id } = useParams();
  const cid = Number(id);
  const { data: live, loading, error, refresh } = usePolling(() => api.liveView(cid), 2000, [cid]);
  const [tab, setTab] = useState("discussion");

  if (loading && !live) return <div className="page"><div className="container"><Loading /></div></div>;
  if (error && !live)
    return (
      <div className="page">
        <div className="container">
          <Empty icon="⚠" title="Classroom not found" hint={error} />
          <div className="center">
            <Link to="/" className="btn ghost">
              ← Back to classrooms
            </Link>
          </div>
        </div>
      </div>
    );

  const room = live.classroom;
  const counts = {
    discussion: live.messages.length,
    grades: live.grades.length,
    journals: live.journals.length,
    evals: live.evals.length,
  };
  const tabs = [
    ["discussion", "Discussion"],
    ["grades", "Grades"],
    ["journals", "Journals"],
    ["evals", "Evals"],
  ];

  return (
    <div className="page">
      <div className="container">
        <Link to="/" className="faint" style={{ fontSize: 14 }}>
          ← All classrooms
        </Link>

        <div className="spread reveal" style={{ margin: "12px 0 6px", alignItems: "flex-start" }}>
          <div>
            <h1 className="h-page">{room.name}</h1>
            <div className="row wrap" style={{ gap: 10, marginTop: 8 }}>
              <span className={`room-subject ${room.subject ? "" : "empty"}`}>
                {room.subject || "no subject yet"}
              </span>
              <span className="tag">
                {room.sprint_minutes}m sprint · {room.break_minutes}m break · {room.num_sprints} sprints
              </span>
            </div>
          </div>
          <StatusBadge status={room.status} />
        </div>

        {room.status !== "waiting" && (
          <div className="stack reveal" style={{ gap: 6, margin: "10px 0 4px" }}>
            <ProgressBar value={room.progress} cyan={room.status === "running"} />
            <span className="faint mono" style={{ fontSize: 12 }}>
              {room.status === "running"
                ? `sprint ${room.current_sprint}/${room.num_sprints} · phase: ${room.phase}`
                : "session complete — archived to history"}
            </span>
          </div>
        )}

        <hr className="chalk-rule" style={{ margin: "20px 0" }} />

        <div className="detail-grid">
          {/* main column */}
          <div>
            <div className="tabs">
              {tabs.map(([key, label]) => (
                <button
                  key={key}
                  className={`tab ${tab === key ? "on" : ""}`}
                  onClick={() => setTab(key)}
                >
                  {label}
                  <span className="count">{counts[key]}</span>
                </button>
              ))}
            </div>

            {tab === "discussion" && <Transcript messages={live.messages} />}
            {tab === "grades" && <Grades grades={live.grades} />}
            {tab === "journals" && <Journals journals={live.journals} />}
            {tab === "evals" && <Evals evals={live.evals} />}
          </div>

          {/* sidebar */}
          <div className="sticky-side stack" style={{ gap: 18 }}>
            <div className="card card-pad">
              <h3 className="h-sec" style={{ fontSize: 18, marginBottom: 14 }}>
                {room.status === "finished" ? "Final roster" : "Seats"}
              </h3>
              <Members members={room.members} />
            </div>

            {room.status !== "finished" && (
              <div className="card card-pad">
                <JoinControls live={live} refresh={refresh} />
              </div>
            )}

            <div className="card card-pad" style={{ minHeight: 360 }}>
              <Chat classroomId={cid} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
