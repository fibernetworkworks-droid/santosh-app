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
import shutil
import threading
import time

log = __import__("logging").getLogger("coder.skills")

NAME_MAX = 64
DESC_MAX = 60
BODY_MAX = 4_000
BATCH_MAX_OPS = 10

# v0.494 CLAUDE SKILLS P1: a skill that came IN through the import lane (Anthropic's SKILL.md
# format) carries `imported: true` in its frontmatter and lives under Claude's own limits
# (description 1,024 chars, a long body); skills Hoola/the model writes keep the strict ones.
IMPORT_DESC_MAX = 1_024
IMPORT_BODY_MAX = 30_000
FILE_READ_MAX = 60_000                       # one read_file answer (chars)
FILES_LIST_MAX = 60
BLOCKED_EXTS = {".exe", ".dll", ".msi", ".apk", ".dmg", ".jar", ".so", ".dylib", ".bat", ".cmd", ".scr"}
# Extra frontmatter kept verbatim on every rewrite so a round-trip loses nothing. Honoured today:
# when_to_use (added to the search text) and disable-model-invocation (indexed out of the
# model's shortlist); the rest are stored for export and later phases.
KEEP_FIELDS = ("imported", "when_to_use", "license", "disable-model-invocation", "user-invocable",
               "allowed-tools", "paths", "context", "model", "argument-hint", "compatibility")

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_FRONT_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

_LOCK = threading.RLock()
_READ_OK: set[tuple[str, str]] = set()       # (tenant, name) that did a read() in this process

_OPS = ("read", "list", "create", "update", "delete", "read_file")


class SkillError(Exception):
    """Refusal with a reason - the tool turns it into a plain error dict."""


# ---------------------------------------------------------------- lint

def validate_name(name: str) -> str:
    n = str(name or "").strip()
    if not n or len(n) > NAME_MAX or not _NAME_RE.match(n):
        raise SkillError(f"skill name must be lowercase-hyphenated, <= {NAME_MAX} chars "
                         f"(got {n[:80]!r})")
    return n


def validate(desc: str, body: str, imported: bool = False) -> tuple[str, str]:
    dmax = IMPORT_DESC_MAX if imported else DESC_MAX
    bmax = IMPORT_BODY_MAX if imported else BODY_MAX
    d = str(desc or "").strip()
    if not d:
        raise SkillError("description is required (one sentence, <= 60 chars)")
    if len(d) > dmax:
        raise SkillError(f"description must be <= {dmax} chars (got {len(d)})")
    b = str(body or "").strip()
    if not b:
        raise SkillError("body is required (the instructions)")
    if len(b) > bmax:
        raise SkillError(f"body must be <= {bmax} chars (got {len(b)})")
    return d, b


def _truthy(v) -> bool:
    return str(v or "").strip().lower() in ("true", "1", "yes", "on")


# ---------------------------------------------------------------- files

def skills_dir(tenant: str) -> str:
    from .store import root
    t = re.sub(r"[^A-Za-z0-9_-]", "_", str(tenant or "default"))[:64] or "default"
    d = os.path.join(root(), "skills", t)
    os.makedirs(d, exist_ok=True)
    return d


def _flat(tenant: str, name: str) -> str:
    return os.path.join(skills_dir(tenant), validate_name(name) + ".md")


def _folder(tenant: str, name: str) -> str:
    return os.path.join(skills_dir(tenant), validate_name(name))


def _path(tenant: str, name: str) -> str:
    """The skill's SKILL.md: a folder skill (<name>/SKILL.md, may carry resources) wins over the
    legacy single file (<name>.md). New model-written skills are always the single file."""
    f = os.path.join(_folder(tenant, name), "SKILL.md")
    return f if os.path.isfile(f) else _flat(tenant, name)


def raw_path(tenant: str, name: str) -> str:
    """Public: where this skill's SKILL.md lives (for export / share code that reads the file)."""
    return _path(tenant, name)


def is_folder(tenant: str, name: str) -> bool:
    return os.path.isfile(os.path.join(_folder(tenant, name), "SKILL.md"))


def files_of(tenant: str, name: str) -> list[str]:
    """Bundled resource files of a folder skill (relative paths, SKILL.md and backups left out)."""
    base = _folder(tenant, name)
    out: list[str] = []
    for dp, dns, fns in os.walk(base):
        dns[:] = sorted(d for d in dns if not d.startswith("."))
        for fn in sorted(fns):
            if fn.startswith(".") or fn.endswith((".bak", ".tmp")):
                continue
            rel = os.path.relpath(os.path.join(dp, fn), base).replace(os.sep, "/")
            if rel != "SKILL.md":
                out.append(rel)
    return out


def safe_rel(rel: str) -> str:
    """A resource path that stays INSIDE a skill folder: relative, no '..', no dot-parts, no
    drive letters, no backslashes. Raises SkillError otherwise."""
    r = str(rel or "").replace("\\", "/").strip()
    parts = r.split("/")
    if (not r or r.startswith("/") or len(r) > 200 or ":" in r
            or any(p in ("", ".", "..") or p.startswith(".") for p in parts)):
        raise SkillError(f"bad file path {r[:80]!r}")
    return "/".join(parts)


def parse_front(text: str) -> tuple[dict, str]:
    """Full frontmatter -> ({key: value}, body). Understands quoted values and YAML block scalars
    (`description: >` / `|`) as real Claude skills write them; one-line values otherwise."""
    m = _FRONT_RE.match(text or "")
    if not m:
        return {}, (text or "").strip()
    lines = m.group(1).splitlines()
    out: dict = {}
    i = 0
    while i < len(lines):
        ln = lines[i]
        i += 1
        if not ln.strip() or ln[0] in " \t" or ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        k, v = k.strip(), v.strip()
        if v in (">", "|", ">-", "|-", ">+", "|+"):
            block: list[str] = []
            while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
                block.append(lines[i].strip())
                i += 1
            v = (" " if v[0] == ">" else "\n").join(x for x in block if x)
        elif len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k] = v
    return out, text[m.end():].strip()


def _extra_of(front: dict) -> dict:
    """The preserved extra frontmatter (single-line, capped) from a parsed frontmatter dict."""
    out = {}
    for k in KEEP_FIELDS:
        if k in front and str(front[k]).strip():
            out[k] = " ".join(str(front[k]).split())[:1536]
    return out


def render(name: str, desc: str, body: str, enabled: bool = True, extra: dict | None = None) -> str:
    head = f"---\nname: {name}\ndescription: {' '.join(str(desc).split())}"
    if not enabled:
        head += "\nenabled: false"          # v0.484 the parked skill keeps its flag on disk
    for k in KEEP_FIELDS:
        if extra and extra.get(k):
            head += f"\n{k}: {' '.join(str(extra[k]).split())}"
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

def _mirror(tenant: str, name: str, desc: str, body: str, enabled: bool = True,
            extra: dict | None = None) -> None:
    from . import store
    extra = extra or {}
    if _truthy(extra.get("disable-model-invocation")):
        enabled = False                  # manual-only: never in the model's shortlist (file flag untouched)
    search_desc = desc
    if extra.get("when_to_use"):
        search_desc = f"{desc} {extra['when_to_use']}"   # trigger phrases make the skill findable
    store.skill_mirror(name, tenant, search_desc, body, enabled=int(bool(enabled)))


def _unmirror(tenant: str, name: str) -> None:
    from . import store
    store.skill_unmirror(name, tenant)


# ---------------------------------------------------------------- single ops

WHEN_MAX = 300                               # v0.753 a shipped skill's plain trigger words (when_to_use)


def _when_only(extra: dict | None) -> dict:
    """v0.753: the strict lane takes ONE extra field - when_to_use, the plain words people type for this skill (searched
    with the description). Nothing else rides here: `imported` (Claude's big limits) stays the import lane's alone."""
    w = " ".join(str((extra or {}).get("when_to_use") or "").split())
    if len(w) > WHEN_MAX:
        raise SkillError(f"when_to_use must be <= {WHEN_MAX} chars (got {len(w)})")
    return {"when_to_use": w} if w else {}


def create(tenant: str, name: str, desc: str, body: str, extra: dict | None = None) -> dict:
    with _LOCK:
        name = validate_name(name)
        desc, body = validate(desc, body)
        extra = _when_only(extra)
        p = _path(tenant, name)
        if os.path.exists(p):
            raise SkillError(f"skill {name!r} already exists (use update)")
        _write_atomic(p, render(name, desc, body, extra=extra))
        _READ_OK.add((tenant, name))             # creating counts as knowing it
        _mirror(tenant, name, desc, body, extra=extra)
        return {"op": "create", "name": name, "chars": len(body)}


def get_when(tenant: str, name: str) -> str | None:
    """v0.753: a skill's when_to_use ('' = none), None when she has no such skill."""
    try:
        p = _path(tenant, validate_name(name))
    except SkillError:
        return None
    if not os.path.exists(p):
        return None
    front, _ = parse_front(open(p, encoding="utf-8").read())
    return " ".join(str(front.get("when_to_use") or "").split())


def add_when(tenant: str, name: str, when: str, replace: bool = False) -> bool:
    """v0.753: give an EXISTING skill its shipped trigger words - her description and body are never touched. With
    replace=False only a skill that has none gets them; the caller passes replace=True only for a line Hoola itself
    shipped earlier (a when_to_use she wrote is never overwritten). True when the file changed."""
    w = _when_only({"when_to_use": when}).get("when_to_use", "")
    if not w:
        return False
    with _LOCK:
        name = validate_name(name)
        p = _path(tenant, name)
        if not os.path.exists(p):
            return False
        raw = open(p, encoding="utf-8").read()
        front, _ = parse_front(raw)
        extra = _extra_of(front)
        if extra.get("when_to_use") and (not replace or extra["when_to_use"] == w):
            return False
        _, desc, body = parse_skill(raw)
        enabled = _front_enabled(raw)
        extra["when_to_use"] = w
        _write_atomic(p, render(name, desc, body, enabled=enabled, extra=extra))
        _mirror(tenant, name, desc, body, enabled=enabled, extra=extra)
        return True


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
        extra = _extra_of(parse_front(raw)[0])   # nor drops the imported flag / extra fields
        new_desc, new_body = validate(desc if desc is not None else old_desc,
                                      body if body is not None else old_body,
                                      imported=_truthy(extra.get("imported")))
        _write_atomic(p, render(name, new_desc, new_body, enabled=enabled, extra=extra))
        _mirror(tenant, name, new_desc, new_body, enabled=enabled, extra=extra)
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
    out = {"name": name, "description": desc, "body": body, "enabled": _front_enabled(raw)}
    when = _extra_of(parse_front(raw)[0]).get("when_to_use")
    if when:
        out["when_to_use"] = when
    if is_folder(tenant, name):
        out["files"] = files_of(tenant, name)[:FILES_LIST_MAX]   # read_file pulls one on demand
    return out


def read_file(tenant: str, name: str, rel: str) -> dict:
    """Level-3 loading: one bundled text file of a folder skill, on demand. Confined to the
    skill's own folder (no '..', no symlink out), size-capped, text types only."""
    name = validate_name(name)
    if not is_folder(tenant, name):
        raise SkillError(f"skill {name!r} has no bundled files")
    rel = safe_rel(rel)
    base = os.path.realpath(_folder(tenant, name))
    target = os.path.realpath(os.path.join(base, rel))
    if os.path.commonpath([base, target]) != base or not os.path.isfile(target):
        raise SkillError(f"file {rel!r} is not in skill {name!r}")
    ext = os.path.splitext(target)[1].lower()
    if ext in BLOCKED_EXTS or ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ttf", ".otf",
                                      ".woff", ".woff2", ".zip", ".mp3", ".mp4", ".wav"):
        raise SkillError(f"{rel!r} is not a text file (it ships with the skill but cannot be read here)")
    with open(target, "rb") as f:
        data = f.read(FILE_READ_MAX * 4 + 1)
    text = data.decode("utf-8", "replace")
    return {"op": "read_file", "name": name, "path": rel, "content": text[:FILE_READ_MAX],
            "truncated": len(text) > FILE_READ_MAX}


def install(tenant: str, name: str, desc: str, body: str, extra: dict | None = None,
            files: dict | None = None) -> dict:
    """The IMPORT lane's writer (Anthropic SKILL.md format): Claude's limits, `imported: true`
    stamped, optional bundled files (folder layout). Create-if-missing - never overwrites.
    A folder is built beside the final name and renamed in, so a failure leaves nothing."""
    with _LOCK:
        name = validate_name(name)
        desc = " ".join(str(desc or "").split())
        desc, body = validate(desc, body, imported=True)
        if os.path.exists(_flat(tenant, name)) or os.path.isdir(_folder(tenant, name)):
            raise SkillError(f"skill {name!r} already exists (use update)")
        extra = {**_extra_of(extra or {}), "imported": "true"}
        content = render(name, desc, body, extra=extra)
        if files:
            clean: dict[str, bytes] = {}
            for rel, data in files.items():
                r = safe_rel(rel)
                if r.lower() == "skill.md" or os.path.splitext(r)[1].lower() in BLOCKED_EXTS:
                    continue
                clean[r] = bytes(data)
            tmp = os.path.join(skills_dir(tenant), f".{name}.partial")
            shutil.rmtree(tmp, ignore_errors=True)
            try:
                os.makedirs(tmp)
                with open(os.path.join(tmp, "SKILL.md"), "w", encoding="utf-8") as f:
                    f.write(content)
                for r, data in clean.items():
                    dest = os.path.join(tmp, r)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as f:
                        f.write(data)
                os.replace(tmp, _folder(tenant, name))
            except Exception:
                shutil.rmtree(tmp, ignore_errors=True)
                raise
        else:
            _write_atomic(_flat(tenant, name), content)
        _READ_OK.add((tenant, name))
        _mirror(tenant, name, desc, body, extra=extra)
        return {"op": "install", "name": name, "chars": len(body), "files": len(files or {})}


def delete(tenant: str, name: str) -> dict:
    with _LOCK:
        name = validate_name(name)
        if (tenant, name) not in _READ_OK:       # a destructive op demands the read too
            raise SkillError(f"read skill {name!r} before deleting it")
        p = _path(tenant, name)
        if not os.path.exists(p):
            raise SkillError(f"skill {name!r} does not exist")
        if os.path.basename(p) == "SKILL.md":    # a folder skill goes with all its files
            shutil.rmtree(os.path.dirname(p), ignore_errors=True)
        else:
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
            folder = os.path.isfile(os.path.join(d, fn, "SKILL.md"))
            if not folder and not fn.endswith(".md"):
                continue
            try:
                fp = os.path.join(d, fn, "SKILL.md") if folder else os.path.join(d, fn)
                with open(fp, encoding="utf-8") as f:
                    raw = f.read()
                _, desc, body = parse_skill(raw)
                row = {"name": fn if folder else fn[:-3], "description": desc, "chars": len(body),
                       "enabled": _front_enabled(raw),
                       "updated_at": time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(fp)))}
                if folder:
                    row["folder"] = True
                out.append(row)
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
        extra = _extra_of(parse_front(raw)[0])
        _write_atomic(p, render(name, desc, body, enabled=bool(on), extra=extra))
        _mirror(tenant, name, desc, body, enabled=bool(on), extra=extra)
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
                if act not in ("list", "read", "read_file"):
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
                elif act == "read_file":
                    results.append(read_file(tenant, nm, str(op.get("path") or "")))
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
