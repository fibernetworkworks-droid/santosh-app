"""v0.344 MOSPI + BROKERS: MoSPI eSankhyiki (no login), Upstox / Dhan (one-tap OAuth), Zerodha Kite / FYERS (login inside
one MCP session, kept per account), Groww (partner-gated) and Razorpay on the featured list; every order / GTT /
alert / login waits for her tap, reads run straight; the sticky session id is stored encrypted, per account."""
import json

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_custom_mcp import FakeRemote, _probe, mcp  # noqa: F401  (fixtures)


class FakeSession:
    made: list = []

    def __init__(self, url, get_sid, put_sid, guard):
        self.url, self.get_sid, self.put_sid = url, get_sid, put_sid
        FakeSession.made.append(self)

    def list_tools(self):
        return [{"name": n, "description": n, "input_schema": {"type": "object"}} for n in
                ("login", "get_holdings", "get_positions", "place_order", "place_gtt_order", "cancel_order")]

    def call_tool(self, name, args):
        if not self.get_sid():
            self.put_sid("kitemcp-abc-123")
        return {"is_error": False, "text": f"{name} ok", "data": {"tool": name, "sid": self.get_sid()}}


@pytest.fixture
def brokers(mcp, monkeypatch):  # noqa: F811
    from app.bazar import service
    from app.bazar.agent.toolbox import default_executors
    from app.bazar.connectors.mcp_remote import McpExecutor
    ex = default_executors()
    ex["mcp"] = McpExecutor(remote_factory=lambda url, h: FakeRemote(url, h), session_factory=FakeSession)
    McpExecutor._cache.clear()
    service.set_executors(ex)
    FakeSession.made = []
    return mcp


def test_featured_list_has_mospi_and_the_brokers(env):
    from app.bazar import featured, logos
    want = {"mospi": "none", "upstox": "oauth_dcr", "dhan": "oauth_dcr", "zerodha-kite": "none", "fyers": "none",
            "groww": "oauth_partner", "razorpay": "api_key"}
    for fid, auth in want.items():
        c = featured.get(fid)
        assert c and c["auth"] == auth and c["india"], fid
        assert c["url"].startswith("https://"), fid
        assert logos.featured_logo(fid), fid
        if fid != "mospi":
            assert c.get("caution"), fid                       # money / trading: every non-read tool needs her tap
    assert featured.get("zerodha-kite")["options"]["session"] and featured.get("fyers")["options"]["session"]
    assert not (featured.get("upstox").get("options") or {}).get("session")
    assert featured.search("zerodha holdings")[0]["id"] == "zerodha-kite"
    assert featured.search("mehngai cpi gdp statistics")[0]["id"] == "mospi"


def test_mospi_one_tap_and_reads_run_straight(brokers):
    svc, conv = brokers["svc"], brokers["conv"]
    out = svc.mcp_connect_featured("default", "mospi", probe_client=_probe(200))
    assert out["status"] == "ready"
    r = svc.run("default", conv, out["pack_id"], "get_holdings", {})     # FakeRemote's read tool
    assert r["data"]["tool"] == "get_holdings" and FakeSession.made == []  # MoSPI uses the normal client


def test_groww_says_partner_pending(brokers):
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="approved apps"):
        brokers["svc"].mcp_connect_featured("default", "groww")


def test_kite_keeps_one_session_reads_straight_orders_and_login_need_tap(brokers):
    svc, conv = brokers["svc"], brokers["conv"]
    out = svc.mcp_connect_featured("default", "zerodha-kite", probe_client=_probe(200))
    assert out["status"] == "ready"
    pid = out["pack_id"]
    mine = [p for p in svc.find("default", "kite holdings")["packs"] if p["pack_id"] == pid][0]
    tiers = {t["tool"]: t["tier"] for t in mine["tools"]}
    assert tiers["get_holdings"] == 0 and tiers["get_positions"] == 0
    assert tiers["place_order"] == 2 and tiers["place_gtt_order"] == 2 and tiers["cancel_order"] == 2
    assert tiers["login"] == 2                                            # caution server: not a read = her tap
    r1 = svc.run("default", conv, pid, "get_holdings", {})
    r2 = svc.run("default", conv, pid, "get_positions", {})
    assert r1["data"]["sid"] == r2["data"]["sid"] == "kitemcp-abc-123"    # same broker session across calls
    order = svc.run("default", conv, pid, "place_order", {"tradingsymbol": "INFY", "quantity": 1, "transaction_type": "BUY"})
    assert order["needs_approval"] is True and "money/code" in order["card"]["title"]
    # the session id is stored encrypted, under her account + this server only
    from app.bazar.db import KVState
    from app.db import session
    with session() as s:
        row = s.get(KVState, f"mcp_sid:default:{pid}")
        assert row is not None and row.value and "kitemcp" not in row.value


def test_session_remote_reuses_reopens_and_parses_sse(env):
    from app.bazar.connectors.mcp_session import SessionRemote
    seen = []
    state = {"alive": {"s1"}, "n": 0}

    def handler(req: httpx.Request):
        body = json.loads(req.content)
        sid = req.headers.get("mcp-session-id", "")
        seen.append((body.get("method"), sid))
        if body.get("method") == "initialize":
            state["n"] += 1
            new = f"s{state['n']}"
            state["alive"].add(new)
            return httpx.Response(200, headers={"mcp-session-id": new, "content-type": "application/json"},
                                  json={"jsonrpc": "2.0", "id": body["id"], "result": {"protocolVersion": "2025-06-18"}})
        if body.get("method", "").startswith("notifications/"):
            return httpx.Response(202)
        if sid not in state["alive"]:
            return httpx.Response(404, text="session not found")
        data = {"jsonrpc": "2.0", "id": body["id"], "result": {"content": [{"type": "text", "text": "Please log in: https://kite.zerodha.com/connect/login?x"}]}}
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text="event: message\ndata: " + json.dumps(data) + "\n\n")

    box = {"sid": ""}
    r = SessionRemote("https://mcp.kite.trade/mcp", lambda: box["sid"], lambda s: box.__setitem__("sid", s),
                      client=httpx.Client(transport=httpx.MockTransport(handler)))
    out = r.call_tool("login", {})
    assert "kite.zerodha.com" in out["text"] and box["sid"] == "s1"
    r.call_tool("get_holdings", {})
    assert [m for m, _ in seen].count("initialize") == 1                 # reused, not reopened
    state["alive"].discard("s1")                                          # the broker forgot the session
    r.call_tool("get_holdings", {})
    assert box["sid"] == "s2" and [m for m, _ in seen].count("initialize") == 2
