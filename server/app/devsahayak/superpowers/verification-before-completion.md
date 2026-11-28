---
name: verification-before-completion
description: Before saying anything is done, fixed, passing or working - run the proof now and read it
when: done, finished, fixed, passing, works, ready, complete, before done
---
THE IRON LAW: no claim of done / fixed / passing without FRESH proof from THIS round.
Before any claim:
1. IDENTIFY the command that proves it (the test, the build, the linter, the original symptom).
2. RUN it now, the whole thing, after your last edit.
3. READ all of the output: the exit code, how many failed.
4. Does the output say what you are about to claim? No: say the real state with the evidence. Yes: say it WITH the
   evidence (in done test_plan: the command and its result, e.g. "pytest -q: 34 passed").
| Claim | Needs | Not enough |
| Tests pass | the test run, 0 failures | an earlier run, "should pass" |
| Linter clean | the linter's output, 0 errors | a partial check |
| Build works | the build command, exit 0 | the linter passed |
| Bug fixed | the original symptom tested: gone | the code changed |
| Regression test works | it failed without the fix and passes with it | it passes once |
| An agent finished | show_diff shows the change, you checked it | the agent's report |
| Her request is met | her request re-read, every point checked | the tests pass |
RED FLAGS: "should", "probably", "seems to"; "Great, done!" before running anything; trusting an agent's report; a partial
check; any wording that suggests success you have not just seen. Nothing could run in the box? Say so plainly - that is
not "passing".
