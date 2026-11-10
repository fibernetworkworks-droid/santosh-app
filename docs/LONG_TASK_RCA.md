# Long tasks: how Claude does it, and why Hoola fails (31 Oct 2026, checked on v0.310.0)

STATUS (31 Oct): shipped - v0.314 (causes 1-4, tool fixes 1/2/4), v0.326 + v0.330 (her test run: plan card, one PDF, no quiet PC),
v0.334 (effort for long jobs, tool lanes, clean cuts, FRESH tool card). All her live tests passed on v0.330. Deliberately not done:
renaming / merging tools (lanes instead), strict schemas + usage examples (next, after the tool_card numbers).

## Part A - why Hoola fails long tasks (proved in code)

Two of these were reproduced with a scripted model on the real `run_turn` (repro script kept outside the repo).

### 1. The "say one line" ask ENDS the job (biggest cause) - REPRODUCED
- `santosh.py` (v0.258 CHALTE CHALTE BOLO): after EVERY silent tool round, a ~900-character system ask
  (`goal._NARRATE`: "ab use EK chhoti line batao...") is added to the tool results, up to 6 times a turn.
- It asks for a line, and never says "and call the next tool in the same message".
- A model that answers with ONLY the line returns `end_turn`. With no `kaam_plan` open, the loop treats that as
  the final answer and stops.
- Repro: an ask needing 3 checks. Round 1 ran one tool, then the model wrote
  "Status mein 3 kaam mile. Ab doosra hissa dekh raha hoon." The turn ENDED: 2 model calls, the other tools never ran.
  She sees "dekh raha hoon" and then nothing happens.
- Claude never stops on such a line: its progress text sits in the SAME message as the next tool call.
- The only backstops are weak:
  - `pakka` self-check needs 3+ real calls or a failure, and runs at most 2 times a turn.
  - The goal nudge works only after `kaam_plan` was written.
  - `looks_big` is a word regex and misses most asks; it missed this one.

### 2. A false "atak gaya" at 30 tool calls - REPRODUCED
- `breaker.MAX_CALLS = 30` per turn when no plan is open, and every parallel look-up counts as one call.
- Repro: a research job doing 4 searches per round, every call succeeding. It was killed at round 8 with
  "Main ek jagah atak gaya tha, isliye maine yeh kaam rok diya".
- The v0.221 rescue (moving to long-job caps at step 24) is never reached, because the call cap trips at step 8.

### 3. The 900-second turn limit kills slow jobs that have no plan (read in code)
- `_with_deadline` gives a turn 900 s. It extends to 2,700 s only if a `kaam_plan` goal is open or the turn
  already passed step 24.
- Four browser / PC steps of ~270 s each go past 900 s at step 4, and the job dies with
  "Yeh kaam bahut der se chal raha tha, isliye maine ise rok diya".

### 4. Persistence depends on the model choosing to write `kaam_plan`
- Background rounds, restart recovery, "Aage badhaun?", the progress card and the 80-step / 150-call caps all
  exist ONLY after the model calls `kaam_plan set`.
- Without that call, a long job is an ordinary 24-step turn with every cap from causes 1-3 above.
- Claude Code does not depend on the model to switch on its safety net. The task list is always there, and a
  "done" is checked against the list and tests.

### 5. CORRECTION (31 Oct, live healthz): the live chat brain is CLAUDE (`chat_brain: claude`), not GLM
The points below apply ONLY if `CHAT_LLM` / a GLM or OmniRoute key is switched back on - HISTORY's "production brain
is GLM" notes are from older versions. Causes 1-4 do not depend on the brain and were reproduced either way.

### 5 (old reading). Production brain = GLM / OmniRoute (read in code + HISTORY)
- `llm.choose` sends every text turn to the cheap brain when one is set (`CHAT_LLM=auto`), and HISTORY says the
  production brain is GLM / OmniRoute.
- Claude-only things are then missing on long jobs:
  - adaptive / interleaved thinking (`glm_thinking` is "disabled");
  - prompt caching;
  - Claude's habit of writing text and a tool call in one message.
- `max_tokens` starts at 2,000. A big tool input (a document, a site section) is cut, the half-made call is
  dropped silently (`from_openai` broken calls), and the step is retried.
- Wake turns do not stream, so a slow cheap-brain answer hits the 90 s httpx read timeout.

### 6. Many system nudges per turn, all in Hinglish, all competing
- One long turn can carry several different `[System: ...]` asks at once: narrate, PLAN_FIRST / PLAN_NOW, the
  goal nudge (x8), pakka self-check, steer, replan rescue and the max_tokens cut.
- They pull the model in different directions ("say a line", "write a plan", "don't stop in text").
- Anthropic's own advice: one clear prompt at the right "altitude", and give the model a check rather than a
  "keep going" line.

## Part B - how Claude runs long tasks (primary Anthropic sources)
1. **One loop: gather context -> act -> verify -> repeat.**
   - Stop only on ground truth: a test, build, check or screenshot.
   - A Stop hook can send the model back to work, capped at 8 blocks.
   - Sources: anthropic.com/engineering/building-effective-agents, claude.com/blog/building-agents-with-the-claude-agent-sdk, code.claude.com/docs/en/best-practices.
2. **State outside the model, always.**
   - A task list (TaskCreate / TaskUpdate), a JSON feature list where only `passes` may change, a progress file
     and git commits.
   - Each new window reads them first, then works one item at a time.
   - Source: anthropic.com/engineering/effective-harnesses-for-long-running-agents.
3. **Context engineering.**
   - Clear old tool results first (API `clear_tool_uses`: trigger 100k tokens, keep the last 3).
   - Then compact, keeping recent turns word for word.
   - Sub-agents get clean context and return 1-2k-token summaries.
   - Keep references (paths, links), not full content.
   - Sources: anthropic.com/engineering/effective-context-engineering-for-ai-agents, platform.claude.com/docs/en/build-with-claude/context-editing, platform.claude.com/docs/en/build-with-claude/compaction.
4. **Tools.**
   - Few, consolidated, namespaced tools with meaningful names in their results.
   - Concise vs detailed response formats, truncation that tells the model how to narrow the query, and errors
     that say how to fix the call.
   - Tool search once there are more than 30-50 tools (accuracy 79.5% -> 88.1%).
   - 1-5 usage examples per tool (72% -> 90%).
   - `strict: true` schemas.
   - Programmatic tool calling to keep bulk results out of context.
   - Sources: anthropic.com/engineering/writing-tools-for-agents, anthropic.com/engineering/advanced-tool-use.
5. **Thinking and effort.**
   - Adaptive thinking is interleaved between tool calls.
   - `effort` xhigh is meant for agentic tasks over 30 minutes, with `max_tokens` headroom (64k suggested).
   - Source: platform.claude.com/docs/en/build-with-claude/effort.
6. **Scale effort to the task.**
   - The lead agent spawns 3-5 parallel sub-agents.
   - Rules in the prompt: 1 agent and 3-10 calls for a simple fact, 2-4 agents for comparisons.
   - Plan saved to memory before the context limit.
   - Source: anthropic.com/engineering/multi-agent-research-system.
7. **Progress text never ends the work.**
   - Claude writes its one-line update inside the same message as the next tool call.
   - A turn ends only when the model stops calling tools AND the check passes.

## Part C - the fix plan (proposed, needs GO; PC files not touched)
1. **NARRATE fix.**
   - The ask says "write the line AND call the next tool in the same message".
   - A text-only reply that announces more work ("...kar raha hoon", "ab ... dekhta hoon", "next I'll") never
     ends the turn; it gets one continue nudge.
   - Test: the repro above must run all 3 tools.
2. **Call cap.**
   - Count model STEPS, not single calls. A parallel batch of read-only look-ups counts as 1.
   - Raise the plan-less cap so step 24 (the long-job switch) is always reached first.
3. **Deadline.** A turn that is still making progress (a tool finished in the last N minutes) gets the long-job
   deadline whether or not a plan exists.
4. **Plan always on for multi-step work.**
   - Any turn with 3+ tool rounds gets an automatic plan (written by the server from the request, or at least a
     forced `kaam_plan set`).
   - Background rounds, recovery and the card then work for every long job, not only when the model remembers.
5. **Long jobs on Claude.**
   - Once a turn becomes long (a plan, the extension, or a hard ask), its next calls go to Claude, with thinking
     on and the 6k+ token cap; short chats stay on GLM.
   - Or, at least, turn GLM thinking on for goal rounds and stream wake turns.
6. **One nudge per step.** Merge the system nudges into a single short "state of the job" block (plan steps
   left, what she said, the one rule), in her language.
7. **Done = verified.** A finished goal needs the evidence (file / link / status) from a tool result, like
   Claude's feature list, before `kaam_plan finish done`.
8. **Measure it.** A long-task card in `app.quality`: 20 real multi-step asks scored on finished / stopped /
   false-stuck, run before and after.

---

# Part D - why Hoola picks the WRONG tool (measured on v0.310.0, 31 Oct 2026)

Measured by loading the real registry (`app.agent.tools`), the router (`admit.plan_for`) and the prompt builder.
No model was called: there is no API key in the sandbox, so `python -m app.quality tools --live` must run on the VPS.

## What the model is given
- **430 tools in total**, 132 families, about 418 KB of specs (~105k tokens).
- **Every turn sees 65-96 tools.** "hello" alone gets 65 tools (35 KB): 18 families are always on, plus 10
  WhatsApp-campaign tools that have no family and so ride on every turn.
  - Anthropic: tool-selection accuracy "degrades once you exceed 30-50 available tools".
- **A 41-49 KB system prompt** of rules sits on top of that.
- **The router itself is fine.**
  - Its own 163-ask card scores 163/163 tools "in view".
  - On 26 NEW asks written for this check, the right family was in view 25 times (the APK check missed `appcheck`).
  - So the problem is not "the tool is missing". It is "the model has 65-96 tools whose descriptions are cut,
    and it must choose".

## The root causes
1. **The "schema diet" cuts away the "when to use which" text.** This is the biggest cause.
   - `tools.py` (v0.187) cuts every tool description to 140 characters (700 if it mentions confirm / payment /
     OTP) and every parameter description to 72.
   - It hits **291 of 430 tools**, and 150 descriptions now END MID-SENTENCE with "…".
   - What is cut is exactly the part that tells similar tools apart:
     - `google_search` loses "use it whenever the answer could have changed since your training".
     - `web_sources` loses "when the answer must stand on the sources' own words … or when google_search is not
       answering".
     - `open_website` loses "pages that need login or JavaScript come back empty; then use google_search".
     - `data_fetch` loses "Prefer this over api_call / open_website / the cloud PC". That is the exact rule whose
       absence caused the 100-repo PDF going to the PC.
     - `make_document` loses its whole content format and "Returns file_id (attach to email / hoola_send)".
   - Anthropic says tool descriptions are where the effort pays most ("small refinements … dramatic improvements";
     the team "spent more time optimizing tools than the overall prompt").
   - Hoola did the opposite: it moved that text into a long prompt, or deleted it.
2. **Overlapping tools for the same job, with no clear line between them.**
   - Web: google_search, web_sources, open_website, browse_web, computer_operator.
   - Files and documents: make_document, doc_studio, docs_writer, hoola_make, artifact_make, notebook_make.
   - Memory: remember, memory_search, yaad_khojo, gyaan_khojo, haal_ki_chats.
   - 22 tools say they make or handle PDF / Word / Excel.
   - Anthropic: "If a human engineer can't definitively say which tool should be used … an AI agent can't be
     expected to do better."
3. **No naming scheme.**
   - Verbs are mixed English and Hinglish: `photo_banao`, `app_banao`, `make_document`, `gyaan_khojo`,
     `indiamart_khoj`, `seekhe_kaam`, `haan_karo`.
   - Some desks are one-word tools: `chai`, `paisa`, `seva`, `ads`, `niryat`.
   - There are no `service_action` prefixes (Anthropic: namespace by service, e.g. `asana_projects_search`).
4. **The prompt names tools that are not loaded.**
   - Even with no PC family loaded, the prompt mentions `pc_do` 5 times and `hoola_pc_do` twice.
   - The model is pushed toward tools it cannot see. `pick.py` exists only to block that afterwards, and it
     covers the PC only.
5. **The cheap brain picks** (only when GLM / OmniRoute is configured - the live server runs Claude, see the correction in Part A).
   - GLM / OmniRoute choose the tools at temperature 0.6, with thinking disabled.
   - Claude's tool-choice training, `strict` tool schemas, the tool search tool and tool-use examples are all
     absent.
6. **Raw truncation of tool results.**
   - `_short` cuts every result at 6,000 characters of raw JSON, ending in "…(truncated)", with no hint of how to
     get the rest.
   - Anthropic: truncate with a steer ("use a narrower query / page=2"), and return meaningful fields, not raw
     JSON.

## How Claude does it (sources in Part B)
- **Few tools in view.**
  - Tool search with `defer_loading`: keep the 3-5 most-used tools loaded and let the model search the rest.
  - The definitions shrank from 77K to 8.7K tokens, and selection accuracy rose from 79.5% to 88.1% (Opus 4.5).
- **Full, specific descriptions** that say what the tool does, when to use it, when NOT to, and how it differs
  from its neighbour. They are written like docs for a new teammate, and checked against evals.
- **Consolidated, namespaced tools**, e.g. one `schedule_event` instead of list + create.
- **1-5 real usage examples per tool** for complex inputs (72% -> 90% correct parameters).
- **`strict: true`**, so the tool name and its inputs always match the schema.
- **Concise results by default** (`response_format`), with a 25k-token cap and a truncation hint.
- **Measure picks on real transcripts**, then have Claude rewrite weak descriptions. A tool-testing agent cut task
  time by 40%.

## The fix plan (needs GO; PC files not touched)
1. **Remove the 140-character cut.**
   - Give every tool a full description in one format: what it does; use when; do NOT use when (name the
     neighbour); what it returns.
   - Keep this prose in the tool, not the prompt. Prompt caching (Claude) pays for the size.
2. **A smaller always-on set.**
   - About 12 core tools plus `tool_search`.
   - Everything else is deferred, found by the router or by search.
   - The 10 WhatsApp-campaign tools get their own family.
3. **One tool per job.**
   - Web: `web_search` (short answer) -> `web_read` (one page / quotes) -> `browser_task` (logins, clicks).
   - Documents: one `doc_make` (the doc_studio engine; make_document becomes its quick mode).
   - Memory: one `memory_find` (facts + diary + Gyaan + old chats, with a `scope` field).
   - The old names stay as aliases in `dispatch`, so nothing breaks.
4. **Clean the prompt.** Drop every tool name that is not loaded this turn; the routing rules live in the tool
   descriptions.
5. **Picks on Claude.**
   - Tool picking for owner asks goes to Claude (or at least GLM thinking on, at temperature 0.2).
   - Add `strict: true` and 1-3 usage examples to the 30 most-used tools.
6. **Smarter truncation.** Cap results at a token budget with a hint ("showing 20 of 340 - call again with
   page=2 or a filter"), plus a concise / detailed mode for the big readers.
7. **Measure.**
   - Run `python -m app.quality tools --live` on the VPS before and after.
   - Add the 26 fresh asks from this check plus 50 more taken from her real chats (`harness_events`), scored on
     the first pick and on the finished job.
