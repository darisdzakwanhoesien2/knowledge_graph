export type Subject = { id: string; name: string }

export type Concept = {
  id: string
  subject_id: string
  name: string
  definition?: string
}

export type PackageSummary = {
  package_key: string
  subject: string
  package_id: string
  title: string
  level?: string | null
  description?: string | null
  status: string
  version: number
  published_at?: string | null
  mcq_count: number
  essay_count: number
}

export type McqQuestion = {
  id: string
  question: string
  options: Record<string, string>
  learning_objective?: string
}

export type EssayQuestion = {
  id: string
  prompt: string
  learning_objective?: string
  rubric?: { total_points?: number }
}

export type Snapshot = {
  title?: string
  level?: string
  version: number
  content_hash?: string
  mcqs?: McqQuestion[]
  essay?: EssayQuestion[]
}

export type AssessmentStart = {
  attempt_id: string
  user_id: string
  subject_id: string
  package_id: string
  package_version: number
  content_hash: string
  started_at: string
  snapshot: Snapshot
}

export type RubricCriterion = {
  keyword: string
  matched: boolean
  weight?: number
  evidence?: string
}

export type ResponseRecord = {
  question_kind: 'mcq' | 'essay'
  question_id: string
  question?: string
  prompt?: string
  selected_option?: string
  correct_option?: string
  correct?: boolean
  essay_text?: string
  matched_keywords?: string[]
  matched_criteria?: RubricCriterion[]
  grading_notes?: string
  score?: number
  max_score?: number
  node_links?: string[]
}

export type Scores = {
  mcq_score: number
  mcq_max: number
  mcq_pct: number | null
  essay_score: number
  essay_max: number
  essay_pct: number | null
  final_score: number
}

export type GradingResult = {
  attempt_id: string
  submitted_at: string
  scores: Scores
  responses: ResponseRecord[]
}
