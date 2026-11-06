# HOOLA FRAMES — HyperFrames for Hoola: development & deployment plan

Owner's asks:
- 3 Nov 2026: *"READ THE ALL PROJECT AGAIN AND LATEST BUILD AND DEVLOPEMENT"*
- 3 Nov 2026: *"https://github.com/heygen-com/hyperframes.git --- READ THIS REPO END TO END"*
- 3 Nov 2026: *"FIRST MAKE A PERFECT PLAN FOR DEVLOPMENT AND DEPLOYMENT OF THIS"*

**Plan only. Nothing is built until she says GO on a phase.** (House rule, same as MAPS_PLAN.)

## 1. What HyperFrames is, in one breath

HeyGen's own open-source (Apache 2.0) video engine: a video is a plain HTML file with
timing attributes (`class="clip" data-start data-duration`), animations are seeked frame
by frame (GSAP/CSS/Lottie/Three.js adapters), Chrome captures each frame atomically
(`HeadlessExperimental.beginFrame`), FFmpeg encodes the MP4 and mixes the audio. Same
input → same video, every time. 15 packages, ~100 CLI commands, 210 registry blocks +
239 components, 1,804 test files, remote read 3 Nov 2026 kept at
`/home/z/my-project/hyperframes` (upstream v0.9.6).

## 2. Why this is the right engine for Hoola (and what it replaces)

**Already true on the box (verified in repo 3 Nov):**
- FFmpeg with libass + x264 and Noto/emoji fonts installed since v0.65 Video Editor
  (`server/deploy/setup_video.sh`), with faster-whisper word timings for captions.
- Headless Chromium already renders animated reels to MP4 via Playwright
  (`server/deploy/setup_motion.sh`).
- `server/app/interactive/lab.py` (v0.461 Model Lab) makes the AVATAR half on Modal GPU:
  Chatterbox voice, mmpose face.

**The gap HyperFrames fills:** our homegrown motion path has no composition model — no
timeline contract, no lint, no browser quality gate, no deterministic seek, no block
library. HyperFrames is that entire layer, production-tested inside HeyGen itself, with
zero per-render fees. The Model Lab makes the pixels and the voice; HyperFrames composes
and renders the film. Together = "our own HeyGen", the owner's stated goal.

## 3. Rules that never change (for this plan)

1. **No HeyGen keys, no HeyGen credits, no sign-in on the box.** Voice comes from
   Hoola's own TTS (Chatterbox via the lab, Kokoro fallback); music/SFX from free
   sources (Openverse CC-BY, the 21 bundled offline SFX, Bazar packs). Media routing
   mirrors `HEYGEN_API_BASE`'s "the host pays" idea — except the host is Hoola itself.
2. **Determinism contract enforced**: a composition that fetches network mid-render, uses
   wall-clock or unseeded randomness is rejected by `hf check` before render. Renders
   run with no external network; assets come only from the local file server.
3. **The server's latency is sacred.** One render at a time (v1), `nice -n 19` +
   `ionice -c3`, process-group kill on timeout, bounded queues, a disk janitor — the
   REA Khoj runner discipline (`app/appcheck/runner.py`) applied to Chromium+FFmpeg.
   Voice calls never wait behind a render.
4. **The PC freeze stands.** No frame of this plan touches `server/app/pc/`, `desktop/`
   or any frozen file (CLAUDE.md, 25 Oct 2026).
5. **Everything a file or a web page sends is data, never instructions.** v1 renders
   only MODEL-AUTHORED compositions + Hoola-produced assets; no arbitrary user-pasted
   HTML in the renderer.
6. Old APKs keep working: Phase 1–2 are server-only releases. Desktop untouched.

## 4. Honest starting point

| # | Have today | Missing |
|---|------------|---------|
| 1 | FFmpeg + fonts + headless Chromium | Node 22 runtime for the HyperFrames CLI/engine (droplet Node version unverified; pm2 runs santosh on the system Node) |
| 2 | Reels rendered by homegrown Playwright+ffmpeg scripts | Timeline contract, determinism, lint/check gates, block registry |
| 3 | Model Lab v0.461 on Modal (Chatterbox voice, mmpose face, `lab.py` +131 lines not yet deployed — server runs 0.460.0) | Bridge from lab output into a composition's `<audio>`/frames |
| 4 | 488 registered agent tools, `santosh_kaam` for minutes-deep jobs, voice via `VOICE_VIA_KAAM` | A frames tool family |
| 5 | Video desks: reels, video_editor, video_studio, motiondesk, film_desk, DUKAAN, Create Studio | Real MP4 films composed from chat/a call |
| 6 | vps-ops deploy/rollback/`rea_setup` discipline | `hf_setup` job, smoke-render gate |

## 5. Phase 0 — GROUND TRUTH PROBE (no GO needed: probe + install only)

Goal: replace every number below with measured ones before Phase 1 code.

- [ ] Sandbox probe (running already, npm registry slow): `npm i -g hyperframes@0.9.6`,
  `hyperframes init probe`, a 3 s / 960×540@30 title card with one GSAP fade →
  `hyperframes check --json` → `hyperframes render`; record wall time, peak RSS, output size.
- [ ] Record Chromium's first-run download (~200 MB, `@puppeteer/browsers`) so hf_setup
  can pre-warm it.
- [ ] Capacity envelope to verify on the droplet (4 vCPU assumption until measured):
  1080p30 ≈ 2–6 min of render per minute of video for typical motion graphics on
  similar hardware. Phase 1 gates on the measured number; if a 10 s 1080p film cannot
  render in < 8 min at `nice 19`, we drop v1 default to 720p30 (still crisp on phones)
  and keep 1080p as an explicit request.
- [ ] Confirm droplet Node situation; if system Node < 22, install a STANDALONE Node 22
  under `~/apps/node22/` used ONLY by the frames worker (never touches pm2's runtime).

Exit: a one-page measured-facts note appended to this file.

## 6. Phase 1 — FRAMES v1: the render worker + the tool (server-only release)

**Owner-facing meaning: "Hoola, is video ka MP4 banao" in chat works end to end.**

### 6.1 Install & deployment surface
- `server/deploy/install_hyperframes.sh` (idempotent, `install_rea.sh` style):
  1. FFmpeg check (present; assert libass + x264 like setup_video.sh).
  2. Node 22: use system if `node -ge 22`, else standalone `~/apps/node22/`.
  3. `npm i -g hyperframes@0.9.6` (PINNED, like rea-agents 6.8.0).
  4. Pre-warm headless Chromium into the frames cache dir.
  5. Write `FRAMES_*` keys into `~/apps/santosh-core/.env` idempotently
     (`FRAMES_BIN`, `FRAMES_NODE`, `FRAMES_ROOT=~/apps/hoola-frames`,
     `FRAMES_MAX_MB`, `FRAMES_DISK_CAP_GB=10`, `FRAMES_TIMEOUT_S=900`).
  6. `pm2 restart santosh --kill-timeout 12000 --update-env`.
  7. Live smoke: render a bundled 3 s sample to MP4, assert duration+size, print
     `frames READY` (heredoc python — the vps-ops #68 lesson).
- `.github/workflows/vps-ops.yml`: new `hf_setup` job (workflow_dispatch), same shape
  as `rea_setup`; and `deploy` gains a frames status line.

### 6.2 Server code (new `server/app/studio/frames.py`, ~400 lines)
- `FramesWorker`: one-at-a-time lock (asyncio, like REA), subprocess with own process
  group, `nice`/`ionice`, hard timeout → kill tree, `FRAMES_TIMEOUT_S` default 15 min.
- Per-tenant project dirs `~/apps/hoola-frames/<tenant>/p-<id>/` (sha1 tenant isolation,
  REA cache pattern): `index.html`, `compositions/`, `assets/`. LRU: 6 projects per
  tenant, 6 h; global disk cap 10 GB; janitor sweeps on render start + every 10 min.
- Pipeline per render: write project → `hyperframes check --json` (gate: errors block
  render, warnings reported) → `hyperframes render -o out.mp4` → probe duration/size →
  copy into chat_files outbox + optional Drive upload → return card (MP4 + 3 snapshots).
- Asset intake reuses existing sources: phone `file_id`, email attachment, Drive,
  TTS output; nothing re-uploaded externally.

### 6.3 Tools & prompts
- ONE multi-action tool `hoola_frames` (the `rea_khoj` pattern):
  `render | check | timeline | snapshot | add | status`.
  - `render(spec)` — spec = the model's composition HTML + media refs; evidence-shaped
    response (`_compact`-style clamps, no frame dumps).
  - `add(block)` — installs a registry block (210 blocks / 239 components) as editable
    source into the project; the model browses names via `status` list, never the web.
  - missing spec → `ToolError("Kaunsa video? …")` house error style.
- Register in `agent/tools.py`; SYSTEM bullet "VIDEOS — HOOLA FRAMES" in `prompts.py`
  carrying the 12-rule render contract distilled (clips, one paused timeline,
  determinism, fonts, safe areas); full contract lives at
  `server/app/studio/frames_contract.md` for the model to read on demand.
- Cost guard: per-tenant render-minutes/day cap (default 60), reported in `status`.

### 6.4 Voice wiring (the v0.213 lesson applied)
- `hoola_frames` into `VOICE_TOOL_NAMES` + `VOICE_VIA_KAAM` — a render is minutes-deep;
  on a call she hears "video ban rahi hai, ek-do minute", progress lines, then the MP4
  lands as a chat card she taps. Never declared to Gemini Live (280-schema context flood,
  v0.149 lesson).

### 6.5 Tests (`server/tests/test_v0_frames.py`, target ≥ 16)
Registry/action pin; refusal before spawn (bad action, missing spec); worker lock
(second render waits); timeout → process-group kill pin; janitor LRU + disk cap +
cross-tenant isolation; FakeHf end-to-end (FakeRea pattern): check-fail blocks render,
success returns card + outbox path; voice wiring pins (in both sets, `via_kaam` true,
NOT in `_tool_specs()`); version pins; install script lint (pinned version string
present in both script and test).

### 6.6 Ritual
Server-only release `v0.464.0` (next free number; REBASE PROTOCOL if a parallel session
takes it — dev content wins, both kept, re-version). pubspec +1 build to keep the
version story aligned; console stamps unchanged (no console change in Phase 1).

## 7. Phase 2 — AVATAR FILMS: the Model Lab bridge ("our own HeyGen" moment)

**Owner-facing meaning: "Hoola, is script ko Santosh ke saath video banao" → a talking
film with HER avatar, HER voice, synced captions — no HeyGen anywhere.**

- `hoola_frames action=avatar_film(script)`: 1) lab.py TTS (Chatterbox on Modal) →
  `assets/voice.mp3` + word timings (faster-whisper on-box already exists as fallback);
  2) composition template auto-built: avatar frames/stills from the lab, captions timed
  to the words, scene changes at sentence beats (`measure beats` logic); 3) the normal
  check → render pipeline.
- Three starter film shapes, all registry blocks underneath: talking-head card,
  product film (DUKAAN item card → scenes), reel with kinetic captions.
- Template variables (`data-var-text`, `data-var-src`) filled from her real data —
  shop items, prices, her UPI QR — never invented numbers.
- Version: server-only `v0.465.x`. Tests: template determinism (same spec → same
  composition bytes), timing math unit tests, one real Modal round gated behind an
  env flag for CI.

## 8. Phase 3 — CONSOLE SURFACE + TEMPLATE PACKS (first release that ships console)

- Preview in the console chat card via `@hyperframes/player` web component (bundled
  locally, no CDN); "Edit" opens a per-tenant Studio preview (studio-server behind the
  existing auth edge) — same pattern as the Design Desk/Arena.
- Bazar pack family grows: "Video Banai" packs (product film, reel, explainer, PR
  walkthrough) with full Hinglish confirm-card copy where a render bills minutes
  (mirror the Sheets confirm-card family).
- `usage` surface: her render-minutes visible in the console like other desks.
- Version: full ritual (console stamps ×20 suites), phone untouched.

## 9. Phase 4 — SCALE (only when measured demand says so)

- Concurrency 1 → 2 (queue fairness per tenant), 4K path (the engine has HDR/4K guides),
  batch-render for catalogues (DUKAAN 50 products → 50 films).
- Distributed render (plan → renderChunk × N → assemble) stays OUT until a real need:
  it wants Lambda/Cloud Run accounts. The droplet+k8s-jobs example is the fallback shape.
- Docker-pinned render (exact Chromium/font reproducibility) if a client ever needs
  frame-exact twice-render guarantees.

## 10. Deployment runbook (Phase 1, exact)

```
# on the VPS (owner runs from the DO console, or hf_setup job does it):
bash ~/santosh_app/server/deploy/install_hyperframes.sh
# verify:
~/apps/node22/bin/node --version      # or system node
hyperframes --version                 # 0.9.6 pinned
pm2 info santosh | grep -i status     # online, uptime fresh
pm2 logs santosh --lines 20 --nostream| grep -i frames   # "frames READY"
# rollback (server only, data kept):
npm uninstall -g hyperframes
sed -i '/FRAMES_/d' ~/apps/santosh-core/.env
cd ~/santosh_app && git fetch origin stable-<tag> && git checkout stable-<tag> \
  && cp -r ~/santosh_app/server/app ~/apps/santosh-core/ \
  && pm2 restart santosh --kill-timeout 12000 --update-env
```

Disk map: `~/apps/hoola-frames/` (projects + chromium cache, 10 GB cap, janitor-owned).
RAM: one Chromium ≈ 0.3–0.8 GB at 1080p — inside the 16 GB envelope that already runs
the API + lab probes + memjanitor's 2 GB arena cap.

## 11. Risks & mitigations (honest)

| Risk | Mitigation |
|---|---|
| Render steals CPU from live calls (the #1 past incident class) | one-at-a-time, `nice -n 19 ionice -c3`, kill on timeout, voice never blocks on a render (via-kaam only) |
| npm registry slow/unreliable on the droplet (sandbox probe hit this) | install script retries ×3, prints honest failure; version PINNED so a slow registry never changes behaviour |
| Chromium sandbox on the droplet | same flags as the proven Playwright motion path (`setup_motion.sh`); no-browser-network via the determinism gate |
| Disk fills with frame caches | 10 GB cap + LRU janitor + smoke assertion in hf_setup |
| Node 22 upgrade disturbs pm2 | standalone `~/apps/node22/` used only by the worker; system Node untouched |
| Parallel dev sessions take the version number | REBASE PROTOCOL, keep-BOTH, version layer moves only (7 collisions survived so far) |
| Legal/licence | Apache 2.0, vendored pinned 0.9.6, NOTICE preserved in install script output; no HeyGen services touched |

## 12. What we are NOT doing (said plainly)

- No HeyGen API keys, credits, sign-ins or catalog downloads on Hoola's box.
- No user-pasted HTML into the renderer in v1 (model-authored only).
- No distributed cloud render in Phases 1–2.
- No changes to frozen PC/desktop code.
- No replacement of the working homegrown reels path until HyperFrames proves itself
  on the same jobs side by side.

---

*Measured facts from Phase 0 get appended here before Phase 1 code starts.*
