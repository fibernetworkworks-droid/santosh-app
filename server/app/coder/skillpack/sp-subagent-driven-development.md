---
name: sp-subagent-driven-development
description: Use to run a plan via fresh implementer + reviewer per task
when_to_use: subagents, implement plan with agents, agent per task
---
Execute a plan by dispatching a FRESH implementer subagent per task, a task
review (spec compliance + code quality) after each, and one broad
whole-branch review at the end. Subagents never inherit your session's
context - you construct exactly what they need; this preserves your own
context for coordination. Use when tasks are mostly independent and a
subagent tool exists; tightly coupled tasks, the partner chose inline, or no
subagent tool -> executing-plans or manual.

RULINGS, NOT STALLS: decide conflicts yourself (spec is the binding
authority, the plan its argument); ledger "Ruling: <decision> - <why> -
<cost if wrong>"; keep going. Stop only for: irreversible/destructive operations; security-sensitive
actions; side effects outside the worktree norms say ask about first; a plan
so broken every path is a guess. Continuous execution - never "should I
continue?".

SETUP: isolated workspace (using-git-worktrees); ledger at
<workspace>/progress.md ("# SDD ledger - plan: <path>"); trust the ledger and
git log over your recollection after compaction; pre-flight conflict scan over the plan's Interfaces blocks.

MODEL SELECTION: the least powerful model that can handle each role.
Mechanical 1-2-file tasks with complete specs -> cheap tier; integration and
multi-file coordination -> standard; architecture/design and the FINAL
whole-branch review -> the most capable model. ALWAYS specify the model
explicitly - an omitted model inherits the session's. Turn count beats token price: the cheapest models take 2-3x the turns
on multi-step work. Complete code in the plan text = transcription +
testing -> cheapest tier.

DISPATCH (one task; NEVER parallel implementation subagents - conflicts):
record BASE (git rev-parse HEAD) before dispatching. task-brief PLAN_FILE N
extracts the task to a file - the brief is the single source of requirements;
exact values (numbers, magic strings, signatures, test cases) appear ONLY
there; never make a subagent read the whole plan. The dispatch carries: one
line where the task fits; the brief path ("read this first - your
requirements, exact values verbatim"); interfaces and decisions from earlier
tasks the brief cannot know; your resolution of ambiguities you noticed; the
report-file path (task-N-report.md) and the report contract (status, commits,
one-line test summary, concerns). Do NOT paste prior-task summaries or
session history - a real session's dispatch hit 42k chars of which 99% was
history. The no-subagents contract: the implementer never dispatches helpers
or a reviewer - review arrives from you, after the report.

REPORTS: DONE -> review-package PLAN_FILE BASE HEAD - never HEAD~1, it
silently drops all but the last commit of a multi-commit task -> dispatch the task reviewer with brief + report +
package paths plus Global Constraints copied verbatim (the reviewer's
attention lens). DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED -> follow the
handling-reports reference, EVERY time. Answer implementer questions fully
- never rush.

REVIEW GATE: never skip the task review; never accept a report missing
either verdict (spec AND quality); implementer self-review never replaces
it. Never pre-judge findings - "do not flag X", "at most Minor" is you
sparing yourself a loop; let the reviewer raise it and adjudicate.

FIX LOOP: triggers on spec-x, any Critical or Important finding, or a
confirmed gap. Read references/fix-loop.md before EVERY round - the round
cap, the breaker, and the ledger line live there; memory of it does not
survive compaction. Past the cap, rounds don't converge - adjudicate and
park with a ledgered ruling.

COMPLETE: ledger "Task N: complete (commits <b>..<h>, review clean)" (or
"<K> parked") in the same message as the bookkeeping; never advance with
open Critical/Important that are neither fixed nor parked. Then the final
whole-branch review (most capable model), one fix wave, delete the
workspace, finishing-a-development-branch.