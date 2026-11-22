"""F12 proof (FINANCE_GLOBAL_PLAN phase F12): the three things that must be true before the finance employees are called proven.

  1 every employee's card runs and passes on HER server (F1-F12), each with its time;
  2 at least one real user per size (personal, solo, business, firm, small regulated firm = institution) has used it for a month:
    a workspace of that size whose own tool use spans at least 28 days; card and test tenants ("card...") are never counted;
  3 the country packs are clean: no schema error and no rule past its review date. How many rules are only "verify" (from memory)
    is reported too - a pack can be clean and still have nothing checked by a person, and the report says so.

The report says PROVEN only when all three hold. Anything short of that is named.

    python -m app.fin.proof            the full report (runs every card; a few minutes)
    python -m app.fin.proof --quick    smaller cards, the same checks
"""
from __future__ import annotations

import importlib
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

SIZES = ("personal", "solo", "business", "firm", "institution")
CARDS = [("F1", "card_f1", {}, {}), ("F2", "card_f2", {}, {"n": 10}), ("F3", "card_f3", {}, {"n": 6}), ("F4", "card_f4", {}, {"n": 2}),
         ("F5", "card_f5", {}, {"n": 4}), ("F6", "card_f6", {}, {"n": 3}), ("F7", "card_f7", {}, {"n_clients": 12}),
         ("F8", "card_f8", {}, {"seeds": 1}), ("F9", "card_f9", {}, {"customers": 3000}), ("F10", "card_f10", {}, {"seeds": 1}),
         ("F11", "card_f11", {}, {"seeds": 1}), ("F12", "card_f12", {}, {"seeds": 1})]
MONTH_DAYS = 28


def cards(quick: bool = False, only: list[str] | None = None) -> list[dict[str, Any]]:
    out = []
    for phase, mod, full, small in CARDS:
        if only and phase not in only:
            continue
        t0 = time.time()
        try:
            r = importlib.import_module(f"app.fin.{mod}").run(**(small if quick else full))
            ok = bool(r["ok"]) if "ok" in r else (r.get("failed") == 0)      # F1 reports its failures, the later cards an ok
            total = r.get("checks", r.get("cases"))
            note = f"{r.get('passed', '')}/{total}" if total is not None else ""
        except Exception as e:      # a crash is a failed card, the report goes on
            ok, note = False, f"{type(e).__name__}: {e}"
        out.append({"phase": phase, "card": mod, "ok": ok, "seconds": round(time.time() - t0, 1), "note": note})
    return out


def users(now: datetime | None = None) -> dict[str, Any]:
    from .. import db
    from .models import FinEvent, FinWorkspace, ensure
    ensure()
    now = now or datetime.now(timezone.utc)
    span: dict[str, list[datetime]] = defaultdict(list)
    with db.session() as s:
        ws = {w.id: (w.tenant_id, w.size) for w in s.query(FinWorkspace).all() if not str(w.tenant_id).startswith("card")}
        tenant_size = defaultdict(set)
        for wid, (t, size) in ws.items():
            tenant_size[t].add(size)
        for e in s.query(FinEvent).filter(FinEvent.kind == "tool", FinEvent.at >= now - timedelta(days=120)).all():
            if str(e.tenant_id).startswith("card"):
                continue
            at = e.at if e.at.tzinfo else e.at.replace(tzinfo=timezone.utc)
            sizes = {ws[e.workspace_id][1]} if e.workspace_id in ws else tenant_size.get(e.tenant_id, set())
            for size in sizes:
                span[f"{e.tenant_id}|{size}"].append(at)
    per = {}
    for size in SIZES:
        best = 0
        n = 0
        for k, ats in span.items():
            if k.endswith("|" + size):
                n += 1
                best = max(best, (max(ats) - min(ats)).days)
        per[size] = {"users": n, "longest_use_days": best, "a_month": best >= MONTH_DAYS}
    return {"sizes": per, "missing": [s for s in SIZES if not per[s]["a_month"]]}


def packs() -> dict[str, Any]:
    from . import pack as P
    r = P.check_all()
    rows = r["packs"]
    tot = {k: sum(p.get(k, 0) for p in rows) for k in ("total", "checked", "source_read", "verify", "expired")}
    return {"countries": len(rows), "errors": r["errors"], **tot, "clean": not r["errors"] and tot["expired"] == 0,
            "says": (f"{tot['verify']} of {tot['total']} rules are from memory (verify) and are never used in a calculation; "
                     f"{tot['checked']} are checked by a person.")}


def report(quick: bool = False) -> dict[str, Any]:
    c = cards(quick)
    u = users()
    p = packs()
    short = []
    if not all(x["ok"] for x in c):
        short.append("cards failing: " + ", ".join(x["phase"] for x in c if not x["ok"]))
    if u["missing"]:
        short.append("no real user for a month yet: " + ", ".join(u["missing"]))
    if not p["clean"]:
        short.append("packs not clean: " + (f"{len(p['errors'])} errors" if p["errors"] else f"{p['expired']} rules past review"))
    return {"proven": not short, "short_of": short, "cards": c, "users": u, "packs": p,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


if __name__ == "__main__":
    r = report("--quick" in sys.argv)
    for x in r["cards"]:
        print(f"{'PASS' if x['ok'] else 'FAIL'} {x['phase']:>4} {x['card']:<10} {x['seconds']:>6}s {x['note']}")
    for s, v in r["users"]["sizes"].items():
        print(f"users {s:<12} {v['users']} using it, longest {v['longest_use_days']} days{'  (a month)' if v['a_month'] else ''}")
    pk = r["packs"]
    print(f"packs {pk['countries']} countries: {pk['total']} rules, checked {pk['checked']}, source read {pk['source_read']}, "
          f"verify {pk['verify']}, past review {pk['expired']}, errors {len(pk['errors'])}")
    print("PROVEN" if r["proven"] else "NOT PROVEN YET: " + "; ".join(r["short_of"]))
    if "--json" in sys.argv:
        print(json.dumps(r, default=str))
    sys.exit(0 if all(x["ok"] for x in r["cards"]) else 1)
