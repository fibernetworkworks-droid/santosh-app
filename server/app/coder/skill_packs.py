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
FE_STAMP = "skills:fepack:{}"           # its OWN once-ever stamp (the v0.492 pattern): the FE pack, same once-ever law
CS_STAMP = "skills:cspack:{}"           # its OWN once-ever stamp (the v0.492 pattern): the CS pack, same once-ever law
MG_STAMP = "skills:magicpack:{}"        # its OWN once-ever stamp (the v0.492 pattern): the 21st/Magic UI pack, same once-ever law
BD_STAMP = "skills:bdpack:{}"           # its OWN once-ever stamp (the v0.492 pattern): the Big Data pack, same once-ever law
CR_STAMP = "skills:crewpack:{}"         # its OWN once-ever stamp (the v0.492 pattern): the crewAI pack, same once-ever law
TH_STAMP = "skills:thpack:{}"           # its OWN once-ever stamp (the v0.492 pattern): the Theory pack, same once-ever law
ED_STAMP = "skills:edpack:{}"           # its OWN once-ever stamp (the v0.492 pattern): the Editors pack, same once-ever law
GA_STAMP = "skills:gapack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Gaming pack, same once-ever law
DE_STAMP = "skills:devpack:{}"   # its OWN once-ever stamp (the v0.492 pattern): the Dev Environment pack, same once-ever law
EN_STAMP = "skills:enpack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Entertainment pack, same once-ever law
DB_STAMP = "skills:dbpack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Databases pack, same once-ever law
ME_STAMP = "skills:mepack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Media pack, same once-ever law
LE_STAMP = "skills:lepack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Learn pack, same once-ever law
SE_STAMP = "skills:secpack:{}"   # its OWN once-ever stamp (the v0.492 pattern): the Security pack, same once-ever law
CM_STAMP = "skills:cmpack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the CMS pack, same once-ever law
HA_STAMP = "skills:hapack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Hardware pack, same once-ever law
BU_STAMP = "skills:bupack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Business pack, same once-ever law
WO_STAMP = "skills:wopack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Work pack, same once-ever law
NE_STAMP = "skills:nepack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Networking pack, same once-ever law
DC_STAMP = "skills:dcpack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Decentralized pack, same once-ever law
HS_STAMP = "skills:hspack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Health pack, same once-ever law
EV_STAMP = "skills:evpack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Events pack, same once-ever law
TE_STAMP = "skills:tepack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Testing pack, same once-ever law
MI_STAMP = "skills:mipack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Miscellaneous pack, same once-ever law
RE_STAMP = "skills:repack:{}"    # its OWN once-ever stamp (the v0.492 pattern): the Related pack, same once-ever law


# ---------------------------------------------------------------- helpers

WHEN_STAMP = "skills:when:{}"      # v0.753: <digest of the shipped trigger lines>:<tenant> - re-runs when a line changes


def _when_of(f: Path) -> dict:
    """v0.753: a shipped pack file's `when_to_use` (the plain words people type), for the strict create lane."""
    try:
        front, _ = skills_store.parse_front(f.read_text(encoding="utf-8"))
        w = str(front.get("when_to_use") or "").strip()
        return {"when_to_use": w} if w else {}
    except Exception:
        return {}


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
                      if not f.name.startswith(("byox-", "prog-", "sp-", "fe-", "cs-", "mg-", "bd-", "cr-", "th-", "ed-",
                      "ga-", "de-", "en-", "db-", "me-", "le-", "se-", "cm-", "ha-", "bu-",
                      "wo-", "ne-", "dc-", "hs-", "ev-", "te-", "mi-", "re-")))
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


def fe_files() -> list[Path]:
    """The FE pack (the awesome Front-End read): the HyperFrames template packs + campaign
    email templates + the Hoola UI kit tokens."""
    try:
        return sorted(SEED_DIR.glob("fe-*.md"))
    except Exception:
        return []


def cs_files() -> list[Path]:
    """The CS pack (the awesome Computer Science read): the zoo expansion radar + the
    operator loop's dialogue/QA patterns."""
    try:
        return sorted(SEED_DIR.glob("cs-*.md"))
    except Exception:
        return []


def mg_files() -> list[Path]:
    """The MAGIC pack (v0.512, the 21st-dev/magic-mcp read): the 21st.dev UI skill -
    search-first over the catalog, the generate entitlement law, the family laws."""
    try:
        return sorted(SEED_DIR.glob("mg-*.md"))
    except Exception:
        return []


def bd_files() -> list[Path]:
    """The Big Data pack (the awesome Big Data read): the public-dataset eval
    benchmarks for quality regression + the campaign-graph analytics."""
    try:
        return sorted(SEED_DIR.glob("bd-*.md"))
    except Exception:
        return []


def cr_files() -> list[Path]:
    """The crewAI pack (v0.514, the crewAIInc/crewAI read): when to run a crew, how to
    shape roles/tasks/guardrails, the three-door routing (delegate vs crew vs dhara)."""
    try:
        return sorted(SEED_DIR.glob("cr-*.md"))
    except Exception:
        return []


def th_files() -> list[Path]:
    """The Theory pack (the awesome Theory read, v0.547): the vision-lane syllabus
    (awesome-vlm-architectures - screenshot->action, Hoola's PC operator IS one)
    + the agent-architecture research loop (awesome-agi-cocosci - read, probe,
    ledger, adopt)."""
    try:
        return sorted(SEED_DIR.glob("th-*.md"))
    except Exception:
        return []


def ed_files() -> list[Path]:
    """The Editors pack (the awesome Editors read, v0.548): the VS Code cockpit
    (palette first, ax tree, never pixels) + the Neovim cockpit (modal grammar,
    buffers, key lane) - drive Hoola from inside the IDE, editors are already
    semantically controllable via ax_*."""
    try:
        return sorted(SEED_DIR.glob("ed-*.md"))
    except Exception:
        return []


def ga_files() -> list[Path]:
    """The Gaming pack (the awesome Gaming read, v0.549): the game-dev syllabus (awesome-godot + awesome-flame), the Steam/Deck launcher recipes, the community home (samudaay)."""
    try:
        return sorted(SEED_DIR.glob("ga-*.md"))
    except Exception:
        return []


def de_files() -> list[Path]:
    """The Dev Environment pack (v0.561): the naya-PC routine - awesome-cli-apps + awesome-dotfiles + awesome-shell as one vetted bundle, visible installs only."""
    try:
        return sorted(SEED_DIR.glob("de-*.md"))
    except Exception:
        return []


def en_files() -> list[Path]:
    """The Entertainment pack (v0.561): the daily-brief routine over the awesome-podcasts + awesome-newsletters catalogs."""
    try:
        return sorted(SEED_DIR.glob("en-*.md"))
    except Exception:
        return []


def db_files() -> list[Path]:
    """The Databases pack (v0.561): DB GUIs over the ax tree (the awesome-db-tools kit) + the SQLite->Postgres scale path with printed row proof."""
    try:
        return sorted(SEED_DIR.glob("db-*.md"))
    except Exception:
        return []


def me_files() -> list[Path]:
    """The Media pack (v0.549, the content goldmine): the awesome-stock-resources legal asset library, the fonts/icons typography laws, the ffmpeg recipe numbers."""
    try:
        return sorted(SEED_DIR.glob("me-*.md"))
    except Exception:
        return []


def le_files() -> list[Path]:
    """The Learn pack (v0.561): the mentor lane - awesome-roadmaps curated into mem, a daily study routine, a printed progress ledger."""
    try:
        return sorted(SEED_DIR.glob("le-*.md"))
    except Exception:
        return []


def se_files() -> list[Path]:
    """The Security pack (v0.561): the prompt-injection adversarial suite (attack our own prompts first) + the appsec hardening checklist with the BLOCKED law codified."""
    try:
        return sorted(SEED_DIR.glob("se-*.md"))
    except Exception:
        return []


def cm_files() -> list[Path]:
    """The CMS pack (v0.561): the campaign auto-publish lane - Hoola CMS first, the WP API next, the ax-driven admin UI last; approval + consent laws."""
    try:
        return sorted(SEED_DIR.glob("cm-*.md"))
    except Exception:
        return []


def ha_files() -> list[Path]:
    """The Hardware pack (v0.561): the Pi home-agent path (awesome-raspberry-pi) - one Pi, one job, then scale on printed proof."""
    try:
        return sorted(SEED_DIR.glob("ha-*.md"))
    except Exception:
        return []


def bu_files() -> list[Path]:
    """The Business pack (v0.561): the Places-to-Post target ledger + the billing/BYOK accounting lane (ai_kharcha, tally, sheets - all printed)."""
    try:
        return sorted(SEED_DIR.glob("bu-*.md"))
    except Exception:
        return []


def wo_files() -> list[Path]:
    """The Work pack (v0.561): ChatOps from a chat (awesome-slack shapes, same approval laws) + the morning task triage (the brief's faisla)."""
    try:
        return sorted(SEED_DIR.glob("wo-*.md"))
    except Exception:
        return []


def ne_files() -> list[Path]:
    """The Networking pack (v0.561): the diagnostics ladder from pc_status down to lab-only PCAP/Scapy, every rung printed."""
    try:
        return sorted(SEED_DIR.glob("ne-*.md"))
    except Exception:
        return []


def dc_files() -> list[Path]:
    """The Decentralized pack (v0.561): the no-blockchain stance kept - only the Tor/privacy outside-view angle on our own endpoints."""
    try:
        return sorted(SEED_DIR.glob("dc-*.md"))
    except Exception:
        return []


def hs_files() -> list[Path]:
    """The Health pack (v0.561): wellbeing guardrails in routines - break reminders, gentle one-time night nags; non-core by design."""
    try:
        return sorted(SEED_DIR.glob("hs-*.md"))
    except Exception:
        return []


def ev_files() -> list[Path]:
    """The Events pack (v0.561): the event radar - tech-event/CFP watch into calendar, free-slot check first, approval on money."""
    try:
        return sorted(SEED_DIR.glob("ev-*.md"))
    except Exception:
        return []


def te_files() -> list[Path]:
    """The Testing pack (v0.561): the web-E2E plan - Playwright + k6 + HyperFrames golden-frame diff, lab-first, printed numbers."""
    try:
        return sorted(SEED_DIR.glob("te-*.md"))
    except Exception:
        return []


def mi_files() -> list[Path]:
    """The Misc pack (v0.549, the biggest catalog): the self-host lens + free-for-dev finder + the personas/research/metrics/regex lanes, all printed."""
    try:
        return sorted(SEED_DIR.glob("mi-*.md"))
    except Exception:
        return []


def re_files() -> list[Path]:
    """The Related pack (v0.561): Hoola's own awesome-search over the ingested index (the awesomelists.top pattern), fetched-date on every row."""
    try:
        return sorted(SEED_DIR.glob("re-*.md"))
    except Exception:
        return []


def pack_files_all() -> list[Path]:
    """Every prefixed pack lane in one list - the 28 pack prefixes (v0.561)."""
    out: list[Path] = []
    for pref in ("byox-", "prog-", "sp-", "fe-", "cs-", "mg-", "bd-", "cr-", "th-", "ed-",
                 "ga-", "de-", "en-", "db-", "me-", "le-", "se-", "cm-", "ha-", "bu-",
                 "wo-", "ne-", "dc-", "hs-", "ev-", "te-", "mi-", "re-"):
        try:
            out.extend(sorted(SEED_DIR.glob(pref + "*.md")))
        except Exception:
            continue
    return out


def all_seed_files() -> list[Path]:
    """Everything the file pack seeders copy: the 11 starters + every prefixed pack
    lane. The desk-total pins ride this ONE list (v0.561) - still drift-sensitive:
    any new .md in skillpack/ lands in exactly one of its two halves."""
    return seed_files() + pack_files_all()


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
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("byox seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("byox seed: %d skills into %s", wrote, tenant)
    return {"byox_seeded": wrote}


# FINAL CHECK: a pack seeder used to stamp itself "done for ever" even when every skill in it crashed on install -
# that tenant then never received the pack (the skills card found the Claude pack missing this way). A stamp is now
# consumed only when no install crashed; a crash leaves it open, so the next desk open / first turn retries.
_FAILED_STAMPS: set[str] = set()


def _consume(stamp: str) -> None:
    if stamp in _FAILED_STAMPS:
        _FAILED_STAMPS.discard(stamp)
        log.warning("skill pack %s had a failed install - left open to retry", stamp)
        return
    store.mark_consumed(stamp)


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
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("claude skill seed: %d skills into %s", wrote, tenant)
    return {"claude_seeded": wrote}


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
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("prog seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("prog seed: %d skills into %s", wrote, tenant)
    return {"prog_seeded": wrote}


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
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("sp seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("sp seed: %d skills into %s", wrote, tenant)
    return {"sp_seeded": wrote}


def seed_fepack(tenant: str) -> dict:
    """Copy the FE pack into a tenant once ever, create-if-missing (the seed_progpack twin).
    Its own stamp: tenants that already consumed seed AND byox AND prog still get this pack."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "fepack_enabled", True):
            return {"fe_seeded": 0}
    except Exception:
        return {"fe_seeded": 0}
    if not _seed_armed():
        return {"fe_seeded": 0}
    stamp = FE_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"fe_seeded": 0}
    except Exception:
        return {"fe_seeded": 0}
    wrote = 0
    for f in fe_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("fe seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("fe seed: %d skills into %s", wrote, tenant)
    return {"fe_seeded": wrote}


def seed_cspack(tenant: str) -> dict:
    """Copy the CS pack into a tenant once ever, create-if-missing (the seed_fepack twin).
    Its own stamp: tenants that already consumed seed AND byox AND prog AND sp AND fe still get this pack."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "cspack_enabled", True):
            return {"cs_seeded": 0}
    except Exception:
        return {"cs_seeded": 0}
    if not _seed_armed():
        return {"cs_seeded": 0}
    stamp = CS_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"cs_seeded": 0}
    except Exception:
        return {"cs_seeded": 0}
    wrote = 0
    for f in cs_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("cs seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("cs seed: %d skills into %s", wrote, tenant)
    return {"cs_seeded": wrote}


def seed_magicpack(tenant: str) -> dict:
    """Copy the MAGIC pack into a tenant once ever, create-if-missing (the seed_fepack twin,
    v0.512). Its own stamp: tenants that already consumed seed AND byox AND prog AND sp AND
    fe AND cs still get this pack. Discovered automatically by _pack_seeders (no seed_all edit)."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "magicpack_enabled", True):
            return {"mg_seeded": 0}
    except Exception:
        return {"mg_seeded": 0}
    if not _seed_armed():
        return {"mg_seeded": 0}
    stamp = MG_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"mg_seeded": 0}
    except Exception:
        return {"mg_seeded": 0}
    wrote = 0
    for f in mg_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("mg seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("mg seed: %d skills into %s", wrote, tenant)
    return {"mg_seeded": wrote}


def seed_bdpack(tenant: str) -> dict:
    """Copy the Big Data pack into a tenant once ever, create-if-missing (the seed_cspack twin).
    Its own stamp: tenants that already consumed seed AND byox AND prog AND sp AND fe AND cs AND mg
    still get this pack."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "bdpack_enabled", True):
            return {"bd_seeded": 0}
    except Exception:
        return {"bd_seeded": 0}
    if not _seed_armed():
        return {"bd_seeded": 0}
    stamp = BD_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"bd_seeded": 0}
    except Exception:
        return {"bd_seeded": 0}
    wrote = 0
    for f in bd_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("bd seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("bd seed: %d skills into %s", wrote, tenant)
    return {"bd_seeded": wrote}


def seed_crewpack(tenant: str) -> dict:
    """Copy the crewAI pack into a tenant once ever, create-if-missing (the seed_bdpack twin).
    Its own stamp: tenants that already consumed seed AND byox AND prog AND sp AND fe AND cs
    AND mg AND bd still get this pack."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "crewpack_enabled", True):
            return {"cr_seeded": 0}
    except Exception:
        return {"cr_seeded": 0}
    if not _seed_armed():
        return {"cr_seeded": 0}
    stamp = CR_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"cr_seeded": 0}
    except Exception:
        return {"cr_seeded": 0}
    wrote = 0
    for f in cr_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("cr seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("cr seed: %d skills into %s", wrote, tenant)
    return {"cr_seeded": wrote}


def seed_thpack(tenant: str) -> dict:
    """Copy the Theory pack into a tenant once ever, create-if-missing (the seed_crewpack twin).
    Its own stamp: tenants that already consumed seed AND byox AND prog AND sp AND fe AND cs
    AND mg AND bd AND cr still get this pack."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "thpack_enabled", True):
            return {"th_seeded": 0}
    except Exception:
        return {"th_seeded": 0}
    if not _seed_armed():
        return {"th_seeded": 0}
    stamp = TH_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"th_seeded": 0}
    except Exception:
        return {"th_seeded": 0}
    wrote = 0
    for f in th_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("th seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("th seed: %d skills into %s", wrote, tenant)
    return {"th_seeded": wrote}


def seed_edpack(tenant: str) -> dict:
    """Copy the Editors pack into a tenant once ever, create-if-missing (the seed_thpack twin).
    Its own stamp: tenants that already consumed seed AND byox AND prog AND sp AND fe AND cs
    AND mg AND bd AND cr AND th still get this pack."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "edpack_enabled", True):
            return {"ed_seeded": 0}
    except Exception:
        return {"ed_seeded": 0}
    if not _seed_armed():
        return {"ed_seeded": 0}
    stamp = ED_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"ed_seeded": 0}
    except Exception:
        return {"ed_seeded": 0}
    wrote = 0
    for f in ed_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("ed seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("ed seed: %d skills into %s", wrote, tenant)
    return {"ed_seeded": wrote}


def seed_gapack(tenant: str) -> dict:
    """Copy the Gaming pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "gapack_enabled", True):
            return {"ga_seeded": 0}
    except Exception:
        return {"ga_seeded": 0}
    if not _seed_armed():
        return {"ga_seeded": 0}
    stamp = GA_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"ga_seeded": 0}
    except Exception:
        return {"ga_seeded": 0}
    wrote = 0
    for f in ga_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("ga seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("ga seed: %d skills into %s", wrote, tenant)
    return {"ga_seeded": wrote}


def seed_devpack(tenant: str) -> dict:
    """Copy the Dev Environment pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "devpack_enabled", True):
            return {"de_seeded": 0}
    except Exception:
        return {"de_seeded": 0}
    if not _seed_armed():
        return {"de_seeded": 0}
    stamp = DE_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"de_seeded": 0}
    except Exception:
        return {"de_seeded": 0}
    wrote = 0
    for f in de_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("de seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("de seed: %d skills into %s", wrote, tenant)
    return {"de_seeded": wrote}


def seed_enpack(tenant: str) -> dict:
    """Copy the Entertainment pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "enpack_enabled", True):
            return {"en_seeded": 0}
    except Exception:
        return {"en_seeded": 0}
    if not _seed_armed():
        return {"en_seeded": 0}
    stamp = EN_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"en_seeded": 0}
    except Exception:
        return {"en_seeded": 0}
    wrote = 0
    for f in en_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("en seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("en seed: %d skills into %s", wrote, tenant)
    return {"en_seeded": wrote}


def seed_dbpack(tenant: str) -> dict:
    """Copy the Databases pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "dbpack_enabled", True):
            return {"db_seeded": 0}
    except Exception:
        return {"db_seeded": 0}
    if not _seed_armed():
        return {"db_seeded": 0}
    stamp = DB_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"db_seeded": 0}
    except Exception:
        return {"db_seeded": 0}
    wrote = 0
    for f in db_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("db seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("db seed: %d skills into %s", wrote, tenant)
    return {"db_seeded": wrote}


def seed_mepack(tenant: str) -> dict:
    """Copy the Media pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "mepack_enabled", True):
            return {"me_seeded": 0}
    except Exception:
        return {"me_seeded": 0}
    if not _seed_armed():
        return {"me_seeded": 0}
    stamp = ME_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"me_seeded": 0}
    except Exception:
        return {"me_seeded": 0}
    wrote = 0
    for f in me_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("me seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("me seed: %d skills into %s", wrote, tenant)
    return {"me_seeded": wrote}


def seed_lepack(tenant: str) -> dict:
    """Copy the Learn pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "lepack_enabled", True):
            return {"le_seeded": 0}
    except Exception:
        return {"le_seeded": 0}
    if not _seed_armed():
        return {"le_seeded": 0}
    stamp = LE_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"le_seeded": 0}
    except Exception:
        return {"le_seeded": 0}
    wrote = 0
    for f in le_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("le seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("le seed: %d skills into %s", wrote, tenant)
    return {"le_seeded": wrote}


def seed_secpack(tenant: str) -> dict:
    """Copy the Security pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "secpack_enabled", True):
            return {"se_seeded": 0}
    except Exception:
        return {"se_seeded": 0}
    if not _seed_armed():
        return {"se_seeded": 0}
    stamp = SE_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"se_seeded": 0}
    except Exception:
        return {"se_seeded": 0}
    wrote = 0
    for f in se_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("se seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("se seed: %d skills into %s", wrote, tenant)
    return {"se_seeded": wrote}


def seed_cmpack(tenant: str) -> dict:
    """Copy the CMS pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "cmpack_enabled", True):
            return {"cm_seeded": 0}
    except Exception:
        return {"cm_seeded": 0}
    if not _seed_armed():
        return {"cm_seeded": 0}
    stamp = CM_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"cm_seeded": 0}
    except Exception:
        return {"cm_seeded": 0}
    wrote = 0
    for f in cm_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("cm seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("cm seed: %d skills into %s", wrote, tenant)
    return {"cm_seeded": wrote}


def seed_hapack(tenant: str) -> dict:
    """Copy the Hardware pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "hapack_enabled", True):
            return {"ha_seeded": 0}
    except Exception:
        return {"ha_seeded": 0}
    if not _seed_armed():
        return {"ha_seeded": 0}
    stamp = HA_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"ha_seeded": 0}
    except Exception:
        return {"ha_seeded": 0}
    wrote = 0
    for f in ha_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("ha seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("ha seed: %d skills into %s", wrote, tenant)
    return {"ha_seeded": wrote}


def seed_bupack(tenant: str) -> dict:
    """Copy the Business pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "bupack_enabled", True):
            return {"bu_seeded": 0}
    except Exception:
        return {"bu_seeded": 0}
    if not _seed_armed():
        return {"bu_seeded": 0}
    stamp = BU_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"bu_seeded": 0}
    except Exception:
        return {"bu_seeded": 0}
    wrote = 0
    for f in bu_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("bu seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("bu seed: %d skills into %s", wrote, tenant)
    return {"bu_seeded": wrote}


def seed_wopack(tenant: str) -> dict:
    """Copy the Work pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "wopack_enabled", True):
            return {"wo_seeded": 0}
    except Exception:
        return {"wo_seeded": 0}
    if not _seed_armed():
        return {"wo_seeded": 0}
    stamp = WO_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"wo_seeded": 0}
    except Exception:
        return {"wo_seeded": 0}
    wrote = 0
    for f in wo_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("wo seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("wo seed: %d skills into %s", wrote, tenant)
    return {"wo_seeded": wrote}


def seed_nepack(tenant: str) -> dict:
    """Copy the Networking pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "nepack_enabled", True):
            return {"ne_seeded": 0}
    except Exception:
        return {"ne_seeded": 0}
    if not _seed_armed():
        return {"ne_seeded": 0}
    stamp = NE_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"ne_seeded": 0}
    except Exception:
        return {"ne_seeded": 0}
    wrote = 0
    for f in ne_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("ne seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("ne seed: %d skills into %s", wrote, tenant)
    return {"ne_seeded": wrote}


def seed_dcpack(tenant: str) -> dict:
    """Copy the Decentralized pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "dcpack_enabled", True):
            return {"dc_seeded": 0}
    except Exception:
        return {"dc_seeded": 0}
    if not _seed_armed():
        return {"dc_seeded": 0}
    stamp = DC_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"dc_seeded": 0}
    except Exception:
        return {"dc_seeded": 0}
    wrote = 0
    for f in dc_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("dc seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("dc seed: %d skills into %s", wrote, tenant)
    return {"dc_seeded": wrote}


def seed_hspack(tenant: str) -> dict:
    """Copy the Health pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "hspack_enabled", True):
            return {"hs_seeded": 0}
    except Exception:
        return {"hs_seeded": 0}
    if not _seed_armed():
        return {"hs_seeded": 0}
    stamp = HS_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"hs_seeded": 0}
    except Exception:
        return {"hs_seeded": 0}
    wrote = 0
    for f in hs_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("hs seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("hs seed: %d skills into %s", wrote, tenant)
    return {"hs_seeded": wrote}


def seed_evpack(tenant: str) -> dict:
    """Copy the Events pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "evpack_enabled", True):
            return {"ev_seeded": 0}
    except Exception:
        return {"ev_seeded": 0}
    if not _seed_armed():
        return {"ev_seeded": 0}
    stamp = EV_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"ev_seeded": 0}
    except Exception:
        return {"ev_seeded": 0}
    wrote = 0
    for f in ev_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("ev seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("ev seed: %d skills into %s", wrote, tenant)
    return {"ev_seeded": wrote}


def seed_tepack(tenant: str) -> dict:
    """Copy the Testing pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "tepack_enabled", True):
            return {"te_seeded": 0}
    except Exception:
        return {"te_seeded": 0}
    if not _seed_armed():
        return {"te_seeded": 0}
    stamp = TE_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"te_seeded": 0}
    except Exception:
        return {"te_seeded": 0}
    wrote = 0
    for f in te_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("te seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("te seed: %d skills into %s", wrote, tenant)
    return {"te_seeded": wrote}


def seed_mipack(tenant: str) -> dict:
    """Copy the Miscellaneous pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "mipack_enabled", True):
            return {"mi_seeded": 0}
    except Exception:
        return {"mi_seeded": 0}
    if not _seed_armed():
        return {"mi_seeded": 0}
    stamp = MI_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"mi_seeded": 0}
    except Exception:
        return {"mi_seeded": 0}
    wrote = 0
    for f in mi_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("mi seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("mi seed: %d skills into %s", wrote, tenant)
    return {"mi_seeded": wrote}


def seed_repack(tenant: str) -> dict:
    """Copy the Related pack into a tenant once ever, create-if-missing (the seed_edpack twin).
    Its own stamp: tenants that already consumed every earlier pack's stamp still get this one."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "repack_enabled", True):
            return {"re_seeded": 0}
    except Exception:
        return {"re_seeded": 0}
    if not _seed_armed():
        return {"re_seeded": 0}
    stamp = RE_STAMP.format(str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"re_seeded": 0}
    except Exception:
        return {"re_seeded": 0}
    wrote = 0
    for f in re_files():
        try:
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            skills_store.create(tenant, name or f.stem, desc, body, extra=_when_of(f))
            store.skill_use_mark(tenant, name or f.stem, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue
        except Exception:
            log.exception("re seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    if wrote:
        log.info("re seed: %d skills into %s", wrote, tenant)
    return {"re_seeded": wrote}


def _when_pairs() -> list[tuple[str, str]]:
    out = []
    for f in sorted(set(seed_files()) | set(pack_files_all())):
        w = _when_of(f).get("when_to_use")
        if w:
            try:
                name, _, _ = parse_skill(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            out.append((name or f.stem, " ".join(w.split())))
    return out


def _h(text: str) -> str:
    import hashlib
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def seed_when(tenant: str) -> dict:
    """v0.753: the shipped trigger words (`when_to_use`) reach skills a tenant ALREADY holds - only that field, never her
    description or body. A skill with no trigger line gets one; a trigger line Hoola itself shipped earlier is replaced
    by the newer one; a line she wrote herself is never touched (each shipped line is remembered by its hash). The stamp
    carries a digest of every shipped line, so improving one later re-runs this once for everybody."""
    if not _seed_armed():
        return {"when_added": 0}
    pairs = _when_pairs()
    stamp = WHEN_STAMP.format(_h(repr(pairs)) + ":" + str(tenant or "default"))
    try:
        store.ensure()
        if store.is_consumed(stamp):
            return {"when_added": 0}
    except Exception:
        return {"when_added": 0}
    changed = 0
    for name, w in pairs:
        try:
            cur = skills_store.get_when(tenant, name)
            if cur is None:
                continue                                         # she does not have (or deleted) this skill
            mine = f"skills:whenmine:{tenant}:{name}:{{}}"
            if cur == w:
                pass
            elif not cur:
                changed += skills_store.add_when(tenant, name, w)
            elif store.is_consumed(mine.format(_h(cur))):        # a line WE shipped earlier: replace with the new one
                changed += skills_store.add_when(tenant, name, w, replace=True)
            else:
                continue                                         # her own words: leave them
            store.mark_consumed(mine.format(_h(w)))
        except Exception:
            log.exception("when_to_use refresh of %s failed for %s", name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
    except Exception:
        pass
    return {"when_added": changed}


def _pack_seeders() -> list:
    """Every pack seeder in this module, found by name: the starters (`seed`) plus every `seed_<pack>(tenant)`.
    A new pack therefore needs NO edit to seed_all - it only has to follow the convention (its own stamp,
    create-if-missing, fail-open). Order is stable (sorted by name)."""
    skip = {"seed_all", "seed_files"}
    return [seed] + [f for n, f in sorted(globals().items())
                     if n.startswith("seed_") and n not in skip and callable(f)]


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
    for fn in _pack_seeders():
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
            skills_store.create(tenant, name, desc, body, extra=_when_of(f))   # create-if-missing: hers win
            store.skill_use_mark(tenant, name, "installed", surface="seed")
            wrote += 1
        except SkillError:
            continue                       # already exists (or lint): her file stays
        except Exception:
            log.exception("seed of %s failed for %s", f.name, tenant)
            _FAILED_STAMPS.add(stamp)
    try:
        _consume(stamp)
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
