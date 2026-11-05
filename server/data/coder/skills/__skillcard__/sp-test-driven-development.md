---
name: sp-test-driven-development
description: Use when implementing anything - failing test first, always
---
THE IRON LAW: NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.
Wrote code before the test? DELETE it - don't keep it as "reference", don't
"adapt" it while writing tests, don't look at it. Delete means delete;
implement fresh from tests. Violating the letter of the rules is violating
the spirit.

USE ALWAYS for: new features, bug fixes, refactoring, behavior changes.
Exceptions need the human partner: throwaway prototypes, generated code,
configuration files. Thinking "skip TDD just this once"? That's
rationalization.

RED - write ONE minimal failing test: one behavior, clear name, real code
(no mocks unless unavoidable). It tests real behavior, not mocks - a test
named "retries failed operations 3 times" counting real attempts beats
"retry works" over a mock.

VERIFY RED - MANDATORY, never skip: run the test; it must FAIL (not error)
with the expected message, because the feature is missing. Passes? You're
testing existing behavior - fix the test. Errors? Fix and re-run until it
fails correctly.

GREEN - write the SIMPLEST code to pass: no features beyond the test, no
refactoring other code, no "improvements" (YAGNI).

VERIFY GREEN - MANDATORY: the test passes, OTHER tests still pass, output
pristine (no errors, warnings). "Other tests" means the PROJECT'S suite, not
just your file: run the repo's own command (bare pytest / npm test / cargo
test) even when your task named only one test file - a green run of the test
you wrote is not a green suite. Any failure that run shows - including one
you didn't cause - goes in your report by name; a red test you watched
scroll past and didn't mention is a report falsified by omission. Test
fails? Fix the CODE, not the test.

REFACTOR - after green only: remove duplication, improve names, extract
helpers; keep tests green; add no behavior. Then the next failing test for
the next feature.

BUG FOUND? Write the failing test reproducing it first; the test proves the
fix and prevents regression. Never fix bugs without a test.

GOOD TESTS: minimal (an "and" in the name means split it), clear (the name
describes behavior, not test1), shows intent (demonstrates the desired API).
Before writing or changing any test: name the production change that would
make it fail - before writing it; assert real behavior, never mock behavior;
keep test-only code in test utilities, out of production classes;
understand a dependency's side effects before mocking it.

RATIONALIZATIONS: "too simple to test" - simple code breaks; the test takes
30 seconds. "I'll test after" - tests written after pass immediately, which
proves nothing; they test what you remembered, not what you'd have
discovered. "Already manually tested" - ad-hoc has no record and no re-run.
"Deleting X hours is wasteful" - sunk cost; keeping code you can't trust is
the waste. "Keep as reference" - you'll adapt it; that's testing after.
"TDD will slow me down" - TDD catches bugs before commit and lets you
refactor without fear; shortcuts mean debugging in production. "Test hard =
design unclear" - hard to test is hard to use; listen to the test.

RED FLAGS (STOP - delete code, start over): code before test; test after
implementation; test passes immediately; can't explain why the test failed;
tests added "later"; "just this once"; "spirit not ritual"; "this is
different because...".

WHEN STUCK: write the wished-for API, assertion first, ask the partner; a
test too complicated means the design is too complicated - simplify the
interface; must mock everything = too coupled, use dependency injection;
huge setup = extract helpers.

CHECKLIST before "done": every new function has a test; watched each fail
for the expected reason; minimal code per test; all tests pass; output
pristine; real code; edge cases and errors covered. Can't check all boxes?
You skipped TDD. Start over.
