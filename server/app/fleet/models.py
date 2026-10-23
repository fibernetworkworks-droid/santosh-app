"""Tables of the Fleet Sahayak (all prefixed fleet_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class FleetSettings(Base):
    __tablename__ = "fleet_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    home_state: Mapped[str] = mapped_column(String(4), default="")          # MH ...
    diesel_rate: Mapped[float] = mapped_column(Float, default=0.0)         # HER rate per litre (0 = not given)
    petrol_rate: Mapped[float] = mapped_column(Float, default=0.0)
    cng_rate: Mapped[float] = mapped_column(Float, default=0.0)
    toll_per_km: Mapped[str] = mapped_column(Text, default="{}")           # {vehicle type: rupees per km} (her numbers)
    fill_pct: Mapped[float] = mapped_column(Float, default=85.0)           # how full a body can be packed by volume
    low_kmpl_pct: Mapped[float] = mapped_column(Float, default=25.0)       # km/l this much below usual = flag
    idle_days: Mapped[int] = mapped_column(Integer, default=3)
    avg_speed: Mapped[float] = mapped_column(Float, default=0.0)           # her planning speed km/h (0 = no duration guess)
    morning_time: Mapped[str] = mapped_column(String(5), default="08:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    trip_seq: Mapped[int] = mapped_column(Integer, default=0)
    spend_seq: Mapped[int] = mapped_column(Integer, default=0)


class FleetVehicle(Base):
    __tablename__ = "fleet_vehicles"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    reg: Mapped[str] = mapped_column(String(20), default="")               # spaced: MH 30 AB 1234
    reg_key: Mapped[str] = mapped_column(String(20), default="", index=True)  # MH30AB1234
    vtype: Mapped[str] = mapped_column(String(16), default="truck")
    make: Mapped[str] = mapped_column(String(60), default="")
    model: Mapped[str] = mapped_column(String(80), default="")
    fuel: Mapped[str] = mapped_column(String(10), default="diesel")
    bs: Mapped[str] = mapped_column(String(4), default="")                 # BS4 / BS6
    reg_date: Mapped[str] = mapped_column(String(10), default="")
    capacity_t: Mapped[float] = mapped_column(Float, default=0.0)          # payload tonnes
    capacity_cbm: Mapped[float] = mapped_column(Float, default=0.0)
    body: Mapped[str] = mapped_column(Text, default="{}")                  # {l, w, h} metres
    axles: Mapped[int] = mapped_column(Integer, default=0)
    tank_l: Mapped[float] = mapped_column(Float, default=0.0)
    owner_name: Mapped[str] = mapped_column(String(120), default="")       # RC owner (own / attached / leased)
    ownership: Mapped[str] = mapped_column(String(12), default="own")      # own | attached | leased
    national: Mapped[bool] = mapped_column(Boolean, default=False)         # runs on a national permit
    driver: Mapped[str] = mapped_column(String(80), default="")            # usual driver (name only; drivers sahayak owns drivers)
    odo: Mapped[float] = mapped_column(Float, default=0.0)                 # latest known odometer
    odo_at: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(12), default="active")      # active | workshop | sold
    fastag_note: Mapped[str] = mapped_column(String(160), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FleetDoc(Base):
    __tablename__ = "fleet_docs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    vehicle_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="other")
    number: Mapped[str] = mapped_column(String(60), default="")
    issued: Mapped[str] = mapped_column(String(10), default="")
    expires: Mapped[str] = mapped_column(String(10), default="")
    expires_guess: Mapped[bool] = mapped_column(Boolean, default=False)    # suggested, not from her paper
    issuer: Mapped[str] = mapped_column(String(120), default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    windows: Mapped[str] = mapped_column(Text, default="")                 # her own reminder days, JSON list ("" = kind default)
    reminded: Mapped[str] = mapped_column(Text, default="{}")              # {expires date: window}
    not_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class FleetFuel(Base):
    __tablename__ = "fleet_fuel"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ff"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    vehicle_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(10), default="")
    litres: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    odo: Mapped[float] = mapped_column(Float, default=0.0)
    full: Mapped[bool] = mapped_column(Boolean, default=True)
    station: Mapped[str] = mapped_column(String(120), default="")
    source: Mapped[str] = mapped_column(String(12), default="manual")      # manual | card
    ref: Mapped[str] = mapped_column(String(80), default="", index=True)   # fuel card txn id (dedupe)
    kmpl: Mapped[float | None] = mapped_column(Float, nullable=True)
    flags: Mapped[str] = mapped_column(Text, default="[]")
    by: Mapped[str] = mapped_column(String(60), default="Owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FleetServiceItem(Base):
    """A schedule line per vehicle (every N km / months) with when it was last done."""
    __tablename__ = "fleet_service_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fs"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    vehicle_id: Mapped[str] = mapped_column(String(40), index=True)
    item: Mapped[str] = mapped_column(String(80), default="")
    every_km: Mapped[float] = mapped_column(Float, default=0.0)
    every_months: Mapped[int] = mapped_column(Integer, default=0)
    last_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_on: Mapped[str] = mapped_column(String(10), default="")
    starter: Mapped[bool] = mapped_column(Boolean, default=True)           # from starter list (maker's manual decides)
    reminded: Mapped[str] = mapped_column(String(20), default="")


class FleetEvent(Base):
    """Service done / tyre / breakdown / expense / challan rows (one log for cost per km)."""
    __tablename__ = "fleet_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fe"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    vehicle_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="expense")       # service | tyre | breakdown | expense | challan
    day: Mapped[str] = mapped_column(String(10), default="")
    what: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)              # what she says was spent (0 = not yet / unknown)
    odo: Mapped[float | None] = mapped_column(Float, nullable=True)
    data: Mapped[str] = mapped_column(Text, default="{}")                  # tyre: position, brand, serial, life_km; breakdown: place, hours; challan: number, offence, status
    status: Mapped[str] = mapped_column(String(12), default="done")        # done | open | paid (challan) | removed (tyre)
    spend_id: Mapped[str] = mapped_column(String(40), default="")
    by: Mapped[str] = mapped_column(String(60), default="Owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FleetTrip(Base):
    __tablename__ = "fleet_trips"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ft"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # TR-0001
    origin: Mapped[str] = mapped_column(String(160), default="")
    destination: Mapped[str] = mapped_column(String(160), default="")
    stops: Mapped[str] = mapped_column(Text, default="[]")
    origin_state: Mapped[str] = mapped_column(String(4), default="")
    dest_state: Mapped[str] = mapped_column(String(4), default="")
    day: Mapped[str] = mapped_column(String(10), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")                 # [{name, weight_kg, cbm, count, dims}]
    vehicle_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    driver: Mapped[str] = mapped_column(String(80), default="")
    driver_phone: Mapped[str] = mapped_column(String(20), default="")
    km: Mapped[float | None] = mapped_column(Float, nullable=True)
    km_source: Mapped[str] = mapped_column(String(10), default="")         # maps | her
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    toll: Mapped[float | None] = mapped_column(Float, nullable=True)       # her number for this trip
    estimate: Mapped[str] = mapped_column(Text, default="{}")
    checks: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(12), default="planned")     # planned | assigned | started | done | cancelled
    odo_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    odo_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    ref: Mapped[str] = mapped_column(String(80), default="")               # her LR / order ref (logistics sahayak owns LR / e-way)
    notes: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class FleetSpend(Base):
    """Any spend (service, tyres, permit fee, tax, challan, insurance, repair): waits for HER tap; Hoola never pays."""
    __tablename__ = "fleet_spends"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # FS-0001
    vehicle_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    kind: Mapped[str] = mapped_column(String(12), default="other")
    what: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    vendor: Mapped[str] = mapped_column(String(120), default="")
    where: Mapped[str] = mapped_column(Text, default="")                   # how / where she pays (official portal / workshop)
    checks: Mapped[str] = mapped_column(Text, default="[]")
    link_id: Mapped[str] = mapped_column(String(40), default="")           # event / doc / service item it is for
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")     # waiting | approved | rejected | done | stale
    asked_by: Mapped[str] = mapped_column(String(80), default="Hoola")
    reason: Mapped[str] = mapped_column(Text, default="")
    paid_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    paid_ref: Mapped[str] = mapped_column(String(80), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FleetAlert(Base):
    """Alerts already told (once each)."""
    __tablename__ = "fleet_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)        # tenant:kind:target:window
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
