---
name: mi-bots-research
description: Personas + research + metrics + regex, all printed
---
GOAL: chaar chhoti lanes, ek skill - bot ke personas banana, research
chalana, campaign ke metrics padhna, regex likhna. Syllabus chaar
catalogs: hackerkid/bots (bot design patterns - personas ke shapes
yahan se), typedarray/awesome-research (research tools ka curated
list), onurakpolat/awesome-analytics (analytics ka catalog),
aloisdg/awesome-regex (regex snippets ka collection). Chaaron ka ek
hi niyam: jawab PRINTED hoga - printed output hi evidence, chat ka
andaaz kuch nahi.

LANE 1 - PERSONAS: awesome-bots ke patterns se shape uthao (helper,
notifier, researcher, FAQ...) - har persona ke likho: personality,
tone, kya karega, kya nahi, limits kis topic pe chup rahega, kab
owner ko handoff karega. Persona hoola_make se banao (persona /
personality bundle), par hamesha DISCLOSED bot: pehle message ya bio
me saaf bolo "ye ek bot hai, owner ke naam se nahi bol raha". Owner
ki awaaz me human ban ke baat karna undisclosed bot hai - wo lane
band hai.

LANE 2 - RESEARCH: research-assistant loop, isi order me: pehle
SOURCE LIST printed (shodh se dekho kya nikla, web_sources se sources
kaunse) - phir research_run se deep dive, research_document se
findings likho, research_watch se topic pe lambi nazar, notebook_ask
se apne notes se sawaal-jawab. Har claim ke saath source; bina
source ke finding = gossip, evidence nahi. Findings ka format:
sawaal, jawab, source, date - sab printed.

LANE 3 - METRICS: campaign metrics = bazar_activity (runs, usage,
activity) + youtube_analytics (video side) + seo (search side).
Numbers PRINTED honge, invented nahi: jo number tool ne nahi diya,
wo number hai hi nahi. Format: chhota printed table - metric, value,
source tool, date. Trend bolna ho to do points chahiye, ek nahi.
Campaign shuru se pehle baseline numbers print karo, baad me wahi
tools dobara chalao - tabhi "badha ya nahi" bol payoge.

LANE 4 - REGEX: awesome-regex se snippets uthana allowed, par pylab
TEST ke saath: sample strings + expected match/no-match likho, test
chala ke printed result dekho, pass hua tabhi ship. Regex bina test
= guess; guess ship nahi hota. Test set bhi printed rakho - baad
me wahi cases regress check karenge.

THE LAWS: printed output = only evidence; private data tenant se
bahar nahi (research me bhi - PII/personal wale sources se door
raho); paid ya install wali cheez pehle ask_approval; metrics sirf
tools se, kabhi dimaag se nahi.

NEVER: login-walled source scrape karna (wall ka matlab nahi);
metric invent karna ya bina tool ke "approx" number dena; undisclosed
bot chalana - owner ke naam se bot ki baat karna; regex bina test
ship karna; research ka source nahi batana.
