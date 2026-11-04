---
name: sp-receiving-code-review
description: Use on review feedback - verify first, push back with proof
---
Code review requires technical evaluation, not emotional performance. Verify
before implementing. Ask before assuming. Technical correctness over social
comfort.

THE RESPONSE PATTERN: 1) READ the complete feedback without reacting;
2) UNDERSTAND - restate the requirement in your own words (or ask);
3) VERIFY - check against codebase reality; 4) EVALUATE - technically sound
for THIS codebase? 5) RESPOND - technical acknowledgment or reasoned
pushback; 6) IMPLEMENT - one item at a time, test each.

FORBIDDEN RESPONSES - NEVER: "You're absolutely right!" (explicit
violation), "Great point!" / "Excellent feedback!" (performative), "Let me
implement that now" (before verification). No gratitude either - no "Thanks
for catching that!"; the code itself shows you heard the feedback. If you
catch yourself about to write "Thanks" - DELETE it and state the fix
instead. Acknowledging correct feedback: "Fixed. <brief description of what
changed>." or "Good catch - <specific issue>. Fixed in <location>." Pushed
back and were wrong? "You were right - I checked X and it does Y.
Implementing now." State the correction factually and move on - no long
apology, no defending why you pushed back, no over-explaining.

UNCLEAR FEEDBACK: if ANY item is unclear, STOP - do not implement anything
yet - and ask. Items may be related; partial understanding = wrong
implementation. ("I understand items 1,2,3,6. Need clarification on 4 and 5
before proceeding.")

FROM THE HUMAN PARTNER: trusted - implement after understanding; still ask
if scope is unclear; no performative agreement; skip to action or technical
acknowledgment. FROM EXTERNAL REVIEWERS, check before implementing:
technically correct for THIS codebase? breaks existing functionality? is
there a reason for the current implementation? works on all
platforms/versions? does the reviewer have full context? Seems wrong -> push
back with technical reasoning. Can't easily verify -> say so: "I can't
verify this without X. Should I investigate/ask/proceed?" Conflicts with the
partner's prior decisions -> stop and discuss with them first.

YAGNI CHECK: a reviewer suggests "implementing properly"? grep the codebase
for actual usage. Unused -> "This endpoint isn't called. Remove it (YAGNI)?"
Used -> then implement properly.

IMPLEMENTATION ORDER for multi-item feedback: clarify anything unclear
FIRST; then blocking issues (breaks, security), then simple fixes (typos,
imports), then complex fixes (refactoring, logic); test each fix
individually; verify no regressions.

PUSH BACK WHEN: the suggestion breaks existing functionality; the reviewer
lacks full context; it violates YAGNI; it's technically incorrect for this
stack; legacy/compatibility reasons exist; it conflicts with the partner's
architectural decisions. How: technical reasoning, not defensiveness; ask
specific questions; reference working tests/code; involve the partner when
architectural. If you're uncomfortable pushing back out loud: name that
tension, then tell the partner the issue you've seen.