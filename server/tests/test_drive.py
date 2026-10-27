"""Google Drive: connecting by Google sign-in, finding / listing / reading files, sending to phone or email, upload,
Google Docs, organising, and share / public link / trash behind confirm cards."""
import asyncio
import io
import json
import re
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

import app.drive.models  # noqa: F401  (tables)
from app.agent import drive_tools as dt
from app.agent.tools import Ctx, ToolError
from app.drive.client import FOLDER, GDOC, GSHEET, GSLIDES
from tests.test_life import conv_ctx

ME = "meghana@fnw.in"


def _pdf(text):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, text)
    c.save()
    return buf.getvalue()


class FakeDrive:
    def __init__(self):
        self.files = {}
        self.perms = {}
        self.comments_store: dict = {}      # fid -> [comment dicts]
        self.revs: dict = {}                # fid -> [revision dicts]
        self.n = 0
        self.pn = 0                         # permission id counter
        self.cn = 0                         # comment id counter
        self.add("root", "My Drive", FOLDER, parents=[])

    def add(self, fid, name, mime, parents=("root",), content=b"", **kw):
        self.files[fid] = {"id": fid, "name": name, "mimeType": mime, "parents": list(parents), "trashed": False,
                           "starred": False, "shared": False, "modifiedTime": f"2026-10-{10 + len(self.files):02d}T10:00:00Z",
                           "size": str(len(content)), "quotaBytesUsed": str(len(content)), "description": "",
                           "createdTime": "2026-10-01T09:00:00Z", "lastModifyingUser": {"displayName": "Meghana"},
                           "copyRequiresWriterPermission": False, "writersCanShare": True,
                           "webViewLink": f"https://drive.google.com/file/d/{fid}/view",
                           "owners": [{"displayName": "Meghana", "emailAddress": ME}], "_content": content, **kw}
        if mime in (GDOC, GSHEET, GSLIDES):
            self.revs[fid] = [{"id": "1", "modifiedTime": self.files[fid]["modifiedTime"],
                               "lastModifyingUser": {"displayName": "Meghana"}, "keepForever": False,
                               "mimeType": mime, "size": str(len(content))}]
        return self.files[fid]

    @staticmethod
    def _pub(f):
        return {k: v for k, v in f.items() if not k.startswith("_")}

    def _atom(self, f, a):
        a = a.strip()
        if a.startswith("(") and a.endswith(")"):
            return any(self._atom(f, x) for x in re.split(r"\s+or\s+", a[1:-1]))
        if a == "trashed = false":
            return not f["trashed"]
        if a == "trashed = true":
            return f["trashed"]
        if a == "starred = true":
            return f["starred"]
        if a == "sharedWithMe = true":
            return f.get("_shared_with_me", False)
        m = re.fullmatch(r"name contains '(.*)'", a)
        if m:
            return m.group(1).lower() in f["name"].lower()
        m = re.fullmatch(r"fullText contains '(.*)'", a)
        if m:
            return m.group(1).lower() in (f["name"] + f["_content"].decode("utf-8", "ignore")).lower()
        m = re.fullmatch(r"'(.*)' in parents", a)
        if m:
            return m.group(1) in f["parents"]
        m = re.fullmatch(r"mimeType (=|!=) '(.*)'", a)
        if m:
            return (f["mimeType"] == m.group(2)) == (m.group(1) == "=")
        m = re.fullmatch(r"mimeType contains '(.*)'", a)
        if m:
            return m.group(1) in f["mimeType"]
        m = re.fullmatch(r"modifiedTime > '(.*)'", a)
        if m:
            return True
        raise AssertionError(f"query atom not handled: {a}")

    def __call__(self, req: httpx.Request):
        u, p = req.url, req.url.params
        if u.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at", "refresh_token": "rt", "expires_in": 3600,
                                             "scope": "openid email https://www.googleapis.com/auth/drive"})
        if u.host == "openidconnect.googleapis.com":
            return httpx.Response(200, json={"email": ME, "name": "Meghana"})
        assert req.headers["authorization"] == "Bearer at"
        path = u.path
        if path == "/upload/drive/v3/files":
            boundary = req.headers["content-type"].split("boundary=")[1]
            parts = req.content.split(f"--{boundary}".encode())
            meta = json.loads(parts[1].split(b"\r\n\r\n", 1)[1].strip())
            media = parts[2].split(b"\r\n\r\n", 1)[1][:-2]
            self.n += 1
            mt = meta.get("mimeType") or parts[2].split(b"\r\n\r\n", 1)[0].split(b": ")[1].decode()
            f = self.add(f"up{self.n}", meta["name"], mt, parents=meta.get("parents") or ["root"], content=media)
            return httpx.Response(200, json=self._pub(f))
        path = path.removeprefix("/drive/v3")
        if path == "/about":
            return httpx.Response(200, json={"user": {"emailAddress": ME},
                                             "storageQuota": {"limit": str(15 * 1024 ** 3), "usage": str(3 * 1024 ** 3),
                                                              "usageInDrive": str(2 * 1024 ** 3), "usageInDriveTrash": "0"}})
        if path == "/files" and req.method == "GET":
            atoms = re.split(r"\s+and\s+(?![^(]*\))", p["q"])
            hits = [self._pub(f) for f in self.files.values() if f["id"] != "root" and all(self._atom(f, a) for a in atoms)]
            return httpx.Response(200, json={"files": hits[: int(p.get("pageSize", 100))]})
        if path == "/files" and req.method == "POST":
            body = json.loads(req.content)
            self.n += 1
            f = self.add(f"fo{self.n}", body["name"], body["mimeType"], parents=body.get("parents") or ["root"],
                         **({"shortcutDetails": body["shortcutDetails"]} if body.get("shortcutDetails") else {}))
            return httpx.Response(200, json=self._pub(f))
        if path == "/drives" and req.method == "GET":
            return httpx.Response(200, json={"drives": [{"id": "sd1", "name": "FNW Team Drive"}]})
        if path == "/files/emptyTrash" and req.method == "DELETE":
            for k in [k for k, v in self.files.items() if v["trashed"]]:
                self.files.pop(k)
                self.perms.pop(k, None)
                self.comments_store.pop(k, None)
            return httpx.Response(204)
        parts = path.split("/")          # /files/<id>[/<sub>]
        fid = parts[2]
        if fid not in self.files:
            return httpx.Response(404, json={"error": {"message": "File not found"}})
        f = self.files[fid]
        sub = parts[3] if len(parts) > 3 else ""
        if sub == "export":
            mt = p["mimeType"]
            if mt == "text/plain":
                return httpx.Response(200, content=f["_content"])
            return httpx.Response(200, content=b"PK-exported-" + mt.encode())
        if sub == "copy":
            body = json.loads(req.content or b"{}")
            self.n += 1
            nf = self.add(f"cp{self.n}", body.get("name", f["name"]), f["mimeType"], parents=body.get("parents") or f["parents"],
                          content=f["_content"])
            return httpx.Response(200, json=self._pub(nf))
        if sub == "permissions" and len(parts) > 4:      # /files/<id>/permissions/<pid>
            me = next((x for x in self.perms.get(fid, []) if x.get("id") == parts[4]), None)
            if me is None:
                return httpx.Response(404, json={"error": {"message": "Permission not found"}})
            if req.method == "PATCH":
                me["role"] = json.loads(req.content).get("role", me["role"])
                return httpx.Response(200, json=me)
            if req.method == "DELETE":
                self.perms[fid].remove(me)
                return httpx.Response(204)
        if sub == "comments":
            if req.method == "GET":
                return httpx.Response(200, json={"comments": self.comments_store.get(fid, [])})
            if req.method == "POST" and len(parts) == 4:
                body = json.loads(req.content)
                self.cn += 1
                cm = {"id": f"cm{self.cn}", "author": {"displayName": "Meghana", "emailAddress": ME},
                      "content": body["content"], "createdTime": "2026-10-27T10:00:00Z",
                      "modifiedTime": "2026-10-27T10:00:00Z", "resolved": False, "replies": []}
                self.comments_store.setdefault(fid, []).append(cm)
                return httpx.Response(200, json=cm)
            cm = next((x for x in self.comments_store.get(fid, []) if x["id"] == parts[4]), None)
            if cm is None:
                return httpx.Response(404, json={"error": {"message": "Comment not found"}})
            if len(parts) > 5 and req.method == "POST":        # .../comments/<cid>/replies
                rp = {"id": f"cr{self.cn}", "author": {"displayName": "Meghana"},
                      "content": json.loads(req.content)["content"], "createdTime": "2026-10-27T10:05:00Z",
                      "resolved": False}
                cm["replies"].append(rp)
                return httpx.Response(200, json=rp)
            if req.method == "PATCH":
                cm.update({k: v for k, v in json.loads(req.content).items() if k in ("content", "resolved")})
                return httpx.Response(200, json=cm)
            if req.method == "DELETE":
                self.comments_store[fid].remove(cm)
                return httpx.Response(204)
        if sub == "revisions":
            if req.method == "GET":
                return httpx.Response(200, json={"revisions": self.revs.get(fid, [])})
            rev = next((x for x in self.revs.get(fid, []) if x["id"] == parts[4]), None)
            if req.method == "PATCH" and rev is not None:
                rev["keepForever"] = json.loads(req.content).get("keepForever")
                return httpx.Response(200, json=rev)
            return httpx.Response(404, json={"error": {"message": "Revision not found"}})
        if sub == "permissions":
            if req.method == "POST":
                self.pn += 1
                self.perms.setdefault(fid, []).append({**json.loads(req.content), "notify": p.get("sendNotificationEmail"),
                                                       "id": f"perm{self.pn}"})
                f["shared"] = True
                return httpx.Response(200, json={"id": f"perm{self.pn}"})
            return httpx.Response(200, json={"permissions": self.perms.get(fid, [])})
        if req.method == "GET":
            if p.get("alt") == "media":
                return httpx.Response(200, content=f["_content"])
            return httpx.Response(200, json=self._pub(f))
        if req.method == "PATCH":
            body = json.loads(req.content or b"{}")
            f.update({k: v for k, v in body.items()
                      if k in ("name", "starred", "trashed", "description", "copyRequiresWriterPermission",
                               "writersCanShare")})
            if p.get("addParents"):
                f["parents"] = [x for x in f["parents"] if x not in p.get("removeParents", "").split(",")] + [p["addParents"]]
            return httpx.Response(200, json=self._pub(f))
        if req.method == "DELETE" and not sub:
            self.files.pop(fid)
            self.perms.pop(fid, None)
            self.comments_store.pop(fid, None)
            self.revs.pop(fid, None)
            return httpx.Response(204)
        return httpx.Response(400)


@pytest.fixture
def d(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.mailbox import accounts as ma
    fake = FakeDrive()
    fake.add("fold1", "Invoices", FOLDER)
    fake.add("doc1", "Quotation Sharma Traders", GDOC, content="Quotation: 10 routers @ Rs 1,200 each".encode())
    fake.add("pdf1", "MSEDCL bill October.pdf", "application/pdf", parents=["fold1"], content=_pdf("Bill amount 1540"))
    fake.add("img1", "Shop photo.jpg", "image/jpeg", content=b"\xff\xd8jpeg")
    fake.add("dup1", "Report", GDOC, content=b"one")
    fake.add("dup2", "Report", GDOC, content=b"two")
    fake.add("1AbCdEfGhIjKlMnOpQrStUvWxYz012345", "GST notes", GDOC, content=b"GSTIN 27ABCDE1234F1Z5")
    ma.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    from app.drive import accounts as da
    url = da.start_link("default")
    assert "auth%2Fdrive" in url and "state=gdr_" in url
    state = httpx.URL(url).params["state"]
    assert da.is_link_state(state)
    out = da.finish_link("code", state)
    assert out["address"] == ME and out["tenant"] == "default"
    cards = []

    def fake_card(ctx, pid):
        from app.bazar.connectors.drive import DriveExecutor
        from app.bazar.packs.registry import Pack
        pack = Pack(**json.loads((Path(__file__).parents[1] / "app" / "bazar" / "packs" / "manifests" / "santosh-drive.json").read_text()))
        bctx = SimpleNamespace(user=SimpleNamespace(id=ctx.tenant_id))
        na = DriveExecutor().call(pack, "confirm_change", {"pending_id": pid}, bctx)
        cards.append((pack, na, bctx))
        return {"needs_approval": True, "approval_id": pid, "card": {"title": na.title, "items": na.items}}
    monkeypatch.setattr(dt, "_card", fake_card)
    yield SimpleNamespace(fake=fake, cards=cards)
    ma.set_http(None)


def run(name, args, ctx=None):
    return asyncio.run(dt.DRIVE_HANDLERS[name](ctx or conv_ctx(), **args))


def _approve(d):
    from app.bazar.connectors.drive import DriveExecutor
    pack, na, bctx = d.cards[-1]
    return DriveExecutor().execute(pack, na.action["name"], na.action["args"], bctx)


def test_find_list_and_resolve(d):
    out = run("drive_find", {"query": "quotation"})
    assert [f["name"] for f in out["files"]] == ["Quotation Sharma Traders"] and out["files"][0]["type"] == "Google Doc"
    assert out["files"][0]["id"].startswith("gdr_") or "~doc1" in out["files"][0]["id"]
    pdfs = run("drive_find", {"kind": "pdf"})
    assert [f["name"] for f in pdfs["files"]] == ["MSEDCL bill October.pdf"]
    inside = run("drive_list_folder", {"folder": "Invoices"})
    assert inside["folder"] == "Invoices" and [i["name"] for i in inside["items"]] == ["MSEDCL bill October.pdf"]
    by_words = run("drive_find", {"query": "1,200"})                      # finds by text inside the file
    assert by_words["count"] == 1
    with pytest.raises(ToolError, match="kai files"):
        run("drive_read_file", {"file": "Report"})
    link = run("drive_read_file", {"file": "https://docs.google.com/document/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012345/edit?usp=sharing"})
    assert link["name"] == "GST notes" and "GSTIN" in link["text"]


def test_read_doc_and_pdf(d):
    doc = run("drive_read_file", {"file": "Quotation Sharma Traders"})
    assert doc["kind"] == "doc" and "10 routers" in doc["text"] and "hukum nahi" in doc["note"]
    pdf = run("drive_read_file", {"file": "MSEDCL bill October.pdf"})
    assert pdf["kind"] == "pdf" and "1540" in pdf["text"]


def test_send_to_phone_and_for_email(d):
    from tests.test_bazar import _events
    ctx = conv_ctx()
    out = run("drive_send_file", {"file": "MSEDCL bill October.pdf", "to": "phone"}, ctx)
    assert out["sent_to_phone"] == "MSEDCL bill October.pdf"
    card = _events(ctx.conversation_id, "pc_file")[-1]
    assert card["name"] == "MSEDCL bill October.pdf" and card["url"].startswith("/api/pc/files/")
    em = run("drive_send_file", {"file": "Quotation Sharma Traders", "to": "email"}, ctx)
    assert em["name"] == "Quotation Sharma Traders.docx"
    from app.db import PcFile, session
    with session() as s:
        f = s.get(PcFile, em["file_id"])
        assert f.tenant_id == "default" and Path(f.stored_path).read_bytes().startswith(b"PK-exported")
    pdf = run("drive_send_file", {"file": "Quotation Sharma Traders", "to": "email", "format": "pdf"}, ctx)
    assert pdf["name"].endswith(".pdf")
    with pytest.raises(ToolError, match="folder"):
        run("drive_send_file", {"file": "Invoices"}, ctx)


def test_upload_docs_and_organise(d):
    from app.mailbox import service as ms
    row = ms.store_bytes("default", "rates.csv", b"item,rate\nrouter,1200\n", "mail")
    up = run("drive_upload", {"source": {"file_id": row.id}, "folder": "Invoices", "convert": True})
    f = d.fake.files[up["uploaded"]["id"].split("~", 1)[1]]
    assert f["name"] == "rates.csv" and f["parents"] == ["fold1"] and f["mimeType"].endswith("spreadsheet")
    note = run("drive_upload", {"source": {"text": "Kal Ramesh ko call karna"}, "name": "todo.txt"})
    assert d.fake.files[note["uploaded"]["id"].split("~", 1)[1]]["_content"] == "Kal Ramesh ko call karna".encode()
    with pytest.raises(ToolError, match="card/Aadhaar"):
        run("drive_upload", {"source": {"text": "Aadhaar 1234 5678 9012"}, "name": "x.txt"})
    with pytest.raises(ToolError, match="card/Aadhaar"):
        run("drive_create_doc", {"title": "x", "text": "my password: hunter2"})
    ok = run("drive_create_doc", {"title": "Akola office address", "text": "Khanapur Ves, Akot, PIN 444101"})
    assert ok["link"] and d.fake.files[ok["doc"]["id"].split("~", 1)[1]]["mimeType"] == GDOC   # a PIN code is fine
    alias = run("doc_create", {"title": "Meeting notes", "content": "Agenda"})
    assert alias["doc"]["name"] == "Meeting notes"
    folder = run("drive_create_folder", {"name": "Diwali 2026"})
    fid = folder["folder"]["id"]
    run("drive_organize", {"file": "Shop photo.jpg", "action": "move", "folder": fid})
    assert d.fake.files["img1"]["parents"] == [fid.split("~", 1)[1]]
    run("drive_organize", {"file": "Shop photo.jpg", "action": "rename", "name": "Dukaan photo.jpg"})
    run("drive_organize", {"file": "Dukaan photo.jpg", "action": "star"})
    assert d.fake.files["img1"]["name"] == "Dukaan photo.jpg" and d.fake.files["img1"]["starred"]
    cp = run("drive_organize", {"file": "Quotation Sharma Traders", "action": "copy"})
    assert cp["file"]["name"] == "Copy of Quotation Sharma Traders"


def test_share_public_and_trash_wait_for_tap(d):
    from app.mailbox import contacts
    contacts.learn("default", [("Swati Sirsath", "swati@fnw.in")], 1.0, sent=True)
    out = run("drive_share", {"file": "Quotation Sharma Traders", "people": ["Swati"], "role": "writer",
                              "message": "Please check"})
    assert out["needs_approval"] and out["card"]["title"] == "File share karein?"
    assert "swati@fnw.in" in json.dumps(out["card"]) and not d.fake.perms           # nothing shared yet
    msg = _approve(d)["message"]
    assert d.fake.perms["doc1"][0] == {"type": "user", "role": "writer", "emailAddress": "swati@fnw.in", "notify": "true",
                                       "id": "perm1"}
    assert "swati@fnw.in" in msg
    from app.bazar.connectors.base import ToolError as CardError
    with pytest.raises(CardError, match="baaki nahi"):
        _approve(d)                                                                  # a card runs once
    run("drive_share", {"file": "Shop photo.jpg", "public": True})
    assert "img1" not in d.fake.perms
    _approve(d)
    assert d.fake.perms["img1"][0]["type"] == "anyone"
    run("drive_trash", {"files": ["Invoices", "MSEDCL bill October.pdf"]})
    card = d.cards[-1][1]
    assert card.title == "Trash mein daalein?" and any("Folder ke andar" in i["name"] for i in card.items)
    assert not d.fake.files["fold1"]["trashed"]
    _approve(d)
    assert d.fake.files["fold1"]["trashed"] and d.fake.files["pdf1"]["trashed"]
    ref = [f["id"] for f in run("drive_storage", {})["recent"] if f["name"] == "MSEDCL bill October.pdf"][0]
    run("drive_organize", {"file": ref, "action": "restore"})                         # back from Trash
    assert not d.fake.files["pdf1"]["trashed"]


def test_storage_and_accounts(d):
    out = run("drive_storage", {})
    assert out["accounts"][0]["address"] == ME and out["storage"][0]["percent"] == 20.0
    assert out["storage"][0]["used"] == "3.0 GB"
    from app.drive import api
    st = api.state_for("default")
    assert st["can_link"] and st["accounts"][0]["removable"]
    from app.drive.accounts import remove
    assert remove("default", st["accounts"][0]["key"])


def test_not_connected(env):
    with pytest.raises(ToolError, match="Profile > Google Drive"):
        asyncio.run(dt.DRIVE_HANDLERS["drive_find"](Ctx("someone", "c"), query="x"))


# ---------------- v0.197.0: full Drive coverage ----------------
def test_trash_list_find_and_delete_forever(d):
    run("drive_trash", {"files": ["Shop photo.jpg"]})
    _approve(d)
    assert d.fake.files["img1"]["trashed"]
    tl = run("drive_trash_list", {})
    assert [f["name"] for f in tl["items"]] == ["Shop photo.jpg"]
    tr = run("drive_find", {"query": "Shop photo", "in_trash": True})
    assert tr["count"] == 1 and tr["files"][0]["name"] == "Shop photo.jpg"
    ref = tl["items"][0]["id"]
    out = run("drive_delete", {"files": [ref]})
    assert out["needs_approval"] and out["card"]["title"] == "Hamesha ke liye delete?"
    assert "img1" in d.fake.files                                              # nothing deleted yet
    msg = _approve(d)["message"]
    assert "img1" not in d.fake.files and "hamesha" in msg.lower()
    with pytest.raises(ToolError, match="Kaunsi files"):
        run("drive_delete", {})


def test_empty_trash_card(d):
    run("drive_trash", {"files": ["Shop photo.jpg"]})
    _approve(d)
    out = run("drive_delete", {"empty": True})
    assert out["card"]["title"] == "Poora Trash khaalein?"
    assert "img1" in d.fake.files
    _approve(d)
    assert "img1" not in d.fake.files and not any(f["trashed"] for f in d.fake.files.values())


def test_details_and_access(d):
    from app.mailbox import contacts
    contacts.learn("default", [("Swati Sirsath", "swati@fnw.in")], 1.0, sent=True)
    contacts.learn("default", [("Ramesh Patil", "ramesh@fnw.in")], 1.0, sent=True)
    d.fake.perms["doc1"] = [{"id": "perm0", "type": "user", "role": "owner", "emailAddress": ME,
                             "displayName": "Meghana"}]                         # the real API lists the owner too
    run("drive_share", {"file": "Quotation Sharma Traders", "people": ["Swati"], "role": "writer"})
    _approve(d)
    run("drive_share", {"file": "Quotation Sharma Traders", "people": ["Ramesh"], "role": "reader"})
    _approve(d)
    det = run("drive_details", {"file": "Quotation Sharma Traders"})
    who = {a["who"]: a["role"] for a in det["access"]}
    assert who.get("swati@fnw.in") == "writer" and who.get("ramesh@fnw.in") == "reader"
    assert who.get(ME) == "owner" and det["modified_by"] == "Meghana"
    out = run("drive_access", {"file": "Quotation Sharma Traders", "action": "role", "person": "swati",
                               "role": "reader"})
    assert out["card"]["title"] == "Role badlein?" and d.fake.perms["doc1"][1]["role"] == "writer"
    _approve(d)
    assert d.fake.perms["doc1"][1]["role"] == "reader"
    out = run("drive_access", {"file": "Quotation Sharma Traders", "action": "remove", "person": "ramesh"})
    assert out["card"]["title"] == "Sharing hata dein?"
    _approve(d)
    assert all(x["emailAddress"] != "ramesh@fnw.in" for x in d.fake.perms["doc1"])
    with pytest.raises(ToolError, match="Owner ki permission nahi hatati"):
        run("drive_access", {"file": "Quotation Sharma Traders", "action": "remove", "person": "Meghana"})
    run("drive_access", {"file": "Quotation Sharma Traders", "action": "stop"})
    _approve(d)
    assert [x["id"] for x in d.fake.perms["doc1"]] == ["perm0"]                 # only the owner remains
    run("drive_share", {"file": "Quotation Sharma Traders", "people": ["Swati"], "role": "writer"})
    _approve(d)
    out = run("drive_access", {"file": "Quotation Sharma Traders", "action": "owner", "person": "swati"})
    assert out["card"]["title"] == "Ownership de dein?"
    _approve(d)
    sw = next(x for x in d.fake.perms["doc1"] if x["emailAddress"] == "swati@fnw.in")
    assert sw["role"] == "owner"
    with pytest.raises(ToolError, match="action: remove"):
        run("drive_access", {"file": "Quotation Sharma Traders", "action": "magic"})


def test_comments(d):
    out = run("drive_comments", {"file": "Quotation Sharma Traders"})
    assert out["count"] == 0 and "manzoori" in out["note"]
    add = run("drive_comments", {"file": "Quotation Sharma Traders", "action": "add",
                                 "text": "Please check the rates"})
    assert add["card"]["title"] == "Comment daalein?" and not d.fake.comments_store.get("doc1")
    _approve(d)
    assert d.fake.comments_store["doc1"][0]["content"] == "Please check the rates"
    lst = run("drive_comments", {"file": "Quotation Sharma Traders"})
    assert lst["count"] == 1 and lst["comments"][0]["by"] == "Meghana"
    cid = lst["comments"][0]["comment_id"]
    rep = run("drive_comments", {"file": "Quotation Sharma Traders", "action": "reply", "comment": cid,
                                 "text": "Done, rates are final"})
    assert rep["card"]["title"] == "Reply daalein?" and "rates" in rep["card"]["items"][0]["name"]
    _approve(d)
    lst = run("drive_comments", {"file": "Quotation Sharma Traders"})
    assert lst["comments"][0]["replies"][0]["text"] == "Done, rates are final"
    res = run("drive_comments", {"file": "Quotation Sharma Traders", "action": "resolve", "comment": cid})
    assert res["done"] == "resolved" and d.fake.comments_store["doc1"][0]["resolved"]
    run("drive_comments", {"file": "Quotation Sharma Traders", "action": "reopen", "comment": cid})
    assert not d.fake.comments_store["doc1"][0]["resolved"]
    dele = run("drive_comments", {"file": "Quotation Sharma Traders", "action": "delete", "comment": cid})
    assert dele["card"]["title"] == "Comment hatayein?"
    _approve(d)
    assert d.fake.comments_store["doc1"] == []
    with pytest.raises(ToolError, match="card/Aadhaar"):
        run("drive_comments", {"file": "Quotation Sharma Traders", "action": "add", "text": "OTP 123456 hai"})
    with pytest.raises(ToolError, match="kya likhna"):
        run("drive_comments", {"file": "Quotation Sharma Traders", "action": "add", "text": "  "})
    with pytest.raises(ToolError, match="comment nahi mila"):
        run("drive_comments", {"file": "Quotation Sharma Traders", "action": "reply", "comment": "cm99",
                               "text": "x"})


def test_revisions(d):
    out = run("drive_revisions", {"file": "Quotation Sharma Traders"})
    assert out["count"] == 1 and out["revisions"][0]["revision_id"] == "1" and "100 revisions" in out["note"]
    res = run("drive_revisions", {"file": "Quotation Sharma Traders", "revision": "1", "keep": True})
    assert res["done"] == "kept" and d.fake.revs["doc1"][0]["keepForever"]
    rel = run("drive_revisions", {"file": "Quotation Sharma Traders", "revision": "1", "keep": False})
    assert rel["done"] == "released" and not d.fake.revs["doc1"][0]["keepForever"]


def test_organize_describe_restrict_shortcut(d):
    run("drive_organize", {"file": "Quotation Sharma Traders", "action": "describe",
                           "description": "Quotation for 10 routers"})
    assert d.fake.files["doc1"]["description"] == "Quotation for 10 routers"
    with pytest.raises(ToolError, match="description"):
        run("drive_organize", {"file": "Quotation Sharma Traders", "action": "describe"})
    run("drive_organize", {"file": "Quotation Sharma Traders", "action": "restrict_copying"})
    assert d.fake.files["doc1"]["copyRequiresWriterPermission"]
    run("drive_organize", {"file": "Quotation Sharma Traders", "action": "allow_copying"})
    assert not d.fake.files["doc1"]["copyRequiresWriterPermission"]
    sc = run("drive_organize", {"file": "Quotation Sharma Traders", "action": "shortcut", "folder": "Invoices"})
    assert sc["file"]["type"] == "Shortcut" and sc["file"]["name"] == "Quotation Sharma Traders"
    assert d.fake.files[sc["file"]["id"].split("~", 1)[1]]["parents"] == ["fold1"]


def test_changes_biggest_shared_drives(d):
    ch = run("drive_changes", {"hours": 24})
    assert ch["count"] >= 6 and "Shop photo.jpg" in [f["name"] for f in ch["files"]]
    d.fake.add("big1", "Backup.pst", "application/octet-stream", size="104857600", quotaBytesUsed="104857600")
    big = run("drive_biggest", {})
    assert big["files"][0]["name"] == "Backup.pst" and "MB" in big["files"][0]["size"]
    sd = run("drive_shared_drives", {})
    assert sd["count"] == 1 and sd["shared_drives"][0]["name"] == "FNW Team Drive"


def test_find_order_size_and_hours(d):
    d.fake.add("big1", "Backup.pst", "application/octet-stream", size="104857600", quotaBytesUsed="104857600")
    out = run("drive_find", {"order": "size"})
    assert out["files"][0]["name"] == "Backup.pst"
    out = run("drive_find", {"modified_hours": 1})
    assert out["count"] >= 7


def test_export_new_formats(d):
    ctx = conv_ctx()
    out = run("drive_send_file", {"file": "Quotation Sharma Traders", "to": "email", "format": "md"}, ctx)
    assert out["name"] == "Quotation Sharma Traders.md"
    out2 = run("drive_send_file", {"file": "Quotation Sharma Traders", "to": "email", "format": "epub"}, ctx)
    assert out2["name"].endswith(".epub")
    with pytest.raises(ToolError):
        run("drive_send_file", {"file": "Quotation Sharma Traders", "to": "email", "format": "exe"}, ctx)
