"""Server-side runner for the ADDING_DATA.md pipeline chain.

merge_graph → generate_flashcards → extract_subject_index → build_registry →
check_quality → migrate_json_to_sqlite.

Each step runs as a subprocess using the same interpreter as the API, so the
chain behaves exactly like the documented CLI commands and script-style
pipelines (extract_subject_index.py) stay importable-safe. Synchronous by
design for the MVP; swap this function for a queued job without touching the
API contract once uploads get slow (see docs/UPLOAD_SYSTEM_PLAN.md).
"""

import subprocess
import sys
from pathlib import Path

from core.store import BASE_DIR

PIPELINE_TIMEOUT_SECONDS = 180


def database_path() -> Path:
    """Resolve the app's SQLite path from KG_DATABASE_URL (same default as app/db.py)."""
    import os

    url = os.environ.get("KG_DATABASE_URL", "sqlite:///database/knowledge.db")
    if url.startswith("sqlite:////"):
        return Path("/" + url[len("sqlite:////"):])
    if url.startswith("sqlite:///"):
        return BASE_DIR / url[len("sqlite:///"):]
    return BASE_DIR / "database" / "knowledge.db"


def _steps():
    py = sys.executable
    root = str(BASE_DIR)
    return [
        ("merge_graph", [py, str(BASE_DIR / "pipelines" / "merge_graph.py")], root),
        ("generate_flashcards", [py, str(BASE_DIR / "pipelines" / "generate_flashcards.py")], root),
        ("extract_subject_index", [py, str(BASE_DIR / "pipelines" / "extract_subject_index.py")], root),
        ("build_registry", [py, str(BASE_DIR / "pipelines" / "build_registry.py")], root),
        ("check_quality", [py, str(BASE_DIR / "pipelines" / "check_quality.py")], root),
        ("migrate_json_to_sqlite", [
            py, "-m", "scripts.migrate_json_to_sqlite",
            "--database", str(database_path()),
        ], root),
    ]


def run_pipeline_chain() -> dict:
    """Run every step in order; abort the chain at the first failure.

    Returns {"ok": bool, "steps": [{step, ok, detail}]} — detail carries the
    last output lines so the curator sees *why* a step failed.
    """
    results = []
    ok = True
    for name, cmd, cwd in _steps():
        try:
            proc = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True,
                timeout=PIPELINE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            results.append({"step": name, "ok": False, "detail": f"timed out after {PIPELINE_TIMEOUT_SECONDS}s"})
            ok = False
            break
        except OSError as exc:
            results.append({"step": name, "ok": False, "detail": f"failed to launch: {exc}"})
            ok = False
            break
        tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-5:])
        step_ok = proc.returncode == 0
        results.append({"step": name, "ok": step_ok, "detail": tail or f"exit {proc.returncode}"})
        if not step_ok:
            ok = False
            break
    return {"ok": ok, "steps": results}


def graph_counts() -> dict:
    """Node/edge/subject counts from the freshly merged graph."""
    from core.store import GRAPHS_DIR, load_json

    graph = load_json(GRAPHS_DIR / "merged_graph.json", {})
    return {
        "nodes": len(graph.get("nodes", {})),
        "edges": len(graph.get("edges", [])),
        "subjects": len(graph.get("metadata", {}).get("subjects", {})),
    }
