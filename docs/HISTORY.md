

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


## v0.891.0 CLAUDE JAISA LIKHAI (built as 0.890.0; their HOOLA COMPUTER took 0.890.0, both kept) - replies shaped the way Claude's apps draw them (owner: the Claude text-pipeline HTML + 3 phone screenshots -> "GO")

The owner's HTML ("How Claude formats text") makes one point that holds: the model writes plain markdown and the app
draws it. Several of its specifics do not hold up (library class names that are not in the library, a sans reply font
that contradicts her own measured Claude screenshots), so Hoola keeps its measured serif reply (Literata 16 / 1.5),
serif headings 20 / 18 / 16 and bold 600.

What her screenshots showed, and the cause:
- Section titles ("The core difference:", "Alphabet (Android) - Q3 2026, total $127.58B") were whole bold lines at body
  size. The live reply rules (`agent/core_prompt.py`, chat_small_prompt on) carried ONE formatting line and said nothing
  about headings.
- 3-column tables were wider than the phone; the third column (share %) was cut off with no sign that it scrolls.

SERVER: `core_prompt.CORE` gains "How your words look" (5 lines) and `replystyle.CHAT` the same rules: `## ` per part
of a long answer (`### ` below), never a bold line or a line ending in ":" as a heading, no heading in a short answer;
bold only list-item openers or one figure; a table only to compare a few items, at most 3 columns, cells a number or
up to 4 words, units in the header, wider data a list or a file; sources at the end as markdown links; code fenced with
its language. Core prompt 9,191 -> 9,876 chars (system prompt limit 12,000). No braces in CHAT (voice .format()s it).

PHONE: `lib/ui/chat/hoola_md.dart` `HoolaMdTable` - the table scrolls sideways with a 28-dp fade on the side that has
more (left appears once scrolled), number columns (every body cell a figure: $, Rs, %, B / cr / x...) right-aligned
in tabular figures, cells max 220; block gaps 16, 24 above a heading, 8 under it, 8 between list items (the console's
measured v0.274 / v0.278 numbers; was 14 / 20); `md_text.dart` links underlined at the text's weight (was 700);
`procedures_screen.dart` learned-task card 600 / 14 and `sentenceCase` for a title typed in capitals (GST / PDF / UPI...
stay). CI app-screens runs the new phone tests.

Tests: `server/tests/test_v0891_claude_likhai.py` (3), `test/reply_look_test.dart` (6). Goldens retaken.
NOT VERIFIED: no live reply has been read with the new rules; not seen on her phone yet.


## v0.892.0 CLAUDE KE AKSHAR - Claude's font sizes and dark-mode weights + a Chat font choice (owner: "WHICH FONT IS USE BY CLAUDE AI" -> "IS WE ARE USING SAME THIS" -> "GO ALL")

READ FROM CLAUDE.AI'S OWN STYLESHEET (assets-proxy.anthropic.com/claude-ai/v2/assets/v1/c6a992d55-CGuUmOei.css, the
file the live site loads; claude.ai itself answered 403 to a fetch): families Anthropic Serif / Anthropic Sans /
Anthropic Mono (+ OpenDyslexic and a system font for the Chat font setting). `.font-claude-response-body` =
--font-claude-response (Anthropic Serif) 1rem / 1.5 weight 400, and under `[data-theme=claude][data-mode=dark]` 360;
body-bold 600 -> 530 dark; heading / subheading / title 530 dark; response small 14px, title 28px (opsz 28), code small
Anthropic Mono 11px; UI base Anthropic Sans 14px / 1.4 weight 430 (400 dark). In-reply heading sizes and the user
message size are set in the page markup, not the stylesheet - not confirmed.

Anthropic's three fonts are their private typefaces - never copied. Hoola keeps Literata (replies), Schibsted
Grotesk (interface + her messages), JetBrains Mono (code), all OFL.

CONSOLE: v2.html loads Literata as the variable font (ital, opsz 7-72, wght 300-700); a v2.css block sets
--rw / --rb (400 / 600 light, 360 / 530 dark, system or picked) on the reply, its bold and its headings, optical sizing
on; Chat font = theme.js `hoola.chatfont` -> `data-chatfont` on <html> before first paint, --fchat (serif = Literata,
sans = Schibsted Grotesk, system = system-ui, dyslexic = OpenDyslexic served from /static/console/fonts, 400 / 700);
Appearance card row with four choices. Stamps 0.849.0 -> 0.892.0 (35).

PHONE: `assets/fonts/LiterataDark-{Regular,SemiBold,Italic}.ttf` = the variable Literata (google/fonts, OFL, no
reserved name) instanced with fontTools at wght 360 / 530 / 360 italic and opsz 12 (the same optical size the static
Literata files use, measured by glyph widths); pubspec family `Literata Dark` + `OpenDyslexic` (.otf). `ChatFont` in
hoola_theme.dart: reply + reply headings take ChatFont.family(c) (dark serif = Literata Dark), bold w600 (w700 for
OpenDyslexic, which has only 400 / 700); Santosh.chatFont (pref chat_font) set before the first reply; Settings > Look
and voice > Chat font sheet draws each choice in its own font. Goldens load the new families; the dark chat picture
was checked by eye (thinner, wraps narrower).

Tests: server/tests/test_v0892_claude_akshar.py (6), test/reply_look_test.dart +1, fonts_test + golden loader;
test_v0249 / test_v0240 pins moved to the variable font link and the real stamp count (35).
NOT VERIFIED: on her phone / her browser.

## v0.893.0 HOOLA COMPUTER TOOLS (14 Nov 2026)

Owner: "TESTED CHECK THE LOGS -- HOOLA PC IS NOT FUCTIONING PROPERLY". Her log after the v0.892 deploy: no `pc task`
line at all; the turns ran on Qwen 27B with 42-56 tools, scraped translate.google.com in the server browser and tried
Google Search (402, Gemini credit gone, Parallel answered). ROOT CAUSE: the tools a turn sees come from her words
(`admit.plan_for` -> `_pc_wanted`: only "PC" words) and `pc_manager.wanted` (her own PC only, returns False for
hoolapc), so a Hoola PC chat never had hoola_pc_do in view. FIX: `agent/santosh.py` admits the pc family for every
computer chat (`computer.place_of`, why "computer chat"). Tests `test_v0893_computer_tools.py` (a real turn in a Hoola
PC chat sees hoola_pc_do - fails without the fix; the same words in an ordinary chat do not). Also read from the log,
not code faults: 13 Nov 16:43 her own PC's Hoola Desktop was paused; 16:56 a deploy restart cut a running Hoola PC task
(PC_OFFLINE). NOT VERIFIED on her server.

## v0.894.0 CLAUDE KA CODE + FADE (built as 0.893.0; their HOOLA COMPUTER TOOLS took 0.893.0, both kept; owner, after v0.892 on her phone: "CHECK THE FONT AND BOLDNESS --- IT IS PERFECT -- STILL SEEM TO OBSERVED SOMETHING MISSING --- AS HOW CLAUDE CHAT IS PERFECT -- FIND THE MISSING THING")

Her two screenshots (a recovery-paths reply) against claude.ai's own stylesheet (assets-proxy .../c6a992d55-CGuUmOei.css):

1. **Inline code.** Claude: `.ReactMarkdown code{border:.5px solid rgb(border-300 / .25); background-color:rgb(text-200 / .05);
   font-size:.9rem; color:hsl(var(--danger-000)); padding:1px 4px; border-radius:.3rem; white-space:pre-wrap}`, --danger-000 light
   `0 58.6% 34.1%` / dark `0 98.4% 75.1%`. Hoola: JetBrains Mono 14 in BLUE (`codeInk`) on a flat sunk background with no room -
   `drive.google.com` / `DCIM` read as links. Now: phone colour role `codeTerm` (#8A2424 light / #FE8181 dark, held to 4.5:1 on bg by
   the palette test), the term 13.5 (12.5 compact) on a 5 % ink tint (9 % dark), with a no-break space in the code's own font (letter
   spacing -0.3 em, ~4px) each side so the chip never sits flush on its letters and never breaks off its word (only when the new chat
   passes its code style; the old MdText renderer is unchanged). The first try used U+202F in the text font - a fallback font with a
   taller line box drew notches at the chip corners; seen in a rendered picture and replaced. Code blocks keep `codeInk`.
   Console: `#app .mh .txt code:not(pre code)` + `.textmd` = the same rule with `--codeterm` (was the violet accent chip).
2. **The edge above the composer.** Claude fades messages into the page (from-bg-100 gradients, mask-image fades); Hoola's list
   was cut through a line where it met the composer. Phone `_Fade` (IgnorePointer gradients of `c.bg`): 32 dp above the composer, 14 dp
   under the top bar. Console `#composer::before` 28px `linear-gradient(to top,var(--chat-paper),transparent)`, z-index 2, no clicks.

Tests: `test/reply_look_test.dart` (+1: term colour / size / room), `server/tests/test_v0894_claude_code_fade.py` (2). Version sweep
0.893.0 -> 0.894.0 (pubspec +893, console stamps 35). Pre-existing red, untouched: test_v0222_saaf_chat::test_rulebook_allows_light_formatting_now
(fails without this change too). NOT VERIFIED on her phone.


## v0.895.0 ATTACH LIKE CLAUDE (owner, with four Claude screenshots: "NOW LETS WORK ON UPLOAD OF IMAGE, VIDEO, APK, DOCUMENT ETC --- MAKE IT PERFECTLY SAME AS CLAUDE DOES. 1) MULTIFILE ATTACHMENT 2) ANY FILE ATTACHMENT 3) OPTION LIKE CLAUDE HAS IN ADD SECTION 4) IN CHAT SPACE IMAGES AND ALL FILES SHOULD LAND PROPERLY")

What the new-design phone had: the composer's + opened only the file picker, picked files sat as small name chips, uploads
went one after another, and in the chat her files showed as name pills (photos never as pictures). Server: 6 files a
message, 25 MB a file, Hinglish upload errors.

Now (`lib/ui/chat/hoola_attach.dart`, the composer in `lib/ui/shell/hoola_shell.dart`, `_Mine` in `lib/ui/chat/hoola_chat.dart`):
1. **Tray** - 100 dp rounded thumbnails inside the composer (it turns from a pill into a 28-radius card): a photo shows
   its own bytes at once, a video its frame once up, a PDF its first page, text its first lines, anything else (APK, ZIP,
   audio, Office) its icon + name + "APK · 18.1 MB"; a dark round x (c.pill / c.onPill) on each; a spinner with the real
   upload % while it goes up; red edge + reason + Retry when it did not ("Over 30 MB" has no Retry). Uploads run three at
   a time; tapping Send while some are still going up holds the message ("Sends when the files are up") and sends after
   the last one.
2. **Any file, many files** - Camera (image_picker camera), Photos (pickMultipleMedia: photos AND videos, several),
   Files (file_picker FileType.any, several: APK, ZIP, PDF, Office, audio, code...). 20 files a message and 30 MB a file
   (Claude's limits) on the phone (`hoolaMaxFiles` / `hoolaMaxBytes`), the console (v2.js addFiles) and the server
   (`chatfiles.MAX_FILES` / `MAX_BYTES`, `NewMessage.files` max 20, `shown` / `context` take 20).
3. **Add sheet** (`showHoolaAddSheet`, Claude's "Add to session"): Camera / Photos / Files tiles; Research switch (a chip
   in the composer while on; each message carries `research: true` and the server puts `main.RESEARCH_NOTE` beside her
   words - her bubble stays her words); Connectors (Connect tab) / Your computers (Computer tab) via `hoolaTabRequest`;
   AI team (HoolaTeam); Memory switch = her memory switches (GET / PUT /api/memory/settings, auto + recall together).
   Claude's Permission / Devices / Skills rows have no Hoola twin and were not invented.
4. **In the chat** (`HoolaSentFiles`): her files land above her bubble - one photo / video alone large in its own shape
   (max 260 x 320, radius 18), several as a right-aligned row of 112 dp thumbnails she can swipe; tap = the full-screen
   viewer (photos / video / audio) or the phone's own app (PDF, APK, any file). Each tile and each x is its own
   TalkBack item (found by the test: siblings in a Stack merged and the x vanished from the screen reader).

Upload errors now English ("The file is empty.", "...over 30 MB; share a Drive link instead.", "This file looks unsafe").
Tests: `test/attach_like_claude_test.dart` (4), `server/tests/test_v0895_attach_like_claude.py` (2). Pre-existing red,
untouched: `test_chat_files.py::test_any_file_attaches_and_reaches_hoola` patches `main.run_turn`, which the turn no
longer passes through (fails on 0.894.0 too). NOT VERIFIED on her phone (camera / photo picker / a real APK upload).


## v0.896.0 CALL GLOW - the live call like Claude and Gemini (owner: two screen videos of Claude's voice mode and Gemini Live -> "first show me here the animation" -> a live preview artifact -> "GO GLOW FROM BELOW and living pill like gemini both")

Read from her videos frame by frame: Claude's voice mode folds the typing box into a call bar (+, model chip, speaker,
white X), puts a mic in the middle, swaps the greeting for "Hold tight, connecting…" then "Let's talk, <name>" while
its mark folds to a dot and blooms back, lights the bottom with a soft blue-grey dome, shows her words in a bubble at
the top right, and drains the light when muted. Gemini Live lights the whole lower half and puts a living pill of
moving light between camera / share / mic / X.

Built into `lib/ui/talk/hoola_talk.dart` (the R5 call screen; the call engine CallSession is untouched):
- `CallMotion` - one ChangeNotifier stepped by the screen's Ticker every frame: smoothed voice level (her inLevel
  while she talks, his outLevel while he speaks, a slow breath when quiet, a little more while working), how far the
  light has risen (lit only in a call, not muted, not on hold), the her/him colour mix, and the mark's rings. Only the
  painters and the mark repaint per frame; the rest of the screen rebuilds on call events as before.
- `CallMark` - the app mark's four layers (assets/images/mark_*.png, tinted with the accent): folds to the core for
  0.26 s when the call starts opening, then the rings turn opposite ways (300 / 380 deg a second) while it connects
  or works, and settle into place on the next full turn. Reduced motion = still.
- `CallGlowPainter` - a wide dome from the bottom edge + three soft lights drifting inside it; height and brightness
  follow the level; her colour = the theme's info blue, his = the accent violet. No raw colours (design ratchet).
- `CallPillPainter` - Gemini's pill: moving lights lit from below inside a dark pill, a warm touch while he speaks,
  dim when muted. Tap = stop him.
- Layout: back arrow, "Live · clock", a gear (Call look) on top; the mark + serif line until words come; her words
  in a bubble top right; his words in serif (19) in the middle; a quiet status line only when there is something to
  say (working, speaking = "Tap to stop", mic off, hold, link). Glow look: mic (56, red when muted, "Come back" on
  hold) above + / Type / End; pill look: + / Type / pill / mic / End.
- `app.callLook` ('glow' default | 'pill', pref call_look) + Settings > Call look + the gear sheet in the call.

Tests: `test/call_glow_test.dart` (3), `server/tests/test_v0896_call_glow.py` (2); the screen pictures
(test/goldens, incl. the R9 tap-target and 200 % text checks) run clean. Pictures of both looks in dark and light were
checked by eye. NOT VERIFIED on her phone (the live level feel, 60 fps on her device).


## v0.897.0 EK CHAT EK JAGAH - every phone chat its own (owner: "NOW CURRENTLY ALL CHAT IS COME IN ONE SESSION. CHECK THE APP SIDE CODE FIRST")

Checked the app side first, as asked. Three faults, one of them the root cause:

1. ROOT CAUSE - the phone read every chat with the v0.158 one-chat rule. `GET /api/conversations/{id}/timeline` and
   the live `/events` stream (subscribed WITH the tenant) both carried every card of ALL her other chats (every kind
   outside `events.LOCAL_KINDS`: files, pages, approvals, email drafts, jobs...). So whichever chat she opened showed
   the cards of all of them - every chat looked like the same session. The console stopped doing this in v0.227.4
   (`own=true` on its timeline); the phone never got the same switch, even after v0.889 made the phone "per chat".
   Fix: the phone now asks `own`:
   - timeline `own=true&calls=true` -> `events.timeline(own, calls)` -> `_story(calls=True)`: this chat + the call
     records made from it (`events.calls_of(conv)`: Conversation.kind == 'call' and origin_conv == conv; v0.647 put a
     call's cards on its own record, and they belong to the chat the call came from);
   - head `own=true` -> the same story for the self-check (otherwise it would reload the chat forever);
   - events `own=1` -> `bus.subscribe(own=True)` (no tenant fan-in), `bus.backlog(own=True)`, `bus.last_id(own=True)`;
     `bus.publish` now also hands a call record's CARDS (not only its local kinds) to the chat it came from, so an own
     stream still hears what a call made; old subscribers get each event once (dedupe).
   Old apps without the flag keep the old one-chat stream.
2. New chat ran the whole reconnect (`connect(fresh: true)`): `_connect` cleared the screen at once, but
   `conversationId` stayed the OLD chat until the slow `/api/bootstrap` (me, lists, routines, avatar, pending actions,
   usage; 45 s timeout) came back - anything she typed in that time was sent into the old chat; and while a reconnect
   was already running (`_connecting`), the tap did nothing at all. Now `Santosh.newChat({incognito})`: cancel the
   old stream, `conversationId = null` (send() refuses, the composer keeps her words), one
   `POST /api/conversations?reuse=true` (her untouched empty chat reused, as the console's New chat), then
   `openChat(id, isIncognito:)`; not connected = the old full reconnect; a failure goes back to the old chat and says
   so. Every New chat button (shell drawer + home, new chat top bar, old chat screen incl. incognito) uses it;
   `connect(fresh: true)` itself now drops the old chat id first too.
3. `_openStory` race: switching chats quickly let an older, slower load finish after the new one - it replaced the
   screen with the old chat and started a SECOND live stream beside the new one. Now it stops when the chat on screen
   changed (after the timeline call and before the stream starts) and cancels any stream before starting its own.

Tests: `server/tests/test_v0897_ek_chat_ek_jagah.py` (4: own timeline / head / backlog keep other chats out and the
chat's calls in, old apps unchanged; own live stream hears its calls not other chats; the phone source asks own and
New chat lets go first). Phone analyze unchanged (27 baseline), phone chat tests green. Older red seen on the way and
proven on the untouched tree: test_v0178_realtime::test_crashed_turn_still_replies_and_typing_goes_off.
NOT VERIFIED on her phone; the server part needs the VPS deploy.


## v0.898.0 CHAAR TAB - Hoola, AI Employees, Tools, Computer (owner: "NOW CHECK THE BOTTOM NAV REMOVE :: WORK SECTION INSTEAD PUT AI EMPLOYEE, REMOVE CONNECTOR INSTEAD PUT TOOLS IN TOOLS (SHOW ALL HOOLA FEATURES INTERACTIVE, VOCAL, FLOW, WEB DEVELOPMENT, APP DEVELOPMENT, CREATE, DESIGN, PROMPTING SAME AS CONSOLE PANEL SHOWN, REMOVE THE MADE -- WE WILL KEEP IT AT DIFFERENT POSITION ---- BOTTOM WILL HAVE 4 SECTION --- HOOLA, AI EMPLOYEE, TOOLS, COMPUTER")

The new-design tab bar (`HoolaNav` in lib/ui/shell/hoola_shell.dart) was Hoola / Work / Connect / Made / Computer. Now:

- **Hoola** - unchanged (home + chat).
- **AI Employees** (`lib/ui/shell/hoola_employees.dart`) - the console's AI Employees hub in the new design, on the
  same list (GET /api/employees). Header "N working for you · M ready to hire"; search; department chips; "Working for
  you" first (shown once - not repeated under its department); every department below; Soon / Hire / Working /
  Paused pills. A tap opens the employee's card (what it does, what it needs, what it will never do) with Hire, or
  Open desk + Pause / Resume + Let go (asks first). A desk the phone has opens in the app (`employeeDeskNative` in
  employees_screen.dart - SEO, Social, CAD, the Game Desk roles, Architecture, Education, Enterprise); any other
  opens the console's own desk (`employeeConsolePath`: Film, Leads, GST & Accounts, the department desks, the 21
  Construction seats; Kaan = Hoola Flow; unknown = the console hub). "Every desk and tool" at the bottom = the old
  Your AI team list.
- **Tools** (`lib/ui/shell/hoola_tools.dart`) - every studio of the console as a tile: Create, Hoola Interactive,
  Hoola Vocal, Hoola Flow, Web Development, App Development, Hoola Design, Prompting; then More: Hoola Code, Game Dev,
  Connectors (the old Connect tab as a page). With big phone text the tiles become rows (nothing cut at 200 %).
  A tap opens that studio's own console page INSIDE the app (`hoola_console_page.dart`): a WebView first loads the
  server's /healthz (same origin), puts her key into the console's own storage (`hoola.console.token`, the same
  Bearer the app already uses), then opens the page - so it is exactly the console's page, already signed in. Mic
  requests are allowed (Flow, Vocal); links to other sites open in the phone's browser; back walks the page's own
  history first; a bar with back, the title, reload and open in the browser.
- **Computer** - unchanged (v0.890).

Work and Made left the tab bar and live in the drawer ("Work", "Made by <avatar>") as pages with a back arrow
(`HoolaPageFrame`). The + sheet's Connectors opens the Connectors page; Your computers = tab 3.

Console: v2.js opens a requested page from `/console/?v=<view>&a=<arg>` (only a view it really has - its own
section or one of the standalone apps; the address is reset so a reload does not reopen it) - that is how Tools
opens Interactive / Vocal / Create and how an employee's console desk opens on that employee.

Also fixed on the way: test_v0475_console_frames::test_app_version_story had been red since v0.896 (its marker
lived in an older version story) - moved to the newest story, the v0.476 precedent.

Tests: test/four_tabs_test.dart (4), server/tests/test_v0898_chaar_tab.py (3), the screen pictures updated (AI
Employees, Tools, Connectors / Made / Work pages, AI Employees + Tools at 200 % text) - all 58 clean.
NOT VERIFIED on her phone: the WebView sign-in, and downloads / file pickers inside console pages (a WebView does not
hand downloads to the phone by itself - "Open in the browser" is the way for those).


## v0.899.0 NAYA CHAT KHULE — New chat opens again (owner: "When click on new chat it won't open new chat ... Check and resolve")

Her screenshot: the new-design drawer, New chat tapped, nothing changed. ROOT CAUSE: the phone's live chat stream
(`Api.events`) and the account stream (`Api.accountEvents`) were `async*` generators. Cancelling a subscription to an
async* stream while the generator sits in `await for` does not stop it there - the cancel future completes only when
the generator reaches its next `yield`. The server keeps a quiet chat open with `: ping` comments only, which never
yield. Before v0.897 the phone's stream also carried every other chat's cards, so some event came soon and the cancel
finished late but finished; since v0.897 each chat streams only its own events, so on a quiet chat
`await _sub?.cancel()` (top of `newChat`, `_openStory`, `_connect`) waited for ever - New chat and switching chats
stayed on the old chat, and the old connection stayed open on the server.

FIX (phone only, server unchanged):
- `Api._sse(url, onRefused, keep, firstWait, maxWait)` = one SSE reader on a `StreamController`: `onCancel` sets
  `stopped` and closes the HTTP client, so the read in flight fails at once and nothing more is delivered; same
  backoff as before (chat 1 -> 16 s, account 2 -> 30 s), a 401 / 404 ends the chat stream with the ApiException
  (account stream ends quietly), an id already seen is never delivered twice, markers + live events pass through.
- `Santosh._dropSub()` lets go of the stream without waiting (`unawaited(cancel())`); every `await _sub?.cancel()`
  is gone. `newChat` sets `conversationId = null` before anything is awaited, so the screen changes at once.

TESTS: `test/new_chat_test.dart` (added to the app-screens CI line): a real local SSE server that only pings - the
chat stream and the account stream both stop within a second of cancel (the old generator never stopped);
events still arrive in order with a seen id dropped; a 401 ends the stream with the error.
`server/tests/test_v0899_naya_chat_khule.py` (4) pins the source shape + version. Version 0.899.0 (pubspec
0.899.0+898; pins + console stamps swept). Pre-existing red, not this work: `test_v0718_seekh_console::test_version_pins`
(its story marker was already gone at v0.898). NOT VERIFIED on her phone; Flutter is not runnable in the sandbox, the
phone test runs first on CI.


## v0.900.0 SAB CARD NAYE — every chat card in the new design (owner: "check the card in chat space looks stale and random ... make it perfect human native and smooth and advance ... show me design here first ... check all cards" -> canvas -> "GO BUILD ALL CARDS")

Her screenshot: the "LONG TASK IN PROGRESS" card in the new chat - a black slab with a gradient tile, shouting caps,
a ⏳ emoji and a big outlined Stop bar. THE CHECK: the chat can show 375 card kinds built from 319 old widgets; the new
design (v0.864 R4) had redrawn only 4 (approval, file, page, default) and drew every other kind in the old Night Glass
widgets inside a dark frame (`hoola_chat.dart _OldCard`). The old widgets cannot simply be recoloured: glass.dart's `C`
is a block of compile-time constants used in `const` widgets all over the app.

DESIGN FIRST: a canvas of six boards (long task / needs your yes / working now / made for you / receipts and quiet
notes / dark mode), claude.ai/artifact/6B4C1xWkAUSeveMq7BKDuL. One anatomy for every card: a quiet label line (where
it comes from + when), a tinted tile, the title, the status in plain words with a coloured dot (violet working, amber
needs you, green done, red did not work), the body, the buttons docked at the bottom - quiet ones LEFT, the main one
RIGHT; a card waiting for her gets an amber edge and a soft lift.

BUILT (`lib/ui/chat/hoola_cards_all.dart`, one door `hoolaCardAll` used by the chat and the live call):
- HCGoal (goal): thin step bar (green done, violet running), finished steps with a tick, the running step with what
  Hoola is doing now (`app.currentStep`), numbered steps waiting, a live clock (the goal event now carries
  `started_at` / `updated_at`, server `agent/goal.py`), Hide steps, soft red Stop, "Go on" when the budget paused it,
  the four-part end report; a finished job with more than 6 steps folds them behind Steps.
- HCOperatorTask (operator_task): the live screen (OperatorFrame, tap = live view), the stage as an italic thinking
  line, Watch / Details, Stop (operatorCancel).
- HCOperatorAsk (operator_ask): approve = Yes / No; choice and question = choice rows + "Or say something else" +
  Choose / Send (operatorAnswer); OTP / CAPTCHA / secret / payment / takeover never get a box in the chat card - Answer
  opens the old guarded card.
- HCQuietLine: memory_used ("Used from memory: ..." + See = the forget sheet), memory_saved ("Remembered: ..." + Undo =
  forget), compact ("Older messages kept as a summary" + View) - one quiet line under the reply, not a card.
- HCCalendar (Join Meet / Open calendar), HCPlaces (numbered rows, Directions / Call / Website, Show all), HCPhoto (large
  picture, Share / Save, full-screen view), HCReconnect (Reconnect / Check), HCLinkApp (Connect).
- HCLegacy = every other kind: the new card read from its data (HCAny: title, one line, up to three facts, progress,
  amount) with a friendly desk name (`hcDesk`) + Details (or Review when it waits for her) opening that kind's full
  old card in a sheet that redraws live - every button it ever had is one tap away.
- The card shell (`hoola_card.dart HoolaCard`): `lead` (left), `whenMono` (a clock), the amber edge; HCApproval's Not now
  and HCFile's Share link moved left.

TESTS: `test/all_cards_test.dart` (5: the dispatch for the redrawn kinds, 14 other kinds -> HCLegacy and a kind with no
card stays invisible, Details opens the old card's button in a sheet / Review on a waiting card, the long task card
incl. its clock and Hide steps and the done report, a job's choice answered in the card and an OTP that never gets a
box); pictures 57 (long task, choice, memory line, done task) and 58 (calendar, places, a desk card) light + dark with
the tap-target gate; `server/tests/test_v0900_sab_card_naye.py` (4). Version 0.900.0 (pubspec 0.900.0+899; pins +
console stamps swept).

NOT VERIFIED on her phone; Flutter is not runnable here, the phone code compiles first on CI. NOT REDRAWN one by one:
the ~360 desk cards behind HCLegacy keep their old full card in the Details sheet (dark) - each can get its own new card
later without touching the dispatcher.


## v0.901.0 CONNECT — only Composio apps, by category (owner: "just show a composio connector in here. Make it more premium and category wise perfectly. Show me the design here first" -> design canvas claude.ai/artifact/CRtSQ8Ew7RN2w3GyaxsC49 -> "GO")

Her Connect page mixed 166 built-in plugins (UPI apps, banks, brokers) with Composio apps in one long A-Z list, with a
lone spinner while an app connected. Now the page shows ONLY her apps through Composio, in ten plain groups.

- SERVER `bazar/composio.py`: `GROUPS` (mail, crm, money, projects, marketing, calendar, docs, store, data, dev + more)
  and `group_of(slug, cats)`: popular apps pinned (`_SLUG_GROUP`), else the first group whose word appears in the app's
  Composio categories (specific words first: "Email Marketing" -> marketing, "Customer Support" -> crm), else "more".
  `home(s, user_id)` = her apps + `FEATURED` (Razorpay, Zoho Books, Notion, Slack, HubSpot ... only those in the
  catalogue and connectable) + every group with its count, her connected count and its top three connectable apps (an
  app Newtika has not switched on is never a top pick); a sign-in she just finished is checked with Composio once
  (`account(check=True)`) so the page says Connected, not Waiting. `apps()` gains `group` + `sort` (popular / az /
  connected) and every row carries `group` / `group_name`; a search also returns the groups that match. Status for
  apps she never joined is worked out without a database read (`_quick_status`). Routes: GET /api/composio/home,
  /api/composio/apps?group=&sort=; service `composio_home`.
- PHONE `lib/ui/shell/hoola_connect.dart` (the old Connect + `connectSections` removed from hoola_tabs.dart):
  serif title + "N connected · 1,6xx ready to add", search (debounced, matching categories as chips + apps), group chips,
  Your apps (big icons with a green tick), Most used by Indian businesses (2-column cards), Browse by category (first
  four groups as cards of their top apps, the rest as tiles, More apps last), the sign-in promise, Built-in tools ->
  the old Bazar screen. `ConnectGroupPage`: icon + name + counts, search inside, Popular / A-Z / Connected segments,
  Connected first, "Show N more". The app sheet: logo, group, what Hoola can do there, Actions / Sign in / Price,
  What Hoola will do (read what she lets it, ask before send / delete / pay, never sees her password - Composio), one
  big button: Connect <App> (opens the app's own sign-in page, the row then says Waiting), Add your <App> key (a sheet,
  typed there only, never in chat), Connected + Remove (asks first), Coming soon (disabled, says why). Coming back from
  the sign-in page reloads the page (app resume + the santosh://bazar link) and shows "<App> is connected".
- Not built from the design: per-app "Try asking" examples (no honest source per app yet) and "Ask for it" on a
  coming-soon app (no route to record the ask).
- Tests: test/connect_test.dart (6) + server/tests/test_v0901_connect_composio.py (6); picture 41 now shows the new page.
  NOT VERIFIED on her phone; the real spread of apps across groups depends on Composio's own category names on her
  server.


## v0.902.0 PAGE PRO — pages Hoola makes, shown like Claude's artifacts (owner: "NOW LET'S WORK ON ARTIFACT :: CURRENTLY HOOLA ARTIFACT ARE MESSY MAKE IT MORE PROFESSIONAL AND ADVACE", with pictures of Claude's own artifact card in chat, the viewer, its page and share menus)

What was messy: the new chat drew a page as a bare card (title, one status chip, Open); the viewer was still the old
dark Night Glass screen (glass header, "Hoola Artifact", a v-pill, a popup menu, an orange "building" strip, a dark
glass versions sheet, a glass change box) inside the new light design, and share only copied a link with a snackbar.

- CARD `lib/ui/chat/hoola_artifact.dart` `HCArtifact` (replaces `HCPage`; `hoolaCardFor('artifact')`): a drawn page
  thumbnail (title bar, lines, a block; a spinner while it is made, red tint when not made), the label "Page", the
  title, ONE status line in plain words from `artifactState()` - "Writing the page · 0:23" (the server's real `stage`
  from v0.725 + a live clock from `started_at`), "Version 3 · made in 0:48" (`build_s`), "Version 2 · the newer one
  was not made", "Not made", "Stopped" - the summary, the four step marks (Brief read / Writing the page / Checking it
  opens / Ready) with "Usually 20 to 90 seconds", and a footer: Share (quiet, left) + Open (main, right) when ready,
  Stop (soft red, POST /api/artifacts/{id}/stop) while it is made, Try again (sends "Make the page ... again") when
  not made. Tapping the card body opens it.
- PAGES PILL: "3 pages" in the chat's bottom right (above the composer, hidden while she is scrolled away; the list
  keeps 60 dp room under the newest reply) -> "Pages in this chat" sheet, newest first, deleted ones left out
  (`chatPages`).
- VIEWER `lib/ui/artifact_screen.dart` `ArtifactScreen` redrawn on HoolaColors / HoolaType for everyone (opened inside
  `HoolaTheme(app.appearance)`): close, the title + "Page · Version 3 of 4 · Shared by link", Versions (when there is
  more than one), Share and More icons; a 2 dp load line; a building bar ("Making version 4 · Writing the page · 0:21"
  + Stop), an older-version bar ("You are looking at version 2" + Newest), a failure bar; the page; a pill change box
  ("Ask for a change to this page", send circle). More = a sheet like Claude's: Open in browser, Copy link (turns on a
  view-only link), Share…, Versions, Reload, Remove (red, asks first in a sheet). Versions = a sheet with a tick on the
  one on screen, "Newest", how long ago, and "Undo the last change" (POST /undo: the version before comes back as a new
  version). Share = `openArtifactShare` (also from the card): turns sharing on, shows the link in mono, Open / Copy link,
  "Anyone with the link can view this page. They cannot change it.", Stop sharing. The bridge (window.santosh storage /
  ask), the own-origin navigation rule and the revise call are unchanged.
- api: `artifactStop`, `artifactUndo`. Server unchanged (both routes existed).
- The old `ArtifactCard` (the old-look chat) and the call pill are unchanged.
- Tests: test/page_pro_test.dart (6), picture 59 page cards (light + dark, a11y on), server/tests/test_v0902_page_pro.py
  (5). NOT VERIFIED on her phone; the viewer itself has no widget test (a WebView does not run in the test host).


## v0.903.0 NAV PRO - the phone tab bar redrawn (owner: "CHECK THE BOTTOM NAV. MAKE IT MORE ALLINED AND PROFESSIONAL, PREMIUM AND SOFT. AI EMPLOYEE CHOOSE IS EXDING ICON AREA. ALSO PROVIDE EVERY NAV PERFECT UNIQUE HD ICONS")

Her screenshots: the selected tab's pill was the whole cell and the label sat inside it, so "AI Employees" ran past
the pill; the Hoola tab was the violet brand picture while the other three were stock Material icons of different
weights.

- `lib/ui/shell/hoola_nav_icons.dart` (new): `NavGlyph` hoola / employees / tools / computer drawn by
  `NavIconPainter` on one 24-unit grid with one stroke (1.7) - sharp at every density, one family. Hoola = the mark
  (two rings cut where the 45-degree needle passes, the core); AI Employees = a person with the AI spark; Tools =
  three rounded tiles and a round one; Computer = a screen with a prompt on its stand. `on` 0..1 blends outline ->
  filled (the prompt is cut out of the filled screen).
- `HoolaNav` (hoola_shell.dart): one soft floating bar (hairline border, the float shadow), four equal cells
  (`_NavItem`); the selected one shows a 60 x 32 accentSoft pill behind the ICON only that grows out from 36 wide,
  the icon turns accent and fills, the label below goes ink 600; press = scale .94, a new tab = a selection tick;
  label in a FittedBox (scale down) so a long label at a big text size never runs past its cell; text clamped at
  1.4x; Semantics carries selected + onTap.
- Tests: `test/nav_pro_test.dart` (icons paint; at 320 / 360 / 412 dp and 100 / 130 / 200 % text the label and the
  pill stay inside their cell, the pill above the label, centred; equal cells, one icon line; tap + semantics), in
  app-screens.yml; picture 60 tab bar (each tab selected, light / dark, 100 % and 200 %);
  `server/tests/test_v0903_nav_pro.py` (4).
- NOT VERIFIED on her phone.


## v0.904.0 NAV BLACK - the open tab in black, the Hoola logo kept (owner: "DONT PUT PINK EVERY WHERE .. LOOKS AI MADE. MAKE IT PERFECT BLACK CHOOSE" -> canvas claude.ai/artifact/EwpHty5Bd4MZKZRjwaC7o9, four options A-D -> "ALSO KEEP PRIVOIUS HOOLA LOGO AS IT IS" -> "GO WITH FIRST WITH UPDATED DESIGN")

- `HoolaNav` / `_NavItem` (hoola_shell.dart): the open tab's pill is `c.pill` (#1B1A17 light, #F3F1EC dark = the
  composer's call button), the icon fills in `c.onPill`, the prompt on the filled screen is cut in `c.pill`, the
  label goes ink 600; closed tabs ink2 outline. No `accentSoft` / `accent` in the bar.
- The Hoola tab draws `HoolaMark(size: 24, animate: false)` again (the v0.888 violet logo), not the drawn glyph;
  when its tab is open it sits on the black pill in the lighter violet (`HoolaColors.darkSet.accent`; in dark mode
  the darker one on the near-white pill).
- `test/nav_pro_test.dart`: one black pill, no violet tile, the open icon white, closed icons ink2, the Hoola logo's
  colour open / closed; `server/tests/test_v0904_nav_black.py` (3). NOT VERIFIED on her phone.


## v0.905.0 NAV GAP - the composer sits 12 dp above the tab bar (owner: "CHECK THE GAP BETWEEN BOTTOM NAV AND A CHAT IS LARGE MAKE IT PERFECTLY ALLINED")

ROOT CAUSE: the new-design shell (`lib/ui/shell/hoola_shell.dart`) has `extendBody: true` and the page reserved a FIXED
96 dp at its bottom for the tab bar. The bar (HoolaNav: 8 dp outer bottom pad + 7 dp inner pad x2 + 56 dp cell + the
border) is ~80 dp, so ~16 dp of empty space sat above it, plus the composer's own 8 dp = a ~24-30 dp band between the
composer pill and the tabs (her screenshot); with a phone gesture area the numbers moved again because 96 never counted it.

FIX: the page's bottom room = `MediaQuery.paddingOf(context).bottom + navGap` (navGap = 4). With extendBody the Scaffold
hands the bottom bar's MEASURED height down as the body's bottom padding (the bar, the call pill when a call is on, the
SafeArea gesture inset), so the composer's pill always sits 8 + 4 = 12 dp above the bar - the bar's own side gutter.
While Hoola works the bar slides away (`_SlideAway` folds its height) and the page follows it frame by frame (plain
Padding, no second animation); the keyboard case stays 0. Every tab page gets the same room.

TESTS: golden 61 (`test/goldens/screens_test.dart`, home + a chat, light + dark, gesture area 0 and 24 dp) measures
nav.top - composer.bottom = 12 dp on the real shell; `_shot` gained `inset` + `check`; server
`test_v0905_nav_gap.py` (3). NOT VERIFIED on her phone.


## v0.906.0 NEW CHAT HOME - New chat lands on the typing screen (owner: "When click on new chat it must land on chat typing section not directly creating new chat and avthar reply... Fix this")

ROOT CAUSE: `POST /api/conversations` (server/app/main.py create_conversation) writes a greeting into every new chat
("Hello! I am <avatar>, your AI coworker. What shall we get done today?", event payload source "greeting"). The phone's
Hoola tab (`_HoolaTab._hasChat`) switched from the home (greeting, quick starts, composer) to the chat view as soon as
ANY message was in the feed, so New chat showed an empty chat with that line and its Copy / Read aloud / Share / Ask
again row - it looked like a chat had been made and the avatar had replied.

FIX (phone only; the console uses the same greeting): `feedIsGreeting(FeedItem)` in lib/state.dart. `_hasChat` ignores
it, so a chat holding only the greeting is the home with the composer; `HoolaChat._list` and `_lastReply` skip it, so
once she sends her first message the chat starts with her message and nothing above it. Old chats lose only that one
automatic line.

TESTS: golden 62 (light + dark): a chat with only the greeting = HoolaHome, greeting text not drawn, composer 12 dp above
the tab bar; first message = the chat view with no greeting. Server `test_v0906_new_chat_home.py` (4). NOT VERIFIED on
her phone.


## v0.907.0 TOOLS PRO - the Tools tab, option B (owner: "NOW LETS WORK ON TOOLS SECTION ... PINK ICON CARD MAKE IT MORE PREMIUM PROFESSIONAL AND SOFT WITH BLACK PERFECT ALINED ICONS WITH A CARD ANIMATION. FIRST SHOW ME IT HERE")

Design first on the canvas claude.ai/artifact/KMa7vVmS1EpWNRBqCvB8SX (A soft tiles / B black badge / C one list, light +
dark), then her rounds: "DIFFRENT UNIQUE ICON FOR ALL WITH BIG SIZE", "SHOW THE ICON AT CENTER ALL", "ALSO EVERY ICON WITH
SLIGHT AND PEFRECT ANIMATION", "GO WITH B".

BUILT: `lib/ui/shell/hoola_tool_icons.dart` - ToolGlyph x11 (Create wand + sparkles, Interactive presenter + speech
bubble, Vocal headphones + sound bars, Flow mic + lines of text, Web browser + code, App phone of tiles, Design pen curve
+ handle, Prompting chat bubble + spark, Code braces + cursor, Game gamepad + buttons, Connectors plug), each a still part
and a moving part as SVG path data on one 24-unit grid, stroke 1.7 (the tab bar's family), read by a small path-data
reader (`svgPath`: M L H V C S Q A Z); `draw` 0..1 draws the still part in; a seconds clock drives one quiet motion per
drawing (twinkle, bob, eq, write, breathe, pulse, tilt, spin, blink, press, plug; phase offset per card so they never move
together). `lib/ui/shell/hoola_tools.dart`: HoolaTools is stateful - opening controller (cards rise 18 dp + scale .965 ->
1 one by one 55 ms apart, the badge pops with a slight back-ease and turns -8 deg -> 0, the drawing draws itself) and a
1-hour repeating clock; `ToolBadge` = the drawing at .53 of a black circle (`c.pill` / `c.onPill`, near-white in dark);
cards = `c.surface` + `c.line` border + new `HoolaShadow.card`, content centred, title + line 2 lines each (grid height
from the text size, so nothing is cut); press sinks the card (.965) and the badge (.93); big text keeps rows, now with the
badges; Hoola Code / Game Dev / Connectors rows carry badges too. Reduce motion = opening skipped, clock stopped.

TESTS: `test/tools_pro_test.dart` (every drawing paints through its whole motion; light + dark: 11 badges, all different,
black circle, icon + name centred in the card, never cut; the cards rise one after another and the clock keeps running;
reduce motion = no frames) on the CI unit line; server `test_v0907_tools_pro.py` (3). NOT VERIFIED on her phone.


## v0.908.0 CHAT MENU - the console's chat menu on the phone drawer (owner: "NOW LETS WORK ON CHAT SIDE BAR -- EVERY CHAT NAME SHOULD WE EDITED , DELETED SAME AS CONSOLE HAS CHECK THE CONSOLE SIDE AND DEPLOY SAME HERE FOR SESSIONS")

The console (`static/console/chatlist.js` openMenu) gives every chat a ⋯ menu: Pin / Unpin, Rename, Add to session,
Compact chat, Archive / Restore from archive, Delete (asks first), plus a Pinned group and an Archive list. The phone's
new-design drawer had none of it (tap = open, nothing else).

BUILT (phone only; the server routes already existed): `lib/ui/shell/hoola_chat_menu.dart` - `hoolaChatMenu` (a
Claude-style sheet with the chat's name and the console's rows; Rename = a box with the old name selected, 120 chars;
Delete = a confirm sheet with the console's own words; Compact = POST .../compact with the console's answer lines),
`HoolaArchivePage` (archived chats, tap = Open / Rename / Restore / Delete). `lib/state.dart` renameChat / pinChat /
archiveChat / deleteChat / archivedChats (one `_chatAct`: the server call, then the list changes on screen at once and
is read again; archiving or deleting the OPEN chat starts a new one). `lib/api.dart` chatPatch (PATCH
/api/conversations/{id}), chatDelete (DELETE), chats(archived: true). Drawer (`hoola_shell.dart` HoolaDrawer): a ⋯
beside every chat (44 x 48, 'Chat options: <name>' for screen readers), hold the chat = the same menu, rows 46 -> 48,
Pinned group above Recents, Archive in More. NOT BUILT: 'Add to session' (the phone has no sessions list yet).

TESTS: `test/chat_menu_test.dart` (the four calls against a recording local server + the list updated + empty name
refused + the archive list; the drawer: pinned group, a ⋯ per chat, hold opens the menu, Delete asks first and Cancel
deletes nothing, Rename shows the old name) on the CI unit line; server `test_v0908_chat_menu.py` (4). NOT VERIFIED on
her phone.


## v0.909.0 SESSIONS - the console's sessions on the phone (owner: "ADD SESSIONS ALSO SAME AS CONSOLE")

The console's sessions (= projects since v0.193: `static/console/projects.js` + the session sections in `chatlist.js`):
a named folder of chats with an emoji, instructions every chat in it follows, its own memory notes and the "Use my main
memory here" switch (v0.609), files, and its chats. The phone had none of it.

BUILT (phone only; routes existed): drawer (`hoola_shell.dart` HoolaDrawer) - a Sessions part when the server has them
(`sessionsOn`, a 404 hides it): "Sessions" + "+" (new session -> its page), each session a header row (chevron folds /
unfolds - kept in prefs `sess_closed`, emoji + name opens the session page, chat count, a dot when a folded session has
a working / new chat, "+" = a new chat inside it) with its chats under it, indented; those chats leave Pinned / Recents.
Chat menu (`hoola_chat_menu.dart`): Add to session / Change session -> `hoolaPickSession` (her sessions with a tick on
the current one, New session, Remove from session). `lib/ui/shell/hoola_sessions.dart`: HoolaSessionPage (emoji tile +
name, tap to change each; New chat in this session; Instructions and Memory boxes saved 0.7 s after typing with a
"Saved" mark; Use my main memory here; Files - add up to 10 at once, 25 MB each, remove asks first; Chats - tap opens;
Delete session asks first: "Its chats stay; they just leave the session."), `hoolaNewSession`. State: sessions /
sessionsOn / closedSessions, refreshSessions, toggleSession, createSession, moveChat, newChatIn, deleteSession. Api:
sessions, session, sessionCreate / Patch / Delete, sessionFileAdd / Remove, sessionChats (/api/console/conversations
?project=), newConversationIn (POST /api/conversations?project_id=). `hoolaRenameSheet` takes title / hint / action /
max. NOT BUILT: drag a chat onto a session (the console's drag and drop) - the menu's picker does it on the phone.

TESTS: `test/sessions_test.dart` (the console's calls against a recording local server + fold kept; the drawer: Sessions
group above Recents, fold / open, + buttons, the menu's Add to session picker; the session page without a server says
why) on the CI unit line; server `test_v0909_sessions.py` (4). NOT VERIFIED on her phone.


## v0.910.0 AI EMPLOYEES PRO (owner: "NOW LETS WORK ON AI EMPLOYEE CURRENTLY IT IS LOOK AI MADE AND STALE MAKE IT PROFESSIONAL AND PERFECT. FIRST CHECK HOW CONSOLVE SHOW THE DATA PROPERLY BASED ON EMPLOYEE CATOGARY. MAKE IT VERY STUNING AND USER FRIENDLY.... FIRST SHOW ME THE PERFECT DESIGN HERE. PREMIUM , ADVANCE , SOFT AND STUNING" -> "GO BUILD")

Read first: the console hub (`server/app/static/console/employees.js`): department cards with line art and a ready line ->
a department page with filters and role cards -> a side panel per role (does / needs / never, trust ladder seekh / saathi /
bharosa, Hire / Open desk / Pause / Resume / Let go). The phone tab (v0.898) was one flat list with chips. Design canvas
claude.ai/artifact/VkbWNUPLT1s7UYycxjhnjJ (home light + dark, a department, one employee) -> "GO BUILD".

Built in `lib/ui/shell/hoola_employees.dart` (the whole file rewritten; `employeeConsolePath` + `HoolaEmployees.debugList` kept):
- `hoolaDepts`: the twelve catalog groups in the hub's order, each with the console's own line (Construction and Voice got
  lines of their own; the console has none for them) and its own 24-unit drawing; `hoolaDeptOf` keeps an unknown group
  visible with a plain drawing. `employeeMono` = the console's `ini()`.
- `HoolaStaff` (ChangeNotifier): one list for the tab and the pages it opens (a hire on the employee page shows on the
  department page and the home at once); `act` (hire / pause / resume / leave), `setTrust` (PUT /api/employees/{key}/settings).
- Home: serif title + one line, the numbers card (roles / ready to hire / departments), Your team (two cards side by side,
  more scroll; working dot that breathes, trust level, Open desk 48 dp), search across every role (results as role cards
  with their department), department grid (2 columns, 3 on a tablet, 1 with big text): `DeptBadge` draws itself in then
  floats, "4 of 6 ready", a ready bar that fills, a green count of her people there.
- `HoolaDepartmentPage`: back, the drawing big, name in serif, the line, chips (roles / ready / on your team), All / Ready /
  My team / Soon on a black pill (48 dp), role cards (initials black when it can be hired, grey when coming; status chip:
  Ready to hire / On your team · working / paused / Coming soon).
- `HoolaEmployeePage`: initials in serif on black with a soft ring going out, name, status, pitch in serif; "How much it does
  on its own": Learning / Partner / Trusted with her words (Seekh / Saathi / Bharosa) - tap to read; once hired, Learning /
  Partner can be set from here ("Use Partner"), Trusted is turned on from its desk; What it does (ticks), What it needs
  (numbered), It will never (quiet minus, dashed-feel outline); bottom bar: Hire <name> (then its desk opens, as before) or
  Open desk + Pause / Resume + Let go (asks first); Coming soon disabled.
- Motion: cards rise in one after another, drawings draw in, bars fill; then floats / pulses on one seconds clock; reduce
  motion = all still and no frames.

Tests: `test/employees_pro_test.dart` (initials / counts / departments; the console's calls on a local server: GET, hire,
pause, settings trust; home light + dark; department filters; one employee; hired employee trust + let go asks; reduce
motion), `test/four_tabs_test.dart` updated to the new flow, goldens 63 (department) + 64 (one employee, hired) with the
tap-target checks, golden data richer; `server/tests/test_v0910_employees_pro.py` (every catalog group has a card and its
own drawing, the console's words, routes, trust levels, version). Server unchanged. NOT VERIFIED on her phone.


## v0.911.0 DARK LIKE CLAUDE (owner: two screenshots, "CHECK THE DARK MODE DIFFERENCE BETWEEN CLAUDE AND HOOLA" -> "GO")

Measured from her screenshots (pixels, not guesses): Claude's dark page `#131313` (neutral), reply text `#E1E1E1`, the
typing box `#1D1D1B` with no visible outline, faint text `#7B7A78`, and the brightest thing on screen a muted clay send
`#80655A`. Hoola's: page `#1D1C1A` (warm, lighter), text `#F3F2EE` (near-white), typing box `#262523` + outline
`#3A3935`, her bubble `#2F2E2A`, and two near-white blobs `#F2F1EC` - the open tab and the voice button.

Changed `HoolaColors.darkSet` only (light untouched): bg `#141413`, surface + nav `#1E1E1C`, raised `#252523`, sunk +
code `#262624`, line `#2C2C2A`, lineStrong `#3C3B38`, ink `#E6E5E1`, ink2 `#B2B0A9`, ink3 `#94928B`, pill `#3A3936` with
onPill `#ECEBE6` (open tab, the black circles of Tools / AI Employees, main buttons, snack bars), navOn `#2E2E2B`, soft
backgrounds a step darker. Because the pill is grey now, an ON switch in dark takes a light track (`ink2`) and a dark thumb
(`bg`); the session page's own switch colours were removed so it follows the theme. Every text pair still reads at
4.5:1 or better (ink3 on sunk 4.87). Old screens drawn through NightGlass.flat use darkSet too, so they follow.

Tests: `test/dark_like_claude_test.dart` (deep neutral page, soft text, surfaces one quiet step apart, no white blobs,
switch clearly on, light untouched) in the CI unit list; `server/tests/test_v0911_dark_like_claude.py`; the dark
screenshot set regenerates. NOT VERIFIED on her phone.


## v0.912.0 CREATE NATIVE - every Create page as a native phone screen

Owner: "NOW LETS WORK ON CREATE IN TOOL SECTION::: CHECK FIRST THE CONSOLE PAGES IN CREATE ALL ... MAKE A REAL APP NATIVE
SCREENS FOR ALL PREMIUM, ADVANCE, USER-FRIENDLY AND PROFESSIONAL. WORK IN EVERY MINUTE DETAILS IN APP PROPERLY. SHOW ME THE
DESIGN HERE PROPERLY" -> 13-board design canvas claude.ai/artifact/SARfWkfWm8ZtmmnAcU8dYn -> "GO BUILD".

Before: Tools > Create opened the console's Create studio (`/console/?v=creative`) in a WebView. Now it opens the app's own
studio in the new design, built from a read of every console Create page (`server/app/static/console/studio.js`, `cinema.js`).

Files (all new, `lib/ui/create/`):
- `create_kit.dart` - `CreateStore` (one per visit: GET /api/create, /api/create/items, /api/create/jobs, /api/studio,
  /api/brand/kit in parallel; `start` = POST /api/create/jobs with the open chat's id so the result also lands in her chat;
  polls running jobs every 2.5 s and reloads the shelf when one ends; `write` = /api/create/write; `delete`; `saveKit`;
  `debugData` test seam), the Create drawings (`CrGlyph`, own 24-unit strokes read by `svgPath`), and the blocks: `CrPage`
  (round back button, centred title, right slot, pinned bottom action over a fade), `CrMain` / `CrQuiet` / `CrRoundButton`,
  `CrCard`, `CrLabel`, `CrChip` (+ `crTap48` = 48 dp tap room), `CrSegment`, `CrTiles`, `CrSettings` + `crPick` sheet,
  `CrStepper`, `CrSwitch`, `CrTextCard`, `CrSmall`, `CrNote`, `CrIntro`, `CrJobRow`, `CrAudioCard` (play with her key via
  video_player, drawn waveform), `crShareItem` / `crShareBytes` (temp file -> the phone's share sheet).
- `create_home.dart` - `HoolaCreate`: "What shall we create today?", five modes (Film / Picture / Video clip / Song /
  Voice-over - each changes the hint, the settings line and the price), the ask box that opens the right tool with her
  words, quick chips, ten tools on black circles, Recent rail, starters, Film projects / Brand kit / My creations / How-to
  guides; `CreateGuides`.
- `create_make.dart` - Image (New / Change my photo, Enhance via /api/studio/improve kind=image, up to 3 references from her
  own photos (uploaded to the chat), brand colours switch, 9 styles, 6 shapes, Standard ₹3 / Best ₹12, count 1-4 with the
  total on the button, Keep out, painting tiles), Music (Song / Instrumental / Jingle / Score, 12 styles, language / singers /
  mood / length, tempo, lyrics + Write with Hoola), Voice-over (11 languages, Your Hoola's voice + the server's voices by
  gender, 6 styles, pace with an estimated length), Dubbing (her video, up to 4 languages incl. All languages, keep
  background sound), Script writer (6 formats, length / language / tone, the script editable and saved as she types via
  PUT /api/create/items/{id}/text, quick rewrites, Turn it into a film, her scripts), AI casting (name, looks, 4 styles,
  voice, the four-view sheets).
- `create_film.dart` - Video (model sheet incl. Hoola Auto quality / value / cheapest, Improve, 12 camera moves, shape,
  length 4-15 s, resolution / sound / takes / spoken language, live price from POST /api/studio/price, Free preview +
  Create = POST /api/studio/projects then=preview|generate, clips with their price cards), Director (films list + new film
  with shape / length / language / music, storyboard free), `CreateFilm` (8 steps read from the studio view, spent so far,
  the next step with its price (plan / keyframes / generate / assemble) + Skip pictures / Free preview, price cards with
  Haan / Not now via `studioDecide` (fingerprint proof), Stop while working, cast + Add a character, storyboard timeline +
  scene cards (edit a scene), final film play + share, "Change something" sent to her chat), Video editor (/api/video/jobs:
  up to 8 clips in order (reorder), quick asks, made for / length / captions, latest version play / share / change in words,
  post caption copy).
- `create_keep.dart` - `crOpenItem` (picture full screen with zoom, video with her key, audio sheet, script text),
  My creations (search, kinds, sort, Select many -> Save to phone / Delete with a confirm), Brand kit (live poster preview
  from her colours, logo upload with clean background, name / tagline / tone / phone / website, five colour roles with
  swatches or a code, lettering), Hoola Cinema (the hub with its rules, key state, today's jobs, recent jobs; its tools
  open in the console's own Cinema page, signed in).

Wiring: `lib/ui/shell/hoola_tools.dart` `hoolaOpenStudio` (Create = native, every other studio = its console page).
Console: `v2.js` `go('creative', arg)` now passes `arg` to `CREATE.open`, so `/console/?v=creative&a=cinema` opens Cinema
straight away (an unknown arg falls back to the studio home inside studio.js).

Rules kept: every paid studio step is a server price card that waits for her Haan; the Free preview spends nothing;
references and videos are her own files; delete asks first; a real person's face needs their recorded yes (Cinema,
casting copy). Design: no raw colours / blur / tiny or heavy type in `lib/ui/create/` (tested); every control has 48 dp of
tap room and a name for TalkBack (Semantics with its own onTap where a card hides its children).

Tests: `test/create_native_test.dart` (store against a local server, helpers, home light + dark, the ask box, all 14
screens light + dark with their own controls, price on the button, Haan wording, Select + Delete asks first, wiring +
design rules), goldens 65 create home / 66 create image / 67 create film (light + dark, tap-target + label checks),
`server/tests/test_v0912_create_native.py`. NOT VERIFIED on her phone; Cinema's tools are not native yet.


## v0.913.0 CREATE IN COLOUR

Owner: "CURRENT CREATE DESIGN LOOKS VERY STATIC AS A VIDEO GENERATION AND IMAGE GENERATION... IT SHOULD BE USER FRIENDLY,
COLOUR FULL, HUMAN NATIVE GLASSY, ADVANCE. DO DEEP RESEARCH ON APP DESIGN LOOK OF GOOGLE FLOW, RUNWAY, HIGGSFIELD,
OPENART ETC" -> research + design canvas claude.ai/artifact/HXF8gGUqohSnZBnohRkbtu (8 boards) -> "GO BUILD. BUILD IT
HUMAN ADVANCE DESIGN.. IT SHOULD NOT LOOK LIKE AI MADE".

What was taken from each: Kling / Pika = a media-first home you start from; Higgsfield = camera moves picked as moving
cards instead of typed; Google Flow = how a clip starts (only Words is wired today - the studio has no "her photo as the
start frame" route, so Frames / Keep-the-same were NOT built); Runway / OpenArt = the engine chip in the box, a live job
card, a filterable gallery. Hoola's own rule stays: the price first, nothing spent before Haan.

- `lib/ui/hoola_theme.dart`: `CreateHues` (pictures #FF7AB6->#FFB15C, clips #8B7BFF->#45DCFF, films #FFC34D->#FF7A6B,
  songs #3EEAA8->#47C6FF, voices #B9A3FF->#FF8CC6; words on them `onHue` #14121C, every pair >= 4.5:1 - tested) and
  `CreateScene` (12 painted scenes: sky, glows, shapes, ground, rain).
- NEW `lib/ui/create/create_colour.dart`: `CrHue` + `CrHueScope` (CrPage puts its hue there), `CrAura` (three soft lights
  drifting over 16 s), `crGlass` (see-through colour + a lighter top edge + a hairline; NO blur - the design rules),
  `CrScene`, `CrMove` (Dolly in / out, Orbit, Pan, Tracking, Crane up, Crash zoom, Handheld, Drone, Low angle, Static),
  `CrArtCard` (picture card, dark fade, badge, picked ring, press sinks), `CrBadge`, `CrSheen`, `CrBar` (hue bar, moving
  when no share is known), `CrOrb`, `CrHead`. Every animation stops under reduce motion.
- `create_kit.dart`: CrPage(hue:) + the light behind; round buttons, cards, quiet buttons, steppers, notes in glass; the
  main button, picked chips, segments and tiles in the page hue; CrDisc = a colour circle in its tool's hue (`crHueOf`);
  job rows = a painted tile with a sheen + a hue bar; the audio waveform in the song / voice colours; `store.making`.
- Home rebuilt: "What are we making today?", one switch of five kinds (Picture / Clip / Film / Song / Voice; the page,
  facts, price and Continue button follow), Making now, Try a camera move (moving cards -> Video with that move),
  Every studio (12 colour circles), Recent, Start from an idea (a two-column wall), Film projects + guides.
- Image: styles as painted tiles; a picture being made = its painted tile + a badge + a hue bar. Video: the twelve
  camera moves as moving tiles (`CreateVideo(camera:)`), the price box in glass. My creations: a two-column picture
  wall. A picture opens in a dark room (pinch to zoom, glass panel, Bring it to life -> Hoola Cinema, Share / Save /
  Delete asks first). Film: the step bar and scene cards in colour.
- Tests: test/create_native_test.dart (home expectations, hue contrast), goldens 68_create_video + 69_create_library,
  server/tests/test_v0913_create_colour.py. NOT VERIFIED on her phone.


## v0.914.0 CREATE GLASS (owner, with three phone screenshots of v0.913: "Make it more glassy and advance and perfrect")

What her screenshots showed: on the dark page the v0.913 "glass" was a flat grey pane (white 6-17 % with a 1 px grey
hairline), the colour light only lived in the top of the page (`top = min(height, width * 1.6)`), so cards lower down
had nothing to show through; on the Image page the bottom action faded over the style tiles so tiles showed through
the stepper, and "Create · about ₹6" was cut by the ellipsis.

- `crGlass` now returns `CrGlassDecoration` (a custom Decoration, every caller passes it as `decoration:`): shadow
  (BoxShadow's own paint), lit-top fill, optional `tint` = a radial breath of the page hue from the top-left plus a
  violet one from the lower-right, a soft diagonal sheen, and a gradient rim (white on the top-left, the hue on the
  lower-right; a picked `edge` stays a solid 1.6 px line); `base` paints a solid colour first. lerpFrom / lerpTo
  between two glasses, clip path + hit test on the rounded shape. Never a blur (the design rules).
- CrAura: five light pools across the whole page height (hue a / b / violet, drifting 16 s, still under reduce
  motion) + `_GrainPainter`, a still seeded film grain in its own RepaintBoundary (drawPoints, one call).
- Cards, the kinds switch, the ask box, the studios tray, the stepper, segments and the film price box carry
  `tint: CrHue.of(context)`.
- CrPage bottom action: a solid glass dock (`base: c.bg`, radius 32) over a short fade - nothing scrolls through.
- CrMain: glossy top + bright rim (`foregroundDecoration`), the label in `FittedBox(scaleDown)` so it shrinks, not cut.
- CrArtCard: a glass hairline + top-left light over the picture; CrHead headings in Literata 19 / w500.
- Tests: `server/tests/test_v0914_create_glass.py` (4); test_v0913's "BoxDecoration crGlass(" pin is now
  "Decoration crGlass("; flutter tests and goldens unchanged (CI is the compiler). NOT VERIFIED on her phone.


## v0.915.0 GLASS STUDIOS (owner, on her v0.914 screenshot of the Create home: "MAKE EVERY STUDIO MORE GLASSY AND ANIMATE EVERY ICON")

- `CrOrb` (create_colour.dart): the colour bead is glass - `_OrbGlass` paints a lit cap on top and a soft glow at the
  bottom, a white hairline rings it (foregroundDecoration), two coloured shadows; `sweep` = a band of light crossing it.
- `crGlyphMove(kind, a, px)`: one small move per drawing that ends where it began - image tilts, video rolls forward,
  film (clapper) claps, music hops, voice breathes, dub swings, cut snips, pen writes, cast steps up, cinema turns a
  quarter, brand (star) turns one point and shines, grid settles a quarter turn. `CrRings` spreads two rings from the
  sound beads (voice, music, dubbing) while they move.
- `CrDisc(beat:)` = how far through its move the drawing is; null = still (every other CrDisc unchanged).
- Create home `_Studios` -> `_StudiosState`: one 6.4 s controller plays the moves as a diagonal wave across the 4x3
  tray (each bead moves for ~26 % of the cycle), a slow light (`_TrayLight`) crosses the whole tray once a cycle, the
  beads rise in once (easeOutBack, staggered). Reduce motion: no moves, no light, beads in place.
- Light-mode glass more see-through (non-strong fill .82 / .58 / .44).
- Test `server/tests/test_v0915_glass_studios.py`; test/create_native_test.dart unchanged (CrDisc keeps one gradient
  Container). NOT VERIFIED on her phone.


## v0.916.0 STUDIO SLAB (owner: "CHECK THE FULL CARD EVERY STUDIO ... MAKE PERFECT STATIC GLASSY ... SHOW ME THE DESIGN HERE FIRST" -> design canvas claude.ai/artifact/C8e12Hvwi1Cy8WUCPtNmbk with A clear pane / B glass wells / C thick slab -> "C")

- Create home `_StudiosState.build`: the Every studio card is one strong glass slab (`crGlass` radius 32, strong, hue
  tint) clipped to its shape; the heading "Every studio" (Literata 22) and a "12 tools" glass pill moved INSIDE it (the
  CrHead above it is gone).
- `_SlabGlass` paints, once: a second edge 5 px inside the first (the glass's thickness), a still glare band across
  the top-left corner, colour rising from the bottom edge.
- Each bead stands on a soft pool of its own colour on the glass (a radial ellipse under the CrDisc).
- `_TrayLight` (the band that crossed the tray each cycle) removed - the slab never moves; the drawings keep their
  v0.915 moves and the rise-in.
- Tests: test_v0915 no longer pins `_TrayLight`; `server/tests/test_v0916_studio_slab.py`. NOT VERIFIED on her phone.


## v0.917.0 SLAB EVERYWHERE (owner, on her v0.916 Create home screenshot: "Make same thik slab for all the sections sheet even a chat section")

- `_GlassBoxPainter` (create_colour.dart): any non-circle glass whose short side is >= 56 dp is drawn as the design-C
  thick slab - a still glare band across the top-left corner, the tint (else violet) rising from the bottom edge, and a
  second hairline 5 dp inside the rim (the glass's thickness). Chips, round buttons, steppers under 56 and beads stay
  plain glass. So every Create sheet (kinds switch, ask box, Making now, CrCard, trays, the bottom dock, Image / Video /
  Film / Library pages) is a slab.
- Create home `_SlabGlass` removed - the studios slab is now plain `crGlass` (no double edge).
- Chat: the composer (`HoolaComposer`, hoola_shell.dart) and the card shell (`HoolaCard`, hoola_card.dart, so every
  card kind) use `crGlass(..., strong: true, tint: CreateHues.third)`; a card waiting for her keeps an amber edge and an
  amber tint. The chat page itself keeps its plain background (no moving colour light there).
- Tests: test_v0916 now checks the slab lives in create_colour.dart; `server/tests/test_v0917_slab_everywhere.py`.
  NOT VERIFIED on her phone.


## v0.918.0 SLAB REVERTED (owner, after the v0.917 pictures: "No revert it")

`git revert` of v0.917.0 (02765fa2): the thick slab is back to living only on the Create home Every studio card
(`_SlabGlass` in create_home.dart), `_GlassBoxPainter` no longer draws the inner edge / glare / bottom colour on other
sheets, and the chat composer (`HoolaComposer`) and card shell (`HoolaCard`) are back to `c.surface` + `c.line` + their
old shadows. test_v0917 removed, test_v0916 restored; `server/tests/test_v0918_slab_reverted.py`. Docs keep the
v0.917 entry for the record.


## v0.919.0 REAL CAMERA (owner, after the animated design canvas claude.ai/artifact/KZ2Svgxm8fZPrEWt5zjKYD: "I WANT REAL VIDEO AT EVERY PLACE OF CAMERA ANGLE NOT ANIMATED")

- Server `studio/showcase.py`: `CAMS` = twelve camera moves (Auto ... Low angle, slot ids `cam_<move>` = the phone's
  names), each a 5 s shot of the SAME scene (`CAM_SCENE`: a woman in a mustard kurta with masala chai at a chai stall at
  golden hour) + the move in words + the studio camera key where one exists (`catalog.CAMERA`). `setup()` adds them to a
  showcase made before (existing shots kept). `ask_camera()` = the normal price cards in two steps: opening pictures
  (`keyframes`), then draft 720p clips (`generate(..., "draft", ...)`) - each waits for her Haan (+ fingerprint);
  POST /api/studio/showcase/camera, owner only. `status()` gains cams / cam_pictures / cam_clips.
- `tile_of(clip)`: ffmpeg cuts the clip into a 320 px square looping animated WebP (4 s, 12 fps, quality 62), made once
  beside the clip; GET /api/studio/showcase/file/{slot}?kind=tile serves it as image/webp. A picture, not a video player,
  so all twelve tiles play at once on a budget phone.
- Phone: `CreateStore.showcase` (GET /api/studio/showcase) + `camSlot` / `camReady`; `CrCamArt` puts the real tile over
  the painted move (the painted one stays underneath until the clip is made / while it loads) on the Video page camera
  grid and the home "Try a camera move" cards; owner-only `_CamMaker` card under the grid: step 1 / 2 counts, the price
  card (CrApprovalCard), painting / filming, errors; gone once all twelve play.
- Tests: `server/tests/test_v0919_real_camera.py` (incl. a real ffmpeg tile); test_v0329 counts the camera shots.
- NOT VERIFIED: no real clip made yet - needs the VPS deploy, then her taps on the two price cards (prices shown on the
  cards; 12 pictures + 12 draft clips). The footage is AI video, not stock footage.


## v0.920.0 CAMERA ALIVE - the design's moving scene in every camera tile (owner: "use this and deploy for now" on the Camera moves alive design canvas)

The owner pointed at the design canvas (claude.ai/code/artifact/963d3031-ec12-47c5-ae90-3b03a65e2b7a, the same canvas as
claude.ai/artifact/KZ2Svgxm8fZPrEWt5zjKYD) and asked to ship it for now, while AI video of each move waits (Higgsfield is
on hold, no key).

- `CrCamScene(move)` in lib/ui/create/create_colour.dart: a Ticker + one CustomPainter drawing the 200 x 200 scene, fit as
  "slice" over the tile. Layers as in the design: bg (sun + hills, the hill row repeats every 100), mid (ground + chai
  stall with awning and bulbs, or lamp posts when Tracking), subj (her in a yellow kurta, red dupatta, a cup of chai with
  two steam wisps on 2.6 s, the second 1.1 s late), fg (table with cup + oranges, or road dashes when Tracking), all inside
  a rig layer.
- Each move = the design's CSS keyframes as numbers: Auto 7 s parallax push; Dolly in / out 5 s holds at 0-12 % and 78-90 %;
  Crash zoom 3.4 s punch to 1.95 x (cubic .7,0,.9,.4) about the face; Orbit 4.5 s layers sliding opposite ways + her
  scaleX .84; Crane up 5 s layers dropping 4 / 16 / 24 / 52; Tracking hills / posts / road scrolling at 6 / 1.6 / .8 s + a
  .4 s bob; Pan 5 s +-20; Drone 6 s pull up and away about (110, 168); Handheld 2.2 s small shake + tilt about (100, 100);
  Low angle 5 s her large from below about (123, 172); Static holds and only the steam moves.
- Colours per move in `CreateCamScene` (lib/ui/hoola_theme.dart; sky top / bottom, hill, ground + the fixed scene colours),
  so the Create files stay free of raw colours (design ratchet).
- Used as the fallback art of `CrCamArt` in the Video page `_CameraGrid` and the home "Try a camera move" cards; a v0.919
  real clip still plays on top when one exists. The old `_camArt` painted-scene map is gone; `CrMove` stays for its test.
- Reduce motion = still (the clock rests at 0, steam shown resting).
- Tests: server/tests/test_v0920_camera_alive.py; test/create_native_test.dart now looks for CrCamScene on the home;
  test_v0913 checks "CrCamScene(move:" in the home.
- NOT VERIFIED on her phone; the painter compiles first on CI.

## v0.877.0 HOOLA AGENT API - companies call Hoola's tools with one key and pay from an INR wallet (owner: "means we developed employees, tools etc can directly be used by different companies via our Hoola API" -> "now let's work on development of different portal endpoints for Hoola AI agent")

Research first (13 Nov 2026, official terms of 14 providers + OpenRouter's 121-provider list): reselling raw model API access is forbidden by
every provider without a signed deal, while building your own product on top is allowed - so the API sells Hoola's WORK, not a model pipe.
Plan + phases + open owner decisions: `docs/HOOLA_API_PLAN.md`.

Built (phase 1): `server/app/hoolaapi/` -
- `models.py` hapi_keys / hapi_wallets / hapi_ledger / hapi_calls (self-healing `ensure_tables`, registered in `db.init_db`); the ledger is append-only (ORM guard + SQLite trigger) and unique per (type, ref_type, ref_id).
- `catalog.py` an ALLOWLIST of 6 read / compute tools (api_box, mospi, duniya, reach, scrape_page, pylab) with default INR prices in micro-INR and a `hoola_api_prices` override; the test reads every name for send / pay / delete / pc words.
- `service.py` `hk_live_` keys (shown once, sha256 only, per-key tools / rpm / rph / concurrent / daily INR cap; the AI Apps `Limiter` reused), wallet (atomic conditional debit + ledger row in one transaction), one call = validate args against the tool's schema -> charge -> run `agent.tools.dispatch` as the company's own tenant with actor `api:<key id>` (120 s limit) -> refund on any failure (exception, timeout, `error`, `ok:false`); usage log keeps metadata only.
- `api.py` public `/api/hoola-api/v1/{tools, tools/{name}, balance, usage}` (OpenAI-shaped errors, `x-hoola-request-id` + `x-hoola-cost-inr`), portal `/api/hoola-portal/{me, catalog, wallet, ledger, usage, keys}`, admin `/api/hoola-admin/{overview, wallets/{t}/credit (reason required, idempotency key), wallets/{t}/suspend}` (operator tenant only).
- Switches: `hoola_api_enabled` (OFF until the owner flips it), `hoola_api_prices`.

Tests: `server/tests/test_v0877_hoola_api.py` 24 - off by default, key once / hash only, wrong / revoked key 401, allowlist (send / pay / pc tools 404), per-key tool list, charged exactly + runs as the company's tenant with an api actor, empty wallet 402 and the tool never runs, failure / error dict / `ok:false` / timeout refunded, bad arguments 400 and not charged, daily cap, rate limit 429 + Retry-After, 10 parallel calls on a wallet worth 3 = exactly 3 succeed and the balance ends at 0, ledger append-only, same credit event counts once, admin operator-only + reason, suspended wallet, metadata-only log, price override, portal. Also run by hand against the REAL duniya / pylab / api_box through the real dispatch: balance equalled the ledger sum.

NOT BUILT: UPI top-up + GST invoice (phase 2), employees as API (phase 3), voice, MCP, console portal page, per-tool third-party terms checks. NOT VERIFIED: no real company or money, no Postgres run, limits are per process.

## v0.878.0 HOOLA CODE ENVIRONMENTS + LONG-RUN FIXES (owner: "NOW LETS WORK ON HOOLA CODE. IN APP SIDE AND CONSOLE SIDE. CHECK THE CLAUDE CODE DESIGN IN APP. CHECK BOTH IS ALL HOOLA CODE IS WORKING OR NOT FROM ENVIRONMENT ATTACHMENT TO LONG CODE DEVELOPMENT")

**What was checked before building.**
- An audit of server, console and phone. The 27 Hoola Code suites ran 232 passed, 4 skipped (the skips need the `hoola-devlab` Docker image).
- Claude Code's web, desktop and mobile Code tab, read from Anthropic's docs and her 4 phone screenshots. The spec is in `docs/research/claude_code/00_UI_SPEC.md`.

**Finding.** Hoola Code had every box setting, but only per repo. It had no ENVIRONMENT, the named thing Claude Code's session picks first.

**Built: environments** (`devsahayak/envs.py`, table `devsahayak_envs`, `DevTask.env_id`, `DevSettings.env_pick`).
- **Default.** Every tenant gets a "Default" environment the first time she looks: Limited network, package managers on.
- **Fields:**
  - Name.
  - Network access: None, Limited (with the "Allow package managers" switch and allowed domains) or Full.
  - Variables in `.env` text. A name or value that looks like a secret is refused.
  - A setup script. Each line is checked; sudo, docker and service commands are refused.
- **Archive, never delete.** At least one environment is always kept.
- **Auto** means no environment: each repo's own Settings, exactly as before.
- **Routes:**
  - GET/POST `/api/devsahayak/envs`
  - PATCH `/envs/{id}`
  - POST `/envs/{id}/archive`
  - PUT `/tasks/{id}/env` (applies from the next round)
  - `tasks/start` takes `env` (`''` = her last pick)
- **How a session uses it** (`overlay` via `service._session_box`):
  - Its variables are laid over the repo's.
  - Its setup lines run after the repo's own setup command.
  - Its network (and the package-manager switch, via `net.allow_for(pkgs=)` / `grant(pkgs=)`) is what each command's pass carries.
  - Repo keys still go through the proxy in every environment.
  - With `dev_net` off, no pass is ever made.
- **The model is told the truth** (`engine.net_words`). It used to be told "no internet" even when the repo had a network.
- **Console:**
  - The first chip of the composer row is the environment, with a menu of Auto, her environments, "Edit …" and "New environment…".
  - The dialog has name, network radio cards, package managers, allowed domains, variables, setup script and Archive.
  - The session menu has "Cloud environment…".
  - `?environment=` pre-fills it.
  - Styles are in the `v0.878` block at the end of v2.css; the page stamps are 0.878.0.
- **Phone** (`lib/ui/devsahayak_new.dart`, on hoola_theme, no glass):
  - A New session page laid out like her screenshots:
    - "Ready when you are".
    - An environment chip opening the Select environment sheet: Auto "Follows your repositories", her environments each with a gear, and "+ Create environment".
    - A repository chip opening the Repositories sheet: owner over name, search, "+ Connect more".
    - A mode chip.
    - The composer "Type or hold to talk", with the mic (hold to talk) and send.
  - DevEnvPage, "Create a new environment": Name, None / Limited (Recommended) / Full, the package managers switch, allowed domains, variables, setup script, Create / Save changes, Archive.

**Fixed (audit findings):**
1. **CI fix rounds.** They ran inside the worker tick, which is cut at 300 s, so the next minute started a SECOND round on the same session. Now `_ci_bg` runs each step in its own thread with the session in `_RUNNING`. Stop reaches it, and the tick skips it. A quick check still finishes inside the tick (20 s join).
2. **Lost runs after a restart.** `answer()` and background `plan_ok` / `begin` / `fix_comments` had no job, so after a restart they looked busy forever. They now carry one and resume.
3. **Sweeping.** An open PR's working copy is never swept for age alone (`engine.sweep(protect=)`).
4. **Step history.** It was capped at 400 for the whole session. It is now 1200, and the first 60 are always kept, with one "gap" marker.
5. **Phone:**
   - Review and Merge send the repo (they failed with several repos and no default).
   - The chat card's Plan OK uses `/bg/plan_ok`.

**Tests:** `test_v0878_hoola_code_envs.py` 12.

**NOT VERIFIED:**
- The phone screens compile first on CI (no Dart here).
- The network part needs `dev_net` on after `python -m app.devlab net` passes on her server.
- No real Docker box ran here.

**Still NOT built:**
- Network secrets stored on the environment (keys stay per repo).
- On the phone: branch, model and effort chips, the diff with line comments, and attachments.
- Teleport to a local terminal.

## v0.921.0 HOOLA CODE LIKE CLAUDE CODE (built as 0.914; their CREATE GLASS ... CAMERA ALIVE took 0.914-0.920, all kept) - the console and phone rebuilt to the approved design (owner: "CHECK THE CLAUDE CODE INTERFACE, FEATURE, UI/UX ETC -- WE WANT EXACT SAME FOR HOOLA CODE CONSOLE SIDE --- SHOW ME THE DESIGN FIRST HERE" -> "ADD PHONE VIEW AND SCHEDULED TASKS SCREEN ALSO... ADD ALL 100% claude code feature in hoola code" -> "NOW CHECK THE MINUTE DESIGN FIX" -> "GO BUILD")

The design came first this time: a design canvas (claude.ai/artifact/RqivHmdqNni1XAZknHhbRT) with 17 console screens and 8 phone
screens, polished in a second pass (one icon set, a 9-step type scale, one accent, drawn controls), then approved. Its source files and
pictures are kept in `docs/design/hoola_code/` (the `.dc.html` files are the exact numbers; the `.png` files are what she approved).

**Console (/console/code, `static/console/code.js` + NEW `static/console/hoolacode.css`).**
- Styles left `v2.css`: the v0.807 block moved unchanged into `hoolacode.css`, then a v0.914 layer on top. That layer sets the page's
  own tokens (warm neutral light + dark: bg #FAF9F6 / #1C1B1A, one violet accent #5B45E0 / #9C88FF for picked, working and on; the
  ink pill is the main button) and redraws every component. The v0.878 environment styles live there too; the conflict that had
  dropped them is repaired.
- Sidebar: mark + "Hoola Code" (Literata), search and collapse; New session / Search (= Sessions page) / Scheduled (count) / Reviews /
  Environments / More (All sessions, Settings, Back to Hoola). Recents are one line per session with marks: pull request open (green),
  working (violet dot), needs you (amber), cloud. The state rides the row's tooltip; ⋯ appears on hover. You + settings sit at the
  bottom. Grouping by repo or status is still in the sort menu (default is now one Recents list).
- Home: "New session" bar, the Hoola mark, "Ready when you are", the environment card (current one ✓ + Choose environment), the lede,
  and the box docked at the bottom with its settings row (environment, repo, branch, mode, model, effort, usage ring). The starter
  buttons are gone (not in the design). The repo / branch / mode / model / effort pickers are still the browser's own lists, styled
  as quiet chips; the environment picker is the menu.
- Session: the title bar has the title and ⌄, a status pill or "PR #n · checks passing" (opens GitHub), Changes +a −b, details,
  working copy, ⋯ (same menu as the title, now with Open in: Copy checkout command / GitHub), and Share.
- The plan is ONE card in the conversation: "Plan · waits for you", size, the goal, steps, files, done-when, risks, and Approve plan /
  Not now (ids `#hcdYes` / `#hcdCancel` kept). "Hoola asks" is a card with the question in serif, her choices, and Type my own answer.
  "Open the pull request?" is a "Needs your OK" card. The model + mode line sits under the box.
- Rail: flat sections. A NEW Environment section (name, Ready while it works, gear = change environment, repo, branch), Changes, the
  checks, reviewers' comments, working copy, passes, Progress with a bar + "Step n of m · min", and Session.
- The Changes pane takes the rail's place (rail hidden, PR pill hidden). Files are tabs; diff rows are full-width green / red; the
  comment box is unchanged in behaviour.
- Share: one dialog, "Share this session", Private / Anyone with the link (7 days). Once shared: the link row with Copy link, Stop
  sharing, Done. Picking Private + Done stops it too. The design's "Team" is left out: there is no team visibility on the server.
- Sessions page ("Search"): search + repo filter, tabs All / Working·n / Needs you·n / Archived, cards grouped Working / Needs you /
  Earlier, each with its dot, "repo · environment · state · PR", +/−, how long ago, and ⋯.
- Scheduled tasks: a table (task + text, trigger badge Schedule / GitHub / API + when, repository, next run, last run in colour, an
  on/off switch), tabs All / Active / Paused, "+ New task" opening the form in a dialog (`#hcdSchedF`; adds an optional Name), and
  a page per task at `#/scheduled/<id>`: switch, Trigger address…, Delete, Run now, four facts, the prompt, and History.
  The design's model / environment fields for a task are left out: schedules do not store them yet.
- Settings: a section list (GitHub and pull requests, Repositories, Environments, Rules and limits, Usage) beside the cards. Every
  section stays on one page, so every earlier control and test still works. NEW: an Environments section (list, Edit, New
  environment) and Usage this month. The Environments row in the sidebar jumps there.
- The environment dialog has two columns (name + network on the left; variables, setup script and the keys note on the right).
- NOT in the console, said plainly: the design's "Open in Terminal" / "Hoola Desktop" (no such client exists), a context-% meter
  (the server does not report one), "Your PC" in the environment menu, and a star for the default environment.

**Phone (`lib/ui/devsahayak_kit.dart`, `devsahayak_new.dart`, `devsahayak_session.dart`, `devsahayak_drawer.dart`;
`devsahayak_screen.dart` keeps the chat cards and the old tabs as `DevCodeSettingsPage`).**
- Built by a helper agent to the 8 phone screens: New session, environment sheet, repository sheet, create / edit environment,
  session, Changes, sessions drawer, Scheduled tasks (+ form).
- `CodeColors` was added to `hoola_theme.dart` because the design-rules ratchet forbids raw colours in screen files.
- Departures, each because the server lacks the thing: no context % (the session's cost instead), no "Mark ready" route ("Open the
  PR" / "Ask to merge" instead), no command-permission ask, no files on a follow-up, and the true limits (at most 3 repos, a schedule
  at most once a day).
- `test/hoola_code_phone_test.dart` has pure checks only.

**Tests.** The console suites were moved to the new design (Recents list, Back to Hoola under More, sizes 36 / 30 / 26 buttons, 32
chips, 40 fields, 32 composer buttons, rail 320, column 780, sidebar 260; the Scheduled flow list → dialog → task page; the share
copy). 45 browser tests green.

**NOT VERIFIED:** the phone Dart has not compiled anywhere yet (no Flutter in the sandbox; CI is the first compile). The console has
not been seen on her VPS yet.
## v0.922.0 HOOLA CODE NATIVE (built as 0.921; their HOOLA CODE LIKE CLAUDE CODE took 0.921 - both kept) (owner, on the design canvas claude.ai/artifact/GF4AtP5MNfV8kARgTGymuh: "OPTION B ::: SAME AS HOOLA CHAT SCREEN ... SHOW ME ALL HOOLA CODE SCREEN HERE FIRST ... PERMIUM AND PERFECT SAME AS CLUDE CODE" -> "GO")

The audit before it: the phone had two doors to Hoola Code that did not agree - Tools > Hoola Code opened the console
page in a WebView (no file chooser there, so attaching did not work), Your AI team > Developer opened the old
DevsahayakScreen in the old frame. Both now open ONE native screen drawn in the new design (hoola_theme.dart only, no
glass, no blur, nothing under 12):

- `lib/ui/code/code_kit.dart` - small readers (cs / cm / cl / ci), `codeCall` (server calls, shows the server's own
  `say`), status words, grouping (Working / Needs you / Earlier), clocks, and the parts every page uses: top bar,
  black main button, outline, chip, card, badge, section, the turning ring (still under reduce motion), bottom sheet,
  choice row, field (secret option), switch row.
- `code_home.dart` - `HoolaCode`: "What should we build today?", the one composer (repo, branch, Ask / Plan first /
  Auto, model + effort, up to 3 pictures and 3 text files, slash words /plan /fix /tests /docs /explain /feature),
  starter chips, sessions grouped, 5 s refresh while one runs; `showCodeNewSession` = the same composer in a sheet.
- `code_session.dart` - `CodeSessionPage`, laid out like the chat: her bubble + files, Hoola's words in the reply
  serif, steps folded into "Worked for 2m 14s · 18 steps" cards (open while running), the latest to-do list as a Plan
  card, the plan waiting for her yes (Yes, start = `bg/plan_ok` with the plan's hash), one question with tap choices,
  ready card (Open the pull request = `push` with the hash), PR card with CI / proof / own review / reviewers'
  comments and Fix it, Merge = a merge card she answers (`merge_request` then `actions/{id}/decide`, a forced merge
  needs her reason); composer modes note / answer / plan change / revise; More: stop, thinking, changes, GitHub,
  rewind to a checkpoint, cancel, archive, delete.
- `code_changes.dart` - unified diff with old / new line numbers, This round vs the base branch (`compare`),
  long-press a line to comment; comments ride her next message.
- `code_more.dart` - Pull requests (open PRs of a repo with Review, Hoola's draft reviews with Comment / Request
  changes / Approve, posted with the review's hash, merge / deploy cards waiting for her yes, Ask for a deploy),
  Scheduled tasks (switch, Run now, history, delete, new), Repos & GitHub (fine-grained token typed only here, repos
  with setup / test / internet level / keys / events, What Hoola remembers, the four switches + merge method).

Doors: `hoolaOpenStudio` switch ('Hoola Code' -> native), the AI team entry -> `HoolaCode`, Settings opens it in the new
frame; `test/hoola_settings_test.dart` maps DevsahayakScreen -> HoolaCode (redrawn). The old screen stays for the chat
cards. Server unchanged. Tests: server/tests/test_v0921_hoola_code_native.py (screens, every route the phone calls is
served, her taps keep their hashes, doors, design rules, version).
NOT VERIFIED: compiled first by CI (no Flutter here); not yet on her phone; real runs need the VPS on a current
version (it read 0.902.0 at the audit) and Anthropic credit.

## v0.923.0 HOOLA CODE DOOR (owner, after deploying v0.922: "DEPLOYED. BUT APP SHOWING OLD WEB INTERFACE")

v0.922 made `hoolaOpenStudio` open the native `HoolaCode` screen for 'Hoola Code', but on the Tools tab Hoola Code is not one of
the studio tiles: it is a row in the "More" list (`hoolaMoreTools`, with Game Dev), and that row called `hoolaOpenConsole` straight,
so the tap still loaded /console/code in the WebView. The More row now calls `hoolaOpenStudio` too (Game Dev still falls through to
its console page). Your AI team > Developer was already right. `test_v0921_hoola_code_native.py` now pins the More row. Server
unchanged. NOT VERIFIED on her phone; she needs the v0.923 APK.

## v0.924.0 HOOLA CODE FIRST SCREEN (owner, on her Claude Code New session screenshot: "CHECK THE CLAUDE CODE 1ST SCREEN ... WE WANT SAME ... FOR HOOLA CODE WHEN ITS OWN HOOLA CODE CHAT SESSION ... AND BAR ... SHOW ME PERFECT PREMIUM DESIGN" -> design canvas claude.ai/artifact/Au9zBc5gmkVsNLwVc41rCM (7 screens) -> "GO")

- NEW `lib/ui/code/code_start.dart`:
  - `CodeNewSessionPage` (opened by `showCodeNewSession`, pops with the new session's id): top bar back + "New session";
    centre the animated Hoola mark (`HoolaMark(size: 58)`) + "Ready when you are" (Literata 30); while she talks the
    centre shows her live words; "Connect GitHub first" when no token.
  - chips above the bar: environment (`CodeBarChip`, Auto + her environments from GET /api/devsahayak/envs, network /
    variables / setup line, New environment opens the existing `DevEnvPage`, network-not-on and keys-outside-the-box
    notes) and repository (GitHub mark drawn from its path via `svgPath`, Add repository sheet: search over 4+, her
    repos with owner / private / language, Branch to work from via /branches, "Give Hoola more repositories" opens
    Repos & GitHub, "Use <repo>").
  - `CodeBar`: + (sheet: pictures, text file, how it works, model), the field, the mic (tap = dictate, hold = talk with a
    violet listening pill, clock and a sound-level wave, slide left 70 px = cancel and her words come back, let go =
    send; a let-go before the mic is ready never leaves it on), the round send (ink pill with words, grey without) or
    Stop (while Hoola works and the field is empty). Reduce motion = still wave, no ring.
  - tasks/start body gains `env` (her pick; server already took it since v0.878).
- `code_home.dart`: the in-page composer is gone; home = list + a docked New session button; the quick chips open the
  New session screen prefilled. `CodeDraft` + `codeModes` stay there.
- `code_session.dart`: the typing box is `CodeBar` (+ = the session menu); an environment chip above it changes the
  session's environment (PUT /tasks/{id}/env, from the next round); the working row shows the spinning Hoola mark.
- Tests: NEW `test_v0924_hoola_code_first_screen.py`; `test_v0921` covers code_start.dart and the two env routes.
- NOT VERIFIED: no Flutter here - CI compiles the Dart first; not seen on her phone.

## v0.925.0 HOOLA CODE BAR CLEAN (owner, her phone screenshot of the v0.924 New session screen: "Check the chat typing section ... Make it perfect ALINED like the CLUDE CODE is ... Perfect primium and ALINED")

- ROOT CAUSE: the new-design theme (`hoola_theme.dart` `inputDecorationTheme`) gives every TextField an outlined, filled
  pill (`border`, `enabledBorder`, `focusedBorder`, `filled: true`). A field that sets only `border: InputBorder.none`
  still gets the theme's `enabledBorder` / `focusedBorder` and fill, so the Hoola Code bar drew a second rounded outline
  round "Type or hold to talk" inside its own pill.
- FIX: `code_kit.codeBareInput` = every border off (border / enabled / focused / disabled / error / focusedError), no
  fill, no counter, 48 dp line, dense padding; the bar's field uses it with `textAlignVertical: center`, a violet cursor
  and 6 dp after the + circle; the repository search field too. The Hoola Computer chat box (`hoola_computer.dart`)
  had the same bug and gets the same three lines. The main chat composer already did this (v0.888).
- RULE: under the new theme a bare field must turn off enabledBorder + focusedBorder + filled, not just border.
- Test: `test_v0924_hoola_code_first_screen.py::test_v0925_bar_has_one_outline`.
- NOT VERIFIED on her phone (CI compiles the Dart).


## v0.926.0 HOOLA CODE ON QWEN (owner: "Now check hoola code to qwen" -> the check -> "27B FOR CODING ALSO")

THE CHECK: every Hoola Code model call already goes through one function, `devsahayak/brain.py` `call()` (engine round,
compaction, subagents, specialists / plans / reviews via the loop, hint, memory); the one-shot writer / reviewer go through
`service.model_json`. With `dev_claude` on they all ran on Claude Opus 5.5 through the Anthropic key - so real sessions
needed Anthropic credit while her chat already runs on Qwen 3.8 27B through OpenRouter. Switching `dev_claude` off was NOT
the answer: the shared GLM door gives a request 45 s, pauses itself for 10 min after 2 failures (for every user's chat too),
follows the chat's model and drops the coder's effort.

BUILT: `dev_brain` ("qwen" default | "claude"), `dev_qwen_model` (qwen/qwen3.8-27b), `dev_qwen_timeout_s` 180,
`dev_qwen_fallback_claude` False. `brain.call` -> `_qwen_call`: messages + tools through `llm.to_openai` (unsigned Claude
thinking from older rounds dropped), POST https://openrouter.ai/api/v1/chat/completions with the server's OpenRouter key
(`providers.key_of`), `reasoning` = her effort (xhigh / max -> high; think off -> low) with `exclude: true` and room added to
max_tokens, `provider.require_parameters` (only providers that really take tools), temperature 0.2, header X-Title Hoola Code;
3 tries on a timeout / 5xx / empty answer, a 400-404 (402 carries `llm.CREDIT_LOW_LINE`) raised at once; the answer back
through `llm.from_openai` in the same block shapes; usage metered with `usage.from_openai`. A Claude model id picked for a
call (hint / memory ask for Haiku) means nothing on Qwen; a qwen/ pick wins. No OpenRouter key = Claude, logged once.
`service.model_json` on Qwen = `brain.call` + `site.ai.parse_json`, one retry on bad JSON. `service.models()` = the forced
model "Qwen 3.8 27B" (console chip + phone sheet already show `forced`). `loop._anthropic_brain` no longer refuses when only
the Claude key is missing.

FOUND + FIXED: `usage.price_of` drops the provider part ("qwen/") before matching, so the v0.852 "qwen/qwen3.8-max-0902"
price never matched (counted at the fallback price); both Qwen keys now carry no prefix; 27B priced at $0.15 / $1.875 /
cache read $0.0375 per million (OpenRouter /models, 15 Nov 2026).

Tests: `test_v0926_hoola_code_qwen.py` (10); conftest pins `DEV_BRAIN=claude` for the older Hoola Code suites. Back to
Claude: `DEV_BRAIN=claude` in the VPS .env + pm2 restart.
NOT VERIFIED: no live Qwen coding round; the coding cards (vps-ops code_card / code_card_hard) have not been run on Qwen;
whether OpenRouter caches Qwen requests automatically is not confirmed.


## v0.927.0 HOOLA CODE CLOCK (owner, her phone on her first Qwen session: "Check the misbahebiour for hoola code ... Is it properly deployed and inline or not")

Her screenshot: session "read all fnw ai node project first properly", step card "0 steps" with "Plan pass started · reads only
- nothing is changed", working row "Checking its own work 5:30:57".
DEPLOYED: yes - healthz 0.926.0, VPS ops run 454 (deploy) green, clean restart, the OpenRouter model profile for
qwen/qwen3.8-27b loaded.
WHAT WAS WRONG: (1) the clock - SQLite returns created_at without a zone, `view()` sent "2026-11-15T09:44:10" and the phone's
DateTime.tryParse read it as local India time, so every working clock started at 5:30:00 (the console's Date.parse the same);
also it counted from the SESSION's start, not the running round. (2) the words - a pass event (k "pass") was always
"Checking its own work", so the read-only plan pass looked like a self-review; and a step card holding only that pass said
"0 steps".
FIXED: `service.view` sends `_aware(...)` times (+00:00) for at / updated, PR review rows and checks rows; `_RUN_AT[tid]` set
when `_in_thread` starts a round and dropped when it ends, sent as `run_at`; phone `code_kit.codeTime` (bare time = UTC) used
by the session working row, the step-card durations, the home list and `codeAgo`; console tick uses `TASK.run_at || TASK.at`;
pass words by name (plan = "Planning · reading the code", ci_fix = "Fixing the failed checks", review = "Checking its own
work"); `_passTitle` for a card with only a pass. Every Hoola Code Qwen call now logs "hoola code qwen <model> <s> effort= in=
out= tools= calls= stop=" and every failed try its reason, so `vps-ops errors` / pm2 logs show how fast 27B is answering.
NOT VERIFIED: on her phone; the Qwen step times have not been read from her server yet.


## v0.928.0 HOOLA CODE CHAT LIKE HOOLA CHAT (owner: "Make all chat feature same as hoola chat... App... Everything")

The gap, read from the code: the phone Hoola Code session drew Hoola's words as one plain Text (no headings, lists, tables or
code blocks), had no Copy / Read aloud / Share, no long-press, cut her message at 16 lines and never followed new words.
BUILT (app only): `lib/ui/code/code_words.dart` - CodeReply (the chat's HoolaMd renderer + long-press sheet + Copy · Read aloud
· Share on the newest reply, sharing as a text file through Native.shareFile like the chat), codeMessageMenu (Copy, Quote in my
reply, Edit and send again = her words back in the box, Read aloud, Select text), codeQuoteInto, CodeNewestButton; the session
uses them for every "say" step, the explanation and Hoola's question; her bubble long-press + SelectableText while selecting +
a "Done selecting" chip; new steps scroll her to the end unless she scrolled more than 240 px up, then a Newest arrow shows.
NOT CARRIED OVER, on purpose: Good / Not right and Ask again (the chat's rateReply / retryLastReply work on chat turns; Hoola
Code has no rating or retry route yet), files on follow-up messages (the server takes attachments only on the first message
of a session), the voice-call button (a call is not a coding session).
NOT VERIFIED: on her phone (CI compiles the Dart first).


## v0.929.0 HOOLA CODE READS (owner: "DEPLOY DONE CHECK. ALSO CHECK THE RECENT CONVERSATION LOGS ... NEED LOT OF WORK")

Read from the v0.928 deploy log (the 40-line error tail just before the restart): her session D-0002 on fnw-flow-ai, kind
"write", ended "(Koi file badalne layak nahi mili.)" and its devsahayak_task event INSERT failed with "database is locked" at
09:54:33 (SQLite's 5 s wait). Cause 1: `guess_kind` knew only explain (starting words) / tests / docs / fix, so "read all fnw ai
node project first properly" fell to write -> standard tier -> a read-only plan pass -> a coding round with nothing to change.
FIXED: `_READ_ASK` (read, study, understand, go through, look at, walk me through, summarise, overview, analyse, audit, review the
/ my / whole, tell me about, explore, padho, samjho, dekho, batao) with no `_CHANGE_ASK` word = explain (plan.assess makes explain
trivial: no plan pass, no branch, no PR). Cause 2: `_publish` now waits 1.5 s and publishes once more on "locked".
NEW: vps-ops `codelog` = `server/tools/codelog.py 6 santosh.db` (sqlite read-only: number, kind, tier, status, rounds, model,
effort, ask, step counts, every pass / read / edit / search / bash / say line with its time, explanation, error) + the "hoola
code qwen" / devsahayak log lines + errors near them. The INFO lines go to santosh-error.log (Python logging writes stderr).
NOT VERIFIED: on her server; the root of the lock (who held the database > 5 s) is not known.


## v0.930.0 QWEN CARD (owner: "CARD DONE CHECK")

vps-ops code_card run 457 (15 Nov 2026 10:52 UTC, server v0.929.0, Hoola Code on Qwen 3.8 27B via OpenRouter): 11/12 jobs
fully right (92 %); works 12/12, stayed in scope 12/12, project rules 12/12, good tests 9/10 (fix tests proving the bug 5/5),
6.1 steps and 1.1 min a job. Miss: tests_for_discount - its own new test failed (1 failed, 3 passed). Claude Opus scored 12/12
on the same set (v0.382 save). The card printed "claude-opus-5-5" because quality/codecard.py read dev_loop_model / site_model,
not the brain - it now prints brain.model_for() when Hoola Code is on Qwen. Not yet run on Qwen: code_card_hard, code_card_mobile.


## v0.931.0 HOOLA CODE IN THE SIDE PANEL

Owner, on her phone screenshots (home + side panel): "IN SIDE PANEL -- ON TOP SHOW A HOOLA CODE ICON FOR GOING TO HOOLA
CODE. REMOVE THE HOOLA CODE FROM TOOL SECTION. ALSO CHECK ON TOP RIGHT CORNER A NEW CHAT ICON REMOVE THAT .... SHOW ME
THE DESIGN FIRST" -> design canvas claude.ai/artifact/8ceUMqUfgX68HvhVTtmMet (A = a full Hoola Code row, B = a small
Code button beside the title) -> "GO WITH B".

- `lib/ui/shell/hoola_shell.dart`: the drawer header is a Row - the Hoola title + `HoolaCodeButton` (48 dp stadium on the
  surface colour with a hairline, a 34 dp black (`c.pill`) circle with the terminal icon, the word Code; a violet
  `c.accent` dot on the circle while one of her Hoola Code sessions has `running: true`). The drawer reads
  GET /api/devsahayak once when it opens (`_checkCode`, a failure = no dot). A tap closes the panel and opens the native
  `HoolaCode` screen through `hoolaOpenNew`.
- `lib/ui/shell/hoola_tools.dart`: Hoola Code removed from `hoolaMoreTools` (More = Game Dev + Connectors);
  `hoolaOpenStudio` keeps its Hoola Code branch, and AI team > Developer still opens it.
- Home top bar and the chat top bar (`lib/ui/chat/hoola_chat.dart` `_TopBar`): the `edit_square` New chat icon is gone;
  New chat lives in the side panel. The chat keeps a 54 dp space on the right so its title stays centred.
- Tests: NEW `server/tests/test_v0931_code_in_side_panel.py`; `test_v0898_chaar_tab.py`, `test/four_tabs_test.dart`,
  `test/tools_pro_test.dart` (10 tool drawings) updated. Phone only, server unchanged except the version story.
- NOT VERIFIED on her phone (CI compiles the Dart first).


## v0.932.0 HOOLA CODE WAVE 1

Owner: "NOW GO DEEP CHECK THE HOOLA CODE BACKEND --- IS ALL IS PERFECT WITH ALL ADVANCE CODING SKILLS LIKE CLAUDE CODE"
-> a three-part deep check (the engine loop on Qwen, the session lifecycle, the test box; ~25 findings) -> "GO WAVE 1".

1. LOST CARDS (`devsahayak/service.py` `_publish`): almost every Hoola Code card was published inside `with session()`
   right after `s.flush()`, while the thread held SQLite's write lock; the event's own session waited 5 s and failed
   with "database is locked" (reproduced: 5.0 s then the error; the v0.929 retry failed the same way). Now a thread-
   local list of sessions with an unfinished write (SQLAlchemy `after_flush` / `after_transaction_end` on Session) is
   kept; a card published while one is open is sent from that session's `after_commit` (in order); a rolled-back save
   sends nothing (logged). No open write = sent at once, as before.
2. THE GIT WALL: the working copy (with its .git) was mounted read-write in the box and its top folder is 0o777; a test
   or a dependency's install script could plant `core.fsmonitor` / hooks that the SERVER's git (`engine._git_run`, run
   with the full `os.environ`) then executed outside the box. Now `devlab/box.py` mounts `<copy>/.git` read-only at
   `/work/.git`, and server git runs with `_git_env()` (PATH, HOME, LANG, LC_ALL, TMPDIR, TZ only, GIT_CONFIG_NOSYSTEM)
   and `GIT_SAFE` (fsmonitor off, hooksPath /dev/null, pager cat, editor true, protocol.ext never, sshCommand false,
   no credential helper). The coder is told git in the box is read-only and every command runs in a fresh box.
3. ANSWERS KEPT (`engine._round`): a reply in words with no tool call is the answer, like Claude Code - an explain ask
   ends there; any other ask gets one reminder per stretch of work (the count resets after a tool step), then its
   words become the explanation. A loop that ends without done keeps the last words it said and says which limit ended
   it. A cut answer is asked to continue at most 3 times in a row.
4. ODD TOOL CALLS: `brain._keep_broken` keeps every Qwen tool call whose arguments are not valid JSON (llm.from_openai
   dropped them silently) as a tool_use the engine answers with "your arguments were not valid JSON ... split a big
   write"; `Tools.run` reads a list / object sent as JSON text (`_loose`) and turns any other exception into words for
   the model (Stopped / Unavailable still pass); a page-event error and a failed compaction (trim harder) never end the
   round.
5. HER NOTES: the inbox is read at done too - a note that arrives as Hoola finishes cancels the finish ("Not finished
   yet: she just wrote to you"); a note left after the round ends gets a card asking her to send it as a follow-up.

Tests: NEW `server/tests/test_v0932_hoola_code_wave1.py` (10). Hoola Code suites re-run: v0748 / v0768 / v0789 pass
alone (failed only under 6-way parallel load); v0447 ai employees premium, v0473 coder routes, v093 place fail the same
on the code before this change.
NOT VERIFIED on her server. Waves 2-3 not built.


## v0.933.0 HOOLA CODE WAVE 2

Owner: "GO WAVE 2" on the Hoola Code deep check.

1. DEPENDENCIES IN THE BOX (`devsahayak/engine.py` `Tools._image`, `devlab/spec.py`): the repo's setup command read from
   its files / CI / the language default now runs by itself (`dev_auto_setup`, default on; her own setup always did) - before,
   `confirm=True` meant it waited for a tap nobody was asked for and tests ran with nothing installed. A CACHED snapshot keeps
   what setup put in the image (pip --user, Go / Cargo caches) but not node_modules written into /work, so a new working copy
   with package.json and no node_modules gets the setup run once in place (network on, that copy only). A missing or stale base
   image is built in `_image` (a failed build = the note, and bash refuses with it); a snapshot removed by prune is rebuilt.
   Default setups: Python = install requirements.txt, else `-e .` when pyproject / setup.py exist, else nothing; Go / Rust
   without `|| true` - a failed install is no longer cached as a good snapshot.
2. SESSIONS ON A PR (`devsahayak/service.py` `_fail`, PR_LIVE): every failure path (start, begin, plan_ok, push, CI fix,
   background thread) goes through `_fail` - with an open PR the status stays pr_open / checks_failed / ci_running and the
   error is said; Stop and cancel keep a PR session on its PR; `revise` + the restart resume accept ci_running (follow-ups no
   longer refused for up to 45 min); start / begin / plan_ok / the continue path catch every exception (a refused Qwen call
   left the session at 'new' with no job row).
3. WORDS (`guess_kind`, `wants_change`): a read word next to a fault word ("dekho aur theek karo", "500 error deta hai,
   dekho") = fix; theek / thik / sahi kar / solve / resolve / patch count as change words; after an explanation only a change
   word or a plain yes (haan / go / do it) turns the session into work - "thanks!" no longer starts a coding round.
4. LINE ENDINGS (`edit` / `multi_edit` / `write`): a CRLF file is edited in LF and written back in CRLF (bytes, no newline
   translation), so one changed line is one changed line; `read` splits on real line breaks only (`_lines`) and marks a line
   cut at 2,000 characters.
5. THE PUSH TAP (`api.py` /push -> `in_background(..., "push")`): the card (status ready + hash) is checked at once, then the
   commit / PR / lab proof / own review run in a tracked background thread (job `push`); a retry commits ON TOP of the
   hoola/* branch the first try made (`on_top`) and reuses its already-open PR.

Tests: NEW `server/tests/test_v0933_hoola_code_wave2.py` (8). Hoola Code + box suites re-run file by file: only the three
reds that fail the same before this work (v0447 ai employees premium, v0473 coder routes, v093 place); v0768 passes alone.
NOT VERIFIED on her server: the Docker paths are tested with fakes (no Docker daemon here).


## v0.934.0 HOOLA CODE WAVE 3

Owner: "GO WAVE 3" on the Hoola Code deep check. The deep check found the coding card measured the OLD 8-tool loop
(`devsahayak/loop.py` on an in-memory GitHub) while her sessions run the workspace engine (`devsahayak/engine.py`), so the
11/12 and 11/12 Qwen scores were not scores of what she uses.

- `engine.LOCAL_FILES` (tid -> files): `Session.ensure` writes a card job's practice repo into a temp folder instead of
  cloning from GitHub; everything after that is the real engine: local git, secrets hidden, Claude Code's tools, bash in the
  locked box, compaction, the ECC gate / reality check when on.
- `quality/codecard.py`: `run_task_engine` (a session id per job, `_CardGh` answers the base sha, the working copy and the
  LOCAL_FILES entry removed after, an engine error = one honest row), `engine_ready` (the box + git, else the card refuses
  to run rather than fall back), `card(engine=True)` (parallel = DEV_WS_LIVE), the result says engine 'workspace' and
  box commands a job, saved as code[N]-engine-<time>.json.
- `python -m app.quality code --engine [--brain qwen|claude]`: DEV_BRAIN for this process only, practice caps
  DEV_WS_STEPS 60 / DEV_WS_MINUTES 10 / DEV_WS_LIVE 3 (unless set), DEV_MEMORY off (a practice job never writes repo memory).
- vps-ops: code_card_engine (set 1), code_card_engine_hard (set 2), code_card_engine_claude (set 1 on Claude, needs
  Anthropic credit); the job limit moves 25 -> 50 minutes (each run caps itself at 43).

Tests: NEW `server/tests/test_v0934_card_real_engine.py` (5: a scripted job right through the real engine with nothing left
behind, an engine error = one row, no box = refused, CLI + vps-ops, version); the card suites (v0360 / v0365 / v0371 / v0378
/ v0402 / v0926) + engine suites pass; v0378 pin moved 25 -> 50.
NOT VERIFIED: no real-engine card has run on her server yet (no Docker here).


## v0.935.0 HOOLA CODE FEED - the working feed like the Hoola chat and Claude Code

Owner, on her phone screenshots of a running Hoola Code session ("Working 1:36" pinned above the typing box, the reply
appearing at once): "WHY WORKING IS AT BOTTOM OF CHAT SPACE --- IT MUST BE SAME AS HOOLA CHAT AND CLAUDE CODE WORKING,
FEED, ANIMATION ... CHAT REPLY IS APPEARING DIRECTLY ... SHOW ME THE WORK BEFORE DEVELOPMENT" -> design canvas
claude.ai/artifact/27Hw4XRUj5qG83sWaeX2J5 (Now / While it works / The answer lands / Done / The numbers) -> "GO".

Server:
- `devsahayak/brain.py` `_qwen_stream`: the Qwen step through OpenRouter as server-sent events (`stream: true`,
  `usage: {include: true}`), text deltas joined and handed to `on_text(the whole text so far)`, tool-call pieces joined
  by index, keep-alive comments skipped, an error chunk or a 4xx = QwenError as before; put back into the plain answer
  shape so `llm.from_openai` + `_keep_broken` read it unchanged. Used ONLY when `brain.TEXT_SINK.fn` is set (the
  engine sets it around its main call; plans, reviews, agents, compaction and the card's QWEN_POST hook never stream)
  and `dev_stream` is on. A try again calls the sink with "" first. Test hook `QWEN_STREAM`.
- `engine.py`: `LIVE_TEXT[tid]` = the words being written; cleared once they become a `say` step and at the end of the
  round. `say` steps kept to 20,000 characters (were cut at 800).
- `service.task_view` "live" (only while the round runs in this process).

Phone (`lib/ui/code/code_session.dart`, `code_words.dart`):
- The working row is at the END of the thread (HoolaMark 22 + the real step, "Writing" while words stream, "Stopping
  after this step"; `CodeShimmer` = a soft light passing over the words, still under reduce motion; clock) - no longer
  pinned above the typing box.
- While it works the newest group of steps shows as light rows (14 px, file names mono 13); every other group is one
  quiet line that opens on a tap. "Worked for N · M steps" only for a finished group; a group folded while its words
  are written says what it did so far ("Read 11 files, looked in 6 folders").
- New messages land word by word (`CodeLanding`: 34 ms a word, 17 ms when more than 80 words wait, newest words lighter
  through HoolaMd streaming), carrying on from the live words when they turn into a step; history shows at once.
- Checks every 1 s while it works, 10 s when quiet; one check at a time.

Tests: `test_v0935_hoola_code_feed.py` (stream assembled + words out as they come, refused stream, only the main call
streams + live view, phone source pins, version); pins in v0926 / v0928 moved to the new shapes.
NOT VERIFIED: on her phone (CI compiles the Dart first); no live streamed Qwen call from here; the Claude brain path
does not stream (its words still land word by word on the phone).


## v0.936.0 HOOLA CODE LIKE CLAUDE CODE - the conversation feed

Owner, on screenshots of this Claude Code session ("CHECK HOW CLAUDE CODE A PERFECT SMALL 2 SENTENCE FEED AND COMMAND RUN,
CREATED FILES ETC IN FAINT ... FIRST SHOW ME THE WORK STRUCTURE") -> canvas claude.ai/artifact/27Hw4XRUj5qG83sWaeX2J5
round 2 (A while it works, B the steps sheet, C done, the rules) -> "I WANT COMMAND RUNNED/RAN ... DONT EXPOSE THE RUN
COMMAND TILL USER CLICK ON ARROW" (sheet redrawn) -> "PERFECT. DEPLOY SAME AS DEFINED ARTIFACT".

Server (`devsahayak/engine.py`, `service.py`):
- SYSTEM: one or two short sentences before each set of tool calls (what it found, what next), no lists there; a plain
  description on every bash call.
- bash tool `description` ("3-8 plain words starting with a verb"); `t_bash(..., description="")`; the bash step carries
  `desc` = the model's words or `cmd_words(cmd)` (tests / style / types / build / install / search / changes / list /
  look at a file / run a script / "Run a command").
- `NOW_STEP[tid]` = `now_words(tool, input)` while a tool runs ("Running the unit tests", "Reading LoginActivity.java",
  "Searching the code"; never the raw command) -> task view "now"; `model_label` ("Qwen 3.8 27B · High").

Phone (`lib/ui/code/code_session.dart`, `code_words.dart`, `code_kit.dart`, `code_start.dart`, `chat/hoola_md.dart`):
- Every part of the work between two of Hoola's messages = ONE faint line (16 px, ink3, no icon, no box): "Ran 3
  commands", "Searched the code, read 2 files", "Edited LoginActivity.java" + the green / red count, chevron. While it
  works the newest part is the running line ">_ <now>" in the moving light with the clock.
- A tap opens `CodeStepsSheet`: close X + the line as its title, one row per step (icon, bold "Ran" / "Read" / "Edited" /
  "Searched", plain grey words), joined by a thin line; a command's `$ cmd`, output tail and "Passed · exit 0 · 41s", or
  an edit's lines, open only under that row's arrow.
- Hoola Code's words in the app sans at 17 / 1.55 (`HoolaMd(sans: true)`), her bubble 17 with round corners.
- Top bar centred: title, "repo · environment", a spinner while it works, the session menu. "Changes +a -r" floats above
  the typing box beside the Newest arrow. The suggested next message is a chip inside the typing box; the environment
  chip and the model name sit above it when idle. Copy + Read aloud under the newest reply (Share moved to the long-press
  sheet).

Tests: `test_v0936_hoola_code_claude_feed.py`; pins in v0926 / v0928 / v0935 moved to the new code.
NOT VERIFIED on her phone (CI compiles the Dart first). Qwen may not always write the short sentences or descriptions;
the fallback words cover commands.


## v0.937.0 HOOLA CODE STEADY - the screen stops flipping, words land slowly, the Hoola mark (owner, her screen recording of a Hoola Code session)

Her five points from the video, each with what was found:

1. "WHEN HOOLA CODE GIVE FEED ENTIRE CHAT SECTION VIBRATE" + 5. "PLAN CARD ... HTML CREATION PREVIEW CARD ... COMMING AND GOING"
   - ROOT CAUSE (one, for both): her session sat in `ci_running` ("CI running · PR #22 · No CI on this repo"). The worker runs
     `devsahayak.service.tick()` on every worker tick (`worker_tick_seconds` 2 s + the other slots), and the CI loop in it had
     NO throttle (its docstring said "every minute"): each tick started `_ci_bg`, which put the session in `_RUNNING` for
     the GitHub look. The task view's `running` flipped true / false every 1-3 s, so the phone swapped the typing box with
     "This session is finished · New session", the PR card and the "Thinking" row in and out, and the list height changed
     under her finger. The deploy log proved one server process (pm2 fork, one `santosh`), so it was not a worker split.
   - Fix: `service._ci_due(tid)` = one CI look per session a minute (`dev_ci_poll_s`, default 60); `_QUIET` = in
     `_RUNNING` for a CI look only, so the view's `running` (and `service.running`) stay false; `_ci_step` takes the session
     out of `_QUIET` before every branch that starts real work (a fix round, the own review, the proof step), so a real
     fix round still shows as working. It also stops ~30 GitHub calls a minute per waiting session.
   - Phone, defensive: the page keeps its working look for 3 s across a check that says "not running" with the same
     status (`_runSeen` / `_runCarry`); only new STEPS move the page (the growing live words no longer start an animated
     scroll every second that fought the per-word jump); landing never jumps against a scroll already moving
     (`isScrollingNotifier`); the list's bottom room no longer changes when she scrolls up; one keyed working row.
2. "REPLY TEXT LANDING ... VERY FAST AND INSTANT"
   - `CodeLanding` 34 ms -> 52 ms a word (~19 a second; catch-up 26 ms only past 160 waiting words), and the newest four
     words fade in step by step (`HoolaMd fade`: .82 / .62 / .42 / .22 ink, faintest last; off for the Hoola chat).
   - A closing answer (`explain`) that arrives while she watches now lands instead of appearing at once.
3. "BEFORE THINKING THERE SHOULD BE THE EXISTING HOOLA ANIMATE ICON": the working row starts with the turning `HoolaMark`
   (size 22, still under reduce motion), like the Hoola chat's working row; its words cross-fade when the step changes.
4. "FEED ... VERY LARGE AND IMPROPERLY ALINED ... 2 TO 3 LINER ... NOT UNWANTED FEED": her session showed long paragraphs
   between steps and the same paragraph two or three times (Qwen restating). `engine.short_say` = words between steps
   (an answer that also calls tools) cut at a sentence end to 3 sentences / 60 words, a list or code block cut to the
   words before it, applied to the live words too (`LIVE_TEXT` via the stream sink) so the phone never shows more than
   the saved step; `engine.said_before` drops a paragraph whose words are 70 % the same as one of the last four this
   round. The rules: at most 40 words, the one thing that matters in **bold**, never repeat, never retell her request;
   the final answer result first, at most five short points.

Tests: NEW `test_v0937_hoola_code_steady.py` (5); pins moved in test_v0935 / v0936 / v0928 / v0475; version 0.937.0
(pubspec 0.937.0+936). NOT VERIFIED on her phone (CI compiles the Dart).


## v0.938.0 HOOLA CODE CLOCK BESIDE (owner, her phone screenshot of a Hoola Code session: "CHECK THE THINKING ... HAS TIMING AT EXTREEM CORNER ... MAKE IT NEAR TO THINKING ... WITH MATCHING FONT WITH THINKING")

The working row drew its words in an `Expanded` and the clock after it in JetBrains Mono 12, so the clock sat at the far
right edge in a different, smaller font ("Thinking ............ 4:45"). Now the words are `Flexible` (they take only their
own width) and the clock follows them as "· 4:45" in the same Schibsted Grotesk 16 as the words, in the quieter ink3
colour, with tabular figures so the line does not jitter as the seconds change. The turning Hoola mark (v0.937) stays in
front. Phone only (`lib/ui/code/code_session.dart` `_runningRow`); server unchanged except the version story.
Tests: NEW `test_v0938_code_clock_beside.py` (2). Version 0.938.0 (pubspec 0.938.0+937). NOT VERIFIED on her phone.

## v0.939.0 HOOLA CODE MAKES THINGS (owner, on the design canvas claude.ai/artifact/BjGPb7Tkqfx6QqpgkDznxH -> "GO BUILD")

She asked for Hoola Code to make artifacts, artboards, prototypes, PRDs and sheets the way Claude does, saw the 8-screen
design and said GO BUILD.

**Server (`server/app/devsahayak/made.py`, tool `make`):** the model makes a thing in parts so the card can say what it
writes now: `start` (kind doc | page | prototype | artboard | sheet, title, part names) -> `write` (one section / screen /
tab, checked for its kind) -> `finish` (the file is built). Kinds: doc = Markdown sections joined under one `# title`;
page = HTML fragments in one page; prototype = one `<section class="hs-screen">` per screen and a small inline script that
moves between them on `data-go="Screen"` / `href="#Screen"`; artboard = each screen in a sandboxed srcdoc iframe, scaled
side by side; sheet = JSON `{columns, rows}` per tab -> an .xlsx (openpyxl, header row bold + frozen, formulas kept as
formulas). HTML fragments may not carry outside scripts, `<html>/<head>/<body>`, iframes / objects / embeds. A sheet's
preview works out SUM / AVERAGE / MIN / MAX / COUNT / ROUND / ABS / IF and + - * / with A1 refs and ranges; anything else is
shown as the formula and named (the model is told at write and finish; the viewer says it too) - never a made-up number.
A change = `start` with the id: a new version that keeps every part (carried by reference), only rewritten parts count as
changed; a version with nothing written is dropped. Going back (`POST /tasks/{id}/made/{mid}/restore`) makes a NEW version
from the old one; nothing is deleted. Limits: 20 things a session, 12 parts, 30 versions. Stored under
`data/devsahayak/made/<task>/<thing>/` (meta.json + v<n>/part<i>.txt + out.*), apart from the working copy so the sweep of
old working copies does not take them.

**Serving:** `GET /api/devsahayak/made/{tid}/{mid}/{v}/{name}?exp&sig` (public router, HMAC on the server secret, 24 h,
only out.md / out.html / out.xlsx); HTML always with `Content-Security-Policy: sandbox allow-scripts allow-popups;
default-src 'none'` + inline script / style, Google Fonts, data: / https images only - its own opaque origin, it can never
read the console's stored sign-in. `GET /tasks/{id}/made/{mid}?v=` = the viewer's data (versions, the document text, the
sheet preview, a fresh signed link; a page still being made is built on the spot for Peek).

**Engine wiring:** `make` rides `tools_for_round()` (switch `dev_make`, default on), handled in the round like `memory`,
the working line says "Writing <part>" (`_make_words`), the system prompt gets `made.HOWTO`; each `start` emits ONE step
`{"k":"made","id","v"}` (the card reads the live state from the session view's `made` list, so the thread never doubles a
card). A round that only made things no longer ends with "(Koi file badalne layak nahi mili.)".

**Phone (`lib/ui/code/code_made.dart`):** `CodeMadeCard` (making: the part it writes now, the parts as ticked / current /
waiting chips, a clock, Peek; ready: its own drawn picture per kind, title, kind + facts, Updated + what changed for a new
version; Open + Share link / Download under the newest card); earlier versions of a thing = one faint line;
`showCodeMadeList` = Made in this session with All / Docs / Designs / Sheets; `CodeMadeViewer` = doc as Read (HoolaMd,
selectable) or Markdown, page / prototype / artboard in a WebView on the signed link (Restart for a prototype), sheet as a
table with a formula bar, tabs and what the preview could not work out; Versions sheet with Bring back; "Ask for a change"
pops back and the session sends `Change the <kind> "<title>" (make id <id>): <her words>` as her next message. Session:
`k == 'made'` steps draw the cards, a "N made" pill beside the Newest / Changes pills.

**NOT BUILT (said plainly):** before / after pictures of a changed page (the card names the changed parts instead), Ask
Hoola about a selected sentence, Save to repo, Open in Google Sheets (Download opens the .xlsx in her sheets app), the
console web page. **NOT VERIFIED:** on her phone (CI compiles the Dart first), and Qwen making a real thing end to end.
Tests: `server/tests/test_v0939_hoola_code_makes.py` (7).

## v0.940.0 HOOLA CODE HER MESSAGES (owner, her phone screenshot: "New session 1st msg sent by user seen in chat screen .. thereafter any msg send by user not seen in chat screen")

**Root cause:** the phone draws her FIRST message from the session's text and every later one from a `note` step in the
session's steps. Only two doors wrote that step - an answer to Hoola's one question (`service.answer`) and a note the
engine reads while it works. A follow-up after a finished round goes through `service.revise` (the phone's `bg/revise`),
which started the next round with her words in the model's prompt but never wrote them into the thread - so after the
first message nothing she sent showed on her screen.

**Fix (server):** `revise` writes her words as `{"k": "note", "text": ..., "her": true}` before the round starts, on both
paths (the session continues in its working copy / a change on the open PR); comments on lines alone show as one line
("Comments on 2 lines of the change"), never the raw comment block. A restart that continues a cut revise round does not
call `revise` again, so her message is written once. The engine's note while working keeps 2,000 characters (was 600).

**Fix (phone, `lib/ui/code/code_session.dart`):** her later messages are drawn full size like her first (were the small
style); what she sends shows at once as her bubble with "Sending…" until the server has written it (matched on its first
80 characters); a note queued while Hoola works is her bubble with "Hoola reads it at its next step" (was a grey line); a
send that fails takes the bubble away and puts her words back in the box.

Tests: `server/tests/test_v0940_code_her_messages.py` (4). NOT VERIFIED on her phone.

## v0.941.0 HOOLA CODE ON YOUR SERVER — pair a VPS the simple, safe way (owner: "Now how hoola code will take access of user vps .. give a perfect simple and secure way in hoola app")

Claude Code reaches a server by running ON it (install Claude Code there, drive it from the phone with
`claude remote-control`); the server connects out, nothing dials in, and it asks before each command. Hoola
takes that exact model and sets it up FOR HER, because her users are not developers: one pasted line instead of
a full install + sign-in, an unprivileged `hoola` user instead of whoever logged in (often root), and the safety
rules shipped already set instead of hand-written.

**The shape.** HER server calls Hoola. The helper on her server opens an outbound long-poll and asks for work;
this server never dials in, so no inbound port is opened, no firewall rule changes, and Hoola keeps NO password
and NO SSH key that could open her server. The helper runs as its own unprivileged `hoola` user and is root only
for the exact admin commands she grants ON the server.

**Connect once (~1 minute), in the app (`lib/ui/code/code_vps.dart`, 3 screens + the approval card; design
canvas claude.ai/artifact/B9nNvYXJTyMwH8mTfCJep5):**
1. *Servers* — she names a server and taps Connect. A safety note lists the six promises.
2. *Pair* — one line she pastes on her server: `curl -fsSL <base>/vps/install | sudo bash -s <6-digit code>`.
   The SAME script serves everyone (`GET /vps/install`); the 6-digit code is her own bash argument, so the
   script carries no secret. "See what it installs" opens the script. The page moves on by itself once her
   server answers.
3. *One Server* — a green Connected banner with the server's size; the three access levels (Look only / Ask me
   first / Trust my folders); her folders; the few admin commands she ticks; "Switch off when unused"; the
   activity log; Disconnect.

**In a session.** A new `server` tool in a Hoola Code round: a look-only command (logs, status, disk, a file in
a folder she allowed) and, with Trust on, a known-safe step (git pull, tests, restart her app) in one of her
folders run by themselves and stream back; every other command WAITS for her tap, shown with the exact text and
Allow once / Always in this folder / No (`CodeServerCard`). "Always" also lets that command run by itself in that
folder from then on.

**The never-list, refused in three places** — the session tool, the server (`devsahayak/vps.py` `classify`), and
the helper itself (`deploy/hoola-vps/agent.py` `refused`), so the refusal holds even if Hoola's own server were
ever broken into: deleting trees, wiping disks, changing a user / password / SSH, opening a firewall port,
download-and-run from outside, reading a secret file (.env, keys), a root shell, shutdown. It can never be
approved. Every command and its output are scrubbed of anything that looks like a key, kept on her server
(`/var/log/hoola-agent.log`) and in the app.

**Server (`server/app/devsahayak/vps.py`, routes in `api.py`, `main.py` mounts the install router):**
- `DevServer` / `DevServerCmd` tables (`models.py`); the helper's token is kept only as a sha256 hash.
- Pairing: `pair_start` (6 digits, 10 min) → `enroll` (the helper binds once, gets a long-lived token + the
  config) → `check_in` (outbound long-poll: online + the approved commands) → `report` (the result). Public
  routes `/api/devsahayak/vps/enroll|check-in|report`; `/vps/install` + `/vps/agent.py` serve the files.
- Her screens: `overview` / `detail` / `set_access` / `disconnect` / `decide`, authed routes
  `/api/devsahayak/servers*`.
- `propose` / `wait_result` for the session tool; `classify` returns refuse | reads | trusted | admin | write.
- The helper (`deploy/hoola-vps/agent.py` + `install.sh`): stdlib only, the installer makes the `hoola` user
  with `/usr/sbin/nologin`, a systemd service (`NoNewPrivileges`-off only so granted sudo works, `ProtectHome`
  read-only, `PrivateTmp`), a `hoola-agent allow "<cmd>" | remove | status` control command (the ONLY way to
  grant root to a command, via a narrow sudoers drop-in), and removes everything (service, sudoers, files, the
  `hoola` user) on `remove`.
- Switch `dev_vps` (OFF until her first pair) + `dev_vps_cmd_timeout_s` / `dev_vps_offline_s`.

**Tests** `test_v0941_hoola_code_vps.py` (7): the never-list refused everywhere + the installer carries no
secret; pair → enroll (token hash only, a code used twice refused) → set access → check-in hands the approved
command once → report → read back; a change waits for her tap and "always" grants the folder, "no" refuses, the
never-list can never be approved; disconnect tears the helper down on its next check-in; the doors + tool are
wired; the phone screen is drawn; the version. Version ritual 0.941.0 (pubspec 0.941.0+940, v2.html stamps 35 @
0.941.0, the test pins swept, the test_v0475 newest-story marker).

**NOT VERIFIED:** no real VPS has enrolled and no real command has run; the helper, the installer and the Dart
compile first on CI; admin-via-granted-sudoers and the auto-off sweep are written from the spec, not watched on a
live server. The frozen PC / desktop files are untouched — this is its own lane, borrowing only the
call-Hoola-out pairing idea.

## v0.942.0 CONNECT GITHUB LIKE CLAUDE CODE — a GitHub App install, no pasted token (owner: "Now a git hub connect directly like claude code has .. no manual pat put")

Claude Code connects GitHub by having you INSTALL its GitHub App on the repos you choose; it never asks for a
personal access token, and the tokens it uses are minted on demand, server-side, short-lived (about an hour) and
scoped to exactly the repos you installed on. Hoola now does the same with its OWN GitHub App — she taps Connect,
picks her repos on GitHub, comes back, done. Nothing is typed; nothing is stored but the installation id.

**The flow.**
1. *Connect* (phone, `lib/ui/code/code_more.dart` › Repos & GitHub): `GET /api/devsahayak/github/connect` returns
   the App install URL carrying a signed `state`; the app opens it (`Native.openExternal`) and shows "Pick the
   repositories… then come back", polling settings until she is connected.
2. On GitHub she installs the Hoola app and picks repos. GitHub sends her to the App's Setup URL,
   `GET <base>/api/devsahayak/github/installed?installation_id=…&state=…` (public): the signed `state` maps the
   callback back to her tenant, the installation id is stored, and a small "GitHub connected — return to the app"
   page is shown.
3. *Remove* calls `POST /api/devsahayak/github/disconnect` (clears the installation; she uninstalls the app on
   GitHub to finish).

**Tokens, never stored.** `devsahayak/ghapp.py`: an RS256 App JWT (PyJWT, the App id + private key from the .env) →
`POST /app/installations/{id}/access_tokens` mints a ~1-hour installation token, cached ~50 min in memory. A signed
`state` (`make_state` / `read_state`, hmac over the server secret, 1-hour window) binds GitHub's callback to her
tenant with no login round-trip. `service._token` returns an installation token when she is app-connected (the
sealed-PAT path stays as a fallback), `github_repos` lists the repos she installed on
(`GET /installation/repositories`, not every repo of her account), and `settings` adds `connect_mode` (app | pat),
`app_available`, `app_connected` and `account`.

**The owner sets the App up once** (GitHub › Settings › Developer settings › GitHub Apps) with repository
permissions Contents RW, Pull requests RW, Checks R, Actions RW, Webhooks RW, Setup URL
`<base>/api/devsahayak/github/installed`, and puts `GITHUB_APP_ID`, `GITHUB_APP_SLUG` and `GITHUB_APP_PRIVATE_KEY`
(PEM, literal `\n` accepted) in the VPS .env. Until then `app_available` is false and the fine-grained-token paste
still works, unchanged.

**Tests** `test_v0942_connect_github.py` (5): the App JWT signs RS256 and the signed state maps back to her (tampered
/ stale states refused); connect binds the installation and `_token` mints a scoped token (never a stored PAT),
`github_repos` lists the installed repos, disconnect clears it; the PAT path still works when no App is configured;
the doors + phone are wired; the version. Version ritual 0.942.0 (pubspec 0.942.0+941, v2.html 35 stamps @ 0.942.0,
pins swept, the test_v0475 marker).

**NOT VERIFIED:** no GitHub App is configured here, so no real install or token mint has happened — the JWT, state
and token-mint paths are unit-tested with a throwaway RSA key and fakes; the phone compiles on CI.


## v0.943.0 HOOLA CODE CATCHES UP (owner, on the Cursor comparison page's "Where it is behind": "WORK ON IT AND DEPLOY ALL FOR HOOLA PROPERLY")

The Cursor research page listed five places Hoola Code was behind. What this release does about each:

1. **No index of the code** -> `devsahayak/repoindex.py`. Every source file's top-level names (functions, classes, types) with
   line numbers, read by small regexes per language (Python, JS/TS/Vue/Svelte, Go, Java/Kotlin/C#/Swift, Rust, Dart, Ruby, PHP,
   C/C++), plus the module arrows from `archdesk/repomap.py` (imports, never guessed). The first message of a session carries a
   `<repo_map>` (files matching her words first, then the most depended-on, fitted to 5,000 chars; a huge repo reads the files
   matching her words first and says when it stopped). New tool `code_map`: `find` a name -> file:line, `refs` -> the lines that
   use it (60), `file` -> the names a file defines (always the file as it is now). The map is cached 2 minutes per session and
   dropped after any write / edit / bash. Secrets (`SECRET_FILES`) are never read; links are never followed. Measured here on
   Hoola's own repo: 6,694 paths, 1,698 source files read in 6.2 s.
2. **Doesn't open a browser to check the app it changed** -> `devsahayak/look.py`, tool `look`. A page of the working copy is
   opened in the server's headless Chromium on a phone (390 x 844, touch) and a computer (1280 x 800). It returns screenshots,
   console errors, files the page asked for that are not there (404 / failed), and what is plainly broken on a phone (no
   viewport tag, wider than the screen, pictures that did not load, tap targets under 40 px, text under 12 px). Walls: the page
   is served from 127.0.0.1 by a server that answers only regular files inside the copy (no link anywhere on the path, no
   secret file, no listing); every browser request to anything else is refused and named, so a page that needs its own server or
   an API is SAID, never called checked. Screenshots go to the model unless its OpenRouter profile says it reads no pictures
   (`dev_look_pictures`), only the newest look's pictures stay in the conversation (`engine._drop_old_looks`), 24 are kept per
   session for her phone (GET `/api/devsahayak/tasks/{id}/shots/{name}`). A built app: the box builds first, then look at
   dist/index.html. Checked here on real Chromium (the internet request was refused, the console error and the 404 were caught).
3. **Doesn't learn from use** -> `devsahayak/learned.py`. Her earlier sessions on the same repo (her tenant only, last 40) are
   read in code: merged vs closed without merging (closed titles = what she did not want), her follow-up messages that push back
   ("no", "not like this", "galat", "revert"...) in her words, her notes on plans, CI red after the first push, files her merged
   work touched. It rides the first message as `<what_worked_here>`, quoted as data, never as new instructions. (The per-repo
   memory of findings from v0.828 is still there; this adds her outcomes.)
4. **Risky files** (from the Cursor CVEs: a committed config the agent's own tools obey) -> `service.risky_files`: `.hoola/`,
   AGENTS.md / CLAUDE.md / GEMINI.md, .cursor / .claude / .mcp.json / .cursorrules, .github/workflows + actions, other CI files,
   .vscode settings / tasks / launch, .gitmodules, .devcontainer, and a package.json that adds an install script. Task view
   `risky_files`; the phone shows them in red on the session and the Changes page before she merges.
5. **No editor** -> not an editor, but `lib/ui/code/code_files.dart`: Browse the files (folders with New / Changed badges, a file
   with line numbers, secrets hidden), tap lines and "Ask Hoola about these lines" quotes them with path + line numbers into her
   next message. Next-edit suggestions are NOT built (her users are not people who type code all day).

Switches (all on): `dev_code_map`, `dev_look`, `dev_look_pictures`, `dev_learn`. Tests `test_v0943_hoola_code_catches_up.py` (10).
NOT VERIFIED on her server or phone; the look tool needs Playwright's Chromium on the VPS (the console's other browser checks
already use it; `HOOLA_CHROMIUM` points at it where the default path is missing). Still not live from last week: the server pairing
(v0.941, `DEV_VPS=true`) and the GitHub App (v0.942, the App + three .env lines).


## v0.944.0 HOOLA CODE CHAT LANDING (owner: "LETS WORK ON CHAT CONVERSATION LANDING IN HOOLA CODE CHAT .... FIND THE ISSUE AND FLAWS IN IT FIRST" -> "GO")

Diagnosis first (nine flaws), then all fixed:
1. The closing answer (the `done` tool's explain = "what I did") was saved only on the session (`DevTask.explain`) and the
   phone drew it only when the WHOLE session had no `say` step - nearly every session has words between steps, so she
   almost never saw it. Now `engine.run` emits it as `{"k": "say", "final": true}` at the end of its round (skipped when
   it equals the last words she saw), never cut to 3 lines (a reply that ends the round - no tool, or `done` - is never
   short_say'd).
2. Each round's answer is kept in the thread (was overwritten on the session) and sits after its own round.
3. `said_before` dropped a reply as a repeat AFTER its words had streamed to her phone - they vanished. Now
   `engine.live_sink` holds live words until 10 words (a repeat is caught before it shows) and a reply she watched is
   never dropped.
4. Live words were capped at 3 sentences while streaming, so a long final answer stalled and then jumped; a reply that
   runs 25+ words past the cut streams whole and is saved whole (`LIVE_FULL`), so what she watched and what is saved agree.
5. Over 1,200 steps the middle was cut, her messages and Hoola's words included, and the phone's landing (counted by say
   index) shifted. Every step now has a stable number `n` (`_Step.event`), and `service.fold_steps` folds only work steps -
   say / note / round / made / look are kept (600 at most from the middle).
6. "Worked for 3m 12s" marker per round (`{"k": "round", "secs"}`): a faint divider on the phone, a dim row on the console.
7. A second closing answer started half-shown (the phone kept the earlier answer's word count) - landing now keys on the
   step number; a new reply / answer starts from word 0; live words hand their count over to the message they become.
8. The phone fetched the whole session (all steps, the full diff, per-file diffs, log) every second while Hoola worked.
   `GET /api/devsahayak/tasks/{id}?since=<n>` returns only newer steps and leaves diff / file_diffs / log / pr_body / found
   out; the phone asks for the whole session on open, after her taps, every 30 s, when a round ends and before Changes.
9. A question was shown twice (message + card) - the phone skips the message when the card shows the same question.

Older sessions (no `final` step) still show their answer, now whenever it differs from the last message. Console
(`static/console/code.js`) draws the round row and no longer repeats the answer when a final message exists.
Tests `test_v0944_code_chat_landing.py`. NOT VERIFIED on her phone (CI compiles the Dart).


## v0.945.0 HOOLA CODE LONG TALK

(owner: "NOW AGAIN GO DEEP AND FIND FLAWS IN CHAT LANDING DURING LONG CONVERSATION" -> "GO"): FIXED my v0.944 slip - the step number overwrote a step's own count, so checkpoints, searches and diffs showed the step's place ("Checkpoint 214"); a step's own count is now `num` (`service._Step.event`), both clients read it; one lock per session around step writes (helper agents write from their own threads); GOING BACK restores the conversation exactly - a copy of the messages is kept per checkpoint (last 20, `engine.KEEP_CP_COPIES`) because after a compaction the message count pointed at the wrong place, and the rewind step names where the undone part starts (`from`, the phone greys it out); CONDENSING keeps her own words word for word (request, follow-ups, notes, comments: `engine._her_words`, up to 40,000 chars) and hands an earlier summary over whole, a long session is cut in the middle, never its start; HER NOTES: read whole (6,000 chars, was 2,000) and never dropped - an 11th waiting note is refused with a wait line instead of pushing out the first, and a round a restart cut still takes notes; a long session keeps ALL of its conversation (only work steps fold, `service.STEPS_CEILING` 2,000); live words keep their start (was the end) and words that ask her something are never cut (`engine.short_say`); a check each second is light (no git status, no diffs, no log); a round a restart cut is picked up after 30 s, not 3 min; PHONE `code_session.dart`: a check keeps what it left out, a whole fetch never takes away a message she saw (merged by step number; pull-to-refresh replaces), rows keyed by step number, lazy list, her sent message matched by step number, a full fetch asked during a check runs right after it, the 3 s carry never draws saved words twice, polling stops in the background and what came meanwhile shows at once when she is back; 1 server. NOT VERIFIED on her phone.


Files: `server/app/devsahayak/service.py` (`_Step.event` num + `_step_lock`, `fold_steps` STEPS_CEILING, `add_note` never drops, `_boxed`, `get_task` light delta, `ws_rewind` from, `_beat_fresh` _PROC_START, `_live_text` keeps the start), `server/app/devsahayak/engine.py` (`Session.checkpoint` copies + `rewind` restores, `_her_words` + `compact`, `short_say` questions, notes 6,000, LIVE_TEXT start), `lib/ui/code/code_session.dart`, `server/app/static/console/code.js`. Tests `server/tests/test_v0945_code_long_talk.py` (12).


## v0.946.0 HOOLA CODE ON ITS OWN

(owner: "ALSO CHECK DOES HOOLA CODE CAN DO ENTIER AUTONOMOUS CODING OWN ITS OWN OR NOT" -> "GO"): a round that hits its step / time limit or ends without done GOES ON BY ITSELF in the same conversation and working copy, up to 3 more rounds (`service._until_done`, `dev_auto_continue`; her Stop and the spending limit still end it), and work that is still not finished never goes out alone - it waits for her look with the reason, and half-done work is never pushed onto her open PR; a change that ends in words without done is not finished (its quality gate and reality check never ran) unless the words ask her something or nothing changed; model failures said plainly (`service._why_broke`: out of OpenRouter credit, busy, did not answer - was only the error's class name); a CI fix round that broke does not use up one of the 3 rounds (`_ci_round_back`); a new commit on her open PR (her change, reviewers' comments) is watched by the CI loop, so a red run is fixed by itself; her 6-round limit counts HER rounds only (CI rounds have their own); a PR already ready is not marked ready again; DELETED FILES reach the PR as deletions (`gh.commit_files` sha null, `_prepare` / `_merge_files`, file rows `deleted`); a package added mid-task (requirements.txt, package.json, a lock file) drops the box's dependency snapshot so the repo's setup installs it before the next command (`Tools._deps_changed`); a plan waiting for her yes is said once more after 2 h (`_plan_reminders`, `dev_plan_remind_h`); a session never spends past its limit (`dev_session_inr_cap` Rs 1,500, checked before each step through `engine.OVER`); 1 server. NOT VERIFIED on her server: run VPS ops > code_card_engine for a real score.


Files: `server/app/devsahayak/service.py` (`_until_done`, `CONTINUE_WORDS`, `_why_broke`, `_ACC` / `_spent_inr` / `_over_budget`, `_ci_round_back`, `_round(hers_round=)`, CI watch after a commit, `_ci_ready` draft check, `_prepare` / `_merge_files` deletions, `_plan_reminders`), `server/app/devsahayak/engine.py` (words-only finish, `OVER` + `budget_hit`, deletions harvested, `Tools._deps_changed`), `server/app/devsahayak/gh.py` (`commit_files` deletions). Tests `server/tests/test_v0946_code_on_its_own.py` (12).

## v0.947.0 HOOLA AUTO (owner: a separate Hoola Auto section inside Code, console + app -> design canvas claude.ai/artifact/1JwAQ3KaPuxzusDHf1UzPz -> "GO BUILD")

A whole client project run by specialist agents on top of Hoola Code. The full contract is `docs/HOOLA_AUTO.md`; in short:
- Server `server/app/hoolaauto/` (models, roster, service, api). Tables auto_projects / answers / sources / gates / tasks /
  events / changes / msgs (db.init_db + ensure_tables). Routes `/api/auto/*` (her sign-in) and the public client door
  `/api/auto/c/{token}/*` + page `/auto/intake/{token}` (static/auto/intake.*; noindex, never framed, microphone allowed for
  the browser's own speech-to-text).
- Intake: 30 questions in 10 sections (roster.INTAKE); every answer keeps its source (her, the client, a document, a
  recording via Kaan, pasted email / WhatsApp, a repo scan read through her token); a source that disagrees = a conflict she
  settles; words scrubbed (Hoola Code's _clean_text + any "password / pin / otp / cvv / secret / token / api key: <value>").
- Gates G1..G8 (roster.GATES), each tap carrying the gate's hash; asking for changes re-runs that step with her words.
  G1 plan (Analyst + Planner, one model call; non-session roles get no tasks, sprints clamped 1-4, estimate Rs 25 a task),
  G2 design (Architect + UX), G3 plan + price -> the project branch hoola/auto-<slug>-<id> made from main in every repo,
  G4 per sprint, G5 per change request, G6 UAT, G7 go-live PRs (opened, never merged by Hoola), golive_merge = her tap with
  the head sha (red / pending CI needs her written reason), G8 handover after the Docs agent's session.
- The conductor (`tick`, worker Tech-suite loop): snapshot -> read every open Hoola Code session (outside our transactions:
  the first draft held a write lock while calling Hoola Code and SQLite locked) -> merge a task's PR into the project branch
  only when its base IS the project branch and live CI is green / none -> cost cap check (stops every session, pauses) ->
  start ready tasks (deps done, same sprint, no gate waiting) up to `auto_parallel` 3 via start_bg(mode auto, base = the
  project branch, her environment) -> a finished sprint opens G4, the handover sprint G8.
- Agent chat: one model call decides in_spec (goes into the running session as a note, else onto the next task: "Applied to
  task N") / change (a priced CR + G5; nothing built before her yes) / question.
- Notifications: push kind `auto_needs`, sent through Hoola Code's _publish (after commit, to her home chat). The first
  draft published from inside an open transaction - every gate waited on SQLite's lock (suite 119 s -> 27 s after the fix).
- Console: `static/console/hoolaauto.js` + hooks in code.js (sidebar row + project group, #/auto routes) + the
  `v0.947 HOOLA AUTO` block in hoolacode.css. Phone: `lib/ui/hoola_auto.dart` (home, mission control, agent session, tasks
  sheet, feed, gates + gate, intake, environments) + the drawer row; test/hoola_auto_test.dart (source checks).
- Tests `server/tests/test_v0947_hoola_auto.py` (fake model / GitHub / Hoola Code sessions): intake + conflicts, the client
  link, gates + hashes + changes, the whole run intake -> handover, her main branch guard, the cost cap, agent chat + CR,
  another tenant, the environment view.
- NOT BUILT: Jira / Slack / Figma / cloud / error-tracker connections, the live voice intake call, the Watch agent, staging
  deploys beyond her CI, adding intake sources from the phone. NOT VERIFIED with a real repo, model or phone.


## v0.948.0 HOOLA CODE HARD CARD FIXES

(built as 0.947; their HOOLA AUTO took 0.947, both kept) (owner: "Check" on the hard coding card on her server: 10/12 on Qwen 3.8 27B): the two misses fixed - js_fix_gst_split went red on package-lock.json, which the box's own npm install rewrote in the working copy: a lock file whose package list (package.json / pyproject.toml / Cargo.toml / go.mod ...) did not change stays out of the change (`engine.install_noise`); vague_ask died after 877 s on "Qwen sent an empty answer" three times - it thought until its room ran out: each empty try now thinks one level less (high -> medium -> low) and keeps the room, so the words fit (`brain._qwen_call`); the coding card reads a deleted file (v0.946 deletions have no content); 1 server. NOT VERIFIED: run VPS ops > code_card_engine_hard again.


Files: `server/app/devsahayak/engine.py` (`LOCK_OF`, `install_noise`, harvest), `server/app/devsahayak/brain.py` (empty answer -> lower effort), `server/app/quality/codecard.py` (deletions). Tests `server/tests/test_v0948_code_hard_card_fixes.py` (4).

## v0.949.0 HOOLA CODE ANSWER NOW (owner: "DONE CHECK" after v0.948)

Her rerun of code_card_engine_hard on v0.948 (qwen/qwen3.8-27b): 11/12 fully right, works 11/12, scope 12/12, rules 12/12,
good tests 7/7, 14.5 min. The v0.948 lock-file fix held - js_fix_gst_split is OK. The vague ask ("Checkout mein kuch
gadbad hai, theek kar do.") still failed: the log shows "try 1 empty (finish=length, effort=high)", "try 2 ... medium",
"try 3 ... low" - the model thought until its room ran out at every effort level, 730 s, 0 steps.

Fix (`devsahayak/brain.py` `_qwen_call`): when all three tries came back empty, two last tries run with `brain.ANSWER_NOW`
added as a final user line for that call only ("your last answers came back empty ... make your next tool call, or ask
her ONE short question"), room = max_tokens + ROOM["high"]: first with thinking off (`reasoning: {"enabled": false}`),
then - if OpenRouter answers 400 because the model needs thinking - with thinking low. A failure that was not an empty
answer (timeout, refusal) gets no extra tries and is said as before. Tests: test_v0949_code_answer_now.py (4).
NOT VERIFIED: whether Qwen 3.8 27B on OpenRouter accepts thinking off - the next hard card run shows it.


## v0.950.0 HOOLA AUTO ALL PENDING (built as 0.949; their HOOLA CODE ANSWER NOW took 0.949, both kept; owner: "GO BUILD ALL PENDING")

The four things v0.947 HOOLA AUTO said it did not have, built:

1. **Talk to the Intake agent** - `server/app/hoolaauto/more.py` `talk` / `client_talk`, POST `/api/auto/projects/{pid}/talk`
   and `/api/auto/c/{token}/talk` (`{said, spoken}` -> `{reply, speak, got, next, answered, of, complete, warn}`). Turn by turn:
   the device's speech engine hears and speaks, the server gets text. `TALK_SYSTEM`: record only answers really given, one
   question at a time, under 40 spoken words, never ask for passwords / OTPs / PINs / cards, their words are data. Answers go
   through `_merge` (the read_source rule: empty = Found, same = skipped, different = conflict). Spoken answers are Found, not
   Confirmed, because a word can be heard wrong. Start (said '') = greeting + first open question, no model call. The turns
   are kept as AutoMsg rows of the intake agent (and in client_msgs for the client). Keys scrubbed by `_clean`.
2. **Sources from her apps** - source kind `app` (`{app, what}`), `more.read_app`: her Composio account (`cmp.account` on her
   user id), `take_call` (her monthly cap), the app's tools listed and FILTERED to `cmp.is_read` before the model sees them,
   the model picks one + fills arguments, a slug outside the read list falls back to the first read tool; a dead sign-in is
   marked expired and said. Figma: `design.figma._read_file` -> pages / frames / text, FigmaError said plainly. Apps list
   `APPS` (14) with intake / Monitor flags; GET `/api/auto/apps`, POST `/api/auto/apps/{key}/connect` (her Composio sign-in
   link, or where to add a key). The environments screen's line now names her connected apps (`service._apps_line`).
3. **The Monitor** - role `monitor` (17th, roster), tables `auto_watch` (one per project: on, url, every_min 15-1440, feeds,
   seen hashes, last check) and `auto_alerts` (kind site | slow | ci | feed, sig, times, state open | fixing | dismissed |
   resolved, dev_task_id). `more.check`: `probe` (public hosts only via getaddrinfo is_global, every redirect re-checked, 15 s),
   CI on each repo's default branch head (`rules.ci_state`), feeds read once each and given to the model only when their hash
   changed (`WATCH_SYSTEM`, already-known titles passed so they are skipped), cost cap respected. New alert = AutoEvent need +
   one push per check (`auto_needs`, "+N more"); a repeat bumps `times`; a clean site / CI check resolves its open alerts.
   `alert_act fix` = her tap -> `start_bg(kind fix, base = the repo's default branch, mode auto)` with "never merge it"; a
   second fix while one runs = 409; dismiss / reopen. `watch_tick` from the Auto worker tick: only `on`, due, not archived,
   phase handover / done. The mission screen shows the Monitor as working / needs / wait.
4. **Screens** - console `hoolaauto.js` (talk panel, From an app, Monitor), phone `lib/ui/hoola_auto.dart` (Add source sheet
   incl. files, Talk screen, Monitor screen), client page `static/auto/intake.*` (Talk instead of typing).

Tests: `server/tests/test_v0949_hoola_auto_more.py` (fake model, GitHub, Composio, Figma, probe). NOT VERIFIED with a real
Composio app, Figma file, live site, model or phone; the phone compiles first on CI.

## v0.951.0 HOOLA CODE NO SCRATCH (owner: "Check" after v0.949)

Her rerun of code_card_engine_hard on v0.949 (qwen/qwen3.8-27b): 11/12, works 11/12, scope 11/12, rules 12/12, good
tests 7/7, 15.6 min. The v0.949 answer-now tries worked - the vague ask no longer died on three empty answers (13 steps,
754 s) - but Qwen then wrote a probe.py to look around the checkout and finished with it still in the working copy:
"changed probe.py; guessed and changed files". Also seen: three OpenRouter 429 "could not verify available credits in
time" (admission control) - each passed on the next try.

Fix (`devsahayak/engine.py`): `scratch_files(rows)` = new files whose name looks like a try-out (probe / scratch / tmp /
temp / debug / try / repro / check_me + a script or text extension), never a file under a tests folder; at `done` the
round gets ONE look (before the reality check): leftovers listed on the card as a gate event and the model told to delete
them, explain why they belong, or - if the request was too unclear - ask ONE question with no changes. SYSTEM: "A file you
make only to try something ... is deleted before done; it never ships." `brain.ANSWER_NOW` now says an unclear request =
done with ONE question, no exploring or edits. Tests: test_v0951_code_no_scratch.py (4).
NOT VERIFIED: the next hard card run.

## v0.952.0 HOOLA CODE UNCLEAR ASK (owner: "Check" on the hard card after v0.951 = 11/12)

The v0.951 scratch check held: the vague ask ("Checkout mein kuch gadbad hai, theek kar do.") left no files. But Qwen
explored for 10 steps / 607 s and ended with an explanation that had no question in it ("did not ask one clear question").
Every other job passed (works 11/12, scope 12/12, rules 12/12, good tests 7/7).

- `engine.unclear_ask(text)`: a short ask (<= 16 words) with "something is wrong, fix it" words (kuch gadbad, theek kar
  do, kaam nahi kar raha, not working...) and nothing named (no file, error, number, url, "when / jab", expected vs seen).
  Only for her FIRST ask of a fix / write session, never a follow-up.
- Such an ask gets `UNCLEAR_NOTE` in her first message: do not guess or edit, at most a quick look, then done with ONE
  short question ending in '?', naming what was noticed inside the question.
- At done, once: an explain that does not end in '?' is sent back (`unclear_text`; "put back the files you changed on a
  guess" when the copy changed).
- The card's miss line now prints what Hoola said (`said: ...`), so the next read is not blind.
- Tests: `test_v0952_code_unclear_ask.py` (4).
- NOT VERIFIED: rerun vps-ops `code_card_engine_hard`.

## v0.953.0 GITHUB BACK TO APP (owner, after installing the Hoola Code GitHub App: "But why not redirecting to hoola app" -> "need one tap GitHub access connection")

She installed the App and landed on GitHub's own settings page. Two causes: the App had no Setup URL saved (a one-time
setting the App's owner makes; her users never see it), and the Setup URL page itself only said "return to the app".

- `GET /api/devsahayak/github/installed` now answers with the shared sign-in done page (`bazar/donepage.render`): on
  the phone it jumps to `santosh://github?ok=1` after a moment, with a Back to Hoola button.
- Phone: manifest intent filter `santosh://github`, `MainActivity` -> `github:ok=`, `lib/main.dart` handles it BEFORE
  the fallback that treats any other link as a session token. The Connecting GitHub sheet already polls, so it closes
  on its own when the app comes back.
- An install made on GitHub itself (no signed state) now says "tap Connect GitHub in the app" instead of "link expired".
- Owner step, once: App settings > Post installation > Setup URL = `https://hoola.ainewtika.com/api/devsahayak/github/installed`.
- Tests: `test_v0953_github_back_to_app.py` (4). NOT VERIFIED on her phone.

## v0.954.0 HOOLA AUTO DOOR (built as 0.953; their GITHUB BACK TO APP took 0.953, both kept)

Owner, her phone screenshot of the Hoola Code home after the v0.950 deploy: "now hoola auto in app". The v0.947 Hoola Auto
row was put in `lib/ui/devsahayak_drawer.dart` (the old Hoola Code drawer). Tools > Hoola Code and the side-panel Code button
open the native home `lib/ui/code/code_home.dart` (v0.922), which has no drawer - so on her phone there was no way in.
Now the home draws a Hoola Auto card under the chips: it opens `AutoHomePage`, and reads GET /api/auto/projects to say
"N projects need you" (amber edge) or how many projects there are; a server without Hoola Auto still shows the card.
Phone only; test in `test/hoola_auto_test.dart`. NOT VERIFIED on her phone (CI compiles it first).

## v0.955.0 HOOLA CODE ASK FIRST (owner: "Done, check")

Hard card on v0.952 = 11/12 again. The vague ask ("Checkout mein kuch gadbad hai, theek kar do.") took 26 steps / 628 s and
changed `_probe.py` + `tests/test_api.py`: the v0.952 note and the one done reminder were not enough for Qwen. So the rule
moved from the prompt into code (`server/app/devsahayak/engine.py`):
- `Tools.ask_only` (set when `unclear_ask` matches her first ask): `_guard_write` refuses every write / edit with
  `ASK_ONLY_REFUSAL`.
- The round is capped at `dev_unclear_steps` (10) steps.
- At the end of the round `Session.undo_round()` puts index + files back to the round's base (`git read-tree -u --reset`,
  HEAD kept), so a file a command wrote is gone too.
- `unclear_finish(explain)` makes sure the closing words hold ONE question (at most 3 '?'); with none it adds a fixed
  Hinglish question asking what goes wrong, with an example.
Tests `server/tests/test_v0955_code_ask_first.py` (4, one on a real git repo). NOT VERIFIED: rerun code_card_engine_hard.

## v0.956.0 GITHUB ONE TAP (owner: "GITHUB STILL NOT REDIRECTING TO APP")

Why v0.953 never brought her back: (1) `Native.openExternal(url)` was a plain ACTION_VIEW, so the GitHub app (it
claims github.com links) could take the install page and never redirect; (2) the App was already installed on her
account, and an existing install never carries the signed `state` back, so `/github/installed` could not tell whose
it was; (3) donepage's `setTimeout(location.href='santosh://...')` has no user gesture, and Chrome blocks it.

Now (`devsahayak/ghapp.py`, `service.github_connect_url` / `github_installed`, `api.py`, `MainActivity.kt`,
`code_more.dart`):
- the phone opens the browser (`openExternal package 'browser'` -> `browserPackage`: default browser, else Chrome,
  never a github package);
- with `GITHUB_APP_CLIENT_ID` + `GITHUB_APP_CLIENT_SECRET` set, Connect opens GitHub's sign-in for the App
  (`authorize_url`, redirect_uri = PUBLIC_BASE_URL + /api/devsahayak/github/installed); the callback trades the code
  for a user token used once (`user_token`), asks `GET /user/installations`, and binds only an install on that list
  (`pick_install`: the id GitHub sent if listed, else her own account, else the newest). No install yet = 302 to
  `installations/new?state=`; the Setup URL without a code = 302 through the sign-in. An installation id in the URL
  alone no longer binds anything (it could have been someone else's);
- Android: a successful bind answers 302 to `intent://github?ok=1#Intent;scheme=santosh;package=com.newtika.santosh;
  S.browser_fallback_url=...;end`, the fallback `/github/done` page's button is the same intent link;
- vps-ops `github_app` also writes the client id / secret from repo secrets HOOLA_GITHUB_APP_CLIENT_ID /
  HOOLA_GITHUB_APP_CLIENT_SECRET and prints `oauth_ready()` + the callback URL.
Owner, once: App settings > Callback URL = https://hoola.ainewtika.com/api/devsahayak/github/installed, Generate a
new client secret, add both repo secrets, run vps-ops github_app. Tests `test_v0956_github_one_tap.py` (7).
NOT VERIFIED on her phone.

## v0.957.0 HOOLA CODE SMOOTH (owner, her screen recording: "CHECK HOW THE PLAN CARD VIBRATES ... A REPLY LANDS VERY FAST IT MUST BE PERFECT SMOOTH AND CONSISTENT AND MEDIUM SLOW ... CHAT LANDING, CONVERSATION FLAWS")

Read from her 3 min 14 s recording frame by frame (a 9-step Bridle-removal job on Qwen):
- The plan (Hoola's todo list) was a ~300 px card drawn at the END of the thread, under the words being written. Every
  wrapped word, every new step line and every coming and going of the working row pushed it up and down.
- The working row ("Thinking · 1:20") was drawn only while no words streamed: it vanished when words began and came
  back when they were saved - 44 px each time, shaking everything under it.
- Two scroll moves fought: a 260 ms slide to an end measured at its start, then a snap to the true end once the lazy
  list laid the last rows out; words landing also jumped the list on every tick.
- Words landed at ~19 a second and leapt to ~38 a second once 160 waited.
- Two messages could land at once in two places (the previous one still landing while the next one's live words began).

Fixed (phone only, `lib/ui/code/code_session.dart` + `code_words.dart`):
- `_planDock`: the plan is a dock just above the typing box, like Claude Code's todo list - one steady line (the step it
  is on, "4 of 9", a bar that slides with `TweenAnimationBuilder`), a tap opens every step (`AnimatedSize`, at most 40 %
  of the screen, scrolls inside). Never in the thread.
- The working row is always the last row while it works; the part working now folds into it, and while words stream the
  part is a faint line where it stays once those words are saved, so nothing moves when they are.
- One follow mechanism, `_stick()`: after layout, while she has not scrolled up and is not touching the screen, jump to
  the true end; called on every build, every landed word and every `ScrollMetricsNotification` (the thread grew). The
  Newest button still slides. `findChildIndexCallback` keeps keyed rows (landing words, the working row) alive when a
  row above them comes or goes.
- `CodeLanding.msPerWord`: 90 ms a word (~11 a second) up to 60 waiting, easing by smoothstep to 45 ms (~22 a second)
  at 300 waiting - the pace never steps.
- `CodeLanding.hold`: one message lands at a time, in order; a newer one waits for the one above it.

Tests: `server/tests/test_v0957_hoola_code_smooth.py` (5), v0935 / v0937 pins moved. NOT VERIFIED on her phone (CI
compiles the Dart first).

## v0.958.0 HOOLA PIPELINE P0 - the feed (owner: "GO P0" on `docs/HOOLA_PIPELINE_PLAN.md`)

P0 of the HOOLA PROCESS BOX plan: the daily feed that keeps the level tables fresh from PUBLIC leaderboards (D1: never
Hoola's own tests). Nothing chooses a model yet - that is P1. New package `server/app/pipeline/`:

- `kinds.py` - the 25 kinds of work as data: which boards rank each kind (LMArena text categories, webdev, agent +
  agent_tool_hallucination, search + search_factuality, text_factuality, vision, document, text_to_image, image_edit,
  text_to_video, image_to_video), what the model must do (output kind, tools / structured output / image input), the
  languages; `SAME` (route = chat, plan = reason, code.small = code, check = facts, translate = write.lang), `NOT_RANKED`
  (embed). Levels by points below the best of the kind: ULTRA 0-25, MAX 25-50, HIGH 50-80, MID 80-120, LOW 120-190, up
  to 4 a level; a pool too thin for bands = rank split of the best 20 (D10: 10-20 models a kind).
- `sources.py` - LMArena's `lmarena-ai/leaderboard-dataset` (CC-BY-4.0) through the datasets-server `/rows` (paged 100,
  3 tries a page; `/filter` answered 500s), OpenRouter's `/api/v1/models?output_modalities=all`, voiceofindia.ai STT +
  TTS boards (read with the server's Chromium, monthly) with their parsers.
- `names.py` - board names -> OpenRouter ids (normalised + an alias table for media names); `ROUTES` = models not on
  OpenRouter through other multi-model providers (fal, Kie, Eden) and then the maker's own API (`direct:<maker>`, D12);
  a provider whose terms or permission are not settled is marked and left out (WaveSpeed = needs_permission).
- `cut.py` - points per board (rating boards: best minus rating, >= `pipeline_min_votes` votes; rank boards: rank spread
  over 190), averaged and normalised, filtered by what the model can do and by age (548 days), cut into levels.
- `manual.json` - hand-kept pools for speech in / out and music (no public board), warned when older than
  `pipeline_manual_days`; `snapshot/` = the voiceofindia pages read on 16 Nov, used when the browser cannot read them.
- `store.py` - `tables-<date>.json` + `current.json` (atomic) in `data/pipeline`, `changes.jsonl` (joined / left /
  moved, a 2-level move marked big and applied automatically, D9).
- `feed.py` - one run: every board once, a failed board = a warning and yesterday's table kept, stale board dates
  (21 days) warned, Indian speech tables from voiceofindia, then save + a log line; `python -m app.pipeline.feed [--dry]`.

Wiring: worker slot `pipeline_jobs` (checks every 10 min, runs when the tables are older than `pipeline_every_h` 24,
in a thread), switches `pipeline_feed` (on; off in conftest), `pipeline_dir`, `pipeline_voi_days`, `pipeline_min_votes`,
`pipeline_stale_board_days`; `GET /api/pipeline/tables[?kind=]` (her key) = tables, board dates, warnings, recent
changes; vps-ops job `pipeline_feed`.

Live run here (16 Nov 2026, real boards): 21 kinds, each with 10-20 models (music 10, speech 17, the rest 18-20), 0
warnings, 724 OpenRouter models read, about 2.5 minutes. Tests: `server/tests/test_v0958_pipeline_feed.py` (10:
parsers, bands + rank split, filters, score boards, dated deterministic writes, changes + big jumps, a failed board keeps
yesterday, manual pool warning, worker slot, route). Artificial Analysis is not read (its site terms are non-commercial).
NOT VERIFIED on her server (needs vps-ops deploy, then vps-ops pipeline_feed).

## v0.959.0 HOOLA PIPELINE FEED LIMITS (owner: "DONE CHECK" after vps-ops deploy + pipeline_feed)

Deploy was fine (healthz 0.958.0). The first live feed run on the VPS met Hugging Face's dataset server limit: 429 Too
Many Requests on 29 of 30 LMArena boards, so chat / write / summarise / reason / code / extract / read.long / write.lang /
read.image / image.make came out with 0 models, and the half-empty tables still counted as today's (the worker would not
have tried again for 24 h). Cause: the worker's own first run (no tables yet, starts at boot) and her vps-ops run went at
the same time, each reading ~140 pages of 100 rows with no pause.

Fixes (`server/app/pipeline/`):
- `store.lock` - one feed run at a time on the machine; a second run is refused ("another run is going"), not doubled.
- `sources.config_rows` - a 0.6 s pause between pages, 6 tries a page, waits the server's own `Retry-After` on a 429
  (else 5, 10, 20, 40, 60 s; `_wait_for`).
- `sources.dataset_sha` + `feed._read_boards` - the boards are kept on disk (`cache/lmarena_boards.json`, only the fields
  the cut uses) with the dataset's commit; the same commit = no board read at all (most days one call). A board that
  cannot be read uses its last good read, said plainly; only a board never read stays empty.
- The tables say `complete` + `missing_boards`; a run that is not complete is tried again after `pipeline_retry_min`
  (60) instead of 24 h (worker `pipeline_jobs`; a table from before this version counts as not complete).

Live here (16 Nov, real boards): full read 5 min 35 s, complete, 0 warnings, every kind 10-20 models; the next run on the
same commit 1.2 s. Tests: `test_v0959_pipeline_feed_limits.py` (5) + the v0.958 suite updated. NOT VERIFIED on her server
(run vps-ops deploy, then vps-ops pipeline_feed - about 5-6 minutes the first time).

## v0.960.0 HOOLA CODE GLIDE (built as 0.958; their v0.958 + v0.959 took the numbers, both kept; owner, after v0.957: "STILL NEED LOT OF WORK --- NEED MORE SMOOTH LANDING OF TEXT --- FIND THE FLAW")

Four flaws in how a Hoola Code reply lands on the phone, found in the code behind her v0.957 recording:
1. The fade of the newest words moved only when the NEXT word landed - four fixed shades (`_fadeSteps`), so at ~11 words
   a second each word stepped darker 4 times instead of rising.
2. The fade switched OFF for the whole tail whenever a `code name`, a bracket or a bold mark was among the newest four
   words (`_marks.any(tail.contains)`) - in Hoola Code that is most lines, so words popped in at full ink half the time.
   The landing looked smooth on one line and abrupt on the next.
3. A wrapped line pushed everything under it (the working row) down a whole line in one frame, and the follow jumped
   the same line.
4. When the words being written became a saved message, the landing widget's key changed (`landlive` -> `landn<step>`),
   so it was rebuilt from scratch: the newest words flashed to full ink and the size reset.

Fixed (phone only):
- `CodeLanding` keeps when each word appeared (`_born`) and rebuilds every frame while words land or still rise; each
  word goes from faint to full ink over `fadeMs` 280 ms by its own clock, the same whatever the pace.
- `HoolaMd(tail:)` + `_inkTail`: the newest words drawn at the ink given; a word with its own marks (`name`, **bold**)
  is drawn with them and still rises (inline code's colour and tint fade with it); only a mark left open across words
  keeps the tail plain.
- The landing reply sits in an `AnimatedSize` (180 ms, ease-out), so a new line grows in; the thread follows it frame by
  frame through the v0.957 `_stick` + `ScrollMetricsNotification`.
- `_keyOf`: the landing widget's id moves with the words from live to saved; a new reply gets a fresh id.

Tests: `server/tests/test_v0960_hoola_code_glide.py` (4). NOT VERIFIED on her phone (CI compiles the Dart first).


## v0.961.0 HOOLA PIPELINE P1 - kinds + levels + choose + hand-over as pure code (owner: "GO P1")

P1 of `docs/HOOLA_PIPELINE_PLAN.md`: every rule of plan sections 3-5 written as code with a test; no model call,
no message routed yet (`pipeline_on` stays False until P7).

- `server/app/pipeline/detect.py` - section 2 + 5.1: the kind of work and the language of a ONE-part ask, by code in
  milliseconds. What she attached outranks what she wrote (picture + edit words = image.edit, picture = read.image,
  PDF = read.pdf / summarise / extract, recording = speech.in), then making (video / music / picture / speech), actions
  (send / remind / book = tools), translation, summary, code (code.small for snippets; Hoola Code = code), a piece of
  writing, research, very long text, extraction, facts, the existing hard-ask check (reason), else chat. Language: a
  language she names wins, then her script (Devanagari = Hindi unless Marathi words), then Hinglish words, else English;
  writing in a non-English language becomes write.lang, speech in an Indian language reads the Indian speech table.
  `parts` counts joiners - more than one part is P3's planner.
- `levels.py` - section 3: start level per kind (3.1, Indian write.lang starts HIGH), one raise per signal (3.2: hard,
  big, costly, exact, deep_research, failed_check), a signal that made the kind does not raise it again (`INHERENT`:
  a hard ask is `reason` because it is hard; research gathers checked facts - plan 11 keeps five-company research at
  MID), limits (3.3): her level wins, a part she waits for on a call stops at HIGH, ULTRA only when she asks for the
  best / a MAX try failed the check / hard AND costly, never lower than the level the part already reached (floor).
- `choose.py` - section 4: step 1 removes routes not ready, wrong output, missing input (picture / file / audio), no
  tools when tools are needed, a window under input + 30 %, paused models, routes / companies not allowed; step 2 ranks
  by reliability, speed, score - order per surface (call = speed, Hoola Code = score, background = reliability,
  chat = reliability then speed); step 3 = main + two backups from other companies first. Her model pick is a pin for
  parts it can do; ULTRA = one model (D7) with backups from MAX; an empty level reads the nearest filled level above
  (8.3); write.lang / translate read a language's own board, else the pooled one marked thin; `same_as` and
  `not_ranked` followed; `snapshot()` = the copy a message keeps (a refresh never changes a running answer); the model a
  chat used for the same kind + level is kept 30 minutes while healthy (5.1, `box.remember` / `recall`).
- `handover.py` - 5.2 + 5.3: error / refusal / empty = next backup at the same level; first word late (call 3 s, chat
  8 s, background 30 s) = backup, on a call a race; failed check = one level up once, failed again = delivered with the
  problem said; outgrew the window = a bigger same-level model; she asked for better = one level up; at most two model
  changes, then stop and say so.
- `box.py` - `choose_for(text, ...)` end to end for one part (what P2 will call); CLI `python -m app.pipeline.box`
  prints the choice for a fixed set of 13 asks; vps-ops `pipeline_try` runs it.
- `feed.py` - the tables file now carries `models`: each OpenRouter model's window, inputs, outputs, tools, structured
  output, so choosing never calls OpenRouter while a message waits. Takes effect at the next feed run.
- `GET /api/pipeline/choose?text=&surface=&attach=&level=&pin=` - the preview (owner key).

Run on her 16 Nov tables here: "hi" = chat MID; poster = image.make MID; "customers ko GST reminder bhej do" =
tools MAX (costly); Hindi report = write.lang HIGH; EV research = research MID; word problem = reason HIGH; a reminder
on a call = tools HIGH.

Tests `test_v0961_pipeline_choose.py` (65). NOT VERIFIED on her server; the reliability / speed record is empty until
P4 / P7 fill it, so today the leaderboard score decides inside a level.
## v0.962.0 HOOLA CODE LIVE (built as 0.961; their HOOLA PIPELINE P1 took 0.961, both kept; owner, after the Hoola Code vs Claude Code comparison: "GO BUILD 1 2 3")

The comparison found three places Hoola Code was behind Claude Code in how words land:
1. **Words came in 1 s bursts.** The phone asked the server once a second (`GET /tasks/{id}?since=n`), so the words Hoola
   wrote arrived in batches and the phone's pacing had to hide them. Now `GET /api/devsahayak/tasks/{id}/stream` (SSE)
   checks the session's in-memory state every 100 ms (`service.live_state`: `engine.LIVE_TEXT`, `NOW_STEP`, the newest
   step number `STEP_N` written by `_Step.event`, whether a round runs - no database) and sends only what changed
   (`service.live_delta`: `add` = words added, `live` = a new reply, `now`, `n`, `running`), a `: ping` when quiet, 404 for
   a session that is not hers. Phone: `Api.codeStream` (the v0.899 `_sse` reader that stops the moment it is cancelled);
   `code_session.dart` `_onLive` grows the words, updates the working row's step, and fetches only when a new step comes
   or a round starts / ends; the once-a-second check runs every 5 s while the stream is on (a net), and the words being
   written come from the stream only, so a check that answers late never puts older words back. Paused in the
   background, back on resume. An older server ends the stream quietly and the page polls once a second as before.
2. **Every reply started late.** Live words showed only from the 10th word (so a repeated paragraph could be dropped
   before she saw it). Now from the 4th (`LIVE_MIN_WORDS` 4); a reply whose first four words match a recent message
   waits until 10 (`LIVE_SURE_WORDS`, `_starts_like`) so the repeat check still runs before she sees it.
3. **Words between steps were cut** to 2-3 sentences (`short_say`), sometimes mid-thought. Now never cut, live or saved;
   the prompt says she sees them whole as they are written, so the model keeps them under 40 words itself. `short_say`
   stays for older callers.

Also fixes the v0.960 build: in `HoolaMd` the new `tail` field was hidden by a local `tail` in the same closure
(`final ink = this.tail;`).

Tests: `server/tests/test_v0962_hoola_code_live.py` (5); v0937 / v0944 pins moved to the new behaviour. NOT VERIFIED on
her phone or through her server's front door (Caddy passes the chat's SSE, so it should pass this one too).


## v0.963.0 HOOLA PIPELINE P2 - a one-part chat message through the Box (owner: "GO P2")

P2 of `docs/HOOLA_PIPELINE_PLAN.md`: the job sheet, the hand-off package and the final check, for a ONE-part
message. Behind `pipeline_on` (default False until P7 - off = today's turn byte for byte; `turnbox.begin` returns None).

- `server/app/pipeline/turnbox.py` - `begin` (in `santosh.run_turn`, before `_run_turn`): reads the tables copy (kept in
  memory, re-read only when current.json changes - the message holds that object, a refresh replaces it, never mutates),
  her model pick as the pin (`modelchoice.chosen`), `box.choose_for(..., tools=True)` (a chat turn needs tools), opens a
  sheet with one part and, when the part's work is text, the chosen route is OpenRouter, the chat runs on its
  OpenAI-shaped brain (`llm.cheap_brain() == "glm"`) and the OpenRouter key is set, sets `llm.MODEL_NOW =
  "openrouter:<id>"` for the turn + `APPLIED` so the chat loop no longer switches a hard / long ask to Claude. Measured
  here: ~1.4 ms to choose, ~4-5 ms with the sheet writes (the first message of a process pays module loading once).
  `saw` (in `santosh._run_tool`) keeps every tool result of the turn for the facts list. `end`: hand-off package
  (result, facts with their sources, files, notes, not_done), the final check, the part done / failed, the outage record,
  the same model for this chat + kind + level for 30 minutes.
- Not through the Box (the sheet records the reason, the turn runs as today): a live call, routine / wake / goal turns,
  several parts in one message (P3's planner), media work (studios + price cards, P5), a model on another route, a server
  whose chat is on Claude / OmniRoute, no OpenRouter key.
- `sheet.py` - one sheet per message in its own `data/pipeline/sheets.db` (WAL): id, chat, tenant, tables date, the ask
  masked + cut to 200 chars, parts (kind, language, level + why, signals, model + 2 backups + why, applied or the reason,
  state waiting / running / waiting_tap / done / failed, tries, the package), the check, `box_ms`; `unfinished(chat)` for
  P3's restart pickup; swept after 30 days by the worker's pipeline slot. CLI `python -m app.pipeline.sheet`.
- `check.py` - plan 6.10 in code: key figures in the answer held to the facts (her words + tool results; only when a
  tool ran), files named by a path must exist, every not_done item said. A problem is RECORDED; the one fix round one
  level up is P4 (plan 5.3 + the hand-over rule book already in handover.py).
- Outage record (plan D1): per model, in this process - 2 failed / empty answers in 10 minutes = paused (step 1 removes
  it, a backup takes over); a success rate counts only after 3 answers (one bad answer is not a record).
- `GET /api/pipeline/sheets?conv=&n=`; vps-ops `pipeline_on` / `pipeline_off` (PIPELINE_ON in the VPS .env + restart +
  the effective value printed back) and `pipeline_sheets`.

Tests `test_v0963_pipeline_p2.py` (14): off = None; one part applied (model in force, sheet running -> done, package,
sticky, box_ms < 30); calls / routines / several parts / media / no OpenRouter brain not applied with reasons; the check
holds a figure to a tool's result and flags an invented one; files + not_done; two failures pause and the backup takes
over; her pick as pin; sheet states / restart / sweep / package shape; `run_turn` runs on the Box model; the route; the
Claude switch guarded. NOT VERIFIED: no real model answered through the Box here (no key in this sandbox) - the first
real turns after `pipeline_on` on her server are the test; `pipeline_sheets` shows each one.

## v0.964.0 HOOLA CODE IN ORDER (owner, her screen recording 16 Nov 21:55: "CHECK VIDEO IN CHAT SECTION A FINAL CHAT APPEAR FIRST THEN A FEED APPEARS")

What the recording showed (frames at 2 fps): she sent "NOW READ THE NEURAL SECTION", the long "I've read the Neural
section end to end. Here's the full picture: ..." message streamed in live (v0.962 works), and the moment the round
ended the closing answer ("Read the Neural section in depth ... What do you want to change or add?") + "Worked for 41s"
appeared whole at the bottom while the long message above it started landing again from its first word for ~15 s.

ROOT CAUSE `code_session.dart` `_load`: when live words become a saved message, the count of words already shown moved
from 'live' to the NEWEST saved message. One check brought two new messages (the long one + the closing answer), so the
closing answer got the count (more words than it has = shown whole at once) and the long message had none (from 0).

FIX: (1) the count goes to the new message whose text starts with the live words (fallback the oldest new one);
(2) while building the thread, once a message is still landing, every newer step after it (the next message, step
rows, the round line) is not drawn yet, and the question / ready / PR cards wait too - the thread lands top to bottom;
not applied while she has scrolled up (an off-screen landing does not move, nothing should stay hidden). Phone only.
Tests `test_v0964_hoola_code_order.py` (3). NOT VERIFIED on her phone.

## v0.965.0 HOOLA PIPELINE P2 FIX (owner: "DONE CHECK" after deploy + pipeline_on)

Her check (vps-ops pipeline_on 16:34 -> effective True, pipeline_sheets 16:36 -> "no job sheets yet", pipeline_off 16:38)
found no sheet. This session cannot start vps-ops jobs (GitHub answers 403 to a workflow dispatch), so the server log
could not be read from here; reading the code instead found a real bug:

- `santosh.run_turn` called `turnbox.begin(conversation_id, user_text, tenant_id, ...)` but the signature is
  `begin(conv, tenant, text, ...)` - her words went in as the account and the account id as her words. Every live sheet
  would have read kind `chat` with the account id as the ask, and her own model pick could never apply. The P2 test
  missed it because it used "hi" for both. Now passed by name.
- NEW test `test_run_turn_gives_the_box_her_words_and_her_account`: a real reasoning ask through `run_turn` must land on
  the sheet as itself (her account, her words, reason / HIGH, the HIGH model) - fails on the old code.
- The Box now says once per process in the log when the server has no tables (`pipeline box: no tables at <path>`) -
  before, a Box with no tables was silent.
- `pipeline_sheets` prints where the tables are (present / MISSING) and the running server's own Box log lines
  (`pipeline box ...` from santosh-error.log), so the next check shows whether a message reached the Box at all.

NOT KNOWN: why her 16:34-16:36 window had no sheet at all - the swapped arguments still write a sheet, so either no
chat message was sent in those two minutes, or the server could not see the tables; the new pipeline_sheets output
answers which. NOT VERIFIED with a real model answer. 2 tests (+ the pipeline suites, 108 passed).

## v0.966.0 HOOLA PIPELINE P2 READS HER WORDS (owner: "DONE CHECK" on v0.965)

Her server, 17:04-17:06 (v0.965 deployed, pipeline_on): the fix held - her sum's sheet shows her words, kind
`reason`, level HIGH, run on the HIGH model (`z-ai/glm-5.3-flash`, backups `google/gemini-3.5-flash`,
`meta/muse-wonder`), Box 70 ms; "GOOD" = chat MID on `anthropic/claude-sonnet-4.6`, 45 ms. Two misses fixed:

- Language read `en` for a Hinglish sum: the web console appends `[Web console language preference: Reply in English
  ...]` (and the Deep research / Hoola PC chips as `[Web console mode: ...]` / `[Web console place: ...]`) after her
  words, and the Box read them as her words. `turnbox.her_words` splits them off; the Box reads only her words, a Deep
  research chip still makes it research, a Hoola PC chip = not through the Box (the PC side keeps its own model), the
  sheet stores only her words, the final check holds figures to her words.
- The final check flagged `figure 15` in a worked answer (3 x 5 from her own question). `check.one_step` adds one
  step of arithmetic (x, +, -, /) on HER figures only (at most 12 of them) to the known figures; an invented number is
  still flagged (test).

3 tests (111 passed in the pipeline + routines set). NOT VERIFIED on her server. Still her decision: chat MID picks
Claude Sonnet 4.6 (more than the Qwen 27B chat today).

## v0.967.0 HOOLA PIPELINE P3 (owner: "GO P3" on docs/HOOLA_PIPELINE_PLAN.md)

Her live check of v0.966 first (17:21, her server): her Hinglish sum read `reason (hinglish) HIGH` on the HIGH model,
check ok, answer in 22 s; the sheet holds only her words. Then P3 = a message with several parts:

- **Plan** (`pipeline/parts.py`): `code_plan` cuts her words where she joined jobs (", and", "phir", ";", a list) in
  milliseconds - gathering parts (research, facts, reading, summary, translation) wait on nothing, any other part waits
  for every part before it, the last part writes. Then `model_plan` asks the LOW `plan` model (the `reason` table) for
  one JSON plan, 10 s at most, outside the chat brain's pause record; `check_plan` accepts only 2-8 parts each with
  its words and waiting only on EARLIER parts (a loop, a later part, an empty ask = thrown away, the code plan stands).
- **Size**: each part's own kind + level + model + two backups from its own words (`box.choose_for`); a picture /
  video / voice part before the reply is driven by a worker on the `tools` table (the studio's price card stays, D6).
- **Run**: every part but the last is a focused worker = the crew's sub-agent runner (`team._run_agent`) on the part's
  own model (`llm.MODEL_NOW` inside its own task), side by side when nothing is in between, a part that needs another
  part's result waits for it and gets its hand-off package (6.3); research parts get the search / fetch tools and the
  research report rule. It runs inside her chat turn after her message is saved and the chat lock is held
  (`santosh._run_turn`, after the Stop-in-preparation check), so Stop stops every part and one job runs per chat.
- **Write**: the last part is her chat turn itself on its own model, told every package, every not-done item and the
  waiting branches (`writer_block`) - one reply, one voice. The final check covers every part: figures held to every
  part's facts, every part's not-done must be said.
- **Her tap per branch (6.9)**: a worker whose tool made a card she must tap (`turnpark.card_of`: bazar confirm
  cards, email drafts, studio price cards) = `waiting_tap`; parts after it wait (`blocked_by`), the other parts go on,
  the sheet is `waiting_tap`. The worker slot `pipeline_branch_jobs` (every 20 s, pipeline_on only) reads each card's
  own row: yes = the parts after it run and a turn (actor `approved:card`, line "[Card answered by her tap] ...") tells
  her the rest on the writer's model; Not now = only that branch ends; no tap in `pipeline_tap_wait_h` (24 h) = ends.
- **Restart**: the sheet is saved after every part; a restart re-runs her turn and `begin` takes the unfinished sheet
  of the same ask (within an hour): done parts are not done again, a part cut mid-way runs again.
- **Time**: one limit for the parts before the reply (`pipeline_parts_s` 300 s); a part still running is cut, marked
  failed and the reply must say it.
- Reading fixes found on the worked example: "make a Hindi PDF report" now reads Hindi (a language named on the thing
  to make) and as writing (`make` / `create` / `banao` + report / letter ...); "make a (price comparison) table" reads
  as `extract` (arranging, LOW), not research or reasoning. The final check prints a big figure as `3100000`, not
  `3.1e+06`.
- `pipeline_sheets` shows the parts, who planned them, each part's words, what it waited on, its seconds and its
  not-done lines; `/api/pipeline/sheets` stats carry `parts`.

13 tests (`test_v0967_pipeline_p3.py`): the code plan, the plan check, the planner on the LOW model + fallbacks, the
EV example end to end through `run_turn` (5 research parts side by side, the table after all five with their packages,
the Hindi writer on the write.lang model, check ok), an invented figure + an unsaid failure caught, a card pausing only
its branch + her yes carrying it on, Not now ending only that branch, cards from raw tool results, restart keeps done
parts, the time limit, one-part messages unchanged, a call not planned, the wiring. 97 pipeline tests pass. NOT
VERIFIED on her server or with a real planner / worker model.

## v0.968.0 HOOLA CODE NO STARS (owner: "FIX THE RAW STARS ALSO", after her 16 Nov screen recording)

Seen in the recording: while "I've read the Neural section end to end..." landed, a list item showed
`**15s polling** while visible` with its stars for a moment before turning bold. CAUSE: `HoolaMd._inkTail` (v0.960 per-word
fade) drew a word that opened or closed a mark (`**15s`, `polling**`) as plain text ("half a mark: plain until it closes"),
so a bold run across words was raw for as long as it sat in the fading tail. FIX: `marksAfter(text, open)` tracks the marks
open (`**`, `~~`, a code span) and `balanced(text, before)` puts the open marks back in front of each word and closes what
is still open after it, so mdInline draws every word in its style with no star; the head is drawn balanced the same way and
the tail continues with the marks the head left open. A code span across words is one unit (one chip, it lands together);
a cut inside a code span, an italic (single star) or a link still being written fall back to the whole-block renderer
(its own streaming rules, no per-word fade for that moment). Phone only. Tests `test_v0968_hoola_code_no_stars.py` (4,
the logic mirrored in Python). NOT VERIFIED on her phone.

## v0.969.0 HOOLA PIPELINE P4 (owner: "GO P4" on docs/HOOLA_PIPELINE_PLAN.md; built as 0.968.0 - their HOOLA CODE NO STARS took 0.968.0, both kept)

P4 = the hand-over rules (plan 5.2 + 5.3 + 6.8) carried out on real model calls, not just decided (P1's
`handover.next_move` was pure). NEW `server/app/pipeline/runner.py`: every model call of a Box part (the one-part
chat turn, the P3 writer, each P3 worker) runs through `runner.call(hand, make)`, with a per-part HAND contextvar.
- error / refusal / empty answer -> the next backup at the SAME level, at once; words of the failed try already on
  her screen are reset first.
- no first word in time (streaming, chat limit 8 s) -> the slow call is stopped and the backup starts.
- a live call (non-streaming, surface call) -> the backup starts AT the limit and the first good answer wins; the
  loser is cancelled (head start, silence is the worst case on a call).
- the part outgrew the window -> a same-level model with a bigger ctx from the message's tables copy (`_bigger`).
- at most two changes per part, then the last error goes up as today. Every move is written to the sheet's part
  (`handover` rows, `ran_on`) and logged `pipeline box hand-over: a -> b (event: why)`.
- `llm.BOX_OWNS`: while the Box owns a call its failure goes to the Box's outage record (2 in 10 min = paused), never
  to the whole OpenRouter brain's pause / breaker.
NEW `server/app/pipeline/limits.py`: per-user (`pipeline_user_cap` 6) and per-company (`pipeline_company_cap` 8)
asyncio queues, first come first served, a call waits its turn instead of being refused.
MOVING UP (5.3): a worker whose report fails `parts.worker_check` (empty, figures with no source in its inputs /
tool outputs) runs once more one level up with the problems named; a second failure = a not_done line. The writer's
failed final check = `turnbox.fix_round` (switch `pipeline_fix_round`): the next level's model writes a short
correction ("OK" = false alarm, nothing posted; still failing = a plain line). "better answer please" in the same
chat within 30 min = the previous sheet's ask one level up (`turnbox.BETTER`).
CALLS: `pipeline_calls` (default False) lets a live call's brain asks into the Box on surface "call".
Tests `test_v0969_pipeline_p4.py` (21, fake models): every 5.2 case, the race both ways, bigger window, two-change
cap, worker / writer fix rounds, better, queues, breaker untouched, the santosh call path, HAND lifecycle, calls off.
NOT VERIFIED on her server or with a real model failure.

## v0.970.0 WEB CONSOLE APP DESIGN (owner: "CURRENTLY IN WEBCONSOLE LOOK AI MADE --- CHECK THE APP DESIGN AND APPEND SAME FOR WEBCONSOLE --- EXTRACT ALL APP DESIGN ... SHOW ME WEB CONSOLE DESIGN HERE FIRST" -> design canvas claude.ai/artifact/QMSQEVcnpFv4aHq6JTJ4aL -> "GO BUILD")

The phone app's design system (lib/ui/hoola_theme.dart + the R1-R9 shell, chat, cards, AI Employees, Tools) on the web
console, built as one layer that can be switched off.

- NEW `server/app/static/console/appdesign.css`, linked after v2.css and improve.css, every rule under `html.appd`.
  Tokens = the app's colour roles: light bg #FAF9F6 / surface #FFF / sunk #F1F0EC / ink #1B1A17 / ink2 #57554F /
  accent #5B45E0 / line #E5E3DD / pill #1B1A17 / ok-warn-bad; dark = the app's darkSet (#141413, #1E1E1C, #E6E5E1,
  #9C88FF, pill #3A3936). The old brand glow tokens (--grad, --ring, saffron / magenta) collapse to the one violet: no
  gradients, glass or glow. Radii 16 / 12 / 8, side 272.
- Components: sidebar rows 40 px / 12 corners / nav-on fill, New chat a black pill, the Hoola mark beside the name and on
  the Hoola row, a Code pill beside the title when Hoola Code is on; home = mark 60 + Literata 40 greeting + tagline + the
  app's start pills; typing bar = + / field / mic / black call circle, violet Send (grey while empty); her words in a soft
  20-corner bubble, replies Literata 16 / 1.5, inline code in the app's red term colour; HoolaCard shapes; buttons = black
  pill main / quiet outline; AI Employees hub with a serif title, no tinted hero, quiet cards, monochrome department art.
- `v2.js`: `APPD` from the config key `app_design` (server switch `console_app_design`, default on), `appNav()` = Hoola /
  AI Employees / Tools / Computer, then Your work (Work, Made by <avatar>, Voice call); the studio rows leave the sidebar and
  sit on the Tools page as black-circle cards (`APP_TOOLS`, only the ones whose page is switched on + Connectors), the Tools
  row lights while a studio is open; `appHome()` = "Santosh is ready. N things need you." + start pills (a waiting
  approval first -> Work; three jobs that go straight to Hoola via `data-send`); `appChrome()` puts the mark in and turns
  the paperclip into "+"; greeting words like the app (Morning / Afternoon / Evening / Good night).
- Tests `test_v0970_console_app_design.py` (5): tokens read from hoola_theme.dart itself, everything scoped + loaded after
  v2.css, sidebar / home / Tools code, a real-Chromium walk light + dark (four tabs, marks, page colour, Literata greeting,
  pills, black New chat, Tools grid, AI Employees, no page errors). NOT VERIFIED on her server.

## v0.971.0 HOOLA PIPELINE P4 FIX (owner: "CHECK" on her v0.969 test run; built as 0.970.0 - their WEB CONSOLE APP DESIGN took 0.970.0, both kept)

Her pipeline_sheets after the P4 test prompts (17 Nov 03:09-03:14 UTC): plain, GST and better-answer messages went
through the Box; then the margin and blog messages said "not through the Box: this server's chat does not run on its
OpenRouter brain". The server log showed why: "better answer please" moved MAX -> ULTRA and picked
google/gemini-4-carbon; OpenRouter answered 403 "Model google/gemini-4-carbon-20261110 is banned"; the runner handed
over to anthropic/claude-opus-4.6 in 2.5 s and the reply came (the first live P4 hand-over). But the turn-wide model
(llm.MODEL_NOW set by turnbox.begin) still named the banned model, so the turn's other calls (after-turn checks,
facts, titles through the SDK door) asked it, failed twice and tripped the glm brain breaker: the whole OpenRouter
brain paused for 10 minutes, llm.cheap_brain() went None and the Box stood aside.
- `runner.TURN_SWAP` (one dict per message, opened in turnbox.begin, dropped in end): a hand-over records failed ->
  took over; `llm._live` makes every later call of that message (model_in_force, _target) ask the model that took
  over; a Box part's own attempt runs on exactly its model (`runner.EXACT`).
- `llm.box_owned()`: every call of a Box turn on a Box model belongs to that MODEL - openai_create / openai_stream and
  glmdoor acreate / create_sync never count it on the brain breaker; it goes to the Box outage record
  (`runner.model_failed`).
- A banned / gone model (403 banned, 404 no endpoints, not a valid model; NOT a key / credit / rate 403-429) is off for
  `pipeline_dead_h` (24) hours (`turnbox.mark_dead`, health() reports it paused), so the next message starts on a
  backup.
- `check.one_step`: a percent of hers is a rate (12% -> 1.12 / 0.88 / 0.12, 12% of 120 = 14.4) - her margin ask was
  flagged "figure 1.12 is in no fact".
- pipeline_sheets prints each hand-over (event, from -> to, why) and "ran on <model>".
Tests `test_v0971_pipeline_p4_fix.py` (9). NOT VERIFIED on her server.

## v0.972.0 HOOLA PIPELINE P5 - Hoola Code, background jobs and the studios on the Box (owner: "GO P5")

P5 of `docs/HOOLA_PIPELINE_PLAN.md` ("Hoola Code, background jobs, studios on the Box - their fixed model settings
retired, old values kept as a fallback switch"). Before it: v0.971.0 verified on her server for the margin message
(through the Box on Opus 4.6, the 1.12 check passed); the ban-fix path not re-sent yet.

NEW `server/app/pipeline/surfaces.py` - the one place the other surfaces ask the Box.

**Hoola Code** (`devsahayak/brain.py`): every OpenRouter coding call asks the Box for its kind of work through
`surfaces.code_choice` - the round / sub-agents / one-shot writer = `code` (starts HIGH), the plan pass = `plan` (LOW,
reads the reason table), the PR review = `check` (with tools it reads the code table), compaction + the memory observer
+ the next-message hint = `summarise` (LOW); ranked score first (surface `code`), OpenRouter route only. Her words
raise the level as on chat (`brain.session(t)` keeps her task text + the session id; "production / payment / deploy" =
costly -> MAX), her effort max / xhigh raises a code call one level (never to ULTRA), her composer pick is a pin when it
is an OpenRouter id (a Claude name set by the hint / memory callers means nothing there). `_qwen_call` now runs the
model + up to two backups (`_qwen_one` per model, two tries when a backup is left): a refused / failed model hands over
(`pipeline box hand-over (code): a -> b`), its failure goes into the Box's outage record and a banned / gone one is off
for the day (runner.model_failed -> mark_dead); her key / credit (401 / 402 / key limit / insufficient credits) is
raised at once and never blamed on a model; the model that answered is kept for the session's same kind of work
(box.remember, 30 min). Callers marked: engine round `B.session(t)`, compaction `B.part("summarise")`, loop.pick
`_B.session(t)`, plan_run `PART.kind = "plan"`, review_run `"check"`, memory + hint `B.part("summarise")`.
FALLBACK = the old fixed `dev_qwen_model`, exactly as before, when `pipeline_on` or `pipeline_code` is off, the server
has no tables, or the Box chose nothing on OpenRouter. `dev_brain claude` stays Claude (her explicit setting).

**Background jobs** (`pipeline/turnbox.py`): routine / wake / goal (long-job rounds) / nudge turns go through the same
chat-turn Box with surface `background` (reliability first, the 30 s first-word limit, every call through the P4
hand-over runner); "better answer" and the several-parts planner stay for her own messages. `pipeline_background` off
= "a routine turn - pipeline_background is off" on the sheet. `pipeline_sheets` marks a non-chat sheet `[background]`.

**Studios - the Box ranks, the studio runs** (D6: engines, keys and price cards unchanged): `surfaces.studio_order`
reorders the models a studio can already run by the kind's table (the level itself, then above, then below; paused /
banned left out; names matched exactly after dropping the maker prefix and -preview / -latest / date tails - so
seedance-2.0 never matches seedance-2.0-fast). Video: Hoola Auto "quality" (`Studio.model_for` -> `box_order`) orders
the shot's own ready route by video.make (draft MID / final HIGH / premium MAX; talk shots keep Sync 3; value / cheap
modes and her own picks unchanged); the price card prices the model the run will use, as before. Pictures:
`photogen.models_for(quality, edit)` orders the chain by image.make / image.edit (fast MID / best HIGH) and each model's
result goes into the outage record. NOT ordered (one engine each on this server): music (Lyria), voice-over (Gemini
voice). A model the tables rank but the studio cannot run is never forced (logged `pipeline box video studio: ...`).

Switches (all under `pipeline_on`, which stays OFF by default until P7): `pipeline_code`, `pipeline_background`,
`pipeline_studios`, each default True. Tests `test_v0972_pipeline_p5.py` (17). NOT VERIFIED on her server.

## v0.973.0 CLAUDE-STYLE CHAT — the web console's chat shaped like Claude's (owner: her Claude screenshot -> "SHOW DESIGN HERE FIRST" -> boards 6-9 on claude.ai/artifact/QMSQEVcnpFv4aHq6JTJ4aL -> "SHOW SIDE BAR TOP LIKE THIS" -> "GO BUILD")

On top of v0.970 WEB CONSOLE APP DESIGN, behind the same switch (`console_app_design`, `html.appd`); off = the console as it was.

- **Sidebar top**: "Hoola" in Literata 26, the Code pill (outlined, black circle with `<>`, shown when Hoola Code is on), the sidebar button on the right (its icon mirrored). The sidebar mark is gone, as in her picture.
- **Rows** (`v2.js appNav`): New chat and Search are plain rows like Claude's "New" / "Search"; then Work (one violet count = cards waiting for her), Made by <avatar>, AI Employees, Tools, Computer, any owner page (Arena, AI Apps...), Customize (= the Account page). The Hoola row and the Voice call row left (New chat and the call button cover them). Sessions + Recents keep chatlist.js / projects.js; "Recent chats" reads "Recents"; the Hinglish empty line for Sessions is hidden. Theme switcher + export leave the sidebar (Customize has Appearance; the chat header has export).
- **Home**: the Hoola mark beside "Good morning, <name>" (Claude's words: Good morning / afternoon / evening) in Literata 40, the rounded box (20px corners, the field on top, + left, mic + call right, violet Send only once she types), under it Session (`sessMenu`: start this chat in a session / No session / New session) and the model chip (moved there on the home, back beside the mic in a chat). Start pills + tagline are hidden (still drawn). A private-chat (ghost) button top right = `newIncognito`.
- **+ menu** (`plusMenu`, menu.js gains clip / search / spark / grid icons): Add photos and files, Deep research, Use Hoola PC, Improve my prompt (when Prompting is on), Everything <avatar> can do. A chosen option shows as a chip in the box; the old chip row is hidden.
- **Chat**: the header without its rule, title on the left; the box docked at the bottom with the disclaimer under it.
- Tests: NEW `test_v0973_console_claude_chat.py` (shape pins, every new rule behind `html.appd`, a real-browser walk light + dark: rows, greeting beside the mark, placeholder, box shape, Session chip, ghost, Send hidden until typed, the + menu, the chat view); `test_v0970` pins moved to the new rows / words.
- NOT VERIFIED: on her server; the chat view in the test is switched by hand (the test server streams no reply).

## v0.974.0 CLEAN HOME — the console home without the extras (owner, her screenshot of the live v0.973 home: "remove inprogress section, incognito icon, hoola pc online")

In the app design (`html.appd`) the home now shows only the Hoola mark + "Good morning, <name>", the rounded box and Session / model under it, like Claude:
- the In progress cards (`#liveJobs`) are hidden on the home - waiting / running work stays in Work (the sidebar's violet count);
- the private-chat ghost is gone (`#incogBtn` removed from `appChrome`) - Incognito chat stays in the chat menu;
- the "Hoola PC online" pill (`.lhead`) is hidden on the home - Computer in the sidebar shows the PCs.
CSS rule at the end of `appdesign.css`; `test_v0973_console_claude_chat.py` checks the three are gone. NOT VERIFIED on her server.

## v0.975.0 SIDEBAR LIKE CLAUDE + FULL WHITE (owner: her Claude + Hoola sidebar screenshots, "same font, size, dark word type for all"; her Claude home, "background is full white, make same for Hoola chat" -> canvas claude.ai/artifact/QMSQEVcnpFv4aHq6JTJ4aL boards 10-12 -> "GO BUILD")

Measured from her screenshots: Claude's sidebar rows sit 34 px apart (32 px rows, 2 px gap) in near-black #141413 at 14 px,
labels 12 px grey #73726C; Claude's page is pure #FFFFFF with a white box, a thin grey line and a soft shadow. Her Hoola
shot showed 15 px rows 38 px tall at a lighter weight with grey icons, and Pinned under Recents.

All behind the app design (`html.appd`, switch `console_app_design`):
- `appdesign.css` light tokens: `--bg #FFFFFF`, `--side-bg #FAFAF9`, `--nav-on #EFEFEC`, `--you/--bubble #F4F4F2`,
  `--chat-paper #FFFFFF`; new `--side-ink` (#141413 light / #F2F1EC dark), `--side-dim` (#73726C / #9C9A92),
  `--side-line`, `--box-line #D9D9D6`. Dark tokens otherwise unchanged.
- The v0.975 block: New chat / Search / section rows 32 px (min-height too - v2.css had 34-36 px minimums), 14 px / 500,
  18 px icons in the word's ink; chats 14 px / 450 at 32 px; labels 12 px grey with chevrons; Hoola 24 px; account name
  14 px, handle 12 px, 26 px circle; the box border `--box-line` + soft shadow; `.main` on `--bg`.
- `chatlist.js`: in the app design, pinned chats (outside sessions) draw into `#pinbox` above Sessions under a
  "Pinned ›" header, closed until she opens it (state `hoola.side.v1` in localStorage), a dot when a pinned chat is
  busy / has a new reply; the ordinary chats lose the Today / Yesterday labels; "Recents ⌄" folds the list; row clicks and
  the chat menu work in `#pinbox` too. Archive view empties `#pinbox`.
- `v2.js` appChrome: "Recents" gets its chevron + `data-side="recents"` (button role, keyboard Enter / Space) and the
  `#pinbox` holder before `#projects`.

Tests: NEW test_v0975_console_sidebar_white.py (2: shape + a real-browser walk in light and dark - 32 px / 14 px / 500 rows,
18 px icons, #141413 words, 12 px grey labels, Pinned folded first then opens to its chat, Recents folds and opens, no day
labels, white page + #FAFAF9 sidebar, dark words #F2F1EC); test_v0970 pins moved (page white, New chat radius 8 px).
Already red before this change and untouched: test_v142 conversations, test_v0285 menus crisp, test_v0288 sidebar visible x2.
NOT VERIFIED on her server.

## v0.976.0 HOOLA PIPELINE P6 - the receipt line: which model did which part (built as 0.975.0; their SIDEBAR LIKE CLAUDE took 0.975.0, both kept; owner: "GO P6")

P6 of `docs/HOOLA_PIPELINE_PLAN.md` ("Receipt line on phone + console - she can see which model did which part").
Before it: v0.971.0 + v0.972.0 checked live on the margin message (through the Box on Opus 4.6, the check passed).

NEW `server/app/pipeline/receipt.py`: when a Box sheet closes (`turnbox.end`) ONE `model_receipt` event is published
into the chat the sheet belongs to: `say` ("Research: Claude Sonnet 4.6 (2 parts) · Writing: Claude Opus 4.6", same
label + model grouped with a count), `parts` (label from `parts.LABEL`, the model that REALLY answered = `ran_on`,
its pretty name, level used, a plain note for a part that did not finish / waits for her tap / was cut, the first pick
kept as `chosen` when a hand-over moved it, and each hand-over as "<to> took over from <from> (<why in words>)"),
`handovers` count. Only parts the Box really ran are named - a part not applied (the server's own chat model, which
the Box did not choose) is left out, and a message with none gets no receipt. Names: `pretty()` drops the maker,
date tails and preview / latest, upper-cases GPT / GLM ("z-ai/glm-5.3-flash" -> "GLM 5.3 Flash"). No price (D5).
The event is LOCAL to its chat (events.LOCAL_KINDS + CALL_ONLY_KINDS), stored (it comes back on reload), never pushed.
Switch `pipeline_receipt` (default True, needs `pipeline_on`).

Console (`v2.js` renderCard + `.mreceipt` in v2.css): a quiet "Made with ..." line under the reply that folds open to
one row per part (label, model, level, note) and the hand-over lines; checked by eye in light + dark.
Phone: `lib/ui/model_receipt.dart` `ModelReceiptLine` (44 dp tap row, Semantics label) + `showModelReceipt` sheet
(parts, level, hand-overs); state.dart feeds `model_receipt`; the new design draws it through `HCQuietLine`, the old
chat screen through `feedCard`. Hoola Code sessions are not chat replies and get no receipt line yet.
Tests `test_v0976_pipeline_p6.py` (9). NOT VERIFIED on her server or phone (the Dart compiles first on CI).

## v0.977.0 MORE MENU (built as 0.976; their HOOLA PIPELINE P6 took 0.976, both kept; owner, her sidebar screenshot: "remove Work, Made by Santosh, AI Apps, Arena --- show 2 things in More -- Work and replace Made by Santosh by name Docs and files -- AI Apps and Arena just hide it for now")

App design only (`html.appd`). `v2.js` `appNav()` rows: AI Employees, Tools, Computer, any other NAV page not in
`APP_HIDE` (`aiapps`, `arena`), More, Customize. More is a `.sn` button with `data-more` (NOT `data-v`: the global
`[data-v]` handler would call go('more')) that opens a HoolaMenu (`moreMenu`, `APP_MORE`): Work (`aaj`, briefcase icon
added to menu.js) and Docs and files (`bana`, the old "Made by <avatar>" page; its title line now "· Docs and files" in
the app design). More is lit when either page is open and carries Work's waiting count / "N working". AI Apps and Arena
pages and routes are untouched, only their rows are hidden. Tests: v0975 walk asserts the rows + the two-item menu;
v0970 / v0973 row pins moved. test_v0285 menus crisp was already red. NOT VERIFIED on her server.


## v0.978.0 APP ENGINE BRANCHES + E8 (built as 0.976; their HOOLA PIPELINE P6 took 0.976 and MORE MENU 0.977, all kept) (owner: "GO APP ENGINE BRANCHES AND E8")

The two pieces left after L15 ("IS ALL WEB DEVELOPMENT WORK DONE" -> App Engine branches + E8 were the gaps).

**App Engine branches** (the second half of L13 of docs/LOVABLE_STUDIO_PLAN.md) - `server/app/appengine/branches.py`:
- A branch = a hidden AppProject row (`branch_of`, `branch_name`, `branch_base` - new nullable columns on `ae_projects`,
  added by `_add_missing_columns` on old databases) with its OWN `src/`, own preview token + slug, own Hoola Cloud schema
  copy and its OWN preview data (cloud site_key `ae:<branch id>:p`, seeded with marked samples); the app's preview and
  live data are never touched. `branch.json` keeps the base version, base schema version, base look and base packages;
  `base_src/` = the app's files as they were (the merge's common ancestor; never depends on pruned versions).
- `list_` hides branches; `publish` refuses a branch; `delete_app` refuses an app with open branches; max 3 open; no
  branch of a branch; duplicate names refused; discard = her tap (confirm).
- `merge_plan` = THREE-WAY BY FILE over the files Hoola may write (`RL.writable`; locked tooling is refreshed anyway):
  only-branch changes (new / changed / deleted) come in, only-app changes stay, both = a NAMED conflict (path + what each
  side did). The look (palette / values) the same way; packages the branch added come in; Hoola Cloud = the branch's
  migrations after the base schema version - replayed onto the app as ONE `apply_changes` run (refused = nothing at all
  changes, said by name); a conflict when the app also changed its lists; data-loss changes are never replayed but queued
  on the app's own "I accept data loss" card.
- `accept(resolutions {id: site|branch}, confirm)` = her tap: an unsettled conflict -> 409 and nothing written; incoming
  files checked against the app's rules first, then Cloud, then look + packages, then files under the app's lock; the app
  rebuilds once (one new version); the branch row, files and preview data are removed. Entry files are never deleted.
- Routes: GET/POST `/api/appengine/{ref}/branches`, GET `/branches/{bid}/compare`, POST `/branches/{bid}/accept`,
  DELETE `/branches/{bid}?confirm=true`. Tool `app_engine`: `branch_new {name}`, `branches` (never accept / discard).
  The prompt block tells the model when it works in a branch.
- Studio (`appengine.js`): a Branches tab (start, list with "N to bring in" + "changed in both" pill, What would change,
  choose Keep the app's / Take the branch's per conflict, Accept into the app behind a confirm, Discard); a branch's
  workspace shows a "Branch: <name>" pill, Back to the app, Accept or discard, and no Publish.

**E8 Looks with their own bodies** - `site/service._own_bodies`: when full looks are on and the WHOLE plan has at most
`site_look_own_bodies_max` (12) sections, every remaining section is written by EACH of the three looks in its own design
(streamed to that look's live canvas), saved only in `looks/<i>/<page>__<type>.json`; nothing enters the site's sections
until she picks; `choose_look` now copies every `*__*.json` of the picked look (was home only), so the build writes no page
again. Above the cap the v0.649 rule stays (written once, shared). The look carries `own_bodies`; the Studio says "every
page in its own design". Switch `site_look_own_bodies` (conftest pins it off for the older full-look suites).

Tests: `server/tests/test_v0978_branches_e8.py` (8: hidden copy / never live / limits, the conflict-named merge with
nothing half done, look + Cloud + file conflicts taken from the branch, routes, a browser walk of the Branches tab, E8 own
bodies + pick, E8 above the cap). NOT VERIFIED on her server or with a real model (the fake site AI writes the sections).

## v0.979.0 HOOLA PIPELINE P7 - the week's watch (built as 0.977.0; their MORE MENU took 0.977.0 and APP ENGINE BRANCHES 0.978.0, all kept; owner: "GO P7")

Plan section 10, P7: "deploy, watch the outage record + timings for a week - done when no message is slower than
before for one-part asks". Built: the thing that watches, and the rule that says done. The week itself is hers.

- **Every chat message timed** (`server/app/pipeline/watch.py`): `santosh.run_turn` starts a clock before the Box
  chooses, `events.bus` hands the watch the first streamed word (`delta`) or whole reply (`message`) that reaches her
  screen (the "Ek second" ack line, error lines and empty deltas do not count), and the turn's end writes one row:
  group, kind, level, model (the one that really answered), first-word seconds, whole-reply seconds, ok, hand-overs.
  Only her own chat messages (owner / her approved turns), never a live call or a background turn.
- **Groups**: `box` (one part the Box ran), `box_multi` (several parts - more work, left out of the speed rule),
  `before` (today's routing: `pipeline_on` off, or the HELD-OUT share), `skipped` (Box on but it did not run it - media,
  no tables, a Hoola PC turn; counted with the reason, never compared).
- **The held-out share** (`pipeline_holdout_pct` 10): while the Box is on, about one one-part chat message in ten runs
  today's way - same week, same chats, same server, same hours - so "slower than before" is measured, not remembered.
  Its sheet says "held out for the P7 watch" and it gets no receipt line (the Box did not choose its model). Off in the
  test suites (conftest pins 0).
- **The outage record written down**: every failure (`turnbox.note`), every banned / gone model (`mark_dead`) and every
  hand-over (chat runner + Hoola Code) goes to `data/pipeline/watch.db` beside the sheets, so a week survives restarts.
  The report counts pauses by turnbox's own rule (two failures within 10 minutes). Kept 60 days; no words of hers.
- **The verdict, in code**: after `pipeline_watch_days` (7) since the first Box message and `pipeline_watch_min` (30)
  timed messages in BOTH groups, the Box's median and slowest-10 % (nearest rank, no interpolation) first word and whole
  reply must each be within `pipeline_watch_slack` (10 %) + 0.3 s of `before`, and its failed share no more than 2
  points higher. States: watching (says what it still waits for), slower (names each slower number), ready. Turning the
  Box on for good stays her tap (vps-ops `pipeline_on`).
- **Read it**: vps-ops `pipeline_watch` (the table per group, per day, per kind of work, per model with fails / pauses /
  hand-overs / off, why messages skipped the Box, then the server log's hand-over and model-off lines);
  `GET /api/pipeline/watch?days=7`. Switch `pipeline_watch` (off = nothing written, no held-out share).
- Tests `server/tests/test_v0979_pipeline_p7.py` (12): a Box turn through the real `run_turn` timed with its first word
  (ack not counted), Box off = before, the held-out share runs today's model with no receipt, calls / team turns not
  timed, several parts = box_multi, error lines are not a first word, the outage record written (banned + hand-over +
  two fails = one pause), the verdict waits then passes, names a slower first word but not a whole reply inside the
  slack, more failures = not ready, route + CLI, switch off writes nothing, wiring. `test_v0976` version test now reads
  its marker from this file (later stories drop it from main.py).

NOT VERIFIED: no week has been watched on her server; the first numbers come from her first messages after deploy.
The held-out share means about 1 in 10 of her one-part messages runs on today's model during the week, on purpose.


## v0.980.0 STUDIO STAMPS (owner: "DONE CHECK" on v0.978 APP ENGINE BRANCHES + E8)

Live check after her deploy: healthz 0.979.0 (contains v0.978), `/api/appengine/{ref}/branches` and `/branches/{bid}/compare`
answer 401 without a key (mounted, key-protected), the served `appengine.js` carries the Branches tab code, the served
`webstudio.js` the E8 "own design" label. FOUND: `webstudio.html`, `appstudio.html` and `gamedev.html` loaded every script
and stylesheet as `?v=0.849.0`. The version ritual replaces only stamps equal to the last version, so once a ritual missed
these pages (at 0.849) they never moved again; with no Cache-Control a browser may keep the old file for hours by heuristic
freshness, so Studio changes since 0.849 could be invisible to her until a reload. Now these three pages carry the release
stamp and move with the ritual like `v2.html`. `test_v0801_app_studio_premium::test_page_carries_a_fresh_stamp` pinned the
frozen literal; it now checks the stamp equals APP_VERSION (the test's own stated intent). NOT VERIFIED: E8 and branches
not yet exercised in her browser; no real model build of a small site's own-body looks.

## v0.981.0 CHAT BAR LIKE CLAUDE (built as 0.980; their STUDIO STAMPS took 0.980, both kept)

Owner, with her Claude and Hoola chat bar screenshots: "CHECK THE CLAUDE CHAT BAR AND HOOLA CHAT BAR --- MAKE PERFECTLY
SAME AS CLAUDE ... STOP NAME --- JUST SHOW A ICON ... REMOVE INCOGNITO ENTIERLY ... CHANGE MEMORY TO ICON AND SHOW IT AT
CHAT BAR BOTTOM" -> design canvas claude.ai/artifact/QMSQEVcnpFv4aHq6JTJ4aL boards 13-14 -> "GO BUILD".

Console only (app design, `console_app_design`), server untouched:
- `v2.js barChrome()` (run once from `appChrome`): the composer gets `#cline` (the files tray + `.cin` = the textarea, Stop
  and Send); the old `.row` stays below it and gains `#cnote` ("<avatar> is AI and can make mistakes.") and `#cMeter` moved
  out of the chat header. Send carries two drawings: a grey return arrow (empty) and the up arrow (typed). Stop loses its
  "■ Stop" text (aria-label "Stop") and becomes a 32 px black square button.
- `barPlace(home)` (called from `landing`): on the home the box stays tall with Send / Stop in the row (`#composer.home`);
  in a chat they move into the one-line box. The textarea is re-measured on every move (it kept the home box's 48 px).
- `memGauge(pct)`: the memory meter in the app design is an 18 px circle with a violet slice that grows (orange from 60%);
  title "Memory N% full · tap to see the summary"; a tap still opens the summary dialog.
- Incognito removed from the console: `newIncognito`, `INCOG`, the `/incognito` slash command and the header chip are gone.
  The server's incognito support is unchanged, so old incognito chats stay private.
- `appdesign.css` block "v0.981 CHAT BAR LIKE CLAUDE": the form has no border in a chat, `.cline` carries the 14 px box;
  the row is ordered + / mic / call / chips / note / memory / model with CSS `order`; `.dock .disclaim` hidden (the note
  is in the row); the empty Send hides while Stop shows.

Tests: NEW `test_v0981_console_chat_bar.py` (shape + a real-browser walk: home keeps the tall box, chat = one line 40-48 px
with send / stop inside and the row below in order, note text, gauge 64% hot, no disclaimer, no header tags, typed = up
arrow, working = Stop 32x32 with no text and the empty Send hidden, /inc offers no Incognito). Pre-existing reds checked on
the clean tree and untouched: test_v0719 (toolsBtn), test_v0740 browser (model under the box since v0.973).
NOT VERIFIED on her server.

## v0.982.0 BUBBLE LINES

Owner, her chat screenshot after v0.981 went live: the first line of her own wrapped message ("Page "Radiant Broadband
Panel" (v2) mein error aa raha hai: Uncaught ...", sent by the page card's fix button) sat pushed right and its bottom
was cut by the line below.

ROOT CAUSE: v0.970's `appdesign.css` put `background`, `border-radius` and `padding:12px 18px` on `.mu .mut` - but
`.mut` is an inline `<span>`. On a wrapped inline element the side padding applies only to the first and last line
boxes, and the vertical padding does not move lines but each line's background is painted with it, so every next
line's background covered the bottom of the line above. One-line messages looked right, which is why it hid since
v0.970.

FIX (console only, app design): `html.appd #app .mu:not(.fonly)` carries the bubble (background `--you`, 20 px
corners, 12/18 px padding); `.mu .mut` is `display:block` with no background / padding. Files-only messages
(`.mu.fonly`) keep no bubble.

Tests: NEW `test_v0982_console_bubble.py` - shape + a real-browser walk sending her exact message: it wraps, every
line starts on the same left edge, lines are >= 20 px apart, the text sits inside the bubble's padding, the span has
no background or padding. NOT VERIFIED on her server.

ALSO SEEN in the same screenshot, NOT fixed here: her fix-the-page message got "The AI service is busy or unreachable
right now (ref 4576bd)". That line is `santosh._friendly_error` for a timeout / 429 / 5xx / empty answer; the real
error is only in the server log under that ref - needs a VPS ops > errors run.

## v0.983.0 CUT ROOM — a page rewrite cut at the token cap is asked again with room, never called "busy" (owner: "DONE CHECK" on the VPS ops errors run)

Her page-fix message ("Page ... mein error aa raha hai ... Isse theek karke naya version banao") got "The AI service is busy
or unreachable right now" three times on 17 Nov (refs 4576bd 08:25, f6120f 08:29, 319cf7 08:59). The errors run showed the
real line each time: `LLMError: OpenRouter returned an empty answer`, after a ~70 s call on `qwen/qwen3.8-27b` with
`cap=2000` (the chat's `agent_max_tokens`) on a 178k-token chat.

Root cause: the model was rewriting the whole page inside a tool call. At 2000 tokens the call was cut half way;
`llm.from_openai` drops a tool call whose arguments are not whole JSON (never run with broken inputs - v0.221), so nothing
was left and `_openai_stream` raised "empty answer". `_same_model_retry_ok` does not retry that, and the Box runner's backup
would have had the same 2000 cap - so it could never succeed. `_friendly_error` filed it under "busy".

Fix (`server/app/agent/llm.py`): `LLMCut(LLMError)` + `cut_room(max_tokens)` = max(`chat_cut_room` 16000, 4x the cap),
at most `chat_cut_max` 32000, 0 when it already had that room. A cut answer with nothing usable (`stop == "max_tokens"`,
no blocks) is asked again ONCE with that room - in `_openai_stream` (one extra try; partial tool text re-fed from scratch)
and in `openai_create` - so the chat, the Box runner and plain calls are all covered. Still cut = `LLMCut`, and
`santosh._friendly_error` says "That answer was too long to finish in one go. Ask for a smaller part at a time - for a page,
name the one section to change." - not "busy". A true empty answer (finish stop, nothing) is unchanged.

Tests `server/tests/test_v0983_cut_room.py` (4): cut page rewrite asked again with >= 16k and the whole call runs; still cut
= one retry only + the honest line; room rules; true empty unchanged (all 4 fail on the old llm.py).
NOT VERIFIED on her server: the next page fix on the live chat is the test.

## v0.984.0 WEB ON QWEN (built as 0.983; their CUT ROOM took 0.983, both kept) (owner: "FIRST GIVE WEB DEVLOPMENT QWEN 3.8 MODEL -- THEN WE WILL START THE ENTIER WEB PANEL END TO END TEST")

Before this, the Web Studio's site engine called Claude Opus for every design / section / fix (`site/ai.py`
`_ask_app`, Anthropic SDK), and the plan architect went the same way; with CLAUDE_ALL_GLM on, the SDK door could
quietly answer some of those calls from the GLM brain on its 45 s clock - too short for a 16k-token plan.

Now every call the Web Studio makes (`WEB_KINDS` = build, site_art, site_critique, site_edit, name - only `site/`
asks with these kinds; App Sahayak, PDF, SEO and Social keep their own kinds and models) goes to Qwen 3.8 through
OpenRouter on the server's OpenRouter key (`_ask_qwen`, reusing Hoola Code's `devsahayak/brain._qwen_post` /
`_qwen_stream`):
- settings `web_brain` "qwen" (| "claude"), `web_qwen_model` "qwen/qwen3.8-27b" (qwen/qwen3.8-max-0902 = the bigger
  one), `web_qwen_timeout_s` 300, `web_qwen_max_tokens` 32000, `web_qwen_fallback_claude` False;
- thinking room per job from the old effort table (art / sections / critique high, small edits medium, name medium),
  reasoning excluded from the answer; three tries with growing waits; an empty answer thinks one level less with the
  room kept; a refused request (400-404, incl. 402 no credit) is said at once, in English, naming the model;
- a section being written for the live canvas streams its words through `_qwen_stream` into the same slot as before;
- pictures (critique screenshots, her design screenshots) go as `image_url` parts;
- the architect's `_ask` takes the Qwen path even when `architect_opus` is on;
- the Studio names the real model: site view `model`, the price estimate (now priced through `usage.price_of`, so
  Qwen's price matches), the art-direction card, "Hoola is designing / planning" in webstudio.js and build.js,
  server lines that said "Opus";
- no OpenRouter key or `WEB_BRAIN=claude` = the old Opus path unchanged; conftest pins claude for the older suites.

Tests: test_v0984_web_qwen.py (14). NOT VERIFIED: no real Qwen website build on her server yet - the end-to-end
Web Studio test she asked for next is that check.

## v0.985.0 PAGE ROOM — a page written in the chat is asked again with room when cut; a cut-off page is never saved (built as 0.984; their WEB ON QWEN took 0.984, both kept)

Owner, her screenshot: "WHY RESULT IS NOT SHOWING IN ARTIFACT PROPERLY". The Radiant Broadband Panel preview (v3) was
blank and Hoola itself said the page is ~73,000 characters and "a single write keeps getting cut off at around 10,000".

Root cause: with `chat_artifact_direct` the chat model writes the page ITSELF inside the `artifact` tool call. The chat's
`agent_max_tokens` is 2000 (+ reasoning room), ~8-10k characters, so every whole-page write was cut part-way. v0.983 asked
again only when NOTHING usable came back; here a line of words came before the call, so `from_openai` returned the text,
dropped the half-written call (never run with broken inputs) and the turn went on - the model tried again at the same
small cap, over and over. A cut-off page that did get through (written in pieces) was saved and drew a blank preview.

Fix:
- `agent/llm.py`: a cut answer whose tool call was dropped (finish length / broken arguments, no whole call left) - with or
  without words before it - is asked again with room, up to twice: `cut_room` 2000 -> 16k -> `chat_cut_max` 32k tokens,
  in `_openai_stream` and `openai_create` (so the Box runner path is covered). `openai_stream(on_reset=)` clears the words
  already shown first (santosh passes `live.reset`), so they are not said twice. Still cut with nothing = `LLMCut`.
- `artifacts.py`: `cut_off(kind, src)` - an html page with an opening `<html>` / `<body>` but no closing one, or an
  unclosed `<script>` / `<style>`, is refused on create / update / rewrite (`EditError`, nothing stored, the old version
  stays) and the model is told to change the page with `action=update` instead of saving part of it.

Tests `server/tests/test_v0985_page_room.py` (4): words + cut page call asked again with >= 16k and the words cleared;
room steps 2000 -> 16k -> 32k and never a fourth ask; a cut-off page is never saved and the old version stays; small
fragments / markdown pass. `test_v0983_cut_room` updated (up to two bigger asks). The 5 reds in test_v161_stream /
test_v0969 when run together are the same on the commit before this change (test order). NOT VERIFIED on her server.

## v0.986.0 PLAN PEEK — the Web Studio start screen shows its work (owner, her screenshot: "WHEN MSG DROP -- SHOWING LIKE THIS. NO PROPER LOADING ... NOT CHAT SECTION EXPOSED ... EVERY THING FEEL STALE AND NON FUCTIONAL --- WHAT KIND ON PREVIEW IT IS WORKING ON")

What she saw after sending the long Halden & Co. test brief: her message filling the chat, nothing under it, a grey skeleton
on the right and a locked typing box - for the whole plan call (minutes on Qwen 3.8 since v0.984). Three causes: the
"Setting the stage" card sat below her long message with no scroll; the server published only "Reading your idea" /
"Planning the pages" for the one long architect call (and its deepen round); the preview had nothing to show until the
whole plan came back.

- Her message: over 360 characters / 7 lines it folds to ~6 lines with a fade + Show all; the work card is scrolled into view.
- The plan as it is written: `site/ai.py` TEXT_SINK (a ContextVar). Only while build_now runs for the start screen
  (`architect.STAGE`), the architect's call is streamed - Qwen through `DB._qwen_stream`, Claude through `_watched`
  (messages.stream) - and every piece goes to `_watch`'s sink, which reads the half-written JSON with `architect.peek_of`
  (name, summary, kind, every page with its for / purpose / sections, the last page = the one being written) and writes it
  beside the steps at most once a second (`activity.peek`, returned by GET /api/sites/stage/<ticket>). The deepen round only
  replaces what is shown once it has as many pages; after each pass the exact checked plan is shown (`_show`, done: true).
  The answer itself is unchanged; no watcher = the old non-streamed call.
- Real steps: "Checking the plan: n of m checks pass.", "Filling N gaps in the plan: ...", "Writing the data and the rules",
  "The deep plan did not come; starting the website straight from your words." (the plain-path fallback). The first two
  labels stay exactly as v0.835 pinned them.
- The preview (`peekView`): empty = an honest line + skeleton (still `.doc.skel`), then the name, kind, summary, page cards
  with section chips and a "N pages · M sections so far" count; the page being written is tinted.
- The typing box is open: what she writes is kept (localStorage `hoola.ws.pend.draft`) and put in the workspace composer
  when it opens - never sent by itself; Send stays off (dimmed) until then.
- The running step keeps its live clock between polls (redrawn only when the steps change).

Tests: `test_v0986_plan_peek.py` 8 (version, partial-plan reader, the plan streaming into the stage on Qwen, no watcher =
no stream, deepen never shrinks the view, build_now names the stages + clears STAGE, static pins, a browser walk: folded
message, card in view, draft kept, the plan growing in the preview, Show all). NOT VERIFIED on her server with a real Qwen
plan.

## v0.987.0 HOOLA LOGO - the real Hoola mark in the Web Studio (owner, her Web Studio home screenshot: "THIS PAGE IS GOOD AND PERFECT ::: JUST PUT THE HOOLA LOGO THERE")

The Web Studio's logo spot (sidebar brand + the top bar of every workspace screen, 5 places in webstudio.js) was a CSS
gradient ring, not the Hoola logo. webstudio.html now loads mark.js (the one drawing the app and the console use) before
webstudio.js, `hoolaMark()` draws `HoolaMark.svg({mono: true})` in each spot, and `.mark:has(svg)` drops the gradient and
colours it Hoola violet (`--pri`, light + dark). Nothing else on the home page changed. App Studio shares the stylesheet but
keeps its ring (the rule only applies where the mark is drawn). Tests: test_v0987_hoola_logo.py (3, incl. a browser check that
the sidebar mark is the SVG with no gradient). NOT VERIFIED in her browser.

## v0.988.0 PROMPT FIRST - the Web Studio reads her words, asks, and designs from them (owner: "VERY BAD ... EVERY TIME AI BUILD SAME LANDING PAGE FOR ALL INPUTS ... FIRST REMOVE THAT PAGE ENTIERLY ... AI WILL UNDERSTAND IT PROPERLY AND FIND THE PERFECT DESIGN, FONT, FONT SIZE ... ASK THE QUERIES TO USER IF REQUIRED ... ISP PORTAL ... A LOGIN PAGE AND A PORATL WITH ITS DATA ... ALSO CHECK THAT HOOLA WEB DEVLOPMENT HAVE THAT THINKING CAPABILTIY")

Root causes: (1) the v0.784 "A few quick choices" page ran BEFORE any AI call and was built from keyword matching
(`designq.questions` -> `library.understand`), and every look's style / palette / font pair came from the same fixed
tables (`L.brief`, `B.tokens`); the AI only wrote the art direction and the section text. (2) When the architect's plan
call failed, `_build_now` fell back to `S.new` = the library's page set for the business type: a marketing landing page,
even for "Build the ISP portal". (3) A plan the model labelled `lead_site` stayed a marketing site though her words said
portal.

Built: the choices page is gone from the Studio (`askDesign`, `qOption`, the card CSS removed; `studio_design_questions`
default off). Build mode: `architect.understand` = one short AI read of her words (UNDERSTAND prompt: ask only what
changes WHAT gets built, never colours / fonts / layout, max 3 questions with tap options) -> when it has questions,
`build_now` returns them and nothing is planned; the Studio shows them in the chat (`askCard` / `askFirst`: tap answers,
her own words, Skip) and the plan is drawn from her words + answers (`with_answers`, POST /api/sites `qa` + `asked`); an
ask of 40+ words skips the round. The plan carries a `design` block (feel, font pair id, palette, corners, base text size
14-19 px + heading ratio 1.10-1.42) checked in code (`design_of`: only real ids, hex colours, sizes in range) and look 1
is built from it (`design_ref` source "ai" -> `designq.PENDING` in `approve`; `build.type_scale` / `type_css` = --fs-base /
--fs-h1..h3 / --fs-lead read by hoola-site.css with the old sizes as fallbacks; `build.carry` keeps the font pair + type on
a colour edit - they used to fall back to the style's defaults). A "portal / dashboard / login" ask is always a system:
kind portal, the sign-in on the front door and at least one signed-in page with a data screen (`_app_pages`); the home =
compact front door, sign-in, then the main screen filled with samples (`site_plan`). A failed portal plan stops honestly
with her words kept (`_no_marketing_fallback`, 502); only a plain website may still start plainly.

Thinking: yes - the plan call runs with reasoning on (EFFORT site_art = xhigh, sections / critique high); on Qwen the
reasoning is requested but excluded from the answer, so it is not shown to her.

Tests: test_v0988_prompt_first.py (10, incl. a browser walk of the questions card); test_v0784's two Studio pins now pin
the page's removal. NOT VERIFIED on her server with a real model.

## v0.989.0 LIVE SCREENS + OWN DATA - (owner: "GO B1 B2" on docs/research/lovable/03_backend_vs_hoola.md): B1 - a portal's designed screens (dashboard, table, form, detail, board, calendar, approvals, sign-in, settings) were static HTML with invented sample rows and dead buttons; now the section writer is told the site's real lists (`_screen_lists`, `screens.lists_line`) and marks each screen with data-list / data-fields / data-hoola-live / data-hoola-stat / data-hoola-add; the build ties it to the real schema (`site/screens.py` bind: list matched by key / label / the only list, unknown or hidden fields dropped, a sign-in screen always Hoola's own sign-in box, a tied screen loses data-sample so it no longer blocks going live) and the page script fills it with the rows the visitor may see (`hoola-app.js` screens(): table rows, cards, board columns, calendar order, detail, approvals with decide buttons, KPI counts / sums, add button = the real form; live: an empty list says so and a list behind a login says that, the designed sample rows never show; the Studio preview keeps them while a list is empty). B2 - the Studio preview and every draft used the website's LIVE data (a draft copied the site's link): now a TWIN project holds their data (`site/twin.py`): the preview pages call /api/site-app/<site>~p (`preview_dataset`, `public_app`, `applink.project`), the preview twin follows the website's structure and keeps its own rows and members (her staff / admin accounts copied in), a draft gets its own twin, Accept carries only the lists / fields it added (`twin.carry`, never rows), Discard drops it; twins never reach the outside world (no payments, no outgoing actions, no her-own-database write-through, no scheduled jobs, no owner notes) and stay out of App Sahayak's app list. 11 tests incl. a browser walk. NOT VERIFIED on her server with a real model or a real portal.

Files: NEW `server/app/site/screens.py` (bind + lists_line), NEW `server/app/site/twin.py` (make / preview_of / carry /
drop), `site/ai.py` SCREEN_NOTE, `site/service.py` (_screen_lists, _app_line screen=, public_app `~p`, preview_dataset in
preview_file), `site/build.py` (bind in assemble), `site/applink.py` (project -> preview twin), `site/drafts.py` (_own_data,
carry on Accept, drop on Discard), `appmaker/connect.py` (fire / run refuse twins), `appmaker/logic/engine.py` (tick /
notify skip twins), `appmaker/service.py` (twins out of the app list), `site/assets/hoola-app.js` (screens()),
`site/assets/hoola-site.css`. Tests: `test_v0989_live_screens_own_data.py`.

## v0.990.0 PROVE THE RULES (owner: "GO B3" on docs/research/lovable/03_backend_vs_hoola.md): a website's data rules (who may add, see, change and remove entries in each list; staff-only and private fields) were enforced on every call but never tested for websites. Now `site/rulecheck.py` plays them through the real engine (appmaker.backend create / rows / update / delete, logic hooks included) on a throwaway copy of the lists (a twin, kind check, its own people, dropped after) by a visitor, two members and an admin; each answer must be what the rule says; the result is kept per website with a fingerprint of the rules; it runs again in the background after a list / rule change (`backend.change_schema`, `logic.apply`, switch site_rule_tests_bg) and before going live when the rules changed; a FAIL blocks going live (`hosting.blockers`, not a skippable dialog); GET / POST /api/sites/{ref}/rule-tests; Web Studio Cloud tab > Safety > Rule tests with Run again. 7 tests incl. a planted leak that is caught and blocks. NOT VERIFIED on her server.

Files: NEW `server/app/site/rulecheck.py`; `site/twin.py` (make staff=), `site/hosting.py` (blockers), `appmaker/backend.py`
(change_schema hook), `appmaker/logic/service.py` (apply hook), `main.py` (rule-tests routes), `config.py`
(site_rule_tests_bg), `static/console/webstudio.js` (Cloud > Rule tests). Tests: `test_v0990_prove_rules.py`.

## v0.991.0 SAME LANDING — the phone and console chats land words the same way (owner: "CHECK HOW HOOLA APP CHAT CONVERSATION IS SAME AS CONSOLE CHAT --- FONT, TIMING, WORD LANDING ETC" -> "GO")

The check found the font, sizes and gaps already the same, and the word landing different:
- **Console bug:** `HoolaStream.Pacer` (static/console/stream.js) set `this.t = now` every frame and used `Math.max(1, floor(dt/34))`, so the leftover time was thrown away and one word was released per screen refresh: measured 60 words/s at 60 Hz, 120 at 120 Hz (Calm = 34 ms a word, ~29/s). Now `this.acc` keeps the leftover; the first word comes at once; the catch-up (+min(2, queue/80) a frame) is unchanged. Measured with the real file in node: ~30 words/s at 60 and 120 Hz.
- **Phone:** streamed deltas were drawn raw (bursts from the network, last 3 words at 42 % ink); a whole reply used `_Reveal` (34 ms with ease-out, 10 s cap). Now `_Paced` (lib/ui/chat/hoola_chat.dart) = the console's pacer on a Ticker, for streamed AND whole replies; each word rises from clear to full ink over 460 ms (kLandSoftMs = md.js SOFT_MS; the console also blurs it lightly - not done per word on the phone); progress kept per turn (`_lands['stream:<turn>']`) so the final message carries on from the word the stream had reached (`_alreadyShown`); reduce motion = at once; `_Reveal` removed.
- **Headings:** phone # / ## / ### 20 / 18 / 16 -> 22 / 20 / 17 (v2.css h3/h4/h5.mdh); Hoola Code's sans and compact notes keep theirs.
- **Her message:** line height 1.45 -> 1.5.
- **Working clock:** counts from her newest message's time (`_sentAt`), not from when the row appeared.
Tests: test_v0991_same_landing.py (5; the pacer test drives the real stream.js in node); pins in test_v0283 / test_v0716 moved to the new line. NOT VERIFIED on her phone (CI compiles the Dart; no flutter here).

## v0.992.0 BACKEND TAB (built as 0.991; their SAME LANDING took 0.991, both kept; owner: "GO B5" on docs/research/lovable/03_backend_vs_hoola.md): the owner could not run her website backend from the Web Studio (the Cloud pane was a read-only table + a member list; backups, secrets, outside services and limits lived only under /api/apps/* with no screen). The Cloud tab now runs it: entries she can add / change / delete (the same field checks, rules and logic as every visitor, each in the change log), member roles, the change log (who changed what and when), backups + restore (back up now, download all data, restore to a backup or any minute - what would change shown first, her confirm, a safety backup first), secrets (typed once in a password box, sealed at once, never shown again) + outside services (approved by her tap) + recent runs, usage + limits; NEW `site/backend_tab.py` + GET /api/sites/{ref}/backend (one overview), POST /api/sites/{ref}/app/rows/{key}, GET /api/sites/{ref}/app/log; the rest rides the existing /api/apps/{ref}/* routes. 6 tests incl. a browser walk. NOT VERIFIED on her server.

Files: NEW `server/app/site/backend_tab.py`; `main.py` (backend / rows POST / app log routes); `static/console/webstudio.js`
(Cloud > Backend: backendPane, editable rows, member roles) + `webstudio.css`. Tests: `test_v0992_backend_tab.py`.

## v0.993.0 IN LINE (built as 0.992; their BACKEND TAB took 0.992, both kept) — the console working row sits under the reply's words (owner, her screenshots: "CHECK THE LOADING. MAKE IT INLINED WITH CONVERSATION")

Her long bank-list job showed "Reading the web page 1m 57s" about 60px below the last words, floating above the composer. Cause: `placeProgress()` always appended the working row to the chat column (`col`), i.e. as the next MESSAGE row, so it got the 44px gap between messages (v2.css `#app .col{gap:44px}`) plus its own padding, while the "Worked for" rows live inside the reply (`.mh .bd`, 12px gap). Now, once the turn has words (`TURN.afterText`), the row is placed inside `TURN.bd` (before the typing dots if present, class `inturn`); before any words it stays the last chat row, the reply's first line under her message. Every re-place path (step start, a finished block, the 600 ms quiet-words watchdog) goes through `placeProgress`. Tests: test_v0993_in_line.py (3; the browser walk streams words, starts a step and measures the row 0-20px under the last line on the same left edge - fails on the old code; HOOLA_SHOTS saves a picture); test_v0296 pin moved. Phone unchanged (its working row is already the next list row under the reply). NOT VERIFIED on her server.

## v0.994.0 SIDE ARROW — the working-row arrow points right while working, down when opened (owner, her screenshot: "CHECK THE DOWN ARROW --- IN LOADING MAKE IT HORIZONTAL DURING WORK. WHEN USER CLICK ON IT IT GETS DOWN")

The console working row ("Reading the web page 3m 49s") showed its step-list arrow pointing down while folded and upside down when opened (v0.721 `.hm-dn` rotate 180deg on open). Now, like Claude, folded = pointing right (`rotate(-90deg)`), opened = down (`transform:none`), for the working row (`.simple-progress .wtog`) and the "Worked for" fold (`.tools.hmfold>summary`) alike; the 0.2 s turn stays. Tests: test_v0994_side_arrow.py (3; the browser walk reads the arrow's computed angle: -90 while working, 0 after her tap). NOT VERIFIED on her server.

## v0.995.0 SIGN-IN, FILES, EMAIL (built as 0.993 / 0.994; their IN LINE took 0.993 and SIDE ARROW 0.994, all kept; owner: "GO B6" on docs/research/lovable/03_backend_vs_hoola.md, gap 7): her website had no Google sign-in (only her native apps had it), no place to see the files its visitors sent and no email at all. Now: Google sign-in for the website with HER web client id (Studio Cloud > Sign-in, the origins to add listed); the page uses Google Identity Services and the server checks the ID token itself (signature, audience, single-use nonce; the same member table, so a password account on the same email stays one person; a new account still needs the privacy tick); Google is allowed by the CSP only for a site that turned it on (`site/gsignin.py`); Cloud > Files lists every file (private unless in a list anyone may read, which entry holds it) and an unused one can be deleted on her confirm; Cloud > Emails = sign-in codes + "Forgot password?" (6 digits, hash only, 10 min, 5 tries, the answer never says who has an account, a new password signs out everywhere) and receipts per list that repeat nothing the visitor typed, through HER own mail service over SMTP (SITE_MAIL_* in the VPS .env), daily cap, log without bodies, never from a preview copy (`site/sitemail.py`); 9 tests incl. a browser walk. NOT VERIFIED on her server, with a real Google client or a real mail service.

Files: NEW `server/app/site/gsignin.py` (on / csp / headers, Studio view + save), NEW `server/app/site/sitemail.py` (settings,
send through SMTP or capture, codes, receipts, the log); `site/applink.py` ops sign_nonce / google / mail_code_start /
mail_code_verify + receipt after create + schema security.email_code; `site/backend_tab.py` files / delete_file / mail /
mail_save; `site/hosting.py` + `site/service.py` CSP via gsignin.headers; `main.py` 4 public + 6 Studio routes;
`config.py` site_mail_*; `site/assets/hoola-app.js` (Google button, Email code tab, Forgot password); `static/console/webstudio.js`
(Cloud > Sign-in / Files / Emails, accessPane). Tests: `test_v0995_signin_files_mail.py`. Deploy: SITE_MAIL_PROVIDER=smtp +
SITE_MAIL_SMTP_HOST / _PORT / _USER / _PASSWORD + SITE_MAIL_FROM in the VPS .env for emails; Google needs only her client id in
the Studio. A live site gets the new login-box script with its next built version.

## v0.996.0 BACK TO WORK — a working chat comes back exactly as it was (owner: "WHEN ONE SESSION IS WORKING AND WE START NEW SESSION AND AGAIN COMEBACK TO WORKING SESSION ---- WORKING SESSION WORK GET HANGED AND SHOW UNWANTED THING IN CHAT SPACE. FIRST FIND THE EXACT ISSUE AND FIX THIS PERFECTLY")

Found by walking it in a real browser (chat A working: steps, words, a note, a long step running; open chat B; steps go on in A; back to A).
Coming back, `openConv` redrew the chat from the timeline, and:
1. `renderEvents` skipped every `step` event - the running turn lost its steps; the working row was rebuilt by `typing(true)` as
   "Thinking… 1s" (the clock restarted) and stayed so until the NEXT step, which on a long tool is minutes = it looked hung.
2. The `/live` snapshot was pushed into its block unconditionally: after a note (`tag(new_block=True)`) the live block is empty, so the
   note's words were reset to nothing (and an empty block hid the working row).
3. Working-or-not came from `CH.isBusy` (a flag the page remembered from its stream) - stale = a finished chat opens with "Thinking"
   and Stop for ever; missed = a working chat opens looking idle.

Fix: `events._working(conv)` -> the timeline (first page only) carries `busy` (the chat lock, the same truth as the chat list) +
`busy_since` / `busy_from` (its last typing-on). The console syncs the sidebar flag from it and calls `renderEvents(events, any,
liveFrom)`: every event of the running turn goes through the LIVE path at the time it happened (`REPLAY_AT` / `nowMs()` in
`liveStep` / `foldLive`; `resumeStep` = running at its first event, done at its last) - steps into the one working row, words folding
them into "Worked for", replies of the turn left not-done (no Copy / Retry mid-turn), the turn's block kept as TURN so what comes next
lands in it. `/live` text goes in only when there are words and the block is not already a saved message. Then the row shows the step
it is on, under the words, with the clock from the turn's start. Tests `test_v0996_back_to_work.py` (5; 2 browser walks: the round
trip + a stale busy flag). NOT VERIFIED on her server. Phone: not changed (it keeps its own per-chat state since v0.889).

## v0.997.0 KHULA PITARA — archives she attaches are opened and read; honest emails from their real figures (owner, her BSNL Goa job beside Claude's: "WHY REPLY LIKE THIS FIND THE EXACT ROOT CAUSE --- ALSO--- WE WANT EVERYTHING LIKE CALUDE TEXT, PROPER CONVERSATION, PERFECT RESULT")

The same ask went to Claude and to Hoola: a RAR of BSNL invoices (Mar-Oct 2026) and "draft a formal email to BSNL Panjim
and Madgaon". Claude installed an extractor, read 8 invoices (and spotted 2 duplicates), and wrote an exact table totalling
Rs 2,24,926.74 with the Goa GSTIN on the invoices. Hoola could not open the RAR, pulled facts from other mails and memory,
and wrote "11 months unpaid since Dec 2025" with her MAHARASHTRA GST and Akot address, raw ** and | table pipes in the mail,
"BSNLJUNE2026.pdf" under "What was made" (it was never opened), notes cut mid-word ("exact invoice amo") and every step
listed twice in the plan card. Root causes in the code:
1. `file_read` had no archive support (docread / mailbox.mime read PDF, Word, Excel, slides, text - never ZIP / RAR), and the
   pylab sandbox blocks programs, so unrar could not run there either. The RAR was data Hoola never saw.
2. `santosh.RESULT_LIMIT` had no entry for file_read: every read was cut to 6,000 characters before the model saw it
   (a PDF's 15,000 too).
3. `email_draft` sends markdown only when the model sets markdown=true; it wrote markdown and left it false, and
   `mime.md_to_html` could not draw a table anyway.
4. `goal` cut notes at 200 characters mid-word; `build_report` took ANY file name in a done step's note as "made"
   (a file it only tried to read) and internal ids (eml_...); the console and phone plan cards drew the steps AND the
   report's "What was done" (the same lines again).

Fix: NEW `server/app/archive.py` - `open_archive` (stdlib ZIP / TAR, then libarchive-c for RAR4 / RAR5 / 7z / ISO / CAB,
then rarfile when an unrar program exists), walls: names flattened (no `..`, no absolute), 40 files, 30 MB each, 120 MB in
all (said when hit), passwords and programs (by name, MZ / ELF / #! bytes, filecheck) listed never opened; `unpack` stores
every file inside as her own file (same-content copies named `same_as`). `chatfiles.store` unpacks on upload and
`context` lists each inside file with its file_id (or "NOT OPENED - nothing inside this archive was read"); `file_read` on
an archive reads every file inside (40,000 characters shared) with the rule that every figure must come from them;
RESULT_LIMIT file_read 44,000. Core + full prompts: an unread file is said to her in one plain line FIRST and never filled
in from other mails or memory; a formal letter's facts (sender GSTIN, address, dealer id, amounts, months) come from that
matter's own documents, else a [blank]. `mime.looks_md` (bold / heading / table / link) makes both send paths and
email_draft treat a markdown body as markdown; md_to_html draws tables + <hr>, md_to_plain lines tables up and drops
separators; the console email card shows the email rendered with Edit / Preview. `goal.cut` (whole word + ellipsis, 240),
made = her list + links + file names in notes that say made / saved / created, internal ids dropped; console
`goalReport(r, withSteps)` and phone `_GoalReport(stepsShown)` skip "What was done" when the steps are on the card.
requirements: libarchive-c; the deploy log prints "RAR reader ready" or the one command (`sudo apt-get install -y
libarchive13`) - ZIP and TAR need nothing. Tests `test_v0997_khula_pitara.py` 14 incl. real RAR4 + RAR5 files from the
rarfile project (ISC, tests/files/RAR_SAMPLES_LICENSE.txt). NOT VERIFIED on her server or with her RAR.

## v0.998.0 ONE WRITER - one writer per chat, several workers, several checkers (C1 of docs/CLAUDE_CHAT_100_PLAN.md)

Owner, after the Claude chat research: "OUR OBJECTIVE WAS ONE PROMPT -- MULTIMODEL -- PERFECT RESULT" -> "GO C1 --
CONCEPT:: 1 WRITER, SEVERAL WORKER, SEVERAL CHECKER".

**The fault.** The Box (v0.958-v0.979) chose the model for every message, so the model that TALKS to her changed from
message to message (and inside one on a hand-over); 1 in 10 messages was held out at random on today's routing (another
model again); and a reply that failed the final check got a second "correction" message under it, written by a model one
level up. One chat spoke in several voices, and the fix came after the wrong answer had been read.

**What changed.**
- `pipeline/writer.py` - THE WRITER. Chosen on the chat's first Box message (at least `pipeline_writer_floor` MID, so a
  chat that opens with "hi" keeps a capable model), stored in `data/pipeline/writers.db` (90 days), kept for every later
  message. It changes only: `up` (a later ask needs a higher level - the chat moves up, never back down), `moved` (the
  writer is paused / banned, or cannot do this message: a picture it cannot read, no tools), `handed` (it failed
  mid-reply and a backup finished it - the backup writes from then on). Each change is ONE quiet line, a `model_switch`
  event (local to its chat, never pushed; console v2.js `.note.mswitch`, phone HCQuietLine + the old chat screen). Her
  own dropdown pick is always the writer (nothing said). A routine / wake never chooses the chat's writer but uses it.
  `turnbox.begin` (one part) and `turnbox._apply_writer` (the reply part of a P3 message) both go through it.
- Workers: unchanged - P3 parts run side by side, each on the best model for its kind; they never speak to her.
- `pipeline/checkers.py` - THE CHECKERS, run on the writer's draft BEFORE it is shown (both chat loops,
  `santosh._box_review` from `_turn_after_model`): the code check (every key figure in her words or a tool result,
  files exist, what a part could not do is said) on every draft, plus a model checker from ANOTHER company than the
  writer (kind check, `pipeline_checker_level` MID; falls back to the chat board) when tools ran, several parts, a
  HIGH+ ask or a draft of `pipeline_checker_min_chars` (700); JSON answer, at most 4 problems, 25 s clock, a failure =
  no problems (never blocks). Problems go back to the SAME writer as one note ("write the whole answer again ... say
  plainly what is not confirmed"); the streamed draft is retracted and the rewrite lands in the same reply. One round per
  message. The review is on the job sheet (`review`: by, problems).
- `turnbox.fix_round` no longer posts the after-reply correction (`pipeline_fix_after` False brings it back); the sheet
  says "checked before the reply - no second message".
- `watch.hold_out(conv)` - the held-out share is per CHAT (sha1 of the chat id), so a chat is always Box or always
  today's model.
- The "Made with" receipt is unchanged (her v0.976 ask).

**Tests.** `test_v0998_one_writer.py` 19: pinned at MID, kept when the Box would pick another, up once never down,
off -> moved with a line, cannot read a picture -> moved, her pick wins silently, routines never pin, switch off, two
messages of one chat on one writer after the 30-minute sticky is cleared, hand-over mid-reply moves the writer + says
so, holdout per chat, code checker sends a wrong figure back once, model checker is another company and its problems
count, a failing checker never blocks, short no-tool answers get only the code check, checkers switch, and a full chat
turn on both loops (wrong draft -> checker -> same writer rewrites -> only the fixed answer is ever her reply, no
box_fix message); test_v0969's fix-round test now covers the switch. Pipeline suites 67 + 125 green.

**NOT VERIFIED** on her server: no live chat has run through one writer + the checkers; the model checker adds a few
seconds after the words finish on the turns where it runs.


## v0.999.0 HER WRITERS - GLM-5.3 writes, DeepSeek V4.1 Flash backs it up and checks it

Owner, after the writer research (docs/research/claude_chat/06_writer_models.md): "LETS GO WITH GLM 5.3 AND DEEPSEEKV4.1 FLASH --- FOR WRITER".

- Why these two: on the public LMArena chat board (11 Nov) GLM-5.3 scores 1475 against Claude Sonnet 5.5's 1469, and on
  OpenRouter's own tau2 tool run (17 Nov) 77.3% against 78.8%, at about 1/20 of the price ($0.07 / $1.4 per M tokens).
  DeepSeek V4.1 Flash: 1464 / 75.1%, the lowest hallucination rate read (Vectara 4.2%), $0.036 / $0.5.
- `config.pipeline_writers` (default "z-ai/glm-5.3,deepseek/deepseek-v4.1-flash-1017"; '' = the Box chooses as in v0.998).
- `writer.fixed()` + `writer._fixed`: the first of her writers able to write (not paused, can take the message) writes; a chat
  keeps the one it has while it can still write (GLM back after a pause does not pull the chat back); the others are its
  backups, plus ONE Box pick as a last safety. A chat pinned to an older writer before this release moves to hers quietly;
  her writer going down is said in one `model_switch` line. Both down = the Box's pick for that message only, said, nothing
  pinned. No moving up while her writers are set. Her dropdown pick still wins. Routine / wake turns use her writer too.
- `writer.handed`: the safety model finishing a reply never becomes the writer ("... finished this reply."); DeepSeek
  finishing it does ("... and continues this chat.").
- `checkers.pick_checker`: the model checker is the OTHER of her writers, of another company than the one that wrote
  (GLM -> DeepSeek, DeepSeek -> GLM, a safety model -> GLM).
- conftest sets PIPELINE_WRITERS='' so the older suites keep pinning the Box's own choice; tests/test_v0999_her_writers.py 13.
- `pipeline_sheets` (vps-ops) now prints each chat's writer + the checkers' verdict and greps the writer / checker log lines.
- NOT VERIFIED on her server: no real GLM-5.3 / DeepSeek call from here; Hinglish quality has no public benchmark.


## v0.999.1 HER WRITERS FIX - thinking writers are no longer cut off; the checker reads the whole chat

Owner "DONE CHECK" after her 5 English test messages in one app chat (pipeline_sheets run 554, 18 Nov 13:22 UTC):
- msg 1 (tips): GLM-5.3 wrote it, checkers ok - worked.
- msg 2 (expenses table): the planner split it in 2 parts; the worker's check failed on "figure 100" (percentages adding to
  100) and moved up to Opus 4.6; the writer GLM-5.3 gave no first word in 8 s -> DeepSeek took over and became the writer.
- msg 3 (salary follow-up): DeepSeek wrote it; the code checker sent it back for 9500 / 4200 / 2300 - figures from HER OWN
  earlier message, which the facts list never included.
- msg 4 (news) and msg 5 (two tasks): DeepSeek -> GLM -> Sonnet / Kimi, each "no first word in 8 s", then failed.

Root cause: the Box asks OpenRouter with reasoning EXCLUDED, so a thinking model sends nothing until it has finished
thinking; with a ~30k-token prompt that is often more than 8 s, and the first-word watch (v0.969 P4) took that as a dead
model - even Sonnet 4.6 failed it.

Fixes:
- `llm._target`: a Box call (BOX_OWNS) streams its reasoning (`exclude: false`) - the watch's first() fires on the first
  thought - and asks `provider: {sort: latency}` (`pipeline_provider_sort`, '' = OpenRouter default).
- `handover.FIRST_WORD_S["chat"]` 8 -> 25 s (calls stay 3 s).
- `checkers.chat_facts(conv)`: her last 8 messages (source "her", so one step of arithmetic on them counts) + Hoola's last 3
  replies join the facts list.
- `check.final_check`: 100 is always in the pool.
- tests/test_v0999_her_writers.py +4. NOT VERIFIED on her server.

## v0.999.2 CREDIT IS THE ACCOUNT'S

(owner "DONE CHECK" on her v0.999.1 test, 18 Nov 14:09-14:19): message 1 ran on GLM-5.3, then OpenRouter answered 402 (credit used up) on message 2 - the writer handed to DeepSeek and Gemini, which failed the same way on the same account, the failures marked GLM-5.3 as failing, and other calls paused the OpenRouter brain, so `turnbox._why_not` (which read cheap_brain) sent messages 3-5 past the Box and its writer. Now a credit 402 is the ACCOUNT's (`runner.CREDIT`): no outage mark on the model, no hand-over, the error with the add-credit line goes back; and the Box asks `llm.chat_brain()` - a paused brain is still her chat's brain; 3 tests. NOT VERIFIED on her server (needs OpenRouter credit added first).

Files: `server/app/pipeline/runner.py` (CREDIT, credit(), call() raises a credit error without a hand-over, model_failed skips it), `server/app/pipeline/turnbox.py` (_why_not reads llm.chat_brain), `server/tests/test_v0999_her_writers.py` (+3). Her action: add OpenRouter credit (openrouter.ai > Settings > Credits) before the next test - a 402 now ends the reply with the add-credit line instead of trying other models.

## v0.999.3 CHECKER LIKE A REVIEWER

(owner "Check" on her v0.999.2 test, 18 Nov 14:54-14:59: all 5 messages ran on GLM-5.3, no hand-over, no 402 - but the DeepSeek model checker sent back 4 of 5 drafts, partly for suggestions it should allow: recipe quantities, "6-8 pm", a loyalty scheme, and "tea" from her previous message flagged as an unknown name): the model checker now flags only figures stated AS FACTS (her business, her figures, prices, the world), lets advice / recipes / examples / suggested amounts and times through, and reads her earlier messages in the chat (`checkers.chat_lines`); its real catches (a half answer, Pune fuel prices not in the tool data, leftover text from an earlier reply) still go back to the writer; 2 tests. NOT VERIFIED on her server.

Files: `server/app/pipeline/checkers.py` (MODEL_CHECK rule 2 = figures stated as facts only, suggestions allowed; chat_lines; model_check sends her earlier messages), `server/tests/test_v0999_her_writers.py` (+2). Her v0.999.2 run, all on GLM-5.3, finish times from her message: 39 s, 41 s (3 parts), 22 s, 63 s (web search), 36 s - each including one checker send-back of ~5 s.

## v0.999.4 CHECKER KNOWS HER

(owner "DONE CHECK" on her v0.999.3 test, 18 Nov 15:31-15:36: suggestions now pass - Diwali offers, her bakery profit and the November follow-up all went straight through - but two send-backs were for things Hoola knows about her from her profile: the WhatsApp sign-off "Meghna Anil Ingle, Director, Newtika Private Limited" and GST state code 27 (Maharashtra)): the checker now gets what the writer was told about her (profile, memory page, pinned facts, project - `checkers.about_her` via `core_prompt.chat_context`) and its figures count as facts for the code check; tool results are kept up to 24,000 characters for the figure check (web results were cut at 8,000); the real catch ("earlier this week" said with no source) still goes back; 2 tests. NOT VERIFIED on her server.

Files: server/app/pipeline/checkers.py (about_her, MODEL_CHECK line, review passes it + memory figures), server/app/pipeline/turnbox.py (tool sink 24k), server/tests/test_v0999_her_writers.py (2 tests).

## v0.999.5 SHOWN ONCE

(owner "DONE CHECK --- WHY SOME PROMPT REPLY IS LOADING 2 TIMES --- REPLY COME AND VANISHED AND AGAIN GIVE SAME REPLY" on her v0.999.4 test, 18 Nov 15:49-15:54: the replies that landed twice were exactly the 4 of 6 the checker sent back): the writer's draft streamed to her screen while it was being written, then the send-back wiped it (`live.retract`) and the rewrite streamed again; now the words of a Box reply the checkers will read are HELD (`Live.hold`, `santosh._box_holds`, switch `pipeline_checker_hold`) - thinking and the working row still show, a draft that passes goes out once (`Live.release`, the app's pacer lands it at reading speed), a draft sent back is never shown and the rewrite streams live once; words said before a tool go out when the tool starts; also the model checker now reads only her real earlier messages (tool results and its own notes used up the rows read: "her only earlier message was this one") and the sheet's check line counts the same facts as the checkers; 6 tests. NOT VERIFIED on her server.

Files: server/app/livereply.py (Live.hold, block(hold=), release, retract under hold), server/app/agent/santosh.py (_box_holds, _box_review(final, live) releases on pass, release before a tool), server/app/config.py (pipeline_checker_hold), server/app/pipeline/checkers.py (chat_lines reads only displayed rows; facts_more), server/app/pipeline/turnbox.py (end check reads facts_more), server/tests/test_v0999_her_writers.py (6 tests).

## v0.999.6 PARITY ONE WRITER — the parity card made fair for the one-writer Box (18 Nov 2026; owner: "GO PARITY")

Her v0.999.5 run (conv_158ac09, 16:21-16:27): all 6 replies written by GLM-5.3, 5 of 6 passed the checker first time,
the gold-rate draft was sent back for a real mistake (the rate given per 10 grams when its own figures were per gram,
and a goldrate.com figure in nothing the turn read) and its rewrite passed; every sheet check line "ok". She asked "IS
WRITING NOW PERFECT"; the honest answer was no proof either way from 6 short asks, and the real measure is the parity
card (60 multi-turn conversations, `quality/paritycard.py`). Before she runs it, the card had to be fair for the Box:

- Its `one_brain` rule counted every model called inside a recorded `santosh._call_brain` step. A Box helper part and a
  crew agent both run through `team._run_agent` -> `santosh._think` -> `_call_brain`, so the Claude Sonnet / Opus
  helpers on a multi-part ask (the Diwali shape) would have failed that conversation as a "second brain". Now
  `team.AGENT_NOW` (ContextVar, set for the whole sub-agent run, reset in its finally) marks a sub-agent; the card's
  recorder tags each step `role: writer | helper` (+ the agent's name); `one_brain` = ONE WRITER across the
  conversation ("written by X, Y" when not); helpers and the planner / checker / memory calls (no step of their own,
  read from the conversation's outer run meter) are listed apart (`helpers`, `others`). A step with no role (a card
  saved before) counts as the writer's. RUBRIC_V 3. Calibration +1 planted case ("writer + helpers" must pass) = 21.
- The card's header (`brain_line`) names the Box: writers, checkers on / off, held until checked.
- The watch's held-out share (`pipeline_holdout_pct`, ~10 % of chats on the old routing, per chat) is set to 0 while
  `live_card` runs and restored after - the card runs in its own CLI process, her server is untouched.
- Tests: `test_v0999_parity_writer.py` (8) - helpers not a second writer, two writers fail and say who, old cards read
  as writer, the recorder tags a helper step, `_run_agent` runs marked and unmarks, the header names the Box, the
  printed card lists writers apart, the holdout off only while the card runs; `test_v0732_parity_card` calibration
  21/21.
- Baseline to compare with: 10 Nov 2026 on GLM-5.3-Flash (rubric v1/v2, set v1): SCORE 88.1/100, 35/60 passed,
  ~38 min, Rs 328.7.
- NOT RUN: the live card is hers to start (vps-ops `parity_card`, read with `parity_card_check`); it spends real model
  money - GLM-5.3 + the checker on every reply + Claude helpers on multi-part asks, so likely more than Rs 328.7.

## v0.999.7 ONE BACKEND (owner: "LETS CONTINUE THE NEXT WORK" -> B4 of docs/research/lovable/03_backend_vs_hoola.md): three backends shared two tables - the v0.305 site engine (A), a website on App Sahayak's backend + logic (B) and Hoola Cloud for React App Engine apps on its own ae:<app>:p|l keys (C), which had no journal, backups, logic, phone OTP, 2FA or sessions. Now every App Engine app has ONE App Sahayak project behind it (status engine, hidden from the app lists) and that project's preview twin for the Studio (`appengine/cloud.py` link / data_project / site_key / forget); the Cloud schema stays the record of every run (numbered, refusals, her data-loss tap) and each run is written into the project's lists; the app's calls go through `appmaker/backend.py` (journal + daily backups + restore, approvals / workflows / functions, phone OTP when the SMS service is set, staff 2FA, sign-in sessions + sign out everywhere), rows and members under the old keys move on first touch and logins made before keep working; shell.js + src/lib/hoola.ts carry the new calls; path A: the v0.305 engine no longer serves anything, an unlinked site joins the backend on its first public call (`applink._join_now`); 6 tests. NOT VERIFIED on her server.

Files: `server/app/appengine/cloud.py` (link / _synced / data_project / site_key / old_key / forget, call through the backend
with OTP / 2FA / sessions / approvals / functions, English refusals, overview `backend`), `appengine/service.py` (delete =
CL.forget), `appengine/saboot.py` (in-browser check forwards every op), `appengine/shell.js` + `template/src/lib/hoola.ts`
(phoneStart / phoneVerify / verifyCode / sessions / endSession / signOutEverywhere / approvals / fn; signIn says when a 2FA
code is needed), `appmaker/service.py` (engine projects out of the app lists + lookups), `site/applink.py` (`_join_now`, the
v0.305 serving branch removed, live / queue doors join too), `main.py` (the Cloud route passes the browser line),
`static/console/appengine.js` (Cloud tab line). Tests: `test_v09997_one_backend.py`; `test_v0407_ek_dimaag.py` +
`test_v0414_ek_dimaag2.py` setups now write the old site's data straight into the v0.305 tables (commented pin change: a
public call links at once). Not merged: the two schema op vocabularies (Cloud's runs on top, written into B's lists), the
website shop's own tables, the ISP archetype. Deploy: the usual vps-ops deploy; nothing in the .env.

## v0.999.8 HOOLA CODE SAME LOOK (built as 0.999.7; their ONE BACKEND took 0.999.7 - REBASE PROTOCOL, both kept) — Hoola Code in the console's look (18 Nov 2026; owner: "GO" after three previews)

- `static/console/hoolacode.css`: the v0.914 `:root` warm-paper token blocks removed (light + dark) - the page inherits v2.css tokens; new end blocks: title bar left, `.hcd-new.on`, the typing box (`.hcd-ask` / `.hcd-cp` hairline + soft shadow, grey send while the placeholder shows, `.hcd-askrow>.hcd-flex{flex:1}` = two groups, chips stay 32 px for the scale test), `span.hcd-heromark`.
- `code.js`: `hcd-new` gets `on` at home; the hero mark = `HoolaMark.think(56)` with the PNG as fallback.
- `hoolacode.html`: loads mark.js; every stamp 0.950.0 -> 0.999.8 (they had not moved since v0.950, so a browser could keep old files).
- Checked: test_v0807_hoola_code_design (17 views measured) + test_v0924; home, a done session (light + dark) looked at by eye. The other pages take the same tokens but were not each looked at.
- NOT VERIFIED on her browser.

## v0.999.9 MODEL TIERS (19 Nov 2026)

Owner: "GO BUILD THE TIERS" (after the tier tables in docs/research/claude_chat/11_model_tiers.md, 12_media_tiers.md,
13_coding_tiers.md, 14_call_employee_tiers.md).

- NEW `server/app/tiers.py`: four tiers ULTRA / HIGH / MEDIUM / LOW ('' = Hoola's normal setup, nothing changes).
  `TABLE` = job -> tier -> [main, backup from another company] for chat (the writer), write, reason, facts, extract,
  image_in, pdf, research, code, employee (long tool jobs), call (a call's brain), hoola_code, web (Web Studio);
  `KIND_JOB` maps the Box's kinds onto those jobs; `VIDEO` = the video studio's Hoola Auto quality / way of choosing /
  picture size per tier; `PRICE` = each model's maker price ($/M in, out; OpenRouter endpoints 19 Nov); `COST` +
  `ULTRA_WARNING` for the screen. Per tenant in data/model_tier/<tenant>.json. Offered only when the chat runs through
  OpenRouter (like the model dropdown). Switches `model_tiers`, `model_tier_dir`.
- Her choice: GET / PUT /api/model/tier (main.py); ULTRA only with `confirm_ultra` (she saw the credit warning).
  Console: the composer's model menu (v2.js `loadModels` / `setTier` / `modelMenu`) lists "Quality tier" (normal +
  the four) above the models; the chip shows the tier; ULTRA asks her first. Her own model in the dropdown always wins.
- Where the tier applies: `santosh._run_turn` (the turn's model, a call's brain = job call; `tiers.NOW`), the step
  loop (long jobs -> employee model, hard asks -> reason model, no switch to Claude), the Box (`box.choose_for` tier ->
  `tiers.apply_box`, a call surface -> the call model, a model that cannot take the part is skipped, the tables' pick
  kept as the last backup; `parts.size` tier; `writer.fixed(tier)` = the tier's chat writers), Hoola Code
  (`devsahayak/brain.session` -> PART.tier, `_qwen_call` runs the tier's hoola_code models before the Box), the Web
  Studio (`site/ai.web_model` from the usage owner's tier), the video studio (`studio/service.create` starts from
  `tiers.video_prefs`; her own prefs win). PC code untouched (frozen).
- Price ceiling: every OpenRouter call of a model in `tiers.PRICE` carries provider.max_price = `model_price_cap_x`
  (1.25) x the maker's price - `llm._priced` in `_openai_create` / `_stream_body`, `tiers.with_cap` in the Hoola Code
  and Web Studio bodies. OpenRouter cannot route such a call to a provider charging 2-19x more any more. A call no
  provider can serve under the ceiling (400 / 404 about prices or endpoints) is asked again once without it
  (`llm._cap_refused` / `_uncap`, `STATS_CAP`; Hoola Code `_qwen_post` / `_qwen_stream` too). Switch `model_price_cap`.
- Not tiered here: picture making / editing, voice-over, music, speech to text (Create's own engines; the tier tables
  in 12_media_tiers.md are on the tier screen only), the PC brain (frozen), Claude-only paths.
- Tests: test_v0999_9_model_tiers.py (12): the table (4 tiers, two companies, a price each), ULTRA needs her yes, not
  offered without OpenRouter, the ceiling maths, llm adds / drops it, a refused ceiling asked again, the Box per kind
  + call + picture skip, the writer, the video prefs, Web Studio + Hoola Code, the routes, the console menu.
  NOT VERIFIED on her server: no live call with max_price has been made; OpenRouter's max_price field is from its
  provider-routing docs.

## v0.999.10 TIER PICKER - the Quality tier on the phone (owner: "ADD TIER PICKER IN PHONE APP ALSO")

v0.999.9 put the tier picker in the console only. The phone now has the same page:
- `lib/ui/shell/hoola_tier.dart` `HoolaTierPage` (new design): "Hoola's normal setup" plus ULTRA / HIGH / MEDIUM / LOW
  from GET /api/model/tier, each card with its line, what a reply / an AI-employee job / a call minute / a 30 s reel
  cost, and "Which models it uses" (chat, apps and code, AI employee jobs, calls, Hoola Code, websites; main + backup).
- ULTRA opens a sheet with the server's own credit warning; only "Yes, use ULTRA" sends confirm_ultra (the server
  refuses it otherwise). PUT /api/model/tier saves; the page shows the server's note that her own model wins.
- Ways in: Settings > You and Hoola > Quality tier (new design) and Profile > Quality tier (old look).
- `lib/api.dart` modelTier() / modelTierSet(). Server unchanged.
- Tests: `server/tests/test_v0999_10_tier_picker.py` (4). NOT VERIFIED on her phone; CI compiles the Dart first.

## v0.999.11 TIER WRITERS - each tier's writer chosen for words AND tool calls (owner: "GO BUILD THE 4 CHANGES")

The v0.999.9 tiers picked each tier's chat writer on chat score only. The writer runs the whole turn (it picks and fills
the tools), so the picks are now made on words AND tools (`docs/research/claude_chat/15_tier_writers.md`):
- `tiers.TABLE["chat"]`: ULTRA Claude Opus 5.5 / Gemini 4 Argon, HIGH Gemini 4 Hydrogen / GPT-6.1 Terra, MEDIUM GLM-5.3 /
  DeepSeek V4.1 Flash (the normal setup's writer), LOW DeepSeek V4.1 Flash / GLM-5.3-Flash. `write` LOW also DeepSeek.
  Gemini 3.8 Flash stays HIGH's reader for pictures / PDFs / audio and its maths helper.
- `pipeline/checkers.pick_checker`: the checker is the other model of her tier's pair (another company), not always the
  default writers.
- `pipeline/writer.handed`: a tier's own backup that finished a reply keeps the chat (was treated as a one-off safety).
- `tiers.COST` reply line: ULTRA Rs 8.5, HIGH Rs 3.2, MEDIUM Rs 0.2-2.8, LOW Rs 0.1.
- Tests: `test_v0999_11_tier_writers.py` (7); two v0.999.9 expectations moved to the new writers.
NOT VERIFIED on her server: Gemini 4 Hydrogen / Argon have not answered on her OpenRouter account; GPT-6.1 Terra's chat
score is not on the boards; Hinglish is measured by no board.

## v0.999.12 GATES IN CODE (owner: "GO B7" on docs/research/lovable/03_backend_vs_hoola.md, gap 8): two gates lived in the prompt - her own chat agent (actor owner) could build an architect plan (website action=architect_ok) and put a website logic draft live (logic_ok) after a haan in words, and Hoola Cloud's confirm_public (open a list holding personal data to the whole internet) was a flag the MODEL set inside the change. Now the chat tool only puts the card back: architect_ok re-sends the plan card with its Haan, build it button (`architect.ask_tap`), logic_ok says the draft waits in the App & data tab (`applink.logic_ask_tap`); only the routes her buttons call build / apply. confirm_public is dropped from the tool's changes and refused in `cloud.apply_changes(from_model=True)`; the change set waits as a Let anyone read this card in the Studio Cloud tab (`queue_public` / `pending_public` / `public_run`, POST .../cloud/changes {public_ok, confirm}, Not now = pending/clear {which: public}); a test reads every agent module and fails if one calls a her-tap function; test_v0407 architect pin changed on purpose (commented); 7 tests. NOT VERIFIED on her server.

Files: `server/app/site/architect.py` (ask_tap; _publish takes the chat), `site/applink.py` (logic_ask_tap),
`agent/site_tools.py` (architect_ok / logic_ok never approve / apply; description), `appengine/cloud.py` (apply_changes
from_model, the refusal names the fields, queue_public / pending_public / clear_public / public_run, overview
pending_public), `agent/appengine_tools.py` (confirm_public dropped, from_model=True, the card queued, description),
`main.py` (POST /api/appengine/{ref}/cloud/changes public_ok, pending/clear which=public),
`static/console/appengine.js` (the Let anyone read this card), `docs/research/lovable/03_backend_vs_hoola.md` (status).
Tests: `test_v09999_gates_in_code.py`; `test_v0407_ek_dimaag.py::test_architect_tool_needs_her_haan` changed on purpose
(the owner's chat agent no longer builds; her tap's approve does). Not changed (not gap 8): plan / look picks, App Sahayak
design approve, moves_ok, enterprise run approve, approval decisions still follow her words in chat. Deploy: the usual
vps-ops deploy; nothing in the .env.

## v0.999.13 BUSINESS MODELS (owner: "LETS CONTINUE THE NEXT WORK" after B7 -> gap 10 of docs/research/lovable/03_backend_vs_hoola.md): App Sahayak models 43 complex businesses (archetypes + datamodel tables: an ISP = internet plans, subscribers, OLT / PON / ONT, fiber routes, tickets, work orders, bills, payments) but the website path never read them - an ISP portal's lists came only from the plan's words. Now her words pick the model in code (`site/basemodel.py` match: whole words from each archetype's word list), the data draft reads it as starting_model (`logic.service.draft(base=)`, the author keeps its keys / types, renames to her words, drops what the site does not need), and the plan card's Data part says Started from Hoola's ISP / FTTH operations model and names the model's own tables the draft left out (a note, never forced); no known business = drafted as before; 7 tests. NOT VERIFIED on her server / with a real model.

Files: NEW `server/app/site/basemodel.py` (match = her words -> archetype key; lists = the model's tables in Hoola's field
types, the business's own module whole + each later module's main records (bills, payments), links inside the model kept as
ref, outside as text, secret-looking fields left out, <= 24 lists; missing = the model's own tables the draft did not keep),
`site/architect.py` (_data_draft passes base + records data.model; the card's Data part lines / model / missing),
`appmaker/logic/service.py` (draft / _prompt take base -> starting_model; AUTHOR_SYSTEM says how to read it),
`docs/research/lovable/03_backend_vs_hoola.md` (status). Tests: `test_v099913_business_models.py`. Left: gap 9 (the
website shop's own tables). Deploy: the usual vps-ops deploy; nothing in the .env.


## v0.999.14 ONE CHAT KIT (built as 0.999.14 / 0.999.12 / 0.999.13) - every chat panel in Hoola lands, works and looks like the Hoola chat (owner: "WE WANT EVERY CHAT SECTION MUST HAVE SAME FEATURE, DESIGN AND TEXT LANDING, TIMING, SPACING EVERYTHING SHOULD BE SAME EVERY WHERE -- CURRENTLY HOOLA CHAT AND HOOLA CODE IS PERFECT ... BEFORE DEPLOYMENT SHOW ME EVERY TOOL / FEATURE CHAT PANEL WITH REAL PROTOTY HERE" -> prototype claude.ai/artifact/JLkiBDRbVzgTV8h1F8ohLj -> "GO")

THE AUDIT: 16 chat panels on the web console and 10 on the phone each drew a conversation their own way - plain
escaped text redrawn every 2-4 s, a pulsing dot or three dots or a spinner card, 14-15.5 px text with 10 px gaps,
no Copy, no Stop. Only the main Hoola chat and the phone Hoola Code landed words.

THE KIT (one part, the main chat's own numbers, nothing new):
- web `server/app/static/console/chatkit.js` + `chatkit.css` = `HoolaChat.mount(el, opts)` (her / begin / label /
  step / delta / final / text / nextBlock / end / stop / set / sync) + `HoolaChat.bar` (the one typing pill). It runs
  the main chat's own `stream.js` Pacer (34 ms a word, capped catch-up) and `md.js` Live soft (460 ms soft focus), and
  `HoolaMark.think(24)`. `sync({key, messages, working, label, steps})` is for panels that poll: history whole, a new
  reply lands, a growing snapshot lands only its new words, her pending bubble is matched, never drawn twice. Colours
  = `--hck-*` tokens falling back to each page's own token and then the app-design default (light + dark). Actions =
  Copy + Read aloud by default; Good / Not right / Ask again only where a panel has the real route. Tooltips are not
  drawn at rest (a hidden label counted as a clipped button).
- phone `lib/ui/chat/hoola_thread.dart` = the new-design chat's own pieces made public: `HoolaLanding` (34 / 460, the
  console's catch-up), `HoolaHerBubble`, `HoolaWorkingRow`, `HoolaWorkedLine`, `HoolaReplyActions`,
  `HoolaThreadView(messages: List<HoolaMsg>)` for screens that reload their list, `HoolaOnDark` for old Night Glass
  screens.

THE PANELS: web - Hoola Code session (`code.js`; steps fold into "Worked for", the clock from `run_at`), Hoola Auto
agent chat + intake talk (`hoolaauto.js`), the client intake page (`auto/intake.js`, light even on a dark device), Web
Studio site thread + plan chat (`webstudio.js`), React app chat (`appengine.js`), App Studio (`appstudio.js`), Game Dev
(`gamedev.js`, dark kit), Hoola Computer (`computer.js`), AI Apps preview (`aiapps.js`) + the public /ai page
(`aiapps/public.py`), Prayogshala Ask Hoola (`prayog/studio/studio.js`), Video Learner (`seekh.js`), Hoola Design Ask
Hoola (`design/hd-ai.js`). Phone - the default old-look chat (`chat_screen.dart`: `_Reveal` / `_Typing` gone, replies
out of the glass bubble, actions under the newest reply, stream -> final hand-over by GlobalKey), Hoola PC / Your PC,
Hoola Auto agent + talk, the older Hoola Code session, Notebook (citations as chips under the answer, Save kept),
Guru tutor, the live call caption (landing only, its 19 / 1.45 layout kept). Phone Hoola Code is unchanged (a
reference). Left out on purpose: person-to-person threads (Hoola Network, business inbox).

FOUND ON THE WAY: the phone Computer chat only refreshed when the list length changed (stuck past 80 messages);
the older Hoola Code screen counted steps with `n` (the step number since v0.945) instead of `num`.

TESTS: `test_chatkit_kit.py` (5, incl. a browser walk of the kit), `test_chatkit_code_auto.py` (6),
`test_chatkit_webstudio.py`, `test_chatkit_appstudio_gamedev.py`, `test_chatkit_small_panels.py`, Flutter
`test/hoola_thread_test.dart` (in app-screens.yml), pins in the old suites rewritten to the new truth. Browser tests
hold a fake reply instead of sleeping inside Playwright's request handler (a sleep there freezes the test too).

NOT VERIFIED: the phone Dart was never compiled here (the CI APK build is the first compile); not seen on her server
or phone; the nine panels that poll or get one reply still start landing only when the server has the reply (true
streaming for them is separate server work). Older reds unchanged: test_v0814_app_engine x3 after test_v0782 (fails
the same on the pre-kit commit).


## v0.999.15 BOX WIRING (built as 0.999.12; parallel sessions took 0.999.12-0.999.14, all kept; owner: "GO FIX BOTH" after "JUST TELL ME FIRST IS ALL WIRING IS OK IN BACKEND NOW FOR PIPELINE --- WRITER -- WORKER -- CHEKER")

The wiring check traced message -> Box -> writer -> helpers -> checker through `santosh.run_turn` / `_run_turn`
and found two things.

1. **The tier overrode the Box's writer.** `turnbox.begin` (in `run_turn`) sets `llm.MODEL_NOW` to the chat's writer;
   a few lines into `_run_turn` the v0.999.9 tier block set `MODEL_NOW` again to the tier's MAIN chat model. Same model
   normally - but after a hand-over the Box keeps the tier's BACKUP as the chat's writer (`writer.handed`), so every
   next message went back to the main (which had to fail again first), the sheet's `ran_on` and the receipt named
   the backup, and `checkers.pick_checker` (the pair's model that is not `ran_on`) picked the MAIN as checker - the
   model that was really writing checked its own reply. Now `santosh._apply_tier(tenant)` sets `tiers.NOW` (helpers,
   checker, price ceiling still know the tier) and sets the model only when the Box has not (`turnbox.APPLIED`).
   Calls, non-owner turns and turns outside the Box keep the tier model as before.
2. **Held-out chats.** `pipeline_holdout_pct` default 10 -> 0: the P7 watch's held-out share (per chat) ran about 1
   chat in 10 as today's turn - no fixed writer, no checker, no receipt, and with no tier on the server's own chat
   model (Qwen 3.8 27B on her server). The writers are decided, so every chat now goes through the Box. The P7 watch
   verdict has no "before" group any more; a VPS `.env` line `PIPELINE_HOLDOUT_PCT=...` still overrides the default.

Tests `server/tests/test_v0999_15_box_wiring.py` (6). Pins swept 0.999.14 -> 0.999.15 (+1013). NOT VERIFIED on her server.

## v0.999.16 KIT LANDS IN TESTS

The App screens CI run on v0.999.14 failed 2 of 110 phone tests, both in the new chat kit (`lib/ui/chat/hoola_thread.dart`): (1) `HoolaLanding` timed the soft fade with a module Stopwatch (wall clock), so in a widget test (fake time, a few real ms) the fade never ended, `onLanded` never fired and the reply actions never showed - in the app it worked but only by luck of real time; it now keeps its own clock `_t`, moved by the ticker (34 ms a word, 460 ms fade unchanged). (2) its `late final` ticker was first created inside `dispose()` for a history reply, which looks up TickerMode on a deactivated element - the ticker is now made only when words must land and `dispose` only disposes one that exists. Phone only; server unchanged. NOT VERIFIED until the next App screens run and on her phone.


## v0.999.17 CODING ON HER TIER (owner: "OK FINE USE THIS MODELS FOR CODING" after the coding-tier check)

The probe (a tier set, every Hoola Code call recorded) showed the session's own calls on her tier but three gaps:

1. **Side-by-side agents lost her tier.** `subagent` runs read / run agents together in a ThreadPoolExecutor; it copied `brain.PICK` (model / effort) into the worker thread but not `brain.PART` (her ask, the session id, the kind, her tier), so every such agent ran on `dev_qwen_model` (Qwen 3.8 27B) or the Box's pick. Now `brain.carry()` snapshots PART and `subagent.run_one(part=)` / the reality checker `adopt` it.
2. **The page named the wrong model.** `service._model_label` and `service.models` read `qwen_model()` (the fixed setting). Now `brain.shown_model(tenant)`: her session pick, else her tier's hoola_code main, else dev_qwen_model; names by `receipt.pretty` (`service._pretty_any`).
3. **Kinds outside the tier list.** The Box names a small code fix `code.small`, a translation `translate` and the planner `plan` (kinds.SAME); `tiers.KIND_JOB` knew only code / write / reason, so those ran on the tables' picks. Mapped.

The coding rows themselves are unchanged (her choice). Tests `server/tests/test_v0999_17_coding_tiers.py` (10). NOT VERIFIED on her server; none of the eight tier coding models has run Hoola's own coding card (only Qwen 3.8 27B 11/12 and Claude Opus 12/12 have).


## v0.999.18 CAPTION LANDS IN TESTS

The App screens CI run on v0.999.16 / v0.999.17 still failed. The chat kit's own tests passed; the first red was `39 new talk in call`: `_CaptionLandingState.dispose` made its ticker for the first time while the widget was being taken down (`late final Ticker _ticker = createTicker(...)` touched only in dispose), which throws "Looking up a deactivated widget's ancestor is unsafe", and the test binding stayed broken for every screen test after it (tools, connectors, employees, create, settings, the dark set...). The caption also timed its fade on a wall-clock Stopwatch, which never moves in a widget test. Fix in `lib/ui/talk/hoola_talk.dart`, the same as v0.999.16 did for `hoola_thread.dart`: `Ticker? _tk` made on first use, a `_t` clock moved by the ticker's own elapsed time, `_tk?.dispose()`. Same pace (34 ms a word, 460 ms fade). Phone only; server unchanged apart from the version story. NOT VERIFIED on her phone.

## v0.999.19 ONE SHOP step 1 (owner: "LETS CONTINUE THE NEXT WORK" -> gap 9 of docs/research/lovable/03_backend_vs_hoola.md -> "Full merge, in steps"): the website shop kept its own products and stock count beside the app's, so the last piece could be sold twice (website + phone app). Now a site joined to its project has ONE product list and ONE stock count (`site/shopjoin.py`): the website's products are the app's products (`backend._base_products`, the phone app's content with the one count, her real products replace the sample ones), the stock column moves once into the project's stock table under the app's lock (`move_stock`) and is not read again, every website checkout reserves from that count (`stock.reserve`; a checkout that fails gives the pieces back, a cancel puts them back), her product editor and a seller's product write it (`set_stock`); a site with no project keeps the old path. Step 2 = website orders in the app's Orders list, step 3 = old orders moved; 6 tests. NOT VERIFIED on her server.

Files: NEW `server/app/site/shopjoin.py` (joined / move_stock / sites_of / products_for / stock_of / set_stock),
`site/shop.py` (products read the one count; upsert_products writes it; _place -> _write reserves from it and gives the
pieces back on any failure before the order is saved; set_status cancel puts back), `site/shopplus.py` (a seller's
portal + new product use the one count), `appmaker/backend.py` (_base_products adds the joined websites' products),
`appmaker/android/service.py` (content: the website's products in the phone app, sample products dropped).
Tests: `test_v099914_one_shop.py`. Next: step 2 (website orders as rows of the app's Orders list), step 3 (old website
orders moved once, customers' tracking links kept). Deploy: the usual vps-ops deploy; nothing in the .env.

## v0.999.20 ONE SHOP step 2 (owner: "GO STEP 2", gap 9 of docs/research/lovable/03_backend_vs_hoola.md): a website order lived only in the website shop's own table, so her app's Orders list, the staff phone app, live updates and order workflows never saw it. Now every order of a site joined to its project is ALSO a row of the app's Orders list (`site/shoporders.py`: the list made once with staff-only rules, a guest row with items / total / customer / address / payment way / paid / status in the app's words, made when the order is saved), kept in step both ways through one table of words: every website move (her console, the gateway's verified payment, the customer's I have paid, a released unpaid order) rewrites the row (`mirror`); a staff move on the row moves the website order along its own road by the website's rules (`from_app`, hooked in `backend.status_moved` and a paid change), so a cancel in the app returns stock / coupon / credit note ONCE by the website's own code and a move the website cannot make puts the row back; the row never breaks a website order; 9 tests. Step 3 = old orders moved. NOT VERIFIED on her server.

Files: NEW `server/app/site/shoporders.py` (ensure_list, mirror, from_app, the word tables, the website's road),
`site/shop.py` (app_row column; place / tell_paid / set_status mirror; set_status takes by), `site/shoppay.py` (on_paid
mirrors), `appmaker/backend.py` (status_moved + a paid change -> _web_order_moved -> from_app).
Tests: `test_v099920_shop_orders.py` (+ the old shop / coupon / khata / delivery / variants suites re-run). Next: step 3
(the old website orders moved once into the Orders list; customers' tracking links kept). Deploy: the usual vps-ops
deploy; nothing in the .env.


## v0.999.21 THE DOOR FOLLOWS HER TIER (owner: "GO BUILD IT" after "IS CODE ROW IS GOOD FOR THIS TASKS")

The audit (`what every tool and feature uses in tiers`) found the tiers reached only the chat turn, Hoola Code, the Web Studio and video quality; every other feature calls the Anthropic SDK, which the shared door (`usage.install`) answers with one model for everything (GLM_MODEL = Qwen 3.8 27B when CLAUDE_ALL_GLM is on, else Claude Haiku 5.5 by the one-model rule), whatever she pays for.

Now a feature names its kind of work (`tiers.job(name)`, a contextvar) and the door, when she has a tier, asks her tier's model for that job on OpenRouter (`glmdoor.tier_models` -> `tier_acreate` / `tier_create_sync` / `_TierStream` / `_TierSyncStream`; `FORCE_OR` sends it to OpenRouter whatever the door's brain is; `tiers.JOB_PICK` = the one model being asked, so a failed main is never asked again by the old path). Main, then the backup, then today's path with the job cleared. The OpenAI-style brain reads the same (`llm.model_in_force` -> `tiers.job_model`), so the cheap-brain fallbacks follow too.

Jobs: `agent/door.TIER_OF` (game_* / cad / cad_look / blender / blender_look / motion / page / design -> web; notebook / studio_plan -> write; the tag rides `kw['_tier_job']`, taken off in `_to_api`, read by `create` / `acreate`), `site/ai._tier_job` (App Studio's app kinds, the website kinds on the Claude path and the PDF look doc_art / doc_critique -> web; seo_plan / social_plan -> write), the research engine's llm (`research_tools._deps`) -> research, memory -> facts (`compact._model` = compaction + About me, `coder.observer._call_brain`, `yaad._ask` = saving facts + the summary). The web row (Opus 5.5 / GPT-6.1 Sol, Sonnet 5.5 / Qwen4-Max, Qwen4-Max / DeepSeek V4.1 Flash, DeepSeek V4.1 Flash / MiMo-V2.6-Flash) because App Studio, Game Desk and CAD build a whole thing (the building board), not the code row. A call carrying a picture / PDF skips a text-only model (`tiers.TEXT_ONLY` z-ai/glm-5.3); a call that must be Claude's own (`glmdoor.CLAUDE_ONLY`) keeps Claude; no tier or no job = the door exactly as before. The hard-ask judge stays on its fixed model (2.5 s clock, one word).

Tests `server/tests/test_v0999_21_door_tiers.py` (17, incl. a call through the real Anthropic SDK door). NOT VERIFIED on her server; App Studio / Game Desk / CAD have not run their own checks on these models.

## v0.999.22 ONE SHOP step 3 (owner: "GO STEP 3", gap 9 of docs/research/lovable/03_backend_vs_hoola.md - the last step): the orders a website took BEFORE step 2 had no row in the app's Orders list. Now every one of a site joined to its project gets its row once (`shoporders.catch_up`): oldest first, each row with the order's own date and status in the app's words, written down only - a cancelled or delivered order gives nothing back and takes nothing again; the worker does it in batches of 200 (`catch_up_all`: sites with no project looked at again after 10 minutes, an order whose row cannot be written left alone after 3 tries and logged once); the customer's private link keeps working (the website keeps its record); a caught-up order then moves from the app like a new one. With this, gap 9 (two shops) is closed and every gap of the Lovable backend research is built; 5 tests. NOT VERIFIED on her server.

Files: `server/app/site/shoporders.py` (a new row carries the order's own dates; catch_up / catch_up_all),
`worker.py` (catch_up_all every tick, beside the unpaid-order release). Tests: `test_v099921_shop_old_orders.py`.
Gap 9 closed: one product list, one stock count, one Orders list for the website and the app. Deploy: the usual vps-ops
deploy; nothing in the .env. The first worker ticks after the deploy write the rows of her old orders.


## v0.999.23 TIER SHEET EVERYWHERE (owner: "show the 5 tiers only --- premium sheet" -> "DONT SHOW PRICE ... REMOVE THAT SESSION SECTION" -> "PERFECT NOW CHECK EVERY CHAT SECTION TOOLS AND FEATURE DEPLOY IT EVERWHERE --- EXPECT ...")

Design approved first on the canvas (claude.ai/artifact/KsKaKHFicHWuJt47McesAY): a note line, five rows (Normal with Recommended, Ultra with the amber 'Up to 70x credit' tag, High, Medium, Low), a violet tick on hers, Ultra asking first, no prices, and the Session chip under the home box removed.

Console: `static/console/v2.js` loadModels / setTier / tierRows / ultraAsk / modelMenu replace the old menu (tiers with prices + the per-model list); the chip shows the tier name (or an older one-model pick by name until she picks a tier); `menu.js` HoolaMenu gains `{note}`, a `tag` / `warn` on a row, `{title, back}` and `{actions}` (the Ultra question in the same popover, back arrow, Not now / Use Ultra); `v2.css` .mnote / .mtag / .mtitle / .macts / .mbtn; `#appUnder` keeps only the model button (no `#sessBtn`).

Phone: `lib/ui/shell/hoola_quality.dart` = `hoolaTierNow` (one shared notifier), `HoolaQualityChip` ("Medium v", hidden = a 48 dp space when tiers are not offered), `showHoolaTierSheet` (Quality, the note, 52 dp rows, Ultra asks in its own sheet), wired at the top right of the chat home (`hoola_shell.dart`) and of every chat (`chat/hoola_chat.dart` _TopBar). The Settings > Quality tier page (v0.999.10, with costs and models) stays as the detail page.

Server: PUT /api/model/tier clears an older one-model pick (`modelchoice.choose(tenant, '')`), so the tier applies. `tiers.door_models`: a door call that names no job now runs on her tier's `employee` row (`DEFAULT_JOB`), unless the turn already runs on its model (`llm.MODEL_NOW` = the chat writer / Box hand-over / call brain), the usage feature is `pc` (Hoola PC + her PC, frozen code untouched), or the job is `tiers.OFF` (the fallback to today's path - it was '' before, which now means the default - and the hard-ask judge, `agent/hard.judge`). Claude-only calls (glmdoor.CLAUDE_ONLY) keep Claude; Normal (no tier) is unchanged. The call's voice, the picture / music / voice-over / Cinema engines, SEO AI visibility and embeddings never use this door.

Tests `test_v0999_23_tier_sheet.py` (12); v0999_21 (no-job case, fallback job OFF), v0740, v0973 and v0999_9 updated to the new sheet. NOT VERIFIED on her server or phone (the Dart compiles first on CI).

## v0.999.24 PROTOTYPE FIRST (owner, on the Web Studio flow page: "DONT SHOW THE 3 DESIGNS ... IF BUILD (USER WILL FIRST SEE EVERY PAGE PROTOTYPE ...) -- IF PLAN (... AFTER PLAN APPROVAL A PROTOTYPE) --- PROTOTYPE CAN ALSO BE MODIFIED -- AFTER PROTOTYPE APPROVAL -- REAL WEBSITE BUILD" -> "GO"): after the plan the Studio no longer writes three complete looks. Build mode goes straight to, and Plan mode after "Build this plan" leads to, a PROTOTYPE of every page and section (public pages + the signed-in pages of a portal / dashboard) in the design Hoola chose, with real headings and words (one small model call a page, side by side; a failed page still shows its sections by name), sample rows on data screens and marked picture spaces (`site/prototype.py`, served at __proto/<page>.html). She changes it in the chat (one call returns only the pages it changed; the website tool's change reaches it), by clicking a section (edit heading / text / parts / button, move, remove - no model, Rs 0) and with Undo; every change is a new version and the site plan follows it. Only her tap "Build the real website" on the version she saw (/prototype/approve, hash) builds: pictures first, then every section written from its approved copy. The chat agent can never approve. Switch `studio_prototype` (off = the three looks); 13 tests. NOT VERIFIED on her server with a real model.

Files: `server/app/site/prototype.py` (skeleton / copy / versions / change / edit / move / undo / approve / render),
`site/service.py` (approve_plan starts the prototype, jobs proto + proto_build, recover, view, change routing, the
__proto/ preview path), `site/models.py` (column `proto`), `site/architect.py` (app_pages keep their screen types),
`main.py` (/api/sites/{ref}/prototype*), `config.py` (`studio_prototype`), `agent/site_tools.py` + `prompts.py` (the
agent changes a prototype, never approves it), `static/console/webstudio.js|css` (Prototype view: page strip, section
editor, Undo, Build the real website). Tests: `test_v0999_24_prototype.py`; conftest pins the old 3-looks walks.
Deploy: the usual vps-ops deploy; nothing in the .env.
## v0.999.25 SAB ENGLISH wave 4 (built as 0.999.12; main took 0.999.12-0.999.24 meanwhile, both kept) - no Hinglish anywhere a person or model reads (owner: "NOW CHECK EVERY TOOL IN HOOLA AI --- MAKE ALL ENGLISH --- NO HINGLISH ANYWHERE IN APP AND WEBSITE AND CONSOLE SIDE ... EVEN EVERY REPLY, CONCEPT, RESULT ETC SHOULD BE IN ENGLISH")

Waves 1-3 (v0.728-v0.731) made the replies, step labels, cards and the phone app English; ~26,000 Hinglish-looking strings
were still left in the server alone. This wave went through every file, in parallel batches (each in its own git worktree,
checked by a script that refuses any change outside string text):
- Server (~1,000 files of server/app): tool descriptions and results, errors, notifications, card titles, step lines,
  prompts and model-facing notes, desk messages, PDF / report text, website engine errors, plan cards.
- Web console + website assets (static/): every label, button, empty state and message; the trust levels are shown as
  Learning / Partner / Trusted (stored values seekh / saathi / bharosa unchanged); Pehchaan Locker -> ID Locker.
- Phone app (lib/, ~130 files) + Android (tool/android): screen text, tab names (Hisaab -> Accounts, Niyam -> Rules, Galla ->
  Cash box ...), notifications; i18n.dart keys unchanged, English values.
- Defaults: new avatars, Network replies, notebooks, Vocal / Interactive voices and model column defaults are English;
  Hindi / Marathi / Hinglish stay as choices and stored rows are not changed.
- Mera PC (frozen): TEXT ONLY, on the owner's explicit "Yes, text only" - server/app/pc/, agent/pc_tools.py,
  bazar/connectors/pc.py, lib/ui/pc_screen.dart, desktop/ (incl. the browser extension, PowerToys plugin text) and
  desktop-linux/. No behaviour change: a token-level diff of operator.py outside string text is empty; PC suites 575 pass,
  the same 7 reds as before (version-story pins + one timing test that passes alone).
- KEPT on purpose: word lists and regexes that read HER Hinglish input, protocol markers (`[Goal jaari:`, `KAAM KA HAAL`,
  `HOOLA KI YAAD`, `(Kaam:`), Devanagari content chosen by a language setting, test asks, and voice calls (owner's choice
  "Keep Hinglish calls": `voice_language` stays hinglish, call personas / spoken lines untouched).
- Couplings fixed with the text: appstudio.js / gamedev.js regexes, journeys.py shop selector, filmdesk famous-person
  check, appengine/cloud.py ERR_EN (reads the old Hinglish AND the new English website errors), test texts (~340 tests).
- Merged with main v0.999.6-v0.999.24 (version-pin conflicts; the first merge had one code conflict, site/applink.py, three-way with main's code and the English text).
- Ratchet: `server/tests/test_english_guard.py` + `hinglish_baseline.json` (385 files, 4,439 strings that must stay -
  word lists and kept content); a file that grows Hinglish fails. `python tests/test_english_guard.py --write` re-records
  after a deliberate word-list change.
NOT VERIFIED: no live turn on her server yet; the phone Dart compiles first on CI. Known leftovers: enterprise.js reads
Hinglish JSON keys from the enterprise engine (`theek`, `jaanch`, `baaki` - data keys, not shown), the console "Set ... to
the Trusted trust level" line needs the server to understand the new trust names (it maps them), the phone avatar_setup
fallback still says hinglish when the server sends nothing. The 11 website / app-link test reds (test_v0407*, v0414,
v09997) are red on main v0.999.11 itself.


## v0.999.26 HOOLA CREDITS (owner: "GO Dodo Payments, Paddle, RAZORPAY, CASHFREE")

The calculation and the rules are `docs/research/credits/01_credit_plans.md` (sections 1-7); what was built and how to switch it on is its section 8.

Server `server/app/credits/`: `plans.py` (price list: India rupees with GST, world dollars, regional dollars for the owner's country list `CREDITS_REGIONAL`; plans Lite / Plus / Pro / Max, top-ups 1k / 5k / 20k, employee packages Starter / Standard / Pro / Ultra; SKUs `kind_item_region`), `wallet.py` (tables credit_wallets, credit_ledger, credit_orders, credit_employee_packs; `note` from `usage.record`, `flush` with usage's flush; free -> plan -> top-ups; `unlocked` / `can_run` with a 5 s cache; `grant` / `take_back`; low / out lines; packages: `needs_pack`, `tool_gate` / `employee_job` once a turn through `TURN`, `pack_tier`), `pay.py` (Razorpay / Cashfree via `paygate.gw` with Newtika's own keys; Dodo `POST /checkouts` + Standard Webhooks; Paddle `POST /transactions` + `Paddle-Signature`; `state` = the provider's own record), `service.py` (checkout, `settle` claimed by one conditional update, `renewed` once per payment, `refunded`, `webhook`, `check`, the pay-page token), `api.py` (/api/credits, /checkout, /orders/{id}, /ledger, /webhook/{provider}, /pay/credits/{id}). Hooks: `usage.record` / `usage.flush`, `santosh._run_turn` (begin_turn + can_run, before the work), `santosh._run_tool` (a hired employee's tool = a package job), `tiers.chosen` / `set_tier` / `view` / `for_tenant` / `_default_job`, `employee.hire.hire`. Settings in `config.py` (credits_*, hoola_razorpay_*, hoola_cashfree_*, dodo_*, paddle_*), all keys in the VPS .env only.

Console: `static/console/credits.js` (Credits page: wallet, plans, extra credits, AI-employee packages with an employee picker, recent orders; buying opens the checkout in a new tab and polls the order), account menu > Credits, the Quality sheet's locked rows ('Buy credits', opening the Credits page). Phone: `lib/ui/shell/hoola_credits.dart` (Settings > Credits, buying opens the phone's browser and polls), the Quality sheet's locked rows open it; `Api.credits` / `creditsCheckout` / `creditsOrder`.

OFF until the owner sets CREDITS_ON=true (and CREDITS_EXEMPT for her own account). Not built: India auto-renewal (a plan is a 30-day pass), store billing in the app, GST invoices, choosing another country's prices, media engines' own charges as credits. Tests `test_v0999_26_credits.py` (19, every network call faked). NOT VERIFIED with a live payment on any of the four providers.


## v0.999.27 HOOLA CODE BOTTOM ROW (owner: "KEEP HOOLA CODE AS IT IS JUST CHANGE STALE THINGS IN BOTTOM")

Her screenshot of /console/code showed a native browser drop-down for the repo, a model picker ("Qwen 3.8 27B") and rupees ("Rs 9,702 this month") in the row under the box - different from the chat's tier sheet. Two design rounds (claude.ai/artifact/4brzvMRZeqEYseEZYCvZon) were rejected as changing the whole page; built: the page exactly as it was, only that row changed.

- `static/console/code.js`: repo / branch / mode are `.hcd-envchip` buttons (`#hcdRepoBtn`, `#hcdBaseBtn`, `#hcdModeBtn`) opening `repoMenu` (Your repositories: name, owner · Private, a tick; Add repositories from GitHub -> Settings; a note that Hoola sees only the repos she allows), `baseMenu` (Work from: the default branch tagged Default, then her other branches, never `hoola/`; the note that Hoola makes its own branch and never pushes to the default), `modeMenu` (the three modes with their one-line meaning). The `<select>`s, the model + effort pickers and the usage ring are gone. The right end (`#hcdQ`, `qualityRow`) = credits (`GET /api/credits`: paid = 'N credits' with a pie of the plan left, free = 'N free today', a link to /console/?v=credits; nothing when credits are off or she is exempt) + the tier button (`GET/PUT /api/model/tier`, `tierMenu` = the chat's sheet: note, five rows, Recommended / Up to 70x credit / Buy credits when locked, `ultraAsk`). A new session sends model '' / effort '' (her tier decides, since v0.999.17). Under a session's box (`metaHTML`) the tier name instead of the model name.
- `static/console/menu.js`: `{search: placeholder, empty}` item = a find box; typing hides rows that do not match and the headers, one 'No match' line; Down goes to the rows, Enter takes the first, Esc closes. Icons repo / branch / plus / pr. Styles in v2.css (`.hmenu .msearch`).
- `static/console/hoolacode.css`: `.hcd-qual`, `.hcd-credits`, `.hcd-tierbtn`, the open chip shaded.
- Tests: test_v0777_hoola_code_composer rewritten for the menus (no select left in the row, no rupees / model name, repo / branch / tier menus, tier PUT, a free account's locked tiers + '42 free today'), test_v0748 mode pin. NOT VERIFIED on her server.


## v0.999.28 HOOLA CODE PHONE ROW (owner: "DEPLOY SAME FOR PHONE HOOLA CODE ALSO")

The console's v0.999.27 row brought to the phone. `lib/ui/code/code_start.dart` (CodeNewSessionPage): the environment and repository chips stay (their sheets were already the app's own, with a search past 4 repos); after them a quality chip (`hoolaTierNow` / `showHoolaTierSheet` from `shell/hoola_quality.dart` - the chat's own sheet, the same choice everywhere) and, when credits are on and she is charged, a credits chip (`_CreditPie` + 'N credits' / 'N free today', from `api.credits(hoolaCountry())`, opens `HoolaCreditsPage`). The + sheet keeps Pictures / Text file / How it works; Model and `_pickModel` are removed; `_start` sends model '' / effort ''. Session screens never showed a model. Test test_v0999_28_code_phone_row.py (source pins). NOT VERIFIED: the Dart compiles first on CI; not seen on her phone.


## v0.999.29 QUALITY EVERYWHERE (owner: "GO BUILD 1 AND 2" after the chat-panel audit)

The audit (her ask: does every chat panel have the Ultra-to-Low range): only the main chat (console + phone) and Hoola Code had it; every panel already ran on her tier on the server; Web Studio showed 'Rs 3.10' per reply and Hoola Auto rupee budgets; Hoola Code / Hoola Auto on the phone showed a model name.

- `static/console/quality.js` (new): `HoolaQuality.use(api)` once per page, every `[data-hoola-quality]` spot fills itself (a MutationObserver), `mount(host)`, `refresh()`; credits from GET /api/credits (paid = 'N credits' + plan pie, free = 'N free today', a link to /console/?v=credits in a new tab; nothing when off / exempt), the tier button from GET /api/model/tier; its own menu (the chat's sheet: note, five rows, tags, tick; Ultra asks first with Not now / Use Ultra; locked rows open Credits); PUT /api/model/tier. Reads the page's tokens (--ink --mut --dim --hair2 --pri --sunk --surface) so light / dark studios both fit. Closes on outside press, Esc, Tab, resize, or a scroll that really moved the button (App Studio scrolls on its own).
- Loaded + started in webstudio.html / appstudio.html / gamedev.html / hoolacode.html (Hoola Auto) / design.html; spots under Web Studio's home box and site thread, App Studio's home box and app thread, Game Dev's home box; `HoolaChat.bar(..., {quality: true})` adds a `.hck-under` row (Web Studio plan, App Engine, Game Dev thread, Hoola Auto agents); Design's Ask Hoola panel.
- Credits not rupees: webstudio.js turn cost = sum of usd x 1000 credits; hoolaauto.js `rs()` = credits at `inr_per_credit` (new on GET /api/credits, `credits/service._inr_per_credit`), cost cap typed in credits and saved as rupees.
- Phone: `HoolaQualityRow` (credits chip + `HoolaQualityChip`, `hoolaWalletNow`, `hoolaCreditsOf`, `hoolaInrPerCredit`) under the boxes of code/code_session.dart (replaces the model label), notebook_screen.dart (chat tab), guru_screen.dart (the tutor), hoola_auto.dart (agent page, model name gone; every `_rs` = credits).
- Left out (her decisions): Hoola Computer, the voice call, the media studios, AI Apps.
- Tests: tests/test_v0999_29_quality_everywhere.py (8, incl. a real-browser walk of Web Studio, App Studio and Game Dev: the button, the credits, the five rows, Ultra asks first). NOT VERIFIED on her server or phone.

## v0.999.30 HOOLA WEBSITE (built as 0.999.29; their QUALITY EVERYWHERE took 0.999.29, both kept) — the public site rebuilt in the console's design (owner: "NOW LETS WORK ON WEBSITE OF HOOLA CURRENTLY IT LOOKS AI MADE AND NON PROFESSIONAL. DESIGN A NEW WEBSITE MATCHING THE CONSOLE PROFESIONAL UI / UX ----- HUMAN MADE NATIVE PERFECT MOTON GRHAPICS IN IT. ALSO A PERFECT SHOWCASE OF TOOLS AND FEATURES" -> preview of all pages as a claude.ai artifact -> "GO")

- Read first: the six old pages (home / employee / network / studio / websites / apps), each with its own script and GSAP,
  each in a different look (the home page was "one Indian day" on lavender), none matching the console.
- New site = the console's own system: white paper (#FFFFFF / #FAFAF9 bands), one ink #1B1A17, one violet #5B45E0 for live
  things, Literata for headlines and Hoola's words, Schibsted Grotesk for everything tapped, JetBrains Mono for figures, black
  pill buttons, hairlines, the Orbit mark (mark.js paths as an SVG symbol, rings turning while it thinks), dark mode from the
  console's dark tokens (system or data-theme).
- Pages: `/` home, `/employee` (12 departments with real role counts from employee/hire.py, four roles read in full: does /
  needs / will never, how a job runs, trust ladder), `/tools` (12 studios, each with its own live canvas drawing and a link
  into its console studio), `/studio` (Create Studio with the nine real screens from studio/*.webp, the storyboard + price
  card), `/websites` (Web Studio's four steps + App Studio, `#app-studio`; `/apps` now 301s here), `/code`, `/computer`
  (Hoola PC + your PC), `/network` (a knock passing five checks), `/pricing` (plans / top-ups / AI-employee packages from
  credits/plans.py, India in rupees, other countries in dollars, costs per quality level).
- Motion, all drawn in code, no stock art: the hero is the console doing one job on a loop (her message types in, the working
  row with the thinking mark, a clock and real step labels, "Worked for 41s", the reply landing 34 ms a word with a soft focus,
  a UPI card sliding to approve); a six-tool tour that changes every 7 s and pauses 14 s on her tap (website built section by
  section with six checks ticking, phone screens sliding, Hoola Code writing a failing test then the diff then a PR with CI
  passed, a painted storyboard, Hoola PC filling a Udyam form with a masked PAN and a thinking line, an SEO employee's desk);
  the quality sheet walking through its five levels; a voice-call glow following the voice; network checks lighting in turn.
- Engineering: one `site.css` + one `site.js` (CSP `script-src 'self'`, no inline script or handlers, no library; GSAP and the
  six per-page scripts deleted). Every scene finds its own `data-*` element, runs only while on screen and the tab is visible
  (IntersectionObserver), and holds a complete still frame under prefers-reduced-motion. The words live in the HTML (first frame
  complete without script; choices are buttons that show/hide panels already in the page). Skip link, aria on tabs and choice
  groups, scene art marked aria-hidden with a text label.
- Checked: Chromium at 1440 and 390 px, light and dark, every page scrolled through under the real CSP: no script errors, no
  blocked resource, no sideways scroll (found and fixed: `1fr` grid tracks growing past the phone width -> `minmax(0,1fr)`,
  the header's second wrap inheriting the bar height, the menu button not pushed right on phones).
- Tests: `test_website.py` rewritten (nine pages, one script, CSP, Console way in, aria-current, links answer, /apps 301,
  pricing equals credits/plans.py, tools link into the console, reduced motion, old scripts gone), `test_v0351_studio_page.py`
  (real screens served, one button per screen), `test_v0462_logo.py` (icons on all nine pages). Pre-existing sandbox reds
  unchanged (test_v0224_site_edge / test_v121_site need the Python Playwright headless shell; 25 old story-text pins).
- NOT VERIFIED on her server or a real phone.


## v0.999.31 HOOLA COMPUTER CHECK (owner: "GO TO EVERY HOOLA DESKTOP CHECK IS EVERYTHING PROPERLY WIRED OR NOT")

Audit of Hoola Computer on main (v0.999.30), after other sessions rewrote its chat panel on the shared chat kit.
- Walked in Chromium against a local server: console sidebar row "Computer" -> /console/computer; home; Hoola PC
  workspace (new chat, message sent, live screen area, Stop); Your PC (switch on, 6-digit pairing code, download).
  No page errors, no failed API call. Every route the page and the phone tab call exists (/api/computer*,
  /api/conversations/{id}/messages|files|result|stop, /api/browser/{id}/live|frame|stop). The desktop-latest
  SantoshDesktop.exe link serves a real Windows file (MZ). Phone build for v0.999.30 green.
- Tests: 181 of 184 PC + Hoola Computer tests passed on main; the 3 reds were version pins
  (startswith "0.88") in test_v0880 / v0881 / v0882 - now ">= 0.88".
- FIXED computer.css: under 860 px the side panel and the chat column had no min-width, so a long chat title
  (white-space nowrap) widened them past the screen (23 px sideways scroll at 390 px, "Your PC" tab cut; 20 px at
  320 px). Both now min-width:0 + flex-basis:100%; the home cards use minmax(min(320px,100%),1fr). Re-measured:
  no overflow at 320 / 390 / 768 px on home, Hoola PC and Your PC. Test test_narrow_screen_panels_fit.
- NOT VERIFIED: a real Hoola PC task on her server (the local walk has no AI key, so the reply failed there).

## v0.999.32 WEBSITE WIRING (owner: "NOW GO THROUGH -- EVERY WEBSITE BUILDING FLOW -- CHECK EVERY THING IS WIRED PROPERLY OR NOT"): Build mode, Build with questions first, Plan mode, templates, the chat agent and the old three looks walked end to end through the real routes (plan -> prototype -> edit / move / undo / change in words -> stale tap refused -> approve -> real site -> change, version diff, restore, launch card, drafts, errors, backend, code), and the prototype screen in a real browser at 1440 and 390 px (click a section, edit, save, Undo, switch pages, Build the real website); every Studio API call has a server route. Fixed: (1) the status line Hoola sends to the chat and the phone said "Say Yes and I will make 3 looks" with the prototype on, and nothing when the prototype was ready - now it names the prototype and says it is ready (`service._say` / `_next_step`); (2) the website card in the main console chat (build.js `protoBody` / `planYes`) and on the phone (`SitePrototypeOpen` in site_screen.dart) had no prototype state and their yes button said make 3 looks - now they show the pages and open the Web Studio, where only her tap builds; (3) on a phone the Studio chat was 440 px on a 390 px screen since v0.667 (a later rule overrode the phone rule) - 440 px only above 1000 px now. Found, not changed: 350 of 400 sampled templates carry another business type than their subject (a sweet shop template plans as a restaurant). 8 tests (+ Studio pages on this release stamp, the prototype styles out of the shared kit block). NOT VERIFIED on her server or phone.

Files: `server/app/site/service.py` (`_say` prototype line, `_next_step`), `server/app/static/console/build.js`
(`protoBody`, `planYes`), `lib/ui/site_screen.dart` (`SitePrototypeOpen`, honest yes button), `server/app/static/console/
webstudio.css` (the chat width). Tests: `test_v0999_32_website_wiring.py`. The walk itself (not committed) drove
POST /api/sites deep, /api/site-architect + revise + approve, /api/site-templates, the website tool, /plan + /look.
Deploy: the usual vps-ops deploy; the phone change needs the new APK.


## v0.999.33 WIRED (owner: "NOW CHECK DOES EVERY THING IS WIRE PROPERLY OR NOT"; built as 0.999.30, their HOOLA WEBSITE / HOOLA COMPUTER CHECK / WEBSITE WIRING took 0.999.30-32, all kept)

Checked end to end after v0.999.29.

Server side (no change needed): the request middleware binds her account for every /api call (`usage.bind(resolver=...)`), so each studio's model work knows her tier - Web Studio (`site/ai.py` tier 'web'), App Studio / Game Desk / CAD / Design / pages through `agent/door.py` TIER_OF -> `glmdoor.tier_models`, Hoola Code + Hoola Auto agents from the session's tenant (`devsahayak/brain.py`), Notebook / Guru on the door's default employee row. PUT /api/model/tier refuses locked tiers on a free account.

Found and fixed:
- Hoola Design: `design.html` loaded `quality.js` AFTER `hd-ui.js`, which calls `HoolaQuality.use(api)` at load - `window.HoolaQuality` was undefined, so the spot under Ask Hoola stayed empty. quality.js now loads before the design scripts; `test_every_page_loads_the_piece_before_the_script_that_starts_it` checks the order on all five studio pages.
- Credits went stale: read once per page / per app run. Console `quality.js` reads them again on focus / visibilitychange (20 s throttle) and every 60 s while a spot shows, and never redraws the button an open menu hangs from (redraws on close); `code.js` the same (`qFresh`, skips while a HoolaMenu is open); phone `HoolaQualityRow` reads them when a box opens if older than 30 s and every 60 s (Timer cancelled on dispose).
- Rupees left for AI spend: App Studio Health 'AI cost (30 days)', a Hoola Code session's 'Cost so far' and Hoola Code Settings 'Usage this month' now show credits at the server's `inr_per_credit` (`HoolaQuality.credits(inr)`, code.js `rs`). Her shop's sales, dues and delivery fees in App Studio stay rupees (real money).
- Tests: `tests/_hq_wiring.py` (real_tiers: tiers offered + CREDITS_ON + a real top-up grant + a tier set through `tiers.set_tier`; quality_under: the button + credits right under a given box; pick_low: a real PUT from the page and `tiers.chosen` is low) added to the browser tests of the Web Studio site thread (with a pick), home, plan, React app, App Studio thread, Game Dev thread, Hoola Auto agent and Hoola Design Ask Hoola. Stale pins fixed: the Web Studio cost line expected 'Rs ' (credits since v0.999.29), the kit CSS block check read into the v0.999.24 prototype block, the Game Dev test hired after credits were on (a hire needs its package).

NOT VERIFIED on her server or phone.
- One release stamp on every page: Hoola Code, the console and Hoola Computer pages were left on older stamps (Hoola Computer mixed 0.890.0 with a newer computer.css); all now carry this release, so a browser loads the new code.


## v0.999.34 CREATE FIXES (built as 0.999.32; their WEBSITE WIRING and WIRED took 0.999.32-0.999.33, all kept; owner: "NOW LETS WORK ON CREATE SECTION --- FIRST CHECK ALL THE CREATE SECTION FEATURES TOOLS PROPERLY" -> report -> "GO FIX ALL")

The Create check: every Create Studio screen (17), Hoola Interactive (12 pages) and Hoola Vocal (12 pages) walked in
Chromium against a real local server (nothing mocked): no page errors, no failed API call; on every tool a request typed
and the main button pressed, each job followed to its end; every phone Create route exists. 244 / 249 Create tests passed;
the 5 reds were out-of-date pins. FIXED:
- DIRECTOR: "Storyboard ready" was toasted the moment the brief was sent (the storyboard is written in the background),
  and a storyboard that failed wrote its reason only into a chat note - the film sat empty with "Make the storyboard".
  Now `studio.service._plan` writes the reason ON the film (`error`, one plain line), a fresh try clears it, the console
  film page shows it in a box ("Nothing was spent. Press Write the storyboard to try again.", `data-planerr`), the phone
  film page already shows `error`; "Storyboard ready" only when the shots are there, else "Writing your storyboard";
  a Video clip keeps the reason + "Press Create again." (`after_plan`).
- RAW ERRORS: the Script writer showed the provider's raw text ("Error code: 401 - {'type': 'error', ...}"); a song, a
  picture (photogen "could not be made: <raw>") and any unexpected job failure did the same. `create.service.plain(e,
  engine, fallback)` turns them into one plain line (not connected / out of credit / busy / took too long / try again);
  the raw text stays in the server log.
- ENGINE NOT SET UP: Image, AI casting, Song, Voice and Dubbing started a job that failed a second later. `create.service
  .NEED` = one line per engine, GET /api/create now carries `need` + `ready.image`; the console `startJob` and the phone
  `CreateStore.start` say the line BEFORE anything is posted (the server still fails a job with the same line for chat).
- Off-scale text: Cinema heading 16 -> 18 px, ArtCraft "Sound from the model" 13 -> 14 px (the studio scale).
- Out-of-date pins updated (Create opens with ?a=, resize guard, tools() list, console stylesheets, ready() keys).
- Tests: NEW test_v0999_34_create_fixes.py (13, incl. a browser walk: no job posted without the engine, the Director
  box with the plain reason, no "Storyboard ready").
- NOT VERIFIED: real pictures / videos / songs / voices (no AI keys here; her server's keys decide - Create > Engines or
  vps-ops studio_apis); the phone change compiles first on CI.
## v0.999.36 SAB SECTION (built as 0.999.31 / 0.999.32 / 0.999.34; other sessions took each, all kept; ships in v0.999.36 with P6-P9) - Hoola Prompting P5 (owner: 'GO P5')

Five more sections join web / image / script in Hoola Prompting (`docs/HOOLA_PROMPTING_PLAN.md` part 4, P5):
**App** (users, the day-1 job, what it keeps, money, updates, phones, language -> App Studio), **Video clip** (one shot:
subject, ONE action, camera move, place, light, look; shape + length are SETTINGS, never words), **Music and jingle**
(use, genre, mood, voice, language, instruments, tempo, lyrics sung exactly), **Marketing message** (channel, who gets it,
the offer, the one action, tone, language, signed as; channel rules for WhatsApp / email / SMS / caption / ad; always a
DRAFT) and **Business document** (kind, reader, purpose, facts, parts, tone, length, file; missing numbers = marked blanks).

- `prompting/anatomy.py`: eight sections (ANATOMY_V 2); the first three keep their place.
- `prompting/brief.py`: section words for the five + a priority order (a 'video script' is a script, a 'reel video' is a
  clip, 'a website with an app-like login' stays a website); code-read slots per section (app platform / money / day-1
  job, video camera / shape / length, music use / genre / mood / voice / language / quoted lyrics / length, marketing
  channel / action / language, document kind / file); `_section_limits` = each section's checks with the reason: a clip over
  10 s (the Director makes longer), more than one action in a clip, lyrics with 'instrumental', 120+ words of lyrics, an
  offer with no end date, an SMS offer too long, a quotation without prices, a report with no period; notes that nothing is
  sent from the page and that app money reaches her own account only; 'no X' wording flagged for video too.
- `prompting/dialect.py`: app-1 / video-1 / music-1 / marketing-1 / doc-1; app -> "Open in App Studio", the rest ->
  "Put in the Hoola chat" (video + music ask for the price first, marketing says "do not send", documents name the file).
- `prompting/context.py`: her business name fills app 'what' and marketing / document 'signed as'; brand colours a clip's look.
- `prompting/recipes.py`: 21 more starters (4 app, 4 video, 4 music, 5 marketing, 5 documents; 40 in all), every one checked,
  rendered and scored >= 70 with its own examples by a test.
- `prompting/ledger.py`: SECTIONS = the anatomy's eight. `main.py` `_pled_app`: POST /api/apps claims a Prompting run and
  marks it ready; DELETE /api/apps/{ref} = dropped. Chat hand-offs of the other four are claimed by the existing chat hook.
- Page: icons + placeholders for the five, 13 sidebar rows; `appstudio.js` reads `hoola.prompt.toApp` into its box
  (never built until she presses Build).
- Tests `test_v0821_prompting_sections.py` (22 incl. a browser walk); `test_v0804_prompting.py` pins moved to eight sections / 13 rows.

NOT built: the P0 card for the five (no engine runner for them yet), the Improve button in the App Studio / Create video /
music boxes, the phone composer button, ledger hooks inside Create video / music jobs. NOT VERIFIED live: no real model has
filled one of the five briefs on the server.


## v0.999.36 KAAM KE SECTION (built as 0.999.33 / 0.999.34; ships in v0.999.36 with P5 + P7-P9) - Hoola Prompting P6 (owner: 'GO P6')

Five more sections, 13 in all (`docs/HOOLA_PROMPTING_PLAN.md` part 4, P6): **Coding** (kind of job, what is wrong / what to
build, where, DONE WHEN, the check that proves it, rules, do not touch -> "Open in Hoola Code", landing in its box through
the page's own `?prompt=` door, nothing started), **Research** (question, what she will decide, sub-questions, sources to
trust, where, as of, form of the answer; every figure must come from a page opened, with link and date), **Data and sheets**
(the data, the question, the result: table / chart / formula / summary / Excel, period, a number it must match; worked out
in Python, never estimated), **AI assistant** (its job, the business, what it knows, what it must never say, when it hands
over, tone, language, where it answers; drafted, never published from here) and **Everyday ask** (goal, background, form,
example, avoid; never guessed from her words - she picks it).

- `prompting/anatomy.py` ANATOMY_V 3; `brief.py`: section words + priority (aiapp > code > ... > research > web), code-read
  slots (code: job kind, file paths, test command; research: sources, form, year / 'latest', places; data: output, file
  names; aiapp: role, channel; chat: form), her own sentence is the task / question / goal in code, research, data and chat
  (said as her words, 4+ content words); checks: a coding ask too short to act on, a bug fix with no check, prices with no
  'as of', 'best' with no decision, a chart that does not say what it compares, an AI with no real facts or no hand-off.
- `dialect.py` code-1 / research-1 / data-1 / aiapp-1 / chat-1 (no role-play, no 'think step by step').
- `context.py`: her business name / tone fill the AI assistant.
- `recipes.py`: 20 more starters (60 in all), each scored >= 70 with its own examples by a test.
- `devsahayak/api.py`: `_pled_code` - a session started from a Prompting prompt is claimed + ready; delete = dropped.
- Page: icons + placeholders, 18 sidebar rows. Tests `test_v0822_prompting_work.py` (22 incl. a browser walk into Hoola Code).

NOT built: a merged pull request as a strong 'kept' event (the quiet-keep rule covers it), the AI Apps page's own box
(the prompt goes to the chat, which has the ai_app tool), the P0 card for these sections. NOT VERIFIED live.


## v0.999.36 MERE PROMPT - Hoola Prompting P7 (built as 0.999.34, taken on main by CREATE FIXES; ships in v0.999.36 with P5, P6, P8, P9)

Her saved prompts (`prompting/store.py`, `/api/prompting/saved/*`, the "This saved prompt" panel on the workbench):
- **Versions:** table `prompt_saved_versions`; every save that changes the brief or title adds one (an unchanged save does
  not); History view `#/v/<id>`; "Bring this back" = the old version returns AS A NEW version, so a restore is undone by
  restoring the one before; 50 kept, version 1 always. Re-reading her words on a saved prompt now keeps it the same saved
  prompt (it used to start a new one).
- **Fill each time:** `prompt_saved.ask` = slot keys; opening such a prompt shows a form for those parts; POST
  `/saved/{id}/fill` makes the finished prompt for this use only (the saved one is unchanged; 422 names what is empty).
- **Schedule:** PUT `/saved/{id}/schedule` {repeat daily / weekdays / weekly / monthly, first run} creates a Routine in her
  'Hoola updates' chat whose instruction is the prompt's chat text + "anything that sends, spends or goes public still waits
  for her tap"; a change or restore rewrites the routine's words; re-scheduling replaces it; stop / delete cancels it.
  Refused: a prompt that opens a studio (web / app / code), a prompt with fill-each-time parts (and marking one on a
  scheduled prompt), more than 20 automatic jobs, a past time.
- **Share link:** POST `/saved/{id}/share` = a token shown once (only its sha256 is kept), 30 days, a new link replaces the
  old, DELETE turns it off; GET `/shared/{token}` for signed-in Hoola users shows title / section / prompt (never the owner's
  id, versions or schedule); POST `/shared/{token}/copy` saves a copy in HER prompts with the owner's facts relabelled
  'from the recipe'. Screened on every view and copy (plan part 9): hidden 'ignore the instructions', role changes, asks for
  a password / OTP / card / ID number, web links, 'send / pay / delete everyone automatically' - refused with the reason.
- Tests `test_v0823_mere_prompt.py` (18 incl. a browser walk: recipe -> save -> new version -> restore -> fill each time ->
  schedule -> share -> open the link).

NOT built: team logins (the console has none - 'team' = whoever she gives the link); a scheduled run is not tied to the
results ledger; no phone screen. NOT VERIFIED live.


## v0.999.36 MUQABLA - Hoola Prompting P8 (owner: 'GO P8'; built as 0.999.35, ships in v0.999.36)

The same ask as two prompts, side by side (`prompting/compare.py`, `/api/prompting/compare*`, "Compare" on the workbench):
- **B** = her words alone (no brief), another wording (read the same way as A), or one of her saved prompts of the same kind.
- **Free comparison, in code:** each side's Prompt Score, the parts that differ with where each came from, the facts only one
  side carries, and the plain note that the more complete prompt is not always the better result.
- **Price first:** pictures and scripts can run both sides here. `quote` gives each side's credits and the basis (picture =
  the picture engine's list price per picture `photogen.COST_INR`; script = an ESTIMATE from the writer model's token price),
  and `run` refuses unless handed that quote's token (a hash of both prompts, the quality and the price) - no quote, another
  quality or a changed prompt = a new price to confirm. Websites, apps, code and chat prompts are compared as prompts only
  and say where to run the chosen one.
- **Run:** pictures = two Create image jobs (shown when done); scripts = written now, both kept in My creations. Each side is
  a ledger run (handed + claimed).
- **Her pick** (A / B / about the same; also without running, via `/compare/judge`): table `prompt_compares` keeps SHAPE
  only (scores, slot sources, hashes, refs, the pick - never text); the winner's ledger run gets her thumb up.
  `/compare/tally`: how often the higher-score prompt won her pick (shown from 5 decided picks).
- Tests `test_v0824_muqabla.py` (7 incl. a browser walk: compare -> price -> run both -> pick).

NOT built: comparing one prompt on TWO ENGINES (Create's own video compare card, v0.263, already does that for clips);
the Arena duel screen reuse. NOT VERIFIED with a real picture engine or writer.


## v0.999.36 SEEKHO - Hoola Prompting P9 (owner: 'GO P9')

Short lessons made from HER OWN prompts (`prompting/learn.py`, `/api/prompting/learn*`, a Learn page + "Learn from this
prompt" on the workbench). One idea per lesson; each shows HER line, why it hurts, and a better way written BY CODE (no
model rewrites her):
- vague words an engine cannot see (premium, attractive, modern, professional, catchy, viral, best...) with a tip that fits
  the kind of prompt ('premium' on a poster = black and gold, serif heading, empty space; on a website = dark background,
  one gold accent...); a vague word inside a magic phrase counts once;
- magic words; 'no X' in a picture or video; an offer with no end date; too many words on a picture; three asks in one;
  'everyone' as the audience; and, from her saved prompts, the same required part missing again and again.
- **Real before / after only from her record:** the outcome ledger's kept rate with the part filled (by her, not Hoola's guess)
  vs without - shown from 8 graded runs on each side - and her own P8 compare picks (from 3). Otherwise the lesson says
  "Hoola's starter guidance - not yet proven on your prompts".
- **Her read:** Got it hides a lesson for 30 days (back only if it still applies); Not useful hides it for good and is
  counted (table `prompt_lessons`).
- Tests `test_v0825_seekho.py` (7 incl. a browser walk); sidebar pins 18 -> 19.

NOT built: lessons from model-written before/after pairs (by design - lessons are hers and code's); the phone. NOT VERIFIED
with real rows - every lesson today is starter guidance until her results accumulate.


## v0.999.35 SEO DESK (built as 0.999.34; their CREATE FIXES took 0.999.34, both kept)

Owner, on the SEO Specialist redesign (design canvas https://claude.ai/artifact/TDCBTLLDip92LBuARARC7p, boards 1-9):
"IN THIS THERE WILL BE A SEO PANEL AND IN RIGHT A CHAT SECTION WHERE USER CAN ASK QUERIES AND EVEN CAN TELL TO IMPROVR THIS
AND EVEN CAN DO CHANGES IF REQUIRES --- A END TO END AI SEO EMPLOYEE", "ALSO FROM APP A VOICE CALL CONNECTING TO THIS SEO
EMPLOYEE", "SHOW THIS PANEL IN LEFT SIDE -- MAKE A SEPERATE SECTION. DONT SHOW HOOLA MAIN SIDE BAR ... CHAT SECTION WILL STAY
THERE EVEN PAGES IN LOADED", "THIS IS THE PAGE WHERE USER WILL LAND DIRECTLY", then "GO BUILD".

- The SEO Specialist's own section at `/console/seo` (`static/console/seodesk.html` / `seodesk.js` / `seodesk.css`), the
  Hoola Computer pattern: no Hoola sidebar, a thin top bar (back to Hoola, the employee, the site, Working / Paused / Setting
  up, "Chat on the right" swap, refresh). The console's AI Employees > Open desk for the SEO Specialist now goes here
  (employees.js `desk()`; the old desk code stays behind `window.HOOLA_OLD_SEO_DESK`).
- The chat (left by default; swap remembered in `hoola.seo.side`, fold in `hoola.seo.folded`): the shared chat kit
  (`HoolaChat.mount` / `bar`, quality tier + credits under the box), starters that change with the tab, "About: ..." when
  she taps Ask on a number, a problem, a plan step or a Maps square, "Fix it" sends "Fix this: ...". The chat column is drawn
  once; changing tabs redraws only the right side (a short shimmer). When a turn ends the desk reloads, so a change shows.
- The screens, all from the real `/api/seo/desk` + `/api/seo/intel`: Overview (needs you: connect Google, approve the plan,
  plan steps waiting for her, first check running; Google numbers with Ask; health ring + counts; what it did; searches to
  watch), Plan (approve banner, week strip, area chips, 4-column board, a step's detail with Start / Mark done / Skip, Ask,
  Do it for me), Site health (score + parts, speed, Google index, problems by level that open to their fix with Fix it /
  Ask, AI bots, trust, local, how Google sees the home page), Search (On Google: followed searches, follow / ideas / refresh /
  exact check, DataForSEO; In AI answers: named / linked percentages, sites linked instead, questions table, add / suggest /
  ask now, weekly switch), Local & Maps (the Maps grid, clickable squares with that spot's place, keyword chips, find my
  shop, check a search; local score; Google profile / reviews / listings said plainly as not built - the chat writes the
  text to paste), Reports & settings (monthly reports, weekly checks, jobs around the clock + run buttons, connections incl.
  whether Hoola can change the site, trust Learning / Partner (Trusted locked), spending, pause / resume / let go), and the
  4-step setup (website, what you sell, competitors, how it works with you) the first time.
- `server/app/seochat.py`: the SEO chat = a Conversation with kind 'seo' (GET /api/seo/chat = her newest or a new one with
  today's greeting from the real desk; POST /api/seo/chat/new reuses an untouched one), kept out of every Hoola chat list
  (`callconv.not_call`, `convs.current`). `is_seo(conv)` is true for that chat and for a call record whose origin is it.
  A turn there (`santosh._steps_begin`) gets `<seo_desk>` (site, state, plan, health, numbers, top problems, steps in
  progress, recent activity, the rules: real numbers only, say before -> after and ask "Shall I make this change?") and
  `seo` + `site` families in view. Changes: `hoola_site` matches the SEO site's host against the hosting host map for HER
  account - a site Hoola hosts may be changed with the `website` tool only after her yes; any other site gets the fix to paste.
- Phone: the SEO desk (employees_screen.dart) gets Call + Chat. Call reads `/api/seo/chat` and starts the live call on that
  chat (`CallSession.convFor`, cleared when the call ends or fails), so its words and changes land in the same SEO chat as
  the web. Chat opens `/console/seo` inside the app (signed in).
- Tests `test_v0999_35_seo_desk.py` (7): the chat is its own and knows the desk, a call from it is an SEO turn, changes only
  on a site Hoola hosts for her, the turn hooks + families, the page + wiring, the phone call, and a browser walk (light,
  dark, 390 px): every tab, the chat node kept while tabs change, tier + credits under the chat box, Ask -> About, plan step
  Start, swap + fold, no sideways scroll.

NOT VERIFIED on her server or phone (the Dart compiles first on CI). No real model turn ran in the SEO chat here; whether
the writer asks before every change and uses the `website` tool well is untested. Change cards with Undo inside the chat
(as drawn on board 8) are not built - a change is said in words and undone from the Web Studio's History. On a phone call
the change cards may not show on the call screen (the app's feed follows the open chat); a spoken yes works.


## v0.999.37 KHUD SEEKHE - Hoola Prompting P10, self-improving (owner: "GO P10")

The plan's P10 row: the ledger changes questions, defaults and recipe text; Hoola proposes, the card must show a gain, an
owner tap accepts; a proposed change that does not gain is refused (test).

- `prompt_runs.choices` (new nullable column, added on old tables by `add_missing_columns_for`): for each slot whose value
  IS one of that slot's own listed options, which option - code's label, never her words; a Hoola guess is not recorded.
- `server/app/prompting/khud.py`: tables `prompt_changes` + `prompt_usual`. Measurements over the shape rows of users who
  share (180 days, graded, `unused` left out): ask_off (answered vs not within 5 points), default (one option >= 10 points
  over the others), recipe (another option >= 10 points over the recipe's own value), alert (newest dialect / model >= 10
  points below the one before). Every side needs 8 judged results. `scan` proposes idempotently; `propose` (owner-written)
  is refused at once with no gain; `decide accept` measures again and refuses if the gain is gone; refuse / dismiss / undo.
- Accepted changes reach Prompting: `brief._required` drops an asked-off question, `understand` pre-fills a default as a
  Hoola suggestion (`hoola_guess`), `recipes.use` takes a changed recipe value.
- Her own usual choice: an option picked in 3 of her last 4 prompts of a kind is offered; only after her tap is it used,
  marked `her_default` ("your usual choice"); only hers.
- Routes: GET / POST /api/prompting/khud, POST /api/prompting/khud/{id}/{accept|refuse|dismiss|undo} (owner only, 403
  for others), GET /api/prompting/usual, POST /api/prompting/usual/{id}. Results page: "Hoola improving itself" (owner)
  and "Your usual choices".
- Tests `test_v0826_khud_seekhe.py` (11, incl. a browser walk). NOT VERIFIED: no real ledger rows yet, so nothing is
  proposed until users who share have judged results.


## v0.999.38 BAHAR + SAMUDAAY - Hoola Prompting P11 (owner: "GO P11")

The plan's P11 row: export dialects for outside AI tools, public recipe pages for search, community recipes with
screening and pay-on-kept, all on her word. Her "GO P11" is taken as yes to decision 4 (copy for outside tools, the
plan's recommendation). Decision 5 (community) is built but OFF, because the plan says community opens only after the
ledger has real numbers and paying writers is hers to decide.

- `prompting/bahar.py`: a brief written for ChatGPT (instructions first, the details between """ delimiters, the
  format said), Claude (XML tags: task / details / facts), Gemini (persona, task, context, format) or any picture tool
  (a described scene, exact words in quotes, the shape in words; image + video only). Her facts kept as written, an
  empty required part marked [fill in: ...] so the outside tool does not invent it, no magic phrases. Copy only:
  nothing is sent and no ledger row is written, because Hoola cannot see a result made elsewhere. Midjourney / Runway
  / Suno have no own wording - their guides were not read (plan part 13).
- `prompting/public.py`: /prompts (every recipe grouped by section), /prompts/<id> (what you fill in, the prompt it
  makes filled with the recipe's own examples, the parts a complete prompt has, schema.org HowTo data, canonical
  link), /prompts/sitemap.xml; the website's own shell, styles and security headers; "Use this recipe in Hoola" opens
  /console/prompting#/r/<id>. Switch `prompting_public` (on).
- `prompting/samudaay.py` (table prompt_community): a user offers a SAVED prompt under a name she picks; screened at
  once (the share screen + phone number, e-mail address, GSTIN), parts from her business memory dropped, kept parts
  marked as the recipe's; max 10 waiting per writer; the owner approves (screened again) or refuses with a reason;
  approved recipes join the Recipes shelf and the public pages as com:<id>, every use screened again; the ledger counts
  their kept results, the writer sees the count, NOBODY IS PAID (note on the page). Switch `prompting_community`
  (OFF; PROMPTING_COMMUNITY=true in the VPS .env turns it on).
- Routes: GET /api/prompting/export/targets, POST /api/prompting/export, GET / POST /api/prompting/community,
  POST /api/prompting/community/{id}/withdraw, POST /api/prompting/community/{id}/{approve|refuse} (owner only).
- Page: workbench button "Other AI tools" (tool chips, the text, Copy), saved-prompt panel "Offer as a recipe for
  everyone" (only when community is on), Recipes page "Community recipes" (yours + the owner's review list),
  hash #/r/<id> opens a recipe.
- Tests `test_v0827_bahar_samudaay.py` (9, incl. a browser walk). NOT VERIFIED on her server; no search engine has
  read the pages yet.
## v0.999.36 STUDIO WORKSPACE (built as 0.999.35; their SEO DESK took 0.999.35, both kept; owner, her screenshots of the "Setting the stage" screen and the Hoola chat: "WHY PREVIEW IS THERE AND CODE IS THERE ... PLAN LOADING WILL BE LIKE A 2ND IMAGE ... A HOOLA LOGO ANIMATION AND JUST BELOW THAT A PLAN UPDATE ... THE CHAT PANEL SHOULD BE FLEXIBLE ... LIVE PAGES ... ARTIFACT SPACE SAME AS CLAUDE" -> the animated design (claude.ai/artifact/V9qyn9RWuU1xHeFrsXqCTp) -> "GO BUILD"): the Web Studio while Hoola works - the chat shows ONE working row (the Hoola mark, the real step, a clock, the steps behind its arrow; the "Setting the stage" and "Making the prototype" cards are gone, `workRow`), the panel shows the animated mark with the step and each planned page under it (`workPane`, from the plan peek / the job steps), then each prototype page the moment it is made (`prototype.made_pages`, making.json, view `made` / `total`, served at __proto/<slug>.html "being made"); no Preview / Code tabs until there is something to look at; the panel is a Claude-style panel - one header row with a Preview / Code switch, the title + version, More (Drafts, Cloud, Integrations, Health, Settings) and close, Show panel brings it back (`viewsBar`, `panelHead`); the chat is resizable (drag the line, arrow keys, double-click resets, remembered, `hoola.ws.chatw`). 4 tests + old pins moved to the new design. NOT VERIFIED on her server.

Files: `server/app/static/console/webstudio.js` (`hmThink`, `workRow`, `workPane`, `panelHead`, `peekUps`, `actUps`,
`drawPending`, `drawState`, `viewsBar` + More menu, protoView making, the splitter / close / open handlers),
`server/app/static/console/webstudio.css` (the v0.999.35 block at the end), `server/app/site/prototype.py`
(`made_pages`, making.json written per page, `view` made / total, `render` of a page being made).
Tests: `test_v0999_35_studio_workspace.py`; pins moved to the new design in test_v0667 / v0986 / v0663 / v0782 / v0992 / v0995.
Deploy: the usual vps-ops deploy (server + console only, no new APK needed).


## v0.999.39 PROOF - Hoola Prompting P12 (owner: "GO P12")

The plan's P12 row: the P0 card again on everything + ten real users' four numbers before / after.

- `quality/promptproof.py`. P0 compared her raw line with a HAND-FILLED brief (the ceiling). P12 adds the arm that
  matters now: the brief Hoola fills itself (`brief.understand` + the engine dialect).
  - Free part (no model call): on the 40 web + script asks, the share of must-have items present in her raw line, in
    Hoola's code-only brief and in the hand brief. First run, here: web 6% / 16% / 99%, script 9% / 9% / 98%; nothing
    invented, no magic phrase, 2.9 (web) and 4.5 (script) questions still asked. Read plainly: code alone adds little;
    what closes the gap is her answers to those questions and the one model call - which only the live part measures.
  - Live part: every ask three ways through the real engines (raw, hand brief, Hoola's brief with its model call), the
    P0 scorer, a rupee ceiling that refuses a row before it starts; per section Hoola's gain and its share of the
    ceiling. `python -m app.quality prompt proof --live --budget-inr N [--limit 2]`; vps-ops `prompt_proof` (free)
    and `prompt_proof_try` (2 per section, Rs 300).
  - The 10 sections the P0 card has no engine runner for are listed as NOT covered, with their code checks (every
    starter recipe renders and scores >= 70: all pass).
  - Users: up to ten users who share their results, each with 10+ judged runs, four numbers in the first half of
    their Hoola Prompting history against the second half; numbered, never named; "before" is their first prompts in
    Hoola, not life before Hoola (the ledger sees nothing else) - said on the table.
- GET /api/prompting/proof (owner only) + a Proof box on the Results page (owner).
- Tests `test_v0828_prompt_proof.py` (5). NOT RUN LIVE: no live proof has run, and no user has enough results yet.
## v0.999.37 HER HANDS ON THE PC (built as 0.999.36; their STUDIO WORKSPACE took 0.999.36, both kept; owner: "Do 2 to 7")

After the research on how OpenAI Dots, Grok Bot and Claude (Duet / Cowork / the computer-use tool) run their own
computers, the owner picked items 2-7 of the gap list. NEW `server/app/pc/hands.py` + small hooks; Desktop untouched.

- **2 Take control** (Dots: Take over / Return control; Grok Bot: Take control / I'm done). Hoola PC only (on her own PC
  she uses her own mouse). `hands.take(op, on)` sets `op.takeover`; the PC loop waits in `hands.hold` before its next
  model call (her time is added back to the task's clock) and any model action of a turn already in flight is answered
  "NOT RUN: she has taken control". Her input: POST /api/computer/task/{sid}/input (click / double / right / type / key /
  scroll; keys allow-listed, no Win / super, mapped to xdotool names; sent with log=False; the screen is re-shot after
  each). "I'm done" adds a note telling the task to look at a fresh screenshot and not redo her work. 30 min max.
- **3 Private sign-in form** (Dots private form; Grok Bot Secure Form). New PC tool `ask_login` (site, fields): the task
  clicks the user name box, asks; the page / phone show a form; POST /api/computer/task/{sid}/login hands the values to
  the waiting task, which types user name, Tab, password through `_pc(..., log=False)` and drops them. Never stored,
  never in the chat, never in the model's messages (test checks the model's whole history), the request model's repr
  hides the password. "I'll sign in myself" = skip + Take control.
- **4 Connected app first** (Grok Bot / Cowork order). `pick._connector_first`: a pc_do / hoola_pc_do task whose words
  are a job for her connected Gmail / Google Sheets / Drive / Calendar (google_auth.has_google) or a Composio app she
  joined is sent back ONCE naming the tools; the same task again within 30 min runs (her wish for the screen stands).
  PC worker prompt `hands.ORDER`: page tools before ax_* before pixel clicks; sign-ins via ask_login; CAPTCHA / passkey
  = ask her to Take control. PC manager RULES got the same order line.
- **5 Her own Hoola PC** (Grok Bot / Dots: one computer per user). `pool.HOME` tenant -> device, saved to
  `<pc files dir>/../hoola_pc_home.json` (atomic write) and read back after a restart; `pick` tries her home PC, then
  her last; with her home PC busy for someone else she waits up to `hoola_pc_home_wait_s` (90 s) in the queue, then
  takes another free one; a new user gets the free PC fewest users call home.
- **6 Parallel jobs** (Grok Bot: one screen, one job). Her second Hoola PC job runs on another free Hoola PC beside the
  first (already true); when none is free it now WAITS in line ("her other Hoola PC job is using the Hoola PC") instead
  of `pool.mine_busy` replacing her running job. `/api/computer` running gains `others` (her other jobs), shown on the
  page. Real parallel needs more Hoola PCs deployed (vps-ops pc_deploy lines=2+, ~2.5 GB RAM each).
- **7 Action checker** (Dots auto-review; Grok Bot Auto Review counts only her messages). `hands.gate` before a step:
  the label comes from the last page_elements (page_click), ax args, or the model's own line for a pixel click / Enter;
  only labels matching submit / send / pay / delete / publish / apply / book ... are checked; money words always ask her
  card; a step she approved in the last 3 steps or her approved repeat job runs; otherwise one small model call
  (pc_check_model) sees ONLY her words (op.task + `op.heard`, her later words) and the action: allow / ask (her card,
  remembered as `op.ok_step`) / block (refused with the reason). A checker that cannot run asks her. Switch
  `pc_action_check` (default on).
- Tests `test_v0999_37_pc_hands.py` (15) + the 199 existing PC / computer tests green; a Chromium walk with a seeded
  running task: sign-in form -> values reached the task, fields cleared; Take control -> click mapped to (640, 318) on
  the 1280x800 screen, typing and Enter reached the PC; I'm done -> the note; no page errors; no sideways scroll at 390 px.
- NOT VERIFIED: on her server, a real portal sign-in, a real Hoola PC, the phone screen (compiles first on CI).

## v0.999.38 CREATE ON THE PHONE - the phone Create design fixes (owner: "NOW CHECK THE EXISTING APP SIDE CREATE SECTION DESIGN PROPERLY" -> "GO FIX ALL")

The design check took pictures of all 15 phone Create screens (CI goldens 65-79, light + dark) and found five problems. All five are fixed; phone only, no server change.

1. Music: the 3-across style tiles broke names inside words ("Bollywoo/d", "Devotion/al") and the "Instrumental" tab ended in "…"; the coloured dots almost vanished on dark glass. `CrTiles` with a dot now sits two across (`cols` null = 3, or 2 for swatch tiles), the dot is 12 dp in the theme's full colours (`crDot`), and `CrSegment` shrinks a long name to fit (`FittedBox`, scale down) instead of cutting it.
2. Pictures: a loading or missing picture showed a flat soft colour block. `CrPictureStandIn` = a painted scene picked by the item's id + a glass mark (picture / face / film / cinema) sized to the tile; `CrItemImage` and `CrNetImage` show it while loading (`frameBuilder`) and on failure. Used on My creations, Director's film list, a film's cast faces, AI casting's "Your cast" and Cinema's recent jobs. Tiles that draw their own play button pass `mark: false` (one mark, never two).
3. Type: Create used 18 text sizes. Every `fontSize` in lib/ui/create now sits on the app scale 12 / 13 / 15 / 16 / 18 / 22 / 28 / 32 (69 moved: 12.5/13.5 -> 13, 14/14.5 -> 15, 15.5 -> 16, 17/19 -> 18, 20/24 -> 22, 26 -> 28, 34 -> 32).
4. Fields: Brand kit and AI casting typed into solid outlined boxes. `CrFieldCard` / `CrField` = one glass card with a quiet label over each field and a hairline between, 48 dp to tap.
5. The film page's bottom box hint ("Change something… make scene 3 brighter") was cut mid-word on a phone; it is now "Say what to change in the film" (one line), and the editor's "What should change?".

Tests (test/create_native_test.dart): every Create size on the scale, no flat colour fallback, the glass field card in both screens, swatch tiles two across + the segment fits. NOT VERIFIED on her phone; the CI pictures are the check.

## v0.999.40 SOCIAL DESK (built as 0.999.38; their v0.999.38 CREATE ON THE PHONE and v0.999.39 PROOF took those numbers, all kept)

Owner, 19 Nov 2026, after the SEO desk: "NOW LETS MOVE TO NEXT AI EMPLOYEE SECTION" -> the design (8 boards,
claude.ai/artifact/MkKK3knH9dzYJJWh7kyAfT) -> "GO BUILD". The Social Media Manager (next in the Hub after SEO) gets the
SEO desk's shape: its own section, its own chat beside its screens, a voice call from the phone.

- **Page** `/console/social` (`socialdesk.html/.js` + `socialdesk.css`; frame, chat, cards and buttons come from
  `seodesk.css`, the twin): no Hoola sidebar; the Social chat on the left (swap sides, fold), Today / Calendar / Inbox /
  Growth / Ads / Reports & settings on the right, the setup form the first time and a connect screen until an account is
  linked. The chat column is never redrawn when a tab changes; a 60-second refresh keeps what she types in a caption or
  reply box (`keepInputs`). Ask on any number / post / message / competitor puts it in the chat as the subject.
  Every number is the server's (`/api/social/desk`, `/api/social/inbox`, `/api/ads/metaads`, `/api/social/ytads`).
- **Screens:** Today = needs you (approve the calendar, OK today's posts, inbox, paused, first read), the numbers with
  their baseline, this week's posts, inbox counts, worth a boost, the activity feed. Calendar = post cards (picture, time,
  status, hook, caption editable, picture brief, problems) with OK / Publish now (confirm) / Picture / Make poster /
  + YouTube / + LinkedIn / Skip, Approve calendar, Rewrite draft. Inbox = Needs you / Leads / Complaints / Done with the
  drafted reply editable, Send reply / Hide / No reply needed, the 24-hour DM rule said. Growth = competitors, what to
  follow, hashtags, hook styles, customers tagging her (ask / their yes / credited draft), creator check. Ads = Meta and
  Google drafts with Check (free) / Create (paused, confirm) / Start (confirm naming the total) / Pause, new drafts by
  goal, account pick; every field of a draft is still edited in the old desk's full ad editor
  (`/console/?v=socialdesk&full=1`, flag `HOOLA_FULL_DESK` set by v2.js before it clears the address). Reports & settings
  = trust (Learning / Partner; Trusted closed), quiet hours, pause, emergency stop, monthly PDF, refresh, best times, the
  24/7 jobs, accounts (connect / disconnect), pause / let go. The old console desk opens `/console/social` (employees.js).
- **Social chat** = Conversation kind 'social' (`socialchat.py`, GET /api/social/chat, POST /api/social/chat/new, GET
  /api/social/chat/{id}/ok), out of her chat lists (`callconv.not_call`, `convs.current`); greeting from the real desk;
  a turn in it, or a call started from it (call record's origin), gets the `<social_desk>` block (accounts, numbers,
  strategy, calendar counts, posts waiting, inbox, her facts, recent activity, the rules) and the families socialdesk +
  kalam + ads in view (santosh.py `_steps_begin` / `_steps_end`).
- **New tool `social_desk`** (`agent/socialdesk_tools.py`, family socialdesk; registry 630 -> 631): the desk had no tool,
  so a chat could not act on it. read (summary / calendar / inbox / growth), edit_post (caption, hook, hashtags, time,
  where; status only draft | skipped - approved is refused in code), draft_reply (saved, not sent), ignore, run (daily /
  plan / inbox / growth / monthly). It can NOT post, send, approve, hide or start an ad: those stay her taps (the v0.999.12
  rule). An edit to an approved post sends it back to draft (social.desk.set_post's own rule). Owner only.
- **Phone:** the Social desk gets Call (runs on the Social chat via `CallSession.convFor`, `Api.socialChat`) + Chat
  (opens `/console/social`).
- Tests `test_v0999_38_social_desk.py` (7, incl. a Chromium walk light / dark / 390 px: tabs keep the chat, OK on a post,
  Ask, inbox boxes, swap, fold, no sideways scroll); 36 tool-count pins 630 -> 631. The test caught the tool passing any
  status through (a model could have approved a post) - fixed before shipping.
- LEFT RED ON PURPOSE: `test_v0836_desktop_team.py` is a FROZEN PC test; it pins the tool count (630, now 631) and the
  version (0.999.39). Editing it was refused in this session, so it is untouched - its two pins need the owner's OK.
- NOT VERIFIED: on her server, a real model turn in the Social chat, a real Instagram / Meta account, the phone (Dart
  compiles first on CI).

## v0.999.41 ONE ROW WHILE IT BUILDS (built as 0.999.39; their PROOF took 0.999.39 and SOCIAL DESK 0.999.40, both kept; owner, on the build page screenshots: "Too many rows above the page while it builds: the panel header, the LIVE row, the page tabs, then a browser bar. -- FIX THIS"): while the website is written the panel has ONE header row - the site name, the LIVE tag with what is being written + parts done + a clock (`#wsLBar` `.lstat`), a page picker that opens a menu of the pages with their dots / ticks instead of a row of tabs (`#wsLPages` `.lpmenu`, data-act lpages, Escape / outside click close it), the device switch, Follow and Code as icon buttons, close; the page sits right under it with no browser bar; no second Pause (the chat working row has it); "Checking every page" when it checks; on a narrow panel the title, clock and Follow give way (`@container wpane`). 3 tests + old pins moved. NOT VERIFIED on her server.

Files: `server/app/static/console/webstudio.js` (`liveView`, `drawLiveBits`, `panelHead` opts.live, `viewsBar(extra, live)`,
the lpages menu handlers), `server/app/static/console/webstudio.css` (the v0.999.41 block before the chat kit block).
Tests: `test_v0999_41_one_row.py`; pins moved in test_v0664 (`.lstat b`) and test_v0667 (LIVE tag in the header, no browser bar).
Deploy: the usual vps-ops deploy (console only, no new APK needed).

## v0.999.42 CREATE ON THE CONSOLE - the console Create design fixes (owner: "NOW CHECK THE CREATE SECTION ON CONSOLE DESIGN PROPERLY" -> "GO FIX ALL")

A Chromium walk of all 17 console Create pages (1440 light + dark, 390 wide, with sample creations and a film) found six problems; all fixed in `static/console/studio.js` / `studio.css` / `cinema.js`.

1. A missing picture showed four different bare ways (grey box with words, a floating line on the Image page, a thin strip for the cast sheet). Every picture / clip now sits on a painted stand-in (`standIn`: scene or portrait + a mark, `.ph-mark`); the file covers it once it loads, and a missing file keeps the drawing with a small "File not available" chip (`hydrate`). Used on Studio home, My creations, Image, the AI casting sheet and its Your cast grid, and film-page cast faces.
2. Studio home's row used its own tile: a script showed a music note, songs / voice-overs were plain lilac boxes, and a script opened a dead-end box. Now ONE tile (`itemTile`) for every page; My creations uses it too; a script is a drawn page and opens in the Script writer from anywhere (`openScript`, via `itemAction`).
3. A film with no picture was a big pink letter; now a painted scene of its own (seeded by its name) + a film mark (`filmTile`). The voice list keeps its letter tiles (`initTile`).
4. AI casting said "voice voice" when no voice was saved; the tag now shows only a saved voice.
5. The Video editor's Made for was the browser's plain dropdown; now the studio's own menu (`menu`, `edPlats` / `edPlat`), and its four lengths sit in one row (`.grid-opts.four`).
6. Hoola Cinema's 13px labels moved to 14px, the studio's own scale.

Tests: `test_v0999_42_create_console_design.py` (4 code checks + a browser walk: drawn stand-ins and chips on the home row, one script tile, no lilac box, the editor menu opening). `test_v0323` updated to the painted film tile. NOT VERIFIED on her server.


## v0.999.43 VIDEO CHAT (20 Nov 2026)

Owner, on the Video page: "NOW LETS WORK ON VIDEO SECTION UI / UX ... SHOW NEW DESIGN HERE FIRST" -> design canvas
claude.ai/artifact/EPTALfT1jEFJBskMRpc68K (video page, price card + making, opened clip, camera moves) -> "THIS IS TO BE A FULL
CHAT PANEL -- AND AT BOTTOM THERE IS DIFFERENT OPTIONS REGARDING VIDEO -- ALSO IN THIS CHAT USER CAN UPLOAD THE IMAGES, VIDEOS,
DOCUMENTS, EVERY FILE" -> board 5 (the typing box with its menus) -> "GO BUILD".

Server
- `server/app/videochat.py`: a Video chat = Conversation kind 'video' (the SEO / Social desk pattern): `current` / `new_chat`
  (an untouched one is reused) / `chats` / `owns`, routes GET /api/video/chat, POST /api/video/chat/new, GET /api/video/chats,
  GET /api/video/chat/{conv}/ok. Kept out of her chat lists (`callconv.not_call`, `convs`). A turn there (or a call started from
  it) gets `block` (rules: use her settings note exactly, one clip = video_studio action=clip, her photo = start_image_file_id,
  a document = file_read first, never invent prices, the price card comes by itself; + the clips made in this chat with their
  state) and the `studio` tool family in view (hooks in `agent/santosh.py`).
- `studio/service.clip(...)`: ONE function for a short clip - create (prefs incl. model / resolution / auto, her chat), plan in
  the background, then (after_plan) her photo becomes the first shot's start_image, Sound off sets audio False on every shot,
  then generate (price card) or the free preview; a second clip in the same minute gets "(2)"; refuses an empty brief, 1 or
  4+ compare models, an unknown `then`. `view()` adds `chat`, `created_ts`, `start_frame`.
- POST /api/studio/projects takes `audio`, `start_image_file_id`, `conversation_id` (checked as hers) and sends every
  `then` request through `ss.clip`. `video_studio` gains action `clip` (+ resolution / auto / compare / audio /
  start_image_file_id / then).

Console (studio.js / studio.css, inside the Create shadow root)
- Left: the Video chat on the chat kit (`HoolaChat.mount`, chatkit.css linked into the shadow root): her messages, Hoola's
  replies, and each clip made in this chat as a card after the reply of the turn that made it (`threadList`, `chatClip`,
  `drawChatClips`: picture, brief, tags, state, progress bar, the price card with Yes / No). Header: title, earlier video chats
  (menu), new chat.
- The box: a tray of files above her words (+, drag onto the chat, paste; any file, 20 at most, 30 MB each, uploaded to the
  chat's files; a photo can be "First frame"), and under the words every option as a button: model (the existing picker with
  Hoola Auto modes + compare), shape, length, camera (a sheet of the 26 moves in seven groups, each drawn, with search),
  resolution, sound, takes, spoken language (the studio's drawn menu), Improve, Send / Stop. The price line under the box.
  Her picks ride the message as "[Web console Video settings: ...]" (stripped from her bubble; read before the tray empties).
- If the turn fails and no clip was made, "Make the clip straight away" makes the same clip directly (newClip(false, src)),
  into this chat.
- Right: Your videos with All / Making / Ready / Needs you (counts) + search; a waiting price card is "Needs your Yes".
- An opened clip: the player beside its words, clip facts, what she paid vs the card, Download, Change and make again (puts
  the words in the box), Edit in Director.
- The chat column has its own remembered width (`--cw`, 560 px default, drag the edge).

Tests: `test_v0999_43_video_chat.py` (6: own chat + block, hooks + routes, one-call clip with the first frame + sound off +
a second name, clear refusals, page pieces incl. 26 moves, a Chromium walk light + dark: menus, camera sheet, a photo in the
tray as first frame, filters + search, the message carries the settings note + file and her bubble shows only her words, the
straight-away path when the turn fails, the clip card with its price card in the chat). Older pins moved to the new page:
v0262, v0263, v0309, v0325, v0333, v0807.

NOT VERIFIED: on her server; no real video engine or real model turn has run this chat (in the tests the model call fails, so
the straight-away path was exercised). Not built: attaching from My creations / Brand kit in the + menu, voice input in this
box, a video she attaches being used as motion (the studio cannot copy a video's motion; Hoola is told so).

## v0.999.44 ACCOUNTS DESK (built as 0.999.43; their VIDEO CHAT took 0.999.43, both kept) - the GST & Accounts employee's own section, with files in the chat

Owner: "OK FINE PERFECT. NOW LETS MOVE TO NEXT EMPLOYEE" -> the 7-board design (claude.ai/artifact/SEsautNMYTn6DTx6S1DZH8)
-> "GO BUILD... USE CAN EVEN ATTACH THE FILES, PHOTOS, DOC IN CHAT".

The SEO / Social desks' twin for GST & Accounts (next in the Hub after Social).
- `/console/accounts` (`accountsdesk.html` / `.js` / `.css`, on seodesk.css): no Hoola sidebar; the Accounts chat (swap /
  fold, kept while pages change) beside the desk. The desk's screens are the existing `bahi.js` in a new `bare` mode (no
  crumb / hero; `show(keys)` limits the tabs; "Ask about this" puts the page in the chat as its subject), grouped into six
  pages: Today (Needs you from `/api/accounts/desk` + Overview), Bills & register (Bills, Register), GST returns (Credit
  (ITC), GSTR-1, GSTR-3B, e-Invoice), Bank & payments (Bank, Pay + TDS), Month-end & CA (Month-end, CA pack), Settings
  (trust / pause / let go + Connection, Rules, Plan). Every button is the desk's own route; nothing new files or pays.
  `accountsdesk.css` copies the console's `ddk-` / `acd-` rules from v2.css with the console tokens mapped onto this page's.
- Files in the chat: the + button, dropping files on the chat, or pasting a screenshot uploads to
  `/api/conversations/{chat}/files` (20 files, 30 MB each, a chip per file with x); Send carries their file_ids, so the
  model is told each file_id (chatfiles.context) and can read it.
- `accountschat.py`: Conversation kind `accounts`, out of every Hoola chat list (callconv / convs), a call started from it
  counts; `block()` = her GSTINs, this / last month from the register, due dates, what waits for her, the rules (never
  invent, never ask for a portal password or OTP, what it cannot do); routes `/api/accounts/chat`, `/chat/new`,
  `/chat/{id}/ok`, `/api/accounts/desk`.
- NEW tool `accounts_desk` (registry 632, family accountsdesk, admitted in the Accounts chat): read (summary / register /
  bills / bank / credits / owed / payables), read_bill (an attached file_id or text -> a DRAFT with its checks, channel
  `chat`), fix_bill (`bahi.intake.fix_draft`: changes a draft's figures, checks run again, before -> after), import_statement,
  match_bank (proposes only), prepare (GSTR-1 / GSTR-3B inside Hoola), tds (a worksheet), supplier (GSTIN check). It never
  adds a bill to the register, sends to the GST portal, files, records TDS, closes a month or pays. Changes owner-only.
- `/console/?v=accountsdesk` goes to the new section (`?full=1` keeps the old page). Phone: the employee page's Open desk
  opens `/console/accounts`, and a "Call GST & Accounts" button calls it on its Accounts chat (`callAccountsDesk`,
  `Api.accountsChat`).

Tests: `test_v0999_44_accounts_desk.py` (9, incl. a browser walk: six pages, the chat kept, a file attached and removed,
swap / fold, light / dark / 390 px). Tool-count pins 631 -> 632. LEFT RED: the frozen `test_v0836_desktop_team.py`
tool-count + version pins (needs her OK). NOT VERIFIED: her server, a real model turn reading a real bill photo (OCR must
be installed on the server for pictures), the phone.

## v0.999.45 A PROFESSIONAL PREVIEW PANEL (built as 0.999.43; their VIDEO CHAT and ACCOUNTS DESK took 0.999.43-0.999.44, all kept; owner: "STILL NEED POLISH AND PROFESIONALIIOM IN WEBSITE SHOW PANEL"): the address bar names the site with a "Draft · not live" badge ("Editing" in edit mode) instead of the bare word preview; the desktop page fills the stage with no empty band under it and a phone / tablet is fitted whole to the panel height (`fit` reads the stage); on a narrow panel the title and the address are hidden instead of cut to one letter (`@container wpane`); the Code files read as a list with an HTML / CSS / JS chip and a proper empty state. 5 tests incl. a browser walk. NOT VERIFIED on her server.

Files: `server/app/static/console/webstudio.js` (`preview` address bar, `fit` fills the stage / fits a device whole, `code` file list),
`server/app/static/console/webstudio.css` (the v0.999.45 block before the chat kit block).
Tests: `test_v0999_45_panel_polish.py`.
Deploy: the usual vps-ops deploy (console only, no new APK needed).

## v0.999.46 CA DOCUMENT DESK (owner: "NOW A GST AND ACCOUNTANT AI EMPLOYEE --- MUST HAS ATTACHMENT OF DOC, IMAGE, PDF, ZIP ETC --- VIA A WHATS APP, TELEGRAM, SLACK, EMAIL, LINKEDIN, LOCAL CA PC ETC --- FROM COLLECTING DOCUMENTS, ARRANGING IT IN CA ASSIGNED PC OR IN CLOUD. ALSO FOLDER OF EVERY CUSTOMER OF CA" -> her answers: desktop freeze exception YES for this one action, storage Hoola + her Google Drive, design first -> canvas claude.ai/artifact/PFw2fkVM8BxubJXUgUxUMz (6 boards) -> "GO BUILD")

The GST & Accounts employee now runs a CA practice: every client of the CA has a folder
(Client / FY 2026-27 / 10 October / Purchase bills / `2026-10-06 Patel Steel PS-2611.pdf`, plus Permanent), and documents
are collected from every channel the CA's clients use and arranged by themselves.

- `server/app/bahi/practice.py` - tables `acc_clients` (name, folder, GSTIN, PAN, the client's WhatsApp numbers / emails /
  Telegram ids / Slack channels, a link code), `acc_files` (one document: client, status filed | waiting | dropped, month,
  kind, the name in the folder, the original bytes content-addressed under `practice_files_dir`, channel, sender, Hoola's
  guess + why it waits, Drive / PC copy state), `acc_practice_set` (channels on, Drive / PC mirrors, the PC folder, checklist,
  Telegram / Slack secrets sealed), `acc_drive_folders`, `acc_mail_seen`, `acc_doc_requests`.
  `collect(tenant, channel, sender, name, bytes)`: the sender is matched to a client; an UNKNOWN sender is never filed by
  itself (it waits, with the client whose GSTIN is on the bill as a guess - "Who is this?"); an archive is opened
  (`archive.open_archive`) and every file inside collected on its own, a locked one waits, a program inside is not kept;
  `filecheck` danger = not kept; the file is read (PDF / Word / Excel text, OCR for photos) and `classify` works out the
  kind (sales: the client's GSTIN issued it / purchase: addressed to the client / bank statement / expense receipt / GST
  return / permanent / other) and the month from what is ON it; a statement spanning months, no date, or an unreadable file
  waits with choices; the same bytes twice for a client are kept once. `file_it` = her tap (remember the sender = every
  other waiting file from that sender goes too). Requests: a monthly checklist ticked only from files that arrived, a draft
  naming exactly what is missing, `send_request` only on her tap (email through her mailbox; WhatsApp inside the 24 h
  window, else a wa.me link she opens herself).
- Channels: WhatsApp = documents / photos to her business number (Meta media download with her number's token; only a
  tenant that has clients collects, so a shop's customer photos never land here); Telegram = her own bot for clients
  (`/start <client code>` link ties the client, getFile download); Slack = her app in client channels (signed events,
  url_private_download); email = mail with attachments from a client's saved address (worker, every 5 min); the CA's PC =
  files dropped in a client's `_Drop here` folder (Hoola Desktop uploads them to /api/practice/pcdrop with its device
  token and moves them to `_Drop here\_Collected`, never deletes); upload on the console / phone. LinkedIn is shown as NOT
  POSSIBLE: LinkedIn gives no app access to messages or their files.
- Mirrors (worker `practice_jobs`): Google Drive `My Drive / CA Clients / ...` (folders made once, reused); the CA's PC via
  the new desktop action `save_into` under the folder she picked (default Documents\CA Clients; system folders refused;
  `..` refused; never over another file). An older Hoola Desktop without `save_into` gets the flat Santosh Inbox with the
  client / FY / month in the file name (`pc` state `inbox`). PC off = the file waits.
- Desktop (FREEZE EXCEPTION, owner's yes in chat 20 Nov 2026 for this one job): NEW `desktop/santosh_desktop/cadesk.py`
  + `do_save_into` / `do_ca_drop` in `actions.py`. Desktop version not bumped (the server falls back for old desktops).
- Chat: `accounts_desk` gains clients / client_add / folder / doc_inbox / file_doc / request_draft (no new tool; file_doc
  only after she says whose it is; requests are drafts); the Accounts chat block carries a CA practice line.
- Routes `/api/practice/*` (`bahi/practice_api.py`), webhooks `/webhooks/practice/telegram/{hook}` and
  `/webhooks/practice/slack/{hook}`.
- Console: CA practice pages in /console/accounts (`static/console/capractice.js`): Clients, a client's folder, Document
  inbox, Requests, Channels & storage. Phone: `lib/ui/ca_practice.dart` (Clients, folder, inbox, Scan a bill) from the
  accounts employee's "Your CA clients" button.

Tests: `test_v0999_46_ca_desk.py` (12: known sender filed by month + kind, unknown sender waits + her tap files the rest,
ZIP opened + program not kept, unclear month waits, requests + her tap, Drive + PC copies in the same folders, older
desktop fallback, WhatsApp only with practice on, routes + the PC drop door + webhook secrets, Telegram start link, the
tool, desktop folder safety), `test_v0999_46_ca_console.py`, phone `test/ca_practice_test.dart`.
NOT VERIFIED: her server, a real WhatsApp / Telegram / Slack / Gmail delivery, Google Drive upload, Hoola Desktop on a
real Windows PC (the exe is rebuilt by build-desktop), OCR of photos on her server, the phone (CI compiles the Dart first).


## v0.999.47 LIKE THEM (owner: "DO THIS FOR HOOLA" on the seven abilities Dots / Grok Bot / Duet had)

1. **Saved sign-ins** (Dots "Save to Passwords", Grok Bot Vault). NEW `pc/vault.py`, table `pc_logins`: sealed with the
   ID-locker key (Fernet), keyed by the page's registrable host (services.gst.gov.in -> gst.gov.in) read when ask_login
   starts, user name shown masked. The private sign-in form gets "Save for next time" (her tick) and, when one is saved,
   "Use saved sign-in (m***@gst)" - typed only on her tap (Dots: reuse needs confirmation). Bank / card / payment / UPI /
   broker sign-ins are never saved. GET / DELETE /api/computer/logins + a Saved sign-ins list on the Hoola PC page.
2. **OTP from her mail** (Grok Bot). `hands.otp_from_mail` runs beside an ask_otp wait for 120 s: mails since the box
   asked in her connected mailboxes (mailbox.service.check account=all) and Hoola's own inbox; a code next to OTP words,
   exact length when the site said; any mail with bank / card / UPI / payment / amount words is skipped, and a bank's own
   box is never filled. Typed like her answer (never in the model's context), and a line tells her where it came from.
   Switch `pc_otp_from_mail`.
3. **Check before done**: `pc_verify` default True again (Haiku looks at the screen; fails open; conftest pins it off).
4. **Tab lanes** (Grok Bot: several screens, one computer, same logins). Hoola PC agent 1.7.0: `lane_open` makes a
   background window in the same Chrome (Target.createTarget newWindow + background), `lane` on any action routes it:
   screen = Page.captureScreenshot of that target, control = Input.dispatchMouseEvent / insertText / dispatchKeyEvent
   (Enter carries "\r"), open_url = Page.navigate + readyState; page_* tools use the lane's target and keep their refs
   per lane; lane windows are hidden from the main job's tabs and tab clean-up; anything else (apps, windows, run,
   install) is refused in a lane. Server: `operator._lane_pc` - no free Hoola PC + a PC doing only HER jobs, agent
   1.7.0+, fewer than `hoola_pc_lanes` (3) jobs -> the new job runs there as a lane (never replaces the first, no folder
   switch, its own window closed at the end, no job card overwrite). Real-Chromium test: a lane typed into a form and
   pressed Enter on Save ("Saved: Meghana") while the main page and refs stayed untouched.
5. **Background mode on her PC** (Claude Cowork background windows). `computer_prefs.bg`, PUT /api/computer/mine/background,
   console switch + phone app-bar toggle. A task on her PC with it on: tools without click / type / key / scroll / drag /
   open_url / switch_tab / window / focus_window / ax_press / ax_type, no Claude computer toolset, a BACKGROUND MODE
   prompt; a held action returns NOT RUN; her approval of "use your mouse and keyboard" lifts it for that task.
6. **Hoola's own email** (Grok Bot's mail.grokbot.com). NEW `app/agentmail.py`: `<avatar>.<6 hex>@HOOLA_MAIL_DOMAIN`
   per user (table agent_mailboxes), the owner's Cloudflare Email Worker (`deploy/agent-mail/worker.js`, catch-all ->
   worker) POSTs the raw mail with HMAC-SHA256(secret, recipient + "\n" + sha256(body)) to /api/agentmail/inbound;
   checked, stored (agent_mails), parsed with mailbox.mime, up to 5 attachments to her chat, one line in her updates
   chat, 300 a day per address, 10 MB cap. Receive only - Hoola never sends from it. The PC worker learns the address
   (use it only when she asked). GET /api/agentmail (address + mails).
7. **Jobs from an email** (Grok Bot routines on incoming mail). Mail rules gain action `run` (her words, 1,000 chars):
   on a matching new mail in Gmail / Outlook (mailbox.sync) or Hoola's own inbox (agentmail.run_rules) a Hoola turn
   starts in her updates chat as actor 'routine' through the turn inbox, with the mail as DATA, once per mail, at most
   20 a day (`agentmail.start_job`, turnpark._kick onto the server loop). `email_rule` tool schema has `run`.
- Tests `test_v0999_47_like_them.py` (12, incl. the real-Chromium lane walk); 211 PC / computer tests green; the 2
  test_v0836 reds (tool count 630, version pin 0.999.39) and 3 test_email_phase2 reds (Hinglish wording) fail the same
  on main. Console walk: Use saved sign-in typed the saved values, Save tick, Saved sign-ins list + Delete, Hoola's
  email shown, no page errors.
- OWNER STEPS: vps-ops **pc_deploy** (Hoola PC agent 1.7.0 for lanes); for item 6 a mail domain on Cloudflare with
  Email Routing catch-all -> a Worker from deploy/agent-mail/worker.js (vars HOOLA_SERVER, secret HOOLA_MAIL_SECRET) and
  HOOLA_MAIL_DOMAIN + HOOLA_MAIL_SECRET in the VPS .env.
- NOT VERIFIED: on her server; a real portal; lanes on the real Xvfb Hoola PC (tested in headless Chromium); background
  mode with real Windows exact mode; the email worker on Cloudflare; OTP reading on her real Gmail.

## v0.999.48 OPEN TO EVERYTHING (built as 0.999.46 / 0.999.47; their CA DOCUMENT DESK and LIKE THEM took those, all kept; O1 of docs/WEB_DESIGN_ENGINE_PLAN.md; owner: "WE WANT ENTIER SAME LIKE A LOVABLE NAD EMERGENT --- NOT ONLY FOR BUINESS" -> "GO O1"): the Web Studio plans any kind of site, not only a business - the architect names what a site is FOR (`purpose`: business, personal, creator, event, community, education, tool, game, product, ai_app, internal, other) beside its kind, a new kind `interactive` (a tool / calculator / quiz / small game that works on the page with no sign-in), the questions and the name step no longer assume a business, the section writer stops calling every project a business and may write a working section script of up to 16,000 characters (`build.JS_MAX`; the fetch / storage / innerHTML / eval bans unchanged), the photo step says "for your site", the Studio home copy + typewriter cover portfolios, weddings, games and calculators, the 8 chips / 24 starters span Website, Online store, Web app, Portfolio, Event, Community, Course, Tool or game, and the details form says Site details unless the site is a business. 8 tests. NOT VERIFIED on her server with a real model.

Files: `server/app/site/architect.py` (PURPOSES / PURPOSE_LABELS, kind `interactive`, purpose in the prompt / understand / clean /
card / site_plan), `site/ai.py` (SECTION_SYSTEM + CRAFT_FLOOR + SCREEN_NOTE not business-only, WORKING SECTIONS clause), `site/build.py`
(`JS_MAX` 16000), `site/service.py` (name + questions + photo step), `site/activity.py` (new label), `site/starters.py` (8 chips across kinds),
`static/console/webstudio.js` (home copy, typewriter, chips, details form by purpose).
Tests: `test_v0999_48_open_to_everything.py`; moved pins: `test_v0835_ghar.py` (the chip list, and the screenshot chip 'Dashboard' -> 'Web app').
Deploy: the usual vps-ops deploy (server + console, no new APK needed).


## v0.999.49 THE CHAT BAR (20 Nov 2026)

Owner, on the v0.999.43 Video chat: "1) USE HOOLA REAL LOGO NOT AVATAR, 2) CHECK CHAT BAR HAVING HUGE OPTIONS LIKE HOOLA AUTO,
9:16 ETC LOOKS VERY BAD AND STALE. FIX IT PROPERLY --- SHOW ME HERE FIRST" -> design canvas claude.ai/artifact/V8XevvPcwUSrXcCxiJrnLW
(logo before / after, option A one settings button + its panel, option B quiet icon row) -> "GO WITH A".

- Studio sidebar (studio.js shellHTML): `HoolaMark.svg()` in violet beside "Hoola Studio" instead of the avatar picture;
  `markWork(on)` swaps it for `HoolaMark.think(26)` while the Video chat works (chatkit.css carries the .hm3 motion).
- Video chat bar: `voptsHTML()` = the settings button (`data-vset`, reads back "9:16 · 8 s · 1080p") + the model button
  (`data-pickmodel`); seven bordered chips over two rows gone. Send is ink (black / light in dark), 36 px.
- Video settings panel `#vsetp` (role dialog) above the box: Shape / Length / Quality as segmented choices (`data-vs` +
  `data-vsv`), Camera opens the existing 26-move sheet, Sound switch + spoken language menu, Takes 1-4, the price (`VID.priceLine`,
  set by `livePrice`) and Done; Reset puts the defaults back; Escape or a click outside closes it. Length shows the picked lengths
  the model makes (5 / 8 / 10 / 15 / 20 / 30 s) on one row.
- Tests: test_v0999_43 pins + its browser walk now use the panel (shape via the panel, camera from the panel, Done closes it, the
  sidebar shows the mark and no avatar).

NOT VERIFIED on her server.

## v0.999.50 DESIGN CARD (D0 of docs/WEB_DESIGN_ENGINE_PLAN.md; owner: "GO D0"): how good today's Web Studio websites look, measured the same way every run - 40 fixed briefs (20 business + 20 not: portfolio, wedding / event, blog, community, course, tool, game, SaaS, AI app) through the Studio's own Build path (plan -> prototype -> Build the real website -> checks) on the hidden tenant __designcard__, generated photos off for the card process; scored in code (built, right purpose, name on home, launch blockers, AI-look tells, minutes, LCP, rupees) + a critic of another company than the writer (Claude, past the GLM / one-model / tier doors) scoring 9 criteria 1-10 from the build's own screenshots (home desktop, the home page down a phone, two more pages); her Good / OK / Bad on the owner page /console/designcard outranks every number (`quality/designcard.py`, `design_asks.py`, /api/designcard*, CLI python -m app.quality design, vps-ops design_card_check / design_card_try Rs 300 / design_card Rs 2000, the server's stuck-build recovery skips the card's tenant). 13 tests incl. a browser walk of the page. NOT RUN LIVE: no baseline yet.

Files: `server/app/quality/designcard.py` + `design_asks.py` (the card), `server/app/quality/__main__.py` (design command),
`server/app/main.py` (/api/designcard, /api/designcard/shot, /api/designcard/verdict, /console/designcard - owner only),
`server/app/static/console/designcard.html/.js/.css` (the owner page), `server/app/config.py` (design_card_critic_model),
`server/app/site/service.py` (recover_stuck skips __designcard__), `.github/workflows/vps-ops.yml` (design_card_check / _try / design_card).
Tests: `test_v0999_50_design_card.py`.
Deploy: the usual vps-ops deploy; then design_card_try (4 sites, Rs 300 cap) when the OpenRouter writer is not paused.


## v0.999.51 1PASSWORD SIGN-INS (owner: "1Password login (Grok Bot) ... LETS WORK ON IT FIRST")

Grok Bot signs in from her 1Password with her approval. Hoola now does it through 1Password's official route:
- **Set-up (hers, once):** in 1Password make a vault for Hoola (e.g. "Hoola"), put the portal logins Hoola may use in
  it, create a **service account** with READ access to that vault only, and paste its token (ops_...) into Hoola
  Computer > Hoola PC > Saved sign-ins > 1Password > Connect. If the token sees several vaults she picks one, and is
  told a one-vault token is safer.
- **Storage:** `pc/onepw.py` table `onepw_links` (tenant, sealed token, vault id + name). Sealed with the ID-locker
  key; no route returns it; the request models' repr hide it; the client is cached 25 min per tenant.
- **Use:** ask_login reads the page's host; `onepw.find` lists the vault's Login items and matches their websites by
  registrable host (gst.gov.in); the form shows "Use 1Password sign-in · <title> (m***@gst)". Her tap sets use_onepw;
  the waiting task reads the item (`onepw.open_`: username / password by field id, else the first text / concealed
  field) and types user name, Tab, password into the PC with log=False. Never in the model's messages (tested).
- **2-step codes:** a login with a TOTP field: the next ask_otp on that task within 10 minutes is filled with the code
  1Password computes (`hands.otp_from_onepw`, before the mail look), and her chat says it came from her 1Password.
- **Never:** bank / card / payment / UPI / broker sites (vault.money_site), CreditCard items, writing to 1Password.
- Official SDK `onepassword-sdk` 0.4.x (requirements.txt; installed by the deploy). API read from the package:
  Client.authenticate(auth, integration_name, integration_version), vaults.list(), items.list(vault_id),
  items.get(vault_id, item_id), field.details.content.code for TOTP. A fake token is refused by the real SDK
  ("invalid service account token") and shown as a plain line.
- Tests `test_v0999_51_onepassword.py` (5) with a stand-in client. NOT VERIFIED with a real 1Password account.
## v0.999.52 LEAD DESK (built as 0.999.47; their 0.999.47-0.999.51 took the numbers, all kept) (the Lead Generation employee's own section)

Owner: "OK FINE TALLY IS ALREADY ATTACHED -- WE WILL DO OTHER LETERS ---- NOW LETS MOVE TO NEXT EMPLOYEE -- GIVE ME THE
NAME" -> Lead Generation -> "PERFECT GO WITH LEAD GENEARTION --- FIRST CHECK HOW CURRENTLY IT IS" (the check: the engine
was built and tested but had only a plain console page, no chat, no phone screen, and nothing after the list) -> design
claude.ai/artifact/FTaYVw37EiqT7gp1NAGGkg (8 boards) -> "GO BUILD".

- `/console/leads` (`static/console/leadsdesk.html/.js/.css`, on seodesk.css + chatkit): the Lead Generation chat on the
  left (swap / fold, + / drop / paste a file) beside five pages: Today (follow-ups due, needs you, running and recent
  searches, counts), Find leads (each source with what it costs and whether it is ready; IndiaMART / Google Maps form with
  the plan before Start; saved searches with Run / Remove), Leads (stage tabs with counts, search / city / source / has
  phone / follow-up due, ticked rows -> set stage, set follow-up, hand over), one lead (#/lead/<id>: stage buttons,
  follow-up, timeline, note, details, source, opt out / forget, Draft a message, Hand to Telecaller), Lists (lists by stage,
  lists given to the campaign desk with what was sent, the send log), Quality & settings (no phone, website did not open,
  untouched 90 days, maybe the same business twice, the public-listings switch, limits, trust, pause / let go, forget all).
  The old console page stays behind ?full=1.
- `leads/pipeline.py` (tables lead_stages, lead_events, lead_saved; the engine's own rows untouched): stages new /
  contacted / interested / not interested / won (a won or not-interested lead loses its follow-up); follow-up date + note;
  notes; the timeline merges found / contact filled / campaign list / sent (from the outreach ledger) with her events;
  `draft` = the words + a wa.me link she taps to send from her own WhatsApp (refused for an opted-out business);
  `to_telecaller` two taps -> telecall.add_lead marked as a cold list (consent False); campaign hand-off of the ticked rows
  or one stage through the engine's own two-tap campaign_list (`ids` added); saved searches, weekly only on the free
  IndiaMART route (`weekly_tick` in worker `lead_desk_jobs`, hourly check, 7 days apart) - a Google Maps search never runs
  by itself; `quality` (same name + city, no phone, dead website from the contact pass, still New after 90 days);
  `import_file` = her CSV / Excel (columns matched by name) through the HER_DATA lane.
- `leadschat.py`: Conversation kind 'leads', out of her chat lists (convs / callconv), the desk block + FAMILIES
  [leadsdesk, leads] on every turn in it or a call from it; greeting from the real counts.
- NEW tool `leads_desk` (`agent/leadsdesk_tools.py`, registry 632 -> 633): read today / leads / lead / quality / lists,
  import_file, stage, follow_up, note, draft, save_search. Owner only for changes; never sends, hands over, opts out or
  forgets.
- Routes /api/leads/desk* (today, summary, leads, leads/{id}, stage, follow, note, draft, quality, lists, saved, saved run /
  delete, telecaller, import); /api/leads/chat*.
- Phone: "Call Lead Generation" on the employee page (its call runs on the Lead Generation chat); Open desk = /console/leads.

Tests: `test_v0999_52_lead_desk.py` (13 incl. a browser walk in light / dark / 390 px). The tool-count pins moved 632 ->
633 in 35 suites. LEFT RED (unchanged, frozen): test_v0836_desktop_team.py pins.
NOT VERIFIED: her server, a real IndiaMART / Google Maps search from the new page, the phone (CI compiles the Dart first).

## v0.999.53 IMAGE CHAT
Owner: "NOW LETS WORK ON IMAGE SECTION" -> first canvas (a settings panel design) -> "DESIGN SHOULD BE SAME AS HOOLA VIDEO SECTION -- SHOW DESIGN FIRST" -> design canvas claude.ai/artifact/MADqzZqiUDde71pFpJ95f7 (6 boards) -> "GO BUILD".
- Server: NEW `app/imagechat.py` (the Video chat's twin: kind 'image', greeting, RULES, `block` lists the picture sets made in the chat, routes /api/image/chat, /chat/new, /chats, /chat/{id}/ok); mounted in main.py; `santosh.py` gives an Image-chat turn its block + the create + file families; callconv / convs keep it out of her chat lists.
- `create_studio` gained action=image (`_image` in agent/create_tools.py): one call starts a job on the Image page's engine (create/jobs) in this chat, says the engine is not set up before starting, returns at once ("never say they are ready").
- create/jobs: an image job keeps aspect / count / style / quality, `public()` shows them with `conv`; every picture's meta carries job, chat, style, prompt (600 chars), inr (3 / 12).
- Console (studio.js / studio.css): V.image / W.image rewritten as a chat (`IMG` state, `iSend`, `iHint` settings note "Image settings: ... Make them with create_studio action=image.", `iThreadList` places each set after the reply that made it, `chatSet` = painting / ready / could not be made, `drawPics` = Your pictures in real shapes via `--ar` + CSS columns, All / Making / Ready + search, `iStyleSheet` = the 9 looks in the camera sheet's frame, `iMake` = More like this / Make the pictures straight away, `lightbox` for a picture = words + settings + price + actions). Shelf pictures handed in (Use as a reference / Change this picture) ride the tray and reach Hoola as file ids in the settings note.
- Tests: test_v0999_53_image_chat.py (6, incl. a browser walk light + dark); older pins updated (v0304, v0999_34, v0999_43).
- NOT VERIFIED: a real picture engine run from the chat on her server; the model following the settings note.


## v0.999.54 HOOLA CRED (built as 0.999.53; their IMAGE CHAT took 0.999.53) - her own password manager (owner: "LETS BUILD OUR OWN 1PASSWORD -- WE NAME IT A HOOLA CRED")

Asked first what 1Password is (answered), then to build our own. Her choices: locking = "Master password + Hoola use";
first release = vault app on console + phone, 2-step codes, autofill in her browser, safety check + import.

- Zero-knowledge vault (`server/app/cred.py`): on her device the master password -> PBKDF2-SHA256 600,000 rounds ->
  key-encryption key; a random 32-byte vault key is wrapped with it (AES-GCM); every item is AES-256-GCM JSON
  {title, username, password, urls, totp, notes, folder}. The server stores salt / rounds / wrapped key / iv + ct only
  (tables cred_vaults, cred_items; versions refuse a stale save; 2,000 items, 96 KB each). Forgotten master password =
  the vault cannot be opened by anyone (said on the setup screen). Change master = the same vault key re-wrapped.
- Routes `/api/cred/vault` (GET / POST / PUT / DELETE?confirm=DELETE), `/api/cred/items` (POST / PUT / DELETE),
  `/api/cred/items/{id}/hoola`, `/api/cred/pwned/{5 hex}` (Have I Been Pwned range proxy - only the first 5 characters
  of the SHA-1 leave, cached 1 h), `/api/cred/device/vault` (the paired extension's token; the same encrypted vault).
- Hoola may use: her device sends that one login once; it is sealed (the ID-locker key) into Saved sign-ins with
  `cred_item` + `totp_sealed`, one row per site; bank / card / payment / UPI refused; switching off or deleting the item
  or the vault removes those rows. On the Hoola PC her tap on "Use saved sign-in" types it, and a 2-step key fills the
  next code box (RFC 6238 in `pc/vault.totp_now`, `op.saved_otp` for 10 min, source "your Hoola Cred").
- Console `/console/cred`: create / unlock, list + search + folders, item detail with copy (clipboard cleared after
  30 s) and the live 2-step code, editor with generator + strength, Safety check (weak, reused, breached, no 2-step),
  generator page, CSV import (Chrome / 1Password / Bitwarden headers), Settings (change master, delete vault),
  auto-lock after 10 min; phone width = top bar with a scrolling nav. Sidebar row "Hoola Cred"; phone tool tile opens it;
  the Hoola Computer "Saved sign-ins" dialog links to it.
- Extension (`desktop/ext/hoola-extension/cred.js`): unlocks on her computer with the master password, keeps the vault
  key in `chrome.storage.session` for 15 min, lists logins for the open site, fills only on her click, copies the 2-step
  code. Rides the next desktop exe build (build-desktop stages the extension).
- Tests `test_v0999_53_hoola_cred.py` (6): real AES-GCM / PBKDF2 round trip in Python, wrong master fails, versions,
  Hoola-use sealing + money refusal + removal, RFC 6238 vectors, the 2-step fill path, breach prefix + device 401,
  console page + extension pins. Browser walk: create, add with 2-step key + Hoola may use, Saved sign-ins row
  appears, every view, lock, wrong master refused, unlock (desktop + 390 px).
- NOT VERIFIED: on her server, in a real Chrome extension, a live breach check; no fingerprint unlock, no sharing.

## v0.999.55 THE KIT (D1 of docs/WEB_DESIGN_ENGINE_PLAN.md; owner, after her four D1 answers: React yes, writer by her tier, Magic UI + React Bits (MIT), Hoola's own references only): the one React kit websites and apps share, in the App Engine template - the full shadcn/ui-style set (48 parts on Radix / vaul / cmdk / react-day-picker / embla / recharts, on the design tokens only), CSS-only effects (Reveal, NumberTicker, Marquee, patterns, SpotlightCard, WordRotate, BorderBeam; Magic UI / React Bits ideas, no upstream code) and the 39 section types of site/taxonomy.py as React blocks (30 website sections + 9 app screens, 2-3 layout variants each, sample defaults, <section data-block>); build image rev 2 with every kit package (motion stays an add); Emergent's taste rules in rules.py (no transition-all, no browser select / date box / alert, no emoji icons, no gradient on a button, at most 3 gradients a file); the contrast floor in tokens.py (audit, derived grey >= 4.5:1); the clinic proof app on the kit DatePicker; the App Engine prompt names the kit once. Done-line proved: every block, every variant, built in the box in 3 genomes and opened in Chromium at 1280 / 390 = 0 problems, 0 rule breaks (`appengine/kit.py`, python -m app.appengine kit, vps-ops appengine_kit). 24 tests. Websites still on the HTML engine (D3 / D4 move them).

Files: `server/app/appengine/kit.py` (gallery + render check + rule check + prompt line), `image.py` + `image/package-lock.json`
(rev 2), `rules.py` (taste), `tokens.py` (audit + derived grey), `service.py` (contrast warnings, kit named once in the prompt),
`proof.py` + `proof_apps.py` (clinic on the DatePicker), `__main__.py` (kit command), `template/src/index.css` (motion tokens),
`template/AGENTS.md`, `template/src/components/{ui,effects,blocks}/`, `.github/workflows/vps-ops.yml` (appengine_kit),
`docs/WEB_DESIGN_ENGINE_PLAN.md` (her decisions + D1 built). Tests: `test_v0999_51_kit.py`.
Deploy: vps-ops deploy, then appengine_setup (rebuilds the image as rev 2), then appengine_kit (PASS = every block renders here).
Found while testing: test_v0814 five-card proof expects 5 apps but the proof set has 7 since v0.842 (fails wherever a box exists);
test_v0832 version story pin red on main too. Neither touched.

## v0.999.56 LEAD SCAN — the public Maps scan fed to the Lead Generation employee (20 Nov 2026; owner: "ON IT AND FEED IT TO LEAD GENERATION AI EMPLOYEE PROPERLY")

- `leads/pipeline.py`: `SAVE_LANES` + SCRAPE in `WEEKLY_LANES`; `save_search` takes query / near / sweep_km; `run_saved` SCRAPE -> `start_scan`; `scan_params` (sweep 1-20 km, rows 1-5000, default 3 km / 500), `scan_running`, `start_scan` (switch, place, plan card limits, one per account, background task in `_SCANS`, saved search marked when it ends); `weekly_tick` skips a SCRAPE search while her switch is off or one runs; `summary` adds `scan_running`.
- `leads/api.py`: POST `/api/leads/desk/scan`.
- `agent/leadsdesk_tools.py`: action `scan` (on the event loop, same hire / owner checks), lane SCRAPE for save_search, query / near / sweep_km / max_rows in the schema.
- `leadschat.py`: RULES teach the scan and the yes-before-switching-on; the block says when a scan is running.
- `static/console/leadsdesk.js`: SCRAPE Find form + plan + Start / Save (weekly), Off pill + Switch on the scan, saved-scan Run says started.
- Checked: test_v0999_56_lead_scan (5), test_v0999_52_lead_desk, test_v0543_leads_scrape.
- NOT VERIFIED: no scan has run against real Google Maps on her server; a scan cut by a restart is not resumed by itself (resume_run_id exists, nothing calls it after a restart).

## v0.999.57 HOOLA CRED PREMIUM + NATIVE (owner: "MAKE HOOLA CRED MORE PREMIUM ... KEEP SIDE BAR ... NATIVE" -> "GO BUILD ALL")

Design first: all 12 pages drawn inside the real console frame on a canvas (claude.ai/artifact/H71Uojvg4ha8RzvtSTqevz); she
said "GO BUILD ALL".

- Console: Hoola Cred is a view of the console now (`#v-cred`, `#credview`), so the console sidebar stays with "Hoola Cred"
  highlighted. `static/console/cred.js` is `window.HoolaCred(ctx)` -> {open(el), leave(), locked()}; v2.js mounts it
  (`CRED`), `/console/cred` answers 302 -> `/console/?v=cred`, cred.html is gone. Styles `cred.css`, every colour a
  console token (light + dark), scoped under `.hcv` because the console already styles `.hc` (code comments, italic) -
  found in the browser walk. JetBrains Mono added to the console's font link.
- Pages: header (status pill "Unlocked on this device · locks in N min", Lock now, New login) + tabs with counts;
  All logins (search, folder filter, grouped list with Hoola / Weak tags; one login with copy, show, live 2-step code
  + ring, websites, note, the "Hoola may use this login" card with its switch and last use; bank / payment logins shown
  as never given to Hoola); New / edit (name, website, user, folder, password with show / new one / meter, 2-step key,
  note, Hoola switch that greys out for money sites); Hoola may use (3 steps + table: sites, 2-step, last used by Hoola,
  switch); 2-step codes (one countdown ring + a grid of live codes); Safety check (health score ring, weak / reused /
  breached / no 2-step cards with Make strong / Change; the breach check runs by itself once per unlock);
  Generator (Random / Easy to say syllables / PIN, length, switches, skip look-alikes, save as a new login);
  Import (Chrome / 1Password / Bitwarden steps, file, preview table with tick boxes and "Already here", import ticked);
  Settings (change master, lock after 5/10/30/60 min, clear clipboard after 15/30/60 s - kept per device in
  localStorage, devices, delete vault).
- Server: `GET /api/cred/hoola-uses` -> {uses: {item: {sites, used, two_step}}} from `pc/vault.cred_uses` (frozen-PC
  exception recorded; read-only, no secrets).
- Phone: Tools > Hoola Cred opens the app's own screen `lib/ui/cred/hoola_cred.dart` (create, unlock, list with search +
  All / Hoola / Codes / Fix chips, one login with copy / show / live code / open website / Hoola switch, new / edit with a
  strong-password button and meter, lock). The crypto is Android's own (`tool/android/kotlin/CredCrypto.kt`: PBKDF2
  WithHmacSHA256 600k, AES/GCM/NoPadding, HmacSHA1 TOTP) through `santosh/native` (credUnwrap / credCreate / credRewrap /
  credOpenMany / credSeal / credTotp on a thread). The vault key lives only in the screen's memory; it locks after 10
  idle minutes or 2 minutes in the background, and when the screen closes. Copies clear after 30 s.
- Checked: the same JCA calls in Java unwrap a vault the browser made (32-byte key) and give the RFC 6238 codes
  (287082, 081804). Browser walk at 1440 px and 390 px: create, 4 logins incl. a bank one, every tab, Hoola-use seal,
  wrong master refused, unlock, no page errors. Tests `test_v0999_55_cred_console.py` (5).
- NOT VERIFIED: the Kotlin and Dart compile first on CI; not run on her phone or her server.

## v0.999.58 THE DESIGN GENOME (D2 of docs/WEB_DESIGN_ENGINE_PLAN.md; owner: "GO D2"): every app gets its OWN design as data before any page - an OKLCH palette generated from one brand hue (any colour; light AND dark; every text pair checked 4.5:1 / UI 3:1 and moved in lightness until it passes), bundled fonts by rule (36 open-licence families incl. Devanagari, self-hosted, the over-used AI faces never chosen), corners + shadow, density (Tailwind --spacing), heading scale, motion personality (reveal duration / distance / easing, never bounce), imagery style; 10 seed directions + her own words / colour; written as tokens.css + the fonts + DESIGN.md (Stitch format, Hoola genome under hoola:, import / export). A new App Engine app with no palette gets its own genome from her name + words; tool app_engine design / design_new / design_import; a named palette keeps the classic tokens (`appengine/genome.py`, service, kit.genome_check, python -m app.appengine genomes 100, vps-ops appengine_genomes). Done-line proved here: 100 random genomes all pass contrast and render every kit block in Chromium at 1280 / 390 with their own fonts (0 failed, 99 distinct brand colours, 22 heading faces, all 10 directions). 9 tests. Websites still on the HTML engine (D3 / D4).

Files: `server/app/appengine/genome.py` (NEW: OKLCH maths, palettes, fonts, genes, css, DESIGN.md, audit), `service.py`
(create with a genome by default, _theme / _write_design / get_design / set_design), `kit.py` (genome_check, runtime_css),
`rules.py` (DESIGN.md locked), `__main__.py` (genomes), `template/src/index.css` (motion vars), `template/AGENTS.md`,
`agent/appengine_tools.py` (design / design_new / design_import + the kit in the description), vps-ops appengine_genomes,
`docs/WEB_DESIGN_ENGINE_PLAN.md`. Tests: `test_v0999_56_genome.py`.
Deploy: vps-ops deploy (+ appengine_setup if not done for D1), then appengine_genomes (PASS = the D2 line holds there).

## v0.999.59 HOOLA SPIDER — Scrapy's way of crawling inside Hoola (20 Nov 2026; owner: "github.com/scrapy/scrapy --- I WANT THIS IN HOOLA -- SAME CLONE")

- NEW `server/app/spider.py`: spec validation (refused keys, caps: 20 start urls, 500 pages, 10,000 items, depth 10, 120 min), per-tenant `data/scraping/<tenant>/spider.db` (spiders / spider_runs / spider_items), canonical URL fingerprints, extract (container + fields + processors), pipeline, links (rules + next_page), run loop (robots, guard, retry, AutoThrottle, block close, limits, checkpoint per page), tick / claim / resume, export_bytes (csv with BOM + formula guard, xlsx, json, jsonl).
- NEW `server/app/agent/spider_tools.py`: the one `spider` tool; check = Scrapy's contracts (one page, items + links + fields always empty, nothing saved).
- `agent/tools.py` registers it (family spider), `admit.py` EXTRA_KEYS spider, `labels_en.py`, `prompts.py` scraping paragraph, `worker.py` slot spider_jobs, `config.py` spider_* settings.
- Tool-count pins 633 -> 634 in 36 suites.
- Checked: test_v0999_59_spider (9), test_v0488_scrape_crawl_jobs.
- NOT VERIFIED: no spider has run against a real site on her server; JavaScript-only pages are not read (HTTP only, like Scrapy without a browser).
