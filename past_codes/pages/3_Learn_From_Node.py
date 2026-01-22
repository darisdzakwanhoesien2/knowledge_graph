# ==============================================
# pages/2_Learn_From_Node.py
# ==============================================
import streamlit as st
import json
import networkx as nx
from pathlib import Path
from pyvis.network import Network

# ==============================
# --- CONFIGURATION ---
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent
GRAPH_FILE = BASE_DIR / "merged_graph.json"

# ==============================
# --- PAGE SETTINGS ---
# ==============================
st.set_page_config(page_title="📘 Learn From Node", layout="wide")
st.title("📘 Learn From Any Node")

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
    st.error("⚠️ merged_graph.json is corrupted or unreadable.")
    st.stop()

# Build graph
G = nx.DiGraph()

# Add defined nodes from merged_graph.json
defined_nodes = set(data["nodes"].keys())

for node_name, props in data["nodes"].items():
    G.add_node(node_name, **props)

# Add edges → may create ghost nodes
for edge in data["edges"]:
    G.add_edge(edge["source"], edge["target"], type=edge.get("type", "related_to"))

# Identify ghost nodes (nodes created from edges only)
graph_nodes = set(G.nodes)
ghost_nodes = graph_nodes - defined_nodes

# ==============================
# --- RELATION TRANSLATION ---
# ==============================
RELATION_TRANSLATIONS = {
    "used_in": "is used in",
    "extends": "extends",
    "includes": "includes",
    "is_a_goal_of": "is a goal of",
    "follows": "follows",
    "leads_to": "leads to",
    "part_of": "is part of",
    "related_to": "is related to",
    "influences": "influences",
    "supports": "supports",
    "affects": "affects",
}

# ==============================
# --- SIDEBAR ---
# ==============================
st.sidebar.header("🧠 Learn From Node")
node_list = sorted(list(G.nodes))
selected_node = st.sidebar.selectbox("Select a node to explore:", node_list, index=0)

if not selected_node:
    st.stop()

# ==============================
# --- FETCH NODE PROPERTIES ---
# ==============================
props = G.nodes[selected_node]
incoming_edges = [(u, v, G[u][v]['type']) for u, v in G.in_edges(selected_node)]
outgoing_edges = [(u, v, G[u][v]['type']) for u, v in G.out_edges(selected_node)]

# ==============================
# --- NODE DETAILS ---
# ==============================
st.subheader(f"🔹 Concept: **{selected_node}**")

# Ghost node detection
if selected_node in ghost_nodes:
    st.warning("⚠️ This is an **incomplete ghost node** created because it appears in edges but is missing from the database.")
    node_type = "Ghost / Incomplete"
else:
    node_type = "Complete Node"

st.markdown(f"**Node Type:** `{node_type}`")

# Metadata fields (with safe fallback)
st.markdown(f"**Domain:** {props.get('domain', 'N/A') or 'N/A'}")
st.markdown(f"**Definition:** {props.get('definition', 'N/A') or 'N/A'}")
st.markdown(f"**Description:** {props.get('description', 'N/A') or 'N/A'}")

# Additional properties
if props.get("properties"):
    with st.expander("📦 Additional Properties", expanded=False):
        for key, value in props["properties"].items():
            st.markdown(f"- **{key}:** {value}")

# ==============================
# --- CONNECTIONS ---
# ==============================
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔁 Incoming (Prerequisites)")
    if not incoming_edges:
        st.info("No incoming connections.")
    else:
        for u, v, rel in incoming_edges:
            readable = RELATION_TRANSLATIONS.get(rel, rel)
            st.markdown(f"- **{u}** → {selected_node} ({readable})")

with col2:
    st.markdown("### 🔀 Outgoing (Consequences)")
    if not outgoing_edges:
        st.info("No outgoing connections.")
    else:
        for u, v, rel in outgoing_edges:
            readable = RELATION_TRANSLATIONS.get(rel, rel)
            st.markdown(f"- {selected_node} → **{v}** ({readable})")

# ==============================
# --- LEARNING NARRATIVE ---
# ==============================
st.markdown("---")
st.subheader("🧩 Learning Narrative")

incoming_nodes = [u for u, _, _ in incoming_edges]
outgoing_nodes = [v for _, v, _ in outgoing_edges]

if not incoming_nodes and not outgoing_nodes:
    st.write("This node is isolated — no conceptual relationships found.")
else:
    narrative = []
    if incoming_nodes:
        narrative.append(f"**{selected_node}** is influenced by {', '.join(incoming_nodes)}.")
    if outgoing_nodes:
        narrative.append(f"It contributes to or leads to {', '.join(outgoing_nodes)}.")
    st.write(" ".join(narrative))

# ==============================
# --- LEARNING ORDER ---
# ==============================
st.markdown("---")
st.subheader("🎯 Recommended Learning Order")

st.markdown(f"**Before:** {', '.join(incoming_nodes) if incoming_nodes else '—'}")
st.markdown(f"**Now:** {selected_node}")
st.markdown(f"**After:** {', '.join(outgoing_nodes) if outgoing_nodes else '—'}")

# ==============================
# --- VISUALIZATION ---
# ==============================
st.markdown("---")
st.subheader("🌐 Concept Neighborhood")

def visualize_node_context(G, center, incoming, outgoing):
    net = Network(height="750px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
    net.barnes_hut()

    # Center
    net.add_node(center, color="#00FFFF", size=25)

    # Incoming (green)
    for u, v, rel in incoming:
        net.add_node(u, color="#32CD32")
        net.add_edge(u, v, label=rel)

    # Outgoing (orange)
    for u, v, rel in outgoing:
        net.add_node(v, color="#FFA500")
        net.add_edge(u, v, label=rel)

    html = net.generate_html()
    st.components.v1.html(html, height=750)

visualize_node_context(G, selected_node, incoming_edges, outgoing_edges)

# ==============================
# --- FOOTNOTE ---
# ==============================
st.markdown("---")
st.caption("💡 Ghost nodes come from edges that reference undefined entities. They should be reviewed and merged in the cleanup page.")
