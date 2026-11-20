"""v0.999.52 LEAD DESK - what happens to a lead AFTER it is found (owner: "PERFECT GO WITH LEAD GENEARTION" -> the
design claude.ai/artifact/FTaYVw37EiqT7gp1NAGGkg -> "GO BUILD").

The leads engine (service.py) finds businesses and keeps one row per business with its source. This module adds the
rest of a lead desk, on top of those rows and never inside them:

- a STAGE per lead (new -> contacted -> interested / not interested -> won), a follow-up date + note, her notes, and a
  timeline (found, list made, sent, her notes, stage changes) read from the real ledgers;
- saved searches (a search she can run again; weekly only for the free IndiaMART route - a paid route never runs by
  itself);
- quality checks (maybe the same business twice, no phone, website that did not open, untouched for 90 days);
- hand-offs on her tap: the WhatsApp campaign desk (the engine's two-tap campaign_list), the Telecaller list
  (telecall.add_lead, marked as a cold business list), a CSV;
- a message DRAFT for one lead with a wa.me link: she sends it from her own WhatsApp. Nothing here contacts anyone.

An opted-out business is never handed anywhere, never drafted for, and stays out of every list.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from .models import LeadContact, LeadOutreach, LeadRun, ensure_tables as _base_tables

STAGES = ("new", "contacted", "interested", "not_interested", "won")
STAGE_NAME = {"new": "New", "contacted": "Contacted", "interested": "Interested", "not_interested": "Not interested",
              "won": "Won"}
LANE_NAME = {"HER_DATA": "Your list", "REGISTRY": "IndiaMART", "OFFICIAL_API": "Google Maps",
             "SCRAPE": "Public Maps listings", "VENDOR": "Paid lead seller"}
WEEKLY_LANES = ("REGISTRY", "SCRAPE")   # free routes only: a paid route never runs by itself. The public Maps scan
                                        # is free (server time) and runs weekly only while her switch is on.
SAVE_LANES = ("REGISTRY", "OFFICIAL_API", "SCRAPE")


class DeskError(ValueError):
    pass


class LeadStage(Base):
    __tablename__ = "lead_stages"
    __table_args__ = (UniqueConstraint("tenant_id", "contact_id", name="uq_lead_stage"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lst"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[str] = mapped_column(String(40), index=True)
    stage: Mapped[str] = mapped_column(String(20), default="new", index=True)
    follow_on: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    follow_note: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LeadEvent(Base):
    __tablename__ = "lead_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lev"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="note")      # note | stage | follow | draft | handoff
    text: Mapped[str] = mapped_column(Text, default="")
    by: Mapped[str] = mapped_column(String(40), default="owner")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LeadSaved(Base):
    __tablename__ = "lead_saved"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lsv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    lane: Mapped[str] = mapped_column(String(14), default="REGISTRY")
    params: Mapped[str] = mapped_column(Text, default="{}")
    weekly: Mapped[bool] = mapped_column(Boolean, default=False)
    runs: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_kept: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_ready = False


def ensure_tables() -> None:
    global _ready
    _base_tables()
    if _ready:
        return
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        for t in (LeadStage, LeadEvent, LeadSaved):
            t.__table__.create(eng, checkfirst=True)
    _ready = True


def _iso(d: Any) -> str | None:
    return d.isoformat() if d is not None else None


def _aware(d: datetime | None) -> datetime | None:
    if d is not None and d.tzinfo is None:
        return d.replace(tzinfo=timezone.utc)
    return d


def _today() -> date:
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


def _contact(s, tenant: str, cid: str) -> LeadContact:
    c = s.get(LeadContact, str(cid or ""))
    if c is None or c.tenant_id != tenant:
        raise DeskError("That lead was not found.")
    return c


def _stage_row(s, tenant: str, cid: str, make: bool = True) -> LeadStage | None:
    r = s.query(LeadStage).filter(LeadStage.tenant_id == tenant, LeadStage.contact_id == cid).first()
    if r is None and make:
        r = LeadStage(tenant_id=tenant, contact_id=cid, stage="new")
        s.add(r)
        s.flush()
    return r


def _mask(p: str) -> str:
    p = re.sub(r"\D", "", str(p or ""))
    return ("+" + p[:-6] + "••••••") if len(p) > 6 else p


def view(c: LeadContact, st: LeadStage | None) -> dict[str, Any]:
    stage = st.stage if st is not None else "new"
    return {"id": c.id, "name": c.name or "(no name)", "category": c.category, "city": c.city, "address": c.address,
            "pincode": c.pincode, "phone": c.phone, "phone_shown": _mask(c.phone), "email": c.email,
            "website": c.website, "rating": c.rating, "review_count": c.review_count, "source": c.source_lane,
            "source_name": LANE_NAME.get(c.source_lane, c.source_lane), "source_url": c.source_url,
            "found_at": _iso(c.fetched_at), "run_id": c.run_id, "opt_out": bool(c.opt_out),
            "stage": "opted_out" if c.opt_out else stage, "stage_name": "Opted out" if c.opt_out else STAGE_NAME.get(stage, stage),
            "follow_on": _iso(st.follow_on) if st is not None else None,
            "follow_note": st.follow_note if st is not None else "",
            "enriched_from": c.enriched_from, "enrich_note": c.enrich_note}


# ---------------------------------------------------------------- the list
def leads(tenant: str, stage: str = "", q: str = "", city: str = "", lane: str = "", has_phone: bool = False,
          due: bool = False, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    ensure_tables()
    from .service import _filters
    conds = _filters(tenant, q, city, "", lane, has_phone, False, None)
    with session() as s:
        qy = (s.query(LeadContact, LeadStage).outerjoin(LeadStage, (LeadStage.contact_id == LeadContact.id)
                                                        & (LeadStage.tenant_id == tenant)).filter(*conds))
        if stage == "opted_out":
            qy = qy.filter(LeadContact.opt_out.is_(True))
        elif stage in STAGES:
            qy = qy.filter(LeadContact.opt_out.is_(False))
            qy = qy.filter((LeadStage.stage == stage) | (LeadStage.stage.is_(None))) if stage == "new" \
                else qy.filter(LeadStage.stage == stage)
        if due:
            qy = qy.filter(LeadStage.follow_on.isnot(None), LeadStage.follow_on <= _today(), LeadContact.opt_out.is_(False))
        total = qy.count()
        got = qy.order_by(LeadContact.fetched_at.desc(), LeadContact.id).offset(max(0, offset)).limit(min(max(1, limit), 500)).all()
        return {"total": total, "rows": [view(c, st) for c, st in got], "counts": counts(tenant)}


def counts(tenant: str) -> dict[str, int]:
    ensure_tables()
    with session() as s:
        total = s.query(LeadContact).filter(LeadContact.tenant_id == tenant).count()
        out_ = s.query(LeadContact).filter(LeadContact.tenant_id == tenant, LeadContact.opt_out.is_(True)).count()
        by = dict.fromkeys(STAGES, 0)
        for stg, n in (s.query(LeadStage.stage, LeadContact.id).join(LeadContact, LeadContact.id == LeadStage.contact_id)
                       .filter(LeadStage.tenant_id == tenant, LeadContact.opt_out.is_(False)).all()):
            if stg in by:
                by[stg] += 1
        by["new"] = total - out_ - sum(v for k, v in by.items() if k != "new")
        return {"all": total, **by, "opted_out": out_}


# ---------------------------------------------------------------- one lead
def lead(tenant: str, cid: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        c = _contact(s, tenant, cid)
        st = _stage_row(s, tenant, c.id, make=False)
        v = view(c, st)
        tl: list[dict[str, Any]] = []
        run = s.get(LeadRun, c.run_id) if c.run_id else None
        tl.append({"kind": "found", "at": _iso(_aware(c.fetched_at)),
                   "text": f"Found on {v['source_name']}" + (f' · search "{run.ask[:80]}"' if run is not None and run.ask else "")})
        if c.enriched_at:
            tl.append({"kind": "found", "at": _iso(_aware(c.enriched_at)), "text": f"Contact filled in from {c.enriched_from or 'its website'}"})
        for o in s.query(LeadOutreach).filter(LeadOutreach.tenant_id == tenant, LeadOutreach.contact_id == c.id).all():
            word = {"campaign_list": "Put in a WhatsApp campaign list", "campaign_sent": "WhatsApp sent from the campaign desk",
                    "email_sent": "Email sent"}.get(o.kind, o.kind)
            tl.append({"kind": "sent", "at": _iso(_aware(o.at)), "text": word})
        for e in s.query(LeadEvent).filter(LeadEvent.tenant_id == tenant, LeadEvent.contact_id == c.id).all():
            tl.append({"kind": e.kind, "at": _iso(_aware(e.at)), "text": e.text, "by": e.by})
        tl.sort(key=lambda x: x.get("at") or "", reverse=True)
        return {"lead": v, "timeline": tl[:80], "stages": [{"key": k, "name": STAGE_NAME[k]} for k in STAGES]}


def _event(s, tenant: str, cid: str, kind: str, text: str, by: str = "owner") -> None:
    s.add(LeadEvent(tenant_id=tenant, contact_id=cid, kind=kind, text=str(text or "")[:2000], by=str(by or "owner")[:40]))


def set_stage(tenant: str, ids: list[str], stage: str, by: str = "owner") -> dict[str, Any]:
    ensure_tables()
    if stage not in STAGES:
        raise DeskError("Stage is one of: " + ", ".join(STAGES))
    ids = [str(i) for i in (ids or []) if str(i)][:500]
    if not ids:
        raise DeskError("Pick at least one lead.")
    done = skipped = 0
    with session() as s:
        for cid in ids:
            c = _contact(s, tenant, cid)
            if c.opt_out:
                skipped += 1
                continue
            r = _stage_row(s, tenant, c.id)
            if r.stage != stage:
                _event(s, tenant, c.id, "stage", f"Stage: {STAGE_NAME.get(r.stage, r.stage)} → {STAGE_NAME[stage]}", by)
                r.stage, r.updated_at = stage, now()
                if stage in ("won", "not_interested"):
                    r.follow_on = None
            done += 1
    return {"ok": True, "changed": done, "skipped_opted_out": skipped, "stage": STAGE_NAME[stage]}


def set_follow(tenant: str, ids: list[str], on: str, note: str = "", by: str = "owner") -> dict[str, Any]:
    ensure_tables()
    try:
        d = date.fromisoformat(str(on)[:10]) if on else None
    except ValueError:
        raise DeskError("The follow-up date must look like 2026-11-28.") from None
    ids = [str(i) for i in (ids or []) if str(i)][:500]
    if not ids:
        raise DeskError("Pick at least one lead.")
    with session() as s:
        for cid in ids:
            c = _contact(s, tenant, cid)
            if c.opt_out and d is not None:
                raise DeskError(f"{c.name or 'This business'} opted out - no follow-up can be set.")
            r = _stage_row(s, tenant, c.id)
            r.follow_on, r.follow_note, r.updated_at = d, str(note or "")[:600], now()
            _event(s, tenant, c.id, "follow", (f"Follow-up set for {d.isoformat()}" + (f": {note}" if note else "")) if d else "Follow-up cleared", by)
    return {"ok": True, "leads": len(ids), "follow_on": _iso(d)}


def add_note(tenant: str, cid: str, text: str, by: str = "owner") -> dict[str, Any]:
    ensure_tables()
    text = str(text or "").strip()
    if not text:
        raise DeskError("The note is empty.")
    with session() as s:
        c = _contact(s, tenant, cid)
        _event(s, tenant, c.id, "note", text, by)
    return {"ok": True}


def draft(tenant: str, cid: str, text: str, by: str = "owner") -> dict[str, Any]:
    """A message for ONE lead: the words + a wa.me link that opens HER WhatsApp with them. Nothing is sent here."""
    ensure_tables()
    text = str(text or "").strip()
    if not text:
        raise DeskError("Write the message first.")
    with session() as s:
        c = _contact(s, tenant, cid)
        if c.opt_out:
            raise DeskError(f"{c.name or 'This business'} opted out - no message can be drafted for them.")
        phone = re.sub(r"\D", "", c.phone or "")
        link = f"https://wa.me/{phone}?text={quote(text[:1500])}" if phone else ""
        _event(s, tenant, c.id, "draft", "Message drafted: " + text[:300], by)
        return {"ok": True, "lead": c.name, "text": text, "whatsapp_link": link,
                "note": ("Opens WhatsApp on her phone with this message; she presses send herself." if link
                         else "This business has no phone. Copy the text, or fill in the contact first.")}


# ---------------------------------------------------------------- her file (attached in the chat or on the desk)
_COLS = {"name": ["name", "business", "business name", "company", "firm", "shop", "clinic", "naam", "party", "customer name",
                  "customer", "contact name", "client"],
         "phone": ["whatsapp", "mobile", "phone", "number", "contact", "mob", "cell", "tel"],
         "email": ["email", "e-mail", "mail"], "city": ["city", "town", "district", "location"],
         "category": ["category", "type", "business type", "industry", "segment"], "address": ["address", "area", "locality"],
         "website": ["website", "site", "url", "web"], "pincode": ["pincode", "pin", "zip", "postal"], "state": ["state"]}


def file_rows(name: str, data: bytes) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Her CSV / Excel -> rows in the store's own fields (columns matched by name), and which column fed which field."""
    from .importer import _pick, _rows_from_file
    header, raw = _rows_from_file(name, data)
    if not header:
        raise DeskError("The file looks empty. The first row should have column names like Name, Mobile and City.")
    used: dict[str, str] = {}
    for f, keys in _COLS.items():
        col = _pick([h for h in header if h not in used.values()], keys)
        if col:
            used[f] = col
    if "name" not in used and "phone" not in used:
        raise DeskError("No name or phone column found. Columns seen: " + ", ".join(header[:12]) + ".")
    rows = [{f: (r.get(col) if r.get(col) is not None else "") for f, col in used.items()} for r in raw]
    return rows, used


def import_file(tenant: str, file_id: str, ask: str = "") -> dict[str, Any]:
    """A file she attached -> her list into the store (the engine's own HER_DATA lane: caps, one row per business,
    the file named as the source)."""
    from ..gstp.service import GstError, _load_file
    from . import service as S
    try:
        name, data = _load_file(tenant, str(file_id or ""))
    except GstError as e:
        raise DeskError(str(e)) from None
    if not name.lower().endswith((".csv", ".xlsx", ".xlsm", ".txt", ".tsv")):
        raise DeskError(f"{name} is not a list. Send a CSV or Excel (.xlsx) file with names and phone numbers.")
    rows, used = file_rows(name, data)
    out = S.run_her_data(tenant, ask or f"her file {name}", rows, name)
    return {**out, "file": name, "columns_used": used, "rows_in_file": len(rows)}


# ---------------------------------------------------------------- today
def today(tenant: str) -> dict[str, Any]:
    ensure_tables()
    t = _today()
    with session() as s:
        due = (s.query(LeadContact, LeadStage).join(LeadStage, LeadStage.contact_id == LeadContact.id)
               .filter(LeadStage.tenant_id == tenant, LeadStage.follow_on.isnot(None), LeadStage.follow_on <= t,
                       LeadContact.opt_out.is_(False)).order_by(LeadStage.follow_on).limit(30).all())
        week = s.query(LeadContact).filter(LeadContact.tenant_id == tenant,
                                           LeadContact.fetched_at >= datetime.now(timezone.utc) - timedelta(days=7)).count()
        no_phone = s.query(LeadContact).filter(LeadContact.tenant_id == tenant, LeadContact.phone == "",
                                               LeadContact.opt_out.is_(False)).count()
        running = (s.query(LeadRun).filter(LeadRun.tenant_id == tenant, LeadRun.status.in_(("PLANNED", "RUNNING")))
                   .order_by(LeadRun.created_at.desc()).limit(5).all())
        from .service import _view as run_view
        recent = (s.query(LeadRun).filter(LeadRun.tenant_id == tenant).order_by(LeadRun.created_at.desc()).limit(6).all())
        return {"counts": counts(tenant), "new_this_week": week, "no_phone": no_phone,
                "due": [{**view(c, st), "late_days": (t - st.follow_on).days} for c, st in due],
                "running": [run_view(r) for r in running], "recent_runs": [run_view(r) for r in recent],
                "saved": saved(tenant)}


# ---------------------------------------------------------------- saved searches
def saved(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        return [{"id": r.id, "name": r.name, "lane": r.lane, "lane_name": LANE_NAME.get(r.lane, r.lane),
                 "params": json.loads(r.params or "{}"), "weekly": bool(r.weekly), "runs": r.runs,
                 "last_run_at": _iso(r.last_run_at), "last_kept": r.last_kept}
                for r in s.query(LeadSaved).filter(LeadSaved.tenant_id == tenant).order_by(LeadSaved.created_at.desc()).limit(50)]


def save_search(tenant: str, name: str, lane: str, params: dict, weekly: bool = False) -> dict[str, Any]:
    ensure_tables()
    lane = str(lane or "").upper()
    if lane not in SAVE_LANES:
        raise DeskError("A search can be saved for IndiaMART, Google Maps or the public Maps listings scan.")
    if weekly and lane not in WEEKLY_LANES:
        raise DeskError("Only the free searches (IndiaMART, the public Maps listings scan) can run every week by "
                        "themselves. A Google Maps search costs money, so it runs only when you tap Run.")
    p = {k: params.get(k) for k in ("search_term", "query", "city", "kinds", "near", "max_rows", "details", "sweep_km", "zoom")
         if params and params.get(k) not in (None, "")}
    if lane == "SCRAPE":
        p.setdefault("query", p.get("search_term") or "")
        if not str(p.get("near") or p.get("city") or "").strip():
            raise DeskError("Say where to scan (a city or area).")
    if not (p.get("search_term") or p.get("kinds") or p.get("query")):
        raise DeskError("Say what to search for.")
    with session() as s:
        r = LeadSaved(tenant_id=tenant, name=(str(name or "").strip() or str(p.get("search_term") or p.get("kinds")))[:200],
                      lane=lane, params=json.dumps(p), weekly=bool(weekly))
        s.add(r)
        s.flush()
        rid = r.id
    return {"ok": True, "id": rid, "saved": saved(tenant)}


def drop_saved(tenant: str, sid: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        r = s.get(LeadSaved, sid)
        if r is None or r.tenant_id != tenant:
            raise DeskError("That saved search was not found.")
        s.delete(r)
    return {"ok": True}


async def run_saved(tenant: str, sid: str) -> dict[str, Any]:
    from . import service as S
    ensure_tables()
    with session() as s:
        r = s.get(LeadSaved, sid)
        if r is None or r.tenant_id != tenant:
            raise DeskError("That saved search was not found.")
        lane, p, name = r.lane, json.loads(r.params or "{}"), r.name
    ask = f"saved search: {name}"
    if lane == "REGISTRY":
        out = await S.run_indiamart(tenant, ask, str(p.get("search_term") or ""), str(p.get("city") or ""), None, "", "",
                                    int(p.get("max_rows") or 200))
    elif lane == "OFFICIAL_API":
        kinds = p.get("kinds") or [str(p.get("search_term") or "")]
        out = await S.run_places(tenant, ask, kinds if isinstance(kinds, list) else [str(kinds)], str(p.get("near") or p.get("city") or ""),
                                 details=bool(p.get("details", True)), max_rows=int(p.get("max_rows") or 50))
    elif lane == "SCRAPE":
        return start_scan(tenant, ask, p, saved_id=sid)
    else:
        raise DeskError("This saved search cannot run.")
    kept = int(((out or {}).get("run") or {}).get("kept") or 0)
    with session() as s:
        r = s.get(LeadSaved, sid)
        if r is not None:
            r.runs, r.last_run_at, r.last_kept = (r.runs or 0) + 1, now(), kept
    return out


# ---------------------------------------------------------------- the public Maps listings scan from the desk
# A scan reads up to 400 map squares at one request a second, so it can take many minutes: the desk, the Lead
# Generation chat and the weekly run START it here and come back at once; the run shows under "Running now" and
# lands in Recent searches when it ends. One scan per account at a time. The walls are service.run_scrape's own
# (her switch, caps checked before anything runs, stop at a block page, business facts only).
_SCANS: dict[str, Any] = {}


def scan_params(p: dict | None) -> dict[str, Any]:
    p = dict(p or {})
    q = str(p.get("query") or p.get("search_term") or "").strip()
    near = str(p.get("near") or p.get("city") or "").strip()
    try:
        km = min(20.0, max(1.0, float(p.get("sweep_km") or 3)))
    except (TypeError, ValueError):
        km = 3.0
    try:
        rows = min(5000, max(1, int(p.get("max_rows") or 500)))
    except (TypeError, ValueError):
        rows = 500
    return {"query": q, "near": near, "sweep_km": km, "max_rows": rows, "zoom": int(p.get("zoom") or 15)}


def scan_running(tenant: str) -> bool:
    t = _SCANS.get(tenant)
    return bool(t is not None and not t.done())


def start_scan(tenant: str, ask: str, params: dict | None, saved_id: str = "") -> dict[str, Any]:
    """Check, then start the public Maps scan in the background. Raises DeskError with the reason when it cannot
    start (switch off, no query / place, over a limit, one already running)."""
    import asyncio
    from . import service as S
    p = scan_params(params)
    if not p["query"]:
        raise DeskError("Say which kind of business to scan for (for example 'dentists').")
    if not p["near"]:
        raise DeskError("Say where to scan (a city or area).")
    if not S.scrape_opted_in(tenant):
        raise DeskError("The public Maps listings scan is off. Switch it on in Quality & settings (or say yes in the "
                        "chat), then start it again.")
    if scan_running(tenant):
        raise DeskError("A scan is already running. It shows under Running now; start the next one when it ends.")
    card = S.plan(tenant, ask, ["SCRAPE"], p["near"], planned_rows=p["max_rows"])
    if not card.get("ok"):
        raise DeskError("; ".join(card.get("why") or []) or card.get("cap_refusal") or card.get("need") or "The scan was refused.")

    async def _go() -> None:
        kept = 0
        try:
            out = await S.run_scrape(tenant, ask, p["query"], near=p["near"], sweep_km=p["sweep_km"], zoom=p["zoom"],
                                     max_rows=p["max_rows"])
            kept = int(((out or {}).get("run") or {}).get("kept") or 0)
        except Exception:   # noqa: BLE001 - the run row carries the reason; nothing else to do here
            import logging
            logging.getLogger(__name__).exception("leads scan failed")
        if saved_id:
            with session() as s:
                r = s.get(LeadSaved, saved_id)
                if r is not None:
                    r.runs, r.last_run_at, r.last_kept = (r.runs or 0) + 1, now(), kept

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        raise DeskError("The scan could not be started here.") from None
    _SCANS[tenant] = loop.create_task(_go())
    return {"ok": True, "started": True, "lane": "SCRAPE", "scan": p,
            "note": (f"Scanning public Google Maps listings for '{p['query']}' around {p['near']} ({p['sweep_km']:g} km across, "
                     f"at most {p['max_rows']} businesses), one request a second. It can take several minutes; it shows "
                     "under Running now and the businesses land in Leads when it ends. Nothing is sent to anyone.")}


async def weekly_tick(limit: int = 5) -> int:
    """The worker: free weekly searches that are due (7 days since the last run). A paid route is never here."""
    ensure_tables()
    cut = datetime.now(timezone.utc) - timedelta(days=7)
    with session() as s:
        due = [(r.tenant_id, r.id) for r in s.query(LeadSaved).filter(LeadSaved.weekly.is_(True), LeadSaved.lane.in_(WEEKLY_LANES)).all()
               if r.last_run_at is None or _aware(r.last_run_at) <= cut][:limit]
    n = 0
    from .service import scrape_opted_in
    for tenant, sid in due:
        try:
            with session() as s:
                r = s.get(LeadSaved, sid)
                lane = r.lane if r is not None else ""
            if lane == "SCRAPE" and (not scrape_opted_in(tenant) or scan_running(tenant)):
                continue                       # her switch is off (or one is running): not this week, nothing marked
            await run_saved(tenant, sid)
            n += 1
        except Exception:   # noqa: BLE001 - one failing search never stops the others; it is tried next week
            with session() as s:
                r = s.get(LeadSaved, sid)
                if r is not None:
                    r.last_run_at = now()
    return n


# ---------------------------------------------------------------- quality
def _nm(v: str) -> str:
    v = re.sub(r"[^a-z0-9 ]", " ", str(v or "").lower())
    v = re.sub(r"\b(the|pvt|ltd|private|limited|and|co|llp|m s|ms)\b", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def quality(tenant: str) -> dict[str, Any]:
    ensure_tables()
    old = datetime.now(timezone.utc) - timedelta(days=90)
    with session() as s:
        rows = s.query(LeadContact).filter(LeadContact.tenant_id == tenant).limit(20000).all()
        stages = {r.contact_id: r for r in s.query(LeadStage).filter(LeadStage.tenant_id == tenant).all()}
        groups: dict[tuple[str, str], list[LeadContact]] = {}
        for c in rows:
            k = (_nm(c.name), str(c.city or "").strip().lower())
            if k[0]:
                groups.setdefault(k, []).append(c)
        pairs = []
        for (nm, city), cs in groups.items():
            if len(cs) > 1:
                pairs.append({"name": cs[0].name, "city": cs[0].city, "leads": [view(c, stages.get(c.id)) for c in cs[:5]]})
        no_phone = [view(c, stages.get(c.id)) for c in rows if not c.phone and not c.opt_out]
        dead = [view(c, stages.get(c.id)) for c in rows
                if c.website and re.search(r"dead|did not open|not reachable|no answer|failed|error", c.enrich_note or "", re.I)]
        stale = [view(c, stages.get(c.id)) for c in rows if not c.opt_out and (stages.get(c.id) is None or stages[c.id].stage == "new")
                 and _aware(c.fetched_at) is not None and _aware(c.fetched_at) < old]
    return {"maybe_same": pairs[:50], "maybe_same_count": len(pairs), "no_phone": no_phone[:50], "no_phone_count": len(no_phone),
            "dead_sites": dead[:50], "dead_sites_count": len(dead), "untouched": stale[:50], "untouched_count": len(stale)}


# ---------------------------------------------------------------- hand-offs (her tap)
def ids_for(tenant: str, ids: list[str] | None = None, stage: str = "") -> list[str]:
    if ids:
        return [str(i) for i in ids][:20000]
    if stage:
        got = leads(tenant, stage=stage, limit=500)
        return [r["id"] for r in got["rows"]]
    return []


def to_telecaller(tenant: str, ids: list[str], confirm: bool = False) -> dict[str, Any]:
    """Put leads on the Telecaller's call list. Two taps like the campaign hand-off. They are a cold business list,
    so the Telecaller marks them as no-consent; a person still makes every call."""
    ensure_tables()
    ids = [str(i) for i in ids or []][:2000]
    if not ids:
        raise DeskError("Pick at least one lead.")
    with session() as s:
        rows = [c for c in s.query(LeadContact).filter(LeadContact.tenant_id == tenant, LeadContact.id.in_(ids)).all()]
    go = [c for c in rows if c.phone and not c.opt_out]
    card = {"rows": len(go), "rows_without_phone": sum(1 for c in rows if not c.phone and not c.opt_out),
            "opt_out_excluded": sum(1 for c in rows if c.opt_out)}
    if not confirm:
        return {"ok": True, "confirm_required": True, **card,
                "say": "These are businesses that have not asked to be called. The Telecaller marks them as a cold list; "
                       "you or your team make every call."}
    from ..telecall import service as TC
    added = 0
    for c in go:
        try:
            TC.add_lead(tenant, name=c.name, phone=c.phone, source="list", purpose="sales", need=c.category or "",
                        city=c.city or "", notes=f"From Lead Generation ({LANE_NAME.get(c.source_lane, c.source_lane)})",
                        consent=False)
            added += 1
        except Exception:   # noqa: BLE001 - a number the Telecaller refuses (not a mobile) is skipped, counted
            continue
    with session() as s:
        for c in go:
            _event(s, tenant, c.id, "handoff", "Put on the Telecaller's call list")
    return {"ok": True, "confirmed": True, "added": added, **card}


def lists(tenant: str) -> dict[str, Any]:
    """Lists made from the store (the campaign desk's copies), with what was sent from each, + saved searches."""
    ensure_tables()
    from ..db import LeadList
    from .models import LeadListRef
    with session() as s:
        out = []
        for ll in (s.query(LeadList).filter(LeadList.tenant_id == tenant, LeadList.source_filename.like("leads-store:%"))
                   .order_by(LeadList.created_at.desc()).limit(40).all()):
            cids = [r.contact_id for r in s.query(LeadListRef).filter(LeadListRef.tenant_id == tenant, LeadListRef.list_id == ll.id).all()]
            sent = (s.query(LeadOutreach).filter(LeadOutreach.tenant_id == tenant, LeadOutreach.contact_id.in_(cids or ["-"]),
                                                 LeadOutreach.kind.in_(("campaign_sent", "email_sent"))).count())
            out.append({"id": ll.id, "name": ll.name, "rows": ll.valid, "made_at": _iso(_aware(ll.created_at)), "sent": sent})
    c = counts(tenant)
    smart = [{"stage": k, "name": STAGE_NAME[k], "rows": c.get(k, 0)} for k in ("interested", "contacted", "new") if c.get(k)]
    return {"lists": out, "saved": saved(tenant), "smart": smart}


def summary(tenant: str) -> dict[str, Any]:
    """What the Lead Generation chat knows each turn."""
    from ..employee import hire
    st = hire.status(tenant, "leads")
    if st not in ("hired", "paused"):
        return {"hired": False}
    d = today(tenant)
    trust = ""
    try:
        with session() as s:
            trust = (hire._view(hire._row(s, tenant, "leads")).get("trust") or "")
    except Exception:   # noqa: BLE001
        pass
    from .service import scrape_opted_in
    return {"hired": True, "status": st, "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
            "counts": d["counts"], "new_this_week": d["new_this_week"], "no_phone": d["no_phone"],
            "due": [{"id": x["id"], "name": x["name"], "city": x["city"], "follow_on": x["follow_on"], "note": x["follow_note"]}
                    for x in d["due"][:10]],
            "running": [{"id": r["id"], "ask": r["ask"], "status": r["status"], "kept": r["kept"]} for r in d["running"]],
            "saved": [{"id": x["id"], "name": x["name"], "lane": x["lane_name"], "weekly": x["weekly"]} for x in d["saved"][:10]],
            "scrape_on": scrape_opted_in(tenant), "scan_running": scan_running(tenant)}
