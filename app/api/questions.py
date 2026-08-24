from fastapi import APIRouter, Depends
from ..models.domain import Question, EssayPrompt

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("/{question_id}", response_model=Question)
async def get_question(question_id: str) -> Question:
    """Get a question by ID."""
    ...


@router.post("", response_model=Question)
async def create_question(question: Question) -> Question:
    """Create a new question."""
    ...


@router.post("/{question_id}", response_model=Question)
async def update_question(question_id: str, question: Question) -> Question:
    """Update a question."""
    ...