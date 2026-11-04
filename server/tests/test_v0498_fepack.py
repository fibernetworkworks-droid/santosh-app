"""v0.498.0 FE PACK: the awesome Front-End read turned into three fed skills - the
HyperFrames template packs (charts + motion assembled, check cheap before render),
the campaign email templates (proven structures, her facts only), and the Hoola UI
kit tokens (every surface one Night Glass family). Own once-ever stamp, the v0.492
pattern; the seed never overwrites hers."""
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


def test_seed_files_exclude_fe_and_fe_files_are_3():
    from app.coder import skill_packs
    assert len(skill_packs.seed_files()) == 10          # the starter library is untouched
    assert len(skill_packs.byox_files()) == 31          # the BYOX pack is untouched
    assert len(skill_packs.prog_files()) == 2           # the PROG pack is untouched
    fe = skill_packs.fe_files()
    assert len(fe) == 3
    assert {f.stem for f in fe} == {"fe-frames-templates", "fe-email-templates", "fe-ui-kit"}


def test_seed_fepack_reaches_a_tenant_already_seeded(desk):
    from app.coder import skill_packs, skills_store, store
    T = "fe-t1"
    store.ensure()
    store.mark_consumed(skill_packs.SEED_STAMP.format(T))    # the old once-ever stamps
    store.mark_consumed(skill_packs.BYOX_STAMP.format(T))    # all three are set -
    store.mark_consumed(skill_packs.PROG_STAMP.format(T))    # the fe stamp is NOT
    r = skill_packs.seed_fepack(T)
    assert r["fe_seeded"] == 3
    assert skill_packs.seed_fepack(T)["fe_seeded"] == 0      # own stamp: never twice
    names = {s["name"] for s in skills_store.listing(T)}
    assert names == {"fe-frames-templates", "fe-email-templates", "fe-ui-kit"}


def test_seed_fepack_hers_win(desk):
    from app.coder import skill_packs, skills_store
    T = "fe-t2"
    skills_store.create(T, "fe-ui-kit", "Her own token notes", "her words")
    skill_packs.seed_fepack(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "fe-ui-kit")
    assert row["description"] == "Her own token notes"


def test_seed_fepack_switch_off(desk):
    monkeypatch = desk
    from app.coder import skill_packs
    from app.config import get_settings
    monkeypatch.setenv("FEPACK_ENABLED", "false")
    get_settings.cache_clear()
    assert skill_packs.seed_fepack("fe-t3")["fe_seeded"] == 0
    get_settings.cache_clear()


def test_desk_route_seeds_fepack():
    from app.coder import service
    assert "seed_fepack(tenant)" in inspect.getsource(service)


def test_fe_files_pass_the_lint_gate():
    from app.coder import skill_packs
    from app.coder.skills_store import DESC_MAX, BODY_MAX, parse_skill, validate
    for f in skill_packs.fe_files():
        name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
        assert name == f.stem
        assert len(desc) <= DESC_MAX, (f.name, len(desc))
        assert len(body) <= BODY_MAX, (f.name, len(body))
        validate(desc, body)                             # raises on an over-long row


def test_frames_pack_pins_the_discipline():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.fe_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "fe-frames-templates":
            body = b
    for token in ("CHECK", "render", "determinism", "1920x1080", "1080x1920",
                  "safe margins", "action=check", "action=render", "NEVER",
                  "fe-ui-kit"):
        assert token in body, token


def test_email_pack_pins_the_lane_and_the_law():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.fe_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "fe-email-templates":
            body = b
    for token in ("email_draft", "markdown=true", "email_bulk", "kalam",
                  "approval card", "[blank", "45 chars", "NEVER", "OTP"):
        assert token in body, token


def test_ui_kit_pins_the_real_tokens():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.fe_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "fe-ui-kit":
            body = b
    # the tokens are the REAL values from lib/ui/glass.dart class C, not invented
    for token in ("#FFB15C", "#7C5CFF", "#F4F2FF", "#B9B3DA", "#0B0A1A", "#120E2A",
                  "#1B1030", "#C055F5", "#34D399", "#F87171", "#FFD9A8",
                  "Sora", "NEVER", "7:1"):
        assert token in body, token
    # cross-check against the source of truth itself
    from pathlib import Path
    glass = (Path(__file__).resolve().parents[2] / "lib" / "ui" / "glass.dart").read_text(encoding="utf-8")
    for hexv in ("0xFFFFB15C", "0xFF7C5CFF", "0xFFF4F2FF", "0xFF0B0A1A"):
        assert hexv in glass, hexv


def test_injection_matches_a_front_end_ask(desk):
    from app.coder import inject, skill_packs
    T = "fe-t4"
    skill_packs.seed_fepack(T)
    block = inject.skills_block(T, "reels ke liye charts wali video banao mp4")
    assert "fe-frames-templates" in block
    block2 = inject.skills_block(T, "diwali offer ka email template likho campaign ke liye")
    assert "fe-email-templates" in block2
    block3 = inject.skills_block(T, "video aur card ke colors Hoola ke brand jaise rakho")
    assert "fe-ui-kit" in block3
