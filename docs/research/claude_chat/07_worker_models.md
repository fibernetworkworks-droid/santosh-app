# Workers: when to use them and which model (18 Nov 2026)

Owner's ask: "NOW LETS WORK NEXT A WORKER" (after the writer was settled: GLM-5.3 writes, DeepSeek V4.1 Flash checks).
A worker = a helper part the Box runs before the writer when one message is split into parts (`pipeline/parts.py`).

## What her own test showed (18 Nov, chat conv_158ac09, v0.999.5)
| Message | Parts | Workers and time | Total |
|---|---|---|---|
| Diwali offers + discount | 3 | brainstorm on Claude Sonnet 4.6 (18.4 s), discount on Claude Opus 4.6 (16.3 s, waited for the first), then the writer | 66 s |
| Bakery October numbers | 2 | "calculate the profit" on GLM-5.3-Flash (8.0 s), then the writer | 20 s |
| The other 4 | 1 | none | 9-35 s |

## The four problems
1. **Workers start on a comma.** `detect.PARTS` and `parts.SPLIT` count ", and", "then", "also", ";" or a list as a new
   job. "...sales Rs 1,84,000, costs Rs 1,12,500, and rent Rs 25,000" became a worker for one subtraction. "4 Diwali
   ideas, and suggest a discount" became two workers for what one writer answers in one go.
2. **Price is not in the choice.** `choose.ORDER["chat"]` ranks by reliability, speed, score only. So a MID brainstorm
   went to Sonnet 4.6 (arena 1458, $3 / $15 per million) although GLM-5.3 is higher (1475) at $0.07 / $1.4 - 29x
   cheaper and better. The MAX discount went to Opus 4.6 ($5 / $25), about 70x GLM-5.3's input price.
3. **Workers wait for each other.** The planner put the discount part "after" the brainstorm, so they ran one after the
   other, then the writer wrote it all again: three model turns in a row.
4. **Nothing caps a worker's time in chat.** The parts share `pipeline_parts_s` = 300 s; a slow worker holds her reply.

## How Claude does it (Anthropic's published multi-agent research system, 2025)
- One model answers almost everything itself, calling tools in one loop.
- Sub-agents only for breadth-first work that splits into independent pieces (research of several things), 3-5 at once,
  side by side. A simple fact = one agent, a few tool calls.
- Sub-agents cost about 15x the tokens of a chat, so they are kept for work worth that much. Tasks whose parts depend
  on each other or share context are done by one agent.
- The lead (here: the writer) decides how much effort; sub-agents get a clear goal, the tools for it, and a limit.

## Candidate worker models (same data as 06_writer_models.md; Rs / step = 20k read + 800 written, list price)
Board columns from LMArena (2026-11-11): overall / hard prompts / math. Reads = OpenRouter's input types (18 Nov).

| Model | Overall | Hard | Math | Reads | $/M in / out | Rs / step |
|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash | 1464 | 1483 | 1462 | text, image | 0.036 / 0.5 | 0.10 |
| GLM-5.3 (Max) | 1475 | 1493 | 1474 | text | 0.07 / 1.4 | 0.22 |
| GLM-5.3-Flash | 1472 | 1490 | 1471 | text, image, video | 0.15 / 0.5 | 0.30 |
| Qwen 3.8 27B | 1437 | - | - | text, image, video | 0.06 / 2.2 | 0.26 |
| MiMo-V2.6-Pro | 1492 | 1511 | 1471 | text, image, video, audio | 0.43 / 0.87 | 0.83 |
| Gemini 3.8 Flash | 1500 | 1510 | 1503 | text, image, file, audio, video | 0.83 / 4.12 | 1.74 |
| Claude Sonnet 4.6 (picked today) | 1458 | 1484 | 1463 | text, image, file | 3 / 15 | 6.34 |
| Claude Opus 4.6 (picked today) | 1501 | 1524 | 1512 | text, image, file | 5 / 25 | 10.56 |

Other facts: DeepSeek V4.1 Flash has the lowest measured hallucination rate (Vectara HHEM 4.2%); Qwen 3.8 27B scored
11/12 on Hoola's own coding card (v0.930); every model above has a ~1M-token window.

## Suggested worker setup (her choice, like the writers)
| Worker kind | Main | Backup | Why |
|---|---|---|---|
| Research / facts (search, read pages, note) | DeepSeek V4.1 Flash | GLM-5.3-Flash | cheapest, fewest made-up facts |
| Working out (sums, plans, comparisons) | GLM-5.3 + pylab for every figure | Gemini 3.8 Flash | strong at math for Rs 0.22; numbers computed, not guessed |
| Reading files / pictures / PDFs | Gemini 3.8 Flash | Qwen 3.8 27B | reads every file type |
| Tables / extraction | DeepSeek V4.1 Flash | GLM-5.3-Flash | cheap, exact |
| Code | Qwen 3.8 27B | GLM-5.3 | Hoola Code's model, coding card 11/12 |

Claude Opus / Sonnet and GPT-5.x only when she pins them: 10-50x the price for scores no better on these boards.

## The plan (W1-W4, one version)
- **W1 When.** The writer answers every ordinary message alone, even with "and", "then", "also" or a list. Workers only
  for: 2-5 independent things to look up or compare, several files to read, or a heavy job (document, code) that can run
  beside the reply. Decided by the kinds of the pieces, never by a comma.
- **W2 Which.** A worker list per kind (`pipeline_workers`, the table above), price inside the choice, her pick wins.
- **W3 Side by side, capped.** At most 5 workers at once, none waits on another unless it needs its result, 90 s each in
  a chat; the writer goes on with what is done and says plainly what is missing.
- **W4 Seen.** `pipeline_sheets` shows each worker's model, time and rupees, and the message's total.

Expected on her test: the Diwali and bakery messages answered by the writer alone (about 20 s, not 66 s), no Opus /
Sonnet charges; a "compare gold, silver and petrol prices today" message runs 3 research workers side by side.
NOT MEASURED yet: the parity card (running 18 Nov from 22:24 IST) is the before-picture; it runs again after W1-W4.
