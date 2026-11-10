---
name: mi-selfhost
description: Self-host lens - alternatives first, free tiers next
---
GOAL: Ainewtika ko jab bhi naya tool chahiye, pehle ye poochho -
"khareedna hi kyun?" Syllabus do catalogs hain:
awesome-selfhosted/awesome-selfhosted (self-hosted software ka curated
catalog - har category, license ke saath) aur ripienaar/free-for-dev
(developers ke liye free tiers ka bada list). Pehla catalog Ainewtika
ka SELF-HOST lens hai - SaaS dekhne se pehle poori category uski
aankh se dekho. Doosra apne infra costs ka finder hai - jab host
karna bhaari lage to wahan muft tier dhundo. Order hamesha yahi:
self-host option, phir free tier, phir paid.

DO SAWAAL (har tool-need pe, isi order me):
1. SELF-HOSTED alternative hai? awesome-selfhosted ko lens ki tarah
   use karo - "notes app", "analytics", "file sync" jo bhi need hai,
   uski category kholo aur 2-3 naam uthao. Mili to LICENSE padho
   (MIT/GPL/AGPL - embedding me chalega ya nahi, ye license hi
   batata hai) aur DATA-EXIT note banao: hamara data kahan rahega,
   wapas kaise niklega (export format, DB dump, API). Jo tool exit
   nahi deta wo lock-in hai, chahe muft ho. Recommendation hamesha
   license + data-exit note ke saath jayegi.
2. FREE TIER kaafi hai? Self-host bhaari hai - server, updates,
   backup, ek insaan ka time. free-for-dev list me wahi category
   dekho: limits (requests/storage/users), lock-in kya hai, credit
   card kab mangega. "Kaafi hai" ka faisla numbers se: current need
   + 6 mahine ka growth likho, phir limit se milao. Andaaz se
   "chalega" bolna mana hai.

INTEGRATION (dono sawaal ke jawab print ho gaye to):
bazar_find se related skills/tools dhundo, bazar_mcp se MCP servers
check karo (self-hosted tool ka MCP wrapper mila to integration muft
aur saaf hai), phir bazar_run se chhota smoke test - "install + ek
call + ek printed output" - tabhi ise stack me lo. Bina bazar_run
ke "chalega" mat bolo; printed output hi sach hai, chat ki baat nahi.

RECOMMENDATION FORMAT: chhota comparison PRINTED - max 3 options,
har option ki row me: license, data exit, effort (install/run/backup
ka kharcha ghanton me). Free-tier option ko bhi row do (license =
"hosted TOS"). Neeche ek line ka verdict: "X chuna kyunki Y" -
compare kiye bina "best tool" bolna mana hai. Ye printed table hi
evidence hai.

THE LAWS: paid kuch bhi ya install (self-host bhi install hai)
karne se pehle ask_approval; printed output = only evidence; private
data tenant se bahar nahi jayega - naya host pehle approval, phir
migration, kabhi ulta nahi.

NEVER: cracked/pirated tool suggest karna, chahe sasta "shortcut"
lage; tenant data naye host pe bina approval bhejna; money lanes
(payment/billing) ka self-host bina backup + rollback plan ke;
license padhe bina kisi tool ko recommend karna - anjaan license
anjanI zimmedari hai; "best tool" ek hi option ke saath bolna - 3
comparison rows ke bina recommendation valid hi nahi.
