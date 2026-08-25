from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..models.domain import PackageSummary
from ..security import require_curator
from core import packages as P
from core.packages import (
    list_packages as core_list_packages,
    load_package,
    load_published_version,
)
from core.registry import list_subjects as core_list_subjects


router = APIRouter(prefix="/packages", tags=["packages"])


class PackageCreate(BaseModel):
    subject: str
    title: str = Field(min_length=1)
    level: str = ""
    description: str = ""


def _summary(subject: str, package_id: str) -> PackageSummary:
    pkg = load_package(subject, package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    return PackageSummary(
        package_key=pkg.get("package_key", f"{subject}/{package_id}"),
        subject=pkg.get("subject", subject),
        package_id=pkg.get("package_id", package_id),
        title=pkg.get("title", package_id),
        level=pkg.get("level") or None,
        description=pkg.get("description") or None,
        status=pkg.get("status", "draft"),
        version=int(pkg.get("version") or 1),
        published_at=pkg.get("published_at"),
        mcq_count=len(pkg.get("mcqs", [])),
        essay_count=len(pkg.get("essay", [])),
    )


@router.get("", response_model=List[PackageSummary])
async def list_packages(status: str = "") -> List[PackageSummary]:
    """List packages, optionally filtered by status (draft/review/published)."""
    summaries = [_summary(entry["subject"], entry["package_id"]) for entry in core_list_packages()]
    if status:
        summaries = [s for s in summaries if s.status == status]
    return summaries


@router.post("", dependencies=[Depends(require_curator)])
async def create_package(payload: PackageCreate):
    """Create a new draft package under an existing registry subject."""
    subject = (payload.subject or "").strip()
    if subject not in core_list_subjects():
        raise HTTPException(
            status_code=422,
            detail=f"Unknown subject '{subject}'; add graph content and rebuild the registry first",
        )
    pkg = P.new_package(subject, payload.title.strip(), level=payload.level,
                        description=payload.description)
    if P.package_path(subject, pkg["package_id"]).exists():
        raise HTTPException(status_code=409, detail=f"Package '{pkg['package_id']}' already exists")
    P.save_package(pkg)
    return {
        "package_key": pkg["package_key"],
        "package_id": pkg["package_id"],
        "subject": pkg["subject"],
        "title": pkg["title"],
        "status": pkg["status"],
        "version": pkg["version"],
    }


def _locate(package_id: str):
    found = [entry for entry in core_list_packages() if entry["package_id"] == package_id]
    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Package {package_id} not found; create it first via POST /packages",
        )
    return found[0]["subject"], package_id


FULL_PACKAGE_MARKERS = ("schema_version", "package_key", "subject", "title", "created_at", "status")


def _normalize_into(pkg: dict, payload: dict, replace_content: bool) -> None:
    """Merge uploaded question content into the draft; server owns identity fields."""
    if replace_content:
        pkg["mcqs"], pkg["essay"] = [], []
        for field in ("title", "level", "description"):
            value = payload.get(field)
            if isinstance(value, str) and value.strip():
                pkg[field] = value.strip()
    for q in payload.get("mcqs") or []:
        if not isinstance(q, dict):
            raise HTTPException(status_code=422, detail="mcqs entries must be objects")
        P.add_mcq(
            pkg,
            question=q.get("question", ""),
            options=q.get("options") or {},
            correct_option=q.get("correct_option", ""),
            difficulty=q.get("difficulty", "medium"),
            learning_objective=q.get("learning_objective", ""),
            slide_refs=q.get("slide_refs"),
            node_links=q.get("node_links"),
        )
    for q in payload.get("essay") or []:
        if not isinstance(q, dict):
            raise HTTPException(status_code=422, detail="essay entries must be objects")
        rubric = q.get("rubric") or {}
        P.add_essay(
            pkg,
            prompt=q.get("prompt", ""),
            expected_keywords=q.get("expected_keywords"),
            criteria=rubric.get("criteria"),
            total_points=rubric.get("total_points", 0),
            grading_notes=rubric.get("grading_notes", ""),
            difficulty=q.get("difficulty", "medium"),
            learning_objective=q.get("learning_objective", ""),
            slide_refs=q.get("slide_refs"),
            node_links=q.get("node_links"),
        )


@router.post("/{package_id}/content", dependencies=[Depends(require_curator)])
async def upload_package_content(package_id: str, payload: dict):
    """Upload a full package.json or a partial {mcqs, essay} into the target draft.

    Validation errors block the write entirely (fail closed); warnings are
    returned without blocking. A published package is never mutated — uploading
    into one auto-starts the next draft version. `package_key` is always
    recomputed server-side and never trusted from the file.
    """
    subject, package_id = _locate(package_id)
    pkg = load_package(subject, package_id)

    is_full = any(marker in payload for marker in FULL_PACKAGE_MARKERS)
    has_questions = isinstance(payload.get("mcqs"), list) or isinstance(payload.get("essay"), list)
    if not is_full and not has_questions:
        raise HTTPException(
            status_code=422,
            detail="Payload must be a full package.json or contain mcqs[]/essay[] lists",
        )

    if pkg.get("status") == "published":
        # Editing a published package auto-starts the next draft, same as the UI.
        pkg = P.start_next_draft(subject, package_id)

    _normalize_into(pkg, payload, replace_content=is_full)

    # Server-side identity: an upload can never spoof another package's key.
    pkg["subject"] = subject
    pkg["package_id"] = package_id
    pkg["package_key"] = f"{subject}/{package_id}"

    issues = P.validate_package(pkg)
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    if errors:
        # Fail closed before any write touches the draft on disk.
        raise HTTPException(status_code=422, detail={"errors": errors, "warnings": warnings})

    P.save_package(pkg)
    return {
        "status": "updated",
        "package_key": pkg["package_key"],
        "version": int(pkg.get("version") or 1),
        "mcq_count": len(pkg.get("mcqs", [])),
        "essay_count": len(pkg.get("essay", [])),
        "errors": [],
        "warnings": warnings,
    }


@router.post("/{package_id}/publish", dependencies=[Depends(require_curator)])
async def publish_package(package_id: str):
    """Publish the current draft as an immutable version snapshot."""
    subject, package_id = _locate(package_id)
    try:
        snapshot = P.publish_package(subject, package_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return snapshot


@router.get("/{package_id}", response_model=PackageSummary)
async def get_package(package_id: str) -> PackageSummary:
    """Get a package summary by ID."""
    found = [entry for entry in core_list_packages() if entry["package_id"] == package_id]
    if not found:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    return _summary(found[0]["subject"], found[0]["package_id"])


@router.get("/{package_id}/versions")
async def list_package_versions(package_id: str) -> List[dict]:
    """List all immutable published versions of a package."""
    found = [entry for entry in core_list_packages() if entry["package_id"] == package_id]
    if not found:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    subject = found[0]["subject"]

    from pathlib import Path

    versions_path = Path(P.package_dir(subject, package_id)) / P.VERSIONS_DIR
    versions = []
    if versions_path.exists():
        for f in sorted(versions_path.glob("v*.json")):
            snapshot = load_published_version(subject, package_id, int(f.stem[1:]))
            if snapshot:
                versions.append(snapshot)
    return versions


@router.get("/{package_id}/versions/{version_id}")
async def get_package_version(package_id: str, version_id: str) -> dict:
    """Get one immutable published version snapshot."""
    found = [entry for entry in core_list_packages() if entry["package_id"] == package_id]
    if not found:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    snapshot = load_published_version(found[0]["subject"], package_id, int(version_id))
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
    return snapshot
