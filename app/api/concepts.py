from typing import List

from fastapi import APIRouter, Depends
from ..models.domain import Concept, ConceptRelation

router = APIRouter(prefix="/concepts", tags=["concepts"])


@router.get("", response_model=List[Concept])
async def list_concepts(subject_id: str = "") -> List[Concept]:
    """List concepts, optionally filtered by subject."""
    ...


@router.get("/{concept_id}", response_model=Concept)
async def get_concept(concept_id: str) -> Concept:
    """Get a concept by ID."""
    ...


@router.get("/{concept_id}/neighbors", response_model=List[Concept])
async def get_concept_neighbors(concept_id: str) -> List[Concept]:
    """Get neighbor concepts of a given concept."""
    ...