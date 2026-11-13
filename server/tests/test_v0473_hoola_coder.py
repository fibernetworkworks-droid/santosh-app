"""v0.473.0 HOOLA CODER - persistent session memory for Santosh, the claude-mem architecture
ported into the house stack (owner: 'I WANT EVERYTHING FROM THIS FOR HOOLA CODER').

What the port keeps from claude-mem, piece by piece:
(1) CAPTURE: the tool funnel (santosh._run_tool) spools one atomic event per completed call -
    fail-open, redacted at the boundary, the session can never notice a memory failure.
(2) SPOOL: filename IS the dedupe key, exactly-once via consumed markers stamped only after the
    row commits, 7-day retry window, corrupt/ and expired/ quarantine.
(3) OBSERVER: a stateful per-session conversation with the CHEAPEST existing brain; batches of
    tool events in, XML observations out; noise sentinels consume for free; prose is salvaged as
    a discovery; 3 consecutive failures park the session; overflow recycles the history.
(4) VAULT: SQLite + FTS5 external-content tables with triggers; the dedup ladder (exact content
    hash -> normalized title Tier-0 merge with reinforcement -> TF-IDF near-duplicate CANDIDATES
    with an IDF veto, never auto-merged); prompts table anchors the privacy gate.
(5) SEARCH: the three-layer discipline - search (index) -> timeline (neighbourhood) ->
    get_observations (full rows), with any-term widening and a LIKE fallback without FTS5.
(6) INJECT: the session-start primer (voice 10k cap, chat-turn compact 1.6k) rides AFTER the
    KAAM YAAD block, never instead of it; whole-item budget fitter; kill switch = silence.
(7) PRIVACY: <private> blocks stripped at every boundary, ~13 secret patterns masked BEFORE
    spool/model/store, and a wholly-redacted turn marks the conversation so nothing from it
    is stored. Secrets never reach the memory file - the Hoola golden floor, now for memory.
Kill switch coder_enabled: off = nothing is written or read (capture, observe, inject, routes).
"""
import asyncio
import json
import os
from types import SimpleNamespace

import pytest

from app import coder
from app.coder import capture, dedup, inject, observer, parser, prompts, redact, search, spool, store

T = "default"
CONV = "conv_coder"


def _settings(**over) -> SimpleNamespace:
    base = dict(coder_enabled=True, coder_observe=True, coder_dir="./data/coder", coder_mode="code",
                coder_batch_max=6, coder_retain_days=0, anthropic_api_key="")
    base.update(over)
    return SimpleNamespace(**base)


@pytest.fixture()
def cod(env, monkeypatch):
    """Fresh vault + fresh RAM session state + the kill switch ON for this test only.
    observer._call_brain is restored afterwards - a brain fake must never leak between tests."""
    monkeypatch.setenv("CODER_ENABLED", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    store.ensure()
    observer.reset_for_tests()
    real_brain = observer._call_brain
    yield
    observer._call_brain = real_brain
    observer.reset_for_tests()
    get_settings.cache_clear()


def _obs_xml(title: str = "Order flow now validates replayed envelopes", typ: str = "bugfix",
             facts: str = "<fact>deal.py checks the seal freshness</fact>") -> str:
    return (f"<observation><type>{typ}</type><title>{title}</title>"
            f"<subtitle>the duplicate 400 is dead</subtitle><facts>{facts}</facts>"
            f"<narrative>Replayed envelopes were accepted twice; the seal check now refuses them.</narrative>"
            f"<concepts><concept>problem-solution</concept><concept>how-it-works</concept></concepts>"
            f"<files_read><file>server/app/net/deal.py</file></files_read>"
            f"<files_modified><file>server/app/net/chain.py</file></files_modified></observation>")


def _summ_xml() -> str:
    return ("<summary><request>fix the duplicate envelope bug</request>"
            "<investigated>chain.py and deal.py</investigated>"
            "<learned>the seal freshness window was 15 min but replay checked only the id</learned>"
            "<completed>replay check added, tests pin it</completed>"
            "<next_steps>run the full hoola sweep</next_steps>"
            "<notes>none</notes></summary>")


# ---------------------------------------------------------------- 1. settings + kill switch

def test_settings_defaults():
    from app.config import Settings
    s = Settings()
    assert s.coder_enabled is True and s.coder_observe is True
    assert s.coder_batch_max == 6 and s.coder_retain_days == 0 and s.coder_mode == "code"


def test_kill_switch_means_nothing_is_written(cod, monkeypatch):
    monkeypatch.setenv("CODER_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    capture.tool_observed(T, CONV, "get_weather", {"city": "Indore"}, {"ok": True}, True, 12, "t1")
    capture.turn_prompt(T, CONV, "save this forever")
    capture.session_started(T, CONV, "chat")
    capture.session_ended(T, CONV)
    assert store.stats()["observations"] == 0 and store.stats()["tool_uses"] == 0
    assert store.session_row(CONV) is None
    assert store.stats()["sessions"] == 0
    assert inject.turn_block(T, CONV) == "" and inject.voice_block(T, CONV) == ""


# ---------------------------------------------------------------- 2. capture + redaction

def test_capture_redacts_before_spool_and_store(cod):
    secret = "the key is sk-ant-api95-VERYSECRETKEY123456"
    capture.tool_observed(T, CONV, "run_command", {"cmd": f"deploy --token {secret}"},
                          {"out": secret}, True, 20, "t1", "owner")
    files = spool.drain()
    assert len(files) == 1
    raw = open(os.path.join(spool.root(), files[0]["_file"])).read()
    assert "VERYSECRETKEY" not in raw and "redacted" in raw
    with store.db() as c:
        row = c.execute("SELECT args_brief, line FROM tool_uses WHERE conv=?", (CONV,)).fetchone()
    assert "VERYSECRETKEY" not in row["args_brief"] and "VERYSECRETKEY" not in row["line"]


def test_strip_private_removes_blocks_and_marks_the_turn(cod):
    assert redact.strip_private("hello <private>secret plan</private> world") == "hello  world"
    assert redact.strip_private("a <private>never closed") == "a "       # unbalanced drops to the end
    capture.turn_prompt(T, CONV, "<private>everything this turn</private>")
    assert store.latest_prompt_private(CONV) is True
    capture.tool_observed(T, CONV, "run_command", {"x": "1"}, "result", True, 5, "t1")
    assert spool.drain()                                  # events spool (fail-open) ...
    observer._session(CONV, T)["pending"] = observer._session(CONV, T)["pending"][:0]
    assert observer._store_observations(CONV, T, _obs_xml(), coder.modes.load_mode(), "t1", "owner", 0) == 0


def test_secret_patterns_masked_labels_survive(cod):
    t = redact.redact_secrets("password=hunter2 and otp is 4821 and AKIAIOSFODNN7EXAMPLE "
                              "-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----")
    assert "hunter2" not in t and "4821" not in t and "AKIAIOSFODNN7" not in t and "abc" not in t
    assert "password=" in t and "otp" in t                 # labels survive, values never do


# ---------------------------------------------------------------- 3. spool semantics

def test_spool_dedupe_key_and_exactly_once(cod):
    ev = {"conv": CONV, "tool": "get_weather", "args": {"city": "Indore"}, "result": "31c",
          "turn_id": "t1", "seq": 1, "at": "now", "ok": True}
    assert spool.spool_event("observation", ev) and spool.spool_event("observation", ev)
    assert len([f for f in os.listdir(spool.root()) if f.endswith(".json")]) == 1   # filename IS the key
    drained = spool.drain()
    assert len(drained) == 1
    spool.consume(drained[0]["_file"])
    assert not os.path.exists(os.path.join(spool.root(), drained[0]["_file"]))
    assert spool.is_consumed(drained[0]["_file"]) is True


def test_spool_too_big_dropped_never_queued(cod):
    assert spool.spool_event("observation", {"conv": CONV, "result": "x" * (2 * 1024 * 1024)}) is False
    assert spool.drain() == []


# ---------------------------------------------------------------- 4. dedup ladder

def test_dedup_exact_hash_reconfirms(cod):
    a = store.store_observation(CONV, T, {"type": "bugfix", "title": "Same fact", "narrative": "same words"})
    b = store.store_observation(CONV, T, {"type": "bugfix", "title": "Same fact", "narrative": "same words"})
    assert a == b
    with store.db() as c:
        r = c.execute("SELECT occurrence_count FROM observations WHERE id=?", (a,)).fetchone()
    assert r[0] == 2


def test_dedup_tier0_title_merge_reinforces(cod):
    a = store.store_observation("conv1", T, {"type": "bugfix", "title": "Replay Check Added to Chain",
                                             "narrative": "first wording"})
    b = store.store_observation("conv2", T, {"type": "feature", "title": "replay check ADDED to chain!",
                                             "narrative": "totally different wording"})
    assert a == b                                          # same normalized title = THE same memory
    with store.db() as c:
        r = c.execute("SELECT occurrence_count, last_reinforced, reinforcement_dates FROM observations "
                      "WHERE id=?", (a,)).fetchone()
    assert r[0] == 2 and r[1] and len(json.loads(r[2])) == 1


def test_dedup_idf_veto_and_candidates(cod):
    # the symmetric difference carries only COMMON words -> no veto: a candidate for review
    df = lambda t: 1 if t == "chaindb" else 50
    score, dup, veto = dedup.classify_pair("migrate the chaindb index", "migrate the chaindb schema",
                                           df, 100)
    assert dup is True and veto is None and score >= 0.80
    # the rare token on ONE side only vetoes the merge - even when the cosine alone would pass
    common = " ".join(f"word{i}" for i in range(35))     # 35 shared common-weight tokens
    score2, dup2, veto2 = dedup.classify_pair("chaindb " + common, common + " extra", df, 100)
    assert score2 >= 0.80 and dup2 is False and veto2 == "chaindb"
    store.note_candidate(11, 7, 0.91)
    assert store.candidates()[0]["observation_id"] == 11   # review-only, never auto-merged


# ---------------------------------------------------------------- 5. parser

def test_parser_extracts_capped_and_validated(cod):
    mode = coder.modes.load_mode()
    obs = parser.parse_observations(_obs_xml() + _obs_xml("Another one", "not-a-type"),
                                    {t["id"] for t in mode["observation_types"]},
                                    set(mode["observation_concepts"]))
    assert len(obs) == 2
    assert obs[1]["type"] == "discovery"                   # invalid type falls back, fact survives
    assert obs[0]["concepts"] == ["problem-solution", "how-it-works"]
    assert parser.parse_summary(_summ_xml())["next_steps"] == "run the full hoola sweep"
    assert parser.parse_skip('<skip_summary reason="noise" />') == "noise"
    assert parser.salvage_prose("The deal cap moved to 2 crore in code.")[0]["schema_drift"] is True
    assert parser.salvage_prose("ok done") == []


# ---------------------------------------------------------------- 6. observer end to end

def _run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def test_observer_end_to_end_capture_to_summary(cod):
    calls = {"n": 0}

    async def brain(system, user, settings):
        calls["n"] += 1
        return _obs_xml() if calls["n"] == 1 else _summ_xml()

    observer._call_brain = brain                            # the injectable seam
    capture.turn_prompt(T, CONV, "fix the duplicate envelope bug")
    capture.session_started(T, CONV, "chat")
    capture.tool_observed(T, CONV, "run_command", {"cmd": "pytest -q"}, "82 passed", True, 900, "t1", "owner")
    st = _run(observer.tick(_settings()))
    assert st["observed"] == 1 and st["drained"] == 1
    rows = store.recent_observations(T)
    assert rows and rows[0]["title"] == "Order flow now validates replayed envelopes"
    assert rows[0]["discovery_tokens"] > 0
    assert not spool.drain()                                # the spool file was consumed AFTER the commit
    capture.session_ended(T, CONV)
    st2 = _run(observer.tick(_settings()))
    assert st2["summaries"] == 1
    s = store.last_summary(T, CONV)
    assert s["request"] == "fix the duplicate envelope bug" and s["next_steps"] == "run the full hoola sweep"
    assert store.session_row(CONV)["status"] == "completed"


def test_observer_noise_consumed_free_and_prose_salvaged(cod):
    outs = ['<skip_summary reason="noise" />', "Just a routine status check, nothing durable here."]
    idx = {"n": 0}

    async def brain(system, user, settings):
        v = outs[min(idx["n"], 1)]
        idx["n"] += 1
        return v

    observer._call_brain = brain
    capture.tool_observed(T, CONV, "get_weather", {"city": "Indore"}, "31c", True, 5, "t1")
    st = _run(observer.tick(_settings()))
    assert st["noise"] == 1 and store.stats()["observations"] == 0
    capture.tool_observed(T, CONV, "get_weather", {"city": "Ujjain"}, "29c", True, 5, "t2")
    st2 = _run(observer.tick(_settings()))
    assert st2["observed"] == 1                             # prose becomes ONE discovery, not a drop
    rows = store.recent_observations(T)
    assert rows[0]["title"].startswith("Just a routine status check")


def test_observer_no_brain_leaves_spooled_and_parks_after_three(cod):
    n = {"count": 0}

    async def brain(system, user, settings):
        n["count"] += 1
        raise RuntimeError("no coder brain available")

    observer._call_brain = brain
    capture.tool_observed(T, CONV, "run_command", {"cmd": "x"}, "y", True, 1, "t1")
    st = _run(observer.tick(_settings()))
    assert st["observed"] == 0 and len(spool.drain()) == 1  # the event waits, nothing is lost
    st2 = _run(observer.tick(_settings()))                  # failure 2...
    st3 = _run(observer.tick(_settings()))                  # failure 3 -> parked
    assert n["count"] == 3 and len(spool.drain()) == 1
    s = observer._session(CONV, T)
    assert s["parked_until"] > 0
    assert _run(observer.tick(_settings()))["observed"] == 0    # parked: no call this tick


def test_observer_recycles_history_on_overflow(cod):
    observer._session(CONV, T)["history"] = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "x" * (observer.MAX_CONVERSATION_CHARS + 10)},
        {"role": "assistant", "content": "y"},
    ]
    observer._recycle(observer._session(CONV, T), "sys")
    h = observer._session(CONV, T)["history"]
    assert h[0]["role"] == "system" and len(h) <= 3 and "trimmed" in h[-1]["content"]


# ---------------------------------------------------------------- 7. search: the three layers

def test_three_layers_search_timeline_fetch(cod):
    store.store_observation(CONV, T, {"type": "bugfix", "title": "Replay check added to envelope flow",
                                      "narrative": "seals refuse duplicates"})
    store.store_observation(CONV, T, {"type": "feature", "title": "Pickup code shown at handover",
                                      "narrative": "4-digit code required"})
    r = search.search(T, "replay envelope")
    assert r["total"] >= 1 and r["observations"][0]["title"].startswith("Replay check")
    assert "| ID |" in search.render_index(r)              # the index shape (50-100 tok/row)
    tl = search.timeline(T, str(r["observations"][0]["id"]), 2, 2)
    assert any(row["title"].startswith("Pickup code") for row in tl["rows"])
    full = search.get_observations([r["observations"][0]["id"]])
    assert full[0]["narrative"] == "seals refuse duplicates" and full[0]["facts"] == []
    assert search.search(T, "zzznothing")["total"] == 0


def test_work_state_roundtrip_and_primer(cod):
    # (wave 9: work lists are per tenant - one user's list never rides another user's primer)
    store.work_write("build", [{"text": "ship the coder module", "status": "doing"},
                               {"text": "old done thing", "status": "done"}], tenant=T)
    open_lists = store.work_read(tenant=T)
    assert list(open_lists) == ["build"] and len(open_lists["build"]) == 1   # done hidden by default
    assert len(store.work_read(include_closed=True, tenant=T)["build"]) == 2
    assert store.work_read(tenant="someone-else") == {}
    store.store_observation(CONV, T, {"type": "decision", "title": "Coder memory is server-side only",
                                      "narrative": "no APK surface in v1"})
    blk = inject.primer(T, CONV)
    assert blk.startswith(inject.HEADER) and "ship the coder module" in blk
    assert "Coder memory is server-side only" in blk and "[todo]" in blk or "[doing]" in blk


def test_primer_budget_fits_whole_items(cod):
    for i in range(40):
        store.store_observation(CONV, T, {"type": "discovery",
                                          "title": f"Observation number {i} about the network module",
                                          "narrative": "x" * 300})
    full = inject.primer(T, CONV)
    compact = inject.primer(T, CONV, compact=True)
    assert len(full) <= inject.VOICE_BUDGET and len(compact) <= inject.COMPACT_BUDGET
    assert full.count("\n") > 5 and compact.count("\n") >= 2     # rows survived the fit, never empty


# ---------------------------------------------------------------- 8. wiring pins (source-scrape)

def test_voice_block_rides_after_kaam_yaad_never_instead():
    src = open("app/voice.py").read()
    assert "coder.inject.voice_block" in src
    assert src.index("if kb:") < src.index("if cb:")       # KAAM block first, coder after
    assert "_coder_blk" in src and src.index("_coder_blk") < src.index("ymem, kb, cb, mcp_defs")


def test_capture_rides_the_tool_funnel_and_the_turn():
    src = open("app/agent/santosh.py").read()
    assert "_coder.tool_observed" in src
    funnel = src.index("_evlog.log_event(_ev_t, _ev_c, \"tool_result\"")   # inside _run_tool
    ret = src.index("    return out", funnel)                              # its exit
    assert funnel < src.index("_coder.tool_observed") < ret
    assert "_coder.turn_prompt" in src and "_coder.inject.turn_block" in src


def test_session_lifecycle_pins():
    vs = open("app/voice.py").read()
    assert "_coder.session_started" in vs and "_coder.session_ended" in vs
    assert vs.index("_coder.session_started") < vs.index("_coder.session_ended")  # start before end
    assert "coder.inject.voice_block" in vs            # the primer rides _build_context's gather
    ms = open("app/main.py").read()
    assert 'coder.session_started(tenant, cid, "chat")' in ms
    assert "if not incognito:" in ms and ms.index("if not incognito:") < ms.index('coder.session_started(tenant')
    assert "_coder_router(require_key, current_tenant)" in ms
    ws = open("app/worker.py").read()
    # (v0.662 every worker slot runs through the guarded slot loop: coder_jobs is one of its slots, not a bare await)
    assert ("await coder_jobs()" in ws or "coder_jobs" in ws) and "coder.observer.tick" in ws


def test_coder_routes_mounted(env):
    from app.main import app
    paths = {r.path for r in app.routes}
    for p in ("/api/coder/search", "/api/coder/timeline", "/api/coder/observations/batch",
              "/api/coder/work-state", "/api/coder/memory", "/api/coder/stats", "/api/coder/drain"):
        assert p in paths


# ---------------------------------------------------------------- 9. retention

def test_retention_typo_never_purges(cod):
    store.store_observation(CONV, T, {"type": "decision", "title": "keep me forever", "narrative": ""})
    store.forget_old("not-a-number")
    store.forget_old(0)
    store.forget_old(-5)
    assert store.stats()["observations"] == 1              # a typo must never turn into a purge


# ---------------------------------------------------------------- 10. version

def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.891.0"
