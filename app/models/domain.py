from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class SourceType(str, Enum):
    PDF = "pdf"
    JSON = "json"
    NOTES = "notes"


class Provenance(BaseModel):
    source_type: SourceType
    source_id: str
    file_path: str
    extracted_at: datetime
    notes: Optional[str] = None


class Subject(BaseModel):
    id: str
    name: str
    description: Optional[str] = None


class Concept(BaseModel):
    id: str
    subject_id: str
    name: str
    definition: Optional[str] = None
    provenance: Optional[Provenance] = None
    neighbors: List[str] = Field(default_factory=list)


class PackageSummary(BaseModel):
    package_key: str
    subject: str
    package_id: str
    title: str
    level: Optional[str] = None
    description: Optional[str] = None
    status: str
    version: int
    published_at: Optional[datetime] = None
    mcq_count: int = 0
    essay_count: int = 0


class AssessmentStart(BaseModel):
    attempt_id: str
    user_id: str
    subject_id: str
    package_id: str
    package_version: int
    content_hash: str
    started_at: datetime
    snapshot: Dict[str, Any]


class ConceptRelation(BaseModel):
    source_concept_id: str
    target_concept_id: str
    relation_type: str


class Flashcard(BaseModel):
    id: str
    subject_id: str
    concept_id: Optional[str] = None
    question: str
    answer: str
    difficulty: Difficulty = Difficulty.MEDIUM


class MCQOption(BaseModel):
    key: str
    text: str
    is_correct: bool = False


class Question(BaseModel):
    id: str
    subject_id: str
    package_version_id: str
    prompt: str
    options: Optional[List[MCQOption]] = Field(default=None)
    correct_answer_key: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    learning_objective: Optional[str] = None
    slide_reference: Optional[str] = None
    provenance: Provenance
    essay_kwargs: Optional[Dict[str, Any]] = Field(default=None)


class EssayPrompt(BaseModel):
    id: str
    subject_id: str
    package_version_id: str
    prompt: str
    keywords: List[str] = Field(default_factory=list)
    rubric_criteria: List[str] = Field(default_factory=list)
    weights: List[float] = Field(default_factory=list)
    learning_objective: Optional[str] = None


class PackageVersion(BaseModel):
    id: str
    package_id: str
    subject_id: str
    version: int
    status: str  # "draft", "review", "published"
    questions: List[Question] = Field(default_factory=list)
    essay_prompts: List[EssayPrompt] = Field(default_factory=list)
    created_at: datetime
    created_by: Optional[str] = None


class Package(BaseModel):
    id: str
    subject_id: str
    package_id: str
    versions: List[PackageVersion] = Field(default_factory=list)


class Attempt(BaseModel):
    id: str
    user_id: str  # could be anonymous session ID
    package_version_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    answers: Dict[str, str] = Field(default_factory=dict)  # question_key -> selected_option_or_answer
    mcq_score: int = 0
    essay_score: int = 0
    total_score: int = 0
    max_possible: int = 0
    completed: bool = False


class ResultSummary(BaseModel):
    attempt_id: str
    package_version_id: str
    subject_id: str
    learner: Optional[str] = None
    mcq_score: int
    essay_score: int
    total_score: int
    max_possible: int
    percentage: float
    answered_at: datetime
    incorrectly_missed: List[str] = Field(default_factory=list)
    related_concepts: List[str] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    id: str
    type: str  # "missing_definition", "invalid_reference", "malformed_question", etc.
    severity: str  # "error", "warning"
    message: str
    location: Optional[str] = None  # e.g., "package.json -> questions[3]"
    entity_id: Optional[str] = None


class GraphNode(BaseModel):
    id: str
    label: str
    concept_id: Optional[str] = None
    subject_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    relation_type: str
    provenance: Optional[Provenance] = None


class SearchResult(BaseModel):
    results: List[GraphNode]
    total: int


class PackageImportRequest(BaseModel):
    subject_id: str
    package_id: str
    package_json: dict


class IngestPDFRequest(BaseModel):
    subject_id: str
    file_path: str


class ValidationReport(BaseModel):
    issues: List[ValidationIssue]
    clean: bool
