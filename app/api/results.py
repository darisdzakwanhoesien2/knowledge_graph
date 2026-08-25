from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..models.domain import ResultSummary
from core.attempts import attempts_csv, list_attempts, load_attempt


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
    user = rec.get("user", {})
    return ResultSummary(
        attempt_id=rec["attempt_id"],
        package_version_id=f"{rec.get('subject')}/{rec.get('package_id')}/v{rec.get('package_version')}",
        subject_id=rec.get("subject") or "",
        learner=user.get("display_name") or user.get("external_key"),
        mcq_score=scores.get("mcq_score", 0),
        essay_score=scores.get("essay_score", 0),
        total_score=scores.get("mcq_score", 0) + scores.get("essay_score", 0),
        max_possible=scores.get("mcq_max", 0) + scores.get("essay_max", 0),
        percentage=(scores.get("final_score") or 0) * 100,
        answered_at=rec.get("submitted_at"),
        incorrectly_missed=missed_ids,
        related_concepts=list(dict.fromkeys(related)),
    )


def _load_records(
    subject_id: str,
    package_version_id: str,
    learner: str,
    submitted_after: Optional[date],
    submitted_before: Optional[date],
):
    """Load full attempt records matching the review filters (newest first)."""
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
        if learner and (summary.learner or "").lower() != learner.lower():
            continue
        if submitted_after and summary.answered_at.date() < submitted_after:
            continue
        if submitted_before and summary.answered_at.date() > submitted_before:
            continue
        out.append((rec, summary))
    return out


@router.get("", response_model=List[ResultSummary])
async def list_results(
    subject_id: str = "",
    package_version_id: str = "",
    learner: str = "",
    submitted_after: Optional[date] = None,
    submitted_before: Optional[date] = None,
    limit: int = 0,
) -> List[ResultSummary]:
    """List submitted attempt summaries, newest first, optionally filtered."""
    summaries = [summary for _, summary in _load_records(
        subject_id, package_version_id, learner, submitted_after, submitted_before)]
    if limit > 0:
        summaries = summaries[:limit]
    return summaries


@router.get("/export/csv")
async def export_results_csv(
    subject_id: str = "",
    package_version_id: str = "",
    learner: str = "",
    submitted_after: Optional[date] = None,
    submitted_before: Optional[date] = None,
) -> PlainTextResponse:
    """Export filtered submissions as one row per response for spreadsheet review."""
    records = [rec for rec, _ in _load_records(
        subject_id, package_version_id, learner, submitted_after, submitted_before)]
    csv_text = attempts_csv(attempts=[{"attempt_id": rec["attempt_id"]} for rec in records])
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="results.csv"'},
    )


@router.get("/{attempt_id}")
async def get_attempt_results(attempt_id: str) -> dict:
    """Get full transparent grading results for one attempt."""
    rec = load_attempt(attempt_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Attempt {attempt_id} not found")
    return rec
