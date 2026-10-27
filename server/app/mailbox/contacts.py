"""The user's email address book, learned from their own mail (who writes to them, whom they write to)."""
from __future__ import annotations

import re
from typing import Iterable

from sqlalchemy import select

from ..db import MailContact, now, session
from .mime import NOREPLY

EMAIL_RE = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[a-z]{2,}$", re.I)


def valid(addr: str) -> bool:
    return bool(EMAIL_RE.match((addr or "").strip()))


def learn(tenant: str, people: Iterable[tuple[str, str]], weight: float = 0.2, sent: bool = False) -> None:
    rows = [(n.strip(), a.strip().lower()) for n, a in people if a and valid(a) and not NOREPLY.search(a)]
    if not rows:
        return
    with session() as s:
        for name, a in rows:
            c = s.scalar(select(MailContact).where(MailContact.tenant_id == tenant, MailContact.email == a))
            if c is None:
                c = MailContact(tenant_id=tenant, email=a, name="", score=0)
                s.add(c)
            if name and name.lower() != a and (not c.name or sent):
                c.name = name[:200]
            c.score = (c.score or 0) + weight
            if sent:
                c.sent_to = (c.sent_to or 0) + 1
            c.last_seen = now()


def find(tenant: str, query: str, limit: int = 8) -> list[dict]:
    q = (query or "").strip().lower()
    with session() as s:
        rows = s.scalars(select(MailContact).where(MailContact.tenant_id == tenant)
                         .order_by(MailContact.score.desc()).limit(2000)).all()
        out = []
        for c in rows:
            name, a = (c.name or "").lower(), c.email
            if not q:
                hit = 1.0
            elif a == q:
                hit = 10.0
            elif any(w == q for w in re.split(r"[\s._-]+", name)) or name == q:
                hit = 5.0
            elif name.startswith(q) or a.startswith(q):
                hit = 3.0
            elif q in name or q in a.split("@")[0]:
                hit = 2.0
            elif q in a:
                hit = 1.0
            else:
                continue
            out.append((hit * 10 + (c.score or 0) + (c.sent_to or 0) * 2,
                        {"name": c.name or a.split("@")[0], "email": a, "times_emailed": c.sent_to or 0}))
        out.sort(key=lambda x: -x[0])
        return [o[1] for o in out[:limit]]


def resolve(tenant: str, text: str) -> tuple[str, list[str]]:
    """'Swati, ramesh@vendor.in' -> 'swati.s@fnw.in, ramesh@vendor.in'. Returns (addresses, problems)."""
    out, problems = [], []
    for part in re.split(r"[,;]", text or ""):
        p = part.strip()
        if not p:
            continue
        m = re.search(r"<([^>]+)>", p)
        if m:
            p = m.group(1).strip()
        if "@" in p:
            if valid(p):
                out.append(p)
            else:
                problems.append(f"'{p}' sahi email address nahi lagta.")
            continue
        found = find(tenant, p, limit=4)
        exact = [f for f in found if f["name"].lower() == p.lower() or p.lower() in f["name"].lower().split()]
        pick = exact or found
        if len(pick) == 1 or (pick and len(pick) > 1 and pick[0]["times_emailed"] >= 3 * max(1, pick[1]["times_emailed"])):
            out.append(pick[0]["email"])
        elif pick:
            problems.append(f"'{p}' naam ke kai log hain: " + ", ".join(f"{f['name']} <{f['email']}>" for f in pick[:4])
                            + ". User se poochiye kaunsa.")
        else:
            problems.append(f"'{p}' ka email address nahi mila. User se address poochiye.")
    return ", ".join(dict.fromkeys(out)), problems
