from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class PublicApiKey(Base):
    """The owner's own key for one public API (typed in the app, sealed with the server key, never shown to the model)."""
    __tablename__ = "public_api_keys"
    __table_args__ = (UniqueConstraint("tenant_id", "api_id", name="uq_public_api_key"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pak"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    api_id: Mapped[str] = mapped_column(String(80))
    sealed: Mapped[str] = mapped_column(Text)
    place: Mapped[str] = mapped_column(String(10), default="query")      # query | header
    field: Mapped[str] = mapped_column(String(60), default="apikey")     # param / header name
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PublicApiRecipe(Base):
    """A call that worked (method + url pattern, values blanked): next time the avatar goes straight to it.
    Shared across owners only as a pattern + success count (no values, no keys, no owner)."""
    __tablename__ = "public_api_recipes"
    __table_args__ = (UniqueConstraint("api_id", "pattern", name="uq_public_api_recipe"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("par"))
    api_id: Mapped[str] = mapped_column(String(80), index=True)
    pattern: Mapped[str] = mapped_column(Text)
    example_params: Mapped[str] = mapped_column(Text, default="")        # parameter names only
    ok_count: Mapped[int] = mapped_column(Integer, default=0)
    owners: Mapped[int] = mapped_column(Integer, default=0)
    last_ok: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    first_tenant: Mapped[str] = mapped_column(String(64), default="")
