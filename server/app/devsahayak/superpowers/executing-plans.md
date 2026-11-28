---
name: executing-plans
description: She approved a plan - carry it out task by task yourself
when: execute the plan, go ahead with the plan, implement the plan, approved plan
---
The plan did the thinking: carry it out exactly. todo_write one item per task.
For each task: mark it in_progress; do its steps in order with test-driven-development (failing test first); run each
step's check; when every check of the task is green, mark it completed - never earlier (verification-before-completion).
Keep going without asking "should I continue?". Stop only for: a step that cannot be done as written, a check that keeps
failing after systematic-debugging, a plan that contradicts her request or the code, or a need for her decision. Then ask
ONE clear question.
A small conflict or gap you can decide safely: decide, follow her request as the binding text, and say what you decided
in explain.
At the end: re-read her request and the plan, check each point, run the whole suite, show_diff, then ask the reviewer for
the language (requesting-code-review) before done.
