---
name: sp-dispatching-parallel-agents
description: Use for 2+ independent problems - parallel agents, one each
when_to_use: parallel agents, many independent tasks, split the work, do these in parallel
---
Delegate to specialized agents with isolated context: they never inherit
your session's context or history - you construct exactly what they need.
When several unrelated failures exist (different test files, subsystems,
bugs), investigating them sequentially wastes time.

CORE RULE: dispatch ONE agent per independent problem domain - all dispatches
in the SAME response run in parallel; one per response is sequential.

USE WHEN: 3+ test files failing with different root causes; multiple
subsystems broken independently; each problem understandable without the
others' context; no shared state. DON'T when: failures are related (fixing
one might fix the others - investigate together first); you need full system
state; agents would interfere (same files, same resources); exploratory
debugging where you don't yet know what's broken.

PATTERN: 1) identify independent domains - group failures by what's broken;
2) create focused tasks: specific scope (one test file or subsystem), clear
goal (make these pass), constraints ("do NOT change other code"), expected
output (summary of what you found and fixed); 3) dispatch all in one
response; 4) review and integrate - read each summary, verify fixes don't
conflict, run the FULL test suite, spot check (agents can make systematic
errors).

PROMPT SHAPE - good agent prompts are: focused (one clear problem domain:
"fix agent-tool-abort.test.ts", never "fix all the tests" - an agent gets
lost); self-contained (paste the actual error messages and test names - "fix
the race condition" without location is nothing); specific about output.
Name the class of fix you expect: "replace arbitrary timeouts with
event-based waiting; do NOT just increase timeouts - find the real issue."

REAL SHAPE: 6 failures across 3 files -> agent 1 abort timing, agent 2 batch
completion, agent 3 race conditions; results independent, no conflicts, full
suite green after integration.