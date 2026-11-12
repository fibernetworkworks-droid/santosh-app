---
name: de-naya-pc
description: New PC setup - vetted bundle, visible installs, one pass
when_to_use: new laptop, new pc, set up computer, install developer tools, fresh windows, setup for coding, naya laptop, apps to install
---
GOAL: "Set up my new PC" means ONE vetted bundle, not a random pile of
apps. Syllabus repos: agarrharr/awesome-cli-apps (curated catalog of
CLI tools), alebcay/awesome-shell (shells, prompts, frameworks),
webpro/awesome-dotfiles (config / dotfiles recipes). Make a curated
pick from these and, after the user approves, install it visibly in
one pass - with printed proof of every step.

RULES:
1. Installs, deletes, paid tools: ask_approval first, action after.
2. Printed output is the only evidence - what was not printed did
   not happen.
3. Semantic doors first: get the facts from pc_status, pc_list,
   pc_read, pc_search, api_find, api_docs; use a screenshot / ax_find
   only when no semantic door is available.
4. Private data stays in the tenant - files, history and serial
   numbers never leave it.

STEPS:
1. SNAPSHOT: print the machine's state with pc_status + pc_list - OS,
   free disk, RAM, what is already installed. This is the baseline;
   without it the plan is blind.
2. CURATED PICK: never take versions from memory. Turn categories
   into search terms - "productivity", "file manager", "shell
   prompt", "dotfiles manager" - and run pc_search or api_find over
   the three syllabus repos. For each candidate confirm the live
   version and install method with api_docs / api_call. Shortlist
   8-12 items, not 50 - a bundle is curated, not a marketplace.
3. PLAN: print a plain-text plan - what will be installed, where
   (user directory vs system-wide), how much space it needs, whether
   any step is destructive. Easy to read, not a wall of text.
4. APPROVAL: submit the plan with ask_approval. The first install
   starts only after a "Yes".
5. VISIBLE INSTALL: use open_app to open the installer / package GUI
   so it shows on screen. The operator REFUSES to open cmd /
   powershell / terminal / regedit / diskpart (BLOCKED_APPS) - do
   not even think of a hidden terminal shortcut. win+r, win+x,
   ctrl+shift+esc and win+l are refused too (BLOCKED_KEYS). Use only
   the install door pc_do offers.
6. EVIDENCE: take a printed result after every step - a version
   check, the new entry in pc_list, a screenshot of the GUI. Print
   one result line per step, then move to the next step.
7. RECIPE SAVE: save the final bundle with remember - items,
   versions, order, quirks (first check with memory_search that an
   older recipe does not exist). Make it repeatable with
   create_routine - the next new PC is ready in one pass from the
   same recipe.

ORDER: snapshot -> curated pick -> plan -> ask_approval -> visible
install -> printed evidence -> recipe save. Skip no step, and do not
reorder without a new approval.

NEVER: install or delete without approval; run curl | bash blindly
(read the script first with pc_read / api_docs); touch registry or
disk tools (the operator itself refuses under the BLOCKED_APPS law);
install in the background without telling the owner; say "setup is
done" without printed proof; write versions from memory - only the
live docs are true.

ALSO ASKED AS (Hinglish asks this skill answers): naya laptop ya naya PC
setup karo, coding ke liye ready karo, zaroori apps install kar do, office
ka naya computer
