"""Santosh's Google Photos work. Blocking; tools run it in a thread.

What Google allows (since 31 Mar 2025): the user picks photos in the Google Photos Picker (Santosh gets only those),
and Santosh can upload photos and make albums, and read back only what it uploaded. Santosh can't browse, search,
share or delete the user's library through the API, and says so honestly.
"""
from __future__ import annotations

import logging
import mimetypes
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from ..db import as_utc, now, session
from ..events import bus, notify
from .accounts import get_client
from .client import PhotosClient, PhotosError
from .models import PhotosPending, PhotosPick

log = logging.getLogger("santosh.photos")

BIG_UPLOAD = 20
MAX_BYTES = 50 * 1024 * 1024
PICK_MINUTES = 30
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff", ".avif")
VIDEO_EXT = (".mp4", ".mov", ".3gp", ".avi", ".mkv", ".m4v", ".wmv", ".mpg", ".webm")


def _client_for(tenant: str, key: str | None) -> PhotosClient:
    try:
        return get_client(tenant, key or None)
    except PhotosError:
        return get_client(tenant)


# ---------------- picking ----------------
def _item_view(m: dict) -> dict[str, Any]:
    mf = m.get("mediaFile") or {}
    meta = mf.get("mediaFileMetadata") or {}
    return {"id": m.get("id", ""), "type": m.get("type", "PHOTO"), "filename": mf.get("filename", "") or f"{m.get('id', 'photo')}.jpg",
            "mime": mf.get("mimeType", "image/jpeg"), "width": meta.get("width"), "height": meta.get("height"),
            "taken": m.get("createTime", ""), "base_url": mf.get("baseUrl", "")}


def _public_item(it: dict) -> dict[str, Any]:
    return {k: it.get(k) for k in ("id", "type", "filename", "mime", "width", "height", "taken")}


def pick_view(p: PhotosPick) -> dict[str, Any]:
    return {"pick_id": p.id, "status": p.status, "purpose": p.purpose, "picker_uri": p.picker_uri,
            "count": p.item_count, "items": [_public_item(i) for i in (p.items or [])][:60]}


def start_pick(tenant: str, conv: str, purpose: str = "", max_items: int = 0, account: str | None = None) -> dict[str, Any]:
    c = get_client(tenant, account)
    ses = c.new_session(int(max_items or 0))
    uri = (ses.get("pickerUri") or "").rstrip("/")
    if not uri:
        raise PhotosError("Google Photos ne chunne ka link nahi diya; dobara try kijiye.")
    exp = None
    if ses.get("expireTime"):
        try:
            exp = datetime.fromisoformat(ses["expireTime"].replace("Z", "+00:00"))
        except ValueError:
            exp = None
    with session() as s:
        p = PhotosPick(tenant_id=tenant, conversation_id=conv, account=c.key, session_id=ses["id"],
                       picker_uri=uri + "/autoclose", purpose=(purpose or "")[:300],
                       expires_at=exp or now() + timedelta(minutes=PICK_MINUTES))
        s.add(p)
        s.flush()
        view = pick_view(p)
    if conv:
        bus.publish(conv, "photos_pick", {**{k: view[k] for k in ("pick_id", "picker_uri", "purpose", "status")}})
    return view


def _get_pick(tenant: str, pick_id: str) -> PhotosPick:
    with session() as s:
        p = s.get(PhotosPick, pick_id)
        if p is None or p.tenant_id != tenant:
            raise PhotosError("Yeh photo chunne ka session nahi mila. photos_pick se naya shuru kijiye.")
        s.expunge(p)
        return p


def refresh_pick(tenant: str, pick_id: str) -> dict[str, Any]:
    """Ask Google whether the user finished picking; if so store the picked items."""
    p = _get_pick(tenant, pick_id)
    if p.status != "waiting":
        return pick_view(p)
    c = _client_for(tenant, p.account)
    exp = as_utc(p.expires_at)
    try:
        ses = c.get_session(p.session_id)
    except PhotosError as e:
        if "nahi mila" in str(e):
            _mark(p.id, "expired")
            return pick_view(_get_pick(tenant, pick_id))
        raise
    if not ses.get("mediaItemsSet"):
        if exp and exp < now():
            _mark(p.id, "expired")
        return pick_view(_get_pick(tenant, pick_id))
    items = [_item_view(m) for m in c.picked(p.session_id)]
    with session() as s:
        row = s.get(PhotosPick, p.id)
        row.items, row.item_count, row.status = items, len(items), "ready"
    try:
        c.delete_session(p.session_id)      # Google asks apps to clean up finished sessions
    except PhotosError:
        pass
    return pick_view(_get_pick(tenant, pick_id))


def _mark(pid: str, status: str) -> None:
    with session() as s:
        row = s.get(PhotosPick, pid)
        if row:
            row.status = status


def poll_tick() -> int:
    """Worker, every ~15 s: picks the user is still choosing; announce the ones that just became ready."""
    with session() as s:
        waiting = [(p.id, p.tenant_id, p.conversation_id) for p in s.scalars(select(PhotosPick).where(
            PhotosPick.status == "waiting", PhotosPick.created_at >= now() - timedelta(minutes=PICK_MINUTES + 5))).all()]
        for p in s.scalars(select(PhotosPick).where(PhotosPick.status == "waiting",
                                                    PhotosPick.created_at < now() - timedelta(minutes=PICK_MINUTES + 5))).all():
            p.status = "expired"
    done = 0
    for pid, tenant, conv in waiting:
        try:
            v = refresh_pick(tenant, pid)
        except Exception as e:
            log.info("photos pick %s poll failed: %s", pid, e)
            continue
        if v["status"] != "ready":
            continue
        done += 1
        if conv:
            names = ", ".join(i["filename"] for i in v["items"][:3])
            text = f"{v['count']} photo{'s' if v['count'] != 1 else ''} chun li gayi ({names}{'…' if v['count'] > 3 else ''})."
            if v["purpose"]:
                text += f" Ab: {v['purpose']}"
            notify(conv, text)
            bus.publish(conv, "photos_pick", {"pick_id": pid, "status": "ready", "count": v["count"],
                                              "purpose": v["purpose"], "picker_uri": v["picker_uri"]})
            try:
                from ..voice import inject
                inject(conv, f"(Google Photos: the user picked {v['count']} items for pick_id {pid}. Purpose: "
                             f"{v['purpose'] or '-'}. Continue with photos_send / the task now, in one short line.)")
            except Exception:
                pass
    return done


def _items_of(tenant: str, pick_id: str, ids: list[str] | None = None) -> tuple[PhotosPick, list[dict]]:
    v = refresh_pick(tenant, pick_id)
    p = _get_pick(tenant, pick_id)
    if v["status"] == "waiting":
        raise PhotosError("User ne abhi photos nahi chuni hain. Chat card par 'Photos chuniye' dabakar chun lein, phir boliye.")
    if v["status"] == "expired":
        raise PhotosError("Photos chunne ka session expire ho gaya; photos_pick se naya shuru kijiye.")
    items = list(p.items or [])
    if ids:
        want = set(ids)
        items = [i for i in items if i["id"] in want or i["filename"] in want]
        if not items:
            raise PhotosError("In ids ki photo is pick mein nahi hai.")
    return p, items


def _bytes(c: PhotosClient, it: dict) -> bytes:
    if not it.get("base_url"):
        raise PhotosError(f"{it.get('filename')} ka download link nahi mila; dobara chuniye.")
    return c.download(it["base_url"], it.get("type", "PHOTO"))


def send(tenant: str, conv: str, pick_id: str, to: str = "phone", ids: list[str] | None = None,
         folder: str | None = None) -> dict[str, Any]:
    """Picked photos -> phone (download cards) / for_email (file ids for email_draft) / pc / drive."""
    from ..mailbox import service as ms
    from ..pc import service as pcs
    p, items = _items_of(tenant, pick_id, ids)
    c = _client_for(tenant, p.account)
    if len(items) > 50:
        raise PhotosError("Ek baar mein 50 photos tak; kam chuniye ya ids dijiye.")
    out, problems = [], []
    for it in items:
        try:
            data = _bytes(c, it)
        except PhotosError as e:
            problems.append(f"{it['filename']}: {e}")
            continue
        if len(data) > MAX_BYTES:
            problems.append(f"{it['filename']}: 50 MB se badi")
            continue
        direction = "to_pc" if to == "pc" else ("mail" if to in ("for_email", "drive") else "to_phone")
        row = ms.store_bytes(tenant, it["filename"], data, direction)
        entry = {"filename": row.name, "file_id": row.id, "size": len(data)}
        if to == "phone":
            if conv:
                bus.publish(conv, "pc_file", {**pcs.public_file(row), "source": "photos"})
        elif to == "pc":
            from ..pc.hub import hub
            if not hub.is_online(tenant):
                raise PhotosError("PC offline hai. PC par Santosh Desktop chalu kijiye, ya to='phone' se bhejiye.")
            try:
                res = hub.call_sync(tenant, "save_file", {"file_id": row.id, "name": row.name,
                                                          "url": f"/api/pc/fetch/{row.id}"})
                entry["saved"] = (res or {}).get("path", "")
            except Exception as e:
                problems.append(f"{row.name}: PC par save nahi hua ({e})")
                continue
        elif to == "drive":
            try:
                from ..drive import service as ds
                up = ds.upload(tenant, {"file_id": row.id}, folder=folder)
                entry["drive"] = up.get("uploaded", {})
            except Exception as e:
                problems.append(f"{row.name}: Drive mein nahi gaya ({e})")
                continue
        out.append(entry)
    res: dict[str, Any] = {"to": to, "count": len(out), "files": out}
    if problems:
        res["problems"] = problems
    if to == "for_email":
        res["note"] = "Attach with email_draft attachments [{file_id}, ...]."
    return res


def describe(tenant: str, pick_id: str, ids: list[str] | None = None) -> dict[str, Any]:
    p, items = _items_of(tenant, pick_id, ids)
    return {"pick_id": pick_id, "count": len(items), "items": [_public_item(i) for i in items[:100]],
            "note": "Santosh sees file names, sizes and dates, not what is in the picture. Ask the user if the content matters."}


# ---------------- uploading into Google Photos ----------------
def _source_bytes(tenant: str, src: dict[str, Any]) -> tuple[str, str, bytes]:
    from pathlib import Path
    from ..mailbox import service as ms
    if src.get("email_id"):
        name, mt, data = ms.attachment(tenant, src["email_id"], str(src.get("attachment_id") or "0"))
    elif src.get("file_id"):
        row = ms._file_row(tenant, str(src["file_id"]))
        path = Path(row.stored_path)
        if not path.exists():
            raise PhotosError(f"{row.name} ab server par nahi hai (files 24 ghante baad hat jaati hain).")
        name, mt, data = row.name, mimetypes.guess_type(row.name)[0] or "application/octet-stream", path.read_bytes()
    elif src.get("drive_file"):
        try:
            from ..drive import service as ds
            name, mt, data, _c, _f = ds.fetch(tenant, str(src["drive_file"]))
        except Exception as e:
            raise PhotosError(f"Drive se file nahi mili: {e}")
    else:
        raise PhotosError("Har source: {email_id, attachment_id}, {file_id} ya {drive_file}")
    low = name.lower()
    if not (mt.startswith(("image/", "video/")) or low.endswith(IMAGE_EXT + VIDEO_EXT)):
        raise PhotosError(f"{name} photo ya video nahi hai; Google Photos mein sirf photo / video jaati hai.")
    if len(data) > MAX_BYTES:
        raise PhotosError(f"{name} 50 MB se badi hai.")
    if not mt.startswith(("image/", "video/")):
        mt = mimetypes.guess_type(name)[0] or "image/jpeg"
    return name, mt, data


def _album_id(c: PhotosClient, album: str | None) -> tuple[str | None, str | None]:
    if not album:
        return None, None
    for a in c.albums():
        if (a.get("title") or "").strip().lower() == album.strip().lower():
            return a["id"], a.get("productUrl")
    a = c.create_album(album.strip())
    return a["id"], a.get("productUrl")


def upload_now(tenant: str, sources: list[dict], album: str | None = None, description: str = "",
               account: str | None = None) -> dict[str, Any]:
    c = get_client(tenant, account)
    if not c.can_library:
        raise PhotosError("Upload ke liye Profile > Google Photos se Google Photos alag se jodiye (sign-in mein upload "
                          "ki permission nahi hai).")
    album_id, album_url = _album_id(c, album)
    uploaded, problems = [], []
    batch: list[dict] = []
    names: list[str] = []

    def flush():
        if not batch:
            return
        for name, r in zip(names, c.batch_create(list(batch), album_id)):
            st = r.get("status") or {}
            if r.get("mediaItem") and st.get("message", "Success") in ("Success", "OK", "") and not st.get("code"):
                uploaded.append({"filename": name, "url": r["mediaItem"].get("productUrl", "")})
            else:
                problems.append(f"{name}: {st.get('message') or 'upload fail'}")
        batch.clear()
        names.clear()
    for src in sources:
        try:
            name, mt, data = _source_bytes(tenant, src)
            token = c.upload_bytes(data, mt)
        except PhotosError as e:
            problems.append(str(e))
            continue
        batch.append({"description": (description or "")[:1000], "simpleMediaItem": {"uploadToken": token, "fileName": name}})
        names.append(name)
        if len(batch) == 50:
            flush()
    flush()
    res: dict[str, Any] = {"uploaded": len(uploaded), "items": uploaded, "album": album or None, "album_url": album_url}
    if problems:
        res["problems"] = problems
    return res


def plan_or_upload(tenant: str, conv: str, sources: list[dict], album: str | None = None, description: str = "",
                   account: str | None = None) -> dict[str, Any]:
    if not sources:
        raise PhotosError("Kaunsi photos? sources do ({email_id, attachment_id}, {file_id} ya {drive_file}).")
    if len(sources) > 500:
        raise PhotosError("Ek baar mein 500 photos tak.")
    if len(sources) > BIG_UPLOAD:
        with session() as s:
            p = PhotosPending(tenant_id=tenant, conversation_id=conv, action="upload",
                              payload={"sources": sources, "album": album, "description": description, "account": account},
                              summary={"count": len(sources), "album": album or ""})
            s.add(p)
            s.flush()
            return {"pending_id": p.id}
    return upload_now(tenant, sources, album, description, account)


def pending(tenant: str, pid: str) -> dict | None:
    with session() as s:
        p = s.get(PhotosPending, pid)
        if p is None or p.tenant_id != tenant:
            return None
        return {"id": p.id, "action": p.action, "payload": p.payload, "summary": p.summary, "status": p.status,
                "conversation_id": p.conversation_id}


def run_pending(tenant: str, pid: str) -> dict[str, Any]:
    p = pending(tenant, pid)
    if p is None or p["status"] != "pending":
        raise PhotosError("Yeh upload ab baaki nahi hai.")
    pl = p["payload"]
    try:
        res = upload_now(tenant, pl["sources"], pl.get("album"), pl.get("description", ""), pl.get("account"))
    except PhotosError:
        with session() as s:
            s.get(PhotosPending, pid).status = "failed"
        raise
    with session() as s:
        s.get(PhotosPending, pid).status = "done"
    msg = f"{res['uploaded']} photos Google Photos mein daal di" + (f" (album '{pl['album']}')" if pl.get("album") else "") + "."
    if res.get("problems"):
        msg += f" {len(res['problems'])} nahi gayi."
    return {"message": msg, **res}


# ---------------- albums (only the ones Santosh made) ----------------
def albums(tenant: str, account: str | None = None) -> list[dict[str, Any]]:
    c = get_client(tenant, account)
    return [{"id": a["id"], "title": a.get("title", ""), "items": int(a.get("mediaItemsCount") or 0),
             "url": a.get("productUrl", "")} for a in c.albums()]


def create_album(tenant: str, title: str, account: str | None = None) -> dict[str, Any]:
    if not (title or "").strip():
        raise PhotosError("Album ka naam do.")
    c = get_client(tenant, account)
    aid, url = _album_id(c, title)
    return {"id": aid, "title": title.strip(), "url": url}


def album_items(tenant: str, album: str, limit: int = 50, account: str | None = None) -> dict[str, Any]:
    c = get_client(tenant, account)
    found = [a for a in c.albums() if a["id"] == album or (a.get("title") or "").lower() == (album or "").strip().lower()]
    if not found:
        raise PhotosError(f"'{album}' album nahi mila. Santosh sirf apne banaye albums dekh sakta hai.")
    a = found[0]
    items = c.album_items(a["id"], limit)
    return {"album": a.get("title", ""), "url": a.get("productUrl", ""), "count": len(items),
            "items": [{"id": m.get("id"), "filename": m.get("filename", ""), "url": m.get("productUrl", ""),
                       "taken": (m.get("mediaMetadata") or {}).get("creationTime", "")} for m in items]}


LIMITS = ("Google ki policy (31 March 2025 se): Santosh aapki poori Google Photos library nahi dekh sakta, na share "
          "kar sakta hai, na delete. Aap photos chunte hain (photos_pick), ya Santosh photos upload karke apne albums "
          "bana sakta hai. Share / delete Google Photos app mein khud kijiye.")

