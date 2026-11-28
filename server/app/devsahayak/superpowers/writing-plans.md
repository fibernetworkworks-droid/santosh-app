---
name: writing-plans
description: A multi-step change with requirements known - write the plan before touching code
when: plan, multi-step, several files, big change, migration, refactor across, implement the spec
---
Write the plan for a reader with no context of this conversation: an eager junior engineer who follows it to the letter.
HEADER: Goal (one sentence), Approach (2-3 sentences), Stack, Constraints that hold for every task (style, no new
dependency, compatibility).
FILES: list the files to create or change and what each is responsible for, before the tasks.
TASKS - each task is one reviewable piece (one component / one behaviour), with:
- Files (exact paths), Interfaces (function names, signatures, data shapes it creates or uses).
- Steps, each ONE action with a checkable result, a few minutes each:
  1. write the failing test (the exact case), 2. run it -> check: it fails because X is missing,
  3. write the code, 4. run it -> check: it passes, 5. run the suite -> check: all green.
- No step that says "handle errors appropriately" or "add validation" without saying which: name the case.
SELF-REVIEW before showing it: (1) every point of her request maps to a task - list gaps; (2) every step lets the
implementer do exactly one clear thing; (3) names and types match across tasks (clearLayers in task 3 = clearLayers in
task 7).
Show the plan to her and wait for her yes before any edit. Then todo_write one item per task, each with its check.
