---
name: de-naya-pc
description: New PC setup - vetted bundle, visible installs, one pass
when_to_use: new laptop, new pc, set up computer, install developer tools, fresh windows, setup for coding, naya laptop, apps to install
---
GOAL: "Set up my new PC" means ONE vetted bundle, not a pile of random
apps. Syllabus repos: agarrharr/awesome-cli-apps (a curated catalog of
CLI tools), alebcay/awesome-shell (shells, prompts, frameworks),
webpro/awesome-dotfiles (config/dotfiles recipes). Pick from these,
and after the user's approval install in a single visible pass - every
step with printed proof.

RULES:
1. Installs, deletes, paid tools: ask_approval first, act after.
2. Printed output is the evidence - what was not printed did not happen.
3. Semantic doors first: take the truth from pc_status, pc_list,
   pc_read, pc_search, api_find, api_docs; use screenshot/ax_find only
   when no semantic door is available.
4. Private data stays in the tenant - files, history and serial numbers
   do not go outside.

STEPS:
1. SNAPSHOT: print the machine's state with pc_status + pc_list - OS,
   free disk, RAM, what is already installed. This is the baseline;
   without it the plan is blind.
2. CURATED PICK: never take versions from memory. Turn the categories
   into search terms - "productivity", "file manager", "shell prompt",
   "dotfiles manager" - and run pc_search or api_find over all three
   syllabus repos. For each candidate confirm the live version and
   install method with api_docs/api_call. Shortlist 8-12 items, not 50
   - the bundle is curated, not a bazaar.
3. PLAN: print a plain-text plan - what will be installed, where (user
   dir vs system-wide), how much space it needs, whether any step is
   destructive. Easy to read, not a wall of text.
4. APPROVAL: submit the plan with ask_approval. Only after a "yes" does
   the first install start.
5. VISIBLE INSTALL: open the installer/package GUI with open_app so it
   shows on screen. The operator REFUSES to open
   cmd/powershell/terminal/regedit/diskpart (BLOCKED_APPS) - do not even
   think of a hidden terminal shortcut. win+r, win+x, ctrl+shift+esc and
   win+l are refused too (BLOCKED_KEYS). Use only the install door that
   pc_do offers.
6. EVIDENCE: after every step take a printed result - a version check, a
   new entry in pc_list, a screenshot of the GUI. Print a one-line
   result per step, then go to the next.
7. RECIPE SAVE: save the final bundle with remember - items, versions,
   order, quirks (first check memory_search that an old recipe does not
   already exist). Make it repeatable with create_routine - the next new
   PC is ready from the same recipe in one pass.

ORDER: snapshot -> curated pick -> plan -> ask_approval -> visible
install -> printed evidence -> recipe save. No step is skipped, and no
reordering without a new approval.

NEVER: install or delete without approval; run curl | bash blindly
(read the script first via pc_read/api_docs); touch registry or disk
tools (the operator itself refuses under the BLOCKED_APPS law); install
in the background without telling the owner; say "setup is done"
without printed proof; write versions from memory - the live docs are
the truth.
