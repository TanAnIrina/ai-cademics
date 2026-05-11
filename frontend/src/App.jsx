import { useEffect, useState } from 'react'
import Dashboard from './pages/Dashboard.jsx'
import StudentsPage from './pages/StudentsPage.jsx'
import SprintsPage from './pages/SprintsPage.jsx'
import AchievementsPage from './pages/AchievementsPage.jsx'
import RunPage from './pages/RunPage.jsx'

const TABS = [
  { id: 'dashboard',    label: 'Dashboard' },
  { id: 'students',     label: 'Students' },
  { id: 'sprints',      label: 'Sprints' },
  { id: 'achievements', label: 'Achievements' },
  { id: 'run',          label: 'Run' },
]

export default function App() {
  const [tab, setTab] = useState(() => {
    const saved = localStorage.getItem('activeTab')
    return TABS.some(t => t.id === saved) ? saved : 'dashboard'
  })

  useEffect(() => {
    localStorage.setItem('activeTab', tab)
  }, [tab])

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="logo-dot" />
          <h1>ai-cademics</h1>
          <span className="subtitle">distributed multi-agent classroom · v2</span>
        </div>
        <nav className="tabs">
          {TABS.map(t => (
            <button
              key={t.id}
              className={`tab ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="app-main">
        <div style={{ display: tab === 'dashboard' ? 'block' : 'none' }}>
          <Dashboard />
        </div>
        <div style={{ display: tab === 'students' ? 'block' : 'none' }}>
          <StudentsPage />
        </div>
        <div style={{ display: tab === 'sprints' ? 'block' : 'none' }}>
          <SprintsPage />
        </div>
        <div style={{ display: tab === 'achievements' ? 'block' : 'none' }}>
          <AchievementsPage />
        </div>
        <div style={{ display: tab === 'run' ? 'block' : 'none' }}>
          <RunPage />
        </div>
      </main>
    </div>
  )
}
