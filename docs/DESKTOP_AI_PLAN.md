# HOOLA DESKTOP AI - the plan for "any job on her PC, like a person does"

Owner, 12 Nov 2026: "GO DEEP FIND THE PERFECT SMOOTH, ULTIMATE, PERFORMABLE, ADVANCED, GENERALIZE DESKTOP AI HANDLE
SYSTEM. THE AI CAN DO ANY JOB ON PC PERFECTLY LIKE HUMAN DOES."

This is a research-backed plan, not a promise. Nothing below is built yet unless marked HAVE. The PC code is frozen
(CLAUDE.md); every phase needs her "GO" and is recorded as a freeze exception.

## 1. What the best desktop agents do today (Nov 2026)

- **The bar is above human on the standard test.** OSWorld-Verified (369 real desktop tasks) has the top agent at
  90.2%, Claude Fable 5 at 86.0%, Claude Opus 5 at 83.4%, and the human baseline at 72.4%. On the harder OSWorld 2.0,
  Claude Opus 5.5 is reported at 81.8% (partial score); another source has GPT-6 Astra at 72.6% (different metric).
  Sources disagree in places - the official leaderboard is the authority. [presenc.ai], [miraflow.ai]
- **The model's OWN computer-use tool beats a home-made one.** Anthropic's newest `computer_toolset_20260801` (no beta
  header) is supported by Claude Fable 5.2, Mythos 5.2, Opus 5.5, Sonnet 5.5 and Haiku 5.5. It has 17 member tools,
  including `zoom` (a full-resolution crop of a screen region) and `cursor_position`, `hold_key`, `left_mouse_down/up`,
  `key` with `repeat`. The models are trained on exactly this action set. ~4,500 input tokens per request.
  [Anthropic docs]
- **Anthropic's own reliability rules** (docs + best-practices blog): pre-downscale screenshots yourself (the single
  biggest win - the API's internal downscale is "the main cause of click misses"); start around 1280x720; put the text
  BEFORE the image; zoom before clicking small or dense things; keyboard for tiny targets; end every batch of actions
  with a screenshot and check the result; a human confirms consequential actions; screenshots are untrusted
  (prompt injection). Overlaid grids / tiling did NOT help. [Anthropic docs], [Anthropic blog]
- **Microsoft UFO2 (Windows, MIT licence) - the closest design to what Hoola needs:** a HostAgent decides WHICH app and
  WHEN; per-app AppAgents act inside one app; controls found by Windows UI Automation PLUS a vision model (custom
  controls); a hybrid action layer that calls an app's own API (Win32, COM - e.g. Excel/Word) instead of clicking when
  one exists; a "picture-in-picture" desktop so the agent works without taking her mouse (marked "coming soon" in their
  repo). [Microsoft Research], [arXiv 2504.14603]
- **Simular Agent S3 - more tries + a judge:** run several attempts and let a judge pick the best from a written
  summary of each ("behavior best-of-N"): 62.6% -> 69.9% on OSWorld, later 72.6% on OSWorld-Verified. It works on
  sandboxes, NOT on her real PC (you cannot order the pizza 5 times). [arXiv 2510.02250], [Simular]

## 2. What Hoola already has (HAVE)

| Piece | Where |
|---|---|
| Vision loop: screenshot -> model -> tool calls -> screenshot, 40 / 64 steps, 15 / 22 min | `pc/operator.py` `_run` |
| Two brains: Sonnet 5.5 (live) or Qwen 3.8 Max via OpenRouter | `pc/brain.py` |
| Screenshots at 1280 px wide, text before the image, only 2 old shots kept | `_shot`, `KEEP_IMAGES` |
| Exact mode for apps: Windows UI Automation tree via agent-desktop (`ax_*`, 23 tools) | desktop 1.10.0 `axtree.py` |
| Exact mode for web pages: element refs + whole-form fill (`page_*`) | desktop `control.py` |
| Never points blind after the screen moved; keyboard right after an app opens | v0.91 / v0.857 |
| Her browser, a new tab, her answers / choices asked (`ask_user`), her words into the running task | v0.858 |
| Approval before send / submit / pay / delete / install; OTP typed by the system; ID locker | operator safety |
| Memory of recent runs on this PC; learned recipes from videos (Seekh) | `pc/memory.py`, `seekh.py` |
| One task per PC; several PCs at once; Hoola's own Linux PC | v0.850 |
| Live card + spoken milestones on a call | v0.180 / v0.858 |

## 3. The gaps between Hoola and "like a person, any job"

1. **Home-made action tools, no zoom.** 58 custom tools the model learns from text; the trained toolset is not used
   and there is no zoom - small text / tiny buttons are guessed from a 1280 px picture.
2. **One flat loop for everything.** No planner that splits "order pizza" into stages (open site -> find shop -> pick
   item -> her choice -> cart -> address -> her approval -> pay by her) with a check at each stage. Long jobs drift.
3. **No app-native actions.** Excel / Word / Outlook / Tally are driven by clicks; a person who knows the app uses its
   shortcuts and menus, and a program can use COM (Excel) or Tally's XML port - exact and 10x faster.
4. **No verification step.** The model says "done"; nothing checks the screen against what was asked (the order page
   shows the item, the file exists, the cell holds the number) before the result is spoken.
5. **No recovery playbook.** Pop-ups, cookie banners, "update available", login expired, slow page, wrong window in
   front - handled ad hoc by the model each time.
6. **Skills are not reused.** A job done well once (Swiggy order, GST download, Tally entry) is not kept as a checked
   recipe the next run follows step by step and only falls back to vision when the screen differs.
7. **It takes her mouse.** While it works she cannot use her PC. People expect to keep working.
8. **No measurement.** There is no Windows task suite for Hoola, so "perfect" cannot be shown or protected.

## 4. The plan - phases (each = one release, her GO each time)

**D0 - MEASURE FIRST (the PC card).** 40 real Windows tasks in her world (open apps, Chrome/Edge sites, Excel sum +
chart, Word letter, Tally voucher, Settings change, file move, WhatsApp Web message draft, Swiggy cart up to approval,
IRCTC search, GST portal download...), each with a CODE check of the end state (file exists / cell value / page title /
window). Run on Hoola's own Windows test PC (a cloud Windows VM - her decision, cost) and never on her PC. Scores:
success, steps, seconds, rupees, asks, false "done". Every phase below must move this card or it is reverted.

**D1 - THE TRAINED TOOLSET.** Drive Sonnet / Opus 5.5 with `computer_toolset_20260801` (zoom, cursor_position,
hold_key, mouse down/up, key repeat) for the pixel lane, keep Hoola's `page_*` / `ax_*` / `open_app` / `ask_user` /
`ask_approval` / `ask_otp` as extra tools beside it. Exact pre-downscale to fit the model's limit, coordinates scaled
back, "end each batch with a screenshot". Qwen stays on the custom tools. Expected: fewer missed clicks, smaller
prompt (17 trained members instead of ~40 described ones).

**D2 - PLANNER + STAGE CHECKS (HostAgent / AppAgent).** A cheap planner turns her ask into 3-8 stages, each with a
"done when" a code check or one zoom can confirm; the operator works one stage at a time and may not move on until the
check passes; a failed check = one retry with the reason, then ask her. Her choices (item / size / address / slot)
become planned `ask_user` stages, not luck.

**D3 - APP-NATIVE LANE.** Where an app has a real interface, use it instead of pixels: Excel / Word / PowerPoint /
Outlook via COM (read/write cells, save, export PDF), Tally via its XML port (vouchers, ledgers - ties into BAHI A9),
Windows Settings via `ms-settings:` URIs, files via the desktop file ops. Pixels only where nothing else exists.
Needs a desktop release (1.11.0).

**D4 - VERIFY BEFORE "DONE".** A separate short check reads the final screen (+ zoom + page text / ax text) against her
ask and the plan's "done when". Only a passed check is reported as done; otherwise "partial" with what is missing.
Kills false "ho gaya".

**D5 - RECOVERY PLAYBOOK.** Known interruptions handled by rule before the model sees them: cookie / notification /
"update" pop-ups (ax tree), a login wall (ask her), page not loaded (wait + reload once), wrong window in front (focus
the task's window), screen locked (tell her). Each rule counted on the card.

**D6 - SKILLS THAT GET BETTER.** A job that passed its D4 check is saved as a recipe (stages + the ax/page targets that
worked); the next run of the same job replays the recipe step by step, checking each step, and only calls the vision
model when the screen differs. Seekh video recipes feed the same store. Expected: the 2nd Swiggy order in a fraction of
the time and cost.

**D7 - HER PC STAYS HERS.** Run the agent on a second Windows desktop session (the loopback remote-desktop idea UFO2
describes) or, for web jobs, a separate browser profile window she can watch - so her mouse and keyboard stay free.
Research + a desktop release; Windows edition limits must be checked first.

**D8 - TWO BRAINS WHERE IT PAYS.** For a hard stage on Hoola's own PC (never on her live accounts), allow 2-3 tries
with a judge (the Agent S3 idea). On her PC: one try, her approval gates as now.

## 5. Decisions only she can make

1. A Windows test PC in the cloud for the D0 card (monthly cost) - without it nothing can be measured safely.
2. PC brain per job: Sonnet 5.5 (fast, cheaper) vs Opus 5.5 (stronger on hard jobs, ~5x price) - or Opus only for
   the planner / verifier and Sonnet for clicks.
3. Order: recommended D0 -> D1 -> D2+D4 -> D3 -> D5 -> D6 -> D7 -> D8.
4. D7 changes how Hoola uses her PC (a second session) - her explicit yes.

## 6. Honest limits

- No agent is "perfect" today; the best score above 72% human baseline on a benchmark, not on every real site. Sites
  change, CAPTCHAs and OTPs stay with her, payments stay her tap (house rule, never changes).
- Benchmark numbers above are from leaderboard pages and vendor posts, some disagree; the D0 card is the only number
  that will count for Hoola.

## Sources

- [OSWorld leaderboard 2026 (presenc.ai)](https://presenc.ai/research/osworld-computer-use-leaderboard-2026)
- [OSWorld 2.0 explained (miraflow.ai)](https://miraflow.ai/blog/osworld-2-explained-computer-use-agent-benchmark-2026)
- [Anthropic computer use docs](https://platform.claude.com/docs/en/agents-and-tools/computer-use)
- [Anthropic: best practices for computer and browser use](https://claude.com/blog/best-practices-for-computer-and-browser-use-with-claude)
- [UFO2: The Desktop AgentOS (Microsoft Research)](https://www.microsoft.com/en-us/research/publication/ufo2-the-desktop-agentos/)
- [UFO2 paper (arXiv 2504.14603)](https://arxiv.org/html/2504.14603v2)
- [Agent S3 / behavior best-of-N (arXiv 2510.02250)](https://huggingface.co/papers/2510.02250)
- [Simular: Agent S3 above human baseline](https://www.simular.ai/articles/simular-turns-three)
