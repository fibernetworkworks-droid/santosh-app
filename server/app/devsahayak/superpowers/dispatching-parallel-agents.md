---
name: dispatching-parallel-agents
description: Two or more independent problems (separate failing areas, separate files) - one agent each, at the same time
when: several failures, independent tasks, in parallel, at the same time, many files
---
Use when the problems are truly independent: different areas, no shared state, fixing one will not fix another.
Not when the failures may share a cause (look at them together first), or when the work needs the whole picture.
1. Group them by area. 2. One agent per area, each task standing alone: one clear area, everything it needs (the error
text, the test names, the files), constraints ("change only the tests", "do not touch the API"), and what to return
(the cause found and what was changed). 3. Ask for all of them in ONE reply (editing agents with isolation=worktree) so
they run at once. 4. When they report: read each change (agent_worktree show), check they do not conflict, bring the
good ones in (apply), run the whole suite fresh.
Bad task: "fix all the tests". Good task: "make tests/test_abort.py pass; the error is ...; do not change src/".
