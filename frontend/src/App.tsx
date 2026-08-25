import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import BrowseView from './components/BrowseView'
import FlashcardsView from './components/FlashcardsView'
import HistoryView from './components/HistoryView'
import TestFlow from './components/TestFlow'
import './App.css'

type View = 'browse' | 'flashcards' | 'test' | 'history'

const INTRO_COPY: Record<View, { eyebrow: string; accent: string; lede: string }> = {
  browse: {
    eyebrow: 'Explore the graph',
    accent: 'one connection at a time.',
    lede: 'Browse curated subjects and the concepts that shape them.',
  },
  flashcards: {
    eyebrow: 'Study & organize',
    accent: 'tag your way to mastery.',
    lede: 'Browse flashcards, group them by topic or exam, and filter by tag.',
  },
  test: {
    eyebrow: 'Assessment',
    accent: 'prove what you know.',
    lede: 'Take a published test and get transparent scoring with study suggestions.',
  },
  history: {
    eyebrow: 'Assessment history',
    accent: 'learn from every attempt.',
    lede: 'Reopen submitted tests, review grading evidence, and study linked concepts.',
  },
}

const VIEW_BY_PATH: Record<string, View> = {
  '/': 'browse',
  '/flashcards': 'flashcards',
  '/test': 'test',
  '/history': 'history',
}

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return isActive ? 'active' : ''
}

function App() {
  const location = useLocation()
  const view = VIEW_BY_PATH[location.pathname] ?? 'browse'
  const copy = INTRO_COPY[view]

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">KG</span>
          <span>Knowledge Studio</span>
        </div>
        <nav className="nav-tabs" aria-label="Main navigation">
          <NavLink to="/" end className={navLinkClass}>
            Browse
          </NavLink>
          <NavLink to="/flashcards" className={navLinkClass}>
            Flashcards
          </NavLink>
          <NavLink to="/test" className={navLinkClass}>
            Take a test
          </NavLink>
          <NavLink to="/history" className={navLinkClass}>
            History
          </NavLink>
        </nav>
      </header>
      <section className="intro">
        <p className="eyebrow">{copy.eyebrow}</p>
        <h1>
          Build understanding,
          <br />
          <em>{copy.accent}</em>
        </h1>
        <p className="lede">{copy.lede}</p>
      </section>
      <Routes>
        <Route path="/" element={<BrowseView onErrorPrefix="Unable to load data. " />} />
        <Route
          path="/flashcards"
          element={<FlashcardsView onErrorPrefix="Unable to load flashcards. " />}
        />
        <Route path="/test" element={<TestFlow />} />
        <Route path="/history" element={<HistoryView />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </main>
  )
}

export default App
