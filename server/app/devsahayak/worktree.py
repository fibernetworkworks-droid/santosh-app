"""v0.999 WORKTREES FOR AGENTS, Claude Code's `isolation: worktree` (owner: "GO NEXT - WORKTREES FOR AGENTS").

In Claude Code an agent can work in its own git worktree: its edits never touch the main working copy, several editing
agents can run at once (and in the background), an agent whose copy ended unchanged has it removed, and a changed one is
kept for the main agent to bring in. Hoola Code does the same with ONE difference, on purpose: a `git worktree` keeps
its `.git` as a pointer to a path on the server, and commands run in a locked box that only sees the copy - git would
break there. So an agent's copy here is a SELF-CONTAINED copy of the working copy at the moment it starts (her
uncommitted edits included, secrets still hidden), with its own git starting point:

- make(): copied with reflinks where the disk can (cheap), refused when the copy would be too big or the disk too full,
  and the repo's WorktreeCreate hook may say no.
- finish(): unchanged copy = removed; changed = KEPT, with the files it changed.
- apply(): its changes come into the main working copy as one patch - plainly when nothing moved under it, else a three-way
  merge (conflicts are marked in the files and named); secret files and paths the coder may not write (CI workflows
  unless she allowed them) are never brought in.
- discard(), listing(), prune() (kept copies live 7 days, at most 8 per session).
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from . import engine as EN

log = logging.getLogger("santosh.devsahayak.worktree")
_LOCK = threading.Lock()
STATS = {"made": 0, "kept": 0, "removed": 0, "applied": 0, "conflicts": 0, "discarded": 0, "refused": 0}


class WTError(Exception):
    pass


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def on() -> bool:
    return bool(_set("dev_agent_worktrees", True))


class Copy(EN.Session):
    """An agent's own copy, shaped like a Session so the coder's Tools work in it unchanged."""

    def __init__(self, parent: EN.Session, wid: str):        # noqa: D401 - no super().__init__: other paths
        self.tid, self.parent, self.wid = parent.tid, parent, wid
        self.dir = parent.dir / "worktrees" / wid
        self.repo = self.dir / "repo"
        self.meta_path = self.dir / "meta.json"
        self.msg_path = self.dir / "messages.json"
        self.meta: dict[str, Any] = {}
        if self.meta_path.is_file():
            try:
                self.meta = json.loads(self.meta_path.read_text())
            except ValueError:
                self.meta = {}


# ---------------------------------------------------------------- the registry (one file per session)
def _reg_path(ses: EN.Session) -> Path:
    return ses.dir / "worktrees.json"


def _load(ses: EN.Session) -> dict[str, dict[str, Any]]:
    try:
        return json.loads(_reg_path(ses).read_text())
    except (OSError, ValueError):
        return {}


def _save(ses: EN.Session, reg: dict[str, dict[str, Any]]) -> None:
    ses.dir.mkdir(parents=True, exist_ok=True)
    tmp = _reg_path(ses).with_name(f".worktrees.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(reg))
    os.replace(tmp, _reg_path(ses))


def _update(ses: EN.Session, wid: str, **kw: Any) -> dict[str, Any]:
    with _LOCK:
        reg = _load(ses)
        rec = reg.setdefault(wid, {"id": wid})
        rec.update(kw)
        _save(ses, reg)
        return dict(rec)


def new_id(ses: EN.Session, want: str = "") -> str:
    """A free id, RESERVED at once (two agents started in the same moment never share a copy)."""
    with _LOCK:
        reg = _load(ses)
        if want and re.fullmatch(r"[A-Za-z0-9_-]{1,20}", want) and want not in reg:
            wid = want
        else:
            n = len(reg) + 1
            while f"wt{n}" in reg:
                n += 1
            wid = f"wt{n}"
        reg[wid] = {"id": wid, "status": "reserved", "at": time.time()}
        _save(ses, reg)
        return wid


# ---------------------------------------------------------------- make / finish
def _size_mb(path: Path) -> int:
    try:
        p = subprocess.run(["du", "-sm", "--exclude=.git", str(path)], capture_output=True, text=True, timeout=25)
        return int((p.stdout or "0").split()[0])
    except Exception:  # noqa: BLE001 - unknown size: the disk check below still guards
        return 0


def _copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    items = [str(p) for p in src.iterdir() if p.name != ".git"]
    if items:
        try:                                               # reflink = a cheap copy on filesystems that can; plain otherwise
            p = subprocess.run(["cp", "-a", "--reflink=auto", *items, str(dst)], capture_output=True, text=True, timeout=600)
            if p.returncode == 0:
                return
        except Exception:  # noqa: BLE001
            pass
        for it in items:                                   # fallback: Python's own copy, links copied as links
            s = Path(it)
            t = dst / s.name
            if s.is_symlink():
                os.symlink(os.readlink(s), t)
            elif s.is_dir():
                shutil.copytree(s, t, symlinks=True, dirs_exist_ok=True)
            else:
                shutil.copy2(s, t)


def make(tools: Any, wid: str, agent: str) -> Copy:
    """A fresh copy of the coder's working copy for one agent."""
    ses = tools.s
    if isinstance(ses, Copy):
        raise WTError("an agent working in its own copy cannot make another copy")
    if not ses.repo.is_dir():
        raise WTError("this session has no working copy yet")
    try:
        return _make(tools, ses, wid, agent)
    except BaseException:
        _update(ses, wid, status="failed")                # its reserved id is not left hanging
        raise


def _make(tools: Any, ses: EN.Session, wid: str, agent: str) -> Copy:
    prune(ses)
    kept = [r for k, r in _load(ses).items() if r.get("status") in ("working", "kept", "reserved") and k != wid]
    if len(kept) >= int(_set("dev_worktree_max", 8) or 8):
        STATS["refused"] += 1
        raise WTError(f"{len(kept)} agent copies are already open in this session - bring one in or discard it first "
                      "(agent_worktree)")
    mb = _size_mb(ses.repo)
    cap = int(_set("dev_worktree_max_mb", 2000) or 2000)
    if mb and mb > cap:
        STATS["refused"] += 1
        raise WTError(f"the working copy is {mb} MB, over the {cap} MB an agent's own copy may be")
    try:
        free = shutil.disk_usage(ses.dir).free // (1024 * 1024)
        if free < mb * 2 + 500:
            STATS["refused"] += 1
            raise WTError(f"the server has only {free} MB free - not enough for another copy")
    except OSError:
        pass
    try:                                                   # v0.999 WorktreeCreate: the repo's hook may say no
        from . import repoconf as RC
        if RC.hooks_for(getattr(tools, "conf", {}) or {}, "WorktreeCreate"):
            said = EN.run_hooks(tools, "WorktreeCreate", extra={"name": wid, "worktree_id": wid, "agent_type": agent})
            if said.get("block") or said.get("stop"):
                raise WTError("this repo's WorktreeCreate hook said no: " + (said.get("text") or said.get("stop_reason") or "")[:300])
    except WTError:
        raise
    except Exception:  # noqa: BLE001 - a broken hook does not stop the copy
        pass
    with EN._git_lock(ses.repo):                           # her blobs into the object store: the three-way merge needs them
        EN._git_run(ses.repo, "add", "-A")
    cp = Copy(ses, wid)
    if cp.dir.exists():
        shutil.rmtree(cp.dir, ignore_errors=True)
    t0 = time.time()
    _copy_tree(ses.repo, cp.repo)
    os.chmod(cp.repo, 0o777)
    rc, _ = EN._git(cp.repo, "init", "-q")
    if rc != 0:
        shutil.rmtree(cp.dir, ignore_errors=True)
        raise WTError("git is not available on the server")
    ex = ses.repo / ".git" / "info" / "exclude"
    (cp.repo / ".git" / "info").mkdir(parents=True, exist_ok=True)
    if ex.is_file():
        (cp.repo / ".git" / "info" / "exclude").write_text(ex.read_text())
    base = EN._commit(cp.repo, f"agent copy {wid} for {agent}")
    if not base:
        shutil.rmtree(cp.dir, ignore_errors=True)
        raise WTError("the copy's starting point could not be recorded")
    cp.meta = {k: ses.meta.get(k) for k in ("repo", "sha", "hidden", "mb", "image", "image_setup") if k in ses.meta}
    cp.meta.update({"base": base, "worktree": wid, "made": time.time()})
    cp.save_meta()
    _update(ses, wid, agent=agent, status="working", base=base, at=time.time(), mb=mb, secs=round(time.time() - t0, 1), files=[])
    STATS["made"] += 1
    return cp


def _paths(cp: Copy) -> list[dict[str, str]]:
    return [r for r in cp.changed(cp.meta.get("base") or "") if r.get("path")]


def finish(tools: Any, cp: Copy, agent: str) -> dict[str, Any]:
    """The agent ended: an unchanged copy goes, a changed one stays for the coder (or her) to bring in."""
    ses = cp.parent
    rows = _paths(cp)
    if not rows:
        _remove(tools, ses, cp.wid, "removed")
        STATS["removed"] += 1
        return {"kept": False, "files": []}
    rc, out = EN._git(cp.repo, "diff", "--cached", "--numstat", cp.meta.get("base") or "HEAD")
    add = rem = 0
    for ln in out.splitlines() if rc == 0 else []:
        a, r, *_ = (ln.split("\t") + ["", ""])[:3]
        add += int(a) if a.isdigit() else 0
        rem += int(r) if r.isdigit() else 0
    files = [r["st"] + " " + r["path"] for r in rows][:200]
    _update(ses, cp.wid, status="kept", files=files, added=add, removed=rem, done=time.time())
    STATS["kept"] += 1
    return {"kept": True, "files": files, "added": add, "removed": rem}


def _remove(tools: Any, ses: EN.Session, wid: str, status: str) -> None:
    shutil.rmtree(ses.dir / "worktrees" / wid, ignore_errors=True)
    _update(ses, wid, status=status, gone=time.time())
    try:                                                   # v0.999 WorktreeRemove: a notice for the repo's hook
        from . import repoconf as RC
        if tools is not None and RC.hooks_for(getattr(tools, "conf", {}) or {}, "WorktreeRemove"):
            EN.run_hooks(tools, "WorktreeRemove", extra={"worktree_id": wid, "status": status})
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------- show / apply / discard
def _rec(ses: EN.Session, wid: str) -> dict[str, Any]:
    rec = _load(ses).get(str(wid or ""))
    if rec is None:
        raise WTError(f"there is no agent copy {wid} in this session")
    return rec


def show(ses: EN.Session, wid: str, limit: int = 40000) -> str:
    rec = _rec(ses, wid)
    if rec.get("status") not in ("kept", "working"):
        raise WTError(f"agent copy {wid} is {rec.get('status')}")
    cp = Copy(ses, wid)
    return cp.diff(cp.meta.get("base") or "", limit=limit) or "(no changes)"


def _blocked(rel: str, hidden: set[str], allow_workflows: bool) -> str:
    from . import rules as R
    if rel in hidden:
        return "holds secrets"
    try:
        why = R.path_problem(rel, allow_workflows)
    except Exception:  # noqa: BLE001
        why = ""
    return str(why or "")


def apply(tools: Any, ses: EN.Session, wid: str, allow_workflows: bool = False) -> dict[str, Any]:
    """Bring an agent copy's changes into the main working copy. {ok, files, conflicts, skipped, how}."""
    rec = _rec(ses, wid)
    if rec.get("status") != "kept":
        raise WTError(f"agent copy {wid} is {rec.get('status')} - only a finished copy with changes can be brought in")
    cp = Copy(ses, wid)
    rows = _paths(cp)
    hidden = set(ses.meta.get("hidden") or [])
    skipped, take = [], []
    for r in rows:
        why = _blocked(r["path"], hidden, allow_workflows)
        (skipped if why else take).append((r["path"], why))
    if not take:
        _remove(tools, ses, wid, "discarded")
        return {"ok": False, "files": [], "conflicts": [], "skipped": [f"{p} ({w})" for p, w in skipped],
                "how": "nothing it changed may be brought in"}
    base = cp.meta.get("base") or "HEAD"
    with EN._git_lock(cp.repo):
        EN._git_run(cp.repo, "add", "-A")
        rc, patch = EN._git_run(cp.repo, "diff", "--cached", "--binary", "--full-index", "--no-color", base, "--",
                                *[p for p, _ in take])
    if rc != 0 or not patch.strip():
        raise WTError("its changes could not be read: " + patch.strip()[:200])
    pf = ses.dir / f"agent-{wid}.patch"
    pf.write_text(patch if patch.endswith("\n") else patch + "\n")
    conflicts: list[str] = []
    with EN._git_lock(ses.repo):
        EN._git_run(ses.repo, "add", "-A")
        rc, out = EN._git_run(ses.repo, "apply", "--check", "--whitespace=nowarn", str(pf))
        if rc == 0:
            rc, out = EN._git_run(ses.repo, "apply", "--whitespace=nowarn", str(pf))
            how = "applied cleanly"
        else:                                             # something moved under it: a three-way merge
            rc, out = EN._git_run(ses.repo, "apply", "--3way", "--whitespace=nowarn", str(pf))
            how = "merged three-way"
            u_rc, u = EN._git_run(ses.repo, "diff", "--name-only", "--diff-filter=U")
            conflicts = [x for x in u.splitlines() if x.strip()] if u_rc == 0 else []
            if rc != 0 and not conflicts:
                pf.unlink(missing_ok=True)
                raise WTError("its changes do not fit the working copy any more and were NOT brought in: " + out.strip()[:400])
    pf.unlink(missing_ok=True)
    files = [p for p, _ in take]
    for f in files:                                       # the coder must read them again before it edits them
        try:
            tools.read.discard(f)
        except Exception:  # noqa: BLE001
            pass
    STATS["applied"] += 1
    if conflicts:
        STATS["conflicts"] += 1
    _remove(tools, ses, wid, "applied")
    _update(ses, wid, applied=files, conflicts=conflicts, skipped=[p for p, _ in skipped])
    return {"ok": True, "files": files, "conflicts": conflicts, "skipped": [f"{p} ({w})" for p, w in skipped], "how": how}


def discard(tools: Any, ses: EN.Session, wid: str) -> None:
    rec = _rec(ses, wid)
    if rec.get("status") == "working":
        raise WTError(f"agent copy {wid} is still in use - stop its agent first")
    if rec.get("status") != "kept":
        raise WTError(f"agent copy {wid} is already {rec.get('status')}")
    _remove(tools, ses, wid, "discarded")
    STATS["discarded"] += 1


def listing(ses: EN.Session) -> list[dict[str, Any]]:
    rows = sorted(_load(ses).values(), key=lambda r: r.get("at") or 0, reverse=True)
    return [{k: r.get(k) for k in ("id", "agent", "status", "files", "added", "removed", "at", "done", "conflicts")}
            for r in rows][:40]


def prune(ses: EN.Session) -> int:
    """Copies whose agent is gone (a restart) are finished; kept copies live dev_worktree_days (7)."""
    n = 0
    days = float(_set("dev_worktree_days", 7) or 7)
    reg = _load(ses)
    for wid, r in list(reg.items()):
        d = ses.dir / "worktrees" / wid
        st = r.get("status")
        if st == "working" and time.time() - float(r.get("at") or 0) > 3 * 3600:
            if d.is_dir():                                 # its agent died with a restart: keep what it changed
                try:
                    finish(None, Copy(ses, wid), str(r.get("agent") or ""))
                except Exception:  # noqa: BLE001
                    _remove(None, ses, wid, "removed")
            else:
                _update(ses, wid, status="removed")
            n += 1
        elif st == "kept" and time.time() - float(r.get("done") or r.get("at") or 0) > days * 86400:
            _remove(None, ses, wid, "expired")
            n += 1
        elif st == "reserved" and time.time() - float(r.get("at") or 0) > 3600:
            _update(ses, wid, status="failed")
            shutil.rmtree(d, ignore_errors=True)
            n += 1
        elif st not in ("working", "kept", "reserved") and d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            n += 1
    return n


# ---------------------------------------------------------------- the coder's tool
TOOL = {
    "name": "agent_worktree",
    "description": ("The own copies your agents worked in (agent with isolation=worktree). An agent's changes stay in its "
                    "copy until you bring them in: action=list shows the copies, show the diff of one, apply brings its "
                    "changes into your working copy (re-read those files after), discard throws them away. Look at the "
                    "diff before you apply it."),
    "input_schema": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["list", "show", "apply", "discard"]},
        "id": {"type": "string", "description": "the copy's id, e.g. wt1 or bg2"}}, "required": ["action"]},
}


def tool(tools: Any, inp: dict[str, Any]) -> str:
    ses = tools.s
    act = str(inp.get("action") or "list")
    wid = str(inp.get("id") or "")
    try:
        if act == "list":
            rows = listing(ses)
            if not rows:
                return "No agent copies in this session."
            return "\n".join(f"- {r['id']} ({r.get('agent') or '?'}): {r.get('status')}"
                             + (f", {len(r.get('files') or [])} file(s): " + ", ".join((r.get('files') or [])[:8])
                                if r.get("status") == "kept" else "") for r in rows)
        if act == "show":
            return show(ses, wid)
        if act == "apply":
            r = apply(tools, ses, wid, bool(getattr(tools, "allow_workflows", False)))
            if not r["ok"]:
                return f"Nothing from {wid} came in: {r['how']}." + (" Skipped: " + "; ".join(r["skipped"]) if r["skipped"] else "")
            msg = f"Brought {wid}'s changes into your working copy ({r['how']}): {', '.join(r['files'][:20])}. Read those files again before you edit them."
            if r["conflicts"]:
                msg += (" CONFLICTS in " + ", ".join(r["conflicts"]) + ": your working copy and the agent changed the same lines - "
                        "open those files, settle the <<<<<<< / >>>>>>> parts and remove the markers.")
            if r["skipped"]:
                msg += " Not brought in: " + "; ".join(r["skipped"]) + "."
            return msg
        if act == "discard":
            discard(tools, ses, wid)
            return f"Discarded {wid}: its changes are gone."
        return "action must be list, show, apply or discard."
    except WTError as e:
        return f"Could not: {e}."
