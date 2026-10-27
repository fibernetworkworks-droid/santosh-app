"""Tables of the Influencer Sahayak (all prefixed influencer_). JSON kept in Text columns (pattern of banquet / interior)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class InfluencerSettings(Base):
    __tablename__ = "influencer_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agency: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    gst_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    lut: Mapped[bool] = mapped_column(Boolean, default=False)              # LUT filed this FY (exports without IGST)
    state: Mapped[str] = mapped_column(String(2), default="")              # GST state code (from GSTIN when given)
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    commission_pct: Mapped[float | None] = mapped_column(Float, nullable=True)   # HER default cut (None = not said)
    pay_days: Mapped[int] = mapped_column(Integer, default=30)             # brand payment terms she offers
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    terms: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    cr_seq: Mapped[int] = mapped_column(Integer, default=0)
    deal_seq: Mapped[int] = mapped_column(Integer, default=0)
    post_seq: Mapped[int] = mapped_column(Integer, default=0)
    inv_seq: Mapped[int] = mapped_column(Integer, default=0)


class InfluencerCreator(Base):
    __tablename__ = "influencer_creators"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ic"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # C-001
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    language: Mapped[str] = mapped_column(String(60), default="")
    niche: Mapped[str] = mapped_column(String(160), default="")
    handles: Mapped[str] = mapped_column(Text, default="[]")               # [{platform, handle, followers, on}]
    follower_log: Mapped[str] = mapped_column(Text, default="[]")          # [{platform, followers, on}] as SHE typed
    qualification: Mapped[str] = mapped_column(String(200), default="")    # health / nutrition credential (as she says)
    sebi_reg: Mapped[str] = mapped_column(String(40), default="")          # SEBI RA / IA registration number
    virtual: Mapped[bool] = mapped_column(Boolean, default=False)          # AI / virtual influencer
    gst_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    pan_ref: Mapped[str] = mapped_column(String(40), default="")           # Pehchaan Locker {id:...}
    pan_masked: Mapped[str] = mapped_column(String(20), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # her commission for THIS creator (None = default)
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(10), default="active")      # active | left | forgotten
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InfluencerRate(Base):
    __tablename__ = "influencer_rates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ir"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    creator_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    platform: Mapped[str] = mapped_column(String(16), default="")
    fmt: Mapped[str] = mapped_column(String(16), default="")
    price: Mapped[float] = mapped_column(Float, default=0.0)               # HER number, before GST
    usage_days: Mapped[int] = mapped_column(Integer, default=0)            # brand may reuse for N days (0 = organic only)
    usage_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class InfluencerDeal(Base):
    __tablename__ = "influencer_deals"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("id"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # D-0001
    creator_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    brand: Mapped[str] = mapped_column(String(160), default="")
    brand_contact: Mapped[str] = mapped_column(String(120), default="")
    brand_phone: Mapped[str] = mapped_column(String(20), default="")
    brand_email: Mapped[str] = mapped_column(String(120), default="")
    brand_gstin: Mapped[str] = mapped_column(String(15), default="")
    brand_state: Mapped[str] = mapped_column(String(2), default="")
    brand_foreign: Mapped[bool] = mapped_column(Boolean, default=False)
    sebi_regulated: Mapped[bool] = mapped_column(Boolean, default=False)   # brand is a SEBI-registered entity (broker / AMC ...)
    product: Mapped[str] = mapped_column(String(200), default="")
    brief: Mapped[str] = mapped_column(Text, default="")                   # brand's brief (DATA)
    categories: Mapped[str] = mapped_column(Text, default="[]")
    kind: Mapped[str] = mapped_column(String(10), default="paid")          # paid | barter | affiliate | employee | mixed
    stage: Mapped[str] = mapped_column(String(12), default="lead")
    deliverables: Mapped[str] = mapped_column(Text, default="[]")          # [{platform, fmt, qty, price, due}]
    fee: Mapped[float | None] = mapped_column(Float, nullable=True)        # agreed (from rate card / her words)
    barter_value: Mapped[float] = mapped_column(Float, default=0.0)
    barter_items: Mapped[str] = mapped_column(Text, default="")
    usage_days: Mapped[int] = mapped_column(Integer, default=0)
    excl_category: Mapped[str] = mapped_column(String(80), default="")
    excl_from: Mapped[str] = mapped_column(String(10), default="")
    excl_to: Mapped[str] = mapped_column(String(10), default="")
    pay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    lost_reason: Mapped[str] = mapped_column(Text, default="")
    invoice_no: Mapped[str] = mapped_column(String(24), default="")
    invoice: Mapped[str] = mapped_column(Text, default="{}")               # frozen at her tap
    due_on: Mapped[str] = mapped_column(String(10), default="")
    receipts: Mapped[str] = mapped_column(Text, default="[]")              # [{amount, tds, ref, on}]
    payout: Mapped[str] = mapped_column(Text, default="{}")                # creator share statement + sent
    report: Mapped[str] = mapped_column(Text, default="{}")
    contract_hash: Mapped[str] = mapped_column(String(64), default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InfluencerPost(Base):
    __tablename__ = "influencer_posts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ip"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # P-0001
    deal_id: Mapped[str] = mapped_column(String(40), index=True)
    creator_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    platform: Mapped[str] = mapped_column(String(16), default="")
    fmt: Mapped[str] = mapped_column(String(16), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(12), default="planned")
    caption: Mapped[str] = mapped_column(Text, default="")
    script: Mapped[str] = mapped_column(Text, default="")
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_media: Mapped[bool] = mapped_column(Boolean, default=False)
    ticks: Mapped[str] = mapped_column(Text, default="{}")
    check: Mapped[str] = mapped_column(Text, default="{}")
    brand_notes: Mapped[str] = mapped_column(Text, default="")             # brand's feedback (DATA)
    approved_hash: Mapped[str] = mapped_column(String(64), default="")     # content the brand OK'd (her word)
    live_url: Mapped[str] = mapped_column(String(400), default="")
    posted_on: Mapped[str] = mapped_column(String(10), default="")
    metrics: Mapped[str] = mapped_column(Text, default="{}")


class InfluencerCard(Base):
    __tablename__ = "influencer_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("icd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="")
    deal_id: Mapped[str] = mapped_column(String(40), default="")
    post_id: Mapped[str] = mapped_column(String(40), default="")
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")     # waiting | approved | rejected | stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InfluencerAlert(Base):
    __tablename__ = "influencer_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
