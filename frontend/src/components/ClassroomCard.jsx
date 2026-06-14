import { useNavigate } from "react-router-dom";
import { ProgressBar, StatusBadge } from "./ui.jsx";

const SLOT_ORDER = ["teacher", "student_a", "student_b"];

export default function ClassroomCard({ room }) {
  const navigate = useNavigate();
  const filled = new Set(room.members.map((m) => m.slot));

  return (
    <div className="card room reveal" onClick={() => navigate(`/classroom/${room.id}`)}>
      <div className="room-top">
        <div>
          <div className="room-name">{room.name}</div>
          <div className={`room-subject ${room.subject ? "" : "empty"}`}>
            {room.subject || "no subject yet"}
          </div>
        </div>
        <StatusBadge status={room.status} />
      </div>

      <div className="slots">
        {SLOT_ORDER.map((slot) => {
          const kind = slot === "teacher" ? "teacher" : "student";
          return (
            <span
              key={slot}
              className={`slot ${kind} ${filled.has(slot) ? "filled" : ""}`}
              title={`${slot}${filled.has(slot) ? " · filled" : " · open"}`}
            />
          );
        })}
      </div>

      <div className="spread">
        <div className="slot-legend">
          <span>
            <span className="dot amber" />1 teacher
          </span>
          <span>
            <span className="dot cyan" />2 students
          </span>
        </div>
        <span className="faint mono" style={{ fontSize: 12 }}>
          {room.members.length}/3 seats
        </span>
      </div>

      {room.status !== "waiting" && (
        <div className="stack" style={{ gap: 6 }}>
          <ProgressBar value={room.progress} cyan={room.status === "running"} />
          <span className="faint mono" style={{ fontSize: 11.5 }}>
            {room.status === "running"
              ? `sprint ${room.current_sprint}/${room.num_sprints} · ${room.phase}`
              : "session complete"}
          </span>
        </div>
      )}
    </div>
  );
}
