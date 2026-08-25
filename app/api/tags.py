"""Flashcard tagging API (FR-16).

Tags live in SQLite (tag, flashcard_tag); flashcards stay in
data/flashcards/flashcards.json and are identified by their stable entity key,
so regenerating the JSON never orphans tag links.
"""
import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from ..db import get_session
from ..models.sqlmodel import FlashcardTag, Tag
from core.learning_links import load_flashcards

router = APIRouter(tags=["tags"])


class TagRead(BaseModel):
    id: str
    tag_key: str
    label: str
    category: str
    flashcard_count: int = 0


class TagCreate(BaseModel):
    label: str
    category: str = "topic"
    tag_key: Optional[str] = None


class FlashcardRead(BaseModel):
    id: str
    domain: str
    subjects: List[str]
    front: str
    back: str
    tags: List[TagRead]


class AttachRequest(BaseModel):
    tag_id: Optional[str] = None
    tag_key: Optional[str] = None


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug


def _tag_read(tag: Tag, counts) -> TagRead:
    return TagRead(
        id=tag.id,
        tag_key=tag.tag_key,
        label=tag.label,
        category=tag.category,
        flashcard_count=counts.get(tag.id, 0),
    )


def _tags_by_card(session) -> dict:
    """Map flashcard_id -> [Tag] in one query per table."""
    joins = session.exec(select(FlashcardTag)).all()
    tags = {t.id: t for t in session.exec(select(Tag)).all()}
    mapping: dict = {}
    for join in joins:
        tag = tags.get(join.tag_id)
        if tag:
            mapping.setdefault(join.flashcard_id, []).append(_tag_read(tag, {}))
    return mapping


@router.get("/tags", response_model=List[TagRead])
async def list_tags(session=Depends(get_session)):
    """List all tags with usage counts."""
    tags = session.exec(select(Tag)).all()
    counts: dict = {}
    for join in session.exec(select(FlashcardTag)).all():
        counts[join.tag_id] = counts.get(join.tag_id, 0) + 1
    return sorted((_tag_read(t, counts) for t in tags), key=lambda t: (t.category, t.label))


@router.post("/tags", response_model=TagRead)
async def create_tag(payload: TagCreate, session=Depends(get_session)):
    """Create a tag; idempotent on tag_key so re-submitting returns the existing tag."""
    if not payload.label.strip():
        raise HTTPException(status_code=422, detail="Tag label must not be empty")
    key = slugify(payload.tag_key or payload.label)
    if not key:
        raise HTTPException(status_code=422, detail="Tag key must not be empty")
    existing = session.exec(select(Tag).where(Tag.tag_key == key)).first()
    if existing:
        return _tag_read(existing, {})
    tag = Tag(id=str(uuid.uuid4()), tag_key=key, label=payload.label.strip(), category=payload.category or "topic")
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return _tag_read(tag, {})


@router.delete("/tags/{tag_id}")
async def delete_tag(tag_id: str, session=Depends(get_session)):
    """Delete a tag and its flashcard links."""
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")
    for join in session.exec(select(FlashcardTag).where(FlashcardTag.tag_id == tag_id)).all():
        session.delete(join)
    session.delete(tag)
    session.commit()
    return {"deleted": tag.tag_key}


@router.get("/flashcards", response_model=List[FlashcardRead])
async def list_flashcards(
    subject_id: str = "",
    q: str = "",
    tags: str = "",
    untagged: bool = False,
    limit: int = 0,
    session=Depends(get_session),
):
    """Browse flashcards with their tags attached.

    Filters: subject_id (exact), q (substring on entity/front/back),
    tags (comma-separated tag keys; a card matches when it carries ANY of them).
    """
    cards = _tags_by_card(session)
    selected_keys = {slugify(k) for k in tags.split(",") if k.strip()} if tags else set()
    key_to_id = {t.tag_key: t.id for t in session.exec(select(Tag)).all()}

    result = []
    for entity, card in load_flashcards().items():
        card_tags = cards.get(entity, [])
        subjects = card.get("subjects", [])
        if subject_id and subject_id not in subjects:
            continue
        if untagged and card_tags:
            continue
        if selected_keys:
            card_tag_ids = {c_tag.id for c_tag in card_tags}
            wanted = {key_to_id[k] for k in selected_keys if k in key_to_id}
            if not card_tag_ids & wanted:
                continue
        if q:
            haystack = " ".join([entity, card.get("front", ""), card.get("back", "")]).lower()
            if q.lower() not in haystack:
                continue
        result.append(FlashcardRead(
            id=entity,
            domain=card.get("domain", ""),
            subjects=subjects,
            front=card.get("front", ""),
            back=card.get("back", ""),
            tags=sorted(card_tags, key=lambda t: (t.category, t.label)),
        ))
    if limit > 0:
        result = result[:limit]
    return result


@router.post("/flashcards/{flashcard_id}/tags", response_model=FlashcardRead)
async def attach_tag(flashcard_id: str, payload: AttachRequest, session=Depends(get_session)):
    """Attach a tag to a flashcard. Idempotent: attaching twice is a no-op."""
    card = load_flashcards().get(flashcard_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Flashcard {flashcard_id} not found")
    tag = None
    if payload.tag_id:
        tag = session.get(Tag, payload.tag_id)
    elif payload.tag_key:
        tag = session.exec(select(Tag).where(Tag.tag_key == slugify(payload.tag_key))).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    existing = session.exec(
        select(FlashcardTag).where(
            FlashcardTag.flashcard_id == flashcard_id,
            FlashcardTag.tag_id == tag.id,
        )
    ).first()
    if not existing:
        session.add(FlashcardTag(flashcard_id=flashcard_id, tag_id=tag.id))
        session.commit()
    return await get_flashcard(flashcard_id, session)


@router.delete("/flashcards/{flashcard_id}/tags/{tag_id}", response_model=FlashcardRead)
async def detach_tag(flashcard_id: str, tag_id: str, session=Depends(get_session)):
    """Remove a tag from a flashcard."""
    join = session.exec(
        select(FlashcardTag).where(
            FlashcardTag.flashcard_id == flashcard_id,
            FlashcardTag.tag_id == tag_id,
        )
    ).first()
    if join:
        session.delete(join)
        session.commit()
    return await get_flashcard(flashcard_id, session)


@router.get("/flashcards/{flashcard_id}", response_model=FlashcardRead)
async def get_flashcard(flashcard_id: str, session=Depends(get_session)):
    """One flashcard with its tags."""
    card = load_flashcards().get(flashcard_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Flashcard {flashcard_id} not found")
    cards = _tags_by_card(session)
    return FlashcardRead(
        id=flashcard_id,
        domain=card.get("domain", ""),
        subjects=card.get("subjects", []),
        front=card.get("front", ""),
        back=card.get("back", ""),
        tags=cards.get(flashcard_id, []),
    )
