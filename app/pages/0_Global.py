import streamlit as st
from components.graph_loader import load_graph
import pandas as pd

st.title("🌍 Global Overview")

G, _ = load_graph()

rows = []
for n, props in G.nodes(data=True):
    rows.append({
        "node": n,
        "degree": G.degree(n),
        "subjects": ", ".join(props.get("metadata", {}).get("subjects", []))
    })

df = pd.DataFrame(rows).sort_values("degree", ascending=False)
st.dataframe(df, use_container_width=True)
