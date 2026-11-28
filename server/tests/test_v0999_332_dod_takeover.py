"""v0.999.332 HOOLA DOD, HER HANDS ON ITS BROWSER (owner, after the kwant read: "Hand over the bot's browser to sign in
or solve a CAPTCHA ... work on it").

The coworker asks with hoola_ask kind=browser; she takes over its page on the Hoola DOD page (clicks on the live picture,
keys, typing) and presses Done. Her input reaches OpenClaw's own browser tool through /tools/invoke (act: clickCoords /
press, batched), only on that task's tab and only while it waits for her there. What she types is never stored, logged
or shown to the model. A fake OpenClaw stands in for the real one.
"""
import base64
import io
import json
import logging
import os

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0999_306_dod import BASE, FakeClaw, _call, _sse, _wait, dod  # noqa: F401

SECRET = "hunter2-Pass word"


def _jpeg(w=800, h=500):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (240, 240, 240)).save(buf, "JPEG")
    return buf.getvalue()


class SignInClaw(FakeClaw):
    """Asks her to sign in (kind=browser), then finishes; serves screenshots and records act calls."""

    def __init__(self, workspace_of):
        super().__init__(workspace_of)
        self.acts, self.jpg = [], _jpeg()

    def __call__(self, req: httpx.Request):
        if req.url.path == "/tools/invoke":
            body = json.loads(req.content)
            assert body["tool"] == "browser" and body["sessionKey"].startswith("hoola-dod-")
            if body["action"] == "screenshot":
                return httpx.Response(200, json={"ok": True, "result": {
                    "details": {"targetId": "t7"},
                    "content": [{"type": "image", "data": base64.b64encode(self.jpg).decode(), "mimeType": "image/jpeg"}]}})
            assert body["action"] == "act"
            self.acts.append(body["args"]["request"])
            return httpx.Response(200, json={"ok": True, "result": {"content": [{"type": "text", "text": "ok"}]}})
        if req.url.path == "/v1/responses":
            body = json.loads(req.content)
            first = body["input"][0]
            if first.get("type") == "message":
                self.bodies.append(body)
                self.headers.append(dict(req.headers))
                self.n += 1
                out = [_call("hoola_ask", {"question": "Please sign in to Swiggy", "kind": "browser",
                                           "details": "The page asks for your phone number and a code."}, "s1")]
                resp = {"id": f"resp_{self.n}", "status": "completed", "output": out}
                return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                      content=_sse([{"type": "response.completed", "response": resp}]))
            if first.get("call_id") == "s1":
                self.bodies.append(body)
                self.n += 1
                out = [_call("hoola_done", {"summary": "Signed in. Your order list is open."}, "s2")]
                resp = {"id": f"resp_{self.n}", "status": "completed", "output": out}
                return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                      content=_sse([{"type": "response.completed", "response": resp}]))
        return super().__call__(req)


@pytest.fixture
def on(dod, monkeypatch):
    GW, S, docker = dod
    monkeypatch.setenv("DOD_ENGINE", "true")
    monkeypatch.setenv("OPENROUTER_PROVISIONING_KEY", "prov-key")
    from app.config import get_settings
    get_settings.cache_clear()
    GW._VIEWS.clear()
    t_id = get_settings().tenant_id
    claw = SignInClaw(lambda: GW.workspace_dir(t_id))
    monkeypatch.setattr(GW, "TRANSPORT", httpx.MockTransport(claw))
    return GW, S, claw


def test_her_inputs_become_openclaw_act_requests():
    from app.dod import gateway as GW
    acts = GW.operator_actions([{"kind": "click", "x": 0.5, "y": 0.25}, {"kind": "text", "text": "a b+"},
                                {"kind": "key", "key": "Enter"}, {"kind": "key", "key": "Control+W"},
                                {"kind": "scroll", "dir": "up"}, {"kind": "eval", "fn": "x"}], 801, 401)
    assert acts == [{"kind": "clickCoords", "x": 400.0, "y": 100.0}, {"kind": "press", "key": "a"},
                    {"kind": "press", "key": "Space"}, {"kind": "press", "key": "b"}, {"kind": "press", "key": "+"},
                    {"kind": "press", "key": "Enter"}, {"kind": "press", "key": "PageUp"}], \
        "only clicks, the allowed keys, typed characters and page scrolls; no shortcuts, no scripts"


def test_she_takes_over_its_browser_and_says_done(on, caplog):
    GW, S, claw = on
    from fastapi.testclient import TestClient
    from app.main import app
    caplog.set_level(logging.DEBUG)
    with TestClient(app) as c:
        c.put("/api/dod/profile", json={"name": "Ananya", "look": "f002"})
        tid = c.post("/api/dod/tasks", json={"ask": "Open my Swiggy orders", "kind": "browser"}).json()["task"]["id"]
        t = _wait(c, tid, "needs_you")
        q = t["question"]
        assert q["kind"] == "browser" and q["question"] == "Please sign in to Swiggy"
        body0 = claw.bodies[0]
        ask = [x for x in body0["tools"] if x["name"] == "hoola_ask"][0]
        assert "browser" in ask["parameters"]["properties"]["kind"]["enum"] and "kind=browser" in body0["instructions"]
        # a yes / no does not answer a browser question
        assert c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": "yes"}).status_code == 409
        # her hands: a click on the picture, typing, a key - on this task's own tab, at the picture's scale
        r = c.post(f"/api/dod/tasks/{tid}/control", json={"inputs": [
            {"kind": "click", "x": 0.5, "y": 0.5}, {"kind": "text", "text": SECRET}, {"kind": "key", "key": "Enter"},
            {"kind": "key", "key": "Alt+F4"}, {"kind": "click", "x": 3, "y": 0}]})
        assert r.status_code == 200 and r.json()["sent"] == 2 + len(SECRET)
        batch = claw.acts[0]
        assert batch["kind"] == "batch" and batch["targetId"] == "t7"
        assert batch["actions"][0] == {"kind": "clickCoords", "x": 399.5, "y": 249.5}
        assert batch["actions"][-1] == {"kind": "press", "key": "Enter"}
        assert "".join(a["key"] if a["key"] != "Space" else " " for a in batch["actions"][1:-1]) == SECRET
        # what she typed is nowhere: not in the task, not in the log, not sent to the model
        t = c.get(f"/api/dod/tasks/{tid}").json()["task"]
        assert SECRET not in json.dumps(t) and "hunter2" not in caplog.text
        assert [s["title"] for s in t["steps"]].count("You took over its browser") == 1
        c.post(f"/api/dod/tasks/{tid}/control", json={"inputs": [{"kind": "scroll", "dir": "down"}]})
        assert [s["title"] for s in c.get(f"/api/dod/tasks/{tid}").json()["task"]["steps"]].count("You took over its browser") == 1
        assert c.get(f"/api/dod/tasks/{tid}/screen").headers["content-type"] == "image/jpeg"
        # Done hands the page back and the coworker carries on
        ok = c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": "done"})
        assert ok.status_code == 200
        t = _wait(c, tid, "done")
        back = claw.bodies[-1]["input"][0]["output"]
        assert "has done what the page needed" in back and "Look at the page again" in back
        assert all("hunter2" not in json.dumps(b) for b in claw.bodies)
        assert any(s.get("detail") == "Done in its browser" for s in t["steps"])
        # her hands are off once it no longer waits for her there
        assert c.post(f"/api/dod/tasks/{tid}/control", json={"inputs": [{"kind": "key", "key": "Enter"}]}).status_code == 409


def test_control_only_on_her_own_task_and_only_for_a_browser_question(on):
    GW, S, claw = on
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        c.put("/api/dod/profile", json={"name": "Ananya", "look": "f002"})
        assert c.post("/api/dod/tasks/nope/control", json={"inputs": [{"kind": "key", "key": "Enter"}]}).status_code == 404
        tid = c.post("/api/dod/tasks", json={"ask": "Open my Swiggy orders"}).json()["task"]["id"]
        _wait(c, tid, "needs_you")
        assert c.post(f"/api/dod/tasks/{tid}/control", json={"inputs": []}).status_code == 409
        assert c.post(f"/api/dod/tasks/{tid}/control", json={"inputs": [{"kind": "key", "key": "x"}] * 61}).status_code == 409
        # another user's task is not hers
        from app import db
        from app.dod.models import DodTask
        with db.session() as ss:
            ss.get(DodTask, tid).tenant_id = "someone-else"
            ss.commit()
        assert c.post(f"/api/dod/tasks/{tid}/control", json={"inputs": [{"kind": "key", "key": "Enter"}]}).status_code == 404
        assert not claw.acts


def test_the_notification_and_the_page_say_it():
    from app import push
    title, body = push.render("dod_ask", {"name": "Ananya", "kind": "browser", "question": "Please sign in to Swiggy"})
    assert title == "Ananya needs you in its browser" and "Swiggy" in body
    js = (BASE / "dod.js").read_text()
    css = (BASE / "dod.css").read_text()
    for s in ("data-take=", "/control`", "Done, carry on", "Needs you in its browser", "Hoola keeps none of it",
              "kind: 'click'", "kind: 'text'", "data-scroll"):
        assert s in js, s
    assert ".dd-ctl{" in css and "prefers-reduced-motion" in css


@pytest.fixture
def brt(on, monkeypatch):
    GW, S, claw = on
    sync_api = pytest.importorskip("playwright.sync_api")
    import threading
    import time
    import uvicorn
    from app import main
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    try:
        pw = sync_api.sync_playwright().start()
        try:
            b = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        yield f"http://127.0.0.1:{port}/console/dod", b, KEY, claw
        b.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_take_control_in_a_real_browser(brt):
    base, b, key, claw = brt
    for w, h in ((1440, 900), (390, 844)):
        ctx = b.new_context(viewport={"width": w, "height": h})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        p = ctx.new_page()
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.goto(base)
        import httpx as _h
        hdr = {"Authorization": f"Bearer {key}"}
        api = base.replace("/console/dod", "")
        _h.put(f"{api}/api/dod/profile", json={"name": "Ananya", "look": "f002"}, headers=hdr)
        tid = _h.post(f"{api}/api/dod/tasks", json={"ask": "Open my Swiggy orders", "kind": "browser"}, headers=hdr).json()["task"]["id"]
        p.goto(f"{base}#/t/{tid}")
        p.wait_for_selector("#tQ [data-take]", timeout=20000)
        assert "Needs you in its browser" in p.inner_text("#tQ")
        p.click("#tQ [data-take]")
        p.wait_for_selector(".dd-ctl #ctlImg:not([hidden])", timeout=15000)
        assert p.locator(".dd-ctl").count() == 1
        n = len(claw.acts)
        p.click("#ctlImg", position={"x": 10, "y": 10})
        p.wait_for_function(f"() => true", timeout=1000)
        p.fill("#ctlText", "98")
        p.click("#ctlForm button[type=submit]")
        p.click("[data-key='Tab']")
        for _ in range(60):
            if len(claw.acts) >= n + 3:
                break
            p.wait_for_timeout(100)
        sent = claw.acts[n:]
        assert sent[0]["kind"] == "clickCoords" and sent[0]["x"] < 40 and sent[0]["y"] < 40
        assert any(a.get("kind") == "batch" or a.get("key") == "9" for a in sent[1:]) and sent[-1] == {"kind": "press", "key": "Tab", "targetId": "t7"}
        assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"sideways scroll at {w}"
        if os.environ.get("HOOLA_SHOTS"):
            p.screenshot(path=f"{os.environ['HOOLA_SHOTS']}/dod_takeover_{w}.png")
        p.click("[data-ctl='done']")
        p.wait_for_selector(".dd-reply", timeout=15000)
        assert p.locator(".dd-ctl").count() == 0 and "Signed in." in p.inner_text(".dd-reply")
        assert not errs, errs
        ctx.close()
