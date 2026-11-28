"""F9 maker-checker (FINANCE_GLOBAL_PLAN institution mode): every draft an institution makes - a SAR narrative, a policy, a board paper,
a return, a limit change - is made by one named person and checked by another before it counts. It cannot be bypassed:

  - a draft is made only by a person with the maker role, and checked only by a person with the checker role;
  - the checker is never the maker (nor the person who made any earlier version);
  - a check is bound to the text's hash: change the text and every check falls away;
  - an amount above her single-check limit needs TWO different checkers;
  - a stale read (the hash the checker saw is not the current one) is refused;
  - there is no action that sets a draft's state directly; state words in the arguments are ignored;
  - a draft of one workspace cannot be checked from another.

People and limits live in the workspace's settings (`inst`); drafts in fin_draft (meta: maker, checks, amount, history)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from . import evidence as EV


class MCError(ValueError):
    pass


ROLES = ("admin", "maker", "checker", "mlro", "compliance", "risk", "audit", "secretary", "viewer")


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def inst(w: dict[str, Any]) -> dict[str, Any]:
    return dict((w.get("settings") or {}).get("inst") or {})


def save(tenant: str, ws: str, change) -> Any:
    from .. import db
    from .models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != tenant:
            raise MCError("No such workspace.")
        st = json.loads(row.settings or "{}")
        out = change(st.setdefault("inst", {}))
        row.settings = json.dumps(st)
        s.commit()
    return out


def workspace(tenant: str, ws: str) -> dict[str, Any]:
    from .profile import ProfileError, get
    try:
        return get(tenant, ws)
    except ProfileError as e:
        raise MCError(str(e))


def person(tenant: str, ws: str, pid: Any, role: str = "") -> dict[str, Any]:
    p = (inst(workspace(tenant, ws)).get("people") or {}).get(str(pid or ""))
    if not p:
        raise MCError("person: who is doing this (a person of this institution - add them with person_add).")
    if role and role not in p["roles"]:
        raise MCError(f"{p['name']} does not hold the {role} role.")
    return {"id": str(pid), **p}


def person_add(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    roles = [r for r in a.get("roles") or [] if r in ROLES]
    if not roles:
        raise MCError("roles: " + ", ".join(ROLES))
    name = str(a.get("name") or "").strip()[:80]
    if not name:
        raise MCError("name: the person's name.")
    st = inst(workspace(tenant, ws))
    if st.get("people"):
        person(tenant, ws, a.get("person"), "admin")
    elif "admin" not in roles:
        raise MCError("The first person of an institution is an admin.")
    pid = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")[:40]

    def ch(s):
        if pid in s.setdefault("people", {}):
            raise MCError(f"{name} is already here.")
        s["people"][pid] = {"name": name, "roles": roles}
        return {"id": pid, "name": name, "roles": roles}
    out = save(tenant, ws, ch)
    EV.record(tenant, ws, str(a.get("person") or pid), "inst", f"person added: {name} {roles}")
    return {"person": out}


def limits(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    person(tenant, ws, a.get("person"), "admin")
    try:
        lim = float(a.get("single_check_limit"))
    except (TypeError, ValueError):
        raise MCError("single_check_limit: the amount above which two checkers are needed.")
    save(tenant, ws, lambda s: s.__setitem__("single_check_limit", lim))
    EV.record(tenant, ws, str(a.get("person")), "inst", f"single-check limit set to {lim}")
    return {"single_check_limit": lim}


def _row(d) -> dict[str, Any]:
    m = json.loads(d.meta or "{}")
    return {"id": d.id, "kind": d.kind, "title": m.get("title", ""), "body": d.body, "hash": d.hash, "state": d.state,
            "maker": m.get("maker"), "amount": m.get("amount"), "checks": [c for c in m.get("checks", []) if c["hash"] == d.hash],
            "needs_checks": m.get("needs", 1), "history": m.get("history", [])}


def submit(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    from .. import db
    from .models import FinDraft, ensure
    p = person(tenant, ws, a.get("person"), "maker")
    body = str(a.get("body") or "").strip()
    if not body:
        raise MCError("body: the text of the draft.")
    amount = a.get("amount")
    lim = inst(workspace(tenant, ws)).get("single_check_limit")
    needs = 2 if (amount is not None and lim is not None and float(amount) > float(lim)) else 1
    ensure()
    with db.session() as s:
        d = FinDraft(tenant_id=tenant, workspace_id=ws, kind=str(a.get("kind") or "draft")[:24], body=body, hash=_h(body), state="waiting",
                     meta=json.dumps({"title": str(a.get("title") or "")[:160], "maker": p["id"], "makers": [p["id"]], "checks": [],
                                      "amount": amount, "needs": needs, "history": [{"at": _now(), "by": p["id"], "did": "made", "hash": _h(body)}]}))
        s.add(d)
        s.flush()
        out = _row(d)
        s.commit()
    EV.record(tenant, ws, p["id"], "maker", f"draft made: {out['kind']}", {"hash": out["hash"]})
    return {"draft": out, "says": f"Waiting for {needs} checker{'s' if needs > 1 else ''}; the maker cannot check it."}


def _open(tenant: str, ws: str, did: Any, fn) -> dict[str, Any]:
    from .. import db
    from .models import FinDraft, ensure
    ensure()
    with db.session() as s:
        d = s.get(FinDraft, str(did or ""))
        if not d or d.tenant_id != tenant or d.workspace_id != ws:
            raise MCError("No such draft in this workspace.")
        m = json.loads(d.meta or "{}")
        fn(d, m)
        d.meta = json.dumps(m)
        s.commit()
        return _row(d)


def revise(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    p = person(tenant, ws, a.get("person"), "maker")
    body = str(a.get("body") or "").strip()
    if not body:
        raise MCError("body: the new text.")

    def fn(d, m):
        if d.state == "approved":
            raise MCError("An approved draft is not changed: make a new one.")
        d.body, d.hash, d.state = body, _h(body), "waiting"
        m.setdefault("makers", []).append(p["id"])
        m["history"].append({"at": _now(), "by": p["id"], "did": "changed - every check falls away", "hash": d.hash})
    out = _open(tenant, ws, a.get("draft"), fn)
    EV.record(tenant, ws, p["id"], "maker", "draft changed", {"hash": out["hash"]})
    return {"draft": out}


def check(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    p = person(tenant, ws, a.get("person"), "checker")
    verdict = a.get("verdict")
    if verdict not in ("approve", "reject"):
        raise MCError("verdict: approve | reject.")
    seen = str(a.get("hash") or "")

    def fn(d, m):
        if p["id"] in (m.get("makers") or [m.get("maker")]):
            raise MCError("A maker of this draft cannot check it.")
        if d.state != "waiting":
            raise MCError(f"This draft is {d.state}, not waiting for a check.")
        if seen != d.hash:
            raise MCError("The text you read is not the current text: read it again (send its hash).")
        live = [c for c in m.get("checks", []) if c["hash"] == d.hash]
        if any(c["by"] == p["id"] for c in live):
            raise MCError("You have already checked this text: a different checker is needed.")
        if verdict == "reject" and not str(a.get("reason") or "").strip():
            raise MCError("reason: why it is rejected.")
        m.setdefault("checks", []).append({"by": p["id"], "verdict": verdict, "hash": d.hash, "at": _now(),
                                           "reason": str(a.get("reason") or "")[:500]})
        if verdict == "reject":
            d.state = "rejected"
        elif len([c for c in m["checks"] if c["hash"] == d.hash and c["verdict"] == "approve"]) >= int(m.get("needs", 1)):
            d.state = "approved"
            d.approved_by = ",".join(c["by"] for c in m["checks"] if c["hash"] == d.hash and c["verdict"] == "approve")
        m["history"].append({"at": _now(), "by": p["id"], "did": verdict, "hash": d.hash})
    out = _open(tenant, ws, a.get("draft"), fn)
    EV.record(tenant, ws, p["id"], "checker", f"draft {verdict}", {"hash": out["hash"]})
    return {"draft": out}


def drafts(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    from .. import db
    from .models import FinDraft, ensure
    person(tenant, ws, a.get("person"))
    ensure()
    with db.session() as s:
        q = s.query(FinDraft).filter(FinDraft.tenant_id == tenant, FinDraft.workspace_id == ws)
        if a.get("state"):
            q = q.filter(FinDraft.state == str(a["state"]))
        return {"drafts": [_row(d) for d in q.order_by(FinDraft.created_at).limit(500)]}


def is_approved(tenant: str, ws: str, did: str) -> bool:
    from .. import db
    from .models import FinDraft, ensure
    ensure()
    with db.session() as s:
        d = s.get(FinDraft, did)
        if not d or d.tenant_id != tenant or d.workspace_id != ws or d.state != "approved":
            return False
        m = json.loads(d.meta or "{}")
        ok = [c for c in m.get("checks", []) if c["hash"] == d.hash and c["verdict"] == "approve" and c["by"] not in m.get("makers", [])]
        return len({c["by"] for c in ok}) >= int(m.get("needs", 1)) and _h(d.body) == d.hash
