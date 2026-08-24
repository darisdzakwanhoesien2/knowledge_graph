from fastapi import APIRouter, Depends
from ..models.domain import ValidationIssue, ValidationReport

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("", response_model=ValidationReport)
async def validate_content(
    subject_id: str,
    package_version_id: str,
) -> ValidationReport:
    """Validate a package version and report issues."""
    ...