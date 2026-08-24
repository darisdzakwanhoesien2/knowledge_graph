import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from core.attempts import (
    attempts_csv,
    attempts_dataframe,
    list_attempts,
    load_attempt,
)

BASE_DIR = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="📊 Review Results", layout="wide")
st.title("📊 Review Results")
st.caption("Inspect submissions, expand per-question grading evidence, and export a CSV comparison.")

entries = list_attempts()
if not entries:
    st.info("No submissions yet. Learners submit attempts from 🎯 Take a Test.")
    st.stop()

records = [load_attempt(e["attempt_id"]) for e in entries]
records = [r for r in records if r]

# =====================================================
# FILTERS
# =====================================================

f1, f2, f3 = st.columns(3)
subjects = ["All"] + sorted({r.get("subject") for r in records if r.get("subject")})
packages = ["All"] + sorted({r.get("package_key") for r in records if r.get("package_key")})
users = ["All"] + sorted({(r.get("user") or {}).get("display_name", "anonymous") for r in records})

subject_filter = f1.selectbox("Subject", subjects)
package_filter = f2.selectbox("Package", packages)
user_filter = f3.selectbox("Learner", users)

filtered = [
    r for r in records
    if subject_filter in ("All", r.get("subject"))
    and package_filter in ("All", r.get("package_key"))
    and user_filter in ("All", (r.get("user") or {}).get("display_name", "anonymous"))
]

if not filtered:
    st.warning("No submissions match the filters.")
    st.stop()

# =====================================================
# ATTEMPT SUMMARY TABLE
# =====================================================

summary_rows = []
for r in filtered:
    scores = r.get("scores", {})
    summary_rows.append({
        "attempt": r["attempt_id"],
        "learner": (r.get("user") or {}).get("display_name", "anonymous"),
        "subject": r.get("subject"),
        "package": r.get("package_key"),
        "version": f"v{r.get('package_version')}",
        "submitted_at": str(r.get("submitted_at", ""))[:19],
        "mcq": None if scores.get("mcq_pct") is None else round(scores["mcq_pct"], 4),
        "essay": None if scores.get("essay_pct") is None else round(scores["essay_pct"], 4),
        "final": scores.get("final_score"),
    })

summary = pd.DataFrame(summary_rows)
st.dataframe(
    summary,
    use_container_width=True,
    hide_index=True,
    column_config={
        "mcq": st.column_config.NumberColumn("MCQ %", format="percent"),
        "essay": st.column_config.NumberColumn("Essay %", format="percent"),
        "final": st.column_config.NumberColumn("Final %", format="percent"),
    },
)

st.download_button(
    "⬇️ Export filtered results as CSV",
    data=attempts_csv(filtered),
    file_name="results_export.csv",
    mime="text/csv",
    use_container_width=True,
)
st.caption(f"{len(filtered)} attempt(s) · CSV contains one row per question response "
           "with matched criteria evidence.")

st.divider()

# =====================================================
# PER-ATTEMPT EXPANDED REVIEW
# =====================================================

for r in filtered[:10]:
    scores = r.get("scores", {})
    header = (f"`{r['attempt_id']}` · {str(r.get('submitted_at', ''))[:19]} · "
              f"final {scores.get('final_score', 0):.0%}")
    with st.expander(header):
        st.markdown(f"**Package:** `{r.get('package_key')}` v{r.get('package_version')} · "
                    f"content hash `{str(r.get('package_content_hash'))[:12]}` · "
                    f"**Learner:** {(r.get('user') or {}).get('display_name', 'anonymous')}")
        for resp in r.get("responses", []):
            if resp.get("question_kind") == "mcq":
                correct = resp.get("correct") is True
                icon = "✅" if correct else "❌"
                body = (f"Answered `{resp.get('selected_option') or '—'}` · "
                        f"correct `{resp.get('correct_option')}`")
                label = resp.get("question", resp.get("question_id"))
            else:
                max_s = float(resp.get("max_score") or 0)
                pct = resp["score"] / max_s if max_s else 0
                icon = "✅" if pct >= 0.999 else ("🟡" if pct > 0 else "❌")
                body = f"Scored **{resp['score']:g}/{resp['max_score']:g}** ({pct:.0%})"
                label = (resp.get("prompt") or resp.get("question_id") or "").splitlines()[0]

            with st.expander(f"{icon} {str(label)[:90]}"):
                st.caption(body)
                if resp["question_kind"] == "essay":
                    text = resp.get("essay_text") or ""
                    st.markdown(text[:2000] + ("…" if len(text) > 2000 else ""))
                    crit = resp.get("matched_criteria") or []
                    if crit:
                        rows = [{
                            "keyword": c["keyword"],
                            "matched": c["matched"],
                            "weight": c["weight"],
                            "evidence": (c.get("evidence") or "")[:120],
                        } for c in crit]
                        st.dataframe(pd.DataFrame(rows), hide_index=True,
                                     use_container_width=True)
                    mk = ", ".join(f"`{k}`" for k in resp.get("matched_keywords", []))
                    if mk:
                        st.markdown(f"Matched keywords: {mk}")

        missed_links = []
        for resp in r.get("responses", []):
            good = resp.get("correct") is True or (
                resp.get("max_score") and (resp["score"] / resp["max_score"]) >= 0.999)
            if not good:
                missed_links.extend(resp.get("node_links", []))
        missed_links = [m for m in dict.fromkeys(missed_links)]
        if missed_links:
            st.markdown("**Concepts behind missed questions:** " +
                        ", ".join(f"`{m}`" for m in missed_links))
