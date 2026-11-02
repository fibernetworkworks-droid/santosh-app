# Hoola Interactive — our own real-time AI human (plan)

Owner's ask (2 Nov 2026): "LET WE BUILD OUR OWN HEYGEN — HOOLA INTERACTIVE AI". First use: the Personal Tutor —
a real-looking teacher who gives pre-made chapter lessons and talks live with the student when he raises his hand,
the same face in both, natural classroom background, the student's own language.

Owner's decision (2 Nov 2026, later): "AS WE ARE BUILDING WORLD CLASS PRODUCT :: WE WILL BUILD OUR OWN HEYGEN FOR WORLD AS
GPU ON VPS". So the scope is the WHOLE product for every user worldwide (section 7), on our own rented GPU server(s);
the Personal Tutor is its first customer, not its limit.

Status: PLAN. No code written yet. Nothing here has run on a GPU yet — every speed figure is the model authors' or a
framework's own published number, to be re-measured on our machine in Phase 1.

## 1. What "our own HeyGen" actually is

Three parts. Only the middle one is new for Hoola.

```
student's voice ─► [1] VOICE BRAIN (already ours) ─► reply audio ─► [2] FACE ENGINE (new, GPU) ─► video frames ─► [3] STREAM (new) ─► phone / console
                   speech-in, tutor brain, Indian-language voice        lip-synced talking face            WebRTC, 25 fps
```

1. **Voice brain — already built.** The call pipeline (Gemini Live / the OpenAI real-voice engine, v0.264-v0.289) and the
   Guru tutor (v0.387: hint ladder, code-checked answers, exam mode, guardian consent). Languages come from here, so
   Hindi / Marathi / Tamil never depend on the face engine.
2. **Face engine — new.** Takes the reply audio, returns frames of the teacher's face speaking those exact sounds. Runs
   on a GPU. Two modes on the same face: *live* (frames as audio streams in) and *render* (a whole lesson to MP4).
3. **Stream — new.** Sends the frames to the phone with low delay (WebRTC), keeps an idle loop (breathing, blinking)
   while she listens, stops instantly when the student interrupts.

## 2. The model choice — licence first

A talking-face model is useless to us if its licence or its bundled sub-models forbid commercial use. Checked against
each repository's own LICENSE / README and the weight's model card on 2 Nov 2026:

| Model | Code | Weights | Catch | Use? |
|---|---|---|---|---|
| **MuseTalk 1.5** (Tencent Music) | MIT | MIT (HF model card) | VAE `sd-vae-ft-mse` = MIT; its face pre-processing helpers must each be checked (Phase 0) | **YES — the live engine.** Authors: real-time, 30 fps+ on a V100 |
| LatentSync (ByteDance) | Apache-2.0 | — | aligns faces with **InsightFace**, whose models are "non-commercial research purposes only" | Only with the face detector swapped |
| Ditto (Ant Group) | Apache-2.0 | no licence tag on the weights | ships `insightface_det` models (same non-commercial problem); A100 in the README | Not before the detector is swapped and the weights' licence is confirmed |
| LivePortrait (Kuaishou) | MIT | — | uses InsightFace models | Same as above |
| Wav2Lip | — | research / personal only (trained on LRS2) | — | **NO** |
| Duix (HeyGem / Duix-Mobile) | DUIX community licence | — | free below 100,000 users / USD 10 M revenue, then a signed licence | Avoid — a ceiling on our own growth |
| NVIDIA Audio2Face-3D | MIT / Apache | NVIDIA Open Model Licence | drives a 3D face rig, not a photo-real person | Not for this look |
| LiveTalking (framework) | Apache-2.0 | — | a streaming wrapper around the models above; its HD wav2lip is sold separately | Reuse its ideas (WebRTC, interrupt), not its bundled weights |

**Decision: MuseTalk 1.5 for both live and lessons**, with every pre-processing model replaced by one whose licence
allows commercial use where needed (face detection → a commercially licensed detector; to be fixed in Phase 0).
Published speed for MuseTalk in a real-time stream (LiveTalking's table): RTX 3080 Ti 42 fps, RTX 3090 45 fps, RTX 4090
72 fps. 25 fps is real time, so one RTX 4090 should carry about **two live teachers at once** — to be measured.

## 3. How a face is made (and the rule that comes with it)

MuseTalk does not invent a face: it re-animates the mouth of an existing **reference video** (10-60 s of the person
looking at the camera, natural background, idle movement). So the teacher face is one short video, prepared once
(landmarks + latents cached), then reused by every lesson and every live session — that is how "the same face in
both" comes free.

Where the reference video comes from — her choice:
- **A real presenter** (an actor / a teacher) who signs a written consent and licence for this exact use. Most
  natural. Each face = one signed record in Hoola; no record, no face.
- **An AI-made person** (Create Studio's video models make a 30 s clip of a person who does not exist). No consent
  problem; realism depends on the model.

Hard rules, in code: no face of anyone without a consent record; never a face uploaded by a user of someone else;
never a child's face; every frame carries a small "AI teacher" label; a student's camera is never needed or stored.

## 4. Cost — own GPU vs renting a provider

GPU rental, published September 2026 (vary weekly): RTX 4090 about $0.34-0.74 an hour (RunPod community / secure),
L4 about $0.39-0.49, L40S about $0.48-0.86. India-hosted GPU prices (E2E Networks, Yotta) were not found — to be quoted,
and they matter: children's data under DPDP is better kept in India.

Rough per-minute cost of a live teacher on our own RTX 4090 at about $0.50 an hour, two streams per GPU:
**about $0.004 a minute while busy** — against about $0.08-0.095 for HeyGen LiveAvatar in its cheapest mode and $0.26+ for
Tavus. The catch is the idle GPU: one GPU kept on all month costs about **$360**, the same as about 4,500 rented
LiveAvatar minutes. So our own engine wins once the students' live minutes pass roughly 4,500 a month per GPU, and
pre-made lessons are almost free after rendering (render once, play for everyone).

Our own engine also means: no per-minute bill from someone else, the face is ours, and students' audio never leaves
our servers.

## 5. Phases

| Phase | What ships | Proof it works |
|---|---|---|
| **0 Decisions + licence sweep** | GPU provider + monthly cap (her word); face source; every MuseTalk dependency's licence written down, non-commercial ones replaced | a licence table with no "unknown" row |
| **1 Face lab** | one GPU box; upload reference video → prepared face; render a 30 s clip from a Hindi line | her eyes on the clip; measured fps on our GPU |
| **2 Lesson renderer** | lesson script → our TTS → MuseTalk → MP4 + board overlay + captions, cached per chapter / language | 1 full chapter (Class 9 Motion) in Hindi + English |
| **3 Live engine** | audio stream in → 25 fps frames out → WebRTC; idle loop while listening; interrupt cuts her off within 300 ms | speech-end → first moving lip under 1.5 s (p95) |
| **4 Into the tutor** | Guru's live voice drives the face; "Raise hand" opens the live teacher inside a lesson | the conversation prototype (7c) working for real |
| **5 Phone + console player** | player screens; fallback = voice + still photo when no GPU is free | works on a mid-range Android on 4G |
| **6 Scale + money** | 2 streams per GPU, queue, minute meter per student, daily cap, GPU up only when needed | cost per student-hour on a dashboard |
| **7 Quality card** | lip-sync score, latency p95, fps, dropped frames, per language | a card run before every version, like the other cards |

Hoola's sandbox has no GPU: code for Phases 1-6 can be written here, but it is only proven on the GPU box.

## 6. What she decides before Phase 0 starts

1. **GPU**: decided - our own GPU server (section 8). Still open: which provider (India-hosted quotes first) and a monthly cap.
2. **The face**: a consenting real presenter, or an AI-made person.
3. **Order**: lessons first (cheaper, proves the look) or live first.


## 7. The world product — HeyGen's list, mapped to ours

| HeyGen feature | Hoola Interactive module | Built on | Phase |
|---|---|---|---|
| Stock avatars | **Faces library**: a starting set of consented / AI-made presenters, many ages, regions, looks | face engine | 2 |
| Digital Twin | **My Twin**: a user records 30-60 s of themselves + a spoken consent line; becomes their avatar | face engine + consent check | 8 |
| Photo avatar (Avatar IV) | **Photo to talking video** | needs a photo-to-video model; licence sweep first | 11 |
| Text to talking video | **Hoola Studio Video**: script / prompt -> presenter video | lesson renderer (Phase 2) + Create Studio Director | 2, 9 |
| LiveAvatar | **Hoola Live**: real-time talking avatar for tutors, support desks, sales, kiosks | live engine (Phase 3) | 3-4 |
| Voice cloning | **My Voice**: a user's own voice from a consented recording | open voice-clone model, licence sweep first | 10 |
| Video Translate | **Lip-sync dubbing**: re-dub any video into Indian + world languages, lips matched | face engine + existing Dubbing | 9 |
| AI Studio, Templates, Brand Kit, Video Agent | already in Create Studio (Video Editor, Director, Brand kit, templates) — gains the avatar track | Create Studio | 9 |
| Video Podcast | **Two-host video podcast** from a script / PDF / link | Notebook podcast + two faces | 12 |
| Personalised video at scale | **One video, many names** (each viewer's name / details), opted-in contacts only | renderer + Phase 6 queue | 12 |
| API, MCP, integrations | **Hoola Interactive API** (keys, per-minute metering, webhooks) + MCP server | Phase 6 meter | 13 |

## 8. GPU on our own VPS — what to rent

- **Start: one GPU server**, Ubuntu, NVIDIA driver + CUDA, Docker, a public IP for WebRTC, 100+ GB disk.
  RTX 4090 (24 GB, cheapest per frame, ~2 live streams) or L40S (48 GB, room for lesson rendering + live on one box).
- **Where**: an India-hosted GPU provider first (students' and Indian users' data stays in India under DPDP); a second
  region (EU / US) when foreign users arrive. Quotes needed — Indian GPU prices were not found published.
- **How it joins Hoola**: the main VPS stays the brain (accounts, voice, tutor, billing). The GPU server runs ONLY the face
  engine behind a private, key-protected API; it stores no user data beyond the job it is rendering, and wipes it after.
- **Scale**: more GPU servers behind one queue; a server is started only when the queue needs it (Phase 6).
- Deploy like the rest of Hoola: a setup script + a vps-ops job; keys only in that server's `.env`, never in chat.

## 9. Trust and safety — required for a public avatar product

A public "make anyone talk" tool is a deepfake tool unless these hold, in code, from the first public release:
- **Consent you can prove**: a Twin is made only from a person who records themselves on the spot saying a random
  sentence shown on screen (liveness), matched to the face in the upload. No upload of someone else's video or photo.
- **Refused faces**: children; public figures / politicians / celebrities (a face-match block list); anyone without
  the consent record.
- **Marked as AI**: a visible "AI" mark on every frame plus C2PA content credentials in every file we export.
- **Content rules**: no political persuasion, no impersonating a real organisation, no financial / medical claims in a
  real person's voice; a report button and a takedown queue.
- **Indian law**: the IT Rules on synthetically generated content (labelling) and DPDP consent apply; reviewed with a
  lawyer before the public launch.


## 10. Hoola Voice — our own "ElevenLabs" on the same GPU (her ask: "IS ON GPU WE CAN CLONE A 11LABS")

Yes: realistic text-to-speech + voice cloning runs on the same GPU server as the face engine. Model licences checked on
the Hugging Face model cards / repo LICENSE files on 2 Nov 2026:

| Model | Licence | Indian languages | Cloning | Use? |
|---|---|---|---|---|
| **Chatterbox Multilingual V3** (Resemble AI, 0.5B) | MIT | Hindi (+ a Hindi single-language pack), 20+ others | yes, zero-shot from a short clip | **YES — main cloning voice.** Every output carries Resemble's Perth watermark (survives MP3) = built-in deepfake marking |
| **IndicF5** (AI4Bharat) | MIT (weights) | 11: hi, mr, bn, gu, kn, ml, or, pa, ta, te, as | yes, from a reference clip | **YES — the Indian-language voice.** Gated download (accept terms); check its training-data terms in Phase 0 |
| **Indic Parler-TTS** (AI4Bharat) | Apache-2.0 | 21 Indian languages | no — voice described in words ("calm female teacher") | **YES — stock voices, no cloning needed** |
| CosyVoice 2 / 3 (Alibaba) | Apache-2.0 | not Indian-first | yes | Maybe, if Hindi quality passes |
| Kokoro-82M | Apache-2.0 | limited | no | Small and fast fallback |
| F5-TTS (original) | CC-BY-NC-4.0 | — | yes | **NO** (non-commercial) |
| XTTS-v2 (Coqui) | Coqui Public Model Licence | Hindi | yes | **NO** (non-commercial) |
| Fish Audio S1-mini | CC-BY-NC-SA-4.0 | — | yes | **NO** |
| Higgs TTS 2 / IndexTTS-2 | custom / unclear | — | yes | Not until their licences are read |

What "our ElevenLabs" becomes: voice library (stock Indian voices), My Voice (clone with a spoken consent line, same
liveness rule as My Twin), text to speech API, long-form narration for lessons, and the voice that drives the face
engine — one GPU box, two engines. Consent rules of section 9 apply to voices exactly as to faces; Perth watermarking
stays ON for every cloned voice. Phase 10 in section 7 (My Voice) moves earlier: voice is needed by the lessons anyway.

## Sources (2 Nov 2026)
- Licences read directly: github.com/TMElyralab/MuseTalk (LICENSE + README), huggingface.co/TMElyralab/MuseTalk (model card
  licence: mit), huggingface.co/stabilityai/sd-vae-ft-mse (mit), github.com/bytedance/LatentSync (Apache-2.0, README uses
  InsightFace), github.com/antgroup/ditto-talkinghead (Apache-2.0, ships insightface_det), github.com/KwaiVGI/LivePortrait
  (MIT), github.com/deepinsight/insightface README ("models ... available for non-commercial research purposes only"),
  github.com/lipku/LiveTalking (Apache-2.0, fps table), github.com/duixcom/Duix-Mobile (DUIX.COM Community Licence).
- Wav2Lip research-only: sync.so/blog/what-is-wav2lip; huggingface.co/spaces/H-Liu1997/TANGO (Wav2Lip README).
- Audio2Face licences: github.com/NVIDIA/Audio2Face-3D-SDK, huggingface.co/nvidia/Audio2Face-3D-v3.0.
- GPU prices: computeprices.com (RunPod L4 / RTX 4090 / L40S), gpu-cost.pages.dev, pricingsaas.com/companies/runpod.
- Provider prices for comparison: docs in the v0.456-era chat price card (LiveAvatar, Tavus, Anam).
