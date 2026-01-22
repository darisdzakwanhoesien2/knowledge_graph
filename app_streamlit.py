import streamlit as st
from components.graph_loader import load_graph
from components.visualizations import draw_graph

st.set_page_config(page_title="🧠 Knowledge Graph", layout="wide")
st.title("🧠 Knowledge Graph Platform")

try:
    G, raw = load_graph()
except Exception as e:
    st.error(str(e))
    st.stop()

st.success(f"Loaded {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

net = draw_graph(G)
html = net.generate_html()
st.components.v1.html(html, height=750)
