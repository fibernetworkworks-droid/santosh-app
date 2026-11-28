# Hoola Vocal, global (v0.999.89) - the build contract

Owner, 21 Nov 2026, on the design canvas claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue: "GO BUILD ALL".

Research behind it:
- `docs/research/elevenlabs/00_FEATURES.md` - every ElevenLabs feature.
- `docs/research/elevenlabs/01_BUILD_OR_BUY.md` - the engine mix and the global rules.

This file is the CONTRACT between the server (`server/app/vocal/`), the console page (`static/console/vocal.js`) and the
phone (`lib/ui/vocal/`). Every route sits under `/api/vocal`, behind the usual key + tenant. Errors are 422 with a plain
English `detail`, or 404 for something not found.

## Engines (server picks, "Hoola Auto")
| id | name | jobs | needs |
|---|---|---|---|
| `gemini` | Gemini voice | speech, dialogue, readings, preview, matched dubbing, voice design / clone / remix when the account allows | GEMINI_API_KEY |
| `eleven` | ElevenLabs (premium) | premium speech, Zulu / Urdu / Yoruba etc., voice changer, voice out of music / remove people, sound effects from words, dubbing in the speakers' own voices | ELEVENLABS_API_KEY in the VPS .env |
| `lab` | Hoola GPU lab | clone / design fallback (Chatterbox / Indic Parler) | the lab address + key |
| `server` | Hoola server | noise clean-up, loudness, joining, game sounds, format conversion | ffmpeg |

An engine that is not set up is `state: "needs_key"` or `"off"`. Its controls are disabled and say why. A language that
no ready engine speaks is refused with a plain line; it is never read in another language.

## GET /overview
```
{ voices: [Voice], langs: [Lang], styles: {id: name}, feelings: [str], engines: [Engine], prices: [Price],
  rules: [...], history: [Row], projects: [...], usage: {...}, limits: {...}, sfx: [preset],
  status: {engines: {...}, connected: {...}} }
```
- **Voice:** `{id, name, gender: "female"|"male"|"", age: "young"|"middle"|"older"|"", tone, accent, langs: [code],
  use: str, engine: "gemini"|"eleven"|"lab", tier: "standard"|"premium", kind: "hoola"|"clone"|"design"|"remix",
  ready: bool, color: "#hex"}`
- **Lang:** `{code, name, native, region: "Africa"|"Americas"|"Asia"|"Europe"|"Middle East"|"Pacific",
  speech: "yes"|"premium"|"none", clone, dialogue, dub, voices: int, quality: "not_tested"|"excellent"|"good"|"fair"|"none"}`
- **Engine:** `{id, name, does, langs, state: "ready"|"needs_key"|"off"}`
- **Price:** `{job, engine, credits, usd}` - estimates; 1 credit = $0.001 of engine cost.
- **Row** (history): `{id, kind: "tts"|"dialogue"|"chapter"|"book"|"sfx"|"cleanup"|"change"|"dub"|"music", title,
  voice_name, lang, engine, seconds, made, ext, take?, job?, chat?, credits?}`

## Speech
- **`POST /quote`** `{job: "tts"|"dialogue"|"sfx"|"change"|"isolate"|"dub_own"|"dub_matched"|"clone"|"design",
  chars?, seconds?, takes?, voice?, lang?, engine?}` -> `{credits, usd, engine, engine_name, line}`.
  `line` is a plain sentence for under the button.
- **`POST /tts`** `{text, voice, lang: code|"auto", style, speed: 0.7-1.3, expressive: 0-1, takes: 1-3,
  engine: "auto"|"gemini"|"eleven", format: "wav"|"mp3"|"flac", rules: bool, chat?}`
  -> `{items: [Row], lang: code, lang_name, engine, credits}`.
  - The text may hold feelings in square brackets: [warm], [whispers], [laughs], [sighs], [excited], [serious],
    [slowly], [cheerful], [pause]. The server turns them into each engine's own form:
    - Gemini: point events become `<laugh>` `<sigh>` `<short pause>`; a feeling at the start of a part becomes that
      part's style.
    - ElevenLabs v3: reads them natively.
    The brackets are never spoken.
  - Limit: 100,000 characters, cut at sentence ends.
- **`GET /voice/preview?id=&lang=`** -> audio. Made once per voice + language and kept, so hearing a voice is free
  after the first time.
- **`GET /audio?id=&format=wav|mp3|flac`** -> the file, converted on the fly.

## Your voice
- **`GET /consent-line?lang=`** -> `{line, english, lang, locale}`. Google's consent statement in one of its 30 consent
  locales. A language without one gets the English statement, and the page says so.
- **`POST /voice/clone`** `{name, file_id, consent_file_id, lang, consent: true}` -> Voice. Needs BOTH recordings
  (uploaded through the chat file lane: the sample 10-30 s, the consent = the person reading the consent line) and a
  real `true`.
- **`POST /voice/design`** `{description, gender}` -> `{previews: [{pid, title, audio_id}]}` - 3 candidates.
- **`POST /voice/design/save`** `{pid, name}` -> Voice.
- **`POST /voice/remix`** `{base, change, name}` -> Voice.
- **`DELETE /voice?id=`**.

## Dialogue
- **`POST /dialogue`** `{lines: [{speaker, text}], cast: {speaker: voice_id}, lang, style, engine?, chat?}` -> Row.
  Up to 6 speakers and 40 lines.
- **`POST /podcast`** `{file_id?|url?|text?, minutes: 1-15, hosts: [{name, voice}], lang}`
  -> `{lines: [{speaker, text}], title}`. Writes the script only; `/dialogue` then makes the sound.

## Studio
- Existing routes: `/project`, `/project/chapter`, `/project/export`.
- **`POST /project/import`** `{file_id?|url?|text?, title?}` -> project. Takes EPUB, PDF, TXT, DOCX, a web page or
  pasted text, split into chapters.
- **`POST /project/cast`** `{id, n}` -> `{characters: [{name, voice}], paragraphs: [{who, text}]}`. Finds who speaks
  each paragraph of chapter `n` and gives each character a voice.
- Reading a chapter only reads paragraphs that changed (cached by paragraph text + voice).
- **`POST /project/export`** `{id, format: "wav"|"mp3"|"m4b"|"srt"}`.

## Dubbing
- **`POST /dub`** `{file_id, langs: [code] (1-6), mode: "matched"|"own", keep_sound: bool}` -> `{id, status}`.
- **`GET /dub/{id}`** -> `{id, status: "working"|"ready"|"failed", mode, source_lang, langs: [{code, name, status,
  audio_id?, video_id?, subtitles_id?}], lines: [{start, end, speaker, text, tr: {code: text}}], error?}`.
- **`GET /dubs`** -> `{dubs: [...]}`.

## Sound tools
- **`POST /change`** `{file_id, voice, denoise}` -> Row. ElevenLabs only. The target voice must be an ElevenLabs voice.
- **`POST /cleanup`** `{file_id, denoise, voice, silence, level, people: bool, music: bool}` -> Row. `people` / `music`
  use ElevenLabs isolation.
- **`POST /sfx`** `{prompt, seconds: 0 = auto | 0.5-30, loop, takes: 1-4}` -> `{items: [Row]}`. ElevenLabs only.
  Presets stay as `{preset, seed}`, free.

## Vocal chat
A Conversation of kind `vocal`, kept out of every Hoola chat list (like the Music chat).
- `GET /chat`, `POST /chat/new`, `GET /chats`, `GET /chat/{conv}/ok`.
- `GET /chat/{conv}/items` -> `{items: [Row]}` - the sounds made in that chat, newest first. Each row carries `job` (one
  ask = one job, holding its takes) and `made`.
- Messages go through the normal `/api/conversations/{id}/messages` route. Her settings ride her message as
  `"[Vocal settings: language X; voice Y; style Z; speed 0.9; takes 2; engine auto]"`, exactly like the Music chat's note.
- In a Vocal chat the model uses `create_studio`:
  - `action=voice` -> Vocal speech with takes;
  - `action=dialogue` -> Vocal dialogue;
  - `action=sound` -> sound effect.

## Global rules
- The default language is the browser's (console) or the phone's; else Auto.
- Every language is shown with its own-script name.
- Prices are in credits plus the user's own money.
- A cloned voice needs the person's spoken yes, in their language. No public figures. No named-person imitation.
- Every file carries an AI mark in its metadata.
- Nothing paid runs without her tap.
