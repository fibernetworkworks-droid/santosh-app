"""v0.999.46 CA DOCUMENT DESK - the GST & Accounts employee for a CA practice: every client has a folder (FY > month > kind),
files come in from WhatsApp / Telegram / Slack / email / the CA's PC '_Drop here' folder / an upload, an unknown sender is
never filed by itself, a ZIP is opened and each file inside filed, copies go to Google Drive and the CA's PC, a request for
missing documents is drafted by Hoola and sent only by her tap."""
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0845_bahi_a6 import GOOD, _valid_gstin

ROOT = Path(__file__).resolve().parents[2]
T = "default"
BANK = """HDFC BANK  Statement of Account
Account No 50100XXXX1234  IFSC HDFC0000123
Opening Balance 12,000.00
02/10/2026  NEFT from Gupta  5,000.00
14/10/2026  UPI to Patel  1,200.00
28/10/2026  Cash deposit 20,000.00
Closing Balance 35,800.00
"""


@pytest.fixture
def pr(env, tmp_path, monkeypatch):
    monkeypatch.setenv("PRACTICE_FILES_DIR", str(tmp_path / "practice"))
    from app.config import get_settings
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
    from app.bahi import practice as P
    from app.db import init_db
    init_db()
    P.ensure_tables()
    cg = _valid_gstin("27AAKFG2210L1Z")
    sup = _valid_gstin("27AABCA1234B1Z")
    c = P.save_client(T, {"name": "Gupta Packaging", "gstin": cg, "phones": ["+91 98220 44410"],
                          "emails": ["Accounts@Gupta.in"]})
    yield P, c, cg, sup


def bill(sup, buyer):
    return GOOD.format(sup=sup, mine=buyer).encode()


def test_a_known_sender_s_bill_is_filed_in_its_month_and_kind(pr):
    P, c, cg, sup = pr
    assert c["folder"] == "Gupta Packaging" and c["phones"] == ["9822044410"] and c["emails"] == ["accounts@gupta.in"]
    rows = P.collect(T, "whatsapp", "919822044410", "IMG_1.txt", bill(sup, cg), "October bills sir")
    assert len(rows) == 1 and rows[0]["status"] == "filed"
    r = rows[0]
    assert r["kind"] == "purchase" and r["month"] == "2026-10" and r["client_id"] == c["id"]
    assert r["name"].startswith("2026-10-05") and "ACM-26-0042" in r["name"]
    f = P.folder(T, c["id"])
    assert f["tree"]["FY 2026-27"]["10 October"]["Purchase bills"] == 1
    assert f["files"][0]["path"] == "Gupta Packaging / FY 2026-27 / 10 October / Purchase bills"
    name, data = P.get_file(T, r["id"])
    assert data == bill(sup, cg)                                 # the original bytes, unchanged
    again = P.collect(T, "whatsapp", "919822044410", "copy.txt", bill(sup, cg))
    assert again[0].get("duplicate")                             # the same file twice is kept once
    sale = P.collect(T, "email", "accounts@gupta.in", "inv.txt", bill(cg, sup))
    assert sale[0]["kind"] == "sales"


def test_an_unknown_sender_waits_with_a_guess_and_her_tap_files_the_rest(pr):
    P, c, cg, sup = pr
    a = P.collect(T, "whatsapp", "919000002231", "a.txt", bill(sup, cg))[0]
    b = P.collect(T, "whatsapp", "919000002231", "b.txt", bill(sup, cg).replace(b"0042", b"0043"))[0]
    assert a["status"] == "waiting" and "Gupta Packaging" in a["why"] and a["guess"]["client_id"] == c["id"]
    assert P.folder(T, c["id"])["files"] == []                   # never filed by itself
    out = P.file_it(T, a["id"], c["id"], remember_sender=True)
    assert out["status"] == "filed"
    assert "9000002231" in P._cview(P.client(T, c["id"]))["phones"]
    assert {x["id"] for x in P.folder(T, c["id"])["files"]} == {a["id"], b["id"]}   # the same sender's other file too
    assert P.waiting(T) == []
    nxt = P.collect(T, "whatsapp", "919000002231", "c.txt", bill(sup, cg).replace(b"0042", b"0044"))[0]
    assert nxt["status"] == "filed"                              # now a known sender


def test_a_zip_is_opened_and_a_program_inside_is_never_kept(pr):
    P, c, cg, sup = pr
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Oct/bill1.txt", bill(sup, cg))
        z.writestr("Oct/statement.txt", BANK)
        z.writestr("run.exe", b"MZ\x90\x00 not a bill")
    rows = P.collect(T, "email", "accounts@gupta.in", "October.zip", buf.getvalue())
    kinds = {r["orig_name"]: (r["status"], r["kind"]) for r in rows}
    assert kinds["October.zip"] == ("filed", "other")
    assert ("filed", "purchase") in kinds.values() and ("filed", "bank") in kinds.values()
    assert all(r["parent"] for r in rows if r["orig_name"] != "October.zip")
    assert not any(r["status"] == "filed" and r["orig_name"].endswith(".exe") for r in rows)


def test_unclear_month_waits_with_choices(pr):
    P, c, cg, sup = pr
    spread = BANK.replace("02/10/2026", "28/09/2026").replace("14/10/2026", "29/09/2026").replace("28/10/2026", "01/10/2026")
    w = P.collect(T, "email", "accounts@gupta.in", "scan_0042.txt", spread.encode())[0]
    assert w["status"] == "waiting" and w["kind"] == "bank" and "2026-09" in w["guess"]["months"]
    out = P.file_it(T, w["id"], c["id"], month="2026-10")
    assert out["month"] == "2026-10" and out["status"] == "filed"
    with pytest.raises(P.PracticeError):
        P.file_it(T, w["id"], c["id"], month="Oct")


def test_requests_name_what_is_missing_and_only_her_tap_sends(pr, monkeypatch):
    P, c, cg, sup = pr
    P.collect(T, "whatsapp", "919822044410", "b.txt", bill(sup, cg))
    v = P.requests_view(T, "2026-10")
    row = next(r for r in v["missing"] if r["id"] == c["id"])
    assert "purchase" not in row["missing"] and "bank" in row["missing"]
    d = P.request_draft(T, c["id"], "2026-10")
    assert "bank statements" in d["text"] and "purchase" not in d["text"] and d["channels"] == ["email", "whatsapp"]
    from app.mailbox import service as ms
    sent = []
    monkeypatch.setattr(ms, "send_draft", lambda tenant, did, **k: sent.append(did) or {"status": "sent"})
    import asyncio
    out = asyncio.run(P.send_request(T, c["id"], "email", d["text"], "2026-10", d["subject"]))
    assert out["sent"] and len(sent) == 1
    wa = asyncio.run(P.send_request(T, c["id"], "whatsapp", d["text"], "2026-10"))
    assert not wa["sent"] and wa["link"].startswith("https://wa.me/919822044410")   # outside the window: her own WhatsApp
    assert P.requests_view(T, "2026-10")["missing"][0]["asked"]


def test_drive_and_pc_copies_land_in_the_same_folders(pr, monkeypatch):
    P, c, cg, sup = pr
    P.save_settings(T, {"drive_on": True, "pc_on": True, "pc_root": "D:\\CA Clients"})
    r = P.collect(T, "whatsapp", "919822044410", "b.txt", bill(sup, cg))[0]
    from app.drive import service as DS
    made, ups = [], []
    monkeypatch.setattr(DS, "create_folder", lambda t, name, parent=None: made.append((name, parent)) or {"folder": {"id": f"k~{name}"}})
    monkeypatch.setattr(DS, "upload", lambda t, src, folder=None, name=None: ups.append((folder, name)) or {"uploaded": {"id": "k~f1"}})
    from app.pc import hub as H
    calls = []

    async def call(t, action, args=None, **k):
        calls.append((action, args))
        return {"saved_path": "D:\\CA Clients\\x.pdf"}
    monkeypatch.setattr(H.hub, "is_online", lambda t, *a, **k: True)
    monkeypatch.setattr(H.hub, "call", call)
    import asyncio
    asyncio.run(P.mirror_tick())
    assert [m[0] for m in made] == ["CA Clients", "Gupta Packaging", "FY 2026-27", "10 October", "Purchase bills"]
    assert ups == [("k~Purchase bills", r["name"])]
    act, args = calls[0]
    assert act == "save_into" and args["parts"] == ["Gupta Packaging", "FY 2026-27", "10 October", "Purchase bills"]
    f = P.folder(T, c["id"])["files"][0]
    assert f["drive"] == "done" and f["pc"] == "done"
    # a second file reuses the folders Hoola already made in Drive
    P.collect(T, "whatsapp", "919822044410", "b2.txt", bill(sup, cg).replace(b"0042", b"0099"))
    asyncio.run(P.mirror_tick())
    assert len(made) == 5


def test_an_older_desktop_gets_the_flat_inbox_with_the_client_in_the_name(pr, monkeypatch):
    P, c, cg, sup = pr
    P.save_settings(T, {"pc_on": True})
    P.collect(T, "whatsapp", "919822044410", "b.txt", bill(sup, cg))
    from app.pc import hub as H
    calls = []

    async def call(t, action, args=None, **k):
        calls.append((action, args))
        if action == "save_into":
            raise H.PcError("Unknown action save_into")
        return {"saved_path": "C:\\Santosh Inbox\\x"}
    monkeypatch.setattr(H.hub, "is_online", lambda t, *a, **k: True)
    monkeypatch.setattr(H.hub, "call", call)
    import asyncio
    asyncio.run(P.mirror_tick())
    assert calls[1][0] == "save_file" and calls[1][1]["name"].startswith("Gupta Packaging - FY 2026-27 - 10 October")
    assert P.folder(T, c["id"])["files"][0]["pc"] == "inbox"


def test_whatsapp_media_is_taken_only_with_practice_on(pr, monkeypatch):
    P, c, cg, sup = pr
    from app.employee import inbox as biz
    monkeypatch.setattr(biz, "tenant_of_number", lambda pnid: T if pnid == "pn1" else "")
    value = {"metadata": {"phone_number_id": "pn1"}, "messages": [
        {"from": "919822044410", "type": "document", "timestamp": "1", "document": {"id": "m1", "filename": "bill.pdf",
                                                                                  "mime_type": "application/pdf"}},
        {"from": "919822044410", "type": "text", "text": {"body": "hi"}}]}
    got = P.whatsapp_wanted(value)
    assert got == [(T, "9822044410", "m1", "bill.pdf", "")]
    P.save_settings(T, {"whatsapp_on": False})
    assert P.whatsapp_wanted(value) == []


def test_routes_upload_inbox_folder_zip_and_the_pc_drop_door(pr, monkeypatch):
    P, c, cg, sup = pr
    from app.main import app
    with TestClient(app) as cl:
        h = cl.get("/api/practice").json()
        assert h["settings"]["linkedin"]["on"] is False and "LinkedIn gives no app access" in h["settings"]["linkedin"]["why"]
        r = cl.post("/api/practice/upload", files={"file": ("b.txt", bill(sup, cg))}, data={"client_id": c["id"]}).json()
        assert r["files"][0]["status"] == "filed"
        w = cl.post("/api/practice/upload", files={"file": ("n.txt", bill(sup, cg).replace(b"0042", b"0077"))}).json()
        assert w["files"][0]["status"] == "waiting"                # no client picked = waits
        inbox = cl.get("/api/practice/inbox").json()
        assert inbox["waiting_count"] == 1 and inbox["filed_count"] == 1
        fid = w["files"][0]["id"]
        assert cl.post(f"/api/practice/files/{fid}/file", json={"client_id": c["id"]}).json()["status"] == "filed"
        cs = cl.get("/api/practice/clients", params={"month": "2026-10"}).json()["clients"]
        assert cs[0]["files_month"] == 2 and "purchase" not in cs[0]["missing"]
        z = cl.get(f"/api/practice/clients/{c['id']}/zip", params={"month": "2026-10"})
        assert z.status_code == 200 and len(zipfile.ZipFile(io.BytesIO(z.content)).namelist()) == 2
        one = cl.get(f"/api/practice/files/{r['files'][0]['id']}")
        assert one.status_code == 200 and one.content == bill(sup, cg)
        assert cl.post("/api/practice/pcdrop", files={"file": ("x.txt", b"x")}, data={"folder": "Gupta Packaging"}).status_code == 401
        from app.pc import service as pcs
        dev = type("D", (), {"tenant_id": T, "id": "dev1"})()
        monkeypatch.setattr(pcs, "device_for_token", lambda tok: dev if tok == "spc_ok" else None)
        ok = cl.post("/api/practice/pcdrop", headers={"Authorization": "Bearer spc_ok"},
                     files={"file": ("d.txt", bill(sup, cg).replace(b"0042", b"0088"))}, data={"folder": "Gupta Packaging"})
        assert ok.json()["files"] == 1
        assert cl.post("/webhooks/practice/telegram/nope", json={}).status_code == 403
        assert cl.post("/webhooks/practice/slack/nope", content=b"{}").status_code == 401
        assert cl.post("/api/practice/clients", json={"name": "Bad", "gstin": "27ABCDE1234F1ZX"}).status_code == 400


def test_telegram_start_link_ties_a_client_and_files_come_in(pr, monkeypatch):
    P, c, cg, sup = pr
    import asyncio
    import httpx
    sent = []

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None):
            sent.append((url, json))
            return httpx.Response(200, json={"ok": True})

        async def get(self, url, params=None, headers=None):
            if url.endswith("/getFile"):
                return httpx.Response(200, json={"ok": True, "result": {"file_path": "documents/b.txt", "file_size": 100}})
            return httpx.Response(200, content=bill(sup, cg))
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    sec = {"token": "1:x", "header": "h"}
    asyncio.run(P.telegram_update(T, sec, {"message": {"from": {"id": 777}, "chat": {"id": 777, "type": "private"},
                                                       "text": f"/start {c['code']}"}}))
    assert "777" in P._cview(P.client(T, c["id"]))["telegram"] and "Linked for Gupta Packaging" in sent[0][1]["text"]
    n = asyncio.run(P.telegram_update(T, sec, {"message": {"from": {"id": 777}, "chat": {"id": 777, "type": "private"},
                                                           "document": {"file_id": "F", "file_name": "b.txt"}}}))
    assert n == 1 and P.folder(T, c["id"])["files"][0]["channel"] == "telegram"


def test_the_accounts_tool_knows_the_clients_and_files_only_on_her_word(pr):
    P, c, cg, sup = pr
    from app.employee import hire
    from app.agent.tools import Ctx, ToolError
    from app.agent.accountsdesk_tools import _do
    hire.hire(T, "accounts", trust="saathi")
    w = P.collect(T, "whatsapp", "919000002231", "a.txt", bill(sup, cg))[0]
    ctx = Ctx(tenant_id=T, conversation_id="c1", actor="owner")
    out = _do(ctx, {"action": "clients"})
    assert out["clients"][0]["name"] == "Gupta Packaging"
    assert _do(ctx, {"action": "doc_inbox"})["waiting"][0]["id"] == w["id"]
    staff = Ctx(tenant_id=T, conversation_id="c1", actor="staff:x")
    with pytest.raises(ToolError):
        _do(staff, {"action": "file_doc", "file_id": w["id"], "client_id": c["id"]})
    assert _do(ctx, {"action": "file_doc", "file_id": w["id"], "client_id": c["id"]})["status"] == "filed"
    assert "A draft only" in _do(ctx, {"action": "request_draft", "client_id": c["id"], "month": "2026-10"})["note"]
    from app import accountschat
    assert "CA practice: 1 clients" in accountschat.block(T)


def test_desktop_saves_only_inside_the_ca_folder_and_keeps_dropped_files(tmp_path):
    import sys
    sys.path.insert(0, str(ROOT / "desktop"))
    from santosh_desktop import cadesk
    from santosh_desktop.safety import Denied
    root = tmp_path / "CA Clients"
    p = cadesk.target(str(root), ["Gupta Packaging", "FY 2026-27", "10 October", "Purchase bills"], "b.pdf")
    assert p == root / "Gupta Packaging" / "FY 2026-27" / "10 October" / "Purchase bills" / "b.pdf"
    p.write_bytes(b"1")
    assert cadesk.target(str(root), ["Gupta Packaging", "FY 2026-27", "10 October", "Purchase bills"], "b.pdf").name == "b (2).pdf"
    with pytest.raises(Denied):
        cadesk.target(str(root), ["..", "x"], "y.pdf")                          # '..' is never a folder
    assert root in cadesk.target(str(root), ["a/../../etc"], "z").parents         # slashes become plain spaces
    for bad in ("/", "/etc", "/usr/lib"):
        with pytest.raises(Denied):
            cadesk.root_of(bad)
    drop = root / "Gupta Packaging" / "_Drop here"
    drop.mkdir(parents=True)
    (drop / "bill.pdf").write_bytes(b"x")
    (drop / "~$lock.docx").write_bytes(b"x")
    got = cadesk.drop_scan(str(root), ["Gupta Packaging", "New Client"])
    assert [(f, q.name) for f, q in got] == [("Gupta Packaging", "bill.pdf")]
    assert (root / "New Client" / "_Drop here").is_dir()
    moved = cadesk.collected(got[0][1])
    assert moved.parent.name == "_Collected" and moved.exists() and not (drop / "bill.pdf").exists()
    src = (ROOT / "desktop/santosh_desktop/actions.py").read_text()
    assert "def do_save_into" in src and "def do_ca_drop" in src and "/api/practice/pcdrop" in src
