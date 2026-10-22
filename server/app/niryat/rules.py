"""Export rules Hoola works to (researched 22 Oct 2026; sources in CLAUDE.md v0.110). Pure functions.

FEMA (RBI): export value realised and repatriated within 9 months of the shipment date (restored from 15 months; the
2026 regulations in force from 1 Oct 2026), 12 months when invoiced / settled in rupees; extensions only through the AD
bank. GST: exports are zero-rated - under LUT (Form RFD-11, one per financial year) without IGST, or with IGST paid and
refunded through the shipping bill. RoDTEP (FTP 2023) extended to 31 Dec 2026 at the Appendix 4R / 4RE rates and caps,
claimed by declaring it in the shipping bill. FTAs: UAE CEPA, Australia ECTA, EFTA TEPA (from 1 Oct 2025), UK CETA
(from 15 Jul 2026) - preference needs a certificate / declaration of origin (DGFT eCoO portal) and the rules of origin.
EU CBAM definitive phase from 1 Jan 2026 for iron & steel, aluminium, cement, fertilisers, hydrogen: the EU importer
needs the embedded-emissions data. US duty on Indian goods changed several times in 2025-26: always check the current
rate for the HS code before quoting.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

INCOTERMS = {
    "EXW": "Buyer picks up at your door; you only pack.", "FCA": "You hand over to the buyer's carrier / forwarder, export cleared.",
    "FAS": "Alongside the ship at the port (sea only).", "FOB": "Loaded on board at the Indian port; buyer pays sea freight + insurance.",
    "CFR": "You pay sea freight to the destination port; risk passes when loaded.", "CIF": "You pay freight + insurance to the destination port.",
    "CPT": "You pay carriage to the named place; risk passes at first carrier.", "CIP": "Carriage + insurance (all-risk) to the named place.",
    "DAP": "Delivered at the buyer's place, not unloaded, buyer pays import duty.", "DPU": "Delivered and unloaded at the named place.",
    "DDP": "Delivered with the buyer's import duty paid BY YOU - risky, check duty first."}
PAY_TERMS = {"advance": "100% advance (safest)", "lc": "Letter of credit (documents must match the LC exactly)",
             "dp": "D/P - documents against payment through banks", "da": "D/A - documents against acceptance (credit, ECGC cover advised)",
             "open": "Open account (highest risk: ECGC cover advised)", "part": "Part advance, balance against documents"}
FTA = {"AE": "India-UAE CEPA", "AU": "India-Australia ECTA", "GB": "India-UK CETA (from 15 Jul 2026)", "CH": "India-EFTA TEPA",
       "NO": "India-EFTA TEPA", "IS": "India-EFTA TEPA", "LI": "India-EFTA TEPA", "JP": "India-Japan CEPA", "KR": "India-Korea CEPA",
       "SG": "India-Singapore CECA", "MY": "India-Malaysia CECA / AIFTA", "TH": "ASEAN-India FTA", "VN": "ASEAN-India FTA",
       "ID": "ASEAN-India FTA", "PH": "ASEAN-India FTA", "LK": "India-Sri Lanka FTA", "NP": "India-Nepal treaty", "BT": "India-Bhutan agreement",
       "MU": "India-Mauritius CECPA", "BD": "SAFTA", "AF": "SAFTA"}
EU = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL",
      "PT", "RO", "SK", "SI", "ES", "SE"}
CBAM_CHAPTERS = ("72", "73", "76", "2523", "2808", "2814", "2834", "3102", "3105", "2804")
SANCTION_CHECK = {"RU": "Russia", "BY": "Belarus", "IR": "Iran", "KP": "North Korea", "SY": "Syria", "CU": "Cuba", "MM": "Myanmar",
                  "AF": "Afghanistan", "VE": "Venezuela"}
COUNTRIES = {"united states": "US", "usa": "US", "us": "US", "america": "US", "uk": "GB", "united kingdom": "GB", "england": "GB",
             "uae": "AE", "dubai": "AE", "united arab emirates": "AE", "saudi": "SA", "saudi arabia": "SA", "germany": "DE", "france": "FR",
             "netherlands": "NL", "italy": "IT", "spain": "ES", "australia": "AU", "canada": "CA", "singapore": "SG", "japan": "JP",
             "china": "CN", "bangladesh": "BD", "nepal": "NP", "sri lanka": "LK", "switzerland": "CH", "norway": "NO", "qatar": "QA",
             "oman": "OM", "kuwait": "KW", "bahrain": "BH", "malaysia": "MY", "thailand": "TH", "vietnam": "VN", "indonesia": "ID",
             "south africa": "ZA", "kenya": "KE", "nigeria": "NG", "russia": "RU", "iran": "IR", "belgium": "BE", "poland": "PL",
             "korea": "KR", "south korea": "KR", "mauritius": "MU", "egypt": "EG", "brazil": "BR", "mexico": "MX"}
CURRENCIES = ("USD", "EUR", "GBP", "AED", "AUD", "JPY", "SGD", "CAD", "CHF", "SAR", "INR")
REALISE_MONTHS = 9
REALISE_MONTHS_INR = 12
RODTEP_UNTIL = date(2026, 12, 31)

NEVER = ("Paisa Hoola nahi leta / bhejta; buyer seedha aapke AD bank mein bhejta hai.",
         "Shipping bill (ICEGATE), certificate of origin (DGFT eCoO), e-BRC aur forward contract aap / CHA / bank karte hain.",
         "Buyer ko PI / invoice / reminder sirf aapki haan se.",
         "Sanctioned desh / party ke saath sauda nahi: pehle jaanch.",
         "Galat HS code ya kam / zyada value nahi: customs mein jurmana.")


def iec_ok(iec: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{10}", (iec or "").strip().upper()))


def country(v: str) -> str:
    s = str(v or "").strip()
    if len(s) == 2 and s.isalpha():
        return s.upper()
    return COUNTRIES.get(s.lower(), "")


def add_months(d: date, n: int) -> date:
    from calendar import monthrange
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def realise_by(ship_date: date, currency: str) -> date:
    return add_months(ship_date, REALISE_MONTHS_INR if currency == "INR" else REALISE_MONTHS)


def fob_value(total: float, incoterm: str, freight: float = 0.0, insurance: float = 0.0) -> float:
    """FOB = invoice value minus the freight / insurance included by the term (customs + RoDTEP + realisation use FOB)."""
    t = (incoterm or "FOB").upper()
    if t in ("CFR", "CPT"):
        return round(total - freight, 2)
    if t in ("CIF", "CIP", "DAP", "DPU", "DDP"):
        return round(total - freight - insurance, 2)
    return round(total, 2)


def rodtep(fob_inr: float, rate_pct: float, cap_per_unit: float = 0.0, qty: float = 0.0, on: date | None = None) -> dict:
    if on and on > RODTEP_UNTIL:
        return {"amount": 0.0, "note": "RoDTEP abhi 31 Dec 2026 tak notified hai; uske baad ki shipment ke liye DGFT notification dekhiye."}
    amt = fob_inr * rate_pct / 100
    if cap_per_unit and qty:
        amt = min(amt, cap_per_unit * qty)
    return {"amount": round(amt, 2), "note": "Shipping bill mein RoDTEP claim declare karna zaroori (baad mein nahi milta); e-scrip ICEGATE par."}


def checks(dest: str, hs_codes: list[str], incoterm: str, pay: str, currency: str) -> list[dict]:
    out = []
    if dest in SANCTION_CHECK:
        out.append({"level": "stop", "text": f"{SANCTION_CHECK[dest]}: pabandi (sanctions) wala desh. Bank, buyer aur maal ki pehle poori jaanch; bank payment rok sakta hai."})
    if dest in FTA:
        out.append({"level": "info", "text": f"{FTA[dest]}: buyer ko kam duty mil sakti hai. Certificate of origin DGFT eCoO portal se (rules of origin poore hon)."})
    if dest in EU and any(h.startswith(c) for h in hs_codes for c in CBAM_CHAPTERS):
        out.append({"level": "warn", "text": "EU CBAM (1 Jan 2026 se): steel / aluminium / cement / fertiliser par buyer ko embedded emissions ka data chahiye."})
    if dest == "US":
        out.append({"level": "warn", "text": "US duty 2025-26 mein kai baar badli: is HS code ki aaj ki duty check karke hi daam pakka kariye."})
    bad = [h for h in hs_codes if len(re.sub(r"\D", "", h)) != 8]
    if bad:
        out.append({"level": "warn", "text": "Export mein 8 ank ka ITC-HS code chahiye: " + ", ".join(bad or ["-"]) + "."})
    if (incoterm or "").upper() == "DDP":
        out.append({"level": "warn", "text": "DDP: buyer ke desh ki import duty aur VAT aapko deni hogi."})
    if pay in ("da", "open"):
        out.append({"level": "warn", "text": "Udhaar par export: ECGC policy / buyer limit lijiye."})
    return out


def doc_list(incoterm: str, pay: str, fta: bool, mode: str = "sea") -> list[str]:
    docs = ["Commercial invoice", "Packing list", "Shipping bill (CHA / ICEGATE)", "Bill of lading" if mode == "sea" else "Airway bill"]
    if (incoterm or "").upper() in ("CIF", "CIP"):
        docs.append("Insurance certificate")
    if fta:
        docs.append("Certificate of origin (DGFT eCoO, FTA wala)")
    else:
        docs.append("Certificate of origin (non-preferential, agar buyer maange)")
    if pay == "lc":
        docs.append("LC ki har shart wale kaagaz (naam, maatra, tareekh hubahu)")
    if pay in ("dp", "da"):
        docs.append("Bill of exchange + bank ko collection letter")
    return docs
