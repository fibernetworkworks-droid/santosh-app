"""Godown Sahayak (warehouse manager): bins + SKUs linked to her stock list, GRN with expiry / damage / serial / PO-short checks,
putaway suggestions, FEFO pick lists with a walking path (her list, Hoola Deals orders, Thok bills; waves; short picks -> spot
count), shared stock count kept right, ABC + blind cycle counts, variance, adjustment / write-off cards decided ONLY by her tap
(hash, stale when stock moved), slow / dead / near-expiry, labels PDF, Excel, morning tick, tools (staff / customer actors), API."""
import asyncio
from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.warehouse.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 23)


@pytest.fixture
def wh(env, monkeypatch):
    from app.warehouse import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "today", lambda t: DAY)
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def stock_qty(name):
    from app.net import deal
    return next(x["qty"] for x in deal.stock(T) if x["name"] == name)


def setup(S):
    from app.net import deal
    deal.set_stock(T, [{"name": "Atta 50kg", "price": 1500, "gst_pct": 5, "unit": "bag", "qty": 0, "aliases": ["atta"]},
                       {"name": "Biscuit carton", "price": 400, "gst_pct": 18, "unit": "ctn", "qty": 0, "aliases": ["biscuit"]},
                       {"name": "Mixer grinder", "price": 2500, "gst_pct": 18, "unit": "pc", "qty": 0, "aliases": ["mixer"]}])
    S.save_settings(T, name="Akola godown")
    S.make_bins(T, "A", aisles=2, racks=2, kind="pick", capacity=100)          # A-1-1, A-1-2, A-2-1, A-2-2
    S.save_bin(T, code="B-1", kind="bulk", capacity=500)
    S.save_sku(T, name="Biscuit carton", track="batch")
    S.save_sku(T, name="Mixer grinder", track="serial")


def test_rules():
    from app.warehouse import rules as R
    assert R.split_code("A-12") == {"zone": "A", "aisle": "12", "rack": "", "bin": ""}
    assert R.split_code("b-03-r2-4")["rack"] == "R2" and R.valid_code("B-03-R2-4") and not R.valid_code("A--1")
    order = sorted(["A-1-2", "A-1-1", "A-2-1", "A-2-2", "B-1"], key=lambda c: R.path_key(R.split_code(c)))
    assert order == ["A-1-1", "A-1-2", "A-2-2", "A-2-1", "B-1"]            # serpentine: aisle 2 walked back down
    assert R.parse_date("03/2027") == date(2027, 3, 31) and R.parse_date("5-1-27") == date(2027, 1, 5) and R.parse_date("x") is None
    lots = [{"expiry": "2027-05-01", "received_on": "2026-01-01"}, {"expiry": "", "received_on": "2025-01-01"},
            {"expiry": "2026-12-01", "received_on": "2026-09-01"}]
    assert [l["expiry"] for l in sorted(lots, key=R.fefo_key)] == ["2026-12-01", "2027-05-01", ""]
    cls = R.abc([{"id": "a", "value": 800}, {"id": "b", "value": 150}, {"id": "c", "value": 40}, {"id": "d", "value": 10}, {"id": "e", "value": 0}])
    assert cls == {"a": "A", "b": "B", "c": "C", "d": "C", "e": "C"}
    assert R.abc([{"id": "x", "picks": 9}, {"id": "y", "picks": 1}])["x"] == "A"
    assert R.within(-1, 50, "A") and not R.within(-2, 50, "A") and R.within(-4, 100, "C")
    assert R.count_due("A", "2026-09-01", DAY) == (True, 22) and R.count_due("C", "2026-09-01", DAY)[0] is False
    assert R.count_due("B", "", DAY)[0] is True
    assert R.expiry_state("2026-10-01", DAY) == "expired" and R.expiry_state("2026-11-10", DAY) == "near" and R.expiry_state("", DAY) == ""
    assert R.shelf_left_pct("2026-01-01", "2026-12-31", DAY) < 30
    plan = R.putaway_plan(30, [{"code": "A-1-1", "kind": "pick", "capacity": 100, "used": 80, "skus": {"s1": ["B1"]}, "rank": 0},
                               {"code": "A-2-2", "kind": "pick", "capacity": 100, "used": 0, "skus": {}, "rank": 3},
                               {"code": "QTN", "kind": "quarantine", "capacity": None, "used": 0, "skus": {}, "rank": 4}], "s1", "B1", fast=True)
    assert plan[0] == {"bin": "A-1-1", "qty": 20.0, "why": plan[0]["why"], "score": plan[0]["score"]} and "yahi SKU" in plan[0]["why"]
    assert plan[1]["bin"] == "A-2-2" and plan[1]["qty"] == 10 and all(p["bin"] != "QTN" for p in plan)
    assert R.parse_scan("HOOLA-BIN:A-12") == {"type": "bin", "code": "A-12"} and R.parse_scan("8901234567890")["type"] == "code"
    assert R.reason_of("3 carton toot gaye", -3) == "damaged" and R.reason_of("", 2) == "found"


def test_grn_putaway_and_shared_stock(wh):
    S = wh
    setup(S)
    g = S.grn(T, lines=[{"item": "atta", "qty": 40, "damaged": 2},
                        {"item": "biscuit", "qty": 60, "batch": "B1", "expiry": "2027-06-30"},
                        {"item": "biscuit", "qty": 10, "batch": "B0", "expiry": "2026-10-10"},          # expired on arrival
                        {"item": "mixer", "qty": 2, "serials": ["MX1", "MX2"]},
                        {"item": "Dal 30kg", "qty": 5}],
              supplier="Shree Mills", doc="CH-77", expected=[{"item": "atta", "qty": 50}, {"item": "Rice 25kg", "qty": 10}])
    assert g["number"] == "GRN-0001" and kinds(S)[-1] == "warehouse_grn"
    atta = next(l for l in g["lines"] if l["name"] == "Atta 50kg")
    assert atta["linked"] and any("toota" in n for n in atta["notes"]) and any("50 tha" in n for n in atta["notes"])
    exp = next(l for l in g["lines"] if l["batch"] == "B0")
    assert exp["to_bin"] == "QTN" and any("EXPIRED" in n for n in exp["notes"]) and "putaway" not in exp
    dal = next(l for l in g["lines"] if l["name"] == "Dal 30kg")
    assert not dal["linked"] and any("stock list" in n for n in dal["notes"])
    assert "Rice 25kg".lower() in " ".join(g["notes"]).lower() and "kam aaya" in g["draft"]["text"].lower()
    # shared stock count went up for linked items only (incl. damaged + quarantined: still her stock until a write-off)
    assert stock_qty("Atta 50kg") == 40 and stock_qty("Biscuit carton") == 70 and stock_qty("Mixer grinder") == 2
    assert all(p["bin"] != "QTN" for l in g["lines"] for p in l.get("putaway") or [])
    with pytest.raises(S.WarehouseError, match="serial MX1"):
        S.grn(T, lines=[{"item": "mixer", "qty": 1, "serials": ["MX1"]}])
    S.putaway(T, grn=g["number"])
    assert S.grn_view(T, g["id"])["status"] == "putaway"
    rcv = S.bin_view(T, "RCV")
    assert rcv["used"] == 0
    assert S.bin_view(T, "DMG")["used"] == 2 and S.bin_view(T, "QTN")["used"] == 10
    total = sum(b["used"] for b in S.bins(T) if b["kind"] == "pick" or b["kind"] == "bulk")
    assert total == 38 + 60 + 2 + 5
    S.save_bin(T, code="S-1", kind="pick", capacity=5)
    src = next(l["bin"] for l in S.stock_by_bin(T, sku="atta") if l["bin_kind"] == "pick" or l["bin_kind"] == "bulk")
    with pytest.raises(S.WarehouseError, match="jagah"):
        S.move(T, "atta", src, "S-1", 6)
    S.move(T, "atta", src, "S-1", 5)
    assert S.bin_view(T, "S-1")["used"] == 5
    led = S.ledger(T, sku="atta")
    assert led["totals"]["grn"] == 40 and "putaway" in led["totals"]
    rc = S.recon(T)
    assert rc["items"] == []                                                  # bins == stock list for linked SKUs


def test_pick_fefo_path_short_and_spot_count(wh):
    S = wh
    setup(S)
    S.opening(T, lines=[{"item": "biscuit", "qty": 20, "bin": "A-2-1", "batch": "OLD", "expiry": "2026-12-31"},
                        {"item": "biscuit", "qty": 30, "bin": "A-1-1", "batch": "NEW", "expiry": "2027-08-31"},
                        {"item": "biscuit", "qty": 5, "bin": "A-1-2", "batch": "EXP", "expiry": "2026-09-30"},
                        {"item": "atta", "qty": 10, "bin": "B-1"}])
    assert stock_qty("Biscuit carton") == 0                                  # opening never touches the shared count
    from app.net import deal
    deal.set_stock(T, [{"name": "Biscuit carton", "qty": 55}, {"name": "Atta 50kg", "qty": 10}])
    p = S.pick_list(T, "list", text="biscuit 35 ctn, atta 12 bori, chai patti 2", party="Gupta Kirana")
    tasks = p["tasks"]
    assert [t["bin"] for t in tasks] == ["A-1-1", "A-2-1", "B-1"]            # walking order, not FEFO order
    bis = [t for t in tasks if t["name"] == "Biscuit carton"]
    assert {t["batch"]: t["qty"] for t in bis} == {"OLD": 20, "NEW": 15}       # oldest expiry first, expired never
    assert any("EXPIRED" in n for n in p["notes"]) and any("chai patti" in n for n in p["notes"])
    atta = next(l for l in p["lines"] if l["name"] == "Atta 50kg")
    assert atta["short"] == 2 and "Kam:" in p["say"]
    p2 = S.pick_list(T, "list", text="biscuit 20")                             # held stock of the open list is not promised twice
    assert next(l for l in p2["lines"] if l["name"] == "Biscuit carton")["short"] == 5
    S.pick_cancel(T, p2["number"])
    old = next(t for t in tasks if t["batch"] == "OLD")
    r = S.pick_confirm(T, p["number"], picked=[{"n": old["n"], "qty": 18}], all_done=True)
    assert r["status"] == "done" and "dobara ginne" in r["say"]
    assert stock_qty("Biscuit carton") == 55 - 18 - 15 and stock_qty("Atta 50kg") == 0
    spot = [c for c in S.counts(T, "open") if c["kind"] == "spot"]
    assert spot and spot[0]["bins"] == ["A-2-1"] and "system" not in str(spot[0]["lines"])
    sheet = S.pick_sheet(T, p["number"])
    assert sheet["file"]["name"].endswith(".pdf")


def test_deal_and_thok_sources_do_not_double_count(wh, monkeypatch):
    S = wh
    setup(S)
    from app.db import session
    from app.net import deal
    from app.thok import service as TS
    monkeypatch.setattr(TS, "today", lambda t: DAY)
    deal.set_stock(T, [{"name": "Atta 50kg", "qty": 0}])
    TS.save_party(T, "Shree Mills", kind="supplier", phone="9844444444")
    pur = TS.purchase(T, "Shree Mills", "atta 50 bori @ 1400", bill_no="SM-9")
    pid = pur.get("purchase", {}).get("id") if isinstance(pur.get("purchase"), dict) else None
    if not pid:
        with session() as s:
            from sqlalchemy import select
            pid = s.scalars(select(TS.ThokPurchase.id)).first()
    after_purchase = stock_qty("Atta 50kg")
    g = S.grn(T, purchase=pid)
    assert g["source"] == "thok_purchase" and not g["sync"] and stock_qty("Atta 50kg") == after_purchase   # no double add
    S.putaway(T, grn=g["id"])
    with session() as s:
        s.add(deal.Deal(tenant_id=T, dkey="k1", role="seller", peer="gupta@hoola", title="Gupta Kirana", state="accepted", number="D-1001",
                        quote={"lines": [{"item": "Atta 50kg", "qty": 5, "status": "ok"}]}))
        s.add(deal.Deal(tenant_id=T, dkey="k2", role="seller", peer="sharma@hoola", title="Sharma", state="accepted", number="D-1002",
                        quote={"lines": [{"item": "Atta 50kg", "qty": 3, "status": "ok"}]}))
    w = S.pick_list(T, "deal")
    assert w["wave"] and w["orders"] == ["D-1001", "D-1002"] and w["lines"][0]["orders"] == {"D-1001": 5, "D-1002": 3}
    with pytest.raises(S.WarehouseError, match="pehle se khuli"):
        S.pick_list(T, "deal", refs=["D-1001"])
    before = stock_qty("Atta 50kg")
    S.pick_confirm(T, w["number"], all_done=True)
    assert stock_qty("Atta 50kg") == before                                  # Deals handover changes the shared count itself
    led = S.ledger(T, sku="atta")
    assert led["totals"]["pick"] == -8 and all(not m["synced"] for m in led["moves"] if m["kind"] == "pick")


def test_blind_count_variance_and_her_tap(wh):
    S = wh
    setup(S)
    from app.net import deal
    S.opening(T, lines=[{"item": "atta", "qty": 20, "bin": "A-1-1"}, {"item": "biscuit", "qty": 10, "bin": "A-1-2", "batch": "B1"}])
    deal.set_stock(T, [{"name": "Atta 50kg", "qty": 20}, {"name": "Biscuit carton", "qty": 10}])
    S.save_sku(T, sku="atta", abc="A")
    c = S.count_plan(T)                                                      # never counted -> due
    assert set(c["bins"]) == {"A-1-1", "A-1-2"} and c["blind"] and kinds(S)[-1] == "warehouse_count"
    assert all("system" not in l for l in S.count_view(T, c["id"])["lines"])
    S.count_enter(T, c["number"], [{"bin": "A-1-1", "item": "atta", "qty": 17}, {"bin": "A-1-2", "item": "biscuit", "batch": "B1", "qty": 10},
                                   {"bin": "A-1-2", "item": "atta", "qty": 1}])          # found something not on record
    assert all("system" not in l for l in S.count_view(T, c["id"])["lines"])
    res = S.count_close(T, c["number"])
    assert res["accuracy_pct"] == pytest.approx(33.3) and res["adjust"] and kinds(S)[-1] == "warehouse_adjust"
    adj = res["adjust"]
    assert adj["status"] == "waiting" and adj["minus"] == 1 and adj["plus"] == 1 and "17(5)(h)" in adj["itc_note"]
    assert adj["value"] == pytest.approx(-3 * 1500 + 1500) and "Atta 50kg" in adj["recount_first"]
    assert S.sku_view(T, "atta")["last_counted"] == DAY.isoformat()
    with pytest.raises(S.WarehouseError, match="tap"):
        S.decide_adjust(T, adj["id"], True, adj["hash"])                    # not her tap
    with pytest.raises(S.WarehouseError, match="badal gaya"):
        S.decide_adjust(T, adj["id"], True, "wrong", by_tap=True)
    assert S.bin_view(T, "A-1-1")["used"] == 20 and stock_qty("Atta 50kg") == 20       # nothing changed yet
    out = S.decide_adjust(T, adj["id"], True, adj["hash"], by_tap=True)
    assert out["status"] == "approved"
    assert S.bin_view(T, "A-1-1")["used"] == 17 and stock_qty("Atta 50kg") == 18
    with pytest.raises(S.WarehouseError, match="pehle se approved"):
        S.decide_adjust(T, adj["id"], True, adj["hash"], by_tap=True)
    led = S.ledger(T, sku="atta")["moves"]
    assert any(m["kind"] == "adjust" and m["ref"] == adj["number"] and m["synced"] for m in led)
    # stale: stock moved after the card -> nothing changes
    c2 = S.count_plan(T, bins=["A-1-1"])
    S.count_enter(T, c2["id"], [{"bin": "A-1-1", "item": "atta", "qty": 15}])
    a2 = S.count_close(T, c2["id"])["adjust"]
    S.move(T, "atta", "A-1-1", "A-2-1", 1)
    with pytest.raises(S.WarehouseError, match="hila"):
        S.decide_adjust(T, a2["id"], True, a2["hash"], by_tap=True)
    assert S.adjust_view(T, a2["id"])["status"] == "stale" and S.bin_view(T, "A-1-1")["used"] == 16
    # reject
    w = S.writeoff_request(T, "biscuit", "A-1-2", 2, reason="damaged", note="carton geela")
    assert w["kind"] == "writeoff" and w["lines"][0]["diff"] == -2
    r = S.decide_adjust(T, w["id"], False, w["hash"], "abhi nahi", by_tap=True)
    assert r["status"] == "rejected" and S.bin_view(T, "A-1-2")["used"] == 11
    var = S.export(T, "variance", count=c["number"])
    assert var["file"]["name"].endswith(".xlsx")


def test_abc_due_expiry_slow_labels_export_tick(wh, monkeypatch):
    S = wh
    setup(S)
    from app.db import session
    from app.warehouse.models import WhMove
    S.opening(T, lines=[{"item": "atta", "qty": 100, "bin": "B-1"}, {"item": "biscuit", "qty": 50, "bin": "A-1-1", "batch": "Z", "expiry": "2026-11-05"},
                        {"item": "mixer", "qty": 1, "bin": "A-2-2", "serials": ["S9"]}])
    p = S.pick_list(T, "list", text="atta 40")
    S.pick_confirm(T, p["id"], all_done=True)
    cl = S.classify(T)
    assert cl["basis"] == "value" and S.sku_view(T, "atta")["abc"] == "A"
    S.save_sku(T, sku="mixer", abc="A")
    assert S.classify(T) and S.sku_view(T, "mixer")["abc"] == "A"            # her fixed class stays
    ne = S.near_expiry(T)
    assert ne["near"][0]["name"] == "Biscuit carton" and ne["near"][0]["days_left"] == 13
    with session() as s:                                                      # make the mixer look old
        from sqlalchemy import select
        for m in s.scalars(select(WhMove)).all():
            if m.kind == "opening" and m.batch == "":
                m.day = "2026-01-01"
    sd = S.slow_dead(T)
    assert any(x["name"] == "Mixer grinder" for x in sd["dead"])
    lb = S.labels(T, "bins")
    assert lb["count"] >= 5 and lb["file"]["name"] == "labels_bins.pdf"
    assert S.labels(T, "skus", ["SKU-0002"])["count"] == 1
    for what in ("stock", "ledger", "abc", "expiry", "slow"):
        assert S.export(T, what)["file"]["name"].endswith(".xlsx")
    S.save_settings(T, morning_time="09:00")
    n = S.tick(datetime(2026, 10, 23, 4, 0, tzinfo=timezone.utc))           # 9:30 IST
    assert n == 1 and kinds(S)[-1] == "warehouse_day"
    assert S.tick(datetime(2026, 10, 23, 4, 30, tzinfo=timezone.utc)) == 0   # once a day
    d = S.day(T)
    assert "jaldi expire" in d["say"]


def test_tools_actors(wh):
    S = wh
    setup(S)
    from app.agent import warehouse_tools as W
    from app.agent.tools import ToolError
    ctx = conv_ctx()
    run = lambda _tool, **a: asyncio.run(W.WAREHOUSE_HANDLERS[_tool](ctx, **a))
    r = run("warehouse", action="grn", lines=[{"item": "atta", "qty": 10}], supplier="Shree")
    assert r["number"] == "GRN-0001"
    run("warehouse", action="putaway", grn="GRN-0001")
    w = run("warehouse", action="writeoff", item="atta", bin=S.stock_by_bin(T, sku="atta")[0]["bin"], qty=1, reason="damaged")
    assert w["status"] == "needs_tap" and S.adjust_view(T, w["id"])["status"] == "waiting"
    assert "decide" not in str(W.WAREHOUSE_TOOLS[0]["input_schema"]["properties"]["action"]["enum"])
    ctx.actor = "staff:abc"
    with pytest.raises(ToolError, match="owner"):
        run("warehouse", action="settings", name="X")
    assert run("warehouse", action="count", bins=["A-1-1"])["number"]
    ctx.actor = "customer:wa:9811111111"
    with pytest.raises(ToolError, match="graahak"):
        run("warehouse_dekho", what="day")
    with pytest.raises(ToolError, match="graahak"):
        run("warehouse", action="pick", text="atta 1")
    ctx.actor = "owner"
    d = run("warehouse_dekho", what="rules")
    assert "17(5)(h)" in d["itc"]
    assert run("warehouse_dekho", what="bin", bin="HOOLA-BIN:A-1-1")["code"] == "A-1-1"


def test_api(wh):
    S = wh
    setup(S)
    from app.warehouse.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/warehouse").status_code == 200
    assert c.post("/api/warehouse/bins", json={"code": "C-5", "kind": "pick", "capacity": 50}).json()["bin"]["code"] == "C-5"
    assert c.post("/api/warehouse/bins", json={"code": "bad--code"}).status_code == 400
    c.post("/api/warehouse/opening", json={"lines": [{"item": "atta", "qty": 9, "bin": "C-5"}]})
    cnt = c.post("/api/warehouse/counts", json={"bins": ["C-5"]}).json()
    assert "system" not in str(c.get(f"/api/warehouse/counts/{cnt['id']}").json()["lines"])
    c.post(f"/api/warehouse/counts/{cnt['id']}/enter", json={"entries": [{"bin": "C-5", "item": "atta", "qty": 8}]})
    adj = c.post(f"/api/warehouse/counts/{cnt['id']}/close", json={}).json()["adjust"]
    assert c.post(f"/api/warehouse/adjustments/{adj['id']}/decide", json={"hash": adj["hash"]}).status_code == 400
    ok = c.post(f"/api/warehouse/adjustments/{adj['id']}/decide", json={"yes": True, "hash": adj["hash"]}).json()
    assert ok["status"] == "approved" and S.bin_view(T, "C-5")["used"] == 8
    pk = c.post("/api/warehouse/picks", json={"source": "list", "text": "atta 3"}).json()
    assert pk["tasks"][0]["bin"] == "C-5"
    assert c.post(f"/api/warehouse/picks/{pk['id']}/confirm", json={"all": True}).json()["status"] == "done"
    assert c.get("/api/warehouse/recon").status_code == 200 and c.get("/api/warehouse/expiry").status_code == 200
    assert c.post("/api/warehouse/labels", json={"what": "skus"}).json()["count"] >= 1
