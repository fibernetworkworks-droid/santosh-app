"""v0.81 (owner's decision): Hoola types Aadhaar / PAN / any number with no restriction - in its own browser (Computer
Operator + browse_web) and on the PC. Still hers: OTP, login passwords / PIN, card number / CVV (by the box)."""
import asyncio
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

AAD = "234567890124"
PAGE = b"""<!doctype html><html><body><h1>Bill</h1><form>
<label for=c>Consumer number</label><input id=c name=consumer_no>
<label for=v>Aadhaar VID</label><input id=v name=aadhaar_vid>
<label for=a>Aadhaar card number</label><input id=a name=aadhaar_card_no type=password>
<label for=o>Enter OTP</label><input id=o name=otp>
<label for=k>Card number</label><input id=k name=cardnumber autocomplete=cc-number>
</form></body></html>"""


class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *a):
        pass


def test_operator_guard_value_never_blocks():
    from app.operator import guard
    box = lambda **a: {"attributes": a}                                                 # noqa: E731
    assert guard.classify_input(box(name="consumer_no"), "1234 5678 9012 3456") == "ok"   # 16 digits, not a card box
    assert guard.classify_input(box(name="mobile"), "9876543210") == "ok"
    assert guard.classify_input(box(name="aadhaar"), AAD) == "id"
    assert guard.classify_input(box(name="otp")) == "secret"
    assert guard.classify_input(box(name="cc", autocomplete="cc-number")) == "secret"
    assert guard.classify_input({"attributes": {"name": "x"}, "label": "Card number"}) == "secret"


def test_worker_guard_types_aadhaar_and_numbers():
    from browser_worker import guard
    f = lambda t="", **a: guard.classify_input({"tag": "input", "attributes": a}, t)  # noqa: E731
    assert f(AAD, name="aadhaar_no") == "ok"
    assert f("4111 1111 1111 1111", name="ref") == "ok"
    assert f(name="x", **{"aria-label": "Aadhaar card number"}) == "ok"
    assert f(name="otp") == "secret" and f(type="password") == "secret" and f(name="cardnumber") == "secret"


def test_browse_web_gets_the_real_number_and_the_model_gets_it_masked(env, monkeypatch):
    from app import browser, idvault
    from app.agent import web_tools
    from tests.test_life import conv_ctx
    rec = idvault.save("default", "aadhaar", AAD)
    seen = {}

    def start(tenant, task, url, wait, conv):
        seen["task"] = task
        return {"status": "done", "summary": f"Status checked for Aadhaar {AAD[:4]} {AAD[4:8]} {AAD[8:]}"}
    monkeypatch.setattr(browser, "start", start)
    monkeypatch.setattr(browser, "deliver", lambda t, c, res, x: {"answer": res["summary"]})
    out = asyncio.run(web_tools.browse_web(conv_ctx(), f"Check status for Aadhaar {rec['ref']}"))
    assert AAD in seen["task"]
    assert AAD[:4] not in json.dumps(out) and "0124" in json.dumps(out)


def test_pc_operator_types_the_locker_number(env, monkeypatch):
    from app import idvault
    from app.pc import operator as pcop
    rec = idvault.save("default", "aadhaar", AAD)
    sent = []

    async def fake_pc(op, action, args=None, timeout=20):
        sent.append((action, args))
        return {}
    monkeypatch.setattr(pcop, "_pc", fake_pc)
    op = pcop.Op(id="pcop_t", tenant="default", conv="c", task="t")
    out = asyncio.run(pcop._do(op, "type", {"text": rec["ref"]}))
    assert out == "typed" and sent[-1][1]["text"] == AAD and AAD not in out
    assert asyncio.run(pcop._do(op, "type", {"text": "{id:zzzzzzzz}"})).startswith("REFUSED")


def test_desktop_types_any_number():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))
    from santosh_desktop import control
    assert not hasattr(control, "SECRET_TEXT")


try:
    import playwright  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False


@pytest.mark.skipif(not HAVE_PW, reason="needs playwright + chromium")
def test_operator_fills_any_number_on_any_site(env, tmp_path):
    from app import idvault
    from app.operator.browser import Operator, fmt_snapshot
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
            ref = lambda label: re.search(r'\[(\w+)\] textbox "' + re.escape(label), page).group(1)  # noqa: E731
            assert (await op.act(s, "fill", ref("Consumer number"), value="1234567890123456"))["ok"]
            assert await s.page.eval_on_selector("#c", "e => e.value") == "1234567890123456"
            r = await op.act(s, "fill", ref("Aadhaar VID"), value="9123 4567 8901 2345")
            assert r["ok"] and await s.page.eval_on_selector("#v", "e => e.value") == "9123 4567 8901 2345"
            r = await op.act(s, "fill", ref("Aadhaar card number"), value=AAD)      # hidden box, no tap, plain number
            assert r["ok"] and AAD not in json.dumps(r)
            assert await s.page.eval_on_selector("#a", "e => e.value") == AAD
            assert any(x["masked"].endswith("0124") for x in idvault.list_("default"))   # kept in her locker
            assert all(AAD not in json.dumps(st) for st in s.trace)
            assert (await op.act(s, "fill", ref("Enter OTP"), value="482913"))["blocked"] == "secret"
            assert (await op.act(s, "fill", ref("Card number"), value="4111111111111111"))["blocked"] == "secret"
        finally:
            await op.shutdown()
    try:
        asyncio.run(go())
    finally:
        srv.shutdown()
