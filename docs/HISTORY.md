## v0.742.0 AIHUBMIX — free GLM 5.3 Flash (and more) for testing every Hoola feature (10 Nov 2026; owner: "AIHubMix -- LETS DO IT")

AIHubMix (aihubmix.com/models/free, read 10 Nov) runs 71 models billed at $0. The catch is a one-time $1 top-up, after which each account gets 100 requests a day, 10 a minute, and 1M tokens a day shared across its free models. Its tool support is not published per model.
- `agent/providers.py`: new provider `aihubmix` (https://aihubmix.com/v1, key `AIHUBMIX_API_KEY`). `providers.free()` is True for OpenRouter `:free` and AIHubMix `-free` names, so the dropdown shows them as Free.
- The WHOLE server can run on it with only that key: `GLM_MODEL=aihubmix:coding-glm-5.3-flash-free`. `llm.glm_ready()` is now `providers.ready(GLM_MODEL)`, and `llm.model_in_force()` (her pick, else GLM_MODEL) decides the provider in `_target` / `is_openrouter` / `is_nvidia` / picture checks. `glmdoor._ready` and `modelchoice.offered` follow, so background jobs, Web Studio and the SDK door use it too.
- `modelprofile._norm` drops `coding-` and `-free / :free / -latest / -instruct / -it / -preview`, so `coding-glm-5.3-flash-free` is matched to `z-ai/glm-5.3-flash` in OpenRouter's catalogue and gets its pictures / tools / window.
- `santosh._friendly_error`: an AIHubMix 429 or limit says the free limit is used up (per minute / per day), not "something went wrong".
- Tests: `test_v0742_aihubmix.py` has 5 tests: names + free flag + matching, the whole server on AIHubMix with only its key (url, key, model, no extra fields, GLM 5.3 Flash's abilities, pictures stay on it), the SDK door, the dropdown showing Free, and the plain limit line.
- NOT VERIFIED LIVE: no AIHubMix key yet. Whether its free GLM 5.3 Flash accepts tools like the paid one is unknown until the first call. Its data terms were not read; use it for test chats only.

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
