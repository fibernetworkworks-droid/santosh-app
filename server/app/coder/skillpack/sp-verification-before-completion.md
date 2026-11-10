---
name: sp-verification-before-completion
description: Use before claiming done - run the proof, evidence first
when_to_use: is it done, verify, prove it works, check before done
---
THE IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.
If you haven't run the verification command IN THIS MESSAGE, you cannot
claim it passes. Evidence before claims, always. Violating the letter of
this rule is violating the spirit.

THE GATE FUNCTION (before claiming any status or expressing satisfaction):
1. IDENTIFY - what command proves this claim?
2. RUN - execute the FULL command (fresh, complete).
3. READ - full output, check the exit code, count the failures.
4. VERIFY - does the output confirm the claim? If NO: state the actual
   status with evidence. If YES: state the claim WITH the evidence.
5. ONLY THEN: make the claim.
Skip any step = lying, not verifying.

WHAT EACH CLAIM REQUIRES: "tests pass" -> the test command's output with 0
failures (never the previous run, never "should pass"). "Linter clean" ->
linter output with 0 errors (not a partial check). "Build succeeds" -> build
command exit 0 (a linter passing is not compilation). "Bug fixed" -> the
test of the ORIGINAL symptom now passes (code changed is not fixed).
"Regression test works" -> the red-green cycle verified: write -> run
(pass) -> revert the fix -> run (MUST FAIL) -> restore -> run (pass) - one
green run proves nothing. "Agent completed" -> the VCS diff shows the
changes (an agent reporting "success" is not success). "Requirements met" ->
a line-by-line checklist against the plan (tests passing is not requirements
met).

RED FLAGS - STOP: any wording implying success without having run
verification - "should", "probably", "seems to"; expressing satisfaction
before verification ("Great!", "Perfect!", "Done!"); about to commit, push,
or open a PR without verification; trusting agent success reports; relying
on partial verification; thinking "just this once"; tired and wanting the
work over.

RATIONALIZATIONS: "should work now" -> RUN the verification. "I'm
confident" -> confidence is not evidence. "Just this once" -> no exceptions.
"Linter passed" -> a linter is not a compiler. "Agent said success" ->
verify independently. "I'm tired" -> exhaustion is not an excuse. "Partial
check is enough" -> partial proves nothing. "Different words so the rule
doesn't apply" -> spirit over letter.

APPLY ALWAYS BEFORE: any success/completion claim, any expression of
satisfaction, any positive statement about work state; committing, PR
creation, task completion; moving to the next task; delegating to agents.
The rule reaches exact phrases, paraphrases, synonyms, and any implication
of completion or correctness.