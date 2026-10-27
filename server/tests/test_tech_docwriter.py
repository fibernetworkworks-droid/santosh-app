"""Docs Sahayak (technical writer): rules (Diataxis kinds, safe step language, style guide, translation lock, privacy masks),
OpenAPI -> reference by code, her live site (ownership proof, real-Chromium screenshots with numbered highlights and solid masks,
password boxes never filled, other hosts refused), Hoola-built app as a source (screens, blueprint, existing screenshots),
docs tied to parts -> sync after a new version (stale found, drafts updated, her own edits kept), GitHub read-only (README,
OpenAPI, releases, merged PRs -> release notes), translation with locked labels, files, publishing ONLY on her tap
(page / GitHub pull request), worker tick, tools (owner / staff / customer) and API."""
import asyncio
import base64
import functools
import http.server
import json
import socketserver
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.docwriter.models  # noqa: F401  (tables for the env fixture's init_db)
import app.appmaker.models  # noqa: F401
from app.agent.tools import Ctx, ToolError
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def dw(env, monkeypatch, tmp_path):
    from app.docwriter import service as S
    events = []
    monkeypatch.setenv("DOCWRITER_DIR", str(tmp_path / "docwriter"))
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_ai", lambda system, prompt, max_tokens=2500: "")     # no model: code / template path
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def client():
    from app.docwriter.api import make_router
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: T))
    return TestClient(a)


# ---------------------------------------------------------------- rules
def test_rules():
    from app.docwriter import rules as R
    assert R.guess_kind("app ka quick start banao") == "quickstart" and R.guess_kind("API docs from openapi") == "api"
    assert R.guess_kind("naya kya hai is release mein") == "release_notes" and R.guess_kind("user manual") == "manual"
    st = R.validate_steps(['goto /orders', 'click "Save"', 'fill "Email" = demo@shop.in', 'press Enter', 'screenshot "Orders list."'],
                          "shop.example.in")
    assert [x["do"] for x in st] == ["goto", "click", "fill", "press", "screenshot"] and st[-1]["shot"] and st[2]["value"] == "demo@shop.in"
    for bad in ([{"do": "eval", "value": "alert(1)"}], [{"do": "goto", "url": "https://evil.example.com/"}],
                [{"do": "fill", "target": {"label": "OTP"}, "value": "482913"}],
                [{"do": "fill", "target": {"label": "Card"}, "value": "4111 1111 1111 1111"}],
                [{"do": "click", "target": {"css": "a[href^='javascript:x']"}}], [{"do": "press", "key": "Control+Shift+I"}]):
        with pytest.raises(R.StepError):
            R.validate_steps(bad, "shop.example.in")
    assert R.same_site("app.shop.example.in", "shop.example.in") and not R.same_site("shop.example.in.evil.com", "shop.example.in")
    md = "# T\n\n![](img/a.png)\n\nSimply click here to open it. Kindly wait.\n\nPrice: [blank]\n\n1. Tap **Save** and then tap **Done**."
    res = R.style_check(md, [{"term": "order", "avoid": "booking"}], "en")
    kb = {x["kind"] for x in res["blocking"]}
    assert {"blank", "alt"} <= kb
    kw = {x["kind"] for x in res["warnings"]}
    assert {"word", "step"} <= kw
    assert any(x["kind"] == "glossary" for x in R.style_check("Your booking is saved.", [{"term": "order", "avoid": "booking"}])["warnings"])
    locked, table = R.lock("Tap **Save** to keep order 1234 at https://x.in/a and run `npm i`.", ["Hoola"])
    assert "**Save**" not in locked and "1234" not in locked and "https" not in locked and "npm" not in locked
    back, lost = R.unlock(locked, table)
    assert back.startswith("Tap **Save**") and not lost
    assert R.unlock(locked.replace("⟦1⟧", ""), table)[1] == ["**Save**"]
    assert "[hataya]" in R.mask_text("call 98765 43210 or a@b.in") and "98765 43210" in R.mask_text("call 98765 43210", ["98765 43210"])


def test_openapi_reference_by_code():
    from app.docwriter import openapi as OA
    spec = {"openapi": "3.1.0", "info": {"title": "Shop API", "version": "2.0"}, "servers": [{"url": "https://api.shop.in/v2"}],
            "components": {"securitySchemes": {"key": {"type": "apiKey", "in": "header", "name": "X-Key"}},
                           "schemas": {"Order": {"type": "object", "required": ["item"], "properties": {
                               "item": {"type": "string", "description": "What to buy"}, "qty": {"type": "integer"}}}}},
            "security": [{"key": []}],
            "paths": {"/orders": {"get": {"summary": "List orders", "parameters": [{"name": "status", "in": "query",
                                                                                    "schema": {"type": "string", "enum": ["open", "done"]}}],
                                          "responses": {"200": {"description": "OK"}}},
                                  "post": {"summary": "Create order", "requestBody": {"required": True, "content": {
                                      "application/json": {"schema": {"$ref": "#/components/schemas/Order"}}}},
                                      "responses": {"201": {"description": "Created"}, "400": {"description": "Bad input"}}}}}}
    doc = OA.load(json.dumps(spec))
    ops = OA.operations(doc)
    assert [o["id"] for o in ops] == ["op:GET /orders", "op:POST /orders"] and ops[1]["body"]["fields"][0]["name"] == "item"
    md = OA.op_markdown(ops[1])
    assert "`POST /orders`" in md and "| `item` | string | yes | What to buy |" in md and "| 201 | Created |" in md and "key" in md
    assert "string (open, done)" in OA.op_markdown(ops[0])
    assert OA.info(doc)["servers"] == ["https://api.shop.in/v2"]
    sw = OA.load("swagger: '2.0'\ninfo: {title: X, version: '1'}\nhost: x.in\npaths:\n  /a:\n    post:\n      parameters:\n"
                 "        - {in: body, name: b, schema: {type: object, properties: {n: {type: string}}}}\n      responses: {200: {description: ok}}\n")
    assert OA.operations(sw)[0]["body"]["fields"][0]["name"] == "n"
    with pytest.raises(OA.OpenApiError):
        OA.load("{\"hello\": 1}")
    a, b = OA.operations(doc)[0]["hash"], OA.operations(OA.load(json.dumps({**spec, "paths": {"/orders": {**spec["paths"]["/orders"],
            "get": {**spec["paths"]["/orders"]["get"], "summary": "List all orders"}}}})))[0]["hash"]
    assert a != b


# ---------------------------------------------------------------- her live site in real Chromium
SITE = {
    "index.html": """<!doctype html><html><head><title>Kirana Hub</title>{meta}</head><body style="font-family:sans-serif">
<h1>Kirana Hub</h1><form onsubmit="event.preventDefault();location.href='orders.html'">
<label>Email <input name="email" type="email"></label><label>Password <input name="pw" type="password"></label>
<button type="submit">Sign in</button></form><a href="orders.html">Orders</a></body></html>""",
    "orders.html": """<!doctype html><html><head><title>Orders</title></head><body style="font-family:sans-serif">
<h1>Orders</h1><p>Ramesh Patil - ramesh.patil@gmail.com - 98765 43210</p><button>{btn}</button></body></html>""",
}


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture
def live_site(tmp_path):
    root = tmp_path / "site"
    root.mkdir()

    def write(meta="", btn="New order"):
        (root / "index.html").write_text(SITE["index.html"].replace("{meta}", meta))
        (root / "orders.html").write_text(SITE["orders.html"].replace("{btn}", btn))
    write()
    srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(root)))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/", write
    srv.shutdown()


def test_live_site_flow_screens_masks_and_sync(dw, live_site, monkeypatch):
    from app.docwriter import capture as CP
    if CP.available():
        pytest.skip("no playwright")
    S = dw
    monkeypatch.setattr(CP, "ALLOW_PRIVATE", True)
    url, write = live_site
    out = S.add_product(T, "web", url, "Kirana Hub")
    p = out["product"]
    assert not p["verified"] and "meta" in p["verify"]
    with pytest.raises(S.DocError):
        S.record_flow(T, p["id"], "Login", ['click "Orders"'])                  # not proved yet
    assert S.verify_product(T, p["id"])["verified"] is False
    write(meta=p["verify"]["meta"])
    v = S.verify_product(T, p["id"])
    assert v["verified"] and v["product"]["verify_how"] == "meta"
    with pytest.raises(S.DocError) as e:                                      # password value refused before a browser opens
        S.record_flow(T, p["id"], "Login", [{"do": "fill", "target": {"label": "Password"}, "value": "123456"}])
    assert "OTP" in str(e.value) or "PIN" in str(e.value)
    bad = S.record_flow(T, p["id"], "Login", [{"do": "fill", "target": {"label": "Password"}, "value": "demo-only"}])
    assert "password" in bad["flow"]["error"].lower()                         # the real box is a password box: never filled
    with pytest.raises(S.DocError):
        S.record_flow(T, p["id"], "x", ["goto https://example.org/"])
    steps = ['fill "Email" = demo@kirana.in', 'click "Orders"', {"do": "screenshot", "target": {"role": "button", "name": "New order"},
                                                                 "alt": "Orders screen with the New order button."}]
    r = S.record_flow(T, p["id"], "Order dekhna", steps)
    assert not r["flow"]["error"], r["flow"]["error"]
    shots = r["flow"]["shots"]
    assert len(shots) == 3 and all(x["box"] for x in shots)
    assert shots[-1]["masked"] >= 2 and shots[-1]["alt"] == "Orders screen with the New order button."
    assert shots[0]["alt"].startswith("Kirana Hub: In Email")
    from PIL import Image
    img = Image.open(S.flow_image(T, r["flow"]["id"], shots[-1]["file"]))
    assert img.width == 780                                                   # phone 390 px x2
    assert "docwriter_shots" in kinds(S)
    # docs from the flow (no model: steps written by code), screenshots copied
    q = S.write(T, p["id"], "quickstart", "en", words="pehli baar order dekhna")
    doc = q["doc"]
    sec = doc["section_list"][0]
    assert sec["part"].startswith("flow:") and "1. In **Email**, enter your details." in sec["body"] and len(sec["shots"]) == 3
    assert all(x["alt"] for x in sec["shots"])
    # the product changes -> sync re-shoots, finds the changed flow, redrafts the section; publish stays hers
    write(meta=p["verify"]["meta"], btn="Naya order")
    steps[-1] = {"do": "screenshot", "target": {"role": "button", "name": "Naya order"}, "alt": "Orders screen."}
    S.record_flow(T, p["id"], "Order dekhna", steps, flow=r["flow"]["id"])
    with pytest.raises(S.DocError):
        S.get(T, doc["id"]) and S.decide_publish(T, doc["id"], True, "x", by_tap=False)
    syn = S.sync(T, p["id"])
    d2 = S.get(T, doc["id"])
    assert d2["version"] == 2 and not d2["stale"] and syn["docs"] and "docwriter_sync" in kinds(S)


# ---------------------------------------------------------------- a Hoola-built app as the source
def _make_app(tenant, version=1, home_btn="Dukaan kholo"):
    from app.appmaker import kit as K
    from app.appmaker.models import AppProject
    from app.db import session
    with session() as s:
        a = s.query(AppProject).filter_by(tenant_id=tenant, number="A-0001").first()
        if a is None:
            a = AppProject(tenant_id=tenant, number="A-0001", name="Sharma Kirana", status="approved")
            s.add(a)
        a.version = version
        a.plan = json.dumps({"screens": ["home", "cart"], "tabs": ["home"], "flow": ["home", "cart"],
                             "labels": {"home": "Home", "cart": "Cart"}})
        s.flush()
        aid = a.id
    sd = K.src_dir(tenant, aid) / "screens"
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "home.json").write_text(json.dumps({"html": f"<section><h1>Sharma Kirana</h1><button>{home_btn}</button></section>", "css": "",
                                              "spec": {"purpose": "Shop ki main screen", "data": ["offers"],
                                                       "actions": [{"label": home_btn, "go": "cart"}]}}))
    (sd / "cart.json").write_text(json.dumps({"html": "<section><h1>Cart</h1><button>Order karo</button></section>", "css": "",
                                              "spec": {"purpose": "Saaman aur total", "actions": [{"label": "Order karo"}]}}))
    from PIL import Image
    shots = K.app_dir(tenant, aid) / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (780, 1688), (240, 240, 250)).save(shots / "home-android.jpg")
    return aid


def test_hoola_app_docs_sync_and_her_edits(dw, monkeypatch):
    S = dw
    aid = _make_app(T)
    p = S.add_product(T, "hoola_app", "A-0001")["product"]
    assert p["verified"] and p["verify_how"] == "hoola" and p["parts"] == 2 and p["version"] == "v1"
    calls = []

    def fake_ai(system, prompt, max_tokens=2500):
        calls.append(prompt)
        if "FACTS" in prompt and "Cart" in prompt:
            return json.dumps({"title": "Cart", "body": "Cart mein saaman dikhta hai. Delivery 30 minute mein. Daam: [blank]."})
        return json.dumps({"title": "Home", "body": "1. **Dukaan kholo** dabaiye."})
    monkeypatch.setattr(S, "_ai", fake_ai)
    out = S.write(T, "A-0001", "manual", "hinglish")
    d = out["doc"]
    assert [x["title"] for x in d["section_list"]] == ["Home", "Cart"] and len(d["section_list"][0]["shots"]) == 1
    assert "blank" in {x["kind"] for x in d["check_list"]["blocking"]}
    assert any(x["kind"] == "fact" and "30" in x["text"] for x in d["check_list"]["warnings"])     # '30 minute' is not in the app
    with pytest.raises(S.DocError):
        S.publish_request(T, d["id"], "page")                                   # [blank] blocks publishing
    cart = d["section_list"][1]["id"]
    S.edit(T, d["id"], cart, body="Cart mein saaman aur total dikhta hai. **Order karo** dabaiye.")
    assert S.get(T, d["id"])["status"] == "ready"
    # new app version: home button renamed, cart changed too; her edited cart section is kept (marked), home redrafted
    _make_app(T, version=2, home_btn="Shop kholo")
    from app.appmaker import kit as K
    sd = K.src_dir(T, aid) / "screens"
    c = json.loads((sd / "cart.json").read_text())
    c["html"] += "<p>Coupon</p>"
    (sd / "cart.json").write_text(json.dumps(c))
    monkeypatch.setattr(S, "_ai", lambda system, prompt, max_tokens=2500: json.dumps({"title": "Home", "body": "1. **Shop kholo** dabaiye."}))
    res = S.tick(datetime.now(timezone.utc) + timedelta(hours=2))
    assert res["synced"] == 1
    d2 = S.get(T, d["id"])
    home, cart2 = d2["section_list"]
    assert "Shop kholo" in home["body"] and not home["stale"]
    assert cart2["stale"] and "aapne khud likha" in cart2["why"] and "Order karo" in cart2["body"]
    assert S.tick(datetime.now(timezone.utc) + timedelta(hours=3))["synced"] == 0          # same version: nothing to do
    assert S.day(T)["stale"]


# ---------------------------------------------------------------- GitHub read-only + release notes + publish by tap
def _b64(s):
    return base64.b64encode(s.encode()).decode()


SPEC = json.dumps({"openapi": "3.0.3", "info": {"title": "Kirana API", "version": "1.4"}, "paths": {
    "/items": {"get": {"summary": "List items", "responses": {"200": {"description": "Items"}}}},
    "/orders/{id}": {"get": {"summary": "Get one order", "parameters": [{"name": "id", "in": "path", "required": True,
                                                                         "schema": {"type": "string"}}],
                             "responses": {"200": {"description": "The order"}, "404": {"description": "Not found"}}}}}})


class FakeGitHub:
    def __init__(self):
        self.calls = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        p, m = req.url.path, req.method
        self.calls.append((m, p))
        assert req.headers["authorization"] == "Bearer github_pat_TESTTOKEN_abcdefghijklmnop"
        j = None
        if p == "/user":
            j = {"login": "meghana"}
        elif p == "/repos/meghana/kirana":
            j = {"default_branch": "main", "description": "Kirana app", "private": True}
        elif p == "/repos/meghana/kirana/git/trees/main":
            j = {"tree": [{"path": "README.md", "type": "blob"}, {"path": "docs/setup.md", "type": "blob"},
                          {"path": "api/openapi.json", "type": "blob"}, {"path": "src/app.py", "type": "blob"}]}
        elif p.startswith("/repos/meghana/kirana/contents/"):
            path = p.split("/contents/", 1)[1]
            body = {"README.md": "# Kirana\nOrder groceries.", "docs/setup.md": "# Setup\nInstall the app.", "api/openapi.json": SPEC}[path]
            j = {"type": "file", "size": len(body), "content": _b64(body)}
        elif p == "/repos/meghana/kirana/releases":
            j = [{"tag_name": "v1.3.0", "name": "v1.3.0", "published_at": "2026-10-01T10:00:00Z", "body": "Old"}]
        elif p == "/repos/meghana/kirana/pulls" and m == "GET":
            j = [{"number": 41, "title": "feat: UPI QR on bill", "merged_at": "2026-10-10T10:00:00Z", "labels": [{"name": "feature"}]},
                 {"number": 42, "title": "fix: cart total rounding", "merged_at": "2026-10-12T10:00:00Z", "labels": []},
                 {"number": 39, "title": "chore: old", "merged_at": "2026-09-01T10:00:00Z", "labels": []},
                 {"number": 43, "title": "not merged", "merged_at": None}]
        elif p == "/repos/meghana/kirana/git/ref/heads/main":
            j = {"object": {"sha": "base1"}}
        elif p == "/repos/meghana/kirana/git/commits/base1":
            j = {"tree": {"sha": "tree0"}}
        elif p.endswith("/git/blobs"):
            j = {"sha": "blob" + str(len(self.calls))}
        elif p.endswith("/git/trees"):
            body = json.loads(req.content)
            assert body["base_tree"] == "tree0" and all(t["path"].startswith("docs/hoola/") for t in body["tree"])
            j = {"sha": "tree1"}
        elif p.endswith("/git/commits"):
            j = {"sha": "commit1"}
        elif p.endswith("/git/refs"):
            assert json.loads(req.content)["ref"].startswith("refs/heads/hoola-docs/")
            j = {"ref": "ok"}
        elif p.endswith("/pulls") and m == "POST":
            j = {"html_url": "https://github.com/meghana/kirana/pull/44", "number": 44}
        if j is None:
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(201 if m == "POST" else 200, json=j)


def test_github_api_docs_release_notes_translate_publish(dw, monkeypatch):
    S = dw
    from app.docwriter import github as GH
    fake = FakeGitHub()
    GH.set_transport(httpx.MockTransport(fake))
    try:
        c = client()
        tok = "github_pat_TESTTOKEN_abcdefghijklmnop"
        assert c.put("/api/docwriter/github", json={"token": tok}).json()["label"] == "@meghana"
        assert S.settings(T)["github"]["joined"]
        p = S.add_product(T, "github", "https://github.com/meghana/kirana")["product"]
        assert p["verified"] and p["version"] == "v1.3.0"
        assert not any(c_[1].startswith("/repos/meghana/kirana/contents/src") for c_ in fake.calls)    # code is never read
        api_doc = S.write(T, p["id"], "api", "en")["doc"]
        titles = [x["title"] for x in api_doc["section_list"]]
        assert titles[0] == "Kirana API" and "List items" in titles and "Get one order" in titles
        one = next(x for x in api_doc["section_list"] if x["title"] == "Get one order")
        assert "| `id` | path | string | yes |" in one["body"] and one["by"] == "code"
        rn = S.write(T, p["id"], "release_notes", "en")["doc"]
        body = rn["section_list"][0]["body"]
        assert "UPI QR on bill (#41)" in body and "cart total rounding (#42)" in body and "#39" not in body and "#43" not in body
        assert "### New" in body and "### Fixed" in body
        # translation: UI labels / numbers locked; a dropped marker is caught
        S.save_settings(T, keep=["Kirana"])

        def tr(system, prompt, max_tokens=2500):
            if "Translate" in system:
                return prompt.replace("New", "Naya").replace("Fixed", "Theek hua")
            return ""
        monkeypatch.setattr(S, "_ai", tr)
        hd = S.translate(T, rn["id"], "hinglish")["doc"]
        assert hd["translation_of"] == rn["id"] and "(#41)" in hd["section_list"][0]["body"] and "Naya" in hd["section_list"][0]["body"]
        monkeypatch.setattr(S, "_ai", lambda system, prompt, max_tokens=2500: prompt.replace("⟦1⟧", "") if "Translate" in system else "")
        lost = S.translate(T, rn["id"], "hi")
        assert any(x["kind"] == "lost" for x in lost["doc"]["check_list"]["blocking"])
        # publish = card only from the tool; GitHub PR only on her tap with the right hash
        ctx = asyncio.run(_ctx())
        from app.agent.docwriter_tools import DOCWRITER_HANDLERS as H
        r = asyncio.run(H["docs_writer"](ctx, action="publish", doc=api_doc["id"], dest="github"))
        assert r["status"] == "needs_tap" and "card" in r["say"].lower()
        assert not any(c_[0] == "POST" and c_[1].endswith("/pulls") for c_ in fake.calls)
        card = [pl for k, pl in S.EVENTS if k == "docwriter_publish"][-1]
        assert card["repo"] == "meghana/kirana" and card["dest"] == "github"
        assert c.post(f"/api/docwriter/docs/{api_doc['id']}/decide", json={"yes": True, "hash": "wrong"}).status_code == 400
        ok = c.post(f"/api/docwriter/docs/{api_doc['id']}/decide", json={"yes": True, "hash": card["hash"]}).json()
        assert ok["url"] == "https://github.com/meghana/kirana/pull/44" and S.get(T, api_doc["id"])["status"] == "published"
        # Hoola docs page: card -> tap -> public page with a strict CSP; a change after the card voids it
        S.publish_request(T, rn["id"], "page")
        card2 = [pl for k, pl in S.EVENTS if k == "docwriter_publish"][-1]
        S.edit(T, rn["id"], rn["section_list"][0]["id"], body=body + "\n- Small text fix.")
        assert c.post(f"/api/docwriter/docs/{rn['id']}/decide", json={"yes": True, "hash": card2["hash"]}).status_code == 400
        S.publish_request(T, rn["id"], "page")
        card3 = [pl for k, pl in S.EVENTS if k == "docwriter_publish"][-1]
        done = c.post(f"/api/docwriter/docs/{rn['id']}/decide", json={"yes": True, "hash": card3["hash"]}).json()
        token = done["url"].rsplit("/", 1)[1]
        pg = c.get(f"/api/docwriter/page/{token}")
        assert pg.status_code == 200 and "default-src 'none'" in pg.headers["content-security-policy"] and "Small text fix" in pg.text
        assert c.get("/api/docwriter/page/nope").status_code == 404
        S.unpublish_page(T, rn["id"])
        assert c.get(f"/api/docwriter/page/{token}").status_code == 404
    finally:
        GH.set_transport(None)


async def _ctx():
    return conv_ctx()


def test_files_tools_actors_and_api(dw, monkeypatch):
    S = dw
    _make_app(T)
    ctx = conv_ctx()
    from app.agent.docwriter_tools import DOCWRITER_HANDLERS as H
    staff = Ctx(T, ctx.conversation_id, actor="staff:s1")
    cust = Ctx(T, ctx.conversation_id, actor="customer:wa:9198")
    run = lambda c, **a: asyncio.run(H["docs_writer"](c, **a))       # noqa: E731
    with pytest.raises(ToolError):
        run(cust, action="write", product="A-0001")
    with pytest.raises(ToolError):
        run(ctx, action="add_product", kind="github", ref="ghp_abcdefghijklmnopqrstuvwxyz0123")       # token in chat refused
    assert run(staff, action="add_product", kind="hoola_app", ref="A-0001")["product"]["verified"]
    d = run(staff, action="write", product="A-0001", kind="faq", lang="hinglish")["doc"]
    assert d["sections"] >= 1 and "kaise karein" in d["section_list"][0]["title"]
    with pytest.raises(ToolError):
        run(staff, action="delete", doc=d["id"])
    with pytest.raises(ToolError):
        run(staff, action="settings", tone="friendly")
    m = run(ctx, action="write", product="A-0001", kind="manual", lang="en")["doc"]
    assert "**What you can do here**" in m["section_list"][0]["body"]
    f = run(ctx, action="files", doc=m["id"], formats=["md", "docx", "pdf"])
    names = [x["name"] for x in f["files"]]
    assert any(n.endswith(".zip") for n in names) and any(n.endswith(".docx") for n in names) and "pc_file" in kinds(S)
    assert any(n.endswith(".pdf") for n in names)                 # Chromium printer (Devanagari shaped right)
    import zipfile, io
    from app.analyst.service import _load_file
    _, z = _load_file(T, next(x["file_id"] for x in f["files"] if x["name"].endswith(".zip")))
    zf = zipfile.ZipFile(io.BytesIO(z))
    assert "README.md" in zf.namelist() and any(n.startswith("img/") for n in zf.namelist())
    html = S.doc_html(T, __import__("app.docwriter.models", fromlist=["DocDoc"]).DocDoc(
        id=m["id"], title=m["title"], lang="en", sections=json.dumps(S.get(T, m["id"])["section_list"]), version=1))
    assert "data:image/jpeg;base64," in html and "<script" not in html
    rd = asyncio.run(H["docs_writer_dekho"](ctx, what="rules"))
    assert rd["sources"] and "JavaScript" in " ".join(rd["never"])
    assert asyncio.run(H["docs_writer_dekho"](ctx, what="day"))["docs"]
    c = client()
    all_ = c.get("/api/docwriter").json()
    assert all_["products"] and all_["kinds"] and all_["never"]
    assert c.get(f"/api/docwriter/docs/{m['id']}").json()["number"] == m["number"]
    img = S.get(T, m["id"])["section_list"][0]["shots"][0]["url"]
    assert c.get(img).status_code == 200 and c.get(f"/api/docwriter/docs/{m['id']}/img/..%2F..%2Fx").status_code == 404
    assert c.post("/api/docwriter/docs", json={"product": "A-0001", "kind": "admin"}).status_code == 400   # no blueprint: nothing to say
    assert c.put("/api/docwriter/settings", json={"glossary": [{"term": "order", "avoid": "booking"}]}).json()["glossary"][0]["term"] == "order"
    assert c.delete(f"/api/docwriter/docs/{d['id']}").json()["ok"]
