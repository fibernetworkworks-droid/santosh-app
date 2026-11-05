"""HOOLA CREW engine - the executor (v0.514.0, the crewAI kickoff over a runner seam).

Upstream (crew.py _execute_tasks + agents/agent_executor.py): kickoff interpolates the
inputs, runs the task list under the process, threads context from earlier outputs,
joins async tasks before the next sync task, applies guardrails with bounded retries,
aggregates usage metrics, and in hierarchical mode lets a manager agent delegate to
crew members until it finishes.

THE SEAM (the whole port in one decision): the engine never talks to a provider. It
calls an injected async RUNNER:

    await runner(role=..., goal=..., backstory=..., prompt=...,
                 expected_output=..., tools=[...], max_iter=N) -> RunnerResult

RunnerResult(text, ok, tokens_in, tokens_out, requests, tool_calls) - the door's real
runner (coder/crew_run.py) is a role-framed house child worker (coder/delegate.py's
bounded _call_brain + _run_tool loop), so capture, scrub, timeout and the deny set see
every crew worker exactly like every other child. The library stays inert and fully
testable on a mocked seam (the docs7/magic21 law).

Kept upstream invariants:
- async tasks queue and JOIN before the next sync task (_process_async_tasks shape);
  trailing asyncs join at the end.
- context only from EARLIER tasks (validated in crew.py; the engine builds the block
  from what the task named, capped at CONTEXT_CAP).
- guardrail returns (bool, feedback); a retry carries the feedback back into the
  prompt; exhaustion is an HONEST failed TaskOutput (upstream raises; a crew reports -
  one failed task never sinks the crew).
- hierarchical: the manager speaks a strict text protocol - DELEGATE <role>: <assignment>
  / ASK <role>: <question> / FINISH <final answer> - bounded rounds, unparseable rounds
  get one honest nudge, round exhaustion fails honestly. Upstream delegates via
  function-calling tools; the seam is text, so the protocol is text (pinned deviation).
- CrewOutput.raw = the LAST task's output (sequential) or the manager's FINISH line
  (hierarchical), the upstream shape.
- kickoff_for_each: one run per input (upstream's shape).

Inert library until awaited: no app imports, no threads on import, no config reads.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from .agent import Agent
from .core import CrewOutput, Process, TaskOutput, UsageMetrics
from .crew import Crew
from .task import Task, interpolate

CONTEXT_CAP = 6000          # the house RETURN_CAP numbers (docs7)
FEEDBACK_MAX = 800


# ---------------------------------------------------------------- the runner seam

@dataclass
class RunnerResult:
    text: str = ""
    ok: bool = True
    tokens_in: int = 0
    tokens_out: int = 0
    requests: int = 1
    tool_calls: int = 0


Runner = Callable[..., Awaitable["RunnerResult"]]


def _usage_of(r: RunnerResult) -> UsageMetrics:
    return UsageMetrics(successful_requests=int(getattr(r, "requests", 1) or 1),
                        tool_calls=int(getattr(r, "tool_calls", 0) or 0),
                        tokens_in=int(getattr(r, "tokens_in", 0) or 0),
                        tokens_out=int(getattr(r, "tokens_out", 0) or 0))


def _context_block(task: Task, outputs: dict[str, TaskOutput]) -> str:
    if not task.context:
        return ""
    parts: list[str] = []
    for name in task.context:
        o = outputs.get(name)
        if o is None:
            parts.append(f"[{name}] (no output recorded)")
            continue
        parts.append(f"[{name}] said:\n{o.short()}")
    return "\n\n".join(parts)[:CONTEXT_CAP]


# ---------------------------------------------------------------- one task

async def _run_one_task(task: Task, agent: Agent, runner: Runner, inputs: dict | None,
                        outputs: dict[str, TaskOutput], max_task_seconds: float
                        ) -> tuple[TaskOutput, UsageMetrics]:
    """One task: interpolate, run, guardrail-retry, honest result (upstream _execute_core)."""
    t0 = time.time()
    base_prompt = interpolate(task.prompt_for(_context_block(task, outputs)), inputs)
    attempts = 0
    feedback = ""
    while True:
        attempts += 1
        prompt = base_prompt
        if feedback:
            prompt = (prompt + f"\n\nA REVIEWER REJECTED the previous result: {feedback[:FEEDBACK_MAX]}\n"
                      "Redo the task with the feedback applied.")
        try:
            r = await asyncio.wait_for(
                runner(role=agent.role, goal=agent.goal, backstory=agent.backstory,
                       prompt=prompt, expected_output=task.expected_output,
                       tools=list(agent.tools), max_iter=agent.max_iter),
                timeout=max_task_seconds)
        except asyncio.TimeoutError:
            return (TaskOutput(task=task.name, agent_role=agent.role, raw="", ok=False,
                               attempts=attempts, seconds=time.time() - t0,
                               guardrail_feedback=f"timed out after {int(max_task_seconds)}s"),
                    UsageMetrics())
        except Exception as e:                                  # noqa: BLE001 - one task never sinks the crew
            return (TaskOutput(task=task.name, agent_role=agent.role, raw="", ok=False,
                               attempts=attempts, seconds=time.time() - t0,
                               guardrail_feedback=f"{type(e).__name__}: {str(e)[:200]}"),
                    UsageMetrics())
        usage = _usage_of(r)
        if task.guardrail is None:
            return (TaskOutput(task=task.name, agent_role=agent.role, raw=r.text, ok=r.ok,
                               attempts=attempts, seconds=time.time() - t0), usage)
        try:
            passed, fb = task.guardrail(r.text)
        except Exception as e:                                  # noqa: BLE001 - a broken guardrail is honest
            return (TaskOutput(task=task.name, agent_role=agent.role, raw=r.text, ok=False,
                               attempts=attempts, seconds=time.time() - t0,
                               guardrail_feedback=f"guardrail failed to run: {type(e).__name__}: {str(e)[:200]}"),
                    usage)
        if passed:
            return (TaskOutput(task=task.name, agent_role=agent.role, raw=r.text, ok=r.ok,
                               attempts=attempts, seconds=time.time() - t0), usage)
        feedback = str(fb or "result rejected")
        if attempts > task.max_guardrail_retries:
            return (TaskOutput(task=task.name, agent_role=agent.role, raw=r.text, ok=False,
                               attempts=attempts, seconds=time.time() - t0,
                               guardrail_feedback=f"guardrail kept rejecting: {feedback[:FEEDBACK_MAX]}"),
                    usage)


# ---------------------------------------------------------------- sequential

async def kickoff(crew: Crew, runner: Runner, inputs: dict | None = None, *,
                  max_task_seconds: float = 180.0) -> CrewOutput:
    """The crewAI kickoff: validate, interpolate, execute under the process, aggregate."""
    crew.validate()
    t0 = time.time()
    usage = UsageMetrics()
    outputs: dict[str, TaskOutput] = {}
    pending: list[asyncio.Future] = []

    async def _join_pending() -> None:
        if not pending:
            return
        for out, u in await asyncio.gather(*pending):
            outputs[out.task] = out
            usage.add(u)
        pending.clear()

    for task in crew.tasks:
        agent = crew.agent_for(task)
        coro = _run_one_task(task, agent, runner, inputs, outputs, max_task_seconds)
        if task.async_execution:
            pending.append(asyncio.ensure_future(coro))
            continue
        await _join_pending()
        out, u = await coro
        outputs[task.name] = out
        usage.add(u)
    await _join_pending()

    ok = bool(outputs) and all(o.ok for o in outputs.values())
    last = crew.tasks[-1] if crew.tasks else None
    raw = outputs[last.name].raw if last and last.name in outputs else ""
    return CrewOutput(crew=crew.name, process=str(crew.process.value), ok=ok, raw=raw,
                      outputs=[outputs[t.name] for t in crew.tasks if t.name in outputs],
                      usage=usage, seconds=time.time() - t0)


# ---------------------------------------------------------------- hierarchical

DELEGATE_PREFIX = "DELEGATE "
ASK_PREFIX = "ASK "
FINISH_PREFIX = "FINISH "


def parse_manager_moves(text: str) -> list[tuple[str, str, str]]:
    """The strict protocol parse: [(move, target, payload)] in line order."""
    moves: list[tuple[str, str, str]] = []
    for line in str(text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(DELEGATE_PREFIX):
            rest = s[len(DELEGATE_PREFIX):]
            if ":" in rest:
                target, payload = rest.split(":", 1)
                moves.append(("DELEGATE", target.strip(), payload.strip()))
        elif s.startswith(ASK_PREFIX):
            rest = s[len(ASK_PREFIX):]
            if ":" in rest:
                target, payload = rest.split(":", 1)
                moves.append(("ASK", target.strip(), payload.strip()))
        elif s.startswith(FINISH_PREFIX):
            moves.append(("FINISH", "", s[len(FINISH_PREFIX):].strip()))
    return moves


async def _run_worker_assignment(crew: Crew, role: str, assignment: str, runner: Runner,
                                 inputs: dict | None, max_task_seconds: float
                                 ) -> tuple[TaskOutput, UsageMetrics]:
    """A manager DELEGATE/ASK: run the named agent on the assignment."""
    agent = next((a for a in crew.agents if a.role == role), None)
    if agent is None:
        return (TaskOutput(task=f"delegate:{role}", agent_role=role, ok=False,
                           guardrail_feedback=f"no crew member named '{role}'"), UsageMetrics())
    task = Task(description=assignment or "help the manager", agent=role, name=f"delegate:{role}")
    t0 = time.time()
    try:
        r = await asyncio.wait_for(
            runner(role=agent.role, goal=agent.goal, backstory=agent.backstory,
                   prompt=interpolate(task.prompt_for(""), inputs),
                   expected_output="", tools=list(agent.tools), max_iter=agent.max_iter),
            timeout=max_task_seconds)
    except asyncio.TimeoutError:
        return (TaskOutput(task=task.name, agent_role=role, ok=False, seconds=time.time() - t0,
                           guardrail_feedback=f"timed out after {int(max_task_seconds)}s"), UsageMetrics())
    except Exception as e:                                      # noqa: BLE001
        return (TaskOutput(task=task.name, agent_role=role, ok=False, seconds=time.time() - t0,
                           guardrail_feedback=f"{type(e).__name__}: {str(e)[:200]}"), UsageMetrics())
    return (TaskOutput(task=task.name, agent_role=role, raw=r.text, ok=r.ok,
                       seconds=time.time() - t0), _usage_of(r))


async def kickoff_hierarchical(crew: Crew, runner: Runner, inputs: dict | None = None, *,
                               max_task_seconds: float = 180.0,
                               max_rounds: int | None = None) -> CrewOutput:
    """The manager loop (upstream _run_hierarchical_process + AgentTools delegation)."""
    crew.validate()
    t0 = time.time()
    manager = crew.manager
    assert manager is not None                      # crew.validate() guarantees it
    roster = "\n".join(f"- {a.role}: {a.goal}" for a in crew.agents)
    task_list = "\n".join(f"- {t.name}: {t.description}" for t in crew.tasks)
    rounds_cap = max_rounds if max_rounds is not None else 2 * len(crew.tasks) + 2
    transcript: list[str] = []
    usage = UsageMetrics()
    raw = ""
    ok = False
    outcome = TaskOutput(task="manager", agent_role=manager.role, ok=False)
    outputs: list[TaskOutput] = [outcome]

    for round_no in range(1, rounds_cap + 1):
        prompt = (
            f"You are the MANAGER of a crew.\n\nCREW MEMBERS:\n{roster}\n\n"
            f"CREW TASK LIST:\n{task_list}\n\n"
            + ("TRANSCRIPT SO FAR:\n" + "\n\n".join(transcript[-6:]) + "\n\n" if transcript else "")
            + "Move the work forward with ONE OR MORE lines, exactly one move per line:\n"
            f"{DELEGATE_PREFIX}<crew member role>: <the assignment for them>\n"
            f"{ASK_PREFIX}<crew member role>: <the question for them>\n"
            f"{FINISH_PREFIX}<the final answer once the task list is done>")
        try:
            r = await asyncio.wait_for(
                runner(role=manager.role, goal=manager.goal, backstory=manager.backstory,
                       prompt=interpolate(prompt, inputs), expected_output="",
                       tools=[], max_iter=manager.max_iter),
                timeout=max_task_seconds)
        except asyncio.TimeoutError:
            outcome.guardrail_feedback = f"manager timed out after {int(max_task_seconds)}s"
            break
        except Exception as e:                                  # noqa: BLE001
            outcome.guardrail_feedback = f"{type(e).__name__}: {str(e)[:200]}"
            break
        usage.add(_usage_of(r))
        moves = parse_manager_moves(r.text)
        if not moves:
            transcript.append(f"[round {round_no}] manager (no move parsed): {r.text[:300]}")
            continue
        finished = False
        for move, target, payload in moves:
            if move == "FINISH":
                raw, ok, finished = payload, True, True
                transcript.append(f"[round {round_no}] manager FINISH")
                break
            out, u = await _run_worker_assignment(crew, target, payload, runner, inputs,
                                                  max_task_seconds)
            outputs.append(out)
            usage.add(u)
            transcript.append(f"[round {round_no}] {move} {target} -> "
                              f"{'ok' if out.ok else 'FAILED'}: {out.short(cap=800)}")
        if finished:
            outcome.ok = True
            outcome.raw = raw
            break
    else:
        outcome.guardrail_feedback = (outcome.guardrail_feedback or
                                      f"round budget exhausted ({rounds_cap} rounds)")

    crew_ok = ok and all(o.ok for o in outputs)
    return CrewOutput(crew=crew.name, process=str(crew.process.value), ok=crew_ok, raw=raw,
                      outputs=outputs, usage=usage, seconds=time.time() - t0)


# ---------------------------------------------------------------- fan-out

async def kickoff_for_each(crew: Crew, runner: Runner, inputs_list: list[dict], *,
                           max_task_seconds: float = 180.0) -> list[CrewOutput]:
    """One run per input (upstream kickoff_for_each; aggregation is the caller's)."""
    return [await kickoff(crew, runner, dict(inp or {}), max_task_seconds=max_task_seconds)
            for inp in (inputs_list or [])]
