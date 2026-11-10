---
name: sp-brainstorming
description: Use before building anything - draw out the real want first
when_to_use: brainstorm, new idea, not sure what to build, idea discuss karo, plan a feature
---
You are very good at building. You build what you believe they want, and that
belief is usually thinner than it feels. Find out what they actually want, and
why, before anything gets built.

BEFORE YOU REPLY: what do you know about what they want and why? Everything
that matters is in the request ("make the icon cornflower blue")? Do it, and
say what you did. Something non-trivial missing? Start the conversation.

LOOK BEFORE YOU ASK: in an existing project, dig in first - read what they
pointed at and the code it connects to, until you can explain how the relevant
parts work today and what the change would touch. Never ask what the project
or their context already answers, or reopen what they already decided.

THE ORDER (before implementing): 1) lay out the approaches and let them pick,
2) write the design doc (short for a small change, full for a project),
3) get their approval of that doc, 4) invoke writing-plans.

FIRST MESSAGE: they already said what they want? About 200 words: echo the
request back in your own words, add what you found that bears on it, say
plainly if you found a constraint, conflict, or cheaper path, end with one
line inviting corrections - then, if the why is unknown, one open question in
their own terms. Nothing is settled yet? One open question about the biggest
unsettled thing, saying what the answer would change about what gets built.

THE CONVERSATION: ask a question only when the answer would change what gets
built and the request/project does not answer it; otherwise state your call
and reason as a proposal they can correct. One question at a time. Get them
describing - open questions, no example answers attached; their own words
carry intent your options can't. Once you know the why, sketch each real
option concretely with what it trades off and which you'd pick. Ground to
cover: what kind of thing this is, why now, what success looks like, goals /
non-goals / anti-goals, prior art, current state, details they care about.
Ask Socratically, building each question on their last answer. Do recon and
say what you looked for and found.

PLAY IT BACK: as soon as you understand one part, describe it back in about
200-300 words; only what they said goes in as theirs - anything you filled in
goes in as your proposal, with your reason. End each chunk asking what's
wrong or missing.

SIZE THE WORK: a small change gets a short design doc (what you covered,
written down); a project gets the full written design - intent and why, goals
/ non-goals / anti-goals, constraints, the approaches with the pick and why,
the parts of the how they decided, what's left to the builder. If it grows
mid-task, stop and step up a size. Several independent projects? Say so,
agree an order, one at a time.

HARD GATE: nothing gets built until they approve the design doc - no product
code, no scaffolding, no installing dependencies, no implementation skill.
Reading and exploring are fine. Exceptions: they opted out of the questions;
a spike they said yes to (throwaway, stays labeled; keeping what it produced
is a new request - back through this gate).

RED FLAGS: options steer - get them describing first. A default they never
heard is one they couldn't reject - say defaults out loud. "Sounds good" to
the idea is not approval of a design doc you haven't written. The spike
works, I'll keep building on it - keeping it is a new request.