# Hoola's current design for long, multi-step tasks (read from source, repo HEAD on 2 Nov 2026, v0.435.0)

All sources are local files in `/home/user/santosh-app` (paths relative to it). "file:N" = line number at the time
of reading. Nothing was changed. The frozen PC files were not opened (none were needed).

## 1. What the long-task RCA (docs/LONG_TASK_RCA.md) found and what was fixed

### Takeaway
On 31 Oct 2026 an internal RCA found that long jobs failed for harness reasons, not model reasons. The four main causes were: a narration prompt that ended turns; a false "stuck" at 30 calls; a 900 s turn limit; and the safety net only switching on if the model chose to write a plan. Causes 1-4 were fixed in v0.314. Several deeper fixes were left undone: done = verified, one merged nudge per step, and a scripted long-task eval.

### Cited Findings
- Cause 1 (reproduced): after every silent tool round a ~900-char "say one line" system ask was appended. A model that answered with only the line returned `end_turn`, and with no `kaam_plan` open the loop treated it as the final answer. Repro: 2 model calls, and the other tools never ran — [docs/LONG_TASK_RCA.md:11-24](docs/LONG_TASK_RCA.md)
- Cause 2 (reproduced): `breaker.MAX_CALLS = 30` counted every parallel lookup separately. A 4-searches-per-round research job was killed at round 8 with "Main ek jagah atak gaya tha" — [docs/LONG_TASK_RCA.md:26-30](docs/LONG_TASK_RCA.md)
- Cause 3: a 900 s turn deadline, extended to 2,700 s only if a plan existed or the turn passed step 24. Four ~270 s browser steps died at step 4 — [docs/LONG_TASK_RCA.md:32-36](docs/LONG_TASK_RCA.md)
- Cause 4: background rounds, restart recovery, "Aage badhaun?", the progress card and the 80-step / 150-call caps all existed only after the model called `kaam_plan set` — [docs/LONG_TASK_RCA.md:38-43](docs/LONG_TASK_RCA.md)
- Cause 6: one turn could carry many competing Hinglish `[System: ...]` nudges (narrate, PLAN_FIRST/PLAN_NOW, goal nudge x8, pakka, steer, replan, max_tokens) — [docs/LONG_TASK_RCA.md:60-65](docs/LONG_TASK_RCA.md)
- Correction: the live chat brain is Claude (`chat_brain: claude`), not GLM, so the GLM-specific causes apply only if a cheap brain is switched back on — [docs/LONG_TASK_RCA.md:45-47](docs/LONG_TASK_RCA.md)
- Fix plan proposed eight items: NARRATE fix, count steps not calls, progress-based deadline, plan always on, long jobs on Claude, one merged nudge per step, "done = verified" with tool evidence, and a 20-ask long-task card scored on finished / stopped / false-stuck — [docs/LONG_TASK_RCA.md:105-129](docs/LONG_TASK_RCA.md)
- Status line: v0.314 shipped causes 1-4. v0.326/v0.330 shipped the plan card and the one-PDF fixes. v0.334 shipped effort, tool lanes and clean cuts. Not done on purpose: renaming or merging tools, strict schemas, usage examples — [docs/LONG_TASK_RCA.md:3-5](docs/LONG_TASK_RCA.md)
- What v0.314 actually changed:
  - the AAGE BADHO nudge;
  - MAX_CALLS 30→48, with a parallel batch costing one call;
  - a progress-based deadline;
  - PLAN_NOW at step 4 and a server-written plan 3 steps later;
  - the 140-char tool-description cut raised to 1200.

  The history entry also says it was "Not verified on a live model here" and lists the not-done items — [docs/HISTORY.md:11805-11843](docs/HISTORY.md)
- Part D (tool choice): 430 tools, and every turn sees 65-96 of them. The 140-char description cut hit 291 tools. Raw 6,000-char result truncation had no hint — [docs/LONG_TASK_RCA.md:138-190](docs/LONG_TASK_RCA.md). Later fixed: `DIET_DESC_MAX = 1200` — [server/app/agent/tools.py:987-988](server/app/agent/tools.py); `TOOL_LANES` use-for / not-for text — [server/app/agent/tools.py:1076-1122](server/app/agent/tools.py); `_short` now slims lists and adds a "how to get the rest" hint — [server/app/agent/santosh.py:325-344](server/app/agent/santosh.py)

### Inferences
- RCA fixes 6, 7 and 8 have no matching code (see sections 6 and 8). The design is still "nudge-driven", not "verifier-driven".

### Gaps
- No live before/after finish-rate numbers for the v0.314 fixes were found in the repo. The RCA's proposed "20 real multi-step asks" card does not exist (see section 8).

## 2. The agent loop: caps, deadlines, model/effort choice, parallel tools, when it ends

### Takeaway
One turn is a think → tools → think loop (`_steps_inner`). It has fixed caps: 24 model steps / 48 tool calls / 900 s for a short turn, and 80 steps / 150 calls / 2,700 s once a plan exists or the turn is extended. Model and effort are picked per step from the turn's state. The turn ends when the model stops calling tools AND no nudge sends it back. A nudge can come from the self-check, open plan steps, or a "promise" line.

### Cited Findings
- Caps from config: `agent_max_steps=24`, `agent_max_tokens=2000`, `agent_tool_timeout_s=300`, `agent_turn_timeout_s=900`, `agent_goal_max_steps=80`, `agent_goal_max_calls=150`, `agent_goal_turn_s=2700`, `agent_goal_max_tokens=16000` — [server/app/config.py:16-31](server/app/config.py)
- Breaker:
  - the 3rd identical call is refused (`SAME_CALL_STEER=2`);
  - a tool that failed 3 times is removed;
  - 4 failures in a row stops the turn;
  - `MAX_CALLS = 48` (raised from 30);
  - goal mode allows 7 failures in a row and turns the first stop into one "replan rescue" (search the web, read docs, pick another route).

  Sources — [server/app/agent/breaker.py:12-17](server/app/agent/breaker.py), [server/app/agent/breaker.py:86-100](server/app/agent/breaker.py)
- The loop bound is `agent_goal_max_steps` if a goal is open or the turn was extended, else `agent_max_steps` — [server/app/agent/santosh.py:996-999](server/app/agent/santosh.py)
- Step-24 switch: when the short cap is hit with work still going and no plan, the turn moves once to long caps and is told to write `kaam_plan set` for the rest — [server/app/agent/santosh.py:1323-1340](server/app/agent/santosh.py)
- Deadline `_with_deadline`: the first timeout is 900 s. It extends to the long timeout if the turn is in `_LONG_TURN`, has an active goal, or finished a tool within `agent_progress_window_s` (300 s, stamped in `_PROGRESS` after every tool) — [server/app/agent/santosh.py:269-294](server/app/agent/santosh.py), [server/app/agent/santosh.py:1149](server/app/agent/santosh.py), [server/app/config.py:78](server/app/config.py). On timeout the user sees "Yeh kaam bahut der se chal raha tha, isliye maine ise rok diya" — [server/app/agent/santosh.py:1743-1752](server/app/agent/santosh.py)
- Long-job model/effort per step:
  - `_long_now` = goal / extended / auto_plan / big;
  - a long job is forced onto Claude even when a cheaper chat brain is configured (`agent_long_on_claude`);
  - effort = `agent_long_effort` ("xhigh") for long jobs, `agent_hard_effort` ("high") for hard asks;
  - thinking is on while a goal is open or for big/hard asks (`chat_thinking="goal"`).

  Sources — [server/app/agent/santosh.py:1013-1024](server/app/agent/santosh.py), [server/app/agent/santosh.py:407-421](server/app/agent/santosh.py), [server/app/config.py:32-37](server/app/config.py), [server/app/config.py:51](server/app/config.py)
- Hard asks: `hard.decide` (word rules plus a small judge) marks reasoning asks. They run on `agent_hard_model = "claude-opus-5-5"` with 16k tokens, but only when NOT a long job: "long jobs ... stay on the chat model at agent_long_effort". A hard turn also gets the "SOCH KA TAREEKA" reasoning recipe in the system prompt — [server/app/agent/santosh.py:398-404](server/app/agent/santosh.py), [server/app/agent/santosh.py:748-761](server/app/agent/santosh.py), [server/app/agent/santosh.py:939-942](server/app/agent/santosh.py), [server/app/agent/hard.py:184-230](server/app/agent/hard.py)
- "Big ask" detection is `goal.looks_big`, a word-rule regex: ≥3 list items, sequence words, ≥4 verbs + 25 words, ≥80 words, or ≥3 parts after a colon. Its own comment admits looks_big "missed 50 of 50" hard questions — [server/app/agent/goal.py:349-372](server/app/agent/goal.py), [server/app/agent/santosh.py:747-750](server/app/agent/santosh.py)
- Parallel tools: tools run concurrently only when every tool_use in the step is in `PARALLEL_SAFE`, an 11-tool read-only allowlist (search, open_website, weather, maps, memory_search, kaam_status, IndiaMART, MoSPI). Otherwise they run serially. A batch costs one breaker call — [server/app/agent/santosh.py:684-689](server/app/agent/santosh.py), [server/app/agent/santosh.py:1219-1235](server/app/agent/santosh.py), [server/app/agent/breaker.py:67-72](server/app/agent/breaker.py)
- max_tokens cut: the cap doubles (up to 16k) and a "continue exactly where you were cut" nudge is sent — [server/app/agent/santosh.py:1085-1093](server/app/agent/santosh.py)
- End conditions, when stop != tool_use, in this order:
  1. the pakka check / draftcheck nudge;
  2. a goal with open steps (up to 8 goal nudges);
  3. a server auto-plan closed by the real final answer;
  4. an AAGE "promise" nudge (max 2);
  5. otherwise break.

  Sources — [server/app/agent/santosh.py:1094-1127](server/app/agent/santosh.py). If the step cap runs out with a goal open, the user gets an honest "Goal jaari hai: x/y ... background mein aage badh raha hoon" — [server/app/agent/santosh.py:1349-1360](server/app/agent/santosh.py)
- Tool calls have a per-tool timeout (300 s). A timed-out tool returns an error that says "Don't stop the task" — [server/app/agent/santosh.py:1192-1205](server/app/agent/santosh.py)

### Inferences
- All caps are fixed numbers, not budgets tied to task size or progress. The progress window only helps the wall-clock deadline, not the step or call caps.
- Hard reasoning and long jobs are mutually exclusive for Opus: a long, hard job runs on the chat model at xhigh effort, not on Opus.

### Gaps
- The value of `anthropic_model` (the chat model long jobs actually run on) was not checked in this pass.

## 3. Long-job machinery: kaam_plan, auto plan, AAGE, background rounds, recovery, ask-on-limit, steering, stop

### Takeaway
Persistence lives in a DB table `GoalRun`: goal, step list with states, rounds, hold, recovered count. The model writes it with `kaam_plan`, or the server writes a fallback plan. When a turn ends with steps open, ONE background continuation turn is scheduled. That repeats up to 6 rounds / 180 working minutes, then the job holds and asks "Aage badhaun?". Worker sweeps resume paused goals and recover goals orphaned by a restart. Messages sent mid-job are injected at the next step boundary.

### Cited Findings
- `kaam_plan` tool: actions set / step / add / show / finish. The schema keeps it short: max 15 steps, and `finish` takes outcome done | blocked_on_her | failed | stopped plus `made`, `left`, `your_turn` — [server/app/agent/goal_tools.py:16-44](server/app/agent/goal_tools.py), [server/app/agent/goal.py:36](server/app/agent/goal.py). A new `set` stops any earlier working goal (one plan per chat) — [server/app/agent/goal.py:149-169](server/app/agent/goal.py)
- `GoalRun` columns include rounds, recovered, hold ("limit"), milestones — [server/app/agent/goal.py:57-74](server/app/agent/goal.py). Every change publishes a `goal` bus event, which drives the card in chat and in the call — [server/app/agent/goal.py:1-16](server/app/agent/goal.py)
- Plan prompts:
  - PLAN_FIRST is injected into the turn block when `looks_big` is true;
  - PLAN_NOW comes after `agent_plan_after_steps` (4) tool steps;
  - `_auto_plan` writes a server plan if there is still no plan 3 steps after PLAN_NOW, or right after the first tool round for a "big" ask.

  Sources — [server/app/agent/santosh.py:1717-1725](server/app/agent/santosh.py), [server/app/agent/santosh.py:1269-1291](server/app/agent/santosh.py), [server/app/config.py:49-50](server/app/config.py)
- `_auto_plan` / `_ask_steps`: the server plan comes from her words only, never a model call. It splits on commas / "phir" / "then" into ≤8 clauses. With fewer than 2 clauses it is ONE step (the whole request). It raises the caps to goal level and tells the model via AUTO_PLAN_NOTE — [server/app/agent/santosh.py:814-870](server/app/agent/santosh.py). The real final answer then closes the auto plan, marking all steps done (`_close_auto_plan`) — [server/app/agent/santosh.py:878-885](server/app/agent/santosh.py), [server/app/agent/santosh.py:1098-1104](server/app/agent/santosh.py)
- AAGE BADHO (`aage.py`): `promised()` reads the LAST sentence of a text-only reply. A first-person future or ongoing-work regex (Hinglish / English / Devanagari) means "not finished", unless the sentence waits on her (a "?", card, tap, OTP, confirm). Then a "do it now with tools, or give the real final answer" nudge is sent, at most `MAX_PER_TURN = 2` — [server/app/agent/aage.py:1-57](server/app/agent/aage.py), [server/app/agent/santosh.py:1108-1118](server/app/agent/santosh.py)
- Goal nudge: while open steps remain, text never ends the turn. `nudge_text` lists the steps left plus a "try another way" ladder, up to 8 times per turn — [server/app/agent/goal.py:337-346](server/app/agent/goal.py), [server/app/agent/santosh.py:1105-1107](server/app/agent/santosh.py). Every new turn in the chat gets the "GOAL JAARI HAI" block (done / left / failed steps) at the top — [server/app/agent/goal.py:419-435](server/app/agent/goal.py)
- Background rounds:
  - at turn end, `maybe_continue` schedules ONE continuation turn — [server/app/agent/santosh.py:1797-1802](server/app/agent/santosh.py);
  - it refuses if a card waits on her (pause), or if a background job of the chat is still moving (pause, `JOB_WAIT_S` 1 h) — [server/app/agent/goal.py:481-503](server/app/agent/goal.py);
  - the continuation is a synthetic user message "[Goal jaari: … baaki steps …]" run through the normal `run_turn` — [server/app/agent/goal.py:546-553](server/app/agent/goal.py), [server/app/agent/goal.py:600-616](server/app/agent/goal.py).
- Limits: `agent_goal_rounds = 6`, `agent_goal_minutes = 180` working minutes (time waiting on her is not counted) — [server/app/config.py:38-41](server/app/config.py), [server/app/agent/goal.py:506-512](server/app/agent/goal.py). When used up, `_hold_for_limit` sets status=blocked, hold=limit and the reason "Aage badhaun? Bas 'haan aage badho' likhiye" — [server/app/agent/goal.py:539-544](server/app/agent/goal.py), [server/app/agent/goal.py:620-632](server/app/agent/goal.py)
- Continue after limit:
  - her "aage badho" (or a pure yes) reopens the same goal with a fresh budget, keeping done steps — [server/app/agent/goal.py:645-675](server/app/agent/goal.py), [server/app/agent/santosh.py:1633-1634](server/app/agent/santosh.py);
  - the card button `continue_now` also starts the round at once — [server/app/agent/goal.py:678-692](server/app/agent/goal.py), [server/app/main.py:681](server/app/main.py).
- Resume and recovery: worker sweeps call `goal.resume_tick()` and `goal.recover_tick()` — [server/app/worker.py:433-434](server/app/worker.py).
  - `resume_tick` restarts goals paused on her once nothing waits (within 24 h) — [server/app/agent/goal.py:558-590](server/app/agent/goal.py).
  - `recover_tick` restarts a "working" goal not updated for 600 s with no turn holding the chat. It posts "Server dobara chalu hua — … wahin se aage badha raha hoon", and after 3 recoveries it holds and asks — [server/app/agent/goal.py:695-747](server/app/agent/goal.py), [server/app/config.py:43-45](server/app/config.py).
- Steering (`steer.py`): a message she sends while a turn runs is `offer`ed to a queue. The running turn `take`s it at the next step boundary and appends it to that step's tool results. Her queued turn then `claim`s and does nothing if the message was already delivered — [server/app/agent/steer.py:1-13](server/app/agent/steer.py), [server/app/agent/santosh.py:1237-1248](server/app/agent/santosh.py), [server/app/agent/santosh.py:1642-1655](server/app/agent/santosh.py). While the chat is busy, a quick lane answers her at once — [server/app/agent/santosh.py:1638-1646](server/app/agent/santosh.py)
- Stop: `santosh.stop` cancels the running model or tool call and marks an open goal stopped. Tools in flight return "Stopped by the owner … it may have partly happened" — [server/app/agent/santosh.py:1498-1510](server/app/agent/santosh.py), [server/app/agent/santosh.py:1173-1182](server/app/agent/santosh.py), [server/app/agent/goal.py:324-330](server/app/agent/goal.py)
- Milestones: jobs of 4+ steps push at most `agent_goal_milestones` (2) "half done" notes — [server/app/agent/goal.py:199-210](server/app/agent/goal.py), [server/app/config.py:60](server/app/config.py)
- Background job results: when a watched job (video, website, PC…) finishes, `kaam_followup` sends one short model-written line and can start a "wake" turn with the real brain — [server/app/kaam_followup.py:1-14](server/app/kaam_followup.py), [server/app/kaam_followup.py:171](server/app/kaam_followup.py)

### Inferences
- The "plan" is a flat checklist of strings with states. There are no per-step acceptance criteria, no dependencies, and no artifacts attached except free-text notes.
- The auto plan is often a single step equal to the request. The card then shows 0/1 → 1/1, which gives little progress signal.
- Within a turn, the live state lives only in process memory and is lost on restart: the breaker, call list, steer queue, `_PROGRESS`, `_STOPPED`, `_PENDING`. Recovery restarts from the DB plan plus the saved chat history, not from an exact checkpoint.

### Gaps
- The resume/recover sweep interval in worker.py was not read.

## 4. Context management over a long job

### Takeaway
Hoola sends the whole chat word for word ("FULL CLAUDE MODE"), measured before every call against 75% of the window. Older tool results are trimmed head-and-tail inside a turn. Above the line a "safety net" shortens or drops OLD exchanges. Real compaction (a written checkpoint summary) happens only BETWEEN turns: drafted at 60%, swapped in at 75%. So a long job compacts between its background rounds, not within one 80-step turn.

### Cited Findings
- Gauge: under `chat_context_full_at` (0.75) the request goes as loaded. Over it, the oldest exchanges are shortened in blocks of 10, then dropped and replaced by the rolling summary. "This turn's own messages are never touched." A "too long" error triggers `squeeze` once — [server/app/agent/context.py:1-21](server/app/agent/context.py), [server/app/agent/context.py:244-296](server/app/agent/context.py), [server/app/config.py:87-92](server/app/config.py), [server/app/agent/santosh.py:1035-1045](server/app/agent/santosh.py)
- In-turn pruning (`prune.py`): every tool_result except the newest step's is cut to head 2,800 + tail 500 chars when over 3,500. This is a projection only; the DB keeps the full result — [server/app/agent/prune.py:1-19](server/app/agent/prune.py), [server/app/agent/prune.py:31-34](server/app/agent/prune.py), [server/app/agent/santosh.py:904-915](server/app/agent/santosh.py)
- Result cap at birth: `_short` caps every tool result at 6,000 chars. Lists are slimmed to 50/25/12/6/3 items with a note, and a hard cut says "ask for less … or save big data with data_fetch and read it with data_read" — [server/app/agent/santosh.py:325-372](server/app/agent/santosh.py)
- Compaction (`compact.py`): before a turn, past 75% → compact now; between 60% and 75% → write a draft in the background. The summary has 7 sections: goal, her exact words, decisions, work done with exact ids/links, problems + fixes, pending, "now". The last 4 exchanges stay verbatim. Each checkpoint builds on the previous one. A "too long" answer forces compaction on the next turn — [server/app/agent/compact.py:1-24](server/app/agent/compact.py), [server/app/agent/compact.py:190-204](server/app/agent/compact.py), [server/app/config.py:96-99](server/app/config.py), [server/app/agent/santosh.py:1670-1674](server/app/agent/santosh.py)
- Data stays in files (DATA DESK): big data is saved as a server JSON dataset (14 days) and the model reads small slices with `data_fetch` / `data_read` / `data_note`. The trigger was a "top 100 repos" job that saw ~2 repos through the 6,000-char cap — [server/app/datasets.py:1-8](server/app/datasets.py)
- Memory fence: auto facts, the work diary and running jobs are scoped to the chat's project (Session) — [server/app/fence.py:1-15](server/app/fence.py)
- Tool exposure per turn: the router admits families once per turn (byte-stable for the prompt cache). `tool_search` can admit more mid-turn, and only admitted families' guides go into the prompt — [server/app/agent/admit.py:1-25](server/app/agent/admit.py), [server/app/agent/santosh.py:960-994](server/app/agent/santosh.py)

### Inferences
- An 80-step turn can grow past the window within itself. After that there is only the one-shot `squeeze`, which cuts this turn's old results to 1,500 chars (`SQUEEZE_RESULT`, [server/app/agent/context.py:40](server/app/agent/context.py)). There is no mid-turn summary and no "clear tool uses" by token threshold.
- No structured external notes file (todo/progress JSON) is maintained for the model to re-read. Re-orientation relies on the GOAL JAARI block plus the chat history and checkpoint.

### Gaps
- Real token sizes of long turns in production are not in the repo (context `reading` is recorded live only).

## 5. Sub-agents (agent team)

### Takeaway
`deploy_agents` runs up to 4 parallel sub-agents per call (8 per turn), depth 1. Each has a fresh throwaway context, at most 8 steps, 1,500 tokens per call, and no thinking. Each returns a free-text deliverable of about 8 lines. Inline crews must finish inside the 260 s tool clock. Background crews are persisted and report through the follow-up and wake path.

### Cited Findings
- Design: parallel sub-agents with their own context and admitted tool subset, the same actor and trust level, no teams spawning teams, throwaway transcripts, with the deliverable plus the event log as the record — [server/app/agent/team.py:1-26](server/app/agent/team.py), [server/app/agent/team.py:53](server/app/agent/team.py)
- Config: `team_max_agents=4`, `team_agent_max_steps=8`, `team_agent_timeout_s=240`, `team_max_tokens=1500`, `team_bg_max_running=2`, `team_bg_timeout_s=1200` — [server/app/config.py:114-120](server/app/config.py). The per-turn total is capped at 8 — [server/app/agent/team.py:311-321](server/app/agent/team.py)
- What a sub-agent gets:
  - a system brief ("FINAL message is your report … max ~8 lines … verify before you report");
  - a first user message with the mission and its task;
  - CORE + the main turn's families + the families it asked for (PC only if the main turn had one);
  - `_THINK_NOW` set to False (no thinking).

  Sources — [server/app/agent/team.py:99-145](server/app/agent/team.py), [server/app/agent/team.py:186-207](server/app/agent/team.py)
- Tool calls inside a sub-agent run serially, with no breaker, no pakka, and no AAGE nudge. The loop ends at the first non-tool_use reply or after 8 steps — [server/app/agent/team.py:194-223](server/app/agent/team.py)
- Return path: inline results go back as one tool result `{"agents": [...deliverable...], "note": "SACH sirf yahi hai … merge"}`, which then passes through `_short` (6,000 chars) like any result — [server/app/agent/team.py:349-364](server/app/agent/team.py), [server/app/agent/santosh.py:1151](server/app/agent/santosh.py). The digest for the log or follow-up keeps 340 chars per agent — [server/app/agent/team.py:276-287](server/app/agent/team.py)
- Inline timeout: `asyncio.wait_for(gather(...), 260)`. On timeout EVERY agent's result is replaced by "time out", including agents that had already finished — [server/app/agent/team.py:333-346](server/app/agent/team.py)

### Inferences
- Sub-agents are much weaker than the main loop: 1,500 tokens, no thinking, 8 steps, no self-check. They suit parallel lookups but not delegated long subtasks.
- The timeout handling throws away finished deliverables. This is a concrete defect. Read the code at team.py:342-346 to confirm.
- No verifier or critic sub-agent role exists. Sub-agents are only workers.

### Gaps
- The background crew's reporting path (`run_background`, team.py:465-540) was only skimmed.

## 6. Verification before "done"

### Takeaway
Verification is light and mostly cheap:
- a free code check for "claims done but only reads ran";
- a 400-token LLM self-check only when ≥3 real tools ran or one failed;
- a post-hoc draft check after the reply is already shown;
- per-domain QA (e.g. doc_studio holds a warned draft once).

`kaam_plan finish done` is accepted on the model's word. Nothing checks that `made` links or files exist.

### Cited Findings
- `_pakka_check`, in order:
  - draftcheck `fake_done` runs only when no goal is open;
  - it then skips if no real tools ran, or if fewer than 3 calls ran with none failing;
  - otherwise one `pakka.self_check` decides: not done + a next step → a "[System self-check] The task is NOT finished yet … Next step:" nudge; claim not backed → a "(Saaf baat: abhi yeh baaki hai …)" line is appended;
  - limit: 2 checks per turn, 4 in goal mode.

  Sources — [server/app/agent/santosh.py:1455-1495](server/app/agent/santosh.py), [server/app/agent/pakka.py:41-43](server/app/agent/pakka.py)
- The self-checker sees the request, the last 20 calls (ok/error + the first 220 chars of each result) and the final message, and returns JSON done / missing / next / claim_ok. It runs on the cheap brain if configured, else `anthropic_model`, at max_tokens 400 with a 30 s timeout — [server/app/agent/pakka.py:365-424](server/app/agent/pakka.py)
- Failure ladder: on a tool failure, past "lessons" (failed → fixed pairs) are attached. Otherwise a web search for the fix runs (2 per turn, 6 in goal mode), plus docs in goal mode. The user sees "Yeh raasta nahi chala — ek doosra tareeka try karta hoon…" at most once per 45 s — [server/app/agent/pakka.py:282-355](server/app/agent/pakka.py)
- Draft check: a free in-turn "claim with nothing behind it" check, plus one cheap-brain check AFTER the reply is on screen for unsupported hard facts or missed parts. It appends a note and never rewrites — [server/app/agent/draftcheck.py:1-22](server/app/agent/draftcheck.py), [server/app/agent/santosh.py:806-810](server/app/agent/santosh.py)
- `goal.finish` builds the 4-part report (kya hua / kya bana / kya baaki / aapka) from step states plus `made` strings plus link regexes in step notes, with no existence check — [server/app/agent/goal.py:243-305](server/app/agent/goal.py). The `made` schema only asks for "real ones from tool results" — [server/app/agent/goal_tools.py:36-37](server/app/agent/goal_tools.py)
- doc_studio QA: a draft with a QA warn status is held once for a fix (`_HELD`) — [server/app/agent/docstudio_tools.py:127-140](server/app/agent/docstudio_tools.py), [server/app/agent/docstudio_tools.py:228-235](server/app/agent/docstudio_tools.py)
- Tool-pick guard: `pick.py` refuses PC tools that were not in view or not placed by her, data jobs sent to a PC, and app-file analysis on a PC — [server/app/agent/pick.py:1-17](server/app/agent/pick.py)
- Outcome log: every working turn is recorded in `TaskRun` with outcome done / partial / stuck / stopped / talk, plus steps, failures, fixes and seconds — [server/app/agent/pakka.py:426-445](server/app/agent/pakka.py), [server/app/agent/santosh.py:784-803](server/app/agent/santosh.py)
- Quality cards: `python -m app.quality longjobs` reads REAL records (TaskRun, GoalRun, turn_failed events) for the last N hours and reports done_pct. It makes no model call and runs no scripted task set — [server/app/quality/longjobs.py:1-20](server/app/quality/longjobs.py), [server/app/quality/__main__.py:3](server/app/quality/__main__.py). `tools` and `hard` cards exist for tool choice and hard-ask detection — [server/app/quality/__main__.py:63-70](server/app/quality/__main__.py)

### Inferences
- In goal mode (the long jobs) the free fake-done check is switched off by design. Truth then rests on the model's own step ticks plus at most 4 cheap self-checks that see only 220 chars per result.
- "Done = verified" (RCA fix 7) is not implemented. There is no ground-truth check (file exists, link resolves, test passes) before closing a goal.
- The self-check is a weak model with a tiny budget. It is not an independent verifier agent with tool access.

### Gaps
- Whether `cheap_brain()` is configured in production, which decides who self-checks, could not be verified from the repo.

## 7. Human in the loop and progress narration

### Takeaway
The human gates (confirm cards, her taps) live in dispatch and the tools and are unchanged by long-job mode. A goal pauses when a card waits on her and resumes by itself after she answers. Progress reaches her in several ways:
- live `step` events and the work strip;
- a plan card;
- rule-based "say" lines built from tool results;
- prompted 15-30-word narration lines (up to 6 per turn);
- at most 2 milestone pushes;
- a 4-part report on the card, with one short chat line at the end.

### Cited Findings
- Gates: "Nothing here pays, sends or approves anything: every gate (cards, money taps, OTP) stays exactly where it was" — [server/app/agent/goal.py:14-15](server/app/agent/goal.py). Sub-agents run as the same actor, so the same cards apply — [server/app/agent/team.py:19-21](server/app/agent/team.py)
- Waiting on her = an open card whose latest state needs her tap (`events.needs_her`), checked over the last 40 events. The goal pauses and the paused time is not counted — [server/app/agent/goal.py:438-458](server/app/agent/goal.py), [server/app/events.py:59-71](server/app/events.py)
- AAGE never pushes back a line that waits on her ("?", card, tap, OTP, confirm) — [server/app/agent/aage.py:33-38](server/app/agent/aage.py)
- Step events: every tool publishes `step` running / done / error with masked args, plus a `work` entry — [server/app/agent/santosh.py:1144-1162](server/app/agent/santosh.py)
- `say.line_for`: one true Hinglish line pulled from the tool result by rules (counts, hosts, done words), with no model call. It is fed to the live reply and to the narration ask — [server/app/agent/say.py:1-30](server/app/agent/say.py), [server/app/agent/santosh.py:1163-1176](server/app/agent/santosh.py)
- Narration: after each silent tool round (`agent_narrate_every=1`, max `agent_narrate_max=6`) the NARRATE ask is appended to the tool results. It demands two halves (a fact with a real number, then the "now doing" part), 15-30 words, and "line AND next tool in the same reply" — [server/app/agent/santosh.py:1250-1267](server/app/agent/santosh.py), [server/app/agent/goal.py:390-412](server/app/agent/goal.py), [server/app/config.py:58-59](server/app/config.py)
- Ack: a turn that is silent for N seconds sends one ephemeral "Ek second, dekh raha hoon…" line — [server/app/agent/santosh.py:1366-1372](server/app/agent/santosh.py)
- Final: `kaam_plan finish` returns `card_shows` and tells the model to write only ONE short human line in chat (CHHOTA JAWAB) — [server/app/agent/goal_tools.py:113-122](server/app/agent/goal_tools.py)

### Inferences
- In one step the tool results can carry several system texts at once: NARRATE, PLAN_NOW, the AUTO_PLAN note, the steer note, the replan note — [server/app/agent/santosh.py:1237-1316](server/app/agent/santosh.py). RCA cause 6 (competing nudges) is therefore still structurally present. Fix 6, "one nudge per step", was not built.

### Gaps
- Client-side rendering of the work strip and cards (Flutter / console JS) was not read.

## 8. Gaps and weaknesses visible in code, compared with common long-task practice

### Takeaway
Hoola has built many Claude-inspired pieces: plans, background continuation, restart recovery, steering, compaction, data files, and sub-agents. But long-task completion still rests on regex heuristics and prompt nudges, not on externalised state plus ground-truth verification, and there is no fixed eval measuring finish rate.

### Cited Findings
- **Heuristic routing of "big" and "promise"**: `looks_big` and `aage.promised` are regexes over Hinglish/English text — [server/app/agent/goal.py:358-372](server/app/agent/goal.py), [server/app/agent/aage.py:21-52](server/app/agent/aage.py). The server plan is a regex clause split — [server/app/agent/santosh.py:848-870](server/app/agent/santosh.py)
- **Fixed caps**: 24/80 steps, 48/150 calls, 900/2,700 s per turn, 6 rounds / 180 min per goal, 15 plan steps, 8 goal nudges, 2 AAGE nudges, 2/4 self-checks — [server/app/config.py:16-41](server/app/config.py), [server/app/agent/breaker.py:15](server/app/agent/breaker.py), [server/app/agent/goal.py:36](server/app/agent/goal.py), [server/app/agent/aage.py:17](server/app/agent/aage.py), [server/app/agent/pakka.py:41-43](server/app/agent/pakka.py)
- **No ground-truth "done"**: `finish done` is not checked against artifacts — [server/app/agent/goal.py:284-305](server/app/agent/goal.py). The fake-done check is disabled in goal mode — [server/app/agent/santosh.py:1462-1467](server/app/agent/santosh.py)
- **No independent verifier agent**: the self-check is a 400-token, no-tool call seeing 220 chars per result — [server/app/agent/pakka.py:376-424](server/app/agent/pakka.py)
- **No in-turn compaction**: the checkpoint summary runs only before a turn; in-turn there is only prune + net + one squeeze — [server/app/agent/compact.py:9-14](server/app/agent/compact.py), [server/app/agent/context.py:7-13](server/app/agent/context.py)
- **No external progress or notes file for the model**: state = the GoalRun steps (strings + notes) and the chat history. No persisted todo with acceptance criteria and no scratchpad the model writes and re-reads — [server/app/agent/goal.py:57-74](server/app/agent/goal.py)
- **In-memory turn state**: `_PROGRESS`, `_LONG_TURN`, `_stopped`, the steer `_Q`, the goal `_STOPPED` and `_PENDING` live in the process. A restart loses the breaker counts and the steering queue; recovery restarts from plan + history after 600 s idle — [server/app/agent/santosh.py:263-266](server/app/agent/santosh.py), [server/app/agent/steer.py:22](server/app/agent/steer.py), [server/app/agent/goal.py:41-47](server/app/agent/goal.py), [server/app/agent/goal.py:695-706](server/app/agent/goal.py)
- **Weak sub-agents + a timeout defect**: 1,500 tokens, no thinking, 8 steps, no self-check; a timeout discards finished deliverables — [server/app/config.py:114-117](server/app/config.py), [server/app/agent/team.py:207](server/app/agent/team.py), [server/app/agent/team.py:342-346](server/app/agent/team.py)
- **Narrow parallelism**: only 11 read-only tools may run concurrently, and a mixed batch runs fully serially — [server/app/agent/santosh.py:684-689](server/app/agent/santosh.py), [server/app/agent/santosh.py:1219-1221](server/app/agent/santosh.py)
- **Competing nudges still possible** in one step (see section 7); RCA fix 6 not built — [docs/LONG_TASK_RCA.md:124-125](docs/LONG_TASK_RCA.md)
- **No finish-rate eval**: `longjobs` only reports real past records. The RCA's "20 real multi-step asks scored on finished / stopped / false-stuck" card was not found in `server/app/quality/` (files: asks, code_tasks*, hard_asks, longjobs, review_tasks, tool_asks, toolchoice…) — [server/app/quality/longjobs.py:1-20](server/app/quality/longjobs.py), [docs/LONG_TASK_RCA.md:128-129](docs/LONG_TASK_RCA.md)
- **Opus not used for long jobs**: `model_for` gives the hard model only when `not long_job` — [server/app/agent/santosh.py:398-404](server/app/agent/santosh.py)
- **Too many tools are still visible per turn**: 56 tools on a plain "hello" after v0.314 (from 65); strict schemas and usage examples are not done — [docs/HISTORY.md:11834-11840](docs/HISTORY.md)
- **Mostly not verified live**: v0.314's own note says "Not verified on a live model here" — [docs/HISTORY.md:11839-11840](docs/HISTORY.md)

### Inferences
- What is strong compared with common practice:
  - restart-safe goals in the DB with auto-recovery;
  - asking for "Aage badhaun?" on budget exhaustion instead of failing;
  - mid-job steering at step boundaries;
  - pausing on human cards with resume-by-itself;
  - data-in-files for big results;
  - Claude-style compaction between rounds;
  - a per-turn outcome log.
- The main structural differences from the Claude Code / Devin / Manus style: no model-maintained todo or progress artifact with checkable acceptance; no verify-against-ground-truth loop; caps that do not scale with the task; and no offline benchmark of long-task finish rate.

### Gaps
- No production numbers (done_pct from `longjobs`, STATS_LONG counters, breaker STATS) are stored in the repo, so actual finish rates cannot be stated.
- Tests (e.g. `server/tests/test_v0311_aage_badho.py`, `test_v0226_long_jobs.py`, `test_v0228_long_jobs_b.py`, `test_v0242_compact.py`) exist but were not read or run in this pass.
