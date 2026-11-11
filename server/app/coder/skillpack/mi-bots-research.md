---
name: mi-bots-research
description: Personas + research + metrics + regex, all printed
when_to_use: bot persona, regex, regular expression, research a topic, campaign metrics, analytics, survey
---
GOAL: four small lanes, one skill - building bot personas, running
research, reading campaign metrics, writing regex. The syllabus is
four catalogs: hackerkid/bots (bot design patterns - persona shapes
come from here), typedarray/awesome-research (a curated list of
research tools), onurakpolat/awesome-analytics (a catalog of
analytics), aloisdg/awesome-regex (a collection of regex snippets).
All four share one rule: the answer is PRINTED - printed output is
the only evidence, a guess in chat counts for nothing.

LANE 1 - PERSONAS: take a shape from the awesome-bots patterns
(helper, notifier, researcher, FAQ...) - for each persona write:
personality, tone, what it does, what it does not, the topics it
stays silent on, when it hands off to the owner. Build the persona
with hoola_make (a persona / personality bundle), but always as a
DISCLOSED bot: say clearly in the first message or bio "this is a
bot, it is not speaking as the owner". Talking as a human in the
owner's voice is an undisclosed bot - that lane is closed.

LANE 2 - RESEARCH: the research-assistant loop, in this order: first
a printed SOURCE LIST (see what shodh found, which sources
web_sources gives) - then a deep dive with research_run, write the
findings with research_document, keep a long watch on a topic with
research_watch, ask questions of your own notes with notebook_ask.
A source with every claim; a finding without a source = gossip, not
evidence. Findings format: question, answer, source, date - all
printed.

LANE 3 - METRICS: campaign metrics = bazar_activity (runs, usage,
activity) + youtube_analytics (the video side) + seo (the search
side). Numbers are PRINTED, not invented: a number the tool did not
give is not a number. Format: a short printed table - metric, value,
source tool, date. A trend needs two points, not one. Print the
baseline numbers before a campaign starts and run the same tools
again afterwards - only then can you say "it grew or it did not".

LANE 4 - REGEX: taking snippets from awesome-regex is allowed, but
with a pylab TEST: write sample strings + the expected match /
no-match, run the test and look at the printed result, ship only if
it passes. A regex without a test = a guess; a guess does not ship.
Keep the test set printed too - later the same cases check for
regressions.

THE LAWS: printed output = the only evidence; private data never
leaves the tenant (in research too - stay away from PII / personal
sources); ask_approval first for anything paid or any install;
metrics only from tools, never from your head.

NEVER: scrape a login-walled source (a wall means no); invent a
metric or give an "approx" number without a tool; run an undisclosed
bot - a bot speaking as the owner; ship a regex without a test;
leave out the source of research.

ALSO ASKED AS (Hinglish asks this skill answers): bot ka persona banao, is
topic pe research karo, campaign ke numbers dikhao, regex likh do
