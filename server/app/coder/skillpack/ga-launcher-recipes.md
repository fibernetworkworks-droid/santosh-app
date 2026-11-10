---
name: ga-launcher-recipes
description: Steam/Deck recipes - launch, notes, playtime, approval
when_to_use: steam, steam deck, game launcher, game settings, launch options, controller, playtime, pc game not working
---
GOAL: Hoola launcher me har game apni RECIPE CARD ke saath khulta hai
- launch path, flags, controller notes, known fixes - sab memory me.
Syllabus: Steam/Steam Deck ke curated community lists (SteamDB,
PCGamingWiki style) - ye SEARCH TERMS hain ("proton rating",
"controller support"), invented version numbers memory se nahi.

RECIPE CARD (per game - remember se save, memory_search se wapis):
- launch path + executable + working dir
- flags: ek flag ek line, saath me kyun (e.g. borderless force)
- controller notes: mapping, deadzone, deck-style layout
- fixes: "alt-tab pe crash -> ye karo" jaise one-liners
Card zinda document hai - naya seekho to turant update karo; game ki
history launcher ke paas hi rahegi, tenant se bahar nahi jayegi.
Naya flag jo kaam kare aur jo fail kare - dono lines likho; sirf
success wali diary agle session me dhokha degi.

LAUNCH FLOW (operator lane asli lane hai):
1. memory_search se recipe card nikalo; naya game ho to user se
   poochh kar pehla card banao.
2. pc_status pe dekho: machine free hai, client chal raha hai, disk
   me jagah hai? Kami ho to user ko batao, khud install mat thopo.
3. open_app ya pc_do se launch - ek turn, ek action.
4. Game window semantically chalao: ax_find (role/name) - "Play",
   "Resume", "Options" naam se milte hain, coordinates se nahi.
   Screenshot sirf tab jab ax jawab na de. Har turn me ek hi screen
   action - stale clicks aur galtiyan dono bachte hain.

DECK-STYLE SOCH: playable-first. Launch se pehle proton note,
controller mapping, performance flags card me likho; session ke
dauran playtime aur naye notes card me update karte raho. "Update
available" dikhe to turant mat chalao - user se poochho, session ke
baad schedule karo. Proton note me sirf wahi likho jo tumne dekha ya
user ne bataya - rating ka andaaz apna nahi. Save files aur playtime
data tenant ke andar hi rahenge. Game window ke andar bhi pehle naam-wala door (ax_find),
pixel click sabse aakhri me.

SESSION CLOSE: khel khatam to sirf window band karna kaam nahi -
card me naye notes likho (remember), playtime update karo, save
backup chahiye to pehle ask_approval. Agli baar memory_search se
wahi card milega aur session wahin se shuru hoga jahan chhoda tha.

NEVER: save-file edit ya config overwrite bina ask_approval ("tumhari
save likh du?"); cracked/pirated build ya DRM bypass - chhoona bhi
nahi; mid-session auto-update ya background download shuru karna;
pixel click jab ax door khula ho; uninstall/cloud-resync jaisa
irreversible step bina ask_approval; bina launch output dekhe "game
chal gaya" bolna.
