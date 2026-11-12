---
name: me-ffmpeg-recipes
description: ffmpeg recipes - compress numbers for video lanes
when_to_use: compress video, video size, ffmpeg, convert video, reduce file size, video quality, encode, mp4 too big
---
GOAL: Hoola's video lanes - video_edit, video_studio, motion_video -
encode by themselves; the encoder runs inside them. This lane's job
is to give the numbers: how much to compress, which preset, which
crf, which bitrate. The Awesome-ffmpeg catalog (a curated list of
ffmpeg tools, libraries, scripts and docs) is the syllabus - it is
the RECIPE BOOK. The lane encodes, we give the recipe; the role is
clear: the one who gives numbers, without choosing pixels.

RECIPE FLOW (every compress / re-encode job, same order):
1. ORIGINAL SACRED: treat the source file as read-only. Output
   always goes to a NEW file; the original is never an overwrite
   target. First note the original's size in print - the BEFORE
   line starts here.
2. PROBE FIRST: re-encoding the whole film blind is a gamble. Take
   a 2-second probe clip (pick a detail-heavy scene - text, motion,
   a dark area) and encode it with the SAME crf / preset / ladder.
   Look at the probe: is the quality sane? the size ratio sane? One
   printed line: probe in-size vs out-size.
3. PLATFORM LADDER: take the numbers from the catalog / docs - each
   platform has its own bitrate ladder (1080p, 720p, audio with its
   own numbers). Give the lane the ladder; the recipe's crf, not
   your own. Codec / container / preset come from the recipe too,
   not from mood.
4. FULL RUN: the full encode only after the probe passes. Print
   both the BEFORE and AFTER size; the size-diff line is the proof
   of "compressed" - without it that word is not used.
5. VERIFY: look at the output again (the probe point + one random
   point), check audio sync, match the duration. A job is not
   called complete without printed evidence.

QUALITY LAW: winning the number by compressing below legibility is
losing. If the size target is not met, lower the resolution, not
the quality floor; the viewer should never see blocky pixels.

NUMBERS TO KNOW (useful when reading a recipe): lower crf = better
quality, bigger file; slower preset = smaller file, longer time -
look at the trade-off of both in the probe. On platforms with a
bitrate ladder follow the ladder, not crf. Audio has its own
numbers - the video crf does not apply to audio, audio has its own
recipe line.

THE LAWS: the original file always survives; no full run without a
probe; before / after is printed for every job - that is the
evidence; private footage is never uploaded outside the tenant;
ask_approval at the publish / upload step - the lane can do the
whole job staying local.

NEVER: overwrite the original file; celebrate a size reached by
compressing below legibility; start a full re-encode without a
probe; say "compressed" without a printed size diff; rips that
break a platform's Terms (DRM content, paid streams); skip verify
and apply the probe's result blindly to the full run.

ALSO ASKED AS (Hinglish asks this skill answers): video ka size kam karo,
video compress kar do, whatsapp ke liye chhoti file banao
