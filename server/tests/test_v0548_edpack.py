"""v0.549.0 ED PACK: the awesome Editors read turned into two fed skills -
ed-vscode-cockpit (drive Hoola from inside the IDE: the palette first -
every command by NAME, quick open, the ax tree over pixels, the integrated
terminal, the problems panel as printed evidence) and ed-neovim-cockpit
(the modal grammar: mode first, buffers/windows, the key lane one
key-sequence per turn, the terminal's printed output as evidence). The
owner's line: editors are already semantically controllable via ax_*.
Own once-ever stamp, the v0.492 pattern; the seed never overwrites hers."""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_seed_files_exclude_ed_and_ed_files_are_2():
    from app.coder import skill_packs
    assert len(skill_packs.seed_files()) == 11          # the starter lane is untouched
    assert len(skill_packs.byox_files()) == 31          # the BYOX pack is untouched
    assert len(skill_packs.prog_files()) == 2           # the PROG pack is untouched
    assert len(skill_packs.sp_files()) == 15            # the superpowers lane is untouched
    assert len(skill_packs.fe_files()) == 3             # the FE pack is untouched
    assert len(skill_packs.cs_files()) == 2             # the CS pack is untouched
    assert len(skill_packs.mg_files()) == 1             # the magic21 pack is untouched
    assert len(skill_packs.bd_files()) == 2             # the Big Data pack is untouched
    assert len(skill_packs.cr_files()) == 1             # the crew pack is untouched
    assert len(skill_packs.th_files()) == 2             # the Theory pack is untouched
    ed = skill_packs.ed_files()
    assert len(ed) == 2
    assert {f.stem for f in ed} == {"ed-vscode-cockpit", "ed-neovim-cockpit"}


def test_seed_edpack_reaches_a_tenant_already_seeded(desk):
    from app.coder import skill_packs, skills_store, store
    T = "ed-t1"
    store.ensure()
    store.mark_consumed(skill_packs.SEED_STAMP.format(T))    # the old once-ever stamps
    store.mark_consumed(skill_packs.BYOX_STAMP.format(T))    # ALL TEN are set -
    store.mark_consumed(skill_packs.PROG_STAMP.format(T))    # the ed stamp is NOT
    store.mark_consumed(skill_packs.SP_STAMP.format(T))
    store.mark_consumed(skill_packs.FE_STAMP.format(T))
    store.mark_consumed(skill_packs.CS_STAMP.format(T))
    store.mark_consumed(skill_packs.MG_STAMP.format(T))
    store.mark_consumed(skill_packs.BD_STAMP.format(T))
    store.mark_consumed(skill_packs.CR_STAMP.format(T))
    store.mark_consumed(skill_packs.TH_STAMP.format(T))
    r = skill_packs.seed_edpack(T)
    assert r["ed_seeded"] == 2
    assert skill_packs.seed_edpack(T)["ed_seeded"] == 0      # own stamp: never twice
    names = {s["name"] for s in skills_store.listing(T)}
    assert names == {"ed-vscode-cockpit", "ed-neovim-cockpit"}


def test_seed_edpack_hers_win(desk):
    from app.coder import skill_packs, skills_store
    T = "ed-t2"
    skills_store.create(T, "ed-vscode-cockpit", "Her own cockpit notes", "her words")
    skill_packs.seed_edpack(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "ed-vscode-cockpit")
    assert row["description"] == "Her own cockpit notes"


def test_seed_edpack_switch_off(desk):
    monkeypatch = desk
    from app.coder import skill_packs
    from app.config import get_settings
    monkeypatch.setenv("EDPACK_ENABLED", "false")
    get_settings.cache_clear()
    assert skill_packs.seed_edpack("ed-t3")["ed_seeded"] == 0
    get_settings.cache_clear()


def test_pack_seeders_finds_edpack():
    from app.coder import service
    from app.coder import skill_packs
    assert "seed_all(tenant)" in inspect.getsource(service)                      # the desk calls seed_all ...
    assert "seed_edpack" in [f.__name__ for f in skill_packs._pack_seeders()]    # ... which finds this pack by name


def test_ed_files_pass_the_lint_gate():
    from app.coder import skill_packs
    from app.coder.skills_store import DESC_MAX, BODY_MAX, parse_skill, validate
    for f in skill_packs.ed_files():
        name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
        assert name == f.stem
        assert len(desc) <= DESC_MAX, (f.name, len(desc))
        assert len(body) <= BODY_MAX, (f.name, len(body))
        validate(desc, body)                             # raises on an over-long row


def test_vscode_cockpit_pins_the_discipline():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.ed_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "ed-vscode-cockpit":
            body = b
    for token in ("COMMAND PALETTE", "Ctrl+Shift+P", "QUICK OPEN", "Ctrl+P",
                  "ax_find", "INTEGRATED TERMINAL", "PROBLEMS", "ask_approval",
                  "NEVER", "semantic", "pixel", "stale", "printed",
                  "Awesome-vscode", "THE LAWS", "ek turn ek editor action"):
        assert token in body, token


def test_neovim_cockpit_pins_the_discipline():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.ed_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "ed-neovim-cockpit":
            body = b
    for token in ("MODE", "normal", "insert", "command", "BUFFERS", ":ls", ":b",
                  ":w", ":q!", "ask_approval", "MACROS", "%s/old/new/gc",
                  "NEVER", "printed", "Awesome-neovim", "THE GRAMMAR",
                  "ek turn ek key-sequence", "insert mode me akhead"):
        assert token in body, token


def test_cockpits_match_the_real_operator():
    """The cockpit skills teach the PC operator's REAL semantic doors (the
    never-invent law): every tool the skills name must exist in
    server/app/pc/operator.py - the editor IS drivable through the doors
    the operator already has."""
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    bodies = {}
    for f in skill_packs.ed_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        bodies[name] = b
    src = (REPO_ROOT / "server" / "app" / "pc" / "operator.py").read_text(encoding="utf-8")
    for door in ("ax_find", "ask_approval", "screenshot", "key", "type"):
        assert door in src, door                        # the real operator has it
    for door in ("ax_find", "ask_approval", "screenshot"):
        assert door in bodies["ed-vscode-cockpit"], door    # the skill teaches it


def test_injection_matches_an_editor_ask(desk):
    from app.coder import inject, skill_packs
    T = "ed-t4"
    skill_packs.seed_edpack(T)
    block = inject.skills_block(T, "vs code editor ke andar se kaam karao palette terminal")
    assert "ed-vscode-cockpit" in block
    block2 = inject.skills_block(T, "neovim vim modal buffer terminal se save karo")
    assert "ed-neovim-cockpit" in block2
