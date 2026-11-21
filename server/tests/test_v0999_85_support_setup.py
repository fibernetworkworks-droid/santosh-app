"""v0.999.86 SUPPORT SETUP (built as 0.999.82) (G0 of docs/SUPPORT_GLOBAL_PLAN.md): 8 setup answers -> a profile + one of 15 industry packs
(categories, urgent words, reply times, workflow templates, policy starting values, knowledge questions, saved-reply
starters, law notes with sources). Nothing changes until her tap on the preview's hash; a pack only fills what she left
empty; saved replies arrive as drafts; law notes are shown, never applied. Walked in a real browser."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)

T = "default"


@pytest.fixture
def sv(env, monkeypatch):
    from app.seva import service as S
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    from app import supportchat as SC
    SC._OF.clear()
    SC._BLOCK.clear()
    return S


def test_fifteen_packs_are_whole():
    from app.seva import profile as PF
    ps = PF._packs()
    assert len(ps) == 15
    for k in ("shop", "online_store", "restaurant", "clinic", "telecom", "utility", "finance", "saas", "travel", "logistics",
              "education", "government", "real_estate", "automotive", "other"):
        assert k in ps, k
    bad = [b for p in ps.values() for b in PF.check_pack(p)]
    assert bad == []
    for p in ps.values():
        assert p["flows"] and p["knowledge_questions"] and p["saved_replies"]
        assert all(l["status"] == "check" and l["source"] for l in p["law"])     # nothing claimed as verified
        assert any(l["id"] == "ai" for l in p["law"])                            # AI disclosure everywhere


def test_check_pack_catches_a_broken_workflow():
    from app.seva import profile as PF
    import copy
    p = copy.deepcopy(PF.pack("telecom"))
    p["flows"][0]["arrows"]["new"] = ["nowhere"]
    p["flows"][0]["stages"][1]["owner"] = "boss"
    bad = PF.check_pack(p)
    assert any("arrow new" in b for b in bad) and any("owner boss" in b for b in bad)


def test_clean_and_derive(sv):
    from app.seva import profile as PF
    a = PF.clean(T, {})
    assert a["size"] == "me" and a["industry"] == "other" and a["countries"] and a["languages"] == ["English"]
    p = PF.derive(a)
    assert p["tier"] == "small" and p["mode"] == "own" and not p["parts"]["queues"] and not p["parts"]["workflow_designer"]
    big = PF.clean(T, {"size": "enterprise", "industry": "finance", "countries": ["DE", "us", "XX"], "languages": ["German", "Klingon"],
                       "helpdesk": "zendesk", "team": {"people": 400, "split": ["shifts", "language", "nope"]},
                       "money": {"agent": 50, "supervisor": 500, "currency": "eur"}, "data": "salesforce"})
    assert big["countries"] == ["DE", "US"] and big["languages"] == ["German"] and big["team"]["split"] == ["shifts", "language"]
    bp = PF.derive(big)
    assert bp["tier"] == "enterprise" and bp["mode"] == "layer" and bp["currency"] == "EUR"
    assert all(bp["parts"][k] for k in ("queues", "shifts", "workflow_designer", "approval_chain", "trust_controls",
                                         "several_countries", "live_lookups"))
    with pytest.raises(PF.ProfileError):
        PF.clean(T, {"money": {"agent": 500, "supervisor": 50}})
    assert PF.derive(PF.clean(T, {"size": "me", "team": {"people": 3}}))["tier"] == "team"


def test_preview_changes_nothing_and_apply_needs_the_hash(sv):
    from app.seva import profile as PF
    S = sv
    before = S.settings(T)
    ans = {"size": "small_team", "industry": "telecom", "countries": ["IN"], "languages": ["English", "Hindi"]}
    pv = PF.preview(T, ans)
    assert pv["hash"] and any(c["what"] == "Reply times" for c in pv["changes"])
    assert S.settings(T) == before and PF.get(T) == {}
    with pytest.raises(PF.ProfileError):
        PF.apply(T, ans, "wrong")
    with pytest.raises(PF.ProfileError):                      # answers changed after the preview
        PF.apply(T, dict(ans, industry="clinic"), pv["hash"])
    out = PF.apply(T, ans, pv["hash"])
    assert out["done"] and out["pack"]["name"] == "Internet / telecom"
    st = S.settings(T)
    assert st["kind"] == "isp" and st["sla"]["urgent"] == [1.0, 8.0]
    drafts = [m for m in S.macros(T)]
    assert {m["name"] for m in drafts} >= {"Outage in area", "Restart steps"}
    assert all(m["status"] == "draft" for m in drafts if m["name"] in ("Outage in area", "Restart steps")), drafts
    assert "Internet / telecom" in PF.line(T)


def test_apply_keeps_what_she_set(sv):
    from app.seva import profile as PF
    S = sv
    S.save_settings(T, sla={"urgent": [0.5, 2]}, refund_days=3)
    S.macro_add(T, "Return policy", "Our own wording: [days].")
    ans = {"industry": "shop"}
    pv = PF.preview(T, ans)
    assert not any(c["what"] == "Reply times" for c in pv["changes"])
    PF.apply(T, ans, pv["hash"])
    st = S.settings(T)
    assert st["sla"]["urgent"] == [0.5, 2.0] and st["policy"]["refund_days"] == 3 and st["policy"]["replace_days"] == 7
    assert [m for m in S.macros(T) if m["name"] == "Return policy"][0]["texts"]
    assert "Our own wording" in str([m for m in S.macros(T) if m["name"] == "Return policy"][0]["texts"])


def test_pack_categories_and_urgent_words_sort_tickets(sv):
    from app.seva import profile as PF
    S = sv
    pv = PF.preview(T, {"industry": "clinic"})
    PF.apply(T, {"industry": "clinic"}, pv["hash"])
    t = S.new_ticket(T, "I need to reschedule my appointment with the doctor", "whatsapp", name="Ana")
    assert t["ticket"]["category"] == "appointment" and t["ticket"]["category_label"] == "Appointment"
    u = S.new_ticket(T, "my father has chest pain what do i do", "phone", name="Ben")
    assert u["ticket"]["priority"] == "urgent"


def test_law_notes_follow_her_countries(sv):
    from app.seva import profile as PF
    for ans, want, never in (({"industry": "finance", "countries": ["GB"]}, "fca", "rege"),
                             ({"industry": "finance", "countries": ["US"]}, "rege", "fca"),
                             ({"industry": "online_store", "countries": ["IN"]}, "ecom_in", "eu_odr")):
        pv = PF.preview(T, ans)
        PF.apply(T, ans, pv["hash"])
        ids = {l["id"] for l in PF.view(T)["pack"]["law"]}
        assert want in ids and never not in ids, (ans, ids)


def test_routes_and_wiring(sv):
    from pathlib import Path
    from app.employee import hire
    from app import supportchat as SC
    from app.main import app
    hire.hire(T, "support", trust="seekh")
    c = TestClient(app)
    r = c.get("/api/support/setup").json()
    assert r["done"] is False and len(r["questions"]) == 9 and len(r["packs"]) == 15 and len(r["countries"]) > 200
    assert SC.summary(T)["setup_done"] is False
    pv = c.post("/api/support/setup/preview", json={"answers": {"industry": "saas", "countries": ["US", "DE"]}}).json()
    assert c.post("/api/support/setup/apply", json={"answers": {"industry": "saas"}, "hash": pv["hash"]}).status_code == 409
    ok = c.post("/api/support/setup/apply", json={"answers": pv["answers"], "hash": pv["hash"]})
    assert ok.status_code == 200 and ok.json()["done"]
    assert SC.summary(T)["setup_done"] is True and "Software / SaaS" in SC.block(T)
    js = (Path(__file__).resolve().parents[1] / "app/static/console/supportdesk.js").read_text()
    for w in ("pageSetup", "/api/support/setup/preview", "/api/support/setup/apply", "applysetup", "Start setup"):
        assert w in js, w


@pytest.fixture
def su_server(sv, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "support", trust="seekh")
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_setup_in_a_real_browser(su_server):
    base, browser, key = su_server
    errors = []
    for width in (1440, 390):
        ctx = browser.new_context(viewport={"width": width, "height": 900})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/support")
        pg.wait_for_selector("#spSetupCard a[href='#/setup']", timeout=20000)
        pg.click("#spSetupCard a[href='#/setup']")
        pg.wait_for_selector("#spSetup")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        ctx.close()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/support#/setup")
    pg.wait_for_selector("#spSetup")
    pg.check("#spSetup input[name=size][value=teams]")
    pg.select_option("#spSetup select[name=industry]", "online_store")
    pg.wait_for_function("() => document.querySelector('#spPackNote').innerText.includes('Return')")
    pg.fill("#spCtryFind", "germ")
    pg.select_option("#spCtry", ["DE", "IN"])
    pg.check("#spSetup input[name=languages][value=German]")
    pg.fill("#spSetup input[name=agent]", "20")
    pg.fill("#spSetup input[name=supervisor]", "200")
    pg.click("#spSetup button[type=submit]")
    pg.wait_for_selector("[data-act=applysetup]", timeout=10000)
    assert "Online store" in pg.inner_text("#spPreview")
    pg.click("[data-act=applysetup]")
    pg.wait_for_function("() => location.hash === '#/today'", timeout=10000)
    pg.wait_for_function("() => !document.querySelector('#spSetupCard')", timeout=10000)
    pg.click("#sdTabs [data-tab='settings']")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Rules that may apply')", timeout=10000)
    txt = pg.inner_text("#spPage")
    assert "Online store" in txt and "Check this" in txt and "2013/11/EU" in txt
    pg.click("#sdTabs [data-tab='knowledge']")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Questions most businesses like yours answer')", timeout=10000)
    ctx.close()
    assert not errors, errors
