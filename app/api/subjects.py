from fastapi import APIRouter, Depends
from typing import List
from ..models.domain import Subject, Provenance

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=List[Subject])
async def list_subjects() -> List[Subject]:
    """List all subjects in the knowledge graph."""
    ...


@router.get("/{subject_id}", response_model=Subject)
async def get_subject(subject_id: str) -> Subject:
    """Get a subject by ID."""
    ...