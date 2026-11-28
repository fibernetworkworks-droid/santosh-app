---
name: brainstorming
description: Before building something new or changing behaviour when what she wants is still open - shape the design with her first
when: build, create, new feature, new app, idea, design, add functionality, how should, what if, I want
---
Use when what to build is still open. A clear, small, fully specified change does not need it - do the change.
1. LOOK FIRST: read the repo parts the idea touches (files, docs, recent changes) before asking anything; never ask what
   the code can tell you.
2. WHAT DO YOU KNOW? Say back in two lines what you understood and what is still unknown.
3. ASK, ONE QUESTION AT A TIME, with ask_user. Prefer 2-4 choices she can tap. Specific to her project, never a generic
   checklist. Learn: why she wants it, who uses it, what must not change, what "done" looks like. Stop when the next
   answer would not change the design.
4. APPROACHES: give 2-3 ways with their trade-offs and say which you recommend and why. Smaller is better (YAGNI).
5. PLAY IT BACK, then the design in short sections she can read (what, how it works, data, errors, how it is tested),
   asking after each section whether it is right. Change what she corrects.
6. SIZE IT: small = go straight to the change; bigger = a plan (writing-plans) she approves first.
7. WRITE IT DOWN only after her yes: save the design as docs/designs/YYYY-MM-DD-<topic>.md in the change if she wants it
   kept; otherwise it lives in done explain.
Never write code during brainstorming. RED FLAGS: jumping to code, ten questions in one message, one approach only,
asking about things the repo already shows, designing features she did not ask for.
