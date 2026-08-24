# Product Requirements Document

## Product

**Knowledge Graph Learning Studio** is a local-first learning tool that turns subject-scoped JSON notes into a navigable knowledge graph and retrieval-practice flashcards.

## Problem

Learners have concepts spread across files and subjects, but lack a reliable way to see relationships, find a path between ideas, identify incomplete notes, and review knowledge. Manual curation is slow and generated learning material is difficult to trace back to its source.

## Goals

- Make a learner's knowledge base searchable and graph-navigable.
- Show how concepts connect, including shortest paths and local neighborhoods.
- Preserve subject and source-file provenance for every node and edge.
- Turn defined concepts into browsable flashcards.
- Surface incomplete or low-quality nodes before they affect learning.
- Keep the MVP local-first, reproducible, and usable without a hosted backend.

## Non-goals

- Replacing a general-purpose note-taking application.
- Real-time multi-user collaboration or permissions in the MVP.
- Automatic factual validation of source material.
- Rendering the entire graph as the primary learning workflow at very large scale.
- A public REST API or production database in the current release.

## Users and Use Cases

### Independent learner

- Explore a subject and its central concepts.
- Open a node to read its definition, description, properties, subjects, and neighbors.
- Find a shortest connection between two concepts.
- Review flashcards by search or subject.

### Knowledge-base curator

- Add JSON files under `json_nodes/<subject_id>/`.
- Validate and normalize source data.
- Rebuild graph, flashcard, and subject-index artifacts.
- Find nodes missing metadata or definitions and clean them up.

## MVP Scope

### Ingestion and build

- Support full graph payloads, single-entity payloads, and lists of entities.
- Normalize entity names and relation records.
- Merge duplicate nodes and edges deterministically.
- Attach subject IDs and source filenames as provenance.
- Write generated artifacts to `data/`.

### Exploration

- Interactive graph overview with filtering.
- Global narrative showing central concepts and suggested structure.
- Node detail view with metadata and neighboring concepts.
- Shortest-path lookup between two valid nodes.

### Learning

- Generate flashcards from node content.
- Search and paginate flashcards.
- Filter flashcards by subject.

### Quality

- Validate graph metadata and supported input shapes.
- List incomplete nodes and provide enough context to correct their source files.
- Ignore malformed records safely and report actionable failures where appropriate.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
| --- | --- | --- | --- |
| FR-1 | Merge supported JSON inputs | Must | A build produces one graph containing valid nodes and typed edges from all subject folders. |
| FR-2 | Preserve provenance | Must | Each node identifies contributing subjects and source files. |
| FR-3 | Explore graph | Must | A user can inspect the graph and filter the displayed content. |
| FR-4 | Inspect a node | Must | A user can view definition, description, properties, subjects, and neighbors. |
| FR-5 | Find connections | Must | A user can select two nodes and see a shortest path or a clear no-path result. |
| FR-6 | Generate and browse flashcards | Must | Defined nodes can be reviewed as searchable flashcards and grouped by subject. |
| FR-7 | Detect incomplete nodes | Should | The UI identifies nodes missing definitions or required metadata. |
| FR-8 | Reproducible builds | Should | Identical sorted inputs produce equivalent graph content and a build timestamp/metadata record. |

## Non-functional Requirements

- Python 3.10+ and UTF-8 JSON support.
- No network connection required for the local MVP.
- Invalid input records must not silently corrupt valid graph data.
- UI must remain usable on desktop and narrow screens through Streamlit's responsive layout.
- Pipeline output paths and schemas must be documented and stable.
- Graph loading should be cached or optimized before the corpus becomes large enough to cause repeated-session latency.

## Success Metrics

- A new subject can be added and made available after the documented build commands complete successfully.
- At least 95% of defined source entities appear in the merged graph and flashcard artifact, excluding intentionally invalid records.
- A learner can go from a subject to a node, a related node, and a flashcard in under three interactions.
- Every displayed node can be traced to at least one subject and source file.
- Validation failures identify the affected record or node.

## Risks and Open Decisions

- Free-text entity names can create false duplicates; a canonical ID strategy may be needed.
- JSON artifacts are sufficient for the MVP but are not ideal for concurrent writes or multi-hop queries at scale.
- Generated flashcards currently provide retrieval prompts, not scheduling or mastery tracking.
- Future ingestion from PDFs/LLMs requires human review and provenance before publication.

## Roadmap

1. MVP: current JSON pipelines, Streamlit exploration, flashcards, and cleanup.
2. MVP+: schema files, build history, graph diffs, cached loading, and flashcard export.
3. Growth: persistent Postgres or graph storage, API endpoints, authentication, spaced repetition, and human-reviewed assisted ingestion.
