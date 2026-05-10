import { useEffect, useState } from 'react'
import * as api from '../api.js'
import { Loading, ErrorBox } from '../components/UI.jsx'

const RARITY_ORDER = ['common', 'uncommon', 'rare', 'epic', 'legendary']

export default function AchievementsPage() {
  const [all, setAll]           = useState(null)
  const [students, setStudents] = useState(null)
  const [unlockedMap, setUnlocked] = useState({}) // { studentName: Set(keys) }
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')   // 'all' | studentName

  useEffect(() => {
    Promise.all([
      api.getAchievements(),
      api.getStudents(),
    ])
      .then(async ([allA, ss]) => {
        setAll(allA)
        setStudents(ss)
        // fetch badges per student
        const map = {}
        await Promise.all(ss.map(async s => {
          const b = await api.getStudentBadges(s.name)
          map[s.name] = new Set((b.unlocked || []).map(x => x.key))
        }))
        setUnlocked(map)
      })
      .catch(setError)
  }, [])

  if (error) return <ErrorBox error={error} />
  if (!all || !students) return <Loading />

  // Group by rarity for nicer layout
  const byRarity = {}
  for (const r of RARITY_ORDER) byRarity[r] = []
  for (const a of all) (byRarity[a.rarity] || (byRarity[a.rarity] = [])).push(a)

  const totalCount = all.length

  // Stats per student
  const studentStats = students.map(s => ({
    name: s.name,
    unlocked: unlockedMap[s.name]?.size || 0,
  }))

  return (
    <div className="achievements-page">
      <header className="ach-header">
        <h2>Achievements</h2>
        <div className="ach-stats">
          {studentStats.map(s => (
            <button
              key={s.name}
              className={`ach-student-pill ${filter === s.name ? 'active' : ''}`}
              onClick={() => setFilter(filter === s.name ? 'all' : s.name)}
            >
              <strong>{s.name}</strong> {s.unlocked}/{totalCount}
            </button>
          ))}
          <button
            className={`ach-student-pill ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            show all
          </button>
        </div>
      </header>

      {RARITY_ORDER.map(rarity => (
        byRarity[rarity]?.length > 0 && (
          <section key={rarity} className="rarity-section">
            <h3 className="rarity-title" style={{ '--r-color': byRarity[rarity][0].color }}>
              <span className="rarity-dot" />
              {rarity}
            </h3>
            <div className="badge-grid">
              {byRarity[rarity].map(a => (
                <BadgeFull
                  key={a.key}
                  achievement={a}
                  students={students}
                  unlockedMap={unlockedMap}
                  filter={filter}
                />
              ))}
            </div>
          </section>
        )
      ))}
    </div>
  )
}

function BadgeFull({ achievement, students, unlockedMap, filter }) {
  // Determine if shown as unlocked depending on filter
  let unlocked = false
  let unlockedBy = []
  for (const s of students) {
    if (unlockedMap[s.name]?.has(achievement.key)) {
      unlockedBy.push(s.name)
    }
  }
  if (filter === 'all') {
    unlocked = unlockedBy.length > 0
  } else {
    unlocked = unlockedMap[filter]?.has(achievement.key) || false
  }

  return (
    <div
      className={`badge-full ${unlocked ? 'unlocked' : 'locked'}`}
      style={{ '--rarity-color': achievement.color }}
    >
      <div className="badge-icon-lg">{achievement.icon}</div>
      <div className="badge-title-lg">{achievement.title.replace(/[^\w\s]+$/, '').trim()}</div>
      <div className="badge-desc">{achievement.description}</div>
      <div className="badge-footer">
        <span className="badge-rarity">{achievement.rarity}</span>
        {unlockedBy.length > 0 && (
          <span className="badge-unlocked-by">
            {unlockedBy.join(', ')}
          </span>
        )}
      </div>
    </div>
  )
}
