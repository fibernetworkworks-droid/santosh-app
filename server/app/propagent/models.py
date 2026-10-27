"""Tables of the Propagent Sahayak (all prefixed propagent_). Money in rupees (Float); JSON in Text columns."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class PropagentSettings(Base):
    __tablename__ = "propagent_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    agent_name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(16), default="")             # her business number (shown on public pages)
    office: Mapped[str] = mapped_column(String(300), default="")
    state: Mapped[str] = mapped_column(String(4), default="MH")
    city: Mapped[str] = mapped_column(String(80), default="")
    rera_agent_no: Mapped[str] = mapped_column(String(40), default="")
    rera_valid_until: Mapped[str] = mapped_column(String(10), default="")
    coc: Mapped[str] = mapped_column(String(10), default="")               # Certificate of Competency date ('' = not given)
    gstin: Mapped[str] = mapped_column(String(20), default="")
    gst_on: Mapped[bool] = mapped_column(Boolean, default=False)
    gst_pct: Mapped[float] = mapped_column(Float, default=18.0)
    sale_pct: Mapped[float] = mapped_column(Float, default=0.0)           # HER usual brokerage % per side (0 = not set)
    rent_months: Mapped[float] = mapped_column(Float, default=0.0)        # HER usual months of rent per side
    rates: Mapped[str] = mapped_column(Text, default="{}")                # {area key: {stamp_pct, cess_pct, women_less_pct, reg_pct, reg_cap, reg_flat}}
    visit_minutes: Mapped[int] = mapped_column(Integer, default=30)
    gap_minutes: Mapped[int] = mapped_column(Integer, default=30)         # her travel guess between visits when Maps can't tell
    stale_days: Mapped[int] = mapped_column(Integer, default=45)
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    terms: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    listing_seq: Mapped[int] = mapped_column(Integer, default=0)
    lead_seq: Mapped[int] = mapped_column(Integer, default=0)
    visit_seq: Mapped[int] = mapped_column(Integer, default=0)
    deal_seq: Mapped[int] = mapped_column(Integer, default=0)
    card_seq: Mapped[int] = mapped_column(Integer, default=0)


class PropagentListing(Base):
    __tablename__ = "propagent_listings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    purpose: Mapped[str] = mapped_column(String(8), default="sale")
    kind: Mapped[str] = mapped_column(String(16), default="flat")
    title: Mapped[str] = mapped_column(String(200), default="")
    project: Mapped[str] = mapped_column(String(160), default="")
    new_project: Mapped[bool] = mapped_column(Boolean, default=False)      # under construction / new in a RERA project
    rera_project_no: Mapped[str] = mapped_column(String(40), default="")
    locality: Mapped[str] = mapped_column(String(120), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    pin: Mapped[str] = mapped_column(String(6), default="")
    address: Mapped[str] = mapped_column(Text, default="")                 # full address: never on a public page
    bhk: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carpet_sqft: Mapped[float] = mapped_column(Float, default=0.0)
    built_sqft: Mapped[float] = mapped_column(Float, default=0.0)
    plot_sqft: Mapped[float] = mapped_column(Float, default=0.0)
    floor: Mapped[str] = mapped_column(String(20), default="")
    facing: Mapped[str] = mapped_column(String(20), default="")
    furnishing: Mapped[str] = mapped_column(String(12), default="")
    parking: Mapped[str] = mapped_column(String(60), default="")
    age_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    rent: Mapped[float] = mapped_column(Float, default=0.0)
    deposit: Mapped[float] = mapped_column(Float, default=0.0)
    maintenance: Mapped[float] = mapped_column(Float, default=0.0)
    negotiable: Mapped[bool] = mapped_column(Boolean, default=False)
    available_from: Mapped[str] = mapped_column(String(10), default="")
    amenities: Mapped[str] = mapped_column(Text, default="[]")
    description: Mapped[str] = mapped_column(Text, default="")
    owner_name: Mapped[str] = mapped_column(String(120), default="")
    owner_phone: Mapped[str] = mapped_column(String(16), default="")
    owner_nri: Mapped[bool] = mapped_column(Boolean, default=False)
    mandate: Mapped[str] = mapped_column(Text, default="{}")              # {consent, on, exclusive, commission_pct, months, file_id, until}
    status: Mapped[str] = mapped_column(String(14), default="draft")
    public: Mapped[bool] = mapped_column(Boolean, default=False)
    public_hash: Mapped[str] = mapped_column(String(64), default="")
    page_token: Mapped[str] = mapped_column(String(40), default="", index=True)
    published: Mapped[str] = mapped_column(Text, default="[]")            # [{where, at}]
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PropagentPhoto(Base):
    __tablename__ = "propagent_photos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    listing_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(8), default="photo")          # photo | qr | plan
    path: Mapped[str] = mapped_column(Text, default="")
    sha: Mapped[str] = mapped_column(String(64), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PropagentLead(Base):
    __tablename__ = "propagent_leads"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(16), default="", index=True)
    role: Mapped[str] = mapped_column(String(8), default="buyer")          # buyer | tenant
    need: Mapped[str] = mapped_column(Text, default="{}")                 # parse_need() + her edits
    words: Mapped[str] = mapped_column(Text, default="")                  # what they asked (masked)
    source: Mapped[str] = mapped_column(String(16), default="enquiry")
    consent: Mapped[bool] = mapped_column(Boolean, default=True)          # agreed to be contacted
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    stage: Mapped[str] = mapped_column(String(12), default="new")
    next_at: Mapped[str] = mapped_column(String(16), default="")          # local 'YYYY-MM-DD HH:MM'
    next_what: Mapped[str] = mapped_column(String(200), default="")
    telecall_id: Mapped[str] = mapped_column(String(40), default="")
    shared: Mapped[str] = mapped_column(Text, default="[]")               # listing ids sent to them
    feedback: Mapped[str] = mapped_column(Text, default="{}")             # {listing id: liked|no|price|...}
    notes: Mapped[str] = mapped_column(Text, default="")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PropagentVisit(Base):
    __tablename__ = "propagent_visits"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    lead_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(10), default="")
    stops: Mapped[str] = mapped_column(Text, default="[]")                # [{listing, number, at 'HH:MM', where, km, feedback}]
    start: Mapped[str] = mapped_column(String(5), default="")
    status: Mapped[str] = mapped_column(String(12), default="planned")    # planned | done | cancelled | no_show
    route_known: Mapped[bool] = mapped_column(Boolean, default=False)
    appt_id: Mapped[str] = mapped_column(String(40), default="")
    reminded: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PropagentDeal(Base):
    __tablename__ = "propagent_deals"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    listing_id: Mapped[str] = mapped_column(String(40), index=True)
    lead_id: Mapped[str] = mapped_column(String(40), default="")
    purpose: Mapped[str] = mapped_column(String(8), default="sale")
    price: Mapped[float] = mapped_column(Float, default=0.0)              # agreed (sale) / rent (rent)
    deposit: Mapped[float] = mapped_column(Float, default=0.0)
    market_value: Mapped[float] = mapped_column(Float, default=0.0)       # ready reckoner value she gives
    token: Mapped[float] = mapped_column(Float, default=0.0)
    token_mode: Mapped[str] = mapped_column(String(20), default="")
    token_ref: Mapped[str] = mapped_column(String(40), default="")
    rate_area: Mapped[str] = mapped_column(String(60), default="")
    women: Mapped[bool] = mapped_column(Boolean, default=False)
    buyer_nri: Mapped[bool] = mapped_column(Boolean, default=False)
    seller_nri: Mapped[bool] = mapped_column(Boolean, default=False)
    tenant_business: Mapped[bool] = mapped_column(Boolean, default=False)
    loan: Mapped[bool] = mapped_column(Boolean, default=False)
    society: Mapped[bool] = mapped_column(Boolean, default=False)
    agreement_by: Mapped[str] = mapped_column(String(10), default="")
    registration_by: Mapped[str] = mapped_column(String(10), default="")
    ids: Mapped[str] = mapped_column(Text, default="[]")                  # [{side, person, id, ref, kind, masked}] (Pehchaan Locker)
    commission: Mapped[str] = mapped_column(Text, default="{}")           # {buyer:{pct|months, amount, gst, total}, seller:{...}}
    received: Mapped[str] = mapped_column(Text, default="[]")             # [{side, amount, mode, ref, on}] her word
    checklist: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(14), default="draft")      # draft | token | agreement | registered | done | fell
    log: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PropagentCard(Base):
    """Everything that waits for HER tap: publish (listing public), message (client / owner), document (money on paper)."""
    __tablename__ = "propagent_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(10), default="message")
    sub: Mapped[str] = mapped_column(String(24), default="")              # page|copy|sheet / lead|owner / token_receipt|offer|...
    ref: Mapped[str] = mapped_column(String(40), default="", index=True)
    body: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    money: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(10), default="waiting")    # waiting | approved | rejected | stale | sent
    result: Mapped[str] = mapped_column(Text, default="{}")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(String(300), default="")
    conv: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PropagentAlert(Base):
    __tablename__ = "propagent_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
