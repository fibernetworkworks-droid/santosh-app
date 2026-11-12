"""v0.478.0 HOOLA SELF-TEACH - skills + the nudge fork (the Hermes self-teaching loop ported).

What this suite pins, piece by piece:
(1) SKILLS STORE: SKILL.md files under <coder_dir>/skills/<tenant>/, frontmatter lint HARD
    (name <=64 lowercase-hyphenated, description <=60 one sentence, body <=4000), atomic writes
    with a .bak on overwrite, read-before-write on update, delete is a SOLO op, batch cap 10,
    atomic batch (snapshot -> any failure restores every file), tenant isolation, and every
    write mirrored into the vault so the FTS5 search covers skills (LIKE fallback without FTS5).
(2) skill_manage: ONE tool, operations array, kill-switched by coder_skills; a successful use
    RESETS the nudge's turn counter (Hermes's rule).
(3) INJECT: matched skills ride at the TOP of the coder primer block (inside its budget,
    name+description only - read-before-follow via skill_manage), voice <=1200 / chat <=400,
    and the block order pin holds: coder memory AFTER yaad, skills INSIDE the coder block.
(4) NUDGE (the self-teaching fork): every coder_nudge_every turns ONE background reflection
    writes durable observations (actor='nudge') and class-level skills; ONE combined pass on
    the cheap brain with a STABLE prefix; counter resets on skill_manage use; cooldown 5 min;
    privacy gate extends to the fork (a wholly <private> latest ask skips it); a live turn's
    poke() makes the fork DROP its writes - the live turn never waits; update needs the skill
    listed AND a real read; kill switches coder_enabled + coder_nudge silence everything.
"""
import asyncio
import os

import pytest

from app import coder
from app.coder import capture, inject, nudge, prompts, skills_store, skills_tool, store
from app.coder.skills_store import SkillError

T = "default"
CONV = "conv_selfteach"

OBS_XML = ("<observation><type>discovery</type><title>The VPS runs the server with systemd</title>"
           "<subtitle>restart discipline</subtitle><facts><fact>unit name hoola</fact></facts>"
           "<narrative>Deploys restart the unit; logs via journalctl.</narrative>"
           "<concepts><concept>how-it-works</concept></concepts></observation>")
SKILL_XML = ('<skill action="create" name="deploy-flask" description="How to deploy a Flask app to the VPS">'
             "1. scp the repo. 2. write the systemd unit. 3. restart hoola.</skill>")
SKILL_UPD_XML = ('<skill action="update" name="deploy-flask" description="How to deploy a Flask app to the VPS">'
                 "1. git pull. 2. restart the unit.</skill>")


def _settings(**over):
    from app.config import get_settings
    return get_settings()


@pytest.fixture()
def sk(env, monkeypatch, tmp_path):
    """Fresh vault in a TEMP dir (skill .md files must never land in the repo), skills ON,
    nudge state empty. coder_nudge stays OFF unless a test flips it."""
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_SKILLS", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    store.ensure()
    skills_store.reset_for_tests()
    nudge.reset_for_tests()
    nudge._BG.clear()
    yield monkeypatch
    skills_store.reset_for_tests()
    nudge.reset_for_tests()
    nudge._BG.clear()
    get_settings.cache_clear()


@pytest.fixture()
def nud(sk, monkeypatch):
    """The nudge ARMED (coder_nudge=true) with a short interval."""
    monkeypatch.setenv("CODER_NUDGE", "true")
    monkeypatch.setenv("CODER_NUDGE_EVERY", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    return monkeypatch


# ---------------------------------------------------------------- (1) lint + store

def test_skill_lint_rejects(sk):
    for bad in ("Bad Name", "Deploy Flask", "x" * 65, "-lead", "a_b"):
        with pytest.raises(SkillError):
            skills_store.create(T, bad, "desc", "body")
    with pytest.raises(SkillError):
        skills_store.create(T, "good-one", "d" * 61, "body")
    with pytest.raises(SkillError):
        skills_store.create(T, "good-one", "desc", "b" * 4001)
    with pytest.raises(SkillError):
        skills_store.create(T, "good-one", "desc", "   ")
    with pytest.raises(SkillError):
        skills_store.create(T, "good-one", "", "body")


def test_skill_crud_and_bak(sk, tmp_path):
    d = skills_store.skills_dir(T)
    assert skills_store.create(T, "deploy-flask", "How to deploy a Flask app to the VPS",
                               "1. scp the repo")["op"] == "create"
    with pytest.raises(SkillError):
        skills_store.create(T, "deploy-flask", "another", "body")   # exists -> update
    assert skills_store.update(T, "deploy-flask", body="2. systemd unit")["op"] == "update"
    # (the creator knew the body: create counts as the read; the fresh-process guard has its own test)
    assert os.path.exists(os.path.join(d, "deploy-flask.md.bak"))    # overwrite kept a .bak
    assert "systemd unit" in skills_store.read(T, "deploy-flask")["body"]
    assert skills_store.delete(T, "deploy-flask")["op"] == "delete"
    with pytest.raises(SkillError):
        skills_store.read(T, "deploy-flask")


def test_read_before_write_guard_on_fresh_process(sk):
    """Hermes's guard: a process that never read the skill cannot rewrite it. The nudge fork
    depends on this - listing alone is not knowing."""
    skills_store.create(T, "deploy-flask", "How to deploy a Flask app to the VPS",
                        "1. scp the repo")
    skills_store.reset_for_tests()                     # a fresh fork: the ledger is empty
    with pytest.raises(SkillError):
        skills_store.update(T, "deploy-flask", body="hijack")
    with pytest.raises(SkillError):
        skills_store.delete(T, "deploy-flask")         # delete demands the read too
    skills_store.read(T, "deploy-flask")
    assert skills_store.update(T, "deploy-flask", body="2. unit")["op"] == "update"
    skills_store.reset_for_tests()
    skills_store.read(T, "deploy-flask")
    assert skills_store.delete(T, "deploy-flask")["op"] == "delete"


def test_delete_solo_and_batch_cap(sk):
    assert "error" in skills_store.apply(T, [
        {"action": "delete", "name": "a-one"}, {"action": "create", "name": "b-two",
                                                "description": "d", "body": "b"}])
    assert "error" in skills_store.apply(T, [{"action": "create", "name": f"s{i}",
                                              "description": "d", "body": "b"}
                                             for i in range(11)])
    assert "error" in skills_store.apply(T, [])
    assert "error" in skills_store.apply(T, [{"action": "delete", "name": "missing-one"}])


def test_atomic_batch_rollback(sk):
    d = skills_store.skills_dir(T)
    skills_store.create(T, "keep-me", "An existing skill for the rollback test", "original")
    res = skills_store.apply(T, [{"action": "update", "name": "keep-me", "body": "changed"},
                                 {"action": "create", "name": "keep-me",
                                  "description": "dup create must fail", "body": "b"}])
    assert "error" in res
    assert "changed" not in skills_store.read(T, "keep-me")["body"]   # snapshot restored
    assert os.listdir(d).count("keep-me.md") == 1


def test_skill_mirror_search_and_tenant_isolation(sk):
    skills_store.create(T, "deploy-flask", "How to deploy a Flask app to the VPS with systemd",
                        "1. scp the repo")
    hits = store.skills_search(T, "deploy flask")
    assert hits and hits[0]["name"] == "deploy-flask"
    skills_store.create("other-tenant", "deploy-flask", "A DIFFERENT tenant's skill", "secret steps")
    hits_t = store.skills_search(T, "deploy flask")
    assert all("A DIFFERENT tenant" not in h["description"] for h in hits_t)
    assert store.skills_search("other-tenant", "deploy flask")[0]["description"].startswith("A DIFFERENT")
    skills_store.delete(T, "deploy-flask")
    assert store.skills_search(T, "deploy flask") == []               # unmirror on delete


# ---------------------------------------------------------------- (2) the tool

def test_skill_manage_handler_applies_and_resets_counter(sk, nud):
    ctx = type("C", (), {"tenant_id": T, "conversation_id": CONV})()
    nudge._counts[(T, CONV)] = 5                       # a mid-stretch counter
    res = asyncio.run(skills_tool.skill_manage(
        ctx, operations=[{"action": "create", "name": "note-orders",
                          "description": "How to record a WhatsApp order", "body": "1. ask"}]))
    assert res.get("ok"), res
    assert (T, CONV) not in nudge._counts              # Hermes's rule: use resets the counter
    assert any(x["name"] == "note-orders" for x in skills_store.listing(T))


def test_skill_manage_kill_switch(sk, monkeypatch):
    monkeypatch.setenv("CODER_SKILLS", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    ctx = type("C", (), {"tenant_id": T, "conversation_id": CONV})()
    res = asyncio.run(skills_tool.skill_manage(
        ctx, operations=[{"action": "create", "name": "no-skill",
                          "description": "must be refused", "body": "b"}]))
    assert "error" in res
    assert skills_store.listing(T) == []


def test_skill_manage_bad_ops_refused(sk):
    ctx = type("C", (), {"tenant_id": T, "conversation_id": CONV})()
    assert "error" in asyncio.run(skills_tool.skill_manage(ctx, operations="not-a-list"))
    assert "error" in asyncio.run(skills_tool.skill_manage(
        ctx, operations=[{"action": "explode", "name": "x"}]))


# ---------------------------------------------------------------- (3) injection

def test_skills_block_and_primer_placement(sk):
    skills_store.create(T, "deploy-flask", "How to deploy a Flask app to the VPS with systemd",
                        "1. scp the repo")
    blk = inject.skills_block(T, "deploy my flask app")
    assert "deploy-flask" in blk and blk.startswith("LEARNED SKILLS")
    assert inject.skills_block(T, "completely unrelated query about cooking") == ""
    p = inject.primer(T, conv=CONV, query="deploy my flask app")
    assert p.startswith(inject.HEADER)                 # the header stays FIRST
    assert "LEARNED SKILLS" in p.split("\n")[1]        # skills ride at the TOP, inside the block
    assert inject.primer(T, conv=CONV, query="") == ""  # no ask -> no skills, no primer rows


def test_skills_block_budgets_and_switch(sk, monkeypatch):
    skills_store.create(T, "deploy-flask", "How to deploy a Flask app to the VPS with systemd",
                        "1. scp the repo")
    assert len(inject.skills_block(T, "deploy my flask app", compact=True)) <= inject.SKILLS_COMPACT_BUDGET
    assert len(inject.skills_block(T, "deploy my flask app")) <= inject.SKILLS_VOICE_BUDGET
    monkeypatch.setenv("CODER_SKILLS", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert inject.skills_block(T, "deploy my flask app") == ""
    assert "LEARNED SKILLS" not in inject.primer(T, conv=CONV, query="deploy my flask app")


def test_turn_block_carries_skills_query(sk):
    skills_store.create(T, "deploy-flask", "How to deploy a Flask app to the VPS with systemd",
                        "1. scp the repo")
    blk = inject.turn_block(T, CONV, query="deploy my flask app")
    assert "deploy-flask" in blk
    # v0.559 SKILL KI SOOCHI (Claude's level 1): with no ask there is no MATCHED line, but every skill is still named
    empty = inject.turn_block(T, CONV, query="")
    assert "LEARNED SKILLS matching" not in empty and "ALL HER SKILLS" in empty and "deploy-flask" in empty


# ---------------------------------------------------------------- (4) the nudge fork

def test_nudge_counter_fires_at_interval(sk, nud, monkeypatch):
    fired: list = []

    async def spy(tenant, conv):
        fired.append((tenant, conv))

    monkeypatch.setattr(nudge, "reflect", spy)

    async def _turns(n):
        for _ in range(n):
            nudge.count_turn(T, CONV)
        await asyncio.sleep(0.02)          # let the spawned fork actually run

    asyncio.run(_turns(1))                             # 1 of 2: no fire
    assert fired == []
    asyncio.run(_turns(1))                             # 2 of 2: fire
    assert len(fired) == 1
    asyncio.run(_turns(1))                             # cooldown: no second fork within 5 min
    assert len(fired) == 1


def test_nudge_reset_on_skill_use(sk, nud, monkeypatch):
    fired: list = []

    async def spy(tenant, conv):
        fired.append((tenant, conv))

    monkeypatch.setattr(nudge, "reflect", spy)

    async def _turn():
        nudge.count_turn(T, CONV)
        await asyncio.sleep(0.02)

    asyncio.run(_turn())                               # 1 of 2
    nudge.reset_counter(T, CONV)                       # skill_manage happened
    asyncio.run(_turn())                               # 1 of 2 again: no fire yet
    assert fired == []


def test_nudge_disarmed_by_default(sk, monkeypatch):
    """coder_nudge default false: bakes on the VPS, then flips - nothing fires until then."""
    fired: list = []

    async def spy(tenant, conv):
        fired.append((tenant, conv))

    monkeypatch.setattr(nudge, "reflect", spy)

    async def _turn():
        nudge.count_turn(T, CONV)
        await asyncio.sleep(0.02)

    asyncio.run(_turn())
    asyncio.run(_turn())
    assert fired == [] and not nudge.armed()


def _arm_brain(monkeypatch, xml: str, poke_before: bool = False):
    from app.coder import observer

    async def fake_brain(system, user, settings):
        if poke_before:
            nudge.poke(CONV)                           # a live turn arrived mid-think
        return xml
    monkeypatch.setattr(observer, "_call_brain", fake_brain)


def test_nudge_reflect_writes_memory_and_skill(sk, nud, monkeypatch):
    capture.turn_prompt(T, CONV, "help me deploy my flask app")
    _arm_brain(monkeypatch, OBS_XML + SKILL_XML)
    asyncio.run(nudge.reflect(T, CONV))
    rows = store.recent_observations(T, limit=10, conv=CONV)
    assert rows and rows[0]["actor"] == "nudge"
    assert "systemd" in rows[0]["title"]
    assert any(s["name"] == "deploy-flask" for s in skills_store.listing(T))
    st = nudge.stats()
    assert st["runs"] == 1 and st["observations"] == 1 and st["skills"] == 1


def test_nudge_reflect_update_needs_list_and_read(sk, nud, monkeypatch):
    skills_store.create(T, "deploy-flask", "How to deploy a Flask app to the VPS with systemd",
                        "1. scp the repo")
    skills_store.reset_for_tests()                     # even the fork: listing, not a prior read
    capture.turn_prompt(T, CONV, "deploy my flask app again")
    _arm_brain(monkeypatch, SKILL_UPD_XML)
    asyncio.run(nudge.reflect(T, CONV))
    assert "git pull" in skills_store.read(T, "deploy-flask")["body"]
    _arm_brain(monkeypatch, '<skill action="update" name="ghost-skill" '
                            'description="not listed anywhere">new body</skill>')
    asyncio.run(nudge.reflect(T, CONV))
    with pytest.raises(SkillError):
        skills_store.read(T, "ghost-skill")            # an unlisted update never creates a file


def test_nudge_privacy_gate_extends_to_fork(sk, nud, monkeypatch):
    capture.turn_prompt(T, CONV, "<private>my tax passwords</private>")   # wholly private ask
    _arm_brain(monkeypatch, OBS_XML + SKILL_XML)
    asyncio.run(nudge.reflect(T, CONV))
    assert store.recent_observations(T, limit=10, conv=CONV) == []
    assert skills_store.listing(T) == []
    assert nudge.stats()["skipped"] == 1


def test_nudge_cancel_drops_writes(sk, nud, monkeypatch):
    capture.turn_prompt(T, CONV, "deploy my flask app")
    _arm_brain(monkeypatch, OBS_XML + SKILL_XML, poke_before=True)       # live turn mid-think
    asyncio.run(nudge.reflect(T, CONV))
    assert store.recent_observations(T, limit=10, conv=CONV) == []
    assert skills_store.listing(T) == []
    assert nudge.stats()["dropped"] == 1


def test_nudge_max_writes_cap(sk, nud, monkeypatch):
    monkeypatch.setenv("CODER_NUDGE_MAX_WRITES", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    capture.turn_prompt(T, CONV, "deploy my flask app")
    many = "".join(OBS_XML.replace("systemd", f"systemd {i}") for i in range(3))
    _arm_brain(monkeypatch, many)
    asyncio.run(nudge.reflect(T, CONV))
    assert len(store.recent_observations(T, limit=10, conv=CONV)) == 2   # the cap held


def test_nudge_reflection_prompts_are_stable_and_capped(sk):
    s1 = prompts.reflection_system()
    assert s1 == prompts.reflection_system()           # the stable-prefix discipline
    assert "never" in s1 and "Hindi" in s1             # English-observations law is IN the prompt
    user = prompts.reflection_user("[she asked] deploy flask", [], "")
    assert len(user) <= 20_000 + 2_000                 # the input budget


# ---------------------------------------------------------------- routes / stats / version

def test_skills_routes_mounted(sk):
    import inspect

    from app.coder import service
    src = inspect.getsource(service)
    assert '@r.get("/skills")' in src and '@r.post("/skills")' in src


def test_stats_carry_skills_and_nudge(sk, nud, monkeypatch):
    skills_store.create(T, "deploy-flask", "How to deploy a Flask app to the VPS with systemd",
                        "1. scp")
    capture.turn_prompt(T, CONV, "deploy my flask app")
    _arm_brain(monkeypatch, OBS_XML)
    asyncio.run(nudge.reflect(T, CONV))
    s = store.stats()
    assert s["skills"] == 1 and s["nudge_observations"] == 1 and s["nudge_conversations"] == 1


def test_version_stamp(sk):
    from app.main import APP_VERSION
    assert APP_VERSION == "0.838.0"
