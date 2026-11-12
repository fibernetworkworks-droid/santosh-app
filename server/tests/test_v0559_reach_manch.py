"""v0.559.0 REACH MANCH - the Agent-Reach discipline layer (owner: "MAKE A HOOLA AGENT REACH FEATURE, DEVLOPE END TO END").

The Agent-Reach repo (Panniantong/Agent-Reach, MIT, READ archived at download/AGENT_REACH_READ.md) ported
IDEA-ONLY onto the house internet stack: ONE envelope {schema_version, ok, tool, action, backend, items,
meta.attempts, error:{code, message, hint}}, an error taxonomy whose hints instruct the model, ordered
backends with health memory + TTL pauses, a global channel cooldown on rate limits, a per-tenant minute
budget, honest labels (content_scope, completeness_verified:false) and status/channels introspection.
Zero upstream code, zero new pip, zero new keys, zero client changes. All tests are network-free: the
doors (web.open_website / google_search / parallel_search) are plugged with fakes.
"""
import asyncio
import json

import pytest

from app.agent import reach_tools as rt
from app.agent.tools import Ctx
from app.config import get_settings
from app.web import WebError


@pytest.fixture(autouse=True)
def _clean_ledgers():
    rt.reset_health()
    yield
    rt.reset_health()


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    """The zero-network law: any test that reaches a real door fails loudly instead of calling out."""
    from app import web as webmod

    def _forbidden(where):
        def boom(*a, **k):
            raise AssertionError(f"test tried the REAL {where} door - plug a fake instead")
        return boom
    monkeypatch.setattr(webmod, "open_website", _forbidden("open_website"))
    monkeypatch.setattr(webmod, "google_search", _forbidden("google_search"))
    monkeypatch.setattr(webmod, "parallel_search", _forbidden("parallel_search"))


@pytest.fixture()
def st(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "reach_enabled", True, raising=False)
    monkeypatch.setattr(s, "reach_per_tenant_per_min", 0, raising=False)
    return s


def ctx(tenant="t1"):
    return Ctx(tenant_id=tenant, conversation_id="c1")


def fake_backend(monkeypatch, name, fn):
    monkeypatch.setattr(rt, name, fn)


# ---------------------------------------------------------------- the envelope
def test_envelope_shape_is_exactly_one_object(st, monkeypatch):
    async def house(url, **_):
        return [{"title": "Sharma Electronics", "url": url, "text": "LED TV price ₹21,499"}], \
            {"content_scope": "page_text"}
    fake_backend(monkeypatch, "_read_house", house)
    out = asyncio.run(rt.run_reach(ctx(), "read", url="https://shop.example.in/tv"))
    assert set(out) == {"schema_version", "ok", "tool", "action", "backend", "items", "meta", "error"}
    assert out["schema_version"] == 1 and out["ok"] and out["tool"] == "reach"
    assert out["backend"] == "house" and out["error"] is None
    assert out["items"] == [{"title": "Sharma Electronics", "url": "https://shop.example.in/tv",
                             "text": "LED TV price ₹21,499"}]
    meta = out["meta"]
    assert meta["completeness_verified"] is False and meta["content_scope"] == "page_text"
    assert meta["attempts"] == [{"backend": "house", "result": "ok", "ms": meta["attempts"][0]["ms"]}]
    assert isinstance(meta["elapsed_ms"], int) and meta["elapsed_ms"] >= 0


def test_failure_envelope_carries_code_message_hint_and_empty_items(st, monkeypatch):
    async def house(url, **_):
        raise WebError("The website answered with error 503.")
    fake_backend(monkeypatch, "_read_house", house)
    fake_backend(monkeypatch, "_read_parallel", house)
    out = asyncio.run(rt.run_reach(ctx(), "read", url="https://shop.example.in/gone"))
    assert out["ok"] is False and out["items"] == [] and out["backend"] is None
    assert out["error"]["code"] == "UPSTREAM_BROKEN"
    assert out["error"]["message"] and out["error"]["hint"]
    assert [a["backend"] for a in out["meta"]["attempts"]] == ["house", "parallel"]


# ---------------------------------------------------------------- the doors: read
def test_read_uses_the_house_door_first(st, monkeypatch):
    seen = {}

    async def house(url, **_):
        seen["url"] = url
        return [{"title": "T", "url": url, "text": "body"}], {"content_scope": "page_text"}

    async def parallel(url, **_):
        raise AssertionError("parallel must not be called when the house door answers")
    fake_backend(monkeypatch, "_read_house", house)
    fake_backend(monkeypatch, "_read_parallel", parallel)
    out = asyncio.run(rt.run_reach(ctx(), "read", url="https://shop.example.in/"))
    assert out["ok"] and out["backend"] == "house" and seen["url"] == "https://shop.example.in/"


def test_read_falls_back_to_the_free_fetch_and_keeps_the_trail(st, monkeypatch):
    async def house(url, **_):
        raise WebError("Could not open the website: connection refused")

    async def parallel(url, **_):
        return [{"title": "T", "url": url, "text": "excerpt"}], \
            {"content_scope": "page_text", "note": "excerpt via the free fetch backup (Parallel), not the full page"}
    fake_backend(monkeypatch, "_read_house", house)
    fake_backend(monkeypatch, "_read_parallel", parallel)
    out = asyncio.run(rt.run_reach(ctx(), "read", url="https://shop.example.in/"))
    assert out["ok"] and out["backend"] == "parallel"
    trail = out["meta"]["attempts"]
    assert [a["result"] for a in trail] == ["UPSTREAM_BROKEN", "ok"]
    assert "excerpt via the free fetch backup" in out["meta"]["note"]


def test_an_empty_result_is_no_rows_never_one_fake_row(st, monkeypatch):
    async def house(url, **_):
        raise WebError("Could not open the website: nope")

    async def parallel(url, **_):
        return [], {"content_scope": "page_text"}
    fake_backend(monkeypatch, "_read_house", house)
    fake_backend(monkeypatch, "_read_parallel", parallel)
    out = asyncio.run(rt.run_reach(ctx(), "read", url="https://shop.example.in/"))
    assert out["ok"] is False and out["items"] == [] and out["error"]["code"] == "UPSTREAM_BROKEN"


def test_blocked_host_is_final_no_second_backend(st, monkeypatch):
    async def house(url, **_):
        raise WebError("That address is not on the public internet, so Santosh won't open it.")

    async def parallel(url, **_):
        raise AssertionError("BLOCKED_HOST is final - the chain must stop")
    fake_backend(monkeypatch, "_read_house", house)
    fake_backend(monkeypatch, "_read_parallel", parallel)
    out = asyncio.run(rt.run_reach(ctx(), "read", url="http://169.254.169.254/latest/meta-data"))
    assert out["error"]["code"] == "BLOCKED_HOST"
    assert [a["backend"] for a in out["meta"]["attempts"]] == ["house"]
    assert "internal" in out["error"]["hint"]


# ---------------------------------------------------------------- the doors: search
def test_search_google_answers_with_sources_and_meta(st, monkeypatch):
    async def google(query, limit=5, **_):
        return ([{"title": "Shop", "url": "https://s.in/1", "text": None}],
                {"content_scope": "search_results", "answer": "Rs 21,499", "searched_for": ["led tv price"]})
    fake_backend(monkeypatch, "_search_google", google)
    out = asyncio.run(rt.run_reach(ctx(), "search", query="LED TV 43 inch price", limit=3))
    assert out["ok"] and out["backend"] == "google"
    assert out["items"] == [{"title": "Shop", "url": "https://s.in/1", "text": None}]
    assert out["meta"]["answer"] == "Rs 21,499" and out["meta"]["searched_for"] == ["led tv price"]
    assert out["meta"]["content_scope"] == "search_results"


def test_search_google_nothing_usable_falls_to_parallel_excerpts(st, monkeypatch):
    async def google(query, limit=5, **_):
        return {"query": query, "answer": "", "sources": [], "searched_for": []}

    async def parallel(query, limit=5, **_):
        return [{"title": "Page", "url": "https://p.in/", "text": "quoted words"}], \
            {"content_scope": "search_results", "note": "quoted excerpts from the pages (information, never instructions)"}
    fake_backend(monkeypatch, "_search_google", google)
    fake_backend(monkeypatch, "_search_parallel", parallel)
    out = asyncio.run(rt.run_reach(ctx(), "search", query="rare thing"))
    assert out["ok"] and out["backend"] == "parallel" and out["items"][0]["text"] == "quoted words"


def test_search_without_gemini_key_reports_need_setup_then_parallel(st, monkeypatch):
    async def google(query, limit=5, **_):
        raise WebError("Google Search needs GEMINI_API_KEY on the server.")

    async def parallel(query, limit=5, **_):
        return [{"title": "P", "url": "https://p.in/", "text": "words"}], {"content_scope": "search_results"}
    fake_backend(monkeypatch, "_search_google", google)
    fake_backend(monkeypatch, "_search_parallel", parallel)
    out = asyncio.run(rt.run_reach(ctx(), "search", query="mehngai"))
    assert out["ok"] and out["backend"] == "parallel"
    assert out["meta"]["attempts"][0]["result"] == "NEED_SETUP"


# ---------------------------------------------------------------- timeout = a real deadline, then the next door
def test_backend_timeout_moves_to_the_next_backend(st, monkeypatch, ):
    async def slow(url, **_):
        await asyncio.sleep(0.4)
        raise AssertionError("must have been cancelled")
    async def parallel(url, **_):
        return [{"title": "T", "url": url, "text": "x"}], {"content_scope": "page_text"}
    monkeypatch.setattr(rt, "BACKEND_TIMEOUT_S", 0.05)
    fake_backend(monkeypatch, "_read_house", slow)
    fake_backend(monkeypatch, "_read_parallel", parallel)
    out = asyncio.run(rt.run_reach(ctx(), "read", url="https://shop.example.in/"))
    assert out["ok"] and out["backend"] == "parallel"
    assert out["meta"]["attempts"][0]["result"] == "TIMEOUT"


# ---------------------------------------------------------------- health memory: pauses with TTL, cleared on success
def test_a_failing_backend_is_paused_then_skipped(st, monkeypatch):
    calls = {"n": 0}

    async def house(url, **_):
        calls["n"] += 1
        raise WebError("Could not open the website: timed out")

    async def parallel(url, **_):
        return [{"title": "T", "url": url, "text": "x"}], {"content_scope": "page_text"}
    fake_backend(monkeypatch, "_read_house", house)
    fake_backend(monkeypatch, "_read_parallel", parallel)
    first = asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/1"))
    assert first["ok"] and first["backend"] == "parallel" and calls["n"] == 1
    second = asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/2"))
    assert second["ok"] and second["backend"] == "parallel" and calls["n"] == 1      # house skipped, not retried
    skipped = second["meta"]["attempts"][0]
    assert skipped["backend"] == "house" and skipped["skipped"] is True and skipped["result"] == "TIMEOUT"
    assert skipped["retry_after_seconds"] <= 60


def test_the_pause_expires_after_its_ttl(st, monkeypatch):
    async def house(url, **_):
        raise WebError("Could not open the website: timed out")
    fake_backend(monkeypatch, "_read_house", house)
    fake_backend(monkeypatch, "_read_parallel", house)
    asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/1"))
    assert rt.backend_pause("read", "house") is not None
    rt._HEALTH[("read", "house")]["at"] -= 61                       # the clock moves past the pause
    assert rt.backend_pause("read", "house") is None                # expired: the door may be tried again


def test_success_clears_the_backend_health(st, monkeypatch):
    async def house_fail(url, **_):
        raise WebError("Could not open the website: timed out")

    async def parallel(url, **_):
        return [{"title": "T", "url": url, "text": "x"}], {"content_scope": "page_text"}
    fake_backend(monkeypatch, "_read_house", house_fail)
    fake_backend(monkeypatch, "_read_parallel", parallel)
    asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/1"))
    rt._HEALTH[("read", "house")]["at"] -= 61                     # the pause runs out
    fake_backend(monkeypatch, "_read_house", parallel)             # the house door recovers
    out = asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/2"))
    assert out["backend"] == "house"
    assert rt.backend_pause("read", "house") is None and rt.backend_pause("read", "parallel") is None


# ---------------------------------------------------------------- rate limit: the whole channel cools down, globally
def test_rate_limit_cools_the_channel_and_reports_retry_after(st, monkeypatch):
    async def house(url, **_):
        raise WebError("The website answered with error 429.")
    fake_backend(monkeypatch, "_read_house", house)
    fake_backend(monkeypatch, "_read_parallel", house)
    first = asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/1"))
    assert first["error"]["code"] == "RATE_LIMITED"
    second = asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/2"))
    assert second["error"]["code"] == "RATE_LIMITED" and second["meta"]["budget"] == "channel"
    assert second["error"]["retry_after_seconds"] >= 1
    assert second["meta"]["attempts"] == []                         # cooled before any door was tried


def test_the_search_channel_is_not_blocked_by_the_read_channel(st, monkeypatch):
    async def house(url, **_):
        raise WebError("The website answered with error 429.")
    async def google(query, limit=5, **_):
        return ([{"title": "S", "url": "https://s.in/1", "text": None}],
                {"content_scope": "search_results", "answer": "a", "searched_for": []})
    fake_backend(monkeypatch, "_read_house", house)
    fake_backend(monkeypatch, "_read_parallel", house)
    fake_backend(monkeypatch, "_search_google", google)
    asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/1"))
    out = asyncio.run(rt.run_reach(ctx(), "search", query="anything"))
    assert out["ok"] and out["backend"] == "google"          # the read cooldown never touches search


# ---------------------------------------------------------------- the per-tenant budget
def test_tenant_budget_stops_the_third_call_and_frees_the_other_tenant(st, monkeypatch):
    st.reach_per_tenant_per_min = 2
    async def house(url, **_):
        return [{"title": "T", "url": url, "text": "x"}], {"content_scope": "page_text"}
    fake_backend(monkeypatch, "_read_house", house)
    assert asyncio.run(rt.run_reach(ctx("a"), "read", url="https://s.in/1"))["ok"]
    assert asyncio.run(rt.run_reach(ctx("a"), "read", url="https://s.in/2"))["ok"]
    third = asyncio.run(rt.run_reach(ctx("a"), "read", url="https://s.in/3"))
    assert third["error"]["code"] == "RATE_LIMITED" and third["meta"]["budget"] == "tenant"
    assert third["meta"]["attempts"] == [] and third["items"] == []
    other = asyncio.run(rt.run_reach(ctx("b"), "read", url="https://s.in/1"))
    assert other["ok"]                                              # tenant b is untouched


def test_a_rate_limit_cooldown_is_global_but_the_budget_is_per_tenant(st):
    st.reach_per_tenant_per_min = 100
    rt.remember_backend("read", "house", rt.ReachError("RATE_LIMITED", "too many requests", retry_after=3600))
    for t in ("a", "b"):
        out = asyncio.run(rt.run_reach(ctx(t), "read", url="https://s.in/1"))
        assert out["error"]["code"] == "RATE_LIMITED" and out["meta"]["budget"] == "channel"


# ---------------------------------------------------------------- classify: any failure becomes a code
@pytest.mark.parametrize("msg,code", [
    ("Google Search needs GEMINI_API_KEY on the server.", "NEED_SETUP"),
    ("Parallel search is turned off on this server.", "NEED_SETUP"),
    ("The website answered with error 404.", "NOT_FOUND"),
    ("Website 'nosuch.example.in' not found.", "NOT_FOUND"),
    ("The website answered with error 429.", "RATE_LIMITED"),
    ("The website answered with error 403.", "PLATFORM_BLOCKED"),
    ("That address is not on the public internet, so Santosh won't open it.", "BLOCKED_HOST"),
    ("Only normal http(s) website links can be opened.", "BAD_INPUT"),
    ("Only standard website ports (80/443) are allowed.", "BAD_INPUT"),
    ("This link is a file (application/pdf), not a web page Santosh can read.", "BAD_INPUT"),
    ("Could not open the website: timed out", "TIMEOUT"),
    ("The website redirected too many times.", "UPSTREAM_BROKEN"),
    ("Parallel could not finish this search right now.", "UPSTREAM_BROKEN"),
])
def test_classify_maps_the_house_messages(msg, code):
    assert rt.classify(WebError(msg)).code == code
    assert rt.classify(rt.ReachError(code, msg)).code == code          # a ReachError rides as-is


def test_unknown_exceptions_become_upstream_broken():
    assert rt.classify(RuntimeError("boom")).code == "UPSTREAM_BROKEN"
    assert rt.classify(asyncio.TimeoutError()).code == "TIMEOUT"


# ---------------------------------------------------------------- validation
@pytest.mark.parametrize("kwargs,frag", [
    ({"action": "flying"}, "unknown action"),
    ({"action": "read"}, "read needs a url"),
    ({"action": "search"}, "search needs a query"),
    ({"action": "read", "url": "https://s.in/", "limit": True}, "limit must be"),
    ({"action": "read", "url": "https://s.in/", "limit": 9}, "limit must be"),
    ({"action": "read", "url": "https://s.in/", "limit": "3"}, "limit must be"),
])
def test_bad_input_envelopes(st, kwargs, frag):
    out = asyncio.run(rt.run_reach(ctx(), **kwargs))
    assert out["ok"] is False and out["error"]["code"] == "BAD_INPUT" and frag in out["error"]["message"]
    if "valid" in out["error"]["message"]:
        assert "read, search, channels, status" in out["error"]["message"]


def test_limit_clamps_the_rows(st, monkeypatch):
    async def google(query, limit=5, **_):
        return ([{"title": f"S{i}", "url": f"https://s.in/{i}", "text": None} for i in range(8)],
                {"content_scope": "search_results", "answer": "a", "searched_for": []})
    fake_backend(monkeypatch, "_search_google", google)
    out = asyncio.run(rt.run_reach(ctx(), "search", query="q", limit=2))
    assert len(out["items"]) == 2


# ---------------------------------------------------------------- introspection: channels + status
def test_channels_lists_the_doors_and_their_arguments(st):
    out = asyncio.run(rt.run_reach(ctx(), "channels"))
    assert out["ok"] and out["action"] == "channels" and out["error"] is None
    chans = {r["channel"]: r for r in out["items"]}
    assert set(chans) == {"read", "search"}
    assert chans["read"]["backends"] == ["house", "parallel"]
    assert chans["search"]["backends"] == ["google", "parallel"]
    assert "url" in chans["read"]["params"] and "query" in chans["search"]["params"]


def test_status_shows_the_ledgers_and_never_a_secret(st, monkeypatch):
    st.gemini_api_key = "sk-secret-gemini-value"
    async def house(url, **_):
        raise WebError("Could not open the website: timed out")
    fake_backend(monkeypatch, "_read_house", house)
    fake_backend(monkeypatch, "_read_parallel", house)
    asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/1"))
    out = asyncio.run(rt.run_reach(ctx(), "status"))
    assert out["ok"] and out["action"] == "status"
    rows = {(r["channel"], r["backend"]): r for r in out["items"]}
    assert rows[("read", "house")]["state"] == "paused" and rows[("read", "house")]["last_code"] == "TIMEOUT"
    assert rows[("search", "google")]["state"] == "ok"
    assert out["meta"]["parallel"] is not None and out["meta"]["enabled"] is True
    payload = json.dumps(out)
    assert "sk-secret-gemini-value" not in payload and "gemini_api_key" not in payload


def test_status_looking_never_consumes_the_budget(st, monkeypatch):
    st.reach_per_tenant_per_min = 2
    async def house(url, **_):
        return [{"title": "T", "url": url, "text": "x"}], {"content_scope": "page_text"}
    fake_backend(monkeypatch, "_read_house", house)
    assert rt.tenant_budget_left("t1") is None                      # hit 1 of 2
    out = asyncio.run(rt.run_reach(ctx(), "status"))
    assert out["ok"] and out["meta"]["tenant_budget"]["seconds_left"] is None
    second = asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/1"))
    assert second["ok"]                                             # hit 2 lands: status took nothing
    fourth = asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/2"))
    assert fourth["error"]["code"] == "RATE_LIMITED" and fourth["meta"]["budget"] == "tenant"


def test_reach_disabled_says_need_setup_but_introspection_survives(st, monkeypatch):
    st.reach_enabled = False
    out = asyncio.run(rt.run_reach(ctx(), "read", url="https://s.in/"))
    assert out["error"]["code"] == "NEED_SETUP"
    assert asyncio.run(rt.run_reach(ctx(), "channels"))["ok"]
    assert asyncio.run(rt.run_reach(ctx(), "status"))["meta"]["enabled"] is False


# ---------------------------------------------------------------- the house wiring
def test_the_tool_is_registered_in_the_house():
    from app.agent import admit, tools
    names = [t["name"] for t in tools.TOOLS]
    assert names.count("reach") == 1
    assert "reach" in tools.HANDLERS and "reach" in tools.TOOL_LABELS
    assert tools.FAMILY_OF["reach"] == "reach"                      # REACH_TOOLS -> the "reach" family
    assert len(tools.TOOLS) == 627, "626 + 1 app_engine (v0.824 APP ENGINE 1: the Web Studio React app lane - one new tool). 625 + 1 hoola_design (v0.817.0 HOOLA DESIGN: the design editor's one tool). 623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " + ("581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 569 (v0.558) + 1 reach (v0.559 REACH MANCH: the Agent-Reach "
                                     "discipline layer - one envelope, ordered backends, health memory, "
                                     "channel cooldown, tenant budget, status/channels) + 1 speckit (v0.569 SPEC SUTRA)")
    assert "reach" in admit.CORE_FAMILIES                           # always visible: the fallback door
    assert "reach" in admit.EXTRA_KEYS and "website nahi khul" in admit.EXTRA_KEYS["reach"]


def test_the_spec_promises_the_envelope_and_the_hints():
    from app.agent import tools
    spec = next(t for t in tools.TOOLS if t["name"] == "reach")
    assert "envelope" in spec["description"] and "error.hint" in spec["description"]
    assert spec["input_schema"]["properties"]["action"]["enum"] == ["read", "search", "channels", "status"]


def test_app_version_is_the_conscious_bump():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.839.0"
