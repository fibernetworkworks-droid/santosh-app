# HOOLA PROMPTING - the moat plan

Owner, 11 Nov 2026: "NEW FEATURE HOOLA PROMPT ENGINEERING SECTION --- A FEATURE NAME HOOLA PROMPTING --- VARIOUS
SECTIONS. PROMPT FOR WEB DESIGN, PROMPT FOR APP DEVELOPMENT, PROMPT FOR SCRIPT ETC ... FIRST DO DEEP RESEARCH HOW THIS
PROMPT ENGINEERING WORKS --- AND PREPARE A ULTIMATE MOAT PLAN FOR HOOLA".

Research (sources for every claim below): `docs/research/prompting/00_INDEX.md`. This is the plan; each phase starts
on her GO. STATE: P0 built as v0.794 (built as 0.785) (the card exists, `python -m app.quality prompt`); no live run yet, so no
numbers (owner: test everything together at the end). P1-P3 built as v0.804 for web / image / script (engine, Improve
button in the console chat box + Web Studio + Create Image, the page /console/prompting); the phone composer button is
not built. P4 (the outcome ledger, NATIJA KHATA) built as v0.816: `prompting/ledger.py`, the Results tab; hooks for web / image /
script / chat; NOT hooked yet: Kalam, video, app; decisions 2-5 of part 7 (question pruning, slot defaults, dialect
alerts, personal defaults) wait for real rows. P5 onwards not started.

## 0. The verdict in seven lines

1. Prompt engineering in 2026 is NOT magic words. "Act as an expert", "think step by step", CAPITALS, tips and
   threats measure as zero or harmful on current models. What makes a prompt work is the INFORMATION in it: who it is
   for, what it must do, real facts, examples, limits, and what "good" means.
2. Every engine (website builder, image, video, music, coding agent) has its own ANATOMY (the parts a good ask must
   have) and its own DIALECT (how that engine wants it said). The vendor's advice changes with every model.
3. Nobody can call a prompt "better" without measuring the result. Every prompt optimiser in the research needs a
   score to work against.
4. The prompt market is dying where it is only text: prompt shops sell at $2-10 and cannot promise a result, the
   standalone optimiser is closing, and an Enhance button is free in every tool.
5. So Hoola must not build a prompt shop or one more rewrite button. Hoola builds the thing the others cannot:
   **a prompt that is tied to the work and its result.**
6. The moat = four things together: (a) the OUTCOME LEDGER - which brief led to a result she kept, published or paid
   for; (b) HER CONTEXT filled in for her (brand, products, prices, city, language); (c) HINGLISH IN, ENGINE-GRADE
   SPEC OUT for Indian business; (d) dialects RE-TESTED by Hoola each time an engine changes.
7. One honest risk: automatic rewriting has been measured making results WORSE. So phase P0 measures first, and no
   phase ships unless its card shows a better kept result, not a nicer-looking prompt.

## 1. What HOOLA PROMPTING is (one paragraph)

A new section of Hoola - its own page `/console/prompting`, a phone screen, and a **Sudhaaro (Improve)** button
inside every place she types an ask. She writes a rough line in Hinglish or English ("Diwali sale ka poster, thoda
premium, gold wala"). Hoola shows **what it understood** as editable chips, fills in what it already knows about her
business, asks at most three questions for what is truly missing, gives a **Prompt Score** worked out in code, and
then either **runs it** in the right Hoola engine or gives her the finished prompt to copy. Every run is recorded
against what happened to the result, and that record decides which recipes and which questions Hoola uses next time.

## 2. The core object: a BRIEF, not a text

Everything in this plan rests on one decision: inside Hoola a prompt is a **structured brief**, and text is only how
it is shown or sent.

```
brief = {
  section:   "web" | "app" | "script" | "image" | ...        (the sections in part 4)
  intent:    her own words, kept exactly
  slots:     { name: {value, source: "her_words" | "her_memory" | "her_answer" | "recipe" | "hoola_guess",
                      locked: bool} }
  facts:     prices, names, phone, dates, offers - ALWAYS locked, never reworded, never invented
  missing:   slots the anatomy needs and nobody has given
  examples:  up to 3 (her own past kept results first)
  must_not:  what must stay / must not appear
  good_when: how the result will be judged (the engine's own checks)
  recipe_id, dialect_version, hash
}
```

Rules that never bend:
- **Her facts are locked.** A price, phone number, name, date or offer she wrote is copied, never rewritten. A fact
  nobody gave is a marked blank, never an invented value (the house rule since Kalam).
- **A guess is labelled a guess.** A slot Hoola filled on its own shows as "Hoola's suggestion" and one tap removes it.
- **Nothing is rewritten silently.** She always sees the brief before it runs; "Run as I wrote it" is always there.
- **A short ask gets help, a full ask is left alone** (auto by how much is missing, not by a fixed rule).
- **No magic phrases.** The compiler never adds "act as", "think step by step", CAPITALS or praise. A test holds this.

## 3. The six machines behind it

| # | Machine | What it does | Built on (already in Hoola) |
|---|---|---|---|
| 1 | **Anatomy registry** `prompting/anatomy/<section>.json` | Per section: the slots, which are required, the one question for each, visual options, the checks that define "good" | `site/taxonomy.py`, `site/designq.py` (v0.784 question cards), `appmaker/ideas.py` keys |
| 2 | **Brief compiler** `prompting/compile.py` | Her words -> slots. Code first (numbers, phone, price, colour, festival, city, language), then ONE cheap model call for the rest, then code checks the answer against her words | `hard.assess`, `research_plan` sizing, `devsahayak.guess_kind`, `architect.wants_plan` |
| 3 | **Context fill** `prompting/context.py` | Fills slots from what Hoola knows: brand kit, business type, city, products + prices, UPI, language, her last kept results in this section | `memory.search_all`, `aboutme`, Create brand kit, shop catalogue |
| 4 | **Dialects** `prompting/dialect/<engine>.py` | Brief -> the exact form each engine wants (scene prose for images; shot / camera / light for video; genre + mood + tempo for music; pages + sections + key action for the website architect; file + symptom + check for Hoola Code). Versioned per engine + model | `studio.improve_brief` (video + image only today), `service.brief_text`, `loop.SYSTEM` |
| 5 | **Outcome ledger** table `prompt_runs` | One row per run: brief hash, recipe, section, engine, model, rupees, seconds, and what happened next - kept / published / sent / downloaded / edited / regenerated / deleted / her thumb | `usage.run_meter`, `create/jobs.keep`, site versions, `feedback/` |
| 6 | **Prompt card** `quality/promptcard.py` | The measure: fixed rough asks per section, run raw vs through the brief, scored by the checks each engine already has + her verdict | `quality/` cards, Design Arena, hard card, code card |

Why this is hard to copy: machines 1, 2 and 4 any competitor can write. Machines 3, 5 and 6 need a product that
holds her business context, runs the work itself, and has already built scoring for its own engines. Hoola has all
three today; a prompt shop has none.

## 4. The sections

Each section = one anatomy + one or more dialects + a recipe shelf + its own "good when" checks. Order = build order.

| # | Section | Anatomy (what a complete ask has) | Runs in | "Good" is measured by |
|---|---|---|---|---|
| 1 | **Web design** | what it is, who visits, the ONE key action, pages + sections, style direction, brand facts, real content, states (empty / error), what must not change | Web Studio architect | site gates, look check, Arena judge, published or not |
| 2 | **App development** | users + roles, the main job of each, lists + fields, rules, money, notifications, offline, what must work on day 1 | App Studio (naksha) | naksha checks, Pillar J story tests, build passes |
| 3 | **Script** (reel, ad, video, YouTube, podcast) | platform + length, audience, hook, one message, proof / facts, call to action, tone, language mix | Create script writer, Kalam | length fit, facts present, hook in first 3 s, kept or rewritten |
| 4 | **Image and poster** | subject, action, place, composition, style, light, exact words on it + script, size, brand colours | Create Image, image_edit | text rendered right, brand colour used, kept / regenerated |
| 5 | **Video** | per shot: subject, one action, one camera move, light, style; dialogue apart; length + size as settings | Create Video, Director, Frames | price first, takes per kept clip |
| 6 | **Music and voice** | genre, mood, instruments, tempo, vocal style + language, lyrics with sections, what to leave out | Create Music, Voice | kept / regenerated |
| 7 | **Marketing messages** (WhatsApp, email, social, ads) | audience, offer + facts, one action, channel rules (template category, length), tone, opt-out | campaigns, email, Social desk, Ads desk | channel checks pass, sent on her tap, replies |
| 8 | **Business documents** (proposal, quote, letter, report, policy) | reader, purpose, facts + numbers, structure, tone, length, format | doc_studio, HOOLA PRINT | QA pass, kept without edits |
| 9 | **Coding** | repo, file, symptom, what "fixed" means, the check to run, rules to follow, what not to touch | Hoola Code | CI green, own review clean, merged |
| 10 | **Research and analysis** | question, sub-questions, sources to trust / avoid, as-of date, the form of the answer | research_run, pylab | claims supported, her verdict |
| 11 | **Data and sheets** | the data, the question, the output (table / chart / formula), checks | pylab, data desk, Sheets | numbers recomputed |
| 12 | **AI employee / AI app** (the prompt for an assistant that answers HER customers) | role, what it knows, what it must never say, actions allowed, tone, hand-off rule | HOOLA AI APPS soul, business inbox | soul checker, answered vs unknown rate |
| 13 | **Everyday chat** (anything else) | goal, context, form of the answer, example | the chat itself | Good answer / Not right |

A fourteenth shelf, **For other AI tools**, exports any brief in the dialect of ChatGPT, Claude, Gemini or an image
tool she uses outside Hoola (copy only). It brings people in; the page says plainly that Hoola cannot follow a result
it did not make. Dialects for outside tools are written only from the vendor's own published guide.

## 5. The page, screen by screen (`/console/prompting`, its own page like Flow and Hoola Code)

Sidebar: Home / the sections / Recipes / My prompts / Compare / Learn.

1. **Home.** One box: "What do you want to make?" + section chips. Below: Continue (her last briefs), "Worked for
   businesses like yours" (recipes ranked by kept rate for her business type - shown only once there is data; until
   then "Hoola's starters", said as such).
2. **The workbench** (the heart).
   - Left: her words, always editable.
   - Middle: **What Hoola understood** - a chip per slot, coloured by source (her words / from your business / Hoola's
     suggestion / missing). Tap a chip to change it; locked facts carry a small lock.
   - Under it: **up to three questions**, as cards she can see (the v0.784 card), only for missing required slots.
     Skip is always allowed; a skipped slot stays a marked blank.
   - Right: **Prompt Score** out of 100 with the reasons in words ("Who is it for? missing. The offer has no end
     date."), then the finished prompt for the chosen engine, the **price before running**, and three buttons:
     **Run in Hoola** / **Copy** / **Save**.
3. **Recipes.** A recipe = a brief with blanks. Search, section, business type. Each card shows what it makes, the
   blanks it needs, and - when the ledger has enough runs - "kept 7 of 10 times by shops like yours". No star
   ratings, no likes: only what really happened.
4. **My prompts.** Her saved briefs with versions (every change kept, restore any), blanks she fills each time
   ("this week's offer"), and "Run every Monday" handing the brief to routines. Team sharing inside her business.
5. **Compare.** The same ask as two briefs (or one brief on two engines), **price first**, results side by side, she
   picks; her pick is written to the ledger. Reuses the Create compare card (v0.263) and the Arena duel screen.
6. **Learn.** Short lessons made from HER OWN prompt: "You wrote 'premium'. An engine cannot see premium. Say: black
   and gold, serif heading, lots of empty space." One idea per lesson, before / after from real runs. India pays to
   learn prompting; here she learns by doing her real work.

**Sudhaaro everywhere.** The same engine as a small button in the console chat box, Web Studio and App Studio home
boxes, every Create tool (replacing the two-kind Enhance), Hoola Code's composer and the phone composer. It opens
the understood-chips sheet in place; one tap applies, one tap undoes. In the chat itself there is no extra step for
an ordinary message - only an ask that is big AND missing a required slot gets ONE question (the house rule of
v0.371 / v0.734), never a form.

**On a voice call** nothing changes on screen: the call brain uses the same compiler to ask the one missing thing
aloud ("Kis taareekh tak offer hai?") before a paid job starts.

## 6. The Prompt Score (code, not opinion)

Per section, 100 points from checks a program can run on the brief:
- required slots present (the biggest part);
- facts present where the section needs them (a price for an offer, a date for an event);
- no contradiction between slots (dark theme + "white, airy");
- engine limits respected (length of a clip, characters of a WhatsApp template, words on a poster);
- wording the engine handles badly found and turned round ("no cars" -> "empty street"), shown to her;
- an example or reference present where the section gains from one.

The score is a completeness measure and the page says so: "This counts what is in your prompt. It cannot promise the
result." Phase P4 then checks the score against the ledger: if a higher score does not go with a higher kept rate
in a section, that section's weights are changed or the score is removed there. A score that does not predict
anything is decoration.

## 7. The outcome ledger and the learning loop (the real moat)

- **Recorded per run:** section, recipe, brief hash, slots by source, engine + model + dialect version, rupees,
  seconds, and the outcome events that engine already emits. Outcome grades: `kept` (published / sent / downloaded /
  merged / used as is), `kept_after_edit`, `redone` (regenerated / asked again), `dropped` (deleted / abandoned),
  plus her explicit thumb.
- **Not recorded:** the text of her facts in any shared table. The shared (cross-business) learning uses only
  shapes: which slots were filled, which recipe, which business type, which outcome. Her words stay in her tenant.
  Incognito chats write nothing. A switch in Profile turns her contribution to shared learning off.
- **What the ledger decides, in code:**
  1. recipe order - kept rate per business type and language, with a minimum number of runs before any number shows;
  2. which questions are worth asking - a slot whose answer does not change the kept rate stops being asked;
  3. default choices per slot for her business type ("salons that kept their poster chose 4:5");
  4. dialect health - a drop in kept rate after an engine or model change raises an owner alert;
  5. her personal defaults - what SHE always changes becomes her standing preference (joins v0.615 corrections).
- **Four numbers the whole feature is judged by:** kept rate, redos per kept result, rupees per kept result, minutes
  to the first kept result. Shown on an owner page; improved or the phase is not done.

## 8. Dialects kept honest

- One dialect file per engine, written from that vendor's OWN current guide, with the source link and date at the top.
- Each dialect carries a version; every ledger row stores it.
- `python -m app.quality prompt --section image` re-runs the section's card; a new engine or model is not made the
  default for a section until its card runs (the rule the Create price list and model profile already follow).
- Model-specific facts live here and nowhere else (for example: no forced reasoning tags and no prefill on current
  Claude models; clip length is a setting, not a word, on video engines; negatives as a list on Veo).

## 9. Safety walls

- A recipe or a shared prompt is **data, never instructions**: it can fill a brief, it can never call a tool, send,
  pay, delete or change a setting. Anything that sends or spends still goes through the same card and her tap.
- Shared recipes (team now, community only on her later word) are screened on entry: hidden instructions, links,
  asks for secrets, and blanks that would collect a password / OTP / card number are refused.
- Her variables are passed as marked data, not pasted into instruction text.
- Keys, passwords, OTPs never go into a brief (the existing masks apply); ID numbers stay as locker references.
- The existing refusals stay per engine (no real person's face without consent, no watermark removal, no fake
  reviews, no invented prices or awards). A recipe cannot switch one off.
- No scraping of other prompt sites, no copying of their prompts. Recipes are written by Hoola or by her.

## 10. What we deliberately do NOT build

| Not built | Why |
|---|---|
| A prompt shop selling prompt files | commodity at $2-10, copied in a second, breaks with each model, no result promised |
| A developer prompt-ops product (versions, traces, eval suites for engineers) | the labs and data companies have absorbed that market |
| Magic-phrase boosters | measured as useless or harmful on current models |
| A silent auto-rewrite | measured to cut quality; loses her details and her trust |
| Likes / stars on recipes | they measure popularity; the ledger measures what was kept |
| Paying creators per download | if a community comes, pay on kept results - the one thing a shop cannot measure |

## 11. Phases (each = one version, tests + a measured card, starts on her GO)

| # | Name | What ships | Proof |
|---|---|---|---|
| P0 | **NAAP** (measure first) | `quality/promptcard.py`: 20 rough asks per section for web, image, script (60), in Hinglish + English, each run raw and through a hand-built brief; scored by the engines' own checks + her verdict. Free `--check` mode, live mode with a rupee ceiling | the numbers: does a complete brief beat her raw line, by how much, per section. A section with no gain is dropped or rethought BEFORE it is built |
| P1 | **SAMJHA** (understood) | brief object + anatomy registry + compiler + context fill for web, image, script; `POST /api/prompting/understand`, `/score`, `/compile`; the no-magic-phrase + locked-facts tests | compiler card: slots right on the P0 asks; a locked fact never changes (test) |
| P2 | **SUDHAARO** (improve, everywhere) | the button + chips sheet in console chat, Web Studio, Create (replaces Enhance), phone composer; one question only for a big ask with a required slot missing | browser walks; undo restores her words byte for byte |
| P3 | **PROMPTING PAGE** | `/console/prompting`: home, workbench, score, Run in Hoola / Copy / Save, recipes shelf (starters from the 1,00,000 web templates + app ideas + new image / script recipes), sidebar row | browser walk light + dark + phone |
| P4 | **BAHI** (the ledger) | `prompt_runs`, outcome hooks in Web Studio / Create / Kalam, the four numbers page, recipe order from kept rate, score checked against outcomes | hooks tested per engine; privacy test (no fact text in shared rows; incognito writes nothing) |
| P5 | **SAB SECTION** | anatomy + dialect + recipes + checks for app, video, music, marketing, documents | P0 card extended to each; ships only where it gains |
| P6 | **KAAM KE SECTION** | coding, research, data, AI employee / AI app, everyday chat | same |
| P7 | **MERE PROMPT** | saved briefs, versions, blanks, team sharing, run on a schedule | restore + schedule tests |
| P8 | **MUQABLA** (compare) | two briefs / two engines side by side, price first, her pick to the ledger | cost shown before run (test) |
| P9 | **SEEKHO** (learn) | lessons from her own prompts + real before / after | her read |
| P10 | **KHUD SEEKHE** (self-improving) | the ledger changes questions, defaults and recipe text: Hoola proposes a recipe change, the card must show a gain, an owner tap accepts (the research's optimiser loop, with a real metric) | a proposed change that does not gain is refused (test) |
| P11 | **BAHAR + SAMUDAAY** (on her word only) | export dialects for outside AI tools; public recipe pages for search; community recipes with screening and pay-on-kept | screening tests; her decisions in part 12 |
| P12 | **PROOF** | the P0 card again on everything + ten real users' four numbers before / after | the table |

Order logic: P0 decides whether and where this is worth building. P1-P3 give her the feature. P4 starts the data
that makes the moat - the earlier it starts, the longer the lead. P5-P9 widen and finish. P10 is where the lead
becomes hard to catch. P11 is growth and needs her decisions.

## 12. Decisions only the owner can make

1. **Name on screen**: "Hoola Prompting" for the page (assumed) and "Sudhaaro" or "Improve" for the button. The
   console is English since v0.728, so "Improve" is the default unless she wants the Hindi word as the brand.
2. **Price**: understanding + score are one cheap model call (well under Rs 1). Free and unlimited, or a daily free
   count? Recommendation: free - it reduces wasted paid runs, which is what users actually resent.
3. **Shared learning**: may the shapes (never the words) of one business's kept runs improve recipes for others?
   Default proposed: on, with a clear switch in Profile, and off for incognito.
4. **Outside-tool export (P11)**: give finished prompts for ChatGPT / Midjourney and others, knowing some users will
   take the prompt and leave? Recommendation: yes for copy, since "Run in Hoola" is one tap closer and tracked.
5. **Community (P11)**: open recipes from other users at all? Only after P4 has real numbers.
6. **First three sections**: this plan assumes web, image, script (highest use + checks already exist). Her call.

## 13. Not verified, said plainly

- Nothing here is built or measured. Whether a compiled brief beats her raw line IN HOOLA's engines is unknown until
  P0 runs; the research found cases where rewriting hurt.
- The claim "no Hinglish prompt product exists" = none was found in one day's search, not proof.
- Market prices, traffic and the PromptPerfect closing date come from secondary sources.
- Midjourney, Runway, Suno and Kling official guides could not be opened; their dialects must be read from the
  primary page before P5 / P11 writes them.
- The kept-rate numbers need volume. With few users a recipe's "kept 7 of 10" will be thin for months; the page must
  show starters as starters until then.
- The Prompt Score may not predict outcomes; P4 tests that and may remove it.
