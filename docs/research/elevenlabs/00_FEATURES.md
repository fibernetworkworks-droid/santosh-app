# ElevenLabs - every feature, and where Hoola Vocal stands (read 21 Nov 2026)

Owner, 21 Nov 2026: "THIS IS HOOLA OWN 11LABS --- EXTRACT ALL FEATURES FROM 11LABS FIRST".

Sources, all read 21 Nov 2026:
- the docs index `elevenlabs.io/docs/llms.txt`, its overview / API / Creative indexes in full, and the Agents index plus
  `overview/models.md` in part;
- the product pages: pricing, home, creative, text-to-speech, music, video, agents, voice-cloning, voice-changer,
  voice-isolator, dubbing-studio, sound-effects, studio, voice-library, speech-to-text, avatars, image, voice-design,
  pricing/api and pricing/agents;
- elevenreader.io.

`elevenlabs.io/audio-native` gave a 404. Not read: the per-endpoint API reference pages, the Help Center and the
changelog. Their own pages contradict each other on several numbers (voices 10,000+ / 17,500+ / 20,000+; voice changer
29 / 70+ languages); both figures are given where they clash. Per-plan numbers from flattened tables are marked
"(table)".

**Status column** (Hoola Vocal today, from the 21 Nov walk of /console/vocal):
- HAVE - built and working
- PART - partly built
- NO - not built
- NC - built but its engine is not connected
- ELSE - lives in another part of Hoola

## 0. The shape of ElevenLabs
Three products on one credit pool: **ElevenCreative** (the app), **ElevenAgents** (voice / chat agents) and
**ElevenAPI** (developers). Claims: 90+ languages, 17,500+ voices, 5M words a minute. Web app, iOS / Android apps,
MCP servers, SDKs.

## 1. Models (their engines)
| Model | Languages | Limit / speed | Price (API) |
|---|---|---|---|
| Eleven v4 (Sep 2026, "most emotive") | 90+ | 100,000 chars per request (docs) | $0.08 / 1K chars |
| Eleven v4 Turbo | 90+ | ~100 ms | $0.04 / 1K |
| Eleven v3 | 70+ | 5,000 chars, audio tags, multi-speaker | $0.08 / 1K |
| Eleven v3 Conversational | 70+ | ~165-280 ms, custom audio tags | $0.04 / 1K |
| Multilingual v2 | 29 | 10,000 chars | $0.08 / 1K |
| Flash v2.5 / Turbo v2.5 | 32 | ~75-100 ms, 40,000 chars | $0.04 / 1K |
| Flash v2 (English) | 1 | ~135 ms, 30,000 chars | - |
| Voice Design v3 / ttv v2 | 70+ / 29 | - | - |
| Voice Changer sts v2 | 29 (page says 70+) | ~400 ms | $0.12 / min |
| Scribe v3 / v3 Live / v2 / v2 Medical / v3 Live Medical | 90+ (99 on one page) | Live ~150 ms | $0.20 / hr batch, $0.22 / hr live |
| SFX v3 (text to sound) | - | 30 s, loops | $0.12 / min |
| Music v2.5 / v2 | many | 5 min a track | $0.15 / min |
| Eleven Realtime v1 Mini / Max (speech-to-speech for agents) | 90+ | fast / tool calling | $0.08 / min + LLM |
| Dubbing v2 (May 2026) | 92 | carries the speaker's emotion | $2.20 / min |
| Dubbing v1 | 29 | watermark / none | $0.33 / $0.50 per min |

Hoola Vocal today: ONE speech engine (Gemini TTS, 22 voices, 11 languages on screen) + the GPU lab (Chatterbox /
Indic Parler, not connected live).

## 2. Text to Speech
| # | Feature | Hoola |
|---|---|---|
| 1 | Type / paste text -> speech, pick voice + model | HAVE (no model choice) |
| 2 | 90+ languages, language auto-detected, mixed-language text read right | PART (11 Indian + English, no Auto) |
| 3 | Audio tags in the text: [whispers] [laughs] [sighs] [excited] [sarcastic] etc. (v3 / v4) | NO |
| 4 | Voice settings: stability, similarity, style exaggeration, speaker boost, speed | PART (style 6 presets + speed only) |
| 5 | Long text: up to 100,000 chars (v4), request stitching keeps the flow across pieces | HAVE 40,000 (cut at sentence ends, no stitching) |
| 6 | Pronunciation dictionaries (alias + IPA / CMU phonemes), shareable, used by API / Studio / agents | PART (alias words only, no phonemes) |
| 7 | Text normalisation (numbers, dates, currency read right) | PART (left to the engine) |
| 8 | Regenerate / several takes, compare | NO |
| 9 | History: every generation, play, download, re-use settings | HAVE (200 kept, no "use these settings again") |
| 10 | Download MP3 (default), WAV, M4A, FLAC; 44.1 kHz / 192 kbps on higher plans; PCM, u-law / A-law, Opus via API | PART (WAV only) |
| 11 | Streaming output (words start playing before the whole file is done), WebSocket input streaming | NO |
| 12 | Multi-context WebSocket, low-latency modes | NO (calls use Gemini Live separately) |
| 13 | Best-practice guides (pauses with breaks, emotion by context) | NO |

## 3. Text to Dialogue
| # | Feature | Hoola |
|---|---|---|
| 14 | Several speakers, each a voice, one file, natural turn-taking + interruptions (v3 / v4) | PART (lines joined with a gap, no overlap / interruptions) |
| 15 | Audio tags per line | NO |
| 16 | Dialogue WebSocket streaming | NO |
| 17 | Podcast from a document / URL (Studio "create podcast": two hosts discuss your text) | NO |

## 4. Voices
| # | Feature | Hoola |
|---|---|---|
| 18 | Voice Library: 17,500+ community voices, filter by language, accent, gender, age, use case (narration, ads, characters, conversational, social, TV, education, story), collections (TikTok, games, meditation...) | PART (22 voices, filter male / female only) |
| 19 | Preview every voice before use | HAVE (each Hear is a new paid call, nothing kept) |
| 20 | My Voices: saved / added voices, folders, labels | PART (list only) |
| 21 | Instant Voice Clone: 10 s - 5 min sample, upload or record in the browser, 32+ languages | NC (needs the GPU lab; upload only, no in-browser record) |
| 22 | Professional Voice Clone: 30 min - 3 h, trained model, voice verification (read a line to prove it is you) | NO |
| 23 | Voice Design: describe a voice -> 3 previews -> save; age, gender, pitch, accent, emotion, audio quality | NC (description saved, no previews) |
| 24 | Voice Remix: change an existing voice's gender, accent, style, pacing, quality | NO |
| 25 | Share your voice to the library + earn payouts ($1M paid by Oct 2024) | NO (product decision) |
| 26 | Iconic voices (licensed famous voices: Michael Caine, Stan Lee...) | NO (and never without a licence) |
| 27 | Voice slots by plan (3 -> 2,200 custom voices) | PART (30 a user) |
| 28 | Captcha / consent / safety: no clone of public figures, no-go voices list | HAVE (consent tick, refuses named people) |

## 5. Voice Changer (speech to speech)
| # | Feature | Hoola |
|---|---|---|
| 29 | Record or upload, get it back in another voice, keeping emotion, timing, accent, whispers, laughs | NO (no model) |
| 30 | Remove background noise on the way | NO |
| 31 | Up to 50 MB / 5 min per conversion; MP3 / WAV / AAC / video | NO |
| 32 | Change into your own clone | NO |

## 6. Voice Isolator
| # | Feature | Hoola |
|---|---|---|
| 33 | Removes noise, music, reverb, wind, street, chatter, mic feedback; keeps the voice | PART (ffmpeg noise filters only, no music / chatter removal) |
| 34 | 500 MB / 1 hour, audio or video in, WAV / MP3 / FLAC / OGG / AAC | PART (limits not stated) |

## 7. Dubbing
| # | Feature | Hoola |
|---|---|---|
| 35 | Dub a video / audio / URL into 92 languages | ELSE (Create > Dubbing: 16 languages, 4 at once, 3 min, own video only) |
| 36 | Clones each original speaker automatically (same voice in the new language) | NO (matched voices) |
| 37 | Carries emotion and delivery (audio-to-audio, v2) | NO |
| 38 | Speaker detection, sync-aware translation | ELSE (have) |
| 39 | Dubbing Studio editor: transcript + translation per line, regenerate a line, move clips on a timeline, per-speaker voice | NO |
| 40 | Bring your own transcript / translation | NO |
| 41 | Subtitles editor + export SRT / VTT | NO (Flow exports SRT for transcripts) |
| 42 | Watermark / no watermark | NO |
| 43 | Productions: human translators, casting, mixing (managed service) | NO (service, not software) |

## 8. Sound Effects
| # | Feature | Hoola |
|---|---|---|
| 44 | Describe any sound -> 4 takes in seconds | NO (10 code-made game sounds only) |
| 45 | Up to 30 s, length setting, seamless loop | NO |
| 46 | Prompt influence, several instructions in one prompt | NO |
| 47 | Sound library / categories, publish to Explore | NO |
| 48 | Soundboard ("SB1 Infinite") | NO |
| 49 | MP3 44.1 kHz or WAV 48 kHz, royalty-free | PART (WAV) |

## 9. Music
| # | Feature | Hoola |
|---|---|---|
| 50 | Song / instrumental from a prompt, any language, up to 5 min | ELSE (Create > Music chat, 40 languages + Auto) |
| 51 | Composition plans (sections, lyrics, styles as structured data) | ELSE PART (lyrics by parts) |
| 52 | Inpainting: change one section of a song | NO (free edits make a new version) |
| 53 | Stems (2 / 4 / 6), audio reference, finetunes on your sound, vocal library | NO |
| 54 | Music Marketplace, ElevenMusic app, release to Spotify / Apple | NO |

## 10. Speech to Text (Scribe)
| # | Feature | Hoola |
|---|---|---|
| 55 | Transcribe audio / video, 90+ languages, 3 GB files | ELSE (Hoola Flow / Kaan, Whisper) |
| 56 | Speaker labels up to 32, word timestamps, sound events (laughter, footsteps) | ELSE PART |
| 57 | Keyterms (1,000 names / brands), entity detection, PII redaction, number formatting | ELSE PART (vocabulary list) |
| 58 | Realtime transcription ~150 ms, VAD, turn detection | ELSE (live captions) |
| 59 | Transcript editor: edit the text, export captions | ELSE PART (exports, no editor) |
| 60 | Medical model, multichannel, async webhooks | NO |

## 11. Forced alignment
| # | Feature | Hoola |
|---|---|---|
| 61 | Text + audio in -> a timestamp for every word | NO |

## 12. Studio (long form)
| # | Feature | Hoola |
|---|---|---|
| 62 | Projects for audiobooks, podcasts, narrated video; import EPUB / PDF / TXT / HTML / URL | PART (paste text into chapters, no import) |
| 63 | Chapters, regenerate a paragraph or a line, speech correction (edit the text, same voice redoes only that bit) | PART (whole chapter re-read) |
| 64 | Multi-cast: a different voice per character / paragraph | NO (one voice a reading) |
| 65 | Timeline: voiceover + music + SFX + video on tracks, trim / merge | NO |
| 66 | Video in (MP4 / MOV), auto captions, styled, multilingual, export | NO |
| 67 | Studio Agent (AI co-editor: scripts, picks voices, places SFX) | NO |
| 68 | Share a project link with timed comments, snapshots / versions | NO |
| 69 | Export MP3 / WAV, audiobook-ready (ACX / chapter files) | PART (one WAV) |

## 13. Reading and publishing
| # | Feature | Hoola |
|---|---|---|
| 70 | Audio Native: a player on her website that reads the page aloud (React, WordPress, Wix, Webflow, Ghost, Framer, Squarespace) | NO |
| 71 | ElevenReader app: reads PDFs / EPUB / web pages aloud, 1,000+ voices, a voice per character, offline, audiobook store | NO |
| 72 | Audiobook publishing (Spotify / Reader store) | NO |

## 14. Image, video, avatars (their newer side)
| # | Feature | Hoola |
|---|---|---|
| 73 | ~30 video models, ~15 image models, upscale 4K, lip-sync, talking photo, background removal | ELSE (Create / Cinema / image_edit) |
| 74 | Avatars: persistent talking-head identities, any voice incl. clone, lip-synced | ELSE (Hoola Interactive, mouth-only engine) |
| 75 | Flows (visual pipelines), Templates, Ads Engine (localise ads) | ELSE PART (Dhara flows, Interactive templates, Ads desk) |

## 15. Agents (ElevenAgents)
Hoola has this as AI Apps + the AI Telecaller + calls. Listed for completeness:
- **Channels:** voice, chat and email agents on phone, web widget, mobile, WhatsApp, SMS, Teams.
- **Models:** any LLM, a fallback chain, realtime speech-to-speech models.
- **Building:** knowledge base + RAG, workflows (visual graph), procedures.
- **Tools:** client / webhook / code / MCP tools, plus system tools: end call, language detection, transfer to an agent
  or a number, DTMF, voicemail detection.
- **Voice on a call:** dynamic variables, multi-voice, expressive mode, background audio.
- **Telephony:** SIP, Twilio, Vonage, Telnyx, Plivo, Exotel, Bandwidth, Sinch; batch calls and campaigns (calling
  windows, retries).
- **Testing and release:** tests, simulations, A/B experiments, versions + branches.
- **Watching calls:** analytics, sentiment, data collection, live monitoring, alerts.
- **Privacy:** redaction, Zero Retention, HIPAA / TCPA rules.
- **Tooling:** Architect (an AI that builds agents), CLI, SDKs (Python, JS, React, Swift, Kotlin, Unity).
- **Price:** $0.08 / min (+ LLM).

Hoola: ELSE (AI Apps, AI Telecaller with every provider, Hoola calls). Not part of Vocal.

## 16. Platform, API, trust
| # | Feature | Hoola |
|---|---|---|
| 76 | Public API + keys (scoped, rotated), SDKs (Python, JS...), OpenAPI spec, MCP server | NO for Vocal (the Developers tab shows a request shape only) |
| 77 | Webhooks for long jobs | NO |
| 78 | One credit pool across every product, price per character / minute shown, rollover, pay as you go | NO for Vocal (Hoola Credits exist but Vocal is not on them) |
| 79 | Plans by usage (Free 10k credits -> Business 6M) | ELSE (Hoola Credits plans) |
| 80 | Usage analytics per product / per key | PART (counts only) |
| 81 | AI watermark in every file + Audio Detector / Content Provenance API ("was this made by AI?") | NO |
| 82 | Workspaces: seats, groups, sharing voices / projects, SSO, SCIM, audit logs, data residency (US / EU / India), Zero Retention | NO for Vocal |
| 83 | Mobile apps | NO (the phone opens the console page) |
| 84 | Private deployment (their engines in your cloud) | n/a |

## Count
84 numbered features, plus the Agents product (section 15):

| Status | Count |
|---|---|
| HAVE | 5 (#1, 5, 9, 19, 28) |
| PART | 16 |
| NC | 2 (#21, 23) |
| ELSE | 13 (in another part of Hoola, some only partly) |
| NO | 47 |
| n/a | 1 (#84 private deployment) |

## What makes ElevenLabs ElevenLabs (the core to match first)
1. Many voices in many languages (a library with filters).
2. Expressive speech: audio tags, voice settings, takes.
3. Cloning that works: instant + professional, with verification.
4. Voice design with previews.
5. Voice changer.
6. Real voice isolation.
7. Sound effects from words.
8. Dubbing that keeps the speaker's own voice.
9. Studio for long form with a voice per character.
10. Streaming + an API.
11. A price on everything.

Engines Hoola would need for these (licence check first, per avatar_engine/registry.py):
- a multilingual expressive TTS with tags;
- a cloning model;
- a speech-to-speech model;
- a source-separation model;
- a text-to-sound model.

Gemini TTS covers only part of the first.
