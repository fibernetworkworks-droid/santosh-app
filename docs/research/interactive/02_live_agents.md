# Live interactive avatar agents — research, 23 Nov 2026

Read from each vendor's own pages where they loaded. "Not confirmed" = no official page could be read. Vendor speed
claims are vendor claims; Hoola measures its own before naming a default.

## Two findings that shape the plan

1. **"Gemini Omni" is not a live avatar.** `gemini-omni-1.2-flash` is Google's clip generator: 3-15 s clips with sound,
   about $0.07 per second at 720p. Nothing on its page about streaming, the Live API or avatars.
   https://aistudio.google.com/docs/models/gemini-omni-flash · https://aistudio.google.com/docs/pricing
2. **Gemini Live (`gemini-3.8-live`) and OpenAI Realtime give no video out.** They are voice brains: audio / image /
   text in, text / audio out. A live face comes from an avatar vendor or Hoola's own GPU.
   https://aistudio.google.com/docs/models/gemini-3.8-live

## Engines

| Engine | What it does | Brain ours? | How a browser joins | Price (published) | Custom face + consent |
|---|---|---|---|---|---|
| **HeyGen LiveAvatar** (the old Streaming API ended 31 Mar 2026) | FULL: their speech recognition + 4o-mini + ElevenLabs voice. LITE: we send audio, they render the face. | LITE: yes | server `POST /v1/sessions/token` (`X-API-KEY`, mode FULL / LITE) → WebRTC room; `is_sandbox` = free test avatar | LITE 1 credit/min, FULL 2; $19 = 150 credits → about $0.10-0.13/min LITE (help page; not confirmed on the price page) | 2-minute video or a photo; live webcam consent (Business: pre-recorded consent) |
| **Tavus CVI** | Raven-2 sees the user, Sparrow-2 turn-taking, Phoenix-4.5 face; Daily WebRTC; 42+ languages | yes: `layers.llm` = our OpenAI-compatible endpoint; voice Cartesia / ElevenLabs / Azure; Echo mode = face only | `POST https://tavusapi.com/v2/conversations` (`x-api-key`) → `conversation_url` / `@tavus/embed` | Builder $59 for 175 min, then $0.35/min; Growth $397 for 1,300 min, then $0.31/min; Business $0.26/min; 30 s minimum per call | training video with a spoken consent statement, reviewed by Tavus; photo / AI faces need none |
| **D-ID Agents** | V2 photo, V3 clips over WebRTC; V4 Expressives over LiveKit with mic input | custom OpenAI-compatible LLM | `@d-id/client-sdk` with a client key limited to her domains | not confirmed (page would not render) | not confirmed |
| **Simli** | face only from our 16 kHz PCM audio, WebRTC | always ours | server `POST /compose/token` (`x-simli-api-key`, `faceId`, 5-min token) | Hobby $10 for 1,000 min ($0.01/min); Enterprise down to $0.005/min | not confirmed |
| **Anam** | full persona or face only; 70+ languages; voice cloning | yes (`POST /v1/llms`, or `CUSTOMER_CLIENT_V1` = their AI off) | server `POST https://api.anam.ai/v1/auth/session-token` | Free 30 min; Explorer $49 for 250 min, then $0.14/min; Growth $299 for 2,000 min; Enterprise from $0.04/min; billed by the second | faces from a photo or a text prompt; consent required (how not confirmed) |
| **Beyond Presence** | Speech-to-Video face only, or video agents | yes | `POST https://api.bey.dev/v1/sessions` (`x-api-key`) into a LiveKit room | Starter €49 (280 face min); Scale €349; down to €0.03/min | not confirmed |
| **bitHuman** | face from our voice audio, in their cloud or on our own CPU / GPU | always ours | LiveKit / Pipecat plugins | about $0.02/min self-hosted, $0.04 cloud, $0.10 managed with voice | from a portrait (250-500 credits once) |
| **Akool Live Avatar** | streaming avatar through Agora | not confirmed | `POST openapi.akool.com/api/open/v4/liveAvatar/session/create` | 1-1.2 credits per 10 s at 1080p; USD per credit not confirmed | not confirmed |
| **Synthesia Interactive** | LiveKit plugin; our LLM, voice and tools | yes | LiveKit | Enterprise only; not confirmed | — |

Voice brains (no face):
- **Gemini Live** `gemini-3.8-live`:
  - about $0.005/min of audio in and $0.018/min of audio out;
  - about 70 languages, incl. hi, bn, mr, ta, te;
  - ephemeral tokens for the browser;
  - about 15 minutes of audio-only per session.
- **OpenAI Realtime:** `gpt-realtime-2.1` and mini; `gpt-live-1` at $0.05/min active.
- **ElevenLabs Agents:** about $0.08/min plus the LLM at cost. Its own avatar path is LiveAvatar LITE.

Frameworks that keep the brain ours:
- **LiveKit Agents** avatar plugins: Anam, Beyond Presence, bitHuman, D-ID, LiveAvatar, Runway, Simli, Synthesia,
  Tavus and others.
- **Pipecat:** Anam, bitHuman, HeyGen LiveAvatar, Simli, Tavus.

Self-hosted:
- **MuseTalk:** MIT code + free weights. Hoola's GPU lab measured 37 fps on an L40S.
- **LiveTalking:** Apache-2.0.
- **Ditto:** Apache-2.0.
- **Wav2Lip:** its open weights are non-commercial, so never.

## Shortlist

- **Brain ours, face rented** (fits Hoola: her chosen LLM + tools + Vocal voice):
  - Simli, bitHuman, Beyond Presence, LiveAvatar LITE, Anam (client mode), Tavus Echo, Synthesia;
  - or any LiveKit plugin.
- **Best quality (vendor claims):** Tavus Phoenix-4.5 > HeyGen LiveAvatar > Anam.
- **Best value:** Simli $0.005-0.01 · bitHuman $0.02-0.04 · Beyond Presence €0.03 at scale · Anam Enterprise $0.04 ·
  LiveAvatar LITE about $0.10 · Tavus $0.26-0.35.
- **Indian languages:** keep the listening and the voice ours (Gemini Live or Vocal / ElevenLabs) and use a face-only
  renderer.

## Not available by API

- A live face from Gemini Live, Gemini Omni or OpenAI Realtime.
- HeyGen's retired Interactive Avatar streaming API.
- Synthesia interactive: Enterprise only.
- Not confirmed: D-ID and Akool per-minute prices, and the consent rules of Simli, Beyond Presence and Akool.
- Commercial / embedding terms of most vendors: read each one's terms before signing.
