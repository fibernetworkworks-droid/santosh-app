"""CLAUDE SKILLS - FIX SEEDING: a user's skills are installed on her FIRST memory-block build (chat turn or
call start), not only when she opens the Skill Desk. Pins: (1) the first turn seeds all three packs and the
matched skill rides that same turn; (2) later turns pay nothing; (3) exactly-once - a skill she deleted does
not come back; (4) internal tenants ('_packs', '__quality__') are never auto-seeded; (5) the switches still
turn it off, and turning one back on works without a restart; (6) the voice path seeds too; (7) the desk uses
the same function; (8) a failing pack is retried next turn, never remembered as done.
"""
import pytest

from app.coder import inject, skill_packs, skills_store, store

T = "firstturn-user"


@pytest.fixture()
def desk(env, monkeypatch, tmp_path):
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_SKILLS", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    store.ensure()
    skills_store.reset_for_tests()
    skill_packs.reset_for_tests()
    yield monkeypatch
    skills_store.reset_for_tests()
    skill_packs.reset_for_tests()
    get_settings.cache_clear()


def _count(tenant=T):
    return len(skills_store.listing(tenant))


def test_first_turn_seeds_everything_and_the_skill_rides_that_turn(desk):
    assert _count() == 0
    block = inject.turn_block(T, "conv1", query="write this week's status report for my team")
    assert _count() == len(skill_packs.seed_files()) + len(skill_packs.byox_files()) + len(skill_packs.prog_files()) + len(skill_packs.sp_files()) + len(skill_packs.fe_files()) + len(skill_packs.cs_files()) + len(skill_packs.mg_files()) + len(skill_packs.bd_files()) + len(skill_packs.claude_dirs())
    assert "internal-comms" in block                        # found on the SAME turn that seeded it


def test_second_turn_pays_nothing(desk, monkeypatch):
    inject.turn_block(T, "c1", query="status report")
    calls = []
    for name in ("seed", "seed_byox", "seed_claude"):
        monkeypatch.setattr(skill_packs, name, lambda t, n=name: calls.append(n) or {})
    inject.turn_block(T, "c1", query="status report")
    inject.turn_block(T, "c2", query="newsletter")
    assert calls == []


def test_deleted_skill_does_not_come_back(desk):
    inject.turn_block(T, "c1", query="x")
    skills_store.read(T, "internal-comms")
    skills_store.delete(T, "internal-comms")
    skill_packs.reset_for_tests()                           # a restart: the stamps, not the memo, must protect her
    inject.turn_block(T, "c1", query="status report")
    assert not any(s["name"] == "internal-comms" for s in skills_store.listing(T))


def test_internal_tenants_never_auto_seeded(desk):
    for t in ("_packs", "__quality__", "__skillcard__", ""):
        assert skill_packs.seed_all(t) == {}
        inject.turn_block(t, "c", query="status report") if t else None
    assert _count("_packs") == 0 and _count("__quality__") == 0


def test_switches_turn_it_off_and_back_on_without_restart(desk):
    from app.config import get_settings
    desk.setenv("CODER_SKILLS_SEED", "false")
    get_settings.cache_clear()
    inject.turn_block(T, "c1", query="status report")
    assert _count() == 0
    desk.setenv("CODER_SKILLS_SEED", "true")
    get_settings.cache_clear()
    inject.turn_block(T, "c1", query="status report")
    assert _count() == len(skill_packs.seed_files()) + len(skill_packs.byox_files()) + len(skill_packs.prog_files()) + len(skill_packs.sp_files()) + len(skill_packs.fe_files()) + len(skill_packs.cs_files()) + len(skill_packs.mg_files()) + len(skill_packs.bd_files()) + len(skill_packs.claude_dirs())
    desk.setenv("CODER_SKILLS", "false")
    get_settings.cache_clear()
    assert inject.turn_block("other-user", "c1", query="status report") == "" and _count("other-user") == 0


def test_voice_path_seeds_too(desk):
    assert _count("caller") == 0
    inject.voice_block("caller", "call1", query="status report")
    assert _count("caller") == len(skill_packs.seed_files()) + len(skill_packs.byox_files()) + len(skill_packs.prog_files()) + len(skill_packs.sp_files()) + len(skill_packs.fe_files()) + len(skill_packs.cs_files()) + len(skill_packs.mg_files()) + len(skill_packs.bd_files()) + len(skill_packs.claude_dirs())


def test_desk_route_uses_the_same_function():
    import inspect

    from app.coder import service
    src = inspect.getsource(service)
    assert "skill_packs.seed_all(tenant)" in src and "seed_byox(tenant)" not in src


def test_failing_pack_is_retried_not_remembered(desk, monkeypatch):
    def boom(t):
        raise RuntimeError("disk full")
    monkeypatch.setattr(skill_packs, "seed_claude", boom)
    inject.turn_block(T, "c1", query="status report")                      # must not raise
    assert not any(s["name"] == "internal-comms" for s in skills_store.listing(T))
    monkeypatch.undo()
    desk.setenv("CODER_ENABLED", "true")
    desk.setenv("CODER_SKILLS", "true")
    inject.turn_block(T, "c1", query="status report")                      # next turn heals
    assert any(s["name"] == "internal-comms" for s in skills_store.listing(T))


def test_seed_all_finds_every_pack_by_name():
    """A new pack follows the convention (a seed_<pack>(tenant) function) and needs no edit to seed_all."""
    names = {f.__name__ for f in skill_packs._pack_seeders()}
    assert {"seed", "seed_byox", "seed_claude", "seed_progpack", "seed_sp", "seed_fepack"} <= names
    assert "seed_all" not in names and "seed_files" not in names
