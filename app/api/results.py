from typing import List

from fastapi import APIRouter, Depends
from ..models.domain import ResultSummary, ValidationIssue

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/{attempt_id}", response_model=ResultSummary)
async def get_attempt_results(attempt_id: str) -> ResultSummary:
    """Get results for a specific attempt."""
    ...


@router.get("", response_model=List[ResultSummary])
async def list_results(
    subject_id: str = "",
    package_version_id: str = "",
) -> List[ResultSummary]:
    """List results, optionally filtered."""
    ...