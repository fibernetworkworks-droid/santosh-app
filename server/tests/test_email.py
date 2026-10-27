"""Email: the user's own mailboxes. Reading, sorting, attachments, drafts that wait for Bhejo, scheduled send,
follow-ups, delete and bulk mail behind approval cards, contacts, accounts (IMAP / Gmail / Outlook)."""
import asyncio
import base64
import io
import json
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from app.db import EmailDraft, MailWatch, now, session
from app.mailbox import mime
from app.mailbox.base import Box, MailError
from tests.test_bazar import _events, _notices, bz  # noqa: F401
from tests.test_life import conv_ctx


def _raw(frm, to, subject, body, files=(), msgid=None, extra=None, cc=""):
    name, addr = frm
    m = mime.build(from_addr=addr, from_name=name, to=to, cc=cc, subject=subject, body=body, files=list(files))
    if msgid:
        del m["Message-ID"]
        m["Message-ID"] = msgid
    for k, v in (extra or {}).items():
        m[k] = v
    return m.as_bytes()


def _xlsx(rows):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _pdf(text):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, text)
    c.save()
    return buf.getvalue()


class FakeBox(Box):
    kind = "gmail"

    def __init__(self, key="mbx_test", address="meghana@fnw.in", signature=""):
        super().__init__(key, address, "Meghana Ingle", signature)
        self.msgs = {}        # id -> {"raw", "folder", "unread", "starred", "thread"}
        self.sent = []
        self.reply_state = {"from_them": False, "from_me": False}

    def add(self, mid, raw, folder="inbox", unread=True, thread=""):
        self.msgs[mid] = {"raw": raw, "folder": folder, "unread": unread, "starred": False, "thread": thread or "t" + mid}

    def list(self, folder="inbox", unread_only=False, search=None, limit=10, since=None, snippets=False):
        out = []
        for mid, m in reversed(list(self.msgs.items())):
            if m["folder"] != folder or (unread_only and not m["unread"]):
                continue
            p = mime.parse(m["raw"])
            if search and search.lower() not in (p["subject"] + p["body"] + p["from_email"]).lower():
                continue
            out.append({"id": mid, "thread_id": m["thread"], "from": p["from"], "from_email": p["from_email"],
                        "to": p["to"], "subject": p["subject"], "date": p["date"], "unread": m["unread"],
                        "starred": m["starred"], "snippet": p["body"][:200], "bulk": p["bulk"],
                        "has_attachments": bool(p["attachments"]), "message_id": p["message_id"]})
        return out[:limit]

    def raw(self, mid):
        if mid not in self.msgs:
            raise MailError("Yeh email nahi mila")
        return self.msgs[mid]["raw"]

    def thread_of(self, mid):
        return self.msgs[mid]["thread"]

    def mark(self, ids, read):
        for i in ids:
            self.msgs[i]["unread"] = not read

    def star(self, ids, on):
        for i in ids:
            self.msgs[i]["starred"] = on

    def archive(self, ids):
        for i in ids:
            self.msgs[i]["folder"] = "archive"

    def trash(self, ids):
        for i in ids:
            self.msgs[i]["folder"] = "trash"

    def move(self, ids, folder):
        for i in ids:
            self.msgs[i]["folder"] = folder

    def send(self, msg, thread_id=None):
        self.sent.append((msg, thread_id))
        return {"message_id": msg["Message-ID"], "thread_id": thread_id or "tnew"}

    def replies(self, message_id, thread_id, since):
        return dict(self.reply_state)


@pytest.fixture
def box(env, monkeypatch):
    b = FakeBox()
    b.add("101", _raw(("Ramesh Patil", "ramesh@vendor.in"), "meghana@fnw.in, swati@fnw.in", "Quotation for 10 routers",
                      "Namaste, kya aap 10 routers ka quotation bhej sakte hain? Dhanyavaad, Ramesh",
                      msgid="<abc@vendor.in>", cc="ankita@fnw.in"))
    b.add("102", _raw(("HDFC Bank", "alerts@hdfcbank.net"), "meghana@fnw.in", "Your OTP for login",
                      "Your OTP is 482913. Do not share it."))
    b.add("103", _raw(("Amazon", "store-news@amazon.in"), "meghana@fnw.in", "Diwali sale is live",
                      "Up to 70% off", extra={"List-Unsubscribe": "<mailto:u@amazon.in>"}))
    b.add("104", _raw(("MSEDCL", "billing@mahadiscom.in"), "meghana@fnw.in", "Electricity bill for October",
                      "Amount payable Rs 1,540. Due date 25 Oct.", files=[("bill.pdf", "application/pdf", _pdf("Bill amount 1540"))]))
    b.add("105", _raw(("Sharma Traders", "accounts@sharmatraders.in"), "meghana@fnw.in", "Customer list for Diwali mail",
                      "List attached", files=[("customers.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                               _xlsx([["Name", "Email", "Amount"], ["Raju", "raju@example.in", 500],
                                                      ["Sita", "sita@example.in", 750], ["Dup", "RAJU@example.in", 1],
                                                      ["Bad", "not-an-email", 2]]))]))
    import app.mailbox.accounts as ma
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    return b


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


def ref(mid):
    return f"mbx_test~{mid}"


# ---------------- reading and sorting ----------------
def test_check_read_and_reply_all_threads(box):
    ctx = conv_ctx()
    lst = run("email_check", {"unread_only": True}, ctx)
    assert lst["count"] == 5 and lst["emails"][-1]["id"] == ref("101") and lst["account"] == "meghana@fnw.in"
    full = run("email_read", {"id": ref("101")}, ctx)
    assert "quotation" in full["body"].lower() and full["thread_id"] == "t101"
    assert box.msgs["101"]["unread"] is False                     # reading marks it read
    out = run("email_draft", {"reply_to_id": ref("101"), "reply_all": True, "body": "Ji Ramesh, quotation bhej rahi hoon."}, ctx)
    assert out["status"] == "pending_approval"
    with session() as s:
        d = s.get(EmailDraft, out["draft_id"])
        assert d.to_addr == "ramesh@vendor.in" and d.subject == "Re: Quotation for 10 routers"
        assert set(a.strip() for a in d.cc_addr.split(",")) == {"swati@fnw.in", "ankita@fnw.in"}   # everyone but me
        assert d.in_reply_to == "<abc@vendor.in>" and d.thread_id == "t101" and d.kind == "reply"
    assert box.sent == []                                         # nothing sent before Bhejo


def test_triage_sorts_and_hides_codes(box):
    out = run("email_triage", {}, conv_ctx())
    g = out["groups"]
    assert [i["subject"] for i in g["needs_reply"]] == ["Quotation for 10 routers"]
    assert [i["subject"] for i in g["otp_alerts"]] == ["Your OTP for login"]
    assert "482913" not in json.dumps(out)                        # OTPs are never handed to the model
    assert any(i["subject"] == "Electricity bill for October" for i in g["bills_payments"])
    assert out["counts"]["newsletters_updates"] >= 1


def test_attachments_read_and_go_to_phone(box):
    ctx = conv_ctx()
    m = run("email_read", {"id": ref("104")}, ctx)
    att = m["attachments"][0]
    assert att["name"] == "bill.pdf" and att["size"] > 0
    text = run("email_attachment", {"email_id": ref("104"), "attachment_id": att["id"], "do": "read"}, ctx)
    assert text["kind"] == "pdf" and "1540" in text["text"]
    x = run("email_read", {"id": ref("105")}, ctx)["attachments"][0]
    sheet = run("email_attachment", {"email_id": ref("105"), "attachment_id": x["id"]}, ctx)
    assert sheet["kind"] == "excel" and "sita@example.in" in sheet["text"]
    out = run("email_attachment", {"email_id": ref("104"), "attachment_id": att["id"], "do": "phone"}, ctx)
    assert out["sent_to_phone"] == "bill.pdf"
    card = _events(ctx.conversation_id, "pc_file")[-1]
    assert card["name"] == "bill.pdf" and card["url"].startswith("/api/pc/files/")


def test_organise_and_delete_needs_approval(bz, box):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    run("email_action", {"ids": [ref("103")], "action": "archive"}, ctx)
    assert box.msgs["103"]["folder"] == "archive"
    run("email_action", {"ids": [ref("101")], "action": "move", "folder": "Vendors"}, ctx)
    assert box.msgs["101"]["folder"] == "Vendors"
    out = run("email_delete", {"ids": [ref("102")]}, ctx)
    assert out["needs_approval"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "1 email delete karein?" and "Your OTP for login" in json.dumps(card)
    assert box.msgs["102"]["folder"] == "inbox"                   # not deleted before the tap
    bz["svc"].decide("default", card["id"], "approve")
    assert box.msgs["102"]["folder"] == "trash"


# ---------------- sending ----------------
def test_send_with_attachment_signature_and_follow_up(box):
    from app import main
    from app.mailbox.accounts import set_signature
    box.signature = "Meghana Ingle\nDirector, FNW"
    ctx = conv_ctx()
    out = run("email_draft", {"to": "ramesh@vendor.in", "subject": "Bill copy", "body": "Bill attach hai.",
                              "attachments": [{"email_id": ref("104"), "attachment_id": "1"}], "follow_up_days": 2}, ctx)
    assert out["attachments"] == ["bill.pdf"]
    with TestClient(main.app) as c:
        pend = c.get("/api/emails/pending").json()["emails"]
        mine = [e for e in pend if e["id"] == out["draft_id"]][0]
        assert mine["body"].endswith("Director, FNW") and mine["attachments"][0]["name"] == "bill.pdf"
        r = c.post(f"/api/emails/{out['draft_id']}/send", json={"body": mine["body"] + "\n\nPS: jaldi dekhiye"})
        assert r.status_code == 200 and r.json()["status"] == "sent", r.text
    msg, _ = box.sent[0]
    assert msg["To"] == "ramesh@vendor.in" and "PS: jaldi dekhiye" in msg.get_body(("plain",)).get_content()
    files = [p for p in msg.iter_attachments()]
    assert files[0].get_filename() == "bill.pdf" and files[0].get_payload(decode=True).startswith(b"%PDF")
    assert msg["From"].endswith("<meghana@fnw.in>")
    with session() as s:
        w = s.query(MailWatch).one()
        assert w.mode == "their_reply" and w.status == "waiting" and w.peer == "ramesh@vendor.in"
        w.due_at = now() - timedelta(minutes=1)
    from app.mailbox import service as ms
    assert ms.check_watches() == 1                                 # nobody replied: user is told
    assert any("jawab nahi diya" in (n or "") for n in _notices(ctx.conversation_id))
    _ = set_signature


def test_reply_marks_watch_replied_silently(box):
    from app.mailbox import service as ms
    ctx = conv_ctx()
    out = run("email_follow_up", {"action": "add", "email_id": ref("101"), "days": 1}, ctx)
    assert out["follow_up"]["mode"] == "my_reply"                  # a mail the user received: remind them to reply
    with session() as s:
        s.query(MailWatch).update({"due_at": now() - timedelta(minutes=1)})
    box.reply_state = {"from_them": False, "from_me": True}
    before = len(_notices(ctx.conversation_id))
    assert ms.check_watches() == 0
    assert len(_notices(ctx.conversation_id)) == before
    with session() as s:
        assert s.query(MailWatch).one().status == "replied"


def test_scheduled_send_waits_for_its_time(box):
    from app import main
    from app.mailbox import service as ms
    ctx = conv_ctx()
    out = run("email_draft", {"to": "ramesh@vendor.in", "subject": "Kal subah", "body": "Good morning",
                              "send_at": (now() + timedelta(days=1)).astimezone().strftime("%Y-%m-%dT%H:%M")}, ctx)
    with TestClient(main.app) as c:
        r = c.post(f"/api/emails/{out['draft_id']}/send")
        assert r.json()["status"] == "scheduled"
    assert box.sent == []
    assert ms.send_due_scheduled() == 0
    with session() as s:
        s.get(EmailDraft, out["draft_id"]).send_at = now() - timedelta(minutes=1)
    assert ms.send_due_scheduled() == 1 and box.sent[0][0]["Subject"] == "Kal subah"


def test_names_resolve_from_past_mail(box):
    ctx = conv_ctx()
    run("email_read", {"id": ref("101")}, ctx)                      # learns Ramesh Patil
    out = run("email_draft", {"to": "Ramesh", "subject": "Hi", "body": "Namaste"}, ctx)
    assert out["to"] == "ramesh@vendor.in"
    with pytest.raises(ToolError, match="nahi mila"):
        run("email_draft", {"to": "Kishore", "subject": "Hi", "body": "x"}, ctx)
    assert run("email_contacts", {"query": "ram"}, ctx)["contacts"][0]["email"] == "ramesh@vendor.in"


def test_forward_carries_attachments(box):
    out = run("email_forward", {"id": ref("104"), "to": "ca@accounts.in", "note": "Please file this"}, conv_ctx())
    assert out["subject"] == "Fwd: Electricity bill for October" and out["attachments"] == ["bill.pdf"]
    with session() as s:
        d = s.get(EmailDraft, out["draft_id"])
        assert "Forwarded message" in d.body and d.body.startswith("Please file this")


def test_draft_needs_recipient(box):
    with pytest.raises(ToolError, match="Kis email"):
        run("email_draft", {"body": "hello"}, conv_ctx())


def test_cancelled_draft_is_never_sent(box):
    from app import main
    did = run("email_draft", {"to": "x@y.in", "subject": "s", "body": "b"}, conv_ctx())["draft_id"]
    with TestClient(main.app) as c:
        assert c.post(f"/api/emails/{did}/cancel").status_code == 200
        assert all(e["id"] != did for e in c.get("/api/emails/pending").json()["emails"])
        assert c.post(f"/api/emails/{did}/send").status_code == 502
    assert box.sent == []


# ---------------- bulk mail ----------------
def test_bulk_mail_from_excel_after_approval(bz, box, monkeypatch):  # noqa: F811
    from app.mailbox import service as ms
    monkeypatch.setenv("MAIL_BULK_PER_MINUTE", "6000")
    from app.config import get_settings
    get_settings.cache_clear()
    ctx = Ctx("default", bz["conv"])
    with pytest.raises(ToolError, match="gst"):
        run("email_bulk", {"subject": "Hi", "body": "{{gst}}", "source": {"email_id": ref("105"), "attachment_id": "1"}}, ctx)
    out = run("email_bulk", {"subject": "Diwali offer for {{name}}", "body": "Namaste {{Name}}, aapka balance Rs {{amount}} hai.",
                             "source": {"email_id": ref("105"), "attachment_id": "1"}}, ctx)
    assert out["recipients"] == 2 and out["invalid_skipped"] == 1        # duplicate and bad address dropped
    assert out["sample_body"].startswith("Namaste Raju, aapka balance Rs 500")
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "2 logon ko email bhejein?"
    assert ms.bulk_tick() == 0 and box.sent == []                         # nothing before approval
    bz["svc"].decide("default", card["id"], "approve")
    for _ in range(5):
        ms._bulk_last.clear()
        ms.bulk_tick()
    sent = {m["To"]: m.get_body(("plain",)).get_content() for m, _ in box.sent}
    assert set(sent) == {"raju@example.in", "sita@example.in"}
    assert "Rs 750" in sent["sita@example.in"] and "Raju" not in sent["sita@example.in"]
    assert all("," not in to for to in sent)                              # each person gets their own mail
    assert run("email_bulk_status", {"bulk_id": out["bulk_id"]}, ctx)["status"] == "done"
    assert any("poora: 2 ko gaya" in (n or "") for n in _notices(bz["conv"]))


# ---------------- settings ----------------
def test_daily_summary_routine_and_signature(box):
    ctx = conv_ctx()
    out = run("email_accounts", {"daily_summary": "09:00"}, ctx)
    assert "daily inbox summary at 09:00" in out["changed"]
    from app.db import Routine
    with session() as s:
        r = s.query(Routine).filter(Routine.status == "active").one()
        assert r.title == "Inbox summary" and "email_triage" in r.instruction
    run("email_accounts", {"daily_summary": "off"}, ctx)
    with session() as s:
        assert s.query(Routine).filter(Routine.status == "active").count() == 0


def test_no_mailbox_tells_user_where_to_connect(env):
    with pytest.raises(ToolError, match="Profile > Email"):
        run("email_check", {}, Ctx("someone", "c1"))


# ---------------- accounts: IMAP, Gmail and Outlook ----------------
def test_connect_imap_stores_password_encrypted(env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    from app.db import MailAccount
    from app.mailbox.imap import ImapBox
    checked = []
    monkeypatch.setattr(ImapBox, "check", lambda self: checked.append((self.address, self.imap_host, self.smtp_host)))
    with TestClient(main.app) as c:
        r = c.post("/api/mail/accounts/imap", json={"address": "office@newtika.in", "password": "abcd efgh"})
        assert r.status_code == 200, r.text
        acc = r.json()["accounts"][0]
        assert acc["address"] == "office@newtika.in" and acc["kind"] == "imap" and acc["default"]
    assert checked == [("office@newtika.in", "imap.newtika.in", "smtp.newtika.in")]
    with session() as s:
        row = s.query(MailAccount).one()
        assert row.password_enc and "abcd" not in row.password_enc
        key = row.id
    with TestClient(main.app) as c:
        accs = c.patch(f"/api/mail/accounts/{key}", json={"signature": "— Meghana, FNW"}).json()["accounts"]
        assert accs[0]["signature"] == "— Meghana, FNW"
    from app.mailbox.accounts import boxes
    assert boxes("default")[0].password == "abcd efgh"           # a custom-domain password is kept exactly


def _mock(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_gmail_link_then_read_and_send(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    from app.mailbox import accounts as ma
    raw = _raw(("Ramesh", "ramesh@vendor.in"), "me@gmail.com", "Hello", "Kaise ho?")
    calls = []

    def handler(req: httpx.Request):
        calls.append((req.method, req.url.path))
        if req.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at1", "refresh_token": "rt1", "expires_in": 3600,
                                             "scope": "openid email https://www.googleapis.com/auth/gmail.modify"})
        if req.url.host == "openidconnect.googleapis.com":
            return httpx.Response(200, json={"email": "me@gmail.com", "name": "Meghana"})
        assert req.headers["authorization"] == "Bearer at1"
        p = req.url.path
        if p.endswith("/messages") and req.method == "GET":
            assert "in:inbox" in req.url.params["q"] and "is:unread" in req.url.params["q"]
            return httpx.Response(200, json={"messages": [{"id": "g1", "threadId": "th1"}]})
        if p.endswith("/messages/g1") and req.url.params.get("format") == "metadata":
            return httpx.Response(200, json={"id": "g1", "threadId": "th1", "labelIds": ["INBOX", "UNREAD"], "snippet": "Kaise ho?",
                                             "payload": {"headers": [{"name": "From", "value": "Ramesh <ramesh@vendor.in>"},
                                                                     {"name": "Subject", "value": "Hello"}]}})
        if p.endswith("/messages/g1") and req.url.params.get("format") == "raw":
            return httpx.Response(200, json={"raw": base64.urlsafe_b64encode(raw).decode()})
        if p.endswith("/messages/g1") and req.url.params.get("format") == "minimal":
            return httpx.Response(200, json={"threadId": "th1"})
        if p.endswith("/messages/batchModify"):
            return httpx.Response(204)
        if p.endswith("/messages/send"):
            body = json.loads(req.content)
            assert body["threadId"] == "th1"
            sent = base64.urlsafe_b64decode(body["raw"] + "==")
            assert b"In-Reply-To" in sent and b"ramesh@vendor.in" in sent
            return httpx.Response(200, json={"id": "g2", "threadId": "th1"})
        return httpx.Response(404)
    ma.set_http(_mock(handler))
    try:
        with TestClient(main.app) as c:
            url = c.get("/api/mail/accounts/link", params={"provider": "google"}).json()["url"]
            assert "gmail.modify" in url and "state=mail_" in url
            state = httpx.URL(url).params["state"]
            page = c.get("/auth/google/callback", params={"code": "c0de", "state": state})
            assert page.status_code == 200 and "me@gmail.com" in page.text
            accs = c.get("/api/mail/accounts").json()["accounts"]
            assert accs[0]["kind"] == "gmail" and accs[0]["address"] == "me@gmail.com"
        ctx = conv_ctx()
        lst = run("email_check", {"unread_only": True}, ctx)
        mid = lst["emails"][0]["id"]
        assert lst["emails"][0]["subject"] == "Hello" and lst["emails"][0]["unread"]
        out = run("email_draft", {"reply_to_id": mid, "body": "Badhiya!"}, ctx)
        with TestClient(main.app) as c:
            assert c.post(f"/api/emails/{out['draft_id']}/send").json()["status"] == "sent"
        assert ("POST", "/gmail/v1/users/me/messages/send") in calls
    finally:
        ma.set_http(None)


def test_outlook_box_sends_mime_through_graph():
    from app.mailbox.outlook import OutlookBox
    seen = {}

    def handler(req):
        seen["path"], seen["ctype"] = req.url.path, req.headers["content-type"]
        seen["mime"] = base64.b64decode(req.content)
        return httpx.Response(202)
    b = OutlookBox("mbx_o", "me@outlook.com", lambda force: "tok", "Me", "", _mock(handler))
    msg = mime.build(from_addr="me@outlook.com", from_name="Me", to="a@b.in", bcc="secret@b.in", subject="नमस्ते",
                     body="Hello", files=[("a.txt", "text/plain", b"hi")])
    b.send(msg)
    assert seen["path"] == "/v1.0/me/sendMail" and seen["ctype"] == "text/plain"
    assert b"a@b.in" in seen["mime"] and b"a.txt" in seen["mime"]


def test_old_database_gains_new_columns(tmp_path, monkeypatch):
    import sqlite3
    dbf = tmp_path / "old.db"
    con = sqlite3.connect(dbf)
    con.execute("CREATE TABLE email_drafts (id VARCHAR(40) PRIMARY KEY, tenant_id VARCHAR(64), conversation_id VARCHAR(40), "
                "to_addr VARCHAR(1000), cc_addr VARCHAR(1000), subject VARCHAR(500), body TEXT, in_reply_to VARCHAR(500), "
                "\"references\" TEXT, status VARCHAR(16), error TEXT, created_at DATETIME, sent_at DATETIME)")
    con.commit()
    con.close()
    from app import db
    db.init_db(f"sqlite:///{dbf}")
    cols = {r[1] for r in sqlite3.connect(dbf).execute("PRAGMA table_info(email_drafts)")}
    assert {"attachments", "send_at", "account", "thread_id", "follow_up_days", "bcc_addr"} <= cols


def test_mime_roundtrip_hindi_and_attachments():
    raw = _raw(("रमेश", "r@x.in"), "m@y.in", "बिल भेजिए", "कृपया बिल भेजिए", files=[("रसीद.txt", "text/plain", "राशि 500".encode())])
    p = mime.parse(raw)
    assert p["from"] == "रमेश" and p["subject"] == "बिल भेजिए" and "कृपया" in p["body"]
    assert p["attachments"][0]["name"] == "रसीद.txt"
    name, mt, data = mime.get_attachment(raw, p["attachments"][0]["id"])
    assert data.decode() == "राशि 500"


# ---------------- IMAP (the server .env mailbox and "Other email") ----------------
class FakeIMAP:
    """Answers like imaplib.IMAP4_SSL does (same tuple / literal shapes)."""
    store = {}

    def __init__(self, host, port, timeout=None):
        self.capabilities = ("IMAP4REV1", "MOVE", "UIDPLUS")
        self.cur = None

    def login(self, u, p):
        if p != "app-pass":
            import imaplib
            raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")
        return "OK", [b"ok"]

    def logout(self):
        return "BYE", []

    def list(self):
        return "OK", [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Sent Mail"',
                      b'(\\HasNoChildren \\Trash) "/" "[Gmail]/Trash"', b'(\\All \\HasNoChildren) "/" "[Gmail]/All Mail"']

    def select(self, name, readonly=False):
        self.cur = name.strip('"')
        return "OK", [str(len(self.store.get(self.cur, {}))).encode()]

    def create(self, name):
        self.store.setdefault(name.strip('"'), {})
        return "OK", []

    def append(self, *a):
        return "OK", []

    def expunge(self):
        return "OK", []

    def uid(self, cmd, *args):
        box = self.store.setdefault(self.cur, {})
        cmd = cmd.upper()
        if cmd == "SEARCH":
            crit = " ".join(str(a) for a in args[1:])
            uids = [u for u, m in box.items() if ("UNSEEN" not in crit or "\\Seen" not in m["flags"])]
            return "OK", [" ".join(uids).encode()]
        if cmd == "FETCH":
            uid = args[0].decode() if isinstance(args[0], bytes) else args[0]
            m = box[uid]
            if "BODY.PEEK[]" in args[1]:
                return "OK", [(f"1 (UID {uid} BODY[] {{{len(m['raw'])}}}".encode(), m["raw"]), b")"]
            hdr, _, text = m["raw"].partition(b"\n\n")
            flags = " ".join(m["flags"])
            out = [(f"1 (UID {uid} FLAGS ({flags}) BODY[HEADER.FIELDS (FROM TO)] {{{len(hdr)}}}".encode(), hdr + b"\r\n")]
            if "TEXT" in args[1]:
                out.append((f" BODY[TEXT]<0> {{{len(text)}}}".encode(), text))
            out.append(b")")
            return "OK", out
        if cmd == "STORE":
            for u in args[0].split(","):
                if args[1].startswith("+"):
                    box[u]["flags"].add(args[2].strip("()"))
                else:
                    box[u]["flags"].discard(args[2].strip("()"))
            return "OK", []
        if cmd == "MOVE":
            dest = self.store.setdefault(args[1].strip('"'), {})
            for u in args[0].split(","):
                dest[u] = box.pop(u)
            return "OK", []
        raise AssertionError(cmd)


def test_owner_env_mailbox_over_imap(env, monkeypatch):
    import imaplib
    from app.mailbox import imap as mi
    raw = _raw(("Ramesh", "ramesh@vendor.in"), "owner@gmail.com", "Quotation", "Kya rate hai?\nDhanyavaad",
               files=[("rate.csv", "text/csv", b"item,rate\nrouter,1200\n")]).replace(b"\r\n", b"\n")
    FakeIMAP.store = {"INBOX": {"7": {"raw": raw, "flags": set()}}}
    monkeypatch.setattr(imaplib, "IMAP4_SSL", FakeIMAP)
    monkeypatch.setenv("EMAIL_ADDRESS", "owner@gmail.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "app-pass")
    from app.config import get_settings
    get_settings.cache_clear()
    ctx = conv_ctx()
    lst = run("email_check", {"unread_only": True}, ctx)
    e = lst["emails"][0]
    assert e["id"] == "env~7" and e["from_email"] == "ramesh@vendor.in" and e["unread"] and e["subject"] == "Quotation"
    full = run("email_read", {"id": "env~7"}, ctx)
    assert "Kya rate hai" in full["body"] and full["attachments"][0]["name"] == "rate.csv"
    assert "\\Seen" in FakeIMAP.store["INBOX"]["7"]["flags"]
    txt = run("email_attachment", {"email_id": "env~7", "attachment_id": full["attachments"][0]["id"]}, ctx)
    assert "router,1200" in txt["text"]
    run("email_action", {"ids": ["env~7"], "action": "archive"}, ctx)
    assert "7" in FakeIMAP.store["[Gmail]/All Mail"] and "7" not in FakeIMAP.store["INBOX"]
    arch = run("email_check", {"folder": "archive"}, ctx)["emails"][0]
    assert arch["id"].startswith("env~7@") and mi.split_id(arch["id"].split("~", 1)[1]) == ("[Gmail]/All Mail", "7")
    # a non-owner never sees the server's mailbox
    with pytest.raises(ToolError, match="juda nahi"):
        run("email_check", {}, Ctx("usr_other", "c2"))
    # wrong password gives a clear message
    monkeypatch.setenv("EMAIL_PASSWORD", "wrong")
    get_settings.cache_clear()
    with pytest.raises(ToolError, match="App password"):
        run("email_check", {}, ctx)
