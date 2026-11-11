# HOOLA CINEMA - plan, what is built, what is left

Owner, 11 Nov 2026: "https://github.com/Autom8AI/Open-Higgsfield-AI.git -- read this repo first" -> "GO BUILD THE WHOLE SET AS
HOOLA CINEMA END TO END". Built as 0.807, shipped as v0.811.0.

## What was read

`Autom8AI/open-higgsfield-ai` @ 297151c (a fork of Anil-matcha's Open Higgsfield AI, branded MATAI): a plain-JavaScript page on
Netlify functions. It has no models of its own; every generation is a paid call to kie.ai or fal.ai, ElevenLabs for voices,
Airtable through Composio for sign-in and the library. Its README still describes the upstream app (Muapi.ai, Next.js) - the
code is different. Licence: README and one package.json say MIT, there is no LICENSE file. Treated as ideas only: ZERO code
copied (a test greps for its names). Every request shape in Hoola was read from the ENGINE'S OWN documents instead.

## What is built (v0.811.0)

| Tool | What she gets | Engine | Models |
|---|---|---|---|
| Cinema still | picture with camera / lens / focal length / aperture / light | Hoola's own picture engine | - |
| Motion transfer | her character performs the moves of a source video | kie.ai | Kling 3.0 / 2.6 motion control, Wan Animate Move |
| Character swap | the person in a video becomes her character | kie.ai | Wan Animate Replace |
| Item swap / edit | change a product / outfit / place, keep the shot | kie.ai | HappyHorse video edit, Wan 2.7 video edit |
| Restyle | whole video in one of 16 looks (incl. Madhubani, Warli) | kie.ai | the two edit models |
| Talking photo | a photo speaks her audio or her typed words (Hoola voice) | kie.ai + Hoola voice | Kling AI Avatar std / pro, InfiniteTalk, OmniHuman 1.5, Wan speech-to-video |
| Lip sync a video | lips follow new audio | kie.ai | Volcengine video-to-video lip sync |
| Picture to video | one picture + one of 26 camera moves | kie.ai | Wan 2.5 image-to-video, Seedance 2.0 Fast |
| Content factory | one brief -> up to 6 different scenes (free) -> one confirmed batch | kie.ai | Seedance 2.0 Fast, Kling 3 Turbo, Wan 2.5 |
| Characters | a person / made-up character / product saved once (1-5 photos) | - | - |

Also: the Video page has 26 camera moves (was 8); My creations tiles have "Use in Hoola Cinema"; finished Cinema videos have
Restyle / Lip sync links, finished stills have Make it move / Make it talk.

Files: `server/app/cinema/` (`specs.py` shapes + presets, `kie.py` client, `service.py`, `api.py`), `static/console/cinema.js`,
styles at the end of `studio.css`, mounted in `studio.js` (`CIN`, view `cinema`), settings `cinema_page`, `kie_api_key`,
`cinema_daily_jobs`. Data: `data/cinema/<tenant>/` (jobs.json, characters.json, photos/).

## Rules held in code

- The key (`KIE_API_KEY`) is in the server's .env only; it is scrubbed from every error.
- Nothing starts without confirm=true (the Create button + one more "are you sure"). A createTask is never retried.
- A source video needs her rights tick. A driven face / body needs her consent tick, unless a saved character vouches
  (a real person is saved only with a recorded yes; the time is kept). Lip sync always asks: the face is in the video.
- This reverses nothing: `image_edit` and `video_kit` still refuse face swap. Cinema's character swap exists only behind the
  two ticks above. It is the owner's call whether that is enough - see "decisions".
- Files are judged by their bytes; photos are re-saved as plain JPEGs (no hidden data); her file names never leave.
- The engine's filter (`nsfw_checker`) is switched on wherever a model has it (their default is off); a short word list is
  refused before anything is sent.
- `cinema_daily_jobs` (20) per person per IST day, counted before any upload. 25 MB per file (the console upload limit).
- A finished video is fetched once, only from the link the engine returned for that task, through the link wall (public
  https, no private hosts), must really be a video, and is kept on her Create shelf marked `ai_made`.

## NOT verified / not built

- No live engine call has been made. Every shape comes from the documents; the first real job is the test.
- No rupee price before a job: the engine publishes no price list. The page shows credits left and what each finished job
  used. The Create month meter does not count Cinema.
- No AI mark / C2PA on the video (only the shelf record says ai_made).
- Source videos over 25 MB (the engine takes 100 MB) need a bigger console upload.
- No agent tool (chat cannot ask for Cinema), no phone screen, no trained (LoRA) character, no first / last frame control,
  no Veo / Sora class models in the factory (the Video page has them, with price cards).
- All users spend the ONE server key's credits; only the daily cap limits a person.

## Decisions that are hers

1. Is the two-tick rule enough for character swap, or should it be owner-only / off (`CINEMA_PAGE`, or drop the tool)?
2. Who pays: one server key for everyone (today), or each user's own key (like ArtCraft could be)?
3. Raise the console upload limit past 25 MB for source videos?

## Next steps, in order

C1 a live run of each tool on her key (cheapest model first) and fix whatever the engine answers differently.
C2 measured cost per tool from `creditsConsumed` -> a price shown before Create, and Cinema in the month meter.
C3 the agent tool (`cinema`) + voice route, cards in chat.
C4 AI mark on every Cinema video (ffmpeg watermark option + C2PA when the signer exists).
C5 phone screen.
