"""v0.806 BAHI A0 - the GST & Accounts employee's foundation (owner: 'GO A0'; docs/ACCOUNTS_EMPLOYEE_PLAN.md).

What A0 promises and these tests hold:
- the WhiteBooks client keeps the SPEC's contract: client_id / client_secret headers + `email` query on every call, the sandbox host
  by default, success ONLY on status_cd "1" (HTTP 200 carries failures), WB_ERR codes in plain English, no password / OTP in a log
  line, a per-tenant daily cap + per-minute guard that refuse BEFORE the call, every call metered;
- the contract check records reply SHAPES with no values and never makes a taxpayer call in production;
- rules live as data with source / basis / checked_on / review_by; unverified rows are flagged, never computed with;
- the register reads the engines Hoola already has, once per document, flags a document entered in two places, holds a change to a
  locked month instead of applying it, marks (never deletes) what its source dropped, and writes an append-only trail;
- the desk + routes + Hub entry + console page are wired; nothing files, pays or returns a secret."""
import json
import re
from datetime import date
from pathlib import Path

import httpx
import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"


@pytest.fixture
def wbenv(env, monkeypatch):
    monkeypatch.setenv("WHITEBOOKS_EMAIL", "dev@example.com")
    monkeypatch.setenv("WHITEBOOKS_GST_CLIENT_ID", "cid-123")
    monkeypatch.setenv("WHITEBOOKS_GST_CLIENT_SECRET", "sec-456")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bahi import wb
    wb._MINUTE.clear()
    yield wb
    wb.TRANSPORT = None
    get_settings.cache_clear()


def _transport(handler):
    return httpx.MockTransport(handler)


# ---------------------------------------------------------------- the WhiteBooks client
def test_every_call_carries_the_spec_headers_email_and_sandbox_host(wbenv):
    wb = wbenv
    seen = {}

    def h(req: httpx.Request):
        seen.update(url=str(req.url), headers=dict(req.headers))
        return httpx.Response(200, json={"status_cd": "1", "status_desc": "ok", "data": {"gstin": "27AAAAA0000A1Z5", "sts": "Active"}})
    wb.TRANSPORT = _transport(h)
    env_ = wb.public_search("t1", "27aaaaa0000a1z5")
    assert wb.data_of(env_)["sts"] == "Active"
    assert seen["url"].startswith("https://apisandbox.whitebooks.in/public/search?")
    assert "email=dev%40example.com" in seen["url"] and "gstin=27AAAAA0000A1Z5" in seen["url"]
    assert seen["headers"]["client_id"] == "cid-123" and seen["headers"]["client_secret"] == "sec-456"
    assert wb.calls_today("t1") == 1                                          # metered


def test_failure_rides_http_200_and_becomes_plain_english(wbenv):
    wb = wbenv
    wb.TRANSPORT = _transport(lambda r: httpx.Response(200, json={
        "status_cd": "0", "status_desc": "WB_ERR_9001 : Invalid credentials provided or your account is not active"}))
    with pytest.raises(wb.WbError) as e:
        wb.public_search("t1", "27AAAAA0000A1Z5")
    assert e.value.code == "WB_ERR_9001" and "keys" in e.value.message and "WHITEBOOKS_" in e.value.message
    wb.TRANSPORT = _transport(lambda r: httpx.Response(200, json={"status_cd": "0", "error": {"error_cd": "2150", "message": "Duplicate IRN"}}))
    with pytest.raises(wb.WbError) as e:
        wb.public_search("t1", "27AAAAA0000A1Z5")
    assert e.value.code == "2150" and "IRN" in e.value.message
    wb.TRANSPORT = _transport(lambda r: httpx.Response(500, text="<html>oops</html>"))
    with pytest.raises(wb.WbError) as e:
        wb.public_search("t1", "27AAAAA0000A1Z5")
    assert e.value.code == "bad_reply"


def test_not_configured_and_caps_refuse_before_any_call(wbenv, monkeypatch):
    wb = wbenv
    hits = []
    wb.TRANSPORT = _transport(lambda r: (hits.append(1), httpx.Response(200, json={"status_cd": "1"}))[1])
    monkeypatch.setenv("WHITEBOOKS_DAILY_CALLS", "2")
    monkeypatch.setenv("WHITEBOOKS_PER_MINUTE", "0")
    from app.config import get_settings
    get_settings.cache_clear()
    wb.public_search("t2", "27AAAAA0000A1Z5")
    wb.public_search("t2", "27AAAAA0000A1Z5")
    with pytest.raises(wb.WbError) as e:
        wb.public_search("t2", "27AAAAA0000A1Z5")
    assert e.value.code == "cap" and len(hits) == 2                         # refused BEFORE the call, nothing sent
    assert wb.calls_today("t3") == 0                                         # the cap is per tenant
    monkeypatch.setenv("WHITEBOOKS_DAILY_CALLS", "0")
    monkeypatch.setenv("WHITEBOOKS_PER_MINUTE", "1")
    get_settings.cache_clear()
    wb._MINUTE.clear()
    wb.public_search("t4", "27AAAAA0000A1Z5")
    with pytest.raises(wb.WbError) as e:
        wb.public_search("t4", "27AAAAA0000A1Z5")
    assert e.value.code == "rate"
    monkeypatch.setenv("WHITEBOOKS_GST_CLIENT_SECRET", "")
    get_settings.cache_clear()
    with pytest.raises(wb.WbError) as e:
        wb.public_search("t5", "27AAAAA0000A1Z5")
    assert e.value.code == "not_configured"
    assert wb.status()["products"]["gst"] is False and "sec" not in json.dumps(wb.status())


def test_no_password_or_otp_reaches_a_log_line(wbenv, caplog):
    wb = wbenv
    wb.TRANSPORT = _transport(lambda r: httpx.Response(200, json={"status_cd": "1", "data": {}}))
    caplog.set_level("INFO", logger="bahi.wb")
    wb.ewb_auth("t1", "27AAAAA0000A1Z5", "API_shop", "S3cretPass!")
    wb.auth_token("t1", "user1", "27", "txn-9", "575757")
    text = caplog.text
    assert "S3cretPass!" not in text and "575757" not in text and "sec-456" not in text
    assert "password=%2A%2A%2A" in text or "password=***" in text
    assert wb.safe_url("https://x/y", {"evcotp": "123456", "gstin": "G"}).count("123456") == 0


def test_shape_keeps_structure_never_values(wbenv):
    wb = wbenv
    s = wb.shape({"txn": "abc123", "data": [{"irn": "f00", "ack": 12}], "ok": True, "n": None})
    assert s == {"txn": "str", "data": [{"irn": "str", "ack": "int"}], "ok": "bool", "n": "null"}
    assert "abc123" not in json.dumps(s)
    assert wb.find_txn({"status_cd": "1", "header": {"txn": "T-77"}}) == "T-77"
    assert wb.find_txn({"status_cd": "1", "data": json.dumps({"txn": "T-88"})}) == "T-88"


def test_contract_check_walks_the_sandbox_and_records_shapes(wbenv, monkeypatch):
    wb = wbenv
    monkeypatch.setenv("WHITEBOOKS_SANDBOX_GSTIN", "29AAGCB1286Q000")
    monkeypatch.setenv("WHITEBOOKS_SANDBOX_GST_USERNAME", "sandbox_user")
    from app.config import get_settings
    get_settings.cache_clear()
    paths = []

    def h(req: httpx.Request):
        paths.append(req.url.path)
        if req.url.path == "/":
            return httpx.Response(200, json={"message": "I-HUB is up and running!", "version": "2.0.0"})
        if req.url.path == "/authentication/otprequest":
            return httpx.Response(200, json={"status_cd": "1", "header": {"txn": "TXN-1"}})
        if req.url.path == "/authentication/authtoken":
            assert req.url.params["otp"] == "575757" and req.headers["txn"] == "TXN-1"
        return httpx.Response(200, json={"status_cd": "1", "data": {"value": 1}})
    wb.TRANSPORT = _transport(h)
    from app.bahi import wbcheck
    res = wbcheck.run(today=date(2026, 11, 11))
    got = {s["step"]: s["result"] for s in res["steps"]}
    assert got["ping"] == got["public_search"] == got["otp_request"] == got["auth_token"] == got["refresh"] == got["ledger_balance"] == "PASS"
    assert got["einv_auth"] == "SKIP" and got["ewb_auth"] == "SKIP"           # their sandbox logins are not set
    assert res["shapes"]["otp_request"]["envelope"]["header"] == {"txn": "str"}
    saved = wbcheck.last()
    assert saved["passed"] == res["passed"] and "TXN-1" not in json.dumps(saved) and "575757" not in json.dumps(saved)
    # production: the ping only - no taxpayer call, no OTP, ever
    monkeypatch.setenv("WHITEBOOKS_ENV", "production")
    get_settings.cache_clear()
    paths.clear()
    res = wbcheck.run(today=date(2026, 11, 11))
    assert paths == ["/"] and not any(p.startswith("/authentication") for p in paths)


# ---------------------------------------------------------------- rules as data
def test_every_rule_row_says_where_it_came_from():
    from app.bahi import rules as RU
    for n in RU.NAMES:
        for r in RU.rows(n):
            assert r["basis"] in RU.BASES and r["source"] and re.match(r"\d{4}-\d{2}-\d{2}$", r["checked_on"]), (n, r["id"])
    assert RU.slabs_on("2025-09-21") == [0, 0.25, 3, 5, 12, 18, 28]
    assert RU.slabs_on("2025-09-22") == [0, 0.25, 3, 5, 18, 40]              # GST 2.0
    assert not RU.usable(RU.row("due_dates", "tds_deposit")) and RU.usable(RU.row("due_dates", "gstr3b"))
    f = RU.freshness(date(2026, 11, 11))
    assert f["total"] == sum(f["by_basis"].values()) and f["unverified"] and not f["stale"]
    assert RU.freshness(date(2028, 1, 1))["stale"]                             # past review_by = due for a re-check
    assert RU.row("forms_map", "26Q")["new"] == "140"


def test_the_month_calendar():
    from app.bahi import rules as RU
    d = {x["id"]: x for x in RU.dues_for("2026-10", today=date(2026, 11, 11))}
    assert d["gstr1"]["date"] == "2026-11-11" and d["gstr1"]["days_left"] == 0
    assert d["gstr3b"]["date"] == "2026-11-20" and d["gstr3b"]["days_left"] == 9 and "LOCKED" in d["gstr3b"]["what"]
    assert "pf_esi" not in d and "tds_deposit" not in d and "pmt06" not in d   # not an employer / deductor / QRMP filer
    q = {x["id"] for x in RU.dues_for("2026-10", scheme="qrmp", employer=True, tds=True, today=date(2026, 11, 11))}
    assert {"iff", "pmt06", "pf_esi", "tds_deposit"} <= q and "gstr1" not in q
    assert {x["id"]: x for x in RU.dues_for("2026-03", tds=True)}["tds_deposit"]["date"] == "2026-04-30"


# ---------------------------------------------------------------- the register
def _seed(tenant="default"):
    from app.db import session
    from app.gstp.service import GstClient, GstDoc
    from app.office.service import OfficeBill, OfficeVendor
    from app.thok.service import ThokOrder, ThokParty, ThokPurchase, ThokSettings
    with session() as s:
        c = GstClient(tenant_id=tenant, name="Shree Traders", gstin="27AAAAA0000A1Z5", state="27")
        s.add(c)
        s.flush()
        s.add(GstDoc(tenant_id=tenant, client_id=c.id, period="2026-10", direction="out", kind="inv", number="INV-7",
                     doc_date="2026-10-05", party_gstin="27BBBBB1111B1Z5", party_name="Kumar Stores", txval=1000, cgst=90, sgst=90, value=1180))
        s.add(GstDoc(tenant_id=tenant, client_id=c.id, period="2026-10", direction="in", kind="inv", number="P/55",
                     doc_date="2026-10-08", party_gstin="27CCCCC2222C1Z5", party_name="Mill Supply", txval=500, igst=90, value=590))
        s.add(ThokSettings(tenant_id=tenant, gstin="27AAAAA0000A1Z5", state="27"))
        p = ThokParty(tenant_id=tenant, kind="supplier", name="Mill Supply", gstin="27CCCCC2222C1Z5", state="27")
        q = ThokParty(tenant_id=tenant, kind="customer", name="Gupta Mart", gstin="", state="27")
        s.add_all([p, q])
        s.flush()
        s.add(ThokPurchase(tenant_id=tenant, supplier_id=p.id, bill_no="P-55", bill_date="2026-10-08", taxable=500, tax=90, total=590))
        s.add(ThokOrder(tenant_id=tenant, party_id=q.id, number="TS/26-27/0004", status="billed", bill_date="2026-10-12",
                        taxable=2000, tax=360, total=2360, intra=True))
        s.add(ThokOrder(tenant_id=tenant, party_id=q.id, number="TS/26-27/0005", status="draft", bill_date="2026-10-13", taxable=1, tax=0, total=1))
        v = OfficeVendor(tenant_id=tenant, name="Airtel", gstin="27DDDDD3333D1Z5")
        s.add(v)
        s.flush()
        s.add(OfficeBill(tenant_id=tenant, vendor_id=v.id, number="AT-991", bill_date="2026-10-02", amount_paise=118000, gst_paise=18000, what="Broadband"))
        s.commit()


def test_register_reads_every_engine_once_and_flags_doubles(env):
    from app.bahi import register as REG
    _seed()
    r = REG.sync("default", months=["2026-10"])
    assert r["errors"] == {} and r["added"] == 5 and r["by_source"] == {"gst_sahayak": 2, "thok": 2, "office": 1, "app": 0}
    again = REG.sync("default", months=["2026-10"])
    assert again["added"] == 0 and again["unchanged"] == 5                  # idempotent
    rows = REG.listing("default", period="2026-10")
    assert len(rows) == 5
    thok_sale = next(x for x in rows if x["number"] == "TS/26-27/0004")
    assert thok_sale["cgst"] == 180 and thok_sale["sgst"] == 180 and thok_sale["source_name"] == "Wholesale (Thok)"
    assert not any(x["number"] == "TS/26-27/0005" for x in rows)             # a draft order is not a document
    dup = [x for x in rows if any(p["kind"] == "duplicate" for p in x["problems"])]
    assert {x["number"] for x in dup} == {"P/55", "P-55"}                   # same bill typed in GST Sahayak AND Thok: both flagged
    s = REG.summary("default", "2026-10")
    assert s["sales"]["count"] == 2 and s["sales"]["tax"] == 540 and s["purchases"]["count"] == 3 and s["problems"] == 2


def test_locked_month_holds_changes_and_dropped_rows_are_marked(env):
    from app.bahi import register as REG
    from app.db import session
    from app.gstp.service import GstDoc
    from sqlalchemy import select
    _seed()
    REG.sync("default", months=["2026-10"])
    REG.set_lock("default", "2026-10", True, note="filed")
    with session() as s:
        d = s.scalars(select(GstDoc).where(GstDoc.number == "INV-7")).first()
        d.txval, d.cgst, d.sgst, d.value = 2000, 180, 180, 2360
        s.commit()
    r = REG.sync("default", months=["2026-10"])
    assert r["held_locked"] == 1 and r["changed"] == 0
    row = next(x for x in REG.listing("default", period="2026-10") if x["number"] == "INV-7")
    assert row["taxable"] == 1000 and any(p["kind"] == "changed_after_lock" for p in row["problems"])   # locked figures kept
    REG.set_lock("default", "2026-10", False)
    r = REG.sync("default", months=["2026-10"])
    assert r["changed"] == 1
    with session() as s:
        s.delete(s.scalars(select(GstDoc).where(GstDoc.number == "INV-7")).first())
        s.commit()
    r = REG.sync("default", months=["2026-10"])
    assert r["gone"] == 1
    gone = next(x for x in REG.listing("default", period="2026-10") if x["number"] == "INV-7")
    assert gone["status"] == "gone"                                          # marked, never deleted
    evs = REG.events("default", 50)
    whats = [e["what"] for e in evs]
    assert any(e["label"] == "GST Sahayak · INV-7 · Kumar Stores" for e in evs)      # the trail shows documents, never internal ids
    assert not any(re.search(r"\b(gd|ob|tb|to)_[0-9a-f]{6}", e["label"]) for e in evs)
    for w in ("added", "lock", "change_held_locked", "unlock", "changed", "gone_at_source"):
        assert w in whats, w


# ---------------------------------------------------------------- the desk, the routes, the Hub
def test_routes_overview_and_no_secret_ever(env, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    monkeypatch.setenv("WHITEBOOKS_EMAIL", "dev@example.com")
    monkeypatch.setenv("WHITEBOOKS_GST_CLIENT_ID", "cid-123")
    monkeypatch.setenv("WHITEBOOKS_GST_CLIENT_SECRET", "sec-456")
    from app.config import get_settings
    get_settings.cache_clear()
    _seed()
    c = TestClient(app)
    assert c.post("/api/bahi/sync", json={"months": ["2026-10"]}).json()["added"] == 5
    ov = c.get("/api/bahi/overview")
    assert ov.status_code == 200
    body = ov.text
    assert "sec-456" not in body and "cid-123" not in body and "dev@example.com" not in body
    o = ov.json()
    assert o["whitebooks"]["products"]["gst"] is True and o["whitebooks"]["env"] == "sandbox" and o["filing"] is False
    assert o["employee"]["key"] == "accounts" and [p["state"] for p in o["phases"]][:2] == ["built", "next"]
    assert c.get("/api/bahi/register", params={"period": "2026-10", "direction": "in"}).json()["rows"][0]["direction"] == "in"
    assert c.post("/api/bahi/periods/2026-13x/lock", json={"on": True}).status_code == 400
    assert c.post("/api/bahi/periods/2026-10/lock", json={"on": True}).json()["state"] == "locked"
    assert c.get("/api/bahi/rules").json()["freshness"]["total"] > 10
    get_settings.cache_clear()


def test_hub_entry_live_and_gates_nothing(env):
    from app.employee import hire
    cat = hire.CATALOG["accounts"]
    assert cat["live"] is True and cat["name"] == "GST & Accounts" and cat["does"] and cat["needs"] and cat["never"]
    assert any("OTP" in x for x in cat["never"]) and any("money" in x.lower() for x in cat["never"])
    agent = ROOT / "server" / "app" / "agent"
    for f in ("gst_tools.py",):
        assert "is_hired" not in (agent / f).read_text(encoding="utf-8")       # hiring adds the desk, never gates GST Sahayak
    hire.hire("default", "accounts", "seekh")
    assert hire.status("default", "accounts") == "hired"


def test_console_wiring_and_css():
    html = (CON / "v2.html").read_text(encoding="utf-8")
    v2 = (CON / "v2.js").read_text(encoding="utf-8")
    emp = (CON / "employees.js").read_text(encoding="utf-8")
    js = (CON / "bahi.js").read_text(encoding="utf-8")
    css = (CON / "v2.css").read_text(encoding="utf-8")
    assert '<section class="view" id="v-accountsdesk"' in html and "/static/console/bahi.js?v=" in html
    assert "accounts: 'accountsdesk'" in emp and "if (v === 'accountsdesk') BAHI?.open($('#accountsdesk'));" in v2
    assert "/api/bahi/overview" in js and "/api/bahi/sync" in js and "esc(" in js
    assert "client_secret" not in js and "type=\"password\"" not in js     # the desk never asks for a key or a password
    blk = css[css.index("/* v0.806 BAHI"):]
    assert "infinite" not in blk and "backdrop-filter" not in blk and not re.search(r"#[0-9a-fA-F]{6}", blk)
    wf = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text(encoding="utf-8")
    assert "          - wb_check\n" in wf and "python -m app.bahi.wbcheck" in wf


def test_the_desk_in_a_real_browser(arena_server):  # noqa: F811
    import os
    base, browser, key = arena_server
    _seed()
    from app.bahi import register as REG
    REG.sync("default", months=REG.months_back(2) + ["2026-10"])
    shots = os.environ.get("CONSOLE_SHOTS")
    for w, h, scheme in ((1280, 1000, "light"), (390, 900, "dark")):
        ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "/console/")
        pg.wait_for_selector("#composer")
        pg.evaluate("document.querySelector('.sn[data-v=\"hire\"]')?.click()")
        pg.wait_for_selector("[data-ae=dept]")
        pg.locator("[data-ae=dept][data-id=biz]").first.click()
        pg.locator("[data-ae=role][data-key=accounts]").first.click()
        pg.wait_for_selector("[data-ae=hire][data-key=accounts], [data-ae=open][data-key=accounts]")
        if pg.locator("[data-ae=hire][data-key=accounts]").count():          # the second pass finds it already hired
            pg.locator("[data-ae=hire][data-key=accounts]").first.click()
        pg.wait_for_selector("[data-ae=open][data-key=accounts]")
        pg.locator("[data-ae=open][data-key=accounts]").first.click()
        pg.wait_for_selector(".acd .ddk-hero")
        assert pg.locator(".ddk-h1").text_content() == "GST & Accounts"
        assert pg.locator(".acd-dues li").count() >= 3
        if shots:
            pg.screenshot(path=f"{shots}/bahi-overview-{w}-{scheme}.png", full_page=True)
        pg.locator("[data-a=tab][data-t=register]").click()
        pg.wait_for_selector(".acd-filters")
        pg.select_option("[data-f=period]", "2026-10")
        pg.wait_for_selector("#acdReg table")
        assert pg.locator("#acdReg tbody tr").count() >= 5 and pg.locator(".acd-flag").count() == 2
        pg.locator("[data-a=tab][data-t=connection]").click()
        assert "Not set" in pg.locator(".acd-body").text_content()
        pg.locator("[data-a=tab][data-t=plan]").click()
        assert pg.locator(".acd-plan li").count() >= 10
        assert pg.evaluate("document.querySelector('.ddk').scrollWidth <= document.querySelector('.ddk').clientWidth + 1")
        assert not errs, errs
        ctx.close()
