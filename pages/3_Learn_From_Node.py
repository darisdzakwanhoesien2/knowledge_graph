import streamlit as st
from components.graph_loader import load_graph

st.title("📘 Learn From Node")

G, _ = load_graph()
node = st.selectbox("Select node", sorted(G.nodes()))

props = G.nodes[node]
st.write("### Definition")
st.write(props.get("definition", "N/A"))

st.write("### Subjects")
st.write(", ".join(props.get("metadata", {}).get("subjects", [])))

st.write("### Neighbors")
st.write(list(G.successors(node)))
