"""v0.560.0 SPEC SUTRA - the spec-driven ladder (owner: "FEED THIS TO HOOLA AI . GIT SPEC KIT TO HOOLA END TO END").

The github/spec-kit repo (MIT, READ archived at download/SPEC_KIT_READ.md) ported IDEA-ONLY onto
house rails: ONE tool `speckit`, actions constitution | specify | clarify | plan | tasks | analyze |
converge | list. What is tested FOR REAL (all offline, per-tenant sqlite wiped per test): the ladder
end to end to verdict=converged; the never-guess law (markers, clarify priority order, answers
recorded, open marker blocks analyze); the constitution (starter auto-serve, every-law-checked,
justified violations, amendments logged + the amended-after-plan note); traceability (T### numbers,
ghost refs refused, untraced story tasks refused, P1 coverage blocking, P2/P3 a note); the converge
loop (append-only tasks, never-rewrite enforcement, computed verdict, severity-first ordering,
unrequested-work note, unknown done ids refused); the envelope shape and OUT_OF_ORDER hints; the
kill switch (list stays answerable); tenant isolation; registry 581 pin; APP_VERSION pin.
"""
import asyncio
import json
import shutil
from pathlib import Path

import pytest

from app.agent import speckit_tools as S
from app.agent.tools import Ctx

CTX = Ctx(tenant_id="sp-test-tenant", conversation_id="c1")
CTX2 = Ctx(tenant_id="sp-other-tenant", conversation_id="c2")


def _wipe(tenant):
    shutil.rmtree(Path("data") / "speckit" / tenant, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_state():
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)
    yield
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)


def run(action="list", ctx=None, **kw):
    return asyncio.run(S.speckit(ctx or CTX, action, **kw))


def specify(name="Dukaan Site", **over):
    args = dict(name=name,
                intent="Her shop wants an online catalogue with WhatsApp orders, because walk-ins fell.",
                features=[
                    {"title": "Catalogue page with photos", "priority": "P1",
                     "detail": "She adds items with a photo and price [NEEDS CLARIFICATION: how many items per page?]"},
                    {"title": "WhatsApp order button", "priority": "P1", "detail": "One tap opens WhatsApp with the cart"},
                    {"title": "Hindi + English toggle", "priority": "P2", "detail": ""},
                ],
                stories=[{"title": "Owner adds a product", "priority": "P1",
                          "scenarios": [{"given": "she is on the add page", "when": "she saves with photo+price",
                                         "then": "the product shows on the catalogue"}]},
                         {"title": "Buyer orders on WhatsApp", "priority": "P1",
                          "scenarios": [{"given": "a cart has items", "when": "the buyer taps order",
                                         "then": "WhatsApp opens with the list"}]}],
                metrics=[{"name": "orders per week", "target": "10 in month one"}])
    args.update(over)
    return run("specify", **args)


def plan_gates():
    return [{"article": "I", "status": "pass"}, {"article": "II", "status": "pass"},
            {"article": "III", "status": "pass"}, {"article": "IV", "status": "pass"},
            {"article": "V", "status": "pass"}]


def task_list():
    return [
        {"title": "Scaffold the site project", "phase": "setup"},
        {"title": "Catalogue data model + storage", "phase": "foundational", "source_refs": ["FR-001"]},
        {"title": "Catalogue page with photos", "phase": "story", "story": "US1", "source_refs": ["FR-001", "US1-AC1"]},
        {"title": "WhatsApp order flow", "phase": "story", "story": "US2", "source_refs": ["FR-002", "US2-AC1"]},
        {"title": "Lighthouse pass + polish", "phase": "polish"},
    ]


# ---------------------------------------------------------------- the envelope
def test_envelope_shape_is_exactly_one_object():
    out = run()
    assert set(out) >= {"schema_version", "ok", "tool", "action", "project_id", "stage", "meta", "error"}
    assert out["schema_version"] == 1 and out["ok"] and out["tool"] == "speckit" and out["error"] is None
    assert isinstance(out["meta"]["elapsed_ms"], int) and out["meta"]["elapsed_ms"] >= 0


def test_unknown_action_and_bad_input_are_envelopes_never_exceptions():
    out = run("flying")
    assert out["ok"] is False and out["error"]["code"] == "BAD_INPUT"
    assert "constitution" in out["error"]["message"] and "list" in out["error"]["message"]


def test_unknown_project_is_not_found_with_a_list_hint():
    out = run("analyze", project_id="sp_nope")
    assert out["error"]["code"] == "NOT_FOUND" and "action=list" in out["error"]["hint"]


# ---------------------------------------------------------------- the ladder: end to end
def test_the_full_ladder_runs_to_converged():
    sp = specify()
    assert sp["ok"] and sp["stage"] == "specified" and sp["project_id"]
    pid = sp["project_id"]
    assert sp["meta"]["requirements"] == 3 and sp["meta"]["stories"] == 2 and sp["meta"]["success_metrics"] == 1
    assert sp["meta"]["open_unknowns"] == 1 and sp["meta"]["next"] == "clarify"

    cl = run("clarify", project_id=pid)
    assert cl["ok"] and cl["items"][0]["id"] == "Q1" and cl["items"][0]["klass"] == "scope"
    assert "[NEEDS CLARIFICATION" not in cl["items"][0]["question"]
    cl2 = run("clarify", project_id=pid, answers=[{"id": "Q1", "answer": "12 items per page with load more"}])
    assert cl2["ok"] and cl2["meta"]["open_unknowns"] == 0

    pl = run("plan", project_id=pid, decisions=[{"topic": "storage", "decision": "sqlite per tenant", "why": "house lane"}],
             gates=plan_gates())
    assert pl["ok"] and pl["stage"] == "planned" and pl["meta"]["laws_checked"] == 5

    tk = run("tasks", project_id=pid, tasks=task_list())
    assert tk["ok"] and tk["stage"] == "tasks_ready"
    assert [t["id"] for t in tk["tasks"]] == [f"T{i:03d}" for i in range(1, 6)]
    assert tk["tasks"][1]["source_refs"] == ["FR-001"]

    an = run("analyze", project_id=pid)
    assert an["ok"] and an["meta"]["verdict"] == "clean" and an["meta"]["blocking"] == 0
    # FR-003 (P2) has no task yet: an honest deferral note, never a silent pass
    assert an["meta"]["traceability"] == {"covered": 4, "total": 5, "pct": 80}
    assert an["meta"]["notes"] == 1 and an["findings"][0]["kind"] == "coverage_p2_p3"

    cv = run("converge", project_id=pid, done=["T001", "T002", "T003", "T004", "T005"], gaps=[])
    assert cv["ok"] and cv["stage"] == "converged" and cv["meta"]["verdict"] == "converged"
    assert cv["meta"]["open_tasks"] == 0 and cv["meta"]["round"] == 1

    full = run("list", project_id=pid)
    assert full["ok"] and full["meta"]["tasks_done"] == 5 and full["meta"]["tasks_total"] == 5
    assert len(full["converge_log"]) == 1


def test_converge_loop_appends_gaps_until_converged():
    pid = specify()["project_id"]
    run("plan", project_id=pid, gates=plan_gates())
    run("tasks", project_id=pid, tasks=task_list())
    r1 = run("converge", project_id=pid, done=["T001", "T002"],
             gaps=[{"type": "missing", "severity": "critical", "description": "photo upload rejects 8 MB files",
                    "source_ref": "FR-001"},
                   {"type": "unrequested", "severity": "minor", "description": "a footer nobody asked for"}])
    assert r1["meta"]["verdict"] == "more_rounds" and r1["stage"] == "converging"
    added = {t["id"] for t in r1["tasks_added"]}
    assert added == {"T006", "T007"}
    # severity-first: the critical gap got the lower number
    t6 = next(t for t in r1["tasks_added"] if t["id"] == "T006")
    assert t6["gap_severity"] == "critical" and t6["phase"] == "convergence" and t6["source_refs"] == ["FR-001"]
    r2 = run("converge", project_id=pid, done=["T003", "T004", "T005", "T007"], gaps=[])
    assert r2["meta"]["verdict"] == "more_rounds"
    r3 = run("converge", project_id=pid, done=["T006"], gaps=[])
    assert r3["meta"]["verdict"] == "converged" and r3["stage"] == "converged"
    log = run("list", project_id=pid)["converge_log"]
    assert [r["verdict"] for r in log] == ["more_rounds", "more_rounds", "converged"]


def test_unrequested_gap_carries_her_word_note():
    pid = specify()["project_id"]
    run("plan", project_id=pid, gates=plan_gates())
    run("tasks", project_id=pid, tasks=task_list())
    out = run("converge", project_id=pid, done=[],
              gaps=[{"type": "unrequested", "description": "crypto miner found in the build"}])
    assert out["ok"] and "her word" in out["meta"]["note"]


# ---------------------------------------------------------------- never guess: markers + clarify
def test_marker_cap_and_priority_order():
    feats = [{"title": f"F{i}", "priority": "P1",
              "detail": f"[NEEDS CLARIFICATION: q{i} about scope?]"} for i in range(1, 7)]
    out = specify(name="Too Vague", features=feats)
    assert out["error"]["code"] == "BAD_INPUT" and "too vague" in out["error"]["message"]

    feats = feats[:5]
    sp = specify(name="Five Unknowns", features=feats)
    assert sp["ok"] and sp["meta"]["open_unknowns"] == 5
    cl = run("clarify", project_id=sp["project_id"])
    assert [i["id"] for i in cl["items"]] == [f"Q{i}" for i in range(1, 6)]


def test_clarify_orders_scope_security_ux_technical():
    sp = specify(name="Ordered", features=[
        {"title": "A", "priority": "P1", "detail": "[NEEDS CLARIFICATION: what api latency target?]"
         "[NEEDS CLARIFICATION: what data does privacy need?]"
         "[NEEDS CLARIFICATION: what should the screen look like?]"
         "[NEEDS CLARIFICATION: which cities are in scope?]"}])
    cl = run("clarify", project_id=sp["project_id"])
    assert [i["klass"] for i in cl["items"]] == ["scope", "security", "ux", "technical"]


def test_answers_are_recorded_and_open_marker_blocks_analyze():
    sp = specify()
    pid = sp["project_id"]
    run("plan", project_id=pid, gates=plan_gates())
    run("tasks", project_id=pid, tasks=task_list())
    an = run("analyze", project_id=pid)
    kinds = {f["kind"] for f in an["findings"]}
    assert "open_unknowns" in kinds and an["meta"]["verdict"] == "findings"
    blocking = [f for f in an["findings"] if f["severity"] == "blocking"]
    assert any(f["kind"] == "open_unknowns" for f in blocking)

    cl = run("clarify", project_id=pid, answers=[{"id": "Q1", "answer": "12 items per page with load more"}])
    assert cl["ok"] and cl["meta"]["open_unknowns"] == 0 and cl["meta"]["resolved_now"] == 1
    full = run("list", project_id=pid)
    assert full["spec"]["clarifications"][0]["answer"] == "12 items per page with load more"
    an2 = run("analyze", project_id=pid)
    assert "open_unknowns" not in {f["kind"] for f in an2["findings"]}


def test_empty_answer_is_refused_and_stale_q_id_too():
    sp = specify()
    pid = sp["project_id"]
    out = run("clarify", project_id=pid, answers=[{"id": "Q1", "answer": "   "}])
    assert out["error"]["code"] == "BAD_INPUT"
    out = run("clarify", project_id=pid, answers=[{"id": "Q9", "answer": "x"}])
    assert out["error"]["code"] == "BAD_INPUT" and "Q1" in out["error"]["message"]


# ---------------------------------------------------------------- the constitution
def test_starter_constitution_serves_and_shows():
    out = run("constitution")
    assert out["ok"] and [a["id"] for a in out["items"]] == ["I", "II", "III", "IV", "V"]
    assert out["meta"]["starter"] is True
    sp = specify()
    show = run("constitution", project_id=sp["project_id"])
    assert show["ok"] and len(show["items"]) == 5 and show["meta"]["starter"] is True


def test_plan_must_check_every_law_and_justify_violations():
    sp = specify()
    pid = sp["project_id"]
    out = run("plan", project_id=pid, gates=[{"article": "I", "status": "pass"}])
    assert out["error"]["code"] == "BAD_INPUT" and "III" in out["error"]["message"]
    out = run("plan", project_id=pid, gates=plan_gates()[:4] + [{"article": "V", "status": "violation"}])
    assert out["error"]["code"] == "BAD_INPUT" and "justification" in out["error"]["message"]
    out = run("plan", project_id=pid, gates=plan_gates()[:4] +
              [{"article": "V", "status": "violation", "justification": "the simpler shared cart was rejected: her buyers order one shop at a time"}])
    assert out["ok"] and out["meta"]["violations"] == 1
    full = run("list", project_id=pid)
    assert full["plan"]["gates"][4]["justification"].startswith("the simpler")


def test_own_constitution_needs_rationale_and_is_logged():
    sp = specify()
    pid = sp["project_id"]
    out = run("constitution", project_id=pid, articles=[{"title": "Offline first", "text": "Works with no network"}])
    assert out["error"]["code"] == "BAD_INPUT" and "rationale" in out["error"]["message"]
    out = run("constitution", project_id=pid, articles=[{"title": "Offline first", "text": "Works with no network"}],
              rationale="her shop runs on a flaky connection; the site must not need it")
    assert out["ok"] and out["meta"]["amended"] and out["meta"]["rationale_logged"]
    full = run("list", project_id=pid)
    assert full["constitution"][0]["title"] == "Offline first" and len(full["constitution"]) == 1
    assert full["meta"]["starter_constitution"] is False
    # amendment after the plan -> analyze notes the re-check (needs spec + plan + tasks to cross)
    run("plan", project_id=pid, gates=plan_gates())
    run("tasks", project_id=pid, tasks=task_list())
    run("constitution", project_id=pid, articles=[{"title": "One page", "text": "Single page only"}],
        rationale="simpler")
    an = run("analyze", project_id=pid)
    assert "constitution_amended_after_plan" in {f["kind"] for f in an["findings"]}


# ---------------------------------------------------------------- traceability
def test_ghost_refs_and_untraced_story_tasks_are_refused():
    sp = specify()
    pid = sp["project_id"]
    run("plan", project_id=pid, gates=plan_gates())
    out = run("tasks", project_id=pid, tasks=[{"title": "X", "phase": "story", "story": "US1",
                                               "source_refs": ["FR-009"]}])
    assert out["error"]["code"] == "BAD_INPUT" and "ghost" in out["error"]["message"] and "FR-009" in out["error"]["message"]
    out = run("tasks", project_id=pid, tasks=[{"title": "X", "phase": "story", "story": "US1"}])
    assert out["error"]["code"] == "BAD_INPUT" and "unrequested" in out["error"]["message"]
    out = run("tasks", project_id=pid, tasks=[{"title": "X", "phase": "story", "story": "US99",
                                               "source_refs": ["FR-001"]}])
    assert out["error"]["code"] == "BAD_INPUT" and "US99" in out["error"]["message"]
    out = run("tasks", project_id=pid, tasks=[{"title": "X", "phase": "story", "story": "US1",
                                               "source_refs": ["NOT-A-REF"]}])
    assert out["error"]["code"] == "BAD_INPUT" and "does not look like" in out["error"]["message"]


def test_analyze_blocks_on_p1_coverage_and_notes_p2_p3():
    sp = specify()
    pid = sp["project_id"]
    run("plan", project_id=pid, gates=plan_gates())
    run("tasks", project_id=pid, tasks=[
        {"title": "only the catalogue", "phase": "story", "story": "US1", "source_refs": ["FR-001"]}])
    an = run("analyze", project_id=pid)
    kinds = {f["kind"]: f["severity"] for f in an["findings"]}
    assert kinds.get("coverage_p1") == "blocking"        # FR-002 + US2 unserved
    assert kinds.get("coverage_p2_p3") == "note"          # FR-003 unserved
    assert an["meta"]["verdict"] == "findings"
    assert an["meta"]["traceability"]["total"] == 5 and an["meta"]["traceability"]["covered"] == 2


def test_phase_order_note():
    sp = specify()
    pid = sp["project_id"]
    run("plan", project_id=pid, gates=plan_gates())
    run("tasks", project_id=pid, tasks=[
        {"title": "story first, wrong order", "phase": "story", "story": "US1", "source_refs": ["FR-001", "US1-AC1"]},
        {"title": "setup after", "phase": "setup"}])
    an = run("analyze", project_id=pid)
    assert "phase_order" in {f["kind"] for f in an["findings"]}


# ---------------------------------------------------------------- the ladder's order
def test_out_of_order_envelopes_name_the_step():
    sp = specify()
    pid = sp["project_id"]
    # spec exists, plan missing: tasks must say plan first
    out = run("tasks", project_id=pid, tasks=task_list())
    assert out["error"]["code"] == "OUT_OF_ORDER" and "action=plan" in out["error"]["hint"]
    # converge on a ladder with no plan/tasks
    out = run("converge", project_id=pid, done=[], gaps=[])
    assert out["error"]["code"] == "OUT_OF_ORDER" and "ladder" in out["error"]["hint"]
    run("plan", project_id=pid, gates=plan_gates())
    # plan exists, tasks missing: converge still says no
    out = run("converge", project_id=pid, done=[], gaps=[])
    assert out["error"]["code"] == "OUT_OF_ORDER"
    out = run("analyze", project_id=pid)
    assert out["error"]["code"] == "OUT_OF_ORDER"


def test_analyze_needs_both_spec_and_tasks():
    sp = specify()
    out = run("analyze", project_id=sp["project_id"])
    assert out["error"]["code"] == "OUT_OF_ORDER"


# ---------------------------------------------------------------- append-only law
def test_tasks_action_refuses_to_rewrite_after_converge():
    pid = specify()["project_id"]
    run("plan", project_id=pid, gates=plan_gates())
    run("tasks", project_id=pid, tasks=task_list())
    run("converge", project_id=pid, done=["T001"], gaps=[])
    out = run("tasks", project_id=pid, tasks=task_list())
    assert out["error"]["code"] == "CONFLICT" and "append-only" in out["error"]["message"]
    # converge keeps appending instead
    out = run("converge", project_id=pid, done=["T002"],
              gaps=[{"type": "partial", "description": "cart total misses GST", "source_ref": "FR-002"}])
    assert out["ok"] and out["meta"]["append_only"] is True and out["meta"]["round"] == 2


def test_converge_refuses_invented_done_ids_and_bad_gaps():
    pid = specify()["project_id"]
    run("plan", project_id=pid, gates=plan_gates())
    run("tasks", project_id=pid, tasks=task_list())
    out = run("converge", project_id=pid, done=["T999"], gaps=[])
    assert out["error"]["code"] == "BAD_INPUT" and "T999" in out["error"]["message"]
    out = run("converge", project_id=pid, done=[], gaps=[{"type": "alien", "description": "x"}])
    assert out["error"]["code"] == "BAD_INPUT" and "missing" in out["error"]["message"]
    out = run("converge", project_id=pid, done=[], gaps=[{"type": "missing", "description": "x", "severity": "cosmic"}])
    assert out["error"]["code"] == "BAD_INPUT"
    out = run("converge", project_id=pid, done=[], gaps=[{"type": "missing", "description": "x", "source_ref": "US9"}])
    assert out["error"]["code"] == "BAD_INPUT" and "US9" in out["error"]["message"]


def test_converge_before_anything_is_out_of_order():
    sp = specify()
    out = run("converge", project_id=sp["project_id"], done=[], gaps=[])
    assert out["error"]["code"] == "OUT_OF_ORDER"


# ---------------------------------------------------------------- once-only names + NOT_FOUND
def test_project_names_are_once_only():
    specify(name="Ek Naam")
    out = specify(name="Ek Naam")
    assert out["error"]["code"] == "CONFLICT" and "already exists" in out["error"]["message"]


def test_specify_validation_table():
    out = specify(name="")
    assert out["error"]["code"] == "BAD_INPUT"
    out = specify(intent="short")
    assert out["error"]["code"] == "BAD_INPUT" and "intent" in out["error"]["message"]
    out = specify(features=[])
    assert out["error"]["code"] == "BAD_INPUT"
    out = specify(features=[{"title": "no p1", "priority": "P2"}])
    assert out["error"]["code"] == "BAD_INPUT" and "P1" in out["error"]["message"]
    out = specify(features=[{"title": "x", "priority": "P9"}])
    assert out["error"]["code"] == "BAD_INPUT"
    out = specify(stories="nope")
    assert out["error"]["code"] == "BAD_INPUT"
    out = specify(metrics=[{"name": ""}])
    assert out["error"]["code"] == "BAD_INPUT"


# ---------------------------------------------------------------- the doctor surfaces
def test_list_boards_and_full_ladder():
    assert run()["meta"]["count"] == 0
    a = specify(name="P A")["project_id"]
    b = specify(name="P B")["project_id"]
    board = run()
    assert board["meta"]["count"] == 2
    assert {i["stage"] for i in board["items"]} == {"specified"}
    one = run("list", project_id=a)
    assert one["project_id"] == a and one["spec"]["name"] == "P A"
    assert one["meta"]["starter_constitution"] is True and one["meta"]["tasks_total"] == 0


def test_kill_switch_is_honest_but_introspection_survives(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "speckit_enabled", False, raising=False)
    out = specify()
    assert out["ok"] is False and out["error"]["code"] == "NEED_SETUP"
    assert run()["ok"] is True                        # list stays answerable
    assert run("constitution")["ok"] is True          # the starter reading too
    # a write dressed as constitution still stops
    out = run("constitution", articles=[{"title": "X", "text": "y"}], rationale="why")
    assert out["error"]["code"] == "NEED_SETUP"


# ---------------------------------------------------------------- how-leak scanner (a warning, never a block)
def test_how_leaks_are_warned_not_blocked():
    out = specify(intent="Build it in React with a Postgres database because the shop needs an online catalogue.",
                  features=[{"title": "Catalogue", "priority": "P1", "detail": "FastAPI endpoints for items"}])
    assert out["ok"]
    leaks = out["meta"]["how_leaks"]
    assert {"react", "postgres"} <= set(leaks[0]["words"]) and "fastapi" in leaks[1]["words"]


def test_scanners_unit():
    assert S.scan_markers("a [NEEDS CLARIFICATION: what?] b") == ["what?"]
    assert S.classify_question("which cities are in scope?") == "scope"
    assert S.classify_question("is OTP needed?") == "security"
    assert S.classify_question("hindi or english first?") == "ux"
    assert S.classify_question("rate limit per hour?") == "technical"
    assert S.classify_question("???") == "scope"          # unclassifiable stays with the owner
    assert S._roman(4) == "IV" and S._roman(12) == "XII"


# ---------------------------------------------------------------- tenant isolation
def test_tenants_cannot_see_each_others_projects():
    a = run("specify", ctx=CTX, name="Meri Dukaan",
            intent="Her shop catalogue, because walk-ins fell.",
            features=[{"title": "Catalogue", "priority": "P1"}])
    b = run("specify", ctx=CTX2, name="Uska Bazaar",
            intent="Her bazaar stalls tracker, because Sundays crowd.",
            features=[{"title": "Stalls", "priority": "P1"}])
    assert run("list", ctx=CTX2)["meta"]["count"] == 1
    # tenant 2 cannot touch tenant 1's project, and the reverse
    assert run("analyze", ctx=CTX2, project_id=a["project_id"])["error"]["code"] == "NOT_FOUND"
    assert run("list", ctx=CTX, project_id=b["project_id"])["error"]["code"] == "NOT_FOUND"
    assert run("list", ctx=CTX2, project_id=b["project_id"])["project_id"] == b["project_id"]


# ---------------------------------------------------------------- the house wiring
def test_the_tool_is_registered_in_the_house():
    from app.agent import admit, tools
    names = [t["name"] for t in tools.TOOLS]
    assert names.count("speckit") == 1
    assert "speckit" in tools.HANDLERS and "speckit" in tools.TOOL_LABELS
    assert tools.FAMILY_OF["speckit"] == "speckit"
    assert len(tools.TOOLS) == 627, "626 + 1 app_engine (v0.824 APP ENGINE 1: the Web Studio React app lane - one new tool). 625 + 1 hoola_design (v0.817.0 HOOLA DESIGN: the design editor's one tool). 623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " + ("581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 580 (the dev chain on the merged tree, their v0.568.0 fef8a44ea) + 1 speckit "
                                     "(v0.569 SPEC SUTRA: the spec-kit ladder - constitution/specify/clarify/plan/"
                                     "tasks/analyze/converge/list, append-only converge, computed verdict, "
                                     "per-tenant sqlite)")
    assert "speckit" not in admit.CORE_FAMILIES      # a work lane, not the always-on set
    assert "speckit" in admit.EXTRA_KEYS and "user story" in admit.EXTRA_KEYS["speckit"]
    assert "spec" not in admit.EXTRA_KEYS["speckit"]  # bare "spec" stays with product's action=spec


def test_the_spec_promises_the_ladder():
    from app.agent import tools
    spec = next(t for t in tools.TOOLS if t["name"] == "speckit")
    desc = spec["description"]
    for word in ("specify", "clarify", "plan", "tasks", "analyze", "converge", "APPENDS", "OUT_OF_ORDER"):
        assert word in desc, word
    assert spec["input_schema"]["properties"]["action"]["enum"] == list(S.VALID_ACTIONS)


def test_app_version_is_the_conscious_bump():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.849.0"
    root = Path(__file__).resolve().parents[2]
    assert "0.849.0+848" in (root / "pubspec.yaml").read_text()
