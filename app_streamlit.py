import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components.graph_loader import load_graph
from core.attempts import list_attempts
from core.packages import list_packages, load_package

st.set_page_config(page_title="🧠 Knowledge Graph Learning Studio", layout="wide")
st.title("🧠 Knowledge Graph Learning Studio")

st.markdown(
    "Local-first learning loop: **ingest → graph → flashcards → assessments → results → remediation**."
)

try:
    G, raw = load_graph()
    subjects = raw.get("metadata", {}).get("subjects", {})
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Subjects", len(subjects))
    c2.metric("Nodes", G.number_of_nodes())
    c3.metric("Edges", G.number_of_edges())
    pkgs = [p for e in list_packages()
            for p in [load_package(e["subject"], e["package_id"])] if p]
    published = sum(1 for p in pkgs if p.get("status") == "published")
    c4.metric("Question packages", f"{published}/{len(pkgs)}", help="published / total")
    attempts = list_attempts()
    c5.metric("Attempts", len(attempts))
except FileNotFoundError as e:
    st.error(f"{e}\n\nRun `python3 pipelines/merge_graph.py` to build the graph first.")
    st.stop()

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("📚 Study")
    st.page_link("pages/0_Global.py", label="Global overview of the graph", icon="🌐")
    st.page_link("pages/2_Find_Connection.py", label="Find a path between two concepts", icon="🔗")
    st.page_link("pages/3_Learn_From_Node.py", label="Study a concept in depth", icon="📖")
    st.page_link("pages/4_Flashcards.py", label="Browse flashcards", icon="🃏")
    st.page_link("pages/5_Flashcards_By_Subject.py", label="Flashcards by subject", icon="🗂️")

with right:
    st.subheader("🎯 Practice & curate")
    st.page_link("pages/9_Take_Test.py", label="Take a test from a published package", icon="🎯")
    st.page_link("pages/10_Review_Results.py", label="Review submissions & export CSV", icon="📊")
    st.page_link("pages/7_Author_Packages.py", label="Author question packages", icon="✍️")
    st.page_link("pages/8_PDF_Drafts.py", label="Scaffold drafts from a PDF", icon="📄")
    st.page_link("pages/6_Node_Cleanup.py", label="Check content quality", icon="🧹")

st.divider()

with st.expander("🗺️ Show full knowledge graph"):
    from components.visualizations import draw_graph

    net = draw_graph(G)
    st.components.v1.html(net.generate_html(), height=650)
