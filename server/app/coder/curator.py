"""HOOLA CURATOR (v0.480.0) - the weekly memory consolidation, the review layer the dedup
ladder was built for.

claude-mem's curator role, ported onto the vault's own surfaces. Three acts, one cheap-brain
call per tenant, about once a week:

  SCAN        the dedup ladder's Tier-1 near-duplicate scan finally wired for production
              (dedup.classify_pair existed since v0.473 with no caller - candidates were only
              ever written by tests). Blocked on shared tokens, IDF vetoed, gated on a minimum
              corpus (coder_dedup_min_docs, default 10 - "IDF on 3 documents is astrology").
              New pairs land as pending candidates; existing ones are never re-inserted.
  ARBITRATE   every pending pair is shown to the cheap brain ONCE, both rows side by side
              (already-redacted vault content only - the privacy gate extends to the curator),
              and it answers per pair: merge / distinct / dismiss. The pinned decisions:
              - the ladder's law "nothing is ever auto-merged on Tier 1" becomes "the owner's
                flip of coder_curator IS the human decision": one opt-in switch delegates the
                weekly judgment, and every merge is SOFT - the absorbed row stays on disk with
                superseded_by=canonical, search stops showing it, and revive() undoes it.
              - a merge always absorbs the NEWER row into the OLDER one (the older row is the
                memory that has been re-confirmed) and reinforces the canonical row.
              - silence is safe: a pair the brain does not rule on stays pending.
  PROMOTE     the same call may propose skills from recurring memories (class-level names,
              <=2 ops per run), through the SAME skills_store.apply funnel with read-before-
              write honored - update targets only the skills listed in the prompt.
  NOMINATE    v0.484 the same call may also hand much-read skills to the SHARE ledger: the
              telemetry is the evidence (>= coder_skills_share_min_reads real reads), the body
              is re-redacted at nomination, and NOTHING leaves the tenant until the owner taps
              approve on the Skill Desk (skill_packs.share_decide) - the auto-anonymised lane
              with the human hand on the tap.

Scheduling: worker.coder_jobs calls curator.tick() beside observer.tick() - the worker slot
discipline, never inside a live turn (no poke coupling needed: nothing here can stall a voice
latency budget). due() reads the last-run stamp from the consumed table; a malformed stamp is
read as due (running again is harmless - the caps bound every run; refusing to run could let
the pending pile rot).

Kill switches: coder_curator (default OFF - bake on the VPS, then flip) over coder_enabled
(master). coder_skills gates only the promotion act; arbitration is pure vault bookkeeping.
Every failure is the log's problem, never a session's - fail-open end to end.
"""
from __future__ import annotations

import logging
import re
import time
from collections import defaultdict

from . import dedup, prompts, skills_store, store

log = logging.getLogger("coder.curator")

LAST_RUN_KEY = "curator:last_run"
SKILL_OPS_PER_RUN = 2                 # promotions ride the same funnel, but sparingly

_PAIR_RE = re.compile(r'<pair\b([^>]*)/>', re.DOTALL)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')

_stats = {"runs": 0, "scanned": 0, "pairs_decided": 0, "merged": 0, "distinct": 0,
          "dismissed": 0, "skills": 0, "skipped": 0}


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
                and getattr(st, "coder_curator", False))


def _every_hours() -> int:
    st = _settings()
    try:
        return max(1, int(getattr(st, "coder_curator_every_hours", 168) or 168))
    except Exception:
        return 168


def _max_pairs() -> int:
    st = _settings()
    try:
        return max(1, int(getattr(st, "coder_curator_max_pairs", 20) or 20))
    except Exception:
        return 20


def _min_reads() -> int:
    st = _settings()
    try:
        return max(1, int(getattr(st, "coder_skills_share_min_reads", 3) or 3))
    except Exception:
        return 3


def _max_merges() -> int:
    st = _settings()
    try:
        return max(0, int(getattr(st, "coder_curator_max_merges", 10) or 10))
    except Exception:
        return 10


def _min_docs() -> int:
    st = _settings()
    try:
        return max(2, int(getattr(st, "coder_dedup_min_docs", 10) or 10))
    except Exception:
        return 10


def stats() -> dict:
    return {**_stats, "last_run": store.last_run_at(LAST_RUN_KEY)}


def due() -> bool:
    """Time for a consolidation? Never ran -> due the moment the owner flips the switch."""
    if not armed():
        return False
    at = store.last_run_at(LAST_RUN_KEY)
    if not at:
        return True
    try:
        then = time.mktime(time.strptime(at[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return True                      # a malformed stamp: run again (caps bound the run)
    return (time.time() - then) >= _every_hours() * 3600


# ---------------------------------------------------------------- SCAN - wire the Tier-1 ladder

def _blocked_pairs(rows: list[dict]) -> list[tuple[int, int]]:
    """Candidate index pairs sharing >= 2 distinct tokens (blocking, the standard trick that
    keeps a weekly scan off a 2000x2000 pairwise walk)."""
    by_tok: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        for t in set(dedup.tokens(r["title"])):
            by_tok[t].append(i)
    seen: set[tuple[int, int]] = set()
    for ids in by_tok.values():
        if len(ids) > 200:               # a stop-word shared by half the vault carries no signal
            continue
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                ia, ib = ids[a], ids[b]
                if ia != ib:
                    seen.add((min(ia, ib), max(ia, ib)))
    shared: list[tuple[int, int]] = []
    for ia, ib in seen:
        if len(set(dedup.tokens(rows[ia]["title"])) & set(dedup.tokens(rows[ib]["title"]))) \
                >= dedup.MIN_SHARED_TOKENS:
            shared.append((ia, ib))
            if len(shared) >= 20_000:    # the scan's own budget: the next run gets the rest
                break
    return shared


def scan(tenant: str) -> int:
    """Tier-1 near-dup scan for one tenant -> how many NEW pending candidates it wrote."""
    with store.db() as c:
        n = c.execute("SELECT COUNT(*) FROM observations WHERE tenant=? AND superseded_by=0",
                      (tenant,)).fetchone()[0]
    if n < _min_docs():
        return 0                          # the astrology gate
    with store.db() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT id, title FROM observations WHERE tenant=? AND superseded_by=0 "
            "ORDER BY created_epoch ASC, id ASC LIMIT ?", (tenant, dedup.MAX_SCAN)).fetchall()]
        df = {t: d for t, d in c.execute("SELECT token, df FROM token_df WHERE tenant=?", (tenant,))}
    doc_count = max(n, 1)
    df_fn = lambda t: df.get(t, 0)        # noqa: E731 - unseen token: df 0, maximum rarity
    wrote = 0
    for ia, ib in _blocked_pairs(rows):
        older, newer = (rows[ia], rows[ib]) if rows[ia]["id"] < rows[ib]["id"] else (rows[ib], rows[ia])
        score, is_dup, _veto = dedup.classify_pair(older["title"], newer["title"], df_fn, doc_count)
        if is_dup:
            store.note_candidate(newer["id"], older["id"], score)
            wrote += 1
    return wrote


# ---------------------------------------------------------------- ARBITRATE + PROMOTE - one call

def _share_candidates(tenant: str, limit: int = 3) -> list[str]:
    """v0.484 the nomination shortlist: live skills with the most REAL reads (the telemetry's
    evidence), the ones already decided never re-nominated. Fail-open, capped."""
    out: list[str] = []
    try:
        counts = store.skill_use_counts(tenant)
        decided = {r["name"] for r in store.skill_share_rows(tenant)
                   if r["status"] in ("published", "pending")}
        live = {s["name"] for s in skills_store.listing(tenant) if s.get("enabled", True)}
        ranked = sorted(((d["read"], n) for n, d in counts.items()
                         if n in live and n not in decided and d.get("read", 0) >= _min_reads()),
                        reverse=True)
        out = [n for _reads, n in ranked[:limit]]
    except Exception:
        log.exception("share candidates failed (%s)", tenant)
    return out


def _pending_for(tenant: str) -> list[dict]:
    """Pending pairs of one tenant, both rows loaded, guards applied, oldest row first.
    Each item: {'key': (obs_id, dup_of), 'score': s, 'older': row, 'newer': row}."""
    out: list[dict] = []
    for cand in store.candidates("pending"):
        newer_row, older_row = store.get_observations([cand["observation_id"],
                                                       cand["duplicate_of_id"]])
        if not newer_row or not older_row:
            continue                       # a row was retention-forgotten: leave it pending
        if newer_row["tenant"] != tenant or older_row["tenant"] != tenant:
            continue                       # tenant law: never arbitrate across tenants
        if newer_row["superseded_by"] or older_row["superseded_by"]:
            store.set_candidate_status(cand["observation_id"], cand["duplicate_of_id"], "merged")
            continue                       # already absorbed by an earlier verdict
        # orientation: the OLDER row is the canonical; duplicate_of_id from capture is the older
        # row by construction, but rank by epoch so a hand-made pair cannot invert the merge.
        if int(newer_row["created_epoch"]) < int(older_row["created_epoch"]):
            newer_row, older_row = older_row, newer_row
        out.append({"key": (cand["observation_id"], cand["duplicate_of_id"]),
                    "score": float(cand.get("score") or 0.0),
                    "older": older_row, "newer": newer_row})
        if len(out) >= _max_pairs():
            break
    return out


def _parse_verdicts(text: str) -> dict[int, str]:
    """<pair id="N" verdict="merge|distinct|dismiss" /> -> {N: verdict}. Garbage lines are
    silence: the pair stays pending (the safe side)."""
    out: dict[int, str] = {}
    for m in _PAIR_RE.finditer(text or ""):
        attrs = dict(_ATTR_RE.findall(m.group(1) or ""))
        try:
            pid = int(str(attrs.get("id") or "").strip())
        except ValueError:
            continue
        v = str(attrs.get("verdict") or "").strip().lower()
        if v in ("merge", "distinct", "dismiss"):
            out[pid] = v
    return out


async def consolidate(tenant: str, st) -> dict:
    """One tenant's run: scan, ONE combined cheap-brain call, apply the verdicts + promotions.
    Best-effort end to end; every failure leaves the vault exactly as it was."""
    report = {"tenant": tenant, "new_candidates": 0, "decided": 0, "merged": 0,
              "distinct": 0, "dismissed": 0, "skills": 0, "nominated": 0, "brain": False}
    try:
        report["new_candidates"] = scan(tenant)
    except Exception:
        log.exception("curator scan failed (%s) - arbitrating what is pending", tenant)
    # v0.484 NOMINATE - the share lane runs FIRST and needs NO brain call: the telemetry is the
    # whole evidence, and a quiet week with no pending pairs must not starve the shelf.
    if getattr(st, "coder_skills_share", True):
        try:
            from . import skill_packs
            for name in _share_candidates(tenant):
                res = skill_packs.share_nominate(tenant, name,
                                                 note="curator nomination: the telemetry shows "
                                                      "this skill was followed repeatedly")
                if res.get("ok"):
                    report["nominated"] += 1
        except Exception:
            log.exception("curator share nomination failed (%s)", tenant)
    pairs = _pending_for(tenant)
    if not pairs:
        _stats["skipped"] += 1
        _stats["runs"] += 1
        _stats["skills"] += 0
        return report
    numbered = [{**p, "id": i + 1} for i, p in enumerate(pairs)]
    skills_now = skills_store.listing(tenant)
    try:
        from .observer import _call_brain   # the same cheap brain + fallback, nothing new
        out = await _call_brain(prompts.curator_system(),
                                prompts.curator_user(numbered, skills_now, _max_merges()), st)
    except Exception as e:
        log.info("curator brain failed (%s): %s", tenant, e)
        return report
    report["brain"] = True
    verdicts = _parse_verdicts(out or "")
    merges = 0
    for p in numbered:
        v = verdicts.get(p["id"])
        if v is None:
            continue                        # silence: the pair stays pending
        obs_id, dup_of = p["key"]
        if v == "merge":
            if merges >= _max_merges():
                continue                    # over budget: stays pending for the next run
            if store.supersede(p["newer"]["id"], p["older"]["id"]):
                store.reinforce(p["older"]["id"], bump=True)   # absorbing a duplicate IS a re-confirm
                store.set_candidate_status(obs_id, dup_of, "merged")
                merges += 1
                report["merged"] += 1
        elif v == "distinct":
            store.set_candidate_status(obs_id, dup_of, "distinct")
            report["distinct"] += 1
        elif v == "dismiss":
            store.set_candidate_status(obs_id, dup_of, "dismissed")
            report["dismissed"] += 1
    report["decided"] = report["merged"] + report["distinct"] + report["dismissed"]
    # PROMOTE - the same response may carry skills; the read-before-write law applies to the
    # curator like to everyone: an update targets only a listed skill, opened by a real read.
    if getattr(st, "coder_skills", True):
        from .nudge import _parse_skills
        budget = SKILL_OPS_PER_RUN
        for action, name, desc, body in _parse_skills(out or ""):
            if budget <= 0:
                break
            if action == "update":
                if not any(s["name"] == name for s in skills_now):
                    continue                # never heard of it: not updatable
                try:
                    skills_store.read(tenant, name)   # the honest read
                except skills_store.SkillError:
                    continue                # vanished between list and write: skip it
            res = skills_store.apply(tenant, [{"action": action, "name": name,
                                               "description": desc, "body": body}])
            if res.get("ok"):
                report["skills"] += 1
                budget -= 1
            else:
                log.info("curator skill write refused (%s): %s", name, res.get("error"))
    _stats["runs"] += 1
    _stats["scanned"] += report["new_candidates"]
    _stats["pairs_decided"] += report["decided"]
    _stats["merged"] += report["merged"]
    _stats["distinct"] += report["distinct"]
    _stats["dismissed"] += report["dismissed"]
    _stats["skills"] += report["skills"]
    return report


async def tick(st, force: bool = False) -> dict:
    """The worker entry (beside observer.tick): due-gated, per-tenant, fail-open. force=True
    (the admin route / tests) runs now and skips the due gate - never the kill switch. The
    last-run stamp is written even on a partial run - the caps bound every attempt, and a
    wedged stamp would pile pending work forever."""
    if not armed():
        return {"ran": False}
    if not force and not due():
        return {"ran": False}
    tenants: list[str] = []
    try:
        store.ensure()
        with store.db() as c:
            tenants = [r[0] for r in c.execute(
                "SELECT DISTINCT tenant FROM observations ORDER BY tenant").fetchall()]
    except Exception:
        log.exception("curator tenant listing failed")
    reports = []
    for t in tenants:
        try:
            reports.append(await consolidate(t, st))
        except Exception:
            log.exception("curator run failed for tenant %r", t)
    store.mark_consumed(LAST_RUN_KEY)
    return {"ran": True, "tenants": reports}


def reset_for_tests() -> None:
    """Test isolation: forget stats (the consumed stamp lives in the vault, wiped with it)."""
    for k in _stats:
        _stats[k] = 0
