"""Tables of the Vakil Sahayak (lawyer's junior), all prefixed vakil_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class VakilSettings(Base):
    __tablename__ = "vakil_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    advocate: Mapped[str] = mapped_column(String(120), default="")
    enrolment_no: Mapped[str] = mapped_column(String(40), default="")      # Bar Council enrolment (printed on drafts)
    office: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(40), default="")
    place: Mapped[str] = mapped_column(String(80), default="")
    closed_dates: Mapped[str] = mapped_column(Text, default="[]")          # her court holidays / vacation days (ISO)
    closed_weekdays: Mapped[str] = mapped_column(String(20), default="6")   # 0=Mon .. 6=Sun, comma list
    remind_days: Mapped[str] = mapped_column(String(40), default="30,15,7,3,1,0")
    morning_time: Mapped[str] = mapped_column(String(5), default="08:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class VakilClient(Base):
    __tablename__ = "vakil_clients"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("vc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(16), default="individual")   # individual | company | firm | other
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    id_ref: Mapped[str] = mapped_column(String(80), default="")           # {id:...} Pehchaan Locker reference only
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VakilMatter(Base):
    __tablename__ = "vakil_matters"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("vm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    client_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    title: Mapped[str] = mapped_column(String(240), default="")           # "Patil vs Deshmukh"
    kind: Mapped[str] = mapped_column(String(20), default="other")
    side: Mapped[str] = mapped_column(String(16), default="other")
    opposite: Mapped[str] = mapped_column(String(200), default="")
    opposite_advocate: Mapped[str] = mapped_column(String(160), default="")
    opposite_contact: Mapped[str] = mapped_column(String(160), default="")
    court: Mapped[str] = mapped_column(String(200), default="")
    court_no: Mapped[str] = mapped_column(String(80), default="")          # court hall / judge
    case_type: Mapped[str] = mapped_column(String(40), default="")
    case_no: Mapped[str] = mapped_column(String(12), default="")
    case_year: Mapped[str] = mapped_column(String(4), default="")
    case_key: Mapped[str] = mapped_column(String(80), index=True, default="")
    cnr: Mapped[str] = mapped_column(String(16), index=True, default="")
    filing_no: Mapped[str] = mapped_column(String(40), default="")
    acts: Mapped[str] = mapped_column(Text, default="")
    stage: Mapped[str] = mapped_column(String(40), default="")
    next_date: Mapped[str] = mapped_column(String(10), default="")
    next_purpose: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(12), default="pending")    # draft | pending | disposed | closed
    events: Mapped[str] = mapped_column(Text, default="[]")              # list of dates & events [{on, what, src}]
    hearings: Mapped[str] = mapped_column(Text, default="[]")            # [{on, purpose, stage, result, next, src}]
    docs: Mapped[str] = mapped_column(Text, default="{}")                # {key: {state, file_id, note}}
    notes: Mapped[str] = mapped_column(Text, default="")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class VakilDeadline(Base):
    __tablename__ = "vakil_deadlines"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("vd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    matter_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(40), default="")
    label: Mapped[str] = mapped_column(String(200), default="")
    start: Mapped[str] = mapped_column(String(10), default="")
    last_date: Mapped[str] = mapped_column(String(10), default="")
    calc: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(10), default="open")      # open | done | dropped
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VakilDraft(Base):
    __tablename__ = "vakil_drafts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("vf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    matter_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    number: Mapped[str] = mapped_column(String(12), default="")
    kind: Mapped[str] = mapped_column(String(20), default="")            # adjournment | vakalatnama | dates_events | synopsis | notice_reply | note
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    blanks: Mapped[int] = mapped_column(Integer, default=0)
    file_id: Mapped[str] = mapped_column(String(60), default="")
    lekhak_doc: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VakilCard(Base):
    """Things that only her tap decides: filing, a message / notice to someone outside, a fee request."""
    __tablename__ = "vakil_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("vk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    matter_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    number: Mapped[str] = mapped_column(String(12), default="")
    kind: Mapped[str] = mapped_column(String(10), default="message")     # filing | message | fee
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")   # waiting | approved | rejected | stale | done
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VakilFee(Base):
    __tablename__ = "vakil_fees"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("vg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    matter_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(10), default="agreed")      # agreed | requested | received | expense
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    ref: Mapped[str] = mapped_column(String(60), default="")
    card_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VakilOnce(Base):
    __tablename__ = "vakil_once"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
