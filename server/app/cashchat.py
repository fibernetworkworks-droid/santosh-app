"""CASH & TREASURY DESK - the Cash & Treasury employee's own section, like Payroll, Tax and Books & Accounts (owner: "NOW LETS WORK ON
NEXT EMPLOYEE CASH AND TRESARY ---- MAKE IT FULLY FUCTIONAL SAME AS PAYROLL SECTION. ALSO MAKE DESIGN ADVANCE AND PREMIUM SAME AS OTHER
SECTIONS").

- The Cash chat = a Conversation with kind 'cash', kept out of every Hoola chat list (callconv.not_call); facts she tells it still reach
  her one memory. A turn in it (or a voice call started from it) gets the desk's state as a block and the cash tool (`cash_treasury`,
  family treasury) in view.
- The desk's pages run the F5 engine (fin/desks/cash.py) on the business she picked (a finance workspace, the same businesses as Books &
  Accounts). Her team works here too: owner / accountant / approver change things, auditor and viewer read.
- What the desk adds to the engine, kept in the workspace settings under `cash_desk`:
    opening    the cash she says is in the bank today, with the day she said it (else the statements' balance).
    items      her own one-off money in / out she expects (a tax payment, a loan coming in), each with who added it.
    checked    a loan covenant is tested only once a person checked it against the loan agreement - who and when are kept; a changed
               covenant needs checking again.
    figures    the figures her covenants divide (net debt, EBITDA ...), as she gave them and when.
    rates      the exchange rates she gave (book currency per one unit), with the day.
- Hoola works out the figures. It moves no money, opens no account and names no product.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.cashchat")

KIND = "cash"
KEY = "cash_treasury"          # the Hub employee
TOOL = "cash_treasury"         # its tool
FAMILIES = ["treasury"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FOOT = "Hoola works out your cash figures. It moves no money, opens no account and names no product."
WRITE = {"owner", "accountant", "approver"}
ROLE_SAY = {"owner": "Owner", "accountant": "Accountant", "approver": "Approver", "auditor": "Auditor", "viewer": "Viewer"}
KIND_SAY = {"min_cash": "Cash at least", "max_ratio": "Ratio at most", "min_ratio": "Ratio at least"}
STALE_DAYS = 7


class CashDeskError(ValueError):
    pass


def is_cash(conv: str) -> bool:
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
        log.exception("cash chat kind read failed")
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
        raise CashDeskError("No such business.")
    try:
        _hire().save_settings(tenant, KEY, workspace=ws)
    except Exception:   # noqa: BLE001
        pass
    forget(tenant)
    return {"workspace": ws}


# ---------------------------------------------------------------- desk state (kept in the workspace settings)
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _settings(owner: str, ws: str) -> dict[str, Any]:
    from .fin import profile as PR
    return dict(PR.get(owner, ws).get("settings") or {})


def _cfg(owner: str, ws: str) -> dict[str, Any]:
    from .fin.calc import from_minor
    from .fin import profile as PR
    w = PR.get(owner, ws)
    c = dict((w.get("settings") or {}).get("cash") or {})
    if "min_cash_minor" in c:
        c["min_cash"] = float(from_minor(int(c.pop("min_cash_minor")), str(w.get("currency") or "USD").upper()))
    return c


def _state(owner: str, ws: str) -> dict[str, Any]:
    st = dict(_settings(owner, ws).get("cash_desk") or {})
    for k, v in (("items", []), ("checked", {}), ("figures", {}), ("rates", {}), ("opening", None)):
        st.setdefault(k, v)
    return st


def _put(owner: str, ws: str, st: dict[str, Any]) -> None:
    from . import db
    from .fin.models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != owner:
            raise CashDeskError("No such business.")
        cur = json.loads(row.settings or "{}")
        cur["cash_desk"] = st
        row.settings = json.dumps(cur)
        s.commit()


def _num(v: Any, what: str) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        raise CashDeskError(f"{what}: a number.")


def _day(v: Any, what: str) -> str:
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        raise CashDeskError(f"{what}: a date as YYYY-MM-DD.")


def _sig(c: dict[str, Any]) -> str:
    return f"{c.get('kind')}|{c.get('numerator') or ''}|{c.get('denominator') or ''}|{float(c.get('limit') or 0):g}"


def covenants_view(owner: str, ws: str) -> list[dict[str, Any]]:
    """Every covenant she set, with whether a person checked it against the loan agreement at these terms."""
    chk = _state(owner, ws)["checked"]
    out = []
    for c in _cfg(owner, ws).get("covenants") or []:
        k = chk.get(c["name"])
        ok = bool(k and k.get("sig") == _sig(c))
        test = (f"cash at least {c['limit']:g}" if c["kind"] == "min_cash" else
                f"{c['numerator']} / {c['denominator']} {'at most' if c['kind'] == 'max_ratio' else 'at least'} {c['limit']:g}")
        out.append({**c, "test": test, "checked": ok, "checked_on": k.get("on") if ok else None, "checked_by": k.get("by") if ok else None})
    return out


# ---------------------------------------------------------------- what the desk does
def _engine(owner: str, me: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin import core
    from .fin.desks import cash as C
    return core.run_tool(owner, me, TOOL, action, dict(a), lambda: C.run(owner, action, a, me))


def _fargs(owner: str, ws: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    st = _state(owner, ws)
    a: dict[str, Any] = {"workspace": ws, "items": [{"date": x["date"], "amount": x["amount"], "label": x["label"]} for x in st["items"]]}
    if st.get("opening"):
        a["opening"] = st["opening"]["amount"]
    for k, v in (extra or {}).items():
        if k in ("start", "weeks", "lag_days", "weeks_buffer", "since", "upto", "move_pct"):
            a[k] = v
    return a


def forecast(owner: str, ws: str, me: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    from .fin.desks import cash as C
    extra = dict(extra or {})
    late = int(_num(extra.pop("pay_later_days", 0) or 0, "pay_later_days"))
    if late:
        extra["lag_days"] = int(_cfg(owner, ws).get("lag_days") or 0) + late
    try:
        f = _engine(owner, me, "forecast", _fargs(owner, ws, extra))
    except C.CashError as e:
        raise CashDeskError(str(e))
    st = _state(owner, ws)
    op = st.get("opening")
    if op:
        f["opening_from"] = f"the cash you said was in the bank on {op['as_of']}"
        f["opening_stale"] = op["as_of"] < (date.today() - timedelta(days=STALE_DAYS)).isoformat()
    f["what_if"] = {"pay_later_days": late} if late else None
    weeks = f.get("weeks") or []
    f["total_in"] = round(sum(w["in"] for w in weeks), 2)
    f["total_out"] = round(sum(w["out"] for w in weeks), 2)
    f["closing"] = weeks[-1]["closing"] if weeks else f.get("opening")
    return f


def backtest(owner: str, ws: str, me: str) -> dict[str, Any]:
    from .fin.desks import cash as C
    try:
        return _engine(owner, me, "backtest", {"workspace": ws})
    except C.CashError as e:
        return {"error": str(e)}


def add_item(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    label = str(a.get("label") or "").strip()[:80]
    if not label:
        raise CashDeskError("What is it (a tax payment, a loan coming in ...).")
    amt = abs(_num(a.get("amount"), "amount"))
    if not amt:
        raise CashDeskError("amount: more than zero.")
    direction = str(a.get("direction") or "out")
    if direction not in ("in", "out"):
        raise CashDeskError("direction: in | out.")
    st = _state(owner, ws)
    n = 1 + max([int(x.get("n") or 0) for x in st["items"]] or [0])
    row = {"n": n, "date": _day(a.get("date"), "date"), "amount": amt if direction == "in" else -amt, "label": label, "by": me, "on": _now()}
    st["items"].append(row)
    st["items"] = sorted(st["items"], key=lambda x: x["date"])[-100:]
    _put(owner, ws, st)
    return {"item": row, "items": st["items"]}


def remove_item(owner: str, ws: str, n: int) -> dict[str, Any]:
    st = _state(owner, ws)
    before = len(st["items"])
    st["items"] = [x for x in st["items"] if int(x.get("n") or 0) != int(n)]
    if len(st["items"]) == before:
        raise CashDeskError("No such item.")
    _put(owner, ws, st)
    return {"items": st["items"]}


def set_opening(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if a.get("amount") in (None, ""):
        st["opening"] = None
    else:
        st["opening"] = {"amount": _num(a["amount"], "amount"), "as_of": _day(a.get("as_of") or date.today().isoformat(), "as_of"), "by": me}
    _put(owner, ws, st)
    return {"opening": st["opening"]}


def save_settings(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    from .fin.desks import cash as C
    keep = {k: a[k] for k in ("min_cash", "lag_days", "weeks_buffer", "exclude") if k in a and a[k] not in (None, "")}
    if isinstance(keep.get("exclude"), str):
        keep["exclude"] = [x.strip() for x in keep["exclude"].split(",") if x.strip()]
    try:
        return _engine(owner, me, "settings", {"workspace": ws, **keep})
    except C.CashError as e:
        raise CashDeskError(str(e))


def set_covenant(owner: str, ws: str, a: dict[str, Any], me: str, remove: bool = False) -> dict[str, Any]:
    """Add, change or remove one covenant; a changed one needs checking again (its terms are part of the check)."""
    from .fin.desks import cash as C
    name = str(a.get("name") or "").strip()[:80]
    if not name:
        raise CashDeskError("name: what your loan agreement calls it.")
    cur = [c for c in (_cfg(owner, ws).get("covenants") or []) if c["name"] != name]
    if not remove:
        cur.append({"name": name, "kind": a.get("kind"), "limit": a.get("limit"), "numerator": a.get("numerator") or "",
                    "denominator": a.get("denominator") or ""})
    try:
        _engine(owner, me, "settings", {"workspace": ws, "covenants": cur})
    except C.CashError as e:
        raise CashDeskError(str(e))
    if remove:
        st = _state(owner, ws)
        st["checked"].pop(name, None)
        _put(owner, ws, st)
    return {"covenants": covenants_view(owner, ws)}


def check_covenant(owner: str, ws: str, name: str, me: str) -> dict[str, Any]:
    c = next((x for x in _cfg(owner, ws).get("covenants") or [] if x["name"] == name), None)
    if c is None:
        raise CashDeskError("That covenant is not in your settings.")
    st = _state(owner, ws)
    st["checked"][name] = {"sig": _sig(c), "on": _now(), "by": me}
    _put(owner, ws, st)
    return {"covenants": covenants_view(owner, ws)}


def set_figure(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    name = str(a.get("name") or "").strip()[:40]
    if not name:
        raise CashDeskError("name: the figure your covenant uses (net_debt, ebitda ...).")
    st = _state(owner, ws)
    if a.get("value") in (None, ""):
        st["figures"].pop(name, None)
    else:
        st["figures"][name] = {"value": _num(a["value"], "value"), "as_of": _day(a.get("as_of") or date.today().isoformat(), "as_of"), "by": me}
    _put(owner, ws, st)
    return {"figures": st["figures"]}


def covenants(owner: str, ws: str, me: str) -> dict[str, Any]:
    """Only the covenants a person checked are tested; the rest are listed to check against the loan agreement."""
    from .fin.desks import cash as C
    view = covenants_view(owner, ws)
    st = _state(owner, ws)
    done = [c for c in view if c["checked"]]
    out: dict[str, Any] = {"covenants": view, "figures": st["figures"], "results": [], "breached": [],
                           "to_check": [c["name"] for c in view if not c["checked"]]}
    if done:
        a = _fargs(owner, ws)
        a["covenants"] = [{k: c[k] for k in ("name", "kind", "limit", "numerator", "denominator")} for c in done]
        a["figures"] = {k: v["value"] for k, v in st["figures"].items()}
        try:
            r = _engine(owner, me, "covenants", a)
            out["results"], out["breached"], out["says"] = r["covenants"], r["breached"], r["says"]
        except C.CashError as e:
            out["error"] = str(e)
    return out


def set_rate(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    code = str(a.get("currency") or "").strip().upper()
    if len(code) != 3 or not code.isalpha():
        raise CashDeskError("currency: a three-letter code like EUR.")
    st = _state(owner, ws)
    if a.get("rate") in (None, ""):
        st["rates"].pop(code, None)
    else:
        r = _num(a["rate"], "rate")
        if r <= 0:
            raise CashDeskError("rate: more than zero.")
        st["rates"][code] = {"rate": r, "on": _day(a.get("on") or date.today().isoformat(), "on"), "by": me}
    _put(owner, ws, st)
    return {"rates": st["rates"]}


def fx(owner: str, ws: str, me: str, move_pct: Any = None) -> dict[str, Any]:
    from .fin.desks import cash as C
    st = _state(owner, ws)
    a = {"workspace": ws, "rates": {k: v["rate"] for k, v in st["rates"].items()}}
    if move_pct not in (None, ""):
        a["move_pct"] = _num(move_pct, "move_pct")
    try:
        r = _engine(owner, me, "fx", a)
    except C.CashError as e:
        raise CashDeskError(str(e))
    for p in r.get("positions") or []:
        g = st["rates"].get(p["currency"])
        p["rate_on"] = g["on"] if g else None
        p["rate_stale"] = bool(g and g["on"] < (date.today() - timedelta(days=STALE_DAYS)).isoformat())
    r["move_pct"] = float(a.get("move_pct", 10))
    return r


def idle(owner: str, ws: str, me: str, weeks_buffer: Any = None) -> dict[str, Any]:
    from .fin.desks import cash as C
    extra = {} if weeks_buffer in (None, "") else {"weeks_buffer": int(_num(weeks_buffer, "weeks_buffer"))}
    try:
        return _engine(owner, me, "idle", _fargs(owner, ws, extra))
    except C.CashError as e:
        raise CashDeskError(str(e))


def fees(owner: str, ws: str, me: str, since: str = "", upto: str = "") -> dict[str, Any]:
    from .fin.desks import cash as C
    try:
        return _engine(owner, me, "fees", {"workspace": ws, "since": since, "upto": upto})
    except C.CashError as e:
        raise CashDeskError(str(e))


def forecast_csv(f: dict[str, Any]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["13-week cash forecast", f.get("start", ""), f.get("currency", "")])
    w.writerow(["Opening", f.get("opening"), f.get("opening_from", "")])
    w.writerow([])
    w.writerow(["Week", "From", "To", "Money in", "Money out", "Closing"])
    for wk in f.get("weeks") or []:
        w.writerow([wk["week"], wk["from"], wk["to"], wk["in"], wk["out"], wk["closing"]])
    w.writerow([])
    w.writerow(["Day", "Amount", "What", "From"])
    for wk in f.get("weeks") or []:
        for ln in wk["lines"]:
            w.writerow([ln["day"], ln["amount"], ln["what"], ln["source"] + (" (overdue)" if ln.get("overdue") else "")])
    w.writerow([])
    for k, v in (f.get("view_30_60_90") or {}).items():
        w.writerow([k.replace("_", " "), v])
    w.writerow([])
    w.writerow([f.get("says", "")])
    w.writerow([FOOT])
    return buf.getvalue().encode("utf-8")


def forecast_pdf(f: dict[str, Any], business: str) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    W, H = landscape(A4)
    y = H - 18 * mm
    cur = f.get("currency", "")

    def line(txt: str, size: float = 10, bold: bool = False, cols: list[tuple[float, str]] | None = None):
        nonlocal y
        if y < 18 * mm:
            c.showPage()
            y = H - 18 * mm
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        if txt:
            c.drawString(16 * mm, y, str(txt)[:150])
        for x, t in cols or []:
            c.drawRightString(x, y, str(t))
        y -= size * 1.6

    line(business, 14, True)
    line(f"13-week cash forecast from {f.get('start', '')} · {cur} · opening {f.get('opening', 0):,.2f} ({f.get('opening_from', '')})", 10)
    y -= 4
    xs = [90 * mm, 130 * mm, 170 * mm, 210 * mm]
    line("Week", 9, True, list(zip(xs, ["From", "Money in", "Money out", "Closing"])))
    mn = f.get("minimum")
    for wk in f.get("weeks") or []:
        flag = "  below your minimum" if mn is not None and wk["closing"] < mn else ""
        line(f"{wk['week']}{flag}", 9, False, list(zip(xs, [wk["from"], f"{wk['in']:,.2f}", f"{wk['out']:,.2f}", f"{wk['closing']:,.2f}"])))
    y -= 4
    lo = f.get("lowest") or {}
    line(f"Lowest: week {lo.get('week')} at {lo.get('closing', 0):,.2f}" + (f" · your minimum {mn:,.2f}" if mn is not None else ""), 11, True)
    line("  ".join(f"{k.replace('_', ' ')}: {v:,.2f}" for k, v in (f.get("view_30_60_90") or {}).items()), 10)
    y -= 4
    line(str(f.get("says", "")), 8)
    line(FOOT, 8)
    c.save()
    return buf.getvalue()


def today_view(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    cfg = _cfg(owner, ws)
    out: dict[str, Any] = {"settings": cfg, "opening": st.get("opening"), "items": st["items"], "rates": st["rates"]}
    try:
        f = forecast(owner, ws, me)
    except CashDeskError as e:
        f = {"error": str(e)}
    out["forecast"] = f
    try:
        out["idle"] = idle(owner, ws, me)
    except CashDeskError as e:
        out["idle"] = {"error": str(e)}
    cv = covenants(owner, ws, me)
    out["covenants"] = {k: cv.get(k) for k in ("to_check", "breached", "results")}
    try:
        fe = fees(owner, ws, me)
        out["fees"] = {k: fe.get(k) for k in ("total", "a_year_at_this_rate", "months_read")}
    except CashDeskError:
        out["fees"] = None
    try:
        x = fx(owner, ws, me)
        out["fx"] = {"rates_missing": x.get("rates_missing") or [], "positions": len(x.get("positions") or []),
                     "total_if_all_fall": x.get("total_if_all_fall")}
    except CashDeskError:
        out["fx"] = None
    needs = []
    if f.get("error"):
        needs.append({"say": f["error"], "go": "settings"})
    else:
        if f.get("opening_stale"):
            needs.append({"say": f"The cash in the bank was last given on {st['opening']['as_of']} - add today's figure", "go": "settings"})
        if cfg.get("min_cash") is None:
            needs.append({"say": "Set the least cash you want in the bank, so Hoola can warn you", "go": "settings"})
        if f.get("under_minimum_weeks"):
            wk = f["under_minimum_weeks"]
            needs.append({"say": f"Cash goes under your minimum in week {wk[0]}" + (f" ({len(wk)} weeks in all)" if len(wk) > 1 else ""),
                          "go": "forecast"})
        if f.get("lowest") and f["lowest"]["closing"] < 0:
            needs.append({"say": f"The bank goes overdrawn in week {f['lowest']['week']}", "go": "forecast"})
        for x in (f.get("overdue_invoices") or [])[:5]:
            needs.append({"say": f"Overdue: {x} - counted in week 1, chase it", "go": "forecast"})
    for n in out["covenants"]["breached"] or []:
        needs.append({"say": f"Covenant {n} is not met on these figures - talk to your lender before the test date", "go": "covenants"})
    if out["covenants"]["to_check"]:
        needs.append({"say": f"{len(out['covenants']['to_check'])} covenant(s) to check against your loan agreement", "go": "covenants"})
    if out["fx"] and out["fx"]["rates_missing"]:
        needs.append({"say": "Give a rate for " + ", ".join(out["fx"]["rates_missing"]), "go": "currencies"})
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
            return {"hired": False, "status": st, "say": "Cash & Treasury is not hired. Hire it from AI Employees."}
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
            log.exception("cash desk read failed")
            out["desk_error"] = str(e)[:200]
    return out


READS = {"forecast", "backtest", "idle", "fees", "fx", "covenants"}


def do(caller: str, part: str, a: dict[str, Any]) -> dict[str, Any]:
    """Every desk action: her role on this business first, then the engine / the desk state on the OWNER's books."""
    from .fin.desks import books_ent as E
    from .fin.desks import cash as C
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    ws = str(a.get("workspace") or "")
    acc = E.access(caller, ws)
    role, owner = acc["role"], acc["owner"]
    me = f"{acc['name']} <{caller}>"
    if part not in READS and role not in WRITE:
        raise CashDeskError(f"Your role ({ROLE_SAY.get(role, role)}) can read this desk but not change it.")
    try:
        if part == "forecast":
            out = forecast(owner, ws, me, {k: a[k] for k in ("start", "weeks", "pay_later_days") if k in a})
        elif part == "backtest":
            out = backtest(owner, ws, me)
        elif part == "idle":
            out = idle(owner, ws, me, a.get("weeks_buffer"))
        elif part == "fees":
            out = fees(owner, ws, me, str(a.get("since") or ""), str(a.get("upto") or ""))
        elif part == "fx":
            out = fx(owner, ws, me, a.get("move_pct"))
        elif part == "covenants":
            out = covenants(owner, ws, me)
        elif part == "settings":
            out = save_settings(owner, ws, a, me)
        elif part == "opening":
            out = set_opening(owner, ws, a, me)
        elif part == "add_item":
            out = add_item(owner, ws, a, me)
        elif part == "remove_item":
            out = remove_item(owner, ws, int(a.get("n") or 0))
        elif part == "set_covenant":
            out = set_covenant(owner, ws, a, me)
        elif part == "remove_covenant":
            out = set_covenant(owner, ws, a, me, remove=True)
        elif part == "check_covenant":
            out = check_covenant(owner, ws, str(a.get("name") or ""), me)
        elif part == "figure":
            out = set_figure(owner, ws, a, me)
        elif part == "rate":
            out = set_rate(owner, ws, a, me)
        else:
            raise CashDeskError("Not a Cash & Treasury desk action.")
    except C.CashError as e:
        raise CashDeskError(str(e))
    forget(owner)
    forget(caller)
    return out


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- the chat
def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def _m(v: Any, cur: str) -> str:
    try:
        return f"{float(v):,.2f} {cur}"
    except (TypeError, ValueError):
        return "-"


def greeting(tenant: str) -> str:
    d = summary(tenant)
    if not d.get("hired"):
        return "I keep an eye on your cash. Hire me from AI Employees to start."
    if not d.get("workspace"):
        return "Hello. Set up your business in Books & Accounts first (name, country, currency), and import a bank statement there."
    k = d.get("desk") or {}
    f = k.get("forecast") or {}
    cur = f.get("currency") or d["workspace"].get("currency") or ""
    if f.get("error"):
        return f"Hello. {f['error']} Then I can show your next 13 weeks of cash."
    lo = f.get("lowest") or {}
    line = (f"Hello. You start with {_m(f.get('opening'), cur)}; the lowest point in the next 13 weeks is "
            f"{_m(lo.get('closing'), cur)} in week {lo.get('week')}. ")
    if k.get("needs"):
        line += f"{len(k['needs'])} thing(s) need you. "
    return line + "Ask what moves your cash, add money you expect, or drop a bank statement here. I move no money."


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
        c = Conversation(tenant_id=tenant, kind=KIND, title="Cash chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False, delivered_to_agent=True))
    return {"id": cid, "new": True}


RULES = ("You are her Cash & Treasury employee, talking in the desk's own chat (or a voice call started from it). Use the " + TOOL +
         " tool with workspace set to the business below: forecast (13 weeks from her open invoices and bills, her last payroll and what "
         "repeats in her statements; pass items for money she expects and opening for the cash she gave), backtest (how well the model "
         "predicted months she already lived), idle (cash not needed in any week after her buffer), fees (bank charges), fx (money in "
         "other currencies at the rates she gives), covenants (her loan covenants on her figures), settings. Every figure you say comes "
         "from the tool - never estimate one, never invent an exchange rate. A covenant is tested on this desk only once a person checked "
         "it against the loan agreement; the lender's own calculation decides. You move no money, open no account, place no deposit and "
         "name no bank product: what to do with spare cash is hers. Never ask for or keep a password or a bank login. Plain English, "
         "short. Not financial advice. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<cash_desk>{RULES}Cash & Treasury is not hired yet: tell her to hire it from AI Employees.</cash_desk>"
        elif not d.get("workspace"):
            txt = f"\n\n<cash_desk>{RULES}\nNo business set up yet: ask her to set it up in Books & Accounts.</cash_desk>"
        else:
            w, k = d["workspace"], d.get("desk") or {}
            f = k.get("forecast") or {}
            cur = f.get("currency") or w.get("currency") or ""
            cfg = k.get("settings") or {}
            lo = f.get("lowest") or {}
            items = "; ".join(f"{x['date']} {x['label']} {x['amount']:g}" for x in (k.get("items") or [])[:10]) or "none"
            cv = k.get("covenants") or {}
            txt = (f"\n\n<cash_desk>{RULES}\nBusiness: {w['name']} (workspace {w['id']}), {', '.join(w['countries'])}, book currency {cur}."
                   + (f"\nForecast: {f['error']}" if f.get("error") else
                      f"\nForecast from {f.get('start')}: opening {_m(f.get('opening'), cur)} ({f.get('opening_from')}); lowest week "
                      f"{lo.get('week')} at {_m(lo.get('closing'), cur)}; after 13 weeks {_m(f.get('closing'), cur)}; weeks under her "
                      f"minimum {f.get('under_minimum_weeks') or 'none'}; overdue invoices {', '.join(f.get('overdue_invoices') or []) or 'none'}.")
                   + f"\nHer settings: minimum {cfg.get('min_cash', 'not set')}, customers pay {cfg.get('lag_days', 0)} days late, buffer "
                     f"{cfg.get('weeks_buffer', 4)} weeks."
                   + f"\nHer own expected items: {items}."
                   + f"\nCovenants breached: {', '.join(cv.get('breached') or []) or 'none'}; to check against the loan agreement: "
                     f"{', '.join(cv.get('to_check') or []) or 'none'}."
                   + (f"\nShe is the {d.get('role')} on this business (someone else owns it): explain from these figures and send her "
                      "to the desk for changes." if d.get("role") not in (None, "owner") else "")
                   + "</cash_desk>")
    except Exception:   # noqa: BLE001
        log.exception("cash block failed")
        txt = f"\n\n<cash_desk>{RULES}The desk could not be read just now.</cash_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/cash/chat", dependencies=dep)
    def cash_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/cash/chat/new", dependencies=dep)
    def cash_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/cash/chat/{conv}/ok", dependencies=dep)
    def cash_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Cash chat")
        return {"ok": True}

    @router.get("/api/cash/desk", dependencies=dep)
    def cash_desk(workspace: str = "", tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant, workspace)

    @router.post("/api/cash/do/{part}", dependencies=dep)
    def cash_do(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        from .fin import laws as L
        from .fin.desks.safety import SafetyError
        try:
            return do(tenant, part, body or {})
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (SafetyError, ValueError) as e:
            raise HTTPException(400, str(e))

    @router.get("/api/cash/download", dependencies=dep)
    def cash_download(workspace: str, what: str, pay_later_days: int = 0, tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response
        from .fin.desks import books_ent as E
        try:
            acc = E.access(tenant, workspace)
        except ValueError as e:
            raise HTTPException(404, str(e))
        me = f"{acc['name']} <{tenant}>"
        try:
            f = forecast(acc["owner"], workspace, me, {"pay_later_days": pay_later_days} if pay_later_days else None)
        except CashDeskError as e:
            raise HTTPException(400, str(e))
        biz = next((b["name"] for b in businesses(tenant) if b["id"] == workspace), "Business")
        if what == "csv":
            return Response(forecast_csv(f), media_type="text/csv",
                            headers={"Content-Disposition": f'attachment; filename="cash-forecast-{f["start"]}.csv"'})
        if what == "pdf":
            return Response(forecast_pdf(f, biz), media_type="application/pdf",
                            headers={"Content-Disposition": f'attachment; filename="cash-forecast-{f["start"]}.pdf"'})
        raise HTTPException(400, "what: pdf | csv")

    @router.put("/api/cash/workspace", dependencies=dep)
    def cash_workspace(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return pick(tenant, str((body or {}).get("workspace") or ""))
        except CashDeskError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
