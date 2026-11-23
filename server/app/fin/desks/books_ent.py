"""v0.999.159 BOOKS ENTERPRISE - what a large finance team needs on top of the F3 books (owner: "HOW BIG ENTERPRISE WILL USE
IT" -> "MAKE IT ENTERPRISE READY").

  team         people on one business's books, each with a role; the owner (the workspace's tenant) is never a row
               admin       everything, the team and the controls
               accountant  reads, drafts, and starts postings
               approver    reads, approves other people's postings, locks a month
               auditor     reads everything and downloads the files
               viewer      reads
  controls     a business's switch: when ON, every posting (issue, journal, bank match, bank posting, depreciation,
               revaluation) above her approval limit waits for a SECOND person, never the one who made it; above her
               two-approver limit it needs two. A posting is bound to its arguments' hash and runs once, through _exec.
  cost centres a fixed list per business (or free text when she has none) carried on every income / expense line;
               profit and loss by cost centre
  group        her businesses consolidated in one presentation currency with HER rates (closing for the balance sheet,
               average for profit and loss); intercompany sales / purchases and balances eliminated, mismatches named;
               the translation difference shown, never hidden

Hoola never sends, pays or files; nothing here moves money."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .. import evidence as EV
from .safety import SafetyError


class EntError(SafetyError):
    pass


ROLES = ("admin", "accountant", "approver", "auditor", "viewer")
ROLE_NAMES = {"owner": "Owner", "admin": "Admin", "accountant": "Accountant", "approver": "Approver", "auditor": "Auditor", "viewer": "Viewer"}
POSTING = ("issue", "journal", "apply_match", "post_bank", "depreciation", "revalue")
READ = ("chart", "documents", "matches", "reconcile", "ageing", "reports", "close_check", "inventory",
        "requests", "by_cost_centre", "consolidate", "controls_read", "team", "inbox")
INBOX_WORK = {"inbox_post", "inbox_drop", "inbox_scan"}          # v0.999.163 the books inbox
INBOX_SET = {"inbox_settings", "inbox_key", "inbox_key_stop"}
PREPARE = ("invoice", "bill", "receipt", "asset")
CAN = {
    "owner": set(READ) | set(PREPARE) | set(POSTING) | INBOX_WORK | INBOX_SET | {"export", "close_lock", "add_account", "approve",
                                                                            "reject", "team_add", "team_remove", "controls"},
    "admin": set(READ) | set(PREPARE) | set(POSTING) | INBOX_WORK | INBOX_SET | {"export", "close_lock", "add_account", "approve",
                                                                            "reject", "team_add", "team_remove", "controls"},
    "accountant": set(READ) | set(PREPARE) | set(POSTING) | INBOX_WORK | {"export"},
    "approver": set(READ) | {"export", "close_lock", "approve", "reject"},
    "auditor": set(READ) | {"export"},
    "viewer": set(READ),
}


def _db():
    from ... import db
    from .. import models as M
    M.ensure()
    return db, M


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---- controls (in the workspace's settings, key books_ent) ---------------------------------------------------------------------

def controls(tenant: str, ws: str) -> dict[str, Any]:
    db, M = _db()
    with db.session() as s:
        w = s.get(M.FinWorkspace, ws)
        if not w or w.tenant_id != tenant:
            return {}
        return dict((json.loads(w.settings or "{}")).get("books_ent") or {})


def set_controls(tenant: str, ws: str, a: dict[str, Any], by: str) -> dict[str, Any]:
    cur = controls(tenant, ws)
    out = dict(cur)
    if "on" in a:
        out["on"] = bool(a["on"])
    for k in ("limit", "dual"):
        if k in a:
            v = a.get(k)
            if v in (None, ""):
                out[k] = None if k == "dual" else 0.0
            else:
                try:
                    f = float(v)
                except (TypeError, ValueError):
                    raise EntError(f"{k}: an amount.")
                if f < 0:
                    raise EntError(f"{k}: an amount of 0 or more.")
                out[k] = f
    if "cost_centres" in a:
        raw = a["cost_centres"]
        items = raw if isinstance(raw, list) else str(raw or "").split(",")
        out["cost_centres"] = list(dict.fromkeys(str(x).strip()[:80] for x in items if str(x).strip()))[:200]
    if out.get("dual") is not None and out["dual"] < float(out.get("limit") or 0):
        raise EntError("The two-approver amount must be at least the approval limit.")
    if out.get("on") and not cur.get("on"):
        approvers = [m for m in team(tenant, ws) if m["role"] in ("approver", "admin") and m["active"]]
        if not approvers:
            raise EntError("Add an approver (or an admin) to the team first: with the controls on, nobody approves their own posting.")
    db, M = _db()
    with db.session() as s:
        w = s.get(M.FinWorkspace, ws)
        if not w or w.tenant_id != tenant:
            raise EntError("No such business.")
        st = json.loads(w.settings or "{}")
        st["books_ent"] = out
        w.settings = json.dumps(st)
        s.commit()
    EV.record(tenant, ws, by, "books_controls", "controls changed", {"before": cur, "after": out})
    return out


# ---- the team -------------------------------------------------------------------------------------------------------------------

def team(tenant: str, ws: str) -> list[dict[str, Any]]:
    db, M = _db()
    with db.session() as s:
        rows = s.query(M.FinBooksMember).filter(M.FinBooksMember.tenant_id == tenant, M.FinBooksMember.workspace_id == ws) \
            .order_by(M.FinBooksMember.created_at).all()
        return [{"id": r.id, "email": r.email, "name": r.name or r.email, "role": r.role, "active": bool(r.active),
                 "joined": bool(r.user_id)} for r in rows]


def team_add(tenant: str, ws: str, email: str, role: str, name: str, by: str) -> dict[str, Any]:
    email = str(email or "").strip().lower()
    if "@" not in email or len(email) > 320:
        raise EntError("email: the person's email address (they sign in to Hoola with it).")
    if role not in ROLES:
        raise EntError("role: " + ", ".join(ROLES))
    db, M = _db()
    with db.session() as s:
        if not s.get(M.FinWorkspace, ws) or s.get(M.FinWorkspace, ws).tenant_id != tenant:
            raise EntError("No such business.")
        r = s.query(M.FinBooksMember).filter(M.FinBooksMember.tenant_id == tenant, M.FinBooksMember.workspace_id == ws,
                                             M.FinBooksMember.email == email).first()
        if r is None:
            r = M.FinBooksMember(tenant_id=tenant, workspace_id=ws, email=email, added_by=by)
            s.add(r)
        r.role, r.active, r.name = role, True, str(name or "").strip()[:120] or r.name or ""
        s.commit()
        mid = r.id
    EV.record(tenant, ws, by, "books_team", f"{email} is {role}", {})
    return {"id": mid, "email": email, "role": role}


def team_remove(tenant: str, ws: str, member_id: str, by: str) -> dict[str, Any]:
    db, M = _db()
    with db.session() as s:
        r = s.get(M.FinBooksMember, member_id)
        if r is None or r.tenant_id != tenant or r.workspace_id != ws:
            raise EntError("No such person on these books.")
        r.active = False
        s.commit()
        email = r.email
    if controls(tenant, ws).get("on") and not [m for m in team(tenant, ws) if m["role"] in ("approver", "admin") and m["active"]]:
        set_controls(tenant, ws, {"on": False}, by)          # never leave postings with nobody who may approve them
    EV.record(tenant, ws, by, "books_team", f"{email} removed", {})
    return {"removed": member_id}


def _email_of(user_id: str) -> str:
    try:
        from ...db import User, session
        with session() as s:
            u = s.get(User, user_id)
            return (u.email or "").lower() if u else ""
    except Exception:   # noqa: BLE001
        return ""


def _name_of(user_id: str) -> str:
    try:
        from ...db import User, session
        with session() as s:
            u = s.get(User, user_id)
            return (u.name or u.email or "") if u else ""
    except Exception:   # noqa: BLE001
        return ""


def access(caller: str, ws: str) -> dict[str, Any]:
    """Who the caller is on this business: the owner (its tenant) or a team member with a role. Refused otherwise."""
    db, M = _db()
    email = _email_of(caller)
    with db.session() as s:
        w = s.get(M.FinWorkspace, ws)
        if w is None or w.status != "active":
            raise EntError("No such business.")
        if w.tenant_id == caller:
            return {"owner": caller, "role": "owner", "id": caller, "name": _name_of(caller) or "Owner", "workspace": ws}
        q = s.query(M.FinBooksMember).filter(M.FinBooksMember.tenant_id == w.tenant_id, M.FinBooksMember.workspace_id == ws,
                                             M.FinBooksMember.active.is_(True))
        r = q.filter(M.FinBooksMember.user_id == caller).first() or (q.filter(M.FinBooksMember.email == email).first() if email else None)
        if r is None:
            raise EntError("No such business.")
        if not r.user_id:
            r.user_id = caller
            s.commit()
        return {"owner": w.tenant_id, "role": r.role, "id": caller, "name": r.name or r.email, "workspace": ws}


def shared_with(caller: str) -> list[dict[str, Any]]:
    """Businesses other people put the caller on."""
    db, M = _db()
    email = _email_of(caller)
    with db.session() as s:
        q = s.query(M.FinBooksMember).filter(M.FinBooksMember.active.is_(True))
        rows = q.filter((M.FinBooksMember.user_id == caller) | (M.FinBooksMember.email == email)).all() if email else \
            q.filter(M.FinBooksMember.user_id == caller).all()
        out = []
        for r in rows:
            w = s.get(M.FinWorkspace, r.workspace_id)
            if w is None or w.status != "active" or w.tenant_id == caller:
                continue
            out.append({"id": w.id, "name": w.name or "Business", "size": w.size, "currency": w.currency,
                        "countries": json.loads(w.countries or "[]"), "role": r.role, "shared_by": _name_of(w.tenant_id) or "its owner"})
        return out


def allowed(role: str, action: str) -> bool:
    return action in CAN.get(role, set())


# ---- postings that wait for a second person ---------------------------------------------------------------------------------

def _actor_id(tenant: str, actor: str) -> str:
    """'Name <id>' from the desk; anything else (the tool, the owner's own API) is the owner."""
    a = str(actor or "")
    if a.endswith(">") and "<" in a:
        return a[a.rindex("<") + 1:-1]
    return tenant


def _amount(tenant: str, ws: str, action: str, a: dict[str, Any]) -> tuple[float | None, str]:
    from . import books as BK
    db, M = _db()
    w = BK._ws(tenant, ws)                         # noqa: SLF001
    book = BK._book_cur(w)                         # noqa: SLF001
    if action == "issue":
        with db.session() as s:
            d = s.get(M.FinInvoice, str(a.get("doc") or ""))
            if not d or d.tenant_id != tenant or d.workspace_id != ws:
                raise BK.BooksError("No such document.")
            amt = d.total_minor * (d.rate if d.currency != book else 1)
            return BK._u(int(round(amt)), book), f"{'Invoice' if d.kind == 'sales' else 'Bill'} {d.party} {d.currency} {BK._u(d.total_minor, d.currency):,.2f}"   # noqa: SLF001
    if action in ("apply_match", "post_bank"):
        t = BK._bank_line(tenant, ws, str(a.get("txn") or ""))   # noqa: SLF001
        if not t:
            raise BK.BooksError("No such bank line.")
        what = f"Bank line {t['day']} {t['narration'][:60]}"
        if action == "apply_match":
            with db.session() as s:
                d = s.get(M.FinInvoice, str(a.get("doc") or ""))
                what += f" pays {d.number}" if d else ""
        else:
            what += f" to account {a.get('code')}"
        return BK._u(abs(t["amount_minor"]), book), what   # noqa: SLF001
    if action == "journal":
        dr = sum(Decimal(str(l.get("debit") or 0)) for l in a.get("lines") or [])
        return float(dr), f"Journal {str(a.get('memo') or '')[:80]}".strip()
    return None, {"depreciation": "Depreciation", "revalue": "Revaluation"}.get(action, action) + f" {a.get('period') or ''}"


def _hash(action: str, a: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps({"action": action, "a": a}, sort_keys=True, default=str).encode()).hexdigest()


def hold(tenant: str, ws: str, action: str, a: dict[str, Any], actor: str) -> dict[str, Any] | None:
    """Called by books.run for every action. Controls off -> None (runs at once). On -> a posting above the limit becomes a
    request; an invoice / bill asked to be issued at once is saved as a draft and its issue waits."""
    c = controls(tenant, ws)
    if not c.get("on"):
        return None
    if action in ("invoice", "bill") and a.get("issue_now"):
        from . import books as BK
        out = BK._exec(tenant, action, {**a, "issue_now": False}, actor)   # noqa: SLF001
        req = hold(tenant, ws, "issue", {"workspace": ws, "doc": out["id"]}, actor)
        if req is None:                            # under the limit: issued straight away
            out.update(BK._exec(tenant, "issue", {"workspace": ws, "doc": out["id"]}, actor))   # noqa: SLF001
        else:
            out["approval"] = req
            out["says"] = "Saved as a draft. Its issue waits for an approver."
        return out
    if action not in POSTING:
        return None
    amount, what = _amount(tenant, ws, action, a)
    limit = float(c.get("limit") or 0)
    if amount is not None and amount <= limit and limit > 0:
        return None                                # small enough to post without a second person
    dual = c.get("dual")
    needs = 2 if (dual is not None and (amount is None or amount > float(dual))) else 1
    db, M = _db()
    h = _hash(action, a)
    with db.session() as s:
        dup = s.query(M.FinBooksRequest).filter(M.FinBooksRequest.tenant_id == tenant, M.FinBooksRequest.workspace_id == ws,
                                                M.FinBooksRequest.hash == h, M.FinBooksRequest.status == "pending").first()
        if dup:
            return {"queued": True, "request": dup.id, "needs": dup.needs, "says": "Already waiting for approval."}
        r = M.FinBooksRequest(tenant_id=tenant, workspace_id=ws, action=action, args=json.dumps(a, default=str), hash=h, what=what[:240],
                              amount=amount, needs=needs, maker=str(actor)[:160], maker_id=_actor_id(tenant, actor))
        s.add(r)
        s.commit()
        rid = r.id
    EV.record(tenant, ws, str(actor), "books_request", f"{action} waits for approval", {"request": rid, "amount": amount})
    return {"queued": True, "request": rid, "needs": needs, "amount": amount,
            "says": f"Sent for approval ({'two approvers' if needs == 2 else 'one approver'}, never the person who made it). Nothing is posted yet."}


def _req_row(r) -> dict[str, Any]:
    return {"id": r.id, "action": r.action, "what": r.what, "amount": r.amount, "needs": r.needs, "maker": r.maker,
            "maker_id": r.maker_id, "approvals": json.loads(r.approvals or "[]"), "status": r.status, "result": r.result,
            "created_at": r.created_at.isoformat() if r.created_at else "", "decided_at": r.decided_at.isoformat() if r.decided_at else ""}


def requests(tenant: str, ws: str, status: str = "pending", limit: int = 200) -> list[dict[str, Any]]:
    db, M = _db()
    with db.session() as s:
        q = s.query(M.FinBooksRequest).filter(M.FinBooksRequest.tenant_id == tenant, M.FinBooksRequest.workspace_id == ws)
        if status:
            q = q.filter(M.FinBooksRequest.status == status)
        return [_req_row(r) for r in q.order_by(M.FinBooksRequest.created_at.desc()).limit(limit).all()]


def approve(tenant: str, ws: str, req_id: str, who_id: str, who: str) -> dict[str, Any]:
    from . import books as BK
    db, M = _db()
    with db.session() as s:
        r = s.get(M.FinBooksRequest, req_id)
        if r is None or r.tenant_id != tenant or r.workspace_id != ws:
            raise EntError("No such request.")
        if r.status != "pending":
            raise EntError(f"It is already {r.status}.")
        if who_id == r.maker_id:
            raise EntError("You made this posting; another person approves it.")
        got = json.loads(r.approvals or "[]")
        if any(x["id"] == who_id for x in got):
            raise EntError("You have already approved it; it needs a different second approver.")
        got.append({"id": who_id, "by": who, "at": _now().isoformat(timespec="seconds")})
        r.approvals = json.dumps(got)
        args, action, ready = json.loads(r.args or "{}"), r.action, len(got) >= r.needs
        if _hash(action, args) != r.hash:
            raise EntError("The request changed since it was made; it cannot run.")
        s.commit()
    EV.record(tenant, ws, who, "books_approve", f"approved {action}", {"request": req_id})
    if not ready:
        return {"request": req_id, "status": "pending", "approvals": len(got), "says": "Approved. It needs one more approver."}
    actor = f"{r.maker}, approved by {', '.join(x['by'] for x in got)}"[:80]
    try:
        out = BK._exec(tenant, action, args, actor)   # noqa: SLF001
        status, res = "done", out
    except Exception as e:   # noqa: BLE001
        status, res = "failed", {"error": str(e)[:300]}
    with db.session() as s:
        r = s.get(M.FinBooksRequest, req_id)
        r.status, r.result, r.decided_at = status, json.dumps(res, default=str)[:4000], _now()
        s.commit()
    return {"request": req_id, "status": status, "result": res,
            "says": "Approved and posted." if status == "done" else "Approved, but the books refused it: " + res["error"]}


def reject(tenant: str, ws: str, req_id: str, who_id: str, who: str, reason: str) -> dict[str, Any]:
    if len(str(reason or "").strip()) < 3:
        raise EntError("reason: why it is rejected (the maker sees it).")
    db, M = _db()
    with db.session() as s:
        r = s.get(M.FinBooksRequest, req_id)
        if r is None or r.tenant_id != tenant or r.workspace_id != ws:
            raise EntError("No such request.")
        if r.status != "pending":
            raise EntError(f"It is already {r.status}.")
        r.status, r.result, r.decided_at = "rejected", json.dumps({"by": who, "reason": str(reason)[:500]}), _now()
        s.commit()
    EV.record(tenant, ws, who, "books_reject", "rejected", {"request": req_id, "reason": reason})
    return {"request": req_id, "status": "rejected"}


# ---- cost centres ---------------------------------------------------------------------------------------------------------

def by_cost_centre(tenant: str, ws: str, since: str, upto: str) -> dict[str, Any]:
    from . import books as BK
    w = BK._ws(tenant, ws)              # noqa: SLF001
    book = BK._book_cur(w)              # noqa: SLF001
    types = {c["code"]: c["type"] for c in BK.coa(tenant, ws)}
    db, M = _db()
    inc: dict[str, int] = defaultdict(int)
    exp: dict[str, int] = defaultdict(int)
    with db.session() as s:
        q = s.query(M.FinLine.code, M.FinLine.debit_minor, M.FinLine.credit_minor, M.FinLine.dim) \
            .join(M.FinJournal, M.FinJournal.id == M.FinLine.journal_id) \
            .filter(M.FinLine.tenant_id == tenant, M.FinLine.workspace_id == ws, M.FinJournal.day >= since, M.FinJournal.day <= upto)
        for code, dr, cr, dim in q.all():
            t = types.get(code)
            k = dim or ""
            if t == "income":
                inc[k] += cr - dr
            elif t == "expense":
                exp[k] += dr - cr
    rows = []
    for k in sorted(set(inc) | set(exp), key=lambda x: (x == "", x)):
        rows.append({"cost_centre": k or "(none)", "income": BK._u(inc[k], book), "expenses": BK._u(exp[k], book),   # noqa: SLF001
                     "profit": BK._u(inc[k] - exp[k], book)})                                                     # noqa: SLF001
    return {"currency": book, "from": since, "to": upto, "rows": rows,
            "total_profit": BK._u(sum(inc.values()) - sum(exp.values()), book)}                                   # noqa: SLF001


# ---- the group: consolidation with her rates --------------------------------------------------------------------------------

def consolidate(caller: str, ws_ids: list[str], currency: str, rates: dict[str, Any], since: str, upto: str) -> dict[str, Any]:
    """Her businesses in one presentation currency. Every rate is hers (closing for the balance sheet, average for profit and loss);
    a currency with no rate is refused by name. Intercompany documents (ic_ws) are eliminated both ways; any difference is named."""
    from . import books as BK
    currency = str(currency or "").upper()
    if len(currency) != 3:
        raise EntError("currency: the group's presentation currency, e.g. GBP.")
    ids = list(dict.fromkeys(str(x) for x in ws_ids or [] if x))
    if len(ids) < 2:
        raise EntError("Choose at least two businesses.")
    ents = []
    for w in ids:
        acc = access(caller, w)
        if not allowed(acc["role"], "consolidate"):
            raise EntError("You cannot read one of these businesses.")
        info = BK._ws(acc["owner"], w)      # noqa: SLF001
        ents.append({"ws": w, "owner": acc["owner"], "name": info["name"] or "Business", "cur": BK._book_cur(info)})   # noqa: SLF001
    rates = {str(k).upper(): v for k, v in (rates or {}).items()}

    def rate(cur: str, kind: str) -> float:
        if cur == currency:
            return 1.0
        r = rates.get(cur) or {}
        try:
            v = float(r.get(kind) if isinstance(r, dict) else r)
        except (TypeError, ValueError):
            raise EntError(f"rates: {cur} to {currency} - the {kind} rate (your own, with its source).")
        if v <= 0:
            raise EntError(f"rates: {cur} {kind} must be more than 0.")
        return v
    per, tot = [], defaultdict(float)
    ic_sales, ic_purch, ic_ar, ic_ap = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    db, M = _db()
    for e in ents:
        rep = BK.reports(e["owner"], e["ws"], since, upto)
        pl, bs = rep["profit_and_loss"], rep["balance_sheet"]
        avg, close = rate(e["cur"], "average"), rate(e["cur"], "closing")
        row = {"business": e["name"], "currency": e["cur"], "average_rate": avg, "closing_rate": close,
               "income": round(pl["income"] * avg, 2), "expenses": round(pl["expenses"] * avg, 2),
               "assets": round(bs["assets"] * close, 2), "liabilities": round(bs["liabilities"] * close, 2),
               "equity": round(bs["equity"] * close, 2)}
        per.append(row)
        for k in ("income", "expenses", "assets", "liabilities", "equity"):
            tot[k] += row[k]
        with db.session() as s:
            for d in s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == e["owner"], M.FinInvoice.workspace_id == e["ws"],
                                                  M.FinInvoice.ic_ws != "", M.FinInvoice.ic_ws.isnot(None),
                                                  M.FinInvoice.status != "draft").all():
                if d.ic_ws not in ids:
                    continue
                to_book = d.rate if d.currency != e["cur"] else 1.0
                net = BK._u(d.net_minor, d.currency) * to_book * avg            # noqa: SLF001
                left = BK._u(d.total_minor - d.paid_minor, d.currency) * (d.carried_rate if d.currency != e["cur"] else 1.0) * close   # noqa: SLF001
                pair = tuple(sorted((e["ws"], d.ic_ws)))
                if since <= d.issue <= upto:
                    (ic_sales if d.kind == "sales" else ic_purch)[pair] += net
                (ic_ar if d.kind == "sales" else ic_ap)[pair] += left
    elim, mismatches = [], []
    names = {e["ws"]: e["name"] for e in ents}
    for pair in sorted(set(ic_sales) | set(ic_purch) | set(ic_ar) | set(ic_ap)):
        a, b = names[pair[0]], names[pair[1]]
        s_, p_, ar, ap = ic_sales[pair], ic_purch[pair], ic_ar[pair], ic_ap[pair]
        elim.append({"between": f"{a} and {b}", "sales": round(s_, 2), "purchases": round(p_, 2), "receivable": round(ar, 2),
                     "payable": round(ap, 2)})
        if abs(s_ - p_) > 0.01:
            mismatches.append(f"{a} and {b}: sales {round(s_, 2)} vs purchases {round(p_, 2)} {currency} - one side is missing or different")
        if abs(ar - ap) > 0.01:
            mismatches.append(f"{a} and {b}: owed {round(ar, 2)} vs owing {round(ap, 2)} {currency}")
    inc = tot["income"] - sum(x["sales"] for x in elim)
    exp = tot["expenses"] - sum(x["purchases"] for x in elim)
    assets = tot["assets"] - sum(x["receivable"] for x in elim)
    liab = tot["liabilities"] - sum(x["payable"] for x in elim)
    eq = tot["equity"]
    cta = round(assets - liab - eq, 2)
    return {"currency": currency, "from": since, "to": upto, "businesses": per, "eliminations": elim, "mismatches": mismatches,
            "profit_and_loss": {"income": round(inc, 2), "expenses": round(exp, 2), "profit": round(inc - exp, 2)},
            "balance_sheet": {"assets": round(assets, 2), "liabilities": round(liab, 2), "equity": round(eq, 2),
                              "translation_and_elimination_difference": cta},
            "rates_note": "Every rate is yours: average for profit and loss, closing for the balance sheet. "
                          "The difference line is the translation difference plus any intercompany mismatch - it is shown, never hidden.",
            "not_advice": "A management consolidation from your books, not audited group accounts."}
