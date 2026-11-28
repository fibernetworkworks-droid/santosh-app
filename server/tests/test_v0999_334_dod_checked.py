"""v0.999.334 HOOLA DOD, "DONE" MEANS CHECKED (owner, after the kwant read: '"Done" means checked ... work on it').

When the coworker says it is done, Hoola runs the task's checks itself: files (Hoola's own copy from the hand-over),
public web addresses, text on its page, and commands in a fresh locked box (workspace read-only, no network). Her checks
count at once; the coworker's own checks wait for her approval. A reviewer on another model goes through her request
part by part; it can stop a Pass but never make one. A failed check sends the work back (twice), then it waits for her
look. A fake OpenClaw, a fake web and a fake docker stand in for the real ones.
"""
import asyncio
import json
import os

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0999_306_dod import BASE, _call, _sse, _wait, dod  # noqa: F401


def _resp(n, out):
    resp = {"id": f"resp_{n}", "status": "completed", "output": out}
    return httpx.Response(200, headers={"content-type": "text/event-stream"},
                          content=_sse([{"type": "response.completed", "response": resp}]))


class CheckedClaw:
    """Round 1: a wrong receipt + a suggested web check + done. Sent back -> round 2: the right receipt + done."""

    def __init__(self, ws):
        self.ws, self.bodies, self.n, self.keys = ws, [], 0, 0

    def __call__(self, req: httpx.Request):
        if req.url.host == "openrouter.ai":
            if req.method == "POST":
                self.keys += 1
                return httpx.Response(201, json={"key": "sk-or-user-1", "data": {"hash": "h1"}})
            return httpx.Response(200, json={"data": {"usage": 0.5, "limit": 10}})
        if req.url.path == "/readyz":
            return httpx.Response(200, json={"ready": True})
        body = json.loads(req.content)
        self.bodies.append(body)
        self.n += 1
        first = body["input"][0]
        by = {i.get("call_id"): i for i in body["input"] if i.get("call_id")}
        ws = self.ws()
        ws.mkdir(parents=True, exist_ok=True)
        if first.get("type") == "message" and str(first.get("content")).startswith("Not done yet"):
            return _resp(self.n, [{"type": "message", "content": [{"type": "output_text", "text": "I could not fix it."}]}])
        if first.get("type") == "message" and "sent it back" not in str(first.get("content")):
            (ws / "receipt.txt").write_text("Order 4471 - INR 500")
            return _resp(self.n, [
                _call("hoola_deliver", {"path": "receipt.txt", "title": "Receipt"}, "d1"),
                _call("hoola_check", {"kind": "web", "url": "https://shop.example.com/order/4471", "text": "Confirmed",
                                      "why": "the order page says it is confirmed"}, "k1"),
                _call("hoola_check", {"kind": "file_exists", "path": "../../etc/passwd", "why": "x"}, "k2"),
                _call("hoola_done", {"summary": "Ordered. Paid INR 549."}, "f1")])
        if "f1" in by:
            first = by["f1"]
            assert "Not done yet" in first["output"] and "does not contain" in first["output"]
            (ws / "receipt.txt").write_text("Order 4471 - INR 549")
            return _resp(self.n, [_call("hoola_deliver", {"path": "receipt.txt", "title": "Receipt"}, "d2"),
                                  _call("hoola_done", {"summary": "Fixed. Paid INR 549."}, "f2")])
        if "f2" in by or "sent it back" in str(first.get("content") or first.get("output")):
            return _resp(self.n, [_call("hoola_done", {"summary": "Done again."}, "f3")])
        return _resp(self.n, [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}])


@pytest.fixture
def on(dod, monkeypatch):
    GW, S, docker = dod
    monkeypatch.setenv("DOD_ENGINE", "true")
    monkeypatch.setenv("OPENROUTER_PROVISIONING_KEY", "prov-key")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.dod import checks as CK
    t_id = get_settings().tenant_id
    claw = CheckedClaw(lambda: GW.workspace_dir(t_id))
    monkeypatch.setattr(GW, "TRANSPORT", httpx.MockTransport(claw))
    reviews = []

    async def fake_review(model, msg):
        reviews.append((model, msg))
        return json.dumps({"parts": [{"part": "Order the dinner", "result": "passed", "why": "The receipt shows it."},
                                     {"part": "Pay INR 549", "result": "passed", "why": "The receipt says INR 549."}]})

    monkeypatch.setattr(CK, "REVIEW", fake_review)

    def web(req):
        if req.url.host == "shop.example.com":
            return httpx.Response(200, text="<h1>Order 4471</h1><p>Confirmed</p>")
        return httpx.Response(404)

    monkeypatch.setattr(CK, "TRANSPORT", httpx.MockTransport(web))
    monkeypatch.setattr("app.agent.scrape_tools._guard_url",
                        lambda u: u if "example.com" in u else (_ for _ in ()).throw(ValueError("private address")))
    return GW, S, CK, claw, reviews


def test_a_check_is_what_she_or_it_described():
    from app.dod import checks as CK
    assert CK.normalize({"kind": "file_contains", "path": "/home/node/.openclaw/workspace/out/a.csv", "text": " a  b "}) == \
        {"kind": "file_contains", "path": "out/a.csv", "text": "a b"}
    assert CK.normalize({"kind": "web", "url": "https://x.example.com", "status": "201"})["code"] == 201
    for bad in ({"kind": "file_exists", "path": "../x"}, {"kind": "file_exists", "path": "/etc/passwd"},
                {"kind": "web", "url": "ftp://x"}, {"kind": "page"}, {"kind": "command", "command": "x" * 700},
                {"kind": "exec", "command": "ls"}, {"kind": "web", "url": "https://x", "code": 99}):
        with pytest.raises(ValueError):
            CK.normalize(bad)
    mine, its = CK.new({"kind": "page", "text": "Paid"}, "you"), CK.new({"kind": "page", "text": "Paid"}, "coworker")
    assert mine["approved"] and mine["status"] == "pending"
    assert not its["approved"] and its["status"] == "needs_approval", "its own check never counts without her"
    assert CK.review_model().split("/")[0] != "anthropic", "the reviewer is never the coworker's company"


def test_done_means_checked_end_to_end(on):
    GW, S, CK, claw, reviews = on
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        c.put("/api/dod/profile", json={"name": "Ananya", "look": "f002"})
        tid = c.post("/api/dod/tasks", json={"ask": "Order dinner and pay INR 549", "checks": [
            {"kind": "file_contains", "path": "receipt.txt", "text": "INR 549"}]}).json()["task"]["id"]
        t = _wait(c, tid, "review", 20)
        # round 1: her check failed on the wrong receipt -> the work went back; round 2 passed it
        titles = [s["title"] for s in t["steps"]]
        assert "A check failed, sent back" in titles and titles.count("Checking the work") == 2
        assert "Done again." not in t["reply"] and t["reply"] == "Fixed. Paid INR 549."
        ck = {x["kind"]: x for x in t["checks"]}
        assert ck["file_contains"]["status"] == "passed" and ck["file_contains"]["by"] == "you"
        assert ck["web"]["status"] == "needs_approval" and ck["web"]["by"] == "coworker" and not ck["web"]["approved"]
        assert len(t["checks"]) == 2, "a check outside its workspace is refused, not added"
        assert t["verdict"] == "needs_you", "its own check waits for her: no Pass on its word"
        assert [p["result"] for p in t["review"]["parts"]] == ["passed", "passed"] and t["review"]["model"]
        assert any("runs once you approve it" in x["why"] for x in t["review"]["couldnt"])
        assert reviews and "a claim" in reviews[-1][1] and "INR 549" in reviews[-1][1]
        # she approves its check -> Hoola runs it itself -> passed -> done
        t = c.post(f"/api/dod/tasks/{tid}/checks/{ck['web']['id']}/approve").json()["task"]
        assert t["status"] == "done" and t["verdict"] == "passed"
        assert {x["kind"]: x["status"] for x in t["checks"]} == {"file_contains": "passed", "web": "passed"}
        assert "Confirmed" in [x for x in t["checks"] if x["kind"] == "web"][0]["result"]
        assert c.post(f"/api/dod/tasks/{tid}/checks/{ck['web']['id']}/approve").status_code == 409
        # her own check on finished work runs at once
        t = c.post(f"/api/dod/tasks/{tid}/checks", json={"kind": "file_contains", "path": "receipt.txt", "text": "INR 9999"}).json()["task"]
        assert t["verdict"] == "failed" and t["status"] == "review"
        # she sends it back: the coworker continues from its done call with her words
        t = c.post(f"/api/dod/tasks/{tid}/sendback", json={"note": "The receipt must say INR 9999"}).json()["task"]
        assert t["status"] in ("working", "checking", "review")
        t = _wait(c, tid, "review", 20)
        sent = [i for b in claw.bodies for i in b["input"] if i.get("call_id") == "f2"][-1]["output"]
        assert "sent it back: The receipt must say INR 9999" in sent
        assert "You sent it back" in [s["title"] for s in t["steps"]]
        # Looks good: done, the verdict stays, her OK is written down
        t = c.post(f"/api/dod/tasks/{tid}/accept").json()["task"]
        assert t["status"] == "done" and t["verdict"] == "failed" and t["review"]["accepted"]
        assert c.post(f"/api/dod/tasks/{tid}/accept").status_code == 409
        st = c.get("/api/dod/status").json()["summary"]
        assert "to_review" in st and "checked_week" in st


def test_command_checks_run_in_a_locked_box(on, monkeypatch):
    GW, S, CK, claw, reviews = on
    from app.config import get_settings
    ran = []

    async def box(*args, timeout=0):
        ran.append(list(args))
        if args[0] == "rm":
            return 0, ""
        cmd = args[-1]
        return {"pytest -q": (0, "3 passed"), "exit 1": (1, "boom"), "sleep 999": (124, "")}[cmd]

    monkeypatch.setattr(CK, "DOCKER", box)
    t_id = get_settings().tenant_id
    GW.workspace_dir(t_id).mkdir(parents=True, exist_ok=True)
    ok = asyncio.run(CK.run_one(t_id, "t1", [], CK.new({"kind": "command", "command": "pytest -q"}, "you")))
    assert ok[0] == "passed" and "3 passed" in ok[1]
    a = ran[0]
    assert a[0] == "run" and "--rm" in a and a[a.index("--network") + 1] == "none" and "--read-only" in a
    assert a[a.index("-v") + 1].endswith(":/work:ro"), "her workspace is mounted read-only"
    assert a[a.index("--user") + 1] == "1000:1000" and "no-new-privileges" in a and a[-3] == get_settings().dod_image
    assert asyncio.run(CK.run_one(t_id, "t1", [], CK.new({"kind": "command", "command": "exit 1"}, "you")))[0] == "failed"
    late = asyncio.run(CK.run_one(t_id, "t1", [], CK.new({"kind": "command", "command": "sleep 999"}, "you")))
    assert late == ("failed", "It ran past its time limit.") and ran[-1][:2] == ["rm", "-f"]


def test_web_and_page_checks(on, monkeypatch):
    GW, S, CK, claw, reviews = on
    from app.agent import scrape_tools
    monkeypatch.setattr(scrape_tools, "_guard_url", lambda u: (_ for _ in ()).throw(ValueError("private")) if "10.0.0.1" in u else u)

    def web(req):
        if req.url.host == "a.example.com":
            return httpx.Response(302, headers={"location": "http://10.0.0.1/admin"})
        if req.url.host == "b.example.com":
            return httpx.Response(500)
        return httpx.Response(200, text="Hello world")

    monkeypatch.setattr(CK, "TRANSPORT", httpx.MockTransport(web))
    run = lambda spec: asyncio.run(CK.run_one("x", "t1", [], CK.new(spec, "you")))   # noqa: E731
    assert run({"kind": "web", "url": "https://a.example.com/"})[0] == "error", "a redirect to a private address is refused"
    assert run({"kind": "web", "url": "https://b.example.com/"})[0] == "failed"
    assert run({"kind": "web", "url": "https://c.example.com/", "text": "hello WORLD"})[0] == "passed"
    assert run({"kind": "web", "url": "https://c.example.com/", "text": "bye"})[0] == "failed"

    async def page(tenant, key):
        return "Your order is CONFIRMED" if key == "hoola-dod-t1" else None

    monkeypatch.setattr(GW, "page_text", page)
    assert run({"kind": "page", "text": "order is confirmed"})[0] == "passed"
    assert asyncio.run(CK.run_one("x", "t2", [], CK.new({"kind": "page", "text": "x"}, "you")))[0] == "error"


def test_a_check_that_cannot_run_is_never_a_pass_and_no_checks_says_so(on, monkeypatch):
    GW, S, CK, claw, reviews = on

    async def silent(model, msg):
        raise RuntimeError("down")

    monkeypatch.setattr(CK, "REVIEW", silent)
    res = asyncio.run(CK.verify("x", "t9", "Do it", "Done", [], [], [CK.new({"kind": "page", "text": "x"}, "you")]))
    assert res["verdict"] == "not_checked" and res["checks"][0]["status"] == "error"
    whats = [x["what"] for x in res["couldnt"]]
    assert "Its page shows \"x\"" in whats and "A second look by another AI" in whats
    res = asyncio.run(CK.verify("x", "t9", "Do it", "Done", [], [], []))
    assert res["verdict"] == "not_checked"

    async def not_met(model, msg):
        return '{"parts": [{"part": "Send the file to Ravi", "result": "not_met", "why": "Nothing was sent."}]}'

    monkeypatch.setattr(CK, "REVIEW", not_met)
    GW.workspace_dir("x").mkdir(parents=True, exist_ok=True)
    (GW.workspace_dir("x") / "a.txt").write_text("hi")
    res = asyncio.run(CK.verify("x", "t9", "Make a.txt and send it to Ravi", "Done", [], [],
                                [CK.new({"kind": "file_exists", "path": "a.txt"}, "you")]))
    assert res["checks"][0]["status"] == "passed" and res["verdict"] == "needs_you", "the reviewer can stop a Pass"


def test_the_page_and_its_wiring():
    js = (BASE / "dod.js").read_text()
    css = (BASE / "dod.css").read_text()
    for s in ("checksBox", "Done, not checked", "Couldn't check", "Looks good", "Send back", "Add a check",
              "/checks/${enc(b.dataset.cid)}/", "/recheck`", "/sendback`", "To review", "Waiting for your OK"):
        assert s in js, s
    assert ".dd-verdict" in css and ".dd-ck{" in css
    from app.dod import service as S
    names = [x["name"] for x in S.TOOLS]
    assert "hoola_check" in names and "Hoola checks your work itself" in S.instructions("Ananya", "task")


@pytest.fixture
def brc(on, monkeypatch):
    GW, S, CK, claw, reviews = on
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
        yield f"http://127.0.0.1:{port}/console/dod", b, KEY
        b.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_checked_done_in_a_real_browser(brc):
    base, b, key = brc
    api = base.replace("/console/dod", "")
    hdr = {"Authorization": f"Bearer {key}"}
    httpx.put(f"{api}/api/dod/profile", json={"name": "Ananya", "look": "f002"}, headers=hdr)
    for w, h in ((1440, 900), (390, 844)):
        tid = httpx.post(f"{api}/api/dod/tasks", json={"ask": "Order dinner and pay INR 549", "checks": [
            {"kind": "file_contains", "path": "receipt.txt", "text": "INR 549"}]}, headers=hdr).json()["task"]["id"]
        ctx = b.new_context(viewport={"width": w, "height": h})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        p = ctx.new_page()
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.goto(f"{base}#/t/{tid}")
        p.wait_for_selector("#tChecks [data-ck='approve']", timeout=30000)
        txt = p.inner_text("#tChecks").lower()   # headings are drawn in capitals
        for want in ("needs you", "passed", "waiting for your ok", "couldn't check", "ananya suggested", "order the dinner"):
            assert want in txt, want
        assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"sideways scroll at {w}"
        if os.environ.get("HOOLA_SHOTS"):
            p.screenshot(path=f"{os.environ['HOOLA_SHOTS']}/dod_checks_{w}.png", full_page=True)
        p.click("#tChecks [data-ck='approve']")
        p.wait_for_selector("#tChecks .dd-verdict.ok", timeout=15000)
        assert "Checked: passed" in p.inner_text("#tChecks")
        p.click("#tChecks summary")
        p.select_option("#ckKind", "web")
        assert p.is_visible("#ckUrl") and not p.is_visible("#ckPath")
        assert not errs, errs
        ctx.close()
