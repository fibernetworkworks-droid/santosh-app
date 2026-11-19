# Four tiers for pictures, video, voice and music (19 Nov 2026)

Owner's ask: "THIS IS PERFECT. NOW FOR IMAGE, VIDEO, ETC GENERATION" (after `11_model_tiers.md`).

How these differ from the text tiers: in media the best model is often also cheap (Gemini Omni 1.2 Flash is #1 for
video and cheaper than most), and the price is set by the size of what is made - resolution and seconds for video,
minutes for voice. So a tier here is a model AND a size. Quality = LMArena media boards (11 Nov 2026, 500+ votes) and
voiceofindia.ai for Indian speech; prices = OpenRouter's live media price list (18-19 Nov) or the maker's own page,
Rs 88 to the dollar. "Not rated" = no public board has scored it; "free" = Hoola's own tools on her server (no AI model).

| Job | ULTRA (best, burns credit) | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| Making pictures (per picture) | GPT-Image-2.5 Sunburst, Rs 3.41 (#1) | Grok Imagine Image 2.0, Rs 1.09 (110 below) | Muse Image, Rs 0.27 (162 below, 62k votes) | Muse Image, Rs 0.27 - nothing cheaper is worth using (next: Recraft V4.1 Flash, Rs 0.19, 327 below) |
| Editing pictures (per picture) | GPT-Image-2.5 Sunburst, Rs 3.41 (#1) | Grok Imagine Image 2.0, Rs 1.09 (82 below) | Muse Image, Rs 0.27 (119 below, 211k votes) | free: Hoola's own edits (crop, resize, text, filters, background removal - `image_edit` local) |
| Video from words (per 5 seconds, with sound) | Gemini Omni 1.2 Flash at 4K, Rs 91.7 (#1 model, top size) | Gemini Omni 1.2 Flash at 720p, Rs 30.6 | Grok Imagine Video 1.5 Lite at 720p, Rs 13.2 (lite version of a model 52 below; lite itself not rated) | Gemini Omni 1.2 Flash at 360p, Rs 10.2 (best model, small picture) |
| Video from a picture (per 5 seconds) | Gemini Omni 1.2 Flash at 4K, Rs 91.7 (1080p choice: MiniMax H3, Rs 57, 10 below) | Gemini Omni 1.2 Flash at 720p, Rs 30.6 | Grok Imagine Video 1.5 Lite at 720p, Rs 13.2 | Gemini Omni 1.2 Flash at 360p, Rs 10.2 / Grok 1.5 Lite at 480p, Rs 8.8 |
| Editing video (per 5 seconds) | Wan 3.0 at 1080p, Rs 88 (#1) | Wan 3.0 at 720p, Rs 44 | Gemini Omni 1.2 Flash at 720p, Rs 30.6 (28 below) | free: Hoola's own `video_kit` (trim, crop, captions, music, ffmpeg) |
| Talking avatar video (per minute) | HeyGen Avatar 6, Rs 528 (1080p) | HeyGen Avatar 6 Turbo, Rs 264 | Hoola's own lab (MuseTalk), about Rs 3.2 a live minute - not in production yet | free: Hoola Frames (photo + voice, animated, not lip-synced) |
| Voice-over, text to speech (per spoken minute) | Eleven v4, Rs 6.3 (#1) | Gemini 3.8 Flash TTS, Rs 1.5 (18 below - nearly the best) | Gemini 3.8 Flash-Lite TTS, Rs 1.06 (48 below) | Gemini 3.8 Flash-Lite TTS, Rs 1.06 - nothing rated is cheaper |
| Speech to text, Indian languages (per hour, error rate) | Bodhan Indic Transcribe Core, 3.4% (its own API; price not checked) | Sarvam Saaras v3, 3.7%, Rs 30 (Rs 45 with speaker names) | MAI-Transcribe-2, 4.8%, about Rs 9 (OpenRouter's unit unclear) | Nemotron 3.5 Transcribe, 6.6%, Rs 5.3 / free: Hoola's own Whisper (Kaan, not rated) |
| Music (per song) | Lyria 3 Pro (Hoola Create; Google's price) | Eleven Music, about Rs 13 a minute | Stable Audio 2.5, about Rs 18 a song (up to 3 min) | MiniMax Music, about Rs 3 a song / Lyria 3 Clip, Rs 3.5 per 30 s |

Music has no public quality board: its order is by the maker's standing, not a score.

## What common jobs cost in each tier

| Job | ULTRA | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| 10 product pictures | Rs 34 | Rs 11 | Rs 2.7 | Rs 2.7 |
| A 30-second reel from words (6 clips of 5 s) | Rs 550 (4K) | Rs 184 (720p) | Rs 79 (720p) | Rs 61 (360p) |
| A 2-minute voice-over | Rs 12.6 | Rs 3.0 | Rs 2.1 | Rs 2.1 |
| A 1-minute talking-avatar video | Rs 528 | Rs 264 | about Rs 3 (own lab, when live) | free (not lip-synced) |
| Transcribing a 1-hour Hindi meeting | Bodhan's price | Rs 30 | about Rs 9 | Rs 5 / free |

## Notes

- Video is where credit burns fastest: one 30-second ULTRA reel costs as much as about 130 ULTRA chat replies.
- Gemini Omni 1.2 Flash is the best video model AND the HIGH pick: going down a tier mostly means a smaller picture.
- Google risk: every Gemini pick needs one test call on her account first (Gemini 4 Carbon was refused on 17 Nov).
- Picture prices are approximate: makers price by image tokens and the size changes the cost.
- Hoola Create already shows a price card and waits for her Haan before any paid picture / video / voice job.
