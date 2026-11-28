---
name: subagent-driven-development
description: An approved plan with several independent tasks - a fresh agent per task, each reviewed twice
when: execute the plan with agents, many tasks, long plan, independent tasks
---
Why: each task gets a fresh agent with only what it needs; your own context stays free for coordinating.
FOR EACH TASK, in order (never two implementers at once on the same files):
1. DISPATCH one implementer with the agent tool (an editing agent; isolation=worktree when tasks can run side by side).
   Its task text stands alone: where the task fits (one line), the task's full text with exact values, the interfaces
   from earlier tasks it needs, your decision on anything ambiguous, and what to report: status DONE / DONE_WITH_CONCERNS
   / NEEDS_CONTEXT / BLOCKED, the files changed, the test command and its result. Never paste the whole conversation or
   earlier task reports.
2. HANDLE THE REPORT. NEEDS_CONTEXT: answer fully and send it back. BLOCKED: decide - more context, smaller task, or ask
   her. DONE: do not trust it - show_diff (or agent_worktree show) and read the change.
3. REVIEW IT TWICE: (a) spec - does it do exactly the task, nothing missing, nothing extra? (b) quality - the language
   reviewer agent on that diff. Both verdicts needed; a self-review by the implementer never replaces them.
4. FIX LOOP: send the open findings back (up to 3 rounds); still open -> a fresh implementer who owns it now. Minor
   findings: note them for the final review, do not loop on them.
5. Bring an isolated copy in with agent_worktree apply, then the next task.
AT THE END: one broad review of the whole change (the reviewer + security-reviewer when it touches input, auth, money,
files or secrets), the whole suite run fresh, then done.
Keep going between tasks without asking her; stop only when blocked or a decision is hers.
