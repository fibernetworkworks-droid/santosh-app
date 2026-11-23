# Talking-avatar video makers with an API — research, 23 Nov 2026

Read from each vendor's own pages where they loaded. Several price tables render with JavaScript and could not be read
(HeyGen, D-ID API, Kling official); those figures come from secondary sources, which are named. Check before budgeting.

| Engine | What it makes | API (create → poll / webhook) | Price (source) | Her own face |
|---|---|---|---|---|
| **HeyGen** Avatar 6 / 6-turbo (also IV, V), photo avatars, translation with lip-sync | studio avatars, twins, photos; 1080p / 2k | `https://api.heygen.com`, `x-api-key`; `POST /v3/videos` (engine `heygen-avatar-6`) → `GET /v3/videos/{id}`; own image / video + audio `POST /v3/models/avatars`; `POST /v3/video-translations` (175+ languages, webhook) | pay-as-you-go wallet, no free API credits since Feb 2026; secondary: Avatar III photo $0.99/min, Avatar IV photo $2.31/min (+$1.32 per photo avatar); Avatar 6 not confirmed | twin: webcam consent statement via API; photo avatars: the customer's responsibility. Resale on standard API terms not confirmed; the enterprise agreement allows end-user integrations |
| **Synthesia** | studio + personal avatars, dubbing; 140+ languages | `POST https://api.synthesia.io/v2/videos`; test mode free; 3-10 min a video | plans $0-89/mo; API per-minute price not published | not confirmed |
| **D-ID** | `/talks` photo → head; `/clips` V3 Pro medium shot with body + hands | `POST https://api.d-id.com/clips` (webhook), `Authorization: Basic` | secondary about $0.59-0.78/min; billed in 15-second units | not confirmed |
| **Hedra** Character-3 | image + audio → expressive character, up to 10 min, 7 shapes | not confirmed | $1.50/min at 540p, $3.00 at 720p, $3.75 at 1080p (model page) | not confirmed |
| **Captions Mirage** | talking-head videos from scripts / actors | — | $0.15/s ≈ $9/min | — |
| **Akool** | talking photo, talking avatar, lip-sync, translation | — | credits only; secondary ≈ $3.5-4/min | — |
| **Tavus** video | a filmed replica + script / audio | `POST https://tavusapi.com/v2/videos` (`x-api-key`, callback_url) | $0.80-1.00/min overage, 30 s minimum | spoken consent, required |
| **Runway** avatar videos (`gwm1_avatars`) | an avatar from one reference image speaks | `POST https://api.dev.runwayml.com/v1/avatar_videos` → `GET /v1/tasks/{id}`; Bearer + `X-Runway-Version` | 1 credit per 3 s = **$0.20/min** (+ typed script 1 credit / 50 chars) | not confirmed; max length / resolution not confirmed |
| **Kling AI Avatar v2** | image + audio | kie.ai `POST /api/v1/jobs/createTask` (callBackUrl); fal | kie.ai $0.0505/s at 720p (≈ $3/min), $0.101/s at 1080p, up to 300 s; fal Pro $0.115/s | not confirmed |
| **ByteDance OmniHuman** 1.5 / 2.0 | photo + audio → talking, gesturing, full body | BytePlus (sales); fal `POST https://fal.run/fal-ai/bytedance/omnihuman/v1.5` | BytePlus $0.07/s body, $0.12/s lip-sync, 720p, 30-300 s; fal $0.14-0.16/s (audio < 30 s at 1080p) | not confirmed |
| **Google Gemini Omni** `gemini-omni-1.2-flash` | 3-15 s clips with sound (to 30 s); NO audio input, no recognisable people | `v1beta/interactions`, `x-goog-api-key` | ≈ $0.07/s at 720p | the Avatar feature is consumer-app only, no API |
| **OpenAI Sora 2** | — | shut down: the Videos API was removed 24 Sep 2026 | — | — |
| **Alibaba Wan 2.2-S2V** | photo + speech → video | DashScope (Beijing region) | $0.0717/s at 480p; Replicate ≈ $0.02/s; Apache-2.0 weights | — |
| **Hosted open models** | InfiniteTalk (kie.ai $0.015-0.06/s), MuseTalk (MIT), LatentSync (Apache-2.0), Hallo3 (MIT); Wav2Lip = non-commercial, never | — | — | — |

## Shortlist

- **Quality:**
  - HeyGen Avatar 6 for filmed twins, with consent built into its API;
  - OmniHuman for a photo becoming a gesturing body;
  - Synthesia for corporate presenters.
- **Value:**
  - Runway avatar videos at about $0.20/min (limits not confirmed: test first);
  - Wan S2V on Replicate at about $1.20/min;
  - Hedra 540p at $1.50/min;
  - Kling via kie.ai at about $3/min.
- **Languages:**
  - HeyGen translation 175+, Synthesia 140+, Tavus 42+.
  - For Indian languages, make the speech with Hoola's own voice (Vocal) and give the audio to an audio-driven face model
    (OmniHuman, Kling, Hedra, Runway, Wan). No published Indian-language lip-sync scores were found.
- **Self-host:** Wan 2.2-S2V (Apache-2.0), LatentSync (Apache-2.0), MuseTalk (MIT), Hallo3 (MIT).
- **Not available:**
  - Sora 2: shut down.
  - Gemini Omni: avatars in the consumer app only, no audio input.
  - Runway Act-Two: needs a driving video.
  - Synthesia / D-ID: API per-minute prices not published.
- **India availability:** not confirmed for any vendor.
