# Realtime / conversational voice AI landscape (as of 11 Nov 2026)

Scope: options for a live, human-feeling voice call (Hoola's call path). Research done 11 Nov 2026 with web search + primary pages where reachable. Many pricing figures could only be found on third-party aggregators; those are marked. Items known only from model knowledge (pre-2026) are marked "from memory, not re-verified".

## Commercial realtime voice platforms: what each is, architecture, languages, latency, emotion, voices, price

### Takeaway
The quality leaders on the independent Artificial Analysis Speech-to-Speech Index (late 2026 snapshot) are Phonic 1, xAI/SpaceXAI Grok Voice 3.0, OpenAI GPT-Live-1, Google Gemini 3.8 Live Extended Thinking and ElevenLabs Eleven Realtime v1 Max. For breadth of languages, Gemini Live is the clear leader (99 languages listed, incl. 14 South Asian ones). It is also the cheapest of the big three per minute (~$0.02-0.03/min, aggregator prices). Note that Gemini 3.8 removed "affective dialog" as a switch.

### Cited Findings

**Google Gemini Live API**
- Current models: `gemini-3.8-live`, `gemini-3.8-live-extended-thinking`, `gemini-3.1-flash-live-preview`, `gemini-2.5-flash-native-audio-preview-12-2025` — [Gemini Live capabilities guide](https://aistudio.google.com/docs/live-api/capabilities)
- Vertex docs list gemini-3.8-live as GA / Recommended, with native audio, VAD, affective dialog, proactive audio, tool use and live avatar. Older `gemini-live-2.5-flash-native-audio` is scheduled for discontinuation on 13 Dec 2026 — [Vertex Live API overview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/live-api) (search-snippet level)
- 99 supported languages. Indian/South Asian ones: Assamese, Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Nepali, Odia, Punjabi, Sindhi, Sinhala, Tamil, Telugu, Urdu. Native-audio models pick the language automatically and switch mid-conversation. You can't set a language code, only restrict the language through system instructions — [capabilities guide](https://aistudio.google.com/docs/live-api/capabilities)
- CONFLICT: the Vertex overview and the 2.5 Flash docs still say "24 supported languages", which is probably a stale figure — [Vertex overview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/live-api); [2.5 Flash Live](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-live-api)
- Affective dialog: only on 2.5 Flash Live (v1beta, `enable_affective_dialog`). It is REMOVED on 3.8 Live (the field must be omitted) and not supported on 3.1 Flash Live — [capabilities guide](https://aistudio.google.com/docs/live-api/capabilities)
- Proactive audio: always on for 3.8 Live; `proactive_audio:false` returns an error. Configurable on 2.5, not supported on 3.1 Flash Live — [capabilities guide](https://aistudio.google.com/docs/live-api/capabilities)
- Thinking: 3.8 Live uses interleaved reasoning (no `thinkingLevel`). The 3.8 Extended Thinking variant takes low/medium/high and allows only NON_BLOCKING function calls. 3.1 Flash Live defaults to `minimal` and supports only synchronous function calls — [capabilities guide](https://aistudio.google.com/docs/live-api/capabilities)
- Session limits: 15 min audio-only, 2 min audio+video, extendable with session management. Context is 128k tokens on native-audio models. Audio is 16 kHz PCM in, 24 kHz out. Voices are the TTS voice set (no count published on that page) — [capabilities guide](https://aistudio.google.com/docs/live-api/capabilities)
- Gemini 3.1 Flash Live (26 Mar 2026): "90+ languages", better background-noise filtering, better instruction following, picks up pitch/pace, "step change in latency" (no figures) — [Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-3-1-flash-live/)
- Separate live speech translation model: `gemini-3.5-live-translate-preview`, 70+ languages — [live translate docs](https://ai.google.dev/gemini-api/docs/live-api/live-translate) (snippet)
- Price, 3.8 Live (aggregators, not Google's page): audio in ~$3/M tokens (~$0.005/min), audio out ~$12/M (~$0.018/min), text $0.75/$4.50 per M. Extended Thinking reasoning tokens bill at the text output rate — [cloudprice.net](https://cloudprice.net/models/google-gemini-3-8-live); [tokenkarma](https://tokenkarma.app/blog/gemini-live-api-pricing-voice-agents-2026/)
- AA index: Gemini 3.8 Live Extended Thinking (High) scores 82.6 (Big Bench Audio 97.7%, time to first audio 1.35 s). Gemini 3.8 Live scores 74.5 (91.7%, 1.18 s) — [Artificial Analysis S2S leaderboard](https://artificialanalysis.ai/models/speech-to-speech)
- Hoola's own measurement: Gemini Live bills the whole context (tool list, persona, brief, the call's audio so far) on every reply. One call measured ~13.5k tokens a reply, ~Rs 4.8 a call — [repo CLAUDE.md v0.626/v0.629 lines](/home/user/santosh-app/CLAUDE.md)

**OpenAI**
- gpt-realtime-2.1 (token-billed, speech-to-speech): audio $32/M in ($0.40 cached), $64/M out. gpt-realtime-2.1-mini: $10/$0.30/$20. Rough per-minute estimates are ~$0.04-0.10/min (2.1) and ~$0.016/min (mini), but these depend heavily on caching and prompt length — [aireiter](https://aireiter.com/blog/openai-realtime-api-pricing); [layer3labs](https://www.layer3labs.io/guides/openai-realtime-api-pricing) (secondary)
- Measured production data (older gpt-realtime-mini): $0.063-0.146/min — [hackernoon](https://hackernoon.com/openai-realtime-api-pricing-in-2026-real-world-data-from-4000-measured-sessions) (secondary)
- Per-minute siblings: gpt-realtime-translate $0.034/min, gpt-realtime-whisper (streaming STT) $0.017/min. One source says the original gpt-realtime shuts down 20 Jan 2027 — [search summary of the pricing blogs above] (unverified against openai.com)
- GPT-Live-1 (API from 10 Sep 2026) is a full-duplex voice layer that listens and speaks at once and hands reasoning to a backend model you pick. Voice layer costs $0.05/min, and backend model and tools are billed separately — [cellcog](https://cellcog.ai/blog/gpt-live-1/); [runtimewire](https://runtimewire.com/article/openai-gpt-live-1-1-six-languages) (secondary)
- GPT-Live-1.1 (15 Oct 2026, ChatGPT first, API "coming soon"): native voices for French, German, Hindi, Japanese, Korean, Mexican Spanish + English. OpenAI publishes no full language list and no per-language test results — [Notebookcheck](https://www.notebookcheck.net/ChatGPT-Voice-GPT-Live-1-1-brings-new-voices-for-six-languages.1425810.0.html); [datanorth](https://datanorth.ai/news/gpt-live-1-1-new-voices)
- AA index: GPT-Live-1 (Astra, medium) scores 83.2 (Big Bench Audio 90.1%, TTFA 1.34 s) and GPT-Realtime-2.1 High scores 75.2 (95.8%, 1.21 s). A third-party blog says a GPT-Live-1 row at 81.5 was a routing configuration rather than one model — [AA leaderboard](https://artificialanalysis.ai/models/speech-to-speech); [orcarouter](https://www.orcarouter.ai/blog/gpt-live-1-tops-speech-to-speech-index)

**xAI / SpaceXAI Grok Voice and Phonic**
- Phonic 1 (High) is #1 on the AA index at 87.1 (Big Bench Audio 98.9%, TTFA 0.61 s). Grok Voice 3.0 is #2 at 86.9 (98.5%, 0.81 s), and Grok Voice 2.0 scores 81.3 (TTFA 0.70 s) — [AA leaderboard](https://artificialanalysis.ai/models/speech-to-speech)
- The AA index launched 23 Jun 2026 and combines Big Bench Audio, Full Duplex Bench and τ-Voice, equally weighted. At launch GPT-Realtime-2 (High) led at 77.2% — [AA announcement](https://artificialanalysis.ai/articles/announcing-the-artificial-analysis-speech-to-speech-index)

**ElevenLabs**
- Agents platform: $0.08 per call minute on every plan, $0.16/min above the concurrency cap, LLM billed separately. Sources disagree on telephony and LLM markup — [getmacha](https://www.getmacha.com/blog/elevenlabs-agents-pricing-explained); [cloudzero](https://www.cloudzero.com/blog/elevenlabs-pricing/) (secondary)
- Eleven v3 supports 74 languages (help page; the models page says "70+"). v3 Conversational is ~280 ms ("low latency") with 29 languages. Flash v2.5 is <75 ms, and its India agents page lists 32 languages incl. Hindi and Tamil — [ElevenLabs languages](https://elevenlabs.io/docs/help-center/other/what-languages-do-you-support); [models FAQ](https://elevenlabs.io/docs/help-center/technical/what-models-do-you-offer-and-what-is-the-difference-between-them); [India agents](https://start.elevenlabs.io/india/agents)
- Eleven Realtime v1 Max (its own speech-to-speech model) scores 77.3 on the AA index (Big Bench Audio 98.8%) with TTFA 0.57 s, the fastest of the top 10 — [AA leaderboard](https://artificialanalysis.ai/models/speech-to-speech)

**Cartesia Sonic (TTS for cascades)**
- Sonic 3 / 3.x: 42-44 languages incl. Hindi. Vapi lists nine Indian languages. Vendor latency is "sub-90 ms", Vapi measured a 166 ms median including network, and the changelog says ~190 ms. sonic-3.6 has been GA since 27 Aug 2026 — [Vapi humanness index](https://humannessindex.vapi.ai/models/cartesia-sonic-3); [cekura](https://www.cekura.ai/discover/cartesia-text-to-speech); [SignalWire docs](https://signalwire.com/docs/platform/voice/tts/cartesia)

**Hume EVI**
- EVI 4 mini brings Octave 2's capabilities to speech-to-speech in 11 languages. It still needs an external LLM because it "doesn't yet generate its own language natively". Overage is about $0.02-0.035/min by tier (EVI 3 was $0.06 on Pro). The public pricing page was reportedly removed in Oct 2026 — [Hume Octave 2 launch](https://hume.ai/blog/octave-2-launch); [usagepricing](https://www.usagepricing.com/blueprint/activity/hume-ai-2026-06-30-evi-mini-octave-models)

**Amazon Nova Sonic**
- Output languages: English, French, Italian, German, Spanish, Portuguese and Hindi, with automatic switching. v1 (`amazon.nova-sonic-v1:0`) reached end of life in Sep 2026. A "Nova 2.5 Sonic" name appears but couldn't be verified — [getstream](https://getstream.io/blog/speech-apis/) (secondary)

**Sarvam AI (India, cascaded stack)**
- Voice agents run Saaras v4 ASR (22 Indian languages + English, auto-detect, code-mixed in and out) → Sarvam LLMs auto-routed (incl. `sarvam-105b-conversations`, "colloquial, code-mixed Indic") → Bulbul v3/v4 TTS (11 languages, 176 voices, 0.5-2x pace, up to 48 kHz). Platform price is "from ₹3 a minute". No bring-your-own model at any stage — [Sarvam voice-agent models docs](https://docs.sarvam.ai/voice-agents/build/models.md)
- Saaras v4 and Bulbul v4 were announced 30 Jul 2026. The "<500 ms" latency is a vendor claim, and ~70 ms is the STT stage only — [Sarvam Epoch](https://www.sarvam.ai/epoch/summary); [AIM](https://analyticsindiamag.com/ai-features/sarvams-biggest-leap-yet-all-that-happened-at-epoch)

**Other speech-to-speech entries on AA (late 2026)**
- Qwen Audio 3.0 Realtime Plus: Big Bench Audio 99.2%, TTFA 1.54 s, input ~$0.0331/hr, the lowest listed price. StepAudio 3 Realtime: 99.7% but TTFA 8.83 s. Deepslate Opal: 85.0%, 0.44 s. Raon SpeechChat: 57.5%, 0.04 s — [AA leaderboard](https://artificialanalysis.ai/models/speech-to-speech)

### Inferences
- For a Hinglish/Indian-language 24/7 call, Gemini Live remains the strongest single-vendor speech-to-speech choice on language breadth and price. Hoola already runs it.
- OpenAI GPT-Live and Grok lead on reasoning and duplex scores, but neither publishes Indian-language coverage. Hindi is the only Indian language with confirmed native OpenAI voices.
- "Emotion" is now mostly implicit (prosody understanding, proactive audio) rather than a switch. Google removed the affective-dialog flag on 3.8, so any code that sends it must stop (Hoola already treats this as a rule).

### Gaps
- No official Google or OpenAI pricing page was fetched; all per-minute figures are aggregator conversions.
- AA leaderboard price columns were mostly empty, and the page carries no explicit data date ("as of July 2026" for one table).
- No independent per-language quality benchmark (e.g. Hindi or Tamil naturalness or WER) was found for any realtime S2S model.
- Deepgram and AssemblyAI voice agents, Microsoft Azure Voice Live and Sesame's commercial product weren't researched (call budget). Their current prices and languages are unknown here.

## Open models: what exists and what the licence allows

### Takeaway
Open full-duplex speech-to-speech in Indian languages is still thin. Josh Talks' Human-1 (Hindi, built on Moshi) is the one clear example, and NVIDIA's Nemotron VoiceChat is the strongest general open duplex model. For cascades, clean commercial open TTS with Hindi is Chatterbox (MIT), Indic Parler-TTS (Apache-2.0), IndicF5 (MIT, said to be commercial-OK), Veena (Apache-2.0) and Kokoro (Apache-2.0, weak Hindi). XTTS-v2, F5-TTS, Fish Speech and MMS-TTS are non-commercial.

### Cited Findings
- Josh Talks Human-1 is an open Hindi full-duplex conversational model trained on 26,000 h of two-person Hindi conversations (14,695 speakers). The dataset is proprietary and only the weights are open. A community list says it is built on Moshi. Its licence wasn't found — [AIM](https://analyticsindiamag.com/ai-news/josh-talks-launches-full-duplex-conversational-ai-model-in-hindi); [Awesome-Full-Duplex-SDM PR](https://github.com/Ruiqi-Yan/Awesome-Full-Duplex-SDM/pull/9)
- NVIDIA NemotronLabs VoiceChat: 11B, full-duplex, with tool calling. Code is on the NeMo Speech branch and weights are on HF (paper Sep 2026) — [arXiv 2609.21967](https://arxiv.org/pdf/2609.21967). AA also wrote about it as a "speech Pareto" leader in Mar 2026 — [AA article](https://artificialanalysis.ai/articles/nemotron-3-voicechat-leader-speech-pareto)
- Other open duplex models: KRAFTON Raon-SpeechChat (9B, English/Korean), NVIDIA PersonaPlex (7B), and DuplexCascade, a VAD-free cascade that talks in micro-turns — [search summary + arXiv 2603.09180](https://arxiv.org/abs/2603.09180). Active 2026 research covers tool calls in duplex models, backchannel control, and self-listening — [arXiv 2609.19334](https://arxiv.org/pdf/2609.19334); [2609.29418](https://arxiv.org/pdf/2609.29418); [2609.05592](https://arxiv.org/pdf/2609.05592)
- TTS licences:
  - Kokoro-82M: Apache-2.0
  - Chatterbox: MIT, 23 languages
  - Orpheus: Apache-2.0 code, Llama-derived weights (check before shipping)
  - XTTS-v2: Coqui Public Model License, non-commercial, also covers outputs; Coqui is shut down so no commercial licence can be bought
  - F5-TTS: MIT code, CC BY-NC 4.0 weights
  - Fish Speech S2 Pro: Fish Audio Research License, non-commercial; one source says Apache, which conflicts — [Cartesia licence guide](https://www.cartesia.ai/learn/open-source-tts); [codesota](https://www.codesota.com/guides/tts-models); [dograh](https://www.dograh.com/hub/blogs/kokoro-vs-chatterbox-vs-xtts)
- Hindi open TTS (24 Oct 2026 review):
  - IndicF5: MIT, maintainer says "completely open for commercial usage", clone only with permission; skips words in long paragraphs and garbles numbers/OTPs
  - Indic Parler-TTS: Apache-2.0, 69 speakers set by text description, 21 languages; open question whether the training-data CC terms reach outputs
  - Indic-Speak (Bodhan): custom licence, written sign-off needed before offering it as an API
  - Veena (Maya Research): Apache-2.0, 4 voices, Hindi/English
  - Kokoro: Hindi graded C, crashes on long Hindi passages
  - XTTS-v2: non-commercial
  - MMS-TTS Hindi: CC BY-NC
  - Hinglish isn't documented for any of them — [Sonex Labs](https://www.sonexlabs.com/blog/best-open-source-hindi-tts)
- Indic Parler-TTS model card: Apache-2.0. Training data is GLOBE, IndicTTS, IndicVoices and IndicVoices-R (CC BY 4.0) — [HF card](https://huggingface.co/ai4bharat/indic-parler-tts-pretrained)
- Hoola's own lab: its registry refuses F5-TTS, XTTS-v2, Fish and Wav2Lip on licence grounds and marks IndicF5 "lab_only". Chatterbox (hi+en) and Indic Parler (hi+en) ran OK on a GPU — [repo CLAUDE.md v0.461](/home/user/santosh-app/CLAUDE.md). This conflicts with the "MIT, commercial OK" reading of IndicF5 above, likely because Hoola's verdict was conservative about the F5 base. Recheck before shipping.

### Inferences
- From memory, not re-verified for 2026: Kyutai Moshi = code Apache/MIT, weights CC-BY 4.0; Kyutai Unmute = an open cascaded STT→LLM→TTS wrapper; Sesame CSM-1B = Apache-2.0, English-centred; Dia (Nari Labs) = Apache-2.0, English; Qwen2.5/3-Omni = Apache-2.0 open omni models. If Human-1 is a Moshi fine-tune, its weights may inherit CC-BY terms, but this is unconfirmed.
- Open full-duplex is research-grade outside English/Korean, Hindi excepted via Human-1. A production Indian-language call on open weights today would be a cascade: Indic ASR → LLM → Indic Parler / Chatterbox / Veena TTS.

### Gaps
- No primary 2026 source was fetched for Moshi/Unmute, Sesame CSM, Orpheus multilingual, Dia, Qwen-Omni or Qwen-TTS licences and languages.
- Human-1's licence and HF availability weren't confirmed.
- No measured Hindi naturalness (MOS) comparison between open models was found.

## Full-duplex vs cascaded: trade-offs

### Takeaway
Full-duplex speech-to-speech wins on naturalness: overlap, backchannels, barge-in, prosody carried through, sub-second first audio. Cascades win on control (pick any LLM and TTS voice, inspect text, check tools, cost per stage) and language coverage. The market is converging on hybrids: a duplex "voice layer" plus a backend brain (GPT-Live-1's design, and Hoola's own Gemini-speaks / Haiku-brain split since v0.630).

### Cited Findings
- GPT-Live-1 explicitly splits a full-duplex listening/speaking layer ($0.05/min) from a backend model you pick — [cellcog](https://cellcog.ai/blog/gpt-live-1/)
- Sarvam's production Indian stack is a cascade (Saaras → LLM → Bulbul) with code-mixing at each stage — [Sarvam docs](https://docs.sarvam.ai/voice-agents/build/models.md)
- The AA index adds Full Duplex Bench and τ-Voice (tool-using tasks), not just reasoning, so turn-taking and tool use are now scored — [AA announcement](https://artificialanalysis.ai/articles/announcing-the-artificial-analysis-speech-to-speech-index)
- Research is closing duplex gaps in tool calling, streaming user transcription and backchannel control — [arXiv 2609.19334](https://arxiv.org/pdf/2609.19334); [arXiv 2609.15759](https://arxiv.org/pdf/2609.15759); [arXiv 2609.29418](https://arxiv.org/pdf/2609.29418)
- A cascade can approach duplex feel with micro-turns and no VAD (DuplexCascade) — [arXiv 2603.09180](https://arxiv.org/abs/2603.09180)
- Cost hazard for S2S: Gemini Live re-bills the whole context every reply (Hoola measured; trimming tools and persona cut ~22k → ~13.5k tokens a reply) — [repo CLAUDE.md v0.626-v0.629](/home/user/santosh-app/CLAUDE.md)
- Latency: best S2S time to first audio is ~0.57-0.81 s (Eleven Realtime, Phonic, Grok), while Gemini 3.8 and GPT-Live are ~1.2-1.35 s — [AA leaderboard](https://artificialanalysis.ai/models/speech-to-speech). Cascade TTS-only stages are ~75 ms (ElevenLabs Flash) to ~166-190 ms (Cartesia measured), plus STT and LLM time — [ElevenLabs models](https://elevenlabs.io/docs/help-center/technical/what-models-do-you-offer-and-what-is-the-difference-between-them); [Vapi](https://humannessindex.vapi.ai/models/cartesia-sonic-3)

### Inferences
- For Hoola, the existing hybrid (Gemini Live voice + Haiku brain via `santosh_kaam`) matches the industry direction. The main remaining levers are the per-reply context size and the choice of voice layer.
- A cascade is the only way to get a specific Indian TTS voice (Sarvam Bulbul, a cloned voice, or an open model) on a call. The cost is turn-taking naturalness and extra latency per hop.

### Gaps
- No head-to-head blind listener study of duplex vs cascade in Hindi/Hinglish was found. One Sep 2026 blog discusses benchmarks vs listener preference in general — [digitalapplied](https://www.digitalapplied.com/blog/realtime-voice-models-benchmarks-vs-listener-preference) (not read).

## Best for Indian languages and Hinglish

### Takeaway
- Widest single-model coverage: Gemini Live (15 South Asian languages, auto-switching).
- Deepest India-specific code-mixing: Sarvam (22-language ASR, code-mixed in and out, 11-language TTS, from ₹3/min).
- ElevenLabs Flash v2.5: Hindi/Tamil and more at <75 ms TTS for cascades.
- OpenAI: Hindi voices confirmed in ChatGPT, with no published Indian-language list for the API.
- Open: Human-1 for Hindi duplex research; Indic Parler-TTS, Chatterbox and Veena for commercial-clean Hindi TTS.

### Cited Findings
- Gemini Live's language list includes as, bn, gu, hi, kn, ml, mr, ne, or, pa, sd, si, ta, te, ur — [capabilities guide](https://aistudio.google.com/docs/live-api/capabilities)
- Sarvam: code-mixed audio and text in ASR, mixed-script TTS, LLM replies "colloquial, code-mixed Indic". Hinglish isn't named explicitly — [Sarvam docs](https://docs.sarvam.ai/voice-agents/build/models.md)
- ElevenLabs India agents page: 32 languages for Flash v2.5, incl. Hindi and Tamil — [ElevenLabs India](https://start.elevenlabs.io/india/agents)
- Cartesia: nine Indian languages per Vapi — [Vapi](https://humannessindex.vapi.ai/models/cartesia-sonic-3)
- Nova Sonic: Hindi is the only Indian language — [getstream](https://getstream.io/blog/speech-apis/)
- OpenAI GPT-Live-1.1: Hindi voices (ChatGPT first, API later) — [Notebookcheck](https://www.notebookcheck.net/ChatGPT-Voice-GPT-Live-1-1-brings-new-voices-for-six-languages.1425810.0.html)
- Hume EVI 4 mini: 11 languages; whether any Indian language is included wasn't confirmed — [Hume](https://hume.ai/blog/octave-2-launch)
- No open Hindi TTS documents Hinglish handling — [Sonex Labs](https://www.sonexlabs.com/blog/best-open-source-hindi-tts)

### Inferences
- Hinglish (Roman-script Hindi/English mixing) is best served by S2S models trained on mixed speech (Gemini) or by Sarvam's code-mixed stack. Most TTS-only options need Devanagari or English input, so a cascade would need a transliteration step.
- For lower-resource Indian languages (Odia, Assamese, Sindhi), Gemini Live is likely the only realtime S2S option listed. Quality there is unmeasured.

### Gaps
- No independent Hinglish or Indian-language naturalness or accuracy benchmark for any realtime model was found. Choosing between Gemini, Sarvam and ElevenLabs for Hinglish needs Hoola's own ear test (Hoola has an ear-test harness, v0.232/v0.241).
- Sarvam per-minute model pricing and measured end-to-end latency are not public.
