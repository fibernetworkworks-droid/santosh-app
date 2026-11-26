"""FIRM PRACTICE DESK - the Firm Practice employee's own section, like Payroll, Tax, Cash & Treasury and Credit & Lending (owner: "NOW LETS
WORK ON NEXT EMPLOYEE FIRM PRACTICE -- MAKE IT SAME PREMIUM AND ADVANCE AS WE DONE WITH OTHER SECTIONS").

- The Firm chat = a Conversation with kind 'firm', kept out of every Hoola chat list (callconv.not_call); facts she tells it still reach
  her one memory. A turn in it (or a voice call started from it) gets the desk's state as a block and the firm tool (`firm_practice`,
  family firmmode) in view.
- The desk runs the F7 engine (fin/desks/firm.py) on a FIRM workspace: client books inside it, the firm's people (partner, manager,
  preparer, reviewer, client), papers asked for, drafts that go preparer -> reviewer -> the named signer -> the client's portal.
- Every engine action is done AS a person of the firm. Who the signed-in user is on the desk is kept in the firm's settings under
  `practice_desk`:
    who     the firm's owner picks which person of the firm she is (she can switch, it is her account);
    logins  a partner links a person to a team member's email (a Books & Accounts team member of this firm): that member is always that
            person, never another.
  So a preparer can never sign, a client never sees another client, and the preparer never reviews their own draft - the engine checks it.
- Hoola prepares. It files nothing, sends nothing to a client and pays nothing: the firm's named people review and sign. Not advice.
"""
from __future__ import annotations

import io
import json
import logging
import re
import time
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.firmchat")

KIND = "firm"
KEY = "firm_practice"          # the Hub employee
TOOL = "firm_practice"         # its tool
FAMILIES = ["firmmode"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FOOT = ("Hoola prepares. It files nothing, sends nothing to a client and pays nothing - the firm's named people review and sign. "
        "Not advice.")
ROLE_SAY = {"partner": "Partner", "manager": "Manager", "preparer": "Preparer", "reviewer": "Reviewer", "client": "Client"}
KIND_SAY = {"tax_return": "Tax return", "accounts": "Accounts", "letter": "Letter", "engagement": "Engagement letter",
            "suitability": "Suitability report", "plan": "Plan", "memo": "Memo", "cfo_pack": "CFO pack", "other": "Other"}


class FirmDeskError(ValueError):
    pass


def is_firm(conv: str) -> bool:
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
        log.exception("firm chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _hire():
    from .employee import hire
    return hire


def firms(tenant: str) -> list[dict[str, Any]]:
    from .bookschat import businesses as B
    return [b for b in B(tenant) if b.get("size") == "firm"]


def workspace(tenant: str, want: str = "") -> dict[str, Any] | None:
    fs = firms(tenant)
    if not want:
        try:
            want = str(_hire().settings(tenant, KEY).get("workspace") or "")
        except Exception:   # noqa: BLE001
            want = ""
    for b in fs:
        if b["id"] == want:
            return b
    return fs[0] if fs else None


def pick(tenant: str, ws: str) -> dict[str, Any]:
    if not any(b["id"] == ws for b in firms(tenant)):
        raise FirmDeskError("No such firm.")
    try:
        _hire().save_settings(tenant, KEY, workspace=ws)
    except Exception:   # noqa: BLE001
        pass
    forget(tenant)
    return {"workspace": ws}


def setup(tenant: str, a: dict[str, Any]) -> dict[str, Any]:
    """A new firm (a finance workspace of size firm) with her as its first partner."""
    from .fin import profile as PR
    from .fin.desks import firm as FM
    name = str(a.get("name") or "").strip()[:80]
    me = str(a.get("partner") or "").strip()[:80]
    cc = str(a.get("country") or "").strip().upper()
    cur = str(a.get("currency") or "").strip().upper()
    if not name or not me:
        raise FirmDeskError("name (the firm) and partner (your name, the first partner).")
    if len(cc) != 2 or len(cur) != 3:
        raise FirmDeskError("country (two letters, like GB) and currency (three letters, like GBP).")
    pv = PR.preview({"size": "firm", "countries": [cc], "currency": cur, "name": name, "wants": []})
    w = PR.apply(tenant, pv["answers"], pv["hash"])
    try:
        p = FM.run(tenant, "person_add", {"firm": w["id"], "name": me, "role": "partner"})["person"]
    except FM.FirmError as e:
        raise FirmDeskError(str(e))
    _put(tenant, w["id"], lambda st: st.setdefault("who", {}).__setitem__(tenant, p["id"]))
    pick(tenant, w["id"])
    _regreet(tenant)
    return {"firm": {"id": w["id"], "name": w["name"]}, "person": p}


def _regreet(tenant: str) -> None:
    """A Firm chat nobody has written in yet gets the greeting that fits the desk now (it was written before the firm existed)."""
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
        log.exception("firm chat greeting refresh failed")


# ---------------------------------------------------------------- desk state (kept in the firm's settings)
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _settings(owner: str, ws: str) -> dict[str, Any]:
    from .fin import profile as PR
    return dict(PR.get(owner, ws).get("settings") or {})


def _state(owner: str, ws: str) -> dict[str, Any]:
    st = dict(_settings(owner, ws).get("practice_desk") or {})
    st.setdefault("who", {})
    st.setdefault("logins", {})
    return st


def _put(owner: str, ws: str, change) -> Any:
    from . import db
    from .fin.models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != owner:
            raise FirmDeskError("No such firm.")
        cur = json.loads(row.settings or "{}")
        out = change(cur.setdefault("practice_desk", {}))
        row.settings = json.dumps(cur)
        s.commit()
    return out


def _people(owner: str, ws: str) -> dict[str, dict[str, Any]]:
    return dict((_settings(owner, ws).get("practice") or {}).get("people") or {})


def _email(caller: str) -> str:
    try:
        from .fin.desks import books_ent as E
        return str(E._email_of(caller) or "").lower()   # noqa: SLF001
    except Exception:   # noqa: BLE001
        return ""


def whoami(caller: str, ws: str) -> dict[str, Any]:
    """The person of the firm the signed-in user is on this desk: a team member by the login a partner linked; the owner by her pick."""
    from .fin.desks import books_ent as E
    acc = E.access(caller, ws)
    owner = acc["owner"]
    people = _people(owner, ws)
    st = _state(owner, ws)
    pid = ""
    if caller == owner:
        pid = st["who"].get(caller) or ""
        if pid not in people:
            pid = next((k for k, v in people.items() if v["role"] == "partner"), "")
    else:
        em = _email(caller)
        pid = next((k for k, v in st["logins"].items() if v and (v.lower() == em or v == caller)), "")
        if pid not in people:
            pid = ""
    p = {"id": pid, **people[pid]} if pid else None
    return {"owner": owner, "is_owner": caller == owner, "person": p, "acc": acc}


def _engine(owner: str, me: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin import core
    from .fin.desks import firm as FM
    try:
        return core.run_tool(owner, me, TOOL, action, dict(a), lambda: FM.run(owner, action, a, me))
    except FM.FirmError as e:
        raise FirmDeskError(str(e))


def _clients(owner: str, ws: str) -> dict[str, dict[str, Any]]:
    from .fin.desks import firm as FM
    return FM._clients(owner, ws)   # noqa: SLF001


# ---------------------------------------------------------------- what the desk reads
def _cname(cl: dict[str, Any], cid: str) -> str:
    return (cl.get(cid) or {}).get("name") or "?"


def drafts_view(owner: str, ws: str, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Drafts this person may see (the engine's rule), newest first, without the body."""
    from .fin.desks import firm as FM
    cl = _clients(owner, ws)
    out = []
    for d in FM._drafts(owner, ws):   # noqa: SLF001
        if d["client"] not in cl or not FM._sees(p, d["client"]):   # noqa: SLF001
            continue
        if p["role"] == "client" and not d.get("shared"):
            continue
        out.append({k: d[k] for k in ("id", "client", "kind", "title", "state", "prepared_by", "signer", "shared", "hash")}
                   | {"client_name": _cname(cl, d["client"]), "reviews": len(d.get("reviews") or []),
                      "last_notes": ((d.get("reviews") or [{}])[-1] or {}).get("notes") if d["state"] == "sent_back" else None,
                      "signed_on": (d.get("signed") or {}).get("on")})
    return list(reversed(out))


def draft_one(owner: str, ws: str, p: dict[str, Any], did: str) -> dict[str, Any]:
    from .fin.desks import firm as FM
    cl = _clients(owner, ws)
    d = next((x for x in FM._drafts(owner, ws) if x["id"] == did), None)   # noqa: SLF001
    if not d or d["client"] not in cl or not FM._sees(p, d["client"]) or (p["role"] == "client" and not d.get("shared")):   # noqa: SLF001
        raise FirmDeskError("No such draft for this person.")
    people = _people(owner, ws)
    nm = lambda k: (people.get(k) or {}).get("name") or k   # noqa: E731
    out = {**d, "client_name": _cname(cl, d["client"]), "prepared_by_name": nm(d["prepared_by"]), "signer_name": nm(d["signer"]),
           "reviews": [{**r, "by_name": nm(r["by"])} for r in d.get("reviews") or []]}
    me = p["id"]
    out["can"] = {
        "edit": p["role"] in FM.STAFF and not d.get("signed"),
        "review": p["role"] in FM.REVIEWERS and d["state"] == "waiting" and d["prepared_by"] != me,
        "sign": d["state"] == "approved" and d["signer"] == me,
        "share": p["role"] in ("partner", "manager") and bool(d.get("signed")) and not d.get("shared"),
    }
    out["why_not_review"] = ("You prepared it - another reviewer must review it." if d["state"] == "waiting" and d["prepared_by"] == me
                             else "")
    return out


def client_view(owner: str, ws: str, p: dict[str, Any], cid: str, me: str) -> dict[str, Any]:
    from .fin.desks import firm as FM
    cl = _clients(owner, ws)
    if cid not in cl or not FM._sees(p, cid):   # noqa: SLF001
        raise FirmDeskError("No such client for this person.")
    sett = _settings(owner, ws).get("practice") or {}
    reqs = [r for r in sett.get("requests") or [] if r["client"] == cid]
    ff = (sett.get("factfinds") or {}).get(cid) or {}
    people = _people(owner, ws)
    team = [{"id": k, "name": v["name"], "role": v["role"]} for k, v in people.items()
            if v["role"] != "client" and FM._sees({"id": k, **v}, cid)]   # noqa: SLF001
    contacts = [{"id": k, "name": v["name"]} for k, v in people.items() if v["role"] == "client" and cid in (v.get("clients") or [])]
    return {"client": cl[cid], "requests": list(reversed(reqs)), "drafts": [d for d in drafts_view(owner, ws, p) if d["client"] == cid],
            "factfind": ff, "factfind_missing": [k for k in FM.FACTFIND if k not in ff], "team": team, "client_people": contacts,
            "signers": [t for t in team if t["role"] in ("partner", "manager")]}


def today_view(owner: str, ws: str, p: dict[str, Any], me: str) -> dict[str, Any]:
    from .fin.desks import firm as FM
    pid = p["id"]
    sett = _settings(owner, ws).get("practice") or {}
    out: dict[str, Any] = {"me": p, "people": [{"id": k, **v} for k, v in (sett.get("people") or {}).items()],
                           "logins": _state(owner, ws)["logins"]}
    if p["role"] == "client":
        out["portal"] = _engine(owner, me, "portal", {"firm": ws, "person": pid})
        out["needs"] = [{"say": f"{len([i for r in out['portal']['requests'] for i in r['items'] if not i['sent']])} paper(s) your firm asked for",
                         "go": "portal"}] if any(not i["sent"] for r in out["portal"]["requests"] for i in r["items"]) else []
        return out
    out["clients"] = _engine(owner, me, "clients", {"firm": ws, "person": pid})["clients"]
    out["queue"] = _engine(owner, me, "queue", {"firm": ws, "person": pid})
    out["drafts"] = drafts_view(owner, ws, p)
    if p["role"] in ("partner", "manager"):
        out["dashboard"] = _engine(owner, me, "dashboard", {"firm": ws, "person": pid})
    today = date.today().isoformat()
    cl = _clients(owner, ws)
    out["overdue"] = [{"client": r["client"], "client_name": _cname(cl, r["client"]), "due": r["due"],
                       "missing": [i["item"] for i in r["items"] if not i["sent"]]}
                      for r in sett.get("requests") or [] if r["client"] in cl and FM._sees(p, r["client"])   # noqa: SLF001
                      and r["due"] and r["due"] < today and any(not i["sent"] for i in r["items"])]
    q = out["queue"]
    needs = []
    for d in q.get("to_sign") or []:
        needs.append({"say": f"Sign: {d['title']} for {d['client']}", "go": f"draft/{d['id']}", "bad": False})
    for d in q.get("to_review") or []:
        needs.append({"say": f"Review: {d['title']} for {d['client']}", "go": f"draft/{d['id']}"})
    for d in q.get("sent_back_to_me") or []:
        needs.append({"say": f"Sent back to you: {d['title']} for {d['client']}", "go": f"draft/{d['id']}", "bad": True})
    for o in out["overdue"][:5]:
        needs.append({"say": f"{o['client_name']}: {len(o['missing'])} paper(s) late since {o['due']}", "go": f"clients/{o['client']}",
                      "bad": True})
    for d in out["drafts"]:
        if d["state"] == "signed" and not d["shared"] and p["role"] in ("partner", "manager"):
            needs.append({"say": f"Signed, not shared yet: {d['title']} for {d['client_name']}", "go": f"draft/{d['id']}"})
    if not cl and p["role"] in ("partner", "manager"):
        needs.append({"say": "Add your first client", "go": "clients"})
    out["needs"] = needs
    return out


def summary(tenant: str, want: str = "") -> dict[str, Any]:
    h = _hire()
    st = h.status(tenant, KEY)
    trust = ""
    fs = firms(tenant)
    if st not in ("hired", "paused"):
        if not any(f.get("role") != "owner" for f in fs):
            return {"hired": False, "status": st, "say": "Firm Practice is not hired. Hire it from AI Employees."}
    else:
        with session() as s:
            trust = h._view(h._row(s, tenant, KEY)).get("trust") or ""    # noqa: SLF001
    out: dict[str, Any] = {"hired": True, "status": st if st in ("hired", "paused") else "member",
                           "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
                           "firms": fs, "workspace": workspace(tenant, want), "roles": ROLE_SAY, "kinds": KIND_SAY, "foot": FOOT}
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
            log.exception("firm desk read failed")
            out["desk_error"] = str(e)[:200]
    return out


READS = {"client", "draft", "portal", "audit", "dashboard", "queue", "meeting", "drift", "cfo_pack"}


def do(caller: str, part: str, a: dict[str, Any]) -> dict[str, Any]:
    """Every desk action: who she is on this firm first, then the engine AS that person on the OWNER's books."""
    from .fin.desks import firm as FM
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    ws = str(a.get("workspace") or "")
    who = whoami(caller, ws)
    owner = who["owner"]
    if part == "be":      # the owner chooses which person of her firm she is on this desk
        if not who["is_owner"]:
            raise FirmDeskError("Only the firm's owner switches person; a partner links your login to your person.")
        pid = str(a.get("person") or "")
        if pid not in _people(owner, ws):
            raise FirmDeskError("No such person of the firm.")
        _put(owner, ws, lambda st: st.setdefault("who", {}).__setitem__(caller, pid))
        forget(caller)
        _regreet(caller)
        return {"person": {"id": pid, **_people(owner, ws)[pid]}}
    p = who["person"]
    if not p:
        raise FirmDeskError("You are not a person of this firm on the desk yet: a partner links your login on the Team page.")
    me = f"{p['name']} <{caller}>"
    base = {"firm": ws, "person": p["id"]}
    if part == "link":    # a partner links a person of the firm to a team member's login (email)
        if p["role"] != "partner":
            raise FirmDeskError("Only a partner links a login to a person.")
        pid, em = str(a.get("target") or ""), str(a.get("email") or "").strip().lower()[:120]
        if pid not in _people(owner, ws):
            raise FirmDeskError("No such person of the firm.")
        if em and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", em):
            raise FirmDeskError("email: the email of their Hoola account.")
        _put(owner, ws, lambda st: (st.setdefault("logins", {}).__setitem__(pid, em) if em else st.setdefault("logins", {}).pop(pid, None)))
        out: dict[str, Any] = {"logins": _state(owner, ws)["logins"],
                               "says": "Linked. Add them to this firm's team in Books & Accounts too, so they can open it."}
    elif part == "client":
        out = client_view(owner, ws, p, str(a.get("client") or ""), me)
    elif part == "draft":
        out = draft_one(owner, ws, p, str(a.get("draft") or ""))
    elif part == "new_draft":
        body = str(a.get("body") or "")
        out = _engine(owner, me, "draft", {**base, "client": a.get("client"), "kind": a.get("kind"), "title": a.get("title"),
                                           "body": body, "signer": a.get("signer")})
    elif part in ("person_add", "client_add", "request", "provide", "edit", "review", "sign", "share", "engagement", "factfind",
                  "suitability", "portal", "audit", "dashboard", "queue", "meeting", "drift", "cfo_pack"):
        keep = {k: v for k, v in a.items() if k not in ("workspace", "person", "firm")}
        out = _engine(owner, me, part, {**base, **keep})
    else:
        raise FirmDeskError("Not a Firm Practice desk action.")
    if part not in READS:
        forget(owner)
        forget(caller)
    return out


def draft_pdf(d: dict[str, Any], firm_name: str) -> bytes:
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

    line(firm_name, 13, True)
    line(f"{d.get('title')} - {d.get('client_name')} - {KIND_SAY.get(d['kind'], d['kind'])}", 11, True)
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
    sg = d.get("signed")
    line(f"Signed by {sg['name']} ({sg['role']}) on {sg['on']} - text {sg['hash'][:16]}" if sg else "NOT SIGNED - a draft.", 9, True)
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
        return "I run your firm's clients - papers, drafts, reviews and signing. Hire me from AI Employees to start."
    if not d.get("workspace"):
        return "Hello. Set up your firm on the desk first (its name, country, currency and you as the first partner)."
    if not d.get("me"):
        return "Hello. A partner needs to link your login to your person of the firm on the Team page."
    k = d.get("desk") or {}
    me = d["me"]
    if me["role"] == "client":
        return f"Hello {me['name']}. Your firm's papers and documents are on your page. Ask me anything about them."
    q = k.get("queue") or {}
    bits = [f"{len(k.get('clients') or [])} client(s)"]
    if q.get("to_review"):
        bits.append(f"{len(q['to_review'])} to review")
    if q.get("to_sign"):
        bits.append(f"{len(q['to_sign'])} to sign")
    if k.get("overdue"):
        bits.append(f"{len(k['overdue'])} late paper request(s)")
    return (f"Hello {me['name']} ({ROLE_SAY.get(me['role'], me['role'])}). " + ", ".join(bits) + ". Ask me to draft an engagement letter, "
            "read meeting notes or check a fact-find. I prepare; your named people review and sign.")


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
        c = Conversation(tenant_id=tenant, kind=KIND, title="Firm chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False, delivered_to_agent=True))
    return {"id": cid, "new": True}


RULES = ("You are her Firm Practice employee, talking in the desk's own chat (or a voice call started from it). Use the " + TOOL +
         " tool with firm set to the firm below and person set to HER person id below - never another person's id: clients (the switcher), "
         "request (papers from a client), draft (a draft for a client with the named signer), engagement, factfind, meeting (actions / "
         "decisions from notes), suitability (only with the adviser's own recommendation), cfo_pack, queue, dashboard, audit. Only the "
         "named signer signs, the preparer never reviews their own draft and a client sees only their own book - the tool checks it; never "
         "work around it. Hoola files nothing, sends nothing to a client and pays nothing. Never ask for or keep a password or a login. "
         "Plain English, short. Not advice. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<firm_desk>{RULES}Firm Practice is not hired yet: tell her to hire it from AI Employees.</firm_desk>"
        elif not d.get("workspace"):
            txt = f"\n\n<firm_desk>{RULES}\nNo firm set up yet: ask her to set it up on the Firm Practice desk.</firm_desk>"
        elif not d.get("me"):
            txt = (f"\n\n<firm_desk>{RULES}\nFirm: {d['workspace']['name']} (firm {d['workspace']['id']}). She is not linked to a person "
                   "of the firm yet: a partner links her login on the desk's Team page. Do not act as anyone.</firm_desk>")
        else:
            w, k, me = d["workspace"], d.get("desk") or {}, d["me"]
            q = k.get("queue") or {}
            cl = "; ".join(f"{c['name']} ({c['id']}): {c['papers_outstanding']} papers out, {c['drafts_waiting_review']} waiting review, "
                           f"{c['drafts_to_sign']} to sign" for c in (k.get("clients") or [])[:15]) or "none"
            people = ", ".join(f"{p['name']} ({p['id']}, {p['role']})" for p in (d.get("people") or [])[:20])
            txt = (f"\n\n<firm_desk>{RULES}\nFirm: {w['name']} (firm {w['id']}), {', '.join(w['countries'])}, currency {w['currency']}."
                   f"\nShe is {me['name']} - person id {me['id']}, {me['role']}."
                   f"\nPeople: {people}.\nClients: {cl}."
                   f"\nHer queue: {len(q.get('to_review') or [])} to review, {len(q.get('to_sign') or [])} to sign, "
                   f"{len(q.get('sent_back_to_me') or [])} sent back to her; late paper requests {len(k.get('overdue') or [])}."
                   + ("\nShe is a CLIENT of the firm: only her own portal and sending papers." if me["role"] == "client" else "")
                   + "</firm_desk>")
    except Exception:   # noqa: BLE001
        log.exception("firm block failed")
        txt = f"\n\n<firm_desk>{RULES}The desk could not be read just now.</firm_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/firm/chat", dependencies=dep)
    def firm_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/firm/chat/new", dependencies=dep)
    def firm_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/firm/chat/{conv}/ok", dependencies=dep)
    def firm_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Firm chat")
        return {"ok": True}

    @router.get("/api/firm/desk", dependencies=dep)
    def firm_desk(workspace: str = "", tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant, workspace)

    @router.post("/api/firm/setup", dependencies=dep)
    def firm_setup(body: dict | None = None, tenant: str = Depends(current_tenant)):
        from .fin.profile import ProfileError
        try:
            return setup(tenant, body or {})
        except (FirmDeskError, ProfileError, ValueError) as e:
            raise HTTPException(400, str(e))

    @router.post("/api/firm/do/{part}", dependencies=dep)
    def firm_do(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        from .fin import laws as L
        from .fin.desks.safety import SafetyError
        try:
            return do(tenant, part, body or {})
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (SafetyError, ValueError) as e:
            raise HTTPException(400, str(e))

    @router.get("/api/firm/download", dependencies=dep)
    def firm_download(workspace: str, draft: str, what: str = "pdf", tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response
        try:
            who = whoami(tenant, workspace)
            if not who["person"]:
                raise FirmDeskError("Not linked to a person of the firm.")
            d = draft_one(who["owner"], workspace, who["person"], draft)
        except ValueError as e:
            raise HTTPException(400, str(e))
        firm_name = next((f["name"] for f in firms(tenant) if f["id"] == workspace), "Firm")
        slug = "".join(ch if ch.isalnum() else "-" for ch in f"{d['title']}-{d['client_name']}".lower())[:60].strip("-") or "draft"
        if what == "md":
            return Response(str(d["body"]).encode("utf-8"), media_type="text/markdown",
                            headers={"Content-Disposition": f'attachment; filename="{slug}.md"'})
        if what == "pdf":
            return Response(draft_pdf(d, firm_name), media_type="application/pdf",
                            headers={"Content-Disposition": f'attachment; filename="{slug}.pdf"'})
        raise HTTPException(400, "what: pdf | md")

    @router.put("/api/firm/workspace", dependencies=dep)
    def firm_workspace(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return pick(tenant, str((body or {}).get("workspace") or ""))
        except FirmDeskError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
