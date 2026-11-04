"""v0.495.0 PROG PACK: the vetted-library registry + the windows script lane reach every
tenant (own once-ever stamp, the v0.492 pattern), the registry never invents a package
name, the script lane never self-runs."""
from __future__ import annotations

import inspect

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


def test_seed_files_exclude_prog_and_prog_files_are_2():
    from app.coder import skill_packs
    assert len(skill_packs.seed_files()) == 11          # 11 here: uiux-pro-max joined the starters lane (v0.498)
    assert len(skill_packs.byox_files()) == 31          # the BYOX pack is untouched
    prog = skill_packs.prog_files()
    assert len(prog) == 2
    assert {f.stem for f in prog} == {"prog-library-registry", "prog-windows-script-lane"}


def test_seed_progpack_reaches_a_tenant_already_seeded(desk):
    from app.coder import skill_packs, skills_store, store
    from app.config import get_settings
    get_settings.cache_clear()
    T = "prog-t1"
    store.ensure()
    store.mark_consumed(skill_packs.SEED_STAMP.format(T))    # the old once-ever stamps are set
    store.mark_consumed(skill_packs.BYOX_STAMP.format(T))    # (both) - the prog stamp is NOT
    r = skill_packs.seed_progpack(T)
    assert r["prog_seeded"] == 2
    assert skill_packs.seed_progpack(T)["prog_seeded"] == 0  # own stamp: never twice
    names = {s["name"] for s in skills_store.listing(T)}
    assert names == {"prog-library-registry", "prog-windows-script-lane"}


def test_seed_progpack_hers_win(desk):
    from app.coder import skill_packs, skills_store
    T = "prog-t2"
    skills_store.create(T, "prog-library-registry", "Her own registry notes", "her words")
    skill_packs.seed_progpack(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "prog-library-registry")
    assert row["description"] == "Her own registry notes"


def test_seed_progpack_switch_off(desk):
    monkeypatch = desk
    from app.coder import skill_packs
    from app.config import get_settings
    monkeypatch.setenv("PROGPACK_ENABLED", "false")
    get_settings.cache_clear()
    assert skill_packs.seed_progpack("prog-t3")["prog_seeded"] == 0
    get_settings.cache_clear()


def test_desk_route_seeds_progpack():
    from app.coder import service, skill_packs
    assert "seed_all(tenant)" in inspect.getsource(service)           # v0.494: the desk calls seed_all ...
    assert "seed_progpack" in [f.__name__ for f in skill_packs._pack_seeders()]  # ... which finds the PROG pack by name


def test_prog_files_pass_the_lint_gate():
    from app.coder import skill_packs
    from app.coder.skills_store import DESC_MAX, BODY_MAX, parse_skill, validate
    for f in skill_packs.prog_files():
        name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
        assert name == f.stem
        assert len(desc) <= DESC_MAX, (f.name, len(desc))
        assert len(body) <= BODY_MAX, (f.name, len(body))
        validate(desc, body)                             # raises on an over-long row


def test_registry_never_invents_and_names_real_packages():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.prog_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "prog-library-registry":
            body = b
    assert body
    for pkg in ("requests", "httpx", "beautifulsoup4", "openpyxl", "pandas",
                "pypdf", "reportlab", "pdfplumber", "python-docx", "Pillow",
                "flask", "fastapi", "pytest"):
        assert pkg in body, pkg
    assert "pypi.org" in body                            # the verify-before-naming door
    assert "NEVER" in body                               # the never-invent law is pinned


def test_script_lane_pins_the_three_lanes_and_the_law():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.prog_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "prog-windows-script-lane":
            body = b
    for token in ("ax_", "AutoHotkey v2", "#Requires AutoHotkey v2.0", "AutoIt", "VBA",
                  "gated run door", "NEVER"):
        assert token in body, token


def test_injection_matches_a_code_ask(desk):
    from app.coder import inject, skill_packs
    T = "prog-t4"
    skill_packs.seed_progpack(T)
    block = inject.skills_block(T, "excel sheet ke liye python script library batao")
    assert "prog-library-registry" in block
    block2 = inject.skills_block(T, "autohotkey script likho is app ke liye")
    assert "prog-windows-script-lane" in block2
