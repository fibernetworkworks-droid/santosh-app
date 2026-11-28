---
name: using-worktrees
description: Work that should not touch the main copy until checked - an agent in its own copy
when: isolate, separate copy, try an approach, side by side, parallel edits
---
In Hoola Code an editing agent with isolation=worktree works in its own copy of the working copy: its edits stay there.
- Use it for two or more changes that touch different files at the same time, or to try a risky approach without
  touching the main copy.
- When it reports: agent_worktree show (its diff) -> read it -> apply (brings it in; a conflict is named - settle it) or
  discard. Never apply a copy you have not read.
- Run the suite in the main copy after bringing copies in.
- Never use bash git worktree / git commit yourself: Hoola records the changes.
