"""v0.485.0 HOOLA SAPNE - the nightly curator (OpenClaw's dreaming sweep ported).

What this suite pins, piece by piece:
(1) STORE: the dreams_state clock (per tenant x kind), the obs_preimages undo line (exact prior
    text, restore puts it back), the deep rewrite keeps the row id, the candidate query only
    ever names tenants with fresh RAW rows (the curator's own output never re-enters).
(2) KILL SWITCHES: coder_dreams default OFF, coder_enabled gates everything - disarmed means
    zero passes, zero brain calls, zero files.
(3) THE LIGHT PASS: raw rows in the window -> at most coder_dreams_max_writes curated rows via
    store.store_observation actor='dreams' (the same dedup ladder + primer + yaad_khojo reach);
    budget respected; empty window books the run and never calls the brain; a private latest
    prompt skips politely; the usage gate refuses before anything else.
(4) THE DEEP PASS: an ALREADY CURATED title restated -> obs_update_curated rewrites THAT row
    (same id, preimage row first); a failed update falls through to the funnel (the Tier-0
    title merge turns it into a reinforce - the fact is never lost nor duplicated).
(5) REVIEWABLE: every run appends a dated section to dreams/<tenant>/dreams.md and the previous
    file text survives as dreams.md.pre; per-tenant conv buckets keep two tenants' identical
    curated facts in two rows (no cross-tenant dedup ever).
(6) SCHEDULING: light throttle after a run, deep wins when both due, the worker's coder_jobs
    awaits dreams.tick.
(7) THE ROUTE: GET /api/coder/dreams returns the digest; with the switch off it says so.
(8) VERSION: APP_VERSION == "0.692.0".
"""
import asyncio
import os

import pytest

from app import coder
from app.coder import capture, dreams, store
from app.coder.observer import _call_brain as _unused_brain_ref  # noqa: F401 (monkeypatch target doc)

T = "default"
T2 = "meghana"

OBS_XML = ("<observation><type>decision</type><title>She wants reminders at 7:30 every morning</title>"
           "<subtitle>standing preference</subtitle><facts><fact>time 07:30</fact></facts>"
           "<narrative>She asked for the morning briefing at 7:30 daily.</narrative>"
           "<concepts><concept>how-it-works</concept></concepts></observation>")
OBS2_XML = ("<observation><type>discovery</type><title>The kirana shop closes at 9 pm</title>"
            "<subtitle>local fact</subtitle><facts><fact>closes 21:00</fact></facts>"
            "<narrative>She mentioned the shop timing.</narrative>"
            "<concepts><concept>how-it-works</concept></concepts></observation>")
SIX_OBS = "".join(
    f'<observation><type>discovery</type><title>Durable fact number {i} worth keeping</title>'
    f"<subtitle>budget filler</subtitle><facts><fact>fact {i}</fact></facts>"
    f'<narrative>Filler {i}.</narrative></observation>' for i in range(6))


@pytest.fixture()
def dr(env, monkeypatch, tmp_path):
    """Fresh vault in a TEMP dir, dreams ON, stats empty. (env = the house fresh-DB fixture.)"""
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_DREAMS", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    store.ensure()
    dreams.reset_for_tests()
    yield monkeypatch
    dreams.reset_for_tests()
    get_settings.cache_clear()


def _seed_raw(tenant: str, conv: str, n: int = 2) -> None:
    """Raw material inside the window (capture's own funnel: redaction already done)."""
    for i in range(n):
        store.store_observation(conv, tenant, {
            "type": "discovery", "title": f"Raw note {tenant} {i} about her delivery timings",
            "subtitle": "seeded", "facts": [f"fact {i}"], "narrative": f"seeded narrative {i}",
            "concepts": [], "files_read": [], "files_modified": []}, actor="observer")


def _brain(monkeypatch, text: str, calls: list | None = None):
    async def fake(system, user, settings):
        if calls is not None:
            calls.append((system, user))
        return text
    monkeypatch.setattr("app.coder.observer._call_brain", fake)


# ---------------------------------------------------------------- (1) store

def test_dreams_state_roundtrip(dr):
    assert store.dreams_state_get(T, "light") == {"last_epoch": 0, "runs": 0}
    store.dreams_state_set(T, "light", 12345)
    assert store.dreams_state_get(T, "light")["last_epoch"] == 12345
    store.dreams_state_set(T, "light", 23456)
    assert store.dreams_state_get(T, "light")["last_epoch"] == 23456
    assert store.dreams_state_get(T, "light")["runs"] == 2
    assert store.dreams_state_get(T, "deep") == {"last_epoch": 0, "runs": 0}


def test_preimage_roundtrip_restores_exact_text(dr):
    oid = store.store_observation("c1", T, {"type": "decision", "title": "Original title",
                                            "subtitle": "before", "facts": ["f1"],
                                            "narrative": "the original narrative"})
    assert oid is not None
    assert store.obs_preimage(oid, "test why") is True
    assert store.obs_preimage(999999, "ghost") is False      # a preimage of nothing is a lie
    new = {"title": "Original title", "subtitle": "after", "facts": ["f2"],
           "narrative": "the rewritten narrative", "concepts": []}
    assert store.obs_update_curated(oid, new, "deep") == oid
    row = store.get_observations([oid])[0]
    assert row["narrative"] == "the rewritten narrative" and row["subtitle"] == "after"
    pres = store.obs_preimages_for(oid)
    # TWO undo lines: the explicit snapshot + the rewrite's own mandatory preimage
    assert len(pres) == 2 and pres[0]["pre_narrative"] == "the original narrative"
    assert pres[0]["why"] == "deep"          # the rewrite's preimage names its pass
    assert store.obs_restore_preimage(pres[0]["id"]) == oid
    row2 = store.get_observations([oid])[0]
    assert row2["narrative"] == "the original narrative" and row2["subtitle"] == "before"


def test_tenants_candidate_query_excludes_dreams_rows(dr):
    _seed_raw(T, "conv_a")
    store.store_observation("dreams-default", T, {"type": "decision", "title": "Curated only row",
                                                  "narrative": "curated"}, actor="dreams")
    assert T in store.tenants_with_rows_since(0)
    # a tenant whose ONLY rows are the curator's own output is never a candidate
    store.store_observation("dreams-only", T2, {"type": "decision", "title": "Curated only",
                                                "narrative": "x"}, actor="dreams")
    assert T2 not in store.tenants_with_rows_since(0)


# ---------------------------------------------------------------- (2) kill switches

def test_kill_switch_default_off(dr, monkeypatch):
    monkeypatch.setenv("CODER_DREAMS", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert dreams.armed() is False
    calls: list = []
    _brain(monkeypatch, OBS_XML, calls)
    res = asyncio.run(dreams.tick(type("S", (), {})()))
    assert res == {"ok": False, "reason": "disarmed"}
    assert calls == [] and dreams.stats()["runs"] == 0


def test_coder_enabled_gates_everything(dr, monkeypatch):
    monkeypatch.setenv("CODER_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert dreams.armed() is False
    co = dreams.consolidate(T, "light")          # a no-op coroutine: never touches the vault
    assert asyncio.iscoroutine(co)
    co.close()


# ---------------------------------------------------------------- (3) the light pass

def test_light_pass_writes_curated_rows(dr, monkeypatch):
    _seed_raw(T, "conv_a", 3)
    calls: list = []
    _brain(monkeypatch, OBS_XML + OBS2_XML, calls)
    res = asyncio.run(dreams.consolidate(T, "light"))
    assert res["ok"] and res["kind"] == "light" and res["written"] == 2
    rows = store.curated_recent(T, 10)
    assert len(rows) == 2
    titles = {r["title"] for r in rows}
    assert "She wants reminders at 7:30 every morning" in titles
    allrows = store.observations_since(T, 0, 50)
    assert all(r["actor"] == "dreams" or r["conv"] == "conv_a" for r in allrows)
    assert len(calls) == 1
    sys_p, user_p = calls[0]
    assert "nightly curator" in sys_p and "Raw note default 0" in user_p


def test_budget_respected(dr, monkeypatch):
    _seed_raw(T, "conv_a", 2)
    _brain(monkeypatch, SIX_OBS)                    # six blocks; budget is 4
    res = asyncio.run(dreams.consolidate(T, "light"))
    assert res["written"] == 4
    assert len(store.curated_recent(T, 10)) == 4


def test_empty_window_books_the_run_and_never_calls_the_brain(dr, monkeypatch):
    calls: list = []
    _brain(monkeypatch, OBS_XML, calls)
    res = asyncio.run(dreams.consolidate(T, "light"))
    assert res == {"ok": True, "reason": "no-rows"}
    assert calls == []
    assert store.dreams_state_get(T, "light")["runs"] == 1
    assert dreams.stats()["skipped"] == 1


def test_private_window_skips_politely(dr, monkeypatch):
    capture.session_started(T, "conv_p", "chat")
    capture.turn_prompt(T, "conv_p", "<private>she whispered something personal</private>")
    _seed_raw(T, "conv_a", 1)
    calls: list = []
    _brain(monkeypatch, OBS_XML, calls)
    res = asyncio.run(dreams.consolidate(T, "light"))
    assert res == {"ok": True, "reason": "private"}
    assert calls == [] and len(store.curated_recent(T, 10)) == 0


def test_usage_gate_refuses_first(dr, monkeypatch):
    import app.usage as usage
    monkeypatch.setattr(usage, "allowed", lambda tenant, feature: False)
    _seed_raw(T, "conv_a", 1)
    calls: list = []
    _brain(monkeypatch, OBS_XML, calls)
    res = asyncio.run(dreams.consolidate(T, "light"))
    assert res == {"ok": False, "reason": "usage"}
    assert calls == []


# ---------------------------------------------------------------- (4) the deep pass

def test_deep_pass_rewrites_matching_curated_row(dr, monkeypatch):
    oid = store.store_observation("dreams-default", T, {
        "type": "decision", "title": "She wants reminders at 7:30 every morning",
        "subtitle": "old wording", "facts": ["old"], "narrative": "OLD NARRATIVE"}, actor="dreams")
    _seed_raw(T, "conv_a", 1)
    _brain(monkeypatch, OBS_XML)                    # restates the SAME normalized title
    res = asyncio.run(dreams.consolidate(T, "deep"))
    assert res["ok"] and res["rewritten"] == 1 and res["written"] == 0
    row = store.get_observations([oid])[0]
    assert row["id"] == oid and "OLD" not in row["narrative"] and row["subtitle"] == "standing preference"
    assert len(store.obs_preimages_for(oid)) == 1   # the undo line exists
    assert dreams.stats()["preimages"] == 1


def test_deep_failed_update_falls_through_to_reinforce(dr, monkeypatch):
    oid = store.store_observation("dreams-default", T, {
        "type": "decision", "title": "She wants reminders at 7:30 every morning",
        "narrative": "OLD"}, actor="dreams")
    _seed_raw(T, "conv_a", 1)
    monkeypatch.setattr(store, "obs_update_curated", lambda *a, **k: None)   # the rewrite fails
    _brain(monkeypatch, OBS_XML)
    res = asyncio.run(dreams.consolidate(T, "deep"))
    assert res["rewritten"] == 0 and res["written"] == 1    # the funnel caught it
    rows = [r for r in store.get_observations([oid]) ]
    assert rows[0]["occurrence_count"] == 2                 # reinforced, never duplicated


# ---------------------------------------------------------------- (5) reviewable + isolation

def test_digest_appends_and_preimage_file(dr, monkeypatch):
    _seed_raw(T, "conv_a", 1)
    _brain(monkeypatch, OBS_XML)
    asyncio.run(dreams.consolidate(T, "light"))
    d1 = dreams.read_digest(T)
    assert "light" in d1 and "She wants reminders at 7:30 every morning" in d1
    _seed_raw(T, "conv_b", 1)
    _brain(monkeypatch, OBS2_XML)
    asyncio.run(dreams.consolidate(T, "light"))
    d2 = dreams.read_digest(T)
    assert "kirana" in d2 and d1 in d2                       # append, never truncate
    with open(dreams.digest_path(T) + ".pre", "r", encoding="utf-8") as f:
        assert f.read() == d1                                # the file-level undo line


def test_tenant_buckets_never_meet(dr, monkeypatch):
    _seed_raw(T, "conv_a", 1)
    _seed_raw(T2, "conv_z", 1)
    _brain(monkeypatch, OBS_XML)
    asyncio.run(dreams.consolidate(T, "light"))
    asyncio.run(dreams.consolidate(T2, "light"))
    a = store.curated_recent(T, 10)
    b = store.curated_recent(T2, 10)
    assert len(a) == 1 and len(b) == 1                       # identical fact, TWO rows
    assert a[0]["id"] != b[0]["id"]
    assert {r["id"] for r in a}.isdisjoint({r["id"] for r in b})


# ---------------------------------------------------------------- (6) scheduling

def test_light_throttles_after_a_run(dr, monkeypatch):
    _seed_raw(T, "conv_a", 1)
    store.dreams_state_set(T, "deep", int(__import__("time").time()))   # deep not due tonight
    assert dreams.due(T) == "light"
    _brain(monkeypatch, OBS_XML)
    asyncio.run(dreams.consolidate(T, "light"))
    assert dreams.due(T) is None                             # tonight's work is done


def test_deep_wins_when_both_due(dr, monkeypatch):
    store.dreams_state_set(T, "light", int(__import__("time").time()))    # light just ran
    store.dreams_state_set(T, "deep", 1)                                  # deep overdue
    assert dreams.due(T) == "deep"


def test_worker_coder_jobs_awaits_dreams_tick(dr, monkeypatch):
    called = {"n": 0}

    async def fake_tick(settings, max_passes: int = 1):
        called["n"] += 1
        return {"ok": True}

    monkeypatch.setattr("app.coder.dreams.tick", fake_tick)
    from app import worker
    asyncio.run(worker.coder_jobs())
    assert called["n"] == 1


# ---------------------------------------------------------------- (7) the route

def test_dreams_route_returns_digest(dr, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.coder.service import make_router

    _seed_raw(T, "conv_a", 1)
    _brain(monkeypatch, OBS_XML)
    asyncio.run(dreams.consolidate(T, "light"))

    async def allow(request):
        return None
    app = FastAPI()
    app.include_router(make_router(allow, lambda request: T))
    c = TestClient(app)
    res = c.get("/api/coder/dreams").json()
    assert "She wants reminders at 7:30" in res["digest"]
    assert res["state"]["light"]["runs"] == 1

    monkeypatch.setenv("CODER_DREAMS", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    res2 = c.get("/api/coder/dreams").json()
    assert res2["digest"] == "" and "switched off" in res2["note"]


# ---------------------------------------------------------------- (8) version

def test_version_stamp(dr):
    from app.main import APP_VERSION
    assert APP_VERSION == "0.692.0"
