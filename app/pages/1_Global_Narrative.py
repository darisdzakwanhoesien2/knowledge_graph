import streamlit as st
import networkx as nx
from components.graph_loader import load_graph

st.title("📖 Global Narrative")

G, _ = load_graph()
deg = nx.degree_centrality(G)

top = sorted(deg.items(), key=lambda x: -x[1])[:10]
st.markdown("### 🔝 Most Central Concepts")
for n, s in top:
    st.write(f"- **{n}** ({round(s,3)})")
