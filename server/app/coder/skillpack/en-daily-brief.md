---
name: en-daily-brief
description: Daily brief - podcasts/newsletters into one routine
when_to_use: podcasts, newsletters, morning news, daily brief, summary every morning, what to listen, reading list, news digest
---
GOAL: the user's day starts in one place - a short morning brief
built from podcasts and newsletters, made and pushed by Hoola.
Syllabus: rshipp/awesome-podcasts (curated shows, a category-wise
catalog) + zudochkin/awesome-newsletters (a big index of
newsletters). These lists are for DISCOVERY only - the real lane
runs through Hoola's real doors, nothing is "auto-fetched" from a
list.

THE FLOW:
1. PICK SOURCES: from the syllabus lists choose 2-3 podcasts +
   2-3 newsletters that match the user's interests. Discover
   names from the lists; keep the free feed as the default. Any
   paid subscription / premium feed = ask_approval first ("this
   one is paid, shall I take it?"). Look up the user's older
   favorites with memory_search too - set up once, do not ask
   again every day.

2. ROUTINE SLOT: make a daily morning slot with create_routine
   (such as 7:30 AM, with push delivery). Look at the existing
   routines with list_routines first - there must be no overlap.
   If a slot is missed, one nudge with create_reminder.

3. PODCAST LANE: pick up new episodes through the podcast door
   (those since yesterday). For video shows use youtube_search,
   and youtube_watch / youtube_playlist to watch. With
   podcast_dekho the user can listen right there. Do NOT take
   every episode into context in full - a short summary first,
   never a transcript dump.

4. EMAIL LANE: find the newsletters arriving in the inbox with
   email_read, tag them brief vs later with email_triage. Batch
   it in one pass - do not give every newsletter its own turn.

5. NOTEBOOK LANE: a "Daily Brief" notebook with notebook_create -
   a 2-3 line summary of each episode / issue on one card. When
   the user asks "what came out today?", answer from the notebook
   with notebook_ask. With notebook_audio make a short
   listenable version of the whole digest (good for a commute).

6. DIGEST + PUSH: join it all into a one-screen / one-page
   digest - top headlines, one podcast pick, one newsletter
   quote, a 2-3 line "what happened yesterday" recap. Morning
   delivery by push in that same slot. Say "brief ready" only
   when the printed digest is in front of you - no claim without
   evidence.

7. CONTINUITY: "what happened yesterday" from memory_search -
   which episodes / issues came yesterday, which were left
   unfinished. Note each day's digest in memory, so the next
   day's recap builds itself and sources do not repeat.

THE LAWS: any paid or subscribe step = ask_approval first; the
printed digest = the only evidence, everything else is a guess;
the user's private data (inbox, notes, history) never leaves the
tenant - summaries go only into their own notebook and their own
push.

NEVER: subscribe to anything paid without asking; put a whole
episode / transcript into context (summarize, do not dump);
autoplay at night (podcast_dekho only in the day, while the user
is awake); send private notes about sources outside the tenant;
say "brief ready" without a printed digest; add a random source
from outside the syllabus lists without asking.

ALSO ASKED AS (Hinglish asks this skill answers): roz subah ka brief
chahiye, podcast aur newsletter ka saar do, kya sunna aur padhna hai
