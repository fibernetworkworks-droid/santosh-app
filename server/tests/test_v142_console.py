"""v0.142 Hoola Console: web logins (Hoola ID + console password, Google one-time code), console read views, the page."""
import asyncio
import re
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

KEY = "owner-key-for-console-tests"


@pytest.fixture
def con(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    monkeypatch.setenv("SECRET_KEY", "a-very-long-random-secret-for-tests-0123456789")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://hoola.example.in")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csecret")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    from app.console import service as cs
    cs._IP_FAILS.clear()
    with TestClient(main.app) as c:
        yield c, get_settings()
    get_settings.cache_clear()


def owner(c):
    return {"Authorization": f"Bearer {KEY}"}


def test_password_login_end_to_end(con):
    c, st = con
    me = c.get("/api/console/me", headers=owner(c)).json()
    assert me["tenant"] == st.tenant_id and me["handle"].startswith("@") and me["has_password"] is False
    handle = me["handle"]
    # rules: length, too simple
    assert c.put("/api/console/password", json={"password": "short"}, headers=owner(c)).status_code == 400
    assert c.put("/api/console/password", json={"password": "aaaaaaaaaaaa"}, headers=owner(c)).status_code == 400
    r = c.put("/api/console/password", json={"password": "Chai-Galla-2026!"}, headers=owner(c))
    assert r.status_code == 200 and r.json()["handle"] == handle
    # changing it needs the current one
    assert c.put("/api/console/password", json={"password": "Naya-Password-77"}, headers=owner(c)).status_code == 403
    # the hash is scrypt, never the password
    from app.console.service import ConsoleLogin
    from app.db import session
    with session() as s:
        row = s.get(ConsoleLogin, st.tenant_id)
        assert row and "Chai" not in row.pw_hash and len(row.pw_hash) == 64 and len(row.salt) == 32

    # login with the handle (with or without @), the session works like the phone's
    r = c.post("/api/console/login", json={"handle": handle.lstrip("@").upper(), "password": "Chai-Galla-2026!"})
    assert r.status_code == 200, r.text
    tok = r.json()["session_token"]
    H = {"Authorization": f"Bearer {tok}"}
    assert c.get("/api/console/me", headers=H).json()["tenant"] == st.tenant_id
    conv = c.post("/api/conversations", headers=H).json()["id"]
    assert c.get(f"/api/conversations/{conv}/messages", headers=H).status_code == 200
    # she is told about every console login in her chat
    from app.db import Message
    from sqlalchemy import select
    with session() as s:
        assert any("Hoola Console mein" in (m.display or "") for m in s.scalars(select(Message)).all())

    # a wrong password and an unknown ID give the same answer
    bad = c.post("/api/console/login", json={"handle": handle, "password": "nahi-pata-hai"})
    unknown = c.post("/api/console/login", json={"handle": "@koi.aur.nahi", "password": "nahi-pata-hai"})
    assert bad.status_code == unknown.status_code == 401 and bad.json()["detail"] == unknown.json()["detail"]
    # 5 wrong tries lock the ID (even the right password waits)
    for _ in range(4):
        c.post("/api/console/login", json={"handle": handle, "password": "galat-password-1"})
    locked = c.post("/api/console/login", json={"handle": handle, "password": "Chai-Galla-2026!"})
    assert locked.status_code == 429
    # logout ends that session
    assert c.post("/api/logout", headers=H).status_code == 200
    assert c.get("/api/console/me", headers=H).status_code == 401


def test_ip_limit_and_password_removal(con):
    c, st = con
    from app.console import service as cs
    ip = {"X-Real-IP": "49.36.120.20"}
    for i in range(cs.IP_LIMIT):
        c.post("/api/console/login", json={"handle": f"@nobody{i}", "password": "x" * 12}, headers=ip)
    assert c.post("/api/console/login", json={"handle": "@nobody", "password": "x" * 12}, headers=ip).status_code == 429
    # a faked X-Forwarded-For doesn't get around it, and a proxy without X-Real-IP (127.0.0.1) never blocks everyone
    assert c.post("/api/console/login", json={"handle": "@nobody", "password": "x" * 12},
                  headers={**ip, "X-Forwarded-For": "198.51.100.9"}).status_code == 429
    assert c.post("/api/console/login", json={"handle": "@nobody", "password": "x" * 12}).status_code == 401
    cs._IP_FAILS.clear()
    c.put("/api/console/password", json={"password": "Pehla-Password-1"}, headers=owner(c))
    assert c.put("/api/console/password", json={"remove": True, "current": "galat"}, headers=owner(c)).status_code == 403
    assert c.put("/api/console/password", json={"remove": True, "current": "Pehla-Password-1"}, headers=owner(c)).json()["removed"]
    assert c.get("/api/console/me", headers=owner(c)).json()["has_password"] is False


def test_google_web_signin_gives_one_time_code(con, monkeypatch):
    c, st = con
    from app import accounts
    url = accounts.start_google(web=True)
    state = url.split("state=")[1]
    assert state.startswith("cw_")
    r = c.get("/auth/google/start?web=1", follow_redirects=False)
    assert r.status_code in (302, 307) and "state=cw_" in r.headers["location"]

    def handler(req: httpx.Request):
        if req.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "A1", "refresh_token": "R1", "expires_in": 3600,
                                             "scope": " ".join(accounts.GOOGLE_SCOPES)})
        return httpx.Response(200, json={"email": "priya@example.com", "name": "Priya", "sub": "g-1"})
    real = httpx.AsyncClient
    monkeypatch.setattr(accounts.httpx, "AsyncClient", lambda **k: real(transport=httpx.MockTransport(handler)))
    r = c.get(f"/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code in (302, 307)
    loc = r.headers["location"]
    assert loc.startswith("/console/?code=") and r.headers.get("referrer-policy") == "no-referrer"
    code = loc.split("code=")[1]
    assert "session" not in loc
    tok = c.post("/api/console/exchange", json={"code": code}).json()["session_token"]
    me = c.get("/api/console/me", headers={"Authorization": f"Bearer {tok}"}).json()
    assert me["email"] == "priya@example.com" and me["tenant"] != st.tenant_id      # her own Hoola, not the owner's
    # the code works once
    assert c.post("/api/console/exchange", json={"code": code}).status_code == 401
    # an old code is refused
    from app.console import service as cs
    from app.db import session
    from datetime import timedelta
    code2 = cs.issue_code("tok-xyz")
    with session() as s:
        row = s.get(cs.ConsoleCode, cs._sha(code2))
        row.created_at = row.created_at - timedelta(minutes=5)
    assert c.post("/api/console/exchange", json={"code": code2}).status_code == 401
    # the phone flow is unchanged (deep link, no console code)
    st2 = accounts.start_google().split("state=")[1]
    assert not st2.startswith("cw_")
    r = c.get(f"/auth/google/callback?code=abc&state={st2}", follow_redirects=False)
    assert r.status_code == 200 and "://auth?session=" in r.text


def test_conversations_recent_and_isolation(con):
    c, st = con
    H = owner(c)
    a = c.post("/api/conversations", headers=H).json()["id"]
    b = c.post("/api/conversations", headers=H).json()["id"]
    from app.db import Message, session
    from app.events import bus
    with session() as s:
        s.add(Message(conversation_id=a, role="user", content="GST bana do", display="October ka GST bana do"))
    bus.publish(a, "email_draft", {"id": "d1", "subject": "v1", "status": "pending"})
    bus.publish(a, "email_draft", {"id": "d1", "subject": "v2", "status": "pending"})
    bus.publish(a, "step", {"tool": "gst", "state": "done", "id": "x"})
    convs = c.get("/api/console/conversations", headers=H).json()["conversations"]
    ids = [x["id"] for x in convs]
    assert a in ids and b in ids
    ca = next(x for x in convs if x["id"] == a)
    assert ca["title"] == "October ka GST bana do" and ca["empty"] is False
    assert next(x for x in convs if x["id"] == b)["empty"] is True
    rec = c.get(f"/api/console/conversations/{a}/recent", headers=H).json()
    assert rec["last_event_id"] > 0
    drafts = [x for x in rec["cards"] if x["kind"] == "email_draft"]
    assert len(drafts) == 1 and drafts[0]["payload"]["subject"] == "v2"            # newest state per card
    assert not any(x["kind"] in ("step", "message") for x in rec["cards"])
    # another person's session can't see or open these chats
    from app import accounts
    from app.db import User
    with session() as s:
        u = User(email="other@example.com", name="Other")
        s.add(u)
        s.flush()
        uid = u.id
    O = {"Authorization": f"Bearer {accounts.issue_session(uid)}"}
    assert a not in [x["id"] for x in c.get("/api/console/conversations", headers=O).json()["conversations"]]
    assert c.get(f"/api/console/conversations/{a}/recent", headers=O).status_code == 404
    assert c.get("/api/console/conversations").status_code == 401


def test_pending_and_today(con):
    c, st = con
    from app.db import ListItem, session
    from app.employee.models import EmployeeAsk
    with session() as s:
        s.add(EmployeeAsk(tenant_id=st.tenant_id, tool="email_draft", duty="email", why="customer ne maanga", args="{}"))
        s.add(ListItem(tenant_id=st.tenant_id, list_name="shopping", text="Doodh"))
    p = c.get("/api/console/pending", headers=owner(c)).json()["pending"]
    assert any(x["kind"] == "employee_ask" and x["money"] is False for x in p)
    t = c.get("/api/console/today", headers=owner(c)).json()
    assert t["lists"]["shopping"][0]["text"] == "Doodh" and len(t["pending"]) == len(p)


def test_console_page_and_assets(con):
    c, st = con
    r = c.get("/console/")
    assert r.status_code == 200 and "Hoola Console" in r.text
    csp = r.headers["content-security-policy"]
    assert "script-src 'self';" in csp and "frame-ancestors 'none'" in csp and "connect-src 'self'" in csp
    assert r.headers["x-frame-options"] == "DENY" and r.headers["referrer-policy"] == "no-referrer"
    # no inline script: every <script> has a src on this server
    for tag in re.findall(r"<script[^>]*>", r.text):
        assert 'src="/static/console/' in tag
    for f in ("app.js", "app.css", "kaam.js"):
        assert c.get(f"/static/console/{f}").status_code == 200
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "app.js").read_text()
    assert "eval(" not in js and "innerHTML = p." not in js and "hoola-key." in js and "/api/console/exchange" in js
    cfg = c.get("/api/console/config").json()
    assert cfg["google"] is True and cfg["password"] is True and cfg["version"] == "0.142.0"
    kaam = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "kaam.js").read_text()
    assert kaam.count("[\"") > 80


def test_voice_socket_takes_the_token_as_subprotocol(con):
    c, st = con
    from app import accounts
    conv = c.post("/api/conversations", headers=owner(c)).json()["id"]
    tok = accounts.issue_session(st.tenant_id)
    with c.websocket_connect(f"/api/voice/ws?conv={conv}", subprotocols=["hoola", "hoola-key." + tok]) as ws:
        assert ws.accepted_subprotocol == "hoola"
        msg = ws.receive_json()
        assert msg["type"] == "error"            # no GEMINI_API_KEY in tests: the call itself can't start
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect) as e:
        with c.websocket_connect(f"/api/voice/ws?conv={conv}", subprotocols=["hoola", "hoola-key.galat"]) as ws:
            ws.receive_json()
    assert e.value.code == 4401
