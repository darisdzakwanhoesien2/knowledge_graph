import streamlit as st
import json
import networkx as nx
from pyvis.network import Network
from pathlib import Path
import tempfile
from datetime import datetime

# --- CONFIG ---
GRAPH_FILE = "merged_graph.json"
MERGE_LOG = "merge_log.txt"

# --- STREAMLIT SETTINGS ---
st.set_page_config(page_title="Knowledge Graph Explorer", layout="wide")
st.title("🧠 Knowledge Graph Explorer")

# --- LOAD GRAPH ---
if not Path(GRAPH_FILE).exists():
    st.error("merged_graph.json not found. Please run build_graph.py first.")
    st.stop()

with open(GRAPH_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# --- CONSTRUCT NETWORKX GRAPH ---
G = nx.DiGraph()
for node_name, props in data["nodes"].items():
    G.add_node(node_name, **props)
for edge in data["edges"]:
    G.add_edge(edge["source"], edge["target"], type=edge["type"])

# --- HELPER FUNCTIONS ---

def save_graph(graph_data):
    """Save merged graph to file."""
    with open(GRAPH_FILE, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    st.toast("💾 Graph saved successfully!", icon="💾")

def log_merge(old_node, new_node):
    """Log manual merges for traceability."""
    with open(MERGE_LOG, "a", encoding="utf-8") as log:
        log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {old_node} → {new_node}\n")

def merge_nodes(graph_data, old_node, new_node):
    """Merge one node into another (manual QA)."""
    if old_node not in graph_data["nodes"] or new_node not in graph_data["nodes"]:
        st.error("One or both selected nodes do not exist in the graph.")
        return graph_data, False

    old_data = graph_data["nodes"][old_node]
    new_data = graph_data["nodes"][new_node]

    # Merge properties
    new_data["properties"].update(old_data.get("properties", {}))
    if not new_data.get("domain") and old_data.get("domain"):
        new_data["domain"] = old_data["domain"]

    # Redirect edges
    for edge in graph_data["edges"]:
        if edge["source"] == old_node:
            edge["source"] = new_node
        if edge["target"] == old_node:
            edge["target"] = new_node

    # Remove duplicate node
    del graph_data["nodes"][old_node]

    # Log and notify
    log_merge(old_node, new_node)
    st.success(f"✅ Merged '{old_node}' into '{new_node}' successfully.")
    return graph_data, True


def draw_graph(graph, show_labels=True):
    """Generate Pyvis HTML graph visualization."""
    net = Network(height="700px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
    net.barnes_hut(gravity=-20000, central_gravity=0.3, spring_length=150, spring_strength=0.02)

    for node, props in graph.nodes(data=True):
        title = f"<b>{node}</b><br>{props.get('definition','')}<br><i>{props.get('domain','')}</i>"
        net.add_node(node, label=node, title=title, group=props.get("domain", "Unknown"))

    for src, tgt, rel in graph.edges(data=True):
        net.add_edge(src, tgt, title=rel["type"], label=rel["type"] if show_labels else "")

    return net

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Search & Filter")
search_query = st.sidebar.text_input("Search for entity name or domain:")
selected_domain = st.sidebar.selectbox(
    "Filter by domain",
    ["All"] + sorted({props.get("domain", "Unknown") for _, props in data["nodes"].items()})
)
show_relations = st.sidebar.checkbox("Show relation labels", value=True)

# --- FILTER GRAPH ---
filtered_nodes = []
for node, props in G.nodes(data=True):
    if (
        (not search_query or search_query.lower() in node.lower() or search_query.lower() in props.get("definition", "").lower())
        and (selected_domain == "All" or props.get("domain", "") == selected_domain)
    ):
        filtered_nodes.append(node)

H = G.subgraph(filtered_nodes).copy()

# --- GRAPH VISUALIZATION ---
net = draw_graph(H, show_labels=show_relations)

# --- SAVE TO TEMP HTML AND DISPLAY ---
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
    net.save_graph(tmp.name)
    html_path = tmp.name

st.components.v1.html(open(html_path, "r", encoding="utf-8").read(), height=750)

# --- NODE DETAILS ---
if filtered_nodes:
    st.sidebar.subheader("🧩 Node Details")
    selected_node = st.sidebar.selectbox("Select a node to inspect:", filtered_nodes)
    props = G.nodes[selected_node]
    st.sidebar.markdown(f"**Entity:** {selected_node}")
    st.sidebar.markdown(f"**Domain:** {props.get('domain', 'N/A')}")
    st.sidebar.markdown(f"**Definition:** {props.get('definition', 'N/A')}")
    st.sidebar.markdown(f"**Description:** {props.get('description', 'N/A')}")
    if props.get("properties"):
        st.sidebar.markdown("**Properties:**")
        for key, value in props["properties"].items():
            st.sidebar.markdown(f"- **{key}:** {value}")

# --- MANUAL MERGE QA ---
st.sidebar.markdown("---")
st.sidebar.subheader("🧠 Manual Merge QA")

with st.sidebar.expander("Merge Duplicate or Similar Nodes", expanded=False):
    all_nodes = sorted(list(G.nodes.keys()))
    node_to_merge = st.selectbox("Merge this node (old/duplicate):", [""] + all_nodes, key="old_merge")
    node_target = st.selectbox("Into this node (canonical):", [""] + all_nodes, key="new_merge")

    if st.button("🔄 Merge Nodes"):
        if node_to_merge and node_target and node_to_merge != node_target:
            merged_graph, merged = merge_nodes(data, node_to_merge, node_target)
            if merged:
                save_graph(merged_graph)
                st.experimental_rerun()
        else:
            st.warning("Please select two *different* nodes to merge.")
