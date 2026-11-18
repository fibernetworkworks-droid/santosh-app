# Hoola chat today vs Claude (code audit, repo at v0.997.0, 18 Nov 2026)

Read-only audit. file:line references are under `server/app/` unless a path says otherwise. The live server's `.env` was not
visible; live facts: healthz `chat_brain glm:openrouter:qwen/qwen3.8-27b`, `pipeline_on` set on the VPS.

## 1. Parity switches (config.py) - all default ON, conftest turns them off for old suites
chat_one_model 443, chat_small_prompt 270, chat_core_tools 302, chat_work_in_turn 331 (1200 s / 200 calls),
chat_answer_only 589, chat_plain_loop 662, chat_thinking_adaptive 109, chat_artifact_direct 495, chat_one_memory 275,
chat_every_message 638, chat_files_by_code 636, chat_graph 641 (LangGraph turn), chat_model_choice 603 (per user, not per
chat), chat_context "claude" 1M 278-281, chat_compact 292-295. console_v2 507 turns sessions / projects / stream / side
panel on.

Pipeline (the Box): pipeline_on False by default, ON on the VPS; pipeline_holdout_pct 10.0 (628: 1 in 10 one-part messages
run the old routing); pipeline_fix_round True (618); pipeline_receipt True (623); pipeline_background True (621).

## 2. One console message, today
- Entry: POST /api/conversations/{id}/messages (main.py:927-952) -> turn_inbox.run_owned -> santosh.run_turn
  (agent/santosh.py:3220-3313): ticket, cost meter, watch clock, **turnbox.begin** (the Box picks kind / level / model),
  _run_turn, turnbox.end + fix_round.
- Console appends `[Web console language preference: Reply in English ...]` to every message (static/console/v2.js:35).
- Before the model (_run_turn 3316+): her dropdown model re-sets MODEL_NOW (3327-3334), usage budget canned refusal,
  OTP / CAPTCHA and PC-question answered from chat, locker capture, goal reopen, stop words (model still replies),
  steering a running job (her message may get no reply of its own, 3530-3533), worker notes + place note prepended,
  compaction, 5 s "One second, looking into it..." ack, memory "since your last reply" note (<=1,800) + goal / PLAN_FIRST
  + time line on her newest message, Box P3 parts run first.
- System prompt (small mode): core_prompt CORE 7,912 + files 455 + pages 330 + KAAM TIPS 1,196 + THIS CHAT <=3,500
  = ~10-13.5k chars. Old ~50-60k prompt only for calls / routines. Per-turn notes ride on her message.
- Tools: ~21 core (agent/core_tools.py:25-47) incl. BOTH `artifact` and `artifact_make` (overlap), families by whole
  words, tool_search native only on Claude.
- Model (_turn_model 2250-2393): Box pick `openrouter:<model>`; holdout / PC / studios run the old way, where a long or
  hard ask switches to Claude if a key exists; pictures / PDFs to Claude; the Box can hand a call to a backup model
  mid-message and keeps a model per chat+kind+level for 30 min. **One message and one chat can use several models.**
- Prompt caching only on the Claude path; none found on OpenRouter.
- Loop (graph prepare -> model -> check/tools -> finish -> deliver): plain check retracts a false action claim and asks
  again; max_tokens continuation; goal nudge (open kaam_plan step, up to 8) + promise nudge; narration lines; auto plan;
  step-24 extension.
- After: ledger event (steps fold), pakka / procedures learn, yaad facts + "Yaad se" note, auto title,
  goal.maybe_continue background rounds (up to 6 rounds / 180 min), Box final check -> "Made with ..." receipt, and a
  failed check posts a **separate correction message** (source box_fix) from a model one level up (turnbox.py:452-519).
- Streaming: livereply delta events, SSE /events?live=1, Pacer ~1 word / 20 ms; /live snapshot for reloads.

## 3. Shown with a reply that the model did not write
Ack line; ledger (in the fold); in-reply correction lines (SAID_*); Gyaan "(Dhyaan: ...)" note appended even with
answer_only (gyaan/answer.py:78-101) + Sources card; Box receipt + box_fix message; memory_used / memory_saved / procedure
cards (phone); plan card incl. the server-written auto plan; compaction card; canned lines ("Changing my approach...",
breaker stop, step cap "This task has become long...", "Done." / "Sorry, I did not understand..." when the model said
nothing, timeout / error); follow-ups: wake-turn reports, one-shot / canned job result lines, kaamwatch started /
progress / stuck / stale lines, restart recovery line, goal continuation rounds.

## 4. Answered without the model
Usage refusal; OTP / CAPTCHA; PC-question; steering (no reply); duplicate; STOPPED_IN_PREP; canned timeout / error /
breaker / cap / silent lines; job results by a one-shot or canned line (kaam_followup.py:609-636).

## 5. Long work
In-turn for her own chat turns (1200 s, crews inline up to 900 s, research in the turn) - BUT goal mode still makes
background rounds when steps are left, and video / app / site builds / vendor research report later through kaamwatch ->
kaam_followup wake turns.

## 6. Gaps vs Claude.ai
- One model: broken by the Box (per message, hand-over, holdout, fix round on another model), Claude switch, PC / media.
- Thinking: the console's "thought for Ns" fold is dead code (v2.js:1059 thinkEvent only updates the progress label;
  THINKS is never filled; verified). Thinking is never stored, lost on reload. Phone shows a Soch card.
- Retry only on the newest reply, blocked while working (v2.js:1117, 1146). Edit / branches present.
- Artifacts: `update` not streamed (livereply.py:293); two overlapping artifact tools in the core list.
- Memory: background fact extraction + "Yaad se" notes still run.
- Projects: project files not in small mode, no project search tool.
- Styles: none; one fixed rulebook; console forces English on every message.
- Citations: Sources card only for Gyaan; web answers have text links only, no "searched N sources" row.
- Prompt cache: not on OpenRouter.
- Answer-only not complete: Dhyaan note, Box receipt + fix message, canned lines, follow-up / kaamwatch lines.
