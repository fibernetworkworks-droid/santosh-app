---
name: sp-diagnosing-superpowers
description: Use when a session went wrong - report with path:line proof
---
A session went wrong - repeated work, ignored plans, stumbles, poor
results, a skill that didn't fire, "it took too long", "why is it so
expensive", "what is it doing" - and they want to know why. Pin down the
problem, read the transcripts on disk, and report what happened WITH
EVIDENCE. You report; you do not diagnose the skills themselves - whoever
triages the report decides whether anything changes.

CORE PRINCIPLE: every finding cites path:line. No citation, no finding.
Every number comes from the transcript or from a command you ran - never
from memory.

WORKFLOW: 1) INTAKE - one question at a time until you can state the
session(s), the turn range if known, what was expected, what happened, and
the observable they care about (wall-clock, tokens, repeated actions, one
specific action). "It took too long" is a complaint, not a problem
statement. INTAKE BEFORE ANALYSIS: nothing downstream starts until they have
answered; if they're away, write the questions and stop - a statement you
reconstructed for them is not an answer. An already-scoped request (one
specific event, what is running now) is itself the statement. 2) LOCATE -
resolve each session to verified absolute filesystem paths; confirm a past
session by quoting its first prompt and timestamp; list every rejected
candidate with the reason; enumerate subagent transcripts; open a case file
per session and tell them the path. 3) TRIAGE - read the region around the
reported problem yourself; dispatch one analyst per dimension in parallel
(skill-timeline, plan-adherence, repeated-work, stumbles, quality-evidence,
request-conflicts, cost-and-time; split by turn range when long); DISCARD
any returned finding without path:line. 4) REPORT - fill every section in
order, write it to the workspace, show it, give the path. 5) BUG REPORT -
only when they ask: search open AND closed issues for the symptoms first,
show matches, suggest adding to the closest; a new issue only after they
approve the exact text - none with a placeholder summary. 6) EXPORT - only
when asked, NEVER unprompted: ask the redaction level (skeleton = no
tool-result bodies; evidence = bodies only for cited events; full), build
the bundle, run scrub + scrub-audit until CLEAN, archive only after
approval, and say scrubbing can miss things - they must review every file
before sharing.

LEAD WITH the dimension matching the complaint: "took too long" ->
cost-and-time + stumbles; "why this extra work" -> repeated-work +
plan-adherence; "so expensive" -> cost-and-time; "what is it doing" ->
skill-timeline; "ignored the plan" -> plan-adherence (compaction lines
first); "skill X never fired" -> skill-timeline.

HARD RULES: one transcript line can be a megabyte - read defensively and
chunked, on every session file, every time. READ-ONLY - never modify, move,
or delete a session file. Pass subagents exact absolute paths (a subagent's
"current session" is its own). HUMAN PROMPTS ONLY - hook output, system
reminders, and tool results are not the partner's words; in a subagent
transcript "user" is the parent agent. NO SKILL DIAGNOSIS - state
involvement and stop; never name a defect in a skill or propose a change;
the partner pressing for a fix does not waive this. Approval gates on issue
text and on any archive.
