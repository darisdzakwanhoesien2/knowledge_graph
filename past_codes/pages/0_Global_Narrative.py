# pages/4_Global_Narrative.py
import streamlit as st
import json
from pathlib import Path
import networkx as nx
import itertools
import pandas as pd
from datetime import datetime

# Try to import Louvain (python-louvain)
try:
    import community as community_louvain
    _LOUVAIN_AVAILABLE = True
except Exception:
    _LOUVAIN_AVAILABLE = False

st.set_page_config(page_title="📖 Global Narrative", layout="wide")
st.title("📖 Global Narrative — Auto-generated Chapter Overviews")

BASE_DIR = Path(__file__).resolve().parents[1]
GRAPH_FILE = BASE_DIR / "merged_graph.json"

if not GRAPH_FILE.exists():
    st.error(f"merged_graph.json not found at: {GRAPH_FILE}")
    st.stop()

with open(GRAPH_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Build directed graph
G = nx.DiGraph()
for node_name, props in data.get("nodes", {}).items():
    G.add_node(node_name, **props)
for edge in data.get("edges", []):
    s = edge.get("source")
    t = edge.get("target")
    if s and t:
        G.add_edge(s, t, type=edge.get("type", "related_to"))

if G.number_of_nodes() == 0:
    st.warning("Graph is empty.")
    st.stop()

# Sidebar options
st.sidebar.header("Options")
algo_options = []
if _LOUVAIN_AVAILABLE:
    algo_options.append("Louvain Modularity (recommended)")
algo_options += ["Greedy Modularity", "Label Propagation", "Girvan-Newman (edge betweenness)"]
algorithm = st.sidebar.selectbox("Clustering algorithm", algo_options)
max_chapters = st.sidebar.slider("Max chapters to produce/display", 1, 50, 12)
include_examples = st.sidebar.checkbox("Include short chapter examples (from definitions)", True)
compute_centrality = st.sidebar.checkbox("Compute centralities (degree & pagerank)", True)
gn_levels = st.sidebar.slider("Girvan-Newman levels (if used)", 1, 3, 1)

st.info("This page produces a narrative summary of the graph: chapter titles, descriptions, recommended learning order, and a downloadable Markdown.")

# --- helper clustering functions (streamlit-caching safe naming) ---
@st.cache_data(ttl=3600)
def _run_louvain(_graph):
    partition = community_louvain.best_partition(_graph.to_undirected())
    clusters = {}
    for n, com in partition.items():
        clusters.setdefault(com, []).append(n)
    return {k: sorted(v) for k, v in clusters.items()}

@st.cache_data(ttl=3600)
def _run_greedy(_graph):
    und = _graph.to_undirected()
    comms = list(nx.algorithms.community.greedy_modularity_communities(und))
    return {i: sorted(list(c)) for i, c in enumerate(comms)}

@st.cache_data(ttl=3600)
def _run_label_prop(_graph):
    und = _graph.to_undirected()
    comms = list(nx.algorithms.community.label_propagation_communities(und))
    return {i: sorted(list(c)) for i, c in enumerate(comms)}

@st.cache_data(ttl=3600)
def _run_girvan(_graph, _levels=1):
    und = _graph.to_undirected()
    comp = nx.algorithms.community.girvan_newman(und)
    limited = list(itertools.islice(comp, _levels))
    if not limited:
        return {}
    partition = limited[-1]
    return {i: sorted(list(c)) for i, c in enumerate(partition)}

# run selected clustering
with st.spinner("Running clustering..."):
    try:
        if algorithm.startswith("Louvain"):
            if not _LOUVAIN_AVAILABLE:
                st.error("Louvain not installed. Choose another algorithm.")
                st.stop()
            clusters = _run_louvain(G)
        elif algorithm == "Greedy Modularity":
            clusters = _run_greedy(G)
        elif algorithm == "Label Propagation":
            clusters = _run_label_prop(G)
        elif algorithm.startswith("Girvan-Newman"):
            clusters = _run_girvan(G, _levels=gn_levels)
        else:
            st.error("Unknown algorithm selected")
            st.stop()
    except Exception as e:
        st.error(f"Clustering error: {e}")
        st.stop()

if not clusters:
    st.warning("No clusters found.")
    st.stop()

# compute centralities
pagerank = {}
deg = dict(G.degree())
if compute_centrality:
    try:
        pagerank = nx.pagerank(G.to_undirected())
    except Exception:
        pagerank = {n: 0.0 for n in G.nodes()}

# prepare cluster summaries
def cluster_score_and_title(members):
    # score by average degree + pagerank
    avg_deg = sum(deg.get(m, 0) for m in members) / (len(members) or 1)
    avg_pr = sum(pagerank.get(m, 0.0) for m in members) / (len(members) or 1)
    # pick title candidate: highest degree then pagerank
    sorted_members = sorted(members, key=lambda n: (-deg.get(n, 0), -pagerank.get(n, 0)))
    title = sorted_members[0] if sorted_members else "Untitled"
    return (avg_deg + avg_pr), title, sorted_members

cluster_infos = []
for cid, members in clusters.items():
    score, title, sorted_members = cluster_score_and_title(members)
    cluster_infos.append({
        "cluster_id": cid,
        "members": members,
        "size": len(members),
        "score": score,
        "title": title,
        "top_members": sorted_members[:8]
    })

# sort clusters by size (or score)
cluster_infos_sorted = sorted(cluster_infos, key=lambda x: (-x["size"], -x["score"]))
cluster_infos_sorted = cluster_infos_sorted[:max_chapters]

# build inter-cluster edges (counts) to estimate flow for learning order
cluster_map = {}
for info in cluster_infos_sorted:
    for m in info["members"]:
        cluster_map[m] = info["cluster_id"]

inter_cluster_counts = {}
for u, v in G.edges():
    cu = cluster_map.get(u)
    cv = cluster_map.get(v)
    if cu is not None and cv is not None and cu != cv:
        inter_cluster_counts[(cu, cv)] = inter_cluster_counts.get((cu, cv), 0) + 1

# estimate learning order by cluster "importance" and outgoing edges
def estimate_learning_order(cluster_infos_sorted):
    # simple heuristic: clusters with many incoming edges are prerequisites
    incoming = {info["cluster_id"]: 0 for info in cluster_infos_sorted}
    outgoing = {info["cluster_id"]: 0 for info in cluster_infos_sorted}
    for (a, b), cnt in inter_cluster_counts.items():
        if a in incoming:
            outgoing[a] += cnt
        if b in incoming:
            incoming[b] += cnt
    # compute score: high incoming -> learned earlier, high outgoing -> foundations
    order_scores = []
    for info in cluster_infos_sorted:
        cid = info["cluster_id"]
        s = outgoing.get(cid, 0) - incoming.get(cid, 0)  # positive => foundational
        order_scores.append((cid, s))
    # sort descending s (foundational first)
    ordered = [cid for cid, _ in sorted(order_scores, key=lambda x: -x[1])]
    return ordered

learning_order_cluster_ids = estimate_learning_order(cluster_infos_sorted)

# generate human-readable chapter narratives
def make_chapter_paragraph(info):
    title = info["title"]
    size = info["size"]
    top_members = info["top_members"]
    members = info["members"]
    # gather short definitions for examples
    examples = []
    if include_examples:
        for m in top_members[:3]:
            d = G.nodes.get(m, {}).get("definition") or G.nodes.get(m, {}).get("description") or ""
            if d:
                # just first sentence-ish
                examples.append(f"**{m}** — {d.split('. ')[0].strip()}.")
    # compose paragraph
    para_lines = []
    para_lines.append(f"### Chapter {info['cluster_id'] + 1}: {title}")
    para_lines.append(f"- **Summary:** This chapter groups **{size}** closely related concepts centered on *{title}*.")
    para_lines.append(f"- **Core ideas:** {', '.join(top_members[:6])}.")
    if examples:
        para_lines.append(f"- **Short examples / definitions:**")
        for e in examples:
            para_lines.append(f"  - {e}")
    # identify bridging clusters (neighbors)
    neighbors = set()
    for m in members:
        for _, v in G.out_edges(m):
            cid_v = cluster_map.get(v)
            if cid_v is not None and cid_v != info["cluster_id"]:
                neighbors.add(cid_v)
    if neighbors:
        neighbor_list = ", ".join([f"Chapter {n+1}" for n in sorted(neighbors)])
        para_lines.append(f"- **Connected chapters:** {neighbor_list}.")
    return "\n".join(para_lines)

# build full narrative
narrative_lines = []
narrative_lines.append(f"# Global Knowledge Graph Narrative\n*Generated: {datetime.utcnow().isoformat()} UTC*\n")
narrative_lines.append("## Executive Summary\nThis narrative summarizes the main chapters discovered across the knowledge graph, highlights core concepts for each chapter, and suggests a recommended learning order based on inter-chapter dependencies and centrality.\n")

# top central concepts global
if compute_centrality:
    # degree/top-k
    top_by_degree = sorted(deg.items(), key=lambda x: -x[1])[:8]
    narrative_lines.append("### Core Concepts (Global)\n")
    narrative_lines.append("The most central concepts across the entire graph are: " + ", ".join([n for n, _ in top_by_degree]) + ".\n")

# chapters
narrative_lines.append("## Chapters\n")
for info in cluster_infos_sorted:
    narrative_lines.append(make_chapter_paragraph(info))
    narrative_lines.append("")  # spacer

# recommended learning order
narrative_lines.append("## Recommended Learning Order (High-level)\n")
ordered_chapters = learning_order_cluster_ids
if ordered_chapters:
    readable_order = " → ".join([f"Chapter {cid+1} ({next((i['title'] for i in cluster_infos_sorted if i['cluster_id']==cid), 'Unknown')})" for cid in ordered_chapters])
    narrative_lines.append(readable_order)
else:
    narrative_lines.append("No inter-chapter flow detected.")

# cross-chapter bridges
narrative_lines.append("\n## Cross-chapter Bridges\n")
if inter_cluster_counts:
    # show top bridges
    sorted_bridges = sorted(inter_cluster_counts.items(), key=lambda x: -x[1])[:12]
    for (a, b), cnt in sorted_bridges:
        narrative_lines.append(f"- Chapter {a+1} → Chapter {b+1} (edges: {cnt})")
else:
    narrative_lines.append("No strong bridges detected between chapters.")

# finalize narrative string
full_narrative_md = "\n".join(narrative_lines)

# UI: show narrative in page
st.header("Auto-generated Narrative")
st.markdown(full_narrative_md, unsafe_allow_html=True)

# offer per-chapter quick view table
st.markdown("---")
st.subheader("Chapter Index (quick view)")
index_rows = []
for info in cluster_infos_sorted:
    index_rows.append({
        "chapter": info["cluster_id"] + 1,
        "title": info["title"],
        "size": info["size"],
        "top_members": "; ".join(info["top_members"][:6])
    })
st.dataframe(pd.DataFrame(index_rows), use_container_width=True)

# download buttons
st.markdown("---")
st.subheader("Download Narrative / Data")
st.download_button("⬇️ Download Narrative (Markdown)", data=full_narrative_md, file_name="global_narrative.md", mime="text/markdown")
clusters_json = json.dumps({info["cluster_id"]: info for info in cluster_infos_sorted}, indent=2, ensure_ascii=False)
st.download_button("⬇️ Download Cluster Metadata (JSON)", data=clusters_json, file_name="clusters_metadata.json", mime="application/json")

st.info("Tip: Review clusters in the Node Cleanup page to fix ghost/incomplete nodes, then re-run clustering and re-generate the narrative for cleaner chapter descriptions.")
