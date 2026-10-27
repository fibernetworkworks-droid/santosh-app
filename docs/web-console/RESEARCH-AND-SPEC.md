# Hoola Web Workspace — research and implementation specification

Research date: 27 October 2026 (India). Repository baseline: c63f1e9, Hoola 0.204.0.
Status: source-backed discovery complete for the listed public workflows; first web-only implementation underway.

## Decision and boundaries

Build Hoola as an independent desktop web experience sharing existing APIs with the Android product. Preserve Hoola's Night Glass identity. Chat is the permanent entry point and the record of the work. A result appears in chat; detailed interaction opens in a companion workspace without losing the conversation.

The owner's instruction overrides the historical release ritual: do not edit lib/, tool/, assets used by the APK, pubspec.yaml, Android/desktop build workflows, or frozen PC code. This phase edits only server/app/static/console/ plus web-specific documentation/tests. No backend schemas, shared agent prompts, API contracts or deploy workflows change. No APK release or mobile version bump. Research and implementation are not permission to deploy a public service.

“100% features” means a tracked acceptance checklist covering the agreed Hoola web workflows. It cannot honestly mean every feature of every competitor, every private experiment, every subscription tier, or guaranteed model output quality. Feature availability and layouts change. No exact private product internals, hidden prompts, animation timings, or unverified live-account behavior are claimed here.

## Research method

Read first-party help pages, product feature inventories and changelogs. Separate documented capabilities from our proposed Hoola design. Read Hoola's actual JS/HTML/CSS and backend contracts rather than treating older README descriptions as implemented behavior. Public documentation was inspected; paid/account-specific competitor UI was not exercised. Availability claims do not establish Hoola backend readiness.

### Source register

| ID | First-party source | Verified pattern / limit |
|---|---|---|
| S1 | https://help.openai.com/en/articles/10169521-projects-in-chatgpt | Related chats, files and instructions in projects; contextual work organization. |
| S2 | https://help.openai.com/en/articles/10500283-deep-research-in-chatgpt | Research planning, source choice, visible progress, interruption and cited report/export. |
| S3 | https://help.openai.com/en/articles/9260256-chatgpt-capabilities-overview | Text, image understanding/generation/editing and file/audio workflows. |
| S4 | https://help.openai.com/en/articles/6825453-chatgpt-release-notes | Image-library/reuse direction; release entries are historical, not universal current availability. |
| S5 | https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them | Editable outputs beside chat, return/share, document/design/deck/tool surfaces; plan-specific features. |
| S6 | https://support.claude.com/en/articles/14604416-get-started-with-claude-design | Conversational design, on-canvas iteration and design-system consistency. |
| S7 | https://support.claude.com/en/articles/13454812-use-interactive-connectors-in-claude | Compact in-chat apps and expanded interaction, sandbox boundary and existing connector permissions. |
| S8 | https://support.claude.com/en/articles/10684626-enable-and-use-web-search | Search indicator, verifiable citations and source links. |
| S9 | https://openart.ai/suite/home | Chat/director entry points, specialist tools, brand/character/media assets and templates. |
| S10 | https://openart.ai/features/ | Image, video, audio and animation tool families; capabilities are provider-dependent. |
| S11 | https://openart.ai/whats-new | Unified creation panel, cross-tool reuse and shared assets; dated feature announcements. |
| S12 | https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References | Saved/named image references, iterative consistency and image-to-video handoff. |
| S13 | https://help.runwayml.com/hc/en-us/articles/51683104370451-Creating-with-Edit-Studio | Frame-range/keyframe-guided video editing interface. |
| S14 | https://support.google.com/gemini/answer/16047321?hl=en | Canvas editing, code/preview/logs and output transformations. |
| S15 | https://www.perplexity.ai/help-center/en/articles/10352903-what-is-pro-search | Research-first discovery and source-grounded answers. |

Sources support the concise patterns above. The detailed Hoola specifications below are our synthesis, not claims that every competitor implements every row.

## What to combine

| Product | Adopted interaction principle | Hoola adaptation |
|---|---|---|
| ChatGPT | One chat entry point, contextual projects, multimodal attachments, research with evidence | Keep sessions, improve composer discoverability and make output types visible in chat. |
| Claude | Durable editable outputs beside an ongoing conversation | Use Hoola's existing artifact, panel, version and build APIs; improve full-size editor layout. |
| OpenArt | Dedicated controls when creating media, with reusable assets across workflows | Add a media workspace after capability discovery, not an enormous default composer. |
| Runway | References, iteration and deliberate motion/shot controls | Add storyboard, references and per-shot action surfaces where Hoola's video backend supports them. |
| Gemini | Preview/code context with conversational changes | Preserve Hoola's existing preview/revise/version/error flow and improve its usability. |
| Perplexity | Evidence is part of the answer | Expand actual Gyaan source snippets and links, never fabricate URLs or source counts. |

Do not copy competing logos, trade dress or exact screen composition. The combination is a workflow, not a page containing six products' navigation trees.

## Existing Hoola contract map

- v2.html / v2.css / v2.js: default web shell; index.html / app.css / app.js: legacy fallback.
- md.js: escaped Markdown, tables, code and streaming block renderer.
- stream.js: authenticated fetch/SSE and word pacing; backend livereply.py: transient text/status snapshots.
- chatlist.js + projects.js: chats, sections, drag/drop, project instructions/notes/files.
- panel.js + panel.py: images/audio/video/PDF/text/Office previews, artifact versions and share approvals.
- build.js: website/app stages, looks, preview, screenshots, checks and Android output from existing services.
- console/service.py: login, profile, pending approvals and today views; main.py mounts these routes.
- Existing events include photo_made, pc_file, motion, video_job, artifact, site_board, app_board, app_android, gyaan_sources, goal and approval families.
- Existing business modules have broad backend coverage, but many web cards are generic summaries, not full specialist editors.

## Independent web information architecture

1. Sidebar: New chat, Search, Sessions, Creations, Tools, Activity, Account. Sessions contain chats and project context. Do not confuse web sessions with a voice call's transport session.
2. Conversation: greeting, compact capability suggestions, threaded text, live execution, typed results, citations and follow-up edits. Keep the composer usable during long work.
3. Companion workspace: one active right column, resizable on desktop, full-screen option; tabs for outputs rather than opening a new browser tab by default.
4. Media workspace: prompt + references + supported options + job queue + results grid; an advanced surface entered from chat or a creation.
5. Creations: searchable/filterable image/video/audio/document/app/site results linked to the originating chat and version.
6. Activity: queued/running/waiting/completed/failed/stopped jobs; navigate to originating session. A busy animation is never a substitute for persisted job state.

Suggested navigation labels are product proposals; retain existing familiar Hinglish labels during incremental migration and add language choice later.

## Design system: preserve Hoola

| Token | Current identity / rule |
|---|---|
| Background | #0B0A1A / #120E2A |
| Surfaces | #17122F, translucent white 6–12%, restrained backdrop blur |
| Text | #F4F2FF primary; #B9B3DA secondary; #9C96C2 tertiary |
| Accents | #FFB15C saffron, #7C5CFF violet, #C055F5 magenta |
| Primary action | Existing peach → orange → magenta gradient |
| Status | #34D399 success, #F87171 failure; text/icon in addition to color |
| Typography | Sora headings, Manrope body; system fallback, real Hindi/Marathi wrapping |
| Shape | Existing rounded cards, 12–28 px according to scale; pills for compact metadata |
| Desktop density | 292 px sidebar, 72 px collapsed; readable central thread; wider workspace for actual editing |
| Small screens | <=1100 drawer/overlay; <=820 bottom-sheet workspace and compact navigation; no horizontal page overflow |

Typography hierarchy proposal: 15–16 px body, 13–14 px metadata, 22–28 px page titles, 32–44 px greeting. User content can grow independently of navigation. Code and data tables scroll within their container.

## Complete workflow acceptance inventory

Status: E = present in baseline code, P = present but partial/inconsistent, N = new work/dependency. None of these labels claims production verification.

| ID | Requirement | Baseline | Acceptance condition |
|---|---|---|---|
| C01 | Google/ID login | E | Same account resolves correctly; useful errors; logout clears sensitive state. |
| C02 | Desktop independent navigation | P | Sidebar collapse and drawer actually work. |
| C03 | New chat and deep links | E | Reload/back/open link restores intended conversation. |
| C04 | Global chat search | E | Source chat and message jump; stale queries cannot repaint. |
| C05 | In-chat search | E | Result counts and next/previous handle old pages. |
| C06 | Sessions and nested chat list | E | Create/rename/move/delete preserve chats correctly. |
| C07 | Project instructions/notes | E | Scoped to project; explicit saved/error state. |
| C08 | Project files | E | Upload, extract, remove; clear retention limits. |
| C09 | Context/source picker | N | Explicit uploaded/project/connector references; do not imply unsupported source access. |
| C10 | Tool picker | P | Capability-aware search grouped by user outcome; unavailable tools explain why. |
| C11 | Model/quality selection | N | Only configured supported options, cost and limits visible. |
| C12 | Autosized composer | E | No clipped placeholder or disabled button mismatch. |
| C13 | Per-chat drafts | E | Pending debounce cannot write another chat's text. |
| C14 | Attach/drop/paste | E | Per-file upload state, limits, cancel and retry; no cross-chat leakage. |
| C15 | Dictation | P | Final transcript appends without exception, permission failure clear. |
| C16 | Live voice | P | Mic, mute, hangup, output interruption; reconnect/resume needs web-specific work. |
| C17 | Streaming Markdown | E | No flashing raw syntax; long code/table content remains contained. |
| C18 | Stop execution | E | Stops actual job; no false “done.” |
| C19 | Queue/steer/takeback | E | Receipt matches server state; submitted request remains tied to source chat. |
| C20 | Edit/retry/branches | E | Prior output versions preserved; external actions never replayed silently. |
| C21 | Copy/quote/feedback/export | E | Accurate content, accessible actions, download success/failure. |
| C22 | Keyboard shortcuts | P | One handler, no collisions, modal focus restoration. |
| R01 | Image result in chat | P | Actual protected image bytes render; label, open and download. |
| R02 | Video/animation playback in chat | P | Real output controls, no automatic playback, expired link state. |
| R03 | Audio result in chat | P | Player, duration when known, download. |
| R04 | Documents as result cards | P | Filename/type/size, open existing preview, download. |
| R05 | Inline PDF preview | P | Optional lazy preview, readable workspace, conversion failure recovery. |
| R06 | Spreadsheet inspection | P | Existing PDF/text preview exposed; real editable grid requires work. |
| R07 | Slides inspection | P | Existing preview exposed; page navigation/editor requires work. |
| R08 | Artifact/code preview | E | Open in workspace; preview/code/version/error/revise intact. |
| R09 | In-chat interactive app | N | Restricted bridge, resource limits and explicit supported actions. |
| R10 | Source evidence cards | P | Actual snippets, page references, valid source/file links. |
| R11 | Mixed text + multiple outputs | P | Results remain in creation order with stable IDs. |
| R12 | Update result in place | E | Final card replaces prior state without duplicates or stale requests. |
| R13 | Version lineage | P | Parent/child relations persist for every edit; not merely display ordering. |
| R14 | Reuse output as input | N | File/asset ID travels to new tool, no re-upload requirement. |
| R15 | Preview loading/error/expiry | P | Status survives auth failures and missing files honestly. |
| R16 | Result sharing | E | Existing server approval before public link; never bypass phone gates. |
| W01 | Companion workspace sizing | P | Appropriate width, scroll containment, desktop/tablet/browser-phone checks. |
| W02 | Selected tabs and zoom | P | Styling matches actual DOM attributes; zoom is a modal. |
| W03 | Multi-output tabs | E | Tab close cleans media/blobs; capped number of open outputs. |
| W04 | Split/fullscreen/resize | N | Keyboard-operable resize, minimum readable widths, persisted preference. |
| W05 | Direct document editing | N | Save/revert/conflict handling through dedicated backend contracts. |
| W06 | Selection-to-edit | P | Code selection context exists; granular document/image selection needs work. |
| W07 | Real version comparison | N | Side-by-side data for selected versions, restore as a new version. |
| W08 | Artifact state and ask bridge | E | Origin/source validated, isolated frame, no token in frame. |
| M01 | Image generation controls | P | Supported aspect/quality/reference fields connected to actual tool. |
| M02 | Image editing and variations | P | Existing photo_banao input used; reference lineage exposed. |
| M03 | Mask/inpaint/outpaint | N | Real mask model API, mask tools, preview and reproducibility. |
| M04 | Crop/resize/background tools | P | Check existing service actions before offering an editor. |
| M05 | Brand kits | P | Existing brand service mapped to web UI; logo/colors/fonts/rules per project. |
| M06 | Reusable character/product assets | P | Existing studio character data; cross-tool persistence needs validation. |
| M07 | Batch comparison grid | N | Multiple outputs, consistent job IDs and per-output actions. |
| M08 | Image-to-video handoff | N | Actual reference transfer into supported video job. |
| M09 | Storyboard/shot list | P | Existing studio structures surfaced on web. |
| M10 | Per-shot generation/redo | P | Live states, approvals and selected takes connected. |
| M11 | Keyframes/camera/motion | N | Show only options accepted by selected backend provider. |
| M12 | Timeline editor | N | Trim/split/sequence/audio alignment, export pipeline and undo. |
| M13 | Voiceover/music/subtitles | P | Existing studio/video services; integrated controls still needed. |
| M14 | Audio waveform and scrubbing | N | Real decoded audio and position; not decorative progress. |
| M15 | Prompt/history/settings | P | Persist exact inputs, provider/model, resolution, cost and references. |
| M16 | Credits/cost estimate | P | Existing usage/approval concepts; estimate vs actual distinguished. |
| Q01 | Research plan/source scope | P | Existing goals/search/Gyaan; explicit research workflow needs web and backend mapping. |
| Q02 | Research progress and stop | E | Real tool activity; user can steer and stop. |
| Q03 | Cited report in chat | P | Numbered evidence and export; report reader needs refinement. |
| Q04 | Sources used/limitations | P | Distinguish visited/retrieved/cited; show unresolved questions. |
| Q05 | Connector search and actions | P | Respect real auth/capability state. |
| Q06 | Interactive connector interfaces | N | Registered sandbox/bridge contract; no arbitrary HTML from tools. |
| Q07 | Web/agent activity view | P | Existing cards/kaamwatch; full web task inbox needed. |
| Q08 | Background task recovery | P | Persisted backend job lifecycle, never infer from spinner alone. |
| Q09 | Approvals and budgets | E | Phone biometric gates remain; no web bypass. |
| Q10 | Hoola business tools | P | Every module has an explicit result/approval renderer or honest generic fallback. |
| A01 | Output library | E | Existing Banaya hua filters/search; expired item recovery needed. |
| A02 | Folders/tags/favorites | N | Persistent asset metadata and provenance. |
| A03 | Media resource cleanup | P | Abort stale loads, revoke object URLs, pause hidden playback. |
| A04 | Accessibility | P | Focus states exist; keyboard modal management, labels and contrast need measured checks. |
| A05 | Reduced motion | E | Disable nonessential transitions and ambient motion. |
| A06 | Localization | P | Hinglish exists; web language switch and full Hindi/Marathi labels needed. |
| A07 | Persistent web preferences | N | Sidebar/workspace density/language scoped safely per user. |
| A08 | Telemetry and error boundaries | P | Measure first response, result readiness, preview failures and UI exceptions. |

## Result contracts

Use existing event names; do not modify mobile-facing payloads in this phase. Web adapters map them into a common view: kind, stable result ID, status, title, origin conversation, version, safe preview, supported actions and any exact cost/provenance available. Never invent missing metadata.

Queued → running → needs input → completed/failed/stopped are distinct. A failed generation is not an empty image. Partial output can remain usable with its limitation stated. Generic unknown events remain visible without exposing tokens, signatures or raw payloads. External actions keep their existing approvals.

File access uses authenticated GET into local blob URLs. Generated pages remain sandboxed and credential-free. Sharing remains a deliberate server-approved action. PNG/WebP/MP4/audio previews are genuine output bytes. PDF/Office opens existing workspace preview; do not generate Office PDFs for every history replay. A future inline interactive artifact must keep the existing storage/ask bridge available, not create a non-working duplicate iframe.

## Motion and micro-interaction specification (Hoola proposal)

These are implementation targets, not reverse-engineered competitor timings.

- 120–160 ms button hover/press; 180–240 ms panel/preview reveal; opacity/transform only when possible.
- Maintain text/container geometry while streaming; preserve scroll position when reading older content.
- Show honest indeterminate state until a real percentage exists; show step labels and elapsed time, never a made-up ETA.
- Keep completed output static; no permanent shimmering, spinning or simulated waveform on idle results.
- Ambient aurora stays subdued; no new autoplay audio/video. Reduced motion disables decorative effects.
- Skeletons have stable dimensions; final media uses object-fit:contain to preserve logos, text and product details.
- One pane opens at a time; closing a panel restores focus and never interrupts the actual background job.
- Browser speech must distinguish input dictation, live conversation and generated audio playback.

## Delivery sequence

1. Foundation: web-only source boundary, console defects, typed in-chat media/document result cards, real source details, correct studio/panel DOM styling. Browser fixtures and mobile-file hash verification.
2. Workspace: resize/fullscreen, deterministic focus, result actions, context picker, tool capability discovery and creation library improvements.
3. Creative workflow: image/video/audio controls, reference reuse, variants, brand/character asset UI. Validate provider contracts before implementing expensive controls.
4. Documents/research: evidence reader, editable document/grid/deck surfaces, version comparison, report exports; requires backend additions isolated behind web endpoints where needed.
5. Advanced orchestration: storyboard/timeline, interactive apps/connectors, task recovery/observability and organization controls.

Do not promise a timeline until required providers, persistence and deployment constraints are verified. Each phase has a bounded, testable output; not a fake “all tools work” screen.

## Phase 1 implementation and verification record

Web-only local branch: web/console-research-foundation. Source changes: v2.html, v2.js, v2.css and new results.js. Preserved server version and Android pubspec. Results use existing APIs, not a second backend.

Implemented: image/video/audio result players, file cards with authenticated download and workspace expansion, artifact launch cards, expanded Gyaan citations, native progress-summary handling, dictation mutation fix, sidebar collapse styles, selected studio tabs and DOM-compatible workspace/media layouts.

Still pending: genuine in-chat interactive artifact bridge, creative mode controls, timeline, editable Office grid/deck/document surface, persisted asset lineage, resizing/fullscreen, full browser voice resume, comprehensive accessibility and live account acceptance. Do not describe these as shipped.

Local browser download failed (truncated network response); rendered browser validation is not yet complete. Backend test dependencies are absent in this environment. Node syntax checks and dependency-free functional contract tests are used for the first code pass; the release gate still requires browser and real-server checks.

Verified in this local pass:

- `node --test server/tests/web/results.test.cjs`: 10/10 passing. These execute real renderer/dictation code against a small DOM double; they do not validate CSS layout.
- `node --check` for changed JavaScript: passing.
- `git diff --check`: passing.
- 692 tracked mobile, Android asset/tool, desktop and frozen PC files compared byte-for-byte with HEAD: zero differences.
- Existing numeric application cache-version assertions remain compatible; changed web assets have independent cache parameters.

Before release: run existing console backend suites in a dependency-complete environment; render authenticated desktop/tablet/browser-phone fixtures; test multiple output types, keyboard/focus and real downloads; inspect browser errors; validate signed/expired assets; verify mobile paths remain unchanged; then review deployment separately.
