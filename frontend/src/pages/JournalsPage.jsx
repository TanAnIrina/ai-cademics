import { useEffect, useState } from 'react'
import { API_BASE } from '../api.js'
import { Loading, ErrorBox } from '../components/UI.jsx'

export default function JournalsPage() {
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')  // 'all' | studentName

  async function load() {
    try {
      const r = await fetch(`${API_BASE}/api/journals?limit=200`)
      if (!r.ok) throw new Error(`${r.status}`)
      const j = await r.json()
      setData(j)
      if (!selected && j.journals?.length) setSelected(j.journals[0])
    } catch (e) { setError(e) }
  }

  useEffect(() => { load() }, [])
  useEffect(() => {
    const t = setInterval(load, 10_000)  // refresh every 10s
    return () => clearInterval(t)
  }, [])

  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading />

  const journals = data.journals || []
  const stats = data.stats || {}

  // Group students for filter pills
  const studentNames = [...new Set(journals.map(j => j.student_name))]

  const filtered = filter === 'all'
    ? journals
    : journals.filter(j => j.student_name === filter)

  return (
    <div className="journals-page">
      <header className="page-header">
        <div>
          <h2>Journals</h2>
          <p className="muted small">
            {stats.total_journals || 0} total · avg {stats.average_word_count || 0} words
            {' · '}
            <span className={stats.over_limit_count ? 'warn-text' : ''}>
              {stats.over_limit_count || 0} over the {stats.word_limit || 1000}-word limit
            </span>
          </p>
        </div>
        <div className="tab-pills">
          <button
            className={`pill ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All <span className="pill-count">{journals.length}</span>
          </button>
          {studentNames.map(name => (
            <button
              key={name}
              className={`pill pill-accent ${filter === name ? 'active' : ''}`}
              onClick={() => setFilter(name)}
            >
              {name}
              <span className="pill-count">
                {journals.filter(j => j.student_name === name).length}
              </span>
            </button>
          ))}
        </div>
      </header>

      {filtered.length === 0 ? (
        <div className="empty-state">
          <p className="muted">No journals yet.</p>
          <p className="muted small">
            Run a sprint — at the end, each student will write a journal entry automatically.
          </p>
        </div>
      ) : (
        <div className="journal-layout">
          <aside className="journal-list">
            {filtered.map(j => (
              <button
                key={j.id}
                className={`journal-list-item ${selected?.id === j.id ? 'active' : ''}`}
                onClick={() => setSelected(j)}
              >
                <div className="jli-head">
                  <strong>{j.student_name}</strong>
                  {j.over_word_limit && <span className="warn-pill">⚠ over</span>}
                </div>
                <div className="jli-subject muted small">
                  {j.subject || j.sprint_subject || 'no subject'}
                </div>
                <div className="jli-meta muted small">
                  {j.word_count} words · {formatDateTime(j.written_at)}
                </div>
              </button>
            ))}
          </aside>

          <section className="journal-reader">
            {selected ? <JournalPaper journal={selected} /> : (
              <div className="muted">Select a journal to read it.</div>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

function JournalPaper({ journal }) {
  const pct = Math.min(100, (journal.word_count / 1000) * 100)
  return (
    <article className="journal-paper-wrap">
      <header className="journal-paper-header">
        <div>
          <h3>{journal.student_name}'s Journal</h3>
          <div className="muted small">
            {journal.subject || journal.sprint_subject || 'no subject'}
            {' · '}
            {formatDateTime(journal.written_at)}
            {journal.sprint_id && <> · <code>{journal.sprint_id}</code></>}
          </div>
        </div>
        <div className={`word-meter ${journal.over_word_limit ? 'over' : ''}`}>
          <div className="word-meter-label">
            <span>{journal.word_count}</span>
            <span className="muted">/ 1000 words</span>
          </div>
          <div className="word-meter-track">
            <div className="word-meter-fill" style={{ width: `${pct}%` }} />
          </div>
          {journal.over_word_limit && (
            <div className="warn-text small">⚠ Exceeds 1000-word limit (US 11)</div>
          )}
        </div>
      </header>

      <div className="journal-paper">
        {journal.content.split(/\n+/).map((p, i) => (
          p.trim() && <p key={i}>{p}</p>
        ))}
      </div>
    </article>
  )
}

function formatDateTime(iso) {
  if (!iso) return ''
  try { return new Date(iso).toLocaleString() } catch { return iso }
}
