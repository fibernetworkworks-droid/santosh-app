---
name: test-driven-development
description: Writing a feature, a bug fix or a behaviour change - the failing test comes first
when: add feature, implement, new function, fix bug, change behaviour, refactor
---
THE IRON LAW: no production code without a failing test first. If you watched no test fail, you do not know it tests the
right thing. Code written before its test: undo it (rewind or edit it away) and start from the test.
Exceptions only with her word: a throwaway prototype, generated code, config files.

RED - write ONE small test for one behaviour, with a clear name, using real code (mocks only where there is no other way).
VERIFY RED - run it with bash. It must FAIL, and fail because the feature is missing - not a typo or an import error.
  Passes already? You are testing behaviour that exists: fix the test. Errors? Fix the error until it fails properly.
GREEN - the simplest code that makes it pass. No extra features, no "improving" nearby code.
VERIFY GREEN - run it again, and the rest of the suite: all pass, output clean (no new warnings or errors).
REFACTOR - only while green: remove duplication, better names. Run again after.
Then the next behaviour: a new failing test.

A good test: one behaviour ("and" in its name = split it), its name says what should happen, it shows the API you want,
it tests the real thing. Hard to test = the design is too tangled; listen to the test.
Bug fix: the test reproduces the bug first; it must fail on the old code and pass on the fix (Hoola also proves this on
her CI).
RED FLAGS: code before the test, a test that passed at once, "I'll add tests after", "just this once", "tests after give
the same result" (they do not: tests after ask "what does this do", tests first ask "what should this do").
