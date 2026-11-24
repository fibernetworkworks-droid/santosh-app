"""v0.999.176 TAX DESK - the Tax (worldwide) employee's own section, like Payroll and Books & Accounts (owner: "OK FINE LET CONTINUE
THE WORK OF AI EMPLOYEE" -> Tax (worldwide) -> the design claude.ai/artifact/Faegn7ZmcGkTQqdkqRtZ1v -> "GO").

- The Tax chat = a Conversation with kind 'tax', kept out of every Hoola chat list (callconv.not_call); facts she tells it still reach
  her one memory. A turn in it (or a voice call started from it) gets the desk's state as a block and the tax tool (`tax_worldwide`,
  family taxwide) in view.
- The desk's pages run the F4 engine (fin/desks/tax.py) on the business she picked (a finance workspace, the same businesses as
  Books & Accounts). Her team works here too: owner / accountant / approver change things, auditor and viewer read.
- What the desk adds to the engine, kept in the workspace settings under `tax_desk`:
    checked   a rate (her VAT rates, state rates, EU country rates, state sales limits) is used by the desk only once a person
              tapped "I checked it" - who and when are kept. A return with an unchecked rate in it is not worked out.
    letters   tax letters she dropped or pasted, read by the engine; the reply-by date read from a letter is a reminder only once
              she confirms it.
    filed     "I filed it" = her tap + the reference from the official site; the period is then locked on this desk.
    papers    the personal papers she ticked as gathered.
- Hoola prepares the figures. She (or her accountant) files and pays. Never files, never pays, never sends a reply.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.taxchat")

KIND = "tax"
KEY = "tax_worldwide"          # the Hub employee
TOOL = "tax_worldwide"         # its tool
FAMILIES = ["taxwide"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FOOT = "Hoola prepares the figures. You or your accountant file and pay."
WRITE = {"owner", "accountant", "approver"}     # change settings, check rates, add dates and letters
FILE = {"owner", "approver"}                    # "I filed it"
ROLE_SAY = {"owner": "Owner", "accountant": "Accountant", "approver": "Approver", "auditor": "Auditor", "viewer": "Viewer"}
RATE_KINDS = ("rates", "state_rates", "oss_rates", "nexus")
RATE_SAY = {"rates": "rate", "state_rates": "state sales tax rate", "oss_rates": "EU country rate", "nexus": "state sales limit"}


class TaxDeskError(ValueError):
    pass


def is_tax(conv: str) -> bool:
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
        log.exception("tax chat kind read failed")
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
        raise TaxDeskError("No such business.")
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


def _state(owner: str, ws: str) -> dict[str, Any]:
    st = dict(_settings(owner, ws).get("tax_desk") or {})
    for k in ("checked", "letters", "filed", "papers"):
        st.setdefault(k, {} if k != "letters" else [])
    return st


def _put(owner: str, ws: str, st: dict[str, Any]) -> None:
    from . import db
    from .fin.models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != owner:
            raise TaxDeskError("No such business.")
        cur = json.loads(row.settings or "{}")
        cur["tax_desk"] = st
        row.settings = json.dumps(cur)
        s.commit()


def _rate_key(kind: str, code: str) -> str:
    return f"{kind}:{code}"


def rates_view(owner: str, ws: str) -> list[dict[str, Any]]:
    """Every rate / limit she set, with whether a person checked it at that value."""
    tax = dict(_settings(owner, ws).get("tax") or {})
    chk = _state(owner, ws)["checked"]
    out = []
    for kind in RATE_KINDS:
        for code, val in sorted((tax.get(kind) or {}).items()):
            c = chk.get(_rate_key(kind, code))
            ok = bool(c and float(c.get("value", -1)) == float(val))
            out.append({"kind": kind, "code": code, "value": float(val), "what": RATE_SAY[kind], "checked": ok,
                        "checked_on": c.get("on") if ok else None, "checked_by": c.get("by") if ok else None})
    return out


def unchecked(owner: str, ws: str, kinds: tuple[str, ...] = RATE_KINDS) -> list[str]:
    return [f"{r['what']} {r['code']} {r['value']:g}" for r in rates_view(owner, ws) if r["kind"] in kinds and not r["checked"]]


def _period_key(p: str) -> str:
    p = str(p or "").upper().strip()
    if not re.fullmatch(r"\d{4}(-Q[1-4]|-\d{2})?", p):
        raise TaxDeskError("period: YYYY-Qn, YYYY-MM or YYYY.")
    return p


def current_period(cfg: dict[str, Any], today: date | None = None) -> str:
    """The last finished return period (the one to prepare now)."""
    t = today or date.today()
    kind = cfg.get("period_kind") or "quarterly"
    if kind == "monthly":
        last = t.replace(day=1) - timedelta(days=1)
        return f"{last.year}-{last.month:02d}"
    if kind == "yearly":
        return str(t.year - 1)
    q = (t.month - 1) // 3          # this quarter is 1..4 -> the previous finished one
    return f"{t.year - 1}-Q4" if q == 0 else f"{t.year}-Q{q}"


def periods(cfg: dict[str, Any], n: int = 6, today: date | None = None) -> list[str]:
    out, p = [], current_period(cfg, today)
    for _ in range(n):
        out.append(p)
        m = re.fullmatch(r"(\d{4})-Q([1-4])", p)
        if m:
            y, q = int(m[1]), int(m[2]) - 1
            p = f"{y - 1}-Q4" if q == 0 else f"{y}-Q{q}"
        elif re.fullmatch(r"\d{4}-\d{2}", p):
            y, mo = int(p[:4]), int(p[5:])
            p = f"{y - 1}-12" if mo == 1 else f"{y}-{mo - 1:02d}"
        else:
            p = str(int(p) - 1)
    return out


# ---------------------------------------------------------------- what the desk does
def _engine(owner: str, me: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin import core
    from .fin.desks import tax as T
    return core.run_tool(owner, me, TOOL, action, dict(a), lambda: T.run(owner, action, a, me))


def prepare(owner: str, ws: str, period: str, me: str) -> dict[str, Any]:
    """The return for a period, refused while a rate in it is unchecked; a filed period comes back locked with its reference."""
    from .fin.desks import tax as T
    p = _period_key(period)
    st = _state(owner, ws)
    filed = st["filed"].get(p)
    todo = unchecked(owner, ws, ("rates",))
    if todo and not filed:
        return {"period": p, "blocked": True, "rates_to_check": todo,
                "say": "A rate is used only once a person checks it. Check these in Dates & settings first: " + ", ".join(todo) + "."}
    try:
        out = _engine(owner, me, "return", {"workspace": ws, "period": p})
    except T.TaxError as e:
        return {"period": p, "blocked": True, "say": str(e)}
    out["period"] = p
    out["filed"] = filed
    out["locked"] = bool(filed)
    out["checks"] = _checks(owner, ws, out)
    return out


def _checks(owner: str, ws: str, r: dict[str, Any]) -> list[dict[str, Any]]:
    from .fin.desks import books as BK
    rows = [{"ok": True, "say": f"Every sale and bill in the period is in the return ({len(r.get('documents') or [])} documents)"}]
    since, upto = r.get("since", ""), r.get("upto", "")
    months, d = [], date.fromisoformat(since) if since else None
    while d and d.isoformat() <= upto:
        months.append(f"{d.year}-{d.month:02d}")
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    try:
        open_m = [m for m in months if not BK.locked(owner, ws, m)]
    except Exception:   # noqa: BLE001
        open_m = []
    rows.append({"ok": not open_m, "say": "Every month in the period is closed in your books" if not open_m else
                 f"Not closed in your books yet: {', '.join(open_m)} - a late posting would change the figures"})
    chk = [x for x in rates_view(owner, ws) if x["kind"] == "rates" and x["checked"]]
    if chk:
        rows.append({"ok": True, "say": "Rates " + ", ".join(f"{x['value']:g}%" for x in chk) + " checked by a person"})
    for w_ in r.get("warnings") or []:
        rows.append({"ok": False, "say": str(w_)})
    return rows


def mark_filed(owner: str, ws: str, period: str, reference: str, me: str) -> dict[str, Any]:
    p = _period_key(period)
    ref = str(reference or "").strip()[:80]
    if len(ref) < 3:
        raise TaxDeskError("Add the reference the official site gave you when you filed.")
    st = _state(owner, ws)
    if p in st["filed"]:
        raise TaxDeskError(f"{p} is already marked as filed (reference {st['filed'][p]['reference']}).")
    r = prepare(owner, ws, p, me)
    st["filed"][p] = {"reference": ref, "on": _now(), "by": me, "to_pay": r.get("to_pay"), "to_reclaim": r.get("to_reclaim"),
                      "currency": r.get("currency")}
    _put(owner, ws, st)
    return {"period": p, "filed": st["filed"][p], "locked": True,
            "say": f"{p} marked as filed by you, reference {ref}. The period is locked on this desk."}


def check_rate(owner: str, ws: str, kind: str, code: str, me: str) -> dict[str, Any]:
    if kind not in RATE_KINDS:
        raise TaxDeskError("kind: " + ", ".join(RATE_KINDS))
    tax = dict(_settings(owner, ws).get("tax") or {})
    val = (tax.get(kind) or {}).get(code)
    if val is None:
        raise TaxDeskError("That rate is not in your settings.")
    st = _state(owner, ws)
    st["checked"][_rate_key(kind, code)] = {"value": float(val), "on": _now(), "by": me}
    _put(owner, ws, st)
    return {"kind": kind, "code": code, "value": float(val), "checked": True}


def set_rate(owner: str, ws: str, kind: str, code: str, value: Any, me: str) -> dict[str, Any]:
    """Add or change one rate; a changed value needs checking again."""
    from .fin.desks import tax as T
    if kind not in RATE_KINDS:
        raise TaxDeskError("kind: " + ", ".join(RATE_KINDS))
    code = str(code or "").strip()
    if kind != "rates":
        code = code.upper()
    if not code:
        raise TaxDeskError("Which rate (a tax code, a state like CA, or a country like IT).")
    tax = dict(_settings(owner, ws).get("tax") or {})
    cur = dict(tax.get(kind) or {})
    if value in (None, ""):
        cur.pop(code, None)
    else:
        cur[code] = value
    if not cur:
        cur = {}
    try:
        _engine(owner, me, "settings", {"workspace": ws, kind: cur}) if cur else _clear(owner, ws, kind)
    except T.TaxError as e:
        raise TaxDeskError(str(e))
    return {"rates": rates_view(owner, ws)}


def _clear(owner: str, ws: str, kind: str) -> None:
    from . import db
    from .fin.models import FinWorkspace
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        stt = json.loads(row.settings or "{}")
        stt.setdefault("tax", {})[kind] = {}
        row.settings = json.dumps(stt)
        s.commit()


def add_letter(owner: str, ws: str, text: str, name: str, me: str) -> dict[str, Any]:
    from .fin.desks import tax as T
    tax = dict(_settings(owner, ws).get("tax") or {})
    try:
        r = T.notice(owner, "", {"text": text, "country": tax.get("country") or ""})   # no workspace: the date waits for her confirm
    except T.TaxError as e:
        raise TaxDeskError(str(e))
    st = _state(owner, ws)
    n = 1 + max([int(x.get("n") or 0) for x in st["letters"]] or [0])
    row = {"n": n, "name": str(name or "Tax letter")[:120], "added": _now(), "by": me, "text": text[:20000],
           "authority": r["authority"], "reference": r["reference"], "amount": r["amount"], "reply_by": r["reply_by"],
           "dates": r["dates_in_letter"], "asks": r["what_it_is"], "draft": r["reply_draft"], "state": "needs_you",
           "date_confirmed": False}
    if not r["reply_by"]:
        row["state"] = "read"
    st["letters"].insert(0, row)
    st["letters"] = st["letters"][:200]
    _put(owner, ws, st)
    return {"letter": _letter_out(row)}


def _letter_out(x: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in x.items() if k != "text"} | {"text_start": str(x.get("text") or "")[:600]}


def letter_act(owner: str, ws: str, n: int, act: str, me: str, a: dict[str, Any]) -> dict[str, Any]:
    st = _state(owner, ws)
    x = next((l for l in st["letters"] if int(l.get("n") or 0) == int(n)), None)
    if x is None:
        raise TaxDeskError("No such letter.")
    if act == "confirm_date":
        day = str(a.get("reply_by") or x.get("reply_by") or "")[:10]
        try:
            date.fromisoformat(day)
        except ValueError:
            raise TaxDeskError("reply_by: the date as YYYY-MM-DD, as written in the letter.")
        x["reply_by"], x["date_confirmed"] = day, True
        _engine(owner, me, "add_date", {"workspace": ws, "due": day,
                                        "title": f"Reply to {x['authority']} letter {x['reference']}".replace(" not found", "").strip()})
    elif act == "draft":
        x["draft"] = str(a.get("draft") or "")[:8000] or x["draft"]
    elif act == "sent":
        x["state"], x["sent_on"], x["sent_by"] = "sent", _now(), me
    elif act == "done":
        x["state"] = "done"
    elif act == "reopen":
        x["state"] = "needs_you"
    else:
        raise TaxDeskError("act: confirm_date | draft | sent | done | reopen")
    _put(owner, ws, st)
    return {"letter": _letter_out(x)}


def letter(owner: str, ws: str, n: int) -> dict[str, Any]:
    x = next((l for l in _state(owner, ws)["letters"] if int(l.get("n") or 0) == int(n)), None)
    if x is None:
        raise TaxDeskError("No such letter.")
    return {"letter": x}


def borders(owner: str, ws: str, period: str, me: str) -> dict[str, Any]:
    """US sales by state against her limits and the EU One Stop Shop for a period, each said with its checked state."""
    from .fin.desks import tax as T
    out: dict[str, Any] = {"period": period}
    chk = {(r["kind"], r["code"]): r["checked"] for r in rates_view(owner, ws)}
    try:
        nx = _engine(owner, me, "nexus", {"workspace": ws})
        for s in nx["states"]:
            s["limit_checked"] = chk.get(("nexus", s["state"]), False) if s.get("threshold") is not None else None
            if s.get("threshold"):
                s["pct"] = round(100 * float(s["sales_12m"]) / float(s["threshold"]), 1)
        out["nexus"] = nx
    except T.TaxError as e:
        out["nexus"] = {"error": str(e)}
    try:
        o = _engine(owner, me, "oss", {"workspace": ws, "period": period})
        for c in o["countries"]:
            c["rate_checked"] = chk.get(("oss_rates", c["country"]), False) if c.get("rate") is not None else None
        out["oss"] = o
    except T.TaxError as e:
        out["oss"] = {"error": str(e)}
    return out


def personal(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    from .fin.desks import tax as T
    st = _state(owner, ws)
    args = {"workspace": ws, **{k: v for k, v in a.items() if k in ("year", "bands", "allowance", "extra_income")}}
    try:
        r = _engine(owner, me, "organiser", args)
    except T.TaxError as e:
        return {"error": str(e), "papers": [{"name": p, "have": bool(st["papers"].get(p))} for p in T.PAPERS]}
    r["papers"] = [{"name": p, "have": bool(st["papers"].get(p))} for p in r.pop("papers_to_gather", T.PAPERS)]
    r["total_in"] = round(sum(float(v) for v in (r.get("income") or {}).values()), 2)
    return r


def tick_paper(owner: str, ws: str, name: str, have: bool) -> dict[str, Any]:
    from .fin.desks import tax as T
    if name not in T.PAPERS:
        raise TaxDeskError("No such paper on the list.")
    st = _state(owner, ws)
    if have:
        st["papers"][name] = True
    else:
        st["papers"].pop(name, None)
    _put(owner, ws, st)
    return {"name": name, "have": have}


def organiser_csv(owner: str, ws: str, me: str) -> tuple[str, bytes]:
    r = personal(owner, ws, {}, me)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Personal tax organiser", r.get("since", ""), r.get("upto", ""), r.get("currency", "")])
    w.writerow([])
    w.writerow(["Money in, from your statements", "Amount"])
    for k, v in (r.get("income") or {}).items():
        w.writerow([k, v])
    w.writerow([])
    w.writerow(["Costs that may matter", "Amount"])
    for k, v in (r.get("costs_that_may_matter") or {}).items():
        w.writerow([k, v])
    w.writerow([])
    w.writerow(["Papers for your accountant", "Have it"])
    for p in r.get("papers") or []:
        w.writerow([p["name"], "yes" if p["have"] else "missing"])
    w.writerow([])
    w.writerow([FOOT])
    return "tax-organiser.csv", buf.getvalue().encode("utf-8")


def return_csv(r: dict[str, Any]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([r.get("form", ""), r.get("since", ""), r.get("upto", ""), r.get("currency", "")])
    w.writerow(["Box", "What it is", "Amount"])
    for b in r.get("boxes") or []:
        w.writerow([b["box"], b["label"], b["amount"]])
    w.writerow([])
    w.writerow(["Number", "Kind", "Date", "Party"])
    for d in r.get("documents") or []:
        w.writerow([d["number"], d["kind"], d["issue"], d["party"]])
    w.writerow([])
    w.writerow([r.get("layout", "")])
    w.writerow([FOOT])
    return buf.getvalue().encode("utf-8")


def return_pdf(r: dict[str, Any], business: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    y = H - 22 * mm

    def line(txt: str, size: float = 10, bold: bool = False, x: float = 18 * mm, right: str | None = None):
        nonlocal y
        if y < 22 * mm:
            c.showPage()
            y = H - 22 * mm
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(x, y, str(txt)[:110])
        if right is not None:
            c.drawRightString(W - 18 * mm, y, str(right))
        y -= size * 1.6

    line(business, 14, True)
    line(f"{r.get('form', '')} · {r.get('since', '')} to {r.get('upto', '')} · {r.get('currency', '')}", 10)
    line("For filing by you or your accountant. Hoola does not file.", 9)
    y -= 6
    for b in r.get("boxes") or []:
        line(f"Box {b['box']}  {b['label']}", 10, False, right=f"{b['amount']:,.2f}" if isinstance(b["amount"], float) else str(b["amount"]))
    y -= 6
    line(f"To pay: {r.get('to_pay', 0):,.2f}    To reclaim: {r.get('to_reclaim', 0):,.2f}", 11, True)
    y -= 4
    for ck in r.get("checks") or []:
        line(("OK   " if ck["ok"] else "!    ") + ck["say"], 9)
    y -= 4
    line(str(r.get("layout", "")), 8)
    line(str(r.get("basis", "")), 8)
    line(FOOT, 8)
    c.save()
    return buf.getvalue()


def today_view(owner: str, ws: str, me: str) -> dict[str, Any]:
    from .fin.desks import tax as T
    tax = dict(_settings(owner, ws).get("tax") or {})
    st = _state(owner, ws)
    out: dict[str, Any] = {"set": bool(tax.get("country")), "tax": {k: v for k, v in tax.items() if k != "seller"}}
    out["period"] = current_period(tax)
    out["periods"] = periods(tax)
    items, seen = [], set()
    for year in (date.today().year, date.today().year + 1):     # this year and next: a January date added in November still shows
        try:
            for it in _engine(owner, me, "calendar", {"workspace": ws, "year": year})["items"]:
                key = (it.get("what"), it.get("due"))
                if key not in seen:
                    seen.add(key)
                    items.append(it)
        except T.TaxError as e:
            out["calendar_error"] = str(e)
            break
    items.sort(key=lambda x: (x.get("due") is None, x.get("due") or ""))
    for it in items:
        if it.get("period_end"):
            it["filed"] = any(st["filed"].get(p) for p in [_period_of(it["period_end"], tax)])
    today = date.today().isoformat()
    soon = [x for x in items if x.get("due") and x["due"] >= today and not x.get("filed")]
    out["overdue"] = [x for x in items if x.get("period_end") and x.get("due") and x["due"] < today and not x.get("filed")
                      and x["due"] >= (date.today() - timedelta(days=400)).isoformat()]
    out["dates"] = items
    out["next_due"] = soon[0] if soon else None
    out["coming_up"] = soon[:6]
    out["rates_to_check"] = unchecked(owner, ws)
    out["letters_waiting"] = [_letter_out(x) for x in st["letters"] if x.get("state") == "needs_you"]
    ret = prepare(owner, ws, out["period"], me) if out["set"] else {"blocked": True, "say": "Set your country first."}
    out["return"] = {k: ret.get(k) for k in ("period", "blocked", "say", "to_pay", "to_reclaim", "currency", "form", "filed",
                                             "warnings", "rates_to_check")}
    needs = []
    if not out["set"]:
        needs.append({"say": "Tell Hoola your country, tax number and return period", "go": "settings"})
    for x in out["overdue"]:
        needs.append({"say": f"Overdue since {x['due']}: {x['what']} - mark it filed if you already did", "go": "returns/" + _period_of(x["period_end"], tax)})
    for x in out["letters_waiting"]:
        needs.append({"say": f"{x['authority']} letter {x['reference']}" + (f" · reply by {x['reply_by']}" if x.get("reply_by") else ""),
                      "go": "letters", "n": x["n"]})
    if out["rates_to_check"]:
        needs.append({"say": f"{len(out['rates_to_check'])} rate(s) to check before they are used", "go": "settings"})
    if ret.get("warnings"):
        needs.append({"say": f"{len(ret['warnings'])} line(s) in the {out['period']} return to look at", "go": "returns"})
    if out["set"] and not ret.get("blocked") and not ret.get("filed"):
        needs.append({"say": f"The {out['period']} return is ready to check", "go": "returns"})
    out["needs"] = needs
    return out


def _period_of(end: str, cfg: dict[str, Any]) -> str:
    d = date.fromisoformat(end)
    kind = cfg.get("period_kind") or "quarterly"
    if kind == "monthly":
        return f"{d.year}-{d.month:02d}"
    if kind == "yearly":
        return str(d.year)
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


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
            return {"hired": False, "status": st, "say": "Tax is not hired. Hire it from AI Employees."}
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
            out["can_file"] = acc["role"] in FILE
            out["desk"] = today_view(acc["owner"], w["id"], f"{acc['name']} <{tenant}>")
        except Exception as e:   # noqa: BLE001
            log.exception("tax desk read failed")
            out["desk_error"] = str(e)[:200]
    return out


def do(caller: str, part: str, a: dict[str, Any]) -> dict[str, Any]:
    """Every desk action: her role on this business first, then the engine / the desk state on the OWNER's books."""
    from .fin.desks import books_ent as E
    from .fin.desks import tax as T
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    ws = str(a.get("workspace") or "")
    acc = E.access(caller, ws)
    role, owner = acc["role"], acc["owner"]
    me = f"{acc['name']} <{caller}>"
    reads = {"return", "borders", "rates", "letters", "letter", "personal", "withholding", "einvoice", "calendar", "codes", "quarterly",
             "sales_tax"}
    if part not in reads and role not in WRITE:
        raise TaxDeskError(f"Your role ({ROLE_SAY.get(role, role)}) can read this desk but not change it.")
    if part == "filed" and role not in FILE:
        raise TaxDeskError("Only the owner or an approver marks a return as filed.")
    try:
        if part == "return":
            out = prepare(owner, ws, str(a.get("period") or ""), me)
        elif part == "filed":
            out = mark_filed(owner, ws, str(a.get("period") or ""), str(a.get("reference") or ""), me)
        elif part == "borders":
            out = borders(owner, ws, str(a.get("period") or current_period(dict(_settings(owner, ws).get("tax") or {}))), me)
        elif part == "rates":
            out = {"rates": rates_view(owner, ws)}
        elif part == "check_rate":
            out = check_rate(owner, ws, str(a.get("kind") or ""), str(a.get("code") or ""), me)
        elif part == "set_rate":
            out = set_rate(owner, ws, str(a.get("kind") or ""), str(a.get("code") or ""), a.get("value"), me)
        elif part == "settings":
            keep = {k: v for k, v in a.items() if k in ("country", "scheme", "period_kind", "due_offset_days", "home_state", "seller")}
            out = _engine(owner, me, "settings", {"workspace": ws, **keep})
        elif part == "letters":
            out = {"letters": [_letter_out(x) for x in _state(owner, ws)["letters"]]}
        elif part == "letter":
            out = letter(owner, ws, int(a.get("n") or 0))
        elif part == "add_letter":
            out = add_letter(owner, ws, str(a.get("text") or ""), str(a.get("name") or ""), me)
        elif part == "letter_act":
            out = letter_act(owner, ws, int(a.get("n") or 0), str(a.get("act") or ""), me, a)
        elif part == "personal":
            out = personal(owner, ws, a, me)
        elif part == "paper":
            out = tick_paper(owner, ws, str(a.get("name") or ""), bool(a.get("have")))
        elif part == "add_date":
            out = _engine(owner, me, "add_date", {"workspace": ws, "due": a.get("due"), "title": a.get("title")})
        elif part in ("withholding", "einvoice", "calendar", "codes", "quarterly", "sales_tax"):
            out = _engine(owner, me, part, {**a, "workspace": ws})
        else:
            raise TaxDeskError("Not a Tax desk action.")
    except T.TaxError as e:
        raise TaxDeskError(str(e))
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


def greeting(tenant: str) -> str:
    d = summary(tenant)
    if not d.get("hired"):
        return "I prepare your tax figures. Hire me from AI Employees to start."
    if not d.get("workspace"):
        return "Hello. Set up your business in Books & Accounts first (name, country, currency), then tell me your tax details."
    k = d.get("desk") or {}
    if not k.get("set"):
        return "Hello. Tell me your country, your tax number and how often you file (monthly, quarterly or yearly), and I will set up your tax dates."
    needs = []
    if k.get("next_due"):
        needs.append(f"next due: {k['next_due']['what']} on {k['next_due']['due']}")
    if k.get("letters_waiting"):
        needs.append(f"{len(k['letters_waiting'])} letter(s) waiting")
    if k.get("rates_to_check"):
        needs.append(f"{len(k['rates_to_check'])} rate(s) to check")
    line = "Hello. " + ("Today: " + "; ".join(needs) + ". " if needs else "Nothing needs you right now. ")
    return line + "Ask about a return, a letter or selling abroad, or drop a tax letter here. I prepare the figures; you or your accountant file and pay."


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
        c = Conversation(tenant_id=tenant, kind=KIND, title="Tax chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False, delivered_to_agent=True))
    return {"id": cid, "new": True}


RULES = ("You are her Tax employee, talking in the desk's own chat (or a voice call started from it). Use the " + TOOL +
         " tool with workspace set to the business below: return (a VAT / GST return for a period, laid out like her country's form), "
         "sales_tax and nexus (US states), oss (EU One Stop Shop), withholding, einvoice, organiser (her personal tax papers), "
         "quarterly, notice (read a tax letter she gave), calendar, add_date, settings. Every figure you say comes from the tool - never "
         "estimate one. Rates and limits are hers: on this desk a rate is used only once a person checked it in Dates & settings; if a "
         "return is blocked by an unchecked rate, say which rate and send her there. A reply-by date read from a letter is a reminder only "
         "once she confirms it on the Letters page. You never file a return, pay tax or send a reply: filing and paying are hers or her "
         "accountant's, and \"I filed it\" is her tap with the reference. Never ask for or keep a password or a portal login. Plain "
         "English, short. Not tax advice. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<tax_desk>{RULES}Tax is not hired yet: tell her to hire it from AI Employees.</tax_desk>"
        elif not d.get("workspace"):
            txt = f"\n\n<tax_desk>{RULES}\nNo business set up yet: ask her to set it up in Books & Accounts.</tax_desk>"
        else:
            w, k = d["workspace"], d.get("desk") or {}
            t = k.get("tax") or {}
            r = k.get("return") or {}
            txt = (f"\n\n<tax_desk>{RULES}\nBusiness: {w['name']} (workspace {w['id']}), {', '.join(w['countries'])}. "
                   f"Tax country {t.get('country') or 'not set'}, scheme {t.get('scheme') or 'not set'}, period {t.get('period_kind') or 'quarterly'}."
                   f"\nReturn to prepare now: {k.get('period')}: "
                   + (r.get("say") or f"to pay {r.get('to_pay')} {r.get('currency')}, to reclaim {r.get('to_reclaim')}")
                   + (f" (filed, reference {r['filed']['reference']})" if r.get("filed") else "") + "."
                   f"\nNext due: {(k.get('next_due') or {}).get('what', 'none')} {(k.get('next_due') or {}).get('due', '')}."
                   f"\nLetters waiting: {'; '.join(x['authority'] + ' ' + x['reference'] + ' reply by ' + str(x.get('reply_by')) + ('' if x.get('date_confirmed') else ' (date not confirmed)') for x in k.get('letters_waiting') or []) or 'none'}."
                   f"\nRates to check: {', '.join(k.get('rates_to_check') or []) or 'none'}."
                   + (f"\nShe is the {d.get('role')} on this business (someone else owns it): explain from these figures and send her "
                      "to the desk for changes." if d.get("role") not in (None, "owner") else "")
                   + "</tax_desk>")
    except Exception:   # noqa: BLE001
        log.exception("tax block failed")
        txt = f"\n\n<tax_desk>{RULES}The desk could not be read just now.</tax_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/tax/chat", dependencies=dep)
    def tax_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/tax/chat/new", dependencies=dep)
    def tax_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/tax/chat/{conv}/ok", dependencies=dep)
    def tax_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Tax chat")
        return {"ok": True}

    @router.get("/api/tax/desk", dependencies=dep)
    def tax_desk(workspace: str = "", tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant, workspace)

    @router.post("/api/tax/do/{part}", dependencies=dep)
    def tax_do(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        from .fin import laws as L
        from .fin.desks.safety import SafetyError
        try:
            return do(tenant, part, body or {})
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (SafetyError, ValueError) as e:
            raise HTTPException(400, str(e))

    @router.get("/api/tax/download", dependencies=dep)
    def tax_download(workspace: str, what: str, period: str = "", tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response
        from .fin.desks import books_ent as E
        try:
            acc = E.access(tenant, workspace)
        except ValueError as e:
            raise HTTPException(404, str(e))
        me = f"{acc['name']} <{tenant}>"
        if what == "organiser":
            name, data = organiser_csv(acc["owner"], workspace, me)
            return Response(data, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})
        try:
            r = prepare(acc["owner"], workspace, period, me)
        except TaxDeskError as e:
            raise HTTPException(400, str(e))
        if r.get("blocked"):
            raise HTTPException(400, r.get("say") or "This return cannot be worked out yet.")
        biz = next((b["name"] for b in businesses(tenant) if b["id"] == workspace), "Business")
        if what == "csv":
            return Response(return_csv(r), media_type="text/csv",
                            headers={"Content-Disposition": f'attachment; filename="tax-return-{r["period"]}.csv"'})
        if what == "pdf":
            return Response(return_pdf(r, biz), media_type="application/pdf",
                            headers={"Content-Disposition": f'attachment; filename="tax-return-{r["period"]}.pdf"'})
        raise HTTPException(400, "what: pdf | csv | organiser")

    @router.put("/api/tax/workspace", dependencies=dep)
    def tax_workspace(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return pick(tenant, str((body or {}).get("workspace") or ""))
        except TaxDeskError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
