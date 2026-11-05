"""v0.502.0 CS PACK: the awesome Computer Science read turned into two fed skills -
the zoo expansion radar (catalog first, never invented model ids, the append shape
only the owner can apply) and the operator loop's dialogue/QA patterns (slot ledger,
repair ladder, close the loop). Own once-ever stamp, the v0.492 pattern; the seed
never overwrites hers."""
from __future__ import annotations

import inspect
import json
from pathlib import Path

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


def test_seed_files_exclude_cs_and_cs_files_are_2():
    from app.coder import skill_packs
    assert len(skill_packs.seed_files()) == 11          # the starter lane is untouched
    assert len(skill_packs.byox_files()) == 31          # the BYOX pack is untouched
    assert len(skill_packs.prog_files()) == 2           # the PROG pack is untouched
    assert len(skill_packs.sp_files()) == 15            # the superpowers lane is untouched
    assert len(skill_packs.fe_files()) == 3             # the FE pack is untouched
    cs = skill_packs.cs_files()
    assert len(cs) == 2
    assert {f.stem for f in cs} == {"cs-zoo-radar", "cs-dialogue-patterns"}


def test_seed_cspack_reaches_a_tenant_already_seeded(desk):
    from app.coder import skill_packs, skills_store, store
    T = "cs-t1"
    store.ensure()
    store.mark_consumed(skill_packs.SEED_STAMP.format(T))    # the old once-ever stamps
    store.mark_consumed(skill_packs.BYOX_STAMP.format(T))    # all five are set -
    store.mark_consumed(skill_packs.PROG_STAMP.format(T))    # the cs stamp is NOT
    store.mark_consumed(skill_packs.SP_STAMP.format(T))
    store.mark_consumed(skill_packs.FE_STAMP.format(T))
    r = skill_packs.seed_cspack(T)
    assert r["cs_seeded"] == 2
    assert skill_packs.seed_cspack(T)["cs_seeded"] == 0      # own stamp: never twice
    names = {s["name"] for s in skills_store.listing(T)}
    assert names == {"cs-zoo-radar", "cs-dialogue-patterns"}


def test_seed_cspack_hers_win(desk):
    from app.coder import skill_packs, skills_store
    T = "cs-t2"
    skills_store.create(T, "cs-zoo-radar", "Her own radar notes", "her words")
    skill_packs.seed_cspack(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "cs-zoo-radar")
    assert row["description"] == "Her own radar notes"


def test_seed_cspack_switch_off(desk):
    monkeypatch = desk
    from app.coder import skill_packs
    from app.config import get_settings
    monkeypatch.setenv("CSPACK_ENABLED", "false")
    get_settings.cache_clear()
    assert skill_packs.seed_cspack("cs-t3")["cs_seeded"] == 0
    get_settings.cache_clear()


def test_pack_seeders_finds_cspack():
    from app.coder import service
    from app.coder import skill_packs
    assert "seed_all(tenant)" in inspect.getsource(service)                      # the desk calls seed_all ...
    assert "seed_cspack" in [f.__name__ for f in skill_packs._pack_seeders()]    # ... which finds this pack by name


def test_cs_files_pass_the_lint_gate():
    from app.coder import skill_packs
    from app.coder.skills_store import DESC_MAX, BODY_MAX, parse_skill, validate
    for f in skill_packs.cs_files():
        name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
        assert name == f.stem
        assert len(desc) <= DESC_MAX, (f.name, len(desc))
        assert len(body) <= BODY_MAX, (f.name, len(body))
        validate(desc, body)                             # raises on an over-long row


def test_zoo_radar_pins_the_discipline():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.cs_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "cs-zoo-radar":
            body = b
    for token in ("436", "186 image", "221 video", "29 audio", "muapi", "kie",
                  "action=models", "model_id", "unverified", "curated studios",
                  "ZOO_MUAPI_KEY", "ZOO_KIE_KEY", "action=status", "NEVER",
                  "HOOLA_ZOO_CATALOG", "aspects"):
        assert token in body, token


def test_dialogue_pack_pins_the_patterns():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.cs_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "cs-dialogue-patterns":
            body = b
    for token in ("SLOT LEDGER", "CONFIRM BEFORE IRREVERSIBLE", "REPAIR LADDER",
                  "QA SHAPE", "CLOSE THE LOOP", "VOICE BUDGET", "EK sawaal",
                  "never-invent", "mujhe nahi pata", "NEVER", "Retry-spam",
                  "Silent failure"):
        assert token in body, token


def test_zoo_radar_numbers_match_the_real_catalog():
    """The baked 436/186/221/29 + gateway splits are the REAL catalog, not invention
    (the fe-ui-kit cross-check pattern). The test fails loudly when the catalog grows,
    so the skill's numbers get refreshed in the same commit as the catalog change."""
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    cat = json.loads((Path(__file__).resolve().parents[1] / "app" / "zoo_catalog.json")
                     .read_text(encoding="utf-8"))
    models = cat["models"]
    kinds: dict = {}
    gws: dict = {}
    for m in models:
        kinds[m.get("kind", "?")] = kinds.get(m.get("kind", "?"), 0) + 1
        gws[m.get("gateway", cat.get("gateway", "muapi"))] = \
            gws.get(m.get("gateway", cat.get("gateway", "muapi")), 0) + 1
    body = ""
    for f in skill_packs.cs_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "cs-zoo-radar":
            body = b
    assert f"{len(models)}-model" in body                       # 436
    assert f"{kinds.get('image', 0)} image" in body             # 186
    assert f"{kinds.get('video', 0)} video" in body             # 221
    assert f"{kinds.get('audio', 0)} audio" in body             # 29
    assert f"{gws.get('muapi', 0)}" in body and f"{gws.get('kie', 0)}" in body


def test_injection_matches_a_cs_ask(desk):
    from app.coder import inject, skill_packs
    T = "cs-t4"
    skill_packs.seed_cspack(T)
    block = inject.skills_block(T, "zoo mein naya model radar se dhoondo byok")
    assert "cs-zoo-radar" in block
    block2 = inject.skills_block(T, "customer se baat karte waqt ek hi sawaal dialogue pattern")
    assert "cs-dialogue-patterns" in block2
