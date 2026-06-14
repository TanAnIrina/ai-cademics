import { useNavigate } from "react-router-dom";
import { ProgressBar, StatusBadge } from "./ui.jsx";

const STUDENT_SLOTS = ["student_a", "student_b", "student_c", "student_d", "student_e"];

export default function ClassroomCard({ room }) {
  const navigate = useNavigate();
  const filled = new Set(room.members.map((m) => m.slot));
  const maxStudents = room.max_students ?? 2;
  const capacity = 1 + maxStudents;
  const slots = ["teacher", ...STUDENT_SLOTS.slice(0, maxStudents)];

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
        {slots.map((slot) => {
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
            <span className="dot cyan" />{maxStudents} student{maxStudents === 1 ? "" : "s"}
          </span>
        </div>
        <span className="faint mono" style={{ fontSize: 12 }}>
          {room.members.length}/{capacity} seats
        </span>
      </div>

      {room.scheduled_start && room.status === "waiting" && (
        <span className="faint mono" style={{ fontSize: 11.5, color: "var(--violet)" }}>
          🕑 starts {new Date(room.scheduled_start).toLocaleString()}
        </span>
      )}

      {room.status !== "waiting" && (
        <div className="stack" style={{ gap: 6 }}>
          <ProgressBar value={room.progress} cyan={room.status === "running"} />
          <span className="faint mono" style={{ fontSize: 11.5 }}>
            {room.status === "running"
              ? room.phase === "choosing"
                ? "choosing next subject…"
                : `sprint ${room.current_sprint}/${room.num_sprints} · ${room.phase}`
              : "session complete"}
          </span>
        </div>
      )}
    </div>
  );
}
