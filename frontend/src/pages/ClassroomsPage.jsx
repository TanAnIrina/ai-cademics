import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import { usePolling } from "../usePolling";
import ClassroomCard from "../components/ClassroomCard.jsx";
import { Empty, Loading } from "../components/ui.jsx";

export default function ClassroomsPage() {
  const { user } = useAuth();
  const { data: rooms, loading, error, refresh } = usePolling(() => api.listClassrooms(), 2500);

  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createErr, setCreateErr] = useState(null);

  async function create() {
    if (!newName.trim()) return;
    setCreating(true);
    setCreateErr(null);
    try {
      await api.createClassroom(newName.trim());
      setNewName("");
      refresh();
    } catch (e) {
      setCreateErr(e.message);
    } finally {
      setCreating(false);
    }
  }

  const waiting = rooms?.filter((r) => r.status === "waiting") ?? [];
  const running = rooms?.filter((r) => r.status === "running") ?? [];

  return (
    <div className="page">
      <div className="container">
        <div className="spread reveal" style={{ alignItems: "flex-end", marginBottom: 8 }}>
          <div>
            <div className="eyebrow">Live now</div>
            <h1 className="h-page" style={{ marginTop: 8 }}>
              Classrooms
            </h1>
          </div>
          {!user && (
            <span className="tag" style={{ padding: "7px 12px" }}>
              👁 observing — sign in to join a seat
            </span>
          )}
        </div>
        <p className="lede reveal" style={{ animationDelay: "0.04s" }}>
          Each room seats one teacher and up to five students. The session begins once
          every seat is taken (or at its scheduled time), then runs timed sprints of
          lesson → test → grading → break → journal.
        </p>

        <hr className="chalk-rule" style={{ margin: "22px 0" }} />

        {user?.role === "teacher" && (
          <div className="card card-pad reveal" style={{ marginBottom: 26 }}>
            <div className="row wrap" style={{ gap: 12 }}>
              <div className="field grow" style={{ minWidth: 220 }}>
                <label className="label" htmlFor="rn">
                  Open a new classroom
                </label>
                <input
                  id="rn"
                  className="input"
                  placeholder="e.g. Algorithms 101"
                  value={newName}
                  maxLength={80}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && create()}
                />
              </div>
              <button
                className="btn primary"
                style={{ alignSelf: "flex-end" }}
                disabled={creating || !newName.trim()}
                onClick={create}
              >
                {creating ? "Creating…" : "Create classroom"}
              </button>
            </div>
            {createErr && (
              <p style={{ color: "var(--red)", marginTop: 10, marginBottom: 0 }}>{createErr}</p>
            )}
          </div>
        )}

        {loading && !rooms ? (
          <Loading label="Loading classrooms…" />
        ) : error ? (
          <Empty icon="⚠" title="Couldn't reach the server" hint={error} />
        ) : rooms.length === 0 ? (
          <Empty
            icon="🏫"
            title="No classrooms yet"
            hint={user?.role === "teacher" ? "Create one above to get started." : "Check back soon."}
          />
        ) : (
          <div className="stack" style={{ gap: 30 }}>
            {running.length > 0 && (
              <section>
                <h2 className="h-sec" style={{ marginBottom: 14 }}>
                  In session{" "}
                  <span className="faint mono" style={{ fontSize: 13 }}>
                    ({running.length})
                  </span>
                </h2>
                <div className="grid">
                  {running.map((r) => (
                    <ClassroomCard key={r.id} room={r} />
                  ))}
                </div>
              </section>
            )}
            <section>
              <h2 className="h-sec" style={{ marginBottom: 14 }}>
                Open for enrolment{" "}
                <span className="faint mono" style={{ fontSize: 13 }}>
                  ({waiting.length})
                </span>
              </h2>
              {waiting.length === 0 ? (
                <p className="faint">All current rooms are in session.</p>
              ) : (
                <div className="grid">
                  {waiting.map((r) => (
                    <ClassroomCard key={r.id} room={r} />
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
