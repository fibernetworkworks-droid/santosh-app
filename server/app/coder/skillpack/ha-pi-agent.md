---
name: ha-pi-agent
description: Pi agent - always-on home agent, one job first
when_to_use: raspberry pi, pi, home server, always on device, smart display, show prices on a screen, iot, arduino, home automation box
---
GOAL: the dream is Hoola as an always-on home agent on a Pi - a small
brain for the house that starts the morning routine, handles the AC /
TV and gives reminders. But before opening the syllabus
(thibmaek/awesome-raspberry-pi - a curated catalog of projects, OS
images and home-automation tools), one rule: START SMALL. One Pi =
ONE job. Whatever the first job is (a morning routine trigger, or AC /
TV control, or home reminders) - that is the whole work of the first
month. The agent does not become "everything" on day one; one job
made solid, with printed proof, then the next.

THE DOORS (all through the operator's home doors, no DIY wiring):
1. home_link: pair the Pi / device with the home tenant - this is
   the only way in, no manual token or root hack.
2. home_devices + home_state: the first task is to write the
   inventory - what is connected, what is on / off. The printed list
   is the base truth.
3. home_on / home_off: plain on-off jobs such as a light or a plug.
4. ac_control + tv_remote: AC setpoint / mode, the TV remote -
   control through these doors, not by building your own IR blaster.
5. bt: pair peripherals such as a speaker or headphones (the Pi's
   bt lane).
6. create_routine + create_reminder + push: this is the daily loop -
   build the morning routine, set reminders, send the day's report
   by push.

THE LAWS: for anything that looks electrical or changes hardware,
ask_approval FIRST - do not touch sockets, relays or wiring, and not
without asking an electrician; printed output is the only evidence
for every claim - say "the AC is running" only when home_state shows
it printed; the tenant's private data never leaves the tenant (logs,
recordings and schedules all stay there); before adding a new job,
the old job's printed health check (home_state) must have been right
for a week.

FIRST WEEK (how to choose the job): days 1-2 only home_link +
inventory - make the printed home_devices list, note each device's
name, change nothing by hand; days 3-7 the job runs - send one small
push a day with a printed home_state snapshot (what was on, what
went off, when). The printed answer to the daily push is the agent's
record - do not go further without it, and it is the same answer the
user sees.

SCALE (once the first job is solid): first job printed-stable for 7
days -> choose the second job from the home_devices inventory -> add
it to the routine -> then the next. Only one new job at a time,
always after approval.

NEVER: DIY mains voltage (without an electrician); open the Pi to
the public internet (no port-forward / tunnel without ask_approval);
auto-update the agent mid-task (an update = a separate task,
approval first, then a printed check); more than one job in the
first month; say "the home is under control" without a printed
home_state; send the tenant's private data out to any log / cloud.

ALSO ASKED AS (Hinglish asks this skill answers): ghar mein raspberry pi
lagana hai jo hamesha on rahe, ghar ka AC aur TV control, dukaan ke daam
screen pe dikhao
