import { useEffect, useMemo, useState } from 'react'
import { attachTag, createTag, detachTag, fetchFlashcards, fetchSubjects, fetchTags } from '../api'
import type { Flashcard, Subject, Tag } from '../types'

type Props = { onErrorPrefix?: string }

function cardPreview(card: Flashcard): string {
  const match = card.back.match(/\*\*Definition:\*\*\s*(.*)/)
  return match ? match[1] : card.back
}

export default function FlashcardsView({ onErrorPrefix }: Props) {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [cards, setCards] = useState<Flashcard[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [query, setQuery] = useState('')
  const [selectedTagKeys, setSelectedTagKeys] = useState<string[]>([])
  const [untaggedOnly, setUntaggedOnly] = useState(false)
  const [selected, setSelected] = useState<Flashcard | null>(null)
  const [newTagLabel, setNewTagLabel] = useState('')
  const [newTagCategory, setNewTagCategory] = useState('topic')
  const [attachTagId, setAttachTagId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refreshTags = () =>
    fetchTags()
      .then(setTags)
      .catch((reason: Error) => setError(reason.message))

  useEffect(() => {
    Promise.all([fetchSubjects(), refreshTags()])
      .then(([subjectData]) => {
        setSubjects(subjectData)
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    setLoading(true)
    setError('')
    fetchFlashcards({
      subjectId: subjectId || undefined,
      q: query || undefined,
      tags: selectedTagKeys,
      untagged: untaggedOnly,
    })
      .then((data) => {
        setCards(data)
        if (selected && !data.some((card) => card.id === selected.id)) {
          setSelected(null)
        }
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
    // `selected` is intentionally excluded: clearing it inside the effect
    // should not refetch the list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subjectId, query, selectedTagKeys, untaggedOnly])

  const groupedTags = useMemo(() => {
    const groups: Record<string, Tag[]> = {}
    for (const tag of tags) (groups[tag.category] ||= []).push(tag)
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
  }, [tags])

  const toggleTagFilter = (tagKey: string) =>
    setSelectedTagKeys((keys) =>
      keys.includes(tagKey) ? keys.filter((key) => key !== tagKey) : [...keys, tagKey],
    )

  const handleCreateTag = async () => {
    if (!newTagLabel.trim()) return
    try {
      await createTag(newTagLabel.trim(), newTagCategory.trim() || 'topic')
      setNewTagLabel('')
      await refreshTags()
    } catch (reason) {
      setError((reason as Error).message)
    }
  }

  const handleAttach = async () => {
    if (!selected || !attachTagId) return
    try {
      const updated = await attachTag(selected.id, attachTagId)
      setSelected(updated)
      setCards((current) => current.map((card) => (card.id === updated.id ? updated : card)))
      setAttachTagId('')
      await refreshTags()
    } catch (reason) {
      setError((reason as Error).message)
    }
  }

  const handleDetach = async (tagId: string) => {
    if (!selected) return
    try {
      const updated = await detachTag(selected.id, tagId)
      setSelected(updated)
      setCards((current) => current.map((card) => (card.id === updated.id ? updated : card)))
      await refreshTags()
    } catch (reason) {
      setError((reason as Error).message)
    }
  }

  const activeSubject = subjects.find((subject) => subject.id === subjectId)

  return (
    <section className="workspace">
      <aside className="sidebar">
        <label htmlFor="flashcard-subject">Subject</label>
        <select
          id="flashcard-subject"
          value={subjectId}
          onChange={(event) => setSubjectId(event.target.value)}
        >
          <option value="">All subjects</option>
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              {subject.name}
            </option>
          ))}
        </select>

        <div className="tag-filter">
          <span className="sidebar-label">Filter by tag</span>
          {groupedTags.map(([category, categoryTags]) => (
            <div key={category} className="tag-group">
              <span className="tag-category">{category}</span>
              <div className="tag-chip-row">
                {categoryTags.map((tag) => (
                  <button
                    key={tag.id}
                    className={`tag-chip ${selectedTagKeys.includes(tag.tag_key) ? 'active' : ''}`}
                    onClick={() => toggleTagFilter(tag.tag_key)}
                  >
                    {tag.label} <small>{tag.flashcard_count}</small>
                  </button>
                ))}
              </div>
            </div>
          ))}
          {!groupedTags.length && <p className="muted">No tags yet — create one below.</p>}
          <label className="untagged-toggle">
            <input
              type="checkbox"
              checked={untaggedOnly}
              onChange={(event) => setUntaggedOnly(event.target.checked)}
            />
            Untagged only
          </label>
        </div>

        <div className="tag-create">
          <span className="sidebar-label">New tag</span>
          <input
            aria-label="New tag label"
            placeholder="e.g. midterm-2"
            value={newTagLabel}
            onChange={(event) => setNewTagLabel(event.target.value)}
          />
          <select value={newTagCategory} onChange={(event) => setNewTagCategory(event.target.value)}>
            <option value="topic">topic</option>
            <option value="exam">exam</option>
            <option value="difficulty">difficulty</option>
          </select>
          <button className="link-button" onClick={handleCreateTag} disabled={!newTagLabel.trim()}>
            Create tag
          </button>
        </div>

        <div className="side-meta">
          <span>Flashcards</span>
          <strong>{cards.length}</strong>
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
            <p className="eyebrow">{activeSubject?.name || 'All subjects'}</p>
            <h2>Flashcards</h2>
          </div>
          <input
            aria-label="Search flashcards"
            placeholder="Search flashcards"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        {loading && <p className="muted">Loading flashcards...</p>}
        {!loading && !cards.length && !error && <p className="muted">No flashcards match your filters.</p>}
        <div className="concept-grid">
          {cards.map((card) => (
            <button
              className={`concept-card ${selected?.id === card.id ? 'active' : ''}`}
              key={card.id}
              onClick={() => setSelected(card)}
            >
              <span className="card-index">{card.domain}</span>
              <strong>{card.id}</strong>
              <span>{cardPreview(card)}</span>
              {!!card.tags.length && (
                <span className="card-tags">
                  {card.tags.map((tag) => (
                    <em key={tag.id}>{tag.label}</em>
                  ))}
                </span>
              )}
            </button>
          ))}
        </div>

        {selected && (
          <article className="detail detail-dark">
            <p className="eyebrow">Selected flashcard · {selected.domain}</p>
            <h2>{selected.id}</h2>
            <p>{cardPreview(selected)}</p>
            <div className="tag-editor">
              <div className="tag-chip-row">
                {selected.tags.map((tag) => (
                  <button
                    key={tag.id}
                    className="tag-chip active removable"
                    title="Click to remove this tag"
                    onClick={() => handleDetach(tag.id)}
                  >
                    {tag.label} ✕
                  </button>
                ))}
                {!selected.tags.length && <p className="muted">No tags on this card yet.</p>}
              </div>
              <div className="tag-attach-row">
                <select value={attachTagId} onChange={(event) => setAttachTagId(event.target.value)}>
                  <option value="">Attach a tag…</option>
                  {tags
                    .filter((tag) => !selected.tags.some((st) => st.id === tag.id))
                    .map((tag) => (
                      <option key={tag.id} value={tag.id}>
                        {tag.label} ({tag.category})
                      </option>
                    ))}
                </select>
                <button className="primary-action" onClick={handleAttach} disabled={!attachTagId}>
                  Attach
                </button>
              </div>
            </div>
          </article>
        )}
      </div>
    </section>
  )
}
