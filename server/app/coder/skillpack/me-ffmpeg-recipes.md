---
name: me-ffmpeg-recipes
description: ffmpeg recipes - compress numbers for video lanes
when_to_use: compress video, video size, ffmpeg, convert video, reduce file size, video quality, encode, mp4 too big
---
GOAL: Hoola ke video lanes - video_edit, video_studio, motion_video -
khud encode karte hai, andar se encoder chalta hai. Lane ka kaam
numbers dena hai: kitna compress, kaunsa preset, kaunsa crf, kaunsa
bitrate. Awesome-ffmpeg ka catalog (ffmpeg tools, libraries, scripts,
docs ka curated list) syllabus hai - ye RECIPE BOOK hai. Encoding
lane karta hai, recipe hum dete hai; role line se: numbers dene wala,
pixels chune bina.

RECIPE FLOW (har compress/re-encode job, same order):
1. ORIGINAL SACRED: source file read-only samjho. Output hamesha
   NAYI file me; original kabhi overwrite target nahi. Pehle
   original ka size printed note karo - BEFORE line yahi se shuru
   hoti hai.
2. PROBE PEHLE: poori film andhe re-encode karna jua hai. 2-second
   ka probe clip lo (detail bhara scene chuno - text, motion, dark
   area), USI crf/preset/ladder se encode karao. Probe dekho:
   quality sane? size ratio sane? Ek printed line: probe in-size
   vs out-size.
3. PLATFORM LADDER: catalog/docs se numbers uthao - har platform ka
   apna bitrate ladder hai (1080p, 720p, audio ka apna hisaab).
   Ladder lane ko do; apne mann ka crf nahi, recipe ka crf. Codec/
   container/preset bhi recipe se hi, mood se nahi.
4. FULL RUN: probe pass hua tab poora encode. Printed BEFORE/AFTER
   size dono; size-diff ka line hi "compress ho gaya" ka saboot
   hai - uske bina ye word band rahega.
5. VERIFY: output ko wapas dekho (probe point + ek random point),
   audio sync check, duration match. Printed evidence ke bina job
   complete nahi bola jayega.

QUALITY LAW: legibility se neeche compress karke number jeetna haar
hai. Size target na mile to resolution neeche karo, quality floor
nahi; viewer ko pixel ka mosam nahi dikhna chahiye.

NUMBERS GYAN (recipe padhte waqt kaam aayega): crf lower = better
quality, bada file; preset slower = chhota file, lamba time - probe
me dono ka trade-off dekho. Bitrate ladder wale platforms pe crf
nahi, ladder follow karo. Audio apna hisaab hai - video ka crf
audio pe nahi chalta, audio ka apna recipe line hota hai.

THE LAWS: original file hamesha bachegi; probe bina full run nahi;
har job ka before/after printed hoga - wahi evidence; private
footage tenant se bahar upload nahi hoti; publish/upload step pe
ask_approval - lane local rehkar pura kaam kar sakti hai.

NEVER: original file overwrite karna; legibility se neeche compress
karke size celebrate karna; bina probe poora re-encode shuru karna;
bina printed size-diff ke "compress ho gaya" bolna; platform ki
Terms todne wale rips (DRM content, paid streams); verify skip
karke probe ka result full run pe blind lagana.
