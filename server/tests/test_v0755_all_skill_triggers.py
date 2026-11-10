"""v0.755 EVERY SKILL FINDABLE: after v0.753 gave the 42 awesome-pack skills plain trigger words, the other 57 shipped
skills (build-your-own-x, superpowers, the starter skills, UI/UX Pro Max) get theirs too - every shipped skill file now
carries a `when_to_use` line, and one plain ask per skill reaches it."""
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


def test_every_shipped_skill_has_trigger_words():
    from app.coder import skill_packs, skills_store
    files = sorted(set(skill_packs.seed_files()) | set(skill_packs.pack_files_all()))
    assert len(files) >= 99
    missing = [f.stem for f in files if not skill_packs._when_of(f)]
    assert missing == []
    for f in files:
        assert len(skill_packs._when_of(f)["when_to_use"]) <= skills_store.WHEN_MAX, f.stem


def test_one_plain_ask_reaches_each_other_skill(desk):
    from app.coder import skill_packs
    from app.quality import skillscard
    from app.quality.skills_asks import REST
    skill_packs.seed_all("restT")
    r = skillscard.rest_rows("restT")
    assert r["n"] == len(REST) == 57
    assert r["ok"] == 57, [x for x in r["rows"] if not x["ok"]]
    aw = skillscard.awesome_rows("restT")
    assert aw["neg_clean"] == aw["neg"] == 8                       # unrelated asks still pull nothing
    assert aw["tuned_ok"] == 20 and aw["held_ok"] >= 19
