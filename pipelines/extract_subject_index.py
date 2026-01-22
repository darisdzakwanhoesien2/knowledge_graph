import json
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
GRAPH = BASE_DIR / "data" / "graphs" / "merged_graph.json"
OUT = BASE_DIR / "data" / "indexes" / "subject_index.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

graph = json.loads(GRAPH.read_text())

index = defaultdict(list)

for node, props in graph["nodes"].items():
    for s in props.get("metadata", {}).get("subjects", []):
        index[s].append(node)

OUT.write_text(json.dumps(index, indent=2))
print(f"✅ Subject index saved → {OUT}")
