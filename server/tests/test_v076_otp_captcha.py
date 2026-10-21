"""v0.76 Setu-operator flow: Hoola fills everything itself (even a hidden / password-style Aadhaar box), asks her only for
the OTP, shows the CAPTCHA picture on her phone, and takes the OTP / CAPTCHA she just says in chat straight into the box."""
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

AAD = "234567890124"

PAGE = b"""<!doctype html><html><head><title>e-KYC</title></head><body><h1>Apply</h1><form>
<label for=a>Aadhaar Number (OTP will be sent to the mobile linked with Aadhaar)</label>
<input id=a name=txtUidNo type=password>
<label for=o>Enter OTP</label><input id=o name=otp>
<img id=captchaImg src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='150' height='50'><rect width='150' height='50' fill='%23eee'/><text x='20' y='35' font-size='28'>X7pQ2</text></svg>" width=150 height=50>
<a href="#" id=reload title="Refresh captcha" onclick="document.getElementById('captchaImg').dataset.n='2';return false">&#8635;</a>
<label for=c>Enter captcha</label><input id=c name=captcha_text>
<label for=u>User ID</label><input id=u name=uid>
</form></body></html>"""
PAY = b"""<!doctype html><html><head><title>Razorpay - Secure Checkout</title></head><body><form>
<label for=o>Enter OTP sent by your bank</label><input id=o name=otp></form></body></html>"""


class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAY if self.path.startswith("/pay") else PAGE)

    def log_message(self, *a):
        pass


def test_guard_id_box_wins_over_otp_words_and_password_type():
    from app.operator import guard
    from app.operator.browser import field_kind
    node = {"attributes": {"name": "txtUidNo", "type": "password"}, "label": "Aadhaar Number (OTP will be sent)"}
    assert guard.classify_input(node) == "id"
    assert guard.classify_input({"attributes": {"name": "otp"}, "label": "Enter OTP sent to Aadhaar mobile"}) == "secret"
    assert guard.classify_input({"attributes": {"name": "pwd", "type": "password"}, "label": "Password"}) == "secret"
    assert guard.classify_input({"attributes": {"name": "uid"}, "label": "User ID"}) == "ok"
    assert field_kind({"type": "password", "name": "Aadhaar number", "nameAttr": "aadhaar"}) == "id"


def test_chat_words_that_are_an_otp_or_captcha():
    from app.operator import service as ops
    assert ops._OTP_SAID.match("482913") and ops._OTP_SAID.match("OTP 482 913 hai") and ops._OTP_SAID.match("otp is 4829")
    assert not ops._OTP_SAID.match("kal 3 baje 2 log aayenge 45 minute")
    assert ops._CAPTCHA_SAID.match("X7pQ2").group(1) == "X7pQ2"
    assert ops._CAPTCHA_SAID.match("captcha hai X7pQ2").group(1) == "X7pQ2"


try:
    import playwright  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False


@pytest.mark.skipif(not HAVE_PW, reason="needs playwright + chromium")
def test_setu_flow_in_a_real_browser(env, tmp_path):
    import re
    from app import idvault
    from app.operator import service as ops
    from app.operator.browser import Operator, fmt_snapshot
    rec = idvault.save("default", "aadhaar", AAD)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"

    async def go():
        op = Operator(tmp_path / "op", allow_private=True, screenshots=False)
        op.id_tenant = "default"
        ops._ops["default"] = (asyncio.get_running_loop(), op)
        try:
            s = await op.session("main")
            await op.goto(s, url)
            page = fmt_snapshot(await op.snapshot(s))
            ref = lambda label: re.search(r'\[(\w+)\] textbox "' + re.escape(label), page).group(1)   # noqa: E731
            aref, oref, cref, uref = ref("Aadhaar Number"), ref("Enter OTP"), ref("Enter captcha"), ref("User ID")
            assert "ID number" in page.split(f"[{aref}]")[1].split("\n")[0]
            # the hidden Aadhaar box takes the locker number (after her one approval: not a gov site)
            a = await op.request_human(s, "approve", "Aadhaar bharun?", aref)
            await op.resolve_human(a.id, "approved")
            assert (await op.act(s, "fill", aref, value=rec["ref"], approval_id=a.id))["ok"]
            assert await s.page.eval_on_selector("#a", "e => e.value") == AAD
            assert (await op.act(s, "fill", uref, value="meghana01"))["ok"]            # a login "User ID" is a normal box
            # OTP: she just says it in chat
            assert (await op.act(s, "fill", oref, value="482913"))["blocked"] == "secret"
            otp = await op.request_human(s, "otp", "Site ne OTP bheja hai, bataiye", oref)
            assert ops.chat_answer_target("default", "kal milte hain") is None
            got = await ops.answer_from_chat("default", "OTP 482913 hai")
            assert got["ok"] and "482913" not in str(got)
            assert await s.page.eval_on_selector("#o", "e => e.value") == "482913" and otp.status == "approved"
            # CAPTCHA: picture for her phone, refresh, and her answer in chat
            cap = await op.request_human(s, "captcha", "CAPTCHA bataiye", cref)
            png = await op.captcha_image(cap.id)
            assert png[:4] == b"\x89PNG" and len(png) > 200
            assert await op.captcha_refresh(cap.id)
            assert await s.page.eval_on_selector("#captchaImg", "e => e.dataset.n") == "2"
            assert (await ops.answer_from_chat("default", "X7pQ2"))["kind"] == "captcha"
            assert await s.page.eval_on_selector("#c", "e => e.value") == "X7pQ2"
            # a bank / payment OTP stays with her
            await op.goto(s, url + "pay")
            page = fmt_snapshot(await op.snapshot(s))
            pay = await op.request_human(s, "otp", "OTP bataiye", re.search(r'\[(\w+)\] textbox', page).group(1))
            assert pay.kind == "payment"
            assert ops.chat_answer_target("default", "482913") is None
        finally:
            ops._ops.pop("default", None)
            await op.shutdown()
    try:
        asyncio.run(go())
    finally:
        srv.shutdown()
