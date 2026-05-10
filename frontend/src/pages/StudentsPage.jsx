import { useEffect, useState } from 'react'
import * as api from '../api.js'
import { Loading, ErrorBox } from '../components/UI.jsx'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area
} from 'recharts'

export default function StudentsPage() {
  const [students, setStudents] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getStudents()
      .then(s => {
        setStudents(s)
        if (s.length && !selected) setSelected(s[0].name)
      })
      .catch(setError)
  }, [])

  if (error) return <ErrorBox error={error} />
  if (!students) return <Loading />
  if (students.length === 0) return <p className="muted">No students yet. Run a sprint first.</p>

  return (
    <div className="students-page">
      <aside className="students-list">
        {students.map(s => (
          <button
            key={s.name}
            className={`student-pill ${selected === s.name ? 'active' : ''}`}
            onClick={() => setSelected(s.name)}
          >
            <div className="student-pill-name">{s.name}</div>
            <div className="student-pill-meta">
              <span>avg {Number(s.average_grade ?? 0).toFixed(1)}</span>
              <span>·</span>
              <span>{s.total_sprints ?? 0} sprints</span>
              <span>·</span>
              <span>{s.total_badges ?? 0} 🏆</span>
            </div>
          </button>
        ))}
      </aside>

      <section className="student-detail">
        {selected && <StudentDetail name={selected} />}
      </section>
    </div>
  )
}

function StudentDetail({ name }) {
  const [detail, setDetail] = useState(null)
  const [progression, setProgression] = useState(null)
  const [emoHistory, setEmoHistory] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setDetail(null); setProgression(null); setEmoHistory(null); setError(null)
    Promise.all([
      api.getStudent(name),
      api.getStudentProgression(name),
      api.getStudentEmotionHistory(name, 200),
    ])
      .then(([d, p, e]) => { setDetail(d); setProgression(p); setEmoHistory(e) })
      .catch(setError)
  }, [name])

  if (error) return <ErrorBox error={error} />
  if (!detail) return <Loading />

  // progression: list of { sprint_id, subject, average_grade, sprint_number, ... }
  const progData = (progression || []).map((p, i) => ({
    idx: i + 1,
    grade: p.average_grade,
    subject: p.subject,
    sprint_id: p.sprint_id,
  }))

  // emotion history: list of { frustration, happiness, recorded_at, context }
  const emoData = (emoHistory || []).map((e, i) => ({
    idx: i + 1,
    frustration: e.frustration,
    happiness: e.happiness,
    context: e.context,
  }))

  return (
    <div className="student-detail-inner">
      <header className="student-header">
        <h2>{detail.name}</h2>
        <div className="student-header-stats">
          <span>avg <b>{Number(detail.average_grade ?? 0).toFixed(2)}</b>/10</span>
          <span>{detail.total_sprints ?? 0} sprints</span>
          <span>{detail.total_breaks ?? 0} breaks</span>
          <span>{detail.total_comforts_given ?? 0} comforts given</span>
        </div>
      </header>

      <div className="cards-grid">
        <section className="card">
          <h3>Current state</h3>
          <Stat label="Frustration" value={detail.current_emotions?.frustration} color="danger" />
          <Stat label="Happiness"   value={detail.current_emotions?.happiness}   color="success" />
        </section>

        <section className="card">
          <h3>Grades over time</h3>
          {progData.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={progData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a35" />
                <XAxis dataKey="idx" stroke="#888" label={{ value: 'sprint #', position: 'insideBottom', offset: -4, fill: '#888' }} />
                <YAxis domain={[0, 10]} stroke="#888" />
                <Tooltip
                  contentStyle={{ background:'#15151c', border:'1px solid #333' }}
                  formatter={(val, _, { payload }) => [val, payload.subject]}
                />
                <Line type="monotone" dataKey="grade" stroke="#e8b86d" strokeWidth={2} dot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : <p className="muted">No data yet.</p>}
        </section>

        <section className="card span-2">
          <h3>Emotional history</h3>
          {emoData.length ? (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={emoData}>
                <defs>
                  <linearGradient id="frustGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"  stopColor="#c98a8a" stopOpacity={0.6}/>
                    <stop offset="100%" stopColor="#c98a8a" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="happyGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"  stopColor="#88c997" stopOpacity={0.6}/>
                    <stop offset="100%" stopColor="#88c997" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a35" />
                <XAxis dataKey="idx" stroke="#888" />
                <YAxis domain={[0, 10]} stroke="#888" />
                <Tooltip contentStyle={{ background:'#15151c', border:'1px solid #333' }} />
                <Legend />
                <Area type="monotone" dataKey="frustration" stroke="#c98a8a" fill="url(#frustGrad)" strokeWidth={2} />
                <Area type="monotone" dataKey="happiness"   stroke="#88c997" fill="url(#happyGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : <p className="muted">No emotion data.</p>}
        </section>

        <section className="card span-2">
          <h3>Badges <span className="muted">({detail.badges?.length ?? 0} / {(detail.badges?.length ?? 0) + (detail.locked_achievements?.length ?? 0)})</span></h3>
          <div className="badge-grid">
            {(detail.badges || []).map(b => (
              <Badge key={b.key} achievement={b} unlocked />
            ))}
            {(detail.locked_achievements || []).map(b => (
              <Badge key={b.key} achievement={b} />
            ))}
          </div>
        </section>
      </div>
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
      <div className="bar"><div className={`bar-fill bar-${color}`} style={{ width: `${pct}%` }} /></div>
    </div>
  )
}

function Badge({ achievement, unlocked = false }) {
  return (
    <div
      className={`badge ${unlocked ? 'unlocked' : 'locked'}`}
      style={{ '--rarity-color': achievement.color }}
      title={achievement.description}
    >
      <div className="badge-icon">{achievement.icon}</div>
      <div className="badge-title">{achievement.title.replace(/[^\w\s]+$/, '').trim()}</div>
      <div className="badge-rarity">{achievement.rarity}</div>
    </div>
  )
}
