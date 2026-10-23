"""Product Sahayak: rules (RICE / ICE / Kano / store limits / checks), harvest from seeded Feedback + Seva + Telecaller data,
backlog dedupe / merge / scoring with HER numbers only, roadmap with capacity + dependencies + plan, specs with Given / When /
Then + tasks for dev / QA, release notes from her words + merged PRs (fake GitHub) + shipped items, publishing only on her
tap (GitHub release / public page / copy), before / after for shipped items, tools (actors, tokens) and API."""
import asyncio
import json
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.feedback.models  # noqa: F401  (tables for init_db)
import app.product.models  # noqa: F401
import app.seva.service  # noqa: F401
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def pm(env, monkeypatch):
    from app.feedback import service as F
    from app.product import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    monkeypatch.setattr(F, "_ai_json", lambda *a, **k: {})
    monkeypatch.setattr(F, "_publish", lambda *a, **k: None)
    S.EVENTS = events
    yield S
    S.set_transport(None)


def kinds(S):
    return [k for k, _ in S.EVENTS]


def _seed(S):
    from app.feedback import service as F
    from app.seva import service as SV
    F.add_text(T, "Delivery bahut late aayi, 2 ghante lage 2*\n\n- delivery late thi phir se, call karo 9876543210 1*\n\n"
                  "- delivery boy late aaya 2*\n\n- khana accha tha 5*")
    for txt in ("Delivery nahi aayi abhi tak", "Order deliver nahi hua, kab aayega", "delivery bahut late hai"):
        SV.new_ticket(T, txt, channel="phone", name="Ramesh", category="delivery")


def test_rules():
    from app.product import rules as R
    assert R.rice(500, 2, 80, "2 mahine")["score"] == 400.0
    m = R.rice(500, None, 0.8, None)
    assert m["score"] is None and m["missing"] == ["impact", "effort"] and "andaaza" in m["ask"]
    assert R.effort_months("2 hafte") == pytest.approx(0.462, abs=0.01) and R.effort_months("10 din") == pytest.approx(0.461, abs=0.01)
    assert R.impact_of("bada") == 2.0 and R.impact_of(1.7) == 2.0 and R.confidence_of("50%") == 0.5
    assert "moonshot" in R.rice(10, 1, 30, 1)["notes"][0]
    assert R.ice(8, 6, 5)["score"] == 240.0 and R.ice(8, None, 5)["missing"] == ["confidence"]
    assert R.kano("pasand", "bura") == "performance" and R.kano("pasand", "farak nahi") == "attractive"
    assert R.kano("farak nahi", "bura") == "must" and R.kano("farak nahi", "farak nahi") == "indifferent"
    assert R.kano_tally([("pasand", "farak nahi"), ("pasand", "chalega"), ("zaroori", "bura")])["category"] == "attractive"
    assert R.change_type("Fix crash on login") == "Fixed" and R.change_type("Naya UPI payment option") == "Added"
    assert R.internal_only("chore: bump deps") and not R.internal_only("Order tracking screen")
    assert R.strip_refs("feat(app): order tracking (#42) by @ramesh") == "order tracking by"
    long = [f"• line number {i} with some words" for i in range(40)]
    out = R.fit(long, R.PLAY_MAX, "• Aur bhi")
    assert len(out) <= 500 and out.endswith("• Aur bhi")
    probs = {p["id"] for p in R.note_problems("Ab 100% guarantee. Call 9876543210 [blank]", "")}
    assert {"blank", "personal", "promise"} <= probs
    assert R.mask("mail ramesh@x.com otp is 482913 ghp_" + "a" * 30) == "mail [email] otp [hataya] [key hataya]"
    g = R.gherkin("Tracking", [{"id": "US-1", "as_a": "graahak", "i_want": "order dekhna", "so_that": "pata rahe",
                                "criteria": [{"given": "order hua", "when": "tracking kholu", "then": "status dikhe"}]}])
    assert "Scenario: US-1.1" in g and "Given order hua" in g and "Then status dikhe" in g


def test_harvest_feedback_seva_telecall(pm, monkeypatch):
    S = pm
    _seed(S)
    from app.telecall import service as TC
    monkeypatch.setattr(TC, "objection_library", lambda tenant, purpose="", limit=8: [
        {"objection": "price zyada hai", "times": 4, "won_pct": 25, "worked": ""},
        {"objection": "ek baar", "times": 1, "won_pct": 0, "worked": ""}])
    h = S.harvest(T, 30)
    assert len(h["new"]) >= 2 and "product_backlog" in kinds(S)
    bl = S.backlog(T)["items"]
    srcs = {s for o in bl for s in o["sources"]}
    assert {"feedback", "telecall"} <= srcs and ("seva" in srcs)
    fb = next(o for o in bl if "feedback" in o["sources"])
    full = S.opportunity(T, fb["number"])
    ev = next(e for e in full["evidence"] if e["source"] == "feedback")
    assert ev["count"] >= 3 and ev["key"] == "feedback:delivery:neg"
    assert all("9876543210" not in q for q in ev["quotes"])          # customer phone never kept
    assert full["score"] is None and "andaaza" in full["ask"]         # no invented numbers
    assert full["reach"] is None
    # again: refreshed, never doubled
    h2 = S.harvest(T, 30)
    assert h2["new"] == [] and len(S.backlog(T)["items"]) == len(bl)
    assert not any("ek baar" in o["title"] for o in bl)               # heard once = not a pattern yet


def test_ideas_dedupe_merge_score(pm):
    S = pm
    a = S.add_opportunity(T, "Graahak ko order ka status nahi pata chalta", who="app users")["opportunity"]
    j = S.add_ideas(T, "- Graahak ko order ka status nahi pata chalta hai\n- WhatsApp par bill bhejna", source="idea")
    assert a["number"] in j["joined"] and len(j["new"]) == 1
    c = S.add_ideas(T, "Swiggy jaisa live tracking map", competitor="Swiggy")
    cv = S.opportunity(T, c["items"][0]["number"])
    assert cv["sources"] == ["competitor"] and "Swiggy" in cv["evidence"][0]["note"]
    with pytest.raises(S.ProductError):
        S.score(T, a["number"], impact=7.5, reach="x")
    r = S.score(T, a["number"], reach=400, impact=2, confidence=80, effort="1 mahina")
    assert r["opportunity"]["score"] == 640.0 and "640" in r["say"]
    with pytest.raises(S.ProductError):
        S.score(T, cv["number"], use_seen=True)                          # competitor note has no people count
    S.add_opportunity(T, "Tracking map chahiye", source="her", key="test:k", count=None, people=12)
    m = S.merge(T, cv["number"], "Tracking map chahiye")
    merged = m["opportunity"]
    assert len(merged["evidence"]) == 2 and S.opportunity(T, cv["number"])["status"] == "merged"
    s2 = S.score(T, merged["number"], use_seen=True, impact=1, confidence=50, effort=0.5)
    assert s2["opportunity"]["reach"] == 12.0 and "kam se kam" in s2["say"]
    k = S.kano_set(T, merged["number"], answers=[["pasand", "farak nahi"], ["pasand", "chalega"]])
    assert k["opportunity"]["kano"] == "attractive"
    sol = S.add_solution(T, a["number"], "Order status SMS")
    assert "3 tareeke" in sol["say"]
    assert S.duplicates(T) == [] or all(p["similar"] >= 0.55 for p in S.duplicates(T))


def test_roadmap_capacity_dependencies_plan(pm, monkeypatch):
    S = pm
    S.save_settings(T, product="Kirana app", capacity={"now": "1 mahina", "next": 2}, north_star={"name": "Weekly ordering customers", "target": 300})
    k = S.set_kpi(T, "Repeat orders", unit="%", target=40)["kpi"]
    o = [S.add_opportunity(T, t, join=False)["opportunity"]["number"] for t in
         ("Login OTP late aata hai", "Order tracking screen", "Bill WhatsApp par", "Dark mode")]
    S.score(T, o[0], reach=900, impact=3, confidence=100, effort="2 hafte")
    S.score(T, o[1], reach=500, impact=2, confidence=80, effort=1)
    S.score(T, o[2], reach=300, impact=1, confidence=80, effort="2 hafte")
    S.set_depends(T, o[1], [o[2]])
    S.update_opportunity(T, o[1], goal="Repeat orders", theme="Bharosa")
    with pytest.raises(S.ProductError):
        S.update_opportunity(T, o[1], goal="nahi hai")
    p = S.plan(T)
    to = {m["number"]: m["to"] for m in p["moves"]}
    assert to[o[0]] == "now" and o[3] in p["unscored"]
    assert {"now": 0, "next": 1, "later": 2}[to[o[1]]] >= {"now": 0, "next": 1, "later": 2}[to[o[2]]]   # after its dependency
    assert S.roadmap(T)["buckets"]["now"]["items"] == []                # suggestion only
    S.plan(T, apply=True)
    rm = S.roadmap(T)
    assert rm["buckets"]["now"]["effort"] <= 1.0 + 1e-6 and o[0] in [v["number"] for v in rm["buckets"]["now"]["items"]]
    pl = S.place(T, o[2], "later")
    assert any("nirbhar" in w["say"] for w in pl["warnings"]) or any("nirbhar" in p["say"] for p in pl["roadmap"]["problems"])
    S.place(T, o[3], "now")
    rm = S.roadmap(T)
    assert any(p["id"] == "effort_now" for p in rm["problems"])
    S.set_depends(T, o[2], [o[1]])
    assert S._cycles(T)
    assert any(p["id"] == "cycle" for p in S.roadmap(T)["problems"])
    pub = S.roadmap_text(T, public=True)
    assert "score" not in pub.lower() and "Dark mode" in pub and "pakki nahi" in pub
    assert k["id"]
    from app import chatfiles
    monkeypatch.setattr(chatfiles, "store", lambda tenant, name, data, mime="": {"file_id": "f_" + name, "name": name, "size": len(data)})
    f = S.roadmap_files(T)
    assert [x["name"] for x in f["files"]] == ["Roadmap.docx", "Roadmap.md", "Roadmap.xlsx"]


def test_spec_tasks_and_files(pm, monkeypatch):
    S = pm
    o = S.add_opportunity(T, "Order tracking screen", problem="Graahak baar baar call karke status poochhte hain", who="app users")
    num = o["opportunity"]["number"]
    sp = S.write_spec(T, num)["spec"]                                   # no model: honest template with blanks
    assert sp["status"] == "draft" and sp["blocks"] >= 1 and "product_spec" in kinds(S)
    good = {"title": "Order tracking", "problem": "Graahak status ke liye call karte hain",
            "users": ["app users"], "goals": ["Status calls kam hon"], "non_goals": ["Live map nahi"],
            "stories": [{"id": "US-1", "as_a": "graahak", "i_want": "order ka status dekhna", "so_that": "call na karna pade",
                         "criteria": [{"given": "order place hua", "when": "Orders kholu", "then": "status aur samay dikhe"}]}],
            "flows": ["Orders kholo", "Order chuno"], "edge_cases": ["Net band"], "events": [{"name": "Order Tracking Viewed", "when": "screen khule"}],
            "metrics": ["status calls"], "risks": [], "open_questions": [], "rollout": ["10% graahak"]}
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: good)
    sp2 = S.write_spec(T, num)["spec"]
    assert sp2["status"] == "ready" and sp2["body"]["events"][0]["name"] == "order_tracking_viewed"
    assert "**Given** order place hua" in sp2["markdown"]
    t = S.tasks(T, sp2["number"])
    assert t["ready"] and t["dev_tasks"][0]["acceptance"][0].startswith("Given order place hua")
    assert any(c["id"].endswith("EDGE-1") for c in t["qa_cases"]) and "Feature: Order tracking" in t["gherkin"]
    e = S.edit_spec(T, sp2["number"], {"stories": good["stories"] + [{"id": "US-2", "as_a": "staff", "i_want": "status badalna",
                                                                      "so_that": "x", "criteria": [{"given": "", "when": "", "then": ""}]}]})
    assert e["spec"]["status"] == "draft" and e["spec"]["version"] == 2
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    rv = S.revise_spec(T, sp2["number"], "Hindi mein bhi")
    assert "open questions" in rv["say"]
    from app import chatfiles
    monkeypatch.setattr(chatfiles, "store", lambda tenant, name, data, mime="": {"file_id": "f_" + name, "name": name, "size": len(data)})
    files = S.spec_files(T, sp2["number"])["files"]
    assert [f["name"].rsplit(".", 1)[1] for f in files] == ["docx", "md", "feature"]


class FakeGitHub:
    def __init__(self, write=True):
        self.calls = []
        self.write = write

    def handler(self, req: httpx.Request) -> httpx.Response:
        self.calls.append((req.method, req.url.path, req.content))
        if req.url.path == "/user":
            return httpx.Response(200, json={"login": "meghana"})
        if req.url.path == "/repos/newtika/kirana":
            return httpx.Response(200, json={"permissions": {"push": self.write}})
        if req.url.path == "/repos/newtika/kirana/pulls":
            from app.db import now
            d = (now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
            return httpx.Response(200, json=[
                {"number": 41, "title": "feat: order tracking screen", "merged_at": d, "labels": [], "html_url": "https://github.com/x/41"},
                {"number": 42, "title": "chore: bump deps", "merged_at": d, "labels": [{"name": "dependencies"}], "html_url": "u"},
                {"number": 43, "title": "Fix crash when cart is empty", "merged_at": d, "labels": [], "html_url": "u43"},
                {"number": 44, "title": "WIP not merged", "merged_at": None, "labels": []}])
        if req.url.path == "/repos/newtika/kirana/releases" and req.method == "POST":
            if not self.write:
                return httpx.Response(403, json={"message": "Resource not accessible by personal access token"})
            return httpx.Response(201, json={"html_url": "https://github.com/newtika/kirana/releases/tag/2.4.0"})
        return httpx.Response(404, json={"message": "nf"})


def test_release_notes_and_publish_on_her_tap(pm):
    S = pm
    gh = FakeGitHub()
    S.set_transport(httpx.MockTransport(gh.handler))
    with pytest.raises(S.ProductError):
        S.merged_prs(T)
    j = S.save_github(T, "ghp_" + "x" * 30, "newtika/kirana")
    assert j["label"] == "@meghana" and j["can_write"] is True
    with S.session() as s:
        assert "ghp_" not in s.scalars(S.select(S.ProductKey)).first().sealed
    assert "ghp_" not in json.dumps(S.settings(T))
    o = S.add_opportunity(T, "Bill WhatsApp par", join=False)["opportunity"]["number"]
    S.ship(T, o)
    rel = S.release_new(T, "2.4.0", text="Naya: UPI se payment\nrefactor checkout code")["release"]
    items = rel["items_list"]
    cust = [i["text"] for i in items if i["customer"]]
    assert any("order tracking" in t for t in cust) and any("crash" in t.lower() for t in cust)
    assert not any("bump deps" in t for t in cust) and not any("refactor" in t for t in cust)
    assert any(i.get("opp") == o for i in items) and not any(i.get("pr") == 44 for i in items)
    n = rel["notes"]
    assert len(n["play"]["hinglish"]) <= 500 and len(n["play"]["en-IN"]) <= 500 and len(n["appstore"]) <= 4000
    assert "#41" in n["changelog"] and "### Fixed" in n["changelog"] and "## [2.4.0]" in n["changelog"]
    assert "#41" not in "\n".join(n["hinglish"]) and "product_release" in kinds(S)
    # her edit with a phone number blocks publishing
    S.release_edit(T, "2.4.0", hinglish=n["hinglish"] + ["Call karo 9876543210"])
    with pytest.raises(S.ProductError):
        S.publish_request(T, "release", "2.4.0", "github")
    S.release_edit(T, "2.4.0", hinglish=n["hinglish"])
    card = S.publish_request(T, "release", "2.4.0", "github")["card"]
    assert card["status"] == "waiting" and "product_publish" in kinds(S)
    assert not any(c[0] == "POST" and c[1].endswith("/releases") for c in gh.calls)   # nothing went out yet
    with pytest.raises(S.ProductError):
        S.decide_publish(T, card["id"], True, card["hash"])                            # not a tap
    with pytest.raises(S.ProductError):
        S.decide_publish(T, card["id"], True, "wrong", by_tap=True)
    d = S.decide_publish(T, card["id"], True, card["hash"], by_tap=True)
    assert d["status"] == "published" and "releases/tag/2.4.0" in d["url"]
    body = json.loads(next(c[2] for c in gh.calls if c[0] == "POST" and c[1].endswith("/releases")))
    assert body["tag_name"] == "2.4.0" and "## [2.4.0]" in body["body"]
    assert S.release(T, "2.4.0")["status"] == "published"
    assert S.opportunity(T, o)["release_id"]
    with pytest.raises(S.ProductError):
        S.decide_publish(T, card["id"], True, card["hash"], by_tap=True)              # once
    with pytest.raises(S.ProductError):
        S.release_new(T, "2.4.0", text="again")
    # public page for the roadmap, then taken down
    S.place(T, S.add_opportunity(T, "Dark mode", join=False)["opportunity"]["number"], "next")
    rc = S.publish_request(T, "roadmap", dest="page")["card"]
    no = S.decide_publish(T, rc["id"], False, rc["hash"], by_tap=True)
    assert no["status"] == "rejected"
    rc = S.publish_request(T, "roadmap", dest="page")["card"]
    pg = S.decide_publish(T, rc["id"], True, rc["hash"], by_tap=True)
    token = pg["url"].rsplit("/", 1)[1]
    code, html_ = S.public_page(token)
    assert code == 200 and "Dark mode" in html_ and "<script" not in html_
    S.unpage(T, rc["id"])
    assert S.public_page(token)[0] == 404
    # write refused by GitHub -> failed, release back to draft
    gh.write = False
    r2 = S.release_new(T, "2.5.0", text="Naya: coupon code")["release"]
    c2 = S.publish_request(T, "release", r2["number"], "github")["card"]
    f = S.decide_publish(T, c2["id"], True, c2["hash"], by_tap=True)
    assert f["status"] == "failed" and "Contents: write" in f["error"] and S.release(T, "2.5.0")["status"] == "draft"


def test_before_after_and_metrics(pm):
    S = pm
    _seed(S)
    S.harvest(T, 30)
    from app.db import now, session
    from app.feedback.models import FbItem
    from app.seva.service import SevaTicket
    fb = next(o for o in S.backlog(T)["items"] if "feedback" in o["sources"])
    ship_day = (now() - timedelta(days=35)).date()
    with session() as s:   # all the seeded complaints were before shipping
        for r in s.query(FbItem).all():
            r.at = now() - timedelta(days=40)
        for t in s.query(SevaTicket).all():
            t.created_at = now() - timedelta(days=40)
    S.save_settings(T, north_star={"name": "Weekly orders", "target": 300})
    S.update_opportunity(T, fb["number"], goal="north_star")
    S.metric_add(T, "north_star", 100, (ship_day - timedelta(days=5)).isoformat())
    S.metric_add(T, "Weekly orders", 130, (ship_day + timedelta(days=10)).isoformat())
    with pytest.raises(S.ProductError):
        S.metric_add(T, "nahi hai", 5)
    S.ship(T, fb["number"], ship_day.isoformat())
    from app.seva import service as SV
    SV.new_ticket(T, "delivery late", channel="phone", name="A", category="delivery")   # one after
    ba = S.before_after(T, fb["number"])
    fbp = next(p for p in ba["signals"] if p["source"] == "feedback")
    assert fbp["before"] >= 3 and fbp["after"] == 0 and ba["complete"]
    sv = [p for p in ba["signals"] if p["source"] == "seva"]
    assert not sv or sv[0]["after"] == 1
    assert ba["kpi"]["before"] == 100 and ba["kpi"]["after"] == 130 and "behtar" in ba["say"] and "pakka nahi" in ba["say"]
    assert S.opportunity(T, fb["number"])["result"]["complete"]
    m = S.metrics(T)
    assert m["kpis"][0]["latest"] == 130 and m["shipped"][0]["number"] == fb["number"]


def test_tools_actors_and_tick(pm):
    from app.agent.product_tools import PRODUCT_HANDLERS, PRODUCT_TOOLS
    from app.agent.tools import ToolError
    S = pm
    assert {t["name"] for t in PRODUCT_TOOLS} == set(PRODUCT_HANDLERS)
    ctx = conv_ctx()
    run = lambda name, ctx_, **a: asyncio.run(PRODUCT_HANDLERS[name](ctx_, **a))  # noqa: E731
    r = run("product", ctx, action="opportunity", title="Payment fail hota hai")
    assert r["opportunity"]["number"] == "O-001"
    with pytest.raises(ToolError):
        run("product", ctx, action="settings", repo="a/b", rules="token ghp_" + "z" * 30)
    staff = conv_ctx()
    staff.actor = "staff:1"
    run("product", staff, action="idea", text="Hindi mein app chahiye")
    with pytest.raises(ToolError):
        run("product", staff, action="settings", product="x")
    with pytest.raises(ToolError):
        run("product", staff, action="plan", apply=True)
    cust = conv_ctx()
    cust.actor = "customer:wa:91"
    with pytest.raises(ToolError):
        run("product_dekho", cust, what="backlog")
    rd = run("product_dekho", ctx, what="opportunity", ref="O-001")
    assert rd["missing"] and run("product_dekho", ctx, what="rules")["play_max"] == 500
    rel = run("product", ctx, action="release", version="1.0.1", text="Fix: payment fail")
    p = run("product", ctx, action="publish", release=rel["release"]["number"], dest="copy")
    assert p["status"] == "needs_tap"
    # tick: once a day after her morning time
    from app.db import now
    with S.session() as s:
        S._st(s, T).morning_time = "00:00"
    S.EVENTS.clear()
    assert S.tick(now())["tenants"] == 1
    assert "product_day" in kinds(S)
    assert S.tick(now())["tenants"] == 0


def test_api(pm):
    from app.product.api import make_router
    S = pm
    app_ = FastAPI()
    app_.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app_)
    assert c.put("/api/product/settings", json={"product": "Kirana", "capacity": {"now": 2}}).json()["capacity"]["now"] == 2
    o = c.post("/api/product/opportunities", json={"title": "Order tracking"}).json()["opportunity"]
    sc = c.post(f"/api/product/opportunities/{o['number']}/score", json={"reach": 100, "impact": 1, "confidence": 80, "effort": 1}).json()
    assert sc["opportunity"]["score"] == 80.0
    assert c.post(f"/api/product/opportunities/{o['number']}/score", json={"impact": "zz"}).status_code == 400
    c.post(f"/api/product/opportunities/{o['number']}/place", json={"bucket": "now"})
    assert c.get("/api/product/roadmap").json()["buckets"]["now"]["items"][0]["number"] == o["number"]
    sp = c.post(f"/api/product/opportunities/{o['number']}/spec", json={}).json()["spec"]
    assert c.get(f"/api/product/specs/{sp['number']}/tasks").json()["dev_tasks"]
    rel = c.post("/api/product/releases", json={"version": "3.0", "text": "Naya: order tracking"}).json()["release"]
    card = c.post("/api/product/publish", json={"what": "release", "ref": rel["number"], "dest": "page"}).json()["card"]
    assert c.post(f"/api/product/publish/{card['id']}/decide", json={"yes": True, "hash": "x"}).status_code == 400
    d = c.post(f"/api/product/publish/{card['id']}/decide", json={"yes": True, "hash": card["hash"]}).json()
    tok = d["url"].rsplit("/", 1)[1]
    pg = c.get(f"/api/product/page/{tok}")
    assert pg.status_code == 200 and "order tracking" in pg.text.lower() and "default-src 'none'" in pg.headers["content-security-policy"]
    assert c.get("/api/product/page/short").status_code == 404
    assert "settings" in c.get("/api/product").json()
