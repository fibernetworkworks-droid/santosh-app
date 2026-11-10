---
name: ev-calendar
description: Event radar - CFPs and meetups into calendar
when_to_use: events, conferences, tech conference, call for papers, cfp, meetups, hackathon, workshop dates, upcoming events, hackathons
---
GOAL: owner ke liye event radar chalu - meetups, conferences, CFP
deadlines sab uske calendar me pahunchein, bina double-booking ke.
Syllabus: awesome tech-events / dev-events type curated GitHub
catalogs - inhi lists se sources chunne hain. Radar Hoola ke operator
doors se hi chalta hai, apni marzi se kahin nahi.

THE DOORS (sab operator ke asli tools):
1. SOURCES PICK: syllabus lists padho, owner ki interests wale sources
   chuno - meetup group pages, CFP pages, conference calendars. 3-5
   solid sources kaafi hain, poora internet nahi.
2. NAZAR: har source pe crawl_start; kaam ka haal crawl_status se
   poochho; lagataar nazar ke liye research_watch - weekly check,
   naya event ya CFP khud samne aayega.
3. TOPIC MATCH: naya event dikhe to pehle owner ki interests (mem)
   se milao - topic match hai tabhi aage badho, warna radar chup;
   bina matlab ka event calendar bhar nahi sakta.
4. FREE SLOT PEHLE: calendar_free_slots dekho PEHLE - double-book
   kabhi nahi. Slot khali ho tab calendar_add_event, aur travel
   buffer ke saath (venue tak ka safar bhi event ka hissa hai).
5. CFP DEADLINES: CFP mila to create_reminder do baar - ek hafte
   pehle aur ek din pehle. Bina deadline reminder CFP adhoora hai.
6. MULTI-DAY: door ya bahut-din wala conference ho to event_plan
   banao, event_plan_dekho se owner ko dikhao - add karne se PEHLE.
7. WEEKLY DIGEST: calendar_agenda se agle hafton ka saara saaman ek
   nazar me - printed digest owner ke haath me, chat me nahi.

THE LAWS: paid ticket ya RSVP karna = pehle ask_approval (paise aur
faisla owner ke hain, radar sirf suggest karta hai, khud pay nahi
karta); jo bhi hua hai wo printed output se hi saabit hota hai -
bina printed proof koi "ho gaya" nahi; owner ki private data
(interests, calendar, mem) tenant ke andar hi rehta hai -
crawl/research sirf public event aur CFP pages pe chalta hai.

FLOW: syllabus se sources chuno -> crawl_start + research_watch on
-> naya event? topic match mem se -> calendar_free_slots ->
calendar_add_event (travel buffer) -> CFP? create_reminder 7 din
pehle + 1 din pehle -> hafte ke end me calendar_agenda digest,
print karke pesh karo. Duplicate se bachna: add se pehle
calendar_find_event - wahi event pehle se hai to skip.

NEVER: paid ticket ya RSVP bina ask_approval; calendar_add_event
bina calendar_free_slots check (double-book kabhi); same event do
baar add - calendar_find_event se pehle verify; CFP note bina
deadline reminder; agenda digest bina printed proof; owner ki
private data tenant se bahar bhejna.
