"""v0.473 R2 APNA ENGINE - the research loop, tested with NO model, NO network, NO clock.

Pinned: the url discipline (a link may be read only if it came from her ask, a search of this run, or the SAME site as a page
already admitted - never from another site's page), the source policy as data (blocked / allowed domains; a caller can lower a
budget, never raise it), that a note's words are checked against the page (a note whose words are not there is kept and marked
NOT VERIFIED, never silently trusted), the budgets (pages per goal / per run, calcs, steps, time), parallel workers + the
planner's more-or-stop round, that a failing worker or planner never kills the run, that the dossier says what it could not
confirm, the tool (owner only, the switch, in view only for a research ask), and the result is not cut at 6,000 characters.
"""
from __future__ import annotations

import asyncio
import json
import time

import pytest

from app.research import engine as E

PAGE_A = ("Test Authority of Nowhere - Quarterly Index. The Corvane Index stood at 412.5 in March 2025, up from 389.0 a year earlier. "
          "Output was 18,240 units across the period under review.")
PAGE_B = ("Corvane Trade Journal, 2 April 2025: analysts put the Corvane Index at 412.5 for March 2025. A second paragraph "
          "describes unrelated matters at some length so that this page is clearly longer than its excerpt.")
SEARCH = {"corvane index": [
    {"title": "Index", "url": "https://index.example.gov.in/corvane/2025", "excerpt": "The Corvane Index stood at 412.5 in March 2025"},
    {"title": "Journal", "url": "https://journal.example.com/corvane", "excerpt": "analysts put the Corvane Index at 412.5 for March 2025"},
    {"title": "Spam", "url": "https://spam.example.org/x", "excerpt": "buy now"}]}
PAGES = {"https://index.example.gov.in/corvane/2025": {"url": "https://index.example.gov.in/corvane/2025", "title": "Index", "text": PAGE_A,
                                                       "links": [("Annex", "https://index.example.gov.in/annex.html"),
                                                                 ("Elsewhere", "https://other.example.net/evil")]},
         "https://journal.example.com/corvane": {"url": "https://journal.example.com/corvane", "title": "Journal", "text": PAGE_B, "links": []},
         "https://index.example.gov.in/annex.html": {"url": "https://index.example.gov.in/annex.html", "title": "Annex", "text": "Annex table: 412.5", "links": []}}


def tu(i, name, **inp):
    return {"type": "tool_use", "id": i, "name": name, "input": inp}


class Script:
    """A scripted model: each worker (identified by its goal in the system text) plays its own list of tool calls in turn."""

    def __init__(self, plays, replan=None):
        self.plays, self.replan, self.n, self.systems = plays, replan, {}, []

    async def llm(self, system, history, tools, max_tokens):
        if "planner of Hoola's research engine" in system:
            self.systems.append("replan")
            if isinstance(self.replan, Exception):
                raise self.replan
            return [{"type": "text", "text": json.dumps(self.replan or {"action": "stop", "reasoning": "answered"})}], "end_turn"
        goal = next(g for g in self.plays if g in system)
        i = self.n.get(goal, 0)
        self.n[goal] = i + 1
        plan = self.plays[goal]
        if i >= len(plan):
            return [{"type": "text", "text": "done"}], "end_turn"
        item = plan[i]
        if isinstance(item, Exception):
            raise item
        return [tu(f"{goal[:4]}{i}", item[0], **item[1])], "tool_use"


def deps(script, calc=None, stopped=None, **kw):
    log = {"searches": [], "fetches": [], "calcs": [], "emits": []}

    async def search(goal, qs):
        log["searches"].append((goal, qs))
        return SEARCH.get(qs[0].lower(), [])

    async def fetch(url):
        log["fetches"].append(url)
        if url not in PAGES:
            raise RuntimeError("404")
        return dict(PAGES[url])

    async def calc_(code, purpose):
        log["calcs"].append(code)
        return {"ok": True, "output": "6.04"} if calc is None else calc(code)
    d = E.Deps(llm=script.llm, search=search, fetch=fetch, calc=calc_, stopped=stopped or (lambda: False),
               emit=lambda g, s, l: log["emits"].append((g, s)), **kw)
    return d, log


def run(goals, script, policy=None, **kw):
    d, log = deps(script, **kw)
    return asyncio.run(E.run("What is the Corvane Index?", goals, policy or E.Policy(), d)), log


GOOD_PLAY = [("search", {"queries": ["corvane index"]}),
             ("read", {"url": "https://index.example.gov.in/corvane/2025"}),
             ("note", {"claim": "The Corvane Index was 412.5 in March 2025", "url": "https://index.example.gov.in/corvane/2025",
                       "excerpt": "The Corvane Index stood at 412.5 in March 2025", "date": "March 2025"}),
             ("calc", {"code": "print((412.5-389.0)/389.0*100)", "purpose": "year-on-year growth"}),
             ("finish", {"summary": "412.5, up 6.04%", "unresolved": "baseline revision not checked"})]


def test_one_goal_end_to_end_makes_a_verified_note_a_calc_and_a_source(env):
    d, log = run(["Corvane value"], Script({"Corvane value": GOOD_PLAY}))
    t = d["tasks"][0]
    assert t["notes"][0]["verified"] and t["notes"][0]["n"] == 1 and t["calcs"][0]["output"] == "6.04"
    assert t["unresolved"] == "baseline revision not checked" and d["sources"][0]["primary_looking"] is True
    assert d["stats"]["verified_notes"] == 1 and d["stats"]["pages_read"] == 1 and d["stats"]["calcs"] == 1
    assert ("Corvane value", "running") in log["emits"] and ("Corvane value", "done") in log["emits"]
    text = E.render(d)
    assert "RESEARCH DOSSIER" in text and "[1] https://index.example.gov.in/corvane/2025" in text and "NOT CONFIRMED: baseline" in text


def test_a_link_that_never_came_from_ask_or_search_is_not_opened(env):
    play = [("read", {"url": "https://never.example.com/page"}), ("finish", {"summary": "x"})]
    d, log = run(["g"], Script({"g": play}))
    assert log["fetches"] == [] and d["stats"]["refused_reads"] == 1


def test_a_link_from_her_ask_is_hers_to_open(env):
    d, log = deps(Script({"g": [("read", {"url": "https://journal.example.com/corvane"}), ("finish", {"summary": "x"})]}))
    out = asyncio.run(E.run("Read https://journal.example.com/corvane", ["g"], E.Policy(), d,
                            asked_urls=["https://journal.example.com/corvane"]))
    assert log["fetches"] == ["https://journal.example.com/corvane"] and out["stats"]["pages_read"] == 1


def test_a_same_site_link_is_admitted_after_the_page_is_read_but_an_offsite_one_is_not(env):
    play = [("search", {"queries": ["corvane index"]}), ("read", {"url": "https://index.example.gov.in/corvane/2025"}),
            ("read", {"url": "https://index.example.gov.in/annex.html"}),
            ("read", {"url": "https://other.example.net/evil"}), ("finish", {"summary": "x"})]
    d, log = run(["g"], Script({"g": play}))
    assert "https://index.example.gov.in/annex.html" in log["fetches"] and "https://other.example.net/evil" not in log["fetches"]
    assert d["stats"]["refused_reads"] == 1


def test_the_source_policy_blocks_and_allows_by_domain_and_a_caller_can_only_lower_a_budget(env):
    pol = E.Policy(exclude_domains=["journal.example.com"])
    assert pol.allows("https://www.journal.example.com/x")[0] is False and pol.allows("https://index.example.gov.in/")[0]
    only = E.Policy(include_domains=["gov.in"])
    assert only.allows("https://index.example.gov.in/x")[0] and not only.allows("https://journal.example.com/x")[0]
    st = type("S", (), {"research_pages_total": 30, "research_calcs_max": 8})()
    low = E.Policy.from_settings(st, pages_total=10, calcs_total=100, include_domains=["GOV.in"], after_date="2025-01-01T00:00")
    assert low.pages_total == 10 and low.calcs_total == 8 and low.include_domains == ["gov.in"] and low.after_date == "2025-01-01"
    # a blocked site never reaches the worker, even when the search returned it
    d, log = run(["g"], Script({"g": [("search", {"queries": ["corvane index"]}), ("read", {"url": "https://journal.example.com/corvane"}),
                                      ("finish", {"summary": "x"})]}), E.Policy(exclude_domains=["journal.example.com"]))
    assert log["fetches"] == [] and d["stats"]["refused_reads"] == 1


def test_a_note_whose_words_are_not_on_the_page_is_kept_but_marked_not_verified(env):
    play = [("search", {"queries": ["corvane index"]}), ("read", {"url": "https://index.example.gov.in/corvane/2025"}),
            ("note", {"claim": "Output was 99,999 units", "url": "https://index.example.gov.in/corvane/2025",
                      "excerpt": "Output was 99,999 units in the period"}), ("finish", {"summary": "x"})]
    d, _ = run(["g"], Script({"g": play}))
    n = d["tasks"][0]["notes"][0]
    assert n["verified"] is False and d["stats"]["verified_notes"] == 0 and d["stats"]["notes"] == 1
    assert "NOT VERIFIED" in E.render(d)


def test_excerpt_check_handles_ellipsis_whitespace_case_and_too_short_words(env):
    assert E.excerpt_in("The Corvane   Index stood … up from 389.0", PAGE_A)
    assert E.excerpt_in("THE CORVANE INDEX STOOD AT 412.5", PAGE_A)
    assert not E.excerpt_in("The Corvane Index stood at 999.9", PAGE_A)
    assert not E.excerpt_in("412.5", PAGE_A)                 # too short to prove anything
    assert not E.excerpt_in("", PAGE_A)


def test_a_search_excerpt_can_back_a_note_when_the_page_was_not_read(env):
    play = [("search", {"queries": ["corvane index"]}),
            ("note", {"claim": "412.5", "url": "https://journal.example.com/corvane",
                      "excerpt": "analysts put the Corvane Index at 412.5 for March 2025"}), ("finish", {"summary": "x"})]
    d, _ = run(["g"], Script({"g": play}))
    assert d["tasks"][0]["notes"][0]["verified"] and d["sources"][0]["read"] is False
    assert "search excerpt only" in E.render(d)


def test_budgets_pages_per_goal_pages_per_run_calcs_and_steps(env):
    many = [("search", {"queries": ["corvane index"]}), ("read", {"url": "https://index.example.gov.in/corvane/2025"}),
            ("read", {"url": "https://journal.example.com/corvane"}), ("read", {"url": "https://index.example.gov.in/annex.html"})]
    d, log = run(["g"], Script({"g": many + [("finish", {"summary": "x"})]}), E.Policy(pages_per_task=2))
    assert len(log["fetches"]) == 2                                   # the third read was refused by the goal's budget
    d, log = run(["g"], Script({"g": many + [("finish", {"summary": "x"})]}), E.Policy(pages_total=1))
    assert len(log["fetches"]) == 1
    calcs = [("calc", {"code": f"print({i})", "purpose": "p"}) for i in range(4)] + [("finish", {"summary": "x"})]
    d, log = run(["g"], Script({"g": calcs}), E.Policy(calcs_total=2))
    assert len(log["calcs"]) == 2 and d["stats"]["calcs"] == 2
    d, _ = run(["g"], Script({"g": [("search", {"queries": ["corvane index"]})] * 20}), E.Policy(steps_per_task=3))
    assert d["tasks"][0]["steps"] == 3 and "without finishing" in d["tasks"][0]["unresolved"]


def test_a_failing_calc_is_a_result_the_worker_reads_not_a_crash(env):
    d, _ = run(["g"], Script({"g": [("calc", {"code": "1/0", "purpose": "p"}), ("finish", {"summary": "x"})]}),
               calc=lambda code: {"ok": False, "output": "ZeroDivisionError"})
    assert d["tasks"][0]["calcs"][0]["ok"] is False and "FAILED" in E.render(d)


def test_workers_run_in_parallel_and_the_planner_can_add_a_goal_then_stop(env):
    plays = {"g1": [("finish", {"summary": "a", "unresolved": "key figure missing"})], "g2": [("finish", {"summary": "b"})],
             "g3 follow-up": [("finish", {"summary": "c"})]}
    s = Script(plays, replan={"action": "tasks", "reasoning": "figure missing", "tasks": ["g3 follow-up", "g1"]})
    d, _ = run(["g1", "g2"], s)
    assert [t["goal"] for t in d["tasks"]] == ["g1", "g2", "g3 follow-up"]       # g1 was already done: not repeated
    assert [t["round"] for t in d["tasks"]] == [1, 1, 2] and d["stop_reason"] == "round limit"
    assert d["rounds"][0]["replan"]["action"] == "tasks"
    s = Script(plays, replan={"action": "stop", "reasoning": "answered"})
    d, _ = run(["g1", "g2"], s)
    assert len(d["tasks"]) == 2 and d["stop_reason"].startswith("planner stopped")


def test_workers_really_overlap(env):
    started = []

    async def slow_llm(system, history, tools, mt):
        goal = "a" if "YOUR GOAL: a" in system else "b"
        started.append((goal, time.time()))
        await asyncio.sleep(0.2)
        return [tu("x", "finish", summary="ok")], "tool_use"
    d_ = E.Deps(llm=slow_llm, search=None, fetch=None, calc=None)
    t0 = time.time()
    asyncio.run(E.run("q", ["a", "b"], E.Policy(rounds=1, parallel=2), d_))
    assert time.time() - t0 < 0.38 and len(started) == 2


def test_a_broken_worker_or_planner_never_kills_the_run(env):
    d, _ = run(["g1", "g2"], Script({"g1": [RuntimeError("model down")], "g2": [("finish", {"summary": "fine"})]},
                                    replan=RuntimeError("planner down")))
    bad = next(t for t in d["tasks"] if t["goal"] == "g1")
    assert "model down" in bad["error"] and bad["unresolved"] and d["tasks"][1]["summary"] == "fine"
    assert d["stop_reason"].startswith("planner stopped")


def test_stop_and_the_soft_clock_end_the_work_with_what_exists(env):
    d, _ = run(["g"], Script({"g": GOOD_PLAY}), stopped=lambda: True)
    assert d["tasks"][0]["steps"] == 0 and "ran out of time" in d["tasks"][0]["unresolved"] and d["stop_reason"] == "stopped by her"
    d, _ = run(["g"], Script({"g": GOOD_PLAY}), E.Policy(soft_s=0.0))
    assert d["tasks"][0]["steps"] == 0


def test_words_instead_of_a_tool_call_become_the_summary(env):
    class Talky(Script):
        async def llm(self, system, history, tools, mt):
            return [{"type": "text", "text": "I think the answer is fine."}], "end_turn"
    d, _ = run(["g"], Talky({}))
    assert d["tasks"][0]["summary"].startswith("I think")


# ---------------------------------------------------------------- the tool
def test_the_tool_is_owner_only_has_a_switch_and_is_in_view_only_for_research(env):
    from app.agent import admit, tools
    from app.agent.research_tools import research_run
    from app.agent.tools import Ctx, ToolError
    from app.config import get_settings
    st = get_settings()
    assert tools.FAMILY_OF["research_run"] == "research" and "research_run" in tools.HANDLERS
    names = lambda text: {t["name"] for t in admit.plan_for(text, st).specs()}      # noqa: E731
    assert "research_run" in names("Do deep research on the Indian EV two-wheeler market with sources")
    assert "research_run" in names("Research the cotton situation for Vidarbha farmers")
    assert "research_run" not in names("kal subah 7 baje jagana")
    with pytest.raises(ToolError):
        asyncio.run(research_run(Ctx(tenant_id="t", conversation_id="c", actor="customer:9"), question="q", sub_questions=["a"]))
    st.research_engine_on = False
    try:
        with pytest.raises(ToolError, match="band"):
            asyncio.run(research_run(Ctx(tenant_id="t", conversation_id="c", actor="owner"), question="q", sub_questions=["a"]))
    finally:
        st.research_engine_on = True
    with pytest.raises(ToolError):
        asyncio.run(research_run(Ctx(tenant_id="t", conversation_id="c", actor="owner")))


def test_the_tool_runs_the_engine_and_returns_the_dossier_with_an_honest_say(env, monkeypatch):
    from app.agent import research_tools as RT
    from app.agent.tools import Ctx
    script = Script({"g": GOOD_PLAY})
    d, _ = deps(script)
    monkeypatch.setattr(RT, "_deps", lambda ctx, st: d)
    out = asyncio.run(RT.research_run(Ctx(tenant_id="t", conversation_id="c", actor="owner"), question="What is it?",
                                      sub_questions=["g"], exclude_domains=["spam.example.org"], mode="inline"))
    assert "RESEARCH DOSSIER" in out["dossier"] and out["stats"]["verified_notes"] == 1 and "dossier only" in out["say"]
    empty = Script({"g": [("finish", {"summary": "nothing"})]})
    d2, _ = deps(empty)
    monkeypatch.setattr(RT, "_deps", lambda ctx, st: d2)
    out = asyncio.run(RT.research_run(Ctx(tenant_id="t", conversation_id="c", actor="owner"), question="q", sub_questions=["g"], mode="inline"))
    assert "no readable pages" in out["say"]


def test_the_dossier_is_not_cut_at_the_usual_six_thousand_characters(env):
    from app.agent import santosh
    assert santosh.RESULT_LIMIT["research_run"] >= 30000
    d, _ = run(["g"], Script({"g": GOOD_PLAY}))
    big = {"dossier": E.render(d) + ("\nfiller line of text" * 800), "stats": d["stats"]}
    s = santosh._short(big, santosh.RESULT_LIMIT["research_run"])
    assert "[1] https://index.example.gov.in/corvane/2025" in s and len(s) > 6000
    short = santosh._short(big)                                            # the default limit would have lost the source list
    assert "cut:" in short or "more characters cut" in short               # (v0.667: a long string is shortened in place)


def test_the_planner_prompt_formats_without_a_crash_so_it_can_really_ask_for_more(env):
    """The first run of the loop found the planner always answering 'stop': its prompt holds JSON braces and was run
    through str.format(), which raised and was swallowed. Pin the prompt itself."""
    s = E._REPLAN_SYSTEM.replace("{n}", "3")
    assert "At most 3 new goals" in s and '"action"' in s


def test_the_approved_plan_tells_the_model_to_call_the_engine(env):
    from app.agent import hard, research_plan as P
    blk = P.approved_block({"sub_questions": ["a?", "b?"], "look_in": ["x"], "as_of": "today"}, "also Pakistan")
    assert "research_run" in blk and "EXACTLY these sub-questions" in blk and "also Pakistan" in blk
    assert "research_run" in hard.RECIPE_KIND["research"]
