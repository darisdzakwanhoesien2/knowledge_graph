# Next Action Plan

This plan moves the project from a working FastAPI scaffold to a usable,
database-backed learning studio. Work should proceed in order because each
phase supplies the foundation for the next one.

## Current Baseline

- FastAPI routes are present and `app.main` imports successfully.
- Core logic still reads and writes JSON files.
- Alembic schema exists, but the SQLite database contains no application data.
- The React frontend is still the stock Vite starter screen.
- Streamlit remains the only complete user interface.

## Phase 1: Stabilize The API

Priority: high

1. Add API tests for subjects, concepts, packages, validation, questions,
   assessments, and results.
2. Test both successful responses and expected 404/validation failures.
3. Remove unused imports and make route response models match the core payloads.
4. Document the local API start command and health-check endpoint.

Exit criteria:

- `pytest` passes for the API test suite.
- `python -c "from app.main import app"` succeeds in a clean virtualenv.
- OpenAPI generation succeeds without response-model errors.

## Phase 2: Migrate JSON Data To SQLite

Priority: high

1. Define the canonical import mapping from graph, registry, package, and
   submission JSON into the tables described in `docs/ERD.md`.
2. Implement an idempotent migration command, for example:
   `python -m scripts.migrate_json_to_sqlite`.
3. Preserve source paths, package version identifiers, content hashes, and
   timestamps during import.
4. Add duplicate and referential-integrity checks to the migration.
5. Run the migration against a copy of the current JSON data.
6. Compare row counts and representative records against the source files.

Exit criteria:

- A fresh database can be created with Alembic and populated in one command.
- Re-running the migration does not duplicate records.
- Imported subjects, concepts, packages, versions, questions, and results are
  queryable through the API.
- The source JSON remains unchanged and can still be used for rollback.

## Phase 3: Move API Reads To SQLite

Priority: high

1. Add database session dependency management to the FastAPI application.
2. Replace filesystem reads in API handlers with SQLModel queries.
3. Keep core JSON pipelines as import/build tooling rather than request-time
   storage.
4. Add indexes for subject IDs, package IDs, version IDs, and concept names.
5. Add transaction handling for assessment submission and result creation.

Exit criteria:

- API responses are backed by SQLite rather than direct JSON reads.
- Assessment submissions are atomic and retain the exact package version used.
- API tests pass with an isolated temporary database.

## Phase 4: Build The React Learning Studio

Priority: medium

1. Replace the Vite starter screen with a responsive application shell.
2. Implement the first vertical slice: subjects → concepts → concept detail.
3. Add package browsing and published-version selection.
4. Add the test-taking flow for MCQs and essays.
5. Add results and remediation views using the existing API.
6. Add loading, empty, error, and mobile states for every screen.

Exit criteria:

- A learner can select a subject, inspect concepts, take a published test, and
  review results without opening Streamlit.
- Frontend API calls use one documented base URL configuration.
- The production frontend build completes successfully.

## Phase 5: Retire Streamlit Gradually

Priority: medium

1. Keep Streamlit available as an authoring and operational fallback.
2. Compare the React and Streamlit flows using the same imported database.
3. Move authoring and validation workflows to React or a dedicated admin UI.
4. Add a migration/backup runbook before removing Streamlit dependencies.
5. Remove Streamlit only after all required workflows have equivalent coverage.

Exit criteria:

- React covers learner, curator, validation, and results-review workflows.
- A documented backup and restore procedure exists.
- Streamlit can be removed without losing supported functionality.

## Phase 6: Quality And Production Hardening

Priority: low after the vertical slice

- Add authentication and authorization for learner versus curator actions.
- Add structured logging, request IDs, and basic health/readiness checks.
- Add frontend and API CI checks.
- Add pagination and bounded graph-neighbor responses.
- Add backup, restore, and database migration procedures.
- Add content-quality checks to the import pipeline and deployment process.

## Immediate Sprint

The next implementation sprint should contain only these deliverables:

1. API tests for the recently fixed routes.
2. A JSON-to-SQLite migration command with row-count verification.
3. Database-backed subject and concept read endpoints.
4. A React subject/concept browsing vertical slice.

Do not retire Streamlit or add production infrastructure until these four
deliverables are complete and verified together.

## Verification Commands

```bash
./.venv/bin/python -c "from app.main import app; print(app.title)"
./.venv/bin/python -m pytest tests/ -q
./.venv/bin/alembic upgrade head
./.venv/bin/python -m scripts.migrate_json_to_sqlite
cd frontend && npm run build
```
