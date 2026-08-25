# Adding New Data

There are two independent kinds of "new data" in this project, and they live in different places:

1. **Graph/subject content** — notes that become knowledge-graph nodes, edges, and flashcards. Source of truth: `json_nodes/<subject_id>/*.json`.
2. **Exam content** — MCQ/essay questions delivered as a test. Source of truth: `database/<subject>/<package_id>/package.json`.

A third kind, **flashcard tags** (letting one flashcard belong to multiple exam topics/groups), is defined in [`ERD.md`](ERD.md) (`TAG` / `FLASHCARD_TAG`) and [`PRD.md`](PRD.md) (`FR-16`) but **not implemented yet** — see the note at the end of this doc.

## 1. Graph/subject content

### Where files go

```
json_nodes/<subject_id>/<any_name>.json
```

`subject_id` is the folder name (snake_case, e.g. `numerical_matrix`) — it becomes the canonical subject identifier everywhere downstream (graph metadata, registry, package authoring). File names inside the folder are free-form; `pipelines/merge_graph.py` reads every `*.json` in the folder except `flashcards.json` and `merged_graph.json`.

### Accepted shapes

A file can be **one** of three shapes:

**A. List of entities** (most common — see `json_nodes/introduction_to_optimization/01_data.json` for a real example):

```json
[
  {
    "entity": "Continuous Optimization",
    "type": "Concept",
    "domain": "Optimization",
    "definition": "One or two sentences defining the concept precisely.",
    "description": "Extra context: why it matters, how it contrasts with related ideas.",
    "properties": {
      "Goal": "Free-form key/value facts — any keys you want",
      "Methods": ["Bulleted values are supported"],
      "Examples": []
    },
    "relations": [
      { "type": "has_component", "target": "Objective Function ($f$)" },
      { "type": "contrasts_with", "target": "Discrete Optimization" }
    ],
    "metadata": {
      "created_by": "system",
      "source": "chapter_1.pdf",
      "created_at": "2025-11-10"
    }
  }
]
```

**B. Single entity** — same object as above, not wrapped in a list.

**C. Full graph payload** — pre-merged nodes + edges, for bulk/programmatic import:

```json
{
  "nodes": { "Entity Name": { "type": "...", "domain": "...", "definition": "...", "description": "...", "properties": {} } },
  "edges": [ { "source": "Entity Name", "target": "Other Entity", "type": "relation_type" } ]
}
```

### Field reference

| Field | Required | Notes |
| --- | --- | --- |
| `entity` | Yes | The node's identity. **This is a free-text string, not a stable ID** — two files using slightly different spelling/whitespace create two separate nodes (a known risk, see `ERD.md` → Risks and Decisions). Reuse the exact string to extend an existing node from another file. |
| `type` | No | Defaults to `"Concept"`. |
| `domain` | No | Free text, e.g. `"Optimization"`. |
| `definition` | Recommended | Shown as the node's primary text; nodes missing this are flagged by `pipelines/check_quality.py`. |
| `description` | No | Longer supporting text. |
| `properties` | No | Any dict of extra facts; rendered as bullet points on flashcards. |
| `relations` | No | List of `{ "type": <relation label>, "target": <entity name> }`. `target` must match another entity's `entity` string (exactly) to become a resolvable edge. |
| `metadata` | No | Curator-supplied fields (e.g. `source`, `created_at`) are preserved as-is. The build pipeline adds `subjects` and `source_files` into this same object automatically — don't use those two keys yourself. |

### Turning a new file into a live subject

Run in order from the repo root (`.venv` activated):

```bash
python3 pipelines/merge_graph.py          # merges json_nodes/ -> data/graphs/merged_graph.json
python3 pipelines/generate_flashcards.py  # derives data/flashcards/flashcards.json from graph nodes
python3 pipelines/extract_subject_index.py
python3 pipelines/build_registry.py       # data/registry/registry.json — subject list package authoring reads from
python3 pipelines/check_quality.py        # reports missing definitions / broken relation targets
python3 -m scripts.migrate_json_to_sqlite # syncs the same content into knowledge.db for the FastAPI/React path
```

Flashcards are **derived**, not authored directly — every node with a `definition`, `description`, or `properties` automatically becomes one flashcard. There's no separate flashcard file to write.

## 2. Exam content (question packages)

### Where files go

```
database/<subject>/<package_id>/package.json
```

`subject` must already exist in the registry (run `pipelines/build_registry.py` after adding new `json_nodes/` content, before authoring a package against it). The easiest way to create one is the curator UI (Streamlit → **Author Packages**, or the eventual React curator workspace), which writes this file for you and runs validation — hand-editing is only needed for bulk/scripted authoring.

### Package shape

```json
{
  "schema_version": 1,
  "package_key": "introduction_to_optimization/optimization_basics_quiz",
  "package_id": "optimization_basics_quiz",
  "subject": "introduction_to_optimization",
  "title": "Optimization Basics Quiz",
  "level": "Undergraduate",
  "status": "draft",
  "version": 1,
  "mcqs": [ /* see below */ ],
  "essay": [ /* see below */ ]
}
```

`package_key` must always equal `"<subject>/<package_id>"` — this is validated on publish.

### MCQ fields (`mcqs[]`)

| Field | Required | Notes |
| --- | --- | --- |
| `question` | Yes | The prompt text. |
| `options` | Yes | Dict of 2–5 entries keyed `A`–`E`, e.g. `{"A": "...", "B": "..."}`. |
| `correct_option` | Yes | Must be one of the keys in `options`. |
| `difficulty` | No | `easy` / `medium` / `hard`. |
| `learning_objective` | No | Free text. |
| `slide_refs` | No | List of strings (page/slide citations). |
| `node_links` | No | List of graph `entity` names this question assesses — powers the "study this concept" remediation shown on a missed question (`FR-11`). Must match an `entity` string from part 1 exactly to resolve. |

### Essay fields (`essay[]`)

| Field | Required | Notes |
| --- | --- | --- |
| `prompt` | Yes | The essay question text. |
| `expected_keywords` | No* | Case-insensitive keyword match, used if `criteria` is empty. |
| `rubric.criteria` | No* | List of `{ "keyword": "...", "weight": <number>, "description": "..." }` for weighted grading. |
| `rubric.total_points` | No | If unset, computed as the sum of criteria weights. |
| `rubric.grading_notes` | No | Shown to curators/learners alongside the score. |
| `node_links` | No | Same as MCQ. |

\* At least one of `expected_keywords` or `rubric.criteria` should be set, or the essay can't be graded transparently.

### Publishing

A package starts as `status: "draft"`. Validate it (`core.packages.validate_package`, or the "Validate & publish" button in Author Packages) before publishing — publishing snapshots the package to `versions/v<N>.json` and makes it immutable; any further edit auto-starts the next draft version rather than mutating the published one.

## 3. Flashcard tags (not yet implemented)

The design for letting one flashcard belong to multiple exam topics/groups (e.g. tagging a card `midterm-2` and `gradient-methods` simultaneously) is written up in `ERD.md` (`TAG` / `FLASHCARD_TAG`, a many-to-many join) and `PRD.md` (`FR-16`). There is no `tags` field on a flashcard or package today — adding one means implementing that model first, not editing a JSON file.
