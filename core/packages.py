"""Question packages: QUESTION_PACKAGE / PACKAGE_VERSION / QUESTION /
QUESTION_OPTION / ESSAY_RUBRIC / RUBRIC_CRITERION / QUESTION_NODE.

Layout (per PRD): database/<subject>/<package_id>/package.json with immutable
published snapshots under versions/v<N>.json. The canonical package_key is
"<subject>/<package_id>" so the directory name and payload id can never drift.
"""

import re
from pathlib import Path

from core.store import (
    DATABASE_DIR,
    VALID_DIFFICULTIES,
    content_hash,
    load_json,
    new_id,
    now_utc,
    slugify,
    write_json,
)

MCQ_OPTION_KEYS = ("A", "B", "C", "D", "E")
PACKAGE_FILE = "package.json"
VERSIONS_DIR = "versions"


def package_dir(subject: str, package_id: str) -> Path:
    return DATABASE_DIR / subject / package_id


def package_path(subject: str, package_id: str) -> Path:
    return package_dir(subject, package_id) / PACKAGE_FILE


def list_packages():
    """Return [{subject, package_id, path}] for every package.json on disk."""
    found = []
    if not DATABASE_DIR.exists():
        return found
    for subject_dir in sorted(DATABASE_DIR.iterdir()):
        if not subject_dir.is_dir():
            continue
        for pkg_dir in sorted(subject_dir.iterdir()):
            pkg_file = pkg_dir / PACKAGE_FILE
            if pkg_dir.is_dir() and pkg_file.exists():
                found.append(
                    {
                        "subject": subject_dir.name,
                        "package_id": pkg_dir.name,
                        "path": pkg_file,
                    }
                )
    return found


def load_package(subject: str, package_id: str):
    return load_json(package_path(subject, package_id))


def load_published_version(subject: str, package_id: str, version: int):
    return load_json(
        package_dir(subject, package_id) / VERSIONS_DIR / f"v{version}.json"
    )


def new_package(subject: str, title: str, level: str = "", description: str = "",
                source=None) -> dict:
    package_id = slugify(title)
    return {
        "schema_version": 1,
        "package_key": f"{subject}/{package_id}",
        "package_id": package_id,
        "subject": subject,
        "title": title or package_id,
        "level": level,
        "description": description,
        "source": source or {},
        "status": "draft",
        "version": 1,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "published_at": None,
        "mcqs": [],
        "essay": [],
    }


def save_package(pkg: dict) -> dict:
    """Persist the working copy. Published versions are never touched here;
    call start_next_draft() before editing a published package."""
    subject, package_id = pkg.get("subject"), pkg.get("package_id")
    if not subject or not package_id:
        raise ValueError("Package needs non-empty subject and package_id")
    pkg["updated_at"] = now_utc()
    write_json(package_path(subject, package_id), pkg)
    return pkg


def publish_package(subject: str, package_id: str) -> dict:
    """Publish current content as an immutable version snapshot.

    If version N was already published with identical content this is a no-op;
    otherwise the next version number is used, so earlier snapshots stay valid
    for historical attempts (FR-12).
    """
    pkg = load_package(subject, package_id)
    if pkg is None:
        raise FileNotFoundError(f"Package not found: {subject}/{package_id}")
    issues = [i for i in validate_package(pkg) if i["severity"] == "error"]
    if issues:
        raise ValueError("Cannot publish a package with validation errors:\n" +
                         "\n".join(f"- {i['message']}" for i in issues))

    content = content_hash(repr(sorted_questions(pkg)))
    versions_dir = package_dir(subject, package_id) / VERSIONS_DIR
    existing = sorted(versions_dir.glob("v*.json")) if versions_dir.exists() else []
    last_version, last_hash = 0, None
    if existing:
        last = load_json(existing[-1], {})
        last_version = int(existing[-1].stem[1:])
        last_hash = last.get("content_hash")

    if last_hash is not None and last_hash == content:
        return load_json(existing[-1])

    if existing:
        version = last_version + 1
    else:
        version = max(int(pkg.get("version") or 0), 1)
    pkg["version"] = version
    pkg["status"] = "published"
    pkg["published_at"] = now_utc()

    snapshot = dict(pkg)
    snapshot["content_hash"] = content
    snapshot["status"] = "published"
    write_json(versions_dir / f"v{version}.json", snapshot)
    write_json(package_path(subject, package_id), pkg)
    return snapshot


def start_next_draft(subject: str, package_id: str) -> dict:
    """Copy latest state into an incremented draft version (published stays immutable)."""
    pkg = load_package(subject, package_id)
    if pkg is None:
        raise FileNotFoundError(f"Package not found: {subject}/{package_id}")
    pkg["version"] = int(pkg.get("version") or 1) + 1
    pkg["status"] = "draft"
    pkg["updated_at"] = now_utc()
    save_package(pkg)
    return pkg


def add_mcq(pkg: dict, question: str, options: dict, correct_option: str,
            difficulty: str = "medium", learning_objective: str = "",
            slide_refs=None, node_links=None) -> str:
    cleaned = {}
    for key, value in options.items():
        match = re.match(r"^\(?([A-Ea-e])[\)\.\:]?$", str(key).strip())
        letter = (match.group(1).upper() if match else str(key).strip().upper()[:1])
        if not isinstance(value, str) or not value.strip():
            continue
        cleaned[letter] = value.strip()
    qid = new_id("mcq")
    pkg.setdefault("mcqs", []).append({
        "id": qid,
        "kind": "mcq",
        "question": (question or "").strip(),
        "options": cleaned,
        "correct_option": (correct_option or "").strip().upper(),
        "difficulty": difficulty,
        "learning_objective": learning_objective or "",
        "slide_refs": list(slide_refs or []),
        "node_links": list(node_links or []),
    })
    return qid


def add_essay(pkg: dict, prompt: str, expected_keywords=None, criteria=None,
              total_points: float = 0, grading_notes: str = "",
              difficulty: str = "medium", learning_objective: str = "",
              slide_refs=None, node_links=None) -> str:
    eid = new_id("ess")
    pkg.setdefault("essay", []).append({
        "id": eid,
        "kind": "essay",
        "prompt": (prompt or "").strip(),
        "expected_keywords": [k for k in (expected_keywords or []) if str(k).strip()],
        "rubric": {
            "total_points": total_points,
            "grading_notes": grading_notes or "",
            "criteria": [
                {
                    "keyword": c.get("keyword", "").strip(),
                    "weight": c.get("weight", 1),
                    "description": c.get("description", ""),
                }
                for c in (criteria or [])
                if str(c.get("keyword", "")).strip()
            ],
        },
        "difficulty": difficulty,
        "learning_objective": learning_objective or "",
        "slide_refs": list(slide_refs or []),
        "node_links": list(node_links or []),
    })
    return eid


def validate_package(pkg: dict):
    """Return [{severity: error|warning, location, message}]. Empty errors = publishable."""
    issues = []
    loc = f"{pkg.get('subject', '?')}/{pkg.get('package_id', '?')}"

    if not str(pkg.get("package_id", "")).strip():
        issues.append({"severity": "error", "location": loc,
                       "message": "package_id is missing"})
    expected_key = f"{pkg.get('subject')}/{pkg.get('package_id')}"
    if pkg.get("package_key") != expected_key:
        issues.append({"severity": "error", "location": loc,
                       "message": f"package_key '{pkg.get('package_key')}' must be '{expected_key}'"})
    if not str(pkg.get("subject", "")).strip():
        issues.append({"severity": "error", "location": loc,
                       "message": "subject is missing"})
    if pkg.get("status") not in ("draft", "review", "published"):
        issues.append({"severity": "error", "location": loc,
                       "message": f"invalid status '{pkg.get('status')}'"})

    seen_ids = set()
    for idx, mcq in enumerate(pkg.get("mcqs", []), start=1):
        where = f"{loc} mcqs[{idx}]"
        qid = str(mcq.get("id", "")).strip()
        if not qid:
            issues.append({"severity": "error", "location": where,
                           "message": "question id is missing"})
        elif qid in seen_ids:
            issues.append({"severity": "error", "location": where,
                           "message": f"duplicate question id '{qid}'"})
        else:
            seen_ids.add(qid)

        options = mcq.get("options") or {}
        if not (2 <= len(options) <= len(MCQ_OPTION_KEYS)):
            issues.append({"severity": "error", "location": where,
                           "message": f"needs 2-{len(MCQ_OPTION_KEYS)} options, found {len(options)}"})
        invalid_keys = [k for k in options if k not in MCQ_OPTION_KEYS]
        if invalid_keys:
            issues.append({"severity": "error", "location": where,
                           "message": f"invalid option keys {invalid_keys}; allowed A-E"})
        texts = [str(v) for v in options.values()]
        if any(not t.strip() for t in texts):
            issues.append({"severity": "error", "location": where,
                           "message": "option text cannot be empty"})
        correct = mcq.get("correct_option")
        if correct not in options:
            issues.append({"severity": "error", "location": where,
                           "message": f"correct_option '{correct}' is not one of {sorted(options)}"})
        if not str(mcq.get("question", "")).strip():
            issues.append({"severity": "error", "location": where,
                           "message": "question prompt is empty"})
        difficulty = mcq.get("difficulty", "")
        if difficulty and difficulty not in VALID_DIFFICULTIES:
            issues.append({"severity": "warning", "location": where,
                           "message": f"unknown difficulty '{difficulty}'"})
        if not str(mcq.get("learning_objective", "")).strip():
            issues.append({"severity": "warning", "location": where,
                           "message": "missing learning_objective"})

    for idx, essay in enumerate(pkg.get("essay", []), start=1):
        where = f"{loc} essay[{idx}]"
        qid = str(essay.get("id", "")).strip()
        if not qid:
            issues.append({"severity": "error", "location": where,
                           "message": "question id is missing"})
        elif qid in seen_ids:
            issues.append({"severity": "error", "location": where,
                           "message": f"duplicate question id '{qid}'"})
        else:
            seen_ids.add(qid)

        if not str(essay.get("prompt", "")).strip():
            issues.append({"severity": "error", "location": where,
                           "message": "prompt is empty"})
        keywords = essay.get("expected_keywords") or []
        if any(not str(k).strip() for k in keywords):
            issues.append({"severity": "error", "location": where,
                           "message": "expected_keywords contains blank entries"})
        rubric = essay.get("rubric") or {}
        total_points = rubric.get("total_points", 0) or 0
        try:
            total_points_f = float(total_points)
        except (TypeError, ValueError):
            total_points_f = -1
        if total_points_f < 0:
            issues.append({"severity": "error", "location": where,
                           "message": f"rubric.total_points must be non-negative, got '{total_points}'"})
        weight_sum = 0.0
        for c_idx, crit in enumerate(rubric.get("criteria", []) or [], start=1):
            kw = str(crit.get("keyword", "")).strip()
            if not kw:
                issues.append({"severity": "error",
                               "location": f"{where} criteria[{c_idx}]",
                               "message": "criterion keyword is empty"})
            try:
                w = float(crit.get("weight", 0))
            except (TypeError, ValueError):
                issues.append({"severity": "error",
                               "location": f"{where} criteria[{c_idx}]",
                               "message": f"criterion weight '{crit.get('weight')}' is not numeric"})
                w = 0
            if w < 0:
                issues.append({"severity": "error",
                               "location": f"{where} criteria[{c_idx}]",
                               "message": f"criterion weight must be non-negative, got {w}"})
            weight_sum += max(w, 0)
        if total_points_f > 0 and weight_sum > total_points_f + 1e-9:
            issues.append({"severity": "warning", "location": where,
                           "message": f"criteria weights sum to {weight_sum:g} but total_points is {total_points_f:g}"})
        if total_points_f == 0 and not rubric.get("criteria"):
            issues.append({"severity": "warning", "location": where,
                           "message": "no rubric criteria; grading falls back to expected_keywords"})

    return issues


def sorted_questions(pkg: dict):
    questions = [("mcq", q["id"], q.get("question", "")) for q in pkg.get("mcqs", [])]
    questions += [("essay", e["id"], e.get("prompt", "")) for e in pkg.get("essay", [])]
    return sorted(questions)
