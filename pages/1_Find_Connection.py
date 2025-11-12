# ==============================================
# pages/1_Find_Connection.py
# ==============================================
import streamlit as st
import json
import networkx as nx
from pathlib import Path
from pyvis.network import Network
import tempfile

# ==============================
# --- CONFIG ---
# ==============================
GRAPH_FILE = "merged_graph.json"

# ==============================
# --- PAGE SETTINGS ---
# ==============================
st.set_page_config(page_title="🔗 Find Connections", layout="wide")
st.title("🔗 Explore Relationships Between Two Nodes")

# --- LOAD GRAPH ---
if not Path(GRAPH_FILE).exists():
    st.error("merged_graph.json not found. Please run build_graph.py first.")
    st.stop()

with open(GRAPH_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

G = nx.DiGraph()
for node_name, props in data["nodes"].items():
    G.add_node(node_name, **props)
for edge in data["edges"]:
    G.add_edge(edge["source"], edge["target"], type=edge["type"])

# ==============================
# --- SIDEBAR SELECTION ---
# ==============================
st.sidebar.header("🎯 Connection Finder")
all_nodes = sorted(list(G.nodes))

source_node = st.sidebar.selectbox("Select Source Node:", all_nodes, key="source_node")
target_node = st.sidebar.selectbox("Select Target Node:", all_nodes, key="target_node")

max_depth = st.sidebar.slider("🔍 Maximum Path Length", min_value=1, max_value=6, value=4)

find_button = st.sidebar.button("🚀 Find Connection")

# ==============================
# --- FIND CONNECTION ---
# ==============================
def find_paths(G, source, target, cutoff=4):
    """Find all simple paths between source and target (up to cutoff)."""
    try:
        paths = list(nx.all_simple_paths(G, source=source, target=target, cutoff=cutoff))
        return paths
    except nx.NetworkXNoPath:
        return []
    except nx.NodeNotFound:
        return []

# ==============================
# --- VISUALIZATION FUNCTION ---
# ==============================
def visualize_path(G, path_nodes):
    """Visualize the found path in Pyvis."""
    net = Network(height="700px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
    net.barnes_hut(gravity=-20000, central_gravity=0.3, spring_length=150, spring_strength=0.02)

    # Highlight only the path subgraph
    subgraph = G.subgraph(path_nodes).copy()

    for node, props in subgraph.nodes(data=True):
        color = "#00FFAA" if node in [path_nodes[0], path_nodes[-1]] else "#FFD700"
        title = f"<b>{node}</b><br>{props.get('definition', '')}<br><i>{props.get('domain', '')}</i>"
        net.add_node(node, label=node, title=title, color=color, group=props.get("domain", "Unknown"))

    for src, tgt, rel in subgraph.edges(data=True):
        net.add_edge(src, tgt, title=rel["type"], label=rel["type"])

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        return tmp.name

# ==============================
# --- EXECUTION ---
# ==============================
if find_button:
    if source_node == target_node:
        st.warning("Please select two *different* nodes.")
    else:
        paths = find_paths(G, source_node, target_node, cutoff=max_depth)
        if not paths:
            st.error(f"No connection found between '{source_node}' and '{target_node}' within depth {max_depth}.")
        else:
            st.success(f"✅ Found {len(paths)} connection path(s) between the nodes!")
            for i, path in enumerate(paths[:3]):  # show up to 3 paths
                st.markdown(f"### 🧭 Path {i+1}")
                path_str = " → ".join(path)
                st.markdown(f"**{path_str}**")

                # Annotate with edge types
                relation_text = []
                for j in range(len(path) - 1):
                    edge_data = G.get_edge_data(path[j], path[j + 1])
                    if edge_data:
                        relation_text.append(f"({edge_data['type']})")
                if relation_text:
                    rel_chain = " → ".join(relation_text)
                    st.caption(f"Relations: {rel_chain}")

                # Visualize
                html_path = visualize_path(G, path)
                st.components.v1.html(open(html_path, "r", encoding="utf-8").read(), height=750)
