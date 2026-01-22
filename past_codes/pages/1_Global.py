# ==============================================
# pages/3_Global_Overview.py
# ==============================================
import streamlit as st
import json
from pathlib import Path
import networkx as nx
import pandas as pd
import itertools

# Try importing Louvain modularity algorithm
try:
    import community as community_louvain   # package name: python-louvain
    _LOUVAIN_AVAILABLE = True
except Exception:
    _LOUVAIN_AVAILABLE = False

# ==============================================
# Streamlit Configuration
# ==============================================
st.set_page_config(page_title="🌐 Global Topic Overview", layout="wide")
st.title("🌐 Global Topic Overview — Chapters, Clusters & Curriculum")

# ==============================================
# Load merged_graph.json
# ==============================================
BASE_DIR = Path(__file__).resolve().parents[1]
GRAPH_FILE = BASE_DIR / "merged_graph.json"

if not GRAPH_FILE.exists():
    st.error(f"❌ merged_graph.json not found at: {GRAPH_FILE}")
    st.stop()

with open(GRAPH_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Build NetworkX graph
G = nx.DiGraph()
for node_name, props in data.get("nodes", {}).items():
    G.add_node(node_name, **props)

for edge in data.get("edges", []):
    src = edge.get("source")
    tgt = edge.get("target")
    rel = edge.get("type", "related_to")
    if src and tgt:
        G.add_edge(src, tgt, type=rel)

# ==============================================
# Sidebar Options
# ==============================================
st.sidebar.header("⚙️ Options")

algo = st.sidebar.selectbox(
    "Clustering Algorithm",
    [
        "Louvain Modularity (recommended)" if _LOUVAIN_AVAILABLE else "Louvain (missing)",
        "Greedy Modularity",
        "Label Propagation",
        "Girvan-Newman (edge betweenness)"
    ]
)

max_clusters_to_show = st.sidebar.slider("How many clusters to display:", 1, 40, 12)
gn_levels = st.sidebar.slider("Girvan–Newman Levels", 1, 4, 1)
show_visual = st.sidebar.checkbox("Show PyVis Visualization", True)
compute_centrality = st.sidebar.checkbox("Compute Centrality Scores", True)

# ==============================================
# Cached Helper Functions (Streamlit-Safe)
# ==============================================

@st.cache_data(ttl=3600)
def run_louvain(_graph):
    if not _LOUVAIN_AVAILABLE:
        raise RuntimeError("python-louvain is not installed.")
    partition = community_louvain.best_partition(_graph.to_undirected())

    clusters = {}
    for node, com in partition.items():
        clusters.setdefault(com, []).append(node)

    # sort clusters
    return {cid: sorted(members) for cid, members in clusters.items()}


@st.cache_data(ttl=3600)
def run_greedy(_graph):
    und = _graph.to_undirected()
    comms = list(nx.algorithms.community.greedy_modularity_communities(und))
    return {i: sorted(list(c)) for i, c in enumerate(comms)}


@st.cache_data(ttl=3600)
def run_label_prop(_graph):
    und = _graph.to_undirected()
    comms = list(nx.algorithms.community.label_propagation_communities(und))
    return {i: sorted(list(c)) for i, c in enumerate(comms)}


@st.cache_data(ttl=3600)
def run_girvan_newman(_graph, _levels=1):
    und = _graph.to_undirected()
    comp = nx.algorithms.community.girvan_newman(und)
    limited = list(itertools.islice(comp, _levels))
    if not limited:
        return {}

    partition = limited[-1]
    return {i: sorted(list(c)) for i, c in enumerate(partition)}


def summarize_clusters(clusters, G, top_k=6):
    rows = []
    deg = dict(G.degree())

    try:
        pr = nx.pagerank(G.to_undirected())
    except Exception:
        pr = {n: 0 for n in G.nodes()}

    for cid, members in sorted(clusters.items(), key=lambda x: -len(x[1]))[:max_clusters_to_show]:
        ranked = sorted(members, key=lambda n: (-deg.get(n, 0), -pr.get(n, 0)))
        rows.append({
            "cluster_id": cid,
            "size": len(members),
            "top_members": "; ".join(ranked[:top_k])
        })

    return pd.DataFrame(rows)


def clusters_to_json(clusters, G):
    deg = dict(G.degree())
    exported = []
    for cid, members in clusters.items():
        exported.append({
            "cluster_id": cid,
            "size": len(members),
            "members": members,
            "top_members": sorted(members, key=lambda n: -deg.get(n, 0))[:10]
        })
    return json.dumps(exported, indent=2, ensure_ascii=False)

# ==============================================
# Run Selected Clustering Algorithm
# ==============================================
with st.spinner(f"Running {algo} clustering..."):
    try:
        if algo.startswith("Louvain"):
            clusters = run_louvain(G)
        elif algo == "Greedy Modularity":
            clusters = run_greedy(G)
        elif algo == "Label Propagation":
            clusters = run_label_prop(G)
        elif algo.startswith("Girvan-Newman"):
            clusters = run_girvan_newman(G, _levels=gn_levels)
        else:
            st.error("Unknown algorithm")
            st.stop()
    except Exception as e:
        st.error(f"Error running clustering algorithm: {e}")
        st.stop()

# ==============================================
# Display Cluster Summary
# ==============================================
st.subheader("🔎 Chapters (Clusters) Discovered")

num_clusters = len(clusters)
st.markdown(f"**Number of clusters:** `{num_clusters}`")

summary_df = summarize_clusters(clusters, G)
st.dataframe(summary_df, use_container_width=True)

# JSON download
st.download_button(
    "⬇️ Download Clusters (JSON)",
    data=clusters_to_json(clusters, G),
    file_name=f"clusters_{algo.replace(' ', '_')}.json",
    mime="application/json"
)

# ==============================================
# Detailed Per-Cluster View
# ==============================================
st.markdown("---")
st.subheader("📚 Detailed Cluster Inspection")

view_n = st.number_input(
    "Show details for top N clusters:",
    min_value=1, max_value=min(40, num_clusters), value=min(6, num_clusters)
)

deg = dict(G.degree())
try:
    pr = nx.pagerank(G.to_undirected())
except:
    pr = {}

for cid, members in sorted(clusters.items(), key=lambda x: -len(x[1]))[:view_n]:
    with st.expander(f"Cluster {cid} — size {len(members)}"):
        rows = []
        for n in members:
            props = G.nodes[n]
            rows.append({
                "node": n,
                "degree": deg.get(n, 0),
                "pagerank": round(pr.get(n, 0), 6),
                "domain": props.get("domain", "")
            })
        df = pd.DataFrame(rows).sort_values(["degree", "pagerank"], ascending=[False, False])
        st.dataframe(df, use_container_width=True)

# ==============================================
# Global Centralities
# ==============================================
st.markdown("---")
st.subheader("🏆 Global Centrality Rankings")

if compute_centrality:
    with st.spinner("Computing centralities..."):
        deg_sorted = sorted(deg.items(), key=lambda x: -x[1])[:20]

        try:
            pr_sorted = sorted(pr.items(), key=lambda x: -x[1])[:20]
        except:
            pr_sorted = []

        try:
            bc = nx.betweenness_centrality(G.to_undirected())
            bc_sorted = sorted(bc.items(), key=lambda x: -x[1])[:20]
        except:
            bc_sorted = []

    col1, col2, col3 = st.columns(3)
    col1.markdown("### 🔹 Degree Centrality")
    col1.dataframe(pd.DataFrame(deg_sorted, columns=["node", "degree"]).set_index("node"))

    col2.markdown("### 🔹 PageRank")
    if pr_sorted:
        col2.dataframe(pd.DataFrame(pr_sorted, columns=["node", "pagerank"]).set_index("node"))
    else:
        col2.info("PageRank unavailable.")

    col3.markdown("### 🔹 Betweenness Centrality")
    if bc_sorted:
        col3.dataframe(pd.DataFrame(bc_sorted, columns=["node", "betweenness"]).set_index("node"))
    else:
        col3.info("Betweenness unavailable or too expensive.")

# ==============================================
# Visualization
# ==============================================
if show_visual:
    st.markdown("---")
    st.subheader("🌐 Cluster Visualization")

    try:
        from pyvis.network import Network as PyVisNetwork

        net = PyVisNetwork(height="700px", width="100%", bgcolor="#0e1117", font_color="white")
        net.barnes_hut()

        # Palette
        palette = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
        ]

        # node -> cluster mapping
        node_map = {}
        for cid, members in clusters.items():
            for m in members:
                node_map[m] = cid

        # Add nodes
        for n in G.nodes():
            cid = node_map.get(n, -1)
            color = palette[cid % len(palette)] if cid >= 0 else "#cccccc"
            title = G.nodes[n].get("definition", "") or ""
            net.add_node(n, label=n, title=title, color=color)

        # Add edges
        for u, v, d in G.edges(data=True):
            net.add_edge(u, v, title=d.get("type", ""), arrows="to")

        # Render
        tmp = Path("tmp_cluster_view.html")
        net.save_graph(str(tmp))
        st.components.v1.html(tmp.read_text(), height=720)
        tmp.unlink(missing_ok=True)

    except Exception as e:
        st.error(f"Visualization error: {e}")

# ==============================================
# Notes
# ==============================================
st.markdown("---")
st.info("""
### How to interpret this page:
- **Clusters = Chapters**  
- Louvain → Best for topic structure  
- Greedy → Hierarchical clusters  
- Label Propagation → Broad fuzzy groups  
- Girvan–Newman → Sharp conceptual splits  
- Centrality shows the *core curriculum topics*  
- Visualization reveals how chapters connect  
""")
