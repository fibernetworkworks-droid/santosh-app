"""HOOLA CREW crew - the team and its laws (v0.514.0, the crewAI Crew feature surface).

Upstream (lib/crewai/src/crewai/crew.py, 2607 lines): Crew is a pydantic model over
agents + tasks + a Process, with validators (validate_tasks, validate_first_task,
validate_context_no_future_tasks, check_manager_llm...), kickoff / kickoff_for_each,
sequential and hierarchical runs (the manager agent + DelegateWork/AskQuestion tools),
replay from stored outputs, planning, usage metrics, memory/knowledge, checkpoints.

The Hoola shape (pinned deviations, the voice-box law):
- VALIDATION LAWS KEPT: roles unique; every task names an agent in the roster (empty =
  the first agent, upstream's default shape); context refs resolve to EARLIER tasks
  only; hierarchical REQUIRES a manager and the manager carries NO tools (upstream's
  "Manager agent should not have tools" invariant, raised the same way).
- CAPS (a voice box is not a cluster): agents <= 6, tasks <= 12, and the door passes
  its own knobs; a kickoff runs under one wall clock.
- ABSENT, named honestly: replay/fork/from_checkpoint (needs the task-output storage
  handler - the next lane), planning (CrewPlanner - next lane), memory/knowledge
  (upstream's unified Memory - the house has yaad + the vault; the bridge is its own
  story), streaming, process events. ZERO of these pretend to exist.
- from_spec(): the door's dict shape, validated into the dataclasses - the tool call
  carries the whole crew; nothing is stored server-side in v0.514 (stateless crew,
  the docs7/magic21 shape), so there is no crew to leak and nothing to replay YET.

Inert library: dataclasses + validation + spec parsing, nothing executes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .agent import Agent, CrewSpecError
from .core import Process
from .task import Task

MAX_AGENTS = 6
MAX_TASKS = 12


@dataclass
class Crew:
    """A named team working a task list under one process (upstream Crew, Hoola-trimmed)."""

    name: str
    agents: list[Agent] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    process: Process = Process.sequential
    manager: Agent | None = None

    # ------------------------------------------------------------------ laws
    def validate(self) -> None:
        if not str(self.name or "").strip():
            raise CrewSpecError("crew needs a name.")
        self.name = str(self.name).strip()
        if not self.agents:
            raise CrewSpecError("crew needs at least one agent.")
        if len(self.agents) > MAX_AGENTS:
            raise CrewSpecError(f"too many agents: {len(self.agents)} (max {MAX_AGENTS}).")
        roles: list[str] = []
        for a in self.agents:
            a.validate()
            if a.role in roles:
                raise CrewSpecError(f"duplicate agent role: '{a.role}'.")
            roles.append(a.role)
        if not self.tasks:
            raise CrewSpecError("crew needs at least one task.")
        if len(self.tasks) > MAX_TASKS:
            raise CrewSpecError(f"too many tasks: {len(self.tasks)} (max {MAX_TASKS}).")
        seen: dict[str, int] = {}
        for i, t in enumerate(self.tasks):
            t.validate()
            t.name = t.name or f"task-{i + 1}"
            if t.name in seen:
                raise CrewSpecError(f"duplicate task name: '{t.name}'.")
            seen[t.name] = i
            if t.agent and t.agent not in roles:
                raise CrewSpecError(f"task '{t.name}' names agent '{t.agent}', "
                                    f"which is not in the crew roster.")
            for c in t.context:
                if c not in seen:
                    raise CrewSpecError(
                        f"task '{t.name}' context ref '{c}' is not an EARLIER task "
                        f"(context may only reference tasks before it).")
        self.process = Process(self.process) if not isinstance(self.process, Process) else self.process
        if self.process is Process.hierarchical:
            if self.manager is None:
                raise CrewSpecError("hierarchical crew needs a manager.")
            self.manager.validate()
            if self.manager.tools:
                raise CrewSpecError("the manager must not carry tools "
                                    "(the manager delegates; workers work).")

    @property
    def roles(self) -> list[str]:
        return [a.role for a in self.agents]

    def agent_for(self, task: Task) -> Agent:
        """The task's agent (upstream's default-agent shape: empty = the first)."""
        if task.agent:
            for a in self.agents:
                if a.role == task.agent:
                    return a
        return self.agents[0]

    # ------------------------------------------------------------------ the door shape
    @classmethod
    def from_spec(cls, spec) -> "Crew":
        """Validate a tool-call dict into a Crew (raises CrewSpecError, honest errors)."""
        if not isinstance(spec, dict):
            raise CrewSpecError("crew must be an object: {name, process, agents[], tasks[], manager?}.")
        try:
            process = Process(str(spec.get("process") or "sequential"))
        except ValueError:
            raise CrewSpecError(f"unknown process '{spec.get('process')}' "
                                f"(sequential or hierarchical).")
        agents_raw = spec.get("agents")
        if not isinstance(agents_raw, list) or not agents_raw:
            raise CrewSpecError("crew.agents must be a non-empty array.")
        agents = [Agent.from_spec(a) for a in agents_raw]
        tasks_raw = spec.get("tasks")
        if not isinstance(tasks_raw, list) or not tasks_raw:
            raise CrewSpecError("crew.tasks must be a non-empty array.")
        tasks: list[Task] = []
        for t in tasks_raw:
            if not isinstance(t, dict):
                raise CrewSpecError("each task must be an object.")
            tasks.append(Task(
                description=str(t.get("description") or ""),
                expected_output=str(t.get("expected_output") or ""),
                agent=str(t.get("agent") or ""),
                context=tuple(t.get("context") or ()),
                name=str(t.get("name") or ""),
                async_execution=bool(t.get("async_execution") or False),
            ))
        mgr_spec = spec.get("manager")
        manager = None
        if mgr_spec is not None:
            manager = Agent.from_spec(mgr_spec)
        c = cls(name=str(spec.get("name") or ""), agents=agents, tasks=tasks,
                process=process, manager=manager)
        c.validate()
        return c
