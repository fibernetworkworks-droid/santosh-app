---
name: requesting-code-review
description: After a task, a feature or before done on a real change - get an independent review
when: review my change, before done, finished feature, before pull request
---
When: after each task of a plan, after a feature, before done on anything bigger than a few lines, and when stuck (a
fresh look).
How: the agent tool with the reviewer for the language (and security-reviewer when it touches input, auth, money, files,
SQL, shell or secrets). Its task stands alone: what was built and why, the requirement it must meet, which files changed
(it reads them), what to check. Ask in one reply for both when both apply.
Act on the findings: fix Critical at once, Important before done, note Minor ones. Check each finding against the code
first (receiving-code-review): a finding you can show is wrong, you leave and say why in risk.
Never skip it because "it is simple", and never call done with an Important finding open.
