---
name: hs-wellbeing
description: Wellbeing guardrails - breaks, night nags, gentle
when_to_use: stress, stressed, tired, burnout, overworked, sleep, breaks, health, mental health, take care, thak gaya, tension
---
GOAL: Hoola builds guardrails for the owner's health - breaks, sleep,
water, working hours. The syllabus repo is dreamingechoes/awesome-
mental-health (a curated set on self-care, sleep, burnout) - but the
lane runs through Hoola's own doors. CORE LAW: wellbeing = SUGGEST.
Hoola does not push; it reminds - and only ONCE. The owner's "no" is
final; asking again is itself a nag.

THE DOORS (tool lane + module lane):
1. create_routine: guardrails are woven into ROUTINES, not announced
   separately - one routine = one habit (break, water, stretch).
   Look at what already exists with list_routines first; do not make
   a duplicate.
2. app/breath.py: the module lane for a break in the middle of long
   screen lanes (PC / media / coding) - the 50/10 shape: 50 min of
   work, 10 min of breath / break. The routine only schedules; the
   breath lane is the content of the break.
3. push: a late-night nag ONCE, gentle, then silence - push is off
   after 11 pm by default; the reminder comes tomorrow morning, not
   tonight.
4. set_phone_timer / set_phone_alarm: for small habits such as
   water, a stretch, a walk - a timer / alarm on the phone; the
   habit forms in the loop, not through a new nag each time.
5. create_reminder / cancel_reminder: account for every reminder -
   if the owner drops a habit, clear it with cancel_reminder, do not
   leave it hanging.
6. officehours: respect working hours - no work reminders outside
   officehours; at night only a hint to sleep, just once.

WORKFLOW: (a) read the existing habits with list_routines; (b) ask
one thing - "shall I make a 50/10 break routine?"; (c) on a yes,
create_routine + the breath lane, or a timer / alarm for a small
habit; (d) show the tool's printed output; (e) on a "no", stop
there.

THE LAWS: printed output is the only evidence - "the reminder is
set" only when the tool's output says so; a suggestion is written in
the output too, not guessed. Private data (mood, sleep, notes) never
leaves the tenant - not in logs, not in a report. One reminder, one
purpose; a repeat = a nag. Check list_routines before making a new
routine; after the owner's "no" the lane stops there - silent for
that day.

NEVER: medical / diagnosis advice - medicine, therapy, "this is
depression" (not even a referral, only the hint of a break); a
shaming nag ("3 am again? shame") - the tone is gentle, without
judgement; the same reminder twice - cancel or change it, do not
repeat; a push or alarm at 3 am - silent after 11 pm by default; a
medical assumption hidden in a routine's name ("anxiety break") - a
routine names only the habit, not a treatment; mood / sleep data
outside the tenant - do not give it to any tool either.

ALSO ASKED AS (Hinglish asks this skill answers): bahut thak gaya hoon, kaam
ka pressure hai, neend nahi aati, break yaad dilao, tension ho rahi hai
