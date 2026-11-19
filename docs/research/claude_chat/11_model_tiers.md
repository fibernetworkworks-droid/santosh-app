# Four tiers of models: ULTRA, HIGH, MEDIUM, LOW (19 Nov 2026)

Owner's ask: "NOW THIS ARE TOP MODEL ITS PRICING IS ULTRA --- THUS HOOLA USER IF WANT ULTRA OUTPUT THEY CAN USE THIS
AND IT CAUSE BURNING CREDIT FAST ---- NOW GIVE ME HIGH MODEL COMBINATION .. SAME FOR MEDIUM AND LAST LOW".

Rule, the same quality bands the Box already uses (`pipeline/kinds.py` BANDS), measured as points below the best
model on each LMArena board (11 Nov 2026, 1,000+ votes only; Gemini 4 Carbon left out: refused on her account):
ULTRA = the best; HIGH = 25-50 points below; MEDIUM = 50-80 below; LOW = 80+ below. Inside a tier, the cheapest model
that reaches it. Price = the maker's own standard price on OpenRouter, read 19 Nov (Rs 88 to the dollar).
Rs a step = 20,000 tokens read + 800 written; a chat reply is about 1 step, a worker job about 10.
Long tool jobs use the agent board: ULTRA = places 1-5, HIGH = 6-15, MEDIUM = 16-30, LOW = 31+, measured cost per job.

| Job | ULTRA (best, burns credit) | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| Everyday answers, business, law, languages, long documents, long chats | Gemini 4 Argon (Rs 4.22) | Gemini 3.8 Flash (Rs 1.58; 30-44 below) | GLM-5.3-Flash (Rs 0.30; 52-66 below) | GPT-6 Luna (Rs 0.21; 98-141 below) |
| Writing: posts, emails, scripts | Gemini 4 Argon (Rs 4.22) | Gemini 3.8 Flash (Rs 1.58) | GLM-5.3 (Rs 2.77 at Z.AI, Rs 0.22 cheapest provider; 73 below) | GPT-6 Luna (Rs 0.21) |
| Maths, working out | Gemini 4 Argon (Rs 4.22) | GLM-5.3-Flash (Rs 0.30; 41 below) | GLM-5.3-Flash (Rs 0.30) | GPT-6 Luna (Rs 0.21) |
| Medicine and health | Claude Fable 5.1 (Rs 21.12) | GLM-5.3-Flash (Rs 0.30; 49 below) | Qwen3-Next 80B (Rs 0.24; 72 below) | GPT-6 Luna (Rs 0.21) |
| Facts without making things up | Claude Opus 5.5 (Rs 8.45) | GLM-5.3-Flash (Rs 0.30; 43 below) | MiMo-V2.6-Flash (Rs 0.27; 56 below) | GPT-6 Luna (Rs 0.21; 39 below = HIGH quality) |
| Pictures, screenshots, reading text in pictures | Claude Fable 5 (Rs 21.12) | Gemini 3.8 Flash (Rs 1.58; 5-9 below = near the best) | GLM-5.3-Flash (Rs 0.30; 31-34 below) | GPT-6 Luna (Rs 0.21) |
| PDFs and documents | Claude Fable 5.1 (Rs 21.12) | Gemini 3.8 Flash (Rs 1.58; 33 below) | GPT-5.6 Luna (Rs 0.44; 61 below) | GPT-6 Luna (Rs 0.21) |
| Building apps, websites, code | Claude Fable 5.2 (Rs 16.90) | Claude Sonnet 5.5 (Rs 4.22; 54 below - nothing cheaper is closer) | DeepSeek V4.1 Flash (Rs 0.61) / Qwen 3.8 27B (Hoola Code, 11/12 on Hoola's card) | MiMo-V2.6-Flash (Rs 0.27; 46 below on coding chat) |
| Web research with sources | Qwen3.8-Max (Rs 3.94, #1) | Qwen3.8-Max (Rs 3.94) - no cheaper model is in this band | Hoola's own web search + GLM-5.3-Flash | Hoola's own web search + GPT-6 Luna |
| AI employee: long jobs with tools | Claude Fable 5.2 (#1, Rs 794 a job) | Gemini 4 Argon (#11, Rs 62 a job) | DeepSeek V4.1 Flash (#30, Rs 12 a job) | GPT-6 Luna (#32, Rs 7 a job; #5 at not inventing tools) |
| Backup (another company) | Claude Opus 5.5 (Rs 8.45) | Qwen3.8-Max (Rs 3.94) | DeepSeek V4.1 Flash (Rs 0.61) | Claude Haiku 5.5 (Rs 0.21) |

## What one message costs in each tier

| Tier | A chat reply (1 step) | A worker job (10 steps) | A long tool job | Compared with MEDIUM |
|---|---|---|---|---|
| ULTRA | Rs 4.22 (Rs 21 for pictures / PDFs / medicine) | Rs 42-211 | Rs 794 | 14-70x |
| HIGH | Rs 1.58 | Rs 3-16 | Rs 62 | about 5x |
| MEDIUM | Rs 0.30 | Rs 3-6 | Rs 12 | 1x |
| LOW | Rs 0.21 | Rs 2 | Rs 7 | 0.7x |

## Notes

- Two models carry most of it: Gemini 3.8 Flash (HIGH) and GLM-5.3-Flash (MEDIUM, and HIGH for maths, medicine and facts).
- Hoola's writer today, GLM-5.3, is MEDIUM quality (55-73 below the best) but costs HIGH prices when Z.AI serves it
  (Rs 2.77). At its cheapest provider it is Rs 0.22. A price ceiling on each call decides which one Hoola pays.
- LOW is thin: GPT-6 Luna and Claude Haiku 5.5 are 100-140 points below the best on everyday answers. GLM-5.3-Flash at
  its cheapest providers (Rs 0.08, lower-precision copies) gives MEDIUM quality at LOW prices, with some quality risk.
- Google risk: Gemini 4 Carbon is refused on her account; Gemini 4 Argon and Gemini 3.8 Flash need one test call first.
- Boards rate answers people prefer, not Hoola's own jobs and not speed.
