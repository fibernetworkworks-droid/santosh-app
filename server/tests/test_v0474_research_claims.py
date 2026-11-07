"""v0.474 R3 SABOOT - a research report is built from FIELDS and checked against them before she sees it.

Pinned: a field's confidence is a RULE with printed reasons (high / medium / low / unconfirmed), a claim whose figure is not in its
own quoted words is LOW even when the quote is real, a derived figure backed by a calculation stands, corroboration by a different
website lifts a field, the report check catches each planted fault (a figure from memory, a figure cited to the wrong source, a figure
only an unverified note carries, a link that is not a source, hidden gaps) for its own reason and passes an honest report, the worker is
told when its claim's figure is not in its words, the check runs in the turn (and a broken check never blocks the answer), the R0 card
uses the same figure code and adds the claim check when the turn used the engine.
"""
from __future__ import annotations

import asyncio

import pytest

from app.research import claims as C
from app.research import engine as E
from app.research import figures as F
from tests.test_v0473_research_engine import GOOD_PLAY, PAGES, SEARCH, Script, deps, run, tu

PAGE_TWO = "Corvane Trade Journal, 2 April 2025: analysts put the Corvane Index at 412.5 for March 2025. A second paragraph pads this out."


def _dossier(plays=None, replan=None, **kw):
    d, _ = run(["Corvane value"], Script(plays or {"Corvane value": GOOD_PLAY}, replan))
    return d


def test_figure_helpers_are_shared_and_read_figures_the_indian_way(env):
    assert F.numbers("Rs 17,994.52 and 23.18 lakh and 1.5 crore") == [17994.52, 2318000.0, 15000000.0]
    assert F.key_figures("Index 412.5 up 6.04 percent in 2025 [1], 7 papers on 12 March 2025") == [412.5, 6.04]
    body, src = F.split_report("Body 412.5 [1]\n\nSources:\n[1] https://a.example.com 2025")
    assert "Body" in body and src == ["[1] https://a.example.com 2025"]
    from app.quality import researchcard as R
    assert R.key_figures("Index 412.5 up 6.04 percent in 2025 [1]") == F.key_figures("Index 412.5 up 6.04 percent in 2025 [1]")


def test_the_dossier_carries_fields_with_a_rule_based_confidence_and_reasons(env):
    d = _dossier()
    f = d["fields"][0]
    assert f["verified"] and f["supported"] and f["read"] and f["primary"] and f["dated"]
    assert f["confidence"] == "high" and "the site looks primary by its name" in f["why"] and "dated" in f["why"]
    assert d["stats"]["confidence"] == {"unconfirmed": 0, "low": 0, "medium": 0, "high": 1}
    assert d["tasks"][0]["notes"][0]["confidence"] == "high"
    assert "confidence: high" in E.render(d) and "Field confidence" in E.render(d)


def test_a_real_quote_whose_figure_is_not_in_it_is_low_not_trusted(env):
    play = [("search", {"queries": ["corvane index"]}), ("read", {"url": "https://index.example.gov.in/corvane/2025"}),
            ("note", {"claim": "The Corvane Index grew to 450.1", "url": "https://index.example.gov.in/corvane/2025",
                      "excerpt": "The Corvane Index stood at 412.5 in March 2025"}), ("finish", {"summary": "x"})]
    d = _dossier({"Corvane value": play})
    f = d["fields"][0]
    assert f["verified"] is True and f["supported"] is False and f["confidence"] == "low" and f["unsupported_figures"] == [450.1]
    assert "FIGURE NOT IN THE QUOTED WORDS" in E.render(d)


def test_a_derived_figure_stands_when_a_calculation_of_the_run_printed_it(env):
    play = [("search", {"queries": ["corvane index"]}), ("read", {"url": "https://index.example.gov.in/corvane/2025"}),
            ("calc", {"code": "print(6.04)", "purpose": "growth"}),
            ("note", {"claim": "The Corvane Index grew 6.04 percent in a year", "url": "https://index.example.gov.in/corvane/2025",
                      "excerpt": "The Corvane Index stood at 412.5 in March 2025, up from 389.0 a year earlier",
                      "date": "March 2025"}), ("finish", {"summary": "x"})]
    f = _dossier({"Corvane value": play})["fields"][0]
    assert f["supported"] and f["confidence"] == "high"


def test_unconfirmed_and_search_only_fields_get_their_confidence(env):
    play = [("search", {"queries": ["corvane index"]}),
            ("note", {"claim": "412.5", "url": "https://journal.example.com/corvane",
                      "excerpt": "analysts put the Corvane Index at 412.5 for March 2025"}),
            ("note", {"claim": "Output was 99,999 units", "url": "https://index.example.gov.in/corvane/2025",
                      "excerpt": "Output was 99,999 units in the whole period"}), ("finish", {"summary": "x"})]
    f1, f2 = _dossier({"Corvane value": play})["fields"]
    assert f1["confidence"] == "low" and "page itself was not read" in f1["why"][0]
    assert f2["confidence"] == "unconfirmed"


def test_two_different_websites_carrying_the_same_figure_lift_a_non_primary_field(env):
    play = [("search", {"queries": ["corvane index"]}), ("read", {"url": "https://index.example.gov.in/corvane/2025"}),
            ("read", {"url": "https://journal.example.com/corvane"}),
            ("note", {"claim": "Index 412.5 in March 2025", "url": "https://journal.example.com/corvane",
                      "excerpt": "analysts put the Corvane Index at 412.5 for March 2025"}),
            ("note", {"claim": "Index 412.5 in March 2025", "url": "https://index.example.gov.in/corvane/2025",
                      "excerpt": "The Corvane Index stood at 412.5 in March 2025"}), ("finish", {"summary": "x"})]
    j, g = _dossier({"Corvane value": play})["fields"]
    assert j["confidence"] == "high" and j["corroborated_by"] == ["index.example.gov.in"] and not j["primary"]
    assert g["corroborated_by"] == ["journal.example.com"]


HONEST = ("Summary: the Corvane Index was 412.5 in March 2025 [1], up 6.04 percent on a year earlier.\n\n"
          "What I could not confirm: whether the baseline was revised later.\n\n"
          "Sources:\n[1] Test Authority, 2025 - https://index.example.gov.in/corvane/2025\n")


def test_an_honest_report_passes_the_check(env):
    assert C.check_report(HONEST, _dossier()) == []


def test_a_figure_from_memory_is_caught(env):
    found = C.check_report(HONEST.replace("412.5", "999.9"), _dossier())
    assert found and "999.9" in found[0] and "memory" in found[0]


def test_a_figure_cited_to_the_wrong_source_is_caught(env):
    d = _dossier()
    d["sources"].append({"n": 2, "url": "https://journal.example.com/corvane", "host": "journal.example.com", "primary_looking": False, "read": True})
    found = C.check_report(HONEST.replace("412.5 in March 2025 [1]", "412.5 in March 2025 [2]"), d)
    assert found and "[2]" in found[0] and "[1]" in found[0] and "do not carry" in found[0]


def test_a_figure_only_an_unverified_or_unsupported_note_carries_is_caught(env):
    play = [("search", {"queries": ["corvane index"]}), ("read", {"url": "https://index.example.gov.in/corvane/2025"}),
            ("note", {"claim": "Output was 99,999 units", "url": "https://index.example.gov.in/corvane/2025",
                      "excerpt": "Output was 99,999 units in the whole period"}), ("finish", {"summary": "x", "unresolved": "output unclear"})]
    d = _dossier({"Corvane value": play})
    found = C.check_report("Output was 99,999 units [1]. What I could not confirm: the baseline.", d)
    assert found and "99999" in found[0] and "NOT VERIFIED" in found[0]


def test_a_figure_stated_as_unconfirmed_in_its_own_sentence_is_not_flagged_but_stated_as_fact_is(env):
    """v0.477: an honest report may name a figure only to say it could not be confirmed."""
    play = [("search", {"queries": ["corvane index"]}), ("read", {"url": "https://index.example.gov.in/corvane/2025"}),
            ("note", {"claim": "Output was 99,999 units", "url": "https://index.example.gov.in/corvane/2025",
                      "excerpt": "Output was 99,999 units in the whole period"}), ("finish", {"summary": "x", "unresolved": "output unclear"})]
    d = _dossier({"Corvane value": play})
    assert C.check_report("I could not confirm the figure of 99,999 units that one note gave.", d) == []
    found = C.check_report("Output was 99,999 units [1]. What I could not confirm: the baseline.", d)
    assert found and "99999" in found[0]


def test_a_link_that_is_not_a_source_of_this_run_is_caught(env):
    found = C.check_report(HONEST + "[2] https://made-up.example.org/page\n", _dossier())
    assert found and "made-up.example.org" in found[0]
    # a source of this run with a different scheme / www / trailing slash is still the same source
    assert C.check_report(HONEST.replace("https://index", "http://www.index") + "\n", _dossier()) == []


def test_hidden_gaps_are_caught_and_stating_them_passes(env):
    d = _dossier()                                                       # the worker listed an unresolved item
    no_gap = HONEST.replace("What I could not confirm: whether the baseline was revised later.\n\n", "")
    found = C.check_report(no_gap, d)
    assert found and "could NOT be confirmed" in found[-1]
    assert C.check_report(HONEST, d) == []


def test_a_calculation_the_run_printed_backs_the_figure_even_without_a_note(env):
    assert C.check_report("Growth was 6.04 percent. Not confirmed: the baseline.\n\nSources:\n[1] https://index.example.gov.in/corvane/2025",
                          _dossier()) == []


def test_no_dossier_or_an_empty_one_means_nothing_to_check_against(env):
    assert C.check_report("anything 123456", None) == [] and C.check_report("anything 123456", {}) == []


def test_findings_are_capped(env):
    rep = "Figures 111.1, 222.2, 333.3, 444.4, 555.5, 666.6, 777.7 appear. Not confirmed: x."
    assert 0 < len(C.check_report(rep, _dossier())) <= C.MAX_FINDINGS


def test_the_worker_is_told_when_its_claims_figure_is_not_in_its_words(env):
    got = {}

    class Spy(Script):
        async def llm(self, system, history, tools, mt):
            if self.n.get("g", 0) == 3:
                got["fb"] = history[-1]["content"][0]["content"]
            return await super().llm(system, history, tools, mt)
    play = [("search", {"queries": ["corvane index"]}), ("read", {"url": "https://index.example.gov.in/corvane/2025"}),
            ("note", {"claim": "The index grew to 450.1", "url": "https://index.example.gov.in/corvane/2025",
                      "excerpt": "The Corvane Index stood at 412.5 in March 2025"}), ("finish", {"summary": "x"})]
    d, _ = deps(Spy({"g": play}))
    asyncio.run(E.run("q", ["g"], E.Policy(rounds=1), d))
    assert "450.1" in got["fb"] and "calc" in got["fb"] and "LOW confidence" in got["fb"]
    assert E.STATS["figure_gaps"] >= 1


def test_the_run_is_remembered_per_conversation_and_bounded(env):
    d = _dossier()
    E.remember("conv-a", d)
    assert E.recall("conv-a") is d and E.recall("nope") is None
    for i in range(E.LAST_MAX + 5):
        E.remember(f"c{i}", d)
    assert len(E.LAST) <= E.LAST_MAX and E.recall("conv-a") is None


def test_the_tool_remembers_the_dossier_for_the_check(env, monkeypatch):
    from app.agent import research_tools as RT
    from app.agent.tools import Ctx
    d_, _ = deps(Script({"g": GOOD_PLAY}))
    monkeypatch.setattr(RT, "_deps", lambda ctx, st: d_)
    asyncio.run(RT.research_run(Ctx(tenant_id="t", conversation_id="conv-z", actor="owner"), question="q", sub_questions=["g"], mode="inline"))
    assert E.recall("conv-z")["fields"]


def test_the_turn_sends_a_report_with_a_made_up_figure_back_for_one_fix(env, monkeypatch):
    """_hard_check: research_run ran, the draft states a figure no note carries -> the problem list is the claim findings."""
    import app.agent.santosh as S
    d = _dossier()
    E.remember("conv-h", d)
    history = [{"role": "user", "content": "Do deep research on the Corvane Index"},
               {"role": "assistant", "content": [tu("a", "research_run", question="q", sub_questions=["g"])]},
               {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": "https://index.example.gov.in/corvane/2025"}]}]
    state = {"request": "Do deep research on the Corvane Index", "hard_why": {"why": ["research"]}}
    from app.config import get_settings
    bad = asyncio.run(S._hard_check("conv-h", state, HONEST.replace("412.5", "999.9"), history, get_settings()))
    assert bad and "999.9" in bad[0]
    ok = asyncio.run(S._hard_check("conv-h", dict(state), HONEST, history, get_settings()))
    assert not any("999.9" in x for x in ok)


def test_a_broken_claim_check_never_blocks_the_answer(env, monkeypatch):
    import app.agent.santosh as S
    from app.research import claims
    monkeypatch.setattr(claims, "check_report", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    E.remember("conv-b", _dossier())
    history = [{"role": "user", "content": "q"}, {"role": "assistant", "content": [tu("a", "research_run", question="q")]},
              {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": "https://index.example.gov.in/corvane/2025"}]}]
    from app.config import get_settings

    async def no_review(*a, **k):
        return []
    monkeypatch.setattr("app.agent.hard.review", no_review)
    assert asyncio.run(S._hard_check("conv-b", {"request": "q", "hard_why": {"why": ["research"]}}, HONEST, history, get_settings())) == []


def test_the_r0_card_adds_the_claim_check_only_when_the_turn_used_the_engine(env, monkeypatch):
    import app.agent.santosh as S
    from app import yaad
    from app.quality import researchcard as R
    hist = [{"role": "user", "content": "q"},
            {"role": "assistant", "content": [tu("a", "open_website", url="https://index.example.gov.in/corvane/2025")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": PAGES["https://index.example.gov.in/corvane/2025"]["text"]}]},
            {"role": "assistant", "content": [tu("b", "pylab", code="x")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "b", "content": "6.04"}]}]
    reply = HONEST
    captured = {}

    async def fake_turn(conv, text, tenant_id=None, **kw):
        captured["conv"] = conv
        return reply
    monkeypatch.setattr(S, "run_turn", fake_turn)
    monkeypatch.setattr(yaad, "full_history", lambda conv: hist)
    ask = {"id": "x", "kind": "topic", "min_sources": 1, "calc": False, "text": "Research the Corvane Index"}
    row = asyncio.run(R._one(ask, "__quality__", judge=False))
    assert "claims_supported" not in row["checks"]                       # no engine run in this conversation
    d = _dossier()
    orig = R._new_conv if hasattr(R, "_new_conv") else None
    from app.quality import run as RUN
    monkeypatch.setattr(RUN, "_new_conv", lambda tenant: (E.remember("conv-card", d), "conv-card")[1])
    row = asyncio.run(R._one(ask, "__quality__", judge=False))
    assert row["checks"]["claims_supported"] is True and row["field_confidence"]["high"] == 1
    E.remember("conv-card", _dossier())                                  # same dossier; now a reply with a made-up figure
    monkeypatch.setattr(S, "run_turn", lambda conv, text, tenant_id=None, **kw: asyncio.sleep(0, result=reply.replace("6.04", "77.7")))
    row = asyncio.run(R._one(ask, "__quality__", judge=False))
    assert row["checks"]["claims_supported"] is False and not row["right"] and "claims_supported" in row["failed"]
