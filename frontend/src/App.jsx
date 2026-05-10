import { useState } from 'react'
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
  const [tab, setTab] = useState('dashboard')

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
        {tab === 'dashboard'    && <Dashboard />}
        {tab === 'students'     && <StudentsPage />}
        {tab === 'sprints'      && <SprintsPage />}
        {tab === 'achievements' && <AchievementsPage />}
        {tab === 'run'          && <RunPage />}
      </main>
    </div>
  )
}
