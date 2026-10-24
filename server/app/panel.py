"""v0.163 The side panel for finished work (SIDE_PANEL): pages, files, pictures, reels, videos, websites and apps open
beside the chat, and "Banaya hua" lists everything Hoola made for her.

Safety (same rule as the Build studio): nothing the panel shows can read her login.
- Pages (artifacts) and site / app previews run in sandboxed frames without allow-same-origin (opaque origin; the
  page's own CSP sandbox says the same). The page bridge (storage / ask / error) goes through postMessage to the
  console, which answers for THAT page only; the token never enters the frame.
- Her files come from `GET /api/panel/files/{id}` with the Bearer token. Only images (no SVG), video, audio and PDF
  are sent as viewable (`inline`); the console turns them into blob: URLs with the type the server named. Every other
  type is a download, never rendered (an .html / .svg file can't run next to the console).
- Share always makes a Haan card first (`share_ask`); only her tap turns the public link on.
"""
from __future__ import annotations

import logging
import mimetypes
import re
import secrets
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column

from .config import get_settings
from .db import Base, Event, now, session

log = logging.getLogger("santosh.panel")

KINDS = ("artifact", "pc_file", "photo_made", "motion", "video_job", "site_board", "app_board")
INLINE = {   # extension -> the only types ever sent as viewable
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
    ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime", ".m4v": "video/mp4",
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".ogg": "audio/ogg", ".wav": "audio/wav", ".pdf": "application/pdf",
}
TEXT_EXT = (".txt", ".md", ".csv", ".json", ".html", ".htm", ".css", ".js", ".ts", ".py", ".xml", ".yaml", ".yml",
            ".kt", ".dart", ".java", ".sql", ".log", ".svg")
TEXT_MAX = 1_000_000
_PDF: "OrderedDict[str, bytes]" = OrderedDict()      # file id -> Office as PDF (small cache)


class PanelError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def enabled() -> bool:
    return bool(get_settings().side_panel)


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ------------------------------------------------------------------ what an item is
def _media(name: str) -> str:
    from .net import media
    return media.media_kind(name or "")


def item_of(kind: str, p: dict) -> dict[str, Any] | None:
    """One card -> one panel item {type, ref, title, sub} (None: nothing to open)."""
    if not isinstance(p, dict):
        return None
    if kind == "artifact" and p.get("id"):
        return {"type": "page", "ref": p["id"], "title": p.get("title") or "Page", "sub": p.get("summary") or "",
                "version": p.get("version") or 0, "status": p.get("status") or ""}
    if kind in ("pc_file", "photo_made") and p.get("file_id"):
        m = _media(p.get("name") or "")
        return {"type": m if m in ("image", "video", "audio", "pdf", "doc", "sheet", "slides", "text") else "file",
                "ref": p["file_id"], "title": p.get("title") or p.get("name") or "File",
                "sub": (p.get("prompt") or "")[:160], "name": p.get("name") or ""}
    if kind == "motion" and p.get("id") and p.get("url"):
        return {"type": "video", "ref": p["id"], "title": p.get("title") or "Reel", "sub": "Hoola Motion reel",
                "url": p.get("url"), "src": "motion"}
    if kind == "video_job":
        latest = p.get("latest") or {}
        if isinstance(latest, dict) and latest.get("url"):
            return {"type": "video", "ref": p.get("id"), "title": p.get("title") or "Video", "sub": p.get("brief", "")[:160],
                    "url": latest.get("url"), "file_id": latest.get("file_id"), "src": "video_job",
                    "versions": [{"n": v.get("n"), "url": v.get("url")} for v in p.get("versions") or [] if isinstance(v, dict)]}
        return None
    if kind in ("site_board", "app_board"):
        pv = _preview(p.get("preview"))
        ref = p.get("id") or p.get("site_id") or p.get("app_id") or p.get("project")
        if not ref:
            return None
        return {"type": "website" if kind == "site_board" else "app", "ref": ref,
                "title": p.get("title") or p.get("name") or ("Website" if kind == "site_board" else "App"),
                "sub": p.get("now") or p.get("status") or "", "preview": pv, "status": p.get("status") or ""}
    return None


def _preview(u: Any) -> str:
    """Only our own site / app preview pages, as a same-server path."""
    s = str(u or "")
    m = re.search(r"(/api/(?:site|app)-preview/[\w-]+/)$", s)
    return m.group(1) if m else ""


# ------------------------------------------------------------------ Banaya hua (library)
def library(tenant: str, kind: str = "", q: str = "", limit: int = 200) -> list[dict[str, Any]]:
    """Everything Hoola made for her, newest first, each card once in its latest state."""
    from . import convs
    from .events import card_key
    ids = convs.ids(tenant)
    if not ids:
        return []
    with session() as s:
        rows = s.scalars(select(Event).where(Event.conversation_id.in_(ids), Event.kind.in_(KINDS))
                         .order_by(Event.id.desc()).limit(4000)).all()
        seen: dict[str, dict] = {}
        for e in rows:
            k = card_key(e.kind, e.payload, e.id)
            if k in seen:
                seen[k]["first_id"] = e.id
                continue
            it = item_of(e.kind, e.payload)
            if it is None:
                continue
            seen[k] = {**it, "kind": e.kind, "event_id": e.id, "first_id": e.id, "conv": e.conversation_id,
                       "at": (_utc(e.created_at) or now()).isoformat()}
    out = list(seen.values())
    group = {"page": "pages", "website": "sites", "app": "apps", "image": "photos", "video": "videos"}
    if kind:
        out = [o for o in out if group.get(o["type"], "files") == kind]
    if q:
        ql = q.lower()
        out = [o for o in out if ql in (o["title"] + " " + o.get("sub", "")).lower()]
    return out[:limit]


# ------------------------------------------------------------------ her files, safely
def _file(tenant: str, fid: str):
    from .mailbox import service as ms
    try:
        f = ms._file_row(tenant, fid)
    except Exception:
        raise PanelError(404, "File nahi mili (Hoola ki files 24 ghante baad hat jaati hain).")
    if not f.stored_path or not Path(f.stored_path).exists():
        raise PanelError(404, "File ab server par nahi hai (24 ghante baad hat jaati hai).")
    return f


def file_info(tenant: str, fid: str) -> dict[str, Any]:
    f = _file(tenant, fid)
    ext = Path(f.name or "").suffix.lower()
    m = _media(f.name)
    return {"file_id": f.id, "name": f.name, "size": f.size, "media": m, "inline": ext in INLINE and m != "other",
            "mime": INLINE.get(ext, ""), "text": ext in TEXT_EXT and (f.size or 0) <= TEXT_MAX,
            "office": m in ("doc", "sheet", "slides") and bool(get_settings().gotenberg_url)}


def file_bytes(tenant: str, fid: str) -> tuple[bytes, str, str, bool]:
    """(data, media type, file name, viewable). Only INLINE types are viewable; the rest is a download."""
    f = _file(tenant, fid)
    ext = Path(f.name or "").suffix.lower()
    data = Path(f.stored_path).read_bytes()
    if ext in INLINE:
        return data, INLINE[ext], f.name, True
    return data, "application/octet-stream", f.name, False


def file_text(tenant: str, fid: str) -> dict[str, Any]:
    f = _file(tenant, fid)
    ext = Path(f.name or "").suffix.lower()
    if ext not in TEXT_EXT or (f.size or 0) > TEXT_MAX:
        raise PanelError(415, "Is file ka code / text yahan nahi dikh sakta; Download kijiye.")
    raw = Path(f.stored_path).read_bytes()
    return {"name": f.name, "text": raw.decode("utf-8", "replace"), "lang": ext.lstrip(".")}


def file_pdf(tenant: str, fid: str) -> bytes:
    """Word / Excel / PowerPoint shown as PDF (the server's Gotenberg; cached)."""
    f = _file(tenant, fid)
    if _media(f.name) not in ("doc", "sheet", "slides"):
        raise PanelError(415, "Yeh Office file nahi hai.")
    if f.id in _PDF:
        _PDF.move_to_end(f.id)
        return _PDF[f.id]
    from .net import media
    pdf = media.office_to_pdf(f.name, Path(f.stored_path).read_bytes())
    if not pdf:
        raise PanelError(404, "Is server par Office preview set nahi hai (GOTENBERG_URL). Download karke kholiye.")
    _PDF[f.id] = pdf
    while len(_PDF) > 12:
        _PDF.popitem(last=False)
    return pdf


def page_source(tenant: str, aid: str, version: int = 0) -> dict[str, Any]:
    from . import artifacts
    a = artifacts.get(tenant, aid)
    if a is None or not a.version:
        raise PanelError(404, "Page abhi taiyaar nahi hai.")
    v = version if 0 < version <= a.version else a.version
    html = artifacts.latest_html(aid, v)
    if html is None:
        raise PanelError(404, "Yeh version nahi mila.")
    return {"id": aid, "version": v, "title": a.title, "html": html}


def page_view(tenant: str, aid: str, version: int = 0) -> dict[str, Any]:
    """The signed page link as a same-server path (the console frames only its own origin)."""
    from . import artifacts
    a = artifacts.get(tenant, aid)
    if a is None or not a.version:
        raise PanelError(404, "Page abhi taiyaar nahi hai.")
    v = version if 0 < version <= a.version else a.version
    url = artifacts.view_url(aid, v)
    m = re.search(r"(/a/[\w-]+/\d+\?.*)$", url)
    return {"url": m.group(1) if m else url, "version": v}


# ------------------------------------------------------------------ share = a Haan card first
class ShareAsk(Base):
    __tablename__ = "panel_share_asks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(8))              # page | file
    target: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(12), default="pending")   # pending | approved | rejected
    url: Mapped[str] = mapped_column(String(600), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)




def _card(a: ShareAsk) -> dict[str, Any]:
    hours = get_settings().pc_file_hours
    what = "page ka public link" if a.kind == "page" else f"file ka link (file {hours} ghante tak server par rehti hai)"
    return {"id": a.id, "kind": a.kind, "title": f"Share: {a.title}"[:120], "what": what, "status": a.status,
            "url": a.url if a.status == "approved" else "",
            "say": ("Koi bhi jiske paas yeh link hoga, yeh dekh payega. Haan karein?" if a.status == "pending" else
                    "Link ban gaya." if a.status == "approved" else "Share nahi kiya.")}


def ask_share(tenant: str, conv: str, kind: str, target: str) -> dict[str, Any]:
    if kind == "page":
        from . import artifacts
        a = artifacts.get(tenant, target)
        if a is None or not a.version:
            raise PanelError(404, "Page nahi mila.")
        title = a.title or "Page"
    elif kind == "file":
        f = _file(tenant, target)
        if f.direction != "to_phone":
            raise PanelError(409, "Sirf Hoola ki banayi file ka link ban sakta hai; apni file aap seedhe bhejiye.")
        title = f.name
    else:
        raise PanelError(400, "kind: page | file")
    row = ShareAsk(id="sh_" + secrets.token_hex(6), tenant_id=tenant, conversation_id=conv or "", kind=kind,
                   target=target, title=title)
    with session() as s:
        s.add(row)
        s.flush()
        card = _card(row)
    _publish(tenant, conv, card)
    return card


def decide_share(tenant: str, sid: str, approve: bool) -> dict[str, Any]:
    with session() as s:
        a = s.get(ShareAsk, sid)
        if a is None or a.tenant_id != tenant:
            raise PanelError(404, "Yeh share card nahi mila.")
        if a.status != "pending":
            return _card(a)
        if approve:
            if a.kind == "page":
                from . import artifacts
                r = artifacts.set_share(tenant, a.target, True)
                if r is None:
                    raise PanelError(404, "Page nahi mila.")
                a.url = r.get("share_url") or ""
            else:
                from .pc.service import download_path
                _file(tenant, a.target)
                a.url = (get_settings().public_base_url or "").rstrip("/") + download_path(a.target)
            a.status = "approved"
        else:
            a.status = "rejected"
        card, conv = _card(a), a.conversation_id
    _publish(tenant, conv, card)
    return card


def _publish(tenant: str, conv: str, card: dict) -> None:
    from . import convs
    from .events import bus
    c = conv or convs.current(tenant)
    if c:
        bus.publish(c, "share_ask", card)
