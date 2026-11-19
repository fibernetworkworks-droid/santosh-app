# Four tiers for voice calls and AI employees (19 Nov 2026)

Owner's ask: "NOW FOR VOICE CALL AND AI EMPLOYEE" (after `11`-`13`).

## Voice calls

A Hoola call is two parts: the VOICE (hears her and speaks; Gemini Live today) and the BRAIN (does the work when she
asks for something; Claude Haiku 5.5 today, `voice_brain_model`). There is no public quality board for live voice, so
the voice is picked by ear; the brain uses the text tiers in `11_model_tiers.md`.

Voice engines Hoola already has (v0.825):

| Voice | Price | Note |
|---|---|---|
| Gemini Live (`gemini-3.8-live`, Hoola's default) | about Rs 1.2 a reply, measured on her calls (6 Nov) = about Rs 2.4 a talking minute | parks when quiet, so silence costs nothing |
| GPT-Live-1 (OpenAI) | Rs 4.40 a minute, brain extra | |
| Phonic 1 | Rs 6.16 a minute, all in | |
| Grok Voice 3.0 (xAI) | Rs 7.04 a minute (list) | |

Call tiers (one brain ask a minute assumed; a call brain reads less than a chat turn, so these are upper estimates):

| Tier | Voice | Brain | About a minute | A 10-minute call |
|---|---|---|---|---|
| ULTRA | GPT-Live-1 | Gemini 4 Argon (Rs 4.22 an ask) | Rs 8.6 | Rs 86 |
| HIGH | Gemini Live | Gemini 3.8 Flash (Rs 1.58) | Rs 4.0 | Rs 40 |
| MEDIUM | Gemini Live | GLM-5.3-Flash (Rs 0.30) | Rs 2.7 | Rs 27 |
| LOW (Hoola today) | Gemini Live | Claude Haiku 5.5 (Rs 0.21) | Rs 2.6 | Rs 26 |
| LOW, turn by turn (not live: she waits after each sentence) | Sarvam Saaras v3 hears (Rs 0.5 a min) + Gemini 3.8 Flash-Lite TTS speaks (Rs 1.06 a min) | GPT-6 Luna (Rs 0.21) | Rs 1.8 | Rs 18 |

- The voice is most of the cost: MEDIUM and LOW differ by paise because Gemini Live dominates.
- A call brain must answer fast; the board places of Gemini 4 Argon and Gemini 3.8 Flash were measured at high
  thinking, which is slower than a call allows. On a call they run with low thinking, a little below their board place.

## AI employees (long jobs with tools)

From the agent board (LMArena, 57 models): the cost of one whole job is LMArena's measured median. Sub-places: finishes
the job / does not invent tools / follows her instructions / runs commands (out of 57 each).

| Tier | Model | Place | One job | Finishes | No invented tools | Follows her | Commands |
|---|---|---|---|---|---|---|---|
| ULTRA | Claude Fable 5.2 | #1 | Rs 794 | #1 | #6 | #1 | #3 |
| ULTRA, cheaper | Claude Opus 5.5 | #2 | Rs 497 | #2 | #28 | #4 | #2 |
| HIGH | GPT-6.1 Terra | #10 | Rs 77 | #14 | #6 | #5 | #4 |
| HIGH, Google | Gemini 4 Argon | #11 | Rs 62 | #8 | #32 | #11 | #51 |
| MEDIUM | DeepSeek V4.1 Flash | #30 | Rs 12 | #31 | #38 | #24 | #35 |
| MEDIUM, stronger | Hy4 | #19 | Rs 50 | #15 | #40 | #18 | #24 |
| LOW | GPT-6 Luna | #32 | Rs 7 | #39 | #5 | #26 | #15 |
| LOW backup | Claude Haiku 5.5 | #36 | Rs 7.5 | #33 | #54 | #30 | #20 |

What an AI employee costs a month (5 jobs a day = 150 jobs; helpers and replies use the text tiers on top):

| Tier | A month |
|---|---|
| ULTRA (Fable 5.2 / Opus 5.5) | Rs 1,19,100 / Rs 74,550 |
| HIGH (GPT-6.1 Terra) | Rs 11,550 |
| MEDIUM (DeepSeek V4.1 Flash) | Rs 1,800 |
| LOW (GPT-6 Luna) | Rs 1,050 |

For comparison on the same board: GLM-5.3 (the chat writer) is #33 at about Rs 76 a job (HIGH price, LOW-MEDIUM
place); Qwen 3.8 27B #48 at Rs 34; GLM-5.3-Flash #45 at Rs 13. Board jobs are LMArena's tasks, not Hoola's desks.
