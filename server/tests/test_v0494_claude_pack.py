"""CLAUDE SKILLS P2+P3 - Anthropic example skills (Apache 2.0) shipped as a seed pack: internal-comms,
theme-factory, frontend-design (P2), canvas-design, webapp-testing (P3), plus one Hoola original,
coauthor-docs (the upstream doc-coauthoring has no licence, so it is NOT copied).

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
    "canvas-design": "a1f288079624402f30682753c1d43920b6664785698d21d3e7aa197450a6448b",
    "webapp-testing": "51b7349e77ec63b7744a6f63647e7566a0b4d2e301121cc10e8c2113af6556a2",
    "mcp-builder": "3b2ace9cadc148da1ed15d6458f81a1dea38c4df6fa4aee25a4f77ddc243dd08",
}
HOOLA_ORIGINAL = {"coauthor-docs", "skill-maker"}          # written by Newtika, no upstream text, no LICENSE.txt needed
ALL = set(UPSTREAM_SHA) | HOOLA_ORIGINAL
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

def test_pack_contents_and_licences():
    d = _dirs()
    assert set(d) == ALL
    for name in UPSTREAM_SHA:
        lic = (d[name] / "LICENSE.txt").read_text(encoding="utf-8")
        assert "Apache License" in lic and "Version 2.0" in lic, name
    for orig in HOOLA_ORIGINAL:
        assert not (d[orig] / "LICENSE.txt").exists()
        txt = (d[orig] / "SKILL.md").read_text(encoding="utf-8")
        assert "Hoola original" in txt and "contains no text from any third-party skill" in txt, orig


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
    assert (d["webapp-testing"] / "scripts" / "with_server.py").is_file()
    assert (d["mcp-builder"] / "reference" / "python_mcp_server.md").is_file()
    assert (d["mcp-builder"] / "scripts" / "evaluation.py").is_file()
    assert not (d["canvas-design"] / "canvas-fonts").exists()            # 5.5 MB of binary Latin fonts: not shipped
    assert (d["theme-factory"] / "theme-showcase.pdf").is_file()
    assert len(list((d["theme-factory"] / "themes").glob("*.md"))) == 10


# ---------------------------------------------------------------- (3)+(4) seeding

def test_seed_claude_once_ever_as_imported_folders(desk):
    res = skill_packs.seed_claude(T)
    assert res == {"claude_seeded": len(ALL)}
    assert skill_packs.seed_claude(T) == {"claude_seeded": 0}                       # exactly-once
    rows = {s["name"]: s for s in skills_store.listing(T)}
    assert set(rows) == ALL
    assert all(r.get("folder") for n, r in rows.items() if n not in HOOLA_ORIGINAL)  # originals = one file
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
    assert res == {"claude_seeded": len(ALL) - 1}
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
    ("create a poster as a pdf with a design philosophy", "canvas-design"),
    ("ek poster banao diwali ke liye, art jaisa design", "canvas-design"),
    ("test my web app with playwright and take a screenshot", "webapp-testing"),
    ("meri website ke button aur form test karo, console errors dekho", "webapp-testing"),
    ("help me write a proposal document step by step", "coauthor-docs"),
    ("ek spec document likhna hai saath mein, outline se shuru karein", "coauthor-docs"),
    ("build an MCP server in python for my crm api", "mcp-builder"),
    ("mere service ke liye MCP server banana hai, FastMCP se tools likhne hain", "mcp-builder"),
    ("i repeat this task every month, make it a reusable skill", "skill-maker"),
    ("ye kaam baar baar karti hoon, iska skill banao aur sudharo", "skill-maker"),
]
NEGATIVE = [        # unrelated asks: none of the three pack skills may ride the injected top 2
    "mera GST invoice banao for Sharma traders",
    "WhatsApp campaign chalao diwali offer ka",
    "Flask app VPS par deploy karna hai",
    "build a regex engine from scratch",
]


def _full_tenant():
    for fn in skill_packs._pack_seeders():          # every pack a real user gets (found by name)
        fn(T)


def test_retrieval_card_right_skill_in_top2(desk):
    _full_tenant()
    assert len(skills_store.listing(T)) == len(skill_packs.seed_files()) + len(skill_packs.byox_files()) + len(skill_packs.prog_files()) + len(skill_packs.sp_files()) + len(skill_packs.fe_files()) + len(skill_packs.cs_files()) + len(ALL)
    miss = [(a, w, [r["name"] for r in inject._matched(T, a)]) for a, w in ASKS
            if w not in [r["name"] for r in inject._matched(T, a)]]
    assert not miss, f"right skill missing from top 2: {miss}"


def test_retrieval_card_unrelated_asks_do_not_pull_pack_in(desk):
    _full_tenant()
    pack = ALL
    pulled = [(a, [r["name"] for r in inject._matched(T, a)]) for a in NEGATIVE
              if pack & {r["name"] for r in inject._matched(T, a)}]
    assert not pulled, f"pack skill pulled in by an unrelated ask: {pulled}"


def test_injected_block_stays_inside_budget(desk):
    _full_tenant()
    for a, _ in ASKS:
        blk = inject.skills_block(T, a, compact=True)
        assert len(blk) <= inject.SKILLS_COMPACT_BUDGET
        assert re.search(r"^- [a-z0-9-]+: ", blk, re.M)


# ---------------------------------------------------------------- P4: mcp-builder + skill-maker

def test_mcp_builder_reference_files_readable_and_note_honest(desk):
    skill_packs.seed_claude(T)
    r = skills_store.read(T, "mcp-builder")
    assert "reference/mcp_best_practices.md" in r["files"] and "scripts/evaluation.py" in r["files"]
    bp = skills_store.read_file(T, "mcp-builder", "reference/mcp_best_practices.md")
    assert len(bp["content"]) > 1000
    big = skills_store.read_file(T, "mcp-builder", "reference/node_mcp_server_v2.md")
    assert big["content"]                                                       # the longest guide still opens
    assert "code likha hai, abhi chalaya nahi" in r["body"]                    # never claims a test it did not run
    assert "bazar_find" in r["body"] and "scrape_page" in r["body"]


def test_skill_maker_respects_the_store_limits(desk):
    skill_packs.seed_claude(T)
    r = skills_store.read(T, "skill-maker")
    for needle in ("60 characters", "4,000 characters", "Save only after her yes", "Dry-run"):
        assert needle in r["body"], needle
    assert "not proof that the skill works" in r["body"]                      # no fake test claim


def test_skill_maker_advice_is_enforced_by_the_real_store(desk):
    """The limits the skill teaches are the limits skill_manage really enforces."""
    ok = skills_store.apply(T, [{"action": "create", "name": "monthly-gst-prep",
                                 "description": "Prepare the monthly GST filing pack",
                                 "body": "Use when: gst filing, GST ka hisaab\n1. collect invoices"}])
    assert ok.get("ok"), ok
    bad = skills_store.apply(T, [{"action": "create", "name": "x-y", "description": "d" * 61, "body": "b"}])
    assert "error" in bad and "60" in bad["error"]
