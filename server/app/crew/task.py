"""HOOLA CREW task - the unit of work (v0.514.0, the crewAI Task feature surface).

Upstream (lib/crewai/src/crewai/task.py, 1634 lines): a Task carries description +
expected_output + agent + context (EARLIER task outputs fed in) + async_execution +
output_json/output_pydantic + human_input + guardrail(s) + output_file + callbacks.
Guarantees upstream states and this port keeps: context may only reference EARLIER
tasks (validate_context_no_future_tasks); exactly one structured-output model; a
guardrail returns (bool, Any) and retries up to guardrail_max_retries, then raises.

The Hoola shape (pinned deviations, the voice-box law):
- description / expected_output / agent (role ref) / context / guardrail / name ride.
- {key} interpolation from the kickoff inputs (upstream interpolates via its i18n
  utils); UNKNOWN {tokens} stay verbatim - an honest template never silently eats text.
- async_execution rides: independent tasks run concurrently (bounded) and JOIN before
  the next sync task (upstream _process_async_tasks), inside the one door turn.
- output_json / output_pydantic / output_file / human_input / callbacks are ABSENT:
  output shaping is the worker's expected_output prompt; files go through the house
  doors (sheet_*, create, ...); an approval loop needs a parked turn (the dhara
  approval shape) - a crew is one turn. Named in the story as the next lane.
- guardrail is a CALLABLE in the library (tests, aep interop). The tool door carries
  expected_output only - tool args cannot carry functions, and the door does not
  pretend otherwise.

Inert library: a dataclass + validation + interpolation, nothing executes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .agent import CrewSpecError

Guardrail = Callable[[str], tuple[bool, Any]]


def interpolate(text: str, inputs: dict | None) -> str:
    """{key} interpolation from kickoff inputs (upstream's input interpolation idea).

    Known keys are replaced; unknown {tokens} stay verbatim (honest templates);
    braces that name nothing stay braces."""
    if not inputs:
        return text
    out = str(text or "")
    for k, v in (inputs or {}).items():
        if not str(k).strip():
            continue
        out = out.replace("{" + str(k) + "}", str(v))
    return out


@dataclass
class Task:
    """One unit of crew work (upstream Task, Hoola-trimmed)."""

    description: str
    expected_output: str = ""
    agent: str = ""                       # a role in the crew roster; "" = the first agent
    context: tuple[str, ...] = ()         # names of EARLIER tasks whose output rides in
    name: str = ""                        # defaults to task-N at crew validation
    async_execution: bool = False
    guardrail: Guardrail | None = None
    max_guardrail_retries: int = 2

    def validate(self) -> None:
        if not str(self.description or "").strip():
            raise CrewSpecError("task needs a description.")
        self.description = str(self.description).strip()
        self.expected_output = str(self.expected_output or "").strip()
        self.agent = str(self.agent or "").strip()
        self.name = str(self.name or "").strip()
        self.context = tuple(str(c).strip() for c in (self.context or ()) if str(c).strip())
        if self.guardrail is not None and not callable(self.guardrail):
            raise CrewSpecError("task guardrail must be a callable returning (bool, feedback).")
        try:
            self.max_guardrail_retries = int(self.max_guardrail_retries)
        except Exception:
            raise CrewSpecError("task max_guardrail_retries must be an integer.")
        if not (0 <= self.max_guardrail_retries <= 3):
            raise CrewSpecError("task max_guardrail_retries must be 0..3.")
        if self.async_execution and self.context:
            raise CrewSpecError(
                "async task with context is refused: it would read outputs that are not "
                "guaranteed to exist yet. Run it sync, or make it context-free.")

    def prompt_for(self, context_block: str) -> str:
        """The worker prompt: the task, what done looks like, and the threaded context."""
        parts = [f"TASK: {self.description}"]
        if context_block:
            parts.append(f"CONTEXT (earlier crew outputs you build on):\n{context_block}")
        if self.expected_output:
            parts.append(f"EXPECTED OUTPUT: {self.expected_output}")
        parts.append("Do the task with the tools you have and finish with the final "
                     "result as your report. No greetings, no questions back.")
        return "\n\n".join(parts)
