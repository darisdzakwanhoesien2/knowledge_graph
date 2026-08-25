# Upload System Plan

`ADDING_DATA.md` documents the two data formats a curator can add today — both by hand-placing a file on disk. This plans the upload system that replaces "hand-place a file" with "upload through the API/UI," for the same two data types, without changing either format.

Today there is **no write path in the API at all**: `app/api/subjects.py` is GET-only, and package creation only happens through the Streamlit curator UI calling `core/packages.py` directly against the filesystem. This plan adds that write path.

## Design principles carried over from the PRD

- **Human-governed**: an upload is never live until validated and, for exam content, explicitly published. Uploading is equivalent to writing a draft file, not publishing it.
- **Traceable**: every upload keeps its content hash and origin, same as the existing `SOURCE_DOCUMENT` registry entries and `package.source`.
- **Invalid records must not silently corrupt valid data**: an upload that fails validation must not touch `merged_graph.json`, `knowledge.db`, or an existing package — it fails closed, before any write.

## 1. Graph/subject content upload

### Flow

1. Curator picks a target: an **existing** `subject_id` (from the registry) or types a **new** one (creates the folder).
2. Curator uploads one JSON file matching one of the three shapes from `ADDING_DATA.md` (list of entities / single entity / full graph payload).
3. Server-side, before writing anything:
   - Parse JSON — reject on parse error.
   - Validate shape (must match one of the three accepted forms).
   - For each entity: check `entity` is non-empty; warn (don't block) if the exact string already exists in another subject's file, since that's a duplicate-node risk called out in `ERD.md`, not necessarily an error — a curator may be intentionally extending a shared concept.
   - Check every `relations[].target` resolves to some entity in this upload or the existing graph; unresolved targets are a warning (`check_quality.py` already reports this class of issue post-merge), not a block.
4. On accept: write the file to `json_nodes/<subject_id>/<original_filename>.json`. If a file with that name already exists for the subject, require an explicit "replace" confirmation (content-hash compare first — identical content is a no-op, not an error).
5. Trigger the existing pipeline chain in order: `merge_graph` → `generate_flashcards` → `extract_subject_index` → `build_registry` → `check_quality` → `migrate_json_to_sqlite`. Return the quality report (errors/warnings) and node/edge counts to the curator as the upload result.

### API surface (new)

```
POST /subjects                          create a new subject_id (just registers the folder)
POST /subjects/{subject_id}/content      multipart file upload; runs steps 3-5 above
GET  /subjects/{subject_id}/content      list files currently backing this subject, with content hashes
```

### Why synchronous is fine for MVP, and where that breaks

The pipeline chain over the current dataset (a few thousand nodes) runs in well under a second, so running it synchronously inside the upload request is fine for the MVP. `PRD.md`'s NFR that PDF ingestion "must support a later job pipeline" applies here too once subject folders get large: the upload endpoint should be written so steps 3-5 can move to a background task (same interface, called from a queue instead of inline) without changing the request/response contract — return a `job_id` immediately, poll or receive a webhook for the quality report, rather than reworking the endpoint later.

### Flashcard-tag interaction

Tags (`TAG`/`FLASHCARD_TAG`, implemented in `app/api/tags.py`) are keyed by a flashcard's stable `entity` string, not a row ID, specifically so `generate_flashcards.py` can be re-run safely. A graph-content upload that changes an entity's `entity` name (rather than editing its definition in place) will orphan any tags attached to the old name — worth a UI warning ("renaming this entity will detach N existing tags") rather than a silent loss.

## 2. Exam content upload

### Flow

1. Curator picks subject + either an existing `package_id` (draft only — a published package is immutable) or types a new one.
2. Curator uploads either:
   - a **full `package.json`** (bulk import / migration case), or
   - a **partial payload**: just `{"mcqs": [...], "essay": [...]}` to append to an existing draft (the common case — adding a batch of questions to a package already being built).
3. Server-side: merge into the target draft in memory, run `core.packages.validate_package()`. Errors block the write entirely; warnings are returned but don't block (matches existing `Author Packages` UI behavior).
4. On accept: `core.packages.save_package()` writes the draft. Publishing remains a separate, explicit action — upload never publishes.

### API surface (new)

```
POST /packages                                  create a new draft package (subject, title, level, description)
POST /packages/{package_id}/content             upload full package.json or {mcqs, essay} to merge into the draft
POST /packages/{package_id}/publish             existing action, exposed via API (currently Streamlit-only)
```

### Enforced invariants (unchanged from `ADDING_DATA.md` / `ERD.md`)

- `package_key` is always recomputed server-side as `"<subject>/<package_id>"` — never trusted from the uploaded file, so an upload can't spoof a different package's key.
- A publish snapshot (`versions/v<N>.json`) is never touched by an upload; only `publish_package()` writes there.
- Uploading into a `published` package auto-starts the next draft version (`start_next_draft()`), same as editing through the UI — the upload never mutates a published version's file in place.

## 3. Shared upload safeguards

- **Size limit**: reject uploads above a fixed cap (e.g. 5 MB) before parsing — avoids a curator (or malformed script) accidentally pasting a huge file into a synchronous request.
- **Content-hash dedup**: reuse the `content_hash()` helper already in `core/store.py` for both flows — an upload identical to what's already on disk is reported as a no-op, not written again.
- **No auth yet**: same gap as the rest of the API (`docs/CODE_MAP.md`) — an upload endpoint is exactly the kind of write path that makes "no auth" a real risk rather than a theoretical one. Recommend gating upload endpoints specifically behind at least a shared curator token before exposing them past `127.0.0.1`, even if the read endpoints stay open longer.
- **Atomic writes**: reuse `core/store.py.write_json()` (tmp file + `os.replace`) for every write in both flows — already the pattern for packages, should be the pattern for `json_nodes/` writes too (today `merge_graph.py`'s output uses it, but nothing writes the *input* `json_nodes/` files programmatically yet).

## Implementation order

1. `POST /packages/{package_id}/content` — smallest surface, reuses `core.packages.save_package`/`validate_package` as-is, no new pipeline orchestration needed.
2. `POST /subjects/{subject_id}/content` — needs the pipeline-chain wrapper (step 5 above); start synchronous.
3. Curator UI panels for both, replacing "SSH in and drop a file" / the Streamlit-only package editor with an upload widget that surfaces the validation report before commit.
4. Move the graph-content pipeline chain to a background job once subject folders are large enough that synchronous upload requests become slow (no endpoint contract change needed if step 2 is built with that in mind).

## Status (updated after implementation)

Steps **1** and **2** are implemented:

- `app/api/packages.py` — `POST /packages`, `POST /packages/{package_id}/content`, `POST /packages/{package_id}/publish`.
- `app/api/subjects.py` — `POST /subjects`, `GET /subjects/{id}/content`, `POST /subjects/{id}/content` (multipart).
- `core/pipelines.py` — synchronous chain runner (`run_pipeline_chain()`), each step a subprocess using the API's interpreter; swap for a queued job later without changing endpoints (step 4).
- `core/graph_content.py` — shape validation + duplicate-entity / unresolved-target warnings; orphaned flashcard tags are detected post-chain and returned as `detached_tags`.
- `app/security.py` — optional shared-token gate: set `KG_CURATOR_TOKEN` and all write endpoints require a matching `X-Curator-Token` header (unset = open, matching the read API's local-first posture).

Tests: `tests/test_api_uploads.py` (13 cases) run both flows hermetically against temp dirs with the chain replaced by a recording fake.

Step **3** (React curator upload panels) remains open.

---

# Math/Markdown Rendering Plan

Unrelated to the upload system above — appended here per request rather than a new file. Tracks fixing rendered content: `json_nodes/*.json` `definition`/`description`/`properties` fields routinely contain LaTeX (`$f: \mathbb{R}^{n}\rightarrow\mathbb{R}$`, `\nabla f`, `\mathbb{R}^{n} \mid f(x) = c$`) and `pipelines/generate_flashcards.py` additionally bakes Markdown (`**Definition:**`, `**Description:**`) into a flashcard's `back` field. None of it renders today — confirmed by reading the frontend, not guessing: `grep -rn "katex\|mathjax\|marked\|remark\|dangerouslySetInnerHTML" frontend/src/` returns nothing. Every call site interpolates the raw string straight into JSX, which React escapes as plain text.

## Affected call sites (grep-confirmed, not assumed)

| File | Field(s) |
| --- | --- |
| `frontend/src/components/FlashcardsView.tsx` | `card.back` (list preview via regex-stripped `**Definition:**`, and the full text in the detail view) |
| `frontend/src/components/BrowseView.tsx` | `concept.definition` (list + detail) |
| `frontend/src/components/ResultsView.tsx` | `context.definition`, `context.flashcard.front`, `context.flashcard.back` (concept remediation panel) |
| `frontend/src/components/TestFlow.tsx` | `q.question` (MCQ prompt), MCQ `options` text, `q.prompt` (essay prompt) |

All four components independently interpolate `{text}` — there's no shared rendering component to patch once; that's the actual fix, not four separate patches.

## Plan

1. **Add rendering libraries** to `frontend/`: `react-markdown` (Markdown → React elements, no `dangerouslySetInnerHTML`), `remark-math` (extract `$...$` / `$$...$$` into math nodes), `rehype-katex` + `katex` (render those nodes). Import `katex`'s CSS once, in `main.tsx`.
2. **One shared component**, `frontend/src/components/RichText.tsx`: wraps `react-markdown` configured with `remark-math`/`rehype-katex`, takes `{ text: string }`. This is the single thing that gets tested/fixed, instead of four ad hoc renderers drifting apart.
3. **Replace the 4 call sites above** with `<RichText text={...} />`, deleting `FlashcardsView.tsx`'s regex-based `cardPreview()` in favor of passing the raw `back` straight through (Markdown handles the `**Definition:**` bold marker natively — no regex needed once it's actually rendered as Markdown).
4. **Explicitly do not add `rehypeRaw`** (the plugin that would let Markdown contain literal HTML). Content ultimately originates from uploaded `json_nodes/*.json` (see `UPLOAD_SYSTEM_PLAN.md` above) — allowing raw HTML through the renderer would turn a curator-content upload into a stored-XSS path. `react-markdown` without `rehypeRaw` already refuses to render embedded HTML, which is the safe default here, not an oversight to "fix" later.
5. **No backend/API change needed** — the content shape is unchanged; this is purely how the frontend renders strings it already receives.
6. **Verification**: no frontend test harness exists yet (no vitest/jest configured in `frontend/package.json`), so this is a manual check — reuse the routes added in the routing work: `/flashcards` (many real LaTeX examples already in the data, e.g. "Continuous Optimization"), `/` (Browse concept detail), `/test` (any package with LaTeX in a prompt/option), `/history` → a result's concept remediation panel.

## Non-goals

- Not fixing the LaTeX/Markdown *at the source* (`json_nodes/*.json`) — the content is valid, it's the renderer that's missing.
- Not adding a Markdown/math preview to the curator authoring flow (Streamlit `Author Packages`, or the not-yet-built upload UI from the plan above) — same underlying `RichText` component could serve that later, but it's a separate follow-up, not part of this fix.
