---
name: sp-writing-skills
description: Use when creating or editing skills - TDD applied to docs
---
Writing a skill IS test-driven development applied to process documentation:
write the tests (pressure scenarios), watch them fail (baseline agent
behavior WITHOUT the skill), write the skill, watch tests pass (agents
comply), refactor.
THE IRON LAW: NO SKILL WITHOUT A FAILING TEST FIRST - for NEW
skills AND EDITS. Written before testing?
Delete it, start over. If you didn't watch an agent fail without the
skill, you don't know the skill teaches the right thing.

WHAT A SKILL IS: a reference guide for proven techniques, patterns, tools -
reusable across projects. NOT a narrative about how you solved one problem.
CREATE when: not intuitively obvious, referenced again across projects,
applies broadly. DON'T create for: one-offs, standard
practices well-documented elsewhere, project-specific conventions, anything
enforceable with regex/validation - automate that; documentation is for
judgment calls.

TDD MAPPING: test case = pressure scenario with a subagent; RED = the agent
violates the rule without the skill (document the EXACT rationalizations,
verbatim); GREEN = the minimal skill addressing those specific violations;
REFACTOR = a new rationalization appeared -> add its explicit counter ->
re-test until bulletproof. Build the rationalization table and red-flags
list from every iteration.

MATCH THE FORM TO THE FAILURE (the form that fixes one failure backfires on
another): skips/violates a rule under pressure -> prohibition +
rationalization table + red flags. Complies but the output has the wrong
shape -> a positive recipe stating what the output IS - its parts, in order
(prohibitions backfire here: agents negotiate with "don't X" - in
head-to-head wording tests the prohibition arm produced MORE of the
unwanted content; a recipe leaves nothing to negotiate). Omits a required
element -> a REQUIRED slot in the template they fill in. Behavior should
depend on a condition -> a conditional keyed to an observable predicate.
RULES FOR EITHER: no nuance clauses - "don't X unless it matters" reopens
the negotiation; express a real exception as its own conditional.
Exemption clauses don't scope - restructure so the rule can't reach the
exempt part.

MICRO-TEST WORDING first: one fresh-context sample per
call; ALWAYS a no-guidance control (control doesn't fail -> nothing to fix
- stop, don't author); 5+ reps per variant (single samples lie); manually
read every flagged match (template echoes fake hits); variance is
a metric - five interpretations across five reps means the wording isn't
binding.

TEST BY TYPE: discipline skills -> pressure scenarios (time + sunk cost +
authority + exhaustion); technique skills -> application,
variation, and missing-information scenarios; pattern skills ->
recognition, application, counter-examples; reference skills -> retrieval
and gap tests.

THE DESCRIPTION says only when to use it - triggers and symptoms, starting
"Use when...", third person, never a workflow summary (an agent that reads
a workflow summary follows the summary instead of the skill). Name:
letters, numbers, hyphens only. Keywords early and often - agents search,
match the description, scan the overview, read the quick-reference table,
load the example only when implementing.

ONE EXCELLENT EXAMPLE beats many mediocre ones: complete, runnable,
commented with WHY, from a real scenario, ready to adapt. Never five
languages, never fill-in-the-blank templates. Inline code <50 lines; heavy
reference (100+ lines) in its own file; invoke bundled scripts through
their interpreter in prose ("bash scripts/tool.sh") - never bare paths
(packagers strip executable bits).

STRUCTURE: SKILL.md plus supporting files only for reusable tools or heavy
reference; overview with the core principle; quick-reference table; common
mistakes; no narrative storytelling; flowcharts only for non-obvious
decisions; semantic labels, never helper1/step3.

STOP AFTER EACH SKILL: deploy before starting the next - batching untested
skills is deploying untested code.
