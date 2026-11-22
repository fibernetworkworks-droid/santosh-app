"""F7 of docs/FINANCE_GLOBAL_PLAN.md - Firm mode (tool `firm_practice`): an accounting, tax or advisory firm runs its clients in one
account. The firm is a workspace of size `firm`; each client is a client book inside it (its own workspace, parent = the firm).

Every action is done AS a named person of the firm (`person`), and what that person may see is checked in code on every call:
  partner / manager   every client of the firm
  preparer / reviewer the clients they are assigned to (or all, if the partner said so)
  client              their own client book only - never another client's name, figures, requests or drafts

  person_add   a person of the firm: name, role, clients (for a client: their one book; for staff: their assigned clients or "all").
  client_add   a new client book inside the firm (name, size, countries, currency).
  clients      the client switcher: the clients this person may see, with what is open for each.
  engagement   an engagement letter for a client (services, fee, period, terms) - a draft that goes through review like any other.
  request      ask a client for papers (items, due date); provide = the client marks an item sent (only on their own request).
  portal       a client's own page: their requests, the drafts shared with them, their dates. Nothing of anyone else.
  draft        a preparer makes a draft for a client (tax return, accounts, letter, suitability, plan, memo, cfo pack ...). The body is
               hashed; the named signer is set on the draft.
  review       a reviewer approves it or sends it back with notes. The preparer can never review their own draft; a client never reviews.
               An approval holds only for the exact text: change the body and it goes back to review.
  sign         only the named signer, only on the approved text; the signature records who, when and the text's hash.
  share        a signed draft is shared to the client's portal.
  queue        the review queue for this person; dashboard: the firm's view (per client and per preparer).
  audit        one client's audit trail (who did what, in order, hash-linked).
  factfind     an adviser's fact-find for a client: the answers given, what is still missing.
  meeting      meeting notes read for actions, decisions and dates.
  suitability  a suitability-report draft from the fact-find and HER recommendation: required parts present or named missing.
  drift        a portfolio against its target mix (rebalancing drift).
  cfo_pack     a fractional-CFO pack for a client from their own books: profit and loss, balance sheet, cash forecast.

Hoola prepares; the firm's named people review and sign. Not advice."""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from typing import Any

from .. import evidence as EV
from .. import laws as L


class FirmError(ValueError):
    pass


STAFF = ("partner", "manager", "preparer", "reviewer")
ROLES = STAFF + ("client",)
REVIEWERS = ("partner", "manager", "reviewer")
KINDS = ("tax_return", "accounts", "letter", "engagement", "suitability", "plan", "memo", "cfo_pack", "other")
SUITABILITY_PARTS = ("client objectives", "risk profile", "capacity for loss", "time horizon", "knowledge and experience",
                     "recommendation", "why it suits the client", "costs and charges", "risks", "alternatives considered")
FACTFIND = ("full_name", "date_of_birth", "dependants", "income", "spending", "assets", "debts", "objectives", "time_horizon",
            "attitude_to_risk", "capacity_for_loss", "knowledge_experience", "health", "existing_cover")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ---- storage --------------------------------------------------------------------------------------------------------------

def _firm(tenant: str, firm: str) -> dict[str, Any]:
    from ..profile import ProfileError, get
    try:
        w = get(tenant, firm)
    except ProfileError as e:
        raise FirmError(str(e))
    if w["size"] != "firm":
        raise FirmError("firm: this workspace is not a firm (set it up with size firm).")
    return w


def _state(w: dict[str, Any]) -> dict[str, Any]:
    return dict((w.get("settings") or {}).get("practice") or {})


def _save(tenant: str, firm: str, change) -> Any:
    from ... import db
    from ..models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, firm)
        if not row or row.tenant_id != tenant:
            raise FirmError("No such workspace.")
        st = json.loads(row.settings or "{}")
        out = change(st.setdefault("practice", {}))
        row.settings = json.dumps(st)
        s.commit()
    return out


def _clients(tenant: str, firm: str) -> dict[str, dict[str, Any]]:
    from ... import db
    from ..models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        return {w.id: {"id": w.id, "name": w.name, "currency": w.currency, "countries": json.loads(w.countries or "[]")}
                for w in s.query(FinWorkspace).filter(FinWorkspace.tenant_id == tenant, FinWorkspace.parent_id == firm,
                                                      FinWorkspace.status == "active").order_by(FinWorkspace.created_at)}


# ---- who may see what ----------------------------------------------------------------------------------------------------

def _person(st: dict[str, Any], pid: Any) -> dict[str, Any]:
    p = (st.get("people") or {}).get(str(pid or ""))
    if not p:
        raise FirmError("person: who is doing this (a person of the firm - add them with person_add).")
    return {"id": str(pid), **p}


def _sees(p: dict[str, Any], client: str) -> bool:
    if p["role"] in ("partner", "manager"):
        return True
    return p.get("clients") == "all" or client in (p.get("clients") or [])


def _need(p: dict[str, Any], client: str, all_clients: dict[str, Any]) -> None:
    if client not in all_clients or not _sees(p, client):
        raise FirmError("No such client for this person.")          # the same words whether it exists or not: nothing leaks


def _staff(p: dict[str, Any], roles: tuple[str, ...] = STAFF) -> None:
    if p["role"] not in roles:
        raise FirmError(f"Only {', '.join(roles)} can do this.")


# ---- people and clients ---------------------------------------------------------------------------------------------------

def person_add(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    st = _state(w)
    role = a.get("role")
    if role not in ROLES:
        raise FirmError("role: " + " | ".join(ROLES))
    name = str(a.get("name") or "").strip()[:80]
    if not name:
        raise FirmError("name: the person's name.")
    if st.get("people"):                                   # after the first partner, only a partner adds people
        _staff(_person(st, a.get("person")), ("partner",))
    elif role != "partner":
        raise FirmError("The first person of a firm is a partner.")
    cl = a.get("clients")
    all_cl = _clients(tenant, firm)
    if role == "client":
        if not isinstance(cl, list) or len(cl) != 1 or cl[0] not in all_cl:
            raise FirmError("clients: a client person belongs to exactly one client book of this firm.")
    elif cl not in (None, "all") and not (isinstance(cl, list) and all(c in all_cl for c in cl)):
        raise FirmError("clients: a list of this firm's client books, or all.")
    pid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]

    def ch(s):
        ppl = s.setdefault("people", {})
        if pid in ppl:
            raise FirmError(f"{name} is already a person of the firm.")
        ppl[pid] = {"name": name, "role": role, "clients": cl if cl is not None else ([] if role != "partner" else "all")}
        return {"id": pid, **ppl[pid]}
    out = _save(tenant, firm, ch)
    EV.record(tenant, firm, str(a.get("person") or pid), "practice", f"person added: {name} ({role})")
    return {"person": out}


def client_add(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    from .. import profile as PR
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    _staff(p, ("partner", "manager"))
    name = str(a.get("name") or "").strip()
    if not name:
        raise FirmError("name: the client's name.")
    size = a.get("size") or "business"
    if size not in ("personal", "solo", "business"):
        raise FirmError("size: personal | solo | business.")
    countries = a.get("countries") or w["countries"]
    ans = {**PR.preview({"size": size, "countries": countries, "wants": [], "people": []})["answers"],
           "currency": a.get("currency") or w["currency"], "name": name}
    c = PR.apply(tenant, ans, PR.preview(ans)["hash"], parent_id=firm, actor=p["id"])
    EV.record(tenant, c["id"], p["id"], "practice", f"client book opened: {name}")
    return {"client": {"id": c["id"], "name": c["name"], "currency": c["currency"], "countries": c["countries"]}}


def clients(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    st = _state(w)
    p = _person(st, a.get("person"))
    all_cl = _clients(tenant, firm)
    drafts = _drafts(tenant, firm)
    out = []
    for cid, c in all_cl.items():
        if not _sees(p, cid):
            continue
        reqs = [r for r in st.get("requests") or [] if r["client"] == cid]
        items = [i for r in reqs for i in r["items"] if not i.get("sent")]
        ds = [d for d in drafts if d["client"] == cid]
        out.append({**c, "papers_outstanding": len(items),
                    "drafts_waiting_review": sum(d["state"] == "waiting" for d in ds),
                    "drafts_to_sign": sum(d["state"] == "approved" and not d.get("signed") for d in ds)})
    return {"person": p["name"], "role": p["role"], "clients": out}


# ---- requests and the portal ----------------------------------------------------------------------------------------------

def request(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    _staff(p)
    cid = str(a.get("client") or "")
    _need(p, cid, _clients(tenant, firm))
    items = [{"item": str(x)[:120], "sent": False} for x in a.get("items") or [] if str(x).strip()]
    if not items:
        raise FirmError("items: the papers asked for.")
    due = str(a.get("due") or "")[:10]

    def ch(s):
        rs = s.setdefault("requests", [])
        rid = f"rq{len(rs) + 1}"
        rs.append({"id": rid, "client": cid, "items": items, "due": due, "by": p["id"], "on": date.today().isoformat()})
        return rid
    rid = _save(tenant, firm, ch)
    EV.record(tenant, cid, p["id"], "practice", f"papers asked for ({len(items)})")
    return {"request": rid, "items": items, "due": due, "says": "The client sees this on their portal. Hoola sends no message."}


def provide(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    rid, item = str(a.get("request") or ""), str(a.get("item") or "")

    def ch(s):
        r = next((x for x in s.get("requests") or [] if x["id"] == rid), None)
        if not r or not _sees(p, r["client"]):
            raise FirmError("No such request for this person.")
        it = next((i for i in r["items"] if i["item"].lower() == item.lower()), None)
        if not it:
            raise FirmError(f"item: one of {', '.join(i['item'] for i in r['items'])}.")
        it["sent"] = True
        it["sent_on"] = date.today().isoformat()
        return r["client"]
    cid = _save(tenant, firm, ch)
    EV.record(tenant, cid, p["id"], "practice", f"paper sent: {item[:60]}")
    return {"request": rid, "item": item, "sent": True}


def portal(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    st = _state(w)
    p = _person(st, a.get("person"))
    all_cl = _clients(tenant, firm)
    cid = str((p.get("clients") or [""])[0] if p["role"] == "client" else a.get("client") or "")
    _need(p, cid, all_cl)
    reqs = [{"id": r["id"], "due": r["due"], "items": r["items"]} for r in st.get("requests") or [] if r["client"] == cid]
    shared = [{"id": d["id"], "kind": d["kind"], "title": d["title"], "body": d["body"], "signed": d["signed"]}
              for d in _drafts(tenant, firm) if d["client"] == cid and d.get("shared")]
    from .. import models as M
    from ... import db
    with db.session() as s:
        dates = [{"what": o.title, "due": o.due} for o in s.query(M.FinObligation).filter(
            M.FinObligation.tenant_id == tenant, M.FinObligation.workspace_id == cid).all()] if hasattr(M, "FinObligation") else []
    return {"client": all_cl[cid]["name"], "requests": reqs, "shared_with_you": shared, "dates": dates}


# ---- drafts, review, signing ------------------------------------------------------------------------------------------------

def _m(d) -> dict[str, Any]:
    return json.loads(d.meta or "{}")


def _row(d) -> dict[str, Any]:
    m = _m(d)
    return {"id": d.id, "client": d.workspace_id, "kind": d.kind, "title": m.get("title", ""), "body": d.body, "hash": d.hash,
            "state": d.state, "prepared_by": m.get("prepared_by"), "signer": m.get("signer"), "reviews": m.get("reviews", []),
            "signed": m.get("signature"), "shared": bool(m.get("shared")), "approved_by": d.approved_by}


def _drafts(tenant: str, firm: str) -> list[dict[str, Any]]:
    from ... import db
    from ..models import FinDraft, ensure
    ensure()
    ids = list(_clients(tenant, firm))
    if not ids:
        return []
    with db.session() as s:
        return [_row(d) for d in s.query(FinDraft).filter(FinDraft.tenant_id == tenant, FinDraft.workspace_id.in_(ids))
                .order_by(FinDraft.created_at).all()]


def _on_draft(tenant: str, firm: str, p: dict[str, Any], did: Any, fn) -> dict[str, Any]:
    """Open the draft (only one this person may see), let fn change it, commit, return its row."""
    from ... import db
    from ..models import FinDraft, ensure
    ensure()
    all_cl = _clients(tenant, firm)
    with db.session() as s:
        d = s.get(FinDraft, str(did or ""))
        if not d or d.tenant_id != tenant or d.workspace_id not in all_cl or not _sees(p, d.workspace_id):
            raise FirmError("No such draft for this person.")
        fn(d)
        s.commit()
        return _row(d)


def draft(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    from ... import db
    from ..models import FinDraft, ensure
    w = _firm(tenant, firm)
    st = _state(w)
    p = _person(st, a.get("person"))
    _staff(p)
    cid = str(a.get("client") or "")
    _need(p, cid, _clients(tenant, firm))
    kind = a.get("kind") or "other"
    if kind not in KINDS:
        raise FirmError("kind: " + " | ".join(KINDS))
    body = str(a.get("body") or "").strip()
    if not body:
        raise FirmError("body: the text of the draft.")
    signer = str(a.get("signer") or "")
    sp = (st.get("people") or {}).get(signer)
    if not sp or sp["role"] not in ("partner", "manager") or not _sees({"id": signer, **sp}, cid):
        raise FirmError("signer: the named partner or manager who will sign it (and who looks after this client).")
    ensure()
    with db.session() as s:
        d = FinDraft(tenant_id=tenant, workspace_id=cid, kind=kind, body=body, hash=_hash(body), state="waiting",
                     meta=json.dumps({"title": str(a.get("title") or kind)[:120], "prepared_by": p["id"], "signer": signer, "reviews": []}))
        s.add(d)
        s.flush()
        out = _row(d)
        s.commit()
    EV.record(tenant, cid, p["id"], "practice", f"draft made: {kind}", {"hash": out["hash"]})
    return {"draft": out, "says": f"Waiting for review; {sp['name']} signs it once it is approved."}


def edit(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    _staff(p)
    seen: dict[str, str] = {}

    def change(d):
        m = _m(d)
        if m.get("signature"):
            raise FirmError("A signed draft is not changed: make a new one.")
        body = str(a.get("body") or "").strip()
        if not body:
            raise FirmError("body: the new text.")
        d.body, d.hash = body, _hash(body)
        seen["was"] = d.state
        d.state, d.approved_by = "waiting", ""
    out = _on_draft(tenant, firm, p, a.get("draft"), change)
    was = seen["was"]
    EV.record(tenant, out["client"], p["id"], "practice", "draft changed" + (" after approval: back to review" if was == "approved" else ""))
    return {"draft": out, "says": "Changed: it goes back to review." if was != "waiting" else "Changed."}


def review(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    _staff(p, REVIEWERS)
    verdict = a.get("verdict")
    if verdict not in ("approve", "send_back"):
        raise FirmError("verdict: approve | send_back.")

    def change(d):
        m = _m(d)
        if m.get("prepared_by") == p["id"]:
            raise FirmError("The person who prepared a draft cannot review it: another reviewer must.")
        if d.state != "waiting":
            raise FirmError(f"This draft is {d.state}, not waiting for review.")
        if a.get("hash") and a["hash"] != d.hash:
            raise FirmError("The text changed since you read it: read it again.")
        notes = str(a.get("notes") or "")[:2000]
        if verdict == "send_back" and not notes:
            raise FirmError("notes: what needs changing.")
        m.setdefault("reviews", []).append({"by": p["id"], "verdict": verdict, "notes": notes, "hash": d.hash,
                                            "on": date.today().isoformat()})
        d.meta = json.dumps(m)
        d.state = "approved" if verdict == "approve" else "sent_back"
        d.approved_by = p["id"] if verdict == "approve" else ""
    out = _on_draft(tenant, firm, p, a.get("draft"), change)
    EV.record(tenant, out["client"], p["id"], "practice", f"draft {verdict.replace('_', ' ')}", {"hash": out["hash"]})
    return {"draft": out}


def sign(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    st = _state(w)
    p = _person(st, a.get("person"))

    def change(d):
        m = _m(d)
        if m.get("signer") != p["id"]:
            raise FirmError(f"Only the named signer ({(st['people'].get(m.get('signer')) or {}).get('name', '?')}) can sign this draft.")
        if d.state != "approved":
            raise FirmError("Only an approved draft is signed.")
        last = (m.get("reviews") or [{}])[-1]
        if last.get("verdict") != "approve" or last.get("hash") != d.hash:
            raise FirmError("The approval was for another text: it must be reviewed again.")
        if m.get("signature"):
            raise FirmError("Already signed.")
        m["signature"] = {"by": p["id"], "name": p["name"], "role": p["role"], "on": date.today().isoformat(), "hash": d.hash}
        d.meta = json.dumps(m)
        d.state = "signed"
    out = _on_draft(tenant, firm, p, a.get("draft"), change)
    EV.record(tenant, out["client"], p["id"], "practice", f"draft signed by {p['name']}", {"hash": out["hash"]})
    return {"draft": out, "says": f"Signed by {p['name']} ({p['role']}) on the approved text."}


def share(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    _staff(p, ("partner", "manager"))

    def change(d):
        m = _m(d)
        if not m.get("signature"):
            raise FirmError("Only a signed draft is shared with the client.")
        m["shared"] = True
        d.meta = json.dumps(m)
    out = _on_draft(tenant, firm, p, a.get("draft"), change)
    EV.record(tenant, out["client"], p["id"], "practice", "shared with the client")
    return {"draft": out}


def queue(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    _staff(p)
    all_cl = _clients(tenant, firm)
    ds = [d for d in _drafts(tenant, firm) if _sees(p, d["client"])]
    return {"to_review": [{**_brief(d), "client": all_cl[d["client"]]["name"]} for d in ds
                          if d["state"] == "waiting" and d["prepared_by"] != p["id"] and p["role"] in REVIEWERS],
            "to_sign": [{**_brief(d), "client": all_cl[d["client"]]["name"]} for d in ds if d["state"] == "approved" and d["signer"] == p["id"]],
            "sent_back_to_me": [{**_brief(d), "client": all_cl[d["client"]]["name"], "notes": d["reviews"][-1]["notes"]} for d in ds
                                if d["state"] == "sent_back" and d["prepared_by"] == p["id"]]}


def _brief(d: dict[str, Any]) -> dict[str, Any]:
    return {"id": d["id"], "kind": d["kind"], "title": d["title"], "state": d["state"]}


def dashboard(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    st = _state(w)
    p = _person(st, a.get("person"))
    _staff(p, ("partner", "manager"))
    all_cl = _clients(tenant, firm)
    ds = _drafts(tenant, firm)
    today = str(a.get("today") or date.today().isoformat())
    per = defaultdict(lambda: defaultdict(int))
    for d in ds:
        per[d["prepared_by"]][d["state"]] += 1
    overdue = [{"client": all_cl[r["client"]]["name"], "due": r["due"], "missing": [i["item"] for i in r["items"] if not i["sent"]]}
               for r in st.get("requests") or [] if r["due"] and r["due"] < today and any(not i["sent"] for i in r["items"])
               and r["client"] in all_cl]
    return {"clients": len(all_cl), "drafts": {k: sum(d["state"] == k for d in ds) for k in ("waiting", "sent_back", "approved", "signed")},
            "by_preparer": {k: dict(v) for k, v in per.items()}, "papers_overdue": overdue,
            "people": {k: v["role"] for k, v in (st.get("people") or {}).items()}}


def audit(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    _staff(p, ("partner", "manager", "reviewer"))
    cid = str(a.get("client") or "")
    _need(p, cid, _clients(tenant, firm))
    ev = [e for e in EV.events(tenant, cid, limit=int(a.get("limit") or 500)) if e["workspace_id"] == cid]
    return {"client": cid, "events": ev, "chain": EV.verify(tenant)}


# ---- adviser and practice parts ----------------------------------------------------------------------------------------------

def factfind(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    _staff(p)
    cid = str(a.get("client") or "")
    _need(p, cid, _clients(tenant, firm))
    given = {k: v for k, v in (a.get("answers") or {}).items() if k in FACTFIND and str(v).strip()}

    def ch(s):
        ff = s.setdefault("factfinds", {}).setdefault(cid, {})
        ff.update({k: str(v)[:500] for k, v in given.items()})
        return dict(ff)
    ff = _save(tenant, firm, ch)
    if given:
        EV.record(tenant, cid, p["id"], "practice", f"fact-find updated ({len(given)} answers)")
    return {"factfind": ff, "missing": [k for k in FACTFIND if k not in ff]}


_ACTION = re.compile(r"^\s*(?:[-*]\s*)?(?:action|todo|to do|follow[- ]?up)\s*[:\-]\s*(.+)$", re.I | re.M)
_DECIDE = re.compile(r"^\s*(?:[-*]\s*)?(?:decided|decision|agreed)\s*[:\-]\s*(.+)$", re.I | re.M)
_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def meeting(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    _staff(p)
    cid = str(a.get("client") or "")
    _need(p, cid, _clients(tenant, firm))
    t = str(a.get("text") or "")
    if not t.strip():
        raise FirmError("text: the meeting notes.")
    acts = [{"action": x.strip(), "due": (_DATE.search(x) or [None])[0] if _DATE.search(x) else None} for x in _ACTION.findall(t)]
    out = {"actions": acts, "decisions": [x.strip() for x in _DECIDE.findall(t)], "dates": sorted(set(_DATE.findall(t))),
           "says": "Read from lines starting 'Action:' / 'Decided:'; check nothing was missed."}
    EV.record(tenant, cid, p["id"], "practice", f"meeting notes read ({len(acts)} actions)")
    return out


def suitability(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _firm(tenant, firm)
    st = _state(w)
    p = _person(st, a.get("person"))
    _staff(p)
    cid = str(a.get("client") or "")
    _need(p, cid, _clients(tenant, firm))
    rec = str(a.get("recommendation") or "").strip()
    if not rec:
        raise FirmError("recommendation: the adviser's own recommendation - Hoola never makes one.")
    ff = (st.get("factfinds") or {}).get(cid) or {}
    parts = {k: str(v) for k, v in (a.get("parts") or {}).items()}
    parts["recommendation"] = rec
    for k, f in (("client objectives", "objectives"), ("risk profile", "attitude_to_risk"), ("capacity for loss", "capacity_for_loss"),
                 ("time horizon", "time_horizon"), ("knowledge and experience", "knowledge_experience")):
        if k not in parts and ff.get(f):
            parts[k] = ff[f] + " (from the fact-find)"
    missing = [k for k in SUITABILITY_PARTS if not parts.get(k)]
    body = "# Suitability report (DRAFT)\n\n" + "\n\n".join(f"## {k.capitalize()}\n{parts.get(k) or '[ to be written ]'}" for k in SUITABILITY_PARTS)
    out = {"body": body, "missing": missing, "factfind_missing": [k for k in FACTFIND if k not in ff]}
    if a.get("signer"):
        out["draft"] = draft(tenant, firm, {"person": p["id"], "client": cid, "kind": "suitability", "title": "Suitability report",
                                            "body": body, "signer": a["signer"]})["draft"]
    return {**out, "says": "The adviser writes the recommendation and signs; parts still missing are named."}


def drift(a: dict[str, Any]) -> dict[str, Any]:
    from ...riskdesk import orders as O
    try:
        return O.drift(a.get("holdings") or [], a.get("targets"), a.get("tolerance_pct", 5))
    except ValueError as e:
        raise FirmError(str(e))


def cfo_pack(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    from . import books as B
    from . import cash as CS
    w = _firm(tenant, firm)
    p = _person(_state(w), a.get("person"))
    _staff(p)
    cid = str(a.get("client") or "")
    _need(p, cid, _clients(tenant, firm))
    since, upto = str(a.get("since") or f"{date.today().year}-01-01"), str(a.get("upto") or date.today().isoformat())
    rep = B.reports(tenant, cid, since, upto)
    try:
        fc = CS.run(tenant, "forecast", {"workspace": cid, "start": upto})
        cash = {"lowest": fc["lowest"], "view_30_60_90": fc["view_30_60_90"], "under_minimum_weeks": fc["under_minimum_weeks"]}
    except Exception as e:
        cash = {"not_available": str(e)[:200]}
    EV.record(tenant, cid, p["id"], "practice", "cfo pack made")
    return {"profit_and_loss": rep["profit_and_loss"], "balance_sheet": rep["balance_sheet"], "cash": cash,
            "says": "From the client's own books; for the partner's review before it goes to the client."}


# ---- door --------------------------------------------------------------------------------------------------------------------

ACTIONS = ("person_add", "client_add", "clients", "engagement", "request", "provide", "portal", "draft", "edit", "review", "sign",
           "share", "queue", "dashboard", "audit", "factfind", "meeting", "suitability", "drift", "cfo_pack")
CLIENT_OK = {"portal", "provide", "clients"}


def engagement(tenant: str, firm: str, a: dict[str, Any]) -> dict[str, Any]:
    svc = [str(x)[:120] for x in a.get("services") or []]
    if not svc:
        raise FirmError("services: what the firm will do.")
    body = (f"# Engagement letter (DRAFT)\n\nClient: {a.get('client_name') or '[client]'}\nPeriod: {a.get('period') or '[period]'}\n\n"
            "## What we will do\n" + "\n".join(f"- {x}" for x in svc) +
            f"\n\n## Fee\n{a.get('fee') or '[fee]'}\n\n## What you will give us\n{a.get('client_duties') or '[papers and dates]'}\n\n"
            f"## Terms\n{a.get('terms') or '[the firm terms]'}")
    return draft(tenant, firm, {**a, "kind": "engagement", "title": "Engagement letter", "body": body})


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    firm = str(a.get("firm") or a.get("workspace") or "")
    if not firm:
        raise FirmError("firm: the firm's workspace.")
    if re.search(r"file|submit|send_to_client|pay", action):
        raise L.Refused("file_as_institution", "Hoola does not file, send or pay: the firm's named people do.")
    if action == "drift":
        return {**drift(a), "not_advice": L.NOT_ADVICE}
    f = {k: globals()[k] for k in ACTIONS if k != "drift"}
    if action not in f:
        raise FirmError("action: " + ", ".join(ACTIONS))
    st = _state(_firm(tenant, firm))
    if (st.get("people") or {}).get(str(a.get("person") or ""), {}).get("role") == "client" and action not in CLIENT_OK:
        raise FirmError("A client can only see their own portal and send papers.")
    out = f[action](tenant, firm, a)
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
