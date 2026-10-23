"""QA Sahayak: safe step language, ISTQB-style test design, ownership proof before testing her own site, real Chromium runs
(discover -> cases -> run -> bugs with screenshots), de-duplication, fixed -> retest -> verified / reopened / regression, test
accounts sealed and never shown, payments / secret boxes refused, Hoola-built site + app prototype tested from disk, APK
checklist + manual marks + release readiness, GitHub issue only on her tap, tools (actors, no passwords in chat), API, tick."""
import asyncio
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.qa.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
HOST = "shop.qa-test.in"

GOOD_CSS = "body{font-family:sans-serif;color:#111;background:#fff;margin:0;padding:16px}a,button{display:inline-block;min-height:32px;min-width:32px;padding:6px}"


def page(title, body, lang="en"):
    return (f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
            f"<title>{title}</title><style>{GOOD_CSS}</style></head><body><header><nav><a href='/'>Home</a> <a href='/contact/'>Contact</a> "
            f"<a href='/shop/'>Shop</a></nav></header><main>{body}</main></body></html>")


def site_pages(broken=True):
    contact = ("<h1>Contact us</h1><form action='/send' method='post'>"
               "<label for='nm'>Name</label><input id='nm' name='name' required>"
               "<label for='em'>Email</label><input id='em' name='email' type='email'>"
               "<label for='ag'>Age</label><input id='ag' name='age' type='number' min='18' max='99'>"
               "<button type='submit'>Send</button></form><a href='tel:+919800000000'>Call</a>")
    shop = "<h1>Shop</h1><p>Chai patti 250 g</p><button onclick=\"location.href='/checkout/'\">Pay now</button><a href='https://evil.example/'>Partner</a>"
    if broken:
        shop += "<img src='/assets/missing.jpg'>"                                   # no alt + does not load
        contact += "<div style='width:900px;background:#eee'>wide banner</div>"     # sideways scroll on phones
    home = "<h1>Ingle Chai Store</h1><p>Achhi chai, Akola.</p><a href='/shop/'>Shop dekho</a>" + ("<a href='/old/'>Purana offer</a>" if broken else "")
    return {"/": page("Ingle Chai", home), "/contact/": page("Contact", contact), "/shop/": page("Shop", shop),
            "/login/": page("Login", "<h1>Login</h1><form method='post' action='/login/'><label for='u'>Email</label><input id='u' name='u' type='email'>"
                                     "<label for='p'>Password</label><input id='p' name='p' type='password'><button type='submit'>Login</button></form>"),
            "/dashboard/": page("Dashboard", "<h1>Welcome back</h1>")}


class FakeSite:
    def __init__(self):
        self.pages = site_pages()
        self.headers = {"Strict-Transport-Security": "max-age=31536000", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY"}
        self.posts = []

    def __call__(self, route) -> bool:
        from urllib.parse import parse_qs, urlparse
        req = route.request
        u = urlparse(req.url)
        if u.hostname != HOST:
            route.fulfill(status=200, body="/* third party */", headers={"Content-Type": "text/javascript"})
            return True
        if req.method == "POST":
            self.posts.append(u.path)
            self.last_post = req.post_data
            f = parse_qs(req.post_data or "")
            if f.get("u") == ["qa@ingle.in"] and f.get("p") == ["S3cret!pass"]:
                route.fulfill(status=200, body=self.pages["/dashboard/"], headers={"Content-Type": "text/html"})
            else:
                route.fulfill(status=200, body=self.pages["/login/"], headers={"Content-Type": "text/html"})
            return True
        p = u.path if u.path.endswith("/") or "." in u.path.rsplit("/", 1)[-1] else u.path + "/"
        if p in self.pages:
            route.fulfill(status=200, body=self.pages[p], headers={"Content-Type": "text/html", **self.headers})
        else:
            route.fulfill(status=404, body="<html><body>not found</body></html>", headers={"Content-Type": "text/html"})
        return True


@pytest.fixture
def qa(env, monkeypatch, tmp_path):
    from app.qa import runner as RN
    from app.qa import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_model", lambda system, prompt: "")
    monkeypatch.setattr(RN, "is_public", lambda h: h != "10.0.0.5")
    monkeypatch.setenv("QA_DIR", str(tmp_path / "qa"))
    fake = FakeSite()
    monkeypatch.setattr(RN, "NET_FULFILL", fake)
    S.EVENTS, S.FAKE = events, fake
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def own_transport(token_ref: dict, how: str = "meta"):
    def handler(req: httpx.Request):
        if req.url.host == "cloudflare-dns.com":
            ans = [{"type": 16, "data": f'"hoola-qa-verify={token_ref["t"]}"'}] if how == "dns" and req.url.params.get("name") == f"_hoola-qa.{HOST}" else []
            return httpx.Response(200, json={"Answer": ans})
        if req.url.path == "/" and how == "meta":
            return httpx.Response(200, text=f"<html><head><meta name='hoola-qa-verification' content='{token_ref['t']}'></head></html>")
        if req.url.path == "/.well-known/hoola-qa.txt" and how == "file":
            return httpx.Response(200, text=token_ref["t"] + "\n")
        return httpx.Response(200, text="<html>hello</html>")
    return httpx.MockTransport(handler)


def verified_url_target(S, how="meta", **kw):
    out = S.add_target(T, "url", url=f"https://{HOST}/", **kw)
    assert out["target"]["verified"] is False and "TXT" in out["say"]
    tok = {"t": out["target"]["verify"]["token"]}
    S.set_transport(own_transport(tok, how))
    v = S.verify(T, out["target"]["id"])
    assert v["verified"] is True and v["target"]["verified_how"] == how
    return out["target"]["id"]


def test_steps_rules_and_design():
    from app.qa import rules as R
    from app.qa import steps as ST
    good, bad = ST.clean([{"do": "goto", "path": "/contact/"}, {"do": "fill", "target": {"label": "Name"}, "value": "Ramesh"},
                          {"do": "click", "target": {"role": "button", "name": "Send"}}, {"do": "expect_text", "text": "Thanks"}])
    assert len(good) == 4 and not bad
    _, bad = ST.clean([{"do": "eval", "js": "fetch('/x')"}, {"do": "click", "target": {"css": "a[href^='javascript:alert(1)']"}},
                       {"do": "goto", "path": "javascript:alert(1)"}, {"do": "press", "key": "Control+W"}, {"do": "viewport", "width": 999},
                       {"do": "click", "target": {"role": "evil"}}])
    assert len(bad) == 6
    assert "test password" in ST.describe({"do": "fill", "target": {"label": "Password"}, "value": "{account.password}"})
    # EP + 2-value BVA from the field's own rules (nothing guessed)
    parts = R.field_cases({"type": "number", "min": "18", "max": "99", "required": True})
    vals = {(p["value"], p["valid"]) for p in parts}
    assert {("", False), ("17", False), ("18", True), ("99", True), ("100", False)} <= vals
    assert any(not p["valid"] for p in R.field_cases({"type": "email"}))
    assert R.severity("functional", "P1") == "critical" and R.severity("accessibility", "P3", govt_facing=True) == "major"
    assert R.severity("security", "P2") == "critical" and R.severity("functional", "P1", console_only=True) == "minor"
    assert R.fingerprint("t", "c", 2, "Toota link (404): /old/ at 12:31") == R.fingerprint("t", "c", 2, "Toota link (404): /old/ at 09:05")
    assert R.host_problem("localhost") and R.host_problem("10.0.0.5") and R.host_problem("intranet.local") and not R.host_problem(HOST)
    rd = R.readiness([{"status": "active", "number": "TC-1", "title": "home", "priority": "P1", "type": "functional", "last_result": "pass"}],
                     [{"status": "open", "severity": "major", "number": "B-1", "title": "x"}])
    assert rd["verdict"] == "not_ready" and rd["blockers"]
    assert "GIGW 3.0" in R.STANDARDS["govt"] and "SEBI" in R.STANDARDS["securities"]


def test_ownership_before_any_test(qa):
    S = qa
    with pytest.raises(S.QaError):
        S.add_target(T, "url", url="http://localhost:8077/")
    with pytest.raises(S.QaError):
        S.add_target(T, "url", url="https://10.0.0.5/")
    out = S.add_target(T, "url", url=f"https://{HOST}/")
    tid = out["target"]["id"]
    S.set_transport(own_transport({"t": "someone-else"}, "meta"))
    assert S.verify(T, tid)["verified"] is False
    with pytest.raises(S.QaError, match="ownership"):
        S.run(T, tid)
    with pytest.raises(S.QaError, match="ownership"):
        S.discover(T, tid)
    tok = {"t": out["target"]["verify"]["token"]}
    for how in ("dns", "file", "meta"):
        S.set_transport(own_transport(tok, how))
        assert S.verify(T, tid)["target"]["verified_how"] == how
    assert S.add_target(T, "url", url=f"https://{HOST}/shop")["target"]["id"] == tid       # same host = same target


def test_discover_cases_run_bugs_retest_regression(qa, monkeypatch):
    S = qa
    tid = verified_url_target(S)
    # the model writes cases for her requirements: one in the safe language, one with JavaScript (-> manual)
    monkeypatch.setattr(S, "_model", lambda system, prompt: json.dumps({"cases": [
        {"title": "Contact form: sahi naam aur email", "type": "functional", "priority": "P2", "expected": "Form bhara ja sake",
         "steps": [{"do": "goto", "path": "/contact/"}, {"do": "fill", "target": {"label": "Name"}, "value": "Ramesh"},
                   {"do": "expect_valid", "target": {"label": "Name"}}]},
        {"title": "Shop page ka sneaky test", "type": "functional", "priority": "P3", "steps": [{"do": "eval", "js": "document.cookie"}],
         "steps_text": ["Shop kholo"], "expected": "Shop khule"}]}))
    g = S.generate(T, tid, text="Graahak contact form se message bhej sake. Shop page par products dikhne chahiye.")
    assert g["added"] >= 15 and any("haath se jaanch" in n for n in g["notes"])
    cs = S.cases(T, tid)
    titles = [c["title"] for c in cs]
    assert "Page / khulta hai" in titles and any("'Age' seema se upar (100)" in x for x in titles)
    assert any(c["type"] == "accessibility" for c in cs) and any(c["type"] == "security" for c in cs)
    sneaky = next(c for c in cs if c["title"] == "Shop page ka sneaky test")
    assert sneaky["auto"] is False and sneaky["source"] == "model"
    assert "qa_cases" in kinds(S)
    # her own case that tries to pay, and one that tries to put a made-up password in -> blocked, never a bug
    pay = S.add_case(T, tid, "Pay karke dekho", [{"do": "goto", "path": "/shop/"}, {"do": "click", "target": {"text": "Pay now"}}])["case"]
    pw = S.add_case(T, tid, "Password daalo", [{"do": "goto", "path": "/login/"}, {"do": "fill", "target": {"label": "Password"}, "value": "hello123"}])["case"]
    out_c = S.add_case(T, tid, "Partner link", [{"do": "goto", "path": "/shop/"}, {"do": "click", "target": {"text": "Partner"}},
                                                {"do": "expect_url", "contains": "evil"}])["case"]
    r = S.run(T, tid)
    c = r["run"]["counts"]
    assert c["pass"] > 5 and c["fail"] >= 4, c
    res = {x["case_id"]: x for x in r["run"]["results"]}
    assert res[pay["id"]]["status"] == "blocked" and "Payment" in res[pay["id"]]["message"]
    assert res[pw["id"]]["status"] == "blocked"
    assert res[out_c["id"]]["status"] == "fail" and any("bahar" in n for n in res[out_c["id"]]["notes"])
    bs = S.bugs(T, tid)
    texts = " | ".join(b["title"] for b in bs)
    assert "Toota link" in texts and "1.4.10" in texts and "1.1.1" in texts
    assert all(b["number"].startswith("B-") and b["steps"] and b["expected"] and b["actual"] for b in bs)
    shot_bug = next(b for b in bs if b["shot"])
    rid, name = shot_bug["shot"].split("/")
    assert S.shot_path(T, rid, name) and S.shot_path(T, rid, "../../x.jpg") is None
    assert "qa_run" in kinds(S) and "qa_bug" in kinds(S)
    assert S.FAKE.posts == []                          # nothing was submitted to her live site
    # the same failures again = the same bugs, seen twice
    n_bugs = len(bs)
    r2 = S.run(T, tid, "failed")
    assert not r2["bugs"]["new"] and len(S.bugs(T, tid)) == n_bugs and all(b["seen"] == 2 for b in S.bugs(T, tid) if b["status"] == "open")
    # her developer fixes the site; she marks one fixed; retest -> verified + regression suite
    link_bug = next(b for b in S.bugs(T, tid) if "Toota link" in b["title"])
    S.FAKE.pages = site_pages(broken=False)
    S.set_bug(T, link_bug["number"], "fixed", by="owner")
    rt = S.retest(T, link_bug["number"])
    assert rt["bug"]["status"] == "verified" and "regression" in S.case(T, link_bug["case_id"])["tags"]
    # it breaks again later -> reopened as a regression
    S.FAKE.pages = site_pages(broken=True)
    r3 = S.run(T, tid, "regression")
    again = S.bug(T, link_bug["number"])
    assert again["status"] == "reopened" and again["regression"] is True
    assert link_bug["number"] in r3["run"]["bugs"]["reopened"]
    with pytest.raises(S.QaError):
        S.set_bug(T, link_bug["number"], "wont_fix")                      # needs a reason
    with pytest.raises(S.QaError):
        S.set_bug(T, link_bug["number"], "verified")                      # only a passing retest verifies
    ready = S.readiness(T, tid)["readiness"]
    assert ready["verdict"] == "not_ready" and ready["blockers"]


def test_test_account_login_sealed(qa):
    S = qa
    tid = verified_url_target(S, how="file")
    S.update_target(T, tid, allow_writes=True)
    S.set_account(T, tid, "test", "qa@ingle.in", "S3cret!pass")
    v = S.target(T, tid)
    assert v["accounts"][0]["hint"].startswith("qa") and "S3cret" not in json.dumps(v)
    from app.db import session
    from app.qa.models import QaAccount
    with session() as s:
        a = s.query(QaAccount).first()
        assert "S3cret" not in a.sealed_pass and "qa@ingle" not in a.sealed_user
    c = S.add_case(T, tid, "Login with test account", [
        {"do": "goto", "path": "/login/"}, {"do": "fill", "target": {"label": "Email"}, "value": "{account.username}"},
        {"do": "fill", "target": {"label": "Password"}, "value": "{account.password}"}, {"do": "click", "target": {"role": "button", "name": "Login"}},
        {"do": "expect_text", "text": "Welcome back"}])["case"]
    assert c["account"] == "test" and "(test password)" in " ".join(c["steps_text"])
    r = S.run(T, tid, case_ids=[c["number"]])
    assert r["run"]["counts"]["pass"] == 1, (r["run"]["results"], S.FAKE.posts, S.FAKE.last_post)
    assert "S3cret" not in json.dumps(r) and "/login/" in S.FAKE.posts
    # without the account the case is blocked, not a bug
    S.remove_account(T, tid, "test")
    r = S.run(T, tid, case_ids=[c["id"]])
    assert r["run"]["results"][0]["status"] == "blocked" and not r["bugs"]["new"]


def _site(tmp_path, monkeypatch):
    from app.db import session
    from app.site.models import Site
    monkeypatch.setenv("SITE_DIR", str(tmp_path / "sites"))
    with session() as s:
        r = Site(tenant_id=T, number="S-0001", name="Ingle Chai", brief="Chai ki dukaan ki website", version=1,
                 plan=json.dumps({"pages": [{"slug": "home", "title": "Home", "sections": [{"label": "Hero"}]}]}))
        s.add(r)
        s.flush()
        sid = r.id
    from app.site import build as SB
    out = SB.out_dir(T, sid, 1)
    for p, html in site_pages(broken=False).items():
        if p in ("/login/", "/dashboard/"):
            continue
        d = out / p.strip("/")
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(html)
    return sid


def _app(tmp_path, monkeypatch, apk=False):
    from app.appmaker import kit
    from app.appmaker.models import AppProject
    from app.db import session
    monkeypatch.setenv("APP_DIR", str(tmp_path / "apps"))
    with session() as s:
        r = AppProject(tenant_id=T, number="A-0001", name="Ingle Chai App", brief="Chai order app", version=1,
                       plan=json.dumps({"screens": ["home", "menu", "consent"], "labels": {"home": "Home", "menu": "Menu", "consent": "Consent"},
                                        "tabs": ["home", "menu"], "flow": ["home", "menu"]}),
                       android=json.dumps({"apk": "app.apk"}) if apk else None)
        s.add(r)
        s.flush()
        aid = r.id
    live = kit.app_dir(T, aid) / "live"
    (live / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(kit.__file__).parent / "assets" / "proto.js", live / "assets" / "proto.js")
    (live / "assets" / "s.css").write_text(".scr{display:none}.scr.on{display:block}body{color:#111;background:#fff}"
                                           "button,a,label{min-height:30px;min-width:30px;display:inline-block}")
    (live / "index.html").write_text(
        "<!doctype html><html lang='en'><head><title>Ingle Chai App</title><link rel='stylesheet' href='assets/s.css'></head>"
        "<body class='p-android'><div class='frame'>"
        "<section class='scr' data-screen='home' data-tabbed><h1>Home</h1><button data-go='menu'>Menu dekho</button></section>"
        "<section class='scr' data-screen='menu' data-tabbed><h1>Menu</h1><button data-go='home'>Wapas</button></section>"
        "<section class='scr' data-screen='consent'><h1>Consent</h1><label><input type='checkbox' data-consent> Main maanti hoon</label>"
        "<button data-needs-consent disabled data-go='home'>Aage</button></section>"
        "</div><script src='assets/proto.js'></script></body></html>")
    return aid


def test_hoola_site_and_app_from_disk(qa, tmp_path, monkeypatch):
    S = qa
    sid = _site(tmp_path, monkeypatch)
    t = S.add_target(T, "site", ref="S-0001")
    assert t["target"]["verified"] and t["target"]["verified_how"] == "hoola_site"
    g = S.generate(T, t["target"]["id"])
    assert g["added"] >= 8
    r = S.run(T, t["target"]["id"], "smoke")
    assert r["run"]["counts"]["fail"] == 0 and r["run"]["counts"]["pass"] >= 3, r["run"]["results"]
    full = S.run(T, t["target"]["id"])
    fails = [x for x in full["run"]["results"] if x["status"] == "fail"]
    assert not any("Toota link" in x["message"] for x in fails), fails       # every internal link of the built site works
    # someone else's site id can't be added
    with pytest.raises(S.QaError):
        S.add_target(T, "site", ref="site_nope")
    aid = _app(tmp_path, monkeypatch)
    a = S.add_target(T, "app", ref=aid)["target"]
    g = S.generate(T, a["id"])
    cs = S.cases(T, a["id"])
    assert any("tick ke bina aage nahi" in c["title"] for c in cs) and any(c["technique"] == "navigation" for c in cs)
    r = S.run(T, a["id"])
    assert r["run"]["counts"]["fail"] == 0, [x for x in r["run"]["results"] if x["status"] != "pass"]
    assert sid


def test_apk_checklist_marks_and_readiness(qa, tmp_path, monkeypatch):
    S = qa
    aid = _app(tmp_path, monkeypatch, apk=True)
    out = S.add_target(T, "apk", ref=aid)
    tid = out["target"]["id"]
    cs = S.cases(T, tid)
    assert len(cs) >= 15 and all(not c["auto"] for c in cs) and any("pre-launch" in c["title"] for c in cs)
    with pytest.raises(S.QaError, match="haath"):
        S.run(T, tid)
    assert S.readiness(T, tid)["readiness"]["verdict"] == "not_ready"      # P1 checks not done yet
    bad = next(c for c in cs if "Back" in c["title"])
    m = S.mark(T, bad["number"], "fail", note="Menu screen par Back dabane se app band ho gaya")
    assert m["bugs"]["new"] and m["bugs"]["new"][0]["actual"].startswith("Menu screen")
    again = S.mark(T, bad["number"], "fail", note="phir se band")
    assert not again["bugs"]["new"]                                         # same manual failure = same bug
    for c in cs:
        S.mark(T, c["id"], "pass")
    assert S.bug(T, m["bugs"]["new"][0]["number"])["status"] == "verified"
    assert S.readiness(T, tid)["readiness"]["verdict"] == "ready"


def test_github_issue_only_on_her_tap(qa, monkeypatch):
    S = qa
    tid = verified_url_target(S)
    c = S.add_case(T, tid, "Home par offer", [{"do": "goto", "path": "/"}, {"do": "expect_text", "text": "Diwali offer"}],
                   expected="Diwali offer dikhe")["case"]
    r = S.run(T, tid, case_ids=[c["id"]])
    b = r["bugs"]["new"][0]
    with pytest.raises(S.QaError, match="GitHub juda"):
        S.github_request(T, b["number"], "newtika/ingle-site")
    from app.bazar.security import vault
    from app.db import session
    from app.site.hosting_models import SiteHostingKey
    with session() as s:
        s.add(SiteHostingKey(tenant_id=T, provider="github", sealed=vault().seal("github_pat_" + "x" * 30), label="@newtika", verified=True))
    with pytest.raises(S.QaError):
        S.github_request(T, b["number"], "not a repo")
    card = S.github_request(T, b["number"], "newtika/ingle-site")
    assert card["status"] == "needs_tap" and "qa_export" in kinds(S)
    e = card["export"]
    assert "Diwali offer" in e["body"] and "Expected" in e["body"]
    calls = []

    def gh(req: httpx.Request):
        calls.append((req.method, req.url.path, json.loads(req.content or b"{}")))
        return httpx.Response(201, json={"number": 7, "html_url": "https://github.com/newtika/ingle-site/issues/7"})
    from app.site import github as G
    G.set_transport(httpx.MockTransport(gh))
    try:
        with pytest.raises(S.QaError):
            S.github_push(T, e["id"], e["hash"])                                  # not her tap
        with pytest.raises(S.QaError):
            S.github_push(T, e["id"], "wrong", by_tap=True)
        assert not calls
        done = S.github_push(T, e["id"], e["hash"], by_tap=True)
        assert done["export"]["status"] == "done" and calls[0][1] == "/repos/newtika/ingle-site/issues"
        assert "hoola-qa" in calls[0][2]["labels"] and S.bug(T, b["number"])["tracker"]["github"]["number"] == 7
        assert S.github_push(T, e["id"], e["hash"], by_tap=True)["export"]["status"] == "done" and len(calls) == 1
    finally:
        G.set_transport(None)


def test_tools_api_register_and_tick(qa, monkeypatch):
    S = qa
    from app.agent import qa_tools as Q
    from app.agent.tools import Ctx, ToolError
    ctx = conv_ctx()
    out = asyncio.run(Q.qa(ctx, action="target_add", kind="url", url=f"https://{HOST}/"))
    tid = out["target"]["id"]
    with pytest.raises(ToolError, match="Password"):
        asyncio.run(Q.qa(ctx, action="write", target=tid, text="login karo, password: Ingle@2026"))
    cust = Ctx(T, ctx.conversation_id, actor="customer:wa:9800000000")
    with pytest.raises(ToolError):
        asyncio.run(Q.qa(cust, action="ready", target=tid))
    staff = Ctx(T, ctx.conversation_id, actor="staff:abc")
    with pytest.raises(ToolError, match="owner"):
        asyncio.run(Q.qa(staff, action="github", bug="B-0001", repo="a/b"))
    with pytest.raises(ToolError, match="owner"):
        asyncio.run(Q.qa(staff, action="target_edit", target=tid, allow_writes=True))
    assert "goto" in asyncio.run(Q.qa_dekho(ctx, what="steps"))["steps"]
    assert asyncio.run(Q.qa_dekho(ctx, what="targets"))["targets"][0]["verified"] is False
    # API
    from app.qa.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/qa").json()["targets"]
    tok = {"t": c.get(f"/api/qa/targets/{tid}").json()["verify"]["token"]}
    S.set_transport(own_transport(tok, "meta"))
    assert c.post(f"/api/qa/targets/{tid}/verify").json()["verified"] is True
    assert c.put(f"/api/qa/targets/{tid}/accounts", json={"username": "a"}).status_code == 400
    ca = c.post("/api/qa/cases", json={"target": tid, "title": "Home", "steps": [{"do": "goto", "path": "/"}, {"do": "expect_text", "text": "Ingle"}]})
    assert ca.status_code == 200, ca.text
    assert c.post("/api/qa/cases", json={"target": tid, "title": "Bad", "steps": [{"do": "eval"}]}).status_code == 400
    assert c.patch(f"/api/qa/targets/{tid}", json={"schedule": "25:99"}).status_code == 400
    c.patch(f"/api/qa/targets/{tid}", json={"schedule": "21:30"})
    assert c.get("/api/qa/shots/nope/x.jpg").status_code == 404
    assert c.post("/api/qa/exports/nope/push", json={"hash": "x"}).status_code == 400
    reg = c.post("/api/qa/register", json={"target": tid}).json()
    assert len(reg["files"]) == 2
    started = []
    monkeypatch.setattr(S, "start_run", lambda tenant, t, which="all", case_ids=None, by="owner", conv="": started.append((t, which, by)))
    ist = timezone(timedelta(hours=5, minutes=30))
    assert S.tick(datetime(2026, 10, 23, 21, 0, tzinfo=ist)) == 0
    assert S.tick(datetime(2026, 10, 23, 21, 31, tzinfo=ist)) == 1 and started == [(tid, "regression", "routine")]
    assert S.tick(datetime(2026, 10, 23, 22, 0, tzinfo=ist)) == 0           # once a day
