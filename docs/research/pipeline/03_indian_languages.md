# Pipeline research 03 - Indian-language benchmarks (read 16 Nov 2026)

For `docs/HOOLA_PIPELINE_PLAN.md` section 8.4 (D8: "DO RESEARCH"). Read live by a research agent on 16 Nov 2026.

**Short answer:** no live public board ranks current frontier models on Indian-language TEXT. Speech is well covered
by one board (voiceofindia.ai). For text, Hinglish and translation, the honest routes are the newest multilingual arena
view and the public Indian test sets run on a shortlist.

## Candidates checked
| # | Benchmark | Who | State 16 Nov 2026 | Covers | Licence | Use |
|---|---|---|---|---|---|---|
| 1 | AI4Bharat Indic LLM Arena | AI4Bharat / IIT Madras + Josh Talks | arena.ai4bharat.org redirects to voiceofindia.ai; **no text leaderboard yet** (LLM / OCR / agent "Soon") | promised 22 languages + Hinglish / Tanglish | "All rights reserved", none found | watch; not usable yet |
| 2 | **voiceofindia.ai speech boards** | same | **live, current (Nov 2026 models)** | STT: 32 models, 21,020 held-out samples, 536 h unscripted phone speech, 15 languages (hi, bn, mr, ta, te, gu, kn, ml, pa, or, as, ur, mai, bho, hne), OI-WER metric; TTS: human-vote Elo, 44,405 votes, 23 models, 10 languages | terms not found; no download / API | **speech in + speech out** |
| 3 | MILU | AI4Bharat (NAACL 2025) | dataset modified 2026-09-08, gated; **no leaderboard** | ~80k MCQ from regional / state exams, 10 Indic languages + English, 41 subjects | data CC BY 4.0, code MIT | text test set (run on a shortlist); ~25 % items translated; MCQ only |
| 4 | IndicGenBench | Google | **repo archived 19 Apr 2026**, no leaderboard | 29 languages: summarisation, translation, QA (human-made, canary strings) | mixed; CrossSum part CC BY-NC-SA (not commercial) | backup test set (skip CrossSum) |
| 5 | IN22 / IndicTrans2 | AI4Bharat | last news Jan 2025, no LLM board | IN22-Gen 1,024 + IN22-Conv 1,503 sentences, 22 languages | CC-BY-4.0 | **translation test set** (chrF++ / COMET) |
| 6 | Vistaar | AI4Bharat | undated | 59 ASR benchmarks, 12 languages | MIT | test sets, not a ranking |
| 7 | LMArena text | arena.ai (HF dataset) | **fresh, 11 Nov 2026** | 29 categories; language views en, zh, ru, de, fr, es, ja, ko, pl + pooled `non_english`; **no Indian language** | CC-BY-4.0 | ranking proxy only |
| 8 | Artificial Analysis Multilingual (Global-MMLU-Lite) | AA | **looks stale** (Gemini 3.1 Pro 94, Opus 4.6 92 top Hindi); near ceiling | Hindi + Bangla only | site non-commercial | rough signal only |
| 9 | MMMLU / Global-MMLU | OpenAI / Cohere | only in labs' model cards | translated MMLU; hi, bn (+ te) | - | not independent |
| 10 | Sarvam IndiVibe | Sarvam (vendor) | 6 Mar 2026 | 110 prompts x 22 languages, native + romanised script; Gemini 3 judge | not checked | prompt set useful; results self-reported |
| 11 | Krutrim BharatBench | Krutrim (vendor) | behind their console; inconsistent coverage | 8 or 10 languages | - | not trustworthy for ranking |
| 12 | IndicMMLU-Pro | arXiv 2501.15747 | no live board | MMLU-Pro in 9 languages incl. Urdu (translated) | - | Urdu gap-filler |
| 13 | Bhashini / Inspect India Evals | MeitY co-author | no Bhashini board; framework tested only small open models | 6 evals, 16 languages | not stated | not a ranking |
| 14 | Hinglish: Indi-RomCoM (arXiv 2606.30790), COMI-LINGUA, CodeMixBench | papers | Indi-RomCoM: 19 models, best Claude Opus 4.6; no data release found | romanised hi / bn / gu / ta; COMI-LINGUA 376K Hinglish items (CC-BY-4.0) | mixed | **no live board**; COMI-LINGUA as a test set |

A 2026 arXiv review (2608.11891): "no single Indic benchmark has achieved broad adoption"; most reported results are
developer-reported.

## Recommendations (the research's)
| For | Use |
|---|---|
| Text (primary) | MILU run on the shortlist through OpenRouter (Urdu from IndicMMLU-Pro) |
| Text ranking proxy | LMArena `non_english` - tiebreaker only |
| Text (backup) | IndicGenBench without CrossSum |
| Translation | IN22-Gen + IN22-Conv, chrF++ + COMET |
| Speech | voiceofindia.ai STT (OI-WER) + TTS Elo |
| Hinglish | Indi-RomCoM findings as reference + a small set from COMI-LINGUA and IndiVibe's romanised prompts, judged pairwise |
| Long writing in the language | nothing public; IndiVibe-style pairwise judging + a native-speaker spot check |

Note: running MILU / IN22 on a shortlist is a **public test set run by Hoola**, not a Hoola-written test. Whether that
fits D1 is her decision (plan section 12).

## Current top models
**LMArena `non_english` (11 Nov 2026):** Gemini 4 Carbon 1534 (google/gemini-4-carbon), Gemini 4 Argon 1523
(google/gemini-4-argon), Claude Fable 5.1 1507 (anthropic/claude-fable-5.1), Claude Opus 5.5 1503
(anthropic/claude-opus-5.5), Claude Opus 5 1500 (anthropic/claude-opus-5), Gemini 4 Hydrogen 1495
(google/gemini-4-hydrogen), Gemini 3.8 Flash 1492 (google/gemini-3.8-flash), Muse Wonder 1491 (meta/muse-wonder), Qwen3.8
Max 1475 (qwen/qwen3.8-max-0902), GPT-5.5 1466 (openai/gpt-5.5). No GPT-6.x in the top 43; Fable 5.2 not yet on it.

**voiceofindia STT (OI-WER %, lower = better):** Bodhan Indic Transcribe Core 3.39, Sarvam Saaras v3 3.69, Bodhan Flex
4.01, Amazon Transcribe 4.69, Microsoft MAI-Transcribe-2 4.79, Gemini 3.5 Transcribe 5.59, Gemini 3.8 Flash 6.25.

**voiceofindia TTS (Elo):** Eleven v4 1119, Gemini 3.8 Flash TTS 1101, Cartesia Sonic-3.6 1100, Gemini 3.1 Flash TTS
1084, Maya 2 Native 1063.

**Correction (checked on OpenRouter's API the same day):** the research said none of the TTS leaders is on OpenRouter.
That is wrong - `elevenlabs/eleven-v4`, `elevenlabs/eleven-v4-turbo`, `google/gemini-3.8-flash-tts` and
`google/gemini-3.8-flash-lite-tts` are listed (output: speech).
