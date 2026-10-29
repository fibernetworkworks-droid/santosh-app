"""v0.184.0 "Gmail polish": saved searches (email_rule kind=search — the watcher never touches them), the weekly
inbox digest, sending FROM a verified Gmail send-as alias, Gmail's own snoozed folder, and labels with nesting
(Office/Clients) + colours. Every safety rule intact: a saved search only lists, an alias send still waits for Bhejo,
and star colours are honestly impossible through Google's API."""
import json

import pytest

from app.agent.tools import Ctx, ToolError
from app.db import MailAccount, now, session
from app.mailbox import service as ms
from app.mailbox.base import Box, MailError
from app.mailbox.gmail import FOLDER_Q, GmailBox
from tests.test_bazar import _events, bz  # noqa: F401
from tests.test_email import FakeBox, _raw, run  # noqa: F401
from tests.test_email_phase3 import SettingsBox
from tests.test_life import conv_ctx


class AliasBox(SettingsBox):
    """The settings box + a send() that records the MIME message (nothing actually leaves)."""

    def __init__(self, key="mbx_alias", address="meghana@fnw.in"):
        super().__init__(key, address)
        self.sent = []

    def send(self, msg, thread_id=None):
        self.sent.append(msg)
        return {"message_id": msg["Message-ID"], "thread_id": thread_id or "tnew"}


class RecBox(FakeBox):
    """FakeBox that records its list() calls — saved searches must pass the query through verbatim."""

    def __init__(self, key="mbx_test", address="meghana@fnw.in"):
        super().__init__(key, address)
        self.list_calls = []

    def list(self, folder="inbox", unread_only=False, search=None, limit=10, since=None, snippets=False):
        self.list_calls.append({"folder": folder, "search": search, "unread": bool(unread_only), "limit": limit})
        return super().list(folder, unread_only, search, limit, since, snippets)


class LabelBox(GmailBox):
    """A GmailBox that speaks /labels from memory: list, create (nesting) and PATCH (colour)."""

    def __init__(self, key="mbx_lab", address="meghana@fnw.in"):
        super().__init__(key, address, lambda force: "tok", "Meghana", "")
        self.labels = [{"id": "L_INBOX", "name": "INBOX", "type": "system", "labelListVisibility": "labelShow"},
                       {"id": "L1", "name": "Office", "type": "user",
                        "color": {"backgroundColor": "#4986e7", "textColor": "#ffffff"}},
                       {"id": "L2", "name": "Office/Clients", "type": "user"}]
        self.patches = []
        self.creates = []

    def _req(self, method, path, **kw):
        p = path.split("?")[0]
        if method == "GET" and p == "/labels":
            return {"labels": [dict(x) for x in self.labels]}
        if method == "POST" and p == "/labels":
            self.creates.append(kw["json"]["name"])
            row = {"id": f"L{len(self.labels) + 1}", "name": kw["json"]["name"], "type": "user"}
            self.labels.append(row)
            return dict(row)
        if method == "PATCH" and p.startswith("/labels/"):
            lid = p.rsplit("/", 1)[-1]
            self.patches.append((lid, kw.get("json") or {}))
            for r in self.labels:
                if r["id"] == lid:
                    r.update(kw.get("json") or {})
                    return dict(r)
            raise MailError("Gmail error 404: label nahi mila")
        raise MailError(f"LabelBox: unexpected {method} {p}")


# ---------------- saved searches (email_rule kind=search) ----------------
@pytest.fixture
def rbox(env, monkeypatch):
    b = RecBox()
    b.add("201", _raw(("HDFC Bank", "alerts@hdfcbank.net"), "meghana@fnw.in", "Your March statement",
                      "Your monthly statement is ready. Invoice attached for your account.", msgid="<h1@hdfc.net>"),
          unread=True)
    b.add("202", _raw(("Zomato", "promo@zomato.com"), "meghana@fnw.in", "Diwali offers inside",
                      "50% off this week only, order now!", msgid="<z1@zomato.com>"), unread=False)
    import app.mailbox.accounts as ma
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    return b


def test_saved_search_save_run_and_delete(rbox):
    ctx = Ctx("default", conv_ctx().conversation_id)
    out = run("email_rule", {"action": "create", "kind": "search", "name": "Bank mails",
                             "match": {"from": "hdfcbank"}}, ctx)
    assert out["kind"] == "search" and out["actions"] == {}
    with pytest.raises(ToolError, match="Kya dhoondhna hai"):
        run("email_rule", {"action": "create", "kind": "search", "name": "khaali", "match": {}}, ctx)
    lst = run("email_rule", {"action": "searches"}, ctx)
    assert [s["name"] for s in lst["searches"]] == ["Bank mails"]
    assert run("email_rule", {"action": "list"}, ctx)["rules"] == []          # the watcher list stays clean
    hit = run("email_rule", {"action": "run", "rule_id": out["id"]}, ctx)
    assert hit["count"] == 1 and hit["emails"][0]["id"] == "mbx_test~201"
    assert hit["emails"][0]["subject"] == "Your March statement"
    assert rbox.list_calls[-1]["folder"] == "inbox" and not rbox.list_calls[-1]["search"]
    assert rbox.msgs["201"]["unread"] is True                                 # a run changes nothing
    # a raw Gmail query goes through verbatim, on the search folder
    q = run("email_rule", {"action": "create", "kind": "search", "name": "Q",
                           "match": {"query": "from:hdfcbank has:attachment"}}, ctx)
    run("email_rule", {"action": "run", "rule_id": q["id"]}, ctx)
    assert rbox.list_calls[-1] == {"folder": "search", "search": "from:hdfcbank has:attachment",
                                   "unread": False, "limit": 15}
    with pytest.raises(ToolError, match="saved search nahi mila"):
        run("email_rule", {"action": "run", "rule_id": "rule_none"}, ctx)
    # the watcher engine never sees a saved search
    from app.mailbox import sync
    rule = sync.rule_create("default", "Bank rule", {"from": "hdfcbank"}, {"label": "Bills"})
    assert [r.id for r in sync.rules_for("default")] == [rule["id"]]
    assert [r["id"] for r in sync.rules_list("default")] == [rule["id"]]
    assert run("email_rule", {"action": "delete", "rule_id": out["id"]}, ctx)["deleted"]
    left = run("email_rule", {"action": "searches"}, ctx)["searches"]
    assert [s["id"] for s in left] == [q["id"]]


def test_saved_search_gmail_syntax_on_non_gmail(env, monkeypatch):
    b = Box("mbx_x", "office@newtika.in")                       # kind = base: no Gmail query language
    import app.mailbox.accounts as ma
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    ctx = Ctx("default", conv_ctx().conversation_id)
    out = run("email_rule", {"action": "create", "kind": "search", "name": "Q", "match": {"query": "from:bank"}}, ctx)
    from app.mailbox import sync
    with pytest.raises(MailError, match="Gmail ke apne syntax"):
        sync.search_run("default", out["id"])


def test_api_mail_rules_lists_searches(rbox):
    from app import main
    from fastapi.testclient import TestClient
    ctx = Ctx("default", conv_ctx().conversation_id)
    run("email_rule", {"action": "create", "kind": "search", "name": "Bank mails", "match": {"from": "hdfcbank"}}, ctx)
    with TestClient(main.app) as c:
        out = c.get("/api/mail/rules").json()
        assert [s["name"] for s in out["searches"]] == ["Bank mails"] and out["rules"] == []


# ---------------- weekly digest ----------------
def test_weekly_digest_routine(bz):
    ctx = Ctx("default", bz["conv"])
    out = run("email_accounts", {"daily_summary": "weekly 09:30"}, ctx)
    assert any("weekly inbox digest at 09:30" in c for c in out["changed"])
    from sqlalchemy import select
    from app.db import Routine
    with session() as s:
        r = s.scalar(select(Routine).where(Routine.tenant_id == "default", Routine.status == "active",
                                           Routine.title == "Weekly inbox summary"))
        assert r is not None and r.repeat == "weekly"
        assert "last 7 days" in r.instruction and "newsletters" in r.instruction
    out = run("email_accounts", {"daily_summary": "08:15"}, ctx)          # daily replaces the weekly
    with session() as s:
        old = s.scalars(select(Routine).where(Routine.tenant_id == "default",
                                              Routine.title == "Weekly inbox summary")).all()
        assert all(x.status != "active" for x in old)
        daily = s.scalar(select(Routine).where(Routine.tenant_id == "default", Routine.status == "active",
                                               Routine.title == "Inbox summary"))
        assert daily is not None and daily.repeat == "daily"
    run("email_accounts", {"daily_summary": "off"}, ctx)
    with session() as s:
        left = s.scalars(select(Routine).where(Routine.tenant_id == "default", Routine.status == "active",
                                               Routine.title.in_(["Inbox summary", "Weekly inbox summary"]))).all()
        assert left == []


# ---------------- send-from-alias ----------------
@pytest.fixture
def abox(bz, monkeypatch):  # noqa: F811
    import app.mailbox.accounts as ma
    b = AliasBox()
    with session() as s:
        s.add(MailAccount(id="mbx_alias", tenant_id="default", kind="gmail", address="meghana@fnw.in",
                          scopes=f"{ma.GMAIL_SCOPE} {ma.SETTINGS_SCOPE}"))
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    return b


def test_alias_draft_needs_verified_and_scope(abox, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    with pytest.raises(ToolError, match="verify nahi hua"):
        run("email_draft", {"to": "ramesh@vendor.in", "body": "Namaste", "from_alias": "hello@newtika.in"}, ctx)
    with pytest.raises(ToolError, match="alias nahi hai"):
        run("email_draft", {"to": "ramesh@vendor.in", "body": "Namaste", "from_alias": "nope@x.in"}, ctx)
    with pytest.raises(ToolError, match="dobara jod"):
        with session() as s:   # an old mailbox (mail scope only): the honest reconnect, before any card
            s.get(MailAccount, "mbx_alias").scopes = "https://www.googleapis.com/auth/gmail.modify"
        run("email_draft", {"to": "ramesh@vendor.in", "body": "Namaste", "from_alias": "hello@newtika.in"}, ctx)


def test_alias_send_goes_from_the_alias(abox, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    abox.sendas[1]["verificationStatus"] = "accepted"                     # verified in Gmail web now
    out = run("email_draft", {"to": "ramesh@vendor.in", "body": "Quotation chahiye", "subject": "Quotation for routers",
                              "from_alias": "HELLO@newtika.in"}, ctx)     # case-insensitive
    assert out["draft_id"]
    card = _events(bz["conv"], "email_draft")[-1]
    assert card["from_alias"] == "hello@newtika.in"
    sent = ms.send_draft("default", out["draft_id"])
    assert sent["status"] == "sent"
    msg = abox.sent[0]
    assert "hello@newtika.in" in str(msg["From"])                          # it really goes out from the alias
    # the mailbox's own address as alias: no settings round-trip needed
    out2 = run("email_draft", {"to": "ramesh@vendor.in", "body": "seedha", "from_alias": "meghana@fnw.in"}, ctx)
    ms.send_draft("default", out2["draft_id"])
    assert "meghana@fnw.in" in str(abox.sent[1]["From"])


# ---------------- Gmail's own snoozed pile ----------------
def test_snoozed_folder_gmail_only(env, monkeypatch):
    b = Box("mbx_x", "office@newtika.in")
    import app.mailbox.accounts as ma
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    with pytest.raises(MailError, match="Snoozed folder"):
        ms.check("default", folder="snoozed")
    with pytest.raises(MailError, match="email_snooze"):
        ms.check("default", folder="snoozed", account="mbx_x")
    assert FOLDER_Q["snoozed"] == "in:snoozed"                             # the official operator, on the API


# ---------------- labels: nesting + colours (star colours stay impossible) ----------------
@pytest.fixture
def lbox(env, monkeypatch):
    b = LabelBox()
    import app.mailbox.accounts as ma
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    return b


def test_label_list_tree_and_colors(lbox):
    out = ms.label_op("default", "list")
    assert "Office" in out["labels"] and "Office/Clients" in out["labels"]
    tree = out["tree"]
    office = next(n for n in tree if n["name"] == "Office")
    assert office["path"] == "Office"
    assert [c["path"] for c in office["children"]] == ["Office/Clients"]
    assert out["colors"]["Office"] == "#4986e7"


def test_label_create_builds_the_nested_path(lbox):
    n = len(lbox.creates)
    out = ms.label_op("default", "create", "Kaam/Clients/Acme")
    assert out["created"] == "Kaam/Clients/Acme"
    assert lbox.creates[n:] == ["Kaam", "Kaam/Clients", "Kaam/Clients/Acme"]   # level by level, so Gmail nests it
    out2 = ms.label_op("default", "create", "Office/Vendors")                  # parent exists: only the leaf is made
    assert lbox.creates[-1] == "Office/Vendors"


def test_label_color_and_honest_star_note(lbox):
    out = ms.label_op("default", "color", "Office", color="green")
    assert out["colored"] == "Office" and out["color"] == "green"
    assert lbox.patches[-1][1]["color"] == {"backgroundColor": "#16a765", "textColor": "#ffffff"}
    with pytest.raises(MailError, match="Star ka rang"):
        ms.label_op("default", "color", "Office", color="pink")
    with pytest.raises(MailError, match="Rang in mein se hai"):
        ms.label_op("default", "color", "Office", color="")


def test_email_label_tool_color(lbox):
    ctx = Ctx("default", conv_ctx().conversation_id)
    out = run("email_label", {"action": "color", "name": "Office", "color": "sky"}, ctx)
    assert out["color"] == "sky" and lbox.patches[-1][1]["color"]["backgroundColor"] == "#9fc6e7"


# ---------------- version ----------------
def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.250.0"
