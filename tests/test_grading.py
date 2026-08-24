import pytest

from core.grading import compute_scores, find_evidence, grade_mcq, grade_essay


MCQ = {
    "id": "mcq_1",
    "kind": "mcq",
    "question": "Pick one",
    "options": {"A": "one", "B": "two"},
    "correct_option": "B",
}

ESSAY = {
    "id": "ess_1",
    "kind": "essay",
    "prompt": "Explain convexity.",
    "expected_keywords": ["convex", "global"],
    "rubric": {
        "total_points": 5,
        "grading_notes": "",
        "criteria": [
            {"keyword": "convex", "weight": 3, "description": "mentions convexity"},
            {"keyword": "minimum", "weight": 2, "description": "relates minima"},
        ],
    },
}


def test_mcq_exact_match_case_insensitive():
    assert grade_mcq(MCQ, "b")["score"] == 1.0
    assert grade_mcq(MCQ, "B")["correct"] is True
    assert grade_mcq(MCQ, " A ")["score"] == 0.0
    none_selected = grade_mcq(MCQ, None)
    assert none_selected["score"] == 0.0 and none_selected["selected_option"] == ""


def test_essay_rubric_matching_with_evidence():
    result = grade_essay(ESSAY, "A Convex function has no local traps; every LOCAL MINIMUM is global.")
    assert result["score"] == 5.0
    assert result["max_score"] == 5.0
    matched = {c["keyword"]: c["matched"] for c in result["matched_criteria"]}
    assert matched == {"convex": True, "minimum": True}
    evidence = {c["keyword"]: c["evidence"] for c in result["matched_criteria"]}
    assert "Convex" in evidence["convex"]
    assert all(c["matched"] for c in result["matched_criteria"])
    assert set(result["matched_keywords"]) >= {"convex", "global"}


def test_essay_partial_and_zero_scores():
    partial = grade_essay(ESSAY, "It is convex.")
    assert partial["score"] == 3.0 and partial["pct"] == 0.6
    empty = grade_essay(ESSAY, "")
    assert empty["score"] == 0.0 and empty["matched_criteria"][0]["evidence"] == ""


def test_find_evidence_context_window():
    text = "x" * 100 + " KEYWORD " + "y" * 100
    ev = find_evidence(text, "keyword")
    assert len(ev) < len(text) and ev.startswith("...") and ev.endswith("...")


def test_compute_scores_guards_empty_sections():
    scores = compute_scores([], [])
    assert scores["final_score"] == 0.0
    assert scores["mcq_pct"] is None and scores["essay_pct"] is None

    only_mcq = compute_scores([grade_mcq(MCQ, "B")], [])
    assert only_mcq["mcq_pct"] == 1.0 and only_mcq["essay_pct"] is None
    assert only_mcq["final_score"] == 1.0

    mixed = compute_scores([grade_mcq(MCQ, "B")], [grade_essay(ESSAY, "It is convex.")])
    assert mixed["final_score"] == pytest.approx((1.0 + 0.6) / 2)
