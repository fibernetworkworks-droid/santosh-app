"""v0.999.158 BOOKS DESK - the Books & Accounts employee's own section, like the business desks (owner: "NOW LETS WORK ON BOOKS
AND ACCOUNT --- FIRST CHECK WANT IT HAS AND THEN A NEW DESIGN HERE" -> the design claude.ai/artifact/VZnFUmr3C1KtjrK3ESRnk3
-> "GO").

- The Books & Accounts chat = a Conversation with kind 'books', kept out of every Hoola chat list (callconv.not_call); facts
  she tells it still reach her one memory.
- A turn in it (or in a voice call started from it) gets the desk's state as a block (`block`) and the books tool
  (`books_accounts`, family books) in view.
- The desk's pages call the F3 engine (fin/desks/books.py through /api/fin/books/*) on the business she picked here (a finance
  workspace; she sets one up on the desk with the F0 setup and its hash). Every number comes from her books. Hoola never sends
  an invoice, pays a bill or files a return; a month locks only on her confirm of the checklist she saw.
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.bookschat")

KIND = "books"
KEY = "books_accounts"          # the Hub employee
TOOL = "books_accounts"         # its tool (same name)
FAMILIES = ["books"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
SIZES = ("solo", "business", "firm", "institution")     # the sizes Books & Accounts serves


class BooksDeskError(ValueError):
    pass


def is_books(conv: str) -> bool:
    """True for the Books & Accounts chat, and for a voice call started from it (the call record's origin)."""
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
        log.exception("books chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


# ---------------------------------------------------------------- the business these books belong to
def _hire():
    from .employee import hire
    return hire


def businesses(tenant: str) -> list[dict[str, Any]]:
    from .fin import profile as PR
    return [{"id": w["id"], "name": w["name"] or "My business", "size": w["size"], "currency": w["currency"],
             "countries": w["countries"]} for w in PR.workspaces(tenant) if w["size"] in SIZES]


def workspace(tenant: str) -> dict[str, Any] | None:
    """The business she picked on this desk, else her first business workspace."""
    bs = businesses(tenant)
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
        raise BooksDeskError("No such business.")
    _hire().save_settings(tenant, KEY, workspace=ws)
    forget(tenant)
    return {"workspace": ws}


def _last_month(today: date) -> str:
    return (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")


def numbers(tenant: str, ws: str) -> dict[str, Any]:
    """Today's figures, all from her books: bank, owed to her, she owes, this month's profit, and what needs her."""
    from .fin.desks import books as BK
    t = date.today()
    out: dict[str, Any] = {}
    BK.ensure_coa(tenant, ws)
    bal = BK.balances(tenant, ws, upto=t.isoformat())
    w = BK._ws(tenant, ws)                                   # noqa: SLF001
    cur = BK._book_cur(w)                                    # noqa: SLF001
    out["currency"] = cur
    out["bank"] = BK._u(bal.get("1000", 0), cur)              # noqa: SLF001
    ar = BK.ageing(tenant, ws, "sales", t.isoformat())
    ap = BK.ageing(tenant, ws, "purchase", t.isoformat())
    late = lambda b: round(sum(v for k, v in b["buckets"].items() if k != "not_due"), 2)   # noqa: E731
    out["owed_to_you"], out["overdue_to_you"] = ar["total"], late(ar)
    out["you_owe"], out["overdue_you_owe"] = ap["total"], late(ap)
    p = BK.reports(tenant, ws, t.replace(day=1).isoformat(), t.isoformat())["profit_and_loss"]
    out["month"] = {"income": p["income"], "expenses": p["expenses"], "profit": p["profit"], "from": p["from"]}
    m = BK.propose_matches(tenant, ws)["lines"]
    out["bank_to_confirm"] = len(m)
    out["bank_sure"] = sum(1 for x in m if x.get("sure"))
    docs = BK.docs(tenant, ws)
    out["drafts"] = sum(1 for d in docs if d["status"] == "draft")
    out["overdue_docs"] = [{"id": d["id"], "number": d["number"], "party": d["party"], "open": d["open"], "currency": d["currency"],
                            "due": d["due"], "days": (t - date.fromisoformat(d["due"])).days}
                           for d in docs if d["kind"] == "sales" and d["status"] == "open" and d["due"] < t.isoformat()]
    lm = _last_month(t)
    try:
        ck = BK.close_checklist(tenant, ws, lm)
        out["close"] = {"period": lm, "locked": ck["locked"], "ready": ck["ready"],
                        "done": sum(1 for i in ck["items"] if i["ok"]), "of": len(ck["items"])}
    except Exception:   # noqa: BLE001
        out["close"] = {"period": lm, "locked": False, "ready": False, "done": 0, "of": 0}
    return out


def summary(tenant: str) -> dict[str, Any]:
    h = _hire()
    st = h.status(tenant, KEY)
    if st not in ("hired", "paused"):
        return {"hired": False, "status": st, "say": "Books & Accounts is not hired. Hire it from AI Employees."}
    with session() as s:
        trust = h._view(h._row(s, tenant, KEY)).get("trust") or ""    # noqa: SLF001
    out: dict[str, Any] = {"hired": True, "status": st,
                           "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
                           "businesses": businesses(tenant), "workspace": workspace(tenant)}
    if out["workspace"]:
        try:
            out["numbers"] = numbers(tenant, out["workspace"]["id"])
        except Exception as e:   # noqa: BLE001
            log.exception("books numbers failed")
            out["numbers_error"] = str(e)[:200]
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
        return "I keep your business books. Hire me from AI Employees to start."
    if not d.get("workspace"):
        return ("Hello. Set up your business on the desk (name, country, currency) and I will start your books. "
                "Then drop in a bank statement, a bill or a receipt.")
    n = d.get("numbers") or {}
    needs = []
    if n.get("bank_to_confirm"):
        needs.append(f"{n['bank_to_confirm']} bank line{'s' if n['bank_to_confirm'] > 1 else ''} to confirm")
    if n.get("overdue_docs"):
        k = len(n["overdue_docs"])
        needs.append(f"{k} invoice{'s' if k > 1 else ''} overdue")
    if n.get("drafts"):
        needs.append(f"{n['drafts']} draft{'s' if n['drafts'] > 1 else ''} to check")
    line = "Hello. " + ("Today: " + "; ".join(needs) + ". " if needs else "Your books need nothing right now. ")
    return line + "Ask about your figures, or drop a bill, a receipt or a statement here. I never send, pay or file anything."


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:          # her newest untouched Books chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Books & Accounts chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False,
                      delivered_to_agent=True))
    return {"id": cid, "new": True}


# ---------------------------------------------------------------- what a turn in the Books chat knows
RULES = ("You are her Books & Accounts employee, talking in the desk's own chat (or a voice call started from it). "
         "Use the " + TOOL + " tool with workspace set to the business below: documents, matches, ageing, reports, close_check "
         "to read; invoice and bill make DRAFTS; issue posts a draft (only when she asks); receipt reads a receipt's text into a "
         "draft bill; apply_match / post_bank only after she confirms that line; close_lock only with the hash of the checklist "
         "she saw. Every figure you say comes from the tool - never estimate or invent one. Her tax rate is hers; a country's "
         "rate is shown, never used, until checked. You never send an invoice, pay a bill or file a return: she does. "
         "Plain English, short. This is help with her books, not tax or legal advice. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<books_desk>{RULES}Books & Accounts is not hired yet: tell her to hire it from AI Employees.</books_desk>"
        elif not d.get("workspace"):
            txt = f"\n\n<books_desk>{RULES}\nNo business set up yet: ask her to set it up on the desk (Settings).</books_desk>"
        else:
            w, n = d["workspace"], d.get("numbers") or {}
            cur = n.get("currency", w["currency"])
            od = "; ".join(f"{x['number']} {x['party']} {x['open']} {x['currency']}, {x['days']} days late" for x in n.get("overdue_docs", [])[:8])
            txt = (f"\n\n<books_desk>{RULES}\nBusiness: {w['name']} (workspace {w['id']}), {', '.join(w['countries'])}, books in {cur}."
                   f"\nBank {n.get('bank')}; customers owe {n.get('owed_to_you')} ({n.get('overdue_to_you')} overdue); "
                   f"she owes {n.get('you_owe')}; profit this month {(n.get('month') or {}).get('profit')}."
                   f"\nBank lines to confirm: {n.get('bank_to_confirm', 0)}. Drafts: {n.get('drafts', 0)}. Overdue: {od or 'none'}."
                   f"\nLast month {(n.get('close') or {}).get('period')}: "
                   f"{'locked' if (n.get('close') or {}).get('locked') else str((n.get('close') or {}).get('done')) + ' of ' + str((n.get('close') or {}).get('of')) + ' checks done'}."
                   f"</books_desk>")
    except Exception:   # noqa: BLE001
        log.exception("books block failed")
        txt = f"\n\n<books_desk>{RULES}The desk could not be read just now.</books_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/books/chat", dependencies=dep)
    def books_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/books/chat/new", dependencies=dep)
    def books_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/books/chat/{conv}/ok", dependencies=dep)
    def books_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Books & Accounts chat")
        return {"ok": True}

    @router.get("/api/books/desk", dependencies=dep)
    def books_desk(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant)

    @router.put("/api/books/workspace", dependencies=dep)
    def books_workspace(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return pick(tenant, str((body or {}).get("workspace") or ""))
        except BooksDeskError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
