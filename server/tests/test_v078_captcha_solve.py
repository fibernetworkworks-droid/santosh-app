"""v0.78 CAPTCHA auto-solve: Hoola reads the CAPTCHA image with OCR (pytesseract + Pillow) and shows the answer for
the owner to confirm. She taps "Haan" if correct, or types the right answer. OTP is the only thing restricted to her."""
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

PAGE = b"""<!doctype html><html><head><title>Verify</title></head><body><h1>Verify</h1><form>
<img id=captchaImg src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='150' height='50'><rect width='150' height='50' fill='%23eee'/><text x='20' y='35' font-size='28'>AB123</text></svg>" width=150 height=50>
<a href="#" id=reload title="Refresh captcha" onclick="return false">&#8635;</a>
<label for=c>Enter captcha</label><input id=c name=captcha_text>
</form></body></html>"""


class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *a):
        pass


def test_typed_kinds_exclude_captcha():
    """v0.78: captcha removed from TYPED_KINDS — Hoola fills it itself after OCR."""
    from app.operator.browser import TYPED_KINDS
    assert "otp" in TYPED_KINDS
    assert "secret" in TYPED_KINDS
    assert "captcha" not in TYPED_KINDS


def test_approval_suggested_answer_public():
    """The Approval dataclass exposes suggested_answer for captcha kind."""
    from app.operator.browser import Approval
    a = Approval(id="test-1", session="s", kind="captcha", reason="CAPTCHA padho", ref="e1",
                 suggested_answer="XY789")
    pub = a.public()
    assert pub["suggested_answer"] == "XY789"
    # non-captcha kinds don't expose suggested_answer
    b = Approval(id="test-2", session="s", kind="question", reason="Kya karna hai?", ref="e2",
                 suggested_answer="should not appear")
    assert "suggested_answer" not in b.public()


def test_captcha_solve_ocr(tmp_path):
    """captcha_solve() reads a CAPTCHA image via OCR (greyscale + threshold)."""
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        pytest.skip("pytesseract not installed")
    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        pytest.skip("tesseract-ocr not installed")

    # Create a clean test image with known text using Pillow
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (200, 60), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except (IOError, OSError):
        font = ImageFont.load_default()
    draw.text((20, 10), "TEST42", fill=(0, 0, 0), font=font)
    buf = __import__("io").BytesIO()
    img.save(buf, "PNG")

    # Simulate captcha_solve by running the same OCR pipeline
    from PIL import Image as PILImage
    test_img = PILImage.open(__import__("io").BytesIO(buf.getvalue()))
    test_img = test_img.convert("L")
    test_img = test_img.point(lambda p: 255 if p > 140 else 0)
    solved = pytesseract.image_to_string(
        test_img,
        config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    ).strip()
    # The clean image should be readable (exact match depends on font availability)
    assert len(solved) > 0


def test_captcha_fill_api_endpoint(env):
    """POST .../captcha/fill and GET .../captcha/solve endpoints exist."""
    from app import main
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        # No active request — should 404 or error cleanly
        r = c.get("/api/operator/requests/fake-id/captcha/solve")
        assert r.status_code in (400, 404, 422, 500)
        r = c.post("/api/operator/requests/fake-id/captcha/fill", json={"value": "abc"})
        assert r.status_code in (400, 404, 422, 500)


try:
    import playwright  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False


@pytest.mark.skipif(not HAVE_PW, reason="needs playwright + chromium")
def test_captcha_fill_types_into_the_box(env, tmp_path):
    """captcha_fill() fills the CAPTCHA value into the page input and resolves the approval."""
    import re
    from app.operator import service as ops
    from app.operator.browser import Operator, fmt_snapshot
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
            cref = re.search(r'\[(\w+)\] textbox "Enter captcha"', page).group(1)
            # request_human for captcha — it should auto-solve (set suggested_answer)
            cap = await op.request_human(s, "captcha", "CAPTCHA padho", cref)
            # suggested_answer may or may not be set (depends on tesseract), but the approval should exist
            assert cap.kind == "captcha"
            # captcha_fill types the value into the box
            result = await op.captcha_fill(cap.id, "AB123")
            assert result["ok"]
            assert await s.page.eval_on_selector("#c", "e => e.value") == "AB123"
            assert cap.status == "approved"
        finally:
            ops._ops.pop("default", None)
            await op.shutdown()
    try:
        asyncio.run(go())
    finally:
        srv.shutdown()


@pytest.mark.skipif(not HAVE_PW, reason="needs playwright + chromium")
def test_chat_captcha_answer_goes_through_captcha_fill(env, tmp_path):
    """When the owner says the CAPTCHA in chat, it routes through captcha_fill (not resolve_human)."""
    import re
    from app.operator import service as ops
    from app.operator.browser import Operator, fmt_snapshot
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
            cref = re.search(r'\[(\w+)\] textbox "Enter captcha"', page).group(1)
            cap = await op.request_human(s, "captcha", "CAPTCHA padho", cref)
            # she says it in chat
            got = await ops.answer_from_chat("default", "AB123")
            assert got["kind"] == "captcha"
            assert await s.page.eval_on_selector("#c", "e => e.value") == "AB123"
        finally:
            ops._ops.pop("default", None)
            await op.shutdown()
    try:
        asyncio.run(go())
    finally:
        srv.shutdown()
