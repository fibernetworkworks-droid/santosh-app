"""v0.92 From the owner's real 14-day report: every website job was "download my Aadhaar" and none finished (UIDAI
refuses the VPS), and the phone-offline email digest failed every 2 minutes for hours (SMTP blocked on the VPS).
Now: sites that refuse the server are remembered and the job goes to her PC (OTP asked and typed there too), the digest
goes through her Gmail sign-in with a back-off, and Hoola Jaanch checks every part live."""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import select


def _conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


# ---------------------------------------------------------------- sites that refuse the server
def test_site_names_and_base_domains(env):
    from app.operator import reach
    assert reach.base("myaadhaar.uidai.gov.in") == "uidai.gov.in" and reach.base("tathya.uidai.gov.in") == "uidai.gov.in"
    assert reach.base("www.irctc.co.in") == "irctc.co.in" and reach.base("a.b.example.com") == "example.com"
    assert reach.site_for("माझे आधार कार्ड डाउनलोड करा.") == "myaadhaar.uidai.gov.in"
    assert reach.site_for("Aadhaar card download kar do") == "myaadhaar.uidai.gov.in"
    assert reach.site_for("PNR status dekho 4512345678") == "www.irctc.co.in"
    assert reach.site_for("kuch bhi", "https://myaadhaarbeta.uidai.gov.in/genericDownloadAadhaar/en") == "myaadhaarbeta.uidai.gov.in"
    assert reach.site_for("open example.org and read it") == "example.org"


def test_a_failed_job_teaches_which_sites_refuse_the_server(env):
    from app.operator import reach
    net_failed = ["tathya.uidai.gov.in:443 did not answer this server (timed out)",
                  "myaadhaar.uidai.gov.in: name not found (DNS)", "junk line"]
    got = reach.learn_from_job("https://myaadhaar.uidai.gov.in/", "Aadhaar download", False, net_failed, "chrome-error://chromewebdata/")
    assert got == ["uidai.gov.in"]
    assert reach.remembered("myaadhaarbeta.uidai.gov.in")              # same family of sites
    chk = reach.check("Aadhaar card download kar do", "", live=False)
    assert chk["ok"] is False and chk["remembered"] and chk["site"] == "myaadhaar.uidai.gov.in"
    reach.learn_from_job("", "Aadhaar download", True, [], "https://myaadhaar.uidai.gov.in/done")   # it worked once
    assert reach.remembered("myaadhaar.uidai.gov.in") is None
    # old refusals expire
    reach.note_fail("www.irctc.co.in", "x")
    d = json.loads(reach._path().read_text())
    d["irctc.co.in"]["last_bad"] = time.time() - reach.KEEP_S - 5
    reach._path().write_text(json.dumps(d))
    assert reach.remembered("www.irctc.co.in") is None


def test_past_failures_are_learned_on_the_first_check(env, monkeypatch):
    """Her VPS already has 7 failed Aadhaar jobs that ended on Chrome's error page: learned without a new failure."""
    from app.db import session
    from app.operator import reach
    from app.operator.models import OperatorTask
    with session() as s:
        s.add(OperatorTask(tenant_id="default", task="Aadhaar card download kar do", status="failed",
                           url="chrome-error://chromewebdata/"))
    monkeypatch.setattr(reach, "_booted", False)
    assert reach.remembered("myaadhaar.uidai.gov.in")


class _FakeHubConn:
    def __init__(self, control=True):
        self.info = {"control": control}
        self.device_id = "pc1"


def test_a_blocked_site_job_moves_to_her_pc(env, monkeypatch):
    from app.agent import operator_tools
    from app.agent.tools import Ctx
    from app.config import get_settings
    from app.operator import reach
    from app.operator import service as ops
    monkeypatch.setenv("OPERATOR_PREFLIGHT", "true")
    get_settings.cache_clear()
    reach.note_fail("myaadhaar.uidai.gov.in", "timed out")
    started, pc_tasks = [], []
    monkeypatch.setattr(ops, "start", lambda *a, **k: started.append(a) or {"id": "x", "status": "queued"})

    async def fake_pc_do(ctx, task, _wait=None, **_):
        pc_tasks.append(task)
        return {"session_id": "pcop_1", "status": "running", "step": 0}
    import app.agent.pc_tools as pc_tools
    monkeypatch.setattr(pc_tools, "pc_do", fake_pc_do)
    ctx = Ctx(tenant_id="default", conversation_id=_conv())
    r = asyncio.run(operator_tools.computer_operator(ctx, "start", task="Papa ka Aadhaar {id:ab12cd34ef} download kar do"))
    assert r["moved_to"] == "pc" and "PC" in r["say"] and not started
    assert "{id:ab12cd34ef}" in pc_tasks[0] and "ask_otp" in pc_tasks[0]
    assert reach.STATS["routed_pc"] >= 1

    # PC offline: told at once, plainly, with the choices
    async def offline(ctx, task, _wait=None, **_):
        from app.agent.tools import ToolError
        raise ToolError("PC offline hai.")
    monkeypatch.setattr(pc_tools, "pc_do", offline)
    r = asyncio.run(operator_tools.computer_operator(ctx, "start", task="Aadhaar download karo"))
    assert r["status"] == "site_blocks_server" and "open_on_phone" in r["next"] and not started
    # she asks to try the server anyway
    r = asyncio.run(operator_tools.computer_operator(ctx, "start", task="Aadhaar download karo", where="server"))
    assert started and r["task_id"] == "x"
    get_settings.cache_clear()


def test_browse_web_does_not_walk_into_a_known_wall(env, monkeypatch):
    from app.agent import web_tools
    from app.agent.tools import Ctx
    from app.config import get_settings
    from app.operator import reach
    monkeypatch.setenv("OPERATOR_PREFLIGHT", "true")
    get_settings.cache_clear()
    reach.note_fail("myaadhaar.uidai.gov.in", "timed out")
    r = asyncio.run(web_tools.browse_web(Ctx(tenant_id="default", conversation_id="c"), "Aadhaar download page kholo",
                                         "https://myaadhaar.uidai.gov.in/"))
    assert r["status"] == "site_blocks_server" and "computer_operator" in r["next"]
    get_settings.cache_clear()


# ---------------------------------------------------------------- OTP on her PC
def test_pc_operator_asks_for_the_otp_and_types_it_itself(env, monkeypatch):
    from app.db import Event, session
    from app.operator import service as ops
    from app.pc import operator as pcop
    conv = _conv()
    typed = []

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        typed.append((action, dict(args or {})))
        return {"ok": True}
    monkeypatch.setattr(pcop, "_pc", fake_pc)
    op = pcop.Op(id="pcop_otp", tenant="default", conv=conv, task="Aadhaar download")
    pcop.OPS[op.id] = op

    async def go():
        pcop._loop = asyncio.get_running_loop()
        asking = asyncio.create_task(pcop._ask_otp(op, {"reason": "myAadhaar", "digits": 6}))
        for _ in range(50):
            await asyncio.sleep(0.02)
            if ops.pending_otp("default") is not None:
                break
        p = ops.pending_otp("default")
        assert p is not None and p.id.startswith("pcotp_") and p.digits == 6
        got = await ops.answer_from_chat("default", "chaar paanch chhe saat aath nau")   # she just says it
        assert got["ok"] and "456789" not in json.dumps(got)
        return await asking
    try:
        msg = asyncio.run(go())
    finally:
        pcop.OPS.pop(op.id, None)
    assert typed == [("control", {"op": "type", "text": "456789"})]
    assert "456789" not in msg and "press the verify" in msg
    assert ops.recently_filled("default") and ops.pending_otp("default") is None
    with session() as s:
        cards = [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "operator_ask")).all()]
    assert cards[0]["status"] == "pending" and cards[0]["kind"] == "otp" and cards[-1]["status"] == "approved"
    assert all("456789" not in json.dumps(c) for c in cards)


def test_pc_otp_from_the_card_or_sms_and_a_refusal(env, monkeypatch):
    from app.operator import service as ops
    from app.pc import operator as pcop
    conv = _conv()

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        return {"ok": True}
    monkeypatch.setattr(pcop, "_pc", fake_pc)
    op = pcop.Op(id="pcop_otp2", tenant="default", conv=conv, task="DigiLocker login")
    pcop.OPS[op.id] = op

    async def go(answer_ok: bool):
        pcop._loop = asyncio.get_running_loop()
        asking = asyncio.create_task(pcop._ask_otp(op, {"reason": "DigiLocker"}))
        for _ in range(50):
            await asyncio.sleep(0.02)
            if pcop.pending_otp("default") is not None:
                break
        rid = pcop.pending_otp("default").id
        r = await ops.resolve("default", rid, "approved" if answer_ok else "rejected", "123456" if answer_ok else "")
        assert r["status"] == ("approved" if answer_ok else "rejected")
        return await asking
    try:
        assert "verify" in asyncio.run(go(True))
        assert "did not give" in asyncio.run(go(False))
    finally:
        pcop.OPS.pop(op.id, None)


# ---------------------------------------------------------------- the email digest
def _offline_setup(monkeypatch, smtp=True):
    from datetime import datetime, timedelta, timezone

    from app import offline
    from app.config import get_settings
    from app.db import PhoneSeen, session
    from app.events import notify
    if smtp:
        monkeypatch.setenv("EMAIL_ADDRESS", "owner@gmail.com")
        monkeypatch.setenv("EMAIL_PASSWORD", "app-pass")
    get_settings.cache_clear()
    offline._touched.clear()
    offline._FAIL.clear()
    conv = _conv()
    offline.touch("default")
    notify(conv, "Reminder: bijli ka bill")
    with session() as s:
        s.get(PhoneSeen, "default").at = datetime.now(timezone.utc) - timedelta(minutes=45)
    return offline


def test_digest_goes_through_her_gmail_sign_in(env, monkeypatch):
    from app import mail
    from app.mailbox import accounts
    offline = _offline_setup(monkeypatch)
    sent = []
    box = SimpleNamespace(kind="gmail", address="meghana@gmail.com", send=lambda msg: sent.append(msg) or {"message_id": "x"})
    monkeypatch.setattr(accounts, "boxes", lambda t: [box])

    async def smtp_never(*a, **k):
        raise AssertionError("SMTP must not be used when Gmail works")
    monkeypatch.setattr(mail, "send_email", smtp_never)
    assert asyncio.run(offline.send_due()) == 1
    assert sent[0]["From"] == "meghana@gmail.com" and "bijli ka bill" in sent[0].get_content()
    assert offline.STATS["via_api"] >= 1


def test_a_failing_digest_backs_off_instead_of_every_two_minutes(env, monkeypatch, caplog):
    from app import mail
    from app.mailbox import accounts
    offline = _offline_setup(monkeypatch)
    monkeypatch.setattr(accounts, "boxes", lambda t: [])
    tries = []

    async def smtp_down(*a, **k):
        tries.append(1)
        raise mail.MailError("Email bhejne mein dikkat: [Errno 101] Network is unreachable")
    monkeypatch.setattr(mail, "send_email", smtp_down)
    assert asyncio.run(offline.send_due()) == 0
    assert asyncio.run(offline.send_due()) == 0          # the worker calls again 2 minutes later: no new attempt
    assert len(tries) == 1
    n, next_at = offline._FAIL["default"]
    assert n == 1 and next_at - time.time() > 29 * 60
    assert "sign in with Google" in caplog.text
    offline._FAIL["default"] = (1, time.time() - 1)       # the wait is over: one more try, then a longer wait
    asyncio.run(offline.send_due())
    assert len(tries) == 2 and offline._FAIL["default"][1] - time.time() > 59 * 60


# ---------------------------------------------------------------- Hoola Jaanch
def test_jaanch_finds_what_is_broken_and_says_the_fix(env, monkeypatch):
    from app import jaanch, mail
    from app.agent import santosh
    from app.config import get_settings
    from app.operator import reach
    monkeypatch.setenv("EMAIL_ADDRESS", "owner@gmail.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "app-pass")
    get_settings.cache_clear()

    class _Models:
        async def list(self, limit=1):
            return []
    monkeypatch.setattr(santosh, "get_client", lambda: SimpleNamespace(models=_Models()))
    monkeypatch.setattr(reach, "probe", lambda host, port=443, timeout=5: (not host.startswith("myaadhaar"), "timed out"))
    monkeypatch.setattr(jaanch, "_tcp", lambda host, port, timeout=5.0: (False, "jawab nahi diya (timeout)"))
    from app.mailbox import accounts
    monkeypatch.setattr(accounts, "boxes", lambda t: [])
    r = asyncio.run(jaanch.run("default"))
    by = {c["id"]: c for c in r["checks"]}
    assert by["claude"]["ok"] is True
    assert by["gemini"]["ok"] is False and "GEMINI_API_KEY" in by["gemini"]["detail"]
    assert by["email"]["ok"] is False and "Google" in by["email"]["fix"]
    assert by["site:myaadhaar.uidai.gov.in"]["ok"] is False and "PC" in by["site:myaadhaar.uidai.gov.in"]["fix"]
    assert by["site:www.irctc.co.in"]["ok"] is True
    assert reach.remembered("myaadhaar.uidai.gov.in")       # the live check is remembered for the next job
    assert r["bad"] >= 3 and r["total"] == len(r["checks"]) and "report" in r and r["seconds"] < 30
    assert "chat" in r["report"] and "website" in r["report"]
    get_settings.cache_clear()


def test_jaanch_api_and_tool(env, monkeypatch):
    from fastapi.testclient import TestClient

    from app import jaanch, main
    from app.agent.jaanch_tools import hoola_jaanch
    from app.agent.tools import Ctx

    async def fake_run(tenant):
        return {"ok": 1, "bad": 1, "warn": 0, "total": 2, "say": "1 cheez kharab",
                "checks": [{"id": "a", "name": "A", "ok": True}, {"id": "b", "name": "B", "ok": False, "fix": "x"}],
                "report": {"chat": {}, "website": {}, "crashes": 0, "lessons": []}}
    monkeypatch.setattr(jaanch, "run", fake_run)
    with TestClient(main.app) as c:
        assert c.get("/api/jaanch").json()["bad"] == 1
        assert "chat" in c.get("/api/jaanch/report").json()
    r = asyncio.run(hoola_jaanch(Ctx(tenant_id="default", conversation_id="c"), "check"))
    assert [x["name"] for x in r["checks"]] == ["B"]          # only what is broken is read out
