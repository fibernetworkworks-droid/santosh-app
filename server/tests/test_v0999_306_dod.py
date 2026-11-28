"""v0.999.306 HOOLA DOD - her coworker on her own OpenClaw Gateway (owner: "BUILD HOOLA DOD" after the design canvas).

A fake OpenClaw Gateway (the documented /v1/responses SSE stream + /readyz) and a fake OpenRouter provisioning API stand
in for the real ones; docker is a recorder. One task goes end to end: steps, her note read at the next step, a payment
question that waits for HER tap (bound to its hash), a file handed over, the result. Plus: the coworker profile with
the 200 looks, the engine staying off until the owner switches it on, isolation between users, Stop, and the page.
"""
import json
import os
import threading
import time
from pathlib import Path

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401

BASE = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _sse(events):
    out = []
    for e in events:
        out.append(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n")
    out.append("data: [DONE]\n\n")
    return "".join(out).encode()


def _call(name, args, cid):
    return {"type": "function_call", "name": name, "call_id": cid, "arguments": json.dumps(args)}


class FakeClaw:
    """OpenClaw's documented surface, just enough: POST /v1/responses (stream), GET /readyz; and OpenRouter keys."""

    def __init__(self, workspace_of):
        self.bodies, self.headers, self.n = [], [], 0
        self.workspace_of = workspace_of
        self.keys = 0

    def __call__(self, req: httpx.Request):
        if req.url.host == "openrouter.ai":
            if req.method == "POST" and req.url.path.endswith("/keys"):
                self.keys += 1
                assert req.headers["authorization"] == "Bearer prov-key"
                return httpx.Response(201, json={"key": f"sk-or-user-{self.keys}", "data": {"hash": f"h{self.keys}"}})
            return httpx.Response(200, json={"data": {"usage": 1.25, "limit": 10}})
        if req.url.path == "/readyz":
            return httpx.Response(200, json={"ready": True})
        assert req.url.path == "/v1/responses"
        body = json.loads(req.content)
        self.bodies.append(body)
        self.headers.append(dict(req.headers))
        self.n += 1
        items = body["input"]
        first = items[0]
        if first.get("type") == "message":
            out = [_call("hoola_step", {"title": "Opening the restaurant's website", "detail": "Baner branch"}, "c1")]
        elif first.get("call_id") == "c1":
            out = [_call("hoola_step", {"title": "Adding Penne Arrabbiata to the cart"}, "c2")]
        elif first.get("call_id") == "c2":
            out = [_call("hoola_ask", {"question": "Pay for the order?", "kind": "pay", "amount": 549, "currency": "INR",
                                       "details": "2 items, delivery at 8:30"}, "c3")]
        elif first.get("call_id") == "c3":
            ws = self.workspace_of()
            ws.mkdir(parents=True, exist_ok=True)
            (ws / "receipt.txt").write_text("Order 4471 - INR 549")
            out = [_call("hoola_deliver", {"path": "receipt.txt", "title": "Your receipt"}, "c4"),
                   _call("hoola_done", {"summary": "Ordered. Arrives at 8:30. Paid INR 549."}, "c5")]
        else:
            out = [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}]
        resp = {"id": f"resp_{self.n}", "status": "completed", "output": out}
        events = [{"type": "response.created", "response": {"id": resp["id"]}},
                  {"type": "response.output_text.delta", "delta": "Working on it. "},
                  {"type": "response.completed", "response": resp}]
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=_sse(events))


@pytest.fixture
def dod(bz, monkeypatch, tmp_path):
    monkeypatch.setenv("DOD_DATA_DIR", str(tmp_path / "dod"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app.dod import gateway as GW, service as S
    S._RUNS.clear(); S._WAKE.clear(); S._ANSWERS.clear()
    S._RECOVERED = True
    docker = []

    async def fake_docker(*args, timeout=0):
        docker.append(list(args))
        return (1, "No such container") if args[0] == "start" else (0, "ok")

    monkeypatch.setattr(GW, "DOCKER", fake_docker)
    yield GW, S, docker
    monkeypatch.setattr(GW, "TRANSPORT", None)


def _wait(c, tid, status, secs=10):
    end = time.time() + secs
    while time.time() < end:
        t = c.get(f"/api/dod/tasks/{tid}").json()["task"]
        if t["status"] == status:
            return t
        time.sleep(0.05)
    raise AssertionError(f"task stayed {t['status']}, wanted {status}: {t}")


def test_the_coworker_profile_and_the_200_looks(dod):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        looks = c.get("/api/dod/looks").json()["looks"]
        assert len(looks) == 200 and {l["gender"] for l in looks} == {"f", "m"}
        assert c.get(looks[1]["head"]).headers["content-type"] == "image/webp"
        assert c.get("/api/dod/look/../../main.py").status_code == 404 and c.get("/api/dod/look/x999.webp").status_code == 404
        st = c.get("/api/dod/status").json()
        assert st["profile"] is None and st["engine"]["ok"] is False and "admin" not in st["engine"]
        assert c.post("/api/dod/tasks", json={"ask": "Order dinner"}).status_code == 400   # meet the coworker first
        assert c.put("/api/dod/profile", json={"name": "Police Station", "look": "f002"}).status_code == 400
        assert c.put("/api/dod/profile", json={"name": "Ananya", "look": "z001"}).status_code == 400
        p = c.put("/api/dod/profile", json={"name": "Ananya", "look": "f002", "voice": "calm"}).json()["profile"]
        assert p["name"] == "Ananya" and p["head"].endswith("f002_head.webp") and p["voice"] == "calm"
        # the main Hoola avatar is not touched by the coworker
        from app import db
        from app.avatar.models import Avatar
        with db.session() as ss:
            assert ss.query(Avatar).count() == 0


def test_engine_off_says_so_plainly(dod):
    GW, S, docker = dod
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        c.put("/api/dod/profile", json={"name": "Ananya", "look": "f002"})
        tid = c.post("/api/dod/tasks", json={"ask": "Order dinner for two"}).json()["task"]["id"]
        t = _wait(c, tid, "failed")
        assert "not switched on" in t["error"] and docker == [], "nothing starts while the owner has not switched it on"


def test_a_whole_task_with_her_yes(dod, monkeypatch, tmp_path):
    GW, S, docker = dod
    monkeypatch.setenv("DOD_ENGINE", "true")
    monkeypatch.setenv("OPENROUTER_PROVISIONING_KEY", "prov-key")
    from app.config import get_settings
    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app.main import app
    t_id = get_settings().tenant_id
    claw = FakeClaw(lambda: GW.workspace_dir(t_id))
    monkeypatch.setattr(GW, "TRANSPORT", httpx.MockTransport(claw))
    with TestClient(app) as c:
        c.put("/api/dod/profile", json={"name": "Ananya", "look": "f002"})
        tid = c.post("/api/dod/tasks", json={"ask": "Order Penne Arrabbiata for 8:30", "kind": "browser"}).json()["task"]["id"]
        t = _wait(c, tid, "needs_you")
        q = t["question"]
        assert q["kind"] == "pay" and q["amount"] == 549 and q["currency"] == "INR" and q["hash"]
        titles = [s["title"] for s in t["steps"]]
        assert "Opening the restaurant's website" in titles and "Asked you" in titles
        # her yes is bound to the question she saw
        bad = c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": "0" * 16, "choice": "yes"})
        assert bad.status_code == 409
        assert c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": "maybe"}).status_code == 409
        ok = c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": "yes"})
        assert ok.status_code == 200
        t = _wait(c, tid, "done")
        assert t["reply"].startswith("Ordered.") and t["files"] == [{"name": "receipt.txt", "size": 20, "title": "Your receipt"}]
        assert c.get(f"/api/dod/tasks/{tid}/files/receipt.txt").content == b"Order 4471 - INR 549"
        assert c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": "yes"}).status_code == 409
        # what OpenClaw was sent: Hoola's tools, the rules, one session per task, continuation by response id
        b0 = claw.bodies[0]
        assert {x["name"] for x in b0["tools"]} == {"hoola_step", "hoola_ask", "hoola_deliver", "hoola_done"}
        assert "Ananya" in b0["instructions"] and "Never type card numbers" in b0["instructions"] and b0["stream"] is True
        assert claw.headers[0]["x-openclaw-session-key"] == f"hoola-dod-{tid}" and claw.headers[0]["authorization"].startswith("Bearer ")
        assert claw.bodies[1]["previous_response_id"] == "resp_1"
        paid = [b for b in claw.bodies if b["input"][0].get("call_id") == "c3"][0]["input"][0]["output"]
        assert "APPROVED" in paid and "never type card numbers" in paid
        # her own container: the official image, 127.0.0.1 only, memory capped, her own network, no Control UI flags
        run = [a for a in docker if a[0] == "run"][0]
        assert run[-1] == get_settings().dod_image and "127.0.0.1:" in run[run.index("-p") + 1]
        assert run[run.index("--memory") + 1] == "2g" and run[run.index("--network") + 1] == GW.network_name(t_id)
        assert "OPENCLAW_NO_AUTO_UPDATE=1" in run and "DO_NOT_TRACK=1" in run
        cfg = json.loads((GW.state_dir(t_id) / "openclaw.json").read_text())
        assert cfg["gateway"]["http"]["endpoints"]["responses"]["enabled"] is True
        assert cfg["env"]["vars"]["OPENROUTER_API_KEY"] == "sk-or-user-1", "her own limited key, never the server's"
        assert oct((GW.state_dir(t_id) / "openclaw.json").stat().st_mode)[-3:] == "600"
        st = c.get("/api/dod/status").json()
        assert st["engine"]["ok"] and st["spent"] == {"usage": 1.25, "limit": 10} and st["summary"]["done_week"] == 1
        # a second task reuses her awake Gateway and her key
        tid2 = c.post("/api/dod/tasks", json={"ask": "Order Penne Arrabbiata again"}).json()["task"]["id"]
        _wait(c, tid2, "needs_you")
        assert claw.keys == 1 and len([a for a in docker if a[0] == "run"]) == 1
        c.post(f"/api/dod/tasks/{tid2}/stop")
        assert c.get(f"/api/dod/tasks/{tid2}").json()["task"]["status"] == "stopped"


def test_her_note_reaches_the_next_step_and_users_are_apart(dod, monkeypatch):
    GW, S, docker = dod
    monkeypatch.setenv("DOD_ENGINE", "true")
    monkeypatch.setenv("OPENROUTER_PROVISIONING_KEY", "prov-key")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.dod.models import DodTask
    from app import db
    t_id = get_settings().tenant_id
    claw = FakeClaw(lambda: GW.workspace_dir(t_id))
    monkeypatch.setattr(GW, "TRANSPORT", httpx.MockTransport(claw))
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        c.put("/api/dod/profile", json={"name": "Ananya", "look": "f002"})
        tid = c.post("/api/dod/tasks", json={"ask": "Order Penne"}).json()["task"]["id"]
        _wait(c, tid, "needs_you")
        # a note is queued and read back to the coworker with the next hoola_step answer
        with db.session() as ss:
            ss.get(DodTask, tid).status = "working"
            ss.commit()
        c.post(f"/api/dod/tasks/{tid}/note", json={"text": "Make it extra spicy"})
        assert S._take_notes(tid) == "ok. New words from the owner: Make it extra spicy" and S._take_notes(tid) == "ok"
        with db.session() as ss:
            other = DodTask(tenant_id="someone-else", title="hers", ask="hers", status="done")
            ss.add(other)
            ss.commit()
            oid = other.id
        assert c.get(f"/api/dod/tasks/{oid}").status_code == 404
        assert c.post(f"/api/dod/tasks/{oid}/stop").status_code == 404
        assert all(t["id"] != oid for t in c.get("/api/dod/tasks").json()["tasks"])
        assert GW.container_name("a") != GW.container_name("b") and GW.state_dir("a") != GW.state_dir("b")


def test_the_page_and_its_wiring():
    js, css, html = (BASE / "dod.js").read_text(), (BASE / "dod.css").read_text(), (BASE / "dod.html").read_text()
    for part in ("Meet your coworker.", "What should ", "Working now", "Done today", "Give real work", "/api/dod/tasks",
                 "data-answer", "/answer", "/note", "/stop", "Tap again to stop", "speechSynthesis", "Never"):
        assert part in js, part
    for part in ("prefers-reduced-motion", "dd-breathe", "dd-shimmer", "dd-stripes", "dd-float", ":root[data-theme=\"dark\"]"):
        assert part in css, part
    assert "prompt(" not in js and "confirm(" not in js and "innerHTML = ex" not in js
    assert 'src="/static/console/dod.js' in html
    v2 = (BASE / "v2.js").read_text()
    assert "['dod', 'Hoola DOD']" in v2 and "location.assign('/console/dod'" in v2
    # nothing of Hoola PC, Hoola Code or the main avatar imports the coworker
    app_dir = BASE.parents[1]
    for f in ("pc/operator.py", "devsahayak/service.py", "avatar/service.py", "agent/santosh.py"):
        assert "dod" not in (app_dir / f).read_text().replace("dodo", ""), f


@pytest.fixture
def br(dod, monkeypatch):
    GW, S, docker = dod
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    monkeypatch.setenv("DOD_ENGINE", "true")
    monkeypatch.setenv("OPENROUTER_PROVISIONING_KEY", "prov-key")
    from app.config import get_settings
    get_settings.cache_clear()
    t_id = get_settings().tenant_id
    monkeypatch.setattr(GW, "TRANSPORT", httpx.MockTransport(FakeClaw(lambda: GW.workspace_dir(t_id))))
    import uvicorn
    from app import main
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
        yield f"http://127.0.0.1:{port}/console/dod", b, KEY
        b.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_the_page_in_a_real_browser(br):
    base, b, key = br
    shots = os.environ.get("HOOLA_SHOTS")
    for w, h in ((1440, 900), (390, 844)):
        ctx = b.new_context(viewport={"width": w, "height": h})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        p = ctx.new_page()
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.goto(base)
        try:
            p.wait_for_selector(".dd-face" if w == 1440 else "#main", timeout=20000)
        except Exception:
            raise AssertionError(p.inner_text("body")[:600] + " | " + str(errs))
        if w == 1440:
            # first time: meet the coworker
            assert "Meet your coworker." in p.inner_text("#main") and p.locator(".dd-face").count() == 100
            p.click("[data-g='m']")
            p.click(".dd-face >> nth=3")
            p.click("[data-g='f']")
            p.click(".dd-face >> nth=1")
            assert p.input_value("#nm") == "Ananya" and "Ananya" in p.inner_text("#startBtn")
            p.fill("#nm", "Police")
            p.click("#startBtn")
            p.wait_for_selector("#nmErr:not([hidden])")
            p.fill("#nm", "Ananya")
            if shots:
                p.screenshot(path=f"{shots}/dod_setup.png", full_page=True)
            p.click("#startBtn")
        else:
            p.goto(base + "#/")
        p.wait_for_selector("#ask")
        assert "What should Ananya do next?" in p.inner_text("#main") and p.locator(".dd-try button").count() == 4
        assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"sideways scroll at {w}"
        if w == 1440:
            p.click(".dd-try button >> nth=0")
            assert p.is_enabled("#sendBtn") and "Order dinner" in p.input_value("#ask")
            p.fill("#ask", "Order Penne Arrabbiata for 8:30")
            p.click("#sendBtn")
            p.wait_for_selector("#tQ [data-answer='yes']", timeout=15000)
            txt = p.inner_text("#main")
            assert "Opening the restaurant's website" in txt and "Approve INR 549" in txt
            p.click("#watchBtn")
            p.wait_for_selector("#tScreen >> text=No page open right now")
            assert p.inner_text("#watchBtn") == "Stop watching"
            if shots:
                p.screenshot(path=f"{shots}/dod_task.png", full_page=True)
            p.click("#tQ [data-answer='yes']")
            p.wait_for_selector(".dd-reply", timeout=15000)
            assert "Ordered." in p.inner_text(".dd-reply") and p.locator("[data-file='receipt.txt']").count() == 1
            p.goto(base + "#/")
            p.wait_for_selector("#doneList .it")
            if shots:
                p.wait_for_timeout(900)
                p.screenshot(path=f"{shots}/dod_home.png", full_page=True)
        elif shots:
            p.wait_for_timeout(900)
            p.screenshot(path=f"{shots}/dod_home_phone.png", full_page=True)
        assert not errs, errs
        ctx.close()


# ------------------------------------------------------------------ v0.999.307: what a real OpenClaw Gateway taught us + the pending work
def test_the_config_a_real_gateway_accepts():
    """Found by running the official image: it refuses to start without gateway.mode, refuses a state folder others can
    write to, and hides client / MCP tools behind its Tool Search unless they are excluded from it."""
    from app.dod.gateway import config_for
    c = config_for("tok", "sk-or-x", "openrouter/x", "mcp-tok", "http://172.18.0.1:8077/mcp/dod")
    assert c["gateway"]["mode"] == "local"
    ts = c["tools"]["toolSearch"]
    assert {"source": "client"} in ts["exclude"] and {"source": "mcp", "name": "hoola__*"} in ts["exclude"]
    srv = c["mcp"]["servers"]["hoola"]
    assert srv["transport"] == "streamable-http" and srv["headers"]["Authorization"] == "Bearer mcp-tok"
    assert "mcp" not in config_for("tok", "k", "m"), "no MCP entry without Hoola's address"


def test_her_state_folder_is_private(tmp_path):
    from app.dod.gateway import _own
    d = tmp_path / "state"
    (d / "workspace").mkdir(parents=True)
    (d / "openclaw.json").write_text("{}")
    d.chmod(0o777)
    (d / "dangling").symlink_to(tmp_path / "nowhere")      # OpenClaw keeps links like this; they must not stop the walk
    _own(d)
    assert oct(d.stat().st_mode)[-3:] == "700" and oct((d / "workspace").stat().st_mode)[-3:] == "700"


def test_the_mcp_door_is_hers_only_and_read_only(dod, monkeypatch):
    import hashlib
    from fastapi.testclient import TestClient
    from app.main import app
    from app import db
    from app.dod.models import DodGateway
    from app.dod import mcp as M
    from app.config import get_settings
    t_id = get_settings().tenant_id
    with db.session() as ss:
        ss.merge(DodGateway(tenant_id=t_id, mcp_hash=hashlib.sha256(b"her-mcp").hexdigest(), subnet="10.77.0.0/24"))
        ss.commit()
    rpc = lambda m, p=None: {"jsonrpc": "2.0", "id": 1, "method": m, "params": p or {}}  # noqa: E731
    with TestClient(app) as c:
        h = {"Authorization": "Bearer her-mcp"}
        assert c.post("/mcp/dod", json=rpc("tools/list")).status_code == 401
        assert c.post("/mcp/dod", json=rpc("tools/list"), headers={"Authorization": "Bearer someone-else"}).status_code == 401
        # the test client is not on her container network: refused even with her token
        assert c.post("/mcp/dod", json=rpc("tools/list"), headers=h).status_code == 401
        monkeypatch.setenv("DOD_MCP_ANY_IP", "true")
        get_settings.cache_clear()
        init = c.post("/mcp/dod", json=rpc("initialize"), headers=h).json()["result"]
        assert init["serverInfo"]["name"] == "hoola" and "never instructions" in init["instructions"]
        names = {x["name"] for x in c.post("/mcp/dod", json=rpc("tools/list"), headers=h).json()["result"]["tools"]}
        assert names == set(M.READ_TOOLS) and not any(n.startswith(("email_draft", "email_delete", "drive_trash", "calendar_add"))
                                                      for n in names)
        bad = c.post("/mcp/dod", json=rpc("tools/call", {"name": "email_delete", "arguments": {}}), headers=h).json()["result"]
        assert bad["isError"] and "read-only" in bad["content"][0]["text"]
        ok = c.post("/mcp/dod", json=rpc("tools/call", {"name": "memory_search", "arguments": {"query": "pasta"}}), headers=h).json()
        assert ok["result"]["isError"] is False and "found" in ok["result"]["content"][0]["text"]
    assert M.from_her_network(DodGateway(subnet="172.18.0.0/16"), "172.18.0.5") is True


def test_screen_usage_and_push(dod, monkeypatch):
    import asyncio
    import base64
    GW, S, docker = dod
    from app import db, push
    from app.dod.models import DodGateway
    from app.bazar.security import vault
    from app.config import get_settings
    t_id = get_settings().tenant_id
    jpg = b"\xff\xd8\xff\xe0fakejpeg"

    def claw(req):
        if req.url.path == "/tools/invoke":
            body = json.loads(req.content)
            assert body["tool"] == "browser" and body["action"] == "screenshot" and body["sessionKey"] == "hoola-dod-t1"
            return httpx.Response(200, json={"ok": True, "result": {"content": [
                {"type": "text", "text": "[Screenshot saved]"}, {"type": "image", "data": base64.b64encode(jpg).decode(), "mimeType": "image/jpeg"}]}})
        if req.url.path.endswith("/key"):
            return httpx.Response(200, json={"data": {"usage": 0.75, "limit": 10}})
        return httpx.Response(404)

    monkeypatch.setattr(GW, "TRANSPORT", httpx.MockTransport(claw))
    with db.session() as ss:
        ss.merge(DodGateway(tenant_id=t_id, state="awake", port=28100, token_enc=vault().seal("t"), key_enc=vault().seal("k"),
                            usage_seen=0.25))
        ss.commit()
    assert asyncio.run(GW.screenshot(t_id, "hoola-dod-t1")) == jpg
    noted = []
    from app.credits import wallet
    monkeypatch.setattr(wallet, "note", lambda t, usd, f="": noted.append((t, round(usd, 6), f)))
    monkeypatch.setattr(wallet, "flush", lambda: None)
    assert asyncio.run(GW.charge_usage(t_id)) == 0.5 and noted == [(t_id, 0.5, "dod")]
    assert asyncio.run(GW.charge_usage(t_id)) == 0.0, "the same usage is never charged twice"
    with db.session() as ss:
        ss.get(DodGateway, t_id).state = "asleep"
        ss.commit()
    assert asyncio.run(GW.screenshot(t_id, "hoola-dod-t1")) is None, "never wakes her coworker just to look"
    title, body = push.render("dod_ask", {"name": "Ananya", "kind": "pay", "question": "Pay INR 549 for the order?"})
    assert title == "Ananya needs your OK" and "549" in body and "dod_ask" in push.PUSH_KINDS
    assert push.render("dod_ask", {"name": "Ananya", "kind": "choice", "question": "Which size?"})[0] == "Ananya has a question"
