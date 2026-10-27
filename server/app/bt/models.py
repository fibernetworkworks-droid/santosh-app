"""A Bluetooth job the phone must answer (scan, pair, connect...). Imported by db.init_db so create_all makes it."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class BtRequest(Base):
    __tablename__ = "bt_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(20))
    args: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="sent")     # sent | done | failed
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
