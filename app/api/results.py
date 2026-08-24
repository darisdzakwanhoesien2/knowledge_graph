from typing import List

from fastapi import APIRouter, Depends, HTTPException
from ..models.domain import ResultSummary, ValidationIssue
from core.attempts import start_attempt, submit_attempt, list_attempts, compute_scores
from core.grading import grade_mcq, grade_essay, compute_scores as compute_grades
from core.packages import load_package, list_packages


router = APIRouter(prefix="/results", tags=["results"])


@router.get("/{attempt_id}", response_model=ResultSummary)
async def get_attempt_results(attempt_id: str) -> ResultSummary:
    """Get results for a specific attempt."""
    attempts = list_attempts()
    match = [a for a in attempts if a["attempt_id"] == attempt_id]
    if not match:
        raise HTTPException(status_code=404, detail=f"Attempt {attempt_id} not found")
    return match[0]


@router.get("", response_model=List[ResultSummary])
async def list_results(
    subject_id: str = "",
    package_version_id: str = "",
) -> List[ResultSummary]:
    """List results, optionally filtered."""
    attempts = list_attempts()
    # Apply filters
    if subject_id:
        attempts = [a for a in attempts if a.get("subject_id") == subject_id]
    if package_version_id:
        attempts = [a for a in attempts if a.get("package_version_id") == package_version_id]
    return attempts