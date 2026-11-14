"""v0.500.0 HOOLA SUPERPOWERS: the obra/superpowers process pack (15 sp-* seeds, MIT)
reaches already-seeded tenants via its OWN once-ever stamp - the v0.492 BYOX lesson,
third lane. The verbatim archive (LICENSE + skills/** complete, byte-verified at feed
time) rides under skillpack/upstream/obra-superpowers and never seeds."""
from __future__ import annotations

import os

import pytest

UPSTREAM = {"brainstorming", "diagnosing-superpowers", "dispatching-parallel-agents",
            "executing-plans", "finishing-a-development-branch", "receiving-code-review",
            "requesting-code-review", "subagent-driven-development", "systematic-debugging",
            "test-driven-development", "using-git-worktrees", "using-superpowers",
            "verification-before-completion", "writing-plans", "writing-skills"}


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


def test_four_lanes_counts_and_names():
    from app.coder import skill_packs
    seeds = skill_packs.seed_files()
    byox = skill_packs.byox_files()
    sp = skill_packs.sp_files()
    assert len(seeds) == 11                       # starters lane untouched by this feed
    assert len(byox) == 31
    assert len(sp) == 15
    assert {f.stem for f in sp} == {"sp-" + n for n in UPSTREAM}
    # no lane glob ever reaches the upstream/ archive subtree
    for files in (seeds, byox, sp):
        for f in files:
            assert os.sep not in f.name and not f.name.startswith("upstream")


def test_seed_files_exclude_sp():
    from app.coder import skill_packs
    names = {f.name for f in skill_packs.seed_files()}
    assert not any(n.startswith(("sp-", "byox-")) for n in names)


def test_seed_sp_reaches_a_tenant_already_seeded(desk):
    from app.coder import skill_packs, skills_store, store
    T = "sp-t1"
    store.ensure()
    store.mark_consumed(skill_packs.SEED_STAMP.format(T))   # the old once-ever stamp is already set
    store.mark_consumed(skill_packs.BYOX_STAMP.format(T))   # so is the BYOX one
    r = skill_packs.seed_sp(T)
    assert r["sp_seeded"] == 15                   # the new lane reaches her anyway
    assert skill_packs.seed_sp(T)["sp_seeded"] == 0          # own stamp: never twice
    names = {s["name"] for s in skills_store.listing(T)}
    assert "sp-systematic-debugging" in names and len(names) == 15
    assert names == {"sp-" + n for n in UPSTREAM}


def test_seed_sp_hers_win(desk):
    from app.coder import skill_packs, skills_store
    T = "sp-t2"
    skills_store.create(T, "sp-systematic-debugging", "Her own debugging notes", "her words")
    skill_packs.seed_sp(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "sp-systematic-debugging")
    assert row["description"] == "Her own debugging notes"


def test_seed_sp_switch_off(desk):
    monkeypatch = desk
    from app.coder import skill_packs
    from app.config import get_settings
    monkeypatch.setenv("SP_ENABLED", "false")
    get_settings.cache_clear()
    assert skill_packs.seed_sp("sp-t3")["sp_seeded"] == 0
    get_settings.cache_clear()


def test_desk_route_seeds_sp():
    import inspect
    from app.coder import service, skill_packs
    assert "seed_all(tenant)" in inspect.getsource(service)           # v0.494: the desk calls seed_all ...
    assert "seed_sp" in [f.__name__ for f in skill_packs._pack_seeders()]   # ... which finds the superpowers lane by name


def test_desk_route_returns_all_four_lanes(desk):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.coder.service import make_router
    app = FastAPI()
    app.include_router(make_router(lambda _req: None, lambda _req: "sync-t"))
    got = TestClient(app).get("/api/coder/skills")
    assert got.status_code == 200
    names = [s["name"] for s in got.json()["skills"]]
    from app.coder import skill_packs
    assert len(names) == len(skill_packs.all_seed_files()) + len(skill_packs.claude_dirs())   # 11 starters + 31 byox + 15 sp + 2 prog + 3 fe + 2 cs + 1 mg + 2 bd + 1 cr (v0.514) + the 18 omni families (v0.561) + the Claude pack
    assert len([n for n in names if n.startswith("sp-")]) == 15
    assert len([n for n in names if n.startswith("byox-")]) == 31


def test_archive_is_verbatim_and_never_executes():
    from app.coder import skill_packs
    arch = os.path.join(os.path.dirname(skill_packs.__file__), "skillpack",
                        "upstream", "obra-superpowers")
    assert os.path.exists(os.path.join(arch, "LICENSE"))          # the MIT text itself ships
    assert os.path.exists(os.path.join(arch, "PROVENANCE.md"))
    import json
    plugin = json.load(open(os.path.join(arch, ".claude-plugin", "plugin.json"), encoding="utf-8"))
    assert plugin["license"] == "MIT" and plugin["version"] == "7.0.2"
    skills_dir = os.path.join(arch, "skills")
    got = {d for d in os.listdir(skills_dir)
           if os.path.exists(os.path.join(skills_dir, d, "SKILL.md"))}
    assert got == UPSTREAM                        # all 15, byte-verified at feed time


def test_seeds_carry_upstream_words_not_the_scripts():
    """The distilled seeds keep upstream's iron laws; the bundled SCRIPTS ride only in
    the archive. Seeds may QUOTE commands (git worktree add, pytest -q) - that is the
    advice; what they may not be is executable code."""
    from app.coder import skill_packs
    for f in skill_packs.sp_files():
        raw = f.read_text(encoding="utf-8")
        assert raw.startswith("---\nname: sp-")   # frontmatter name carries the lane
        assert not raw.lstrip("#\n").startswith("#!")          # no shebang
        assert "def main(" not in raw and "if __name__" not in raw
        assert "subprocess.run(" not in raw and "os.system(" not in raw


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.909.0"
