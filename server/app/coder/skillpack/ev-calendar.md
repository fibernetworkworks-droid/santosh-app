---
name: ev-calendar
description: Event radar - CFPs and meetups into calendar
when_to_use: events, conferences, tech conference, call for papers, cfp, meetups, hackathon, workshop dates, upcoming events, hackathons
---
GOAL: run an event radar for the owner - meetups, conferences and CFP
deadlines all reach their calendar, with no double-booking. Syllabus:
awesome tech-events / dev-events type curated GitHub catalogs - choose
the sources from these lists. The radar runs only through Hoola's
operator doors, never on its own whim.

THE DOORS (all real operator tools):
1. SOURCES PICK: read the syllabus lists and choose sources that match
   the owner's interests - meetup group pages, CFP pages, conference
   calendars. 3-5 solid sources are enough, not the whole internet.
2. WATCH: crawl_start on each source; ask crawl_status for how the job
   is going; for continuous watching use research_watch - a weekly
   check, and a new event or CFP surfaces by itself.
3. TOPIC MATCH: when a new event shows up, first match it against the
   owner's interests (memory) - go on only if the topic matches,
   otherwise the radar stays quiet; an event with no relevance must not
   fill the calendar.
4. FREE SLOT FIRST: look at calendar_free_slots FIRST - never
   double-book. When the slot is free, calendar_add_event, with a
   travel buffer (the trip to the venue is part of the event).
5. CFP DEADLINES: when you find a CFP, create_reminder twice - one week
   before and one day before. A CFP without a deadline reminder is
   unfinished.
6. MULTI-DAY: for a far-away or multi-day conference make an event_plan
   and show it to the owner with event_plan_dekho - BEFORE adding it.
7. WEEKLY DIGEST: calendar_agenda gives everything for the coming weeks
   at a glance - a printed digest in the owner's hands, not just in chat.

THE LAWS: buying a paid ticket or an RSVP = ask_approval first (the
money and the decision are the owner's; the radar only suggests and
never pays itself); whatever happened is proved only by printed output -
no printed proof, no "done"; the owner's private data (interests,
calendar, memory) stays inside the tenant - crawl/research runs only on
public event and CFP pages.

FLOW: choose sources from the syllabus -> crawl_start + research_watch
on -> new event? topic match from memory -> calendar_free_slots ->
calendar_add_event (travel buffer) -> CFP? create_reminder 7 days before
+ 1 day before -> at the end of the week a calendar_agenda digest,
printed and presented. To avoid duplicates: before adding, run
calendar_find_event - if the same event is already there, skip.

NEVER: a paid ticket or RSVP without ask_approval; calendar_add_event
without checking calendar_free_slots (never double-book); add the same
event twice - verify with calendar_find_event first; a CFP note without
a deadline reminder; an agenda digest without printed proof; send the
owner's private data outside the tenant.
