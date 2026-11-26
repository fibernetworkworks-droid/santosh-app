"""PAYMENTS DESK - the Payments employee's own section, like Payroll, Tax, Cash & Treasury, Credit & Lending and Firm Practice (owner:
"NOW LETS WORK ON NEXT EMPLOYEE PAYMENTS DESK").

- The Payments chat = a Conversation with kind 'payments', kept out of every Hoola chat list (callconv.not_call); facts she tells it still
  reach her one memory. A turn in it (or a voice call started from it) gets the desk's state as a block and the payments tool
  (`payments_desk`, family paydesk) in view.
- The desk runs the F8 engine (fin/desks/payments.py) on the business she picked (the same businesses as Books & Accounts). Her team works
  here too: owner / accountant / approver change things, auditor and viewer read.
- The engine is stateless; the desk keeps her data in the business's settings under `payments_desk`:
    disputes    a case file per chargeback: network, reason code, amount, when it came, her processor's window, the evidence she has,
                her earlier transactions with the customer (Visa 10.4), the status SHE records (open / responded / won / lost) with her
                reference. Hoola never submits a response.
    gateways    each gateway with the rate in her contract (percent + fixed) and its dispute window.
    settlements the payout lines she uploads from each gateway (CSV), orders she uploads (CSV) - matched against the deposits in her
                imported bank statements.
    failed      failed recurring payments (CSV / form) -> the retry plan and the messages; Hoola never charges.
    market      marketplace sales by seller (CSV) + her commission -> what each seller is owed; Hoola never pays.
    thresholds  her dispute-rate limits per network.
- Payment-firm tools on the desk (stateless): KYB beneficial owners, ISO 20022 message check, safeguarding by day.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.paychat")

KIND = "payments"
KEY = "payments_desk"          # the Hub employee
TOOL = "payments_desk"         # its tool
FAMILIES = ["paydesk"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FOOT = ("Hoola works out the payments. It never submits a dispute response, charges a card or pays anyone - you or your processor do. "
        "Reason codes are from Hoola's table until your processor's guide is checked.")
WRITE = {"owner", "accountant", "approver"}
ROLE_SAY = {"owner": "Owner", "accountant": "Accountant", "approver": "Approver", "auditor": "Auditor", "viewer": "Viewer"}
STATUSES = ("open", "responded", "won", "lost", "accepted")
MAX_ROWS = 20000


class PayDeskError(ValueError):
    pass


def is_payments(conv: str) -> bool:
    if not conv:
        return False
    if conv in _OF:
        return _OF[conv]
    hit = False
    try:
        with session() as s:
            c = s.get(Conversation, conv)
            if c is not None:
                if (c.kind or "") == KIND:
                    hit = True
                elif (c.kind or "") == "call" and c.origin_conv:
                    o = s.get(Conversation, c.origin_conv)
                    hit = bool(o is not None and (o.kind or "") == KIND)
    except Exception:   # noqa: BLE001
        log.exception("payments chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _hire():
    from .employee import hire
    return hire


def businesses(tenant: str) -> list[dict[str, Any]]:
    from .bookschat import businesses as B
    return B(tenant)


def workspace(tenant: str, want: str = "") -> dict[str, Any] | None:
    bs = businesses(tenant)
    if not want:
        try:
            want = str(_hire().settings(tenant, KEY).get("workspace") or "")
        except Exception:   # noqa: BLE001
            want = ""
    for b in bs:
        if b["id"] == want:
            return b
    return bs[0] if bs else None


def pick(tenant: str, ws: str) -> dict[str, Any]:
    if not any(b["id"] == ws for b in businesses(tenant)):
        raise PayDeskError("No such business.")
    try:
        _hire().save_settings(tenant, KEY, workspace=ws)
    except Exception:   # noqa: BLE001
        pass
    forget(tenant)
    return {"workspace": ws}


# ---------------------------------------------------------------- desk state
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _wsrow(owner: str, ws: str) -> dict[str, Any]:
    from .fin import profile as PR
    return PR.get(owner, ws)


def _state(owner: str, ws: str) -> dict[str, Any]:
    st = dict((_wsrow(owner, ws).get("settings") or {}).get("payments_desk") or {})
    for k, v in (("disputes", []), ("gateways", {}), ("settlements", []), ("orders", []), ("failed", []), ("market", []),
                 ("commission_pct", None), ("thresholds", {}), ("retry_days", [1, 3, 7]), ("window_days", 5), ("files", [])):
        st.setdefault(k, v)
    return st


def _put(owner: str, ws: str, st: dict[str, Any]) -> None:
    from . import db
    from .fin.models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != owner:
            raise PayDeskError("No such business.")
        cur = json.loads(row.settings or "{}")
        cur["payments_desk"] = st
        row.settings = json.dumps(cur)
        s.commit()


def _num(v: Any, what: str, lo: float | None = None) -> float:
    try:
        x = float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        raise PayDeskError(f"{what}: a number.")
    if lo is not None and x < lo:
        raise PayDeskError(f"{what}: not below {lo:g}.")
    return x


def _day(v: Any, what: str) -> str:
    try:
        return date.fromisoformat(str(v).strip()[:10]).isoformat()
    except ValueError:
        raise PayDeskError(f"{what}: a date as YYYY-MM-DD.")


def _text(v: Any, n: int = 80) -> str:
    return str(v or "").strip()[:n]


def _next_n(rows: list[dict[str, Any]]) -> int:
    return 1 + max([int(x.get("n") or 0) for x in rows] or [0])


def _find(rows: list[dict[str, Any]], n: Any, what: str) -> dict[str, Any]:
    for x in rows:
        if int(x.get("n") or 0) == int(_num(n, "n")):
            return x
    raise PayDeskError(f"No such {what}.")


def _engine(owner: str, me: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin import core
    from .fin.desks import payments as P
    try:
        return core.run_tool(owner, me, TOOL, action, dict(a), lambda: P.run(owner, action, a, me))
    except P.PaymentsError as e:
        raise PayDeskError(str(e))


# ---------------------------------------------------------------- CSV files she uploads
_ALIAS = {
    "payout_id": ("payout_id", "payout", "payout id", "settlement id", "settlement_id", "transfer id", "batch"),
    "payout_date": ("payout_date", "payout date", "settlement date", "settled", "date", "arrival date"),
    "order_id": ("order_id", "order", "order id", "reference", "ref", "invoice", "merchant reference"),
    "type": ("type", "kind", "transaction type", "category"),
    "amount": ("amount", "gross", "value", "net", "total"),
    "id": ("id", "order_id", "order", "order id", "reference", "invoice"),
    "gateway": ("gateway", "processor", "provider", "psp"),
    "date": ("date", "created", "order date", "day"),
    "customer": ("customer", "customer name", "name", "email"),
    "plan": ("plan", "product", "subscription"),
    "reason": ("reason", "decline reason", "failure", "error"),
    "seller": ("seller", "vendor", "merchant", "shop"),
    "fee": ("fee", "fees", "commission fee", "processing fee"),
}
_TYPE = {"charge": "sale", "payment": "sale", "sale": "sale", "capture": "sale", "refund": "refund", "chargeback": "chargeback",
         "dispute": "chargeback", "fee": "fee", "fees": "fee", "adjustment": "adjustment", "adjust": "adjustment"}


def _read_csv(text: str, want: list[str], need: list[str]) -> list[dict[str, Any]]:
    rows = list(csv.reader(io.StringIO(str(text or "").lstrip("﻿"))))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise PayDeskError("The file needs a header line and at least one row.")
    head = [h.strip().lower() for h in rows[0]]
    col: dict[str, int] = {}
    for k in want:
        for al in _ALIAS.get(k, (k,)):
            if al in head and head.index(al) not in col.values():
                col[k] = head.index(al)
                break
    miss = [k for k in need if k not in col]
    if miss:
        raise PayDeskError(f"The file has no column for {', '.join(miss)} (its header: {', '.join(rows[0])[:200]}).")
    out = []
    for r in rows[1:MAX_ROWS + 1]:
        out.append({k: (r[i].strip() if i < len(r) else "") for k, i in col.items()})
    return out


def upload(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    """A CSV from a gateway (settlement lines), her shop (orders), her billing (failed payments) or her marketplace (seller sales)."""
    kind = str(a.get("kind") or "")
    text = str(a.get("text") or "")
    gw = _text(a.get("gateway"), 40).lower()
    st = _state(owner, ws)
    if kind == "settlements":
        if not gw:
            raise PayDeskError("gateway: which gateway the file is from.")
        rows = _read_csv(text, ["payout_id", "payout_date", "order_id", "type", "amount"], ["payout_id", "payout_date", "amount"])
        new = []
        for k, r in enumerate(rows):
            t = _TYPE.get(str(r.get("type") or "sale").strip().lower(), None)
            if t is None:
                raise PayDeskError(f"Row {k + 2}: type {r.get('type')!r} - sale | refund | chargeback | fee | adjustment.")
            new.append({"gateway": gw, "payout_id": r["payout_id"], "payout_date": _day(r["payout_date"], f"row {k + 2} date"),
                        "order_id": r.get("order_id") or "", "type": t, "amount": abs(_num(r["amount"], f"row {k + 2} amount"))
                        if t in ("sale", "refund", "chargeback", "fee") else _num(r["amount"], f"row {k + 2} amount")})
        keep = [x for x in st["settlements"] if not (x["gateway"] == gw and x["payout_id"] in {n["payout_id"] for n in new})]
        st["settlements"] = (keep + new)[-MAX_ROWS:]
        st["gateways"].setdefault(gw, {})
    elif kind == "orders":
        rows = _read_csv(text, ["id", "amount", "date", "gateway"], ["id", "amount"])
        new = [{"id": r["id"], "amount": _num(r["amount"], f"row {k + 2} amount"), "date": _day(r["date"], f"row {k + 2} date") if r.get("date") else "",
                "gateway": (r.get("gateway") or gw).lower()} for k, r in enumerate(rows)]
        ids = {n["id"] for n in new}
        st["orders"] = ([x for x in st["orders"] if x["id"] not in ids] + new)[-MAX_ROWS:]
    elif kind == "failed":
        rows = _read_csv(text, ["customer", "amount", "plan", "date", "reason"], ["customer", "amount", "date"])
        st["failed"] = (st["failed"] + [{"n": _next_n(st["failed"]) + k, "customer": r["customer"][:80],
                                         "amount": _num(r["amount"], f"row {k + 2} amount"), "plan": (r.get("plan") or "")[:60],
                                         "date": _day(r["date"], f"row {k + 2} date"), "reason": (r.get("reason") or "")[:80],
                                         "status": "chasing"} for k, r in enumerate(rows)])[-2000:]
    elif kind == "market":
        rows = _read_csv(text, ["seller", "amount", "type", "fee", "date"], ["seller", "amount"])
        new = []
        for k, r in enumerate(rows):
            t = str(r.get("type") or "sale").strip().lower()
            if t not in ("sale", "refund"):
                raise PayDeskError(f"Row {k + 2}: type - sale | refund.")
            new.append({"seller": r["seller"][:80], "amount": abs(_num(r["amount"], f"row {k + 2} amount")), "type": t,
                        "fee": abs(_num(r["fee"] or 0, f"row {k + 2} fee")) if r.get("fee") else 0.0, "date": r.get("date") or ""})
        st["market"] = new[-MAX_ROWS:] if a.get("replace") else (st["market"] + new)[-MAX_ROWS:]
    else:
        raise PayDeskError("kind: settlements | orders | failed | market.")
    st["files"] = (st["files"] + [{"kind": kind, "gateway": gw, "name": _text(a.get("name"), 80), "rows": len(rows), "by": me,
                                   "on": _now()}])[-50:]
    _put(owner, ws, st)
    return {"kind": kind, "rows": len(rows)}


def clear(owner: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    kind = str(a.get("kind") or "")
    if kind not in ("settlements", "orders", "failed", "market"):
        raise PayDeskError("kind: settlements | orders | failed | market.")
    st = _state(owner, ws)
    gw = _text(a.get("gateway"), 40).lower()
    if kind == "settlements" and gw:
        st["settlements"] = [x for x in st["settlements"] if x["gateway"] != gw]
    else:
        st[kind] = []
    _put(owner, ws, st)
    return {"cleared": kind}


# ---------------------------------------------------------------- disputes
def _evkeys() -> dict[str, str]:
    from .fin.desks import payments as P
    return dict(P.EVIDENCE)


def add_dispute(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    from .fin.desks import payments as P
    st = _state(owner, ws)
    net = str(a.get("network") or "").lower()
    if net not in P.REASONS:
        raise PayDeskError("network: visa | mastercard | amex.")
    code = str(a.get("reason_code") or "").strip()
    code = code.upper() if net == "amex" else code
    if code not in P.REASONS[net]:
        raise PayDeskError(f"reason_code: one of {', '.join(P.REASONS[net])} for {net}.")
    gw = _text(a.get("gateway"), 40).lower()
    win = a.get("window_days") or (st["gateways"].get(gw) or {}).get("window_days")
    row = {"n": _next_n(st["disputes"]), "network": net, "reason_code": code, "amount": _num(a.get("amount"), "amount", 0.01),
           "currency": _text(a.get("currency"), 3).upper() or str(_wsrow(owner, ws).get("currency") or "").upper(),
           "transaction_id": _text(a.get("transaction_id"), 60), "transaction_date": _day(a["transaction_date"], "transaction_date")
           if a.get("transaction_date") else "", "customer": _text(a.get("customer"), 80), "gateway": gw,
           "received": _day(a.get("received") or date.today().isoformat(), "received"),
           "window_days": int(_num(win, "window_days", 1)) if win not in (None, "") else None,
           "evidence": {}, "prior": [], "status": "open", "notes": "", "by": me, "on": _now()}
    st["disputes"].append(row)
    st["disputes"] = st["disputes"][-500:]
    _put(owner, ws, st)
    return {"dispute": dispute_view(owner, ws, row, me)}


def edit_dispute(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    row = _find(st["disputes"], a.get("n"), "dispute")
    if "evidence" in a:
        ev = a.get("evidence") or {}
        bad = [k for k in ev if k not in _evkeys()]
        if bad:
            raise PayDeskError("evidence: " + ", ".join(_evkeys()))
        row["evidence"] = {k: bool(v) for k, v in ev.items() if v}
    if "window_days" in a:
        row["window_days"] = int(_num(a["window_days"], "window_days", 1)) if a["window_days"] not in (None, "") else None
    if "notes" in a:
        row["notes"] = _text(a.get("notes"), 2000)
    if "prior" in a:
        pr = []
        for k, p in enumerate(a.get("prior") or []):
            pr.append({"date": _day(p.get("date"), f"prior {k + 1} date"), **{x: _text(p.get(x), 120) for x in ("ip", "device", "shipping", "account")},
                       "disputed": bool(p.get("disputed"))})
        row["prior"] = pr[:20]
    if "disputed" in a:
        row["disputed_tx"] = {x: _text((a.get("disputed") or {}).get(x), 120) for x in ("ip", "device", "shipping", "account")}
    row["changed_by"], row["changed_on"] = me, _now()
    _put(owner, ws, st)
    return {"dispute": dispute_view(owner, ws, row, me)}


def set_status(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    """She records what happened - Hoola submits nothing."""
    st = _state(owner, ws)
    row = _find(st["disputes"], a.get("n"), "dispute")
    s = str(a.get("status") or "")
    if s not in STATUSES:
        raise PayDeskError("status: " + " | ".join(STATUSES))
    if s == "responded" and not _text(a.get("reference"), 80):
        raise PayDeskError("reference: the reference your processor gave when you submitted the response.")
    row["status"] = s
    row["history"] = (row.get("history") or []) + [{"status": s, "reference": _text(a.get("reference"), 80), "by": me, "on": _now()}]
    if a.get("reference"):
        row["reference"] = _text(a.get("reference"), 80)
    _put(owner, ws, st)
    return {"dispute": dispute_view(owner, ws, row, me)}


def remove_dispute(owner: str, ws: str, n: Any) -> dict[str, Any]:
    st = _state(owner, ws)
    st["disputes"].remove(_find(st["disputes"], n, "dispute"))
    _put(owner, ws, st)
    return {"disputes": len(st["disputes"])}


def dispute_view(owner: str, ws: str, row: dict[str, Any], me: str) -> dict[str, Any]:
    a = {"network": row["network"], "reason_code": row["reason_code"], "amount": row["amount"], "currency": row.get("currency"),
         "transaction_id": row.get("transaction_id"), "transaction_date": row.get("transaction_date"), "evidence": row.get("evidence") or {},
         "received": row.get("received")}
    if row.get("window_days"):
        a["window_days"] = row["window_days"]
    if row["reason_code"] == "10.4" and row.get("prior"):
        a.update({"prior": row["prior"], "disputed": row.get("disputed_tx") or {}, "dispute_date": row.get("received")})
    try:
        r = _engine(owner, me, "dispute", a)
    except PayDeskError as e:
        r = {"error": str(e)}
    if r.get("letter"):
        r["letter"] = r["letter"].replace("[merchant name, contact]", str(_wsrow(owner, ws).get("name") or "[merchant name, contact]"))
    out = {**row, "read": r}
    dl = r.get("respond_by") if isinstance(r.get("respond_by"), str) and r["respond_by"][:4].isdigit() else None
    out["respond_by"] = dl
    out["days_left"] = (date.fromisoformat(dl) - date.today()).days if dl else None
    return out


# ---------------------------------------------------------------- reconciliation, fees, prevention
def _deposits(owner: str, ws: str, since: str) -> list[dict[str, Any]]:
    from .fin import spine as SP
    try:
        return [{"id": r["id"], "date": r["day"], "amount": float(r["amount"]), "narration": r.get("narration") or ""}
                for r in SP.txns(owner, ws, since=since, limit=5000) if float(r["amount"]) > 0]
    except Exception:   # noqa: BLE001
        return []


def reconcile(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["settlements"]:
        return {"empty": True, "says": "Upload a settlement file from each gateway (and your orders) to match them with your bank."}
    pays: dict[tuple[str, str], dict[str, Any]] = {}
    for x in st["settlements"]:
        p = pays.setdefault((x["gateway"], x["payout_id"]), {"gateway": x["gateway"], "payout_id": x["payout_id"],
                                                               "payout_date": x["payout_date"], "lines": []})
        p["lines"].append({"order_id": x["order_id"], "type": x["type"], "amount": x["amount"]})
    since = (date.fromisoformat(min(x["payout_date"] for x in st["settlements"])) - timedelta(days=2)).isoformat()
    deps = _deposits(owner, ws, since)
    a = {"settlements": list(pays.values()), "deposits": deps, "window_days": st["window_days"],
         "orders": [{"id": o["id"], "gateway": o["gateway"], "amount": o["amount"]} for o in st["orders"]]}
    r = _engine(owner, me, "reconcile", a)
    dmap = {d["id"]: d for d in deps}
    for p in r["payouts"]:
        d = dmap.get(p.get("deposit") or "")
        p["deposit_date"], p["deposit_narration"] = (d["date"], d["narration"][:80]) if d else (None, None)
        p["date"] = pays[(p["gateway"], p["payout"])]["payout_date"]
    r["deposits_read"] = len(deps)
    r["orders_read"] = len(st["orders"])
    r["unmatched_deposits"] = [{"id": i, "date": dmap[i]["date"], "amount": dmap[i]["amount"], "narration": dmap[i]["narration"][:80]}
                               for i in r["deposits_without_payout"]][:50]
    if not st["orders"]:
        r["orders"]["missing_at_gateway"] = []
        r["orders"]["gateway_sale_without_order"] = []
        r["no_orders"] = True
    return r


def fee_audit(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    rates = {g: {"pct": v.get("pct", 0), "fixed": v.get("fixed", 0)} for g, v in st["gateways"].items() if v.get("pct") is not None}
    if not rates:
        return {"empty": True, "says": "Give each gateway the rate in your contract (Settings) to check its fees."}
    sale: dict[tuple[str, str], float] = defaultdict(float)
    fee: dict[tuple[str, str], float] = defaultdict(float)
    for x in st["settlements"]:
        if not x["order_id"] or x["gateway"] not in rates:
            continue
        if x["type"] == "sale":
            sale[(x["gateway"], x["order_id"])] += x["amount"]
        elif x["type"] == "fee":
            fee[(x["gateway"], x["order_id"])] += x["amount"]
    tx = [{"id": k[1], "gateway": k[0], "amount": round(v, 2), "fee": round(fee.get(k, 0.0), 2)} for k, v in sale.items() if k in fee]
    if not tx:
        return {"empty": True, "says": "No sale with its own fee line in your settlement files (fee lines need the order id)."}
    r = _engine(owner, me, "fee_audit", {"contract": rates, "transactions": tx})
    r["by_gateway"] = {}
    for ln in r["overcharged_lines"]:
        r["by_gateway"][ln["gateway"]] = round(r["by_gateway"].get(ln["gateway"], 0) + ln["over"], 2)
    return r


def prevention(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    sales = defaultdict(int)
    for x in st["settlements"]:
        if x["type"] == "sale":
            sales[x["payout_date"][:7]] += 1
    for o in st["orders"]:
        if o.get("date") and not any(x["type"] == "sale" for x in st["settlements"]):
            sales[o["date"][:7]] += 1
    disp = defaultdict(int)
    for d in st["disputes"]:
        disp[(d.get("received") or "")[:7]] += 1
    months = sorted(set(sales) | set(disp))[-12:]
    a = {"sales": [{"month": m, "count": sales.get(m, 0)} for m in months], "disputes": [{"month": m, "count": disp.get(m, 0)} for m in months],
         "thresholds": {"all": st["thresholds"]["all"]} if st["thresholds"].get("all") is not None else {}}
    if not months:
        return {"months": [], "over": []}
    return _engine(owner, me, "prevention", a)


def dunning(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    chasing = [f for f in st["failed"] if f.get("status") == "chasing"]
    if not chasing:
        return {"customers": [], "failed": st["failed"]}
    cur = str(_wsrow(owner, ws).get("currency") or "").upper()
    r = _engine(owner, me, "dunning", {"failed": [{**{k: f[k] for k in ("customer", "plan", "date", "reason")}, "amount": f"{cur} {f['amount']:,.2f}".strip()}
                                                  for f in chasing],
                                       "retry_days": st["retry_days"]})
    for c, f in zip(r["customers"], chasing):
        c["n"] = f["n"]
        c["date"] = f["date"]
    r["failed"] = st["failed"]
    return r


def set_failed(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if a.get("n") in (None, ""):
        row = {"n": _next_n(st["failed"]), "customer": _text(a.get("customer"), 80), "amount": _num(a.get("amount"), "amount", 0.01),
               "plan": _text(a.get("plan"), 60), "date": _day(a.get("date") or date.today().isoformat(), "date"),
               "reason": _text(a.get("reason"), 80), "status": "chasing"}
        if not row["customer"]:
            raise PayDeskError("customer: who the payment is from.")
        st["failed"].append(row)
    else:
        row = _find(st["failed"], a.get("n"), "failed payment")
        s = str(a.get("status") or "")
        if s not in ("chasing", "recovered", "cancelled"):
            raise PayDeskError("status: chasing | recovered | cancelled.")
        row["status"], row["status_by"], row["status_on"] = s, me, _now()
    _put(owner, ws, st)
    return {"failed": row}


def payouts(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["market"]:
        return {"sellers": [], "empty": True}
    if st.get("commission_pct") is None:
        return {"sellers": [], "error": "Give your commission in Settings to work out what each seller is owed."}
    r = _engine(owner, me, "payouts", {"commission_pct": st["commission_pct"],
                                       "orders": [{"seller": m["seller"], "amount": m["amount"], "type": m["type"], "fee": m["fee"]}
                                                  for m in st["market"]]})
    return r


def payouts_csv(r: dict[str, Any]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Seller", "Sales", "Refunds", "Commission", "Fees", "Owed", "Carried forward"])
    for s in r.get("sellers") or []:
        w.writerow([s["seller"], s["sales"], s["refunds"], s["commission"], s["fees"], s["owed"], "yes" if s["carry_forward"] else ""])
    w.writerow([])
    w.writerow([FOOT])
    return buf.getvalue().encode("utf-8")


def save_settings(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if "gateway" in a:
        gw = _text(a.get("gateway"), 40).lower()
        if not gw:
            raise PayDeskError("gateway: its name.")
        if a.get("remove"):
            st["gateways"].pop(gw, None)
        else:
            g = st["gateways"].setdefault(gw, {})
            for k in ("pct", "fixed", "window_days"):
                if k in a:
                    g[k] = _num(a[k], k, 0) if a[k] not in (None, "") else None
            g["source"] = _text(a.get("source"), 160) or g.get("source", "")
            g["by"], g["on"] = me, _now()
    if "commission_pct" in a:
        st["commission_pct"] = _num(a["commission_pct"], "commission_pct", 0) if a["commission_pct"] not in (None, "") else None
    if "threshold_pct" in a:
        if a["threshold_pct"] in (None, ""):
            st["thresholds"].pop("all", None)
        else:
            st["thresholds"]["all"] = _num(a["threshold_pct"], "threshold_pct", 0)
    if "retry_days" in a:
        rd = a["retry_days"]
        rd = [x.strip() for x in rd.split(",")] if isinstance(rd, str) else rd
        st["retry_days"] = sorted({int(_num(x, "retry_days", 0)) for x in rd if str(x).strip()})[:8] or [1, 3, 7]
    if "window_days" in a and "gateway" not in a:
        st["window_days"] = int(_num(a["window_days"], "window_days", 0))
    _put(owner, ws, st)
    return {"gateways": st["gateways"], "commission_pct": st["commission_pct"], "thresholds": st["thresholds"], "retry_days": st["retry_days"],
            "window_days": st["window_days"]}


# ---------------------------------------------------------------- today
def today_view(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    ds = [dispute_view(owner, ws, d, me) for d in st["disputes"]]
    open_ = [d for d in ds if d["status"] == "open"]
    out: dict[str, Any] = {"disputes": [{k: v for k, v in d.items() if k not in ("read", "prior", "disputed_tx")}
                                        | {"verdict": (d.get("read") or {}).get("verdict"), "reason": (d.get("read") or {}).get("reason"),
                                           "missing": len((d.get("read") or {}).get("evidence_missing") or [])} for d in ds],
                           "gateways": st["gateways"], "commission_pct": st["commission_pct"], "thresholds": st["thresholds"],
                           "retry_days": st["retry_days"], "window_days": st["window_days"], "files": list(reversed(st["files"]))[:12],
                           "counts": {k: len(st[k]) for k in ("settlements", "orders", "failed", "market")},
                           "evidence_keys": _evkeys()}
    try:
        rc = reconcile(owner, ws, me)
    except PayDeskError as e:
        rc = {"error": str(e)}
    out["reconcile"] = {k: rc.get(k) for k in ("empty", "error", "balanced", "payouts_without_deposit", "by_gateway", "deposits_read")} | {
        "orders_off": (len((rc.get("orders") or {}).get("missing_at_gateway") or []) + len((rc.get("orders") or {}).get("amount_differs") or [])
                       + len((rc.get("orders") or {}).get("gateway_sale_without_order") or [])) if rc.get("orders") else 0}
    try:
        fa = fee_audit(owner, ws, me)
    except PayDeskError as e:
        fa = {"error": str(e)}
    out["fees"] = {k: fa.get(k) for k in ("empty", "error", "overcharged_total", "checked", "by_gateway")}
    try:
        out["prevention"] = prevention(owner, ws, me)
    except PayDeskError as e:
        out["prevention"] = {"error": str(e), "months": []}
    cur = str(_wsrow(owner, ws).get("currency") or "").upper()
    chasing = [f for f in st["failed"] if f.get("status") == "chasing"]
    out["failed_chasing"] = {"count": len(chasing), "amount": round(sum(f["amount"] for f in chasing), 2)}
    needs = []
    for d in sorted(open_, key=lambda d: (d["days_left"] if d["days_left"] is not None else 999)):
        if d["days_left"] is not None and d["days_left"] < 0:
            needs.append({"say": f"Dispute #{d['n']} ({d['network'].title()} {d['reason_code']}) - the response date has passed", "go": f"disputes/{d['n']}",
                          "bad": True})
        elif d["days_left"] is not None:
            needs.append({"say": f"Dispute #{d['n']} ({d['network'].title()} {d['reason_code']}, {cur} {d['amount']:,.2f}) - respond within {d['days_left']} days",
                          "go": f"disputes/{d['n']}", "bad": d["days_left"] <= 3})
        else:
            needs.append({"say": f"Dispute #{d['n']}: give your processor's response window to see the date", "go": f"disputes/{d['n']}"})
    for p in (out["reconcile"].get("payouts_without_deposit") or [])[:5]:
        needs.append({"say": f"Payout {p} has no matching deposit in your bank statements", "go": "reconcile", "bad": True})
    if out["reconcile"].get("orders_off"):
        needs.append({"say": f"{out['reconcile']['orders_off']} order(s) do not match the gateway's lines", "go": "reconcile"})
    if fa.get("overcharged_total"):
        needs.append({"say": f"Fees above your contract rate: {cur} {fa['overcharged_total']:,.2f} - raise them with the gateway", "go": "reconcile",
                      "bad": True})
    for m in (out["prevention"].get("over") or [])[:3]:
        needs.append({"say": f"Disputes {m['dispute_pct']}% of sales in {m['month']} - at or over your limit", "go": "disputes", "bad": True})
    if chasing:
        needs.append({"say": f"{len(chasing)} failed recurring payment(s) to chase", "go": "recurring"})
    if any(g.get("pct") is None for g in st["gateways"].values()):
        needs.append({"say": "Give each gateway the rate in your contract so Hoola can check its fees", "go": "settings"})
    out["needs"] = needs
    return out


def summary(tenant: str, want: str = "") -> dict[str, Any]:
    from .fin.desks import books_ent as E
    h = _hire()
    st = h.status(tenant, KEY)
    trust = ""
    if st not in ("hired", "paused"):
        try:
            shared = E.shared_with(tenant)
        except Exception:   # noqa: BLE001
            shared = []
        if not shared:
            return {"hired": False, "status": st, "say": "Payments is not hired. Hire it from AI Employees."}
    else:
        with session() as s:
            trust = h._view(h._row(s, tenant, KEY)).get("trust") or ""    # noqa: SLF001
    out: dict[str, Any] = {"hired": True, "status": st if st in ("hired", "paused") else "member",
                           "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
                           "businesses": businesses(tenant), "workspace": workspace(tenant, want), "roles": ROLE_SAY, "foot": FOOT}
    w = out["workspace"]
    if w:
        try:
            acc = E.access(tenant, w["id"])
            out["role"] = acc["role"]
            out["can_write"] = acc["role"] in WRITE
            out["desk"] = today_view(acc["owner"], w["id"], f"{acc['name']} <{tenant}>")
        except Exception as e:   # noqa: BLE001
            log.exception("payments desk read failed")
            out["desk_error"] = str(e)[:200]
    return out


READS = {"dispute", "reconcile", "fee_audit", "prevention", "dunning", "payouts", "reasons", "kyb", "iso20022", "safeguarding",
         "merchant_risk", "exceptions", "returns"}


def do(caller: str, part: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin.desks import books_ent as E
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    ws = str(a.get("workspace") or "")
    acc = E.access(caller, ws)
    role, owner = acc["role"], acc["owner"]
    me = f"{acc['name']} <{caller}>"
    if part not in READS and role not in WRITE:
        raise PayDeskError(f"Your role ({ROLE_SAY.get(role, role)}) can read this desk but not change it.")
    tool = {k: a[k] for k in a if k != "workspace"}
    f = {
        "dispute": lambda: dispute_view(owner, ws, _find(_state(owner, ws)["disputes"], a.get("n"), "dispute"), me),
        "reconcile": lambda: reconcile(owner, ws, me), "fee_audit": lambda: fee_audit(owner, ws, me),
        "prevention": lambda: prevention(owner, ws, me), "dunning": lambda: dunning(owner, ws, me), "payouts": lambda: payouts(owner, ws, me),
        "reasons": lambda: _engine(owner, me, "reasons", {}),
        "kyb": lambda: _engine(owner, me, "kyb", tool), "iso20022": lambda: _engine(owner, me, "iso20022", tool),
        "safeguarding": lambda: _engine(owner, me, "safeguarding", tool), "merchant_risk": lambda: _engine(owner, me, "merchant_risk", tool),
        "exceptions": lambda: _engine(owner, me, "exceptions", tool), "returns": lambda: _engine(owner, me, "returns", tool),
        "add_dispute": lambda: add_dispute(owner, ws, a, me), "edit_dispute": lambda: edit_dispute(owner, ws, a, me),
        "status": lambda: set_status(owner, ws, a, me), "remove_dispute": lambda: remove_dispute(owner, ws, a.get("n")),
        "upload": lambda: upload(owner, ws, a, me), "clear": lambda: clear(owner, ws, a),
        "failed": lambda: set_failed(owner, ws, a, me), "settings": lambda: save_settings(owner, ws, a, me),
    }.get(part)
    if f is None:
        raise PayDeskError("Not a Payments desk action.")
    out = f()
    if part not in READS:
        forget(owner)
        forget(caller)
    return out


def letter_pdf(d: dict[str, Any], business: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    y = H - 18 * mm

    def line(txt: str, size: float = 10, bold: bool = False):
        nonlocal y
        for part in [txt[i:i + 100] for i in range(0, max(1, len(txt)), 100)] or [""]:
            if y < 18 * mm:
                c.showPage()
                y = H - 18 * mm
            c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
            c.drawString(16 * mm, y, part)
            y -= size * 1.55

    line(business, 13, True)
    for i, ln in enumerate(str((d.get("read") or {}).get("letter") or "").splitlines()):
        line(ln.replace("[merchant name, contact]", business), 11 if i == 0 else 10, i == 0)
    y -= 8
    line("Prepared by Hoola for you to check and submit through your processor. Hoola submits nothing.", 8)
    c.save()
    return buf.getvalue()


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- the chat
def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def greeting(tenant: str) -> str:
    d = summary(tenant)
    if not d.get("hired"):
        return "I look after your payments: chargebacks, gateway payouts, fees and failed payments. Hire me from AI Employees to start."
    if not d.get("workspace"):
        return "Hello. Set up your business in Books & Accounts first (name, country, currency), then I can work on your payments."
    k = d.get("desk") or {}
    open_ = [x for x in k.get("disputes") or [] if x["status"] == "open"]
    bits = []
    if open_:
        bits.append(f"{len(open_)} open dispute(s)")
    if (k.get("reconcile") or {}).get("payouts_without_deposit"):
        bits.append(f"{len(k['reconcile']['payouts_without_deposit'])} payout(s) not found in the bank")
    if (k.get("failed_chasing") or {}).get("count"):
        bits.append(f"{k['failed_chasing']['count']} failed payment(s) to chase")
    return ("Hello. " + ("On this desk: " + ", ".join(bits) + ". " if bits else "")
            + "Ask me what a chargeback reason code needs, drop a gateway settlement file here, or ask why a payout is short. I submit, "
              "charge and pay nothing.")


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Payments chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False, delivered_to_agent=True))
    return {"id": cid, "new": True}


RULES = ("You are her Payments employee, talking in the desk's own chat (or a voice call started from it). Use the " + TOOL +
         " tool: dispute (a chargeback's reason code -> the evidence that answers it, what is missing, the response letter; Visa 10.4 "
         "compelling evidence), reasons, prevention, reconcile (orders vs gateway settlement lines vs bank deposits), fee_audit (fees vs her "
         "contract rate), dunning, payouts (marketplace sellers), export, kyb, merchant_risk, safeguarding, iso20022, exceptions, returns. "
         "Every figure you say comes from the tool or the desk below - never estimate one. Reason-code tables are Hoola's, from memory: say "
         "'check this against your processor's dispute guide'. Hoola never submits a dispute response, never charges a card and never pays "
         "anyone: she or her processor does. Never ask for or keep a card number, a CVV, a password or an API key. Plain English, short. Not "
         "legal or scheme advice. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<payments_desk>{RULES}Payments is not hired yet: tell her to hire it from AI Employees.</payments_desk>"
        elif not d.get("workspace"):
            txt = f"\n\n<payments_desk>{RULES}\nNo business set up yet: ask her to set it up in Books & Accounts.</payments_desk>"
        else:
            w, k = d["workspace"], d.get("desk") or {}
            ds = "; ".join(f"#{x['n']} {x['network']} {x['reason_code']} {x['amount']:,.2f} {x['status']}"
                           + (f", {x['days_left']} days left" if x.get("days_left") is not None else "") for x in (k.get("disputes") or [])[-12:]) or "none"
            rc = k.get("reconcile") or {}
            gws = ", ".join(f"{g} ({v.get('pct')}% + {v.get('fixed')})" for g, v in (k.get("gateways") or {}).items()) or "none"
            txt = (f"\n\n<payments_desk>{RULES}\nBusiness: {w['name']} (workspace {w['id']}), {', '.join(w['countries'])}, currency {w['currency']}."
                   f"\nDisputes: {ds}.\nGateways and her contract rates: {gws}."
                   f"\nReconciliation: {'no settlement files yet' if rc.get('empty') else ('balanced' if rc.get('balanced') else 'not balanced')}"
                   f"; payouts with no bank deposit: {', '.join(rc.get('payouts_without_deposit') or []) or 'none'}."
                   f"\nFees above contract: {(k.get('fees') or {}).get('overcharged_total') or 0}."
                   f"\nFailed recurring payments being chased: {(k.get('failed_chasing') or {}).get('count', 0)}."
                   + (f"\nShe is the {d.get('role')} on this business (someone else owns it): explain from these figures and send her "
                      "to the desk for changes." if d.get("role") not in (None, "owner") else "")
                   + "</payments_desk>")
    except Exception:   # noqa: BLE001
        log.exception("payments block failed")
        txt = f"\n\n<payments_desk>{RULES}The desk could not be read just now.</payments_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/payments/chat", dependencies=dep)
    def pay_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/payments/chat/new", dependencies=dep)
    def pay_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/payments/chat/{conv}/ok", dependencies=dep)
    def pay_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Payments chat")
        return {"ok": True}

    @router.get("/api/payments/desk", dependencies=dep)
    def pay_desk(workspace: str = "", tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant, workspace)

    @router.post("/api/payments/do/{part}", dependencies=dep)
    def pay_do(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        from .fin import laws as L
        from .fin.desks.safety import SafetyError
        try:
            return do(tenant, part, body or {})
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (SafetyError, ValueError) as e:
            raise HTTPException(400, str(e))

    @router.get("/api/payments/download", dependencies=dep)
    def pay_download(workspace: str, what: str, n: int = 0, tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response
        from .fin.desks import books_ent as E
        try:
            acc = E.access(tenant, workspace)
            me = f"{acc['name']} <{tenant}>"
            biz = next((b["name"] for b in businesses(tenant) if b["id"] == workspace), "Business")
            if what == "letter":
                d = dispute_view(acc["owner"], workspace, _find(_state(acc["owner"], workspace)["disputes"], n, "dispute"), me)
                if (d.get("read") or {}).get("error"):
                    raise PayDeskError(d["read"]["error"])
                return Response(letter_pdf(d, biz), media_type="application/pdf",
                                headers={"Content-Disposition": f'attachment; filename="dispute-{d["n"]}-response.pdf"'})
            if what == "payouts":
                return Response(payouts_csv(payouts(acc["owner"], workspace, me)), media_type="text/csv",
                                headers={"Content-Disposition": 'attachment; filename="seller-payouts.csv"'})
        except ValueError as e:
            raise HTTPException(400, str(e))
        raise HTTPException(400, "what: letter | payouts")

    @router.put("/api/payments/workspace", dependencies=dep)
    def pay_workspace(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return pick(tenant, str((body or {}).get("workspace") or ""))
        except PayDeskError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
