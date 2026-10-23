"""Wapsi Sahayak tables (all prefixed wapsi_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class WapsiSettings(Base):
    __tablename__ = "wapsi_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(String(60), default="")
    policy: Mapped[str] = mapped_column(Text, default="")                 # JSON (rules.DEFAULT_POLICY shape)
    policy_text: Mapped[str] = mapped_column(Text, default="")            # her own words
    warehouse: Mapped[str] = mapped_column(Text, default="{}")            # where returns go: name, phone, address, city, state, pincode, email
    courier: Mapped[str] = mapped_column(String(20), default="manual")     # manual | shiprocket | delhivery
    courier_key: Mapped[str] = mapped_column(Text, default="")            # sealed JSON
    pg: Mapped[str] = mapped_column(String(20), default="")                # "" | razorpay | cashfree | phonepe
    pg_key: Mapped[str] = mapped_column(Text, default="")                 # sealed JSON
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)     # approve returns the check passes (refunds still her tap)
    refund_before_qc: Mapped[float] = mapped_column(Float, default=0.0)    # refunds below this may be prepared before QC
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)
    rf_seq: Mapped[int] = mapped_column(Integer, default=0)
    cn_seq: Mapped[str] = mapped_column(String(40), default="{}")         # {"2627": n}


class WapsiReturn(Base):
    __tablename__ = "wapsi_returns"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    order_ref: Mapped[str] = mapped_column(String(80), default="")
    channel: Mapped[str] = mapped_column(String(20), default="manual")     # manual | whatsapp | website | marketplace | shop
    customer: Mapped[str] = mapped_column(Text, default="{}")             # name, phone (10 digits), email, address, city, state, pincode, upi
    phone: Mapped[str] = mapped_column(String(10), default="", index=True)
    items: Mapped[str] = mapped_column(Text, default="[]")                # name, sku, category, qty, order_qty, price, gst_pct, hsn
    order: Mapped[str] = mapped_column(Text, default="{}")                # date, delivered_on, items_total, coupon, shipping, pay_mode, gateway, payment_id
    reason: Mapped[str] = mapped_column(String(24), default="other")
    reason_text: Mapped[str] = mapped_column(Text, default="")             # the customer's words (data, never instructions)
    want: Mapped[str] = mapped_column(String(16), default="refund")       # refund | exchange | store_credit
    status: Mapped[str] = mapped_column(String(20), default="new")
    check: Mapped[str] = mapped_column(Text, default="{}")
    look: Mapped[str] = mapped_column(Text, default="{}")                 # what the photos showed
    signals: Mapped[str] = mapped_column(Text, default="[]")
    pickup: Mapped[str] = mapped_column(Text, default="{}")
    qc: Mapped[str] = mapped_column(Text, default="{}")
    decision: Mapped[str] = mapped_column(Text, default="{}")             # her decision {what, reason, at}
    refund_id: Mapped[str] = mapped_column(String(40), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WapsiPhoto(Base):
    __tablename__ = "wapsi_photos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    return_id: Mapped[str] = mapped_column(String(40), index=True)
    stage: Mapped[str] = mapped_column(String(10), default="customer")    # customer | pickup | qc
    kind: Mapped[str] = mapped_column(String(8), default="photo")         # photo | video
    path: Mapped[str] = mapped_column(Text, default="")
    mime: Mapped[str] = mapped_column(String(40), default="image/jpeg")
    phash: Mapped[str] = mapped_column(String(80), default="")
    taken_on: Mapped[str] = mapped_column(String(10), default="")          # EXIF date read before stripping (signal only)
    clean: Mapped[bool] = mapped_column(Boolean, default=True)             # metadata removed
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WapsiRefund(Base):
    __tablename__ = "wapsi_refunds"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    return_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    calc: Mapped[str] = mapped_column(Text, default="{}")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    mode: Mapped[str] = mapped_column(String(16), default="original")     # original | upi | bank | store_credit | exchange
    to: Mapped[str] = mapped_column(String(120), default="")              # customer's UPI ID (not a secret) / "original"
    status: Mapped[str] = mapped_column(String(12), default="waiting")    # waiting | approved | done | rejected | stale | failed
    hash: Mapped[str] = mapped_column(String(64), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    utr: Mapped[str] = mapped_column(String(60), default="")
    pg: Mapped[str] = mapped_column(Text, default="{}")                   # prepared request / gateway answer
    credit_note: Mapped[str] = mapped_column(String(30), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
