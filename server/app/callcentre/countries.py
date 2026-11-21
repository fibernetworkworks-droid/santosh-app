"""v0.999.67 AI TELECALLER - the calling rules per country, as DATA (owner: "ALSO MAKE IT GLOBAL NOT ONLY FOR INDIA").

Every outbound AI call is checked against the pack of the country of the number being called:
- local calling hours of the PERSON CALLED (their time zone, not the business's),
- who may be called at all (`cold_ok`: a person who never asked to be called),
- the AI announcement (always on, everywhere: Hoola's own rule, stricter than most laws),
- the national do-not-call register Hoola cannot read itself (the business confirms the list was checked).

Only India's pack is `checked` (its rules are the ones the Telecaller has used since v0.99: TRAI TCCCPR 2018 as amended
12 Feb 2025, calls 9 am - 9 pm, promotional calls to people without consent only from a registered 140 / 1600 line).
Every other pack is written from Hoola's own knowledge and marked `checked: False`: an outbound list to such a country
starts only after the owner confirms, for that country, that she checked the local law (`confirm_country`), and cold
lists stay closed there whatever she confirms. Rules here are a floor for safety, never legal advice.
"""
from __future__ import annotations

import re
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

# code: name, dial code, default time zone ("" = the country has several: the list must carry a time zone), currency,
# calling hours (local to the person called), cold_ok, the national do-not-call register (None = Hoola knows none),
# the consent the business needs, checked (rules verified against the law text by Hoola's maintainers)
PACKS: dict[str, dict[str, Any]] = {
    "IN": {"name": "India", "dial": "91", "tz": "Asia/Kolkata", "currency": "INR", "hours": ("09:00", "21:00"),
           "cold_ok": "registered_line", "dnc": "TRAI DND (NCPR)", "checked": True,
           "consent": "a person who asked to be called, your own customer, or a promotional call from a registered "
                      "140 / 1600 line after the DND check",
           "source": "TRAI Telecom Commercial Communications Customer Preference Regulations 2018, amended 12 Feb 2025"},
    "US": {"name": "United States", "dial": "1", "tz": "", "currency": "USD", "hours": ("08:00", "21:00"),
           "cold_ok": False, "dnc": "National Do Not Call Registry", "checked": False,
           "consent": "prior express consent (written consent for sales calls) - AI voices count as artificial voices "
                      "under the TCPA",
           "source": "TCPA 47 U.S.C. 227; FCC declaratory ruling on AI voices, Feb 2024 (not re-checked by Hoola)"},
    "CA": {"name": "Canada", "dial": "1", "tz": "", "currency": "CAD", "hours": ("09:00", "21:30"),
           "cold_ok": False, "dnc": "National Do Not Call List (CRTC)", "checked": False,
           "consent": "express consent, or an existing business relationship", "source": "CRTC Unsolicited Telecommunications Rules"},
    "GB": {"name": "United Kingdom", "dial": "44", "tz": "Europe/London", "currency": "GBP", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": "Telephone Preference Service (TPS)", "checked": False,
           "consent": "specific consent for automated calls", "source": "PECR regulation 19 (automated calls)"},
    "IE": {"name": "Ireland", "dial": "353", "tz": "Europe/Dublin", "currency": "EUR", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": "National Directory Database opt-out", "checked": False,
           "consent": "prior consent for automated calls", "source": "S.I. 336/2011"},
    "DE": {"name": "Germany", "dial": "49", "tz": "Europe/Berlin", "currency": "EUR", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "prior express consent (UWG 7)", "source": "UWG s.7"},
    "FR": {"name": "France", "dial": "33", "tz": "Europe/Paris", "currency": "EUR", "hours": ("10:00", "20:00"),
           "cold_ok": False, "dnc": "Bloctel", "checked": False, "consent": "prior consent; calls only on weekdays",
           "source": "Code de la consommation L223-1; decree of 2023 on calling hours", "days": [0, 1, 2, 3, 4]},
    "ES": {"name": "Spain", "dial": "34", "tz": "Europe/Madrid", "currency": "EUR", "hours": ("09:00", "21:00"),
           "cold_ok": False, "dnc": "Lista Robinson", "checked": False, "consent": "prior consent", "source": "LGT 11/2022"},
    "IT": {"name": "Italy", "dial": "39", "tz": "Europe/Rome", "currency": "EUR", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": "Registro delle Opposizioni", "checked": False, "consent": "prior consent",
           "source": "Codice privacy art. 130"},
    "NL": {"name": "Netherlands", "dial": "31", "tz": "Europe/Amsterdam", "currency": "EUR", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "prior consent (opt-in)", "source": "Telecommunicatiewet 11.7"},
    "AE": {"name": "United Arab Emirates", "dial": "971", "tz": "Asia/Dubai", "currency": "AED", "hours": ("09:00", "18:00"),
           "cold_ok": False, "dnc": "TDRA DNCR", "checked": False, "consent": "a person who asked, or your customer",
           "source": "TDRA telemarketing regulations"},
    "SA": {"name": "Saudi Arabia", "dial": "966", "tz": "Asia/Riyadh", "currency": "SAR", "hours": ("09:00", "21:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "a person who asked, or your customer", "source": "CST rules"},
    "QA": {"name": "Qatar", "dial": "974", "tz": "Asia/Qatar", "currency": "QAR", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "a person who asked, or your customer", "source": "CRA rules"},
    "SG": {"name": "Singapore", "dial": "65", "tz": "Asia/Singapore", "currency": "SGD", "hours": ("09:00", "21:00"),
           "cold_ok": False, "dnc": "Do Not Call Registry (PDPC)", "checked": False, "consent": "clear consent, DNC checked",
           "source": "PDPA Part 9"},
    "MY": {"name": "Malaysia", "dial": "60", "tz": "Asia/Kuala_Lumpur", "currency": "MYR", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "consent", "source": "PDPA 2010"},
    "AU": {"name": "Australia", "dial": "61", "tz": "", "currency": "AUD", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": "Do Not Call Register", "checked": False, "consent": "consent; no calls on Sundays",
           "source": "Telecommunications (Telemarketing and Research Calls) Industry Standard 2017", "days": [0, 1, 2, 3, 4, 5]},
    "NZ": {"name": "New Zealand", "dial": "64", "tz": "Pacific/Auckland", "currency": "NZD", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": "Do Not Call register (Marketing Association)", "checked": False, "consent": "consent",
           "source": "Fair Trading Act; marketing code"},
    "ZA": {"name": "South Africa", "dial": "27", "tz": "Africa/Johannesburg", "currency": "ZAR", "hours": ("08:00", "20:00"),
           "cold_ok": False, "dnc": "National Opt-Out Registry", "checked": False, "consent": "consent",
           "source": "Consumer Protection Act s.11 + regs"},
    "NG": {"name": "Nigeria", "dial": "234", "tz": "Africa/Lagos", "currency": "NGN", "hours": ("08:00", "20:00"),
           "cold_ok": False, "dnc": "NCC DND (2442)", "checked": False, "consent": "consent", "source": "NCC consumer code"},
    "KE": {"name": "Kenya", "dial": "254", "tz": "Africa/Nairobi", "currency": "KES", "hours": ("08:00", "20:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "consent", "source": "Data Protection Act 2019"},
    "BR": {"name": "Brazil", "dial": "55", "tz": "", "currency": "BRL", "hours": ("09:00", "21:00"),
           "cold_ok": False, "dnc": "Nao Me Perturbe", "checked": False, "consent": "consent (LGPD)", "source": "Anatel; LGPD"},
    "MX": {"name": "Mexico", "dial": "52", "tz": "", "currency": "MXN", "hours": ("09:00", "21:00"),
           "cold_ok": False, "dnc": "REPEP", "checked": False, "consent": "consent", "source": "Ley Federal de Proteccion al Consumidor"},
    "PH": {"name": "Philippines", "dial": "63", "tz": "Asia/Manila", "currency": "PHP", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "consent", "source": "Data Privacy Act 2012"},
    "ID": {"name": "Indonesia", "dial": "62", "tz": "", "currency": "IDR", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "consent", "source": "PDP Law 2022"},
    "PK": {"name": "Pakistan", "dial": "92", "tz": "Asia/Karachi", "currency": "PKR", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": "PTA DNCR (3627)", "checked": False, "consent": "consent", "source": "PTA telemarketing regs"},
    "BD": {"name": "Bangladesh", "dial": "880", "tz": "Asia/Dhaka", "currency": "BDT", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "consent", "source": "BTRC"},
    "LK": {"name": "Sri Lanka", "dial": "94", "tz": "Asia/Colombo", "currency": "LKR", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "consent", "source": "PDPA 2022"},
    "NP": {"name": "Nepal", "dial": "977", "tz": "Asia/Kathmandu", "currency": "NPR", "hours": ("09:00", "20:00"),
           "cold_ok": False, "dnc": None, "checked": False, "consent": "consent", "source": "NTA"},
}
# the countries a +1 number can be (NANP): Canada or the US - the list must say which, with a time zone
_DIAL = sorted(((p["dial"], c) for c, p in PACKS.items()), key=lambda x: -len(x[0]))
UNKNOWN = {"name": "this country", "dial": "", "tz": "", "currency": "", "hours": ("09:00", "20:00"), "cold_ok": False,
           "dnc": None, "checked": False, "consent": "consent", "source": "no pack - Hoola has no rules for this country"}


def pack(code: str) -> dict[str, Any]:
    return PACKS.get((code or "").upper(), UNKNOWN) | {"code": (code or "").upper()}


def digits(v: Any) -> str:
    return re.sub(r"\D", "", str(v or ""))


def e164(v: Any, default_country: str = "IN") -> str:
    """Any written number -> +<country><number>. A number with + or 00 keeps its own country; a local number gets the
    list's country. '' when it cannot be a phone number."""
    raw = str(v or "").strip()
    d = digits(raw)
    if not d:
        return ""
    if raw.startswith("+"):
        return f"+{d}" if 8 <= len(d) <= 15 else ""
    if d.startswith("00"):
        d = d[2:]
        return f"+{d}" if 8 <= len(d) <= 15 else ""
    p = pack(default_country)
    dial = p.get("dial") or ""
    if (default_country or "").upper() == "IN":
        from . import rules as R
        return R.phone_e164(raw)
    if d.startswith(dial) and len(d) > len(dial) + 6:
        return f"+{d}" if len(d) <= 15 else ""
    d = d.lstrip("0")
    return f"+{dial}{d}" if dial and 6 <= len(d) <= 12 else ""


def country_of(number: str) -> str:
    """'+44..' -> 'GB'. A +1 number is 'US' unless the list says CA. '' when unknown."""
    d = digits(number)
    for dial, code in _DIAL:
        if d.startswith(dial):
            return "US" if dial == "1" else code
    return ""


def tz_of(code: str, given: str = "") -> str:
    """The person's time zone: the one the list gives (when real), else the country's only one, else ''."""
    if given:
        try:
            ZoneInfo(given)
            return given
        except Exception:      # noqa: BLE001 - a wrong name is no time zone
            return ""
    return pack(code).get("tz") or ""


def _hm(v: str) -> time:
    h, m = (v or "09:00").split(":")
    return time(int(h), int(m))


def window(code: str, start: str = "", end: str = "") -> tuple[str, str]:
    """The calling hours for this country: hers, but never wider than the pack's."""
    lo, hi = pack(code)["hours"]
    s = max(_hm(start or lo), _hm(lo))
    e = min(_hm(end or hi), _hm(hi))
    return s.strftime("%H:%M"), e.strftime("%H:%M")


def can_call_now(code: str, tz: str, start: str = "", end: str = "", at: datetime | None = None) -> tuple[bool, str]:
    """(ok, why not) for calling a person in `code` / `tz` at `at` (now)."""
    if not tz:
        return False, "no time zone for this person (their country has several: add a time zone column)"
    try:
        local = (at or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo(tz))
    except Exception:          # noqa: BLE001
        return False, f"unknown time zone {tz}"
    days = pack(code).get("days")
    if days is not None and local.weekday() not in days:
        return False, "not a calling day there"
    s, e = window(code, start, end)
    if not (_hm(s) <= local.time() < _hm(e)):
        return False, f"outside calling hours there ({s}-{e} their time)"
    return True, ""


def basis_ok(code: str, basis: str, registered_line: bool, confirmed: bool) -> tuple[bool, str]:
    """May a person with this consent basis be called by AI in this country?
    basis: asked (enquired / asked to be called) | customer (an existing customer) | cold (never asked) | unknown."""
    p = pack(code)
    if p is UNKNOWN or not p.get("dial"):
        return False, "Hoola has no calling rules for this country yet"
    if not p["checked"] and not confirmed:
        return False, f"confirm first that you checked the calling law of {p['name']} (Settings > Countries)"
    if basis in ("asked", "customer"):
        return True, ""
    if basis == "cold" and p["cold_ok"] == "registered_line":
        return (True, "") if registered_line else (False, "a cold list needs your registered 140 / 1600 line (TRAI)")
    if basis == "cold":
        return False, f"people who never asked to be called are not called in {p['name']}"
    return False, "unknown whether this person asked to be called"


def summary() -> list[dict[str, Any]]:
    return [{"code": c, "name": p["name"], "dial": "+" + p["dial"], "checked": p["checked"], "hours": "-".join(p["hours"]),
             "cold_calls": "registered line only" if p["cold_ok"] == "registered_line" else ("yes" if p["cold_ok"] else "no"),
             "dnc": p["dnc"], "consent": p["consent"], "needs_time_zone": not p["tz"]}
            for c, p in sorted(PACKS.items(), key=lambda x: x[1]["name"])]
