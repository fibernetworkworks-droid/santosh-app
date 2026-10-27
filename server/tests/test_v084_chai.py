"""v0.84 Chai Sahayak + Galla: a chai stall's sales from UPI alerts (only credits, nothing secret), best hours,
tomorrow's milk / sugar / patti from the menu and earlier days, stock orders waiting for her Haan, learning from the day."""
import asyncio
from datetime import datetime, time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_life import conv_ctx

T = "default"

ALERTS = [   # (title, text, expected rupees or None)
    ("Payment received", "₹50 received from RAHUL KUMAR", 50),
    ("", "Ramesh paid you ₹20.00", 20),
    ("Paytm for Business", "Received ₹ 1,250 from Mr. Anil Ingle. UPI Ref No. 412398765432", 1250),
    ("", "₹30 received in your BharatPe account from Priya", 30),
    ("", "Rs.40.00 credited to your account by SURESH, UTR 512345678901", 40),
    ("", "₹5,430 settled to your bank account", None),
    ("", "You paid ₹20 to Tea Point", None),
    ("", "Your OTP is 4821 for ₹500 payment received", None),
    ("", "₹200 cashback received", None),
    ("PhonePe", "Today you received ₹4,300 from 120 payments", None),
    ("", "₹500 added to your wallet", None),
    ("", "Request of ₹100 from Mohan", None),
    ("", "Payment of ₹60 to Mohan failed", None),
]


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


@pytest.fixture(autouse=True)
def _late_evening(env, monkeypatch):
    """The tests write payments at fixed hours of today (7 am ... 6 pm). The service rightly drops alerts from the
    future, so before 6 pm these tests failed every morning: pin the galla clock to 11:50 pm local today."""
    from app.galla import service as G
    end = datetime.combine(G.today(T), time(23, 50), G._tz(T)).astimezone(timezone.utc)
    monkeypatch.setattr(G, "now", lambda: end)


def _at(days_ago: int, hour: int, minute: int = 0) -> int:
    from app.galla import service as G
    d = G.today(T) - timedelta(days=days_ago)
    return int(datetime.combine(d, time(hour, minute), G._tz(T)).timestamp() * 1000)


def test_alert_parser_counts_only_plain_credits():
    from app.galla.parse import parse_alert
    for title, text, want in ALERTS:
        got = parse_alert(title, text)
        assert (got["amount"] if got else None) == want, (text, got)
    assert parse_alert("", "Ramesh paid you ₹20.00")["payer"] == "Ramesh"
    assert parse_alert("", "Received ₹1,250 from Mr. Anil Ingle. UPI Ref No. 412398765432")["ref_tail"] == "5432"


def test_kotlin_parser_has_the_same_rules():
    """The phone runs the same rules: the word lists in PayAlerts.kt and parse.py must match."""
    from pathlib import Path
    kt = (Path(__file__).resolve().parents[2] / "tool" / "android" / "kotlin" / "PayAlerts.kt").read_text()
    for w in ("settle", "cashback", "otp", "paid you", "request", "wallet", "summary", "com.phonepe.app.business",
              "com.paytm.business", "com.google.android.apps.nbu.paisa.merchant", "com.bharatpe.app"):
        assert w in kt.lower(), w


def test_ingest_dedupe_and_day_summary(env):
    from app.galla import service as G
    items = [{"app": "com.phonepe.app.business", "amount": 10, "at_ms": _at(0, 7, m), "payer": "Ravi", "key": f"k{m}"}
             for m in range(0, 50, 5)]                                   # 10 chais 7-8 am
    items += [{"app": "com.paytm.business", "amount": 15, "at_ms": _at(0, 18, 10), "ref_tail": "123456", "key": "x1"},
              {"app": "com.paytm.business", "amount": 15, "at_ms": _at(0, 18, 11), "ref_tail": "123456", "key": "x2"},  # same ref
              {"app": "com.phonepe.app.business", "amount": 10, "at_ms": _at(0, 7, 0), "payer": "Ravi", "key": "k0"},   # same key
              {"app": "com.whatsapp", "amount": 99, "at_ms": _at(0, 9)},                                               # not allowed
              {"app": "net.one97.paytm", "amount": 99, "at_ms": _at(0, 9)},                                             # personal app, off
              {"title": "", "text": "Your OTP is 4821 for ₹500 payment received"}]
    r = G.ingest_alerts(T, items)
    assert r == {"added": 11, "skipped": 5}
    cash = G.add_cash(T, 300, "aaj", note="shaam")
    d = G.day_summary(T)
    assert d["total"] == "₹415" and d["upi_count"] == 11 and d["cash"] == "₹300"
    assert d["best"][0]["hour"] == 7 and "7 subah" in d["best"][0]["label"]
    G.void(T, cash["id"])
    assert G.day_summary(T)["total"] == "₹115"


def test_statement_import_only_credits(env):
    from app.galla import service as G
    t = G.today(T)
    rows = ["Date,Time,Description,Type,Amount,UPI Ref",
            f"{t:%d/%m/%Y},07:15:00,Received from RAVI,CR,10.00,412300001111",
            f"{t:%d/%m/%Y},07:20:00,Paid to MILK DAIRY,DR,500.00,412300002222",
            f"{t:%d/%m/%Y},08:05:00,Received from ASHA,CR,\"1,020.00\",412300003333",
            f"{t:%d/%m/%Y},08:05:00,Received from ASHA,CR,\"1,020.00\",412300003333"]
    r = G.import_statement(T, "phonepe.csv", "\n".join(rows).encode())
    assert r["added"] == 2 and r["skipped"] == 2
    assert G.day_summary(T)["total"] == "₹1,030"
    with pytest.raises(G.GallaError):
        G.import_statement(T, "x.csv", b"foo,bar\n1,2")


def test_best_hours_over_weeks(env):
    from app.galla import service as G
    items = []
    for d in range(1, 8):
        for m in range(0, 60, 3):
            items.append({"app": "com.phonepe.app.business", "amount": 10, "at_ms": _at(d, 17, m), "key": f"e{d}-{m}"})
        for m in range(0, 60, 10):
            items.append({"app": "com.phonepe.app.business", "amount": 10, "at_ms": _at(d, 8, m), "key": f"m{d}-{m}"})
    assert G.ingest_alerts(T, items)["added"] == len(items)
    assert G.ingest_alerts(T, [{"app": "com.phonepe.app.business", "amount": 5, "at_ms": _at(20, 9)}])["added"] == 0   # too old
    h = G.best_hours(T, 28)
    assert h["top"][0]["hour"] == 17 and "5 shaam" in h["text"]


def test_plan_from_menu_history_weather_and_stock_orders(env):
    from app.chai import service as C
    from app.galla import service as G
    conv = conv_ctx().conversation_id
    assert C.plan_tomorrow(T)["needs"] == "typical_cups"                   # nothing known yet: asks her
    C.save_settings(T, stall_name="Meghana Tapri", menu=[{"name": "Chai", "price": 10, "milk_ml": 60, "sugar_g": 8, "tea_g": 3, "share": 100}],
                    other_pct=0, cash_pct=0, safety_pct=10, milk_packet_ml=500,
                    suppliers=[{"name": "Gopal doodhwala", "phone": "+91 98220 11111", "items": ["milk"]},
                               {"name": "Blinkit", "items": ["sugar", "tea"], "site": "blinkit"}])
    tomorrow = G.today(T) + timedelta(days=1)
    for wk in (1, 2, 3):            # same weekday: 200 cups (₹2,000 UPI) each
        day_ago = (G.today(T) - (tomorrow - timedelta(days=7 * wk))).days
        G.add_cash(T, 2000, (G.today(T) - timedelta(days=day_ago)).isoformat(), hour=9, source="manual")
    C.set_stock(T, milk_l=1, sugar_kg=0.5, tea_kg=10)
    p = C.plan_tomorrow(T, weather={"tomorrow_rain_chance_pct": 80, "tomorrow_max_c": 29}, conv=conv)
    assert p["cups"] == 220                                                  # 200 + 10% rain
    assert p["need"]["milk_l"] == pytest.approx(220 * 0.06 * 1.1, abs=0.01)  # 14.52 L
    assert p["buy"]["milk_l"] == 14.0                                        # minus 1 L left, in 500 ml packets
    assert p["buy"]["sugar_kg"] > 0 and "tea_kg" not in p["buy"]             # sugar for ~0.3 day left; patti enough
    sups = {o["supplier"]: o for o in p["orders"]}
    assert set(sups) == {"Gopal doodhwala", "Blinkit"}
    assert sups["Gopal doodhwala"]["wa_link"].startswith("https://wa.me/919822011111?text=")
    assert "14 litre doodh" in sups["Gopal doodhwala"]["text"] and sups["Gopal doodhwala"]["status"] == "pending"
    assert any("baarish" in r for r in p["reasons"]) and _events("chai_plan")
    # a new plan replaces the unanswered cards
    p2 = C.plan_tomorrow(T, conv=conv)
    assert p2["cups"] == 200 and len(p2["orders"]) == 2
    # her Haan: the doodhwala card gives her the WhatsApp draft; nothing is sent by Hoola
    gid = next(o["id"] for o in p2["orders"] if o["supplier"] == "Gopal doodhwala")
    r = C.decide_order(T, gid, True, conv)
    assert r["order"]["status"] == "approved" and "Bhejo" in r["say"]
    with pytest.raises(C.ChaiError):
        C.decide_order(T, gid, False)
    bid = next(o["id"] for o in p2["orders"] if o["supplier"] == "Blinkit")
    assert C.decide_order(T, bid, False)["order"]["status"] == "rejected"


def test_learns_milk_per_cup_and_cash_share(env):
    from app.chai import service as C
    from app.galla import service as G
    C.save_settings(T, menu=[{"name": "Chai", "price": 10, "milk_ml": 50, "sugar_g": 8, "tea_g": 2, "share": 100}],
                    other_pct=0, cash_pct=50, safety_pct=0, milk_packet_ml=0, typical_cups=100)
    t = G.today(T)
    # plan for today (as if made yesterday): 100 cups -> 5 L
    p = C.plan_tomorrow(T, for_date=t.isoformat())
    assert p["buy"]["milk_l"] == 5.0
    # the real day: ₹600 UPI + ₹400 cash = 100 cups; 0 L left and it ran out at 6 pm -> more milk per cup than 50 ml
    G.ingest_alerts(T, [{"app": "com.phonepe.app.business", "amount": 600, "at_ms": _at(0, 9), "key": "d1"}])
    fb = C.feedback(T, t.isoformat(), milk_left_l=0, ran_out_at="18:00", cash=400)
    st = C.settings(T)
    assert st["cash_learned"] == 1 and st["cash_pct"] == pytest.approx(40, abs=0.5)
    assert st["factor_learned"] == 1 and st["milk_factor"] > 1.0 and fb["learned"]
    assert C.get_plan(T, t.isoformat())["status"] == "done"


def test_tools_api_and_role(env):
    from app import main
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    assert roles.duty_of("chai") == "stall" and roles.kind_of("chai_dekho") == "read"
    assert roles.PRESETS["chai"]["role"] == "chai_stall"
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    assert "₹800" in run("chai", action="cash", amount=800)["say"]
    out = run("chai", action="alerts", alerts=[{"title": "", "text": "Ramesh paid you ₹20"},
                                               {"title": "", "text": "OTP 1234 ₹20 received"}])
    assert out["added"] == 1 and out["skipped"] == 1
    assert run("chai_dekho", what="today")["total"] == "₹820"
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["chai"](staff, action="setup", typical_cups=5))
    with TestClient(main.app) as c:
        assert "chai" in c.get("/healthz").json()["features"]
        pv = c.get("/privacy")
        assert pv.status_code == 200 and "notification access" in pv.text and "never leaves the phone" in pv.text
        r = c.post("/api/galla/alerts", json={"items": [{"app": "com.paytm.business", "amount": 15, "payer": "Asha",
                                                         "ref_tail": "9876", "key": "api1"}]})
        assert r.json() == {"added": 1, "skipped": 0}
        assert c.get("/api/galla/today").json()["total"] == "₹835"
        assert c.post("/api/galla/cash", json={"amount": 100, "hour": 8}).status_code == 200
        assert c.get("/api/galla/settings").json()["picked"][0] == "com.phonepe.app.business"
        c.put("/api/chai/settings", json={"typical_cups": 150, "stall_name": "Test Tapri"})
        plan = c.post("/api/chai/plan", json={}).json()
        assert plan["cups"] > 0 and plan["orders"]
        oid = plan["orders"][0]["id"]
        assert c.post(f"/api/chai/orders/{oid}", json={"approve": True}).json()["order"]["status"] == "approved"
        assert c.post("/api/chai/feedback", json={"milk_left_l": 1}).status_code == 200
        assert c.get("/api/galla/hours").status_code == 200
        f = ("s.csv", "Date,Amount,Type\n" + f"{datetime.now().strftime('%d/%m/%Y')},50,CR\n", "text/csv")
        assert c.post("/api/galla/statement", files={"file": f}).json()["added"] == 1
