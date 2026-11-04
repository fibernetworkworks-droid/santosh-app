"""HOOLA SKILL PACKS (v0.484.0) - the skills platform's shipping lanes: the seed library,
import/export, and the anonymised share shelf. Bigger than a static skills folder: skills
TRAVEL - in from files and packs, out to the shelf - and every hop is linted, redacted and
telemetry-marked.

  SEED      a first tenant opens the desk with a starter library (10 class-level skills under
            skillpack/, copied create-if-missing, exactly-once via the consumed stamp,
            coder_skills_seed gate). Files are the source of truth - seeds are ordinary
            SKILL.md files the owner can edit or delete like any other.
  IMPORT    raw SKILL.md markdown (Claude Code / ClawHub shape: the same `---` frontmatter with
            name + description) or JSON rows, linted through the SAME skills_store funnel,
            create-if-missing, <=25 per call. Nothing is ever overwritten by an import - the
            owner's skills are hers; a collision reports 'exists'.
  EXPORT    the tenant's skills as JSON rows (the same shape import takes) - her library is
            never locked in.
  SHARE     the auto-anonymised lane with the owner's hand on the tap:
              the curator NOMINATES (a skill with enough real reads - the telemetry's evidence),
              the body is RE-REDACTED at nomination and again at publish (redact.redact_secrets
              + strip_private - a memory file is a wire, the shelf is a wire),
              the owner CONFIRMS on the desk (publish or reject - nothing leaves the tenant
              without her tap, the same law as money),
              the published pack lands in the RESERVED tenant `_packs` with NO trace of the
              source tenant (no name, no row, nothing - the shelf is anonymous by construction),
              any avatar INSTALLS from the shelf into its own tenant (create-if-missing,
              telemetry kind='installed').
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from . import redact, skills_store, store
from .skills_store import SkillError, parse_skill, validate

log = logging.getLogger("coder.skillpacks")

PACK_TENANT = "_packs"                  # the reserved shelf tenant (never a real login)
SEED_DIR = Path(__file__).parent / "skillpack"
IMPORT_MAX = 25
SEED_STAMP = "skills:seeded:{}"
SHARE_STAMP = "skills:shared:{}"
BYOX_STAMP = "skills:byox:{}"           # its OWN once-ever stamp: tenants already seeded still get the BYOX pack


# ---------------------------------------------------------------- helpers

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _clean(text: str) -> str:
    """The two privacy passes every leaving body takes (the memory-file-is-a-wire law)."""
    return redact.redact_secrets(redact.strip_private(str(text or "")))


def _lint_row(name: str, desc: str, body: str) -> tuple[str, str, str]:
    n = skills_store.validate_name(name)
    d, b = validate(desc, body)
    return n, d, b


def _share_armed() -> bool:
    try:
        from ..config import get_settings
        st = get_settings()
        return bool(getattr(st, "coder_enabled", True) and getattr(st, "coder_skills", True)
                    and getattr(st, "coder_skills_share", True))
    except Exception:
        return False


def _seed_armed() -> bool:
    try:
        from ..config import get_settings
        st = get_settings()
        return bool(getattr(st, "coder_enabled", True) and getattr(st, "coder_skills", True)
                    and getattr(st, "coder_skills_seed", True))
    except Exception:
        return False


def _min_reads() -> int:
    try:
        from ..config import get_settings
        return max(1, int(getattr(get_settings(), "coder_skills_share_min_reads", 3) or 3))
    except Exception:
        return 3


def _max_pending() -> int:
    try:
        from ..config import get_settings
        return max(1, int(getattr(get_settings(), "coder_skills_share_max_pending", 10) or 10))
    except Exception:
        return 10


# ---------------------------------------------------------------- SEED

def seed_files() -> list[Path]:
    """The shipped starter library (SKILL.md files beside this module)."""
    try:
        return sorted(f for f in SEED_DIR.glob("*.md") if not f.name.startswith("byox-"))
    except Exception:
        return []


def byox_files() -> list[Path]:
    """The Build-Your-Own-X pack (31 SKILL.md files, one per category)."""
    try:
        return sorted(SEED_DIR.glob("byox-*.md"))
    except Exception:
        return []


def seed_byox(tenant: str) -> dict:
    """Copy the BYOX pack into a tenant once ever, create-if-missing. Independent of seed()'s stamp."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "byox_enabled", True):
            return {"byox_seeded": 0}
    except Exception:
        return {"byox_seeded": 0}
    if not _seed_armed():
        return {"byox_seeded": 0}
    stamp = BYOX_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"byox_seeded": 0}
    except Exception:
        return {"byox_seeded": 0}
    wrote = 0
    for f in byox_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body)
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("byox seed of %s failed for %s", f.name, tenant)
    try:
        store.mark_consumed(stamp)
    except Exception:
        pass
    if wrote:
        log.info("byox seed: %d skills into %s", wrote, tenant)
    return {"byox_seeded": wrote}


CLAUDE_DIR = SEED_DIR / "claude"
CLAUDE_STAMP = "skills:claude:{}"        # its OWN once-ever stamp: older tenants still get this pack


def claude_dirs() -> list[Path]:
    """The Anthropic example skills Hoola ships (each a folder with SKILL.md + LICENSE.txt + resources)."""
    try:
        return sorted(d for d in CLAUDE_DIR.iterdir() if (d / "SKILL.md").is_file())
    except Exception:
        return []


def seed_claude(tenant: str) -> dict:
    """Install the shipped Claude-format skills into a tenant once ever, create-if-missing (a skill she
    already has, edited or deleted-and-recreated, is never touched). They go through the SAME import
    lane as a zip: Claude's limits, `imported: true`, the folder kept with its LICENSE.txt."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "claude_skills_enabled", True):
            return {"claude_seeded": 0}
    except Exception:
        return {"claude_seeded": 0}
    if not _seed_armed():
        return {"claude_seeded": 0}
    stamp = CLAUDE_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"claude_seeded": 0}
    except Exception:
        return {"claude_seeded": 0}
    wrote = 0
    for d in claude_dirs():
        try:
            front, body = skills_store.parse_front((d / "SKILL.md").read_text(encoding="utf-8"))
            files = {}
            for f in sorted(d.rglob("*")):
                if f.is_file() and f.name != "SKILL.md":
                    files[f.relative_to(d).as_posix()] = f.read_bytes()
            res = skills_store.install(tenant, str(front.get("name") or d.name),
                                       str(front.get("description") or ""), body, extra=front, files=files)
            store.skill_use_mark(tenant, res["name"], "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue                       # already exists: hers stays
        except Exception:
            log.exception("claude seed of %s failed for %s", d.name, tenant)
    try:
        store.mark_consumed(stamp)
    except Exception:
        pass
    if wrote:
        log.info("claude skill seed: %d skills into %s", wrote, tenant)
    return {"claude_seeded": wrote}


_SEEDED: set[tuple[str, str]] = set()      # (coder root, tenant) already checked in this process


def seed_all(tenant: str) -> dict:
    """Every shipped pack for a tenant, exactly-once each (their own stamps), fail-open. Called on a user's
    FIRST memory-block build (chat turn or call start) and by the Skill Desk, so a user who never opens the
    desk still gets her skills. Internal tenants (a leading '_': the shelf, the cards) are never auto-seeded.
    After one successful pass the process remembers it, so later turns pay nothing."""
    t = str(tenant or "")
    if not t or t.startswith("_"):
        return {}
    try:
        key = (os.path.realpath(store.root()), t)
    except Exception:
        return {}
    if key in _SEEDED or not _seed_armed():
        return {}
    out: dict = {}
    for fn in (seed, seed_byox, seed_claude):
        try:
            out.update(fn(t))
        except Exception:
            log.exception("%s failed for %s", fn.__name__, t)
            return out                       # not remembered: the next turn tries again
    _SEEDED.add(key)
    return out


def seed(tenant: str) -> dict:
    """Copy the starter library into a tenant once ever (create-if-missing, stamped)."""
    if not _seed_armed():
        return {"seeded": 0}
    stamp = SEED_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"seeded": 0}
    except Exception:
        return {"seeded": 0}
    wrote = 0
    for f in seed_files():
        try:
            raw = f.read_text(encoding="utf-8")
            name, desc, body = parse_skill(raw)
            if not name:
                name = f.stem
            skills_store.create(tenant, name, desc, body)   # create-if-missing: hers win
            store.skill_use_mark(tenant, name, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue                       # already exists (or lint): her file stays
        except Exception:
            log.exception("seed of %s failed for %s", f.name, tenant)
    try:
        store.mark_consumed(stamp)
    except Exception:
        pass
    if wrote:
        log.info("skill seed: %d starters into %s", wrote, tenant)
    return {"seeded": wrote}


# ---------------------------------------------------------------- IMPORT / EXPORT

def _rows_from(items) -> list[tuple[str, str, str]]:
    """Import payload -> lintable rows. Dict rows are {name, description, body}; string rows are
    raw SKILL.md markdown (the Claude Code / ClawHub file shape - same frontmatter keys)."""
    rows: list[tuple[str, str, str]] = []
    for it in items:
        if isinstance(it, str):
            name, desc, body = parse_skill(it)
            if not name:
                raise SkillError("markdown item without frontmatter name")
            rows.append((name, desc, body))
        elif isinstance(it, dict):
            rows.append((str(it.get("name") or ""), str(it.get("description") or ""),
                         str(it.get("body") or "")))
        else:
            raise SkillError("each item is an object or a markdown string")
    return rows


def _import_full(tenant: str, items, surface: str) -> dict:
    """The Claude-format lane (v0.494): raw SKILL.md strings under Claude's own limits, stamped
    `imported: true`, the extra frontmatter kept. Create-if-missing, same report shape."""
    created, skipped, errors = [], [], []
    for it in items:
        name = ""
        try:
            if isinstance(it, str):
                front, body = skills_store.parse_front(it)
                name, desc = str(front.get("name") or ""), str(front.get("description") or "")
            elif isinstance(it, dict):
                front, body = it, str(it.get("body") or "")
                name, desc = str(it.get("name") or ""), str(it.get("description") or "")
            else:
                raise SkillError("each item is an object or a markdown string")
            if not name:
                raise SkillError("markdown item without frontmatter name")
            res = skills_store.install(tenant, name, desc, body, extra=front)
            created.append(res["name"])
            store.skill_use_mark(tenant, res["name"], "installed", surface=surface)
        except SkillError as e:
            msg = str(e)
            if "already exists" in msg:
                skipped.append({"name": name[:80], "reason": msg})
            else:
                errors.append({"name": name[:80], "error": msg})
        except Exception as e:                                   # noqa: BLE001
            errors.append({"name": name[:80], "error": f"{type(e).__name__}: {e}"})
    return {"ok": True, "created": created, "skipped": skipped, "errors": errors}


ZIP_FILES_MAX = 200
ZIP_TOTAL_MAX = 8_000_000
ZIP_FILE_MAX = 1_000_000
ZIP_BYTES_MAX = 10_000_000


def import_zip(tenant: str, data: bytes, surface: str = "zip") -> dict:
    """One skill from a .zip (the claude.ai / Claude Code shape: SKILL.md at the root or inside ONE
    top folder, plus its reference/ examples/ scripts/ files). Safe extraction: no '..', no
    absolute paths, no symlinks, no executables, capped count/size (the declared size is not
    trusted - every file is read with a hard limit). Stored, never executed. Never overwrites."""
    import io
    import zipfile
    if not data or len(data) > ZIP_BYTES_MAX:
        return {"error": f"zip must be 1 byte to {ZIP_BYTES_MAX // 1_000_000} MB."}
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        infos = [i for i in zf.infolist() if not i.is_dir()]
    except zipfile.BadZipFile:
        return {"error": "not a zip file."}
    entries: dict[str, zipfile.ZipInfo] = {}
    for i in infos:
        n = i.filename.replace("\\", "/")
        if n.startswith("__MACOSX/") or n.rsplit("/", 1)[-1] in (".DS_Store", "Thumbs.db"):
            continue
        if (i.external_attr >> 16) & 0o170000 == 0o120000:
            return {"error": f"zip holds a symbolic link ({n[:80]!r}) - refused."}
        try:
            skills_store.safe_rel(n)
        except SkillError as e:
            return {"error": f"zip path refused: {e}"}
        entries[n] = i
    if len(entries) > ZIP_FILES_MAX or sum(i.file_size for i in entries.values()) > ZIP_TOTAL_MAX:
        return {"error": f"zip is too big (max {ZIP_FILES_MAX} files / {ZIP_TOTAL_MAX // 1_000_000} MB)."}
    roots = [n for n in entries if n.rsplit("/", 1)[-1] == "SKILL.md" and n.count("/") <= 1]
    if len(roots) != 1:
        return {"error": "zip must hold exactly one skill: a SKILL.md at the root or inside one top folder."}
    prefix = roots[0][:-len("SKILL.md")]

    def _read(info) -> bytes:
        with zf.open(info) as f:
            b = f.read(ZIP_FILE_MAX + 1)
        if len(b) > ZIP_FILE_MAX:
            raise SkillError(f"{info.filename[:80]!r} is over {ZIP_FILE_MAX // 1000} KB")
        return b

    try:
        raw = _read(entries[roots[0]]).decode("utf-8")
        front, body = skills_store.parse_front(raw)
        name = str(front.get("name") or prefix.strip("/"))
        files = {n[len(prefix):]: _read(i) for n, i in entries.items()
                 if n.startswith(prefix) and n != roots[0]}
        res = skills_store.install(tenant, name, str(front.get("description") or ""), body,
                                   extra=front, files=files)
    except UnicodeDecodeError:
        return {"error": "SKILL.md is not UTF-8 text."}
    except SkillError as e:
        return {"error": str(e)}
    store.skill_use_mark(tenant, res["name"], "installed", surface=surface)
    return {"ok": True, "created": [res["name"]], "files": res["files"]}


def export_zip(tenant: str, name: str) -> bytes | None:
    """One skill as a .zip (SKILL.md at the root + its bundled files) - the same shape import_zip
    takes, so a round-trip loses nothing. None when the skill does not exist."""
    import io
    import zipfile
    try:
        p = skills_store.raw_path(tenant, name)
        if not os.path.isfile(p):
            return None
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(p, "SKILL.md")
            if skills_store.is_folder(tenant, name):
                base = os.path.dirname(p)
                for rel in skills_store.files_of(tenant, name):
                    z.write(os.path.join(base, rel), rel)
        return buf.getvalue()
    except (SkillError, OSError):
        return None


def import_skills(tenant: str, items, surface: str = "import", full: bool = False) -> dict:
    """Linted create-if-missing batch. Never overwrites: a name that exists reports 'exists'.
    full=True is the Claude-format lane (Claude's limits, `imported: true`, extra frontmatter kept)."""
    if not isinstance(items, list) or not items:
        return {"error": "items must be a non-empty array (markdown strings or {name, description, body})."}
    if len(items) > IMPORT_MAX:
        return {"error": f"import is capped at {IMPORT_MAX} skills per call."}
    if full:
        return _import_full(tenant, items, surface)
    try:
        rows = _rows_from(items)
    except SkillError as e:
        return {"error": str(e)}
    created, skipped, errors = [], [], []
    for name, desc, body in rows:
        try:
            n, d, b = _lint_row(name, desc, body)
        except SkillError as e:
            errors.append({"name": str(name)[:80], "error": str(e)})
            continue
        try:
            skills_store.create(tenant, n, d, b)
            created.append(n)
            store.skill_use_mark(tenant, n, "installed", surface=surface)
        except SkillError as e:
            skipped.append({"name": n, "reason": str(e)})
        except Exception as e:                                   # noqa: BLE001 - one bad row never sinks the batch
            errors.append({"name": n, "error": f"{type(e).__name__}: {e}"})
    return {"ok": True, "created": created, "skipped": skipped, "errors": errors}


def export_skills(tenant: str, names=None) -> dict:
    """The tenant's library as JSON rows (raw files read directly - export never pollutes the
    follow telemetry). Same shape import takes, so a round-trip is a no-op."""
    out = []
    want = {str(n) for n in names} if names else None
    for row in skills_store.listing(tenant):
        if want is not None and row["name"] not in want:
            continue
        try:
            with open(skills_store.raw_path(tenant, row["name"]), encoding="utf-8") as f:
                _, desc, body = parse_skill(f.read())
            out.append({"name": row["name"], "description": desc, "body": body,
                        "enabled": bool(row.get("enabled", True))})
        except Exception:
            continue
    return {"ok": True, "exported_at": _now(), "skills": out}


# ---------------------------------------------------------------- SHARE: nominate -> decide -> shelf

def share_nominate(tenant: str, name: str, note: str = "") -> dict:
    """The curator's nomination: a much-read class-level skill proposed for the shelf. The body
    is re-redacted BEFORE anything is stored; nothing leaves the tenant here - this only rows
    the proposal into the owner's ledger."""
    if not _share_armed():
        return {"error": "sharing is switched off (coder_skills_share)"}
    name = name.strip()
    try:
        name = skills_store.validate_name(name)
        p = skills_store.raw_path(tenant, name)
        with open(p, encoding="utf-8") as f:
            raw = f.read()
        _, desc, body = parse_skill(raw)
    except (SkillError, OSError):
        return {"error": f"skill {name!r} does not exist"}
    if skills_store._truthy(skills_store.parse_front(raw)[0].get("imported")):
        return {"error": "an imported skill is never nominated (its licence travels with its source)"}
    if skills_store.is_folder(tenant, name) and skills_store.files_of(tenant, name):
        return {"error": "a skill with bundled files cannot go on the shelf yet"}
    reads = store.skill_reads(tenant, name)
    if reads < _min_reads():
        return {"error": f"only {reads} read(s) - a skill needs {_min_reads()} real reads before "
                         f"it can be nominated (the telemetry is the evidence)"}
    try:
        if skills_store.is_parked(tenant, name):
            return {"error": "a parked skill is never nominated"}
    except SkillError:
        return {"error": f"skill {name!r} does not exist"}
    pending = store.skill_share_rows(tenant, "pending")
    if len(pending) >= _max_pending():
        return {"error": f"{len(pending)} nominations already wait for the owner (cap {_max_pending()})"}
    if any(r["name"] == name for r in pending):
        return {"error": f"skill {name!r} is already pending"}
    try:
        store.ensure()
        with store.db(write=True) as c:
            old = c.execute("SELECT status FROM skill_shares WHERE name=? AND tenant=?",
                            (name, str(tenant or ""))).fetchone()
            if old is None:
                c.execute("INSERT INTO skill_shares(name, tenant, status, note, created_at) "
                          "VALUES (?,?,'pending',?,?)",
                          (name, str(tenant or ""), _clean(note)[:300], _now()))
            elif old["status"] in ("pending", "rejected"):
                c.execute("UPDATE skill_shares SET status='pending', note=?, created_at=?, "
                          "decided_at='' WHERE name=? AND tenant=?",
                          (_clean(note)[:300], _now(), name, str(tenant or "")))
            else:
                return {"error": f"skill {name!r} was already published"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "name": name, "reads": reads, "status": "pending"}


def share_decide(tenant: str, name: str, approve: bool, note: str = "") -> dict:
    """THE TAP. approve=True publishes the REDACTED body into the reserved `_packs` shelf with
    no trace of the source tenant; approve=False closes the nomination. Everything else refuses."""
    if not _share_armed():
        return {"error": "sharing is switched off (coder_skills_share)"}
    try:
        name = skills_store.validate_name(name)
    except SkillError as e:
        return {"error": str(e)}
    rows = {r["name"]: r for r in store.skill_share_rows(tenant)}
    row = rows.get(name)
    if not row:
        return {"error": f"no share nomination for {name!r}"}
    if row["status"] != "pending":
        return {"error": f"nomination is already {row['status']}"}
    now = _now()
    if not approve:
        with store.db(write=True) as c:
            c.execute("UPDATE skill_shares SET status='rejected', note=?, decided_at=? "
                      "WHERE name=? AND tenant=? AND status='pending'",
                      (_clean(note)[:300], now, name, str(tenant or "")))
        return {"ok": True, "name": name, "status": "rejected"}
    # publish: read, redact, lint, write to the shelf (the source tenant is never recorded)
    try:
        p = skills_store.raw_path(tenant, name)
        with open(p, encoding="utf-8") as f:
            raw = f.read()
        _, desc, body = parse_skill(raw)
        desc, body = _clean(desc), _clean(body)
        shelf_path = os.path.join(skills_store.skills_dir(PACK_TENANT), name + ".md")
        if os.path.exists(shelf_path):
            with open(shelf_path, encoding="utf-8") as f:
                _, s_desc, s_body = parse_skill(f.read())
            if s_body.strip() == body.strip():
                pass                                     # the same pack is already on the shelf
            else:
                return {"error": f"a different pack named {name!r} is already on the shelf - "
                                 f"rename your skill to publish it"}
        else:
            skills_store.create(PACK_TENANT, name, desc, body)
        store.skill_use_mark(tenant, name, "published", surface="shelf")
    except SkillError as e:
        return {"error": f"publish refused: {e}"}
    except Exception as e:                                   # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}
    with store.db(write=True) as c:
        c.execute("UPDATE skill_shares SET status='published', note=?, decided_at=? "
                  "WHERE name=? AND tenant=? AND status='pending'",
                  (_clean(note)[:300], now, name, str(tenant or "")))
    return {"ok": True, "name": name, "status": "published"}


def packs() -> list[dict]:
    """The shelf: every published pack, anonymous by construction (a pack file carries only the
    skill's own frontmatter - the source tenant exists in no row, no file, nowhere)."""
    return skills_store.listing(PACK_TENANT)


def pack_read(name: str) -> dict | None:
    try:
        name = skills_store.validate_name(name)
    except SkillError:
        return None
    p = os.path.join(skills_store.skills_dir(PACK_TENANT), name + ".md")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        _, desc, body = parse_skill(f.read())
    return {"name": name, "description": desc, "body": body}


def pack_install(tenant: str, name: str) -> dict:
    """One shelf pack into the tenant's own library (create-if-missing - her file wins)."""
    if not _share_armed():
        return {"error": "sharing is switched off (coder_skills_share)"}
    row = pack_read(name)
    if not row:
        return {"error": f"pack {name!r} is not on the shelf"}
    try:
        skills_store.create(tenant, row["name"], row["description"], row["body"])
    except SkillError as e:
        return {"error": str(e)}
    store.skill_use_mark(tenant, row["name"], "installed", surface="pack")
    return {"ok": True, "name": row["name"], "installed": True}


def reset_for_tests() -> None:
    """Test isolation hook: forget which tenants this process already seeded."""
    _SEEDED.clear()
