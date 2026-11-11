"""Every database read and write of HOOLA DESIGN. All functions are synchronous and are called from a worker
thread (room.bg) or a threadpool route - never on the event loop. Every row access is tenant-checked here, so a
caller can not forget it.
"""
from __future__ import annotations

import re
import secrets
import zlib
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import undefer

from ..db import Profile, User, as_utc, now, session
from .models import DesignComment, DesignFile, DesignOp, DesignShare, DesignVersion, ensure_tables

NAME_MAX = 200
COMMENT_MAX = 4000
NOTE_MAX = 1000
_HASH_REF = re.compile(r'"([0-9a-f]{64})"')    # an image hash anywhere in a document (fills, overrides, styles ...)


def pack(doc_json: str) -> bytes:
    return zlib.compress(doc_json.encode("ascii"), 6)


def unpack(blob: bytes) -> str:
    return zlib.decompress(blob).decode("ascii")


def clean_name(name: Any, fallback: str = "Untitled") -> str:
    text = " ".join(str(name or "").split())[:NAME_MAX]
    return text or fallback


def _iso(value: datetime | None) -> str | None:
    return as_utc(value).isoformat() if value else None


def who(tenant: str) -> str:
    """The name shown beside a cursor, a comment and a version."""
    with session() as s:
        user = s.get(User, tenant)
        if user:
            return user.name or user.email.split("@")[0]
        profile = s.get(Profile, tenant)
        if profile and profile.name:
            return profile.name
    return "Owner"


# ---------------------------------------------------------------------------------------------- files
def _file(row: DesignFile) -> dict:
    return {"id": row.id, "name": row.name, "star": bool(row.star), "trashed": row.trashed_at is not None,
            "trashed_at": _iso(row.trashed_at), "nodes": row.node_count, "seq": row.snapshot_seq,
            "thumb_at": _iso(row.thumb_at), "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)}


def _own(s, tenant: str, file_id: str) -> DesignFile | None:
    row = s.get(DesignFile, file_id)
    return row if row is not None and row.tenant_id == tenant else None


def list_files(tenant: str, q: str = "", trash: bool = False) -> list[dict]:
    ensure_tables()
    with session() as s:
        stmt = select(DesignFile).where(DesignFile.tenant_id == tenant)
        stmt = stmt.where(DesignFile.trashed_at.is_not(None) if trash else DesignFile.trashed_at.is_(None))
        needle = (q or "").strip().lower()
        if needle:
            needle = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(func.lower(DesignFile.name).like(f"%{needle}%", escape="\\"))
        rows = s.scalars(stmt.order_by(DesignFile.updated_at.desc(), DesignFile.id).limit(500)).all()
        return [_file(r) for r in rows]


def create_file(tenant: str, name: str, doc_json: str, node_count: int) -> dict:
    ensure_tables()
    with session() as s:
        row = DesignFile(tenant_id=tenant, name=clean_name(name), snapshot=pack(doc_json), node_count=node_count)
        s.add(row)
        s.flush()
        return _file(row)


def duplicate_file(tenant: str, file_id: str, doc_json: str, node_count: int) -> dict | None:
    """A new file holding a copy of the document. It carries the source's client-number counter on: the copied
    nodes keep their ids, and a new editor must never mint one of them again."""
    ensure_tables()
    with session() as s:
        src = _own(s, tenant, file_id)
        if src is None:
            return None
        row = DesignFile(tenant_id=tenant, name=clean_name(f"{src.name} copy"), snapshot=pack(doc_json),
                         node_count=node_count, next_cid=src.next_cid)
        s.add(row)
        s.flush()
        return _file(row)


def get_file(tenant: str, file_id: str) -> dict | None:
    ensure_tables()
    with session() as s:
        row = _own(s, tenant, file_id)
        if row is None:
            return None
        out = _file(row)
        share = s.scalar(select(DesignShare).where(DesignShare.file_id == file_id))
        out["share"] = {"role": share.role, "token": share.token} if share else None
        out["role"] = "edit"
        return out


def patch_file(tenant: str, file_id: str, name: str | None, star: bool | None) -> dict | None:
    ensure_tables()
    with session() as s:
        row = _own(s, tenant, file_id)
        if row is None:
            return None
        if name is not None and clean_name(name, row.name) != row.name:
            row.name, row.updated_at = clean_name(name, row.name), now()
        if star is not None:
            row.star = bool(star)
        return _file(row)


def set_trashed(tenant: str, file_id: str, trashed: bool) -> dict | None:
    ensure_tables()
    with session() as s:
        row = _own(s, tenant, file_id)
        if row is None:
            return None
        row.trashed_at = (row.trashed_at or now()) if trashed else None
        return _file(row)


def delete_forever(tenant: str, file_id: str) -> str:
    """'gone', 'missing', or 'not_trashed' (a file is deleted for good only out of the trash)."""
    ensure_tables()
    with session() as s:
        row = _own(s, tenant, file_id)
        if row is None:
            return "missing"
        if row.trashed_at is None:
            return "not_trashed"
        for model in (DesignOp, DesignVersion, DesignComment, DesignShare):
            s.execute(delete(model).where(model.file_id == file_id))
        s.delete(row)
        return "gone"


def set_thumb(tenant: str, file_id: str) -> str | None:
    with session() as s:
        row = _own(s, tenant, file_id)
        if row is None:
            return None
        row.thumb_at = now()
        return _iso(row.thumb_at)


# ---------------------------------------------------------------------------------- snapshot + journal
def load_raw(file_id: str, tenant: str | None, allow_trashed: bool = False) -> dict | None:
    """The stored snapshot plus the journal after it. tenant None = the caller already proved access (a share token)."""
    ensure_tables()
    with session() as s:
        row = s.get(DesignFile, file_id, options=[undefer(DesignFile.snapshot)])
        if row is None or (tenant is not None and row.tenant_id != tenant):
            return None
        if row.trashed_at is not None and not allow_trashed:
            return None
        journal = s.execute(select(DesignOp.seq, DesignOp.by, DesignOp.ops)
                            .where(DesignOp.file_id == file_id, DesignOp.seq > row.snapshot_seq)
                            .order_by(DesignOp.seq)).all()
        return {"tenant": row.tenant_id, "name": row.name, "seq": row.snapshot_seq,
                "doc": unpack(row.snapshot) if row.snapshot else "",
                "journal": [(seq, by, ops) for seq, by, ops in journal]}


def next_cid(file_id: str) -> int:
    """Hand out the next client number of a file, durably: ids minted under it must never be minted again."""
    with session() as s:
        s.execute(update(DesignFile).where(DesignFile.id == file_id).values(next_cid=DesignFile.next_cid + 1))
        return int(s.scalar(select(DesignFile.next_cid).where(DesignFile.id == file_id)) or 2) - 1


def append_ops(file_id: str, rows: list[tuple[int, int, str, datetime]]) -> None:
    with session() as s:
        s.execute(insert(DesignOp), [{"file_id": file_id, "seq": seq, "by": by, "ops": ops, "at": at}
                                     for seq, by, ops, at in rows])


def save_snapshot(file_id: str, blob: bytes, seq: int, node_count: int, version_every_s: float, keep: int,
                  by: str = "") -> None:
    """Checkpoint: store the snapshot, trim the journal below it, and cut an automatic version when one is due
    (`by` = the person whose edit was the last one in it)."""
    with session() as s:
        row = s.get(DesignFile, file_id)
        if row is None or seq < row.snapshot_seq:
            return
        stamp = now()
        row.snapshot, row.snapshot_seq, row.node_count, row.updated_at = blob, seq, node_count, stamp
        s.execute(delete(DesignOp).where(DesignOp.file_id == file_id, DesignOp.seq <= seq))
        since = as_utc(row.version_at or row.created_at)
        if version_every_s > 0 and (stamp - since).total_seconds() >= version_every_s:
            s.add(DesignVersion(file_id=file_id, tenant_id=row.tenant_id, auto=True, seq=seq, node_count=node_count,
                                by_name=(by or "")[:200], snapshot=blob, created_at=stamp))
            row.version_at = stamp
            s.flush()
            old = s.scalars(select(DesignVersion.id).where(DesignVersion.file_id == file_id, DesignVersion.auto.is_(True))
                            .order_by(DesignVersion.created_at.desc(), DesignVersion.id.desc()).offset(max(1, keep))).all()
            if old:
                s.execute(delete(DesignVersion).where(DesignVersion.id.in_(old)))


# ------------------------------------------------------------------------------------------- versions
def _version(row: DesignVersion) -> dict:
    return {"id": row.id, "file": row.file_id, "label": row.label, "auto": bool(row.auto), "seq": row.seq,
            "nodes": row.node_count, "by": row.by_name, "note": row.note or "", "created_at": _iso(row.created_at)}


def list_versions(tenant: str, file_id: str) -> list[dict] | None:
    ensure_tables()
    with session() as s:
        if _own(s, tenant, file_id) is None:
            return None
        rows = s.scalars(select(DesignVersion).where(DesignVersion.file_id == file_id)
                         .order_by(DesignVersion.created_at.desc(), DesignVersion.id.desc()).limit(500)).all()
        return [_version(r) for r in rows]


def add_version(tenant: str, file_id: str, label: str, doc_json: str, seq: int, node_count: int, by: str,
                note: str = "") -> dict | None:
    ensure_tables()
    with session() as s:
        if _own(s, tenant, file_id) is None:
            return None
        row = DesignVersion(file_id=file_id, tenant_id=tenant, label=clean_name(label, ""), seq=seq,
                            node_count=node_count, by_name=by[:200], note=" ".join(str(note or "").split())[:NOTE_MAX],
                            snapshot=pack(doc_json))
        s.add(row)
        s.flush()
        return _version(row)


def version_doc(tenant: str, version_id: str) -> dict | None:
    ensure_tables()
    with session() as s:
        row = s.get(DesignVersion, version_id, options=[undefer(DesignVersion.snapshot)])
        if row is None or row.tenant_id != tenant:
            return None
        return {**_version(row), "doc": unpack(row.snapshot)}


def file_from_version(tenant: str, version_id: str, name: str = "") -> dict | None:
    """A NEW file holding this version's document; the file it came from is not touched. It carries the source's
    client-number counter on, like a duplicate: the copied nodes keep their ids."""
    ensure_tables()
    with session() as s:
        ver = s.get(DesignVersion, version_id, options=[undefer(DesignVersion.snapshot)])
        if ver is None or ver.tenant_id != tenant:
            return None
        src = s.get(DesignFile, ver.file_id)
        label = ver.label or as_utc(ver.created_at).strftime("%d %b %Y")
        fallback = f"{src.name if src else 'Untitled'} ({label})"
        row = DesignFile(tenant_id=tenant, name=clean_name(name, clean_name(fallback)), snapshot=ver.snapshot,
                         node_count=ver.node_count, next_cid=src.next_cid if src else 1)
        s.add(row)
        s.flush()
        return _file(row)


# ------------------------------------------------------------------------------------------- comments
def _comment(row: DesignComment) -> dict:
    return {"id": row.id, "file": row.file_id, "node": row.node, "page": row.page, "x": row.x, "y": row.y,
            "ox": row.ox, "oy": row.oy, "text": row.text, "parent": row.parent, "resolved": bool(row.resolved), "author": row.author,
            "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)}


def list_comments(tenant: str | None, file_id: str) -> list[dict] | None:
    """tenant None = the caller already proved access (a share token), exactly like load_raw."""
    ensure_tables()
    with session() as s:
        if tenant is not None and _own(s, tenant, file_id) is None:
            return None
        rows = s.scalars(select(DesignComment).where(DesignComment.file_id == file_id)
                         .order_by(DesignComment.created_at, DesignComment.id).limit(5000)).all()
        return [_comment(r) for r in rows]


def add_comment(tenant: str, file_id: str, author: str, text: str, node: str | None, page: str,
                x: float, y: float, parent: str | None, ox: float | None = None, oy: float | None = None) -> dict | None:
    """None = no such file. A reply to a reply is filed under the thread's first comment (threads are one level)."""
    ensure_tables()
    with session() as s:
        if _own(s, tenant, file_id) is None:
            return None
        if parent:
            head = s.get(DesignComment, parent)
            if head is None or head.file_id != file_id:
                raise ValueError("The comment being replied to is not in this file.")
            parent = head.parent or head.id
        row = DesignComment(file_id=file_id, tenant_id=tenant, author=author[:200], text=text[:COMMENT_MAX],
                            node=(node or None)[:64] if node else None, page=page[:64], x=x, y=y,
                            ox=ox if node else None, oy=oy if node else None, parent=parent or None)
        s.add(row)
        s.flush()
        return _comment(row)


def patch_comment(tenant: str, comment_id: str, text: str | None, resolved: bool | None) -> dict | None:
    ensure_tables()
    with session() as s:
        row = s.get(DesignComment, comment_id)
        if row is None or row.tenant_id != tenant:
            return None
        if text is not None:
            row.text = text[:COMMENT_MAX]
        if resolved is not None:
            row.resolved = bool(resolved)
        row.updated_at = now()
        return _comment(row)


def delete_comment(tenant: str, comment_id: str) -> dict | None:
    """Delete a comment and the replies under it. Returns {id, file} of what was asked for."""
    ensure_tables()
    with session() as s:
        row = s.get(DesignComment, comment_id)
        if row is None or row.tenant_id != tenant:
            return None
        gone = {"id": row.id, "file": row.file_id}
        s.execute(delete(DesignComment).where(DesignComment.parent == comment_id))
        s.delete(row)
        return gone


# --------------------------------------------------------------------------------------------- shares
def set_share(tenant: str, file_id: str, role: str) -> dict | None:
    """role 'view' = make (or return) the one view link of the file; 'none' = every link of it stops working."""
    ensure_tables()
    with session() as s:
        if _own(s, tenant, file_id) is None:
            return None
        row = s.scalar(select(DesignShare).where(DesignShare.file_id == file_id))
        if role == "none":
            s.execute(delete(DesignShare).where(DesignShare.file_id == file_id))
            return {"token": None, "role": "none"}
        if row is None:
            row = DesignShare(token=secrets.token_urlsafe(24), file_id=file_id, tenant_id=tenant, role="view")
            s.add(row)
        return {"token": row.token, "role": row.role}


def share_target(token: str) -> dict | None:
    """What a share link opens: {file, tenant, name, role}. None for an unknown link or a file in the trash."""
    ensure_tables()
    if not token or len(token) > 64:
        return None
    with session() as s:
        share = s.get(DesignShare, token)
        row = s.get(DesignFile, share.file_id) if share else None
        if row is None or row.trashed_at is not None:
            return None
        return {"file": row.id, "tenant": row.tenant_id, "name": row.name, "role": share.role}


# ---------------------------------------------------------------------------------- images still in use
def tenants() -> list[str]:
    """Everyone who has (or had) a design file: whose image folders the sweep looks at."""
    ensure_tables()
    with session() as s:
        return [t for t in s.scalars(select(DesignFile.tenant_id).distinct()).all() if t]


def asset_refs(tenant: str) -> set[str]:
    """Every image hash this tenant's documents still draw: the current snapshot of every file (the trash
    included), the journal after it, and every kept version. Read row by row, never all in memory at once."""
    ensure_tables()
    found: set[str] = set()
    with session() as s:
        file_ids = s.scalars(select(DesignFile.id).where(DesignFile.tenant_id == tenant)).all()
        for file_id in file_ids:
            blob = s.scalar(select(DesignFile.snapshot).where(DesignFile.id == file_id))
            if blob:
                found.update(_HASH_REF.findall(unpack(blob)))
            for ops in s.scalars(select(DesignOp.ops).where(DesignOp.file_id == file_id)):
                found.update(_HASH_REF.findall(ops))
        for vid in s.scalars(select(DesignVersion.id).where(DesignVersion.tenant_id == tenant)).all():
            blob = s.scalar(select(DesignVersion.snapshot).where(DesignVersion.id == vid))
            if blob:
                found.update(_HASH_REF.findall(unpack(blob)))
    return found
