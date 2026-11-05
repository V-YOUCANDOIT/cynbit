# Cynbit Growth Pipeline (AI/ML Intern Task)

An automated, waterfall-plus-iterative pipeline (Research → Marketing → Development → QA) with critic and human feedback loops, built for Cynbit Technologies.

- `docs/01_AI_Opportunity_Report.md`: industry analysis and opportunity ranking
- `docs/02_Technical_Approach_Report.md`: architecture, models, data, prompts, plan
- `pipeline.py`: core logic. `app.py`: Streamlit demo.

```
pip install -r requirements.txt
streamlit run app.py
```
Runs offline in mock mode; set `ANTHROPIC_API_KEY` for real LLM output.
