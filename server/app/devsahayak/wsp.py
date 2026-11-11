"""Hoola Code Phase 4 - the WORKSPACE ENGINE (docs/HOOLA_CODE_WEB_PLAN.md, owner: "GO PHASE 4 WITH 2 LIVE SESSIONS").

What changes. Until now a session was a TASK: the repo was read through the GitHub API, edits lived in memory and the
only thing Hoola could run was her one declared check, on a throwaway clone. Here a session gets a REAL CHECKOUT that
stays for the life of the session, in one locked box (app/devlab: no internet, no keys, non-root, caps on memory /
CPU / pids, a time limit per command). Hoola can run commands in it, the files stay as it left them between her
messages, and the session is a CONVERSATION: her next message continues the same model history instead of starting
a new round from nothing.

What does NOT change, on purpose:
- her GitHub token never enters the box - the clone happens outside it, `.git` is stripped, and every commit still
  goes through the GitHub API from the server (service.push / _round), on a hoola/* branch only;
- the checks on a change (secrets, paths, limits, workflows), her PR tap and her merge tap are the same code;
- the old engine (loop.run) is the fallback whenever the box cannot open.

The budget she set: at most `dev_workspace_live` (2) sessions are LIVE on the whole server at once. A third one
pauses the idle one that was used longest ago (its edits are saved, its box and files are removed and rebuilt on
its next message); when both are busy the new one waits, and says so.

Honest limits of this version: a deleted or renamed file is not sent in a change (the model is told, she is told);
a live checkout has no hard disk quota beyond the clone limit; a command that is running cannot be stopped before
its own time limit."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import logging
import os
import re
import shutil
import threading
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..db import now, session
from . import loop as L
from . import rules as R
from .models import DevRepo, DevTask, DevWorkspace

log = logging.getLogger("santosh.devsahayak.wsp")

ROOT = Path(os.environ.get("HOOLA_DATA", "data")) / "devws"
JUNK = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
        ".gradle", ".next", ".nuxt", ".dart_tool", ".idea", ".cache", "coverage", "htmlcov", "dist", "build", "target"}
MAX_TEXT = 512 * 1024        # a file larger than this is never shown, searched or sent in a change
MAX_FILES = 20000
TERM_KEEP = 80               # terminal entries kept per session
OUT_TAIL = 6000              # characters of one command's output kept for her terminal
HISTORY_BUDGET = 160_000     # characters of conversation sent to the model before older tool output is cleared
KEEP_RESULTS = 14            # ... the newest tool results always kept whole
ON_BRANCH = ("pr_open", "checks_failed", "ci_running")

_LOCK = threading.RLock()


class Unavailable(Exception):
    """The box could not open for this turn (switch off, no docker, clone failed, no free slot). Raised BEFORE any
    model step, so the caller can fall back to the old engine with nothing half-done."""


def _setting(name: str, default: Any) -> Any:
    from ..config import get_settings
    return getattr(get_settings(), name, default)


def _j(v: Any, d: Any) -> Any:
    try:
        return json.loads(v) if v else d
    except (TypeError, ValueError):
        return d


# ---------------------------------------------------------------- the box, behind one object (tests swap it)
class DockerBox:
    """Everything the engine asks of the machine. One object so a test can stand in a local folder for Docker and
    exercise every line of the engine above it."""

    def available(self) -> dict[str, Any]:
        from ..devlab import box
        return box.available()

    def fetch(self, repo: str, ref: str, token: str) -> dict[str, Any]:
        from ..devlab import service as LS
        return LS.materialize(repo, ref, token)

    def spec(self, work: str, paths: list[str], hers: dict[str, str] | None) -> dict[str, Any]:
        from ..devlab import service as LS
        return LS.spec_for(work, paths, hers)

    def image(self, repo: str, work: str, setup: str, key: str) -> dict[str, Any]:
        from ..devlab import service as LS
        return LS.snapshot(repo, work, setup, key)

    def base_image(self) -> str:
        from ..devlab import box
        return box.BASE_IMAGE

    def start(self, name: str, image: str, work: str) -> dict[str, Any]:
        from ..devlab import box
        return box.start_live(name, image, work, mem=str(_setting("dev_workspace_mem", "") or ""))

    def alive(self, name: str) -> bool:
        from ..devlab import box
        return box.live_alive(name)

    def run(self, name: str, command: str, timeout: int, env: dict[str, str] | None = None) -> dict[str, Any]:
        from ..devlab import box
        return box.exec_live(name, command, timeout, env)

    def bg_start(self, name: str, slot: str, command: str, limit: int, env: dict[str, str] | None = None) -> dict[str, Any]:
        from ..devlab import box
        return box.bg_start(name, slot, command, limit, env)

    def bg_read(self, name: str, slot: str) -> dict[str, Any]:
        from ..devlab import box
        return box.bg_read(name, slot)

    def bg_stop(self, name: str, slot: str) -> bool:
        from ..devlab import box
        return box.bg_stop(name, slot)

    def stop(self, name: str, work: str = "") -> bool:
        from ..devlab import box
        return box.stop_live(name, work)

    def names(self) -> list[str]:
        from ..devlab import box
        return box.live_boxes()

    def name_for(self, tid: str) -> str:
        from ..devlab import box
        return box.live_name(tid)


BOX: Any = DockerBox()


def ready(tenant: str = "") -> dict[str, Any]:
    """May a turn use the workspace engine right now? Two doors, named separately: the switch and the machine."""
    if not bool(_setting("dev_workspace", False)):
        return {"ok": False, "why": "off", "say": "The workspace engine is switched off on this server."}
    try:
        av = BOX.available()
    except Exception as e:  # noqa: BLE001 - a broken docker client must read as 'not available', never as a crash
        return {"ok": False, "why": "box", "say": f"The box is not available: {e.__class__.__name__}"}
    return {"ok": bool(av.get("ok")), "why": "" if av.get("ok") else "box", "say": str(av.get("why") or "")}


# ---------------------------------------------------------------- where a session's files live
def _safe(tid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", str(tid or ""))[:60] or "x"


def _dir(tid: str) -> Path:
    return Path(ROOT) / _safe(tid)


def _work(tid: str) -> Path:
    return _dir(tid) / "work"


def _meta(tid: str) -> Path:
    p = _dir(tid) / "meta"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _save_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), "utf-8")
    os.replace(tmp, path)


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return default


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _walk(work: Path):
    """Every regular file under the checkout, as a repo path. Symlinks are never followed and never listed as files:
    code in the box can create one that points anywhere on the server, and the server must not read through it."""
    n = 0
    base = str(work)
    for root, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in JUNK and not os.path.islink(os.path.join(root, d)))
        for f in sorted(files):
            full = os.path.join(root, f)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            yield os.path.relpath(full, base).replace(os.sep, "/")
            n += 1
            if n >= MAX_FILES:
                return


def build_manifest(work: Path) -> dict[str, list]:
    """What the checkout looked like at its base commit: path -> [sha1, size, mtime_ns]. Everything 'changed' is
    measured against this, so a formatter or a code generator that a command ran is seen exactly like an edit."""
    out: dict[str, list] = {}
    for rel in _walk(work):
        p = work / rel
        try:
            st = p.stat()
            out[rel] = [_sha1(p), st.st_size, st.st_mtime_ns]
        except OSError:
            continue
    return out


def ignore_fn(work: Path):
    """The repo's own root .gitignore, read simply (no negations). A file a command creates that the repo ignores -
    a build folder, a cache, a log - is not part of the change."""
    pats: list[tuple[str, bool, bool]] = []
    try:
        gi = work / ".gitignore"
        if gi.is_file() and not gi.is_symlink() and gi.stat().st_size < 64 * 1024:
            for raw in gi.read_text("utf-8", errors="replace").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                dir_only = line.endswith("/")
                core = line.strip("/")
                if core:
                    pats.append((core, dir_only, line.startswith("/") or "/" in core))
    except OSError:
        pass

    def ignored(rel: str) -> bool:
        segs = rel.split("/")
        if any(s in JUNK for s in segs[:-1]) or segs[-1].endswith((".pyc", ".pyo", ".log", ".DS_Store")):
            return True
        for core, dir_only, anchored in pats:
            if anchored:
                if fnmatch.fnmatch(rel, core + "/*") or (not dir_only and fnmatch.fnmatch(rel, core)) \
                        or rel.startswith(core + "/"):
                    return True
            else:
                parts = segs[:-1] if dir_only else segs
                if any(fnmatch.fnmatch(s, core) for s in parts):
                    return True
        return False
    return ignored


def scan_dir(work: Path, manifest: dict[str, list], ignored) -> dict[str, list[str]]:
    """The checkout against its base: modified (a tracked file whose content differs), created (a new file the repo
    does not ignore), deleted (a tracked file that is gone), skipped (new but binary / too large to send)."""
    seen: set[str] = set()
    modified, created, skipped = [], [], []
    for rel in _walk(work):
        seen.add(rel)
        p = work / rel
        try:
            st = p.stat()
        except OSError:
            continue
        m = manifest.get(rel)
        if m is not None:
            if st.st_size == m[1] and st.st_mtime_ns == m[2]:
                continue
            if _sha1(p) == m[0]:
                m[1], m[2] = st.st_size, st.st_mtime_ns        # touched, not changed: remember the new stamp
                continue
            modified.append(rel)
        elif not ignored(rel):
            if st.st_size > MAX_TEXT or R.BINARY_EXT.search(rel):
                skipped.append(rel)
            else:
                created.append(rel)
    deleted = sorted(p for p in manifest if p not in seen and not any(s in JUNK for s in p.split("/")[:-1]))
    return {"modified": sorted(modified), "created": sorted(created), "deleted": deleted, "skipped": sorted(skipped)}


def scrub(text: str) -> str:
    """Output of a command is shown to the model and to her: a line that looks like a key or a password is hidden."""
    try:
        hits = R.secrets_in(text or "")
    except Exception:  # noqa: BLE001
        hits = []
    if not hits:
        return text or ""
    lines = (text or "").splitlines()
    for h in hits:
        i = int(h.get("line") or 0) - 1
        if 0 <= i < len(lines):
            lines[i] = f"[line hidden: it looks like a {h.get('kind') or 'secret'}]"
    return "\n".join(lines)


# ---------------------------------------------------------------- the eight tools, on the real files
class DiskWorkspace(L.Workspace):
    """loop.Workspace with the same tools and the same refusals, but the truth is the checkout on disk - so a command
    sees every edit at once and every file a command changes is seen as part of the change."""

    def __init__(self, g, repo: str, base_sha: str, root: Path, manifest: dict[str, list], allow_workflows: bool = False):
        super().__init__(g, repo, base_sha, sorted(manifest), allow_workflows)
        self.root = Path(root)
        self.manifest = manifest
        self.ignored = ignore_fn(self.root)
        self.hidden: set[str] = set()

    # -- `current` is what loop.Workspace keeps in memory; here it is read off the disk whenever it is asked for
    @property
    def current(self) -> dict[str, str]:
        return {p: self._text(p) for p in self.changed()}

    @current.setter
    def current(self, _v: Any) -> None:
        return

    # ------------------------------------------------------------ paths and reads
    def _abs(self, path: str) -> Path | None:
        from ..devlab.service import safe_rel
        rel = safe_rel(path)
        if not rel:
            return None
        p = self.root / rel
        root = os.path.realpath(self.root)
        parent = os.path.realpath(p.parent)
        if p.is_symlink() or not (parent == root or parent.startswith(root + os.sep)):
            return None
        return p

    def _exists(self, path: str) -> bool:
        p = self._abs(path)
        return bool(p and p.is_file())

    def _disk(self, path: str) -> str | None:
        p = self._abs(path)
        if p is None or not p.is_file():
            return None
        try:
            if p.stat().st_size > MAX_TEXT:
                return None
            return p.read_text("utf-8", errors="replace")
        except OSError:
            return None

    def _hide(self, path: str, text: str | None) -> str:
        if R.SECRET_FILES.search(path) or R.BINARY_EXT.search(path):
            return "secret / binary file: not shown"
        if text and R.secrets_in(text):
            return "this file holds a key / secret: not shown, not changed"
        return ""

    def _load(self, path: str) -> dict[str, str]:
        """The file as it was at the base commit. While the file on disk is untouched that IS the disk; once it has
        changed, the original comes from GitHub at the base commit (the only time a turn asks GitHub for a file)."""
        if path in self.orig:
            return self.orig[path]
        m = self.manifest.get(path)
        if m is None:
            self.orig[path] = {"text": "", "sha": "", "hidden": ""}
            return self.orig[path]
        p = self._abs(path)
        same = False
        if p is not None and p.is_file():
            try:
                st = p.stat()
                same = (st.st_size == m[1] and st.st_mtime_ns == m[2]) or _sha1(p) == m[0]
            except OSError:
                same = False
        if same:
            text = self._disk(path)
            hidden = self._hide(path, text) or ("" if text is not None else "file too large to show")
            self.orig[path] = {"text": "" if hidden else (text or ""), "sha": m[0], "hidden": hidden}
        else:
            if R.SECRET_FILES.search(path) or R.BINARY_EXT.search(path):
                self.orig[path] = {"text": "", "sha": m[0], "hidden": "secret / binary file: not shown"}
            else:
                text, sha = self.g.file(self.repo, path, self.base)
                hidden = "this file holds a key / secret: not shown, not changed" if text and R.secrets_in(text) else ""
                self.orig[path] = {"text": "" if hidden else text, "sha": sha or m[0], "hidden": hidden}
        if self.orig[path].get("hidden"):
            self.hidden.add(path)
        return self.orig[path]

    def _text(self, path: str) -> str:
        return self._disk(path) or ""

    def _resolve(self, path: str) -> str:
        p = str(path or "").strip().removeprefix("./").lstrip("/")
        if p and self._exists(p):
            return p
        m = R.match_path(self.paths, p) if p else ""
        return m or p

    def _write(self, path: str, text: str) -> str:
        p = self._abs(path)
        if p is None:
            return "that path cannot be written (outside the repo, or a link)"
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.parent.is_symlink():
                return "that folder is a link"
            p.write_text(text, "utf-8")
            os.chmod(p, 0o666)
            for d in p.parents:
                if d == self.root or self.root not in d.parents:
                    break
                try:
                    os.chmod(d, 0o777)
                except OSError:
                    pass
        except OSError as e:
            return f"could not write: {e.__class__.__name__}"
        return ""

    # ------------------------------------------------------------ the tools
    def list_dir(self, path: str = "") -> str:
        base = str(path or "").strip().strip("/")
        d = self.root if not base else self._abs(base)
        if d is None or not Path(d).is_dir() or (base and Path(d).is_symlink()):
            return f"No folder '{base}' (or it is empty)."
        entries = []
        try:
            for e in sorted(os.scandir(d), key=lambda x: x.name):
                if e.name == ".git" or e.is_symlink():
                    continue
                entries.append(e.name + "/" if e.is_dir(follow_symlinks=False) else e.name)
        except OSError:
            return f"No folder '{base}' (or it is empty)."
        entries = sorted(x for x in entries if x.endswith("/")) + sorted(x for x in entries if not x.endswith("/"))
        if not entries:
            return f"No folder '{base}' (or it is empty)."
        self.trail.append(f"folder dekha: {base or '/'}")
        more = f"\n… {len(entries) - L.LIST_MAX} more" if len(entries) > L.LIST_MAX else ""
        body = "\n".join(entries[:L.LIST_MAX]) + more
        return self._with_rules(base + "/x", body) if base else body

    def _grep(self, pat: re.Pattern, cap_files: int, cap_lines: int) -> list[tuple[str, int, str]]:
        out: list[tuple[str, int, str]] = []
        files = 0
        for rel in _walk(self.root):
            if R.BINARY_EXT.search(rel) or R.SECRET_FILES.search(rel):
                continue
            text = self._disk(rel)
            if not text or not pat.search(text):
                continue
            files += 1
            for i, line in enumerate(text.splitlines(), 1):
                if pat.search(line):
                    out.append((rel, i, line.strip()[:200]))
                    if len(out) >= cap_lines:
                        return out
            if files >= cap_files:
                break
        return out

    def search_code(self, words: str) -> str:
        w = [x for x in re.split(r"\s+", str(words or "").strip()) if x][:3]
        if not w:
            return "Give 1-3 words or a name to search for."
        self.searched.append(" ".join(w))
        pat = re.compile("|".join(re.escape(x) for x in w), re.I)
        hits: dict[str, tuple[int, str]] = {}
        for rel, i, line in self._grep(pat, 40, 400):
            hits.setdefault(rel, (i, line))
        low = [x.lower() for x in w]
        names = [p for p in _walk(self.root) if any(x in p.lower() for x in low) and p not in hits][:20]
        self.trail.append(f"dhoondha: {' '.join(w)} ({len(hits) + len(names)} files)")
        if not hits and not names:
            return "No file found. Try other words, or list_dir."
        rows = [f"{p}:{i}: {line}" for p, (i, line) in list(hits.items())[:30]] + names[:max(0, 30 - len(hits))]
        return "\n".join(rows)

    def read_file(self, path: str, start: int = 0, end: int = 0) -> str:
        p = self._resolve(path)
        if not self._exists(p):
            return f"No file '{path}' in the repo. Use list_dir or search_code."
        text = self._disk(p)
        hidden = self._hide(p, text) or ("" if text is not None else "file too large to show")
        if hidden:
            self.hidden.add(p)
            return f"{p}: {hidden}."
        self._load(p)                                   # remember the original before anything changes it
        self.read.add(p)
        self.trail.append(f"padha: {p}")
        return self._with_rules(p, f"{p}\n" + L._numbered(text or "", int(start or 0), int(end or 0)))

    def find_usages(self, name: str) -> str:
        n = str(name or "").strip()
        if not n or len(n) < 2:
            return "Give the function / class / variable name."
        pat = re.compile(r"(?<![\w])" + re.escape(n) + r"(?![\w])")
        rows = self._grep(pat, 60, L.USAGE_LINES)
        self.trail.append(f"'{n}' kahan use hota hai dekha ({len(rows)} jagah)")
        return "\n".join(f"{p}:{i}: {line}" for p, i, line in rows) if rows else f"No usage of '{n}' found."

    def edit_file(self, path: str, old: str, new: str) -> str:
        p = self._resolve(path)
        if p not in self.read:
            L.STATS["refused_edits"] += 1
            return f"Refused: read_file {p} first - never change code you have not read."
        if self._rules_for(p):
            L.STATS["refused_edits"] += 1
            return ("Not applied yet: read this folder's rules first, then make the edit again following them.\n"
                    + self._show_rules(self._rules_for(p)))
        why = R.path_problem(p, self.allow_workflows)
        if why or p in self.hidden:
            L.STATS["refused_edits"] += 1
            return f"Refused: {p}: {why or 'this file is not shown and not changed'}"
        old_s = str(old or "")
        if not old_s:
            return "Refused: old is empty. Copy the exact text to replace."
        text = self._text(p)
        n = text.count(old_s)
        if n != 1:
            L.STATS["refused_edits"] += 1
            return (f"Refused: that text appears {n} times in {p} (must be exactly once). "
                    + ("read_file it again and copy the text exactly." if n == 0 else "Add more surrounding lines."))
        bad = self._write(p, text.replace(old_s, str(new or ""), 1))
        if bad:
            return f"Refused: {p}: {bad}"
        L.STATS["edits"] += 1
        self.trail.append(f"badla: {p}")
        return f"Edited {p}."

    def new_file(self, path: str, content: str) -> str:
        p = str(path or "").strip().removeprefix("./").lstrip("/")
        if not p:
            return "Give a path."
        if self._exists(p):
            return f"{p} already exists: read_file it, then edit_file."
        if self._rules_for(p):
            L.STATS["refused_edits"] += 1
            return ("Not created yet: read this folder's rules first, then create the file again following them.\n"
                    + self._show_rules(self._rules_for(p)))
        why = R.path_problem(p, self.allow_workflows)
        if why:
            L.STATS["refused_edits"] += 1
            return f"Refused: {p}: {why}"
        bad = self._write(p, str(content or ""))
        if bad:
            return f"Refused: {p}: {bad}"
        self.created.add(p)
        self.read.add(p)
        self.trail.append(f"nayi file: {p}")
        return f"Created {p}."

    def show_diff(self) -> str:
        sc = self.scan()
        changed = sc["modified"] + sc["created"]
        if not changed and not sc["deleted"]:
            return "Nothing changed yet."
        parts = [R.unified(p, self._load(p)["text"], self._text(p))[:12000] for p in changed if p not in self.hidden]
        if sc["deleted"]:
            parts.append("Deleted on disk (a deletion is NOT sent in a change yet - say so in risk): "
                         + ", ".join(sc["deleted"][:20]))
        if sc["skipped"]:
            parts.append("New but not part of the change (binary / too large): " + ", ".join(sc["skipped"][:20]))
        self.trail.append(f"apna badlav jaancha ({len(changed)} files)")
        return "\n".join(parts)[:40000]

    # ------------------------------------------------------------ results
    def scan(self) -> dict[str, list[str]]:
        return scan_dir(self.root, self.manifest, self.ignored)

    def changed(self) -> list[str]:
        sc = self.scan()
        return [p for p in sc["modified"] + sc["created"] if p not in self.hidden and not R.SECRET_FILES.search(p)]


# ---------------------------------------------------------------- her terminal (output only)
def term_add(tid: str, entry: dict[str, Any]) -> dict[str, Any]:
    path = _meta(tid) / "term.json"
    with _LOCK:
        rows = _load_json(path, [])
        entry = {**entry, "n": (rows[-1]["n"] + 1) if rows else 1, "at": now().isoformat()}
        rows.append(entry)
        _save_json(path, rows[-TERM_KEEP:])
    return entry


def term_set(tid: str, n: int, **kw: Any) -> None:
    path = _meta(tid) / "term.json"
    with _LOCK:
        rows = _load_json(path, [])
        for r in rows:
            if r.get("n") == n:
                r.update(kw)
        _save_json(path, rows)


def terminal(tid: str, after: int = 0) -> list[dict[str, Any]]:
    return [r for r in _load_json(_dir(tid) / "meta" / "term.json", []) if int(r.get("n") or 0) > int(after or 0)]


# ---------------------------------------------------------------- live / paused / closed
def _row(s, tid: str) -> DevWorkspace | None:
    return s.get(DevWorkspace, tid)


def live_now() -> list[dict[str, Any]]:
    with session() as s:
        return [{"id": w.id, "busy": bool(w.busy), "tenant": w.tenant_id}
                for w in s.scalars(select(DevWorkspace).where(DevWorkspace.state == "live")).all()]


def cap() -> int:
    return max(1, int(_setting("dev_workspace_live", 2) or 2))


def overlay(tid: str) -> dict[str, Any]:
    """Everything this session changed, as text: what a pause saves and what a snapshot keeps."""
    work = _work(tid)
    manifest = _load_json(_meta(tid) / "base.json", {})
    sc = scan_dir(work, manifest, ignore_fn(work))
    files: dict[str, str] = {}
    for rel in sc["modified"] + sc["created"]:
        p = work / rel
        try:
            if p.is_symlink() or p.stat().st_size > MAX_TEXT:
                continue
            files[rel] = p.read_text("utf-8", errors="replace")
        except OSError:
            continue
    _save_json(_meta(tid) / "base.json", manifest)
    return {"files": files, "deleted": sc["deleted"]}


def pause(tid: str, why: str = "") -> bool:
    """Save the session's edits, then remove its box and its files. Its next message rebuilds both."""
    with _LOCK:
        with session() as s:
            w = _row(s, tid)
            if w is None or w.state != "live" or w.busy:
                return False
            base = w.base_sha
        work = _work(tid)
        if work.exists():
            saved = overlay(tid)
            saved["base_sha"] = base
            _save_json(_meta(tid) / "saved.json", saved)
        try:
            BOX.stop(BOX.name_for(tid), str(work))
        except Exception:  # noqa: BLE001
            log.info("workspace %s: box stop failed", tid, exc_info=True)
        shutil.rmtree(work, ignore_errors=True)
        with session() as s:
            w = _row(s, tid)
            if w is not None:
                w.state = "paused"
        log.info("workspace %s paused (%s)", tid, why or "idle")
        return True


def close(tid: str) -> None:
    """The session is over (deleted, merged, closed): the box and every file of it go."""
    with _LOCK:
        try:
            BOX.stop(BOX.name_for(tid), str(_work(tid)))
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(_dir(tid), ignore_errors=True)
        with session() as s:
            w = _row(s, tid)
            if w is not None:
                w.state, w.busy, w.todo, w.ask = "closed", False, None, None


def _claim(tid: str, tenant: str, repo: str) -> tuple[bool, str]:
    """Take one of the live places for this session, pausing the idle session that was used longest ago if that is
    what it takes. False = every place is busy working right now."""
    with _LOCK:
        with session() as s:
            others = [w for w in s.scalars(select(DevWorkspace).where(DevWorkspace.state.in_(("live", "opening")))).all()
                      if w.id != tid]
            room = len(others) < cap()
            victim = ""
            if not room:
                idle = sorted((w for w in others if not w.busy and w.state == "live"), key=lambda w: w.used_at or w.created_at)
                victim = idle[0].id if idle else ""
        if not room and victim:
            room = pause(victim, "made room for another session")
        if not room:
            return False, f"{cap()} sessions are working in their boxes right now"
        with session() as s:
            w = _row(s, tid)
            if w is None:
                w = DevWorkspace(id=tid, tenant_id=tenant, repo=repo)
                s.add(w)
            if w.state != "live":
                w.state = "live" if _work(tid).exists() else "opening"
            w.busy, w.used_at = True, now()
        return True, ""


def _release(tid: str) -> None:
    with session() as s:
        w = _row(s, tid)
        if w is not None:
            w.busy, w.used_at = False, now()
            if w.state == "opening":
                w.state = "paused" if (_meta(tid) / "saved.json").exists() else ""


def _repo_hers(tenant: str, repo: str) -> tuple[dict[str, str], dict[str, str]]:
    with session() as s:
        r = s.scalars(select(DevRepo).where(DevRepo.tenant_id == tenant, DevRepo.full_name == repo)).first()
        if r is None:
            return {}, {}
        hers = {k: v for k, v in (("setup", r.setup_cmd or ""), ("test", r.test_cmd or "")) if v.strip()}
        env = {str(k): str(v) for k, v in (_j(r.env_vars or "", {}) or {}).items()}
        return hers, env


def _open_up(work: Path) -> None:
    """The clone belongs to the server's user and the box runs as uid 1000: a formatter or a code generator in the box
    must be able to change her files, so the whole checkout is opened for it (it is a private copy, never her repo)."""
    for root, dirs, files in os.walk(str(work), followlinks=False):
        for name in [""] + dirs:
            try:
                os.chmod(os.path.join(root, name) if name else root, 0o777)
            except OSError:
                pass
        for name in files:
            full = os.path.join(root, name)
            try:
                if not os.path.islink(full):
                    os.chmod(full, os.stat(full).st_mode | 0o666)
            except OSError:
                pass


def _apply_overlay(work: Path, saved: dict[str, Any]) -> None:
    from ..devlab.service import write_overlay
    write_overlay(str(work), saved.get("files") or {})
    for rel in saved.get("deleted") or []:
        p = work / rel
        try:
            if p.is_file() and not p.is_symlink():
                p.unlink()
        except OSError:
            pass


def _open(tid: str, tenant: str, t: Any, g: Any, token: str, emit, allow_workflows: bool) -> tuple[DiskWorkspace, dict[str, Any]]:
    """Make this session's checkout and box real: a fresh clone for a new session, a rebuild (clone + her saved edits)
    for a paused one, nothing at all for one that is already live. Returns the workspace and what the box knows
    about the repo (its check command, whether setup worked)."""
    work = _work(tid)
    meta = _meta(tid)
    with session() as s:
        w = _row(s, tid)
        base, image, spec = w.base_sha, w.image, _j(w.spec or "", {})
    hers, env = _repo_hers(tenant, t.repo)
    note = ""
    if not work.exists():
        if not base:
            base = (t.head_sha if t.status in ON_BRANCH and t.head_sha else "") or g.branch_sha(t.repo, t.base)
            if not base:
                raise Unavailable(f"branch {t.base} was not found")
        emit({"k": "box", "state": "clone", "text": "Getting the repo into the box"})
        m = BOX.fetch(t.repo, base, token)
        if not m.get("ok"):
            raise Unavailable("the repo could not be brought into the box: " + str(m.get("why") or "")[:300])
        work.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(m["dir"], str(work))
        _open_up(work)
        manifest = build_manifest(work)
        _save_json(meta / "base.json", manifest)
        spec = BOX.spec(str(work), sorted(manifest), hers)
        saved = _load_json(meta / "saved.json", None)
        if saved and saved.get("base_sha") == base:
            _apply_overlay(work, saved)
        try:
            (meta / "saved.json").unlink()
        except OSError:
            pass
        image = ""
    else:
        manifest = _load_json(meta / "base.json", {})
    name = BOX.name_for(tid)
    if not image:
        emit({"k": "box", "state": "setup", "text": "Installing the repo's dependencies (first time for this repo takes a few minutes)"})
        setup = str(spec.get("setup") or "")
        key = str(spec.get("deps_key") or "nodeps") + ("-" + _hash_text(setup)[:6] if hers.get("setup") else "")
        snap = BOX.image(t.repo, str(work), setup, key)
        if snap.get("ok"):
            image = snap["image"]
        else:
            image = BOX.base_image()
            note = ("The repo's dependency install did not finish, so commands that need its packages will fail: "
                    + str(snap.get("why") or "")[:200])
            term_add(tid, {"kind": "setup", "cmd": setup or "(no setup command)", "rc": 1, "ok": False,
                           "seconds": snap.get("seconds"), "out": scrub(str(snap.get("out") or ""))[-OUT_TAIL:]})
    if not BOX.alive(name):
        st = BOX.start(name, image, str(work))
        if not st.get("ok"):
            raise Unavailable(str(st.get("why") or "the box did not start"))
    with session() as s:
        w = _row(s, tid)
        w.state, w.base_sha, w.image, w.repo = "live", base, image, t.repo
        w.spec = json.dumps({k: spec.get(k) for k in ("setup", "test", "source", "confirm", "lang", "why", "deps_key", "timeout")})
    emit({"k": "box", "state": "live", "text": "The box is ready"})
    dw = DiskWorkspace(g, t.repo, base, work, manifest, allow_workflows)
    seen = _load_json(meta / "seen.json", {})           # a conversation: what it read in an earlier turn is still read
    dw.read |= {p for p in seen.get("read") or [] if dw._exists(p)}
    dw.rules_shown += [r for r in seen.get("rules") or [] if r not in dw.rules_shown]
    return dw, {"spec": spec, "env": env, "note": note, "name": name}


def _sync(tid: str, t: Any, dw: DiskWorkspace) -> None:
    """After a commit reached her PR branch the comparison point moves to that commit. Files the commit carried are
    fast-forwarded on disk when this session had not touched them since (a CI fix made by the old engine, say); a file
    this session edited further stays as it is and shows up as a change again."""
    head = str(getattr(t, "head_sha", "") or "")
    if t.status not in ON_BRANCH or not head or head == dw.base:
        return
    for c in _j(getattr(t, "changes", "") or "", []):
        path, new = str(c.get("path") or ""), c.get("new")
        if not path or not isinstance(new, str):
            continue
        p = dw._abs(path)
        if p is None:
            continue
        m = dw.manifest.get(path)
        want = _hash_text(new)
        try:
            have = _sha1(p) if p.is_file() else ""
        except OSError:
            have = ""
        if have != want and (have == (m[0] if m else "")):
            dw._write(path, new)                                   # untouched here: bring it up to the pushed commit
            have = want
        try:
            st = p.stat()
            dw.manifest[path] = [want, st.st_size if have == want else -1, st.st_mtime_ns if have == want else -1]
        except OSError:
            dw.manifest[path] = [want, -1, -1]
    dw.base = head
    dw.orig.clear()
    dw.paths = sorted(dw.manifest)
    dw.pathset = set(dw.paths)
    _save_json(_meta(tid) / "base.json", dw.manifest)
    with session() as s:
        w = _row(s, tid)
        if w is not None:
            w.base_sha = head


# ---------------------------------------------------------------- snapshots (rewind) and the conversation
def _history(tid: str) -> dict[str, Any]:
    return _load_json(_meta(tid) / "history.json", {"messages": []})


def _save_history(tid: str, messages: list[dict], name: str = "history.json") -> None:
    """Saved after every step, so a server restart continues from the last finished step. Pictures are not kept."""
    slim = []
    for m in messages:
        c = m.get("content")
        if isinstance(c, list):
            c = [({"type": "text", "text": "[a picture she attached]"} if isinstance(b, dict) and b.get("type") == "image" else b)
                 for b in c]
        slim.append({"role": m.get("role"), "content": c})
    _save_json(_meta(tid) / name, {"messages": slim})


def trim(messages: list[dict]) -> list[dict]:
    """A long session must not carry every old file read for ever (Anthropic clears old tool results the same way):
    past the budget, the output of older tool calls is replaced by one line. The newest ones stay whole, and so does
    everything she and Hoola SAID - only bulk output goes, and the model can run the tool again."""
    if len(json.dumps(messages, ensure_ascii=False)) <= HISTORY_BUDGET:
        return messages
    spots = [(i, j) for i, m in enumerate(messages) if isinstance(m.get("content"), list)
             for j, b in enumerate(m["content"]) if isinstance(b, dict) and b.get("type") == "tool_result"]
    for i, j in spots[:-KEEP_RESULTS]:
        b = messages[i]["content"][j]
        if len(str(b.get("content") or "")) > 400:
            messages[i]["content"][j] = {**b, "content": "[older output cleared to save room - run the tool again if you need it]"}
    return messages


def _append_user(messages: list[dict], text: str, pics: list[dict] | None = None) -> None:
    blocks = [{"type": "text", "text": text}] + list(pics or [])
    if messages and messages[-1].get("role") == "user":
        c = messages[-1].get("content")
        messages[-1]["content"] = (c if isinstance(c, list) else [{"type": "text", "text": str(c or "")}]) + blocks
    else:
        messages.append({"role": "user", "content": blocks if pics else text})


def _said(messages: list[dict], text: str) -> bool:
    """Is this message of hers already in the conversation? (A restart can cut a turn before or after it was saved.)"""
    key = (text or "").strip()[:120]
    if not key:
        return True
    for m in messages[-6:]:
        if m.get("role") != "user":
            continue
        c = m.get("content")
        body = c if isinstance(c, str) else " ".join(str(b.get("text") or "") for b in c if isinstance(b, dict))
        if key in body:
            return True
    return False


def _snapshot(tid: str, text: str, messages: list[dict]) -> int:
    """The files as they are BEFORE Hoola acts on this message of hers - what 'rewind to here' brings back."""
    with session() as s:
        w = _row(s, tid)
        n = int(w.msgs or 0) + 1
        base = w.base_sha
    snap = overlay(tid) if _work(tid).exists() else {"files": {}, "deleted": []}
    snap.update({"base_sha": base})
    _save_json(_meta(tid) / f"snap-{n}.json", snap)
    _save_history(tid, messages, f"hist-{n}.json")
    with session() as s:
        w = _row(s, tid)
        rows = _j(w.snaps or "", [])
        rows.append({"n": n, "at": now().isoformat(), "text": text[:160], "files": len(snap["files"]), "base": base[:12]})
        w.snaps, w.msgs = json.dumps(rows[-30:]), n
    return n


def rewind(tenant: str, tid: str, n: int, g: Any, token: str) -> dict[str, Any]:
    """Put the files (and the conversation) back to where they were before her message `n`. Only what is still in the
    box can go back: a commit already on her PR stays on her PR."""
    with session() as s:
        w = _row(s, tid)
        t = s.get(DevTask, tid)
        if w is None or t is None or t.tenant_id != tenant:
            raise ValueError("This session has no checkout.")
        if w.busy:
            raise ValueError("Hoola is working in this session - stop it first.")
        snaps = _j(w.snaps or "", [])
        base = w.base_sha
        s.expunge(t)
    snap = _load_json(_meta(tid) / f"snap-{int(n)}.json", None)
    if snap is None or not any(x["n"] == int(n) for x in snaps):
        raise ValueError("That point is not kept any more.")
    if snap.get("base_sha") != base:
        raise ValueError("A commit went to your pull request after that message. What is on the pull request cannot "
                         "be rewound here - ask for the change instead.")
    ok, why = _claim(tid, tenant, t.repo)
    if not ok:
        raise ValueError(why + " - try again in a minute.")
    try:
        dw, _ = _open(tid, tenant, t, g, token, lambda ev: None, False)
        sc = dw.scan()
        want: dict[str, str] = snap.get("files") or {}
        gone = set(snap.get("deleted") or [])
        for path in set(sc["modified"]) | set(sc["created"]) | set(sc["deleted"]) | set(want) | gone:
            p = dw._abs(path)
            if p is None:
                continue
            if path in want:
                dw._write(path, want[path])
            elif path in gone or path not in dw.manifest:
                try:
                    if p.is_file():
                        p.unlink()
                except OSError:
                    pass
            else:
                text, _sha = g.file(t.repo, path, base)            # back to the base commit's own text
                dw._write(path, text)
        _save_history(tid, _load_json(_meta(tid) / f"hist-{int(n)}.json", {}).get("messages") or [])
        with session() as s:
            w = _row(s, tid)
            w.snaps = json.dumps([x for x in snaps if x["n"] < int(n)])
            w.msgs, w.ask = int(n) - 1, None
        text = next((x.get("text", "") for x in snaps if x["n"] == int(n)), "")
        return {"ok": True, "n": int(n), "text": text, "files": len(dw.changed())}
    finally:
        _release(tid)


# ---------------------------------------------------------------- the tools only a real box can give
BOX_TOOLS: list[dict[str, Any]] = [
    {"name": "run_command", "description": "Run ONE shell command in the repo root, inside the session's locked box, and "
     "get its real output and exit code. Use it to run a test, a linter, a build, a script, or to look at files with "
     "grep / ls / cat. The box has no internet and no keys; there is no git in it. Output is cut for you (a failure keeps "
     "its END). background=true starts something that must keep running (a dev server, a watcher) and returns at once - "
     "read it later with command_output.",
     "input_schema": {"type": "object", "properties": {
         "command": {"type": "string", "description": "one line of shell"},
         "why": {"type": "string", "description": "one short line: what this is for (she sees it)"},
         "background": {"type": "boolean"},
         "timeout": {"type": "integer", "description": "seconds (optional, the server caps it)"}},
         "required": ["command"]}},
    {"name": "command_output", "description": "The latest output of a background command you started, and whether it "
     "is still running. stop=true ends it.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}, "stop": {"type": "boolean"}},
                      "required": ["id"]}},
    {"name": "todo", "description": "Your own short list of steps for this job. Send the WHOLE list every time, each "
     "item with a state. Use it for any job with three or more steps, and update it as you go - she watches it.",
     "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
         "text": {"type": "string"}, "state": {"type": "string", "enum": ["pending", "doing", "done"]}},
         "required": ["text", "state"]}}}, "required": ["items"]}},
    {"name": "ask_her", "description": "Ask the owner ONE question when you truly cannot go on without her: her words "
     "have two readings, or the choice is hers to make. Give 2-4 short choices. It ENDS your turn; her answer comes back "
     "in this same conversation with your work still in place. Never ask what the code or a command can tell you.",
     "input_schema": {"type": "object", "properties": {
         "question": {"type": "string"},
         "choices": {"type": "array", "items": {"type": "string"}, "description": "2-4 short answers she can tap"}},
         "required": ["question"]}},
]

BOX_BLOCK = """YOU HAVE A REAL CHECKOUT (this session's box).
The repo's files are on disk in a locked box: no internet, no keys, a time limit on every command ({cmd_s}s; a
background command {bg_m} min).
- run_command runs shell in the repo root: tests, a linter, a build, a script. Commands see your edits at once.
- The files stay exactly as you leave them between her messages. A file a command creates or changes is part of your
  change (show_diff shows it): delete output that should not go into the pull request. Deleting or renaming one of HER
  files is not sent in a change yet - if the work needs that, say so in risk.
- Packages cannot be installed here (no internet): dependencies come from the repo's setup step. If a command fails
  for a missing package, say so in risk and finish what you can stand behind - do not keep retrying.
- todo: keep a short list for any job with three or more steps and update it as you go.
- ask_her: only when you cannot go on without her. One question, 2-4 choices; it ends your turn.
- This is a conversation. Her later messages continue it, with everything you did still in place - do not start over.
- Never claim a command passed unless you ran it and saw it pass."""

CHECK_BLOCK = """HER CHECK IS RUNNABLE. Command: `{cmd}` - declared in {source}. run_check runs exactly that command
(`only` = one test file when her command allows it); grep_log searches the last run's whole output.
- A bug fix is proved, not claimed: write the failing test first, run_check and SEE IT FAIL on the unfixed code, then
  fix and run_check until it passes. A new test that passes before the fix proves nothing - write a better one.
- Before you call done, run_check once with everything in place. If it fails you are not finished."""


def _box_tool(tid: str, dw: DiskWorkspace, ctx: dict[str, Any], name: str, inp: dict[str, Any], state: dict[str, Any],
              emit) -> str:
    """run_command / command_output / run_check / grep_log, as text for the model and one terminal entry for her."""
    from ..devlab import out as O
    from ..devlab import spec as SP
    box, env = ctx["name"], ctx["env"]
    cmd_s = int(_setting("dev_workspace_cmd_s", 300))
    if name == "command_output":
        slot = re.sub(r"[^a-z0-9]", "", str(inp.get("id") or "").lower())[:12]
        if slot not in state["bg"]:
            return "No background command with that id in this session."
        if inp.get("stop"):
            BOX.bg_stop(box, slot)
            time.sleep(0.3)
        r = BOX.bg_read(box, slot)
        text = scrub(str(r.get("out") or ""))[-OUT_TAIL:]
        term_set(tid, state["bg"][slot], out=text, running=bool(r.get("running")), rc=r.get("rc"),
                 ok=(r.get("rc") == 0) if r.get("rc") is not None else None)
        dw.trail.append(f"background {slot} dekha")
        emit({"k": "cmdout", "id": slot, "running": bool(r.get("running")), "rc": r.get("rc")})
        return (f"[{slot}] " + ("still running" if r.get("running") else f"finished, exit {r.get('rc')}") + "\n" + text)[:20000]
    if name == "grep_log":
        pat = str(inp.get("pattern") or "").strip()
        if not pat:
            return "grep_log needs a pattern: a test name, a file path, 'Error', 'assert'."
        if not state.get("log"):
            return "Run run_check or run_command first - then its output can be searched."
        dw.trail.append(f"log mein dhoonda: {pat[:40]}")
        emit({"k": "grep", "q": pat[:60]})
        return scrub(O.grep_log(state["log"], pat))[:20000]
    if state["cmds"] >= int(_setting("dev_workspace_cmds", 60)):
        return "This turn has run its limit of commands. Finish with what you have and say what is left."
    if name == "run_check":
        sp = ctx["spec"]
        base_cmd = str(sp.get("test") or "")
        if not base_cmd or sp.get("confirm"):
            return "run_check has no declared command here. Use run_command with the repo's own test command instead."
        only = str(inp.get("only") or "").strip()
        cmd = (SP.one_file(base_cmd, str(sp.get("lang") or ""), only) if only else "") or base_cmd
        note = f"[{only} cannot run alone with her command - ran the whole check]\n" if only and cmd == base_cmd else ""
        kind, why, bg = "check", str(inp.get("why") or "")[:200], False
    else:
        cmd = SP._clean(str(inp.get("command") or ""))
        bad = SP.refuse_reason(cmd) if cmd else "the command is empty"
        if not bad and R.secrets_in(cmd):                  # a key typed into a command would sit in her terminal and the log
            bad = "it has a key or a password in it"
        if bad or "\n" in str(inp.get("command") or "").strip():
            emit({"k": "refused", "tool": "run_command", "why": "That command does not run in the box: " + (bad or "one line only")})
            return ("Refused: that command does not run in the box (sudo / docker / a service, a key or password in it, "
                    "more than one line, or too long). Use a plain one-line command.")
        only, note, kind, why, bg = "", "", "cmd", str(inp.get("why") or "")[:200], bool(inp.get("background"))
    state["cmds"] += 1
    if bg:
        slot = f"bg{len(state['bg']) + 1}"
        limit = int(_setting("dev_workspace_bg_s", 900))
        st = BOX.bg_start(box, slot, cmd, limit, env)
        if not st.get("ok"):
            return f"The background command did not start: {st.get('why', '')}"
        e = term_add(tid, {"kind": "bg", "id": slot, "cmd": cmd[:400], "why": why, "running": True, "out": ""})
        state["bg"][slot] = e["n"]
        dw.trail.append(f"background command: {cmd[:60]}")
        emit({"k": "cmd", "cmd": cmd[:200], "why": why, "bg": slot})
        return f"Started in the background as {slot} (it is stopped after {limit // 60} min). Read it with command_output."
    lim = cmd_s if kind == "cmd" else int(ctx["spec"].get("timeout") or _setting("dev_lab_timeout", 600))
    if kind == "cmd" and inp.get("timeout"):
        try:
            lim = max(5, min(cmd_s, int(inp["timeout"])))
        except (TypeError, ValueError):
            pass
    r = BOX.run(box, f"set -o pipefail; {cmd}", lim, env)
    text = scrub(str(r.get("out") or ""))
    logs = _meta(tid) / "logs"
    logs.mkdir(exist_ok=True)
    for old in sorted(logs.glob("*.log"), key=lambda p: p.stat().st_mtime)[:-20]:
        try:
            old.unlink()
        except OSError:
            pass
    logp = O.write_log(str(logs), f"{kind}-{int(time.time() * 1000)}", text)
    res = O.shape(text, int(r.get("rc") or 0), logp, float(r.get("secs") or 0), bool(r.get("timed_out")))
    state["log"] = logp
    ok = bool(res.get("ok"))
    term_add(tid, {"kind": kind, "cmd": cmd[:400], "why": why, "rc": r.get("rc"), "ok": ok,
                   "seconds": res.get("seconds"), "timed_out": bool(r.get("timed_out")), "out": text[-OUT_TAIL:]})
    tail = [x.strip()[:200] for x in text.splitlines() if x.strip()][-6:]
    if kind == "check":
        state["checks"].append({"ok": ok, "cmd": cmd, "only": only, "seconds": res.get("seconds"), "log": logp, "why": why})
        dw.trail.append(("check PASS" if ok else "check FAIL") + f" ({res.get('seconds')}s)")
        emit({"k": "check", "ok": ok, "seconds": res.get("seconds"), "cmd": cmd[:120], "only": only[:120], "tail": tail})
    else:
        dw.trail.append(f"command chalayi: {cmd[:60]} ({'ok' if ok else 'exit ' + str(r.get('rc'))})")
        emit({"k": "cmd", "cmd": cmd[:200], "why": why, "ok": ok, "rc": r.get("rc"), "seconds": res.get("seconds"), "tail": tail})
    more = "\n(The whole output is in a log - use grep_log to search it.)" if res.get("cut") else ""
    return f"{note}{O.say(res, cmd)}\n{'-' * 40}\n{res.get('shown', '')}{more}"[:60000]


def _todo(tid: str, inp: dict[str, Any], emit) -> str:
    items = []
    for it in (inp.get("items") or [])[:20]:
        if isinstance(it, dict) and str(it.get("text") or "").strip():
            st = str(it.get("state") or "pending")
            items.append({"text": str(it["text"]).strip()[:160], "state": st if st in ("pending", "doing", "done") else "pending"})
    with session() as s:
        w = _row(s, tid)
        if w is not None:
            w.todo = json.dumps(items) if items else None
    emit({"k": "todo", "items": items})
    return "Saved." if items else "The list is empty."


def turn(tenant: str, t: Any, g: Any, cfg: Any, token: str, *, extra_files: list[str] | None = None, issue_txt: str = "",
         plan_txt: str = "", attach: tuple[str, list[dict[str, Any]]] | None = None, on_step: Any = None,
         follow: str = "", by_her: bool = True, system_extra: str = "", resume: bool = False,
         max_steps: int = 40, minutes: float = 20.0) -> tuple[str, list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """One turn of the conversation, in the session's box. Returns exactly what loop.run returns - (base_sha, read,
    ctx, out) - so everything after the edit (the checks on the change, her PR tap, the CI loop) is the same code.

    `follow` = her next message (or a CI log) for a session that already has history; empty on the first turn.
    `resume` = the server restarted in the middle of this turn: go on from the last step that was saved."""
    tid = t.id
    ev_fn, inbox, stopped, beat = (L._hook(on_step, n) for n in ("event", "inbox", "stopped", "beat"))

    def emit(ev: dict[str, Any]) -> None:
        if ev_fn:
            try:
                ev_fn(ev)
            except Exception:  # noqa: BLE001
                pass
    rd = ready(tenant)
    if not rd["ok"]:
        raise Unavailable(rd["say"] or rd["why"])
    # 1. a live place (hers is one of at most `dev_workspace_live` on the server)
    t_wait, told = time.time(), False
    while True:
        if stopped and stopped():
            raise L.Stopped("stopped")
        ok, why = _claim(tid, tenant, t.repo)
        if ok:
            break
        if not told:
            told = True
            emit({"k": "box", "state": "wait", "text": f"Waiting for a free box - {why}"})
        if time.time() - t_wait > float(_setting("dev_workspace_wait_min", 20)) * 60:
            raise Unavailable("no box came free in time")
        if beat:
            beat()
        time.sleep(float(_setting("dev_workspace_poll_s", 3)))
    L.STATS["runs"] += 1
    L.pick(t)
    messages: list[dict] = []
    try:
        try:
            dw, ctx = _open(tid, tenant, t, g, token, emit, bool(getattr(cfg, "allow_workflows", False)))
        except Unavailable:
            raise
        except Exception as e:  # noqa: BLE001 - nothing has been asked of the model yet: the old engine can take over
            log.exception("workspace %s could not open", tid)
            raise Unavailable(f"the box could not open ({e.__class__.__name__})")
        _sync(tid, t, dw)
        sp = ctx["spec"]
        can_check = bool(sp.get("test")) and not sp.get("confirm")
        tools = L.TOOLS + BOX_TOOLS + (L.LAB_TOOLS if can_check else [])
        system = (L.SYSTEM + ("\n\n" + system_extra if system_extra else "") + "\n\n"
                  + BOX_BLOCK.format(cmd_s=int(_setting("dev_workspace_cmd_s", 300)),
                                     bg_m=int(_setting("dev_workspace_bg_s", 900)) // 60)
                  + ("\n\n" + CHECK_BLOCK.format(cmd=sp["test"], source=sp.get("source") or "her repo") if can_check else "")
                  + ("\n\n" + ctx["note"] if ctx["note"] else ""))
        messages = list(_history(tid).get("messages") or [])
        tr = R.trace(t.text + "\n" + issue_txt)
        if resume and messages and not (follow and not _said(messages, follow)):
            _append_user(messages, "[The server restarted in the middle of your work. Your files in the box are as you "
                                   "left them. Continue from where you were, or call done.]")
        elif not messages:
            hints = [p for p in (R.match_path(dw.paths, f["file"]) for f in tr["files"]) if p]
            hints += [p for p in (R.match_path(dw.paths, f) for f in (extra_files or [])) if p]
            line = (f"\nHer check command for this repo: `{sp['test']}` ({sp.get('source')}) - run it with run_check.\n"
                    if can_check else "")
            first = L.first_message(t, dw, getattr(cfg, "rules", "") or "", issue_txt, hints, plan_txt=plan_txt,
                                    attach=attach, check_line=line)
            if follow:
                first += "\n\n" + follow
            _snapshot(tid, t.text, [])
            _append_user(messages, first, list(attach[1]) if attach and attach[1] else None)
        else:
            if by_her:
                n = _snapshot(tid, follow, messages)
                emit({"k": "msg", "n": n, "text": re.sub(r"</?her_\w+>", "", follow).strip()[:1200]})
            where = (f"\n(Her pull request #{t.pr_number} is open on branch {t.branch}: new edits become a new commit on it.)"
                     if t.status in ON_BRANCH and getattr(t, "pr_number", 0) else "")
            _append_user(messages, (follow or "Continue.") + where)
        with session() as s:
            w = _row(s, tid)
            w.ask = None
        _save_history(tid, messages)
        finish: dict[str, Any] | None = None
        asked: dict[str, Any] | None = None
        state: dict[str, Any] = {"cmds": 0, "bg": {}, "checks": [], "log": ""}
        t0, steps, nudged = time.time(), 0, 0
        while steps < max_steps and time.time() - t0 < minutes * 60:
            if stopped and stopped():
                raise L.Stopped("stopped")
            if beat:
                beat()
            steps += 1
            blocks, stop = L.BRAIN(system, trim(messages), tools)
            messages.append({"role": "assistant", "content": blocks})
            for b in blocks:
                if b.get("type") == "text" and str(b.get("text") or "").strip():
                    emit({"k": "say", "text": str(b["text"]).strip()[:800]})
            uses = [b for b in blocks if b.get("type") == "tool_use"]
            if not uses:
                if stop == "max_tokens":
                    messages.append({"role": "user", "content": "[Your answer was cut. Continue with the tools.]"})
                    continue
                if nudged >= 1:
                    break
                nudged += 1
                messages.append({"role": "user", "content": "[Use the tools to continue, or call done if the work is finished.]"})
                continue
            results = []
            for b in uses:
                name, inp = b["name"], (b.get("input") or {})
                if name == "done":
                    finish = dict(inp)
                    results.append({"type": "tool_result", "tool_use_id": b["id"], "content": "Finished."})
                    continue
                if name == "ask_her":
                    q = str(inp.get("question") or "").strip()[:600]
                    asked = {"q": q if q.endswith("?") else (q.rstrip(".") + "?"),
                             "choices": [str(c).strip()[:80] for c in (inp.get("choices") or []) if str(c).strip()][:4]}
                    results.append({"type": "tool_result", "tool_use_id": b["id"],
                                    "content": "Asked. Your turn ends here; her answer continues this conversation."})
                    continue
                before = len(dw.trail)
                if name == "todo":
                    out_ = _todo(tid, inp, emit)
                elif name in ("run_command", "command_output", "run_check", "grep_log"):
                    out_ = _box_tool(tid, dw, ctx, name, inp, state, emit)
                else:
                    out_ = dw.run(name, inp)
                    for ev in L.step_event(dw, name, inp, out_, before):
                        emit(ev)
                if on_step and len(dw.trail) > before:
                    try:
                        on_step(dw.trail[-1])
                    except Exception:  # noqa: BLE001
                        pass
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": out_[:60000]})
            notes = []
            if inbox and finish is None and asked is None:
                try:
                    notes = [str(x)[:2000] for x in (inbox() or []) if str(x).strip()]
                except Exception:  # noqa: BLE001
                    notes = []
            if notes:
                results.append({"type": "text", "text": "<her_note_while_you_work>\n" + "\n".join(notes)
                                + "\n</her_note_while_you_work>\nTake this into account from your next step."})
                for n_ in notes:
                    emit({"k": "note", "text": n_[:600]})
            messages.append({"role": "user", "content": results})
            _save_history(tid, messages)
            if finish is not None or asked is not None:
                break
        for slot in list(state["bg"]):                        # nothing of this turn keeps running after it
            try:
                BOX.bg_stop(ctx["name"], slot)
            except Exception:  # noqa: BLE001
                pass
        finished = finish is not None or asked is not None
        if not finished:
            L.STATS["step_cap"] += 1
            finish = {"explain": "I reached this turn's limit of steps / time. What I changed so far is in the box - "
                                 "send a message and I will go on from here.",
                      "risk": "Step / time limit reached before the work was called done - review the diff carefully."}
        else:
            L.STATS["done"] += 1
        finish = finish or {}
        sc = dw.scan()
        files = [{"path": p, "why": "", "content": dw._text(p)} for p in dw.changed()]
        risk = str(finish.get("risk") or "")
        if sc["deleted"]:
            risk = (risk + "\n" if risk else "") + ("Deleted in the box but NOT sent (a deletion is not part of a change "
                                                    "yet): " + ", ".join(sc["deleted"][:10]))
        if asked is not None:
            with session() as s:
                w = _row(s, tid)
                w.ask = json.dumps(asked)
            files = []
        elif t.kind == "explain":
            files = []
        read = [{"path": p, "sha": o["sha"], "text": o["text"], **({"hidden": o["hidden"]} if o.get("hidden") else {})}
                for p, o in ((f["path"], dw._load(f["path"])) for f in files)]
        out = {"explain": asked["q"] if asked else finish.get("explain", ""), "cause": finish.get("cause", ""),
               "files": files, "pr_title": finish.get("pr_title", ""), "pr_summary": finish.get("pr_summary", ""),
               "test_plan": finish.get("test_plan", ""), "risk": risk, "rules_followed": finish.get("rules_followed", ""),
               "checks": state["checks"], "asked": asked is not None, "engine": "workspace"}
        found = {"trace": tr["files"], "errors": tr["errors"], "words": tr["words"], "read": sorted(dw.read),
                 "checks": state["checks"], "hidden": sorted(dw.hidden), "tree_size": len(dw.paths),
                 "issue": bool(issue_txt), "rules": list(dict.fromkeys(dw.rules_shown)),
                 "loop": {"steps": steps, "searched": dw.searched[-20:], "trail": dw.trail[-60:], "finished": finished,
                          "engine": "workspace", "commands": state["cmds"]}}
        _save_json(_meta(tid) / "seen.json", {"read": sorted(dw.read), "rules": list(dict.fromkeys(dw.rules_shown))})
        return dw.base, read, {"found": found, "context": ""}, out
    finally:
        if messages:
            try:
                _save_history(tid, messages)
            except Exception:  # noqa: BLE001
                log.debug("workspace history save failed", exc_info=True)
        _release(tid)


# ---------------------------------------------------------------- what the page asks
def view(tid: str) -> dict[str, Any]:
    """The session's box for the page: is the engine on, is this one live / paused, Hoola's own list, a question that
    waits, the points she can rewind to, the check command."""
    on = bool(_setting("dev_workspace", False))
    with session() as s:
        w = _row(s, tid)
        if w is None or w.state in ("", "closed"):
            return {"on": on, "state": "", "cap": cap()}
        sp = _j(w.spec or "", {})
        ask = _j(w.ask or "", {})
        live = s.scalars(select(DevWorkspace).where(DevWorkspace.state == "live")).all()
        return {"on": on, "state": w.state, "busy": bool(w.busy), "cap": cap(), "live": len(live),
                "todo": _j(w.todo or "", []), "question": ask.get("q", ""), "choices": ask.get("choices") or [],
                "snaps": _j(w.snaps or "", [])[-12:], "msgs": int(w.msgs or 0),
                "check": {"cmd": sp.get("test") or "", "source": sp.get("source") or "", "confirm": bool(sp.get("confirm"))},
                "used": w.used_at.isoformat() if w.used_at else ""}


def status() -> dict[str, Any]:
    rd = ready()
    with session() as s:
        rows = s.scalars(select(DevWorkspace).where(DevWorkspace.state.in_(("live", "paused")))).all()
        return {"on": bool(_setting("dev_workspace", False)), "ready": rd["ok"], "say": rd.get("say", ""), "cap": cap(),
                "live": [{"id": w.id, "busy": bool(w.busy)} for w in rows if w.state == "live"],
                "paused": sum(1 for w in rows if w.state == "paused"),
                "idle_min": int(_setting("dev_workspace_idle_min", 30))}


def tree(tid: str, path: str = "") -> dict[str, Any]:
    """One folder of the session's checkout, for the Files pane. A paused session has no files on the server."""
    work = _work(tid)
    if not work.is_dir():
        return {"live": False, "entries": []}
    from ..devlab.service import safe_rel
    rel = safe_rel(path) if path else ""
    d = work / rel if rel else work
    root = os.path.realpath(work)
    real = os.path.realpath(d)
    if (path and not rel) or not (real == root or real.startswith(root + os.sep)) or not d.is_dir() or d.is_symlink():
        return {"live": True, "path": rel, "entries": [], "missing": True}
    manifest = _load_json(_meta(tid) / "base.json", {})
    rows = []
    for e in sorted(os.scandir(d), key=lambda x: (not x.is_dir(follow_symlinks=False), x.name.lower())):
        if e.name == ".git" or e.is_symlink():
            continue
        p = (rel + "/" if rel else "") + e.name
        if e.is_dir(follow_symlinks=False):
            rows.append({"name": e.name, "path": p, "dir": True, "junk": e.name in JUNK})
        else:
            try:
                st = e.stat(follow_symlinks=False)
            except OSError:
                continue
            m = manifest.get(p)
            mark = "new" if m is None else ("" if (st.st_size == m[1] and st.st_mtime_ns == m[2]) else "changed")
            rows.append({"name": e.name, "path": p, "dir": False, "size": st.st_size, "mark": mark})
        if len(rows) >= 400:
            break
    return {"live": True, "path": rel, "entries": rows}


def file_text(tid: str, path: str) -> dict[str, Any]:
    work = _work(tid)
    if not work.is_dir():
        return {"live": False}
    from ..devlab.service import safe_rel
    rel = safe_rel(path)
    p = work / rel if rel else None
    root = os.path.realpath(work)
    if p is None or p.is_symlink() or not p.is_file() or not os.path.realpath(p.parent).startswith(root):
        return {"live": True, "path": rel, "missing": True}
    if R.SECRET_FILES.search(rel) or R.BINARY_EXT.search(rel):
        return {"live": True, "path": rel, "hidden": "This file is not shown (a key file or a binary)."}
    if p.stat().st_size > MAX_TEXT:
        return {"live": True, "path": rel, "hidden": "This file is too large to show here."}
    text = p.read_text("utf-8", errors="replace")
    if R.secrets_in(text):
        return {"live": True, "path": rel, "hidden": "This file holds a key or a password, so it is not shown."}
    return {"live": True, "path": rel, "text": text, "lines": text.count("\n") + 1}


# ---------------------------------------------------------------- the worker's minute
def tick(running: Any = None) -> None:
    """Every minute: pause a live session nobody used for a while, free a 'busy' mark a restart left behind, and
    remove a box that belongs to no live session."""
    if not bool(_setting("dev_workspace", False)):
        return
    is_running = running or (lambda _tid: False)
    idle = timedelta(minutes=float(_setting("dev_workspace_idle_min", 30)))
    with session() as s:
        rows = [(w.id, w.state, bool(w.busy), w.used_at or w.created_at)
                for w in s.scalars(select(DevWorkspace).where(DevWorkspace.state.in_(("live", "opening")))).all()]
    for tid, state, busy, used in rows:
        if busy and not is_running(tid):
            with session() as s:
                w = _row(s, tid)
                if w is not None:
                    w.busy = False
                    if w.state == "opening":
                        w.state = ""
            busy = False
        if state == "live" and not busy and used is not None:
            u = used if used.tzinfo else used.replace(tzinfo=now().tzinfo)
            if now() - u > idle:
                pause(tid, "idle")
    try:
        live = {BOX.name_for(w["id"]) for w in live_now()}
        for name in BOX.names():
            if name not in live:
                BOX.stop(name, "")
    except Exception:  # noqa: BLE001
        log.debug("workspace box sweep failed", exc_info=True)


# ---------------------------------------------------------------- `python -m app.devsahayak.wsp check`
def selftest() -> list[str]:
    """Does a LIVE box work on this machine? No repo of hers, no model: a folder, a box, a few commands."""
    import tempfile
    from ..devlab import box
    lines = []
    av = box.available()
    lines.append("docker: " + ("ok " + str(av.get("docker")) if av["ok"] else "NO - " + av["why"]))
    if not av["ok"]:
        return lines
    if not av.get("base_built") or av.get("base_stale"):
        b = box.build_base(nocache=bool(av.get("base_stale")))
        lines.append(f"base image build: {'ok' if b['ok'] else 'FAIL - ' + b['why']} ({b.get('seconds')}s)")
        if not b["ok"]:
            return lines
    work = tempfile.mkdtemp(prefix="hoola-ws-self-")
    name = box.live_name("selftest")
    try:
        os.chmod(work, 0o777)
        Path(work, "a.txt").write_text("one\n")
        st = box.start_live(name, box.BASE_IMAGE, work)
        lines.append("live box starts: " + ("ok" if st["ok"] else "FAIL - " + st["why"]))
        if not st["ok"]:
            return lines
        r1 = box.exec_live(name, "echo two >> a.txt; echo made > made.txt; cat a.txt", 60)
        lines.append("a command runs and sees the files: " + ("ok" if r1["rc"] == 0 and "two" in r1["out"] else "FAIL " + r1["out"][-200:]))
        r2 = box.exec_live(name, "cat made.txt", 60)
        lines.append("files stay between commands: " + ("ok" if "made" in r2["out"] else "FAIL " + r2["out"][-200:]))
        lines.append("the server sees what the box wrote: " + ("ok" if Path(work, "made.txt").is_file() else "FAIL"))
        net = box.exec_live(name, "python3 -c \"import socket;socket.create_connection(('1.1.1.1',53),timeout=4)\"", 60)
        lines.append("no internet in the box: " + ("ok" if net["rc"] != 0 else "DANGER - the box reached the internet"))
        ro = box.exec_live(name, "touch /etc/hoola-should-fail 2>&1; echo rc=$?", 60)
        lines.append("root filesystem read-only: " + ("ok" if "rc=0" not in ro["out"] else "FAIL - it could write"))
        who = box.exec_live(name, "id -u", 60)
        lines.append("not root: " + ("ok" if who["out"].strip() not in ("0", "") else "FAIL (" + who["out"].strip()[:20] + ")"))
        slow = box.exec_live(name, "sleep 30", 3)
        lines.append("a command is cut at its time limit: " + ("ok" if slow["timed_out"] else f"FAIL (rc {slow['rc']})"))
        box.bg_start(name, "bg1", "for i in 1 2 3; do echo tick $i; sleep 1; done", 30)
        time.sleep(4.5)
        bg = box.bg_read(name, "bg1")
        lines.append("a background command runs and is read later: " + ("ok" if "tick 3" in bg["out"] and not bg["running"]
                                                                        else f"FAIL {bg}"))
        lines.append("the box stops: " + ("ok" if box.stop_live(name, work) and not box.live_alive(name) else "FAIL"))
        try:
            shutil.rmtree(work)
            lines.append("the server can remove the files afterwards: ok")
        except OSError as e:
            lines.append(f"the server can remove the files afterwards: FAIL ({e})")
    finally:
        box.stop_live(name, work)
        shutil.rmtree(work, ignore_errors=True)
    lines.append(f"live boxes allowed at once: {cap()} (dev_workspace_live); switch dev_workspace is "
                 + ("ON" if _setting("dev_workspace", False) else "OFF"))
    return lines


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["check"]:
        for line in selftest():
            print(line)
    else:
        print("usage: python -m app.devsahayak.wsp check")
