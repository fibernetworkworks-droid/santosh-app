---
name: de-naya-pc
description: Naya PC setup - vetted bundle, visible installs, one pass
when_to_use: new laptop, new pc, set up computer, install developer tools, fresh windows, setup for coding, naya laptop, apps to install
---
GOAL: "Naya PC setup karo" ka matlab EK vetted bundle hai, random apps
ki pile nahi. Syllabus repos: agarrharr/awesome-cli-apps (CLI tools ka
curated catalog), alebcay/awesome-shell (shells, prompts, frameworks),
webpro/awesome-dotfiles (config/dotfiles recipes). Inse curated pick,
user ke approval ke baad, ek hi pass me visible installs - har step ka
printed proof ke saath.

RULES:
1. Installs, deletes, paid tools: pehle ask_approval, action baad me.
2. Printed output hi evidence hai - jo print nahi hua, hua hi nahi.
3. Semantic doors pehle: pc_status, pc_list, pc_read, pc_search,
   api_find, api_docs se sach lo; screenshot/ax_find sirf jab koi
   semantic door available na ho.
4. Private data tenant me rahe - files, history, serials bahar nahi.

STEPS:
1. SNAPSHOT: pc_status + pc_list se machine ka haal print karo - OS,
   disk free, RAM, jo pehle se installed hai. Ye baseline hai; iske
   bina plan andha hai.
2. CURATED PICK: versions memory se kabhi nahi. Categories ko search
   terms banao - "productivity", "file manager", "shell prompt",
   "dotfiles manager" - aur teeno syllabus repos me pc_search ya
   api_find chalao. Har candidate ke liye api_docs/api_call se live
   version aur install method confirm karo. Shortlist 8-12 items, 50
   nahi - bundle curated hai, bazaar nahi.
3. PLAN: plain text plan print karo - kya install hoga, kahan (user
   dir vs system-wide), kitna space lagega, koi step destructive hai
   ya nahi. Padhne me aasan ho, wall of text nahi.
4. APPROVAL: ask_approval se plan submit karo. "Haan" aane ke baad hi
   pehla install start hota hai.
5. VISIBLE INSTALL: open_app se installer/package GUI kholo jo screen
   pe dikhe. Operator cmd/powershell/terminal/regedit/diskpart opens
   REFUSE karta hai (BLOCKED_APPS) - hidden terminal shortcut sochna
   bhi mat. win+r, win+x, ctrl+shift+esc, win+l bhi refused hain
   (BLOCKED_KEYS). Jo install door pc_do de raha hai wahi use karo.
6. EVIDENCE: har step ke baad printed result lo - version check,
   pc_list me nayi entry, GUI ka screenshot. Per step ek line result
   print karo, phir agla step.
7. RECIPE SAVE: final bundle remember me save karo - items, versions,
   order, quirks (pehle memory_search se check karo ki purana recipe
   to nahi hai). create_routine se repeatable banao - agla naya PC
   same recipe se ek pass me taiyar.

ORDER: snapshot -> curated pick -> plan -> ask_approval -> visible
install -> printed evidence -> recipe save. Koi step skip nahi, bina
naye approval reorder nahi.

NEVER: approval ke bina install ya delete; curl | bash blindly chala
na (pehle pc_read/api_docs se script padho); registry ya disk tools
chhoona (BLOCKED_APPS law operator khud refuse karta hai); owner ko
bataye bina background install; bina printed proof "setup ho gaya"
bolna; versions memory se likhna - live docs hi sach hai.
