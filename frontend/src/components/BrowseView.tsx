import { useEffect, useState } from 'react'
import { fetchConcepts, fetchSubjects } from '../api'
import type { Concept, Subject } from '../types'

type Props = { onErrorPrefix?: string }

export default function BrowseView({ onErrorPrefix }: Props) {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [selected, setSelected] = useState<Concept | null>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchSubjects()
      .then((data) => {
        setSubjects(data)
        setSubjectId(data[0]?.id || '')
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    setError('')
    fetchConcepts(subjectId)
      .then((data: Concept[]) => {
        setConcepts(data)
        setSelected(data[0] || null)
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [subjectId])

  const visibleConcepts = concepts.filter((concept) =>
    concept.name.toLowerCase().includes(query.toLowerCase()),
  )
  const activeSubject = subjects.find((subject) => subject.id === subjectId)

  return (
    <section className="workspace">
      <aside className="sidebar">
        <label htmlFor="subject">Subject</label>
        <select id="subject" value={subjectId} onChange={(event) => setSubjectId(event.target.value)}>
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              {subject.name}
            </option>
          ))}
        </select>
        <div className="side-meta">
          <span>Concept library</span>
          <strong>{concepts.length}</strong>
        </div>
      </aside>
      <div className="content">
        {error && (
          <div className="notice">
            {onErrorPrefix}
            {error}.
          </div>
        )}
        <div className="content-heading">
          <div>
            <p className="eyebrow">{activeSubject?.name || 'Subject'}</p>
            <h2>Concepts</h2>
          </div>
          <input
            aria-label="Search concepts"
            placeholder="Search concepts"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        {loading && <p className="muted">Loading the knowledge graph...</p>}
        {!loading && !visibleConcepts.length && !error && <p className="muted">No concepts match your search.</p>}
        <div className="concept-grid">
          {visibleConcepts.map((concept) => (
            <button
              className={`concept-card ${selected?.id === concept.id ? 'active' : ''}`}
              key={concept.id}
              onClick={() => setSelected(concept)}
            >
              <span className="card-index">{String(visibleConcepts.indexOf(concept) + 1).padStart(2, '0')}</span>
              <strong>{concept.name}</strong>
              <span>{concept.definition || 'Explore this concept and its place in the graph.'}</span>
            </button>
          ))}
        </div>
        {selected && (
          <article className="detail">
            <p className="eyebrow">Selected concept</p>
            <h2>{selected.name}</h2>
            <p>{selected.definition || 'No definition has been added yet.'}</p>
          </article>
        )}
      </div>
    </section>
  )
}
