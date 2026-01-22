import streamlit as st
import json
from pathlib import Path

# -------------------------------
# CONFIGURATION
# -------------------------------
st.set_page_config(page_title="🧠 Flashcards", layout="wide")
st.title("🧠 Interactive Flashcards")

BASE_DIR = Path(__file__).resolve().parents[1]
FLASHCARDS_FILE = BASE_DIR / "flashcards.json"

# -------------------------------
# LOAD FLASHCARDS
# -------------------------------
def load_flashcards():
    if not FLASHCARDS_FILE.exists():
        st.error(f"❌ Flashcards file not found at {FLASHCARDS_FILE}")
        st.stop()
    with open(FLASHCARDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

flashcards = load_flashcards()

# -------------------------------
# DOMAIN FILTERING
# -------------------------------
st.markdown("### 🔍 Filter Flashcards by Domain")

def extract_domain(card):
    """
    Extracts domain from the 'front' text.
    Expected format: "🧩 Something\n📘 Domain: Data Quality"
    """
    front = card.get("front", "")
    if "Domain:" in front:
        return front.split("Domain:")[1].strip()
    return "Unknown"

# Unique domains
domains = sorted(list({extract_domain(c) for c in flashcards}))

# Selector
selected_domains = st.multiselect(
    "Choose one or more domains:",
    options=domains,
    default=domains,  # Show all by default
)

# Filtered list
filtered_cards = [
    c for c in flashcards
    if extract_domain(c) in selected_domains
]

st.markdown(f"### 📚 Showing {len(filtered_cards)} flashcards")

# -------------------------------
# FLASHCARD DISPLAY
# -------------------------------
col_count = st.slider("Number of cards per row:", 1, 4, 2)
cols = st.columns(col_count)

# Flip-state management
if "flipped" not in st.session_state or len(st.session_state.flipped) != len(filtered_cards):
    st.session_state.flipped = [False] * len(filtered_cards)

# Display cards
for idx, card in enumerate(filtered_cards):
    col = cols[idx % col_count]
    with col:
        st.markdown("---")

        # FRONT or BACK
        if st.session_state.flipped[idx]:
            # Back side
            st.markdown(
                f"""
                <div style='background-color:#f0f2f6; padding:20px; border-radius:15px; min-height:300px;'>
                    <h4>🪄 Back</h4>
                    <p style='font-size:0.95em;'>{card['back']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Front side
            st.markdown(
                f"""
                <div style='background-color:#e8f0fe; padding:20px; border-radius:15px; min-height:300px;'>
                    <h4>📘 Front</h4>
                    <p style='font-size:1.05em; font-weight:bold;'>{card['front']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Flip button
        if st.button("🔁 Flip", key=f"flip_{idx}"):
            st.session_state.flipped[idx] = not st.session_state.flipped[idx]
            st.rerun()

st.markdown("---")
st.info("💡 Tip: Use the filter dropdown to focus on specific domains.")
