# Hoola Interactive rebuild — the plan (23 Nov 2026)

Owner: "NOW OUR PLAN FOR REBUILDING IT PROPERLY ::: 1) REDESIGN WORK AS WE DONE FOR VOCAL 2) WIRING THE EXISTING BACKEND TO
EVERY TOOL PERFECTLY 3) BEST INTERACTIVE GENEARTOR AND IT API ATTACHMENT HERE LETS USER CHOOSE THE PERFECT INTERACTIVE
LLM AGENT FROM HEYGEN TO GEMINI OMNI ETC".

What it stands on: the audit of 23 Nov 2026 (every file of `server/app/interactive/`, `static/console/interactive.js`, the
`#hiRoot` block of `v2.css`, the tests, `docs/HOOLA_INTERACTIVE_CONSOLE_PLAN.md`, screenshots of all twelve pages).

## 0. Where it is today (the audit, short)

- **The flow:** one line in → a draft of 3-7 scenes (one spoken line + one look each) → edit → Generate → an MP4 drawn by
  HyperFrames on the server.
- **Real:** the draft writer, scene editor, real make steps with Stop, brand, glossary, templates, batch, many names,
  translate + proofread, trash, live "brains", usage.
- **Rules held by code:**
  - a number she did not write is blanked;
  - a photo avatar needs her consent tick;
  - a translated line with a changed number is flagged.
- **The weak links:**
  1. **Voice comes only from the GPU voice lab** (`interactive/lab.py`, Chatterbox). Vocal's Gemini / ElevenLabs voices
     (140 languages, her cloned and designed voices) are not used. Without the lab every video is captions only.
  2. **The avatar does not talk.** It is a still photo beside the words. Cinema already makes talking photos through one
     key (Kling AI Avatar / Pro, OmniHuman 1.5, InfiniteTalk, Wan S2V, plus lip sync), but Interactive does not call it.
  3. **About 15 controls say "Not connected yet".** Several are already built elsewhere in Hoola (podcast script, speech
     clean-up, voice clone / design, dubbing, lip sync).
  4. **The look predates the Create / Vocal frame:** violet gradient hero, violet buttons, no chat.
  5. **The phone opens the console page in a web view**, not a native screen.
  6. **Smaller gaps:**
     - the Studio preview is a mock layout;
     - 10 languages only;
     - no credits meter;
     - no AI mark in the video file;
     - styles live in the shared `v2.css`.

## 1. Redesign (the way Vocal was done)

Same frame as Create Studio / Hoola Vocal:
- the real Hoola mark and a sidebar in groups;
- Literata page titles over a Schibsted body, ink pill main buttons and violet only for what is chosen;
- the docked Music-style chat bar, light + dark, and a phone drawer.

Its own stylesheet (`interactive2.css`, scoped `#hiRoot`), out of `v2.css`.

Sidebar groups:
- **Make:**
  - Interactive chat (the home): one line → the plan card → the video;
  - Studio (the scene editor);
  - Templates;
  - Apps.
- **Faces and voices:**
  - Avatars (photo, talking photo, AI-made face, twin);
  - Voices: Vocal's whole library, her own voices, a picker shared with Vocal.
- **Live:**
  - Live agents: the interactive agent builder, the engine chosen per agent;
  - Try it.
- **Assets:**
  - Projects (videos, drafts, translations, trash);
  - Brand (kit + glossary);
  - Engines (part 3);
  - Developers (API keys + webhooks);
  - Settings.

Boards for the design canvas (first, for her eyes, before any build):
1. Interactive chat home: the box, a few ideas, recent videos, the engine chips under the box.
2. The plan card in the chat: scenes, face, voice, engine, price → "Make it" (her tap).
3. Studio: the script left; a real preview of the selected scene (the HyperFrames still of that scene, not a mock); tools
   right (Look / Face / Voice / Captions / Music / Brand); the scene strip.
4. Making: real steps (voice → talking face → drawing → saving), each with its engine and time, Stop.
5. The finished video: player, Download, share link, Translate, Make a version, AI mark said.
6. Avatars: her faces as cards (photo / talking / AI-made), consent shown, which engines can drive each face.
7. Engines: every generator and live agent engine as a card, with what it does, quality, price per minute, languages,
   connected or not, and her default per job (part 3).
8. Live agent builder: brain (facts + LLM), face engine, voice, language, Try it, embed code.
9. Phone: chat home + the video player + the live agent try.

## 2. Wiring the existing backend to every tool

Every control is either wired to a real Hoola function below or removed — no "Not connected yet" left on a page that
Hoola can already do somewhere else.

| Interactive tool | Wired to (already in Hoola) | Notes |
|---|---|---|
| Speech in a video | `vocal.service._say` (Gemini voice, ElevenLabs premium, her cloned / designed voices, GPU lab) | replaces the lab-only voice in `frames.do_avatar_film`; her Vocal dictionary applies; 140 languages |
| Voice picker | Vocal's library + her voices (`vocal.service.library`, `_mine`) | the same picker as Vocal |
| Talking photo avatar | Cinema `talk` (kie.ai: Kling AI Avatar / Pro, OmniHuman 1.5, InfiniteTalk, Wan S2V) | her photo + the spoken track → a talking clip placed in the scene; consent kept |
| Lip sync onto her own video | Cinema `lipsync` (Volcengine) | "Twin from a video" in the meantime |
| Translate with her voice / lips | Vocal dubbing (`dub_start`, matched or own voices) + Cinema lip sync | outside videos too |
| Podcast app | Vocal `podcast` (script from her document) + `dialogue` | two hosts, each a face |
| Speech clean-up app | Vocal `cleanup` | |
| Clone / design my voice | Vocal Your voice (`voice_clone`, `design_preview`) | consent statement in 30 languages |
| AI-made face | Create pictures (`create.service` image) | marked "AI-made person", never a real person |
| Music under the video | Vocal music bed / Create songs (Lyria) | her choice, volume ducked under speech |
| Clips from a long recording | `vidkit` (cut) + Kaan transcript for the moments | |
| Link to video / slides to video | `scrape_page` / the file reader (PDF pages) → scenes | facts only from her source |
| Series on a schedule | routines | each run = a draft she approves unless she says otherwise |
| Live agent brain | Hoola's own brain (the chat model + her facts + tools) | part 3 picks the face / voice engine |
| Credits meter | `credits` / `usage.record` per engine | the price card before every paid make |
| AI mark | Vocal `ai_mark` (audio) + MP4 metadata via ffmpeg | said on every video |
| API keys + webhooks | the Vocal apps pattern (`vocal/apps.py`) | one key, signed webhooks |
| Interactive chat | the Vocal chat pattern (`vocalchat.py`, kind `interactive`) | the brain plans; making = her tap |

## 3. Generators and live agents she chooses (from HeyGen to Gemini)

Research: `docs/research/interactive/01_video_makers.md` and `02_live_agents.md` (23 Nov 2026). Two facts first:

- **"Gemini Omni" exists, but it is a clip generator**: `gemini-omni-1.2-flash`, 3-15 s clips with sound, about $0.07/s.
  It takes no audio input, refuses recognisable people, and its Avatar feature is consumer-app only. So it is offered
  for **B-roll scenes** (a shot of the shop, the product), never for her talking face.
- **No voice brain gives a live face.** Gemini Live, OpenAI Realtime and ElevenLabs Agents are voice only. A live face
  comes from a face engine (rented, or Hoola's own GPU).

Hoola's design follows from that. **The brain and the voice stay Hoola's; only the face is chosen.**
- **Brain:** her tier's chat model and tools, or the model she picks.
- **Voice:** Vocal, 140 languages and her own voices.
- **Face:** each engine is one adapter behind one interface, so she picks per video or per agent and can switch any time.
  Indian languages work on every face engine because the face only follows the audio.

### 3.1 Video makers (a finished MP4)

| Engine | Why it is offered | Cost (published) | Key on the server |
|---|---|---|---|
| **Hoola standard** (HyperFrames + her photo + Vocal voice) | free, any language, numbers checked by code | free (voice credits only) | none |
| **Kling AI Avatar** (via kie.ai, already in Cinema) | her photo talks, steady lips | ≈ $3/min at 720p | `KIE_API_KEY` (already there) |
| **OmniHuman 1.5** (kie.ai today; BytePlus / fal later) | a photo becomes a gesturing upper body | ≈ $0.07-0.16/s | `KIE_API_KEY` / `FAL_KEY` |
| **InfiniteTalk, Wan S2V** (kie.ai) | long talking videos cheaply | $0.015-0.13/s | `KIE_API_KEY` |
| **Runway avatar videos** | cheapest published ($0.20/min), one reference image | ≈ $0.20/min | `RUNWAY_API_KEY` |
| **HeyGen Avatar 6** | top quality, filmed twins with consent in the API, translation in 175+ languages | wallet; ≈ $1-7/min (not confirmed) | `HEYGEN_API_KEY` |
| **Hedra Character-3** | expressive characters up to 10 min | $1.50-3.75/min | `HEDRA_API_KEY` |
| **Synthesia, D-ID, Tavus video** | corporate presenters, filmed replicas | prices not published / $0.8-1/min | each its own key |
| **Gemini Omni** (B-roll only) | a 4-8 s scene without a person | ≈ $0.07/s | `GEMINI_API_KEY` (already there) |

### 3.2 Live agents (a face that listens and talks)

| Face engine | Why | Cost (published) |
|---|---|---|
| **Simli** | face only, cheapest | $0.005-0.01/min |
| **bitHuman** | face only, can run on Hoola's own machine | $0.02-0.04/min |
| **Anam** | 70+ languages, faces from a photo or words, about 1.2 s replies (vendor) | $0.04-0.16/min |
| **HeyGen LiveAvatar (LITE)** | HeyGen faces, audio from Hoola | ≈ $0.10-0.13/min |
| **Beyond Presence** | face only, LiveKit | €0.03-0.175/min |
| **Tavus CVI** | best perception + turn-taking (vendor), our LLM through `layers.llm` | $0.26-0.35/min |
| **D-ID Agents** | domain-locked client key, our LLM | not confirmed |
| **Hoola GPU lab** (MuseTalk) | her own GPU, no per-minute vendor | GPU time (37 fps measured) |

**How a live agent runs:**
- Her **brain** is a "brain" from the Live page: her facts + links + Hoola's model and tools.
- The **ears + voice** are Gemini Live (`gemini-3.8-live`, ≈ $0.02/min, Hindi / Bengali / Marathi / Tamil / Telugu) or
  Vocal / ElevenLabs.
- The **face** is the engine she picked, joined over LiveKit (one pipeline, every face a plugin) or the vendor's own
  room.
- **The key stays on the server.** A visitor's browser gets a short-lived token only, the way `/api/interactive/ticket`
  already works.

### 3.3 The Engines page

Each engine is a card: what it does, a sample, languages, cost per minute from its published price, which key it needs,
and **connected / not connected** (read from the server, never assumed). She sets a default per job (video / live / B-roll).

Before every paid make, the price card shows engine × minutes → credits, and nothing runs without her tap. A vendor that
refuses (out of credit, key wrong) is said in its own words.

## 4. Safety (held by code, every engine)

- **A face needs consent.**
  - Her own face: her yes plus a spoken consent line (Vocal's 30-language statements).
  - Another person: that person's recorded yes.
  - AI-made: marked as not a real person.
  - Never a public figure or anyone under 18.
- **Vendor consent flows are used where they exist:** HeyGen's webcam consent, Tavus's consent statement.
- **Numbers only from her words,** as today, for every engine.
- **AI mark on every file:** said on the page and in the MP4's metadata.
- **No face swap.** No outside video of another person is lip-synced without that person's recorded consent.
- **Keys** live in the VPS `.env` only; a browser only ever gets a short-lived token.

## 5. Phases (each ends in something she opens and judges)

| Phase | What ships | Her check |
|---|---|---|
| **R0 Design canvas** | the boards of part 1, for her eyes | she says GO BUILD |
| **R1 Look + chat** | the new frame, Interactive chat (plan card → her tap), all pages redrawn, `interactive2.css`, phone native screens | every page opens in the new look, light + dark, desktop + phone |
| **R2 Wiring** | Vocal voices in every video, Cinema talking photo as a face, the "Not connected" controls wired to Vocal / Cinema / Create / vidkit / routines (part 2), credits + AI mark | a 30-second Hindi video with her photo talking in a Vocal voice |
| **R3 Engines** | the engine interface + adapters (Kling / OmniHuman / InfiniteTalk / Wan via kie.ai first, then Runway, HeyGen, Hedra, Gemini Omni B-roll), the Engines page, price cards, a live check like `vocal_check` | the same script made on two engines side by side |
| **R4 Live agents** | brain + Gemini Live ears / voice + a face engine (Simli or Anam first, then LiveAvatar LITE, Tavus, bitHuman, the GPU lab), Try it, embed code with short tokens | she talks to her shop agent on a phone in Hindi |
| **R5 API** | keys + webhooks (the Vocal apps pattern), `/v1/interactive/videos` | a second app makes a video with only a key |

## 6. What only she decides

1. **Which keys to add**, in this order of value:
   - `KIE_API_KEY` is already there (Kling / OmniHuman / InfiniteTalk / Wan);
   - then `RUNWAY_API_KEY` (cheapest);
   - `HEYGEN_API_KEY` (top quality);
   - one live face (`SIMLI_API_KEY` or `ANAM_API_KEY`).
   Each vendor's own terms must be read before selling (resale rules are unconfirmed for most).
2. **The default engine per job** (Hoola standard is free; the rest cost per minute).
3. **The price in credits per minute** per engine (the vendor's cost is shown; the margin is hers).
4. **Whether the GPU lab stays** (own faces, no vendor) or is switched off.
