# Notes (archived)

This file contains the prior README content that was previously located at `past_codes/README.md`.
It’s kept as a scratchpad / historical reference and is not guaranteed to be up to date with the current repo layout.

---

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

