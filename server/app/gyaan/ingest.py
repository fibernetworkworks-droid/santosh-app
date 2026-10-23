"""Gyaan ingest: everything that goes INTO an owner's knowledge base, and everything that takes it out again.

Sources: her chat / call files (automatically, `auto_files`), files she adds on the Gyaan screen, Google Drive folders she
picks (re-synced daily), her mailbox (only when SHE switches it on; last GYAAN_MAIL_DAYS days, newest first), and notes
(text she or Hoola saves). Chats and calls are not copied: search reads Hoola ki yaad directly.

Every text is masked first (norm.mask), chunked (chunk.split), indexed twice (FTS5 words + trigram Roman key), its IDs
are pulled out, and vectors are made in the background (int8). The same item added again with the same text is a no-op;
changed text replaces the old chunks completely (no stale pieces)."""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from . import chunk, norm, store

log = logging.getLogger("santosh.gyaan")
SOURCES = ("file", "drive", "mail", "note", "web", "record")
MAX_DOC_CHARS = 600_000
_EMBEDDING: set[str] = set()
_ELOCK = threading.Lock()


class GyaanError(ValueError):
    pass


def doc_id(source: str, ref: str) -> str:
    return "g" + hashlib.sha1(f"{source}|{ref}".encode()).hexdigest()[:14]


def _index_body(prefix: str, text: str) -> str:
    """What the word index sees: prefix + text + canonical numbers (so "1.5 lakh" and "150000" meet)."""
    nums = " ".join(norm.numbers(text)[:60])
    return f"{prefix}\n{norm.ascii_digits(text)}\n{nums}"


def _tri_body(prefix: str, text: str) -> str:
    return norm.phon(prefix + " " + text)


def add_text(tenant: str, source: str, ref: str, title: str, text: str, kind: str = "doc", at: str = "",
             meta: dict[str, Any] | None = None, scope: str = "owner") -> dict[str, Any]:
    if source not in SOURCES:
        raise GyaanError(f"source must be one of {', '.join(SOURCES)}")
    text = (text or "").replace("\x00", "")[:MAX_DOC_CHARS]
    title = (title or ref or "Bina naam").strip()[:200]
    masked, found = norm.mask(text)
    if not masked.strip():
        return {"status": "empty", "doc_id": "", "chunks": 0}
    sha = hashlib.sha256(masked.encode()).hexdigest()
    did = doc_id(source, ref)
    pieces = chunk.split(masked, kind)
    if not pieces:
        return {"status": "empty", "doc_id": "", "chunks": 0}
    with store.db(tenant, write=True) as c:
        old = c.execute("SELECT sha FROM docs WHERE id=?", (did,)).fetchone()
        if old and old["sha"] == sha:
            c.execute("UPDATE docs SET updated=? WHERE id=?", (store.now(), did))
            return {"status": "same", "doc_id": did, "chunks": 0, "title": title}
        if old:
            store.delete_doc(c, did)
        pre = chunk.prefix(title, kind, at)
        tri = store.has_tri(c)
        for i, p in enumerate(pieces):
            cur = c.execute("INSERT INTO chunks(doc_id, ord, page, text, prefix) VALUES(?,?,?,?,?)",
                            (did, i, p["page"], p["text"], pre))
            cid = cur.lastrowid
            c.execute("INSERT INTO fts(rowid, body) VALUES(?, ?)", (cid, _index_body(pre, p["text"])))
            if tri:
                c.execute("INSERT INTO tri(rowid, body) VALUES(?, ?)", (cid, _tri_body(pre, p["text"])))
            for kind_, v in norm.ids(p["text"] + " " + title):
                c.execute("INSERT INTO ids(value, kind, chunk_id) VALUES(?,?,?)", (v, kind_, cid))
        c.execute("INSERT INTO docs(id, source, ref, title, kind, sha, scope, at, added, updated, chunks, chars, masked, meta)"
                  " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (did, source, ref, title, kind, sha, scope, at or "", store.now(), store.now(), len(pieces), len(masked),
                   ",".join(found), json.dumps(meta or {})))
        store.bump(c)
    kick(tenant)
    return {"status": "updated" if old else "added", "doc_id": did, "chunks": len(pieces), "title": title,
            "masked": found}


def add_bytes(tenant: str, name: str, data: bytes, source: str = "file", ref: str = "", mime: str = "",
              meta: dict[str, Any] | None = None) -> dict[str, Any]:
    from .extract import text_of
    if not data:
        raise GyaanError("File khaali hai.")
    if len(data) > 60 * 1024 * 1024:
        raise GyaanError("60 MB se badi file Gyaan mein nahi jaati.")
    from .. import filecheck
    rt = filecheck.real_type(name or "file", data)
    if rt.get("danger"):
        raise GyaanError(f"Yeh file khatarnak lag rahi hai ({rt.get('note')}); Gyaan mein nahi li.")
    r = text_of(name, data, tenant, mime)
    if not r["text"].strip():
        return {"status": "empty", "doc_id": "", "chunks": 0, "title": name, "note": r["note"]}
    out = add_text(tenant, source, ref or hashlib.sha256(data).hexdigest()[:24], name, r["text"],
                   "sheet" if r["kind"] == "sheet" else "doc", "", {**(meta or {}), "ocr": r["ocr"], "file_kind": r["kind"]})
    if r["note"]:
        out["note"] = r["note"]
    return out


def add_owner_file(tenant: str, file_id: str) -> dict[str, Any]:
    """One of her stored files (chat / call attachment, Document desk, made by Hoola) -> Gyaan."""
    from pathlib import Path
    from ..mailbox import service as ms
    try:
        f = ms._file_row(tenant, str(file_id))
    except Exception as e:
        raise GyaanError(str(e))
    data = Path(f.stored_path).read_bytes()
    return add_bytes(tenant, f.name, data, "file", f"file:{f.id}", meta={"file_id": f.id})


# ---------------------------------------------------------------- auto: her chat / call files
def auto_file(tenant: str, file_id: str) -> None:
    """Called when she attaches a file anywhere (chatfiles.store): indexed in the background when `auto_files` is on."""
    from ..config import get_settings
    if not get_settings().gyaan_on or not settings(tenant).get("auto_files", True):
        return

    def _go() -> None:
        try:
            add_owner_file(tenant, file_id)
        except Exception as e:
            log.info("gyaan auto file %s skipped: %s", file_id, e)
    if get_settings().gyaan_sync:
        _go()
    else:
        threading.Thread(target=_go, daemon=True, name="gyaan-file").start()


# ---------------------------------------------------------------- notes
def add_note(tenant: str, title: str, text: str) -> dict[str, Any]:
    ref = "note:" + hashlib.sha1((title + "|" + text).encode()).hexdigest()[:16]
    return add_text(tenant, "note", ref, title or text[:60], text, "note", datetime.now(timezone.utc).date().isoformat())


# ---------------------------------------------------------------- Google Drive folders
def add_drive_folder(tenant: str, folder: str) -> dict[str, Any]:
    from ..drive import service as ds
    from ..drive.client import FOLDER
    try:
        c, f = ds.resolve(tenant, folder, folder=True)
    except Exception as e:
        raise GyaanError(f"Drive folder nahi mila: {e}")
    if f.get("mimeType") != FOLDER:
        raise GyaanError(f"'{f.get('name')}' folder nahi, file hai. Folder ka naam ya link dijiye.")
    ref = ds.make_ref(c, f["id"])
    wid = "w" + hashlib.sha1(ref.encode()).hexdigest()[:10]
    with store.db(tenant, write=True) as db:
        db.execute("INSERT OR REPLACE INTO watch(id, kind, ref, name, added, synced, files, error) VALUES(?,?,?,?,?,?,?,?)",
                   (wid, "drive", ref, f.get("name") or "Drive folder", store.now(), 0, 0, ""))
    res = sync_drive(tenant, wid)
    return {"watch_id": wid, "folder": f.get("name"), **res}


def _drive_text(tenant: str, c, f: dict) -> str:
    from ..drive import service as ds
    from ..drive.client import GDOC, GSHEET, GSLIDES
    from .extract import text_of
    mt = f.get("mimeType", "")
    if mt in (GDOC, GSLIDES):
        return c.export(f["id"], "text/plain").decode("utf-8", "replace")
    if mt == GSHEET:
        return c.export(f["id"], "text/csv").decode("utf-8", "replace")
    if mt.startswith("application/vnd.google-apps"):
        return ""
    name, emime, data, _c, _f = ds.fetch(tenant, ds.make_ref(c, f["id"]))
    return text_of(name, data, tenant, emime)["text"]


def sync_drive(tenant: str, watch_id: str = "", max_files: int = 200) -> dict[str, Any]:
    """Re-read the folder (and sub-folders 2 levels down): new / changed files in, files gone from Drive out."""
    from ..drive import service as ds
    from ..drive.client import FOLDER, q_str
    with store.db(tenant) as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM watch WHERE kind='drive'" + (" AND id=?" if watch_id else ""),
                                            (watch_id,) if watch_id else ())]
    total = {"added": 0, "updated": 0, "same": 0, "removed": 0, "skipped": 0, "errors": []}
    for w in rows:
        try:
            c, root = ds.resolve(tenant, w["ref"], folder=True)
            queue, seen_files, depth = [(root["id"], 0)], [], {}
            while queue and len(seen_files) < max_files:
                fid, d = queue.pop(0)
                for f in c.search(f"{q_str(fid)} in parents and trashed = false", 100, order="folder,name"):
                    if f.get("mimeType") == FOLDER:
                        if d < 2:
                            queue.append((f["id"], d + 1))
                        continue
                    seen_files.append(f)
            keep: set[str] = set()
            for f in seen_files[:max_files]:
                ref = "drive:" + ds.make_ref(c, f["id"])
                keep.add(doc_id("drive", ref))
                with store.db(tenant) as db:
                    old = db.execute("SELECT meta FROM docs WHERE id=?", (doc_id("drive", ref),)).fetchone()
                if old and json.loads(old["meta"] or "{}").get("modified") == f.get("modifiedTime"):
                    total["same"] += 1
                    continue
                try:
                    text = _drive_text(tenant, c, f)
                except Exception as e:
                    total["skipped"] += 1
                    total["errors"].append(f"{f.get('name')}: {str(e)[:80]}")
                    continue
                if not text.strip():
                    total["skipped"] += 1
                    continue
                r = add_text(tenant, "drive", ref, f.get("name") or "Drive file",
                             text, "sheet" if f.get("mimeType", "").endswith("spreadsheet") or f.get("name", "").lower().endswith((".csv", ".xlsx")) else "doc",
                             (f.get("modifiedTime") or "")[:10],
                             {"modified": f.get("modifiedTime"), "link": f.get("webViewLink", ""), "watch": w["id"]})
                total[r["status"] if r["status"] in total else "skipped"] += 1
            with store.db(tenant, write=True) as db:
                gone = [r["id"] for r in db.execute("SELECT id, meta FROM docs WHERE source='drive'")
                        if json.loads(r["meta"] or "{}").get("watch") == w["id"] and r["id"] not in keep]
                for g in gone:
                    store.delete_doc(db, g)
                total["removed"] += len(gone)
                db.execute("UPDATE watch SET synced=?, files=?, error=? WHERE id=?",
                           (store.now(), len(keep), "", w["id"]))
                if gone:
                    store.bump(db)
        except Exception as e:
            log.info("gyaan drive sync %s failed: %s", w.get("name"), e)
            total["errors"].append(f"{w.get('name')}: {str(e)[:120]}")
            with store.db(tenant, write=True) as db:
                db.execute("UPDATE watch SET synced=?, error=? WHERE id=?", (store.now(), str(e)[:300], w["id"]))
    total["errors"] = total["errors"][:10]
    return total


def remove_watch(tenant: str, watch_id: str, forget_files: bool = True) -> dict[str, Any]:
    with store.db(tenant, write=True) as db:
        n = 0
        if forget_files:
            for r in db.execute("SELECT id, meta FROM docs WHERE source='drive'").fetchall():
                if json.loads(r["meta"] or "{}").get("watch") == watch_id:
                    store.delete_doc(db, r["id"])
                    n += 1
        db.execute("DELETE FROM watch WHERE id=?", (watch_id,))
        store.bump(db)
    return {"removed_docs": n}


# ---------------------------------------------------------------- mailbox (only when she turns it on)
def sync_mail(tenant: str, limit: int = 40) -> dict[str, Any]:
    from ..config import get_settings
    from ..mailbox import service as ms
    if not settings(tenant).get("mail_on"):
        return {"status": "off"}
    days = get_settings().gyaan_mail_days
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        listed = ms.check(tenant, "inbox", False, None, limit, None, since, False)
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
    added = same = 0
    for it in listed.get("emails") or []:
        ref = "mail:" + str(it.get("id"))
        did = doc_id("mail", ref)
        with store.db(tenant) as db:
            if db.execute("SELECT 1 FROM docs WHERE id=?", (did,)).fetchone():
                same += 1
                continue
        if it.get("bulk"):
            continue                       # newsletters / no-reply mail are not her knowledge
        try:
            m = ms.read(tenant, str(it.get("id")), mark_seen=False)
        except Exception:
            continue
        body = f"From: {m.get('from')} <{m.get('from_email')}>\nSubject: {m.get('subject')}\nDate: {m.get('date')}\n\n{m.get('body') or ''}"
        add_text(tenant, "mail", ref, m.get("subject") or "(no subject)", body, "mail", _mail_date(m.get("date")),
                 {"from": m.get("from_email"), "thread": m.get("thread_id")})
        added += 1
    with store.db(tenant, write=True) as db:
        store.set_meta(db, "mail_synced", store.now())
    return {"status": "ok", "added": added, "known": same}


def _mail_date(d: Any) -> str:
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(str(d)).date().isoformat()
    except Exception:
        return ""


# ---------------------------------------------------------------- vectors (background)
def embed_pending(tenant: str, limit: int = 256) -> int:
    from . import embed
    e = embed.embedder()
    if e is None:
        return 0
    with store.db(tenant) as db:
        rows = db.execute("SELECT c.id, c.text, c.prefix FROM chunks c LEFT JOIN vecs v ON v.chunk_id=c.id "
                          "WHERE v.chunk_id IS NULL OR v.model != ? LIMIT ?", (e.name, limit)).fetchall()
    if not rows:
        return 0
    done = 0
    for i in range(0, len(rows), 32):
        part = rows[i:i + 32]
        m, name = embed.safe_embed([(r["prefix"] + "\n" + r["text"])[:2000] for r in part], "doc")
        if m is None:
            break
        with store.db(tenant, write=True) as db:
            for r, v in zip(part, m):
                q, s = embed.quantize(v)
                db.execute("INSERT OR REPLACE INTO vecs(chunk_id, model, dim, q, scale) VALUES(?,?,?,?,?)",
                           (r["id"], name, int(v.shape[0]), q, s))
            store.bump(db)
        done += len(part)
    return done


def kick(tenant: str) -> None:
    """Make vectors for new chunks: inline in tests (GYAAN_SYNC), else one background thread per owner."""
    from ..config import get_settings
    if get_settings().gyaan_sync:
        while embed_pending(tenant):
            pass
        return
    with _ELOCK:
        if tenant in _EMBEDDING:
            return
        _EMBEDDING.add(tenant)

    def _go() -> None:
        try:
            for _ in range(400):
                if not embed_pending(tenant):
                    break
        except Exception:
            log.exception("gyaan embedding failed")
        finally:
            with _ELOCK:
                _EMBEDDING.discard(tenant)
    threading.Thread(target=_go, daemon=True, name="gyaan-embed").start()


# ---------------------------------------------------------------- forget
def forget(tenant: str, doc: str) -> dict[str, Any]:
    with store.db(tenant, write=True) as db:
        r = db.execute("SELECT title FROM docs WHERE id=?", (doc,)).fetchone()
        if not r:
            raise GyaanError("Yeh cheez Gyaan mein nahi hai.")
        n = store.delete_doc(db, doc)
        store.bump(db)
    from . import search
    search.drop_cache(tenant)
    return {"forgot": r["title"], "chunks": n}


def forget_where(tenant: str, source: str = "", title_has: str = "") -> dict[str, Any]:
    with store.db(tenant, write=True) as db:
        q, a = "SELECT id, title FROM docs WHERE 1=1", []
        if source:
            q += " AND source=?"
            a.append(source)
        if title_has:
            q += " AND lower(title) LIKE ?"
            a.append(f"%{title_has.lower()}%")
        rows = db.execute(q, a).fetchall()
        for r in rows:
            store.delete_doc(db, r["id"])
        store.bump(db)
    from . import search
    search.drop_cache(tenant)
    return {"forgot": [r["title"] for r in rows][:30], "count": len(rows)}


def forget_all(tenant: str) -> dict[str, Any]:
    store.wipe(tenant)
    return {"forgot_all": True}


# ---------------------------------------------------------------- settings + views
DEFAULTS = {"auto_files": True, "mail_on": False}


def settings(tenant: str) -> dict[str, Any]:
    with store.db(tenant) as db:
        s = store.get_meta(db, "settings", {}) or {}
    return {**DEFAULTS, **s}


def save_settings(tenant: str, **kw: Any) -> dict[str, Any]:
    cur = settings(tenant)
    for k in DEFAULTS:
        if k in kw and kw[k] is not None:
            cur[k] = bool(kw[k])
    with store.db(tenant, write=True) as db:
        store.set_meta(db, "settings", cur)
    if not cur["mail_on"] and "mail_on" in kw:
        forget_where(tenant, "mail")          # mail switched off = mail forgotten too
    return cur


def docs(tenant: str, source: str = "", q: str = "", limit: int = 100) -> list[dict[str, Any]]:
    with store.db(tenant) as db:
        sql, a = "SELECT id, source, ref, title, kind, at, added, chunks, chars, masked, meta FROM docs WHERE 1=1", []
        if source:
            sql += " AND source=?"
            a.append(source)
        if q:
            sql += " AND lower(title) LIKE ?"
            a.append(f"%{q.lower()}%")
        rows = db.execute(sql + " ORDER BY added DESC LIMIT ?", (*a, limit)).fetchall()
    out = []
    for r in rows:
        m = json.loads(r["meta"] or "{}")
        out.append({"id": r["id"], "source": r["source"], "title": r["title"], "kind": r["kind"], "at": r["at"],
                    "added": datetime.fromtimestamp(r["added"], timezone.utc).isoformat(), "chunks": r["chunks"],
                    "chars": r["chars"], "masked": [x for x in (r["masked"] or "").split(",") if x],
                    "link": m.get("link", ""), "file_id": m.get("file_id", "")})
    return out


def status(tenant: str) -> dict[str, Any]:
    from . import embed
    e = embed.embedder()
    with store.db(tenant) as db:
        by = {r[0]: r[1] for r in db.execute("SELECT source, COUNT(*) FROM docs GROUP BY source")}
        chunks = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        vec = db.execute("SELECT COUNT(*) FROM vecs WHERE model=?", (e.name if e else "",)).fetchone()[0]
        watches = [dict(r) for r in db.execute("SELECT id, kind, ref, name, synced, files, error FROM watch")]
        mail_synced = store.get_meta(db, "mail_synced", 0)
        ver = store.version(db)
    for w in watches:
        w["synced"] = datetime.fromtimestamp(w["synced"], timezone.utc).isoformat() if w["synced"] else ""
    from ..config import get_settings
    st = get_settings()
    return {"docs": sum(by.values()), "by_source": by, "chunks": chunks, "vectors": vec,
            "vectors_pct": round(100 * vec / chunks) if chunks else 100, "embedder": e.name if e else "none",
            "reranker": st.gyaan_rerank_model if (st.gyaan_rerank and st.voyage_api_key) else "",
            "keyword": "fts5 + trigram" if store.HAS_TRIGRAM else "fts5", "watches": watches,
            "mail_synced": datetime.fromtimestamp(mail_synced, timezone.utc).isoformat() if mail_synced else "",
            "settings": settings(tenant), "version": ver}


def daily(tenant: str) -> dict[str, Any]:
    """Worker: Drive folders once a day, mail every 30 min when on."""
    out: dict[str, Any] = {}
    with store.db(tenant) as db:
        stale = [r["id"] for r in db.execute("SELECT id, synced FROM watch") if store.now() - (r["synced"] or 0) > 20 * 3600]
        mail_synced = store.get_meta(db, "mail_synced", 0) or 0
    for w in stale:
        out[w] = sync_drive(tenant, w)
    if settings(tenant).get("mail_on") and time.time() - mail_synced > 1800:
        out["mail"] = sync_mail(tenant)
    return out


def tenants_with_gyaan() -> list[str]:
    """Owners who have a Gyaan file (the worker looks only at these). Each file records its owner in meta."""
    import sqlite3
    out: list[str] = []
    for p in sorted(store.root().glob("*.db")):
        try:
            c = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=5)
            r = c.execute("SELECT v FROM meta WHERE k='tenant'").fetchone()
            c.close()
            if r:
                out.append(json.loads(r[0]))
        except sqlite3.Error:
            continue
    return out
