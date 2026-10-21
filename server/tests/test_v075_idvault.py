"""v0.75 Pehchaan Locker: Hoola accepts Aadhaar / PAN like a Seva Kendra, keeps them encrypted, shows the model only
masked references, and the Computer Operator types the real number only into the form box."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

AAD = "234567890124"          # Verhoeff-valid test numbers (not real people)
AAD2 = "987654321012"
PAN = "ABCPE1234F"


def test_capture_masks_saves_and_knows_whose(env):
    from app import idvault
    txt, saved = idvault.capture("default", f"Mera PAN {PAN} aur aadhaar {AAD[:4]} {AAD[4:8]} {AAD[8:]} hai. Papa ka aadhaar {AAD2}")
    assert AAD not in txt and AAD2 not in txt and PAN not in txt and "XXXX XXXX 0124" in txt
    who = {(r["person"], r["kind"]) for r in saved}
    assert who == {("self", "aadhaar"), ("papa", "aadhaar"), ("self", "pan")}
    again, s2 = idvault.capture("default", f"aadhaar {AAD}")
    assert [r["ref"] for r in s2] == [r["ref"] for r in saved if r["person"] == "self" and r["kind"] == "aadhaar"]   # same number, same row
    assert idvault.capture("default", "order 123456789012 ka status")[1] == []       # fails the checksum: not an Aadhaar
    assert idvault.capture("default", "OTP 482913 hai")[1] == []
    rows = idvault.list_("default")
    assert len(rows) == 3 and all(AAD not in json.dumps(r) for r in rows)
    me = next(r for r in rows if r["person"] == "self" and r["kind"] == "aadhaar")
    assert idvault.resolve("default", me["ref"]) == (AAD, "aadhaar")
    assert idvault.resolve("someone-else", me["ref"]) is None
    assert idvault.fill_value(f"x {me['ref']} y", "default") == (f"x {AAD} y", ["aadhaar"])
    assert idvault.reveal("default", me["id"])["value"] == "2345 6789 0124"
    from app.db import session
    with session() as s:
        row = s.get(idvault.IdRecord, me["id"])
        assert AAD not in row.sealed                                                # encrypted at rest
    summary = idvault.summary_for_model("default")
    assert AAD not in summary and "{id:" in summary and "Papa" in summary
    with pytest.raises(idvault.VaultError):
        idvault.save("default", "aadhaar", "123456789012")
    with pytest.raises(idvault.VaultError):
        idvault.save("default", "pan", "ABC123")
    assert idvault.delete("default", me["id"])["deleted"]


def test_guard_and_masking():
    from app.operator import guard
    from app.operator.browser import mask_ids
    box = lambda n: {"attributes": {"name": n}}          # noqa: E731
    assert guard.classify_input(box("aadhaar_no")) == "id"
    assert guard.classify_input(box("pan_number")) == "id"
    assert guard.classify_input(box("password")) == "secret"
    assert guard.classify_input(box("otp")) == "secret"
    assert guard.classify_input(box("amount"), "4111111111111111") == "ok"   # v0.81 the value never blocks
    assert guard.classify_input(box("pincode"), "444101") == "ok"
    assert guard.classify_input(box("panel_name")) == "ok"
    t = mask_ids(f"Aadhaar: {AAD[:4]} {AAD[4:8]} {AAD[8:]} PAN {PAN} order 123456789012")
    assert AAD not in t.replace(" ", "") and "XXXX XXXX 0124" in t and PAN not in t and "123456789012" in t


def test_chat_remember_and_operator_accept_ids(env):
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.db import Conversation, MemoryFact, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        cid = c.id
    out = asyncio.run(dispatch("remember", {"fact": f"Maa ka PAN {PAN} hai"}, Ctx("default", cid)))
    with session() as s:
        facts = [f.text for f in s.query(MemoryFact).all()]
    assert any("{id:" in f for f in facts) and not any(PAN in f for f in facts)
    with pytest.raises(ToolError):
        asyncio.run(dispatch("remember", {"fact": "mera ATM PIN 4321 hai"}, Ctx("default", cid)))
    lst = asyncio.run(dispatch("id_locker", {"action": "list"}, Ctx("default", cid)))
    assert lst["ids"][0]["person_label"] == "Maa" and PAN not in json.dumps(lst)
    sv = asyncio.run(dispatch("id_locker", {"action": "save", "person": "papa", "kind": "aadhaar", "number": AAD2}, Ctx("default", cid)))
    assert sv["masked"] == "XXXX XXXX 1012" and "Locker" in sv["say"]
    from app.agent.prompts import system_prompt
    sp = system_prompt(False, tenant="default")
    assert "Pehchaan Locker" in sp and AAD2 not in sp and PAN not in sp


def test_api(env):
    from app import main
    with TestClient(main.app) as c:
        r = c.post("/api/ids", json={"kind": "aadhaar", "number": AAD, "person": "self"}).json()
        assert r["masked"] == "XXXX XXXX 0124"
        assert c.post("/api/ids", json={"kind": "aadhaar", "number": "111122223333"}).status_code == 400
        lst = c.get("/api/ids").json()
        assert lst["ids"][0]["masked"] == "XXXX XXXX 0124" and AAD not in json.dumps(lst)
        assert c.post(f"/api/ids/{r['id']}/reveal").json()["value"] == "2345 6789 0124"
        assert c.delete(f"/api/ids/{r['id']}").json()["deleted"]


# ----------------------------------------------------------------------------- the browser, for real
try:
    import playwright  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False

FORM = b"""<!doctype html><html><body><h1>KYC form</h1><form>
<label for=n>Full name</label><input id=n name=full_name>
<label for=a>Aadhaar number</label><input id=a name=aadhaar_no>
<label for=p>Password</label><input id=p name=password type=password>
</form><p>Saved Aadhaar on file: 2345 6789 0124</p></body></html>"""


class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(FORM)

    def log_message(self, *a):
        pass


@pytest.mark.skipif(not HAVE_PW, reason="needs playwright + chromium")
def test_operator_types_the_locker_number_only_into_the_box(env, tmp_path):
    from app import idvault
    from app.operator.browser import Operator, fmt_snapshot
    rec = idvault.save("default", "aadhaar", AAD)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"

    async def go():
        op = Operator(tmp_path / "op", allow_private=True, screenshots=False)
        op.id_tenant = "default"
        try:
            s = await op.session("main")
            await op.goto(s, url)
            page = fmt_snapshot(await op.snapshot(s))
            assert "ID number" in page and "XXXX XXXX 0124" in page and AAD not in page.replace(" ", "")
            import re
            aref = re.search(r'\[(\w+)\] textbox "Aadhaar number"', page).group(1)
            pref = re.search(r'\[(\w+)\] textbox "Password"', page).group(1)
            # v0.81 (owner's decision): any site, no tap - the reference and a plain number both go into the box
            r = await op.act(s, "fill", aref, value=rec["ref"])
            assert r["ok"] and AAD not in json.dumps(r)
            assert await s.page.eval_on_selector("#a", "e => e.value") == AAD     # the real number is in the box
            r = await op.act(s, "fill", aref, value=AAD)
            assert r["ok"] and AAD not in json.dumps(r)
            assert await s.page.eval_on_selector("#a", "e => e.value") == AAD
            assert (await op.act(s, "fill", pref, value=rec["ref"]))["blocked"] == "secret"   # never into a password box
            again = fmt_snapshot(await op.snapshot(s))
            assert AAD not in again.replace(" ", "")
            assert all(AAD not in json.dumps(st) for st in s.trace)            # recipes / traces keep the reference
        finally:
            await op.shutdown()
    try:
        asyncio.run(go())
    finally:
        srv.shutdown()


def test_official_sites():
    from app.idvault import official_site
    assert official_site("https://uidai.gov.in/en/") and official_site("https://eportal.incometax.gov.in/x")
    assert official_site("https://onlineservices.nsdl.com/paam") and official_site("https://pmkisan.gov.in")
    assert not official_site("https://example.com") and not official_site("https://gov.in.evil.com")
