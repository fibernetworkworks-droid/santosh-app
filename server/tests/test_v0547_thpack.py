"""v0.547.0 TH PACK: the awesome Theory read turned into two fed skills -
th-vision-lane (awesome-vlm-architectures as Hoola's vision-lane syllabus:
the PC operator IS a screenshot->action model - one action per turn, the
semantic lane before the pixel lane, grounding on the CURRENT screenshot,
the golden-suite eval) and th-agent-research (awesome-agi-cocosci as the
agent-architecture research loop: the catalog's vocabulary mapped onto
Hoola's real doors - graph engine, crew, dhara, stores - the EK pattern
EK probe law, printed metrics, the adopt|park|kill ledger). Own once-ever
stamp, the v0.492 pattern; the seed never overwrites hers."""
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


def test_seed_files_exclude_th_and_th_files_are_2():
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
    th = skill_packs.th_files()
    assert len(th) == 2
    assert {f.stem for f in th} == {"th-vision-lane", "th-agent-research"}


def test_seed_thpack_reaches_a_tenant_already_seeded(desk):
    from app.coder import skill_packs, skills_store, store
    T = "th-t1"
    store.ensure()
    store.mark_consumed(skill_packs.SEED_STAMP.format(T))    # the old once-ever stamps
    store.mark_consumed(skill_packs.BYOX_STAMP.format(T))    # ALL NINE are set -
    store.mark_consumed(skill_packs.PROG_STAMP.format(T))    # the th stamp is NOT
    store.mark_consumed(skill_packs.SP_STAMP.format(T))
    store.mark_consumed(skill_packs.FE_STAMP.format(T))
    store.mark_consumed(skill_packs.CS_STAMP.format(T))
    store.mark_consumed(skill_packs.MG_STAMP.format(T))
    store.mark_consumed(skill_packs.BD_STAMP.format(T))
    store.mark_consumed(skill_packs.CR_STAMP.format(T))
    r = skill_packs.seed_thpack(T)
    assert r["th_seeded"] == 2
    assert skill_packs.seed_thpack(T)["th_seeded"] == 0      # own stamp: never twice
    names = {s["name"] for s in skills_store.listing(T)}
    assert names == {"th-vision-lane", "th-agent-research"}


def test_seed_thpack_hers_win(desk):
    from app.coder import skill_packs, skills_store
    T = "th-t2"
    skills_store.create(T, "th-vision-lane", "Her own vision notes", "her words")
    skill_packs.seed_thpack(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "th-vision-lane")
    assert row["description"] == "Her own vision notes"


def test_seed_thpack_switch_off(desk):
    monkeypatch = desk
    from app.coder import skill_packs
    from app.config import get_settings
    monkeypatch.setenv("THPACK_ENABLED", "false")
    get_settings.cache_clear()
    assert skill_packs.seed_thpack("th-t3")["th_seeded"] == 0
    get_settings.cache_clear()


def test_pack_seeders_finds_thpack():
    from app.coder import service
    from app.coder import skill_packs
    assert "seed_all(tenant)" in inspect.getsource(service)                      # the desk calls seed_all ...
    assert "seed_thpack" in [f.__name__ for f in skill_packs._pack_seeders()]    # ... which finds this pack by name


def test_th_files_pass_the_lint_gate():
    from app.coder import skill_packs
    from app.coder.skills_store import DESC_MAX, BODY_MAX, parse_skill, validate
    for f in skill_packs.th_files():
        name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
        assert name == f.stem
        assert len(desc) <= DESC_MAX, (f.name, len(desc))
        assert len(body) <= BODY_MAX, (f.name, len(body))
        validate(desc, body)                             # raises on an over-long row


def test_vision_lane_pins_the_discipline():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.th_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "th-vision-lane":
            body = b
    for token in ("screenshot", "ONE action", "monitor", "ax_find",
                  "page_fill_form", "PIXEL", "SEMANTIC", "ground", "CAPTCHA",
                  "ask_approval", "stale", "NEVER", "golden", "bd-eval-benchmarks",
                  "SEARCH TERMS", "catalog", "unverified", "Claude (vision)"):
        assert token in body, token


def test_agent_research_pins_the_discipline():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.th_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "th-agent-research":
            body = b
    for token in ("AGI-CoCoSci", "catalog", "PROBE", "LEDGER", "adopt|park|kill",
                  "StateGraph", "interrupt", "checkpointers", "crew", "dhara",
                  "stores", "605", "printed", "NEVER", "unverified", "synthetic",
                  "PERCEPTION", "MEMORY", "REASONING", "ACTION", "source"):
        assert token in body, token


def test_vision_lane_matches_the_real_operator():
    """The skill teaches the PC operator's REAL doors (the never-invent law,
    applied to the vision lane): every tool/word the skill names must exist in
    server/app/pc/operator.py - the catalog-vs-real cross-check."""
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.th_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "th-vision-lane":
            body = b
    src = (REPO_ROOT / "server" / "app" / "pc" / "operator.py").read_text(encoding="utf-8")
    for door in ("ax_find", "page_fill_form", "ask_approval", "screenshot",
                 "monitor", "ONE action", "CAPTCHA"):
        assert door in src, door                        # the real operator has it
        assert door in body, door                       # the skill teaches it


def test_agent_research_matches_the_real_engine():
    """The research skill maps the catalog's vocabulary onto Hoola's REAL engine
    doors - aep.graph (StateGraph/interrupt/Command), the crew port, and the
    registry count the body quotes (554). Registry badle to test chillayega,
    body + test same commit me refresh (the zoo-numbers law)."""
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.th_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "th-agent-research":
            body = b
    graph_src = (REPO_ROOT / "server" / "app" / "aep" / "graph.py").read_text(encoding="utf-8")
    for door in ("StateGraph", "interrupt", "Command", "add_conditional_edges",
                 "MemorySaver", "SqliteSaver"):
        assert door in graph_src, door                  # the real engine has it
        assert door in body, door                       # the skill teaches it
    assert (REPO_ROOT / "server" / "app" / "crew" / "crew.py").exists()
    from app.agent import tools
    assert len(tools.TOOLS) == 626, "625 + 1 pdf_kit (v0.807 HOOLA DOCUMENT KIT). 623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " + ("582 (their v0.588 base incl. paisa_sahayak) + 2 sandarbh (v0.589 SANDARBH MANCH: workspace + kgmemory). Was: registry moved - refresh th-agent-research's "
                                     "'abhi 569' and this pin in the SAME commit + 1 reach (v0.559 REACH MANCH) + 1 speckit (v0.569 SPEC SUTRA)")


def test_injection_matches_a_theory_ask(desk):
    from app.coder import inject, skill_packs
    T = "th-t4"
    skill_packs.seed_thpack(T)
    block = inject.skills_block(T, "pc ki screen dekh ke action lo screenshot operator vision")
    assert "th-vision-lane" in block
    block2 = inject.skills_block(T, "agent architecture ka naya pattern research probe karo")
    assert "th-agent-research" in block2
