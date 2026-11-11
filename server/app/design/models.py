"""Tables for HOOLA DESIGN. Imported by db.init_db so create_all makes them; `ensure_tables` heals a database
that was born before this module (the v0.190.1 lesson: a model create_all never saw has no table live).

    design_files     one row per file; `snapshot` = the whole document (zlib JSON) as of `snapshot_seq`
    design_ops       the journal: one row per accepted op batch after the snapshot (trimmed at every checkpoint)
    design_versions  named + automatic versions (a full snapshot each)
    design_comments  pinned comments and their replies
    design_shares    view-only share links

The heavy columns are deferred: listing files must never read megabytes of snapshots.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class DesignFile(Base):
    __tablename__ = "design_files"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("df"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200), default="Untitled")
    star: Mapped[bool] = mapped_column(Boolean, default=False)
    trashed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    snapshot_seq: Mapped[int] = mapped_column(Integer, default=0)
    # Node ids are "<cid>:<n>", so a client number is never handed out twice for one file - not even after a
    # restart. 0 is the server's own (the root "0:0", the first page "0:1").
    next_cid: Mapped[int] = mapped_column(Integer, default=1)
    node_count: Mapped[int] = mapped_column(Integer, default=2)
    thumb_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # last auto version
    # D9c branches (design/branches.py): a branch is a normal file linked to its main file. NULL on every other file.
    branch_of: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    branch_base_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)         # main's seq at branch / update time
    branch_state: Mapped[str | None] = mapped_column(String(12), nullable=True)         # "open" | "merged"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DesignOp(Base):
    __tablename__ = "design_ops"
    __table_args__ = (Index("ix_design_ops_file_seq", "file_id", "seq"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(String(40))
    seq: Mapped[int] = mapped_column(Integer)
    by: Mapped[int] = mapped_column("by_cid", Integer, default=0)     # the sender's client number
    ops: Mapped[str] = mapped_column(Text)                            # the accepted ops, the JSON that was fanned out
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DesignVersion(Base):
    __tablename__ = "design_versions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dv"))
    file_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    label: Mapped[str] = mapped_column(String(200), default="")
    auto: Mapped[bool] = mapped_column(Boolean, default=False)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    by_name: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)             # what changed, in her words (D5)
    snapshot: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DesignComment(Base):
    __tablename__ = "design_comments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dc"))
    file_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page: Mapped[str] = mapped_column(String(64), default="")
    x: Mapped[float] = mapped_column(Float, default=0.0)
    y: Mapped[float] = mapped_column(Float, default=0.0)
    # D5: where the pin sits INSIDE its node (the node's own 0..w / 0..h box), so it follows the node when that
    # moves, turns or is reparented; x / y stay the page point it was dropped on (used when the node is gone).
    ox: Mapped[float | None] = mapped_column(Float, nullable=True)
    oy: Mapped[float | None] = mapped_column(Float, nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")
    parent: Mapped[str | None] = mapped_column(String(40), nullable=True)     # the comment this one replies to
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    author: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DesignShare(Base):
    __tablename__ = "design_shares"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(8), default="view")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DesignBranch(Base):
    """D9c: the BASE of a branch (main's document when the branch was made or last updated from main) - the third
    document of a three-way merge. One row per branch file, kept after the merge (it numbers the branches of a main)."""
    __tablename__ = "design_branches"
    file_id: Mapped[str] = mapped_column(String(40), primary_key=True)          # the branch file
    main_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    no: Mapped[int] = mapped_column(Integer, default=1)                         # 1, 2, ... per main: its own id range
    base: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    merged_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_ready_for: int | None = None


def ensure_tables() -> None:
    """Create the five tables in place on a database that never saw them. Keyed on the engine, so a process
    that opens a second database (every test does) heals that one too."""
    global _ready_for
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None:
        _db.init_db()
        eng = _db._engine
    if _ready_for == id(eng):
        return
    tables = [m.__table__ for m in (DesignFile, DesignOp, DesignVersion, DesignComment, DesignShare, DesignBranch)]
    for table in tables:
        table.create(eng, checkfirst=True)
    _db.add_missing_columns_for(eng, *tables)        # a column added after the table was born (design_versions.note)
    _ready_for = id(eng)
