"""HOOLA SAPNE (v0.479.0) - the nightly curator, OpenClaw's dreaming sweep ported to the house stack.

OpenClaw's memory doc (docs/concepts/dreaming.md) is the shape: background consolidation that
moves strong short-term signals into durable memory while keeping the process explainable and
reviewable. The house translation (every deviation is a pinned decision):

  two passes        LIGHT nightly (merge the last coder_dreams_light_hours of raw vault rows into
                    at most coder_dreams_max_writes curated memory rows) and DEEP weekly (a wider
                    window which MAY also rewrite up to that many EXISTING curated rows - each
                    rewrite stores the exact preimage first, so every consolidation is undoable).
  one brain call    the same cheap path as the observer/nudge (observer._call_brain), a STABLE
                    system prompt (prompts.dreams_system never changes - the cache shape), the
                    same <observation> XML the parser already knows. No new output format.
  same funnel       curated rows ride store.store_observation (dedup ladder, redaction already
                    done) with actor='dreams', so yaad_khojo / the primer / the three-layer
                    search find them with zero new plumbing. The ladder's Tier-0 title merge
                    means a curated fact said again REINFORCES the old row instead of duplicating.
  no self-recursion the input digest NEVER includes actor='dreams' rows (it must not re-read its
                    own output); the curator has no tools and cannot spawn anything.
  privacy           the tenant-level gate: the tenant's most recent prompt is <private> -> the
                    pass is skipped entirely (the observer's per-conv rule, lifted one level).
                    Private turns never produced vault rows in the first place, so a wholly
                    private window leaves nothing to consolidate anyway.
  reviewable        every run appends a dated section to the tenant's dreams digest file
                    (<coder_dir>/dreams/<tenant>/dreams.md); the previous file text is saved as
                    dreams.md.pre before each rewrite (OpenClaw's preimage discipline, file level).
                    GET /api/coder/dreams returns it - she can read everything the curator did.
  quiet by law      a tenant with no raw rows in the window is not even queried (the candidate
                    list is one indexed DISTINCT query). At most ONE consolidation runs per
                    worker tick, so a thousand tenants cost at most one brain call each 5s tick.
  kill switch       coder_dreams default OFF (bake on the VPS, then flip), under coder_enabled;
                    every failure is the log's problem, never a session's.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time

from . import parser, prompts, store

log = logging.getLogger("coder.dreams")

_MAX_ROWS_INPUT = 40            # raw rows fed to one pass (the digest, capped again in the prompt)
_CURATED_SHOWN = 12             # curated titles shown so the pass merges, not repeats

_BG: set = set()                # running passes (GC protection, the nudge._BG pattern)
_stats = {"runs": 0, "light": 0, "deep": 0, "written": 0, "rewritten": 0, "preimages": 0,
          "skipped": 0, "dropped": 0}


# ---------------------------------------------------------------- knobs

def _settings():
    try:
        from ..config import get_settings
        return get_settings()
    except Exception:
        return None


def armed() -> bool:
    st = _settings()
    return bool(st is not None and getattr(st, "coder_enabled", True)
                and getattr(st, "coder_dreams", False))


def _light_window_s() -> int:
    try:
        return max(1, int(getattr(_settings(), "coder_dreams_light_hours", 26) or 26)) * 3600
    except Exception:
        return 26 * 3600


def _deep_window_s() -> int:
    try:
        return max(1, int(getattr(_settings(), "coder_dreams_deep_days", 7) or 7)) * 86400
    except Exception:
        return 7 * 86400


def _max_writes() -> int:
    try:
        return max(1, int(getattr(_settings(), "coder_dreams_max_writes", 4) or 4))
    except Exception:
        return 4


def stats() -> dict:
    return dict(_stats)


# ---------------------------------------------------------------- scheduling

def due(tenant: str) -> str | None:
    """Which pass is due for this tenant right now ('deep' | 'light' | None). Deep wins: it
    subsumes the light pass when both are overdue."""
    now = int(time.time())
    deep = store.dreams_state_get(tenant, "deep")
    light = store.dreams_state_get(tenant, "light")
    if now - deep["last_epoch"] >= _deep_window_s():
        return "deep"
    if now - light["last_epoch"] >= _light_window_s():
        return "light"
    return None


async def tick(settings, max_passes: int = 1) -> dict:
    """The worker entry (coder_jobs calls it every >=5 s). Candidates = tenants with fresh raw
    rows; at most max_passes consolidations per tick; every failure is the log's problem."""
    if not armed():
        return {"ok": False, "reason": "disarmed"}
    try:
        store.ensure()
        since = int(time.time()) - _light_window_s()
        tenants = store.tenants_with_rows_since(since)
    except Exception:
        log.exception("dreams candidate query failed")
        return {"ok": False, "reason": "query"}
    done = 0
    for tenant in tenants:
        if done >= max_passes:
            break
        kind = due(tenant)
        if kind is None:
            continue
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            break                          # a sync caller (tests run consolidate() directly)
        t = asyncio.ensure_future(consolidate(tenant, kind))
        _BG.add(t)
        t.add_done_callback(_BG.discard)
        done += 1
    return {"ok": True, "candidates": len(tenants), "started": done}


# ---------------------------------------------------------------- digest file

def digest_dir(tenant: str) -> str:
    import os
    from .store import root
    d = os.path.join(root(), "dreams", _safe(tenant))
    os.makedirs(d, exist_ok=True)
    return d


def digest_path(tenant: str) -> str:
    import os
    return os.path.join(digest_dir(tenant), "dreams.md")


def _safe(tenant: str) -> str:
    return "".join(ch for ch in (tenant or "default") if ch.isalnum() or ch in "-_.")[:64] or "default"


def read_digest(tenant: str) -> str:
    try:
        with open(digest_path(tenant), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception:
        log.exception("dreams digest read failed")
        return ""


def _append_digest(tenant: str, kind: str, lines: list[str]) -> bool:
    """Append the dated section; the previous file text survives as dreams.md.pre (the file-level
    preimage - OpenClaw's rewrite-preimage rule)."""
    path = digest_path(tenant)
    pre = path + ".pre"
    try:
        old = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                old = f.read()
            with open(pre, "w", encoding="utf-8") as f:
                f.write(old)
        stamp = time.strftime("%Y-%m-%d %H:%M")
        head = f"\n\n## {stamp} - {kind}\n"
        body = "\n".join(f"- {ln}" for ln in lines) if lines else "- nothing durable tonight"
        with open(path, "a", encoding="utf-8") as f:
            f.write(head + body + "\n")
        return True
    except Exception:
        log.exception("dreams digest write failed (%s)", tenant)
        return False


# ---------------------------------------------------------------- the passes

def _rows_digest(rows: list[dict], curated: list[dict]) -> str:
    import json
    lines = []
    for r in rows:
        try:
            fl = [str(x) for x in json.loads(r.get("facts") or "[]")][:4]
        except Exception:
            fl = []
        facts = "; ".join(fl)
        lines.append(f"- [{r.get('type') or 'discovery'}] {r.get('title')}"
                     + (f" :: {r.get('subtitle')}" if r.get("subtitle") else "")
                     + (f" :: {facts}" if facts else ""))
    cur = [f"- {c['title']}" for c in curated]
    return ("THE WINDOW'S RAW NOTES (oldest first):\n" + ("\n".join(lines) or "(none)") +
            "\n\nALREADY CURATED (write only if something genuinely CHANGED; same title = "
            "reinforce, not duplicate):\n" + ("\n".join(cur) or "(nothing curated yet)"))


async def consolidate(tenant: str, kind: str) -> dict:
    """One pass. Best-effort end to end: any failure means nothing was curated tonight."""
    st = _settings()
    tenant = str(tenant or "default")
    if st is None or not armed() or kind not in ("light", "deep"):
        return {"ok": False}
    try:   # the house usage gate (the observer's rule): her plan pays for her own memory
        from .. import usage
        if not usage.allowed(tenant, "coder"):
            _stats["skipped"] += 1
            return {"ok": False, "reason": "usage"}
    except Exception:
        pass
    try:
        store.ensure()
        window = _deep_window_s() if kind == "deep" else _light_window_s()
        since = int(time.time()) - window
        rows = store.observations_since(tenant, since, _MAX_ROWS_INPUT)
        if not rows:
            store.dreams_state_set(tenant, kind, int(time.time()))   # an empty window IS the run
            _stats["skipped"] += 1
            return {"ok": True, "reason": "no-rows"}
        if store.latest_prompt_private_for_tenant(tenant):
            store.dreams_state_set(tenant, kind, int(time.time()))   # a private day: skip politely
            _stats["skipped"] += 1
            return {"ok": True, "reason": "private"}
        curated = store.curated_recent(tenant, _CURATED_SHOWN)
        from .observer import _call_brain        # the same cheap brain + fallback, nothing new
        out = await _call_brain(prompts.dreams_system(),
                                prompts.dreams_user(_rows_digest(rows, curated), kind), st)
    except Exception as e:
        log.info("dreams pass failed (%s/%s): %s", tenant, kind, e)
        return {"ok": False, "reason": "brain"}
    text = (out or "").strip()
    written = rewritten = 0
    if text and parser.parse_skip(text) is None:
        try:
            mode = None
            try:
                from .modes import load_mode
                mode = load_mode()
            except Exception:
                mode = None
            valid_types = {t["id"] for t in mode["observation_types"]} if mode else set()
            valid_concepts = set(mode["observation_concepts"]) if mode else set()
            obs = parser.parse_observations(text, valid_types, valid_concepts) or \
                parser.salvage_prose(text)
            budget = _max_writes()
            curated_titles = {store.norm_title(c["title"]) for c in curated}
            conv = f"dreams-{_safe(tenant)}"   # per-tenant bucket: the (conv, hash) dedup pair can
            for o in obs[:max(0, budget)]:     # never meet another tenant's curated row
                if kind == "deep" and store.norm_title(o["title"]) in curated_titles:
                    row = next((c for c in curated
                                if store.norm_title(c["title"]) == store.norm_title(o["title"])), None)
                    if row is not None and store.obs_update_curated(
                            row["id"], o, f"dreams deep consolidation ({tenant})") is not None:
                        rewritten += 1
                        _stats["preimages"] += 1
                        continue
                    # an update that failed falls through to the funnel: the Tier-0 title merge
                    # turns the insert into a reinforce, so the fact is never lost nor duplicated
                if store.store_observation(conv, tenant, o, actor="dreams") is not None:
                    written += 1
        except Exception:
            log.exception("dreams writes failed (tenant continues)")
    _append_digest(tenant, kind, _digest_lines(text, written, rewritten))
    store.dreams_state_set(tenant, kind, int(time.time()))
    _stats["runs"] += 1
    _stats["light" if kind == "light" else "deep"] += 1
    _stats["written"] += written
    _stats["rewritten"] += rewritten
    return {"ok": True, "kind": kind, "written": written, "rewritten": rewritten}


def _digest_lines(text: str, written: int, rewritten: int) -> list[str]:
    lines: list[str] = []
    for o in parser.parse_observations(text or "")[:_max_writes()]:
        lines.append(o["title"])
    if rewritten:
        lines.append(f"{rewritten} existing memory row(s) rewritten (preimage saved - undoable)")
    if not lines:
        lines.append("nothing durable tonight")
    return lines


def reset_for_tests() -> None:
    """Test isolation: forget stats and running passes."""
    for k in _stats:
        _stats[k] = 0
    _BG.clear()
