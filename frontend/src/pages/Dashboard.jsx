import { useEffect, useState } from 'react'
import * as api from '../api.js'
import { Loading, ErrorBox } from '../components/UI.jsx'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    Promise.all([
      api.getLeaderboard(),
      api.getStats(),
      api.getEmotions(),
      api.getSprints(8),
      api.getRoot(),
    ])
      .then(([leaderboard, stats, emotions, sprints, root]) => {
        if (alive) setData({ leaderboard, stats, emotions, sprints, root })
      })
      .catch(e => alive && setError(e))
    return () => { alive = false }
  }, [])

  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading />

  const { leaderboard, stats, emotions, sprints, root } = data

  return (
    <div className="dashboard">
      {/* Class config strip */}
      <section className="strip">
        <span className="strip-label">classroom</span>
        <span className="strip-pill">teacher: <b>{root.config?.teacher_model_name}</b></span>
        <span className="strip-pill">{root.config?.student_1_name} vs {root.config?.student_2_name}</span>
        {root.config?.current_subject && (
          <span className="strip-pill accent">current: {root.config.current_subject}</span>
        )}
      </section>

      {/* Big stat cards */}
      <section className="stat-row">
        <BigStat label="Total sprints" value={stats?.total_sprints ?? 0} />
        <BigStat label="Total breaks"  value={stats?.total_breaks ?? 0} />
        <BigStat label="Avg grade"     value={stats?.average_grade != null ? Number(stats.average_grade).toFixed(2) : '—'} />
        <BigStat label="Badges issued" value={stats?.total_badges ?? 0} />
      </section>

      {/* Leaderboard */}
      <section className="card">
        <h2>Leaderboard</h2>
        {leaderboard.length === 0 ? (
          <p className="muted">No students yet. Run a sprint to populate.</p>
        ) : (
          <table className="leaderboard">
            <thead>
              <tr>
                <th>#</th>
                <th>Student</th>
                <th>Avg grade</th>
                <th>Sprints</th>
                <th>Badges</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((s, i) => (
                <tr key={s.name}>
                  <td className="rank">{i + 1}</td>
                  <td><strong>{s.name}</strong></td>
                  <td><GradeBar value={s.average_grade ?? 0} /></td>
                  <td>{s.total_sprints ?? 0}</td>
                  <td>{s.total_badges ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Current emotions */}
      <section className="card">
        <h2>Current emotional state</h2>
        <div className="state-grid">
          {Object.entries(emotions).map(([name, st]) => (
            <div key={name} className="state-card">
              <h3>{name}</h3>
              <Stat label="Frustration" value={st.frustration} color="danger" />
              <Stat label="Happiness"   value={st.happiness}   color="success" />
            </div>
          ))}
        </div>
      </section>

      {/* Recent sprints */}
      <section className="card">
        <h2>Recent sprints</h2>
        {sprints.recent?.length ? (
          <ul className="sprint-list">
            {sprints.recent.map(sp => (
              <li key={sp.sprint_id} className="sprint-item">
                <code className="sprint-id">{sp.sprint_id}</code>
                <span className="sprint-subject">{sp.subject}</span>
                <span className="muted">{formatDate(sp.started_at)}</span>
              </li>
            ))}
          </ul>
        ) : <p className="muted">No sprints yet.</p>}
      </section>
    </div>
  )
}

function BigStat({ label, value }) {
  return (
    <div className="big-stat">
      <div className="big-stat-value">{value}</div>
      <div className="big-stat-label">{label}</div>
    </div>
  )
}

function Stat({ label, value, color }) {
  const pct = (value ?? 0) * 10
  return (
    <div className="stat">
      <div className="stat-row">
        <span>{label}</span>
        <span className="stat-val">{value ?? '—'}/10</span>
      </div>
      <div className="bar">
        <div className={`bar-fill bar-${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function GradeBar({ value }) {
  const v = Number(value) || 0
  return (
    <div className="grade-bar">
      <span className="grade-num">{v.toFixed(2)}</span>
      <div className="grade-bar-track">
        <div className="grade-bar-fill" style={{ width: `${v * 10}%` }} />
      </div>
    </div>
  )
}

function formatDate(iso) {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString() } catch { return iso }
}
