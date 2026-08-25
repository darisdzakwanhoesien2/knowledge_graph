from __future__ import annotations

from sqlmodel import SQLModel, Field, UniqueConstraint
from typing import Optional
from datetime import datetime


class Subject(SQLModel, table=True):
    """Subject/Discipline."""
    __tablename__ = "subject"
    id: str = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None


class Concept(SQLModel, table=True):
    """Concept/Node in the knowledge graph."""
    __tablename__ = "concept"
    id: str = Field(default=None, primary_key=True)
    subject_id: str = Field(default=None, foreign_key="subject.id", index=True)
    name: str = Field(index=True)
    definition: Optional[str] = None


class ConceptRelation(SQLModel, table=True):
    """Typed directed edge between concepts."""
    __tablename__ = "concept_relation"
    id: str = Field(default=None, primary_key=True)
    source_concept_id: str = Field(default=None, foreign_key="concept.id")
    target_concept_id: str = Field(default=None, foreign_key="concept.id")
    relation_type: str = Field(default=None, index=True)


class PackageVersion(SQLModel, table=True):
    """Immutable version of a question package."""
    __tablename__ = "package_version"
    id: str = Field(default=None, primary_key=True)
    package_id: str = Field(default=None, index=True)
    subject_id: str = Field(default=None, foreign_key="subject.id", index=True)
    version: int = Field(default=None, index=True)
    status: str = Field(default="draft", index=True)  # draft, review, published
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Question(SQLModel, table=True):
    """MCQ or Essay question."""
    __tablename__ = "question"
    id: str = Field(default=None, primary_key=True)
    package_version_id: str = Field(default=None, foreign_key="package_version.id", index=True)
    prompt: str = Field(index=True)
    kind: str = Field(default="mcq", index=True)  # mcq or essay
    difficulty: str = Field(default="medium", index=True)
    learning_objective: Optional[str] = None
    slide_reference: Optional[str] = None
    correct_answer_key: Optional[str] = None  # for mcq: option key like "A"
    essay_keywords: Optional[str] = None  # JSON string
    essay_rubric: Optional[str] = None  # JSON string


class Attempt(SQLModel, table=True):
    """Learner attempt at a package version."""
    __tablename__ = "attempt"
    id: str = Field(default=None, primary_key=True)
    user_id: str = Field(default="anonymous", index=True)
    package_version_id: str = Field(default=None, foreign_key="package_version.id", index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    answers: Optional[str] = None  # JSON string
    mcq_score: int = Field(default=0)
    essay_score: int = Field(default=0)
    total_score: int = Field(default=0)
    max_possible: int = Field(default=0)
    completed: bool = Field(default=False)


class ValidationIssue(SQLModel, table=True):
    """Reported quality issue."""
    __tablename__ = "validation_issue"
    id: str = Field(default=None, primary_key=True)
    type: str = Field(default=None, index=True)  # missing_definition, invalid_reference, etc.
    severity: str = Field(default=None, index=True)  # error, warning
    message: str = Field(index=True)
    location: Optional[str] = None  # e.g., "package.json -> questions[3]"
    entity_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Tag(SQLModel, table=True):
    """Curator-defined grouping (topic, exam, difficulty, ...).

    Open-ended taxonomy: creating a new tag never requires a schema or code
    change. tag_key is the stable slug used in filters and joins.
    """
    __tablename__ = "tag"
    id: str = Field(default=None, primary_key=True)
    tag_key: str = Field(index=True, unique=True)
    label: str = Field(index=True)
    category: str = Field(default="topic", index=True)  # topic, exam, difficulty, ...
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FlashcardTag(SQLModel, table=True):
    """Many-to-many link between a flashcard and a tag.

    flashcard_id holds the stable entity key of the card entry in
    data/flashcards/flashcards.json. It is a plain indexed string rather than a
    foreign key until flashcards themselves migrate into the database.
    """
    __tablename__ = "flashcard_tag"
    __table_args__ = (UniqueConstraint("flashcard_id", "tag_id"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    flashcard_id: str = Field(index=True)
    tag_id: str = Field(default=None, foreign_key="tag.id", index=True)
