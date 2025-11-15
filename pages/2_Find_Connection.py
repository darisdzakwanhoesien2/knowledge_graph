# ==============================================
# pages/1_Find_Connection.py
# ==============================================
import streamlit as st
import json
import networkx as nx
from pathlib import Path
from pyvis.network import Network
import os

# ==============================
# --- CONFIGURATION ---
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent  # project root
GRAPH_FILE = BASE_DIR / "merged_graph.json"

# ==============================
# --- PAGE SETTINGS ---
# ==============================
st.set_page_config(page_title="🔗 Find Connections", layout="wide")
st.title("🔗 Explore Relationships Between Two Nodes")

# ==============================
# --- LOAD GRAPH ---
# ==============================
if not GRAPH_FILE.exists():
    st.error(f"❌ merged_graph.json not found at: `{GRAPH_FILE}`")
    st.stop()

try:
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
except json.JSONDecodeError:
    st.error("⚠️ Failed to parse merged_graph.json — please check file integrity.")
    st.stop()

# Build NetworkX graph
G = nx.DiGraph()
for node_name, props in data["nodes"].items():
    G.add_node(node_name, **props)
for edge in data["edges"]:
    G.add_edge(edge["source"], edge["target"], type=edge.get("type", "related_to"))

# ==============================
# --- RELATION TRANSLATION ---
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_file = os.path.join(BASE_DIR, "../json_nodes/01_data.json")

# Load data dynamically
import json
with open(data_file, "r") as f:
    data = json.load(f)

RELATION_TRANSLATIONS = {
    # Populate dictionary using data
}

# ==============================
# --- SIDEBAR SELECTION ---
# ==============================
st.sidebar.header("🎯 Connection Finder")

all_nodes = sorted(list(G.nodes))

source_node = st.sidebar.selectbox("Select Source Node:", all_nodes, key="source_node")
target_node = st.sidebar.selectbox("Select Target Node:", all_nodes, key="target_node")
max_depth = st.sidebar.slider("🔍 Maximum Path Length", min_value=1, max_value=15, value=6)

find_button = st.sidebar.button("🚀 Find Connection")

# ==============================
# --- PATHFINDING FUNCTIONS ---
# ==============================
def find_paths(G, source, target, cutoff=6):
    """Find all simple paths between source and target (up to cutoff)."""
    try:
        return list(nx.all_simple_paths(G, source=source, target=target, cutoff=cutoff))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []

def find_shortest_path_length(G, source, target):
    """Find minimum path length (fewest hops) between nodes."""
    try:
        return nx.shortest_path_length(G, source=source, target=target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None

# ==============================
# --- VISUALIZATION FUNCTION ---
# ==============================
def visualize_path(G, path_nodes):
    """Generate PyVis visualization entirely in memory (no temp files)."""
    net = Network(height="700px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
    net.barnes_hut(gravity=-20000, central_gravity=0.3, spring_length=150, spring_strength=0.02)

    subgraph = G.subgraph(path_nodes).copy()

    for node, props in subgraph.nodes(data=True):
        if node == path_nodes[0]:
            color = "#00FFAA"
        elif node == path_nodes[-1]:
            color = "#00FFFF"
        else:
            color = "#FFD700"
        title = f"<b>{node}</b><br>{props.get('definition', '')}<br><i>{props.get('domain', '')}</i>"
        net.add_node(node, label=node, title=title, color=color, group=props.get("domain", "Unknown"))

    for src, tgt, rel in subgraph.edges(data=True):
        net.add_edge(src, tgt, title=rel["type"], label=rel["type"])

    # Render in-memory HTML
    html_str = net.generate_html()
    st.components.v1.html(html_str, height=750)

# ==============================
# --- MAIN EXECUTION ---
# ==============================
if find_button:
    if source_node == target_node:
        st.warning("Please select two *different* nodes.")
    else:
        min_length = find_shortest_path_length(G, source_node, target_node)
        if min_length is not None:
            st.info(f"📏 Minimum path length between '{source_node}' and '{target_node}': **{min_length} step(s)**")
        else:
            st.warning(f"⚠️ No direct or indirect path found between '{source_node}' and '{target_node}'.")

        paths = find_paths(G, source_node, target_node, cutoff=max_depth)
        if not paths:
            st.error(f"No connection found between '{source_node}' and '{target_node}' within depth {max_depth}.")
        else:
            st.success(f"✅ Found {len(paths)} connection path(s) within max depth {max_depth}.")
            for i, path in enumerate(paths[:3]):  # limit for readability
                st.markdown(f"### 🧭 Path {i+1}")
                st.markdown(f"**{' → '.join(path)}**")

                # --- Extract edge relations ---
                relations = []
                for j in range(len(path) - 1):
                    edge_data = G.get_edge_data(path[j], path[j + 1])
                    rel = edge_data["type"] if edge_data else "related_to"
                    relations.append(rel)

                # --- Narrative text ---
                narrative_parts = []
                for k in range(len(path) - 1):
                    narrative_parts.append(path[k])
                    readable_rel = RELATION_TRANSLATIONS.get(relations[k], relations[k])
                    narrative_parts.append(readable_rel)
                narrative_parts.append(path[-1])
                narrative_sentence = " ".join(narrative_parts)
                narrative_sentence = narrative_sentence[0].upper() + narrative_sentence[1:] + "."

                st.markdown("**🧩 Narrative Connection:**")
                st.write(narrative_sentence)

                rel_chain = " → ".join([f"({r})" for r in relations])
                st.caption(f"Relations: {rel_chain}")

                visualize_path(G, path)