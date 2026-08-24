"""Transparent grading: MCQ exact-match + essay keyword/rubric matching.

Every graded response returns the matched keywords/criteria plus evidence
snippets so essay scores are auditable (RESPONSE_CRITERION in the ERD).
"""

import re

EVIDENCE_CONTEXT = 40


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).lower()


def grade_mcq(mcq: dict, selected) -> dict:
    correct_option = mcq.get("correct_option")
    selected = str(selected).strip().upper() if selected else ""
    is_correct = bool(selected) and selected == str(correct_option).strip().upper()
    return {
        "question_id": mcq.get("id"),
        "question_kind": "mcq",
        "selected_option": selected,
        "correct": is_correct,
        "score": 1.0 if is_correct else 0.0,
        "max_score": 1.0,
    }


def find_evidence(answer: str, keyword: str) -> str:
    idx = normalize(answer).find(normalize(keyword))
    if idx < 0:
        return ""
    plain = re.sub(r"\s+", " ", answer or "")
    start = max(0, idx - EVIDENCE_CONTEXT)
    end = min(len(plain), idx + len(keyword) + EVIDENCE_CONTEXT)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(plain) else ""
    return f"{prefix}{plain[start:end]}{suffix}"


def grade_essay(essay: dict, essay_text) -> dict:
    text = essay_text if isinstance(essay_text, str) else ""
    norm_text = normalize(text)

    rubric = essay.get("rubric") or {}
    criteria = rubric.get("criteria") or []
    total_points = _to_float(rubric.get("total_points"), 0.0)

    matched_criteria = []
    raw_points = 0.0
    for crit in criteria:
        keyword = str(crit.get("keyword", ""))
        matched = bool(keyword) and normalize(keyword) in norm_text
        weight = _to_float(crit.get("weight"), 0.0)
        if matched:
            raw_points += weight
        matched_criteria.append({
            "keyword": keyword,
            "matched": matched,
            "weight": weight,
            "evidence": find_evidence(text, keyword) if matched else "",
        })

    expected_keywords = [str(k) for k in (essay.get("expected_keywords") or [])]
    matched_keywords = []
    for kw in expected_keywords:
        if normalize(kw) and normalize(kw) in norm_text:
            matched_keywords.append(kw)

    if criteria:
        score = raw_points
        max_score = total_points if total_points > 0 else sum(
            max(_to_float(c.get("weight"), 0.0), 0.0) for c in criteria)
    elif expected_keywords:
        score = float(len(matched_keywords))
        max_score = float(len(expected_keywords))
    else:
        score, max_score = 0.0, 0.0

    if max_score > 0:
        score = min(score, max_score)
    pct = round(score / max_score, 4) if max_score > 0 else None

    return {
        "question_id": essay.get("id"),
        "question_kind": "essay",
        "essay_text": text,
        "score": round(score, 4),
        "max_score": round(max_score, 4),
        "pct": pct,
        "matched_keywords": matched_keywords,
        "matched_criteria": matched_criteria,
    }


def compute_scores(mcq_results, essay_results) -> dict:
    mcq_score = sum(r["score"] for r in mcq_results)
    mcq_max = sum(r["max_score"] for r in mcq_results)
    essay_score = sum(r["score"] for r in essay_results)
    essay_max = sum(r["max_score"] for r in essay_results)

    section_pcts = [
        p for p in (
            mcq_score / mcq_max if mcq_max > 0 else None,
            essay_score / essay_max if essay_max > 0 else None,
        ) if p is not None
    ]
    final = sum(section_pcts) / len(section_pcts) if section_pcts else 0.0

    return {
        "mcq_score": round(mcq_score, 4),
        "mcq_max": round(mcq_max, 4),
        "mcq_pct": round(mcq_score / mcq_max, 4) if mcq_max > 0 else None,
        "essay_score": round(essay_score, 4),
        "essay_max": round(essay_max, 4),
        "essay_pct": round(essay_score / essay_max, 4) if essay_max > 0 else None,
        "final_score": round(final, 4),
    }


def _to_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
