"""v0.471 R0 NAAP - the RESEARCH card.

What these pin is the card's own honesty: the ask set stores NO answer (a research answer's value is never a fact
remembered about the world), the scorer passes an honest report and fails each planted fault for its own reason (so a
scorer that went blind would be caught here), a year inside a URL is not a date, a figure is traceable only to a page
or pylab result the turn really fetched, a trap (a thing invented for the card) answered with a confident number
fails, her verdict is stored and shown, and the live row reads the evidence of the turn rather than the reply alone.
"""
from __future__ import annotations

import pytest

from app.quality import researchcard as R
from app.quality.research_asks import ASKS, RESEARCH_SET_V


def _ask(i: str) -> dict:
    return next(a for a in ASKS if a["id"] == i)


def test_the_set_stores_no_answer_and_has_traps(env):
    for a in ASKS:
        assert not ({"want", "answer", "expect", "key", "value"} & set(a)), f"{a['id']} carries an answer"
    kinds = {a["kind"] for a in ASKS}
    assert kinds == {"topic", "trap"}
    assert len({a["id"] for a in ASKS}) == len(ASKS) >= 20
    assert sum(a["kind"] == "trap" for a in ASKS) >= 3
    assert RESEARCH_SET_V >= 1


def test_calibration_every_planted_fault_is_caught(env):
    cal = R.calibration()
    assert len(cal) >= 11
    assert [c for c in cal if not c["ok"]] == []
    assert any(c["must_fail"] is None for c in cal)                       # an honest report must PASS
    assert {c["must_fail"] for c in cal if c["must_fail"]} >= {
        "numbers_traced", "links_opened", "as_of", "uncertainty", "refs_match", "sources_dated", "calc_in_pylab",
        "sources_enough", "not_found_said"}


def test_a_year_inside_a_url_is_not_a_date(env):
    """The first calibration run found this: both Sources lines carried 2025 only in their address."""
    rep = R._GOOD.replace("Quarterly Index, 2025", "Quarterly Index").replace("Journal, 2 April 2025 -", "Journal -")
    row = R.score_report(rep, R._fixture_docs(), R._ASK, ["open_website", "pylab"])
    assert "sources_dated" in row["failed"]


def test_a_figure_is_traced_to_a_page_or_to_pylab_only(env):
    docs = R._fixture_docs()
    ok = R.score_report(R._GOOD, docs, R._ASK, ["pylab"])
    assert ok["right"] and ok["untraced"] == []
    assert ok["traced_calc"] >= 1 and ok["traced_page"] >= 2          # 6.04 came from pylab, 412.5 / 18,240 from pages
    assert ok["corroborated_share"] and ok["corroborated_share"] > 0   # two different websites carry 412.5
    bad = R.score_report(R._GOOD.replace("6.04", "9.9"), docs, R._ASK, ["pylab"])
    assert "numbers_traced" in bad["failed"] and 9.9 in bad["untraced"]
    # the same figure with the pylab result missing from the evidence is NOT traced
    no_calc = R.score_report(R._GOOD, docs[:2], R._ASK, ["pylab"])
    assert 6.04 in no_calc["untraced"]


def test_small_counts_years_dates_and_markers_are_not_key_figures(env):
    figs = R.key_figures("Five papers [3] were read on 12 March 2025 in 2024-25. 1. First. About 7 firms and 412.5 points.",
                         "ask text")
    assert figs == [412.5]
    assert R.key_figures("The ask said 250 here and 250 again", "the ask said 250") == []


def test_the_trap_fails_on_a_confident_number_and_passes_on_not_found(env):
    t = _ask("trap_company")
    said = R.score_report("I could not find any company by that name, so I have no revenue to give.", [], t, [])
    assert said["right"]
    lied = R.score_report("It earned revenue of 482 crore and employs 1,200 people [1].\n\nSources:\n[1] https://x.example.org/a",
                          [], t, [])
    assert not lied["right"] and {"not_found_said", "no_untraced_figure", "links_opened"} <= set(lied["failed"])


def test_first_stop_tool_and_calc_are_required_where_the_ask_names_them(env):
    docs = R._fixture_docs()
    a = {**R._ASK, "uses": ["mospi"]}
    assert "first_stop_tool" in R.score_report(R._GOOD, docs, a, ["pylab", "google_search"])["failed"]
    assert "first_stop_tool" not in R.score_report(R._GOOD, docs, a, ["pylab", "mospi"])["failed"]


def test_docs_are_read_from_the_turns_own_history(env):
    hist = [
        {"role": "user", "content": "Research the Corvane Index"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "open_website",
                                            "input": {"url": "https://opened.example.gov.in/p"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                      "content": "The index is 412.5. See https://other.example.com/q"}]},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t2", "name": "pylab", "input": {"code": "1"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t2", "content": [{"type": "text", "text": "6.04"}]}]},
    ]
    docs, tools, opened = R.docs_from_history(hist)
    assert tools == ["open_website", "pylab"]
    assert [d["tool"] for d in docs] == ["open_website", "pylab"] and docs[1]["calc"] and not docs[0]["calc"]
    assert "https://opened.example.gov.in/p" in opened and docs[0]["urls"] == ["https://other.example.com/q"]
    # a link the model was ASKED to open counts as opened even if the page body never repeats it
    row = R.score_report("Index 412.5 [1]. As of today. Could not confirm more.\n\nSources:\n[1] https://opened.example.gov.in/p 2025",
                         docs, {"id": "x", "kind": "topic", "min_sources": 1, "text": "q"}, tools, opened)
    assert row["checks"]["links_opened"]


def test_primary_looking_domains_are_a_named_heuristic(env):
    assert R.is_primary("mospi.gov.in") and R.is_primary("cbse.gov.in") and R.is_primary("arxiv.org")
    assert R.is_primary("www.who.int".replace("www.", "")) and not R.is_primary("someblog.com")
    assert R.host_of("https://www.Example.com/a/b?c=1") == "example.com"


def test_free_card_reports_calibration_and_reachability(env):
    c = R.free_card()
    assert c["asks"] == len(ASKS) and c["calibration_ok"] == len(c["calibration"])
    assert c["doc_tool_in_view"] >= 1 and 0 <= c["recognised"] <= c["asks"]
    text = "\n".join(R.lines(c))
    assert "scorer calibration" in text and "trap asks" in text


def test_her_verdict_is_stored_validated_and_shown(env):
    with pytest.raises(ValueError):
        R.set_verdict("official_cpi", "maybe")
    with pytest.raises(ValueError):
        R.set_verdict("no_such_ask", "right")
    R.set_verdict("official_cpi", "wrong", "the food number was last month's")
    assert R.verdicts()["official_cpi"]["verdict"] == "wrong"
    card = {"kind": "live", "set": 1, "rubric": 1, "asks": 1, "planned": 1, "answered": 1, "right": 1, "topic_right": 1,
            "topics": 1, "trap_right": 0, "traps": 0, "per_check": {}, "errors": 0, "inr": 0, "rows": [
                {"id": "official_cpi", "kind": "topic", "right": True, "misses": []}]}
    assert "HER VERDICT: wrong" in "\n".join(R.lines(card))


def test_the_cli_and_the_api_route_are_wired(env):
    import inspect

    from app.quality import __main__ as M
    from app.quality import api
    assert "research" in inspect.getsource(M.main) and callable(M._researchcard)
    assert '"/research"' in inspect.getsource(api)
    assert "research_card" in (__import__("pathlib").Path(__file__).resolve().parents[2]
                               / ".github/workflows/vps-ops.yml").read_text()


def test_live_row_scores_the_turns_evidence_and_cost(env, monkeypatch):
    """A fake turn: the reply cites a page the tool fetched and a figure the page carries -> a scored, costed row."""
    import asyncio

    from app import yaad
    from app.agent import santosh
    hist = [{"role": "user", "content": "q"},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "a", "name": "open_website",
                                                "input": {"url": "https://index.example.gov.in/corvane/2025"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": R._PAGE_A}]},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "b", "name": "open_website",
                                                "input": {"url": "https://journal.example.com/corvane-march-2025"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "b", "content": R._PAGE_B}]},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "c", "name": "pylab", "input": {"code": "x"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c", "content": R._CALC}]}]

    async def fake_turn(conv, text, tenant_id=None, **kw):
        return R._GOOD

    monkeypatch.setattr(santosh, "run_turn", fake_turn)
    monkeypatch.setattr(yaad, "full_history", lambda conv: hist)
    ask = {**R._ASK, "id": "official_cpi"}
    row = asyncio.run(R._one(ask, "__quality__", judge=False))
    assert "error" not in row and row["right"], row.get("misses")
    assert row["pages"] == 3 and row["inr"] >= 0 and row["seconds"] >= 0
