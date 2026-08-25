"""API tests for the upload system (docs/UPLOAD_SYSTEM_PLAN.md).

Both flows run hermetically: package files go to a temp DATABASE_DIR, subject
folders to a temp json_nodes root, the registry to a temp file, and the
pipeline chain is replaced by a recording fake so real derived data
(merged_graph.json, flashcards.json, knowledge.db) is never touched.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
import app.api.packages as packages_api  # noqa: E402
import app.api.subjects as subjects_api  # noqa: E402
import core.graph_content as graph_content  # noqa: E402
import core.packages as packages_core  # noqa: E402
import core.pipelines as pipelines_core  # noqa: E402
import core.registry as registry_core  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    database_dir = tmp_path / "database"
    json_nodes = tmp_path / "json_nodes"
    graphs_dir = tmp_path / "graphs"
    registry_file = tmp_path / "registry.json"
    database_dir.mkdir()
    json_nodes.mkdir()

    monkeypatch.setattr(packages_core, "DATABASE_DIR", database_dir)
    monkeypatch.setattr(subjects_api, "BASE_DIR", tmp_path)
    monkeypatch.setattr(graph_content, "GRAPHS_DIR", graphs_dir)
    monkeypatch.setattr(registry_core, "REGISTRY_FILE", registry_file)
    registry_file.write_text(
        '{"built_at": null, "subjects": {"test_subject": {"subject_id": "test_subject"}}}'
    )

    calls = []

    def fake_chain():
        calls.append(1)
        graphs_dir.mkdir(parents=True, exist_ok=True)
        (graphs_dir / "merged_graph.json").write_text(
            '{"nodes": {"A": {"metadata": {"subjects": ["test_subject"]}}}, "edges": [],'
            ' "metadata": {"subjects": {"test_subject": {}}}}'
        )
        return {"ok": True, "steps": [{"step": "fake", "ok": True, "detail": ""}]}

    monkeypatch.setattr(pipelines_core, "run_pipeline_chain", fake_chain)
    monkeypatch.setattr(pipelines_core, "graph_counts", lambda: {"nodes": 1, "edges": 0, "subjects": 1})
    monkeypatch.setattr(subjects_api, "_chain_calls", calls, raising=False)

    engine = create_engine(f"sqlite:///{tmp_path/'tags.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    yield TestClient(app)
    app.dependency_overrides.pop(get_session, None)


# ------------------------------------------------------------- exam content

def _create_package(client):
    response = client.post(
        "/packages",
        json={"subject": "test_subject", "title": "Upload Flow"},
    )
    assert response.status_code == 200
    return response.json()


def test_create_package_requires_known_subject(client):
    bad = client.post("/packages", json={"subject": "nope", "title": "X"})
    assert bad.status_code == 422


def test_partial_upload_appends_and_invalid_upload_fails_closed(client):
    created = _create_package(client)
    pid = created["package_id"]

    good = client.post(f"/packages/{pid}/content", json={
        "mcqs": [{"question": "What is 2+2?", "options": {"A": "3", "B": "4"}, "correct_option": "b"}],
    })
    assert good.status_code == 200
    body = good.json()
    assert body["mcq_count"] == 1
    assert body["package_key"] == f"test_subject/{pid}"

    stored = packages_core.load_package("test_subject", pid)
    assert stored["mcqs"][0]["options"]["B"] == "4"  # lowercase key normalized

    invalid = client.post(f"/packages/{pid}/content", json={
        "mcqs": [{"question": "Broken?", "options": {"A": "x"}, "correct_option": "A"}],
    })
    assert invalid.status_code == 422
    errors = invalid.json()["detail"]["errors"]
    assert any("options" in e["message"] or "correct_option" in e["message"] for e in errors)

    after = packages_core.load_package("test_subject", pid)
    assert len(after["mcqs"]) == 1  # failed write touched nothing
    assert after == stored


def test_full_package_upload_is_server_owned_and_replacing(client):
    created = _create_package(client)
    pid = created["package_id"]

    response = client.post(f"/packages/{pid}/content", json={
        "schema_version": 1,
        "package_key": "evil_subject/spoofed",
        "subject": "evil_subject",
        "package_id": "spoofed",
        "status": "published",
        "title": "Bulk Imported",
        "mcqs": [
            {"question": "Q1", "options": {"A": "1", "B": "2"}, "correct_option": "A"},
            {"question": "Q2", "options": {"A": "3", "B": "4"}, "correct_option": "B"},
        ],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["package_key"] == f"test_subject/{pid}"
    assert body["mcq_count"] == 2  # full mode replaced the earlier draft content

    stored = packages_core.load_package("test_subject", pid)
    assert stored["status"] == "draft"  # upload never publishes
    assert stored["title"] == "Bulk Imported"
    assert stored["package_key"] == f"test_subject/{pid}"


def test_unknown_package_is_404_with_hint(client):
    miss = client.post("/packages/never_seen/content", json={"mcqs": []})
    assert miss.status_code == 404
    assert "POST /packages" in miss.json()["detail"]


def test_publish_then_identical_publish_is_same_version(client):
    created = _create_package(client)
    pid = created["package_id"]
    client.post(f"/packages/{pid}/content", json={
        "mcqs": [{"question": "Q", "options": {"A": "1", "B": "2"}, "correct_option": "A"}],
    })

    first = client.post(f"/packages/{pid}/publish")
    assert first.status_code == 200
    assert first.json()["version"] == 1

    again = client.post(f"/packages/{pid}/publish")
    assert again.status_code == 200
    assert again.json()["version"] == 1  # identical content: no-op re-publish

    versions = client.get(f"/packages/{pid}/versions").json()
    assert [v["version"] for v in versions] == [1]


def test_upload_into_published_auto_starts_next_draft(client):
    created = _create_package(client)
    pid = created["package_id"]
    client.post(f"/packages/{pid}/content", json={
        "mcqs": [{"question": "Q", "options": {"A": "1", "B": "2"}, "correct_option": "A"}],
    })
    client.post(f"/packages/{pid}/publish")

    followup = client.post(f"/packages/{pid}/content", json={
        "essay": [{"prompt": "Explain.", "expected_keywords": ["because"]}],
    })
    assert followup.status_code == 200
    assert followup.json()["version"] == 2

    versions = client.get(f"/packages/{pid}/versions").json()
    assert [v["version"] for v in versions] == [1]  # published snapshot untouched
    working = packages_core.load_package("test_subject", pid)
    assert working["status"] == "draft"
    assert len(working["essay"]) == 1


# ------------------------------------------------------------ graph content

def _upload(client, subject_id, filename, content: bytes, **params):
    data = {"replace": "true"} if params.get("replace") else {}
    return client.post(
        f"/subjects/{subject_id}/content",
        params=params,
        data=data,
        files={"file": (filename, content, "application/json")},
    )


def test_subject_create_and_upload_runs_pipeline_once(client):
    created = client.post("/subjects", json={"subject_id": "fresh_subject"})
    assert created.status_code == 200

    dup = client.post("/subjects", json={"subject_id": "fresh_subject"})
    assert dup.status_code == 409

    ugly = client.post("/subjects", json={"subject_id": "Not A Slug!"})
    assert ugly.status_code == 422

    listed = client.get("/subjects").json()
    assert "fresh_subject" in [s["id"] for s in listed]

    upload = _upload(
        client, "fresh_subject", "batch1.json",
        b'[{"entity":"Alpha","definition":"First."},{"entity":"Beta","definition":"Second."}]',
    )
    assert upload.status_code == 200, upload.text
    body = upload.json()
    assert body["status"] == "created"
    assert body["counts"]["nodes"] >= 1
    assert body["pipeline"]["ok"] is True

    files = client.get("/subjects/fresh_subject/content").json()["files"]
    assert [f["filename"] for f in files] == ["batch1.json"]
    assert files[0]["content_hash"]


def test_shape_error_never_touches_disk(client):
    bad = _upload(client, "test_subject", "broken.json", b'{"neither": "entity nor graph payload"}')
    assert bad.status_code == 422

    empty = _upload(client, "test_subject", "empty_list.json", b'[{"no_entity_key": true}]')
    assert empty.status_code == 422

    parse_err = _upload(client, "test_subject", "worse.json", b"{not json")
    assert parse_err.status_code == 422

    subject_dir = subjects_api.BASE_DIR / "json_nodes" / "test_subject"
    assert not subject_dir.exists() or not list(subject_dir.glob("*.json"))


def test_duplicate_filename_replace_and_noop(client):
    payload = b'[{"entity":"Alpha","definition":"First."}]'
    assert _upload(client, "test_subject", "same.json", payload).status_code == 200

    noop = _upload(client, "test_subject", "same.json", payload)
    assert noop.status_code == 200
    assert noop.json()["status"] == "noop"

    conflict = _upload(client, "test_subject", "same.json", b'[{"entity":"Different"}]')
    assert conflict.status_code == 409

    replaced = _upload(client, "test_subject", "same.json", b'[{"entity":"Different"}]', replace=True)
    assert replaced.status_code == 200
    assert replaced.json()["status"] == "replaced"


def test_upload_surfaces_cross_subject_and_relation_warnings(client):
    graphs_dir = graph_content.GRAPHS_DIR
    graphs_dir.mkdir(parents=True, exist_ok=True)
    (graphs_dir / "merged_graph.json").write_text(
        '{"nodes": {"Shared Concept": {"metadata": {"subjects": ["other_subject"]}},'
        ' "Known Target": {}}, "edges": [], "metadata": {"subjects": {}}}'
    )
    payload = (
        '[{"entity":"Local","definition":"d",'
        ' "relations":[{"type":"related_to","target":"Nowhere Node"}]},'
        '{"entity":"Shared Concept"}]'
    ).encode()
    response = _upload(client, "test_subject", "warned.json", payload)
    assert response.status_code == 200
    warnings = response.json()["warnings"]
    assert any("'Shared Concept' already exists" in w["message"] for w in warnings)
    assert any("'Nowhere Node'" in w["message"] for w in warnings)


def test_oversized_upload_rejected_before_parse(client, monkeypatch):
    monkeypatch.setattr(subjects_api, "MAX_UPLOAD_BYTES", 16)
    huge = b'["' + b"x" * 64 + b'"]'
    response = _upload(client, "test_subject", "huge.json", huge)
    assert response.status_code == 413


def test_curator_token_gates_write_endpoints(client, monkeypatch):
    monkeypatch.setenv("KG_CURATOR_TOKEN", "sekrit")
    denied = client.post("/packages", json={"subject": "test_subject", "title": "T"})
    assert denied.status_code == 401
    denied_upload = _upload(client, "test_subject", "gated.json", b"[]")
    assert denied_upload.status_code == 401

    allowed = client.post(
        "/packages",
        json={"subject": "test_subject", "title": "T"},
        headers={"X-Curator-Token": "sekrit"},
    )
    assert allowed.status_code == 200


def test_orphaned_tags_reported_after_upload(client):
    from app.models.sqlmodel import FlashcardTag

    session = next(app.dependency_overrides[get_session]())
    session.add(FlashcardTag(flashcard_id="vanished_entity_zz", tag_id="unused"))
    session.commit()

    upload = _upload(
        client, "test_subject", "renames.json",
        b'[{"entity":"Survivor","definition":"still here"}]',
    )
    assert upload.status_code == 200
    assert "vanished_entity_zz" in upload.json()["detached_tags"]
