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
MAX_BYTES = 200 * 1024 * 1024        # v0.999.191 Google's photo limit (was 50 MB)
MAX_VIDEO = 1024 * 1024 * 1024       # Google takes videos up to 20 GB; Hoola reads a file whole, so 1 GB here
STORAGE_NOTE = 25 * 1024 * 1024      # Google asks apps to remind her past 25 MB that uploads use her storage
PICK_MINUTES = 30
LINK_MINUTES = 50                    # Google's download links last 60 minutes; fetch fresh ones before that
PICK_KEEP_MINUTES = 55               # the picked items stay usable this long after she picks
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
    out = {"id": m.get("id", ""), "type": m.get("type", "PHOTO"), "filename": mf.get("filename", "") or f"{m.get('id', 'photo')}.jpg",
           "mime": mf.get("mimeType", "image/jpeg"), "width": meta.get("width"), "height": meta.get("height"),
           "taken": m.get("createTime", ""), "base_url": mf.get("baseUrl", "")}
    cam = " ".join(x for x in (meta.get("cameraMake"), meta.get("cameraModel")) if x)
    if cam:
        out["camera"] = cam
    ph = meta.get("photoMetadata") or {}
    shot = [f"f/{ph['apertureFNumber']}" if ph.get("apertureFNumber") else "",
            f"{ph['focalLength']} mm" if ph.get("focalLength") else "",
            f"ISO {ph['isoEquivalent']}" if ph.get("isoEquivalent") else "", ph.get("exposureTime") or ""]
    if any(shot):
        out["settings"] = " ".join(x for x in shot if x)
    vid = meta.get("videoMetadata") or {}
    if vid.get("fps"):
        out["fps"] = vid["fps"]
    if vid.get("processingStatus"):
        out["video_status"] = vid["processingStatus"]
    return out


def _public_item(it: dict) -> dict[str, Any]:
    return {k: it.get(k) for k in ("id", "type", "filename", "mime", "width", "height", "taken", "camera", "settings",
                                   "fps", "video_status") if it.get(k) not in (None, "")}


def pick_view(p: PhotosPick) -> dict[str, Any]:
    return {"pick_id": p.id, "status": p.status, "purpose": p.purpose, "picker_uri": p.picker_uri,
            "count": p.item_count, "items": [_public_item(i) for i in (p.items or [])][:60]}


def start_pick(tenant: str, conv: str, purpose: str = "", max_items: int = 0, account: str | None = None) -> dict[str, Any]:
    c = get_client(tenant, account)
    ses = c.new_session(int(max_items or 0))
    uri = (ses.get("pickerUri") or "").rstrip("/")
    if not uri:
        raise PhotosError("Google Photos did not give a picker link; please try again.")
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
            raise PhotosError("This photo picking session was not found. Start a new one with photos_pick.")
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
        if "nahi mila" in str(e) or "not found" in str(e):
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
        row.ready_at = row.listed_at = now()
    # v0.999.191 the session is NOT deleted here any more: its download links are what photos_send uses, so it is
    # cleaned up by poll_tick once the picked items are no longer usable (Google: delete it after you are done)
    return pick_view(_get_pick(tenant, pick_id))


def _fresh_links(c: PhotosClient, p: PhotosPick) -> list[dict]:
    """Google's download links last 60 minutes: past LINK_MINUTES ask the picking session for new ones."""
    listed = as_utc(p.listed_at) or as_utc(p.ready_at) or as_utc(p.created_at)
    items = list(p.items or [])
    if listed and listed > now() - timedelta(minutes=LINK_MINUTES):
        return items
    try:
        fresh = {m.get("id"): _item_view(m) for m in c.picked(p.session_id)}
    except PhotosError:
        _mark(p.id, "ended")
        raise PhotosError("The picked photos can no longer be fetched from Google Photos (the picking session ended). "
                          "Start a new pick with photos_pick.")
    items = [fresh.get(i["id"], i) for i in items]
    with session() as s:
        row = s.get(PhotosPick, p.id)
        row.items, row.listed_at = items, now()
    return items


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
        old_ready = [(p.id, p.tenant_id, p.account, p.session_id) for p in s.scalars(select(PhotosPick).where(
            PhotosPick.status == "ready", PhotosPick.ready_at < now() - timedelta(minutes=PICK_KEEP_MINUTES))).all()]
    for pid, tenant, acct, sid in old_ready:       # v0.999.191 clean up finished sessions, as Google asks
        try:
            _client_for(tenant, acct).delete_session(sid)
        except Exception:
            pass
        _mark(pid, "ended")
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
            text = f"{v['count']} photo{'s' if v['count'] != 1 else ''} picked ({names}{'…' if v['count'] > 3 else ''})."
            if v["purpose"]:
                text += f" Next: {v['purpose']}"
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
        raise PhotosError("The user has not picked photos yet. Tap the photo picker card in the chat, pick them, then tell me.")
    if v["status"] == "expired":
        raise PhotosError("The photo picking session has expired; start a new one with photos_pick.")
    if v["status"] == "ended":
        raise PhotosError("Picked photos can be fetched for about an hour after picking (Google's rule); this pick has "
                          "ended. Start a new one with photos_pick.")
    items = _fresh_links(_client_for(tenant, p.account), p)
    if ids:
        want = set(ids)
        items = [i for i in items if i["id"] in want or i["filename"] in want]
        if not items:
            raise PhotosError("These ids are not in this pick.")
    return p, items


def _bytes(c: PhotosClient, it: dict, preview: bool = False) -> bytes:
    if not it.get("base_url"):
        raise PhotosError(f"{it.get('filename')} has no download link; pick it again.")
    if it.get("type") == "VIDEO" and it.get("video_status") not in (None, "", "READY") and not preview:
        raise PhotosError(f"{it.get('filename')} is still being processed by Google Photos; try again in a few minutes.")
    return c.download(it["base_url"], it.get("type", "PHOTO"), preview)


def send(tenant: str, conv: str, pick_id: str, to: str = "phone", ids: list[str] | None = None,
         folder: str | None = None) -> dict[str, Any]:
    """Picked photos -> phone (download cards) / for_email (file ids for email_draft) / pc / drive."""
    p, items = _items_of(tenant, pick_id, ids)
    return deliver(tenant, conv, _client_for(tenant, p.account), items, to, folder)


def deliver(tenant: str, conv: str, c: PhotosClient, items: list[dict], to: str = "phone",
            folder: str | None = None) -> dict[str, Any]:
    """Photos with a Google download link -> phone / for_email / pc / drive (v0.999.191 shared by picks + Hoola's uploads)."""
    from ..mailbox import service as ms
    from ..pc import service as pcs
    if to not in ("phone", "for_email", "pc", "drive"):
        raise PhotosError("to: phone, for_email, pc or drive.")
    if len(items) > 100:
        raise PhotosError("Up to 100 photos at a time; give ids for the rest.")
    if to == "pc":
        from ..pc.hub import hub
        if not hub.is_online(tenant):
            raise PhotosError("The PC is offline. Start Santosh Desktop on the PC, or send with to='phone'.")
    out, problems = [], []
    for it in items:
        try:
            data = _bytes(c, it)
        except PhotosError as e:
            problems.append(f"{it['filename']}: {e}")
            continue
        if len(data) > MAX_BYTES:
            problems.append(f"{it['filename']}: larger than 200 MB")
            continue
        direction = "to_pc" if to == "pc" else ("mail" if to in ("for_email", "drive") else "to_phone")
        row = ms.store_bytes(tenant, it["filename"], data, direction)
        entry = {"filename": row.name, "file_id": row.id, "size": len(data)}
        if to == "phone":
            if conv:
                bus.publish(conv, "pc_file", {**pcs.public_file(row), "source": "photos"})
        elif to == "pc":
            from ..pc.hub import hub
            try:
                res = hub.call_sync(tenant, "save_file", {"file_id": row.id, "name": row.name,
                                                          "url": f"/api/pc/fetch/{row.id}"})
                entry["saved"] = (res or {}).get("path", "")
            except Exception as e:
                problems.append(f"{row.name}: not saved on the PC ({e})")
                continue
        elif to == "drive":
            try:
                from ..drive import service as ds
                up = ds.upload(tenant, {"file_id": row.id}, folder=folder)
                entry["drive"] = up.get("uploaded", {})
            except Exception as e:
                problems.append(f"{row.name}: not saved to Drive ({e})")
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
            raise PhotosError(f"{row.name} is no longer on the server (files are removed after 24 hours).")
        name, mt, data = row.name, mimetypes.guess_type(row.name)[0] or "application/octet-stream", path.read_bytes()
    elif src.get("url"):
        name, mt, data = _from_web(str(src["url"]))
    elif src.get("pick_id"):
        p, items = _items_of(tenant, str(src["pick_id"]), [str(src["id"])] if src.get("id") else None)
        it = items[0]
        data = _bytes(_client_for(tenant, p.account), it)
        name, mt = it["filename"], it.get("mime") or "image/jpeg"
    elif src.get("drive_file"):
        try:
            from ..drive import service as ds
            name, mt, data, _c, _f = ds.fetch(tenant, str(src["drive_file"]))
        except Exception as e:
            raise PhotosError(f"File not found in Drive: {e}")
    else:
        raise PhotosError("Each source: {email_id, attachment_id}, {file_id}, {drive_file} or {url}")
    low = name.lower()
    if not (mt.startswith(("image/", "video/")) or low.endswith(IMAGE_EXT + VIDEO_EXT)):
        raise PhotosError(f"{name} is not a photo or video; only photos / videos can go to Google Photos.")
    if not mt.startswith(("image/", "video/")):
        mt = mimetypes.guess_type(name)[0] or "image/jpeg"
    if mt.startswith("video/") and len(data) > MAX_VIDEO:
        raise PhotosError(f"{name} is larger than 1 GB; upload it from the Google Photos app.")
    if mt.startswith("image/") and len(data) > MAX_BYTES:
        raise PhotosError(f"{name} is larger than 200 MB, Google Photos' limit for a photo.")
    return name, mt, data


def _from_web(url: str) -> tuple[str, str, bytes]:
    """v0.999.191 a photo / video from a public web link, through the same guarded fetch Drive uses."""
    try:
        from ..drive import more as dmore
        name, mt, data = dmore.from_link(url, MAX_BYTES)
    except Exception as e:
        raise PhotosError(f"Could not download {url[:120]}: {e}")
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
               account: str | None = None, position: dict | None = None, descriptions: list[str] | None = None) -> dict[str, Any]:
    c = get_client(tenant, account)
    if not c.can_library:
        raise PhotosError("For uploads, connect Google Photos separately under Profile > Google Photos (the sign-in has no upload "
                          "permission).")
    album_id, album_url = _album_id(c, album)
    uploaded, problems = [], []
    batch: list[dict] = []
    names: list[str] = []

    total = 0
    pos = {"p": position}

    def flush():
        if not batch:
            return
        for name, r in zip(names, c.batch_create(list(batch), album_id, pos["p"] if album_id else None)):
            st = r.get("status") or {}
            if r.get("mediaItem") and not st.get("code"):
                m = r["mediaItem"]
                uploaded.append({"filename": name, "id": m.get("id", ""), "url": m.get("productUrl", "")})
            else:
                problems.append(f"{name}: {st.get('message') or 'upload fail'}")
        if uploaded and pos["p"] and pos["p"].get("position") != "LAST_IN_ALBUM":
            # the next batch goes right after the last one added, so the order she gave holds
            pos["p"] = {"position": "AFTER_MEDIA_ITEM", "relativeMediaItemId": uploaded[-1]["id"]}
        batch.clear()
        names.clear()
    for n, src in enumerate(sources):
        try:
            name, mt, data = _source_bytes(tenant, src)
            token = c.upload_bytes(data, mt)
        except PhotosError as e:
            problems.append(str(e))
            continue
        total += len(data)
        desc = (descriptions[n] if descriptions and n < len(descriptions) and descriptions[n] else description) or ""
        batch.append({"description": str(desc)[:1000], "simpleMediaItem": {"uploadToken": token, "fileName": name}})
        names.append(name)
        if len(batch) == 50:
            flush()
    flush()
    res: dict[str, Any] = {"uploaded": len(uploaded), "items": uploaded, "album": album or None, "album_url": album_url}
    if total > STORAGE_NOTE:
        res["storage_note"] = ("Uploads keep the original quality and count towards her Google Account storage "
                               f"({total // (1024 * 1024)} MB this time).")
    if problems:
        res["problems"] = problems
    return res


def plan_or_upload(tenant: str, conv: str, sources: list[dict], album: str | None = None, description: str = "",
                   account: str | None = None, position: dict | None = None,
                   descriptions: list[str] | None = None) -> dict[str, Any]:
    if not sources:
        raise PhotosError("Which photos? Give sources ({email_id, attachment_id}, {file_id} or {drive_file}).")
    if len(sources) > 500:
        raise PhotosError("Up to 500 photos at a time.")
    if len(sources) > BIG_UPLOAD:
        with session() as s:
            p = PhotosPending(tenant_id=tenant, conversation_id=conv, action="upload",
                              payload={"sources": sources, "album": album, "description": description, "account": account,
                                       "position": position, "descriptions": descriptions},
                              summary={"count": len(sources), "album": album or ""})
            s.add(p)
            s.flush()
            return {"pending_id": p.id}
    return upload_now(tenant, sources, album, description, account, position, descriptions)


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
        raise PhotosError("This upload is no longer pending.")
    pl = p["payload"]
    if p["action"] != "upload":
        from . import more
        return more.run_pending(tenant, pid, p)
    try:
        res = upload_now(tenant, pl["sources"], pl.get("album"), pl.get("description", ""), pl.get("account"),
                         pl.get("position"), pl.get("descriptions"))
    except PhotosError:
        with session() as s:
            s.get(PhotosPending, pid).status = "failed"
        raise
    with session() as s:
        s.get(PhotosPending, pid).status = "done"
    msg = f"{res['uploaded']} photos added to Google Photos" + (f" (album '{pl['album']}')" if pl.get("album") else "") + "."
    if res.get("problems"):
        msg += f" {len(res['problems'])} could not be added."
    return {"message": msg, **res}


# ---------------- albums (only the ones Santosh made) ----------------
def albums(tenant: str, account: str | None = None) -> list[dict[str, Any]]:
    c = get_client(tenant, account)
    return [{"id": a["id"], "title": a.get("title", ""), "items": int(a.get("mediaItemsCount") or 0),
             "url": a.get("productUrl", "")} for a in c.albums()]


def create_album(tenant: str, title: str, account: str | None = None) -> dict[str, Any]:
    if not (title or "").strip():
        raise PhotosError("Give the album name.")
    c = get_client(tenant, account)
    aid, url = _album_id(c, title)
    return {"id": aid, "title": title.strip(), "url": url}


def album_items(tenant: str, album: str, limit: int = 200, account: str | None = None) -> dict[str, Any]:
    c = get_client(tenant, account)
    found = [a for a in c.albums() if a["id"] == album or (a.get("title") or "").lower() == (album or "").strip().lower()]
    if not found:
        raise PhotosError(f"Album '{album}' not found. Santosh can only see albums it created.")
    a = found[0]
    items = c.album_items(a["id"], limit)
    return {"album": a.get("title", ""), "url": a.get("productUrl", ""), "count": len(items),
            "items": [{"id": m.get("id"), "filename": m.get("filename", ""), "url": m.get("productUrl", ""),
                       "taken": (m.get("mediaMetadata") or {}).get("creationTime", "")} for m in items]}


LIMITS = ("Google's rule since 31 March 2025: Hoola cannot see her whole Google Photos library, cannot share albums or "
          "photos, and cannot delete anything. She picks photos for Hoola (photos_pick); Hoola can look at, send and save "
          "those, upload photos and videos into her Google Photos, and manage only the albums and photos Hoola added "
          "(rename, cover, add / remove, notes, places, maps, captions). Sharing and deleting are done in the Google "
          "Photos app.")
