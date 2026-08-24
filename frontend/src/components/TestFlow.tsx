import { useEffect, useMemo, useState } from 'react'
import { fetchPublishedPackages, fetchSubjects, startAssessment, submitAssessment } from '../api'
import type {
  AssessmentStart,
  GradingResult,
  McqQuestion,
  PackageSummary,
  ResponseRecord,
  Subject,
} from '../types'

type Stage = 'catalogue' | 'running' | 'results'

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

function isResponseCorrect(resp: ResponseRecord): boolean {
  return resp.correct === true || (!!resp.max_score && (resp.score || 0) / resp.max_score >= 0.999)
}

function Catalogue({
  onStarted,
}: {
  onStarted: (session: AssessmentStart) => void
}) {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [packages, setPackages] = useState<PackageSummary[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [packageId, setPackageId] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([fetchSubjects(), fetchPublishedPackages()])
      .then(([subjectData, packageData]) => {
        setSubjects(subjectData)
        setPackages(packageData)
        setSubjectId(packageData[0]?.subject || subjectData[0]?.id || '')
        setPackageId(packageData[0]?.package_id || '')
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [])

  const subjectPackages = useMemo(
    () => packages.filter((pkg) => pkg.subject === subjectId),
    [packages, subjectId],
  )
  const activePackage = subjectPackages.find((pkg) => pkg.package_id === packageId)

  function handleSubjectChange(nextSubject: string) {
    setSubjectId(nextSubject)
    const nextPackage = packages.find((pkg) => pkg.subject === nextSubject)
    setPackageId(nextPackage?.package_id || '')
  }

  function handleStart() {
    if (!activePackage || starting) return
    setStarting(true)
    setError('')
    startAssessment(subjectId, activePackage.package_id, displayName)
      .then(onStarted)
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setStarting(false))
  }

  if (loading) return <p className="muted">Loading available tests...</p>

  return (
    <div className="test-layout">
      <aside className="sidebar">
        <label htmlFor="test-subject">Subject</label>
        <select id="test-subject" value={subjectId} onChange={(event) => handleSubjectChange(event.target.value)}>
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              {subject.name}
            </option>
          ))}
        </select>
        <label htmlFor="test-package" className="gap-label">
          Test
        </label>
        <select id="test-package" value={packageId} onChange={(event) => setPackageId(event.target.value)}>
          {subjectPackages.map((pkg) => (
            <option key={pkg.package_key} value={pkg.package_id}>
              {pkg.title} (v{pkg.version})
            </option>
          ))}
        </select>
        <label htmlFor="learner-name" className="gap-label">
          Your name
        </label>
        <input
          id="learner-name"
          placeholder="anonymous"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
        />
        <button className="primary-action" onClick={handleStart} disabled={!activePackage || starting}>
          {starting ? 'Starting...' : 'Start test'}
        </button>
      </aside>
      <div className="content">
        {error && <div className="notice">{error}</div>}
        {!error && !packages.length && (
          <p className="muted">No published tests yet. Curators can publish one from Author Packages.</p>
        )}
        {activePackage && (
          <>
            <div className="content-heading">
              <div>
                <p className="eyebrow">{activePackage.level || 'Assessment'}</p>
                <h2>{activePackage.title}</h2>
              </div>
            </div>
            <p className="muted">{activePackage.description || 'Answer the questions, then submit once.'}</p>
            <div className="metrics">
              <div className="metric">
                <span>Questions</span>
                <strong>{activePackage.mcq_count + activePackage.essay_count}</strong>
              </div>
              <div className="metric">
                <span>MCQs</span>
                <strong>{activePackage.mcq_count}</strong>
              </div>
              <div className="metric">
                <span>Essays</span>
                <strong>{activePackage.essay_count}</strong>
              </div>
              <div className="metric">
                <span>Version</span>
                <strong>v{activePackage.version}</strong>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

type RunnerProps = {
  session: AssessmentStart
  submitting: boolean
  error: string
  onSubmit: (mcq: Record<string, string>, essay: Record<string, string>) => void
  onCancel: () => void
}

function Runner({ session, submitting, error, onSubmit, onCancel }: RunnerProps) {
  const snapshot = session.snapshot
  const mcqs = snapshot.mcqs || []
  const essays = snapshot.essay || []
  const [mcqAnswers, setMcqAnswers] = useState<Record<string, string>>({})
  const [essayAnswers, setEssayAnswers] = useState<Record<string, string>>({})

  const unansweredMcqs = mcqs
    .map((q: McqQuestion, index) => ({ q, index }))
    .filter(({ q }) => !mcqAnswers[q.id])

  function handleSubmit() {
    if (submitting) return
    onSubmit(mcqAnswers, essayAnswers)
  }

  return (
    <div className="runner">
      <div className="content-heading">
        <div>
          <p className="eyebrow">
            {snapshot.title} · v{snapshot.version} · {snapshot.content_hash?.slice(0, 12)}
          </p>
          <h2>Your test</h2>
        </div>
        <button className="link-button" onClick={onCancel} disabled={submitting}>
          Choose another test
        </button>
      </div>
      {error && <div className="notice">{error}</div>}
      {mcqs.length > 0 && <h3 className="section-title">Multiple choice</h3>}
      {mcqs.map((q, index) => (
        <article className="question-card" key={q.id}>
          <p className="question-line">
            <span className="card-index">{String(index + 1).padStart(2, '0')}</span> {q.question}
          </p>
          {q.learning_objective && <p className="muted objective">Objective: {q.learning_objective}</p>}
          <div className="options" role="radiogroup" aria-label={q.question}>
            {Object.keys(q.options)
              .sort()
              .map((key) => (
                <label className={`option-row ${mcqAnswers[q.id] === key ? 'picked' : ''}`} key={key}>
                  <input
                    type="radio"
                    name={q.id}
                    value={key}
                    checked={mcqAnswers[q.id] === key}
                    onChange={() => setMcqAnswers((prev) => ({ ...prev, [q.id]: key }))}
                  />
                  <span className="option-key">{key}</span>
                  <span>{q.options[key]}</span>
                </label>
              ))}
          </div>
        </article>
      ))}
      {essays.length > 0 && <h3 className="section-title">Essays</h3>}
      {essays.map((q, index) => (
        <article className="question-card" key={q.id}>
          <p className="question-line">
            <span className="card-index">{String(mcqs.length + index + 1).padStart(2, '0')}</span>{' '}
            {q.prompt.split('\n')[0]}
          </p>
          {q.learning_objective && <p className="muted objective">Objective: {q.learning_objective}</p>}
          {!!q.rubric?.total_points && <p className="muted objective">Worth up to {q.rubric.total_points} points</p>}
          <textarea
            aria-label={`Essay answer for: ${q.prompt}`}
            placeholder="Write your answer..."
            value={essayAnswers[q.id] || ''}
            onChange={(event) => setEssayAnswers((prev) => ({ ...prev, [q.id]: event.target.value }))}
            rows={5}
          />
        </article>
      ))}
      <div className="submit-row">
        <div className="muted">
          {unansweredMcqs.length > 0
            ? `MCQs not yet answered: ${unansweredMcqs.map(({ index }) => index + 1).join(', ')}`
            : 'All MCQs answered. Submitting grades your test once.'}
        </div>
        <button className="primary-action wide" onClick={handleSubmit} disabled={submitting}>
          {submitting ? 'Submitting...' : 'Submit test'}
        </button>
      </div>
    </div>
  )
}

function Results({ result, onRestart }: { result: GradingResult; onRestart: () => void }) {
  const { scores, responses } = result
  const studySuggestions = Array.from(
    new Set(responses.filter((r) => !isResponseCorrect(r)).flatMap((r) => r.node_links || [])),
  )

  return (
    <div className="runner results">
      <div className="result-banner">
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
                <span className="mark">{correct ? '✓' : '✗'}</span> {title.slice(0, 120)}
              </summary>
              <div className="response-body">
                {resp.question_kind === 'mcq' ? (
                  <p>
                    Your answer: <code>{resp.selected_option || '—'}</code> · Correct:{' '}
                    <code>{resp.correct_option}</code>
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
          <h3 className="section-title">Study suggestions from your misses</h3>
          <ul className="study-list">
            {studySuggestions.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </>
      )}
      <div className="submit-row">
        <button className="primary-action wide" onClick={onRestart}>
          Take another test
        </button>
      </div>
    </div>
  )
}

export default function TestFlow() {
  const [stage, setStage] = useState<Stage>('catalogue')
  const [session, setSession] = useState<AssessmentStart | null>(null)
  const [result, setResult] = useState<GradingResult | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  function handleSubmit(mcq: Record<string, string>, essay: Record<string, string>) {
    if (!session) return
    setSubmitting(true)
    setError('')
    submitAssessment(session.attempt_id, mcq, essay)
      .then((grading) => {
        setResult(grading)
        setStage('results')
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setSubmitting(false))
  }

  function reset() {
    setSession(null)
    setResult(null)
    setError('')
    setStage('catalogue')
  }

  if (stage === 'running' && session) {
    return (
      <Runner
        session={session}
        submitting={submitting}
        error={error}
        onSubmit={handleSubmit}
        onCancel={reset}
      />
    )
  }
  if (stage === 'results' && result) {
    return <Results result={result} onRestart={reset} />
  }
  return (
    <Catalogue
      onStarted={(started) => {
        setSession(started)
        setResult(null)
        setError('')
        setStage('running')
      }}
    />
  )
}
