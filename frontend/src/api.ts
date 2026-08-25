import type {
  AssessmentStart,
  Concept,
  ConceptContext,
  Flashcard,
  GradingResult,
  PackageSummary,
  ResultSummaryRow,
  Subject,
  Tag,
} from './types'

const API_URL = import.meta.env.VITE_API_URL || 'http://43.157.212.74:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, init)
  } catch {
    throw new Error('Unable to reach the API')
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const payload = await response.json()
      if (typeof payload?.detail === 'string') detail = payload.detail
    } catch {
      // non-JSON error body: keep the status-based message
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

function jsonInit(method: string, body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

export function fetchSubjects(): Promise<Subject[]> {
  return request<Subject[]>('/subjects')
}

export function fetchConcepts(subjectId: string): Promise<Concept[]> {
  return request<Concept[]>(`/concepts?subject_id=${encodeURIComponent(subjectId)}`)
}

export function fetchPublishedPackages(): Promise<PackageSummary[]> {
  return request<PackageSummary[]>('/packages?status=published')
}

export function startAssessment(
  subjectId: string,
  packageId: string,
  displayName: string,
): Promise<AssessmentStart> {
  const user = { external_key: 'local_user', display_name: displayName || 'anonymous' }
  return request<AssessmentStart>(
    `/assessments?subject_id=${encodeURIComponent(subjectId)}&package_id=${encodeURIComponent(packageId)}`,
    jsonInit('POST', user),
  )
}

export function submitAssessment(
  attemptId: string,
  answersMcq: Record<string, string>,
  answersEssay: Record<string, string>,
): Promise<GradingResult> {
  return request<GradingResult>(
    `/assessments/${encodeURIComponent(attemptId)}/submit`,
    jsonInit('POST', { answers_mcq: answersMcq, answers_essay: answersEssay }),
  )
}

export function fetchResult(attemptId: string): Promise<GradingResult> {
  return request<GradingResult>(`/results/${encodeURIComponent(attemptId)}`)
}

export function fetchResults(): Promise<ResultSummaryRow[]> {
  return request<ResultSummaryRow[]>('/results')
}

export function fetchConceptContext(conceptId: string): Promise<ConceptContext> {
  return request<ConceptContext>(`/concepts/${encodeURIComponent(conceptId)}/context`)
}

export function fetchTags(): Promise<Tag[]> {
  return request<Tag[]>('/tags')
}

export function createTag(label: string, category: string): Promise<Tag> {
  return request<Tag>('/tags', jsonInit('POST', { label, category }))
}

export type FlashcardFilters = {
  subjectId?: string
  q?: string
  tags?: string[]
  untagged?: boolean
}

export function fetchFlashcards(filters: FlashcardFilters = {}): Promise<Flashcard[]> {
  const params = new URLSearchParams()
  if (filters.subjectId) params.set('subject_id', filters.subjectId)
  if (filters.q) params.set('q', filters.q)
  if (filters.tags?.length) params.set('tags', filters.tags.join(','))
  if (filters.untagged) params.set('untagged', 'true')
  return request<Flashcard[]>(`/flashcards?${params.toString()}`)
}

export function attachTag(flashcardId: string, tagId: string): Promise<Flashcard> {
  return request<Flashcard>(
    `/flashcards/${encodeURIComponent(flashcardId)}/tags`,
    jsonInit('POST', { tag_id: tagId }),
  )
}

export function detachTag(flashcardId: string, tagId: string): Promise<Flashcard> {
  return request<Flashcard>(
    `/flashcards/${encodeURIComponent(flashcardId)}/tags/${encodeURIComponent(tagId)}`,
    { method: 'DELETE' },
  )
}
