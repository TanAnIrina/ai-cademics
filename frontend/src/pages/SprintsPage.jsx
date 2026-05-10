import { useEffect, useState } from 'react'
import * as api from '../api.js'
import { Loading, ErrorBox } from '../components/UI.jsx'

export default function SprintsPage() {
  const [list, setList] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getSprints(50)
      .then(d => {
        setList(d)
        if (d.recent?.length && !selectedId) setSelectedId(d.recent[0].sprint_id)
      })
      .catch(setError)
  }, [])

  if (error) return <ErrorBox error={error} />
  if (!list) return <Loading />
  if (!list.recent?.length) return <p className="muted">No sprints recorded yet. Run one from the "Run" tab.</p>

  return (
    <div className="sprints-page">
      <aside className="sprint-list-pane">
        <div className="muted small">{list.total} total sprints</div>
        {list.recent.map(sp => (
          <button
            key={sp.sprint_id}
            className={`sprint-list-item ${selectedId === sp.sprint_id ? 'active' : ''}`}
            onClick={() => setSelectedId(sp.sprint_id)}
          >
            <code className="sprint-id">{sp.sprint_id}</code>
            <div className="sprint-list-subject">{sp.subject}</div>
            <div className="muted small">{formatDate(sp.started_at)}</div>
          </button>
        ))}
      </aside>

      <section className="sprint-detail-pane">
        {selectedId && <SprintDetail id={selectedId} />}
      </section>
    </div>
  )
}

function SprintDetail({ id }) {
  const [sprint, setSprint] = useState(null)
  const [error, setError] = useState(null)
  const [showLesson, setShowLesson] = useState(false)

  useEffect(() => {
    setSprint(null); setError(null)
    api.getSprint(id).then(setSprint).catch(setError)
  }, [id])

  if (error) return <ErrorBox error={error} />
  if (!sprint) return <Loading />

  const studentNames = Object.keys(sprint.answers || {})
  const questions = sprint.questions || []

  return (
    <div className="sprint-detail">
      <header className="sprint-detail-header">
        <div>
          <h2>{sprint.subject}</h2>
          <div className="muted small">
            <code>{sprint.sprint_id}</code> · {formatDate(sprint.started_at)}
            {sprint.duration_seconds && ` · ${Math.round(sprint.duration_seconds)}s`}
          </div>
        </div>
        <div className="sprint-summary">
          {studentNames.map(s => {
            const sum = sprint.summary?.[s] || {}
            return (
              <div key={s} className="sprint-summary-item">
                <strong>{s}</strong>
                <span className="grade-pill">{Number(sum.average_grade ?? 0).toFixed(2)}</span>
                <span className="muted small">
                  {sum.sanctions ?? 0} sanctions · {sum.rewards ?? 0} rewards
                </span>
              </div>
            )
          })}
        </div>
      </header>

      {sprint.lesson && (
        <section className="card">
          <button className="link-btn" onClick={() => setShowLesson(v => !v)}>
            {showLesson ? '▼' : '▶'} Lesson ({sprint.lesson.length} chars)
          </button>
          {showLesson && (
            <div className="lesson-body">
              {sprint.lesson.split(/\n+/).map((p, i) => <p key={i}>{p}</p>)}
            </div>
          )}
        </section>
      )}

      <section className="card">
        <h3>Questions & Answers</h3>
        <div className="qa-list">
          {questions.map((q, idx) => (
            <div key={idx} className="qa-block">
              <div className="qa-question">
                <span className="qa-num">Q{idx + 1}</span>
                {q}
              </div>
              <div className="qa-answers">
                {studentNames.map(s => {
                  const ans = (sprint.answers[s] || []).find(a => a.question_idx === idx)
                  if (!ans) return null
                  return (
                    <AnswerCard key={s} student={s} answer={ans} />
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </section>

      {sprint.newly_unlocked_achievements && Object.values(sprint.newly_unlocked_achievements).flat().length > 0 && (
        <section className="card">
          <h3>🎉 Achievements unlocked this sprint</h3>
          <div className="badge-grid">
            {Object.entries(sprint.newly_unlocked_achievements).map(([student, badges]) =>
              (badges || []).map(b => (
                <div
                  key={`${student}-${b.key}`}
                  className="badge unlocked"
                  style={{ '--rarity-color': b.color }}
                  title={b.description}
                >
                  <div className="badge-icon">{b.icon}</div>
                  <div className="badge-title">{b.title.replace(/[^\w\s]+$/, '').trim()}</div>
                  <div className="badge-rarity">{student} · {b.rarity}</div>
                </div>
              ))
            )}
          </div>
        </section>
      )}
    </div>
  )
}

function AnswerCard({ student, answer }) {
  const grade = answer.grade ?? 0
  const gradeClass = grade >= 8 ? 'high' : grade <= 4 ? 'low' : 'mid'
  return (
    <div className="answer-card">
      <div className="answer-head">
        <strong>{student}</strong>
        <span className={`grade-pill grade-${gradeClass}`}>{grade}/10</span>
        {answer.action && (
          <span className={`action-badge action-${answer.action.type}`}>
            {answer.action.type === 'reward' ? '+' : ''}{answer.action.points}
          </span>
        )}
      </div>
      <div className="answer-body">
        {answer.answer || <em className="muted">(no answer)</em>}
      </div>
      {answer.reasoning && (
        <div className="answer-reasoning">
          <span className="muted small">teacher:</span> {answer.reasoning}
        </div>
      )}
      {answer.action?.explanation && (
        <div className="answer-action muted small">{answer.action.explanation}</div>
      )}
    </div>
  )
}

function formatDate(iso) {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString() } catch { return iso }
}
