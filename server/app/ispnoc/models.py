"""Tables of the NOC Sahayak (all prefixed ispnoc_). JSON lives in Text columns; new columns must stay nullable / defaulted."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class IspnocSettings(Base):
    __tablename__ = "ispnoc_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    isp_name: Mapped[str] = mapped_column(String(160), default="")
    model: Mapped[str] = mapped_column(String(16), default="isp")            # isp (own licence) | franchise (BSNL / other TIP) | lco
    upstream: Mapped[str] = mapped_column(String(120), default="")           # who gives bandwidth / BNG: "BSNL", "Airtel", ...
    optics: Mapped[str] = mapped_column(String(16), default="gpon_b+")       # rules.OPTICS key used when an OLT has none
    teams: Mapped[str] = mapped_column(Text, default="{}")                   # {team: [{name, phone, email}]}
    sla: Mapped[str] = mapped_column(Text, default="{}")                     # {fault kind: hours}
    bsnl_sla_hours: Mapped[float | None] = mapped_column(Float, nullable=True)   # from HER franchise agreement (blank = not set)
    bsnl_penalty_note: Mapped[str] = mapped_column(String(400), default="")
    window_min: Mapped[int] = mapped_column(Integer, default=15)             # alarms closer than this belong together
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)                     # fault F-0001
    ticket_seq: Mapped[int] = mapped_column(Integer, default=0)              # ticket N-0001
    change_seq: Mapped[int] = mapped_column(Integer, default=0)              # change C-0001


class IspnocSite(Base):
    __tablename__ = "ispnoc_sites"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nsite"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(16), default="pop")            # pop | exchange | cabinet | tower | office
    address: Mapped[str] = mapped_column(String(300), default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    power: Mapped[str] = mapped_column(String(120), default="")             # "UPS 2 h + inverter" (her words)
    contact: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(String(400), default="")


class IspnocOlt(Base):
    __tablename__ = "ispnoc_olts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nolt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    make: Mapped[str] = mapped_column(String(40), default="")               # syrotech | vsol | cdata | bdcom | huawei | zte | other
    model: Mapped[str] = mapped_column(String(80), default="")
    tech: Mapped[str] = mapped_column(String(8), default="gpon")            # gpon | epon
    optics: Mapped[str] = mapped_column(String(16), default="")             # rules.OPTICS key ("" = settings default)
    ip: Mapped[str] = mapped_column(String(64), default="")
    site_id: Mapped[str] = mapped_column(String(40), default="")
    pon_ports: Mapped[int] = mapped_column(Integer, default=0)
    uplinks: Mapped[str] = mapped_column(Text, default="[]")                # ["ge0/9", "xe0/1"]
    upstream: Mapped[str] = mapped_column(String(120), default="")          # who this OLT's uplink goes to
    serial: Mapped[str] = mapped_column(String(80), default="")
    firmware: Mapped[str] = mapped_column(String(80), default="")
    collector_id: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(String(400), default="")


class IspnocSplitter(Base):
    __tablename__ = "ispnoc_splitters"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nspl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")              # "SPL-Akot-Ward5"
    olt_id: Mapped[str] = mapped_column(String(40), default="")
    pon: Mapped[str] = mapped_column(String(20), default="")
    ratio: Mapped[int] = mapped_column(Integer, default=8)                  # 1:N
    level: Mapped[int] = mapped_column(Integer, default=1)                  # 1 = first splitter after the OLT, 2 = second stage
    parent: Mapped[str] = mapped_column(String(120), default="")
    location: Mapped[str] = mapped_column(String(300), default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    route: Mapped[str] = mapped_column(String(160), default="")             # fibre route name from the OLT
    km: Mapped[float | None] = mapped_column(Float, nullable=True)          # fibre km from the OLT


class IspnocOnt(Base):
    __tablename__ = "ispnoc_onts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nont"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    olt_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    pon: Mapped[str] = mapped_column(String(20), default="")                # "0/1" normalised
    onu: Mapped[str] = mapped_column(String(12), default="")
    sn: Mapped[str] = mapped_column(String(40), default="", index=True)     # GPON serial or EPON MAC (upper, no separators)
    customer: Mapped[str] = mapped_column(String(120), default="")
    account: Mapped[str] = mapped_column(String(60), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    splitter: Mapped[str] = mapped_column(String(120), default="")
    route: Mapped[str] = mapped_column(String(160), default="")
    plan: Mapped[str] = mapped_column(String(80), default="")
    rx_base: Mapped[float | None] = mapped_column(Float, nullable=True)     # Rx when it was installed / last good
    rx_last: Mapped[float | None] = mapped_column(Float, nullable=True)
    rx_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="")              # up | down | ""
    state_kind: Mapped[str] = mapped_column(String(16), default="")
    state_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class IspnocEvent(Base):
    __tablename__ = "ispnoc_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nev"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    got_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    olt_id: Mapped[str] = mapped_column(String(40), default="")
    pon: Mapped[str] = mapped_column(String(20), default="")
    onu: Mapped[str] = mapped_column(String(12), default="")
    sn: Mapped[str] = mapped_column(String(40), default="")
    port: Mapped[str] = mapped_column(String(40), default="")               # uplink / ethernet port name
    kind: Mapped[str] = mapped_column(String(20), default="")               # rules.KINDS
    clear: Mapped[bool] = mapped_column(Boolean, default=False)
    rx: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="paste")       # paste | file | email | syslog | snmp | nms | collector | cli
    raw: Mapped[str] = mapped_column(String(400), default="")
    key: Mapped[str] = mapped_column(String(64), default="", index=True)   # dedupe


class IspnocFault(Base):
    __tablename__ = "ispnoc_faults"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nflt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    key: Mapped[str] = mapped_column(String(160), default="", index=True)
    kind: Mapped[str] = mapped_column(String(20), default="")
    scope: Mapped[str] = mapped_column(String(12), default="")              # olt | uplink | pon | splitter | ont
    olt_id: Mapped[str] = mapped_column(String(40), default="")
    pon: Mapped[str] = mapped_column(String(20), default="")
    target: Mapped[str] = mapped_column(String(160), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="open")         # open | ticketed | resolved | dismissed
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    affected: Mapped[str] = mapped_column(Text, default="[]")               # [ont ids]
    n_affected: Mapped[int] = mapped_column(Integer, default=0)
    n_total: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[str] = mapped_column(Text, default="{}")                   # evidence, reasons, team, explain, rx ...
    notes: Mapped[str] = mapped_column(Text, default="[]")                  # her / team notes
    told: Mapped[str] = mapped_column(Text, default="{}")                   # alert tags sent once


class IspnocTicket(Base):
    __tablename__ = "ispnoc_tickets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ntkt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    fault_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    team: Mapped[str] = mapped_column(String(16), default="")               # rules.TEAMS
    assignee: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(12), default="open")         # open | assigned | on_site | fixed | closed | cancelled
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")
    ext_ref: Mapped[str] = mapped_column(String(80), default="")            # BSNL docket / upstream ticket number
    log: Mapped[str] = mapped_column(Text, default="[]")
    told: Mapped[str] = mapped_column(Text, default="{}")
    raised_by: Mapped[str] = mapped_column(String(60), default="")


class IspnocChange(Base):
    __tablename__ = "ispnoc_changes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nchg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    action: Mapped[str] = mapped_column(String(24), default="")             # rules.CHANGE_ACTIONS
    olt_id: Mapped[str] = mapped_column(String(40), default="")
    pon: Mapped[str] = mapped_column(String(20), default="")
    onu: Mapped[str] = mapped_column(String(12), default="")
    fault_id: Mapped[str] = mapped_column(String(40), default="")
    reason: Mapped[str] = mapped_column(String(400), default="")
    commands: Mapped[str] = mapped_column(Text, default="[]")
    rollback: Mapped[str] = mapped_column(Text, default="[]")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)          # command template checked against the vendor's manual
    risk: Mapped[str] = mapped_column(String(400), default="")
    n_affected: Mapped[int] = mapped_column(Integer, default=0)
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(14), default="waiting")      # waiting | rejected | approved | queued | running | done | failed | expired | cancelled
    via: Mapped[str] = mapped_column(String(12), default="")                # collector | manual
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    output: Mapped[str] = mapped_column(Text, default="")
    asked_by: Mapped[str] = mapped_column(String(60), default="")


class IspnocCollector(Base):
    __tablename__ = "ispnoc_collectors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ncol"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    sealed: Mapped[str] = mapped_column(Text, default="")                   # HMAC secret, sealed with the bazar vault
    site_id: Mapped[str] = mapped_column(String(40), default="")
    changes_ok: Mapped[bool] = mapped_column(Boolean, default=False)        # she allowed this collector to run approved changes
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_info: Mapped[str] = mapped_column(Text, default="{}")              # version, olts it reaches, lines pushed
    offline_told: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
