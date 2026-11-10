---
name: sp-executing-plans
description: Use to execute a plan inline, task by task, final review
when_to_use: execute the plan, follow the plan, run the plan step by step
---
Execute the plan YOURSELF, task by task, in this session: no implementer
subagent per task, no reviewer per task, ONE fresh-context review of the
whole branch at the end. The plan already did the thinking - execute it
exactly, prove each step with a test you watched fail and then pass, and
leave a record that survives your own forgetting. Narrate at most one short
line between tool calls. Continuous execution: never pause to ask "should I
continue?" - they chose inline to spend less.

RULINGS, NOT STALLS: conflicts, ambiguities, plan defects - decide them. The
spec is the binding authority, the plan is its argument, your judgment
settles what neither answers. Ledger every decision as
"Ruling: <what you decided> - <why> - <what it costs if wrong>". Deviating
from the plan without a ledgered ruling is a decision made in secret. Four
things stop you, and only these: an irreversible or destructive operation; a
security-sensitive action; a side effect outside this worktree that norms say
you ask about first (a merge, a push to a shared branch, a publish); a plan
so broken every path forward is a guess.

SETUP: isolated workspace (using-git-worktrees) - never on main/master
without consent. Conversation memory does not survive compaction: track
progress in a LEDGER file, not only in todos. Each plan owns a workspace
(sdd-workspace PLAN_FILE prints the git-ignored directory). A ledger whose
first line names your plan and carries "Task N: complete" rows means those
tasks are DONE - do not redo them; resume at the first task without one;
after compaction trust the ledger and git log over your own recollection.
Create it: "# SDD ledger - plan: <plan path>". Read the plan once (note
Global Constraints); read the named Spec too - conflicts inside the plan
resolve against it. REQUIRED SUB-SKILL: load test-driven-development BEFORE
Task 1 - it governs every step. PRE-FLIGHT: scan the plan's Interfaces blocks
for conflicts between tasks; one ledger row per shared interface; rule each
conflict with the spec as authority; tasks sharing nothing get no row.

TASK LOOP: task-start PLAN_FILE N prints the brief path and BASE. Read the
brief EVERY task - your memory is a summary; the brief has the exact values.
Work the steps in RED-GREEN order. Every command
step has an "Expected:" line - run it, read the output, compare. Matches ->
next step. Code wrong -> systematic-debugging; never patch the symptom to
make the output match. PLAN wrong (a step contradicts the spec, an interface
doesn't match, an impossible command) -> rule the smallest change that
satisfies the spec, ledger it, continue - the ruling is carried, not
remembered. Commit as the plan's commit steps say; BASE anchors the review
range, never HEAD~1.

COMPLETION CONTRACT (before the task's ledger line, with evidence in this
session): every test the brief names exists and ran; the final test run
passed - task-done runs the task's tests and only on green appends
"Task N: complete (commits <b>..<h>, tests: <cmd> -> <result>)"; every
Expected: line was compared against real output; every deviation has a
Ruling: line. Any item missing = not complete.

FINAL REVIEW: review-package PLAN_FILE MERGE_BASE HEAD; dispatch a FRESH
reviewer on the most capable model - the one fresh context the whole run
buys; do not skip it or replace it with your own read (without a subagent
tool: self-review and SAY so, the partner decides if that is enough).
Re-grade findings by EFFECT on a reasonable person using the software, not by
the spec's silence. Critical/Important -> ONE fix pass, each fix verified by
its own RED->GREEN test plus a green suite - a fix without a failing test is
not verified. Minor -> ledger as deferred; never in the fix pass. A finding
you decide not to fix is a ruling - ledger it with the cost if wrong.

FINISH: your final message carries "Rulings I made" (in order, with costs)
and "Deferred minors" - both exhaustive. Delete this plan's workspace, then
finishing-a-development-branch.