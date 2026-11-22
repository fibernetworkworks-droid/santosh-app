# Hoola Vocal redesign + fixes (v0.999.96) — the build contract

Owner: "GO BUILD" on the design canvas https://claude.ai/artifact/GkVsAZLf4iTSJMUrEjtiuH
(15 boards: Vocal chat, Speech, Voice library, Your voice, Dialogue, Studio, Dubbing editor,
Voice changer + Clean-up + Sound effects, Settings, dark, phone chat / speech / voices / dubbing)
and on "Create → Voice opens Vocal Speech, one place".

Every part below is built to this file. Server routes live under `/api/vocal/*` (vocal/api.py,
vocalchat.py). Console = `server/app/static/console/vocal.js` + `vocal2.css`. Phone =
`lib/ui/vocal/*.dart`. No visible text names a server key (no `ELEVENLABS_API_KEY`,
`GEMINI_API_KEY` on any page); prices are shown in credits only; all text English.

## 1. Look (console) — the Create Studio frame

- Sidebar 248 px on `--side-bg`, the real Hoola mark (`static/console/mark.js` drawing, violet),
  "Hoola" + a small "Vocal" badge, "Back to chat", then groups:
  Make: Vocal chat, Speech, Dialogue, Studio, Dubbing · Voices: Voice library, Your voice ·
  Tools: Voice changer, Clean-up, Sound effects · Assets: Your sounds, Dictionary, Settings.
  Active row = `--pri-soft` background, `--pri-ink` text, 3 px violet bar on the left.
  Credits card at the bottom ("This month · N credits left", bar, "X of Y used").
- Top bar 52 px: crumb "Vocal · <page>".
- Vocal chat page: chat column 560 px (header row: tile + "Vocal chat" + one line, Earlier
  chats, New chat), Literata replies, her bubble on `--sunk`, take-set cards with waveforms,
  change chips, footnote "Made by AI · marked in the file · <engine> · N credits"; the composer
  DOCKED at the bottom = the Music chat bar (+ 36 px, ONE settings pill "Speech · Hindi · Meera ·
  2 takes" with chevron opening the settings sheet, engine chip, wand = Improve, round 36 px
  send, grey until there are words); price line under it in credits. Right: "Your sounds"
  stage on `--sunk` (tabs All / Speech / Dialogue / Dubs / Voices, search, cards).
- Tool pages: settings panel left (~420 px) + results stage right on `--sunk`.
- Every dropdown = `HoolaMenu` (console menu.js). No native `<select>`, no bare
  `<input type=file>` (a button opens the hidden picker). No hard-coded colours: tokens only
  (`--bg --side-bg --surface --sunk --ink --mut --dim --pri --pri-soft --pri-ink --line
  --box-line --pill --on-pill`), so dark mode follows the console theme.
- Phone width (<= 720 px): sidebar becomes a drawer behind a menu button in the top bar; the
  stage moves under the chat / panel; nothing scrolls sideways at 390 px.
- Delete the old `#hvRoot`-only rules from v2.css (keep shared `:is(#hiRoot,#hvRoot)` rules
  only if Interactive needs them — Interactive must look unchanged).

## 2. Server fixes (all in the same build)

1. Dubbing subtitles really made: every finished dub language has SRT and VTT.
   `GET /api/vocal/dub/{did}/subtitles?lang=es&format=srt|vtt` -> the file.
2. Dubbing editor (matched mode, where Hoola makes each line itself):
   `GET /api/vocal/dub/{did}/lines?lang=es` -> `{lines:[{n,start,end,speaker,src,dst,too_long}]}`;
   `PUT /api/vocal/dub/{did}/lines/{n}` body `{lang, text}` -> saves the text;
   `POST /api/vocal/dub/{did}/lines/{n}/redo` body `{lang}` -> re-speaks that one line, rebuilds
   the language's sound + video, 1 credit. Own-voice mode (ElevenLabs): lines are read-only
   unless the ElevenLabs dubbing resource API is used; if not built, the response says
   `editable:false` and the page says why in plain words.
3. Speech `format` honoured: mp3 / wav / ogg / m4a (ffmpeg); the take's file is in that format.
4. `GET /api/vocal/audio?id=&format=` converts to exactly mp3 / wav / ogg / m4a; the overview
   lists `formats:[{id,name,note}]` = MP3 small for sharing, WAV studio quality, OGG for
   WhatsApp, M4A for iPhone. The download menus read this list.
5. Price hint follows the job id, never a label.
6. Matched dub: up to 6 speakers (the page offers 6).
7. Own-voice dubs (`_dub_own`) are counted in credits like every other job.
8. Voice changer accepts a recording made in the page (webm / ogg / m4a from MediaRecorder —
   converted with ffmpeg) and can target her own cloned voice when that clone lives on
   ElevenLabs; a Gemini-only voice is refused with a plain reason.
9. A designed-voice option with no audio is never returned.
10. The orphan `POST /api/vocal/music` route is removed.
11. 0 credits (when credits are on): the job is refused before any engine call with a plain
    line and the `credits` route the page links to.
12. The AI mark goes into MP3 / M4A / OGG files too (metadata comment "Made by AI · Hoola Vocal").

## 3. New (ElevenLabs gaps)

1. Shared voice library: `GET /api/vocal/library?q=&lang=&gender=&age=&accent=&use=&sort=&page=`
   -> `{voices:[{id,owner,name,line,langs,gender,age,accent,use,uses,preview}], more}` via
   ElevenLabs `/v1/shared-voices`; `POST /api/vocal/library/add {id, owner, name}` adds it to her
   voices (`/v1/voices/add/{public_user_id}/{voice_id}`), engine eleven. Preview audio served
   through `GET /api/vocal/library/preview?url=` (only ElevenLabs storage hosts).
   No ElevenLabs on the server -> `{voices:[], ready:false, why:"..."}`, plain words.
2. Natural dialogue in one take: `POST /api/vocal/dialogue` gains `mode: "natural"|"lines"`.
   natural = Gemini multi-speaker TTS (exactly 2 speakers) or ElevenLabs text-to-dialogue
   (more); `lines` = today's line-by-line.
3. Tone tags `[warm] [whispers] [laughs] [excited] [pause] [slowly]` work on every engine:
   ElevenLabs v3 reads them natively; for Gemini they become the style / pause instructions;
   never read aloud.
4. Pronunciation dictionary with IPA: `POST /api/vocal/rule {word, say, ipa, lang}`;
   `POST /api/vocal/rules/import {text}` (CSV lines `word,say[,ipa][,lang]`), `GET` in overview.
5. Studio: a chapter re-made re-speaks only paragraphs whose words changed (cache by text hash).
6. Streaming: only if a real progressive path exists end to end (ElevenLabs `/stream` mp3 to a
   plain `<audio>`); otherwise not shown anywhere. Never fake it.

## 4. Create → Voice = Vocal Speech (one place)

- Console: Create Studio's "Voice" tool shows the Vocal Speech page inside the Studio frame
  (same component, same routes `/api/vocal/tts`), not the old voice-over form. Create's own
  voice-over route stays for old callers.
- A take made in Vocal also appears in Create → My creations (kind voice) once.
- Phone: Create → Voice opens the Vocal Speech screen.

## 5. Phone (`lib/ui/vocal/`)

Top bar 52: menu (drawer with the same groups), crumb "Vocal · <page>", Earlier chats, Your
sounds. Chat with the docked one-row bar (+ / settings pill / wand / send 44 px), take cards
with waveforms + Slower / Another voice / Make it English chips. Pages reachable: Speech,
Voice library (Hoola / Shared / Yours tabs, filter chips, hear), Your voice (record in app,
consent statement), Dialogue, Studio, Dubbing (video, language chips, line list with Redo,
Download, Add language), Voice changer, Clean-up, Sound effects, Dictionary, Settings.
Tap targets >= 44 dp. Light + dark from the app theme.

## 6. The pending pieces (v0.999.102, owner: "GO BUILD ALL PENDING")

Everything sections 1-5 left as "not built" is built here. Server code: `server/app/vocal/more.py` (reactions + soft
music, Dub it, own-voice lines, streaming, the sweep) and `server/app/vocal/apps.py` (app keys + webhooks).

1. **Takes 1 / 2 / 4** (`MAX_TAKES` 4, takes A-D); the chat tool says takes 1-4.
2. **Dialogue extras**: `POST /dialogue` gains `reactions` (after a long line, now and then the OTHER speaker gives a
   short listener sound with no words: "Mm-hmm." "Hmm." "Mm." "Ah." - at most one in three lines, never after the last;
   the script she sees stays her script) and `music: "soft"` (a quiet four-chord pad made with ffmpeg on the server,
   faded in and out, under the voices - free; no ffmpeg = refused before anything is made). The row keeps `cast`,
   `style`, `reactions`, `music`.
3. **Dub it**: `POST /take/{id}/dub {langs (up to 4), chat}` - a speech or dialogue take written in the other languages
   by ONE Gemini call (tone tags, numbers, names and prices kept; the take's words are data) and spoken in the same
   voice(s), style and format; each language a new take with `dubbed_from`; a language that fails is listed in
   `failed`, never read in another language. A dialogue made before v0.999.102 kept no cast: said plainly.
4. **Own-voice dub lines** (ElevenLabs dubbing project, docs read 22 Nov 2026): `GET /dub/{id}/lines` reads
   `.../language/{lid}/transcript`; `PUT .../lines/{n}` PATCHes that segment's `translation`; `POST .../lines/{n}/redo`
   on an own-voice dub = `.../transcript/regenerate` (ElevenLabs re-makes only the edited parts of that language), then
   a background wait for `status completed` + `output_revision >= revision`, the new lossless sound put on her video and
   the subtitles refreshed. ElevenLabs allows segment edits on **Enterprise accounts only**; a 402 / 403 is said in those
   words. Language targets are kept on the dub (`targets`); older dubs are looked up once.
5. **Play while it is made** (Premium voices only): `POST /tts/stream` checks everything a take checks and returns a
   one-time link `/api/vocal/stream/<token>` (2 minutes, works once - a plain `<audio>` cannot send her sign-in); the
   public route passes ElevenLabs' chunked mp3 (`/v1/text-to-speech/{voice}/stream`, `mp3_44100_128`) on as it comes and
   then keeps the whole take on her shelf with the AI mark. A Standard voice says plainly it is made whole first.
6. **Keep my sounds**: `keep_days` 0 (never delete) / 7 / 30 / 90 in `PUT /settings`; a worker slot
   (`vocal_sweep_jobs`, every 6 hours) and `POST /sweep` delete sounds, dubs and the videos uploaded for them older than
   that. Her voices, dictionary, Studio projects and settings are always kept.
7. **For your own apps**: `GET /apps`, `POST /apps/keys {name}` (the whole `hv_live_` key shown once; only its SHA-256
   + last 4 kept; up to 5; `DELETE` stops it at once), public doors with `Authorization: Bearer hv_live_...`:
   `GET /api/vocal/v1/voices`, `POST /api/vocal/v1/speech` (one take, the file itself back, `X-Hoola-Id` /
   `X-Hoola-Credits`), `GET /api/vocal/v1/sounds/{id}`; 120 calls an hour a key; her credits, the same rules.
   Webhooks: `POST /apps/hooks {url, events}` (https, a public address only - checked again before every send; up to 3;
   the `whsec_` signing secret shown once, kept sealed), events `sound.ready` / `dub.ready` / `dub.failed`, header
   `X-Hoola-Signature: t=<unix time>,v1=<hex HMAC-SHA256 of "<t>.<body>">`, 3 tries (now, 5 s, 30 s), no redirects,
   10 s each, the last answer shown; `POST /apps/hooks/{id}/test`.

NOT VERIFIED: no real ElevenLabs stream / transcript / regenerate call and no real webhook target; the sweep and the
app doors run on this server only after deploy.
