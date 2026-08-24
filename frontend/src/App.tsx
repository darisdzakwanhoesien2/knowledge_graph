import { useState } from 'react'
import BrowseView from './components/BrowseView'
import TestFlow from './components/TestFlow'
import './App.css'

type View = 'browse' | 'test'

function App() {
  const [view, setView] = useState<View>('browse')

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
          <button className={view === 'test' ? 'active' : ''} onClick={() => setView('test')}>
            Take a test
          </button>
        </nav>
      </header>
      <section className="intro">
        <p className="eyebrow">{view === 'browse' ? 'Explore the graph' : 'Assessment'}</p>
        <h1>
          Build understanding,
          <br />
          <em>{view === 'browse' ? 'one connection at a time.' : 'prove what you know.'}</em>
        </h1>
        <p className="lede">
          {view === 'browse'
            ? 'Browse curated subjects and the concepts that shape them.'
            : 'Take a published test and get transparent scoring with study suggestions.'}
        </p>
      </section>
      {view === 'browse' ? <BrowseView onErrorPrefix="Unable to load data. " /> : <TestFlow />}
    </main>
  )
}

export default App
