"""Assessment attempts: USER / ASSESSMENT_ATTEMPT / RESPONSE / RESPONSE_CRITERION.

Each submitted attempt is one JSON file under results/user_submissions/ holding
answers, per-response grading evidence, and score components (FR-9, FR-12).
"""

import csv
import io
from pathlib import Path

from core.grading import grade_mcq, grade_essay, compute_scores
from core.store import RESULTS_DIR, load_json, new_id, now_utc, write_json


def start_attempt(user: dict) -> str:
    return new_id("att")


def submit_attempt(*, user: dict, pkg_snapshot: dict, answers_mcq: dict,
                   answers_essay: dict, started_at: str = None,
                   attempts_dir: Path = None) -> dict:
    """Grade and persist an attempt against an immutable package snapshot.

    answers_mcq: {question_id: selected_option_letter}
    answers_essay: {question_id: essay_text}
    """
    mcq_results = []
    for q in pkg_snapshot.get("mcqs", []):
        mcq_results.append({**grade_mcq(q, answers_mcq.get(q["id"])),
                            "question": q.get("question", ""),
                            "correct_option": q.get("correct_option"),
                            "node_links": list(q.get("node_links", []))})

    essay_results = []
    for q in pkg_snapshot.get("essay", []):
        essay_results.append({**grade_essay(q, answers_essay.get(q["id"], "")),
                              "prompt": q.get("prompt", ""),
                              "expected_keywords": list(q.get("expected_keywords", [])),
                              "grading_notes": (q.get("rubric") or {}).get("grading_notes", ""),
                              "node_links": list(q.get("node_links", []))})

    record = {
        "attempt_id": new_id("att"),
        "user": {"external_key": user.get("external_key", "local_user"),
                 "display_name": user.get("display_name", "")},
        "subject": pkg_snapshot.get("subject"),
        "package_id": pkg_snapshot.get("package_id"),
        "package_key": f"{pkg_snapshot.get('subject')}/{pkg_snapshot.get('package_id')}",
        "package_version": pkg_snapshot.get("version"),
        "package_content_hash": pkg_snapshot.get("content_hash", ""),
        "started_at": started_at or now_utc(),
        "submitted_at": now_utc(),
        "responses": mcq_results + essay_results,
        "scores": compute_scores(mcq_results, essay_results),
    }

    target_dir = Path(attempts_dir) if attempts_dir else RESULTS_DIR
    write_json(target_dir / f"{record['attempt_id']}.json", record)
    return record


def list_attempts(attempts_dir: Path = None):
    """Return [{attempt_id, path}] sorted by submitted_at descending."""
    target_dir = Path(attempts_dir) if attempts_dir else RESULTS_DIR
    if not target_dir.exists():
        return []
    out = []
    for f in sorted(target_dir.glob("*.json")):
        rec = load_json(f)
        if isinstance(rec, dict) and rec.get("attempt_id"):
            out.append((rec.get("submitted_at", ""), rec["attempt_id"], f))
    out.sort(key=lambda item: item[0], reverse=True)
    return [{"attempt_id": attempt_id, "path": path} for _, attempt_id, path in out]


def load_attempt(attempt_id: str, attempts_dir: Path = None):
    target_dir = Path(attempts_dir) if attempts_dir else RESULTS_DIR
    return load_json(target_dir / f"{attempt_id}.json")


def attempts_dataframe(attempts=None, attempts_dir: Path = None):
    """Flatten attempts into one row per response for review tables and CSV export."""
    import pandas as pd

    entries = attempts if attempts is not None else list_attempts(attempts_dir)
    rows = []
    for entry in entries:
        rec = load_attempt(entry["attempt_id"], attempts_dir)
        if not rec:
            continue
        scores = rec.get("scores", {})
        for resp in rec.get("responses", []):
            is_mcq = resp.get("question_kind") == "mcq"
            matched = ", ".join(
                c["keyword"] for c in resp.get("matched_criteria", []) if c.get("matched")
            ) or ", ".join(resp.get("matched_keywords", []))
            pct = resp.get("pct")
            if pct is None:
                max_s = float(resp.get("max_score") or 0)
                pct = (float(resp.get("score") or 0) / max_s) if max_s > 0 else None
            rows.append({
                "attempt_id": rec.get("attempt_id"),
                "user": rec.get("user", {}).get("display_name") or rec.get("user", {}).get("external_key"),
                "subject": rec.get("subject"),
                "package": rec.get("package_key"),
                "version": rec.get("package_version"),
                "submitted_at": rec.get("submitted_at"),
                "kind": resp.get("question_kind"),
                "question_id": resp.get("question_id"),
                "question": resp.get("question") or resp.get("prompt"),
                "answer": resp.get("selected_option") or resp.get("essay_text"),
                "correct_option": resp.get("correct_option", ""),
                "matched_criteria": matched,
                "score": resp.get("score"),
                "max_score": resp.get("max_score"),
                "pct": round(pct, 4) if pct is not None else None,
                "final_score_pct": scores.get("final_score"),
            })
    columns = ["attempt_id", "user", "subject", "package", "version", "submitted_at",
               "kind", "question_id", "question", "answer", "correct_option",
               "matched_criteria", "score", "max_score", "pct", "final_score_pct"]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns)


def attempts_csv(attempts=None, attempts_dir: Path = None) -> str:
    df = attempts_dataframe(attempts, attempts_dir)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(df.columns))
    writer.writeheader()
    for _, row in df.iterrows():
        writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
    return buf.getvalue()
