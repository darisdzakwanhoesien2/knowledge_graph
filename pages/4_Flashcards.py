import streamlit as st
import json
from pathlib import Path

# -------------------------------
# CONFIGURATION
# -------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
FLASHCARDS_FILE = BASE_DIR / "flashcards.json"

st.set_page_config(page_title="🧠 Flashcards", layout="wide")
st.title("🧠 Interactive Flashcards")

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
# FLASHCARD DISPLAY
# -------------------------------
st.markdown("### 📚 Browse and Study Flashcards")

if not flashcards:
    st.warning("⚠️ No flashcards found.")
    st.stop()

# Layout options
col_count = st.slider("Number of cards per row:", 1, 4, 2)
cols = st.columns(col_count)

# State management for flipped cards
if "flipped" not in st.session_state:
    st.session_state.flipped = [False] * len(flashcards)

# Show flashcards
for idx, card in enumerate(flashcards):
    col = cols[idx % col_count]
    with col:
        st.markdown("---")
        if st.session_state.flipped[idx]:
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
            st.markdown(
                f"""
                <div style='background-color:#e8f0fe; padding:20px; border-radius:15px; min-height:300px;'>
                    <h4>📘 Front</h4>
                    <p style='font-size:1.05em; font-weight:bold;'>{card['front']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Toggle button
        if st.button("🔁 Flip", key=f"flip_{idx}"):
            st.session_state.flipped[idx] = not st.session_state.flipped[idx]
            st.rerun()  # ✅ updated from st.experimental_rerun()

st.markdown("---")
st.info("💡 Tip: Adjust the slider above to view multiple flashcards side-by-side.")
