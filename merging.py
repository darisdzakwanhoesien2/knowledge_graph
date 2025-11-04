import json
import os
from datetime import datetime

# --- CONFIG ---
INPUT_FOLDER = "json_nodes"
OUTPUT_FILE = "merged_graph.json"

# --- STEP 1: Load all JSON files ---
def load_json_nodes(folder):
    data_list = []
    for file in os.listdir(folder):
        if file.endswith(".json"):
            path = os.path.join(folder, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        data_list.extend(data)
                    else:
                        data_list.append(data)
            except Exception as e:
                print(f"⚠️ Error loading {file}: {e}")
    return data_list


# --- STEP 2: Merge nodes and relations ---
def merge_graph(json_list):
    graph = {"nodes": {}, "edges": []}
    
    for entry in json_list:
        entity = entry["entity"]
        
        # Merge or create node
        if entity not in graph["nodes"]:
            graph["nodes"][entity] = {
                "type": entry.get("type", "Concept"),
                "domain": entry.get("domain", ""),
                "definition": entry.get("definition", ""),
                "description": entry.get("description", ""),
                "properties": entry.get("properties", {}),
                "metadata": entry.get("metadata", {}),
            }
        else:
            # Merge properties if new ones exist
            existing = graph["nodes"][entity]
            existing["properties"].update(entry.get("properties", {}))
        
        # Add relations as edges
        for rel in entry.get("relations", []):
            edge = {
                "source": entity,
                "type": rel["type"],
                "target": rel["target"],
            }
            # Prevent duplicates
            if edge not in graph["edges"]:
                graph["edges"].append(edge)
    
    return graph


# --- STEP 3: Save unified graph ---
def save_graph(graph, path):
    graph["metadata"] = {
        "last_built": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "node_count": len(graph["nodes"]),
        "edge_count": len(graph["edges"])
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"✅ Merged graph saved to {path}")


# --- MAIN RUNNER ---
if __name__ == "__main__":
    print("🔍 Loading JSON knowledge nodes...")
    json_list = load_json_nodes(INPUT_FOLDER)
    print(f"📦 Loaded {len(json_list)} files.")

    print("🔗 Merging into unified graph...")
    merged_graph = merge_graph(json_list)

    print("💾 Saving result...")
    save_graph(merged_graph, OUTPUT_FILE)

    print("🌐 Done! Knowledge graph now has:")
    print(f"   • {len(merged_graph['nodes'])} nodes")
    print(f"   • {len(merged_graph['edges'])} edges")