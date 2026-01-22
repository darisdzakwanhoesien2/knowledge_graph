def filter_nodes(G, query="", subject=None):
    nodes = []

    for n, props in G.nodes(data=True):
        if query.lower() not in n.lower():
            continue

        subjects = props.get("metadata", {}).get("subjects", [])
        if subject and subject not in subjects:
            continue

        nodes.append(n)

    return nodes
