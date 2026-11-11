# HOOLA VOCAL - plan and state (owner, 11 Nov 2026: "HOOLA VOCAL ... clone VoiceStudio and make same 11labs for hoola end to end, all 100% features")

## 1. The licence finding (read this first)
- `github.com/debpalash/VoiceStudio` was cloned and read at commit c85a866. It is **AGPL-3.0-only** (LICENSE, LICENSE-NOTICE.md).
  Hoola is a hosted product: putting AGPL code in Hoola's server would oblige Hoola to offer its OWN source to every user.
  Its maintainer sells a separate commercial licence for closed products.
- Its default model (`k2-fsa/OmniVoice`) has code under Apache-2.0 but **weights under CC-BY-NC** (non-commercial), and its audio
  tokenizer carries further Higgs Audio / Llama terms. Those weights cannot be sold as part of Hoola.
- DECISION TAKEN: **no VoiceStudio code or weights in Hoola** (the Firecrawl / crawl4ai precedent). Its feature map and ElevenLabs'
  public product were used as the list of what to build; everything runs on engines Hoola already owns. A test asserts the module
  names none of it. If she wants its code itself, the route is its paid commercial licence - her decision, not built on.

## 2. What VoiceStudio is (feature map only)
Voice cloning, voice design (describe a voice), video dubbing (translate, multi-speaker, export), dictation widget, transcription,
vocal isolation, speaker diarization, stories / audiobooks (long-form jobs), batch queue, sound effects, voice conversion,
pronunciation + glossary, personas / profiles, gallery / marketplace, watermark, local API (OpenAI-compatible) + MCP, telephony
(Twilio), 20+ speech engines and 10 transcription engines behind a model manager.

## 3. ElevenLabs feature by feature -> Hoola Vocal today
| ElevenLabs | Hoola Vocal v0.800 | Stands on |
|---|---|---|
| Text to speech (voices, languages, settings) | LIVE - 22 voices, 11 Indian languages, style, speed, 40,000 characters | create.service.voice |
| Voice library | LIVE - Hoola's ready voices, hear + use | avatar voice list |
| Instant voice clone | BUILT, needs the GPU lab - consent required, recording deleted with the voice | interactive.lab (Chatterbox, MIT) |
| Voice design (from a description) | BUILT, needs the GPU lab - refuses a named person | interactive.lab (Indic Parler, Apache-2.0) |
| Text to dialogue (multi-speaker) | LIVE - each speaker her chosen voice, one file | vocal.service.dialogue |
| Studio (long-form, chapters, audiobooks) | LIVE - chapters read separately, export as one file | vocal.service.project_* |
| Pronunciation dictionaries | LIVE - applied by code, counted | vocal.service.apply_rules |
| Sound effects | PARTLY - code-made presets only; from a description = NOT connected | gamedesk.sfx |
| Voice isolator | PARTLY - ffmpeg noise + voice clean-up; lifting a voice out of music = NOT connected | audedit.ops |
| Voice changer (speech to speech) | NOT connected - no model; the page says what works instead | - |
| Speech to text (Scribe) | Lives in Hoola Flow (linked) | kaan |
| Music | LIVE when the music engine is configured | create.service.song |
| Dubbing | Lives in Create (linked) | create.service.dub |
| Agents (conversational AI, phone) | Lives in AI Apps + calls (linked) | aiapps, voice |
| History, downloads | LIVE - newest 200 kept | vocal.service |
| Usage | LIVE as counts; no rupee meter | vocal.service.usage |
| Professional voice clone | NOT built (needs training + a spoken-consent check) | - |
| Voice remixing, community library, payouts | NOT built | - |
| Audio Native (website player), ElevenReader | NOT built | - |
| API keys, webhooks, SDKs | NOT open | - |
| AI watermark / classifier | NOT built | - |

## 4. What is left, in order
- V1 RUN IT LIVE: deploy, open the page, make speech in a Hoola voice; set the GPU lab address + key so clone and design can speak.
  Nothing on this page has been heard from a real engine yet.
- V2 the three missing models, each needing a licence check first (the registry in `avatar_engine/registry.py` is the gate):
  speech-to-speech (voice changer), source separation (voice out of music), text-to-sound (effects from a description).
- V3 real tables instead of one JSON per user; long jobs that survive a restart (Studio chapters as background jobs with progress).
- V4 the rupee meter (engine cost per result) + a monthly ceiling that refuses before the call, like mapsbill.
- V5 AI mark in every file + a "was this made by Hoola" check; consent recorded as a spoken line for clones.
- V6 public API + keys + webhooks (the request shape is on the Developers tab), then the website player.
- V7 professional clone, voice remix, shared library - only on her word; each is a product decision.

## 5. Rules the code keeps
A recorded voice needs her yes (a real True, nothing else); no imitation of a named person; her dictionary is applied by code and
counted; another tenant can never fetch a sound; what is not connected is disabled and named, never faked.
