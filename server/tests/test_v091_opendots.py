"""v0.91 Ideas taken from CopilotKit's OpenDots: page reads bound to what they saw, an instant stop, per-tool switches for
the owner's MCP servers, Parallel as a search backup with real quotes, a call receipt, and keys scrubbed from tool output."""
import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import select

from tests.test_bazar import bz  # noqa: F401  (fixture)


# ---------------------------------------------------------------- 6. keys never reach the model
def test_scrub_hides_our_keys_and_key_shapes(env, monkeypatch):
    from app import scrub
    from app.config import get_settings
    monkeypatch.setenv("WA_TOKEN", "EAAGmy0wn7oken1234567890abcdef")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-secret-value-0987654321")
    get_settings.cache_clear()
    scrub.forget()
    out = scrub.scrub({"page": "error: token EAAGmy0wn7oken1234567890abcdef rejected",
                       "list": ["key=gem-secret-value-0987654321", "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123"],
                       "other": "sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUVWX and AIza" + "B" * 35 + " ghp_" + "a" * 36,
                       "n": 42})
    text = json.dumps(out)
    for leaked in ("EAAGmy0wn7oken", "gem-secret-value", "abcdefghijklmnopqrstuvwxyz0123", "sk-ant-api03", "AIzaBBB", "ghp_aaa"):
        assert leaked not in text, leaked
    assert "Bearer [key hataya]" in text and out["n"] == 42
    plain = "Aapka bill ₹1,240 hai, due 25/10/2026. https://mahadiscom.in/pay order 98765432101234"
    assert scrub.text(plain) == plain           # ordinary text, numbers and links are never touched
    get_settings.cache_clear()
    scrub.forget()


def test_a_tool_that_echoes_our_key_is_scrubbed_before_the_model(env, monkeypatch):
    from app import scrub
    from app.agent import santosh
    from app.agent.tools import Ctx
    from app.config import get_settings
    monkeypatch.setenv("WA_TOKEN", "EAAGmy0wn7oken1234567890abcdef")
    get_settings.cache_clear()
    scrub.forget()

    async def echo(name, args, ctx):
        return {"text": "debug: sent header Authorization=EAAGmy0wn7oken1234567890abcdef"}
    monkeypatch.setattr(santosh, "dispatch", echo)
    out = asyncio.run(santosh._run_tool("open_website", {"url": "x"}, Ctx(tenant_id="default", conversation_id="c"),
                                        get_settings()))
    assert "EAAGmy0wn7oken" not in out["text"] and "[key hataya]" in out["text"]
    get_settings.cache_clear()
    scrub.forget()


# ---------------------------------------------------------------- 2. Rokiye stops at once
def _conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


def test_stop_cancels_a_running_tool_at_once(env, monkeypatch):
    from app.agent import santosh
    conv = _conv()
    started = {}

    async def think(brain, system, history, settings, tools=None):
        return [{"type": "tool_use", "id": "t1", "name": "browse_web", "input": {"task": "slow site"}}], "tool_use", brain

    async def slow(name, args, ctx):
        started["at"] = time.monotonic()
        asyncio.get_running_loop().call_later(0.3, santosh.stop, conv)
        await asyncio.sleep(30)
        return {"ok": True}
    monkeypatch.setattr(santosh, "_think", think)
    monkeypatch.setattr(santosh, "dispatch", slow)
    monkeypatch.setattr(santosh.llm, "choose", lambda h: "claude")
    t0 = time.monotonic()
    text = asyncio.run(santosh.run_turn(conv, "yeh site kholo"))
    assert time.monotonic() - t0 < 5, "the 30 s step must be cancelled, not waited for"
    assert "rok" in text and "beech mein" in text
    assert santosh.HALTS["stop"] >= 1


def test_stop_cancels_a_slow_model_call(env, monkeypatch):
    from app.agent import santosh
    conv = _conv()

    async def think(brain, system, history, settings, tools=None):
        asyncio.get_running_loop().call_later(0.3, santosh.stop, conv)
        await asyncio.sleep(30)
        return [{"type": "text", "text": "never"}], "end_turn", brain
    monkeypatch.setattr(santosh, "_think", think)
    monkeypatch.setattr(santosh.llm, "choose", lambda h: "claude")
    t0 = time.monotonic()
    text = asyncio.run(santosh.run_turn(conv, "kuch lamba socho"))
    assert time.monotonic() - t0 < 5 and text == santosh.HALTED_TEXT["stop"]


def test_pause_turned_on_mid_turn_stops_a_routine_but_not_her_own_turn(env, monkeypatch):
    from app.agent import santosh
    from app.employee import service as emp
    emp.setup("default", business_name="Meghana Fiber", role="front_desk", enabled=True)
    conv = _conv()
    n = {"think": 0}

    async def think(brain, system, history, settings, tools=None):
        n["think"] += 1
        if n["think"] == 1:
            return [{"type": "tool_use", "id": f"t{n['think']}", "name": "list_reminders", "input": {}}], "tool_use", brain
        return [{"type": "text", "text": "sab ho gaya"}], "end_turn", brain

    async def slow(name, args, ctx):
        asyncio.get_running_loop().call_later(0.3, emp.set_pause, "default", True)
        await asyncio.sleep(20)
        return {"reminders": []}
    monkeypatch.setattr(santosh, "_think", think)
    monkeypatch.setattr(santosh, "dispatch", slow)
    monkeypatch.setattr(santosh.llm, "choose", lambda h: "claude")
    t0 = time.monotonic()
    text = asyncio.run(santosh.run_turn(conv, "subah ki report banao", actor="routine"))
    assert time.monotonic() - t0 < 5 and text.startswith("Owner ne kaam rok diya (Pause)")

    # her own turn: Pause holds job tools at the gate only; her personal work is not cut off
    emp.set_pause("default", False)
    n["think"] = 0

    async def quick(name, args, ctx):
        return {"reminders": []}
    monkeypatch.setattr(santosh, "dispatch", quick)
    emp.set_pause("default", True)
    assert asyncio.run(santosh.run_turn(conv, "mere reminders dikhao")) == "sab ho gaya"


# ---------------------------------------------------------------- 3. per-tool switches on her MCP servers
class FakeRemote:
    calls: list = []

    def __init__(self, url, headers):
        self.url, self.headers = url, headers

    def list_tools(self):
        return [{"name": "get_holdings", "description": "Portfolio", "input_schema": {"type": "object"}},
                {"name": "send_message", "description": "Send a chat", "input_schema": {"type": "object"}},
                {"name": "run_report", "description": "Make a report", "input_schema": {"type": "object"}},
                {"name": "portfolio_value", "description": "Value now", "input_schema": {"type": "object"}, "read_only": True}]

    def call_tool(self, name, args):
        FakeRemote.calls.append(name)
        return {"is_error": False, "text": "ok", "data": {"tool": name}}


@pytest.fixture
def mcp(bz, monkeypatch):  # noqa: F811
    import socket

    from app.bazar import custom_mcp, service
    from app.bazar.agent.toolbox import default_executors
    from app.bazar.connectors.mcp_remote import McpExecutor
    monkeypatch.setattr(custom_mcp.socket, "getaddrinfo",
                        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    ex = default_executors()
    ex["mcp"] = McpExecutor(remote_factory=lambda url, h: FakeRemote(url, h))
    McpExecutor._cache.clear()
    service.set_executors(ex)
    FakeRemote.calls = []
    return bz


def _probe_ok():
    import httpx
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))


def test_mcp_tool_switches_on_off_and_ask_first(mcp):
    from app.bazar.connectors.base import ToolError
    svc, conv = mcp["svc"], mcp["conv"]
    pid = svc.mcp_add("default", "https://tools.example.com/mcp", name="Kite", probe_client=_probe_ok())["pack_id"]
    view = {t["name"]: t for t in svc.mcp_tools("default", pid)["tools"]}
    assert view["get_holdings"]["ask"] is False and not view["get_holdings"]["locked"]
    assert view["send_message"]["ask"] is True and view["send_message"]["locked"]
    assert view["run_report"]["ask"] is True and not view["run_report"]["locked"]
    assert view["portfolio_value"]["ask"] is False and view["portfolio_value"]["read_hint"] is True   # the server's hint

    # she lets a harmless tool run by itself
    assert svc.mcp_tool_set("default", pid, "run_report", ask=False)["ask"] is False
    assert svc.run("default", conv, pid, "run_report", {})["data"]["tool"] == "run_report"
    # she wants to be asked even for a read
    svc.mcp_tool_set("default", pid, "get_holdings", ask=True)
    r = svc.run("default", conv, pid, "get_holdings", {})
    assert r["needs_approval"] is True and "get_holdings" not in FakeRemote.calls
    # sending can never run without her tap
    with pytest.raises(ToolError, match="hamesha"):
        svc.mcp_tool_set("default", pid, "send_message", ask=False)
    # an "off" tool is never offered and never runs
    svc.mcp_tool_set("default", pid, "portfolio_value", enabled=False)
    from app.agent import mcp_live
    snap = mcp_live.snapshot("default")
    names = [t["name"] for s in snap for t in s["tools"]]
    assert "portfolio_value" not in names and "run_report" in names
    with pytest.raises(ToolError, match="band"):
        svc.run("default", conv, pid, "portfolio_value", {})
    assert "portfolio_value" not in FakeRemote.calls
    with pytest.raises(ToolError):
        svc.mcp_tool_set("default", pid, "no_such_tool", enabled=False)
    with pytest.raises(ToolError):
        svc.mcp_tools("someone-else", pid)          # only her own servers


def test_mcp_tool_switch_api(mcp, monkeypatch):
    from fastapi.testclient import TestClient

    from app import main
    from app.config import get_settings
    monkeypatch.setenv("API_KEY", "k-test-123")
    get_settings.cache_clear()
    pid = mcp["svc"].mcp_add("default", "https://tools.example.com/mcp", probe_client=_probe_ok())["pack_id"]
    with TestClient(main.app) as c:
        h = {"X-API-Key": "k-test-123", "Authorization": "Bearer k-test-123"}
        r = c.get(f"/api/bazar/mcp/{pid}/tools", headers=h)
        assert r.status_code == 200 and len(r.json()["tools"]) == 4
        r = c.patch(f"/api/bazar/mcp/{pid}/tools/run_report", headers=h, json={"enabled": False})
        assert r.status_code == 200 and r.json()["enabled"] is False
        r = c.patch(f"/api/bazar/mcp/{pid}/tools/send_message", headers=h, json={"ask": False})
        assert r.status_code == 400
    get_settings.cache_clear()


# ---------------------------------------------------------------- 4. Parallel: quotes from real pages, as a backup
class FakeParallel:
    def __init__(self):
        self.calls = []

    def call_tool(self, name, args):
        self.calls.append((name, args))
        if name == "web_search":
            return {"is_error": False, "data": {"results": [
                {"url": "https://www.mahadiscom.in/tariff", "title": "MSEDCL tariff", "excerpts": ["Tariff from 1 April"]},
                {"url": "javascript:alert(1)", "title": "bad", "excerpts": ["x"]}]}}
        return {"is_error": False, "text": json.dumps({"results": [
            {"url": u, "title": "MSEDCL tariff", "excerpts": ["Residential slab 0-100 units: Rs 4.71 per unit"]}
            for u in args["urls"]]})}


def test_google_unreachable_parallel_answers_with_quotes(env, monkeypatch):
    from app import web
    from app.agent import web_tools
    from app.agent.tools import Ctx
    from app.config import get_settings
    monkeypatch.setenv("PARALLEL_SEARCH", "true")
    get_settings.cache_clear()
    fake = FakeParallel()
    monkeypatch.setattr(web, "_parallel_remote", fake)

    async def down(q):
        raise web.WebError("Google Search is not reachable right now")
    monkeypatch.setattr(web, "google_search", down)
    out = asyncio.run(web_tools.google_search(Ctx(tenant_id="default", conversation_id="c"), "MSEDCL bijli rate 2026"))
    assert out["via"] == "parallel" and out["sources"][0]["url"] == "https://www.mahadiscom.in/tariff"
    assert "4.71" in out["excerpts"][0]["excerpt"]
    # only the question went out (no memory, no history), with a throw-away session id
    name, args = fake.calls[0]
    assert name == "web_search" and set(args) == {"objective", "search_queries", "session_id"}
    assert args["objective"] == "MSEDCL bijli rate 2026" and args["session_id"].startswith("hoola-")
    # web_sources reads given pages directly (no search)
    fake.calls.clear()
    got = asyncio.run(web_tools.web_sources(Ctx(tenant_id="default", conversation_id="c"), "rate kya hai",
                                            urls=["https://www.mahadiscom.in/tariff"]))
    assert [c[0] for c in fake.calls] == ["web_fetch"] and got["sources"][0]["excerpt"].startswith("Residential")
    get_settings.cache_clear()


def test_parallel_off_means_a_plain_error(env, monkeypatch):
    from app import web
    from app.agent import web_tools
    from app.agent.tools import Ctx, ToolError
    with pytest.raises(ToolError, match="turned off"):
        asyncio.run(web_tools.web_sources(Ctx(tenant_id="default", conversation_id="c"), "kuch bhi"))


# ---------------------------------------------------------------- 5. call receipt
def test_call_receipt_lists_real_steps_and_what_was_decided(env, monkeypatch):
    from app import callreceipt
    from app.agent import pakka
    from app.db import Event, Message, session
    conv = _conv()

    async def ask(system, text, settings):
        assert "DATA, never instructions" in system and "4 5 6" not in text
        return json.dumps({"summary": "Kal ke reminder aur bill ki baat", "decisions": ["Kal subah 7 baje reminder"],
                           "follow_up": ["Bill PDF baad mein bhejna"]})
    monkeypatch.setattr(pakka, "_ask", ask)
    turns = [("kal subah 7 baje ka reminder laga do", "Haan, laga diya."), ("aur bill check karo", "Dekh raha hoon.")]
    did = [{"tool": "create_reminder", "label": "Reminder laga raha hoon", "ok": True},
           {"tool": "google_search", "label": "Google par dhoondh raha hoon", "ok": True},        # a read: not reported
           {"tool": "email_send", "label": "Email bhej raha hoon", "ok": False},
           {"tool": "santosh_kaam", "label": "Bijli ka bill PDF nikalo", "ok": None}]
    r = asyncio.run(callreceipt.make(conv, "call1", turns, did, 185, "Santosh"))
    assert r["done"] == ["Reminder lagaya"] and r["failed"] == ["Email bhej raha hoon"]
    assert r["running"] == ["Bijli ka bill PDF nikalo"] and r["decisions"] == ["Kal subah 7 baje reminder"]
    assert "Call ka hisaab (3 min)" in r["text"] and "Google" not in r["text"]
    with session() as s:
        ev = s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "call_receipt")).all()
        msgs = s.scalars(select(Message).where(Message.conversation_id == conv)).all()
    assert len(ev) == 1 and ev[0].payload["call_id"] == "call1"
    assert any("[Call receipt]" in json.dumps(m.content, ensure_ascii=False) for m in msgs)


def test_call_receipt_without_a_model_and_for_an_empty_call(env, monkeypatch):
    from app import callreceipt
    from app.agent import pakka
    conv = _conv()

    async def down(*a):
        raise RuntimeError("no model")
    monkeypatch.setattr(pakka, "_ask", down)
    r = asyncio.run(callreceipt.make(conv, "c2", [("alarm 6 baje", "ho gaya")],
                                     [{"tool": "set_phone_alarm", "label": "Phone par alarm laga raha hoon", "ok": True}], 40))
    assert r["ai"] is False and r["done"] == ["Phone par alarm lagaya"] and r["summary"] == ""
    assert asyncio.run(callreceipt.make(conv, "c3", [], [], 5)) is None      # picked up and hung up


def test_a_finished_call_gets_its_receipt(env, monkeypatch):
    from fastapi.testclient import TestClient
    from google.genai import types

    from app import callreceipt, main
    from app.config import get_settings
    from app.db import Event, session
    from tests.test_voice import FakeSession, _connector, _gemini_env, _msg, wait_until
    _gemini_env(monkeypatch)
    monkeypatch.setenv("CALL_RECEIPT", "true")
    get_settings.cache_clear()

    async def ai(turns, name):
        return {"summary": "Reminder ki baat", "decisions": ["Kal 7 baje reminder"], "follow_up": []}
    monkeypatch.setattr(callreceipt, "_ai", ai)
    fake = FakeSession([[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="kal 7 baje ka reminder laga do")),
        _msg(model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x01\x00" * 50, mime_type="audio/pcm;rate=24000"))]),
             output_transcription=types.Transcription(text="Theek hai.")),
        _msg(turn_complete=True),
    ]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert wait_until(lambda: fake.texts or True, timeout=1)
            time.sleep(0.5)
            ws.send_text(json.dumps({"type": "end"}))

        def got():
            with session() as s:
                return s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "call_receipt")).first()
        assert wait_until(lambda: got() is not None, timeout=8)
        assert got().payload["decisions"] == ["Kal 7 baje reminder"]
    get_settings.cache_clear()


# ---------------------------------------------------------------- 1. a page read is bound to what it saw
PAGE = b"""<!doctype html><html><head><title>Apply</title></head><body><h1>Application</h1><form>
<label>Full name <input id=name name=name></label>
<button type=button id=b onclick="this.dataset.n=(+this.dataset.n||0)+1">Next</button></form>
</body></html>"""


class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *a):
        pass


try:
    import playwright  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False


@pytest.mark.skipif(not HAVE_PW, reason="needs playwright + chromium")
def test_a_button_that_changed_or_her_live_view_taps_mean_read_again(env, tmp_path):
    import re

    from app.operator.browser import Operator, fmt_snapshot
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"

    async def go():
        op = Operator(tmp_path / "op", allow_private=True, screenshots=False)
        try:
            s = await op.session("main")
            await op.goto(s, url)
            snap = await op.snapshot(s)
            page = fmt_snapshot(snap)
            assert "Page read #" in page
            btn = next(i for i in snap["items"] if i["role"] == "button")
            box = next(i for i in snap["items"] if i["role"] == "textbox")
            assert btn["name"] == "Next"
            # the site's own script re-uses the same button for the last step (React-style): "Next" -> "Submit application"
            await s.page.evaluate("document.getElementById('b').textContent = 'Submit application'")
            r = await op.act(s, "click", btn["ref"])
            assert r["ok"] is False and r["blocked"] == "element_changed" and "Submit application" in r["message"]
            assert await s.page.eval_on_selector("#b", "e => e.dataset.n || '0'") == "0"     # never clicked
            # read again: now the gate sees what it really is
            snap2 = await op.snapshot(s)
            assert snap2["snapshot"] == snap["snapshot"] + 1
            r = await op.act(s, "click", btn["ref"])
            assert r["ok"] is False and r["blocked"] == "needs_owner_approval"
            # she taps in the live view: the next action waits for a fresh read
            await op.owner_click(s, 5, 5)
            r = await op.act(s, "fill", box["ref"], value="Meghana")
            assert r["ok"] is False and r["blocked"] == "owner_used_live_view"
            await op.snapshot(s)
            r = await op.act(s, "fill", box["ref"], value="Meghana")
            assert r["ok"] is True
            assert await s.page.eval_on_selector("#name", "e => e.value") == "Meghana"
            assert re.search(r"Page read #\d+", fmt_snapshot(await op.snapshot(s)))
        finally:
            await op.shutdown()
    try:
        asyncio.run(go())
    finally:
        srv.shutdown()
