---
name: sp-writing-plans
description: Use with an approved spec - exact bite-sized task plan
---
Write implementation plans for an engineer who has NOT seen this codebase or
the spec. Assume they write idiomatic code once they know the exact interface
and the exact test, and will choose reasonably wherever the plan leaves one
open. What they cannot know is what you decided: which files, which names and
signatures, which values from the spec, which tests prove each task. Document
those. DRY. YAGNI. TDD. Frequent commits.

SCOPE: the spec covers several independent subsystems? Suggest separate plans,
one per subsystem - each must produce working, testable software on its own.

FILE STRUCTURE: before tasks, map which files get created/modified and each
one's responsibility. Clear boundaries, focused files, files that change
together live together; in existing codebases follow established patterns.

TASK RIGHT-SIZING: a task is the smallest unit that carries its own test
cycle and is worth a fresh reviewer's gate. Fold setup/config/scaffolding into
the task whose deliverable needs them; split only where a reviewer could
reject one task while approving its neighbor. Each task ends in an
independently testable deliverable.

STEP GRANULARITY: each step is ONE action with a checkable result - write the
failing test / run it to make sure it fails / implement the minimal code /
run the tests and make sure they pass / commit.

HEADER (every plan): title; a line for agentic workers - REQUIRED SUB-SKILL:
subagent-driven-development (recommended) or executing-plans, steps use
checkbox syntax; Goal (one sentence); Architecture (2-3 sentences); Tech
Stack; Spec path (the plan argues from the spec; executors read both); Global
Constraints (project-wide requirements one line each, exact values copied
verbatim from the spec - every task implicitly includes this section); Review
Focus (the five input classes or failure modes the spec implies but no task's
tests exercise - the ones most likely to bite a person using the software,
most likely first; give each line a test in the owning task).

TASK STRUCTURE: Files (Create/Modify with exact paths; Test path); Interfaces
(Consumes/Produces with exact signatures - a task's implementer sees only
their own task, this block is how they learn the names neighboring tasks
use); then checkbox steps: the failing test as code with the spec's exact
values; the run command with its Expected: output; the implementation with
the exact signature and file - a body appears only for an algorithm the
signature and tests do not determine; the commit.

WHAT A STEP CONTAINS: a step is done when the implementer can write exactly
one reasonable thing from it - unambiguous, not complete. A line that decides
nothing ("TBD", "handle edge cases", "add appropriate validation", "write
tests for the above") is a gap; a function body the signature and tests
already determine is a transcript. A plan longer than the code it describes
has written the code instead.

SELF-REVIEW (you, fresh eyes, after the complete plan): 1) spec coverage -
every requirement has a task; 2) step scan - each step is exactly one
reasonable thing, no gaps, no transcripts; 3) type consistency - names and
signatures match across tasks (clearLayers vs clearFullLayers is a bug);
4) review focus - every implied failure mode has a test; 5) proportion - a
plan several times longer than the spec is a transcript of the program, not a
plan. Fix inline.

HANDOFF: link the plan for review. No execution method supplied? Ask them to
choose: subagent-driven (fresh implementer + reviewer per task; most
thorough) or native/inline (you implement every task, one fresh whole-branch
review at the end; cheapest) - with a one-sentence recommendation from the
plan. Wait for their review before implementing.