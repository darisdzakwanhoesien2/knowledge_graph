import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
GRAPH = BASE_DIR / "data" / "graphs" / "merged_graph.json"

data = json.loads(GRAPH.read_text())

normalized = {}
for name, node in data["nodes"].items():
    key = name.strip()
    normalized[key] = node

data["nodes"] = normalized
GRAPH.write_text(json.dumps(data, indent=2))
print("✅ Graph normalized")
