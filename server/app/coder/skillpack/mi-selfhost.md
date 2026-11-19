---
name: mi-selfhost
description: Self-host lens - alternatives first, free tiers next
when_to_use: self host, open source alternative, free alternative, free tier, cheaper tool, replace paid software, saas alternative
---
GOAL: whenever Ainewtika needs a new tool, first ask - "why buy it at
all?" The syllabus is two catalogs: awesome-selfhosted/awesome-selfhosted
(a curated catalog of self-hosted software - every category, with
licenses) and ripienaar/free-for-dev (a big list of free tiers for
developers). The first catalog is Ainewtika's SELF-HOST lens - look at
the whole category through it before looking at any SaaS. The second
finds savings on our own infra costs - when hosting looks heavy, look
for a free tier there. The order is always: self-host option, then
free tier, then paid.

TWO QUESTIONS (for every tool need, in this order):
1. Is there a SELF-HOSTED alternative? Use awesome-selfhosted as a
   lens - whatever the need is ("notes app", "analytics", "file
   sync"), open its category and pick 2-3 names. If one fits, read
   the LICENSE (MIT / GPL / AGPL - the license itself says whether
   embedding is allowed) and write a DATA-EXIT note: where our data
   will live and how it comes back out (export format, DB dump,
   API). A tool with no exit is lock-in, even when it is free. A
   recommendation always goes out with the license + data-exit note.
2. Is the FREE TIER enough? Self-hosting is heavy - a server,
   updates, backups, a person's time. Look at the same category in
   the free-for-dev list: the limits (requests / storage / users),
   the lock-in, when it asks for a credit card. Decide "enough" from
   numbers: write the current need + 6 months of growth, then
   compare with the limit. Saying "it will do" from a guess is not
   allowed.

INTEGRATION (once both answers are printed):
find related skills / tools with bazar_find, check MCP servers with
bazar_mcp (if the self-hosted tool has an MCP wrapper, integration
is free and clean), then run a small smoke test with bazar_run -
"install + one call + one printed output" - and only then take it
into the stack. Do not say "it works" without bazar_run; printed
output is the truth, not chat talk.

RECOMMENDATION FORMAT: a short PRINTED comparison - at most 3
options, each row with: license, data exit, effort (hours to
install / run / back up). Give the free-tier option a row too
(license = "hosted TOS"). Below it a one-line verdict: "Chose X
because Y" - calling anything the "best tool" without comparing is
not allowed. This printed table is the evidence.

THE LAWS: ask_approval before anything paid or any install
(self-hosting is an install too); printed output = the only
evidence; private data never leaves the tenant - for a new host,
approval first, then migration, never the other way round.

NEVER: suggest a cracked / pirated tool, however cheap the
"shortcut" looks; send tenant data to a new host without approval;
self-host money lanes (payment / billing) without a backup +
rollback plan; recommend a tool without reading its license - an
unknown license is an unknown liability; say "best tool" with only
one option - without 3 comparison rows a recommendation is not
valid.

ALSO ASKED AS (Hinglish asks this skill answers): iska free ya sasta
alternative batao, khud host kar sakte hain kya, paid tool hatana hai
