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

