---
name: sp-requesting-code-review
description: Use after a task or feature - dispatch a reviewer subagent
---
Dispatch a code reviewer subagent to catch issues before they cascade. The
reviewer gets precisely crafted context for evaluation - never your session's
history.

CORE PRINCIPLE: review early, review often.

MANDATORY: after each task in subagent-driven development; after completing a
major feature; before merge to main. OPTIONAL BUT VALUABLE: when stuck (fresh
perspective), before refactoring (baseline check), after fixing a complex
bug.

HOW: 1) get the SHAs - BASE (git merge-base origin/main HEAD, or the BASE you
recorded before the task's dispatch; never HEAD~1 for multi-commit work) and
HEAD (git rev-parse HEAD). 2) Dispatch a general-purpose subagent with the
reviewer template, filling: DESCRIPTION (brief summary of what you built),
PLAN_OR_REQUIREMENTS (what it should do - the plan/spec path), BASE_SHA,
HEAD_SHA. The diff and the evaluation live in the reviewer's context; only
the findings come back to you. 3) Act on the feedback: fix Critical issues
immediately, fix Important issues before proceeding, note Minor issues for
later - and push back if the reviewer is wrong, with reasoning and the
code/tests that prove it, or request clarification.

NEVER: skip review because "it's simple"; ignore Critical issues; proceed
with unfixed Important issues; argue with valid technical feedback.

RATIONALIZATIONS: "I'll just review the diff myself instead of dispatching a
reviewer" - you're the coordinator; reviewing the diff inline burns the
context window you need to keep driving the work, and same-author review has
the same blind spots. Dispatch the reviewer: the diff and the evaluation
live in its context, only the findings come back. "The reviewer needs my
whole session history to understand the change" - hand precisely crafted
context, never history; that keeps the reviewer on the work product, not
your thought process.