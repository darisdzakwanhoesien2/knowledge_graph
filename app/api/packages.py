from typing import List

from fastapi import APIRouter, HTTPException

from ..models.domain import PackageSummary
from core.packages import (
    list_packages as core_list_packages,
    load_package,
    load_published_version,
)


router = APIRouter(prefix="/packages", tags=["packages"])


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

    from core.store import DATABASE_DIR

    versions_path = Path(DATABASE_DIR) / subject / package_id / "versions"
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
