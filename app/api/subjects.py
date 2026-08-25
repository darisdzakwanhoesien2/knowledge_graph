import re
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..db import get_session
from ..models.domain import Subject
from ..security import require_curator
from core import graph_content, pipelines
from core.registry import list_subjects as core_list_subjects
from core.registry import build_registry, load_registry, save_registry
from core.store import BASE_DIR, content_hash, load_json, write_json

router = APIRouter(prefix="/subjects", tags=["subjects"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # UPLOAD_SYSTEM_PLAN §3: reject huge files pre-parse


class SubjectCreate(BaseModel):
    subject_id: str


@router.get("", response_model=List[Subject])
async def list_subjects() -> List[Subject]:
    """List all subjects in the knowledge graph."""
    return [
        Subject(id=sid, name=sid.replace("_", " ").title())
        for sid in core_list_subjects()
    ]


@router.get("/{subject_id}", response_model=Subject)
async def get_subject(subject_id: str) -> Subject:
    """Get a subject by ID."""
    subjects = core_list_subjects()
    match = [s for s in subjects if s == subject_id]
    if not match:
        raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found")
    return Subject(id=match[0], name=match[0].replace("_", " ").title())


@router.post("", dependencies=[Depends(require_curator)])
async def create_subject(payload: SubjectCreate):
    """Register a new subject folder (json_nodes/<subject_id>/)."""
    subject_id = (payload.subject_id or "").strip()
    if not re.fullmatch(r"[a-z0-9]+(_[a-z0-9]+)*", subject_id):
        raise HTTPException(
            status_code=422,
            detail="subject_id must be snake_case ([a-z0-9_] with no leading/trailing underscore)",
        )
    subject_dir = BASE_DIR / "json_nodes" / subject_id
    if subject_dir.exists():
        raise HTTPException(status_code=409, detail=f"Subject {subject_id} already exists")
    subject_dir.mkdir(parents=True)
    # Rebuild the registry in-process so the new subject is immediately visible.
    save_registry(build_registry(BASE_DIR / "json_nodes"))
    return {"created": subject_id}


@router.get("/{subject_id}/content")
async def list_subject_content(subject_id: str):
    """List the files backing a subject, with content hashes."""
    _require_known_subject(subject_id)
    subject_dir = BASE_DIR / "json_nodes" / subject_id
    files = []
    if subject_dir.exists():
        for f in sorted(subject_dir.glob("*.json")):
            raw = f.read_bytes()
            files.append({
                "filename": f.name,
                "media_type": "application/json",
                "content_hash": content_hash(raw),
                "bytes": len(raw),
                "imported_at": None,
            })
        # Fill imported_at from the registry when available (set at build time).
        entry = load_registry().get("subjects", {}).get(subject_id) or {}
        known = {d.get("filename"): d.get("imported_at") for d in entry.get("source_documents", [])}
        for item in files:
            item["imported_at"] = known.get(item["filename"])
    return {"subject_id": subject_id, "files": files}


@router.post("/{subject_id}/content", dependencies=[Depends(require_curator)])
async def upload_subject_content(
    subject_id: str,
    file: UploadFile = File(...),
    replace: bool = Form(False),
    session=Depends(get_session),
):
    """Upload one ADDING_DATA.md-shaped JSON file into a subject and run the pipeline chain.

    Fails closed: shape errors never touch disk. Warnings (duplicate entities,
    unresolved relation targets) are returned but don't block.
    """
    _require_known_subject(subject_id)

    size = getattr(file, "size", None)
    if size is not None and size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit")

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit")

    original_name = (file.filename or "").strip()
    safe_name = re.sub(r"[^\w.\- ]+", "_", original_name).strip() or "upload.json"
    if not safe_name.lower().endswith(".json"):
        safe_name += ".json"

    import json

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}")

    try:
        validation = graph_content.validate_graph_file(payload, subject_id)
    except graph_content.GraphFileError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    subject_dir = BASE_DIR / "json_nodes" / subject_id
    target = subject_dir / safe_name

    status = "created"
    if target.exists():
        def canonical(data) -> str:
            return content_hash(json.dumps(data, sort_keys=True))

        if canonical(payload) == canonical(load_json(target)):
            return {
                "status": "noop",
                "file": safe_name,
                "detail": "identical content already exists; nothing written",
            }
        if not replace:
            raise HTTPException(
                status_code=409,
                detail=f"{safe_name} already exists for {subject_id}; resend with replace=true to overwrite",
            )
        status = "replaced"

    write_json(target, payload)

    result = pipelines.run_pipeline_chain()
    graph_content.reset_caches()

    counts = pipelines.graph_counts() if result["ok"] else None
    detached_tags = _detached_tags(session) if result["ok"] else []

    body = {
        "status": status,
        "subject_id": subject_id,
        "file": safe_name,
        "entities": validation["entities"],
        "warnings": validation["warnings"],
        "pipeline": result,
        "counts": counts or {},
        "detached_tags": detached_tags,
    }
    if not result["ok"]:
        return JSONResponse(status_code=500, content={
            **body,
            "detail": "File was stored but the pipeline chain failed; see pipeline steps.",
        })
    return body


def _detached_tags(session) -> list:
    """FLASHCARD_TAG rows whose flashcard vanished from the regenerated cards.

    Tags key on a card's stable entity string so pipeline re-runs are safe, but
    an upload that renames or removes an entity orphans its tags — surfaced
    here instead of failing silently (UPLOAD_SYSTEM_PLAN §1).
    """
    from sqlmodel import select

    from ..models.sqlmodel import FlashcardTag

    live_cards = graph_content.orphaned_tagged_entities()
    joins = session.exec(select(FlashcardTag)).all()
    return sorted({join.flashcard_id for join in joins if join.flashcard_id not in live_cards})


def _require_known_subject(subject_id: str) -> None:
    subjects = core_list_subjects()
    # A freshly created empty subject may not be in a stale cached registry yet;
    # accept it if its folder exists.
    if subject_id not in subjects and not (BASE_DIR / "json_nodes" / subject_id).exists():
        raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found")
