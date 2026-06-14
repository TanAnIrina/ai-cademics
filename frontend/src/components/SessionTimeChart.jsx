// Hand-rolled SVG chart (no charting library): plots total wall-clock minutes
// against the number of sprints, highlighting the teacher's current choice.

export default function SessionTimeChart({ points, active }) {
  if (!points || points.length === 0) return null;

  const W = 520;
  const H = 240;
  const pad = { top: 18, right: 18, bottom: 34, left: 46 };
  const innerW = W - pad.left - pad.right;
  const innerH = H - pad.top - pad.bottom;

  const xs = points.map((p) => p.num_sprints);
  const ys = points.map((p) => p.total_minutes);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const maxY = Math.max(...ys);

  const xOf = (x) => pad.left + ((x - minX) / Math.max(1, maxX - minX)) * innerW;
  const yOf = (y) => pad.top + innerH - (y / maxY) * innerH;

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${xOf(p.num_sprints).toFixed(1)} ${yOf(p.total_minutes).toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${xOf(maxX).toFixed(1)} ${(pad.top + innerH).toFixed(1)} L ${xOf(minX).toFixed(1)} ${(pad.top + innerH).toFixed(1)} Z`;

  // y gridlines at 4 steps
  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => Math.round((maxY / ticks) * i));

  const fmt = (mins) => {
    if (mins < 60) return `${mins}m`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return m ? `${h}h${m}` : `${h}h`;
  };

  return (
    <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Total time vs sprints">
      <defs>
        <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--amber)" stopOpacity="0.28" />
          <stop offset="100%" stopColor="var(--amber)" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* y grid + labels */}
      {yTicks.map((t) => (
        <g key={t}>
          <line className="chart-grid" x1={pad.left} y1={yOf(t)} x2={W - pad.right} y2={yOf(t)} />
          <text x={pad.left - 8} y={yOf(t) + 4} textAnchor="end">
            {fmt(t)}
          </text>
        </g>
      ))}

      {/* x labels */}
      {points.map((p) => (
        <text key={p.num_sprints} x={xOf(p.num_sprints)} y={H - 12} textAnchor="middle">
          {p.num_sprints}
        </text>
      ))}

      <path className="chart-area" d={areaPath} />
      <path className="chart-line" d={linePath} />

      {points.map((p) => {
        const isActive = p.num_sprints === active;
        return (
          <g key={p.num_sprints}>
            <circle
              className={`chart-dot ${isActive ? "active" : ""}`}
              cx={xOf(p.num_sprints)}
              cy={yOf(p.total_minutes)}
              r={isActive ? 6 : 4}
            />
            {isActive && (
              <text
                x={xOf(p.num_sprints)}
                y={yOf(p.total_minutes) - 12}
                textAnchor="middle"
                style={{ fill: "var(--cyan)", fontWeight: 700 }}
              >
                {fmt(p.total_minutes)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
