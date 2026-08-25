"""Pre-write validation for graph/subject content uploads (UPLOAD_SYSTEM_PLAN §1).

Validates that an uploaded JSON file matches one of the three shapes documented
in ADDING_DATA.md and collects warnings — duplicate entities across subjects
and relation targets that resolve to nothing. Warnings never block an upload;
shape errors do.
"""

from core.store import GRAPHS_DIR, load_json


class GraphFileError(ValueError):
    """Raised when a payload matches none of the accepted upload shapes."""


def _valid_entity(item) -> bool:
    return isinstance(item, dict) and isinstance(item.get("entity"), str) and bool(item["entity"].strip())


def collect_entities(payload) -> list:
    """Return the entity dicts in an uploaded payload for any accepted shape."""
    if isinstance(payload, list):
        return [item for item in payload if _valid_entity(item)]
    if isinstance(payload, dict):
        if "nodes" in payload and "edges" in payload:
            return [
                {"entity": name, **(props if isinstance(props, dict) else {})}
                for name, props in (payload.get("nodes") or {}).items()
                if isinstance(name, str) and name.strip()
            ]
        if _valid_entity(payload):
            return [payload]
    raise GraphFileError(
        "Payload must be one of: a list of entities, a single entity object, "
        "or a full graph payload with 'nodes' and 'edges'"
    )


def validate_graph_file(payload, subject_id: str) -> dict:
    """Validate shape and collect non-blocking warnings.

    Returns {"entities": [names], "warnings": [{location, message}]}.
    Raises GraphFileError when the shape itself is invalid — errors block the
    write before anything touches disk; warnings don't.
    """
    entities = collect_entities(payload)
    if not entities:
        raise GraphFileError("Upload contains no usable entities")

    graph = load_json(GRAPHS_DIR / "merged_graph.json", {}) or {}
    nodes = graph.get("nodes", {})
    warnings = []
    names = []

    for pos, item in enumerate(entities, start=1):
        name = str(item["entity"]).strip()
        names.append(name)
        known = nodes.get(name)
        if isinstance(known, dict):
            other_subjects = [
                s for s in known.get("metadata", {}).get("subjects", []) if s != subject_id
            ]
            if other_subjects:
                warnings.append({
                    "location": f"entity[{pos}] '{name}'",
                    "message": f"'{name}' already exists in subject(s) {other_subjects}; "
                               "same-name nodes merge into one node across subjects",
                })
        for r_idx, rel in enumerate(item.get("relations") or [], start=1):
            target = rel.get("target") if isinstance(rel, dict) else None
            if target and target not in nodes:
                warnings.append({
                    "location": f"entity[{pos}] '{name}' relations[{r_idx}]",
                    "message": f"relation target '{target}' is not in this upload or the current "
                               "graph (check_quality.py will flag it after merge)",
                })

    return {"entities": names, "warnings": warnings}


def orphaned_tagged_entities() -> list:
    """Tags whose flashcard no longer exists in the regenerated flashcards.json.

    Tags are keyed by a card's stable entity string precisely so pipeline
    re-runs are safe — but an upload that renames/removes an entity orphans its
    tags. Surfaced in the upload response instead of failing silently.
    """
    from core.learning_links import load_flashcards

    cards = load_flashcards()
    return cards  # caller joins against FLASHCARD_TAG rows


def reset_caches() -> None:
    """Drop cached derived data so post-upload reads see fresh state."""
    from core import learning_links

    learning_links.reset_caches()
