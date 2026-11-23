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

import json
import logging
import re
import time
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
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
    """Her own businesses (she is the owner) and, v0.999.159, the ones other people put her on with a role."""
    from .fin import profile as PR
    from .fin.desks import books_ent as E
    own = [{"id": w["id"], "name": w["name"] or "My business", "size": w["size"], "currency": w["currency"],
            "countries": w["countries"], "role": "owner"} for w in PR.workspaces(tenant) if w["size"] in SIZES]
    try:
        return own + E.shared_with(tenant)
    except Exception:   # noqa: BLE001
        log.exception("shared books read failed")
        return own


def workspace(tenant: str, want: str = "") -> dict[str, Any] | None:
    """The business asked for (if she may open it), else the one she picked on this desk, else her first."""
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
        raise BooksDeskError("No such business.")
    try:
        _hire().save_settings(tenant, KEY, workspace=ws)
    except Exception:   # noqa: BLE001  a team member who never hired the employee: the page keeps the pick itself
        pass
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
    pm = BK.propose_matches(tenant, ws)
    m = pm["lines"]
    out["bank_to_confirm"] = pm["total"]
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
    try:                                     # v0.999.163 the books inbox
        from .fin.desks import books_feed as F
        cnt = F.listing(tenant, ws, limit=0)["counts"]
        out["inbox_on"] = bool(F.settings(tenant, ws).get("on"))
        out["inbox_needs"] = cnt.get("draft", 0) + cnt.get("failed", 0)
        out["inbox_posted"] = cnt.get("posted", 0)
    except Exception:   # noqa: BLE001
        out["inbox_on"], out["inbox_needs"] = False, 0
    return out


def summary(tenant: str, want: str = "") -> dict[str, Any]:
    from .fin.desks import books_ent as E
    h = _hire()
    st = h.status(tenant, KEY)
    shared = []
    if st not in ("hired", "paused"):
        try:
            shared = E.shared_with(tenant)
        except Exception:   # noqa: BLE001
            shared = []
        if not shared:          # a person put on someone's books opens them without hiring anything
            return {"hired": False, "status": st, "say": "Books & Accounts is not hired. Hire it from AI Employees."}
        trust = ""
    else:
        with session() as s:
            trust = h._view(h._row(s, tenant, KEY)).get("trust") or ""    # noqa: SLF001
    out: dict[str, Any] = {"hired": True, "status": st if st in ("hired", "paused") else "member",
                           "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
                           "businesses": businesses(tenant), "workspace": workspace(tenant, want), "roles": E.ROLE_NAMES}
    w = out["workspace"]
    if w:
        try:
            acc = E.access(tenant, w["id"])
            out["role"] = acc["role"]
            out["can"] = sorted(E.CAN.get(acc["role"], set()))
            c = E.controls(acc["owner"], w["id"])
            out["controls"] = {"on": bool(c.get("on")), "limit": c.get("limit") or 0, "dual": c.get("dual"),
                               "cost_centres": c.get("cost_centres") or []}
            out["pending"] = len(E.requests(acc["owner"], w["id"]))
            out["numbers"] = numbers(acc["owner"], w["id"])
        except Exception as e:   # noqa: BLE001
            log.exception("books numbers failed")
            out["numbers_error"] = str(e)[:200]
    return out


def do(caller: str, part: str, a: dict[str, Any]) -> dict[str, Any]:
    """Every desk action: who she is on this business, whether her role may do it, then the engine (whose own gate sends a
    posting to a second person when the controls are on). The engine runs on the OWNER's books with her name as the actor."""
    from .fin.desks import books as BK
    from .fin.desks import books_ent as E
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    ws = str(a.get("workspace") or "")
    acc = E.access(caller, ws)
    role, owner = acc["role"], acc["owner"]
    if not E.allowed(role, part):
        raise E.EntError(f"Your role ({E.ROLE_NAMES.get(role, role)}) cannot do this on these books.")
    me = f"{acc['name']} <{caller}>"
    if part == "requests":
        return {"requests": E.requests(owner, ws, str(a.get("status") if "status" in a else "pending"))}
    if part == "approve":
        return E.approve(owner, ws, str(a.get("request") or ""), caller, acc["name"])
    if part == "reject":
        return E.reject(owner, ws, str(a.get("request") or ""), caller, acc["name"], str(a.get("reason") or ""))
    if part == "team":
        return {"team": E.team(owner, ws), "you": role}
    if part == "team_add":
        if str(a.get("role")) == "admin" and role != "owner":
            raise E.EntError("Only the owner adds an admin.")
        return E.team_add(owner, ws, str(a.get("email") or ""), str(a.get("role") or ""), str(a.get("name") or ""), me)
    if part == "team_remove":
        return E.team_remove(owner, ws, str(a.get("member") or ""), me)
    if part == "controls_read":
        return E.controls(owner, ws)
    if part == "controls":
        return E.set_controls(owner, ws, a, me)
    if part == "by_cost_centre":
        return E.by_cost_centre(owner, ws, str(a.get("since") or "0000-01-01"), str(a.get("upto") or date.today()))
    if part == "consolidate":
        return E.consolidate(caller, a.get("businesses") or [], str(a.get("currency") or ""), a.get("rates") or {},
                             str(a.get("since") or "0000-01-01"), str(a.get("upto") or date.today()))
    if part.startswith("inbox"):
        return _inbox(owner, ws, part, a, me)
    from .fin import core
    out = core.run_tool(owner, me, "books_accounts", part, a, lambda: BK.run(owner, part, a, me))
    forget(owner)
    forget(caller)
    return out


def _inbox(owner: str, ws: str, part: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    """v0.999.163 the books inbox: invoices and bills that came in by themselves (mail, programs, her shop)."""
    import asyncio
    from .fin.desks import books_feed as F
    if not ws:
        raise F.FeedError("workspace: which business.")
    if part == "inbox":
        return F.listing(owner, ws, str(a.get("status") or ""))
    if part == "inbox_settings":
        return F.set_settings(owner, ws, a)
    if part == "inbox_key":
        return F.new_api_key(owner, ws)
    if part == "inbox_key_stop":
        return F.stop_api(owner, ws)
    if part == "inbox_mail_attach":
        return F.attach_mail(owner, ws, str(a.get("address") or ""), bool(a.get("quiet")))
    if part == "inbox_mail_detach":
        return F.detach_mail(owner, ws, str(a.get("address") or ""))
    if part == "inbox_post":
        out = F.post(owner, ws, str(a.get("item") or ""), me)
    elif part == "inbox_drop":
        out = F.drop(owner, ws, str(a.get("item") or ""), me)
    elif part == "inbox_scan":
        out = {"read": asyncio.run(F.scan_now(owner, ws))}
    else:
        raise F.FeedError("Unknown inbox action.")
    forget(owner)
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
                   + (f"\nApprovals are ON: a posting over {(d.get('controls') or {}).get('limit') or 0} {cur} waits for a second person "
                      f"(the tool answers queued); tell her it waits, never that it is posted. Waiting now: {d.get('pending', 0)}."
                      if (d.get("controls") or {}).get("on") else "")
                   + (f"\nInbox: ON - invoices and bills come in by themselves from her mail, Hoola's own address, her connected programs, "
                      f"other systems and her shop; {n.get('inbox_posted', 0)} posted by Hoola, {n.get('inbox_needs', 0)} waiting for her look "
                      "(Books & Accounts > Inbox). Never ask her to type in an invoice that will come in by itself."
                      if n.get("inbox_on") else "\nInbox: off. If she wants invoices and bills to come in by themselves (mail, programs, shop), "
                      "send her to Books & Accounts > Inbox to turn it on.")
                   + (f"\nShe is the {d.get('role')} on these books (someone else owns them): the tool works only on her own businesses, "
                      "so explain from these figures and send her to the desk for changes." if d.get("role") not in (None, "owner") else "")
                   + "</books_desk>")
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
    def books_desk(workspace: str = "", tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant, workspace)

    @router.post("/api/books/do/{part}", dependencies=dep)
    def books_do(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        from .fin import laws as L
        from .fin.desks.safety import SafetyError
        try:
            return do(tenant, part, body or {})
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (SafetyError, ValueError) as e:
            raise HTTPException(400, str(e))

    @router.post("/api/books/in")
    async def books_in(request: Request):
        """v0.999.163 her other programs send invoices and bills here (Authorization: Bearer <her books key>)."""
        from .fin.desks import books_feed as F
        tok = str(request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        hit = F.ws_of_key(tok) if tok.startswith("bk_") else None
        if not hit:
            raise HTTPException(401, "Not a books key")
        raw = await request.body()
        if len(raw) > 25 * 1024 * 1024:
            raise HTTPException(413, "Too big")
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            raise HTTPException(400, "Send JSON")
        try:
            out = await F.from_api(hit[0], hit[1], body if isinstance(body, dict) else {})
        except F.FeedError as e:
            raise HTTPException(400, str(e))
        forget(hit[0])
        return out

    @router.get("/api/books/inbox/{item}/file", dependencies=dep)
    def books_inbox_file(item: str, workspace: str = "", tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response
        from .fin.desks import books_ent as E
        from .fin.desks import books_feed as F
        acc = E.access(tenant, workspace)
        try:
            name, data = F.file_of(acc["owner"], item)
        except F.FeedError as e:
            raise HTTPException(404, str(e))
        safe = re.sub(r'[^A-Za-z0-9._ -]', "_", name)[:120] or "file"
        return Response(data, media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{safe}"'})

    @router.put("/api/books/workspace", dependencies=dep)
    def books_workspace(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return pick(tenant, str((body or {}).get("workspace") or ""))
        except BooksDeskError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
