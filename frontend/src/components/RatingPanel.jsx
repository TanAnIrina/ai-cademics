import { useEffect, useState } from "react";
import { api } from "../api";

const NICK_KEY = "aicademics.nick";

function Stars({ value, onPick, size = 20, readOnly = false }) {
  return (
    <span className="row" style={{ gap: 2 }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          onClick={readOnly ? undefined : () => onPick(n)}
          style={{
            cursor: readOnly ? "default" : "pointer",
            fontSize: size,
            lineHeight: 1,
            color: n <= value ? "var(--amber)" : "var(--line)",
          }}
          role={readOnly ? undefined : "button"}
          aria-label={`${n} star${n === 1 ? "" : "s"}`}
        >
          ★
        </span>
      ))}
    </span>
  );
}

export default function RatingPanel({ classroomId }) {
  const [summary, setSummary] = useState(null);
  const [nick, setNick] = useState(() => localStorage.getItem(NICK_KEY) || "");
  const [stars, setStars] = useState(0);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  async function load() {
    try {
      setSummary(await api.getRatings(classroomId));
    } catch {
      /* ignore transient errors */
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classroomId]);

  async function submit() {
    if (!nick.trim()) return setErr("Add a nickname first.");
    if (stars < 1) return setErr("Pick a star rating.");
    setBusy(true);
    setErr(null);
    try {
      localStorage.setItem(NICK_KEY, nick.trim());
      const next = await api.postRating(classroomId, {
        nickname: nick.trim(),
        stars,
        comment: comment.trim(),
      });
      setSummary(next);
      setStars(0);
      setComment("");
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack" style={{ gap: 12 }}>
      <div className="spread">
        <h3 className="h-sec" style={{ fontSize: 16 }}>Rate the lesson</h3>
        {summary && summary.count > 0 && (
          <span className="row" style={{ gap: 6 }}>
            <Stars value={Math.round(summary.average)} size={15} readOnly />
            <span className="mono faint" style={{ fontSize: 12 }}>
              {summary.average} · {summary.count}
            </span>
          </span>
        )}
      </div>

      <div className="row" style={{ gap: 8 }}>
        <input
          className="input"
          placeholder="Your nickname"
          value={nick}
          maxLength={60}
          onChange={(e) => setNick(e.target.value)}
          style={{ maxWidth: 160 }}
        />
        <Stars value={stars} onPick={setStars} />
      </div>
      <textarea
        className="textarea"
        placeholder="Optional comment…"
        rows={2}
        value={comment}
        maxLength={1000}
        onChange={(e) => setComment(e.target.value)}
      />
      {err && <p style={{ color: "var(--red)", margin: 0, fontSize: 13 }}>{err}</p>}
      <button className="btn primary sm" disabled={busy} onClick={submit}>
        {busy ? "Sending…" : "Submit rating"}
      </button>

      {summary && summary.ratings.length > 0 && (
        <div className="stack" style={{ gap: 8, marginTop: 4 }}>
          {summary.ratings.slice(0, 5).map((r) => (
            <div key={r.id} className="stack" style={{ gap: 2 }}>
              <div className="row" style={{ gap: 8 }}>
                <Stars value={r.stars} size={13} readOnly />
                <strong style={{ fontSize: 13, color: "var(--cyan)" }}>{r.nickname}</strong>
              </div>
              {r.comment && <p className="muted" style={{ fontSize: 13, margin: 0 }}>{r.comment}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
