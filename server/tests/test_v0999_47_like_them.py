"""v0.999.47 LIKE THEM (owner: "DO THIS FOR HOOLA" on the seven abilities Dots, Grok Bot and Duet have that Hoola lacked):
1 saved sign-ins, 2 OTPs read from her mail, 3 a check before done, 4 several jobs on one Hoola PC with the same logins
(tab lanes), 5 background mode on her own PC, 6 Hoola's own email address, 7 jobs started by an arriving email."""
import asyncio
import email.message
import importlib.util
import json
import os
import shutil
import subprocess
import time
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0193_hoola_pc import FakePC, Scripted, _wire, tu
from tests.test_v0885_hoola_pc_pool import KIND, pool_hub  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def fresh_home(bz, monkeypatch):  # noqa: F811
    from app.pc import pool
    pool.HOME.clear()
    monkeypatch.setattr(pool, "_HOME_LOADED", True)
    yield pool
    pool.HOME.clear()


# ---------------------------------------------------------------- 1. saved sign-ins
def test_saved_sign_in_store(bz):  # noqa: F811
    from app.pc import vault
    assert vault.key_of("GST portal", "https://services.gst.gov.in/services/login") == "gst.gov.in"
    assert vault.key_of("IRCTC", "https://www.irctc.co.in/nget") == "irctc.co.in"
    assert vault.key_of("My Portal") == "my portal"
    r = vault.save("owner", "gst.gov.in", "GST portal", "meghana@gst", "Pa55-W0rd!")
    assert r["user"] == "m***@gst" and "Pa55" not in json.dumps(r)
    found = vault.find("owner", "gst.gov.in")
    assert found["id"] == r["id"] and vault.find("someone", "gst.gov.in") is None   # never another user's
    assert vault.open_("owner", r["id"]) == ("meghana@gst", "Pa55-W0rd!")
    with pytest.raises(ValueError):
        vault.open_("someone", r["id"])
    with pytest.raises(ValueError):
        vault.save("owner", "hdfcbank.com", "HDFC net banking", "u", "p")            # bank sign-ins are never kept
    assert [x["site"] for x in vault.list_("owner")] == ["gst.gov.in"]
    assert vault.delete("owner", r["id"]) and vault.list_("owner") == []


@pytest.mark.asyncio
async def test_saved_sign_in_is_offered_and_used_only_on_her_tap(pool_hub, fresh_home, monkeypatch):  # noqa: F811
    from app.pc import hands, operator, vault
    vault.save("owner", "gst.gov.in", "GST portal", "meghana@gst", "Pa55-W0rd!")
    pc = FakePC(expect_kind=KIND)

    async def call(tenant, action, args=None, device_id=None, timeout=None, log=True, kind=None):
        if action == "page_text":
            return {"title": "GST", "url": "https://services.gst.gov.in/services/login", "text": ""}
        return await pc.call(tenant, action, args, device_id, timeout, log, kind)
    monkeypatch.setattr(pool_hub, "call", call)
    claude = Scripted([tu(1, "ask_login", site="GST portal"), tu(2, "done", answer="signed in")])
    _wire(monkeypatch, claude)
    r = await operator.start("owner", "c1", "GST portal par login karo", wait=0, kind=KIND)
    op = operator.get("owner", r["session_id"])
    for _ in range(200):
        if op.login:
            break
        await asyncio.sleep(0.02)
    lg = op.live()["login"]
    assert lg["saved"]["user"] == "m***@gst" and lg["can_save"] is True
    assert pc.calls == [] or not [c for c in pc.calls if c[0] == "control"]     # nothing typed before her tap
    assert hands.give_login(op, lg["id"], "", "", use_saved=True)
    await asyncio.wait_for(op.done_event.wait(), 10)
    typed = [c[1] for c in pc.calls if c[0] == "control"]
    assert typed == [{"op": "type", "text": "meghana@gst"}, {"op": "key", "keys": "Tab"},
                     {"op": "type", "text": "Pa55-W0rd!"}]
    assert "Pa55" not in json.dumps([kw.get("messages") for kw in claude.seen], default=str)


def test_ticking_save_keeps_it_and_routes_list_and_delete(env):
    from app.pc import hands, operator, vault
    op = operator.Op(id="pcop_v", tenant="default", conv="c", task="t", kind=KIND)
    loop = asyncio.new_event_loop()
    try:
        op.login = {"id": "pl1", "site": "Income Tax", "fields": "username_password", "status": "pending",
                    "event": asyncio.Event(), "key": "incometax.gov.in", "can_save": True, "saved": None}
        assert hands.give_login(op, "pl1", "ABCDE1234F", "secret#1", save=True)
    finally:
        loop.close()
    assert vault.find("default", "incometax.gov.in")["user"] == "AB***4F"
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    rows = c.get("/api/computer/logins").json()["logins"]
    assert rows and "secret" not in json.dumps(rows)
    assert c.delete(f"/api/computer/logins/{rows[0]['id']}").json() == {"ok": True}
    assert c.get("/api/computer/logins").json()["logins"] == []


# ---------------------------------------------------------------- 2. OTP read from her mail
def test_otp_code_reading():
    from app.pc import hands
    assert hands.otp_code("Your OTP for myAadhaar is 482913. Valid for 10 minutes") == "482913"
    assert hands.otp_code("482913 is your verification code") == "482913"
    assert hands.otp_code("Use code 7781 to log in", digits=4) == "7781"
    assert hands.otp_code("Invoice 2024 total 5600") == ""                       # no OTP words: nothing
    assert hands.OTP_MONEY.search("OTP 4455 for debit of Rs 500 on your card")   # money codes stay hers


@pytest.mark.asyncio
async def test_a_fresh_code_mail_fills_the_box(monkeypatch):
    from app.pc import hands, operator
    operator._loop = asyncio.get_running_loop()
    mails = [{"ref": "", "from": "bank@x.in", "text": "OTP 1111 for payment of Rs 99 on your card", "src": "gmail"},
             {"ref": "", "from": "noreply@uidai.gov.in", "text": "Your OTP for myAadhaar is 482913", "src": "gmail"}]
    monkeypatch.setattr(hands, "_mail_candidates", lambda tenant, since: mails)
    op = operator.Op(id="pcop_o", tenant="owner", conv="c", task="t", kind=KIND)
    req = operator.PcOtp(id="pcotp_1", digits=6)
    await asyncio.wait_for(hands.otp_from_mail(op, req, "myAadhaar"), 5)
    assert req.value == "482913" and req.source == "noreply@uidai.gov.in"       # the money code was skipped
    req2 = operator.PcOtp(id="pcotp_2")
    t = asyncio.create_task(hands.otp_from_mail(op, req2, "SBI net banking"))   # a bank's own box: never filled
    await asyncio.wait_for(t, 2)
    assert req2.value == ""


# ---------------------------------------------------------------- 3. a check before done
def test_done_is_checked_by_default():
    from app.config import Settings
    assert Settings.model_fields["pc_verify"].default is True


# ---------------------------------------------------------------- 4. several jobs on one Hoola PC, the same logins
@pytest.mark.asyncio
async def test_her_second_job_opens_a_side_window_on_her_busy_pc(pool_hub, fresh_home, monkeypatch):  # noqa: F811
    from app.pc import operator
    pool_hub.conns["owner"].pop("hp2")
    pool_hub.conns["owner"]["hp1"].info["version"] = "1.7.0"
    hold = asyncio.Event()

    async def slow(o):
        await hold.wait()
        o.status = "done"
        o.done_event.set()
    monkeypatch.setattr(operator, "_run", slow)
    first = await operator.start("owner", "c1", "Aadhaar download", wait=0, kind=KIND)
    second = await operator.start("owner", "c2", "GST status dekho", wait=0, kind=KIND)
    a, b = operator.get("owner", first["session_id"]), operator.get("owner", second["session_id"])
    assert a.status == b.status == "running" and a.device_id == b.device_id == "hp1"
    assert a.lane == "" and b.lane == "new"                         # the first keeps the screen, the second a window
    sent = []

    async def call(tenant, action, args=None, device_id=None, timeout=None, log=True, kind=None):
        sent.append((action, dict(args or {})))
        return {"ok": True}
    monkeypatch.setattr(pool_hub, "call", call)
    b.lane = "T1"
    await operator._pc(b, "screen", {})
    await operator._pc(a, "screen", {})
    assert sent == [("screen", {"lane": "T1"}), ("screen", {})]
    other = await operator.start("someone", "c9", "kuch aur", wait=0, kind=KIND)
    assert other["status"] == "queued"                              # never a window on a PC working for her
    pool_hub.conns["owner"]["hp1"].info["version"] = "1.6.0"
    third = await operator.start("owner", "c3", "teesra kaam", wait=0, kind=KIND)
    assert third["status"] == "queued"                              # an old agent: she waits instead
    hold.set()


@pytest.mark.skipif(not Path("/opt/pw-browsers/chromium-1243/chrome-linux64/chrome").exists() and not os.environ.get("HOOLA_CHROMIUM"),
                    reason="needs a real Chromium")
def test_a_side_window_works_in_real_chromium(tmp_path, monkeypatch):
    import functools
    import http.server
    import threading
    chrome_bin = os.environ.get("HOOLA_CHROMIUM") or "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
    site = tmp_path / "site"
    site.mkdir()
    (site / "form.html").write_text("<title>Portal form</title><input placeholder='Your name'><button onclick=\"document"
                                    ".getElementById('o').textContent='Saved: '+document.querySelector('input').value\">"
                                    "Save</button><p id=o></p>")
    (site / "main.html").write_text("<title>Main job page</title><h1>Main job</h1>")
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler,
                                                                               directory=str(site)))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("HOOLA_DATA", str(tmp_path / "data"))
    spec = importlib.util.spec_from_file_location("hoola_agent_lane_t", ROOT / "desktop-linux" / "agent.py")
    a = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a)
    dbg = 9300 + (os.getpid() % 500)
    a.CDP = f"http://127.0.0.1:{dbg}"
    chrome = subprocess.Popen([chrome_bin, "--headless=new", f"--remote-debugging-port={dbg}", "--no-sandbox",
                               f"--user-data-dir={tmp_path / 'prof'}", f"http://127.0.0.1:{port}/main.html"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import httpx
        for _ in range(80):
            try:
                httpx.get(a.CDP + "/json/version", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        act = a.Actions()
        lane = act.handle("lane_open", {"url": "about:blank"})["lane"]
        assert [t["title"] for t in a._targets()] == ["Main job page"]       # the main job never sees the side window
        assert act.handle("open_url", {"url": f"http://127.0.0.1:{port}/form.html", "lane": lane})["ok"]
        shot = act.handle("screen", {"lane": lane})
        assert shot["width"] > 0 and shot["active_window"] == "Portal form"
        els = act.handle("page_elements", {"lane": lane})["elements"]
        ref = [e["ref"] for e in els if e.get("placeholder") == "Your name"][0]
        act.handle("page_type", {"ref": ref, "text": "Meghana", "lane": lane})
        act.handle("control", {"op": "key", "keys": "tab", "lane": lane})
        act.handle("control", {"op": "key", "keys": "enter", "lane": lane})
        time.sleep(0.4)
        assert "Saved: Meghana" in act.handle("page_text", {"lane": lane})["text"]
        assert "Main job" in act.handle("page_text", {})["text"] and act._els == {}
        with pytest.raises(a.ActionError):
            act.handle("open_app", {"name": "files", "lane": lane})          # desktop apps stay with the main job
        act.handle("lane_close", {"lane": lane})
        assert not a.LANES
        assert a.VERSION == "1.7.0"
    finally:
        chrome.terminate()
        srv.shutdown()


# ---------------------------------------------------------------- 5. background mode on her own PC
def test_background_mode_never_takes_her_mouse(env):
    from app import computer
    from app.pc import operator
    assert computer.bg_on("default") is False
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    assert c.put("/api/computer/mine/background", json={"on": True}).json() == {"background": True}
    assert c.get("/api/computer").json()["mine"]["background"] is True
    op = operator.Op(id="pcop_bg", tenant="default", conv="c", task="t", kind="", bg=True)
    names = {t["name"] for t in operator._tools_for(op)}
    assert not names & {"click", "type", "key", "scroll", "drag", "open_url"} and {"ax_click", "ax_set_value"} <= names
    op.brain = "sonnet"
    assert operator._native_on(op) is False
    assert "BACKGROUND MODE" in open(operator.__file__).read()


# ---------------------------------------------------------------- 6. Hoola's own email address + 7. jobs from a mail
def _mail(subject, body, attach=False):
    m = email.message.EmailMessage()
    m["From"] = "Receipts <receipts@portal.gov.in>"
    m["To"] = "x"
    m["Subject"] = subject
    m.set_content(body)
    if attach:
        m.add_attachment(b"%PDF-1.4 receipt", maintype="application", subtype="pdf", filename="ack.pdf")
    return m.as_bytes()


def test_hoola_gets_its_own_inbox(env, monkeypatch):
    from app import agentmail
    from app.config import get_settings
    st = get_settings()
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    assert c.get("/api/agentmail").json()["address"] == ""                  # not set up: says so, nothing else
    monkeypatch.setattr(st, "hoola_mail_domain", "agents.example.in")
    monkeypatch.setattr(st, "hoola_mail_secret", "s3cret")
    addr = c.get("/api/agentmail").json()["address"]
    assert addr.endswith("@agents.example.in") and c.get("/api/agentmail").json()["address"] == addr   # kept
    raw = _mail("Your acknowledgement", "Application received. OTP for login is 553311", attach=True)
    bad = c.post("/api/agentmail/inbound", content=raw, headers={"x-hoola-to": addr, "x-hoola-sig": "nope"})
    assert bad.status_code == 403
    good = c.post("/api/agentmail/inbound", content=raw,
                  headers={"x-hoola-to": addr, "x-hoola-sig": agentmail.sign(addr, raw)})
    assert good.json()["ok"] and good.json().get("id")
    mails = c.get("/api/agentmail").json()["mails"]
    assert mails[0]["subject"] == "Your acknowledgement" and len(mails[0]["files"]) == 1
    assert agentmail.recent("default", time.time() - 60)[0]["from"] == "receipts@portal.gov.in"
    other = c.post("/api/agentmail/inbound", content=raw, headers={"x-hoola-to": "nobody@agents.example.in",
                                                                  "x-hoola-sig": agentmail.sign("nobody@agents.example.in", raw)})
    assert other.json().get("dropped") == "no such address"
    assert (ROOT / "deploy" / "agent-mail" / "worker.js").read_text().count("HOOLA_MAIL_SECRET") >= 2


def test_a_rule_can_start_a_job_once_per_mail(env, monkeypatch):
    from app import agentmail
    from app.agent import turnpark
    from app.mailbox import sync as msync
    started = []
    monkeypatch.setattr(turnpark, "_kick", lambda coro: (started.append(1), coro.close()))
    r = msync.rule_create("default", "GST acks", {"subject": "acknowledgement"}, {"run": "save the PDF to my GST folder"})
    assert r["actions"]["run"] == "save the PDF to my GST folder"
    item = {"id": "m1", "from": "x@y", "from_email": "x@y", "subject": "Your acknowledgement", "snippet": "",
            "has_attachment": True, "bulk": False, "unread": True}
    assert agentmail.run_rules("default", item) == 1
    assert agentmail.run_rules("default", item) == 0                # the same mail never starts it twice
    assert agentmail.run_rules("default", {**item, "id": "m2", "subject": "newsletter"}) == 0
    monkeypatch.setattr(agentmail, "RULE_JOBS_PER_DAY", 1)
    agentmail._DAY.clear()
    assert agentmail.start_job("default", "r", "n", "do it", {"id": "m3"}) is True
    assert agentmail.start_job("default", "r", "n", "do it", {"id": "m4"}) is False   # capped a day
    assert len(started) == 2
    from app.agent.email_tools import EMAIL_TOOLS
    rule_tool = [t for t in EMAIL_TOOLS if t["name"] == "email_rule"][0]
    assert "run" in rule_tool["input_schema"]["properties"]["actions"]["properties"]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION >= "0.999.53"
