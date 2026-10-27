"""v0.188.0 "the remaining surface": Gmail's OWN filters, the forwarding-address book, send-as alias add/remove,
IMAP / POP / language settings, Gmail drafts read-edit-send, threads as a unit (threads.modify / threads.trash)
and delete-forever (messages.delete) behind its plain-words card. Every settings gate honoured (old mailboxes get
the honest ek-baar-dobara-jodiye), the card never lies, and the fake box speaks the real endpoints from memory."""
import base64
import json

import pytest

from app.agent.email_tools import EMAIL_LABELS, EMAIL_TOOLS
from app.agent.tools import ToolError
from app.db import MailAccount
from app.mailbox import mime
from app.mailbox.base import MailError
from app.mailbox.gmail import GmailBox, b64url
from tests.test_bazar import _events, _notices, bz  # noqa: F401
from tests.test_email import _raw, run  # noqa: F401
from tests.test_life import conv_ctx
from app.agent.tools import Ctx

DRAFT_RAW = None  # built in the fixture (mime.build -> EmailMessage)


class SurfaceBox(GmailBox):
    """A GmailBox that speaks every v0.188.0 endpoint from memory (no HTTP): settings, drafts, threads, messages."""

    def __init__(self, key="mbx5", address="meghana@fnw.in"):
        super().__init__(key, address, lambda force: "tok", "Meghana Ingle", "Meghana Ingle\nDirector, FNW")
        self.calls: list[tuple[str, str]] = []
        self.msgs: dict[str, bytes] = {}
        # settings state
        self.filters = [{"id": "flt_old", "criteria": {"from": "old@x.in"},
                         "action": {"addLabelIds": ["Label_1"], "removeLabelIds": ["INBOX"]}}]
        self.labels = [{"id": "Label_1", "name": "Bills", "type": "user"}]
        self.fwdbook = [{"forwardingEmail": "dup@x.in", "verificationStatus": "accepted"}]
        self.sendas = [{"sendAsEmail": address, "displayName": "Meghana Ingle", "replyToAddress": "",
                        "isPrimary": True, "isDefault": True, "treatAsAlias": False,
                        "verificationStatus": "accepted", "signature": ""},
                       {"sendAsEmail": "hello@newtika.in", "displayName": "Newtika", "replyToAddress": "",
                        "isPrimary": False, "isDefault": False, "treatAsAlias": False,
                        "verificationStatus": "accepted", "signature": "<b>Newtika</b>"}]
        self.imap = {"enabled": False, "autoExpunge": True, "expungeBehavior": "archive", "maxFolderSize": 0}
        self.pop = {"accessWindow": "disabled", "disposition": "leaveInInbox"}
        self.lang = {"displayLanguage": "en"}
        self.vac = {"enableAutoReply": False, "responseSubject": "", "responseBody": "",
                    "restrictToContacts": False, "restrictToDomain": False, "startTime": "0", "endTime": "0"}
        self.fwd = {"enabled": False, "emailAddress": "", "disposition": "keep"}
        # drafts state
        self.drafts: dict[str, dict] = {}
        self.sent_drafts: list[str] = []
        # threads state
        self.threads: list[str] = ["th1", "th2"]
        self.thread_mods: list[tuple[str, dict]] = []
        self.thread_trashed: list[str] = []
        self.deleted_forever: list[str] = []
        self.trashed: list[str] = []
        self.batch_mods: list[dict] = []

    # ---- message storage for the delete cards ----
    def add(self, mid, raw):
        self.msgs[mid] = raw

    def raw(self, mid):
        if mid not in self.msgs:
            raise MailError("Yeh email nahi mila")
        return self.msgs[mid]

    def thread_of(self, mid):
        return "t" + mid

    def _hdr(self, mid, name):
        import email as _e
        m = _e.message_from_bytes(self.msgs[mid])
        return m.get(name, "")

    # ---- the wire ----
    def _req(self, method, path, **kw):
        p = path.split("?")[0]
        self.calls.append((method, p))
        j = kw.get("json") or {}
        # labels (filter list resolution + label creation)
        if method == "GET" and p == "/labels":
            return {"labels": [dict(x) for x in self.labels]}
        if method == "POST" and p == "/labels":
            row = {"id": f"Label_{len(self.labels) + 9}", "name": j.get("name", "?"), "type": "user"}
            self.labels.append(row)
            return row
        # filters
        if method == "GET" and p == "/settings/filters":
            return {"filter": [json.loads(json.dumps(f)) for f in self.filters]}
        if method == "POST" and p == "/settings/filters":
            row = {"id": f"flt_{len(self.filters) + 1}", "criteria": j.get("criteria") or {},
                   "action": j.get("action") or {}}
            self.filters.append(row)
            return row
        if method == "DELETE" and p.startswith("/settings/filters/"):
            fid = p.rsplit("/", 1)[-1]
            self.filters = [f for f in self.filters if f["id"] != fid]
            return {}
        # forwarding addresses
        if method == "GET" and p == "/settings/forwardingAddresses":
            return {"forwardingAddresses": [dict(r) for r in self.fwdbook]}
        if method == "POST" and p == "/settings/forwardingAddresses":
            self.fwdbook.append({"forwardingEmail": j.get("forwardingEmail"), "verificationStatus": "pending"})
            return dict(self.fwdbook[-1])
        if method == "DELETE" and p.startswith("/settings/forwardingAddresses/"):
            em = p.rsplit("/", 1)[-1]
            self.fwdbook = [r for r in self.fwdbook if r.get("forwardingEmail") != em]
            return {}
        # send-as
        if method == "GET" and p == "/settings/sendAs":
            return {"sendAs": [dict(sa) for sa in self.sendas]}
        if method == "PATCH" and p.startswith("/settings/sendAs/"):
            em = p.rsplit("/", 1)[-1]
            for sa in self.sendas:
                if sa["sendAsEmail"] == em:
                    sa.update(j)
                    return {"sendAsEmail": em}
            raise MailError(f"Gmail error 404: sendAs {em} nahi mila")
        if method == "POST" and p == "/settings/sendAs":
            status = "pending" if "pending" in j.get("sendAsEmail", "") else "accepted"
            self.sendas.append({"sendAsEmail": j.get("sendAsEmail"), "displayName": j.get("displayName", ""),
                                "replyToAddress": j.get("replyToAddress", ""), "isPrimary": False,
                                "isDefault": False, "treatAsAlias": False, "verificationStatus": status,
                                "signature": ""})
            return dict(self.sendas[-1])
        if method == "DELETE" and p.startswith("/settings/sendAs/"):
            em = p.rsplit("/", 1)[-1]
            if em == self.address:
                raise MailError("Gmail error 400: primary nahi")
            self.sendas = [sa for sa in self.sendas if sa.get("sendAsEmail") != em]
            return {}
        # imap / pop / language
        if method == "GET" and p == "/settings/imap":
            return dict(self.imap)
        if method == "PUT" and p == "/settings/imap":
            self.imap.update(j)
            return dict(self.imap)
        if method == "GET" and p == "/settings/pop":
            return dict(self.pop)
        if method == "PUT" and p == "/settings/pop":
            self.pop.update(j)
            return dict(self.pop)
        if method == "GET" and p == "/settings/language":
            return dict(self.lang)
        if method == "PUT" and p == "/settings/language":
            self.lang.update(j)
            return dict(self.lang)
        # vacation / auto-forward (settings_status reads them)
        if method == "GET" and p == "/settings/vacation":
            return dict(self.vac)
        if method == "PUT" and p == "/settings/vacation":
            self.vac.update(j)
            return dict(self.vac)
        if method == "GET" and p == "/settings/autoForwarding":
            return dict(self.fwd)
        if method == "PUT" and p == "/settings/autoForwarding":
            self.fwd.update(j)
            return dict(self.fwd)
        # drafts
        if method == "GET" and p.startswith("/drafts/"):
            did = p.rsplit("/", 1)[-1]
            if did not in self.drafts:
                raise MailError("Gmail error 404: draft nahi mila")
            return json.loads(json.dumps(self.drafts[did]))
        if method == "PUT" and p.startswith("/drafts/"):
            did = p.rsplit("/", 1)[-1]
            if did not in self.drafts:
                raise MailError("Gmail error 404: draft nahi mila")
            self.drafts[did]["message"].update(j.get("message") or {})
            return {"id": did, "message": dict(self.drafts[did]["message"])}
        if method == "DELETE" and p.startswith("/drafts/"):
            did = p.rsplit("/", 1)[-1]
            self.drafts.pop(did, None)
            return {}
        if method == "POST" and p == "/drafts/send":
            did = j.get("id", "")
            if did not in self.drafts:
                raise MailError("Gmail error 404: draft nahi mila")
            self.sent_drafts.append(did)
            out = self.drafts.pop(did)
            return {"id": out["message"].get("id", "newmid"), "threadId": out["message"].get("threadId", "")}
        # threads
        if method == "GET" and p == "/threads":
            return {"threads": [{"id": t} for t in self.threads]}
        if method == "GET" and p.startswith("/threads/"):
            tid = p.rsplit("/", 1)[-1]
            return {"id": tid, "messages": [{"id": f"{tid}-1", "threadId": tid, "snippet": "hello",
                                             "labelIds": ["INBOX", "UNREAD"],
                                             "payload": {"headers": [
                                                 {"name": "From", "value": "Ramesh <ramesh@vendor.in>"},
                                                 {"name": "Subject", "value": "Quotation"},
                                                 {"name": "Date", "value": "Sat, 25 Oct 2026 10:00:00 +0530"}]}}]}
        if method == "POST" and p.startswith("/threads/") and p.endswith("/modify"):
            tid = p.split("/")[-2]
            self.thread_mods.append((tid, j))
            return {"id": tid}
        if method == "POST" and p.startswith("/threads/") and p.endswith("/trash"):
            tid = p.split("/")[-2]
            self.thread_trashed.append(tid)
            return {"id": tid}
        # delete forever + normal trash + batchModify
        if method == "DELETE" and p.startswith("/messages/"):
            mid = p.rsplit("/", 1)[-1]
            self.deleted_forever.append(mid)
            self.msgs.pop(mid, None)
            return {}
        if method == "POST" and p == "/messages/batchModify":
            self.batch_mods.append(j)
            return {}
        if method == "POST" and p.startswith("/messages/") and p.endswith("/trash"):
            mid = p.split("/")[-2]
            self.trashed.append(mid)                              # Gmail keeps trashed mail; so does the fake
            return {}
        raise MailError(f"SurfaceBox: unexpected {method} {p}")


@pytest.fixture
def gb(bz, monkeypatch):  # noqa: F811
    """The surface box, connected with a row that carries BOTH scopes (the v0.183.0+ consent)."""
    import app.mailbox.accounts as ma
    b = SurfaceBox()
    b.add("201", _raw(("Ramesh Patil", "ramesh@vendor.in"), "meghana@fnw.in", "Quotation for 10 routers",
                      "Namaste, quotation bhejiye.", msgid="<q10@vendor.in>"))
    with __import__("app.db", fromlist=["session"]).session() as s:
        s.add(MailAccount(id="mbx5", tenant_id="default", kind="gmail", address="meghana@fnw.in",
                          scopes=f"{ma.GMAIL_SCOPE} {ma.SETTINGS_SCOPE}"))
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    return b


def ref(mid):
    return f"mbx5~{mid}"


# ---------------- tool registry ----------------
def test_new_tools_registered_with_labels():
    names = {t["name"] for t in EMAIL_TOOLS}
    assert {"email_filters", "email_forwarding", "email_alias", "email_threads"} <= names
    for n in ("email_filters", "email_forwarding", "email_alias", "email_threads", "email_drafts", "email_delete"):
        assert n in EMAIL_LABELS


# ---------------- Gmail's own filters ----------------
def test_filter_create_list_delete(gb, bz):  # noqa: F811
    ctx = conv_ctx()
    out = run("email_filters", {"action": "create", "match": {"from": "hdfcbank"}, "do": {"label": "Bills"}},
              ctx)
    assert out["created"] and "Gmail ke andar" in out["note"]
    row = gb.filters[-1]
    assert row["criteria"] == {"from": "hdfcbank"}
    assert row["action"]["addLabelIds"] == ["Label_1"]           # existing label resolved, not created
    lst = run("email_filters", {"action": "list"}, ctx)
    assert lst["count"] == 2
    assert "Bills" in lst["filters"][-1]["add_labels"]            # the new filter labels
    assert "INBOX" in lst["filters"][0]["remove_labels"]          # the seeded old filter archives
    out = run("email_filters", {"action": "delete", "filter_id": "flt_old"}, ctx)
    assert out["deleted"] == "flt_old" and gb.filters == [gb.filters[0]]
    assert any(m == "DELETE" and p == "/settings/filters/flt_old" for m, p in gb.calls)


def test_filter_create_needs_match_and_action(gb, bz):  # noqa: F811
    ctx = conv_ctx()
    with pytest.raises(ToolError, match="match do"):
        run("email_filters", {"action": "create", "do": {"archive": True}}, ctx)
    with pytest.raises(ToolError, match="kya karega"):
        run("email_filters", {"action": "create", "match": {"from": "x@y.in"}}, ctx)
    with pytest.raises(ToolError, match="personal / social"):
        run("email_filters", {"action": "create", "match": {"from": "x@y.in"}, "do": {"category": "xyz"}}, ctx)


def test_filter_creates_missing_label_and_size_criteria(gb, bz):  # noqa: F811
    ctx = conv_ctx()
    out = run("email_filters", {"action": "create", "match": {"subject": "invoice", "larger_kb": 500},
                                "do": {"label": "Kaam", "archive": True, "mark_read": True}}, ctx)
    row = gb.filters[-1]
    assert row["criteria"]["size"] == 500 * 1024 and row["criteria"]["sizeComparison"] == "larger"
    assert row["criteria"]["subject"] == "invoice"
    assert row["action"]["addLabelIds"] and row["action"]["removeLabelIds"] == ["INBOX", "UNREAD"]
    assert any(r["name"] == "Kaam" for r in gb.labels)           # the label was really created


def test_filter_forward_needs_verified_address(gb, bz):  # noqa: F811
    ctx = conv_ctx()
    with pytest.raises(ToolError, match="verified forwarding address"):
        run("email_filters", {"action": "create", "match": {"from": "a@b.in"}, "do": {"forward": "nope@x.in"}}, ctx)
    run("email_forwarding", {"action": "add", "email": "new@x.in"}, ctx)      # pending — still refused
    with pytest.raises(ToolError, match="verified forwarding address"):
        run("email_filters", {"action": "create", "match": {"from": "a@b.in"}, "do": {"forward": "new@x.in"}}, ctx)
    next(r for r in gb.fwdbook if r["forwardingEmail"] == "new@x.in")["verificationStatus"] = "accepted"
    out = run("email_filters", {"action": "create", "match": {"from": "a@b.in"}, "do": {"forward": "new@x.in"}}, ctx)
    assert gb.filters[-1]["action"]["forward"] == "new@x.in" and out["created"]


# ---------------- forwarding-address book ----------------
def test_forwarding_add_list_remove(gb, bz):  # noqa: F811
    ctx = conv_ctx()
    lst = run("email_forwarding", {"action": "list"}, ctx)
    assert [a["email"] for a in lst["addresses"]] == ["dup@x.in"] and lst["addresses"][0]["status"] == "verified"
    out = run("email_forwarding", {"action": "add", "email": "office@x.in"}, ctx)
    assert "verification" in out["note"] and gb.fwdbook[-1]["verificationStatus"] == "pending"
    out = run("email_forwarding", {"action": "add", "email": "dup@x.in"}, ctx)
    assert "pehle se" in out["note"]
    out = run("email_forwarding", {"action": "remove", "email": "dup@x.in"}, ctx)
    assert out["removed"] == "dup@x.in" and all(r["forwardingEmail"] != "dup@x.in" for r in gb.fwdbook)


# ---------------- send-as aliases ----------------
def test_alias_add_and_list(gb, bz):  # noqa: F811
    ctx = conv_ctx()
    out = run("email_alias", {"action": "add", "email": "team@newtika.in", "name": "Team"}, ctx)
    assert out["status"] == "accepted" and gb.sendas[-1]["sendAsEmail"] == "team@newtika.in"
    out = run("email_alias", {"action": "add", "email": "hello@newtika.in"}, ctx)
    assert "pehle se" in out["note"]
    lst = run("email_alias", {"action": "list"}, ctx)
    assert {a["email"] for a in lst["aliases"]} >= {"hello@newtika.in", "meghana@fnw.in"}


def test_alias_remove_primary_refused_secondary_card(gb, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    with pytest.raises(ToolError, match="Primary"):
        run("email_alias", {"action": "remove", "email": "meghana@fnw.in"}, ctx)
    out = run("email_alias", {"action": "remove", "email": "hello@newtika.in"}, ctx)
    assert out["needs_approval"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Alias 'hello@newtika.in' hatayein?"
    assert gb.sendas[-1]["sendAsEmail"] == "hello@newtika.in"     # nothing removed before the tap
    bz["svc"].decide("default", card["id"], "approve")
    assert all(sa["sendAsEmail"] != "hello@newtika.in" for sa in gb.sendas)


# ---------------- IMAP / POP / language ----------------
def test_imap_get_set(gb, bz):  # noqa: F811
    ctx = conv_ctx()
    out = run("email_accounts", {"imap": "get"}, ctx)
    assert out["imap"]["enabled"] is False
    out = run("email_accounts", {"imap": "on"}, ctx)
    assert "Outlook" in out["note"] and gb.imap["enabled"] is True
    out = run("email_accounts", {"imap": "off"}, ctx)
    assert gb.imap["enabled"] is False and gb.imap["expungeBehavior"] == "archive"   # rest preserved


def test_pop_get_set_and_bad_mode(gb, bz):  # noqa: F811
    ctx = conv_ctx()
    out = run("email_accounts", {"pop": "get"}, ctx)
    assert out["pop"]["on"] is False
    run("email_accounts", {"pop": "all"}, ctx)
    assert gb.pop["accessWindow"] == "allMail"
    run("email_accounts", {"pop": "from_now_on", "pop_disposition": "trash"}, ctx)
    assert gb.pop == {"accessWindow": "fromNowOn", "disposition": "trash"}
    run("email_accounts", {"pop": "off"}, ctx)
    assert gb.pop["accessWindow"] == "disabled"
    with pytest.raises(ToolError, match="off / all / from_now_on"):
        run("email_accounts", {"pop": "kuch_bhi"}, ctx)


def test_language_set(gb, bz):  # noqa: F811
    ctx = conv_ctx()
    out = run("email_accounts", {"language": "get"}, ctx)
    assert out["language"] == "en"
    out = run("email_accounts", {"language": "hi"}, ctx)
    assert gb.lang["displayLanguage"] == "hi" and "Hoola aapki language" in out["note"]
    with pytest.raises(ToolError, match="code do"):
        run("email_accounts", {"language": "hinglish!!"}, ctx)


def test_settings_status_view_has_all(gb, bz):  # noqa: F811
    from app.mailbox import service as ms
    v = ms.settings_status("default", None)
    assert v["imap"]["enabled"] is False and v["pop"]["on"] is False and v["language"] == "en"
    assert v["aliases"] and v["vacation"]["on"] is False


# ---------------- Gmail drafts: read / edit / send ----------------
@pytest.fixture
def draft(gb):  # noqa: F811
    msg = mime.build(from_addr="meghana@fnw.in", from_name="Meghana Ingle", to="ramesh@vendor.in",
                     subject="Quotation for 10 routers", body="Purana draft text.",
                     files=[("price.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"xx")])
    gb.drafts["d1"] = {"message": {"id": "m_d1", "threadId": "tq", "raw": b64url(msg.as_bytes())}}
    return "d1"


def test_draft_read_and_edit_keeps_attachment(gb, draft, bz):  # noqa: F811
    ctx = conv_ctx()
    v = run("email_drafts", {"action": "read", "id": "d1"}, ctx)
    assert v["to"] == "ramesh@vendor.in" and v["subject"] == "Quotation for 10 routers"
    assert v["attachments"] == ["price.xlsx"] and v["ref"] == "mbx5~d1"
    out = run("email_drafts", {"action": "edit", "id": "d1", "subject": "Quotation (revised)",
                               "body": "**Revised** rate bhejiye.", "markdown": True}, ctx)
    assert "subject" in out["edited"] and out["attachments_kept"] == 1
    raw = base64.urlsafe_b64decode(gb.drafts["d1"]["message"]["raw"] + "=" * (-len(gb.drafts["d1"]["message"]["raw"]) % 4))
    p = mime.parse(raw)
    assert p["subject"] == "Quotation (revised)" and "rate bhejiye" in p["body"] and "<b>Revised</b>" in raw.decode("utf-8", "replace")
    assert [a["name"] for a in p["attachments"]] == ["price.xlsx"]
    assert gb.drafts["d1"]["message"]["threadId"] == "tq"          # the conversation stays


def test_draft_edit_needs_a_field(gb, draft, bz):  # noqa: F811
    ctx = conv_ctx()
    with pytest.raises(ToolError, match="Kya badalna hai"):
        run("email_drafts", {"action": "edit", "id": "d1"}, ctx)


def test_draft_send_card_then_real_send(gb, draft, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("email_drafts", {"action": "send", "id": "d1"}, ctx)
    assert out["needs_approval"] and gb.sent_drafts == []
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Yeh Gmail draft bhejein?"
    flat = json.dumps(card, ensure_ascii=False)
    assert "ramesh@vendor.in" in flat and "Quotation for 10 routers" in flat and "price.xlsx" in flat
    assert "undo nahi" in flat                                    # the card says no undo, in plain words
    assert not any(m == "POST" and p == "/drafts/send" for m, p in gb.calls)
    bz["svc"].decide("default", card["id"], "approve")
    assert gb.sent_drafts == ["d1"] and "d1" not in gb.drafts     # drafts.send really ran, draft gone


# ---------------- threads as a unit ----------------
def test_threads_list_and_act(gb, bz):  # noqa: F811
    ctx = conv_ctx()
    out = run("email_threads", {"action": "list", "query": "in:inbox"}, ctx)
    assert out["count"] == 2 and out["threads"][0]["ref"] == "mbx5~th:th1"
    assert out["threads"][0]["subject"] == "Quotation" and out["threads"][0]["unread"] is True
    out = run("email_threads", {"action": "act", "refs": ["mbx5~th:th1"], "act": "archive"}, ctx)
    assert out["count"] == 1
    assert ("th1", {"addLabelIds": [], "removeLabelIds": ["INBOX"]}) in gb.thread_mods
    out = run("email_threads", {"action": "act", "refs": ["mbx5~th:th2", "mbx5~th:th1"], "act": "trash"}, ctx)
    assert gb.thread_trashed == ["th2", "th1"] and gb.thread_mods[-2:] == gb.thread_mods[-2:]
    run("email_threads", {"action": "act", "refs": ["mbx5~th:th1"], "act": "star"}, ctx)
    assert ("th1", {"addLabelIds": ["STARRED"], "removeLabelIds": []}) in gb.thread_mods
    out = run("email_threads", {"action": "act", "refs": ["mbx5~th:th1"], "act": "move", "folder": "Kaam"}, ctx)
    assert out["done"] == "move"                                  # label created on the fly
    with pytest.raises(ToolError, match="one of"):
        run("email_threads", {"action": "act", "refs": ["mbx5~th:th1"], "act": "explode"}, ctx)


def test_threads_read_and_non_gmail_honest(gb, bz, monkeypatch):  # noqa: F811
    ctx = conv_ctx()
    out = run("email_threads", {"action": "read", "id": "201"}, ctx)
    assert "messages" in out                                      # rides the normal thread reader
    from app.mailbox import service as ms
    from app.mailbox.base import Box

    class NonGmail(Box):
        kind = "imap"

        def __init__(self):
            super().__init__("mbx_imap", "she@zoho.in", "She", "")

    import app.mailbox.accounts as ma
    monkeypatch.setattr(ma, "boxes", lambda tenant: [NonGmail()] if tenant == "default" else [])
    with pytest.raises(MailError, match="Gmail par"):
        ms.threads_list("default", "in:inbox", 5, "mbx_imap")


# ---------------- delete forever ----------------
def test_delete_normal_trash_vs_forever_card_and_execute(gb, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("email_delete", {"ids": [ref("201")]}, ctx)
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "1 email delete karein?" and "Trash" in json.dumps(card, ensure_ascii=False)
    assert "HAMESHA" not in json.dumps(card, ensure_ascii=False)
    assert gb.deleted_forever == []                               # nothing permanent before the tap
    bz["svc"].decide("default", card["id"], "approve")
    assert gb.deleted_forever == [] and "201" in gb.msgs and gb.trashed == ["201"]   # normal delete = Trash

    out = run("email_delete", {"ids": [ref("201")], "forever": True}, ctx)
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "1 email HAMESHA KE LIYE delete karein?"
    flat = json.dumps(card, ensure_ascii=False)
    assert "wapas NAHI aayengi" in flat and "Trash mein bhi nahi" in flat
    assert not any(m == "DELETE" and p.startswith("/messages/") for m, p in gb.calls)
    bz["svc"].decide("default", card["id"], "approve")
    assert gb.deleted_forever == ["201"] and "201" not in gb.msgs


def test_delete_forever_refused_off_gmail(bz, monkeypatch):  # noqa: F811
    from app.mailbox import service as ms
    from app.mailbox.base import Box

    class NonGmail(Box):
        kind = "imap"

        def __init__(self):
            super().__init__("mbx_imap", "she@zoho.in", "She", "")

    import app.mailbox.accounts as ma
    monkeypatch.setattr(ma, "boxes", lambda tenant: [NonGmail()] if tenant == "default" else [])
    with pytest.raises(MailError, match="sirf Gmail"):
        ms.delete_forever("default", ["mbx_imap~9"])


# ---------------- the settings gate still guards everything new ----------------
def test_new_settings_gated_on_old_mailbox(bz, monkeypatch):  # noqa: F811
    import app.mailbox.accounts as ma
    b = SurfaceBox()
    with __import__("app.db", fromlist=["session"]).session() as s:
        s.add(MailAccount(id="mbx5", tenant_id="default", kind="gmail", address="meghana@fnw.in",
                          scopes=ma.GMAIL_SCOPE))                 # mail scope only — no gmail.settings.basic
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    ctx = conv_ctx()
    for name, args in (("email_filters", {"action": "list"}), ("email_forwarding", {"action": "list"}),
                       ("email_alias", {"action": "list"})):
        with pytest.raises(ToolError, match="dobara jodna"):
            run(name, args, ctx)
    for args in ({"imap": "get"}, {"pop": "get"}, {"language": "get"}):
        out = run("email_accounts", args, ctx)                     # the v0.183 gate returns the honest note
        assert out["scope_ok"] is False and "dobara jodna" in out["note"]
    assert not any(p.startswith("/settings/") for _, p in b.calls)   # nothing reached Gmail
