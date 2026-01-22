from pyvis.network import Network


def draw_graph(G):
    net = Network(height="700px", width="100%", directed=True)
    net.barnes_hut()

    for n, props in G.nodes(data=True):
        title = f"{n}<br>{props.get('definition','')}"
        net.add_node(n, label=n, title=title)

    for u, v, d in G.edges(data=True):
        net.add_edge(u, v, label=d.get("type", ""))

    return net
