"""v0.347 (owner: "GO 1 3"):
1. LAMBE KAAM KI REPORT - `python -m app.quality longjobs` / vps-ops long_jobs: how her REAL long jobs went in the last
   24 h, read from what Hoola already records (agent_task_runs, goal_runs, harness_events turn_failed). Free.
2. The tool card reads a question in her style without a '?' ("bataiye kis customer ki complaint hai")."""
import asyncio
from datetime import timedelta
from pathlib import Path

from tests.test_bazar import bz  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


def _seed():
    from app.agent.eventlog import HarnessEvent, ensure_table
    from app.agent.goal import GoalRun
    from app.agent.pakka import TaskRun
    from app.db import now, session
    ensure_table()
    with session() as s:
        s.add(TaskRun(tenant_id="default", request="bakery ka marketing plan banao", outcome="done", steps=9,
                      seconds=300))
        s.add(TaskRun(tenant_id="default", request="Myntra Ajio Amazon price compare karo", outcome="partial",
                      steps=12, failures=3, left="Amazon server se nahi khula", seconds=900,
                      tools='["browse_web", "computer_operator"]'))
        s.add(TaskRun(tenant_id="default", request="namaste", outcome="talk", steps=0))
        s.add(TaskRun(tenant_id="default", request="purana kaam", outcome="stuck", steps=8,
                      created_at=now() - timedelta(days=3)))                     # outside the window
        s.add(GoalRun(tenant_id="default", conversation_id="c1", goal="launch ki taiyari", status="done"))
        s.add(GoalRun(tenant_id="default", conversation_id="c2", goal="price compare", status="blocked",
                      hold="limit", rounds=6, recovered=1, reason="Aage badhaun?"))
        s.add(HarnessEvent(tenant_id="default", conversation_id="c3", kind="turn_failed",
                           payload='{"line": "turn timeout (900s)"}'))


def test_the_report_reads_her_real_jobs(bz):  # noqa: F811
    _seed()
    from app.quality import longjobs as LJ
    r = LJ.report(24)
    assert r["long_jobs"] == 2 and r["done"] == 1 and r["done_pct"] == 50   # talk + 3-day-old turn not counted
    assert r["outcomes"] == {"done": 1, "partial": 1}
    assert r["plans"] == 2 and r["plan_status"] == {"done": 1, "blocked": 1}
    assert r["turn_failures"] == 1 and r["failure_kinds"] == {"timeout": 1}
    text = "\n".join(LJ.lines(r))
    assert "2 ran" in text and "1 finished (50%)" in text
    assert "[partial] Myntra Ajio Amazon price compare karo" in text and "left: Amazon server se nahi khula" in text
    assert "[blocked/limit] price compare" in text and "picked up after restart x1" in text
    assert "turn timeout (900s)" in text


def test_an_empty_day_says_so(bz):  # noqa: F811
    from app.quality import longjobs as LJ
    assert LJ.lines(LJ.report(24)) == ["Long jobs, last 24 h: none ran."]


def test_the_cli_and_the_vps_ops_job():
    src = (ROOT / "server/app/quality/__main__.py").read_text()
    assert 'argv[0] == "longjobs"' in src
    y = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    assert "          - long_jobs\n" in y and "app.quality longjobs --hours 24" in y


def test_a_question_without_a_question_mark_counts(monkeypatch):
    from app.agent import santosh
    from app.config import get_settings
    from app.quality import toolchoice as T

    async def think(*a, **k):
        return [{"type": "text", "text": "Bataiye kis customer ki complaint hai aur kya shikayat hai."}], "end_turn", "claude"
    monkeypatch.setattr(santosh, "_think", think)
    complaint = next(a for a in T.fresh_asks() if a["text"].startswith("customer ki complaint"))
    r = asyncio.run(T._first_pick(complaint, "claude", get_settings()))
    assert r["asked"] and r["right"]
    quote = next(a for a in T.fresh_asks() if "quotation PDF" in a["text"])
    assert not asyncio.run(T._first_pick(quote, "claude", get_settings()))["right"]   # still strict where work was due
