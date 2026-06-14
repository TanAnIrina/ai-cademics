import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import { usePolling } from "../usePolling";
import { Loading, Empty } from "../components/ui.jsx";
import StatsView from "../components/Stats.jsx";

export default function ClassroomStatsPage() {
  const { id } = useParams();
  const cid = Number(id);
  const { data: stats, loading, error } = usePolling(() => api.classroomStats(cid), 3000, [cid]);

  if (loading && !stats)
    return <div className="page"><div className="container"><Loading /></div></div>;
  if (error && !stats)
    return (
      <div className="page">
        <div className="container">
          <Empty icon="⚠" title="No statistics" hint={error} />
          <div className="center">
            <Link to="/" className="btn ghost">← Back to classrooms</Link>
          </div>
        </div>
      </div>
    );

  const room = stats.classroom;

  return (
    <div className="page">
      <div className="container">
        <Link to={`/classroom/${cid}`} className="faint" style={{ fontSize: 14 }}>
          ← Back to classroom
        </Link>

        <div className="spread reveal" style={{ margin: "12px 0 6px", alignItems: "flex-start" }}>
          <div>
            <h1 className="h-page">Statistics · {room.name}</h1>
            <div className="row wrap" style={{ gap: 10, marginTop: 8 }}>
              <span className="tag mono" style={{ color: "var(--cyan)" }}>ID {room.id}</span>
              <span className={`room-subject ${room.subject ? "" : "empty"}`}>
                {room.subject || "no subject"}
              </span>
              <span className="tag">{room.num_sprints} sprints · {room.status}</span>
            </div>
          </div>
        </div>

        <hr className="chalk-rule" style={{ margin: "20px 0" }} />

        <StatsView
          emotions={stats.emotions}
          grades={stats.grades}
          sanctions={stats.sanctions}
        />
      </div>
    </div>
  );
}
