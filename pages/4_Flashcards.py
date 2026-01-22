import streamlit as st
import json
from pathlib import Path

# =====================================================
# PATH RESOLUTION
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]

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

st.set_page_config(page_title="🃏 Flashcards", layout="wide")
st.title("🃏 Flashcards Explorer")

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

st.caption(f"Loaded **{len(cards)}** flashcards from `{FLASHCARDS_PATH.name}`")

# =====================================================
# UI CONTROLS
# =====================================================

search_query = st.text_input("🔍 Search term (entity / text):")

cols = st.columns(3)
with cols[0]:
    sort_key = st.selectbox("Sort by", ["entity", "domain"])
with cols[1]:
    ascending = st.checkbox("Ascending", True)
with cols[2]:
    page_size = st.selectbox("Cards per page", [10, 25, 50, 100], index=1)

# =====================================================
# FILTER + SORT
# =====================================================

def match_query(card):
    if not search_query:
        return True
    q = search_query.lower()
    return (
        q in card.get("entity", "").lower()
        or q in card.get("front", "").lower()
        or q in card.get("back", "").lower()
    )


filtered = [c for c in cards if match_query(c)]

filtered.sort(
    key=lambda c: c.get(sort_key, "").lower(),
    reverse=not ascending
)

# =====================================================
# PAGINATION
# =====================================================

total = len(filtered)
if total == 0:
    st.warning("No flashcards match the filter.")
    st.stop()

pages = max(1, (total + page_size - 1) // page_size)
page = st.number_input(
    "Page",
    min_value=1,
    max_value=pages,
    value=1
)

start = (page - 1) * page_size
end = start + page_size
visible = filtered[start:end]

st.markdown(f"Showing **{start+1}–{min(end,total)}** of **{total}** cards")

# =====================================================
# DISPLAY
# =====================================================

for c in visible:
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
st.caption("Tip: Use search + pagination for large knowledge bases.")
