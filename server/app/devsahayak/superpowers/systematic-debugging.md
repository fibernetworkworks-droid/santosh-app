---
name: systematic-debugging
description: Any bug, test failure, crash, build failure or unexpected behaviour - find the root cause before any fix
when: bug, error, exception, traceback, crash, fails, failing, broken, not working, regression, flaky, wrong result
---
THE IRON LAW: no fix without finding the root cause first. A fix for the symptom is a failure, even if the test goes green.
Use it most when it feels obvious, when you are in a hurry, or when one fix already did not work.

PHASE 1 - ROOT CAUSE (before ANY edit)
1. Read the whole error: every line of the trace, file paths, line numbers, codes. It often says the answer.
2. Reproduce it with bash, the same way every time. Cannot reproduce = gather more data; never guess.
3. Look at what changed: the diff, recent commits (git log -5 --stat in bash is read-only and fine), dependencies, config.
4. Several parts in a chain (CI -> build -> deploy, API -> service -> database)? Before fixing, print what goes in and
   comes out at each boundary in one run; that shows WHICH part breaks. Then look only there.
5. Trace the bad value backwards: where does it come from, who called this with it? Fix at the source, not where it
   shows up.

PHASE 2 - PATTERN
Find similar code in this repo that works; read it whole; list every difference, however small. Know what the broken
code depends on (settings, environment, order).

PHASE 3 - ONE HYPOTHESIS
Write it down in one sentence: "X is the cause because Y". Test it with the smallest change, one thing at a time. Wrong?
Form a new hypothesis - never pile a second fix on the first. Do not know? Say "I don't understand X" in your words to
her; do not pretend.

PHASE 4 - FIX
1. A failing test that reproduces it first (see test-driven-development). Run it: it must FAIL for the right reason.
2. One fix, at the root cause. No "while I'm here" changes.
3. Run the test and the suite: green, nothing else broken.
4. Fix did not work: count the attempts. Under 3: back to Phase 1 with what you learned.
   3 or more: STOP. Each fix showing a new problem somewhere else means the design is wrong, not the line. Do not try a
   4th fix: tell her what you found, what you tried and why it points at the design, and ask (done with one question).

RED FLAGS - stop and go back to Phase 1: "quick fix now, look later", "just try changing X", several changes at once,
"skip the test, I'll check by hand", "it's probably X", proposing a fix before tracing the data, "one more fix" after two
failed ones.
