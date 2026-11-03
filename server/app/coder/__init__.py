"""HOOLA CODER (v0.478.0) - persistent session memory for Santosh, the claude-mem architecture
ported into the house stack: capture -> spool -> observer (cheap brain) -> SQLite/FTS5 vault ->
three-layer search -> session-start primer. Fail-open at every joint; secrets never stored.
v0.478.0 HOOLA SELF-TEACH adds the skills store (SKILL.md files + skill_manage), the nudge
fork (the self-teaching loop between turns) and matched-skill primer injection.
v0.478.0 HOOLA SWARM adds delegate_task: bounded parallel child agents on the same funnel."""
from . import capture, dedup, delegate, inject, modes, nudge, observer, parser, prompts, redact, \
    search, skills_store, skills_tool, spool, store

# v0.478 FIX (caught by the swarm funnel-capture test): the agent funnel calls
# coder.tool_observed / coder.turn_prompt / coder.session_started / coder.session_ended /
# coder.save_memory DIRECTLY on the package - since v0.473 only the MODULES were imported here,
# so every funnel call raised AttributeError and was swallowed by its fail-open wrapper: capture
# was silently dead in production (no tool_uses, no prompts, no sessions) while every suite
# stayed green because the coder suites call the capture MODULE path directly. The boundary
# functions are re-exported here now; the module paths still work.
from .capture import save_memory, session_ended, session_started, tool_observed, turn_prompt

__all__ = ["capture", "dedup", "delegate", "inject", "modes", "nudge", "observer", "parser",
           "prompts", "redact", "search", "skills_store", "skills_tool", "spool", "store",
           "save_memory", "session_ended", "session_started", "tool_observed", "turn_prompt"]
