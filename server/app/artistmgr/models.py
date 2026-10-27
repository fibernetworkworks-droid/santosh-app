"""Tables of the Artist Sahayak (all prefixed artistmgr_). JSON kept in Text columns (pattern of banquet / interior)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ArtistmgrSettings(Base):
    __tablename__ = "artistmgr_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agency: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    commission_pct: Mapped[float | None] = mapped_column(Float, nullable=True)      # HER % on show fees (None = not said)
    royalty_pct: Mapped[float | None] = mapped_column(Float, nullable=True)         # HER % on royalties (None = none)
    same_city_gap: Mapped[int] = mapped_column(Integer, default=120)                # minutes between two gigs in one city
    travel_gap: Mapped[int] = mapped_column(Integer, default=480)                   # minutes between gigs in other / unknown cities
    hold_hours: Mapped[int] = mapped_column(Integer, default=72)
    advance_pct: Mapped[float] = mapped_column(Float, default=50.0)
    balance_days: Mapped[int] = mapped_column(Integer, default=0)                   # balance due N days before the show (0 = show day)
    distributors: Mapped[str] = mapped_column(Text, default="[]")                   # [{name, share_pct, lead_days, payout, notes}]
    terms: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    gig_seq: Mapped[int] = mapped_column(Integer, default=0)
    rel_seq: Mapped[int] = mapped_column(Integer, default=0)
    inv_seq: Mapped[int] = mapped_column(Integer, default=0)
    pay_seq: Mapped[int] = mapped_column(Integer, default=0)


class ArtistmgrArtist(Base):
    __tablename__ = "artistmgr_artists"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ar"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(16), default="singer")
    genre: Mapped[str] = mapped_column(String(80), default="")
    art_form: Mapped[str] = mapped_column(String(12), default="")                  # folk | classical | "" (GST exemption check)
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    city: Mapped[str] = mapped_column(String(60), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    members: Mapped[str] = mapped_column(Text, default="[]")                        # [{name, role, phone, split_pct}]
    fee_note: Mapped[str] = mapped_column(Text, default="")                         # her own words about fees (never a guess)
    min_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    commission_pct: Mapped[float | None] = mapped_column(Float, nullable=True)      # override for this artist
    rider: Mapped[str] = mapped_column(Text, default="{}")                          # {tech:[], hospitality:[], travel, stay, notes}
    regs: Mapped[str] = mapped_column(Text, default="{}")                           # {iprs: {status, ref, note}, ...}
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArtistmgrGig(Base):
    __tablename__ = "artistmgr_gigs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ag"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    artist_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    status: Mapped[str] = mapped_column(String(10), default="enquiry")            # enquiry|hold|confirmed|done|cancelled
    event: Mapped[str] = mapped_column(String(160), default="")
    event_type: Mapped[str] = mapped_column(String(12), default="")
    promoter: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    promoter_gstin: Mapped[str] = mapped_column(String(15), default="")
    city: Mapped[str] = mapped_column(String(60), default="")
    venue: Mapped[str] = mapped_column(String(160), default="")
    day: Mapped[str] = mapped_column(String(10), default="", index=True)
    start: Mapped[str] = mapped_column(String(5), default="")
    end: Mapped[str] = mapped_column(String(5), default="")
    set_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    advance_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ticketed: Mapped[bool] = mapped_column(Boolean, default=False)
    travel_by: Mapped[str] = mapped_column(String(20), default="")                # promoter | artist | ""
    travel_trip: Mapped[str] = mapped_column(String(40), default="")              # travel Sahayak trip number
    hold_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offer_text: Mapped[str] = mapped_column(Text, default="")                     # the promoter's words (data)
    payments: Mapped[str] = mapped_column(Text, default="[]")                     # [{id, amount, mode, ref, day}]
    tds: Mapped[float] = mapped_column(Float, default=0.0)                        # promoter's deduction (her word)
    expenses: Mapped[str] = mapped_column(Text, default="[]")                     # [{what, amount, paid_by manager|artist|promoter}]
    contract_ok: Mapped[str] = mapped_column(String(64), default="")
    invoice_no: Mapped[str] = mapped_column(String(30), default="")
    payout_id: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    cancel: Mapped[str] = mapped_column(Text, default="{}")
    log: Mapped[str] = mapped_column(Text, default="[]")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArtistmgrBlock(Base):
    """Her own blocked days for an artist (leave, studio, travel). Gigs on these days are refused like a clash."""
    __tablename__ = "artistmgr_blocks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ab"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    artist_id: Mapped[str] = mapped_column(String(40), index=True)
    day_from: Mapped[str] = mapped_column(String(10))
    day_to: Mapped[str] = mapped_column(String(10))
    note: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ArtistmgrRelease(Base):
    __tablename__ = "artistmgr_releases"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    artist_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    title: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(10), default="single")               # single | ep | album
    day: Mapped[str] = mapped_column(String(10), default="")
    distributor: Mapped[str] = mapped_column(String(80), default="")
    upc: Mapped[str] = mapped_column(String(14), default="")
    label: Mapped[str] = mapped_column(String(120), default="")
    tracks: Mapped[str] = mapped_column(Text, default="[]")                       # [{title, isrc, writers [{name, role, share, ipi}], ...}]
    artwork: Mapped[bool] = mapped_column(Boolean, default=False)
    done: Mapped[str] = mapped_column(Text, default="{}")                          # step key -> date she ticked
    status: Mapped[str] = mapped_column(String(10), default="plan")               # plan | final | delivered | live
    final_hash: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArtistmgrRoyalty(Base):
    """Royalty lines exactly as in HER statement (IPRS / ISAMRA / PPL / distributor / YouTube); never estimated."""
    __tablename__ = "artistmgr_royalties"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ry"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    artist_id: Mapped[str] = mapped_column(String(40), index=True)
    source: Mapped[str] = mapped_column(String(20), default="")
    period: Mapped[str] = mapped_column(String(20), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    release_id: Mapped[str] = mapped_column(String(40), default="")
    ref: Mapped[str] = mapped_column(String(80), default="")
    payout_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArtistmgrCard(Base):
    """Everything that waits for HER tap: offer | contract | confirm | invoice | pay | payout | message | release."""
    __tablename__ = "artistmgr_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ac"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ref_id: Mapped[str] = mapped_column(String(40), index=True, default="")       # gig / artist / release id
    kind: Mapped[str] = mapped_column(String(10))
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")            # waiting|approved|rejected|stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ArtistmgrPayout(Base):
    """A statement to the artist / members, approved by her tap (money card). She pays; Hoola only writes it down."""
    __tablename__ = "artistmgr_payouts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ap"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(14), default="")
    artist_id: Mapped[str] = mapped_column(String(40), index=True)
    lines: Mapped[str] = mapped_column(Text, default="[]")
    total: Mapped[float] = mapped_column(Float, default=0.0)
    splits: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(10), default="approved")          # approved | paid
    paid_ref: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArtistmgrAlert(Base):
    __tablename__ = "artistmgr_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
