"""CLAUDE SKILLS P2 - the first three Anthropic example skills (Apache 2.0) shipped as a seed pack:
internal-comms, theme-factory, frontend-design.

Pins: (1) the upstream text is UNCHANGED (hash of everything above the Hoola note, minus the one
added when_to_use line) and each skill keeps its LICENSE.txt; (2) the Hoola note + modification
notice are present; (3) seed_claude installs them once ever, as imported folder skills with their
resources, never over a skill she already has, and the switch turns it off; (4) the resources are
reachable through read_file; (5) a small retrieval card: real asks (English and Hinglish) must
find the right skill in the injected top 2 on a tenant that also holds the 10 starters and the 31
BYOX skills, and unrelated asks must NOT pull these three in.
"""
import hashlib
import re

import pytest

from app.coder import inject, skill_packs, skills_store, store

T = "default"

UPSTREAM_SHA = {      # sha256 of the upstream SKILL.md with trailing newlines stripped (anthropics/skills ca45fc49)
    "internal-comms": "6c5721a4357fd5a6aacef9cf1f8cc197425a0f0d5c9e341b3449448e6d307679",
    "theme-factory": "366ee55d92407128fd5f05871d9a6135bfe6fad2146ec2652edf99fc0b0d177b",
    "frontend-design": "c3d0d3ea592ad4f01215009a7ebcf7b7d948f568c15dd77e24ff7172c8643f2b",
}
MARK = "<!-- HOOLA NOTE:"


@pytest.fixture()
def desk(env, monkeypatch, tmp_path):
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_SKILLS", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    store.ensure()
    skills_store.reset_for_tests()
    yield monkeypatch
    skills_store.reset_for_tests()
    get_settings.cache_clear()


def _dirs():
    return {d.name: d for d in skill_packs.claude_dirs()}


# ---------------------------------------------------------------- (1)+(2) files

def test_pack_has_three_skills_with_licence():
    d = _dirs()
    assert set(d) == set(UPSTREAM_SHA)
    for name, p in d.items():
        lic = (p / "LICENSE.txt").read_text(encoding="utf-8")
        assert "Apache License" in lic and "Version 2.0" in lic, name


@pytest.mark.parametrize("name", sorted(UPSTREAM_SHA))
def test_upstream_text_unchanged_and_note_present(name):
    text = (_dirs()[name] / "SKILL.md").read_text(encoding="utf-8")
    assert MARK in text
    above = text.split("\n\n" + MARK)[0]
    lines = [l for l in above.split("\n") if not l.startswith("when_to_use:")]      # the one added line
    assert hashlib.sha256("\n".join(lines).rstrip("\n").encode()).hexdigest() == UPSTREAM_SHA[name]
    note = text.split(MARK, 1)[1]
    assert "Modified by Newtika for Hoola" in note
    assert "house rules" in note and "win over this skill" in note
    assert "when_to_use:" in above


def test_resources_shipped():
    d = _dirs()
    assert (d["internal-comms"] / "examples" / "3p-updates.md").is_file()
    assert (d["theme-factory"] / "themes" / "ocean-depths.md").is_file()
    assert (d["theme-factory"] / "theme-showcase.pdf").is_file()
    assert len(list((d["theme-factory"] / "themes").glob("*.md"))) == 10


# ---------------------------------------------------------------- (3)+(4) seeding

def test_seed_claude_once_ever_as_imported_folders(desk):
    res = skill_packs.seed_claude(T)
    assert res == {"claude_seeded": 3}
    assert skill_packs.seed_claude(T) == {"claude_seeded": 0}                       # exactly-once
    rows = {s["name"]: s for s in skills_store.listing(T)}
    assert set(rows) == set(UPSTREAM_SHA) and all(r.get("folder") for r in rows.values())
    raw = open(skills_store.raw_path(T, "theme-factory"), encoding="utf-8").read()
    assert "imported: true" in raw and "license:" in raw and "when_to_use:" in raw
    r = skills_store.read(T, "theme-factory")
    assert "LICENSE.txt" in r["files"] and "themes/ocean-depths.md" in r["files"]
    assert len(r["description"]) > 60                                                # Claude-length description kept


def test_read_file_reaches_examples_and_themes(desk):
    skill_packs.seed_claude(T)
    ex = skills_store.read_file(T, "internal-comms", "examples/3p-updates.md")
    assert "Progress" in ex["content"] and not ex["truncated"]
    th = skills_store.read_file(T, "theme-factory", "themes/ocean-depths.md")
    assert "#1a2332" in th["content"]
    with pytest.raises(skills_store.SkillError):
        skills_store.read_file(T, "theme-factory", "theme-showcase.pdf")             # binary: shipped, not readable


def test_never_over_her_skill_and_switch_off(desk):
    skills_store.create(T, "internal-comms", "My own", "my own words")
    res = skill_packs.seed_claude(T)
    assert res == {"claude_seeded": 2}
    assert skills_store.read(T, "internal-comms")["body"] == "my own words"
    desk.setenv("CLAUDE_SKILLS_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert skill_packs.seed_claude("another-tenant") == {"claude_seeded": 0}
    desk.setenv("CLAUDE_SKILLS_ENABLED", "true")
    get_settings.cache_clear()
    desk.setenv("CODER_SKILLS_SEED", "false")
    get_settings.cache_clear()
    assert skill_packs.seed_claude("third-tenant") == {"claude_seeded": 0}


def test_imported_pack_skill_not_shareable(desk):
    skill_packs.seed_claude(T)
    for _ in range(4):
        skills_store.read(T, "frontend-design")
    assert "error" in skill_packs.share_nominate(T, "frontend-design")


# ---------------------------------------------------------------- (5) retrieval card

ASKS = [
    # (ask, the skill that MUST be in the injected top 2)
    ("write this week's status report for my team", "internal-comms"),
    ("is hafte ka status update likho team ke liye", "internal-comms"),
    ("draft a company newsletter for our staff", "internal-comms"),
    ("incident report likhna hai kal ke outage ka", "internal-comms"),
    ("apply a theme to my slides and pick colours", "theme-factory"),
    ("mere deck ke liye theme lagao colours aur fonts ke saath", "theme-factory"),
    ("give me a new colour palette and font pairing for the report", "theme-factory"),
    ("design a landing page with distinctive typography", "frontend-design"),
    ("website ka design banao, typography aur layout sundar chahiye", "frontend-design"),
    ("build a dashboard UI that does not look templated", "frontend-design"),
]
NEGATIVE = [        # unrelated asks: none of the three pack skills may ride the injected top 2
    "mera GST invoice banao for Sharma traders",
    "WhatsApp campaign chalao diwali offer ka",
    "Flask app VPS par deploy karna hai",
    "build a regex engine from scratch",
]


def _full_tenant():
    skill_packs.seed(T)
    skill_packs.seed_byox(T)
    skill_packs.seed_claude(T)


def test_retrieval_card_right_skill_in_top2(desk):
    _full_tenant()
    assert len(skills_store.listing(T)) == 10 + 31 + 3
    miss = [(a, w, [r["name"] for r in inject._matched(T, a)]) for a, w in ASKS
            if w not in [r["name"] for r in inject._matched(T, a)]]
    assert not miss, f"right skill missing from top 2: {miss}"


def test_retrieval_card_unrelated_asks_do_not_pull_pack_in(desk):
    _full_tenant()
    pack = set(UPSTREAM_SHA)
    pulled = [(a, [r["name"] for r in inject._matched(T, a)]) for a in NEGATIVE
              if pack & {r["name"] for r in inject._matched(T, a)}]
    assert not pulled, f"pack skill pulled in by an unrelated ask: {pulled}"


def test_injected_block_stays_inside_budget(desk):
    _full_tenant()
    for a, _ in ASKS:
        blk = inject.skills_block(T, a, compact=True)
        assert len(blk) <= inject.SKILLS_COMPACT_BUDGET
        assert re.search(r"^- [a-z0-9-]+: ", blk, re.M)
