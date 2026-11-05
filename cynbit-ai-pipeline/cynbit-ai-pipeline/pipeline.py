"""Cynbit Growth Pipeline: waterfall stages with iterative critic/human feedback loops.

Stages (waterfall):  Research -> Marketing -> Development -> Release QA
Inside each stage (iterative): Draft -> Critic score -> Revise (+ optional human feedback)
Learning loop: every critic/human note is stored in feedback_log.jsonl and injected
into future prompts for the same stage.

Runs offline in MOCK mode (no key needed). Set ANTHROPIC_API_KEY for real LLM calls.
"""
import json, os, re, time
from dataclasses import dataclass, field
from pathlib import Path

MODEL = os.getenv("CYNBIT_MODEL", "claude-sonnet-4-6")
THRESHOLD = float(os.getenv("CYNBIT_THRESHOLD", "8"))
MAX_ITER = int(os.getenv("CYNBIT_MAX_ITER", "3"))
LOG = Path(os.getenv("CYNBIT_LOG", "feedback_log.jsonl"))

COMPANY = """Cynbit Technologies (Jaipur, India; cynbit.in). Builds AI-powered SaaS:
- Cynbit Studio: adaptive coding paths, AI code evaluation, AI mock interviews, resume engine, job matcher.
- TenantEase: property/tenant management, rent tracking, auto reminders, occupancy dashboard.
- Revio: AI review/reputation management, sentiment analysis, auto-replies, multi-location.
- BitElevate learning ecosystem; custom software and AI agent services."""

STAGES = {
    "research": "You are a market-research analyst. Produce: target segments, pain points, 3 competitors, 3 evidence-backed insights, open questions.",
    "marketing": "You are a growth marketer. Using the research, produce: positioning, 3 audience-specific messages, a 2-week content calendar, one landing-page headline set, KPIs.",
    "development": "You are a product engineer. Using research and marketing, produce: a prioritized feature backlog (MoSCoW), one user story with acceptance criteria, data/model needs, risks.",
    "qa": "You are a release reviewer. Check consistency between research, marketing claims and the backlog. List contradictions, unsupported claims, and a go/no-go.",
}

def _mock(system: str, user: str) -> str:
    if "CRITIC" in system:
        n = int(re.search(r"ITERATION=(\d+)", user).group(1))
        score = min(9.0, 5.5 + 1.5 * n)
        fb = "Add concrete metrics and cite a source for each claim." if score < THRESHOLD else "Meets the bar."
        return json.dumps({"score": score, "feedback": fb})
    n = int(re.search(r"ITERATION=(\d+)", user).group(1))
    return f"[MOCK draft v{n}] {system.split('.')[0]}.\nAddressed feedback: {n > 1}\n(Set ANTHROPIC_API_KEY for real output.)"

def llm(system: str, user: str, max_tokens: int = 1200) -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return _mock(system, user)
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    r = client.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                               messages=[{"role": "user", "content": user}])
    return r.content[0].text

def past_feedback(stage: str, k: int = 5) -> list[str]:
    if not LOG.exists():
        return []
    rows = [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    return [r["feedback"] for r in rows if r["stage"] == stage][-k:]

def log_feedback(stage: str, source: str, score, feedback: str):
    with LOG.open("a") as f:
        f.write(json.dumps({"t": time.time(), "stage": stage, "source": source,
                            "score": score, "feedback": feedback}) + "\n")

def critic(stage: str, draft: str, i: int) -> dict:
    system = "CRITIC. Score the draft 0-10 for specificity, evidence, and fit with Cynbit. Reply ONLY JSON: {\"score\": number, \"feedback\": string}."
    raw = llm(system, f"ITERATION={i}\nSTAGE={stage}\nDRAFT:\n{draft}", 300)
    try:
        return json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
    except Exception:
        return {"score": 0, "feedback": "Critic output unparseable; needs human review."}

@dataclass
class StageResult:
    stage: str
    output: str
    score: float
    iterations: int
    passed: bool
    history: list = field(default_factory=list)

def run_stage(stage, goal, upstream, human_feedback=None) -> StageResult:
    notes = past_feedback(stage)
    feedback, history, out, score = "", [], "", 0.0
    for i in range(1, MAX_ITER + 1):
        user = (f"ITERATION={i}\nCOMPANY:\n{COMPANY}\nGOAL: {goal}\nUPSTREAM:\n{upstream}\n"
                f"LESSONS FROM PAST RUNS: {notes}\nREVISE USING: {feedback}")
        out = llm(STAGES[stage], user)
        c = critic(stage, out, i)
        score, feedback = float(c["score"]), c["feedback"]
        log_feedback(stage, "critic", score, feedback)
        history.append({"iteration": i, "score": score, "feedback": feedback})
        if human_feedback:                       # human-in-the-loop hook
            h = human_feedback(stage, out)
            if h:
                feedback += " HUMAN: " + h
                log_feedback(stage, "human", None, h)
                score = min(score, THRESHOLD - 0.1)   # human note forces another pass
        if score >= THRESHOLD:
            return StageResult(stage, out, score, i, True, history)
    return StageResult(stage, out, score, MAX_ITER, False, history)  # escalate to human

def run_pipeline(goal: str, human_feedback=None, on_stage=None) -> list[StageResult]:
    results, upstream = [], ""
    for stage in STAGES:                         # waterfall: each gate feeds the next
        r = run_stage(stage, goal, upstream, human_feedback)
        results.append(r)
        if on_stage:
            on_stage(r)
        upstream += f"\n## {stage}\n{r.output}\n"
        if not r.passed:
            break                                # gate failed: stop and ask a human
    return results

if __name__ == "__main__":
    for r in run_pipeline("Grow Revio adoption among multi-branch restaurants in Rajasthan"):
        print(f"{r.stage:12} score={r.score} iters={r.iterations} passed={r.passed}")
