"""Low-level JSON persistence helpers shared by packages, attempts, and registry.

All writes are atomic (tmp file + os.replace) so a crash never leaves a
half-written record behind, per PRD "Invalid records must not silently corrupt
valid graph or assessment data".
"""

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DATABASE_DIR = BASE_DIR / "database"
RESULTS_DIR = BASE_DIR / "results" / "user_submissions"
REGISTRY_DIR = BASE_DIR / "data" / "registry"
REPORTS_DIR = BASE_DIR / "data" / "reports"

VALID_DIFFICULTIES = ("easy", "medium", "hard")
VALID_STATUSES = ("draft", "review", "published")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(data) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def slugify(text: str, fallback: str = "untitled") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return slug or fallback


def load_json(path: Path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def new_id(prefix: str) -> str:
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:12]}"
