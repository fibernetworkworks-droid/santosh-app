import datetime as dt

import pytest

from app.bazar.connectors.base import ToolError, rupees, to_paise
from app.bazar.connectors.shops import parse_lines
from app.bazar.connectors.sms_parser import parse_sms
from app.bazar.connectors.timeparse import IST, parse_when
from app.bazar.connectors.upi import build_upi_intent, valid_vpa
from app.bazar.packs.registry import registry


def test_159_mvp_packs_load():
    reg = registry()
    assert len(reg.packs) == 160   # 159 MVP packs + Mera PC
    assert all(p.phase == "MVP" for p in reg.packs.values())
    by = {}
    for p in reg.packs.values():
        by[p.executor] = by.get(p.executor, 0) + 1
    assert by == {"bbps": 98, "shop": 20, "upi": 15, "native": 13, "ride": 7, "mcp": 6, "pc": 1}


def test_rupees_and_paise():
    assert rupees(124000) == "₹1,240"
    assert rupees(12345678) == "₹1,23,456.78"
    assert to_paise("₹1,240.50") == 124050
    with pytest.raises(ToolError):
        to_paise("abc")


def test_upi_intent():
    url = build_upi_intent("priya.demo@okaxis", "Priya", 50000, "dinner", tr="SNT1")
    assert url.startswith("upi://pay?pa=priya.demo%40okaxis") and "am=500.00" in url and "tr=SNT1" in url and "cu=INR" in url
    assert valid_vpa("abc@ybl") and not valid_vpa("abc") and not valid_vpa("a b@x")
    with pytest.raises(ToolError):
        build_upi_intent("bad", "x", 100)
    with pytest.raises(ToolError):
        build_upi_intent("a@ybl", "x", 20_000_000)


def test_parse_lines_hinglish_marathi():
    assert parse_lines("Ramesh bhau ke dukaan se 5 kilo atta aur 1 litre tel bhejo") == [
        {"qty": 5.0, "unit": "kg", "name": "atta"}, {"qty": 1.0, "unit": "l", "name": "tel"}]
    assert parse_lines("dedh kilo sakhar ani ek dozen kele")[0] == {"qty": 1.5, "unit": "kg", "name": "sakhar"}
    assert parse_lines("500g paneer")[0] == {"qty": 500.0, "unit": "g", "name": "paneer"}


def test_sms_parser():
    p = parse_sms("Rs.1,240.00 debited from A/c XX1234 on 12-10-26 to VPA zomato@icici. -HDFC Bank", dt.date(2026, 10, 18))
    assert p["amount_paise"] == 124000 and p["direction"] == "debit" and p["category"] == "food" and p["occurred_on"] == dt.date(2026, 10, 12)
    assert parse_sms("Your OTP is 123456 for Rs 500 txn") is None
    c = parse_sms("INR 25,000.00 credited to your A/c XX9 on 01-10-2026. -SBI", dt.date(2026, 10, 18))
    assert c["direction"] == "credit" and c["category"] == "income"


def test_parse_when():
    now = dt.datetime(2026, 10, 18, 19, 0, tzinfo=IST)
    assert parse_when("kal subah 7 baje", now) == dt.datetime(2026, 10, 19, 7, 0, tzinfo=IST)
    assert parse_when("shaam 6 baje", now) == dt.datetime(2026, 10, 19, 18, 0, tzinfo=IST)  # 6 pm already passed today
    assert parse_when("at 9:30 pm", now) == dt.datetime(2026, 10, 18, 21, 30, tzinfo=IST)
    assert parse_when("2 ghante baad", now) == now + dt.timedelta(hours=2)
    assert parse_when("hello", now) is None


def test_keyword_match_routes_bills_and_shops():
    reg = registry()
    top = [p.executor for p, _ in reg.match("bijli ka bill bhar do", limit=3)]
    assert top[0] == "bbps"
    assert reg.match("5 kilo atta kirana se", limit=1)[0][0].id == "kirana-store"
