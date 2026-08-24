from fastapi import APIRouter, Depends
from ..models.domain import Attempt, ResultSummary

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("", response_model=Attempt)
async def start_assessment(attempt: Attempt) -> Attempt:
    """Start a new assessment attempt."""
    ...


@router.post("/{attempt_id}/submit", response_model=ResultSummary)
async def submit_assessment(attempt_id: str, answers: dict) -> ResultSummary:
    """Submit an assessment attempt and get results."""
    ...