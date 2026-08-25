import { useCallback, useEffect, useState } from 'react'
import { fetchResult, fetchResults } from '../api'
import type { GradingResult, ResultSummaryRow } from '../types'
import ResultsView from './ResultsView'

function formatDate(value?: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

export default function HistoryView() {
  const [rows, setRows] = useState<ResultSummaryRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [detail, setDetail] = useState<GradingResult | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const loadHistory = useCallback(() => {
    setLoading(true)
    setError('')
    fetchResults()
      .then(setRows)
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  function openAttempt(attemptId: string) {
    setDetailLoading(true)
    setError('')
    fetchResult(attemptId)
      .then(setDetail)
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setDetailLoading(false))
  }

  if (detail) {
    return (
      <ResultsView
        result={detail}
        onBack={() => {
          setDetail(null)
          loadHistory()
        }}
      />
    )
  }

  return (
    <div className="history">
      <div className="content-heading">
        <div>
          <p className="eyebrow">Assessment history</p>
          <h2>Submitted tests</h2>
        </div>
        <button className="link-button" onClick={loadHistory} disabled={loading}>
          Refresh
        </button>
      </div>
      {error && <div className="notice">{error}</div>}
      {loading && <p className="muted">Loading your results...</p>}
      {!loading && !rows.length && !error && (
        <p className="muted">No submitted tests yet. Take a test to see it here.</p>
      )}
      {!loading && rows.length > 0 && (
        <ul className="history-list">
          {rows.map((row) => (
            <li key={row.attempt_id}>
              <button
                className="history-row"
                onClick={() => openAttempt(row.attempt_id)}
                disabled={detailLoading}
              >
                <span className="score-pill">{Math.round(row.percentage)}%</span>
                <span className="row-main">
                  <strong>{row.package_version_id}</strong>
                  <small>
                    {formatDate(row.answered_at)} · by {row.learner || 'anonymous'} ·{' '}
                    {row.total_score}/{row.max_possible} points
                  </small>
                </span>
                <span className="row-meta">
                  {row.related_concepts.length > 0 && `${row.related_concepts.length} concept(s) to review`}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
