from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models.domain import Subject
from core.registry import list_subjects as core_list_subjects

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=List[Subject])
async def list_subjects() -> List[Subject]:
    """List all subjects in the knowledge graph."""
    return [
        Subject(id=sid, name=sid.replace("_", " ").title())
        for sid in core_list_subjects()
    ]


@router.get("/{subject_id}", response_model=Subject)
async def get_subject(subject_id: str) -> Subject:
    """Get a subject by ID."""
    subjects = core_list_subjects()
    match = [s for s in subjects if s == subject_id]
    if not match:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found")
    return Subject(id=match[0], name=match[0].replace("_", " ").title())