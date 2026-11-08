---
name: sp-systematic-debugging
description: Use on any bug or test failure - root cause before any fix
---
THE IRON LAW: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.
If Phase 1 is not complete, you cannot propose fixes. Symptom fixes are
failure.

USE FOR ANY technical issue: test failures, production bugs, unexpected
behavior, performance problems, build failures, integration issues -
ESPECIALLY when under time pressure, when "just one quick fix" seems
obvious, when you've already tried multiple fixes, when you don't fully
understand the issue. Don't skip when the issue seems simple (simple bugs
have root causes too).

PHASE 1 - ROOT CAUSE INVESTIGATION (before ANY fix):
1. Read error messages completely - they often contain the exact solution;
   note line numbers, paths, codes; read the whole stack trace.
2. Reproduce consistently - exact steps, every time? Not reproducible ->
   gather more data, don't guess.
3. Check recent changes - git diff, recent commits, new dependencies,
   config, environment differences.
4. Multi-component system (CI -> build -> sign, API -> service -> db)?
   BEFORE proposing fixes, add instrumentation at EACH component boundary:
   log what enters and exits each layer, verify config propagation. One run
   shows WHERE it breaks; then investigate that component.
5. Trace data flow - where does the bad value originate? What called it
   with that value? Trace up to the source; fix at source, not symptom.

PHASE 2 - PATTERN ANALYSIS: find similar WORKING code in the same codebase;
read reference implementations COMPLETELY (don't skim - every line); list
EVERY difference between working and broken, however small - never assume
"that can't matter"; understand the dependencies and assumptions.

PHASE 3 - HYPOTHESIS AND TESTING: form ONE hypothesis - state clearly "I
think X is the root cause because Y", write it down, be specific. Test
minimally: the SMALLEST possible change, one variable at a time. Worked ->
Phase 4. Didn't -> form a NEW hypothesis; DON'T stack fixes. When you don't
know: say "I don't understand X" - don't pretend, ask or research.

PHASE 4 - IMPLEMENTATION: create a failing test first (simplest
reproduction; test-driven-development); implement ONE fix for the root
cause - no "while I'm here" improvements, no bundled refactoring; verify
(test green, suite green, issue resolved - verification-before-completion
before claiming success).

IF THE FIX DOESN'T WORK: STOP. Count the fixes tried. Under 3 -> back to
Phase 1 with the new information. 3 OR MORE -> STOP and question the
ARCHITECTURE: each fix revealing new shared state or new symptoms
elsewhere, or fixes needing "massive refactoring", is not a failed
hypothesis - it is a wrong architecture. Discuss with the partner before
fix #4.

RED FLAGS (all mean STOP, return to Phase 1): "quick fix for now,
investigate later"; "just try changing X and see"; "skip the test, I'll
manually verify"; "probably X, let me fix that"; proposing solutions before
tracing data flow; "one more fix attempt" after 2+ failures; each fix
reveals a new problem somewhere else.

THE PARTNER'S SIGNALS: "Is that not happening?" (you assumed); "Will it
show us...?" (gather evidence); "Stop guessing"; "Ultra-think this"; "We're
stuck?" - all mean STOP, back to Phase 1.

RATIONALIZATIONS: "issue is simple, don't need process" - simple issues have
root causes too, and the process is fast for simple bugs. "Emergency" -
systematic is FASTER than guess-and-check thrashing. "Multiple fixes at
once" - you can't isolate what worked; you cause new bugs. "I see the
problem, let me fix it" - seeing symptoms is not understanding the root
cause.

NO ROOT CAUSE FOUND? 95% of "no root cause" cases are incomplete
investigation. Truly environmental/external: document what you
investigated, add handling (retry, timeout, message) and monitoring.

SUPPORTING TECHNIQUES (in the archive): root-cause-tracing (backward
through the call stack), defense-in-depth (validate at layers AFTER the
root cause is fixed), condition-based-waiting (poll conditions, not
arbitrary timeouts).
