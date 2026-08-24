from typing import List

from fastapi import APIRouter, Depends
from ..models.domain import Package, PackageVersion, Question
from core.packages import list_packages as core_list_packages, load_package, \
    new_package, save_package, publish_package, start_next_draft, add_mcq, add_essay, validate_package

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_model=List[Package])
async def list_packages(subject_id: str = "") -> List[Package]:
    """List packages, optionally filtered by subject."""
    return core_list_packages()


@router.get("/{package_id}", response_model=Package)
async def get_package(package_id: str) -> Package:
    """Get a package by ID."""
    found = core_list_packages()
    match = [p for p in found if p["package_id"] == package_id]
    if not match:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    return match[0]


@router.get("/{package_id}/versions", response_model=List[PackageVersion])
async def list_package_versions(package_id: str) -> List[PackageVersion]:
    """List all versions of a package."""
    found = core_list_packages()
    match = [p for p in found if p["package_id"] == package_id]
    if not match:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    pkg = match[0]
    return load_package(pkg["subject"], pkg["package_id"])


@router.get("/{package_id}/versions/{version_id}", response_model=PackageVersion)
async def get_package_version(package_id: str, version_id: str) -> PackageVersion:
    """Get a specific package version."""
    found = core_list_packages()
    match = [p for p in found if p["package_id"] == package_id]
    if not match:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    pkg = load_package(pkg["subject"], pkg["package_id"])
    versions = pkg.get("versions", [])
    v_match = [v for v in versions if str(v.get("version")) == version_id]
    if not v_match:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
    return v_match[0]