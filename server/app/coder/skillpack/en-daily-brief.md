---
name: en-daily-brief
description: Daily brief - podcasts/newsletters into one routine
when_to_use: podcasts, newsletters, morning news, daily brief, summary every morning, what to listen, reading list, news digest
---
GOAL: user ka din ek jagah se shuru ho - podcasts aur newsletters
se bana ek chhota morning brief, Hoola khud banake push kare.
Syllabus: rshipp/awesome-podcasts (curated shows, category-wise
catalog) + zudochkin/awesome-newsletters (newsletters ka bada
index). Ye lists sirf DISCOVERY ke liye - asli lane Hoola ke
asli doors se chalti hai, list se kuch bhi "auto-fetch" nahi.

THE FLOW:
1. SOURCES PICK: syllabus lists me se user ke interest ke
   hisaab se 2-3 podcasts + 2-3 newsletters chuno. Lists se
   naam discover karo; free feed default rakhna. Koi bhi paid
   subscription / premium feed = pehle ask_approval ("ye wala
   paid hai, le lu?"). User ke purane pasand memory_search se
   bhi dekho - pehli baar naya setup, har din dobara na poochna.

2. ROUTINE SLOT: create_routine se daily subah ka slot banao
   (jaise 7:30 AM, push delivery ke saath). Pehle list_routines
   se existing routines dekho - overlap nahi hona chahiye. Slot
   miss ho jaye to create_reminder se ek nudge.

3. PODCAST LANE: podcast door se naye episodes uthao (kal ke
   baad wale). Video wale shows ke liye youtube_search, dekhne
   ke liye youtube_watch / youtube_playlist. podcast_dekho se
   chaho to wahin suno bhi. HAR episode poora context me mat
   lo - pehle chhota summary, transcript dump kabhi nahi.

4. EMAIL LANE: email_read se inbox me aane wale newsletters
   dhoondo, email_triage se brief vs baad-me tag karo. Ek hi
   pass me batch karo - har newsletter ko alag turn dena nahi.

5. NOTEBOOK LANE: notebook_create se "Daily Brief" notebook -
   har episode/issue ka 2-3 line summary ek card me. notebook_ask
   se user jab poochhe "abhi kya nikla?", notebook se hi jawab.
   notebook_audio se poore digest ka sunne-layak chhota version
   banao (commute me chalega).

6. DIGEST + PUSH: sab jodke ek screen/page ka digest - top
   headlines, ek podcast pick, ek newsletter quote, 2-3 line
   ka "kal kya tha" recap. push se morning delivery usi slot
   pe. "Brief ready" tabhi bolo jab printed digest saamne ho -
   bina evidence ka claim nahi.

7. CONTINUITY: memory_search se "kal kya tha" - kaunse
   episodes/issues kal aaye the, kaunse adhoore rahe gaye.
   Har din ka digest memory me note karo, taaki agle din ka
   recap khud ban jaye aur sources repeat na ho.

THE LAWS: paid ya subscribe wala kadam = pehle ask_approval;
printed digest = only evidence, uske alawa sab andaaza; user ka
private data (inbox, notes, history) tenant se bahar kabhi nahi
jayega - summaries sirf uske apne notebook, apne push me.

NEVER: bina poochhe paid subscribe karna; poora episode /
transcript context me dalna (summarize karo, dump nahi);
night-time autoplay (podcast_dekho sirf din me, jaagte hue);
sources ki private notes tenant se bahar bhejna; bina printed
digest ke "brief ready" bolna; syllabus lists ke bahar random
source bina poochhe jodna.
