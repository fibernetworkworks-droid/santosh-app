"""Tables of the Driver Sahayak (all prefixed drivers_). Dates of duties / trips are her local dates (YYYY-MM-DD) and
local times (HH:MM), like the other Sahayaks keep shop days."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class DriversSettings(Base):
    __tablename__ = "drivers_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    rules: Mapped[str] = mapped_column(Text, default="{}")            # her limits {day_h, week_h, spread_h, between_h, days_row}
    notes: Mapped[str] = mapped_column(Text, default="[]")            # her own rule lines
    vehicles: Mapped[str] = mapped_column(Text, default="{}")         # number -> {gvw_kg, kind, kmpl} (when no fleet module)
    morning_time: Mapped[str] = mapped_column(String(5), default="07:00")
    evening_time: Mapped[str] = mapped_column(String(5), default="19:00")
    police_months: Mapped[int] = mapped_column(Integer, default=24)  # her recheck period (starter)
    fuel_tolerance: Mapped[float] = mapped_column(Float, default=0.2)
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    last_evening: Mapped[str] = mapped_column(String(10), default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)              # D-001 drivers
    duty_seq: Mapped[int] = mapped_column(Integer, default=0)         # DU-0001
    trip_seq: Mapped[int] = mapped_column(Integer, default=0)         # TS-0001
    msg_seq: Mapped[int] = mapped_column(Integer, default=0)          # M-0001


class DriversDriver(Base):
    __tablename__ = "drivers_drivers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(10), default="")          # D-001
    name: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(10), default="")
    dl_ref: Mapped[str] = mapped_column(String(30), default="")        # {id:...} in the Pehchaan Locker
    dl_masked: Mapped[str] = mapped_column(String(30), default="")
    classes: Mapped[str] = mapped_column(Text, default="[]")
    dl_valid_to: Mapped[str] = mapped_column(String(10), default="")
    medical_valid_to: Mapped[str] = mapped_column(String(10), default="")
    badge: Mapped[str] = mapped_column(String(40), default="")
    badge_valid_to: Mapped[str] = mapped_column(String(10), default="")
    police_on: Mapped[str] = mapped_column(String(10), default="")
    hazardous_valid_to: Mapped[str] = mapped_column(String(10), default="")
    member_id: Mapped[str] = mapped_column(String(40), default="")     # Hoola Employee team member (Hoola Network)
    payroll_name: Mapped[str] = mapped_column(String(80), default="")  # name / code in the payroll register
    vehicle: Mapped[str] = mapped_column(String(40), default="")       # usual vehicle
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    reminded: Mapped[str] = mapped_column(Text, default="{}")          # {doc: "date:window"}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DriversLeave(Base):
    __tablename__ = "drivers_leaves"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    driver_id: Mapped[str] = mapped_column(String(40), index=True)
    start: Mapped[str] = mapped_column(String(10), default="")
    end: Mapped[str] = mapped_column(String(10), default="")
    kind: Mapped[str] = mapped_column(String(10), default="leave")    # leave | sick | off | unpaid
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DriversDuty(Base):
    __tablename__ = "drivers_duties"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("du"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")        # DU-0001
    driver_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    start: Mapped[str] = mapped_column(String(5), default="")
    end: Mapped[str] = mapped_column(String(5), default="")
    break_min: Mapped[int] = mapped_column(Integer, default=0)
    vehicle: Mapped[str] = mapped_column(String(40), default="")
    fleet_id: Mapped[str] = mapped_column(String(40), default="")
    route: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(12), default="trip")      # trip | local | standby | school | night
    hazardous: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(12), default="planned")  # planned | done | absent | cancelled
    checks: Mapped[str] = mapped_column(Text, default="{}")
    forced: Mapped[str] = mapped_column(String(300), default="")       # her reason when a law flag was accepted
    note: Mapped[str] = mapped_column(Text, default="")
    told: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DriversTrip(Base):
    __tablename__ = "drivers_trips"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")        # TS-0001
    driver_id: Mapped[str] = mapped_column(String(40), index=True)
    duty_id: Mapped[str] = mapped_column(String(40), default="")
    day: Mapped[str] = mapped_column(String(10), index=True)
    vehicle: Mapped[str] = mapped_column(String(40), default="", index=True)
    route: Mapped[str] = mapped_column(String(200), default="")
    start_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_time: Mapped[str] = mapped_column(String(5), default="")
    end_time: Mapped[str] = mapped_column(String(5), default="")
    fuel_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    fuel_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    tolls: Mapped[float | None] = mapped_column(Float, nullable=True)
    expenses: Mapped[str] = mapped_column(Text, default="[]")           # [{what, amount}]
    source: Mapped[str] = mapped_column(String(12), default="words")    # words | photo | driver | app
    file_id: Mapped[str] = mapped_column(String(60), default="")
    raw: Mapped[str] = mapped_column(Text, default="")                  # what was read (masked)
    status: Mapped[str] = mapped_column(String(10), default="ok")       # draft (to check) | ok | rejected
    flags: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DriversMessage(Base):
    __tablename__ = "drivers_messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(10), default="")        # M-0001
    driver_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(14), default="custom")    # duty | licence | sheet | custom
    ref: Mapped[str] = mapped_column(String(60), default="")           # duty id / doc / day it is about
    text: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")    # draft | sent | cancelled
    via: Mapped[str] = mapped_column(String(10), default="")            # self | business | hoola
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
