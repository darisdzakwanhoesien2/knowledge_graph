import json
from datetime import datetime

GRAPH_FILE = "merged_graph.json"
MERGE_LOG = "merge_log.txt"

def load_graph(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_graph(graph, path):
    graph["metadata"]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

def log_merge(old_node, new_node):
    with open(MERGE_LOG, "a", encoding="utf-8") as log:
        log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {old_node} → {new_node}\n")

def merge_nodes(graph, old_node, new_node):
    """Merge old_node into new_node and update edges."""
    if old_node not in graph["nodes"]:
        print(f"⚠️ '{old_node}' not found in graph.")
        return graph
    if new_node not in graph["nodes"]:
        print(f"⚠️ '{new_node}' not found in graph.")
        return graph

    old_data = graph["nodes"][old_node]
    new_data = graph["nodes"][new_node]

    # Merge properties
    new_data["properties"].update(old_data.get("properties", {}))
    if not new_data.get("domain") and old_data.get("domain"):
        new_data["domain"] = old_data["domain"]

    # Redirect edges
    for edge in graph["edges"]:
        if edge["source"] == old_node:
            edge["source"] = new_node
        if edge["target"] == old_node:
            edge["target"] = new_node

    # Remove duplicate node
    del graph["nodes"][old_node]

    log_merge(old_node, new_node)
    print(f"✅ Merged '{old_node}' → '{new_node}' successfully.")
    return graph


if __name__ == "__main__":
    graph = load_graph(GRAPH_FILE)
    print(f"📦 Loaded graph with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges.\n")

    while True:
        print("\n--- Manual Merge Utility ---")
        old_node = input("Enter the node to merge (old/duplicate name): ").strip()
        if not old_node:
            print("🚪 Exiting merge utility.")
            break
        new_node = input("Enter the target node (canonical name): ").strip()

        graph = merge_nodes(graph, old_node, new_node)

        save_graph(graph, GRAPH_FILE)
        print(f"💾 Graph saved. ({len(graph['nodes'])} nodes total)\n")
