---
name: ev-calendar
description: Event radar - CFPs and meetups into calendar
when_to_use: events, conferences, tech conference, call for papers, cfp, meetups, hackathon, workshop dates, upcoming events, hackathons
---
GOAL: an event radar for the owner - meetups, conferences and CFP
deadlines all reach their calendar, with no double-booking.
Syllabus: curated GitHub catalogs of the awesome tech-events /
dev-events kind - sources are chosen from these lists. The radar
runs only through Hoola's operator doors, never anywhere on its own.

THE DOORS (all real operator tools):
1. PICK SOURCES: read the syllabus lists and choose the sources that
   match the owner's interests - meetup group pages, CFP pages,
   conference calendars. 3-5 solid sources are enough, not the
   whole internet.
2. WATCH: crawl_start on every source; ask crawl_status how the job
   is going; for a continuous watch use research_watch - a weekly
   check, so a new event or CFP surfaces by itself.
3. TOPIC MATCH: when a new event shows up, first match it against
   the owner's interests (memory) - go further only on a topic
   match, otherwise the radar stays silent; an irrelevant event
   must not fill the calendar.
4. FREE SLOT FIRST: look at calendar_free_slots FIRST - never
   double-book. When the slot is free, calendar_add_event, with a
   travel buffer (the trip to the venue is part of the event).
5. CFP DEADLINES: for a CFP, create_reminder twice - one week
   before and one day before. A CFP without a deadline reminder is
   incomplete.
6. MULTI-DAY: for a far-away or many-day conference make an
   event_plan and show it to the owner with event_plan_dekho -
   BEFORE adding it.
7. WEEKLY DIGEST: everything in the coming weeks at one glance from
   calendar_agenda - a printed digest in the owner's hands, not
   just said in chat.

THE LAWS: buying a paid ticket or sending an RSVP = ask_approval
first (the money and the decision are the owner's; the radar only
suggests, it never pays); whatever happened is proved only by
printed output - no "done" without printed proof; the owner's
private data (interests, calendar, memory) stays inside the tenant -
crawl / research run only on public event and CFP pages.

FLOW: choose sources from the syllabus -> crawl_start +
research_watch on -> new event? match the topic from memory ->
calendar_free_slots -> calendar_add_event (travel buffer) -> CFP?
create_reminder 7 days before + 1 day before -> at the end of the
week the calendar_agenda digest, printed and presented. Avoid
duplicates: calendar_find_event before adding - if the same event
is already there, skip it.

NEVER: a paid ticket or RSVP without ask_approval;
calendar_add_event without a calendar_free_slots check (never
double-book); add the same event twice - verify with
calendar_find_event first; note a CFP without a deadline reminder;
an agenda digest without printed proof; send the owner's private
data outside the tenant.

ALSO ASKED AS (Hinglish asks this skill answers): is mahine kaun kaun se
hackathon hain, aane wale events batao, conference calendar mein daal do
