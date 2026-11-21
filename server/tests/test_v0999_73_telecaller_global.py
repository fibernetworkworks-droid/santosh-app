"""v0.999.73 TELECALLER GLOBAL (owner: "MAKE IT GLOBAL AS IT CAN BE USE BY EVERY CORNER OF WORLD").

Every country of the world has a calling pack; a country without written law gets Hoola's safe floor; a number tells
its own country and time zone; a country with several time zones is called only inside the hours in all of them; a
person abroad is called in their country's language; knowledge search reads every script.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.callcentre import countries as CO
from app.callcentre import knowledge as K
from app.callcentre.world import WORLD


def test_every_country_has_a_pack():
    assert len(WORLD) >= 240
    assert set(WORLD) <= set(CO.PACKS)
    for code in ("IN", "US", "KE", "PE", "FJ", "IS", "MN", "AG", "TO", "LS"):
        p = CO.pack(code)
        assert p["dial"] and p["zones"] and p["currency"], code
    for z in (z for p in CO.PACKS.values() for z in p["zones"]):
        ZoneInfo(z)                       # every zone is a real IANA zone


def test_written_packs_keep_their_law_and_floor_is_safe():
    assert CO.pack("IN")["checked"] and CO.pack("IN")["written"]
    assert CO.pack("FR")["written"] and CO.pack("FR")["days"] == [0, 1, 2, 3, 4]
    fl = CO.pack("PE")
    assert not fl["written"] and not fl["checked"] and fl["cold_ok"] is False and fl["hours"] == ("09:00", "20:00")
    assert CO.basis_ok("PE", "asked", False, confirmed=False)[0] is False         # her confirmation first
    assert CO.basis_ok("PE", "customer", False, confirmed=True) == (True, "")
    assert CO.basis_ok("PE", "cold", True, confirmed=True)[0] is False             # never a cold list on the floor


def test_number_tells_country():
    assert CO.country_of("+12125551234") == "US"
    assert CO.country_of("+51 912 345 678") == "PE"
    assert CO.country_of("+254712345678") == "KE"
    assert CO.country_of("+447700900123") == "GB"
    assert CO.e164("0712 345678", "KE") == "+254712345678"
    assert CO.e164("98765 43210", "IN") == "+919876543210"
    assert CO.e164("+44 20 7946 0000", "IN") == "+442079460000"


def test_whole_country_hours_when_no_time_zone():
    # 15:00 UTC = 10:00 New York, 05:00 Honolulu: not every US time zone is inside 8 am - 9 pm
    at = datetime(2026, 11, 18, 15, 0, tzinfo=ZoneInfo("UTC"))
    ok, why = CO.can_call_now("US", "", "", "", at)
    assert not ok and "every time zone" in why
    at = datetime(2026, 11, 18, 21, 0, tzinfo=ZoneInfo("UTC"))      # 16:00 NY, 11:00 Honolulu
    assert CO.can_call_now("US", "", "", "", at) == (True, "")
    assert CO.can_call_now("US", "America/New_York", "", "", datetime(2026, 11, 18, 15, 0, tzinfo=ZoneInfo("UTC")))[0]


def test_language_and_currency_follow_the_country():
    assert CO.lang_of("DE") == "de-DE" and CO.lang_of("BR") == "pt-BR" and CO.lang_of("ZZ") == "en-US"
    assert CO.pack("JP")["currency"] == "JPY"
    from app.callcentre.outbound import _lang_for
    assert _lang_for("MX", "IN") == "es-ES" and _lang_for("IN", "IN") == ""


def test_knowledge_reads_every_script():
    w = K.words_of("营业时间 Öffnungszeiten مرحبا Привет")
    assert "营业" in w and "öffnungszeiten" in w and "مرحبا" in w and "привет" in w
    assert K._kind_of("precio ¥3000") == "price"


def test_countries_summary_lists_the_world():
    s = CO.summary()
    assert len(s) == len(CO.PACKS) and any(not c["written"] for c in s)
    assert all(c["needs_time_zone"] is False for c in s)
