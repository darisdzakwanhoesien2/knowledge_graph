import json
from pathlib import Path

GRAPH_FILE = "merged_graph.json"
FLASHCARDS_FILE = "flashcards.json"

def generate_flashcards(graph_path, output_path):
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    flashcards = []

    for entity, props in graph["nodes"].items():
        # Skip placeholder nodes
        if props.get("definition", "N/A") == "N/A" and props.get("description", "N/A") == "N/A":
            continue

        domain = props.get("domain", "General")
        definition = props.get("definition", "No definition available.")
        description = props.get("description", "")
        properties = props.get("properties", {})

        # Combine key facts
        facts = []
        for k, v in properties.items():
            value = ", ".join(v) if isinstance(v, list) else v
            facts.append(f"**{k}:** {value}")

        flashcard = {
            "front": f"🧩 {entity}\n📘 Domain: {domain}",
            "back": f"**Definition:** {definition}\n\n**Description:** {description}\n\n" + "\n".join(facts)
        }

        flashcards.append(flashcard)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(flashcards, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {len(flashcards)} flashcards → {output_path}")

if __name__ == "__main__":
    if not Path(GRAPH_FILE).exists():
        print("❌ merged_graph.json not found. Please run build_graph.py first.")
    else:
        generate_flashcards(GRAPH_FILE, FLASHCARDS_FILE)
