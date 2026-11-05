"""HOOLA CREW (v0.514.0) - the crewAI feature surface, the role-based agent crew port.

The end-to-end read of github.com/crewAIInc/crewAI @ 027638ad (HEAD of main at clone
time, 2026-11-04, MIT (c) 2025 crewAI, Inc.) cloned as house code - ZERO upstream code
or imports (the port law that built aep/dhara/docs7/magic21). What lives here (every
module inert until awaited - no network, no threads on import, no config reads; the
runner seam keeps the provider OUT of the library entirely):

- core    : Process (sequential | hierarchical), TaskOutput, UsageMetrics (the honest
            requests-shaped ledger), CrewOutput
- agent   : Agent (role / goal / backstory / tool allowlist / max_iter) - IDENTITY, not
            machinery; execution rides the house child worker
- task    : Task (description / expected_output / agent ref / context from EARLIER tasks
            / async / guardrail) + {key} interpolation
- crew    : Crew + the laws (roles unique, roster membership, context-no-future-tasks,
            hierarchical manager has NO tools, caps 6 agents / 12 tasks) + from_spec()
- engine  : the executor over the injected RUNNER seam - sequential with context
            threading, async join-before-next-sync, guardrail retries, the hierarchical
            manager loop (DELEGATE / ASK / FINISH text protocol), kickoff_for_each

THE HOOLA SHAPE: a crew worker IS a house child worker (coder/delegate.py's bounded
_call_brain + _run_tool loop) framed by the agent's identity; the door is ONE tool
(coder/crew_run.py, the docs7/magic21 one-tool shape) gated by coder_crew (default OFF).
Money never moves inside a crew: the delegate deny set is structural. Upstream surfaces
consciously ABSENT (the honesty law): replay/fork/from_checkpoint, CrewPlanner,
memory/knowledge bridges, streaming, output_json/pydantic shaping - named in the story,
none pretend to exist.

MIT (c) 2025 crewAI, Inc. - the idea port; no code shipped, no attribution required,
given anyway: this header is the provenance.
"""
from . import (  # noqa: F401 - the package-export law (the v0.478 lesson, extended)
    agent,
    core,
    crew,
    engine,
    task,
)
from .agent import Agent, CrewSpecError
from .core import CrewOutput, Process, TaskOutput, UsageMetrics
from .crew import Crew
from .engine import Runner, RunnerResult, kickoff, kickoff_for_each, kickoff_hierarchical
from .task import Task

__all__ = [
    "Agent", "Crew", "CrewOutput", "CrewSpecError", "Process", "Runner", "RunnerResult",
    "Task", "TaskOutput", "UsageMetrics", "agent", "core", "crew", "engine", "task",
    "kickoff", "kickoff_for_each", "kickoff_hierarchical",
]
