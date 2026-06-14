import { Empty, gradeColor } from "./ui.jsx";

function roleClass(role) {
  if (role === "teacher") return "teacher";
  if (role === "system") return "system";
  return "student";
}

// --- live / archived discussion -------------------------------------------
export function Transcript({ messages }) {
  if (!messages || messages.length === 0)
    return <Empty icon="✎" title="No discussion yet" hint="Messages appear as the sprint runs." />;

  // group with a divider whenever the sprint index changes
  const blocks = [];
  let lastSprint = null;
  messages.forEach((m) => {
    if (m.sprint_index !== lastSprint) {
      blocks.push({ sep: true, sprint: m.sprint_index, key: `sep-${m.id}` });
      lastSprint = m.sprint_index;
    }
    blocks.push({ ...m, key: `m-${m.id}` });
  });

  return (
    <div className="feed">
      {blocks.map((b) =>
        b.sep ? (
          <div className="sprint-sep" key={b.key}>
            <span>Sprint {b.sprint}</span>
          </div>
        ) : (
          <div className={`msg ${roleClass(b.sender_role)}`} key={b.key}>
            <div className="msg-head">
              <span className={`msg-who ${roleClass(b.sender_role)}`}>{b.sender}</span>
              <span className="msg-phase">{b.phase}</span>
            </div>
            <div className="msg-body">{b.content}</div>
          </div>
        )
      )}
    </div>
  );
}

// --- grades ---------------------------------------------------------------
export function Grades({ grades }) {
  if (!grades || grades.length === 0)
    return <Empty icon="◷" title="No grades yet" hint="The teacher grades after each test." />;

  return (
    <div className="stack">
      {grades.map((g) => (
        <div className="grade-row" key={g.id}>
          <div className="grade-pill" style={{ background: gradeColor(g.grade) }}>
            {g.grade}
          </div>
          <div className="grow">
            <div className="row" style={{ gap: 8 }}>
              <strong style={{ color: "var(--cyan)" }}>{g.student_name}</strong>
              <span className="tag">sprint {g.sprint_index}</span>
            </div>
            <div className="muted" style={{ fontSize: 13.5, marginTop: 3 }}>
              {g.reasoning}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// --- journals -------------------------------------------------------------
export function Journals({ journals }) {
  if (!journals || journals.length === 0)
    return <Empty icon="❧" title="No journals yet" hint="Students reflect at the end of each sprint." />;

  return (
    <div className="stack">
      {journals.map((j) => (
        <div className="journal" key={j.id}>
          <div className="spread">
            <strong style={{ color: "var(--violet)" }}>{j.student_name}</strong>
            <span className="faint mono" style={{ fontSize: 11.5 }}>
              sprint {j.sprint_index} · {j.word_count} words
            </span>
          </div>
          <div className="journal-body">{j.content}</div>
        </div>
      ))}
    </div>
  );
}

// --- teacher journal ------------------------------------------------------
export function TeacherJournal({ journals }) {
  if (!journals || journals.length === 0)
    return (
      <Empty
        icon="🧑‍🏫"
        title="No teacher journal yet"
        hint="The teacher reflects on the class at the end of each sprint."
      />
    );

  return (
    <div className="stack">
      {journals.map((j) => (
        <div className="journal teacher" key={j.id}>
          <div className="spread">
            <strong style={{ color: "var(--amber)" }}>{j.student_name} · teacher</strong>
            <span className="faint mono" style={{ fontSize: 11.5 }}>
              sprint {j.sprint_index} · {j.word_count} words
            </span>
          </div>
          <div className="journal-body">{j.content}</div>
        </div>
      ))}
    </div>
  );
}

// --- evals ----------------------------------------------------------------
export function Evals({ evals }) {
  if (!evals || evals.length === 0)
    return (
      <Empty icon="✓" title="No eval results yet" hint="Prompt-compliance checks run during the session." />
    );

  const passed = evals.filter((e) => e.passed).length;
  const pct = Math.round((passed / evals.length) * 100);

  return (
    <div className="stack">
      <div className="panel card-pad eval-summary">
        <div>
          <div className="stat-num" style={{ fontSize: 24 }}>
            {passed}/{evals.length}
          </div>
          <div className="stat-label">checks passed</div>
        </div>
        <div className="eval-meter">
          <span style={{ width: `${pct}%` }} />
        </div>
        <span className="mono" style={{ color: pct === 100 ? "var(--green)" : "var(--amber)" }}>
          {pct}%
        </span>
      </div>

      {evals.map((e) => (
        <div className="eval-row" key={e.id}>
          <span className={`eval-icon ${e.passed ? "pass" : "fail"}`}>{e.passed ? "✓" : "✕"}</span>
          <div className="grow">
            <div className="row" style={{ gap: 8 }}>
              <span className="eval-name">{e.check_name}</span>
              <span className="tag">{e.scope}</span>
            </div>
            <div className="eval-detail">{e.detail}</div>
          </div>
          <span className="eval-score">{e.score.toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
}
