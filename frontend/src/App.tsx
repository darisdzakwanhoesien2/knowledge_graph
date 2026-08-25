import { useState } from 'react'
import BrowseView from './components/BrowseView'
import FlashcardsView from './components/FlashcardsView'
import HistoryView from './components/HistoryView'
import TestFlow from './components/TestFlow'
import './App.css'

type View = 'browse' | 'flashcards' | 'test' | 'history'

function App() {
  const [view, setView] = useState<View>('browse')

  const introCopy: Record<View, { eyebrow: string; accent: string; lede: string }> = {
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

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">KG</span>
          <span>Knowledge Studio</span>
        </div>
        <nav className="nav-tabs" aria-label="Main navigation">
          <button className={view === 'browse' ? 'active' : ''} onClick={() => setView('browse')}>
            Browse
          </button>
          <button className={view === 'flashcards' ? 'active' : ''} onClick={() => setView('flashcards')}>
            Flashcards
          </button>
          <button className={view === 'test' ? 'active' : ''} onClick={() => setView('test')}>
            Take a test
          </button>
          <button className={view === 'history' ? 'active' : ''} onClick={() => setView('history')}>
            History
          </button>
        </nav>
      </header>
      <section className="intro">
        <p className="eyebrow">{introCopy[view].eyebrow}</p>
        <h1>
          Build understanding,
          <br />
          <em>{introCopy[view].accent}</em>
        </h1>
        <p className="lede">{introCopy[view].lede}</p>
      </section>
      {view === 'browse' && <BrowseView onErrorPrefix="Unable to load data. " />}
      {view === 'flashcards' && <FlashcardsView onErrorPrefix="Unable to load flashcards. " />}
      {view === 'test' && <TestFlow />}
      {view === 'history' && <HistoryView />}
    </main>
  )
}

export default App
