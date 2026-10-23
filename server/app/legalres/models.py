"""Tables of the Legalres Sahayak (legal researcher), all prefixed legalres_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class LegalresSettings(Base):
    __tablename__ = "legalres_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ik_sealed: Mapped[str] = mapped_column(Text, default="")          # Indian Kanoon API token, sealed with the bazar vault (app only)
    ik_label: Mapped[str] = mapped_column(String(40), default="")
    ik_ok: Mapped[bool] = mapped_column(Boolean, default=False)       # a call with it worked once
    ik_day_rs: Mapped[float] = mapped_column(Float, default=25.0)     # her daily ceiling on IK spend (Rs)
    ik_spend: Mapped[str] = mapped_column(Text, default="{}")         # {YYYY-MM-DD: rupees}
    use_web: Mapped[bool] = mapped_column(Boolean, default=True)      # official public pages via web search
    use_files: Mapped[bool] = mapped_column(Boolean, default=True)    # her own Gyaan
    firm: Mapped[str] = mapped_column(String(160), default="")
    researcher: Mapped[str] = mapped_column(String(120), default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class LegalresMatter(Base):
    __tablename__ = "legalres_matters"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")       # LR-0001
    title: Mapped[str] = mapped_column(String(200), default="")
    client: Mapped[str] = mapped_column(String(160), default="")      # her label for whose matter (privileged)
    court: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | closed | forgotten
    memos: Mapped[str] = mapped_column(Text, default="[]")            # versions [{v, at, question, short, points, ...}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LegalresSource(Base):
    __tablename__ = "legalres_sources"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ls"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    matter_id: Mapped[str] = mapped_column(String(40), index=True)
    n: Mapped[int] = mapped_column(Integer, default=0)                # [n] inside this matter
    kind: Mapped[str] = mapped_column(String(16), default="web")     # statute | judgment | official | her_file | web
    via: Mapped[str] = mapped_column(String(16), default="web")      # web | ikanoon | gyaan | her_link
    title: Mapped[str] = mapped_column(String(300), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    official: Mapped[bool] = mapped_column(Boolean, default=False)
    ref: Mapped[str] = mapped_column(String(80), default="")          # IK tid / gyaan chunk id / file id
    court: Mapped[str] = mapped_column(String(160), default="")
    text: Mapped[str] = mapped_column(Text, default="")               # what Hoola actually read (trimmed)
    excerpt: Mapped[str] = mapped_column(Text, default="")
    saved: Mapped[bool] = mapped_column(Boolean, default=False)       # her saved authority
    note: Mapped[str] = mapped_column(Text, default="")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LegalresLog(Base):
    __tablename__ = "legalres_log"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ll"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    matter_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="note")    # question | search | fetch | memo | note | share | file | forget
    text: Mapped[str] = mapped_column(Text, default="")
    cost: Mapped[float] = mapped_column(Float, default=0.0)           # Rs (Indian Kanoon)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LegalresShare(Base):
    __tablename__ = "legalres_shares"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lsh"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    matter_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")       # SH-001
    memo_v: Mapped[int] = mapped_column(Integer, default=0)
    to_name: Mapped[str] = mapped_column(String(160), default="")
    to_contact: Mapped[str] = mapped_column(String(160), default="")
    via: Mapped[str] = mapped_column(String(12), default="whatsapp")  # whatsapp | email | file
    note: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")  # waiting | shared | rejected | stale
    file_id: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
