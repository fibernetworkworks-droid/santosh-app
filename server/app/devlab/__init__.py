"""v0.456 PRAYOGSHALA - the coding lab: Hoola runs HER declared checks on her repo's code, in a locked Docker box.

Why it exists (docs/CODING_HARNESS_PLAN.md, researched 2 Nov 2026): without a command that comes back pass or fail, a
coding agent only knows "looks done" and the owner is the test suite. Her CI was the only oracle Hoola had - minutes a
round, three rounds, and only what CI already covers.

The shape, taken from the products that do this well:
- ONE declared command, never a guessed one (Aider's --test-cmd, Devin's blueprint `test`, Jules's setup script);
- the SETUP step gets the network and is cached as a per-repo image snapshot (Codex's `universal` + cache);
- the CHECK step runs with NO network, non-root, no secrets, all capabilities dropped, CPU / memory / pids / time caps;
- the output is shaped FAILURE-FIRST: a failing run keeps its tail (the traceback is at the end) and always hands back
  a log file the model can grep. Claude Code's own contract gives failures the SMALLER window; our research called
  that backwards for debugging, and this module inverts it.

Nothing here talks to the model yet. `service.check()` is the whole public surface; the dev loop is wired to it in the
next step, once she has seen `python -m app.devlab check` pass on the VPS.
"""
from . import box, out, spec  # noqa: F401
