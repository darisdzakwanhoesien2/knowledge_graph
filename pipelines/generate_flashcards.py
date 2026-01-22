import json
from pathlib import Path

# ======================================================
# PATH CONFIG
# ======================================================

BASE_DIR = Path(__file__).resolve().parents[1]

GRAPH_FILE = BASE_DIR / "data" / "graphs" / "merged_graph.json"
FLASHCARD_FILE = BASE_DIR / "data" / "flashcards" / "flashcards.json"

FLASHCARD_FILE.parent.mkdir(parents=True, exist_ok=True)


# ======================================================
# GENERATION
# ======================================================

def generate_flashcards():
    if not GRAPH_FILE.exists():
        raise FileNotFoundError(f"Graph not found: {GRAPH_FILE}")

    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        graph = json.load(f)

    flashcards = []

    for entity, props in graph["nodes"].items():

        # Skip empty placeholder nodes
        if not any([
            props.get("definition"),
            props.get("description"),
            props.get("properties")
        ]):
            continue

        meta = props.get("metadata", {})

        subjects = meta.get("subjects", [])
        sources = meta.get("source_files", [])

        domain = props.get("domain", "General")
        definition = props.get("definition", "No definition available.")
        description = props.get("description", "")
        properties = props.get("properties", {})

        facts = []
        for k, v in properties.items():
            if isinstance(v, list):
                v = ", ".join(map(str, v))
            facts.append(f"**{k}:** {v}")

        flashcards.append({
            "entity": entity,
            "domain": domain,
            "subjects": subjects,
            "sources": sources,
            "front": f"🧩 {entity}\n📘 Domain: {domain}\n📚 Subjects: {', '.join(subjects)}",
            "back": (
                f"**Definition:** {definition}\n\n"
                f"**Description:** {description}\n\n"
                + "\n".join(facts)
            ).strip()
        })

    with open(FLASHCARD_FILE, "w", encoding="utf-8") as f:
        json.dump(flashcards, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {len(flashcards)} flashcards")
    print(f"💾 Saved to {FLASHCARD_FILE}")


# ======================================================
# MAIN
# ======================================================

if __name__ == "__main__":
    generate_flashcards()
