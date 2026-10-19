"""App Jaanch history. Imported by db.init_db so create_all makes it."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class AppCheck(Base):
    __tablename__ = "app_checks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("chk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(300), default="")
    sha256: Mapped[str] = mapped_column(String(64), index=True, default="")
    kind: Mapped[str] = mapped_column(String(16), default="")           # apk | exe | elf | electron | script | other
    verdict: Mapped[str] = mapped_column(String(12), default="")        # danger | caution | clear | unknown
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
