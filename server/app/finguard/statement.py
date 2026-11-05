"""Paisa Sahayak STATEMENT reader (register #1 money manager, #2 fee and charges auditor): her OWN bank / card statement rows in, counts out.

Pure functions: no database, no network, no model, nothing stored (statements are never kept; she hands them over each time).
What it will NOT do: move money, dispute a charge on its own, or call a charge wrong. It shows what the statement says, adds up the fee-like
lines by kind, and tells her what to ASK the bank. Category / fee words are heuristics (hers to correct with `overrides`).
"""
from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import date, datetime
from typing import Any

# (category, keywords) - plain words on a statement line. Heuristic, first match wins, her overrides come first.
CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    ("salary", ("salary", " sal ", "payroll")),
    ("emi_loan", ("emi", "loan", "nach", "ecs", "bajaj fin", "hdfc ltd")),
    ("investment", ("sip", "mutual fund", "zerodha", "groww", "upstox", "nps", "ppf", "icclgrow", "bse", "nse clearing")),
    ("insurance", ("insurance", "lic ", "policy", "premium")),
    ("rent", ("rent", "landlord")),
    ("food", ("swiggy", "zomato", "dominos", "restaurant", "cafe", "eatfit", "mcdonald", "kfc")),
    ("groceries", ("bigbasket", "blinkit", "zepto", "grocery", "dmart", "kirana", "instamart", "jiomart")),
    ("transport", ("uber", "ola", "rapido", "irctc", "metro", "redbus", "fastag", "petrol", "fuel", "indian oil", "hpcl", "bpcl")),
    ("bills", ("electricity", "bescom", "msedcl", "tata power", "water bill", "gas bill", "airtel", "jio", "vodafone", "vi ", "bsnl", "recharge", "broadband", "dth")),
    ("shopping", ("amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa")),
    ("subscriptions", ("netflix", "spotify", "prime", "hotstar", "youtube", "google play", "apple.com", "subscription")),
    ("cash", ("atm wdl", "atm cash", "cash wdl", "cash withdrawal", "nfs ")),
    ("health", ("pharmacy", "apollo", "hospital", "clinic", "medplus", "1mg", "pharmeasy")),
]

FEE_CLASSES: list[tuple[str, str, tuple[str, ...]]] = [
    ("sms_alert", "SMS / alert charges", ("sms chg", "sms charge", "sms alert", "alert chg")),
    ("annual_fee", "Annual / card / joining fee", ("annual fee", "annual chg", "amc", "card fee", "joining fee", "renewal fee", "membership fee")),
    ("min_balance", "Minimum / average balance penalty", ("min bal", "minimum bal", "nmcc", "non maintenance", "non-maintenance", "avg bal", "amb chg", "amb charge")),
    ("atm_fee", "ATM / transaction fee", ("atm chg", "atm charge", "atm fee", "atm txn fee", "atm wdl fee", "excess txn")),
    ("return_fee", "Returned cheque / ECS / NACH charge", ("ecs return", "chq ret", "chq return", "cheque return", "inward return", "nach return", "ach return", "bounce")),
    ("late_fee", "Late payment / overdue charge", ("late payment", "late fee", "overdue", "ovl chg")),
    ("card_interest", "Card finance / interest charge", ("finance charge", "interest charge", "int charge", "fin chg", "revolving")),
    ("forex_markup", "Forex mark-up / cross-currency", ("forex", "mark-up", "markup", "cross currency", "dcc ")),
    ("other_fee", "Other bank charges", ("service charge", "service chg", "processing fee", "proc fee", "debit card chg", "dd charge", "duplicate", "stmt chg", "statement charge")),
]
GST_WORDS = ("gst", "igst", "cgst", "sgst", "gst on")
GST_BAND = (17.0, 19.0)          # a fee's GST line is expected near 18%; outside this band = ask (assumed rate, verify)


def _num(v: Any) -> float:
    if v is None:
        return 0.0
    t = re.sub(r"[^\d.\-]", "", str(v).replace(",", ""))
    try:
        return float(t) if t not in ("", "-", ".") else 0.0
    except ValueError:
        return 0.0


def _day(v: Any) -> str:
    t = str(v or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%y", "%d %b %Y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(t, f).date().isoformat()
        except ValueError:
            continue
    return ""


def parse_csv(text: str) -> list[dict[str, Any]]:
    """Tolerant CSV: finds the header row (date + narration + debit/credit or amount), then reads rows. Returns [{date, narration, debit, credit}]."""
    rows = list(csv.reader(io.StringIO(text or "")))
    head, hi = None, -1
    for i, r in enumerate(rows[:40]):
        low = [c.strip().lower() for c in r]
        if any("date" in c for c in low) and any(k in " ".join(low) for k in ("narration", "description", "particulars", "remarks", "details")):
            head, hi = low, i
            break
    if head is None:
        raise ValueError("Statement ka header nahi mila (date, narration, debit/credit chahiye).")

    def col(*names):
        for n in names:
            for j, c in enumerate(head):
                if n in c:
                    return j
        return -1
    cd, cn = col("date"), col("narration", "description", "particulars", "remarks", "details")
    cdr, ccr = col("debit", "withdrawal", "dr"), col("credit", "deposit", "cr")
    ca, ct = col("amount"), col("type", "dr/cr", "cr/dr")
    out = []
    for r in rows[hi + 1:]:
        if len(r) <= max(cd, cn):
            continue
        d = _day(r[cd])
        if not d:
            continue
        deb = _num(r[cdr]) if cdr >= 0 and cdr < len(r) else 0.0
        cre = _num(r[ccr]) if ccr >= 0 and ccr < len(r) else 0.0
        if cdr < 0 and ccr < 0 and ca >= 0:
            amt = _num(r[ca])
            kind = (r[ct].strip().lower() if ct >= 0 and ct < len(r) else "")
            if kind.startswith("c") or amt > 0 and kind == "":
                cre = abs(amt)
            else:
                deb = abs(amt)
        out.append({"date": d, "narration": re.sub(r"\s+", " ", r[cn]).strip()[:160], "debit": abs(deb), "credit": abs(cre)})
    return out


def _clean_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows or []:
        d = _day(r.get("date"))
        if not d:
            continue
        out.append({"date": d, "narration": re.sub(r"\s+", " ", str(r.get("narration") or "")).strip()[:160],
                    "debit": abs(_num(r.get("debit"))), "credit": abs(_num(r.get("credit")))})
    return sorted(out, key=lambda x: x["date"])


def _hit(text: str, words: tuple[str, ...]) -> bool:
    t = " " + text.lower() + " "
    return any(w in t for w in words)


def category(narration: str, credit: bool, overrides: dict[str, str] | None = None) -> str:
    low = narration.lower()
    for pat, cat in (overrides or {}).items():
        if pat.lower() in low:
            return cat
    for cls, _label, words in FEE_CLASSES:
        if _hit(narration, words):
            return "fees"
    if _hit(narration, GST_WORDS) and not credit:
        return "fees"
    if credit and _hit(narration, ("refund", "reversal", "cashback", "rev ")):
        return "refund"
    for cat, words in CATEGORIES:
        if _hit(narration, words):
            return cat
    if "upi" in low:
        return "upi_other_credit" if credit else "upi_other"
    return "other_credit" if credit else "other"


def _key(narration: str) -> str:
    t = re.sub(r"\d{3,}", "", narration.lower())
    t = re.sub(r"[^a-z ]", " ", t)
    return " ".join(t.split()[:4])


def charges(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _clean_rows(rows)
    by_class: dict[str, dict[str, Any]] = {}
    gst_lines, dups, seen, flags = [], [], defaultdict(int), []
    fee_by_day: dict[str, float] = defaultdict(float)
    for r in rows:
        amt = r["debit"]
        if amt <= 0:
            continue
        sig = (r["date"], r["narration"].lower(), amt)
        seen[sig] += 1
        if seen[sig] == 2:
            dups.append(r)
        is_gst = _hit(r["narration"], GST_WORDS) and amt < 5000
        cls = next(((c, lab) for c, lab, w in FEE_CLASSES if _hit(r["narration"], w)), None)
        if cls and not is_gst:
            e = by_class.setdefault(cls[0], {"class": cls[0], "label": cls[1], "count": 0, "total": 0.0, "lines": []})
            e["count"] += 1
            e["total"] = round(e["total"] + amt, 2)
            e["lines"].append({"date": r["date"], "narration": r["narration"], "amount": amt})
            fee_by_day[r["date"]] += amt
        elif is_gst:
            gst_lines.append(r)
    gst_total = round(sum(r["debit"] for r in gst_lines), 2)
    for r in gst_lines:
        fees = fee_by_day.get(r["date"], 0.0)
        if fees > 0:
            pct = r["debit"] / fees * 100.0
            if not (GST_BAND[0] <= pct <= GST_BAND[1]):
                flags.append({"kind": "measured", "text": f"{r['date']}: GST Rs {r['debit']:.2f} us din ke charges Rs {fees:.2f} ka {pct:.1f}% hai (aam taur par ~18%): bank se breakup maangiye (dar maani hui hai, jaanch lijiye)."})
    fee_total = round(sum(v["total"] for v in by_class.values()), 2)
    for c in by_class.values():
        if c["count"] >= 3:
            flags.append({"kind": "heuristic", "text": f"{c['label']}: {c['count']} baar, kul Rs {c['total']:.2f}: kya yeh aapki sahmati wali sewa hai? Bank se band/waive karne ko poochh sakte hain."})
    for r in dups[:5]:
        flags.append({"kind": "measured", "text": f"{r['date']}: ek hi line Rs {r['debit']:.2f} do baar ({r['narration'][:40]}): dobara kata gaya ho sakta hai, bank se poochhiye."})
    for r in by_class.get("return_fee", {}).get("lines", [])[:3]:
        flags.append({"kind": "heuristic", "text": f"{r['date']}: return / bounce charge Rs {r['amount']:.2f}: pehle check kijiye ki wajah aapki taraf se thi ya bank/system ki."})
    span = ""
    if rows:
        d0, d1 = date.fromisoformat(rows[0]["date"]), date.fromisoformat(rows[-1]["date"])
        days = max((d1 - d0).days, 1)
        span = f"{rows[0]['date']} se {rows[-1]['date']} ({days} din)"
        year = round((fee_total + gst_total) * 365.0 / days, 2) if days >= 25 else None
    else:
        year = None
    return {"period": span, "fee_total": fee_total, "gst_on_charges": gst_total, "all_in_total": round(fee_total + gst_total, 2),
            "yearly_projection": year, "projection_note": "Is statement ke hisaab se saal ka andaaza (sirf agar 25+ din ka statement ho)." if year else "",
            "classes": sorted(by_class.values(), key=lambda c: -c["total"]), "flags": flags,
            "note": "Yeh statement ki lines ka jod hai, kisi charge ko galat kehna nahi. Galat lage to bank ko likhiye (action=complaint). GST dar aur fee ki shabdawali maani hui hain: jaanch lijiye."}


def spend(rows: list[dict[str, Any]], overrides: dict[str, str] | None = None, budget: dict[str, float] | None = None) -> dict[str, Any]:
    rows = _clean_rows(rows)
    if not rows:
        raise ValueError("Statement mein koi line nahi mili.")
    months: dict[str, dict[str, Any]] = {}
    keyed: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        m = r["date"][:7]
        e = months.setdefault(m, {"month": m, "in": 0.0, "out": 0.0, "by_category": defaultdict(float)})
        cat = category(r["narration"], r["credit"] > 0 and r["debit"] == 0, overrides)
        if r["credit"] > 0:
            e["in"] += r["credit"]
        if r["debit"] > 0:
            e["out"] += r["debit"]
            e["by_category"][cat] += r["debit"]
            keyed[_key(r["narration"])][m].append(r["debit"])
    rec = []
    for k, per in keyed.items():
        if len(per) >= 3 and k:
            amts = [sum(v) / len(v) for v in per.values()]
            if max(amts) - min(amts) <= 0.05 * max(amts) + 1:
                rec.append({"what": k, "months": len(per), "avg_amount": round(sum(amts) / len(amts), 2)})
    out_m = []
    for m in sorted(months):
        e = months[m]
        cats = {c: round(v, 2) for c, v in sorted(e["by_category"].items(), key=lambda x: -x[1])}
        row = {"month": m, "in": round(e["in"], 2), "out": round(e["out"], 2), "net": round(e["in"] - e["out"], 2), "by_category": cats}
        if budget:
            row["over_budget"] = {c: round(cats.get(c, 0) - b, 2) for c, b in budget.items() if cats.get(c, 0) > _num(b)}
        out_m.append(row)
    big = sorted([r for r in rows if r["debit"] > 0], key=lambda r: -r["debit"])[:5]
    flags = []
    full = out_m[len(out_m) // 2:] if len(out_m) > 2 else out_m
    for row in out_m:
        if row["in"] and row["out"] > row["in"]:
            flags.append({"kind": "measured", "text": f"{row['month']}: kharcha (Rs {row['out']:,.2f}) aay (Rs {row['in']:,.2f}) se zyada."})
    return {"months": out_m, "recurring": sorted(rec, key=lambda x: -x["avg_amount"])[:10], "biggest_debits": [
        {"date": r["date"], "narration": r["narration"], "amount": r["debit"]} for r in big], "flags": flags,
        "note": "Category shabdon se anumaan hai (apni category `overrides` se theek karwa sakte hain). Apne hi khaton ke beech transfer 'aay' aur 'kharcha' dono mein dikh sakte hain."}
