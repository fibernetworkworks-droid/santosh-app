"""v0.999.43 ACCOUNTS DESK - the GST & Accounts employee's own tool (its chat, a call started from it, any chat of hers).

Before this the GST & Accounts employee had a desk but no tool: a chat could talk about GST and change nothing, and a bill
she attached in a chat never reached the desk. `accounts_desk` reads the register / dues / drafts, reads a bill she
attached (photo, PDF, text) into a DRAFT with its checks, fixes a draft's figures, imports a bank statement she attached,
proposes bank matches, prepares GSTR-1 / GSTR-3B drafts INSIDE Hoola and works out a TDS worksheet. It NEVER adds a bill to
the register, sends credit decisions or a return to the GST portal, files, records TDS, locks / closes a month or moves
money: those stay her taps on the desk (filing also needs her OTP; the house gate: a 'yes' in words never files - v0.999.12).
"""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from .tools import Ctx, ToolError

ACCOUNTSDESK_TOOLS = [
    {"name": "accounts_desk", "description": (
        "HER GST & Accounts desk (one register of every sale and purchase bill, GST dates, credits, returns, bank, TDS) - only "
        "when she has hired the GST & Accounts employee. action=read: what=summary (dues with days left, this / last month's "
        "figures, her GSTINs, what waits for her) | register (period YYYY-MM, direction in|out, q) | bills (bill drafts "
        "waiting for her check, with ids and checks) | bank (bank lines; status open|proposed|matched) | credits (the "
        "proposed 2B credit decisions for gstin + period, each with its reason) | owed (who owes her, by age) | payables (what "
        "she owes, MSME 45-day watch). action=read_bill: file_id of a bill photo / PDF she attached (or text) -> read into a "
        "DRAFT with checks (GSTIN active, taxable + tax = total, rate slab, duplicate); it is NOT in the register. "
        "action=fix_bill: bill_id + changes {supplier_gstin, party_name, number, date, taxable, cgst, sgst, igst, cess, total} "
        "-> changes the draft and runs the checks again. action=import_statement: file_id of a bank statement (CSV / Excel / "
        "MT940 / PDF) + account label -> bank lines. action=match_bank: month -> proposes matches (nothing linked). "
        "action=prepare: form gstr1|gstr3b, gstin, period -> the return drafted inside Hoola with its checks (nothing sent). "
        "action=tds: party_id, nature, amount, paid_on -> the TDS worksheet (nothing recorded). action=supplier: gstin -> is "
        "this supplier's GSTIN active and filing. It cannot add a bill to the register, send to the GST portal, file, record "
        "TDS, close a month or pay: tell her to tap it on her Accounts desk. Never ask for her portal password or an OTP."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["read", "read_bill", "fix_bill", "import_statement", "match_bank", "prepare", "tds", "supplier"]},
         "what": {"type": "string", "enum": ["summary", "register", "bills", "bank", "credits", "owed", "payables"]},
         "file_id": {"type": "string"}, "text": {"type": "string"}, "bill_id": {"type": "string"},
         "changes": {"type": "object"}, "gstin": {"type": "string"}, "period": {"type": "string"}, "month": {"type": "string"},
         "direction": {"type": "string", "enum": ["in", "out"]}, "q": {"type": "string"}, "status": {"type": "string"},
         "account": {"type": "string"}, "form": {"type": "string", "enum": ["gstr1", "gstr3b"]},
         "party_id": {"type": "string"}, "nature": {"type": "string"}, "amount": {"type": "number"}, "paid_on": {"type": "string"}},
         "required": ["action"]}},
]
ACCOUNTSDESK_LABELS = {"accounts_desk": "Working on your accounts desk"}

KEY = "accounts"
CHANGES = ("read_bill", "fix_bill", "import_statement", "match_bank", "prepare")


def _cut(v: Any, n: int = 30) -> Any:
    return v[:n] if isinstance(v, list) else v


def _gstins(tenant: str) -> list[str]:
    from ..bahi import connect as CN
    out = []
    try:
        for c in CN.status(tenant):
            g = str(c.get("gstin") or "")
            if g and g not in out:
                out.append(g)
    except Exception:   # noqa: BLE001
        pass
    return out


def summary(tenant: str) -> dict[str, Any]:
    from ..bahi import bank as BK
    from ..bahi import intake as IN
    from ..bahi import service as SV
    from ..employee import hire
    st = hire.status(tenant, KEY)
    if st not in ("hired", "paused"):
        return {"hired": False, "say": "The GST & Accounts employee is not hired. She can hire it from AI Employees."}
    o = SV.overview(tenant)
    try:
        bills = IN.listing(tenant, "draft")
    except Exception:   # noqa: BLE001
        bills = []
    try:
        prop = len(BK.lines(tenant, "proposed"))
    except Exception:   # noqa: BLE001
        prop = 0
    trust = ""
    try:
        from ..db import session as _s
        with _s() as s:
            trust = (hire._view(hire._row(s, tenant, KEY)).get("trust") or "")
    except Exception:   # noqa: BLE001
        pass
    return {"hired": True, "status": st, "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, trust or "Learning"), "scheme": o.get("scheme"), "period": o.get("period"),
            "prev_period": o.get("prev_period"), "gstins": _gstins(tenant),
            "this_month": o.get("this_month"), "last_month": o.get("last_month"),
            "dues": [{"what": d.get("what"), "name": _short(d.get("what")), "date": d.get("date"), "days_left": d.get("days_left"),
                      "unconfirmed": d.get("basis") == "unverified"} for d in o.get("dues") or []],
            "bills_to_check": len(bills), "bank_to_confirm": prop,
            "recent": [f"{str(e.get('at', ''))[:10]} {e.get('what', '')} {e.get('label') or e.get('ref', '')}" for e in (o.get("events") or [])[:6]],
            "filing_on": bool(o.get("filing"))}


def _short(what: Any) -> str:
    """'GSTR-3B + tax payment (monthly filers). Its sales figures are...' -> 'GSTR-3B + tax payment'."""
    import re
    s = re.split(r"[.;(]", str(what or ""), maxsplit=1)[0].strip(" -,")
    return s[:60] or str(what or "")[:60]


def _her_gstin(tenant: str, given: str) -> str:
    g = str(given or "").strip().upper()
    if g:
        return g
    gs = _gstins(tenant)
    if len(gs) == 1:
        return gs[0]
    if not gs:
        raise ToolError("No GSTIN is connected yet. Ask her which GSTIN this is for, or to connect it in the desk's Settings.")
    raise ToolError("She has more than one GSTIN (" + ", ".join(gs) + "): ask which one, then pass gstin.")


def _prev_period() -> str:
    t = date.today()
    y, m = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
    return f"{y:04d}-{m:02d}"


def _do(ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    from ..employee import hire
    t = ctx.tenant_id
    if hire.status(t, KEY) not in ("hired", "paused"):
        raise ToolError("The GST & Accounts employee is not hired. She can hire it from AI Employees.")
    act = str(a.get("action") or "")
    if act in CHANGES and ctx.actor not in ("owner",) and not str(ctx.actor).startswith("approved:"):
        raise ToolError("Only the owner can change the Accounts desk.")
    from ..bahi import bank as BK
    from ..bahi import connect as CN
    from ..bahi import gstr1 as G1
    from ..bahi import gstr3b as G3
    from ..bahi import intake as IN
    from ..bahi import itc as IT
    from ..bahi import payables as PY
    from ..bahi import register as REG
    errs = tuple(e for e in (getattr(BK, "BankError", None), getattr(CN, "ConnectError", None), getattr(G1, "Gstr1Error", None),
                             getattr(G3, "Gstr3bError", None), getattr(IN, "IntakeError", None), getattr(IT, "ItcError", None),
                             getattr(PY, "PayError", None), getattr(REG, "RegisterError", None)) if e)
    try:
        if act == "read":
            what = str(a.get("what") or "summary")
            if what == "register":
                rows = REG.listing(t, period=str(a.get("period") or ""), direction=str(a.get("direction") or ""), source="",
                                   q=str(a.get("q") or ""), limit=60)
                return {"rows": rows[:60], "shown": len(rows[:60])}
            if what == "bills":
                return {"bills": _cut(IN.listing(t, "draft"))}
            if what == "bank":
                return {"lines": _cut(BK.lines(t, str(a.get("status") or ""), str(a.get("month") or "")), 40)}
            if what == "credits":
                return IT.propose(t, _her_gstin(t, a.get("gstin")), str(a.get("period") or _prev_period()))
            if what == "owed":
                return PY.ageing(t, "out")
            if what == "payables":
                return {"ageing": PY.ageing(t, "in"), "msme": PY.msme_watch(t)}
            return summary(t)
        if act == "read_bill":
            g = _her_gstin(t, a.get("gstin"))
            if a.get("file_id"):
                r = IN.intake_file(t, g, str(a["file_id"]), channel="chat")
            elif str(a.get("text") or "").strip():
                r = IN.intake_text(t, g, str(a["text"]), channel="chat")
            else:
                raise ToolError("Give the file_id of the bill she attached, or the bill's text.")
            return {**r, "note": "Read into a DRAFT - it is NOT in the register. She taps Add to register on the Accounts desk."}
        if act == "fix_bill":
            ch = a.get("changes") if isinstance(a.get("changes"), dict) else {}
            r = IN.fix_draft(t, str(a.get("bill_id") or ""), ch)
            return {**r, "note": "Changed on the draft only. It goes into the register when she taps Add to register."}
        if act == "import_statement":
            if not a.get("file_id"):
                raise ToolError("Give the file_id of the statement she attached.")
            r = BK.import_file(t, str(a.get("account") or "bank")[:40], str(a["file_id"]), "")
            return {**r, "note": "Lines stored. Run match_bank to propose matches; nothing is linked until she confirms."}
        if act == "match_bank":
            r = BK.match(t, str(a.get("month") or ""))
            return {**r, "note": "Proposed only. She confirms each match on the desk (Bank & payments)."}
        if act == "prepare":
            form = str(a.get("form") or "")
            g, per = _her_gstin(t, a.get("gstin")), str(a.get("period") or _prev_period())
            if form == "gstr1":
                r = G1.prepare(t, g, per)
            elif form == "gstr3b":
                r = G3.prepare(t, g, per)
            else:
                raise ToolError("form: gstr1 | gstr3b")
            r = {k: v for k, v in r.items() if k not in ("json", "payload", "return")}
            return {**r, "note": "Drafted inside Hoola only. Nothing was saved to the GST portal or filed - those are her taps."}
        if act == "tds":
            return {**PY.worksheet(t, str(a.get("party_id") or ""), str(a.get("nature") or ""), float(a.get("amount") or 0),
                                   str(a.get("paid_on") or date.today().isoformat())),
                    "note": "A worksheet only. It is recorded when she taps Record on the desk."}
        if act == "supplier":
            return CN.supplier_check(t, str(a.get("gstin") or ""), filing=True)
    except ToolError:
        raise
    except errs as e:
        raise ToolError(str(e)) from e
    raise ToolError("action: read | read_bill | fix_bill | import_statement | match_bank | prepare | tds | supplier")


async def accounts_desk(ctx: Ctx, **args: Any) -> dict[str, Any]:
    out = await asyncio.to_thread(_do, ctx, dict(args))
    try:
        from .. import accountschat
        accountschat.forget(ctx.tenant_id)
    except Exception:   # noqa: BLE001
        pass
    return out


ACCOUNTSDESK_HANDLERS = {"accounts_desk": accounts_desk}
