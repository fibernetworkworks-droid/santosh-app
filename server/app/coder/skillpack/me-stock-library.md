---
name: me-stock-library
description: Stock library - free legal assets into photo lanes
when_to_use: stock photos, free images, royalty free, music for video, b-roll, free assets, background music, icons
---
GOAL: Hoola needs content - a photo in a template, b-roll in a film,
a background track in a story - and the internet holds the biggest
LEGAL goldmine: free stock. nebez/awesome-stock-resources is the
syllabus - a curated catalog of photos, videos, music, SFX and
icons, with each source's license written beside it. This is Hoola's
LEGAL asset library; a pirated shortcut has no place in the lane.

LANE MAP: photo_banao is the photo side, photos_upload /
photos_albums the user library side, hoola_frames the film side -
the stock library FEEDS all of them, it does not replace them. The
app/mediafind.py module lane helps with catalog lookup; the video
lanes (video_edit, video_studio) already encode, our job is to give
them the clip.

THE FLOW (for every asset, same order):
1. CATALOG PICK: write the need - subject, mood, orientation. Find a
   matching source in the catalog; photos, video, music and SFX
   each have different sources. Shortlist 2-3, do not stop at the
   first one found.
2. LICENSE FIRST: read the license before pulling the asset. CC0 =
   free, attribution optional; CC-BY = the creator + source line
   MUST be given. If in doubt, skip to the next source. Note the
   result with memory_search / remember - so the same question does
   not come up again next time.
3. FETCH: with a direct URL bring it in through crawl_start /
   web_sources; if the source offers an API, api_call. The file
   stays inside the tenant - no upload outside.
4. PREP: crop / scale with photo_assist, fix background and noise
   with photo_clean - a raw dump never goes straight into a
   template.
5. USE: place it in photo_banao; make it a clip or track in
   hoola_frames films; keep it in an album with tags (subject +
   source).
6. LEDGER: a license line saved with every asset - source, creator,
   license, date, file path. This line must appear in the printed
   output; print is the evidence.

THE LAWS: the license check comes BEFORE any asset, not after the
download; ask_approval before publishing or paid stock - the free
tier is the default; the user's private photos are never mixed into
stock albums without asking - the tenant's data stays in the tenant.

COMMON TRAPS: if a watermark shows, discard it and change the
source - not "we will crop it out". "Free trial" assets never go
into a commercial template. Some sources forbid scraping - breaking
their ToS is not allowed; use only the official API there. Staying
stuck on one source is wrong too - the catalog is big, move on.

NEVER: use a watermarked or pirated asset; use an asset without a
license note; bring "free trial" assets into commercial work; break
a source's ToS (scraping without permission); print a CC-BY asset
without attribution; say "it looked free so it is free" without a
license check; mix the user's private media into a stock album
without asking.

ALSO ASKED AS (Hinglish asks this skill answers): free photo ya background
music chahiye, video ke liye free b-roll dhoondo, bina copyright wali image
