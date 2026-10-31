# Long tasks: how Claude does it, and why Hoola fails (31 Oct 2026, checked on v0.310.0)

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

### 5. Production brain = GLM / OmniRoute, not Claude (read in code + HISTORY)
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
