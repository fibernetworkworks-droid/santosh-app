# HOOLA MUSIC — our own song studio, for the whole world

Owner, 21 Nov 2026: "WE HAVE EVERY THING -- WE WILL BUILD OUR OWN SUNO -- FOR MUSIC" -> "MAKE IT FOR GLOBAL NOT ONLY FOR
INDIA ... ALL LANGUAGES" -> "ADD AI CHAT TO ALL BOARDS -- SAME LIKE VIDEOS AND IMAGE ... ALL 100% MUSIC AND SONG TOOLS"
-> "START THE BUILD". Design canvas: claude.ai/artifact/Qq4WmnjktJD7VS9torkejn (10 boards).

## What it is

A song studio driven by one chat, like the Create > Video and Image pages. She says what she wants in any language;
Hoola makes the song (2 versions to pick from), then changes it when she asks: shorter, longer, a fade, louder, a new
style, one part remade. Free edits run at once on the server; paid steps show their price and wait for her Yes; every
change is a new version, nothing is lost.

## Engines (research, 21 Nov 2026 — official routes only)

| Engine | Use in Hoola | Status |
|---|---|---|
| Google Lyria 3.5 (Gemini API) | main song engine, ~$0.08 a song (~80 credits) | wired (v0.259, `create/service.song`) |
| ElevenLabs Music v2.5 | remake one part (inpainting), lyrics per part, stems 2/6 | not wired — needs ELEVENLABS key + its terms read |
| ACE-Step 1.5 (MIT, our GPU on Modal) | Hoola Own: fast drafts, extend, cover, backup | not wired — test first |
| Stable Audio 3 | instrumentals / sound effects only (no vocals) | not wired |
| Suno | NO: no developer API, terms forbid bots/scraping/powering other AI | — |
| Udio | NO: no API, walled garden | — |
| MiniMax Music | closed to new users since 20 Aug 2026 | — |

Suno's own MCP lets a person link HER OWN Suno account to an assistant; whether a third-party app may connect is
not checked (read help.suno.com MCP guide first). Not planned.

## Phases

- **M0 MUSIC TEST CARD** — the same songs in the main world languages through each engine, scored in code (made at all,
  length asked vs got, words sung right by listening back, loudness). `python -m app.quality music`. Built v0.999.79 (as 0.999.54)
  (Lyria only; other engines join when wired). NOT RUN LIVE yet.
- **M1 HOOLA MUSIC CORE** — Create > Music as a chat (kind `music`, `app/musicchat.py`, /api/music/chat*), Song
  settings above the box (kind, language Auto + any, singers, length, tempo, versions, keep out, lyrics by parts), songs
  made with `create_studio action=song` in 2 versions on the Create shelf, each set in the chat, free edits
  `create_studio action=song_edit` (trim / cut / fade / loudness / speed / key / EQ / echo-free clean-up) as new
  versions. Built v0.999.79 (as 0.999.54); the phone Music section (the same chat, settings sheet, player, Your songs) v0.999.83. NOT VERIFIED on her server with Lyria.
- **M2 EDITING** — remake one part, change a line, split into parts (stems) + mix: ElevenLabs Music.
- **M3 START FROM YOU** — hum a tune, covers of songs she owns, extend: Hoola Own (ACE-Step) after the test.
- **M4 LANGUAGE MARKS** — each language's quality mark (tested / works / words only) from the M0 card.
- **M5 VIDEO** — lyric / karaoke video in every script, music video via Director, reel hook.

## LATER (owner: "KEEP THIS IN MUSIC WORK MEMORY WE WILL DO THAT LATER")

### Hoola Singers — Hoola's own singing voices
- A cast of named AI singers (10–12: female, male, child; soft, powerful, rap, classical …), made up, never copies of
  real people. The same voice every time: a shop's brand singer for all its jingles, one voice across a series.
- How: make the song with any engine -> split the vocals -> singing-voice conversion to the chosen Hoola Singer on our
  own GPU -> mix back. The same step gives "sing in my own voice" (after her spoken consent take).
- Missing: a singing-voice conversion engine. Research first: licence (many open ones are non-commercial), quality per
  language, GPU cost. Then a "Hoola Singers" board on the design canvas.

## Rules (kept in code)
- Every song carries the AI mark. No copying a named artist's voice or style-by-name for a real person's voice.
- Covers / uploads only of songs she owns or has rights to; film / label songs refused.
- Her own singing voice only after a spoken consent take matched to the singing.
- Money never moves without her tap: a song is made when she sends (price under the box, like Image); paid edits
  (remake, stems) wait for her Yes.
