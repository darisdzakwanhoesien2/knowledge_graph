"""API tests for the assessment lifecycle, result review, and remediation context.

Uses a temp database/results dir so published packages and submissions created
here never touch the real data (FR-12, FR-14).
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
import app.api.assessments as assessments_api  # noqa: E402
import core.attempts as attempts_core  # noqa: E402
import core.packages as packages_core  # noqa: E402


USER = {"external_key": "test_user", "display_name": "tester"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    database_dir = tmp_path / "database"
    results_dir = tmp_path / "results"
    monkeypatch.setattr(packages_core, "DATABASE_DIR", database_dir)
    monkeypatch.setattr(attempts_core, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(assessments_api, "PENDING_DIR", results_dir / "pending")

    pkg = packages_core.new_package("test_subject", "Context Test", level="Basics")
    packages_core.add_mcq(
        pkg,
        question="What does 2+2 equal?",
        options={"A": "3", "B": "4", "C": "5"},
        correct_option="B",
        node_links=["Objective Function ($f$)"],
    )
    packages_core.add_mcq(
        pkg,
        question="What does 3+3 equal?",
        options={"A": "6", "B": "7"},
        correct_option="A",
        node_links=["Convexity"],
    )
    packages_core.add_essay(
        pkg,
        prompt="Describe convexity.",
        expected_keywords=["convex"],
    )
    packages_core.save_package(pkg)
    packages_core.publish_package("test_subject", "context_test")

    return TestClient(app)


def _start(client):
    response = client.post(
        "/assessments",
        params={"subject_id": "test_subject", "package_id": "context_test"},
        json=USER,
    )
    assert response.status_code == 200
    return response.json()


def _submit(client, attempt_id, mcq_answers, essay_answers):
    return client.post(
        f"/assessments/{attempt_id}/submit",
        json={"answers_mcq": mcq_answers, "answers_essay": essay_answers},
    )


def test_full_lifecycle_preserves_attempt_and_evidence(client):
    session = _start(client)
    assert session["package_version"] == 1
    snapshot = session["snapshot"]
    assert len(snapshot["mcqs"]) == 2 and len(snapshot["essay"]) == 1

    mcq_ids = [q["id"] for q in snapshot["mcqs"]]
    essay_id = snapshot["essay"][0]["id"]

    # Answer only the first MCQ and the essay; the second MCQ stays unanswered
    # but must still produce a graded response record.
    response = _submit(
        client,
        session["attempt_id"],
        {mcq_ids[0]: "b"},
        {essay_id: "This is about convex sets."},
    )
    assert response.status_code == 200
    record = response.json()

    assert record["attempt_id"] == session["attempt_id"]
    kinds = {r["question_kind"] for r in record["responses"]}
    assert kinds == {"mcq", "essay"}
    unanswered = [r for r in record["responses"]
                  if r["question_kind"] == "mcq" and r["question_id"] == mcq_ids[1]]
    assert unanswered and unanswered[0]["score"] == 0.0
    # Section percentages are averaged: MCQ 1/2 = 0.5, essay 1/1 = 1.0.
    assert record["scores"]["final_score"] == 0.75
    assert not (attempts_core.RESULTS_DIR / "pending" / f"{session['attempt_id']}.json").exists()

    detail = client.get(f"/results/{session['attempt_id']}")
    assert detail.status_code == 200
    assert len(detail.json()["responses"]) == 3


def test_double_submit_is_rejected(client):
    session = _start(client)
    first = _submit(client, session["attempt_id"], {}, {})
    assert first.status_code == 200
    second = _submit(client, session["attempt_id"], {}, {})
    assert second.status_code == 404


def test_history_filters_and_csv(client):
    session = _start(client)
    mcq_id = session["snapshot"]["mcqs"][0]["id"]
    _submit(client, session["attempt_id"], {mcq_id: "B"}, {})

    listed = client.get("/results", params={"learner": "tester"})
    assert listed.status_code == 200
    summaries = listed.json()
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["learner"] == "tester"
    assert summary["subject_id"] == "test_subject"
    assert summary["package_version_id"].endswith("/v1")
    # Only the first MCQ is answered correctly: (0.5 + 0.0) / 2 = 0.25.
    assert summary["percentage"] == 25.0

    miss = client.get("/results", params={"learner": "nobody"})
    assert miss.json() == []

    csv_response = client.get("/results/export/csv", params={"learner": "tester"})
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert session["attempt_id"] in csv_response.text
    assert csv_response.text.count("\n") >= 2


def test_concept_context_supports_remediation(client):
    found = client.get("/concepts/Objective Function ($f$)/context")
    assert found.status_code == 200
    payload = found.json()
    assert payload["exists"] is True
    assert payload["node"] == "Objective Function ($f$)"
    assert isinstance(payload["neighbors"], list)

    missing = client.get("/concepts/No Such Concept/context")
    assert missing.status_code == 200
    assert missing.json()["exists"] is False
