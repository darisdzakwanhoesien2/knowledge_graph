# Knowledge Graph

Streamlit app + pipelines for building and exploring a directed knowledge graph from subject-scoped JSON files.

## Quick start

1) Create a virtualenv and install deps:
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`

2) Build artifacts:
- `python3 pipelines/merge_graph.py`
- `python3 pipelines/generate_flashcards.py`
- `python3 pipelines/extract_subject_index.py`

3) Run the Streamlit app:
- `streamlit run app_streamlit.py`

## Data layout

Raw inputs live under `json_nodes/<subject_id>/*.json` (one folder per subject). Each JSON file can be:

- A full graph payload: `{ "nodes": { ... }, "edges": [ ... ] }`
- A single-entity payload: `{ "entity": "...", "relations": [ ... ], ... }`
- A list of entities: `[ { "entity": "...", ... }, ... ]`

Generated artifacts are written under `data/`:
- `data/graphs/merged_graph.json` (pipeline output)
- `data/flashcards/flashcards.json`
- `data/indexes/subject_index.json`

## What was audited (bugs / errors / broken logic)

This repo is small and mostly functional already, but there were a few correctness + robustness issues that show up quickly when running the pipelines and pages:

- **Deprecated timestamp construction** in `pipelines/merge_graph.py`: `datetime.utcnow()` emits a deprecation warning on Python 3.12+.
- **Silent exception swallowing** in `pages/2_Find_Connection.py`: a bare `except:` hides real errors (including programming mistakes) and makes debugging harder.
- **Potential mutation of ingested payload dicts** in `pipelines/merge_graph.py`: `setdefault(node_name, node_data)` can later attach metadata into `node_data`, which is a reference to the parsed JSON object. This is subtle but makes the merge logic harder to reason about.
- **Weak file encoding handling** in a few pipelines: `Path.read_text()` without an explicit encoding can break on some systems / inputs.
- **Edge/node robustness** in `components/graph_loader.py`: malformed nodes/edges could cause hard-to-explain downstream errors; it’s cheap to validate at load time.

## Fixes & cleanups applied

Changes are intentionally small and targeted:

- `pipelines/merge_graph.py`
  - Uses a timezone-aware UTC timestamp (`datetime.now(timezone.utc)`) to avoid deprecated APIs.
  - Deep-copies node payloads when ingesting full-graph JSON so merge-time metadata attachment cannot mutate the original parsed payload.
  - Normalizes `entity` strings via `.strip()` to reduce accidental duplicates caused by whitespace.
  - Adds defensive checks for malformed relation records so invalid edges don’t get emitted.

- `components/graph_loader.py`
  - Skips invalid/blank node keys and normalizes node names via `.strip()`.
  - Ignores non-dict edge records instead of crashing.

- `pages/2_Find_Connection.py`
  - Replaces bare `except:` with explicit `networkx` exceptions plus a final catch-all that reports the actual error.

- Pipelines encoding consistency
  - `pipelines/normalize_graph.py`, `pipelines/validate_schema.py`, `pipelines/extract_subject_index.py` now read/write using UTF-8 explicitly and preserve non-ASCII via `ensure_ascii=False`.

## Inline comments policy

Inline comments were added only where the logic is easy to misuse or where the behavior is non-obvious (for example: why we deep-copy node payloads during merge, and why we normalize entity strings before using them as dict keys).

## Notes

The previous README content in this repo is historical (older “past_codes” notes). It has been moved to `notes.md` so the top-level `README.md` stays focused on “how to run” and “what changed / why”.

---

# Complete Project Documentation

## 1) Project Overview

This project builds a directed “knowledge graph” from JSON files organized by subject (e.g. `json_nodes/machine_vision/*.json`), then provides:

- **Pipelines** to merge those inputs into a single graph artifact (`data/graphs/merged_graph.json`)
- **Optional derived artifacts** like flashcards and subject indexes
- **A Streamlit UI** to explore the resulting graph, browse nodes, find paths, and view flashcards

It solves the common problem of having knowledge spread across many small JSON “notes” and wanting:

- A single, queryable representation (graph)
- Provenance (which subject/file each node came from)
- A lightweight UI to explore relationships without writing code every time

## 2) Tech Stack

- **Language:** Python 3 (tested with Python 3.12.x in this repo)
- **Web UI:** Streamlit
- **Graph library:** NetworkX
- **Data/UI helpers:** pandas (tables in Streamlit), numpy (included as dependency)
- **Visualization:** PyVis (interactive network visualization)
- **Plotting (optional / currently unused by the main app):** matplotlib, plotly
- **Community detection (optional / currently unused by the main app):** python-louvain

Dependencies are listed in `requirements.txt`.

## 3) Architecture Overview

High level flow:

1. **Inputs**: `json_nodes/<subject_id>/*.json`
2. **Build**: `pipelines/merge_graph.py` reads all subject folders and creates:
   - `data/graphs/merged_graph.json`
   - Per-node metadata: `subjects` and `source_files`
3. **Derive**:
   - `pipelines/generate_flashcards.py` → `data/flashcards/flashcards.json`
   - `pipelines/extract_subject_index.py` → `data/indexes/subject_index.json`
4. **Explore**:
   - `components/graph_loader.py` loads `merged_graph.json` into a `networkx.DiGraph`
   - `app_streamlit.py` and `pages/*.py` render Streamlit pages on top of that graph

Key modules:

- `pipelines/merge_graph.py`: ingestion + merge into a single graph JSON
- `components/graph_loader.py`: loads graph JSON → `networkx.DiGraph`
- `components/visualizations.py`: renders `networkx` graph using PyVis for interactivity
- `pages/*.py`: Streamlit multi-page UI (overview, narrative, path finding, flashcards, etc.)

## 4) Installation & Setup

### Prerequisites

- Python 3.10+ recommended (this repo runs on 3.12.x)

### Setup (macOS/Linux)

1) Create and activate a virtualenv:

- `python3 -m venv .venv`
- `source .venv/bin/activate`

2) Install dependencies:

- `pip install -r requirements.txt`

3) Build graph + derived artifacts:

- `python3 pipelines/merge_graph.py`
- `python3 pipelines/generate_flashcards.py`
- `python3 pipelines/extract_subject_index.py`

4) Start the app:

- `streamlit run app_streamlit.py`

### Common issues

- If the app says the graph is missing, run `python3 pipelines/merge_graph.py` first.
- If the Flashcards pages can’t find flashcards, run `python3 pipelines/generate_flashcards.py`.

## 5) Usage Guide (with examples)

### Adding new knowledge

1) Create a new subject folder:

- `mkdir -p json_nodes/my_new_subject`

2) Add JSON files under that folder.

Supported formats:

- Full graph:
  - Must contain `nodes` (object/dict) and `edges` (list)
- Single entity:
  - Must contain `entity` and can contain `relations` (list of `{type, target}` dicts)
- List of entities:
  - A JSON list of objects, each with `entity` and optional `relations`

3) Rebuild artifacts:

- `python3 pipelines/merge_graph.py`
- (optional) `python3 pipelines/generate_flashcards.py`

### Using the Streamlit UI

- Main page (`app_streamlit.py`) renders an interactive network visualization (PyVis).
- Pages:
  - `Global Overview`: quick table of nodes with degree + subject metadata.
  - `Global Narrative`: shows central concepts (degree centrality).
  - `Find Connection`: pick two nodes and compute a shortest path.
  - `Learn From Node`: view definition/subjects/neighbors for a node.
  - `Flashcards` and `Flashcards by Subject`: browse/search generated flashcards.
  - `Node Cleanup`: lists nodes missing definitions (simple data quality check).

### CLI examples

- Build graph:
  - `python3 pipelines/merge_graph.py`
- Validate schema:
  - `python3 pipelines/validate_schema.py`
- Normalize node keys (trims whitespace in node names):
  - `python3 pipelines/normalize_graph.py`

## 6) API Reference (if applicable)

There is **no HTTP/REST API** in this repo (no endpoints). The “API surface” is the set of Python scripts and the JSON artifact formats.

### Artifact: `data/graphs/merged_graph.json`

Top-level shape:

- `nodes`: object mapping `node_name -> properties`
- `edges`: list of edges shaped like `{ "source": "...", "target": "...", "type": "..." }`
- `metadata`:
  - `built_at`: ISO8601 timestamp (UTC, timezone-aware)
  - `subjects`: mapping `subject_id -> { subject_id, display_name, files[] }`

Per-node metadata (written by `pipelines/merge_graph.py`):

- `metadata.subjects`: list of subject IDs the node appeared in
- `metadata.source_files`: list of JSON filenames that contributed to the node

### Artifact: `data/flashcards/flashcards.json`

Each entry is shaped like:

- `entity`, `domain`, `subjects[]`, `sources[]`
- `front`: a short “prompt” text
- `back`: definition/description/facts markdown

## 7) Environment Variables

No environment variables are required today. The project uses filesystem paths relative to the repo root.

If you want `.env` support later (e.g., custom input/output paths), a typical approach would be to add variables like:

- `KG_JSON_NODES_DIR`
- `KG_OUTPUT_GRAPH`
- `KG_FLASHCARDS_PATH`

…but these are **not implemented** currently.

## 8) Contributing Guide

Suggested workflow:

1) Create a branch for your change.
2) Keep changes small and focused (one logical change per PR).
3) Run basic checks locally:
   - `python3 -m py_compile app_streamlit.py components/*.py pipelines/*.py pages/*.py`
   - `python3 pipelines/merge_graph.py`
4) If you change ingestion logic, verify:
   - `python3 pipelines/validate_schema.py`
   - Flashcards generation still works: `python3 pipelines/generate_flashcards.py`

Coding guidelines (project conventions):

- Prefer explicit UTF-8 when reading/writing JSON.
- Avoid bare `except:`; catch specific exceptions first.
- Keep pipelines deterministic (sorted iteration over folders/files is preferred).

## 9) License

No license file is present in this repository.

If you want, I can add a `LICENSE` (common choices: MIT, Apache-2.0, or GPL-3.0) once you tell me which one you prefer.

---

# Scaling Guide (MVP → Production)

This repo is currently a **local-first** Python pipeline + **Streamlit** UI that reads artifacts from disk. It does not have a networked backend or database yet, so “scaling” largely means (a) handling larger graphs and (b) serving more concurrent users reliably once you deploy it.

## 1) Current Bottlenecks (what breaks first)

**Data build / pipelines**
- **Single-machine merge**: `pipelines/merge_graph.py` reads many JSON files and builds a single in-memory Python dict. Very large corpora will hit memory/CPU limits first.
- **O(n) JSON parsing**: parsing thousands of JSON files is CPU + filesystem bound.
- **Edge de-dup complexity**: edge de-dup uses `if edge not in graph["edges"]` which is O(n) per edge; this becomes slow if edges grow to millions.

**App / UI**
- **Streamlit concurrency**: Streamlit is great for internal tools but can feel slow under many concurrent sessions, especially if each session loads large artifacts.
- **Graph rendering in-browser**: PyVis/vis-network rendering becomes heavy as node/edge counts grow (browsers struggle first; you’ll see lag/crashes).
- **Repeated artifact loads**: without caching, each user session will re-parse JSON and reconstruct the NetworkX graph.

**Deployment**
- **No auth / rate limiting / observability**: first issues at real scale are often abuse, unexpected traffic spikes, and “we can’t debug production” problems.

## 2) Database Scaling (indexing, caching, sharding, replicas)

There is **no database currently**. If/when you introduce one, a practical split is:

- **Graph data**: nodes + edges + provenance
- **Search**: fast lookup by entity/name/content
- **Artifacts**: versioned graph builds (so you can roll back and compare)

### Option A: Postgres (recommended default)

Model:
- `nodes` table: `id`, `name`, `definition`, `domain`, `metadata_json`, etc.
- `edges` table: `source_id`, `target_id`, `type`

Scale levers:
- **Indexing**: B-tree on `nodes(name)`; full-text / trigram for search; composite indexes like `(source_id, type)` and `(target_id, type)`.
- **Caching**: Redis for hot queries (node lookup, neighbors, cached traversals).
- **Read replicas**: one writer + 1–N read replicas when read traffic dominates.
- **Sharding**: usually unnecessary until graphs are extremely large; if needed, shard by `subject_id` or hash of `node_id`.

### Option B: Managed graph DB (Neo4j / Neptune)

Best when runtime multi-hop traversals and graph analytics are core product features.

Scale levers:
- **Indexes/constraints** on node keys (ids/names).
- **Read replicas** for read-heavy traffic.
- **Caching** for expensive traversals.
- **Sharding** depends heavily on the vendor and can add operational complexity.

## 3) Backend Scaling (load balancing, horizontal vs vertical)

Today the “backend” is Streamlit reading files. For production, you typically evolve in phases:

### Phase 1: Streamlit behind a load balancer
- **Vertical scale first**: bigger instance (more RAM/CPU) is simplest when artifacts grow.
- **Horizontal scale**: run multiple Streamlit instances behind a load balancer.
  - Requirement: shared access to artifacts (object storage like S3/GCS/Azure Blob) and/or a database.

### Phase 2: Split into API + UI

Add a small API service (FastAPI is a common choice) that serves:
- node lookup/search
- neighbors / subgraph queries
- precomputed analytics (centrality, clusters)
- flashcards retrieval

Then you can keep Streamlit as an internal/admin UI, or replace it with a dedicated web frontend.

Load balancing basics:
- Put an L7 load balancer (HTTP) in front of API + UI.
- Add rate limiting, auth, and request logging early.

## 4) Frontend Scaling (CDN, lazy loading, SSR/SSG)

Streamlit is not a traditional SPA/SSR app, but the scaling principles still apply:

- **CDN**: if you move to a web frontend (React/Next.js), serve static assets via a CDN.
- **Lazy loading**: render subgraphs on demand (fetch/display the neighborhood of a node instead of the entire graph).
- **SSR/SSG**:
  - SSG for docs/marketing pages and static content.
  - SSR for authenticated, dynamic pages where it helps perceived performance.
- **Visualization strategy**: for big graphs, prefer server-side filtering + pagination, clustering/sampling, and consider WebGL-based renderers.

## 5) Infrastructure Recommendations (AWS/GCP/Azure)

Below is a “standard” cloud shape that fits this project once deployed.

### AWS (reference setup)
- **Compute**: ECS Fargate (or EKS later), running:
  - Streamlit container (UI)
  - Optional FastAPI container (API)
- **Load Balancer**: ALB (Application Load Balancer)
- **Storage**: S3 for artifacts (`merged_graph.json`, flashcards, indexes), with versioning enabled
- **Database**: RDS Postgres (Multi-AZ), optional read replica
- **Cache**: ElastiCache Redis
- **Auth**: Cognito (or Auth0/Okta)
- **Observability**: CloudWatch logs/metrics (and optionally tracing)
- **CI/CD**: GitHub Actions → ECR → ECS deploy

GCP equivalents:
- Cloud Run (containers), Cloud Storage, Cloud SQL (Postgres), Memorystore (Redis), Cloud Load Balancing, Cloud Logging.

Azure equivalents:
- Container Apps, Blob Storage, Azure Database for PostgreSQL, Azure Cache for Redis, Application Gateway, Azure Monitor.

## 6) Cost Estimate (rough; for planning)

These are **order-of-magnitude** monthly estimates for a hosted deployment. Real costs depend heavily on:
- peak concurrency vs monthly active users
- graph size and query complexity
- whether analytics are computed on-demand vs precomputed
- traffic shape (spiky vs steady)

Assumptions for the table below:
- “Users” ≈ monthly active users; concurrency grows with users.
- Artifacts in object storage; basic API/UI traffic; moderate logging.
- One region; on-demand pricing; excludes engineering time.

### ~1k users/month (small internal/public)
- **$50–$200/mo**
  - 1–2 small containers (or a small VM), basic storage, maybe no DB

### ~10k users/month (growing)
- **$200–$1,000/mo**
  - multiple containers behind an L7 LB, managed Postgres, Redis cache, more bandwidth/logging

### ~100k users/month (serious)
- **$1,000–$10,000+/mo**
  - autoscaling services, read replicas, caching, CDN, stronger observability, possibly a managed graph DB

If you specify “users” as **peak concurrent** (and expected graph size), the estimate can be tightened significantly.

## 7) Roadmap (step-by-step scaling path)

### MVP (today)
- Keep pipelines on one machine.
- Keep artifacts in `data/` locally.
- Use Streamlit for exploration.

### MVP+ (first deployment)
- Containerize the Streamlit app.
- Store artifacts in object storage (S3/GCS/Azure Blob) and load from there at startup.
- Add Streamlit caching (`st.cache_data`) around graph loading/parsing to avoid per-session rework.
- Add basic auth if exposed publicly.

### Growth (~10k users/month)
- Introduce an API (FastAPI) for search + node/edge retrieval.
- Move graph storage to Postgres (or a graph DB if traversals dominate).
- Add Redis caching for hot queries.
- Run multiple UI/API replicas behind a load balancer with autoscaling.

### Production-grade (~100k+ users/month)
- Separate concerns:
  - **Ingestion/build** as a scheduled job (Prefect/Airflow or cloud scheduler)
  - **Serving** as API + frontend
  - **Analytics** precomputed and versioned
- Add:
  - monitoring/alerts and dashboards
  - rate limiting + abuse prevention
  - multi-AZ DB + read replicas
  - blue/green deploys + rollbacks
- For very large graphs:
  - precompute communities/embeddings
  - serve “subgraph slices” and summaries instead of rendering the full graph in the browser

---

# Competitive Landscape (10 Similar Apps / Companies)

This project sits at the intersection of **knowledge graphs**, **personal knowledge management (PKM)**, and **learning/flashcards**. Below are 10 relevant products/companies that solve nearby problems. Some public details (especially tech stack + scale) are incomplete; where unknown, it’s marked accordingly.

## 1) Neo4j (AuraDB / Neo4j Database)

- **What they do**: Native graph database + tooling (Cypher query language), used to build production graph applications.
- **Tech stack (public)**: Neo4j database engine + Cypher; cloud offering AuraDB. (Implementation details vary by edition.)
- **Business model**: Open core + enterprise licenses + managed cloud tiers.
- **Scale (public)**: Widely deployed in enterprises; marketed for large connected datasets.
- **Why they’re successful**: Strong developer ergonomics (Cypher), mature ecosystem/connectors, clear “graph-first” positioning, and production credibility.
- **Niche for you**: Don’t compete as a database. Compete as an *opinionated knowledge ingestion + learning UX* on top of simpler storage.

## 2) TigerGraph

- **What they do**: Enterprise graph platform designed for large-scale analytics and “graph at scale” use cases.
- **Tech stack (public)**: Native graph DB with GSQL; cloud offering.
- **Business model**: Commercial licenses + managed cloud.
- **Scale (public)**: Customer roster emphasizes large organizations and large-scale deployments.
- **Why they’re successful**: Clear performance narrative, enterprise sales motion, and graph analytics focus.
- **Niche for you**: Education/knowledge-work flows with provenance + curation + flashcards (not fraud/MDM/identity resolution).

## 3) Stardog

- **What they do**: Enterprise Knowledge Graph platform (semantic layer / RDF + reasoning/inference) for data unification.
- **Tech stack (public)**: RDF/SPARQL-based KG platform with semantic modeling + virtualization concepts.
- **Business model**: Enterprise subscriptions (and cloud/on-prem offerings).
- **Scale (public)**: Enterprise-focused deployments across industries.
- **Why they’re successful**: Semantic modeling + governance story, “unify without moving data” positioning, enterprise features.
- **Niche for you**: Lightweight, local-first, fast iteration. “KG for individuals/teams” rather than enterprise semantic governance.

## 4) Ontotext GraphDB

- **What they do**: RDF triplestore / knowledge graph database with semantic reasoning and integrations.
- **Tech stack (public)**: RDF + SPARQL; integrates with search engines (e.g., Lucene/Solr/Elasticsearch in some setups).
- **Business model**: Commercial licensing (with multiple editions).
- **Scale (public)**: Marketed for robust/scalable semantic workloads.
- **Why they’re successful**: Long-standing semantic web roots, strong RDF/SPARQL fit, enterprise reliability.
- **Niche for you**: Avoid ontology-heavy onboarding; keep input formats simple and focus on end-user value (learning + discovery).

## 5) Memgraph

- **What they do**: High-performance graph database positioned for real-time analytics and modern “GraphRAG”/AI use cases.
- **Tech stack (public)**: Open-source graph DB; Cypher-compatible; advertised as built in C++.
- **Business model**: Open source + commercial cloud/enterprise offerings.
- **Scale (public)**: Developer/teams adopting for performance-sensitive graph workloads (public customer counts vary).
- **Why they’re successful**: Performance narrative, “real-time” positioning, and modern AI adjacency (GraphRAG).
- **Niche for you**: “KG + curriculum/learning” productization, not “graph DB + AI infra”.

## 6) Diffbot (Knowledge Graph + Extraction APIs)

- **What they do**: Web data extraction + a large, pre-built Knowledge Graph accessible via API.
- **Tech stack (public)**: ML-based extraction pipelines + APIs; hosted knowledge graph dataset.
- **Business model**: Usage-based API pricing (credits/plans).
- **Scale (public)**: Built around a very large web-derived KG; used as a data provider.
- **Why they’re successful**: Strong data moat (web-scale KG) + API-first monetization.
- **Niche for you**: Personal/curated knowledge (private notes, course PDFs, internal docs) where “own your data + provenance” matters more than web-scale coverage.

## 7) Obsidian

- **What they do**: Local-first note-taking with backlinks/graph view; heavy plugin ecosystem; optional sync/publish services.
- **Tech stack (public)**: Electron-based desktop app (web-tech app shell); plugin ecosystem.
- **Business model**: Free core app; paid add-ons (Sync/Publish) + optional commercial licenses.
- **Scale (public)**: Large mainstream PKM adoption; exact numbers not consistently published.
- **Why they’re successful**: Local-first trust, extensibility via plugins, simple file-based workflow (Markdown).
- **Niche for you**: Opinionated “knowledge → graph → flashcards” pipelines and domain-specific schemas (education), rather than a general note editor.

## 8) Logseq

- **What they do**: Local-first, outliner-first PKM with graph concepts and bidirectional linking; open-source community.
- **Tech stack (public)**: Commonly described as Clojure/ClojureScript + Electron; uses a graph-oriented local data model.
- **Business model**: Open-source core; optional sync/services (varies over time).
- **Scale (public)**: Strong open-source adoption; exact user counts often not disclosed.
- **Why they’re successful**: Local-first + open-source alignment, block-based UX, strong community momentum.
- **Niche for you**: Stronger “structured ingestion + validation + learning workflows” (flashcards, QA, curricula) rather than general note/outliner UX.

## 9) Roam Research

- **What they do**: Networked note-taking centered on bidirectional links and graph thinking.
- **Tech stack (public)**: Not consistently public; generally positioned as a web app.
- **Business model**: Subscription.
- **Scale (public)**: Strong influence in PKM community; not known for mass-market scale like Notion.
- **Why they’re successful**: Clear conceptual model (“networked thought”), strong writing/research workflows, loyal power-user base.
- **Niche for you**: “From structured inputs to operational graph artifacts” (pipelines + schemas) and education-first workflows rather than a general writing environment.

## 10) Notion (workspace + databases)

- **What they do**: All-in-one workspace (docs, databases, projects, increasingly AI-assisted search/Q&A). Not a “knowledge graph” product per se, but competes for the same “central brain” job-to-be-done.
- **Tech stack (public)**: Not fully public end-to-end; widely known as a cloud SaaS with multi-platform clients.
- **Business model**: Freemium SaaS (free tier + paid plans); enterprise upgrades.
- **Scale (public)**: Widely reported as “tens of millions” of users; exact current numbers vary by source and time.
- **Why they’re successful**: Low friction onboarding, flexible “database” primitives, collaboration, strong distribution.
- **Niche for you**: Better graph-native exploration (paths/neighborhoods) + reproducible pipelines + local/offline/private workflows that Notion is not designed for.

## How your project can differentiate (niche opportunities)

The products above succeed for one (or more) of: **distribution**, **data moats**, **enterprise features**, or **developer ecosystems**. For your repo specifically, the strongest differentiators to lean into are:

- **Education-first “Knowledge → Flashcards → Mastery” loop**: position the graph as a learning engine (retrieval practice, spaced repetition hooks, curricula).
- **Strong provenance and reproducibility**: every node/edge should be traceable to source files/subjects; version builds; diff between graph versions.
- **Local-first + deploy-anywhere**: keep it lightweight (files + optional DB), privacy-friendly, and easy to self-host.
- **Opinionated schemas + validation**: provide a default schema contract (and validators) that make the knowledge base consistent and queriable.
- **LLM-assisted ingestion (optional)**: differentiate by turning raw materials (PDFs/notes) into validated graph entities + relations with human review, rather than “free-form notes”.
- **“Slice” UX for big graphs**: focus the UI on *subgraphs* (neighborhood view, topic map, learning paths) instead of trying to render the entire network at once.

If you tell me your intended audience (solo learner vs team vs public product) and your distribution plan (open-source tool vs SaaS), I can narrow this down into a concrete product positioning statement and a prioritized feature roadmap.
