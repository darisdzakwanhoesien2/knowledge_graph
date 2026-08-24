import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from core import packages as P
from core.pdf_extract import PdfExtractionError, extract_pdf_text
from core.registry import load_registry

BASE_DIR = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="📄 PDF Drafts", layout="wide")
st.title("📄 PDF → Draft Questions")
st.caption("Upload a PDF to extract text and scaffold draft questions. "
           "Generated content stays in **draft** status until a curator reviews it (PRD: human-governed).")


def chunk_pages(text: str):
    """Split extracted text into page chunks keyed by their page marker."""
    chunks = []
    parts = text.split("--- page ")
    for part in parts[1:]:
        header, _, body = part.partition("---")
        body = body.strip()
        if body:
            chunks.append({"page": header.strip(), "text": body})
    return chunks


def extract_uploaded(uploaded):
    try:
        key_name = getattr(uploaded, "name", None)
        if "pdf_extract" not in st.session_state or \
                st.session_state.get("pdf_name") != key_name:
            st.session_state["pdf_extract"] = extract_pdf_text(uploaded)
            st.session_state["pdf_name"] = key_name
        return st.session_state["pdf_extract"]
    except (PdfExtractionError, TypeError, ValueError) as e:
        st.error(f"PDF extraction failed: {e}")
        return None


def pick_target(existing):
    subjects = sorted(load_registry().get("subjects", {}).keys())
    subject = st.selectbox("Subject", subjects) if subjects else ""
    if not subjects:
        st.warning("No subjects registered yet. Run `python3 pipelines/build_registry.py`.")
        return None

    pkg_options = ["➕ New package from this PDF…"] + \
                  [e["package_id"] for e in existing if e["subject"] == subject]
    choice = st.selectbox("Target package", pkg_options)
    return {"subject": subject, "choice": choice}


def generate_scaffolds(target, result, uploaded, max_chars):
    subject = target["subject"]
    if target["choice"].startswith("➕"):
        title = st.session_state.get("new_pkg_title") or Path(uploaded.name).stem
        pkg = P.new_package(
            subject=subject,
            title=title,
            description=f"Scaffolded from {uploaded.name} "
                        f"(sha256 {result['content_hash'][:12]}). Drafts pending curator review.",
            source={"filename": uploaded.name,
                    "content_hash": result["content_hash"],
                    "media_type": "application/pdf"},
        )
    else:
        current = P.load_package(subject, target["choice"])
        if current is None:
            st.error("Could not load target package.")
            return
        if current.get("status") == "published":
            current = P.start_next_draft(subject, target["choice"])
            st.warning(f"Package was published — editing as draft v{current['version']}.")
        pkg = current

    added_mcq = added_essay = 0
    for chunk in chunk_pages(result["text"]):
        lines = [l for l in chunk["text"].splitlines() if l.strip()]
        first_line = lines[0][:140] if lines else ""
        P.add_mcq(
            pkg,
            question=f"[DRAFT p.{chunk['page']}] Write a multiple-choice question about: “{first_line}”",
            options={"A": "[Replace with option A]", "B": "[Replace with option B]"},
            correct_option="A",
            difficulty="medium",
            learning_objective="[Review the source text and set a learning objective]",
            slide_refs=[f"page {chunk['page']}"],
        )
        added_mcq += 1
        excerpt = chunk["text"][:max_chars]
        P.add_essay(
            pkg,
            prompt=f"[DRAFT p.{chunk['page']}] Explain in your own words: “{first_line}”\n\n"
                   f"Source excerpt:\n> {excerpt}",
            expected_keywords=[],
            criteria=[],
            total_points=0,
            grading_notes="Scaffold — add keywords/criteria after reviewing the source text.",
            slide_refs=[f"page {chunk['page']}"],
        )
        added_essay += 1

    P.save_package(pkg)
    st.session_state.pop("pdf_extract", None)
    st.success(f"Added {added_mcq} MCQ scaffolds and {added_essay} essay scaffolds to "
               f"`{pkg['package_key']}` (status: {pkg['status']}, v{pkg['version']}). "
               f"Review, fill answers/rubrics, then publish in ✍️ Author Packages.")
    st.page_link("pages/7_Author_Packages.py", label="Open Author Packages", icon="✍️")


def main():
    uploaded = st.file_uploader("Question-bank or lecture PDF", type=["pdf"])
    if uploaded is None or not getattr(uploaded, "name", None):
        st.info("No PDF uploaded yet.")
        return

    extracted = extract_uploaded(uploaded)
    if extracted is None:
        return
    result = extracted
    chunks = chunk_pages(result["text"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Pages", result["pages"])
    m2.metric("Characters", len(result["text"]))
    m3.metric("Content hash", result["content_hash"][:12])
    st.caption(f"`{uploaded.name}` · sha256 `{result['content_hash']}`")

    if not chunks:
        st.warning("No extractable text found (scanned images need OCR, which is out of scope).")
        with st.expander("Raw extraction output"):
            st.text(result["text"][:2000])
        return

    st.divider()
    st.subheader("1. Choose target subject and package")
    existing = P.list_packages()
    target = pick_target(existing)
    if target is None:
        return
    if target["choice"].startswith("➕"):
        default_title = Path(uploaded.name).stem.replace("-", "_").replace(" ", "_")
        st.text_input("Package title", key="new_pkg_title", value=default_title)

    st.subheader("2. Generate scaffolded drafts")
    max_chars = st.slider("Excerpt length per scaffolded essay", 200, 1200, 500, step=100)
    if st.button("Generate scaffolded drafts"):
        generate_scaffolds(target, result, uploaded, max_chars)
        return

    with st.expander("Extracted text preview"):
        st.text(result["text"][:4000])


main()
