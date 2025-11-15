import streamlit as st
import json
import difflib
from pathlib import Path
import networkx as nx

# ==============================
# CONFIGURATION
# ==============================
BASE_DIR = Path(__file__).resolve().parents[1]
GRAPH_FILE = BASE_DIR / "merged_graph.json"
MERGE_LOG = BASE_DIR / "merge_log.txt"

st.set_page_config(page_title="🧹 Node Cleanup", layout="wide")
st.title("🧹 Knowledge Graph — Node Cleanup & QA")

# ==============================
# LOAD GRAPH DATA
# ==============================
if not GRAPH_FILE.exists():
    st.error("❌ merged_graph.json not found. Please run build_graph.py first.")
    st.stop()

with open(GRAPH_FILE, "r", encoding="utf-8") as f:
    graph_data = json.load(f)

G = nx.DiGraph()
for node_name, props in graph_data["nodes"].items():
    G.add_node(node_name, **props)
for edge in graph_data["edges"]:
    G.add_edge(edge["source"], edge["target"], type=edge["type"])

# ==============================
# HELPER FUNCTIONS
# ==============================
def find_incomplete_nodes(graph):
    """Return all nodes missing definition/domain/description."""
    incomplete = []
    for node, props in graph.nodes(data=True):
        if (
            not props.get("domain")
            and not props.get("definition")
            and not props.get("description")
            and not props.get("properties")
        ):
            incomplete.append(node)
    return sorted(incomplete)

def find_complete_nodes(graph):
    """Return nodes that have domain, definition, and description."""
    complete = []
    for node, props in graph.nodes(data=True):
        if (
            props.get("domain")
            or props.get("definition")
            or props.get("description")
            or props.get("properties")
        ):
            complete.append(node)
    return sorted(complete)

def suggest_merges(node_name, candidates):
    """Fuzzy matching to find best merge targets."""
    return difflib.get_close_matches(node_name, candidates, n=5, cutoff=0.3)

def merge_nodes(graph_data, old_node, new_node):
    """Merge one node into another."""
    old_props = graph_data["nodes"].get(old_node, {})
    new_props = graph_data["nodes"].get(new_node, {})

    # Merge properties
    merged_props = new_props.get("properties", {})
    merged_props.update(old_props.get("properties", {}))
    graph_data["nodes"][new_node]["properties"] = merged_props

    # Merge domain/definition/description if missing
    for key in ["domain", "definition", "description"]:
        if not new_props.get(key) and old_props.get(key):
            graph_data["nodes"][new_node][key] = old_props[key]

    # Redirect edges
    for edge in graph_data["edges"]:
        if edge["source"] == old_node:
            edge["source"] = new_node
        if edge["target"] == old_node:
            edge["target"] = new_node

    # Remove node
    if old_node in graph_data["nodes"]:
        del graph_data["nodes"][old_node]

    # Log
    with open(MERGE_LOG, "a", encoding="utf-8") as log:
        log.write(f"Merged {old_node} → {new_node}\n")

    return graph_data

def save_graph(graph_data):
    with open(GRAPH_FILE, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    st.success("💾 Graph saved successfully!")


# ==============================
# COMPLETE NODES
# ==============================
st.header("✅ Complete Nodes")

complete_nodes = find_complete_nodes(G)
st.write(f"Found **{len(complete_nodes)}** complete nodes (nodes with metadata).")

st.dataframe({"Complete Nodes": complete_nodes})

st.download_button(
    "⬇️ Download Complete Nodes as JSON",
    data=json.dumps(complete_nodes, indent=2),
    file_name="complete_nodes.json"
)

st.divider()

# ==============================
# INCOMPLETE NODES
# ==============================
st.header("⚠️ Incomplete Nodes")

incomplete_nodes = find_incomplete_nodes(G)
if not incomplete_nodes:
    st.success("🎉 No incomplete nodes — everything is fully enriched!")
    st.stop()

st.write(f"Found **{len(incomplete_nodes)}** incomplete nodes.")
st.dataframe({"Incomplete Nodes": incomplete_nodes})

st.download_button(
    "⬇️ Download Incomplete Nodes as JSON",
    data=json.dumps(incomplete_nodes, indent=2),
    file_name="incomplete_nodes.json"
)

st.divider()

# ==============================
# MERGE TOOL
# ==============================
st.header("🔧 Fix / Merge Incomplete Nodes")

col1, col2 = st.columns(2)

with col1:
    selected_incomplete = st.selectbox("Select incomplete node:", [""] + incomplete_nodes)

with col2:
    all_defined_nodes = sorted(list(graph_data["nodes"].keys()))
    selected_merge_target = st.selectbox("Merge into (existing node):", [""] + all_defined_nodes)

if selected_incomplete:
    st.subheader(f"🔍 Suggestions for: `{selected_incomplete}`")
    suggestions = suggest_merges(selected_incomplete, all_defined_nodes)
    if suggestions:
        st.info("Recommended merge targets:")
        st.write(suggestions)
    else:
        st.warning("No close matches found automatically.")

# ==============================
# MERGE ACTION
# ==============================
if st.button("🚀 Merge Now"):
    if not selected_incomplete or not selected_merge_target:
        st.warning("Please select both nodes.")
    elif selected_incomplete == selected_merge_target:
        st.warning("Cannot merge a node into itself.")
    else:
        graph_data = merge_nodes(
            graph_data,
            old_node=selected_incomplete,
            new_node=selected_merge_target
        )
        save_graph(graph_data)
        st.rerun()
