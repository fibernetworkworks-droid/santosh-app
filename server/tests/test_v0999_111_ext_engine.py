"""v0.999.111 ULTIMATE PC PLAN P1 (rest): page engine 2 on HER PC through the Hoola extension. The server engine
(pc/extlink.py) drives the very same pagekit.js the extension injects; here a stand-in extension runs it in a real
Chromium over CDP (and a second test loads the REAL extension into Chromium and talks to its engine.js over a socket)."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "desktop" / "ext" / "hoola-extension"
CHROME = "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else (shutil.which("chromium") or "")


def test_one_engine_three_copies():
    assert (ROOT / "desktop-linux" / "pagekit.py").read_text() == (ROOT / "server" / "app" / "pc" / "pagekit.py").read_text()
    sys.path.insert(0, str(ROOT / "desktop-linux"))
    import pagekit
    assert (EXT / "pagekit.js").read_text() == pagekit.extension_js()       # regenerate: python desktop-linux/pagekit.py
    m = json.loads((EXT / "manifest.json").read_text())
    assert m["optional_permissions"] == ["debugger"] and "alarms" in m["permissions"]
    assert 'importScripts("engine.js")' in (EXT / "background.js").read_text()
    eng = (EXT / "engine.js").read_text()
    assert "pageEngine !== true" in eng and "eval(" not in eng and "Input.dispatchMouseEvent" in eng


# ---------------------------------------------------------------- the server engine on a real page
class _CdpExt:
    """Stands in for the extension: the same three requests, answered over CDP in a real Chromium."""

    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.js = (EXT / "pagekit.js").read_text()

    def _cdp(self, method, params):
        import websockets.sync.client as W
        with W.connect(self.ws_url, max_size=16 * 1024 * 1024) as c:
            c.send(json.dumps({"id": 1, "method": method, "params": params}))
            while True:
                m = json.loads(c.recv())
                if m.get("id") == 1:
                    return m.get("result") or {}

    def answer(self, msg):
        if msg["op"] == "tab":
            r = self._cdp("Runtime.evaluate", {"expression": "({title: document.title, url: location.href})", "returnByValue": True})
            return r["result"]["value"]
        if msg["op"] == "js":
            self._cdp("Runtime.evaluate", {"expression": self.js})
            expr = f"window.__hoolaPK[{json.dumps(msg['fn'])}]({json.dumps(msg.get('args') or {})})"
            r = self._cdp("Runtime.evaluate", {"expression": expr, "returnByValue": True})
            return (r.get("result") or {}).get("value")
        if msg["op"] == "mouse":
            for e in msg["events"]:
                self._cdp("Input.dispatchMouseEvent", e)
            return {"done": True}


@pytest.fixture
def her_chrome(tmp_path, monkeypatch, env):
    if not CHROME:
        pytest.skip("no Chromium here")
    import httpx
    import uvicorn
    from fastapi import FastAPI
    from app import practice
    from app.pc import extlink
    monkeypatch.setenv("PRACTICE_DIR", str(tmp_path / "practice"))
    practice._MEM.clear()
    app = FastAPI()
    app.include_router(practice.router)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=srv.run, daemon=True).start()
    s = socket.socket(); s.bind(("127.0.0.1", 0)); dport = s.getsockname()[1]; s.close()
    cr = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", f"--remote-debugging-port={dport}",
                           f"--user-data-dir={tmp_path}/cr", "--window-size=1280,760", "about:blank"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            httpx.get(f"http://127.0.0.1:{dport}/json/version", timeout=1)
            break
        except Exception:
            time.sleep(0.25)
    page = next(t for t in httpx.get(f"http://127.0.0.1:{dport}/json", timeout=5).json() if t["type"] == "page")
    fake = _CdpExt(page["webSocketDebuggerUrl"])

    async def send(msg):
        loop = asyncio.get_running_loop()
        try:
            res = await loop.run_in_executor(None, fake.answer, msg)
            extlink.receive("t1", {"id": msg["id"], "ok": True, "result": res})
        except Exception as e:   # noqa: BLE001
            extlink.receive("t1", {"id": msg["id"], "ok": False, "error": str(e)})
    extlink.LINKS["t1"] = extlink.Link(tenant="t1", device_id="ext1", send=send)
    run = practice.new_run()

    def open_(p):
        fake._cdp("Page.navigate", {"url": f"http://127.0.0.1:{port}/practice/{run}/{p}"})
        time.sleep(1.2)
    try:
        yield extlink, open_, (lambda: practice.records(run))
    finally:
        extlink.LINKS.clear()
        cr.kill()
        srv.should_exit = True


def test_her_chrome_does_what_hoola_pc_does(her_chrome):
    X, open_, recs = her_chrome

    async def go():
        async def ref(name, role=None):
            els = (await X.handle("t1", "page_elements", {}))["elements"]
            for e in els:
                if name.lower() in (e.get("name") or "").lower() and (role is None or e["role"] == role):
                    return e["ref"]
            raise AssertionError(f"no {name!r} in {[(e['role'], e['name']) for e in els]}")
        open_("shadow")
        await X.handle("t1", "page_type", {"ref": await ref("work email"), "text": "ops@example.org"})
        r = await X.handle("t1", "page_click", {"ref": await ref("subscribe", "button")})
        assert r["clicked"] and "SHADOW-OK" in r["change"]
        open_("banner")
        t = await X.handle("t1", "page_type", {"ref": await ref("email"), "text": "news@example.com"})
        assert "news@example.com" not in json.dumps(t)
        r = await X.handle("t1", "page_click", {"ref": await ref("subscribe", "button")})
        assert r["clicked"] is False and "We use cookies" in r["covered_by"]
        await X.handle("t1", "page_click", {"ref": await ref("accept all")})
        assert "BANNER-OK" in (await X.handle("t1", "page_click", {"ref": await ref("subscribe", "button")}))["change"]
        open_("menu")
        assert "link: Reports" in (await X.handle("t1", "page_hover", {"ref": await ref("account")}))["change"]
        assert "MENU-OK" in (await X.handle("t1", "page_click", {"ref": await ref("reports")}))["change"]
        open_("wizard")
        f = await X.handle("t1", "page_fill_form", {"entries": [{"ref": await ref("full name"), "text": "Kwame Mensah"},
                                                                {"ref": await ref("date of birth"), "text": "12 April 1988"}]})
        assert f["filled"] == 2
        open_("login")
        els = (await X.handle("t1", "page_elements", {}))["elements"]
        pw = next(e["ref"] for e in els if e.get("type") == "password")
        with pytest.raises(X.ExtError, match="PASSWORD box"):
            await X.handle("t1", "page_type", {"ref": pw, "text": "practice-123"})
        open_("reorder")
        els = (await X.handle("t1", "page_elements", {}))["elements"]
        items = [e for e in els if e.get("draggable")]
        sec = next(e["ref"] for e in items if "Security" in e["name"])
        r = await X.handle("t1", "page_drag", {"ref": sec, "to_ref": items[0]["ref"]})
        assert r["how"] == "drag events"
        await X.handle("t1", "page_click", {"ref": await ref("save order")})
        txt = (await X.handle("t1", "page_text", {}))["text"]
        assert "Order your priorities" in txt
    asyncio.run(go())
    got = recs()
    assert got["shadow"]["email"] == "ops@example.org" and got["banner"]["email"] == "news@example.com"
    assert got["menu"]["opened"] == "reports" and got["reorder"]["order"].startswith("Security,") and "login" not in got


def test_operator_routes_her_pc_page_tools_to_the_extension(monkeypatch):
    from app.pc import extlink
    from app.pc import operator as O
    seen = []

    async def handle(tenant, action, a):
        seen.append((tenant, action))
        return {"title": "T", "elements": [{"ref": 1, "role": "link", "name": "Home"}]}
    monkeypatch.setattr(extlink, "handle", handle)
    monkeypatch.setattr(extlink, "ready", lambda t: True)
    op = O.Op(id="o1", tenant="t9", conv="c", task="x")
    assert asyncio.run(O._pc(op, "page_elements", {}))["elements"][0]["name"] == "Home"
    assert seen == [("t9", "page_elements")]
    names = {t.get("name") for t in O._tools_for(op)}
    assert {"page_hover", "page_drag"} <= names
    op.bg = True
    assert not {"page_hover", "page_drag"} & {t.get("name") for t in O._tools_for(op)}
    hp = O.Op(id="o2", tenant="t9", conv="c", task="x", kind=O.HOOLA_PC_KIND)

    async def hub_call(*a, **k):
        return {"via": "hub"}
    from app.pc.hub import hub
    monkeypatch.setattr(hub, "call", hub_call)
    assert asyncio.run(O._pc(hp, "page_elements", {})) == {"via": "hub"}      # Hoola PC keeps its own agent


def test_the_socket_needs_a_paired_token(env):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    with c.websocket_connect("/api/pc/ext-ws") as ws:
        ws.send_text(json.dumps({"type": "hello", "token": "spc_nope"}))
        assert json.loads(ws.receive_text())["type"] == "refused"


def test_the_real_extension_answers_over_its_socket(tmp_path):
    """The real engine.js + pagekit.js loaded in Chromium (permissions granted up front the way her 'Turn on' click
    grants them) connects to a socket, runs an engine function in the page and clicks with the real mouse."""
    if not CHROME:
        pytest.skip("no Chromium here")
    pw = pytest.importorskip("playwright.sync_api")
    import http.server
    import websockets.sync.server as WS
    ext = tmp_path / "ext"
    shutil.copytree(EXT, ext)
    m = json.loads((ext / "manifest.json").read_text())
    m["permissions"] += ["debugger"]
    m["host_permissions"] += ["http://127.0.0.1/*"]
    m["optional_host_permissions"] = []
    m.pop("optional_permissions")
    (ext / "manifest.json").write_text(json.dumps(m))
    # the engine asks for the same grants her Turn-on gives; with them given up front contains() must see them
    (ext / "engine.js").write_text((ext / "engine.js").read_text().replace(
        'permissions: ["debugger"], origins: ["https://*/*", "http://*/*"]', 'permissions: ["debugger"], origins: ["http://127.0.0.1/*"]'))
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<title>Shop</title><button id=b onclick=\"document.title='CLICKED'\">Buy later</button>")
    hs = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(site), **k))
    threading.Thread(target=hs.serve_forever, daemon=True).start()
    got = {}

    def handler(c):
        hello = json.loads(c.recv())
        got["hello"] = hello
        c.send(json.dumps({"id": "e1", "op": "js", "fn": "elements", "args": {}}))
        r = json.loads(c.recv())
        while r.get("type") == "ping":
            r = json.loads(c.recv())
        got["elements"] = r
        el = r["result"]["elements"][0]
        c.send(json.dumps({"id": "p1", "op": "js", "fn": "point", "args": {"path": el["path"], "role": el["role"], "name": el["name"]}}))
        p = json.loads(c.recv())
        x, y = p["result"]["x"], p["result"]["y"]
        c.send(json.dumps({"id": "m1", "op": "mouse", "events": [
            {"type": "mouseMoved", "x": x, "y": y, "button": "none"},
            {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
            {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1}]}))
        got["mouse"] = json.loads(c.recv())
        c.send(json.dumps({"id": "t1", "op": "tab"}))
        got["tab"] = json.loads(c.recv())
    ws = WS.serve(handler, "127.0.0.1", 0)
    threading.Thread(target=ws.serve_forever, daemon=True).start()
    wport = ws.socket.getsockname()[1]
    try:
        with pw.sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(str(tmp_path / "prof"), headless=True, executable_path=CHROME,
                                                       args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}",
                                                             "--headless=new"])
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(f"http://127.0.0.1:{hs.server_address[1]}/index.html")
            sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=15000)
            sw.evaluate(f"chrome.storage.local.set({{server: 'http://127.0.0.1:{wport}', token: 'spc_test', pageEngine: true}})")
            for _ in range(60):
                if "tab" in got:
                    break
                time.sleep(0.25)
            title = page.title()
            ctx.close()
    finally:
        hs.shutdown()
        ws.shutdown()
    assert got["hello"]["type"] == "hello" and got["hello"]["token"] == "spc_test"
    assert got["elements"]["ok"] and got["elements"]["result"]["elements"][0]["name"] == "Buy later"
    assert got["mouse"]["ok"] and got["tab"]["result"]["title"] == "CLICKED" and title == "CLICKED"


def test_the_manifest_loads_in_chrome():
    # v0.999.111 FOUND: "default_locale" without a _locales folder = Chrome refuses the whole extension
    m = json.loads((EXT / "manifest.json").read_text())
    assert "default_locale" not in m or (EXT / "_locales").is_dir()
    for f in ("background.js", "engine.js", "pagekit.js", "options.html", "popup.html", "offscreen.html"):
        assert (EXT / f).exists(), f
