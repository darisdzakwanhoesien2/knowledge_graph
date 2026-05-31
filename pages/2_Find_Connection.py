import streamlit as st
import networkx as nx
from components.graph_loader import load_graph

st.title("🔗 Find Connection")

G, _ = load_graph()
nodes = sorted(G.nodes())

src = st.selectbox("Source", nodes)
dst = st.selectbox("Target", nodes)

if st.button("Find Path"):
    try:
        path = nx.shortest_path(G, src, dst)
        st.success(" → ".join(path))
    except nx.NetworkXNoPath:
        st.error("No path found.")
    except nx.NodeNotFound:
        st.error("Node not found (graph may have changed).")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
