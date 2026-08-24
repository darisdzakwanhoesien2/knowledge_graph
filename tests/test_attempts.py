import pytest

from core import attempts as A
from core import packages as P


@pytest.fixture()
def snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "DATABASE_DIR", tmp_path / "database")
    monkeypatch.setattr(A, "RESULTS_DIR", tmp_path / "results")
    pkg = P.new_package(subject="subj", title="Snap Quiz")
    pkg["version"] = 3
    P.add_mcq(pkg, "2+2?", {"A": "3", "B": "4"}, "B", node_links=["Convexity"])
    P.add_essay(pkg, "Explain x.", ["x"],
                [{"keyword": "x", "weight": 2}], total_points=2)
    return {**pkg, "content_hash": "deadbeef", "status": "published"}


def test_submit_attempt_persists_and_grades(snapshot):
    record = A.submit_attempt(
        user={"external_key": "u1", "display_name": "Ada"},
        pkg_snapshot=snapshot,
        answers_mcq={snapshot["mcqs"][0]["id"]: "B"},
        answers_essay={snapshot["essay"][0]["id"]: "x marks the spot"},
    )
    stored = A.load_attempt(record["attempt_id"])
    assert stored is not None and stored["package_version"] == 3
    assert stored["package_content_hash"] == "deadbeef"

    mcq_resp = next(r for r in stored["responses"] if r["question_kind"] == "mcq")
    essay_resp = next(r for r in stored["responses"] if r["question_kind"] == "essay")
    assert mcq_resp["score"] == 1.0
    assert essay_resp["score"] == 2.0
    assert essay_resp["matched_criteria"][0]["matched"] is True
    assert stored["scores"]["final_score"] == 1.0


def test_attempt_provenance_and_listing(snapshot):
    A.submit_attempt(user={"display_name": "Bob"}, pkg_snapshot=snapshot,
                     answers_mcq={}, answers_essay={"any": "nothing here"})
    entries = A.list_attempts()
    assert len(entries) == 1
    rec = A.load_attempt(entries[0]["attempt_id"])
    assert rec["user"]["display_name"] == "Bob"
    assert rec["subject"] == "subj"
    assert rec["responses"][0]["node_links"] == ["Convexity"]


def test_csv_export_contains_response_rows_and_evidence(snapshot):
    A.submit_attempt(user={"display_name": "Ada"}, pkg_snapshot=snapshot,
                     answers_mcq={snapshot["mcqs"][0]["id"]: "B"},
                     answers_essay={snapshot["essay"][0]["id"]: "x"})
    csv_text = A.attempts_csv()
    lines = csv_text.strip().splitlines()
    header = lines[0]
    assert len(lines) == 3
    for column in ("attempt_id", "matched_criteria", "final_score_pct",
                   "correct_option", "package", "version"):
        assert column in header

    data_lines = [line.split(",") for line in lines[1:]]
    cols = header.split(",")
    evidence_col = cols.index("matched_criteria")
    assert any(row[evidence_col] == "x" for row in data_lines)


def test_empty_answers_still_grade_to_zero(snapshot):
    record = A.submit_attempt(user={}, pkg_snapshot=snapshot,
                              answers_mcq={}, answers_essay={})
    scores = record["scores"]
    assert scores["mcq_score"] == 0.0 and scores["essay_score"] == 0.0
    assert scores["final_score"] == 0.0
