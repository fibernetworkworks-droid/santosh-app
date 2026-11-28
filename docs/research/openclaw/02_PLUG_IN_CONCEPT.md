# OpenClaw inside Hoola - the concept (28 Nov 2026, corrected)

Owner (1): "WE WILL 100 % USE ENTIERLY AS IT IS. JUST PLUGING IT TO HOOLA PROPERLY ... MAKE IT PERFECTLY MUTITENT FUCTIONAL."
Owner (2, the correction): "THE OPEN CLAW ONLY FOR HOOLA COWORKER --- OPENCLAW WILL RUN IN BACKGROUND FOR EVERY USER --- USER
NEVER SEE HOW IS THERE --- USER WILL ONLY KNOW THAT HOOLA COWORKER IS RUNNING AND PERFROMING OUR TASK SMOTHLY. MEANS OPENCLAW
ONLY FOR REAL LIFE WORK TASK FOR NORMAL PEOPLE TO TOP ENTERPRISE LEVEL -- FROM ORDERING THE PASTA FROM WEBSITE TO PERFROMING
LONG NON STOP CODING, DOCUMENTATION, SCRAPING ENTERPRISE LEVEL COWORKING TASK."

## The concept

**OpenClaw is the invisible engine of the Hoola coworker.** The user only ever sees Hoola. When she gives Hoola real work -
order pasta from a website, code for hours non-stop, write documentation, scrape at enterprise scale, any long office task -
Hoola hands that work to HER OWN OpenClaw running in the background, follows it, and shows the progress and the result as
Hoola's own. No OpenClaw screen, name, settings or chat app is ever shown to the user.

```
She (Hoola chat · voice call · phone · console · Hoola's WhatsApp/Telegram)
   -> Hoola coworker (the face: understands, talks, shows steps, asks her yes)
        -> her own OpenClaw Gateway, in the background (the hands: does the work)
             <- live steps, questions, approvals, files, the result
   <- Hoola's own working row, cards, file cards, reply (and spoken on a call)
```

## How it fits (OpenClaw unchanged - official release, only its configuration written)

- **One OpenClaw per user, in the background.** OpenClaw's trust model: one Gateway = one trust boundary, never shared by
  people who do not trust each other. So each Hoola user gets her own container from the pinned image: own state volume
  (its memory, sessions, logins), own config, own Gateway token sealed in Hoola, caps on RAM / CPU / disk, no network path
  to other users' containers. No Control UI or channel exposed; only Hoola's server talks to it.
- **Hoola drives it over OpenClaw's documented Gateway protocol** (`gateway/external-apps`, `gateway/protocol`): start an
  agent run in a session per Hoola chat / task, stream its events (steps, tool calls, thinking, progress), answer its
  approvals and questions, cancel it, read its files and artifacts. Hoola turns the events into its own working row, plan
  card, step rows and file cards; a voice call speaks the milestones.
- **Her yes stays Hoola's.** OpenClaw's exec approvals, ask-user questions and permission requests arrive at Hoola as Hoola
  cards; her tap is sent back. Paying (the pasta checkout) stops for her tap as Hoola's rule says.
- **Her accounts and Hoola's powers go in as tools.** Hoola is added to her OpenClaw as an MCP server bound to her account:
  Gmail / Drive / Sheets / Calendar, Hoola Cred sign-ins, Hoola PC, her desks, Route - with Hoola's own cards on anything
  that sends, pays or deletes.
- **Models metered into Hoola Credits.** Her OpenClaw uses OpenRouter with a key made for her alone (spending limit), so
  every call is counted and nobody spends another user's credit.
- **Background life.** Started on her first task, kept running while work runs (long coding goes on for hours), stopped
  when quiet with its state kept, woken by the next task. Updates: one pinned version for everyone, moved after testing.
- **Not used:** OpenClaw's own chat-app plugins (its WhatsApp is WhatsApp Web / Baileys, against Hoola's rule), its Control
  UI, its own update checks and telemetry. Hoola keeps its own channels.

## Owner's decision 3 (28 Nov): a separate section, Hoola DOD

"Hoola PC (computer jobs) and Hoola Code (coding) -- NEVER TOUCH ALREADY UPTO MARK ... KEEP IT IS EXSINTING DONT TOUCH ANYTHING.
OPENCLAW WORK WITH SEPERATE SECTON NAME HOOLA DOD ( A COWORKER ) --- WHEN USER WILL USE COWORKER IT WILL CHOOSE THE AVTHAR OF IT
AND GIVE THE NAME TO IT --- CHECK THE APP SIDE ALREADY AVATHAR IS BUILD."

- Nothing existing changes: Hoola chat, Hoola PC, Hoola Code, desks, studios, Route, the main avatar. Someone who never opens
  Hoola DOD sees no difference and nothing of OpenClaw ever runs for them.
- **Hoola DOD** is a new section (console + phone). The first time she opens it she chooses her coworker's avatar and gives
  it a name; then she gives it work and it does the work with her own background OpenClaw.
- **The avatar is already built on the phone** (checked): `lib/ui/avatar_setup_screen.dart` (name in any language, checked
  by `avatar/service.check_name`; male / female; call voice from 10 male / 12 female voices) and `lib/ui/avatar_look.dart`
  `LookPickerScreen` (Santosh + 100 female + 100 male 3D looks from around the world, pre-rendered in `assets/avatars/`, the
  same person as the live 3D avatar in calls, `assets/santosh3d/`). It is stored as ONE avatar per account (`avatars` table,
  `/api/avatar`) - the main Hoola companion. The web console has no avatar picker and the server does not serve the look
  images yet.
- So Hoola DOD reuses those screens and the 200 looks, but saves its OWN coworker profile (name, look, gender, voice) so the
  main Hoola avatar stays as it is; the console gets the same picker (the look images served by the server).

## Open points for the owner

1. (Decided: Hoola DOD only; nothing existing touched.)
2. Server capacity: about 1-2 GB RAM per user whose OpenClaw is awake; the server size limits how many work at once.
