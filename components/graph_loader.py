import json
import networkx as nx
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
GRAPH_FILE = BASE_DIR / "data" / "graphs" / "merged_graph.json"


def load_graph():
    if not GRAPH_FILE.exists():
        raise FileNotFoundError(f"Graph not found: {GRAPH_FILE}")

    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    G = nx.DiGraph()

    for node, props in data.get("nodes", {}).items():
        G.add_node(node, **props)

    for edge in data.get("edges", []):
        G.add_edge(
            edge.get("source"),
            edge.get("target"),
            type=edge.get("type", "related_to")
        )

    return G, data
