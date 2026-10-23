"""Godown Sahayak rules: pure functions (no database). Locations, walking order, FEFO, putaway scoring, ABC classes,
count schedule, count tolerance, write-off notes, hashes, small parsers.

Starter numbers here (count every 30 / 90 / 180 days, ABC 80 / 95 %, tolerances) are good practice, not law: she can change them.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from typing import Any

NEVER = (
    "Count ke baad stock badalna (adjustment / write-off) sirf aapke tap se: Hoola sirf card banata hai.",
    "Paisa kabhi nahi: na supplier ko, na kisi debit note ka bhugtan; GST ITC reverse karna aapke CA ka kaam.",
    "Count sheet par system ki maatra nahi dikhti (blind count), taaki ginti sach ho.",
    "Expired maal pick list mein kabhi nahi jaata; quarantine bin mein rakhne ka sujhaav milta hai.",
    "Daam stock list (Hoola Deals) / Thok ki cost se padhe jaate hain; yahan dobara nahi likhe jaate.",
)

BIN_KINDS = {"pick": "Pick bin", "bulk": "Bulk / reserve", "receiving": "Receiving (aaya maal)", "dispatch": "Dispatch",
             "quarantine": "Quarantine (rok)", "damage": "Toota / kharab"}
PICKABLE = ("pick", "bulk", "receiving")
TRACK = ("none", "batch", "serial")
COUNT_DAYS = {"A": 30, "B": 90, "C": 180}          # her design: A monthly, B quarterly, C half-yearly (editable)
ABC_SPLIT = (80.0, 95.0)                            # cumulative value share: A up to 80 %, B up to 95 %, C rest
TOLERANCE = {"A": {"units": 1, "pct": 0.5}, "B": {"units": 2, "pct": 1.0}, "C": {"units": 5, "pct": 3.0}}
NEAR_EXPIRY_DAYS = 30
SLOW_DAYS = 60
DEAD_DAYS = 180
REASONS = {"damaged": "Toota / kharab", "expired": "Expiry nikal gayi", "lost": "Gum / nahi mila", "theft": "Chori",
           "count": "Ginti mein farak", "found": "Zyada mila", "sample": "Free sample / gift", "other": "Aur"}

ITC_NOTE = ("GST: jo maal kam hua / toota / expire hua / chori hua / likh diya (write-off) ya sample-gift mein gaya, us par liya ITC "
            "wapas karna hota hai - CGST Act Section 17(5)(h). Kitna aur kab, apne CA se GSTR-3B ke liye poochhiye.")
RECORDS_NOTE = ("Rule 56 (CGST Rules): stock register mein opening, aamad, supply, kam / chori / nasht / write-off / sample, aur closing "
                "dikhna chahiye; har godown GST registration mein 'additional place of business' ho. Section 36: record 72 mahine.")
FOOD_NOTE = ("Khaane ka maal: FSSAI storage licence / registration (1 Apr 2026 se nayi turnover seema), FEFO, saaf-safai, pest control; "
             "cold storage ho to taapmaan ka register.")


# ---------------------------------------------------------------- small helpers
def r3(x: float) -> float:
    return round(float(x or 0.0) + 0.0, 3)


def num(v: Any, lo: float = -1e9, hi: float = 1e9) -> float | None:
    if v in (None, ""):
        return None
    try:
        x = float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return x if lo <= x <= hi else None


def qtxt(q: float | None) -> str:
    if q is None:
        return "?"
    return f"{int(q)}" if float(q) == int(q) else f"{q:g}"


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(v or "").lower())).strip()


def canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def hash_of(*parts: Any) -> str:
    return hashlib.sha256("|".join(canon(p) for p in parts).encode()).hexdigest()[:24]


def iso(d: date | None) -> str:
    return d.isoformat() if d else ""


def parse_date(v: Any) -> date | None:
    """'2027-03-31', '31-03-2027', '31/3/27', '03/2027' (month-year: last day of that month)."""
    if isinstance(v, date):
        return v
    s = str(v or "").strip()
    if not s:
        return None
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    try:
        if m:
            return date(int(m[1]), int(m[2]), int(m[3]))
        m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", s)
        if m:
            y = int(m[3])
            return date(y + 2000 if y < 100 else y, int(m[2]), int(m[1]))
        m = re.fullmatch(r"(\d{1,2})[-/.](\d{2,4})", s)       # month-year printed on packs ("EXP 03/2027")
        if m:
            y, mo = int(m[2]), int(m[1])
            y = y + 2000 if y < 100 else y
            nxt = date(y + (mo // 12), mo % 12 + 1, 1)
            return nxt - timedelta(days=1)
    except ValueError:
        return None
    return None


# ---------------------------------------------------------------- locations
def _part_key(p: str) -> tuple:
    p = str(p or "")
    return (0, int(p), "") if p.isdigit() else (1, 0, p.upper())


def split_code(code: str) -> dict[str, str]:
    """'A-12' -> zone A, aisle 12; 'B-03-R2-4' -> zone B, aisle 03, rack R2, bin 4. Letters + numbers only."""
    parts = [p for p in re.split(r"[-/\s.]+", str(code or "").strip().upper()) if p]
    keys = ("zone", "aisle", "rack", "bin")
    out = {k: "" for k in keys}
    for k, p in zip(keys, parts[:4]):
        out[k] = re.sub(r"[^A-Z0-9]", "", p)[:8]
    return out


def make_code(zone: str = "", aisle: str = "", rack: str = "", bin_: str = "") -> str:
    parts = [re.sub(r"[^A-Z0-9]", "", str(x or "").upper())[:8] for x in (zone, aisle, rack, bin_)]
    return "-".join(p for p in parts if p)


def valid_code(code: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{1,8}(-[A-Z0-9]{1,8}){0,3}", str(code or "")))


def path_key(loc: dict[str, Any]) -> tuple:
    """Walking order: zone, then aisle; racks go up in odd aisles and come back down in even ones (serpentine), then bin."""
    a = _part_key(loc.get("aisle", ""))
    rk = _part_key(loc.get("rack", ""))
    odd = a[0] == 0 and a[1] % 2 == 1 or a[0] == 1
    rack = rk if odd else (rk[0], -rk[1], "".join(chr(255 - ord(c)) for c in rk[2]))
    return (_part_key(loc.get("zone", "")), a, rack, _part_key(loc.get("bin", "")))


# ---------------------------------------------------------------- FEFO / FIFO
def fefo_key(lot: dict[str, Any]) -> tuple:
    """First expiry first out; lots without expiry after them, oldest received first."""
    return (lot.get("expiry") or "9999-12-31", lot.get("received_on") or "9999-12-31", lot.get("path") or ())


def expiry_state(expiry: str, on: date, near_days: int = NEAR_EXPIRY_DAYS) -> str:
    d = parse_date(expiry)
    if not d:
        return ""
    if d < on:
        return "expired"
    if d <= on + timedelta(days=near_days):
        return "near"
    return "ok"


def shelf_left_pct(mfg: str, expiry: str, on: date) -> float | None:
    m, e = parse_date(mfg), parse_date(expiry)
    if not m or not e or e <= m:
        return None
    return round(max(0.0, (e - on).days) * 100.0 / (e - m).days, 1)


# ---------------------------------------------------------------- putaway
def putaway_plan(qty: float, bins: list[dict[str, Any]], sku_id: str, batch: str = "", fast: bool = False,
                 limit: int = 3) -> list[dict[str, Any]]:
    """Where to put `qty` of one SKU. bins: [{code, kind, capacity, used, skus: {sku_id: [batches]}, rank}] (rank 0 = nearest to
    dispatch). Same SKU (same batch best) first, then empty bins; fast movers near dispatch, slow ones further back; never more
    than a bin's free capacity; quarantine / damage / dispatch bins never."""
    total = max((b.get("rank", 0) for b in bins), default=0) or 1
    scored = []
    for b in bins:
        if b.get("kind") not in ("pick", "bulk") or b.get("active") is False:
            continue
        cap = b.get("capacity")
        free = None if cap is None else max(0.0, float(cap) - float(b.get("used") or 0.0))
        if free is not None and free <= 0:
            continue
        mine = b.get("skus", {}).get(sku_id)
        others = [k for k in b.get("skus", {}) if k != sku_id]
        score, why = 0.0, []
        if mine is not None:
            score += 50
            why.append("yahi SKU pehle se")
            if batch and batch in (mine or []):
                score += 10
                why.append("yahi batch")
        elif not b.get("skus"):
            score += 20
            why.append("khaali bin")
        if others:
            score -= 25 * len(others)
            why.append("doosra maal bhi hai")
        near = 1.0 - float(b.get("rank", 0)) / total
        if fast:
            score += 15 * near
            if near > 0.6:
                why.append("dispatch ke paas (tez bikta hai)")
        else:
            score += 8 * (1.0 - near)
        if b.get("kind") == "pick" and fast:
            score += 5
        if free is not None and free >= qty:
            score += 10
        scored.append((score, b, free, why))
    scored.sort(key=lambda x: (-x[0], x[1].get("rank", 0)))
    out, left = [], float(qty)
    for score, b, free, why in scored:
        if left <= 0 or len(out) >= limit:
            break
        put = left if free is None else min(left, free)
        if put <= 0:
            continue
        out.append({"bin": b["code"], "qty": r3(put), "why": ", ".join(why) or "jagah hai", "score": round(score, 1)})
        left = r3(left - put)
    if left > 0:
        out.append({"bin": "", "qty": r3(left), "why": "kisi bin mein jagah nahi: naya bin / capacity badhaiye", "score": 0})
    return out


# ---------------------------------------------------------------- ABC + schedule
def abc(items: list[dict[str, Any]], split: tuple[float, float] = ABC_SPLIT) -> dict[str, str]:
    """items: [{id, value, picks}] -> {id: A|B|C}. Value = yearly usage in rupees when known; else picks (velocity)."""
    use_value = any((x.get("value") or 0) > 0 for x in items)
    key = "value" if use_value else "picks"
    rows = sorted(items, key=lambda x: -(x.get(key) or 0))
    total = sum((x.get(key) or 0) for x in rows)
    out: dict[str, str] = {}
    if total <= 0:
        return {x["id"]: "C" for x in rows}
    cum = 0.0
    a_cut, b_cut = split
    for x in rows:
        v = x.get(key) or 0
        share_before = cum * 100.0 / total
        cum += v
        if v <= 0:
            out[x["id"]] = "C"
        elif share_before < a_cut:
            out[x["id"]] = "A"
        elif share_before < b_cut:
            out[x["id"]] = "B"
        else:
            out[x["id"]] = "C"
    return out


def count_due(cls: str, last: str, on: date, days: dict[str, int] | None = None) -> tuple[bool, int]:
    """(due?, days overdue (+) / left (-)). Never counted = due."""
    d = (days or COUNT_DAYS).get(cls or "C", COUNT_DAYS["C"])
    lc = parse_date(last)
    if not lc:
        return True, d
    gap = (on - lc).days - d
    return gap >= 0, gap


def within(diff: float, system: float, cls: str, tol: dict[str, dict] | None = None) -> bool:
    t = (tol or TOLERANCE).get(cls or "C", TOLERANCE["C"])
    allowed = max(float(t.get("units") or 0), abs(float(system or 0)) * float(t.get("pct") or 0) / 100.0)
    return abs(diff) <= allowed + 1e-9


def reason_of(text: str, diff: float) -> str:
    w = norm(text)
    for k, words in (("damaged", ("toot", "broken", "damage", "kharab", "phat", "leak")),
                     ("expired", ("expir", "expiry", "purana", "date nikal")), ("theft", ("chori", "theft", "stolen")),
                     ("sample", ("sample", "gift", "muft")), ("lost", ("gum", "lost", "missing", "nahi mila"))):
        if any(x in w for x in words):
            return k
    return "found" if diff > 0 else "count"


# ---------------------------------------------------------------- scans
def parse_scan(text: str) -> dict[str, str]:
    """What a scanned label says: our own 'HOOLA-BIN:A-12' / 'HOOLA-SKU:SKU-0003', else the raw code (her GTIN / barcode)."""
    t = str(text or "").strip()
    m = re.fullmatch(r"HOOLA-(BIN|SKU):([A-Z0-9-]{1,40})", t.upper())
    if m:
        return {"type": m[1].lower(), "code": m[2]}
    return {"type": "code", "code": t[:60]}


def parse_lines(text: str) -> list[dict[str, Any]]:
    """Her words 'atta 10 bori, cheeni 5 bag' -> [{item, qty, unit}] (Thok's parser, so both read lists the same way)."""
    from ..thok import rules as TR
    return [{"item": x["item"], "qty": x["qty"], "unit": x.get("unit", "")} for x in TR.parse_order(text)]
