---
name: cr-crew-plays
description: Agent crews - roles, tasks, context, the three-door routing
---

# Crew plays (the crewAI way, Hoola-sized)

A CREW is a small named team working ONE job inside one turn: roles (agent with goal +
backstory), a task list, and a process. Use `crew_run`. Route honestly between the
three team doors:

- `delegate_task` = parallel INDEPENDENT one-shots (compare three sites), no memory
  between workers.
- `crew_run` = a PIPELINE with roles and context threading (research -> draft ->
  review -> polish); each task sees the earlier outputs it names.
- `dhara` = the same shape RECURRING on a schedule. Crew once, dhara forever.

## Shaping a crew that works

ROLES: one job per role, goal = what done means for THAT member, backstory = the
expertise lens (1-2 lines, real, no cosplay). 2-4 members usually beat 6. Named tools
allowlist when a member must not wander.

TASKS: description carries the work; `expected_output` carries DONE (shape, length,
what a reviewer would check) - it is the cheapest guardrail there is. `context` names
EARLIER tasks only; it is literally their output pasted in, so keep refs short and
cap your asks. Independent tasks: `async_execution: true` (they run concurrently, no
context allowed). Interpolate her facts with {key} from inputs - never invent slots.

PROCESS: sequential by default. `hierarchical` adds a MANAGER with NO tools that
delegates via DELEGATE/ASK/FINISH lines - use it when the WORK ITSELF is unpredictable
(research scoping); use sequential when the pipeline is known.

## The laws

- Money and sends NEVER ride inside a crew: workers are denied delegate_task /
  confirm_send / haan_karo / pc_do structurally. The crew proposes; SHE approves
  outside it.
- A crew spends brain rounds - small crews, small tasks, one job per kickoff.
- A failed task comes back honest (guardrail feedback, timeouts); read the per-task
  results, never claim a crew success you did not see.
- Voice calls never see crews (minutes vs seconds). Desk/chat only.

NEVER: a crew with 6 vague roles and no expected_output; context refs to future tasks;
async tasks reading context; inventing a role's report; a crew that sends or spends.
