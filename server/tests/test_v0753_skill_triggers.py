"""v0.753 SKILLS FIND + UIUX DATA: the awesome-pack skills carry plain trigger words (`when_to_use`) so everyday
asks reach them, long Anthropic descriptions need two of her words before they ride along, the skills card scores
the awesome packs, and the UI/UX Pro Max database (MIT, upstream 6ae86f6) is in the repo at last."""
from __future__ import annotations

from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"


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


def test_every_awesome_pack_file_has_short_trigger_words():
    from app.coder import skill_packs, skills_store
    files = [f for f in skill_packs.pack_files_all() if not f.stem.startswith(("uiux", "superpowers"))]
    have = {f.stem: skill_packs._when_of(f).get("when_to_use", "") for f in files}
    assert sum(1 for w in have.values() if w) >= 42
    for name, w in have.items():
        assert len(w) <= skills_store.WHEN_MAX, name


def test_create_keeps_when_and_search_sees_it(desk):
    from app.coder import skills_store
    skills_store.create("t1", "net-help", "fix a home network", "steps", extra={"when_to_use": "wifi slow, disconnect"})
    assert skills_store.get_when("t1", "net-help") == "wifi slow, disconnect"
    assert skills_store.get_when("t1", "nobody") is None
    with pytest.raises(skills_store.SkillError):
        skills_store.create("t1", "too-long", "d", "b", extra={"when_to_use": "x" * (skills_store.WHEN_MAX + 1)})


def test_add_when_never_overwrites_her_line(desk):
    from app.coder import skills_store
    skills_store.create("t1", "mine", "my own skill", "body text", extra={"when_to_use": "her words"})
    assert skills_store.add_when("t1", "mine", "our words") is False
    assert skills_store.get_when("t1", "mine") == "her words"
    skills_store.create("t1", "bare", "a skill", "body text")
    assert skills_store.add_when("t1", "bare", "our words") is True
    assert skills_store.get_when("t1", "bare") == "our words"
    raw = skills_store._path("t1", "bare")
    text = open(raw, encoding="utf-8").read()
    assert "a skill" in text and "body text" in text                 # desc + body kept


def test_seed_when_replaces_our_old_line_and_leaves_hers(desk):
    from app.coder import skill_packs, skills_store, store
    T = "w1"
    pairs = dict(skill_packs._when_pairs())
    a, b, c = sorted(pairs)[:3]
    for n in (a, b, c):
        skills_store.create(T, n, "a skill", "body")
    skills_store.add_when(T, a, "an old line we shipped")
    store.mark_consumed(f"skills:whenmine:{T}:{a}:{skill_packs._h('an old line we shipped')}")
    skills_store.add_when(T, b, "her own words")
    skill_packs.seed_when(T)
    assert skills_store.get_when(T, a) == pairs[a]                   # ours -> refreshed
    assert skills_store.get_when(T, b) == "her own words"            # hers -> left alone
    assert skills_store.get_when(T, c) == pairs[c]                   # none -> given
    assert skill_packs.seed_when(T) == {"when_added": 0}             # once per digest


def test_long_description_needs_two_of_her_words(desk):
    from app.coder import inject, skill_packs
    skill_packs.seed_all("u1")
    names = [m["name"] for m in inject._matched("u1", "which python library should I use to read excel")]
    assert "internal-comms" not in names and "theme-factory" not in names
    assert any(n.startswith("prog-library") for n in names)


def test_awesome_card_numbers(desk):
    from app.coder import skill_packs
    from app.quality import skillscard
    skill_packs.seed_all("cardT")
    r = skillscard.awesome_rows("cardT")
    assert r["tuned"] == 20 and r["tuned_ok"] == 20
    assert r["held"] == 20 and r["held_ok"] >= 19
    assert r["neg_clean"] == r["neg"] == 8


def test_uiux_database_is_in_the_repo():
    d = APP / "coder" / "uiux" / "data"
    assert (d / "styles.csv").exists() and (d / "ui-reasoning.csv").exists()
    assert len(list((d / "stacks").glob("*.csv"))) >= 20
    assert "6ae86f6" in (APP / "coder" / "uiux" / "PROVENANCE.md").read_text()
