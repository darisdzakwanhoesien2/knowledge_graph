from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from ..models.domain import Attempt, ResultSummary
from core.attempts import start_attempt, submit_attempt, list_attempts
from core.packages import load_package, list_packages


router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("", response_model=Attempt)
async def start_assessment(user: dict, subject_id: str, package_id: str) -> Attempt:
    """Start a new assessment attempt."""
    attempt_id = start_attempt(user)
    pkg_version = load_package(subject_id, package_id)
    if not pkg_version or pkg_version.get("status") != "published":
        raise HTTPException(status_code=404, detail="Published package not found")
    started_at = datetime.now(timezone.utc)
    return {"id": attempt_id, "user_id": user.get("external_key", "local_user"),
            "package_version_id": f"{subject_id}/{package_id}/v{pkg_version.get('version', 1)}",
            "started_at": started_at, "completed_at": None,
            "answers": {}, "mcq_score": 0, "essay_score": 0, "total_score": 0,
            "max_possible": 0, "completed": False}


@router.post("/{attempt_id}/submit", response_model=ResultSummary)
async def submit_assessment(attempt_id: str, answers_mcq: dict, answers_essay: dict) -> ResultSummary:
    """Submit an assessment attempt and get results.

    answers_mcq: {question_id: selected_option_letter}
    answers_essay: {question_id: essay_text}
    """
    # Find the attempt and its associated package snapshot
    attempts = list_attempts()
    match = [a for a in attempts if a["attempt_id"] == attempt_id]
    if not match:
        raise HTTPException(status_code=404, detail=f"Attempt {attempt_id} not found")

    # Load the attempt to get the package info
    # We need to find the package snapshot - look through all packages
    # For now, use the first published package we can find
    packages = list_packages()
    pkg_snapshot = None
    for pkg_info in packages:
        pkg = load_package(pkg_info["subject"], pkg_info["package_id"])
        versions = pkg.get("versions", [])
        if versions:
            last_version = max(int(v.get("version", 0)) for v in versions)
            v = [v for v in versions if str(v.get("version")) == str(last_version)]
            if v and v[0].get("status") == "published":
                pkg_snapshot = v[0]
                break
    if not pkg_snapshot:
        raise HTTPException(status_code=404, detail="No published package version found for submission")
    # Submit the attempt
    result = submit_attempt(
        user={"external_key": "local_user", "display_name": "local_user"},
        pkg_snapshot=pkg_snapshot,
        answers_mcq=answers_mcq or {},
        answers_essay=answers_essay or {},
    )
    return {
        "attempt_id": result["attempt_id"],
        "package_version_id": result.get("package_key", ""),
        "subject_id": result.get("subject", ""),
        "mcq_score": result["scores"]["mcq_score"],
        "essay_score": result["scores"]["essay_score"],
        "total_score": result["scores"]["mcq_score"] + result["scores"]["essay_score"],
        "max_possible": result["scores"]["mcq_max"] + result["scores"]["essay_max"],
        "percentage": result["scores"]["final_score"] * 100,
        "answered_at": result.get("submitted_at"),
        "incorrectly_missed": [],  # would need to compute from responses
        "related_concepts": [],  # would need graph traversal
    }
