import streamlit as st
from pipeline import run_pipeline, STAGES, THRESHOLD

st.set_page_config(page_title="Cynbit Growth Pipeline", layout="wide")
st.title("Cynbit Growth Pipeline")
st.caption("Research → Marketing → Development → QA, each stage looping on critic and human feedback.")

goal = st.text_input("Goal", "Grow Revio adoption among multi-branch restaurants in Rajasthan")
note = st.text_input("Optional human feedback applied once to every stage", "")

if st.button("Run pipeline"):
    used = {"n": 0}
    def human(stage, out):
        if note and used["n"] < len(STAGES):
            used["n"] += 1
            return note
    for r in run_pipeline(goal, human_feedback=human):
        with st.expander(f"{r.stage.title()} | score {r.score:.1f} | {r.iterations} iteration(s) | {'passed' if r.passed else 'needs human review'}", expanded=True):
            st.write(r.output)
            st.dataframe(r.history, use_container_width=True)
    st.info(f"Pass threshold: {THRESHOLD}. Notes are saved to feedback_log.jsonl and reused in future runs.")
