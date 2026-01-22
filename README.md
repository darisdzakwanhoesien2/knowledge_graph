# knowledge_graph

python merging.py
python generate_flashcard.py
streamlit run app_streamlit.py

Tools for Prompting:
1. https://grok.com/c/8ba9b602-ab42-400e-b047-bca0bc2f4049

1. Numerical Matrix: 1, 4, 7, 10: https://grok.com/c/da3ed06b-500e-4bdd-a602-32ddfc9fa6a9
2. Numerical Matrix: 2, 5, 8, 11: https://grok.com/c/8ba9b602-ab42-400e-b047-bca0bc2f4049
3. Numerical Matrix: 3, 6, 9: https://grok.com/c/eb638b03-5f0a-49f1-b948-102ecb4e79b7

1. Introduction to Optimization: Interesting issue that there is no much connection for the nodes/sparse https://grok.com/c/862353ec-7595-4648-ac67-b3c4192ed7b6

Let's extract topics from this PDF and check with the list of completed_nodes and incompleted_nodes

New codes: https://chatgpt.com/c/6971c79d-1f78-8333-97a3-37ab402e0cc8

Yes — this is exactly the right move.
Once your data becomes:

```
json_nodes/<subject_name>/*.json
```

you unlock **true scalability, clean provenance, curriculum mapping, and automation**.

Below is a **production-grade directory contract** tailored to your project and how you actually use it (graph merging, flashcards, Streamlit analytics, clustering, curriculum mining).

---

# 🧱 Canonical Project Directory Structure

```
education/knowledge_graph/
│
├── README.md
├── requirements.txt
│
├── json_nodes/                         ⭐ Raw Knowledge Sources (Authoritative)
│   ├── introduction_to_optimization/
│   │   ├── 01_data.json
│   │   ├── 02_constraints.json
│   │   └── metadata.json              ← optional subject metadata
│   │
│   ├── machine_vision/
│   │   ├── 01_data.json
│   │   ├── segmentation.json
│   │   └── metadata.json
│   │
│   ├── linear_algebra/
│   │   ├── eigen.json
│   │   ├── svd.json
│   │   └── metadata.json
│   │
│   └── probability/
│       ├── random_variables.json
│       └── metadata.json
│
│
├── pipelines/                         🚜 Data Engineering Pipelines
│   ├── merge_graph.py                 ← replaces merging.py
│   ├── normalize_graph.py
│   ├── validate_schema.py
│   ├── generate_flashcards.py
│   └── extract_subject_index.py
│
│
├── data/                              📦 Generated Artifacts
│   ├── graphs/
│   │   ├── merged_graph.json
│   │   ├── graph_summary.json
│   │   └── graph_versions/
│   │
│   ├── flashcards/
│   │   ├── flashcards.json
│   │   ├── flashcards_by_subject.json
│   │   └── exports/
│   │
│   ├── indexes/
│   │   ├── subject_index.json
│   │   └── node_subject_map.json
│   │
│   └── logs/
│       └── merge_log.txt
│
│
├── app/                               🖥 Streamlit Application
│   ├── app_streamlit.py
│   │
│   ├── pages/
│   │   ├── 0_Global.py
│   │   ├── 1_Global_Narrative.py
│   │   ├── 2_Find_Connection.py
│   │   ├── 3_Learn_From_Node.py
│   │   ├── 4_Flashcards.py
│   │   ├── 5_Flashcards_By_Subject.py
│   │   └── 6_Node_Cleanup.py
│   │
│   └── components/
│       ├── graph_loader.py
│       ├── filters.py
│       └── visualizations.py
│
│
├── schemas/                           📐 Data Contracts
│   ├── entity.schema.json
│   ├── graph.schema.json
│   ├── flashcard.schema.json
│   └── subject.schema.json
│
│
├── tools/                             🛠 Dev Utilities
│   ├── visualize_graph.py
│   ├── structure_code.py
│   └── migration_scripts/
│
└── notebooks/                         📊 Experimental / Analysis
    ├── graph_exploration.ipynb
    └── curriculum_analysis.ipynb
```

---

# 🎯 Why This Structure Works for You

This structure supports:

✅ Subject isolation
✅ Provenance tracking
✅ Curriculum analytics
✅ Scalable ingestion
✅ Multiple pipelines
✅ Clean Streamlit separation
✅ Versioned outputs
✅ Future ML / embeddings

This mirrors the way you already build research tooling in your ESG projects.

---

---

# 📁 json_nodes Contract (Most Important)

Your raw data becomes:

```
json_nodes/<subject_name>/<files>.json
```

### Example

```
json_nodes/
├── introduction_to_optimization/
│   ├── 01_data.json
│   ├── constraints.json
│   └── metadata.json
│
├── machine_vision/
│   ├── 01_data.json
│   └── metadata.json
```

---

## ✅ Subject Folder Rules

Each subject folder:

| Rule          | Description                              |
| ------------- | ---------------------------------------- |
| Folder name   | snake_case canonical subject ID          |
| Files         | Any number of JSON entity or graph files |
| metadata.json | Optional subject-level metadata          |

---

---

# 📘 Example `metadata.json` (Optional but Recommended)

```
json_nodes/introduction_to_optimization/metadata.json
```

```json
{
  "subject_id": "introduction_to_optimization",
  "display_name": "Introduction to Optimization",
  "course": "Numerical Optimization",
  "level": "Undergraduate",
  "tags": ["convexity", "gradients", "constraints"]
}
```

Later you can show:

🎓 Course grouping
📊 Difficulty progression
📚 Curriculum mapping

---

---

# 🚜 Pipeline Responsibility Contracts

### `pipelines/merge_graph.py`

Responsible for:

```
json_nodes/*/*  →  data/graphs/merged_graph.json
```

Injects:

```json
metadata: {
   subjects: [...],
   subject_ids: [...],
   source_files: [...]
}
```

---

### `pipelines/generate_flashcards.py`

Responsible for:

```
merged_graph.json → data/flashcards/flashcards.json
```

Preserves:

```
subjects
domains
entity
sources
```

---

---

# 🖥 Streamlit App Contract

App reads ONLY from:

```
data/
```

Never directly from:

```
json_nodes/
```

This keeps UI stable even if ingestion changes.

---

---

# 🧭 Naming Conventions (Critical for Scaling)

| Element          | Convention       |
| ---------------- | ---------------- |
| Subject folder   | snake_case       |
| Subject display  | Title Case       |
| Entity name      | Human readable   |
| Relation types   | snake_case       |
| Pipeline scripts | verb_object.py   |
| Output artifacts | explicit folders |

---

---

# 🔁 Migration Strategy (Your Current Repo)

You can migrate safely:

### Step 1 — Create folders

```bash
mkdir -p json_nodes/introduction_to_optimization
mkdir -p json_nodes/machine_vision
```

Move files accordingly.

---

### Step 2 — Update merging loader

Change loader to recursively scan:

```
json_nodes/*/*.json
```

Instead of flat folder.

---

### Step 3 — Rebuild graph

```bash
python pipelines/merge_graph.py
python pipelines/generate_flashcards.py
streamlit run app/app_streamlit.py
```

---

---

# 🚀 If You Want

Next I can:

✅ Give you the exact updated recursive loader code
✅ Auto-detect subject from folder name
✅ Auto-load subject metadata.json
✅ Build subject index automatically
✅ Upgrade Streamlit filters
✅ Add subject analytics dashboards
✅ Add curriculum sequencing

Just tell me which piece you want to implement first.

Perfect 👍
Let’s implement this **end-to-end properly** so that:

✅ Your data lives in

```
json_nodes/<subject_name>/*.json
```

✅ Subjects are automatically inferred from folder names
✅ Provenance is preserved
✅ Graph builds cleanly
✅ Flashcards are generated with subject metadata
✅ Streamlit keeps working without hacks
✅ Scales to unlimited subjects

You’ll be able to just drop new folders and everything updates automatically.

---

# 🧱 Target Directory (Minimal Working Version)

Create these folders (if not yet):

```
education/knowledge_graph/
├── json_nodes/
│   ├── introduction_to_optimization/
│   │   └── 01_data.json
│   └── machine_vision/
│       └── 01_data.json
│
├── pipelines/
│   ├── merge_graph.py
│   └── generate_flashcards.py
│
├── data/
│   ├── graphs/
│   └── flashcards/
│
└── app/
    └── app_streamlit.py   (your existing app can stay)
```

---

---

# 🚜 PIPELINE 1 — Recursive Graph Merge with Subjects

Create file:

```
pipelines/merge_graph.py
```

---

## ✅ Full Code — `pipelines/merge_graph.py`

```python
import json
from pathlib import Path
from datetime import datetime

# ======================================================
# PATH CONFIG
# ======================================================

BASE_DIR = Path(__file__).resolve().parents[1]

JSON_NODES_DIR = BASE_DIR / "json_nodes"
OUTPUT_GRAPH = BASE_DIR / "data" / "graphs" / "merged_graph.json"

OUTPUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)


# ======================================================
# UTILITIES
# ======================================================

def display_name_from_slug(slug: str) -> str:
    """Convert snake_case → Title Case."""
    return slug.replace("_", " ").title()


def iter_subject_files():
    """
    Yield:
        subject_id, subject_name, json_file_path
    """
    for subject_dir in JSON_NODES_DIR.iterdir():
        if not subject_dir.is_dir():
            continue

        subject_id = subject_dir.name
        subject_name = display_name_from_slug(subject_id)

        for json_file in subject_dir.glob("*.json"):
            if json_file.name.lower() == "metadata.json":
                continue
            yield subject_id, subject_name, json_file


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ======================================================
# MERGE LOGIC
# ======================================================

def merge_graph():
    graph = {
        "nodes": {},
        "edges": [],
        "metadata": {
            "built_at": datetime.utcnow().isoformat(),
            "subjects": {}
        }
    }

    print("🔍 Scanning subject folders...")

    for subject_id, subject_name, json_path in iter_subject_files():
        print(f"   • {subject_name:<35} ← {json_path.name}")

        payload = load_json(json_path)

        # Register subject globally
        graph["metadata"]["subjects"].setdefault(subject_id, {
            "subject_id": subject_id,
            "display_name": subject_name,
            "files": []
        })
        graph["metadata"]["subjects"][subject_id]["files"].append(json_path.name)

        # ----------------------------------------
        # Case 1 — Graph JSON
        # ----------------------------------------
        if isinstance(payload, dict) and "nodes" in payload and "edges" in payload:

            for node_name, node_data in payload["nodes"].items():
                node = graph["nodes"].setdefault(node_name, node_data)

                meta = node.setdefault("metadata", {})
                meta.setdefault("subjects", set()).add(subject_id)
                meta.setdefault("source_files", set()).add(json_path.name)

            for edge in payload["edges"]:
                if edge not in graph["edges"]:
                    graph["edges"].append(edge)

        # ----------------------------------------
        # Case 2 — Entity JSON
        # ----------------------------------------
        elif isinstance(payload, dict) and "entity" in payload:
            entity = payload["entity"]

            node = graph["nodes"].setdefault(entity, {
                "type": payload.get("type", "Concept"),
                "domain": payload.get("domain", ""),
                "definition": payload.get("definition", ""),
                "description": payload.get("description", ""),
                "properties": payload.get("properties", {}),
                "metadata": {}
            })

            meta = node.setdefault("metadata", {})
            meta.setdefault("subjects", set()).add(subject_id)
            meta.setdefault("source_files", set()).add(json_path.name)

            for rel in payload.get("relations", []):
                edge = {
                    "source": entity,
                    "type": rel.get("type", "related_to"),
                    "target": rel.get("target")
                }
                if edge not in graph["edges"]:
                    graph["edges"].append(edge)

        # ----------------------------------------
        # Case 3 — List of entities
        # ----------------------------------------
        elif isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict) or "entity" not in item:
                    continue

                entity = item["entity"]

                node = graph["nodes"].setdefault(entity, {
                    "type": item.get("type", "Concept"),
                    "domain": item.get("domain", ""),
                    "definition": item.get("definition", ""),
                    "description": item.get("description", ""),
                    "properties": item.get("properties", {}),
                    "metadata": {}
                })

                meta = node.setdefault("metadata", {})
                meta.setdefault("subjects", set()).add(subject_id)
                meta.setdefault("source_files", set()).add(json_path.name)

                for rel in item.get("relations", []):
                    edge = {
                        "source": entity,
                        "type": rel.get("type", "related_to"),
                        "target": rel.get("target")
                    }
                    if edge not in graph["edges"]:
                        graph["edges"].append(edge)

        else:
            print(f"⚠️ Skipped unsupported JSON format: {json_path}")

    # ----------------------------------------
    # Normalize metadata sets → lists
    # ----------------------------------------
    for node in graph["nodes"].values():
        meta = node.get("metadata", {})
        meta["subjects"] = sorted(list(meta.get("subjects", [])))
        meta["source_files"] = sorted(list(meta.get("source_files", [])))

    print("\n✅ Merge completed")
    print(f"   Nodes : {len(graph['nodes'])}")
    print(f"   Edges : {len(graph['edges'])}")
    print(f"   Subjects : {len(graph['metadata']['subjects'])}")

    return graph


# ======================================================
# SAVE
# ======================================================

def save_graph(graph):
    OUTPUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_GRAPH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Graph saved to: {OUTPUT_GRAPH}")


# ======================================================
# MAIN
# ======================================================

if __name__ == "__main__":
    graph = merge_graph()
    save_graph(graph)
```

---

---

# 🃏 PIPELINE 2 — Subject-Aware Flashcard Generator

Create file:

```
pipelines/generate_flashcards.py
```

---

## ✅ Full Code — `pipelines/generate_flashcards.py`

```python
import json
from pathlib import Path

# ======================================================
# PATH CONFIG
# ======================================================

BASE_DIR = Path(__file__).resolve().parents[1]

GRAPH_FILE = BASE_DIR / "data" / "graphs" / "merged_graph.json"
FLASHCARD_FILE = BASE_DIR / "data" / "flashcards" / "flashcards.json"

FLASHCARD_FILE.parent.mkdir(parents=True, exist_ok=True)


# ======================================================
# GENERATION
# ======================================================

def generate_flashcards():
    if not GRAPH_FILE.exists():
        raise FileNotFoundError(f"Graph not found: {GRAPH_FILE}")

    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        graph = json.load(f)

    flashcards = []

    for entity, props in graph["nodes"].items():

        # Skip empty placeholder nodes
        if not any([
            props.get("definition"),
            props.get("description"),
            props.get("properties")
        ]):
            continue

        meta = props.get("metadata", {})

        subjects = meta.get("subjects", [])
        sources = meta.get("source_files", [])

        domain = props.get("domain", "General")
        definition = props.get("definition", "No definition available.")
        description = props.get("description", "")
        properties = props.get("properties", {})

        facts = []
        for k, v in properties.items():
            if isinstance(v, list):
                v = ", ".join(map(str, v))
            facts.append(f"**{k}:** {v}")

        flashcards.append({
            "entity": entity,
            "domain": domain,
            "subjects": subjects,
            "sources": sources,
            "front": f"🧩 {entity}\n📘 Domain: {domain}\n📚 Subjects: {', '.join(subjects)}",
            "back": (
                f"**Definition:** {definition}\n\n"
                f"**Description:** {description}\n\n"
                + "\n".join(facts)
            ).strip()
        })

    with open(FLASHCARD_FILE, "w", encoding="utf-8") as f:
        json.dump(flashcards, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {len(flashcards)} flashcards")
    print(f"💾 Saved to {FLASHCARD_FILE}")


# ======================================================
# MAIN
# ======================================================

if __name__ == "__main__":
    generate_flashcards()
```

---

---

# 🖥 STEP 3 — Update Flashcard UI Filter

Modify:

```
pages/5_Flashcard_per_subject.py
```

---

### 🔁 Replace your filtering section with:

```python
# -------------------------------
# SUBJECT FILTERING
# -------------------------------

all_subjects = sorted({
    s for card in flashcards
    for s in card.get("subjects", [])
})

selected_subjects = st.multiselect(
    "Choose one or more subjects:",
    options=all_subjects,
    default=all_subjects
)

filtered_cards = [
    c for c in flashcards
    if any(s in selected_subjects for s in c.get("subjects", []))
]
```

Everything else can remain unchanged.

---

---

# ▶️ How To Run

From project root:

```bash
python pipelines/merge_graph.py
python pipelines/generate_flashcards.py
streamlit run app/app_streamlit.py
```

---

---

# ✅ What You Now Have

✔ Recursive subject ingestion
✔ Unlimited subjects
✔ Provenance preserved
✔ Flashcards filtered by subject
✔ No brittle filename parsing
✔ Future-proof structure

Drop a new folder:

```
json_nodes/deep_learning/01_data.json
```

Re-run pipelines → instantly available everywhere.

---

---

# 🚀 If You Want Next

I can also give you:

✅ Subject → Chapter auto-mapping
✅ Subject coverage dashboard
✅ Missing concept detector
✅ Curriculum sequencing
✅ Export to Anki
✅ Knowledge gap analytics

Just tell me 👍
