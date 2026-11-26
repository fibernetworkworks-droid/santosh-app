"""INSTITUTION DESK - the Institution employee's own section, like Payroll, Tax, Cash & Treasury, Credit & Lending, Firm Practice and
Payments (owner: "NOW LETS WORK ON NEXT EMPLOYEE INSTITUTION DESK").

- The Institution chat = a Conversation with kind 'institution', kept out of every Hoola chat list (callconv.not_call); facts she tells it
  still reach her one memory. A turn in it (or a voice call started from it) gets the desk's state as a block and the institution tool
  (`institution_desk`, family institution) in view.
- The desk runs the F9 engine (fin/desks/institution.py + fin/makerchecker.py) on an INSTITUTION workspace: five areas - financial crime,
  compliance, risk, audit, governance - and maker-checker under all of them.
- Every engine action is done AS a named person of the institution (admin, maker, checker, MLRO, compliance, risk, audit, secretary,
  viewer). Who the signed-in user is on the desk is kept in the workspace settings under `institution_desk`:
    who     the owner picks which person she is (she can switch, it is her account);
    logins  an admin links a person to a team member's email: that member is always that person, never another.
  So the maker of a draft never checks it, an amount above her single-check limit needs two checkers, a check holds only for the exact
  text it read, and only an MLRO or compliance person scores a SAR draft - the engine checks it.
- The engine keeps the registers it owns (people, obligations, incidents, whistleblowing cases, SAR scores, keys, retention) in `inst`.
  The desk keeps her inputs for the parts that count (the transactions for monitoring, her rule values, her watch list, complaints,
  risks, third parties, models, exposures, prepared-by-client list, samples and test results, journals, the board's agenda, the cap table,
  her related parties) in `institution_desk`, so every page shows her figures again.
- Hoola prepares, screens and counts. Nothing is filed, frozen or reported to a regulator here: the named officer decides. Not legal advice.
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

log = logging.getLogger("santosh.instchat")

KIND = "institution"
KEY = "institution_desk"        # the Hub employee
TOOL = "institution_desk"       # its tool
FAMILIES = ["institution"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FOOT = ("Hoola prepares, screens and counts. Nothing is filed, frozen or reported to a regulator here - the institution's named officer "
        "decides and signs. Not legal advice.")
ROLE_SAY = {"admin": "Admin", "maker": "Maker", "checker": "Checker", "mlro": "MLRO", "compliance": "Compliance", "risk": "Risk",
            "audit": "Audit", "secretary": "Company secretary", "viewer": "Viewer"}
KIND_SAY = {"sar": "Suspicious activity report", "policy": "Policy", "board": "Board paper", "return": "Regulatory return",
            "limit": "Limit change", "procedure": "Procedure", "report": "Report", "draft": "Draft"}
# who changes the desk's own inputs for each area (an admin always can; anyone who is a person of the institution reads)
AREA = {"crime": ("mlro", "compliance", "maker"), "compliance": ("compliance",), "risk": ("risk", "compliance"), "audit": ("audit",),
        "governance": ("secretary",)}
MAX_ROWS = 20000
DEFAULT_CLOCKS = [{"report": "Initial notification", "hours": 4}, {"report": "Intermediate report", "hours": 72},
                  {"report": "Final report", "hours": 720}]


class InstDeskError(ValueError):
    pass


def is_institution(conv: str) -> bool:
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
        log.exception("institution chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _hire():
    from .employee import hire
    return hire


def institutions(tenant: str) -> list[dict[str, Any]]:
    from .bookschat import businesses as B
    return [b for b in B(tenant) if b.get("size") == "institution"]


def workspace(tenant: str, want: str = "") -> dict[str, Any] | None:
    xs = institutions(tenant)
    if not want:
        try:
            want = str(_hire().settings(tenant, KEY).get("workspace") or "")
        except Exception:   # noqa: BLE001
            want = ""
    for b in xs:
        if b["id"] == want:
            return b
    return xs[0] if xs else None


def pick(tenant: str, ws: str) -> dict[str, Any]:
    if not any(b["id"] == ws for b in institutions(tenant)):
        raise InstDeskError("No such institution.")
    try:
        _hire().save_settings(tenant, KEY, workspace=ws)
    except Exception:   # noqa: BLE001
        pass
    forget(tenant)
    return {"workspace": ws}


def _run(owner: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin.desks import institution as IN
    try:
        return IN.run(owner, action, a)
    except IN.InstError as e:
        raise InstDeskError(str(e))


def setup(tenant: str, a: dict[str, Any]) -> dict[str, Any]:
    """A new institution (a finance workspace of size institution) with her as its first person: an admin, plus the roles she holds."""
    from .fin import makerchecker as MC
    from .fin import profile as PR
    name = str(a.get("name") or "").strip()[:80]
    me = str(a.get("admin") or "").strip()[:80]
    cc = str(a.get("country") or "").strip().upper()
    cur = str(a.get("currency") or "").strip().upper()
    if not name or not me:
        raise InstDeskError("name (the institution) and admin (your name, the first person).")
    if len(cc) != 2 or len(cur) != 3:
        raise InstDeskError("country (two letters, like GB) and currency (three letters, like GBP).")
    roles = ["admin"] + [r for r in (a.get("roles") or []) if r in MC.ROLES and r != "admin"]
    pv = PR.preview({"size": "institution", "countries": [cc], "currency": cur, "name": name, "wants": []})
    w = PR.apply(tenant, pv["answers"], pv["hash"])
    p = _run(tenant, "person_add", {"workspace": w["id"], "name": me, "roles": roles})["person"]
    _put(tenant, w["id"], lambda st: st.setdefault("who", {}).__setitem__(tenant, p["id"]))
    pick(tenant, w["id"])
    _regreet(tenant)
    return {"institution": {"id": w["id"], "name": w["name"]}, "person": p}


def _regreet(tenant: str) -> None:
    """An Institution chat nobody has written in yet gets the greeting that fits the desk now."""
    try:
        hi = greeting(tenant)
        with session() as s:
            for c in s.scalars(_q(tenant)).all():
                if s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user")):
                    continue
                for m in s.scalars(select(Message).where(Message.conversation_id == c.id, Message.role == "assistant")).all():
                    m.content = m.display = hi
            s.commit()
    except Exception:   # noqa: BLE001
        log.exception("institution chat greeting refresh failed")


# ---------------------------------------------------------------- desk state
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _settings(owner: str, ws: str) -> dict[str, Any]:
    from .fin import profile as PR
    return dict(PR.get(owner, ws).get("settings") or {})


def _inst(owner: str, ws: str) -> dict[str, Any]:
    return dict(_settings(owner, ws).get("inst") or {})


_DEF = (("who", {}), ("logins", {}), ("tx", []), ("rules", {}), ("watch", []), ("complaints", []), ("deadline_days", None),
        ("risks", []), ("appetite", 12), ("vendors", []), ("models", []), ("exposures", []), ("pbc", []), ("samples", []),
        ("journals", []), ("period_end", ""), ("usual_users", []), ("agenda", []), ("papers", []), ("actions", []), ("holders", []),
        ("related", []), ("clocks", None), ("files", []))


def _state(owner: str, ws: str) -> dict[str, Any]:
    st = dict(_settings(owner, ws).get("institution_desk") or {})
    for k, v in _DEF:
        st.setdefault(k, json.loads(json.dumps(v)))
    return st


def _put(owner: str, ws: str, change) -> Any:
    from . import db
    from .fin.models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != owner:
            raise InstDeskError("No such institution.")
        cur = json.loads(row.settings or "{}")
        st = cur.setdefault("institution_desk", {})
        for k, v in _DEF:
            st.setdefault(k, json.loads(json.dumps(v)))
        out = change(st)
        row.settings = json.dumps(cur)
        s.commit()
    return out


def _inst_put(owner: str, ws: str, change) -> Any:
    from .fin import makerchecker as MC
    try:
        return MC.save(owner, ws, change)
    except MC.MCError as e:
        raise InstDeskError(str(e))


def _people(owner: str, ws: str) -> dict[str, dict[str, Any]]:
    return dict(_inst(owner, ws).get("people") or {})


def _email(caller: str) -> str:
    try:
        from .fin.desks import books_ent as E
        return str(E._email_of(caller) or "").lower()   # noqa: SLF001
    except Exception:   # noqa: BLE001
        return ""


def whoami(caller: str, ws: str) -> dict[str, Any]:
    """The person of the institution the signed-in user is: a team member by the login an admin linked; the owner by her pick."""
    from .fin.desks import books_ent as E
    acc = E.access(caller, ws)
    owner = acc["owner"]
    people = _people(owner, ws)
    st = _state(owner, ws)
    if caller == owner:
        pid = st["who"].get(caller) or ""
        if pid not in people:
            pid = next((k for k, v in people.items() if "admin" in v["roles"]), "")
    else:
        em = _email(caller)
        pid = next((k for k, v in st["logins"].items() if v and (v.lower() == em or v == caller)), "")
        if pid not in people:
            pid = ""
    p = {"id": pid, **people[pid]} if pid else None
    return {"owner": owner, "is_owner": caller == owner, "person": p, "acc": acc}


def _engine(owner: str, me: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin import core
    from .fin.desks import institution as IN
    try:
        return core.run_tool(owner, me, TOOL, action, dict(a), lambda: IN.run(owner, action, a, me))
    except IN.InstError as e:
        raise InstDeskError(str(e))


def _num(v: Any, what: str, lo: float | None = None, hi: float | None = None) -> float:
    try:
        x = float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        raise InstDeskError(f"{what}: a number.")
    if lo is not None and x < lo:
        raise InstDeskError(f"{what}: not below {lo:g}.")
    if hi is not None and x > hi:
        raise InstDeskError(f"{what}: not above {hi:g}.")
    return x


def _day(v: Any, what: str) -> str:
    try:
        return date.fromisoformat(str(v).strip()[:10]).isoformat()
    except ValueError:
        raise InstDeskError(f"{what}: a date as YYYY-MM-DD.")


def _text(v: Any, n: int = 80) -> str:
    return str(v or "").strip()[:n]


def _yes(v: Any) -> bool:
    return v is True or str(v or "").strip().lower() in ("1", "y", "yes", "true", "on", "x")


def _need(p: dict[str, Any], area: str) -> None:
    want = AREA[area]
    if not ({"admin", *want} & set(p.get("roles") or [])):
        say = " or ".join(ROLE_SAY[r] for r in want)
        raise InstDeskError(f"{p['name']} does not hold the {say} role, so cannot change this part. An admin can add the role on Team.")


def _next_n(rows: list[dict[str, Any]]) -> int:
    return 1 + max([int(x.get("n") or 0) for x in rows] or [0])


# ---------------------------------------------------------------- CSV files she uploads
_ALIAS = {
    "id": ("id", "ref", "reference", "transaction id", "transaction_id", "txn id", "journal id", "entry id"),
    "customer": ("customer", "customer id", "customer_id", "account", "account id", "client"),
    "date": ("date", "booked", "value date", "posted", "created", "day"),
    "amount": ("amount", "value", "sum", "gross"),
    "direction": ("direction", "in/out", "dr/cr", "side", "flow"),
    "channel": ("channel", "type", "method", "mode"),
    "country": ("country", "country code", "iso country"),
    "counterparty": ("counterparty", "sender", "receiver", "payee", "payer", "beneficiary", "other party"),
    "category": ("category", "type", "product", "topic"),
    "received": ("received", "opened", "date received", "raised"),
    "closed": ("closed", "resolved", "date closed", "final response"),
    "upheld": ("upheld", "outcome", "result"),
    "ead": ("ead", "exposure", "balance", "outstanding"),
    "pd": ("pd", "probability of default"),
    "pd_lifetime": ("pd_lifetime", "lifetime pd", "pd lifetime"),
    "lgd": ("lgd", "loss given default"),
    "dpd": ("dpd", "days past due", "arrears days"),
    "stage": ("stage",),
    "user": ("user", "posted by", "created by", "preparer", "entered by"),
    "description": ("description", "narrative", "memo", "text", "details"),
}
_DIR = {"in": "in", "credit": "in", "cr": "in", "c": "in", "deposit": "in", "received": "in",
        "out": "out", "debit": "out", "dr": "out", "d": "out", "withdrawal": "out", "paid": "out", "sent": "out"}


def _read_csv(text: str, want: list[str], need: list[str]) -> list[dict[str, Any]]:
    rows = list(csv.reader(io.StringIO(str(text or "").lstrip("﻿"))))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise InstDeskError("The file needs a header line and at least one row.")
    head = [h.strip().lower() for h in rows[0]]
    col: dict[str, int] = {}
    for k in want:
        for al in _ALIAS.get(k, (k,)):
            if al in head and head.index(al) not in col.values():
                col[k] = head.index(al)
                break
    miss = [k for k in need if k not in col]
    if miss:
        raise InstDeskError(f"The file has no column for {', '.join(miss)} (its header: {', '.join(rows[0])[:200]}).")
    return [{k: (r[i].strip() if i < len(r) else "") for k, i in col.items()} for r in rows[1:MAX_ROWS + 1]]


def upload(owner: str, ws: str, p: dict[str, Any], a: dict[str, Any]) -> dict[str, Any]:
    """A CSV: transactions (monitoring), complaints, exposures (ECL) or journals (journal-entry testing)."""
    kind = str(a.get("kind") or "")
    text = str(a.get("text") or "")
    if kind == "transactions":
        _need(p, "crime")
        rows = _read_csv(text, ["id", "customer", "date", "amount", "direction", "channel", "country", "counterparty"],
                         ["customer", "date", "amount"])
        new = []
        for k, r in enumerate(rows):
            d = _DIR.get(str(r.get("direction") or "in").strip().lower())
            if d is None:
                raise InstDeskError(f"Row {k + 2}: direction {r.get('direction')!r} - in or out.")
            amt = _num(r["amount"], f"row {k + 2} amount")
            new.append({"id": r.get("id") or f"r{k + 2}", "customer": r["customer"][:60], "date": _day(r["date"], f"row {k + 2} date"),
                        "amount": abs(amt), "direction": d, "channel": (r.get("channel") or "").lower()[:20],
                        "country": (r.get("country") or "").upper()[:3], "counterparty": (r.get("counterparty") or "")[:80]})
        mode = "replace" if a.get("replace", True) else "add"

        def ch(st):
            st["tx"] = (new if mode == "replace" else st["tx"] + new)[-MAX_ROWS:]
            return len(st["tx"])
        total = _put(owner, ws, ch)
    elif kind == "complaints":
        _need(p, "compliance")
        rows = _read_csv(text, ["id", "category", "received", "closed", "upheld"], ["category", "received"])
        new = [{"id": r.get("id") or f"c{k + 2}", "category": r["category"][:40] or "other", "received": _day(r["received"], f"row {k + 2} received"),
                "closed": _day(r["closed"], f"row {k + 2} closed") if r.get("closed") else "", "upheld": _yes(r.get("upheld"))
                or str(r.get("upheld") or "").strip().lower() == "upheld"} for k, r in enumerate(rows)]
        total = _put(owner, ws, lambda st: (st.__setitem__("complaints", new[-MAX_ROWS:]), len(new))[1])
    elif kind == "exposures":
        _need(p, "risk")
        rows = _read_csv(text, ["id", "ead", "pd", "pd_lifetime", "lgd", "dpd", "stage"], ["ead", "pd", "lgd"])
        new = []
        for k, r in enumerate(rows):
            e = {"id": r.get("id") or f"e{k + 2}", "ead": _num(r["ead"], f"row {k + 2} ead", 0), "pd": _num(r["pd"], f"row {k + 2} pd", 0, 1),
                 "lgd": _num(r["lgd"], f"row {k + 2} lgd", 0, 1), "dpd": _num(r.get("dpd") or 0, f"row {k + 2} dpd", 0)}
            if r.get("pd_lifetime"):
                e["pd_lifetime"] = _num(r["pd_lifetime"], f"row {k + 2} pd_lifetime", 0, 1)
            if r.get("stage"):
                e["stage"] = int(_num(r["stage"], f"row {k + 2} stage", 1, 3))
            new.append(e)
        total = _put(owner, ws, lambda st: (st.__setitem__("exposures", new), len(new))[1])
    elif kind == "journals":
        _need(p, "audit")
        rows = _read_csv(text, ["id", "date", "amount", "user", "description"], ["date", "amount"])
        new = [{"id": r.get("id") or f"j{k + 2}", "date": _day(r["date"], f"row {k + 2} date"), "amount": abs(_num(r["amount"], f"row {k + 2} amount")),
                "user": (r.get("user") or "")[:60], "description": (r.get("description") or "")[:160]} for k, r in enumerate(rows)]
        total = _put(owner, ws, lambda st: (st.__setitem__("journals", new), len(new))[1])
    else:
        raise InstDeskError("kind: transactions | complaints | exposures | journals.")
    name = _text(a.get("name"), 80) or kind
    _put(owner, ws, lambda st: st.__setitem__("files", (st["files"] + [{"kind": kind, "name": name, "rows": len(rows), "at": _now(),
                                                                        "by": p["name"]}])[-30:]))
    return {"rows": len(rows), "total": total, "kind": kind}


def clear(owner: str, ws: str, p: dict[str, Any], a: dict[str, Any]) -> dict[str, Any]:
    kind = str(a.get("kind") or "")
    area = {"tx": "crime", "complaints": "compliance", "exposures": "risk", "journals": "audit"}.get(kind)
    if not area:
        raise InstDeskError("kind: tx | complaints | exposures | journals.")
    _need(p, area)
    _put(owner, ws, lambda st: st.__setitem__(kind, []))
    return {"cleared": kind}


# ---------------------------------------------------------------- registers the desk keeps
def _lines(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v or "").splitlines() if x.strip()]


def save_register(owner: str, ws: str, p: dict[str, Any], a: dict[str, Any]) -> dict[str, Any]:
    """Add to (or remove from) one of the desk's registers: risks, vendors, models, pbc, agenda, papers, actions, holders, related, watch."""
    reg = str(a.get("register") or "")
    area = {"risks": "risk", "vendors": "risk", "models": "risk", "pbc": "audit", "agenda": "governance", "papers": "governance",
            "actions": "governance", "holders": "governance", "related": "governance", "watch": "crime"}.get(reg)
    if not area:
        raise InstDeskError("register: risks | vendors | models | pbc | agenda | papers | actions | holders | related | watch.")
    _need(p, area)
    if a.get("remove") is not None:
        n = int(_num(a["remove"], "remove"))

        def rm(st):
            before = len(st[reg])
            st[reg] = [x for x in st[reg] if int(x.get("n") or 0) != n]
            if len(st[reg]) == before:
                raise InstDeskError("Nothing with that number.")
            return {"removed": n}
        return _put(owner, ws, rm)
    if a.get("edit") is not None:
        n = int(_num(a["edit"], "edit"))
        ch = {k: v for k, v in (a.get("set") or {}).items() if k in ("received", "done", "exit_plan", "validated", "last_assessed", "status")}

        def ed(st):
            for x in st[reg]:
                if int(x.get("n") or 0) == n:
                    for k, v in ch.items():
                        if k in ("received", "done"):
                            x[k] = _yes(v)
                            x[k + "_on"] = date.today().isoformat() if _yes(v) else ""
                        elif k in ("validated", "last_assessed"):
                            x[k] = _day(v, k) if v else ""
                        else:
                            x[k] = _text(v, 160)
                    return {"item": x}
            raise InstDeskError("Nothing with that number.")
        return _put(owner, ws, ed)
    it = dict(a.get("item") or {})
    if reg == "risks":
        row = {"name": _text(it.get("name"), 120), "likelihood": int(_num(it.get("likelihood"), "likelihood", 1, 5)),
               "impact": int(_num(it.get("impact"), "impact", 1, 5)), "control_effect": int(_num(it.get("control_effect") or 0, "control_effect", 0, 24)),
               "owner": _text(it.get("owner")), "control": _text(it.get("control"), 160)}
    elif reg == "vendors":
        row = {"name": _text(it.get("name"), 120), "service": _text(it.get("service"), 120), "critical": _yes(it.get("critical")),
               "contract_end": _day(it["contract_end"], "contract_end") if it.get("contract_end") else "",
               "data_location": _text(it.get("data_location"), 60), "subcontractors": _text(it.get("subcontractors"), 160),
               "exit_plan": _text(it.get("exit_plan"), 160), "last_assessed": _day(it["last_assessed"], "last_assessed") if it.get("last_assessed") else ""}
    elif reg == "models":
        row = {"name": _text(it.get("name"), 120), "owner": _text(it.get("owner")), "ai": _yes(it.get("ai")),
               "validated": _day(it["validated"], "validated") if it.get("validated") else "",
               "validate_every_days": int(_num(it.get("validate_every_days") or 365, "validate_every_days", 1)), "use": _text(it.get("use"), 160)}
    elif reg == "pbc":
        row = {"item": _text(it.get("item"), 160), "owner": _text(it.get("owner")), "due": _day(it["due"], "due") if it.get("due") else "",
               "received": False}
    elif reg == "agenda":
        row = {"item": _text(it.get("item"), 160), "paper": _text(it.get("paper"), 120), "owner": _text(it.get("owner"))}
    elif reg == "papers":
        row = {"paper": _text(it.get("paper"), 120)}
    elif reg == "actions":
        row = {"action": _text(it.get("action"), 200), "owner": _text(it.get("owner")), "due": _day(it["due"], "due") if it.get("due") else "",
               "done": False}
    elif reg == "holders":
        row = {"name": _text(it.get("name"), 80), "shares": int(_num(it.get("shares"), "shares", 0)), "class": _text(it.get("class"), 30)}
    elif reg == "related":
        row = {"name": _text(it.get("name"), 120), "relation": _text(it.get("relation"), 80)}
    else:   # watch
        row = {"name": _text(it.get("name"), 120), "list": _text(it.get("list"), 60), "ref": _text(it.get("ref"), 40)}
    key = "item" if reg in ("pbc", "agenda") else "action" if reg == "actions" else "paper" if reg == "papers" else "name"
    if not row[key]:
        raise InstDeskError(f"{key}: it needs a name.")

    def add(st):
        row["n"] = _next_n(st[reg])
        st[reg].append(row)
        return {"item": row}
    return _put(owner, ws, add)


def save_settings(owner: str, ws: str, p: dict[str, Any], a: dict[str, Any]) -> dict[str, Any]:
    """Her own values: AML rules, the complaint deadline, the risk appetite, incident clocks, the audit period end and usual users."""
    from .fin.desks import institution as IN
    out = {}
    if "rules" in a:
        _need(p, "crime")
        rules = {}
        for k, v in (a.get("rules") or {}).items():
            if k not in IN.DEFAULT_RULES or v in (None, ""):
                continue
            if k == "high_risk_countries":
                rules[k] = [c.strip().upper()[:3] for c in (v if isinstance(v, list) else str(v).split(",")) if c.strip()]
            else:
                rules[k] = _num(v, f"rules.{k}", 0)
        _put(owner, ws, lambda st: st.__setitem__("rules", rules))
        out["rules"] = rules
    if "deadline_days" in a:
        _need(p, "compliance")
        v = int(_num(a["deadline_days"], "deadline_days", 1)) if str(a["deadline_days"]).strip() else None
        _put(owner, ws, lambda st: st.__setitem__("deadline_days", v))
        out["deadline_days"] = v
    if "appetite" in a:
        _need(p, "risk")
        v = _num(a["appetite"], "appetite", 1, 25)
        _put(owner, ws, lambda st: st.__setitem__("appetite", v))
        out["appetite"] = v
    if "clocks" in a:
        _need(p, "risk")
        cl = [{"report": _text(c.get("report"), 60), "hours": _num(c.get("hours"), "hours", 0)} for c in a.get("clocks") or [] if _text(c.get("report"), 60)]
        _put(owner, ws, lambda st: st.__setitem__("clocks", cl or None))
        out["clocks"] = cl
    if "period_end" in a or "usual_users" in a:
        _need(p, "audit")
        pe = _day(a["period_end"], "period_end") if a.get("period_end") else ""
        uu = [u.strip()[:60] for u in (a.get("usual_users") if isinstance(a.get("usual_users"), list) else str(a.get("usual_users") or "").split(","))
              if u.strip()]
        _put(owner, ws, lambda st: (st.__setitem__("period_end", pe), st.__setitem__("usual_users", uu)))
        out.update({"period_end": pe, "usual_users": uu})
    if not out:
        raise InstDeskError("Nothing to save.")
    return out


# ---------------------------------------------------------------- what the desk reads
def aml(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["tx"]:
        return {"empty": True, "alerts": [], "rules_yours": sorted(st["rules"])}
    return _engine(owner, me, "aml_triage", {"transactions": st["tx"], "rules": st["rules"]})


def _tx_for(st: dict[str, Any], ids: list[str]) -> list[dict[str, Any]]:
    want = set(map(str, ids))
    return [t for t in st["tx"] if str(t["id"]) in want]


def rcsa(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["risks"]:
        return {"empty": True, "risks": [], "appetite": st["appetite"]}
    out = _engine(owner, me, "rcsa", {"risks": st["risks"], "appetite": st["appetite"]})
    for r, src in zip(out["risks"], st["risks"]):
        r.update({"n": src["n"], "likelihood": src["likelihood"], "impact": src["impact"], "owner": src.get("owner"), "control": src.get("control")})
    out["appetite"] = st["appetite"]
    return out


def third(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["vendors"]:
        return {"empty": True, "vendors": []}
    out = _engine(owner, me, "third_party", {"vendors": st["vendors"]})
    for v, src in zip(out["vendors"], st["vendors"]):
        v.update({k: src.get(k) for k in ("n", "service", "critical", "contract_end", "data_location", "exit_plan", "last_assessed")})
    return out


def model_inv(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["models"]:
        return {"empty": True, "models": []}
    out = _engine(owner, me, "models", {"models": st["models"]})
    for m, src in zip(out["models"], st["models"]):
        m.update({"n": src["n"], "validated": src.get("validated"), "use": src.get("use"), "every": src.get("validate_every_days")})
    return out


def pbc(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["pbc"]:
        return {"empty": True, "items": []}
    out = _engine(owner, me, "pbc", {"items": st["pbc"]})
    for x, src in zip(out["items"], st["pbc"]):
        x.update({"n": src["n"], "due": src.get("due"), "received_on": src.get("received_on")})
    return out


def board(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    out = _engine(owner, me, "board_pack", {"agenda": st["agenda"], "papers": [x["paper"] for x in st["papers"]],
                                             "actions": [{**x, "done": x.get("done")} for x in st["actions"]]})
    for x, src in zip(out["agenda"], st["agenda"]):
        x.update({"n": src["n"], "owner": src.get("owner")})
    out["papers"] = st["papers"]
    out["actions"] = st["actions"]
    return out


def complaints(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["complaints"]:
        return {"empty": True}
    a = {"complaints": st["complaints"]}
    if st["deadline_days"]:
        a["deadline_days"] = st["deadline_days"]
    return _engine(owner, me, "complaints_mi", a)


def ecl(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["exposures"]:
        return {"empty": True}
    return _engine(owner, me, "ecl", {"exposures": st["exposures"]})


def je(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["journals"]:
        return {"empty": True}
    a: dict[str, Any] = {"journals": st["journals"], "usual_users": st["usual_users"]}
    if st["period_end"]:
        a["period_end"] = st["period_end"]
    out = _engine(owner, me, "je_test", a)
    by = {str(j["id"]): j for j in st["journals"]}
    for f in out["flagged"]:
        j = by.get(str(f["id"])) or {}
        f.update({"date": j.get("date"), "amount": j.get("amount"), "user": j.get("user"), "description": j.get("description")})
    return out


def caps(owner: str, ws: str, me: str, a: dict[str, Any]) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["holders"]:
        return {"empty": True}
    q: dict[str, Any] = {"holders": [{"name": h["name"], "shares": h["shares"]} for h in st["holders"]]}
    if a.get("raise") not in (None, ""):
        q.update({"raise": a["raise"], "pre_money": a.get("pre_money"), "investor": a.get("investor")})
    return _engine(owner, me, "cap_table", q)


def related(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["related"]:
        return {"empty": True, "related_transactions": []}
    tx = [{"id": t["id"], "date": t["date"], "counterparty": t["counterparty"], "amount": t["amount"], "direction": t["direction"]}
          for t in st["tx"] if t.get("counterparty")]
    return _engine(owner, me, "related_party", {"related": [r["name"] for r in st["related"]], "transactions": tx})


def obligations(owner: str, ws: str, me: str) -> dict[str, Any]:
    return _engine(owner, me, "obligations", {"workspace": ws})


def incidents(owner: str, ws: str) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    out = []
    for i, rec in enumerate(_inst(owner, ws).get("incidents") or []):
        rep = rec.get("reported") or {}
        clocks = []
        for c in rec.get("due") or []:
            due = datetime.fromisoformat(c["due"])
            done = rep.get(c["report"])
            clocks.append({**c, "reported": done, "hours_left": None if done else round((due - now).total_seconds() / 3600, 1),
                           "late": (not done and due < now) or bool(done and datetime.fromisoformat(done) > due)})
        out.append({"n": i + 1, **{k: rec.get(k) for k in ("title", "detected", "severity")}, "clocks": clocks,
                    "closed": all(c["reported"] for c in clocks)})
    return list(reversed(out))


def drafts_view(owner: str, ws: str, p: dict[str, Any]) -> list[dict[str, Any]]:
    from .fin import makerchecker as MC
    people = _people(owner, ws)
    nm = lambda k: (people.get(k) or {}).get("name") or k   # noqa: E731
    out = []
    for d in MC.drafts(owner, ws, {"person": p["id"]})["drafts"]:
        approves = [c for c in d["checks"] if c["verdict"] == "approve"]
        out.append({k: d[k] for k in ("id", "kind", "title", "state", "maker", "amount", "needs_checks", "hash")}
                   | {"maker_name": nm(d["maker"]), "approvals": len(approves), "made": (d["history"] or [{}])[0].get("at"),
                      "last": (d["history"] or [{}])[-1].get("at"), "for_me": _can_check(p, d)})
    return list(reversed(out))


def _can_check(p: dict[str, Any], d: dict[str, Any]) -> bool:
    makers = {h["by"] for h in d.get("history") or [] if "made" in h["did"] or "changed" in h["did"]} | {d.get("maker")}
    return ("checker" in p["roles"] and d["state"] == "waiting" and p["id"] not in makers
            and not any(c["by"] == p["id"] for c in d["checks"]))


def draft_one(owner: str, ws: str, p: dict[str, Any], did: str) -> dict[str, Any]:
    from .fin import makerchecker as MC
    d = next((x for x in MC.drafts(owner, ws, {"person": p["id"]})["drafts"] if x["id"] == did), None)
    if not d:
        raise InstDeskError("No such draft.")
    people = _people(owner, ws)
    nm = lambda k: (people.get(k) or {}).get("name") or k   # noqa: E731
    makers = {h["by"] for h in d["history"] if "made" in h["did"] or "changed" in h["did"]} | {d.get("maker")}
    out = {**d, "maker_name": nm(d["maker"]), "history": [{**h, "by_name": nm(h["by"])} for h in d["history"]],
           "checks": [{**c, "by_name": nm(c["by"])} for c in d["checks"]]}
    out["can"] = {"check": _can_check(p, d), "revise": "maker" in p["roles"] and d["state"] != "approved",
                  "score": d["kind"] == "sar" and bool({"mlro", "compliance"} & set(p["roles"]))}
    why = ""
    if d["state"] == "waiting" and not out["can"]["check"]:
        why = ("You made or changed this draft - another checker must check it." if p["id"] in makers
               else "You have already checked this text - a different checker is needed." if any(c["by"] == p["id"] for c in d["checks"])
               else "You do not hold the checker role." if "checker" not in p["roles"] else "")
    out["why_not_check"] = why
    out["scores"] = [{**s, "by_name": nm(s["by"])} for s in _inst(owner, ws).get("sar_scores") or [] if s["draft"] == did]
    return out


def _rule_defaults() -> dict[str, Any]:
    from .fin.desks import institution as IN
    return dict(IN.DEFAULT_RULES)


def today_view(owner: str, ws: str, p: dict[str, Any], me: str) -> dict[str, Any]:
    inst = _inst(owner, ws)
    st = _state(owner, ws)
    drafts = drafts_view(owner, ws, p)
    out: dict[str, Any] = {"me": p, "people": [{"id": k, **v} for k, v in (inst.get("people") or {}).items()],
                           "logins": st["logins"], "single_check_limit": inst.get("single_check_limit"),
                           "retention": inst.get("retention") or {}, "keys": [{k: x.get(k) for k in ("id", "scopes", "made", "revoked")}
                                                                             for x in inst.get("keys") or []],
                           "files": list(reversed(st["files"]))[:12], "clocks": st["clocks"] or DEFAULT_CLOCKS,
                           "clocks_yours": bool(st["clocks"]), "rules": st["rules"], "deadline_days": st["deadline_days"],
                           "appetite": st["appetite"], "period_end": st["period_end"], "usual_users": st["usual_users"],
                           "watch": st["watch"], "holders": st["holders"], "related": st["related"], "rule_defaults": _rule_defaults(),
                           "counts": {k: len(st[k]) for k in ("tx", "complaints", "risks", "vendors", "models", "exposures", "pbc",
                                                              "journals", "agenda", "holders", "related", "watch")}}
    out["drafts"] = {"waiting": len([d for d in drafts if d["state"] == "waiting"]), "approved": len([d for d in drafts if d["state"] == "approved"]),
                     "rejected": len([d for d in drafts if d["state"] == "rejected"]), "for_me": [d for d in drafts if d["for_me"]][:8],
                     "mine_waiting": [d for d in drafts if d["maker"] == p["id"] and d["state"] == "waiting"][:8],
                     "mine_rejected": [d for d in drafts if d["maker"] == p["id"] and d["state"] == "rejected"][:5],
                     "by_kind": {}}
    for d in drafts:
        out["drafts"]["by_kind"].setdefault(d["kind"], {"waiting": 0, "approved": 0, "rejected": 0})
        out["drafts"]["by_kind"][d["kind"]][d["state"]] = out["drafts"]["by_kind"][d["kind"]].get(d["state"], 0) + 1

    def safe(fn, *x):
        try:
            return fn(*x)
        except InstDeskError as e:
            return {"error": str(e)}
    ob = safe(obligations, owner, ws, me)
    am = safe(aml, owner, ws, me)
    rc = safe(rcsa, owner, ws, me)
    tp = safe(third, owner, ws, me)
    md = safe(model_inv, owner, ws, me)
    pb = safe(pbc, owner, ws, me)
    bd = safe(board, owner, ws, me)
    inc = incidents(owner, ws)
    wb = inst.get("whistle") or []
    alerts = am.get("alerts") or []
    by_rule: dict[str, int] = {}
    for x in alerts:
        by_rule[x["rule"]] = by_rule.get(x["rule"], 0) + 1
    out["areas"] = {
        "crime": {"alerts": len(alerts), "customers": am.get("customers_alerted") or 0, "tx": len(st["tx"]), "by_rule": by_rule,
                  "sar_waiting": len([d for d in drafts if d["kind"] == "sar" and d["state"] == "waiting"])},
        "compliance": {"obligations": len(ob.get("obligations") or []), "overdue": ob.get("overdue") or [], "gaps": ob.get("gaps") or [],
                       "complaints": len(st["complaints"])},
        "risk": {"risks": len(st["risks"]), "over": rc.get("over_appetite") or [], "incidents_open": len([i for i in inc if not i["closed"]]),
                 "critical_no_exit": tp.get("critical_without_exit_plan") or [], "models_overdue": md.get("overdue") or [],
                 "heat": rc.get("heat_map_impact_by_likelihood")},
        "audit": {"pbc_outstanding": pb.get("outstanding") or [], "pbc_late": pb.get("late") or [], "journals": len(st["journals"]),
                  "samples": len(st["samples"])},
        "governance": {"papers_missing": bd.get("papers_missing") or [], "open_actions": len(bd.get("open_actions") or []),
                       "whistle_open": len([w for w in wb if (w.get("status") or "open") != "closed"]), "holders": len(st["holders"])}}
    out["incidents"] = inc[:6]
    needs = []
    for d in out["drafts"]["for_me"]:
        needs.append({"say": f"Check: {d['title'] or KIND_SAY.get(d['kind'], d['kind'])} made by {d['maker_name']}", "go": f"drafts/{d['id']}"})
    for d in out["drafts"]["mine_rejected"]:
        needs.append({"say": f"Rejected - change and send again: {d['title'] or d['kind']}", "go": f"drafts/{d['id']}", "bad": True})
    for i in inc:
        for c in i["clocks"]:
            if not c["reported"] and c["hours_left"] is not None and c["hours_left"] < 0:
                needs.append({"say": f"{i['title']}: {c['report']} was due {datetime.fromisoformat(c['due']):%d %b %Y %H:%M}", "go": "risk", "bad": True})
            elif not c["reported"] and c["hours_left"] is not None and c["hours_left"] <= 24:
                needs.append({"say": f"{i['title']}: {c['report']} due in {c['hours_left']:.1f} hours", "go": "risk", "bad": c["hours_left"] <= 4})
    for o in out["areas"]["compliance"]["overdue"][:5]:
        needs.append({"say": f"Obligation overdue: {o}", "go": "compliance", "bad": True})
    if alerts:
        needs.append({"say": f"{len(alerts)} monitoring alert{'s' if len(alerts) != 1 else ''} on {am.get('customers_alerted')} customer{'s' if am.get('customers_alerted') != 1 else ''} for an analyst", "go": "crime"})
    for r in out["areas"]["risk"]["over"][:3]:
        needs.append({"say": f"Risk over your appetite: {r}", "go": "risk", "bad": True})
    for v in out["areas"]["risk"]["critical_no_exit"][:3]:
        needs.append({"say": f"Critical third party with no exit plan: {v}", "go": "risk"})
    for m in out["areas"]["risk"]["models_overdue"][:3]:
        needs.append({"say": f"Model validation overdue: {m}", "go": "risk"})
    for x in out["areas"]["audit"]["pbc_late"][:3]:
        needs.append({"say": f"Audit request late: {x}", "go": "audit"})
    for x in out["areas"]["governance"]["papers_missing"][:3]:
        needs.append({"say": f"Board paper missing: {x}", "go": "governance"})
    if out["areas"]["governance"]["whistle_open"]:
        needs.append({"say": f"{out['areas']['governance']['whistle_open']} whistleblowing case(s) open", "go": "governance"})
    if len(out["people"]) < 2:
        needs.append({"say": "Add a second person - a draft needs a checker who is not its maker", "go": "team"})
    elif not any("checker" in x["roles"] for x in out["people"]):
        needs.append({"say": "Nobody holds the checker role yet", "go": "team"})
    if out["single_check_limit"] is None:
        needs.append({"say": "Set the amount above which a draft needs two checkers", "go": "team"})
    out["needs"] = needs
    return out


def summary(tenant: str, want: str = "") -> dict[str, Any]:
    h = _hire()
    st = h.status(tenant, KEY)
    trust = ""
    xs = institutions(tenant)
    if st not in ("hired", "paused"):
        if not any(x.get("role") != "owner" for x in xs):
            return {"hired": False, "status": st, "say": "Institution is not hired. Hire it from AI Employees."}
    else:
        with session() as s:
            trust = h._view(h._row(s, tenant, KEY)).get("trust") or ""    # noqa: SLF001
    out: dict[str, Any] = {"hired": True, "status": st if st in ("hired", "paused") else "member",
                           "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
                           "institutions": xs, "workspace": workspace(tenant, want), "roles": ROLE_SAY, "kinds": KIND_SAY, "foot": FOOT}
    w = out["workspace"]
    if w:
        try:
            who = whoami(tenant, w["id"])
            out["is_owner"] = who["is_owner"]
            out["me"] = who["person"]
            out["people"] = [{"id": k, **v} for k, v in _people(who["owner"], w["id"]).items()]
            if who["person"]:
                out["desk"] = today_view(who["owner"], w["id"], who["person"], f"{who['person']['name']} <{tenant}>")
        except Exception as e:   # noqa: BLE001
            log.exception("institution desk read failed")
            out["desk_error"] = str(e)[:200]
    return out


READS = {"aml", "obligations", "complaints", "policy_check", "promotion_check", "kyc_review", "sanctions", "rcsa", "third_party", "models",
         "ecl", "pbc", "je_test", "board", "cap_table", "related", "drafts", "draft", "incidents", "whistle_list", "sample_list"}


def do(caller: str, part: str, a: dict[str, Any]) -> dict[str, Any]:
    """Every desk action: who she is on this institution first, then the engine AS that person on the OWNER's workspace."""
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    ws = str(a.get("workspace") or "")
    who = whoami(caller, ws)
    owner = who["owner"]
    if part == "be":      # the owner chooses which person of her institution she is on this desk
        if not who["is_owner"]:
            raise InstDeskError("Only the institution's owner switches person; an admin links your login to your person.")
        pid = str(a.get("person") or "")
        if pid not in _people(owner, ws):
            raise InstDeskError("No such person of the institution.")
        _put(owner, ws, lambda st: st["who"].__setitem__(caller, pid))
        forget(caller)
        _regreet(caller)
        return {"person": {"id": pid, **_people(owner, ws)[pid]}}
    p = who["person"]
    if not p:
        raise InstDeskError("You are not a person of this institution on the desk yet: an admin links your login on the Team page.")
    me = f"{p['name']} <{caller}>"
    base = {"workspace": ws, "person": p["id"]}
    keep = {k: v for k, v in a.items() if k not in ("workspace", "person")}
    st = lambda: _state(owner, ws)   # noqa: E731
    if part == "link":    # an admin links a person of the institution to a team member's login (email)
        if "admin" not in p["roles"]:
            raise InstDeskError("Only an admin links a login to a person.")
        pid, em = str(a.get("target") or ""), str(a.get("email") or "").strip().lower()[:120]
        if pid not in _people(owner, ws):
            raise InstDeskError("No such person of the institution.")
        if em and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", em):
            raise InstDeskError("email: the email of their Hoola account.")
        _put(owner, ws, lambda s: (s["logins"].__setitem__(pid, em) if em else s["logins"].pop(pid, None)))
        out: dict[str, Any] = {"logins": _state(owner, ws)["logins"],
                               "says": "Linked. Add them to this institution's team in Books & Accounts too, so they can open it."}
    elif part == "roles":   # an admin changes a person's roles (the engine has no such action: the desk keeps it on the same register)
        from .fin import makerchecker as MC
        if "admin" not in p["roles"]:
            raise InstDeskError("Only an admin changes roles.")
        pid = str(a.get("target") or "")
        roles = [r for r in a.get("roles") or [] if r in MC.ROLES]
        if not roles:
            raise InstDeskError("roles: at least one of " + ", ".join(MC.ROLES))

        def ch(s):
            if pid not in s.get("people", {}):
                raise InstDeskError("No such person of the institution.")
            if "admin" not in roles and not any("admin" in v["roles"] for k, v in s["people"].items() if k != pid):
                raise InstDeskError("The institution keeps at least one admin.")
            s["people"][pid]["roles"] = roles
            return {"id": pid, **s["people"][pid]}
        out = {"person": _inst_put(owner, ws, ch)}
        from .fin import evidence as EV
        EV.record(owner, ws, p["id"], "inst", f"roles of {pid} set to {roles}")
    elif part == "upload":
        out = upload(owner, ws, p, a)
    elif part == "clear":
        out = clear(owner, ws, p, a)
    elif part == "register":
        out = save_register(owner, ws, p, a)
    elif part == "settings":
        out = save_settings(owner, ws, p, a)
    elif part == "aml":
        out = aml(owner, ws, me)
    elif part == "sar_draft":   # a report from one alert: the transactions behind it come from her file; into maker-checker if she is a maker
        al = a.get("alert") or {}
        tx = _tx_for(st(), al.get("transactions") or [])
        q = {**base, "alert": al, "transactions": tx, "customer": a.get("customer") or {}, "actions_taken": a.get("actions_taken") or ""}
        if "maker" not in p["roles"]:
            q.pop("person")
        out = _engine(owner, me, "sar_draft", q)
        if "maker" not in p["roles"]:
            out["says"] = "A preview only: you do not hold the maker role, so it was not put into maker-checker. " + out.get("says", "")
    elif part == "sanctions":
        names = _lines(a.get("names"))
        out = _engine(owner, me, "sanctions", {"names": names, "watch": st()["watch"], "threshold": a.get("threshold", 0.7)})
    elif part in ("kyc_review", "policy_check", "promotion_check"):
        out = _engine(owner, me, part, keep)
    elif part == "obligations":
        out = obligations(owner, ws, me)
    elif part == "obligation_add":
        out = _engine(owner, me, "obligations", {**base, "add": [a.get("item") or {}]})
    elif part == "obligation_done":
        if not ({"compliance", "admin"} & set(p["roles"])):
            raise InstDeskError(f"{p['name']} does not hold the Compliance role.")
        i, on = int(_num(a.get("i"), "i", 0)), _day(a.get("on") or date.today().isoformat(), "on")

        def ch(s):
            ob = s.get("obligations") or []
            if i >= len(ob):
                raise InstDeskError("No such obligation.")
            ob[i]["last_done"] = on
            return ob[i]
        out = {"obligation": _inst_put(owner, ws, ch)}
        from .fin import evidence as EV
        EV.record(owner, ws, p["id"], "compliance", f"obligation done: {out['obligation']['name']} on {on}")
    elif part == "complaints":
        out = complaints(owner, ws, me)
    elif part == "incident":
        if not ({"risk", "compliance", "admin"} & set(p["roles"])):
            raise InstDeskError(f"{p['name']} does not hold the Risk or Compliance role.")
        clocks = a.get("clocks") or st()["clocks"] or DEFAULT_CLOCKS
        out = _engine(owner, me, "incident", {"workspace": ws, "title": a.get("title"), "detected": a.get("detected"),
                                              "severity": a.get("severity"), "clocks": clocks})
        if not a.get("clocks") and not st()["clocks"]:
            out["says"] = "Clocks from Hoola's starting hours (not confirmed - check this against your regulator's rules). " + out["says"]
    elif part == "incident_report":
        if not ({"risk", "compliance", "admin"} & set(p["roles"])):
            raise InstDeskError(f"{p['name']} does not hold the Risk or Compliance role.")
        n, rep = int(_num(a.get("n"), "n", 1)), _text(a.get("report"), 60)
        at = str(a.get("at") or datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="minutes"))[:16]
        try:
            datetime.fromisoformat(at)
        except ValueError:
            raise InstDeskError("at: when it was reported, YYYY-MM-DDTHH:MM.")

        def ch(s):
            inc = s.get("incidents") or []
            if not 1 <= n <= len(inc):
                raise InstDeskError("No such incident.")
            rec = inc[n - 1]
            if rep not in [c["report"] for c in rec.get("due") or []]:
                raise InstDeskError("No such report on this incident.")
            rec.setdefault("reported", {})[rep] = at
            return rec
        _inst_put(owner, ws, ch)
        out = {"incidents": incidents(owner, ws), "says": "Recorded when YOU reported it. Hoola reports nothing."}
    elif part == "incidents":
        out = {"incidents": incidents(owner, ws)}
    elif part == "rcsa":
        out = rcsa(owner, ws, me)
    elif part == "third_party":
        out = third(owner, ws, me)
    elif part == "models":
        out = model_inv(owner, ws, me)
    elif part == "ecl":
        out = ecl(owner, ws, me)
    elif part == "pbc":
        out = pbc(owner, ws, me)
    elif part == "sample":
        _need(p, "audit")
        src = str(a.get("from") or "list")
        s0 = st()
        pop = ([str(t["id"]) for t in s0["tx"]] if src == "transactions" else [str(j["id"]) for j in s0["journals"]] if src == "journals"
               else _lines(a.get("population")))
        q: dict[str, Any] = {"population": pop, "size": a.get("size")}
        if str(a.get("seed") or "").strip():
            q["seed"] = int(_num(a["seed"], "seed", 0))
        r = _engine(owner, me, "sample", q)
        rec = {"n": _next_n(s0["samples"]), "control": _text(a.get("control"), 120) or "Control", "from": src, "seed": r["seed"],
               "population": r["population"], "sample": r["sample"], "by": p["name"], "on": date.today().isoformat(), "results": {},
               "tolerated": int(_num(a.get("tolerated") or 0, "tolerated", 0))}
        _put(owner, ws, lambda s: s["samples"].append(rec))
        out = {"sample": rec, "says": r["says"]}
    elif part == "sample_list":
        out = {"samples": list(reversed(st()["samples"]))}
    elif part == "test_result":   # one sampled item: passed or failed with a note -> the control test's conclusion
        _need(p, "audit")
        n, item = int(_num(a.get("n"), "n", 1)), str(a.get("item") or "")

        def ch(s):
            for rec in s["samples"]:
                if rec["n"] == n:
                    if item not in rec["sample"]:
                        raise InstDeskError("That item is not in the sample.")
                    rec["results"][item] = {"passed": _yes(a.get("passed")), "note": _text(a.get("note"), 200)}
                    return rec
            raise InstDeskError("No such sample.")
        rec = _put(owner, ws, ch)
        out = {"sample": rec}
        if len(rec["results"]) == len(rec["sample"]):
            out["test"] = _engine(owner, me, "control_test", {"results": [{"item": k, **v} for k, v in rec["results"].items()],
                                                              "tolerated_failures": rec["tolerated"]})
            _put(owner, ws, lambda s: [x.__setitem__("conclusion", out["test"]["conclusion"]) for x in s["samples"] if x["n"] == n])
    elif part == "je_test":
        out = je(owner, ws, me)
    elif part == "board":
        out = board(owner, ws, me)
    elif part == "cap_table":
        out = caps(owner, ws, me, a)
    elif part == "related":
        out = related(owner, ws, me)
    elif part == "whistle":
        out = _engine(owner, me, "whistle", {"workspace": ws, **keep})    # a reporter's name or contact reaches the engine, which refuses it
    elif part == "whistle_status":
        if not ({"compliance", "admin"} & set(p["roles"])):
            raise InstDeskError(f"{p['name']} does not hold the Compliance role.")
        case, status = _text(a.get("case"), 20), str(a.get("status") or "")
        if status not in ("open", "looking", "closed"):
            raise InstDeskError("status: open | looking | closed.")

        def ch(s):
            for w in s.get("whistle") or []:
                if w["case"] == case:
                    w["status"] = status
                    w.setdefault("notes", []).append({"on": date.today().isoformat(), "status": status, "note": _text(a.get("note"), 300)})
                    return w
            raise InstDeskError("No such case.")
        out = {"case": _inst_put(owner, ws, ch)}
    elif part == "whistle_list":
        out = {"cases": list(reversed(_inst(owner, ws).get("whistle") or []))}
    elif part == "drafts":
        out = {"drafts": drafts_view(owner, ws, p)}
    elif part == "draft":
        out = draft_one(owner, ws, p, str(a.get("draft") or ""))
    elif part in ("submit", "revise", "check", "sar_score"):
        out = _engine(owner, me, part, {**base, **keep})
    elif part in ("person_add", "limits", "retention", "api_key"):
        out = _engine(owner, me, part, {**base, **keep})
    else:
        raise InstDeskError("Not an Institution desk action.")
    if part not in READS:
        forget(owner)
        forget(caller)
    return out


def draft_pdf(d: dict[str, Any], name: str) -> bytes:
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

    line(name, 13, True)
    line(f"{d.get('title') or KIND_SAY.get(d['kind'], d['kind'])} - {KIND_SAY.get(d['kind'], d['kind'])} - made by {d.get('maker_name')}", 11, True)
    y -= 4
    for ln in str(d.get("body") or "").splitlines():
        if ln.startswith("# "):
            line(ln[2:], 14, True)
        elif ln.startswith("## "):
            y -= 3
            line(ln[3:], 11, True)
        else:
            line(ln.replace("**", ""), 10)
    y -= 8
    ok = [c_ for c_ in d.get("checks") or [] if c_["verdict"] == "approve"]
    if d["state"] == "approved":
        line("APPROVED by " + ", ".join(f"{c_['by_name']} on {c_['at'][:10]}" for c_ in ok) + f" - text {d['hash'][:16]}", 9, True)
    else:
        line(f"{d['state'].upper()} - not approved. Text {d['hash'][:16]}.", 9, True)
    line(FOOT, 8)
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
        return ("I work for a regulated institution: financial crime, compliance, risk, audit and governance, with maker-checker on every "
                "draft. Hire me from AI Employees to start.")
    if not d.get("workspace"):
        return "Hello. Set up your institution on the desk first (its name, country, currency and you as the first admin)."
    if not d.get("me"):
        return "Hello. An admin needs to link your login to your person of the institution on the Team page."
    k = d.get("desk") or {}
    me = d["me"]
    bits = []
    if (k.get("drafts") or {}).get("for_me"):
        bits.append(f"{len(k['drafts']['for_me'])} draft(s) waiting for your check")
    ar = k.get("areas") or {}
    if (ar.get("crime") or {}).get("alerts"):
        bits.append(f"{ar['crime']['alerts']} monitoring alert(s)")
    if (ar.get("compliance") or {}).get("overdue"):
        bits.append(f"{len(ar['compliance']['overdue'])} obligation(s) overdue")
    if (ar.get("risk") or {}).get("incidents_open"):
        bits.append(f"{ar['risk']['incidents_open']} incident(s) with reports open")
    roles = ", ".join(ROLE_SAY.get(r, r) for r in me["roles"])
    return (f"Hello {me['name']} ({roles}). " + ("On the desk: " + ", ".join(bits) + ". " if bits else "")
            + "Ask me to read monitoring alerts, draft a suspicious-activity report, check a promotion or work out a sample. I prepare; "
              "your named people check, decide and file.")


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
        c = Conversation(tenant_id=tenant, kind=KIND, title="Institution chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False, delivered_to_agent=True))
    return {"id": cid, "new": True}


RULES = ("You are her Institution employee (financial crime, compliance, risk, audit, governance), talking in the desk's own chat (or a "
         "voice call started from it). Use the " + TOOL + " tool with workspace set to the institution below and person set to HER "
         "person id below - never another person's id: aml_triage, sar_draft (every amount and date from the transactions, no accusation "
         "words, the analyst's parts left blank), kyc_review, sanctions (against HER watch list only), obligations, policy_check, "
         "promotion_check, complaints_mi, incident (clocks from HER regulator's hours), rcsa, third_party, models, ecl, pbc, sample, "
         "control_test, je_test, board_pack, cap_table, related_party, whistle (never a reporter's name), submit / revise / check / drafts "
         "(maker-checker). The maker never checks their own draft, a check holds only for the exact text it read, and an amount over the "
         "single-check limit needs two checkers - the tool checks it; never work around it and never check a draft for anyone. Every "
         "figure you say comes from the tool or the desk below. Hoola files nothing, freezes nothing and reports nothing to a regulator: "
         "the named officer decides. Never ask for or keep a password, a key or a reporter's name. Plain English, short. Not legal advice. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<institution_desk>{RULES}Institution is not hired yet: tell her to hire it from AI Employees.</institution_desk>"
        elif not d.get("workspace"):
            txt = f"\n\n<institution_desk>{RULES}\nNo institution set up yet: ask her to set it up on the Institution desk.</institution_desk>"
        elif not d.get("me"):
            txt = (f"\n\n<institution_desk>{RULES}\nInstitution: {d['workspace']['name']} (workspace {d['workspace']['id']}). She is not "
                   "linked to a person of the institution yet: an admin links her login on the desk's Team page. Do not act as anyone."
                   "</institution_desk>")
        else:
            w, k, me = d["workspace"], d.get("desk") or {}, d["me"]
            ar, dr = k.get("areas") or {}, k.get("drafts") or {}
            people = ", ".join(f"{p['name']} ({p['id']}: {', '.join(p['roles'])})" for p in (d.get("people") or [])[:20])
            cr, co, ri, au, go = (ar.get(x) or {} for x in ("crime", "compliance", "risk", "audit", "governance"))
            txt = (f"\n\n<institution_desk>{RULES}\nInstitution: {w['name']} (workspace {w['id']}), {', '.join(w['countries'])}, "
                   f"currency {w['currency']}.\nShe is {me['name']} - person id {me['id']}, roles {', '.join(me['roles'])}."
                   f"\nPeople: {people}.\nSingle-check limit: {k.get('single_check_limit')}."
                   f"\nDrafts: {dr.get('waiting', 0)} waiting, {dr.get('approved', 0)} approved, {dr.get('rejected', 0)} rejected; "
                   f"{len(dr.get('for_me') or [])} waiting for her check."
                   f"\nFinancial crime: {cr.get('tx', 0)} transactions on file, {cr.get('alerts', 0)} alerts on {cr.get('customers', 0)} "
                   f"customers; {cr.get('sar_waiting', 0)} SAR drafts waiting."
                   f"\nCompliance: {co.get('obligations', 0)} obligations, overdue: {', '.join(co.get('overdue') or []) or 'none'}."
                   f"\nRisk: {ri.get('risks', 0)} risks, over appetite: {', '.join(ri.get('over') or []) or 'none'}; "
                   f"{ri.get('incidents_open', 0)} incidents with reports open; models overdue: {', '.join(ri.get('models_overdue') or []) or 'none'}."
                   f"\nAudit: {len(au.get('pbc_outstanding') or [])} requests outstanding, {au.get('samples', 0)} samples."
                   f"\nGovernance: papers missing: {', '.join(go.get('papers_missing') or []) or 'none'}; {go.get('whistle_open', 0)} "
                   "whistleblowing cases open.</institution_desk>")
    except Exception:   # noqa: BLE001
        log.exception("institution block failed")
        txt = f"\n\n<institution_desk>{RULES}The desk could not be read just now.</institution_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/institution/chat", dependencies=dep)
    def inst_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/institution/chat/new", dependencies=dep)
    def inst_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/institution/chat/{conv}/ok", dependencies=dep)
    def inst_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Institution chat")
        return {"ok": True}

    @router.get("/api/institution/desk", dependencies=dep)
    def inst_desk(workspace: str = "", tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant, workspace)

    @router.post("/api/institution/setup", dependencies=dep)
    def inst_setup(body: dict | None = None, tenant: str = Depends(current_tenant)):
        try:
            return setup(tenant, body or {})
        except ValueError as e:
            raise HTTPException(400, str(e))

    @router.post("/api/institution/do/{part}", dependencies=dep)
    def inst_do(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        from .fin import laws as L
        try:
            return do(tenant, part, body or {})
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    @router.get("/api/institution/download", dependencies=dep)
    def inst_download(workspace: str, what: str, draft: str = "", tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response
        try:
            who = whoami(tenant, workspace)
            if not who["person"]:
                raise InstDeskError("You are not a person of this institution on the desk yet.")
            name = next((b["name"] for b in institutions(tenant) if b["id"] == workspace), "Institution")
            if what == "draft":
                d = draft_one(who["owner"], workspace, who["person"], draft)
                return Response(draft_pdf(d, name), media_type="application/pdf",
                                headers={"Content-Disposition": f'attachment; filename="draft-{d["id"][:8]}.pdf"'})
            if what == "export":
                r = _engine(who["owner"], f"{who['person']['name']} <{tenant}>", "export", {"workspace": workspace, "person": who["person"]["id"]})
                return Response(r["file"], media_type="application/json",
                                headers={"Content-Disposition": 'attachment; filename="institution-registers.json"', "X-Sha256": r["sha256"]})
        except ValueError as e:
            raise HTTPException(400, str(e))
        raise HTTPException(400, "what: draft | export")

    @router.put("/api/institution/workspace", dependencies=dep)
    def inst_workspace(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return pick(tenant, str((body or {}).get("workspace") or ""))
        except InstDeskError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
