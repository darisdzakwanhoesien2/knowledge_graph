import { useEffect, useState } from 'react'
import './App.css'

type Subject = { id: string; name: string }
type Concept = { id: string; subject_id: string; name: string; definition?: string }

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [selected, setSelected] = useState<Concept | null>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API_URL}/subjects`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Unable to load subjects')))
      .then((data: Subject[]) => { setSubjects(data); setSubjectId(data[0]?.id || '') })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    fetch(`${API_URL}/concepts?subject_id=${encodeURIComponent(subjectId)}`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Unable to load concepts')))
      .then((data: Concept[]) => { setConcepts(data); setSelected(data[0] || null) })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [subjectId])

  const visibleConcepts = concepts.filter((concept) => concept.name.toLowerCase().includes(query.toLowerCase()))
  const activeSubject = subjects.find((subject) => subject.id === subjectId)

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">KG</span><span>Knowledge Studio</span></div>
        <span className="status"><i /> Local learning space</span>
      </header>
      <section className="intro">
        <p className="eyebrow">Explore the graph</p>
        <h1>Build understanding,<br /><em>one connection at a time.</em></h1>
        <p className="lede">Browse curated subjects and the concepts that shape them.</p>
      </section>
      {error && <div className="notice">{error}. Check that the API is running at {API_URL}.</div>}
      <section className="workspace">
        <aside className="sidebar">
          <label htmlFor="subject">Subject</label>
          <select id="subject" value={subjectId} onChange={(event) => setSubjectId(event.target.value)}>
            {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
          </select>
          <div className="side-meta"><span>Concept library</span><strong>{concepts.length}</strong></div>
        </aside>
        <div className="content">
          <div className="content-heading"><div><p className="eyebrow">{activeSubject?.name || 'Subject'}</p><h2>Concepts</h2></div><input aria-label="Search concepts" placeholder="Search concepts" value={query} onChange={(event) => setQuery(event.target.value)} /></div>
          {loading && <p className="muted">Loading the knowledge graph...</p>}
          {!loading && !visibleConcepts.length && <p className="muted">No concepts match your search.</p>}
          <div className="concept-grid">{visibleConcepts.map((concept) => <button className={`concept-card ${selected?.id === concept.id ? 'active' : ''}`} key={concept.id} onClick={() => setSelected(concept)}><span className="card-index">{String(visibleConcepts.indexOf(concept) + 1).padStart(2, '0')}</span><strong>{concept.name}</strong><span>{concept.definition || 'Explore this concept and its place in the graph.'}</span></button>)}</div>
          {selected && <article className="detail"><p className="eyebrow">Selected concept</p><h2>{selected.name}</h2><p>{selected.definition || 'No definition has been added yet.'}</p></article>}
        </div>
      </section>
    </main>
  )
}

export default App
