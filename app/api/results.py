from typing import List

from fastapi import APIRouter, HTTPException

from ..models.domain import ResultSummary
from core.attempts import list_attempts, load_attempt


router = APIRouter(prefix="/results", tags=["results"])


def _summary(rec: dict) -> ResultSummary:
    scores = rec.get("scores", {})
    responses = rec.get("responses", [])
    missed_ids = [r.get("question_id") for r in responses
                  if not (r.get("correct") is True
                          or (r.get("max_score") and (r.get("score") or 0) / r["max_score"] >= 0.999))]
    related = []
    for r in responses:
        if r.get("correct") is True:
            continue
        related.extend(r.get("node_links", []))
    return ResultSummary(
        attempt_id=rec["attempt_id"],
        package_version_id=f"{rec.get('subject')}/{rec.get('package_id')}/v{rec.get('package_version')}",
        subject_id=rec.get("subject") or "",
        mcq_score=scores.get("mcq_score", 0),
        essay_score=scores.get("essay_score", 0),
        total_score=scores.get("mcq_score", 0) + scores.get("essay_score", 0),
        max_possible=scores.get("mcq_max", 0) + scores.get("essay_max", 0),
        percentage=(scores.get("final_score") or 0) * 100,
        answered_at=rec.get("submitted_at"),
        incorrectly_missed=missed_ids,
        related_concepts=list(dict.fromkeys(related)),
    )


@router.get("", response_model=List[ResultSummary])
async def list_results(
    subject_id: str = "",
    package_version_id: str = "",
) -> List[ResultSummary]:
    """List submitted attempt summaries, newest first, optionally filtered."""
    out = []
    for entry in list_attempts():
        rec = load_attempt(entry["attempt_id"])
        if not rec:
            continue
        summary = _summary(rec)
        if subject_id and summary.subject_id != subject_id:
            continue
        if package_version_id and summary.package_version_id != package_version_id:
            continue
        out.append(summary)
    return out


@router.get("/{attempt_id}")
async def get_attempt_results(attempt_id: str) -> dict:
    """Get full transparent grading results for one attempt."""
    rec = load_attempt(attempt_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Attempt {attempt_id} not found")
    return rec
