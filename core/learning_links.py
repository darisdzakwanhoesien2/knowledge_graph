"""Graph-learning integration (FR-11): missed questions link back to concepts.

Resolves node definitions, neighbors, and related flashcards for any node name
referenced by a question's node_links. Missing links never raise; they return
empty payloads so standalone assessment delivery keeps working.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

_flashcards_cache = None


def reset_caches():
    global _flashcards_cache
    _flashcards_cache = None


def load_flashcards():
    global _flashcards_cache
    if _flashcards_cache is None:
        path = BASE_DIR / "data" / "flashcards" / "flashcards.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _flashcards_cache = {c.get("entity", ""): c for c in json.load(f)}
        else:
            _flashcards_cache = {}
    return _flashcards_cache


def find_node(name: str):
    """Case-insensitive lookup of a node in the merged graph. Returns (name, props)."""
    from components.graph_loader import load_graph

    if not name or not str(name).strip():
        return None
    target = str(name).strip().lower()
    try:
        _, raw = load_graph()
    except FileNotFoundError:
        return None
    for node_name, props in raw.get("nodes", {}).items():
        if str(node_name).strip().lower() == target:
            return node_name, props
    return None


def related_flashcard(name: str):
    found = find_node(name)
    if not found:
        return None
    cards = load_flashcards()
    card = cards.get(found[0])
    if card:
        return card
    for key, value in cards.items():
        if key.strip().lower() == found[0].strip().lower():
            return value
    return None


def neighbors(name: str, limit: int = 20):
    found = find_node(name)
    if not found:
        return []
    from components.graph_loader import load_graph

    G, _ = load_graph()
    node = found[0]
    pairs = []
    for _, target, data in G.out_edges(node, data=True):
        pairs.append((target, "→", data.get("type", "")))
    for source, _, data in G.in_edges(node, data=True):
        pairs.append((source, "←", data.get("type", "")))
    return pairs[:limit]


def learning_context(name: str) -> dict:
    """Everything needed for inline remediation UI for one node."""
    found = find_node(name)
    if not found:
        return {"node": name, "exists": False}
    node_name, props = found
    meta = props.get("metadata", {}) if isinstance(props, dict) else {}
    return {
        "node": node_name,
        "exists": True,
        "definition": props.get("definition", ""),
        "description": props.get("description", ""),
        "domain": props.get("domain", ""),
        "subjects": meta.get("subjects", []),
        "source_files": meta.get("source_files", []),
        "neighbors": neighbors(node_name),
        "flashcard": related_flashcard(node_name),
    }
