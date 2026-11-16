# HOOLA PIPELINE + HOOLA PROCESS BOX - the plan

Owner, 16 Nov 2026: "INPUT WILL BE OPENROUTER LLM ---- HOOLA PROCESS BOX ( RAPID AUTO CHANGE OVER OF LLM BASED ON
TASK ) --- OUTPUT", then "CHOOSING BEST MODEL PER CAPABILITY, RELIABILITY, USE, COMPLEXITY", "ALREADY 1000 OF SITES
ARE THERE FOR CHECKING MODEL QUALITY ... WE WILL USE THIS", "HIGHEST NEVER CHOSEN, BEST AS PER PROMPT ... LOW, MID,
HIGH, MAX, ULTRA", "LOGIC FOR CHOOSING PERFECT MODEL IN PERFECT TIME WITH PROPER SYNCHRONISATION", "GO AHEAD, SAVE
THE PLAN DOC ... COSTING LATER, FIRST DEVELOPMENT AND DEPLOYMENT, THEN PRICING".

Nothing in this document is built yet. Read it before touching model choice anywhere in the server.

---

## 0. What it is, in one picture

```
 her message (chat / call / Hoola Code / background / studio)
        |
        v
 +------------------------- HOOLA PROCESS BOX --------------------------+
 |  1 PLAN     split the ask into parts (code for simple asks,          |
 |             a LOW planner model for asks with several parts)         |
 |  2 SIZE     each part: kind of work + level (LOW..ULTRA) + language  |
 |  3 CHOOSE   each part: one model + two backups from the level table  |
 |  4 RUN      parts side by side where they can, in order where not    |
 |  5 HAND OFF a fixed package from one part to the next                |
 |  6 CHECK    code checks the final answer against the facts           |
 +----------------------------------------------------------------------+
        |
        v
 ONE reply in Hoola's voice + her language (+ files), and one receipt line:
 which model did which part and why
```

Input = the models reachable through OpenRouter first, then other multi-model providers for what OpenRouter lacks (D11).
Output = one answer. She never sees several models talking.

---

## 1. Owner decisions (fixed, do not re-argue)

| # | Decision |
|---|---|
| D1 | Quality comes from **public leaderboards**, not from tests Hoola writes itself. Hoola's own records are used only as an **outage record** (a model that keeps failing is moved down for a while). |
| D2 | **Never the highest by default.** Each part gets the **lowest level that does it well**. |
| D3 | Five levels: **LOW, MID, HIGH, MAX, ULTRA**. Every kind of work has its **own** models at each level. |
| D4 | Built for a **global audience, India included**. Language is part of the kind of work. |
| D5 | **Pricing later.** Order: development -> deployment -> pricing. No price enters the choice until the pricing phase. |
| D6 | Her tap stays where Hoola already asks for it (sending, sharing, deleting, money, paid generation). A part that waits for her tap pauses **only its own branch**; the other parts keep going. During development the existing price cards for paid image / video stay exactly as they are; how the Box shows prices is part of the pricing phase. |
| D7 | ULTRA = **one model**, as in the plan (16 Nov: "ALL AS PER PLAN"). |
| D8 | The Indian-language benchmark is chosen **by research** (16 Nov: "DO RESEARCH") - section 8.4. |
| D9 | A model that moves two levels in a table refresh is **applied automatically** (16 Nov: "AUTO"). |
| D10 | Every kind of work has a pool of **10-20 models** (2-4 per level), not 1-3 (16 Nov: "MIN 10 MODEL MAX 20 MODELS"). Levels are quality bands below the best model of that kind (section 8.2). |
| D11 | A model not on OpenRouter is reached through **another multi-model provider like OpenRouter** (16 Nov: "WE WILL GET IT FROM OTHER LLM PROVIDERS LIKE OPENROUTER"). OpenRouter stays first; the others fill the gaps. Keys only in the VPS .env. Providers (research 05): fal.ai, Kie.ai, Eden AI (terms to read first); WaveSpeed only after written permission. |
| D12 | A model that **no** multi-model provider carries is reached through **its maker's own API** (16 Nov: "THOSE DONT HAVE LLM PROVIDER WE WILL KEEP THERE API DIRECTLY"). Order: OpenRouter -> other multi-model provider -> maker's own API. One key per maker, VPS .env only. |

---

## 2. Kinds of work

Each part of an ask is one of these. The id is what the code uses.

| id | Kind of work | In | Out |
|---|---|---|---|
| `route` | Quick decision: sort a message, yes / no, pick a branch | text | label |
| `plan` | Split an ask into parts (the planner itself) | text | plan |
| `chat` | Short reply, small talk, simple answer | text | text |
| `write` | Long writing: report, letter, article, script | text | text |
| `write.lang` | Writing in a named language (Hindi, Marathi, Spanish, Arabic...) | text | text |
| `translate` | Translation between languages | text | text |
| `summarise` | Summary of a page, chat, file | text | text |
| `reason` | Hard reasoning, maths, logic, planning a solution | text | text |
| `research` | Web research with sources | text | text + sources |
| `facts` | Factual answer where a wrong fact is costly | text | text |
| `extract` | Pull fields / rows out of text into a fixed shape | text | data |
| `read.long` | Read a very long text or many files at once | long text | text |
| `read.pdf` | Read PDFs / scanned documents | PDF / pages | text |
| `read.image` | Read pictures, screenshots, charts | image | text |
| `tools` | Many steps with tools (the agent loop) | text | actions |
| `code` | Change code in a repo (Hoola Code) | repo + text | diff |
| `code.small` | Write a small script or snippet | text | code |
| `check` | Check another model's answer | text | verdict |
| `image.make` | Make an image | text | image |
| `image.edit` | Edit an image | image + text | image |
| `video.make` | Make a video (text or image to video) | text / image | video |
| `speech.in` | Speech to text | audio | text |
| `speech.out` | Text to speech | text | audio |
| `music.make` | Make music | text | audio |
| `embed` | Turn text into numbers for memory search | text | vector |

**Not a model's job:** making the PDF / Word / Excel file (Hoola's own makers), sending, paying, PC control.
**Outside the Box for now:** the live call voice (Gemini Live speaks; the Box works behind `santosh_kaam`) and the PC
brain (`server/app/pc/`, frozen by the owner - it keeps its own route until she says otherwise).

---

## 3. The five levels and how a part gets its level

| Level | Used for |
|---|---|
| LOW | Simple, short, high-volume work |
| MID | Everyday work |
| HIGH | Hard work |
| MAX | Very hard work |
| ULTRA | Rare, highest-stakes work |

### 3.1 Starting level per kind of work

| Starts at | Kinds |
|---|---|
| LOW | `route`, `plan`, `extract`, `summarise` (short), `embed`, `speech.in` |
| MID | `chat`, `write`, `translate`, `research`, `read.pdf`, `read.image`, `check`, `code.small`, `speech.out`, `image.make`, `image.edit`, `music.make` |
| HIGH | `write.lang` for Indian languages, `reason`, `tools`, `code`, `read.long`, `facts`, `video.make` |

### 3.2 Signals that raise the level (code, not a model)

Each signal raises a part **one** level. Most parts get zero or one raise.

| Signal | How code sees it |
|---|---|
| Hard reasoning | `hard.assess()` says hard (already built) |
| Big job | many parts / long input / `devsahayak/plan.py` says standard or large (already built) |
| A mistake is costly | money, legal, medical, tax, code going live, a message to her customers |
| Exact facts needed | figures, dates, prices, names that must be right |
| Deep research asked | `hard.research_wanted()` + deep words (already built) |
| Earlier try failed the check | set while running (see 5.3) |

### 3.3 Limits on the level

- **Her choice wins.** If she picks a level (or a model) for a part, it is used.
- **A live call:** a part she is waiting for on the line is capped at HIGH (speed first); work handed to the background
  is not capped.
- **ULTRA only when:** she asked for it, OR a MAX try failed the check, OR the job is both hard AND costly.
- **Level only goes up inside one message, never down.** The next message starts fresh.
- ULTRA = **one model** (D7).

---

## 4. Choosing the model for a part

A part's needs: kind of work, level, language, what goes in, what comes out, tools yes / no, how much text it must
hold, where the ask came from.

**Step 1 - remove every model that cannot do the part.** Out if:
- not in that level's table for that kind of work (and that language, for `write.lang` / `translate`)
- cannot take that input or give that output (from the OpenRouter catalogue, `agent/modelprofile.py`)
- cannot use tools when the part needs them
- its window is smaller than the input + 30 % room
- paused for recent failures (outage record)
- not allowed for this user or region

**Step 2 - rank what is left.** Everything left is good enough for the level, so:
1. reliability (did it answer well in the last hour: OpenRouter uptime + Hoola's outage record)
2. speed (first word, words a second)
3. leaderboard score - breaks ties

Weights by where the ask came from: call = speed first, Hoola Code = score first, background = reliability first.
(Price is added here in the pricing phase - D5.)

**Step 3 - keep one main model and two backups**, from different companies where possible.

**Same inputs = same choice.** Each message uses the copy of the tables that was current when it started; a table
refresh never changes a running answer.

---

## 5. When: choosing at the right time

### 5.1 The moments

| Moment | What happens |
|---|---|
| Message arrives | A plain ask (one simple job) is planned by **code** in milliseconds - no extra model call. Only an ask with several parts goes to the LOW planner (about 1-2 s). |
| Planning | Parts, kinds, levels, languages, which part waits for which; a **first choice** of model per part, noted. |
| Just before a part starts | The model is **confirmed now**, because earlier results can change the need (e.g. research found 40 PDFs -> the reading part needs a bigger window). |
| While a part runs | **Same model for the whole part** (keeps its prompt cache - faster and cheaper - and one style). |
| Next message, same chat | Same model for the same kind + level for about **30 minutes**, while it stays healthy. |

### 5.2 Hand-over rules (the only reasons to change)

| What happened | Action |
|---|---|
| Error, refusal, empty answer | Backup at the **same** level, at once |
| No first word in time (call 3 s, chat 8 s, background 30 s) | Backup at the same level |
| Answer failed Hoola's check | **One level up**, once per part |
| The part outgrew the model's window | A same-level model with a bigger window |
| She asked for better | One level up |

- A part changes model **at most two times**; after that it stops and says plainly what could not be done. Never a loop.
- **Call only:** if the first word is late, the backup starts **at the same time**; the first to answer is used, the
  other is stopped. Silence on a call is the worst case.

### 5.3 Moving up after a failed check

The check (section 6.10) runs on the part's result. Failed = the part runs once more one level up, with the problems
named. Failed again = the answer goes out with the problem said plainly. No third try.

---

## 6. Staying in step: synchronisation

### 6.1 One job sheet per message
One record: the plan, each part's state (waiting / running / waiting for her tap / done / failed), the model chosen and
why, inputs, outputs, tries. **Every part reads only from the sheet and writes only to it.** Saved after every part, so
a restart continues from the last finished part and nothing is done twice. Built on the turn engine Hoola already has
(LangGraph turn graph: checkpoints G1, one run per chat + Stop G2, tool ledger G1, park on her tap G8).

### 6.2 Parts side by side
Parts that do not wait on each other run together (5 companies researched as 5 searches at once; an image made while
the text is written). A part that needs another part's result waits for it.

### 6.3 The hand-off package
Every part passes on:
```
result        what it produced
facts         [{text, value, source}]   names, figures, dates, prices
files         ids of files it made or read
notes         short notes for the next part
not_done      what it could not do, and why
```
The next model gets this package, **not** the previous model's whole working. **Facts are locked:** a later part may
not change a value from her or from a source; the final check (6.10) confirms it.

### 6.4 One voice
Only the last part (the writer) speaks to her, in Hoola's voice and her language. Earlier parts show as short step
lines ("Researching 5 companies..."). She never sees several models talking.

### 6.5 One memory
All parts read the same memory snapshot taken when the message arrived. Memory is written once, at the end of the job.

### 6.6 One job at a time per chat
A new message while a job runs: about the same job = a note into the running plan; otherwise it waits its turn
(G2 tickets). **Stop** stops every running part and every model call at once.

### 6.7 Time limits
The whole job has a limit (seconds on a call, minutes in chat, longer in background); each part gets a share. A part
that runs over: switch to a faster same-level model, or deliver what is ready and say plainly what is missing.

### 6.8 Calls at once
A cap per user and a cap per company, each company with its own queue, so Hoola never hits a company's rate limit.

### 6.9 Waiting for her tap (D6)
A part that needs her tap pauses **only its own branch** (park, G8). The other parts keep going; that branch carries on
when she taps; "Not now" ends only that branch and the reply says it was not done.

### 6.10 Final check before the reply
Code checks: figures in the answer = the facts list, every file exists, every `not_done` is mentioned. A problem =
one fix round for the writer (the research claim check `research/claims.py` already does this for research answers).

---

## 7. Each surface

| Surface | How it uses the Box |
|---|---|
| Chat (phone + console) | Every message. Most are one part planned by code = no added delay. |
| Live call | Gemini Live keeps speaking; `santosh_kaam` work goes through the Box with speed first, HIGH cap for parts she waits on, the backup head start (5.2). |
| Hoola Code | Score first. `code` parts start at HIGH; the plan pass, the reviewer and compaction are their own parts (`plan`, `check`, `summarise`). Replaces the fixed `dev_qwen_model`. |
| Background / long jobs | Reliability first, no level cap, longer time limits. |
| Create studios | `image.make` / `image.edit` / `video.make` / `music.make` / `speech.out` through the same tables; the existing price cards stay (D6). |
| Her own model pick (console dropdown, `modelchoice.py`) | Her pick is a pin: it wins for the parts it can do; parts it cannot do (e.g. an image) still go to the Box. |

---

## 8. The leaderboard feed

### 8.1 Sources per kind of work (first read 16 Nov 2026 - `docs/research/pipeline/01-03`)

| Kind | Sources |
|---|---|
| `chat`, `write`, `summarise` | LMArena text, Artificial Analysis, LiveBench |
| `reason` | Artificial Analysis, LiveBench maths / reasoning |
| `code`, `code.small` | SWE-bench, Aider, LiveCodeBench, LMArena WebDev |
| `tools` | Berkeley Function Calling Leaderboard, tau-bench |
| `research`, `facts` | LMArena Search, SimpleQA |
| `read.long` | long-context boards |
| `read.image`, `read.pdf` | LMArena Vision, MMMU, document / OCR boards |
| `write.lang`, `translate` | language views of the boards + Indian benchmarks (thin - section 12) |
| `image.make`, `image.edit` | LMArena text-to-image + image edit, Artificial Analysis image arena |
| `video.make` | Artificial Analysis video arena, LMArena video |
| `speech.in`, `speech.out` | Hugging Face Open ASR, Artificial Analysis speech arenas, TTS Arena |
| speed, reliability | Artificial Analysis speed, OpenRouter uptime / latency |

### 8.2 How the feed works
1. Read each source on a schedule (daily or weekly), from its data feed / API where one exists - no scraping a site
   whose terms forbid it.
2. Map each board's model names to the OpenRouter model id (a mapping table, checked by a test).
3. One score per model per kind of work: ranks normalised per source, then averaged across that kind's sources.
4. Missing from one board = the other boards decide (not marked down). On **no** board for that kind = **not used**
   for that kind until it appears.
5. The level tables are cut from those scores, saved as one dated file, and that file is what a message reads
   (4: same inputs = same choice). **Pool size 10-20 per kind (D10), up to 4 per level.** Levels = quality bands below
   the best model of that kind (ULTRA within 25 rating points, MAX 25-50, HIGH 50-80, MID 80-120, LOW 120-190), so LOW
   holds the smaller, faster models; a board too small for bands splits its best 20 into five equal groups. Only
   models OpenRouter lists that day, that take the input and give the output the work needs, added in the last 18
   months. Cut by `docs/research/pipeline/tools/build.py`.
6. A new table is compared with the last one; a big jump (a model moving two levels) is **applied by itself** (D9)
   and written in the table's change log so it can be seen later.

**What the automatic feed may read (from the terms read 16 Nov 2026):**

| Source | Automatic feed | Why |
|---|---|---|
| LMArena data (`lmarena-ai/leaderboard-dataset` on Hugging Face) | **yes - main source** | CC-BY-4.0: free to reuse with credit. Covers text (incl. language views), vision, documents, search, webdev, images, image edit, video. The arena.ai site itself blocks automated reads - use the dataset. |
| OpenRouter models API | **yes** | the catalogue, what each model takes / gives, uptime. Their terms bar scraping the website; the API is the allowed route. Use `?output_modalities=all` - the plain call lists only text models. |
| Music Arena dataset | yes | CC-BY-4.0 |
| HF Open ASR, TTS Arena V2 | after a terms check | data is published (Gradio config / JSON); terms not found yet |
| voiceofindia.ai (Indian speech) | read by hand, monthly | no download or API |
| Artificial Analysis | **not until confirmed** | free API needs credit, but the site licence says personal, non-commercial use; confirm with them or take their paid data plan in the pricing phase (D5) |
| BenchLeader (aggregator) | no | it mirrors other boards; their scores are not relicensed by it |
| SWE-bench Verified, Aider, LiveCodeBench, BFCL, tau2-bench, Fiction.LiveBench, MMMU, LiveBench maths / agentic coding | no - stale | newest entries Jan 2025 - Jun 2026 |

Hoola credits the boards it uses (CC-BY) on a 'How Hoola picks models' page.

### 8.3 Model tables
First copy, cut by hand for her approval: `docs/research/pipeline/04_level_tables.md` (every id checked on
OpenRouter 16 Nov 2026). From P0 on, code cuts them from the feed; the code reads the dated tables file, never this
document. **Only models reachable through OpenRouter** ("INPUT WILL BE OPENROUTER"); better models elsewhere are listed
as "not reachable yet". A level with no scored model uses the nearest filled level above it.

### 8.4 Indian languages (D8) - research 16 Nov 2026 (`docs/research/pipeline/03_indian_languages.md`)
- **Speech: covered.** voiceofindia.ai (AI4Bharat / IIT Madras) - speech-to-text on 15 Indian languages (held-out,
  native-checked phone speech) and a text-to-speech vote arena on 10 languages, both with Nov 2026 models. Used for
  `speech.in` / `speech.out` (Indian).
- **Text, translation, Hinglish: no public board ranks current models.** The AI4Bharat text arena has no board yet,
  LMArena has no Indian-language view, the Artificial Analysis Hindi view is stale, MILU has only self-reported numbers,
  and Hinglish has no benchmark at all. Until she decides (section 12), these rows use LMArena's pooled non-English
  view and are marked **thin**.
- The best public Indian test sets (to run on a shortlist if she agrees): MILU (10 languages, exam questions,
  CC BY 4.0), IN22 (translation, 22 languages, CC-BY-4.0), COMI-LINGUA (Hinglish, CC-BY-4.0).

---

## 9. What Hoola already has, and what is new

**Already built, reused:**
- `agent/llm.py` - `MODEL_NOW` (the per-turn model override), per-brain pause on failure (`brain_paused`)
- `agent/modelprofile.py` - what each OpenRouter model can take and give, its window
- `agent/providers.py` - `provider:model` keys beside OpenRouter
- `agent/hard.py` - hard-ask and research detection
- `devsahayak/plan.py` - job size
- the turn graph (G0-G9) - checkpoints, one run per chat, Stop, tool ledger, park on her tap, told once
- `research/claims.py` - the fact check against sources
- `modelchoice.py` - her own model pick

**New:**
- `server/app/pipeline/` (proposed): `kinds.py` (section 2), `levels.py` (section 3), `choose.py` (section 4),
  `sheet.py` (6.1 + 6.3), `feed.py` (section 8), `limits.py` (6.7 + 6.8), `receipt.py`
- the LOW planner prompt and its code fallback
- the call-only backup head start
- console + phone: the receipt line under a reply ("Research: model A · Writing: model B")

**Not touched:** the PC brain and every frozen PC file (CLAUDE.md freeze).

---

## 10. Build phases

| Phase | What | Done when |
|---|---|---|
| P0 | Feed: read the boards, the name map, dated level tables, `docs/research/pipeline/` | Tables for every kind of work, each with its sources and date - **BUILT v0.958.0** (`server/app/pipeline/`, daily on the worker, `GET /api/pipeline/tables`, vps-ops `pipeline_feed`) |
| P1 | Kinds + levels + choose, as pure code with tests (no model call) | The same inputs always give the same model; every rule in 3-5 has a test - **BUILT v0.961.0** (`pipeline/detect.py`, `levels.py`, `choose.py`, `handover.py`, `box.py`; `GET /api/pipeline/choose`, vps-ops `pipeline_try`; 65 tests) |
| P2 | The job sheet + hand-off package + the final check, for a ONE-part message | Chat answers through the Box with no added delay - **BUILT v0.963.0** (`pipeline/turnbox.py`, `sheet.py`, `check.py`; ~5 ms a message; behind `pipeline_on`; vps-ops `pipeline_on` / `pipeline_off` / `pipeline_sheets`) |
| P3 | Planner + parts side by side + waiting on each other + her tap per branch | The EV example (11) runs end to end |
| P4 | Hand-over rules + moving up + the call head start + limits + queues | Each failure case in 5.2 has a test with a fake model |
| P5 | Hoola Code, background jobs, studios on the Box | Their fixed model settings retired, old values kept as a fallback switch |
| P6 | Receipt line on phone + console | She can see which model did which part |
| P7 | Deploy, watch the outage record + timings for a week | No message slower than before for one-part asks |
| P8 | **Pricing** (D5): price per level, price in the ranking, her limits | Her decision |

Each phase ships behind a switch (`pipeline_on`, default OFF until P7); off = today's routing exactly.

---

## 11. Worked example

"Research the top 5 EV makers in India, compare prices in a table, and make a Hindi PDF report."

| Part | Kind | Level | Why |
|---|---|---|---|
| Plan | `plan` | LOW | several parts -> planner |
| Research x5 (side by side) | `research` | MID | five companies, public facts |
| Price table | `extract` | LOW | arranging facts already found |
| Hindi report | `write.lang` (hi) | HIGH | long Hindi writing |
| PDF | - | - | Hoola's own PDF maker |
| Check | `check` | MID | figures vs facts list |

```
0.0 s  message arrives -> several parts -> LOW planner
1.5 s  plan ready
1.6 s  5 research searches at once      (she sees: "Researching 5 companies...")
~25 s  facts list with sources on the job sheet
~27 s  table
~28 s  Hindi report, streamed as written
~60 s  PDF
~62 s  check passes
~63 s  one Hindi reply + the PDF + the receipt line
```

---

## 12. Open questions (hers)

Answered 16 Nov: ULTRA (D7), the Indian benchmark (D8, by research), big jumps (D9).

1. **Indian-language text (new, 16 Nov):** no public board ranks current models on Hindi / Marathi / Tamil... text or
   Hinglish. Use only the pooled non-English Arena view (pure D1), or also run the PUBLIC Indian test sets (MILU, IN22,
   COMI-LINGUA - made by AI4Bharat and others, not by Hoola) on a shortlist of about 10 models, re-run when a new model
   appears? Recommended: run them; otherwise Indian-language choices are a guess.
2. **Region rules:** any users whose data must stay with certain providers? Until she says, none.

Pricing questions wait for P8 (D5).
