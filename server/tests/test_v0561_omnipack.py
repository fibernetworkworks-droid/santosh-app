"""v0.561.0 OMNI PACK: the 18-category awesome-lists atlas read as eighteen pack
families / 27 fed skills (owner: 'Gaming (28) ... Dev Environment (21) ... NOW DO
THIS ALL IN ONE GO - DEPLOY A 18 SPECIAL AGENT FOR EVERY TASK IN PARALLEL').
ga- game-dev + Steam/Deck recipes + the samudaay community home; de- the naya-PC
bundle; en- the daily brief; db- GUI ops over the ax tree + the SQLite->Postgres
path; me- the stock library + typography + ffmpeg recipes (the content goldmine);
le- the mentor; se- the injection suite + hardening; cm- the publish lane;
ha- the Pi agent; bu- the post list + billing ledger; wo- chatops + task triage;
ne- the diagnostics ladder; dc- the privacy stance; hs- wellbeing; ev- the event
radar; te- the web-E2E plan; mi- selfhost + personas/research; re- Hoola's own
awesome-search. Own once-ever stamps, the v0.492 pattern; the seeds never
overwrite hers; the desk-total pins ride all_seed_files() from this version on."""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

FAMILIES = [
    # (prefix, seeder, files_fn, result_key, expected count)
    ("ga", "seed_gapack", "ga_files", "ga_seeded", 3),
    ("de", "seed_devpack", "de_files", "de_seeded", 1),
    ("en", "seed_enpack", "en_files", "en_seeded", 1),
    ("db", "seed_dbpack", "db_files", "db_seeded", 2),
    ("me", "seed_mepack", "me_files", "me_seeded", 3),
    ("le", "seed_lepack", "le_files", "le_seeded", 1),
    ("se", "seed_secpack", "se_files", "se_seeded", 2),
    ("cm", "seed_cmpack", "cm_files", "cm_seeded", 1),
    ("ha", "seed_hapack", "ha_files", "ha_seeded", 1),
    ("bu", "seed_bupack", "bu_files", "bu_seeded", 2),
    ("wo", "seed_wopack", "wo_files", "wo_seeded", 2),
    ("ne", "seed_nepack", "ne_files", "ne_seeded", 1),
    ("dc", "seed_dcpack", "dc_files", "dc_seeded", 1),
    ("hs", "seed_hspack", "hs_files", "hs_seeded", 1),
    ("ev", "seed_evpack", "ev_files", "ev_seeded", 1),
    ("te", "seed_tepack", "te_files", "te_seeded", 1),
    ("mi", "seed_mipack", "mi_files", "mi_seeded", 2),
    ("re", "seed_repack", "re_files", "re_seeded", 1),
]

EXPECTED_STEMS = {
    "ga": {"ga-game-dev", "ga-launcher-recipes", "ga-community"},
    "de": {"de-naya-pc"},
    "en": {"en-daily-brief"},
    "db": {"db-gui-ops", "db-scale-path"},
    "me": {"me-stock-library", "me-typography", "me-ffmpeg-recipes"},
    "le": {"le-mentor"},
    "se": {"se-injection-suite", "se-hardening"},
    "cm": {"cm-publish-lane"},
    "ha": {"ha-pi-agent"},
    "bu": {"bu-post-list", "bu-billing-ledger"},
    "wo": {"wo-chatops", "wo-task-triage"},
    "ne": {"ne-diagnostics"},
    "dc": {"dc-privacy-tor"},
    "hs": {"hs-wellbeing"},
    "ev": {"ev-calendar"},
    "te": {"te-web-e2e"},
    "mi": {"mi-selfhost", "mi-bots-research"},
    "re": {"re-awesome-search"},
}


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


def test_omni_files_and_counts_pin():
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
    assert len(skill_packs.ed_files()) == 2             # the Editors pack is untouched
    for pref, _s, files_fn, _k, n in FAMILIES:
        files = getattr(skill_packs, files_fn)()
        assert len(files) == n, (pref, len(files))
        assert {f.stem for f in files} == EXPECTED_STEMS[pref], pref
    assert len(skill_packs.pack_files_all()) == 88      # 61 earlier pack lanes + 27 omni
    assert len(skill_packs.all_seed_files()) == 99      # 11 starters + 88 lanes


def test_all_eighteen_seeds_past_the_thirteen_stamps(desk):
    from app.coder import skill_packs, skills_store, store
    T = "omni-t1"
    store.ensure()
    store.mark_consumed(skill_packs.SEED_STAMP.format(T))    # ALL THIRTEEN earlier
    store.mark_consumed(skill_packs.BYOX_STAMP.format(T))    # stamps are set - the
    store.mark_consumed(skill_packs.PROG_STAMP.format(T))    # eighteen omni stamps
    store.mark_consumed(skill_packs.SP_STAMP.format(T))      # are NOT
    store.mark_consumed(skill_packs.FE_STAMP.format(T))
    store.mark_consumed(skill_packs.CS_STAMP.format(T))
    store.mark_consumed(skill_packs.MG_STAMP.format(T))
    store.mark_consumed(skill_packs.BD_STAMP.format(T))
    store.mark_consumed(skill_packs.CR_STAMP.format(T))
    store.mark_consumed(skill_packs.TH_STAMP.format(T))
    store.mark_consumed(skill_packs.ED_STAMP.format(T))
    store.mark_consumed(skill_packs.CLAUDE_STAMP.format(T))
    total = 0
    for pref, seeder, files_fn, key, n in FAMILIES:
        r = getattr(skill_packs, seeder)(T)
        assert r[key] == n, (pref, r)
        total += r[key]
    assert total == 27
    names = {s["name"] for s in skills_store.listing(T)}
    assert names == set().union(*EXPECTED_STEMS.values())
    for pref, seeder, _f, key, _n in FAMILIES:               # own stamp: never twice
        assert getattr(skill_packs, seeder)(T)[key] == 0, pref


def test_seed_all_fills_the_desk_once(desk):
    from app.coder import skill_packs, skills_store, store
    T = "omni-t2"
    store.ensure()
    r1 = skill_packs.seed_all(T)
    assert sum(r1.values()) == len(skill_packs.all_seed_files()) + len(skill_packs.claude_dirs())
    assert {s["name"] for s in skills_store.listing(T)} >= set().union(*EXPECTED_STEMS.values())
    r2 = skill_packs.seed_all(T)                              # every stamp consumed
    assert sum(r2.values()) == 0


def test_hers_win_on_a_new_pack(desk):
    from app.coder import skill_packs, skills_store
    T = "omni-t3"
    skills_store.create(T, "ga-game-dev", "Her own game notes", "her words")
    skill_packs.seed_gapack(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "ga-game-dev")
    assert row["description"] == "Her own game notes"


@pytest.mark.parametrize("env_name,seeder,key", [
    ("GAPACK_ENABLED", "seed_gapack", "ga_seeded"),
    ("DEVPACK_ENABLED", "seed_devpack", "de_seeded"),
    ("ENPACK_ENABLED", "seed_enpack", "en_seeded"),
    ("DBPACK_ENABLED", "seed_dbpack", "db_seeded"),
    ("MEPACK_ENABLED", "seed_mepack", "me_seeded"),
    ("LEPACK_ENABLED", "seed_lepack", "le_seeded"),
    ("SECPACK_ENABLED", "seed_secpack", "se_seeded"),
    ("CMPACK_ENABLED", "seed_cmpack", "cm_seeded"),
    ("HAPACK_ENABLED", "seed_hapack", "ha_seeded"),
    ("BUPACK_ENABLED", "seed_bupack", "bu_seeded"),
    ("WOPACK_ENABLED", "seed_wopack", "wo_seeded"),
    ("NEPACK_ENABLED", "seed_nepack", "ne_seeded"),
    ("DCPACK_ENABLED", "seed_dcpack", "dc_seeded"),
    ("HSPACK_ENABLED", "seed_hspack", "hs_seeded"),
    ("EVPACK_ENABLED", "seed_evpack", "ev_seeded"),
    ("TEPACK_ENABLED", "seed_tepack", "te_seeded"),
    ("MIPACK_ENABLED", "seed_mipack", "mi_seeded"),
    ("REPACK_ENABLED", "seed_repack", "re_seeded"),
])
def test_flag_off(desk, env_name, seeder, key):
    monkeypatch = desk
    from app.coder import skill_packs
    from app.config import get_settings
    monkeypatch.setenv(env_name, "false")
    get_settings.cache_clear()
    assert getattr(skill_packs, seeder)(f"omni-off-{env_name}")[key] == 0
    get_settings.cache_clear()


def test_pack_seeders_finds_all_eighteen():
    from app.coder import service
    from app.coder import skill_packs
    assert "seed_all(tenant)" in inspect.getsource(service)          # the desk calls seed_all ...
    names = [f.__name__ for f in skill_packs._pack_seeders()]
    for _p, seeder, _f, _k, _n in FAMILIES:
        assert seeder in names, seeder                               # ... which finds each by name


def test_omni_files_pass_the_lint_gate():
    from app.coder import skill_packs
    from app.coder.skills_store import DESC_MAX, BODY_MAX, parse_skill, validate
    for _p, _s, files_fn, _k, _n in FAMILIES:
        for f in getattr(skill_packs, files_fn)():
            name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
            assert name == f.stem
            assert len(desc) <= DESC_MAX, (f.name, len(desc))
            assert len(body) <= BODY_MAX, (f.name, len(body))
            validate(desc, body)                                     # raises on an over-long row


DISCIPLINE = {
    "ga-game-dev": ["game_desk", "game_studio", "game_qa", "awesome-godot", "awesome-flame", "printed"],
    "ga-launcher-recipes": ["ax_find", "ask_approval", "open_app", "pc_do", "remember"],
    "ga-community": ["samudaay", "hoola_group_create", "consent"],
    "de-naya-pc": ["ask_approval", "BLOCKED_APPS", "awesome-cli-apps", "remember", "api_call"],
    "en-daily-brief": ["create_routine", "podcast", "notebook", "awesome-podcasts"],
    "db-gui-ops": ["ax_find", "ask_approval", "awesome-db-tools"],
    "db-scale-path": ["dbmove", "postgres", "ask_approval", "row count"],
    "me-stock-library": ["photo_banao", "hoola_frames", "license", "awesome-stock-resources"],
    "me-typography": ["app/fonts", "awesome-fonts", "license"],
    "me-ffmpeg-recipes": ["video_edit", "crf", "Awesome-ffmpeg"],
    "le-mentor": ["create_routine", "notebook_ask", "awesome-roadmaps", "guru"],
    "se-injection-suite": ["prayog", "jaanch", "ask_approval", "injection"],
    "se-hardening": ["BLOCKED_APPS", "BLOCKED_KEYS", "cyber", "awesome-appsec"],
    "cm-publish-lane": ["ask_approval", "consent_jaanch", "api_call", "ax_find", "app/site/cms.py"],
    "ha-pi-agent": ["home_link", "ac_control", "ask_approval", "awesome-raspberry-pi"],
    "bu-post-list": ["create_campaign", "consent_jaanch", "ask_approval"],
    "bu-billing-ledger": ["ai_kharcha", "tally_entry", "ask_approval"],
    "wo-chatops": ["hoola_send", "ask_approval", "awesome-slack"],
    "wo-task-triage": ["email_triage", "kaam_plan", "morning-briefing"],
    "ne-diagnostics": ["pc_status", "session_log", "prayog", "PCAP"],
    "dc-privacy-tor": ["app/pii.py", "dpo", "consent_jaanch", "Tor"],
    "hs-wellbeing": ["app/breath.py", "create_routine"],
    "ev-calendar": ["calendar_add_event", "calendar_free_slots", "crawl_start"],
    "te-web-e2e": ["Playwright", "k6", "hoola_frames", "pylab", "ask_approval"],
    "mi-selfhost": ["bazar_find", "free-for-dev", "awesome-selfhosted"],
    "mi-bots-research": ["research_run", "youtube_analytics", "pylab", "hoola_make"],
    "re-awesome-search": ["crawl_start", "zoo", "publicapis", "skill_manage", "fetched"],
}

# the lanes that touch PC / money / publish / installs must gate on approval
# (hs-wellbeing is the deliberate exception: it suggests, it never acts;
#  re-awesome-search only ingests public lists and serves top-3 - no gate)
NEED_APPROVAL = [s for s in DISCIPLINE if s not in ("hs-wellbeing", "re-awesome-search")]


def _omni_bodies():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    files = []
    for _p, _s, files_fn, _k, _n in FAMILIES:
        files.extend(getattr(skill_packs, files_fn)())
    bodies = {}
    for f in files:
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        bodies[name] = b
    return bodies


def test_every_omni_skill_pins_the_discipline():
    bodies = _omni_bodies()
    assert len(bodies) == 27
    for stem, toks in DISCIPLINE.items():
        for tok in toks:
            assert tok in bodies[stem], (stem, tok)
        assert "NEVER" in bodies[stem], stem
    for stem in NEED_APPROVAL:
        assert "ask_approval" in bodies[stem], stem


def test_omni_skills_match_the_real_doors():
    """The never-invent law: every Hoola door a skill names must be REAL - in the
    tool registry, the operator, or on disk as the named module."""
    import os
    os.environ.setdefault("CODER_ENABLED", "true")
    from app.coder.skills_store import parse_skill
    from app.agent import tools
    real_tools = {t.get("name") for t in tools.TOOLS if isinstance(t, dict)}
    assert len(tools.TOOLS) == 624, "623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family)"        # refresh the same commit when it moves (582 their v0.588 + 2 sandarbh v0.589) (580 after the dev chain + 1 speckit v0.569)
    bodies = _omni_bodies()
    pairs = [
        ("game_desk", "ga-game-dev"), ("samudaay", "ga-community"),
        ("pc_status", "ne-diagnostics"), ("postgres", "db-scale-path"),
        ("photo_banao", "me-stock-library"), ("video_edit", "me-ffmpeg-recipes"),
        ("guru", "le-mentor"), ("cyber", "se-hardening"),
        ("consent_jaanch", "cm-publish-lane"), ("home_link", "ha-pi-agent"),
        ("tally_entry", "bu-billing-ledger"), ("ai_kharcha", "bu-billing-ledger"),
        ("hoola_send", "wo-chatops"), ("email_triage", "wo-task-triage"),
        ("podcast", "en-daily-brief"), ("calendar_add_event", "ev-calendar"),
        ("crawl_start", "re-awesome-search"), ("bazar_find", "mi-selfhost"),
        ("research_run", "mi-bots-research"), ("dpo", "dc-privacy-tor"),
        ("prayog", "se-injection-suite"), ("hoola_frames", "te-web-e2e"),
        ("remember", "de-naya-pc"), ("create_campaign", "bu-post-list"),
    ]
    for door, stem in pairs:
        assert door in real_tools, door                       # the registry really has it
        assert door in bodies[stem], (stem, door)             # the skill really teaches it
    op = (REPO_ROOT / "server" / "app" / "pc" / "operator.py").read_text(encoding="utf-8")
    for door in ("ax_find", "ask_approval", "BLOCKED_APPS", "BLOCKED_KEYS", "open_app"):
        assert door in op, door
    for stem, door in (("ga-launcher-recipes", "ax_find"), ("db-gui-ops", "ax_find"),
                       ("cm-publish-lane", "ax_find"), ("se-hardening", "BLOCKED_APPS"),
                       ("de-naya-pc", "BLOCKED_APPS")):
        assert door in bodies[stem], (stem, door)
    modules = [
        ("app/dbmove.py", "db-scale-path", "dbmove"),
        ("app/pii.py", "dc-privacy-tor", "app/pii.py"),
        ("app/fonts", "me-typography", "app/fonts"),
        ("app/breath.py", "hs-wellbeing", "app/breath.py"),
        ("app/site/cms.py", "cm-publish-lane", "app/site/cms.py"),
        ("app/datasets.py", "re-awesome-search", "publicapis"),
    ]
    for rel, stem, tok in modules:
        assert (REPO_ROOT / "server" / rel).exists(), rel
        assert tok in bodies[stem], (stem, tok)


def test_injection_matches_omni_asks(desk):
    from app.coder import inject, skill_packs
    T = "omni-t4"
    for _p, seeder, _f, _k, _n in FAMILIES:
        getattr(skill_packs, seeder)(T)
    block = inject.skills_block(T, "steam game launch karna hai pc se flags ke saath")
    assert "ga-launcher-recipes" in block
    block = inject.skills_block(T, "naya pc setup karo cli apps bundle install")
    assert "de-naya-pc" in block
    block = inject.skills_block(T, "free stock photos videos chahiye license ke saath")
    assert "me-stock-library" in block
    block = inject.skills_block(T, "wordpress site par campaign publish karo")
    assert "cm-publish-lane" in block
    block = inject.skills_block(T, "roz subah podcast newsletter ka brief chahiye")
    assert "en-daily-brief" in block
