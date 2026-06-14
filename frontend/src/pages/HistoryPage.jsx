import { Link } from "react-router-dom";
import { api } from "../api";
import { usePolling } from "../usePolling";
import { Empty, Loading, timeAgo } from "../components/ui.jsx";

export default function HistoryPage() {
  const { data: archives, loading, error } = usePolling(() => api.listHistory(), 5000);

  return (
    <div className="page">
      <div className="container">
        <div className="reveal">
          <div className="eyebrow">The archive</div>
          <h1 className="h-page" style={{ marginTop: 8 }}>
            Finished sessions
          </h1>
          <p className="lede" style={{ marginTop: 10 }}>
            Every completed classroom is preserved in full — the sprint-by-sprint discussion,
            all grades and journals, the eval report, and the observer chat.
          </p>
        </div>

        <hr className="chalk-rule" style={{ margin: "22px 0" }} />

        {loading && !archives ? (
          <Loading label="Loading the archive…" />
        ) : error ? (
          <Empty icon="⚠" title="Couldn't reach the server" hint={error} />
        ) : archives.length === 0 ? (
          <Empty
            icon="📚"
            title="The archive is empty"
            hint="When a classroom finishes its sprints, it lands here."
          />
        ) : (
          <div className="grid">
            {archives.map((a) => (
              <Link to={`/history/${a.id}`} key={a.id} className="card room reveal">
                <div className="room-top">
                  <div>
                    <div className="room-name">{a.name}</div>
                    <div className={`room-subject ${a.subject ? "" : "empty"}`}>
                      {a.subject || "no subject"}
                    </div>
                  </div>
                  <span className="badge finished">Archived</span>
                </div>
                <div className="spread">
                  <span className="tag">{a.num_sprints} sprints</span>
                  <span className="faint mono" style={{ fontSize: 12 }}>
                    {timeAgo(a.finished_at)}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
