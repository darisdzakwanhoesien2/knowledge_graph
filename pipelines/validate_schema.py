import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
GRAPH = BASE_DIR / "data" / "graphs" / "merged_graph.json"

data = json.loads(GRAPH.read_text(encoding="utf-8"))

errors = []

for n, node in data.get("nodes", {}).items():
    if "metadata" not in node:
        errors.append(n)

if errors:
    print("❌ Missing metadata:", errors)
else:
    print("✅ Schema valid")
