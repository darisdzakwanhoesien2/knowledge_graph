import json
from pyvis.network import Network

# --- CONFIG ---
GRAPH_FILE = "merged_graph.json"
OUTPUT_FILE = "knowledge_graph.html"

# --- LOAD MERGED GRAPH ---
with open(GRAPH_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

net = Network(height="750px", width="100%", bgcolor="#111111", font_color="white", directed=True)
net.barnes_hut(gravity=-20000, central_gravity=0.3, spring_length=150, spring_strength=0.02)

# --- ADD NODES ---
for entity, props in data["nodes"].items():
    domain = props.get("domain", "Unknown")
    definition = props.get("definition", "")
    label = f"{entity}"
    title = f"<b>{entity}</b><br>{definition}<br><i>{domain}</i>"
    net.add_node(entity, label=label, title=title, group=domain)

# --- ADD EDGES ---
for edge in data["edges"]:
    net.add_edge(edge["source"], edge["target"], title=edge["type"], label=edge["type"])

# --- SAVE TO HTML ---
net.show(OUTPUT_FILE)
print(f"✅ Interactive graph saved to {OUTPUT_FILE}")
