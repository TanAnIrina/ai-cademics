import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const NICK_KEY = "aicademics.nick";

export default function Chat({ classroomId }) {
  const [messages, setMessages] = useState([]);
  const [nick, setNick] = useState(() => localStorage.getItem(NICK_KEY) || "");
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const feedRef = useRef(null);
  const lastId = useRef(0);

  useEffect(() => {
    let active = true;
    lastId.current = 0;
    setMessages([]);

    async function poll() {
      if (document.hidden) return;
      try {
        const fresh = await api.getChat(classroomId, lastId.current);
        if (active && fresh.length) {
          lastId.current = fresh[fresh.length - 1].id;
          setMessages((prev) => [...prev, ...fresh]);
        }
      } catch {
        /* transient */
      }
    }
    poll();
    const timer = setInterval(poll, 2500);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [classroomId]);

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [messages]);

  async function send() {
    const name = nick.trim();
    const content = draft.trim();
    if (!name || !content) return;
    setSending(true);
    localStorage.setItem(NICK_KEY, name);
    try {
      await api.postChat(classroomId, name, content);
      setDraft("");
      // optimistic poll
      const fresh = await api.getChat(classroomId, lastId.current);
      if (fresh.length) {
        lastId.current = fresh[fresh.length - 1].id;
        setMessages((prev) => [...prev, ...fresh]);
      }
    } catch {
      /* ignore */
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat-wrap">
      <div className="spread" style={{ marginBottom: 10 }}>
        <h3 className="h-sec" style={{ fontSize: 18 }}>
          Observer chat
        </h3>
        <span className="faint mono" style={{ fontSize: 11.5 }}>
          {messages.length} msg
        </span>
      </div>

      <div className="chat-feed" ref={feedRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">No messages yet — say hello 👋</div>
        ) : (
          messages.map((m) => (
            <div className="chat-msg" key={m.id}>
              <span className="who">{m.nickname}</span>
              {m.content}
            </div>
          ))
        )}
      </div>

      <div className="stack" style={{ gap: 8, marginTop: 12 }}>
        <input
          className="input"
          placeholder="Your nickname"
          value={nick}
          maxLength={32}
          onChange={(e) => setNick(e.target.value)}
        />
        <div className="chat-input" style={{ marginTop: 0 }}>
          <input
            className="input grow"
            placeholder="Message…"
            value={draft}
            maxLength={500}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button className="btn primary" disabled={sending || !nick.trim() || !draft.trim()} onClick={send}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
