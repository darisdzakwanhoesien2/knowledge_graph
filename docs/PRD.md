# Product Requirements Document

## Product

**Knowledge Graph Learning Studio** is a local-first learning and assessment tool. It turns subject-scoped notes and PDFs into a navigable knowledge graph, flashcards, and versioned question packages, then delivers tests with transparent grading and review.

## Problem

Learning material is distributed across notes and documents. Learners need both conceptual context and practice, while curators need to know where every concept and question came from. Existing workflows separate graph exploration, flashcard review, question authoring, testing, and results analysis, making it hard to move from a knowledge gap to targeted practice.

## Product Principles

- **Traceable:** concepts, questions, and results retain source and subject provenance.
- **Learning-first:** graph exploration, retrieval practice, assessment, and feedback form one loop.
- **Transparent:** correct answers, rubric criteria, matched keywords, and per-question diagnostics are visible.
- **Human-governed:** generation can draft content, but publication requires validation and review.
- **Local-first:** the application runs on a local machine, keeps data portable, and does not require hosted infrastructure.

## Product Positioning

Knowledge Graph Learning Studio is a local-first knowledge graph and assessment platform, not a data-science dashboard. Its differentiating loop is:

```text
Sources -> Knowledge Graph -> Learning -> Assessment -> Diagnosis -> Targeted remediation
```

The graph is a learning instrument: the primary outcome is helping a learner understand a weak area, not merely displaying graph data.

## Architecture

```text
React + TypeScript (learner, curator, assessment interfaces)
                         |
                    FastAPI API
                         |
              Domain and application services
                 /                       \
        SQLite (application state)   Filesystem (artifacts)
```

The frontend must not directly manipulate persisted files. All mutations pass through typed API contracts and application services, so domain logic remains usable without a web UI and independently testable.

### Technology baseline

| Layer | Technology |
| --- | --- |
| Frontend/build | React, TypeScript, Vite |
| UI/state | Tailwind CSS, shadcn/ui, TanStack Query or Zustand |
| Graph | React Flow, Cytoscape.js, or Sigma.js after scale testing |
| Backend | FastAPI, Pydantic |
| Persistence | SQLite, SQLAlchemy or SQLModel, Alembic |
| Processing | PyMuPDF, NetworkX |
| Testing | Pytest, Vitest |

Postgres, Redis, Celery, authentication, Docker, and microservices are explicitly deferred. They are not required for the local MVP.

### Storage boundary

Use the filesystem for original PDFs, source JSON, generated drafts, exports, and package snapshots. Use SQLite for subjects, concepts, relations, questions, package versions, provenance, validation issues, attempts, answers, and scores. This preserves portable artifacts without using mutable JSON files as the application database.

### Core domain model

```text
Subject -> Source -> Provenance
Subject -> Concept -> ConceptRelation -> Concept
Concept -> Flashcard
Subject -> QuestionPackage -> PackageVersion -> Question
Question -> MCQOption / RubricCriterion / QuestionConcept
PackageVersion -> Attempt -> Answer
```

`PackageVersion` is immutable once published. Each attempt records the exact package version used, making historical results reproducible after later edits.

### Content lifecycle

```text
DRAFT -> REVIEW -> PUBLISHED
            ^          |
            |          v
            +------ NEW DRAFT
```

Published content cannot be edited in place. A change creates a new draft and eventually a new package version. Generation and ingestion failures must leave the existing published version untouched.

## Goals

- Search and explore concepts, relationships, and learning paths.
- Generate or author flashcards and MCQ/essay question packages from learning material.
- Deliver interactive tests with difficulty and learning-objective metadata.
- Grade MCQs deterministically and essays using explicit rubric/keyword criteria.
- Persist attempts and make results reviewable, comparable, and exportable.
- Connect questions and feedback to graph concepts so weak areas lead to relevant study material.

## Non-goals

- Replacing a full LMS, note-taking app, or high-stakes proctoring system.
- Automatic factual validation or unsupervised publication of generated content.
- Real-time collaboration, tenancy, SSO, or permissions in the MVP.
- Adaptive testing, spaced-repetition scheduling, or mastery analytics in the first release.
- A hosted deployment, multi-user collaboration, or production infrastructure in the MVP.

## Users and Use Cases

### Learner

- Browse a subject's central concepts and relationships.
- Open a concept to read its definition, provenance, and neighbors.
- Find a path between two concepts.
- Review flashcards by search or subject.
- Select a question package, answer MCQs and essays, submit, and see scores.
- Review each response, the correct answer, rubric matches, and related concepts.

### Curator or instructor

- Add JSON notes or upload a PDF as source material.
- Create a question package with subject, level, source, and package ID.
- Add/parse MCQs and specify options, correct answer, difficulty, learning objective, and slide references.
- Define essay prompts, expected keywords, rubric criteria, weights, and grading notes.
- Validate, preview, publish, and version content.
- Inspect submissions, compare answers, and export result tables as CSV.
- Find incomplete graph nodes or malformed questions before publication.

## Unified Learning Loop

1. Ingest JSON notes and source documents.
2. Normalize and validate content.
3. Build graph nodes, typed edges, provenance, flashcards, and question packages.
4. Curator reviews and publishes a package version.
5. Learner studies concepts/flashcards or takes an assessment.
6. System grades and stores the attempt.
7. Results identify weak questions/concepts and link back to targeted graph learning.

## MVP Scope

### Content ingestion and graph

- Support full graph JSON, single entities, and entity lists.
- Normalize entity names and relation records.
- Merge duplicate nodes and typed directed edges deterministically.
- Track subject IDs and contributing source files.
- Build graph, flashcard, and subject-index artifacts under `data/`; persist indexed application state in SQLite.

### Question authoring and generation

- During migration, read packages from `database/<subject>/<package_id>/package.json`; the target system stores package metadata and versions in SQLite while retaining package snapshots on the filesystem.
- Support PDF text extraction as an input to generation; generated content must be marked draft until reviewed.
- Author MCQs manually or by parsing pasted question blocks.
- Support up to five labeled options, one correct option, difficulty, learning objective, and slide references.
- Support essay prompts with expected keywords and weighted rubric criteria.
- Validate IDs, required fields, option keys, score weights, and package metadata.

### Delivery, grading, and review

- Let learners select subject and package and answer MCQ and essay questions.
- Grade MCQs by exact correct-option match.
- Grade essays using explicit case-insensitive keyword/rubric matching in the MVP.
- Calculate MCQ, essay, and final scores without dividing by zero when a section is empty.
- Persist timestamp, package version, answers, scores, matched criteria, and subject/package identifiers.
- Provide result tables, expanded per-question review, and CSV export.

### Graph-learning integration

- Allow questions to reference one or more graph nodes or learning objectives.
- From a missed question, link to related node definitions, neighbors, and flashcards.
- Show provenance for both the question and its linked concepts.

### Interfaces

The frontend has two deliberately separate workspaces:

- **Learner:** continue learning, weak areas, concepts, flashcards, assessments, history, and graph exploration.
- **Curator:** sources, concepts, graph, flashcards, packages, questions, rubrics, versions, validation, provenance, submissions, and exports.

The learner home prioritizes continuation, weak concepts, and recommended remediation. The graph is accessible from that flow but is not the entire homepage. Question authoring provides structured fields and an Edit/Preview mode rather than requiring raw JSON.

### API and processing boundaries

The initial API should cover `subjects`, `concepts`, `concepts/{id}/neighbors`, `graph`, `graph/path`, `flashcards`, `packages`, `packages/{id}/questions`, `questions/{id}`, `assessments`, `assessments/{id}/submit`, `attempts/{id}`, `results`, and `validation`. Assessment navigation should load a package or attempt efficiently rather than requiring a server round-trip for every question.

PDF ingestion is a service workflow. The MVP may run extraction synchronously, but the service boundary must support a later job pipeline: upload, extract, chunk, extract concepts/relations, generate questions, and create a draft package without blocking the UI.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
| --- | --- | --- | --- |
| FR-1 | Ingest supported source formats | Must | Valid JSON inputs and PDF metadata can enter a draft content workflow. |
| FR-2 | Build the knowledge graph | Must | A build produces valid nodes and typed directed edges from subject folders. |
| FR-3 | Preserve provenance | Must | Nodes, questions, and packages identify subjects and source files/documents. |
| FR-4 | Explore concepts | Must | A learner can filter the graph, inspect a node, and view neighbors. |
| FR-5 | Find connections | Must | A learner can select two nodes and see a shortest path or no-path result. |
| FR-6 | Generate/browse flashcards | Must | Defined nodes can become searchable, subject-filterable flashcards. |
| FR-7 | Author question packages | Must | A curator can create valid MCQ and essay content and export/package it. |
| FR-8 | Deliver assessments | Must | A learner can complete available MCQs and essays and submit once per attempt. |
| FR-9 | Grade transparently | Must | Results expose score components, correct MCQ answers, and essay criteria matches. |
| FR-10 | Review and export results | Must | Curators can filter submissions and download a CSV comparison. |
| FR-11 | Link assessment to graph | Should | A missed question exposes related concepts and flashcards. |
| FR-12 | Version content | Should | Attempts retain the exact package version used, even after later edits. |
| FR-13 | Detect quality issues | Should | Missing definitions, invalid references, and malformed question records are reported. |

## Non-functional Requirements

- Python 3.10+ and explicit UTF-8 handling.
- Local MVP requires no network connection; API keys are optional and never required for manual authoring.
- Frontend and backend are independently testable; API request and response schemas are typed.
- Initial UI load is under two seconds for normal datasets; search feels immediate for typical subject datasets.
- Graph views remain interactive for at least several thousand nodes through filtering or progressive rendering.
- Uploaded PDFs and temporary files must be closed and cleaned up reliably.
- Invalid records must not silently corrupt valid graph or assessment data.
- Published packages are immutable; edits create a new version.
- UI works on desktop and narrow screens; large graph/result views are paginated or filtered.
- Result and source data must be kept private when the product is deployed beyond localhost.

## Success Metrics

- A new subject can be built, reviewed, and made available using documented commands.
- Every published question has a valid package, source, subject, and stable question ID.
- Every displayed node/question can be traced to at least one source.
- A learner can move from a missed question to a related concept or flashcard in three interactions or fewer.
- Curators can diagnose a submission without opening raw JSON.
- No published package contains invalid option keys, missing answers, or rubric weights that cannot be explained.

## Risks and Decisions

- Free-text entity names and package IDs can create false duplicates; introduce canonical IDs and explicit package versions.
- The current package directory ID can differ from the `package_id` inside `package.json`; migration must define one canonical identifier.
- Keyword essay grading is explainable but not equivalent to semantic evaluation; retain rubric evidence and label it as assistive.
- PDF generation is currently scaffolded/placeholder-based; generated drafts need a review state and source text provenance.
- JSON files do not provide safe concurrent writes or efficient analytics at scale.

## Migration Strategy and Roadmap

1. **Extract core logic:** separate graph building, parsing, validation, grading, and persistence from Streamlit into framework-independent Python services.
2. **Introduce FastAPI:** expose the domain through typed endpoints while Streamlit remains a temporary client.
3. **Build React alongside Streamlit:** implement learner and curator workspaces against the API, starting with the core learning loop.
4. **Move state to SQLite:** retain PDFs, source JSON, generated drafts, exports, and snapshots under `data/`; migrate structured records and package versions to `knowledge.db`.
5. **Retire Streamlit:** remove the temporary client after feature parity and end-to-end validation.
6. **Content quality:** formal schemas, stable IDs, lifecycle states, provenance, immutable versions, and graph-question links.
7. **Learning loop:** remediation links, mastery history, spaced repetition, and objective-level analytics.
8. **Production, later:** Postgres/object storage, workers, authentication/tenancy, caching, audit logs, and hosted deployment.
