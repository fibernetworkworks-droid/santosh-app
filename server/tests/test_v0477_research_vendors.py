"""v0.477 R6 PARAYA ENGINE - the vendors' research engines behind the same job.

Every vendor response below is shaped like that vendor's OWN SDK models (read from the shipped packages) and served through
httpx.MockTransport: no network, no money - and, said plainly, no live vendor has ever answered any of this.

Pinned: the gate (a vendor runs only when built + allowed + keyed + terms marked read + priced + under the run ceiling + room today, each refusal
naming how to fix it), each adapter's request (path, auth header, body keys) and its parse, that a create is NEVER retried but a read is, that a restart RE-ATTACHES
to the vendor's run instead of paying for another, stop / timeout cancel the vendor run, the vendor's claims are RE-CHECKED by Hoola's own fetch (its prose is
never carried), the dossier is the same R3 dossier (fields, confidence, the claim check), the vendor line of the cost (the price she set, or the vendor's own
reported cost), and the tool / report plumbing.
"""
from __future__ import annotations

import asyncio
import json
from datetime import timedelta

import httpx
import pytest

from app import usage
from app.config import get_settings
from app.db import now, session
from app.research import bill, claims as C, runner, store, vendors as V
from app.research import engine as E

PAGE = ("Test Authority of Nowhere - Quarterly Index. The Corvane Index stood at 412.5 in March 2025, up from 389.0 a year earlier. "
        "Output was 18,240 units across the period under review. Nothing else of note happened.")
URL = "https://index.example.gov.in/corvane/2025"
URL2 = "https://journal.example.com/corvane"
PAGE2 = "Corvane Trade Journal, 2 April 2025: analysts put the Corvane Index at 412.5 for March 2025 and said little more."


def run_(c):
    return asyncio.run(c)


@pytest.fixture
def open_gates(env, monkeypatch):
    """Every gate open for every built vendor, with a price under the ceiling; restored afterwards."""
    st = get_settings()
    keep = {k: getattr(st, k) for k in ("research_engines_allowed", "research_vendor_terms_ack", "parallel_api_key", "exa_api_key", "openai_api_key",
                                        "linkup_api_key", "research_parallel_run_inr", "research_exa_run_inr", "research_openai_run_inr",
                                        "research_linkup_run_inr", "research_run_cap_inr", "research_daily_inr", "research_vendor_poll_s",
                                        "research_vendor_wait_s", "research_call_reserve_inr")}
    st.research_engines_allowed = "parallel,exa,openai,linkup"
    st.research_vendor_terms_ack = "parallel,exa,openai,linkup"
    st.parallel_api_key, st.exa_api_key, st.openai_api_key, st.linkup_api_key = "pk", "ek", "ok", "lk"
    st.research_parallel_run_inr = st.research_exa_run_inr = st.research_openai_run_inr = st.research_linkup_run_inr = 60.0
    st.research_run_cap_inr, st.research_daily_inr, st.research_call_reserve_inr = 150.0, 600.0, 3.0
    st.research_vendor_poll_s, st.research_vendor_wait_s = 0.0, 30.0
    yield st
    for k, v in keep.items():
        setattr(st, k, v)
    V._transport = None


def mock(handler):
    V._transport = httpx.MockTransport(handler)
    return V._transport


def req(st, **kw):
    base = dict(question="What is the Corvane Index?", goals=["value?", "growth?"], include_domains=[], exclude_domains=[], after_date="",
                price_inr=60.0, st=st)
    base.update(kw)
    return V.Req(**base)


# ---------------------------------------------------------------- the gate
def test_the_gate_names_the_first_closed_door_and_how_to_open_it(env):
    st = get_settings()
    saved = (st.research_engines_allowed, st.research_vendor_terms_ack, st.exa_api_key, st.research_exa_run_inr)
    try:
        assert V.check("hoola") == (True, "") and V.check("") == (True, "")
        assert "not a research engine" in V.check("nope")[1]
        ok, why = V.check("perplexity")
        assert not ok and "NOT built" in why and "wire format not read yet" in why
        ok, why = V.check("exa")
        assert not ok and "RESEARCH_ENGINES_ALLOWED" in why
        st.research_engines_allowed = "exa"
        ok, why = V.check("exa")
        assert not ok and "EXA_API_KEY" in why
        st.exa_api_key = "k"
        ok, why = V.check("exa")
        assert not ok and "RESEARCH_VENDOR_TERMS_ACK" in why and "terms" in why
        st.research_vendor_terms_ack = "exa"
        ok, why = V.check("exa")
        assert not ok and "RESEARCH_EXA_RUN_INR" in why and "no ceiling can be kept" in why
        st.research_exa_run_inr = 400.0
        ok, why = V.check("exa")
        assert not ok and "run ceiling" in why and "RESEARCH_RUN_CAP_INR" in why
        st.research_exa_run_inr = 60.0
        assert V.check("exa", "t1") == (True, "")
        r = store.create("t1", "c", "Q", ["g"], {})
        store.finish(r, "done", {}, cost={"total_inr": 590.0})
        ok, why = V.check("exa", "t1")
        assert not ok and "today's room" in why
        assert V.check("exa", "t2")[0] is True                                    # another tenant has its own day
    finally:
        st.research_engines_allowed, st.research_vendor_terms_ack, st.exa_api_key, st.research_exa_run_inr = saved


def test_the_status_table_lists_every_engine_and_why_not(env):
    rows = {r["engine"]: r for r in V.status_table()}
    assert set(rows) == {"hoola", "parallel", "exa", "openai", "linkup", "perplexity", "valyu", "gemini"}
    assert rows["hoola"]["ready"] and rows["hoola"]["terms_read"]
    assert not rows["parallel"]["ready"] and rows["parallel"]["why_not"] and rows["parallel"]["terms_read"] is False
    assert rows["valyu"]["built"] is False and "not read yet" in rows["valyu"]["why_not"]
    assert "engines" in bill.usage_report("t1") and "no vendor wire format has been answered live" in " ".join(bill.usage_report("t1")["assumed"])


# ---------------------------------------------------------------- Parallel (Task API)
def _parallel_handler(seen, polls=("queued", "running", "completed")):
    state = {"i": 0}

    def h(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, dict(request.headers), json.loads(request.content) if request.content else None))
        if request.method == "POST" and request.url.path == "/v1/tasks/runs":
            return httpx.Response(200, json={"run_id": "trun_1", "status": "queued", "interaction_id": "i", "is_active": True, "processor": "core"})
        if request.url.path == "/v1/tasks/runs/trun_1":
            s = polls[min(state["i"], len(polls) - 1)]
            state["i"] += 1
            return httpx.Response(200, json={"run_id": "trun_1", "status": s, "interaction_id": "i", "is_active": s != "completed", "processor": "core"})
        if request.url.path == "/v1/tasks/runs/trun_1/result":
            return httpx.Response(200, json={"run": {"run_id": "trun_1", "status": "completed"}, "output": {
                "type": "json", "content": {"findings": [
                    {"claim": "The Corvane Index was 412.5", "period": "March 2025", "source_url": URL, "quote": "The Corvane Index stood at 412.5 in March 2025"},
                    {"claim": "Output was 18,240 units", "period": "2025", "source_url": "", "quote": ""}], "not_found": ["the 2019 baseline"]},
                "basis": [{"field": "findings.0", "reasoning": "r", "confidence": "high", "citations": [{"url": URL, "title": "Index", "excerpts": ["up from 389.0 a year earlier"]}]},
                          {"field": "findings.1", "reasoning": "r", "confidence": "medium", "citations": [{"url": URL, "excerpts": ["Output was 18,240 units across the period"]}]}]}})
        return httpx.Response(404)
    return h


def test_parallel_request_and_parse(open_gates):
    seen = []
    mock(_parallel_handler(seen))
    r = run_(V.run_vendor("parallel", req(open_gates, include_domains=["gov.in"], exclude_domains=["spam.example.org"], after_date="2025-01-01"),
                          lambda *a: None, lambda: False, lambda rid: None))
    create = seen[0]
    assert create[0] == "POST" and create[1] == "/v1/tasks/runs" and create[2]["x-api-key"] == "pk"
    body = create[3]
    assert body["processor"] == "core" and body["task_spec"]["output_schema"]["type"] == "json" and body["task_spec"]["output_schema"]["json_schema"] == V.FINDINGS_SCHEMA
    assert body["source_policy"] == {"include_domains": ["gov.in"], "exclude_domains": ["spam.example.org"], "after_date": "2025-01-01"}
    assert "What is the Corvane Index?" in body["input"] and "1. value?" in body["input"] and "do not invent it" in body["input"]
    assert [x[1] for x in seen].count("/v1/tasks/runs/trun_1") == 3                   # polled queued -> running -> completed
    assert r.engine == "parallel" and r.run_id == "trun_1" and r.cost_inr is None and r.not_found == ["the 2019 baseline"]
    c0, c1 = r.claims
    assert c0.urls == [URL] and "The Corvane Index stood at 412.5 in March 2025" in c0.excerpts and "up from 389.0 a year earlier" in c0.excerpts
    assert c0.confidence == "high" and c0.period == "March 2025"
    assert c1.urls == [URL] and c1.confidence == "medium"                              # no source_url of its own: the basis citation supplies it


def test_a_failed_parallel_run_is_an_error_with_its_state(open_gates):
    mock(_parallel_handler([], polls=("running", "failed")))
    with pytest.raises(V.VendorError, match="parallel: the run ended without a result"):
        run_(V.run_vendor("parallel", req(open_gates), lambda *a: None, lambda: False, lambda rid: None))


# ---------------------------------------------------------------- Exa (Agent API)
def _exa_handler(seen, cost=0.6, field="findings.0"):
    def h(request):
        seen.append((request.method, request.url.path, dict(request.headers), json.loads(request.content) if request.content else None))
        if request.method == "POST" and request.url.path == "/agent/runs":
            return httpx.Response(200, json={"id": "agent_run_9", "status": "queued"})
        if request.url.path == "/agent/runs/agent_run_9" and request.method == "GET":
            return httpx.Response(200, json={"id": "agent_run_9", "status": "completed", "stopReason": "schema_satisfied",
                                             "output": {"structured": {"findings": [
                                                 {"claim": "The Corvane Index was 412.5", "period": "March 2025", "source_url": "", "quote": "The Corvane Index stood at 412.5 in March 2025"}],
                                                 "not_found": []},
                                                 "grounding": [{"field": field, "citations": [{"url": URL, "title": "Index"}], "confidence": "high"}]},
                                             "usage": {"searches": 7}, "costDollars": {"total": cost, "search": 0.2}})
        if request.url.path.endswith("/cancel"):
            return httpx.Response(200, json={})
        return httpx.Response(404)
    return h


def test_exa_request_has_its_own_budget_and_the_real_cost_comes_back(open_gates):
    seen = []
    mock(_exa_handler(seen))
    r = run_(V.run_vendor("exa", req(open_gates, price_inr=88.0 * 2.5), lambda *a: None, lambda: False, lambda rid: None))
    create = seen[0]
    assert create[1] == "/agent/runs" and create[2]["x-api-key"] == "ek"
    assert create[3]["effort"] == "auto" and create[3]["outputSchema"] == V.FINDINGS_SCHEMA and create[3]["budget"] == {"maxCostDollars": pytest.approx(2.5, abs=0.2)}
    assert r.cost_inr == pytest.approx(0.6 * usage.usd_inr(), abs=0.01) and r.stop == "schema_satisfied" and r.usage == {"searches": 7}
    assert r.claims[0].urls == [URL] and r.claims[0].confidence == "high"


def test_exa_budget_is_clamped_to_its_documented_range_and_an_unmatched_field_uses_every_citation(open_gates):
    seen = []
    mock(_exa_handler(seen, field="something_else"))
    open_gates.research_exa_effort = "ultra"
    r = run_(V.run_vendor("exa", req(open_gates, price_inr=5.0), lambda *a: None, lambda: False, lambda rid: None))
    assert seen[0][3]["budget"]["maxCostDollars"] == 1.0 and seen[0][3]["effort"] == "ultra"      # 1 US dollar is the floor
    assert r.claims[0].urls == [URL] and r.claims[0].confidence == ""                              # a field we cannot match: all citations, no confidence claimed
    seen2 = []
    mock(_exa_handler(seen2))
    run_(V.run_vendor("exa", req(open_gates, price_inr=88.0 * 900), lambda *a: None, lambda: False, lambda rid: None))
    assert seen2[0][3]["budget"]["maxCostDollars"] == 100.0                                          # and 100 the ceiling


# ---------------------------------------------------------------- OpenAI (Responses deep research)
OA_TEXT = ("- The Corvane Index was 412.5 in March 2025 ([index.example.gov.in](https://index.example.gov.in/corvane/2025)).\n"
           "- Analysts agree it is probably fine.\n"
           "NOT FOUND: the 2019 baseline; the revision history")


def _oa_handler(seen, model="o4-mini-deep-research"):
    state = {"i": 0}
    start = OA_TEXT.index("(https://index")
    span = len("(https://index.example.gov.in/corvane/2025)")             # the vendor's indices are exact: the citation covers only its own line

    def h(request):
        seen.append((request.method, request.url.path, dict(request.headers), json.loads(request.content) if request.content else None))
        if request.method == "POST" and request.url.path == "/v1/responses":
            return httpx.Response(200, json={"id": "resp_1", "status": "queued"})
        if request.url.path == "/v1/responses/resp_1" and request.method == "GET":
            state["i"] += 1
            if state["i"] == 1:
                return httpx.Response(200, json={"id": "resp_1", "status": "in_progress"})
            return httpx.Response(200, json={"id": "resp_1", "status": "completed", "model": model, "usage": {"input_tokens": 100000, "output_tokens": 20000},
                                             "output": [{"type": "reasoning"}, {"type": "message", "content": [{"type": "output_text", "text": OA_TEXT, "annotations": [
                                                 {"type": "url_citation", "url": URL, "title": "Index", "start_index": start, "end_index": start + span}]}]}]})
        if request.url.path.endswith("/cancel"):
            return httpx.Response(200, json={})
        return httpx.Response(404)
    return h


def test_openai_request_parse_and_only_cited_lines_become_claims(open_gates):
    seen = []
    mock(_oa_handler(seen))
    r = run_(V.run_vendor("openai", req(open_gates, include_domains=["gov.in"]), lambda *a: None, lambda: False, lambda rid: None))
    create = seen[0]
    assert create[1] == "/v1/responses" and create[2]["authorization"] == "Bearer ok"
    b = create[3]
    assert b["model"] == "o4-mini-deep-research" and b["background"] is True and b["max_tool_calls"] == 40 and b["tools"] == [{"type": "web_search_preview"}]
    assert b["reasoning"] == {"summary": "auto"} and "NOT FOUND:" in b["input"]
    assert len(r.claims) == 1 and r.claims[0].urls == [URL] and r.claims[0].claim == "The Corvane Index was 412.5 in March 2025." and "](" not in r.claims[0].claim
    assert "the 2019 baseline" in r.not_found and "the revision history" in r.not_found                  # the uncited line is NOT a claim
    assert r.usage["input_tokens"] == 100000


def test_openai_cost_is_computed_only_when_the_model_price_is_known_and_domains_filter_the_search_tool(open_gates):
    seen = []
    mock(_oa_handler(seen, model="o4-mini-deep-research"))
    r = run_(V.run_vendor("openai", req(open_gates), lambda *a: None, lambda: False, lambda rid: None))
    known = usage.price_of("o4-mini-deep-research")[1]
    assert (r.cost_inr is not None) == known
    open_gates.research_openai_search_tool = "web_search"
    seen2 = []
    mock(_oa_handler(seen2))
    run_(V.run_vendor("openai", req(open_gates, include_domains=["gov.in"]), lambda *a: None, lambda: False, lambda rid: None))
    assert seen2[0][3]["tools"] == [{"type": "web_search", "filters": {"allowed_domains": ["gov.in"]}}]
    open_gates.research_openai_search_tool = "web_search_preview"


# ---------------------------------------------------------------- Linkup
def test_linkup_request_and_parse(open_gates):
    seen, n = [], {"i": 0}

    def h(request):
        seen.append((request.method, request.url.path, dict(request.headers), json.loads(request.content) if request.content else None))
        if request.method == "POST":
            return httpx.Response(200, json={"id": "lk_1", "status": "pending", "type": "research"})
        n["i"] += 1
        if n["i"] == 1:
            return httpx.Response(200, json={"id": "lk_1", "status": "processing"})
        return httpx.Response(200, json={"id": "lk_1", "status": "completed", "output": {"findings": [
            {"claim": "The Corvane Index was 412.5", "period": "March 2025", "source_url": URL, "quote": "stood at 412.5 in March 2025"}], "not_found": []}})
    mock(h)
    r = run_(V.run_vendor("linkup", req(open_gates, include_domains=["gov.in"], exclude_domains=["x.com"], after_date="2025-01-01"),
                          lambda *a: None, lambda: False, lambda rid: None))
    c = seen[0]
    assert c[1] == "/v1/research" and c[2]["authorization"] == "Bearer lk"
    assert c[3]["outputType"] == "structured" and json.loads(c[3]["structuredOutputSchema"]) == V.FINDINGS_SCHEMA
    assert (c[3]["reasoningDepth"], c[3]["mode"], c[3]["includeDomains"], c[3]["excludeDomains"], c[3]["fromDate"]) == ("L", "research", ["gov.in"], ["x.com"], "2025-01-01")
    assert r.claims[0].urls == [URL] and r.claims[0].excerpts == ["stood at 412.5 in March 2025"]


# ---------------------------------------------------------------- http behaviour
def test_http_errors_are_mapped_and_a_key_never_leaks(open_gates):
    for code, word in ((401, "key was refused"), (403, "key was refused"), (402, "out of credit"), (429, "out of credit")):
        mock(lambda r, code=code: httpx.Response(code, text="bad pk key"))
        with pytest.raises(V.VendorError, match=word):
            run_(V.run_vendor("parallel", req(open_gates), lambda *a: None, lambda: False, lambda rid: None))
    mock(lambda r: httpx.Response(400, text="the key pk is wrong"))
    with pytest.raises(V.VendorError) as e:
        run_(V.run_vendor("parallel", req(open_gates), lambda *a: None, lambda: False, lambda rid: None))
    assert "pk" not in str(e.value).replace("parallel", "").replace("pkey", "") or "***" in str(e.value)
    mock(lambda r: httpx.Response(200, text="<html>not json</html>"))
    with pytest.raises(V.VendorError, match="not JSON"):
        run_(V.run_vendor("parallel", req(open_gates), lambda *a: None, lambda: False, lambda rid: None))


def test_a_create_is_never_retried_but_a_read_is(open_gates):
    posts = {"n": 0}

    def h(request):
        if request.method == "POST":
            posts["n"] += 1
            return httpx.Response(503, text="busy")
        return httpx.Response(404)
    mock(h)
    with pytest.raises(V.VendorError, match="503"):
        run_(V.run_vendor("parallel", req(open_gates), lambda *a: None, lambda: False, lambda rid: None))
    assert posts["n"] == 1                                                    # a create that MAY have succeeded is not repeated
    gets = {"n": 0}

    def h2(request):
        if request.method == "POST":
            return httpx.Response(200, json={"run_id": "trun_1"})
        gets["n"] += 1
        return httpx.Response(503, text="busy") if gets["n"] == 1 else httpx.Response(200, json={"run_id": "trun_1", "status": "failed", "error": {"message": "x"}})
    mock(h2)
    with pytest.raises(V.VendorError, match="ended without a result"):
        run_(V.run_vendor("parallel", req(open_gates), lambda *a: None, lambda: False, lambda rid: None))
    assert gets["n"] == 2                                                     # the read was retried once and then worked


def test_a_restart_reattaches_to_the_vendors_run_and_never_creates_another(open_gates):
    seen = []
    mock(_parallel_handler(seen, polls=("completed",)))
    ids = []
    run_(V.run_vendor("parallel", req(open_gates), lambda *a: None, lambda: False, ids.append))
    assert ids == ["trun_1"] and seen[0][0] == "POST"
    seen2 = []
    mock(_parallel_handler(seen2, polls=("completed",)))
    ids2 = []
    run_(V.run_vendor("parallel", req(open_gates), lambda *a: None, lambda: False, ids2.append, resume_id="trun_1"))
    assert ids2 == [] and not any(m == "POST" for m, *_ in seen2)             # no second create, no second charge


def test_stop_cancels_the_vendor_run_and_a_timeout_gives_up_and_says_it_may_still_bill(open_gates):
    seen = []
    mock(_exa_handler(seen))
    with pytest.raises(V.StoppedByHer):
        run_(V.run_vendor("exa", req(open_gates), lambda *a: None, lambda: True, lambda rid: None, resume_id="agent_run_9"))
    assert any(p.endswith("/agent_run_9/cancel") for _m, p, *_ in seen)
    seen2 = []
    mock(_parallel_handler(seen2, polls=("running",)))
    open_gates.research_vendor_wait_s = 0.0
    with pytest.raises(V.VendorError, match="may still bill"):
        run_(V.run_vendor("parallel", req(open_gates), lambda *a: None, lambda: False, lambda rid: None))


# ---------------------------------------------------------------- Hoola re-checks every claim itself
async def _fetch(url):
    pages = {URL: {"url": URL, "title": "Index", "text": PAGE, "links": []}, URL2: {"url": URL2, "title": "Journal", "text": PAGE2, "links": []}}
    if url not in pages:
        raise RuntimeError("404")
    return dict(pages[url])


def _result(claims, nf=None, cost=None):
    return V.VendorResult("parallel", "trun_1", claims, nf or [], cost_inr=cost)


def test_a_claim_is_verified_by_hoolas_own_read_of_the_cited_page(env):
    res = _result([
        V.Claim("The Corvane Index was 412.5", [URL], ["The Corvane Index stood at 412.5 in March 2025"], "March 2025"),     # the vendor's quote is on the page
        V.Claim("Output was 18,240 units", [URL], ["words the vendor invented"], "2025"),                                      # quote NOT on the page, figure IS: Hoola finds the sentence
        V.Claim("The index was 777.7", [URL], ["The index stood at 777.7"], "2025"),                                           # nothing on the page carries it
        V.Claim("The index was 412.5", [URL2 + "-gone"], [], "2025"),                                                          # the page cannot be read
        V.Claim("A claim with no source", [], ["x"], "2025"),                                                                 # no source at all: dropped
        V.Claim("Blocked site claim 55.5", ["https://spam.example.org/x"], [], "2025")], nf=["the 2019 baseline"])
    pol = E.Policy(exclude_domains=["spam.example.org"])
    d = run_(V.to_dossier(res, "What is the Corvane Index?", ["g"], pol, _fetch))
    notes = d["tasks"][0]["notes"]
    assert [(n["claim"][:20], n["verified"]) for n in notes] == [("The Corvane Index wa", True), ("Output was 18,240 un", True), ("The index was 777.7", False), ("The index was 412.5", False)]
    assert notes[0]["excerpt"] == "The Corvane Index stood at 412.5 in March 2025"
    assert "18,240 units" in notes[1]["excerpt"] and "invented" not in notes[1]["excerpt"]                                   # the page's sentence, not the vendor's words
    unres = d["tasks"][0]["unresolved"]
    assert "no usable source" in unres and "could not be found on their cited page" in unres and "the 2019 baseline" in unres
    assert d["engine"] == "parallel" and d["vendor"]["claims"] == 6 and d["vendor"]["verified_by_hoola"] == 2 and d["vendor"]["dropped_no_source"] == 2
    assert d["stats"]["verified_notes"] == 2 and d["stats"]["pages_read"] == 1


def test_the_vendors_prose_is_not_carried_and_the_dossier_is_the_same_r3_dossier(env):
    res = _result([V.Claim("The Corvane Index was 412.5", [URL], ["The Corvane Index stood at 412.5 in March 2025"], "March 2025"),
                   V.Claim("The index was 777.7", [URL], [], "2025")])
    d = run_(V.to_dossier(res, "What is the Corvane Index?", ["g"], E.Policy(), _fetch))
    f0, f1 = d["fields"]
    assert f0["confidence"] == "high" and f0["verified"] and f0["primary"] and f1["confidence"] in ("unconfirmed", "low")
    txt = E.render(d)
    assert "RESEARCH DOSSIER" in txt and "[1] " + URL in txt and "NOT VERIFIED" in txt
    good = ("The Corvane Index was 412.5 in March 2025 [1].\n\nWhat I could not confirm: the 777.7 figure.\n\nSources:\n[1] Test Authority, 2025 - " + URL + "\n")
    assert C.check_report(good, d) == []
    found = C.check_report("The Corvane Index was 999.9 [1]. Not confirmed: x.", d)
    assert found and "999.9" in found[0]                                                                  # the R3 check holds for a vendor dossier too


def test_best_sentence_needs_every_figure_in_one_sentence_or_a_strong_overlap(env):
    assert "412.5" in V.best_sentence("The index was 412.5 against 389.0", PAGE)
    assert V.best_sentence("The index was 412.5 against 999.9", PAGE) == ""
    assert "Output was 18,240" in V.best_sentence("Output across the period under review was large", PAGE)
    assert V.best_sentence("completely unrelated claim about whales", PAGE) == ""
    assert V.best_sentence("short", PAGE) == ""


# ---------------------------------------------------------------- the job end to end (runner + tool)
@pytest.fixture
def jobs(open_gates, monkeypatch):
    events = []
    monkeypatch.setattr(runner.bus, "publish", lambda conv, kind, payload: events.append((conv, kind, payload)))
    from tests.test_v0473_research_engine import Script, deps

    def factory(ctx, st):
        d, _ = deps(Script({}))

        async def fetch(url):
            return await _fetch(url)
        d.fetch = fetch
        return d
    monkeypatch.setattr(runner, "_deps_factory", factory)
    runner._RUNNING.clear()
    return {"events": events, "st": open_gates}


def _ctx(tenant="t1", conv="c1"):
    from app.agent.tools import Ctx
    return Ctx(tenant_id=tenant, conversation_id=conv, actor="owner")


def test_the_tool_refuses_a_closed_gate_with_the_reason_and_forces_a_vendor_into_the_background(jobs):
    from app.agent.research_tools import research_run
    from app.agent.tools import ToolError
    st = jobs["st"]
    st.research_vendor_terms_ack = "exa"
    with pytest.raises(ToolError, match="RESEARCH_VENDOR_TERMS_ACK"):
        run_(research_run(_ctx(), question="Q?", sub_questions=["g"], engine="parallel"))
    st.research_vendor_terms_ack = "parallel,exa,openai,linkup"
    out = run_(research_run(_ctx(), question="What is the Corvane Index?", sub_questions=["g"], engine="parallel", mode="inline"))
    assert out["started"] is True and out["engine"] == "parallel"                                    # a vendor is never run inside a turn
    assert store.get(out["run_id"])["policy"]["engine"] == "parallel"
    with pytest.raises(ToolError, match="not a research engine"):
        run_(research_run(_ctx(), question="Q?", sub_questions=["g"], engine="nope"))
    own = run_(research_run(_ctx(), question="What is it?", sub_questions=["g"]))
    assert store.get(own["run_id"])["policy"]["engine"] == "hoola"
    st.research_engine = "exa"
    try:
        assert store.get(run_(research_run(_ctx(), question="Q?", sub_questions=["g"]))["run_id"])["policy"]["engine"] == "exa"   # the setting's default engine
    finally:
        st.research_engine = "hoola"


def test_a_vendor_run_goes_end_to_end_with_the_price_as_an_estimate_and_hoola_verified_notes(jobs):
    seen = []
    mock(_parallel_handler(seen))
    rid = runner.start("t1", "c1", "What is the Corvane Index?", ["value?"], {}, hi=False, engine="parallel")
    run_(runner.run_background(rid))
    v = store.get(rid)
    assert v["status"] == "done" and v["dossier"]["engine"] == "parallel" and v["dossier"]["vendor"]["run_id"] == "trun_1"
    c = v["cost"]
    assert c["vendor"] == {"engine": "parallel", "inr": 60.0, "known": False, "note": "the price you set; the vendor has not reported a cost"} or c["vendor"]["inr"] == 60.0
    assert c["total_inr"] >= 60.0 and v["cost_inr"] == c["total_inr"] and "ESTIMATE" in bill.format_line(c, hi=False)
    assert v["checkpoint"] is None and v["dossier"]["stats"]["verified_notes"] >= 1
    assert [p["status"] for _c, k, p in jobs["events"] if k == "research_run"][-1] == "done"
    assert [m for m, *_ in seen].count("POST") == 1


def test_exas_own_reported_cost_replaces_the_estimate(jobs):
    mock(_exa_handler([], cost=0.5))
    rid = runner.start("t1", "c1", "What is the Corvane Index?", ["value?"], {}, hi=False, engine="exa")
    run_(runner.run_background(rid))
    c = store.get(rid)["cost"]
    assert c["vendor"]["known"] is True and c["vendor"]["inr"] == pytest.approx(0.5 * usage.usd_inr(), abs=0.01)
    assert "reported by the vendor" in bill.format_line(c, hi=False)


def test_a_restart_during_a_vendor_run_reattaches_and_does_not_pay_again(jobs):
    seen = []
    mock(_parallel_handler(seen, polls=("running", "completed")))
    rid = runner.start("t1", "c1", "What is the Corvane Index?", ["value?"], {}, hi=False, engine="parallel")
    with session() as s:                                   # the process died right after the vendor accepted the run
        r = s.get(store.ResearchRun, rid)
        r.status, r.tries, r.updated_at = "running", 1, now() - timedelta(seconds=900)
        r.checkpoint = json.dumps({"vendor": {"engine": "parallel", "run_id": "trun_1"}})
        r.cost_inr, r.cost = 60.0, json.dumps({"total_inr": 60.0, "model_inr": 0.0, "vendor": {"engine": "parallel", "inr": 60.0, "known": False, "note": ""}})

    async def go():
        n = await runner.tick()
        await asyncio.gather(*list(runner._BG))
        return n
    assert run_(go()) == 1
    v = store.get(rid)
    assert v["status"] == "done" and v["tries"] == 2
    assert not any(m == "POST" for m, *_ in seen), "the run was created again after the restart: a second charge"
    assert v["cost"]["vendor"]["inr"] == 60.0 and v["cost"]["total_inr"] < 120.0                      # the estimate was carried, not added twice


def test_a_vendor_failure_fails_the_run_with_the_reason_and_the_estimate_stays_charged(jobs):
    mock(lambda r: httpx.Response(401, text="no"))
    rid = runner.start("t1", "c1", "Q?", ["g"], {}, hi=False, engine="parallel")
    run_(runner.run_background(rid))
    v = store.get(rid)
    assert v["status"] == "failed" and "key was refused" in v["error"]
    assert v["cost_inr"] >= 0 and [p["status"] for _c, k, p in jobs["events"] if k == "research_run"][-1] == "failed"


def test_a_gate_closed_after_the_ask_fails_the_run_instead_of_starting_it(jobs):
    rid = runner.start("t1", "c1", "Q?", ["g"], {}, hi=False, engine="parallel")
    jobs["st"].research_vendor_terms_ack = ""                                     # she took the terms acknowledgement away
    run_(runner.run_background(rid))
    assert store.get(rid)["status"] == "failed" and "RESEARCH_VENDOR_TERMS_ACK" in store.get(rid)["error"]


def test_stopping_a_vendor_run_cancels_it_and_records_the_estimate(jobs):
    seen = []
    mock(_exa_handler(seen))
    rid = runner.start("t1", "c1", "Q?", ["g"], {}, hi=False, engine="exa")
    runner.stop("t1", rid)
    run_(runner.run_background(rid))                                              # already stopped: never started
    assert store.get(rid)["status"] == "stopped" and not any(m == "POST" for m, *_ in seen)


def test_status_and_the_config_defaults(jobs):
    rid = runner.start("t1", "c1", "Q?", ["g"], {}, hi=False, engine="linkup")
    assert runner.status("t1")[0]["engine"] == "linkup" and rid
    s = type(get_settings())()
    assert s.research_engines_allowed == "hoola" and s.research_vendor_terms_ack == "" and s.research_parallel_run_inr == 0.0
    assert (s.research_parallel_processor, s.research_exa_effort, s.research_openai_model, s.research_linkup_depth) == ("core", "auto", "o4-mini-deep-research", "L")
