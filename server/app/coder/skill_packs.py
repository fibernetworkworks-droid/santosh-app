"""HOOLA SKILL PACKS (v0.484.0) - the skills platform's shipping lanes: the seed library,
import/export, and the anonymised share shelf. Bigger than a static skills folder: skills
TRAVEL - in from files and packs, out to the shelf - and every hop is linted, redacted and
telemetry-marked.

  SEED      a first tenant opens the desk with a starter library (42 class-level skills under
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
PROG_STAMP = "skills:progpack:{}"       # its OWN once-ever stamp (the v0.492 pattern): the v0.495 PROG pack
SP_STAMP = "skills:sp:{}"               # its OWN once-ever stamp (v0.495): the superpowers lane, same once-ever law


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
        return sorted(f for f in SEED_DIR.glob("*.md")
                      if not f.name.startswith(("byox-", "prog-", "sp-")))
    except Exception:
        return []


def byox_files() -> list[Path]:
    """The Build-Your-Own-X pack (31 SKILL.md files, one per category)."""
    try:
        return sorted(SEED_DIR.glob("byox-*.md"))
    except Exception:
        return []


def prog_files() -> list[Path]:
    """The PROG pack (v0.495): the vetted-library registry + the windows script lane."""
    try:
        return sorted(SEED_DIR.glob("prog-*.md"))
    except Exception:
        return []


def sp_files() -> list[Path]:
    """The obra/superpowers pack (15 distilled seeds; verbatim archive under upstream/)."""
    try:
        return sorted(SEED_DIR.glob("sp-*.md"))
    except Exception:
        return []


def seed_sp(tenant: str) -> dict:
    """Copy the superpowers pack into a tenant once ever, create-if-missing. Own stamp,
    same shape as seed_byox (v0.495): a new library reaches already-seeded tenants too."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "sp_enabled", True):
            return {"sp_seeded": 0}
    except Exception:
        return {"sp_seeded": 0}
    if not _seed_armed():
        return {"sp_seeded": 0}
    stamp = SP_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"sp_seeded": 0}
    except Exception:
        return {"sp_seeded": 0}
    wrote = 0
    for f in sp_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body)
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("sp seed of %s failed for %s", f.name, tenant)
    try:
        store.mark_consumed(stamp)
    except Exception:
        pass
    if wrote:
        log.info("sp seed: %d skills into %s", wrote, tenant)
    return {"sp_seeded": wrote}


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


def seed_progpack(tenant: str) -> dict:
    """Copy the PROG pack into a tenant once ever, create-if-missing (the seed_byox twin).
    Its own stamp: tenants that already consumed seed AND byox still get this pack."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "progpack_enabled", True):
            return {"prog_seeded": 0}
    except Exception:
        return {"prog_seeded": 0}
    if not _seed_armed():
        return {"prog_seeded": 0}
    stamp = PROG_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"prog_seeded": 0}
    except Exception:
        return {"prog_seeded": 0}
    wrote = 0
    for f in prog_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body)
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("prog seed of %s failed for %s", f.name, tenant)
    try:
        store.mark_consumed(stamp)
    except Exception:
        pass
    if wrote:
        log.info("prog seed: %d skills into %s", wrote, tenant)
    return {"prog_seeded": wrote}


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


def import_skills(tenant: str, items, surface: str = "import") -> dict:
    """Linted create-if-missing batch. Never overwrites: a name that exists reports 'exists'."""
    if not isinstance(items, list) or not items:
        return {"error": "items must be a non-empty array (markdown strings or {name, description, body})."}
    if len(items) > IMPORT_MAX:
        return {"error": f"import is capped at {IMPORT_MAX} skills per call."}
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
            with open(os.path.join(skills_store.skills_dir(tenant), row["name"] + ".md"),
                      encoding="utf-8") as f:
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
        p = os.path.join(skills_store.skills_dir(tenant), name + ".md")
        with open(p, encoding="utf-8") as f:
            raw = f.read()
        _, desc, body = parse_skill(raw)
    except (SkillError, OSError):
        return {"error": f"skill {name!r} does not exist"}
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
        p = os.path.join(skills_store.skills_dir(tenant), name + ".md")
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
    """Test isolation hook (parity with the other coder modules; stateless beyond the vault)."""
    return None
