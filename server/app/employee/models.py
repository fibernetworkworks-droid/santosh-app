from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class EmployeeProfile(Base):
    """The owner's business and the job Hoola does in it."""
    __tablename__ = "employee_profiles"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_by: Mapped[str] = mapped_column(String(80), default="")
    role: Mapped[str] = mapped_column(String(32), default="front_desk")
    business_name: Mapped[str] = mapped_column(String(120), default="")
    business_kind: Mapped[str] = mapped_column(String(60), default="")
    about: Mapped[str] = mapped_column(Text, default="")              # what the business sells / does, in her words
    hours: Mapped[str] = mapped_column(Text, default="{}")            # {"open": "10:00", "close": "20:00", "days": [0..6]}
    after_hours: Mapped[str] = mapped_column(String(20), default="note")   # note | answer | quiet
    report_time: Mapped[str] = mapped_column(String(5), default="20:30")
    last_report_date: Mapped[str] = mapped_column(String(10), default="")
    job_sheet: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="")              # extra do / don't lines from the owner
    duties: Mapped[str] = mapped_column(Text, default="[]")           # role "custom": the duties she picked
    reply_to_staff: Mapped[bool] = mapped_column(Boolean, default=True)
    # v0.59 (nullable so _add_missing_columns can add them to a v0.58 database)
    preset: Mapped[str | None] = mapped_column(String(32), nullable=True, default="")       # clinic | shop | isp | ca | coaching | ...
    upi_id: Mapped[str | None] = mapped_column(String(120), nullable=True, default="")      # where customers pay (their own UPI app)
    upi_name: Mapped[str | None] = mapped_column(String(80), nullable=True, default="")
    slot_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True, default=30)
    inbox_on: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)     # Hoola answers the business WhatsApp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TeamMember(Base):
    """A person in the business. manager = may instruct Hoola for every duty of the job; staff = only the duties given."""
    __tablename__ = "employee_team"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(20), default="")
    address: Mapped[str] = mapped_column(String(160), default="")    # Hoola Network address, optional
    role: Mapped[str] = mapped_column(String(12), default="staff")    # manager | staff
    duties: Mapped[str] = mapped_column(Text, default="[]")           # staff only: duty ids they may instruct
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DutyTrust(Base):
    """How far Hoola may go alone in one duty. seekh = asks every time, saathi = routine alone / big things ask,
    bharosa = alone within limits. Grows only when the owner promotes; a correction drops it one level."""
    __tablename__ = "employee_trust"
    __table_args__ = (UniqueConstraint("tenant_id", "duty", name="uq_employee_trust"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    duty: Mapped[str] = mapped_column(String(32))
    level: Mapped[str] = mapped_column(String(10), default="seekh")
    per_day: Mapped[int] = mapped_column(Integer, default=0)          # 0 = the level's default cap
    approved: Mapped[int] = mapped_column(Integer, default=0)         # owner taps "Haan" in a row (reset on Mana / correction)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    corrections: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EmployeeAsk(Base):
    """An action Hoola wanted to take on its own but its trust says: ask first. Runs only after the owner's tap."""
    __tablename__ = "employee_asks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ea"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    actor: Mapped[str] = mapped_column(String(80), default="")
    duty: Mapped[str] = mapped_column(String(32), default="")
    tool: Mapped[str] = mapped_column(String(80))
    args: Mapped[str] = mapped_column(Text, default="{}")
    why: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="pending")   # pending | done | failed | declined | expired
    result: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEntry(Base):
    """One thing Hoola did (or was stopped from doing) while working as the employee. Arguments are masked."""
    __tablename__ = "employee_audit"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("au"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    actor: Mapped[str] = mapped_column(String(80), default="owner")
    duty: Mapped[str] = mapped_column(String(32), default="")
    tool: Mapped[str] = mapped_column(String(80), default="")
    kind: Mapped[str] = mapped_column(String(10), default="action")   # read | action | big | meta (pause, trust change, team task arrived)
    outcome: Mapped[str] = mapped_column(String(12), default="done")  # done | error | asked | refused | paused
    detail: Mapped[str] = mapped_column(Text, default="")
    approved_by: Mapped[str] = mapped_column(String(80), default="")
    wrong: Mapped[bool] = mapped_column(Boolean, default=False)
    wrong_note: Mapped[str] = mapped_column(Text, default="")


class StaffTask(Base):
    """Work a team member sent from their own Hoola (Hoola Network kind staff_task). The worker runs it as an agent turn
    with actor staff:<member>; trust and the member's duties still decide every action."""
    __tablename__ = "employee_tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("st"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    member_id: Mapped[str] = mapped_column(String(40), default="")
    member_name: Mapped[str] = mapped_column(String(80), default="")
    peer: Mapped[str] = mapped_column(String(160), default="")
    thread_key: Mapped[str] = mapped_column(String(60), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="pending")   # pending | running | done | failed
    result: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------- v0.59 business WhatsApp inbox
class BizChannel(Base):
    """The business's own WhatsApp number on the official Cloud API (phone_number_id -> tenant)."""
    __tablename__ = "employee_channels"
    phone_number_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    display_number: Mapped[str] = mapped_column(String(24), default="")
    token: Mapped[str] = mapped_column(Text, default="")              # sealed; "" = the server's WA_TOKEN (same Meta app)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BizContact(Base):
    """One customer who wrote to the business on WhatsApp."""
    __tablename__ = "employee_contacts"
    __table_args__ = (UniqueConstraint("tenant_id", "wa_id", name="uq_employee_contact"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    wa_id: Mapped[str] = mapped_column(String(20))                    # their number, digits with country code
    name: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    human: Mapped[bool] = mapped_column(Boolean, default=False)       # the owner / staff took over: Hoola stays quiet
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_reply: Mapped[bool] = mapped_column(Boolean, default=False)
    unread: Mapped[int] = mapped_column(Integer, default=0)
    last_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    last_text: Mapped[str] = mapped_column(Text, default="")
    channel: Mapped[str] = mapped_column(String(40), default="")      # phone_number_id it came in on
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BizMessage(Base):
    __tablename__ = "employee_messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[str] = mapped_column(String(40), index=True)
    direction: Mapped[str] = mapped_column(String(4))                 # in | out
    by: Mapped[str] = mapped_column(String(80), default="")           # customer | hoola | owner | staff:<id> | system
    kind: Mapped[str] = mapped_column(String(16), default="text")     # text | image | document | audio | video | location | other
    text: Mapped[str] = mapped_column(Text, default="")
    wa_msg_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    status: Mapped[str] = mapped_column(String(12), default="")       # sent | delivered | read | failed | held
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class BizAppointment(Base):
    """Hoola's own appointment book (works without Google Calendar)."""
    __tablename__ = "employee_appointments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ap"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[str] = mapped_column(String(40), default="")
    name: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    minutes: Mapped[int] = mapped_column(Integer, default=30)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="booked")  # booked | done | cancelled | no_show
    by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BizDue(Base):
    """Money a customer owes the business (from the owner, a sheet or Tally). Hoola only reminds; nobody's money moves."""
    __tablename__ = "employee_dues"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("du"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    due_date: Mapped[str] = mapped_column(String(10), default="")      # YYYY-MM-DD
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="open")    # open | promised | paid | disputed | written_off
    promised_on: Mapped[str] = mapped_column(String(10), default="")
    reminders: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
