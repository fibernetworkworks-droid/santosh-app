---
name: skill-maker
description: Turn a task she repeats into a reusable Hoola skill: interview, draft within the limits, dry-run on sample asks, save only after her yes, then tune it from the desk numbers.
license: Hoola original, written by Newtika Pvt Ltd. Inspired by the general idea of a create-test-improve loop for skills; contains no text from any third-party skill.
when_to_use: naya skill, skill sudharo, skill kaam nahi kar raha, reusable skill, baar baar wala kaam, tareeka save karo, reusable instructions, skill improve, new skill, make a skill, the skill is not working, save this method
---

# Making a Hoola skill

A skill is a short how-to for a CLASS of task she will do again (for example "weekly stock count"), never for one single incident. Hoola saves it as a file, finds it when a later ask matches, and reads it before following it. You write it with the `skill_manage` tool.

## 1. Interview (a few short questions, in her language)
- Which task do you keep repeating, and what starts it?
- What are the steps you take, in order? Where do things usually go wrong?
- What does a good result look like (the file, message or number that comes out)?
- Is there anything that must NEVER be done on the way (send without asking, use a certain account)?
If a similar skill may exist, call `skill_manage list` first and offer to improve it instead of making a duplicate.

## 2. Draft within the limits
- `name`: lowercase, words joined by hyphens, at most 64 characters, naming the class of task (`weekly-stock-count`, not `ramesh-14-march-count`).
- `description`: ONE sentence of at most 60 characters. Start with a verb. It is what the model sees first, so it must say what the skill is for.
- `body`: at most 4,000 characters, markdown. Put a line `Use when:` first, with the trigger words she really says, in English and in any other language she uses (search reads the body too, so these words are how the skill gets found). Then the numbered steps, then `Check before finishing:` with 2 to 4 checks, then `Never:` with the hard no's.
- Write instructions, not a story. Keep names, prices and customer details OUT; use placeholders like `<customer>`.
- Never put a password, key, OTP or card number in a skill.

## 3. Dry-run before saving
Write three realistic asks she might type (one in another language she uses, if any) and one that should NOT use this skill. For each ask, walk through the draft step by step and say what you would do and what would come out. Where a step is unclear, missing or wrong, fix the draft. Also check that the `Use when:` words really appear in the three asks. Tell her briefly what the dry-run found.

## 4. Save only after her yes
Show the final name, description and body. When she says yes, call `skill_manage` with `create`. To change an existing skill, `read` it first (update is refused without a read), then `update`. Deleting is a separate call and only on her word.

## 5. Tune it later
After she has used the skill a few times, look at what actually happened: the Skill Desk shows how often each skill was shown and how often it was opened. A skill that is shown but never opened has a weak description or wrong trigger words: sharpen the first line. A skill that is opened but the work still goes wrong has weak steps: ask her what went wrong last time and fix exactly that step.

## Hoola note
This skill was written by Newtika for Hoola. It does not run automated test suites: the dry-run in step 3 is reasoning on sample asks, and it is not proof that the skill works. Say so if she asks. Hoola's own house rules (reply style, privacy, confirm-before-send) win over it if they ever disagree.
