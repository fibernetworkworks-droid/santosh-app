"""MATERIAL STORE DESK (Construction & Real Estate): a store manager for any construction company in any country, on one movement
ledger that is never edited. Receiving matched three ways (order, paper, count) with arithmetic checks on HER numbers; quality hold
decided by a named person; issues that must name the work, oldest lots first with their heat numbers; free-issue material held by
subcontractors; transfers in two steps; blind double counts with a recount and approval by her value tiers; reconciliation of what
the work should have used against what it used, with a recovery draft from HER subcontract; valuation by HER method; the old store
rows brought in once; the chat drafts, a person posts; walked in a browser at 1440 and 390."""
from __future__ import annotations

import os

import pytest

T = "default"


@pytest.fixture
def sd(env):
    from app.storedesk import service as S
    from app.storedesk.core import _READY
    _READY.clear()
    return S


def _setup(S):
    S.run(T, "save_settings", {"country": "AE", "currency": "AED", "valuation": "wavg", "tiers": [[2000, "Store in-charge"], [20000, "Project manager"], [None, "Finance"]]})
    S.run(T, "save_store", {"name": "Main store", "project": "Harbor Point"})
    S.run(T, "save_store", {"name": "Site B", "kind": "sub"})
    S.run(T, "save_item", {"name": "Cement CEM I 42.5N", "unit": "bag", "conv": {"t": 20}, "shelf_days": 90, "price": 18})
    S.run(T, "save_item", {"name": "Rebar B500B 16 mm", "unit": "t", "trace": "heat", "mass_per_m": 1.58, "mass_src": "her standard's table",
                           "tol_pct": 4.5, "price": 3100})
    S.run(T, "save_item", {"name": "Concrete block 200 mm", "unit": "no", "price": 3.5})


# ---------------------------------------------------------------- settings, units, ledger basics
def test_settings_units_and_global(sd):
    S = sd
    from app.storedesk.core import StoreError
    _setup(S)
    st = S.run(T, "settings", {})
    assert st["currency"] == "AED" and st["pack"]["delivery_word"] == "delivery note"
    with pytest.raises(StoreError, match="LIFO is not allowed"):
        S.run(T, "save_settings", {"valuation": "lifo"})
    S.run(T, "save_settings", {"gaap": "usgaap", "valuation": "lifo"})
    S.run(T, "save_settings", {"gaap": "ifrs", "valuation": "wavg"})
    with pytest.raises(StoreError, match="three-letter"):
        S.run(T, "save_settings", {"currency": "rupees"})
    from app.storedesk import packs as P
    assert any(r["id"] == "eu-ce" for r in P.pack("DE")["docs"]) and not any(r["id"] == "eu-ce" for r in P.pack("AE")["docs"])
    assert any(r["id"] == "in-cement" for r in P.storage_for("IN", "Cement OPC 53")) and not P.storage_for("US", "Cement")[1:]
    assert all(r["check"] for r in P.DOCS if r["source"] == "Not read here")


def _receive_rebar(S):
    S.run(T, "save_po", {"number": "PO 2026-119", "supplier": "Gulf Steel LLC", "due": "2026-12-01",
                         "lines": [{"item": "Rebar B500B 16 mm", "qty": 18, "rate": 3100}]})
    lines = [{"item": "Rebar B500B 16 mm", "doc_qty": 8, "qty": 7.4, "lot": "7G39", "cert": "MTC 39-2211", "bars": 390, "length_m": 12},
             {"item": "Rebar B500B 16 mm", "doc_qty": 8, "qty": 7.3, "lot": "7G40", "cert": "MTC 40-2214"},
             {"item": "Rebar B500B 16 mm", "doc_qty": 8, "qty": 7.2, "lot": "7G41"}]
    return S.run(T, "draft_receipt", {"supplier": "Gulf Steel", "doc_no": "DN-4471", "po": "PO 2026-119", "lines": lines}, actor="tool")


def test_receiving_three_way_and_quality(sd):
    S = sd
    from app.storedesk.core import StoreError
    _setup(S)
    g = _receive_rebar(S)
    assert g["status"] == "draft" and g["number"] == "GRN-0001"
    l1, l2, l3 = g["lines"]
    txt = " | ".join(c["text"] for c in l1["checks"])
    assert "-7.5%" in txt and "±4.5%" in txt                  # 7.4 vs 8.0
    assert "390 bars x 12 m x 1.58 kg/m (her standard's table) = 7.394 t nominal" in txt
    assert any("certificate" in c["text"] for c in l3["checks"]) and l3["to"] == "hold" and "no certificate" in l3["hold_why"]
    assert any("More than the order's open" in c["text"] for c in l3["checks"]) is False   # 7.2 alone is within the open 18
    assert l1["short"] == pytest.approx(0.6) and l1["to"] == "hold"   # a heat item always waits for the QC engineer
    # the chat cannot confirm; a person can, by name
    with pytest.raises(PermissionError):
        S.run(T, "confirm_receipt", {"id": g["id"], "who": "Imran"}, actor="tool")
    with pytest.raises(StoreError, match="Who is confirming"):
        S.run(T, "confirm_receipt", {"id": g["id"]})
    c = S.run(T, "confirm_receipt", {"id": g["id"], "who": "Imran"})
    assert c["status"] == "confirmed" and "3 on quality hold" in c["say"]
    po = S.run(T, "docs", {"kind": "po"})["rows"][0]
    assert po["lines"][0]["received"] == pytest.approx(21.9) and po["status"] == "received"
    q = {r["lot"]: r for r in S.run(T, "quality_queue", {})["rows"]}
    assert set(q) == {"7G39", "7G40", "7G41"}
    S.run(T, "quality", {"decision": "accept", "lot": q["7G39"]["lot_id"], "who": "Sana (QC)"})
    with pytest.raises(StoreError, match="no mill test certificate"):
        S.run(T, "quality", {"decision": "accept", "lot": q["7G41"]["lot_id"], "who": "Sana (QC)"})
    S.run(T, "quality", {"decision": "reject", "lot": q["7G41"]["lot_id"], "who": "Sana (QC)"})
    r = S.run(T, "return_vendor", {"lot": q["7G41"]["lot_id"], "who": "Imran", "reason": "no certificate"})
    assert "Gulf Steel" in r["debit_note"] and "7G41" in r["debit_note"]
    st = {x["item"]: x for x in S.run(T, "stock", {})["items"]}
    rb = st["Rebar B500B 16 mm"]
    assert rb["available"] == pytest.approx(7.4) and rb["hold"] == pytest.approx(7.3) and rb["blocked"] == 0
    # a receipt that is confirmed cannot change; nothing enters stock from a rejected one
    with pytest.raises(StoreError, match="already confirmed"):
        S.run(T, "draft_receipt", {"id": g["id"], "supplier": "x", "lines": [{"item": "Concrete block 200 mm", "qty": 1}]})
    g2 = S.run(T, "draft_receipt", {"supplier": "Bluewave", "lines": [{"item": "Concrete block 200 mm", "doc_qty": 100, "qty": 100}]})
    S.run(T, "reject_receipt", {"id": g2["id"], "who": "Imran", "reason": "wrong size"})
    assert S.run(T, "stock", {"q": "block"})["items"][0]["available"] == 0


def test_issue_fifo_units_holders_transfers_reverse(sd):
    S = sd
    from app.storedesk.core import StoreError
    from app.storedesk import core as C
    _setup(S)
    for day, n, made in (("2026-11-10", 300, "2026-11-01"), ("2026-11-20", 200, "2026-11-15")):
        g = S.run(T, "draft_receipt", {"supplier": "Gulf Cement", "doc_no": "N" + day, "lines": [{"item": "cement", "doc_qty": n, "qty": n, "made": made, "lot": "B" + day}]})
        with C.session() as s:
            d = s.get(C.SdDoc, g["id"])
            d.day = day
        S.run(T, "confirm_receipt", {"id": g["id"], "who": "Imran"})
    with pytest.raises(StoreError, match="which work"):
        S.run(T, "draft_slip", {"type": "issue", "item": "cement", "qty": 40}, actor="tool")
    S.run(T, "save_budget", {"work": "Slab L6", "item": "cement", "qty": 194, "allowance": 3})
    sl = S.run(T, "draft_slip", {"type": "issue", "item": "cement", "qty": 2, "unit": "t", "work": "Slab L6"}, actor="tool")   # 2 t = 40 bags
    assert sl["data"]["qty"] == 40 and sl["data"]["lots"][0]["qty"] == 40
    S.run(T, "confirm_slip", {"id": sl["id"], "who": "Imran"})
    sl2 = S.run(T, "draft_slip", {"type": "issue", "item": "cement", "qty": 280, "work": "Slab L6"})
    assert any("Takes Slab L6 to" in w for w in sl2["data"]["warn"])
    S.run(T, "confirm_slip", {"id": sl2["id"], "who": "Imran"})
    led = S.run(T, "ledger", {"item": "cement"})["rows"]
    issued = [r for r in led if r["kind"] == "issue"]
    assert {r["lot"] for r in issued} == {"B2026-11-10", "B2026-11-20"}            # oldest lot used up first, then the next
    assert sum(r["qty"] for r in issued if r["lot"] == "B2026-11-10") == 300
    # free issue to a subcontractor and back
    S.run(T, "save_holder", {"name": "Al Fajr Steel Fixing", "allowance": 3, "rates": {"cement": 18}, "uplift": 10, "clause": "Subcontract cl. 14.3"})
    fi = S.run(T, "draft_slip", {"type": "issue", "item": "cement", "qty": 100, "work": "Stair L6", "holder": "Al Fajr Steel Fixing"})
    S.run(T, "confirm_slip", {"id": fi["id"], "who": "Imran"})
    held = S.run(T, "held", {})["rows"]
    assert held[0]["holder"] == "Al Fajr Steel Fixing" and held[0]["qty"] == 100
    rt = S.run(T, "draft_slip", {"type": "return", "item": "cement", "qty": 10, "from_holder": "Al Fajr Steel Fixing"})
    S.run(T, "confirm_slip", {"id": rt["id"], "who": "Imran"})
    assert S.run(T, "held", {})["rows"][0]["qty"] == 90
    # transfer: out, in short -> a named difference
    S.run(T, "draft_receipt", {"supplier": "Bluewave", "lines": [{"item": "block", "doc_qty": 1000, "qty": 1000}]})
    gid = S.run(T, "docs", {"kind": "grn", "status": "draft"})["rows"][0]["id"]
    S.run(T, "confirm_receipt", {"id": gid, "who": "Imran"})
    tr = S.run(T, "draft_slip", {"type": "transfer", "item": "block", "qty": 400, "to_store": "Site B"})
    t1 = S.run(T, "confirm_slip", {"id": tr["id"], "who": "Imran"})
    assert t1["status"] == "transit"
    t2 = S.run(T, "receive_transfer", {"id": tr["id"], "who": "Omar", "qty": 390})
    assert t2["status"] == "short" and "10 no short" in t2["say"]
    rows = {x["item"]: x for x in S.run(T, "stock", {"store": "Site B"})["items"]}
    assert rows["Concrete block 200 mm"]["available"] == 390 and rows["Concrete block 200 mm"]["transit"] == 10
    # a mistake is reversed with a counter-row, never edited
    one = [r for r in S.run(T, "ledger", {"item": "block"})["rows"] if r["kind"] == "transfer_in"][0]
    with pytest.raises(PermissionError):
        S.run(T, "reverse", {"id": one["id"], "who": "Omar", "reason": "x"}, actor="tool")
    with pytest.raises(StoreError, match="name of the person"):
        S.run(T, "reverse", {"id": one["id"], "reason": "wrong store"})
    S.run(T, "reverse", {"id": one["id"], "who": "Omar", "reason": "booked to the wrong store"})
    led = S.run(T, "ledger", {"item": "block"})["rows"]
    assert any(r["kind"] == "reverse" for r in led) and any(r["id"] == one["id"] and r["reversed"] for r in led)
    with pytest.raises(StoreError, match="already reversed"):
        S.run(T, "reverse", {"id": one["id"], "who": "Omar", "reason": "again"})


def test_counts_blind_recount_tiers(sd):
    S = sd
    from app.storedesk.core import StoreError
    _setup(S)
    g = S.run(T, "draft_receipt", {"supplier": "Bluewave", "lines": [{"item": "block", "doc_qty": 12400, "qty": 12400}]})
    with pytest.raises(StoreError, match="Close these first"):
        S.run(T, "open_count", {"counters": ["Imran", "Sameer"]})
    S.run(T, "confirm_receipt", {"id": g["id"], "who": "Imran"})
    with pytest.raises(StoreError, match="two different people"):
        S.run(T, "open_count", {"counters": ["Imran", "imran"]})
    c = S.run(T, "open_count", {"counters": ["Imran", "Sameer"], "items": ["block"]}, actor="tool")
    assert c["blind"] and "book" not in c["lines"][0]
    c = S.run(T, "enter_count", {"id": c["id"], "who": "Imran", "counts": {"block": 11800}})
    assert c.get("blind")                                        # the book stays hidden until both have counted
    c = S.run(T, "enter_count", {"id": c["id"], "who": "Sameer", "counts": {"block": 11750}})
    assert c["status"] == "recount" and c["lines"][0]["book"] == 12400
    with pytest.raises(StoreError, match="third person"):
        S.run(T, "recounter", {"id": c["id"], "who": "Sameer"})
    S.run(T, "recounter", {"id": c["id"], "who": "Rahul"})
    c = S.run(T, "enter_count", {"id": c["id"], "who": "Rahul", "counts": {"block": 11800}})
    assert c["status"] == "closed" and c["lines"][0]["result"] == "adjust" and c["lines"][0]["diff"] == -600
    adj = S.run(T, "docs", {"kind": "adjust"})["rows"][0]
    assert adj["data"]["value"] == -2100.0 and adj["data"]["tier"]["who"] == "Project manager"
    with pytest.raises(PermissionError):
        S.run(T, "approve_adjust", {"id": adj["id"], "who": "x", "role": "Project manager", "reason": "count"}, actor="tool")
    with pytest.raises(StoreError, match="approved by the Project manager"):
        S.run(T, "approve_adjust", {"id": adj["id"], "who": "Imran", "role": "Store in-charge", "reason": "count error"})
    S.run(T, "approve_adjust", {"id": adj["id"], "who": "Omar", "role": "Project manager", "reason": "broken in handling"})
    assert S.run(T, "stock", {"q": "block"})["items"][0]["available"] == 11800
    assert S.run(T, "accuracy", {})["lines"] == 1


def test_reconcile_holder_recovery_and_valuation(sd):
    S = sd
    from app.storedesk.core import StoreError
    from app.storedesk import core as C
    _setup(S)
    S.run(T, "save_item", {"name": "Rebar B500B 12 mm", "unit": "t", "price": 3000})
    for rate, q in ((3000, 20), (3300, 20)):
        g = S.run(T, "draft_receipt", {"supplier": "Gulf Steel", "lines": [{"item": "12 mm", "doc_qty": q, "qty": q, "rate": rate}]})
        S.run(T, "confirm_receipt", {"id": g["id"], "who": "Imran"})
    S.run(T, "save_holder", {"name": "Al Fajr", "allowance": 3, "rates": {"12 mm": 3100}, "uplift": 10, "clause": "Subcontract cl. 14.3"})
    S.run(T, "save_budget", {"work": "Slab L5", "item": "12 mm", "qty": 31.4, "done": 100})
    s1 = S.run(T, "draft_slip", {"type": "issue", "item": "12 mm", "qty": 34.6, "work": "Slab L5", "holder": "Al Fajr"})
    S.run(T, "confirm_slip", {"id": s1["id"], "who": "Imran"})
    r = S.run(T, "reconcile", {})
    row = r["rows"][0]
    assert row["theoretical"] == 31.4 and row["actual"] == 34.6 and row["pct"] == pytest.approx(10.19, abs=0.01)
    assert row["excess"] == pytest.approx(34.6 - 31.4 * 1.03, abs=1e-6)
    assert any("No cut pieces or scrap" in h for h in row["hints"])
    h = r["holders"][0]
    assert h["recovery"] == pytest.approx(round((34.6 - 31.4 * 1.03) * 3100 * 1.1, 2))
    rc = S.run(T, "draft_recovery", {"holder": "Al Fajr", "item": "12 mm"}, actor="tool")
    assert rc["status"] == "draft" and "your decision" in rc["say"]
    with pytest.raises(PermissionError):
        S.run(T, "decide_recovery", {"id": rc["id"], "decision": "deduct", "who": "x"}, actor="tool")
    # unused at the work front brings it inside the allowance
    S.run(T, "progress", {"work": "Slab L5", "done": 100, "unused": {"12 mm": 2.5}})
    assert S.run(T, "reconcile", {})["rows"][0]["excess"] == 0
    # valuation: 5.4 t left; FIFO = the newer lot's cost; weighted average = the average; LIFO refused under IFRS
    with C.session() as s:
        f = C.valuation(s, T, "fifo")
        w = C.valuation(s, T, "wavg")
        with pytest.raises(StoreError):
            C.valuation(s, T, "lifo")
    i12 = lambda v: next(x for x in v["items"] if x["item"].endswith("12 mm"))   # noqa: E731
    assert i12(f)["value"] == pytest.approx(5.4 * 3300) and i12(w)["value"] == pytest.approx(5.4 * 3150)


def test_demand_shortfall_reorder_and_tool_gate(sd):
    S = sd
    from app.storedesk import core as C
    _setup(S)
    g = S.run(T, "draft_receipt", {"supplier": "Gulf Cement", "lines": [{"item": "cement", "doc_qty": 1240, "qty": 1240}]})
    S.run(T, "confirm_receipt", {"id": g["id"], "who": "Imran"})
    t0 = C.today(T)
    import datetime as D
    d3, d1 = (t0 + D.timedelta(days=3)).isoformat(), (t0 + D.timedelta(days=1)).isoformat()
    S.run(T, "save_budget", {"work": "Slab L6", "item": "cement", "qty": 1000, "need_by": d3, "need_qty": 980})
    S.run(T, "save_budget", {"work": "Core walls", "item": "cement", "qty": 700, "need_by": d3, "need_qty": 630})
    sf = S.run(T, "shortfall", {})["rows"][0]
    assert sf["short"] == {"date": d3, "short": 370.0, "work": "Core walls"}
    S.run(T, "save_po", {"number": "PO 2026-118", "supplier": "Gulf Cement", "due": d1, "lines": [{"item": "cement", "qty": 800, "rate": 18}]})
    assert S.run(T, "shortfall", {})["rows"][0]["short"] is None
    ind = S.run(T, "draft_indent", {"item": "cement", "qty": 900, "work": "Slab L6", "by": "Ravi"}, actor="tool")
    assert ind["status"] == "waiting"
    with pytest.raises(PermissionError):
        S.run(T, "decide_indent", {"id": ind["id"], "decision": "approve", "who": "Ravi"}, actor="tool")
    assert S.run(T, "decide_indent", {"id": ind["id"], "decision": "approve", "who": "Omar"})["status"] == "approved"
    t = S.run(T, "today", {})
    assert t["currency"] == "AED" and t["value"] == pytest.approx(1240 * 18) and t["chart"]["item"].startswith("Cement")
    assert t["coming"][0]["po"] == "PO 2026-118"


def test_old_store_rows_come_in_once(sd):
    S = sd
    from app.construction import store as OLD
    OLD.upsert_lot(T, "Cement OPC 53", "bag", 100, 2000)
    OLD.grn(T, "Cement OPC 53", 500, 400, "Ultra", "CH-1", "", "Site", "2026-11-01")
    OLD.issue(T, "Cement OPC 53", 120, "Site", "Gang A", "Slab 1", "2026-11-02")
    OLD.issue(T, "Cement OPC 53", 5, "Site", "Gang A", "torn", "2026-11-02", waste=True)
    S.run(T, "today", {})
    S.run(T, "today", {})
    it = S.run(T, "stock", {"q": "opc"})["items"][0]
    assert it["available"] == 375
    kinds = [r["kind"] for r in S.run(T, "ledger", {"item": "opc"})["rows"]]
    assert sorted(kinds) == ["issue", "receive", "scrap"]


# ---------------------------------------------------------------- the chat, the tool and the wiring
def test_chat_tool_and_wiring(sd):
    import asyncio
    from pathlib import Path
    from fastapi.testclient import TestClient
    from app import storechat as C
    from app.agent.tools import Ctx, FAMILY_OF, HANDLERS, ToolError
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    C.forget(T)
    assert C.summary(T)["hired"] is False and "Hire me from AI Employees" in C.greeting(T)
    with pytest.raises(PermissionError):
        C.do(T, "save_store", {"name": "Yard"})
    hire.hire(T, "const_store", trust="seekh")
    d = C.summary(T)
    assert d["hired"] and "places no order" in d["foot"] and any(n["go"] == "settings" for n in d["desk"]["needs"])
    chat = C.current(T)
    assert C.is_store(chat["id"]) and C.owns(T, chat["id"]) and "<store_desk>" in C.block(T)
    _setup(sd)
    C.forget(T)
    assert "AED" in C.block(T) and "Main store" in C.block(T)
    # the tool drafts; it can never post a person's decision
    assert FAMILY_OF["store_desk"] in C.FAMILIES and "store_desk" in HANDLERS
    ctx = Ctx(tenant_id=T, conversation_id=chat["id"])
    r = asyncio.run(HANDLERS["store_desk"](ctx, action="draft_receipt", supplier="Gulf Steel", lines=[{"item": "Cement CEM I 42.5N", "qty": 100, "doc_qty": 100}]))
    assert r["status"] == "draft"
    for tap in ("confirm_receipt", "approve_adjust", "decide_recovery", "reverse", "quality"):
        with pytest.raises(ToolError):
            asyncio.run(HANDLERS["store_desk"](ctx, action=tap, id=r["id"], who="x"))
    with pytest.raises(PermissionError):
        sd.run(T, "confirm_receipt", {"id": r["id"], "who": "x"}, actor="tool")
    # the desk posts with a name
    assert C.do(T, "confirm_receipt", {"id": r["id"], "who": "Ravi"})["status"] == "confirmed"
    with pytest.raises(PermissionError):
        C.do(T, "save_store", {"name": "my password is hunter2"})
    hire.pause(T, "const_store")
    assert C.do(T, "stock", {})["items"]
    with pytest.raises(PermissionError):
        C.do(T, "save_store", {"name": "Yard 3"})
    # wiring
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "is_store(conversation_id)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"store"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/store")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "storedesk.js" in r.text
    html = (root / "server/app/static/console/storedesk.html").read_text()
    for x in ("chatkit.js", "storedesk.css", "storedesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "/console/store" in (root / "server/app/static/console/v2.js").read_text()
    assert "const_store = 'storedesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "/console/store" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def st_server(sd, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "const_store", trust="seekh")
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
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(sd, st_server):
    base, browser, key = st_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    def toast(pg, text):
        pg.wait_for_selector(f"#toast:has-text('{text}')", timeout=20000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/store")
    pg.wait_for_selector(".sk-greet", timeout=20000)
    assert "Start here" in pg.inner_text("#stPage")
    snap(pg, "st-today-empty-1440")
    # settings, a store, items
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=company]", "Harbor Builders")
    pg.fill("form[data-form=settings] [name=country]", "AE")
    pg.fill("form[data-form=settings] [name=currency]", "AED")
    pg.click("form[data-form=settings] button")
    toast(pg, "Settings saved")
    assert "Harbor Builders" in pg.inner_text("#stSite") and "AED" in pg.inner_text("#stSite")
    pg.fill("form[data-form=store] [name=name]", "Site B")
    pg.click("form[data-form=store] button")
    pg.wait_for_selector("#stPage :text('Site B')", timeout=20000)
    pg.fill("form[data-form=importitems] [name=text]", "name,unit,code,category,min,price,trace,conv\n"
            "Cement CEM I 42.5N,bag,CEM42,bulk,100,18,none,t=20\nRebar B500B 16 mm,t,RB16,bulk,2,3100,heat,")
    pg.click("form[data-form=importitems] button")
    toast(pg, "2 item(s) saved")
    snap(pg, "st-settings-1440")
    # an order, then a delivery against it
    go(pg, "#/indents", "#stPage .sd-h")
    pg.wait_for_selector("form[data-form=po]", state="attached", timeout=30000)
    pg.evaluate("document.querySelector('form[data-form=po]').closest('details').open = true")
    pg.fill("form[data-form=po] [name=number]", "PO-77")
    pg.fill("form[data-form=po] [name=supplier]", "Gulf Cement")
    pg.fill("form[data-form=po] [name=lines]", "Cement CEM I 42.5N, 800, bag, 18")
    pg.click("form[data-form=po] button")
    pg.wait_for_selector("#stPage :text('PO-77')", timeout=20000)
    go(pg, "#/receive", "form[data-form=receipt]")
    pg.fill("form[data-form=receipt] [name=supplier]", "Gulf Cement")
    pg.fill("form[data-form=receipt] [name=doc_no]", "DN-5521")
    pg.select_option("form[data-form=receipt] [name=po]", "PO-77")
    pg.fill("form[data-form=receipt] [name=text]", "Cement CEM I 42.5N, 400, bag")
    pg.click("form[data-form=receipt] button[type=submit]")
    pg.wait_for_selector(".sk-stepbar", timeout=30000)
    assert pg.locator(".sk-ck").count() >= 1
    snap(pg, "st-receipt-1440")
    pg.fill("form[data-form=confirm] [name=who]", "Ravi Kumar")
    pg.click("form[data-form=confirm] button[value=confirm]")
    pg.wait_for_selector("form[data-form=invoiced]", timeout=30000)
    assert "Received by: Ravi Kumar" in pg.inner_text("#stPage")
    # issue to the work
    go(pg, "#/issue", "form[data-form=slip]")
    pg.select_option("form[data-form=slip] [name=item]", "Cement CEM I 42.5N")
    pg.fill("form[data-form=slip] [name=qty]", "60")
    pg.fill("form[data-form=slip] [name=work]", "Slab L6")
    pg.click("form[data-form=slip] button[type=submit]")
    try:
        pg.wait_for_selector("form[data-form=confirmslip]", timeout=30000)
    except Exception:
        raise AssertionError(pg.inner_text("#toast"))
    pg.fill("form[data-form=confirmslip] [name=who]", "Ravi Kumar")
    pg.click("form[data-form=confirmslip] button[value=confirm]")
    pg.wait_for_selector("#stPage :text('Slab L6')", timeout=30000)
    snap(pg, "st-issue-1440")
    # stock and an item's ledger
    go(pg, "#/stock", "table.sk-stock")
    assert "340" in pg.inner_text("table.sk-stock")
    pg.click("table.sk-stock tr.sk-click >> nth=0")
    pg.wait_for_selector("text=Every movement", timeout=20000)
    assert pg.locator("#stPage table.tb tbody tr").count() >= 2
    snap(pg, "st-item-1440")
    # a blind count with two counters, then a recount by a third person
    go(pg, "#/counts", "form[data-form=opencount]")
    pg.fill("form[data-form=opencount] [name=c1]", "Asha")
    pg.fill("form[data-form=opencount] [name=c2]", "Bilal")
    pg.click("form[data-form=opencount] button")
    pg.wait_for_selector("form[data-form=entercount]", timeout=30000)
    assert "Book" not in pg.inner_text("#stPage table.tb thead")
    for who, n in (("Asha", "300"), ("Bilal", "300")):
        pg.select_option("form[data-form=entercount] [name=who]", who)
        for inp in pg.locator("form[data-form=entercount] input[name^=n_]").all():
            inp.fill(n if "Cement" in (inp.evaluate("e => e.closest('label').textContent")) else "0")
        pg.click("form[data-form=entercount] button")
        pg.wait_for_timeout(600)
    pg.wait_for_selector("#stPage :text('Book')", timeout=30000)
    snap(pg, "st-count-1440")
    # reconcile and the reports
    go(pg, "#/reconcile", "#stPage .sd-h")
    go(pg, "#/reports", "#stPage :text('Stock statement')")
    snap(pg, "st-reports-1440")
    go(pg, "#/today", ".sk-greet")
    assert pg.locator(".cs-hero").count() == 1
    snap(pg, "st-today-1440")
    # the phone: every page fits
    ph = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    ph.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pp = ph.new_page()
    pp.on("pageerror", lambda e: errs.append("phone: " + str(e)))
    pp.goto(base + "/console/store")
    pp.wait_for_selector(".sk-greet", timeout=20000)
    for tab in ("today", "receive", "stock", "issue", "transfers", "indents", "counts", "reconcile", "reports", "settings"):
        go(pp, "#/" + tab, "#stPage .sd-h")
        pp.wait_for_timeout(400)
        w = pp.evaluate("document.documentElement.scrollWidth")
        page_w = pp.evaluate("document.querySelector('#stPage').scrollWidth")
        assert w <= 391, (tab, w)
        assert page_w <= 391, (tab, page_w)
        snap(pp, f"st-{tab}-390")
    assert not errs, errs
