"""Import the repository's JSON content into the SQLModel database.

The importer is deliberately deterministic: IDs are derived from source keys,
so running it repeatedly updates the same rows rather than creating duplicates.
JSON remains the authoritative rollback/source format.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from app.models.sqlmodel import (
    Attempt,
    Concept,
    ConceptRelation,
    PackageVersion,
    Question,
    Subject,
    ValidationIssue,
)

ROOT = Path(__file__).resolve().parents[1]


def stable_id(namespace: str, key: str) -> str:
    return hashlib.sha256(f"{namespace}:{key}".encode()).hexdigest()[:32]


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def upsert(session: Session, item: Any, model: type[Any]) -> None:
    existing = session.get(model, item.id)
    if existing is None:
        session.add(item)
    else:
        for key, value in item.model_dump().items():
            setattr(existing, key, value)


def migrate(database: Path) -> dict[str, int]:
    registry = load(ROOT / "data/registry/registry.json")
    graph = load(ROOT / "data/graphs/merged_graph.json")
    report = load(ROOT / "data/reports/quality_report.json")
    engine = create_engine(f"sqlite:///{database}")
    SQLModel.metadata.create_all(engine)
    counts = {name: 0 for name in ("subjects", "concepts", "relations", "packages", "questions", "attempts", "validation_issues")}

    graph_subjects: dict[str, set[str]] = {}
    for node in graph["nodes"].values():
        for subject_id in node.get("metadata", {}).get("subjects", []):
            graph_subjects.setdefault(subject_id, set()).add(subject_id)

    with Session(engine) as session:
        for key, raw in registry.get("subjects", {}).items():
            subject_id = raw.get("subject_id", key)
            upsert(session, Subject(id=subject_id, name=raw.get("display_name", key)), Subject)
            counts["subjects"] += 1

        concept_ids: dict[str, str] = {}
        for name, raw in graph.get("nodes", {}).items():
            concept_id = stable_id("concept", name)
            concept_ids[name] = concept_id
            subjects = raw.get("metadata", {}).get("subjects", [])
            subject_id = subjects[0] if subjects else None
            if subject_id and session.get(Subject, subject_id) is None:
                upsert(session, Subject(id=subject_id, name=subject_id), Subject)
            upsert(session, Concept(id=concept_id, subject_id=subject_id, name=name, definition=raw.get("definition") or raw.get("description")), Concept)
            counts["concepts"] += 1

        for edge in graph.get("edges", []):
            source, target = concept_ids.get(edge.get("source")), concept_ids.get(edge.get("target"))
            if not source or not target:
                continue
            relation_key = f"{source}:{target}:{edge.get('type', 'related_to')}"
            upsert(session, ConceptRelation(id=stable_id("relation", relation_key), source_concept_id=source, target_concept_id=target, relation_type=edge.get("type", "related_to")), ConceptRelation)
            counts["relations"] += 1

        for package_path in sorted((ROOT / "database").glob("**/package.json")):
            raw = load(package_path)
            package_key = raw.get("package_key") or f"{raw.get('subject', package_path.parent.parent.name)}/{raw.get('package_id', package_path.parent.name)}"
            version = int(raw.get("version", 1))
            version_id = stable_id("package-version", f"{package_key}:v{version}")
            subject_id = raw.get("subject")
            if subject_id and session.get(Subject, subject_id) is None:
                upsert(session, Subject(id=subject_id, name=subject_id), Subject)
            upsert(session, PackageVersion(id=version_id, package_id=package_key, subject_id=subject_id, version=version, status=raw.get("status", "draft"), created_at=timestamp(raw.get("created_at")) or datetime.utcnow()), PackageVersion)
            counts["packages"] += 1
            for section in ("mcqs", "essay"):
                for number, question in enumerate(raw.get(section, [])):
                    question_id = question.get("id") or stable_id("question", f"{package_key}:v{version}:{section}:{number}")
                    essay = question.get("rubric", {})
                    upsert(session, Question(id=question_id, package_version_id=version_id, prompt=question.get("question") or question.get("prompt", ""), kind=question.get("kind", section), difficulty=question.get("difficulty", "medium"), learning_objective=question.get("learning_objective"), slide_reference=json.dumps(question.get("slide_refs", [])), correct_answer_key=question.get("correct_option"), essay_keywords=json.dumps(question.get("expected_keywords", [])), essay_rubric=json.dumps(essay)), Question)
                    counts["questions"] += 1

        for number, raw in enumerate(report.get("issues", [])):
            issue_key = json.dumps(raw, sort_keys=True) + f":{number}"
            upsert(session, ValidationIssue(id=stable_id("validation", issue_key), type=raw.get("type", "quality_issue"), severity=raw.get("severity", "warning"), message=raw.get("message", ""), location=raw.get("location"), entity_id=raw.get("entity_id"), created_at=timestamp(report.get("built_at")) or datetime.utcnow()), ValidationIssue)
            counts["validation_issues"] += 1

        session.commit()

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "knowledge.db")
    args = parser.parse_args()
    counts = migrate(args.database)
    print("Migration complete: " + ", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()
