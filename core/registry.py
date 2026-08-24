"""Subject + source-document registry (SUBJECT, SOURCE_DOCUMENT, NODE_SOURCE).

Builds a shared registry from json_nodes/ and the merged graph metadata so both
graph content and question packages reference one canonical subject list.
"""

from core.store import (
    BASE_DIR,
    REGISTRY_DIR,
    content_hash,
    load_json,
    now_utc,
    write_json,
)

REGISTRY_FILE = REGISTRY_DIR / "registry.json"


def build_registry(json_nodes_dir) -> dict:
    """Scan json_nodes/<subject>/<file>.json and the merged graph metadata."""
    graph_meta = _graph_subjects()
    subjects = {}
    for subject_dir in sorted(json_nodes_dir.iterdir()) if json_nodes_dir.exists() else []:
        if not subject_dir.is_dir():
            continue
        subject_id = subject_dir.name
        files = []
        for f in sorted(subject_dir.glob("*.json")):
            if f.name in ("flashcards.json", "merged_graph.json"):
                continue
            raw = f.read_bytes()
            files.append({
                "filename": f.name,
                "media_type": "application/json",
                "content_hash": content_hash(raw),
                "bytes": len(raw),
                "imported_at": now_utc(),
            })
        meta = graph_meta.get(subject_id, {})
        subjects[subject_id] = {
            "subject_id": subject_id,
            "display_name": meta.get("display_name", subject_id.replace("_", " ").title()),
            "files": [f["filename"] for f in files],
            "source_documents": files,
        }

    return {"built_at": now_utc(), "subjects": subjects}


def save_registry(registry: dict) -> None:
    write_json(REGISTRY_FILE, registry)


def load_registry() -> dict:
    return load_json(REGISTRY_FILE, {"built_at": None, "subjects": {}})


def list_subjects():
    return sorted(load_registry().get("subjects", {}).keys())


def _graph_subjects() -> dict:
    graph = load_json(BASE_DIR / "data" / "graphs" / "merged_graph.json", {})
    return graph.get("metadata", {}).get("subjects", {})
