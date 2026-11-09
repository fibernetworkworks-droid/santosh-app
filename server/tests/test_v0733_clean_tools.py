"""Parity Phase 3 CLEAN TOOLS (docs/CLAUDE_PARITY_PLAN.md): a small core toolbox in view, one web reader, clear English
descriptions, whole-word family admission, head + tail result cuts and no raw Python errors.

conftest pins CHAT_CORE_TOOLS=false for the older suites; every test here removes the pin (the default = on)."""
from __future__ import annotations

import asyncio
import json

import pytest


@pytest.fixture()
def core(monkeypatch):
    from app.config import get_settings
    monkeypatch.delenv("CHAT_CORE_TOOLS", raising=False)
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def _size(specs) -> int:
    return len(json.dumps([{k: t[k] for k in ("name", "description", "input_schema") if k in t} for t in specs]))


PLAIN = "What is the difference between a sole proprietorship and an LLP?"
OLD_READERS = ("open_website", "scrape_page", "scrape", "scrape_stealth", "reach", "duniya", "jharokha",
               "web_sources", "browse_web")
OLD_MEMORY = ("memory_search", "gyaan_khojo", "kgmemory")


class _Ctx:
    tenant_id, conversation_id, user_id, actor, place = "t1", "c-core", "u1", "owner", ""


def test_the_setting_defaults_on(core):
    assert core.chat_core_tools is True


def test_a_plain_ask_sees_about_twenty_core_tools(core):
    from app.agent import admit
    from app.agent.core_tools import CORE
    plan = admit.plan_for(PLAIN, core)
    names = [t["name"] for t in plan.specs()]
    assert len(names) <= 25, names
    assert names[0] == "tool_search"
    assert set(CORE) <= set(names)
    for old in OLD_READERS + OLD_MEMORY:
        assert old not in names, old
    assert plan.families == set()          # no family joins a plain question


def test_the_plain_ask_request_is_much_smaller_than_before(core, monkeypatch):
    from app.agent import admit
    from app.config import get_settings
    new = _size(admit.plan_for(PLAIN, core).specs())
    monkeypatch.setenv("CHAT_CORE_TOOLS", "false")
    get_settings.cache_clear()
    old_plan = admit.plan_for(PLAIN, get_settings())
    old = _size(old_plan.specs())
    assert "web_fetch" not in {t["name"] for t in old_plan.specs()}     # the old mode is unchanged
    assert set(admit.CORE_FAMILIES) <= old_plan.families
    assert new < 0.7 * old, (new, old)


def test_every_old_reader_and_memory_search_is_still_reachable_by_tool_search(core):
    from app.agent import admit, toolsearch
    from app.agent.tools import FAMILY_OF, HANDLERS
    for name in OLD_READERS + OLD_MEMORY:
        assert name in HANDLERS
        ctx = _Ctx()
        ctx.admit = admit.plan_for(PLAIN, core)
        ctx.native_search = False
        out = asyncio.run(admit.tool_search(ctx, need=name))
        assert name in out["admitted"] or ctx.admit._seen(name), (name, out)
        assert name in toolsearch.find(name, {FAMILY_OF[name]}), name     # the native (Claude) search finds it too


def test_web_fetch_is_registered_with_its_modes(core):
    from app.agent.tools import FAMILY_OF, HANDLERS, TOOLS
    spec = next(t for t in TOOLS if t["name"] == "web_fetch")
    assert spec["input_schema"]["properties"]["mode"]["enum"] == ["fast", "browser", "stealth"]
    assert spec["input_schema"]["required"] == ["url"]
    assert "web_fetch" in HANDLERS and FAMILY_OF["web_fetch"] == "webfetch"
    from app.agent.labels_en import LABELS_EN
    assert LABELS_EN["web_fetch"]


def test_core_descriptions_are_clear_english_and_keep_every_property(core):
    from app.agent import admit
    from app.agent.core_tools import CORE, CORE_DESC
    from app.agent.tools import TOOLS
    reg = {t["name"]: t for t in TOOLS}
    shown = {t["name"]: t for t in admit.plan_for(PLAIN, core).specs()}
    for n in CORE:
        if n == "web_fetch":
            continue
        assert shown[n]["description"] == CORE_DESC[n]
        assert "Example:" in CORE_DESC[n]
        old_props = set(((reg[n].get("input_schema") or {}).get("properties") or {}))
        new_props = set(((shown[n].get("input_schema") or {}).get("properties") or {}))
        assert old_props == new_props, n
        assert (shown[n]["input_schema"].get("required") or []) == (reg[n]["input_schema"].get("required") or [])
        for word in ("yaad dilana", "kar do", "baje", "LANE:"):
            assert word not in CORE_DESC[n], (n, word)
    # the safety phrases stay
    assert "NOT sent automatically" in CORE_DESC["email_draft"] and "OTP" in CORE_DESC["email_draft"]
    assert "never pays" in CORE_DESC["file_read"]
    assert "OTP" in CORE_DESC["ask_form"]
    assert "confirms on a card" in CORE_DESC["calendar_add_event"]
    assert reg["email_draft"]["description"] != CORE_DESC["email_draft"]   # the registry itself is untouched


def test_families_join_only_when_her_words_name_them(core):
    from app.agent import admit
    fams = admit.plan_for("What is the current repo rate in India?", core).families
    assert not ({"rentdesk", "rentdesk_biz", "biz_seva", "india"} & fams), fams
    assert "email" in admit.plan_for("Check my inbox and draft a reply to Rahul", core).families
    assert "docstudio" in admit.plan_for("Make a PDF company profile for Newtika", core).families
    assert "life" not in admit.plan_for("Make a PDF company profile for Newtika", core).families
    names = {t["name"] for t in admit.plan_for("Kal Pune mein baarish hogi kya", core).specs()}
    assert "get_weather" in names          # one everyday job comes back by her words, not its whole family
    assert "rentdesk" in admit.plan_for("Mere ghar ka rent agreement check karo", core).families


def test_the_tool_card_stays_full_with_a_slim_median(core):
    from app.quality import toolchoice
    card = toolchoice.router_card()
    assert card["right_in_view"] == card["asks"], [r for r in card["rows"] if not r["in_view"]]
    assert card["wrong_loaded"] == 0
    assert card["median_tools"] <= 32


def test_web_fetch_dispatches_to_the_existing_readers(core, monkeypatch):
    from app.agent import core_tools
    from app.agent.tools import HANDLERS, ToolError
    seen = []

    async def scrape(ctx, url, stealth="auto", max_chars=0, **_):
        seen.append(("scrape", stealth))
        if stealth == "auto":
            raise ToolError("Fetch failed: connection reset")
        return {"url": url, "content": "stealth page"}

    async def open_website(ctx, url, **_):
        seen.append(("open_website", url))
        return {"title": "T", "text": "plain page"}

    async def jharokha(ctx, action="", url=None, **_):
        seen.append(("jharokha", action))
        return {"ok": True, "tree": "- heading 'Hi' [ref=e1]"}

    monkeypatch.setitem(HANDLERS, "scrape", scrape)
    monkeypatch.setitem(HANDLERS, "open_website", open_website)
    monkeypatch.setitem(HANDLERS, "jharokha", jharokha)
    ctx = _Ctx()
    out = asyncio.run(core_tools.web_fetch(ctx, url="https://example.com"))
    assert out["via"] == "open_website" and out["text"] == "plain page" and out["mode"] == "fast"
    out = asyncio.run(core_tools.web_fetch(ctx, url="https://example.com", mode="stealth"))
    assert out["via"] == "scrape" and ("scrape", "always") in seen
    out = asyncio.run(core_tools.web_fetch(ctx, url="https://example.com", mode="browser"))
    assert out["via"] == "jharokha" and ("jharokha", "open") in seen

    async def robots(ctx, url, **_):
        raise ToolError("This site's robots.txt disallows bots for this page (respect_robots on)")
    monkeypatch.setitem(HANDLERS, "scrape", robots)
    seen.clear()
    with pytest.raises(ToolError) as e:
        asyncio.run(core_tools.web_fetch(ctx, url="https://example.com/private"))
    assert "robots" in str(e.value) and not any(s[0] == "open_website" for s in seen)   # a refusal is never bypassed

    async def down(ctx, url, **_):
        raise ToolError("The website answered with error 503.")
    monkeypatch.setitem(HANDLERS, "scrape", down)
    monkeypatch.setitem(HANDLERS, "open_website", down)
    with pytest.raises(ToolError) as e:
        asyncio.run(core_tools.web_fetch(ctx, url="https://example.com"))
    assert "mode=browser" in str(e.value)


def test_big_results_keep_head_and_tail_and_errors_are_plain(core, monkeypatch):
    from app.agent import santosh
    from app.config import get_settings
    big = "START" + "x" * 30000 + "THE_END"
    s = santosh._short(big, 6000)
    assert s.startswith('"START') and s.endswith('THE_END"') and "left out in the middle" in s
    nested = santosh._short({"id": "a1", "body": big, "next": "cursor9"}, 6000)
    assert "THE_END" in nested and "cursor9" in nested and json.loads(nested)["id"] == "a1"
    msg = santosh.clean_error("kaam_plan", TypeError("kaam_plan() missing 1 required positional argument: 'action'"))
    assert "action" in msg and "TypeError" not in msg and "positional" not in msg
    msg = santosh.clean_error("x", KeyError("token"))
    assert "Hoola" in msg and "'token'" not in msg
    monkeypatch.setenv("CHAT_CORE_TOOLS", "false")
    get_settings.cache_clear()
    assert santosh._short(big, 6000).endswith("data_read.]")           # the old cut, byte-for-byte


def test_sub_agents_start_from_the_core_too(core):
    from app.agent import team
    adm = team._agent_admit({"tools": ["web"]}, {"research"}, core)
    names = {t["name"] for t in team._agent_tools(adm, core)}
    assert {"google_search", "web_fetch"} <= names
    assert "deploy_agents" not in names       # depth 1 holds
