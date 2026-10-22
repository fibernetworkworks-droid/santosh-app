"""Hoola Network tables. Imported by db.init_db so create_all makes them."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class HoolaId(Base):
    """One per owner on this server: the unique Hoola ID (handle), a permanent internal uid and a signing key."""
    __tablename__ = "hoola_ids"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    uid: Mapped[str] = mapped_column(String(40), unique=True, index=True)          # hl_<hex>, never changes
    handle: Mapped[str] = mapped_column(String(40), unique=True, index=True)       # meghana.fnw (shown as @meghana.fnw)
    skeleton: Mapped[str] = mapped_column(String(40), index=True, default="")      # look-alike check
    owner_name: Mapped[str] = mapped_column(String(80), default="")
    old_handle: Mapped[str] = mapped_column(String(40), default="")               # points here for 90 days
    handle_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    phone_hash: Mapped[str] = mapped_column(String(64), index=True, default="")    # only when discoverable
    discoverable: Mapped[bool] = mapped_column(Boolean, default=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)                 # person verified by the operator
    business: Mapped[bool] = mapped_column(Boolean, default=False)
    business_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    public_key: Mapped[str] = mapped_column(Text, default="")                      # base64 raw Ed25519
    private_key: Mapped[str] = mapped_column(Text, default="")                     # encrypted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Peer(Base):
    """What this server knows about any Hoola identity it talks to (local or on another server)."""
    __tablename__ = "hoola_peers"
    address: Mapped[str] = mapped_column(String(200), primary_key=True)            # hl_x@domain
    handle: Mapped[str] = mapped_column(String(120), default="")
    owner_name: Mapped[str] = mapped_column(String(80), default="")
    avatar_name: Mapped[str] = mapped_column(String(40), default="")
    avatar_gender: Mapped[str] = mapped_column(String(1), default="m")
    avatar_look: Mapped[str | None] = mapped_column(String(8), nullable=True)        # v0.48 3D look id
    public_key: Mapped[str] = mapped_column(Text, default="")
    server: Mapped[str] = mapped_column(String(200), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    business: Mapped[bool] = mapped_column(Boolean, default=False)
    key_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pending_key: Mapped[str | None] = mapped_column(Text, nullable=True)        # a changed key waits for the owner
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Link(Base):
    """One owner's view of a connection with a peer."""
    __tablename__ = "hoola_links"
    __table_args__ = (UniqueConstraint("tenant_id", "peer", name="uq_hoola_link"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lnk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    peer: Mapped[str] = mapped_column(String(200), index=True)                     # peer address
    status: Mapped[str] = mapped_column(String(12), default="requested")           # requested|incoming|active|declined|blocked
    relation: Mapped[str] = mapped_column(String(12), default="friend")            # family|team|business|friend
    via: Mapped[str] = mapped_column(String(12), default="id")                     # id|qr|invite|phone
    note: Mapped[str] = mapped_column(Text, default="")
    nick: Mapped[str] = mapped_column(String(80), default="")
    vip: Mapped[bool] = mapped_column(Boolean, default=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)                 # safety code compared
    key_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    trust: Mapped[str] = mapped_column(String(10), default="")                      # v0.112 "" auto | trusted | known (her choice)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Invite(Base):
    """A one-time connect code for a QR or a link (expires in 7 days)."""
    __tablename__ = "hoola_invites"
    code: Mapped[str] = mapped_column(String(24), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    used_by: Mapped[str] = mapped_column(String(200), default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Thread(Base):
    """One subject between this owner's avatar and a peer avatar (each side keeps its own row; tkey is shared)."""
    __tablename__ = "hoola_threads"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("thr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    tkey: Mapped[str] = mapped_column(String(60), index=True)
    peer: Mapped[str] = mapped_column(String(200), index=True)
    group_id: Mapped[str] = mapped_column(String(40), default="")
    subject: Mapped[str] = mapped_column(String(300), default="")
    kind: Mapped[str] = mapped_column(String(20), default="message")
    started_by_me: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(12), default="open")               # open|done|declined|closed
    mode: Mapped[str] = mapped_column(String(10), default="relay")                 # relay | handle (avatar handles it)
    goal: Mapped[str] = mapped_column(Text, default="")
    turns: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NetMsg(Base):
    """One signed envelope, as stored on this owner's side (in or out)."""
    __tablename__ = "hoola_msgs"
    __table_args__ = (UniqueConstraint("tenant_id", "env_id", name="uq_hoola_msg"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    env_id: Mapped[str] = mapped_column(String(60), index=True)
    thread_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    direction: Mapped[str] = mapped_column(String(4))                              # in | out
    peer: Mapped[str] = mapped_column(String(200), index=True)
    kind: Mapped[str] = mapped_column(String(24))
    body: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="sent")
    # in: pending | delivered | auto | accepted | declined | snoozed | blocked ; out: sent | refused
    reason: Mapped[str] = mapped_column(Text, default="")
    snooze_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quiet: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Outbox(Base):
    """Something the owner's avatar wants to send that needs the owner's own tap first (files, emails, contacts,
    location, payment requests, or a text carrying phone numbers / addresses / IDs)."""
    __tablename__ = "hoola_outbox"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hob"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    to: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(24))
    body: Mapped[dict] = mapped_column(JSON, default=dict)
    thread_id: Mapped[str] = mapped_column(String(40), default="")
    handle: Mapped[bool] = mapped_column(Boolean, default=False)
    goal: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")       # waiting | sent | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Seen(Base):
    """Envelope ids already accepted (replay protection)."""
    __tablename__ = "hoola_seen"
    env_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
