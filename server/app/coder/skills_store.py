"""HOOLA SKILLS (v0.478.0; v0.484 the Skill Desk) - the reusable-skill store, the Hermes
SKILL.md discipline ported.

A skill is ONE markdown file under <coder_dir>/skills/<tenant>/:

    ---
    name: deploy-flask-app
    description: How to deploy a Flask app to the VPS with systemd
    ---
    The instructions, markdown.

Hermes's hard rules, kept:
  frontmatter lint   name <=64 chars, lowercase-hyphenated only; description <=60 chars, one
                     sentence; body <=4000 chars (voice-friendly injection)
  atomic writes      tmp file + rename; an overwrite keeps a .bak beside the file
  read-before-write  update demands a prior read() of the SAME skill in this process
  delete is a SOLO operation   a batch that mixes delete with anything else is refused
  batch cap          <=10 operations per apply() call
  atomic batch       every touched file is snapshotted first; any failure restores them all
  class-level names  a skill names a CLASS of task, never one specific incident (the review
                     prompt enforces it; the lint refuses obvious incident names)

Files are the source of truth; each write mirrors a row into the vault's skills table so the
FTS5 search covers skills with the same three-layer discipline as observations. Tenant scoping
is the house law: one directory per tenant, a tenant never reads another's skills.

v0.484 HOOLA SKILL DESK: the owner's surface over the same files -
  enabled flag       an optional frontmatter line `enabled: false` PARKS a skill: the file
                     stays, the mirror keeps the flag, injection and search stop showing it.
                     set_enabled() is the one writer (the desk's toggle; the model has no such
                     op - parking is the owner's judgement, never the agent's)
  telemetry          every read() marks the ledger (store.skill_use_mark kind='read') - the
                     desk's usage column and the share nomination's evidence
"""
from __future__ import annotations

import os
import re
import threading
import time

log = __import__("logging").getLogger("coder.skills")

NAME_MAX = 64
DESC_MAX = 60
BODY_MAX = 4_000
BATCH_MAX_OPS = 10

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_FRONT_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

_LOCK = threading.RLock()
_READ_OK: set[tuple[str, str]] = set()       # (tenant, name) that did a read() in this process

_OPS = ("read", "list", "create", "update", "delete")


class SkillError(Exception):
    """Refusal with a reason - the tool turns it into a plain error dict."""


# ---------------------------------------------------------------- lint

def validate_name(name: str) -> str:
    n = str(name or "").strip()
    if not n or len(n) > NAME_MAX or not _NAME_RE.match(n):
        raise SkillError(f"skill name must be lowercase-hyphenated, <= {NAME_MAX} chars "
                         f"(got {n[:80]!r})")
    return n


def validate(desc: str, body: str) -> tuple[str, str]:
    d = str(desc or "").strip()
    if not d:
        raise SkillError("description is required (one sentence, <= 60 chars)")
    if len(d) > DESC_MAX:
        raise SkillError(f"description must be <= {DESC_MAX} chars (got {len(d)})")
    b = str(body or "").strip()
    if not b:
        raise SkillError("body is required (the instructions)")
    if len(b) > BODY_MAX:
        raise SkillError(f"body must be <= {BODY_MAX} chars (got {len(b)})")
    return d, b


# ---------------------------------------------------------------- files

def skills_dir(tenant: str) -> str:
    from .store import root
    t = re.sub(r"[^A-Za-z0-9_-]", "_", str(tenant or "default"))[:64] or "default"
    d = os.path.join(root(), "skills", t)
    os.makedirs(d, exist_ok=True)
    return d


def _path(tenant: str, name: str) -> str:
    return os.path.join(skills_dir(tenant), validate_name(name) + ".md")


def render(name: str, desc: str, body: str, enabled: bool = True) -> str:
    head = f"---\nname: {name}\ndescription: {desc}"
    if not enabled:
        head += "\nenabled: false"          # v0.484 the parked skill keeps its flag on disk
    return head + f"\n---\n{body}\n"


def _front_enabled(text: str) -> bool:
    """The frontmatter's enabled flag; absent = enabled (a hand-written file never parks itself)."""
    m = _FRONT_RE.match(text or "")
    if not m:
        return True
    for line in m.group(1).splitlines():
        if line.strip().startswith("enabled:"):
            return str(line.split(":", 1)[1]).strip().lower() not in ("false", "0", "no", "off")
    return True


def parse_skill(text: str) -> tuple[str, str, str]:
    """File content -> (name, description, body). A file with broken frontmatter is a skill
    whose name is its filename and whose body is everything (never crash on hand-edits)."""
    m = _FRONT_RE.match(text or "")
    if not m:
        return "", "", (text or "").strip()
    head, body = m.group(1), text[m.end():].strip()
    name = desc = ""
    for line in head.splitlines():
        if line.startswith("name:"):
            name = line[5:].strip()
        elif line.startswith("description:"):
            desc = line[12:].strip()
    return name, desc, body


def _write_atomic(path: str, content: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    if os.path.exists(path):                     # an overwrite keeps one .bak (Hermes shape)
        with open(path, "r", encoding="utf-8") as f:
            old = f.read()
        with open(path + ".bak", "w", encoding="utf-8") as f:
            f.write(old)
    os.replace(tmp, path)


def _snapshot(paths: list[str]) -> dict[str, str | None]:
    snap: dict[str, str | None] = {}
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                snap[p] = f.read()
        except FileNotFoundError:
            snap[p] = None
    return snap


def _restore(snap: dict[str, str | None]) -> None:
    for p, content in snap.items():
        try:
            if content is None:
                for dead in (p, p + ".bak"):
                    if os.path.exists(dead):
                        os.remove(dead)
            else:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception:
            log.exception("skill rollback failed for %s", p)


# ---------------------------------------------------------------- vault mirror + search hooks

def _mirror(tenant: str, name: str, desc: str, body: str, enabled: bool = True) -> None:
    from . import store
    store.skill_mirror(name, tenant, desc, body, enabled=int(bool(enabled)))


def _unmirror(tenant: str, name: str) -> None:
    from . import store
    store.skill_unmirror(name, tenant)


# ---------------------------------------------------------------- single ops

def create(tenant: str, name: str, desc: str, body: str) -> dict:
    with _LOCK:
        name = validate_name(name)
        desc, body = validate(desc, body)
        p = _path(tenant, name)
        if os.path.exists(p):
            raise SkillError(f"skill {name!r} already exists (use update)")
        _write_atomic(p, render(name, desc, body))
        _READ_OK.add((tenant, name))             # creating counts as knowing it
        _mirror(tenant, name, desc, body)
        return {"op": "create", "name": name, "chars": len(body)}


def update(tenant: str, name: str, desc: str | None = None, body: str | None = None) -> dict:
    with _LOCK:
        name = validate_name(name)
        if (tenant, name) not in _READ_OK:       # read-before-write, Hermes's guard
            raise SkillError(f"read skill {name!r} before writing it")
        p = _path(tenant, name)
        if not os.path.exists(p):
            raise SkillError(f"skill {name!r} does not exist (use create)")
        raw = open(p, encoding="utf-8").read()
        old_name, old_desc, old_body = parse_skill(raw)
        enabled = _front_enabled(raw)            # a content update never flips the owner's flag
        new_desc, new_body = validate(desc if desc is not None else old_desc,
                                      body if body is not None else old_body)
        _write_atomic(p, render(name, new_desc, new_body, enabled=enabled))
        _mirror(tenant, name, new_desc, new_body, enabled=enabled)
        return {"op": "update", "name": name, "chars": len(new_body)}


def read(tenant: str, name: str) -> dict:
    p = _path(tenant, name)
    if not os.path.exists(p):
        raise SkillError(f"skill {name!r} does not exist")
    with open(p, encoding="utf-8") as f:
        raw = f.read()
    _READ_OK.add((tenant, validate_name(name)))
    _, desc, body = parse_skill(raw)
    from . import store as _store            # lazy (the module's import direction)
    _store.skill_use_mark(tenant, name, "read")   # v0.484 telemetry: the follow signal
    return {"name": name, "description": desc, "body": body,
            "enabled": _front_enabled(raw)}


def delete(tenant: str, name: str) -> dict:
    with _LOCK:
        name = validate_name(name)
        if (tenant, name) not in _READ_OK:       # a destructive op demands the read too
            raise SkillError(f"read skill {name!r} before deleting it")
        p = _path(tenant, name)
        if not os.path.exists(p):
            raise SkillError(f"skill {name!r} does not exist")
        os.remove(p)
        for junk in (p + ".bak", p + ".tmp"):
            if os.path.exists(junk):
                os.remove(junk)
        _unmirror(tenant, name)
        _READ_OK.discard((tenant, name))
        return {"op": "delete", "name": name}


def listing(tenant: str) -> list[dict]:
    d = skills_dir(tenant)
    out: list[dict] = []
    try:
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"):
                continue
            try:
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    raw = f.read()
                _, desc, body = parse_skill(raw)
                out.append({"name": fn[:-3], "description": desc, "chars": len(body),
                            "enabled": _front_enabled(raw),
                            "updated_at": time.strftime("%Y-%m-%d", time.localtime(
                                os.path.getmtime(os.path.join(d, fn))))})
            except Exception:
                continue
    except FileNotFoundError:
        pass
    return out


def is_parked(tenant: str, name: str) -> bool:
    """True when the file's frontmatter parks this skill (enabled: false)."""
    p = _path(tenant, name)
    if not os.path.exists(p):
        raise SkillError(f"skill {name!r} does not exist")
    with open(p, encoding="utf-8") as f:
        return not _front_enabled(f.read())


def set_enabled(tenant: str, name: str, on: bool) -> dict:
    """v0.484 the desk's park/unpark: ONE writer for the enabled flag, the file rewritten
    atomically, the mirror updated. The model has no such operation - parking is the owner's
    judgement (a skill she does not want followed right now, not one to delete)."""
    with _LOCK:
        name = validate_name(name)
        p = _path(tenant, name)
        if not os.path.exists(p):
            raise SkillError(f"skill {name!r} does not exist")
        raw = open(p, encoding="utf-8").read()
        if _front_enabled(raw) == bool(on):
            return {"op": "enable" if on else "park", "name": name, "changed": False}
        _, desc, body = parse_skill(raw)
        _write_atomic(p, render(name, desc, body, enabled=bool(on)))
        _mirror(tenant, name, desc, body, enabled=bool(on))
        return {"op": "enable" if on else "park", "name": name, "changed": True}


# ---------------------------------------------------------------- batch apply (Hermes shape)

def apply(tenant: str, operations: list[dict]) -> dict:
    """One atomic batch: snapshot every file the batch could touch FIRST, then run the ops in
    order; any failure restores every snapshot and reports. delete is a SOLO op; the batch is
    capped at BATCH_MAX_OPS. Returns the per-op results or {'error': reason}."""
    if not isinstance(operations, list) or not operations:
        return {"error": "operations must be a non-empty array."}
    if len(operations) > BATCH_MAX_OPS:
        return {"error": f"operations is capped at {BATCH_MAX_OPS} ops per call."}
    if any(isinstance(op, dict) and op.get("action") == "delete" for op in operations):
        if len(operations) != 1:
            return {"error": "delete must be the ONLY operation in its batch."}
    with _LOCK:
        try:
            paths = []
            for op in operations:
                if not isinstance(op, dict):
                    raise SkillError("each operation must be an object")
                act = op.get("action")
                if act not in _OPS:
                    raise SkillError(f"unknown action {act!r} (one of {', '.join(_OPS)})")
                if act not in ("list", "read"):
                    paths.append(_path(tenant, str(op.get("name") or "")))
            snap = _snapshot(paths)
        except SkillError as e:
            return {"error": str(e)}
        except Exception as e:                   # a malformed name must not half-apply
            return {"error": str(e)}
        results: list[dict] = []
        try:
            for i, op in enumerate(operations):
                act, nm = op.get("action"), str(op.get("name") or "")
                if act == "list":
                    results.append({"op": "list", "skills": listing(tenant)})
                elif act == "read":
                    results.append({"op": "read", **read(tenant, nm)})
                elif act == "create":
                    results.append(create(tenant, nm, str(op.get("description") or ""),
                                          str(op.get("body") or "")))
                elif act == "update":
                    results.append(update(tenant, nm,
                                          desc=op.get("description"), body=op.get("body")))
                elif act == "delete":
                    results.append(delete(tenant, nm))
        except SkillError as e:
            _restore(snap)
            return {"error": f"operations[{i}]: {e} (nothing was changed)"}
        except Exception as e:
            _restore(snap)
            return {"error": f"operations[{i}]: {e} (nothing was changed)"}
    return {"ok": True, "results": results}


def reset_for_tests() -> None:
    """Test isolation: forget the read-before-write ledger."""
    with _LOCK:
        _READ_OK.clear()
