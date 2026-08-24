from fastapi import APIRouter, Depends, HTTPException
from ..models.domain import ValidationIssue, ValidationReport
from core.packages import validate_package, list_packages, load_package
from core.registry import list_subjects


router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("", response_model=ValidationReport)
async def validate_content(
    subject_id: str,
    package_version_id: str,
) -> ValidationReport:
    """Validate a package version and report issues."""
    from core.packages import load_package
    # Find the package
    packages = list_packages()
    pkg_info = None
    for p in packages:
        if p["subject"] == subject_id and p["package_id"] == (package_version_id.split("/")[-1] if "/" in package_version_id else package_version_id):
            pkg_info = p
            break
    if not pkg_info:
        raise HTTPException(status_code=404, detail=f"Package {package_version_id} not found")
    pkg = load_package(pkg_info["subject"], pkg_info["package_id"])
    issues = validate_package(pkg)
    return {"issues": issues, "clean": len([i for i in issues if i["severity"] == "error"]) == 0}