from typing import List

from fastapi import APIRouter, Depends
from ..models.domain import Package, PackageVersion, Question

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_model=List[Package])
async def list_packages(subject_id: str = "") -> List[Package]:
    """List packages, optionally filtered by subject."""
    ...


@router.get("/{package_id}", response_model=Package)
async def get_package(package_id: str) -> Package:
    """Get a package by ID."""
    ...


@router.get("/{package_id}/versions", response_model=List[PackageVersion])
async def list_package_versions(package_id: str) -> List[PackageVersion]:
    """List all versions of a package."""
    ...


@router.get("/{package_id}/versions/{version_id}", response_model=PackageVersion)
async def get_package_version(package_id: str, version_id: str) -> PackageVersion:
    """Get a specific package version."""
    ...