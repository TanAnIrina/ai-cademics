import { Empty, EmotionBars, EMOTIONS } from "./ui.jsx";

const SLOT_LABEL = { teacher: "Teacher", student_a: "Student A", student_b: "Student B" };
const SLOT_ORDER = ["teacher", "student_a", "student_b"];

function slotLabel(slot, i) {
  if (SLOT_LABEL[slot]) return SLOT_LABEL[slot];
  const m = /^student_(\d+)$/.exec(slot);
  if (m) return `Student ${m[1]}`;
  return slot || `Agent ${i + 1}`;
}

// A small multi-series line chart on a 0..yMax scale, x stepped by sprint.
export function MultiLineChart({ series, xs, yMax = 10, height = 200 }) {
  const W = 520;
  const H = height;
  const padL = 34;
  const padR = 14;
  const padT = 14;
  const padB = 28;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const xIndex = (x) => xs.indexOf(x);
  const xpos = (x) => padL + (xs.length <= 1 ? 0.5 : xIndex(x) / (xs.length - 1)) * plotW;
  const ypos = (y) => padT + (1 - y / yMax) * plotH;
  const yTicks = [0, yMax / 2, yMax];

  return (
    <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img">
      {yTicks.map((t) => (
        <g key={t}>
          <line x1={padL} y1={ypos(t)} x2={W - padR} y2={ypos(t)} className="chart-grid" />
          <text x={padL - 6} y={ypos(t) + 3} textAnchor="end">{t}</text>
        </g>
      ))}
      {xs.map((x) => (
        <text key={x} x={xpos(x)} y={H - 9} textAnchor="middle">
          {x === 0 ? "start" : `s${x}`}
        </text>
      ))}
      {series.map((s) => {
        const d = s.points
          .map((p, i) => `${i === 0 ? "M" : "L"}${xpos(p.x).toFixed(1)},${ypos(p.y).toFixed(1)}`)
          .join(" ");
        return (
          <g key={s.label}>
            <path d={d} fill="none" stroke={s.color} strokeWidth="2.2" />
            {s.points.map((p) => (
              <circle key={p.x} cx={xpos(p.x)} cy={ypos(p.y)} r="2.6" fill={s.color} />
            ))}
          </g>
        );
      })}
    </svg>
  );
}

export function Legend({ items }) {
  return (
    <div className="row wrap" style={{ gap: 12, marginTop: 8 }}>
      {items.map((it) => (
        <span key={it.label} className="row" style={{ gap: 6, fontSize: 12.5 }}>
          <span style={{ width: 12, height: 3, borderRadius: 2, background: it.color, display: "inline-block" }} />
          <span className="faint">{it.label}</span>
        </span>
      ))}
    </div>
  );
}

// Renders the full statistics body from a normalized shape:
//   { emotions: [{sprint_index, slot, agent_name, <emotion>:int...}],
//     grades:   [{sprint_index, student_name, grade}],
//     sanctions:[{student_name, sanctions, rewards, net_points}] }
// Used by both the live stats page and the archived-session stats tab.
export default function StatsView({ emotions = [], grades = [], sanctions = [] }) {
  const xs = [...new Set(emotions.map((e) => e.sprint_index))].sort((a, b) => a - b);

  const bySlot = {};
  emotions.forEach((e) => {
    (bySlot[e.slot] ||= []).push(e);
  });
  const knownFirst = SLOT_ORDER.filter((s) => bySlot[s]);
  const extra = Object.keys(bySlot).filter((s) => !SLOT_ORDER.includes(s)).sort();
  const agents = [...knownFirst, ...extra].map((slot, i) => ({
    slot,
    label: slotLabel(slot, i),
    name: bySlot[slot][0].agent_name,
    snaps: [...bySlot[slot]].sort((a, b) => a.sprint_index - b.sprint_index),
  }));

  const studentNames = [...new Set(grades.map((g) => g.student_name))];
  const gradeColors = ["var(--cyan)", "var(--violet)", "var(--amber)", "var(--green)", "var(--red)"];
  const gradeXs = [...new Set(grades.map((g) => g.sprint_index))].sort((a, b) => a - b);
  const gradeSeries = studentNames.map((name, i) => ({
    label: name,
    color: gradeColors[i % gradeColors.length],
    points: grades
      .filter((g) => g.student_name === name)
      .sort((a, b) => a.sprint_index - b.sprint_index)
      .map((g) => ({ x: g.sprint_index, y: g.grade })),
  }));

  if (xs.length === 0) {
    return (
      <Empty
        icon="📈"
        title="No data yet"
        hint="Emotion snapshots and grades appear as the session runs through its sprints."
      />
    );
  }

  const finalBySlot = {};
  agents.forEach((a) => (finalBySlot[a.slot] = a.snaps[a.snaps.length - 1]));

  return (
    <div className="stack" style={{ gap: 22 }}>
      {gradeSeries.length > 0 && (
        <div className="card card-pad">
          <h3 className="h-sec" style={{ fontSize: 18, marginBottom: 4 }}>Grade trajectory</h3>
          <p className="faint" style={{ fontSize: 12.5, margin: "0 0 10px" }}>
            How each student's grade moved across sprints (0–10).
          </p>
          <MultiLineChart series={gradeSeries} xs={gradeXs} yMax={10} />
          <Legend items={gradeSeries} />
        </div>
      )}

      <div className="detail-grid stats-grid">
        {agents.map((a) => {
          const series = EMOTIONS.map((e) => ({
            label: e.label,
            color: e.color,
            points: a.snaps.map((s) => ({ x: s.sprint_index, y: s[e.key] })),
          }));
          return (
            <div className="card card-pad" key={a.slot}>
              <div className="spread" style={{ marginBottom: 4 }}>
                <h3 className="h-sec" style={{ fontSize: 17 }}>{a.name}</h3>
                <span className="tag">{a.label}</span>
              </div>
              <p className="faint" style={{ fontSize: 12.5, margin: "0 0 10px" }}>
                Emotional evolution across the session.
              </p>
              <MultiLineChart series={series} xs={xs} yMax={10} height={180} />
              <Legend items={series} />
              {finalBySlot[a.slot] && (
                <div style={{ marginTop: 14 }}>
                  <span className="eyebrow">Final state</span>
                  <div style={{ marginTop: 8 }}>
                    <EmotionBars source={finalBySlot[a.slot]} />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="card card-pad">
        <h3 className="h-sec" style={{ fontSize: 18, marginBottom: 10 }}>Sanctions &amp; rewards</h3>
        {sanctions.length === 0 ? (
          <p className="faint" style={{ margin: 0 }}>No sanctions or rewards were issued.</p>
        ) : (
          <div className="stack" style={{ gap: 8 }}>
            {sanctions.map((s) => (
              <div className="row spread" key={s.student_name}>
                <strong style={{ color: "var(--cyan)" }}>{s.student_name}</strong>
                <div className="row" style={{ gap: 10 }}>
                  <span className="tag" style={{ color: "var(--red)" }}>
                    {s.sanctions} sanction{s.sanctions === 1 ? "" : "s"}
                  </span>
                  <span className="tag" style={{ color: "var(--green)" }}>
                    {s.rewards} reward{s.rewards === 1 ? "" : "s"}
                  </span>
                  <span className="mono" style={{ color: s.net_points >= 0 ? "var(--green)" : "var(--red)" }}>
                    {s.net_points >= 0 ? "+" : ""}{s.net_points}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
