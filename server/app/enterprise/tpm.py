"""The technical PM's actual work: the computations, done in code.

A TPM's day is not writing paragraphs - it is answering questions that have one right answer:

    what is actually blocking the release          -> the critical path through the dependency graph
    who is over-committed and by how many days     -> capacity against real estimates
    are we getting faster or slower                -> lead time, cycle time, say-do ratio
    what is rotting in the RAID log                -> overdue, stale, unowned, high and open
    can we ship on Friday                          -> every gate, with the ones that fail named
    who owes me an update                          -> owners with no word since a date

Every one of those is arithmetic on rows, so it lives HERE and not in a prompt. The model picks the question and
reads the answer out; it never does the sum. That matters because a wrong critical path or a wrong capacity
number looks exactly as confident as a right one.

Rows come from whatever she has - a tracker through Composio, a sheet, or a paste - so the maths works before
anything is connected. Dates are plain YYYY-MM-DD; estimates are days.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

MAX_ROWS = 5000


class TpmError(Exception):
    pass


def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _day(v: Any) -> date | None:
    s = _s(v)[:10]
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _rows(rows: Any, what: str) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise TpmError(f"{what} ke liye rows chahiye.")
    if len(rows) > MAX_ROWS:
        raise TpmError(f"{MAX_ROWS} se zyada rows nahi - chhota kijiye.")
    out = [r for r in rows if isinstance(r, dict)]
    if not out:
        raise TpmError("Har row ek object honi chahiye.")
    return out


# ---------------------------------------------------------------- 1. what is really blocking the release
def critical_path(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Longest chain of work by duration. rows: id, title, days, depends_on [ids], status, owner.

    A cycle is reported, never silently broken: a dependency loop is a real planning bug and the TPM has to see
    it rather than get a confident wrong answer. Done work counts as zero, because it no longer delays anything.
    """
    items = _rows(rows, "critical path")
    by_id: dict[str, dict[str, Any]] = {}
    for r in items:
        rid = _s(r.get("id") or r.get("key") or r.get("ref"))
        if not rid:
            raise TpmError("Har row mein id chahiye.")
        by_id[rid] = {"id": rid, "title": _s(r.get("title") or r.get("summary"))[:200],
                      "days": max(0.0, _num(r.get("days") or r.get("estimate"), 0)),
                      "deps": [d for d in (r.get("depends_on") or r.get("deps") or []) if _s(d)],
                      "status": _s(r.get("status")).lower(), "owner": _s(r.get("owner"))}
    missing = sorted({d for v in by_id.values() for d in v["deps"] if d not in by_id})
    for v in by_id.values():
        v["deps"] = [d for d in v["deps"] if d in by_id]
        if v["status"] in ("done", "closed", "shipped", "resolved"):
            v["days"] = 0.0

    # longest path by memoised DFS; grey marks the stack, so a cycle is caught rather than looped on
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {k: WHITE for k in by_id}
    best: dict[str, tuple[float, list[str]]] = {}
    cycles: list[list[str]] = []

    def walk(nid: str, stack: list[str]) -> tuple[float, list[str]]:
        if colour[nid] == GREY:
            cycles.append(stack[stack.index(nid):] + [nid])
            return 0.0, []
        if colour[nid] == BLACK:
            return best[nid]
        colour[nid] = GREY
        node = by_id[nid]
        top_len, top_path = 0.0, []
        for d in node["deps"]:
            ln, pth = walk(d, stack + [nid])
            if ln > top_len:
                top_len, top_path = ln, pth
        colour[nid] = BLACK
        best[nid] = (top_len + node["days"], top_path + [nid])
        return best[nid]

    for k in by_id:
        if colour[k] == WHITE:
            walk(k, [])
    if cycles:
        loop = cycles[0]
        raise TpmError("Dependency mein chakkar hai (" + " -> ".join(loop) + "). Pehle ise todiye; "
                       "warna koi bhi tareekh sach nahi hogi.")
    end = max(best, key=lambda k: best[k][0]) if best else ""
    length, path = best.get(end, (0.0, []))
    blockers = [{"id": i, "title": by_id[i]["title"], "days": by_id[i]["days"], "owner": by_id[i]["owner"],
                 "status": by_id[i]["status"]} for i in path if by_id[i]["status"] not in
                ("done", "closed", "shipped", "resolved")]
    return {"din": round(length, 2), "raasta": path, "kaam": blockers,
            "sabse_lamba": {"id": end, "title": by_id.get(end, {}).get("title", "")} if end else {},
            "jo_nahi_mile": missing,
            "note": ("Yeh sabse lamba raasta hai - ise chhota kiye bina release jaldi nahi hogi."
                     if path else "Koi dependency nahi mili.")}


# ---------------------------------------------------------------- 2. who is over-committed
def capacity(rows: list[dict[str, Any]], days_available: float = 10.0,
             per_owner: dict[str, float] | None = None) -> dict[str, Any]:
    """rows: owner, days (estimate), status. Open work only - done work does not use future capacity."""
    items = _rows(rows, "capacity")
    have = {k.lower(): _num(v) for k, v in (per_owner or {}).items()}
    load: dict[str, float] = {}
    count: dict[str, int] = {}
    for r in items:
        if _s(r.get("status")).lower() in ("done", "closed", "shipped", "resolved", "dropped"):
            continue
        o = _s(r.get("owner")) or "(kisi ka nahi)"
        load[o] = load.get(o, 0.0) + max(0.0, _num(r.get("days") or r.get("estimate"), 0))
        count[o] = count.get(o, 0) + 1
    out = []
    for o, d in sorted(load.items(), key=lambda kv: -kv[1]):
        cap = have.get(o.lower(), _num(days_available, 10.0))
        out.append({"owner": o, "kaam": count[o], "lagega": round(d, 2), "hai": round(cap, 2),
                    "zyada": round(d - cap, 2) if d > cap else 0.0,
                    "bhara": round((d / cap * 100) if cap else 0, 1)})
    over = [x for x in out if x["zyada"] > 0]
    return {"log": out, "zyada_bhare": over, "bina_maalik": round(load.get("(kisi ka nahi)", 0.0), 2),
            "note": (f"{len(over)} logon ke paas waqt se zyada kaam hai." if over
                     else "Kisi ke paas waqt se zyada kaam nahi.")}


# ---------------------------------------------------------------- 3. are we getting faster
def delivery_metrics(rows: list[dict[str, Any]], committed: int = 0) -> dict[str, Any]:
    """rows: created, started, done (YYYY-MM-DD), escaped (bool). Median, not mean: one 90-day ticket should not
    decide the number."""
    items = _rows(rows, "metrics")
    lead, cycle, done_n, escaped = [], [], 0, 0
    for r in items:
        c, s, d = _day(r.get("created")), _day(r.get("started")), _day(r.get("done"))
        if d:
            done_n += 1
            if c:
                lead.append((d - c).days)
            if s:
                cycle.append((d - s).days)
        if r.get("escaped") in (True, "true", "True", 1, "1", "yes"):
            escaped += 1

    def med(v: list[int]) -> float | None:
        if not v:
            return None
        v = sorted(v)
        n = len(v)
        return float(v[n // 2]) if n % 2 else round((v[n // 2 - 1] + v[n // 2]) / 2, 1)

    say_do = round(done_n / committed * 100, 1) if committed else None
    return {"poore_hue": done_n, "lead_time_din": med(lead), "cycle_time_din": med(cycle),
            "baad_mein_mile_bugs": escaped,
            "vaada_vs_hua": say_do,
            "note": ("Beech ka number (median) diya hai - ek lamba ticket poori tasveer na badle."
                     if lead or cycle else "Tareekhen nahi theen, isliye samay nahi nikala ja saka.")}


# ---------------------------------------------------------------- 4. what is rotting
def raid_sweep(rows: list[dict[str, Any]], today: str = "", stale_days: int = 14) -> dict[str, Any]:
    """rows: id, title, kind, owner, due, severity, status, updated."""
    items = _rows(rows, "RAID")
    t = _day(today) or date.today()
    overdue, stale, unowned, high = [], [], [], []
    for r in items:
        if _s(r.get("status")).lower() in ("done", "closed", "resolved", "dropped"):
            continue
        row = {"id": _s(r.get("id")), "title": _s(r.get("title"))[:200], "owner": _s(r.get("owner")),
               "due": _s(r.get("due"))[:10], "severity": _s(r.get("severity")).lower()}
        d = _day(r.get("due"))
        if d and d < t:
            overdue.append({**row, "kitne_din": (t - d).days})
        u = _day(r.get("updated"))
        if u and (t - u).days >= stale_days:
            stale.append({**row, "chup": (t - u).days})
        if not row["owner"]:
            unowned.append(row)
        if row["severity"] in ("high", "critical", "bada"):
            high.append(row)
    return {"tareekh_nikli": sorted(overdue, key=lambda x: -x["kitne_din"]),
            "koi_khabar_nahi": sorted(stale, key=lambda x: -x["chup"]),
            "bina_maalik": unowned, "bade": high,
            "note": ("Sabse pehle tareekh nikli hui cheezein." if overdue else
                     "Koi tareekh nikli hui cheez nahi.")}


# ---------------------------------------------------------------- 5. can we ship
def release_readiness(gates: list[dict[str, Any]]) -> dict[str, Any]:
    """gates: name, ok (bool), note, blocking (default True). Go only when every BLOCKING gate passes - and the
    ones that fail are named, because 'not ready' without a reason helps nobody."""
    items = _rows(gates, "readiness")
    passed, failed, warn = [], [], []
    for g in items:
        name = _s(g.get("name") or g.get("gate"))[:120]
        ok = g.get("ok") in (True, "true", "True", 1, "1", "yes", "haan")
        blocking = g.get("blocking", True) not in (False, "false", "False", 0, "0", "no")
        row = {"gate": name, "note": _s(g.get("note"))[:300]}
        (passed if ok else (failed if blocking else warn)).append(row)
    go = not failed
    return {"ja_sakte_hain": go, "paas": passed, "ruke_hue": failed, "chetavni": warn,
            "note": ("Sab zaroori gate paas - ja sakte hain." if go else
                     f"{len(failed)} zaroori gate ruke hue hain: " + ", ".join(x["gate"] for x in failed))}


# ---------------------------------------------------------------- 6. who owes me an update
def chase(rows: list[dict[str, Any]], today: str = "", quiet_days: int = 3) -> dict[str, Any]:
    """rows: id, title, owner, updated, status. Who has said nothing for `quiet_days` on open work."""
    items = _rows(rows, "chase")
    t = _day(today) or date.today()
    owed: dict[str, list[dict[str, Any]]] = {}
    never = []
    for r in items:
        if _s(r.get("status")).lower() in ("done", "closed", "resolved", "dropped"):
            continue
        o = _s(r.get("owner"))
        u = _day(r.get("updated"))
        row = {"id": _s(r.get("id")), "title": _s(r.get("title"))[:200],
               "chup": (t - u).days if u else None}
        if not o:
            never.append(row)
            continue
        if u is None or (t - u).days >= quiet_days:
            owed.setdefault(o, []).append(row)
    return {"kisse_poochna_hai": [{"owner": o, "cheezein": v} for o, v in
                                  sorted(owed.items(), key=lambda kv: -len(kv[1]))],
            "bina_maalik": never,
            "note": ("Hoola khud se koi status nahi likhta - jo unhone kaha wahi likha jaata hai."
                     if owed or never else "Sabne haal hi mein update diya hai.")}
