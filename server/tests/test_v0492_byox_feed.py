"""v0.492.0 BYOX FEED: the 31 skill files reach already-seeded tenants (own stamp), Hinglish routing, card asks."""
from __future__ import annotations

import pytest


@pytest.fixture()
def desk(env, monkeypatch, tmp_path):
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_SKILLS", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    from app.coder import skills_store, store
    get_settings.cache_clear()
    store.ensure()
    skills_store.reset_for_tests()
    yield monkeypatch
    skills_store.reset_for_tests()
    get_settings.cache_clear()


def test_seed_files_exclude_byox_and_byox_files_are_31():
    from app.coder import skill_packs
    assert len(skill_packs.seed_files()) == 11   # the 10 class-level starters + uiux-pro-max (v0.494, healed on the rebase; byox rides its own feed lane)
    assert len(skill_packs.byox_files()) == 31


def test_seed_byox_reaches_a_tenant_already_seeded(desk):
    from app.coder import skill_packs, skills_store, store
    from app.config import get_settings
    get_settings.cache_clear()
    T = "byox-t1"
    store.ensure()
    store.mark_consumed(skill_packs.SEED_STAMP.format(T))          # the old once-ever stamp is already set
    r = skill_packs.seed_byox(T)
    assert r["byox_seeded"] == 31
    assert skill_packs.seed_byox(T)["byox_seeded"] == 0            # own stamp: never twice
    names = {s["name"] for s in skills_store.listing(T)}
    assert "byox-git" in names and len(names) == 31


def test_seed_byox_hers_win(desk):
    from app.coder import skill_packs, skills_store
    T = "byox-t2"
    skills_store.create(T, "byox-git", "Her own git notes", "her words")
    skill_packs.seed_byox(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "byox-git")
    assert row["description"] == "Her own git notes"


def test_seed_byox_switch_off(desk):
    monkeypatch = desk
    from app.coder import skill_packs
    from app.config import get_settings
    monkeypatch.setenv("BYOX_ENABLED", "false")
    get_settings.cache_clear()
    assert skill_packs.seed_byox("byox-t3")["byox_seeded"] == 0
    get_settings.cache_clear()


def test_desk_route_seeds_byox():
    import inspect
    from app.coder import service
    # v0.494: the desk calls seed_all, which runs the starters, BYOX and the Claude pack (each its own stamp)
    from app.coder import skill_packs
    assert "seed_all(tenant)" in inspect.getsource(service)
    assert "seed_byox" in [f.__name__ for f in skill_packs._pack_seeders()]   # found by name


def test_hinglish_asks_admit_byox():
    from app.agent import admit
    for text in ("mujhe database khud se banana sikhao", "ek shell scratch se banana hai",
                 "मुझे ब्लॉकचेन खुद से बनाना सिखाओ", "docker kaise banate hain"):
        assert "byox" in admit._match(text.lower()), text


def test_card_has_byox_asks_and_set_is_valid():
    from app.quality import tool_asks as T
    assert T.check() == []
    ids = [a["id"] for a in T.ASKS if a["id"].startswith("byox_")]
    assert len(ids) >= 8


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.904.0"


def test_coder_routes_work_with_the_real_sync_require_key(desk):
    """main.require_key is a plain function; every route used to `await` it and 500 live."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.coder.service import make_router
    from app.main import require_key as real_key
    app = FastAPI()
    app.include_router(make_router(lambda _req: None, lambda _req: "sync-t"))
    got = TestClient(app).get("/api/coder/skills")
    assert got.status_code == 200
    assert len([s for s in got.json()["skills"] if s["name"].startswith("byox-")]) == 31
    import inspect
    assert not inspect.iscoroutinefunction(real_key)
