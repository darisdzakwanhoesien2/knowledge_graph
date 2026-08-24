"""Build the shared subject/source registry from json_nodes/ and graph metadata.

Usage: python3 pipelines/build_registry.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.registry import build_registry, save_registry  # noqa: E402
from core.store import BASE_DIR  # noqa: E402


def main():
    registry = build_registry(BASE_DIR / "json_nodes")
    save_registry(registry)
    subjects = registry["subjects"]
    docs = sum(len(s["source_documents"]) for s in subjects.values())
    print(f"Registered {len(subjects)} subjects / {docs} source documents -> data/registry/registry.json")


if __name__ == "__main__":
    main()
