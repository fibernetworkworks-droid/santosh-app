# Hoola's own ElevenLabs: build our own engines, or use APIs? (21 Nov 2026)

Owner, 21 Nov 2026: "FOR HOOLA IS IT POSSIBLE TO CREATE OUR OWN 11LABS OR STRAIGHT TO GET APIS --- WHICH IS COST EFFECTIVE
AND PERFORMANCE EFFICIENT".

Sources, read 21 Nov 2026:
- API prices from each provider's own pricing page: ElevenLabs, Google AI Studio (Gemini), OpenAI, Sarvam, Cartesia,
  Deepgram and Amazon Polly. Google Cloud TTS and Azure gave no numbers.
- Open-model licences from each Hugging Face model card / GitHub licence.
- Our own GPU prices as measured on Modal (`docs/INTERACTIVE_AVATAR_PLAN.md` section 11): L4 $0.80/h, L40S $1.95/h.

Rupees use $1 = Rs 88.

## 1. Price of one minute of speech (~1,000 characters)
| Engine | Per minute | Rs / minute | Indian languages | Clone / design |
|---|---|---|---|---|
| ElevenLabs v4 / v3 / Multilingual v2 | $0.08 | ~7.0 | 90+ / 70+ / 29 | yes |
| ElevenLabs Flash / v4 Turbo (~75-100 ms) | $0.04 | ~3.5 | 32 / 90+ | yes |
| OpenAI tts-1-hd / tts-1 | $0.03 / $0.015 | 2.6 / 1.3 | not stated | no |
| Cartesia Sonic (Scale overage) | ~$0.038 | ~3.3 | "44 languages", Indian not stated | yes |
| Deepgram Aura-2 | $0.03 | 2.6 | not stated | no |
| Amazon Polly generative / neural | $0.03 / $0.016 | 2.6 / 1.4 | not stated | creation free |
| Sarvam Bulbul v3 / v4 Flash (Indian) | - | 3.0 / 2.0 | Indian-first | clone Rs 2 / 1K chars |
| **Gemini 3.8 Flash TTS** (Hoola already runs this model, `voice_ack_tts_model`) | ~$0.014 (*) | **~1.2** | 130+, all 9 major Indian | voice replication + design offered (**not wired in Hoola yet**) |
| Gemini 3.8 Flash-Lite TTS | ~$0.009 (*) | ~0.8 | 100+ | same |
| Own GPU, L4 fully busy (Chatterbox / Indic Parler) | ~$0.005-0.007 (**) | ~0.5 | see 2 | Chatterbox clones, Hindi only among Indian |

(*) Gemini bills $9 / $6 per 1M audio tokens. The minute price assumes 25 audio tokens a second; Google states that rate
only for audio input. These prices double on 1 Jan 2027 (to ~Rs 2.4 / ~Rs 1.6 a minute).

(**) Our own GPU price is NOT measured for voice. It assumes the L4 makes about 2 minutes of speech per minute of GPU
time and is kept busy all the time.

Other ElevenLabs tools, per minute:

| Tool | $ / min | Rs / min |
|---|---|---|
| Voice changer | 0.12 | ~10.5 |
| Voice isolator | 0.12 | ~10.5 |
| Sound effects | 0.12 | ~10.5 |
| Dubbing v2 (speaker's own voice, 92 languages) | 2.20 | ~194 |

## 2. What open models Hoola may sell (from each card)
| Job | Allowed commercially | Not allowed / unclear |
|---|---|---|
| Speech + clone | Chatterbox (MIT; 23 languages, Hindi the only Indian one; every file watermarked); Kokoro (Apache; Hindi only, no clone); OpenVoice v2 (MIT; no Indian); Zonos (Apache; no Indian); Kyutai (CC-BY; en / fr) | F5-TTS, Spark-TTS, Fish S2-Pro (83 languages, the best open model, but needs Fish's paid licence); VibeVoice (research only); CSM (research); XTTS (CPML); IndexTTS-2 (ask bilibili); Orpheus / Dia / Higgs (cards not readable) |
| Indian speech | Indic Parler TTS (Apache; 21 Indian languages, 69 fixed voices, NO cloning) | IndicF5 (MIT, 11 Indian languages, clones, but each cloned voice needs that person's explicit permission - Hoola already requires this; stays lab_only until checked) |
| Voice changer | OpenVoice tone converter (MIT) only | seed-vc (GPL, archived); RVC (needs training per voice, weights unchecked) |
| Voice out of music | - | Demucs (code MIT, weights not stated, archived); RoFormer models not checked |
| Sound from words | - | Stable Audio Open (Stability community licence, revenue cap not verified); TangoFlux, AudioLDM2, MMAudio (non-commercial) |
| Noise removal | DeepFilterNet (MIT / Apache, code + weights; runs on a CPU) | resemble-enhance (weights unchecked) |

## 3. Break-even for our own GPU
- One L4 on all the time costs $0.80 x 720 h = **$576 a month (~Rs 50,700)**.
- Gemini 3.8 Flash TTS is about Rs 1.2 a minute, so our own GPU is cheaper only above **~42,000 minutes (~700 hours) of
  speech a month**. Before that, the GPU sits idle and loses money.
- With per-second billing the GPU can switch off when idle. It then waits ~30-60 s to start (measured for the face
  engine), which is fine for an audiobook and bad for "Speak it".
- Building our own engines also means an ML engineer's time, our own quality checks in 9+ Indian languages, and keeping
  models current. ElevenLabs ships a new model every few months (v3 Jun 2025, v4 Sep 2026).

## 4. Verdict
**Neither alone: a mix.** The Hoola Vocal product, page and history are ours; the engines are rented per use, and each
job goes to the cheapest engine that does it well.

| Job | Engine now | Why |
|---|---|---|
| Speech, dialogue, readings, voice preview | **Gemini 3.8 Flash TTS** (already in use) | ~Rs 1.2 / min, 6x cheaper than ElevenLabs v4, 130+ languages incl. all Indian |
| Clone a voice / design a voice | **Gemini 3.8 voice replication + design** (to wire, after reading its consent terms) | no GPU needed; same engine and price |
| Best Indian voices, option | Sarvam Bulbul (Rs 2-3 / min, Indian company) | a second choice if Gemini's Indian voices fall short in her ear test |
| Noise removal | DeepFilterNet on our own server (CPU) | free, licence clean, better than ffmpeg filters |
| Voice changer, voice out of music, sound from words | **ElevenLabs API** (~Rs 10.5 / min each) | no open model is licence-clean today; pay only when used |
| Dubbing in the speaker's own voice | ElevenLabs Dubbing v2 (~Rs 194 / min), premium only | the cheap path stays Create > Dubbing (Gemini, matched voices) |
| Long audiobooks at big volume (later) | own GPU (Indic Parler / Chatterbox) once usage passes ~700 h a month | only then cheaper |

## 5. Rules for the mix
- Every engine sits behind one Hoola interface, so a job can move engines without the page changing.
- The price is shown before every job, and the cost is counted in Hoola Credits.
- Keys live only in the VPS .env.
- The voice used in calls (Gemini Live) is untouched.

## 6. Not verified
- Gemini's audio-token rate for output.
- Whether Gemini 3.8 voice replication is available on her account, and its terms.
- Google Cloud TTS and Azure prices.
- Any self-hosted voice speed on our GPU.
- The licence of Demucs / RoFormer weights and of Stable Audio Open.
- Audio quality in Indian languages: no ear test of any engine yet.

## 7. GLOBAL, every language (owner, 21 Nov 2026: "MAKE IT GLOBAL NOT FOR INDIA ONLY ... EVERY LANGUAGE")
Language coverage, from each provider's own docs (21 Nov 2026):

| Engine | Languages | Commercial | Notes |
|---|---|---|---|
| Gemini 3.8 Flash TTS | 130+ (table of ~130 rows) | yes | Includes Amharic, Hausa, Igbo, Swahili, Filipino, Vietnamese, Thai, Indonesian, Persian, Nepali, Sinhala, Khmer, Burmese, Cebuano, Kinyarwanda. Not in its table: Zulu, Yoruba, Urdu, Quechua. Also offers designed voices (`prompted`), cloned voices from reference + consent audio (`replicated`, 200 a project, 1-year life) and remixing. |
| ElevenLabs v4 / v3 | 90+ / 70+ | yes | v4 adds Zulu and Urdu; v3 adds Yoruba. No Sinhala, Khmer or Quechua. |
| Azure neural TTS | ~150 locales (count not read whole) | yes (prices not readable) | Has Zulu, Sinhala, Khmer, Burmese, Urdu, Nepali, Amharic. |
| Google Cloud Chirp 3 HD | 53 locales | yes | Narrower than Gemini. |
| Amazon Polly | 41 | yes | No African or SE-Asian languages. |
| Meta MMS TTS | 1,107 | **NO (CC-BY-NC-4.0)** | Cannot be sold; the only engine near "every language". |

What "every language" means honestly:
- The union of the licence-clean engines is roughly 150 languages: Gemini 130+, plus Zulu / Urdu from ElevenLabs v4,
  Yoruba from ElevenLabs v3, and more locales from Azure.
- Hundreds of smaller languages (Quechua, most of the 1,107 in MMS) have no engine Hoola may sell today.
- The page must list every language it supports, auto-detect her text's language, and plainly say when a language has
  no engine. Never a silent fallback to another language.

The routing rule replaces the India-first table in section 4:
1. Gemini 3.8 Flash TTS for every language it covers: speech, dialogue, readings, design, cloning.
2. ElevenLabs v4 for the languages Gemini lacks (Zulu, Urdu; Yoruba on v3), and as the premium choice for any language.
3. Azure as a third engine for locales neither covers (Sinhala, Khmer variants, regional accents). Its prices must be
   read from the Azure calculator before it is wired.
4. Sarvam drops out of the default; it stays an optional regional engine.

Other global rules:
- Every page, list and help text in English. Language names shown in their own script beside the English name.
- Prices in Hoola Credits, which already sell in every country.
- No region-only defaults: the default language is the browser's language, else Auto.
- Voice choice filtered by language + accent + gender + age + use; cloning works in any language the engine speaks.
