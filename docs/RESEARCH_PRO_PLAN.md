# RESEARCH LIKE A PRO — any topic, end to end, a document she can hand over

Owner, 3 Nov 2026: *"LETS WORK ON RESEARCH ANY TOPIC LIKE PRO — FULL END TO END — HOOLA WILL DO RESEARCH PERFECTLY
AND GIVE USER A PERFECT RESEARCH DOC. FIND THE LLM MODEL IN WORLD RECENT WHO DO RESEARCH PERFECTLY ON ANY TOPIC —
WE WILL USE THAT APIs for research in hoola"*

Plan only. Nothing is built until she says GO on a phase. Facts about the vendors:
`docs/research/research_apis/00_what_exists.md` (what each vendor offers) and
`docs/research/research_apis/01_techniques.md` (**the exact research technique of each one, one by one**) — both read
from the vendors' own shipped SDKs, because every vendor doc host is blocked from the build sandbox.

---

## 1. Her ask, answered straight

**"Find the model that researches perfectly."** No such model exists, and no honest page can name one. What exists
is **two vendors shipping a deep-research agent** (OpenAI `o3-deep-research` / `o4-mini-deep-research`; Google's
Interactions API with `DeepResearchAgentConfig` and `deep-research-max-preview-04-2026`), **five research-first
search vendors** with a one-call "report with citations" (Parallel — whom Hoola already pays, Exa `/research/v1`,
Linkup `/research`, Perplexity, Valyu), and **Anthropic**, which deliberately ships no such model and instead gives
`web_search` with citations, `web_fetch`, `code_execution` and a **memory tool** for your own loop. Every public
ranking between them is published by a vendor that wins its own benchmark.

So the plan does not pick a winner from a blog. It makes the provider a **swappable engine behind one Hoola research
job**, and then **measures** them on her kinds of topics with a scored card — the same way the coding, tool, hard and
maps cards settled their arguments. The card picks the default, and the number is hers to see.

**"Perfect research doc."** The document is Hoola's, never the vendor's: her sections, her language, every number
carrying its source and date, derived figures computed in `pylab`, and a page that says plainly what could not be
confirmed. A provider that returns prose without usable citations is a draft, not a document.

## 2. What Hoola already has (measured, not assumed)

| Piece | Where | State |
|---|---|---|
| "this is a research ask" signal | `agent/hard.py` (`research_wanted`, the `research` RECIPE line) | works; the recipe already says sub-questions → primary sources → `[n]` + date → `pylab` → PDF |
| sub-agent crew with a research budget | `agent/team.py` (`RESEARCH_RULE`, `team_research_max_steps` / `_max_tokens`, graceful `WRAP_UP`) | works |
| the web | `web_sources` (Parallel, quoted excerpts + links), `google_search`, `open_website`, `browse_web` | works |
| scholarly sources | `app/shodh/sources.py` — OpenAlex, Crossref, arXiv, PubMed, Semantic Scholar, Unpaywall, official APIs only | works, academic only |
| official Indian numbers | `app/mospi.py` (MoSPI's own MCP) | works |
| the honesty gate | `hard.research_check` — refuses a report with no sources, or a link no tool in that run returned | works, but only checks that links EXIST |
| the file | `doc_studio` / HOOLA PRINT (designed HTML → tagged PDF) | works |
| the score | the hard card's research rows: "2+ source links" | **too weak to call anything perfect** |

**The four real gaps**, and they are Hoola's side of the work, not a vendor's:
1. **Nothing measures whether the report is GOOD** — only that it has two links.
2. **No plan she approves before the money is spent.** Google shipping `collaborative_planning` says the industry
   agrees that is the right shape; Hoola already has the plan-card pattern everywhere else.
3. **No long background run.** A serious report is 10–40 minutes of searching; today it rides inside one turn.
4. **No claim-level checking.** A fact's link exists, but nothing re-reads the page to confirm the page says it.

## 3. THE COMBINED ENGINE — one Hoola pipeline, every vendor's technique in it

Owner, 3 Nov 2026: *"COMBINE ALL :: OPENAI, GOOGLE, PARALLEL, EXA, LINKUP, PERPLEXITY, VALYU, CLAUDE ETC — GO DEEP
AND FIND THE EXACT RESEARCH TECHNIQUE USE BY THEM ALL ONE BY ONE — AND GIVE THIS COMBINE RESEARCH POWER TO HOOLA."*

The eight techniques, read one by one from the vendors' own SDKs, are written up in
`docs/research/research_apis/01_techniques.md`. Combining them is **not** calling eight APIs and stapling the
answers together — that pays eight times for the same page and can only be as honest as the loosest vendor. It is
**one Hoola pipeline with ten parts, each part taking the technique whoever does it best**, and the vendors sitting
underneath as interchangeable gatherers (which is what Google itself does: its grounding config ships
`exaaisearchconfig` and `parallelaisearchconfig` beside `googlesearch`).

| # | Part of the pipeline | Technique taken from | What Hoola does |
|---|---|---|---|
| 1 | **SAMAJHO** — read the ask | Linkup `mode` (answer/auto/investigate/research) × `reasoning_depth` S–XL; Perplexity `search_mode` web/academic/sec | score the ask in CODE (as `devsahayak/plan.py` already does for coding): kind, size, corpus, "as of when", and the budget that follows. No model picks the budget. |
| 2 | **PLAN** — her approval | **Google `collaborative_planning`** (plan → her confirm → run) | the question restated, 4–6 sub-questions, where it will look, est. minutes + rupees, on a plan card. Large runs WAIT for her Haan. Her note edits the plan. |
| 3 | **BAANTO** — fan out | **Exa `plan-output: tasks → tasks_instructions[]`**, Parallel `search_queries[]` (3–6 words each), Perplexity `query[]` | one worker per sub-question, each worker carrying a stated **`goal`** (Exa's word) that every later line and citation is tagged with. |
| 4 | **KAHAN DEKHO** — source policy | **Parallel `source_policy`** (+`after_date`), Linkup include/exclude + from/to date, OpenAI `filters.allowed_domains`, Perplexity recency/language, Valyu `search_type` incl. `proprietary` | a declared policy per run: allowed/blocked domains, date window, language, primary-source preference, and `shodh`'s scholarly APIs + MoSPI as the first stop for Indian numbers. The policy is data on the run, never a sentence in a prompt. |
| 5 | **PADHO** — fetch the page properly | **Anthropic `web_fetch`**: `url_sources` (only URLs from approved sources), `max_content_tokens`, citations on the document; Exa `crawl`; Perplexity `search_context_size` | a claim is only "sourced" when the page was actually fetched and the words found in it. **A URL that appeared inside a fetched page is data, never an instruction to go there** — our standing rule, which `url_sources` is the industry's name for. |
| 6 | **GINO** — the arithmetic | OpenAI `code_interpreter`, Anthropic + Google + Valyu `code_execution` | every derived figure computed in **`pylab`** (already built, already wired to hard asks). Never mental maths, never a number the model "remembers". |
| 7 | **SABOOT** — evidence per claim | **Parallel `field_basis`**: per field `reasoning` + `citations{url,title,excerpts}` + **`confidence`** | Hoola's report is written as FIELDS first: each number/claim carries its excerpt, its page, its date and a confidence Hoola can defend — then the prose is written from the fields. This is the gap `research_check` cannot close today. |
| 8 | **LAMBA KAAM** — survive the run | **Google `continuation_token`**, OpenAI `background`, **Anthropic `clear_tool_uses`** (keep N recent tool uses, prune the rest), Valyu per-tool `max_calls` (browser 5 / screenshots 15 / code 10, lowerable only) | the job runs on the durable turn inbox, resumes after a restart with its place, prunes old tool output instead of dying of context, and carries a hard call budget per tool so a run cannot open 200 pages. |
| 9 | **KHARCHA** — the ceiling | **Valyu `data_max_price` + `pricing.cpm` per source**, **Exa itemised `num_pages / num_searches / reasoning_tokens`**, Parallel processor tiers | a `researchbill` built exactly like `mapsbill`: the per-run and per-day rupee ceiling **refuses before the call**, the cost is itemised (pages, searches, tokens, per engine), and `/api/research/usage` shows her what a report cost. |
| 10 | **KAAGAZ** — the deliverable | **Valyu `deliverables`** (pdf/docx/xlsx/pptx/csv), Google `visualization: auto` | her document: sections in her language, one-page summary, tables + charts (`charts.js` / `pylab`), full source list with dates, an appendix of what could NOT be confirmed — through HOOLA PRINT, and as Word / Sheet / Doc when she asks. |
| + | **NIGRANI** — keep it fresh (later) | **Parallel monitors** (`frequency`, snapshot vs event stream), Exa websets | a topic she watches: the report updates itself on a schedule and tells her only what CHANGED. |

**The two rules this combination must not break.** (1) No vendor's text is handed over as Hoola's until that
vendor's terms on storing and re-sharing its output have been READ — the Maps Phase 7 lesson, where a whole designed
feature had to be withdrawn after reading the licence. (2) A provider that cannot return usable citations may draft,
never fill: it feeds part 7, it does not bypass it.

## 4. Build phases

| Phase | What ships | Why here |
|---|---|---|
| **R0 — NAAP (the scorecard first) — BUILT in v0.471, free card green, live card NOT yet run** | a RESEARCH card like the maps / hard cards: ~20 fixed topics in her world (a market size, a rule change, a supplier landscape, a competitor, a tender, a medicine, a school syllabus, a machine spec…), each with **checkable** truths: every claimed number traceable to a fetched page, the primary-source share, dates present, two sources on the key number, a stated uncertainty section, no link the run did not open, the rupee + minute cost, and an Opus judge on usefulness. Free part runs with no money. | **Nothing in this plan may be called "perfect" until this exists**, and it is the only honest way to compare vendors later. |
| **R1 — PLAN PEHLE** (part 1 + 2) — BUILT in v0.472 (typed Haan; no tappable card yet; estimates assumed) | the ask scored in code; over a threshold Hoola answers with a **plan card** first and runs only on her Haan. | Google ships this as a flag; Hoola already has the pattern everywhere else. Her money, her question. |
| **R2 — APNA ENGINE** (parts 3–6) — BUILT in v0.473 (scripted-fake tested; no live run yet) | the Exa-shaped loop in our own code as engine `hoola`: plan → `tasks` → per-goal search + **fetch** + think → re-plan or **stop**, with the source policy as data, `url_sources` discipline, and `pylab` for every derived number. Nothing bought yet. | sets the baseline the paid engines must beat, with code we own |
| **R3 — SABOOT** (part 7) — BUILT in v0.474 (scripted-fake tested; no live run yet) | the report is built from FIELDS: claim → excerpt → page → date → confidence; `research_check` upgraded from "a link exists" to "the page says it"; anything unconfirmable is marked, never dropped. | this is the difference between a research doc and a plausible essay |
| **R4 — LAMBA KAAM** (part 8) — BUILT in v0.475 (fake-tested; no live run, no real restart yet) | background run on the durable turn inbox, resume-with-place, context pruning of old tool output, per-tool call budgets, live step narration with each step's goal. | a real report is 10–40 minutes; today it rides inside one turn |
| **R5 — KHARCHA** (part 9) — BUILT in v0.476 (fake-tested; defaults are guesses, web price unknown) | `researchbill`: per-run + per-day rupee ceiling that refuses pre-flight, itemised cost per engine, `/api/research/usage`. **Ships before any paid engine is switched on.** | the mapsbill lesson: the cap must exist before the spending does |
| **R6 — PARAYA ENGINE** (the vendors) — BUILT in v0.477 for parallel / exa / openai / linkup, OFF by default (perplexity / valyu / gemini not built; nothing answered live; terms + prices unread) | `research_engine`: `hoola` (default) \| `parallel` (the key she already pays for — and the only one with per-field confidence) \| `openai_dr` \| `gemini_dr` (its `collaborative_planning` plan becomes HER plan card) \| `exa` \| `linkup` \| `perplexity` \| `valyu`. Every engine returns into Hoola's own document and through R3's claim check; each has its own ceiling. **Blocked until each vendor's terms are readable.** | her ask, without betting the product on one vendor |
| **R7 — THE RUN-OFF** — BUILT in v0.478 (the card, the table and the rule; never run live, so no table or winner yet) | R0's card run across the engines on the same topics: accuracy, primary-source share, claim-check pass rate, minutes, rupees per report. The winner becomes the default **in the code**; the table is saved and shown. | the honest answer to "which model researches perfectly" |
| **R8 — KAAGAZ** (part 10) — BUILT in v0.479 (PDF / Word / workbook; no Google Doc, no charts in PDF/Word; HOOLA PRINT path not seen) | the document as a product: her sections, summary page, charts, source list with dates, unconfirmed appendix, her brand kit; PDF + Word / Google Doc / Sheet. | "a perfect research doc" is a document, not a chat reply |
| **R9 — NIGRANI (optional)** — BUILT in v0.480 (watch + diff + held review; never run live) | a watched topic: scheduled re-run that reports only what changed; plus the v0.436 held-answer review of a report against its own sources before she sees it. | the last mile, and the thing that makes research a standing employee rather than a one-off job |

## 5. What it will NOT do
- **No scraping.** Only documented APIs and pages a tool actually fetched — the standing rule.
- **No invented source, number or date.** A fact whose page cannot be re-read is marked unconfirmed, not quietly kept.
- **No vendor's report handed over as Hoola's**: if a provider's terms forbid storing or re-sharing its text, that
  provider can draft but not fill the document — the Maps Phase 7 lesson, and it must be read per vendor first.
- **No uncapped spend.** Every engine gets a daily rupee ceiling that refuses pre-flight.
- **No "perfect" claim without the card.** The number on the card is the only claim allowed anywhere.

## 6. Decisions she needs to make
1. **Allow the vendor doc hosts in this session's network settings** (`platform.openai.com`, `docs.anthropic.com`,
   `ai.google.dev`, `docs.perplexity.ai`, `docs.exa.ai`, `docs.parallel.ai`, `linkup.so`, `openrouter.ai`). Without
   them I cannot read a single price, limit or licence — only the SDK shapes above. **R6 must not be built blind**, and
rule (1) in §3 says a vendor's terms must be read before its text can fill her document.
2. **Which engines may spend money at all**, and the daily ceiling for each (she already has `maps_daily_inr` as the
   pattern). Parallel is already paid for, so it is the cheapest first experiment.
3. **One topic she will judge herself** — the first card run should include a report she can mark right or wrong from
   her own knowledge, because her verdict outranks any judge model.
4. Start at **R0** (free, and it makes everything after it measurable) or at **R1** (the plan card, which she will see
   immediately in the chat)? R2–R5 are all our own code and need no vendor decision; R6 is the only phase that waits
   on her keys and on those doc hosts.
