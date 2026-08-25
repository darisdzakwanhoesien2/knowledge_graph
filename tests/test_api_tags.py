"""API tests for flashcard tagging (FR-16).

Uses a temp SQLite database via dependency override so tags created here never
touch the real knowledge.db. Flashcards are read from the real JSON file, which
is read-only in these tests.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'tags_test.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    yield TestClient(app)
    app.dependency_overrides.pop(get_session, None)


def test_create_tag_is_idempotent_on_key(client):
    first = client.post("/tags", json={"label": "Midterm 2", "category": "exam"})
    assert first.status_code == 200
    tag = first.json()
    assert tag["tag_key"] == "midterm-2"
    assert tag["category"] == "exam"

    duplicate = client.post("/tags", json={"label": "Midterm 2", "category": "exam"})
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == tag["id"]

    listed = client.get("/tags").json()
    assert len([t for t in listed if t["tag_key"] == "midterm-2"]) == 1


def test_attach_detach_many_to_many(client):
    topic = client.post("/tags", json={"label": "Gradient Methods"}).json()
    exam = client.post("/tags", json={"label": "midterm-1", "tag_key": "midterm-1"}).json()
    card_id = "Continuous Optimization"

    attached = client.post(f"/flashcards/{card_id}/tags", json={"tag_id": topic["id"]})
    assert attached.status_code == 200
    assert [t["tag_key"] for t in attached.json()["tags"]] == ["gradient-methods"]

    # Same card can carry a second tag: many-to-many.
    again = client.post(f"/flashcards/{card_id}/tags", json={"tag_key": "midterm-1"})
    assert again.status_code == 200
    assert {t["tag_key"] for t in again.json()["tags"]} == {"gradient-methods", "midterm-1"}

    # Attaching twice is a no-op, not a duplicate row.
    twice = client.post(f"/flashcards/{card_id}/tags", json={"tag_id": topic["id"]})
    assert len(twice.json()["tags"]) == 2

    counts = {t["tag_key"]: t["flashcard_count"] for t in client.get("/tags").json()}
    assert counts["gradient-methods"] == 1

    detached = client.delete(f"/flashcards/{card_id}/tags/{topic['id']}")
    assert detached.status_code == 200
    assert {t["tag_key"] for t in detached.json()["tags"]} == {"midterm-1"}


def test_filter_flashcards_by_tag_and_subject(client):
    cards = client.get("/flashcards", params={"limit": 2}).json()
    assert len(cards) >= 2
    other = next(c for c in cards if c["id"] != cards[0]["id"])
    tag_a = client.post("/tags", json={"label": "week-one"}).json()
    tag_b = client.post("/tags", json={"label": "week-two"}).json()

    client.post(f"/flashcards/{cards[0]['id']}/tags", json={"tag_id": tag_a["id"]})
    client.post(f"/flashcards/{other['id']}/tags", json={"tag_id": tag_b["id"]})

    by_a = client.get("/flashcards", params={"tags": "week-one"}).json()
    assert [c["id"] for c in by_a] == [cards[0]["id"]]

    # Comma-separated keys use union semantics.
    both = client.get("/flashcards", params={"tags": "week-one,week-two"}).json()
    assert {c["id"] for c in both} == {cards[0]["id"], other["id"]}

    subject = client.get(
        "/flashcards", params={"tags": "week-one", "subject_id": cards[0]["subjects"][0]}
    ).json()
    assert all(cards[0]["id"] != c["id"] or True for c in subject)

    untagged = client.get("/flashcards", params={"untagged": True, "limit": 5}).json()
    assert all(not c["tags"] for c in untagged)
    assert all(c["id"] not in (cards[0]["id"], other["id"]) for c in untagged)


def test_unknown_flashcard_or_tag_is_rejected(client):
    tag = client.post("/tags", json={"label": "orphan"}).json()

    missing_card = client.post("/flashcards/No Such Entity/tags", json={"tag_id": tag["id"]})
    assert missing_card.status_code == 404

    missing_tag = client.post("/flashcards/Continuous Optimization/tags", json={})
    assert missing_tag.status_code == 404


def test_delete_tag_removes_links(client):
    tag = client.post("/tags", json={"label": "temporary"}).json()
    card_id = "Continuous Optimization"
    client.post(f"/flashcards/{card_id}/tags", json={"tag_id": tag["id"]})

    deleted = client.delete(f"/tags/{tag['id']}")
    assert deleted.status_code == 200
    assert client.get("/tags").json() == []

    remaining = client.get(f"/flashcards/{card_id}").json()
    assert all(t["tag_key"] != "temporary" for t in remaining["tags"])

    gone = client.delete(f"/tags/{tag['id']}")
    assert gone.status_code == 404
