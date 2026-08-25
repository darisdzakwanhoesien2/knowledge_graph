from typing import List

from fastapi import APIRouter, Depends, HTTPException
from ..models.domain import Concept, ConceptRelation
from core.store import load_json
from core.registry import list_subjects, _graph_subjects


router = APIRouter(prefix="/concepts", tags=["concepts"])


@router.get("", response_model=List[Concept])
async def list_concepts(subject_id: str = "") -> List[Concept]:
    """List concepts, optionally filtered by subject."""
    graph = load_json("data/graphs/merged_graph.json", {})
    concepts = graph.get("nodes", {})
    result = []
    for node_id, node_data in concepts.items():
        node_subjects = node_data.get("metadata", {}).get("subjects", [])
        if subject_id and subject_id not in node_subjects:
            continue
        result.append(Concept(
            id=node_id,
            subject_id=node_subjects[0] if node_subjects else "",
            name=node_data.get("label", node_id),
            definition=node_data.get("definition"),
            neighbors=[
                edge.get("target") if edge.get("source") == node_id else edge.get("source")
                for edge in graph.get("edges", [])
                if edge.get("source") == node_id or edge.get("target") == node_id
            ],
        ))
    return result


@router.get("/{concept_id}", response_model=Concept)
async def get_concept(concept_id: str) -> Concept:
    """Get a concept by ID."""
    from core.store import load_json
    graph = load_json("data/graphs/merged_graph.json", {})
    if concept_id not in graph.get("nodes", {}):
        raise HTTPException(status_code=404, detail=f"Concept {concept_id} not found")
    node_data = graph["nodes"][concept_id]
    node_subjects = node_data.get("metadata", {}).get("subjects", [])
    return Concept(
        id=concept_id,
        subject_id=node_subjects[0] if node_subjects else "",
        name=node_data.get("label", concept_id),
        definition=node_data.get("definition"),
    )


@router.get("/{concept_id}/context")
async def get_concept_context(concept_id: str) -> dict:
    """Remediation context for one concept: definition, neighbors, flashcard.

    Missing links never raise; the payload carries exists=false so standalone
    assessment delivery keeps working (FR-11).
    """
    from core.learning_links import learning_context

    return learning_context(concept_id)


@router.get("/{concept_id}/neighbors", response_model=List[Concept])
async def get_concept_neighbors(concept_id: str) -> List[Concept]:
    """Get neighbor concepts of a given concept."""
    from core.store import load_json
    graph = load_json("data/graphs/merged_graph.json", {})
    neighbors = []
    for edge in graph.get("edges", []):
        if edge.get("source") == concept_id:
            neighbor_id = edge.get("target")
        elif edge.get("target") == concept_id:
            neighbor_id = edge.get("source")
        else:
            continue
        if neighbor_id in graph.get("nodes", {}):
            neighbor_node = graph["nodes"][neighbor_id]
            neighbor_subjects = neighbor_node.get("metadata", {}).get("subjects", [])
            neighbors.append(Concept(
                id=neighbor_id,
                subject_id=neighbor_subjects[0] if neighbor_subjects else "",
                name=neighbor_node.get("label", neighbor_id),
                definition=neighbor_node.get("definition"),
            ))
    return neighbors
