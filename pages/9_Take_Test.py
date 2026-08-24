import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from core import attempts as A
from core import packages as P
from core.learning_links import learning_context

BASE_DIR = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="🎯 Take a Test", layout="wide")
st.title("🎯 Take a Test")
st.caption("Answer the MCQs and essays, then submit once. Grading is transparent: "
           "correct options and matched rubric criteria are shown after submission.")

# =====================================================
# LEARNER IDENTITY (local-first; USER is implicit)
# =====================================================


def learner_user():
    display_name = st.session_state.get("learner_name", "").strip()
    return {"external_key": "local_user", "display_name": display_name or "anonymous"}


def published_packages():
    out = {}
    for entry in P.list_packages():
        pkg = P.load_package(entry["subject"], entry["package_id"])
        if pkg and pkg.get("status") == "published":
            out.setdefault(entry["subject"], []).append(pkg)
    return out


def render_results(record):
    scores = record["scores"]
    st.success(f"Attempt `{record['attempt_id']}` submitted at {record['submitted_at']} — "
               f"final score **{scores['final_score']:.0%}**")

    k1, k2, k3 = st.columns(3)
    k1.metric("MCQ", f"{scores['mcq_score']:g}/{scores['mcq_max']:g}",
              None if scores["mcq_pct"] is None else f"{scores['mcq_pct']:.0%}")
    k2.metric("Essay", f"{scores['essay_score']:g}/{scores['essay_max']:g}",
              None if scores["essay_pct"] is None else f"{scores['essay_pct']:.0%}")
    k3.metric("Final", f"{scores['final_score']:.0%}")

    missed_concepts = []
    for resp in record["responses"]:
        correct = resp.get("correct") is True or (
            resp.get("max_score") and (resp["score"] / resp["max_score"]) >= 0.999)
        icon = "✅" if correct else "❌"
        title = resp.get("question") or resp.get("prompt") or resp.get("question_id")
        with st.expander(f"{icon} {str(title)[:100]}"):
            if resp["question_kind"] == "mcq":
                st.markdown(f"**Your answer:** `{resp.get('selected_option') or '—'}` · "
                            f"**Correct:** `{resp.get('correct_option')}`")
            else:
                st.markdown("**Your answer:**")
                st.markdown(resp.get("essay_text") or "_empty_")
                mk = ", ".join(f"`{k}`" for k in resp.get("matched_keywords", []))
                st.markdown(f"**Matched keywords:** {mk or '—'}")
                crit = resp.get("matched_criteria") or []
                if crit:
                    st.markdown("**Rubric criteria:**")
                    for c in crit:
                        mark = "🟢" if c["matched"] else "⚪"
                        evidence = c.get("evidence") or ""
                        line = f"- {mark} `{c['keyword']}` (+{c['weight']:g})"
                        if evidence:
                            line += f' — “…{evidence}…”'
                        st.markdown(line)
                if resp.get("grading_notes"):
                    st.caption(f"Grading note: {resp['grading_notes']}")
                st.caption("Keyword grading is assistive — curators retain final say.")
            for link in resp.get("node_links", []):
                ctx = learning_context(link)
                if not ctx.get("exists"):
                    continue
                card = ctx.get("flashcard") or {}
                missed_concepts.append(ctx["node"])
                st.markdown("---")
                st.markdown(f"🔗 **Concept:** {ctx['node']}"
                            + (f"  \n📘 {ctx['definition']}" if ctx.get("definition") else ""))
                neighbors = ctx.get("neighbors") or []
                if neighbors:
                    st.caption("Related: " + ", ".join(n[0] for n in neighbors[:6]))
                front = card.get("front")
                back = card.get("back")
                if front or back:
                    with st.expander("🃏 Related flashcard"):
                        if front:
                            st.markdown(front)
                        if back:
                            st.markdown(back)

    if missed_concepts:
        st.divider()
        st.subheader("Study suggestions from your misses")
        for name in dict.fromkeys(missed_concepts):
            st.page_link("pages/3_Learn_From_Node.py", label=f"Explore “{name}”", icon="🔎")


def render_test_form():
    user = learner_user()
    with st.sidebar:
        st.header("Learner")
        st.text_input("Your name", key="learner_name")
        st.caption(f"Recording attempts as `{user['display_name']}`")

    available = published_packages()
    if not available:
        st.warning("No published packages yet. Curators can publish one from ✍️ Author Packages.")
        st.stop()

    subjects = sorted(available.keys())
    col1, col2 = st.columns(2)
    subject = col1.selectbox("Subject", subjects)
    pkg_list = available[subject]
    labels = [f"{p['package_id']} — {p.get('title', '')} (v{p.get('version')})" for p in pkg_list]
    package_label = col2.selectbox("Package", labels)
    pkg = pkg_list[labels.index(package_label)]

    snapshot = P.load_published_version(subject, pkg["package_id"], int(pkg["version"]))
    if snapshot is None:
        st.error(f"Published snapshot v{pkg['version']} is missing for {pkg['package_key']}. "
                 "Re-publish from ✍️ Author Packages.")
        st.stop()

    st.info(f"**{snapshot.get('title')}** · level: {snapshot.get('level') or '—'} · "
            f"{len(snapshot.get('mcqs', []))} MCQs · {len(snapshot.get('essay', []))} essays · "
            f"version v{snapshot.get('version')} ({str(snapshot.get('content_hash', ''))[:12]})")

    mcqs = snapshot.get("mcqs", [])
    essays = snapshot.get("essay", [])
    answers_mcq = {}
    answers_essay = {}

    with st.form("test_form"):
        if mcqs:
            st.header("📝 Multiple choice")
            for i, q in enumerate(mcqs):
                st.markdown(f"**{i + 1}. {q['question']}**")
                if q.get("learning_objective"):
                    st.caption(f"Objective: {q['learning_objective']}")
                ordered = sorted(q["options"].items())
                letter = st.radio(
                    "Select one:",
                    [k for k, _ in ordered],
                    format_func=lambda k, _q=q: f"{k}. {_q['options'][k]}",
                    key=f"mcq_{q['id']}",
                    label_visibility="collapsed",
                    index=None,
                )
                answers_mcq[q["id"]] = letter

        if essays:
            st.header("📄 Essays")
            for i, q in enumerate(essays):
                st.markdown(f"**{i + 1}. {q['prompt'].splitlines()[0]}**")
                if len(q["prompt"].splitlines()) > 1:
                    with st.expander("Full prompt / source excerpt"):
                        st.markdown(q["prompt"])
                if q.get("learning_objective"):
                    st.caption(f"Objective: {q['learning_objective']}")
                rubric = q.get("rubric") or {}
                if rubric.get("total_points"):
                    st.caption(f"Worth up to {rubric['total_points']:g} points")
                answers_essay[q["id"]] = st.text_area(
                    "Your answer:", key=f"essay_{q['id']}", height=140,
                    label_visibility="collapsed")

        unanswered = [i + 1 for i, q in enumerate(mcqs) if not answers_mcq.get(q["id"])]
        submitted = st.form_submit_button("Submit test", use_container_width=True,
                                          type="primary")

    if not submitted:
        if unanswered:
            st.caption(f"⚠️ MCQs not yet answered: {', '.join(map(str, unanswered))}")
        st.stop()

    record = A.submit_attempt(user=user, pkg_snapshot=snapshot,
                              answers_mcq=answers_mcq, answers_essay=answers_essay)
    st.session_state["active_attempt"] = record
    st.rerun()


if "active_attempt" in st.session_state:
    render_results(st.session_state["active_attempt"])
    if st.button("Start a new attempt"):
        del st.session_state["active_attempt"]
        st.rerun()
else:
    render_test_form()
