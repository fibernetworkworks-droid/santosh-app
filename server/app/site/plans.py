"""v0.782 TEEN MODE (L2 of docs/LOVABLE_STUDIO_PLAN.md) - a website's PLANS and its STANDING INSTRUCTIONS.

PLANS: what Hoola wrote in Plan mode, kept as numbered versions per site (Lovable keeps `.lovable/plan.md` and archives
it dated on approval). She can open a plan, edit it (her edit = a new version, source 'her'), comment on one passage
(Hoola rewrites it in Plan mode = a new version), then APPROVE (the Studio sends one Build message carrying the approved
text) or SKIP. Only one version is 'approved' at a time; an older approved one becomes 'superseded'. A plan is never
deleted - versions are the history. The same text twice in a row is one version (a re-send never doubles it).

INSTRUCTIONS: her standing brief for THIS website (product, who it is for, tone, colours, words to use or avoid, what
must never change), up to 10,000 characters. Read on every Studio turn for this site (`agent/turnmode.site_block`),
in every mode. Like Lovable's project instructions, but scoped to one website.

One table `site_docs` (registered in db.init_db + ensure_table, the v0.190.1 rule)."""
from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

PLAN_MAX = 30000
INSTR_MAX = 10000
STATUSES = ("draft", "approved", "skipped", "superseded")
_ready_engine = None


class SiteDoc(Base):
    __tablename__ = "site_docs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sd"))
    tenant_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    site_id: Mapped[str] = mapped_column(String(80), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="plan")        # plan | instructions
    version: Mapped[int] = mapped_column(Integer, default=1)
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    source: Mapped[str] = mapped_column(String(20), default="hoola")    # hoola | her
    note: Mapped[str] = mapped_column(String(300), default="")
    sha: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class PlanError(Exception):
    pass


def ensure_table() -> None:
    global _ready_engine
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or eng is _ready_engine:
        return
    SiteDoc.__table__.create(eng, checkfirst=True)
    _ready_engine = eng


def _sha(t: str) -> str:
    return hashlib.sha256(t.strip().encode()).hexdigest()


def _iso(d: datetime | None) -> str:
    return d.replace(microsecond=0).isoformat() if d else ""


def _row(r: SiteDoc) -> dict:
    return {"version": r.version, "text": r.text, "status": r.status, "source": r.source, "note": r.note,
            "at": _iso(r.created_at), "updated": _iso(r.updated_at)}


def plans(tenant: str, site: str) -> list[dict]:
    """Every version, newest first."""
    ensure_table()
    with session() as s:
        rows = s.scalars(select(SiteDoc).where(SiteDoc.tenant_id == tenant, SiteDoc.site_id == site,
                                               SiteDoc.kind == "plan").order_by(SiteDoc.version.desc())).all()
        return [_row(r) for r in rows]


def add_plan(tenant: str, site: str, text: str, source: str = "hoola", note: str = "") -> dict:
    text = str(text or "").strip()
    if not text:
        raise PlanError("The plan is empty.")
    if len(text) > PLAN_MAX:
        raise PlanError(f"A plan can be at most {PLAN_MAX:,} characters.")
    ensure_table()
    sha = _sha(text)
    with session() as s:
        last = s.scalars(select(SiteDoc).where(SiteDoc.tenant_id == tenant, SiteDoc.site_id == site,
                                               SiteDoc.kind == "plan").order_by(SiteDoc.version.desc())).first()
        if last is not None and last.sha == sha:
            return _row(last)                        # the same text again = the same version (a re-send never doubles it)
        r = SiteDoc(tenant_id=tenant, site_id=site, kind="plan", version=(last.version + 1) if last else 1, text=text,
                    status="draft", source="her" if source == "her" else "hoola", note=str(note or "")[:300], sha=sha)
        s.add(r)
        s.commit()
        return _row(r)


def set_status(tenant: str, site: str, version: int, status: str) -> dict:
    if status not in ("approved", "skipped", "draft"):
        raise PlanError("A plan can be approved, skipped or back to draft.")
    ensure_table()
    with session() as s:
        rows = s.scalars(select(SiteDoc).where(SiteDoc.tenant_id == tenant, SiteDoc.site_id == site,
                                               SiteDoc.kind == "plan")).all()
        hit = next((r for r in rows if r.version == int(version)), None)
        if hit is None:
            raise KeyError(f"plan v{version}")
        if status == "approved":                     # one approved plan at a time
            for r in rows:
                if r is not hit and r.status == "approved":
                    r.status, r.updated_at = "superseded", now()
        hit.status, hit.updated_at = status, now()
        s.commit()
        return _row(hit)


def instructions(tenant: str, site: str) -> dict:
    ensure_table()
    with session() as s:
        r = s.scalars(select(SiteDoc).where(SiteDoc.tenant_id == tenant, SiteDoc.site_id == site,
                                            SiteDoc.kind == "instructions")).first()
        return {"text": r.text if r else "", "at": _iso(r.updated_at) if r else "", "max": INSTR_MAX}


def set_instructions(tenant: str, site: str, text: str) -> dict:
    text = str(text or "").strip()
    if len(text) > INSTR_MAX:
        raise PlanError(f"Instructions can be at most {INSTR_MAX:,} characters (now {len(text):,}).")
    ensure_table()
    with session() as s:
        r = s.scalars(select(SiteDoc).where(SiteDoc.tenant_id == tenant, SiteDoc.site_id == site,
                                            SiteDoc.kind == "instructions")).first()
        if r is None:
            r = SiteDoc(tenant_id=tenant, site_id=site, kind="instructions", source="her")
            s.add(r)
        r.text, r.sha, r.updated_at = text, _sha(text), now()
        s.commit()
    return instructions(tenant, site)


def prompt_block(tenant: str, site: str, build: bool = True) -> str:
    t = instructions(tenant, site)["text"]
    if not t:
        return ""
    return ("\n\nHER STANDING INSTRUCTIONS FOR THIS WEBSITE (she wrote these; follow them in every answer and change, "
            "unless her message today says otherwise):\n" + t)
