from fastapi import APIRouter, Depends, HTTPException
from ..models.domain import Attempt, ResultSummary
from core.attempts import start_attempt, submit_attempt
from core.packages import load_package, list_packages


router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("", response_model=Attempt)
async def start_assessment(attempt: Attempt) -> Attempt:
    """Start a new assessment attempt."""
    # Find the package version
    from core.packages import list_packages, load_package
    packages = list_packages()
    # Find the most recent published version
    pkg_version = None
    for pkg_info in packages:
        pkg = load_package(pkg_info["subject"], pkg_info["package_id"])
        versions = pkg.get("versions", [])
        if versions:
            last_version = max(int(v.get("version", 0)) for v in versions)
            v = [v for v in versions if v.get("version") == str(last_version)]
            if v and v[0].get("status") == "published":
                pkg_version = v[0]
                break
    if not pkg_version:
        raise HTTPException(status_code=404, detail="No published package version found")
    attempt_id = start_attempt(pkg_version)
    return {"id": attempt_id, "user_id": "anonymous", "package_version_id": pkg_version.get("id"), "started_at": None, "completed_at": None, "answers": {}, "mcq_score": 0, "essay_score": 0, "total_score": 0, "max_possible": 0, "completed": False}


@router.post("/{attempt_id}/submit", response_model=ResultSummary)
async def submit_assessment(attempt_id: str, answers: dict) -> ResultSummary:
    """Submit an assessment attempt and get results."""
    result = submit_attempt(attempt_id, answers)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result