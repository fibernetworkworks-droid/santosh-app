"""v0.512.0 BD PACK: the awesome Big Data read turned into two fed skills -
the public-dataset eval benchmarks for quality regression (golden sets from
SQuAD / 20 Newsgroups / IMDb / data.gov.in, the scored-run ledger, never an
invented golden answer) and the campaign-graph analytics (the customer x
campaign engagement graph, scipy.csgraph in the pylab sandbox - no networkx,
segments from printed metrics, the approval card before any bulk). Own
once-ever stamp, the v0.492 pattern; the seed never overwrites hers."""
from __future__ import annotations

import inspect
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


def test_seed_files_exclude_bd_and_bd_files_are_2():
    from app.coder import skill_packs
    assert len(skill_packs.seed_files()) == 11          # the starter lane is untouched
    assert len(skill_packs.byox_files()) == 31          # the BYOX pack is untouched
    assert len(skill_packs.prog_files()) == 2           # the PROG pack is untouched
    assert len(skill_packs.sp_files()) == 15            # the superpowers lane is untouched
    assert len(skill_packs.fe_files()) == 3             # the FE pack is untouched
    assert len(skill_packs.cs_files()) == 2             # the CS pack is untouched
    bd = skill_packs.bd_files()
    assert len(bd) == 2
    assert {f.stem for f in bd} == {"bd-eval-benchmarks", "bd-campaign-graph"}


def test_seed_bdpack_reaches_a_tenant_already_seeded(desk):
    from app.coder import skill_packs, skills_store, store
    T = "bd-t1"
    store.ensure()
    store.mark_consumed(skill_packs.SEED_STAMP.format(T))    # the old once-ever stamps
    store.mark_consumed(skill_packs.BYOX_STAMP.format(T))    # ALL SEVEN are set -
    store.mark_consumed(skill_packs.PROG_STAMP.format(T))    # the bd stamp is NOT
    store.mark_consumed(skill_packs.SP_STAMP.format(T))
    store.mark_consumed(skill_packs.FE_STAMP.format(T))
    store.mark_consumed(skill_packs.CS_STAMP.format(T))
    store.mark_consumed(skill_packs.MG_STAMP.format(T))
    r = skill_packs.seed_bdpack(T)
    assert r["bd_seeded"] == 2
    assert skill_packs.seed_bdpack(T)["bd_seeded"] == 0      # own stamp: never twice
    names = {s["name"] for s in skills_store.listing(T)}
    assert names == {"bd-eval-benchmarks", "bd-campaign-graph"}


def test_seed_bdpack_hers_win(desk):
    from app.coder import skill_packs, skills_store
    T = "bd-t2"
    skills_store.create(T, "bd-eval-benchmarks", "Her own eval notes", "her words")
    skill_packs.seed_bdpack(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "bd-eval-benchmarks")
    assert row["description"] == "Her own eval notes"


def test_seed_bdpack_switch_off(desk):
    monkeypatch = desk
    from app.coder import skill_packs
    from app.config import get_settings
    monkeypatch.setenv("BDPACK_ENABLED", "false")
    get_settings.cache_clear()
    assert skill_packs.seed_bdpack("bd-t3")["bd_seeded"] == 0
    get_settings.cache_clear()


def test_pack_seeders_finds_bdpack():
    from app.coder import service
    from app.coder import skill_packs
    assert "seed_all(tenant)" in inspect.getsource(service)                      # the desk calls seed_all ...
    assert "seed_bdpack" in [f.__name__ for f in skill_packs._pack_seeders()]    # ... which finds this pack by name


def test_bd_files_pass_the_lint_gate():
    from app.coder import skill_packs
    from app.coder.skills_store import DESC_MAX, BODY_MAX, parse_skill, validate
    for f in skill_packs.bd_files():
        name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
        assert name == f.stem
        assert len(desc) <= DESC_MAX, (f.name, len(desc))
        assert len(body) <= BODY_MAX, (f.name, len(body))
        validate(desc, body)                             # raises on an over-long row


def test_eval_benchmarks_pins_the_discipline():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.bd_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "bd-eval-benchmarks":
            body = b
    for token in ("SQuAD", "20 Newsgroups", "IMDb", "data.gov.in",
                  "golden set", "data_fetch", "delegate_task", "pylab",
                  "sheet_append", "THE LEDGER", "printed output", "NEVER",
                  "invented golden answers", "teaching to the test",
                  "private customer rows", "version"):
        assert token in body, token


def test_campaign_graph_pins_the_discipline():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.bd_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "bd-campaign-graph":
            body = b
    for token in ("Bipartite", "co-engagement", "scipy.csgraph",
                  "connected_components", "degree", "lookalike", "one-edge",
                  "get_campaign_status", "email_bulk_status", "sheet_append",
                  "approval card", "NEVER", "PII", "printed output",
                  "NO networkx"):
        assert token in body, token


def test_campaign_graph_is_sandbox_honest():
    """The skill teaches the pylab sandbox's REAL library set (scipy.csgraph, plain
    dicts) and says plainly that networkx is not there - never a tool the sandbox
    refuses (the never-invent law, applied to libraries)."""
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.bd_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "bd-campaign-graph":
            body = b
    assert "NO networkx" in body
    assert "scipy" in body
    assert "pylab" in body


def test_injection_matches_a_bd_ask(desk):
    from app.coder import inject, skill_packs
    T = "bd-t4"
    skill_packs.seed_bdpack(T)
    block = inject.skills_block(T, "quality regression ka eval suite dataset se banao golden")
    assert "bd-eval-benchmarks" in block
    block2 = inject.skills_block(T, "campaign graph se customer segments nikaalo analytics")
    assert "bd-campaign-graph" in block2
