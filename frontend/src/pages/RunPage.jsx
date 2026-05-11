import { useEffect, useState, useRef } from 'react'
import * as api from '../api.js'
import { ErrorBox } from '../components/UI.jsx'

const SUBJECT_SUGGESTIONS = [
  "The water cycle",
  "Pythagorean theorem",
  "Photosynthesis basics",
  "How transformers work in NLP",
  "Newton's laws of motion",
  "The French Revolution",
]

const STEP_LABELS = {
  generating_lesson:    "📖 Teacher is preparing the lesson…",
  generating_questions: "❓ Generating 10 questions…",
  asking_questions:     "🎓 Students answering & being graded…",
  break_in_progress:    "☕ Break — students chatting…",
  sprint_complete:      "✓ Sprint complete",
  break_complete:       "✓ Break complete",
}

export default function RunPage() {
  // ── Sprint config ─────────────────────────────────────────────
  const [subject, setSubject] = useState(SUBJECT_SUGGESTIONS[0])
  const [answerTimeout, setAnswerTimeout] = useState(90)
  const [sanctionThreshold, setSanctionThreshold] = useState(4)
  const [rewardThreshold, setRewardThreshold] = useState(8)
  const [breakRounds, setBreakRounds] = useState(5)
  const [breakTimeout, setBreakTimeout] = useState(60)

  // ── Live state from /api/live polling ─────────────────────────
  const [live, setLive] = useState(null)
  const [error, setError] = useState(null)
  const [stopping, setStopping] = useState(false)
  const pollRef = useRef(null)

  // Backend says something is running if status is not 'idle'
  const isRunning = live && live.status && live.status !== 'idle'

  // ── Poll /api/live ────────────────────────────────────────────
  // Always poll while page is mounted. Cheap (1.5s). Backend dictates state.
  useEffect(() => {
    const tick = async () => {
      try {
        const snap = await api.getLive()
        setLive(snap)
      } catch {
        // tolerate transient errors
      }
    }
    tick()
    pollRef.current = setInterval(tick, 1500)
    return () => clearInterval(pollRef.current)
  }, [])

  // ── Start actions (POST, returns instantly thanks to BackgroundTasks) ──
  async function start(action, fn) {
    setError(null)
    setStopping(false)
    try {
      await fn()
      // Next poll will show status=sprint_running, etc.
    } catch (e) {
      setError(e)
    }
  }

  const onSprint = () => start('sprint', () =>
    api.runSprint({ subject, answer_timeout: answerTimeout,
                     sanction_threshold: sanctionThreshold,
                     reward_threshold: rewardThreshold })
  )
  const onBreak = () => start('break', () =>
    api.runBreak({ rounds: breakRounds, timeout: breakTimeout })
  )
  const onSession = () => start('session', () =>
    api.runFullSession({
      subject, answer_timeout: answerTimeout,
      sanction_threshold: sanctionThreshold, reward_threshold: rewardThreshold,
      break_rounds: breakRounds, break_timeout: breakTimeout,
    })
  )

  // ── STOP SPRINT — calls reset endpoint + clears UI immediately ──
  async function onStop() {
    if (!confirm("Stop the current sprint? Progress will be discarded.")) return
    setStopping(true)
    try {
      await api.resetSprint({ reset_emotions: false })
      setLive(null)  // optimistic clear; next poll confirms idle
    } catch (e) {
      setError(e)
    } finally {
      setStopping(false)
    }
  }

  // ── Reset actions (independent of running state) ───────────────
  const onResetEmotions = async () => {
    try { await api.resetEmotions() }
    catch (e) { setError(e) }
  }
  const onResetDB = async () => {
    if (!confirm('Reset entire database? All sprints, badges and emotion history will be wiped.')) return
    try { await api.resetDatabase() }
    catch (e) { setError(e) }
  }

  return (
    <div className="run-page">
      <section className="card">
        <h2>Sprint configuration</h2>
        <div className="form-grid">
          <Field label="Subject" wide>
            <input list="subjects" value={subject} disabled={isRunning}
              onChange={e => setSubject(e.target.value)}/>
            <datalist id="subjects">
              {SUBJECT_SUGGESTIONS.map(s => <option key={s} value={s} />)}
            </datalist>
          </Field>
          <Field label="Answer timeout (s)">
            <input type="number" min="10" value={answerTimeout} disabled={isRunning}
              onChange={e => setAnswerTimeout(+e.target.value)}/>
          </Field>
          <Field label="Sanction threshold (≤)">
            <input type="number" min="0" max="10" value={sanctionThreshold} disabled={isRunning}
              onChange={e => setSanctionThreshold(+e.target.value)}/>
          </Field>
          <Field label="Reward threshold (≥)">
            <input type="number" min="0" max="10" value={rewardThreshold} disabled={isRunning}
              onChange={e => setRewardThreshold(+e.target.value)}/>
          </Field>
          <Field label="Break rounds">
            <input type="number" min="1" value={breakRounds} disabled={isRunning}
              onChange={e => setBreakRounds(+e.target.value)}/>
          </Field>
          <Field label="Break timeout (s)">
            <input type="number" min="10" value={breakTimeout} disabled={isRunning}
              onChange={e => setBreakTimeout(+e.target.value)}/>
          </Field>
        </div>

        <div className="run-buttons">
          <button className="btn primary" onClick={onSprint}  disabled={isRunning}>▶ Run sprint</button>
          <button className="btn"         onClick={onBreak}   disabled={isRunning}>☕ Run break</button>
          <button className="btn accent"  onClick={onSession} disabled={isRunning}>⚡ Full session</button>

          {/* STOP button — only visible while something is running */}
          {isRunning && (
            <button className="btn stop" onClick={onStop} disabled={stopping}>
              {stopping ? '⏳ Stopping…' : '■ STOP SPRINT'}
            </button>
          )}
        </div>
      </section>

      <section className="card">
        <h2>Danger zone</h2>
        <div className="run-buttons">
          <button className="btn ghost" onClick={onResetEmotions} disabled={isRunning}>Reset emotions</button>
          <button className="btn danger" onClick={onResetDB} disabled={isRunning}>Reset database</button>
        </div>
      </section>

      <ErrorBox error={error} />

      {/* LIVE PROGRESS PANEL — visible whenever backend says we're running */}
      {isRunning && <LiveProgress live={live} onStop={onStop} stopping={stopping} />}
    </div>
  )
}

// =========================================================================
// LIVE PROGRESS PANEL
// =========================================================================

function LiveProgress({ live, onStop, stopping }) {
  const pct = live.progress?.percent || 0
  const stepLabel = STEP_LABELS[live.step] || live.step || "Starting…"

  return (
    <section className="card live-panel">
      <div className="live-header">
        <div className="spinner" />
        <div className="live-title">
          <strong>{stepLabel}</strong>
          <span className="muted small">
            {live.subject && `· ${live.subject}`}
            {' · '}
            elapsed {formatElapsed(live.elapsed_seconds)}
          </span>
        </div>
        <code className="live-id">{live.current_id}</code>
        <button className="btn stop btn-stop-inline" onClick={onStop} disabled={stopping}>
          {stopping ? '⏳' : '■ Stop'}
        </button>
      </div>

      {live.progress?.total > 0 && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
          <span className="progress-label">
            {live.progress.current} / {live.progress.total}
            <span className="muted"> · {pct}%</span>
          </span>
        </div>
      )}

      <div className="live-grid">
        {live.recent_answers?.length > 0 && (
          <div className="live-col">
            <h3>Latest answers</h3>
            <div className="live-stream">
              {live.recent_answers.slice().reverse().slice(0, 8).map((a, i) => (
                <div key={`${a.student}-${a.q_idx}-${i}`} className="live-answer">
                  <span className="live-q">Q{a.q_idx + 1}</span>
                  <strong>{a.student}</strong>
                  <span className={`grade-pill grade-${a.grade >= 8 ? 'high' : a.grade <= 4 ? 'low' : 'mid'}`}>
                    {a.grade}/10
                  </span>
                  {a.action && (
                    <span className={`action-badge action-${a.action.type}`}>
                      {a.action.type === 'reward' ? '+' : ''}{a.action.points}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {live.break_messages?.length > 0 && (
          <div className="live-col">
            <h3>Break conversation</h3>
            <div className="live-stream live-stream-chat">
              {live.break_messages.slice(-8).map((m, i) => (
                <div key={i} className={`live-msg ${m.comforted_peer ? 'comfort' : ''}`}>
                  <strong>{m.speaker}:</strong> {m.message}
                  {m.mentioned_subject && <span className="warn-tag">⚠</span>}
                  {m.comforted_peer && <span className="ok-tag">🤗</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {(() => {
          const achEvents = (live.events || []).filter(e => e.kind === 'achievement')
          if (!achEvents.length) return null
          return (
            <div className="live-col">
              <h3>🎉 Achievements unlocked</h3>
              <div className="live-stream">
                {achEvents.map((e, i) => (
                  <div key={i} className="live-achievement"
                       style={{ borderColor: e.color || '#888' }}>
                    <span className="live-achievement-icon">{e.icon}</span>
                    <div>
                      <strong>{e.student}</strong>
                      <div className="muted small">{e.title}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })()}
      </div>
    </section>
  )
}

function formatElapsed(seconds) {
  if (seconds == null) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

function Field({ label, children, wide }) {
  return (
    <label className={`field ${wide ? 'wide' : ''}`}>
      <span className="field-label">{label}</span>
      {children}
    </label>
  )
}
