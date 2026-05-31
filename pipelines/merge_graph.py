import json
import copy
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# ======================================================
# PATH CONFIG
# ======================================================

BASE_DIR = Path(__file__).resolve().parents[1]

JSON_NODES_DIR = BASE_DIR / "json_nodes"
OUTPUT_GRAPH = BASE_DIR / "data" / "graphs" / "merged_graph.json"

OUTPUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)

# Files we never ingest from json_nodes
SKIP_FILES = {
    "flashcards.json",
    "merged_graph.json",
    "subject_index.json",
    ".ds_store"
}

# ======================================================
# UTILITIES
# ======================================================

def display_name_from_slug(slug: str) -> str:
    """snake_case → Title Case"""
    return slug.replace("_", " ").title()


def safe_load_json(path: Path) -> Optional[dict]:
    """
    Safely load JSON.
    Returns None if file is invalid or unreadable.
    """
    try:
        if path.stat().st_size == 0:
            print(f"⚠️ Skipping empty file: {path}")
            return None

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON skipped: {path}")
        return None

    except Exception as e:
        print(f"⚠️ Failed reading {path}: {e}")
        return None


def iter_subject_files():
    """
    Yield:
        subject_id, subject_name, json_file_path
    """

    if not JSON_NODES_DIR.exists():
        raise RuntimeError(f"json_nodes folder not found: {JSON_NODES_DIR}")

    for subject_dir in sorted(JSON_NODES_DIR.iterdir()):
        if not subject_dir.is_dir():
            continue

        subject_id = subject_dir.name
        subject_name = display_name_from_slug(subject_id)

        for json_file in sorted(subject_dir.glob("*.json")):

            if json_file.name.lower() in SKIP_FILES:
                continue

            yield subject_id, subject_name, json_file


# ======================================================
# MERGE ENGINE
# ======================================================

def merge_graph():
    graph = {
        "nodes": {},
        "edges": [],
        "metadata": {
            # Use a timezone-aware UTC timestamp to avoid deprecated `utcnow()`.
            "built_at": datetime.now(timezone.utc).isoformat(),
            "subjects": {}
        }
    }

    print("\n🔍 Scanning subject folders...\n")

    total_files = 0
    valid_files = 0
    skipped_files = 0

    for subject_id, subject_name, json_path in iter_subject_files():
        total_files += 1
        print(f"   • {subject_name:<35} ← {json_path.name}")

        payload = safe_load_json(json_path)
        if payload is None:
            skipped_files += 1
            continue

        valid_files += 1

        # Register subject metadata
        graph["metadata"]["subjects"].setdefault(subject_id, {
            "subject_id": subject_id,
            "display_name": subject_name,
            "files": []
        })
        graph["metadata"]["subjects"][subject_id]["files"].append(json_path.name)

        # --------------------------------------------------
        # CASE 1 — Full graph JSON
        # --------------------------------------------------
        if isinstance(payload, dict) and "nodes" in payload and "edges" in payload:

            for node_name, node_data in payload.get("nodes", {}).items():
                # Copy to avoid mutating the source payload dict when we attach metadata below.
                node = graph["nodes"].setdefault(node_name, copy.deepcopy(node_data))

                meta = node.setdefault("metadata", {})
                meta.setdefault("subjects", set()).add(subject_id)
                meta.setdefault("source_files", set()).add(json_path.name)

            for edge in payload.get("edges", []):
                if edge not in graph["edges"]:
                    graph["edges"].append(edge)

        # --------------------------------------------------
        # CASE 2 — Single entity JSON
        # --------------------------------------------------
        elif isinstance(payload, dict) and "entity" in payload:
            entity = payload["entity"]

            # Some sources can include leading/trailing whitespace; normalize to prevent
            # accidental duplicate nodes like "SVD" vs "SVD ".
            if isinstance(entity, str):
                entity = entity.strip()

            node = graph["nodes"].setdefault(entity, {
                "type": payload.get("type", "Concept"),
                "domain": payload.get("domain", ""),
                "definition": payload.get("definition", ""),
                "description": payload.get("description", ""),
                "properties": payload.get("properties", {}),
                "metadata": {}
            })

            meta = node.setdefault("metadata", {})
            meta.setdefault("subjects", set()).add(subject_id)
            meta.setdefault("source_files", set()).add(json_path.name)

            for rel in payload.get("relations", []):
                # Relations can sometimes be malformed; skip invalid records instead of
                # producing edges with missing endpoints.
                if not isinstance(rel, dict):
                    continue
                edge = {
                    "source": entity,
                    "type": rel.get("type", "related_to"),
                    "target": rel.get("target")
                }
                if edge not in graph["edges"]:
                    graph["edges"].append(edge)

        # --------------------------------------------------
        # CASE 3 — List of entities
        # --------------------------------------------------
        elif isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict) or "entity" not in item:
                    continue

                entity = item["entity"]

                if isinstance(entity, str):
                    entity = entity.strip()

                node = graph["nodes"].setdefault(entity, {
                    "type": item.get("type", "Concept"),
                    "domain": item.get("domain", ""),
                    "definition": item.get("definition", ""),
                    "description": item.get("description", ""),
                    "properties": item.get("properties", {}),
                    "metadata": {}
                })

                meta = node.setdefault("metadata", {})
                meta.setdefault("subjects", set()).add(subject_id)
                meta.setdefault("source_files", set()).add(json_path.name)

                for rel in item.get("relations", []):
                    if not isinstance(rel, dict):
                        continue
                    edge = {
                        "source": entity,
                        "type": rel.get("type", "related_to"),
                        "target": rel.get("target")
                    }
                    if edge not in graph["edges"]:
                        graph["edges"].append(edge)

        # --------------------------------------------------
        # Unsupported JSON schema
        # --------------------------------------------------
        else:
            print(f"⚠️ Unsupported schema skipped: {json_path}")
            skipped_files += 1

    # --------------------------------------------------
    # Normalize metadata sets → lists
    # --------------------------------------------------
    for node in graph["nodes"].values():
        meta = node.get("metadata", {})
        meta["subjects"] = sorted(list(meta.get("subjects", [])))
        meta["source_files"] = sorted(list(meta.get("source_files", [])))

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------
    print("\n📊 Merge Summary")
    print(f"   Total JSON files scanned : {total_files}")
    print(f"   Valid files ingested     : {valid_files}")
    print(f"   Files skipped            : {skipped_files}")
    print(f"   Nodes                     : {len(graph['nodes'])}")
    print(f"   Edges                     : {len(graph['edges'])}")
    print(f"   Subjects                  : {len(graph['metadata']['subjects'])}")

    return graph


# ======================================================
# SAVE
# ======================================================

def save_graph(graph):
    OUTPUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_GRAPH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Graph saved to:\n   {OUTPUT_GRAPH}")


# ======================================================
# MAIN
# ======================================================

if __name__ == "__main__":
    graph = merge_graph()
    save_graph(graph)


# import json
# from pathlib import Path
# from datetime import datetime

# # ======================================================
# # PATH CONFIG
# # ======================================================

# BASE_DIR = Path(__file__).resolve().parents[1]

# JSON_NODES_DIR = BASE_DIR / "json_nodes"
# OUTPUT_GRAPH = BASE_DIR / "data" / "graphs" / "merged_graph.json"

# OUTPUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)


# # ======================================================
# # UTILITIES
# # ======================================================

# def display_name_from_slug(slug: str) -> str:
#     """Convert snake_case → Title Case."""
#     return slug.replace("_", " ").title()


# def iter_subject_files():
#     """
#     Yield:
#         subject_id, subject_name, json_file_path
#     """
#     for subject_dir in JSON_NODES_DIR.iterdir():
#         if not subject_dir.is_dir():
#             continue

#         subject_id = subject_dir.name
#         subject_name = display_name_from_slug(subject_id)

#         for json_file in subject_dir.glob("*.json"):
#             if json_file.name.lower() == "metadata.json":
#                 continue
#             yield subject_id, subject_name, json_file


# def load_json(path: Path):
#     with open(path, "r", encoding="utf-8") as f:
#         return json.load(f)


# # ======================================================
# # MERGE LOGIC
# # ======================================================

# def merge_graph():
#     graph = {
#         "nodes": {},
#         "edges": [],
#         "metadata": {
#             "built_at": datetime.utcnow().isoformat(),
#             "subjects": {}
#         }
#     }

#     print("🔍 Scanning subject folders...")

#     for subject_id, subject_name, json_path in iter_subject_files():
#         print(f"   • {subject_name:<35} ← {json_path.name}")

#         payload = load_json(json_path)

#         # Register subject globally
#         graph["metadata"]["subjects"].setdefault(subject_id, {
#             "subject_id": subject_id,
#             "display_name": subject_name,
#             "files": []
#         })
#         graph["metadata"]["subjects"][subject_id]["files"].append(json_path.name)

#         # ----------------------------------------
#         # Case 1 — Graph JSON
#         # ----------------------------------------
#         if isinstance(payload, dict) and "nodes" in payload and "edges" in payload:

#             for node_name, node_data in payload["nodes"].items():
#                 node = graph["nodes"].setdefault(node_name, node_data)

#                 meta = node.setdefault("metadata", {})
#                 meta.setdefault("subjects", set()).add(subject_id)
#                 meta.setdefault("source_files", set()).add(json_path.name)

#             for edge in payload["edges"]:
#                 if edge not in graph["edges"]:
#                     graph["edges"].append(edge)

#         # ----------------------------------------
#         # Case 2 — Entity JSON
#         # ----------------------------------------
#         elif isinstance(payload, dict) and "entity" in payload:
#             entity = payload["entity"]

#             node = graph["nodes"].setdefault(entity, {
#                 "type": payload.get("type", "Concept"),
#                 "domain": payload.get("domain", ""),
#                 "definition": payload.get("definition", ""),
#                 "description": payload.get("description", ""),
#                 "properties": payload.get("properties", {}),
#                 "metadata": {}
#             })

#             meta = node.setdefault("metadata", {})
#             meta.setdefault("subjects", set()).add(subject_id)
#             meta.setdefault("source_files", set()).add(json_path.name)

#             for rel in payload.get("relations", []):
#                 edge = {
#                     "source": entity,
#                     "type": rel.get("type", "related_to"),
#                     "target": rel.get("target")
#                 }
#                 if edge not in graph["edges"]:
#                     graph["edges"].append(edge)

#         # ----------------------------------------
#         # Case 3 — List of entities
#         # ----------------------------------------
#         elif isinstance(payload, list):
#             for item in payload:
#                 if not isinstance(item, dict) or "entity" not in item:
#                     continue

#                 entity = item["entity"]

#                 node = graph["nodes"].setdefault(entity, {
#                     "type": item.get("type", "Concept"),
#                     "domain": item.get("domain", ""),
#                     "definition": item.get("definition", ""),
#                     "description": item.get("description", ""),
#                     "properties": item.get("properties", {}),
#                     "metadata": {}
#                 })

#                 meta = node.setdefault("metadata", {})
#                 meta.setdefault("subjects", set()).add(subject_id)
#                 meta.setdefault("source_files", set()).add(json_path.name)

#                 for rel in item.get("relations", []):
#                     edge = {
#                         "source": entity,
#                         "type": rel.get("type", "related_to"),
#                         "target": rel.get("target")
#                     }
#                     if edge not in graph["edges"]:
#                         graph["edges"].append(edge)

#         else:
#             print(f"⚠️ Skipped unsupported JSON format: {json_path}")

#     # ----------------------------------------
#     # Normalize metadata sets → lists
#     # ----------------------------------------
#     for node in graph["nodes"].values():
#         meta = node.get("metadata", {})
#         meta["subjects"] = sorted(list(meta.get("subjects", [])))
#         meta["source_files"] = sorted(list(meta.get("source_files", [])))

#     print("\n✅ Merge completed")
#     print(f"   Nodes : {len(graph['nodes'])}")
#     print(f"   Edges : {len(graph['edges'])}")
#     print(f"   Subjects : {len(graph['metadata']['subjects'])}")

#     return graph


# # ======================================================
# # SAVE
# # ======================================================

# def save_graph(graph):
#     OUTPUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)
#     with open(OUTPUT_GRAPH, "w", encoding="utf-8") as f:
#         json.dump(graph, f, indent=2, ensure_ascii=False)

#     print(f"\n💾 Graph saved to: {OUTPUT_GRAPH}")


# # ======================================================
# # MAIN
# # ======================================================

# if __name__ == "__main__":
#     graph = merge_graph()
#     save_graph(graph)
