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

## 6. Status after G7 (11 Nov 2026)

- **On by default.** `chat_graph` defaults to True: every chat turn, wake turn, long-job round and call brain ask runs
  on the turn graph (`agent/turngraph.py` + `turnrun` / `toolledger` / `turnfacts` / `turndeliver` / `turnchannel`).
  The test suite runs on the graph path by default too (conftest pins nothing); tests of the old path set
  `CHAT_GRAPH=false` themselves. The server log says which engine answers at startup (`chat turn engine: ...`) and
  `/api/agent/stats` carries `turn_engine` (`graph` / `old-loop`).
- **Rollback switch.** `CHAT_GRAPH=false` in the VPS `.env` + `pm2 restart santosh --update-env` brings back the old
  while-loop exactly as it was before G0 (`santosh._steps_inner`, marked as the rollback path; every G1-G6 branch is
  behind the same switch). Nothing from G0-G6 had run live when G7 flipped the default, so the old loop is kept.
- **langgraph missing.** If `langgraph`, `langgraph-checkpoint-sqlite` or `aiosqlite` is not installed, `Settings`
  forces `chat_graph` off (one loud ERROR line per process) and every turn runs on the old loop; `turngraph.run_steps`
  has the same fallback as a second belt (also said once).
- **app/aep.** The `POST /api/aep/turn` lane (`agent/aeptune.py`, v0.680 HOOLA ADOPT, broken on every real call) is
  retired with its suite (`test_v0610_hoola_adopt.py`). Kept: `aep/graph.py` (used by `leads/scale.py`), the tracer +
  vault sink (`/api/aep/runs`, `/api/aep/runs/{id}`, `/api/agent/stats`) and the rest of the package with its own
  suites; `aep/agent.py`, `aep/hub.py` (`hoola_brain_factory`), `aep/middleware.py`, `aep/retrieve.py` and
  `aep/audit.py` have no product caller any more and can go in the cleanup step.
- **What remains (not done in G7):**
  1. *Delete the old loop* once the graph has run live for a while: the `while` loop in `santosh._steps_inner` and the
     old-loop branch of `santosh._steps`; the `chat_graph` checks and their `else` paths in `santosh.run_turn` /
     `_run_turn` (the plain per-chat lock without tickets, Stop without `turnrun`), `turn_inbox` (the `RESUME_NOTE`
     re-run), `goal._continuation` (a fresh turn per round), `kaam_followup` (`_recent_said` / `_answered_since`
     timing), `voice` (the `LAST_OUTCOME` / `_late_result` path without a ticket, the spoken-claim regex without
     facts); the `chat_graph` setting and its langgraph probe; tests that pin `CHAT_GRAPH=false`. A turn with no
     conversation id of its own (`run_steps` fallback) needs a thread of its own first.
  2. *Regex claim detection*: `draftcheck.all_claims` still FINDS the claim sentences; only the verdict comes from
     the facts (G3).
  3. *Approval cards* are still non-parking (the tool returns "card created"); the plan's `interrupt()` per card is
     not built.
  4. *Call direct tools*: the tools Gemini Live calls itself on a call (not through `santosh_kaam`) still run outside
     the graph and its ledger.
  5. *Live*: none of G0-G7 has been seen on a real turn on the VPS yet.

## 7. Status after G8 (12 Nov 2026)

Built (items 3 and 4 of section 6), each behind its own switch on top of `chat_graph`:

- **Approval cards park the graph** (`graph_card_park`, default on; `agent/turnpark.py`). A graph run whose tools made
  a card she must tap - a bazar confirm card (orders, payments, and every connector's ask-first change: Drive / Forms /
  Calendar / Photos / mail label deletes, bulk and public changes) or an email draft / forward card - answers as today
  ("tap Approve"), then `finish` routes to `deliver` -> `park` instead of END. `deliver` tells the reply once (G5,
  outcome `waiting`) and writes one `turn_card_parks` row per waiting card (card kind + id, the tool_use id, the tool,
  its argument hash, the chat's newest message id); the `park` node calls LangGraph's official `interrupt()`, so the
  checkpoint holds the pending interrupt. The inbox row says `waiting_tap` (the restart sweep never re-runs it, the
  inbox housekeeping never deletes its thread).
  Her tap runs the action EXACTLY as before (the card's route: bazar's claim-once conditional update, money only on her
  tap, nothing auto-approved). Only after it ran, the card's code calls `turnpark.answered(kind, id, answer, result)`
  (bazar.decide; mailbox.send_draft for her Send; the cancel route for Not now; bazar.expire_approvals for expired /
  interrupted): the park row is claimed `waiting -> answered` by one conditional UPDATE, and the card's own chat line
  ("'X' is done.") is not written. `resume_due` then runs ONE ordinary turn of the chat (actor `approved:card` = her
  tap's authority) through `santosh.run_turn` - its G2 ticket, so a tap while the chat runs another turn waits behind
  it and never runs a second run on the chat. That turn's history-only line says what she answered; its graph run
  resumes the parked thread with `Command(resume=...)`. The park node records the answers as G3 facts (done -> did,
  failed -> failed, declined -> skipped, unknown -> ambiguous) and sends the job back to `model`, which continues the
  SAME job from that step (the parked tool_use already has its tool_result - "card created" - and the resumed request
  ends on the user line, so `_api_ready` holds). The result is delivered by that run's own G5 record, once.
  Answers: done / failed / declined (the model is told not to retry, and the ledger runner refuses the same tool +
  arguments in that thread) / unknown (bazar 'interrupted') / expired / replaced. Expired and replaced never wake the
  model: the row closes and, with nothing else waiting, the thread (checkpoint + ledger) is deleted and the inbox row
  goes `done`.
  - *Two cards in one run*: the run parks on all of them. Each answer resumes once; the resume line carries every
    answer claimed at that moment and names the cards still waiting; a resumed run that ends with cards still waiting
    parks again on those. The job never waits for the slowest card and no answer is told twice.
  - *TTL*: `graph_card_park_ttl_h` = 26 h. A bazar card expires by itself at `ask_ttl_hours` (24 h) and that closes
    its park first; an email draft has no expiry of its own, so the TTL closes its park (the draft stays tappable as a
    plain card - a later Send just sends, as before G8). The worker's `card_park_jobs` slot (every 15 s) closes them
    and also resumes an answer whose resume a restart cut (answered > 60 s ago, or `resuming` > 30 min).
  - *Restart while parked*: the checkpoint and the park rows are on disk; a tap after the restart resumes the thread.
  - *Not parked (today's behaviour)*: the old loop, a call's brain ask (channel `call` - the call tells its own cards),
    a stopped run, a long job whose turn routes to `carry` (G4 keeps the job's rounds), a run whose checkpointer could
    not open. `answered()` then finds no row and the card's code says its own line.
- **Call direct tools on the ledger** (`graph_call_tools`, default on; `agent/calltools.py`). The tools Gemini Live
  calls itself (declared in `VOICE_TOOL_NAMES`, not via `santosh_kaam`) run through `santosh._run_tool` (new optional
  `dispatch_fn` = the call's own dispatch), with toolledger rows on the thread `<chat>:call` (a split call's record maps
  to its chat, so a re-dial after a restart is the same thread). The NEWEST changing row decides: the same tool + the
  same arguments already `done` within `graph_call_tools_window_m` (30 min) -> not run again (the stored result + a
  plain note); still `intent` (a restart cut it) -> the honest "may already have run" error; still running here ->
  "already running". Anything in between (light on / off / on) runs normally; look-ups skip the ledger. No model step,
  no wait: one small row before a changing tool and one after it. Each direct tool's outcome is one G3 fact (did /
  card / read / failed / ambiguous) kept per `did` entry: the spoken "ho gaya" check judges by it (a draft card is not
  "sent") and the receipt in the chat after hang-up lists a card as "waiting for your tap"; the receipt is made once
  through a G5 record `call:<call id>:receipt`. Gemini audio / session / parking / billing / persona / the declared
  tool list / `VOICE_TOOL_BUDGET` / every schema untouched.

Not built: parking for the other card kinds (every desk's own `CARD_KINDS`, ask_forms, operator asks, studio price
cards, pg_write cards - each has its own decide path; adding one = a `card_of` / `still_waiting` branch + one
`answered()` call in its decide code); a resumed run for an email whose Send was scheduled / in the undo window is told
"done - scheduled" at her tap, and a later failure of the worker's send is not fed back into the job; an answer that
lands while the first resume of the same thread is running is resumed after it (by a fresh run when the thread had
already ended).

NOT VERIFIED live: no real card tap has resumed a parked run on the VPS, and no real call has re-issued a direct
tool through the ledger. Everything above is tested with a scripted brain, the real bazar demo pack and real rows
(`tests/test_g8_turngraph.py`).

## 8. Status after G9 (12 Nov 2026)

Built (owner: "GO BOTH"), each behind a switch:

- **Hoola Code's honest "done" + its end notice told once** (`dev_truth`, default on; `devsahayak/truth.py`). Hoola
  Code has its own engine and never runs on the turn graph, so G3 / G5 are reused by SHAPE, not by node. Why a
  devsahayak-side fact builder instead of `turnfacts.step_facts` / `verdicts`: those read a chat tool_use + its
  tool_result + its G1 ledger row and judge a claim through `draftcheck.family_of` (send / book / pay tools); a coding
  round has none of them. Its facts are read from the task row in turnfacts' fact shape ({id, tool, step, effect,
  ledger, object, error}, effect did / failed / ambiguous / stopped): every test-like command the session ran in the
  box with its exit code (the structured `steps`; the LAST run decides; a timeout is ambiguous), the local lab check
  (`proof`), the files changed, the push (`head_sha` + `branch`), the PR object (`pr_number` / `pr_url`), CI's state
  (`ci`: success / failure / still running), her Stop. The model's `explain` / `test_plan` are only searched for WHAT
  is claimed (tests pass / PR ready / pushed / fixed; plans, questions and hedges such as "should pass" are not
  claims; `pr_open` itself claims "the PR is ready"), and each claim gets G3's verdict words from the facts only (true
  / failed / unknown / stopped / none). The task card carries `truth` {confirmed, claims, line}; `tell_end` says "The
  pull request is open, but not everything is confirmed. Not confirmed: 'tests pass' - the last test run failed (exit
  code 1)." (end `needs_you`) instead of "ready" when a claim is not backed. The notice goes through
  `turndeliver.once(key, "push", ...)` with the key `devsahayak:<task>:r<rounds>.<ci_round>.<self_round>:<status>:<head
  sha>` (kind `dev`; turndeliver needed no change - its record takes any key): a repeat call, a run resumed by
  `_resume_cut_runs` that ends in the same state, a restart between intent and sent - none tells it again; a new round
  / CI fix round / own-review round / push is a new key, told once. Off = tell_end and task_view exactly as before.
- **Video Studio / Create price cards park the turn graph** (under the existing `graph_card_park`). `turnpark.card_of`
  knows the studio card (`waiting_owner` "sa..." + a rupee price; the result now also names its `project`),
  `still_waiting` reads the approval from the project's JSON (tenant from the run - `turngraph._note_card` now puts
  the run's tenant on the card - or from the park row; project from the result or the tenant's list), and
  `studio.service.decide` / `expire_asks` call `turnpark.answered("studio", id, ...)` AFTER the action ran: declined
  (Not now: nothing made, nothing spent), done (she approved; for the background jobs - keyframes, character paint,
  music, paint-then-generate - the result text says the work is being made and is NOT ready yet, so the resumed model
  never claims it finished), failed (the error), expired. The one chat line the card's code writes itself (the flux
  character photo "ban gayi") is suppressed only when `answered()` returns True. Her tap still runs the action exactly
  as before; nothing is auto-approved; the money ceiling and fingerprint are untouched.

Found: **Hoola Interactive and Hoola Vocal make no approval cards** (grep of `app/interactive/` and `app/vocal/`: no
approval / pending / card publish; only consent flags on a face / voice). **Hoola Cinema has no chat tool**: its
confirm step is `confirm=true` in the body of the page's own Create button (`cinema/api.py`), nothing waits for a tap
after a chat tool call - so nothing to park; skipped.

Not built: the claim words are still found by regex (as in G3); CI that is still running leaves "tests pass"
`unknown` until the next round end (the CI watcher's own card is unchanged); a studio background job that later fails
is not fed back into the resumed job (its own card + note say it, as before); the other card kinds listed in section 7
(desk `CARD_KINDS`, ask_forms, operator asks, pg_write) still do not park.

NOT VERIFIED live: no real Hoola Code round has been judged on the VPS, and no real studio price card tap has resumed
a parked run. Tested with a scripted brain, real DevTask rows and the real studio approval JSON
(`tests/test_g9_turngraph.py`, 11 tests).
