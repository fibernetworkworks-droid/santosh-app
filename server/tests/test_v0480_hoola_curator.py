"""v0.484.0 HOOLA CURATOR - the weekly memory consolidation (the review layer the dedup
ladder was built for, the claude-mem curator role ported onto the vault).

What this suite pins, piece by piece:
(1) MIGRATION: observations.superseded_by is additive (fresh vaults get the column in the
    schema; legacy vaults are lifted by the pragma check) and the schema version stamps 2.
(2) MERGE MACHINERY: supersede() is SOFT and once-only (the row stays on disk, revive()
    brings it back); the OLDER row is always the canonical, even when a pair was recorded
    inverted; a merge reinforces the canonical row.
(3) SCAN: the Tier-1 near-dup scan finally wired for production (classify_pair had no caller
    since v0.473) - blocked on shared tokens, IDF-vetoed, gated on a minimum corpus.
(4) ARBITRATE: ONE combined cheap-brain call per tenant run; per-pair verdicts merge /
    distinct / dismiss; silence keeps a pair pending (the safe side); max_merges and
    max_pairs caps; cross-tenant pairs are never arbitrated; an already-superseded row's
    pair is marked merged without acting again.
(5) SEARCH HIDING: superseded rows vanish from the FTS leg, the LIKE fallback, the timeline
    and the primer's recent block - but layer-3 get_observations still fetches by id, and
    stats() carries the curator ledger.
(6) PROMOTE: the same response may carry skills; read-before-write honored (update only a
    listed skill, opened by a real read); coder_skills off silences promotion only.
(7) GATES: due() (never ran / fresh stamp / old stamp / malformed stamp), tick() (armed,
    due, force), kill switches coder_curator (default OFF) + coder_enabled (master),
    the package-export law (coder.curator.tick resolves - the v0.478 lesson), routes,
    and the version stamps.
"""
import asyncio
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import coder
from app.coder import curator, inject, nudge, prompts, search, skills_store, store

T = "default"
CONV = "conv_curator"


def _run(coro):
    return asyncio.run(coro)


def _settings(**over):
    from app.config import get_settings
    return get_settings()


def _obs(title, narrative="the body", conv=CONV, tenant=T, subtitle=""):
    return store.store_observation(conv, tenant, {
        "type": "discovery", "title": title, "subtitle": subtitle, "facts": [],
        "narrative": narrative, "concepts": []})


def _row(oid):
    rows = store.get_observations([oid])
    return rows[0] if rows else None


def _pending():
    return store.candidates("pending")


@pytest.fixture()
def cur(env, monkeypatch, tmp_path):
    """Fresh vault in a TEMP dir, skills ON, curator OFF (the default)."""
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_SKILLS", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    store.ensure()
    skills_store.reset_for_tests()
    curator.reset_for_tests()
    yield monkeypatch
    skills_store.reset_for_tests()
    curator.reset_for_tests()
    get_settings.cache_clear()


@pytest.fixture()
def armed(cur, monkeypatch):
    """The curator ARMED (coder_curator=true), one combined call, small caps."""
    monkeypatch.setenv("CODER_CURATOR", "true")
    monkeypatch.setenv("CODER_DEDUP_MIN_DOCS", "2")
    monkeypatch.setenv("CODER_CURATOR_MAX_PAIRS", "20")
    monkeypatch.setenv("CODER_CURATOR_MAX_MERGES", "10")
    from app.config import get_settings
    get_settings.cache_clear()
    return monkeypatch


def _fake_brain(monkeypatch, text, calls=None):
    """Monkeypatch observer._call_brain (curator imports it at call time)."""
    from app.coder import observer

    async def _fake(system, user, settings):
        if calls is not None:
            calls.append((system, user))
        return text
    monkeypatch.setattr(observer, "_call_brain", _fake)


# ---------------------------------------------------------------- (1) migration

def test_migration_lifts_legacy_vault(cur, tmp_path, monkeypatch):
    """A vault created before v0.479 (no superseded_by column) is lifted in place."""
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "legacy"))
    from app.config import get_settings
    get_settings.cache_clear()
    conn = sqlite3.connect(store.path())
    conn.executescript("""
        CREATE TABLE schema_version (v INTEGER NOT NULL);
        INSERT INTO schema_version(v) VALUES (1);
        CREATE TABLE observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, conv TEXT NOT NULL, tenant TEXT NOT NULL DEFAULT '',
            type TEXT NOT NULL, title TEXT NOT NULL, subtitle TEXT NOT NULL DEFAULT '',
            facts TEXT NOT NULL DEFAULT '[]', narrative TEXT NOT NULL DEFAULT '',
            concepts TEXT NOT NULL DEFAULT '[]', files_read TEXT NOT NULL DEFAULT '[]',
            files_modified TEXT NOT NULL DEFAULT '[]', turn_id TEXT NOT NULL DEFAULT '',
            actor TEXT NOT NULL DEFAULT '', discovery_tokens INTEGER NOT NULL DEFAULT 0,
            content_hash TEXT NOT NULL, title_norm_key TEXT NOT NULL DEFAULT '',
            occurrence_count INTEGER NOT NULL DEFAULT 1,
            reinforcement_dates TEXT NOT NULL DEFAULT '[]', last_reinforced TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, created_epoch INTEGER NOT NULL);
    """)
    conn.commit()
    conn.close()
    store.ensure()                                  # the pragma check must ALTER it
    conn = sqlite3.connect(store.path())
    cols = [r[1] for r in conn.execute("PRAGMA table_info(observations)").fetchall()]
    assert "superseded_by" in cols
    # v0.484 HOOLA SKILL DESK: schema_version moved to 3 (the additive skills.enabled lift)
    assert conn.execute("SELECT v FROM schema_version").fetchone()[0] == 3
    conn.close()


def test_fresh_vault_schema_and_stats_shape(cur):
    store.ensure()
    st = store.stats()
    assert st["curator"] == {"pending": 0, "merged": 0, "distinct": 0, "dismissed": 0,
                             "superseded": 0}
    assert isinstance(curator.stats()["last_run"], str)


# ---------------------------------------------------------------- (2) merge machinery

def test_supersede_is_soft_and_once_only(cur):
    a = _obs("spool drain restart loop fixed")
    b = _obs("worker spool drain restart loop fixed")
    assert store.supersede(b, a) is True
    assert store.supersede(b, a) is False           # a live row only, exactly once
    assert _row(b)["superseded_by"] == a
    assert _row(a)["superseded_by"] == 0
    assert store.revive(b) is True
    assert _row(b)["superseded_by"] == 0
    assert store.revive(b) is False                 # nothing left to undo


def test_merge_reinforces_the_canonical(cur, armed, monkeypatch):
    a = _obs("deploy systemd unit restart discipline")
    b = _obs("deploy systemd unit restart discipline v2")   # distinct hash, same subject
    store.note_candidate(b, a, 0.93)
    _fake_brain(monkeypatch, '<pair id="1" verdict="merge" />')
    rep = _run(curator.consolidate(T, _settings()))
    assert rep["merged"] == 1 and rep["brain"] is True
    assert _row(b)["superseded_by"] == a
    canon = _row(a)
    assert canon["occurrence_count"] == 2           # the older row was re-confirmed
    assert canon["last_reinforced"]
    assert [c for c in store.candidates("merged")][0]["observation_id"] == b


def test_older_row_wins_even_when_pair_recorded_inverted(cur, armed, monkeypatch):
    a = _obs("camera upload throttling queue")
    b = _obs("camera upload throttling queue retries")
    with store.db(write=True) as c:                 # make the epochs unmistakably different
        c.execute("UPDATE observations SET created_epoch=1000 WHERE id=?", (a,))
        c.execute("UPDATE observations SET created_epoch=2000 WHERE id=?", (b,))
    store.note_candidate(a, b, 0.9)                 # capture recorded it BACKWARDS
    _fake_brain(monkeypatch, '<pair id="1" verdict="merge" />')
    _run(curator.consolidate(T, _settings()))
    assert _row(b)["superseded_by"] == a            # the NEWER row (b) is absorbed...
    assert _row(a)["superseded_by"] == 0            # ...into the OLDER row (a), always


# ---------------------------------------------------------------- (3) scan

def test_scan_gate_refuses_tiny_corpus(cur):
    _obs("billing invoice webhook retries")
    _obs("camera upload throttling queue")
    assert curator.scan(T) == 0                     # IDF on 3 documents is astrology


def test_scan_wires_the_tier1_ladder(cur, armed):
    a = _obs("spool drain restart loop fixed")
    b = _obs("fixed spool drain restart loop")      # same tokens, different word order
    _obs("billing invoice webhook retries")
    assert curator.scan(T) >= 1
    pend = _pending()
    assert len(pend) == 1
    assert pend[0]["observation_id"] == b           # the NEWER row is the candidate
    assert pend[0]["duplicate_of_id"] == a          # the OLDER row is the canonical
    assert 0.8 <= pend[0]["score"] <= 1.0


def test_parse_verdicts():
    text = ('noise before\n<pair id="2" verdict="merge" />\n'
            '<pair id="1" verdict="distinct" />\n<pair id="3" verdict="MERGE" />\n'
            '<pair id="4" verdict="nonsense" />\n<pair id="x" verdict="merge" />')
    v = curator._parse_verdicts(text)
    assert v == {2: "merge", 1: "distinct", 3: "merge"}   # garbage id + garbage verdict = silence


# ---------------------------------------------------------------- (4) arbitrate

def test_arbitrate_distinct_and_dismiss_leave_rows_live(cur, armed, monkeypatch):
    a = _obs("upi qr card render edge")
    b = _obs("upi qr card render layout")
    c = _obs("upi qr card render corner")
    store.note_candidate(b, a, 0.9)
    store.note_candidate(c, a, 0.85)
    _fake_brain(monkeypatch, '<pair id="1" verdict="distinct" /><pair id="2" verdict="dismiss" />')
    rep = _run(curator.consolidate(T, _settings()))
    assert rep["distinct"] == 1 and rep["dismissed"] == 1 and rep["merged"] == 0
    for oid in (a, b, c):
        assert _row(oid)["superseded_by"] == 0      # nothing was hidden
    statuses = {c2["observation_id"]: c2["status"] for c2 in
                store.candidates("distinct") + store.candidates("dismissed")}
    assert statuses[b] == "distinct" and statuses[c] == "dismissed"


def test_silence_keeps_the_pair_pending(cur, armed, monkeypatch):
    a = _obs("manifest version bump ritual")
    b = _obs("manifest version bump ritual again")
    store.note_candidate(b, a, 0.9)
    _fake_brain(monkeypatch, "I am not sure what to say about these.")   # no verdict lines
    rep = _run(curator.consolidate(T, _settings()))
    assert rep["decided"] == 0
    assert len(_pending()) == 1                     # the safe side: never act on silence


def test_max_merges_cap(cur, armed, monkeypatch):
    armed.setenv("CODER_CURATOR_MAX_MERGES", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    a = _obs("one two three four")
    b = _obs("one two three four five")
    d = _obs("six seven eight nine")
    e = _obs("six seven eight nine ten")
    store.note_candidate(b, a, 0.95)
    store.note_candidate(e, d, 0.9)
    _fake_brain(monkeypatch, '<pair id="1" verdict="merge" /><pair id="2" verdict="merge" />')
    rep = _run(curator.consolidate(T, _settings()))
    assert rep["merged"] == 1
    superseded = [x for x in (b, e) if _row(x)["superseded_by"]]
    assert len(superseded) == 1                     # the second merge waits for the next run
    assert len(_pending()) == 1


def test_max_pairs_cap(cur, armed, monkeypatch):
    armed.setenv("CODER_CURATOR_MAX_PAIRS", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    a = _obs("alpha beta gamma delta")
    b = _obs("alpha beta gamma delta echo")
    d = _obs("kilo lima mike november")
    e = _obs("kilo lima mike november oscar")
    store.note_candidate(b, a, 0.95)
    store.note_candidate(e, d, 0.9)
    _fake_brain(monkeypatch, '<pair id="1" verdict="distinct" /><pair id="2" verdict="distinct" />')
    rep = _run(curator.consolidate(T, _settings()))
    assert rep["decided"] == 1                      # only the top-scored pair was shown
    assert len(_pending()) == 1


def test_cross_tenant_pair_is_never_arbitrated(cur, armed, monkeypatch):
    a = _obs("tenant default row about deploys")
    b = _obs("tenant other row about deploys", tenant="other")
    store.note_candidate(b, a, 0.99)                # a hand-made cross-tenant pair
    _fake_brain(monkeypatch, '<pair id="1" verdict="merge" />')
    rep = _run(curator.consolidate(T, _settings()))
    assert rep["decided"] == 0 and rep["brain"] is False
    assert len(_pending()) == 1                     # untouched, for the human console
    assert _row(a)["superseded_by"] == 0 and _row(b)["superseded_by"] == 0


def test_already_superseded_pair_is_marked_without_acting(cur, armed, monkeypatch):
    a = _obs("old canonical about caching")
    b = _obs("already absorbed about caching")
    c = _obs("fresh row about caching")
    store.supersede(b, a)
    store.note_candidate(c, b, 0.9)                 # its 'canonical' is itself superseded
    _fake_brain(monkeypatch, '<pair id="1" verdict="merge" />')
    rep = _run(curator.consolidate(T, _settings()))
    assert rep["decided"] == 0 and rep["merged"] == 0
    assert _row(c)["superseded_by"] == 0            # C was not hidden
    assert any(x["observation_id"] == c and x["status"] == "merged"
               for x in store.candidates("merged"))


# ---------------------------------------------------------------- (5) search hiding

def test_search_hides_superseded_on_both_legs(cur, armed, monkeypatch):
    a = _obs("redis cache eviction policy notes")
    b = _obs("redis cache eviction policy details")
    _fake_brain(monkeypatch, '<pair id="1" verdict="merge" />')
    store.note_candidate(b, a, 0.95)
    _run(curator.consolidate(T, _settings()))
    store.revive(b)                                 # bring it back so the FTS leg has it too
    assert _row(b)["superseded_by"] == 0
    store.supersede(b, a)
    # FTS5 leg
    ids = [r["id"] for r in search.search(T, "redis cache eviction")["observations"]]
    assert a in ids and b not in ids
    # LIKE fallback leg (no FTS5)
    monkeypatch.setattr(store, "_fts_ok", False)
    ids = [r["id"] for r in search.search(T, "redis cache eviction")["observations"]]
    assert a in ids and b not in ids
    # the primer's recent block and layer 3
    assert all(r["id"] != b for r in store.recent_observations(T, limit=10))
    assert _row(b) is not None and _row(b)["superseded_by"] == a    # explicit fetch still works


def test_timeline_hides_superseded(cur, armed, monkeypatch):
    a = _obs("timeline neighbour one")
    b = _obs("timeline neighbour two")
    store.supersede(b, a)
    t = search.timeline(T, None, depth_before=10)
    assert all(r["id"] != b for r in t["rows"])
    assert any(r["id"] == a for r in t["rows"])
    t2 = search.timeline(T, str(b))                 # a superseded anchor resolves to nothing
    assert t2["rows"] == []


# ---------------------------------------------------------------- (6) promote

def test_promotion_creates_a_skill_in_the_same_call(cur, armed, monkeypatch):
    for i in range(3):
        _obs(f"deploy checklist step {i} verify")
    a = _obs("deploy checklist step one verify")
    b = _obs("deploy checklist step one verified")
    store.note_candidate(b, a, 0.95)
    _fake_brain(monkeypatch,
                '<pair id="1" verdict="distinct" />'
                '<skill action="create" name="deploy-checklist" '
                'description="How to run the deploy checklist">1. pull. 2. verify.</skill>')
    rep = _run(curator.consolidate(T, _settings()))
    assert rep["skills"] == 1 and rep["decided"] == 1
    assert any(s["name"] == "deploy-checklist" for s in skills_store.listing(T))
    assert store.skills_count() == 1


def test_promotion_update_needs_the_listing(cur, armed, monkeypatch):
    _obs("routine row one")
    a = _obs("flask deploy runbook details")
    b = _obs("flask deploy runbook notes")
    store.note_candidate(b, a, 0.95)
    _fake_brain(monkeypatch,
                '<pair id="1" verdict="dismiss" />'
                '<skill action="create" name="flask-deploy" description="The flask deploy runbook">body</skill>')
    rep = _run(curator.consolidate(T, _settings()))
    assert rep["skills"] == 1
    assert skills_store.read(T, "flask-deploy")["body"] == "body"
    # the update run: the brain may target ONLY a skill the CURRENT SKILLS list carried
    _fake_brain(monkeypatch,
                '<pair id="1" verdict="distinct" />'
                '<skill action="update" name="flask-deploy" description="The flask deploy runbook">better body</skill>')
    rep0 = _run(curator.consolidate(T, _settings()))          # no pending pairs: no call, no writes
    assert rep0["brain"] is False and rep0["skills"] == 0
    d = _obs("gunicorn workers tuning notes")
    e = _obs("gunicorn workers tuning count")
    store.note_candidate(e, d, 0.9)                           # a fresh pair brings the brain back
    rep2 = _run(curator.consolidate(T, _settings()))
    assert rep2["skills"] == 1
    assert skills_store.read(T, "flask-deploy")["body"] == "better body"
    # an update for a skill that was NEVER listed is refused even with pairs on the table
    _fake_brain(monkeypatch,
                '<pair id="1" verdict="distinct" />'
                '<skill action="update" name="ghost-skill" description="Never existed">hijack</skill>')
    rep3 = _run(curator.consolidate(T, _settings()))
    assert rep3["skills"] == 0
    assert all(s["name"] != "ghost-skill" for s in skills_store.listing(T))


def test_promotion_respects_coder_skills_off(cur, armed, monkeypatch):
    armed.setenv("CODER_SKILLS", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    a = _obs("weekly report digest notes")
    b = _obs("weekly report digest summary")
    store.note_candidate(b, a, 0.95)
    _fake_brain(monkeypatch,
                '<pair id="1" verdict="merge" />'
                '<skill action="create" name="weekly-report" description="How the weekly report runs">x</skill>')
    rep = _run(curator.consolidate(T, _settings()))
    assert rep["merged"] == 1 and rep["skills"] == 0    # arbitration lived, promotion did not
    assert skills_store.listing(T) == []


def test_one_combined_brain_call_per_run(cur, armed, monkeypatch):
    calls: list = []
    a = _obs("one combined call pin older")
    b = _obs("one combined call pin newer")
    store.note_candidate(b, a, 0.95)
    _fake_brain(monkeypatch, '<pair id="1" verdict="distinct" />', calls)
    _run(curator.consolidate(T, _settings()))
    assert len(calls) == 1                          # arbitration + promotion in ONE call
    system, user = calls[0]
    assert system == prompts.curator_system()
    assert "PENDING PAIRS" in user and "MERGE BUDGET" in user


def test_stable_curator_prefix(cur):
    assert prompts.curator_system() == prompts.curator_system()   # the cheap-brain cache shape
    assert "verdict" in prompts.curator_system()


# ---------------------------------------------------------------- (7) gates

def test_due_gate(cur, armed):
    assert curator.due() is True                    # never ran: due the moment it is flipped
    store.mark_consumed(curator.LAST_RUN_KEY)
    assert curator.due() is False                   # fresh stamp
    with store.db(write=True) as c:
        c.execute("UPDATE consumed SET at='2020-01-01T00:00:00+0000' WHERE key=?",
                  (curator.LAST_RUN_KEY,))
    assert curator.due() is True                    # a week-old stamp
    with store.db(write=True) as c:
        c.execute("UPDATE consumed SET at='garbage' WHERE key=?", (curator.LAST_RUN_KEY,))
    assert curator.due() is True                    # malformed: run again (caps bound the run)


def test_tick_gates_and_stamp(cur, armed, monkeypatch):
    _obs("tick warmup row")                         # a tenant must exist for the run to list it
    _fake_brain(monkeypatch, "<skip_summary reason='nothing to curate' />")
    rep = _run(curator.tick(_settings()))           # armed + due: it runs (and decides nothing)
    assert rep["ran"] is True and rep["tenants"][0]["decided"] == 0
    assert store.last_run_at(curator.LAST_RUN_KEY)              # the stamp is written
    a = _obs("tick gate pair older")
    b = _obs("tick gate pair newer")
    store.note_candidate(b, a, 0.95)
    assert _run(curator.tick(_settings()))["ran"] is False      # freshly stamped: the gate blocks
    _fake_brain(monkeypatch, '<pair id="1" verdict="merge" />')
    rep = _run(curator.tick(_settings(), force=True))
    assert rep["ran"] is True and rep["tenants"][0]["decided"] == 1


def test_kill_switches(cur, monkeypatch):
    monkeypatch.setenv("CODER_DEDUP_MIN_DOCS", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    assert curator.armed() is False                 # coder_curator defaults OFF
    assert _run(curator.tick(_settings())) == {"ran": False}
    monkeypatch.setenv("CODER_CURATOR", "true")
    get_settings.cache_clear()
    assert curator.armed() is True
    monkeypatch.setenv("CODER_ENABLED", "false")    # the master switch rules everything
    get_settings.cache_clear()
    assert curator.armed() is False
    assert _run(curator.tick(_settings())) == {"ran": False}


def test_package_exports_curator():
    """The v0.478 lesson: the worker calls coder.curator.tick on the PACKAGE path."""
    assert callable(coder.curator.tick)
    assert "curator" in coder.__all__


def test_curator_routes_mounted():
    import inspect

    from app.coder import service
    src = inspect.getsource(service)
    assert '@r.get("/curator")' in src and '@r.post("/curator/run")' in src
    assert "if not curator.armed():" in src          # the kill switch is absolute at the route


def test_curator_route_live(cur, monkeypatch):
    async def _nok(request):
        return None
    from app.coder.service import make_router
    app = FastAPI()
    app.include_router(make_router(_nok, lambda: T))
    client = TestClient(app)
    got = client.get("/api/coder/curator").json()
    assert got["armed"] is False and got["due"] is False          # coder_curator defaults OFF
    assert got["vault"] == {"pending": 0, "merged": 0, "distinct": 0, "dismissed": 0,
                            "superseded": 0}
    assert got["config"]["coder_curator"] is False
    off = client.post("/api/coder/curator/run").json()
    assert off["ran"] is False and "coder_curator" in off["error"]
    monkeypatch.setenv("CODER_CURATOR", "true")
    monkeypatch.setenv("CODER_DEDUP_MIN_DOCS", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    _obs("route live pair older")
    _obs("route live pair newer")
    with store.db(write=True) as c:                   # a pending pair with a known verdict
        a = c.execute("SELECT id FROM observations WHERE title LIKE '%older%'").fetchone()[0]
        b = c.execute("SELECT id FROM observations WHERE title LIKE '%newer%'").fetchone()[0]
    store.note_candidate(b, a, 0.95)
    _fake_brain(monkeypatch, '<pair id="1" verdict="merge" />')
    ran = client.post("/api/coder/curator/run").json()
    assert ran["ran"] is True and ran["tenants"][0]["merged"] == 1
    got2 = client.get("/api/coder/curator").json()
    assert got2["armed"] is True and got2["vault"]["superseded"] == 1


# ---------------------------------------------------------------- version

def test_version_stamps():
    import re as _re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    main = (root / "app" / "main.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "0.550.0"' in main
    pubspec = (root.parent / "pubspec.yaml").read_text(encoding="utf-8")
    m = _re.search(r"version:\s*(\S+)", pubspec)
    assert m and m.group(1) == "0.550.0+573"
