# The writer for each tier (19 Nov 2026)

Owner's asks: "WHY TOOLS ARE NECESSARY FOR WRITER" -> "NOW FIND IT ACCORDING TO ULTRA TO LOW" -> "GO BUILD THE 4 CHANGES".

The writer is the model that runs her whole chat turn: it picks the tools, fills their fields, decides the order and
then writes the reply. So a writer is chosen on BOTH: words (LMArena everyday + non-English boards) and tools
(tau2 airline, OpenRouter's run of 17 Nov; LMArena agent board: place, "follows her", "no invented tools").
Sources: `06_writer_models.md`, `08_worker_atlas.md` (everyday / languages / agent board tables), `14_call_employee_tiers.md`.

| Tier | Writer | Backup + checker | Chat / Hindi | Tools | Rs a reply step |
|---|---|---|---|---|---|
| ULTRA | Claude Opus 5.5 | Gemini 4 Argon | 1514 / 1503 | agent board #2, follows her #4, tau2 75.3% | 8.45 |
| HIGH | Gemini 4 Hydrogen | GPT-6.1 Terra | 1502 / 1495 | agent board #5, follows her #2 | 3.17 |
| MEDIUM | GLM-5.3 | DeepSeek V4.1 Flash | 1475 / 1462 | tau2 77.3%, no invented tools #13 | 0.22-2.77 |
| LOW | DeepSeek V4.1 Flash | GLM-5.3-Flash | 1464 / 1450 | tau2 75.1%, agent board #30 | 0.10 |

Why not the v0.999.9 picks:
- ULTRA Gemini 4 Argon writes best (1529) but is #32 of 57 at not inventing tools -> backup.
- HIGH Gemini 3.8 Flash: tau2 71.3% -> it stays HIGH's reader (pictures 1317, OCR 1332, PDFs #7, audio, maths #4).
- MEDIUM GLM-5.3-Flash: same words as GLM-5.3 (3 points) but weaker tools (75.6%, follows her #48) -> GLM-5.3, the
  writer her live tests ran on.
- LOW GPT-6 Luna: 1388 chat, tau2 67.3%, twice DeepSeek's price -> DeepSeek V4.1 Flash.

Not known: GPT-6.1 Terra's chat score (not on the everyday top 20); whether Google models answer on her OpenRouter
account (Gemini 4 Carbon was refused on 17 Nov); Hinglish (no board measures it - a parity card per tier on her
messages settles it).
