import streamlit as st
from components.graph_loader import load_graph

st.title("🧹 Node Cleanup")

G, raw = load_graph()

incomplete = [
    n for n, p in G.nodes(data=True)
    if not p.get("definition")
]

st.write("### Incomplete Nodes")
st.write(incomplete)
