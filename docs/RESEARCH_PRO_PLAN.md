# RESEARCH LIKE A PRO — any topic, end to end, a document she can hand over

Owner, 3 Nov 2026: *"LETS WORK ON RESEARCH ANY TOPIC LIKE PRO — FULL END TO END — HOOLA WILL DO RESEARCH PERFECTLY
AND GIVE USER A PERFECT RESEARCH DOC. FIND THE LLM MODEL IN WORLD RECENT WHO DO RESEARCH PERFECTLY ON ANY TOPIC —
WE WILL USE THAT APIs for research in hoola"*

Plan only. Nothing is built until she says GO on a phase. Facts about the vendors:
`docs/research/research_apis/00_what_exists.md` (read from the vendors' own shipped SDKs, because every vendor doc
host is blocked from the build sandbox).

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

## 3. Build phases

| Phase | What ships | Why here |
|---|---|---|
| **R0 — NAAP (the scorecard first)** | a RESEARCH card like the maps / hard cards: ~20 fixed topics in her world (a market size, a rule change, a supplier landscape, a competitor, a tender, a medicine, a school syllabus, a machine spec…), each with **checkable** truths: every claimed number traceable to a fetched page, the primary-source share, dates present, two sources on the key number, a stated uncertainty section, no link the run did not open, the rupee + minute cost, and an Opus judge on usefulness. Free part runs with no money. | **Nothing else in this plan can be called "perfect" until this exists.** It is also the only honest way to compare vendors later. |
| **R1 — PLAN PEHLE** | a research ask over a size threshold answers with a **plan card** first (the question restated, 4–6 sub-questions, where it will look, est. minutes + rupees), and runs only on her Haan; her note edits the plan. | her money and her question; it is the house pattern and the one feature the market has converged on |
| **R2 — APNA ENGINE, measured** | the existing crew becomes a named engine (`hoola`) behind one `research` job: plan → gather (crew, one agent per sub-question) → **claim check** (every number re-read against the page that carries it) → write → PDF. Nothing bought yet. | fixes gaps 1 and 4 with code we own; sets the baseline the vendors must beat |
| **R3 — LAMBA KAAM** | the job runs in the **background** on the durable turn inbox (survives a restart, resumes where it stopped), with live step narration and a cost meter; the chat gets one short line + the file when it lands. | a real report takes longer than a turn |
| **R4 — PARAYA ENGINE (the vendors, behind the same job)** | `research_engine` setting: `hoola` (default) \| `openai_dr` (`o3-deep-research` / `o4-mini-deep-research`, Responses + background) \| `gemini_dr` (Interactions agent + `DeepResearchAgentConfig`, `collaborative_planning=true` so its plan becomes HER plan card) \| `exa` (`/research/v1`) \| `parallel` (`/v1/tasks/runs`, the key she already pays for) \| `linkup` / `perplexity`. Each returns into Hoola's own document; each has its own rupee cap that **refuses before it spends**, like `mapsbill`. | her ask, done without betting the product on one vendor |
| **R5 — THE RUN-OFF** | the R0 card run across the engines on the same topics: accuracy, primary-source share, claim-check pass rate, minutes, rupees per report. The winner becomes the default **in the code**, and the table is saved. | this is the honest answer to "which model researches perfectly" |
| **R6 — KAAGAZ** | the document itself as a product: her sections, a one-page summary with the key numbers, tables and charts (`charts.js` / `pylab`), full source list with dates, an appendix of what could not be confirmed, her brand kit; Word / Google Doc as well as PDF. | "a perfect research doc" is a document, not a chat reply |
| **R7 — PAKKA (optional)** | a second model reviews the report against its own sources before she sees it (the v0.436 held-answer pattern), one fix round. | the last mile between "good" and "trustworthy" |

## 4. What it will NOT do
- **No scraping.** Only documented APIs and pages a tool actually fetched — the standing rule.
- **No invented source, number or date.** A fact whose page cannot be re-read is marked unconfirmed, not quietly kept.
- **No vendor's report handed over as Hoola's**: if a provider's terms forbid storing or re-sharing its text, that
  provider can draft but not fill the document — the Maps Phase 7 lesson, and it must be read per vendor first.
- **No uncapped spend.** Every engine gets a daily rupee ceiling that refuses pre-flight.
- **No "perfect" claim without the card.** The number on the card is the only claim allowed anywhere.

## 5. Decisions she needs to make
1. **Allow the vendor doc hosts in this session's network settings** (`platform.openai.com`, `docs.anthropic.com`,
   `ai.google.dev`, `docs.perplexity.ai`, `docs.exa.ai`, `docs.parallel.ai`, `linkup.so`, `openrouter.ai`). Without
   them I cannot read a single price, limit or licence — only the SDK shapes above. **R4 must not be built blind.**
2. **Which engines may spend money at all**, and the daily ceiling for each (she already has `maps_daily_inr` as the
   pattern). Parallel is already paid for, so it is the cheapest first experiment.
3. **One topic she will judge herself** — the first card run should include a report she can mark right or wrong from
   her own knowledge, because her verdict outranks any judge model.
4. Start at **R0** (free, and it makes everything after it measurable) or at **R1** (the plan card, which she will see
   immediately in the chat)?
