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
    subjects_meta = _graph_subjects()
    concepts = graph.get("nodes", {})
    result = []
    for node_id, node_data in concepts.items():
        if subject_id and subjects_meta.get(node_id, {}).get("subject_id") != subject_id:
            continue
        result.append(Concept(
            id=node_id,
            subject_id=subjects_meta.get(node_id, {}).get("subject_id", ""),
            name=node_data.get("label", node_id),
            definition=node_data.get("definition"),
            neighbors=[n for n in graph.get("edges", []) if n.get("source") == node_id or n.get("target") == node_id]
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
    subjects_meta = _graph_subjects()
    return Concept(
        id=concept_id,
        subject_id=subjects_meta.get(concept_id, {}).get("subject_id", ""),
        name=node_data.get("label", concept_id),
        definition=node_data.get("definition"),
    )


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
            subjects_meta = _graph_subjects()
            neighbors.append(Concept(
                id=neighbor_id,
                subject_id=subjects_meta.get(neighbor_id, {}).get("subject_id", ""),
                name=graph["nodes"][neighbor_id].get("label", neighbor_id),
                definition=graph["nodes"][neighbor_id].get("definition"),
            ))
    return neighbors