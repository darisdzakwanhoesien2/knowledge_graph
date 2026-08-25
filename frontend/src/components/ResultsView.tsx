import { useMemo, useState } from 'react'
import { fetchConceptContext } from '../api'
import type { ConceptContext, GradingResult, ResponseRecord } from '../types'

type Props = {
  result: GradingResult
  onRestart?: () => void
  onBack?: () => void
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

function isResponseCorrect(resp: ResponseRecord): boolean {
  return resp.correct === true || (!!resp.max_score && (resp.score || 0) / resp.max_score >= 0.999)
}

function weaknessRatio(resp: ResponseRecord): number {
  if (!resp.max_score) return resp.correct === true ? 0 : 1
  return (resp.score || 0) / resp.max_score
}

export default function ResultsView({ result, onRestart, onBack }: Props) {
  const { scores, responses } = result
  const [contextName, setContextName] = useState('')
  const [context, setContext] = useState<ConceptContext | null>(null)
  const [contextLoading, setContextLoading] = useState(false)

  // FR-15: concepts from the weakest responses come first.
  const studySuggestions = useMemo(() => {
    const missed = responses.filter((r) => !isResponseCorrect(r)).sort((a, b) => weaknessRatio(a) - weaknessRatio(b))
    const ordered: string[] = []
    for (const resp of missed) for (const link of resp.node_links || []) {
      if (!ordered.includes(link)) ordered.push(link)
    }
    return ordered
  }, [responses])

  function openConcept(name: string) {
    if (contextName === name && context) {
      setContextName('')
      setContext(null)
      return
    }
    setContextName(name)
    setContext(null)
    setContextLoading(true)
    fetchConceptContext(name)
      .then(setContext)
      .catch(() => setContext({ node: name, exists: false }))
      .finally(() => setContextLoading(false))
  }

  return (
    <div className="runner results">
      <div className="result-banner">
        {onBack ? (
          <button className="banner-back" onClick={onBack}>
            ← Back to history
          </button>
        ) : null}
        <p className="eyebrow">Attempt {result.attempt_id}</p>
        <h2>
          Final score <em>{formatPercent(scores.final_score)}</em>
        </h2>
        <p className="muted">Submitted {new Date(result.submitted_at).toLocaleString()}</p>
      </div>
      <div className="metrics">
        <div className="metric">
          <span>MCQ</span>
          <strong>
            {scores.mcq_score}/{scores.mcq_max}
          </strong>
          {scores.mcq_pct !== null && <small>{formatPercent(scores.mcq_pct)}</small>}
        </div>
        <div className="metric">
          <span>Essay</span>
          <strong>
            {scores.essay_score}/{scores.essay_max}
          </strong>
          {scores.essay_pct !== null && <small>{formatPercent(scores.essay_pct)}</small>}
        </div>
        <div className="metric">
          <span>Final</span>
          <strong>{formatPercent(scores.final_score)}</strong>
        </div>
      </div>
      <h3 className="section-title">Question review</h3>
      <div className="response-list">
        {responses.map((resp, index) => {
          const correct = isResponseCorrect(resp)
          const title = resp.question || resp.prompt || resp.question_id
          return (
            <details className="response-item" key={`${resp.question_kind}-${resp.question_id}-${index}`}>
              <summary>
                <span className={`mark ${correct ? 'ok' : 'bad'}`}>{correct ? '✓' : '✗'}</span> {title.slice(0, 120)}
              </summary>
              <div className="response-body">
                {resp.question_kind === 'mcq' ? (
                  <p>
                    Your answer: <code>{resp.selected_option || '—'}</code> · Correct:{' '}
                    <code>{resp.correct_option}</code>
                    {!!resp.node_links?.length && (
                      <>
                        {' '}· Concept(s):{' '}
                        {resp.node_links.map((link) => (
                          <button className="concept-link" key={link} onClick={() => openConcept(link)}>
                            {link}
                          </button>
                        ))}
                      </>
                    )}
                  </p>
                ) : (
                  <>
                    <p className="answer-text">{resp.essay_text || '(empty answer)'}</p>
                    {!!resp.matched_keywords?.length && (
                      <p className="muted">Matched keywords: {resp.matched_keywords.join(', ')}</p>
                    )}
                    {!!resp.matched_criteria?.length && (
                      <ul className="criteria">
                        {resp.matched_criteria.map((c) => (
                          <li key={c.keyword}>
                            <span className={c.matched ? 'hit' : 'miss'}>{c.matched ? '●' : '○'}</span>{' '}
                            <code>{c.keyword}</code>
                            {c.weight !== undefined && <> (+{c.weight})</>}
                            {c.evidence && <em> — “...{c.evidence}...”</em>}
                          </li>
                        ))}
                      </ul>
                    )}
                    {!!resp.node_links?.length && (
                      <p className="muted">
                        Concept(s):{' '}
                        {resp.node_links.map((link) => (
                          <button className="concept-link" key={link} onClick={() => openConcept(link)}>
                            {link}
                          </button>
                        ))}
                      </p>
                    )}
                  </>
                )}
                {resp.grading_notes && <p className="muted note">Grading note: {resp.grading_notes}</p>}
              </div>
            </details>
          )
        })}
      </div>
      {studySuggestions.length > 0 && (
        <>
          <h3 className="section-title">Study suggestions, weakest first</h3>
          <ul className="study-list">
            {studySuggestions.map((name) => (
              <li key={name}>
                <button className={`concept-link ${contextName === name ? 'open' : ''}`} onClick={() => openConcept(name)}>
                  {name}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      {contextName && (
        <aside className="concept-panel">
          <div className="panel-head">
            <strong>{contextName}</strong>
            <button className="link-button" onClick={() => openConcept(contextName)}>
              Close
            </button>
          </div>
          {contextLoading && <p className="muted">Loading concept context...</p>}
          {!contextLoading && context && !context.exists && (
            <p className="muted">This concept is not in the knowledge graph yet.</p>
          )}
          {!contextLoading && context?.exists && (
            <>
              {context.definition ? <p>{context.definition}</p> : <p className="muted">No definition yet.</p>}
              {!!context.neighbors?.length && (
                <>
                  <p className="eyebrow">Graph neighbors</p>
                  <ul className="neighbor-list">
                    {context.neighbors.slice(0, 8).map(([name, arrow, rel], i) => (
                      <li key={`${name}-${i}`}>
                        <span className="rel">{rel}</span> {arrow} {name}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {(context.flashcard?.front || context.flashcard?.back) && (
                <>
                  <p className="eyebrow">Flashcard</p>
                  {context.flashcard.front && <p>{context.flashcard.front}</p>}
                  {context.flashcard.back && <p className="muted">{context.flashcard.back}</p>}
                </>
              )}
            </>
          )}
        </aside>
      )}
      {onRestart && (
        <div className="submit-row">
          <button className="primary-action wide" onClick={onRestart}>
            Take another test
          </button>
        </div>
      )}
    </div>
  )
}
