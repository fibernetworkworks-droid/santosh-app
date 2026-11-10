"""v0.514.0 HOOLA CREW - the crewAIInc/crewAI port (owner: 'READ THIS REPO AND DEVLOPE IT
FOR HOOLA'). The repo was read end-to-end first (crewAIInc/crewAI @ 027638ad, HEAD of main
at clone time, 2026-11-04, MIT (c) 2025 crewAI, Inc.): Crew/Agent/Task/Process, the
AgentExecutor ReAct loop, hierarchical manager delegation (AgentTools: DelegateWork/
AskQuestion), guardrails with bounded retries, async tasks joining before the next sync
task, kickoff_for_each, usage metrics. This suite pins the port:

(1) INERTNESS: app.crew is inert library - a fresh interpreter imports it with zero
    threads/env/files, and the package has NO network imports (the aep P1 law; the
    provider stays outside - the runner seam carries it).
(2) CORE SHAPES: Process (sequential|hierarchical, upstream's two), TaskOutput (the
    capped context view), UsageMetrics (the honest requests-shaped ledger), CrewOutput
    (raw = the LAST task's output, the upstream shape).
(3) SPEC LAWS (upstream validators, kept): roles unique; every task's agent in the
    roster (empty = the first agent, upstream's default shape); context refs resolve to
    EARLIER tasks only (validate_context_no_future_tasks); hierarchical REQUIRES a
    manager and the manager carries NO tools (upstream's "Manager agent should not have
    tools"); caps 6 agents / 12 tasks; async task with context refused (it would read
    outputs that may not exist); max_iter 1..8; {key} interpolation with unknown tokens
    left verbatim (honest templates).
(4) THE ENGINE on a mocked runner seam (the docs7 _http-seam law - no test touches the
    brain): sequential with context threading + usage aggregation + raw=last; async
    tasks JOIN before the next sync task (_process_async_tasks); guardrail retry carries
    the feedback back into the prompt, exhaustion is an HONEST failed TaskOutput
    (upstream raises; a crew reports); runner timeout honest; hierarchical manager loop
    (DELEGATE/ASK/FINISH strict lines, one nudge on a no-move round, round budget
    honest, unknown role honest); kickoff_for_each.
(5) THE DOOR: ONE crew_run tool mounted last (registry 543); kill switch coder_crew
    default OFF fail-closed; invalid spec honest; door caps beside the library backstop;
    the deny set STRUCTURAL (delegate.CHILD_DENIED - a crew member can never delegate,
    send, approve or start PC jobs; the manager has no surface at all); voice absence;
    package export (the v0.478 lesson); config defaults; inputs caps.
(6) THE SEED LANE: skillpack/cr-crew-plays.md under its own once-ever stamp
    (skills:crewpack:<tenant>, the v0.492 pattern), found by _pack_seeders by name,
    create-if-missing, hers win, the 4,000-char cap, the three-door routing content
    pins; seed_files excludes the cr- prefix (starter stays 11; the library 68, NINE
    lanes).
(7) VERSION: APP_VERSION 0.514.0 + the story; pubspec 0.542.0+565.
"""
import asyncio
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

T, CONV = "tenant-crew", "conv-crew"


def _ctx(tenant=T):
    return type("C", (), {"tenant_id": tenant, "conversation_id": CONV})()


def _call(*args, **kw):
    from app.coder import crew_run
    return asyncio.run(crew_run.crew_run(*args, **kw))


def _spec(**over):
    """A minimal valid sequential crew."""
    base = {
        "name": "demo-crew",
        "agents": [{"role": "Researcher", "goal": "find facts"},
                   {"role": "Writer", "goal": "draft it"}],
        "tasks": [
            {"description": "Find 3 facts about {topic}", "expected_output": "3 bullets",
             "agent": "Researcher", "name": "find"},
            {"description": "Draft a paragraph using the facts", "agent": "Writer",
             "context": ["find"], "name": "draft"},
        ],
    }
    base.update(over)
    return base


@pytest.fixture()
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_CREW", "true")
    monkeypatch.setenv("CODER_SKILLS", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


# ---------------------------------------------------------------- (1) inertness + port law

def test_import_is_inert_fresh_interpreter():
    probe = (
        "import sys, threading, os, pathlib;"
        "before_threads = threading.active_count();"
        "before_env = {k: v for k, v in os.environ.items() if k.startswith(('CODER_', 'CREW_'))};"
        "cwd = pathlib.Path.cwd();"
        "before_files = {p.name for p in cwd.iterdir()};"
        "sys.path.insert(0, sys.argv[1]);"
        "import app.crew;"
        "assert threading.active_count() == before_threads, 'import spawned threads';"
        "assert {k: v for k, v in os.environ.items() if k.startswith(('CODER_', 'CREW_'))} == before_env, 'env read/written';"
        "assert {p.name for p in cwd.iterdir()} == before_files, 'import created files';"
        "print('inert-ok')"
    )
    out = subprocess.run([sys.executable, "-c", probe, str(REPO_ROOT / "server")],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "inert-ok" in out.stdout, out.stderr


def test_crew_source_has_no_network_imports():
    crew_dir = REPO_ROOT / "server/app/crew"
    banned = ("import requests", "import httpx", "import aiohttp", "import socket",
              "import urllib", "from urllib", "urlopen", "from ..agent", "from app.")
    for f in sorted(crew_dir.glob("*.py")):
        src = f.read_text(encoding="utf-8")
        for b in banned:
            assert b not in src, (f.name, b)


def test_zero_upstream_code():
    """The port law: no crewai import anywhere in the new code, and the library carries
    the provenance header (the read, the sha, MIT) instead of upstream files."""
    crew_dir = REPO_ROOT / "server/app/crew"
    for f in sorted(crew_dir.glob("*.py")):
        src = f.read_text(encoding="utf-8")
        assert "import crewai" not in src and "from crewai" not in src, f.name
    init = (crew_dir / "__init__.py").read_text(encoding="utf-8")
    assert "027638ad" in init and "MIT" in init and "ZERO upstream code" in init


# ---------------------------------------------------------------- (2) core shapes

def test_core_shapes():
    from app.crew.core import CrewOutput, Process, TaskOutput, UsageMetrics
    assert {p.value for p in Process} == {"sequential", "hierarchical"}
    u1, u2 = UsageMetrics(successful_requests=2, tool_calls=3), UsageMetrics(successful_requests=1, tool_calls=1, tokens_in=7)
    u1.add(u2)
    assert u1.successful_requests == 3 and u1.tool_calls == 4 and u1.total_tokens == 7
    o = TaskOutput(task="t", agent_role="R", raw="word " * 900)
    assert o.short(cap=100).endswith("...") and len(o.short(cap=100)) <= 100
    co = CrewOutput(crew="c", process="sequential", ok=True, raw="last", outputs=[], usage=u1)
    d = co.to_dict()
    assert d["raw"] == "last" and d["usage"]["successful_requests"] == 3


# ---------------------------------------------------------------- (3) spec laws

def test_spec_laws():
    from app.crew import Crew, CrewSpecError

    def refused(spec, why):
        with pytest.raises(CrewSpecError) as e:
            Crew.from_spec(spec)
        return str(e.value)

    assert "EARLIER" in refused(_spec(tasks=[{"description": "a", "context": ["ghost"]}]), "future ctx")
    assert "roster" in refused(_spec(tasks=[{"description": "a", "agent": "Ghost"}]), "roster")
    assert "must not carry tools" in refused(_spec(
        process="hierarchical", manager={"role": "M", "goal": "g", "tools": ["sheet_read"]}), "manager tools")
    assert "manager" in refused(_spec(process="hierarchical"), "no manager")
    assert "duplicate agent role" in refused(_spec(agents=[
        {"role": "A", "goal": "g"}, {"role": "A", "goal": "g2"}]), "dup role")
    assert "too many agents" in refused(_spec(agents=[{"role": f"A{i}", "goal": "g"} for i in range(7)]), "cap")
    assert "too many tasks" in refused(_spec(tasks=[{"description": f"t{i}"} for i in range(13)]), "cap")
    assert "unknown process" in refused(_spec(process="consensual"), "process")
    assert "context" in refused(_spec(tasks=[
        {"description": "a", "async_execution": True, "context": ["x"]}]), "async+context")
    assert "max_iter" in refused(_spec(agents=[{"role": "A", "goal": "g", "max_iter": 99}]), "max_iter")


def test_interpolation_honest():
    from app.crew.task import interpolate
    assert interpolate("Use {topic} and {n}", {"topic": "saffron", "n": 3}) == "Use saffron and 3"
    assert interpolate("Keep {unknown} verbatim", {"topic": "x"}) == "Keep {unknown} verbatim"
    assert interpolate("No inputs", None) == "No inputs"


# ---------------------------------------------------------------- (4) the engine

def _runner_from(scripts, repeat_last=True):
    """A mocked seam that CONSUMES scripts in order: scripts is a list of
    (expected_role_or_None, RunnerResult kwargs). One call pops one script; past the
    end it repeats the last entry (repeat_last) - an exhausted scripted crew fails
    honestly instead."""
    from app.crew.engine import RunnerResult
    calls = []
    it = {"i": 0}

    async def _run(**kw):
        calls.append(kw)
        i = it["i"]
        it["i"] += 1
        if i >= len(scripts):
            if repeat_last and scripts:
                i = len(scripts) - 1
            else:
                return RunnerResult(text="(script exhausted)", ok=False)
        role, res = scripts[i]
        assert role is None or role == kw.get("role"), (i, role, kw.get("role"))
        return RunnerResult(**res) if isinstance(res, dict) else res

    return _run, calls


def test_sequential_context_threading_and_usage():
    from app.crew import Crew, engine
    run, calls = _runner_from([(None, {"text": "report", "ok": True, "requests": 2, "tool_calls": 1})])
    c = Crew.from_spec(_spec())
    out = asyncio.run(engine.kickoff(c, run, {"topic": "saffron"}, max_task_seconds=5))
    assert out.ok and out.outputs[1].raw == "report"
    assert out.raw == "report"                                # raw = the LAST task's output
    assert "facts about saffron" in calls[0]["prompt"]        # {key} interpolation rode in
    assert "CONTEXT" in calls[1]["prompt"] and "[find] said:" in calls[1]["prompt"]
    assert calls[0]["role"] == "Researcher" and calls[1]["role"] == "Writer"
    assert out.usage.successful_requests == 4 and out.usage.tool_calls == 2
    assert out.seconds >= 0


def test_async_tasks_join_before_next_sync():
    from app.crew import Crew, engine
    order: list[str] = []

    async def run(**kw):
        if kw["prompt"].startswith("TASK: independent"):
            await asyncio.sleep(0.05)
            order.append(f"async:{kw['role']}")
            return engine.RunnerResult(text=f"async done for {kw['role']}", ok=True)
        order.append(f"sync:{kw['role']}")
        return engine.RunnerResult(text="sync done", ok=True)

    c = Crew.from_spec(_spec(tasks=[
        {"description": "independent one", "async_execution": True, "name": "a1"},
        {"description": "independent two", "async_execution": True, "name": "a2"},
        {"description": "dependent on both", "context": ["a1", "a2"], "name": "s1"},
    ]))
    out = asyncio.run(engine.kickoff(c, run, None, max_task_seconds=5))
    assert out.ok and len(out.outputs) == 3
    assert order[-1].startswith("sync:")                       # the join happened first


def test_guardrail_retry_then_exhaustion():
    from app.crew import Crew, engine
    n = {"k": 0}

    def guard(text):
        n["k"] += 1
        return (n["k"] >= 3, "too short")

    run, _ = _runner_from([(None, {"text": "x", "ok": True})])
    c = Crew.from_spec(_spec(agents=[{"role": "W", "goal": "g"}],
                             tasks=[{"description": "do it", "name": "t1"}]))
    c.tasks[0].guardrail = guard
    out = asyncio.run(engine.kickoff(c, run, None, max_task_seconds=5))
    assert out.ok and out.outputs[0].attempts == 3             # the feedback rode the retry

    n2 = {"k": 0}

    def guard_bad(text):
        n2["k"] += 1
        return (False, "no")

    c2 = Crew.from_spec(_spec(agents=[{"role": "W", "goal": "g"}],
                              tasks=[{"description": "do it", "name": "t1"}]))
    c2.tasks[0].guardrail = guard_bad
    c2.tasks[0].max_guardrail_retries = 1
    out2 = asyncio.run(engine.kickoff(c2, run, None, max_task_seconds=5))
    assert not out2.ok and "guardrail kept rejecting" in out2.outputs[0].guardrail_feedback


def test_task_timeout_honest():
    from app.crew import Crew, engine

    async def slow(**kw):
        await asyncio.sleep(2)
        return engine.RunnerResult(text="late", ok=True)

    c = Crew.from_spec(_spec(agents=[{"role": "W", "goal": "g"}],
                             tasks=[{"description": "do it", "name": "t1"}]))
    out = asyncio.run(engine.kickoff(c, slow, None, max_task_seconds=0.05))
    assert not out.ok and "timed out" in out.outputs[0].guardrail_feedback


def test_hierarchical_manager_loop():
    from app.crew import Crew, engine
    script = [
        ("Manager", {"text": "DELEGATE Researcher: find the facts", "ok": True}),
        ("Researcher", {"text": "the three facts", "ok": True, "tool_calls": 1}),
        ("Manager", {"text": "ASK Researcher: which fact matters most?", "ok": True}),
        ("Researcher", {"text": "the climate one", "ok": True}),
        ("Manager", {"text": "FINISH all facts found and ranked", "ok": True}),
    ]
    run, calls = _runner_from(script)
    c = Crew.from_spec(_spec(agents=[{"role": "Researcher", "goal": "facts"}],
                             tasks=[{"description": "find and rank facts"}],
                             process="hierarchical",
                             manager={"role": "Manager", "goal": "get it done"}))
    out = asyncio.run(engine.kickoff_hierarchical(c, run, None, max_task_seconds=5))
    assert out.ok and out.raw == "all facts found and ranked"
    assert calls[0]["tools"] == []                             # the manager has NO surface
    assert "MANAGER" in calls[0]["prompt"] and "DELEGATE" in calls[0]["prompt"]
    assert calls[1]["role"] == "Researcher"                    # the worker ran the assignment
    assert len(calls) == 5                                     # M, W, M(ASK), W, M(FINISH)
    assert out.usage.successful_requests >= 5


def test_hierarchical_honest_failures():
    from app.crew import Crew, engine
    # unknown role + no-move rounds + round exhaustion
    script = [
        ("Manager", {"text": "DELEGATE Ghost: do it", "ok": True}),
        ("Manager", {"text": "I think we are fine", "ok": True}),   # no move parsed -> nudge
        ("Manager", {"text": "DELEGATE Researcher: real work", "ok": True}),
        ("Researcher", {"text": "done", "ok": True}),
        ("Manager", {"text": "still thinking", "ok": True}),
    ]
    run, _ = _runner_from(script)
    c = Crew.from_spec(_spec(agents=[{"role": "Researcher", "goal": "facts"}],
                             tasks=[{"description": "find facts"}],
                             process="hierarchical",
                             manager={"role": "Manager", "goal": "get it done"}))
    out = asyncio.run(engine.kickoff_hierarchical(c, run, None, max_task_seconds=5,
                                                  max_rounds=3))
    assert not out.ok and "round budget exhausted" in out.outputs[0].guardrail_feedback
    assert any("no crew member named 'Ghost'" in (o.guardrail_feedback or "") for o in out.outputs)


def test_parse_manager_moves_strict():
    from app.crew.engine import parse_manager_moves
    moves = parse_manager_moves("DELEGATE Researcher: find facts\n"
                                "junk line\nASK Writer: is this enough?\nFINISH the answer")
    assert moves == [("DELEGATE", "Researcher", "find facts"),
                     ("ASK", "Writer", "is this enough?"),
                     ("FINISH", "", "the answer")]
    assert parse_manager_moves("") == []


def test_kickoff_for_each():
    from app.crew import Crew, engine
    run, _ = _runner_from([(None, {"text": "r", "ok": True})])
    c = Crew.from_spec(_spec())
    outs = asyncio.run(engine.kickoff_for_each(c, run, [{"topic": "a"}, {"topic": "b"}],
                                               max_task_seconds=5))
    assert len(outs) == 2 and all(o.ok for o in outs)


# ---------------------------------------------------------------- (5) the door

def test_registry_mount(env):
    from app.agent import tools
    assert "crew_run" in tools.HANDLERS and "crew_run" in tools.TOOL_LABELS
    assert any(t["name"] == "crew_run" for t in tools.TOOLS)
    assert len(tools.TOOLS) == 620, "617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " + ("581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 541 (v0.502) + 1 magic21 (v0.512) + 1 dhara_dsl (their v0.514) "
                                     "+ 10 construction (v0.522) + 1 crew_run (v0.523) + 2 from main's v0.533 CRAWL BRAIN wiring (healed in v0.537: this pin was red on pristine main) + 1 reach (v0.559 REACH MANCH) + 1 speckit (v0.569 SPEC SUTRA)")


def test_voice_absence(env):
    """A crew takes minutes; a call takes seconds - voice never sees crew_run."""
    from app import voice
    assert "crew_run" not in voice.VOICE_TOOL_NAMES


def test_package_export(env):
    """The v0.478 funnel lesson: coder.crew_run must exist on the PACKAGE path."""
    from app import coder
    assert hasattr(coder, "crew_run") and "crew_run" in coder.__all__
    assert coder.crew_run.CREW_HANDLERS["crew_run"] is not None
    import app.crew as crewlib
    assert hasattr(crewlib, "kickoff") and hasattr(crewlib, "Crew")


def test_config_defaults(env, monkeypatch):
    monkeypatch.delenv("CODER_CREW", raising=False)
    monkeypatch.delenv("CREWPACK_ENABLED", raising=False)
    monkeypatch.delenv("CODER_ENABLED", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    st = get_settings()
    assert st.coder_crew is False                  # the kill switch, default OFF
    assert st.coder_crew_max_agents == 6
    assert st.coder_crew_max_tasks == 12
    assert st.coder_crew_task_timeout_s == 180
    assert st.coder_crew_timeout_s == 600
    assert st.crewpack_enabled is True
    get_settings.cache_clear()


def test_kill_switch_off_fail_closed(env, monkeypatch):
    """coder_crew default OFF - the handler refuses before any brain call."""
    monkeypatch.setenv("CODER_CREW", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    out = _call(_ctx(), crew=_spec())
    assert "coder_crew" in out["error"]
    get_settings.cache_clear()


def test_invalid_spec_honest(env):
    out = _call(_ctx(), crew={"name": "x"})
    assert "invalid crew spec" in out["error"]
    out2 = _call(_ctx(), crew=_spec(process="hierarchical"))
    assert "invalid crew spec" in out2["error"]    # hierarchical without a manager


def test_door_caps(env, monkeypatch):
    monkeypatch.setenv("CODER_CREW_MAX_AGENTS", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    out = _call(_ctx(), crew=_spec(agents=[{"role": f"A{i}", "goal": "g"} for i in range(3)],
                                   tasks=[{"description": "t1"}]))
    assert "too many agents" in out["error"]
    get_settings.cache_clear()


def test_inputs_caps(env):
    out = _call(_ctx(), crew=_spec(), inputs={f"k{i}": "v" for i in range(25)})
    assert "too many inputs" in out["error"]


def test_deny_set_structural(env, monkeypatch):
    """A crew worker's surface NEVER contains the money/depth family - structural, not
    per-call (the delegate.CHILD_DENIED floor); an allowlist narrows further."""
    from app.coder import crew_run
    from app.coder.delegate import CHILD_DENIED
    specs = crew_run._worker_specs(())
    names = {s["name"] for s in specs}
    assert names and not (names & CHILD_DENIED)
    narrowed = crew_run._worker_specs(("sheet_read",))
    assert {s["name"] for s in narrowed} == {"sheet_read"}
    assert CHILD_DENIED == {"delegate_task", "confirm_send", "haan_karo", "pc_do"}


def test_door_runs_a_crew_on_mocked_brain(env, monkeypatch):
    """The full path with the brain mocked at the _call_brain seam: both tasks run,
    the report comes back, usage is the honest requests ledger."""
    from app.agent import llm, santosh

    class FakeBrain:
        pass

    brain = FakeBrain()

    async def fake_call_brain(b, system, history, settings, tools=None, max_tokens=0):
        last = history[-1]["content"]
        text = "".join(c.get("text", "") for c in last if isinstance(c, dict)).strip()
        if "TASK: Find 3 facts" in text:
            return ([{"type": "text", "text": "fact one; fact two; fact three"}], "end_turn")
        return ([{"type": "text", "text": "the drafted paragraph"}], "end_turn")

    monkeypatch.setattr(llm, "cheap_brain", lambda *a, **kw: brain)
    monkeypatch.setattr(santosh, "_call_brain", fake_call_brain)
    out = _call(_ctx(), crew=_spec(), inputs={"topic": "saffron"})
    assert out.get("ok") is True, out
    assert out["crew"] == "demo-crew" and out["process"] == "sequential"
    assert out["raw"] == "the drafted paragraph"
    assert [o["task"] for o in out["outputs"]] == ["find", "draft"]
    assert out["outputs"][0]["text"] == "fact one; fact two; fact three"
    assert out["usage"]["successful_requests"] == 2


# ---------------------------------------------------------------- (6) the seed lane

@pytest.fixture()
def desk(env, monkeypatch, tmp_path):
    from app.coder import skills_store, store
    store.ensure()
    skills_store.reset_for_tests()
    yield monkeypatch
    skills_store.reset_for_tests()


def test_cr_files_and_lane_counts():
    from app.coder import skill_packs
    assert len(skill_packs.seed_files()) == 11          # the starter lane is untouched
    assert len(skill_packs.byox_files()) == 31
    assert len(skill_packs.prog_files()) == 2
    assert len(skill_packs.sp_files()) == 15
    assert len(skill_packs.fe_files()) == 3
    assert len(skill_packs.cs_files()) == 2
    assert len(skill_packs.mg_files()) == 1
    assert len(skill_packs.bd_files()) == 2
    cr = skill_packs.cr_files()
    assert len(cr) == 1 and cr[0].stem == "cr-crew-plays"
    seed_dir = Path(skill_packs.SEED_DIR)
    assert len(list(seed_dir.glob("*.md"))) == 99      # 11+31+2+15+3+2+1+2+1+2+2+27, TWENTY-NINE lanes (th- v0.547, ed- v0.548, the 18 omni families v0.561)


def test_seed_crewpack_reaches_a_tenant_already_seeded(desk):
    from app.coder import skill_packs, skills_store, store
    T = "cr-t1"
    store.ensure()
    for stamp in (skill_packs.SEED_STAMP, skill_packs.BYOX_STAMP, skill_packs.PROG_STAMP,
                  skill_packs.SP_STAMP, skill_packs.FE_STAMP, skill_packs.CS_STAMP,
                  skill_packs.MG_STAMP, skill_packs.BD_STAMP):
        store.mark_consumed(stamp.format(T))            # ALL EIGHT are set - the cr stamp is NOT
    r = skill_packs.seed_crewpack(T)
    assert r["cr_seeded"] == 1
    assert skill_packs.seed_crewpack(T)["cr_seeded"] == 0      # own stamp: never twice
    names = {s["name"] for s in skills_store.listing(T)}
    assert names == {"cr-crew-plays"}


def test_seed_crewpack_hers_win(desk):
    from app.coder import skill_packs, skills_store
    T = "cr-t2"
    skills_store.create(T, "cr-crew-plays", "Her own crew notes", "her words")
    skill_packs.seed_crewpack(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "cr-crew-plays")
    assert row["description"] == "Her own crew notes"


def test_seed_crewpack_switch_off(desk):
    monkeypatch = desk
    from app.coder import skill_packs
    from app.config import get_settings
    monkeypatch.setenv("CREWPACK_ENABLED", "false")
    get_settings.cache_clear()
    assert skill_packs.seed_crewpack("cr-t3")["cr_seeded"] == 0
    get_settings.cache_clear()


def test_pack_seeders_finds_crewpack():
    from app.coder import service, skill_packs
    assert "seed_all(tenant)" in inspect.getsource(service)                      # the desk calls seed_all ...
    assert "seed_crewpack" in [f.__name__ for f in skill_packs._pack_seeders()]  # ... which finds this pack by name


def test_cr_files_pass_the_lint_gate():
    from app.coder import skill_packs
    from app.coder.skills_store import BODY_MAX, DESC_MAX, parse_skill, validate
    for f in skill_packs.cr_files():
        name, desc, body = parse_skill(f.read_text(encoding="utf-8"))
        assert name == f.stem
        assert len(desc) <= DESC_MAX, (f.name, len(desc))
        assert len(body) <= BODY_MAX, (f.name, len(body))
        validate(desc, body)


def test_crew_plays_pins_the_discipline():
    from app.coder import skill_packs
    from app.coder.skills_store import parse_skill
    body = ""
    for f in skill_packs.cr_files():
        name, _, b = parse_skill(f.read_text(encoding="utf-8"))
        if name == "cr-crew-plays":
            body = b
    for token in ("crew_run", "delegate_task", "dhara", "role", "goal", "backstory",
                  "expected_output", "context", "hierarchical", "MANAGER", "DELEGATE",
                  "FINISH", "async_execution", "Money and sends NEVER", "NEVER"):
        assert token in body, token


def test_injection_matches_a_crew_ask(desk):
    from app.coder import inject, skill_packs
    T = "cr-t4"
    skill_packs.seed_crewpack(T)
    block = inject.skills_block(T, "agents ki crew chahiye tasks aur roles ke saath")
    assert "cr-crew-plays" in block


# ---------------------------------------------------------------- (7) version

def test_version(env):
    from app import main as main_mod
    from pathlib import Path as P
    assert main_mod.APP_VERSION == "0.744.0"
    story = P(main_mod.__file__).read_text().split("APP_VERSION = ", 1)[1][:20000]
    # story pin moved to the newest story (the v0.549/v0.476 precedent: the newest
    # release's story carries the marker; the older stories live in git history)
    assert "HOOLA RETRIEVE" in story and "aep/retrieve.py" in story  # the newest-story precedent (the P5 markers live in the Previous chain)
    pub = (REPO_ROOT / "pubspec.yaml").read_text(encoding="utf-8")
    assert "version: 0.744.0+743" in pub
