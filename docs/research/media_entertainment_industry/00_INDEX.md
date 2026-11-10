# The media & entertainment industry across the world - AI Employees register

Owner's ask (5 Nov 2026): *"NOW A MEDIA AND ENTERTAINMENT INDUSTRY AI EMPLOYEES"*. Twentieth in the series. Media and entertainment here means:
news and journalism (print, digital, agencies), television and radio, OTT and video platforms, music, podcasts and audio, book/magazine/comic
publishing, advertising, PR and brand content, social media and the creator economy, live entertainment (concerts, theatre, comedy, festivals),
games and interactive media, animation and VFX studios, and the rights, regulation, platform-trust and audience sides around them. **Film production
has its own register** (`film_industry/`, FI#, 122 roles): this one covers the rest and cross-references film instead of repeating it.

**12 fields, 137 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Laws and codes named are from memory
  and **must be re-checked on primary text per country** before any desk is built: in India the IT Rules 2021 (digital media ethics code, grievance
  officers, takedown timelines), Press Council norms, Cable Television Networks Act and Programme/Advertising Codes, MIB uplink/downlink guidelines,
  Copyright Act (assignment, moral rights, statutory licences, collecting societies such as IPRS/PPL), defamation and contempt law, personality/
  publicity rights case law, CCPA guidelines on endorsements and dark patterns, ASCI code, DPDP Act 2023, the 2025 online-gaming law; abroad DMCA and
  safe-harbour, EU DSA/DMA, the EU AI Act's transparency duties for synthetic and deepfake content, C2PA provenance, GDPR, Ofcom/FCC rules, shield
  laws and libel regimes, platform terms and monetisation policies.
- **Already in Hoola** (extend, do not rebuild): **Kalam** (writing; destinations incl. the site blog and publish-on-her-Haan), the blog engine (`site/blog.py`
  with scheduled posts, categories, RSS, BlogPosting schema), the **Social Media Manager** (Instagram/Facebook/LinkedIn/YouTube; content calendar, approved-post
  publishing, inbox with drafts from her facts, pulse, growth), the **Ads desk** (Meta Ads and YouTube/Google Ads drafts -> check -> create PAUSED -> start on her
  confirm), **Create Studio** (Image, Video + Director, Music via Lyria, Voice, Dubbing, Editor, Script writer, AI casting, Brand kit, My creations), HOOLA FRAMES and
  Avatar Films, the **Game Desk** and Game Crew (49 roles), SEO employee (audits, schema, content plans), HOOLA PRINT (designed PDFs), Doc Studio, Notebook, the research
  engine with citations and verified-claim checks (R0-R9 research suite), `scrape` lane (SSRF/robots-safe), MoSPI facts, WhatsApp opt-in campaigns, voice stack in
  Indian languages, website builder, Dubbing, captions. Roles with `*` exist in some form.

## The findings that shape every media & entertainment desk
### 1. Editorial, creative and legal accountability belong to named people; the AI is the assistant, never the publisher
Ladder as before: **A** admin/prepare, **B** assist (research / draft / check / format for a named person), **C** reserved.
Reserved here: publishing a factual claim to the public (the editor or publisher's decision), naming a source or revealing a confidential one, legal
sign-off on defamation/privacy/contempt risk, headline/photo choices on sensitive stories, takedown and moderation decisions with legal effect,
licence grants and royalty settlements, advertising claims sign-off, the use of any real person's face, voice, name or likeness (consent first),
live broadcast control, and any statement attributed to a person who did not say it. **The AI researches, drafts, formats, monitors and reminds; the
editor, producer, artist, rights holder and lawyer decide.**

### 2. Trust is the product: verification, provenance and honest labels
Deepfakes, AI-generated news sites, fake reviews, clickbait and engagement-bait erode audience trust. The register therefore puts **verification and
provenance first**: every claim traced to a source the journalist can open, every AI-generated asset labelled and carrying provenance metadata (C2PA-style),
every image checked for manipulation, and no AI-written text published as "reported" without a human editor. Hoola's research engine (claims check,
figure check, cited sources) is the right backbone.

### 3. The economy is attention, rights and platform dependence
Advertising/subscription/licensing revenue, platform algorithm shifts, rights windows and collecting societies, creator payouts, takedown wars, and
piracy. The AI's value is in **time (production speed), money (yield, rights, ad quality), and safety (legal and brand risk)**: transcription, repackaging
into formats, localisation, metadata and discovery, rights and royalty tracking, ad ops, community management and audience analytics.

### 4. Creators and workers need protection from the AI too
Musicians, voice actors, illustrators, writers, translators, journalists and moderators face displacement and consent problems. Hoola's rules: consent and
compensation registers for any voice/face/style clone, no training on unlicensed work, credit and attribution, and no replacement framing in marketing. The
film register's **digital-replica consent registry** is the shared foundation here too.

### 5. Local language and local context are the edge
India's media is 22+ languages with huge regional audiences; local news, radio, devotional and folk content, regional OTT and Reels creators are
underserved by English-first tools. Voice-first, translation, transliteration, Hinglish and dialect handling, and low-bandwidth delivery are product features.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)
Seats: [N] newsroom/journalist, [B] broadcaster/OTT/radio, [M] music/audio/podcast, [P] publisher/author, [C] creator/influencer, [D] advertiser/agency/PR, [L] live events/venues, [R] rights/legal/platform/regulator, [A] audience.

### 1. News & journalism  [N]
1. Newsroom Research Assistant - background briefs on a story: timelines, prior coverage, key figures, public records, official statistics (MoSPI), with source links and dates; **reporter verifies** - A - reporter
2. Fact-check Assistant - claim extraction, source tracing, reverse image/video checks via lawful tools, cross-source comparison, confidence and gaps stated; **editor decides the verdict** - B - fact-checker
3. Source & Document Analyst - reads PDFs, court filings, budgets, reports and spreadsheets (pylab), highlights newsworthy figures, flags errors; derived numbers are shown with working - B - investigative reporter
4. Transcription & Interview Assistant - multilingual transcripts with speaker labels, quotes with timestamps, summaries; **reporter checks quotes against audio before publishing** - A - reporter
5. Draft Writer (wire-style) - first drafts from verified notes and structured data (sports results, markets, weather, elections tallies) in the house style; labelled and edited by a human - B - sub-editor
6. Copy Editor - grammar, style guide, headline options, consistency, Hinglish/regional spelling, readability, legal red-flag phrases for lawyer review - B - copy editor
7. Headline & SEO Assistant (accuracy-first headlines, no clickbait, structured data, newsletter subject lines, A/B tests with ethics rules; SEO employee) - B - editor
8. Translation & Localisation Desk (English to regional languages with glossaries, local idiom, cultural checks; back-translation QA) - B - translator / editor
9. Data Journalism Assistant (datasets cleaning, charts, maps, small interactives, methodology boxes; pylab and Data Desk) - B - data journalist
10. Visual Desk Assistant (infographic drafts, caption writing, image sourcing with licences, alt text; photo manipulation checks; **photo editor chooses**) - B - picture editor
11. News Video Producer (explainer videos, reels from stories with HOOLA FRAMES, subtitles in languages, vertical cuts; accuracy gate) - B - video editor
12. Live Blog & Breaking-news Assistant (source monitoring from official channels, draft updates for the editor, verification checklist before posting; **editor publishes**) - B - news editor
13. Election & Polls Desk Assistant (results feeds from official sources, candidate profiles, constituency data; neutral language; polls methodology notes; **no projections without editor sign-off**) - B - political editor
14. Court & Legal Reporting Assistant (case-status tracking, hearing summaries from records, contempt/sub-judice warning flags; **lawyer reviews risky copy**) - B - legal correspondent
15. Local News Reporter Companion (village/ward reporting: voice notes to stories, photos, council meeting summaries, local government records, RTI drafting; verification steps) - A/B - local reporter
16. Investigations Case Manager (evidence index, timelines, entity graphs from public data, source-protection reminders, secure notes; **no source disclosure**) - A - investigations editor
17. Newsletter & Digest Editor (curation, summaries with links, personalisation by topic; subscriber consent) - A - newsletter editor
18. Newsroom Planning Desk (story budget, assignments, deadlines, resource planning, coverage-gap analysis) - A - managing editor
19. Corrections & Updates Tracker (corrections log, update notices, version history, transparency page) - A - standards editor
20. Source Safety & Digital Security Assistant (secure communication guidance for sources and reporters, phishing drills, device hygiene; threats reported to humans) - B - security lead
21. Press Release Triage (separates news from promotion, extracts facts, contacts, embargo tracking) - A - desk editor
22. News Archive Librarian (tagging, entity linking, rights metadata, search, retrospective story packages) - A - archivist

### 2. Television, radio & broadcast operations  [B]
23. Programming Scheduler (grid planning by audience, rights windows, ad breaks, compliance with programme/advertising codes; **programming head approves**) - B - programming head
24. Broadcast Compliance Monitor (ad-time caps, content-code checks, closed captions, logging of aired content; **compliance officer decides**) - B - compliance officer
25. Playout & Traffic Assistant (ad schedules, spot reconciliation, as-run logs, make-goods; **traffic manager approves**) - A - traffic manager
26. Newsroom-to-Air Producer's Assistant (rundowns, graphics lists, guest bookings, timing, teleprompter text, post-show clips) - A - producer
27. Radio Show Assistant (song logs, ad reads, local news bulletins from verified sources, community announcements in dialects, RJ prep notes) - A/B - RJ / station manager
28. Community Radio Helper (volunteer rota, content calendar, licence reporting, local language bulletins; low-budget) - A - station coordinator
29. Live Event Broadcast Planner (feeds, camera plans, graphics, rights holder clearances, run sheets) - B - outside-broadcast producer
30. Media Monitoring Desk (clips tracking of channels, keyword alerts, sentiment themes, reports; rights-aware) - A - PR / newsroom
31. Archive & Licensing Desk (clip retrieval, rights status, licence quotes) - A - archive manager
32. Anchor & Presenter Preparation Assistant (background, questions, pronunciation guides, fact sheets; **presenter owns questions**) - A - presenter
33. Captioning & Audio-description Producer (live and recorded; quality metrics; **accessibility lead approves**) - B - accessibility lead
34. Broadcast Engineering Assistant (signal logs, equipment maintenance, outage reports, spare parts; **engineers act**) - B - chief engineer

### 3. OTT, video platforms & digital distribution  [B]
35. Content Catalogue Manager (metadata, artwork, languages, ratings, availability windows, taxonomy, QC status) - A - catalogue manager
36. Content Acquisition Analyst (title evaluation from public data, comps, cost per viewing hour models, rights terms; pylab; **commissioners decide**) - B - acquisitions head
37. Recommendation Quality Auditor (diversity, regional representation, bias checks, cold-start fairness, filter-bubble measures; transparent rules) - B - product / trust team
38. Subscriber Care Agent (billing, devices, playback issues, parental controls, refunds within policy; escalates) - A - customer-care lead
39. Churn & Pricing Analyst (cohorts, plan mix, promotion impact, ARPU; fair-practice checks, no dark patterns; pylab) - B - growth head
40. Content Localisation Manager (subtitles/dubs pipeline, vendors, QA loops, cultural consultants, delivery specs; see film register FI#52/53/93) - A - localisation manager
41. Video QC Specialist (technical QC to platform specs, loudness, captions sync, artefacts; timecoded reports) - A - QC supervisor
42. Parental Controls & Content-advisory Assistant (age ratings alignment, advisory text, region-specific rules; **rating decisions by classifier/board**) - B - compliance
43. Creator Programme Manager (partner onboarding, payouts statements, policy education, strikes appeals intake; **policy decisions human**) - A - creator-programme lead
44. Streaming Operations Monitor (QoE metrics, CDN incidents, bitrate ladders; **engineers act**) - B - streaming engineer
45. Anti-piracy Monitoring Assistant (watermark forensics, takedown drafts, evidence packs; **rights holder/legal files**) - B - anti-piracy counsel
46. Audience Insight Researcher (survey design, viewing diaries, qualitative coding, privacy-safe analytics) - A - research head
47. Trailer & Promo Variant Producer (cuts per platform and language from approved footage; no misleading previews) - B - marketing editor
48. Short-video Discovery Curator (hooks, clips, series structure, vertical formats) - B - social video lead

### 4. Music industry  [M]
49. Artist Manager's Assistant (calendar, bookings, riders, contracts tracker, invoices, press kits, social plans, royalties summaries; **artist signs**) - A - artist manager
50. Songwriter's Sketchpad (lyric ideas in regional languages, rhyme/metre help, chord progression suggestions, hooks; **writer authors; AI use disclosed**) - B - songwriter
51. Producer's Demo Assistant (arrangement sketches and demos with Hoola Music engine for temp use; sample clearance checks; label AI generation) - B - producer
52. Mixing/Mastering Preparation Assistant (stems naming, loudness targets, reference comparisons, checklists; **engineer decides**) - B - audio engineer
53. Music Metadata & Rights Registrar (ISRC/ISWC, splits sheets, composer/publisher registrations with collecting societies, cue sheets; **filing by rights holders**) - A/B - publisher
54. Royalty Statement Analyst (reconcile DSP, performance and mechanical royalties, audit flags, split payments calculations; **accounts sign**) - B - royalty accountant
55. Music Release Planner (distribution checklist, pitching calendars, pre-save campaigns, artwork specs, release-day tasks) - A - label manager
56. Music Playlist & Discovery Assistant (listener-side recommendations by mood/language with transparent reasons; artist fairness) - A - listener
57. Live Music Booking Assistant (venues, fees, riders, travel, contracts drafts; **artist/manager sign**) - A - booking agent
58. Classical & Folk Heritage Archivist (recordings cataloguing, lyric transcription in scripts, performers credits, rights tracking; community consent) - A - archivist
59. Music Teacher Companion (practice plans, ear training, notation from audio assistance, repertoire for levels; Guru Sahayak) - A - student / teacher
60. Sample & Voice-clone Consent Guard (checks every generated voice/style against consent and licence registers; **blocks unconsented use**) - B - legal / label
61. Label A&R Analyst (streaming data, social signals, release metrics, regional scene scouting; transparent, no hype scores) - B - A&R

### 5. Podcasts, audiobooks & audio  [M]
62. Podcast Producer's Assistant (episode planning, guest research, outlines, show notes, chapters, transcripts, cross-posting) - A - podcast producer
63. Audio Editor Assistant (noise removal, level matching, filler removal, chapter markers, loudness; **producer approves edits**) - A/B - audio editor
64. Podcast Growth Assistant (titles, descriptions, clips, newsletter, cross-promotion partners, analytics; honest claims) - A - host
65. Audiobook Production Assistant (script prep, narrator scheduling, pronunciation lists, QA listening notes; synthetic narration only with disclosure and author consent) - B - audiobook producer
66. Voice Casting & Narrator Matcher (auditions management, demo comparisons; **director chooses**) - A - casting director
67. Audio Dramas & Regional Storytelling Producer (scripts, sound design cues, multi-voice with consented talent; labelled) - B - producer
68. Dubbing & Voice-over Coordinator (language adaptation, lip-sync timing, talent scheduling, QC; cross-ref film dubbing) - B - dubbing director

### 6. Book, magazine & comic publishing  [P]
69. Manuscript Reader (coverage reports, structure, pacing, market comps, sensitivity flags; **editor decides acquisitions**) - B - acquisitions editor
70. Developmental & Line Editing Assistant (suggestions with tracked changes, consistency of characters/timelines, style notes; **author accepts**) - B - editor
71. Proofreading Assistant (typos, typography, house style, citation formatting, language-specific scripts) - A - proofreader
72. Translation & Rights Desk (rights database, foreign-rights pitches, translation project tracking, glossary control) - A/B - rights manager
73. Cover & Layout Assistant (concept covers, typesetting templates, e-book/print specs, accessibility (EPUB), alt text; HOOLA PRINT) - B - designer
74. Metadata & Discovery Manager (ONIX, keywords, categories, blurbs, A+ content; retailer rules) - A - production editor
75. Author Platform Assistant (newsletter, social, launch calendar, events, reader Q&A; claims honest) - A - author
76. Royalty & Contract Tracker (advances, earn-out, reserves, statements, audit rights; **finance signs**) - A/B - contracts manager
77. Magazine Issue Planner (editorial calendar, features, ad pages, deadlines, printing schedule, circulation numbers) - A - magazine editor
78. Comic/Webtoon Production Assistant (script panels, character sheets, colouring pipeline, episodic schedules, translation; creator credit/consent) - B - comic creator
79. Library & Reader Services Assistant (reading lists, accessibility formats, book clubs, community library programmes) - A - librarian
80. Self-publishing Coach (editing, formats, pricing, distribution, ISBN, copyright registration steps, scam warnings) - A/B - author
81. Plagiarism & Originality Checker (similarity checks with sources; **editor judges**) - B - editor

### 7. Advertising, PR & brand content  [D]
82. Campaign Strategist's Assistant (brief analysis, audience insights, channel mix, budget scenarios, KPIs; pylab) - B - strategist
83. Creative Concept Generator (ideas, taglines, scripts, storyboards in languages with cultural checks; originality search; **creative director chooses**) - B - creative director
84. Ad Copy & Variant Producer (platform-specific copy, headlines, A/B variants with claims check) - B - copywriter
85. Ad Claim & Compliance Reviewer (ASCI, CCPA, platform policy, health/finance/children rules, comparative claims, endorsements disclosure; **legal clears**) - B - compliance
86. Media Planner & Buyer's Assistant (reach/frequency estimates, rate cards, GRP/CPM tables, insertion orders, billing checks; **buyer commits spend**) - B - media planner
87. Programmatic & Performance Analyst (campaign diagnostics, pacing, fraud signals, attribution caveats; platform ad desks: Meta/Google, create paused, start on tap) - B - performance marketer
88. Influencer Campaign Manager (matching, briefs, deliverables, disclosures, payment schedules; **contracts and payments human**) - A/B - influencer manager
89. PR Coverage Tracker & Press Office Assistant (media lists, pitches, embargoes, coverage reports, crisis holding statements for approval) - A/B - PR manager
90. Brand Safety & Suitability Monitor (adjacent content checks, blocklists, incident reports) - B - brand safety lead
91. Brand Voice & Asset Librarian (Brand kit, guidelines checker, template library, version control) - A - brand manager
92. Market Research Assistant (survey design, panels analysis, qualitative coding, competitive tracking with lawful sources) - A - researcher
93. Crisis Communication Assistant (monitoring, fact base, stakeholder messages drafts, Q&A prep; **spokesperson approves**) - B - comms head
94. Agency Operations Assistant (time sheets, project budgets, creative reviews rounds, client approvals, invoices; Khata) - A - agency manager
95. Out-of-home & Local Media Booking Assistant (hoardings, radio spots, local newspapers; proof of display photos, rates comparison) - A - local advertiser
96. Small-business Marketing Copilot (festival campaigns, WhatsApp/Instagram plans, posters, budgets; ASCI-safe claims) - A - shop owner

### 8. Social media & the creator economy  [C]
97. * Social Media Manager (existing) - calendar, approved publishing, inbox drafts, pulse, growth; accounts connected on her tap - B - creator / brand
98. Creator Studio Assistant (idea backlog, scripts, hooks, titles, thumbnails, captions, upload checklists; originality and platform-policy checks) - B - creator
99. Reels/Shorts Editing Assistant (cuts, captions, language overlays, music rights-safe choices, vertical formats) - B - creator
100. Channel Analytics Coach (retention curves, impressions, CTR, audience overlaps; experiments design; honest uncertainty) - A - creator
101. Monetisation & Brand-deal Manager (media kit, rate card, contract checklist, disclosure rules, invoices/TDS reminders, payment follow-ups) - A/B - creator
102. Community Manager (comment triage, FAQs, moderation drafts, superfan programmes; **removals/blocks on the creator's tap**) - B - community manager
103. Copyright & Fair-use Guard (checks samples/clips against licences and claim risk; Content ID dispute draft support; **creator/legal decides**) - B - creator / counsel
104. Collab & Network Matcher (creators with complementary audiences, collab pitches, schedules) - A - creator
105. Creator Wellbeing & Business Coach (burnout signals, schedule realism, taxes/GST basics, contracts red flags, scam awareness; **not therapy**) - A/B - creator
106. Regional-language Creator Toolkit (transliteration, dialect-aware captions, trending local audio (licensed), festival calendar) - A - creator
107. Livestream Producer (run-of-show, overlays, chat moderation prompts, donation tracking compliance, safety plans) - A - streamer
108. Fan Club / Membership Manager (tiers, perks, payments via official gateways, renewals, communications) - A - creator

### 9. Live entertainment & venues  [L]
109. Concert & Festival Production Assistant (stage plots, schedules, vendor lists, permits, safety plans, run sheets; **production manager approves**) - A/B - production manager
110. Ticketing & Box-office Assistant (price tiers, holds, comps, refunds, anti-bot, accessibility; consumer-law checks) - A - box office
111. Theatre Company Assistant (rehearsal schedules, props, costume, script versions, tour logistics, grants applications) - A - stage manager
112. Comedy & Open-mic Organiser (lineups, slot timing, venue booking, audience safety code of conduct; content-boundary policies owned by humans) - A - organiser
113. Event Safety & Crowd Planner (capacity, entry/exit flow, medical posts, emergency plans, weather triggers; **authorities approve**) - B - safety officer
114. Artist Hospitality & Travel Desk (riders, transport, accommodation, per diems; Maps) - A - tour manager
115. Local Cultural Events Promoter (folk festivals, jatra, ramlila, community events: calendars, permissions, sponsors, volunteers) - A - cultural committee
116. Venue Operations Assistant (bookings, technical specs, staffing, maintenance, sound limits compliance) - A - venue manager

### 10. Games, animation & interactive media  [cross-ref]
117. Game Studio Producer's Assistant (milestones, tasks, QA tracking; cross-ref Game Desk and Game Crew) - A - producer
118. Animation Studio Pipeline Assistant (shot tracking, render queues, vendor handoffs; cross-ref film register #66-72) - A - production manager
119. Interactive Story Writer (branching narratives, dialogue variants, localisation; author owns canon) - B - narrative designer
120. Esports Broadcast & Content Assistant (tournament highlights, stats overlays, clips, multilingual; cross-ref sports register #60-61) - A - producer
121. Fan Fiction / UGC Community Moderator (guidelines, rating tags, minors protection prompts; **moderator decides**) - B - moderator

### 11. Rights, legal, platform trust & regulation  [R]
122. Rights & Licensing Registry Assistant (catalogue of works, owners, splits, territories, terms, expiries; consent registers) - A - rights manager
123. Contract Drafting & Clause Assistant (creator, licensing, distribution, commission agreements; clause libraries; **lawyer reviews**) - B - media lawyer
124. Defamation & Privacy Risk Reviewer (flags statements about identifiable persons, sub-judice, privacy, harm; suggests rewriting; **lawyer/editor decide**) - B - legal counsel
125. Provenance & Authenticity Assistant (C2PA-style manifests, AI-generation disclosure labels, deepfake detection leads; **trust & safety review**) - B - trust & safety
126. Platform Trust & Safety Triage (reports intake, policy mapping, queue ordering, evidence packs; **moderators decide**) - B - T&S lead
127. Misinformation Monitoring Analyst (narrative clustering, spread maps, fact-check references; no individual targeting; **editors/fact-checkers act**) - B - research / newsroom
128. IT Rules Grievance Officer's Assistant (complaint intake, timelines, takedown decisions logging, transparency reporting; **officer decides**) - B - grievance officer
129. Regulatory Filing Assistant for Broadcasters/OTT (self-classification, annual returns, periodic reports; **authorised signatory files**) - A/B - compliance head
130. Collecting-society Administration Assistant (member registry, usage reports reconciliation, distribution calculations; **board approves**) - B - society admin
131. Media Policy Researcher (regulation tracking across states/countries, impact briefs with sources) - A - policy analyst

### 12. Audience, education & media literacy  [A]
132. Personal Media Guide (what to watch/read/listen by mood, language, time, family-safe settings; transparent reasons, official sources) - A - audience
133. News Literacy Coach (how to check a viral claim, spot deepfakes, understand sources; for schools and adults; local languages) - A - educator
134. Media Studies Tutor (journalism, film, communication theory, ethics; Guru Sahayak) - A - student
135. Accessibility Companion for Audiences (audio descriptions, simplified text, captions, sign-language resources) - A - audience
136. Kids' Content Safety Assistant (age-fit recommendations, screen-time tools with parent control, ad-free modes; no profiling) - B - parent
137. Fan Community Facilitator (discussion prompts, spoiler management, fan events, charity drives) - A - community

## NEVER an AI Employee (tier C)
Publish a factual claim, headline, image or video to the public as news without an accountable human editor; reveal or guess a confidential
source; clone or imitate a real person's face, voice or likeness without recorded consent, scope and compensation; present synthetic media as
real; write fake reviews, comments or testimonials; make or enable astroturfing; sign licences, royalty statements or contracts; decide
legal risk (defamation, contempt, privacy) or takedowns with legal effect; operate live broadcast control; moderate or ban an account
without a human decision; scrape paywalled/copyrighted work for training or republish it; target individuals for harassment or doxxing;
place ad spend or start campaigns without the owner's explicit confirmation; run political persuasion or disinformation operations.

## Suggested build order
1. **Wave 1 - extend what exists (tier A, creators and small publishers feel it immediately)**: 97, 98, 99, 100, 101, 102, 62-64, 75, 77, 96, 1, 4, 6, 8, 17, 18, 22, 35, 38, 55, 110.
2. **Wave 2 - assist with a named editor/producer**: 2, 3, 5, 7, 9-12, 14, 23, 24, 26, 36, 39-41, 49-54, 69-71, 82-88, 103, 109.
3. **Wave 3 - trust, rights, legal and platform-scale roles**: 13, 16, 20, 37, 42, 45, 60, 65, 85, 90, 93, 122-131 (need lawyers, editors and strict consent/provenance infrastructure).
Fit to Hoola: department **"Media & Entertainment"** beside Film & Media; Kalam, the blog, the Social Media Manager, the Ads desk, Create Studio, FRAMES, Avatar Films,
the research engine and the SEO employee already cover a large part of Waves 1-2 for creators, small publishers and brands - the work is **packaging them into role-shaped employees
(Journalist, Creator Manager, Podcast Producer, Publisher's Assistant) and adding the trust layer** (verification, provenance labels, consent registry). Reuse the digital-replica
consent registry from the film register, C2PA-style provenance tags on every generated asset, approval cards for every publish, ad start, payout and takedown, and WhatsApp opt-in
for newsletters and communities.
**Best first pilots**: (a) a **solo creator / small channel** (97-102) in Hindi/Marathi - fast iteration, social publishing already built; (b) a **local news portal or newsletter**
(1, 4, 6, 8, 15, 17, 2, 14) with strict editor-in-loop and verified research - differentiates on trust; (c) a **small publisher or podcast** (62-64, 69-71, 73-75). Broadcasters, OTTs
and labels come later: rights, engineering, and legal integration are heavy.

## Open questions for the owner
- Which side first: **creators**, **local/digital news**, **small publishers/podcasters**, **agencies and brands**, **live events**, or **OTT/broadcast**? I'd start with creators and a local
  news pilot because the publishing, research and creative engines already exist.
- Editorial red lines: confirm that Hoola never publishes news claims without a named human editor, always labels AI-generated media with provenance, and never imitates a real person's voice or face without
  recorded consent.
- Language and market: which languages first (Hindi, Marathi, Tamil, Telugu, English) and which platforms (YouTube, Instagram, WhatsApp channels)? Platform APIs and policies change; each integration is an assigned maintenance cost.
- Rights and money: confirm Hoola tracks and drafts only, with royalty statements and contracts signed by humans, and that Hoola does not scrape or train on copyrighted media beyond the official-route rule.
- "GO per field" turns any field into a sourced report with IT Rules 2021, Copyright Act, ASCI/CCPA and broadcast codes checked on primary text.
