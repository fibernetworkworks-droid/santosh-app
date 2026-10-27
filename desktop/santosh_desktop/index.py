"""Local search index of the shared folders (SQLite FTS5, stays on this PC)."""
from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from . import extract
from .safety import roots

SKIP_DIRS = {"node_modules", ".git", "$recycle.bin", "appdata", "__pycache__", ".venv", "venv", "system volume information",
             ".cache", "temp", "tmp", "windows", "program files", "program files (x86)"}
MAX_FILES = 200_000
MAX_TEXT_BYTES = 15 * 1024 * 1024
EXTRACT_EXT = {".pdf", ".docx", ".xlsx", ".xlsm", ".csv", ".txt", ".md", ".tsv", ".json", ".xml"}


class Index:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, name TEXT, folder TEXT, ext TEXT, size INTEGER,
                                             mtime REAL, kind TEXT, category TEXT, snippet TEXT);
            CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(path UNINDEXED, name, body, tokenize='unicode61 remove_diacritics 2');
        """)
        self.db.commit()
        self.last_run = 0.0

    def count(self) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    def rebuild(self, folders: list[str], extract_text: bool = True) -> int:
        """Incremental: only new or changed files are read again; deleted files are dropped."""
        seen: set[str] = set()
        rs = roots(folders)
        with self.lock:
            known = {p: m for p, m in self.db.execute("SELECT path, mtime FROM files")}
        n = 0
        for root in rs:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if not d.startswith(".") and d.lower() not in SKIP_DIRS]
                for fn in filenames:
                    if fn.startswith(".") or fn.startswith("~$"):
                        continue
                    p = Path(dirpath) / fn
                    try:
                        st = p.stat()
                    except OSError:
                        continue
                    sp = str(p)
                    seen.add(sp)
                    n += 1
                    if n > MAX_FILES:
                        break
                    if known.get(sp) == st.st_mtime:
                        continue
                    text = ""
                    if extract_text and p.suffix.lower() in EXTRACT_EXT and st.st_size <= MAX_TEXT_BYTES:
                        text = extract.text_of(p, 20000)
                    cat = extract.category(fn, text)
                    folder = str(root)
                    with self.lock:
                        self.db.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?,?)",
                                        (sp, fn, folder, p.suffix.lower(), st.st_size, st.st_mtime, extract.kind_of(p),
                                         cat, re.sub(r"\s+", " ", text[:400]).strip()))
                        self.db.execute("DELETE FROM fts WHERE path=?", (sp,))
                        name_words = re.sub(r"[_\-.()\[\]]+", " ", fn)
                        self.db.execute("INSERT INTO fts(path, name, body) VALUES(?,?,?)", (sp, name_words, f"{cat} {text}"))
        with self.lock:
            gone = [p for p in known if p not in seen]
            for p in gone:
                self.db.execute("DELETE FROM files WHERE path=?", (p,))
                self.db.execute("DELETE FROM fts WHERE path=?", (p,))
            self.db.commit()
        self.last_run = time.time()
        return min(n, MAX_FILES)

    def search(self, query: str, kind: str = "any", limit: int = 20, folders: list[str] | None = None) -> list[dict[str, Any]]:
        words = [w for w in re.findall(r"[\wऀ-ॿ]+", query.lower()) if len(w) > 1]
        if not words:
            return []
        allowed = [str(r) for r in roots(folders or [])]
        fts_q = " ".join(f'"{w}"*' for w in words)
        rows: list[tuple] = []
        with self.lock:
            try:
                rows = self.db.execute(
                    "SELECT f.path, f.name, f.folder, f.size, f.mtime, f.kind, f.category, f.snippet, bm25(fts, 4.0, 1.0) AS r "
                    "FROM fts JOIN files f ON f.path = fts.path WHERE fts MATCH ? ORDER BY r LIMIT 200", (fts_q,)).fetchall()
            except sqlite3.OperationalError:
                rows = []
            if len(rows) < 5:  # any-word fallback on names
                like = [f"%{w}%" for w in words]
                cond = " OR ".join("lower(name) LIKE ?" for _ in like)
                extra = self.db.execute(f"SELECT path, name, folder, size, mtime, kind, category, snippet, 0 FROM files "
                                        f"WHERE {cond} ORDER BY mtime DESC LIMIT 100", like).fetchall()
                have = {r[0] for r in rows}
                rows += [r for r in extra if r[0] not in have]
        now = time.time()
        out = []
        for path, name, folder, size, mtime, k, cat, snip, rank in rows:
            if kind and kind != "any" and k != kind:
                continue
            if allowed and not any(path == a or path.startswith(a.rstrip(os.sep) + os.sep) for a in allowed):
                continue
            hits = sum(1 for w in words if w in name.lower())
            age_days = max(0.0, (now - (mtime or now)) / 86400)
            score = -float(rank or 0) + hits * 3 + max(0.0, 3 - age_days / 30)
            out.append((score, {"path": path, "name": name, "folder": folder, "size": size,
                                "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime or 0)),
                                "kind": k, "category": cat, "snippet": snip[:200]}))
        out.sort(key=lambda x: -x[0])
        return [r for _, r in out[:max(1, min(limit, 50))]]
