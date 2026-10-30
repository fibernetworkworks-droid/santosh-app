"""v0.276 COMPOSIO: one Newtika project, every user her own app accounts - isolation, cards, caps, expiry."""
import base64
import hashlib
import hmac
import json
import time

import httpx
import pytest
from sqlalchemy import select

ACCOUNTS = {}   # ca id -> status, the fake Composio's own state


def _fake_composio(calls):
    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path.removeprefix("/api/v3.1")
        body = json.loads(req.content) if req.content else {}
        calls.append((req.method, path, dict(req.url.params), body, req.headers.get("x-api-key")))
        if path == "/auth_configs" and req.method == "GET":
            return httpx.Response(200, json={"items": [{"id": f"ac_{req.url.params['toolkit_slug']}",
                                                        "status": "ENABLED",
                                                        "toolkit": {"slug": req.url.params["toolkit_slug"]}}]})
        if path == "/connected_accounts/link":
            ca = f"ca_{len(ACCOUNTS) + 1}"
            ACCOUNTS[ca] = "INITIATED"
            return httpx.Response(201, json={"redirect_url": f"https://connect.composio.dev/link/{ca}",
                                             "connected_account_id": ca, "link_token": "lt"})
        if path.startswith("/connected_accounts/") and req.method == "GET":
            ca = path.rsplit("/", 1)[1]
            return httpx.Response(200, json={"id": ca, "status": ACCOUNTS.get(ca, "FAILED")})
        if path.startswith("/connected_accounts/") and req.method == "DELETE":
            ACCOUNTS.pop(path.rsplit("/", 1)[1], None)
            return httpx.Response(200, json={})
        if path == "/tools":
            kit = req.url.params["toolkit_slug"]
            return httpx.Response(200, json={"items": [
                {"slug": f"{kit.upper()}_LIST_ALL_CHANNELS", "name": "List channels", "description": "list",
                 "input_parameters": {"type": "object", "properties": {}}, "toolkit": {"slug": kit}},
                {"slug": f"{kit.upper()}_SEND_MESSAGE", "name": "Send message", "description": "send",
                 "input_parameters": {"type": "object", "properties": {"channel": {"type": "string"},
                                                                         "text": {"type": "string"}}},
                 "toolkit": {"slug": kit}}]})
        if path.startswith("/tools/execute/"):
            ca = body.get("connected_account_id")
            if ACCOUNTS.get(ca) == "EXPIRED":
                return httpx.Response(401, json={"error": {"message": "Connected account expired"}})
            return httpx.Response(200, json={"successful": True, "error": None,
                                             "data": {"ok": True, "slug": path.rsplit("/", 1)[1]}})
        if path.startswith("/tools/"):
            slug = path.rsplit("/", 1)[1]
            kit = slug.split("_", 1)[0].lower()
            return httpx.Response(200, json={"slug": slug, "name": slug.title(), "toolkit": {"slug": kit}})
        return httpx.Response(404, json={"error": {"message": "not found"}})
    return handler


@pytest.fixture
def cz(env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://hoola.example.in")
    monkeypatch.setenv("BAZAR_ENV", "dev")
    monkeypatch.setenv("COMPOSIO_API_KEY", "ak_test_project")
    monkeypatch.setenv("COMPOSIO_WEBHOOK_SECRET", "whsec_" + base64.b64encode(b"hook-secret").decode())
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bazar import composio, config as bzc, security, service
    bzc.reset_settings()
    security._vault = None
    service.set_executors(None)
    ACCOUNTS.clear()
    calls = []
    st = get_settings()
    composio.set_client(composio.Client(st.composio_api_key, st.composio_base_url,
                                        http=httpx.Client(transport=httpx.MockTransport(_fake_composio(calls)))))
    from app.db import Conversation, session
    convs = {}
    with session() as s:
        for t in ("default", "other"):
            c = Conversation(tenant_id=t)
            s.add(c)
            s.flush()
            convs[t] = c.id
    yield {"svc": service, "cmp": composio, "calls": calls, "conv": convs}
    composio.set_client(None)
    get_settings.cache_clear()
    bzc.reset_settings()
    security._vault = None
    service.set_executors(None)


def _link(cz, tenant="default", kit="slack"):
    out = cz["svc"].composio_connect(tenant, kit, cz["conv"][tenant])
    ca = out["url"].rsplit("/", 1)[1]
    ACCOUNTS[ca] = "ACTIVE"            # she finished the sign-in on Slack's page
    return out, ca


def test_users_never_need_a_composio_account_and_user_id_is_server_made(cz):
    out, ca = _link(cz)
    assert out["status"] == "open_link" and out["url"].startswith("https://connect.composio.dev/")
    link = [c for c in cz["calls"] if c[1] == "/connected_accounts/link"][0]
    assert link[3]["user_id"] == cz["cmp"].composio_user("default") != "default"
    assert link[3]["callback_url"].startswith("https://hoola.example.in/bazar/composio/callback?st=")
    assert link[4] == "ak_test_project"           # Newtika's one project key, nothing from the user
    from app.db import Event, session
    with session() as s:
        ev = s.scalars(select(Event).where(Event.conversation_id == cz["conv"]["default"],
                                           Event.kind == "bazar_open")).first()
    assert ev and ev.payload["url"] == out["url"]
    apps = {a["toolkit"]: a["status"] for a in cz["svc"].composio_apps("default")["apps"]}
    assert apps["slack"] == "ready" or apps["slack"] == "pending"


def test_read_runs_with_her_own_account_only(cz):
    _, ca = _link(cz)
    res = cz["svc"].run("default", cz["conv"]["default"], "cmp-slack", "SLACK_LIST_ALL_CHANNELS",
                        {"user_id": "someone-else", "connected_account_id": "ca_999"})
    assert res["data"]["ok"] is True and "instructions" in res["note"]
    ex = [c for c in cz["calls"] if c[1].startswith("/tools/execute/")][-1]
    assert ex[3]["user_id"] == cz["cmp"].composio_user("default")
    assert ex[3]["connected_account_id"] == ca     # args can never pick another account or user
    assert ex[3]["arguments"] == {"user_id": "someone-else", "connected_account_id": "ca_999"}


def test_other_tenant_cannot_use_her_slack(cz):
    _link(cz, "default")
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="juda nahi"):
        cz["svc"].run("other", cz["conv"]["other"], "cmp-slack", "SLACK_LIST_ALL_CHANNELS", {})
    assert not [c for c in cz["calls"] if c[1].startswith("/tools/execute/")]


def test_send_is_a_card_and_runs_the_frozen_call_after_her_tap(cz):
    _, ca = _link(cz)
    res = cz["svc"].run("default", cz["conv"]["default"], "cmp-slack", "SLACK_SEND_MESSAGE",
                        {"channel": "#sales", "text": "Kal 11 baje meeting"})
    assert res["needs_approval"] is True
    assert not [c for c in cz["calls"] if c[1].startswith("/tools/execute/")]
    out = cz["svc"].decide("default", res["approval_id"], "approve")
    assert out["status"] == "approved" and out["outcome"]["status"] == "done"
    ex = [c for c in cz["calls"] if c[1].startswith("/tools/execute/")]
    assert len(ex) == 1 and ex[0][1].endswith("SLACK_SEND_MESSAGE")
    assert ex[0][3]["arguments"] == {"channel": "#sales", "text": "Kal 11 baje meeting"}


def test_tool_of_another_app_is_refused(cz):
    _link(cz)
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="ka tool nahi"):
        cz["svc"].run("default", cz["conv"]["default"], "cmp-slack", "NOTION_DELETE_PAGE", {})


def test_monthly_cap_per_user(cz, monkeypatch):
    monkeypatch.setenv("COMPOSIO_USER_MONTHLY_CALLS", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    _link(cz)
    cz["svc"].run("default", cz["conv"]["default"], "cmp-slack", "SLACK_LIST_ALL_CHANNELS", {})
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="poore ho gaye"):
        cz["svc"].run("default", cz["conv"]["default"], "cmp-slack", "SLACK_LIST_ALL_CHANNELS", {})
    assert cz["svc"].composio_apps("default")["calls_this_month"] == 1


def test_hoola_own_and_scraping_apps_never_offered(cz, monkeypatch):
    monkeypatch.setenv("COMPOSIO_TOOLKITS", "gmail, slack, apify, github")
    from app.config import get_settings
    get_settings.cache_clear()
    assert list(cz["cmp"].toolkits()) == ["slack"]
    from app.bazar.packs.registry import registry
    assert registry().lookup("cmp-gmail") is None and registry().lookup("cmp-slack").executor == "composio"


def test_read_or_write_words():
    from app.bazar.composio import is_read
    assert is_read("SLACK_LIST_ALL_CHANNELS", "slack") and is_read("NOTION_FETCH_DATA", "notion")
    assert is_read("JIRA_GET_ISSUE", "jira")
    for s in ("SLACK_SEND_MESSAGE", "NOTION_DELETE_BLOCK", "JIRA_GET_AND_UPDATE_ISSUE", "HUBSPOT_CREATE_CONTACT",
              "SLACK_CHAT_POST_MESSAGE", "TRELLO_ADD_CARD"):
        assert not is_read(s, s.split("_")[0].lower()), s


def test_expired_sign_in_closes_the_link(cz):
    _, ca = _link(cz)
    cz["svc"].run("default", cz["conv"]["default"], "cmp-slack", "SLACK_LIST_ALL_CHANNELS", {})   # becomes active
    ACCOUNTS[ca] = "EXPIRED"                                                                       # Slack revoked it
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="sign-in khatam"):
        cz["svc"].run("default", cz["conv"]["default"], "cmp-slack", "SLACK_LIST_ALL_CHANNELS", {})
    assert {a["toolkit"]: a["status"] for a in cz["svc"].composio_apps("default")["apps"]}["slack"] == "needs_link"


def test_webhook_signature_and_expiry_event(cz):
    _, ca = _link(cz)
    cz["svc"].run("default", cz["conv"]["default"], "cmp-slack", "SLACK_LIST_ALL_CHANNELS", {})   # becomes active
    raw = json.dumps({"type": "composio.connected_account.expired", "data": {"id": ca}}).encode()
    ts = str(int(time.time()))
    sig = base64.b64encode(hmac.new(b"hook-secret", f"evt_1.{ts}.".encode() + raw, hashlib.sha256).digest()).decode()
    assert cz["cmp"].verify_webhook(raw, "evt_1", ts, f"v1,{sig}")
    assert not cz["cmp"].verify_webhook(raw, "evt_1", ts, "v1,AAAA")
    assert not cz["cmp"].verify_webhook(raw, "evt_1", str(int(time.time()) - 900), f"v1,{sig}")
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    assert c.post("/bazar/composio/webhook", content=raw, headers={"webhook-id": "evt_1", "webhook-timestamp": ts,
                                                                   "webhook-signature": "v1,bad"}).status_code == 401
    r = c.post("/bazar/composio/webhook", content=raw, headers={"webhook-id": "evt_1", "webhook-timestamp": ts,
                                                                "webhook-signature": f"v1,{sig}"})
    assert r.status_code == 200
    assert {a["toolkit"]: a["status"] for a in cz["svc"].composio_apps("default")["apps"]}["slack"] == "needs_link"


def test_callback_trusts_only_its_signed_state(cz):
    _link(cz)
    st = cz["cmp"]._state("default", "slack")
    name, ok = cz["svc"].composio_callback(st)
    assert name == "Slack" and ok
    from app.bazar.connectors.base import ToolError
    forged = base64.urlsafe_b64encode(b"other|slack|9999999999|deadbeef").decode()
    with pytest.raises(ToolError, match="purana ya galat"):
        cz["svc"].composio_callback(forged)


def test_disconnect_deletes_at_composio(cz):
    _, ca = _link(cz)
    assert cz["svc"].composio_remove("default", "slack") is True
    assert ca not in ACCOUNTS
    assert {a["toolkit"]: a["status"] for a in cz["svc"].composio_apps("default")["apps"]}["slack"] == "needs_link"


def test_not_configured_says_so(env, monkeypatch):
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bazar import composio, service
    composio.set_client(None)
    assert service.composio_apps("default")["configured"] is False
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="chalu nahi"):
        service.composio_connect("default", "slack")
