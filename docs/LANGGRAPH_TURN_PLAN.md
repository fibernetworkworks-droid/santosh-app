# Hoola chat turn on LangGraph — research + plan (10 Nov 2026)

Owner: "OUR PRODUCT IS IN DEVELOPMENT ... FIX THIS ALL NOW WITH LANGGRAPH ... DO DEEP RESEARCH, FIND THE HOOLA ISSUES
AND FIX THIS PERFECTLY". Three read-only research passes (the turn pipeline, the bug history, the in-house AEP engine)
are summarised here. Read this before touching `agent/santosh.py` or `app/aep/`.

## 1. What a chat turn does today (agent/santosh.py)

One turn = `main.post_message` -> `turn_inbox.run_owned` -> `run_turn` (S:2824) -> `_run_turn` (S:2850, 397 lines)
-> `_steps` -> `_steps_inner` (S:1908, 641 lines, one while-loop with ~10 exits and a while-else). Stages:
pre-lock short cuts (operator OTP, research plan gate, approval words, ID locker, place, goal reopen, stop words)
-> per-chat asyncio lock + steer queue -> worker notes -> compaction -> save her row -> history load + repair ->
memory block -> deadline (900 / 1200 / 2700 s) -> tool admission + system prompt -> LOOP { model call with brain
fallbacks / retries / thinking / effort -> hard-answer hold + review -> plain check (false-done) -> nudges (goal,
promise, plan, narrate, max_tokens) -> tools (breaker, parallel-safe set, timeouts, steer, auto-plan) } ->
outcome + LAST_OUTCOME + diary -> after-turn memory, title, goal continuation round. State is an untyped dict of
~40 keys plus ~15 module globals (`_locks`, `_STOP_AT`, `LAST_OUTCOME`, `_PROGRESS`, steer `_Q` ...) and ~8
contextvars that are set and never reset.

## 2. The issues (13 recurring bug classes, each patched more than once)

| # | Class | Examples | Why the patch is fragile |
|---|---|---|---|
| 1 | Turn not durable (restart / deploy / timeout) | v0.226, v0.343, v0.442, v0.653, v0.657, v0.672 | resume by notes + timestamps + a "did a final reply land" guess; every kind of work has its own resume |
| 2 | Result told late / twice / never / wrong chat | v0.260, v0.552, v0.553, v0.657, v0.714, v0.722 | five delivery paths, each with its own "already told?" timing logic |
| 3 | False "done" | v0.287, v0.655, v0.662, v0.672 w5 | judged by regex on the reply's words (Hinglish + English lists) |
| 4 | Turn ends on text / promise without action | RCA A1, A4, v0.314, v0.727 | regex nudges, max 2; survival depends on the model calling kaam_plan |
| 5 | Caps and timeouts are guesses | RCA A2/A3, v0.705, v0.696 | constants that change with plan / goal / lane; kill instead of pause |
| 6 | Two turns on one chat | v0.637, v0.662, v0.672 w6/w7, v0.649 | in-process lock taken on some paths only; inbox separate from lock |
| 7 | Approval card state outside the turn | v0.651, v0.657, v0.704, v0.723 | alias tables, `_CARD_ASKED` global, text blocks rebuilt per prompt |
| 8 | Stop is not a state | v0.649, v0.662 | stop words by regex, then cancelled job kind by job kind |
| 9 | Side effects repeat | v0.672 w6, v0.657 | dedupe bolted onto each tool / channel |
| 10 | Call and chat are two engines | v0.442, v0.624, v0.630-633, v0.660, v0.692 | every feature wired twice |
| 11 | Prompt building slow / cuts history | v0.637-645, v0.702, v0.723, v0.724 | blocking reads on the loop, 50-57k char system prompt |
| 12 | Many models in one chat | v0.630, v0.631, v0.643, v0.710, v0.736 | per-call routing + SDK-door rewrites |
| 13 | Other chats leak in | v0.711, v0.714, v0.722 | scope added query by query |

Out of scope (not the engine): model quality, third-party outages / billing, CSS, voice audio, domain tools, prompt
wording.

Code risks found on the way: contextvars leak into background tasks; process-wide switches flip off for ever on one
refusal (`THINK["ok"]`, `EFFORT["ok"]`, `_ts.NATIVE`); `run_turn` never raises so the inbox marks failed turns done;
the shown text and the saved text can differ; a reply is published before `_pakka_check` can send the model back to
work; rejected drafts and nudges are saved as real history; tool timeouts do not stop the work behind them.

## 3. The engine decision: official LangGraph, not the in-house AEP copy

The in-house copy (`app/aep/`, 11.9k lines, 384 tests, "230/230 parity") is NOT production-capable:
`astream` is a sync generator (fails `async for`), the async walk skips the checkpointer, `interrupt()` breaks under
`to_thread`, fan-out and tool calls run one after another, no cancellation, the model adapter drops tool calls and
tool results (lossy), `bind_tools` is unimplemented, and the only live lane `POST /api/aep/turn` fails on every real
call (async runner given to a sync `_generate`; its tests only used a sync fake). Fixing it is several weeks.

Official `langgraph` 1.2.x (MIT, pip-installable here) already has: native async graphs, `astream` with
`stream_mode` "custom" / "updates" / "messages", per-node pending writes in the checkpoint (a crash re-runs only the
unfinished node), `interrupt()` / `Command(resume=...)`, `AsyncSqliteSaver` / Postgres savers, recursion limits,
task cancellation. We use the GRAPH ONLY - no LangChain model or tool wrappers: the model node calls Hoola's own
`_call_brain` with Anthropic-format message dicts (lossless; Hoola's history format IS the state), and the tool node
calls Hoola's own `_run_tool` (so approvals, money-on-her-tap, redaction, logging stay in one funnel).

## 4. The new turn (the graph)

```
START -> intake -> prepare -> model -> route
           |          ^         |-- tool calls --> tools -> model
           |          |         |-- draft needs a check --> check -> (fix -> model | finish)
           |          |         `-- final text --> finish -> END
           `-- short answer (stop / approval / OTP) --> finish
```
- **State** (typed): conversation, tenant, actor, messages (Anthropic dicts), plan/todo, budgets (steps, cost, deadline),
  tool ledger, outcome, notified flag, stop flag. Replaces the 40-key dict + module globals.
- **Checkpointer** per conversation thread (thread_id = conversation id). Resume after a restart = re-enter the graph.
- **Tool ledger**: intent (tool_use id + idempotency key) written before a tool runs, result after; an intent with no
  result on resume = "ambiguous", never re-sent automatically (fixes class 9).
- **Done = a state transition** checked against the ledger and the plan, not regex on words (class 3, 4).
- **Budgets** run out -> checkpoint + "continue?" question, never a kill (class 5).
- **One run per thread**; new messages queue as thread input; Stop = a thread flag checked at every node boundary +
  task cancel (class 6, 8).
- **Outcome + notified** live in state; one delivery node (class 2).
- **Approval cards** stay non-parking at first (the tool returns "card created"); later an `interrupt()` per card (7).
- **Voice** becomes a channel over the same thread (class 10), last.

## 5. Phases (each behind `chat_graph`, default OFF; old path untouched until G7)

| Phase | What | Done when |
|---|---|---|
| G0 | langgraph dependency; typed state; nodes intake / prepare / model / tools / finish reusing santosh helpers; SQLite checkpointer; switch `chat_graph`; parity tests (fake brain: same saved rows + SSE events as the old loop) | a plain chat + a tool turn behave the same on both paths |
| G1 | durability: resume from checkpoint after a kill; tool ledger + ambiguous state | killed mid-tool test resumes without re-sending |
| G2 | one run per thread + queue; Stop as state | two messages / Stop during prep / Stop mid-tool tests |
| G3 | done-truth from ledger + plan; nudges folded into the check node | false-done suite passes without regex |
| G4 | long jobs = the same thread continuing (goal rounds removed) | restart mid long job continues from the step |
| G5 | outcome + single delivery node | told-once / right-chat tests |
| G6 | voice as a channel | call reaches every tool via the same graph |
| G7 | default ON, delete the old loop; retire `app/aep/` or keep only what is used | old suites green on the graph path |

Not verified by this plan: anything live. Each phase ships with its own tests and the old path stays the default
until G7.
