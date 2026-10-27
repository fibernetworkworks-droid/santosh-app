"""v0.107 Thok Sahayak: order text -> priced draft from HER stock list (bulk tiers, GST split by state, stock + credit +
e-way checks) -> bill only on her Haan (number, PDF, stock down, due date) -> payments fill oldest bills (cash Rs 2 lakh
warning) -> cheques pending / cleared / bounced with Sec 138 dates -> outstanding + aging + reminder drafts + route ->
purchases (stock up, average cost, MSME due, TDS Sec 393(1)) -> reorder + margins -> day note, tools + API."""
import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 22)            # a Thursday
_C = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin(body14: str) -> str:
    total = 0
    for i, ch in enumerate(body14):
        prod = _C.index(ch) * (1 if i % 2 == 0 else 2)
        total += prod // 36 + prod % 36
    return body14 + _C[(36 - total % 36) % 36]


ME = gstin("27AAAAA1111A1Z")
GUPTA = gstin("27BBBBB2222B1Z")
GOA = gstin("30CCCCC3333C1Z")


@pytest.fixture
def thok(env, monkeypatch):
    from app.thok import service as S
    monkeypatch.setattr(S, "today", lambda t: DAY)
    return S


def setup(S):
    S.save_settings(T, firm="Ingle Traders", gstin=ME, address="Main Road, Akola", phone="9822000000", bank="SBI Akola, A/c on request",
                    prefix="IT", credit_days=15)
    S.save_party(T, "Gupta Kirana", kind="customer", phone="9811111111", gstin=GUPTA, credit_limit=100000, route="Thu")
    S.save_party(T, "Goa Mart", kind="customer", phone="9833333333", gstin=GOA, credit_days=30)
    S.save_party(T, "Shree Mills", kind="supplier", phone="9844444444", msme=True)
    S.save_item(T, "Atta 50kg", price=1500, gst_pct=5, unit="bag", qty=40, hsn="1101", cost=1400, supplier="Shree Mills", lead_days=3,
                tiers=[{"min": 20, "price": 1450}])
    S.save_item(T, "Cheeni 50kg", price=2100, gst_pct=5, unit="bag", qty=10, hsn="1701")
    S.save_item(T, "Fortune Oil 15L", price=2000, gst_pct=5, unit="tin", qty=20, hsn="1512", cost=1900, low_at=5)


def test_rules():
    from app.thok import rules as R
    o = R.parse_order("Atta 10 bori, cheeni 5 bag @ 4200\n20 kg toor dal aur Parle-G 12 peti")
    assert [x["item"] for x in o] == ["Atta", "cheeni", "toor dal", "Parle-G"] and o[1]["rate"] == 4200 and o[0]["unit"] == "BAG"
    assert R.tax_split(1000, 18, True) == {"cgst": 90.0, "sgst": 90.0, "igst": 0.0, "tax": 180.0}
    assert R.tax_split(1000, 5, False)["igst"] == 50.0
    assert R.eway_needed(60000, "27", "27") == (False, 100000.0) and R.eway_needed(60000, "27", "30")[0]
    assert R.hsn_digits(4e7) == 4 and R.hsn_digits(6e7) == 6
    assert R.credit_check(90000, 0, 100000, 20000, 0)["level"] == "stop"
    assert R.credit_check(1000, 500, 0, 100, 70)["level"] == "stop" and R.credit_check(1000, 500, 0, 100, 10)["level"] == "warn"
    st = R.cheque_steps(date(2026, 10, 1))
    assert st["notice_by"] == "2026-10-31"
    t = R.tds_on_purchase(4.8e6, 4e5, 1.5e8)
    assert t["applies"] and t["on"] == 2e5 and t["tds"] == 200.0
    assert not R.tds_on_purchase(4.8e6, 4e5, 5e7)["applies"]
    assert R.msme_due(date(2026, 10, 1), None) == date(2026, 10, 16) and R.msme_due(date(2026, 10, 1), 60) == date(2026, 11, 15)
    assert R.reorder_qty(60, 5, 3, 15) == 31.0 and R.money("2.5 lakh") == 250000


def test_order_bill_pay(thok):
    S = thok
    from app.net import deal
    setup(S)
    r = S.take_order(T, "Gupta", "atta 25 bori, cheeni 5 bag, fortune oil 2 tin, kaju 1 kg")
    o = r["order"]
    atta = next(x for x in o["lines"] if x["item"] == "Atta 50kg")
    assert atta["rate"] == 1450 and atta["cgst"] == atta["sgst"] and atta["igst"] == 0     # bulk tier, intra-state
    assert o["checks"]["missing"] == ["kaju"] and o["checks"]["eway"]["needed"] is False
    assert o["taxable"] == 25 * 1450 + 5 * 2100 + 2 * 2000 and o["total"] == round(o["taxable"] * 1.05)
    assert "haan" in r["say"] and o["status"] == "draft"
    b = S.bill(T, o["id"])
    v = b["order"]
    assert v["number"] == "IT/26-27/0001" and v["due_date"] == "2026-11-06" and b["file"]["name"].endswith(".pdf")
    assert b["draft"]["to"] == "9811111111"
    assert next(x for x in deal.stock(T) if x["name"] == "Atta 50kg")["qty"] == 15
    with pytest.raises(S.ThokError):
        S.bill(T, o["id"])
    pdf = S.invoice_pdf(T, o["id"])
    assert pdf[:4] == b"%PDF"
    # credit: Gupta now owes ~55k of 1 lakh; a 60k order breaks the limit
    big = S.take_order(T, "Gupta", "fortune oil 18 tin, cheeni 5 bag")["order"]
    assert big["checks"]["credit"]["level"] == "stop" and big["checks"]["short"] == []
    S.cancel_order(T, big["id"])
    # inter-state -> IGST + e-way bill
    g = S.take_order(T, "Goa Mart", "atta 10 bori, cheeni 5 bag, fortune oil 15 tin")["order"]
    assert g["intra"] is False and g["lines"][0]["igst"] > 0 and g["checks"]["eway"]["needed"]
    S.bill(T, g["id"])
    # payments: 20k cash + 1.9 lakh cash same day -> Sec 221 warning
    p1 = S.receive(T, "Gupta", 20000, "cash")
    assert p1["ledger"]["outstanding"] == v["total"] - 20000 and not p1["warning"]
    p2 = S.receive(T, "Gupta", 190000, "cash")
    assert "Sec 221" in p2["warning"]
    assert S.get_order(T, o["id"])["balance"] == 0
    led = S.party_view(T, "Gupta")["ledger"]
    assert led["outstanding"] < 0 and led["avg_days_to_pay"] == 0
    # cheque: pending, then bounced -> Goa bill open again with Sec 138 dates
    c = S.receive(T, "Goa Mart", 15000, "cheque", cheque_no="123456", cheque_date="2026-10-25", bank="HDFC")
    assert "mat daaliye" in c["say"] and S.party_view(T, "Goa Mart")["ledger"]["cheques_pending"] == 15000
    S.cheque(T, c["payment_id"], "cleared")
    assert S.get_order(T, g["id"])["paid"] == 15000
    bnc = S.cheque(T, c["payment_id"], "bounced", memo_date="2026-10-22")
    assert bnc["steps"]["notice_by"] == "2026-11-21" and S.get_order(T, g["id"])["paid"] == 0
    with pytest.raises(S.ThokError):
        S.receive(T, "Goa Mart", 100, "cheque")
    with pytest.raises(S.ThokError):
        S.save_party(T, "Bad GST", gstin="27AAAAA1111A1ZZ")


def test_outstanding_purchase_reorder(thok, monkeypatch):
    S = thok
    setup(S)
    S.save_settings(T, last_fy_turnover=150000000)
    o = S.take_order(T, "Gupta", "atta 30 bori")["order"]
    S.bill(T, o["id"], bill_date="2026-09-01")                 # due 16 Sep -> overdue 36 days
    out = S.outstanding(T)
    row = out["parties"][0]
    assert row["party"] == "Gupta Kirana" and row["overdue"] == o["total"] and row["oldest_overdue_days"] == 36
    assert out["aging"]["31-60"] == o["total"]
    d = S.reminder_drafts(T)["drafts"]
    assert d[0]["to"] == "9811111111" and "due date paar" in d[0]["text"] and "kaafi din" in d[0]["text"]
    rp = S.route_plan(T)
    assert rp["route"] == "Thu" and rp["visit"] == ["Gupta Kirana"]
    nxt = S.take_order(T, "Gupta", "cheeni 1 bag")["order"]
    assert nxt["checks"]["credit"]["level"] == "warn"
    # purchase: stock up, average cost, MSME due 15 days, TDS once over 50 lakh this FY
    p = S.purchase(T, "Shree Mills", "atta 100 bori @ 1300", bill_no="SM-9", bill_date="2026-10-20")
    assert p["due_date"] == "2026-11-04" and "MSME" in p["say"] and not p["tds"]["applies"]
    it = next(x for x in S.items(T) if x["name"] == "Atta 50kg")
    assert it["qty"] == 110 and 1300 < it["cost"] < 1400 and it["hsn"] == "1101"
    big = S.purchase(T, "Shree Mills", "atta 3800 bori @ 1300", bill_no="SM-10", bill_date="2026-10-21")
    assert big["tds"]["applies"] and big["tds"]["tds"] == round((130000 + 4940000 - 5000000) * 0.001, 2)
    assert S.payables(T)["msme_soon"] == [] and S.payables(T)["total"] > 0
    S.pay_supplier(T, "Shree Mills", 136500, "neft")
    assert S.party_view(T, "Shree Mills")["supplier"]["payable"] < big["total"]
    with pytest.raises(S.ThokError):
        S.purchase(T, "Shree Mills", "atta 10 bori")              # no rate
    # reorder: oil sold fast, little left
    S.bill(T, S.take_order(T, "Goa Mart", "fortune oil 17 tin")["order"]["id"])
    ro = S.reorder(T)
    oil = [x for rows in ro["suppliers"].values() for x in rows if x["item"] == "Fortune Oil 15L"][0]
    assert oil["free"] == 3 and oil["order_qty"] > 0
    m = S.margins(T, 60)
    assert m["sales"] > 0 and any(x["item"] == "Atta 50kg" and x["margin_pct"] is not None for x in m["items"])
    day = S.day(T)
    assert day["sales"] > 0 and any(x["name"] == "Fortune Oil 15L" for x in day["low_stock"])
    st = S.statement_file(T, "Gupta")
    assert st["file"]["name"].endswith(".xlsx") and st["balance"] == o["total"]
    assert S.send_morning(T)["text"].startswith("Thok:")


def test_tools_api(thok):
    from app import main, voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    assert roles.duty_of("thok") == "wholesale_work" and roles.kind_of("thok_dekho") == "read" and "thok" in voice.VOICE_TOOL_NAMES
    assert roles.PRESETS["wholesale"]["role"] == "wholesale_assistant"
    S = thok
    setup(S)
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    o = run("thok", action="order", party="Gupta Kirana", text="atta 2 bori")["order"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["thok"](staff, action="bill", order_id=o["id"]))
    assert run("thok", action="bill", order_id=o["id"])["order"]["number"].startswith("IT/")
    assert run("thok_dekho", what="outstanding")["total"] > 0
    with TestClient(main.app) as cl:
        assert "thok" in cl.get("/healthz").json()["features"]
        assert cl.get("/api/thok/day").json()["settings"]["firm"] == "Ingle Traders"
        n = cl.post("/api/thok/orders", json={"party": "Goa Mart", "text": "cheeni 2 bag"}).json()["order"]
        b = cl.post(f"/api/thok/orders/{n['id']}/bill", json={"lines": [{"item": "Cheeni 50kg", "qty": 1}]}).json()
        assert b["order"]["lines"][0]["qty"] == 1 and b["order"]["number"] == "IT/26-27/0002"
        assert cl.post("/api/thok/receive", json={"party": "Goa Mart", "amount": 1000, "mode": "upi"}).status_code == 200
        assert cl.get("/api/thok/outstanding").status_code == 200
        assert cl.get("/api/thok/reorder").status_code == 200
        assert cl.get("/api/thok/bogus").status_code == 404
        assert cl.post("/api/thok/orders", json={"party": "Nobody", "text": "atta 1 bori"}).status_code == 400
        assert cl.post("/api/thok/purchases", json={"supplier": "Shree Mills", "text": "atta 5 bori @ 1350", "bill_no": "X1"}).status_code == 200
        assert cl.get("/api/thok/parties").json()["parties"]
        assert cl.post(f"/api/thok/orders/{n['id']}/bogus", json={}).status_code == 404
