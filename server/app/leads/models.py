"""Tables of the LEADS engine (docs/LEADS_PLAN.md section 7), prefix lead_.

- lead_runs: one row per run - the ask, the lanes the plan chose, the plan itself (cells / filters / caps, so a
  resume continues the PLAN, not just the file), the status, the counters (found / kept / duped-away / refused),
  the bill and the run's own provenance (tool versions). The research/store.py R4 pattern.
- lead_contacts: one BUSINESS per row, keyed by key_type + key_value (kgmid > cid > place_id > name+address hash;
  her-data rows key on the E.164 phone). Provenance is ROW COLUMNS, not a side file. opt_out is the row's erasure
  flag the campaign desk honours.
- lead_outreach: every outreach EVENT (list it joined, campaign sent, email sent) with the desk that did it -
  the opt-out ledger extended to leads. The engine WRITES the ledger row only when SHE taps; it never sends.

All three are registered in db.init_db on day one (the v0.190.1 lesson: a lazily-imported model never reaches
create_all() and the live DB stays without its table) AND self-heal via ensure_tables() for databases born earlier.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class LeadRun(Base):
    __tablename__ = "lead_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ask: Mapped[str] = mapped_column(Text, default="")
    place: Mapped[str] = mapped_column(String(200), default="")            # the one question's second half
    lanes: Mapped[str] = mapped_column(Text, default="[]")                 # lanes the plan chose, JSON
    plan: Mapped[str] = mapped_column(Text, default="{}")                  # cells / filters / caps, JSON
    status: Mapped[str] = mapped_column(String(10), default="PLANNED", index=True)  # rules.STATUSES
    found: Mapped[int] = mapped_column(Integer, default=0)                 # rows the lanes saw
    kept: Mapped[int] = mapped_column(Integer, default=0)                  # rows written with provenance
    duped: Mapped[int] = mapped_column(Integer, default=0)                 # same business, already in the store
    refused: Mapped[int] = mapped_column(Integer, default=0)               # bad phone / missing key / filter
    bill: Mapped[str] = mapped_column(Text, default="{}")                  # itemised cost (P0: zero, L0 is free)
    provenance: Mapped[str] = mapped_column(Text, default="{}")            # the run's own tool versions
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LeadContact(Base):
    __tablename__ = "lead_contacts"
    __table_args__ = (UniqueConstraint("tenant_id", "key_type", "key_value", name="uq_lead_contact_key"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    key_type: Mapped[str] = mapped_column(String(14), default="phone_e164")   # rules.KEY_TYPES
    key_value: Mapped[str] = mapped_column(String(120), index=True, default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    category: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(80), default="", index=True)
    state: Mapped[str] = mapped_column(String(80), default="")
    pincode: Mapped[str] = mapped_column(String(10), default="")
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)    # E.164 digits, no "+"
    website: Mapped[str] = mapped_column(String(300), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    email_grade: Mapped[str] = mapped_column(String(10), default="")          # rules.EMAIL_GRADES (P2 fills)
    socials: Mapped[dict] = mapped_column(JSON, default=dict)                 # {"linkedin": "..."} - HER site only, P2
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)        # FACTS only
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # the COUNT, never the text
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_lane: Mapped[str] = mapped_column(String(14), index=True, default="")   # rules.LANES
    source_url: Mapped[str] = mapped_column(String(500), default="")          # the row's provenance, no row without it
    parser_version: Mapped[str] = mapped_column(String(20), default="")       # which code read the source
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enriched_from: Mapped[str] = mapped_column(String(300), default="")   # the site URL the P2 pass read
    enrich_note: Mapped[str] = mapped_column(Text, default="")            # the pick's reason / the dead-site note
    opt_out: Mapped[bool] = mapped_column(Boolean, default=False)             # her erasure flag, campaign desk honours it


class LeadOutreach(Base):
    """The opt-out ledger: what left the store and through which desk - written on HER tap, never by the engine."""
    __tablename__ = "lead_outreach"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lo"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(20), default="")                 # campaign_list | campaign_sent | email_sent
    ref: Mapped[str] = mapped_column(String(120), default="")                 # list id / campaign id / email id
    desk: Mapped[str] = mapped_column(String(20), default="")                 # campaign | email
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LeadCapDay(Base):
    """Per-tenant per-day counters for the caps - a small ledger, not a query over the store (forget() deletes
    rows and must not erase the memory that they were counted). lives in leadscap's module shape (mapsbill)."""
    __tablename__ = "lead_cap_days"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lcd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)                  # YYYY-MM-DD UTC
    rows_kept: Mapped[int] = mapped_column(Integer, default=0)
    runs_started: Mapped[int] = mapped_column(Integer, default=0)


class LeadScrapeOptIn(Base):
    """v0.543.0 P3: the SCRAPE lane's per-tenant opt-in - OFF by default, ON only by the owner's explicit act
    (the amended CLAUDE.md rule: 'opt-in per tenant and OFF by default, ... which no session may move'). One
    row per tenant; the flip records WHO flipped and WHEN, because a lane this loud must be able to say who
    turned it on. It is NOT personal data - it is the lane's permission slip, so leads_forget never deletes it."""
    __tablename__ = "lead_scrape_optins"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    on: Mapped[bool] = mapped_column(Boolean, default=False)
    actor: Mapped[str] = mapped_column(String(64), default="")     # who flipped it (owner tap only)
    note: Mapped[str] = mapped_column(Text, default="")            # the walls quoted at flip time
    at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LeadListRef(Base):
    """A lead_contacts row handed to the campaign desk as a Lead row: the join the export and the opt-out ledger
    both read (a campaign list is a COPY; this is the thread back to the source row)."""
    __tablename__ = "lead_list_refs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("llr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[str] = mapped_column(String(40), index=True)
    lead_row_id: Mapped[int] = mapped_column(Integer, index=True, default=0)  # leads.id the copy became
    list_id: Mapped[str] = mapped_column(String(40), index=True, default="")  # lead_lists.id, ForeignKey kept loose
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_ready = False


def ensure_tables() -> None:
    """Self-heal, the v0.190.1 lesson: databases born before v0.540.0 have no lead_ tables and every query would
    die 'no such table'. The first call after deploy creates them in place."""
    global _ready
    if _ready:
        return
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        for t in (LeadRun, LeadContact, LeadOutreach, LeadCapDay, LeadScrapeOptIn, LeadListRef):
            t.__table__.create(eng, checkfirst=True)
    _ready = True
