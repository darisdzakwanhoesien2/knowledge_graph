import streamlit as st
import json
from pathlib import Path

# =====================================================
# PATH RESOLUTION
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PRIMARY_PATH = BASE_DIR / "data" / "flashcards" / "flashcards.json"
FALLBACK_PATH = BASE_DIR / "flashcards.json"


def resolve_flashcards_path():
    if PRIMARY_PATH.exists():
        return PRIMARY_PATH
    if FALLBACK_PATH.exists():
        return FALLBACK_PATH
    return None


FLASHCARDS_PATH = resolve_flashcards_path()

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(page_title="🗂 Flashcards by Subject", layout="wide")
st.title("🗂 Flashcards — Subject Explorer")

# =====================================================
# LOAD DATA
# =====================================================

if FLASHCARDS_PATH is None:
    st.error(
        "❌ Flashcards file not found.\n\n"
        "Expected one of:\n"
        f"- {PRIMARY_PATH}\n"
        f"- {FALLBACK_PATH}\n\n"
        "Run:\n"
        "`python pipelines/generate_flashcards.py`"
    )
    st.stop()

try:
    cards = json.loads(FLASHCARDS_PATH.read_text(encoding="utf-8"))
except Exception as e:
    st.error(f"❌ Failed to load flashcards:\n{e}")
    st.stop()

if not cards:
    st.warning("⚠️ Flashcards file is empty.")
    st.stop()

st.caption(f"Loaded **{len(cards)}** flashcards")

# =====================================================
# SUBJECT EXTRACTION
# =====================================================

all_subjects = sorted({
    s.strip()
    for card in cards
    for s in card.get("subjects", [])
    if s.strip()
})

if not all_subjects:
    st.warning("No subjects detected in flashcards metadata.")
    st.stop()

# =====================================================
# UI CONTROLS
# =====================================================

selected_subjects = st.multiselect(
    "📚 Select subject(s):",
    options=all_subjects,
    default=all_subjects[:1]  # avoid massive initial rendering
)

search_query = st.text_input("🔍 Optional search inside selected subjects:")

cols = st.columns(2)
with cols[0]:
    sort_key = st.selectbox("Sort by", ["entity", "domain"])
with cols[1]:
    ascending = st.checkbox("Ascending", True)

# =====================================================
# FILTER
# =====================================================

def subject_match(card):
    return any(s in selected_subjects for s in card.get("subjects", []))


def text_match(card):
    if not search_query:
        return True
    q = search_query.lower()
    return (
        q in card.get("entity", "").lower()
        or q in card.get("front", "").lower()
        or q in card.get("back", "").lower()
    )


filtered = [
    c for c in cards
    if subject_match(c) and text_match(c)
]

filtered.sort(
    key=lambda c: c.get(sort_key, "").lower(),
    reverse=not ascending
)

# =====================================================
# DISPLAY
# =====================================================

if not filtered:
    st.info("No flashcards match the current filters.")
    st.stop()

st.markdown(f"### Showing {len(filtered)} flashcards")

for c in filtered:
    title = c.get("entity", "Unnamed Concept")
    subjects = ", ".join(c.get("subjects", [])) or "—"
    domain = c.get("domain", "—")

    with st.expander(f"🧩 {title}", expanded=False):
        st.markdown(f"**Domain:** {domain}")
        st.markdown(f"**Subjects:** {subjects}")
        st.markdown("---")
        st.markdown(c.get("front", ""))
        st.markdown("---")
        st.markdown(c.get("back", ""))

st.divider()
st.caption("Tip: Select fewer subjects for faster rendering on large datasets.")
