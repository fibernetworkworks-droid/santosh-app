"""The F9 card: institution mode (FINANCE_GLOBAL_PLAN phase F9).

SANDBOX WITH 1 M TRANSACTIONS. 20,000 customers with a year of ordinary activity, and 40 customers for each of six patterns planted
in it (cash just under the threshold, money passed straight through, a high-risk country, a sudden month, a dormant account waking up,
many senders into one account). The triage must alert every planted customer for its pattern, and alert few ordinary customers (under
1%); the time is measured.

ALERT TRIAGE AND SAR DRAFTS. For one planted alert of each pattern a SAR draft is made: every amount and date in it comes from the
transactions behind the alert, all parts are there, no accusing words; a draft with a made-up amount or an accusing word fails its
checks. The human review: the draft goes into maker-checker and a named MLRO scores it 1-5 on five points - the card checks that only an
MLRO / compliance person can score and that the score is kept, but it cannot BE that person: the scores a person gives are reported,
and until a person has scored, the card says so.

MAKER-CHECKER CANNOT BE BYPASSED. Every road around it is tried: the maker checks their own draft; someone without the checker role
checks; a stale hash; a reviser checks; the same checker twice on a draft over the limit; a draft of another workspace; a state word sent
in the arguments; a set_state action; an approved draft changed; a reject with no reason; the text changed in the database behind the
check. Each must fail, and the honest road (maker, then one checker - or two over the limit) must work.

LOAD. 1 M transactions triaged; 300 drafts made and checked; times reported.

    python -m app.fin.card_f9 [customers]     scratch database; exit 1 if anything fails
"""
from __future__ import annotations

import random
import sys
import time
from datetime import date, timedelta
from typing import Any

from . import profile as PR
from .desks import institution as IN

RULES = {"cash_threshold": 10000, "structuring_band_pct": 10, "structuring_count": 3, "structuring_days": 7, "pass_through_pct": 90,
         "pass_through_days": 2, "pass_through_min": 5000, "high_risk_countries": ["XA", "XB"], "high_risk_min": 1000, "spike_multiple": 8,
         "spike_min": 5000, "dormant_days": 180, "dormant_min": 2000, "fan_in_senders": 10, "fan_in_days": 7}
PATTERNS = ("structuring", "pass_through", "high_risk_country", "spike", "dormant_reactivated", "fan_in")
START = date(2026, 1, 1)
DAYS = [(START + timedelta(days=k)).isoformat() for k in range(365)]


def sandbox(customers: int, per: int, seed: int) -> tuple[list[tuple], dict[str, str]]:
    rnd = random.Random(seed)
    rows: list[tuple] = []
    n = 0
    pool = ["Acme", "Shop", "Rent Co", "Power", "Grocer"]
    for c in range(customers):
        cust = f"C{c:06d}"
        for _ in range(per):
            n += 1
            d = DAYS[rnd.randrange(365)]
            if rnd.random() < 0.5:
                rows.append((f"t{n}", cust, d, round(rnd.uniform(20, 1500), 2), "out", "card", "GB", rnd.choice(pool)))
            else:
                ch = "cash" if rnd.random() < 0.2 else "transfer"
                rows.append((f"t{n}", cust, d, round(rnd.uniform(20, 2500), 2), "in", ch, "GB", rnd.choice(pool)))
    planted: dict[str, str] = {}
    k = 0
    for pat in PATTERNS:
        for _ in range(40):
            k += 1
            cust = f"P{k:04d}"
            planted[cust] = pat
            base = rnd.randrange(30, 300)

            def add(day: int, amt: float, dirn: str, ch: str, cc: str = "GB", cp: str = "Acme"):
                nonlocal n
                n += 1
                rows.append((f"t{n}", cust, DAYS[day], round(amt, 2), dirn, ch, cc, cp))
            for _ in range(6):
                add(rnd.randrange(0, 20), rnd.uniform(20, 200), "out", "card")
            if pat == "structuring":
                for j in range(4):
                    add(base + j, rnd.uniform(9100, 9950), "in", "cash")
            elif pat == "pass_through":
                add(base, 20000, "in", "wire", "GB", "Big Ltd")
                add(base + 1, 12000, "out", "wire", "GB", "Far Ltd")
                add(base + 1, 7000, "out", "wire", "GB", "Near Ltd")
            elif pat == "high_risk_country":
                add(base, 3000, "out", "wire", rnd.choice(["XA", "XB"]), "Away Co")
            elif pat == "spike":
                for m in range(6):
                    for _ in range(3):
                        add(m * 30 + rnd.randrange(1, 28), 150, "out", "card")
                for _ in range(4):
                    add(200 + rnd.randrange(0, 25), 6000, "in", "transfer", "GB", "Windfall")
            elif pat == "dormant_reactivated":
                add(270, 5000, "in", "transfer", "GB", "Wake Co")
            elif pat == "fan_in":
                for j in range(12):
                    add(base + j % 5, 300, "in", "transfer", "GB", f"Sender {j}")
    # near misses: look like a pattern but are outside its window - they must NOT alert for it
    for pat in ("structuring", "pass_through", "fan_in"):
        for _ in range(20):
            k += 1
            cust = f"N{k:04d}"
            planted[cust] = "not:" + pat
            base = rnd.randrange(20, 120)

            def add(day: int, amt: float, dirn: str, ch: str, cp: str = "Acme"):
                nonlocal n
                n += 1
                rows.append((f"t{n}", cust, DAYS[day], round(amt, 2), dirn, ch, "GB", cp))
            if pat == "structuring":
                for j in range(4):
                    add(base + 30 * j, rnd.uniform(9100, 9950), "in", "cash")
            elif pat == "pass_through":
                add(base, 20000, "in", "wire", "Big Ltd")
                add(base + 5, 19000, "out", "wire", "Far Ltd")
            else:
                for j in range(12):
                    add(base + 5 * j, 300, "in", "transfer", f"Sender {j}")
    rnd.shuffle(rows)
    return rows, planted


def triage_part(customers: int, per: int, seed: int) -> dict[str, Any]:
    t0 = time.perf_counter()
    rows, planted = sandbox(customers, per, seed)
    built = time.perf_counter() - t0
    t1 = time.perf_counter()
    r = IN.aml_triage({"transactions": rows, "rules": RULES})
    secs = time.perf_counter() - t1
    got: dict[str, set[str]] = {}
    for x in r["alerts"]:
        got.setdefault(x["customer"], set()).add(x["rule"])
    bad = []
    missed = [c for c, pat in planted.items() if not pat.startswith("not:") and pat not in got.get(c, set())]
    wrongly = [c for c, pat in planted.items() if pat.startswith("not:") and pat[4:] in got.get(c, set())]
    if wrongly:
        bad.append(f"{len(wrongly)} near misses alerted anyway, e.g. {wrongly[:3]} ({planted[wrongly[0]]})")
    if missed:
        bad.append(f"{len(missed)} planted customers not alerted for their pattern, e.g. {missed[:3]} ({planted[missed[0]]})")
    ordinary = [c for c in got if c.startswith("C")]
    rate = len(ordinary) * 100 / customers
    if rate >= 1:
        bad.append(f"{rate:.2f}% of ordinary customers alerted (needs under 1%)")
    return {"part": "triage", "ok": not bad, "problems": bad, "transactions": len(rows), "alerts": len(r["alerts"]),
            "planted_found": f"{sum(not p.startswith('not:') for p in planted.values()) - len(missed)}/"
                             f"{sum(not p.startswith('not:') for p in planted.values())}",
            "near_misses_held": f"{sum(p.startswith('not:') for p in planted.values()) - len(wrongly)}/{sum(p.startswith('not:') for p in planted.values())}", "ordinary_alerted_pct": round(rate, 3),
            "seconds": round(secs, 1), "build_seconds": round(built, 1), "_rows": rows, "_alerts": r["alerts"], "_planted": planted}


def _ws(t: str, size: str = "institution") -> str:
    pv = PR.preview({"size": size, "countries": ["GB"], "wants": [], "people": []})
    ans = {**pv["answers"], "currency": "GBP"}
    return PR.apply(t, ans, PR.preview(ans)["hash"])["id"]


def sar_part(tr: dict[str, Any], t: str, ws: str) -> dict[str, Any]:
    bad = []
    by_c: dict[str, list[dict[str, Any]]] = {}
    want = {a["customer"] for a in tr["_alerts"] if a["customer"] in tr["_planted"]}
    for row in tr["_rows"]:
        if row[1] in want:
            by_c.setdefault(row[1], []).append({"id": row[0], "customer": row[1], "date": row[2], "amount": row[3], "direction": row[4],
                                                "channel": row[5], "country": row[6], "counterparty": row[7]})
    done = set()
    drafts = []
    for a in tr["_alerts"]:
        pat = tr["_planted"].get(a["customer"])
        if pat != a["rule"] or pat in done:
            continue
        done.add(pat)
        s = IN.run(t, "sar_draft", {"workspace": ws, "person": "mia-maker", "alert": a, "transactions": by_c[a["customer"]],
                                    "customer": {"name": "Test Person", "occupation": "teacher", "expected_activity": "salary and bills"}})
        if not s["checks"]["ok"]:
            bad.append(f"{pat}: the SAR draft fails its own checks: {s['checks']['problems']}")
        if s["draft"]["state"] != "waiting":
            bad.append(f"{pat}: the SAR draft did not wait for a checker")
        drafts.append(s["draft"]["id"])
        for evil, what in ((s["body"].replace("## Why it is unusual", "This criminal laundered money.\n\n## Why it is unusual"), "an accusing word"),
                           (s["body"].replace("## When", "- 2026-02-30: 99,999.99 in\n\n## When"), "a made-up amount")):
            if IN.sar_checks(evil, by_c[a["customer"]])["ok"]:
                bad.append(f"{pat}: a SAR draft with {what} passed its checks")
    if done != set(PATTERNS):
        bad.append(f"SAR drafts made only for {sorted(done)}")
    try:
        IN.run(t, "sar_score", {"workspace": ws, "person": "mia-maker", "draft": drafts[0], "scores": {k: 5 for k in IN.SCORE_ON}})
        bad.append("someone who is not MLRO / compliance scored a SAR")
    except IN.InstError:
        pass
    return {"part": "sar drafts", "ok": not bad, "problems": bad, "drafts": len(drafts), "_drafts": drafts,
            "human_scores": "pending: the drafts wait in maker-checker for a named MLRO to score (sar_score) - the card cannot be that person"}


def mc_part(t: str, ws: str) -> dict[str, Any]:
    from .. import db
    from .models import FinDraft
    bad = []
    go = lambda action, **a: IN.run(t, action, {"workspace": ws, **a})   # noqa: E731

    def refused(what, fn):
        try:
            fn()
            bad.append(f"bypass worked: {what}")
        except (IN.InstError, PermissionError):
            pass
    d = go("submit", person="mia-maker", kind="policy", body="Policy v1")["draft"]
    refused("the maker checks their own draft", lambda: go("check", person="mia-maker", draft=d["id"], verdict="approve", hash=d["hash"]))
    refused("a person without the checker role", lambda: go("check", person="vic-viewer", draft=d["id"], verdict="approve", hash=d["hash"]))
    refused("a stale hash", lambda: go("check", person="cal-checker", draft=d["id"], verdict="approve", hash="0" * 64))
    refused("no hash at all", lambda: go("check", person="cal-checker", draft=d["id"], verdict="approve"))
    refused("a reject with no reason", lambda: go("check", person="cal-checker", draft=d["id"], verdict="reject", hash=d["hash"]))
    refused("a set_state action", lambda: go("set_state", person="adam-admin", draft=d["id"], state="approved"))
    refused("an approve_draft action", lambda: go("approve_draft", person="adam-admin", draft=d["id"]))
    s = go("submit", person="mia-maker", kind="policy", body="Sneaky", state="approved", approved_by="cal-checker")["draft"]
    if s["state"] != "waiting":
        bad.append("a state word in the arguments was obeyed")
    sd = go("submit", person="sol-both", kind="memo", body="Sol's own memo")["draft"]
    refused("a person holding both roles checks their own draft",
            lambda: go("check", person="sol-both", draft=sd["id"], verdict="approve", hash=sd["hash"]))
    od = go("submit", person="mia-maker", kind="memo", body="Mia's memo")["draft"]
    ov = go("revise", person="sol-both", draft=od["id"], body="Mia's memo, changed by Sol")["draft"]
    refused("a person holding both roles checks a draft they changed",
            lambda: go("check", person="sol-both", draft=od["id"], verdict="approve", hash=ov["hash"]))
    r = go("revise", person="max-maker", draft=d["id"], body="Policy v2")["draft"]
    refused("a reviser checks the draft they changed", lambda: go("check", person="max-maker", draft=d["id"], verdict="approve", hash=r["hash"]))
    ok = go("check", person="cal-checker", draft=d["id"], verdict="approve", hash=r["hash"])["draft"]
    if ok["state"] != "approved":
        bad.append("the honest road (maker, then a checker) did not approve")
    refused("an approved draft is changed", lambda: go("revise", person="mia-maker", draft=d["id"], body="Policy v3"))
    big = go("submit", person="mia-maker", kind="limit", body="Raise the limit", amount=5_000_000)["draft"]
    one = go("check", person="cal-checker", draft=big["id"], verdict="approve", hash=big["hash"])["draft"]
    if one["state"] != "waiting":
        bad.append("one checker approved a draft over the single-check limit")
    refused("the same checker twice over the limit", lambda: go("check", person="cal-checker", draft=big["id"], verdict="approve", hash=big["hash"]))
    two = go("check", person="cat-checker", draft=big["id"], verdict="approve", hash=big["hash"])["draft"]
    if two["state"] != "approved":
        bad.append("two checkers did not approve a draft over the limit")
    other = _ws(t)
    IN.run(t, "person_add", {"workspace": other, "name": "Cal Checker", "roles": ["admin", "checker"]})
    w = go("submit", person="mia-maker", kind="memo", body="Memo")["draft"]
    refused("a draft checked from another workspace",
            lambda: IN.run(t, "check", {"workspace": other, "person": "cal-checker", "draft": w["id"], "verdict": "approve", "hash": w["hash"]}))
    from . import makerchecker as MC
    go("check", person="cal-checker", draft=w["id"], verdict="approve", hash=w["hash"])
    with db.session() as ss:                      # the text changed in the database behind the check
        row = ss.get(FinDraft, w["id"])
        row.body = "Memo - quietly changed"
        ss.commit()
    if MC.is_approved(t, ws, w["id"]):
        bad.append("a draft whose text changed behind the check still counts as approved")
    return {"part": "maker-checker", "ok": not bad, "problems": bad}


def load_part(t: str, ws: str, n: int = 300) -> dict[str, Any]:
    t0 = time.perf_counter()
    for k in range(n):
        d = IN.run(t, "submit", {"workspace": ws, "person": "mia-maker", "kind": "memo", "body": f"Load memo {k}"})["draft"]
        IN.run(t, "check", {"workspace": ws, "person": "cal-checker", "draft": d["id"], "verdict": "approve", "hash": d["hash"]})
    secs = time.perf_counter() - t0
    return {"part": "load (maker-checker)", "ok": True, "problems": [], "drafts": n, "seconds": round(secs, 1),
            "per_draft_ms": round(secs * 1000 / n, 1)}


def run(customers: int = 20000, per: int = 50, seed: int = 11) -> dict[str, Any]:
    rows = []
    t = f"card9-{seed}"
    ws = _ws(t)
    for name, roles in (("Adam Admin", ["admin"]), ("Mia Maker", ["maker"]), ("Max Maker", ["maker"]), ("Cal Checker", ["checker"]),
                        ("Cat Checker", ["checker"]), ("Mo MLRO", ["mlro", "checker"]), ("Vic Viewer", ["viewer"]),
                        ("Sol Both", ["maker", "checker"])):
        IN.run(t, "person_add", {"workspace": ws, "person": "adam-admin", "name": name, "roles": roles})
    IN.run(t, "limits", {"workspace": ws, "person": "adam-admin", "single_check_limit": 1_000_000})
    tr = None
    for fn in (lambda: triage_part(customers, per, seed), None, lambda: mc_part(t, ws), lambda: load_part(t, ws)):
        try:
            if fn is None:
                rows.append(sar_part(tr, t, ws) if tr else {"part": "sar drafts", "ok": False, "problems": ["no triage"]})
                continue
            x = fn()
            if x["part"] == "triage":
                tr = x
            rows.append(x)
        except Exception as e:     # a crash is a failed part, not a stopped card
            rows.append({"part": "?", "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    return {"ok": all(r["ok"] for r in rows), "rows": clean}


def _scratch_db() -> None:
    import os
    import tempfile
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="card9_"), "card.db")
    os.environ["HOOLA_FIN_REVIEW_DIR"] = tempfile.mkdtemp(prefix="card9_review_")
    from ..config import get_settings
    get_settings.cache_clear()
    from .. import db
    db.init_db()


if __name__ == "__main__":
    _scratch_db()
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 20000)
    for x in r["rows"]:
        print(("PASS " if x["ok"] else "FAIL ") + x["part"], {k: v for k, v in x.items() if k not in ("part", "ok", "problems")})
        for p in x["problems"]:
            print("   ", p)
    print("F9 card:", "PASS" if r["ok"] else "FAIL")
    sys.exit(0 if r["ok"] else 1)
