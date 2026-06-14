// Small shared presentational pieces used across pages.

export function Loading({ label = "Loading…" }) {
  return (
    <div className="empty-state">
      <div className="spinner" />
      <p className="faint" style={{ marginTop: 14 }}>
        {label}
      </p>
    </div>
  );
}

export function StatusBadge({ status }) {
  const labels = { waiting: "Waiting", running: "Live", finished: "Finished" };
  return (
    <span className={`badge ${status}`}>
      {status === "running" && <span className="pulse" />}
      {labels[status] || status}
    </span>
  );
}

export function ProgressBar({ value, cyan = false }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div className={`progress ${cyan ? "cyan" : ""}`} title={`${pct}%`}>
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}

// colour ramp for a 1..10 grade
export function gradeColor(g) {
  if (g >= 8) return "var(--green)";
  if (g >= 6) return "var(--amber)";
  if (g >= 4) return "var(--amber-deep)";
  return "var(--red)";
}

export function Empty({ icon = "∅", title, hint }) {
  return (
    <div className="empty-state">
      <div className="big">{icon}</div>
      <h3 className="h-sec" style={{ color: "var(--chalk-dim)" }}>
        {title}
      </h3>
      {hint && <p className="faint" style={{ marginTop: 6 }}>{hint}</p>}
    </div>
  );
}

export function timeAgo(iso) {
  if (!iso) return "";
  const then = new Date(iso.endsWith("Z") ? iso : iso + "Z").getTime();
  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
