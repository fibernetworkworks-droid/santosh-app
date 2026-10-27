"""v0.111 Ads Sahayak (performance marketer): reports -> money leaks in rupees -> budget changes with reasons that wait for
her tap (applied through her own Meta account only after it) -> ad copies to test -> a winner only when the numbers say so."""
import asyncio
import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_life import conv_ctx

T = "default"


def _A():
    from app.ads import service as A
    return A


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


def meta_csv(days=14, start=date(2026, 10, 1)) -> bytes:
    lines = ["Day,Campaign name,Ad set name,Amount spent (INR),Impressions,Reach,Frequency,Link clicks,Results,Result indicator"]
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        lines.append(f"{d},Broadband Leads,Pune - Lookalike,300,6000,4000,1.8,90,4,actions:lead")
        lines.append(f"{d},Broadband Leads,Akola - Interest,250,5000,3000,2.0,40,0,actions:lead")
        lines.append(f"{d},Broadband Leads,Nashik - Broad,200,4000,2500,1.9,30,{1 if i % 2 == 0 else 0},actions:lead")
    return "\n".join(lines).encode()


GOOGLE_CSV = ("Search terms report\nOctober 1, 2026 - October 14, 2026\n"
              "Search term,Match type,Campaign,Ad group,Impr.,Clicks,Cost,Conversions\n"
              "free wifi,Broad match,Search - Pune,Broadband,2000,120,900.00,0.00\n"
              "broadband connection pune,Phrase match,Search - Pune,Broadband,1500,140,1200.00,10.00\n"
              "Total: Search terms,,,,3500,260,2100.00,10.00\n").encode()


@pytest.fixture
def setup(env, monkeypatch):
    A = _A()
    monkeypatch.setattr(A, "today", lambda tenant: date(2026, 10, 15))
    A.save_settings(T, business="Asha Fibernet", segment="isp", target_cpl=150, offer="Fibre broadband 100 Mbps Rs 499")
    return A


def test_reading_reports(setup):
    A = setup
    p = A.parse_report("meta.csv", meta_csv())
    assert p["platform"] == "meta" and len(p["rows"]) == 42 and p["rows"][0]["day"] == date(2026, 10, 1)
    g = A.parse_report("terms.csv", GOOGLE_CSV)
    assert g["platform"] == "google" and len(g["rows"]) == 2 and g["rows"][0]["kind"] == "term"   # total line skipped
    assert g["period"] == (date(2026, 10, 1), date(2026, 10, 14))
    with pytest.raises(A.AdsError):
        A.parse_report("x.csv", b"name,phone\nRamesh,98\n")


def test_leaks_winners_and_target(setup):
    A = setup
    A.import_report(T, data=meta_csv(), name="meta.csv")
    r = A.import_report(T, data=GOOGLE_CSV, name="terms.csv")
    rep = r["report"]
    kinds = {(l["kind"], l["name"]) for l in rep["leaks"]}
    assert ("no_result", "Akola - Interest") in kinds
    assert ("high_cpl", "Nashik - Broad") in kinds
    assert any(l["kind"] == "search_terms" and l["terms"][0]["term"] == "free wifi" for l in rep["leaks"])
    assert [w["name"] for w in rep["winners"]] == ["Pune - Lookalike"]
    assert rep["target"] == 150 and rep["target_from"] == "aapka target"
    assert rep["waste"] >= 250 * 14 and "paisa beh raha" in rep["say"]
    # her economics instead of a target: order 6000 x 40 % margin x 10 % close = 240 max, judged at 70 %
    A.save_settings(T, target_cpl=0, avg_order=6000, margin_pct=40, close_pct=10)
    rep2 = A.analyse(T)
    assert rep2["max_cpl"] == 240 and rep2["target"] == 168


def test_plan_waits_for_her_tap_then_steps_or_meta(setup, monkeypatch):
    A = setup
    A.import_report(T, data=meta_csv(), name="meta.csv")
    plan = A.make_plan(T)
    ch = {c["target"]: c for c in plan["changes"]}
    assert ch["Akola - Interest"]["kind"] == "pause" and ch["Nashik - Broad"]["kind"] == "pause"
    up = ch["Pune - Lookalike"]
    assert up["kind"] == "budget" and up["before"] == 300 and up["after"] == 360 and up["spends_more"]
    assert all(c["status"] == "waiting" for c in plan["changes"])
    assert _events("ads_change")[-1]["plan_id"] == plan["plan_id"]
    # no Meta account: Haan gives the Ads Manager steps; she marks it done
    r = A.decide_change(T, ch["Akola - Interest"]["id"], True)
    assert r["change"]["status"] == "manual" and "Ads Manager" in r["change"]["steps"]
    assert A.mark_done(T, ch["Akola - Interest"]["id"])["change"]["status"] == "done"
    with pytest.raises(A.AdsError):
        A.decide_change(T, ch["Akola - Interest"]["id"], True)              # not twice
    assert A.decide_change(T, ch["Nashik - Broad"]["id"], False)["change"]["status"] == "rejected"
    from app import approvekey
    assert A.change_spends(T, up["id"]) and not A.change_spends(T, ch["Nashik - Broad"]["id"])
    assert approvekey.needed(T, "ads", up["id"]) is False                  # no phone key set up yet


def test_meta_account_fetch_and_applied_change(setup, monkeypatch):
    A = setup
    calls = []

    def graph(method, path, token, params=None):
        calls.append((method, path, dict(params or {})))
        if path.endswith("/adsets"):
            return {"data": [{"id": "23850001", "name": "Pune - Lookalike", "status": "ACTIVE", "effective_status": "ACTIVE",
                              "daily_budget": "30000", "campaign": {"name": "Broadband Leads"}},
                             {"id": "23850002", "name": "Akola - Interest", "status": "ACTIVE", "daily_budget": "25000",
                              "campaign": {"name": "Broadband Leads"}}]}
        if path.endswith("/insights"):
            out = []
            for i in range(14):
                d = (date(2026, 10, 1) + timedelta(days=i)).isoformat()
                out.append({"date_start": d, "campaign_name": "Broadband Leads", "adset_id": "23850001", "adset_name": "Pune - Lookalike",
                            "spend": "300", "impressions": "6000", "reach": "4000", "frequency": "1.8", "inline_link_clicks": "90",
                            "actions": [{"action_type": "lead", "value": "4"}]})
                out.append({"date_start": d, "campaign_name": "Broadband Leads", "adset_id": "23850002", "adset_name": "Akola - Interest",
                            "spend": "250", "impressions": "5000", "inline_link_clicks": "40", "actions": []})
            return {"data": out}
        if method == "GET":
            return {"name": "Asha Ads", "currency": "INR", "account_status": 1}
        return {"success": True}
    monkeypatch.setattr(A, "_graph", graph)
    with pytest.raises(A.AdsError):
        A.set_meta(T, "abc", "x" * 50)
    A.set_meta(T, "1234567890", "EAAB" + "x" * 60)
    st = A.settings(T)
    assert st["meta"]["ready"] and "EAAB" not in json.dumps(st)
    f = A.fetch_meta(T, 14)
    assert f["rows"] == 28 and f["adsets"] == 2
    plan = A.make_plan(T)
    ch = {c["target"]: c for c in plan["changes"]}
    assert ch["Akola - Interest"]["can_apply"] and ch["Pune - Lookalike"]["ext_id"] == "23850001"
    posted = [c for c in calls if c[0] == "POST"]
    assert not posted                                                   # nothing changed before her tap
    r = A.decide_change(T, ch["Pune - Lookalike"]["id"], True)
    assert r["change"]["status"] == "applied"
    assert calls[-1] == ("POST", "23850001", {"daily_budget": "36000"})  # paise
    A.decide_change(T, ch["Akola - Interest"]["id"], True)
    assert calls[-1] == ("POST", "23850002", {"status": "PAUSED"})
    # a week later: before / after kept as the lesson
    from app.ads.service import AdsChange, AdsRow
    from app.db import now
    with session() as s:
        c = s.get(AdsChange, ch["Pune - Lookalike"]["id"])
        c.applied_at = now() - timedelta(days=8)
        ad = c.applied_at.date()
        for i in range(1, 8):
            s.add(AdsRow(tenant_id=T, key=f"after{i}", platform="meta", kind="ad", day=ad + timedelta(days=i),
                         campaign="Broadband Leads", adset="Pune - Lookalike", spend=360, impressions=7000, clicks=100, results=4))
    out = A.review_changes(T)
    pune = [o for o in out if o["target"] == "Pune - Lookalike"][0]
    assert pune["outcome"]["cpl_before"] == 75 and pune["outcome"]["cpl_after"] == 90


def test_copies_are_checked_and_never_banned(setup, monkeypatch):
    A = setup

    def ai(system, prompt, max_tokens=2500):
        if "PLATFORM: google" in prompt:
            return json.dumps({"headlines": [{"text": f"Fibre Plan {i}", "angle": "price"} for i in range(10)] +
                               [{"text": "This headline is far too long for Google ads", "angle": "x"}],
                               "descriptions": [{"text": "100 Mbps fibre at Rs 499 a month. Call today.", "angle": "price"},
                                                {"text": "Local team, same week installation.", "angle": "trust"}],
                               "paths": ["broadband", "pune offer!"]})
        return json.dumps({"variants": [
            {"angle": "price", "primary": "100 Mbps fibre sirf Rs 499 mahina. Aaj hi call karein.", "headline": "Fibre Rs 499 mein",
             "description": "Pune mein", "cta": "Call now"},
            {"angle": "proof", "primary": "Hum Pune ke No. 1 broadband hain, 50% off sirf aaj!", "headline": "No. 1 Broadband",
             "description": "Sirf aaj", "cta": "Learn more"},
            {"angle": "too long", "primary": "x" * 200, "headline": "y", "description": "z"}]})
    monkeypatch.setattr(A, "_ai", ai)
    r = A.write_copies(T, "Fibre broadband 100 Mbps Rs 499", "meta", n=4)
    cps = {c["angle"]: c for c in r["test"]["copies"]}
    assert set(cps) == {"price", "proof"} and r["dropped"][0]["why"].startswith("lambi")
    assert not [x for x in cps["price"]["checks"] if "facts mein nahi" in x["text"]]      # 100 / 499 are her facts
    proof = " ".join(x["text"] for x in cps["proof"]["checks"])
    assert "No 1" in proof or "No. 1" in proof
    assert "50" in proof                                                                  # 50 % not in her facts
    g = A.write_copies(T, "Fibre broadband", "google")
    rsa = g["test"]["copies"][0]["fields"]
    assert len(rsa["headlines"]) == 10 and all(len(h["text"]) <= 30 for h in rsa["headlines"]) and rsa["paths"][1] == "pune-offer"
    with pytest.raises(A.AdsError):
        A.write_copies(T, "Rummy khelo aur paise jeeto", "meta")
    assert A.write_copies.__doc__ is None or True
    t = A.test_live(T, r["test"]["number"])
    assert t["test"]["status"] == "running"


def test_winner_only_when_the_difference_is_real(setup):
    A = setup
    from app.ads.service import AdsCopy, AdsTest
    with session() as s:
        t = AdsTest(tenant_id=T, number="T-0099", platform="meta", plan=json.dumps({"min_results_each": 20}))
        s.add(t)
        s.flush()
        for lab in "AB":
            s.add(AdsCopy(tenant_id=T, test_id=t.id, label=lab, angle=lab))
    r = A.test_result(T, "T-0099", {"A": {"impressions": 20000, "clicks": 400, "results": 12, "spend": 2000},
                                    "B": {"impressions": 20000, "clicks": 380, "results": 9, "spend": 2000}})
    assert r["winner"] == "" and "pakka nahi" in r["say"]
    r2 = A.test_result(T, "T-0099", {"A": {"impressions": 40000, "clicks": 1000, "results": 80, "spend": 6000},
                                     "B": {"impressions": 40000, "clicks": 1000, "results": 30, "spend": 6000}})
    assert r2["winner"] == "A" and r2["test"]["status"] == "decided"
    assert A._angle_lessons(T, "meta").startswith("Won: A")


def test_sales_tools_and_api(setup, monkeypatch):
    A = setup
    from app import voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    from app.mailbox import service as ms
    f = ms.store_bytes(T, "meta.csv", meta_csv(), "mail")
    ctx = conv_ctx()

    def run(tool, **a):
        return asyncio.run(HANDLERS[tool](ctx, **a))
    r = run("ads", action="import", file_id=f.id)
    assert r["report"]["leaks"] and r["report"]["waste"] > 0
    A.add_sale(T, "Broadband Leads", 6, 36000)
    assert run("ads_dekho", what="report")["money"]["cost_per_sale"] == round(r["report"]["total"]["spend"] / 6, 2)
    p = run("ads", action="plan")
    assert p["changes"] and "nothing is applied" in p["note"]
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["ads"](Ctx(T, ctx.conversation_id, actor="staff:x"), action="settings", target_cpl=10))
    with pytest.raises(ToolError):
        run("ads", action="done", change="A-9999")
    assert roles.duty_of("ads") == "ads_work" and roles.kind_of("ads_dekho") == "read"
    assert roles.PRESETS["ads"]["role"] == "performance_marketer"
    assert "ads" in voice.VOICE_TOOL_NAMES
    from app import main
    with TestClient(main.app) as c:
        assert "ads" in c.get("/healthz").json()["features"]
        c.put("/api/ads/settings", json={"target_cpl": 150})
        imp = c.post("/api/ads/import", files={"file": ("terms.csv", GOOGLE_CSV, "text/csv")}).json()
        assert imp["platform"] == "google"
        allv = c.get("/api/ads").json()
        assert allv["report"]["leaks"] and allv["changes"]
        cid = allv["changes"][0]["id"]
        d = c.post(f"/api/ads/changes/{cid}/decide", json={"yes": True}).json()
        assert d["change"]["status"] in ("manual", "applied")
        assert c.post("/api/ads/changes/nope/decide", json={"yes": False}).status_code == 400
        assert c.put("/api/ads/settings", json={"segment": "xyz"}).status_code == 400
        assert c.put("/api/ads/meta", json={"account": "1", "token": "short"}).status_code == 400
