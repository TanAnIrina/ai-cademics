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
  const [subject, setSubject] = useState(SUBJECT_SUGGESTIONS[0])
  const [answerTimeout, setAnswerTimeout] = useState(90)
  const [sanctionThreshold, setSanctionThreshold] = useState(4)
  const [rewardThreshold, setRewardThreshold] = useState(8)
  const [breakRounds, setBreakRounds] = useState(5)
  const [breakTimeout, setBreakTimeout] = useState(60)

  const [running, setRunning] = useState(null)
  const [result, setResult]   = useState(null)
  const [error, setError]     = useState(null)
  const [live, setLive]       = useState(null)
  const [sprintStarted, setSprintStarted] = useState(false)

  const pollRef = useRef(null)
  const runTokenRef = useRef(0)

  // Poll /api/live whenever something is running (and for a few seconds after,
  // to let the user see the final state)
  useEffect(() => {
    if (running) {
      const tick = async () => {
        try {
          const snap = await api.getLive()
          setLive(snap)
        } catch (e) {
          // tolerate transient errors
        }
      }
      tick()
      pollRef.current = setInterval(tick, 1000)
    } else {
      // stop polling
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = null
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [running])

  async function withRunning(action, fn) {
    const token = ++runTokenRef.current
    setRunning(action); setError(null); setResult(null); setLive(null)
    try {
      const r = await fn()
      if (token !== runTokenRef.current) return
      setResult({ action, data: r })
    } catch (e) {
      if (token !== runTokenRef.current) return
      setError(e)
    } finally {
      if (token !== runTokenRef.current) return
      setRunning(null)
    }
  }

  const onSprint = () => {
    setSprintStarted(true)
    return withRunning('sprint', () =>
      api.runSprint({ subject, answer_timeout: answerTimeout, sanction_threshold: sanctionThreshold, reward_threshold: rewardThreshold })
    )
  }
  const onBreak = () => withRunning('break', () =>
    api.runBreak({ rounds: breakRounds, timeout: breakTimeout })
  )
  const onSession = () => withRunning('session', () =>
    api.runFullSession({
      subject, answer_timeout: answerTimeout,
      sanction_threshold: sanctionThreshold, reward_threshold: rewardThreshold,
      break_rounds: breakRounds, break_timeout: breakTimeout,
    })
  )

  const onResetEmotions = async () => {
    try { await api.resetEmotions(); setResult({ action: 'reset', data: { ok: true } }) }
    catch (e) { setError(e) }
  }
  const onResetDB = async () => {
    if (!confirm('Reset entire database? All sprints, badges and emotion history will be wiped.')) return
    try { await api.resetDatabase(); setResult({ action: 'reset_db', data: { ok: true } }) }
    catch (e) { setError(e) }
  }
  const onResetSprint = async () => {
    const keepEmotions = confirm('Reset sprint state and keep current emotions?\nPress Cancel to reset emotions too.')
    try {
      // Invalidate any in-flight run response so it cannot overwrite reset UI state.
      runTokenRef.current += 1
      await api.resetSprint(!keepEmotions)
      setResult({ action: 'reset_sprint', data: { ok: true, reset_emotions: !keepEmotions } })
      setLive(null)
      setRunning(null)
      setSprintStarted(false)
    } catch (e) {
      setError(e)
    }
  }

  return (
    <div className="run-page">
      <section className="card">
        <h2>Sprint configuration</h2>
        <div className="form-grid">
          <Field label="Subject" wide>
            <input list="subjects" value={subject} disabled={!!running}
              onChange={e => setSubject(e.target.value)}/>
            <datalist id="subjects">
              {SUBJECT_SUGGESTIONS.map(s => <option key={s} value={s} />)}
            </datalist>
          </Field>
          <Field label="Answer timeout (s)">
            <input type="number" min="10" value={answerTimeout} disabled={!!running}
              onChange={e => setAnswerTimeout(+e.target.value)}/>
          </Field>
          <Field label="Sanction threshold (≤)">
            <input type="number" min="0" max="10" value={sanctionThreshold} disabled={!!running}
              onChange={e => setSanctionThreshold(+e.target.value)}/>
          </Field>
          <Field label="Reward threshold (≥)">
            <input type="number" min="0" max="10" value={rewardThreshold} disabled={!!running}
              onChange={e => setRewardThreshold(+e.target.value)}/>
          </Field>
          <Field label="Break rounds">
            <input type="number" min="1" value={breakRounds} disabled={!!running}
              onChange={e => setBreakRounds(+e.target.value)}/>
          </Field>
          <Field label="Break timeout (s)">
            <input type="number" min="10" value={breakTimeout} disabled={!!running}
              onChange={e => setBreakTimeout(+e.target.value)}/>
          </Field>
        </div>

        <div className="run-buttons">
          <button className="btn primary" onClick={onSprint}  disabled={!!running}>
            {running === 'sprint' ? 'Running sprint…' : '▶ Run sprint'}
          </button>
          <button className="btn"         onClick={onBreak}   disabled={!!running}>
            {running === 'break' ? 'Running break…' : '☕ Run break'}
          </button>
          <button className="btn accent"  onClick={onSession} disabled={!!running}>
            {running === 'session' ? 'Running session…' : '⚡ Full session (sprint + break)'}
          </button>
          {sprintStarted && (
            <button className="btn danger" onClick={onResetSprint}>
              ■ Stop / Reset sprint
            </button>
          )}
        </div>
      </section>

      <section className="card">
        <h2>Danger zone</h2>
        <div className="run-buttons">
          <button className="btn ghost" onClick={onResetEmotions} disabled={!!running}>Reset emotions</button>
          <button className="btn danger" onClick={onResetDB} disabled={!!running}>Reset database</button>
        </div>
      </section>

      <ErrorBox error={error} />

      {/* LIVE PROGRESS */}
      {running && live && <LiveProgress live={live} action={running} />}

      {/* FINAL RESULT */}
      {result && <ResultView result={result} />}
    </div>
  )
}

// =========================================================================
// LIVE PROGRESS PANEL
// =========================================================================

function LiveProgress({ live, action }) {
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
        {/* Recent answers */}
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

        {/* Break messages */}
        {live.break_messages?.length > 0 && (
          <div className="live-col">
            <h3>Break conversation</h3>
            <div className="live-stream live-stream-chat">
              {live.break_messages.slice().reverse().slice(0, 8).reverse().map((m, i) => (
                <div key={i} className={`live-msg ${m.comforted_peer ? 'comfort' : ''}`}>
                  <strong>{m.speaker}:</strong> {m.message}
                  {m.mentioned_subject && <span className="warn-tag">⚠</span>}
                  {m.comforted_peer && <span className="ok-tag">🤗</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Achievements as they unlock */}
        {(() => {
          const achEvents = (live.events || []).filter(e => e.kind === 'achievement')
          if (!achEvents.length) return null
          return (
            <div className="live-col">
              <h3>🎉 Achievements unlocked</h3>
              <div className="live-stream">
                {achEvents.map((e, i) => (
                  <div
                    key={i}
                    className="live-achievement"
                    style={{ borderColor: e.color || '#888' }}
                  >
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

// =========================================================================
// FIELD HELPER
// =========================================================================

function Field({ label, children, wide }) {
  return (
    <label className={`field ${wide ? 'wide' : ''}`}>
      <span className="field-label">{label}</span>
      {children}
    </label>
  )
}

// =========================================================================
// FINAL RESULT (after request resolves)
// =========================================================================

function ResultView({ result }) {
  const { action, data } = result

  if (action === 'reset' || action === 'reset_db' || action === 'reset_sprint') {
    return (
      <div className="card success-banner">
        ✓ {action === 'reset_db'
          ? 'Database wiped.'
          : action === 'reset_sprint'
            ? `Sprint reset${data?.reset_emotions ? ' (emotions reset too).' : '.'}`
            : 'Emotions reset.'}
      </div>
    )
  }
  if (action === 'sprint' || (action === 'session' && data.sprint)) {
    const sprint = action === 'sprint' ? data : data.sprint
    return (
      <div className="card">
        <h2>✓ Sprint complete</h2>
        <SprintSummary sprint={sprint} />
        {action === 'session' && data.break && (
          <>
            <h2 style={{marginTop: 24}}>✓ Break complete</h2>
            <BreakSummary breakData={data.break} />
          </>
        )}
      </div>
    )
  }
  if (action === 'break') {
    return (
      <div className="card">
        <h2>✓ Break complete</h2>
        <BreakSummary breakData={data} />
      </div>
    )
  }
  return <pre className="card">{JSON.stringify(data, null, 2)}</pre>
}

function SprintSummary({ sprint }) {
  return (
    <div>
      <p className="muted small">
        <code>{sprint.sprint_id}</code> · {sprint.subject} · {Math.round(sprint.duration_seconds || 0)}s
      </p>
      <div className="result-grid">
        {Object.entries(sprint.summary || {}).map(([student, sum]) => (
          <div key={student} className="result-card">
            <h4>{student}</h4>
            <div>avg: <b>{Number(sum.average_grade ?? 0).toFixed(2)}</b>/10</div>
            <div>sanctions: {sum.sanctions ?? 0} · rewards: {sum.rewards ?? 0}</div>
            <div className="muted small">
              frust {sum.final_emotional_state?.frustration} · happy {sum.final_emotional_state?.happiness}
            </div>
            {sprint.newly_unlocked_achievements?.[student]?.length > 0 && (
              <div className="result-badges">
                {sprint.newly_unlocked_achievements[student].map(b => (
                  <span key={b.key} className="result-badge" title={b.title} style={{ borderColor: b.color }}>
                    {b.icon}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function BreakSummary({ breakData }) {
  return (
    <div>
      <p className="muted small">
        <code>{breakData.break_id}</code> · {breakData.conversation?.length} messages · forbidden: "{breakData.subject_forbidden}"
      </p>
      <div className="break-conversation">
        {(breakData.conversation || []).map((m, i) => (
          <div key={i} className={`break-msg ${m.comforted_peer ? 'comfort' : ''}`}>
            <strong>{m.speaker}:</strong> {m.message}
            {m.mentioned_subject && <span className="warn-tag">⚠ mentioned subject</span>}
            {m.comforted_peer && <span className="ok-tag">🤗 comforted</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
