"""HOOLA CODER (v0.485.0) - persistent session memory for Santosh, the claude-mem architecture
ported into the house stack: capture -> spool -> observer (cheap brain) -> SQLite/FTS5 vault ->
three-layer search -> session-start primer. Fail-open at every joint; secrets never stored.
v0.477 HOOLA SELF-TEACH adds the skills store (SKILL.md files + skill_manage), the nudge
fork (the self-teaching loop between turns) and matched-skill primer injection.
v0.478 HOOLA SWARM adds delegate_task: bounded parallel child agents on the same funnel.
v0.480 HOOLA CURATOR adds the weekly consolidation: the Tier-1 scan finally wired, one
cheap-brain arbitration of the pending pairs (soft, revivable merges), recurring memories
promoted to skills through the same funnel.
v0.484 HOOLA SKILL DESK adds the skills platform: the usage telemetry, the owner's park flag,
the seed library, import/export (skill_packs) and the anonymised share shelf with the owner's
tap as the only gate out of a tenant.
v0.484 HOOLA SAPNE adds the NIGHTLY curator: the window's raw observations distilled into
curated memory rows (light 26h + deep 7d rewrite with mandatory preimages), OpenClaw's
dreaming sweep ported - the vault that captures starts to COMPOUND. Beside, never instead:
the v0.480 curator merges near-duplicates, SAPNE distills time windows.v0.501 HOOLA CONTEXT7 adds docs7: the upstash/context7 port - resolve a library to its
Context7 ID, pull up-to-date docs into the turn, land every fetch in the vault (the vault
IS the cache); queries redacted before egress.
"""
from . import capture, curator, dedup, delegate, docs7, dreams, inject, modes, nudge, observer, \
    parser, prompts, redact, search, skill_packs, skills_store, skills_tool, spool, store

# v0.478 FIX (caught by the swarm funnel-capture test): the agent funnel calls
# coder.tool_observed / coder.turn_prompt / coder.session_started / coder.session_ended /
# coder.save_memory DIRECTLY on the package - since v0.473 only the MODULES were imported here,
# so every funnel call raised AttributeError and was swallowed by its fail-open wrapper: capture
# was silently dead in production (no tool_uses, no prompts, no sessions) while every suite
# stayed green because the coder suites call the capture MODULE path directly. The boundary
# functions are re-exported here now; the module paths still work. v0.479: the worker calls
# coder.curator.tick on the package path too - curator rides the import list above.
from .capture import save_memory, session_ended, session_started, tool_observed, turn_prompt

__all__ = ["capture", "curator", "dedup", "delegate", "docs7", "dreams", "inject", "modes",
           "nudge", "observer", "parser", "prompts", "redact", "search", "skill_packs",
           "skills_store", "skills_tool", "spool", "store", "save_memory", "session_ended",
           "session_started", "tool_observed", "turn_prompt"]
