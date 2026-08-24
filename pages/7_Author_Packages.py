import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from core import packages as P
from core.mcq_parser import parse_mcq_block
from core.registry import load_registry

BASE_DIR = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="✍️ Author Packages", layout="wide")
st.title("✍️ Author Question Packages")
st.caption("Create packages, add MCQs (manual or pasted) and essays with rubrics, then validate and publish.")

DIFFICULTIES = ["easy", "medium", "hard"]


def graph_node_names():
    from components.graph_loader import load_graph

    try:
        _, raw = load_graph()
        return sorted(raw.get("nodes", {}).keys())
    except FileNotFoundError:
        return []


NODE_NAMES = graph_node_names()


def get_working_package():
    key = st.session_state.get("author_current")
    if not key:
        return None
    subject, package_id = key.split("/", 1)
    return P.load_package(subject, package_id)


def save_and_rerun(pkg):
    P.save_package(pkg)
    st.rerun()


# =====================================================
# PACKAGE SELECTION / CREATION
# =====================================================

existing = P.list_packages()
options = ["➕ Create new package…"] + [f"{e['subject']}/{e['package_id']}" for e in existing]
choice = st.selectbox("Package", options,
                      index=options.index(st.session_state["author_current"])
                      if "author_current" in st.session_state else 0)

if choice.startswith("➕"):
    subjects = sorted(load_registry().get("subjects", {}).keys())
    if not subjects:
        st.warning("No subjects registered yet. Run `python3 pipelines/build_registry.py`.")
    with st.form("new_package_form", clear_on_submit=False):
        subject = st.selectbox("Subject", subjects)
        title = st.text_input("Title")
        level = st.selectbox("Level", ["", "Undergraduate", "Graduate", "Professional"])
        description = st.text_area("Description", height=80)
        created = st.form_submit_button("Create draft package")
    if created:
        if not title.strip():
            st.error("Title is required.")
        else:
            pkg = P.new_package(subject=subject, title=title.strip(),
                                level=level, description=description.strip())
            P.save_package(pkg)
            st.session_state["author_current"] = f"{subject}/{pkg['package_id']}"
            st.success(f"Created {pkg['package_key']} (draft v1)")
            st.rerun()
else:
    st.session_state["author_current"] = choice
    subject, package_id = choice.split("/", 1)
    pkg = P.load_package(subject, package_id)
    if pkg is None:
        st.error(f"Could not load {choice}")
    else:
        render_editor(subject, package_id, pkg)

def render_editor(subject, package_id, pkg):
    published_versions = sorted((P.package_dir(subject, package_id) / P.VERSIONS_DIR).glob("v*.json")) \
        if (P.package_dir(subject, package_id) / P.VERSIONS_DIR).exists() else []

    header_cols = st.columns([3, 2, 2])
    with header_cols[0]:
        st.subheader(f"{pkg.get('title', package_id)}")
        st.caption(f"`{pkg.get('package_key')}` · {len(pkg.get('mcqs', []))} MCQs · "
                   f"{len(pkg.get('essay', []))} essays")
    with header_cols[1]:
        status = pkg.get("status")
        st.markdown(f"**Status:** {'🟢' if status == 'published' else '🟡'} `{status}` — v{pkg.get('version')}")
        st.caption(f"{len(published_versions)} published version(s)")
    with header_cols[2]:
        is_published = status == "published"
        if is_published:
            st.info("Published versions are immutable. Start a next draft to edit content.",
                    icon="🔒")

    if is_published:
        if st.button("Start next draft (v%d)" % (int(pkg["version"]) + 1)):
            P.start_next_draft(subject, package_id)
            st.rerun()
    elif st.button("Validate & publish this version"):
        issues = P.validate_package(pkg)
        errors = [i for i in issues if i["severity"] == "error"]
        if errors:
            st.error("Fix these errors before publishing:\n" +
                     "\n".join(f"- {i['location'].split(' ', 1)[-1]}: {i['message']}" for i in errors))
        else:
            snap = P.publish_package(subject, package_id)
            st.success(f"Published {snap['package_key']} as immutable v{snap['version']}")
            st.rerun()

    st.divider()

    # =====================================================
    # VALIDATION PANEL (always visible)
    # =====================================================

    issues = P.validate_package(pkg)
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Errors", len(errors))
    c2.metric("Warnings", len(warnings))
    c3.metric("Questions", len(pkg.get("mcqs", [])) + len(pkg.get("essay", [])))
    for issue in issues:
        loc = issue["location"].split(" ", 1)[-1] if issue["location"].startswith(subject) else issue["location"]
        st.markdown(f"- {': '.join([loc, issue['message']])}")

    with st.expander("📦 Package metadata"):
        with st.form("meta_form"):
            meta_c1, meta_c2 = st.columns(2)
            new_title = meta_c1.text_input("Title", value=pkg.get("title", ""))
            new_level = meta_c2.selectbox("Level", ["", "Undergraduate", "Graduate", "Professional"],
                                          index=["", "Undergraduate", "Graduate", "Professional"]
                                          .index(pkg.get("level", "")))
            new_desc = st.text_area("Description", value=pkg.get("description", ""), height=70)
            src_name = st.text_input("Source document (filename)",
                                     value=(pkg.get("source") or {}).get("filename", ""))
            src_hash = st.text_input("Source content hash",
                                     value=(pkg.get("source") or {}).get("content_hash", ""))
            if st.form_submit_button("Save metadata"):
                pkg["title"] = new_title.strip() or pkg["title"]
                pkg["level"] = new_level
                pkg["description"] = new_desc.strip()
                pkg["source"] = {"filename": src_name.strip(),
                                 "content_hash": src_hash.strip()}
                save_and_rerun(pkg)

    # =====================================================
    # MCQ SECTION
    # =====================================================

    st.divider()
    st.header("📝 MCQs")

    tab_manual, tab_paste = st.tabs(["Add manually", "Parse pasted blocks"])

    with tab_manual:
        with st.form("add_mcq_form", clear_on_submit=True):
            q_text = st.text_area("Question", height=90)
            opt_cols = st.columns(5)
            opt_inputs = {}
            for i, letter in enumerate(P.MCQ_OPTION_KEYS):
                with opt_cols[i]:
                    opt_inputs[letter] = st.text_input(f"Option {letter}", key=f"opt_{letter}")
            f_c1, f_c2, f_c3 = st.columns(3)
            correct = f_c1.selectbox("Correct option", P.MCQ_OPTION_KEYS)
            difficulty = f_c2.selectbox("Difficulty", DIFFICULTIES, index=1)
            objective = f_c3.text_input("Learning objective")
            slides = st.text_input("Slide refs (comma separated)")
            node_links = st.multiselect("Linked graph concepts", NODE_NAMES) if NODE_NAMES else []
            submitted_mcq = st.form_submit_button("Add MCQ")
        if submitted_mcq:
            opts = {k: v for k, v in opt_inputs.items() if v.strip()}
            if not q_text.strip() or len(opts) < 2 or correct not in opts:
                st.error("A question needs a prompt plus at least two filled options; the correct option must be filled.")
            else:
                slide_refs = [s.strip() for s in slides.split(",") if s.strip()]
                P.add_mcq(pkg, q_text, opts, correct, difficulty, objective,
                          slide_refs, node_links)
                save_and_rerun(pkg)

    with tab_paste:
        st.caption("One question per block. Options as `A)`–`E)` lines, then `Answer: B`. "
                   "Optional `Difficulty:` / `Objective:` / `Slides:` lines.")
        pasted = st.text_area("Paste question blocks", height=220,
                              placeholder=("1. What is X?\nA) Option one\nB) Option two\n"
                                           "Answer: A\n\n2. What is Y?\nA) ...\nB) ...\nAnswer: B"))
        if st.button("Parse blocks"):
            parsed, parse_errors = parse_mcq_block(pasted)
            st.session_state["parsed_mcqs"] = parsed
            st.session_state["parse_errors"] = parse_errors

        parse_errors = st.session_state.pop("parse_errors", [])
        for err in parse_errors:
            st.warning(err)
        parsed_now = st.session_state.get("parsed_mcqs", [])
        if parsed_now:
            st.write(f"Parsed **{len(parsed_now)}** questions:")
            for q in parsed_now:
                st.markdown(f"- **{q['question']}** → correct: `{q['correct_option']}` ({len(q['options'])} options)")
            if st.button(f"Append {len(parsed_now)} questions to package"):
                pkg.setdefault("mcqs", []).extend(parsed_now)
                st.session_state["parsed_mcqs"] = []
                save_and_rerun(pkg)

    for idx, mcq in enumerate(pkg.get("mcqs", [])):
        with st.expander(f"{idx + 1}. {mcq.get('question', '(no prompt)')[:90]}"):
            st.markdown(f"`{mcq.get('id')}` · difficulty `{mcq.get('difficulty', '—')}` · "
                        f"objective: {mcq.get('learning_objective') or '—'}")
            for letter, text in (mcq.get("options") or {}).items():
                mark = "✅" if letter == mcq.get("correct_option") else "  "
                st.markdown(f"{mark} **{letter}.** {text}")
            refs = ", ".join(mcq.get("slide_refs", [])) or "—"
            links = ", ".join(mcq.get("node_links", [])) or "—"
            st.caption(f"Slide refs: {refs} · Concept links: {links}")
            if st.button("Remove", key=f"del_mcq_{mcq.get('id')}_{idx}"):
                pkg["mcqs"].pop(idx)
                save_and_rerun(pkg)

    # =====================================================
    # ESSAY SECTION
    # =====================================================

    st.divider()
    st.header("📄 Essays with rubrics")

    with st.form("add_essay_form", clear_on_submit=True):
        prompt = st.text_area("Prompt", height=90)
        keywords_raw = st.text_input("Expected keywords (comma separated)")
        total_points = st.number_input("Rubric total points", min_value=0.0, value=5.0, step=0.5)
        notes = st.text_area("Grading notes", height=60)
        criteria_df = st.data_editor(
            pd.DataFrame([{"keyword": "", "weight": 1.0, "description": ""}]),
            num_rows="dynamic", key="criteria_editor",
            column_config={
                "keyword": st.column_config.TextColumn("Keyword"),
                "weight": st.column_config.NumberColumn("Weight", min_value=0.0, step=0.5),
                "description": st.column_config.TextColumn("Description"),
            }, use_container_width=True)
        e_c1, e_c2 = st.columns(2)
        e_difficulty = e_c1.selectbox("Difficulty", DIFFICULTIES, index=1, key="essay_difficulty")
        e_objective = e_c2.text_input("Learning objective", key="essay_objective")
        submitted_essay = st.form_submit_button("Add essay")

    if submitted_essay:
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        criteria = [
            {"keyword": r.get("keyword"), "weight": r.get("weight", 0),
             "description": r.get("description", "")}
            for _, r in criteria_df.iterrows()
            if isinstance(r.get("keyword"), str) and r.get("keyword").strip()
        ]
        if not prompt.strip():
            st.error("Prompt is required.")
        elif not keywords and not criteria:
            st.error("Add expected keywords and/or rubric criteria so the essay can be graded transparently.")
        else:
            P.add_essay(pkg, prompt, keywords, criteria, total_points, notes,
                        e_difficulty, e_objective)
            save_and_rerun(pkg)

    for idx, essay in enumerate(pkg.get("essay", [])):
        rubric = essay.get("rubric") or {}
        with st.expander(f"{idx + 1}. {essay.get('prompt', '(no prompt)')[:90]}"):
            st.markdown(f"`{essay.get('id')}` · difficulty `{essay.get('difficulty', '—')}` · "
                        f"total points `{rubric.get('total_points', 0)}`")
            kws = ", ".join(f"`{k}`" for k in essay.get("expected_keywords", []))
            if kws:
                st.markdown(f"Keywords: {kws}")
            crit_rows = [{"keyword": c.get("keyword"), "weight": c.get("weight"),
                          "description": c.get("description")} for c in rubric.get("criteria", [])]
            if crit_rows:
                st.dataframe(pd.DataFrame(crit_rows), use_container_width=True, hide_index=True)
            if rubric.get("grading_notes"):
                st.caption(rubric["grading_notes"])
            links = ", ".join(essay.get("node_links", [])) or "—"
            st.caption(f"Concept links: {links}")
            if st.button("Remove", key=f"del_ess_{essay.get('id')}_{idx}"):
                pkg["essay"].pop(idx)
                save_and_rerun(pkg)

    st.divider()
    st.caption(f"Danger zone — delete the whole package folder `{subject}/{package_id}` "
               f"(including published snapshots) via the filesystem. This UI keeps history intact.")
