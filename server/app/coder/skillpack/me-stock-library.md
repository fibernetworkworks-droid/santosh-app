---
name: me-stock-library
description: Stock library - free legal assets into photo lanes
when_to_use: stock photos, free images, royalty free, music for video, b-roll, free assets, background music, icons
---
GOAL: Hoola ko content chahiye - template me photo, film me b-roll,
story me background track - aur internet pe sabse bada LEGAL goldmine
pada hai: free stock. nebez/awesome-stock-resources syllabus hai -
photos, videos, music, SFX, icons ka curated catalog, har source ka
license saath me likha hai. Ye Hoola ki LEGAL asset library hai;
pirated shortcut ka lane me koi jagah nahi.

LANE MAP: photo_banao photo side, photos_upload/photos_albums user
library side, hoola_frames film side - stock library in sab ko FEED
karti hai, inki jagah nahi leti. app/mediafind.py module lane catalog
lookup me madadgar hai; video lanes (video_edit, video_studio) already
encode karte hai, unhe clip dena hamara kaam hai.

THE FLOW (har asset ke liye, order same):
1. CATALOG PICK: need likho - subject, mood, orientation. Catalog me
   matching source dhundo; photo, video, music, SFX sab alag-alag
   source hote hai. 2-3 shortlist karo, pehla mila to ruk nahi jana.
2. LICENSE PEHLE: asset khinchne se pehle uska license padho. CC0 =
   free, attribution optional; CC-BY = creator + source line DENI
   HI ZAROORI. Doubt ho to skip, agla source. Result memory_search/
   remember me note - agli baar wahi sawal dobara na uthna pade.
3. FETCH: direct URL mila to crawl_start/web_sources se lao; source
   API deta hai to api_call. File tenant ke andar rahegi - bahar
   koi upload nahi.
4. PREP: photo_assist se crop/scale, photo_clean se background aur
   noise theek - raw dump seedha template me nahi jata.
5. USE: photo_banao me lagao; hoola_frames films me clip ya track
   banao; album me tag ke saath rakho (subject + source).
6. LEDGER: har asset ke saath license line saved - source, creator,
   license, date, file path. Ye line printed output me aani hi
   chahiye; printed hi evidence hai.

THE LAWS: license check kisi bhi asset se PEHLE, download ke baad
nahi; ask_approval publish ya paid stock se pehle - free tier hi
default; user ki private photos bina poochhe stock albums me mix
nahi - tenant ka data tenant me hi rahega.

COMMON TRAPS: watermark dikha to discard, source badlo - "crop karke
chhupa denge" nahi. "Free trial" wale assets commercial template me
kabhi nahi. Kuch sources scraping mana karte hai - unki ToS todna
mana; wahan official API hi. Ek hi source pe atakna bhi galat -
catalog bada hai, badlo.

NEVER: watermarked ya pirated asset use karna; license note ke bina
asset use karna; "free trial" wale assets commercial me lana; source
ki ToS todna (bina permission scraping); CC-BY asset bina attribution
chhapna; license check ke bina "free dikha to free hai" bolna; user
ki private media bina poochhe stock album me mix karna.
