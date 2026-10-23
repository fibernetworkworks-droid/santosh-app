"""Gyaan storage: ONE SQLite file per owner (data/gyaan/<owner>.db), so isolation is physical, deletion is real and one
owner's data can never be a search hit for another. Tables:

  docs    one row per source item (file, Drive file, email, note, page) - lineage root for "bhool jao"
  chunks  pieces of each doc (text already masked: no Aadhaar / PAN / card / OTP ever reaches here)
  fts     FTS5 BM25 keyword index, unicode61 + Mc/Mn so Hindi / Marathi words stay whole (the default splits matras off)
  tri     FTS5 trigram index over a spelling-forgiving Roman key (Hinglish variants, transliterated Devanagari, partial IDs)
  vecs    int8 vector per chunk + its scale and the model that made it
  ids     exact identifiers (GSTIN, phone, IFSC, invoice / order codes, long numbers) -> chunk, looked up without any model
  ents    v0.135 names of people / firms / places / products found in a chunk (key = spelling-forgiving), so "Gupta ji"
          or "Shree Ganesh Traders" finds every piece that names them, and which names appear together
  watch   Drive folders and web pages she asked to keep in Gyaan
  meta    settings + a version counter (the in-memory vector matrix is rebuilt when it moves)"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA = [
    "CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)",
    "CREATE TABLE IF NOT EXISTS docs(id TEXT PRIMARY KEY, source TEXT, ref TEXT, title TEXT, kind TEXT, sha TEXT, scope TEXT,"
    " at TEXT, added REAL, updated REAL, chunks INT, chars INT, masked TEXT, meta TEXT, UNIQUE(source, ref))",
    "CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id TEXT, ord INT, page INT, text TEXT, prefix TEXT)",
    "CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(doc_id)",
    "CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(body, tokenize=\"unicode61 remove_diacritics 0 categories 'L* N* Co Mc Mn'\")",
    "CREATE TABLE IF NOT EXISTS vecs(chunk_id INTEGER PRIMARY KEY, model TEXT, dim INT, q BLOB, scale REAL)",
    "CREATE TABLE IF NOT EXISTS ids(value TEXT, kind TEXT, chunk_id INT)",
    "CREATE INDEX IF NOT EXISTS ids_value ON ids(value)",
    "CREATE TABLE IF NOT EXISTS ents(key TEXT, name TEXT, kind TEXT, chunk_id INT, doc_id TEXT)",
    "CREATE INDEX IF NOT EXISTS ents_key ON ents(key)",
    "CREATE INDEX IF NOT EXISTS ents_doc ON ents(doc_id)",
    "CREATE TABLE IF NOT EXISTS watch(id TEXT PRIMARY KEY, kind TEXT, ref TEXT, name TEXT, added REAL, synced REAL, files INT, error TEXT)",
]
TRI = "CREATE VIRTUAL TABLE IF NOT EXISTS tri USING fts5(body, tokenize='trigram')"

_LOCKS: dict[str, threading.RLock] = {}
_GLOCK = threading.Lock()
_READY: set[str] = set()
HAS_TRIGRAM = tuple(int(x) for x in sqlite3.sqlite_version.split(".")[:2]) >= (3, 34)


def _lock(tenant: str) -> threading.RLock:
    with _GLOCK:
        return _LOCKS.setdefault(tenant, threading.RLock())


def root() -> Path:
    from ..config import get_settings
    p = Path(get_settings().gyaan_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def path_of(tenant: str) -> Path:
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", tenant or "default")[:40]
    return root() / f"{slug}-{hashlib.sha1((tenant or 'default').encode()).hexdigest()[:8]}.db"


@contextmanager
def db(tenant: str, write: bool = False) -> Iterator[sqlite3.Connection]:
    p = path_of(tenant)
    lk = _lock(tenant)
    if write:
        lk.acquire()
    try:
        key = str(p.resolve())
        existed = p.exists()
        c = sqlite3.connect(str(p), timeout=30)
        c.row_factory = sqlite3.Row
        if key not in _READY or not existed:
            c.execute("PRAGMA journal_mode=WAL")
            for s in SCHEMA:
                c.execute(s)
            if HAS_TRIGRAM:
                c.execute(TRI)
            c.execute("INSERT OR IGNORE INTO meta(k, v) VALUES('tenant', ?)", (json.dumps(tenant),))
            c.commit()
            _READY.add(key)
        try:
            yield c
            if write:
                c.commit()
        finally:
            c.close()
    finally:
        if write:
            lk.release()


def has_tri(c: sqlite3.Connection) -> bool:
    return HAS_TRIGRAM and bool(c.execute("SELECT 1 FROM sqlite_master WHERE name='tri'").fetchone())


def get_meta(c: sqlite3.Connection, k: str, default: Any = None) -> Any:
    r = c.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    if not r:
        return default
    try:
        return json.loads(r[0])
    except ValueError:
        return default


def set_meta(c: sqlite3.Connection, k: str, v: Any) -> None:
    c.execute("INSERT INTO meta(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, json.dumps(v)))


def bump(c: sqlite3.Connection) -> int:
    v = int(get_meta(c, "ver", 0) or 0) + 1
    set_meta(c, "ver", v)
    return v


def version(c: sqlite3.Connection) -> int:
    return int(get_meta(c, "ver", 0) or 0)


def delete_doc(c: sqlite3.Connection, doc_id: str) -> int:
    """Lineage delete: the doc, its chunks, both keyword indexes, vectors and identifiers."""
    ids = [r[0] for r in c.execute("SELECT id FROM chunks WHERE doc_id=?", (doc_id,))]
    if ids:
        qs = ",".join("?" * len(ids))
        c.execute(f"DELETE FROM fts WHERE rowid IN ({qs})", ids)
        if has_tri(c):
            c.execute(f"DELETE FROM tri WHERE rowid IN ({qs})", ids)
        c.execute(f"DELETE FROM vecs WHERE chunk_id IN ({qs})", ids)
        c.execute(f"DELETE FROM ids WHERE chunk_id IN ({qs})", ids)
        c.execute(f"DELETE FROM ents WHERE chunk_id IN ({qs})", ids)
        c.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
    c.execute("DELETE FROM docs WHERE id=?", (doc_id,))
    return len(ids)


def wipe(tenant: str) -> bool:
    """Forget everything: the whole file (and its WAL / SHM) is removed, nothing left to restore from."""
    p = path_of(tenant)
    with _lock(tenant):
        gone = False
        for suf in ("", "-wal", "-shm"):
            q = Path(str(p) + suf)
            if q.exists():
                q.unlink()
                gone = True
        _READY.discard(str(p.resolve()))
    from . import search
    search.drop_cache(tenant)
    return gone


def now() -> float:
    return time.time()
