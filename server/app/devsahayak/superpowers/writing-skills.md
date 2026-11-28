---
name: writing-skills
description: She asks for a skill for her repo (.claude/skills/<name>/SKILL.md) - write one that really triggers and works
when: write a skill, new skill, SKILL.md, teach hoola, make a skill
---
A skill is a short how-to for a repeated kind of work, saved as .claude/skills/<name>/SKILL.md.
- Frontmatter: name (lowercase-with-dashes) and description = WHEN to use it ("Use when ..."), the words a real request
  uses. The description decides whether it is ever read: name the situations, not the content.
- Body: the rule first (one line), then the steps, each with its check, then the red flags (the excuses to skip it, each
  with the answer). Short: what an agent needs to follow it, nothing it already knows.
- Test it like code: think of 2-3 requests where it should trigger and one where it should not; read it as the agent
  would and fix what is unclear.
- Longer reference material goes in a separate file next to SKILL.md that the skill points to.
