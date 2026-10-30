"""v0.183.0 "Gmail settings": vacation / out-of-office auto-reply, the Hoola signature pushed INTO Gmail (sendAs),
send-as aliases (read-only) and Gmail's own auto-forwarding — every change behind a confirm card, every old
mailbox told honestly (ek baar dobara jodiye) because these ride the new gmail.settings.basic scope."""
import json
from datetime import timedelta

import httpx
import pytest

from app.agent.tools import Ctx, ToolError
from app.db import MailAccount, now, session
from app.mailbox import service as ms
from app.mailbox.base import Box, MailError
from app.mailbox.gmail import GmailBox
from tests.test_bazar import _events, _notices, bz  # noqa: F401
from tests.test_email import _mock, run  # noqa: F401
from tests.test_life import conv_ctx


class SettingsBox(GmailBox):
    """A GmailBox that speaks the settings endpoints from memory (no HTTP): vacation, sendAs, autoForwarding."""

    def __init__(self, key="mbx_set", address="meghana@fnw.in"):
        super().__init__(key, address, lambda force: "tok", "Meghana Ingle", "Meghana Ingle\nDirector, FNW")
        self.calls: list[tuple[str, str]] = []
        self.vac = {"enableAutoReply": False, "responseSubject": "", "responseBody": "",
                    "restrictToContacts": False, "restrictToDomain": False, "startTime": "0", "endTime": "0"}
        self.sendas = [{"sendAsEmail": address, "displayName": "Meghana Ingle", "replyToAddress": "", "isPrimary": True,
                        "isDefault": True, "treatAsAlias": False, "verificationStatus": "accepted", "signature": ""},
                       {"sendAsEmail": "hello@newtika.in", "displayName": "Newtika", "replyToAddress": "",
                        "isPrimary": False, "isDefault": False, "treatAsAlias": False,
                        "verificationStatus": "pending", "signature": "<b>Newtika</b>"}]
        self.fwd = {"enabled": False, "emailAddress": "", "disposition": "keep"}

    def _req(self, method, path, **kw):
        p = path.split("?")[0]
        self.calls.append((method, p))
        if method == "GET" and p == "/settings/vacation":
            return dict(self.vac)
        if method == "PUT" and p == "/settings/vacation":
            self.vac.update(kw.get("json") or {})
            return dict(self.vac)
        if method == "GET" and p == "/settings/sendAs":
            return {"sendAs": [dict(sa) for sa in self.sendas]}
        if method == "PATCH" and p.startswith("/settings/sendAs/"):
            em = p.rsplit("/", 1)[-1]
            for sa in self.sendas:
                if sa["sendAsEmail"] == em:
                    sa.update(kw.get("json") or {})
                    return {"sendAsEmail": em}
            raise MailError(f"Gmail error 404: sendAs {em} nahi mila")
        if method == "GET" and p == "/settings/autoForwarding":
            return dict(self.fwd)
        if method == "PUT" and p == "/settings/autoForwarding":
            self.fwd.update(kw.get("json") or {})
            return dict(self.fwd)
        raise MailError(f"SettingsBox: unexpected {method} {p}")


@pytest.fixture
def sbox(bz, monkeypatch):  # noqa: F811
    """The settings box, connected with a row that carries BOTH scopes (v0.183.0 consent)."""
    import app.mailbox.accounts as ma
    b = SettingsBox()
    with session() as s:
        s.add(MailAccount(id="mbx_set", tenant_id="default", kind="gmail", address="meghana@fnw.in",
                          scopes=f"{ma.GMAIL_SCOPE} {ma.SETTINGS_SCOPE}"))
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    return b


# ---------------- vacation ----------------
def test_vacation_get_and_set_behind_card(sbox, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("email_vacation", {"action": "get"}, ctx)
    assert out["scope_ok"] is True and out["vacation"]["on"] is False
    with pytest.raises(ToolError, match="message do"):
        run("email_vacation", {"action": "set", "enable": True}, ctx)
    end = (now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    out = run("email_vacation", {"action": "set", "enable": True,
                                 "message": "Ek hafte tak bahar hoon. Biz ke liye Swati se baat karo.",
                                 "subject": "Out of office", "end": end}, ctx)
    assert out["needs_approval"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Vacation reply chalu karein?"
    flat = json.dumps(card).lower()
    assert "bahar hoon" in flat and "har mail" in flat and "out of office" in flat
    assert sbox.vac["enableAutoReply"] is False                       # kuch nahi badla, pehle manzoori
    assert not any(m == "PUT" and p == "/settings/vacation" for m, p in sbox.calls)
    bz["svc"].decide("default", card["id"], "approve")
    assert sbox.vac["enableAutoReply"] is True
    assert "bahar hoon" in sbox.vac["responseBody"] and sbox.vac["responseSubject"] == "Out of office"
    assert int(sbox.vac["startTime"]) > 0 and int(sbox.vac["endTime"]) > 0
    assert sbox.vac["restrictToContacts"] is False
    got = run("email_vacation", {"action": "get"}, ctx)
    assert got["vacation"]["on"] is True and got["vacation"]["end"]   # the window comes back as a local-time label
    out = run("email_vacation", {"action": "set", "enable": False}, ctx)   # band karna bhi card se
    assert out["needs_approval"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Vacation reply band karein?"
    bz["svc"].decide("default", card["id"], "approve")
    assert sbox.vac["enableAutoReply"] is False


def test_vacation_window_contacts_and_scope_guards(sbox, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    with pytest.raises(MailError, match="baad ka time"):
        ms.vacation_set("default", "mbx_set", True, "msg", start="2027-01-25T18:00", end="2027-01-25T09:00")
    out = run("email_vacation", {"action": "set", "enable": True, "message": "Chhutti par hoon",
                                 "contacts_only": True}, ctx)
    assert out["needs_approval"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert "saved contacts" in json.dumps(card)
    # an old mailbox (linked before v0.183.0: no settings scope) is told honestly — no card, no doomed API call
    with session() as s:
        s.get(MailAccount, "mbx_set").scopes = "https://www.googleapis.com/auth/gmail.modify"
    got = run("email_vacation", {"action": "get"}, conv_ctx())
    assert got["scope_ok"] is False and "dobara jod" in got["note"]
    before = len(sbox.calls)
    blocked = run("email_vacation", {"action": "set", "enable": True, "message": "x"}, conv_ctx())
    assert blocked["scope_ok"] is False and "dobara jod" in blocked["note"]
    assert len(sbox.calls) == before and sbox.vac["enableAutoReply"] is False
    with pytest.raises(MailError, match="dobara jod"):
        ms.signature_push("default", "mbx_set", "sig")
    with pytest.raises(MailError, match="dobara jod"):
        ms.auto_forwarding_set("default", "mbx_set", True, "ca@newtika.in")


# ---------------- signature into Gmail + send-as aliases ----------------
def test_signature_push_and_aliases(sbox, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("email_accounts", {"send_as": True}, ctx)
    st = out["settings"]
    assert [a["email"] for a in st["aliases"]] == ["meghana@fnw.in", "hello@newtika.in"]
    assert st["aliases"][0]["primary"] is True and st["aliases"][1]["verified"] is False   # alias pending
    assert st["aliases"][1]["has_signature"] is True
    assert st["forwarding"]["enabled"] is False
    sbox.signature = "Meghana <b>FNW</b>\nDirector, FNW"
    out = run("email_accounts", {"signature_push": True}, ctx)
    assert out["needs_approval"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Signature Gmail mein daalein?" and "Director, FNW" in json.dumps(card)
    assert not any(m == "PATCH" for m, _ in sbox.calls)               # sirf manzoori ke baad
    bz["svc"].decide("default", card["id"], "approve")
    assert ("PATCH", "/settings/sendAs/meghana@fnw.in") in sbox.calls  # the PRIMARY sendAs, not the alias
    pushed = sbox.sendas[0]["signature"]
    assert "<br>" in pushed and "&lt;b&gt;FNW&lt;/b&gt;" in pushed    # text goes as escaped HTML, never raw tags
    out = run("email_accounts", {"signature_push": True}, ctx)
    assert out["needs_approval"]


# ---------------- Gmail's own auto-forward ----------------
def test_auto_forward_card_and_off(sbox, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("email_accounts", {"auto_forward": "ca@newtika.in"}, ctx)
    assert out["needs_approval"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Auto-forward chalu karein?" and "ca@newtika.in" in json.dumps(card)
    assert sbox.fwd["enabled"] is False
    bz["svc"].decide("default", card["id"], "approve")
    assert sbox.fwd == {"enabled": True, "emailAddress": "ca@newtika.in", "disposition": "keep"}
    out = run("email_accounts", {"auto_forward": "off"}, ctx)
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Auto-forward band karein?"
    bz["svc"].decide("default", card["id"], "approve")
    assert sbox.fwd["enabled"] is False and sbox.fwd["emailAddress"] == "ca@newtika.in"
    with pytest.raises(ToolError, match="address"):
        run("email_accounts", {"auto_forward": "not-an-email"}, ctx)


# ---------------- plumbing: Gmail-only, new consent carries the scope, API endpoint ----------------
def test_settings_need_a_gmail_box(env, monkeypatch):
    b = Box("mbx_x", "office@newtika.in")
    import app.mailbox.accounts as ma
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    with pytest.raises(MailError, match="Gmail"):
        ms.settings_status("default")
    with pytest.raises(MailError, match="Gmail"):
        ms.vacation_set("default", "mbx_x", False)


def test_oauth_link_asks_settings_scope_and_finish_stores_it(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.mailbox import accounts as ma
    assert ma.SETTINGS_SCOPE in ma.GMAIL_SCOPES                       # the new consent asks for it

    def handler(req: httpx.Request):
        if req.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at1", "refresh_token": "rt1", "expires_in": 3600,
                                             "scope": f"openid email profile {ma.GMAIL_SCOPE} {ma.SETTINGS_SCOPE}"})
        if req.url.host == "openidconnect.googleapis.com":
            return httpx.Response(200, json={"email": "me@gmail.com", "name": "Meghana"})
        raise AssertionError(req.url.host)
    ma.set_http(_mock(handler))
    try:
        url = ma.start_link("default", "google")
        assert ma.SETTINGS_SCOPE in httpx.URL(url).params["scope"].split()   # consent URL carries the settings scope
        state = httpx.URL(url).params["state"]
        ma.finish_link("c0de", state)
        bs = ma.boxes("default")
        assert bs[0].address == "me@gmail.com" and bs[0].kind == "gmail"
        assert ma.settings_scope_ok("default", bs[0]) is True
        with session() as s:                                          # an old token keeps working for MAIL...
            s.get(MailAccount, bs[0].key).scopes = ma.GMAIL_SCOPE
        assert ma.settings_scope_ok("default", bs[0]) is False        # ...but settings need the one-time reconnect
        assert "dobara jod" in ma.settings_scope_message("me@gmail.com")
    finally:
        ma.set_http(None)
        get_settings.cache_clear()


def test_google_check_sees_the_settings_feature():
    from app.google_check import FEATURES
    assert FEATURES["gmail_settings"] == "https://www.googleapis.com/auth/gmail.settings.basic"


def test_api_mail_settings_endpoint(sbox):  # noqa: F811
    from app import main
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        out = c.get("/api/mail/settings").json()
        assert out["account"] == "meghana@fnw.in" and out["scope_ok"] is True
        assert out["vacation"]["on"] is False and len(out["aliases"]) == 2
        assert out["forwarding"]["enabled"] is False


# ---------------- version ----------------
def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.292.0"
