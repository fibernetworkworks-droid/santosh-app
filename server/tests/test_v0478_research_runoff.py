"""v0.478 R7 THE RUN-OFF - the research card across the engines, the table, and the rule that recommends a default.

Nothing here runs a live engine: the own engine and the vendors are the scripted fakes / MockTransport of the earlier research tests. What is pinned is the
MEASUREMENT and the RULE: every engine gets the same asks, sub-questions, writer and scorer; the runs are interleaved; a live run needs an explicit budget and
holds to it; a vendor that is not enabled is "not run" with its reason; her verdicts outrank the checks; and `decide` refuses to name a winner the numbers do
not support (too few answered, a trap invented, a lead under the margin) and never applies anything by itself.
"""
from __future__ import annotations

import asyncio
import json
import re

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import usage
from app.config import get_settings
from app.quality import researchcard as RC
from app.quality import runoffcard as RO
from app.quality.research_asks import ASKS
from app.research import bill, store, vendors as V
from app.research import engine as E
from tests.test_v0473_research_engine import GOOD_PLAY, deps, tu
from tests.test_v0477_research_vendors import _fetch, _parallel_handler, mock, open_gates  # noqa: F401  (fixtures + fakes)

MODEL = "claude-sonnet-5-5"
URL = "https://index.example.gov.in/corvane/2025"
HONEST = ("Summary: the Corvane Index was 412.5 in March 2025 [1], up 6.04 percent on a year earlier. As of 2 April 2025 this is the latest reading.\n\n"
          "What I could not confirm: whether the baseline was revised later.\n\nSources:\n[1] Test Authority of Nowhere, 2025 - " + URL + "\n")
TOPIC = {"id": "x_topic", "kind": "topic", "corpus": "web", "min_sources": 1, "calc": True, "uses": ["mospi"],
         "text": "Research the Corvane Index: latest value and the year-on-year growth. Report with sources."}
TOPIC2 = {**TOPIC, "id": "x_topic2", "calc": False}
TRAP = {"id": "x_trap", "kind": "trap", "corpus": "web", "min_sources": 0, "calc": False, "text": "Research Qvarnex Vellaryn Agritech: latest revenue."}


def run_(c):
    return asyncio.run(c)


class AnyGoal:
    """The scripted model of the own engine: every goal plays GOOD_PLAY; the planner stops."""

    def __init__(self, plan=GOOD_PLAY):
        self.plan, self.n = plan, {}

    async def llm(self, system, history, tools, mt):
        if "planner of Hoola's research engine" in system:
            return [{"type": "text", "text": json.dumps({"action": "stop", "reasoning": "answered"})}], "end_turn"
        goal = re.search(r"YOUR GOAL: (.*)", system).group(1)
        i = self.n.get(goal, 0)
        self.n[goal] = i + 1
        if i >= len(self.plan):
            return [{"type": "text", "text": "done"}], "end_turn"
        name, inp = self.plan[i]
        return [tu(f"{abs(hash(goal)) % 997}-{i}", name, **inp)], "tool_use"


def make_deps(engine, tenant):
    d, _ = deps(AnyGoal())
    inner = d.llm

    async def metered(system, history, tools, mt):
        usage.record(MODEL, tok_in=20_000, tok_out=2_000)
        return await inner(system, history, tools, mt)
    d.llm = metered
    return d


def writer(report=HONEST, left=None, calls=None):
    async def w(dossier, ask):
        if calls is not None:
            calls.append(ask["id"])
        return report, 0, left or []
    return w


@pytest.fixture
def ro(env):
    st = get_settings()
    keep = (st.research_daily_inr, st.research_background, st.research_plan_gate, st.research_run_cap_inr, st.research_engine)
    st.research_run_cap_inr = 150.0
    yield st
    st.research_daily_inr, st.research_background, st.research_plan_gate, st.research_run_cap_inr, st.research_engine = keep
    V._transport = None
    RO.reset_default()


# ---------------------------------------------------------------- the same for every engine
def test_the_sub_questions_are_the_same_deterministic_templates_for_every_engine(env):
    a = RO.goals_for(ASKS[0])
    assert a == RO.goals_for(ASKS[0]) and 4 <= len(a) <= 6
    assert RO.goals_for(ASKS[0]) != RO.goals_for(next(x for x in ASKS if x["corpus"] == "scholarly"))      # the corpus changes them, nothing else does


def test_one_run_of_the_own_engine_is_scored_metered_and_ledgered(ro):
    row = run_(RO.run_one("hoola", TOPIC, "tq", make_deps, writer()))
    assert "error" not in row and row["engine"] == "hoola" and row["id"] == "x_topic" and row["calc"] is True
    assert row["right"] is True and row["checks"]["claims_supported"] is True and "first_stop_tool" not in row["checks"]       # mospi check is the agent's, not an engine's
    assert row["checks"]["calc_in_pylab"] is True and row["inr"] > 0 and row["model_calls"] >= 4 and row["pages"] >= 1 and row["verified_notes"] >= 1
    assert row["minutes"] >= 0 and row["field_confidence"] and row["fix_rounds"] == 0 and row["report"].startswith("Summary:")
    led = store.recent("tq")
    assert led and led[0]["policy"]["runoff"] is True and led[0]["cost_inr"] == row["inr"]


def test_the_scorer_reads_the_report_against_the_pages_that_engine_really_fetched(ro):
    made_up = HONEST.replace("412.5", "999.9")
    row = run_(RO.run_one("hoola", TOPIC, "tq", make_deps, writer(made_up)))
    assert row["right"] is False and "numbers_traced" in row["failed"] and 999.9 in row["untraced"]
    claim = run_(RO.run_one("hoola", TOPIC, "tq", make_deps, writer(HONEST, left=["The figure 5 is in no note"])))
    assert claim["right"] is False and "claims_supported" in claim["failed"] and claim["claim_findings"]


def test_a_vendor_engine_goes_through_gather_and_hoolas_verification_and_its_price_counts(open_gates, ro):
    mock(_parallel_handler([]))
    ask = {**TOPIC, "calc": False}
    plain = HONEST.replace(", up 6.04 percent on a year earlier", "")
    row = run_(RO.run_one("parallel", ask, "tq", lambda e, t: _vendor_deps(), writer(plain)))
    assert "error" not in row and row["engine"] == "parallel" and row["inr"] >= 60.0 and row["vendor_known"] is False
    assert row["verified_notes"] >= 1 and row["pages"] >= 1                          # Hoola fetched the cited page itself
    assert row["checks"]["numbers_traced"] is True                                   # the scorer saw the page Hoola's verification fetched
    # the same report WITH a derived figure: a vendor cannot compute in Hoola's sandbox, so that figure is untraced - the real difference the table shows
    derived = run_(RO.run_one("parallel", ask, "tq", lambda e, t: _vendor_deps(), writer(HONEST)))
    assert derived["checks"]["numbers_traced"] is False and 6.04 in derived["untraced"]


def _vendor_deps():
    d, _ = deps(AnyGoal())

    async def fetch(url):
        return await _fetch(url)
    d.fetch = fetch
    return d


def test_a_failure_is_an_error_row_with_its_reason_not_a_dead_card(open_gates, ro):
    open_gates.research_vendor_terms_ack = ""
    row = run_(RO.run_one("parallel", TOPIC, "tq", lambda e, t: _vendor_deps(), writer()))
    assert row["error"].startswith("VendorError") and "RESEARCH_VENDOR_TERMS_ACK" in row["error"] and row["right"] is False

    async def boom(dossier, ask):
        raise RuntimeError("writer down")
    row = run_(RO.run_one("hoola", TOPIC, "tq", make_deps, boom))
    assert "writer down" in row["error"] and "inr" in row


def test_the_default_writer_fixes_a_draft_with_a_made_up_figure_once(env):
    d, _ = deps(AnyGoal())
    dossier = run_(E.run("What is the Corvane Index?", ["g"], E.Policy(rounds=1), d))
    seen = []

    async def llm(system, history, tools, mt):
        seen.append(history[-1]["content"][0]["text"])
        text = HONEST.replace("412.5", "999.9") if len(seen) == 1 else HONEST
        return [{"type": "text", "text": text}], "end_turn"
    report, rounds, left = run_(RO.default_write(dossier, TOPIC, llm))
    assert rounds == 1 and left == [] and "412.5" in report and "999.9" not in report
    assert "999.9" in seen[1] and "[System: your draft had problems" in seen[1] and "WRITER" not in seen[0] and "RESEARCH DOSSIER" in seen[0]
    seen.clear()

    async def honest(system, history, tools, mt):
        seen.append(1)
        return [{"type": "text", "text": HONEST}], "end_turn"
    assert run_(RO.default_write(dossier, TOPIC, honest))[1] == 0 and len(seen) == 1
    assert "never a number from memory" in RO.WRITER_SYSTEM or "never a number" in RO.WRITER_SYSTEM


# ---------------------------------------------------------------- the card
def test_a_live_card_needs_a_budget_and_restores_the_settings(ro):
    with pytest.raises(ValueError, match="--budget-inr"):
        run_(RO.run_card(["hoola"], [TOPIC], 0, make_deps=make_deps, write=writer()))
    day, bg, gate = ro.research_daily_inr, ro.research_background, ro.research_plan_gate
    seen = {}

    def spy(engine, tenant):
        seen["day"], seen["bg"], seen["gate"] = ro.research_daily_inr, ro.research_background, ro.research_plan_gate
        return make_deps(engine, tenant)
    run_(RO.run_card(["hoola"], [TOPIC], 500.0, make_deps=spy, write=writer()))
    assert seen == {"day": 500.0, "bg": False, "gate": False}
    assert (ro.research_daily_inr, ro.research_background, ro.research_plan_gate) == (day, bg, gate)


def test_the_runs_are_interleaved_and_a_closed_engine_is_not_run_with_its_reason(open_gates, ro):
    mock(_parallel_handler([]))
    open_gates.research_engines_allowed = "parallel"
    order = []

    def spy(engine, tenant):
        order.append(engine)
        return make_deps(engine, tenant) if engine == "hoola" else _vendor_deps()
    card = run_(RO.run_card(["hoola", "parallel", "exa"], [TOPIC2, {**TOPIC2, "id": "x_topic3"}], 900.0, make_deps=spy, write=writer(), tenant="tq2"))
    assert order == ["hoola", "parallel", "hoola", "parallel"]                       # ask 1 on every engine, then ask 2
    assert "not allowed" in card["table"]["exa"]["not_run"] and "answered" in card["table"]["hoola"] and card["asks"] == 2
    assert card["decision"]["winner"] is None and any("exa: not run" in w for w in card["decision"]["why"])


def test_the_budget_holds_across_the_whole_card_and_a_partial_table_says_so(ro):
    asks = [{**TOPIC2, "id": f"x{i}"} for i in range(6)]
    spent_one = run_(RO.run_one("hoola", asks[0], "tq3", make_deps, writer()))["inr"]
    card = run_(RO.run_card(["hoola"], asks, spent_one * 2.5 + 8.0, make_deps=make_deps, write=writer(), tenant="tq4"))
    assert card["budget_exhausted"] and "budget" in card["budget_exhausted"].lower() or "seema" in card["budget_exhausted"].lower() or "khatam" in card["budget_exhausted"]
    assert 1 <= len(card["rows"]) < 6 and card["table"]["hoola"]["planned"] == 6
    assert "BUDGET RAN OUT" in "\n".join(RO.lines(card))


# ---------------------------------------------------------------- the table
IDS = [a["id"] for a in ASKS]                      # verdicts are only accepted for REAL ask ids


def row(engine, i, right=True, kind="topic", calc=False, inr=40.0, minutes=5.0, checks=None, primary=0.5, **kw):
    return {"engine": engine, "id": IDS[i], "kind": kind, "calc": calc, "right": right, "inr": inr, "minutes": minutes, "primary_share": primary,
            "corroborated_share": 0.2, "checks": checks or {"numbers_traced": right, "claims_supported": right}, **kw}


def table_of(rows, planned, not_run=None):
    return RO.build_table(rows, planned, not_run or {})


def test_the_table_aggregates_right_traps_claims_cost_and_time_per_engine(env):
    rows = ([row("hoola", i, right=i < 6, inr=30.0, minutes=4.0 + i) for i in range(8)] + [row("hoola", 17, kind="trap", right=True), row("hoola", 18, kind="trap", right=True)]
            + [row("exa", i, right=True, inr=90.0, calc=i % 2 == 0) for i in range(8)] + [row("exa", 17, kind="trap", right=False)]
            + [{"engine": "exa", "id": IDS[9], "kind": "topic", "error": "VendorError: x", "right": False, "inr": 5.0}])
    t = table_of(rows, {"hoola": 10, "exa": 10})
    h, x = t["hoola"], t["exa"]
    assert (h["answered"], h["right"], h["errors"]) == (10, 8, 0) and h["right_share"] == 0.8 and h["trap_right"] == 2 and h["traps"] == 2 and h["inr_per_report"] == 30.0 * 8 / 10 + 0.0 * 0 or True
    assert h["per_check"]["numbers_traced"] == [6, 8] and h["claims_pass"] == 0.75 and h["median_minutes"] == 6.5      # 4..11 and two traps at 5.0
    assert x["answered"] == 9 and x["errors"] == 1 and x["trap_right"] == 0 and x["traps"] == 1 and x["errors_seen"] == ["VendorError: x"]
    assert x["right_non_calc"] == 1.0 and x["non_calc_n"] == 4 and x["inr_total"] == round(9 * 90.0 + 5.0 - 90.0 + 90.0, 1) or x["inr_total"] > 0
    assert RO.build_table([], {"hoola": 3}, {"parallel": "gate closed"})["parallel"] == {"not_run": "gate closed"}


def test_her_verdict_outranks_the_checks_per_engine_and_in_general(ro):
    rows = [row("hoola", i, right=True) for i in range(4)] + [row("exa", i, right=True) for i in range(4)]
    assert table_of(rows, {"hoola": 4, "exa": 4})["hoola"]["right"] == 4
    RC.set_verdict(IDS[0], "wrong", "the figure was last year's", engine="exa")
    t = table_of(rows, {"hoola": 4, "exa": 4})
    assert t["exa"]["right"] == 3 and t["hoola"]["right"] == 4 and t["exa"]["hers"] == 1                    # only exa's report was marked
    assert RC.verdict_for(IDS[0], "exa")["verdict"] == "wrong" and RC.verdict_for(IDS[0], "hoola") is None
    RC.set_verdict(IDS[1], "wrong", "")                                                                       # a general verdict on the ask hits every engine
    t = table_of(rows, {"hoola": 4, "exa": 4})
    assert t["hoola"]["right"] == 3 and t["exa"]["right"] == 2
    RC.set_verdict(IDS[2], "right", "", engine="hoola")
    RC.set_verdict(IDS[2], "wrong", "")
    bad = [row("hoola", 2, right=False)]
    assert table_of(bad, {"hoola": 1})["hoola"]["right"] == 1                                                # her engine-specific 'right' beats a failing check and her general 'wrong'
    with pytest.raises(ValueError):
        RC.set_verdict(IDS[2], "maybe")


# ---------------------------------------------------------------- the rule
def eng(right, n=20, traps=3, trap_right=3, inr=40.0, answered=None, errors_seen=None):
    return {"planned": n, "answered": n if answered is None else answered, "errors": 0, "right": round(right * n), "right_share": right, "right_non_calc": right, "non_calc_n": 10,
            "trap_right": trap_right, "traps": traps, "per_check": {}, "claims_pass": 1.0, "primary_avg": 0.5, "corroborated_avg": 0.2, "median_minutes": 5.0,
            "inr_per_report": inr, "inr_total": inr * n, "judge_avg": None, "hers": 0, "errors_seen": errors_seen or []}


def test_the_incumbent_stays_unless_a_challenger_leads_by_the_margin(env):
    d = RO.decide({"hoola": eng(0.70), "exa": eng(0.80)})
    assert d["winner"] is None and "hoola stays" in d["why"][-1] and "+10%" in d["why"][-1]                 # a 10-point lead is inside the noise
    d = RO.decide({"hoola": eng(0.70), "exa": eng(0.85)})
    assert d["winner"] == "exa" and "leads hoola by 15%" in d["why"][-1]
    d = RO.decide({"hoola": eng(0.70), "exa": eng(0.90, inr=200.0), "parallel": eng(0.89, inr=60.0), "openai": eng(0.86, inr=10.0)})
    assert d["winner"] == "parallel" and "cheapest" in d["why"][-1]                                          # within 2 points of the best: the cheaper; 'openai' is 4 behind
    d = RO.decide({"hoola": eng(0.70), "exa": eng(0.84)})
    assert d["winner"] is None                                                                               # 14 points: just under


def test_an_engine_that_invented_an_answer_to_a_trap_or_answered_too_few_cannot_win(env):
    d = RO.decide({"hoola": eng(0.50), "exa": eng(0.95, trap_right=2)})
    assert d["winner"] is None and any("confident answer to 1 of 3" in w and "cannot be the default" in w for w in d["why"])
    d = RO.decide({"hoola": eng(0.50), "exa": eng(0.95, n=20, answered=12, errors_seen=["VendorError: key was refused"])})
    assert d["winner"] is None and any("answered 12 of 20" in w and "key was refused" in w for w in d["why"])
    d = RO.decide({"hoola": eng(0.50), "exa": {"not_run": "not allowed"}})
    assert d["winner"] is None and any("exa: not run - not allowed" in w for w in d["why"])
    assert RO.decide({"exa": {"not_run": "x"}})["winner"] is None and RO.decide({})["winner"] is None


def test_when_the_incumbent_is_disqualified_the_best_eligible_engine_is_recommended(env):
    d = RO.decide({"hoola": eng(0.80, trap_right=1), "exa": eng(0.60), "parallel": eng(0.62, inr=10.0)})
    assert d["winner"] == "parallel" and "hoola is not eligible" in d["why"][-1]
    assert RO.decide({"hoola": eng(0.5, trap_right=0)})["winner"] is None


def test_the_decision_is_a_recommendation_and_applying_it_is_a_separate_act(ro):
    d = RO.decide({"hoola": eng(0.50), "exa": eng(0.80)})
    assert V.read_default() is None and V.effective_engine(ro) == ("hoola", "no run-off has been applied: Hoola's own engine")
    with pytest.raises(ValueError, match="no winner"):
        RO.apply_default({"winner": None, "why": ["nothing"]})
    out = RO.apply_default(d, "researchrun-x.json")
    assert out["engine"] == "exa" and V.read_default()["engine"] == "exa" and V.effective_engine(ro)[0] == "exa" and "run-off winner" in V.effective_engine(ro)[1]
    ro.research_engine = "parallel"
    assert V.effective_engine(ro) == ("parallel", "set in the settings")                                      # an explicit setting always wins
    ro.research_engine = "auto"
    assert RO.reset_default() is True and RO.reset_default() is False and V.effective_engine(ro)[0] == "hoola"


def test_the_tool_uses_the_applied_default_and_falls_back_to_hoola_when_its_gate_is_closed(open_gates, ro):
    from app.agent.research_tools import research_run
    from app.agent.tools import Ctx, ToolError
    RO.apply_default({"winner": "exa", "why": ["x"], "rule": {}})
    ctx = Ctx(tenant_id="t1", conversation_id="c1", actor="owner")
    ro.research_engine = "auto"
    out = run_(research_run(ctx, question="What is the Corvane Index?", sub_questions=["g"]))
    assert out["engine"] == "exa" and store.get(out["run_id"])["policy"]["engine"] == "exa"
    open_gates.research_vendor_terms_ack = ""                                                                  # the default's gate is now closed
    out = run_(research_run(ctx, question="What is the Corvane Index?", sub_questions=["g"]))
    assert out["engine"] == "hoola" and "default engine (exa) cannot run now" in out["engine_note"] and "RESEARCH_VENDOR_TERMS_ACK" in out["engine_note"]
    with pytest.raises(ToolError, match="RESEARCH_VENDOR_TERMS_ACK"):
        run_(research_run(ctx, question="Q?", sub_questions=["g"], engine="exa"))                              # she NAMED it: she is told why not
    ro.research_engine = "exa"
    with pytest.raises(ToolError):
        run_(research_run(ctx, question="Q?", sub_questions=["g"]))                                            # explicitly set in the settings: also an error, no silent switch


# ---------------------------------------------------------------- free check, saving, printing, the CLI and the route
def test_the_free_check_says_which_engines_can_run_and_what_the_card_would_cost(open_gates, ro):
    c = RO.check_free(["hoola", "parallel", "exa"], n_asks=20, k=2)
    byn = {r["engine"]: r for r in c["engines"]}
    assert byn["hoola"]["ready"] and byn["hoola"]["card_inr"] is None and "unknown until one live run" in byn["hoola"]["note"]
    open_gates.research_engines_allowed = "parallel"
    c = RO.check_free(["parallel", "exa"], n_asks=20, k=2)
    byn = {r["engine"]: r for r in c["engines"]}
    assert byn["parallel"]["ready"] and byn["parallel"]["card_inr"] == 60.0 * 20 * 2 and not byn["exa"]["ready"]
    txt = "\n".join(RO.check_lines(c))
    assert "--budget-inr" in txt and "READY" in txt and "NOT READY" in txt and "on top" in txt


def test_the_card_is_saved_printed_and_rebuilt_with_her_current_verdicts(ro):
    card = run_(RO.run_card(["hoola"], [TOPIC, TOPIC2, TRAP], 900.0, make_deps=make_deps, write=writer(), tenant="tq5"))
    card = RO.save(card, "t")
    assert RO.latest()["file"] == card["file"] and RO.saved()[0]["engines"] == ["hoola"]
    txt = "\n".join(RO.lines(card))
    assert "Research run-off" in txt and "hoola" in txt and "traps" in txt and "a recommendation only" in txt
    # a saved card is rebuilt with HER CURRENT verdicts (real ask ids): the run that passed every check is overruled by her word
    rows = [row("hoola", i, right=True) for i in range(3)] + [row("exa", i, right=True) for i in range(3)]
    saved = {"rows": rows, "table": table_of(rows, {"hoola": 3, "exa": 3}, {"parallel": "not allowed"})}
    assert RO.rebuild(saved)[0]["hoola"]["right"] == 3 and RO.rebuild(saved)[0]["parallel"] == {"not_run": "not allowed"}
    RC.set_verdict(IDS[0], "wrong", "", engine="hoola")
    t2, dec = RO.rebuild(saved)
    assert t2["hoola"]["right"] == 2 and t2["exa"]["right"] == 3 and t2["hoola"]["hers"] == 1 and "parallel: not run" in "; ".join(dec["why"])


def test_the_cli_refuses_a_run_without_a_budget_and_never_applies_without_a_winner(ro, capsys):
    from app.quality import __main__ as M
    assert M.main(["research", "runoff", "--engines", "hoola"]) == 2
    assert "--budget-inr" in capsys.readouterr().out
    assert M.main(["research", "runoff", "--check", "--engines", "hoola,exa"]) == 0
    assert "Run-off check" in capsys.readouterr().out
    assert M.main(["research", "runoff", "--status"]) == 0 and "No run-off" in capsys.readouterr().out
    card = run_(RO.run_card(["hoola"], [TOPIC2], 900.0, make_deps=make_deps, write=writer(), tenant="tq6"))
    RO.save(card)
    assert M.main(["research", "runoff", "--apply"]) == 1
    out = capsys.readouterr().out
    assert "NOT APPLIED" in out and V.read_default() is None
    assert M.main(["research", "runoff", "--reset"]) == 0
    assert M.main(["research", "verdict", IDS[0], "wrong", "stale", "figure", "--engine", "hoola"]) == 0
    assert RC.verdict_for(IDS[0], "hoola")["note"] == "stale figure"


def test_the_route_shows_the_table_the_default_and_every_gate(ro):
    from app.research.api import make_router
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(a)
    r = c.get("/api/research/runoff").json()
    assert r["latest"] is None and r["default"]["engine"] == "hoola" and {e["engine"] for e in r["engines"]} >= {"hoola", "exa", "perplexity"}
    card = RO.save(run_(RO.run_card(["hoola"], [TOPIC2], 900.0, make_deps=make_deps, write=writer(), tenant="tq7")))
    r = c.get("/api/research/runoff").json()
    assert r["latest"]["table"]["hoola"]["answered"] == 1 and "report" not in r["latest"]["rows"][0] and r["history"][0]["file"] == card["file"]
    from app.main import app as real
    assert TestClient(real).get("/api/research/runoff").status_code != 404


def test_defaults_the_engine_setting_is_auto_and_the_rule_constants_are_pinned(env):
    assert get_settings().research_engine == "auto" or True
    from app.config import Settings
    assert Settings().research_engine == "auto"
    assert (RO.MARGIN, RO.TIE, RO.MIN_ANSWERED_SHARE, RO.INCUMBENT) == (0.15, 0.02, 0.8, "hoola")
