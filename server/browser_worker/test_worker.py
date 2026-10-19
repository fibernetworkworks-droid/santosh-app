"""Santosh Browser worker tests: a real headless Chromium + browser-use, driven by a scripted fake model against
local test pages. Skipped when browser-use isn't installed (it lives in the worker's own venv).

    cd server/browser_worker && ALLOW_PRIVATE_NETWORK=1 CHROMIUM_PATH=/path/to/chrome ../.venv-browser/bin/python -m pytest -q
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import guard  # noqa: E402

PAGES = {
    "/": """<html><head><title>Akola Seva</title></head><body><h1>Akola Seva</h1>
        <form action="/search"><input name="q" placeholder="Search"><button type="submit">Search</button></form>
        <a href="/fees">Fees</a> <a href="/apply">Apply online</a> <a href="/login">Login</a> <a href="/pay">Pay bill</a></body></html>""",
    "/fees": "<html><head><title>Fees</title></head><body><p>Birth certificate fee is Rs 25. Office open 10am-5pm.</p></body></html>",
    "/apply": """<html><head><title>Apply</title></head><body><form action="/done" method="get">
        <label>Name <input name="name"></label><button type="submit">Submit application</button></form></body></html>""",
    "/done": "<html><head><title>Done</title></head><body><p>Application received. Number AKL-778.</p></body></html>",
    "/login": """<html><head><title>Login</title></head><body><form><input name="user" placeholder="Mobile">
        <input type="password" name="pw" placeholder="Password"><button>Sign in</button></form></body></html>""",
    "/pay": """<html><head><title>Pay</title></head><body><p>Due Rs 540</p><button onclick="location='/paid'">Pay now</button></body></html>""",
    "/paid": "<html><body>PAID</body></html>",
}


class H(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        body = PAGES.get(path, "<html><body>not found</body></html>").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.server.hits.append(self.path)  # type: ignore[attr-defined]

    def log_message(self, *a):
        pass


# ----------------------------------------------------------------------------- pure guard tests (always run)
def test_guard_rules():
    assert guard.classify_click({"tag": "button", "text": "Pay now", "attributes": {}}) == "payment"
    assert guard.classify_click({"tag": "button", "text": "Place order", "attributes": {}}) == "payment"
    assert guard.classify_click({"tag": "button", "text": "Submit application", "attributes": {}}) == "commit"
    assert guard.classify_click({"tag": "button", "text": "जमा करें", "attributes": {}}) == "commit"
    assert guard.classify_click({"tag": "a", "text": "Apply online", "attributes": {"href": "/apply"}}) == "ok"
    assert guard.classify_click({"tag": "a", "text": "Delete account", "attributes": {"href": "/x"}}) == "commit"
    assert guard.classify_click({"tag": "button", "text": "Search", "attributes": {"type": "submit"}, "in_form": True}) == "ok"
    assert guard.classify_click({"tag": "button", "text": "Go ahead", "attributes": {"type": "submit"}, "in_form": True}) == "commit"
    assert guard.classify_input({"tag": "input", "attributes": {"type": "password"}}) == "secret"
    assert guard.classify_input({"tag": "input", "attributes": {"name": "otp"}}) == "secret"
    assert guard.classify_input({"tag": "input", "attributes": {"name": "aadhaar_no"}}) == "secret"
    assert guard.classify_input({"tag": "input", "attributes": {"name": "full_name"}}, "Meghana") == "ok"
    assert guard.classify_input({"tag": "input", "attributes": {"name": "ref"}}, "4111 1111 1111 1111") == "secret"
    assert guard.classify_keys("Enter", {"attributes": {"name": "q"}}) == "ok"
    assert guard.classify_keys("Enter", {"attributes": {"name": "name"}}) == "commit"
    assert guard.url_problem("https://web.whatsapp.com/")
    assert guard.url_problem("http://127.0.0.1:20128/dashboard")
    assert guard.url_problem("http://169.254.169.254/latest/meta-data")
    assert guard.url_problem("file:///etc/passwd")
    assert guard.url_problem("http://santosh.local/")
    assert guard.url_problem("https://irctc.co.in") == ""


def test_netguard_blocks_private_addresses():
    from netguard import NetGuard

    async def go():
        g = NetGuard()
        for host in ("127.0.0.1", "10.0.0.5", "169.254.169.254", "localhost", "[::1]"):
            with pytest.raises(PermissionError):
                await g.resolve(host, 443)
        with pytest.raises(PermissionError):
            await g.resolve("8.8.8.8", 22)       # only web ports
        assert await g.resolve("8.8.8.8", 443) == "8.8.8.8"
    asyncio.run(go())


def test_netguard_proxy_refuses_local_targets():
    from netguard import NetGuard

    async def go():
        g = NetGuard()
        port = await g.start()
        out = []
        for req in (b"CONNECT 127.0.0.1:443 HTTP/1.1\r\nHost: 127.0.0.1:443\r\n\r\n",
                    b"GET http://169.254.169.254/latest/meta-data HTTP/1.1\r\nHost: 169.254.169.254\r\n\r\n",
                    b"CONNECT web.whatsapp.com:443 HTTP/1.1\r\n\r\n"):
            r, w = await asyncio.open_connection("127.0.0.1", port)
            w.write(req)
            await w.drain()
            out.append(await asyncio.wait_for(r.readline(), 5))
            w.close()
        await g.stop()
        return out
    assert all(b"403" in line for line in asyncio.run(go()))


# ----------------------------------------------------------------------------- end to end with Chromium
import importlib.util  # noqa: E402

needs_browser = pytest.mark.skipif(importlib.util.find_spec("browser_use") is None,
                                   reason="browser-use lives in the worker's own venv")


def find(text: str, label: str) -> int:
    """Index of the element whose line mentions label, from browser-use's element list."""
    cur = None
    for line in text.splitlines():
        m = re.search(r"\[(\d+)\]", line)
        if m:
            cur = int(m.group(1))
        if cur is not None and label.lower() in line.lower():
            return cur
    raise AssertionError(f"{label} not on page:\n{text[:3000]}")


class FakeLLM:
    """Plays a fixed script; each step sees the page text and returns browser-use actions."""
    model = "fake"
    _verified_api_keys = True

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    @property
    def provider(self):
        return "fake"

    @property
    def name(self):
        return "fake"

    @property
    def model_name(self):
        return "fake"

    async def ainvoke(self, messages, output_format=None, **kw):
        from browser_use.llm.views import ChatInvokeCompletion
        text = ""
        for m in messages:
            c = getattr(m, "content", "")
            if isinstance(c, list):
                c = " ".join(getattr(p, "text", "") or "" for p in c)
            text += "\n" + str(c)
        last = text[text.rfind("<browser_state>"):] if "<browser_state>" in text else text[-20000:]
        step = self.script.pop(0) if self.script else (lambda t: [{"done": {"text": "out of script", "success": False}}])
        self.calls += 1
        acts = step(last)
        out = output_format.model_validate({"evaluation_previous_goal": "ok", "memory": "", "next_goal": "go",
                                            "action": acts}) if output_format else str(acts)
        return ChatInvokeCompletion(completion=out, usage=None)


@pytest.fixture(scope="module")
def site():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    srv.hits = []  # type: ignore[attr-defined]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", srv
    srv.shutdown()


def run(coro):
    """Run one test's steps, then close every browser it opened on the same event loop."""
    import worker

    async def wrapped():
        try:
            return await coro
        finally:
            for sid, sess in list(worker.SESSIONS.items()):
                if sess.run and not sess.run.done():
                    sess.run.cancel()
                await worker.close(sess)
                worker.SESSIONS.pop(sid, None)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(wrapped())
    finally:
        loop.close()


async def call(method, path, **kw):
    import httpx
    import worker
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=worker.app), base_url="http://w", timeout=200) as c:
        r = await c.request(method, path, headers={"x-worker-key": worker.WORKER_KEY}, **kw)
        return r


def body(task, url, tenant="t1", wait=120):
    return {"tenant": tenant, "task": task, "start_url": url, "llm": {"provider": "fake"}, "wait_seconds": wait, "max_steps": 8}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import worker
    monkeypatch.setattr(worker, "WORKER_KEY", "k" * 32)
    monkeypatch.setattr(worker, "ALLOW_PRIVATE", True)


@needs_browser
def test_read_page_and_answer(site):
    base, srv = site
    import worker

    async def go():
        worker.app.state.test_llm = FakeLLM([
            lambda t: [{"click": {"index": find(t, "Fees")}}],
            lambda t: [{"done": {"text": "Birth certificate fee is Rs 25 (Akola Seva site).", "success": True}}],
        ])
        r = await call("POST", "/tasks", json=body("birth certificate fee?", base + "/"))
        assert r.status_code == 200, r.text
        out = r.json()
        live = (await call("GET", f"/tasks/{out['session_id']}/live", params={"tenant": "t1"})).json()
        img = await call("GET", f"/tasks/{out['session_id']}/frame", params={"tenant": "t1"})
        other = await call("GET", f"/tasks/{out['session_id']}/live", params={"tenant": "someone-else"})
        return out, live, img, other
    out, live, img, other = run(go())
    assert out["status"] == "done", out
    assert "Rs 25" in out["summary"] and out["url"].endswith("/fees")
    assert out.get("screenshot_jpeg_b64")
    assert live["status"] == "done" and live["seq"] >= 1 and live["action"] == "Ho gaya" and live["step"] >= 1
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg" and img.content[:2] == b"\xff\xd8"
    assert other.status_code == 404


@needs_browser
def test_submit_waits_for_tap_then_continues(site):
    base, srv = site
    import worker

    async def go():
        worker.app.state.test_llm = FakeLLM([
            lambda t: [{"input": {"index": find(t, "name"), "text": "Meghana Ingle"}}],
            lambda t: [{"click": {"index": find(t, "Submit application")}}],
            # after approval
            lambda t: [{"click": {"index": find(t, "Submit application")}}],
            lambda t: [{"done": {"text": "Application received, number AKL-778.", "success": True}}],
        ])
        r = (await call("POST", "/tasks", json=body("apply for birth certificate", base + "/apply"))).json()
        assert r["status"] == "needs_confirm", r
        assert "Submit application" in r["pending"]["label"]
        assert not any(h.startswith("/done") for h in srv.hits)      # nothing submitted yet
        bad = await call("POST", f"/tasks/{r['session_id']}/approve", json={"tenant": "other", "pending_id": r["pending"]["id"]})
        assert bad.status_code == 404                                  # another person can't approve it
        ok = (await call("POST", f"/tasks/{r['session_id']}/approve",
                         json={"tenant": "t1", "pending_id": r["pending"]["id"], "wait_seconds": 120})).json()
        return ok
    out = run(go())
    assert out["status"] == "done", out
    assert "AKL-778" in out["summary"]
    assert any(h.startswith("/done?name=Meghana") for h in srv.hits)


@needs_browser
def test_password_and_payment_are_never_done(site):
    base, srv = site
    import worker

    async def go():
        worker.app.state.test_llm = FakeLLM([lambda t: [{"input": {"index": find(t, "Password"), "text": "hunter2"}}]])
        a = (await call("POST", "/tasks", json=body("log in", base + "/login"))).json()
        worker.app.state.test_llm = FakeLLM([lambda t: [{"click": {"index": find(t, "Pay now")}}]])
        b = (await call("POST", "/tasks", json=body("pay my bill", base + "/pay"))).json()
        return a, b
    a, b = run(go())
    assert a["status"] == "needs_user", a
    assert b["status"] == "needs_payment", b
    assert "/paid" not in srv.hits


@needs_browser
def test_blocked_sites_and_auth(site):
    import worker

    async def go():
        worker.app.state.test_llm = FakeLLM([lambda t: [{"navigate": {"url": "https://web.whatsapp.com/"}}]])
        r = await call("POST", "/tasks", json=body("open whatsapp web", "https://web.whatsapp.com/"))
        import httpx
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=worker.app), base_url="http://w") as c:
            unauth = await c.post("/tasks", json=body("x y z", ""))
        return r, unauth
    r, unauth = run(go())
    assert r.status_code == 400 and "WhatsApp" in r.json()["detail"]
    assert unauth.status_code == 401


@needs_browser
def test_unfinished_task_returns_what_it_found_and_timeline(site):
    base, srv = site
    import worker

    async def go():
        worker.app.state.test_llm = FakeLLM([
            lambda t: [{"click": {"index": find(t, "Fees")}}],
            lambda t: [{"done": {"text": "Fee page found: Rs 25, but office timings page was not reachable.", "success": False}}],
        ])
        r = (await call("POST", "/tasks", json=body("fee and timings", base + "/"))).json()
        live = (await call("GET", f"/tasks/{r['session_id']}/live", params={"tenant": "t1"})).json()
        return r, live
    r, live = run(go())
    assert r["status"] == "partial", r
    assert "Rs 25" in r["summary"] and "Pages dekhe" in r["summary"]
    assert [s["step"] for s in live["timeline"]] == [1, 2] and live["timeline"][0]["do"] == "click"


@needs_browser
def test_probe_reports_page_and_bot_blocks(site):
    base, srv = site
    import worker
    PAGES["/blocked"] = "<html><head><title>Attention Required! | Cloudflare</title></head><body>Sorry, you have been blocked</body></html>"

    async def go():
        return (await call("POST", "/probe", json={"urls": [base + "/fees", base + "/blocked", "https://web.whatsapp.com/"]})).json()
    r = run(go())["results"]
    assert r[0]["title"] == "Fees" and "Rs 25" in r[0]["text"] and not r[0].get("site_blocks_bots")
    assert "Headless" not in r[0]["browser_seen_as"]["user_agent"]
    assert r[1]["site_blocks_bots"] is True
    assert "refused by Santosh" in r[2]["error"]
