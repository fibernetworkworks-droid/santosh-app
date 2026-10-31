"""v0.288 ZOHO FOR HOOLA: every user adds her own Zoho MCP server (only the tools she ticks).

- the private Zoho address carries its key: sealed in the database, masked everywhere else, opened only to connect;
- old rows with a key in the address are sealed the first time they are read; Bazar tables get new columns on old DBs;
- the OAuth sign-in state is sealed too;
- only Zoho's own MCP domains are accepted for the Zoho card (the console page gets a clear hint);
- a big server shares the native-tool budget fairly and her words pick which of its tools come first;
- bazar_mcp action=tools finds the right tool among hundreds; writes still wait for her tap.
"""
import json

import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_custom_mcp import FakeRemote, _probe, mcp  # noqa: F401  (fixture)

ZURL = "https://hoola-books-60065097786.zohomcp.in/mcp/fe46ddbc48fec3713c8754cea8ec9ac5/message"
KEY = "fe46ddbc48fec3713c8754cea8ec9ac5"


class ZohoRemote(FakeRemote):
    """A Zoho-like server: many tools, Zoho naming."""
    def list_tools(self):
        names = ["list_invoices", "get_invoice", "create_invoice", "email_invoice", "delete_invoice",
                 "get_profit_and_loss_report", "getDealsRecords", "createDealsRecords", "sendEmail", "listEmails"]
        names += [f"get_custom_module_{i}_records" for i in range(120)]
        return [{"name": n, "description": n.replace("_", " "), "input_schema": {"type": "object"}} for n in names]


@pytest.fixture
def zoho(mcp):  # noqa: F811
    from app.bazar import service
    from app.bazar.agent.toolbox import default_executors
    from app.bazar.connectors.mcp_remote import McpExecutor
    ex = default_executors()
    ex["mcp"] = McpExecutor(remote_factory=lambda url, h: ZohoRemote(url, h))
    McpExecutor._cache.clear()
    service.set_executors(ex)
    FakeRemote.calls = []
    return mcp


def _row(pack_id):
    from app.bazar.db import CustomMcp
    from app.db import session
    with session() as s:
        r = s.get(CustomMcp, pack_id)
        return r.url, r.url_enc


def test_mask_and_detect():
    from app.bazar import custom_mcp as m
    assert m.has_secret(ZURL) and KEY not in m.masked(ZURL) and m.masked(ZURL).endswith("/mcp/•••/message")
    q = m.masked("https://acme.zohomcp.com/mcp/message?key=abc123XYZ&x=1")
    assert q == "https://acme.zohomcp.com/mcp/message?key=•••&x=1"
    for plain in ("https://mcp.notion.com/mcp", "https://mcp.supabase.com/mcp?project_ref=abcdefghijklmnopqrst&read_only=true",
                  "https://api.githubcopilot.com/mcp/"):
        assert not m.has_secret(plain) and m.masked(plain) == plain


def test_zoho_card_connects_her_server_and_keeps_the_key_sealed(zoho):
    svc = zoho["svc"]
    out = svc.mcp_connect_featured("default", "zoho-mcp", url=ZURL, probe_client=_probe(200))
    assert out["status"] == "ready" and KEY not in json.dumps(out)
    url, enc = _row(out["pack_id"])
    assert KEY not in url and enc and KEY not in enc                  # sealed, not in clear
    assert KEY not in json.dumps(svc.mcp_list("default"))
    assert all(KEY not in json.dumps(c) for c in svc.mcp_featured("default"))
    svc.run("default", zoho["conv"], out["pack_id"], "list_invoices", {})
    assert FakeRemote.calls[-1][0] == ZURL                             # the real address is used to connect
    w = svc.run("default", zoho["conv"], out["pack_id"], "create_invoice", {"customer": "Ravi", "amount": 500})
    assert w["needs_approval"] is True and len(FakeRemote.calls) == 1  # her tap first
    # adding the same address again is the same row (compared on the real address)
    again = svc.mcp_connect_featured("default", "zoho-mcp", url=ZURL, probe_client=_probe(200))
    assert again["pack_id"] == out["pack_id"] and len(svc.mcp_list("default")) == 1


@pytest.mark.parametrize("bad,why", [("https://mcp.zoho.in/servers/1", "console"),
                                     ("https://evil.example.com/zohomcp.in/mcp/x", "zohomcp"),
                                     ("http://hoola.zohomcp.in/mcp/abc/message", "zohomcp")])
def test_zoho_card_takes_only_zoho_server_addresses(zoho, bad, why):
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match=why):
        zoho["svc"].mcp_connect_featured("default", "zoho-mcp", url=bad, probe_client=_probe(200))


def test_zoho_card_public_has_india_guide_and_starter():
    from app.bazar import featured
    c = featured.public(featured.get("zoho-mcp"))
    assert c["india"] and c["caution"] and c["auth"] == "per_user_url" and "zohomcp.in" in c["url_hint"]
    assert "mcp.zoho.in" in c["how_to_connect"] and "never" in c["how_to_connect"].lower()
    assert "list_invoices" in c["options"]["starter"]["Books / Invoice (accounting, GST)"]
    assert featured.search("zoho books invoice")[0]["id"] == "zoho-mcp"


def test_old_row_with_key_in_address_gets_sealed(zoho):
    from app.bazar.db import CustomMcp
    from app.db import session
    out = zoho["svc"].mcp_add("default", "https://tools.example.com/mcp", probe_client=_probe(200))
    with session() as s:                       # as saved before v0.288: key in clear, nothing sealed
        r = s.get(CustomMcp, out["pack_id"])
        r.url, r.url_enc = ZURL, None
    zoho["svc"].mcp_list("default")            # any read seals it
    url, enc = _row(out["pack_id"])
    assert KEY not in url and enc
    zoho["svc"].run("default", zoho["conv"], out["pack_id"], "list_invoices", {})
    assert FakeRemote.calls[-1][0] == ZURL


def test_bazar_tables_get_new_columns_on_old_databases(zoho):
    from sqlalchemy import inspect, text

    from app import db
    from app.bazar.db import Base as BazarBase
    with db._engine.begin() as c:
        c.execute(text("ALTER TABLE bz_custom_mcp DROP COLUMN url_enc"))
    assert "url_enc" not in {x["name"] for x in inspect(db._engine).get_columns("bz_custom_mcp")}
    db._add_missing_columns(db._engine, BazarBase.metadata)
    assert "url_enc" in {x["name"] for x in inspect(db._engine).get_columns("bz_custom_mcp")}


def test_sign_in_state_is_sealed(zoho, monkeypatch):
    import httpx

    from app.bazar import mcp_auth
    from app.bazar.db import KVState
    from app.db import session
    monkeypatch.setattr(mcp_auth, "discover", lambda url, client: {
        "issuer": "https://accounts.zoho.in", "authorization_endpoint": "https://accounts.zoho.in/oauth/v2/auth",
        "token_endpoint": "https://accounts.zoho.in/oauth/v2/token"})
    monkeypatch.setattr(mcp_auth, "_register", lambda meta, client: {"client_id": "hoola"})
    with session() as s:
        link = mcp_auth.start(s, "default", "custom:mcp-x", ZURL, client=httpx.Client())
        rows = [r for r in s.query(KVState).all() if r.key.startswith("mcp_state:")]
    assert link.startswith("https://accounts.zoho.in/") and rows
    assert all(KEY not in r.value and "verifier" not in r.value for r in rows)


def test_big_server_shares_budget_and_her_words_pick_tools(zoho):
    from app.agent import mcp_live
    assert mcp_live.shares([300, 5, 20], 40) == [18, 5, 17]
    assert mcp_live.shares([3, 4], 40) == [3, 4] and sum(mcp_live.shares([500, 500], 40)) == 40
    zoho_srv = {"pack_id": "mcp-z", "name": "Zoho", "status": "ready", "tools": ZohoRemote("", {}).list_tools()}
    small = {"pack_id": "mcp-n", "name": "Notion", "status": "ready",
             "tools": [{"name": f"notion_{i}", "description": "", "schema": {}, "tier": 0} for i in range(6)]}
    for t in zoho_srv["tools"]:
        t.update(schema={}, tier=0)
    defs, route = mcp_live.tool_defs([zoho_srv, small], 40, "Zoho Books mein mera profit and loss report dikhao")
    assert len(defs) == 40 and sum(1 for v in route.values() if v[0] == "mcp-n") == 6     # small server keeps all
    zoho_tools = [v[1] for v in route.values() if v[0] == "mcp-z"]
    assert zoho_tools[0] == "get_profit_and_loss_report" and zoho_srv["overflow"]
    block = mcp_live.prompt_block([zoho_srv, small], route)
    assert "bazar_mcp action=tools pack_id=mcp-z" in block
    # no words: the old order (unchanged behaviour for small setups)
    d2, r2 = mcp_live.tool_defs([small], 40)
    assert [v[1] for v in r2.values()] == [f"notion_{i}" for i in range(6)]


def test_tools_action_finds_the_right_tool(zoho):
    import asyncio

    from app.agent.bazar_tools import bazar_mcp
    svc = zoho["svc"]
    out = svc.mcp_connect_featured("default", "zoho-mcp", url=ZURL, probe_client=_probe(200))
    res = svc.mcp_find_tools("default", out["pack_id"], "invoice email karo")
    assert res["total_tools"] == 130 and res["tools"][0]["name"] in ("email_invoice", "list_invoices")
    names = [t["name"] for t in res["tools"]]
    assert "email_invoice" in names and {t["name"]: t["needs_tap"] for t in res["tools"]}["email_invoice"] is True
    assert KEY not in json.dumps(res)

    class Ctx:
        tenant_id, conversation_id = "default", zoho["conv"]
    via_tool = asyncio.run(bazar_mcp(Ctx(), action="tools", pack_id=out["pack_id"], query="profit loss"))
    assert via_tool["tools"][0]["name"] == "get_profit_and_loss_report"
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError):
        svc.mcp_find_tools("someone-else", out["pack_id"], "invoice")


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.329.0"
