# Technical Approach Report: Cynbit Growth Pipeline

## 1. Architecture
```
Goal + Cynbit context
        │
        ▼
 ┌─────────────┐   gate≥8   ┌─────────────┐   gate≥8   ┌─────────────┐   gate≥8   ┌──────┐
 │  Research   │ ─────────▶ │  Marketing  │ ─────────▶ │ Development │ ─────────▶ │  QA  │
 └─────────────┘            └─────────────┘            └─────────────┘            └──────┘
   each box:  Draft → Critic (JSON score) → Revise ◀── human note (optional)
                                   │
                                   ▼
                        feedback_log.jsonl  ──▶ injected into future prompts
```
- **Waterfall between stages:** a stage's approved output becomes the next stage's input. If a stage fails its gate after the iteration cap, the pipeline stops and asks a human.
- **Iteration inside a stage:** up to 3 draft/critic/revise rounds.
- **Feedback memory:** every critic and human note is appended to a JSONL log; the last five notes for that stage are added to the next prompt.

## 2. Model choices
| Role | Choice | Reason |
|---|---|---|
| Stage agents | Claude Sonnet-class model (configurable via `CYNBIT_MODEL`) | Strong long-context reasoning and structured writing at moderate cost |
| Critic | Same family, smaller/cheaper model in production | Scoring is a simpler task; separating critic from author reduces self-agreement bias |
| Offline mode | Deterministic mock | Lets reviewers run the demo with no API key |

No fine-tuning at this stage: prompt context plus accumulated feedback is faster to iterate and needs no labelled dataset.

## 3. Data pipeline
| Source | Use | Handling |
|---|---|---|
| cynbit.in pages, product docs | Company context | Static text in `COMPANY`; refresh monthly |
| Revio review data | Customer-voice insight for Research | Planned: aggregate and anonymise before prompting |
| Studio / TenantEase usage data | Backlog evidence | Planned: aggregated metrics only, no personal data in prompts |
| Public web (competitors, news) | Research | Planned: search tool with citations required |
| Feedback log | Learning loop | JSONL now; move to a database with per-stage retrieval later |

## 4. Prompt engineering
- Each stage has a **role prompt** with required output sections, so outputs are comparable across runs.
- Prompts carry: company context, goal, upstream approved output, lessons from past runs, and current revision feedback.
- The **critic** prompt returns strict JSON (`score`, `feedback`) and is parsed defensively; an unparseable reply scores 0 and escalates to a human.
- Planned: require a source for every factual claim in Research, and have QA verify those claims.

## 5. Evaluation
- **Gate score** from the critic (specificity, evidence, fit).
- **Human acceptance rate:** share of stage outputs approved with no edits.
- **Iterations to pass** and **time-to-brief** versus the current manual process.
- **Contradictions caught at QA** per run.
- Calibrate the critic against 20-30 human-rated outputs before trusting its scores.

## 6. Execution plan
| Phase | Weeks | Deliverable |
|---|---|---|
| 1. Prototype (this repo) | 0 | Pipeline, Streamlit UI, mock mode, feedback log |
| 2. Grounding | 1-2 | Web search with citations; real Revio review sample as research input |
| 3. Pilot | 3-5 | Run on one real campaign for Revio; team rates outputs; calibrate critic |
| 4. Integrate | 6-8 | Database-backed feedback store, Notion/Jira export of backlog items, auth and audit log |
| 5. Extend | 9+ | Add review-intelligence module for Revio |

## 7. Limitations of the current prototype
- Mock mode does not demonstrate output quality; real quality depends on the API-backed run.
- No web search or live data connectors yet.
- Feedback memory is a flat log with no ranking; it will need retrieval as it grows.
- Critic scores are model judgments and must be calibrated against humans.

## 8. Run it
```
pip install -r requirements.txt
python pipeline.py            # CLI, mock mode
streamlit run app.py          # UI
export ANTHROPIC_API_KEY=...  # optional: real LLM calls
```
