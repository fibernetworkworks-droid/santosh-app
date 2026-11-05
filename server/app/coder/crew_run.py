"""HOOLA CREW (v0.514.0) - the crew_run tool door, the crewAI port's one surface.

The crewAI idea, house-sized: the OWNER describes a team (roles + goals + backstories)
and a task list; the crew runs INSIDE one turn over the SAME machinery every other
child agent rides - coder/delegate.py's bounded loop (_call_brain for the brain,
_run_tool as the single tool funnel, the CHILD_DENIED deny set for money and depth),
framed by each agent's identity. One tool, one concept: a crew spec goes in, per-task
outputs + an honest ledger come out.

The app.crew library owns the LAWS (validation, context threading, guardrails, the
hierarchical manager protocol); this door owns the RUNNER and the caps:

- kill switch coder_crew (default OFF - a crew spends real brain rounds: bake, then flip;
  the delegate_task shape, not the docs7 outbound-network shape)
- caps: coder_crew_max_agents 6 / coder_crew_max_tasks 12 (the library backstop doubled
  at the door), per-task coder_crew_task_timeout_s 180, whole-crew coder_crew_timeout_s 600
- inputs: <= 20 keys, string values <= 2000 chars, interpolated into task {key} slots
- every worker's tool surface: the registered specs MINUS delegate.CHILD_DENIED
  (delegate_task, confirm_send, haan_karo, pc_do - a crew worker can NEVER delegate,
  send, approve or start PC jobs; the delegate.py floor, structural not per-call),
  further narrowed by an agent's tools allowlist when one is given
- the manager has NO tool surface at all (upstream's "manager should not have tools"
  invariant, structural here; it moves via DELEGATE/ASK/FINISH text lines)
- voice never sees it (out of VOICE_TOOL_NAMES): a crew takes minutes, a call takes seconds
- stateless: the crew is the tool call; nothing stored server-side in v0.514 (the
  docs7/magic21 shape) - replay/checkpoints are the named next lane

The engine never imports this door; the door imports the engine. Tests mock
agent.santosh._call_brain (the docs7 _http-seam law) - no test touches the real brain.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass

log = logging.getLogger("coder.crew_run")

WORKER_SYSTEM = (
    "You are ONE member of Santosh's crew - a small team working one job together. "
    "Your identity:\n{framing}\n\n"
    "Do exactly the task you are given, use the tools you need, and finish with the "
    "final result as your report (no greetings, no questions back, English report). "
    "Other members' outputs may ride in as CONTEXT - build on them, never contradict them.")

MANAGER_SYSTEM = (
    "You are the MANAGER of Santosh's crew. You do not do the work yourself - you "
    "delegate it, ask your crew questions, and decide when the job is done. You have "
    "NO tools. Speak only in move lines:\n"
    "DELEGATE <role>: <assignment>\nASK <role>: <question>\nFINISH <the final answer>\n"
    "English. One move per line.")

CREW_RUNNER_MAX_TOKENS = 2000
INPUTS_MAX_KEYS = 20
INPUT_VALUE_MAX = 2000
RAW_CAP = 6000


def _settings():
    try:
        from ..config import get_settings
        return get_settings()
    except Exception:
        return None


def _knob(name: str, default):
    st = _settings()
    try:
        v = getattr(st, name, default)
        return default if v is None else v
    except Exception:
        return default


def _worker_specs(agent_tools: tuple[str, ...]) -> list[dict]:
    """The worker's tool surface: registered specs MINUS the deny set, optionally
    narrowed to the agent's allowlist (the delegate._child_specs idea, re-filtered)."""
    from .delegate import CHILD_DENIED
    from ..agent.tools import TOOLS
    base = [dict(t) for t in TOOLS if t.get("name") and t["name"] not in CHILD_DENIED]
    if not agent_tools:
        return base
    allow = {str(t) for t in agent_tools}
    return [t for t in base if t.get("name") in allow]


def _framing(role: str, goal: str, backstory: str) -> str:
    parts = [f"ROLE: {role}", f"GOAL: {goal}"]
    if backstory:
        parts.append(f"BACKSTORY: {backstory}")
    return "\n".join(p for p in parts if p)


@dataclass
class _Result:
    """The engine RunnerResult shape, built here so the seam stays one-way."""

    text: str
    ok: bool
    requests: int
    tool_calls: int
    seconds: float
    tokens_in: int = 0
    tokens_out: int = 0


async def crew_runner(ctx, settings, role: str, goal: str, backstory: str, prompt: str,
                      expected_output: str, tools: list, max_iter: int) -> _Result:
    """The seam's real side: ONE bounded worker on the house brain funnel.

    Manager calls arrive with tools=[] and get the manager framing (no tool surface)."""
    from ..agent import llm
    from ..agent.santosh import _call_brain, _run_tool
    from .delegate import CHILD_DENIED

    is_manager = not tools
    brain = llm.cheap_brain()
    if is_manager:
        system = MANAGER_SYSTEM
        specs: list[dict] = []
    else:
        system = WORKER_SYSTEM.format(framing=_framing(role, goal, backstory))
        specs = _worker_specs(tuple(tools))
    history: list[dict] = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    requests = 0
    tool_calls = 0
    t0 = time.time()

    def _blocks_text(blocks: list[dict]) -> str:
        return "".join(b.get("text", "") for b in (blocks or []) if b.get("type") == "text").strip()

    for _ in range(max(1, int(max_iter))):
        blocks, stop = await _call_brain(brain, system, history, settings,
                                         tools=specs, max_tokens=CREW_RUNNER_MAX_TOKENS)
        requests += 1
        text = _blocks_text(blocks)
        if stop != "tool_use" or not any(b.get("type") == "tool_use" for b in blocks or []):
            return _Result(text=text or "(no report)", ok=True, requests=requests,
                           tool_calls=tool_calls, seconds=time.time() - t0)
        history.append({"role": "assistant", "content": blocks})
        results = []
        for b in blocks:
            if b.get("type") != "tool_use":
                continue
            name, args = b.get("name", ""), b.get("input") or {}
            if is_manager or name in CHILD_DENIED or (tools and name not in set(tools)):
                results.append({"type": "tool_result", "tool_use_id": b.get("id", ""),
                                "content": f"DENIED: {name} is not available to this crew "
                                           f"member. Finish with what you have."})
                continue
            tool_calls += 1
            try:
                out = await _run_tool(name, args, ctx, settings)
                try:
                    line = json.dumps(out, ensure_ascii=False, default=str)[:4000]
                except Exception:
                    line = str(out)[:4000]
            except Exception as e:          # one failed tool never kills the worker
                line = f"error: {type(e).__name__}: {str(e)[:300]}"
            results.append({"type": "tool_result", "tool_use_id": b.get("id", ""),
                            "content": line})
        history.append({"role": "user", "content": results})
    return _Result(text="(stopped at the worker iteration budget; partial work above)",
                   ok=True, requests=requests, tool_calls=tool_calls, seconds=time.time() - t0)


def _make_runner(ctx, settings):
    """The engine-facing runner: engine kwargs -> the house worker loop."""

    async def _run(**kw):
        return await crew_runner(ctx, settings,
                                 role=str(kw.get("role") or ""),
                                 goal=str(kw.get("goal") or ""),
                                 backstory=str(kw.get("backstory") or ""),
                                 prompt=str(kw.get("prompt") or ""),
                                 expected_output=str(kw.get("expected_output") or ""),
                                 tools=list(kw.get("tools") or ()),
                                 max_iter=int(kw.get("max_iter") or 6))

    return _run


# ---------------------------------------------------------------- the tool

CREW_SCHEMA = {
    "name": "crew_run",
    "description": (
        "Run a CREW: a small named team of role agents (each with a goal and backstory) "
        "working a task list together inside this turn - sequential (each task builds on "
        "the ones before it via context) or hierarchical (a manager delegates and decides "
        "when it is done). Use for multi-role pipelines (research -> draft -> review); for "
        "parallel independent one-shots use delegate_task instead, for recurring schedules "
        "use dhara. Max 6 agents, 12 tasks; runs bounded by timeouts. Costs brain rounds."),
    "input_schema": {
        "type": "object",
        "properties": {
            "crew": {
                "type": "object",
                "description": "The crew spec.",
                "properties": {
                    "name": {"type": "string", "description": "Short crew name."},
                    "process": {"type": "string", "enum": ["sequential", "hierarchical"],
                                "description": "Default sequential."},
                    "agents": {
                        "type": "array",
                        "description": "1..6 members.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "description": "e.g. 'Researcher'"},
                                "goal": {"type": "string", "description": "What this member is for."},
                                "backstory": {"type": "string", "description": "Optional expertise."},
                                "tools": {"type": "array", "items": {"type": "string"},
                                          "description": "Optional tool-name allowlist."},
                                "max_iter": {"type": "integer", "description": "1..8, default 6."},
                            },
                            "required": ["role", "goal"],
                        },
                    },
                    "tasks": {
                        "type": "array",
                        "description": "1..12 tasks, in order.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "expected_output": {"type": "string",
                                                    "description": "What done looks like."},
                                "agent": {"type": "string", "description": "A role; default the first agent."},
                                "context": {"type": "array", "items": {"type": "string"},
                                            "description": "Names of EARLIER tasks to build on."},
                                "name": {"type": "string", "description": "Optional; defaults task-N."},
                                "async_execution": {"type": "boolean",
                                                    "description": "Independent task, runs concurrently (no context allowed)."},
                            },
                            "required": ["description"],
                        },
                    },
                    "manager": {
                        "type": "object",
                        "description": "Required for hierarchical. No tools.",
                        "properties": {
                            "role": {"type": "string"},
                            "goal": {"type": "string"},
                            "backstory": {"type": "string"},
                        },
                        "required": ["role", "goal"],
                    },
                },
                "required": ["name", "agents", "tasks"],
            },
            "inputs": {
                "type": "object",
                "description": "Optional {key: value} interpolated into task descriptions "
                               "as {key}. Max 20 keys.",
            },
        },
        "required": ["crew"],
    },
}

CREW_TOOLS = [CREW_SCHEMA]
CREW_LABELS = {"crew_run": "Crew bhej raha hoon - choti team ka kaam"}
CREW_HANDLERS: dict = {"crew_run": None}   # set below


async def crew_run(ctx, crew=None, inputs=None, **_):
    """The crew door: validate the spec, build the runner, hand it to the engine."""
    from ..config import get_settings
    st = get_settings()
    if not getattr(st, "coder_enabled", True) or not getattr(st, "coder_crew", False):
        return {"error": "crews are switched off (coder_crew)"}
    if not isinstance(crew, dict):
        return {"error": "crew must be an object: {name, process, agents[], tasks[]}."}
    if inputs is not None and not isinstance(inputs, dict):
        return {"error": "inputs must be an object of {key: value}."}
    clean_inputs: dict = {}
    for k, v in dict(inputs or {}).items():
        if len(clean_inputs) >= INPUTS_MAX_KEYS:
            return {"error": f"too many inputs (max {INPUTS_MAX_KEYS})."}
        clean_inputs[str(k)[:80]] = str(v)[:INPUT_VALUE_MAX]

    import app.crew as _c
    try:
        c = _c.Crew.from_spec(crew)
    except Exception as e:
        return {"error": f"invalid crew spec: {e}"}
    max_agents = int(_knob("coder_crew_max_agents", 6))
    max_tasks = int(_knob("coder_crew_max_tasks", 12))
    if len(c.agents) > max_agents:
        return {"error": f"too many agents: {len(c.agents)} (max {max_agents})."}
    if len(c.tasks) > max_tasks:
        return {"error": f"too many tasks: {len(c.tasks)} (max {max_tasks})."}

    task_timeout = float(_knob("coder_crew_task_timeout_s", 180))
    crew_timeout = float(_knob("coder_crew_timeout_s", 600))
    runner = _make_runner(ctx, st)
    t0 = time.time()
    try:
        if c.process.value == "hierarchical":
            out = await asyncio.wait_for(_c.engine.kickoff_hierarchical(
                c, runner, clean_inputs or None, max_task_seconds=task_timeout),
                timeout=crew_timeout)
        else:
            out = await asyncio.wait_for(_c.engine.kickoff(
                c, runner, clean_inputs or None, max_task_seconds=task_timeout),
                timeout=crew_timeout)
    except asyncio.TimeoutError:
        return {"error": f"crew timed out after {int(crew_timeout)}s (partial work not kept - "
                         f"split it into smaller crews)."}
    except Exception as e:                                      # noqa: BLE001 - honest door
        log.exception("crew_run failed")
        return {"error": f"crew failed: {type(e).__name__}: {str(e)[:200]}"}
    d = out.to_dict(cap=RAW_CAP)
    d["seconds"] = round(time.time() - t0, 1)
    return d


CREW_HANDLERS["crew_run"] = crew_run
