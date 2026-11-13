

## v0.799.0 DESK ROOM (built as 0.796; their 0.796-0.798 took the numbers, all kept) - a console desk for every live AI employee (owner: "LOT OF EMPLOYEE HAS BEEN DEVELOPED IN APP BUT IT IS NOT AVAILABLE IN WEB CONSOLE CHECK THIS FIRST THEN CATEGORY WISE DEVELOP AND DESIGN IT IN CONSOLE")

THE AUDIT (catalog `employee/hire.py` x console `employees.js` DESKS x `v2.html` views): 84 employees, 63 live. Every live one
in Games (10), Education (6), Enterprise (10), Business (seo / social / leads), cad, architect and film already had a console
desk. 31 did not, and their "Open desk" tap went to `<key>desk`, a view that does not exist - nothing happened:
Finance & Banking (paisa_sahayak, vitt_sahayak, risk_desk), Retail & E-commerce (dukaan_desk, retail_growth, retail_trust),
Health Insurance (bima_desk, bima_assist, bima_risk), Voice (kaan) and Construction & Real Estate (21 const_* seats). They were
never desks on the PHONE either: they are chat tools, and `employees_screen.dart` `_deskFor` falls back to the SEO desk for
them (not changed in this release - phone code compiles only on CI).

WHAT WAS BUILT
- `server/app/employee/deskroom.py`: `DEPTS` (four departments, their lanes; Construction in five lanes), `tools_of(key)` (the
  employee's own tool + its read-only `<key>_dekho` when it exists), `spec(tool)` = the tool's schema + its FULL description from
  its own module (the registry copy is cut to 1,200 chars for the model and lost later actions' inputs) read into one form per
  action: the fields that action names, choices from `a|b|c`, hints from `( )`, `[{a, b}]` = a row table with those columns,
  `[x]` = one per line, `{k: v}` = key: value lines, `file_id` = a file picker, and what the action gives back (`->`). 423
  actions, 409 read exactly; the 14 whose inputs the tool never lists say so and show every field folded. `run()` = the SAME
  `dispatch` the chat uses, `Ctx(actor="owner")`, the conversation = her Hoola updates chat (cards land there); hired only,
  paused refused, never another employee's tool, unknown fields dropped, a 9+ digit account / card number cut to its last
  four, 90 s cap, output scrubbed. Routes: GET /api/deskroom, GET /api/deskroom/{dept}, POST /api/deskroom/{key}/run.
- `server/app/static/console/deptdesk.js` (view `deptdesk`): crumb, department switcher, hero (serif title, line, a line drawing
  per department that traces itself once, employees / working / actions counts), employee rail by lane with status dots, the
  employee panel (pitch, Working / Paused / Not hired; not hired = what it does / never / needs + Hire on the careful trust
  level), Work / Records tabs, action chips with what each gives, Find an action when there are many, the form (number / text
  / choice / Default-Yes-No / row table with + Add row and Paste from Excel / lists / file), Run (Ctrl+Enter), and the result as
  tiles, tables, flag lists, letters in the reading serif and a notes callout, with Copy. Records opens today's desk (`day`) or
  the first list by itself. Ask in chat puts a line in the chat box, never sends it.
- `employees.js`: the 30 keys -> 'deptdesk' (opened on that employee), kaan -> 'flow' (Hoola Flow is Kaan's console page).
- `v2.css` block "v0.796 DESK ROOM": tokens only, light / dark / system, scale 12.5-32, weights <= 600, entrances once and
  BACKWARDS (the form and result animate only when they first appear, never on a repaint), only the running dot loops.
- Tests `test_v0799_desk_room.py` (8): every live employee opens a real view (the audit, held), the four departments = every
  live seat, forms from the full description (>95% exact), routes + hire gate + real runs (loan EMI 16,607.15, a store GRN read
  back as stock, paused refused, account masked), dispatch-as-owner pin, console wiring, crisp CSS, a real-browser walk in light
  1280 and dark 390. Pins moved in test_v0453 / test_v0456 (openView now passes the key for deptdesk too).

NOT VERIFIED: not opened on her live console yet; actions that make a card were not walked to the card; the phone still opens
the SEO desk for these 31 (a phone desk is the next step if she wants it).

## v0.741.0 MORE PROVIDERS — Gemini / Groq / Mistral / NVIDIA / Z.ai in the model dropdown (10 Nov 2026; owner: "CHECK ALL MORE FREE POWERFUL OPTION" -> "GO")

- `app/agent/providers.py`: one table of OpenAI-compatible providers. Each entry has a label, a base URL and the settings field that holds its key (gemini_chat_api_key / groq_api_key / mistral_api_key / nvidia_api_key / zai_api_key / openrouter_api_key), and keys live ONLY in .env. A model in `chat_models` is either a plain slug (the GLM endpoint, i.e. OpenRouter) or `<provider>:<model>`; only known prefixes count, so OpenRouter's `:free` is never mistaken for one. The Gemini chat key is its own setting, so chat turns never spend the prepaid voice GEMINI_API_KEY.
- `modelchoice.allowed()` lists a model only when its provider has a key. The dropdown is offered on any OpenAI-style chat (GLM_API_KEY), not only OpenRouter, and not when the chat runs on Claude. Entries carry `provider`; free / paid is None for another provider (its plan is not visible to Hoola), and the menu shows the provider's name instead.
- `llm._target("glm")`: a prefixed pick goes to that provider's endpoint with its own key and a plain request, without OpenRouter's reasoning field or NVIDIA's GLM-only fields. `is_openrouter` / `is_nvidia` follow the turn's model, not GLM_BASE_URL.
- Model profile: a model from another provider is described from the same model in OpenRouter's public catalogue (`modelprofile.catalogue()` + `match()`, matched by normalised name, preferring the provider's own vendor; kept 24 h). One nobody can describe is text only: `glm_reads_images` returns False for it, so it is never sent pictures. It stays pickable, and its own errors teach the rest.
- Tests: `test_v0741_more_providers.py` has 7 tests, on a real catalogue sample fixture. Covered: the prefix split, listing by key, catalogue descriptions, a Groq turn going to Groq with its key and no extra fields, the Gemini chat key never being the voice key, no pictures to an undescribed model, and the OpenRouter default unchanged. `test_v0740` was updated: "not offered" is now the Claude case.
- NOT VERIFIED LIVE: no key for these providers on the server yet. Each provider's free limits and data terms are its own; check them before use.

## v0.740.0 MODEL DROPDOWN — each user picks the chat model in the console (10 Nov 2026; owner: "IN WEB CONSOLE LETS USER CHOOSE THE MODEL VIA DROPDOWN")

- Console: a model chip in the composer row (`#modelBtn`, beside the name label) opens a HoolaMenu titled "Model for your chats". Each model shows its name, Free or Paid, whether it reads pictures, and which is the default; her current model is ticked. A model with no tools is greyed out with the reason. After a pick, a toast says her next message runs on it. On narrow composers the chip shrinks, and below 360 px only the chevron shows (container queries).
- The list is the OWNER's: `GLM_MODEL` + `chat_models`. The default list is nvidia/nemotron-3.5-super-vl:free, thinkingmachines/inkling-2-small:free and google/gemma-4-31b-it:free. A user can never pick a model outside it (cost + safety). Each entry is described from its own OpenRouter list (v0.739 `modelprofile.get(model)`, read for every listed model at start: `modelchoice.warm`).
- `app/modelchoice.py`: per-user choice in `data/model_choice/<tenant>.json` (or `model_choice_dir`); the default is stored as no choice. A model the owner removes falls back to the default; a pick outside the list or without tools is refused (400).
- `santosh._run_turn` sets `llm.MODEL_NOW` from her choice, so the WHOLE turn follows it: `llm._target` sends that model, and the model profile (now per model, `current_model()`) decides picture / PDF routing, the reasoning field and the window for it.
- GET /api/model/choices, PUT /api/model/choice. The dropdown is only offered when the chat runs on OpenRouter; otherwise it says why. Switch `chat_model_choice` (default on; conftest pins it off).
- Tests: `test_v0740_model_dropdown.py` has 7 tests: the owner's list described per model, per-user pick + refusals, the removed-model fallback, her turn running on her pick with that model's own abilities, routes + key + "why not offered", the console wiring, and a real-browser walk at 1440 / 700 / 420 px (inside the box, tick, greyed no-tools model, a pick changes the chip). The browser test needs HOOLA_CHROMIUM in this sandbox.
- NOT VERIFIED LIVE: her OpenRouter key limit; free models' daily caps apply.

## v0.739.0 MODEL PROFILE — a new model needs no code change (10 Nov 2026; owner: "WHY EVERY NEW MODEL NEED UPDATE IN CODE EVERY TIME --- WHY IT IS NOT GENERALIZE" -> "GO")

The root cause: each model's abilities had been written into the code by hand, per provider. Examples: pictures were hard-coded off for GLM in v0.735; OpenRouter needed a reasoning field (v0.699 / v0.700); NVIDIA sent fields only GLM understands (v0.697). OpenRouter publishes every model's facts at GET {base}/models/{model}/endpoints: input kinds, accepted parameters, context length and price. Nothing read it until now.
- `app/agent/modelprofile.py`: reads that list for the configured GLM_MODEL. It runs at start (`refresh_in_background` in the lifespan, off the event loop), again when the profile is more than a day old, or on POST /api/model/profile/refresh. The profile is kept in memory and on disk (`data/modelprofile/`, or `model_profile_dir`), so a restart without a network still knows the model. `reads(kind)` / `supports(param)` / `context()` return None when the profile is unknown, and callers then keep their old settings.
- Wired in:
  - `llm.glm_reads_images`: the list decides; GLM_IMAGES=false still turns pictures off.
  - `llm.pdf_parts`: a scanned PDF is turned into page pictures only for a model that reads pictures. Otherwise the little text it has is sent, and the text says so plainly.
  - `llm._target` (OpenRouter): no reasoning field for a model that takes none.
  - `llm.room`: no reasoning room for such a model.
  - `context.limit("glm")`: the model's own window when it is smaller than the setting.
  - `_post_with_retry`: a model's own "reasoning is mandatory" 400 is retried with the field and LEARNED (saved for that model). A model that refuses the field is learned too.
  - A model without tools is logged as an ERROR at start.
  - GET /api/model/profile; healthz `chat_model_reads`; `python -m app.agent.modelprofile` prints what the model can do.
- Switch `model_profile` (default on; conftest pins it off for the old suites). Claude keeps its own path.
- Tests: `test_v0739_model_profile.py` has 10 tests, on fixtures that are OpenRouter's real answers for z-ai/glm-5.3-flash and deepseek/deepseek-chat-v3.1 (`tests/fixtures/`). Covered: a model swap with no code change, no reasoning field for a plain model, the window, a read failure keeping the old behaviour, the disk copy after a restart, learning "mandatory", a scanned PDF for a text-only model, the switch off, the endpoint and healthz.
- NOT VERIFIED LIVE: her OpenRouter key limit is reached. Non-OpenRouter endpoints (NVIDIA, Z.ai, OmniRoute) have no such list and keep the old settings.

## v0.738.0 PARITY 1 + 9a + 12 — every message to the model, files by code, edit / ask again on the phone (10 Nov 2026; owner: "TILL I TOPUP -- CONTINUE OUR THIS WORK")

The owner's parity table was out of date. Gaps 4, 5 and 10 were already done in v0.733, and gap 3's pictures / PDFs moved to GLM in v0.735. The small gaps left were 1, 9a and 12. Each change has its own switch: on by default, set to the old value in conftest for the old suites.
- GAP 1, every message reaches the model (`chat_every_message`): the research-plan gate no longer answers in the model's place. Research runs inside the turn since v0.732. Stop words still stop the work BEFORE the turn waits for the lock (`kaamstop.cancel`), and the turn still runs: the model gets a "[Done by the system before this turn ...]" note and writes the one-line reply itself. The OTP / CAPTCHA hand-over stays before the model, because a secret must never reach it. Goal reopen only changes state, so it stays.
- GAP 9a, one way to make a file (`chat_files_by_code`): `pylab` already sent its files back into the chat, but it dropped .docx / .pptx / .pdf. It now keeps them (`pylab.service.DOC_TYPES`, `_types()`). The sandbox imports python-docx / python-pptx / reportlab; tested for real, all three written and stored. The core prompt's FILES line says Word / Excel / PDF / PowerPoint / CSV / charts are written with pylab, a change means the same code run again with only that change, and doc_studio is only for a designed, branded report.
- GAP 12, edit / branch on the phone: the server (`chats.edit`, `/retry`, versions) and the web console already had it. The phone long-press menu gains "Edit message" on her own messages (POST /edit, then the chat is read again; the old version stays on the server) and "Ask again" on the newest reply (POST /retry). Not built on the phone: the arrows to switch back to an older version (the console has them).
- Tests: `test_v0738_every_message.py` has 7 tests. Two stale pins in `test_v0649_sach_mein_roko.py` were healed: a source window of 400 -> 1200 characters, and "Kirana site: band" -> "stopped", red since the English waves.
- NOT VERIFIED: the phone code compiles only on CI. Nothing in this version has run live yet (her OpenRouter key limit is reached).

## v0.737.0 KEY LIMIT SAID — the real cause of the photo-test failure (10 Nov 2026; owner: "READ")

vps-ops errors (04:27) showed it: `GLM (OpenRouter) error 403: Key limit exceeded (total limit) ... $10`. Her OpenRouter key has a $10 spending limit and it is used up. That made GLM fail twice and paused it, and the pause failed her photo turn (ref 228d25). Anthropic is also out of credit, so nothing could answer.
- `santosh._friendly_error`: a "key limit exceeded", "insufficient credits" or 402 from the GLM / OpenRouter path now gives the owner a plain line telling her to raise the key's limit at openrouter.ai > Settings > Keys or add credit. Everyone else gets the outage line.
- The OWNER must raise the limit herself; no code fixes it.
- Seen in the same log: the coder observer (background session memory) also spends GLM calls on every chat.

## v0.736.0 GLM PAUSE FIX — a paused GLM no longer fails every chat (10 Nov 2026; owner's photo test: "WHOS IMAGE ID THIS" -> "Sorry, something went wrong just now (ref 228d25)")

Live healthz read `chat_brain: claude` on 0.735.0, which is what the GLM safety switch shows during a pause (2 failures -> 10 minutes). With `chat_one_model` the chat stays on GLM during a pause, but `llm.openai_create` / `openai_stream` still refused every call ("glm paused after repeated failures - another brain answers"). That error has no status code and no "busy" word, so she saw "something went wrong". At the same time the SDK door moved every background call, the picture reading in `media.understand` included, to Claude, whose credit is out.
- `llm.pause_refuses`: a pause refuses a call only when another model may take it. With one model it is ignored and GLM is asked anyway. Switch `glm_pause_one_model` (default False); true brings the old refusal back.
- `glmdoor.active`: during a pause the door stands aside only when the Claude fallback is allowed (`claude_all_glm_fallback`).
- `santosh._friendly_error`: a pause, an empty answer or "no answer" now gives "busy or unreachable, try again".
- `llm.describe` (healthz): names the chat's real model, plus "(paused)".
- NOT KNOWN: what made GLM fail twice in the first place, before the pause. Run vps-ops errors and look for "error ref 228d25"; the photo test after deploy shows whether OpenRouter GLM reads the picture.
- Photo path for reference: a chat photo is NOT sent to the model as a picture. The turn gets a note and calls `file_read`, which does OCR and then `media.understand` (`_claude_see` through the SDK door, so GLM with CLAUDE_ALL_GLM; Gemini as a fallback).

## v0.735.0 ALL GLM — every Claude-only job moved onto GLM-5.3-Flash, one switch each (10 Nov 2026; owner: "WE WILL TEST ONE BY ONE MOVE EVERY THINH ON GLM 5.3 FLASH")

Four places still went to Claude with GLM as the chat brain; now each stays on GLM behind its own switch. Each switch is on by default, set in conftest to the old value for the old suites, and `.env` brings the old routing back.
- PICTURES (`glm_images`, default True): `llm.glm_reads_images` now says yes on OpenRouter as well as NVIDIA. OpenRouter's model list gives z-ai/glm-5.3-flash text + image + video input. `llm.choose` keeps a picture turn on GLM and `_image_parts` sends it as an image_url.
- PDFS (`glm_pdf`, default True): `llm.pdf_parts` turns a PDF document block into its own text with pypdf, capped by `glm_pdf_max_chars` (60000). If the PDF has fewer than 20 words a page, it is a scan: its first `glm_pdf_max_pages` (8) pages are drawn with pypdfium2 and sent as JPEG pictures. A broken PDF gives one honest line and never raises. `to_openai` and `glmdoor.has_media` both use it, so the SDK door keeps PDFs on GLM too.
- WEBSITE ARCHITECT (`architect_opus`, default now False): the plan call is no longer forced onto Opus with `glmdoor.CLAUDE_ONLY`, so it rides the GLM door like every other call.
- NO CLAUDE FALLBACK (`claude_all_glm_fallback`, default now False): when GLM fails at the SDK door, the GLM error is raised and the turn says it is busy, instead of answering on Claude.
- Tests: `test_v0735_all_glm.py` has 10 tests. Each switch is checked both ways, with a real text PDF and a blank (scanned) PDF made by reportlab.
- NOT VERIFIED LIVE: whether GLM-5.3-Flash reads a real photo or scan well, and whether the website plan on GLM is as deep as the one on Opus. The v0.710 root cause was GLM-Flash giving generic plans, so try a website plan first and set `ARCHITECT_OPUS=true` if it comes back as a landing page.

## v0.734.0 TRAPS + LIVE FIXES — after the first live parity card (10 Nov 2026; owner: "FIX TRAPS")

The first live parity card on GLM-5.3-Flash (run on v0.732.0, 02:32-03:10 UTC): SCORE 88.1/100, 35/60 passed; answered 49/60, followed 27/27, right tool 37/58, no invented done 60/60, nothing stapled 60/60, one brain 50/56; first word median 5.0 s, conversation median 16 s, Rs 328.7 for the card; by category followup 93.3, one_tool 100, long 86.5, make 71.7, memory 90, trap 78, lang 93.3.
- TRAPS (core prompt, `agent/core_prompt.py`): an ask pointing at something nobody named gets ONE short question naming what is missing, before any tool; an impossible ask (the past, the physical world, out of every tool's reach) is said plainly in the first sentence with the nearest real help, never written as if it happened; reshaping words already in the chat (shorter, a table, bullets, an example, another tone / language, a caption) is plain writing - no pylab / kalam; code only for exact numbers or a file she asked for. Core stays < 11k chars.
- REQUEST DUMP LIVE FIX (`app/reqdump.py`): the sweep (first write after every restart, then every 200) ran `delete ... where created_at < aware_now` with the session's evaluator against a row loaded naive from SQLite -> "can't compare offset-naive and offset-aware datetimes" -> the write failed and STATS["written"] never moved, so NO request was ever dumped on her server; now naive cutoff + synchronize_session=False; the regression test fails on the old code.
- CARD FAIRNESS: rubric v2 (`artifact` / `graphic` / `make_document` count as making, `web_fetch` as web / research, a `kaam_plan` written first is judged by the next tool unless a plan WAS the expectation) + set v2 (the past-train trap no longer counts "cannot be booked" as a claim).
- FOUND LIVE (vps-ops errors, 03:44 / 03:48): the Anthropic credit is OUT ("Your credit balance is too low") - every tool that calls Claude (doc review, picture reading, site / app model) fails, the most likely cause of the 11 unanswered make / memory conversations (the card's own parity.log was not read); her Google sign-in is still dead for both accounts.
- NOT VERIFIED: the traps fixed only in the prompt - the next live card shows whether GLM follows them.

## v0.733.0 CLAUDE PARITY MEDIUM — thinking, the plain loop, one memory (10 Nov 2026; owner: "GO MEDIUM" on the parity table)

Three parallel worktree agents, merged; each behind its own switch (default ON, pinned OFF in conftest for the old suites).
- Gap 4 THINKING (`chat_thinking_adaptive`): `santosh.think_level` = low for a greeting / thanks / ok (English + her Hinglish forms), high for a hard ask / long job / big ask, medium otherwise; `llm.REASONING_NOW` sends OpenRouter `{"reasoning":{"effort":level,"exclude":false}}` (NVIDIA low/high, Z.ai thinking on at medium+), `room()` adds 2k / 4k / 8k so the answer keeps its budget; reasoning deltas go only to `on_think` (the folded Soch card) - never saved, never in the next request; Claude turns get the level as effort; voice brain unchanged. Switch off = the v0.700 body byte-identical.
- Gap 5 PLAIN LOOP (`chat_plain_loop`): measured every post-answer step (held hard review, pakka self-check, done_note, fake_done, goal + promise nudges, gyaan ground, after_turn draft check); now the answer ends the turn. `_plain_check` (no model call) keeps only a false action claim with no tool behind it, a reminder promised but not set, and 'done' with every tool failed - fired BEFORE she sees the answer: the draft is kept for the model only, the streamed words wiped with the existing `delta_reset` (`Live.retract`), the fix written into the same reply; still false after one try = the honest line inside that reply. Dropped: generic self-check, the reviewer on ordinary hard answers (they stream now), after_turn. Kept: research dossier fix round, goal nudge while a goal is open, the promise nudge. Plain answer = 1 model call, 3-tool turn 3 -> 2 calls.
- Gap 10 ONE MEMORY (`chat_one_memory`, Phase 7): memory text on her newest message 10,565 / 10,683 -> 595 / 585 chars (the 8,952-char described skills list was most of it): one 'SINCE YOUR LAST REPLY' note (<= 1,800: job state, card news, a cut call, a yaad_khojo hint) + skill names (<= 600); the diary, recent words, facts by meaning, recalled chats and the coder primer are fetched with yaad_khojo, whose `memory.search_all` gained a `diary` store (30 days, fenced) and chat titles. Memory summary (<= 1,500) stays in the per-chat block; memory writing and voice turns unchanged.
- VERIFIED: 29 changed / affected suites on this tree and on v0.732.0 - the same 7 reds on both, none new; `test_v0732_parity_all.py` runs all nine switches together (one model call for a plain answer).
- NOT VERIFIED: no live GLM run - whether OpenRouter streams GLM reasoning with exclude:false, the cost / latency of medium / high, whether GLM calls yaad_khojo instead of saying it does not remember, the in-place replace on a real phone / browser.

## v0.732.0 CLAUDE PARITY 0-6 — Hoola's chat handled like Claude chat (9 Nov 2026; owner: "WE WILL KEEP GLM 5.3 FLASH AS PRIMARY FOR ALL FOR NOW --- PHASE 0 + 1" then "GO VIA THIS --- LARGE ISSUE FIRST")

Built from `docs/CLAUDE_PARITY_PLAN.md` by six parallel agents + the join; every phase behind its own switch (default ON, pinned OFF in `tests/conftest.py` for the old suites).
- Phase 0 MEASURE: `quality/parity_convs.py` (60 conversations / 97 turns: follow-ups, one-tool, long, make + 2 edits, memory, traps, Hinglish / Marathi) + `quality/paritycard.py` (six scores per conversation + time to first word, total time, rupees, brains used; `--check` free with 20 planted transcripts; `--live`, `--judge`), GET /api/quality/parity, vps-ops `parity_card_check` / `parity_card`. `app/reqdump.py` = what the model received per step (masked, 20 turns / chat, 14-day sweep, `request_dump`), GET /api/conversations/{id}/request[/{turn}].
- Phase 1 ONE MODEL (`chat_one_model`): `llm.chat_brain` keeps a paused GLM as the chat's brain, `_think` asks the SAME model again (`chat_model_retries` 2, `chat_model_retry_s` 3) on busy / timeout / 5xx, never another brain; `model_for` no Haiku / Sonnet / Opus split; the plain "busy, try again" line after. Exception: a PDF / picture GLM cannot read goes to Claude.
- Phase 2 SMALL PROMPT (`chat_small_prompt`, `agent/core_prompt.py`): measured 52,311 / 62,057 chars -> 9,112 chars, byte-identical turn to turn; core (identity, writing, work, look-ups, safety) + `== THIS CHAT ==` block (date, her name, <=1,500-char memory summary, project, MCP names); per-turn guides ride her newest message; sites / apps / routines / facts / cards fetched (`kaam_status action=cards` added); `agent/cache.py` breakpoints after core + chat; `tools/prompt_measure.py`.
- Phase 3 CLEAN TOOLS (`chat_core_tools`, `agent/core_tools.py`): ~22 core tools in view (median 58 -> 26; tool JSON 48-72k -> 26-39k chars), new `web_fetch` (fast / browser / stealth over the existing readers, which stay reachable by tool_search), English core descriptions with examples, whole-word family admission, head+tail result cuts, clean errors; tool card 176/176.
- Phase 4 WORK IN THE TURN (`chat_work_in_turn`): her chat turn runs deploy_agents crews + research_run inline (crew 260 -> 900 s, tool 300 -> 1080 s, turn 900 -> 1200 s, calls 48 -> 200); the prompt's background sentence swapped; a stopped crew leaves the 8-agent count (leak fixed).
- Phase 5 ANSWER ONLY (`chat_answer_only`): the "(Kaam: ...)" ledger leaves the reply for a `ledger` event drawn in the console's "Worked for" steps; stapled honesty / grounding / HARD_UNSURE notes gone; a false claim gets one self-correction ask, and an honest message only for a real action (send / pay / book / publish / delete) still claimed after it.
- Phase 6 DIRECT ARTIFACTS (`chat_artifact_direct`): tool `artifact` create / update (exact old_str -> new_str, all-or-none) / rewrite, written by the chat model, cleaned like the builder, versions with kind + source, `artifact_draft` live stream into a Writing tab, Undo (POST /api/artifacts/{id}/undo); artifact_make = the studio-polish path. Registry 618 -> 620 (artifact + web_fetch).
- JOIN: the core tool set carries `artifact` (only with the switch on), the small prompt names the page path, `tests/test_v0732_parity_all.py` runs every switch together (<12k prompt, <=30 tools in view, one brain, reply = model text).
- VERIFIED: 101 changed / affected suites run on this tree and on v0.729.0 - every failure new to this tree fixed (stale Hinglish pins, two phase joins).
- NOT VERIFIED: nothing has run against the live GLM - whether GLM-5.3-Flash picks the core tools, writes pages with `artifact`, streams tool arguments, stops choosing background crews, is unproven until the live parity card; no baseline score yet.

## v0.731.0 SAB ENGLISH wave 3 + phone — the model's own working text and the phone app in English (built as 0.730 - their SHILP MANCH took 0.730.0, REBASE PROTOCOL, both kept; 9 Nov 2026; owner: "GO PHONE and GO WAVE 3 -- in parallel")

Nine agents in parallel worktrees, merged and checked against v0.729.0 (`53ab8a366`) by running the same ~60 changed / affected suites on both trees.

- PHONE (Flutter `lib/`, 213 Dart files, ~10,600 strings): every screen's labels, hints, buttons, snackbars, dialogs, tabs, status pills, empty states, errors and the chat lines the app sends for her are English. Code outside string literals was compared old vs new by a Dart string lexer (identical except one intended word-order swap in `hoola_net_screen.dart`); four slips the check caught were fixed. The `app.g()` / `tr()` lookup keys are KEPT as the original text (119 calls in chat / email / today screens were restored after translation) - English comes from `lib/i18n.dart`'s `en` table, so Hindi / Marathi phones keep their language. `lib/ui/pc_screen.dart` frozen and untouched.
- ANDROID (`tool/android/kotlin`, 19 files + manifest + widget layout / strings): notification channels, titles, actions, foreground-service + wake-word lines, toasts / errors back to Flutter, bubble, tile, widget ("Speak" / "Type"), biometric prompt, scroll-limit alerts. Intent actions, extras, MethodChannel names, prefs keys and the payment-alert regex unchanged.
- WAVE 3 (model-facing): `prompts.py` + `replystyle.py` instructions (the two language anchors `lang.apply` swaps are unchanged, so `hoola_language=auto` still answers in her language); tool descriptions, parameter descriptions, ToolErrors and note / say / next hints in ~175 `agent/*_tools.py` (~1,100 strings, lengths same or shorter, safety phrases kept early, voice budget green); nudges + wake texts (aage, draftcheck, goal, santosh injected notes incl. `[Current time:`, kaam_followup, pakka, compact, hard, verify, research_plan, events card blocks, kaamwatch, yaad blocks, ~30 desk prompts that asked for 'Hinglish'); the voice call's persona / lean / brain persona, quiet notes and brief headers.
- KEPT on purpose: every regex / word list that READS her Hinglish or the model's output (`aage._PROMISE`, `draftcheck._DONE`, `_ASKS_PENDING`, voice stop / reminder words), tool + parameter names, enums, dict keys, protocol markers (`[Goal jaari:`, `GOAL JAARI HAI`, `KAAM KI HAALAT`, `HOOLA KI YAAD`...), quoted examples of what she may say, Indian terms, frozen PC files.
- LEFT for a later pass: `research/*.py` runner / bill messages, `kaamlist.py` states, `santosh.py` step / stop labels, `home.py` / `maps.py` say lines, `mailbox/accounts.py`, tourguide / avatar services.
- NOT VERIFIED: the Flutter + Kotlin text compiles only on CI (the APK build); no live chat / call has run on the English prompts yet.

## v0.729.0 SAB ENGLISH wave 2 — notifications, cards and server messages in English (9 Nov 2026; owner: "GO WAVE 2")

## v0.730.0 SHILP MANCH — the ArtCraft generation lane, their Omni API behind her tool (9 Nov 2026; owner: "MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS" on the storytold/artcraft recon)

Planned at v0.686.0; the dev chain ran on to v0.729.0 (SAB ENGLISH waves) while the plan sat — REBASE PROTOCOL onto their 53ab8a366 v0.729.0 tip, their base kept whole. **Registry 617 → 618** (617 + 1 shilp). Zero new pip, zero new keys (BYOK rides her key), zero Flutter change. ArtCraft is github.com/storytold/artcraft (MIT/Apache-2.0), "the IDE for artists"; this lane ports their DOCUMENTED Omni API surface only — nothing inferred (the kala law).

- **One tool, six actions** — `agent/shilp_tools.py`: `video` / `image` (POST /v1/omni_api/generate/... → an inference job token; video takes model, prompt, duration_seconds, aspect_ratio, negative_prompt, resolution, generate_audio, start/end frame urls + reference image/video/audio url lists; image takes model, prompt, image_urls) | `job` / `jobs` (GET /v1/omni_api/job_status/{job,batch} — their states ride raw; pending/started/attempt_failed still run, complete_success/complete_failure/dead/cancelled_* terminal; the finished media at state.maybe_result.media_links.cdn_url) | `status` / `models` (zero network; the curated 62-model catalog from their public README, dated, with the honest note that audio/mesh/splat have NO documented Omni API endpoint yet).
- **BYOK, owner-level** — config `artcraft_api_key` (VPS .env only, ARTCRAFT_API_KEY, never in chat, the repo, or any envelope — tested); API access is gated per account by the ArtCraft team (app.getartcraft.com → Settings → API Keys); no key = every network action answers NEED_SETUP with those exact directions.
- **Money is hers** — every generate call spends her ArtCraft credits; the tool description tells the model to fire only on her explicit ask; their 402 maps to `PAYMENT`, FINAL, never retried (hint: top up, then ask again); a 401 maps to `AUTH` naming the .env knob; their other 400s ride their own words inside UPSTREAM.
- **Idempotency minted here** — a fresh UUID4 per generate call (their doc's own rule), returned in the envelope; caller-supplied tokens ignored.
- **The reference-url wall** — every *_url crosses the lane's own check BEFORE any byte moves: http(s) only (their own rule), no embedded credentials, no loopback / RFC1918 / link-local / reserved / metadata hosts (an internal endpoint must never land in their server logs). Shape problems → BAD_INPUT; wall refusals → NOT_ALLOWED. Tested as a 12-case table, all refused before the seam.
- **URL inputs only** — their *_media_tokens fields are accepted only to be refused BY NAME, quoting their own mutual-exclusivity rule ("Either reference_image_media_tokens or reference_image_urls must be set, not both"); the upload endpoints behind the tokens are not in the public doc, so nothing is invented.
- **Caps refuse, never clamp** — prompt 8000 chars, 20 refs per field, 2048 per url, 25 batch tokens; a generation is money, silently trimming an ask would change the job behind her back.
- **One envelope, honest jobs** — {schema_version, ok, tool, action, ..., meta{elapsed_ms, backend}, error{code, message, hint}}; `ok` is the CALL, `job_ok` is the JOB — a failed generation is not a failed lane call and never hides behind one. Kill switch `shilp_enabled` (default on). All strings English.
- **Doors** — the toolbelt door (agent/tools.py, registry 618) + the MCP stdio door (`app/shilp/mcp_server.py`, the kaan wire: line-delimited JSON-RPC 2.0, protocol 2025-06-18, one tool `shilp`, dispatch through `shilp_tools._sync` so the doors can never drift, serverInfo `hoola-shilp`).
- Tests: NEW `test_v0730_shilp.py` (43, zero network; the seam fake records every call so tests assert method / url / body / auth shape, not just outcomes). Two pins ran red until the ritual landed the version — by design.
- Version ritual: `scripts/ritual_v0730.py` — version tokens swept with the parser-stamp guard, pubspec 0.730.0+729, console stamps `?v=0.730.0`, the APP_VERSION story splice, the three mirrors.
- Server-only deploy = owner's vps-ops dispatch; desktop untouched. NOT VERIFIED live: her first real generation — needs HER ArtCraft key in the VPS .env (`shilp` action=status shows the setup directions); the zero-network status/models ride the deploy. Next: W1 SHILP SEVAK (the job butler worker) once a real key exists.



## v0.743.0 SAAF INSAANI - same console, friendlier (owner: "DO NOT CHANGE EXISTING DESIGN BUT MAKE IT MORE USER FRIENDLY AND HUMAN MADE NATIVE" -> "GO")

The owner first saw a fresh "workroom" redesign on a canvas and asked to keep the EXISTING design instead; the second
canvas kept layout, colours (white, #5B45E0 violet) and fonts (Schibsted Grotesk + Literata) and changed only how the
screens read. Built behind `console_human` (default on; `/api/console/config` -> `human`; v2.js sets `html.human`;
conftest pins it off so older suites see the old wording byte for byte).

- Home: "Good morning / afternoon / evening, <name>" + `humanTagline()` - one sentence from the live queue / jobs
  ("Santosh has one thing waiting for your OK. Review ->", "...is working on 2 jobs for you right now", else ready).
- Work cards (`drawJobs`): a "Working / Waiting for you" tag, the real stage + `soFar(started_at)` ("6 min so far"),
  and a progress bar ONLY when the job reports a real pct (0-100) - no made-up bar.
- Sidebar Today badge in words ("1 needs you" / "2 working"); spend "Rs 412 of Rs 2,000" under "AI spend this month".
- Reply actions: Retry -> Ask again, thumbs get "Good answer" / "Not right"; composer placeholder gives a real example.
- `decisionRow` (every slide-to-approve card): "Slide to approve" / "Not now" + "Nothing happens until you approve."
- No emoji in the long-job report headings or memory notes; the Plan card header mark is still (no spinner).
- One-colour start-pill icons (CSS over the inline strokes); AI Employees role cards show "Needs: <first need>".
- NOT done (said plainly): her message's own time label (the hover Copy / Edit was already there).
- Tests: tests/test_v0743_saaf_insaani.py (switch, old words kept when off, new words present, a real-browser walk of
  the home with a working job). Pre-existing reds stay: test_v0555 card CSS literal-colour check, test_v142 recent list.


## v0.744.0 SEEDHA SEND (owner screenshot: "REMOVE THE AVATAR FACE AND CHAT PANEL SEND BUTTON IS GOING OUT OF PANEL")

Measured in a real browser: at 1440 / 1180 / 1000 px the Send button's right edge sat 12 px past the composer's
(1232 vs 1220). Cause: the v0.740 model chip is up to 200 px and v0.719 made every composer control `flex:none`, so
nothing could give room. Now `#composer .row>.modelb{flex:0 1 auto;min-width:0}` - the chip name ellipses first,
every other control keeps its size. The home greeting's avatar face (`.landing .halo`) is hidden under html.human.
Test: tests/test_v0744_seedha_send.py (Send inside the box at 1440 / 1180 / 1000 / 760, no face) - fails on the old CSS.


## v0.746.0 VIDEO LEARNER REDESIGN (built as 0.745.0 - their WEB + APP PAGES took 0.745.0, both kept; owner: "make all screen perfect and all feature functional" -> canvas -> "go")

Checked first: the v0.718 page was one long column in Hinglish; learned tasks could not be opened or removed; a watch
could not be stopped; the video was never shown; the "realtime" notes were the finished text revealed slowly; Perform
sent a chat turn and left her to find it. Rebuilt (`static/console/seekh.js`, `skv-` styles in v2.css):
- Home: link / upload / drop, today's count, learned tasks with YouTube thumbnails, Proven / Learned, not tried yet /
  Learned as notes / Could not learn (reason + Try again + Remove), filters.
- Watching: YouTube (youtube-nocookie) or her uploaded file plays; notes STREAM as Gemini writes them
  (`seekh._stream_text` over `generate_content_stream`; a thread-local sink so every perceive signature is unchanged;
  console job takes "partial" text without a stage row); [m:ss] chips seek the video; note marks on the bar for files;
  the five real stages with their own times; Stop (`/stop`, a cancel Event checked per chunk and between stages,
  `SeekhStopped`, nothing kept).
- Learned task (`GET /task`): steps with evidence chips, Before you start / Watch out / Not seen, a form built from the
  steps' value hints, confidence, Re-learn, Remove (`DELETE /task`: list row + procedure + a never-run recipe draft).
  Old rows rebuild their steps from the procedure labels.
- Doing it: Do it now = one chat turn (send now returns the chat id); the page follows that chat's timeline - live
  steps, a card that needs her -> Answer (opens the chat), Hoola's reply, then Did it work? (`POST /proven` ->
  sidecar wins/fails + `procedures.record_run`).
- Failed watches are kept (`seekh.record_failure`) and never count toward today's limit. Server messages English.
- Console CSP: + `https://i.ytimg.com` (img) and `https://www.youtube-nocookie.com` (frame) only.
- NOT built: a live picture of Hoola's browser on the run screen (needs the operator's screenshots on this page);
  an OTP typed on this page (it is answered in the chat card). NOT verified with a real Gemini stream or a real run.
- Tests: tests/test_v0745_video_learner.py (7, incl. a browser walk); v0713 / v0718 pins moved to the English wording.

## v0.747.0 HOOLA INTERACTIVE — the console's own video studio, HyperFrames end to end (10 Nov 2026; owner: "a perfect Hoola Interactive page in console - same as heygen - with hyperframes in it end to end" -> the 8-screen canvas -> "go")

Built screens 1, 4, 5, 6 of the approved canvas (Home, Studio, Making it, Ready) plus photo avatars; Live avatar and Translate are tabs that say plainly they are not built yet.
- PAGE: sidebar row "Hoola Interactive" right under Create (`static/console/interactive.js`, `.hiv-` styles in v2.css, switch `interactive_page`, pinned off in conftest for old suites). Home = one line + language / length / avatar + three kinds (talking avatar, product film, reel) + her videos + avatars + an honest engine line (video engine installed? voice engine set up?). Studio = the film as scenes: each spoken line, its look (title / big number / price / bar chart / lower third) and the look's fields, move / remove / add, kind, size, language, avatar, business name, closing card, products for a product film; autosave; what blocks Make is listed in her words and Make stays off until it is clear. Making it = the job's real steps with times + Stop. Ready = the video plays, Download MP4, Change something, Make a new version, the facts (length, size, scenes, how captions were timed).
- SERVER: `app/interactive/studio.py` (projects + avatars in data/interactive/<tenant>/studio.json, finished MP4s and photos beside it - the chat file lane is swept after 24 h; one make per tenant; Stop at the next step boundary) and `app/interactive/console.py` (/api/interactive/studio/status, list, draft, project GET/PUT/DELETE, make, progress, stop, video, photo, avatar POST/DELETE; key-protected, tenant-scoped).
- HER NUMBERS ONLY: the draft is one brain call (`videoedit.brain.think`); a big number / price / chart value not found in her own words is removed BY CODE and the scene is marked "Needs your numbers"; product prices the same. Her own edits are trusted.
- LOOKS in the composition (`studio/avatar.py`): spec `scenes: [{say, look}]` (the old `script` path byte-identical), `validate_look` refuses half-filled looks, `_look_divs` / `_look_script` draw them on track 5 with a GSAP entrance (bars grow), sized to the short side so a 9:16 reel keeps its captions clear; in a product film a look takes the scene's own spot and is refused on a scene that already shows a product.
- `frames.do_avatar_film` gained `on_stage` + `cancel` (optional; the chat tool path unchanged) and passes HYPERFRAMES_BROWSER_PATH / PRODUCER_HEADLESS_SHELL_PATH through to the renderer.
- FOUND BY RENDERING FOR REAL (hyperframes@0.9.6 installed in the sandbox, the box's Chromium): the v0.476 avatar-film composition was REFUSED by the engine's own check - no GSAP loader (`missing_gsap_script`) and `font_family_without_font_face` for Noto Sans Devanagari (not bundled; the bundled fonts are Latin). Fixed: the contract's GSAP loader line + bundled Inter (Indian scripts fall back to the render box's system fonts; the page drafts Hindi in Roman letters). Also found: in no-voice films the closing card started after the end (speech was set to the whole span) - fixed. The check's layout pass also caught looks overlapping reel captions - fixed by sizing to the short side. After the fixes a 14 s 9:16 reel and a 16:9 talking film with all four looks passed the check and rendered in ~26 s each; frames were looked at.
- PROOF: `tests/test_v0747_hoola_interactive.py` 7 (her-numbers-only, looks drawn + plain films unchanged, real steps + kept video, Stop keeps nothing + failure reason, consent-gated photo avatar + tenant scope, routes + switch, the page walked in a real browser). `test_v476_avatar_films.py` font pin moved to what the engine accepts.
- NOT VERIFIED: no voice in any render here (the Model Lab GPU is not reachable from the sandbox) - a voiced film's word timing and length are untested live; the photo avatar in a real render; whether her VPS has hyperframes installed (vps-ops hf_setup) - the page says so on its engine line if not. Not built: Live avatar (WebRTC to a visitor), Translate with lip-sync, consent-video face avatars (MuseTalk), the "AI-made" content credential.

## v0.748.0 HOOLA CODE — Developer Sahayak as a console page, like Claude Code (10 Nov 2026; owner: "we have already built the Hoola Code - first check the code and then a design same like Claude Code" -> the 6-screen canvas -> "GO")

The coding agent (Developer Sahayak, `server/app/devsahayak/`) had a full server and a phone screen but no console page. Now it has one, built on what already runs - nothing about how it codes changed.
- PAGE `static/console/code.js` (`.hcd-` styles in v2.css, sidebar row "Hoola Code" under Create, switch `hoola_code_page`, pinned off in conftest for old suites): its own sessions list (Running / Needs you / Earlier), Home (what should Hoola code + repo + issue + fix / feature / tests / docs / explain, Review a PR), Session (her ask, Hoola's own words, every step with its time, Stop, a box to tell Hoola something while it works; right side: changed files + checks), the big-job plan (goal / files / steps / done when / risks, Yes / Send change / Cancel), the finished work (why, the full diff, risk, Open the pull request = her tap with the card hash, PR link, Fix the CI failure, Check CI again, Ask to merge -> the merge card with CI state and a written reason when CI is not green = her tap, Ask for a change), Reviews (draft reviews with their comments, posted only as her choice of Comment / Request changes / Approve, or discarded), Settings (fine-grained token typed only here, repos, ask-before-PR / draft PR / workflow edits, merge method, review mode, limits, her rules).
- STEPS: `loop.step_event` turns each tool call into a structured record - say (the model's own text), rules, read (+ lines), search (+ count), list, usages (+ count), edit (+ added / removed + a short diff), new (+ preview), diff, check (pass / fail, seconds, command, the failing lines), check_off, grep, refused (+ the reason) - stored in the new nullable `devsahayak_tasks.steps` (JSON, last 400) and returned by GET /tasks/{id}. The old one-line Hinglish log is unchanged.
- HER WORDS WHILE IT WORKS: POST /tasks/{id}/note queues them (`devsahayak_tasks.notes`); the loop reads the queue between steps and adds a `<her_note_while_you_work>` block to its next turn; refused when Hoola is not working (use Ask for a change).
- STOP: POST /tasks/{id}/stop -> the loop raises `loop.Stopped` at its next step; the service lets it through (never the one-shot fallback), the task is marked stopped and nothing is prepared or pushed; a not-running task falls back to cancel.
- BACKGROUND: POST /tasks/start (same checks as start, the row at once, the work in a thread) and POST /tasks/{id}/bg/{plan_ok|revise|fix_ci|begin}; task views carry `running` / `stopping`. The hooks ride the step callback (`service._Step` with event / inbox / stopped), so the chat tool, the phone and every older test (plain lambdas) are unchanged.
- PROOF: `tests/test_v0748_hoola_code.py` 5 (structured steps incl. the refused edit and its diff, a queued note reaching the model + Stop pushing nothing, routes + switch, the plain-callback contract, the page walked in a real browser: home, a live session's steps + diff + Stop + note box, the plan card). The 14 older Developer Sahayak suites re-run.
- NOT VERIFIED: no live GitHub repo has run through the page yet; steps refresh every 2 s (polling), not word by word; the tasks run in this process's threads, so a server restart mid-job ends it (the row keeps its steps; start it again); deploy cards are not on the page yet (merge is).



## v0.749.0 SAB PUBLIC APIS - every public API list in one catalog (owner: "NOW CONSOLIDATE ALL PUBLIC APIS FIRST")

She read publicapis.dev. Its data is github.com/marcelscruz/public-apis (MIT, `db/resources.json`, 2,021 entries, with
AI and Podcasts categories the older list lacks). Hoola's `api_find` / `api_docs` / `api_call` catalog (v0.47) was
built from ONE list, github.com/public-apis/public-apis (2,161 rows at the time).

`server/app/publicapis/build.py` now builds ONE catalog from both:
1. Source 1, the public-apis README, parsed as before (refreshed: 2,343 rows). Its ids are `<category>-<name>` as
   always, so saved keys (`PublicApiKey.api_id`) and remembered recipes (`PublicApiRecipe.api_id`) keep pointing at
   the same API.
2. `keep_old()`: a row of the catalog being replaced whose id the fresh README no longer has is KEPT (5 dropped
   upstream: micro-user-service, micro-db, k-data-gate, hong-kong observatory, micro-weather); when the same name is
   back under a new id (VedIntel AstroAPI moved Science & Math -> Personality) the old id becomes an `aka` alias on
   the new row and `service.by_id()` resolves it.
3. `parse_dev()` + `merge()`: a publicapis.dev API is added only when source 1 lacks it - not the same name (letters
   and digits only) and not the same API-owned host (`SHARED_HOSTS` such as github.com, rapidapi.com, postman,
   swaggerhub, docs sites never count as proof of sameness). Added ids are `dev-<category>-<name>`, so they can never
   collide; an empty Auth means no key. 671 added.
Result: 3,014 APIs, 53 categories, every row tagged `src` (public-apis / publicapis.dev); `find()`'s `source` credits
both. Counts in the agent prompt, the api_find tool text, console Kaam and the website say 3,000+.

Tests: NEW test_v0749_public_apis.py (5): both lists present + unique ids + an added API never repeats a source-1
name, new APIs found + both sources credited + old ones still rank, the merge rules (same name / same own host /
shared host is no proof / no link skipped), keep_old (dropped = kept, renamed = alias), every v0.47 id still resolves
in the shipped catalog. test_publicapis + v0238 data desk + v0561 omnipack green beside it. Note found: source 1
itself lists a few names twice across categories (e.g. Cat Facts) - upstream, left as is. Server + static text only;
no new pip; rebuild with `python -m app.publicapis.build` (fetches both from GitHub).


## v0.750.0 API BOX - the free public APIs behind ONE call (owner: "WE WILL CREATE A BOX FOR PUBLIC APIS AND DEVELOP ONE CALLING API ... THAT SINGLE API GO TO THAT BOX AND EXTRACT THE API REQUIRED" -> "NOW CREATE A BOX FOR FREE APIS FIRST")

Her live site check on the VPS (old 2,161 catalog): 1,796 alive, 128 blocked, 86 dead, 81 timeout, 70 unreachable;
the 1,035 free ones: 852 alive. Before this the model ran api_find -> api_docs -> api_call itself on every ask.

`server/app/publicapis/box.py` - ONE door, free APIs only (auth none):
- `plan(need, params, api)`: candidates = STARTER recipes whose `need` words meet her words (13, each called live on
  10 Nov 2026: india_pincode, ifsc, place_to_coordinates, weather_now, air_quality, currency_rate, dictionary,
  mutual_fund_search, mutual_fund_nav, books, earthquakes, sunrise_sunset, crypto_price) + every learned call
  (PublicApiRecipe) of a free API, scored on that API's own name / description / category (all learned rows, not the
  catalog search's top N - a test caught that a proven call ranked 30+); a learned pattern with a blank in its path is
  skipped. APIs hidden by health are dropped. `api` = a recipe key / api id to use directly.
- `call(tenant, need, params, api)`: fills the recipe (every value URL-quoted, so a value cannot add a path, query or
  host), calls through `service.call` (the same door as api_call: https only, public hosts, GET, size / time caps,
  the owner-key rules), falls back to the next candidate (max 3 tries), answers {ok, api, url, data, tried, source};
  ok false names the missing values (`params_needed`) or the closest free alive APIs + the learn-it hint (api_docs +
  api_call; a call that works becomes a recipe the box uses next time).
- Health: table `public_api_health` (api_id, status alive / blocked / dead / timeout / unreachable, http, failures in a
  row, checked_at); `hidden` = dead or 2 failures in a row; every box call updates it; `check(limit, older_days)` asks
  each free API's own page once (20 at a time, 12 s, the house public-host guard); worker slot `api_box_jobs` once a day
  re-checks the `api_box_check_per_day` (300) least recently checked (0 = off; conftest pins 0 so tests never reach
  the network); `python -m app.publicapis.box check [n]`.
- Doors: tool `api_box` (first in the publicapi family; family words now include pincode / IFSC / exchange rate / AQI /
  earthquake / sunrise / bitcoin / meaning of), prompt line "FIRST try api_box", POST /api/box/call, GET /api/box.
  Switch `api_box_enabled`. Registry 620 -> 621.
Live from the sandbox (no mocks): pincode, IFSC, USD->INR, meaning, bitcoin, earthquakes, mutual fund search - 7/7 ok
through one call. Left out of the starters on purpose: Wikipedia (refuses this address), REST Countries (version
deprecated), Universities (http only), India holidays / Nager for IN (no data).
Tests: NEW test_v0750_api_box.py (8) - free starters with real catalog ids, words -> the right recipe, fill + call +
one shape + quoting, fallback + hidden after two failures, missing values named, health classify + oldest first +
nothing older than 30 days re-checked, route + worker slot off at 0, her words open the family + prompt line; the
tool-count pins moved 620 -> 621.
NOT VERIFIED: the daily health check on her VPS (first run after deploy logs `api box health: ...`); Open-Meteo weather
was rate-limited from the sandbox's shared address that day.

## v0.751.0 HOOLA FLOW — the Kaan pack (W0-W6) as a console page, like Wispr Flow (10 Nov 2026; built as 0.749 - their SAB PUBLIC APIS took 0.749.0 and API BOX 0.750.0, all kept; owner: "a wisperflow of hoola - check the code" -> "WISPERFLOW IS FULLY DEVELOPED, CHECK THE REPO" -> "first show me the design here" -> the 8-screen canvas -> "GO")

The owner's "Wispr Flow" is the Kaan pack (WhisperAI feed plan, W0 v0.601 -> W6 v0.682: transcription, pause turns + minutes, live captions, word list + styles, exports + Gyaan + translate, HTTP / MCP / extension doors, quotas + retention + voiceprint). All 7 Kaan suites pass (154 tests). It had no page of its own; now it has one, riding the /api/kaan/* routes unchanged.
- PAGE `static/console/flow.js` (`.hfl-` styles in v2.css, sidebar row "Hoola Flow" under Create, switch `flow_page`, pinned off in conftest for old suites): Home, Dictate, Files, one transcript, Live captions, My words, Settings (read from the server: the engine, the recording switch KAAN_AUDIO, speakers, voiceprint, the monthly limit, delete-after days, the other doors - changed in the server settings, not on the page).
- MIC: `HoolaFlowRec` captures the mic with an AudioContext + ScriptProcessor and sends 16 kHz mono 16-bit WAV pieces every 2 s; every piece is a whole file, so `live._decode_chunk` (ffmpeg) reads each one on its own. `HoolaFlowSession` wraps live start / chunk (in order, one at a time) / stop. Proven in Chromium with a fake mic: 4 pieces, each decoded by the server's real ffmpeg, 3.25 s for 3.3 s recorded.
- CHAT BOX: `HoolaFlowMic` - when `flow_composer_mic` is on and the engine is ready, the composer mic (and Ctrl + Space in the box) dictates through Kaan and puts the Clean text in the box (nothing sends by itself); otherwise the v0.173 browser speech service as before.
- NEW `kaan/flow.py` -> /api/flow: overview (plain-English state + recent items with kind dictated / live / file), transcript with segments + turns, rename, pin (the W6 sweep keeps it), delete (her tap).
- PROOF: `tests/test_v0751_hoola_flow.py` 6 (switch off = 404, overview / rename / keep / delete, a dictation round trip named as dictated + clean style, the page's WAV decoded by the real ffmpeg piece by piece, the page wiring, the page walked in a real browser: home + search, a transcript with turns, styles, action items -> the chat box, words, settings, dictate, files).
- FOUND, NOT FIXED (frozen desktop/): the Chrome extension's offscreen.js sends MediaRecorder webm slices every 2 s; a webm slice after the first has no header, so ffmpeg likely refuses pieces 2+ of a tab caption. The console's own recorder avoids it with WAV pieces. The fix (restart the recorder per slice, or send WAV) is in desktop/ext, frozen - needs her word.
- NOT VERIFIED: no real voice on her server yet (the engine is installed there per the W1 notes; this sandbox has no Whisper); the phone screen is not built; a file is answered in one go when the whole recording is written (no progress percent); no audio player on a transcript (Kaan keeps text, not audio).

## v0.752.0 ARTCRAFT IN CREATE — the v0.730 SHILP lane as a Create studio tool (10 Nov 2026; owner: "now lets develop a artcraft in create section in hoola --- artcraft is already developed in backend")

The backend (v0.730 SHILP MANCH, `agent/shilp_tools.py`) was a chat tool only: ArtCraft's Omni API (api.storyteller.ai, BYOK key in the VPS .env) for video + picture generation and job polling. Now the Create studio has it as a tool.
- PAGE (studio.js `V.artcraft` / `W.artcraft`, sidebar row "ArtCraft" under Tools + a home tile; shown when the console config says `artcraft` = `shilp_page` and `shilp_enabled`): Video | Picture; the model id (ArtCraft's own snake_case ids - her used ids + the documented `seedance_2p0` as suggestions; the curated catalog by family under "What ArtCraft has"); the prompt; video shape 16:9 / 9:16 / 1:1, seconds, 720p / 1080p, model sound; Advanced: keep-out, first / last frame, reference picture links (public links only). Create = her tap plus one confirm ("spends credits on your ArtCraft account"). Results: running jobs (ArtCraft's own status + %), finished files as normal Create tiles (open / download / delete), failed jobs with ArtCraft's reason, Remove.
- SERVER `server/app/shilp/api.py` -> /api/shilp (switch `shilp_page`, pinned off in conftest): GET (lane state - key set or the setup steps -, catalog, her jobs with running ones refreshed in ONE batch call, models she used), POST /generate (refused without confirm=true; rides the shilp tool, so the idempotency token, the reference-url wall and the 402-is-final law all hold), POST /jobs/{token}/check, DELETE /jobs/{token}. Jobs in data/shilp/<tenant>/jobs.json.
- ON HER SHELF: the first time a job finishes, its file is fetched once from the cdn_url ArtCraft returned for THAT job (through the lane's wall: public https, no loopback / private hosts; 300 MB cap; must really be a video / picture) and kept with `create.jobs.keep` (meta source ArtCraft, model, job), so it is in My creations and outlives ArtCraft's link. A failed copy keeps the link ("Open at ArtCraft") and says why.
- PROOF: `tests/test_v0752_artcraft_create.py` 6 (switch off / no key + setup steps, no confirm = no call, generate -> poll -> complete -> file on the shelf once -> remove keeps the file, 402 and a private reference link refused before anything is kept, a private file link never fetched, wiring, the tool walked in a real browser: running + failed tiles, model suggestion, Create sends confirm + shape, Picture mode). The shilp (43) and Create studio (18) suites re-run green.
- NOT VERIFIED: no real ArtCraft call has ever been made from Hoola (no key in this sandbox; API access is gated per account by the ArtCraft team); the cdn host and the exact model ids her account has are only known after her first real job. Audio / 3D / worlds are not offered - their Omni API documents only video + picture.

## v0.753.0 SKILLS FIND + UIUX DATA — the awesome-pack skills reached by everyday words, quieter Anthropic skills, the UI/UX Pro Max database committed (10 Nov 2026; owner: "now check the awsome skills deployed in backend" -> "go")

THE AUDIT (before): 9 of 20 everyday Hinglish asks got the right awesome-pack skill in the injected top 2 (the descriptions were written in the packs' own vocabulary, not the words people type); internal-comms and theme-factory (long Anthropic descriptions full of everyday words) rode along on unrelated asks ("which python library should I use to read excel", "set up a new laptop"); `server/app/coder/uiux/data/` (the UI/UX Pro Max database, v0.486) had never been committed, so 6 UIUX tests failed and the uiux_design tool had nothing to search on a fresh checkout.
- TRIGGER WORDS: each of the 42 awesome-pack files has a `when_to_use:` line (plain words people type, <= 240 chars here, WHEN_MAX 300). `skills_store.create(extra=)` keeps it on the strict lane; `_mirror` appends it to the searched description. `add_when` / `get_when` change only that frontmatter field. `skill_packs.seed_when` (own stamp = digest of every shipped line, so improving a line re-runs it once): a skill with no line gets one, a line Hoola shipped earlier (remembered by hash, `skills:whenmine:`) is replaced, a line she wrote is never touched; her description / body never change.
- QUIETER MATCH (`store.skills_search`): a description over 200 chars (LONG_DESC) needs two of her words in the name / description, not one plus a body hit; English helper words (should / would / use / need / make / get / some / all ...) joined the stop list - "should" + "use" alone had matched internal-comms ("Claude should use this skill").
- CARD (`python -m app.quality skills`): an Awesome packs line - 20 tuned asks, 20 fresh asks written before tuning (17/20 at first, three trigger words added after), 8 unrelated asks that must pull no skill. Clean tenant: tuned 20/20, fresh 19/20 (miss: "is mahine kaun kaun se hackathon hain"), unrelated 8/8; the original card rows stay 10/10 and 4/4.
- UIUX DATA: restored from upstream nextlevelbuilder/ui-ux-pro-max-skill commit 6ae86f6 (`src/ui-ux-pro-max/data`, MIT, same LICENSE; the vendored scripts are byte-identical to that commit), phosphor-icons-upstream.json left out as PROVENANCE.md already said.
- PROOF: `tests/test_v0753_skill_triggers.py` 7 + the skill suites (desk, byox, uiux, starter / packs, fe, omni, routines) re-run.
- NOT VERIFIED: the free card proves the skill is offered, not that the model follows it (`--live` not run); a tenant's skills get the trigger words on its next chat turn / Skill Desk open.



## v0.754.0 KEYED BOX - data.gov.in on one server key (owner: "Open Government India (data.gov.in) -- GOT THIS" -> "I HAVE NOT PUT ANY KEY IN APP --- IT SHOULD NOT SEEN IN APP --- IT IS FOR HOOLA FOR ALL USER")

The v0.750 box held only free (no key) APIs. A recipe may now be `needs_key`. Keys come from two places, in order:
1. a SERVER key the owner puts in the VPS `.env` for Hoola itself (`publicapis.service.SERVER_KEYS`: api_id ->
   settings field, place, field). It serves every user, appears in no app, never reaches the model. data.gov.in =
   `DATA_GOV_IN_API_KEY`, sent as the query parameter `api-key` (its own docs).
2. else a user's own key saved in the app (the v0.4xx path; `KEY_PLACE` now overrides a wrong field typed on the phone).

New recipes: `mandi_price` = data.gov.in resource 9ef84268-d588-465a-a308-a864a43d0070 (current daily mandi prices;
optional filters commodity / state / district / market, added as `filters[...]` pairs only when given, urlencoded so a
value can never become a parameter of its own) and `india_gov_dataset {resource_id}` (any data.gov.in resource).
No key = the recipe is skipped and the answer says the server owner must add `DATA_GOV_IN_API_KEY`; the model is told
never to ask for a key in chat. service.call says the same for a server-keyed API without a key.

Tests: test_v0754_box_keyed.py (4, offline MockTransport) + test_v0750 starter count 13 -> 15.
NOT VERIFIED: data.gov.in refuses this sandbox (connection reset), so the first live call is on the VPS; the filter
names `filters[commodity]` etc. are from the platform's documented shape and are checked by that first call.

## v0.755.0 EVERY SKILL FINDABLE — trigger words on all 99 shipped skills (10 Nov 2026; built as 0.754, their KEYED BOX took 0.754.0 - REBASE PROTOCOL, both kept; owner: "ALL SKILLS DEVLOPED")

v0.753 gave plain trigger words (`when_to_use`) to the 42 awesome-pack skills. The other 57 shipped skill files still had none: 31 build-your-own-x (byox-*), 15 superpowers (sp-*), the 10 starter skills (deploy-flask-app, excel-data-clean, gst-invoice, hindi-reply-tone, meeting-minutes, morning-briefing, pdf-fill-form, seo-page-audit, upi-payment-chase, whatsapp-campaign) and uiux-pro-max. Each now has one `when_to_use:` line (<= 240 chars) of the words people type ("telegram bot", "gst bill", "payment pending", "debug karo", "unit test likho", "colour palette"...). The 8 Anthropic skills under `skillpack/claude/` keep their own long descriptions (v0.753's stricter match governs them).
- REACH: tenants who already hold these skills get the line through `seed_when` on their next chat turn / Skill Desk open (a line she wrote herself is never replaced).
- CARD: `python -m app.quality skills` prints "Other shipped skills (set v1)" - one plain Hinglish ask per skill (`skills_asks.REST`), the exact skill in the injected top 2: 57/57 on a clean tenant (55/57 at first; "malloc" and "kaunsa skill" added). Awesome packs unchanged 20/20 + 19/20, unrelated asks 8/8 clean, the original rows 10/10 + 4/4.
- PROOF: `tests/test_v0755_all_skill_triggers.py` 2 (every shipped file has a line within WHEN_MAX; 57/57 + negatives clean) + the skill suites re-run.
- NOT VERIFIED: reachability only - whether the model then follows a skill needs the paid `--live` card.



## v0.756.0 DATA.GOV.IN RELAY (built as 0.755; their EVERY SKILL FINDABLE took 0.755.0 - REBASE PROTOCOL, both kept)

Her live test of v0.754: `mandi_price` -> ConnectTimeout. On the VPS: api.data.gov.in (164.100.61.198, IPv4 only) never
answered in 40 s; data.gov.in, enam.gov.in and india.gov.in the same; agmarknet.gov.in and api.postalpincode.in answered
in 0.05 s / 0.2 s; tracepath dies past hop 16. NIC's data centre drops connections from cloud servers - not the key, not
the code.

- `DATA_GOV_IN_BASE` (settings `data_gov_in_base`, https only): her own relay base. `publicapis.service.SERVER_BASES` +
  `rebase()` swap https://api.data.gov.in for it inside service.call before the key is added; empty = direct.
- `deploy/datagov-relay/worker.js`: a Cloudflare Worker (her account, free plan) forwarding only GET /resource/... and
  /lists to api.data.gov.in; keeps and logs nothing; the key still lives in the VPS .env and only passes through.
- box.plan: a `needs_key` recipe is never hidden by failures (the daily check covers free APIs only, so a hidden keyed
  recipe could never come back); a starter recipe scoring under half the best one stays out of the fallbacks (her test
  pulled in mutual_fund_nav and crypto_price on one shared word).
Tests: test_v0754_box_keyed.py +2. NOT VERIFIED: whether NIC answers Cloudflare's addresses - her first relay call says.

## v0.757.0 KALA KHULA — the Google skills catalog reached by everyday Google Cloud words (10 Nov 2026; built as 0.756, their DATA.GOV.IN RELAY took 0.756.0 - REBASE PROTOCOL, both kept; owner: "NOW CHECK ALL GOOGLE SKILLS IN REPO DEVLOPED FOR HOOLA")

THE CHECK: v0.681 KALA MANCH (`agent/kala_tools.py`, tool `kala`) reads Google's public skill catalog github.com/google/skills. Driven live from here: index.json answers 200 with 187 skills (it was ~75 KB at v0.681, now ~129 KB); catalog q=bigquery -> 17 hits, read agent-platform-access-audit -> its SKILL.md (12k cap), list gke- -> 42, status ok; the 34-test suite green. Nothing is copied into the repo - the documents are read on demand, never executed (the v0.681 law).
THE GAP: the tool had no words of its own. Its only admission key was the bare family name `kala`, which is Hindi for black / art - so 'google cloud par GKE cluster kaise banaun', 'bigquery mein ML model', 'firebase setup' never brought it into view (0/8), while 'kala kurta online order karo' did. tool_search could not find it for 'gemini api' / 'bigquery' either.
THE FIX: `admit.EXTRA_KEYS["kala"]` = the products its skills cover (google cloud, gcp, gcloud, gke, kubernetes engine, bigquery, vertex ai, agent platform, gemini api, genkit, firebase, cloud run, cloud logging / monitoring, secops, alloydb, spanner, bigtable, apigee, iam policy / role, google skill, well-architected, google mobile ads, admob); `kala` joins `_GENERIC` (no key from its own name); the tool description names the products. Plain 'google' / 'cloud' / 'drive' / 'maps' / 'gmail' are deliberately NOT keys.
- RESULT: 10/10 Google Cloud asks bring it into view, 0/8 unrelated asks (incl. 'kala kurta', 'google drive', 'google maps', 'gmail'); free tool card unchanged 176/176, wrong family 0.
- PROOF: `tests/test_v0757_kala_khula.py` 3 + test_v0681_kala_manch 34 + the admission suites re-run.
- NOT VERIFIED: whether the model then reads the right SKILL.md and follows it on a real ask (no live chat run).



## v0.758.0 NEWS IN THE BOX (owner: "lets do next" after data.gov.in went live through the relay)

Second server-keyed API family in the box, the v0.754 pattern: `SERVER_KEYS` gains news-newsdata (`newsdata_api_key`,
query `apikey`) and news-gnews (`gnews_api_key`, query `apikey`) - both confirmed from each API's own reply to a keyless
call (newsdata 401 "The API key is missing", gnews 400 "Add your API key as the apikey query parameter"). One key each
in the VPS .env for every user; nothing in any app; the key never reaches the model.
Recipes: news_india = newsdata.io /api/1/latest?country=in (+ optional q / language / category), news_search =
gnews.io /api/v4/search?q=...&country=in&max=10 (+ lang), news_headlines = gnews.io /api/v4/top-headlines?country=in
(+ category / lang). No key = skipped, naming the missing .env line. Tests: test_v0758_box_news.py 3; starter 15 -> 18.
NOT VERIFIED: no live call with a real key yet - her first test on the VPS is it.


## v0.759.0 NEWS SAAF (owner's v0.758 live test)

Her first news test crashed in the test script because `data` was a STRING: newsdata / gnews answers run 30-60k chars,
over service.MAX_OUT_CHARS (12k), so the box passed the model cut-off JSON text. A recipe may now carry
`slim: {list, fields}`: the box calls service.call(full=True), takes the full answer (`_data`, never returned) and keeps
the listed fields per item (a dict field -> its name / url, a list -> joined, text > 300 chars cut), at most 10 items, plus
the scalar totals (`box._slim`). The three news recipes use it. Test: test_v0758_box_news.py +1.


## v0.760.0 SHARE BHAV (owner: "proceed" on Twelve Data + Alpha Vantage)

Third server-keyed family in the box. SERVER_KEYS gains finance-twelve-data (`twelvedata_api_key`) and
finance-alpha-vantage (`alphavantage_api_key`), both query `apikey` (each API's own keyless error names it). Twelve
Data's keyless symbol_search showed RELIANCE on NSE (XNSE) and BSE (XBOM). Recipes: stock_price (/quote, exchange
NSE default), stock_search (/symbol_search), stock_history (/time_series, 1day x 30 default) on Twelve Data;
stock_price_bse (GLOBAL_QUOTE symbol=<SYM>.BSE) on Alpha Vantage as the backup. Alpha Vantage answers a refusal with
HTTP 200 ("Error Message" / "Information" / "Note"), Twelve Data / NewsData with status "error": `box._soft_error`
reads those as failures so the next recipe answers instead of the model being handed a refusal as data.
Tests: test_v0760_box_stocks.py 2; starter 18 -> 22. NOT VERIFIED: whether Twelve Data's FREE plan serves NSE / BSE
quotes - her first live test says; Alpha Vantage free is about 25 calls a day.

## v0.761.0 LANGGRAPH G0 — the chat turn loop on official LangGraph, behind a switch (10 Nov 2026; owner: "OUR PRODUCT IS IN DEVELOPMENT ... FIX THIS ALL NOW WITH LANGGRAPH ... DO DEEP RESEARCH, FIND THE HOOLA ISSUES AND FIX THIS PERFECTLY")

RESEARCH (`docs/LANGGRAPH_TURN_PLAN.md`): the turn pipeline mapped stage by stage; 13 recurring bug classes (durability, delivery, false done, turn ends on text, guessed caps, two turns on one chat, card state, stop, repeated side effects, call vs chat, slow prompt, many models, scope leaks) each patched more than once with globals / regex / timing guesses; the in-house `app/aep` LangGraph copy found NOT production-capable (astream is a sync generator, async walk skips the checkpointer, interrupt breaks under to_thread, no cancel, lossy model adapter, bind_tools missing, `/api/aep/turn` fails on every real call - its tests only used a sync fake) -> decision: the OFFICIAL `langgraph` library (MIT), graph only, Hoola's own model + tool paths. Phases G0-G7.
G0 BUILT: `santosh._steps_inner` (641 lines) split into `_turn_prepare` / `_turn_model` / `_turn_after_model` / `_turn_tools` / `_turn_capped` / `_turn_silent` sharing one `_Turn`, and `_steps` into `_steps_begin` / `_steps_end` - code moved, not copied, so both paths run the same steps. NEW `agent/turngraph.py`: StateGraph prepare -> model -> (tools -> model | check -> model / finish | finish), every tool still through `_run_tool` (approvals, money on her tap, redaction, logging), one shared contextvars Context per turn (LangGraph runs each node in its own task), plain-data state checkpointed by AsyncSqliteSaver at `<chat_graph_dir>/checkpoints.db` (thread = conversation:turn; resume after restart is G1), recursion limit from the step caps, `_with_deadline` still wraps the turn, langgraph missing = the old loop answers. Switch `chat_graph` default OFF; deps langgraph>=1.2.20, langgraph-checkpoint-sqlite>=3.1.3 (pip install on the VPS).
- PROOF: `tests/test_g0_turngraph.py` 11 (the same scripted turn through both paths: identical saved rows, event sequence, reply, model calls and outcome for a plain answer, one tool, two parallel tools, a tool error, a false-sent nudge, a max_tokens continue, the step cap; checkpoint written; old path never touches the graph; contextvars survive nodes). harness2 / harness3 / routines / robust_chat / plain loop / long jobs / realtime / v0649 / v0657 / v0663 / v0664 / v0686 / v0691 / v0683 give the same counts with the switch off and on. Two reds (test_v0667 corrected reply, test_v0638 call memory) fail on the pristine tree too.
- NOT VERIFIED: nothing live; streaming deltas not compared (tests run with streaming off; same function both paths); many concurrent turns on one checkpoint file not tested.



## v0.762.0 SHARE BHAV 2 (owner's v0.760 live test)

Live on the VPS: stock_search (Twelve Data) ok, stock_price + stock_history (Twelve Data) HTTP 404 - Indian exchange
quotes are not on Twelve Data's free plan; stock_price_bse (Alpha Vantage) ok, RELIANCE.BSE 1323.90 (2026-11-09).
- Starter recipes may carry `bonus` (added to the word score). stock_price_bse gets 2 and the wider need words, so
  Alpha Vantage answers Indian price asks first; Twelve Data's stock_price stays as the fallback for a paid plan.
- NEW stock_history_bse = Alpha Vantage TIME_SERIES_DAILY {symbol}.BSE compact; `_slim` gains a dict mode
  (`{"dict": <key>, "n": N}`): the newest N dated rows with "1. open" -> "open" field names; her `days` sets N (<= 100).
- An HTTP error in the box now appends the API's own message (`message` / `error` / the recipe's error_keys), so the
  next live test says WHY (e.g. a plan limit), not only the code.
Tests: test_v0760_box_stocks.py +1 (and the 200-refusal test re-pointed at the new order); starter 22 -> 23.
Limits said plainly: Alpha Vantage free is about 25 calls a day for every user together; NSE is not on Alpha Vantage.


## v0.763.0 ADALAT (owner: "eCourtsIndia")

Read first (ecourtsindia.com/api/docs v4.0 + /api/pricing): base https://webapi.ecourtsindia.com, auth
`Authorization: Bearer eci_live_...` (41 chars), JSON {data, meta.request_id}; PAID per successful call - pay-as-you-go
(3x base) Case Detail Rs 1.50, Case Search v2 Rs 0.60, Cause List Search Rs 3.00; Rs 200 free credits on signup; failed
requests and empty results are not charged; limits 100/min, 3,000/h, 50,000/day; commercial use = a paid plan.
- SERVER_KEYS entries may carry a 4th element, a prefix ("Bearer ") - government-ecourtsindia -> header Authorization.
- Recipes: court_case GET /api/partner/case/{cnr} (CNR checked against [A-Z]{4}\d{12} and upper-cased BEFORE the
  call; answer slimmed by the new `obj` mode: scalars, 5 items a list, 300-char text); court_search GET
  /api/partner/v2/search (litigants / advocates / judges / query, at least one); cause_list GET
  /api/partner/causelist/search (q / advocate / litigant, at least one; date, state).
- Money guard: `patterns` + `need_one_of` refuse an unusable call for free; `daily_cap` = ECOURTS_DAILY_CALLS successful
  calls a day (IST) for ALL users together (table public_api_daily; 0 = switched off); the cap answer names the .env line;
  every eCourts answer tells the model the call was paid and not to repeat it.
Tests: test_v0763_box_courts.py 3 (Bearer header + slim + paid note, free refusals, the cap across tenants); starter 23 -> 26.
NOT VERIFIED: no live call yet; the search / cause-list result field names in the slim lists are read from the docs'
examples and the first live answer may name them differently (unknown fields simply drop out - the owner's test will show).


## v0.764.0 ADALAT 2 (owner's v0.763 live test)

Live on the VPS (Rs ~5 of the free credits): court_case DLHC010351552024 ok (Delhi HC record with its hearing history),
court_search litigants=Ramesh Kumar ok (totalHits 100,150, facetMode full, 10 results with cnr / caseType / petitioners),
cause_list advocate=Sharma state=MH ok (2026-11-16 lists, e.g. Wardha district court) - but each cause-list row carried
only date / courtType / listType / caseNumber / judge / courtNo / state / district: the party and advocate fields were
named differently live than in the docs' example, and the fixed slim list dropped them. A slim list with no `fields` now
keeps every short field the API sent (`_flat`); cause_list uses it. Test: test_v0763_box_courts.py +1.

## v0.765.0 GSTIN JAANCH (owner: "business-gstinapi")
gstinapi.in in the API box on ONE server key (`GSTINAPI_API_KEY` in the VPS .env, header `x-api-key`; never in any app, never to the model).
Recipes: `gstin_verify` (/v1/gstin/{gstin}), `gstin_compliance` (/compliance?fy=), `gstin_returns` (/returns?fy=), `hsn_code` (/v1/hsn/{code}).
Paid per lookup (~Rs 0.40-0.80, 75 free credits): a GSTIN failing the check digit (appmaker.gst.valid_gstin; the sandbox 00AAAAA0000A1ZT allowed)
is refused BEFORE the call, a daily cap for all users (`GSTIN_DAILY_CALLS`, default 50, the PublicApiDaily table), `fy` defaults to the current
Indian financial year (`@fy`), a 200 with success:false counts as a failure. Tests test_v0765_box_gstin.py (3). NOT VERIFIED live until her key is in.

## v0.766.0 GSTIN SACH
Her live v0.765 test: gstin_verify works on her free gstinapi.in account; compliance / returns / HSN answer 403 "This endpoint is
available to accounts that have bought a credit pack". 'gstin compliance' then fell back to gstin_verify and came back ok:true as if it
were the compliance answer. box.call now adds `instead_of` (the failed recipes) and a NOT WHAT SHE ASKED FOR line with the reasons to
note_for_you whenever an earlier recipe errored before the one that answered. Test in test_v0765_box_gstin.py.

## v0.767.0 LANGGRAPH G1 — a graph turn resumes after a restart + the tool ledger (10 Nov 2026; owner: "GO G1")

Phase G1 of `docs/LANGGRAPH_TURN_PLAN.md` (bug classes 1 and 9), only when `chat_graph` is on (default OFF; the old path is unchanged).
- Stable thread id `"<conversation>:<inbox id>"`: `turn_inbox.run_owned` sets `GRAPH_TURN` / `GRAPH_RESUME`, `turngraph.run_steps` takes them once; a turn with no inbox row gets a random id; a conversation with no id falls back to the old loop.
- Every node checkpoints the turn's working state as plain data (the `_steps_begin` dict minus the breaker / native tool list, breaker counters, admitted families, final text, prepared, last stop).
- Sweep: a turn that began and was not answered is checked with `turngraph.resumable()` (next node model / tools / check / finish, prepare done) -> `run_owned(save_user=False, graph_resume=True)`, no RESUME_NOTE; else today's re-run. `resume()` restores history, state and breaker without re-running the hard-ask judge / hint lookup, re-runs prepare in the turn's shared context, then `ainvoke(None)`.
- NEW `agent/toolledger.py` (table `turn_tool_ledger`, in `db.init_db` + `ensure_table`): `intent` before `_run_tool`, `done` with the output / `failed` with the error after. On resume: done = stored result reused (tool not called), failed = same error, intent with no end = re-run only if read-only (`draftcheck._is_read` + `santosh._parallel_ok`), otherwise `santosh.ToolAmbiguous` -> the model reads "may already have run, outcome unknown, check before any retry".
- LangGraph's `NodeCancelledError` is turned back into CancelledError so a cut turn keeps its checkpoint. END or an error reply deletes the thread's checkpoints + ledger rows; ledger rows older than `chat_graph_ledger_keep_h` (24 h) go; daily inbox housekeeping deletes threads of removed rows. New settings `chat_graph_keep_finished`, `chat_graph_ledger_keep_h`.
- TESTS: NEW `test_g1_turngraph.py` 9; g0 11, harness2 15, harness3 17, routines 3, v0657 14, v0664 kaam ek baar 10, v0649 11 and others same with the switch off and on.
- NOT VERIFIED / STILL OPEN: the crash is simulated (CancelledError + cleared memory), not a real process kill; a crash inside the model node after the model answered re-runs that call (a second model call, maybe a second assistant row); a crash in prepare uses the old RESUME_NOTE path; tool_search results and narration state are rebuilt, not restored; a reused done tool skips event-log / coder-memory capture; timed-out turns keep checkpoints until the daily housekeeping. Next: G2 (one run per chat + Stop as state).


## v0.768.0 IMAGE EDIT (built as 0.759.0, re-versioned twice as main moved; owner: "Image editing --- perfect work on it end to end deeply and perfectly for hoola", after the aixploria.com read mapped 4,863 AI tools to Hoola - 210 of them image editing)

ONE new tool `image_edit` (registry 621 -> 622) in `server/app/imgedit/`; photo_banao / photo_clean / id_photo keep their specs.
- LOCAL (`ops.py`, Pillow + numpy, no key, deterministic): resize (17 presets: Insta post / square / Story, YouTube thumb /
  banner, FB cover, LinkedIn, WhatsApp DP, marketplace / Amazon, A4 150 / 300 dpi, visiting card; fit contain / cover / inside /
  stretch), crop (box or aspect + gravity), rotate, flip, adjust, auto_enhance, filters (grayscale, sepia, invert, blur, sharpen,
  denoise, pixelate, posterize, vignette, sketch, SCAN = photo of a paper -> flat white page), redact (blur / pixelate / black
  regions), border, pad, round_corners, bg_color, text + watermark (each character drawn from a font that has it: Devanagari,
  Latin, the rupee sign, dots), upscale_local (plain enlargement, said so), convert + compress to a target KB, collage,
  before/after. Every output re-encoded: camera EXIF / GPS never travels. 50 MP input cap, 8192 px side, 12 steps.
- AI (`ai.py`): remove_bg, upscale, remove_object, replace_bg, restyle, restore, colorize, edit. First engine REALLY set up runs and
  is named: rembg (local) / Gemini via photogen / the zoo gateways (`ai.ROUTES`, every id pinned against zoo_catalog.json). No
  engine = says which key to set; upscale alone falls back to a plain enlargement and says "no new detail". A failing engine
  moves to the next, failures reported. Generative edits labelled "AI se bana".
- SAFETY before any engine: photogen.problem + watermark / copyright / photographer's mark removal refused; an AI edit of a file
  named like an Aadhaar / PAN / marksheet / cheque refused (resize / crop / compress of her own ID is fine); body edits on a
  child's picture refused.
- PIPELINE (`run.py`): local steps + at most ONE AI step per photo, validated before anything is paid for; up to 10 photos, 5 for an
  AI step; one bad file never sinks the batch; routine / staff actors usage-gated for AI steps; collage action.
- TESTS `test_imgedit.py` 38. NOT VERIFIED: no AI engine has answered a live call (no key in the sandbox, rembg not installed);
  kie / muapi request shapes read from zoo_catalog.json only. The first real "background hata do" with ZOO_KIE_KEY set is the proof.

## v0.769.0 AUDIO EDIT (owner: "NOW START AUDIO EDITING" - the second wave of the aixploria coverage map, 60 audio-editing tools)

ONE new tool `audio_edit` (registry 622 -> 623) in `server/app/audedit/`. Every edit is LOCAL on the server's own ffmpeg:
no key, no model, no cost, nothing leaves the server, so - unlike image_edit's AI half - all of it is testable and was
tested on real audio.
- `ops.py`: steps -> one ffmpeg filter chain: trim / cut a middle part / fade in-out / volume (dB or %) / normalize to a named
  loudness (podcast -16, social / music -14, audiobook -19, broadcast -23 LUFS, or a number; loudnorm, the file's own sample
  rate given back after loudnorm's internal 192 kHz) / speed 0.25-4 with pitch kept (chained atempo) / pitch +-12 semitones
  (rubberband, else asetrate + atempo) / denoise light-medium-strong (highpass + afftdn) / enhance_voice (highpass, lowpass,
  afftdn, compressor, presence EQ, loudnorm -16) / remove_silence / eq bass-treble / mono / stereo / sample_rate / reverse
  (<= 10 min). Plus convert (6 formats, a video's sound pulled out), join (2-20, crossfade or gap), mix (voice + music looped
  to the voice, quieter, ducked under speech by sidechaincompress, faded out), split (every N s or at times, <= 20 parts),
  loudness report (LUFS, true peak, range, a plain verdict, clipping risk), waveform PNG. Times read as 90 / 1:30 / 1m30s.
  Every output re-encoded with -map_metadata -1 (no artist / comment / phone tags travel). Limits: 200 MB, 2 h, 12 steps,
  ffmpeg time limit scaled to length; a silent video / non-audio file is refused in plain words.
- Tool `agent/audedit_tools.py`: guide | info | run | convert | join | mix | split | waveform; steps checked before any file is
  touched; one bad file never sinks a batch; mix answers with the "only music you have the right to use" line.
- NOT built, said plainly in the guide and prompt: AI vocal / instrument separation, cloning or impersonating a voice,
  transcription (= kaan), new music or speech (= Create studio).
- TESTS `test_audedit.py` 19, all on real ffmpeg with generated audio and video: lengths after trim / cut / speed / join /
  mix / split MEASURED, normalize lands within 1.5 LU of -16 and keeps the sample rate, silence removal shortens the file,
  metadata gone, a video's sound extracted, a silent video refused, every op and all 6 formats run, the tool reached from
  real Hinglish / English asks. Registry pins 622 -> 623.
- NOT VERIFIED live: the VPS's ffmpeg build is assumed to carry the same filters (afftdn, loudnorm, silenceremove,
  sidechaincompress); rubberband falls back to asetrate when missing. The first real voice note cleaned on the VPS is the proof.

## v0.770.0 LANGGRAPH G2 — one run per chat + Stop as state (11 Nov 2026; owner: "GO G2")

Phase G2 of `docs/LANGGRAPH_TURN_PLAN.md` (bug classes 6 and 8), only when `chat_graph` is on (default OFF; with it off no ticket is made and the old path is unchanged).
- NEW `agent/turnrun.py`: per-chat tickets in arrival order (taken when `run_turn` is entered, before any pre-lock work), the live-run registry, the stop flag + event, the inbox-owner check. A turn takes the old `_locks` chat lock only as the oldest ticket and gives the ticket back in a finally - so a later message can no longer overtake an earlier one (proved with the switch off: A with slow pre-lock work ran after B) and the short gap between two runs can no longer let the sweep start a queued row a second time.
- A message during a live run: her own words during her own job still reach it via the steer queue (today's design); wakes / routines / goal rounds / anything else run right after, in order. `turn_inbox.run_owned` drops a second start of a row already owned here; the sweep skips chats with a live or queued ticket. The inbox id is trusted only from that row's own task (background tasks inherit context vars; the G1 leak closed).
- Stop: `santosh.stop` (button, kaamstop, stop words) also sets the run's flag and an event so `_watched` cancels the in-flight model / tool call at once; every graph node checks the flag at its boundary (model node says the usual stopped line via new `_turn_halted`, mid-tool = the usual "Stopped by the owner..." result, ledger row failed/stopped); the inbox row stays 'stopped'; `stopped` rides every checkpoint and `_resumable_snap` refuses it. Messages queued behind a stopped run keep today's behaviour.
- TESTS: NEW `test_g2_turngraph.py` 14; g1 9, g0 11, harness2 15, harness3 17, routines 3, v0657 14, v0664 10, v0649 11 same off and on.
- NOT COVERED: order is by entry into run_turn, not inbox created_at; tickets are one process's memory (inbox + sweep stay the cross-restart net); Stop does not cut other awaits inside a node (finishes, then the boundary ends it); a slow head ticket makes later messages wait; old-path flaws left alone; nothing verified live. Next: G3 done-truth from the ledger.


## v0.771.0 PROOF APPS — the App plan's five proof apps, the whole road on the server (11 Nov 2026; owner: "CONTINUE THE WORK"; built as 0.770, their LANGGRAPH G2 took 0.770.0 - REBASE PROTOCOL, both kept)

The App plan (`docs/COMPLEX_APPS_PLAN.md`) had twelve pillars built (A-L) and its own gate unmet: "a proof app" -
none existed. `server/app/appmaker/proofapps.py` builds the plan's five: **School ERP** (leave workflow Pending ->
Approved by a teacher only, fee register with due = amount - paid and two rules, notices readable by members only),
**Clinic** (a doctor's slot unique, Booked -> Checked in -> Done by the desk only, patient privacy, rating after Done),
**Food delivery** (the phone never prices - amount = qty x rate_of(item) on the server, 1-20 per order, a four-state
kitchen workflow, rating only after Delivered, menu public but kitchen-only), **Multi-vendor marketplace** (vendors
own their listings - another vendor's edit refused, a free listing refused, sales split into 10% commission + payout,
vendors cannot read the register), **Field-service CRM** (private phone, the office assigns, a technician cannot take
another's job, Done requires visit notes, 24 h SLA stored, rating after Done).

Each one: a hand-written naksha (no model, the same every run) -> Pillar K's checker -> every module approved by its
hash and built through the real engines (lists, logic draft, push) with its own generated proof -> the brain applied
through the real logic engine (on her app that stays HER tap; this is the harness's own hidden app) -> hand-written
Pillar J scenarios checked against the app as it now is and played on a twin. Tenant `__proofapps__`, last run's
projects / twins / rows / accounts cleared first. Card: per app modules built, scenarios pass, refusals checked, her
next steps, what is NOT proved; saved to data/proofapps/last.json. `python -m app.appmaker.proofapps [--only <key>]
[--json]`, vps-ops `proof_apps`.

**Found by its first run, all three in the pillars, all fixed:**
- Pillar J (`quality._Run._role`): making a test person staff / admin ends their logins (`webapp.set_role`: "a new
  role = log in again"), and the runner never logged them in again. Since v0.540 every staff / admin step ran SIGNED
  OUT: an allowed step failed, and a "must be refused" step by staff passed for the wrong reason. They log in again now.
- Pillar J: the per-IP signup limit (5 an hour per site) answered the sixth scenario sign-up with 429, so every later
  story failed on nothing to do with her app. The limits are lifted for the twin only (`_unthrottle`) - hidden, test
  rows only, reachable by nobody but the runner. Her real apps keep every limit.
- Pillar K (`architect._steps_for`): a module whose list only staff may write (fees, sales) had its proof walked by a
  plain member, so the module read as failed. The walk signs up as staff for such a list.

**Named by the proof, NOT built:** a customer seeing a row written FOR her by staff (her child's fee row, her
prescription, a vendor's own sales - rows belong to whoever wrote them; needs a gate / pass list), prescriptions and
report cards as PDFs, the family's rider / vendor apps (design + native build), offline-first on a technician's phone.

**NOT VERIFIED:** nothing here ran on a real phone, which is what the plan's gate asks. Payment keys, Firebase,
connector accounts and live tracking stay her next steps and are never counted as passes.

Tests `test_v0771_proof_apps.py` 5 (all five proved, >= 2 real refusals per app + what is not proved named, her
credentials stay next steps, only the hidden tenant touched, a second run starts fresh); test_v0542_naksha 13/13,
test_v0540_jaanch + test_routines 19/19 green with the fixes.

## v0.772.0 VIDEO KIT (built as 0.771.0; their PROOF APPS took 0.771.0, both kept) - exact video edits on the server's ffmpeg (owner: "NOW START VIDEO EDITING")

The third editing desk after IMAGE EDIT (v0.768) and AUDIO EDIT (v0.769). Hoola already had `video_edit` (v0.65, the AI
editor that watches footage and makes a Reel from a brief) and the Edit Desk (a freelance editor's business desk on top of
it). What was missing was the plain, exact edit she can name: "pehle 3 second hatao", "reel size mein karo", "WhatsApp ke
liye chhota karo", "number plate blur karo". NEW `server/app/vidkit/ops.py` + tool `video_kit` (`agent/vidkit_tools.py`),
registry 623 -> 624, family `video_kit` with its own words in `admit.EXTRA_KEYS`, a prompt line beside audio_edit.

- **run** = up to 15 steps turned into ONE ffmpeg filter graph (labelled video segments + a plain audio chain): trim, cut,
  speed (0.25-4, audio pitch kept), reverse (<= 60 s), fade, crop (aspect + position or a box in px / %), reframe (9:16 with
  a soft blurred background, a colour pad, or a crop), resize (presets / width / percent), rotate, flip, colour (brightness /
  contrast / saturation -100..100, gamma), 9 looks, sharpen, grain removal (hqdn3d), light stabilising (deshake), blur_area
  (time window; chroma radius kept inside the half-size planes - found by a test on a small box), text (rendered by the
  image_edit text engine onto a transparent PNG so Hindi + English + the rupee sign all have glyphs), her logo (her photo
  file only), zoom, fps, mute, volume, loudness, sound noise removal. Frame sizes are tracked through the chain; the output
  is even-sized, yuv420p, max 1080p, H.264 + AAC + faststart (or webm / mov), with `-map_metadata -1`.
- **other actions**: info (+ a verdict with tips), convert, compress (to a target MB / whatsapp / email, resolution picked
  from the bitrate, up to 3 tries until it fits, honest refusal when it cannot be watchable), join (any shapes -> the first
  clip's frame, blur / pad fit, xfade + acrossfade), slideshow (photos, gentle zoom, fades, her music), music (looped to the
  video, ducked under speech with sidechaincompress, or replacing silence), captions (ASS script at the video's own pixel
  size via libass with `shaping=complex` - plain SRT burning broke Hindi conjuncts (नमस्ते showed a halant); her SRT /
  SRT text / auto via faster-whisper when installed, else it names the kaan -> SRT route; the .srt comes back too),
  frames / contact sheet, GIF (palettegen, <= 15 s), split (every / at, exact re-encoded cuts), combine (PiP / side by
  side / top-bottom).
- **refused by name**: delogo / remove_watermark / face_swap / deepfake / voice_clone - and the guide says others' videos
  are not downloaded and new AI footage belongs to Create / video_studio.
- Phone videos with rotation metadata are probed with their turned size (ffmpeg auto-rotates on decode).

Tests `server/tests/test_vidkit.py` 26 on real generated video (pixel checks for reframe / crop / flip / text / logo / blur,
lengths for trim / cut / speed / join / crossfade / slideshow, size for compress, metadata gone, 1080p cap, the tool with
batch + one-bad-file + refusals before any file is touched). NOT VERIFIED: auto captions on the VPS (depends on
faster-whisper being installed there); long (30-60 min) videos timed only by the timeout rule, not on her server.


## v0.773.0 HOOLA CODE PHASE 1 (built as 0.768; their IMAGE EDIT took 0.768.0, AUDIO EDIT 0.769.0, LANGGRAPH G2 0.770.0, PROOF APPS 0.771.0, VIDEO KIT 0.772.0 - REBASE PROTOCOL twice, all kept) - its own page, laid out like Claude Code on the web (11 Nov 2026; owner: "GO PHASE 1" on docs/HOOLA_CODE_WEB_PLAN.md, then mid-build "CREATE A SEPERATE PAGE WITH ITS OWN SIDE BAR FOR HOOLA CODE")

Phase 1 of the plan (the shell and the session) plus her mid-build ask. Nothing about HOW Hoola codes changed - same loop, same routes, same taps.
- OWN PAGE: `/console/code` (`static/console/hoolacode.html` + `hoolacode.js`, route `main.hoola_code_page`, same CSP and sign-in token as the console; switch `hoola_code_page` off = 307 to /console/). Only ONE sidebar - the sessions. Every screen has an address (`#/s/<id>`, `#/reviews`, `#/settings`, `#/all`), so Back works and a link opens one session. The console's "Hoola Code" row now opens this page (`v2.js go('code')`); `code.js` is no longer loaded inside the console and the `#v-code` section is gone. Why: inside the console the page had two sidebars and the chat was squeezed to ~450 px on a 1280 laptop.
- LAYOUT (`code.js` rewritten, `.hcd-` rules in v2.css replaced): sessions sidebar 272 px (collapses to a 52 px strip that keeps running / needs-you sessions one click away) / chat column 760 px / right rail 300 px of cards - Changes (files, the PR, proof, CI, own review, security, the next action), Progress (read / change / tests / own check / PR / CI, each read from the real steps - never a made-up bar), Session. The rail hides itself when the page is narrower than 780 px and comes back as an overlay on her click; the same action buttons are on the recap card in the chat, so they are reachable with the rail hidden.
- SESSION: title bar (click the title to rename; menu: Rename, Transcript view Normal / Verbose, Open the PR, Archive, Delete), steps folded into summaries ("Read the repo's rules, read 2 files, searched 1 time"), an edit's diff folded under its row, a failed test run never folded, a finished session folded to "Worked for N - M steps", a recap card in words, the plan / open-PR / merge question as ONE bar above the message box, her queued notes shown with a take-back button, Stop in the message box. Enter sends, Shift + Enter = new line.
- SIDEBAR: New session, Review a pull request, search, groups by repo (default) / status / none and a Show filter (Group and sort menu, remembered in this browser), a "..." menu per row, View all -> All sessions page (Active / Archived tabs, server search, Archive / Unarchive / Delete).
- SERVER (small): `devsahayak_tasks.title` (her own name; never the PR title on GitHub) + `archived_at` (both nullable, added by the column self-heal); `service.rename / archive / delete_task / drop_note`, `tasks(archived=, q_text=)`; routes PATCH `/tasks/{id}` {title | archived}, DELETE `/tasks/{id}` (the row + its steps; an open PR and its branch stay; a waiting merge card goes stale; refused while it works), DELETE `/tasks/{id}/note/{i}` (a queued note comes back as text; refused once Hoola has read it), GET `/tasks?archived=1&q=`. Task views carry `archived` and `notes` (her queued words).
- TWO BUGS FIXED: (1) every 2 s refresh rebuilt the whole page with innerHTML, so a half-typed note was wiped and the box lost focus - the session is now mounted ONCE and `paint()` repaints only the regions whose HTML changed; the message box is never repainted; clicks go through ONE listener on the root. (2) the working mark was a rotating ring (banned by CRISP TEXT, v0.256) - now a still dot with a soft pulse of shadow.
- HOME: one box + Send, and under it repo / kind of work / issue number. The mode, model and branch pickers of the design are Phase 3.
- PROOF: `tests/test_v0768_hoola_code_shell.py` 8 - rename / archive / search (with % and _ as plain characters) / delete / another tenant refused; a running session not archived or deleted, a queued note taken back; the routes; and FOUR walks in a real browser against an API whose answers change between polls: typing survives a new step arriving (text, focus and the fold she opened all kept - this fails on the v0.748 page), steps fold, no rotating ring, a note comes back into the box; the layout at 1280 px (rail 300, chat >= 600, nothing off-screen), rail hide / show / overlay, sidebar collapse, Verbose, rename; the page on its own address with one sidebar, hash routes, Back, a deep link; the switch. `test_v0748` browser walk updated to the new page. Screenshots were looked at before shipping.
- NOT DONE / NOT VERIFIED: no live GitHub repo has run through the new page yet; the Changes pane with line comments, Create PR on the card, the question dialog = Phase 2; mode / model / branch pickers, attachments = Phase 3; Terminal / Files / a continuing conversation = Phase 4; steps still arrive by a 2 s poll; the phone screen is unchanged; "Merge when ready" stays her tap (decision 1 of the plan, not yet answered).

## v0.774.0 HOOLA INTERACTIVE, THE WHOLE PRODUCT (built as 0.772) — its own page, its own sidebar, twelve pages (owner: "GO - BUILD IT INTO CONSOLE END TO END")

After the HeyGen research (`docs/research/heygen/`), the plan (`docs/HOOLA_INTERACTIVE_CONSOLE_PLAN.md`) and the
clickable twelve-page design she approved. This is the build of that design into the real console.

**The page.** `static/console/interactive.js` (rewritten); its styles are the `#hiRoot` block in `v2.css` (the console keeps ONE stylesheet - a test holds that). Hoola Interactive opens as a
full-screen overlay `#hiRoot` with its own icon rail: Home · Avatars · Voices · Studio · Templates · Brand · Translate ·
Live · Apps · Projects · Developers · Settings, and "Console" to go back to the chat (`back: () => go('chat')` from
v2.js; `leave()` hides it). Console tokens only, so Light / Dark / System follow; the old `.hiv` block left v2.css.
Sub-views: editor, making (real steps), video, avatar, proofread. One click / input / change / submit listener on the
root; her text always through `esc()`.

**Studio** is the script-first editor: script on the left (one block per scene, move / remove / add), a layout
preview canvas with the scene strip, and tools on the right (Look · Avatar · Voice · Video · Brand). It saves through
the same `/api/interactive/studio/project` as v0.747, shows what blocks the make in her words, and Generate opens a
box with scenes, estimated length, size and sound before she taps. Nothing about the film pipeline changed.

**NEW `interactive/hub.py` + `/api/interactive/hub/*` (17 routes)** — everything around the film that needs no GPU:
- `brand` — name, closing line, colour (`#RRGGBB` or refused). New videos start with them; `studio.spec_for` now
  passes the colour into the composition (`_brand_color`), so it is drawn, not just stored.
- `glossary` — "keep exactly as written" or "always translate as X in language L".
- `templates` — six starters that state no price or date (a test checks they contain no digit) + her own, saved from
  any project. Blanks are `{name}`-style; `template_use` fills them ONLY from her values and refuses a missing one by
  name. Her values become the project's `facts`, so her numbers are trusted the same way her edits are.
- `batch` — up to 20 scripts → one draft each, cut into scenes at sentence ends by code (no model call, no rewrite).
- `personalise` — a project that says `{name}` × up to 20 names → a draft each. Nothing is sent from here.
- `translate` — a Hoola-made video into another language as a NEW draft: one model call for the words (spoken lines
  and the words on screen), then CODE compares the digits of every line with its source and applies the glossary; a
  line that fails is flagged (`tr[i].flag`) with the source kept beside it; a wrong line count refuses. The Proofread
  page edits the lines and opens the draft in Studio.
- `trash` / `restore` / `empty` — delete keeps the project and its video file for 30 days; restore brings both back;
  a restored "ready" project whose file is gone becomes a draft instead of a dead player.
- `duplicate`, `brains` (what a live avatar may know: name, facts ≥ 20 chars, opening line, http(s) links only),
  `usage` (videos and minutes this month, read from the videos' own records), `voice` (a sample line; 503 with the
  reason when the engine is off), `overview` (one call for the whole page).
- `status().connected` — the honest switchboard. True today: video, photo avatar, templates, translate (words);
  voice when the engine is set up. False and printed on the page as "Not connected on this server yet": twin,
  AI-made faces, voice clone, lip-matched dubbing of outside videos, the live stream, the public API.

**Not built, said on the page too:** real tables (still one JSON per tenant under `studio._LOCK` — plan phase I1),
jobs that survive a restart, a rupee meter, share links and insights, an AI mark inside the file, pronunciation rules,
logo and fonts in the brand kit, every GPU-backed app (talking photo, slides, link, podcast, series, clips, cleanup,
lip sync, upscale), the Developers API. The Apps page shows those as "Not connected yet" with the button disabled.

**Tests.** NEW `test_v0772_interactive_hub.py` (10): brand colour reaches the spec; a template takes only her values
and names what is missing; own template + many names; batch cuts by code; a translation is checked not trusted (a
changed number, a broken glossary rule, a missing line); trash keeps the file and the 30 days are real; usage counts
this month only and status names what is off; brains; routes locked + switched; the page is wired with no sample
data. `test_v0747`'s browser test rewritten to the new page: twelve rail items, every page opened with no script
error and no sideways scroll, her `<b>` title shown as text, the unset voice engine said, a missing number disabling
Generate, Console hiding the page. It runs in real Chromium with
`HOOLA_CHROMIUM=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome` (the Python Playwright's own browser build is
not installed in the sandbox, so without that variable it skips).

**NOT VERIFIED, said plainly:** not opened by her yet; no video has been made through the new page on the VPS
(the make path is the unchanged v0.747 one); `translate` has only run against scripted model answers, never the
live model; the phone-width layout was checked in the design prototype, not in the console build.

REBASE PROTOCOL: built as 0.772.0; main took 0.772 and 0.773 meanwhile — merged, both kept, shipped as 0.774.0
(pubspec 0.774.0+773, console stamps 0.774.0, pins swept). Mera PC freeze respected: nothing in `server/app/pc/`,
`desktop/`, `lib/` touched. Server + console only; old APKs keep working.

## v0.775.0 LANGGRAPH G3 — done judged from what the tools really did + one check node (11 Nov 2026; owner: "GO G3")

Phase G3 of `docs/LANGGRAPH_TURN_PLAN.md` (bug classes 3 false done, 4 turn ends on a promise), only when `chat_graph` is on (default OFF; with it off no judge is made and the old path is unchanged - the goal / promise nudges and the claim parts of _pakka_check / _plain_check were lifted into shared functions with the same bodies).
- NEW `agent/turnfacts.py`: after each tools step one fact per tool_use {id, tool, step, effect, ledger, object, error}; effect = did / card / read (draftcheck.effect on an ok result) or ambiguous (G1 restart / MAY ALREADY HAVE RUN / a timed-out doing tool) / stopped (G2) / failed (error or ok False) / skipped (breaker). draftcheck still FINDS the claim sentences; the VERDICT comes from the facts of the tools that could make it true: true / card / failed / unknown / stopped / wrong (done for another address than the claim names) / none. Ambiguous and stopped are never excused (except a later successful read of the same kind - the model checked); earlier rounds' work excuses via the harness event log as before.
- The check node: one `Judge` takes every send-back decision (false claim once then the honest note, missed reminder, all tools failed, the self-check in non-plain mode, open kaam_plan step 8, promise with no action 2, max_tokens continue 8 - new cap) with a total of 16 a turn; every decision {kind, why, back, step, claims} rides the checkpoint, spends in `nudges`; a stopped run is never sent back. Old nudge texts reused + NUDGE_FAILED / NUDGE_UNKNOWN / NUDGE_WRONG and SAID_UNKNOWN / SAID_FAILED. An unknown doing step makes the outcome partial, never done.
- TESTS: NEW `test_g3_turngraph.py` 25; the false-done suites (draft_jaanch, v0287, v0654, v0663, v0727, v0311) + g0-g2 + harness2/3 + routines + v0657 + v0649 same off and on (v0311 2 reds + v0667 1 red also fail at v0.770).
- STILL REGEX: finding claim sentences, mapping a claim to its tool family, effect()'s read / card patterns, the past-report excuses, the promise detectors, the all-failed done note. NOT COVERED: plan steps ticked done are still believed (verify.py gate unchanged); facts are per turn (earlier rounds via the event log - G4); 'sent to Ravi' vs an email-only object not matched; nothing verified live. Next: G4 long jobs on the same thread.



## v0.776.0 HOOLA CODE PHASE 2 (built as 0.774; their HOOLA INTERACTIVE took 0.774.0 and LANGGRAPH G3 0.775.0 - REBASE PROTOCOL twice, all kept) - review and the pull request (11 Nov 2026; owner: "GO PHASE 2" on docs/HOOLA_CODE_WEB_PLAN.md)

Phase 2 of the plan, on the page built in v0.773 (`/console/code`). How Hoola codes is unchanged; this is how she REVIEWS what it did and steers the pull request.
- CHANGES PANE (`code.js` `paneHTML` / `drawPane` / `openPane`, `.hcd-pane` in v2.css): opens BESIDE the chat from the Changes button, a file on the Changes card, or "Show in diff" - never a separate page. File list + one file's diff with old / new line numbers (`parseDiff`), "new file" mark, the file's reason, files over 600 lines capped with "Show all". While Hoola is still working it shows the edits so far from the steps (no line numbers yet, and says so). The rail hides while the pane is open; on a window under ~1100 px the sessions sidebar steps aside to its 52 px strip and comes back when the pane closes; under 700 px the pane covers the chat. Task views carry `file_diffs` (per file: path, added, removed, new, why, diff).
- COMPARE AGAINST: once the branch is pushed, a picker of the repo's branches (never its own) shows this branch against any of them as GitHub computes it - `gh.compare` / `gh.branches`, `service.compare` / `branches`, GET `/tasks/{id}/compare?base=`, GET `/branches`. Patches are scrubbed for keys; a binary / oversized file says so. Before a push there is only the prepared change against its base commit, and the server says that plainly.
- COMMENTS ON LINES: hover a line, "+", type, Enter (Esc cancels). Comments QUEUE - shown under their line and as "N comments will go with your next message" above the box - and ride her next message: `revise(..., comments=)` and `add_note(..., comments=)` turn them into ONE `<her_comments_on_the_diff>` block (file, line, the line itself, her words; at most 20; each cleaned and secret-scrubbed like any text of hers). Comments alone are a message. A removed line has no new line number, so it takes no comment. THE PANE IS NEVER REPAINTED WHILE SHE IS WRITING A COMMENT (the Phase 1 rule, kept).
- HER ANSWER CONTINUES THE SESSION: when Hoola answered a vague ask with ONE question and changed nothing (v0.371), the view carries `question`; the page asks it above the box, the session counts as "needs you", and her answer goes to POST `/tasks/{id}/answer` -> `service.answer` adds "You asked / Her answer" to her ask and runs the SAME session again in the background. An explanation that happens to end in "?" is not a question to her.
- OWN REVIEW AS A CARD: each open point with its severity and file:line, "Show in diff" (opens the pane at that file), "Fix this one", and "Fix all N" - each is an ordinary change request on the same pull request.
- PULL REQUEST MENU (the "..." on the Changes card): "Fix a red CI run by itself" on / off for THIS pull request (`devsahayak_tasks.auto_fix`, nullable; False = `_ci_step` tells her and changes nothing, no fix round), Copy the checkout command, Open on GitHub, Check CI again. PATCH `/tasks/{id}` takes `auto_fix`.
- ARCHIVE AFTER MERGE: setting `archive_after_merge` (`devsahayak_settings`, nullable, off by default; a switch on the Settings screen) - a session whose PR is merged leaves the list by itself (`service._merged`), still under View all > Archived.
- SMALL FIXES: a session waiting on her CI showed "This session is finished" - it now says it is waiting and what happens on a failure, with "Check now"; a button stays usable after its action; the Progress card no longer shows earlier stages as not done when a later one is (old sessions with no stored steps).
- NOT CHANGED ON PURPOSE: Merge is still her tap (decision 1 of the plan is unanswered, so no "merge when ready"); opening the PR is the existing tap with its hash; a draft PR is still decided by the CI loop and her setting, not per click.
- PROOF: `tests/test_v0774_hoola_code_review.py` 10 - comments reach the model in their block (a key in a comment is scrubbed, one without a file dropped, 20 at most), a note while it works carries them, her answer restarts the same session with her words in the ask and the transcript, Auto-fix off = told and nothing pushed, a merged session archives itself only when she asked, compare + branches + the routes (a key in another branch's patch not shown), nothing pushed = nothing to compare; and THREE walks in a real browser: the pane beside the chat with exact old / new line numbers, a comment written while a refresh lands (text and focus kept), Esc cancels, two comments ride one message with their file / line / code, Compare against; the review card, the PR menu (auto-fix off, the checkout command really on the clipboard), her answer; the pane on a 1000 px window (sidebar steps aside and comes back, nothing overlaps). Screenshots were looked at.
- NOT DONE / NOT VERIFIED: no live GitHub repo has run through it - `compare` and `branches` are built from GitHub's documented shapes and a fake; split (side-by-side) diff view is not built (Claude Code's docs do not describe one either); a mid-work question with choices (an `ask_her` tool) waits for Phase 4, where a session becomes a conversation; comments on a removed line and multi-line comments are not built; reviewers' comments on GitHub are still not auto-fixed (Phase 5).

## v0.777.0 CHAT JAISA (built as 0.771; L1 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L1"; 0.771-0.776 taken by other sessions meanwhile - REBASE PROTOCOL twice, all kept)
The Web Studio site chat now works like Lovable's:
- LIVE: `webstudio.html` loads `stream.js`; the per-site thread opens `/api/conversations/{id}/events?live=1` (HoolaStream) - reply_start /
  delta / reply_end go through HoolaStream.Pacer into HoolaMD.Live({soft:true}) so each new word fades in out of a soft focus; step / think /
  typing / message events drive the work card. Polling stays as the fallback (1.5 s when the stream is down, 4 s safety read while a turn runs).
- THINKING: a think event shows a shimmering "Thinking..." (1.8 s sweep); the answer then says "Thought for Ns" (kept per answer, keyed by its words).
- VERBS: a running step reads present tense, a finished one past tense (`PAST` map in webstudio.js; a test proves every first -ing word of
  agent/labels_en.py is covered). Applies to the site build activity steps too (test_v0649 pin moved to "Planned three designs").
- COST: `usage.turn_meter` (a TURN contextvar beside the run meter) counts every model call of a chat turn; `santosh.run_turn` writes one
  `turn_costs` row (app/turncost.py, registered in init_db + ensure_table, newest 400 per chat kept; switch `chat_turn_cost`);
  GET /api/conversations/{id}/costs gives start / end / calls / usd / inr. The turn head reads "Thought for 3s · Worked for 42s · 5 steps · Rs 3.10".
- DETAILS: a button per answer opens VIEW 'details' in the right pane - Timeline (each step, its clock time and duration) and Changes (versions
  made by that answer, each with Before / after through the existing compare view).
- QUEUE + STOP: Stop on the work card (POST /stop); a message sent while Hoola works waits greyed at the bottom ("Runs after this step",
  Interrupt) and moves into the thread when its turn starts.
- ATTACH: paperclip, drag-drop and pasted pictures upload through /api/conversations/{id}/files; a paste over 1,500 chars becomes a chip
  ("Pasted text · 121 lines") sent as a .txt file; files ride the message (`files`).
- SCROLL: her new message scrolls to the top of the view; the stream never yanks her down; "Latest" appears only after she scrolls up.
- Found while testing: `.jump / .tray / .livebox` had display rules that beat the `hidden` attribute (the Latest button covered a chip) - fixed;
  the thinking time was lost when a queued message moved in right after an answer - now kept per answer.
Tests: test_v0777_chat_jaisa.py (5, incl. a Playwright walk: thinking shimmer, queued bubble, paste chip, soft-fade spans, past tense,
Rs line, Details timeline; 7 repeat runs green) + the older Studio suites green (v0649 / v0655 / v0663 / v0664 / v0667 / v0669 / v0671 / v0707,
routines, v0657, v0475). NOT VERIFIED live: the first real Studio turn on her server (the browser walk uses a scripted turn).


## v0.778.0 HOOLA FLOW LIKE WISPR FLOW (owner: "NOW SAME FOR HOOLA FLOW --- CHECK DESIGN AND MAKE IT SAME AS WISPERFLOW")

"Same" = what Hoola Code got: its own page with its own sidebar. Hoola Flow (v0.751, the Kaan pack as a console page) now
lives at `/console/flow` (`flowapp.html` + `flowapp.js` boot like `hoolacode.js`, styles in `flow.css`, route behind
`flow_page`, microphone allowed for that page only); the console's Hoola Flow row opens it (`go('flow')` -> location).

The design follows Wispr Flow's desktop hub (docs.wisprflow.ai: sidebar Home / Dictionary / Snippets / Style + Settings, a
Home with "Welcome back" and usage stats, light theme default with dark / system, hold-a-key dictation with the Flow bar):
- **Sidebar** - Home / Dictionary / Snippets / Style, then Transcribe (A file to text, Live captions), a tip card, Settings and
  Back to Hoola. Hash routes `#/`, `#/dictionary`, `#/snippets`, `#/style`, `#/files`, `#/live`, `#/settings`, `#/t/<id>`.
- **Home** - serif "Welcome back, <first name>" (from /api/me), a pill with the day streak, words and WPM counted from her
  last 100 transcripts (WPM from dictations of 20 s or more; the pill says where the numbers come from), the dictate card,
  history grouped Today / Yesterday / date with the time in its own column, Copy / Open on hover, search.
- **The Flow bar** - a dark pill at the bottom of every page. Click, or hold Space: release after 0.45 s = done
  (push-to-talk); a tap keeps listening and Space again (or the tick) finishes; Esc cancels and the transcript the server
  made is deleted. While listening: waveform, clock, her words so far above the pill. When done the text is rendered in
  her Style, copied to the clipboard and the new row is highlighted at the top of the history.
- **Dictionary** (tabs All / Listening hints / Spelling fixes) and **Snippets** ("say a short cue, Hoola writes the whole
  text") share the existing word list; a snippet is a row with `note: "snippet"` (the field existed), 120 chars max.
- **Style** - As said / Clean / Notes / Social as cards with a preview of the same spoken line; honest about what each does
  (Clean only tidies, Notes / Social only pick). Kept in this browser (`hoola.flow.style`).
- Files, live captions, one transcript and settings keep their v0.751 behaviour in the new look. "Put in the Hoola chat"
  hands the text to the console through `localStorage['hoola.flow.toChat']`; the console puts it in the chat box of the
  chat that opens (never sends).
- Found on the way: `studio.js` threw on any window resize before the Create Studio had been opened (R was null) - guarded.

Tests: `test_v0751_hoola_flow.py` browser walk rewritten for the page (console row -> page, welcome + stats, day groups,
search, transcript + styles, dictionary / snippet adds with the exact POST bodies, Style saved, settings, live, files,
the Flow bar with a fake microphone: hold Space -> waveform + words -> release -> her Style used + clipboard + toast, tap +
Esc = cancelled, the chat-box handoff, phone width with no sideways scroll) + a route test. NOT VERIFIED: a real
microphone on her server; Wispr's exact pixel values (built from its documented layout and public screenshots).


## v0.779.0 HOOLA CODE PHASE 3 (built as 0.777; their CHAT JAISA took 0.777.0 and HOOLA FLOW 0.778.0 - REBASE PROTOCOL twice, all kept) - the composer (11 Nov 2026; owner: "GO PHASE 3" on docs/HOOLA_CODE_WEB_PLAN.md)

Phase 3 of the plan: how a session is STARTED on `/console/code`. The form (kind select, issue box) is gone; it is one box and one row, like Claude Code on the web.
- ONE BOX: her words, "+" (bottom left) and Send (bottom right); Enter starts, Shift + Enter is a new line. What she attached sits in a tray inside the box (a thumbnail for a picture, name + size, a remove button each).
- ONE ROW under it, left to right: repo (short name, the full one on hover), BRANCH TO WORK FROM, MODE, then on the right MODEL + EFFORT and the USAGE ring. It stays one line at normal widths and wraps on a narrow window.
- BRANCH: `start_bg(base=)` - default = the repo's own default branch; another branch is checked on GitHub before the row is made ("was not found"), a `hoola/*` work branch is refused. Hoola reads from it, and the pull request is opened AGAINST it. The page lists the repo's branches (GET `/branches`, Phase 2) without Hoola's own.
- MODE for this session (`devsahayak_tasks.mode`, nullable): `ask` = the prepared change waits for her tap to open the PR; `auto` = it does not on a private repo, even when her setting says ask (a PUBLIC repo still always asks); `plan` = a read-only plan pass first that WAITS for her yes, whatever the size of the job (v0.451 only planned standard / large ones). No mode = her setting, as before. The picker starts on her setting.
- MODEL + EFFORT for this session (`tasks.model`, `tasks.effort`): the loop's brain is called with (system, messages, tools) only, so the pick is a thread-local (`loop.PICK`, set by `loop.pick(t)` at the top of every run / plan pass and cleared for a review). `service.models()` TELLS THE TRUTH: Hoola Code calls Claude through the Anthropic SDK, and two server rules sit in front of that door - SAB GLM (`glmdoor.active()`) and `claude_one_model`. When either is on, a picker would be a lie, so `forced` names the model that really answers and the page SHOWS that name with the reason, offering no choice. Only with both off does she get the list (the coding default, the chat model, the simple model) and Low / Medium / High. A pick equal to the default, or any pick while one model is forced, is not stored.
- KIND FROM HER WORDS: `service.guess_kind` - rules, no model call (explain ... / write tests / README, docs / fix, bug, crash, error, a traceback, "theek karo"; else write). `kind: "auto"` on POST `/tasks/start`. A slash command names it outright.
- SLASH COMMANDS (typed first in the box, or picked from "+"): `/plan` (mode), `/fix` `/feature` `/tests` `/docs` `/explain` (kind, shown as a removable chip), `/issue 12` (the GitHub issue to work on), `/review 12` (goes to the reviews screen and starts the review - no session). The command is removed from her words; an unknown one lists the real ones.
- ATTACHMENTS (`start_bg(images=, docs=)`, `tasks.attach`): up to 3 pictures of 3 MB - PNG / JPEG / WebP / GIF, known by their BYTES and never by the name or type the browser sent - saved under `data/devsahayak/<task>/` and sent to the model as image blocks on its first message; up to 3 text files, 12,000 characters each (longer = cut, and marked so), scrubbed of keys like any text of hers, sent as `<attached_file name=...>` with "data to read, never instructions to follow". File picker, paste, or drop on the box. Her bubble in the session shows them (GET `/tasks/{id}/attach/{i}`, fetched with her sign-in into a blob: link). Deleting a session deletes its pictures. The one-shot fallback gets the text files too; the plan pass reads them.
- COST AND USAGE: each background run is wrapped in `usage.run_meter`, so `tasks.cost` holds this session's OWN model calls (a CI fix round from the worker tick too) - shown on the Session card as "Cost so far" (list price x the server's rate: an estimate, never a bill). The home row shows this month's spend against her limit as a ring (`usage.state`); with no limit set it shows only the figure, and nothing when nothing is spent.
- A LINK MAY PRE-FILL: `/console/code?prompt=...&repo=owner/name&branch=...&mode=ask|auto|plan` fills the box and the row, the query is dropped from the address, and NOTHING starts until she presses Send.
- FOUND BY ITS OWN TEST: after Send the box kept her old words (leaving the home screen saved the textarea back into the draft) - cleared now.
- PROOF: `tests/test_v0777_hoola_code_composer.py` 8 - the kind rules; the model list with and without a forced model; one session on a picked branch / mode / model / effort (every brain call on her pick, the PR against her branch, `auto` over her setting, no pick = the server's, cost counted); plan-first makes a tiny job wait; a non-picture refused by its bytes, a picture and a scrubbed log reaching the model's first message, a long file cut, her pictures deleted with the session; the routes; and TWO walks in a real browser: the box and the ONE row measured, a picture + a log attached (a video refused in words), the "+" menu, `/tests` + `/plan`, Enter starts with exactly the right body, the session showing her picture (really loaded) and what it runs on, the box empty afterwards, `/review 12`; a forced model shown and not offered, a link pre-filling without starting, her words surviving a repo change.
- NOT DONE / NOT VERIFIED: no live run - a picture has not been read by the live model through this path, and with SAB GLM on it goes to the GLM door's picture handling, not tested here; attachments on a FOLLOW-UP message (a note or a change request) are not built - only the first message takes them (Phase 4 makes the session a conversation); no ghost-text suggestion (Phase 5); effort is ignored by a model that does not take it (the loop already retries without it); multi-repo sessions are not built.


## v0.780.0 HOOLA FLOW REDRAWN (owner: "YOU HAVE MAKE IT VERY STALE AND OLD DESIGN --- FIX THIS PROPERLY -- TEXT , BUTTON .. EVERY DESIGN --- LOOKS MESSY")

v0.778's page copied Wispr's warm paper + serif look and read as dated. `flow.css` rewritten: Schibsted Grotesk only (h1 30 / 700
/ -0.032em, body 15), white surfaces with hairlines and soft shadows, ONE accent (violet) and the house glow only in the hero and
banners, every control on one scale (32 / 38 / 46 px; radius 10 / 12), spacing on 4 / 8 / 12 / 16 / 24. Home = greeting + stats
pill, a hero ("Just speak. Hoola writes it.") with a big round mic button and key hints, three quick cards, history lists. Sidebar =
logo, nav with accent icons on the active row, a Shortcuts card, Settings / Back, a profile chip. Tabs are segmented controls, meta
are chips, the toast is a dark pill at the top, selects have a chevron, focus rings are violet. Dark mode redrawn. The page no
longer loads v2.css. Bug found by looking at the screenshots: `.wf p{margin:0}` outranked every class margin - now `:where()`.
Checked by eye: home, transcript, dictionary, snippets, style, files, settings, recording, phone, dark.

## v0.781.0 CONNECTORS PAGE (built as 0.776; their HOOLA CODE PHASE 2 took 0.776.0, CHAT JAISA 0.777.0, HOOLA FLOW 0.778.0, HOOLA CODE PHASE 3 0.779.0 and HOOLA FLOW REDRAWN 0.780.0 - REBASE PROTOCOL twice, all kept)
Owner: "LETS WORK ON CONNECTOR IN WEB CONSOLE --- CURRENTLY IT IS ONLY AT APP SIDE --- CHECK THIS FIRST" -> "GO BUILD FULL CONNECTORS
PAGE -- MAKE IT MORE PREMIUM, PROFESSIONAL AND ADVANCE AND A SHORT 1 LINER BELOW EVERY CONNECTOR -- AS WE USE COMPOISO FOR THIS".
- The check: the phone had the whole Connect tab (bazar_screen / mcp_screen / publicapis_screen); the console had only approval cards, the Google
  connect button, Systems and app-backend connectors. Every server route already existed; the gap was the page - plus ONE server defect: both
  sign-in callbacks (`/bazar/link/callback`, `/bazar/composio/callback`) always jumped to `santosh://bazar?linked=1`, a dead page on a computer.
- NEW `static/console/connectors.js` (HoolaConnectors, sidebar row "Connectors" after Tools, account menu + command palette, view #v-connectors):
  hero with Connected / Apps available / app actions this month (Composio cap meter); tabs Apps | Connected | MCP servers | Built in | Public APIs |
  Limits & safety (last tab remembered). Apps = Composio's catalogue: debounced search (results-only redraw, typing never lost), categories with
  counts, All / Connected / Ready to connect, 48 a page + Show more, cards (logo or initial tile, name, category, status pill, ONE-LINE description,
  actions count, Connect / Add key / Manage), a drawer (full text, safety facts, "via Composio", Remove, try lines that go into the composer and are
  never sent by themselves). Connect = a sign-in window opened inside the click (no popup blocker), the address set after the server answers; key
  apps = a modal built from Composio's own fields. MCP servers = her own servers (tools on / off / ask first with locked tools respected, change
  key, remove, sign in), "Add a server" by https address, the 68 official servers by category (sign-in, API key incl. GitHub read-only / Supabase
  project + read-only, personal address with Zoho's steps), the worldwide directory (one-tap with keys / caution flow; says plainly when the
  server has it off). Built in = linked accounts (link / unlink) + the plugin catalogue grouped and searchable ("Ask Hoola" prefills; phone-only
  UPI / cab apps say "On your phone"). Public APIs = search / category / key filter, add / remove a key (sealed). Limits & safety = spending
  limits + delivery details (PUT /api/bazar/settings) and the house safety rules. A list that fails to load shows its error + Try again, never
  an empty list. Styles = the `.cx-` block at the end of v2.css (tokens, light + dark, CRISP TEXT: no spinner rings, no blur; reduced motion off).
- NEW `bazar/oneline.py`: the short line under every connector, made on the server - first sentence, "<App> is a ..." dropped, word-boundary cut
  under 90 characters with an ellipsis, links / markdown removed, honest fallback. `line` added to Composio apps, featured servers, her MCP
  servers, linked accounts, the plugin catalogue and directory results (the full `does` stays).
- NEW `bazar/donepage.py`: one sign-in done page (English, escaped, light / dark). The console writes `hoola.connect.pending` before opening the
  sign-in; the done page (same origin) sees it, tells the console through BroadcastChannel('hoola-connect') + a localStorage `hoola.connect.done`
  write, and closes itself; with no marker (the phone's browser) it keeps the old santosh:// deep link. The MCP redirect_uri and the Composio
  callback URL are unchanged.
- Found while building: this checkout folder is the VPS deploy copy - every deploy runs `git reset --hard origin/main` there, which wiped
  uncommitted edits mid-session; the work moved to a separate git worktree. Work in a worktree, never in ~/santosh_app.
Tests: test_v0781_connectors_page.py (12: one-liner rules, `line` on Composio / featured / catalogue / connections, done page web + phone +
escaping, both callbacks English, a key never echoed, console wiring, the page calls ONLY routes the server has (FastAPI 0.14x lazy routers
walked), no inline handlers, a Playwright walk at 1280 + 390 px: cards with their line, initial tiles, no sideways scroll, key modal, sign-in
window -> done page -> the console toast, drawer try line into the composer, every tab) + test_bazar / v0276 composio / custom_mcp / bazar_p1 /
v0303 / v116 handoff / v0475 green (111). Console stamps 27 -> 28. NOT VERIFIED live: a real Composio or MCP sign-in started from the console
(the done-page hand-off assumes PUBLIC_BASE_URL is the same host as the console - true on hoola.ainewtika.com).

## v0.782.0 TEEN MODE (built as 0.778; L2 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L2"; 0.778-0.781 taken meanwhile - REBASE PROTOCOL, all kept)
Build / Plan / Chat in the Web Studio chat, like Lovable - and enforced on the server, not only asked of the model:
- MODES: the composer has Build | Plan | Chat (Alt+P cycles; a message starting /plan, /chat or /build runs in that mode once). Every
  Studio message carries `[Web console mode: build|plan|chat]` (inside her message, so an inbox re-run after a restart keeps it).
- SERVER: `agent/turnmode.py` - `begin()` reads the mode + the site id at the start of `_run_turn`; `santosh._run_tool` asks
  `allowed(tool)` before ANY tool runs: in Plan / Chat every changing tool is refused (ToolError with what to do instead); reads
  (draftcheck._is_read) and page readers (web_fetch, scrape_page, reach, duniya, api_box, jharokha, open_website) stay open. The mode's
  rules + her site instructions join the turn's hint (both prompt paths). Switches `studio_modes` (on), `studio_chat_model` ("" = same).
- PLANS: a Plan answer becomes a numbered version on the site (`site/plans.py`, table `site_docs`, registered + ensure_table; the same text
  twice = one version; one approved at a time, the older -> superseded). Routes: GET/POST /api/sites/{id}/plans,
  POST /api/sites/{id}/plans/{v}/approve|skip|draft (her site only, 404 otherwise). In the chat: a plan card (v1, Open plan / Approve / Skip);
  the Plan view in the right pane: versions (older / newer), Edit (her edit = a new version, source 'her'), Comment on selection (Hoola
  rewrites that part in Plan mode = a new version), Approve -> the plan is approved and ONE Build message carries the approved text (one
  line, so her bubble shows only "Build the approved plan (vN)."), Skip. A plan's list right under its heading renders as a list.
- CHAT: a Chat answer ending with `[[start-building: ...]]` shows a Start building card (uses money; Build sends that line in Build mode,
  Skip hides it); the marker never shows, even while streaming.
- INSTRUCTIONS: Settings > Instructions for Hoola (10,000 characters, GET/PUT /api/sites/{id}/instructions), read on every Studio turn for
  this site in every mode.
- Pins moved on purpose: test_v0649 Plan-hint wording; test_v0777 reduced-motion check now reads every reduced-motion block.
Tests: test_v0782_teen_mode.py (7: the mode line + guard, _run_tool refusing a change before dispatch, plan versions / status / instructions,
routes hers-only, the turn hint, source wiring, a Playwright walk: Plan -> card v1 -> Open -> Edit -> v2 -> Approve -> one Build message with
the approved text; Chat -> Start building -> Build; Alt+P; instructions saved). Older Studio + agent suites green (131).
NOT VERIFIED live: a real model's Plan / Chat answers on her server (the walk uses scripted replies).

## v0.783.0 LANGGRAPH G4 — a long job continues on one thread (11 Nov 2026; owner: "GO G4")

Phase G4 of `docs/LANGGRAPH_TURN_PLAN.md` (bug classes 1 + 5), only when `chat_graph` is on (default OFF; old goal rounds unchanged).
- One job thread `"<conv>:job-<goal id>"`; the graph gains a `carry` node compiled with interrupt_before. A turn of her job (her words / a round / a routine's job - never a wake or a call's quick brain turn) that reaches finish with the goal still open routes to carry and stops there, checkpointed; `_park` copies that checkpoint onto the job thread (next node kept, the job's earlier facts + counters merged, ledger rows moved - NEW `toolledger.move`), the source thread deleted.
- The goal round (`goal.maybe_continue` -> `_schedule` -> `_continuation`) stays the scheduler - her authority (v0.222), rounds / minutes limits and the "Shall I carry on?" ask, waits on her / on a job, Stop - but sets `turngraph.JOB_RUN` so `run_steps` resumes the job thread with ainvoke(None): at carry = a new segment (fresh step budget, goal breaker, max tokens, G3 nudge budget; facts carried; messages = the thread's own + rows saved since, so memory is not re-read), elsewhere = the cut segment continues from its last finished node. A stale job (goal gone) does nothing and the thread is deleted.
- Restart between segments: `recover_tick` schedules the round, it runs the next segment (no RESUME_NOTE, nothing redone). Restart mid-tool: the cut step resumes, G1 ledger rules (done reused, interrupted read re-run, interrupted send ambiguous). Deadline cut: `santosh` timeout branch calls `park_cut`, she sees the round-timeout text, the next round continues from the cut step. `resume_tick` / `recover_tick` skip chats G2 shows busy. Graph-only fix in `goal._schedule`: a round's own pending entry no longer blocks scheduling the next (old path untouched).
- Cleanup: END deletes its thread and the job threads of this chat's finished / failed / stopped goals; a blocked goal keeps its thread for her yes.
- TESTS: NEW `test_g4_turngraph.py` 9; g0-g3, v0186 long goal, v0226 / v0228 long jobs, v0443 done verified, v0222 goal hers, harness2/3, routines, v0657, v0649, v0727 same off and on.
- NOT COVERED: facts from her in-between turn reach the job only if that turn ends at a boundary; that turn can replace a cut job checkpoint (the cut tool is then not resumed); a 10-min goal recovery before the G1 sweep runs fresh from history; no age-based cleanup of a forever-blocked job; a narrow race on saving the round line; rounds still exist as the scheduler (only the fresh turn per round is gone); nothing verified live. Next: G5 single delivery node.


## v0.784.0 SAWAAL CARD - design questions she can see before a Studio Build (L3 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L3")
Lovable asks a few design questions before it builds; Hoola Studio built straight from one line. Now a Build from the Studio home
first shows "A few quick choices" (up to four, the first option of each already picked):
- THE FEEL: four styles (her field's three from `library.understand` + the next different one), each card drawn in that style's own
  colours, corner and heading font.
- THE COLOURS: four real palettes as swatches (two for the first feel, one each for the next two; `library.palettes_for`).
- THE TYPE: four font pairs written in their own fonts - the bundled woff2 files served by GET /api/site-design/font/{fn} (strict file
  name pattern, nothing from outside).
- THE TOP OF THE HOME PAGE: four hero layouts drawn as wireframes (split / full / grid / big type / centred, read from each hero's
  own description), different shapes first.
Every option is an id in `site/taxonomy.py`, so whatever she picks the builder can really make (GET /api/site-design/questions).
SKIPPED when her words already decide the design: a colour (English or Hindi words), a hex code, a font name, a style name, or
screenshot / Figma / old site / brand colours - and for a template (it has its own design). Skip = Hoola picks; Back = her words kept.
HER PICKS: POST /api/sites carries `design`; `designq.ref_from` keeps only library ids and makes a v0.567-shaped `design_ref`
(source 'answers', palette colours as overrides, the font pair, the style's corner, the hero); the route sets `designq.PENDING` and
`S.new` puts it on the row BEFORE any job starts (no race with the looks job). `_make_looks` then builds look 1 from it ("Your choices",
her front layout) while looks 2-3 stay Hoola's alternatives. Switch `studio_design_questions` (default on; conftest pins it off so the
older Studio walks keep going straight to the workspace).
Pins moved on purpose: test_v0707 source pin now reads `await startFromAsk(t, design)` (the order it checks is unchanged).
Tests: test_v0784_sawaal_card.py (6: library-only options + skip rules + switch, picks -> design_ref, routes incl. font + traversal 404 +
the build carrying picks, look 1 built from her palette, source wiring, a Playwright walk at 1440 px (pick, build, POST carries the picks,
'Your choices' look) and 390 px (fits, Back keeps her words)).
NOT VERIFIED live: a real Opus build of look 1 from her picks on her server (tests use the fake site AI).

## v0.785.0 HOOLA AI APPS — AIs that answer HER CUSTOMERS, D0-D5 end to end (11 Nov 2026; owner: "D0 ... D5 --- DO THIS -- DEPLOY A PARALLEL AGENTS TO FINSH THIS END TO END")

After the Dify read for app building (`docs/research/dify/00_APP_BUILDING.md`; ideas only - their licence bars multi-tenant
use of the source and claims a design patent). Contract: `docs/AIAPPS_PLAN.md`. The core was written first, then four
parallel agents built on it in their own worktrees; everything merged, mounted and walked in a real browser here.

An AI app sits BESIDE the business AI Employee (WhatsApp inbox v0.59, Seva, Call Centre) and reuses its engines; many apps
per business. `server/app/aiapps/`:
- **D0 core** - `models.py` (ai_apps / ai_app_versions / ai_app_keys / ai_app_sessions / ai_app_messages, init_db + self-heal),
  `soul.py` (the checked settings: about, persona, facts, knowledge, ACTIONS handover / ticket / slots / book only, form,
  refuse topics, language, monthly rupee cap, DPDP notice; `blanks()`), `store.py` (draft + immutable versions; publish =
  HER tap bound to the draft hash, 409 stale / 422 unfixed / 422 unfilled [blanks]; restore = old soul published again as
  the newest version), `runtime.py` (the answer: TRAPS in code first - OTP / PIN / card, payments + refunds, other
  customers' data, "ignore your instructions", her refuse topics; then her approved answers (gyaan annotations), Seva
  knowledge, real slots / booking / Seva tickets; the model LAST, from her facts only, under her monthly cap - a reply with a
  number not in her facts or a claim nobody did is thrown away; a model that fails = an honest hand-over; OTP / PIN values
  masked before logging).
- **D1 builder** (agent A) - `builder.py` her one line -> a checked soul, one repair round, invented numbers dropped,
  missing details as questions; `POST /api/aiapps/plan`.
- **D2 publishing** (agent B) - `public.py` hosted chat page `/ai/{code}` (self-contained, strict CSP, DPDP notice + consent
  before the first message, textContent only), `/ai/{code}/embed.js` bubble (sandboxed iframe), `/api/aiapp-pub/{code}/*`;
  `keys.py` API keys (shown once, sha256 kept, rpm / rph / concurrent limits -> 429) + `POST /api/aiapp-api/v1/chat`;
  `mcp.py` `/mcp/aiapp/{code}` (initialize / tools/list / tools/call ask, app key); `wa.py` + a guarded hook in
  `employee/inbox.py` - a live app bound to her business number answers through the existing send path (window, STOP,
  takeover unchanged; unbound numbers byte-identical). Only a LIVE app with that channel on answers the public.
- **D3 run + improve** (agent C) - `api.py` owner routes, `ops.py` logs (masked), correct-an-answer (into her approved
  answers; the same question is answered with her words next time), stats (customer channels only; satisfaction 'no
  ratings yet', never 0%), gaps, cost alerts once a month at 80% / 100% into her chat (worker slot `aiapp_ops_jobs`).
- **D4 proof** (agent D) - `proof.py` shop / clinic / school on `__aiappproof__`: 18 normal questions + 22 traps, every trap
  refused; correction, cap, pause, stale hash, versions + restore and the number guard proved; `python -m app.aiapps.proof`,
  vps-ops `aiapp_proof`.
- **D5 templates** (agent A) - `templates.py` 13 trades (kirana, clinic, school, salon, restaurant, coaching, real estate, CA,
  gym, homestay, repair, pharmacy-info, tiffin form) with a trial that saves nothing; `dsl.py` export (no keys / logs / codes)
  + import with a dependency check, lands as a draft.
- Tool `ai_app` (`agent/aiapp_tools.py`; publish_card = a card for HER tap, never a publish), registry 624 -> 625; console page
  AI Apps (`static/console/aiapps.js` + `.css`, sidebar row).

**Found by the browser walk and fixed here:** a copied template could go live with '[Shop name]' showing to customers
(publish now refuses unfilled blanks, listed under 'Must be fixed'); a model outage told the visitor 'something went wrong'
(now the honest hand-over line); the Numbers tab printed the raw object; a JS `null` child printed the word 'null'.
**Found by agent C:** a typed OTP was stored unmasked in the log (now masked in the core).

Tests: test_v0772_aiapps_{core,builder,publish,ops,proof,console,e2e}.py = 55 passed; tool-count pins 624 -> 625.
**NOT VERIFIED:** no real customer has used one; every answer here came from a fake model (the sandbox has no model key);
rate limits are per process (reset on restart, not shared across workers); the phone app has no AI Apps screen (console
only); WhatsApp delivery through Meta not tried.

## v0.786.0 HOOLA INTERACTIVE, PREMIUM PASS (built as 0.785; their HOOLA AI APPS took 0.785.0; owner: "IT LOOK STALE AND OLD DESIGN MAKE IT MORE PERFECT, ALINE TEXT PROPERLY, FIX ALL BUTTON, ICON, TAB MESSY THINGS --- MAKE IT MORE PREMIUM, ADVANCE AND WITH SOME ANIMATION")

No server change. Same twelve pages, same `/api/interactive/studio/*` and `/api/interactive/hub/*` routes, same data. Only
`static/console/interactive.js`, the `#hiRoot` block in `v2.css` and one line of `studio.js` changed.

**How it was done:** every page was screenshotted in real Chromium first and the faults were read off the pictures, not guessed.

**What was messy, and the fix**
- Each page said its name twice (a top bar AND a heading). The top bar is gone; one heading per page (`head()` -> `.hi-head`).
- The icon rail was too tall for a small laptop and its Create button was squashed. It is a real sidebar now: rows of 34,
  "Create video" on top, the engine state and "Back to console" at the bottom, and it FOLDS to icons (`#hiRoot[data-slim]`).
  The editor opens folded so the canvas has room; once she presses the fold button her choice wins (`UI.slim`).
- Editor: the title row, the scene header and the five tool tabs wrapped onto second lines. Title row = `.hi-edhead` (back,
  title, saved dot, Save as template, Generate). A scene = header (number, move up / down, remove), the words, then a footer
  with the look chip and "about N s". Tools = one five-part segmented control (`.hi-tt`). A browser test holds each to ONE row.
- Dropdowns were raw browser selects. They are drawn (`pick()` -> `.hi-pick`, and `.hi-f:has(>select)`), with an icon and chevron.
- Thumbnails were empty dark boxes. A scene thumbnail shows the scene's own words or bars (`mini()`), with a dot when it
  still needs her numbers; a video tile has a play mark, its length and a tint (`thumb()`, tint picked from the id).
- A picture that cannot load showed a broken image. It shows her initials (`photos()` sets `img.onerror`).
- One control scale: buttons 40 / 32 (+46 for the main ask), fields 42, corners 10 / 16, status chips with a leading dot.
- Stage: tinted with HER brand colour (`--hi-brand`, validated hex), a "Scene 2 of 3 - 16:9" tag, previous / next under it.
- Home: starter lines under the ask box (none carries a number), engine state as one slim line, month figures as three tiles.

**Motion - once only, never held**
- `flash(cls, ms)` puts a class on the view and takes it off again: `hi-in` when a page opens (sections rise in, cards
  staggered), `hi-tabin` when a tab changes, `hi-scin` when the scene changes (words rise, bars grow). A later redraw of the
  same page does not replay it.
- Cards, buttons and thumbnails lift under the pointer; the sidebar marker slides in; the dialog pops.
- Fill is `backwards`, never `both` / `forwards`: a held animation keeps a layer alive under text (CRISP TEXT, v0.256).
- The only looping motion is "working now" (the live chip and the running step). Reduce motion and calm switch everything off.

**Found on the way**
- Three class names of the page (`.top`, `.tag`, `.live`) are styled globally by the console and leaked in (a border under
  every card icon). Renamed to `.hi-ftop`, `.hi-stag`, `.hi-now`. RULE: inside `#hiRoot` use `hi-` names for anything generic.
- `studio.js` (Create Studio) threw `Cannot read properties of null` on EVERY window resize until Create had been opened once
  (`closeMenu()` with no root). One guard.
- `test_v0255 test_sora_only_on_the_logo` was red on main because v0.774's own sidebar used the logo font; green again.

**Tests:** `test_v0747_hoola_interactive.py` - the browser walk now also checks one `h1` per page, every select drawn, the
sidebar fits 1366 x 660 without scrolling, the entrance class leaves by itself, a starter line fills the box, the empty picture
becomes initials, the three editor rows do not wrap, the sidebar folds / opens, next scene works; NEW
`test_the_premium_pass_keeps_the_console_rules` (no blur, no capitals, nothing above 600 or under 12px, no held animation,
motion can be switched off, no clashing class names). Needs `HOOLA_CHROMIUM=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome`.

**Still red on main, not from this work, left alone:** `test_v0221 test_console_chrome_speaks_english` (build.js),
`test_v0255 test_no_heavy_weights_caps_or_tiny_text` and `test_v0256 test_crisp_text_rules` (another block's `font-weight:700`
and `animation:hmWord ... both`).

**NOT VERIFIED:** she has not seen it on her server. Checked here in light, dark, 1366 x 660 and 400 px wide.

## v0.787.0 HOOLA CODE ENGINE (built as 0.784; their SAWAAL CARD took 0.784.0, 0.785.0 and HOOLA INTERACTIVE PREMIUM PASS 0.786.0 - REBASE PROTOCOL, all kept)
Owner: "NOW CHECK IS HOOLA CODE BACKEND IS SAME AS CLAUDE CODE" -> the honest answer was no (the workflow was Claude-Code-like,
the ENGINE was a GitHub-API task: files read one by one, edits in memory, GitHub code search = 3 words / 10 file names / rate
limited / silent on failure, ONE declared check command, 40 steps / 20 min, nothing trimmed or cached, no thinking, every
follow-up a fresh run, and on her server every call went to GLM-5.3-Flash) -> "GO STEP 1 AND 2 --- 2 SESSIONS, USE CLAUDE".
- STEP 1 `devsahayak/brain.py` = one Claude call for every Hoola Code loop (the new engine, the old 8-tool loop, plan and review
  passes): Claude's OWN past SAB GLM / claude_one_model (`dev_claude`, the architect's v0.710 pattern: glmdoor.CLAUDE_ONLY +
  usage.ONE_MODEL_BYPASS), adaptive thinking (`dev_think`; a refused field is dropped once and remembered), prompt caching
  (system + last tool + last message), old tool output trimmed in place past `dev_ws_clear_chars` (newest 6 kept). The model
  picker now offers Claude's models instead of "forced GLM". `model_json` (one-shot / reviews) is Claude's too. A failed GitHub
  code search is now SAID to the model ("GitHub code search FAILED ...") instead of looking like "no file found".
- STEP 2 `devsahayak/engine.py` = the working copy (Phase 4 of docs/HOOLA_CODE_WEB_PLAN.md): data/devsahayak/ws/<task>/repo cloned
  once (outside the box, no token inside), a LOCAL git repo started in it (base commit; node_modules / venv / caches excluded);
  files holding secrets replaced by a marker before anything sees them and never changeable. Claude Code's tools: read (line
  numbers, offset / limit) / write / edit / multi_edit (read-first, unique-or-replace_all) / glob / grep (git grep: extended regex,
  files / content with line numbers / count, context, glob filter; hidden files excluded) / ls / bash (ONE command in the devlab
  box on THIS checkout: no network, uid 1000, read-only root, caps; the repo's dependency snapshot when it DECLARES a setup, else
  the base image; devlab's refusals; 80 a round) / todo_write / show_diff / done. 150 steps / 60 min a round. Past
  `dev_ws_compact_chars` the older conversation is COMPACTED by one model call (cut before an assistant turn so no tool_result
  loses its tool_use). messages.json per session: "Ask for a change", a CI failure, her own review points and a follow-up on an
  explained / failed / stopped session (status CONTINUE, no PR yet) CONTINUE the same conversation in the same checkout
  ("yes, fix it" after an explanation switches the kind). A checkpoint (local commit) after every round; rewind = the checkout
  and the conversation as they were (POST /tasks/{id}/rewind; GitHub untouched until the next push). After a push the checkout
  is marked (the next round diffs from the PR head); a branch moved by someone else = a fresh copy, conversation kept.
  TWO AT A TIME: `dev_ws_live` = 2 (owner) sessions run at once server-wide, the next waits and says so on the page. Disk:
  working copies of deleted / archived / merged / closed sessions and idle ones (`dev_ws_keep_days` 14) swept hourly by the tick.
  engine.run returns the old loop's (base_sha, read, ctx, out), so _prepare's safety rules, the PR, the bug proof, the CI rounds,
  the own review and her taps are unchanged code. No box / no git / switch off = the old loop, said in the log.
- Routes: GET /api/devsahayak/tasks/{id}/ws, GET .../files?path=, POST .../rewind. The full task view carries `ws` + `can_continue`.
- Page (code.js): steps for commands in the box ($ command · exit · seconds, output folded open on failure), the to-do list,
  compaction / waiting for a slot / checkpoint / rewind; a "Working copy" rail card (to-do, checkpoints with Go back, secret
  files hidden, Browse files dialog with a folder tree + file view); a finished session with a working copy takes a follow-up;
  a box command counts as "Run your tests" in Progress.
- Found by its own tests: the follow-up opened the work while holding the DB write lock (SQLite "database is locked");
  `error` is NOT NULL ("" not None).
Tests: test_v0787_hoola_code_engine.py (13: brain = Claude + thinking + cache + effort, refused thinking dropped once, trim keeps the
newest, old loop on the brain + a failed search said, Claude picker, 2 slots then wait, compaction keeps tool pairs, every tool on a
real checkout (secrets hidden / unsearchable / unchangeable, workflows refused), bash in the REAL box (no internet, sudo refused, no
secrets inside), a whole session through the service with real Docker: work -> continue -> rewind -> files -> delete, an explained
session taking "yes, fix it") + the older Hoola Code / lab / plan / review suites green with the engine pinned off in conftest.
NOT VERIFIED live: no real session has run on her server yet (no GitHub token / repo saved there); Anthropic credit must be there
(Hoola Code is Claude-only now); restart mid-round is not resumed (the conversation and checkout survive on disk, the round does not
restart by itself); background commands, env vars / setup script per repo in the page, network allow-lists are not built.
FOUND while testing (her server, not this change): the server's venv is Python 3.12.3 while the devlab box is 3.13 (CLAUDE.md said
her server runs 3.13) - test_v0456_devlab's 'box python vs server python' check says GADBAD. The same test found the box base image
at rev 2 and rebuilt it to rev 3 (what lab_check would do).

## v0.788.0 LANGGRAPH G5 — outcome in state + one delivery node (11 Nov 2026; owner: "GO G5")

Phase G5 of `docs/LANGGRAPH_TURN_PLAN.md` (bug class 2: told late / twice / never / wrong chat), only when `chat_graph` is on (default OFF; every old delivery path unchanged).
- The graph gains `deliver` (finish -> deliver -> carry | END), resumable. State: `result` (done / partial / stuck / stopped / failed - from her Stop, the ending goal, the breaker / LAST_OUTCOME, step cap / carry, G3 facts), `dkey` (idempotency key `turn:<thread>:<nonce>` minted by prepare / carry and checkpointed; wake reports `news:<followup id>`), `dmark`, `delivery`, `notified`.
- NEW `agent/turndeliver.py`: table `turn_deliveries` (in `db.init_db` + `ensure_table`), per-channel stamps (intent before a send, sent after), job aliases `job:<key>:<state>`, the right-chat rule (the turn's own chat, else her pinned updates chat - v0.714), the `NEWS` contextvar for wake turns. Chat: the reply the turn's step already saved + streamed is found by id after `dmark` and stamped (written by the node only if no step wrote one, row + stamp in one transaction). Push rides that message event (push.on_event gates unchanged). Call note + ring only for news (wake reports, a long job ending in a background run) via `kaamwatch._voice` / `kaam_followup._ring` (quiet hours, cap, never over a live call), once each.
- `kaam_followup` on the graph path reads the record (job aliases written by the run that ended the job) instead of `_answered_since` / `_recent_said` timing, and a report queued during a live graph run waits for its record instead of the 5-minute dry line. `turn_inbox` sweep resumes a turn cut at finish / deliver. `worker` drops delivery records older than 7 days.
- Restart: after deliver sent but before its checkpoint -> the re-run finds the stamps, sends nothing; after the answer streamed but before deliver -> the sweep resumes at deliver, stamps the existing row; a wake reply that landed before a crash is recognised, its missing call note / ring sent once, no second wake.
- TESTS: NEW `test_g5_turngraph.py` 11; g0-g4, v0260, v0552, v0652, v0657, v0714, v0722, v0186, v0226, harness2/3, routines, v0649 same off and on (v0554 card khabar 3 reds also fail at v0.783).
- NOT COVERED: voice late results / card notes / call brain answers (G6); a stopped run that crashed before deliver may have its stopped report told once more; `_recent_said` not consulted on the graph path (a service that posts its own line + a followup could show twice); a long job end still sends 2 phone notifications (goal card + final message); a crash inside `check` after it published could publish again (G1 node re-run gap). FOUND, not fixed, both paths: with kaamwatch on, `goal._waiting_on_job` counts the job's own `goal:` kaam_jobs row as a running job, so a long job can pause up to an hour after its first segment. Nothing verified live. Next: G6 voice as a channel.


## v0.789.0 CHHOTA BADLAAV - small exact edits + tiered checks (L4 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L4")
Before: "make the button grey" went through `website action=change` -> Opus wrote the whole section again -> the full
Chromium matrix + journeys + gates. Lovable changes a few lines (line-replace) and checks only what changed.
E1 LINE EDITS (`site/lineedit.py`, no model call):
- `website_dekho what=search` + q: every place the text / colour / class is in the site's code (pages/<page>/<section>.html |
  css | js + design/kit.css), with file and line (30 shown, total counted).
- `website action=edit_lines` + site + file + search + replace: one exact replace. The search text must appear EXACTLY once:
  0 = refused naming the closest lines, 2+ = refused asking for more of the surrounding text, search == replace / empty =
  refused. The result goes through `code_write` - the same safety cleaner as every build, one Undo step - and returns the diff.
- `website action=write_file` + file + code: the whole file (rare).
- The `website` description now says SMALL EXACT CHANGES FIRST; action=change stays for new sections / layout / many parts.
  Both live in the existing tools (registry count unchanged); Plan / Chat mode still refuse `website` (turnmode).
E2 TIERED CHECKS:
- `checks.run(..., only=pages, quick=True)`: only those pages in the browser (scroll width, a11y / contrast, console errors, the
  page's links, h1, weight) - no Lighthouse, no whole-site link scan, no share picture / video.
- `service.save_version(quick=pages)`: used by edit_lines / write_file / a code file / her own-hand preview edit (one section).
  Needs a FULL report to stand on (else the full check runs); `_quick_merge` replaces only the touched pages' results, keeps
  every other page, the visitor journeys and Lighthouse items from the last full run; the gates re-run; report `tier: quick`,
  `checked_pages`, `quick_s`. Edits that pile up while a job runs, Opus code changes and action=change keep the full check.
- `hosting.blockers` refuses Go live (and the blog's auto-update of a live site) while the last report is quick; her Go live
  tap (`launch_request`) starts the full check, then the card is hers again.
- Studio version card: "Quick check of home in 6.2s · the full check runs before going live".
- Switch `site_quick_checks` (default on).
MEASURED HERE (real Chromium, the test site): one page quick-checked in 6.2 s, the whole edit 6.3 s - the plan's target was
< 20 s. The edit itself costs Rs 0; the turn that asks for it is the only model cost (not measured on her server).
Tests: test_v0789_chhota_badlaav.py (8: search file + line, exact-once edits + refusals + cleaner + Undo, quick check then full
before live, switch off / no base = full, the merge rule, the agent tool actions + Plan mode, the real Chromium timing, the
Studio line).
NOT VERIFIED live: a real model choosing edit_lines for "make the button grey" on her server, and the rupees of that turn.
## v0.790.0 HOOLA GAME DEV — game making as its own full-screen app (built as 0.783; owner: "CAN WE DEVLOPE A SEPERATE CONSOLE SECTION / FEATURE -- NAME IT A HOOLA GAME DEV" → "FIEST SHOW ME ALL DESIGN AND PAGES" → "GO BUILD -- DEPLOYE SEVERAL AGENTS TO DEPOLY IF PERFECTLY")

**What it is.** `/console/games`, the twin of Web Studio (`/console/web`) and App Studio (`/console/apps`): a full-screen
app with its own sidebar, opened from a new **Game Dev** row in the console sidebar (`v2.js` NAV, right after App
Development). Before a line was built, the owner was shown a 14-page clickable design canvas (Home, Design doc, Play,
Board, Bible, Scenes, Assets, QA, Release, Live ops, Where it came from, Crew, Game Arena, Big studio) and approved it.

**Pages.** Home (ask box + kinds of game + the six steps every game goes through + "Waiting for your OK" + your games +
"Or start from"); a game workspace = top bar, **the game's own Hoola thread** on the left (a conversation per game, like App
Studio's per app), and tabs: **Design** (the design doc rendered by HoolaMD, "Theek hai, bana do", change it in words;
progress card while it builds) · **Play** (the game in a phone frame from its private `/play/` link in an iframe sandboxed
WITHOUT same-origin, QR + copy, what Hoola's bots proved, fun said plainly as not assessed, versions with "Go back to this"
when there is a long project) · Board · Bible · Scenes · Assets · QA · Release · Live ops · Where it came from · Crew; plus
studio-wide Crew (role cards, hired / not hired), Game Arena and Big studio. A tab that needs a long project offers "Make it a
long project" for a game that already plays.

**How it reuses the tested pages.** `employees.js` gains ONE export, `gameEmbed(el, page, studio)`, that renders the
console's existing Game Desk pages (board, bible, scenes, assets, qa, release, liveops, prov, runtime and every role page,
arena, big) into a pane with the desk's own flags reset for it; `gameEmbed.stop()` ends any poll when a pane is left. While a
page is embedded, its own error path (`game(el)` / `roleBack`) can never draw the whole Game Desk home into a tab — a calm
"Try again" panel instead. The console's own Game Desk is unchanged. Server: `gamedesk/service.view()` now carries the game's
`conversation_id` (so its thread is the same on any browser) and the full `brief` on GET (so "Try again" after a failed first
build loses nothing). Route `game_dev_page` in `main.py` with the console's strict CSP, `X-Frame-Options: DENY`, nosniff.

**How it was built — several agents, as asked.** The lead laid the foundation (route, sidebar row, `gameEmbed`, the page
shell) and a fixed DOM contract; a **builder** wrote `gamedev.js` / `gamedev.css` (every class `gdv-*`, every colour a v2.css
token so dark mode works) and walked it in real Chromium; a **tester** wrote `tests/test_v0783_gamedev.py` against the
contract in parallel (route + headers, load order, the sidebar row, `gameEmbed` run in node, escaping scan, no keys / eval, a
hire gate, and a full real-browser walk of every page at 1440 and 390 px with page + console errors failing every step); then
an **independent reviewer** read the code against the design and the real server. It found 14 problems, most reproduced:
the game being played restarted every ~3 s while the next version built; the home poll wiped what she was typing every 5 s;
a single server hiccup threw a game's thread away; an embedded page's error path drew the whole Game Desk home (with its
own "New game" form) into a tab; stale replies from a game she had left could paint into the one she opened; hint lines
leaked into her bubble when a title held a `]`; embedded pages showed weight 700 and Sora headings. All 14 were fixed, and
each has a regression test that fails on the old behaviour — including one the lead caught itself: re-inserting an iframe
RELOADS it, so "keep the same node" would have passed a node-identity test while the game still restarted; the fix never
touches the stage that holds the frame. **20 tests, 20 pass.**

**Also found while building:** the earlier dependency reinstall had pulled a newer pip Playwright (1.64.1) that cannot find
this machine's pre-installed Chromium (revision 1243); it was pinned back to 1.63.0, the version that matches. And main's
English-tools commit `d84057023` had left the v0.545 scenes test asserting the old Hinglish refusal; its pin was healed.

**NOT VERIFIED, said plainly:** a real Godot build inside the play frame; a live agent reply in a game's thread (no model
key in tests); the 8 embedded tabs are the console's own pages restyled toward the approved design with scoped CSS, not
redrawn to it pixel for pixel. The phone app gets nothing new — on the phone, games stay in chat.

## v0.791.0 KHUD PE NA RUKE — a long job no longer waits on itself (11 Nov 2026; found while building G5)

With kaamwatch on (the production default), `goal._waiting_on_job` counted the long job's OWN kaam_jobs row (kind `goal`, state working) as another running job of the chat, so `maybe_continue` paused the job for up to `JOB_WAIT_S` (an hour) after its first round instead of scheduling the next one. The query now skips `kind == "goal"`; a real job of the chat (cloud PC, website, video...) still holds the goal as v0.238 intended. Both paths (old goal rounds and the G4 graph job). Test: `test_v0238_data_desk.py::test_the_long_jobs_own_row_does_not_hold_it`; the G5 test's patch-around removed. Long-job suites (v0186, v0226, v0228, v0222, v0443, g4, g5) green. NOT VERIFIED live.


## v0.792.0 VIDEO LEARNER PREMIUM (built as 0.785.0 - their HOOLA AI APPS took 0.785.0 and 0.786-0.791 went to INTERACTIVE PREMIUM / CODE ENGINE / G5 / CHHOTA BADLAAV / GAME DEV / KHUD PE NA RUKE, REBASE PROTOCOL, all kept; 11 Nov 2026; owner: "CHECK A AI EMPLOYEE SECTION ... HOOLA AI LEARNER FROM VIDEO READ THIS CODE AND DESIGN FIRST" -> seven problems reported -> "FIX ALL 7 PROPERLY. ALSO MAKE ENTIRE SECTION PROPER AND PREMIUM WITH PERFECT ALIGNMENT OF TEXT, BUTTON, TEXTURE ... WITH SOME VISUAL GRAPHICAL ANIMATION IN IT")

Read first, by rendering the four screens with the page's own files: seven real problems. All seven fixed, then the page redrawn.
1. THE LEARNING PILL: it wore the class `live`, which is the chat's side panel (`.live,.studio,.panel{width:var(--right);flex-direction:column}`, and a
   fixed bottom sheet under 640 px) - so it stretched into a bar on desktop and was pinned to the bottom of a phone. It is `.skv-pill.lrn` now.
2. RE-LEARN REPLACES: the confirm said "replace", the code added a second row. `seekh.watch(..., replace=<row id>)` retires the old row, its learned
   procedure, its never-run recipe draft and its kept video (`_retire`); `relearned` counts it; a failed Re-learn keeps what was learned. Try again on a
   failed row replaces that failure row (success or a second failure), never a learned task. Console `POST /watch {replace}`.
3. PROVEN: the run lived only in the page's memory. Now `POST /api/seekh/console/run {id, conversation_id, after}` keeps it on the task row
   (`run: {cid, after, ts, scored}`); the list and the task show "Hoola is doing it" / "Did it work?"; `GET /run?id=` gives the cards of THAT chat that
   really wait (`events.waiting_cards`) and `busy` (the chat turn or an active OperatorTask of that chat) - so "Did it work?" no longer appears between
   two tool calls. `seekh.operator_done(tenant, task, recipes, conversation_id)` is called from operator `_wrap` on status done: the open run of that
   chat, else the recipe that ran / was saved (`job.ran_recipe`), else the task's title inside the job's words (>= 60 % of its words) -> one win,
   `proven_by: run`. Her Yes afterwards does not count twice; "Something was wrong" takes that win back (`procedures.record_run(undo_win=)`);
   `{skip: true}` closes a run unscored.
4. FILE STEPS: an `upload` step gets a file picker (25 MB, the chat lane); the files ride the same chat turn (`send(text, files)` in v2.js) and are
   named in the message.
5. STAGE TIMES: the page showed when a stage began. It shows how long each took (the job snapshot carries `first_note`, the moment the first streamed
   words arrived), the running stage counts up, and the rail fills.
6. UPLOADS KEPT: the chat file lane is swept after 24 h. The learner keeps its own copy (`data/seekh/media/<tenant>/<row id>.<ext>`, `media` on the
   row, `GET /api/seekh/console/media?id=`), also for a failed watch (Try again) and for direct video links (they now play on the page). Ref
   `kept:<row id>` re-learns from it. Removed with its row; cap `seekh_media_max_mb` (1024) drops the oldest copies, the learned steps stay;
   `seekh_keep_media`.
7. RESTART: every job keeps a record beside the sidecar (`data/seekh/jobs/<id>.json`: stage, notes so far, heartbeat every 5 s, pid + boot mark). A
   record quiet for 30 s that no live process owns is picked up again ONCE with the same id (claimed by an O_EXCL file, so one worker only) - at
   startup (`recover_later` in lifespan) and when the page asks; a second loss becomes a failure row with Try again. The record also lets any worker
   answer the poll and pass Stop (a flag file). Switch `seekh_resume` (conftest: off). The page says "started this video again".
Also: `_save` writes the sidecar atomically under a lock; a runtime sidecar (`server/data/seekh/default.json`) had been committed and made
`test_offline_status_action` fail on a clean checkout - removed and git-ignored.

THE PAGE (`static/console/seekh.js` rewritten, `skv-` block in v2.css replaced; console tokens only, Light / Dark / phone checked by eye):
- Home: hero card with a drawn loop (a video is scanned, three moments light up, they become three ticked steps, a pointer does them), her numbers
  (tasks learned / proven / steps known / today's meter, counted up once), a bar for a run that is open now, the teach card (link, name, upload, drop
  veil), learned tasks as cards with a confidence ring, a segmented filter, an illustrated empty state.
- Watching: the video on the brand-gradient live edge, a "Hoola is watching / writing notes" tag with moving bars, notes that arrive one by one (only
  new notes animate; the list is patched, not redrawn), the stages on a filling rail with durations, notes / time so far.
- Learned task: steps as a numbered timeline with an icon per kind of step and the time chips, three boxes with icons, a sticky card with the big
  confidence ring, how it went so far, the form (text boxes + file pickers), Do it now.
- Doing it: a browser drawing whose fields fill while Hoola works (green when done), the live step, Waiting for you -> Answer opens THAT chat
  (`chat(id)`), steps patched by key, Hoola's reply, Did it work? (Yes / Something was wrong / Not sure yet), a short Proven celebration.
- AI Employees hub card: dotted violet edge, a light scanning the camera icon, a solid Open pill.
- One scale: text 12.5 / 13 / 14 / 15 / 16 / 21 / 30, weights <= 600, corners 11 / 16 / 20, controls 32 / 38 / 46 px. CRISP TEXT kept: only drawings,
  dots, bars and rings move; entrances fill backwards; texture only behind drawings; reduced motion / calm switch it all off.
Pins moved on purpose: test_v0718 `test_router_mounted_with_three_doors` reads the lane's own router (FastAPI 0.162 in the sandbox keeps included
routers nested in `app.routes`), the v2.js wiring window 1400 -> 2400 chars, the stale `?v=0.748.0` stamp pin -> the current stamp.
Tests: tests/test_v0785_video_learner_premium.py (20, incl. a browser walk at 1280 and 390 px that measures the pill, the stage durations, the
row buttons' shared right edge and no sideways overflow); v0713 / v0718 / v0745 green.
NOT VERIFIED: a real Gemini watch, a real operator run reaching `operator_done`, a real pm2 restart mid-watch (tested with a planted record), the
multi-worker path (records + flag file) on a live server. NOT built: a live picture of Hoola's browser on the run screen; an OTP typed on this page.

## v0.793.0 HOOLA CODE SAFETY + RESUME (built as 0.789; their CHHOTA BADLAAV took 0.789.0, HOOLA GAME DEV 0.790.0, KHUD PE NA RUKE 0.791.0 and VIDEO LEARNER PREMIUM 0.792.0) — the working-copy engine made safe against planted links, and a round a restart cut is continued (owner: "GO PHASE 4 WITH 2 LIVE SESSIONS" -> "MERGE")

**What happened.** Two sessions built Phase 4 of `docs/HOOLA_CODE_WEB_PLAN.md` at the same time. The other one reached
main first as v0.787.0 HOOLA CODE ENGINE (`devsahayak/engine.py`) and is proved on real Docker; this session's own
engine (`devsahayak/wsp.py`: a long-lived box per session, pause / resume, Terminal and Files pane tabs) was never
proved on Docker. Two engines for one job would be wrong, so **the shipped engine is THE engine and this session's was
withdrawn** (it is in the branch history, commits 58a13e679..d0b7a8f4e, if a piece is ever wanted). Only what it had
that the shipped engine lacked is re-landed here, on the shipped engine.

**1. The link wall (a real hole, found by comparing the two engines).** A command in the box can run
`ln -s /any/path/on/the/server name`. Inside the box that link leads nowhere, but the SERVER works on the same folder:
`read name` returned the server's own file to the model, `write` / `edit` overwrote it, the file browser showed it, and
the harvest put its content into the pull request. Now `Session.real(rel)` is the only way to a path: it refuses a link
and anything behind a linked folder, and it is used by read, write, edit, multi_edit, ls (a link is listed as
"-> (a link; not followed)"), the walk / glob, the harvest ("a link - Hoola never follows one", said in risk) and
`files()` for the page. The test fails on the engine as shipped (the model was handed the outside file).

**2. Keys.** A key that appears in a file AFTER the clone (a command wrote it) is hidden the first time it is read, added
to the session's hidden list, never changed and never in the PR; `engine.scrub` hides a key-looking line of a command's
output before the model or the page sees it; a command with a key in its own text is refused.

**3. A round cut by a server restart is continued.** A background run writes what it is on the row (`DevTask.job` =
{what, words, beat, tries}) and beats every 30 s on its own small thread while the round lives (one long command says
nothing for minutes). `service._resume_cut_runs` (in the tick): a job still on the row, nobody in this process running
it, heartbeat older than 3 minutes = cut -> `engine.run(resume=True)` goes on from the saved conversation in the same
working copy with one line telling the model the server restarted (her message is not sent twice: `_said`). Twice at
most, then failed with words she can act on. A run of the OLD loop has nothing saved: after 30 silent minutes it is
marked "start this again as a new session" instead of looking busy for ever.

**4. Her repo's box.** `service.save_repo` + `PATCH /api/devsahayak/repos/{owner}/{name}` + a form under each repo in
Settings ("How this repo runs in the box"): her setup command (counts as declared, so the dependencies are installed;
the box image is keyed on it, a changed command = a new box), her test command, plain variables for every command
(`box.run_in(env=)`). A sudo / docker command, a key in a command, and a name or value that looks like a secret are
refused by name.

**5. A question she can answer with a tap.** `done` may carry `choices` (2-4) beside a question; they show as buttons
(`ws.choices`) and her tap is sent as her answer. Cleared when the next round starts.

**6. Fixed on the way.** A revision on an open PR let go of the row before writing it (`s.expunge` before a flush), so
the round count, the security notes and Hoola's explanation of that round were never saved - the "6 rounds" limit never
counted on an open PR.

**Files.** `devsahayak/engine.py`, `service.py`, `api.py`, `models.py` (three nullable columns on repos, `job` on
tasks), `devlab/box.py` (`run_in(env=)`), `static/console/code.js`, `v2.css`; tests `test_v0789_hoola_code_safety.py`
(9, incl. a browser walk) + the v0.787 engine suite and the older Hoola Code suites green.

**NOT VERIFIED.** Docker is not on the machine this was built on: a local folder stood in for the box in these tests,
so the env variables and the scrubbed output have not been through a real `docker run`. No real restart has cut a real
round. **NOT BUILT (this session's withdrawn engine had them, unproved):** background commands, a Terminal pane,
pausing an idle working copy to free disk before the 14-day sweep. Deploy: vps-ops deploy, server-only, no new pip;
four nullable columns create themselves.


## v0.796.0 PRAYOGSHALA WAVE 7 (built as 0.794.0; re-versioned past 0.795.0, all kept) (owner: "Coverage 44.9% ... NOW LETS WORK ON PENDING LAB WORK END TO END")

94 physics set-ups built and walked in a real browser within tolerance, by four build agents in their own pack trios
(kernels + JS twin + labs + rigs): school_w7 (32: Class 6-12 motion, measuring, pressure / floatation, heat, sound,
electricity), ug_mech_w7 (22: pendulums, springs, coupled oscillators, Searle, Maxwell needle, optical lever, trolley,
2-D collision (SIMULATED DATA), harmonics, Callendar-Barnes, Angstrom, cooling, Stefan, capillary vs temperature),
ug_optics_w7 (20: TIR, Wollaston, nodal slide, biprism, Michelson x2, Fabry-Perot, FTS, lycopodium, resolving power,
Malus, Babinet, Brewster, five fibre set-ups, quartz expansion, laser characteristics), ug_em_w7 (20: ballistic
galvanometer family, solenoid, Carey Foster, potentiometer, Anderson, universal bridge, Q-meter, RC / RL, transformer,
motor, generator, falling magnet, galvanometer conversion, CC / CV source, magnetometer, B-H curve). Coverage
362 -> 456 of 807 (school 6-10 78.4 %, 11-12 91.5 %, B.Sc 65.4 %, M.Sc 37.6 %, PhD 28.6 %).
Engine: `tools/prayog_claim.py` takes "<level>:<id>" and warns on ambiguous bare ids (four optics claims would have
overwritten M.Sc rows). Tests: test_v0418_prayog.py was red on main (22-lab pins; twin loaded kernels.js only) - it now
counts every pack and the JS twin loads every pack, so pack kernels and calcs are compared numerically (39 / 39 green).
Skipped rows and every constant written from memory: docs/PRAYOG_PHYSICS_LAKH_PLAN.md, "Wave 7".
## v0.794.0 PROMPT NAAP - P0 of HOOLA PROMPTING: measure before building (built as 0.785; their 0.785.0-0.793.0 took the numbers - REBASE PROTOCOL, all kept; owner pasted the P0 step of the plan = GO)

Plan: `docs/HOOLA_PROMPTING_PLAN.md` part 11. Research: `docs/research/prompting/00_INDEX.md`. No user-facing change.

**The question:** does a complete brief beat her rough line in Hoola's OWN engines, and by how much, per section? A
section with no gain is dropped before it is built.

**Files**
- `server/app/quality/prompt_asks.py` - 60 asks, 20 each for web / image / script, 10 Hinglish + 10 English per
  section. Each has `raw` (her rough line), `brief` (the same job filled in BY HAND in the section's anatomy), `must`
  (what she wanted, checkable) and `facts` (literals that must come back unchanged; a list = alternative spellings,
  because a Hinglish script may say "5 baje" for "5 am"). Made-up businesses, no phone numbers.
- `server/app/quality/promptcard.py` - the scorer, the free card, the live card, her verdicts.
- `python -m app.quality prompt` (free) | `--live --budget-inr N [--section] [--limit N per section] [--only] [--judge]`
  | `--status` | `verdict <id> raw|brief|same ["why"]`.
- `GET /api/quality/prompt`; vps-ops `prompt_card_check` (free) and `prompt_card_try` (2 asks per section, Rs 250 cap).
- `server/tests/test_v0794_prompt_card.py` - 11 tests, engines replaced by fakes, no model.

**What runs live**
- web = the website architect's PLAN only (`architect._ask` + `clean` + `depth`): one call, no project row, no build.
- script = `create.service.write("script", ...)`; the brief arm also sets format / length / language / tone.
- image = `photogen.make` (fast), the PNG kept in `data/quality/promptcard-img/`, then ONE reader call answering
  yes / no per statement from the picture.
- optional `--judge` = a blind pick for web / script with the shown order alternating; the card prints how often
  the first-shown side won.

**Scoring (code, 0-100)** web: must 55, facts 20, architect depth 15, nothing invented 10. script: must 50, facts 25,
length band 10, nothing invented 15. image: share of statements the reader confirms. A pair is a win only with a
lead over 5 points. Section rule: BUILD = gain >= 10 AND the brief clearly better in >= 60% of pairs; DROP = gain
< 4; else RETHINK; under 8 finished pairs = no verdict; once she has picked 5 pairs of a section her picks decide.
All thresholds and weights are judgement, not measured.

**Money** a live card refuses to start without `--budget-inr`; each ask is a PAIR (raw then brief) and a pair starts
only when the budget has room for both, sections interleaved, so a budget that runs out leaves both arms with the
same coverage. Rupees = `usage.run_meter` x the server's rate (+ the picture engine's flat price when its call was
not metered). Three dead pairs in a row stop the card.

**Found by its own checks while building**
1. The architect's plan carries HER words back (`spec["words"]`), so with the same plan the brief arm scored 88 and
   the raw arm 37 - the brief was being paid for its own text. The web runner drops that field and `unecho()` removes
   any pasted-back copy (whole, or any line of 40+ characters) before scoring; a test holds "same plan = same marks".
2. The picture engine's own guard refuses a national-flag picture - the free card asks the engines' free guards for
   every ask, found it, and the ask was replaced (kites).
3. A price followed by a full stop ("Rs 299.") read as invented; a JSON-escaped rupee sign was not read.

**Not verified / limits**
- NO live card has run. There are no numbers. Rs 25 / 3 / 4 a run are ASSUMED (about Rs 1,280 for all 120 runs).
- The brief is hand-filled: this is the CEILING of the idea. BUILD means worth building; whether Hoola can fill the
  brief itself is P1's proof.
- web scores the PLAN, not a built site. The script length band is rough (2-9 words a second over the whole
  screenplay). The picture reader is a model: its yes / no can be wrong; her verdict on the saved PNGs outranks it.
- The engines run on whatever model the server routes to (GLM door / one-model rules apply as in production).
- Older reds proven on the commit before this one, untouched: test_v0240_calm_brand::test_version (28 == 25),
  test_v0649_web_studio three-looks walk, test_v0693_app_studio design-run, test_v0784_sawaal_card look-one.

## v0.795.0 YEH WALA - point at the page instead of describing it (L5 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L5")
Before: Edit mode only typed words / swapped a picture; to change anything else she had to describe where it was, and
"AI se badlo" pasted quoted text into the box (plan gap D3). Now the Studio preview has Lovable's pointing tools, in Hoola's look.
- PREVIEW TOOLBAR (`webstudio.js` YW block, `#wsYW`): Select / Text / Draw / Comment (keys S T D C), Comments count, Undo, Done,
  hide; drag the grip and it snaps to left / centre / right (remembered in this browser). The composer's Select button opens it
  in Select. `hoola-edit.js` gained the modes (select / comment / view) through `edit-cmd` messages from its parent only;
  Text mode is the v0.295 behaviour unchanged (the phone app's edit mode too).
- SELECT -> MODEL (E3): click a part (Ctrl / Shift adds, up to 8): a violet outline + name tooltip in the page, a pill in the
  composer ("Home · Hero · heading 'Sharma Sweets'"). On send, PUT /api/sites/{id}/selection (each part checked against the
  section store: `yehwala._element`) and the hint "selected elements: N"; `turnmode.site_block` adds `<selected_elements>`
  (label, page, the code FILE for edit_lines, the element's HTML without edit numbers, its style picks) ONCE to that turn,
  then it is gone (30 min limit). Her bubble shows only her words.
- STYLE PANEL (one part selected; free, no model): text colour / background from the site's own tokens (brand, accent, text,
  soft, page, panel, dark), size steps, weight, align, padding 0-4, corners; "As designed" removes a pick. Stored as
  `hs-u-<prop>-<value>` classes (`edit.style`, list `edit.STYLE`; utilities in `hoola-site.css` use the token variables, so a
  raw colour can never be written - refused). Each pick = `edit_element op=style` -> one Undo step, a quick-checked version
  (v0.789 tier). Measured in the test: 0 model calls, Rs 0.
- COMMENTS for her team (`site_comments`, registered in db.init_db + self-heal): on a part of the page, numbered pins in the
  preview, list with Resolve / Reopen / Delete; never sent to Hoola. GET/POST /api/sites/{id}/comments,
  POST /api/sites/{id}/comments/{cid}/{resolved|open|deleted}.
- DRAW: pen strokes + numbered notes over the preview frame; Send to Hoola = POST /api/sites/{id}/markup -> the server's
  Chromium screenshots THAT page (the site's own files only) at her width / height / scroll, draws her strokes + note numbers,
  adds the notes as a list under the picture, stores it as her chat file and attaches it to her message. Side panels step
  aside while drawing.
- GET /api/sites/{id}/element = one part as the style panel needs it.
Tests: test_v0795_yeh_wala.py (6: tokens-only free style + Undo + it reaches the built page, selection once + her sites only,
comments CRUD, the marked-up screenshot (real Chromium), source wiring, a Playwright walk: Select -> pill + style panel ->
brand colour -> new version -> her message carries <selected_elements> -> Comment pin + list -> Draw + Send -> hide / Done).
NOT VERIFIED live: a real model acting on <selected_elements> and on a marked-up screenshot on her server.

## v0.797.0 3D SCENES + THE GAME TOOL HUB (owner: "HOW BIG 3D GRAPHICAL STUNING GAME CAN BE BUILD VIA HOOLA AI --- IS THERE ANY WAY THAT OUR ENGINE WILL CONNECTED TO 100 OF PERFECT GAMING DESIGNING TOOLS" → "GO BOTH")

**1. 3D scenes as checked data.** `gamedesk/scene.py` gains the 3D half of the v0.545 rule — the model writes a SPEC,
Hoola checks it in code and GENERATES the `.tscn`, and every scene is loaded in the real engine before she sees it.
Measured in Godot 4.7.2 headless BEFORE a line was written: Vector3 position / rotation_degrees / scale, primitive meshes
carrying a StandardMaterial3D (albedo, metallic, roughness, emission), lights with shadows, a current Camera3D, a
WorldEnvironment (colour or procedural sky, ambient, fog, glow), 3D collision shapes, Vector3 animation tracks, and a
`.glb` model placed by name all load exactly as written; a `.glb` imports headless and instances. The spec now takes:
20 3D node types (NODES3D), `mesh` on a MeshInstance3D (box / sphere / cylinder / capsule / plane / prism / torus +
`material`), `environment` on a WorldEnvironment (sky top / horizon / ground or a background colour, ambient, fog, glow),
3D shapes (box / sphere / capsule / cylinder), light / camera props, and **her APPROVED 3D models** from the Assets tab
placed with `{"model": "<asset key>"}` → `res://assets/<key>.glb` (`scene._models_of` reads the same files a build
copies; a model that was not approved, a path-like key, a model root, or model + type together are refused by name).
`verify()` copies the models in and runs Godot's import first, exactly as a build does, so a model that cannot import is a
FAIL, never a pass; the probe now also reports `three`, `meshes`, `lights`, `cameras`. Every unknown key inside a mesh,
material or environment is dropped AND named (a `script` key inside a mesh is refused like a `source` key on a node), and
the emitted text is still re-scanned for an embedded script. The SCENE prompt teaches what a stunning 3D scene is made of
(a sky, one sun with shadows, a little fog, a framing camera, real roughness / metal, emission where things glow, models /
instances for repeats); the tool description was rewritten to keep every honesty rule inside the registry's 1,200-character
cut (the first draft lost "cannot SEE how it looks" to that cut — caught by the suite). Proved live: a 15-node courtyard
with sky, sun shadows, fog, glow, a glowing spinning diya and three instances of a real `.glb` chair → PASS with 5 meshes,
1 light, 1 camera and the `spin` animation counted by the engine; the same scene with a missing model file → FAIL.
`tests/test_v0792_scenes3d.py` (20) + the 2D suite (13) = 33 green. NOT BUILT: TileMaps / GridMaps and shaders. A headless
check proves a 3D scene loads and counts what is in it; it cannot SEE how it looks — said in the tool, the view and the code.

**2. The Game Tool Hub, researched.** `docs/GAME_TOOL_HUB_PLAN.md`: 110 game-making tools classified into four lanes
(Hoola's own server / cloud API with her key / the vendor's own MCP / her own machine), each with its official API, official
MCP, the licence clause that decides, cost, and status — **62 have an official route today** (lane 1: 15, lane 2: 25,
lane 3: 13, lane 4: 9; 19 already built), 8 need a partner deal, 9 are blocked (no API or the licence forbids Hoola's shape),
31 unverified with what would settle each. Build waves start with CC0 libraries (Poly Haven, Kenney, ambientCG) and her-key
3D / audio (Meshy, Tripo, ElevenLabs). Findings that tighten the moat plan: **Epic DOES ship "Unreal MCP" in UE 5.8**
(Experimental, localhost, no auth — re-checked by the lead on Epic's own page); the AI-3D vendors' terms forbid a shared
Newtika account (her key and her plan, always); Tripo's free tier keeps all rights; Blender's new official MCP runs
model-written code unguarded, so Hoola's guarded runner stays the server path. One question is the owner's: most official
vendor MCPs sign in with OAuth to HER vendor account — whether that fits her "no consumer-subscription OAuth" rule.

Also healed: four game-role tests still asserted the old Hinglish "hired nahi" after main's English-tools commit d84057023.


## v0.800.0 HOOLA VOCAL (built as 0.787; owner: "NOW LETS WORK ON 11LABS ::: HOOLA VOCAL ::: clone VoiceStudio and make same 11labs for hoola end to end")

Full plan, the licence finding and the ElevenLabs-by-feature table: `docs/HOOLA_VOCAL_PLAN.md`.

- **Licence:** VoiceStudio is AGPL-3.0 and its default weights are CC-BY-NC. Read for the feature map only; ZERO code or weights
  copied (a test asserts it). Everything runs on Hoola's own engines.
- **Server:** NEW `server/app/vocal/service.py` (rules) + `vocal/api.py` (20 routes under `/api/vocal`), switch `vocal_page`,
  console flag `vocal`. Storage `data/vocal/<tenant>/vocal.json` + `audio/` + `samples/`.
  `tts`, `dialogue`, `preview`, `voice_clone` (consent must be True; bytes sniffed, never the file name), `voice_design`
  (refuses "sound like ..."), `voice_remove` (deletes the recording), `rule_add/remove` + `apply_rules`, `pieces` (cut at sentence
  ends) + `join_wavs` (one format only - two kinds of voice in one dialogue are refused, not garbled), `sfx`, `cleanup`, `music`,
  `project_save` / `chapter_make` / `project_export`, `history_remove`, `audio_file` (id shape checked, tenant-scoped), `usage`,
  `connected()` = the honest switchboard.
- **Console:** NEW `static/console/vocal.js` (overlay `#hvRoot`, twelve pages, a player bar), sidebar row "Hoola Vocal" under Hoola
  Interactive. The Interactive design block in v2.css is now scoped `:is(#hiRoot,#hvRoot)`; Vocal's own pieces are the `.hv-*` rules.
- **Live bug fixed (in Hoola Interactive since v0.774):** `v2.js` line 234 sends every click on `[data-v]` to `go()`. Both pages'
  tabs carried `data-v`, so one tab click hid the page and returned her to chat. Renamed `data-val`. RULE: inside a full-page overlay
  never use `data-v`.
- **Tests:** `test_v0787_hoola_vocal.py` (11): rules applied by code, long text cut and rejoined exactly, consent, sniffed bytes, no
  named-person imitation, dialogue casting, chapters + export, effects determinism, history / usage, the not-connected switchboard,
  no AGPL names, and a real-Chromium walk of all twelve pages (title once, no sideways scroll, her text never run as HTML, a tab
  click stays on the page, the typed line reaches the server with her voice and language).
- **NOT VERIFIED:** every engine was faked in the tests. No real voice has been heard from this page. Clone and design need the GPU
  lab, which is not connected on her server.

## v0.801.0 APP STUDIO PREMIUM PASS (built as 0.797; their 3D SCENES + GAME TOOL HUB took 0.797.0, HOOLA CODE PHASE 5 0.798.0, DESK ROOM 0.799.0, HOOLA VOCAL 0.800.0 - REBASE PROTOCOL, all kept; owner: "THE WEB CONSOLE APP DEVELOPMENT SECTION LOOKS STALE AND OLD --- MAKE ALL PAGES FUNCTION PROPERLY, ALIGN THE TEXT, TAB, BUTTONS ETC PERFECT, MAKE IT MORE ADVANCED AND PREMIUM")

Every page of /console/apps was first walked in a real Chromium on a seeded built app (a kirana shop app with a finished
design and an Android build) at 1440 px light, 1440 px dark and 390 px, with screenshots of each page, before anything
changed. Every page loaded with no script error; what was wrong was the finish:

- Headers: Plan / Looks / Screens / Data / Business / iPhone had a title, Store / Health / Settings had none, Prototype
  had a different bar 10 px off the others. Now ONE header on every page (`head(title, right, sub)` -> `.phd`: 22 px
  title, one plain line under it, controls on the right), and ONE panel header row (`ph()` -> `.pnh`); plan
  sub-sections are `.psub`. The test holds that no panel keeps a bare `<b>` title.
- Tabs: the tab row ran past the pane (Settings fell off at 1440 px once icons were added). Now an underlined tab bar
  (ink line under the current page, icons per page) sized by a container query on the pane: icons only where they fit.
- Buttons: violet and black primaries mixed, sizes 28-34 px. Now one scale (34 / 30 px), primary = ink like Publish
  (violet stays the working colour), Business cards keep their button on the bottom line.
- Store: the raw browser "Choose File" box replaced by a styled key-file picker that shows the chosen name.
- Android: the 4-step pipeline is one strip with a coloured bar under each finished / running step.
- Settings: App details in two columns; inputs could run past the card edge (no min-width) - fixed.
- Work card: said "Starting..." after its steps had run (now "After: <last step>") and showed "0s" for steps with no
  recorded time (now no clock under 1 s).
- iPhone: the runner note said "iPhone apps compile on a Mac. iPhone apps compile only on a Mac: ... (APP_BUILD_MODE=
  github) (...)." - now `iosWhy()` says it once, brackets dropped.
- Plurals ("1 calls"), language codes shown as names (hinglish / en / hi -> Hinglish / English / Hindi).
- Phone width: a later Web Studio rule pinned the chat column at 440 px and pushed the page sideways - the chat takes the
  full width, the top bar keeps Publish whole and the rest as icons.
- English: "Design pakka" -> "Approve design", "Haan, make 3 looks" -> "Approve plan · make 3 looks", "Waiting for your
  Haan", the feature-switch / language / list-change examples, and two server lines the Studio shows: the approve line
  (`appmaker/service.py`) and the crash summary (`appmaker/quality.py`, "No crash from any phone in N days").
- Motion: the page fades in once when she opens a page (`pane.dataset.fresh`, class `pin` - `.in` is the input class and
  drew a border round the whole page), never on the 2 s poll redraw; off under reduced motion.

Styles = the `v0.794 APP STUDIO PREMIUM PASS` block at the end of `appstudio.css`, scoped `.ws-app`, tokens only (the
test holds no raw hex in it). Tests: NEW `test_v0801_app_studio_premium.py` (markers, English server lines, a real-browser
walk of all 12 pages at 1440 and 390 px: header first, one current tab, no boxed body, no sideways scroll, panel headers,
no Hinglish, no "0s", the tab bar fits; motion once per page); `test_v0693_app_studio.py` pin moved to "Approve design".
NOT VERIFIED: on her own server with a real build in progress; the thread's older Hinglish job lines from other server
messages (design ready / failed / stopped) are unchanged.

## v0.802.0 GALTI PAKDO - the preview tells Hoola when it breaks; Try to fix follows a ladder (L6 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L6")
Before: an error in the preview was invisible to Hoola (and a section script's error was swallowed by its own try/catch);
she had to notice it and describe it. Lovable's error collector + Try to fix, in Hoola's shape:
- COLLECTOR (`hoola-site.js`, last block): runs ONLY in a frame whose page is /api/site-preview/... - `error`,
  `unhandledrejection` (AbortError skipped), failed `fetch` (5xx = Data error, network = Data error) and `window.__hoolaErr`
  (called by the build's per-section catch with `pages/<page>/<section>.js`; on her live site nothing defines it, so the catch
  stays silent as before). Max 20 per page load, posted to the parent window only.
- RELAY (Studio): only messages from its own preview frame; batched 1.2 s; POST /api/sites/{id}/preview-errors with her login
  (64 KB cap -> 413, 20 items, masked by `ops.clean_message`: emails, long numbers, query strings; the preview's private link
  is cut from messages and stacks).
- STORE (`site/galti.py`, table `site_errors`, registered in db.init_db + self-heal): one row per fingerprint (kind +
  message with numbers folded + file + line): count, page, version, stack (6 lines), first / last seen, status
  (open / ignored / fixed - it reopens if it comes back), the LEDGER of attempts. A site that stopped on a build problem
  shows a Build problem card (GET /api/sites/{id}/errors).
- CARDS: above the chat box (up to 3 + "N more") and a "This page hit a problem" bar over the preview: title (Page error /
  Data error / Build problem), page, times seen, version, Show details (file:line, stack, attempts), Ignore, Try to fix
  (Ctrl+Enter when the chat box is empty).
- THE LADDER (plan section 8): Try to fix -> POST /api/sites/{id}/errors/{eid}/fix -> the Build message + `<error_to_fix>`
  (the error, its file, every earlier attempt and its result) read ONCE by that turn via `turnmode.site_block`; the model is
  told to find the cause first, change as little as possible (edit_lines) and NOT claim it fixed. An attempt is marked
  'did not fix' when the same error is seen on a version newer than the one it started from. After two that did not hold,
  the button and the server switch to "Plan for root cause" (Plan mode, "what have we already tried") - never a third blind
  patch. Not seen on a newer version after an attempt = "Not seen since vN" (proven by the preview, never claimed).
- AGENT: `website_dekho what=errors` (+ all) - the open errors with the ledger; the description says read before fixing.
NOT BUILT: the plan's "5 free fixes a day" (Hoola has no per-turn charge to waive, so nothing says free); ladder steps 3-6
stay manual (History > restore a version already exists; rebuild one section = action=change; remix not built).
Tests: test_v0802_galti_pakdo.py (8: one card per fingerprint + masking + caps + her sites only, the ladder two fixes then a
plan with the ledger in the turn, not-seen-since / ignore / reopen, build problem + routes + the agent read + 413, section
errors only in the preview, the preview link never kept, source wiring, and the PLANTED-ERROR walk: a section that throws ->
the card names pages/home/hero.js -> Try to fix -> one exact edit -> the next preview is clean - fixed on try 1).
NOT VERIFIED live: a real model fixing a real error from <error_to_fix> on her server.


## v0.803.0 GAME DEV ENGINE LOOK (built as 0.802; their GALTI PAKDO took 0.802.0, both kept; owner: "NOW MAKE IT MORE STUNING ADVANCE AND A REAL GAME ENGINE FEEL DESIGN WITH ANIMATIONS AND GRAPHICAL VISUALIZATION IN IT" -> five engine boards on the design canvas (v2 · Engine look) -> "GO BUILD - WHOLE APP, REAL GAME IN VIEWPORT")

The whole Hoola Game Dev app (`/console/games`) redrawn as a game engine, behaviour unchanged.

- **Always dark.** `gamedev.js` sets `data-theme="dark"` + `html.gdv-engine` on load; `gamedev.css` puts one engine palette on
  `:root.gdv-engine[data-theme]` (specificity above v2.css's dark block). The embedded console game pages (board, bible,
  scenes, QA, release, crew roles...) read the same tokens, so they wear the engine look without their own CSS changing.
- **Home.** Engine bar (`#gdvEbar`, `drawEbar`) with only real numbers: Godot ready / not installed, games being made, games
  that play. Hero with a living pipeline loop (`loopHtml`: Hoola's six steps, work flowing round; the middle names her newest
  game that plays). Game cards get a living drawn thumbnail when there is no screenshot (`sceneArt`: runner / night skyline /
  tile board - decoration) and a status badge. Studio charts (`statsHtml`, `#gdvStatsBox`, redrawn by the home poll) from her
  own games only: the state split, versions built per game, frame rate measured on the server - a card with nothing real
  to show is left out. The six steps became a connected strip.
- **Workspace = editor.** Engine top bar (web build version + server fps chips when measured), the Hoola chat as a dock,
  tabs. The Play tab (key `play`, label "Editor") is the REAL game in the viewport - the same web build the private link
  opens - with its own toolbar (`viewportAct`): play from the start, stop (the frame goes blank, an overlay offers Play),
  phone / tablet / computer size, full screen (falls back to a toast), open in a new tab. Inspector: version, screen,
  measured performance as bars, Hoola's checks, the private link + QR, the change box / progress. Output dock: the real
  checks, warnings and version notes as a log; a versions timeline with the restore buttons.
- **The viewport is never rebuilt by a poll.** `.gdv-stage[data-key]` = play link + live version: the same key keeps the
  stage node (only the inspector and the dock are swapped), a NEW version reloads it (before, the same link kept showing
  the old build until a reload).
- **Build pipeline** (`pipeHtml`) on the progress card: design, code, build, bots play, your link - the real stage glows,
  work flows along the line into it; the pct / say / stage hooks still update in place.
- design.md shown as an editor file tab. Every loop is off under the computer's reduce-motion setting and Hoola's Calm.
  Type rules kept: weights <= 600, nothing under 12px, no all-caps (mono labels are lower case).
- Board embed fix: a two-word role chip on a task card wraps instead of overlapping the line under it.

Tests: `test_v0783_gamedev.py` 20 + the release suites; screenshots checked by eye at 1440 and 390 (home, editor, design,
building, board, crew). NOT VERIFIED: on her server with a real Godot build (the walk uses a stand-in web page as the game).

**NOT VERIFIED:** no real Claude suggestion, no real GitHub comment feed, no real FCM push, no real program calling the
trigger. The trigger's hourly limit is per task row (not per IP). The phone app has no Scheduled screen (console only).
**Not built from the plan's Phase 5 line:** live "subagent" children as separate panes (the passes are a card, not
panes). Deploy: vps-ops deploy (server-only; no new pip; one new table + five nullable columns make themselves).


## v0.804.0 HOOLA PROMPTING P1-P3 - the understanding engine, the Improve button, the Prompting page (built as 0.796; their 0.796.0-0.803.0 took the numbers - REBASE PROTOCOL, all kept; owner: "GO P1 TO P3")

Plan: `docs/HOOLA_PROMPTING_PLAN.md` parts 2-6 and 11. Research: `docs/research/prompting/00_INDEX.md`. The owner chose to
test everything together at the end, so P0's live card has NOT run: these three sections are built without its numbers.

**P1 - the engine, `server/app/prompting/`**
- `anatomy.py` - the parts a complete ask has, as data: web (what / who / the one key action / pages / look / content),
  image (subject / scene / kind / exact words / shape / colours / layout / light), script (platform / length / audience /
  message / hook / last line / tone / language). `required` slots are the ones worth a question.
- `brief.py` - `understand(tenant, text, section)`: (1) code reads what is certain - `facts_of` (price, percent, phone,
  time, date, quoted words; copied exactly, locked) and `code_slots` (picture shape from 'story / banner / poster',
  script length + platform, language, the website action from 'whatsapp / booking / cart'); (2) `context.fill` puts in
  what Hoola knows (brand kit name / tagline / colours / tone), labelled her_memory, her own words win; (3) ONE small
  model call (`ASK[0]`, `net.ai.llm_json`, switch `prompting_fill_model`) proposes the remaining slots and `model_slots`
  checks it in code: a value it says is hers must share half its content words with her text (`supported`), any number
  not in her text drops the value (`_numbers_ok`), a praise / magic word drops the value, everything else is labelled
  hoola_guess; a model outage = a brief from code alone, never an error. `_finish` recomputes facts, missing and at most
  3 questions (a required slot that is empty or only a guess). `apply(brief, set, drop)` = her answers (strongest source)
  and removals; `validate` rebuilds any brief the page sends back (known slots / sources only, sizes cut, intent never
  altered). `score` = 0-100 in code with a reason per point lost (required 60, detail 15, no clash 10, limits 5, wording
  10) and the note "This counts what is in your prompt. It cannot promise the result."
- `dialect.py` - web (her line first, then labelled lines, FACTS exactly, NOT DECIDED YET as marked samples, MUST NOT),
  image (a described scene, exact words in quotes or "No text ...", aspect as a field), script (labelled lines + fmt /
  length / language / tone fields). `run` says where it goes: Web Studio box or the chat box. No magic phrase (tested).
- `recipes.py` - 10 image + 8 script starters with blanks (an empty blank leaves its slot OUT, never a made-up value) +
  the Web Studio's template library as ready website prompts. Marked as starters; no kept-rate claimed.
- `store.py` - table `prompt_saved` (registered in `db.init_db`, self-heals per engine), fenced to the tenant, 200 max.
- `api.py` - GET /sections, POST /understand, POST /compile (no model), GET /recipes, POST /recipes/use, GET / POST /saved,
  GET / DELETE /saved/{id}. Every route only reads and writes text.

**P2 - the Improve button** `static/console/improve.js` (`HoolaImprove({api, esc, toast})` -> mount / open / sections; the
last instance at `HoolaImprove.ui`) + `improve.css` (own tokens, prefix hpi-, light + dark, no blur). The sheet shows her
words, chips per slot coloured by source (your words / your business / Hoola's suggestion / missing), locked facts,
questions with tap answers, the score and the finished prompt; `Keep mine` / `Use this prompt`. Wired into: the console
chat box (`#impBtn` in the chip row; a non web / picture / script line gets a 3-way choice or Keep mine), the Web Studio
home box (`data-improve`, section web), Create Image (the old Enhance button opens the sheet when it is loaded; Create
Video keeps the old Enhance). After Use, the button reads Undo and restores her text exactly until she edits.

**P3 - the page** `/console/prompting` (`promptapp.html`, `prompting.js`, `prompting.css`; route + `prompting` in
/api/console/config; console sidebar row). Home (one box, Auto / section chips, recipes, Continue, what Hoola knows),
workbench (her words + "Read my words again" | chips, facts, questions | score, prompt, Open in Web Studio / Put in the
Hoola chat, Copy, Save), Recipes (search, kind, blanks form; a website template opens as a ready prompt), My prompts.
Run only HANDS THE TEXT OVER (`hoola.prompt.toWeb` read once by webstudio.js into its box; `hoola.flow.toChat` for the
chat box) - nothing is sent or built for her.

**Tests** `server/tests/test_v0804_prompting.py` - 17, no model: section guess, locked facts, code slots, the model
checked by code, model outage, answers / removals / validate, score reasons, dialects, brand fill, recipes, routes end
to end, tenant fence, switch off, wiring, and 2 real-browser walks (the page at 1360 + 390 px; the console chat box and
the Web Studio with Use + Undo). Screens were looked at by eye (light). Stamp count in v2.html 29 -> 31.

**Also fixed (found while wiring the button)** `bazar.service.ensure_user`: on her FIRST Connectors visit the page's
lists load together, two requests both created her bazar user row and the loser answered 500 (UNIQUE constraint failed:
bz_users.id). The loser now reads the row. Test `test_first_visit_race_on_the_connectors_user_row`.
`test_v0781_connectors_page::test_connectors_page_in_a_real_browser` is unreliable here on main too (3 of 3 failed on an
untouched main checkout: the sign-in window's toast is not seen within 30 s) - not from this change.

**Not built / not verified**
- The phone app's composer button (Flutter cannot be compiled here; a CI-only change was left out on purpose).
- Sections beyond web / image / script (P5-P6), Create Video / Script-writer page buttons, the outcome ledger (P4),
  price shown inside the workbench (each engine still shows its own price card), dark mode looked at by eye.
- No real model has filled a brief on the server: the fill call's quality on GLM / Haiku is unknown until used live.
- P0's live card has not run, so there is no measured gain behind these three sections yet (owner's choice).

## v0.805.0 LANGGRAPH G6 (built as 0.799; their v0.799-v0.804 landed while it was tested - REBASE PROTOCOL, both kept) — voice as a channel of the same graph (11 Nov 2026; owner: "GO G6")

Phase G6 of `docs/LANGGRAPH_TURN_PLAN.md` (bug class 10: call and chat are two engines), only when `chat_graph` is on (default OFF; the old call path unchanged). Gemini Live stays the voice: audio, live session, parking, billing, persona and the declared tool list / budget are untouched.
- A call's `santosh_kaam` already reached `turngraph.run_steps` with the switch on (nodes, G1 ledger, G2 tickets, G3 facts, G5 record); G6 makes the call a CHANNEL: prepare writes `channel` (call / chat) + `profile` (NEW `agent/turnchannel.py`: Haiku, short history, result cut, memory time cap, no compaction / thinking / hint lookup / MCP wait / long-job segment) into the checkpoint, so a call ask resumed after a restart stays a call-brain run. (The santosh helpers still read the speed choices from `VOICE_BRAIN_NOW`; the profile records them.)
- Delivery: `Call._delegate` hands the run a ticket (`turndeliver.CALL`); the deliver node fills it (record key, result, facts) and marks the call channel due; the call tells the result once - as the tool answer or later from the record (`_told_on_call`, `_late_from_record`); while the call is live the reply's push is recorded as held; after a hang-up the chat row + push are the delivery and the next call does not repeat it; held-then-hung-up = told on the next call once. `_late_result` reads the record first (stopped dropped, partial / stuck as before, draft-card only = waiting for her tap, talk-only = neutral line; a cancel drops it only if after the run began).
- `_check_spoken_claim` with a graph run behind it judges the 'ho gaya' by `turnfacts.verdicts` over the run's facts; the 90 s news excuse only for news that is not a graph run's.
- G4: a call ask that changes the chat's running job via kaam_plan reaches its thread (history line the next segment reads, or the steer queue while a segment runs); a job the call finished is marked told. A run queued on a record's ticket counts as busy.
- FIXED (graph path): on a voice-brain call the ask is her words + '(Call ne samjha: ...)' and the word 'Call' made every spoken stop look like stopping the call, so 'band karo' stopped nothing; her own words decide now.
- TESTS: NEW `test_g6_turngraph.py` 11 (graph run with ledger / facts / channel / Haiku, told once + push held, late result from the record, hang-up -> chat push only, held then hung up -> next call once, spoken stop stops the ask, false spoken claim corrected from facts, call reaches the long job thread, registry walk every tool reachable + one undeclared tool end to end, restart keeps the channel, switch off unchanged); g0-g5, test_voice, v0550, v0630, v0634, v0660, v0657, v0649, v0691 call team, harness2, routines same off and on.
- FOUND on the old path (left as is): with the switch off a result returned as the immediate tool answer is also queued as 'That big job is done' late news (the v0.657 hang-up callback runs before `_delegate` resumes).
- NOT COVERED: declared tools / MCP tools / auto-rescue / hold-OTP flows on a call still run directly, not via the graph; the profile is recorded, not yet applied by the prepare node; after a hang-up the reply stays on the call record (no chat copy - the push opens the call record); spoken claims backed only by declared tools use the old check; nothing verified live (no real Gemini call / restart / phone). Next: G7 default ON + delete the old loop.

## v0.806.0 HOOLA CODE PHASE 6 (built as 0.799; their v0.799-v0.805 took the numbers meanwhile) — network levels with an allow-list proxy, keys added outside the box, GitHub events, multi-repo sessions, the phone screen redrawn (owner: "GO PHASE 6")

The last phase of `docs/HOOLA_CODE_WEB_PLAN.md`. Five parts. Nothing here changes who decides: opening a PR on a public
repo, posting a review and merging are still her taps, and every new way to START work makes an ordinary session.

**1. Network levels for the box** (`server/app/devlab/net.py`, `netproxy.py`; switch `dev_net`, default OFF).
A command in the box had no network at all. Per repo (Settings > the repo > "Network for commands") she now picks:
No network (default) / Package registries and her hosts / Any public website. At every level above none the box still
has no route of its own: it is put on a Docker network made with `--internal`, and the one way out is a small allow-list
proxy in its own container (`hoola-lab-proxy`: read-only, no capabilities, not root, 256 MB) which is also on the
default bridge. Each command gets its own pass (`net.grant`: id + secret, a rule file the proxy reads, removed when the
command ends, swept if a command died). The proxy serves only `CONNECT host:443` and `http://host:80`, refuses an IP
address instead of a name, refuses a host off the list by name ("X is not on this repo's allowed list"), and after
resolving refuses any private / loopback / link-local / CGNAT address - so a box can never reach her own server, the
Docker host or a metadata address through it, even on "Any public website". "Limited" always allows 17 package
registries (PyPI, npm, Maven, Gradle, pub.dev, crates, Go, RubyGems, NuGet, Packagist) and NOT GitHub. A proxy that is
not running never turns into an open network: the command runs with none and says so. The one-time setup step is
unchanged (it has the network, as before).

**2. Keys added outside the box** ("network secrets"). Per repo, a key for ONE exact host (header name, optional word
like Bearer). Typed only on the settings screen (`PUT /repos/{o}/{n}/secrets`), sealed with the vault, returned by no
route. For that host the proxy answers the box's TLS itself with a certificate for that one host signed by this server's
own lab CA (`data/devlab/net/ca.pem`; the box is told to trust a bundle, the CA key is never mounted into a box), adds
the header - replacing whatever the box sent - and makes the real, verified TLS connection. Never on plain http. Other
hosts are tunnelled untouched. If a host echoes the key back, the engine hides it before the model or the page see it.
At most 5 a repo.

**3. GitHub events** (`server/app/devsahayak/events.py`; switch `dev_events`, default on). Built as a signed REPOSITORY
WEBHOOK, not a GitHub App: an App needs her to register one and keep its private key on the server; a webhook gives the
same events with her existing token. Settings > the repo > "Connect GitHub events": Hoola adds the webhook with her
token when the token may (Webhooks: write); when it may not, she is shown the address and the secret ONCE to add it
herself. `POST /api/devsahayak/github/{id}` believes a delivery only when `X-Hub-Signature-256` matches (a wrong id and
a wrong signature are the same 401), runs a redelivery once, ignores bots and Hoola's own `hoola/` branches. A scheduled
task can now "start" on: an issue label, a new issue, a new pull request, a CI failure, a push (label / branch filter).
By default only HER events count (the login the token belongs to); "Anyone in the repo" is honoured on a private repo
only. The event's own words (an issue title) ride along inside `<trigger_payload>` as data. A new pull request from
someone else gets a DRAFT review (the existing review flow; posting is her tap). 10 runs an hour per task.

**4. Multi-repo sessions.** Composer "+" > "Add another repo…": "Read it" attaches up to 3 of her other repos to the
session read-only (`DevTask.refs`; `engine.Session.ensure_ref` puts the default branch under the session's own folder
with secrets hidden; the model gets ONE extra tool `other_repo` = ls / glob / grep / read; nothing there can be changed,
committed, pushed or run). "Change it too" (up to 2) starts a LINKED session per repo (`DevTask.grp`), each with its own
pull request and the same checks, each reading the others; the Session card shows "Same job in …".

**5. The phone screen** (`lib/ui/devsahayak_screen.dart`, redrawn by a parallel agent): title Hoola Code; sessions
grouped Working / Needs you / Earlier; New session box (text, repo, mode); the session page with folded steps, Thinking
toggle, changed files + diff sheet, question choices, the suggestion chip, the message box (note / answer / revise),
Stop, Open the PR, Fix CI, Fix reviewer comments; Scheduled tab with Run now + Pause. Merge keeps the old confirm card
exactly. Compiled by CI only (no Flutter in the sandbox).

**Also fixed (found by the browser test):** a closed dialog on the Hoola Code page kept its HTML, so a one-time trigger
token or webhook secret stayed in the page after "Done". Every dialog is emptied when it closes.

**Routes** (under `/api/devsahayak`): PATCH `/repos/{o}/{n}` takes `net_level`, `net_hosts`; PUT `/repos/{o}/{n}/secrets`,
DELETE `/repos/{o}/{n}/secrets/{host}`; POST / DELETE `/repos/{o}/{n}/events`; GET `/net`; POST `/tasks/start` takes
`refs`, `also`; schedules take `event`, `filter`; public: POST `/github/{id}`, GET `/labcheck`.
**Columns** (nullable, self-heal): `DevRepo.net_level / net_hosts / net_secrets / hook_id / hook_secret / hook_gh /
hook_seen`, `DevSchedule.event / event_filter`, `DevTask.refs / grp`.
**On her server:** `python -m app.devlab net` (vps-ops job `lab_net_check`) proves the network walls for real: the
inside-only network + proxy container, a registry reachable, a host off the list refused, no way around the proxy, no
private address, "none" still sealed, "full" works, and a secret that reaches the host (her own server answers with a
fingerprint at `/labcheck`) without being anywhere in the box. Only then set `DEV_NET=true`.

**Tests** `server/tests/test_v0799_hoola_code_phase6.py` (10): host / header rules; the proxy run for real with sockets,
TLS and curl (allow, refuse by name, IP refused, private address refused, no / wrong / expired pass, secret arrives,
replaces the box's own header, never on http, other hosts untouched); the box argv with a pass (inside-only network,
every other wall kept, setup never takes a pass); the proxy container's own walls; a pass per command, handed back,
echoed key hidden, proxy down = no network, `dev_net` off = nothing changes; settings + sealed secret; GitHub events
(signature, redelivery, hers only, anyone only on private, bots, Hoola's branches, CI failure, draft review, hourly
limit, connect both ways, disconnect); another repo read and never changed + linked sessions; one browser walk.

**NOT VERIFIED:** the inside-only Docker network and the proxy container have never run (no Docker in the sandbox) -
that is exactly what `lab_net_check` is for, and why `dev_net` is off; no real GitHub delivery has arrived; the phone
screen has not been seen on a phone. **Not built:** a GitHub App; one session that opens pull requests in two repos
(linked sessions do that instead); reference repos are not mounted into the box (read through the tool only); secrets
work for http(s) APIs only (not a database password); the phone has no settings for network / keys / events.
Deploy: vps-ops deploy (server-only; no new pip; columns make themselves), then `lab_check`, then `lab_net_check`, then
`DEV_NET=true` in .env if every line says ok. GitHub events need PUBLIC_BASE_URL (https) on the server.

## v0.807.0 BAHI A0 - the GST & Accounts employee, foundation (built as 0.806; their HOOLA CODE PHASE 6 took 0.806.0 - REBASE PROTOCOL, both kept; owner: "LET WE DEVELOP A FULL GST AND ACCOUNT EMPLOYEE --- I HAVE WHITEBOOK APIS OF GST" -> "GO A0")

Plan: `docs/ACCOUNTS_EMPLOYEE_PLAN.md` (A0-A12); research `docs/research/accounts/01-04` (what Hoola has, the market, the rules +
calendar, the WhiteBooks API). Hoola already had the accountant in seven engines that never talk; A0 is the floor they all stand on.

NEW `server/app/bahi/`:
- `models.py` - `acc_docs` (the register: one row per (source, source_ref); gstin, period, direction, kind, number, date, party + GSTIN,
  pos, taxable / CGST / SGST / IGST / cess / tax / total, irn, status confirmed | draft | gone, confidence, reason, problems),
  `acc_periods` (open | locked per GSTIN + month), `acc_events` (append-only trail with before / after), `acc_gst_conn` (her GSTIN's GSP
  connection - created now, filled by A1; IRP / EWB passwords sealed, no portal password ever), `acc_wb_calls` (the call meter). Registered
  in `db.init_db` + `ensure_tables()` self-heal.
- `rules.py` + `rules/*.json` - rules as DATA: `gst_rates` (slabs to 21 Sep 2025 and GST 2.0 from 22 Sep 2025, HSNS cess listing),
  `due_dates` (TDS 7th, GSTR-1 11th, IFF 13th, 2B 14th, PF / ESI 15th, GSTR-3B 20th with the LOCK said, PMT-06 25th), `limits` (e-invoice
  Rs 5 cr / Rs 10 cr + 30 days, IRN cancel 24 h, EWB 180 days / Rs 50,000, Rule 37 180 days, s.16(4) 30 Nov, MSME 15 / 45 days, the
  July 2025 3B lock, the 3-year bar), `forms_map` (24Q -> 138, 26Q -> 140, 27Q -> 144, 27EQ -> 143, Form 16 -> 130, 16A -> 131, 12BB -> 124,
  13 -> 128, 15G/H -> 121, 3CA/CB/CD -> Form 26). Every row: `basis` (primary | primary-listing | provider-spec | secondary-confirmed |
  unverified), `source`, `checked_on`, `review_by`; the loader refuses a row without them; `usable()` = not unverified; `freshness()`
  (by basis, stale, unverified) for the desk; `slabs_on(date)`; `dues_for(period, scheme, employer, tds)` with days left.
- `wb.py` - the WhiteBooks client built to their OpenAPI specs (NOT their prose docs): `client_id` / `client_secret` headers per product
  (gst | einv | ewb, one pair may serve all) + `email` query on every call; sandbox / production host from WHITEBOOKS_ENV; success ONLY on
  `status_cd == "1"` (HTTP is 200 on failure); `WbError(code, plain message)` - WB_ERR_9001 / 9000, NIC 2150 / 2174, not_configured, cap,
  rate, bad_reply, network; `safe_url` scrubs password / otp / evcotp from every log line (the EWB password rides a query string); a
  per-tenant daily cap (`whitebooks_daily_calls` 300) and per-minute guard (`whitebooks_per_minute` 50, under the sandbox's 60) refuse
  BEFORE the call; every call metered; `shape()` keeps structure, never values; primitives ping, public_search, rettrack, otp_request,
  auth_token, refresh, ledger_balance, einv_auth, ewb_auth; `find_txn` looks for the OTP transaction id where GSTN puts it.
- `wbcheck.py` - `python -m app.bahi.wbcheck` / vps-ops `wb_check`: sandbox = ping -> GSTIN search -> filing track -> OTP request -> auth
  token with the spec's sandbox OTP 575757 -> refresh -> ledger balance -> e-invoice login -> e-way bill login, each PASS / FAIL / SKIP,
  the reply SHAPES saved to data/bahi/wb_shapes.json (no values); production = the ping only (no taxpayer call, no OTP, ever).
- `register.py` - adapters (read-only): GST Sahayak `gst_docs`, Thok billed orders + purchases (tax split by intra / inter), office
  bills, her app + website invoices / credit notes via `appmaker/hisaab.build` (the same numbers her CA gets). `sync(months)` is
  idempotent (fingerprint), flags the same document from two sources on both rows (purchase "inv" vs "bill" normalised), HOLDS a change
  to a locked month (row kept, `changed_after_lock` note, trail), marks a row its source dropped `gone` (never deletes), writes the trail;
  `listing`, `summary` (sales / purchases taxable + GST, credit notes netted, problems), `events` (labelled "GST Sahayak · INV-7 · Kumar
  Stores", never an internal id), `set_lock`.
- `service.py` overview (employee status, last + this month, last month's dues falling due now, WhiteBooks status - never a key / the
  email -, connections without secrets, rules freshness, the trail, the phases list with honest states); `api.py` GET /api/bahi/overview,
  POST /api/bahi/sync, GET /api/bahi/register, GET /api/bahi/rules, POST /api/bahi/periods/{period}/lock.
- Settings (config.py): `bahi_enabled`, `bahi_filing` (False - prepare only), `whitebooks_env`, `whitebooks_email`,
  `whitebooks_{gst,einv,ewb}_client_{id,secret}`, `whitebooks_ip_address`, `whitebooks_daily_calls`, `whitebooks_per_minute`,
  `whitebooks_timeout_s`, `whitebooks_sandbox_*` (only the check reads them).

Hub: the "Accounts Assistant" row goes live as **GST & Accounts** (does / needs / never), hiring gates no existing tool. Console: its own desk
`static/console/bahi.js` (view `accountsdesk`; employees.js DESKS accounts -> accountsdesk): hero, tabs Overview (dues with days left and
"date not yet checked on a government site" where unverified, last / this month tiles, Sync, the trail), Register (month / type / source
filters, notes on flagged rows, Lock / Unlock a month), Rules (by basis, the unverified list, re-check due), Connection (keys set per
product, calls today / cap, the last contract check steps, the .env line NAMES when unset), Plan (A0 built, A1 next...). Styles `acd-` on the
Desk Room `ddk-` scale; the tab row scrolls on a phone.

Tests: `test_v0807_bahi_a0.py` (14) - spec headers + email + sandbox host + meter; failures on HTTP 200 -> plain English; not-configured /
daily cap / minute guard refuse BEFORE the call; no password / OTP / secret in logs; shapes without values + find_txn; the contract check
on a mock sandbox + production pings only; rule rows carry source / basis / dates, GST 2.0 slabs, freshness; the month calendar; the register
(5 documents from 3 engines, idempotent, the double-entered bill flagged on both, a draft order not a document); a locked month holds a
change, unlock applies it, a dropped row is marked gone, the trail; routes + no secret in any reply; the Hub entry; console wiring + CSS; a
real-browser walk (hire from the Hub -> Open desk -> Register shows the two flags -> Connection says "Not set" -> Plan), light 1280 + dark 390.
Pins moved: test_v0317 / test_v0687 used "accounts" as the not-yet-live example (now "telecaller"); test_v0475 stamps 33 -> 34 (bahi.js).

NOT VERIFIED: nothing has talked to the real WhiteBooks sandbox (the keys are not on the VPS yet) - the client is built to the published
specs and the check exists to pin the real reply shapes the first time it runs. Not built (later phases): the GSTIN connect walk (A1), any
filing, chat / voice tools, the phone screen.

## v0.808.0 WAPAS - every version can come back, before launch too (built as 0.803; their GAME DEV ENGINE LOOK, HOOLA PROMPTING P1, LANGGRAPH G6, HOOLA CODE PHASE 6 and BAHI A0 took 0.803.0-0.807.0 - REBASE PROTOCOL, all kept; L7 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L7")
Before: a version kept only its BUILT pages, so "go back" existed only for her live address (hosting.rollback, after
launch); nothing undid one answer's change, and an edited message could not take the site back first.
- SOURCE PER VERSION (`site/wapas.py`): `service._make_version` now snapshots the section files and the row's plan, look
  (tokens + design kit), facts, styles, style, languages into `<site>/snaps/v<N>/` (JSON only; photos / media stay in place).
- RESTORE ANY VERSION: POST /api/sites/{id}/versions/{v}/restore (and `website action=restore_version`): sections + fields
  back, the hand-edit Undo stack cleared (it belonged to the other version), then a NEW version "Restored vN" through the
  normal save (checked) - so History stays a straight line and the restore is undone the same way. Enquiries, orders,
  app rows are DATA and never touched (said every time). Refused while a build runs; a version made before snapshots
  says so plainly (it can still be Put live if it was published).
- BOOKMARKS: `site_versions.bookmark` (nullable column, added by the schema self-heal); POST .../versions/{v}/bookmark
  {name} (empty removes); a bookmarked version is always in the list, however old.
- WHAT CHANGED: GET .../versions/{v}/diff?against= (default: the version before it): every changed code file (readable
  code, unified diff, + / - counts, new / removed) + which design tokens changed; 60k cap.
- STUDIO: History = Bookmarks, then All versions (current, Live, bookmark name), Changes (inline diff), star, Restore,
  Put live... (the old live rollback, renamed so the two are not confused). Each reply that made a version: "Version N",
  Bookmark, Undo this change (back to the version before that answer; restores are never counted as an answer's change).
  Her message: Edit -> Revert and resend (the site goes back to the version before that message, then the edited words
  go). The chat redraws when a new version lands so every reply gets its own footer.
- E7 LIVE VIEW SURVIVES A RESTART (`site/stream.py`): slots are also written to `<SITE_DIR>/_live/<site>.json` (at most
  once a second while words stream, at once on finish / looks / clear); a restart or a second worker reads them back
  (sequence number continues, a section that was mid-write is marked stale until the build picks it up again).
Tests: test_v0808_wapas.py (7: any version back as a new version + undo the restore + refusals, data untouched,
bookmarks + diff routes, the agent action, the live view after a simulated restart, source wiring, a Playwright walk:
a change -> Version + Undo this change -> undone; Edit -> Revert and resend; History: Changes, Bookmark, Restore).
NOT VERIFIED live: a real restart of her server during a build (the restart is simulated by clearing the memory).


## v0.809.0 HOOLA 3D KIT (owner: "GO 3D GAMEPLAY" - the first of three, "ALL ONE BY ONE")

Before this, a 3D game meant the model writing a player controller, a camera, touch controls, enemies and a HUD from
scratch in every game - the place 3D builds break. Now those pieces exist once, written by Hoola and proved.

- **The kit** `server/app/gamedesk/kit/hoola_3d.gd` = the `Hoola3D` autoload (pack `kit3d`, `template.HOOLA_OWN`):
  `world` (sky, ambient, sun with shadows), `ground`, `block`, `moving_block`, `tree`, `mat`, `model` (her approved 3D
  model or null), `spawn_player` (walk + jump, keyboard arrows / WASD / Space AND a touch stick + jump button,
  knock-back, respawn after a fall), `follow_camera` (third person, distance 0 = first person, drag / Q E to look),
  `coin`, `enemy` (patrol / chase; touch = -1 life, landing on it removes it), `goal`, `hurt`, `make_hud` (coins,
  lives, messages, the on-screen controls). Signals: coin_taken, player_hit, player_fell, goal_reached, enemy_stomped.
- **Only in a 3D game.** `kit3d.wants(brief, design)` (3D / 3-D / third-person / first-person / low-poly ...; "2D",
  "match-3", "30 days" never match). A 2D game's project and prompt are unchanged. For a 3D design `ai._ctx` adds the
  kit's API to the code / fix / change prompts, and the design prompt shapes a 3D game for the kit.
- **Proof without a model** (`kit3d.proof`, `python -m app.gamedesk proof3d [--save]`, vps-ops `game_3d_proof`):
  Hoola's own game Diya Run 3D (`kit/proof_main.gd`, built only from the kit) goes through the real pipeline - guard,
  headless play, web export, browser playtest - then (1) `play_through`: a test player (`kit/proof_bot.gd`, only in a
  throwaway copy) starts it, walks a route, jumps the steps and WINS with the same keys a person uses; (2)
  `browser_touch`: in a real Chromium a tap starts it and the on-screen stick is held until the engine reports a coin;
  (3) `self_test`: the kit's rules in the engine - a guard's touch costs one life, a stomp removes it, a fall respawns,
  stick + jump button, coin, lift. `--save` keeps it as a finished game in her list with a private play link.
- Measured here (Godot 4.7.2 + Chromium): test player won in 6.6 s of game time, 24.4 m walked, 6 of 8 coins, top
  y 2.8 m, 3 lives left; touch collected 2 coins in a real browser; self-test 6 / 6; web download ~9.7 MB.
- Found while building: a headless engine has no window, so injected touch events arrive with broken positions -
  the self-test hands touch events to the kit directly and the real-browser check covers the true path.

Tests: `test_v0809_kit3d.py` 28 (3 need Godot, 1 of those a browser; all ran green here). NOT VERIFIED: no
MODEL-written 3D game has been built from the kit yet (that needs her server and model credit); the proof game has
not been played on a real phone.


## v0.810.0 PRAYOGSHALA WAVE 8

69 physics set-ups built and walked within tolerance (agents' walks + the lead's final walk, 68 / 68 labs): ug_analog_w8 (21:
diodes, LED, tunnel diode, BJT h-parameters and switch, push-pull, op-amp response / difference / analog computer, active
filters, JFET, DAC, ADC, sample-and-hold, 7805, PLL, counter, distortion meter, thermostat, cable noise - one shared analog
bench), ug_modern_w8 (13: work function, Hg ionisation, e/m Thomson / magnetron / focusing, Millikan both methods, Zeeman,
Planck, microwaves x2, plus existing Franck-Hertz, iodine, ESR), ug_matter_w8 (15: beta range, K-40, four Bethe-Bloch
stopping-power labs, XRD, nano XRD, band gap, piezo, Gouy, plus existing Quincke, magnetoresistance, P-E loop, dielectric),
ug_comp_w8 (19 computational labs on comp4-workstation, every one checked against an exact or independent answer), plus
pg:millikan-oil-drop. Coverage 456 -> 525 of 807 (school 78.4 / 91.5 %, B.Sc 86.8 %, M.Sc 38.1 %, PhD 28.6 %).
Not built and constants from memory: docs/PRAYOG_PHYSICS_LAKH_PLAN.md, "Wave 8".


## v0.811.0 GAME FREE LIBRARY - Tool Hub wave 1 (owner: "GO TOOL HUB WAVE 1" - the second of three, "ALL ONE BY ONE")

3D games needed real models and surfaces; until now Hoola could only place a model she uploaded herself. Now three
free libraries are connected, each through its official route (docs/GAME_TOOL_HUB_PLAN.md rows 47-49).

- **Kenney** - 53 low-poly models (platformer pieces, city blocks and roads, shooter props, racing track + trucks),
  2.7 MB, kept on Hoola's disk in `server/app/gamedesk/library/kenney/` with `index.json` and `LICENSE-KENNEY.md`.
  They come from Kenney's own GitHub starter kits (KenneyNL/Starter-Kit-3D-Platformer, -City-Builder, -FPS, -Racing),
  whose READMEs state the models are CC0. kenney.nl has no API and its download sits behind a donate dialog, so
  nothing there is automated. Each GLB pointed at a shared `Textures/colormap.png`; Hoola embedded it so every file
  stands alone. All 53 were loaded in real Godot.
- **Poly Haven** - public API (api.polyhaven.com, no key, unique User-Agent as its terms ask): models (the 1k glTF +
  .bin + textures packed into one GLB; over 12 MB is refused as too big for a web game) and textures (1k colour map).
- **ambientCG** - public API v2: materials; the colour map is taken out of the 1K-JPG zip.
- `gamedesk/glbpack.py`: `embed` / `pack` put every outside buffer and picture inside the GLB; a uri the caller did
  not hand in is an error, never a fetch. `facts` reads meshes / triangles / animations from the file itself.
- `gamedesk/library.py`: `search(q, kind, source)` (a library that is down is named and the others still answer),
  `get`, `add(tenant, project, source, id, kind, key)`. One network door `_fetch`: https only, a fixed host allowlist
  checked on every redirect hop, a byte ceiling per download.
- An added item is a DRAFT asset exactly like her own upload (`source library:<name>`, licence + credit + origin in
  its history) and enters a game only after her OK. It is never called AI: the game's AI credit line is not triggered,
  and the provenance page lists it as a library asset with its licence (class `library`). Fixed on the way: her own
  uploads were classified `unknown` there (the stored source is "her upload", the table said "upload").
- New asset kind `texture` (512 x 512, palette check off by default, free, only from the library or her upload - a
  request to generate one is refused). `Hoola3D.paint(node, key, tile_m, fallback)` puts it on a block or the ground
  (triplanar, so it tiles in metres); `Hoola3D.model(...)` already places an approved model.
- Where she uses it: Assets page > Free library (search, 3D models / Textures, Add); routes GET / POST
  `/api/gamestudio/{id}/library`; Hoola's tool `game_assets` action `library` / `library_add`, told to look in the
  library before making or generating a model.

Tests: `test_v0811_game_library.py` 13 (packer, Kenney files, search with one library down, host allowlist, draft ->
OK -> in the game and not AI, Poly Haven pack + size refusal, textures, routes, tool, real Godot loading a library
model + texture through the kit, and the real libraries when HOOLA_LIVE_LIBRARY=1 - run green here). NOT built: Meshy
(her key and her decision on vendor accounts first), HDRI skies, picture previews in the panel, Kenney 2D / audio packs.

## v0.812.0 ECC AGENTS IN HOOLA CODE (built as 0.794; other sessions took 0.794-0.811 meanwhile (their HOOLA CODE PHASE 5 took 0.798.0, PHASE 6 0.806.0) - REBASE PROTOCOL, all kept)
Owner (11 Nov 2026), after reading github.com/affaan-m/ECC: "ADD ALL MISSING ECC AGENTS TO HOOLA CODE --- MAKE HOOLA CODE
MORE POWERFULL AND SMOOTH THUS CAN PERFROM ANY HARD CODING TASK SMOOTLY AND PERFECTLY LIKE CLAUDE CODE".

Before: v0.402-v0.451 had adapted ~20 of ECC's agents as text inside `devsahayak/specialists.py`, used only AROUND a
round (PR review, CI fix rounds, self-review, plan pass); the v0.787 working-copy engine itself never saw them.
ECC checked at commit d2ef268 (v2.2.3): only 6 commits after the b38be6a snapshot, all its own CI - nothing to re-sync.

What is new:
- `server/app/devsahayak/ecc/` - the catalogue. 63 of ECC's 71 agent files condensed and rewritten as text (four
  parallel agents, one per part file; each prompt 1.5-2.6k chars, credited in its own first line, Claude Code-only parts
  and anything needing the internet dropped): `reviewers_lang.py` (17: python / typescript / react / vue / flutter /
  kotlin / java / go / rust / swift / cpp / csharp / fsharp / php / ruby / django / fastapi), `reviewers_more.py` (19:
  code / security / silent-failure / pr-test / database / commit reviewers, type-design, comment, performance, a11y,
  agent-evaluator, mle, rag, healthcare, bengali, seo, network-config, opensource-sanitizer, harmonyos), `fixers.py` (16:
  build-error-resolver + 10 language resolvers, tdd-guide, e2e-runner, refactor-cleaner, code-simplifier, doc-updater),
  `planners.py` (11: planner, architect, code-architect, spec-miner, network / homelab architects, code-explorer,
  docs-lookup rewritten for OFFLINE lookup in the box, network-troubleshooter, opensource forker / packager).
  `ecc.NOT_ADDED` = the 8 left out with reasons (marketing-agent, chief-of-staff, conversation-analyzer,
  harness-optimizer, loop-operator, gan-planner / generator / evaluator). `rules_text.py` = ECC's rules/ condensed
  (common + 21 languages). Each agent has a tool level: read (look only) / run (+ bash in the box) / edit (+ edit /
  write, with the coder's guards).
- `server/app/devsahayak/subagent.py` - the engine's `agent` tool, Claude Code's subagent shape: a fresh conversation
  with only the task the coder wrote, the agent's text + its level's tools, the SAME working copy through a copy of
  `engine.Tools` (secrets hidden, links never followed, workflows refused, read before edit; an agent's reads are not
  the coder's), ends with `report`. Several read / run agents asked in ONE reply run side by side (threads with the
  session's model / effort and the copied context); edit agents one by one. Limits `dev_agent_steps` 30,
  `dev_agent_minutes` 12, `dev_agent_max` 10 a round, `dev_agent_parallel` 4. An agent cannot start agents, push or end
  the round.
- `engine.py`: the coder's system prompt gets `AGENTS_HOWTO` (when to explore / plan / fix / review with an agent) +
  `ecc.roster()` (all 63 in one line each, best fits for this repo first) + `ecc.rules_for()` (the repo's languages,
  9k chars cap); tool list + `agent`; ECC's pre-commit hook as `ecc.gate` on the round's diff before `done` is accepted
  (console.log / debugger / breakpoint / pdb / pry / var_dump outside tests and docs, `.only` focused tests, conflict
  markers, key-looking lines) - ONE clean-up chance, then done is accepted.
- `specialists.py`: the PR review prompt adds the ECC reviewer for a language / framework the old notes did not cover
  (React, Vue, C++, C#, PHP, Ruby, F#, Django ...); a CI fix round on C++ / C# logs gets the ECC resolver (new log signs).
- `GET /api/devsahayak/agents` (roster + left-out list); the page draws `agent` (asked / reported, the report folds
  open) and `gate` steps, and an agent's edits / commands say "by <agent>".
- Switches: `dev_ecc_agents`, `dev_ecc_rules`, `dev_ecc_rules_chars`, `dev_ecc_gate` (all on).
- Tests `server/tests/test_v0812_ecc_agents.py` (11): every ECC agent in or left out with a reason, every prompt
  adapted (no Claude Code-only words), rules per language, suggestions / roster, the gate, the old review / fix paths
  on new languages, a REAL round through `engine.run` where the coder asks two agents in one reply (they run in two
  threads with read / run tools only, their reports come back) and the gate stops a `breakpoint()` before done; an edit
  agent must read first and cannot touch workflows; the round cap and the switch.
  Older Hoola Code suites re-run green with it (v0402 x2, v0787 engine incl. real Docker, v0789 safety, tech
  devsahayak, v0748 / v0768 / v0774 / v0777). test_v0473 `test_coder_routes_mounted` fails as before (an old red).
  FOUND + FIXED while testing: the gate first judged EVERY file in the diff, so a key file a box command planted (hidden,
  never shippable, the coder may not change it) refused `done` - the v0789 link / key test went 'explained' in long
  runs. The gate now judges only files that would ship (not hidden / key files / binaries / links); a test holds it.
  The roster's path matching was also made 0.08 s for a 4,000-file repo (compiled once, one pass).
NOT VERIFIED: no real model has driven an agent (scripted Claude only - the sandbox has no key); cost per round with
agents is not measured (each agent is its own model conversation, so a reviewed round costs more); no browser walk of
the new step kinds.


## v0.813.0 GAME ARENA RUNNABLE (owner: "GO ARENA" - the third of three, "ALL ONE BY ONE")

The Game Arena (v0.454) was built to answer "is a Hoola game any good?" with numbers. It had never run on a real game.

- **Found by reading it before running it:** `arena._one_card` - the function that takes a built game, lets the QA
  bots play it and writes the score card - looked for the web build in `<version>/web`. No build has ever had that
  folder: the exporter writes `<version>/build`. Every Arena test replaced `_one_card` with a stand-in, so nothing
  ever executed the line. The first real run would have reported EVERY game as "no playable build" - 0 % started -
  and that would have read as "Hoola's games do not work". `duel` had the same line. Both now go through
  `arena._web`, and `test_v0813_game_arena_real.py` runs the REAL `_one_card` on a real game row.
- **A free self-check** (`arena.selfcheck`, `python -m app.gamedesk arena check`, vps-ops `game_arena_check`): the
  500 briefs are checked (500 unique, 20 genres), then Hoola's own proof game (v0.809, no model wrote it) is built
  for real as the hidden Arena tenant and scored through the same path a run uses - the build is found, the QA bots
  (idle / monkey / keys) play it, the card is written - with the judge left out (the only part that needs a model).
  The game is deleted afterwards. A scorer that cannot measure a known-good game says NOT READY and why, before a
  rupee is spent.
- **Running it:** `python -m app.gamedesk arena run --n 3 --budget 150` (REAL: the model writes each game, so it
  spends money and stops at the rupee ceiling), `arena status`; vps-ops `game_arena_try` (3 briefs, Rs 150 ceiling,
  23-minute limit - starting it is her decision) and `game_arena_status`. `_one_card(..., judge_it=False)` exists
  for the check.
- Measured here (Godot 4.7.2 + Chromium, software graphics): the proof game started, loaded in 3.2 s, the bots'
  inputs changed its state, 0 errors, 3 state keys reported, playable = true; `reached_end` false in 12 s of random
  play (the game needs 5 coins and a climb, so a random bot not finishing it is expected); fun = NOT ASSESSED.

Tests: `test_v0813_game_arena_real.py` 6 (one in the real engine + browser, run green here) beside the 12 older
Arena tests. NOT VERIFIED: no real Arena run has happened yet - it needs her server, the model and her go-ahead on
the spend - so there are still NO quality numbers for any Hoola version, and the 2D / 3D briefs' real pass rate is
unknown. The brief set (SET_V 1) has no 3D briefs yet.

## v0.814.0 HOOLA CINEMA - the Create studio's Cinema section (built as 0.807; their BAHI A0, WAPAS, HOOLA 3D KIT and PRAYOGSHALA WAVE 8 took 0.807.0-0.813.0 (also ECC AGENTS and GAME ARENA RUNNABLE) - REBASE PROTOCOL, all kept; owner: "https://github.com/Autom8AI/Open-Higgsfield-AI.git -- read this repo first" -> "GO BUILD THE WHOLE SET AS HOOLA CINEMA END TO END")

**The read.** `Autom8AI/open-higgsfield-ai` is a fork (MATAI) of Anil-matcha's Open Higgsfield AI: a vanilla-JS page on Netlify
functions with no models of its own - every generation is a paid call to kie.ai or fal.ai. No LICENSE file (README says MIT).
Ideas only: zero code copied. Its real lesson was the product gap: Hoola had no video-to-video tools.

**What shipped.** One view `cinema` in the Create studio (`static/console/cinema.js`, which the studio hands its own helpers:
api, go, menu, upload, itemTile...; it lives in the studio's shadow root and uses its styles) with a hub and ten pages:
Cinema still, Motion transfer, Character swap, Item swap / edit, Restyle, Talking photo, Lip sync, Picture to video, Content
factory, Characters. Backend `server/app/cinema/`:
- `specs.py`: 16 models, each request shape read from the engine's own OpenAPI pages (docs.kie.ai) on 2026-11-11 - which field
  is a list and which a string, which durations are strings, which resolutions exist, size and length limits. `build()` is the
  only place a request is shaped and refuses anything the spec does not have. Presets as plain prompt text in Hoola's own words:
  27 camera rows (Auto + 26), 16 restyle looks, 8 looks, the Cinema still's camera / lens / focal / aperture / light.
- `kie.py`: createTask, recordInfo, credits, file-stream-upload behind ONE seam `_http`; 401 / 402 final; a createTask is never
  retried; the key scrubbed from every message.
- `service.py`: characters (a real person only with a recorded yes), `start()` (every refusal before a file leaves: tool / model
  match, word screen, rights tick, consent tick, confirm, daily cap, shape pre-check, then bytes-sniffed files, photos re-saved
  as clean JPEGs, uploads, createTask), talking photo with typed words spoken by Hoola's own voice (`create.service.voice`),
  the factory (scenes by the model, by rule when none answers; one confirmed batch that stops at the first refusal and keeps
  what started), `check()` / `refresh()` (finished video fetched once through the shilp link wall, sniffed, kept on the Create
  shelf with `ai_made`), `connected()` = what is not there, said on the hub.
- `api.py`: `/api/cinema` (overview), `/start`, `/still/prompt`, `/factory/scenes`, `/factory/start`, `/jobs/{id}/check`,
  `DELETE /jobs/{id}`, `/characters` (+ DELETE, photo). Behind `cinema_page`.
Also: 26 camera moves on the Video page (were 8), "Use in Hoola Cinema" on My creations tiles (`CIN.send`).

**Found while building.** (1) `HoolaCreate(...)` runs before `/api/console/config` answers, so `ctx.cinema()` is false at build
time and the view was never mounted - a studio tool behind a switch is mounted always and gated in `go()`. (2) A missing restyle
look raised ValueError past the route (a 500) - caught by its test. (3) Playwright's `document.querySelector` does not pierce the
studio's shadow root, so two overflow checks were passing on nothing; they read `shadowRoot` now.

**Safety note.** `image_edit` and `video_kit` refuse face swap. Cinema's character swap is behind two recorded ticks (her right
to the video; the person is her or agreed) or a saved character that carries a recorded yes. Listed as an owner decision in
`docs/HOOLA_CINEMA_PLAN.md`.

**Tests.** `test_v0807_hoola_cinema.py` 14: every request shape, presets, bytes sniffing + clean photos, motion transfer end to
end with the engine faked at `_http` (upload types, exact createTask body, tenant isolation, finish -> My creations once, no key
or task id in any answer), result link must be a public https video, characters + consent, talking photo with a Hoola voice,
restyle / edit refusals, the factory, the daily cap / 402 / no key, the key never in an error, routes + no foreign code, and a
real-browser walk (hub, ten pages with no overflow and no script error, her text never run as HTML, rights tick blocks the send,
typed words kept, exact bodies sent, factory scenes edited, 26 camera chips). Stamp count 34 -> 35.

**NOT VERIFIED.** No live engine call; rupee cost per job unknown until one runs; all users share the one server key.

## v0.815.0 APP KE PURZE (built as 0.802; other sessions took 0.802.0-0.814.0 meanwhile - REBASE PROTOCOL, all kept; owner: "GO DEEP IS ALL ANDROID AND IOS APP COMPONENT IS THERE" -> "GO 1 2 3 - DEPLOY PARALLEL AGENTS")

The audit (both native kits read file by file, a capability grep across Kotlin and Swift) found the kits strong on accounts,
data, money, maps, push and store work, and three kinds of gap. Four agents fixed them in parallel worktrees; merged here.

1. HONEST PLAN (`appmaker/capabilities.py`, `blueprint.py`, `service.py`, `agent/app_tools.py`, App Studio Plan page).
   The plan card listed 64 phone features by STORE POLICY only - nothing told it what the kit really builds, so a plan
   could promise Face ID or a home-screen widget and the app came without it, and `three_d` claimed SceneView / RealityKit
   while Android draws a server-rendered still and iPhone nothing. Every CAPS entry now carries `built` {android, ios} =
   yes / partial / no + `built_note`, decided by reading the kit code; `CP.gaps(ids)` and `caps_missing` on every blueprint
   (re-worked from the current table on view, so old plans are told too); the chat line says "Not in this version yet: ..."
   and the app_banao tool text forbids promising those; the Plan page has a "Phone features" panel with an Android and an
   iPhone pill per feature (Built / Partly / Not yet) - it replaced a chip line that never showed anything.
2. IPHONE PARITY (`ios/template/Sources/Kit/Media.swift`): `CameraButton` (UIImagePickerController .camera, shown only on
   a phone with a camera, photo sent through the same `local:` upload path) beside the photo picker in PhotoRow /
   PhotosRow; `ShareButton(text:url:)` + `shareText(_:url:)` (twin of Android's Act.share); one `ImageCache` (NSCache,
   150 images / 48 MB) for every kit photo download. NSCameraUsageDescription written for photo fields too.
3. DEVICE FEATURES on both phones, same public names (`kit/Device.kt`, `Sources/Kit/Device.swift`): `BiometricLock` (an
   Unlock card - Android's framework BiometricPrompt, no new library, screen-lock fallback on Android 8; iPhone
   LAContext deviceOwnerAuthentication), `RateAppButton` (Play listing link / StoreKit requestReview), `AddToCalendarButton`
   (calendar insert intent, no permission / EKEventEditViewController, iOS 16 asks first), `PickContactButton` (phone-number
   picker, one row, no READ_CONTACTS / CNContactPickerViewController, no key); screen-reader labels on the kit's unlabelled
   tap targets on both. Android USE_BIOMETRIC only when a screen uses it; iPhone Face ID + calendar purpose strings ALWAYS
   (Device.swift is in every binary and Apple's upload scan flags a protected API with no string, ITMS-90683). The Android
   CI fixture's dashboard uses all four parts so appgen-check compiles and taps them.

Tests: NEW test_v0802_honest_caps.py (9), test_v0802_ios_media.py (7), test_v0802_ios_device.py, test_v0802_android_device.py (7).
NOT VERIFIED: none of the new Kotlin / Swift had been compiled when this was written - no SDK in the sandbox; the
appgen-check (Android) and ios-check (macOS) runs on this push are the first compile. No real phone has tapped any of it;
the iPhone camera button is hidden on the simulator, so only a real iPhone proves it. Still not built: home-screen widgets,
real 3D, deep links / app links, right-to-left, in-app tests in generated apps. Older red, not this work:
test_v0338_app_store.py::test_push_and_submit_through_the_mac (KeyError 'status', red before this change).
## v0.816.0 NATIJA KHATA (built as 0.806; their 0.806-0.815 took the numbers) - the outcome ledger of HOOLA PROMPTING (P4 of docs/HOOLA_PROMPTING_PLAN.md, owner: "GO")

What it is: one row per prompt she takes OUT of Hoola Prompting, and what happened to the result afterwards. This is
the measure the whole feature is judged by, and the data the later phases (recipe order, defaults, self-improvement)
need.

- `server/app/prompting/ledger.py`, tables `prompt_runs` + `prompt_prefs` (registered in db.init_db, self-heal).
- A row holds SHAPE only: section, recipe id, slot names with their source, score, dialect, engine, model, rupees
  (AI list price), seconds, status, grade. The prompt is stored as a SHA-256 of its normalised text plus up to 160
  word hashes salted with the tenant id. No word, price, phone or name of hers is in the table (test).
- Life of a run: `hand()` (POST /api/prompting/runs from the Improve sheet's Use button and the page's Open / Copy)
  -> `claim(tenant, section, text, ref)` when an engine starts with that text: exact hash, or >= 60 % word overlap
  inside 2 hours (= she edited the prompt first, `edited_before`). The same prompt started again inside 6 hours grades
  the earlier run `redone` and opens a new run (origin `again`). -> `ready(ref, more_refs, model, usd, seconds)` ->
  `event(tenant, ref, ev)`: published / downloaded / copied / sent / thumb_up = kept (kept_after_edit when the result
  was edited), edited, deleted / thumb_down = dropped, redo = redone. Her own keep stands against a later redo; only
  her delete undoes it. `failed(ref)` closes a run without a grade (an engine failure is not her verdict).
- Hooks (all through `main._pled`, `_pled_site`, `_pled_sid`, `_pled_chat`; each swallows its own errors):
  POST /api/sites (both the architect path and the plain path), site first build ready (`site/service.py`, with the
  site's cost_usd), /change + /edit, /launch, DELETE; Create image jobs (`create/jobs.py`: run_meter cost, items as
  extra refs, failure), item delete; the Script writer (/api/create/write, item text edit, delete); a chat message of
  40+ characters (never in an incognito chat), reply thumbs, Ask again. Studio downloads call
  POST /api/prompting/runs/event (only `downloaded` / `copied` are accepted from a page).
- Silence, by rule (`settle`, run lazily when numbers are read): handed and never run in 24 hours = `unused`; copied
  out of Hoola = closed with no grade (unknown); a result still there 3 days later, not redone and not deleted =
  kept, marked quiet and counted apart from her own keeps.
- The four numbers (`numbers`): kept rate, redos per kept result, rupees per kept result, minutes to a kept result -
  overall and per section, shown only after 5 judged results. Score check per section: kept rate of runs at or above
  the median score against those below, said only with 16 judged runs: predicts / no link / backwards.
- Recipes: `recipe_rates()` (users who share, 5+ judged runs) orders the image / script recipes and shows
  "kept 5 of 6 times".
- Her controls: keep my record (off = nothing written), share shape for recipe order, Delete my record
  (DELETE /api/prompting/ledger?confirm=DELETE). GET /api/prompting/ledger = her numbers + recent runs;
  `everyone=1` only for the owner tenant (all users who share, no recent list). POST /api/prompting/runs/{id}/thumb.
- Page: Results tab on /console/prompting (`prompting.js` results(), styles at the end of `prompting.css`).
- Switch `prompting_ledger` (default on).
- Tests: `server/tests/test_v0816_prompt_ledger.py`, 14 incl. a browser walk at 1360 and 390 px.

NOT built / NOT verified: no real run has been recorded on the live server. Not hooked: Kalam, video, app builds,
the architect's plan-only path. Rupees for a website are the site's running AI cost at first build, not the build
alone. A chat run is marked ready when the message is sent (the reply's time and cost are not read). Decisions 2-5
of plan part 7 (which questions to stop asking, slot defaults per business type, dialect health alerts, her
personal defaults) need real rows first and are not built.

## v0.817.0 HOOLA CODE DESIGN PASS (built as 0.807; their v0.807-v0.816 took the numbers meanwhile) — one design system for every page of Hoola Code (owner: "DESIGN STILL LOOK OLD AND STALE --- MAKE IT PERFECTLY ALLINED WITH TEXT, BUTTONS, TEXTURE ... MORE PREMIUM AND ADVANCE SMOOTH --- LIKE CLAUDE CODE WEB PORTAL ... SHOW ME ALL PAGES")

Same pages, same routes, same behaviour - the LOOK rebuilt. Seven phases had each added their own rules (311 lines, five
button heights, corners from 5 to 18px, a class used for two different things). All of them are gone; ONE block in
`server/app/static/console/v2.css` ("HOOLA CODE (code.js) - THE DESIGN SYSTEM") replaces them.

**The scale (nothing on the page is outside it)**
- Controls 34px (small 28px, the two composer buttons 36px); a button, a chip, a field and a tab are the same height, so
  any row of them sits on one line.
- Corners 8 (control) / 12 (card) / 18 (composer, dialog); type 12 / 13 / 13.5 / 14 / 16 serif for reading / 28 serif for
  a page title; weights 400 / 500 / 600; space 4 / 8 / 12 / 16 / 24.
- One hairline inside a card (`--line`), one around it (`--hair2`), one soft shadow (`--lift`); the composer is the one
  raised thing on a page (a deeper shadow with a faint violet glow under it).
- Console tokens only, so dark mode follows by itself; primary / green / red buttons take `--on-acc` for their words
  (white words on the bright dark-mode green were unreadable).

**What changed on the page**
- Sidebar: sans brand line (it was monospace by accident: `.hcd-sh` was both "section header" and "shell command" - the
  command is `.hcd-cmd` now), icons on the nav rows, the open session as a raised row, a count badge on Scheduled.
- Home: four starting points under the box (Fix a bug / Build a feature / Write tests / Explain the code) that only fill
  the box; the settings row as quiet inline pickers with one drawn chevron (native select arrows are gone everywhere).
- Session: every step is one grid (16px mark, words, time) so marks and words line up down the page; thinking as a quiet
  italic quote; the recap as one calm card with a coloured edge instead of a tinted slab; the question / plan bar, the
  queue and the message box are the same width; a Working pill with the clock in the top bar.
- Rail: quiet cards on the sidebar colour; buttons share a row and never overflow (a long label wraps to its own row).
- Changes pane: file list on the sidebar colour with the open file raised, 22px code rows, a 36px sticky file header.
- Settings: cards flow in two balanced columns (a long repo card no longer leaves a hole), real switches instead of
  checkboxes, a drawn disclosure arrow on "How this repo runs in the box".
- All sessions: Active / Archived as one segmented control. Dialogs: 18px corners, deeper shadow.
- Narrow windows start with the slim sidebar.

**Motion (CRISP TEXT rules kept):** 140 ms hover / press / focus transitions; a page comes in once (`hcd-enter`, removed
after 320 ms so a later repaint never moves); a dialog pops once; a fold fades in. No blur, nothing spins, text always on
a solid colour. All of it is off under "reduce motion".

**Test** `server/tests/test_v0807_hoola_code_design.py`: walks 17 views in a real browser with full data (home, finished
session, steps + thinking, Changes pane with a comment, working, plan, question, dialog, Scheduled, Reviews, Settings,
All sessions, three in dark, two at 390px) and MEASURES: every control on the scale, every row on one centre line, step
marks on one vertical line, page title and cards on one left edge, nothing under 12px / over weight 600 / all-caps,
nothing wider than the window, no button outside its card, motion once and off under reduce-motion. With HOOLA_SHOTS it
saves a picture of each view. Found by it while building: headings losing their centring to a reset, hint text at 10.4px,
a rail button whose words left the button, bars narrower than the message box.
Kept on purpose (older tests pin them): rail 300px, slim sidebar 52px, reading column 760px.
**NOT VERIFIED:** seen only in headless Chromium here, not on her own screen / Windows ClearType. The phone screen and the
read-only shared page use the same styles but the phone app's Flutter screen is unchanged.
## v0.818.0 HOOLA DESIGN (built as 0.777; their CHAT JAISA took 0.777.0 and the 0.778-0.817 chain landed meanwhile - REBASE PROTOCOL, both kept) — Hoola's own design editor on Figma's published architecture (11 Nov 2026; owner: "A HOOLA DESIGN --- DO EXTREEM DEEP RESEARCH HOW FIGMA WORKS IN BACKEND ... MAKE CLONE OF FIGMA FOR HOOLA END TO END" + "DEPOY SEVERAL AGENT")
- RESEARCH (`docs/research/figma/`, every claim cited to Figma's own engineering blog / help / Evan Wallace): 01 backend + multiplayer (a file = a tree of objects, server-authoritative last-writer-wins PER PROPERTY - not OT, not a full CRDT; client id + counter node ids; fractional index child order; parent+position one property, the server refuses a cycle; one in-memory process per file, checkpoints + a write-ahead log; LiveGraph; dynamic page loading), 02 editor + rendering (C++ -> WebAssembly, own tile-based WebGL / WebGPU renderer, no DOM per layer; plugins in QuickJS), 03 feature inventory (~120 features in tiers) + open-source licences (tldraw: production licence + watermark -> not usable; Plasmic Studio AGPL -> not usable; Penpot MPL = reference only). Original product, original look: no Figma name / assets / code.
- CONTRACT: `docs/HOOLA_DESIGN_PLAN.md` - data model (node props table), ops, WebSocket frames, REST routes, client module API, phases D1-D9, section 6 = as built. Ten builders worked in parallel against it (4 first wave, 6 second wave), each owning its own files.
- SERVER `server/app/design/` (+ main.py page route `/console/design` behind `design_page`, router mount, shutdown flush; db.init_db; config `design_*`): `doc.py` the document rules (LWW per prop, null removes, create = set with type/parent/idx, delete = subtree, cycle refused, root protected, size caps), `fracidx.py`, `room.py` (one room per open file: snapshot + journal replay, cid per connection persisted and never reused, bounded per-connection send queue, ONE serialisation per broadcast, checkpoint every 200 ops / 20 s idle / last leave, journal trim, auto version every 30 min keep 50, `HUB.apply_ops` for server-made edits), `store.py` (all DB access, off the event loop), `api.py` (files CRUD + trash / restore / duplicate, doc, thumb, versions + restore + duplicate-as-file, comments, assets by content sniffing - SVG with script refused, view-only share token + public read routes + `?share=` socket, the WebSocket with the console's subprotocol auth), `assets.py` + a daily unused-image sweep (worker slot `design_asset_jobs`, 7 days), `limits.py` (comment 30/min, share reads 120/min, AI 20/hour), `ai.py` + `ailayout.py` + `icons.py` + `templates.py`.
- CLIENT `server/app/static/console/design/` (plain JS, no build step, strict CSP): `hd-math` `hd-core` (store with a SHADOW of the server's document: screen = shadow + un-acked local ops, replayed by the server's rules; per-client undo as inverse ops; `prop()` defaults never written) `hd-net` (reconnect with backoff, pending ops re-sent, offline queue 5,000, hold / release for version preview) `hd-layout` (text measure from real font metrics, auto layout flex-like with hug / fill / wrap / min-max, constraints, group bounds) `hd-render` (Canvas2D: dirty redraw, viewport culling, LOD, per-subtree bitmap cache, every paint / stroke / effect / blend / mask, booleans with real geometry, toCanvas / toSVG) `hd-tools` (select, deep select, marquee, move / resize / rotate, snapping + smart guides, frame + presets, shapes, pen, pencil, IME text) `hd-ui` (file browser, layers - virtualised, 10,000 rows = 39 DOM rows - pages, Design panel, colour picker + gradients, context menu, command palette, shortcuts) `hd-app`; second wave `hd-vector` (vector edit, booleans, masks, rulers, guides, layout grids, gradient handles, Alt distances) `hd-components` (components, instances + overrides, variants, component props, styles, variables + modes, Assets + library) `hd-export` (PNG / JPG / SVG / image PDF / ZIP, copy as PNG / SVG, SVG + picture import with hostile SVGs inert, Inspect tab with CSS / Flutter / Tailwind, .hoola.json) `hd-collab` (comments with pins that follow layers, version history with read-only preview + restore, share link that works signed out, follow / spotlight / cursor chat) `hd-proto` (interactions, on-canvas wiring, the player with transitions + smart animate, device outlines) `hd-ai` (Ask Hoola composer, Remove / Try again / 3 variations). Console sidebar row "Hoola Design" under Create.
- AGENT: ONE tool `hoola_design` (create / list / add / share; family `design`, tight admission keys, VOICE_VIA_KAAM only; `share` never makes a public link - she taps Share herself). Registry 624 -> 625. The AI never writes ops or ids: it returns a spec that code validates (depth 8, 400 nodes, allowlisted keys and fonts, max 2 families, invented phone / price / email -> [blanks], contrast >= 4.5 checked in code with one fix pass), one retry on bad JSON, then a plain 502; no model key = 11 built-in layouts, said so.
- MEASURED: pan 5 ms a frame with 5,000 layers, under 10 ms with 20,000 (headless Chromium, software raster, 1280x800); store loads 50,000 nodes in 20 ms, 1,000 sets in one step 2-6 ms; server ~20,000 op batches a second, ack p50 0.23 ms; a killed server lost nothing; smart animate 120 layers 2.3 ms a frame; three editors with crossing messages, rejects, undo and dropped connections - 3,000-run soak, zero divergence. Two real browsers on a real server: draw, move, recolour, undo / redo, cursors, Hindi text, reopen all matched.
- PROOF: server 33 + collab 12 + AI + core 4 + render 3 + vector + components 3 + export 3 + proto 3 pytest files; node walks design_core (24), design_ui, design_render (12 sections), design_vector (11), design_components, design_export (273 checks; ZIP read by zipfile, PDF by strict pypdf, hostile SVG made no request), design_proto (169), design_collab (78 checks on a REAL server: two editors + a signed-out visitor).
- NOT DONE / NOT VERIFIED: NOT Figma's raw speed - Canvas2D in plain JS, not a WASM + WebGL engine (phase D9); target is smooth up to a few thousand visible layers and 10-20 people in a file. Rooms are in memory = ONE server process per file (true on the VPS today). The AI was only ever answered by a FAKE model - real design quality unseen; only the templates were looked at. Not built: D7 bridges (import through her own Figma token, design -> Web / App Studio), D8 plugins, D9 WebGL engine + branches; boolean shapes skip text / lines; flatten keeps no outlined strokes; the PDF is page images; SVG import skips patterns / luminance masks / textPath; instances' own overrides are not in the Inspect code; unread comment dots are per browser; player hit-test by bounding box. Real Google Fonts and EyeDropper not exercised (sandbox).

## v0.819.0 WHITEBOOKS PASTE CHECK (built as 0.814; their HOOLA CINEMA took 0.814.0 and 0.815-0.818 followed - REBASE PROTOCOL, all kept; owner ran vps-ops wb_check after putting the sandbox keys in the VPS .env)

Her first live run, sandbox: every WHITEBOOKS_* name set except WHITEBOOKS_SANDBOX_GST_USERNAME (not in WhiteBooks' shared sandbox PDF,
which covers e-Invoice + e-Way Bill only); ping PASS; public_search, rettrack, einv_auth FAIL WB_ERR_9001; ewb_auth FAIL "Invalid
credentials provided or your account is not active" (the same refusal without its code); otp_request SKIP. Hoola's requests were read
again against the specs (client_id / client_secret headers, email query) and match, and a refusal on all three products with their own
keys leaves two causes: a bad paste, or an account WhiteBooks has not activated (her Developer Hub dashboard showed GST / e-Invoice /
e-Way Bill all "not subscribed").

- `wb.clean()` / `wb.email()`: every WhiteBooks value (email, client ids / secrets, sandbox identities) loses stray spaces, tabs,
  Windows line ends and wrapping quotes before it is sent.
- `wbcheck.paste_check()`: printed first by wb_check - per value how it LOOKS, never the value: client ids by leading letters + length
  (the Hub shows them, e.g. GSTS...), secrets / passwords by length only, flags for non-keyboard characters (the Hub shows a secret as dots
  until the eye / copy button is used), a space inside, not an email, not a 15-character GSTIN, and an e-invoice / e-way bill id with the
  same start as the GST one ("is the GST key pasted here?"). The vps-ops redaction sed leaves these lines alone (a length is 2 characters).
- When every value looks right and WhiteBooks still answers 9001, wb_check says so: ask WhiteBooks support to activate sandbox API access
  for GST, e-Invoice and e-Way Bill on the developer account.
- `wb._code_of`: a status_desc saying "invalid credentials" / "account is not active" without a code is WB_ERR_9001.

Tests: 2 in test_v0807_bahi_a0.py (values cleaned; the paste check never carries a value and catches dots, a moved GST key; the EWB
refusal named). NOT VERIFIED: still no accepted WhiteBooks call - the next wb_check after her re-paste or WhiteBooks' activation is the test.

## v0.820.0 PEECHHE KA APP (CI fix for v0.815 APP KE PURZE)

v0.815's first CI run: every new Kotlin / Swift file COMPILED on every job (Android compile / fcm / glogin / fixture2
incl. the field-service emulator walk; iPhone simulator + unsigned device builds). The Android `smoke` job failed its
QA report with 7 of 14 screens "not opened" (support, seller_info, privacy, delete_account, hoola_login, hoola_account,
hoola_inbox) - every screen AFTER the dashboard. Not a crash: the tap walk pressed the dashboard's new "Pick from
contacts" button, the system contacts picker (com.google.android.contacts) stayed in front, and every later screen
was opened behind it (the support screenshot is the picker's "No contacts with phone numbers"). The device check
only ever force-stopped OUR package. FIX: `clean_front` in `appmaker/android/device_check.sh` + `tablet_check.sh` -
reads the top resumed activity, force-stops it when it is not our app / the launcher / system UI, then HOME; called
before each screen, before and after each tap, before the scroll check. Any of her real apps with a button that opens
another app (calendar, contacts, Play, a browser, a share sheet) would have failed the same way. Tests:
test_v0820_device_check_front.py (3, a fake adb on PATH). NOT VERIFIED until this push's appgen-check.


## v0.821.0 HOOLA 3D CHARACTERS - the 3D kit's characters (owner: "GO COMPLEX 3D CHARACTERS BUILD")

Before this the kit's player was a capsule and an enemy a ball. A 3D game with people in it meant the model writing
bodies and walk cycles from scratch, which is exactly where 3D builds broke. Now the kit carries the characters.

**What it is** (all in `server/app/gamedesk/kit/hoola_3d.gd`, `const VERSION := 2`, Hoola's own file):
- `class Figure extends Node3D` - a jointed character built from primitives: hips, torso, head, two arms (shoulder +
  elbow + hand), two legs (hip + knee + foot), eyes, hair, hat, outfit, an item in the right hand. `kind: "animal"` =
  a four-legged body with head, ears, tail and optional horns. `style: "robot"` = box parts, glowing eyes, antenna.
- Animation is procedural, joint targets blended every frame: `set_motion(0..1, on_floor, up_speed)` picks idle / walk /
  run / jump / fall; `play()` runs a one-off - attack (signal `strike` at 40 %), hurt, wave, talk, die (stays down,
  further play() ignored). Signal `finished(anim)`.
- 11 ready-made looks in `LOOKS` (hero, girl, boy, elder, farmer, guard, villain, king, robot, dog, cow);
  `look(preset, changes)` changes skin / shirt / pants / shoes / hair / eyes / hat_color, height, build
  (slim / normal / stocky), hair_style (short / long / bun / none), hat (cap / turban / crown / helmet / antenna),
  outfit (kurta / dress), item (sword / staff / lamp).
- Her approved ANIMATED model instead of the drawn body: `"model": "<key>"` in the look, or `figure_from(parent, pos,
  node)`. The model is sized to the height asked for (bounds of its meshes), turned to face the kit's forward, and its
  clips are matched by name (idle / walk / run / jump / fall / attack / hurt / die / wave / talk; idle-walk-run set to
  loop). No model = the drawn character, so a game never breaks on a missing asset.
- `spawn_hero(parent, pos, look, speed, jump_height, hp)` - the v1 Player with a Figure for a body. With a sword (or
  `"attack": true`) the action key F / J / X or the new violet on-screen button (`act_button`, drawn only when
  `act_on`) strikes: every foe within 2.2 m and in front loses `power` health.
- `foe(parent, pos, look, patrol_to, speed, chase_range, hp)` - the v1 Enemy with a Figure and health: a blow staggers
  it (0.45 s, pushed back 0.6 m), at 0 it falls and is freed after 1.2 s. Its touch still costs 1 hp (it swings),
  landing on it still removes it. New signal `enemy_defeated(left)` for strike or stomp; `enemy_stomped` unchanged.
- `npc(parent, pos, who, lines, look, talk_range)` - turns to the player, waves when the player comes near, shows
  "..." above the head, and says the next line each time the action key is pressed beside it (the last line repeats).
  `hud.say(who, text)` shows it for 3.5 s; signal `npc_talked(who, index)`; HoolaProbe event "talk".
- `figure(parent, pos, look)` - a character that only stands there, for the game's own logic.
- v1 is untouched: `spawn_player`, `enemy` and every signal keep their names and argument order (a test holds it).

**The model is told** in `kit3d.API` (rides only in a 3D design): use the characters, never build people from your own
meshes, never write a walk cycle, at most 12 characters a level. Tests hold every preset, option and animation name in
the API text to something the kit really reads.

**Proof game**: Diya Run 3D now has the hero with a sword, a guard and a tall villain (2 and 3 health), Dadi who says
what to do, and a dog. The test player still wins it with the same keys (6.6 s, 24.4 m, 6 of 8 coins, 3 lives).

**Measured here** (Godot 4.7.2 headless, `kit3d.self_test`, 10 checks, all pass): 11 looks built, fewest joints 8; a
walking figure's leg swings 0.8 rad and the two legs are never on the same side; at rest 0.0; one strike signal, the
attack ends and the figure is idle again; die tips the body 1.5 rad and it stays down; the dog's leg swings 0.6 rad.
Hero with sword: first blow 2 -> 1 health, second fells the foe, the foe behind keeps 2, the hero keeps 3 lives. Dadi:
lines 0, 1, 2, 2 and the HUD reads "Dadi: Then come to the temple"; the person 17 m away says nothing. Kenney's CC0
`platformer_character.glb` wrapped as a figure: 1.6 m tall as asked, plays walk / jump / idle. Web export + browser:
playtest ok, touch collected 2 coins, download 10.2 MB (was 9.7). I looked at the pictures: the eleven looks are
distinct and read as people / robot / animals.

**NOT VERIFIED / not built**: no MODEL-written game with characters yet (needs her server and credit); the looks are
low-poly shapes, not sculpted characters; no faces beyond eyes; no skinned-mesh generation (Meshy waits for her key);
foes do not path round walls; no ranged attacks; talking has no choices.

Files: `gamedesk/kit/hoola_3d.gd` (709 -> 1519 lines), `kit/proof_main.gd`, `kit/selftest_main.gd`, `kit3d.py`,
`tests/test_v0821_characters.py` (12).

## v0.822.0 THE AGENCY IN HOOLA CODE + GAME DEV (built as 0.814; other sessions took 0.813-0.821 meanwhile - REBASE PROTOCOL, all kept)
Owner (11 Nov 2026): "https://github.com/msitarzewski/agency-agents.git --- NOW READ THIS REPO" -> "GO 1 2 3 AND DEPLOY ON VPS".
The Agency (MIT, AgentLand Contributors) read at 8ae6164: ~288 personality-style agent prompts in 18 divisions + the NEXUS
multi-agent playbook. Three parts, all TEXT (condensed + rewritten by three parallel agents; persona / emoji / internet-only
parts dropped; no upstream code; credit in THIRD_PARTY_NOTICES.md):
1. HOOLA CODE: 35 agents ECC did not cover join the catalogue (`server/app/devsahayak/ecc/agency_eng.py` 24 +
   `agency_qa.py` 11; 98 agents in all; new group 'build' = implementers): minimal-change-engineer,
   codebase-onboarding-engineer, senior-developer (it is a Laravel / Livewire persona - titled so), frontend-developer,
   backend-architect, api-platform-engineer, devops-automator (never edits .github/workflows), sre, database-optimizer,
   payments-billing-engineer, i18n-engineer, privacy-engineer, identity-access-engineer, mobile-app-builder,
   mobile-release-engineer, webassembly-engineer, realtime-collaboration-engineer, search-relevance-engineer,
   data-engineer, ai-engineer, prompt-engineer, rapid-prototyper (local storage, no hosted services),
   embedded-firmware-engineer, desktop-app-engineer, reality-checker, evidence-collector (evidence = output / file:line,
   not screenshots), api-tester, performance-benchmarker (smoke only in the box, said so), test-automation-engineer,
   test-results-analyzer, ai-generated-code-auditor, appsec-engineer, secrets-credential-engineer,
   codebase-archaeologist, mcp-builder. `ecc.suggest` keeps code-reviewer + security-reviewer inside the top 6.
2. THE REALITY CHECK (`engine.reality_check`): when the coder calls done (after ECC's gate) on a change of
   `dev_reality_min_lines` (30) added lines or more, ONE fresh reality-checker agent (read + run tools, no edits) reads
   HER request, the coder's claim and the real working copy, runs what it can and answers "VERDICT: READY" or
   "VERDICT: NEEDS WORK" + numbered gaps with file:line and proof. NEEDS WORK goes back to the coder once (confirm each gap,
   fix the real ones, then done); READY / unclear finishes. Once a round, never a loop; a check that cannot run never
   blocks. Page step `reality`; `found.loop.reality` keeps the verdict. Switch `dev_reality_check` (pinned off in conftest
   for the scripted suites).
3. HOOLA GAME DEV (`server/app/gamedesk/agency.py`): `EXPERT` = deeper notes for 21 crew roles (game / level / economy /
   narrative design, technical art, game audio, Godot GDScript / shaders / netcode, Unity, Unreal, Roblox, Blender) that
   ride the model call beside `lens(role)` (`crew.expert`, both studio.py calls); `NEW_ROLES` = 8 writing engine roles
   (unity_editor_tools, unity_multiplayer, roblox_experience, roblox_scripter, roblox_avatar, blender_addon, ue_world,
   ue_tech_art) - the crew is 57 roles (test_v0406 pins healed 49 -> 57). The adapting agent FIXED wrong Godot 4 facts in the
   source (hint_color -> source_color, no Node.remove_from_parent, Web exports cannot use ENet). Switch `game_agency_experts`.
4. FIXED, found while testing (the long-standing 'explained' flake of the v0787 / v0789 / v0794 suites, and live): her
   page polls `view()` (git add -A + diff) while a new round makes its working copy; the round's own `git add` + `commit`
   of the starting point lost on .git/index.lock ("Unable to create index.lock: File exists" - caught with a probe),
   `base` became '', every later diff ran against HEAD (already holding the checkpoint) and the round ended
   'explained' with no pull request. Now `engine._git_lock` = one git command at a time per working copy (add + diff and
   add + commit + rev-parse as one step), `meta.json` written atomically, and `ensure()` refuses to go on without its
   starting commit. Proved both ways: without the lock 4 of 25 round starts under polling lost the commit; with it 0.
Tests `server/tests/test_v0822_agency_agents.py` (8): the 35 in the catalogue and adapted, both sources in the roster, a
NEEDS WORK verdict sends the coder back once and judges against HER request, READY finishes, a small change is not
checked, the switch, the page step, the crew's 57 roles / experts / routing, the notes in the model call, round starts under her page's polling.
NOT VERIFIED: no real model has run the reality check or a game role with the notes (scripted Claude only); the extra
cost of one reality-check conversation per 30+ line round is not measured.

## v0.823.0 HOOLA DESIGN D7 BRIDGES (11 Nov 2026; owner: "D7 Bridges - import your existing Figma files through your own Figma token; send a design to Web Studio or App Studio"; asked "why send to Figma" -> nothing is ever sent to Figma, import is one-way -> "Keep import")
- CONTRACT: `docs/HOOLA_DESIGN_PLAN.md` section 7. Three builders in parallel; no new tool - `hoola_design` grows `import_figma` / `to_site` / `to_app` (registry 626 unchanged).
- A. FIGMA IMPORT (`design/figma.py`, `design/figma_convert.py`, `hd-bridge-figma.js`): `GET/PUT/DELETE /api/design/figma` wrap the website builder's EXISTING sealed token store (`site/inspire.py` SiteFigmaKey) - one token per account for both, typed in the page, no route returns it, the agent action refuses a token. `POST /api/design/import/figma` + `GET /api/design/import/{job}`: Figma's official REST API only (`/v1/files/:key?geometry=paths`, `/v1/files/:key/images`, `/v1/images/:key` fallback), 429 Retry-After (3 tries, 60 s max), request budget, file + picture byte caps, pictures only from Figma's S3 hosts with no redirects and no token sent, sniffed and stored as assets by hash; written through the room in chunks as a NEW file ("<name> (importing...)" until done, trashed on failure). Converts pages, frames, groups, sections, components / sets / instances (overrides + component props when the component is in the file, else detached with a warning), rectangles with per-corner radius, ellipses (arcs -> vector), lines, polygons, stars, vectors, booleans, text with runs, solid / linear / radial / angular / image fills, strokes, shadows + blurs, opacity, blend, masks, clip, auto layout + sizing, constraints, grids, exports, styles, prototype links + scroll / fixed; rotation + mirroring checked against Hoola's own node matrix in a 200-case round trip. NOT converted, each named with a count in the job's warnings: smooth corners, diamond gradients (drawn radial), image crop / filters / rotation, per-side stroke weights, arrow caps, paragraph spacing, lists, links in text, small caps, variable bindings, grid auto layout, luminance masks, slices. Jobs live in memory (a restart loses a running import).
- B. DESIGN -> WEB STUDIO (`design/toweb.py`, `hd-bridge-web.js`): `frame_to_html` = semantic responsive HTML + CSS, no inline style, no script (auto layout -> flex with phone rules, absolute frames scale and stack under 640 px, text -> h1/h2/h3/p by size order, buttons -> `<a class="btn">` with her own prototype URL or `#` + a TODO, pictures -> `<img alt>`, vectors / booleans -> inline SVG; gradient + stroke maths shared with hd-export). `POST /api/design/files/{id}/to-site` (+ `/preview`): a new site or a section on an existing page THROUGH Web Studio's own path (`site/service.py` new / _put_sec / _after_edit / _start("save"), `site/code.py:clean` -> `build.sanitize_section`), so every website guard + a checked version run; never published. Refused past Web Studio's 3 free-form sections a page. Not carried, named: blend, blur, masks, gradient strokes, tiled pictures, fonts Web Studio does not ship.
- C. DESIGN -> APP STUDIO (`design/toapp.py`, `hd-bridge-app.js`): frames read as screens (headings / inputs / buttons / lists of N / bars / links between screens, size class with warnings), matched to App Studio screen kinds by name; `POST /api/design/files/{id}/to-app` (pictures PNG base64, 3 MB each / 16 MB total / 20 frames) -> App Studio's own design run (`appmaker/service.py` get / new / _load / _save(plan) / _start("design")), pictures in `<app>/from_design/`. NEVER approves (App Studio's approve() is her tap only): screens end "ready, waiting for her OK"; an already approved app loses its approval by App Studio's own run and she is warned. Never builds or submits.
- PROOF: figma 21 tests (incl. a browser walk), toweb 13 + a browser walk at 1280 / 390 px with no sideways scroll, toapp 9 (one runs App Studio's real design step with her frame in the screen-writer prompt); with every earlier design suite: 167 pytest + 9 browser walks green on one tree.
- NOT VERIFIED: no REAL Figma API call was ever made (no token in the sandbox) - shapes assumed from Figma's documentation (relativeTransform with geometry=paths, children of groups / booleans relative to the nearest frame, error bodies, UTF-16 style override positions, transition units); her first import is the live test. App Studio does not show the uploaded pictures yet (its screen writer reads the structure); a sent web section has no Undo in Web Studio (restore the previous version in History); toapp calls App Studio's private _load / _save / _start (the same path its own change() uses).
## v0.824.0 APP ENGINE 1 (built as 0.814; other sessions took 0.814-0.823 while it was built - REBASE PROTOCOL, all kept)

Owner: "GO L8" on `docs/LOVABLE_STUDIO_PLAN.md` (L8 = the first App Engine phase: template + tokens + drift check, the
devlab-style box build, the preview, the tool set, build + static publish; proof = 5 card asks built in the box).

**Her four L8 decisions were not answered, so the plan's own recommendations were taken (all switchable):**
1. Where it runs: THIS server, in Docker, at most 2 builds at once (`app_engine_previews` 2; a third says "queued").
2. Model per job: no new model call - whoever answers the Studio turn writes the code through the tool.
3. Free allowances: none built, none promised (a build spends no model money).
4. Brand: "Hoola App Engine" (working name; Hoola identity only, nothing of Lovable's).

### What it is
A second engine in the Web Studio beside the Site Engine: a real React 18 + TypeScript + Vite 7 + Tailwind v4 app per
project, the code written through ONE tool and built in a locked Docker box.

- `server/app/appengine/` (NEW):
  - `template/` = the one template (`vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx` with
    BrowserRouter basename from `<base href>`, `src/index.css`, `src/lib/utils.ts` (cn), `src/lib/hoola.ts` (Hoola
    Cloud NOT connected - says so), `src/components/ui/` = Hoola's kit: button / card / input / textarea / label /
    badge / tabs / dialog / table on `cva` variants, `AGENTS.md`, `public/favicon.svg`).
  - `image.py` = the build image `hoola-appengine:base` (node:22-bookworm-slim + every vetted package from the
    COMMITTED lock file `image/package-lock.json`, `npm ci`; Dockerfile text in Python - the v0.532 lesson);
    `CORE` (template deps), `DEV` (vite / tailwind / typescript / types), `EXTRA` = 9 vetted extras added only by
    `add_dependency` (radix select / popover / switch / checkbox / tooltip / accordion / dropdown-menu, embla
    carousel, motion). Versions pinned exactly, each published before 28 Oct 2026. `build(prebuilt=)` = the same
    lock installed on the host and copied in (for a server whose docker build cannot reach npm - this sandbox).
  - `tokens.py` = the design system is ONE file, `src/styles/tokens.css` (Tailwind v4 `@theme`, default palette OFF
    with `--color-*: initial`): bg surface ink muted line primary primary-ink accent ok warn bad, rounded-card /
    rounded-control, shadow-card, font-head / font-body; 5 palettes (calm warm fresh bold night) or her #rrggbb
    values; muted / line / primary-ink derived (contrast measured); a Web Studio look can seed it (`from_site_look`).
  - `rules.py` = checked in CODE on every write: PATHS (src/ minus locked files, public/, index.html, AGENTS.md,
    .hoola/plan/*.md; no `..`, hidden files, other types; 200 KB / 400 files), SAFETY (no eval / new Function /
    document.write / innerHTML / dangerouslySetInnerHTML, no outside address in fetch / import / script / CSS,
    index.html keeps only its module script, no script in SVG, an import must name a package THIS app lists - a
    vetted-but-not-added one says to add it, anything else is refused with the vetted list), DRIFT (hex / rgb / hsl
    colours, Tailwind palette colours incl. white / black, one-off `[value]` classes refused; `data-[..]` variants,
    `bg-ink/40` opacity and `href="#faq"` allowed). A refusal names file:line and the token to use.
  - `runner.py` = the build: `tsc --noEmit` + `vite build --configLoader runner` in the box with `--network none`,
    `--read-only`, tmpfs /tmp, uid 1000, cap-drop ALL, no-new-privileges, 1.5 GB / 2 CPUs / 256 pids, 240 s; the
    app's files mounted READ-ONLY, only the out folder writable; nothing installed (the image's node_modules).
    Semaphore = `app_engine_previews`; `app_engine_runner=local` only for development.
  - `service.py` = create (template + package.json + tokens + title + brief in .hoola/plan), list / get, view
    (numbered lines, 400 at a time), search, write, edit_lines (the plan's 5.3: exact search -> replace, must
    appear once, `first_line` / `last_line` range, a `...` line skips a long middle, several edits located in the
    ORIGINAL file, overlaps refused, all or nothing, a refused edit changes nothing), rename, delete (App.tsx /
    index.html refused), add_dependency (vetted only, nothing downloaded), set_tokens; a change schedules a build
    ~2 s after the last write (debounced), `build` / `wait_build`; a good build = version N (source + dist kept,
    30 kept, the live one never pruned); a failed build keeps the last good version on screen and its problems
    (file + line) in `last_build`; `logs`; `check_all`; publish = her tap only (`confirm`), the exact version,
    refused (409) while TypeScript or the code check finds a problem; unpublish; preview (`/api/app-preview/
    <token>/`, `__v/<n>/` for older versions) and live (`/apps/<slug>/`) serving: `<base href>` injected, SPA
    routes fall back to index.html, missing asset = 404, strict CSP (script-src 'self', connect-src 'self'),
    noindex + no-store on the preview, immutable cache for live assets.
  - `models.py` = table `ae_projects` (registered in db.init_db AND self-healing; `app_projects` was App Sahayak's).
  - `proof_apps.py` + `proof.py` + `__main__.py` = the L8 card (`python -m app.appengine status | setup | proof`).
- `server/app/agent/appengine_tools.py` (NEW): ONE tool `app_engine` (registry 626 -> 627, family `appengine`):
  actions list / status / files / view / search / logs / check (reads) and create / write / edit_lines / rename /
  delete / add_dependency / tokens / build (changes). Publish refused ("her tap in the Studio"); changes refused in
  Plan / Chat mode by the tool itself (`turnmode._SPLIT` lets the tool through so its reads stay open); changes only
  from the owner's own turns.
- `agent/turnmode.py`: `(app id X)` in the Studio hint -> `APP` contextvar; `agent/prompts.py` adds
  `<app_engine_project>` (app, state incl. a failed last build, packages, file list, AGENTS.md, the rules);
  `agent/admit.py`: a turn with an app always has the tool (`sticky_families`) + words (react app, web app...).
- Routes (`main.py`, `_ae`): GET / POST `/api/appengine`, GET (`?full=0` light) / PATCH / DELETE `/api/appengine/{id}`,
  GET `/file`, POST `/build`, GET `/logs`, POST `/tokens`, POST `/publish` (version + confirm), POST `/unpublish`;
  public GET `/api/app-preview/{token}/...` and `/apps/{slug}/...`.
- Studio (`static/console/appengine.js` + `appengine.css`, hooks in webstudio.js: the `Apps` sidebar row, routes
  `#/apps` and `#/app/<id>/<tab>`, `window.HoolaWSKit`): Apps page (Beta; New app = name + what it should do +
  colour palette swatches; the box's state said plainly when it cannot build) and the workspace: the app's own Hoola
  chat on the left (its own conversation; the first message = "Build this app: <her words>"; Hoola is working + a
  clock), Preview (computer / phone, failed-build or TypeScript problems with file:line, open in a new tab), Code
  (file list + read-only source), Design (palettes + every token with contrast), Versions (open any), Publish (her
  tap + a confirm dialog, the reasons when it is refused, Take down). Polls the light row every 2 s while building.
- Config: `app_engine` (on), `app_engine_previews` (2), `app_engine_runner` ("box").
- vps-ops: `appengine_setup` (build the image) and `appengine_check` (status + the proof).

### Measured here (sandbox, Docker 29.9, real box)
- The bare template builds in 4.6 s; the five card asks in 5.8-8.0 s each (median 6.2 s), JS ~475 KB.
- **Proof card: 5/5 apps PASS** (shop staff tasks, clinic appointment request with zod validation + a second route,
  sales dashboard with recharts + tabs, mithai catalogue with a cart dialog, coaching timetable with date-fns) -
  built, TypeScript clean, rules clean, opened in Chromium with 0 page errors, her words on screen, one click works,
  no sideways scroll on a 390 px phone, published by the tap path, `/apps/<slug>/` serves it; **8/8 planted bad
  writes refused** (one-off colour, palette colour, raw colour, outside fetch, unvetted package, raw HTML, a locked
  file, a path outside the app).
- Tests `test_v0814_app_engine.py` (9): rules, tokens, the tool's exact edits, Plan mode + her tap + who may change,
  the turn block + family + registry, routes + her key, the box (TypeScript problem builds but cannot go live, a
  failed build keeps the old version, fix -> publish -> live -> take down), the five asks, and a browser walk of the
  Studio pages (create -> the chat builds it -> preview works -> code -> design -> rebuild -> publish -> live -> phone).

- Found by its own browser walk (failed 1 run in 3, only after other tests): a tab redraw that waited on the server
  (Design) could land after she had moved to Publish and paint over it; every redraw now carries a ticket and a stale
  one is dropped. Re-run green 3 times after the fix.
- Wider sweep: 982 passed; the 13 reds (crawl jobs x10, officehours / magic21 / crew story pins) fail identically on
  untouched main 0.819.0 - not this release.

### NOT built / NOT verified, said plainly
- NOT VERIFIED on her VPS: the image is not built there yet (run vps-ops `appengine_setup`, then `appengine_check`);
  her VPS's real build time and RAM per build are not measured (the plan's "estimate until L8 measures it" is
  measured HERE only).
- NOT VERIFIED with a real model: no model has written an app; the proof's files are fixed (it proves the engine).
- Not built (later phases): Hoola Cloud data / sign-in (L10 - apps keep sample data on the page and say so), hot
  reload (each change is a fresh ~6 s build, not Vite's dev server), the preview error collector + click-to-source +
  style panel (L9), tests / browser check before done + scans (L11), prerendered HTML for SEO, a custom domain for
  an app, GitHub sync (L14), drafts (L13), growing the vetted list by her tap.

## v0.825.0 TEEN AWAAZEIN (built as 0.816; their 0.816-0.824 took the numbers - REBASE PROTOCOL, all kept) — three more call voices she can pick (owner: "LETS DEPLOY ALL --- USER WILL CHOOSE THE VOICE THEY WANT")

After the deep research (`reports/Human voice in every language.md`) and the price check (Phonic 1 $0.07/min, Grok Voice
3.0 $0.08/min, GPT-Live-1 $0.05/min voice layer + the brain), the three top-ranked live voices are now choices on the
phone's Profile > Call voice screen beside Gemini. **Gemini stays the default and is not touched**: main.py reaches the
new engines only through `voiceengine.pick()`, exactly like the v0.264 OpenAI engine.

- `server/app/voice_more.py` (NEW): `GrokCall`, `GptLiveCall`, `PhonicCall`, each a `voice_openai.OpenAICall`, so
  everything that is not the wire is inherited (phone protocol = same APK, memory + context, the Haiku brain behind
  santosh_kaam, hold on her words, OTP / approvals by voice, job news, stall watchdog, turn saver, captions in time,
  scorecard, resume). Wires written from each vendor's docs, read 11 Nov 2026:
  - Grok: `wss://api.x.ai/v1/realtime?model=grok-voice-3.0`, OpenAI Realtime event names, xAI session body (voice
    rex / eve, server_vad, audio/pcm 24 kHz, reasoning none, function tools). No usage numbers on the stream: cost =
    minutes x $0.08.
  - GPT-Live-1: `wss://api.openai.com/v1/live/sessions`, session.start (model gpt-live-1, voice stone / nira, pcm 24 kHz,
    delegation client). GPT-Live opens a delegation when work is needed; Hoola's brain answers it through the same
    santosh_kaam path; the answer goes back as session.commentary.append for that delegation id. News = commentary
    for the session, quiet notes = session.thinking.append. Live has no turn-done or "she started talking" event, so
    his turn ends when his audio stopped 1 s and her phone played it, and her words while he is audible = she cut in
    (UNVERIFIED heuristics). Cost = the session's own usage.seconds x $0.05 (+ the brain, counted as usual).
  - Phonic 1: `wss://api.phonic.ai/v1/sts/ws`, config (phonic-1, voice sandeep / divya, pcm_16000 in so no resampling,
    pcm_24000 out, language from the call + English, multilingual auto, santosh_kaam as a strict custom_websocket tool,
    no_input_end_conversation_sec 3600 so it never hangs up on a quiet call), audio_chunk <= 40 ms, tool_call ->
    tool_call_output, user_started_speaking = barge-in, assistant_finished_speaking = turn end. Cost = minutes x $0.07.
- `voice_openai.OpenAICall.run()` now calls `_open()` / `_configure()` / `_session_min()` and sends `engine: self.engine`
  in `ready` — behaviour for the OpenAI engine byte-for-byte the same (its tests unchanged and green).
- `voiceengine.py`: ENGINES += grok / gptlive / phonic (`MORE`), per-engine key, on/off, who may pick it (default
  everyone), monthly budget (default $25 each, whole app) and per-user minutes (default 60); spend in its own box in
  `usage-YYYY-MM.json` under `engines`; `view()` grows `engines` (name, ready, why, ₹ per minute, month ₹, minutes).
- Settings: `XAI_API_KEY`, `PHONIC_API_KEY` (GPT-Live uses the existing `OPENAI_API_KEY`) + `VOICE_{GROK,GPTLIVE,PHONIC}_*`.
- Phone: `lib/ui/voice_engine_screen.dart` lists the three with a line, ₹ a minute, the reason when it cannot run,
  and this month's numbers for the one she picked.
- Tests: `test_v0816_teen_awaazein.py` (7) - pick + fallbacks + minutes, and one end-to-end call per engine against a
  scripted fake of its wire.

NOT VERIFIED: no live call has run on any of the three (no keys on the server when this was built). Parking does not
apply to them (CAN_PARK stays Gemini-only), so a quiet call keeps billing per minute until she hangs up. Hindi /
Hinglish quality on each engine is unmeasured - her ear test is the judge.

## v0.826.0 APP ENGINE 2 (L9 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L9")

Point at a Web Studio React app (the v0.824 App Engine) and change it - like Lovable's click-to-source + visual edits,
built on Hoola's own pieces.

- **Click -> source** (`appengine/template/hoola.plugin.mjs`, locked; Vite `enforce: pre`, `@babel/parser` +
  `magic-string` already in the image): in a PREVIEW build only (`HOOLA_SOURCE=1`) every JSX element in
  `src/**/*.tsx` gets `data-hs="<file>:<line>:<col>"` and `data-hc="<Component>"`. Component uses are tagged too: the
  kit spreads its props AFTER its own tag, so `<CardTitle>` on a page points at the PAGE's line - the line a free edit
  should change. Preview builds also keep hidden source maps (`sourcemap: "hidden"`; `.map` is never served).
- **Live = clean**: publish now runs a second, clean build of that version's source (`runner.build(source=False)`) and
  refuses (500) if a tag or a map reached the output. Visitors never get the tags, the maps or the helper.
- **Preview helper** (`appengine/preview.js`, served only at `/api/app-preview/<token>/__hoola/preview.js`, injected
  into the preview's index.html, never into a live one): (1) error collector - page errors, unhandled rejections,
  console.error -> postMessage to the Studio; (2) Select - hover outline + `<tag> Component · file:line` label, a click
  sends the tag instead of running the app's own click, Esc stops; (3) live style / words drawn at once on every element
  from that line (nothing saved) until the real change is built.
- **Free edits** (`appengine/pick.py`, Rs 0, no model): one family at a time on the app's own tokens / scale - text
  colour, background, size, weight, padding, corners, alignment - swapped inside the element's own
  `className="..."` at that exact line (none = one is added); plain words replaced when the source text is plain (no
  `{...}`, no `< > { }`); a computed `className={...}` is refused and named ("ask Hoola in the chat"); every edit goes
  through rules.py like any write; Undo keeps the last 30 files. Routes: GET `/api/appengine/{id}/pick?hs=`, POST
  `/edit` `{hs, style, text}`, POST `/undo`.
- **Error collector**: POST `/api/appengine/{id}/preview-errors` (64 KB, masked with `pii.mask_sensitive`) - each
  stack's first frame of the app's own code is mapped through that version's hidden source map (`map_position`, a
  small VLQ reader) to `src/...:line`; one card per fingerprint (count, version); a version that loaded without it
  marks it "gone" (not seen since vN); dismiss; `app_engine action=logs` and the turn's `<app_engine_project>` block
  list open errors. Studio: "This app hit a problem" bar with file:line, Try to fix (sends it to Hoola with the line),
  Dismiss.
- **Theme file**: `.hoola/theme.json` (colours, radius, fonts, contrast + the class families) written on create /
  tokens / build; tokens.css is now `@theme static` so every token exists as a CSS variable for the live preview.
- **Template refresh**: before every build Hoola's locked tooling (vite.config, tsconfig, the plugin, main.tsx,
  index.css, utils, hoola.ts) is copied fresh into the app and tokens.css / theme.json written again from its look - an
  app made by an older version builds with today's tooling.
- **HMR gate** (the plan's "half-write never shown"): the tool marks its writes with the turn's chat (`TURN_CONV`);
  such a change is NOT built while that turn runs (`santosh.turn_running`), polled every 1.5 s, at most 30 min; the
  model's own `action=build` means "this change set is complete"; the app row says `held` and the Studio shows "Hoola is
  changing the app - the preview updates when the change is complete". Her own Studio edits build after the 2 s pause.
- Studio (`appengine.js` / `.css`): Select button + S key, the style panel (swatches in the app's own colours,
  Default, Words, Apply · free, Cancel, Undo last change, Open in code = the Code tab scrolled to that line and lit,
  Ask Hoola about this = a pill on the composer sent as a `selected part: <tag> in <file> line N` hint), the error bar.

### Measured here (real box + real Chromium)
- Proof card again 5/5 (preview pages carry source tags and the helper, live pages carry neither) + 8/8 traps.
- Tests `test_v0825_app_engine2.py` (6): free edits + Undo + refusals, theme file + refresh, routes (401 / 400 / 413 /
  masked), preview tagged / live clean / a real built position mapped back to the page's line, **a half-written change
  never shown** (a page importing a file not written yet: no build while the turn runs, ONE build with both files when
  it ends, no half version in History), and a browser walk (S -> click the heading -> file:line -> accent drawn at once
  -> Apply -> version 2 -> Open in code lights the line -> a planted error is collected, mapped to its line, Try to fix
  sends it to Hoola). `test_v0814_app_engine.py` 9/9 still green.

### NOT built / NOT verified
- NOT VERIFIED on her VPS (run vps-ops `appengine_setup` then `appengine_check` after the deploy) or with a real model.
- Still a fresh ~6 s build per change, not hot reload; the style panel edits one element's line (a list rendered by
  `.map` changes every item it draws - said by the "same line" behaviour, not yet counted on the panel); no colour
  picker outside the tokens (on purpose); errors are collected only while the Studio has the preview open.
## v0.827.0 WHITEBOOKS ERROR WORDS + GST TEST GSTIN + API SETU (built as 0.825 / 0.826; their TEEN AWAAZEIN took 0.825.0 and APP ENGINE 2 0.826.0 - REBASE PROTOCOL, all kept)

Live wb_check (11 Nov, 09:44 UTC) after her email fix: keys accepted, e-invoice + e-way bill sandbox logins PASS; GST public search
"Public API Search Taxpayer Fail", filing track a bare refusal, OTP login SKIP (no GST username). She then shared ten WhiteBooks files
(GST API doc, GST / e-invoice / e-way bill Postman collections, return-filing guide, released-API list, GSTN + e-invoice error lists,
e-invoice + e-way bill preparation sheets). Read end to end (not committed - their documents; summary in
`docs/research/accounts/05_whitebooks_files.md`):
- Hoola's calls match the specs (public search / rettrack query + headers, e-invoice and e-way bill authenticate).
- The GST doc's sign-up step 3: after creating credentials, "call customer support ask to enable the sandbox Account" - the GST sandbox
  is a separate switch-on, and the shared sandbox PDF has no GST (returns) test GSTIN / username. That is the GST failure.
- NEW `server/app/bahi/wb_errors.json`: 123 GSTN codes + 128 NIC IRP codes (message + fix), basis provider-spec, source + checked_on +
  review_by; `wb.known_error(code)` -> "GST system: Invalid GSTIN." / "e-invoice system: <message>. <fix>"; `_message_of` uses it after
  Hoola's own PLAIN lines. `wb_check` FAIL lines add WhiteBooks' own reply when ours is generic.
Test: test_v0807_bahi_a0.py +1. NOT VERIFIED: the GST sandbox is still off until WhiteBooks enables it.

GST TEST GSTIN (same release): WhiteBooks support replied - the GST sandbox public taxpayer search is tested with GSTIN
27AAGCB1286QKZL and username MH_NT4.2823, a different GSTIN from the e-invoice / e-way bill one (27AAGCB1286Q005, their shared PDF).
NEW setting `whitebooks_sandbox_gst_gstin` (WHITEBOOKS_SANDBOX_GST_GSTIN; empty = the shared one): wb_check's GSTIN search, filing
track, OTP login (state code from it) and ledger use it; e-invoice + e-way bill keep the shared GSTIN; the paste check and vps-ops
wb_check list the new line. Test: test_v0807_bahi_a0.py +1 (each product's request carries its own GSTIN, username header, 0 fails).
Also started (not built yet): API Setu's GSTN Tax Payer API spec read (cf-media.api-setu.in/specfiles/gstn.yaml: GET
https://apisetu.gov.in/gstn/v1/taxpayers/{gstin}, headers X-APISETU-CLIENTID + X-APISETU-APIKEY; v1 and v2 both answer 401 without keys).

### v0.827.0 part 3 - API Setu GSTN Tax Payer lookup (owner: "i have api setu --- api lets check with it")

The government's own free GSTIN lookup, from API Setu's published spec (https://cf-media.api-setu.in/specfiles/gstn.yaml, GSTN Tax
Payer API 1.0.0; notes in `docs/research/accounts/06_apisetu_gstn.md`). `server/app/bahi/apisetu.py`: `taxpayer(gstin)` = one
`GET https://apisetu.gov.in/gstn/v1/taxpayers/{gstin}` with headers `X-APISETU-CLIENTID` + `X-APISETU-APIKEY` (her API Setu partner
app's values, `APISETU_CLIENT_ID` / `APISETU_API_KEY` in the VPS .env only, cleaned like the WhiteBooks values; base overridable by
`APISETU_GSTN_BASE`). A GSTIN failing the check digit is refused before any call; no keys = refused naming the .env lines. The 200 is
read into plain fields (legal name, status + active, registration / cancellation dates as ISO, taxpayer type, jurisdictions,
activities, source "API Setu (GSTN)"). Every failure is ONE plain line: invalid_authentication (keys refused), invalid_authorization
(keys accepted, the app is not subscribed to the GSTN Tax Payer API in the partner portal), record_not_found, a missing path, 5xx
down / busy, unreachable; API Setu's own words appended when they add something. Read-only: a lookup writes nothing.

`python -m app.bahi.apisetucheck [GSTIN]` + vps-ops `apisetu_check`: which APISETU_* names are set (never values), how the two keys
LOOK (length, hidden dots, spaces), ONE lookup of `APISETU_TEST_GSTIN` (else WhiteBooks' GST test GSTIN, else 33AAACC1206D1ZN), PASS /
FAIL with the reason (a 404 for that taxpayer still proves the keys), the public record printed, the reply SHAPE saved to
data/bahi/apisetu_shape.json. Tests `test_v0827_apisetu.py` (9).

Same release, live: her wb_check at 10:18 UTC on main b60b6694 (before this release) - GST OTP request + auth token + refresh PASS
(the GST sandbox is on and MH_NT4.2823 logs in), e-invoice + e-way bill PASS; GSTIN search / filing track / ledger still used the
shared 27AAGCB1286Q005 because the separate GST GSTIN line was not deployed yet (ledger = "Authentication Failed" for a GSTIN the
token is not for) - exactly what part 2 fixes.

NOT VERIFIED: API Setu has not answered a live call from her server; nothing uses the lookup yet beyond the check (next: supplier
GSTIN status in the BAHI register, and a free official answer ahead of the paid gstin_verify).

## v0.828.0 HOOLA CODE MEMORY (built as 0.826; other sessions took 0.826-0.827 meanwhile - REBASE PROTOCOL, all kept)
Owner (11 Nov 2026): "https://github.com/thedotmack/claude-mem.git --- check this repo and devlope same for hoola code".
claude-mem (Apache-2.0) read at 6b779c0: hooks hand every tool call to a local worker, an observer agent turns them into
typed observations + a session summary (SQLite + FTS5, Chroma), the next session starts with a compact layered index
fitted to a measured budget (ContextBudget: drop the costliest-loss-last items whole), and the agent reads more with three
MCP steps (search -> timeline -> get_observations). Ideas only - no upstream code (TypeScript; Hoola is Python).
FOUND FIRST: Hoola's CHAT already has claude-mem since v0.485 (HOOLA CODER, `server/app/coder/`: capture -> spool ->
observer -> vault -> three-layer search -> primer), but it is tenant / chat scoped and the Hoola Code engine never used it.
So this release is the coding engine's OWN memory, PER REPO (two repos' "fixed the login bug" must not merge):
- `server/app/devsahayak/memory.py`: SQLite + FTS5 (LIKE fallback) at data/devsahayak/memory.db, rows scoped (tenant,
  repo); the same title in the same repo = the same memory re-confirmed (hits + 1, newest wording).
- CAPTURE (`capture`, from `engine.run` right after a round): the engine already has the whole round, so there is no live
  per-tool observer - ONE call on `dev_memory_model` (Haiku, no thinking, effort low) reads her request, the steps, what
  the coder said, its explain / test plan / risk, the files changed and the reality verdict, and answers JSON: up to 6
  observations (claude-mem's types minus 'sensitive', which is never stored; its 7 concepts) + a summary (request /
  investigated / learned / completed / next steps). `dev_memory_mode=chill` = only what is painful to rediscover (3 max).
- PRIVACY: `coder.redact` (strip_private + redact_secrets) on the record BEFORE the model and on every field AFTER it; an
  all-<private> ask = no call, nothing kept.
- THE NEXT SESSION (`primer`, in `_first_message` of a NEW session only): `<repo_memory>` = the last session's summary,
  earlier sessions in one line each, an index `#id [type] title - files xN`, and 3 decisions / alerts / fixes in full;
  fitted to `dev_memory_primer_chars` (6000) by measuring and dropping full narratives, then the last-session block, then
  older summaries, then the oldest index lines - whole items only, header + footer always kept.
- THE TOOL (`memory`): search (index with ids) -> timeline (around one) -> get (full details, chosen ids) + save (a note
  on purpose, typed). Page steps `memory` (remembered / searched / read / saved).
- HER PAGE: Settings > a repo > "What Hoola remembers" - sessions + notes, Delete each, "Forget everything about this
  repo"; routes GET /api/devsahayak/memory?repo=&q=, GET /memory/{id}, DELETE /memory/{id}?kind=obs|summary,
  DELETE /memory?repo=.
- Switches: `dev_memory` (pinned off in conftest so scripted rounds keep their turns), `dev_memory_model`,
  `dev_memory_mode`, `dev_memory_primer_chars`.
Tests `server/tests/test_v0828_code_memory.py` (7): store / dedupe / search / timeline / get / walls between repos and
tenants / forget; private text and keys never kept; the primer fitted to its budget; the tool's three steps + save; the
observer call (Haiku, no tools, key not sent) stores observations + summary, an all-private ask makes no call, bad JSON
keeps nothing; END TO END session 2 starts with session 1's memory in its first message and finds it with the tool.
NOT VERIFIED: no real model has been the observer (scripted only); its cost (one Haiku call per round) not measured;
NOT built from claude-mem: Chroma vector search (FTS5 only), the live web viewer / My Work, TeamBrain, cloud sync,
`/learn-codebase` front-loading, and a bridge into the chat's v0.485 vault.


## v0.829.0 PRAYOGSHALA WAVE 9

85 M.Sc physics set-ups built and walked within tolerance (the agents' walks, 300+ labs and variants, and the lead's final walk,
85 / 85): pg_elec_w9 (21: regulators, converters, passive filters incl. band pass, resonance, op-amp linear / integrator /
comparators / parameters, generators, tuned / power / CE amplifiers, counters, AM / FM, analogue computing, crystal oscillator,
multivibrators; reused sn-ce-amplifier, u8-sample-hold, u8-pll), pg_optics_w9 (25: hyperfine and Zeeman by etalon, ellipsometry,
birefringence, photoelasticity, Kerr, Pockels, EO and magneto-optic links, Faraday, 2-D / slit diffraction, constant deviation,
Rowland, AlO bands, absorption bands, uranyl, solar (SIMULATED), film thickness and strain, photometry, acousto-optic, aerosol
(SIMULATED); reused fibre-bending-loss), pg_matter_w9 (26: GM dead time and efficiency, Feather, K-40 vs UX2, spark counter,
proportional counter, Kurie plots, angular correlation, Hall vs T, two-probe, diode ideality, photoconductivity, AC susceptibility,
Stefan by cooling, Cu X-rays with Ni filter, LC lattice, pulse echo, CRO sound, Lecher wire, Fourier, transducers, microwave Bragg,
horn pattern, normal modes, gas photocell; reused w8-em-focusing), pg_comp_w9 (13: NIST XCOM mixture rule from fetched tables,
quantum-dot Brus / Tauc, BET, DSC, TGA, Williamson-Hall, Scherrer + fcc indexing, TEM / SEM grain size, gas sensor, XRR film
thickness - SIMULATED characterisation data, stated). passive-filters un-revoked. Coverage 525 -> 610 of 807.
Not built and constants from memory: docs/PRAYOG_PHYSICS_LAKH_PLAN.md, "Wave 9".
## v0.830.0 API SETU RELAY + GST LOGIN HINT (built as 0.828; their HOOLA CODE MEMORY took 0.828.0 and PRAYOGSHALA WAVE 9 0.829.0 - REBASE PROTOCOL, all kept)

Owner: "CHECK" after deploying v0.827 and running wb_check + apisetu_check (11 Nov 2026, 10:31 UTC).

What her runs showed:
- WhiteBooks (wb_check): ping, GSTIN search (now with the GST test GSTIN 27AAGCB1286QKZL), e-invoice and e-way bill logins PASS.
  rettrack still a bare refusal (no reason in the reply). OTP request FAILED with "user name does not exists" - it had passed at
  10:18 with the earlier username, so the name WhiteBooks gave (for the PUBLIC search, which needs no login at all) is not a GST
  sandbox login. wb_check now prints that plainly and asks for the GST sandbox LOGIN (gst_username + the GSTIN it belongs to) in
  WHITEBOOKS_SANDBOX_GST_USERNAME / WHITEBOOKS_SANDBOX_GST_GSTIN.
- API Setu (apisetu_check): both keys set (10 / 64 characters), lookup = ReadTimeout from the VPS. From this sandbox the same URL
  answers 401 "Authentication failed" in ~1.8 s (v1 and v2), so the API is up and NIC drops the VPS - the data.gov.in story (v0.756).

The fix: her existing Cloudflare relay worker `deploy/datagov-relay/worker.js` also forwards ONLY `GET /gstn/v1|v2/taxpayers/<15
characters>` to apisetu.gov.in with ONLY X-APISETU-CLIENTID / X-APISETU-APIKEY (nothing else passed on, nothing kept); data.gov.in
paths unchanged. `apisetu.base()` = APISETU_GSTN_BASE if set, else DATA_GOV_IN_BASE + `/gstn/v1` when that relay is set, else
apisetu.gov.in (config default for APISETU_GSTN_BASE is now empty). A timeout on the direct road names the relay fix; a 404 from a
relay that has the old code says to paste the new worker. vps-ops apisetu_check also lists APISETU_GSTN_BASE / DATA_GOV_IN_BASE
names. Tests in test_v0827_apisetu.py (+3) and the BAHI suite green.

NOT VERIFIED: API Setu through the relay has not answered live; the GST sandbox login is still waiting on WhiteBooks.

## v0.831.0 HOOLA CLOUD (L10 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L10")

Saved data, sign-in and server-checked rules for the Web Studio's React apps (App Engine), built on what exists.

- **The core = the website-app backend** (`site/webapp.py`, unchanged): members with PBKDF2 passwords, roles member /
  staff / admin in its own member table (never a field a user can edit), signed tokens, rows, and the fixed rule
  vocabulary (create public | member | admin, read public | members | own | admin, update / delete own | admin) checked
  on EVERY call. `admin_only` fields cannot be set by members; `private` fields are hidden from them.
- **`appengine/cloud.py`** (NEW):
  - the SCHEMA is server data (`<app>/cloud/schema.json` + `migrations.json`), not app code - restoring old code never
    touches data;
  - MIGRATIONS: additive ops only - add_list (seeds 3 marked sample rows in preview), add_field, add_option,
    hide_field / show_field, hide_list / show_list, label, rules, signup - applied as ONE numbered run (any bad change =
    nothing changes); drop_list / drop_field / rename_field / rename_list / change_type / remove_option are REFUSED with
    the add-copy-hide way, queued as her data-loss card, and run only by her tap with confirm + accept_data_loss
    (both datasets purged / rewritten);
  - the RULE AUDIT: each list's rules in plain words (read / add / change / delete) + flags (high: anyone on the
    internet reads personal fields; medium: every member reads everyone's personal fields; info: public on purpose,
    public add); a change that makes personal fields (email, phone, name, address, city...) public is refused at plan
    time unless it says confirm_public;
  - `src/lib/cloud.types.ts` (locked) generated from the lists, so `hoola.db.collection("orders")` is typed and tsc
    checks the app's code against the data;
  - TWO DATASETS: core keys `ae:<app>:p` (preview, samples marked) and `ae:<app>:l` (live) - publish never copies a
    preview row or a preview account; the live door exists only while the app is live;
  - the public API `POST /api/cloud/<key>/<op>` (schema, signup, signin, me, signout, list, create, update, remove; CORS;
    32 KB; English errors for her visitors), key `p-<preview token>` / `l-<slug>`.
- **Every app now runs in a SEALED frame** under a Hoola **shell** page (`appengine/shell.js`, served at the app's
  address; the app itself is under `__app/`): the shell keeps the visitor's sign-in (localStorage per app; in the
  Studio only in memory) and makes the Cloud calls; the app asks through `src/lib/hoola.ts` (locked: postMessage RPC,
  `hoola.auth` signUp / signIn / signOut / me / onChange, `hoola.db.collection(list).list / create / update / remove`).
  Why: all live apps share Hoola's address (`/apps/<slug>/`), so an app holding tokens could read another app's; in a
  sealed frame the app has no storage, no cookies and no token at all. `main.tsx` keeps the address bar in step
  (`NavSync`). A rule now refuses `localStorage` / `sessionStorage` / `indexedDB` / `document.cookie` in app code (they do
  not exist in the frame). The preview app page carries no frame-ancestors (a blank-origin shell cannot match one); a
  live app keeps `frame-ancestors 'self'`.
- Tool `app_engine`: `cloud` (lists + audit + counts), `cloud_change` (one run; a destructive ask = her card),
  `cloud_rows` (PREVIEW data only - her visitors' live data is never read by the model); Plan / Chat refuse
  `cloud_change`; the turn's `<app_engine_project>` block lists the lists, rules and flags.
- Studio routes (her login): GET `/api/appengine/{id}/cloud`, POST `/cloud/changes` (additive, or the data-loss card),
  POST `/cloud/pending/clear`, GET `/cloud/{ds}/rows/{list}`, GET `/cloud/{ds}/members`, POST
  `/cloud/{ds}/members/{mid}/role`, POST `/cloud/preview/samples|clear`. Deleting an app deletes its Cloud data.
- Studio **Cloud** tab: Preview data / Live data, every list with its fields, rules in words and flags, its rows (Sample
  badge), members with a role select (her tap), fresh samples / clear preview data, the data-loss card (tick "I accept
  data loss", then Apply), the history of changes, and what is not connected yet.

### Measured here (real box + real Chromium)
- Proof card 5/5 + 8/8: every app runs sealed (`localStorage` throws inside it), the shell page carries no app code;
  the clinic app saves patients' requests through Hoola Cloud; the server held the rules (a visitor adds but cannot
  read; a signed-up member cannot read others' or change status); after publish the live data held ONLY the live
  visitor's request - no sample rows, no preview row, no preview account.
- Tests `test_v0827_hoola_cloud.py` (6): migrations (5 destructive ops refused + nothing changes, one-run all-or-nothing,
  the tool queues her card, her tap purges values in both datasets), hide keeps values, the rule audit + every rule on
  the server (incl. a member trying to grant themselves a role - ignored), preview vs live, shell / sealed app / routes /
  tool / Plan mode, and the Cloud tab in a browser. The v0.824 / v0.826 suites updated for the shell (the app is under
  `__app/` now) and green: 28 passed with teen mode.

### NOT built / NOT verified
- NOT VERIFIED on her VPS or with a real model writing a Cloud app.
- Not connected yet (said on the Cloud tab and in hoola.ts): files, server functions (DIMAAG), live updates, payments,
  AI from the app, phone OTP / Google sign-in, a password-reset email.
- Sign-in on a live app is per browser (the shell's storage); an app on its own domain is not built.

## v0.832.0 API SETU REPLY SHAPE
Her live `apisetu_check` (relay, corrected Client ID `com.ainewtika`) returned HTTP 200 with no top-level `gstin`. `bahi/apisetu.py`: `record_in` finds the record bare, wrapped (data / result / response / list) or with GSTN short names; `shape_keys` lists field names only; a 200 with no record raises `no_record` listing those names. `apisetucheck`: `no_record` = keys accepted, hint to set `APISETU_TEST_GSTIN` to a real registered GSTIN. 2 tests. NOT VERIFIED: the real reply shape.

## v0.833.0 BAHI A1
Connect her GSTIN through WhiteBooks (OTP walk, refresh, disconnect) and supplier checks with no OTP (API Setu, WhiteBooks search, filing track). OTP never stored or returned. Console Connection tab. 6 tests. NOT VERIFIED on production.

## v0.835.0 BAHI A2 (built as 0.834)
Monthly credit loop: GSTR-2B pull via the A1 session, match with the purchase register, proposals with reasons, supplier nudge drafts, her decisions to IMS only on confirm + plan hash, 2B recompute. Console Credit (ITC) tab. 5 tests. NOT VERIFIED on a live portal.
## v0.834.0 SABOOT — L11 of the Lovable Studio plan: nothing is called done that a check did not prove (owner: "L11 SABOOT"; built on main at v0.833.0)

The plan's proof for L11: **a planted bad-rule app is refused at publish.** It is, and so is a planted secret and a planted engine bug.

New module `server/app/appengine/saboot.py` (no model call, Rs 0, all on this server):

1. **Rule tests** (`rule_tests`). When an app's Hoola Cloud rules change or a list is added, the rules are PLAYED against the real rule engine (the website-app core every visitor's call goes through) on a scratch dataset `ae:<app>:t`: a visitor, two members and an admin try to add / read / change / remove in every list and each answer must be what the rule says (an "own" list hides one member's entry from another; an "admin" list refuses a member; ...). It is a test of the engine's enforcement, not a copy of the rule - a planted engine bug (`_can_write` always true) fails it and names the check. Leaves nothing behind. Never run for a copy / label change. The tool runs it after `cloud_change` (add_list / rules) and puts the answer in the reply ("Do NOT say this is done" on a fail).
2. **Browser check** (`browser_check`). Real Chromium opens the built app at PHONE (390) and DESKTOP (1280): it must show something, fit the width, raise no page / console error (a 401 / 403 answer is a rule saying no, not an error), and the journey the app itself makes through the sealed frame - reach Cloud, sign up, stay signed in, add, see it in the list, change, remove, sign out - must work, each step judged against the list's own rules. Served in-process (Playwright routes the preview + Cloud calls to the service functions, no port), so it runs the same on her VPS. Its own people (`hoola-check-*`) are removed from the preview data. Cached per version + schema + build; the tool attaches it to `action=build` for any app that saves data.
3. **Quick scan** (`quick`), on EVERY publish: Cloud rule audit (a list anyone on the internet can read with personal fields and no recorded yes = FAIL; with her `confirm_public` yes it is a warning - the yes is kept as `public_ack` on the list and dropped when the rule stops being public), secrets in the code AND the built files (API keys, GitHub tokens, private keys, JWTs, written-in secrets), a fresh rule-test run. `publish_check` adds every FAIL (and a browser check that ran and failed; one that could not run only warns) to the existing TypeScript + code-rule blockers; switch `app_engine_publish_checks` (default on; conftest pins it off for the older suites).
4. **Deep scan** (`deep`), on demand before a big launch: the quick scan + code patterns (javascript: links = FAIL, target=_blank without noopener, plain http://), lists the code asks for that do not exist (FAIL), lists no screen uses, source maps, and a forced fresh browser check. It is checks in code - NO model reviews the code (not connected; the page and the result say so). Package advisories are NOT checked (the packages are Hoola's fixed vetted set; no feed is connected) - an info line says so.

Surfaces: tool `app_engine` actions `tests` and `scan` (what=quick|deep) (reads; registry stays 627); routes `GET /api/appengine/{ref}/checks`, `POST /api/appengine/{ref}/checks/{tests|browser|quick|deep}`; Studio Publish tab "Checks" (four results, four buttons, the stopping items named); the App Engine proof card also plants a bad-rule app (`bad_rule_refused`). FOUND while building: the core's sign-up rate limit (5 an hour per address) would have failed a repeated check - each check call uses a fresh made-up address; the first browser run failed an app whose root had text but no child element - the wait is on "root has children or text".

Tests `test_v0832_saboot.py` (9): rules on the real engine + planted engine bug, the tool after a rule change, planted bad-rule app refused at publish (fix passes, her yes kept and dropped), secrets in code + built files, the browser walk at both sizes (and a planted crash), the tool's browser proof, deep scan + routes, the Publish tab in a real browser, the story.

NOT VERIFIED on her VPS or with a real model-built app (the browser walk was run on small hand-made apps and the proof apps here). Not built: Vitest tests inside the app (Vitest is not in the vetted package set; the rule tests run on the server engine instead, which is where rules are enforced), a model-based deep review, an advisory feed, scans of files / functions (not built yet).

## v0.836.0 GHAR + SHURUAAT - L12 of the Lovable Studio plan: the Web Studio home and the first-build wait (owner: "GO L12"; built on main at v0.835.0)

- **Home** (`webstudio.js`): greeting by time of day + her first name (`/api/console/me` owner), three rotating lines per part of the day; placeholder typewriter "Ask Hoola to build " + 7 endings (45 ms a character, 1.6 s pause, stops while she types or focuses, not run under reduced motion); eight chips (Website, Online store, Dashboard, Booking site, Portal, Landing page, Blog, Internal tool) - a chip opens that kind's three starters, the same chip again closes them; "Ideas" link to the 1,00,000 generated templates.
- **24 starters** (`site/starters.py`, GET /api/site-starters): a complete specific ask each (what, who, what it must do) + a palette and one of 8 layouts. The thumbnail is an SVG drawn from THAT palette and layout, so the card shows the look the ask will be built in. They are not already-built sites (the plan's "built by the engine itself" needs a real model run on her server; not done here): choosing one puts its ask in the box and the normal Build runs.
- **Setting the stage**: the wait between send and workspace used to be labels moved by a client timer. The Studio now sends a `ticket` with POST /api/sites; `architect.build_now` writes its real stages (Reading your idea / Planning the pages and what each one holds / Choosing colours and fonts, and setting up the website / The workspace is ready) into the activity log under `stage-<ticket>`; the pending screen polls GET /api/sites/stage/<ticket> every 1.2 s and draws those steps with their own times. Plan mode keeps its timed labels (its call is a different route). A refused ask ends the log as an error.
- Tests `test_v0835_ghar.py` (3): the 24 starters, the stage steps + routes (build_now order with stubbed calls), a browser walk (greeting, typewriter moving, still under reduced motion, 8 chips, 3 cards with thumbnails, a card fills the box, the held first call shows the server's steps). One older pin updated on purpose: test_v0649 expected the single fixed greeting.
- NOT VERIFIED with a real model. Not built: the 240 ms composer re-dock move on the way into the workspace; starters with real screenshots; the `+` menu / mic / Chat mode on the home composer.

## v0.837.0 WB LOGOUT (+ refusal words)
AUTH403 'Maximum session allowed' was the real cause of the failed GST login; wb.logout added to wb_check and Disconnect; refusals carry WhiteBooks' own words; wb_check tries more 2B months / IMS spellings.

## v0.838.0 DRAFT - L13 of the Lovable Studio plan: drafts of a website, merged by section with named conflicts (owner: "GO L13", E6; built on main at v0.837.0)

- **Draft** (`site/drafts.py`): a named copy of the website's working files (section store, plan, look, facts, photos) made from its current version - a hidden `Site` row (`draft_of`, `draft_name`, `draft_base`) with its own private preview token and its own Hoola thread, so every existing tool (chat, edits, builds, History) works on it unchanged. At most 3 open per website; same name twice refused; starting needs the website idle and a version that kept its source (L7). The site list hides drafts; `hosting.blockers` refuses to put one live.
- **Accept** (her tap, `confirm`): three-way merge BY SECTION against the website's snapshot at the version the draft started from (`wapas` snapshots): only the draft changed -> comes across (added / changed / removed); only the website changed -> stays; both changed -> a CONFLICT, named ("Home page · hero"), never merged silently - Accept is refused until she picks the website's or the draft's for each. The design keys (plan, look, facts, offered looks, languages) merge the same way and are named in words ("The colours, fonts and design kit"). Applied as one new version of the website ("Merged draft 'X'"), undoable from History; the draft is then deleted. Discard deletes the draft; the website is untouched.
- **Data, said plainly** (different from Lovable's shared data, on purpose): a draft has its OWN data - nothing visitors sent (enquiries, orders, app rows, members) is copied in, and Accept never moves data either way.
- Surfaces: `GET/POST /api/sites/{ref}/drafts`, `POST .../drafts/{id}/accept` (resolutions {item: site|draft}), `DELETE .../drafts/{id}`; `website` tool actions `draft_new` / `draft_list` (Accept is not the tool's); Studio: a Drafts tab (cards with what changed, conflicts as radio choices, Open / Accept / Discard, Start a draft), a "Draft · name" pill, and in a draft the Publish button becomes "Back to the website" + "Accept or discard".
- Tests `test_v0837_draft.py` (5): copy + limits + never live, the conflict-named merge (nothing applied until settled; site-hero / draft-hero both ways), site-only + draft-only changes both survive and the design merge, tool + routes, a browser walk (start a draft, both sides change the hero, the radios, Accept).
- NOT VERIFIED with a real model. Not built: App Engine branches (the plan puts them after L14's GitHub sync), a visual diff of a draft against the website, drafts of a website that is still being built.

## v0.839.0 BAHI A3 (built as 0.838)
GSTR-1 checked against the register, saved as a portal draft on her tap (plan hash); EVC filing walk gated by BAHI_FILING. GSTR-1A not built. NOT VERIFIED on a live portal.

## v0.840.0 GITHUB DO TARAF - L14 of the Lovable Studio plan: App Engine apps and one GitHub branch, both ways, plus import (owner: "GO L14"; built on main at v0.839.0)

- **`appengine/gitsync.py`**, with her fine-grained GitHub token (the one typed only in the app for the website export; never in chat, never in a file). State per app in `<app>/github.json` (repo, branch, last synced commit, a manifest {path: blob sha}, the files kept apart).
- **Link** (her tap): the default branch of a repository, made private if missing. **Push** (her tap): one commit with the whole project (locked template files included so the repo runs), blobs only for files that changed, fast-forward only (never forced); refused while GitHub has commits she has not pulled; a secret in any file refuses the push. **Pull** (her tap): three-way by file against the last synced commit - only GitHub changed -> comes across; only the app changed -> stays; both -> a NAMED conflict she settles (app's or GitHub's) before anything applies. Every incoming file goes through the same laws as a write by Hoola (path rules, safety, design drift, vetted imports, size, secrets): all-or-nothing, the first problems named with file and token. Files Hoola keeps locked (package.json, vite config, tokens, Cloud files ...) and non-text files are never overwritten: they are listed, "kept apart", and the next push keeps GitHub's own copy of them.
- **Import**: a new app from a ZIP (this app's own export, GitHub's Download ZIP, another builder's export; one wrapping folder removed; paths that climb out, links, node_modules and .git dropped; 8 MB / 16 MB unpacked / 1,500 entries) or from a repository. A foreign project rarely obeys the design tokens: a file that breaks the rules is NOT brought in and is listed with the reason (Hoola can be asked to fix them); the project's packages that the vetted set lacks are listed. An app imported from a repository is linked, with the unimported files kept apart so a push does not delete them.
- Not synced, on purpose: her data and Cloud rules (server-side `cloud/`), her visitors' rows, hidden files, node_modules, dist.
- Routes: GET/DELETE `/api/appengine/{ref}/github`, POST `.../github/link|push|pull`, GET `.../github/compare`, GET `/api/appengine/{ref}/export.zip`, POST `/api/appengine-import/zip` (raw body) and `/github`. Studio: a GitHub section on the Publish tab (link form, Compare with conflict radios, Pull, Push, Unlink) and a "Bring in a project" panel on the Apps home.
- Tests `test_v0839_github_sync.py` (5) against `FakeGitHub`, a fake that speaks the Git Data API: the ROUND TRIP (push, a change on GitHub pulled back, push of a local change, the repo imported as app B with equal files, the ZIP export imported back), named conflicts + incoming rule breaks refused + locked files kept apart, ZIP safety + listing of refused files, the routes, a browser walk.
- NOT VERIFIED against real GitHub (the fake follows the documented Git Data API). Not built: several branches, pull requests, webhooks (a pull is her tap), syncing data / Cloud rules, binary files (images are kept apart), resolving a conflict line by line.

## v0.841.0 BAHI A4 (built as 0.840)
GSTR-3B prepared with A2 credit, least-cash set-off, portal compare, draft save + set-off on her confirm (plan hash), payment plan (no challan, no money), EVC filing gated by BAHI_FILING. NOT VERIFIED on a live portal.

## v0.842.0 PROOF - L15 of the Lovable Studio plan: the Studio card and three proof apps (owner: "GO L15"; built on main at v0.841.0)

- **The Studio card** (`quality/studiocard.py`, asks in `studio_asks.py`) - the L0 row of the plan, which had never been built, so there is no recorded baseline on the old Studio. 30 asks in an owner's words: 10 brochure + 8 shop / booking (Site Engine) + 8 portal / dashboard + 4 SaaS (App Engine). Each run is scored IN CODE as the hidden tenant `__studiocard__`: built, seconds to ready, rupees (the tenant's own meter), preview errors, gate failures (Site: launch blockers; App: the scans and rule tests), design failures (over 2 fails), the first screen's must-words, and for 3 asks a small exact edit that must land with NO model call (Rs 0) - its seconds recorded. The scorer is calibrated on 9 planted faults (each fails for its own reason). `python -m app.quality studio` = the free card (ask set valid, scorer calibrated; `--proof` adds the App Engine proof apps); `--live --budget-inr N` = the real run (site / app asks interleaved so a budget that runs out leaves both the same coverage, stops itself); `studio compare a.json b.json` = before / after metric by metric, the right way round. The live App Engine ask is a real Hoola turn (`santosh.run_turn`) with the `app_engine` tool, then the box build, the scans and a Chromium read of the first screen.
- **Three proof apps** (the App Engine proof set is now 7): the clinic (appointment requests saved through Hoola Cloud, visitors cannot read them), a **coaching portal with roles and payments** (students sign up, read notices, RECORD a fee payment with its UPI reference and see only their own payments; the office - role staff - sees all, confirms or rejects, posts notices; payments are records the office confirms, NOT an online gateway), and a **dispatch dashboard** (staff add jobs and see all of them; only the dispatcher assigns a driver, marks delivered or deletes; live counts). Each is built in the box, walked in Chromium (sign-up through the sealed frame), and its rules played against the server (`proof._rules_portal` / `_rules_dispatch`: a second student reads nothing of the first's, cannot confirm; a visitor reads nothing). The proof card also plants a bad-rule app (L11).
- **Numbers, before vs after** (measured in the build sandbox, App Engine proof card, Docker box, Chromium): L8 (v0.824) recorded 5/5 apps built, median 6.2 s, 8/8 planted bad writes refused, publish with only TypeScript + code checks. Now (v0.842): 7/7 apps built and PUBLISHED through the quick scan + rule tests + browser check, build median 7.4 s (portal 5.95 s, dispatch 6.04 s), 8/8 planted bad writes refused, the planted bad-rule app refused, 0 preview errors, phone overflow none on all seven. Sandbox timings; the slower median is the extra apps, not a regression claim.
- **NOT VERIFIED**: no LIVE Studio card has run (a model, the box and Chromium on her server are needed; the card prints the assumed rupees until a run measures them: Rs 60 per site ask, Rs 90 per app ask, assumed); the owner has not walked the three apps; the Site Engine has no "before" row (its baseline would come from the first live card). Tests `test_v0841_studio_proof.py` (5).

## v0.843.0 BAHI A5 (built as 0.842)
e-invoice (IRN) + e-way bill on her confirm: attempt row first, duplicate / timeout adopted, 24 h cancel and 30-day limit, EWB by IRN. NOT VERIFIED on a live IRP.

## v0.844.0 LANGGRAPH G7 (built as 0.806; their v0.806-v0.843 landed while the full suite ran - REBASE PROTOCOL, both kept) — the turn graph on by default (12 Nov 2026; owner: "GO G7")

Phase G7 of `docs/LANGGRAPH_TURN_PLAN.md`, the last phase.
- `config.chat_graph` default True. `Settings._graph_needs_langgraph` probes langgraph.graph / langgraph.checkpoint.sqlite / aiosqlite with find_spec (nothing imported) and forces the switch off with ONE loud ERROR when any is missing.
- `turngraph.run_steps`: the langgraph-missing fallback logs once per process; the no-conversation-id fallback kept.
- `santosh._steps_inner` unchanged, marked as the rollback path. Rollback = `CHAT_GRAPH=false` in the VPS .env + `pm2 restart santosh --update-env`.
- `main.turn_engine()` + a startup log line; `/api/agent/stats` gains `turn_engine`.
- Retired POST /api/aep/turn + `agent/aeptune.py` + `test_v0610_hoola_adopt.py` (it failed on every real call: an async brain handed to a sync _generate). /api/aep/runs and app/aep's tracer / vault sink / graph stay.
- Red check: every red of the full branch run re-run in the same order with CHAT_GRAPH=false and with the default. One graph-only red (test_v0187_realtime::test_the_turns_own_reply_stops_the_duplicate tested the old loop's _answered_since timing; now pins CHAT_GRAPH=false). All others (~457: missing Playwright browser, appmaker/site look tests, stale version / stamp / Hinglish pins, order interference) fail identically with the graph off.
- Tests: test_g7_turngraph.py (7), test_g0 asserts the default is on; 145 passed across g0-g7, routines, v0187, voice on the rebased tree.
- NOT VERIFIED: no real turn has run on the graph on the VPS yet. Not built: approval cards that pause the graph; Gemini Live's directly-called tools through the graph. A later delete of the old loop is listed in the plan doc section 6.

## v0.845.0 BAHI A6 (built as 0.844)
Purchase bills read locally into a cross-checked DRAFT (acc_intake); register only on her tap. WhatsApp / mailbox hand-off not wired.

## v0.846.0 BAHI A7
Bank + UPI reconciliation, stored: statement import (CSV / Excel / MT940 / locked PDF), narration reading, proposed matches with reasons, confirmed on her tap, payers remembered, gateway settlements, stored month-end statement. NOT VERIFIED on real statements.

## v0.847.0 BAHI A8
Party master, ageing, MSME 15/45-day + Rule 37 watches, reminder drafts, TDS worksheet/register/quarter (rules file tds.json), 26AS match. Hoola pays, deducts and files nothing. s.393 item numbers not read.

## v0.848.0 BAHI A9
Tally voucher XML + JSON from the register, party ledgers in the file, her ledger names; the monthly CA pack ZIP with worksheets, evidence and open questions; close a month on the pack hash (locks it). Zoho / live Tally / CA login not built. NOT VERIFIED in a real Tally import.

## v0.849.0 BAHI A10
Month-end checklist ticked only from records, MIS + daily cash line, one calendar with yearly dates (annual.json), accuracy sweep, GSTR-9 comparison. Nothing sent or filed. NOT VERIFIED: GSTR-9 reads.
## v0.850.0 DESKTOP TEAM + HOOLA PC TEAM (12 Nov 2026; owner: "CAN HOOLA DEPLOY MULTIAGENT FOR DESKTOP WORK" -> "GO DESKTOP TEAM + HOOLA PC TEAM --- PERFECT, SYSTEMATIC, SMOOTH AND ADVANCE")

**The audit first (same day):** Mera PC worked end to end (213 PC tests green, desktop 1.9.0 live, agent-desktop
v1.1.0 proven on a real Linux desktop through Hoola's own axtree.py: snapshot -> set_value -> click -> the app returned
the typed text). But desktop work was ONE task per PERSON: `operator.start` cancelled any running task on ANY of her
PCs ("one operator per person"), the hub picked "the last connected" PC (two Windows PCs = always the same one), she
could not name a PC, sub-agents are barred from pc_do, and "band karo" / "cancel" never reached a running PC task
(kaamstop's native stop had no branch for the `browser` kind PC jobs use, so the row said stopped while the PC kept
clicking).

**What changed (frozen-PC exception recorded in CLAUDE.md):**
- `pc/operator.py`: Op gains `device_id` / `device_name` / `team`; `_pc` sends every step to THAT device (kind still
  rides for the old fakes); `start(pc=, team=, replace=)` - `_choose` = the PC she named (hub.find), else for Hoola PC
  a FREE one of Hoola's own PCs, else her personal PC (never the cloud PC by accident). One task per PC: a new task on
  the same PC replaces the old (old pc_do behaviour) unless replace=False -> `PcBusy` (pc_team never interrupts her
  work). `busy(tenant, device)`, `running(tenant, device="")` (newest), `running_all`, `stop_all`. Live card / report
  carry the PC name ("Aapka PC · Office PC").
- `pc/hub.py`: `devices(tenant)`, `find(tenant, name, kind)` (exact name / device id, then every content word of a
  short name; ambiguous = None, never a guess), and `_pick(device_id, kind)` stays on that device or returns None (a
  task never jumps to another PC mid-way).
- `agent/pc_tools.py`: `pc=` on pc_do / hoola_pc_do (PC_NOT_FOUND names what is online); NEW `pc_devices` (every PC,
  her / Hoola's, busy + what it is doing) and `pc_team` (1-6 parts, cap `pc_team_max` 4; every part gets its OWN PC
  before anything starts; 'hoola' = a different free Hoola PC per part; same PC twice / unknown name / control off /
  busy are skipped WITH reasons; one `pcteam_` id; waits pc_wait_seconds then each unfinished PC reports on its own).
  Family `pc` (admitted only when she names a PC, as before); labels; voice reaches them via santosh_kaam.
- `kaamstop.py`: running PC tasks are listed even without a watch row (`_pc_tasks`), and the native stop for
  `browser:pcop_*` calls `operator.stop` - "excel wala band karo" stops that PC, "sab band karo" stops all.
- `prompts.py`: a DESKTOP TEAM paragraph (pc= names, pc_devices, pc_team for separate screen parts, research stays on
  the server, never two parts per PC, never interrupt a busy PC).
- HOOLA PC TEAM: vps-ops `pc_deploy` lines = 1..4 Hoola PCs (anything else = 1 = the old single PC); PC 1 keeps
  `hoola-pc` + `hoola-pc-data` + its pairing, PC i = `hoola-pc-i` + `hoola-pc-i-data` named "Hoola PC i"; a free-RAM
  warning (each PC may use 2.5 GB; 8 GB fits ~2). `pc_pair` lines = CODE (PC 1) or N-CODE (PC N); `pc_logs` shows all.
  `desktop-linux/docker-compose.yml` gains hoola-pc-2 under the `team` profile.
- Registry 627 -> 629 (pins swept); config `pc_team_max` 4.

**Tests:** NEW `test_v0836_desktop_team.py` (16): hub find / devices / device-pinned pick, two PCs at once, replace vs
PcBusy, unknown PC + free Hoola PC pick, control off refused, every step on its own device, pc_team on 4 PCs with one
team id, never interrupts + explains, cap / empty / nothing-online, pc_devices busy state, named + "sab" stop, stop_all,
registry / family / labels / voice route, prompt + vps-ops + compose shapes, version. The 15 PC suites (213) stay green.

**NOT VERIFIED (said plainly):** no real Windows PC and no second paired Hoola PC has run a team job; RAM for 2+ Hoola
PCs on her 8 GB VPS is an estimate; the phone / console show each PC's live card as before but have no "team" view; the
PC operator still runs on whatever the Haiku / GLM switches choose (see the audit - not changed here); the Windows
desktop exe and agent-desktop v1.2.0 upgrade are not part of this release.

## v0.850.0 AGENT-DESKTOP FULL (same release as DESKTOP TEAM; owner: "IS ALL THIS REPO FEATURE IS NOW IN HOOLA DESKTOP" -> "GO AGENT-DESKTOP FULL")

**Before:** Hoola wrapped 10 of agent-desktop's 61 commands (v1.1.0). set-value put the text ON THE COMMAND LINE (an
Aadhaar / PAN from her ID locker was readable by any program listing processes on her PC), element states (checked,
disabled ...) were thrown away, click surfaces printed as a broken Python repr ("{'id': 'w-1.1-org-gn"), and Hoola's
own Linux PC had no exact mode.

**Now (desktop 1.10.0, frozen-PC exception recorded in CLAUDE.md):**
- `build-desktop.yml` pins agent-desktop **v1.2.0** (official archive, checksum-verified; same single agent-desktop.exe).
- `axtree.py`: `_run(stdin=)` - set-value / type / clipboard-set send text over `--stdin`; snapshot rows carry
  `states`; `_surfaces()` turns {id, type, title} into 'menu: File'; NEW get / is_state / act (check, uncheck, toggle,
  expand, collapse, clear, scroll-to, right-click) / select / type_text / scroll / close_app (never --force) /
  displays / window_shot (one window as JPEG) / surfaces / open_surface (start-menu, taskbar, tray, action centre,
  quick settings) / notifications + dismiss / action (an expected app or title is REQUIRED so the wrong popup is
  never touched) / clipboard get / set / clear / batch (2-8 SAFE steps: no text, keys, launch, close; waits clamped).
  Left out on purpose: focus, double / triple click, hover, mouse-*, key-down / up (all need --headed = cursor / focus
  moves; the pixel lane does physical input behind the same switch), mcp, session / trace / cursor overlay, skills.
- `actions.py` do_ax_get ... do_ax_batch behind the same control switch (`_axcall`), close-app refuses Hoola Desktop /
  Explorer / system tools.
- `pc/operator.py`: 14 new tools for the model (ax_get, ax_is, ax_act, ax_select, ax_type, ax_scroll, ax_window_shot,
  ax_displays, ax_system, ax_notifications, ax_notification, ax_clipboard, ax_close_app, ax_batch) in TOOLS and
  HOOLA_TOOLS; `_ax_full`: ID-locker refs filled for ax_type / clipboard set, clipboard READS masked (pii), a
  notification button that sends / pays / deletes needs a FRESH ask_approval (one yes = one press), "not delivered"
  said plainly, a POLICY_DENIED / ACTION_NOT_SUPPORTED answer sends the model to the pixel lane (no retry loop), an
  older desktop gets the upgrade line (AX_FULL); ax_window_shot rides as an IMAGE; prompt paragraph 'v0.842 the full
  exact kit'.
- Hoola PC (`desktop-linux/`): the SAME axtree.py (a test keeps the copies identical), Dockerfile installs the
  checksum-verified Linux binary + at-spi2-core / libatk-adaptor, start.sh runs a real session bus + the AT-SPI bus,
  agent.py routes every ax_* (AX_ACTIONS), agent 1.4.0.

**Proof:** the real v1.2.0 binary on a real Linux desktop (Xvfb + openbox + AT-SPI) through Hoola's own axtree.py:
set_value over stdin verified + read back, clear, type_text, is enabled, select '18%' (the app returned
"Gupta & Sons|18%"), batch of 2, batch refuses typing, window JPEG, displays, surfaces, clipboard set / get / clear,
readable surfaces after a click, a disabled OK seen in the snapshot states, close_app graceful; GTK4's checkbox has
no accessibility action, so check / toggle were REFUSED honestly (ACTION_NOT_SUPPORTED) - the pixel lane covers such
apps. Tests: NEW `test_v0842_agent_desktop_full.py` (16, a recording fake helper: no text on argv, states, surfaces,
every refusal, batch safety, close never forces, server rules); the 15 PC suites + test_v0472 green with the upgrade.

**NOT VERIFIED:** no real Windows PC has run v1.2.0 through Hoola (needs the new SantoshDesktop.exe from build-desktop);
Windows notifications / Start menu / taskbar were not reachable here (Linux has no Start menu; no notification daemon
in the test box); exact mode on the Hoola PC image is untested until `pc_deploy` rebuilds it on the VPS.


## v0.851.0 PC BRAIN — Qwen 3.8 Max or Sonnet 5.5 for the PC loop (owner: "FOR PC WE CURRENTLY CHOOSE 2 MODELS QWEN 3.8 AND SONET 5.5 --- WILL TEST IT FIRST ON THIS --- WILL START WITH QWEN")

After the desktop-model research (OSWorld 2.1 offline: Opus 5.5 87.2, Sonnet 5.5 83.9; OSWorld-Verified: Qwen3.8-Max 86.1) the owner chose two models
to test, Qwen first. Found while reading: the PC loop asked for Sonnet but `usage.one_model` (claude_one_model = Haiku) and the GLM door rewrote it,
and a reply with no tool call was reported as a finished task even when it was cut off (max_tokens 1500) or refused.

- NEW `server/app/pc/brain.py`: `choose(want)` -> (brain, model, note) from the task's pick or `pc_model`; Qwen without `QWEN_API_KEY` = Sonnet + a note
  appended to the result. `think(op, client, messages, params, retry)`: Qwen = Anthropic blocks -> OpenAI chat (`to_openai`: system, image_url data URIs,
  tool_use -> tool_calls, tool_result -> role=tool text + its screenshot in the following user message; `tools_openai`; `from_openai` maps tool_calls back,
  bad JSON args = {}, finish length -> max_tokens, content_filter -> refusal), POST <QWEN_BASE_URL>/chat/completions (default dashscope-us compatible-mode),
  2 retries on 408/429/5xx/network, tokens counted via usage.record (price qwen3.8-max $2/$6, cache read $0.25 - secondary sources). Sonnet = the old
  `_think_retry` with `usage.ONE_MODEL_BYPASS` + `glmdoor.CLAUDE_ONLY` set for that call. Log `pc brain <brain> <model> step N <s> stop=`.
- `pc/operator.py`: Op.brain / brain_model / brain_note (live card carries brain + model), start(brain=), `_run` calls brain.think, `pc_max_tokens` (4000),
  no-action reply with stop max_tokens / refusal / no text = partial with an honest summary.
- `agent/pc_tools.py`: pc_do / hoola_pc_do `model` enum qwen|sonnet. config: pc_model "qwen", pc_qwen_model, pc_sonnet_model, qwen_api_key, qwen_base_url,
  pc_qwen_thinking ("" / on / off -> enable_thinking), pc_max_tokens, pc_brain_timeout_s. conftest pins PC_MODEL=sonnet for the older PC suites.
- Tests `test_v0851_pc_brain.py` (10); PC suites 63 passed.
- NOT VERIFIED: no live Qwen call (no key in this sandbox); Model Studio tool calling with images for qwen3.8-max and its default thinking behaviour are
  from docs / third parties only; the base URL depends on her Model Studio region (Singapore / Tokyo use a workspace host - set QWEN_BASE_URL).


## v0.852.0 QWEN VIA OPENROUTER (owner: "CAN WE ACCESS QWEN VIA A OPENROUTER")
OpenRouter's /models (read 12 Nov 2026) lists qwen/qwen3.8-max-0902 (text + image + video in, tools, $2 / $6 per 1M, 1M context; no plain
qwen3.8-max slug; qwen3.8-max-prime $4 / $12). `pc/brain.qwen_route()` = (url, key, model): QWEN_API_KEY set -> Alibaba Model Studio
(QWEN_BASE_URL may point at OpenRouter too); else the server's OpenRouter key (`providers.key_of("openrouter")`) -> openrouter.ai with
`pc_qwen_openrouter_model`; neither -> Sonnet + the note. On OpenRouter `pc_qwen_thinking` rides as `reasoning.enabled`, never Alibaba's
enable_thinking. Price row for usage. 1 test. NOT VERIFIED: no live call (no key in the sandbox).


## v0.853.0 QWEN ONLY OPENROUTER (owner: "DONT GO VIA ALIBABA CLOUD GO VIA A OPENROUTER")
`pc/brain.qwen_route()` now has ONE route: openrouter.ai/api/v1 with the server's OpenRouter key and `pc_qwen_openrouter_model`
(qwen/qwen3.8-max-0902). Removed: the Alibaba Model Studio path, the `qwen_api_key` / `qwen_base_url` / `pc_qwen_model` settings and the
qwen3.8-max price row; `pc_qwen_thinking` only ever rides as OpenRouter `reasoning.enabled`. A test pins that the Alibaba settings stay gone.

## v0.854.0 LANGGRAPH G8 (built as 0.846; their v0.846-v0.853 (PC BRAIN, QWEN and others) landed while it was built - REBASE PROTOCOL, both kept) — approval cards park the graph + call tools on the ledger (12 Nov 2026; owner: "GO G8")

Phase G8 of `docs/LANGGRAPH_TURN_PLAN.md` (section 7 has the full design).
- NEW `agent/turnpark.py`: table `turn_card_parks` (registered in db.init_db + ensure_table), `answered(kind, id, answer, result)` claimed once, `resume_due` runs one `approved:card` turn that resumes the parked thread with `Command(resume=...)`, `sweep` in worker `card_park_jobs` (15 s), TTL `graph_card_park_ttl_h` 26 h, declined tool + arguments refused in that thread.
- Hooks: bazar.decide + expire_approvals, mailbox.send_draft (sent / scheduled / undo window / failed), the cancel route, email_tools._cancel_pending (replaced); the card's own chat line is not written when a park took the answer. turn_inbox marks `waiting_tap`.
- NEW `agent/calltools.py`: call direct tools through `santosh._run_tool(dispatch_fn=...)`, ledger on `<chat>:call` within `graph_call_tools_window_m` 30 min, G3 facts per did entry, `receipt_once` via a G5 record `call:<id>:receipt`; callreceipt lists cards as waiting and ambiguous steps as to check.
- Switches: `GRAPH_CARD_PARK=false` / `GRAPH_CALL_TOOLS=false` turn each off alone; `CHAT_GRAPH=false` turns the whole graph off.
- Tests: test_g8_turngraph.py; 132 passed across g0-g8, routines, v0187 on the rebased tree; the reds in email / v0554 / v0662 / v0442 / human_voice fail the same on main.
- Not built: parking for the other card kinds (desk CARD_KINDS, ask_forms, operator asks, studio price cards, pg_write); a scheduled / undo-window email's later worker failure is not fed back.
- NOT VERIFIED live: no real tap has resumed a parked run, no real call has re-issued a direct tool through the ledger.

## v0.855.0 PC CONFUSION (owner: "FIRST CHECK DOES IT CONFUSE BETWEEN HOOLA ON PC AND A USER PC" -> "GO FIX PC CONFUSION")
Found by reading the routing: (1) her PC off + Hoola's cloud PC on -> a pc_do job ran on Hoola's PC (operator._choose fell back
to hub._pick = the last-connected PC); (2) every caller with no PC named (email attachment / Drive / Photos save to her PC,
docdesk search / recent / list / send / open, desk_tools open_file, the PC connector) took the LAST CONNECTED PC, which could be
Hoola's VM; (3) agent/pick.py allowed pc_do on a 'Hoola ka PC' ask and hoola_pc_do on a 'mere PC' ask; (4) pc_do took a Hoola PC
name (its description even said 'Hoola PC 2'). Fixed: hub._pick with no device + no kind = her personal PCs only (None if none);
is_online(tenant) = a personal PC online; a device id not online = None (was the last PC); operator._choose: an exact device id is
taken as is (pc_team), a name for pc_do is looked up among HER PCs only and a Hoola PC name is refused naming hoola_pc_do, no
personal PC + Hoola PC online = PC_OFFLINE_HOOLA_ON -> pc_do tells the model to ASK her before hoola_pc_do; pick.check refuses the
wrong PC tool for the place she named. Tests test_v0854_pc_confusion.py (7). NOT VERIFIED with two real PCs online.

## v0.856.0 LANGGRAPH G9 (built as 0.855; nothing took a number while it was built - REBASE PROTOCOL, both kept) — Hoola Code truth + told once, studio price cards park the graph (12 Nov 2026; owner: "GO BOTH")

Phase G9 of `docs/LANGGRAPH_TURN_PLAN.md` (section 8).
- NEW `devsahayak/truth.py`: facts from the task row in the G3 shape; claims read from explain / test_plan (hedges like 'should pass' are not claims); `task_view` gains `truth`; `around.tell_end` says 'not everything is confirmed' + needs_you when a claim has no fact, and is told once via `turndeliver.once` (no turndeliver change). Switch `dev_truth`.
- `agent/turnpark.py` kind `studio` (`card_of`: waiting_owner `sa...` + rupee price; `still_waiting` reads the project JSON); `turngraph._note_card` puts the run's tenant on the card; `studio.service._ask` returns `project`; `studio.decide` / `expire_asks` call `turnpark.answered`.
- Tests: test_g9_turngraph.py 11 (also with DEV_TRUTH=false and GRAPH_CARD_PARK=false); 66 passed / 4 skipped across g7-g9, routines and the Hoola Code suites on the rebased tree; two studio reds (v0259 dropdown pin, v0351 order interference) fail the same on main.
- Not built: claim words still regex; CI still running = 'tests pass' unknown; a studio background job's later failure not fed back; other card kinds (desk, ask_forms, operator, pg_write) still do not park.
- NOT VERIFIED live: no real Hoola Code round judged, no real studio tap resumed a parked run.


## v0.857.0 PC SPEED (owner: "TASK DOING PROCESS IS VERY VERY EXTREEM SLOW IT SHOULD BE IN REAL TIME" -> "GO PC SPEED" -> "ALL 100 % PC WORK FROM APPS TO BROWSER TO SETTINGS")

Her first working PC task (after the AIHubMix quota and the OpenRouter key's $10 cap were fixed) ran far too slowly. Every PC
step = screenshot from her PC -> one model call -> one action. The changes, server only (desktop 1.10.0 untouched):
- Qwen thinking OFF by default (`pc_qwen_thinking` "off"; it reasoned before every click) and OpenRouter `provider.sort`
  "latency" (`pc_qwen_provider_sort`) so the fastest-answering Qwen host serves each step.
- KEEP_IMAGES 3 -> 2: less to read on every step.
- The biggest structural one: a keyboard step (type / key) sent in the SAME turn as open_app / ax_launch / focus_window /
  open_url / switch_tab now runs once that target is really the active window (`_target_of` turns the step into words -
  app name, window title, tab, site host minus www/com and every browser name; `_opened_in_front` checks fresh screens for
  up to ~2.4 s). No match = held exactly as before; clicks after a screen move still always wait for the next screenshot.
  'Open Notepad and write the email' / 'open the site and press the shortcut' save a whole model round.
- SPEED prompt rule: as few turns as possible, a whole text in ONE type, done in the same turn as the last keyboard step,
  page_* / ax_* tools first (no screenshot round).
- Log `pc step N screen Ns` beside `pc brain ... step N s` so the next slow run shows where the time goes.
Tests test_v0856_pc_speed.py (9). NOT VERIFIED: no timing from her PC yet.


## v0.858.0 PC FLOW — the browser she names, her words into the running task, she picks the pizza (owner's Swiggy test, frozen-PC exception)

Her test: "Chrome kholo aur Swiggy se pizza order karo" on her PC. Three problems, three root causes:

1. **Edge instead of Chrome.** The desktop's `open_url` (desktop/santosh_desktop/control.py, frozen exe) focuses the FIRST
   RUNNING browser in the order chrome, msedge, brave, firefox. Chrome was closed; Edge always runs in the background, so
   it won. The open_url tool had no browser choice. Fix (server only, no exe rebuild): `operator._named_browser` reads the
   browser she names in the task or in her later words (negations like 'edge nahi' / 'not edge' skipped, the last one
   wins); `_open_in_named` brings THAT browser forward (open_app, polls the active window up to ~6 s), ctrl+t, types the
   address, Enter, waits for the title and returns the first page words. Chrome already open (a window, or opened earlier
   in this task) keeps the desktop's one-step path, because the desktop tries Chrome first.
2. **Wandering between three browsers on two computers.** Every word she said mid-task was a NEW chat turn: pc_do
   started a fresh task (replace=True threw the running one away), and `where.worked` held the chat on her PC only for
   website-form tasks, so the model could go to hoola_pc_do / browse_web. Fix: `operator.tell` puts her words into the
   running task as a note (`_take_notes` adds 'HER NEW WORDS' to the next step's message; a browser she names switches
   `op.browser`); `pc_do` during her running task in the same chat (or the call made from it, `same_chat` through
   callconv) steers it instead of starting a new one, unless `fresh=true`; `where.working` = "pc" while her PC task runs;
   `pick.check` refuses hoola_pc_do then unless she names Hoola's PC in that message.
3. **No question before choosing.** The PC loop had only ask_approval / ask_otp. NEW `ask_user` tool (question + options,
   read from the page with prices): a chat note with numbered options, a `pc_ask` event, a call inject asking her out
   loud, waits up to 10 min (`ASK_WAIT_S`). Her next chat line answers it before the model (`operator.answer_from_chat`
   in `santosh._run_turn`, stop words excluded), and on a call the voice model passes her words through santosh_kaam,
   which reaches the same hook. Prompt rules: SHE DECIDES THE CHOICES (item, size, add-ons, address, slot), THE BROWSER
   SHE NAMED, HER NEW WORDS win.
4. **Real-time voice.** `_speak` hands the live call a short update at the milestones (open_app / open_url / switch_tab /
   form fill / approvals), at most every 12 s, through the existing `voice.inject` (waits for a pause).

Tests: NEW `test_v0858_pc_flow.py` (11). `test_v0166_pc_full_hands.py`'s fake desktop now lists a Chrome window
(the 'Chrome already open' one-step case). PC sweeps 150+ green; `test_v067_operator::test_replay...` and
`test_v0475::test_console_stamps` red on the commit before too. NOT VERIFIED on her PC: the ctrl+t path, the ask on a
real call.

v0.858.0 follow-up (owner: "IS IT SAME FOR VOICE CALL"): on a call the PC task's question is asked out loud, and her
spoken answer is now caught from her own words at the end of her turn (`Call._pcask_listen` in `finish_turn`, the
spoken-OTP pattern) instead of depending on Gemini passing it on; a call-brain ask answers with her words only (the
'(Call ne samjha: ...)' tail dropped); the first answer counts (`ask["answered"]`), a later line becomes a note.
Follow-ups on the call steer the running task through `same_chat` (call record / side record -> its chat). 2 tests.

v0.858.0 follow-up 2 (owner: "now voice call saying i dont have ability to access your pc"): two causes. (1) A call
ask reaches the brain as her words + "(Call ne samjha: <Gemini's reading>)"; Gemini speaks TO her, so its reading says
"aapke PC", and `where.place` read "aapke PC" as HOOLA's own PC (the v0.194 possessive rule) - the job was refused for
pc_do or pushed to Hoola's PC. Now only her words decide the place; the reading counts only when hers name none, and its
aapke / your / tumhare = HER PC (`where._CALL_READ`, `_CALL_YOUR`). (2) Gemini answers "no-tool" asks itself and its
voice prompt never said Hoola can work on her PC, so it said it could not; PERSONA_BRAIN + the santosh_kaam description
now say her PC work goes to santosh_kaam and never to answer "I can't access your PC". 2 tests.

v0.858.0 follow-up 3 (owner: "STILL VERY CONFUSE" + her pm2 log): the log showed (a) call TNAz9UMxDIgVx0BS: 3 turns,
0/0 tools - Gemini answered her PC ask itself ("cannot access your PC"), Hoola's brain never heard it; (b) the 09:29 chat
job ran with 32 tools + screenshots = `computer_operator`, Hoola's OWN server browser (the Swiggy ask named no PC, so
v0.271 sent it to the server). Fixes in CODE, not prompt words: `Call._pc_rescue` (finish_turn) - a call turn whose words
are a PC ask (chrome / browser / laptop / computer / Excel / Tally / PC...) that reached no santosh_kaam, with her PC
online, is handed to the brain by the system itself + the voice is told to correct itself; `pick._her_account_site` -
an ORDER on a site where she has her own account (Swiggy, Zomato, Amazon, Flipkart, IRCTC, Uber...) with her PC online
and no place named is refused for Hoola's browser and Hoola ASKS 'Yeh aapke PC par karun?' (v0.271 kept: a PC only on
her word); she names Hoola's browser = it runs there. 2 tests.

v0.858.0 follow-up 4 (owner: "IT USES ITS OWN BROWSER THEN SUDDENLY EDGE THEN SUDENLY CHROME"): two more gaps closed.
(1) A PC task that names NO browser still took whatever browser RAN (Edge in the background): now `_browser_for` =
her words > the browser she named in a recent PC task (PC memory) > Chrome; when she named none and a browser WINDOW is
open, that window is used; Chrome missing = her own browser as before (`browser_src` said / remembered / default).
(2) A website call moved onto her PC while her task ran there was dropped as `pc_busy`; now it goes INTO that task
(`tools.py` -> `operator.tell`), and the v0.858 order-site question never fires while her PC task runs or when she named
her PC (the steer moves it). 3 tests.

## v0.859.0 R0 EYES FIRST (the Claude-style phone redesign, phase R0)

Owner: "GO R0" on `docs/HOOLA_APP_REDESIGN_PLAN.md` (the plan made after her Claude APK research files + 24 Claude
screenshots, and the design canvas of the 10 basic Hoola screens). Built as 0.858; their PC FLOW took 0.858.0 -
REBASE PROTOCOL, both kept.

- **Fonts bundled.** `assets/fonts/` = 20 static TTFs (Manrope 400-800, Sora 400-800 = today's look; Literata 400/500/600
  + italic, Schibsted Grotesk 400-700, JetBrains Mono 400/500 = the redesign), 2.0 MB, written by
  `tool/fetch_fonts.py` from Google Fonts with the names google_fonts looks for (`<Family>-<Variant>.ttf`), so
  `GoogleFonts.*` finds them in the asset bundle before any download: no text flicker on first open, works offline,
  and test machines render real glyphs. pubspec gains `- assets/fonts/`; OFL notice in THIRD_PARTY_NOTICES.md.
- **Screen pictures on CI.** `test/goldens/screens_test.dart` pumps 8 main screens (setup, Today, Chat empty, Chat with a
  fixed sample reply incl. heading / list / inline code / bold / table, Talk, Connect, Main, AI employees) at 390 x 844
  x2 with real fonts + the SDK's Material Icons, plugins answered by quiet mocks, each screen its own test so one that
  cannot render never hides the others; `.github/workflows/app-screens.yml` runs it on every app change and uploads
  **hoola-screens** (each PNG + `screens-all.png` contact sheet from `tool/contact_sheet.py` + the log) and lists the
  pictures / failures in the run summary. Pictures only, no pass / fail comparison yet - the screens are about to
  change on purpose. The workflow also runs `test/fonts_test.dart` + the existing `md_text_test.dart` (never run on
  CI before).
- No server behaviour changed (version pins only).

NOT VERIFIED: Flutter cannot run here - the first run of app-screens on CI is the first time these tests execute;
screens with no server behind them show their empty / first-open states (the chat sample is the exception).
v0.858.0 follow-up 5 - DEEP AUDIT (owner: "AGAIN GO DEEP FIND THE FLAWS -- WE WANT IT TO WORK SMOOTHLY ACCROS ALL SURFACES
IN REAL TIME PERFECT AND RELIBLE"). Three independent read-only reviews (chat routing / voice call / PC operator loop)
found ~27 flaws; fixed:
ROUTING (agent/where.py, pick.py, santosh.py, tools.py, pc_tools.py, operator_tools.py)
- her 'haan' to Hoola's own 'Yeh aapke PC par karun?' never named her PC -> pc_do refused both ways = the wandering;
  `where.offer` (set when pick asks) + `remember` turns a plain yes (`_YES`) into place pc.
- 'Chrome kholo ...' named no place -> `where.browser_ask` + her PC online = place pc (santosh._run_turn).
- a FINISHED / stopped task locked the chat on the PC for 45 min (unrelated asks pulled to the PC) -> `where.release`
  in the operator's finally: done keeps only the short follow-up place, stopped / failed keeps nothing.
- steer texts named 'Google Chrome' and overrode the browser she named -> 'her browser'; a moved tool call's wording
  goes into the task as Hoola's note (`tell(hers=False)`, never 'HER NEW WORDS', never overrides her browser).
- place state keyed by raw ids: call / side records lost the chat's place -> every key via `where._k` (chat_of).
- hoola_pc_do follow-ups started a parallel / replacing task -> steer into the running Hoola-PC task (fresh=true for new).
- a pc_do from another chat cancelled her running task -> replace=False there, PcBusy said plainly.
- pick's order-site question fired while steer would move it / on Hoola's PC; Swiggy & co. added to the website words.
PC OPERATOR (pc/operator.py)
- Edge titles carry a zero-width space ('Microsoft​Edge'): no Edge window was EVER recognised -> `_title`/`_browser_of`.
- the desktop's open_url REPLACES her current tab (ctrl+l) -> every open is a NEW tab: `_open_in_named` (focus an
  existing window first - open_app on a running browser made another window; no second blank tab on a fresh browser;
  ctrl+l + type + Delete (drops inline autocomplete) + Enter; title compared against the new tab's), and the Chrome
  one-step path gets ctrl+t first; with no browser named now, the browser window she is using wins.
- 'cutting edge', 'Chrome extension' switched the browser -> a pick needs a browser context word or the full name.
- ask_user's wait ate the task's clock (answer at minute 9 -> 'Samay khatam') -> waited time added back, not a step.
- 'ERROR' results were not errors (fast-type waited for nothing); a seen page title skips the second wait.
- spoken update came BEFORE the action (a refused open was announced) -> after success only.
- any chat's line answered the PC question; questions back ('kitna time?', 'ek minute') were taken as the choice ->
  `pending_ask(conv)` + `_is_answer` (option number / option word / short reply; questions + filler go to the turn).
- the question note went into a hidden side record; questions / results reached no later call -> note in her chat,
  `_inject` to the call of the CHAT.
VOICE (voice.py)
- two PC updates / a second question within 2 min were dropped as duplicate news (shared wrapper words) -> news marks
  its payload with «...» and only that counts (`_news_words`).
- her answer was taken from words said BEFORE the question was spoken, and from interrupted fragments -> only a turn
  after the question had a turn to be spoken (`_prev_turn_end`), never an interrupted one.
- the rescue could send her ask twice (santosh_kaam's flag set after awaits) -> `_kaam_turn` set the moment the tool
  call arrives; rescue needs a doing word, skips when the voice asked her back, steers a running PC task instead of a
  new brain turn, and says her PC is offline instead of staying silent.
- santosh_kaam with a pending PC question answers it directly (no second brain turn / note).
Tests: test_v0858_pc_flow.py 26; test_v0193 report pin follows the release rule. Wider sweep 400 passed; 2 reds
(test_v067 replay, test_v0442 persona) fail identically on the commit before. NOT VERIFIED on her PC / a real call.

## v0.860.0 R1 THE DESIGN SYSTEM (the Claude-style phone redesign, phase R1)

Owner: "GO R1". `lib/ui/hoola_theme.dart` holds every colour, size, corner, space and movement the redesigned screens
use (plan section 1):
- `HoolaColors` (ThemeExtension) light + dark roles: bg / surface / raised / sunk / line / lineStrong / ink / ink2 / ink3 /
  accent (Hoola violet #5B45E0 / #9C88FF) / pill (primary button) / ok / warn / bad / info + soft backgrounds / code /
  nav / navOn / scrim / shadow. `readablePairs` = 19 text pairs, all >= 4.5:1 in both modes (`hoolaContrast`, tested).
- `HoolaType`: hero 32 Literata, display 22/700, heading 18/600, title 16/600, body 16 / 15, small 13, label 12/500,
  button 16/600, reply 17 Literata 1.6, reply headings 22 / 18 / 16 Literata, code JetBrains Mono; a full TextTheme.
- `HoolaRadius` 8 / 12 / 16 / 18 / 20 / 28 / pill, `HoolaSpace` 4-32 + touch 44 / 48 + gutter 16, `HoolaShadow.float`.
- `HoolaMotion`: page 280 ms, sheet 320, menu 160, fade 200, the house curve + a small spring; `reduced(context)` reads
  the phone's Remove-animations setting and every duration collapses to a 120 ms fade; `HoolaPageTransition`.
- `hoolaTheme(brightness)`: Material 3 theme from the tokens only (buttons = pills, cards = 16 + hairline, inputs = pill
  fields, sheets 28 + drag handle + scrim, menus 18, snackbars, switches, list tiles, page transition).
- `HoolaTheme(appearance:)` wraps a redesigned screen; `Santosh.appearance` / `setAppearance` (system / light / dark,
  default system). The row to change it lands with Settings (R7).
- pubspec `fonts:` declares Schibsted Grotesk / Literata / JetBrains Mono from the bundled files (R0).
- `test/design_rules_test.dart`: contrast, theme build (no style under 12 or over 700) and a RATCHET over lib/ -
  raw `Color(0x..)`, `fontSize` < 12 and `FontWeight.w800/900` per file may only go down (`test/design_baseline.json`:
  189 files, 695 / 680 / 779 today); a new file starts at zero.
- `test/goldens/theme_test.dart`: specimen pictures `20_theme_light` / `21_theme_dark` in the CI hoola-screens set;
  font loaders shared in `test/goldens/golden_fonts.dart`.

Nothing on screen changes yet: today's screens keep Night Glass until R2-R8 move them. Icons: Flutter's own rounded /
outlined Material icons (no new package). NOT VERIFIED until the CI run (Flutter does not run here).

## v0.861.0 R2 THE SHELL (the Claude-style phone redesign, phase R2)

Owner: "GO R2". `lib/ui/shell/hoola_shell.dart` (all from `hoola_theme.dart`):
- `HoolaShell`: Scaffold wrapped in `HoolaTheme(appearance)`, tabs Hoola / Work / Connect / Made switched with a fade,
  body padded above the floating bar, edge-swipe drawer, Talk opened as a slide-up route (reduced motion = fade).
- `HoolaNav`: the floating pill bar (68 high, surface + hairline + float shadow), the selected tab on a `navOn` pill,
  icon cross-fade, Hoola tab = the Hoola mark; Semantics per tab.
- `HoolaHome`: hamburger + New chat, the mark, serif greeting by time of day + her first name, "Santosh is ready. N
  things need you.", quick-start chips (the first = waiting approvals when any) that send as her message; a one-time
  fade + rise (still under reduced motion).
- `HoolaComposer`: + picks files (FilePicker, several) and uploads each at once through `attachChatFile` (the chat
  paperclip's own upload) as removable chips with a spinner / error; the field grows to 6 lines; mic + the black voice
  button (Talk) swap to a violet Send when there is text or a ready file; a failed send puts the words and files back.
- `HoolaDrawer`: serif "Hoola", Recents (chat / call icons, the open chat on a sunk row), All chats, More (Calls sheet,
  What Santosh remembers), avatar -> Settings, New chat pill (`connect(fresh: true)`).
- `_CallPill`: while a call runs, "On a call with Santosh · Open" above the bar.
- The Hoola tab shows the new home until the chat has a message, then the existing chat screen; Work = Today, Connect
  = Connect, Made = artifacts, Settings = the old Main - each inside its own Night Glass frame (`_OldLook`) until
  R3-R7 rebuild it.
- Behind `Santosh.newLook` (pref `new_look`, default off): Main gains "Try the new design" + Appearance (System /
  Light / Dark). `main.dart` Home returns `HoolaShell` when it is on (after the locked-screen and avatar-setup checks).
- CI pictures: 30_new_home / 31_new_drawer / 32_new_work, light and dark.

NOT VERIFIED until the CI run; not seen on a real phone.

## v0.862.0 R3 THE CHAT (owner: "GO R3" on docs/HOOLA_APP_REDESIGN_PLAN.md)

The conversation rebuilt in the new design (R1 tokens, R2 shell), still behind Main > "Try the new design".

- `lib/ui/chat/hoola_chat.dart` `HoolaChat` (the Hoola tab shows it once the chat has a message):
  - her message = quiet bubble on the right (sunk role, 16 sans, corner 20 / 6), her files as small tiles above it;
  - Santosh's reply = no bubble, full width, Literata 17 (`hoola_md.dart`); a reply that arrives while the chat is
    open appears at reading speed (34 ms a word, 10 s cap) unless it already streamed in; reduce motion = at once;
  - working mark: the Hoola mark breathing + the real step (`currentStep`) + a clock, until the first word;
  - Stop: the composer's voice buttons become Stop while Santosh works (`stopWork`);
  - steps: the running step live, then one line "Used N steps ›" -> Steps sheet (timeline, an icon per kind of step
    read from its words - `stepIcon` - until R3s sends the kind);
  - thinking: "Thinking · 4s" live, "Thought for 6s ›" after, opens to the text;
  - under the newest reply: Copy · Read aloud · Share (text file via `Native.shareFile`) · Good · Not right (the
    console's `/feedback` route, new `Api.replyFeedback` + `Santosh.rateReply`, lit while chosen) · Ask again;
  - long-press: Copy · Quote in my reply (into the composer) · Edit (hers) · Ask again (newest reply) · Read aloud ·
    Select text; day heads Today / Yesterday / 12 Nov; "Show earlier messages"; a round newest button with the
    count of what arrived while scrolled up; "Reconnecting…" under the top bar while the stream is down.
  - cards (approvals, drafts, payments, plans ...) are still `feedCard` from the old chat, in a dark frame, until R4.
- `lib/ui/chat/hoola_md.dart` `HoolaMd` + `HoolaCodeBlock`: the same parser (`mdBlocks` / `mdInline`, which gained
  an optional `codeStyle`), new drawing: headings 22 / 18 / 16 serif 600, inline code JetBrains Mono on the code
  role, code block = header (language, Copy, Expand to a full-screen sheet) + body that scrolls sideways, tables in
  a bordered box with a tinted header that scrolls sideways, quotes with a rule, the newest 3 plain words of a
  streaming block drawn lighter (the soft tail; never when a mark is open).
- `HoolaComposer` takes the chat's controller / focus and `working` + `onStop`.
- CI pictures 33_new_chat / 34_new_chat_working / 35_new_chat_writing, light and dark.

NOT built in R3 (next): R3s server step `kind` + one turn-result record, the 15 s stall watch, images inside
replies, the warm artifact WebView. NOT VERIFIED on a real phone.

## v0.863.0 R3s - step kinds + one turn result (owner: "GO R3s" on docs/HOOLA_APP_REDESIGN_PLAN.md)

The server half of R3. Old phones ignore every new field.

- `server/app/agent/stepkind.py`: `classify(tool, label)` -> (kind, housekeeping); kinds search / read / write / edit /
  web / run / agent / skill / question / card / memory / other, from the tool name first, the label second.
  Housekeeping = Hoola's own process (tool_search, kaam_plan, the answer check `jaanch`, memory lookups, skill reads).
  `enrich()` is called ONCE in `events.bus.publish` for kind "step" (setdefault: a publisher's own kind wins), so the
  main loop, crews, research and the answer check all carry it without being touched.
- `server/app/turnresult.py`: one record per chat, from stores that already exist (nothing new written):
  status of 8 (queued / working / needs_you / done / partial / stuck / stopped / failed, "" = nothing asked yet or an
  ask with no answer and nothing running - it never guesses), needs_you, one line (the reply's first sentence, the
  card's title, the job's title, or "Partly done: <what is left>"), made (pages / files / pictures / sites published
  since her newest message, each once, at most 4), at. Order of truth: waiting card -> waiting job -> turn lock /
  running inbox / running job -> queued inbox -> failed inbox -> task-log outcome -> answered.
  Readers: `/api/conversations` rows (first 25, `chats.RESULT_ROWS`, cheap form without the card scan), NEW
  GET /api/conversations/{id}/result (full form), the reply notification's FCM data (`status`, `needs_you`).
- Phone (new look only): the steps line hides housekeeping steps and draws the server's kind icon (label fallback for
  older servers); housekeeping never takes over the working line; the drawer shows a spinner (working / queued), an
  amber dot (needs you) or a red mark (did not finish / stuck) beside a chat - a finished chat stays quiet.
- `server/tests/test_v0863_r3s.py` (9).

NOT done here: Work (R6) and the chat card read the record when those screens are rebuilt. NOT VERIFIED live.

## v0.864.0 R4 THE CARDS (owner: "GO R4" on docs/HOOLA_APP_REDESIGN_PLAN.md)

- `lib/ui/chat/hoola_card.dart` (new look only, the chat's default branch asks it first):
  - `HoolaCard` = the one shell: label line (desk + when), tile, title, status (dot + plain words: Needs your yes /
    Working / Done / Did not work / quiet), body, buttons docked at the bottom on a hairline; surface + line + radius 18;
    a card waiting for her gets the stronger edge. Parts: `HCFact` (label left, value on the right edge), `HCAmount`
    (the amount as the hero line), `HCNote` (safety band), `hcMain` (filled pill) / `hcQuiet` (text button).
  - `HCApproval` (kind `bazar`, the confirm card): payee, items, amount, PIN / demo / voice notes; Not now = reject;
    Yes = for a card that moves no money her tap is the yes (`decideBazar` approve - the card IS the confirm card);
    for money it opens the existing approval sheet (deliberate slide, fingerprint when the phone has a key) - the
    server's 428 still guards it. After the answer: the result message and the open button (UPI / link).
  - `HCFile` (pc_file: made PDF / from her PC, Open, Share link), `HCPage` (artifact: building bar / ready + version /
    not made with the reason, Open), `HCAny` (the v0.555 default card's reading of a payload, new drawing).
  - Every other kind keeps its old card in the dark frame (desk cards move in R8).
- Approval notifications (`server/app/push.py` `quick_yes`): a pending `bazar_approval` whose payload says
  money False, with no amount / payment method / PIN / demo / tier 3, gets `yes_card` in the FCM data; anything unsure
  gets nothing. Phone: `SantoshPush` passes it to `Notify.message`, which adds "Not now" / "Yes, do it" actions
  (`setAuthenticationRequired` on Android 12+ = the phone must be unlocked) -> NEW `CardActionReceiver` (broadcast,
  goAsync) POSTs the same `/api/bazar/approvals/{id}` route with her key; the notification then says Done / Not done,
  or "Open Hoola to approve this with your fingerprint" on a 428, or "Could not answer from here" on anything else.
  Manifest gains the receiver (exported false).
- Tests: `server/tests/test_v0864_r4_cards.py` (3); CI pictures 36_new_cards / 37_new_made light + dark.

NOT VERIFIED: the notification buttons on a real phone (Kotlin compiles on CI only); no phone has tapped one yet.

## v0.865.0 R5 TALK (owner: "GO R5" on docs/HOOLA_APP_REDESIGN_PLAN.md)

- `lib/ui/talk/hoola_talk.dart` `HoolaTalk`: the live call in the new design, on the SAME `CallSession`
  (app.voiceCall) - no engine change; leaving the screen never ends the call (screenOpen / voiceMode / autoCall kept).
  - top: close (down chevron; the call keeps running), the avatar's name, "Live" (or "Real voice") + the call clock.
  - the orb (`_OrbPainter`): disc in the accent (ink while she talks), grows with `inLevel` while she talks and with
    `outLevel` while he speaks, breathes when idle, a turning arc while working / connecting; reduce motion = no
    breathing / no turning, the level still shows. Tap while he speaks = `cutSpeech`.
  - the last turn: her words (right, small) and his (serif); the status in plain words (Listening / Working on it /
    Speaking · tap the circle to stop / hold lines / link wobble note).
  - cards that came during the call: drawn with the R4 cards (`hoolaCardFor`), other kinds in the old dark frame;
    chips to switch, remove, Back to call.
  - controls: Show (photo / PDF / file into the call) · Type (writes into the call, `sendText`) · Mute (or Come back
    while on hold) · End (red); before a call one "Start the call" pill.
  - kept: lock-issue and hold banners, background tasks line, file note, browser thumb, page pill, "Recognised by voice".
- `lib/ui/shell/hoola_shell.dart`: the voice button opens it when realtime voice is on; the turn-by-turn
  `VoiceScreen` stays in the old frame until it is rebuilt.
- CI pictures 38_new_talk / 39_new_talk_call, light and dark.

NOT VERIFIED on a real call (the pictures set the call's fields; no live audio in a test).


## v0.866.0 R6 WORK + MADE + CONNECT (owner: "GO R6"; docs/HOOLA_APP_REDESIGN_PLAN.md R6)

The new shell's three other tabs are now in the new design. All three live in ONE new file,
`lib/ui/shell/hoola_tabs.dart`, and read APIs that already exist. Nothing on the server changed.

**Shared parts** (they will be reused in R7 / R8):
- `HoolaTabHeader` (big title + sub line), `HoolaSection` (label + count + dot).
- `HoolaRow` (tile, title, one line, right side, min 60 px, semantics label) and `HoolaGroup` (rows on one card with hairlines).
- `HoolaSearch` (the pill search field), `HoolaChips` (filter chips), `HoolaEmpty` (empty / failed + Try again).
- `hoolaWhen` gives "Today 14:05" / "Yesterday 09:12" / "12 Nov 18:40".

**Work** (`HoolaWork`):
- **Needs you / In progress / Done this week**, built by the pure `workSections(kaam, chatList)` from:
  - GET /api/kaam/list;
  - every chat whose R3s turn result (`chatList[].result`) is needs_you / working / queued.
- A chat already in the kaam list is never shown twice.
- A stuck job reads "Stuck - no progress for a while"; a stuck task reads "Did not finish".
- State words come from the phone in English (`workStateWord`). The server's Hinglish `say` is never shown.
- A tap opens that chat on the Hoola tab.
- It refreshes quietly every 30 s while open, and on pull.
- "Your AI team" (EmployeesScreen) and "Today" (the old TodayScreen) open in their old frame until R7 / R8.

**Made** (`HoolaMade`):
- `madeItems(pages, creations)` merges two lists, newest first:
  - pages from GET /api/artifacts;
  - Create studio items from GET /api/create/items (new `Api.createItems`, `createItemUrl`, `createItemBytes`). The kinds are picture / audio / video / document / other.
- Search box plus type chips (only the types she has).
- A page opens full screen (`openArtifact`). A picture opens large in a pinch-zoom viewer (Image.network with the key header). Anything else is downloaded to the temp folder and handed to her phone's share sheet.
- It refreshes on a live artifact event.

**Connect** (`HoolaConnect`):
- `connectSections(catalog, apps)` builds three groups, each app listed once:
  - **Connected**: apps with status ready;
  - **Add a connection**: needs_link, with a Connect button using the same `app.linkApp`;
  - **Ready to use**: built in, first 6 plus "Show all".
- Press-and-hold on a connected app asks first (a sheet: Remove / Keep it), then `bazarUnlink`. A no-login app (IndiaMART) has nothing to remove.
- "All plugins and settings" opens the old BazarScreen. Spend limits, address and shops stay there until R7.

**Shell:** the tabs Work / Connect / Made are now these screens. TodayScreen / BazarScreen / ArtifactsScreen are no longer tabs; they are reached from the rows above.

**Tests:**
- `test/hoola_tabs_test.dart` (4): sections, no duplicates, newest first, kinds.
- Golden pictures 40 / 41 / 42 (work / connect / made, light + dark), seeded through `HoolaTabsDebug` because the tests have no server.
- The design ratchet is unchanged (no raw colours, no small text, no heavy weights in the new file).

**NOT VERIFIED** on a real phone against the live server:
- the logos (the pictures show the letter fallback);
- the share-out of a song or script;
- picture loading with the key header.


## v0.867.0 R7 SETTINGS + YOUR AI TEAM (owner: "GO R7"; docs/HOOLA_APP_REDESIGN_PLAN.md R7)

The old Main / Profile page (1,676 lines, 129 rows) is split in two, both in the new design.

**Settings** (`lib/ui/shell/hoola_settings.dart`, `HoolaSettings`) opens from the drawer's avatar. It starts with a header card (her avatar's face, name, account email) and then six groups:
- **You and Hoola:** Your AI team, your name / city / morning briefing (`_ProfileEditor`, same `saveProfile` body as before), the avatar's look (LookPickerScreen), My rules, Hoola Network.
- **Memory:** About me, What Hoola remembers (`_FactsScreen`: pinned and remembered, tap = pin, delete asks first), Learned tasks, What Hoola has learned.
- **Look and voice:** new design switch, Appearance (Auto / Light / Dark), Language (sheet), answer by voice, the call voice (sheet, only when realtime voices exist), call voice engine, Voice ID, How you speak, Call quality.
- **Phone and notifications:** work in the background, plus the battery / keep-alive / alarms / calendar fix rows only when needed; "Hey Santosh"; Hoola on the phone; Talk from outside; Hoola Screen.
- **Privacy and safety:** ID Locker, fingerprint approval.
- **Account:** AI spend (this month's rupees), each Google account (Remove asks first), Connect your systems, WhatsApp sending mode, Log out (asks first).

**Your AI team** (`HoolaTeam`) is one searchable list. Its entries (`hoola_team_list.dart`) were GENERATED from the old page's own rows by parsing each ListTile (icon, title without the avatar-name prefix, line, and the screen it opens). That gives 83 desks + 26 tools in 12 groups: Hire and manage, Business and sales, Finance and accounts, Customer service, Software and IT, Logistics and travel, Property and construction, Legal and compliance, Education and research, Hospitality and events, Media and creative, Tools and apps. Search matches every word of the ask against title + line + group (`teamSections`, pure and tested).

Desks and old pages open in their old frame (`hoolaOpenOld`) until R8. New screens open through `hoolaOpenNew`.

**Shell changes:** the drawer avatar opens Settings (was the old ProfileScreen), and Work > Your AI team opens HoolaTeam.

**Tests:** `test/hoola_settings_test.dart` (3):
- every screen the old Main page opened (>100) is in Settings or the team list, exactly once;
- every inline setting it held (22 call names: saveProfile, briefing, language, voice, look, background, battery / alarms / calendar, keep-alive, wake word on / off, Google disconnect, pin / forget, sign out, WhatsApp mode, new design, appearance, rules) is in Settings;
- team search keeps group order and matches every word.

Golden pictures 43 / 44 (settings / team, light + dark). The design ratchet is unchanged.

**NOT VERIFIED on a real phone:** the wake-word switch and background status (Native calls), the look picker round trip, Google account removal. The ~100 desks keep their old look until R8; some titles are still Hinglish (R8 English pass).


## v0.868.0 R8 DESKS wave 1 (owner: "GO R8"; docs/HOOLA_APP_REDESIGN_PLAN.md R8)

There are 149 desk screens (~105,000 lines). Rewriting them one by one is the plan's waves, so this release does three things that move all of them at once, plus wave 1.

**1. THE DESK KIT** (`lib/ui/desk/desk_kit.dart`). `DeskScaffold(title, tabs, tab, onTab, loading, busy, onRefresh, body, actions, fab)` gives every desk:
- a header with Refresh;
- pill tabs in English (`deskWord`: Aaj -> Today, Niyam -> Rules, Jaanch -> Check, ...);
- a thin busy line;
- a first load that turns into "Still loading" + Try again after 12 s. Most desks only snacked a failed load and spun forever;
- pull to refresh, and the desk's own main button.

It draws in the new design's dark roles while the new design is on, and keeps the Night Glass chips when it is off.

**2. WAVE 1.** The 30 desks that all drew the same chip-row layout now stand in DeskScaffold:
- **Moved by a script that refuses anything it does not recognise (26):** archassist, banquet, compliance, contracts, cosec, courier, dpo, editdesk, eventplan, filmdesk, fleet, graphic, influencer, interior, kitab, notary, patrakar, photoassist, pidesk, podcast, rentdesk, shaadi, society, tourguide, vakil, wapsi.
- **Moved by hand (4):** docwriter (its New doc button), frontoffice, seva, sitesup.

Their Hinglish tab labels are now English. Four inner detail pages (ArchProjectPage, ContractPage, CosecEntityPage, ShaadiWeddingPage) still draw their own chip row: wave 2, named in the test.

**3. THE DESK FRAME (every old screen).** `glass.dart` NightGlass.flat is a ValueNotifier set from main.dart whenever the new design is on (guarded so it never flips mid-build; the root MaterialApp rebuilds on it). While it is on:
- Aurora is a flat page (its controller is created in initState and held still - creating it first in dispose crashed);
- Glass is a flat card on the surface colour with a hairline and corner <= 16, with no blur and no shadow;
- GradientButton is the new solid pill;
- GlassButton is an outline pill;
- Pill and Caption use the new chip type;
- `santoshTheme()` = `_deskTheme`: new dark bg / surface, the interface sans, filled inputs, dialogs / sheets / snack / dividers.

So all ~150 old screens lose the drifting aurora and the blur at once (the plan's R9 item), and look of a piece with the new tabs. With the new design off, Night Glass is unchanged (tested). GlassButton labels now ellipsize instead of overflowing on a narrow phone (found by the new picture).

**4. English names in Your AI team.** "Theka sahayak (contractor)" -> "Contractor's assistant", Thok / Niryat / Bima / Darzi / Chai / Shikayat / Dosti / Godown / Prayogshala and others likewise.

**Tests:**
- `test/desk_kit_test.dart` (4): wave 1 shape + English tabs + no leftover chip rows outside the named inner pages; deskWord; tabs / busy / Still loading -> Try again / refresh; flat Glass + Aurora have no blur when on and keep it when off.
- Pictures 45 / 46: a sample desk built from the same old parts, in the new and the old look.

**NOT VERIFIED on a real phone:** the flat frame on the remaining ~119 desks (each still has its own layout inside), and their colours. Inside the cards the desks still use Night Glass text colours, which read on the new dark surface. Light appearance does not reach the old desks; they stay dark until their wave rebuilds them on HoolaColors.


## v0.869.0 R8 DESKS wave 2 (owner: "GO R8 WAVE 2"; docs/HOOLA_APP_REDESIGN_PLAN.md R8)

The second desk family moves onto DeskScaffold. These are the 25 desks drawn as Aurora + RefreshIndicator + ListView, with a Wrap of chips from `const [(0, 'Aaj'), ...]`, a busy bar, an `if (_d == null) spinner else [..][_tab]` line and a footer note.

**Moved by a second script (19)**, which keeps the content above / below the tab content and the footer note inside the desk's list, and refuses what it does not recognise: after-sales, call centre, customs, cyber, school office (daftar), DevOps, Hoola Code (devsahayak), drivers, feedback, franchise, IT helpdesk, IT admin, legal research, logistics, QA, community (samudaay), curriculum (shiksha), contractor (theka), wholesale (thok), warehouse, and the inner pages tutor (guru) and research (shodh), which have no refresh.

**By hand (8):**
- insurance (the stats header + birthdays above the tabs) and export (niryat; per-tab blocks, PI button). The script's splitter broke on a `...[` spread inside an `if`, so these two were restored from the backup and rewritten.
- NOC (its Add an alarm button only on Today), artist manager, product manager.
- The 4 inner detail pages wave 1 left: company (cosec), contract, architecture project (by the wave-1 script), wedding (by hand).

**Kit:** `onRefresh` is optional. With null there is no Refresh button and no pull, for inner pages with nothing to reload.

**English:** every desk header is now English, with no "Sahayak" left: Contractor's assistant, Wholesale assistant, Export assistant, Warehouse, Journalist, Wedding planner and so on. The avatar-name prefix on headers is dropped.

**Totals:** 57 desks + 4 inner pages = 61 DeskScaffold frames. No screen still draws either old chip row (`ChoiceChip(label: Text(tabs[i]))`, `for (final (i, t) in const [(0, ...`, `tabs.indexed`) - held by `test/desk_kit_test.dart` (5 tests now, incl. no "sahayak" titles and the no-refresh inner page).

**Left for later waves:** the ~90 old screens with other layouts (DefaultTabController / TabBar desks such as deal, darzi, kalam, gst, telecall, office; single-page desks; the Notebook) - they already draw flat through the desk frame.

**NOT VERIFIED on a real phone.**


## v0.870.0 R8 DESKS wave 3 - the swipe-tab desks (owner: "GO R8 WAVE 3")

The 21 desks that drew their own `DefaultTabController` + `TabBar` (Buy and sell, Tailor, Mobile shop, Content writer,
GST, Telecaller, Office manager, Tea stall, Financial analyst, Payroll officer, Brand designer, Performance marketer,
Hoola Network, Friends, Consents / papers / outside agents, AI employee, Typist and translator, App designer, Website,
Hoola Business) now stand in `DeskTabsScaffold` (lib/ui/desk/desk_kit.dart): header (English title, the desk's own
actions, Refresh when the desk has a reload), `DeskTabBar` (pill tabs in the new design, underline tabs in Night Glass,
labels through `deskWord`), pages you still swipe between (same TabBarView), one pull over every page for list desks
(`pullAll`), and the first-load state `DeskLoading` (spinner -> after 12 s "Still loading" + Try again; a desk error =
"Could not load" + the error + Try again). The Notebook keeps its own TabController and uses `DeskTabBar(controller:)`.
DeskScaffold's loading now uses the same `DeskLoading`. Converted by a script that parses the build by bracket matching
and refuses what it does not recognise (2 by hand: Employee, Hoola Network). Titles: "${app.aName} ·" prefixes
dropped, "sahayak" names replaced (Tailor, GST, Tea stall). New deskWord entries: Galla -> Cash box, Kharcha ->
Spending, Dhoondhiye -> Find. Tests: desk_kit_test (no TabBar / DefaultTabController outside the kit, >= 20 desks,
English titles; widget test of the frame: pill tabs, tap + swipe, error + Try again, no blur); CI picture
47_desk_tabs. NOT VERIFIED on a real phone. Still to move: single-page desks and other layouts (~70 screens).


## v0.871.0 R8 DESKS wave 4 - one-page desks and detail pages (owner: "GO R8 WAVE 4")

New `DeskPage` in lib/ui/desk/desk_kit.dart: the frame of a one-page desk or screen - English header (title, the
screen's own actions, Refresh when it can reload), the first-load / error state `DeskLoading` (spinner -> after 12 s
"Still loading" + Try again; an error = "Could not load" + the reason + Try again), and the page (it keeps its own pull
to refresh). 181 frames in 122 files moved onto it by a script that parses each Scaffold by bracket matching and
refuses anything it does not recognise (other Scaffold arguments such as bottomNavigationBar / extendBodyBehindAppBar,
non-standard backgrounds, AppBars with bottom / leading options, multi-argument titles): the one-page desks (Google
Drive / Sheets / Forms / Slides / Photos, Calendar, Email, YouTube, Employees desks, game desk pages, CAD /
architecture desks, studios, ID locker, memory, call quality, voice ...) and the detail pages inside the desks moved in
waves 1-3 (orders, bookings, visits, matters, tickets, shipments ...). A loading check `X == null` stays inside the page
as `X == null ? SizedBox.shrink() : page` so Dart still knows the data is there. Titles: "band na ho" -> "Keep ...
running", "Light ka hisaab" -> "Power budget", "Kaam" -> "Work", "Google ads" -> "Google Ads"; Public APIs by hand.
The frozen PC screens (pc_screen.dart, hoola_pc_screen.dart) untouched (test). Left (~23, own layouts on purpose or
for a later pass): screens with a bottom bar (appreview, kalam write, propagent, motiondesk), full-bleed / black
viewers (browser_live, chat_attach, photo_card, hoola_media, video_editor, brand preview), bazar / shopping (image
headers), avatar setup, employee inbox, the notebook / app designer / site detail pages with their own app bars.
Tests: desk_kit_test (>= 120 files / 175 frames, English titles, PC screens untouched; widget test of the frame); CI
picture 48_desk_page. NOT VERIFIED on a real phone.


## v0.872.0 R9 PROOF + POLISH (owner: "GO R9")

The plan's last phase. What was proven, what was fixed, and what still needs a real phone.

- PICTURES PASS: the screen-picture suite (test/goldens/screens_test.dart) had 32 of its tests fail on every run with
  "A Timer is still pending". Two causes: (1) a REAL leak - `Santosh.dispose()` never cancelled `_healTimer` (the 90 s
  self-check), `_replayGuard`, `_typingGuard` or `_workHide`; it now does; (2) the tests never disposed the app and
  stopped 5 s before the shell's 20 s update-offer delay. All 47 pass now.
- ACCESSIBILITY GATE: 22 new-design screens (home, work, chat, cards, the three tabs, settings, team, desk frames,
  light + dark) run Flutter's `androidTapTargetGuideline` (48 dp) and `labeledTapTargetGuideline` (every tap target has
  a name TalkBack can say). Found and fixed: `HoolaSpace.touch` was 44 (the iOS figure) -> 48; pill tabs and filter
  chips (DeskScaffold, DeskTabBar, HoolaChips) now take the tap on the full 48 dp row while the pill still draws 36;
  the chat's "Thought for" / "Used N steps" rows, the composer field, the call pill, the quick starts and GlassButton in
  the new design reach 48. `textContrastGuideline` was tried and dropped: it samples pixels and, with real
  anti-aliased fonts, read the tab bar's border and a fading-in greeting as the text colour (near-black ink measured
  #9F9F9E). Contrast stays proven on the colours themselves (design_rules_test: every text pair >= 4.5:1).
- 200 % TEXT: pictures 50-54 (home, chat, work, settings, a desk) at the largest Android font size; any overflow fails.
  Found: the tab bar had a fixed 68 px height and overflowed 1-2 px at normal size, 32 px at 200 %; it now grows (labels
  capped at 1.6x so four tabs fit). Quick starts wrap to two lines instead of being cut.
- CI: app-screens.yml runs the desk / tabs / settings unit tests too, and a new step FAILS the job when any picture
  test fails (pictures still upload).
- glass.dart: NOT deleted - ~220 old screens still build on its widgets (drawn flat by the R8 desk frame). A ratchet in
  design_rules_test keeps the number of files that use it at or below 222 and forbids blur anywhere outside it.
- NOT DONE, said plainly: 60 fps on a budget phone was not measured (no phone here; the blur and moving aurora are
  already gone in the new design); TalkBack was not walked by hand on a phone; sounds were not added (her decision);
  ~23 special-layout screens (bottom bars, full-screen viewers, black editors) keep their own frame.


## v0.859.0 DESKTOP AI D0 + D1 + D2 + D4 (owner: "GO D0 D1 D2 D4" on docs/DESKTOP_AI_PLAN.md)

- **D0 THE PC CARD** (`server/app/quality/pccard_tasks.py`, `pccard.py`, `pccard_api.py`): 40 Windows tasks in her world
  (apps 6, browser 10, office 5 - skippable without Office, settings 6, files 5, web forms 3, shopping 5 that MUST stop at
  the approval card), each with a CODE check (title / windows / page / answer / status, all / any). Runs through the real
  operator (`start(..., replace=False)`, a busy PC is never taken over) only on a PC whose name contains "test" or with
  `confirm_not_her_pc`; an approval stop is checked then `stop()`ed - nothing is bought; questions answered from the
  task's own `answer` at most twice; one run at a time; results saved like the other cards (success %, median seconds /
  steps, false-done, asks, per group). Owner routes GET /api/quality/pccard, POST .../run, POST .../stop. Rupees not
  measured (no per-task meter); file checks read the screen, not the disk (a desktop file check is D3).
- **D1 CLAUDE'S OWN COMPUTER TOOLSET** (`pc/operator.py`): on the Claude PC brain the pixel lane is
  `computer_toolset_20260801` (Sonnet / Opus 5.5 are trained on it); the clashing custom tools (click, type, key, scroll,
  drag, screenshot, wait) are dropped and Hoola's exact tools ride beside it. Members map onto the desktop's existing
  actions (`_from_native`; xdotool key names -> desktop names; triple click = double + one; key repeat; scroll up/down)
  - no exe change; middle click / hold key / mouse down-up / held modifiers are refused with a reason. ZOOM = a
  full-resolution capture cropped on the server to the region and scaled to the usual size, then the model's
  screenshot scale is restored (a full-size capture changes the desktop's click scale). Results of toolset calls carry
  `toolset_name`. If the API refuses the toolset (400 before any toolset call), this process falls back to the custom
  tools and says so in the log. Qwen keeps the custom tools. Switch `pc_native_tools`.
- **D2 PLAN + STAGE CHECKS**: `pc_plan_model` (Sonnet) splits a job into 2-7 stages with a visible "done when", a stage
  that ASKS her for any open choice, and an approval stage before any send / order / payment; the plan rides the first
  message; `stage_done(stage, evidence)` is checked on a fresh screenshot + page text by `pc_check_model` (Haiku); not
  confirmed = "NOT YET" with the reason, twice = move on (never a loop); stage progress on the live card and the call.
  Short jobs get no plan. Switch `pc_plan`.
- **D4 VERIFY BEFORE DONE**: `done(success=true)` is checked on the screen against her ask (+ the last stage); not ok =
  "NOT VERIFIED: <what is missing>" back to the model (max 2), then accepted; a checker that cannot run never blocks.
  Switch `pc_verify`.
- Tests: `test_v0859_desktop_ai.py` 8, `test_v0859_pc_card.py` 21; conftest pins PC_PLAN / PC_VERIFY / PC_NATIVE_TOOLS
  off for the older PC suites (their fake model client would get the planner / checker calls). PC sweep 187 passed,
  1 red pre-existing (test_v067 replay).
- NOT VERIFIED: no live call with the toolset (the VPS anthropic SDK version and API version header may matter - the
  fallback covers a refusal), no real PC run, no card numbers yet. Cost: + one planner call per job, + one Haiku check
  per stage / done.


## v0.860.0 PC KA HISAAB - every PC task explains itself in the log (fix 1 of the one-by-one PC clean-up)

Owner, after her v0.859 pizza test: "VERY BAD WORKFLOW AND PERFORMANCE - EVERY THING IS MESSY - LETS START WITH
LITTLE FIXES ONE BY ONE". Her grep (11:08-11:12) showed one run reaching step 69 and then two more runs each starting
again at step 0 within 3 minutes - but no line said WHY a task started, was replaced, or ended, and the planner /
checker of v0.859 wrote nothing on success. Nothing can be fixed one by one without seeing it, so fix 1 is the trail:

- `pc task start <id> chat=... pc=... brain=... browser=<name>(said|remembered|default) budget=N steps/M min | task`
- `pc task <old> REPLACED at step N by a new task (old chat, new chat) | old | new` (warning)
- `pc_do new task (chat, fresh=, running elsewhere=, running here=)` / `pc_do steered into running <id>`
- `pc plan <id> N stages: a > b > c`, `pc check <id> ok=True|False | what | why`
- `pc task <id> asks her: ... | options`, `got her answer: ...`, `told (her words|Hoola, from chat ...)`
- `pc task end <id> status=... steps=N Ns stage=k/n asks=yes|no | reason or summary`

No behaviour changed. Files: `server/app/pc/operator.py`, `server/app/agent/pc_tools.py` (frozen-PC exception
recorded). Tests: `test_v0860_pc_log.py` (2) + the PC suites (104) green.
Read a run with: pm2 logs santosh --lines 2000 --nostream | grep -E "pc task|pc_do|pc plan|pc check" | tail -60


## v0.861.0 PC EK BAAR - Hoola stops interrupting a running PC task (fix 2 of the one-by-one PC clean-up)

Her v0.860 log of the biryani run (11:29-11:34): no task was replaced and Chrome was used, but the chat brain called
pc_do again every 15-20 s while the task ran - 'Continue the running task...', 'Step 3: ...', 'The Chrome tab is now
on...', 'Read out exactly what is in the cart', 'Status check only', 'Do not repeat earlier steps' - and each call
put a new note into the task, which stopped and re-read it before its next step. Cause: pc_do waits 12 s and returns
'still working', a steering call returned at once, so the model kept calling it.

Fix (`agent/pc_tools.py`): on a running task in the same chat, Hoola's words are passed in ONCE per ask of hers
(`santosh.ASK_NOW` stored as `Op.hoola_key`; a round with no ask of hers = at most once a minute, `Op.hoola_at`); a
repeat is logged `pc_do repeat ... not passed in`. The steering call now waits up to 30 s (or until the task ends)
and its answer says plainly that the task posts its own result and pc_do must not be called again to check or repeat
steps; the start answer says the same. Her own new words (a new ask) still go straight in. Tests:
`test_v0861_pc_steer_once.py` (2) + the PC suites (75) green.

Still open from the same log (next fixes): one job became 3 separate tasks (cart / address / pay), and 'Cash on
Delivery not available' ended the task as partial instead of asking her how to pay.


## v0.862.0 PC CHROME HI - never Edge first (fix 3 of the one-by-one PC clean-up)

Her report before the next test: "1) every time it first opens Edge, then understands the task needs Chrome; 2) no
real-time conversation, just a late reply; 3) every process is very slow".

1) ROOT CAUSE, read in code (operator open_url + desktop control.open_url): on her PC open_url went through
`_open_in_named` only when Chrome was not already seen; and when that path failed (a cold Chrome taking more than the
6 s it was given to come forward) and her browser was only 'remembered' / 'default', it FELL BACK to the desktop's own
open_url. That one opens in the browser it found running (tasklist, cached 30 s) and, with none, calls
os.startfile = Windows' DEFAULT browser = Edge. Fix: on her PC every site goes through `_open_in_named` (focus her
browser / new tab / address bar), there is no fallback, a cold browser gets 15 s, and the error tells the model to
bring her browser forward and never to use another browser or another way. Hoola's own PC keeps the desktop path.
The v0.858 test that pinned the fallback is rewritten to the new rule.

3) Her v0.859 log split each turn: the model's think 1.5-3.5 s, the actions after it 1-11 s - the time is in the
actions on her PC, not the model. Each action now logs `pc act <task> <name> <seconds>` so the next log names the
slow one.

2) Not changed here beyond the steering wait (back to pc_wait_seconds 12 s, was 30 s in v0.861, which made a
follow-up's reply later). Which surface she means (chat vs call) is asked.


## v0.863.0 PC SAATH (fix 4 of the one-by-one PC clean-up)

Her 13:11-13:19 log after v0.862 ("IT FORGOT THE LAST JOB ... OPENS NEW TAB ... SUDDENLY IT OPENS THE HOOLA OWN PC ...
NO CONSISTANCY, NO MEMORY ... VERY DELAYED REPLY"). Three root causes, each fixed:

1. HOOLA'S OWN PC AFTER HER TASK ENDED: v0.858 `where.release` drops the 45-minute "work is running on her PC" lock when
   a task ends; only the 15-minute follow-up place stays, and only for messages of a few words. "Pizza cancel karo, KFC
   chicken order karo" (or a call's longer reading) lost the place, so the chat brain was free to pick Hoola's PC / its own
   browser. Now `operator.HER_PC_AT[tenant]` is stamped when a task on HER PC starts and ends, `her_pc_recent` = 45 min,
   per person (any chat, call or side record). `pick`: hoola_pc_do refused unless she names Hoola's PC in this message;
   computer_operator / browse_web for an order on her account site refused with "use pc_do" (no question); pc_do allowed
   for a site / order task.
2. A SECOND SWIGGY TAB: `_open_in_named` always pressed ctrl+t. Now the site's own word (`_site_word`: swiggy, amazon) is
   matched against the front tab, then her tabs (`tabs` + `switch_tab`); the home page of an already-open site is NOT
   reopened (her cart / login stay) - the answer says the tab is already open and in front; a deeper link opens in that
   same tab through the address bar; a new site still gets a new tab.
3. SLOW: `pc act` times showed page_text 10.8 s on Swiggy (the desktop walks the whole UIA tree), wait_for 23 s (it polls
   page_text), open_url 15 s (8 s title wait + a page_text digest). The digest after every open is gone; page_text and
   wait_for say in their own descriptions that they are slow on big shopping sites and to use the screenshot /
   page_elements / wait 2 there.

Tests: `test_v0863_pc_saath.py` (6); `test_v0185_pc_browser.py` (no digest) and `test_v0861_pc_steer_once.py` (a site not
already open) updated. NOT VERIFIED on her PC. Not done yet: the 64-step task that scrolled the Swiggy home page instead of
searching (stage 0/0 = no plan for it), and a payment option that is unavailable still ends the task instead of asking her.


## v0.864.0 PC MANAGER (the root cause of "no single PC task is smooth")

Owner, 12 Nov: "NO SINGLE TASK IS SMOOTHLY PERFORMED IN PC ... 20 DAYS AGO EVERYTHING WAS ABSOLUTELY PERFECT ... FIND
ROOT CAUSE", then "put the manager back on Sonnet with its PC rules".

ROOT CAUSE (measured on the code, not guessed): `server/app/pc/operator.py` was byte-identical from 5 Nov to 10 Nov
(1,754 lines) and `agent/pc_tools.py` from 30 Oct to 10 Nov, so the PC code did not cause the drop. Two things around
it did:
1. v0.631 SAB HAIKU (6 Nov): `claude_one_model` = Haiku rewrites EVERY Claude call at the SDK door. The PC loop had no
   bypass until v0.851 (12 Nov), so from 6 Nov the screen reader / clicker was Haiku (or GLM-Flash through the GLM door
   when it was on). The chat turn that RUNS the PC job is still Haiku.
2. v0.732 parity Phase 2/3 (~9-10 Nov): a chat turn gets the small fixed prompt - ONE line about PCs ("her PC only when
   she asks") instead of the ~40 lines of PC rules in prompts.py - and ~22 core tools, pc_do not among them.
Her logs match a weak manager without rules: one order split into 3 PC tasks, steering every 15-20 s ("Step 3...",
"Report the screen"), the job forgotten on a follow-up, the KFC order sent to Hoola's own PC. On 12 Nov the PC code
then grew 108 KB -> 187 KB in one day (v0.836-v0.863: planner, checker, native toolset, Qwen default, steering,
ask_user, team) with nothing walked on a real PC, which added waits and failure points on top.

FIX: NEW `agent/pc_manager.py`: `wanted()` (her place pc / a PC job running or just run in this chat / the pc family
admitted / her PC used in the last 45 min and her words about a site, an order or the computer; never when she named
Hoola's PC, her phone or the server) and `RULES` (places never mix, ONE job = ONE pc_do task with the whole goal and the
stop point, her new words into the running task once and never a check / re-push, a blocker = tell her the reason and
ask, continue from the open tab / cart, money = her tap, say where it runs). `santosh` turn setup marks `pc_turn`,
admits the pc family and appends RULES to the system prompt (small and full); `_turn_model` runs that turn on
`pc_manager_model` (Sonnet) with usage.ONE_MODEL_BYPASS + glmdoor.CLAUDE_ONLY set around its model calls only (reset
after, never leaking into tools). Every other turn keeps Haiku + the small prompt. Switch `pc_manager`; counter
`santosh.PC_MANAGER`. Tests `test_v0864_pc_manager.py` (5). NOT VERIFIED on her PC; the 12 Nov PC layers (planner,
checker) are still on - turning them off is the next step she decides.


## v0.865.0 PC SEEDHA (planner + checker off)

Owner, after the root-cause report and v0.864 PC MANAGER: "TURN OFF PLANNER AND CHECKER ALSO". `config.py`:
`pc_plan` True -> False (no Sonnet planner call before the first PC step, no stages, no per-stage screen check) and
`pc_verify` True -> False (no Haiku screen check before 'done', no send-backs). The v0.859 D2 / D4 code stays and a
`PC_PLAN=true` / `PC_VERIFY=true` line in the VPS .env turns them back on. No test change: tests/conftest.py already
pinned both off for the older suites; the v0.859 suite sets them on for itself. NOT VERIFIED on her PC.


## v0.866.0 SONNET VIA OPENROUTER

Owner, after "RS 3000 IS GONE IN TESTING": "I HAVE CREDIT IN OPENROUTER USE SONET VIA THAT". Her PC work (the manager
turn in chat / call and the PC loop) now runs on Sonnet billed to the server's OpenRouter key
(`providers.key_of('openrouter')`). OpenRouter's id read live from openrouter.ai/api/v1/models:
`anthropic/claude-sonnet-5.5` (vision + tools).
- PC loop: `pc/brain.choose` returns brain `sonnet-or` when `pc_via_openrouter` is on and the key exists; `think` sends it
  over the same OpenAI-shaped path Qwen uses (`think_qwen`), with the system message marked `cache_control` ephemeral
  (OpenRouter passes Anthropic prompt caching through) and without the Qwen-only reasoning / provider-sort fields.
  Claude's native computer toolset (v0.859 D1) needs the Anthropic API, so it now runs only on brain `sonnet`.
- Manager: a PC turn (`pc_manager.wanted`) with the key runs on brain `glm` with `llm.MODEL_NOW` =
  `openrouter:anthropic/claude-sonnet-5.5` - the path her console model pick already uses; no key = v0.864's Anthropic
  Sonnet path.
- `pc_via_openrouter` default on; `pc_openrouter_sonnet` names the model. conftest pins it off for the older suites.
Tests: `test_v0866_sonnet_openrouter.py` (3). NOT VERIFIED: no live OpenRouter Sonnet call from here (no key in the
sandbox); tools are only the cached system prompt - tool definitions are not cached on this path, so a PC step may cost a
little more per token than the direct API with caching. Prices are OpenRouter's (Sonnet 5.5 $2 / M input as listed).


## v0.873.0 REDESIGN JOINS MAIN (owner: "MERGE TO MAIN")

The Claude-style phone redesign (R0-R9, `docs/HOOLA_APP_REDESIGN_PLAN.md`) had been built on the branch
`claude/hoola-project-review-6ba8s5` as v0.859.0-v0.872.0, while main moved on its own PC line v0.859.0-v0.866.0
(DESKTOP AI D0-D4, PC KA HISAAB, PC EK BAAR, PC CHROME HI, PC SAATH, PC MANAGER, PC SEEDHA, SONNET VIA OPENROUTER).
Release APKs are built only from main, so the owner's phone never got the redesign. This merge joins the two lines
(a merge commit, both histories kept as they were). Conflicts: ~230 test version pins (every conflicting hunk was
checked to differ only in the version number), pubspec, APP_VERSION, the CLAUDE.md "Current version" line and this
file (both sections kept). The numbers v0.859-v0.866 now mean two different releases each - look one up by its
NAME here. Merged version 0.873.0 (pubspec 0.873.0+872), above both lines. No product code was edited in the merge.

## v0.874.0 PC SASTA (built as 0.867) - a cheap PC worker with a strong helper (owner: "go more deep find a very low cost api solution for desktop work handling end to end and smoothly", then "GO QWEN 27B")

Research (12 Nov 2026, OpenRouter's live list + aggregator leaderboards, NOT the benchmark authors): per PC step (~8k tokens in, 300 out) Sonnet 5.5 ~Rs 1.8, Qwen 3.8 Max ~Rs 1.5, Qwen 3.8 27B ~Rs 0.15-0.2, Haiku 5.5 ~Rs 0.08, DeepSeek V4.1 Flash ~Rs 0.12-0.24 (a general model, no computer-use claim; V4 Pro / Pro-latest are text only). Reported OSWorld-Verified: Qwen3.8-27B 0.843 (llm-stats), a Qwen UI-Agent 27B 79.5 (Simular), UI-TARS-2 47.5. UI-TARS 1.5 7B has no tool calling on OpenRouter.

Built (all behind settings, Sonnet / Qwen Max one `model=` pick away):
- `pc/brain.py`: brain `qwen27` = `pc_cheap_model` (qwen/qwen3.8-27b) over the existing OpenAI-shaped OpenRouter path (thinking off, provider sort latency); `pc_model` default qwen27; no OpenRouter key = Sonnet and said.
- NEW `pc/rescue.py`: RESCUE (`observe` after every turn: same action x3, screen hash unchanged after 2 actions, 2 error turns; passive actions - scroll / wait / reads - never count; `rescue_active` gives the next `pc_rescue_steps` (3) steps to Sonnet via OpenRouter, max `pc_rescue_max` (4) per task, then the cheap worker returns; the turn's result carries a note naming what failed); PLAYBOOK (10 rules, only the cheap worker); SPEND (`charge` a flat estimate per step by brain, `over_budget` daily Rs `pc_daily_inr` 300 per person, `step_cap` `pc_step_cap` 64).
- `pc/operator.py`: playbook appended to the system prompt, over_budget checked before each step, observe note added to the turn's result, steps_max capped at start; Op fields rescue_left / rescues / sigs / shots / err_run.
- Tests `test_v0867_pc_sasta.py` (16). Log lines: `pc brain qwen27 qwen/qwen3.8-27b step N ... (rescue)`, `pc rescue <id> step N #k -> <model> for 3 steps | <why>`.
NOT VERIFIED: no live Qwen 27B PC step; the spend cap is an estimate held in memory (a restart resets it); the step cap defaults to 64 so it changes nothing until lowered.


## v0.875.0 PC MANAGER COST (owner: "FIX IT PERMANENTLY")

Her OpenRouter activity for 13 Nov: Claude Sonnet 5.5 $2.36, Qwen3.8 27B $0.132. The Qwen line = the cheap PC worker (v0.874); the Sonnet line = the PC MANAGER turn (v0.864 / v0.866 pinned it to Sonnet via OpenRouter, ignoring CHAT_LLM / GLM_MODEL). A manager turn re-sends the chat, the PC rules and every tool in view with no prompt cache, and her log showed one job cut into 8 tiny tasks (open tab, go to the site, click the box, type, Enter, filter) = 8+ manager turns.
- `pc_manager_openrouter_model` (default `qwen/qwen3.8-27b`) - `agent/santosh.py` manager branch uses it (falls back to `pc_openrouter_sonnet`); `anthropic/claude-sonnet-5.5` there = the old behaviour.
- `agent/llm.py` `_cache_system`: an Anthropic model reached through OpenRouter gets `cache_control: ephemeral` on its system message in both OpenAI-style body builders; other models untouched.
- `agent/pc_manager.py` RULES: one ask = one pc_do task, never tiny tasks.
- Tests `test_v0875_pc_manager_cost.py` (5); test_v0866 / test_v0874 pins moved to the Qwen manager.
NOT VERIFIED: Qwen 27B as the manager on her server (tool choice, task writing); the cache saving is OpenRouter's, not measured here.


## v0.876.0 EK BHASHA CALL — one language on a voice call (owner: "voice call is talking in english inbetween find root cause", then picked "Hinglish on calls")

ROOT CAUSE, five pieces of one mistake (two opposite language rules on the same call):
1. The language lock (top + end of the Gemini prompt) said English since v0.728 SAB ENGLISH (`lang.call_lang` -> en-IN).
2. The call script in use kept "Spoken Hinglish ... match her mix": the v0.728 swap regex matched only the long PERSONA's
   line ("the way people really talk:"), not PERSONA_LEAN's or PERSONA_BRAIN's ("as people really talk") - and the live
   server runs PERSONA_BRAIN (voice_brain on).
3. BRAIN_NOTE, attached to every call-brain ask, said "in clear simple English", and the brain's system prompt had the
   English rule, so santosh_kaam answered in English and the voice read it out word for word.
4. The filler / mood examples in PERSONA_BRAIN were English ("one second, checking", "Fair enough, it is late").
5. The web console always opens a call with lang=en-IN (v2.js), the phone sends its app language.

FIX: `voice_language` setting ("hinglish" default, "en" = English calls like v0.728). `lang.call_english()` decides the
lock (`call_lang`: an en-IN / blank ask = the app's language, not hers -> hi-IN), every persona swap (one regex for all
three scripts), the Phonic engine's languages, the call-brain note (`voice.brain_note()` -> BRAIN_NOTE_HI), the
"answer her briefly" note, and `lang.apply` / `lang.quick` leave the brain's own "reply in the user's language" rule on a
call turn (`lang.on_call()` = turnchannel CALL, i.e. VOICE_BRAIN_NOW or a call's ticket). PERSONA_BRAIN fillers in
Hinglish and "say the reply IN THE CALL'S LANGUAGE (an English reply is never read out in English)". Chat stays English.
Tests: test_v0876_call_language.py 7; test_v0728 English-call test now sets VOICE_LANGUAGE=en; test_v0630 filler pin moved
to the Hinglish line. Pre-existing reds (stash-proven, untouched): test_human_voice x4, test_v0728 every_tool_label,
test_v114 lock, test_v119 x2. NOT VERIFIED on a live call. Back to English calls: VOICE_LANGUAGE=en in the VPS .env.


## v0.877.0 PC STEADY — consistent PC work, popups handled, thinking on screen (owner: "NOW LETS WORK ON 2 THINGS FOR DESKTOP WORK 1) WORK CONSITANCY 2) THINKING ON SCREEN" -> diagnosis -> "GO ALL THREE")

Diagnosis (told to her in plain English first): the PC worker sees only the task sentence + the last 2 screenshots and
keeps no list of what is done, so it restarts work; a replacing task starts from zero; a deep link always opened a new
tab and "still loading" invited a second open; the stuck detector only knew the exact same action 3 times; popups and
notifications were left to the model (the browser's own Allow-location bubble is not in page_elements); the address /
text could be typed into a window that had just taken the front; the model's words each turn were thrown away, so her
card only said "Soch raha hoon".

Built (NEW `server/app/pc/steady.py`, hooks in `pc/operator.py`, one rule in `pc/rescue.py`):
1. CONSISTENCY - `record` keeps PROGRESS (what worked, from tool results; failed results and reads never count),
   `progress_block` rides every screen ("DONE - never redo", the task restated); `aim` (open page / app / typed text /
   form) - the same aim again gets a NOTE, `aim_repeats >= 2` = stuck -> Sonnet rescue ("it kept redoing work");
   `already_open`: open_url of a page this task opened while that site is in front is not reopened (new `reload`
   flag on the tool); `carry_from`: a task that REPLACES a running one starts with its progress + opened pages; her
   ask_user choice is a progress line.
2. POPUPS - `screen_note` ("SCREEN UNCHANGED after click ...") when a real action moved nothing; `sweep` (only when
   the screen did not change or the front changed by itself, plus every 5 steps) names a window that came to the front
   on its own / new windows / NEW Windows notifications via the existing ax_notifications (DATA, told once, never
   dismissed by code; a missing helper switches it off for the task); `focus_ok` - a `type` is refused (NOT RUN) when
   the front window's app is not the one on the screenshot the model saw, unless this turn moved focus on purpose
   (fast path / opener); `_open_in_named` re-checks the front before typing the address and refocuses once; the prompt
   (`steady.PROMPT`) makes POPUPS FIRST (Esc / X / Not now / Block / Later; send / pay / delete still ask).
3. THINKING ON SCREEN - the prompt asks for ONE short line a turn (what it sees, what it does next, Hinglish, <= 20
   words); `note_thought` keeps it (masked, 160 chars) as op.thought / op.thoughts; it is the console working-row label
   (`_work`), in the `browser` event + live() + timeline, on the phone's live PC card (`lib/ui/browser_live.dart`, 💭
   line, C.chip colour), spoken at call milestones (`_speak`), logged `pc think`. `pc task end` logs progress /
   repeats / popups.
Tests: test_v0876_pc_steady.py 16 (unit + the real loop with a fake PC: thought kept, progress sent, typing refused
into a stolen window, an open page not reopened, carry, rescue on repeated aims); PC suites 242+ green; the one red
(test_v0173 memory window) fails identically before this change. NOT VERIFIED on her real PC; the sweep's
notification read depends on the agent-desktop helper on her PC.


## v0.878.0 CREDIT ROKE NAHI — an OpenRouter credit hold no longer stops the work (owner: "SUDDENLY IN BETWEEN SAYING CREDIT LIMIT IS OVER AND STOP THE WORK --- FIX THIS FIRST")

Her log: `pc task end ... status=failed ... QwenError: Qwen 402: This request would exceed your available credits given
your current in-flight requests. Retry after in-flight requests settle, or add credits.` ROOT CAUSE: OpenRouter reserves
the cost of prompt + max_tokens for every request in flight against the account balance. Hoola runs on OpenRouter end to
end (chat on qwen3.8-27b, the PC manager turn, the PC worker with max_tokens 4000 and a long screenshot prompt, often
several at once), so a low balance refused a step even though the step itself would have cost a fraction of the hold -
and `think_qwen` treated 402 like any error: the task died as failed.

Fix: `agent/llm.py` CREDIT_WAITS (3 / 6 / 10 s), `credit_402`, `credit_body` (half the max_tokens, floor 1200 for chat,
800 for a PC step), CREDIT_LOW_LINE. `pc/brain.py think_qwen`: a 402 waits for the others to settle and asks again with
less room (up to 3 times, not counted against the ordinary retries); still 402 = `CreditLow`. `pc/operator.py _run`:
CreditLow ends the task PARTIAL (progress kept, summary says add credit at openrouter.ai and say 'continue'), logged as a
warning, never 'failed'. The chat door's non-stream and stream paths do the same and the final error carries the line.
Tests `test_v0878_credit_hold.py` (5). NOT VERIFIED on her server. If 402s keep coming, the balance itself is low:
openrouter.ai > Settings > Credits.


## v0.879.0 EK KAAM EK BAAR - one call job at a time on her PC (owner: "FIX ALL" on the 13 Nov log review)

From her 00:51-03:03 logs: (1) at 02:32 one call sent its asks into three chats (the v0.657 side records), and all
three steered the same PC task at once (Amazon / Aadhaar / 'close Aadhaar, open Amazon') while every brain ran
together - the OpenRouter in-flight credit budget ran out (402s); (2) at 02:59 the PC step after typing the Aadhaar
number got no answer from the AI for 3.5 minutes with nothing said (90 s timeout x 3 silent tries); (3) every PC step
held 4000 output tokens of credit.

Fix: (A) `voice.Call._run_conv` - when the call record is busy and `_pc_in_use()` (a PC task of hers running, or her PC
used in the last 10 min) the new ask waits for the first on the call record (stats `pc_queued`, log 'her PC is in use -
this ask waits'); with no PC work the side record runs it at once as before. Stop words are still caught before the lock.
(B) `pc/brain.py think_qwen` - an httpx timeout (`pc_brain_timeout_s` now 35 s) calls `on_slow` once (`_tell_slow`: a
spoken line on her call + the card) and tries once more; a second timeout raises `BrainSlow` and `operator._run` ends the
task partial ('the AI did not answer in time, twice ... say continue'). (C) `pc_max_tokens` 1500. Tests
`test_v0879_one_job.py` (5); the v0851 default pin moved to >= 1500. NOT VERIFIED on her server. If her VPS .env sets
PC_MAX_TOKENS or PC_BRAIN_TIMEOUT_S, that line wins over the new defaults.


## v0.880.0 TEZ CALL - the call brain answers sooner (owner: "NOW LETS WORK ON VOICE CALL SPEED AND REAL TIME REPLY")

Her 13 Nov call log (v0.879): Gemini itself starts a reply in ~1.3-1.4 s (p50), but every santosh_kaam ask took 10-20 s
("brain answered in 13.2s / 13.6s / 10.1s") and most PC asks hit the 20 s "brain still working" line. Root causes found
in the log:

1. PC asks: pc_do waits `pc_wait_seconds` (12 s) for the PC task before returning, so the call brain could not speak.
2. Memory: "call brain memory: facts / coder / cards not ready in 2.5s" on nearly every ask - each ask paid 2.5 s.
3. Visibility: her call brain runs on the OpenRouter / GLM path, which logged neither the prep line nor a call time,
   so the model's own share could not be read.

Fixes:
- `agent/tools.py _call_pc_wait`: on a call's brain turn (`VOICE_BRAIN_NOW`) pc_do / hoola_pc_do / pc_team get
  `_wait = voice_brain_pc_wait_s` (4 s). Set in the dispatcher; the frozen pc_tools.py is untouched (it already takes
  `_wait`). The PC task keeps running and speaks its milestones on the call itself (v0.858 `_speak`). A caller's own
  `_wait` wins; chat turns are unchanged.
- `agent/santosh._brain_memory`: cap 2.5 -> 1.5 s (`voice_brain_memory_s`); when this call already holds a copy (< 10
  min) of every slow part it waits only `voice_brain_memory_warm_s` 0.6 s; a cached copy, even an empty one, is no
  longer reported as a gap. `brain_prefetch` (called from `voice.Call.run`) reads the parts when the call connects, so
  the first ask is warm too (`voice_brain_prefetch`). Trade-off: the facts-by-meaning part may come from the previous
  ask's words; the fresh read for this ask finishes in its thread and is used next.
- `agent/santosh._call_brain_once` GLM branch: the prep line + `glm call N s model msgs tools cap voice=`.

Not changed on purpose: Qwen 3.8 27B's reasoning on call turns (OpenRouter makes some models refuse reasoning off;
measure first with the new log line). Tests `test_v0880_tez_call.py` (5) + the v0638 default pin moved to 1.5.
NOT VERIFIED on her server or a real call.


## v0.881.0 PC JUDA HAI - "connect to my PC" on a call answered at once (owner: "IN VOICE CALL WHEN ASK HOOLA TO CONNECT TO PC IT TAKES HUGE TIME TO REPLY CHECK THE PERFECT ROOT CAUSE FIRST" -> "go")

Root cause from her 13 Nov log: 00:52:21 "मेरे पीसी से कनेक्ट करो" -> 2.5 s memory wait -> the PC manager turn on Qwen ->
00:52:37 a whole PC screen task ("Connect to this PC and take a look at the current screen") -> "still working" at 20 s;
01:56:49 the same ask 13.6 s (queued behind the weather ask). Her PC is connected whenever Hoola Desktop is open, and the
call already read the hub's online state (in `_pc_rescue`) but never answered with it.

Fix: NEW `server/app/pcconnect.py` - `only_connect(text)` (strict: every word is a connect word, a PC word or filler in
English / Hinglish / Devanagari; any site / doing word = a real job), `status_line(tenant)` from `hub.devices` (her PCs
only: online, control off, paused, offline, plus the task running). `voice.Call._pc_connect_answer` runs in the
santosh_kaam branch (before the brain) and in the PC rescue path; switch `voice_pc_connect_fast`. `agent/pc_manager.py`
RULES: connect / "is it connected" is never a pc_do job; "connect + Amazon" = one task for the Amazon part. Tests
`test_v0881_pc_juda.py` (18). NOT VERIFIED on her server or a real call.


## v0.882.0 PC JOB YAAD - a PC remembers its last job across calls and chats + the drift guard (owner: "also check the long work consistancy of hoola ai on desktop" -> "GO")

Diagnosis from her 13 Nov log (about 2 hours of PC work):
1. The job was forgotten when a task ended - the Aadhaar download was started from zero 7 times (01:29, 01:32, 01:58,
   02:01, 02:34, 02:37, 02:57) from 8 different chat / call records. `steady.carry_from` only passed progress to a
   task that REPLACED a running one; after a task ENDED the next one started blank, and a new call is its own record so
   the brain there could not see the earlier result either.
2. One job became 4-6 tiny tasks (step-by-step asks on a call; the previous task had already ended).
3. Long tasks drifted unchecked - "mobile under 2000" ran 35+ steps until she stopped it; the rescue only reacts to
   repeats / an unchanged screen / errors, and the planner + checker are off (v0.865).

Fix:
- `pc/steady.py` JOB CARD per PC (`JOBS[(tenant, device_id)]`, `pc_job_memory_min` 45, her PCs only): `remember(op)` at
  task end keeps the task, what really got done (the progress list; chained when the task continued the previous job),
  pages it opened, last window, why it stopped (masked). `carry_job(op)` gives the next task on that PC, from ANY chat or
  call, an `EARLIER WORK` block (do not redo, continue if it is the same job) + its opened pages. `job_block(tenant)`
  goes into the PC manager's rules on every PC turn, so the brain on a new call knows what is really on her PC.
- DRIFT GUARD `steady.drift(op)`: `pc_drift_steps` (12) steps with nothing new on the progress list = a note to the
  worker (do the next real part or end partial and say what is left); twice that = `op.drift_stuck` -> `rescue.observe`
  hands the next steps to the strong helper. No planner / checker came back; nothing clicks by itself.
- `pc task end` logs `drifts=N` and `job: <last done items>`.
Tests `test_v0882_pc_job_yaad.py` (8). NOT VERIFIED on her PC.


## v0.883.0 CALL PC SEEDHA - the call answers, the PC task works (owner: "CHECK THE LOGS --- GIVE COMMAND I WILL PASTE HERE" -> diagnosis -> "go")

Her 13 Nov 08:28-08:40 calls (Swiggy pizza, Task Manager) showed v0.881 connect (instant) and v0.882 job card (4 follow-ups
"continue, not restart", tasks 16-51 s) working, and six remaining causes:
1. A call ask that looked big (`goal.looks_big`) made the call brain a long job: 16k cap (one Qwen call 38.4 s) and it kept
   calling tools while the PC task ran (9 calls, msgs 37 -> 55), holding the chat lock - her next words waited 21 / 22 / 58 s
   ("lock 58.4s"). Now: `state["big"]` never on a call turn; once pc_do / hoola_pc_do / pc_team succeeded on a call turn
   (`state["pc_handed"]`), `_pc_watch` tools (pc_do / pc_team / pc_task_result / pc_status / pc_devices / kaam_status) are
   held with "answer her now in one short line" (`CALL_PC_HELD`). Other tools still run.
2. A follow-up with no PC word ("isse minimize kar do") lost the PC tools (tools 64 -> 77 via tool_search), the task
   started 36 s after her ask. Now `pc_manager.wanted` is True on a call turn when her PC worked in the last 10 min.
3. The Web Studio block (`turnmode`) took 2.7 s on a call turn - skipped on calls.
4. Her Chrome's page tools (page_elements / page_text / tabs / page_type) worked until 03:47 and failed on every task from
   03:51 (after Hoola Desktop was paused and resumed); each failure a step, two in a row a Sonnet rescue. Now
   `steady.lane_skip`: 2 failures in a task = SKIPPED (not an ERROR, so no rescue) with "use the screenshot", and every
   failed `pc act` logs `ERROR | <first 200 chars>` so the real reason shows next time. The reason itself is NOT known yet.
5. Hoola's own banner sat over the page; the model clicked it, a new tab opened, the Cart tab was lost. Prompt rule: Hoola's
   window / banner is never a target or a popup to close. (Keeping it out of the click area would be a desktop change - not done.)
6. Task Manager runs as administrator: Windows blocks a normal app's input (UIPI), so minimize took 20 steps / 61 s; and
   Ctrl+Shift+Esc is a blocked key. `steady.admin_note`: after 2 unchanged screens on an admin-looking front window, said once
   ("Yeh window admin mode mein hai... aap khud kar dijiye"); prompt: open Task Manager with open_app, never drive admin windows.
Also: the connect answer spoke "[Team job: ..." word for word - `pcconnect._short_task` speaks only the short goal.
Tests: test_v0883_call_pc_seedha.py (8). NOT VERIFIED on her server or PC.


## v0.884.0 CHROME SAAF — Hoola's own PC Chrome ready for government / legacy portals (13 Nov 2026)

Owner, after asking to work on Hoola's own PC (every user will get one, for repeated manual work on gov / legacy portals,
results reported back to the chat): "ON HOOLA PC CHROME NOT OPEN ALL WEBSITE CLEANLY IT STOPS IN BETWEEN IT IS ISSUE OF
LOCATION OR A CHROMIUM NEED TO FIX THIS FIRST". Her check on the VPS: Hoola PC up 27 h, real Google Chrome present,
IP 139.59.10.30 Bengaluru (DigitalOcean) = an INDIAN address; TZ empty + LANG C.UTF-8 (a UTC, language-less browser);
curl from the container: google / incometax / gst / uidai / epf / aaplesarkar / mahadiscom answer in < 3 s,
parivahan.gov.in never answers (25 s timeout) - it drops cloud servers. Server RAM is 16 GB (not 8).

Fixed (desktop-linux agent 1.5.0, Dockerfile, operator):
- India time (TZ Asia/Kolkata, tzdata) + Chrome --lang=en-IN / --accept-lang en-IN,en,hi.
- Chrome managed policy written before Chrome starts (/etc/opt/chrome + /etc/chromium policies/managed/hoola.json):
  pop-ups allowed, downloads to /data/Downloads without asking, notification / location / translate bubbles off,
  password manager off. Background throttling off (a tab not in front keeps working).
- open_url: the same site's tab is navigated instead of a new tab every time; at most 6 tabs (older closed);
  waits up to `wait` s (30 default, max 60, was 12) on document.readyState; a net error is retried once; a crashed
  tab reloaded once; a "checking your browser" page gets 15 s more; the result carries `problem`
  (blocked / net:ERR_* / slow / bot_check / certificate / no_answer / crashed) + `hint`, which the operator puts in
  front of the model as "PROBLEM: ...". HOOLA_PC_ADDENDUM gains the PORTALS rule.
- A certificate warning is NEVER clicked past (an auto-pass for gov sites was dropped - the safety check refused
  it); the model tells her and offers her own PC.
- `docker exec hoola-pc python /app/agent.py check <urls>` opens each site in the real Chrome and prints OK / FAIL +
  why; vps-ops pc_deploy runs it on six portals after every deploy.

Tests: test_v0884_chrome_saaf.py (6) + a local walk in real headless Chromium (normal page, Access Denied, "Just a
moment", refused port, slow page, tab reuse, tab cap). NOT VERIFIED on her VPS until pc_deploy rebuilds the image.
NOT FIXED (cannot be, from code): a site that drops every cloud-server address (parivahan) - it needs her own PC or
an Indian home-internet route.

Next (her decisions, 13 Nov): every user gets a Hoola PC through a SHARED POOL (per-user Chrome profiles), HUMAN IN
THE LOOP for submits; then repeat jobs over a sheet's rows, files back to the chat, a report back with proof.

- v0.884 follow-up (agent 1.5.1): her live check on the VPS - google / incometax / gst / uidai / aaplesarkar OK in 1-2 s; parivahan.gov.in came back "OK" after 40.6 s with NO title (the tab never left about:blank and a blank tab at the deadline counted as fine). Now `_settle` calls that `no_page` with the hint "the site refuses cloud servers, offer HER PC"; test added.

## v0.885.0 HOOLA PC POOL (13 Nov 2026)

Owner: "EVERY HOOLA USER WILL HAS ITS OWN HOOLA PC --- IF USER WANTS THEY CAN GIVE MANUAL TASK TO HOOLA PC ON CHROME AND
AFTER TASK COMPLETION HOOLA WILL REPORT IT BACK --- IT IS BEST FOR LEGACY PORTALS AND GOV PORTALS WHERE NEED A HUGE
REPEATED MANUAL WORK ... JUST NEED HOOLA OWN PC TO SEND DOCUMENTS ON CHAT" -> "Shared pool AND HUMAN IN LOOP" (after the
v0.884 Chrome fix) -> "GO". Frozen-PC exception recorded in CLAUDE.md.

**Shared pool** (`server/app/pc/pool.py`, `hub.pool()` / `hub.hoola_pcs()`): Hoola's own PCs belong to Hoola, not to the
tenant that paired them. A Hoola PC task for any user picks a FREE one - the PC she used last (`pool.LAST`, her portal
logins are open there), then her own, then any. A PC working for someone else is never taken over (`busy_any`); all busy =
the task is `queued` (`operator._start_queued` / `_queued_go`, FIFO `pool.QUEUE`, `queue_place` on the card, gives up after
`hoola_pc_queue_min` 30 with a plain line). Switch `hoola_pc_pool` (off = only her own Hoola PCs, as before).

**Her own folder on a shared PC** (agent `use_profile` / `do_profile`, server `pool.prepare` before the first step):
- key = HMAC(server signing key, tenant)[:24], secret = HMAC(..., "secret") - nothing stored; the PC holds the secret only
  while it serves her.
- /data/Downloads and /data/work become symlinks to /data/profiles/<key>/{Downloads,files}; Chrome's user-data-dir is
  /data/profiles/<key>/chrome (Chrome restarted, every window of the previous user closed, background commands killed).
- the previous user's folder is tar'd (caches skipped) and encrypted with `openssl enc -aes-256-cbc -pbkdf2 -iter 100000`,
  then the readable copy is deleted; it is decrypted only with her secret (a wrong secret changes nothing).
- the PC's first user (`home`: the tenant that paired it) gets her old /data/chrome + /data/Downloads moved in once.
- shell commands (`run`) run as the unprivileged `hoolawork` user (Dockerfile `useradd -u 1500`), cwd/HOME = her work
  folder; the walls: /data 711, identity.json 600, other folders 700, her Downloads/files owned by hoolawork. Checked here as
  root: whoami = hoolawork, `cat identity.json` / another folder = Permission denied, her own folder writable.
- file actions (list / read / send_file / open_url file://) refuse other users' folders, archives and the token (`allowed`).
- an old agent that does not know `profile` may still serve the user who paired it (legacy shared folder) but never anyone
  else (`HOOLA_PC_OLD`).

**Files and proof to her chat**: tool `send_to_chat {path, title}` (Hoola PC only) - the PC uploads, the server re-tags
the row to HER tenant as a phone download (`pool.claim_file`) and posts a `pc_file` card. Every Hoola PC task that ends
done / partial / failed posts the last screenshot as "Hoola PC screen at the end (proof)" (`_proof`, `hoola_pc_proof`).

**Repeat jobs** (`server/app/pc/batch.py`, tool `hoola_pc_batch`, registry 629 -> 630): her job once with {Column} blanks
+ her Excel / CSV from the chat (or a list). Every blank must be a column (checked before anything runs). Row 1 runs as a
normal watched task (her card on every submit). Then `operator.ask_tap` shows a confirm card with the proof - only HER tap
lets rows 2..N run (the model's `go` only shows the card again). Rows run one by one on the same PC with `batch_ok`: a submit
of the same kind needs no new card, but money / delete / OTP / install / settings always ask (`_batch_needs_tap`). Three
failures in a row pause; a server restart pauses (worker slot `hoola_batch_jobs` -> `sweep_after_restart`) and marks the
cut row "CHECK ON PORTAL" (never resubmitted by Hoola). At the end one Excel (every row's inputs, result, what happened,
proof screenshot link, files sent) comes to her chat. State in `<pc_files_dir>/../hoola_batches/<id>.json`.

**Also**: `run background=true` (up to 2 hours, 6 at once) + `run_status` / `run_stop`; installs from installed.log put
back after an image rebuild (`replay_installs`, background thread at boot); the PC job card (`steady`) is kept per user
for Hoola PCs (`_dev` -> "hoola_pc") so a follow-up continues on whichever Hoola PC she gets. Prompt: THIS PC IS SHARED,
FILES TO HER, LONG COMMANDS, REPEAT JOBS. Agent 1.6.0.

REAL-CHROMIUM WALK here (Xvfb + Chromium 1243, a local page): user A sets a cookie + localStorage, the PC switches to B
(B sees nothing), back to A after encrypt / decrypt = A's login is there. The walk FOUND that a Chrome stopped with
SIGTERM drops a fresh login (cookies are written only on a clean shutdown) - `_stop_chrome` now closes it with CDP
`Browser.close` first. The deploy `check` uses a throwaway profile and never stops a Chrome serving a user.

Tests: NEW `test_v0885_hoola_pc_pool.py` (11: folders lock / open / wrong secret / guard with real openssl, background run +
install replay, pool order + pool off, another user's task switches the folder + proof, queue never takes over, send_to_chat
re-tags the file, batch approval never covers money, prompt / tools, rows from Excel / CSV + blanks, the full repeat job
with her tap, no tap = no rows + restart pause). Pins: registry 630 in 36 suites, bridge tool list, agent version >= 1.5.1.
Older red unchanged: test_v0173 finished_task (fails on the commit before too).

NOT VERIFIED: nothing has run on her VPS yet (needs vps-ops deploy + pc_deploy); a second real user has not used a Hoola PC;
encrypting a big Chrome profile takes seconds on each switch between users (not measured on her server).


## v0.886.0 EK RANG - the logo in one solid colour (built as 0.874; their PC POOL / CHROME SAAF line took 0.874-0.885, both kept)

Owner, 13 Nov 2026, with her logo: "THIS IS A APP LOGO -- CURRENTLY LOOKS STALE AND AI MAKE -- DO PERFECT LOGO WORK WITH
GOOD BACKGROUND AND A ICON IS PROPERLY FILED WITH PERFECT ONE COLOUR".

The logo is ONE vector drawing (`server/app/static/console/mark.js`) that every surface is built from, so it was redrawn
there: same idea (a core, a needle through it, two pairs of orbit arcs), now one solid colour - no gradients, no gloss
ridges, no core highlight, no blur. Geometry: the core at the exact centre (was 49.4 / 50.2 from the artwork), the needle
a true 45 degree diagonal (3 wide each side at the core), the arcs full-bodied (widest 7.0 / 5.6 of 100, was 4.4 / 3.1)
easing to rounded semicircle tips (the first pass had small hooks at the tips, seen by eye and fixed), every gap centred
on the needle and the lower pair the 180 degree turn of the upper. `svg({color})` / `svg({mono})`; default fill follows
the console theme through `--acc-rgb` (light #5B45E0, dark #9C88FF).

Colour + background: Hoola violet #5B45E0 = the redesign's one accent (`lib/ui/hoola_theme.dart`). App icon = the WHITE
mark on a solid violet tile: `tool/make_mark.js` now draws the master (mark 82% of the square) AND the Android adaptive
foreground (white mark alone, needle tips at 0.33 of the canvas = inside the launcher's circle) directly - the old
alpha-from-navy derivation in `tool/make_logo.py` is gone; it now checks both sources and builds the web sizes.
`pubspec.yaml` adaptive background #090F32 -> #5B45E0. The console's light mark (`static/hoola-mark.png`) is the violet
mark on transparent; the phone's thinking-mark layers are white and `lib/ui/hoola_mark.dart` tints them (theme violet,
or a `color` the caller passes), alignment now the centre; v2.css transform-origin 50% 50%. The status-bar silhouette is
regenerated from the new shapes. The thinking animation is unchanged (same four parts).

Tests: test_v0462_logo (adaptive background pin -> violet), v0716 incl. the browser walk, v0720 green; flutter analyze
unchanged (26). NOT VERIFIED: on a real phone launcher / home screen (checked in a rendered preview of circle / squircle /
rounded-square masks and 16-96 px sizes).


## v0.887.0 ORBIT - the Hoola Orbit logo redrawn by hand, white on Espresso

Owner, after v0.886 EK RANG went in: "SHOW THIS DESIGN IN MAN MADE PERFECT LOGO PROFESSION AND HUMAN NATIV" (the same
orbit idea, drawn like a designer would), then "CHANGE BACKGROUND COLOUR -- SHOW PERFECT DARK COLOURS 10 LOGOS", then
"INCRESCE THE CENTERLINE TILL END", and on option 2 "To the edge, bolder" on Espresso: "CHOOSE THIS".

`server/app/static/console/mark.js` rewritten in TILE coordinates (0..100 = the whole app icon; the mark's grid placed at
12..88, K = 0.76):
- one centre (50 / 50), a true 45 degree needle;
- both rings (R 38 / 25.5 on the mark grid) split into halves by ONE needle channel (CH 5.2, parallel to the needle) -
  the ring ends are cut, never rounded off;
- each half tapers by one rule: its inner edge is a circle shifted toward the opposite side (3.6 / 2.6), so a half is
  thickest facing away from the cut;
- the needle is a bold sharp diamond (5.0 wide at the core) whose tips stop just inside the tile edge: 8.94 on the
  diagonal for the 22 % rounded square, 17.14 for a round launcher (`PATHS.needle` / `PATHS.needleRound`);
- every shape is a plain SVG path (arcs + lines), so the Android status-bar vector uses the same data.
`HoolaMark.svg({..., shape: 'circle', full})`: `full` = the whole tile box, otherwise the tight box `7 7 86 86`;
`HoolaMark.tile` = Espresso #2A1C15, `HoolaMark.violet` stays for the in-app mark (console --acc-rgb, phone tint).

`tool/make_mark.js`: the master = the full Espresso square with the white mark full bleed (launchers / iOS round the
corners themselves); the adaptive foreground = the ROUND-needle mark on the launcher's visible 72 / 108 area (padding
16.67 %, needle tips 28 % in from the canvas edge, inside the circle mask); light mark, phone layers on the tight box;
status-bar vector viewport 86 with a -7 translate group. `tool/make_logo.py` BG -> Espresso. pubspec
adaptive_icon_background "#2A1C15".

Tests: test_v0462_logo (adaptive background pin -> Espresso), test_v0716 status vector pin (viewport 86, translate -7,
6 white fills), v0720 / v0254 green. test_v0240::test_version is red on the untouched commit too (console stamps carry
0.849.0) - not this work. NOT VERIFIED on a real phone launcher (checked on rendered rounded-square / circle / squircle
masks, the console light mark, the stacked phone layers, the status vector drawn from its own XML, favicon 32 / 192).


## v0.888.0 SAAF CHAT - the new chat cleaned up from her phone screenshots

Owner, with three screenshots of the new design on her phone: "DESIGN NEED LOT OF FIXES 1) CHECK THE TEXT TYPING PANEL IS
NONUNIFROM AND NOT PROPERLY ALINED 2) TEXT REPLY LANDING AND FONT IS NOT MATCHING CLAUDE DESIGN WE DISCUSED 3) WHEN CHAT
WORK IN PROGRESS HIDE THE BOTTOM NAVE PERECTLY".

1. Composer (`lib/ui/shell/hoola_shell.dart` HoolaComposer): every control is a 48 dp tap area holding a 40 dp circle and a
   22 dp icon. + and mic are bare icons; only the one main action (voice / Send / Stop) is filled. Before: + was a grey disc,
   mic bare, voice a white disc, all 42 dp and end-aligned under a 48 dp field (3 dp low). The pill is 56 dp (4 dp
   padding), radius pill, the field centres its text (TextAlignVertical.center), a long message grows upward with the
   controls at its foot.
2. Reply type (`lib/ui/hoola_theme.dart`): HoolaType.reply 17 / 1.6 -> 16 / 1.5 Literata, the size the console measured
   against Claude's own reply in v0.253 (Literata's tall x-height makes 16 read like Claude's 17); reply H1 22 -> 20.
   Landing: the server's ephemeral ack line ("Thinking, one minute...", `santosh.ACK_LINES`, payload `ack: true`) was drawn
   as a full reply with Copy / Read aloud / Share / Ask again under it (her first screenshot). The new chat now draws it as
   the working row (mark + "Thinking" + clock) and never as a reply; the newest-reply lookup skips it.
3. Tab bar (`hoola_shell.dart` `_navHidden`, `_SlideAway`): on the Hoola tab with a chat open, while `app.typing`, the bar
   slides down, fades and folds its height (280 ms, reduce motion = fade), the chat takes the room (AnimatedPadding to the
   system inset), and it comes back when the turn ends. Hidden = no taps, no TalkBack.
4. The Hoola mark inside the app: the tab bar, the home hero and the working row used `hoola_logo_fg.png`, which v0.886 made
   a WHITE file (the adaptive icon foreground) - invisible on the light theme. They now use `HoolaMark` (the tinted layer
   drawing). `mark.js` gains `needleMark` (tips at 22 on the diagonal) and the tight box 20..80 for the mark on its own: the
   corner-to-corner needle with no tile around it read as a crossed-out sign. The app icon (full tile, square / round
   needle) is byte-identical. The status-bar vector uses the mark-alone shape (viewport 60, translate -20).
5. `lib/ui/hoola_mark.dart` takes its tint from the theme's accent (HoolaColors light / darkSet), not two raw colours - the
   design-rules ratchet had been red since v0.886.

Tests: screens_test new-design pictures 35/35 incl. the 48 dp tap-target + label gates, NEW picture 55 (the placeholder +
the hidden bar, light + dark); design_rules_test green again; flutter analyze back to the baseline 26; test_v0716 status
vector pin -> viewport 60 / translate -20; server logo tests green. NOT VERIFIED on her phone.


## v0.889.0 EK CHAT EK SESSION - every phone chat its own session, like the web console

Owner: "NOW A CHAT SESSION EVERY CHAT HAS ITS INDEPENDENT SESSION CHECK THE WEN CONSOLVE HOW IT HANDLES DEPLOY SAME FOR
MOBILE CHAT".

How the console does it (`static/console/v2.js` openConv + accountStream, `chatlist.js`): ONE account stream
(/api/console/stream, every event of every chat tagged `conv`); the open chat renders its own events; another chat's
`typing` sets its busy spinner, its new reply sets an unread dot, its cards never land in the open chat; opening a chat
loads its timeline, restores a reply still being written (/live), shows Stop if that chat is busy, and brings back her
unfinished words for that chat (per-chat draft) - files and receipts belong to their chat.

What the phone had: one chat at a time on a per-chat stream (`/api/conversations/{id}/events`) - right for the open chat -
but `typing`, `currentStep`, the "Thinking..." placeholder and the typing guard were app-wide and never cleared on a switch
(Stop, the working row and v0.888's hidden tab bar followed her into another chat), the opened chat's own busy state was
never read back (typing events are ignored while replaying), the composer box was one widget across chats (her half-typed
words moved with her), and the drawer only knew other chats' state from the last /api/conversations fetch.

Now (`lib/state.dart`, `lib/api.dart`, `lib/ui/shell/hoola_shell.dart`, `lib/ui/chat/hoola_chat.dart`):
- `Api.accountEvents` reads /api/console/stream (ends quietly on 404 = many chats off, or 401; reconnects on a blip);
  `Santosh._accountStream` keeps `busyChats` (typing on / off of every chat; a turn's end refreshes the chat list 1.5 s
  later for the auto title + result) and `unreadChats` (an assistant reply in another chat, not the placeholder / greeting);
  opening a chat clears its dot.
- `_clearStory` (every switch / reload) clears typing, step, placeholder, say line and the guard; `_syncBusy` then reads
  the opened chat's own state back (account stream, else GET /api/conversations/{id}/result working | queued) and puts
  typing (with its 75 s guard) back on for that chat only.
- drafts per chat: `draftFor` / `saveDraft` (memory + prefs `draft.<id>`, a save timer PER CHAT - a single shared timer
  dropped the other chat's words on a quick switch, found by the new test); the chat screen loads its draft and keeps it.
- the chat screen is keyed by the chat (`ValueKey('chat:<id>')`): its own scroll, reveal and box; a switch crossfades.
- drawer rows: spinner = the account stream's busy OR the server's working / queued result; accent dot = a new reply
  (never on the open chat).

Server unchanged (the account stream, /result and per-chat streams already existed). Tests: NEW test/chat_sessions_test.dart
(drawer spinner / dot / open chat never dotted; drafts kept per chat incl. the phone copy); screen pictures 35/35, design
rules + tabs / settings / md / fonts / desk kit green; flutter analyze at the baseline 26. NOT VERIFIED on her phone (needs
the server's CHAT_SESSIONS / CONSOLE_V2 on, which the web console already uses).

## v0.890.0 HOOLA COMPUTER (13 Nov 2026)

Owner: "LETS DEVELOP A SECTION FOR IT NAME HOOLA COMPUTER --- IN THIS 2 SECTION -- HOOLA PC, USER PC --- IF USER ENABLE
IT -- USER WILL DOWNLOAD .EXE IN USER PC --- STEPS SHOWN IN THAT SECTION AND FOR HOOLA PC --- USER WILL LAND ON ITS
WORKSPACE DIRECTLY --- IN BOTH SECTION CHAT IS DIFFERENT --- IT WILL NOT MIX WITH HOOLA PERSONAL CHAT, SESSION CHAT ---
WHERE AS VOICE CALL REMAIN SAME FOR BOTH COMPUTERS -- PREPARE A PLAN FIRST ... SHOW THE DESIGN HERE FIRST" -> a design
canvas of 8 screens (web home, Hoola PC workspace, Your PC setup, Your PC workspace; phone tab, workspace, setup, call)
-> "GO". Memory: chats separate, facts shared (one Hoola who knows her).

- Server `server/app/computer.py`: a computer chat = `Conversation(kind="computer", computer="hoola"|"mine")` (new
  nullable column). `callconv.not_call()` now leaves out kind `computer` as well as `call`, so every chat list / search
  list / "the chat she is in" (`convs.current`) skips them. `which_of` / `place_of` (cached per conv).
  `agent/where.remember` returns the fixed place for a computer chat (`hoolapc` / `pc`) and records it as HER choice
  (`_asked` true), so pick.py, the PC tools and the steer all follow; `where.note` gives the model a computer-chat line
  (never switch computers by itself; a site refusing Hoola PC = suggest Your PC).
- Her switch `computer_prefs.mine_on` (default: on when she already has a paired personal PC). Routes:
  GET /api/computer (both computers: online, devices, last work, and `running` = the task running on that computer for
  her from ANY chat or call, with `from` call|chat|computer), GET/POST /api/computer/{hoola|mine}/chats (an empty one is
  reused; Your PC refuses with 409 while the switch is off), PUT /api/computer/mine, POST /api/computer/mine/pair (the
  existing 6-digit pairing code + the desktop-latest .exe link). Messages ride the normal conversation routes.
- Web `/console/computer` (`static/console/computer.html/.js/.css`, own sidebar, light + dark): home with the two
  cards + the one-call strip, Hoola PC workspace straight in (its chats, live screen from /api/browser/<pcop>/frame,
  Stop, its own chat + attach), Your PC setup (switch, download, code, waits and opens the workspace when the PC
  connects), Add another PC / Turn off. Console sidebar row "Hoola Computer" first.
- Phone (new design): 5th tab Computer (`lib/ui/shell/hoola_computer.dart`): cards, setup with Copy link + code,
  workspace with live screen, chat list sheet, composer. The old-look shell is unchanged.
- Tests `test_v0890_hoola_computer.py` (5). NOT VERIFIED: on her server / phone (Flutter compiles on CI first); the
  phone screen has no file attach yet; the voice call keeps its own record (the computer workspace shows the call's
  running task, the call's words stay in the call record).
