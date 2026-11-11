# Hoola Interactive — the whole product, page by page (plan)

Owner's ask (11 Nov 2026): *"first check how HeyGen looks in design and all its features in all backend, 100 %, every
page and tool in it. Do deep research and make the same plan for Hoola Interactive, end to end."*

This plan sits on top of `docs/INTERACTIVE_AVATAR_PLAN.md` (the engine: models, licences, GPU, cost, consent). That
document says how a face and a voice are made. This one says what the **product** is: every page, every tool, every
route, and the order to build them.

Research behind it, read from HeyGen's own public files on 11 Nov 2026 (126 KB, kept in the repo):

| File | What it holds |
|---|---|
| `docs/research/heygen/01_app_pages_and_design.md` | Every screen of app.heygen.com, from HeyGen's own shipped string catalogue (72 namespaces), design-token stylesheet and help centre. Layouts, panels, empty states, colours, type, radii. |
| `docs/research/heygen/02_features.md` | Every feature and tool, with inputs, options, limits, plan gates. About 150 named features. |
| `docs/research/heygen/03_backend_api_pricing_safety.md` | The v3 API from HeyGen's own OpenAPI file (every endpoint), LiveAvatar, webhooks, MCP tools, plans, limits, consent and moderation rules, enterprise admin. |

Nobody logged in to HeyGen. Nothing was copied: the plan takes the **structure** (which pages exist, what each one
does), never HeyGen's art, wording, fonts or code. HeyGen's terms forbid using their service to build a competitor,
which is one more reason no account was used.

---

## 1. What HeyGen is today (the short version)

1. **It is three products now.** The avatar video app; **LiveAvatar** (real-time, its own site, key and credits — the
   old "Interactive Avatar" was shut down); and **HyperFrames** (the open-source HTML-to-video engine Hoola already
   uses).
2. **The app is script-first, not timeline-first.** The editor is: script on the left (one block per scene), canvas in
   the middle, tools and a properties panel on the right, a strip of scene cards along the bottom. HeyGen says so in
   its own help: "script-focused, not timeline-based".
3. **Home is a launch pad.** "Where do you want to start?" plus workflow cards (prompt to video, scene by scene,
   avatar from script, avatar from photo, create your avatar, template, translate, upscale, clone your voice), an
   avatars strip, and recent work. One variant is a prompt box with chips.
4. **An avatar is three swappable parts:** a look (how it appears), a voice, and motion. The avatar page has those
   three tabs and a "next steps" checklist.
5. **Everything else is an "app"** in an App Library: quick avatar video, photo to video, PPT/PDF to video, batch,
   scheduled series, clipping, podcast, product placement, upscale, speech cleanup, lip sync, face swap, translate.
6. **The backend is job-shaped.** Create a job, poll or get a signed webhook, fetch the file. Every write takes an
   idempotency key. Batches of 100. Keys carry scopes.
7. **Consent exists only for video twins.** HeyGen's own docs say photo avatars and prompt avatars have *no consent
   check and no consent record*. Hoola already does better (section 7).

---

## 2. What Hoola already has (read from the code, 11 Nov 2026)

| Piece | Where | State |
|---|---|---|
| Console page "Hoola Interactive" | `static/console/interactive.js` (413 lines), switch `interactive_page` | **Live.** Tabs Home / My videos / Avatars. One line → scenes → Make → MP4. |
| Studio service | `interactive/studio.py`, 13 routes in `interactive/console.py` | **Live.** Draft, save, make (real steps: voice → align → draw → save), stop, video, photo avatars with consent. |
| Scene looks | title, big number, price, bar chart, lower third | **Live.** Numbers only from her words; a missing number blocks the make. |
| Renderer | HyperFrames via `studio/frames.py` | **Live** (one render at a time). |
| GPU engine | `avatar_engine/modal_app.py` | Voice (Chatterbox, her choice), face (MuseTalk 1.5), live socket. Measured: 37 fps, one student per GPU. |
| Engine studio ops | `video`, `photo_face`, `voice_save`, `transcribe`, `dub`, `podcast`, `personalised` | **Code + tests; the GPU run of the set is still pending.** |
| Live talk ticket | `interactive/api.py` | Built; her live test pending. |
| AI-made faces | FLUX → Wan → MuseTalk, provenance file | Built in the lab; she picks the face by eye. |

So the engine is ahead of the product. The console page is one screen deep; HeyGen's is about forty.

---

## 3. One honest limit before the feature list

**The face engine repaints the mouth only.** MuseTalk moves lips on a prepared clip. It cannot make hand gestures,
head turns, walking, or a full-body performance. That is what HeyGen's Avatar IV and Avatar V do, and it is most of
what makes their newest videos look alive.

What this means for the plan:

- Everything in HeyGen that needs only lip-sync (their "Avatar III" tier) Hoola can match: talking video, photo
  avatar, translate with lip-sync, podcast, personalised video, live.
- Gestures, expressions on command, camera angles, "avatar shots" and walking avatars need a **different model**.
  That is a research phase (I11) with a licence sweep first, exactly like Phase 0 was. It is not promised here.
- The console must say this plainly on the avatar page ("mouth moves, head still") instead of showing controls that
  do nothing.

---

## 4. The pages — Hoola Interactive, end to end

Hoola Interactive stays **one full-screen studio inside the console** (like Create Studio), opened from its sidebar
row. Inside it has its own left rail. Colours, type and corners are Hoola's existing console tokens; the layout
lessons are HeyGen's.

### 4.1 Shell

- **Left rail**, icon over label: Home · Avatars · Voices · Studio · Templates · Brand · Translate · Live · Apps ·
  Projects. Bottom: usage ring (minutes left this month) and Settings.
- **Top right:** search ("videos or tools"), a bell with what finished, the rupee meter.
- **Create button:** one menu with every start point (section 4.2 cards).
- Phone: the rail becomes a bottom bar of five, the rest under "More".

### 4.2 Home

- Line: "Where do you want to start?"
- **Prompt box** (the one that exists today) with chips for language, length, avatar, size.
- **Workflow cards**, each one line of what it does: Describe a video · Build scene by scene · Avatar video from a
  script · Talking photo · Create my avatar · Start from a template · Translate a video · Clone my voice · Talk live.
- **My avatar card:** three steps with real status — Look ✓ / Voice ✓ / Consent ✓ — and what is missing.
- **Avatars strip** and **Recent / Drafts** tabs.
- Empty state: "Create your avatar once. Use it in every video."

### 4.3 Avatars

- **Library.** Tabs: My avatars · Hoola faces (the AI-made, consented set). Filters: language, age, look, framing.
  Card: picture, name, tags (AI-made / Photo / Twin / Verified), heart, menu.
- **Avatar page.** Tabs **Looks · Voice · Consent**. A "next steps" list. Buttons: Use in a video (Quick / Scene by
  scene / Describe it).
- **Create wizard**, three roads:
  1. **Photo avatar** — photo → checks (one face, facing camera, big enough, sharp) → name → consent → voice.
  2. **My twin** — 30–60 s recording (camera in the browser, or phone by QR) with live checks (face in frame, light,
     one person) → the spoken consent line with a one-time code → voice clone from the same recording, with a listen
     gate → "being made" with the real time.
  3. **AI-made face** — describe it (age, look, clothes, setting) → four choices → pick → provenance saved.
- **Looks.** Upload another photo of the same person, or change background (solid, picture, AI scene), framing
  (full / close / circle).

### 4.4 Voices

- Tabs: My voices · Hoola voices. Filters: language, gender, age, use.
- **Clone my voice:** record or upload, consent line, three takes to choose from.
- **Voice settings:** speed, pause button (0.5 s steps), pronunciation per word ("say it like…", with a hear-it
  button).
- **Speak it my way** (voice mirroring): she records the line, the avatar's voice keeps her timing. Engine op needed.

### 4.5 Studio (the editor)

The biggest build. Layout as HeyGen's, script-first:

- **Left: script.** One block per scene. Under each: add scene, pause, upload or record audio. Scene menu: redo
  audio, preview this scene, translate, delete. Long text splits itself into scenes.
- **Centre: canvas.** Click the avatar to change look, framing, background, corner.
- **Right: tools**, one tab each — Avatar · Voice · Text · Media · Elements · Captions · Music · Layout · Brand · AI
  (script helper: shorter / longer / simpler). A **Properties** panel for whatever is selected.
- **Bottom: scene strip.** One card per scene, drag to reorder, duplicate, a transition between cards, total length.
- **Top bar:** title, size (16:9 / 9:16 / 1:1), brand picker, saved-or-not, Preview, **Generate**.
- **Generate box:** title, folder, quality (720p / 1080p), captions on/off, and the **price in rupees and minutes
  before she taps**. Warnings first ("Scene 3 has no number").
- Today's five looks (title, number, price, chart, lower third) become entries under Text and Elements. The rule
  stays: a number comes only from her words.
- Version history with restore. One editor at a time; others watch.

### 4.6 Templates

- Gallery with category and size filters. Detail: what it contains, length, "Use this".
- **My templates:** save any video as one; fields that change are marked as variables (name, price, date).
- Variables are what personalised video and the API fill in.

### 4.7 Brand

- **Brand kit:** logo, colours, fonts, closing card. Import from her website address (Hoola's website builder already
  reads a site's colours and fonts).
- **Glossary:** how to say a word (typed or recorded), words never to translate, forced translations. Import and
  export as a sheet. Used by Studio, Translate and the agent.

### 4.8 Translate

- Drop a video or pick one of hers. Source language (auto) → up to 10 target languages.
- Three kinds, priced differently: **Voice only** · **Voice + lips (fast)** · **Voice + lips (careful)**.
- Options: keep background music, captions, glossary, fit length to speech.
- **Proofread editor:** segment list with speaker and editable translation, play per segment, find and replace,
  versions, export SRT or sheet, then "Generate result". This is where Hoola's Indian languages are the advantage.

### 4.9 Live (Hoola Live)

- **Avatars** that can go live, **Brains** (a "context": what it knows, opening line, links it may read, variables),
  **Voice agents** (voice + language + brain).
- **Try it** in the page. **Share:** a link and an embed snippet, with a time limit and size.
- Two modes, like LiveAvatar: Hoola runs listening + thinking + speaking, or the caller brings their own and sends
  audio.
- Transcript per session. Push-to-talk or open mic. A free test mode that ends after a minute.

### 4.10 Apps

One grid, three shelves. Each app is a small form over an engine op that mostly exists.

| App | What it does | Engine |
|---|---|---|
| Quick avatar video | One scene, script, voice → video | `video` ✔ |
| Talking photo | Photo + words → video | `photo_face` + `video` ✔ |
| Slides to video | PPT / PDF → one scene per slide, notes as script | new: slide images (Hoola has PDF + PPT readers) |
| Link to video | A page or product link → script → video | scrape lane ✔ + draft |
| Batch | Many scripts at once, one folder | `video` × n |
| Series | The same kind of video on a schedule | routines ✔ |
| Clips | Long video → short clips with captions and a score | new: transcript + cut (Video Editor ✔) |
| Podcast | Two hosts from a topic or script | `podcast` ✔ |
| One video, many names | Template + a list of opted-in people | `personalised` ✔ |
| Lip sync | New audio onto an existing video | `dub` path |
| Speech cleanup | Remove "um", pauses, false starts | new: transcript cut |
| Upscale | To 1080p / 4K | **needs a licensed model — sweep first** |
| Product in hand | Avatar holding her product | **needs an image model + gestures — I11** |
| Face swap | — | **deliberately not built** (section 7) |

### 4.11 Projects

- Tabs: Videos · Drafts · Translations · Live sessions · Media. Grid or list. Sort, search by title or script.
- Folders, move, rename, download (video / audio / captions), duplicate, trash with restore.
- **Share page** per video: player, captions switch, language switch (when translated), a button she sets (label +
  link), her logo. **Insights:** views, average watch time, completion.
- **Interactive video** (later): quiz, branches, buttons, "wait for click". SCORM export for schools.

### 4.12 Settings and Developers

- **Usage:** minutes used, by tool, by day; the rupee ledger.
- **Team:** members and three roles (admin / creator / viewer); who may create avatars.
- **Developers:** keys with scopes and expiry, webhooks with a signing secret, request log, the API guide.

---

## 5. Feature by feature — HeyGen against Hoola

State words: **Live** (in production) · **Engine** (op coded, GPU run pending) · **Build** (planned here) ·
**Research** (needs a model Hoola does not have) · **No** (will not build, reason given).

| HeyGen | Hoola Interactive | State | Phase |
|---|---|---|---|
| Stock avatars (500–1,100) | Hoola faces, AI-made with provenance | Engine (4 faces) → grow to 40 | I3 |
| Digital twin, 15 s record | My twin, 30–60 s + consent line | Build | I3 |
| Consent video with spoken code | Same, and stored as a record | Build | I3 |
| Photo avatar | Photo avatar **with consent** | Live (photo) / Engine (talking) | I3 |
| Prompt avatar ("Design with AI") | AI-made face | Engine | I3 |
| Looks (outfit, background, angle) | Extra photos + backgrounds + framing | Build (background needs matting licence) | I3 |
| Avatar III lip-sync | MuseTalk | Engine | — |
| Avatar IV / V gestures, expressions, gaze | — | **Research** | I11 |
| Avatar shots, cinematic avatars, walking avatar | — | **Research** | I11 |
| Voice library | Hoola voices (Chatterbox; Parler for languages) | Engine | I3 |
| Instant voice clone | My voice, with consent | Engine (`voice_save`) | I3 |
| Professional clone (20 min audio) | — | Research (fine-tune licence) | I11 |
| Voice design from a prompt | Parler description voices | Engine (lab) | I4 |
| Voice mirroring | Speak it my way | Research (speech-to-speech model) | I11 |
| Pauses, pronunciation, glossary | Same | Build | I2, I5 |
| AI Studio editor | Studio | Build (largest) | I2 |
| Script writer | Script helper (her brain already drafts) | Live → extend | I2 |
| Stock media, music library | Pexels fallback ✔, Hoola's free beds ✔ | Build the panel | I2 |
| Stylized captions | Burned-in captions (Devanagari needs testing) | Build | I2 |
| Screen recorder | Browser screen capture into a scene | Build | I4 |
| Templates + variables | Same | Build | I4 |
| Video Agent (prompt → plan → video) | Describe a video: plan first, her yes, then make | Live (basic) → plan card + chat edits | I6 |
| PPT/PDF, URL to video | Slides to video, Link to video | Build | I4 |
| Quick avatar video, Batch, Series | Same | Build | I4 |
| AI clipping | Clips | Build | I7 |
| Video podcast | Podcast | Engine | I4 |
| Personalised video | One video, many names (opted-in only) | Engine | I4 |
| Creative Studio (Veo, Seedance…) | Hoola's Create Studio already has these | Live (elsewhere) — link, do not rebuild | — |
| Upscale, frame interpolation | Upscale | Research (licence) | I11 |
| Speech cleanup, lip sync | Same | Build | I7 |
| Face swap | — | **No** | — |
| Video translate, 3 engines | Translate, 3 kinds | Engine (`dub`) → product | I5 |
| Proofread editor | Same | Build | I5 |
| Multilingual player | Language switch on the share page | Build | I8 |
| LiveAvatar full / lite | Hoola Live, two modes | Built, her test pending → builder | I9 |
| Contexts, voice agents, memory, embed | Brains, voice agents, embed | Build | I9 |
| Share page, insights, comments | Share page + insights | Build | I8 |
| Quizzes, branching, SCORM | Interactive video (ties to Shiksha) | Build | I8 |
| Brand system, glossary | Brand kit ✔ (Create Studio) + glossary | Build | I5 |
| Workspaces, roles, sub-workspaces | Team + roles (Hoola has tenants) | Build | I10 |
| API v3, batches, idempotency | Hoola Interactive API | Build | I10 |
| Webhooks, signed | Same | Build | I10 |
| MCP server | Hoola already serves MCP; add the tools | Build | I10 |
| Zapier / Make / HubSpot | Connectors exist (JODO, Composio) | Build one | I10 |
| SSO, SCIM, audit log | — | Later; not before paying teams ask | — |
| Mobile apps | The phone app gets a Hoola Interactive screen | Build | I8 |

Not copied on purpose: HeyGen's 91 SEO "tool" pages (birthday maker, Santa video…), "Grow / Publishing", vertical
homes, the Orby assistant (Hoola's chat is already the assistant).

---

## 6. The backend

All under the existing `server/app/interactive/` package. Today: one JSON file per tenant. That will not carry forty
pages, so step one of I1 is real tables.

### 6.1 Data (new tables, registered in `db.init_db`, each self-healing)

| Table | Holds |
|---|---|
| `hi_avatars` | owner, kind (photo / twin / ai), name, status, consent id, provenance |
| `hi_looks` | avatar, picture or clip, background, framing |
| `hi_consents` | who, the code spoken, the recording, checked by, verdict, when — **never deleted while the avatar lives** |
| `hi_voices` | owner, kind (stock / clone / designed), language, consent id |
| `hi_projects`, `hi_scenes` | the editor's document; versions kept |
| `hi_templates` | scenes + declared variables |
| `hi_jobs` | every make / translate / clip: kind, status, step, started, cost, error — **survives a restart** |
| `hi_videos` | file, length, size, captions, share settings, view counts |
| `hi_translations`, `hi_segments` | proofread rows per language |
| `hi_brains`, `hi_voice_agents`, `hi_sessions` | Live: context, agent, each session + transcript |
| `hi_glossary` | term, language, say-as, translate-as / never |
| `hi_usage` | minutes and rupees per job, per day — the meter |
| `hi_keys`, `hi_hooks`, `hi_hook_events` | API keys with scopes, webhook endpoints, deliveries |

The v0.747 JSON is moved once by a migration, keeping every project and video.

### 6.2 Routes (console, tenant-scoped)

`/api/interactive/` + `avatars`, `avatars/{id}/looks`, `avatars/{id}/consent`, `voices`, `projects`,
`projects/{id}/scenes`, `projects/{id}/versions`, `projects/{id}/make`, `jobs/{id}`, `videos`, `videos/{id}/share`,
`templates`, `templates/{id}/make`, `brand`, `glossary`, `translations`, `translations/{id}/segments`,
`translations/{id}/generate`, `live/brains`, `live/agents`, `live/sessions`, `apps/{name}`, `usage`. The 13 routes
that exist keep working.

### 6.3 Public API (`/v1/interactive/…`, key in a header, I10)

The same job shape HeyGen uses, because it is the right one: `POST videos` (type avatar / photo / studio),
`GET videos/{id}`, batches of up to 50, `POST translations`, `POST live/sessions/token`, `GET usage`. Every write
takes an `Idempotency-Key`. Scopes per key. Rate limits per key.

### 6.4 Jobs

One job table, the worker loop picks jobs up, **one GPU job per tenant, a queue beyond that**. Every job has real
steps and a heartbeat; a stalled job is picked up from its checkpoint or failed with its real reason. This is the
shape `research_runs` and `crawl_jobs` already use.

### 6.5 The meter

HeyGen sells credits. Hoola shows **minutes and rupees**. Before any make: the price card. A monthly ceiling per
tenant that **refuses before the GPU is called** (the `mapsbill` shape). Measured cost today: about $0.036 per live
student-minute on an L40S; the video rate is not measured yet and must be before a price is printed.

### 6.6 Webhooks and MCP

Events: `video.done`, `video.failed`, `translation.done`, `avatar.ready`, `avatar.rejected`, `batch.finished`.
Signed with HMAC, retried with backoff for a day, safe to receive twice. MCP: the same actions as tools on Hoola's
existing MCP server.

---

## 7. Where Hoola must be stricter than HeyGen

1. **Consent for every real face — photos too.** HeyGen checks consent only for video twins. Hoola already asks for
   a photo. Keep it, and store it as a record.
2. **AI-made faces carry their provenance** (model, prompt, seed, "not a real person") and it travels with the video.
3. **No one under 18, no public figure, no dead person** without written permission — refused in code at upload,
   with the reason said.
4. **Every exported video is marked as AI-made**: a visible mark she may place but not remove on free use, and
   content credentials (C2PA) in the file. HeyGen does not confirm C2PA anywhere; Indian rules on labelling AI
   content are tightening, so Hoola builds it in.
5. **Face swap is not built.** It puts one person's face on another's body; consent cannot be checked for the body.
   If she ever wants it, it is her decision and only between two consented avatars of the same tenant.
6. **Personalised video goes only to opted-in contacts**, and sending is her tap (the existing campaign rule).
7. **Political campaigning content is refused**, like HeyGen, and said plainly.
8. **Her data does not train anything.** HeyGen trains on paid plans' content unless opted out. Hoola says the
   opposite on the settings page.
9. **Removal on request**: the person shown can ask for an avatar to be deleted; the path exists in the console.

---

## 8. Phases

Each phase ends in something she can open and judge. Nothing is called done on tests alone.

| Phase | What ships | Checkpoint (her eyes) |
|---|---|---|
| **I0** Engine proof | Run the engine's studio set on the GPU once (`video`, `photo_face`, `voice_save`, `dub`, `podcast`, `personalised`); her live-talk test | She watches the seven outputs. Whatever fails is fixed before any page is built on it. |
| **I1** Shell + data | Left rail, Home with cards, real tables + migration, Projects page, jobs that survive a restart, the rupee meter | Her existing videos are all there; a make interrupted by a deploy resumes. |
| **I2** Studio editor | Script-left / canvas / tools / scene strip, captions, music, text and elements, generate box with price, versions | She builds a 60-second, 6-scene video without leaving the page. |
| **I3** Avatars + voices | Library, avatar page, three create roads, consent recording with spoken code, voice clone, Hoola faces to 40 | She makes her own twin and it speaks in her voice. |
| **I4** Apps, first shelf | Quick video, talking photo, slides, link, batch, series, podcast, one-video-many-names, templates | Each app makes one real video from her own material. |
| **I5** Translate + brand | Three kinds, proofread editor, glossary, brand kit import | One of her videos in Marathi, Gujarati and English, corrected by her in the editor. |
| **I6** Describe a video | Plan card first, her yes, chat edits, "open in Studio" | One line → a plan she changes → the video. |
| **I7** Edit tools | Clips, speech cleanup, lip sync | A 10-minute recording becomes five clips. |
| **I8** Share + interactive | Share page, insights, language switch, quiz / branch / button, SCORM, phone screen | A lesson with a quiz opens on a phone and reports completion. |
| **I9** Hoola Live builder | Brains, voice agents, embed, transcripts, test mode | A support avatar on her own website answers from her facts. |
| **I10** API + team | Public API, keys, webhooks, MCP tools, roles, one connector | A second developer makes a video with only a key and the guide. |
| **I11** Motion research | Licence sweep and lab card for gesture / full-body / speech-to-speech / upscale models | A written verdict per model. Nothing promised before it. |

Order reason: I0 first because six engine ops have never run on the GPU, and every page from I3 on stands on them.
I2 before I3 because the editor works with today's photo avatars and brand mark. I11 runs alongside from the start;
it is research, not a blocker.

---

## 9. What only she decides

1. **Go on I0** — it spends GPU minutes (a few dollars) and needs the Modal lab switched on.
2. **Hugging Face "Agree"** on FLUX.1-schnell, once, for the AI faces (still open from 5 Nov).
3. **The face-parsing model** MuseTalk depends on is lab-only by licence; it must be replaced before any public
   avatar product. This is the one licence item that blocks selling.
4. **Price.** Minutes per plan and rupees per minute — after I0 measures the real cost.
5. **Own GPU server or keep renting** (the earlier plan's numbers: own card wins past ~4,500 live minutes a month).
6. **Face swap** — the plan says no. Hers to overrule.
7. **Hoola faces:** how many, which ages, regions, languages.

---

## 10. Not verified, said plainly

- **HeyGen's screens were never seen.** The page map comes from the text HeyGen ships to every browser and from its
  help centre. Exact pixel layouts, card sizes and which Home variant an account sees are not known.
- **HeyGen's API prices are behind a login.** Every per-minute API figure in the research is third-party and the
  sources disagree. Do not price against them.
- **HeyGen's own numbers contradict each other** (500 / 700 / 1,100 avatars; 85 or 175 languages). The research
  quotes each with its source.
- **Hoola's engine studio ops have not run on a GPU as a set.** This plan's states marked "Engine" mean coded and
  unit-tested, nothing more.
- **Hoola's video cost per minute is not measured.** Only the live rate is.
- **Burned-in captions in Devanagari** are untested.
- **No phase here has been started.** This is a plan.
