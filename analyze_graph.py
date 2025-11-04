import json
import networkx as nx
import matplotlib.pyplot as plt

with open("merged_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

G = nx.DiGraph()
for node in data["nodes"]:
    G.add_node(node)
for edge in data["edges"]:
    G.add_edge(edge["source"], edge["target"], type=edge["type"])

# Metrics
print("Nodes:", G.number_of_nodes())
print("Edges:", G.number_of_edges())
print("Top degree nodes:", sorted(G.degree, key=lambda x: x[1], reverse=True)[:5])

# Simple plot
plt.figure(figsize=(10, 8))
nx.draw(
    G,
    with_labels=True,
    node_size=500,
    font_size=8,
    node_color="skyblue",
    edge_color="gray",
    arrows=True,
)
plt.show()
