"""v0.83 OTP by voice or text: the moment a website sends an OTP Hoola asks for it (out loud in a call, in the chat with a
push), she says or types it in any way people say numbers, and the system types it into the right box (one box or one
box per digit) and the job goes on. The OTP never lands in the saved chat; bank / payment OTPs stay hers."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from tests.test_voice import FakeSession, _connector, _gemini_env, _msg, wait_until


def test_spoken_otps_in_every_way():
    from app.operator.otpwords import find_otp, mask
    assert find_otp("4 5 6 7 8 9") == "456789"
    assert find_otp("OTP hai 456 789", 6) == "456789"
    assert find_otp("chaar paanch chhe saat aath nau", 6) == "456789"
    assert find_otp("चार पांच छह सात आठ नौ") == "456789"
    assert find_otp("४५६७८९") == "456789"
    assert find_otp("four five double six one two", 6) == "456612"
    assert find_otp("ek do teen chaar", 4) == "1234"
    assert find_otp("4 5 6 7 8 9 de do", 6) == "456789"
    assert find_otp("4 5 6 7 8 9 do", 6) == "456789"          # "do" = "give", not a 7th digit
    for no in ("ek minute ruko", "haan theek hai", "1 2 3", "mera number 9876543210", "do baje"):
        assert find_otp(no) is None, no
    assert mask("OTP hai 4 5 6 7 8 9 ji", "456789") == "OTP hai •••••• ji"
    assert "4" not in mask("चार पांच छह सात आठ नौ", "456789") and "चार" not in mask("चार पांच छह सात आठ नौ", "456789")
    assert mask("kal 10 baje", "456789") == "kal 10 baje"


def test_chat_answer_understands_words_and_the_box_length(monkeypatch):
    from app.operator import service as ops
    a = SimpleNamespace(id="h1", kind="otp", digits=6, status="pending", created=1)
    monkeypatch.setattr(ops, "_pending_otp_or_captcha", lambda t: a)
    assert ops.chat_answer_target("default", "chaar paanch chhe saat aath nau") == (a, "456789")
    assert ops.chat_answer_target("default", "OTP 482913 hai") == (a, "482913")
    assert ops.chat_answer_target("default", "ek do teen chaar") is None       # 4 digits, the box takes 6
    assert ops.chat_answer_target("default", "ruko abhi aaya nahi") is None


def test_hoola_asks_for_the_otp_in_the_call_and_the_chat(env, monkeypatch):
    from app import voice
    from app.operator import service as ops
    said, notes = [], []
    monkeypatch.setattr(voice, "inject", lambda conv, text: said.append((conv, text)) or 1)
    monkeypatch.setattr(ops, "_note", lambda row, text: notes.append(text))
    row = SimpleNamespace(conversation_id="c1", tenant_id="default")
    ops._ask_otp(row, SimpleNamespace(digits=6), "uidai.gov.in")
    assert said and "uidai.gov.in" in said[0][1] and "Never say the digits" in said[0][1]
    assert "6 ankon ka OTP" in notes[0] and "likh dijiye" in notes[0] and "call par bol dijiye" in notes[0]


def test_saying_the_otp_on_a_call_fills_the_box_and_hides_it(env, monkeypatch):
    from app import main
    from app.operator import service as ops
    _gemini_env(monkeypatch)
    pending = SimpleNamespace(id="hX", kind="otp", digits=6)
    filled = []

    async def fill(tenant, rid, value):
        filled.append((rid, value))
        pending_box["a"] = None
        return {"ok": True}

    pending_box = {"a": pending}
    monkeypatch.setattr(ops, "pending_otp", lambda t: pending_box["a"])
    monkeypatch.setattr(ops, "fill_otp", fill)
    fake = FakeSession([[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="haan OTP hai chaar paanch chhe")),
        _msg(input_transcription=types.Transcription(text=" saat aath nau")),
        _msg(model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x01\x00" * 50, mime_type="audio/pcm;rate=24000"))]),
             output_transcription=types.Transcription(text="Mil gaya, 4 5 6 7 8 9, bhar diya.")),
        _msg(turn_complete=True),
    ]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert wait_until(lambda: filled, timeout=5)
            assert wait_until(lambda: any("bhar diya gaya" in t for t in fake.texts), timeout=3)
            ws.send_text(json.dumps({"type": "end"}))
        assert filled == [("hX", "456789")]
        msgs = c.get(f"/api/conversations/{conv}/messages").json()
    text = json.dumps(msgs, ensure_ascii=False)
    assert "456789" not in text and "4 5 6 7 8 9" not in text and "saat aath nau" not in text
    assert "••••••" in text


# ------------------------------------------------------------------ a real page: one box per digit
PAGE = b"""<!doctype html><html><head><title>Verify</title></head><body><h1>Enter OTP</h1><form>
<label>Enter OTP sent to your mobile</label>
<div id=g><input id=d0 name=otp1 maxlength=1><input id=d1 name=otp2 maxlength=1><input id=d2 name=otp3 maxlength=1>
<input id=d3 name=otp4 maxlength=1><input id=d4 name=otp5 maxlength=1><input id=d5 name=otp6 maxlength=1></div>
<button type=button id=v>Verify OTP</button></form>
<script>document.querySelectorAll('#g input').forEach((e, i, all) => e.addEventListener('input', () => {
  if (e.value && all[i + 1]) all[i + 1].focus(); }));</script></body></html>"""


class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *a):
        pass


try:
    import playwright  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False


@pytest.mark.skipif(not HAVE_PW, reason="needs playwright + chromium")
def test_otp_said_in_words_goes_into_six_little_boxes(env, tmp_path):
    import re
    from app.operator import service as ops
    from app.operator.browser import Operator, fmt_snapshot
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"

    async def go():
        op = Operator(tmp_path / "op", allow_private=True, screenshots=False)
        ops._ops["default"] = (asyncio.get_running_loop(), op)
        try:
            s = await op.session("main")
            await op.goto(s, url)
            page = fmt_snapshot(await op.snapshot(s))
            first = re.search(r"\[(\w+)\] textbox", page).group(1)
            a = await op.request_human(s, "otp", "Site ne OTP bheja hai", first)
            assert a.kind == "otp" and a.digits == 6 and a.public()["digits"] == 6
            assert ops.pending_otp("default") is a
            got = await ops.answer_from_chat("default", "chaar paanch chhe saat aath nau")
            assert got["ok"] and "456789" not in json.dumps(got)
            vals = await s.page.eval_on_selector_all("#g input", "es => es.map(e => e.value).join('')")
            assert vals == "456789" and a.status == "approved"
            assert ops.recently_filled("default") and ops.pending_otp("default") is None
            after = fmt_snapshot(await op.snapshot(s))
            assert not re.search(r'"[4-9]"', after)          # no box shows its digit to the model
        finally:
            ops._ops.pop("default", None)
            ops._FILLED.pop("default", None)
            await op.shutdown()
    try:
        asyncio.run(go())
    finally:
        srv.shutdown()
