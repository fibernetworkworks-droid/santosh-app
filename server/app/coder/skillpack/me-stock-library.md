---
name: me-stock-library
description: Stock library - free legal assets into photo lanes
when_to_use: stock photos, free images, royalty free, music for video, b-roll, free assets, background music, icons
---
GOAL: Hoola needs content - photos in a template, b-roll in a film, a
background track in a story - and the biggest LEGAL goldmine on the
internet is free stock. nebez/awesome-stock-resources is the syllabus -
a curated catalog of photos, videos, music, SFX and icons, with each
source's license written beside it. This is Hoola's LEGAL asset library;
a pirated shortcut has no place in the lane.

LANE MAP: photo_banao is the photo side, photos_upload/photos_albums the
user-library side, hoola_frames the film side - the stock library FEEDS
all of these, it does not replace them. The app/mediafind.py module lane
helps with catalog lookup; the video lanes (video_edit, video_studio)
already encode, our job is to hand them the clip.

THE FLOW (for every asset, the same order):
1. CATALOG PICK: write the need - subject, mood, orientation. Find a
   matching source in the catalog; photo, video, music and SFX are
   separate sources. Shortlist 2-3, do not stop at the first one found.
2. LICENSE FIRST: read the asset's license before pulling it. CC0 =
   free, attribution optional; CC-BY = you MUST give the creator + source
   line. If in doubt, skip, go to the next source. Note the result in
   memory_search/remember - so the same question need not come up again
   next time.
3. FETCH: if you have a direct URL, bring it with crawl_start/web_sources;
   if the source offers an API, api_call. The file stays inside the
   tenant - no upload outside.
4. PREP: crop/scale with photo_assist, fix background and noise with
   photo_clean - a raw dump does not go straight into a template.
5. USE: put it in photo_banao; make a clip or track in hoola_frames
   films; keep it in an album with a tag (subject + source).
6. LEDGER: a license line saved with every asset - source, creator,
   license, date, file path. This line must appear in the printed
   output; printed is evidence.

THE LAWS: the license check comes BEFORE any asset, not after the
download; ask_approval before publishing or paid stock - the free tier
is the default; the user's private photos are not mixed into stock
albums without asking - the tenant's data stays in the tenant.

COMMON TRAPS: if a watermark shows, discard and change the source - "we
will crop it out" is not allowed. "Free trial" assets never go into a
commercial template. Some sources forbid scraping - breaking their ToS is
not allowed; use the official API there. Sticking to a single source is
also wrong - the catalog is big, switch.

NEVER: use a watermarked or pirated asset; use an asset without a
license note; bring "free trial" assets into commercial work; break a
source's ToS (scraping without permission); publish a CC-BY asset
without attribution; say "it looked free, so it is free" without a
license check; mix the user's private media into a stock album without
asking.
