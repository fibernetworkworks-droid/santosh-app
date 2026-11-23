"""v0.999.169 PAYROLL DESK - the Payroll employee's own section, like Books & Accounts (owner: "WE WILL WORK ON NEXT AI EMPLOYEE SAME
WAY A PAYROLL" -> the design claude.ai/artifact/M5ukAtPfTjN89y7NzqT8pt -> "GO").

- The Payroll chat = a Conversation with kind 'payroll', kept out of every Hoola chat list (callconv.not_call); facts she tells it
  still reach her one memory. A turn in it (or a voice call started from it) gets the desk's state as a block and the payroll tool
  (`payroll_worldwide`, family payrollwide) in view.
- The desk's pages run the F5 engine + fin/desks/payroll_desk.py on the business she picked (a finance workspace, the same
  businesses as Books & Accounts). The Books & Accounts team works here too: accountant = preparer, approver approves, auditor and
  viewer read. Hoola never pays anyone and never files; a run is approved only by her tap on the hash of the run she saw.
"""
from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.payrollchat")

KIND = "payroll"
KEY = "payroll_worldwide"         # the Hub employee
TOOL = "payroll_worldwide"        # its tool
FAMILIES = ["payrollwide"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
SIZES = ("solo", "business", "firm", "institution")


class PayrollDeskError(ValueError):
    pass


def is_payroll(conv: str) -> bool:
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
        log.exception("payroll chat kind read failed")
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
        raise PayrollDeskError("No such business.")
    try:
        _hire().save_settings(tenant, KEY, workspace=ws)
    except Exception:   # noqa: BLE001
        pass
    forget(tenant)
    return {"workspace": ws}


def summary(tenant: str, want: str = "") -> dict[str, Any]:
    from .fin.desks import books_ent as E
    from .fin.desks import payroll_desk as PD
    h = _hire()
    st = h.status(tenant, KEY)
    trust = ""
    if st not in ("hired", "paused"):
        try:
            shared = E.shared_with(tenant)
        except Exception:   # noqa: BLE001
            shared = []
        if not shared:
            return {"hired": False, "status": st, "say": "Payroll is not hired. Hire it from AI Employees."}
    else:
        with session() as s:
            trust = h._view(h._row(s, tenant, KEY)).get("trust") or ""    # noqa: SLF001
    out: dict[str, Any] = {"hired": True, "status": st if st in ("hired", "paused") else "member",
                           "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
                           "businesses": businesses(tenant), "workspace": workspace(tenant, want), "roles": PD.ROLE_SAY}
    w = out["workspace"]
    if w:
        try:
            acc = E.access(tenant, w["id"])
            out["role"] = acc["role"]
            out["can"] = sorted(PD.CAN.get(acc["role"]) or set(PD.ACTIONS) | {"settings", "employee", "people", "payslip", "payments",
                                                                                "filings", "done", "contractors", "team"})
            out["desk"] = PD.desk(acc["owner"], w["id"])
        except Exception as e:   # noqa: BLE001
            log.exception("payroll desk read failed")
            out["desk_error"] = str(e)[:200]
    return out


def do(caller: str, part: str, a: dict[str, Any]) -> dict[str, Any]:
    """Every desk action: her role on this business first, then the engine on the OWNER's payroll with her name as the actor."""
    from .fin.desks import books_ent as E
    from .fin.desks import payroll as PY
    from .fin.desks import payroll_desk as PD
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    ws = str(a.get("workspace") or "")
    acc = E.access(caller, ws)
    role, owner = acc["role"], acc["owner"]
    if part == "team":
        return {"team": E.team(owner, ws), "you": role}
    if not PD.allowed(role, part):
        raise E.EntError(f"Your role ({PD.ROLE_SAY.get(role, role)}) cannot do this on this payroll.")
    me = f"{acc['name']} <{caller}>"
    if part == "upload":
        try:
            data = base64.b64decode(str(a.get("data_b64") or ""), validate=True)
        except Exception:   # noqa: BLE001
            raise PD.PayrollError("The file did not arrive.")
        out = PD.take_file(owner, ws, str(a.get("name") or "file.csv"), data, "", "upload", me)
    else:
        from .fin import core
        seen = {k: v for k, v in a.items() if k not in ("accounts", "from")}   # account numbers never reach the audit log
        out = core.run_tool(owner, me, "payroll_worldwide", part, seen, lambda: PY.run(owner, part, a, me))
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
        return "I run your payroll. Hire me from AI Employees to start."
    if not d.get("workspace"):
        return "Hello. Set up your business first (name, country, currency) on the desk, then add your people."
    k = d.get("desk") or {}
    needs = []
    if not k.get("rules_set"):
        needs.append("your country's pay rules are not set")
    if k.get("rules_to_check"):
        needs.append(f"{len(k['rules_to_check'])} rule(s) to check")
    if k.get("missing"):
        needs.append(f"hours missing for {len(k['missing'])}")
    if (k.get("inputs") or {}).get("waiting"):
        needs.append(f"{k['inputs']['waiting']} input(s) waiting")
    line = f"Hello. Pay period {k.get('period', '')}, pay day {k.get('pay_day', '')}. "
    line += ("Today: " + "; ".join(needs) + ". ") if needs else "Nothing needs you right now. "
    return line + "Ask about pay, people or dates, or drop a timesheet here. I never pay anyone or file anything."


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
        c = Conversation(tenant_id=tenant, kind=KIND, title="Payroll chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False, delivered_to_agent=True))
    return {"id": cid, "new": True}


RULES = ("You are her Payroll employee, talking in the desk's own chat (or a voice call started from it). Use the " + TOOL +
         " tool with workspace set to the business below: desk, people, inputs, missing, changes, rules, filings, payslip, payments "
         "to read; employee adds or changes a person; input_rows puts the rows of a timesheet she gave (each row is checked); "
         "prepare works out the period's payroll as a draft. Every figure you say comes from the tool - never estimate one. Her pay "
         "rules are hers: a country's starting rule is used only after a person checked it on the desk. You never approve a payroll, "
         "pay anyone, send payslips or file a return: approving, the payment file and payslip emails are her taps on the Payroll "
         "desk, filing is hers. Never ask for or keep a bank account number. Plain English, short. Not payroll or employment advice. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<payroll_desk>{RULES}Payroll is not hired yet: tell her to hire it from AI Employees.</payroll_desk>"
        elif not d.get("workspace"):
            txt = f"\n\n<payroll_desk>{RULES}\nNo business set up yet: ask her to set it up on the desk (Settings).</payroll_desk>"
        else:
            w, k = d["workspace"], d.get("desk") or {}
            run = k.get("run") or {}
            t = run.get("totals") or {}
            txt = (f"\n\n<payroll_desk>{RULES}\nBusiness: {w['name']} (workspace {w['id']}), {', '.join(w['countries'])}, pay in "
                   f"{k.get('currency')}. Payroll country {k.get('country') or 'not set'}, {k.get('frequency')}."
                   f"\nThis period {k.get('period')} ({k.get('start')} to {k.get('end')}), pay day {k.get('pay_day')}, {k.get('people')} people."
                   f"\nRun: {run.get('status')}" + (f", net {t.get('net')}, cost {t.get('cost')}" if t else "") + "."
                   f"\nInputs this period: {k.get('inputs') or {}}. Hours missing for: {', '.join(x['name'] for x in k.get('missing') or []) or 'nobody'}."
                   f"\nRules to check: {', '.join(k.get('rules_to_check') or []) or 'none'}. "
                   + ("Pay rules are not set yet: she sets them in Payroll > Settings (a country starting list or her own). " if not k.get("rules_set") else "")
                   + f"Filings due soon: {'; '.join(f['filing'] + ' ' + f['due'] for f in k.get('filings_soon') or []) or 'none'}."
                   + "\nPay inputs come in by themselves from her sheet, her payroll email, her time / HR software and her own system "
                     "(Payroll > Inputs): never ask her to type in hours that will come in by themselves."
                   + (f"\nShe is the {d.get('role')} on this business (someone else owns it): explain from these figures and send her "
                      "to the desk for changes." if d.get("role") not in (None, "owner") else "")
                   + "</payroll_desk>")
    except Exception:   # noqa: BLE001
        log.exception("payroll block failed")
        txt = f"\n\n<payroll_desk>{RULES}The desk could not be read just now.</payroll_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/payroll/chat", dependencies=dep)
    def payroll_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/payroll/chat/new", dependencies=dep)
    def payroll_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/payroll/chat/{conv}/ok", dependencies=dep)
    def payroll_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Payroll chat")
        return {"ok": True}

    @router.get("/api/payroll/desk", dependencies=dep)
    def payroll_desk(workspace: str = "", tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant, workspace)

    @router.post("/api/payroll/do/{part}", dependencies=dep)
    def payroll_do(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        from .fin import laws as L
        from .fin.desks.safety import SafetyError
        try:
            return do(tenant, part, body or {})
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (SafetyError, ValueError) as e:
            raise HTTPException(400, str(e))

    @router.get("/api/payroll/payslip", dependencies=dep)
    def payroll_payslip(workspace: str, period: str, employee: str, tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response
        from .fin.desks import books_ent as E
        from .fin.desks import payroll_desk as PD
        acc = E.access(tenant, workspace)
        if not PD.allowed(acc["role"], "payslip_pdf"):
            raise HTTPException(403, "Your role cannot open payslips.")
        try:
            name, data, _ = PD.payslip_pdf(acc["owner"], workspace, period, employee)
        except PD.PayrollError as e:
            raise HTTPException(404, str(e))
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @router.post("/api/payroll/in")
    async def payroll_in(request: Request):
        """Her own system sends pay inputs here (Authorization: Bearer <her payroll key>): {period?, rows: [...]}."""
        from .fin.desks import payroll_desk as PD
        tok = str(request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        hit = PD.ws_of_key(tok)
        if not hit:
            raise HTTPException(401, "Not a payroll key")
        raw = await request.body()
        if len(raw) > 5 * 1024 * 1024:
            raise HTTPException(413, "Too big")
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            raise HTTPException(400, "Send JSON")
        if not isinstance(body, dict) or not isinstance(body.get("rows"), list):
            raise HTTPException(400, "Send {period, rows: [{name, hours, ...}]}")
        try:
            out = PD.take_rows(hit[0], hit[1], body["rows"], "api", str(body.get("period") or ""), str(body.get("ref") or "api"),
                               "Your system")
        except PD.PayrollError as e:
            raise HTTPException(400, str(e))
        forget(hit[0])
        return out

    @router.put("/api/payroll/workspace", dependencies=dep)
    def payroll_workspace(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return pick(tenant, str((body or {}).get("workspace") or ""))
        except PayrollDeskError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
