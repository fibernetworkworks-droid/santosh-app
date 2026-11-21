# HOOLA ULTIMATE PC PLAN - every desktop, browser and portal task, measured

Owner: "WE WANT HOOLA CAN PERFORM ALL 100% DESKTOP TASK SMOOTHLY ALSO 100% BROWSER TASK SMOOTHLY / EVERY COMPLEX PORTALS"
-> plan shown in chat -> "GO ULTIMATE PC PLAN" (21 Nov 2026). Repos read end to end the same day (clones in the session
scratchpad, not in this repo): simular-ai/Agent-S (S3 + S4), aaif-goose/goose, browseros-ai/BrowserOS, bytedance/UI-TARS-desktop,
Skyvern-AI/skyvern, vercel-labs/agent-browser, microsoft/playwright-mcp, browserbase/stagehand.

## The honest goal
No agent anywhere does 100% (best published: ~73% on OSWorld 2.0). Some steps are always hers: captchas, OTPs, bank PINs,
Windows admin pop-ups, sites that block cloud computers (those run on HER PC). Goal: **every task Hoola can do, it does
smoothly; every task it cannot, it hands to her cleanly at the right moment.** Every phase is judged by an exam score.

## For the whole world (owner, 21 Nov: "MOST IMPORTANT WE WANT IT FOR GLOBAL AUDIENCE NOT ONLY FOR INDIAN")
- Exams are global: the portal exam covers government / business portals of several countries (US, UK, EU, UAE, Singapore,
  India ...), the practice portal uses international English with mixed currencies, date and phone formats.
- Hoola PC follows each user's country (time zone, language, date format, keyboard) instead of the fixed India setting of
  v0.884 (P1). Hand-off lists (cloud-blocked sites, national logins such as Login.gov / GOV.UK One Login / eIDAS / UAE Pass /
  Singpass / e-Pramaan, captcha styles) are per country, not India-only (P7).

## Rules
- One brain on the server, two kinds of hands: Hoola PC (Linux container) and her PC (Windows now; Mac / Linux in P9).
- Licences: Agent-S, Goose, UI-TARS-desktop, agent-browser, playwright-mcp = Apache 2.0, Stagehand = MIT -> their code may
  be used, with a credit line in THIRD_PARTY_NOTICES.md. **BrowserOS + Skyvern = AGPL-3.0 -> their code runs only as
  SEPARATE, UNCHANGED programs** (Skyvern = its own Docker service on the VPS driving Hoola PC's Chrome over CDP; BrowserOS =
  an optional second browser she installs on her PC). Never mixed into Hoola's own code. Changes to their code would have to
  be published. Owner to confirm with her lawyer; commercial licences exist from both if wanted.
- Every phase: build -> tests here -> she deploys (deploy + pc_deploy) -> exam on a real PC -> keep only if the score rises.
- PC code is frozen; this plan is the recorded exception for all its phases (CLAUDE.md, 21 Nov 2026).

## Phases
| # | Phase | From | Done when |
|---|---|---|---|
| P0 | **The exam**: desktop (40, exists), browser (30, on Hoola's own practice portal, checked by the server), portal (15, real Indian portals, read-only) + a step record of every PC job | Agent-S, all | first score card for all three on both PCs |
| P1 | **One browser engine** + **Hoola PC follows each user's country** (time zone, language, formats): agent-browser in Hoola Desktop + Hoola PC; honest clicks; forms in frames / shadow DOM; before/after page diff; page text marked as data; allowed sites per job; WebMCP when a site offers it; her Chrome driven through the Hoola extension in its own tab group; Electron apps as pages; BrowserOS neo when she installed it | agent-browser, playwright-mcp, Stagehand, BrowserOS | browser exam beats P0, zero false done |
| P2 | **Safety**: smart approval judge (reads free, changes ask), her rules file, data-leaving guard on Hoola PC, passwords only on the right site, approval bound to what she saw | Goose, Skyvern, agent-browser | planted trick tests all blocked, no score drop |
| P3 | **Data without clicking**: Excel / Word / PDF tools, code helper (Hoola PC free, her PC on her tap), cell filler, page data into a fixed shape | Goose, Agent-S, Stagehand | file / sheet exam tasks faster + higher |
| P4 | **Seeing and pointing**: UI-TARS 1.5 7B grounding on a GPU, OCR text spans, reflection after each step, "what can I do here" | Agent-S, UI-TARS | desktop exam up, fewer misses / loops |
| P5 | **Learn once, replay forever**: "watch me do it once" recording, every good run -> a script with blanks, replay without AI, self-heal one step, saved jobs with loops / checks / schedule, Skyvern service for Hoola PC portal workflows | Skyvern (service), playwright-mcp, Stagehand, Goose | a saved portal job replays 10x at ~Rs 0 and survives a planted page change |
| P6 | **Watch and control**: replay page (timeline, screenshots, click markers, video), live dashboard cards (Watch / Stop), take over on her PC, step mode | BrowserOS, UI-TARS, playwright-mcp | every exam job replayable, takeover works on both PCs |
| P7 | **Portals and hard sites**: cloud-blocked list per country -> her PC, clean hand-off for captcha / OTP / national logins of each country (Login.gov, GOV.UK One Login, eIDAS, UAE Pass, Singpass, e-Pramaan / DigiLocker ...), best-of-N for read-only Hoola PC jobs | BrowserOS, Agent-S | portal exam at its best, every blocked step handed to her |
| P8 | **Hoola improves itself**: weekly builder writes helpers from job records, kept only if the exam rises | Agent-S S4 | one cycle raises a score, none drops |
| P9 | **Mac + Linux Hoola Desktop** | agent-desktop / agent-browser binaries, Peekaboo (Goose) | desktop exam runs on a Mac |

## P0 as built (v0.999.68)
- `server/app/pc/trace.py`: every PC step recorded (step, action, tool, masked arguments, window, thought, seconds, the
  screenshot the model acted on) under `data/pc_trace/<tenant>/<job>/`; 200 jobs / 14 days per person kept; owner + her
  own jobs readable at `/api/pc/trace*`.
- `server/app/practice/`: Hoola's own practice portal at `/practice/<run>/<page>` (international English, mixed currencies / dates / phone formats) - forms, login, frames, nested frames,
  shadow DOM, a cookie banner over the button, a wizard, a table, pagination, download, upload, date, slow loading,
  dialogs, a new tab, OTP and captcha hand-offs, a checkout that must stop before paying. What the agent submits is
  recorded per run on the server and checked by code (check kind `server`), never by the agent's word.
- `server/app/quality/pccard_browser.py` (30 tasks) + `pccard_portal.py` (15 read-only real portal tasks across several countries; v0, their
  regexes are unconfirmed until the first run). The card runs a set: `desktop | browser | portal`; Hoola PC is allowed
  without "test" in its name (it is Hoola's own).
- vps-ops `pc_card` lines: `<set>@<pc name>[:id,id]`, e.g. `browser@Hoola PC`, `desktop@test laptop`.

## P0 first result (21 Nov 2026, v0.999.84 on Hoola PC)
Browser exam 24 / 30 (80 %), false done 0, about Rs 92 for the 30 jobs (estimate). Failed (all ran out of time): login (the
password rule - Hoola never types one), a form inside a web component, a cookie banner over the button, a 3-step wizard
with a date box, a hover menu, reordering a list.

## P1 as built (v0.999.93) - Hoola PC first; her Windows PC engine (desktop/) is the next step of P1
- `desktop-linux/pagekit.py` + agent 1.9.0: elements inside web components (open shadow DOM) and same-origin frames
  (frames from another site are counted and said - pixels there); every ref carries role + name and is checked before
  use, a moved element is found again, a gone one is said; the HONEST click = the real mouse at the element's centre via
  CDP Input, refused when something else lies on top (named); `page_hover`, `page_drag` (HTML drag events or a real mouse
  drag); date / month / time boxes take her words ("12 April 1988", day-first unless her country writes month first);
  after every action the page diff (appeared / gone / new text / reordered); page text marked as the website's data; a
  typed value never names its box (privacy: never back to the model, not even in the diff).
- Her country: `pool.her_tz` sends the time zone of her Hoola profile with every profile switch; the agent sets the
  browser's clock, language (`LOCALES`) and date order from it, restarting Chrome only when it changes.
- Exam set v2: `login_code` -> `login_handoff` (pass = the password left alone and the sign-in handed to her cleanly);
  card rows carry the job id; vps-ops `pc_trace` prints every failed job's steps from the step record.
- Measured here: the five jobs walked in a real Chromium on the practice portal, all recorded by the server as asked.
  NOT measured yet: the exam on Hoola PC (deploy + pc_deploy, then pc_card).
- Still to come in P1: the same engine on her Windows PC (desktop/), allowed sites per job, WebMCP, her Chrome through
  the extension, Electron apps, BrowserOS.
