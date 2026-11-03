"""HOOLA CODER (v0.477.0) - persistent session memory for Santosh, the claude-mem architecture
ported into the house stack: capture -> spool -> observer (cheap brain) -> SQLite/FTS5 vault ->
three-layer search -> session-start primer. Fail-open at every joint; secrets never stored.
v0.477.0 HOOLA SELF-TEACH adds the skills store (SKILL.md files + skill_manage), the nudge
fork (the self-teaching loop between turns) and matched-skill primer injection."""
from . import capture, dedup, inject, modes, nudge, observer, parser, prompts, redact, search, \
    skills_store, skills_tool, spool, store

__all__ = ["capture", "dedup", "inject", "modes", "nudge", "observer", "parser", "prompts",
           "redact", "search", "skills_store", "skills_tool", "spool", "store"]
