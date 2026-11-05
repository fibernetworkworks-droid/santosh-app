"""HOOLA CREW core - Process, outputs, usage metrics (v0.514.0 HOOLA CREW, the crewAI port).

The crewAI FEATURE SURFACE (role-based agent crews) cloned into house code after the
end-to-end read of github.com/crewAIInc/crewAI @ 027638ad (HEAD of main at clone time,
2026-11-04; lib/crewai/src/crewai/ - Crew, Agent, Task, Process, the AgentExecutor ReAct
loop, Flows, the unified Memory, the event bus). ZERO upstream code or imports (the port
law that built aep/dhara/docs7/magic21): this package is an independent implementation of
the same ideas, shaped for the Hoola voice box.

This module: the vocabulary the rest of the package speaks.

- Process     : sequential | hierarchical (upstream process.py - the same two; upstream's
                consensual stays a TODO there and here)
- TaskOutput  : one task's result + attempt count + wall time (+ the capped view that
                threads earlier outputs into later prompts)
- UsageMetrics: the crew's cost ledger. Upstream counts tokens because it owns the LLM
                client; Hoola's crew rides the house brain funnel (agent.santosh._call_brain),
                which does not expose usage - so the HONEST ledger counts brain rounds
                (successful_requests) and tool calls, tokens stay 0 (pinned deviation,
                the voice-box law)
- CrewOutput  : the kickoff result (raw = the LAST task's output, the upstream shape)
                + to_dict() for the tool door

Inert library: dataclasses and one enum - no I/O, no threads, no config reads.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Process(str, enum.Enum):
    """How the crew works through its tasks (upstream process.py, verbatim idea)."""

    sequential = "sequential"
    hierarchical = "hierarchical"


@dataclass
class TaskOutput:
    """One task's result (upstream TaskOutput idea, trimmed to what a crew reports)."""

    task: str
    agent_role: str
    raw: str = ""
    ok: bool = False
    attempts: int = 0
    seconds: float = 0.0
    guardrail_feedback: str = ""

    def short(self, cap: int = 2000) -> str:
        """The context-threading view: earlier outputs ride later prompts, capped."""
        t = " ".join(str(self.raw or "").split())
        if len(t) <= cap:
            return t
        return t[: cap - 3].rstrip() + "..."


@dataclass
class UsageMetrics:
    """The cost ledger (upstream UsageMetrics idea; requests-shaped for the funnel)."""

    successful_requests: int = 0
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out

    def add(self, other: "UsageMetrics") -> None:
        self.successful_requests += int(getattr(other, "successful_requests", 0) or 0)
        self.tool_calls += int(getattr(other, "tool_calls", 0) or 0)
        self.tokens_in += int(getattr(other, "tokens_in", 0) or 0)
        self.tokens_out += int(getattr(other, "tokens_out", 0) or 0)

    def to_dict(self) -> dict:
        return {
            "successful_requests": self.successful_requests,
            "tool_calls": self.tool_calls,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "total_tokens": self.total_tokens,
        }


@dataclass
class CrewOutput:
    """The kickoff result (upstream CrewOutput idea: raw is the LAST task's output)."""

    crew: str
    process: str
    ok: bool
    raw: str
    outputs: list[TaskOutput] = field(default_factory=list)
    usage: UsageMetrics = field(default_factory=UsageMetrics)
    seconds: float = 0.0

    def to_dict(self, cap: int = 6000) -> dict:
        return {
            "crew": self.crew,
            "process": self.process,
            "ok": self.ok,
            "raw": (self.raw or "")[:cap],
            "outputs": [
                {
                    "task": o.task,
                    "agent": o.agent_role,
                    "ok": o.ok,
                    "text": (o.raw or "")[:cap],
                    "attempts": o.attempts,
                    "seconds": round(o.seconds, 1),
                    **({"guardrail_feedback": o.guardrail_feedback} if o.guardrail_feedback else {}),
                }
                for o in self.outputs
            ],
            "usage": self.usage.to_dict(),
            "seconds": round(self.seconds, 1),
        }
