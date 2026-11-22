"""G13 SUPPORT REPORTS (docs/SUPPORT_GLOBAL_PLAN.md): requests by channel / country / language / brand / product / queue /
person / topic; solved by Hoola alone vs after a person, reopened; times against the clocks; late by stage;
satisfaction; knowledge gaps grouped; AI credits per request from support's own AI calls; trends against the period
before; the ticket CSV (no formulas), the PDF, the monthly PDF made once on the 1st in her time zone; the page in a browser."""
import os
from datetime import datetime, timedelta, timezone

import pytest

T = "default"


@pytest.fixture
def rp(env, monkeypatch):
    from app.seva import reports as RP
    from app.seva import service as S
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    chat = []
    monkeypatch.setattr(S, "_note_chat", lambda tenant, text, conv="": chat.append(text))
    monkeypatch.setattr(S, "_tell", lambda tenant, tid, text, **k: {"sent": "whatsapp", "text": text})
    box = {"now": datetime(2026, 11, 20, 6, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(S, "clock", lambda: box["now"])
    S.kb_add(T, "What are your timings?", "We are open 10 am to 7 pm, Monday to Saturday.")
    S.box, S.chat = box, chat
    return S, RP


def _fill(S):
    from app.seva import engine as E
    from app.seva import handover as H
    from app.seva import teams as TM
    n1 = S.new_ticket(T, "Router not working since morning", "whatsapp", phone="9811112222", category="technical")["number"]
    n2 = S.new_ticket(T, "=cmd| refund my bill please", "email", customer="email:b@q.com", category="billing")["number"]
    n3 = S.new_ticket(T, "Mi factura está mal, me cobraron dos veces", "email", customer="email:es@q.es", category="billing")["number"]
    TM.save_fields(T, [{"label": "Brand", "type": "text"}])
    TM.set_custom(T, n1, {"brand": "FastNet"})
    S.update(T, n1, status="resolved")
    H.start(T, "email:b@q.com", "email", "the customer asked", "asked", "refund", ref=n2)
    S.update(T, n2, status="resolved", assignee="Ravi")
    from app.db import session
    with session() as s:
        t = s.query(S.SevaTicket).filter_by(number=n1).first()
        t.csat, t.reopens = 5, 1
        s.query(S.SevaTicket).filter_by(number=n2).first().csat = 2
    for q in ("Do you deliver to Pune?", "Do you deliver to Pune city?", "Can I pay in instalments?"):
        E.reply(T, q, "whatsapp", "", "test")
    E.reply(T, "What are your timings?", "whatsapp", "", "test")
    return n1, n2, n3


def test_the_report(rp):
    S, RP = rp
    n1, n2, n3 = _fill(S)
    r = RP.build(T, 30)
    h = {x["key"]: x for x in r["headline"]}
    assert h["tickets"]["now"] == 3 and h["solved_hoola"]["now"] == 1 and h["solved_person"]["now"] == 1
    assert h["handed_over"]["now"] == 1 and h["reopened"]["now"] == 1 and h["answered_alone"]["now"] == 1
    by = {k: {x["key"]: x["count"] for x in v} for k, v in r["by"].items()}
    assert by["channel"] == {"email": 2, "whatsapp": 1} and by["country"].get("IN") == 1 and by["language"].get("es") == 1
    assert by["brand"].get("FastNet") == 1 and by["person"].get("Ravi") == 1
    assert r["csat"]["count"] == 2 and r["csat"]["avg"] == 3.5 and r["csat"]["happy_pct"] == 50 and r["csat"]["spread"]["2"] == 1
    gaps = {g["question"]: g["times"] for g in r["gaps"]}
    assert any("deliver to Pune" in q and t == 2 for q, t in gaps.items()) and any("instalments" in q for q in gaps)
    assert "3 requests" in r["say"] and "1 solved by Hoola alone, 1 after a person" in r["say"]
    assert h["tickets"]["before"] == 0 and h["tickets"]["change_pct"] is None


def test_trends_and_cost_per_request(rp):
    S, RP = rp
    from app import usage
    from app.db import session
    S.new_ticket(T, "Old problem one", "email", customer="email:o1@q.com")
    S.new_ticket(T, "Old problem two", "email", customer="email:o2@q.com")
    S.box["now"] += timedelta(days=30)
    _fill(S)
    with session() as s:
        s.add(usage.UsageDay(tenant_id=T, day=S.box["now"].date().isoformat(), feature="support", model="m", usd=0.03))
        s.add(usage.UsageDay(tenant_id=T, day=S.box["now"].date().isoformat(), feature="chat", model="m", usd=5.0))     # not support
    r = RP.build(T, 30)
    h = {x["key"]: x for x in r["headline"]}
    assert h["tickets"]["now"] == 3 and h["tickets"]["before"] == 2 and h["tickets"]["change_pct"] == 50
    assert r["cost"]["credits"] == 30 and r["cost"]["per_ticket"] == 10.0 and "labelled support" in r["cost"]["note"]
    assert usage.feature_for_path("/api/seva/tickets") == "support" and usage.feature_for_path("/api/support/web/k/session") == "support"


def test_late_by_stage(rp):
    S, RP = rp
    from app.seva import profile as PF
    pv = PF.preview(T, {"industry": "telecom"})
    PF.apply(T, {"industry": "telecom"}, pv["hash"])
    S.new_ticket(T, "My fibre line is down since yesterday", "whatsapp", phone="9822223333")
    S.box["now"] += timedelta(days=5)
    late = RP.build(T, 30)["late_by_stage"]
    assert late and late[0]["count"] == 1 and late[0]["key"] != "(no stage)"


def test_csv_and_pdf(rp):
    S, RP = rp
    _fill(S)
    csv = RP.tickets_csv(T, 30)
    lines = csv.strip().splitlines()
    assert lines[0].startswith("number,created,channel,country,language") and len(lines) == 4
    assert ",=" not in csv and "\n=" not in csv
    pdf = RP.pdf(T, 30)
    assert pdf[:5] == b"%PDF-" and len(pdf) > 2000
    from pypdf import PdfReader
    import io
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    assert "Customer support report" in text and "Requests by channel" in text and "Satisfaction" in text and "deliver to Pune" in text


def test_monthly_pdf_once_on_the_first(rp):
    S, RP = rp
    S.box["now"] = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
    _fill(S)
    assert RP.make_monthly(T, datetime(2026, 11, 15, 6, 0, tzinfo=timezone.utc)) is None             # not the 1st
    S.box["now"] = datetime(2026, 11, 1, 3, 0, tzinfo=timezone.utc)                                   # 1 Nov, 08:30 in India
    got = RP.make_monthly(T, S.box["now"])
    assert got and got["month"] == "2026-10" and "3 requests" in got["say"]
    assert RP.make_monthly(T, S.box["now"]) is None                                                    # once
    assert RP.monthly_pdf(T, "2026-10")[:5] == b"%PDF-" and RP.monthlies(T)[0]["month"] == "2026-10"
    assert any("2026-10 is ready" in c for c in S.chat)
    with pytest.raises(ValueError):
        RP.monthly_pdf(T, "2025-01")
    assert RP.make_monthly("empty-shop", S.box["now"]) is None                                         # nothing that month: no PDF


def test_routes_and_tool(rp):
    S, RP = rp
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.seva.api import make_router
    _fill(S)
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: T))
    cl = TestClient(a)
    r = cl.get("/api/seva/reports/full?days=30").json()
    assert r["headline"][0]["now"] == 3
    assert cl.get("/api/seva/reports/tickets.csv").headers["content-type"].startswith("text/csv")
    assert cl.get("/api/seva/reports/report.pdf").content[:5] == b"%PDF-"
    m = cl.post("/api/seva/reports/monthly").json()
    assert m["monthly"] and cl.get(f"/api/seva/reports/monthly/{m['monthly'][0]['month']}.pdf").content[:5] == b"%PDF-"
    assert cl.get("/api/seva/reports/monthly/bad.pdf").status_code == 400
    import inspect
    from app.agent import seva_tools as ST
    assert 'what == "reports"' in inspect.getsource(ST)


# ---------------------------------------------------------------- the Reports page in a real browser
@pytest.fixture
def r_server(rp, monkeypatch):
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
    S, RP = rp
    _fill(S)
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
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_reports_page_in_a_real_browser(r_server):
    base, browser, key = r_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/support#/reports")
    pg.wait_for_selector("[data-by=country]")
    txt = pg.inner_text("#spPage").lower()
    assert "solved by hoola alone" in txt and "satisfaction" in txt and "ai cost" in txt
    pg.click("[data-by=language]")
    pg.wait_for_function("() => document.querySelector('[data-by=language]').getAttribute('aria-pressed') === 'true'", timeout=15000)
    assert "es" in pg.inner_text("#spPage")
    with pg.expect_download() as dl:
        pg.click("[data-dl*='report.pdf']")
    assert open(dl.value.path(), "rb").read()[:5] == b"%PDF-"
    with pg.expect_download() as dl2:
        pg.click("[data-dl*='tickets.csv']")
    assert open(dl2.value.path()).read().startswith("number,")
    with pg.expect_response(lambda r: r.url.endswith("/api/seva/reports/monthly") and r.request.method == "POST"):
        pg.click("[data-act=monthnow]")
    pg.wait_for_selector("[data-dl*='/monthly/']")
    ctx.close()
    m = browser.new_context(viewport={"width": 390, "height": 900})
    m.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    mp = m.new_page()
    mp.on("pageerror", lambda e: errors.append(str(e)))
    mp.goto(base + "/console/support#/reports")
    mp.wait_for_selector("[data-by=country]")
    assert mp.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    m.close()
    assert not errors, errors
