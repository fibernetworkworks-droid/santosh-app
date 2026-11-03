"""HOOLA CODER (v0.473.0) - persistent session memory for Santosh, the claude-mem architecture
ported into the house stack: capture -> spool -> observer (cheap brain) -> SQLite/FTS5 vault ->
three-layer search -> session-start primer. Fail-open at every joint; secrets never stored."""
from . import capture, dedup, inject, modes, observer, parser, prompts, redact, search, spool, store

__all__ = ["capture", "dedup", "inject", "modes", "observer", "parser", "prompts", "redact",
           "search", "spool", "store"]
