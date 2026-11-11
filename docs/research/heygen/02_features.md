# HeyGen feature catalogue (as of 11 Nov 2026)

Scope: built from HeyGen's own pages fetched today (pricing, help centre, monthly release posts Aug 2025 – Oct 2026, API changelog, LiveAvatar docs). Every entry is CONFIRMED (official HeyGen source) unless marked REPORTED. I could not see inside the logged-in app, so the in-app "Apps" grid is reconstructed from help articles and release posts; gaps are listed in section (b). No files were written.

Three things to know before the detail:
- **HeyGen is now three products, not one**: the avatar video app (app.heygen.com), LiveAvatar (separate site, separate credits and plans), and HyperFrames (open-source HTML-to-video engine plus agent tooling).
- **Since Sept–Oct 2026 HeyGen ships its own foundation models**: HeyGen Video 1 (general text/image/reference-to-video with audio) and HeyGen Voice 1 (TTS, cloning, speech-to-speech), alongside Avatar III/IV/V.
- **HeyGen's own numbers disagree with each other**: stock avatars are quoted as 500+, 700+, 1,100+ and "230+"; languages as 175+/177+ in marketing against 85 languages / 157 locales in the help list; Avatar IV credits as 16–31/min in help and Avatar V as 48/min on the avatars page (a third-party review quotes 20/min for IV, V and Video Agent).

Source abbreviations: PR = heygen.com/pricing; REL-<month> = heygen.com/blog/heygen-<month>-<year>-release; API-CL = developers.heygen.com/changelog.md; HC-<id> = help.heygen.com/en/articles/<id>; LA = liveavatar.com; LA-CL = docs.liveavatar.com/changelog.md.

---

## 0. Plans, credits and plan gates (PR)

| Plan | Price | Credits/mo | Max video | Export | Custom avatars | Notable gates |
|---|---|---|---|---|---|---|
| Free | $0 | not stated | 1 min, 3 videos/mo, watermark | 720p | 1 | 3 photo avatars, 1 voice clone, 3 motion-control uses/mo, 30+ languages |
| Creator | $29 ($24 annual) | 600, rolls over one month | 30 min | 1080p | 1+ (add-on $29/mo each) | Avatar III/IV, limited V; HeyGen Video 1; 20 motion uses/mo; 10 h TTS |
| Pro | $49 – $4,300 | 1,000 – 100,000 | 30 min | 4K | 1+ | Seedance 2.5, Cinematic Avatars, Veo 3.1, Nano Banana, translation proofread, 16+ h TTS |
| Business | $149 + $20/seat | 1,500 | 60 min | 4K + upscale | 5+ | Shared workspace, SAML/SSO, brand kit, SCORM/LMS, n8n/Make/HubSpot/Zapier, credit top-ups, 2x Pro concurrency |
| Enterprise | Custom | Custom | No max | 4K | 10+ | SCIM, MFA, multi-workspace, sub-workspaces, CSM, 3+ seats |

- Each custom avatar holds up to 500 looks. Stock library is 500+ on Free and 700+ on paid.
- Avatar IV is capped at 30 minutes per video on every paid plan.
- Mobile subscriptions differ: a weekly Creator plan (150 credits/week), credits expire in 30 days, one-time top-ups valid 12 months (HC-10207693).
- Limits come in two kinds: "dynamic" (queue, videos per day, fair use, not published) and "non-dynamic" (slots) (HC-12095329).
- The Jan 2026 post launched Pro at $99 / 2,000 credits; the pricing page now shows $49 / 1,000. Pricing has changed during 2026.

---

## 1. Avatars

**1.1 Stock / Public Avatars**
- What: pre-built presenters cleared for commercial use. Categories are Professional (Half-Body or Chest-Up studio framing), Lifestyle (full-body, real settings) and UGC (selfie-style); the Studio overview also names AI-generated and community-created styles.
- Count: 500+ (Free) / 700+ (paid) on PR; "1,100+" on heygen.com/avatars. New avatars and looks are added weekly (REL-Nov 2025).
- Options: favourites, preset voice on some avatars, looks per avatar.
- Limits: public avatars can go offline (HC-10047067). No kids category exists, and the moderation policy bans avatars that appear under 18.
- Sources: PR, heygen.com/avatars, heygen.com/avatar-lab.

**1.2 Digital Twin / Custom Video Avatar ("Clone a real person"; older names Instant Avatar, Video Avatar)**
- What: a personal avatar of a real person, now on Avatar V by default.
- Input, current flow (Jan 2026): one 15-second webcam recording that captures appearance, voice, motion and consent together. More footage, photos and looks can be added later.
- Input, legacy flow: at least 2 minutes of continuous footage, 1080p recommended, 4K60 best, head turns within 30°, hands below chest (HC-8389138).
- Output: reusable avatar plus an included voice clone; ready in 10–20 minutes.
- Limits: one person per slot, 500 looks, one identity redo per billing cycle. Slots: Free 1, Creator/Pro 1 or 5 (varies by region and account date), Business 5–10. Extra slot $29/mo or $288/yr. Third-party AI-generated footage is not accepted.
- Sources: REL-Jan 2026, HC-9380615, HC-14602974.

**1.3 Consent video**
- What: required for every video-based twin; the person reads the exact on-screen text (may include a code).
- Limits: under 30 seconds; MP4/MOV/WebM; 480p–4K; up to 10 GB. Submit by upload, webcam, or phone QR code (a remote person can submit).
- API: `consent_video` and `consent_text` fields. Enterprise can skip consent ("Level 3") only with an indemnity agreement. "Split-out consent" lets enterprise producers use pre-approved avatars.
- Sources: HC-12092609, API-CL, REL-June 2025.

**1.4 Motion (walking) Avatar**
- What: a twin filmed while walking, sitting or standing. Uses one slot.
- Limits: at least 3 minutes of footage, 1080p30 recommended, 4K60 maximum.
- Source: HC-9378124.

**1.5 Studio avatar**
- Could not verify as a current product name. The only trace is "Professional" stock avatars with studio framing, and Enterprise "identity design services" (heygen.com/enterprise).

**1.6 Photo Avatar / Talking Photo ("Create a virtual character")**
- What: a still image animated to speak.
- Input: an uploaded photo, or "Design with AI" with fields for name, age, gender, ethnicity, appearance, orientation, pose and style.
- Options: engines are Avatar III (7 credits/min photo look, 4/min video look), Avatar IV (16/min photo look, 31/min video look), or Kling/Runway/Hailuo/Seedance (10 credits per video). Custom motion prompt supported.
- Limits: Free 3 avatars; paid unlimited. The look is validated before use. Needs human-like face proportions (no beaks, snouts or heavy masks).
- Source: HC-10034438.

**1.7 Avatar IV (launched May 2025; Digital Twin on IV Aug 2025)**
- What: a diffusion-based audio-to-expression engine that animates a single image, with head tilts, micro-expressions and speech-synced hand gestures.
- Animates: realistic humans, anime, cartoons, animals (dogs are the named example), 3D models, hand-drawn portraits, fantasy creatures; portrait, half-body, full-body, tilted or profile poses.
- Input: photo plus a script and voice, uploaded audio, or recorded voice.
- Where: "Photo to Video" app, AI Studio (per scene), Quick Avatar Video, API.
- Options: custom motion prompt; "Max Quality" vs "Faster" modes (Aug 2025), later replaced by automatic render selection (Nov 2025).
- Limits: 30 minutes per video; custom motion costs 2:1; API is 1080p native (a 4K request returns an upscale) at about $4/min. Sub-workspaces get 10 free Avatar IV minutes per user per month.
- Singing: marketed through a separate "Make Photo Sing" tool page; the Avatar IV page does not explicitly claim singing.
- Sources: HC-11269603, heygen.com/avatars/avatar-iv, REL-Aug/Nov 2025.

**1.8 Avatar V (launched 8 Apr 2026)**
- What: a video-context identity model. It learns your motion from a 15-second clip and applies it to any look photo of you.
- Output: waist-up performance, multiple camera angles (wide, medium, close), claimed stable beyond 30 minutes, lip sync in 175+ languages.
- Options: preset Expression, Gesture and Gaze tabs plus free-text Custom Motion (May 2026); `more_blinking` (Oct 2026); choice of motion-reference video in Advanced Settings; photo fallback when no reference look exists.
- Limits: API $0.05/sec; 48 credits/min on the avatars page; Creator gets "limited" access. Selected automatically in Video Agent for real-human avatars.
- Sources: REL-Apr/May 2026, HC-14602974, heygen.com/avatars/avatar-v, API-CL.

**1.9 Avatar III**
- What: the fast, consistent lip-sync-only engine. Unlimited on legacy plans; exposed in the API June 2026.
- Sources: avatar-lab, API-CL.

**1.10 30-minute single-pass talking video (June–July 2026)**
- What: one 30-minute generation with consistent face and voice, on Avatar III, IV and V, in app and API.
- Source: REL-June/July 2026.

**1.11 Looks (Photo Looks and Video Looks)**
- What: variations of outfit, background, pose and camera angle for one identity. An avatar is motion + look + voice, each swappable.
- Sources for a look: upload, Design with AI, webcam, Google Drive, Instagram, YouTube, TikTok, link, phone.
- Edit options:
  - Appearance presets Refine / Studio / Glow, with sliders for skin, makeup, blemishes, face slimming, exposure, contrast, saturation and warmth.
  - Camera angles (front, left, right).
  - Custom Edit by prompt.
  - Remix into a Scene.
- Limits: 500 looks per avatar; video looks need at least 2 minutes; generated looks cost credits, uploads are free.
- Related: "Looks inside Studio" and "Avatar Backgrounds" (solid colour, stock, AI scene, upload; Full, Circle or Close-up framing) from Nov 2025.
- Source: HC-9964694.

**1.12 Edit Look (Aug 2026)**
- What: avatar-level retouch with one intensity slider; every later video inherits it.
- Source: REL-Aug 2026.

**1.13 Look Packs (June 2026)**
- What: persona-based sets of consistent looks (health and wellness, legal, teacher, fitness), generated by a new people-image engine called "Image N".
- API: `POST /v3/avatars/looks`, types `look_pack` and `template`.
- Source: REL-June 2026, API-CL.

**1.14 Personal Model (2026)**
- What: a per-person image model trained on your photos, for higher identity accuracy in generated looks.
- Limits: minimum 10 photos (30+ recommended); 60 credits; 10–15 minutes; paid plans only.
- Source: HC-14896977.

**1.15 Generative AI avatars ("Design with AI" / prompt avatars)**
- What: fictional characters from a text prompt; in the API as prompt avatars with reference images.
- Source: HC-10034438, API-CL.

**1.16 UGC avatars**
- What: a stock category with selfie framing; marketed for UGC ads, often paired with Product Placement.
- Note: the dedicated UGC page I tried returned 404, so no count.
- Source: avatar-lab.

**1.17 Product Placement app**
- What: combines a product image with an avatar so the avatar holds or presents it.
- Flow: generates four combined images; you pick one, then add script, voice, optional Custom Motion; rendered with Avatar IV.
- Limits: script up to 5,000 characters; 720p or 1080p; handheld products work best.
- History: the older Flux-based placement was removed Nov 2025; it now runs through "Edit existing look" with Nano Banana and reference images.
- Source: HC-12704854, REL-Nov 2025.

**1.18 Custom Motion Prompts / Gesture Control**
- Controllable: facial expression, 13 named hand gestures (wave, point, thumbs up, namaste, clapping, shrug and others), posture, gaze, stillness.
- Not controllable: camera moves, props, walking, scene changes.
- Limits: 10 seconds maximum, then it loops or holds; one gesture per prompt; plan quotas Free 3/mo, Creator 20/mo, Pro and above "maximum".
- Nov 2025 added gesture sequencing and expression controls.
- Source: HC-12805098, PR.

**1.19 Avatar Shots (Seedance 2.0, Apr 2026) and Cinematic Avatars**
- What: prompt-directed cinematic clips starring 1–3 identity-verified twins, with camera moves.
- Limits: 5, 10 or 15 seconds; 60 credits at 720p or 150 at 1080p; no 4K; no audio upload; no editing after generation; real-human video looks only; all paid plans. Stable in six languages.
- API "Cinematic Avatar": 1–3 looks, 4–15 seconds, 720p/1080p; from Nov 2026 also runs on HeyGen Video 1.
- "Cinematic Avatars" is listed as a Pro-plan feature on PR.
- Sources: HC-14448006, API-CL, REL-Apr/June 2026.

**1.20 Multi-avatar scenes**
- Up to 3 avatars in Avatar Shots; two hosts in Video Podcast; Veo 3.1 scenes accept up to 3 reference images per scene (Oct 2025); Batch Mode script boxes take one or more avatars.

**1.21 Background remover for avatars**
- Free on all plans, no credits (HC-9380615, HC-11371315). Transparent WebM avatar export exists (HC-9518951).

**1.22 Face Swap app**
- What: swaps a face into a video, image or GIF, from an avatar or an uploaded photo (720p minimum, front-facing).
- Source: HC-7951446.

---

## 2. Voices

**2.1 Voice Library**
- What: public AI voices plus your clones, filterable by region, accent, voice type, use case, age and emotion, with favourites.
- Count: "300+ voices"; 77 languages and about 146 locales (HC-11391932).
- Engines selectable per avatar: ElevenLabs V3, Orca, Panda, Fish, plus HeyGen Voice. Side-by-side TTS engine testing since July 2025.
- Sources: HC-9834925, HC-16139180.

**2.2 HeyGen Voice 1 (launched 9 Oct 2026)**
- What: in-house TTS and cloning model with a scene-aware mode; claims #1 on the Artificial Analysis leaderboard.
- Controls: 4 similarity modes, expressiveness boost, pitch variation, background level, seed.
- Audio tags: 201 tags (whispers, laughs) on public and instant voices (Nov 2026).
- API: $30 per 1M characters; streaming over SSE or WebSocket; outputs pcm/mp3/ulaw/alaw at 8–48 kHz.
- Source: REL-Oct 2026, heygen.com/models/heygen-voice-1, API-CL.

**2.3 HeyGen Voice Turbo (21 Oct 2026)**
- Lower-latency variant, API only, instant voices only, $15 per 1M characters, free to try to 30 Nov.

**2.4 Instant Voice Clone**
- Input: up to 60 seconds of audio (one page says 15 seconds, another 30). Free in app.
- Limits: clone count is plan-gated (Free 1); extra instant slots cannot be bought.
- API: instant mode is active within seconds; `expressiveness_boost`; can also create a voice from an image.

**2.5 Professional Voice Clone (Sept–Oct 2026)**
- Input: at least 20 minutes of audio (30 minutes to 2 hours is best); up to 30 files in app or 10 by API; 1.5 GB total; upload only.
- Price and limits: $29/mo or $288/yr per voice slot; 5 trainings per month; trains in 20–30 minutes; 11 languages; Enterprise includes 5 slots.
- Controls: speed, volume, pitch, inflection, seed, and `<break>` pauses up to 5 seconds.
- Source: HC-17589678, REL-Sept 2026.

**2.6 Voice Design (prompted voices)**
- What: generate a voice from a text description; the prompt is editable and can be regenerated (Aug 2025).
- Source: HC-9834925.

**2.7 Voice Mirroring / Speech to Speech (relaunched 28 Oct 2026 on HeyGen Voice)**
- What: record or upload your own delivery; the output keeps your words, timing and emphasis in the chosen voice.
- Limits: 300 seconds; 100 MB; WAV/MP3/FLAC/OGG/M4A/AAC; instant voices only (not professional clones); API $0.12/min; 30 requests/min.
- Source: HC-17756130, HC-11408956.

**2.8 Voice Director (Direct Voice)**
- What: per-line delivery instruction, with 8 presets (Excited, Casual, Calm, Cool, Serious, Funny, Angry, Sarcastic) and free text. Requires the Panda engine.

**2.9 Enhance Voice / Enhanced Voice**
- What: delivery style and audio clean-up; Enhanced Voice requires ElevenLabs V3.

**2.10 Voice Doctor (Dec 2025)**
- What: a chat interface to fix a cloned or generated voice ("too much reverb").

**2.11 Pauses, pronunciation, speed**
- Pause button in 0.5-second steps; inline pronunciation with phonetic respelling and audio preview; speed, accent and model set in the script panel (HC-11381771, REL-Jan 2026).

**2.12 Brand Glossary (pronunciation dictionary and translation rules)**
- What: per-term, per-language pronunciation (typed or recorded), forced translations, and do-not-translate terms.
- Limits: import/export CSV or XLSX, up to 1,000 rows and 5 MB; one glossary per workspace on the API (Oct 2026).
- Applies to: Studio, Video Agent, translation.
- Source: HC-8830251.

**2.13 Third-party voices**
- Import ElevenLabs and LMNT voices with your own API key (HC-8310663). Eleven v3 was integrated July 2025.

**2.14 Multilingual voices and script translation**
- Any-language scripts; a Translate button in Voice Settings; base language vs localized accent variants.

---

## 3. Video creation

**3.1 AI Studio editor (new Studio June 2025; redesigned Nov 2025)**
- What: a text and scene-based editor; a timeline exists for interactivity and music.
- Panels: Avatar, Script, AI, Media, Text, Music, Stylized Captions, Templates, Layers, Brand, Recorder, plus a Properties panel.
- Features:
  - "/" Quick Commands, Scene Split, auto-split of long scripts into scenes.
  - Script upload/download (txt, docx, xlsx, csv; 1,000 characters per segment).
  - Magic Match transitions and scene transitions; 12 premium motion elements.
  - Getty stock images and a music library organised by mood.
  - Realistic previews; landscape or portrait format.
- Upload limits: images 200 MB, video 200 MB, audio 100 MB.
- Export: 720p/1080p/4K; 25/30/60 fps; MP4; watermark toggle; audio-only; captions as SRT.
- Sources: HC-11049655, HC-7951425, heygen.com/ai-studio, REL-July/Nov 2025.

**3.2 AI tab in Studio**
- Script Writer (GPT), Motion Designer, Image Generator, Video Generator. Models named over time: Nano Banana, Flux Kontext, Veo 3/3.1, Sora 2, Seedance 1.0.

**3.3 Screen Recorder (July 2025)**
- Captures a screen, tab or window with optional microphone; trim and split into scenes.
- Source: HC-14251628.

**3.4 Collaboration in Studio**
- Comments, tagging, Single Editor Mode (one editor, live viewers, request access, presence indicators); Team and Enterprise.
- Source: HC-13540469.

**3.5 Video Agent (public Sept 2025; 2.0 Jan 2026; HyperFrames-powered July 2026)**
- What: one prompt produces the script, avatar, voiceover, visuals, captions, music and code-generated motion graphics. It shows a creative blueprint ("Video Plan") for approval and can be refined by chat.
- Inputs: prompt, files, Brand System, Brand Glossary, avatar picker.
- Options: 100+ Styles (Mar 2026); Seedance Mode; "Edit a Copy in AI Studio" (editable motion graphics).
- Limits: about 60–80 credits/min standard, about 180–240 in Seedance Mode; planning is free; one help page states a 3-minute maximum.
- API: Video Agent API (Feb 2026); scene-scoped `edit_plan` with up to 50 items.
- Sources: HC-16007192, REL-Sept 2025 / Jan / Mar / July 2026.

**3.6 Templates and Brand Templates**
- Library filterable by use case; custom templates; refreshed social templates with a B-roll editor (Oct 2026).
- Template API variables: avatar, text, frames, icons, images, videos, scripts.
- Source: HC-13466178.

**3.7 PPT/PDF to Video app**
- Input: PPT, PPTX or PDF up to 50 MB and 50 editable slides, or generate a deck from a prompt plus PDF/DOCX.
- Options: speaker notes as script (PPT only); auto brand detection; avatar as a circular overlay; Google Slides import (Aug 2025).
- Source: HC-13007313.

**3.8 URL / article / blog / document to video**
- Tool pages route to Video Agent. Extracts copy, images and brand; Shopify and Etsy links supported; outputs 16:9, 1:1, 9:16.
- Limits: login-walled and single-page-app pages fail.
- Source: heygen.com/tool/url-to-video.

**3.9 Quick Avatar Video app**
- One scene; script up to 2,520 characters (about 3 minutes); Avatar III or IV; 720p/1080p; 9:16 or 16:9.
- Source: HC-12903996.

**3.10 Batch Mode**
- Many single-scene videos at once; output goes to an auto-created Batch folder.
- Source: HC-12704317.

**3.11 Automated Video Series**
- A scheduled prompt-to-video automation (every X days, weekly, set days and time).
- Source: HC-13006248.

**3.12 Instant Highlights v2 / AI Clipping**
- Input: URL or upload, MP4/MOV/WEBM up to 10 GB, 1 minute to 10 hours.
- Options: natural-language moment search; face tracking; two-person layouts; aspect 16:9, 9:16, 1:1; caption styles.
- Outputs: clips with an engagement score (Hook, Flow, Value, Trend), transcript and SRT, XML export, publish to YouTube.
- Plans: Free and paid.
- Source: HC-9278954, REL-Apr 2026.

**3.13 HeyGen Creative Studio (late 2026)**
- What: a unified Video, Image and Voice generation app that replaces the "AI Video Generator" and "Generate Images" apps.
- Video models: HeyGen Video, Seedance 2.5 / 2 / 2.0 Mini, Veo 3.1, Gemini Omni Flash, Wan 3 / 2.6, Hailuo 2.3 / Fast, LTX 2 Fast.
- Inputs: prompt, first and last frame, or references (image, video, audio, avatar).
- Image side: "HeyGen Image" combines up to 5 photos with a template; "Animate" sends any image to video.
- Plans: Free has all video models locked; Creator lacks Seedance; Pro has everything; Enterprise is still on the classic apps.
- Source: HC-17680953.

**3.14 HeyGen Video 1 (30 Sept 2026)**
- What: general text-to-video, image-to-video and reference-to-video model with synchronised dialogue and sound effects.
- Limits: 5–30 seconds (reference mode 15 seconds); 480p to 2K; 16:9, 9:16, 1:1; references up to 9 images, 3 videos, 3 audio; API $0.02/sec.
- Also on: OpenRouter, Runware, ComfyUI.
- Source: HC-17272995, API-CL, heygen.com/models/heygen-video-1.

**3.15 Upscale Video app (Mar 2026)**
- To 1080p or 4K; Standard or Precise engine (Topaz Starlight Precise 2.5); frame interpolation to 30/60/90/120 fps; billed per second; free preview.
- Source: heygen.com/apps/ai-upscaler.

**3.16 Speech Cleanup / Filler Word Removal (June 2026)**
- Removes fillers, pauses and false starts without visible jump cuts; pay per cut.

**3.17 Lip Sync**
- New audio or script onto an existing video. Input 2 seconds to 5 GB; Speed 6 credits/min, Precision 10/min; API from $0.84 / $1.74 per minute.
- Source: heygen.com/tool/create-ai-lip-sync-videos.

**3.18 Video Podcast app (July 2026)**
- What: a two-host (Host and Guest) studio podcast from a topic, document or your own script, with multi-camera cuts and B-roll.
- Options: invite a co-host's avatar by email; 16:9 or 9:16; 720p/1080p.
- Limits: 1, 2 or 3 minutes per episode.
- Source: HC-15707329.

**3.19 Captions**
- Stylized word-synced captions: 15 styles (Sept 2025), custom and brand fonts, colour, size, position.
- Closed captions only on translation projects; SRT export.
- API: burned-in `caption.style`; captions are always generated on translations.
- Source: HC-8305536.

**3.20 Edit Video API (Nov 2026)**
- Change script, voice, engine or motion per scene; only changed scenes re-render and bill.

**3.21 Formats**
- 16:9, 9:16, 1:1, 4:5, 5:4, auto; up to 4K; 25/30/60 fps.

**3.22 SEO "tool" landing pages**
- 91 pages on heygen.com/tool. Most are wrappers over the features above (script to video, faceless video, AI news, music video, GIF creator, Santa video, invitation makers, compressor, trimmer, resize, combine, loop). Names are in checklist (a).

---

## 4. Translation

**4.1 Video Translate**
- Input: MP4/MOV/WEBM up to 5 GB, a YouTube or Google Drive link, or an existing project; one source language.
- Engines: Audio Only (4 credits/min), Speed (6), Precision (10; multi-speaker, occlusion, side profiles). Speed and Precision modes launched Nov 2025.
- Options:
  - Up to 10 target languages per job; base language (keeps the speaker's accent) or localized variant.
  - Brand Glossary; Dynamic Duration (±20%); Remove Background Sound; Enhance Voice.
  - Output to Original Specs; captions; collection.
  - SRT in and out.
- Languages: 85 languages / 157 locales in the help list ("175+" in marketing).
- Duration caps: minimum 2 seconds; Creator/Pro 30 minutes; Business 60 minutes; Enterprise 5 hours.
- Gates: audio-only download is Enterprise only; on-screen text is not translated.
- Sources: HC-10029081, HC-11391941.

**4.2 Proofread (Review & Edit)**
- Plans: Pro and above.
- Editor: speaker reassignment and off-screen marking, per-track voices, script edit, pronunciation, Excel/SRT round-trip, version history with restore and a "stale" badge.
- Enterprise: invite external proofreaders without a seat, per language, with comments.
- Source: HC-10024431.

**4.3 Multilingual player (Sept–Oct 2025)**
- One link or embed with an audio and caption language switcher; SCORM tracked.

**4.4 Batch translation API**
- 100 items per call; stock-voice translation (Enterprise); `fps_mode`.

---

## 5. Interactive / real-time (LiveAvatar, liveavatar.com)

**5.1 LiveAvatar (launched Oct–Nov 2025)**
- What: the production successor to HeyGen Labs "Interactive Avatar". WebRTC streaming on LiveKit; separate credits and plans; not cross-compatible with HeyGen avatars.
- Modes: FULL (managed ASR + LLM + TTS, 2 credits/min) and LITE (bring your own stack, 1 credit/min).
- Plans:

| Plan | Price | Credits | Concurrency | Max session | Custom avatar |
|---|---|---|---|---|---|
| Free | $0 | 10 | 1 | 2 min, watermark | none |
| Essential | $99 | 1,100 | Unlimited | 20 min | 720p |
| Business | $475 | 6,000 | Unlimited | 60 min | 1080p |
| Enterprise | Custom (>$40k/yr) | Custom | Dedicated | Custom | Custom; down to $0.01/min |

- Performance claims: under 300 ms to first frame; 99.99% uptime.
- Avatars: 100+ presets, plus 30 new ones on 7 Oct 2026 with six emotions and full body. Custom from a 2-minute video (15 s listening, 90 s talking, 15 s listening) or a single image (alpha).
- Options:
  - Contexts: prompt, opening line, reference URLs that are AI-summarised as knowledge.
  - Voice agents; dynamic variables; session memory.
  - LLM choice (gpt-4o-mini, 4o, 5-nano, 5.4-nano, or custom).
  - TTS: ElevenLabs, Cartesia, Fish. ASR: Deepgram, AssemblyAI, Scribe.
  - Conversational or push-to-talk turn-taking; quality 360p–1080p; session time limits; transcripts.
  - Sandbox Mode (free testing).
- Embed: an iframe with context, voice, language, time limit and orientation.
- Developer surface: JS Web SDK; connectors (ElevenLabs Agents, Cartesia, OpenAI Realtime/GPT-Live, Gemini Live); plugins (LiveKit, Pipecat, Agora, Vision Agents).
- Enterprise: SSO via Okta and Entra.
- Sources: LA, LA-CL, HC-12758516, HC-12758866.

**5.2 Avatar Realtime API / Broadcast (June 2026)**
- Avatars as live-streaming agents that browse the web and react to inputs (developers.heygen.com/avatar-realtime).

**5.3 Zoom meeting avatar (HeyGen Labs, 2024)**
- An Interactive Avatar joins Zoom meetings using OpenAI Realtime Voice; "Zoom" is still on the integrations page. Google Calendar assignment and meeting summaries are REPORTED only (uctoday.com, maginative.com).

**5.4 Open-source GPT-Live + LiveAvatar demos (Sept 2026)**
- MIT-licensed starter demos.

---

## 6. Interactive video, sharing, brand, collaboration

- **Interactivity** (Oct 2025 – Mar 2026): quizzes (single or multiple answer), branching paths with a branch view, action buttons (URL or jump to scene), Wait for Click. Business and Enterprise only (HC-13538881).
- **SCORM export**: 1.2 or 2004 4th Edition; completion-percentage slider; "Host video on HeyGen" auto-updating package. Business and Enterprise. xAPI is mentioned only in the translation article (HC-10549082).
- **LMS integration**: share link (REL-Sept 2025).
- **Share page**: emoji reactions; comments (cannot be turned off); Insights (views, shares, downloads, watch time, completion rate); viewer-triggered translation; closed-caption toggle; embed; X, LinkedIn, email, GIF; native LinkedIn publishing (June 2026); YouTube publish from clips. Password protection and folder sharing are Enterprise only. Downloads: video, captions, audio; a folder downloads as a zip (HC-11788079).
- **Brand System / Brand Kit** (Mar 2026): import from a website URL (logos, colours, fonts, assets, motion); unlimited count; all paid plans; applied in Studio, templates and Video Agent (HC-9889198).
- **Workspaces**: roles are Creator, Developer and Super Admin; project and folder access is Private, Specific Collaborators (Editor, Viewer, Proofreader) or All Collaborators; invites by email, link or domain discovery; nested folders and collections (HC-9468098, HC-13016632).
- **Sub-Workspaces** (Enterprise): parent-managed or self-managed billing; share avatars and voices downward; allocate and reclaim credits and slots (HC-12582746).
- **Personalization**: Memory, UI theme and language, use cases (HC-15046858). An in-app support agent ("Ask AI") shipped June 2026.
- **Personalized Video**: template variables driven through Zapier, Google Sheets, HubSpot or the API. The standalone Labs product is discontinued; CSV upload, email sending and "hybrid mode" have been removed (HC-10324568).
- **Not found**: a formal approval workflow. Only comments, viewer roles and enterprise distribution controls exist.

---

## 7. Integrations, developer surface, mobile, enterprise

**Integrations** (heygen.com/integrations, 50 listed): Adobe Express, Airtable, Apollo, Asana, Atlassian, Autohive, Canva, ChatGPT, Claude, Clay, Cursor, Customer.io, Figma, FlowShare, Gamma, GitHub, Google Drive, Granola, Grok, Hexus, Intercom, HubSpot, Linear, Lovable, Make, Manus, Mindstamp, n8n, Notion, Pabbly, Plainly, PostHog, Repurpose.io, Salesforce, Slack, Snowflake, Stripe, Superhuman, Tolstoy, Trupeer, Vercel, viaSocket, Vimeo, Zapier, Zoom. Marked "coming soon": Discord, Microsoft Copilot, NVIDIA NemoClaw, OpenClaw, Telegram. Codex is named in the May 2026 post.

**Developer surface**
- API v3 (v1 and v2 sunset 31 Oct 2026); pay-as-you-go from $5 (Mar 2026); batches of 100; webhooks; custom watermark (Enterprise); Template and Studio scene-composition APIs; burst concurrency.
- Remote MCP server (mcp.heygen.com/mcp/v1, OAuth, all plans); HeyGen CLI; HeyGen Skills for Claude Code and Cursor.
- Models also on fal, Replicate, Runware and OpenRouter.

**HyperFrames** (Apr 2026, Apache 2.0)
- HTML-to-MP4 engine, with: Studio desktop app, Timeline, KeyFrames, Storyboard mode, Code Snippets, cloud rendering (1080p/4K, HDR), community hub.
- Skills: website-to-video, Figma-to-video, PR-to-video, beat sync, launch video, captions.
- Media library: 10,000+ tracks and 75,000+ images.

**Mobile**
- iOS and Android (US Nov 2025; full Google Play release May 2026). iOS "Edit Styles" with 12 templates.
- Reduced editor; no workspace switching; LiveAvatar is desktop only.

**Vertical product**
- HeyGen for Real Estate, with a "White Glove" done-for-you service (US).

**Enterprise and trust**
- Identity and admin: SAML SSO (self-serve on Business); SCIM; MFA; audit logs; usage export by product; admin controls over sharing, downloads, avatar creation and Brand Kit.
- Compliance claims: SOC 2 Type II, GDPR, CCPA, DPF, EU AI Act, HIPAA (HIPAA appears on the enterprise page only, not the security page).
- Data: US-only residency on AWS; no training on enterprise data; zero-data-retention option; 99.9% SLA; reserved GPU.
- Moderation: automated plus human review; bans political content, under-18 avatars and voices, and public figures without consent.
- Sources: heygen.com/enterprise, /security, /moderation-policy, REL-Mar 2026.

**Labs / research**
- Code2Video benchmark; Avatar Real-time technical report; behaviour LoRAs. Interactive Avatar and Personalized Video have both graduated out of Labs or been retired.

---

## (a) Flat checklist of feature names

Avatars
- Stock/Public Avatars (Professional, Lifestyle, UGC, Community)
- Digital Twin / Custom Video Avatar
- 15-second record flow
- Consent video
- Split-out consent
- Motion (walking) Avatar
- Photo Avatar / Talking Photo
- Design with AI avatar
- Avatar III
- Avatar IV
- Avatar V
- Photo to Video
- 30-minute single-pass video
- Looks (Photo/Video)
- Design a Look
- Edit Look (Appearance, Camera angles, Custom Edit, Remix into Scene)
- Look Packs
- Personal Model
- Avatar Backgrounds
- Background removal
- Custom Motion Prompts / Gesture Control
- Expression/Gesture/Gaze presets
- Avatar Shots (Seedance 2)
- Cinematic Avatars
- Product Placement
- Face Swap
- Transparent WebM avatar export

Voices
- Voice Library
- HeyGen Voice 1
- HeyGen Voice Turbo
- Instant Voice Clone
- Professional Voice Clone
- Voice Design
- Voice from image (API)
- Voice Mirroring / Speech to Speech
- Voice Director
- Enhance Voice / Enhanced Voice
- Voice Doctor
- Audio tags
- Pauses
- Pronunciation
- Brand Glossary
- Voice engine picker (ElevenLabs V3, Orca, Panda, Fish)
- Third-party voices (ElevenLabs, LMNT)
- TTS streaming API
- Script translate

Creation
- AI Studio
- Script panel
- Quick Commands
- GPT Script Writer
- Scene Split / Auto-split
- Script upload/download
- Motion Designer
- Image Generator
- Video Generator
- Magic Match transitions
- Premium motion elements
- Stock media (Getty)
- Music library
- Layers
- Properties panel
- Screen Recorder
- Stylized Captions
- Closed Captions
- Templates / Brand Templates
- Video Agent (2.0, Styles, Seedance Mode, Video Plan)
- PPT/PDF to Video
- Google Slides import
- URL/Article/Blog/Document to Video
- Quick Avatar Video
- Batch Mode
- Automated Video Series
- Instant Highlights / AI Clipping
- Creative Studio
- HeyGen Video 1
- HeyGen Image
- Generative B-roll (Veo 3.1, Sora 2, Seedance, Wan, Hailuo, LTX, Gemini Omni Flash, Nano Banana, Flux Kontext)
- Upscale Video
- Frame interpolation
- Speech Cleanup / Filler Word Removal
- Lip Sync
- Video Podcast
- Edit Video API
- 4K export
- Aspect ratios
- Edit Styles (iOS)

Translation
- Video Translate (Audio Only / Speed / Precision)
- Proofread
- Invite proofreaders
- Dynamic Duration
- Remove Background Sound
- SRT import/export
- Multilingual player
- Batch translation

Real-time
- LiveAvatar (FULL/LITE)
- Contexts
- Voice agents
- Session memory
- Embed
- Web SDK
- Connectors
- Plugins
- Sandbox Mode
- Push-to-talk
- Custom LiveAvatar (video/image)
- Avatar Realtime API
- Zoom avatar

Interactive, share, brand
- Quizzes
- Branching
- Action buttons
- SCORM export
- LMS link
- Share page
- Insights
- Reactions/comments
- Password protection
- Embed
- GIF
- LinkedIn/YouTube publishing
- Brand System / Brand Kit
- Memory
- Workspaces and roles
- Sub-Workspaces
- Folders/Collections
- Single Editor Mode
- Personalized Video (via Zapier/HubSpot/API)

Platform
- API v3
- Pay-as-you-go API
- Template API
- Studio composition API
- Batch APIs
- Webhooks
- Custom watermark
- Remote MCP
- CLI
- Skills
- ChatGPT plugin
- 50 integrations
- HyperFrames (Studio, Timeline, KeyFrames, Storyboard, Snippets, Cloud Rendering, website/Figma/PR-to-video, beat sync, media library)
- iOS app
- Android app
- HeyGen for Real Estate
- White Glove
- SSO
- SCIM
- MFA
- Audit logs
- Usage export
- Admin controls
- Moderation
- "What's new" changelog
- In-app support agent

SEO tool pages (wrappers)
- Make Photo Sing
- AI GIF Creator
- AI Music Video
- Ghibli Art Video
- AI News Generator
- Faceless Video
- Birthday / Invitation / Wedding / Save-the-Date / Anniversary / Baby / Santa makers
- Intro Maker
- Loop / Trim / Resize / Compress / Combine / Increase Volume
- Add Text / Photo / Captions
- Subtitle Generator
- AI Course Creator
- Infographic Video
- AI Movie Maker
- AI Ad Maker
- Audio to Video

## (b) Could not verify

- Release posts before June 2025 (May 2025 and earlier return 404), so original launch dates for Photo Avatar, Voice Mirroring, Face Swap, UGC avatars and Instant Highlights v1 are missing.
- The full in-app Apps grid (needs a login) and the Creative Studio image-model list (shown only as an image).
- Exact stock avatar count and per-category counts; any cartoon or animal stock category; "Studio avatar" as a current product; the UGC avatar page (404).
- Credit rates for Avatar V in the app, Face Swap, Instant Highlights, Speech Cleanup, Image generation; the full API price table (pricing pages returned 404 or empty).
- Avatar IV singing as an official capability, and its output resolution in Studio.
- Maximum Video Agent length today (one help page says 3 minutes; PR says "maximum access").
- LiveAvatar supported-language list, idle timeout, and whether the Zoom meeting avatar still works after the move to LiveAvatar.
- Template library size; numeric voice-clone limits for Creator and Pro; dynamic limits (videos per day, concurrency).
- Version history and approval workflow in AI Studio (found only for Proofread).
- Adobe Premiere integration (only Adobe Express is documented; Premiere appears only as WebM import help).
- Canva and Zapier integration depth (not fetched).
- EU data residency: official pages say US only.
- HIPAA: appears on the enterprise page only.
- Not fetched: iOS App Store details, Avatar Realtime API specs, enterprise fine-tuning and identity-design services.
- Third-party-only claims not confirmed officially: "20 credits/min for Avatar IV, V and Video Agent" and "Avatar Realtime limited to enterprise beta".
