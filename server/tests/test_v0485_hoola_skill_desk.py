"""v0.485.0 HOOLA SKILL DESK - the skills platform (owner: "NOW LETS WORK ON SKILLS FOR HOOLA"
+ "MAKE IT VERY POWERFULL BIGGER THEN HOW CLAUDE HANDDLE SKILLS").

What this suite pins, piece by piece:
(1) TELEMETRY: every matched injection marks skill_uses(shown, surface chat/voice); every
    skills_store.read marks kind='read' (the follow signal); the desk's counts read ONE GROUP BY;
    the recency boost - a skill telemetry saw in 30 days outranks an equally-ranked cold one.
(2) PARK: skills_store.set_enabled is the ONE enabled writer (the model has no such op); the
    frontmatter `enabled: false` flag lives in the file; a parked skill vanishes from search and
    injection but stays listed; a content update never flips the owner's flag; the legacy vault
    lift (a real v2-schema DB gets the column ALTERed in place).
(3) SEED: the 42 class-level starters under coder/skillpack/ copy once ever per tenant
    (create-if-missing - hers win), the consumed stamp makes it exactly-once, coder_skills_seed
    gates it, every shipped file passes the store's own lint.
(4) IMPORT/EXPORT: raw SKILL.md markdown (the Claude Code / ClawHub shape) and JSON rows both
    import through the SAME lint funnel; create-if-missing, NEVER overwrites; <=25 per call;
    a lint refusal never half-applies; export reads raw files (no follow telemetry) and the
    round-trip is a no-op.
(5) SHARE: the curator nominates from the telemetry (>= coder_skills_share_min_reads real
    reads; parked never; dup never; pending cap; no reads = refusal); the owner's tap decides -
    publish re-redacts the body and writes to the RESERVED tenant _packs with NO trace of the
    source tenant; reject closes it; a decided row never re-publishes; coder_skills_share
    switches the lane off.
(6) REACH: inject.child_skills gives a swarm worker the matched lines in 400 chars and
    delegate.run_child puts them in the child's OWN system prompt; DevSahayak's loop reads the
    top-2 matched skills WHOLE into the first message of the edit loop and the plan pass
    (1600 budget) - zero model cost, fail-open, gated.
(7) ROUTES: the desk's ten routes mounted and live against a real FastAPI app; kill switches
    (coder_skills, coder_enabled) refuse honestly; the package-export law (skill_packs on the
    app.coder import list); the version layer (APP_VERSION, pubspec, schema_version 3).
"""
import asyncio
import inspect
import json
import os
import sqlite3

import pytest

from app import coder
from app.coder import inject, skill_packs, skills_store, store
from app.coder.skills_store import SkillError

T = "default"
T2 = "second-tenant"


@pytest.fixture()
def desk(env, monkeypatch, tmp_path):
    """Fresh vault in a TEMP dir (skill .md files must never land in the repo), skills ON."""
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


def _mk(name="deploy-flask-app", desc="How to deploy a Flask app to the VPS", body=None, tenant=T):
    skills_store.create(tenant, name, desc, body or "1. scp the repo. 2. write the unit. 3. restart hoola.")


# ---------------------------------------------------------------- (1) telemetry

def test_shown_marks_on_injection(desk):
    _mk()
    blk = inject.skills_block(T, "deploy the flask app", surface="chat", conv="c1")
    assert "deploy-flask-app" in blk
    counts = store.skill_use_counts(T)
    assert counts["deploy-flask-app"]["shown"] == 1
    assert counts["deploy-flask-app"]["read"] == 0


def test_shown_marks_voice_surface(desk):
    _mk()
    inject.skills_block(T, "deploy the flask app", compact=False, surface="voice")
    assert store.skill_use_counts(T)["deploy-flask-app"]["shown"] == 1


def test_read_marks_follow(desk):
    _mk()
    inject.skills_block(T, "deploy")                       # shown
    skills_store.read(T, "deploy-flask-app")               # the follow
    skills_store.read(T, "deploy-flask-app")
    c = store.skill_use_counts(T)["deploy-flask-app"]
    assert c["shown"] == 1 and c["read"] == 2
    assert c["last_read"] and store.skill_reads(T, "deploy-flask-app") == 2


def test_stats_carry_the_telemetry(desk):
    _mk()
    inject.skills_block(T, "deploy")
    skills_store.read(T, "deploy-flask-app")
    st = store.stats()
    assert st["skills"] == 1 and st["skills_live"] == 1
    assert st["skill_uses"] == 2 and st["skill_reads"] == 1
    assert st["skill_shares_pending"] == 0


def test_recency_boost_hot_first(desk):
    _mk("alpha-deploy", "Alpha deploy how to", "deploy to the VPS with systemd, then deploy again")
    _mk("beta-deploy", "Beta ship how to", "ship to the VPS with docker")
    assert [r["name"] for r in inject._matched(T, "deploy")] == ["alpha-deploy", "beta-deploy"]
    skills_store.read(T, "beta-deploy")                    # beta becomes hot
    assert [r["name"] for r in inject._matched(T, "deploy")] == ["beta-deploy", "alpha-deploy"]


# ---------------------------------------------------------------- (2) park

def test_park_hides_from_search_and_injection_but_stays_listed(desk):
    _mk()
    skills_store.set_enabled(T, "deploy-flask-app", False)
    assert store.skills_search(T, "deploy") == []
    assert inject.skills_block(T, "deploy the flask app") == ""
    lst = skills_store.listing(T)
    assert len(lst) == 1 and lst[0]["enabled"] is False


def test_park_flag_lives_in_the_file(desk):
    _mk()
    skills_store.set_enabled(T, "deploy-flask-app", False)
    raw = open(skills_store._path(T, "deploy-flask-app"), encoding="utf-8").read()
    assert "enabled: false" in raw
    assert skills_store.is_parked(T, "deploy-flask-app") is True
    skills_store.set_enabled(T, "deploy-flask-app", True)
    assert "enabled: false" not in open(skills_store._path(T, "deploy-flask-app"),
                                        encoding="utf-8").read()


def test_unpark_returns_the_skill(desk):
    _mk()
    skills_store.set_enabled(T, "deploy-flask-app", False)
    skills_store.set_enabled(T, "deploy-flask-app", True)
    assert store.skills_search(T, "deploy")
    r = skills_store.set_enabled(T, "deploy-flask-app", True)
    assert r["changed"] is False                            # idempotent, no rewrite


def test_update_preserves_the_owner_flag(desk):
    _mk()
    skills_store.set_enabled(T, "deploy-flask-app", False)
    skills_store.read(T, "deploy-flask-app")                # read-before-write
    skills_store.update(T, "deploy-flask-app", body="1. git pull. 2. restart.")
    assert skills_store.is_parked(T, "deploy-flask-app") is True


def test_model_has_no_park_operation(desk):
    """The apply funnel (the model's only door) knows five actions - never an enable/park."""
    res = skills_store.apply(T, [{"action": "enable", "name": "x"}])
    assert "error" in res and "unknown action" in res["error"]


def test_legacy_vault_lift_adds_enabled(env, monkeypatch, tmp_path):
    """A real v2-schema vault (pre-0.481) gets skills.enabled ALTERed in place - never rebuilt."""
    d = tmp_path / "legacy"
    d.mkdir()
    monkeypatch.setenv("CODER_DIR", str(d))
    from app.config import get_settings
    get_settings.cache_clear()
    conn = sqlite3.connect(str(d / "coder.db"))
    conn.executescript("""
        CREATE TABLE schema_version (v INTEGER NOT NULL);
        INSERT INTO schema_version VALUES (2);
        CREATE TABLE skills (name TEXT NOT NULL, tenant TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (name, tenant));
        CREATE TABLE observations (id INTEGER PRIMARY KEY, conv TEXT, tenant TEXT DEFAULT '',
            type TEXT, title TEXT, subtitle TEXT DEFAULT '', facts TEXT DEFAULT '[]',
            narrative TEXT DEFAULT '', concepts TEXT DEFAULT '[]', files_read TEXT DEFAULT '[]',
            files_modified TEXT DEFAULT '[]', turn_id TEXT DEFAULT '', actor TEXT DEFAULT '',
            discovery_tokens INTEGER DEFAULT 0, content_hash TEXT, title_norm_key TEXT DEFAULT '',
            occurrence_count INTEGER DEFAULT 1, reinforcement_dates TEXT DEFAULT '[]',
            last_reinforced TEXT DEFAULT '', created_at TEXT, created_epoch INTEGER,
            superseded_by INTEGER NOT NULL DEFAULT 0);
    """)
    conn.execute("INSERT INTO skills(name, tenant, description, body, created_at, updated_at) "
                 "VALUES ('old-skill', 'default', 'desc', 'body', 'x', 'y')")
    conn.commit()
    conn.close()
    try:
        store._fts_ok = None
        store.ensure()
        with store.db() as c:
            cols = [r[1] for r in c.execute("PRAGMA table_info(skills)").fetchall()]
            assert "enabled" in cols
            row = c.execute("SELECT name, enabled FROM skills").fetchone()
            assert row["name"] == "old-skill" and row["enabled"] == 1
            assert c.execute("SELECT v FROM schema_version").fetchone()[0] == 3
        _mk("new-skill", "A post lift skill", "body")   # the mirror writes on the lifted table
    finally:
        store._fts_ok = None
        get_settings.cache_clear()


# ---------------------------------------------------------------- (3) seed

def test_seed_lands_once(desk):
    r = skill_packs.seed(T)
    assert r["seeded"] == 11   # the starters lane (v0.492 model; byox rides seed_byox: 31 more, superpowers rides seed_sp: 15 more (v0.495), each under its own stamp, the route total stays 57)
    names = {s["name"] for s in skills_store.listing(T)}
    assert {"deploy-flask-app", "whatsapp-campaign", "gst-invoice", "meeting-minutes",
            "morning-briefing", "excel-data-clean", "upi-payment-chase", "seo-page-audit",
            "hindi-reply-tone", "pdf-fill-form", "uiux-pro-max"} <= names
    assert skill_packs.seed(T)["seeded"] == 0              # the stamp: never twice
    assert store.is_consumed(skill_packs.SEED_STAMP.format(T))


def test_seed_respects_hers(desk):
    skills_store.create(T, "deploy-flask-app", "Her own deploy runbook", "her words win")
    r = skill_packs.seed(T)
    assert r["seeded"] == 10                               # the other ten land (starters lane only)
    assert skills_store.read(T, "deploy-flask-app")["body"] == "her words win"
    assert skill_packs.seed(T)["seeded"] == 0              # the stamp: never twice


def test_seed_switch_off(desk, monkeypatch):
    monkeypatch.setenv("CODER_SKILLS_SEED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert skill_packs.seed(T)["seeded"] == 0
    assert skills_store.listing(T) == []
    get_settings.cache_clear()


def test_seed_files_pass_the_lint():
    """The shipped starters must clear the store's own hard lint (class-level, budgeted)."""
    files = skill_packs.seed_files()
    assert len(files) == 11   # seed_files = the non-byox starters (v0.492 model)
    for f in files:
        name, desc, body = skills_store.parse_skill(f.read_text(encoding="utf-8"))
        assert name == f.stem and desc and len(desc) <= 60 and 0 < len(body) <= 4000
        skills_store.validate_name(name)


def test_tenant_law_holds_for_seeds(desk):
    skill_packs.seed(T)
    assert skills_store.listing(T2) == []                  # a seed belongs to ONE tenant


# ---------------------------------------------------------------- (4) import / export

def test_import_markdown_claude_code_shape(desk):
    md = ("---\nname: meeting-notes\n"
          "description: Turn a meeting into minutes with owners\n---\n1. Decisions first.\n")
    r = skill_packs.import_skills(T, [md])
    assert r["ok"] and r["created"] == ["meeting-notes"] and r["errors"] == []
    assert skills_store.read(T, "meeting-notes")["body"].startswith("1. Decisions")


def test_import_json_rows(desk):
    r = skill_packs.import_skills(T, [{"name": "json-row", "description": "A JSON import row",
                                       "body": "the body"}])
    assert r["created"] == ["json-row"]


def test_import_never_overwrites(desk):
    _mk()
    r = skill_packs.import_skills(T, [{"name": "deploy-flask-app",
                                       "description": "How to deploy a Flask app to the VPS",
                                       "body": "hijack"}])
    assert r["skipped"] and "already exists" in r["skipped"][0]["reason"]
    assert "hijack" not in skills_store.read(T, "deploy-flask-app")["body"]


def test_import_cap_and_lint(desk):
    r = skill_packs.import_skills(T, [{"name": f"bulk-{i:02d}", "description": f"Bulk skill {i}",
                                       "body": "b"} for i in range(26)])
    assert "capped at 25" in r["error"]
    r = skill_packs.import_skills(T, [{"name": "Bad Name!", "description": "x", "body": "y"}])
    assert r["errors"] and skills_store.listing(T) == []   # nothing half-applied


def test_export_round_trip(desk):
    _mk()
    skills_store.set_enabled(T, "deploy-flask-app", False)
    out = skill_packs.export_skills(T)
    assert out["ok"] and out["skills"][0]["enabled"] is False
    r = skill_packs.import_skills(T2, out["skills"])
    assert r["created"] == ["deploy-flask-app"]
    a = skills_store.read(T, "deploy-flask-app")
    b = skills_store.read(T2, "deploy-flask-app")
    assert a["body"] == b["body"] and a["description"] == b["description"]


# ---------------------------------------------------------------- (5) share

def _three_reads(name="deploy-flask-app"):
    for _ in range(3):
        skills_store.read(T, name)


def test_nomination_needs_the_reads(desk):
    _mk()
    skills_store.read(T, "deploy-flask-app")               # 1 of 3
    r = skill_packs.share_nominate(T, "deploy-flask-app")
    assert "3 real reads" in r["error"]
    _three_reads()
    r = skill_packs.share_nominate(T, "deploy-flask-app", note="much used")
    assert r["ok"] and r["status"] == "pending" and r["reads"] == 4   # 1 + 3, gate is >= 3


def test_nomination_refuses_parked_and_dup(desk):
    _mk()
    _three_reads()
    skills_store.set_enabled(T, "deploy-flask-app", False)
    assert "parked" in skill_packs.share_nominate(T, "deploy-flask-app")["error"]
    skills_store.set_enabled(T, "deploy-flask-app", True)
    assert skill_packs.share_nominate(T, "deploy-flask-app")["ok"]
    r = skill_packs.share_nominate(T, "deploy-flask-app")
    assert "already pending" in r["error"]


def test_the_tap_publishes_redacted_and_anonymous(desk):
    _mk(body="1. use the key sk-abcdef1234567890abcdef in the deploy env. 2. restart.")
    _three_reads()
    assert skill_packs.share_nominate(T, "deploy-flask-app")["ok"]
    r = skill_packs.share_decide(T, "deploy-flask-app", approve=True)
    assert r["status"] == "published"
    shelf = skill_packs.pack_read("deploy-flask-app")
    assert shelf and "sk-abcdef1234567890abcdef" not in shelf["body"]   # re-redacted
    assert "***redacted***" in shelf["body"]
    import glob as _g
    shelf_files = " ".join(open(f, encoding="utf-8").read()
                           for f in _g.glob(os.path.join(
                               skills_store.skills_dir(skill_packs.PACK_TENANT), "*.md")))
    assert T not in shelf_files and "second-tenant" not in shelf_files   # no tenant trace
    assert any(s["name"] == "deploy-flask-app" for s in skill_packs.packs())
    rows = store.skill_share_rows(T)
    assert rows[0]["status"] == "published" and rows[0]["decided_at"]


def test_the_tap_rejects_and_cannot_double_decide(desk):
    _mk()
    _three_reads()
    skill_packs.share_nominate(T, "deploy-flask-app")
    assert skill_packs.share_decide(T, "deploy-flask-app", approve=False)["status"] == "rejected"
    assert skill_packs.pack_read("deploy-flask-app") is None
    assert "already rejected" in skill_packs.share_decide(T, "deploy-flask-app", approve=True)["error"]


def test_shelf_collision_needs_a_rename(desk):
    _mk()
    _three_reads()
    skill_packs.share_nominate(T, "deploy-flask-app")
    assert skill_packs.share_decide(T, "deploy-flask-app", approve=True)["ok"]
    skills_store.create(T2, "deploy-flask-app", "How to deploy a Flask app to the VPS", "other body")
    for _ in range(3):
        skills_store.read(T2, "deploy-flask-app")
    skill_packs.share_nominate(T2, "deploy-flask-app")
    r = skill_packs.share_decide(T2, "deploy-flask-app", approve=True)
    assert "different pack" in r["error"]                  # the shelf is curated, not clobbered


def test_install_is_create_if_missing(desk):
    skills_store.create(skill_packs.PACK_TENANT, "shelf-pack", "A pack on the shelf", "pack body")
    assert skill_packs.pack_install(T, "shelf-pack")["ok"]
    assert skills_store.read(T, "shelf-pack")["body"] == "pack body"
    skills_store.create(T, "hers", "Her own pack", "hers")
    r = skill_packs.pack_install(T, "nope-not-there")
    assert "not on the shelf" in r["error"]


def test_share_switch_off(desk, monkeypatch):
    _mk()
    _three_reads()
    monkeypatch.setenv("CODER_SKILLS_SHARE", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert "coder_skills_share" in skill_packs.share_nominate(T, "deploy-flask-app")["error"]
    get_settings.cache_clear()


def test_curator_nominates_end_to_end(desk, monkeypatch):
    """The weekly run hands much-read skills to the ledger - with NO pending pairs needed."""
    from app.coder import curator, observer as coder_observer
    monkeypatch.setenv("CODER_CURATOR", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    _mk()
    _three_reads()
    async def _no_brain(*a, **k):
        raise AssertionError("the brain must not be called for a nomination-only run")
    monkeypatch.setattr(coder_observer, "_call_brain", _no_brain)
    rep = asyncio.run(curator.consolidate(T, get_settings()))
    assert rep["nominated"] == 1 and rep["brain"] is False
    pend = store.skill_share_rows(T, "pending")
    assert len(pend) == 1 and pend[0]["name"] == "deploy-flask-app"


# ---------------------------------------------------------------- (6) reach

def test_child_skills_block(desk):
    _mk()
    blk = inject.child_skills(T, "deploy the flask app")
    assert "deploy-flask-app" in blk and "skill_manage" in blk
    assert len(blk) <= 400
    assert inject.child_skills(T2, "deploy") == ""          # tenant law


def test_child_system_prompt_carries_skills(desk, monkeypatch):
    from app.agent import santosh
    _mk()
    seen = {}

    async def fake_brain(brain, system, history, settings, tools=None, **_):
        seen["system"] = system
        return [{"type": "text", "text": "report"}], "end_turn"

    real = santosh._call_brain
    santosh._call_brain = fake_brain
    try:
        ctx = type("C", (), {"tenant_id": T, "conversation_id": "c", "actor": "owner", "place": ""})()
        out = asyncio.run(_run_child(ctx, {"prompt": "deploy the flask app please"}))
    finally:
        santosh._call_brain = real
    assert out["ok"] is True
    assert "LEARNED SKILLS" in seen["system"] and "deploy-flask-app" in seen["system"]
    assert seen["system"].startswith("You are ONE of Santosh's parallel workers")


async def _run_child(ctx, task):
    from app.config import get_settings
    from app.coder.delegate import run_child
    return await run_child(ctx, get_settings(), task, 0)


def test_devsahayak_skills_block_whole_body(desk):
    _mk(body="1. build with systemd. 2. always add the healthz route.")
    from app.devsahayak.loop import _skills_block, SKILLS_BUDGET
    blk = _skills_block("deploy my flask app to the VPS", T)
    assert "deploy-flask-app" in blk and "systemd" in blk and "healthz" in blk
    assert len(blk) <= SKILLS_BUDGET
    assert _skills_block("deploy my flask app", "") == ""   # no tenant: nothing rides
    assert _skills_block("deploy my flask app", T2) == ""   # tenant law


def test_devsahayak_first_messages_wire_the_block():
    """Source pins: the edit loop AND the plan pass read matching skills into their first ask."""
    from app.devsahayak import loop
    src = inspect.getsource(loop)
    assert "_skills_block(t.text, getattr(t, \"tenant_id\", \"\"))" in src
    # both call sites stand inside a first-message build that ends in the explore instruction
    assert src.count('_skills_block(t.text') >= 2


# ---------------------------------------------------------------- (7) routes + switches + version

def _client(tenant=T):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.coder.service import make_router
    app = FastAPI()
    app.include_router(make_router(_nok, lambda _req: tenant))
    return TestClient(app)


async def _nok(request):
    return None


def test_routes_mounted():
    from app.coder import service as coder_service
    src = inspect.getsource(coder_service)
    for frag in ('@r.get("/skills")', '@r.post("/skills")', '@r.post("/skills/enabled")',
                 '@r.post("/skills/import")', '@r.get("/skills/export")',
                 '@r.get("/skills/shares")', '@r.post("/skills/shares/decide")',
                 '@r.get("/skills/packs")', '@r.post("/skills/packs/read")',
                 '@r.post("/skills/packs/install")'):
        assert frag in src, f"route missing: {frag}"


def test_desk_route_live_seeds_and_counts(desk):
    c = _client()
    got = c.get("/api/coder/skills").json()
    assert len(got["skills"]) == len(skill_packs.all_seed_files()) + len(skill_packs.claude_dirs())
    assert got["skills"][0]["shown"] == 0 and got["skills"][0]["read"] == 0
    inject.skills_block(T, "deploy")                        # one shown
    skills_store.read(T, "deploy-flask-app")
    got = c.get("/api/coder/skills").json()
    row = next(s for s in got["skills"] if s["name"] == "deploy-flask-app")
    assert row["shown"] == 1 and row["read"] == 1
    # a second tenant: her pre-existing skill survives the seed untouched (hers win)
    skills_store.create(T2, "deploy-flask-app", "Her own deploy runbook", "her words")
    got2 = _client(T2).get("/api/coder/skills").json()
    assert len(got2["skills"]) == len(skill_packs.all_seed_files()) + len(skill_packs.claude_dirs())
    row2 = next(s for s in got2["skills"] if s["name"] == "deploy-flask-app")
    assert row2["description"] == "Her own deploy runbook"


def test_toggle_import_export_routes_live(desk):
    c = _client()
    c.get("/api/coder/skills")                              # the seed lands first
    assert c.post("/api/coder/skills/enabled",
                  json={"name": "deploy-flask-app", "enabled": False}).json()["changed"] is True
    row = next(s for s in c.get("/api/coder/skills").json()["skills"]
               if s["name"] == "deploy-flask-app")
    assert row["enabled"] is False
    imp = c.post("/api/coder/skills/import",
                 json={"items": [{"name": "route-skill", "description": "A route import",
                                  "body": "b"}]}).json()
    assert imp["created"] == ["route-skill"]
    exp = c.get("/api/coder/skills/export").json()
    assert any(s["name"] == "route-skill" for s in exp["skills"])


def test_shares_and_packs_routes_live(desk):
    c = _client()
    assert c.get("/api/coder/skills/shares").json()["pending"] == []
    _mk()
    _three_reads()
    assert c.post("/api/coder/skills/shares/decide",
                  json={"name": "deploy-flask-app", "approve": True}).json().get("error")
    # the nomination itself rides the curator; the desk's decide refuses without one
    skill_packs.share_nominate(T, "deploy-flask-app")
    r = c.post("/api/coder/skills/shares/decide", json={"name": "deploy-flask-app",
                                                        "approve": True}).json()
    assert r["status"] == "published"
    assert any(p["name"] == "deploy-flask-app" for p in c.get("/api/coder/skills/packs").json()["packs"])
    assert c.post("/api/coder/skills/packs/read", json={"name": "deploy-flask-app"}).json()["body"]
    inst = c.post("/api/coder/skills/packs/install", json={"name": "deploy-flask-app"}).json()
    assert "already exists" in inst["error"]                # create-if-missing: hers win


def test_kill_switch_skills(desk, monkeypatch):
    monkeypatch.setenv("CODER_SKILLS", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    c = _client()
    assert c.get("/api/coder/skills").json() == {"skills": []}
    assert "coder_skills" in c.post("/api/coder/skills/import", json={"items": []}).json()["error"]
    assert inject.skills_block(T, "deploy") == "" and inject.child_skills(T, "deploy") == ""
    get_settings.cache_clear()


def test_kill_switch_master(desk, monkeypatch):
    monkeypatch.setenv("CODER_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert skill_packs.seed(T)["seeded"] == 0
    get_settings.cache_clear()


def test_package_exports_skill_packs(desk):
    assert getattr(coder, "skill_packs", None) is not None
    assert "skill_packs" in coder.__all__


def test_version_layer():
    server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # server/
    main = open(os.path.join(server_dir, "app", "main.py"), encoding="utf-8").read()
    assert 'APP_VERSION = "0.754.0"' in main   # the story pin rides the newest story (the v0.476 precedent)
    pub = open(os.path.join(server_dir, "..", "pubspec.yaml"), encoding="utf-8").read()
    assert "version: 0.754.0+753" in pub
    assert store._SCHEMA_VERSION == 3
