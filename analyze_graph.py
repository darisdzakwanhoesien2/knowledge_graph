# =======================================
# analyze_graph.py
# =======================================
import json
import networkx as nx
from networkx.algorithms import community


def load_graph_from_json(json_path: str):
    """Load graph structure from a merged JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    G = nx.DiGraph()
    for node, props in data["nodes"].items():
        G.add_node(node, **props)
    for edge in data["edges"]:
        G.add_edge(edge["source"], edge["target"], type=edge["type"])
    return G


def structural_summary(json_path: str = "merged_graph.json"):
    """
    Analyze structural properties of a knowledge graph.
    Works for directed graphs but converts to undirected for community detection.
    """
    G = load_graph_from_json(json_path)

    # --- Compute key metrics ---
    degree_centrality = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G)

    # Convert to undirected for community detection
    G_undirected = G.to_undirected()
    communities = community.label_propagation_communities(G_undirected)

    # --- Extract highlights ---
    top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]
    bridges = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10]

    structural = {
        "Total Nodes": len(G.nodes),
        "Total Edges": len(G.edges),
        "Top Central Concepts": [n for n, _ in top_nodes],
        "Bridging Nodes": [n for n, _ in bridges],
        "Communities": [list(c)[:8] for c in communities],  # show up to 8 nodes per cluster
    }

    return structural


def export_summary_to_file(summary: dict, output_path: str = "graph_summary.json"):
    """Save structural summary results to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return output_path
