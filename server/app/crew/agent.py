"""HOOLA CREW agent - the role persona (v0.514.0, the crewAI Agent feature surface).

Upstream (lib/crewai/src/crewai/agent/core.py + agents/agent_builder/base_agent.py):
an Agent is IDENTITY, not machinery - role, goal, backstory injected into the prompt
templates; plus knobs (tools, max_iter, allow_delegation, llm, cache, rpm...). The
EXECUTION loop lives in agents/agent_executor.py (a ReAct loop over the provider).

The Hoola shape (pinned deviations, the voice-box law):
- IDENTITY rides: role / goal / backstory / an optional tool ALLOWLIST / max_iter.
- The EXECUTION loop is NOT rebuilt here: a crew worker IS the house child worker
  (coder/delegate.py's bounded _call_brain + _run_tool loop) framed by this identity.
  One funnel, capture sees everything, no second ReAct implementation to maintain.
- allow_delegation has NO Hoola shape: workers are structurally denied delegate_task /
  confirm_send / haan_karo / pc_do (delegate.CHILD_DENIED - money and depth never move
  inside a crew). In hierarchical mode the MANAGER's delegation is the process itself
  (engine.py's DELEGATE move), never a tool the worker holds. The field is therefore
  absent on purpose; the tests pin the deny set.
- llm/cache/rpm/max_rpm are absent: the crew rides the house brain + its knobs
  (coder_delegate_timeout_s shaped caps); a crew is not a second rate limiter.

Inert library: a dataclass + validation, nothing executes.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class CrewSpecError(ValueError):
    """A crew/agent/task spec is invalid - the door turns this into an honest error."""


@dataclass
class Agent:
    """One crew member: identity the runner frames (upstream Agent, Hoola-trimmed)."""

    role: str
    goal: str
    backstory: str = ""
    tools: tuple[str, ...] = ()      # optional allowlist; empty = the default worker surface
    max_iter: int = 6                # upstream max_iter default 10; the house child budget is 6

    def validate(self) -> None:
        if not str(self.role or "").strip():
            raise CrewSpecError("agent needs a role.")
        if not str(self.goal or "").strip():
            raise CrewSpecError(f"agent '{self.role}' needs a goal.")
        self.role = str(self.role).strip()
        self.goal = str(self.goal).strip()
        self.backstory = str(self.backstory or "").strip()
        tools = tuple(str(t).strip() for t in (self.tools or ()) if str(t).strip())
        if len(set(tools)) != len(tools):
            raise CrewSpecError(f"agent '{self.role}' has duplicate tool names.")
        self.tools = tools
        try:
            self.max_iter = int(self.max_iter)
        except Exception:
            raise CrewSpecError(f"agent '{self.role}' max_iter must be an integer.")
        if not (1 <= self.max_iter <= 8):
            raise CrewSpecError(f"agent '{self.role}' max_iter must be 1..8 (got {self.max_iter}).")

    def framing(self) -> str:
        """The identity block the runner puts in the worker's system prompt."""
        parts = [f"ROLE: {self.role}", f"GOAL: {self.goal}"]
        if self.backstory:
            parts.append(f"BACKSTORY: {self.backstory}")
        return "\n".join(parts)

    @classmethod
    def from_spec(cls, spec) -> "Agent":
        if not isinstance(spec, dict):
            raise CrewSpecError("each agent must be an object with role and goal.")
        a = cls(
            role=str(spec.get("role") or ""),
            goal=str(spec.get("goal") or ""),
            backstory=str(spec.get("backstory") or ""),
            tools=tuple(spec.get("tools") or ()),
            max_iter=spec.get("max_iter", 6),
        )
        a.validate()
        return a
