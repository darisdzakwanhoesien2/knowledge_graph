import streamlit as st
import json
import networkx as nx
from pyvis.network import Network
from pathlib import Path
import tempfile

# --- CONFIG ---
GRAPH_FILE = "merged_graph.json"

# --- STREAMLIT SETTINGS ---
st.set_page_config(page_title="Knowledge Graph Explorer", layout="wide")
st.title("🧠 Knowledge Graph Explorer")

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

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Search & Filter")
search_query = st.sidebar.text_input("Search for entity name or domain:")
selected_domain = st.sidebar.selectbox("Filter by domain", ["All"] + sorted({props.get("domain", "Unknown") for _, props in data["nodes"].items()}))
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

# --- CREATE VISUALIZATION ---
def draw_graph(graph, show_labels=True):
    net = Network(height="700px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
    net.barnes_hut(gravity=-20000, central_gravity=0.3, spring_length=150, spring_strength=0.02)
    for node, props in graph.nodes(data=True):
        title = f"<b>{node}</b><br>{props.get('definition','')}<br><i>{props.get('domain','')}</i>"
        net.add_node(node, label=node, title=title, group=props.get("domain", "Unknown"))
    for src, tgt, rel in graph.edges(data=True):
        net.add_edge(src, tgt, title=rel["type"], label=rel["type"] if show_labels else "")
    return net

net = draw_graph(H, show_labels=show_relations)

# --- SAVE TO TEMP HTML ---
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
    net.save_graph(tmp.name)
    html_path = tmp.name

# --- DISPLAY GRAPH ---
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
