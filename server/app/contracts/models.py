"""Tables of the Contracts Sahayak (contract manager), all prefixed contracts_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ContractSettings(Base):
    __tablename__ = "contracts_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    party_name: Mapped[str] = mapped_column(String(160), default="")      # her business name as it appears in contracts
    default_role: Mapped[str] = mapped_column(String(16), default="")
    seat_city: Mapped[str] = mapped_column(String(60), default="")       # her preferred arbitration seat / court city
    state: Mapped[str] = mapped_column(String(40), default="")           # her state (stamp duty)
    msme: Mapped[bool] = mapped_column(Boolean, default=False)           # Udyam-registered micro / small supplier
    email: Mapped[str] = mapped_column(String(120), default="")
    playbook: Mapped[str] = mapped_column(Text, default="{}")            # her positions {key: {position, level, value, standard_text, off}}
    stamp_rates: Mapped[str] = mapped_column(Text, default="[]")         # her rate rows [{kind, state, mode, rate, min, max, note}]
    windows: Mapped[str] = mapped_column(Text, default="[60, 30, 15, 7, 1, 0]")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class Contract(Base):
    __tablename__ = "contracts_docs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ct"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(20), default="other")
    counterparty: Mapped[str] = mapped_column(String(160), default="")
    their_contact: Mapped[str] = mapped_column(String(160), default="")    # email / phone of the other side
    our_role: Mapped[str] = mapped_column(String(16), default="")
    our_label: Mapped[str] = mapped_column(String(60), default="")        # how the contract names us ("Vendor")
    their_label: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    file_name: Mapped[str] = mapped_column(String(200), default="")
    stored: Mapped[str] = mapped_column(String(300), default="")          # her original kept by Hoola (read only)
    text: Mapped[str] = mapped_column(Text, default="")                   # masked text
    text_hash: Mapped[str] = mapped_column(String(64), default="")
    reader: Mapped[str] = mapped_column(String(20), default="")
    extract: Mapped[str] = mapped_column(Text, default="{}")             # clauses + values
    risks: Mapped[str] = mapped_column(Text, default="[]")
    summary: Mapped[str] = mapped_column(Text, default="")
    start: Mapped[str] = mapped_column(String(10), default="")
    end: Mapped[str] = mapped_column(String(10), default="")
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    renew_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notice_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    governing_law: Mapped[str] = mapped_column(String(60), default="")
    seat: Mapped[str] = mapped_column(String(60), default="")
    stamp: Mapped[str] = mapped_column(Text, default="{}")               # {state, paid yes|no|unknown|not_needed, amount, cert_no, on}
    sign: Mapped[str] = mapped_column(Text, default="{}")                # {mode, signers, on, file}
    versions: Mapped[str] = mapped_column(Text, default="[]")            # [{n, kind redline|draft|signed, path, at, note, changes}]
    notes: Mapped[str] = mapped_column(Text, default="")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ContractObligation(Base):
    __tablename__ = "contracts_obligations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("co"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contract_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(20), default="other")       # renewal_notice | expiry | payment | delivery | report | insurance | lockin | other
    who: Mapped[str] = mapped_column(String(8), default="us")            # us | them | both
    what: Mapped[str] = mapped_column(Text, default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    every_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto: Mapped[bool] = mapped_column(Boolean, default=False)           # made by Hoola from the contract's dates
    status: Mapped[str] = mapped_column(String(10), default="open")      # open | done | waived
    done_on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ContractCard(Base):
    __tablename__ = "contracts_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contract_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(16), default="send")        # send | esign | estamp | notice
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")   # waiting | approved | rejected | stale | done
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContractOnce(Base):
    __tablename__ = "contracts_once"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
