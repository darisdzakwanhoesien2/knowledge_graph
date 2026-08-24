from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..models.domain import AssessmentStart
from core.attempts import start_attempt, submit_attempt
from core.packages import load_package, load_published_version
from core.store import RESULTS_DIR, load_json, write_json


router = APIRouter(prefix="/assessments", tags=["assessments"])

PENDING_DIR = RESULTS_DIR / "pending"


def _published_snapshot(subject_id: str, package_id: str) -> dict:
    pkg = load_package(subject_id, package_id)
    if not pkg or pkg.get("status") != "published":
        raise HTTPException(status_code=404, detail="Published package not found")
    version = int(pkg.get("version") or 1)
    snapshot = load_published_version(subject_id, package_id, version)
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"Published snapshot v{version} is missing for {subject_id}/{package_id}",
        )
    return snapshot


@router.post("", response_model=AssessmentStart)
async def start_assessment(user: dict, subject_id: str, package_id: str) -> AssessmentStart:
    """Start a new assessment attempt against the current published version."""
    snapshot = _published_snapshot(subject_id, package_id)
    attempt_id = start_attempt(user)
    started_at = datetime.now(timezone.utc)
    # Persist the pending attempt so submission grades against exactly this
    # package version (FR-12), even if a newer version is published meanwhile.
    write_json(PENDING_DIR / f"{attempt_id}.json", {
        "attempt_id": attempt_id,
        "user": {"external_key": user.get("external_key", "local_user"),
                 "display_name": user.get("display_name", "")},
        "subject_id": subject_id,
        "package_id": package_id,
        "version": int(snapshot.get("version") or 1),
        "content_hash": snapshot.get("content_hash", ""),
        "started_at": started_at.isoformat(),
    })
    return AssessmentStart(
        attempt_id=attempt_id,
        user_id=user.get("external_key", "local_user"),
        subject_id=subject_id,
        package_id=package_id,
        package_version=int(snapshot.get("version") or 1),
        content_hash=snapshot.get("content_hash", ""),
        started_at=started_at,
        snapshot=snapshot,
    )


@router.post("/{attempt_id}/submit")
async def submit_assessment(attempt_id: str, answers_mcq: dict, answers_essay: dict) -> Dict[str, Any]:
    """Submit an assessment attempt and get transparent grading results.

    answers_mcq: {question_id: selected_option_letter}
    answers_essay: {question_id: essay_text}
    """
    pending = load_json(PENDING_DIR / f"{attempt_id}.json")
    if not pending:
        raise HTTPException(status_code=404, detail=f"Attempt {attempt_id} not found")

    subject_id = pending["subject_id"]
    package_id = pending["package_id"]
    version = int(pending.get("version") or 1)
    snapshot = load_published_version(subject_id, package_id, version)
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"Package snapshot v{version} for {attempt_id} is missing",
        )

    record = submit_attempt(
        user=pending.get("user", {}),
        pkg_snapshot=snapshot,
        answers_mcq=answers_mcq or {},
        answers_essay=answers_essay or {},
        started_at=pending.get("started_at"),
        attempt_id=attempt_id,
    )
    (PENDING_DIR / f"{attempt_id}.json").unlink(missing_ok=True)
    return record
