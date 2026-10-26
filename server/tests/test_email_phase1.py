"""v0.181.0 Gmail poora: thread view, rich markdown mail (safe HTML + inline images), drafts inside Gmail,
labels CRUD (delete behind a card), mark-important / category tabs, unified inbox, undo-send window,
Drive files as attachments, picture attachments read by OCR."""
import base64
import email
import email.utils
import json

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError
from app.db import EmailDraft, now, session
from app.mailbox import mime
from tests.test_email import FakeBox, _raw, box, ref, run  # noqa: F401
from tests.test_bazar import _events, bz  # noqa: F401
from tests.test_life import conv_ctx


def _raw_at(frm, to, subject, body, when):
    """A raw mail with a definite Date header (replaces the one build() set)."""
    m = email.message_from_bytes(_raw(frm, to, subject, body))
    del m["Date"]
    m["Date"] = email.utils.format_datetime(when)
    return m.as_bytes()


# ---------------- markdown-lite -> html / plain ----------------
def test_md_to_html_safe_and_plain():
    md = ("## Quote\n\nNamaste **Ramesh**, *offer* niche hai:\n\n- _router_ ka bhav `Rs 1200`\n"
          "- [FNW site](https://fnw.in)\n2. Second point\n\n<script>alert(1)</script>")
    html = mime.md_to_html(md)
    assert "<h3>Quote</h3>" in html and "<b>Ramesh</b>" in html and "<i>offer</i>" in html
    assert "<code>Rs 1200</code>" in html and '<a href="https://fnw.in">FNW site</a>' in html
    assert "<li><i>router</i> ka bhav" in html and "<li>Second point</li>" in html and "<ol>" in html
    assert "<script>" not in html and "&lt;script&gt;" in html
    plain = mime.md_to_plain(md)
    assert "**" not in plain and "*" not in plain and "`" not in plain and "#" not in plain.split("\n")[0]
    assert "FNW site (https://fnw.in)" in plain and "Ramesh" in plain and "Second point" in plain


def test_build_html_and_inline_image():
    img = b"\x89PNG\r\n\x1a\n" + b"i" * 40
    msg = mime.build(from_addr="me@fnw.in", from_name="Me", to="a@b.in", subject="Rich",
                     body="plain side", html_body="<p>hi <b>there</b> <img src='cid:logo1'></p>",
                     inline=[("logo.png", "image/png", img, "logo1")],
                     files=[("x.pdf", "application/pdf", b"%PDF")])
    types = [p.get_content_type() for p in msg.walk()]
    assert "multipart/alternative" in types and "text/plain" in types and "text/html" in types
    assert "multipart/related" in types and "image/png" in types and "application/pdf" in types
    html_part = next(p for p in msg.walk() if p.get_content_type() == "text/html")
    assert "cid:logo1" in html_part.get_content().replace("<", "").replace("%3C", "<") or "logo1" in html_part.get_payload()
    atts = list(msg.iter_attachments())
    assert [a.get_filename() for a in atts] == ["x.pdf"]
    plain = msg.get_body(("plain",)).get_content()
    assert plain.strip() == "plain side"


# ---------------- a FakeBox that speaks the v0.181.0 Gmail abilities ----------------
class GmailishBox(FakeBox):
    def __init__(self, key="mbx_test", address="meghana@fnw.in"):
        super().__init__(key, address)
        self.drafts = []
        self.labels = [{"id": "L1", "name": "Vendors", "type": "user"}]
        self.important = set()
        self.cats = {}

    def thread(self, mid):
        tid = self.msgs[mid]["thread"]
        msgs = [{"id": m, "thread_id": self.msgs[m]["thread"], **mime.parse(self.msgs[m]["raw"])}
                for m in self.msgs if self.msgs[m]["thread"] == tid]
        return {"thread_id": tid, "count": len(msgs), "messages": msgs}

    def save_draft(self, msg, thread_id=None):
        self.drafts.append(msg)
        return {"draft_id": f"d{len(self.drafts)}", "message_id": msg["Message-ID"], "thread_id": thread_id or ""}

    def drafts_list(self, limit=10):
        return [{"draft_id": f"d{i + 1}", **mime.parse(m.as_bytes())} for i, m in enumerate(self.drafts)][:limit]

    def draft_delete(self, did):
        self.drafts.pop(int(did[1:]) - 1)
        return {}

    def label_create(self, name):
        self.labels.append({"id": f"L{len(self.labels) + 1}", "name": name, "type": "user"})
        return {"id": f"L{len(self.labels)}", "name": name}

    def label_rename(self, name, new_name):
        for lb in self.labels:
            if lb["name"] == name:
                lb["name"] = new_name
                return

    def label_delete(self, name):
        self.labels = [lb for lb in self.labels if lb["name"] != name]

    def folders(self):
        from app.mailbox.base import FOLDERS
        return list(FOLDERS) + sorted(lb["name"] for lb in self.labels)

    def mark_important(self, ids, on):
        for i in ids:
            (self.important.add if on else self.important.discard)(i)

    def set_category(self, ids, category):
        from app.mailbox.base import MailError
        if category not in GmailishBox.CATS:
            raise MailError("category personal / social / updates / forums / promotions mein se hai")
        for i in ids:
            self.cats[i] = category

    CATS = {"personal", "social", "updates", "forums", "promotions"}


@pytest.fixture
def gbox(env, monkeypatch):
    b = GmailishBox()
    b.add("201", _raw(("Ramesh Patil", "ramesh@vendor.in"), "meghana@fnw.in", "Quotation for 10 routers",
                      "Namaste, quotation chahiye?", msgid="<abc@vendor.in>"), thread="tq")
    b.add("202", _raw(("Meghana Ingle", "meghana@fnw.in"), "ramesh@vendor.in", "Re: Quotation for 10 routers",
                      "Bhej rahi hoon aaj hi."), unread=False, thread="tq")
    b.add("203", _raw(("Swati", "swati@fnw.in"), "meghana@fnw.in", "Haan, rate theek hai",
                      "Rate theek hai, aage badho."), thread="tq")
    import app.mailbox.accounts as ma
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    return b


# ---------------- thread view ----------------
def test_thread_view(gbox):
    out = run("email_thread", {"id": ref("201")}, conv_ctx())
    assert out["count"] == 3 and out["thread_id"] == "tq"
    subs = [m["subject"] for m in out["messages"]]
    assert subs[0] == "Quotation for 10 routers" and subs[2] == "Haan, rate theek hai"
    assert all(m["id"].startswith("mbx_test~") for m in out["messages"])
    assert "quotation chahiye" in out["messages"][0]["body"].lower()


def test_thread_not_supported_on_plain_box(box):  # noqa: F811  (base Box raises a clean line)
    with pytest.raises(ToolError, match="Gmail"):
        run("email_thread", {"id": ref("101")}, conv_ctx())


# ---------------- rich markdown send ----------------
def test_rich_markdown_send(gbox):
    from app import main
    ctx = conv_ctx()
    out = run("email_draft", {"to": "ramesh@vendor.in", "subject": "Offer", "markdown": True,
                              "body": "Namaste **Ramesh**,\n\n- router: `Rs 1200`\n- [site](https://fnw.in)"}, ctx)
    with TestClient(main.app) as c:
        r = c.post(f"/api/emails/{out['draft_id']}/send")
        assert r.status_code == 200 and r.json()["status"] == "sent", r.text
    msg, _ = gbox.sent[0]
    html_part = next(p for p in msg.walk() if p.get_content_type() == "text/html")
    body_html = html_part.get_content()
    assert "<b>Ramesh</b>" in body_html and "<code>Rs 1200</code>" in body_html and "fnw.in" in body_html
    plain = msg.get_body(("plain",)).get_content()
    assert "**" not in plain and "Rs 1200" in plain


# ---------------- drafts inside Gmail ----------------
def test_save_to_gmail_draft(gbox):
    out = run("email_draft", {"to": "ramesh@vendor.in", "subject": "Draft dono jagah", "body": "Dekh lo.",
                              "save_to_gmail": True}, conv_ctx())
    assert "Drafts folder" in out["note"]
    assert len(gbox.drafts) == 1 and gbox.drafts[0]["Subject"] == "Draft dono jagah"
    with session() as s:
        assert s.get(EmailDraft, out["draft_id"]).status == "pending"   # nothing is sent


def test_gmail_drafts_list_delete_card(bz, gbox):  # noqa: F811
    run("email_draft", {"to": "x@y.in", "subject": "Gmail ka draft", "body": "b", "save_to_gmail": True},
        Ctx("default", bz["conv"]))
    lst = run("email_drafts", {"action": "list"}, Ctx("default", bz["conv"]))
    assert lst["count"] == 1 and lst["drafts"][0]["subject"] == "Gmail ka draft"
    did = lst["drafts"][0]["draft_id"]
    out = run("email_drafts", {"action": "delete", "id": f"mbx_test~{did}"}, Ctx("default", bz["conv"]))
    assert out["needs_approval"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Gmail draft delete karein?"
    assert len(gbox.drafts) == 1                                     # nothing before the tap
    bz["svc"].decide("default", card["id"], "approve")
    assert gbox.drafts == []


# ---------------- labels ----------------
def test_labels_crud_and_delete_card(bz, gbox):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("email_label", {"action": "create", "name": "Bill"}, ctx)
    assert "Bill" in out["labels"]
    run("email_label", {"action": "rename", "name": "Bill", "new_name": "Bills 2026"}, ctx)
    assert "Bills 2026" in [lb["name"] for lb in gbox.labels]
    out = run("email_label", {"action": "delete", "name": "Bills 2026"}, ctx)
    assert out["needs_approval"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Label 'Bills 2026' hatayein?"
    bz["svc"].decide("default", card["id"], "approve")
    assert "Bills 2026" not in [lb["name"] for lb in gbox.labels]


# ---------------- importance + category ----------------
def test_mark_important_and_category(gbox):
    ctx = conv_ctx()
    run("email_action", {"ids": [ref("201")], "action": "mark_important"}, ctx)
    assert "201" in gbox.important
    run("email_action", {"ids": [ref("203")], "action": "mark_not_important"}, ctx)
    run("email_action", {"ids": [ref("203")], "action": "category", "folder": "social"}, ctx)
    assert gbox.cats["203"] == "social"
    with pytest.raises(ToolError, match="category"):
        run("email_action", {"ids": [ref("203")], "action": "category", "folder": "nonsense"}, ctx)


# ---------------- unified inbox ----------------
def test_unified_inbox(env, monkeypatch):
    import app.mailbox.accounts as ma
    from datetime import datetime, timezone, timedelta as _td
    ist = timezone(_td(hours=5, minutes=30))
    a, b = GmailishBox(), FakeBox(key="mbx_two", address="office@newtika.in")
    a.add("301", _raw_at(("Old", "old@x.in"), "meghana@fnw.in", "Old one", "purana",
                         datetime(2026, 10, 24, 9, 0, tzinfo=ist)), thread="ta")
    b.add("302", _raw_at(("New", "new@x.in"), "office@newtika.in", "New one", "naya",
                         datetime(2026, 10, 25, 9, 0, tzinfo=ist)))
    monkeypatch.setattr(ma, "boxes", lambda tenant: [a, b] if tenant == "default" else [])
    out = run("email_check", {"account": "all"}, conv_ctx())
    assert out["account"] == "all" and out["count"] == 2
    ids = [e["id"] for e in out["emails"]]
    assert ids == ["mbx_two~302", "mbx_test~301"]                    # newest first across mailboxes
    assert all(e["account"] in ("meghana@fnw.in", "office@newtika.in") for e in out["emails"])
    broken = GmailishBox()
    monkeypatch.setattr(broken, "list", lambda *ar, **kw: (_ for _ in ()).throw(Exception("down")))
    monkeypatch.setattr(ma, "boxes", lambda tenant: [a, broken] if tenant == "default" else [])
    out = run("email_check", {"account": "all"}, conv_ctx())
    assert out["count"] >= 1 and out["errors"] and "down" in out["errors"][0]


# ---------------- undo send ----------------
def test_undo_window_and_cancel(bz, gbox):  # noqa: F811
    from app import main
    from app.mailbox import service as ms
    assert ms.set_undo_seconds("default", 10) == 10
    ctx = Ctx("default", bz["conv"])
    out = run("email_draft", {"to": "ramesh@vendor.in", "subject": "Undo test", "body": "b"}, ctx)
    with TestClient(main.app) as c:
        r = c.post(f"/api/emails/{out['draft_id']}/send")
        assert r.json()["status"] == "undo_window" and r.json()["undo_seconds"] == 10
        assert c.post(f"/api/emails/{out['draft_id']}/cancel").status_code == 200
    assert gbox.sent == []
    assert ms.send_due_scheduled() == 0                              # cancelled inside the window: never goes
    run("email_accounts", {"undo_seconds": 0}, ctx)
    assert ms.get_undo_seconds("default") == 0


def test_undo_window_sends_after_wait(bz, gbox):  # noqa: F811
    from app import main
    from app.mailbox import service as ms
    from app.db import EmailDraft
    ms.set_undo_seconds("default", 60)
    ctx = Ctx("default", bz["conv"])
    out = run("email_draft", {"to": "ramesh@vendor.in", "subject": "Undo phir bheja", "body": "b"}, ctx)
    with TestClient(main.app) as c:
        assert c.post(f"/api/emails/{out['draft_id']}/send").json()["status"] == "undo_window"
    assert ms.send_due_scheduled() == 0 and gbox.sent == []          # still inside the window
    with session() as s:
        s.get(EmailDraft, out["draft_id"]).send_at = now()               # window over (worker fires at <= now)
    assert ms.send_due_scheduled() == 1 and gbox.sent[0][0]["Subject"] == "Undo phir bheja"
    ms.set_undo_seconds("default", 0)


# ---------------- Drive files as attachments ----------------
class FakeDrive:
    def get(self, fid):
        return {"name": "Brochure.pdf", "mimeType": "application/pdf"}

    def download(self, fid):
        return b"%PDF-drive-bytes"


def test_drive_file_attach(gbox, monkeypatch):
    import app.drive.accounts as da
    monkeypatch.setattr(da, "get_client", lambda tenant, which=None: FakeDrive())
    from app import main
    ctx = conv_ctx()
    out = run("email_draft", {"to": "ramesh@vendor.in", "subject": "Brochure", "body": "Attached.",
                              "attachments": [{"drive_file_id": "drv1"}]}, ctx)
    assert out["attachments"] == ["Brochure.pdf"]
    with TestClient(main.app) as c:
        assert c.post(f"/api/emails/{out['draft_id']}/send").json()["status"] == "sent"
    msg, _ = gbox.sent[0]
    atts = list(msg.iter_attachments())
    assert atts[0].get_filename() == "Brochure.pdf" and atts[0].get_payload(decode=True) == b"%PDF-drive-bytes"


# ---------------- picture attachment read by OCR ----------------
def test_image_attachment_ocr(gbox, monkeypatch):
    from app import ocr
    import app.net.media as media
    monkeypatch.setattr(ocr, "read", lambda data, lang: {"text": "TOTAL Rs 500", "conf": 90.0, "langs": ["en"], "good": True})
    monkeypatch.setattr(media, "understand", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no vision when OCR is good")))
    png = b"\x89PNG\r\n\x1a\n" + b"p" * 60
    gbox.add("401", _raw(("Store", "store@x.in"), "meghana@fnw.in", "Receipt photo", "dekh lo",
                         files=[("receipt.png", "image/png", png)]))
    m = run("email_read", {"id": ref("401")}, conv_ctx())
    att = m["attachments"][0]
    assert att["name"] == "receipt.png"
    out = run("email_attachment", {"email_id": ref("401"), "attachment_id": att["id"], "do": "read"}, conv_ctx())
    assert out["kind"] == "image" and "Rs 500" in out["text"] and out["ocr"]["good"] is True


def test_image_attachment_falls_back_to_note(gbox, monkeypatch):
    from app import ocr
    import app.net.media as media
    monkeypatch.setattr(ocr, "read", lambda data, lang: None)
    monkeypatch.setattr(media, "understand", lambda *a, **k: None)
    png = b"\x89PNG\r\n\x1a\n" + b"q" * 60
    gbox.add("402", _raw(("Store", "store@x.in"), "meghana@fnw.in", "Blur photo", "kuch nahi",
                         files=[("blur.png", "image/png", png)]))
    m = run("email_read", {"id": ref("402")}, conv_ctx())
    att = m["attachments"][0]
    out = run("email_attachment", {"email_id": ref("402"), "attachment_id": att["id"], "do": "read"}, conv_ctx())
    assert out["kind"] == "image" and "note" in out and "text" not in out


# ---------------- settings + version ----------------
def test_undo_setting_tool(gbox):
    ctx = conv_ctx()
    out = run("email_accounts", {"undo_seconds": 30}, ctx)
    assert out["changed"] == ["undo window 30s"]
    from app.mailbox import service as ms
    assert ms.get_undo_seconds("default") == 30
    out = run("email_accounts", {"undo_seconds": 500}, ctx)          # capped at 60
    assert out["changed"] == ["undo window 60s"]
    out = run("email_accounts", {"undo_seconds": "off"}, ctx)
    assert out["changed"] == ["undo send off"] and ms.get_undo_seconds("default") == 0


def test_gmail_drafts_needs_id(bz, gbox):  # noqa: F811
    with pytest.raises(ToolError, match="id do"):
        run("email_drafts", {"action": "delete"}, Ctx("default", bz["conv"]))


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.185.3"
