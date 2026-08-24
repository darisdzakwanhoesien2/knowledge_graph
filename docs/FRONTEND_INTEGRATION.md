# Frontend Integration Approach

## Current deployment

The project currently has two user interfaces:

| URL | Application | Current role |
| --- | --- | --- |
| `http://43.157.212.74:5175/` | React/Vite | Subject and concept browsing |
| `http://43.157.212.74:8503/` | Streamlit | Existing learning and assessment UI |
| `http://43.157.212.74:8000/` | FastAPI | Shared application API |

The React application must not embed the Streamlit application. The long-term approach is to reimplement the required screens in React and reuse the FastAPI and core business logic.

## Why React should replace, rather than embed, Streamlit

- Embedded Streamlit pages would create two navigation systems and inconsistent styling.
- Browser authentication, state, errors, and deep links would be difficult to coordinate across ports.
- Streamlit is a server-rendered Python UI, while React is the deployed client application.
- The API already provides the boundary needed for a single frontend.

Streamlit can remain available temporarily for administration and as a fallback during migration.

## Target architecture

```text
Browser
  |
  v
React frontend :5175
  |
  v
FastAPI :8000
  |
  v
Core logic + SQLite/JSON data
```

For production, a reverse proxy should eventually serve the React assets and proxy `/api` to FastAPI on one origin. This removes the need for a public API port and avoids browser CORS issues.

## Feature migration

### Phase 1: Existing browsing

- Subjects: `GET /subjects`
- Concepts: `GET /concepts?subject_id=<subject_id>`
- Concept details: `GET /concepts/{concept_id}`
- Neighbor concepts: `GET /concepts/{concept_id}/neighbors`

### Phase 2: Learner assessment flow

Build these React screens:

1. Test catalogue: list subjects and published packages.
2. Test setup: show package/version information and start an attempt.
3. Test runner: render MCQs and essay prompts, with local answer state.
4. Submission: submit answers once and prevent accidental duplicate submissions.
5. Results: show scores, percentage, and remediation information.

Relevant API routes:

- `GET /packages`
- `GET /packages/{package_id}/versions`
- `GET /packages/{package_id}/versions/{version_id}`
- `POST /assessments?subject_id=<subject_id>&package_id=<package_id>`
- `POST /assessments/{attempt_id}/submit`
- `GET /results/{attempt_id}`

The frontend should treat the package version returned at start time as immutable for the attempt.

### Phase 3: Curator features

Rebuild the Streamlit curator pages in React after the learner flow is stable:

- Author packages
- Add and validate questions
- Publish package versions
- Import PDF drafts
- Review submissions

These features should use dedicated API request models and authorization before public exposure.

## Frontend API configuration

Development can use:

```text
VITE_API_URL=http://localhost:8000
```

The current deployed frontend uses:

```text
VITE_API_URL=http://43.157.212.74:8000
```

Prefer a relative `/api` URL once a reverse proxy is installed. Avoid hardcoding `localhost` in a production browser bundle because it refers to the visitor's computer.

## Deployment responsibilities

- `knowledge-graph-frontend.service` builds are served by Vite preview on port `5175`.
- `knowledge-graph-api.service` runs FastAPI on port `8000`.
- The frontend must be rebuilt after changing API URL or React code.
- The API must allow the deployed frontend origin through CORS until both are served from one origin.

## Acceptance criteria

The React migration is complete for a feature when:

- The feature is reachable from the React navigation without opening Streamlit.
- Loading, empty, validation, and API error states are represented in React.
- API calls use the configured base URL and do not rely on browser-localhost.
- The feature works on desktop and mobile widths.
- Relevant API and frontend tests pass.
- The corresponding Streamlit page can be retired or explicitly marked as legacy.
