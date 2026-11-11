"""#67 Meeting Secretary - OAC / site / coordination meetings (v0.512.0, Wave 1, tier A): minutes taken
as said, action items with owners and due dates, chased till closed (closing is on the owner's / PM's
word). Minutes PDF rides reportlab like theka's bill - one clean sheet to circulate."""
from __future__ import annotations

import io

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, publish, today)
from .models import CActionItem, CMeet

KINDS = ("oac", "site", "coord", "client", "weekly")


def meet(tenant: str, title: str, kind: str = "site", day: str = "", site: str = "", project: str = "",
         attendees: str = "", minutes: list | None = None, actions: list | None = None, conv: str = "") -> dict:
    if not str(title or "").strip():
        raise CstError("Give the meeting's title.")
    k = (kind or "site").strip().lower()
    if k not in KINDS:
        raise CstError("kind: " + " | ".join(KINDS))
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        x = CMeet(tenant_id=tenant, title=title.strip()[:200], kind=k, day=d.isoformat(), site=site[:160],
                  project=project[:160], attendees=str(attendees)[:400],
                  minutes=_dump([{"text": str(m.get("text", ""))[:500], "by": str(m.get("by", ""))[:80]}
                                 for m in (minutes or []) if isinstance(m, dict)][:40]),
                  status="minuted" if minutes else "open")
        s.add(x)
        s.flush()
        mid = x.id
        added: list[dict] = []
        for a in (actions or []):
            if isinstance(a, dict) and str(a.get("what", "")).strip():
                row = CActionItem(tenant_id=tenant, meet_id=mid, what=str(a.get("what"))[:500],
                                  who=str(a.get("who", ""))[:160], due=(_date(a.get("due")) or d).isoformat())
                s.add(row)
                s.flush()
                added.append({"id": row.id, "what": row.what[:60], "who": row.who, "due": row.due})
    publish(tenant, "const_meet", {"kind": "meet", "title": title[:80], "actions": len(added)}, conv)
    say = (f"Meeting recorded: '{title[:60]}' ({k}, {d.strftime('%d %b')})"
           + (f", {len(minutes or [])} minute points" if minutes else "")
           + (f", {len(added)} action items - Hoola will chase them." if added else "."))
    return {"meet_id": mid, "actions": added, "say": say}


def minute(tenant: str, meet_id: str, text: str, by: str = "") -> dict:
    if not str(text or "").strip():
        raise CstError("Give the minute.")
    with _LOCK, session() as s:
        x = s.get(CMeet, meet_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Meeting not found.")
        rows = _j(x.minutes, [])
        rows.append({"text": str(text)[:500], "by": str(by)[:80]})
        x.minutes = _dump(rows[-40:])
        x.status = "minuted"
        title = x.title
    return {"say": f"Minute added: '{title[:50]}' - {text[:80]}"}


def action(tenant: str, meet_id: str = "", what: str = "", who: str = "", due: str = "") -> dict:
    if not str(what or "").strip():
        raise CstError("Tell me what the action is.")
    d = _date(due, today(tenant))
    with _LOCK, session() as s:
        row = CActionItem(tenant_id=tenant, meet_id=meet_id[:40], what=what.strip()[:500], who=who[:160],
                          due=(d or today(tenant)).isoformat())
        s.add(row)
        s.flush()
        aid = row.id
    return {"action_id": aid, "say": f"Action: {what[:70]}" + (f" - {who}" if who else "") + f", due {(d or today(tenant)).strftime('%d %b')}."}


def action_done(tenant: str, action_id: str, actor: str) -> dict:
    """Closed on the owner's / PM's word - Hoola never marks an action done by itself."""
    if actor != "owner" and not str(actor).startswith("approved:"):
        raise CstError("Only the owner / PM can approve closing an action.")
    with _LOCK, session() as s:
        x = s.get(CActionItem, action_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Action not found.")
        x.status = "done"
        x.done_on = today(tenant).isoformat()
        what = x.what
    return {"say": f"Action closed: {what[:70]}."}


def open_actions(tenant: str) -> dict:
    t0 = today(tenant)
    with session() as s:
        rows = s.scalars(select(CActionItem).where(CActionItem.tenant_id == tenant, CActionItem.status == "open")
                         .order_by(CActionItem.due)).all()
    late = [r for r in rows if r.due < t0.isoformat()]
    say = (f"Actions: {len(rows)} open" + (f", {len(late)} past due" if late else "") + "."
           + (" Oldest: " + "; ".join(f"{r.what[:40]} ({r.who or '-'}, due {r.due})" for r in (late or rows)[:2]) if rows else ""))
    return {"open": len(rows), "late": len(late),
            "rows": [{"id": r.id, "what": r.what[:120], "who": r.who, "due": r.due, "meet_id": r.meet_id} for r in rows[:15]],
            "say": say}


def minutes_pdf(tenant: str, meet_id: str) -> bytes:
    with session() as s:
        x = s.get(CMeet, meet_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Meeting not found.")
        minutes = _j(x.minutes, [])
        actions = s.scalars(select(CActionItem).where(CActionItem.meet_id == x.id)).all()
        title, kind, day, site, project, att = x.title, x.kind, x.day, x.site, x.project, x.attendees
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 50

    def t(a, text, size=10, bold=False):
        nonlocal y
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(a, y, str(text).replace("₹", "Rs ")[:110])
        y -= size + 6

    t(50, "MINUTES OF MEETING", 13, True)
    t(50, f"{title}  ({kind}, {day})")
    if site or project:
        t(50, f"Site: {site or '-'}   Project: {project or '-'}")
    t(50, f"Present: {att or '-'}")
    y -= 8
    t(50, "Minutes:", 11, True)
    for i, m in enumerate(minutes, 1):
        t(58, f"{i}. {m.get('text', '')[:100]}", 9.5)
    y -= 8
    t(50, "Action items:", 11, True)
    for a in actions:
        t(58, f"- {a.what[:90]} | {a.who or '-'} | due {a.due} | {a.status}", 9.5)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()
