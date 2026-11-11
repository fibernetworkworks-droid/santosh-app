from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings come from environment variables or a .env file (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Santosh brain (Claude API) ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    usage_month_usd: float = 0.0           # v0.98 server ceiling of AI spend per owner per month (0 = none)
    studio_modes: bool = True             # v0.782 TEEN MODE: Studio Plan / Chat refuse changing tools on the server
    studio_design_questions: bool = True  # v0.784 SAWAAL CARD: up to four visual design questions before a Studio Build
    app_engine: bool = True               # v0.814 APP ENGINE 1: React apps built in the box (L8); off = the tool + routes refuse
    app_engine_previews: int = 2          # v0.814 app builds at once on this server (the plan's decision 1: start at 2 on her VPS)
    app_engine_runner: str = "box"        # v0.814 "box" = Docker, no network (production); "local" = host node (dev / tests only)
    site_quick_checks: bool = True        # v0.789 CHHOTA BADLAAV: a one-section change is checked on its own page only
    studio_chat_model: str = ""            # v0.782 Chat mode may run on a cheaper model ("" = the turn's normal model)
    chat_turn_cost: bool = True           # v0.777 CHAT JAISA: each chat turn's rupees kept (turncost) for the Studio line
    usage_usd_inr: float = 88.0            # v0.98 rupees per dollar for the Kharcha screen
    agent_max_steps: int = 24              # v0.78: more room to finish (the circuit breaker still stops loops)
    agent_max_tokens: int = 2000
    chat_heal_ai: bool = True              # v0.158 after a call, a cheap model judges if its cards were relevant
    agent_self_check: bool = True          # v0.78 Pakka kaam: check the real results before saying done
    draft_check: bool = True               # v0.223 Draft jaanch: the last look at a reply (free in code + one
    draft_check_max_hour: int = 4          #   small check after the words are out); notes per chat per hour
    memory_recent_facts: int = 15          # v0.605 JUST IN TIME: newest unpinned facts in the prompt (was 40; the rest via yaad_khojo)
    memory_auto: bool = True               # v0.108 lasting facts picked after her turns ("yaad rakha" chip)
    agent_fix_search: bool = True          # v0.78: a failed step with no known fix -> search the web for the solution
    agent_tool_timeout_s: int = 300         # a tool that hangs never blocks a chat turn longer than this (browser waits go up to 270 s)
    agent_turn_timeout_s: int = 900         # a whole turn never holds the chat lock longer than this
    # v0.186 Lamba kaam pakka (goal mode): these apply ONLY while a kaam_plan goal is open; short jobs keep today's numbers
    agent_goal: bool = True                 # goal mode on: the turn does not stop on text while goal steps are open
    agent_goal_max_steps: int = 80          # model steps in one goal turn (vs 24)
    agent_goal_max_calls: int = 150         # breaker max_calls while a goal is open (vs 30)
    agent_goal_turn_s: int = 2700           # turn timeout while a goal is open (vs 900)
    agent_goal_max_tokens: int = 16000      # per model call while a goal is open (v0.331: 6000 -> 16000 - thinking tokens count here)
    agent_long_effort: str = "xhigh"       # v0.331 Claude effort for long jobs (Anthropic: xhigh = agentic work over ~30 min); '' = model default
    agent_hard_effort: str = "high"        # v0.331 Claude effort for a hard reasoning ask (agent/hard.py); '' = model default
    agent_long_on_claude: bool = True       # v0.331 a long job's calls go to Claude even when CHAT_LLM picks a cheaper brain
    agent_hard_model: str = "claude-opus-5-5"   # v0.429 SOCH KE JAWAB 2: a hard reasoning ask runs on the strongest model ('' = anthropic_model)
    hoola_operator_tenant: str = "default"   # wave 9: the tenant that owns the server's AI key (only it is told to recharge Anthropic)
    claude_one_model: str = "claude-haiku-5-5"   # v0.631 SAB HAIKU (owner: "DO EVERY THING HAIKU FOR NOW --- SIMPLE TO HARD"): EVERY Claude call in Hoola runs on this model, whatever it asked for ('' = each part uses its own model again)
    chat_simple_model: str = "claude-haiku-5-5"   # v0.630 HAIKU DIMAAG: an ordinary (not hard, not long) ask runs on Haiku ('' = anthropic_model); a failure answers on Sonnet
    agent_hard_max_tokens: int = 16000      # v0.429 per call for a hard ask (thinking counts; 2000 cut the answer)
    agent_hard_on_claude: bool = True       # v0.429 a hard ask goes to Claude even when CHAT_LLM picks a cheaper brain
    agent_goal_rounds: int = 6              # background continuation turns per goal (v0.473: 3 -> 6; resumes after her tap are free)
    agent_goal_minutes: int = 180           # WORKING minutes of one goal (v0.473: 60 -> 180; time waiting on her never counts)
    agent_goal_resume: bool = True          # v0.473 a goal paused on her tap / OTP / answer restarts by itself once she answers
    agent_goal_resume_hours: int = 24       # ... if she answers within this many hours
    # v0.223 PHASE A (long jobs like Claude): restart-proof, steerable, never "failed" just because a limit ran out
    agent_goal_recover: bool = True         # a goal still 'working' with nothing running it (server restart) is picked up again
    agent_goal_recover_after_s: int = 600   # ... once it has not moved for this long and no turn holds the chat
    agent_goal_recover_max: int = 3         # ... at most this many times per goal (then it waits for her)
    agent_steer: bool = True                # her message sent mid-job reaches the RUNNING job at its next step
    agent_goal_ask_on_limit: bool = True    # rounds / minutes used up = "Aage badhaun?" (her yes = a fresh budget), not 'failed'
    agent_plan_early: bool = True           # v0.228 a clearly big ask gets "plan first" up front; no plan after N steps = asked again
    agent_plan_after_steps: int = 4         # ... tool steps without a kaam_plan before the plan is asked for (v0.311: 6 -> 4)
    agent_auto_plan: bool = True            # v0.311 PLAN HAMESHA: still no plan 3 steps after the ask = the server writes a one-step plan
    chat_thinking: str = "goal"             # v0.232 PHASE C: Claude thinks out loud (adaptive) - goal = only while a long job runs, on = every turn, off = never
    chat_thinking_adaptive: bool = True     # parity Phase 4: every chat turn may think, effort by the turn (greeting low / ordinary medium / hard + long high), shown folded; False = thinking only for long jobs / hard asks, GLM reasoning excluded
    hard_detect: bool = True                # v0.272 SOCH KE JAWAB: spot hard reasoning asks (agent/hard.py)
    hard_thinking: bool = True              # v0.272 a hard ask thinks (adaptive) from its first call, like a long job
    hard_judge: bool = True                 # v0.272 the 'not sure' zone asks one tiny model call (1 token, time-limited)
    hard_judge_model: str = "claude-haiku-5-5"
    hard_judge_timeout_s: float = 2.5
    hard_recipe: bool = True                # v0.433 a hard ask gets the reasoning recipe in its system prompt (agent/hard.py)
    hard_check: bool = True                 # v0.436 SOCH KE JAWAB 5: a hard answer is held + checked (code + one reviewer call) before she sees it
    # v0.457 HOOLA INTERACTIVE (docs/INTERACTIVE_AVATAR_PLAN.md): the GPU Model Lab. Address + key live in the VPS
    # .env only; empty = the feature is simply off (never half-open).
    avatar_engine_url: str = ""            # e.g. https://<account>--hoola-lab-web.modal.run
    avatar_engine_key: str = ""            # the same ENGINE_KEY the lab's Modal secret holds
    hard_check_model: str = ""              # v0.436 the reviewer's model ('' = anthropic_model)
    hard_check_independent: bool = True     # wave 13: the reviewer skips the one-model rewrite (never the writer's own Haiku)
    hard_check_timeout_s: float = 60.0      # v0.436 a slow reviewer never blocks the answer
    agent_narrate_every: int = 1            # v0.258 after this many tool rounds with no word to her, ONE short line (8 in v0.240 = silence)
    agent_narrate_max: int = 6              # v0.258 at most this many such lines in a turn (2 in v0.240; Claude writes one per tool group)
    goal_verify_links: bool = True           # v0.443 the gate may reach the link the job produced (one HEAD).
    #                                         Off = links read as "unknown" (tests / an offline box)
    goal_verify: bool = True                # v0.443 DONE = VERIFIED: `kaam_plan finish done` passes verify.gate
    #                                         first (files on disk, pages ready, links alive, step checks) - a
    #                                         failure reopens the step instead of closing the card on a claim
    agent_goal_milestones: int = 2          # v0.228 at most this many 'aadha kaam ho gaya' pushes per long job (0 = off)
    doc_hold_drafts: bool = True            # v0.315 EK HI FILE: a doc_studio draft with QA problems is held for one fix, not shown
    dev_ci_loop: bool = True                # v0.351 a repo with CI gets a DRAFT PR; Hoola fixes until her CI passes, then marks it ready
    dev_ci_rounds: int = 3                  # ... automatic fix rounds before it stops and tells her
    dev_ci_wait_min: int = 15               # ... no CI result this long = the PR is made ready with a 'no tests ran' note
    dev_ci_max_min: int = 45                # ... CI still running this long = ready anyway, result told when it lands
    dev_loop: bool = True                   # v0.350 Developer Sahayak explores + edits step by step with 8 tools (devsahayak/loop.py)
    dev_loop_steps: int = 40                # ... at most this many model steps a task
    dev_loop_minutes: int = 20              # ... and this many minutes
    dev_review_steps: int = 25              # v0.377 a PR review explores at most this many steps (read-only tools)
    dev_review_minutes: int = 10            # ... and this many minutes, then the one-shot review is the fallback
    dev_spec_review: bool = True            # v0.402 ECC specialists in PR reviews; ON since the review card (same 8/8 caught, false alarms 8 -> 4, nits 3 -> 0)
    dev_lab: bool = True                    # v0.533 PRAYOGSHALA ON: her VPS answered lab_check with every wall holding (docker 29.8.1, base image built, pass + fail caught, network blocked, read-only root, uid 1000)
    dev_lab_timeout: int = 600              # ... seconds one check may run (her .hoola/lab.json may lower it)
    dev_lab_keep: int = 12                  # ... per-repo dependency snapshots kept before the oldest are dropped
    dev_plan_first: bool = True             # v0.451 ECC PHASE 4: a standard / large job gets a read-only PLAN pass before any edit
    research_engines_allowed: str = "hoola"   # v0.477 R6: comma list of engines she lets run research ("hoola" is always allowed); a vendor must be listed here ...
    research_vendor_terms_ack: str = ""       # ... AND here: the vendors whose current terms SHE has read and accepts for this use (storing + showing the result to her). Nothing is assumed.
    exa_api_key: str = ""                     # VPS .env only (EXA_API_KEY), never in chat or the repo
    linkup_api_key: str = ""                  # VPS .env only (LINKUP_API_KEY)
    research_parallel_run_inr: float = 0.0    # ONE run's price in rupees per vendor: UNKNOWN until she reads the vendor's plan, so 0 = that engine is REFUSED (a ceiling needs a price)
    research_exa_run_inr: float = 0.0         # (Exa also takes this as its own vendor-side budget.maxCostDollars and reports its real costDollars back)
    research_openai_run_inr: float = 0.0
    research_linkup_run_inr: float = 0.0
    research_parallel_processor: str = "core"          # Parallel processor tier: lite | base | core | pro (read from the SDK; the price of each is NOT known)
    research_exa_effort: str = "auto"                  # Exa agent effort (SDK literal: minimal low medium high xhigh auto ultra max)
    research_openai_model: str = "o4-mini-deep-research"   # or o3-deep-research
    research_openai_search_tool: str = "web_search_preview"
    research_openai_max_tool_calls: int = 40
    research_linkup_depth: str = "L"                   # S | M | L | XL
    research_linkup_mode: str = "research"
    research_vendor_poll_s: float = 10.0
    research_vendor_wait_s: float = 1500.0             # a vendor run that has not finished by now is given up on (it may still bill)
    research_run_cap_inr: float = 150.0     # v0.476 R5: ONE research run may spend at most this many rupees (model calls; a default, not a measured need)
    research_daily_inr: float = 600.0       # ... and one tenant's research runs together at most this much a day (IST); 0 = no research that day
    research_call_reserve_inr: float = 3.0  # a run asks "can I still afford another call?" with this much room - it refuses BEFORE the call that would cross
    research_search_inr: float = 0.0        # price of ONE Parallel search call in rupees: UNKNOWN until her plan is read, so 0 and said so on every cost line
    research_fetch_inr: float = 0.0         # price of ONE page fetch in rupees: same
    research_review: bool = True            # v0.480 R9: after the code checks, a reviewer reads the report against the dossier's notes (wording stronger than the evidence ...)
    research_watch_month_inr: float = 300.0 # v0.480 R9: ONE watched topic may spend at most this many rupees a month, then it pauses itself (a default, not a measured need)
    research_background: bool = True        # v0.475 R4: research_run starts a PERSISTED background run and returns at once (False = inline, inside the turn)
    research_bg_soft_s: float = 1500.0      # a background run's soft clock: after this the workers finish with what they have
    research_bg_max_running: int = 2        # background research runs at once per tenant
    research_bg_stale_s: int = 180          # a running run that has not heartbeated for this long is picked up again from its checkpoint
    research_bg_tries: int = 3              # ... at most this many starts (the first + restarts)
    research_engine_on: bool = True         # v0.473 R2: the `research_run` tool (Hoola's own research engine) is available
    research_engine: str = "auto"           # v0.478 R7: "auto" = the run-off winner she applied, else Hoola's own; or name one (hoola | parallel | exa | openai | linkup) - a vendor still needs every R6 gate open
    research_tasks_max: int = 6             # goals in the first round
    research_steps: int = 8                 # model steps one goal may take
    research_pages_per_task: int = 6        # pages one goal may read
    research_pages_total: int = 30          # pages a whole run may read
    research_calcs_max: int = 8             # pylab calculations a whole run may make
    research_rounds: int = 2                # the first plan + at most one re-plan
    research_parallel: int = 3              # goals worked at once
    research_soft_s: float = 420.0          # after this the workers finish with what they have (a turn is capped at 900 s)
    research_read_chars: int = 12000        # characters of one page shown to a worker
    research_plan_gate: bool = True         # v0.472 R1 PLAN PEHLE: a LARGE research ask shows its plan and waits for her Haan
    dev_plan_gate: bool = True              # ... and a LARGE job waits for her Haan on that plan (ECC's Gate 1)
    dev_plan_steps: int = 18                # ... the plan pass explores at most this many steps
    dev_plan_minutes: int = 8               # ... and at most this long
    dev_fix_proof: bool = True              # v0.447 ECC PHASE 3: a fix's test is pushed FIRST, so her CI proves the bug (red) before the fix lands
    dev_self_review: bool = True            # v0.445 ECC PHASE 2: Hoola reviews its OWN PR before marking it ready for review
    dev_self_rounds: int = 2                # ... its own review may send the work back for a fix this many times
    dev_spec_fix: bool = True               # v0.402 ECC fixer specialist in CI fix rounds; ON since the fix card (6/6 + 6/6 with it, no harm)
    dev_spec_focus_lines: int = 150         # a PR this big (added lines) gets every focused pass
    dev_spec_focus_steps: int = 12          # steps for one focused pass
    dev_loop_model: str = ""                 # ... '' = site_model (Opus)
    dev_loop_effort: str = "high"           # ... Claude effort for coding
    # v0.784 HOOLA CODE ENGINE (owner: "GO STEP 1 AND 2 --- 2 SESSIONS, USE CLAUDE"): devsahayak/engine.py + brain.py
    dev_claude: bool = True                 # every Hoola Code model call is Claude's own (stands SAB GLM / claude_one_model aside)
    dev_think: bool = True                  # ... with adaptive thinking
    dev_hint: bool = True                   # Hoola Code Phase 5: one small model call when a round ends suggests her next message (ghost text)
    dev_hint_model: str = "claude-haiku-5-5"   # ... on this model
    dev_net: bool = False                   # Hoola Code Phase 6: network levels + outside secrets for the box (allow-list proxy). OFF until `python -m app.devlab net` passes on the server
    dev_events: bool = True                 # Hoola Code Phase 6: GitHub events (a signed repository webhook) may start a scheduled task
    dev_workspace: bool = True              # a real working copy per session + bash in the locked box + a conversation that continues
    dev_ws_live: int = 2                    # ... sessions that may RUN at once on the server (owner: 2); the rest wait their turn
    dev_ws_steps: int = 150                 # ... model steps in one round
    dev_ws_minutes: int = 60                # ... minutes in one round
    dev_ws_bash_runs: int = 80              # ... box commands in one round
    dev_ws_clear_chars: int = 180000        # ... past this, old tool output is trimmed (brain.trim)
    dev_ws_compact_chars: int = 480000      # ... past this, the older conversation is summarised (engine.compact)
    dev_ws_keep_days: int = 14              # ... an idle session's working copy is kept this long
    # v0.794 ECC AGENTS (owner: "ADD ALL MISSING ECC AGENTS TO HOOLA CODE"): devsahayak/ecc/ (63 agents) + subagent.py
    dev_ecc_agents: bool = True             # the coder gets the `agent` tool + the roster (Claude Code-style subagents)
    dev_ecc_rules: bool = True              # ECC's coding rules for the repo's languages in the coder's system prompt
    dev_ecc_rules_chars: int = 9000         # ... at most this many characters of them
    dev_ecc_gate: bool = True               # ECC's pre-commit check on the diff before `done` is accepted (one clean-up chance)
    dev_agent_steps: int = 30               # model steps for one agent
    dev_agent_minutes: int = 12             # minutes for one agent
    dev_agent_max: int = 10                 # agents per round
    dev_agent_parallel: int = 4             # read / run agents asked in one reply that run at the same time
    # v0.814 THE AGENCY (owner: "GO 1 2 3"): 35 more agents in devsahayak/ecc/agency_*.py + the reality check before done
    dev_reality_check: bool = True          # an independent reality-checker agent looks once before a round may finish
    dev_reality_min_lines: int = 30         # ... only for a change of at least this many added lines
    game_agency_experts: bool = True        # the Game Developer's crew roles carry The Agency's expert notes (gamedesk/agency.py)
    agent_aage: bool = True                 # v0.311 AAGE BADHO: a text-only reply that only promises more work gets one 'do it now' nudge
    agent_progress_window_s: int = 300      # v0.311 a turn that finished a tool this recently gets the long-job deadline (0 = off)
    agent_ack_after_s: float = 5.0          # v0.187 a turn silent this long first says "ek second, dekh raha hoon…" (0 = off)
    agent_parallel_tools: bool = True       # v0.189 a step asking several pure look-ups (search/weather/status) runs them together; everything else stays serial
    # v0.191 HARNESS-2: step-admitted tool subsets (dsh / Claude Code pattern) - the model of one turn sees only the
    # tool families her words (and any open goal) actually need; the rest stay one tool_search away. Stable for the
    # WHOLE turn, so the Anthropic prompt cache holds; a family admitted mid-turn re-caches once, by design.
    agent_tool_admission: bool = True
    # Parity Phase 2: a chat turn sends a small FIXED system prompt (core + a small per-chat block, ~10k chars, the same
    # every turn so the prompt cache holds); facts / sites / apps / desks are fetched with tools, per-turn notes ride on
    # her newest message (false = the old ~50-60k per-turn prompt). Calls (voice brain) and routines keep the old shape.
    chat_small_prompt: bool = True
    # Parity Phase 7: ONE memory, Claude style - a chat turn carries only the short memory summary (her page + pinned facts,
    # in the per-chat block) plus a capped 'since your last reply' note (job state, card news) and her skill NAMES; the diary,
    # her recent words, the coder primer and the full skills list are fetched with yaad_khojo / skill_manage instead
    # (false = today's per-turn memory blocks). Calls (voice brain) and routines keep their own shape.
    chat_one_memory: bool = True
    prompt_slim: bool = True               # v0.473 PATLA PROMPT: only the admitted families' guides ride in the system prompt (false = the full ~130 KB guide, as before)
    # v0.237 FULL CLAUDE MODE Phase 1 (agent/context.py): the whole chat word for word while it fits the model's window
    chat_context: str = "claude"           # claude = whole chat, gauge + safety net | hoola = the v0.108 40-49 exchange window (instant rollback)
    chat_context_limit_glm: int = 1000000  # v0.724 owner: 1M for every chat (a smaller real window is learned from its "too long" error)
    chat_context_limit_claude: int = 1000000   # v0.724 owner: "MAKE IT 1 MILLION CONTEXT WINDOW FOR EVERY CHAT"
    chat_context_limit_omniroute: int = 1000000  # v0.724 1M; a smaller real window is learned from its error
    chat_context_full_at: float = 0.75     # the request may fill this share of the window; above it the safety net runs
    chat_context_max_tokens_glm: int = 0       # v0.724 owner: 1M window, no GLM cost cap (0 = off); v0.707 cap while the GLM door answers (no prompt cache); v0.724 = tokens
                                               # of CONVERSATION on top of the system prompt + tools (was the whole request)
    chat_context_max_tokens: int = 0       # v0.244 cost cap: compact at this many tokens whatever the model's window (0 = off)
    # v0.242 FULL CLAUDE MODE Phase 2 (agent/compact.py): Claude-style compaction at the full_at line
    about_me: bool = True                  # v0.250 "Mere baare mein" page rebuilt daily for active owners (false = never rebuilt)
    request_dump: bool = True              # v0.732 PARITY Phase 0: every chat model call's request (system text, tool NAMES, messages, brain/model, max_tokens) kept per conversation, secrets masked - GET /api/conversations/{id}/request[/{turn}]
    request_dump_turns: int = 20           # newest turns kept per conversation (older ones dropped)
    chat_alone: bool = True                # v0.714 HAR CHAT ALAG: background / daily messages go to her pinned 'Hoola updates' chat (never the chat she has open), and a chat turn reads only ITS OWN chat's jobs / cards / diary; false = the old shared behaviour
    memory_fence: bool = True              # v0.246 PHASE 3C: Hoola's own memory stays inside its Session (fence.py); false = all chats share
    chat_compact: bool = True              # false = Phase 1 only (the safety net shortens instead of a summary)
    chat_compact_prepare_at: float = 0.6   # past this share a draft summary is written in the background
    chat_compact_keep: int = 4             # newest exchanges that always stay word for word
    chat_compact_max_chars: int = 8000     # the checkpoint summary's size
    tool_admit_cap: int = 220               # admitted specs above this = router over-matched: send the FULL set instead
    # Parity Phase 3 CLEAN TOOLS (docs/CLAUDE_PARITY_PLAN.md): a turn starts from ~22 core tools (agent/core_tools.py:
    # web_search, ONE web reader web_fetch, pylab, artifact, file, one memory search, chats, mail, calendar, drive,
    # plan, agents, form, status) with clear English descriptions; a family joins only when her words clearly name it
    # (whole-word keys), everything else stays one tool_search away; big results keep head + tail; no raw Python errors.
    # false = the old always-on core families (~55 tools a plain turn) and the old result / error text
    chat_core_tools: bool = True
    # v0.191 HARNESS-2: job-completion WAKE turns (dsh completionDelivery + maxConsecutiveWakes) - a finished job whose
    # chat is idle wakes the real brain (tools allowed) instead of only the v0.187 one-shot line; budget keeps it finite.
    agent_wake_turns: bool = True
    agent_wake_max_consecutive: int = 3     # wakes without an intervening user message, per chat
    agent_wake_window_min: int = 10         # ...within this many minutes (then the budget resets by age)
    # v0.191 HARNESS-2: durable accepted-message inbox - the 202 is persisted BEFORE the turn runs; a pm2 restart or a
    # crashed worker no longer silently eats her message (the worker re-runs it once, idempotently).
    agent_turn_inbox: bool = True
    turn_inbox_stale_s: int = 120           # accepted-but-never-started for this long = the task died before it ran
    # v0.193 HARNESS-3: the AGENT TEAM (dsh subagents 8-active/depth-1 + Claude Code's parallel Task tool) - she says
    # "kai agents lagao" and Hoola splits an independent-parts job across a parallel crew; background crews ride the
    # wake lane when done. Plus the event-sourced session log (harness_events) under every turn.
    agent_team: bool = True
    team_max_agents: int = 4                # agents per deploy call (a turn's total is capped at 8)
    team_agent_max_steps: int = 8           # model steps per sub-agent
    team_agent_timeout_s: int = 240         # per-agent wall clock (inline clamps to 260: the main tool clock is 300 s)
    team_max_tokens: int = 1500             # per sub-agent model call
    team_research_max_steps: int = 14       # v0.437 a deep-research crew's agents: more steps (pages to open, sources to check)
    team_research_max_tokens: int = 4000    # v0.437 ... and room for a sourced report (~15 lines with links)
    team_research_soft_s: float = 170.0     # v0.437 a research agent writes its sourced report at this mark (the inline crew clock is 260 s)
    team_background: bool = True            # mode="background" crews (persisted, worker-run, self-reporting)
    team_tenant_inline_max: int = 8      # CALL PAR TEAM: inline agents running at once for one user, across all her asks
    team_bg_max_running: int = 2            # running background crews per tenant
    team_bg_timeout_s: int = 1200           # a whole background crew's wall clock
    # PARITY Phase 4 (docs/CLAUDE_PARITY_PLAN.md): long work stays IN the chat turn, like Claude - deploy_agents crews
    # and Hoola's own research_run run inside her turn and the answer is the reply (no background crew, no wake turn).
    # Background jobs stay only for work that outlives the turn (video renders, app / website builds). False = the old
    # behaviour (crews / research may go to the background, 900 s turn, 300 s tool clock).
    chat_work_in_turn: bool = True
    chat_turn_s: int = 1200                 # her chat turn's budget with work in the turn (20 min; was agent_turn_timeout_s 900)
    chat_max_calls: int = 200               # tool calls one chat turn may make (breaker cap; was 48 / 150 in goal mode)
    chat_long_tool_s: int = 1080            # tool clock for deploy_agents / research_run inside a chat turn (was 300 s)
    team_inturn_timeout_s: int = 900        # an in-turn crew's clock: slow agents are cut, finished agents keep their work
    agent_event_log: bool = True            # the harness session log (harness_events; best-effort writes, never breaks a turn)
    event_log_retain_days: int = 14         # the daily worker sweep drops older rows
    tv_refresh: bool = True                # Hoola TV: download + check the free channel list nightly
    app_release_repo: str = "fibernetworkworks-droid/santosh-app"   # v0.62 where the phone app's releases live
    video_edit_worker: bool = True         # v0.65 Hoola Video Editor: run edits in the background (tests run them inline)
    video_max_output_s: int = 300          # longest finished video the CPU VPS makes
    callcentre_plivo_auth_id: str = ""     # v0.133 Call Centre: Newtika's own Plivo account (used when she typed no keys)
    callcentre_plivo_auth_token: str = ""
    callcentre_max_calls: int = 10         # AI phone calls at once on this server
    callcentre_noise_gate: bool = True     # while Hoola speaks only clearly voiced caller audio may interrupt
    cyber_certin_feed: str = ""            # v0.137 Cyber Suraksha: CERT-In advisories RSS / Atom URL ('' = skipped; NVD + CISA KEV still used)
    cyber_sleep_between_s: float = 1.0     # politeness gap between per-item NVD / HIBP calls (0 in tests)
    devops_llm: bool = True                # v0.137 DevOps: optional model wording for unknown failures / custom scripts
    customs_llm: bool = True               # v0.139 Customs: model HS-code suggestions (false = heading table + her learned codes only)
    contracts_llm: bool = True             # v0.150 Contracts: optional model summary / extra redline ideas (false = rules only)
    courier_dir: str = ""                  # v0.139 Courier desk label PDFs ('' = data/courier)
    courier_poll_min: int = 0              # minutes between courier tracking polls per owner (0 = module default 30)
    courier_bluedart_base: str = ""        # Blue Dart API base ('' = https://apigateway.bluedart.com/in/transportation)
    logistics_dir: str = ""                # v0.139 Logistics POD / loading / damage photos ('' = data/logistics)
    sitesup_dir: str = ""                  # v0.144 Site Sahayak photos (EXIF-stripped JPEG; '' = data/sitesup)
    motiondesk_dir: str = ""               # v0.156 Motion designer desk: client logos ('' = data/motiondesk)
    photoassist_dir: str = ""              # v0.156 Photo Sahayak: culling copies + release proofs ('' = data/photoassist)
    graphic_dir: str = ""                  # v0.156 Graphic desk: job folders, proofs, handover ZIPs ('' = data/graphic)
    studio_on: bool = True                 # v0.68 Hoola Video Studio (AI-generated shots: Seedance / Veo / Kling / Wan / Omni)
    openrouter_api_key: str = ""           # one key for Seedance 2.0 / 2.5, Veo 3.1, Kling 3.0, Wan 3.0 (recommended)
    fal_key: str = ""                      # backup: Seedance via fal
    ark_api_key: str = ""                  # backup: Seedance direct from BytePlus ModelArk
    studio_month_usd: float = 60.0         # most one owner may spend on AI video in a calendar month (every spend is her tap too; v0.157 10 -> 60)
    sync_api_key: str = ""                 # v0.157 Sync Labs sync-3 lip sync (Hindi / any language dialogue)
    studio_sync_url: str = ""              # base URL override (tests)
    studio_music_model: str = "lyria-3.5"  # v0.157 Google Lyria music for the final video ('' = Hoola's own free beds)
    studio_plan_model: str = "claude-opus-5-5"   # v0.157 writes storyboards (shot prompts tuned per video model)
    # v0.313 HOOLA PRINT: PDFs made like Claude makes them (designed HTML printed by Chromium, docstudio/htmlpdf.py)
    doc_engine: str = "chromium"            # chromium | reportlab (the v0.192 Document Studio drawing)
    doc_art: bool = True                    # Opus picks the look per document (off = the topic router picks)
    doc_review: bool = True                 # Opus looks at the printed pages and may ask for one change
    doc_model: str = ""                     # model for doc_art / doc_critique ("" = app_model, Claude Opus 5.5)
    seo_ai: bool = True                     # v0.317 the SEO Employee asks Opus for its 90-day plan (off = the rules plan)
    # v0.353 SOCIAL MEDIA MANAGER (employee 2): Hoola's ONE Meta app - users connect their own Instagram / Facebook Page to it
    meta_app_id: str = ""                   # App settings > Basic (Facebook Login for Business + Pages)
    meta_app_secret: str = ""
    meta_login_config_id: str = ""          # Facebook Login for Business > Configurations (pages + permissions)
    instagram_app_id: str = ""              # Instagram use case > API setup with Instagram login
    instagram_app_secret: str = ""
    meta_social_version: str = "v25.0"      # pinned Graph API version for the social desk (graph.facebook.com / graph.instagram.com)
    wa_es_config_id: str = ""               # v0.384 WhatsApp Embedded Signup: the Login for Business configuration for WhatsApp
    linkedin_client_id: str = ""            # v0.384 LinkedIn app (Sign In with LinkedIn + Share on LinkedIn), Newtika's one app
    linkedin_client_secret: str = ""
    linkedin_version: str = "202510"
    google_ads_developer_token: str = ""   # v0.401 YouTube ads (plan Y2): Google Ads API Center token (test / Basic access)
    google_ads_login_customer_id: str = ""  # optional manager (MCC) id when her ad account sits under Hoola's manager
    google_ads_api_version: str = "v26"
    # v0.541 SEO INTEL: AI visibility through each company's own API (keys in .env only), DataForSEO for competitor data
    perplexity_api_key: str = ""            # Perplexity Sonar API (PERPLEXITY_API_KEY); empty = Perplexity left out
    seo_ai_openai_model: str = "gpt-5-mini"
    seo_ai_openai_search_tool: str = "web_search"
    seo_ai_gemini_model: str = "gemini-2.5-flash"
    seo_ai_perplexity_model: str = "sonar"
    seo_ai_call_inr: float = 2.0            # what one AI answer is charged as (an estimate; every answer counts against her ceiling)
    seo_ai_month_inr: float = 300.0         # default monthly ceiling for AI-visibility answers, per site (she can change it)
    dataforseo_login: str = ""              # Newtika's own DataForSEO login - used ONLY when dataforseo_shared is true
    dataforseo_password: str = ""
    dataforseo_shared: bool = False         # false = every user brings her own DataForSEO login (her money)
    dataforseo_month_usd: float = 5.0       # default monthly DataForSEO ceiling per site (USD, from DataForSEO's own reported cost)
    meta_ads_config_id: str = ""            # v0.417 optional Facebook Login for Business configuration for the ads login (ads_management + ads_read)
    meta_ads_max_daily: int = 2000          # v0.417 Hoola's ceiling on a Facebook / Instagram ad's daily budget (her account currency)
    gads_max_daily: int = 2000              # Hoola's ceiling on a YouTube ad's daily budget (her account currency)
    yt_daily_uploads: int = 90              # v0.392 Hoola-wide YouTube uploads a day (the API quota is the whole project's)        # LinkedIn-Version header (YYYYMM) for /rest/ calls
    social_ai: bool = True                  # the Social Media Manager asks Opus for its strategy + 30-day calendar (off = rules)
    studio_project_usd: float = 5.0        # starting budget of a new project
    studio_usd_inr: float = 85.0           # shown next to dollar prices on her cards
    studio_image_mode: str = "data"        # data = character photos inline; public = short-lived signed links from this server
    studio_concurrency: int = 3
    studio_poll_s: float = 5.0
    studio_openrouter_url: str = ""        # base URL overrides (tests / proxies)
    studio_fal_url: str = ""
    studio_ark_url: str = ""
    studio_gemini_url: str = ""
    studio_allow_private: bool = False     # tests only: provider downloads from local fake servers
    operator_on: bool = True               # v0.67 Computer Operator (Playwright Chromium inside core, own browser per owner)
    operator_worker: bool = True           # run operator jobs in the background (tests run them inline)
    operator_max_jobs: int = 2             # browsers at the same time on this server (~300 MB each)
    operator_max_steps: int = 120          # model steps in one job
    operator_wait_owner_s: int = 900       # how long a job waits for the owner's answer (OTP, approval...)
    operator_allow_private: bool = False   # tests only: lets the browser open local test sites
    operator_headless: bool = False        # v0.74: a real browser window on a virtual screen (Xvfb); headless gets refused by many sites
    browser_upstream_proxy: str = ""       # v0.89 http://user:pass@host:port of HER OWN network (office proxy) for sites that refuse servers
    browser_upstream_hosts: str = ""       # v0.89 comma list: only these sites use the upstream ('' = all traffic)
    operator_browser: str = "auto"         # auto (Google Chrome if installed, else Playwright's Chromium) | chrome | chromium
    operator_chromium: str = ""            # path to a Chromium binary (empty = Playwright's own)
    operator_audit_days: int = 14          # step screenshots + log kept this long
    video_whisper: bool = False            # word-exact captions with faster-whisper (pip install faster-whisper)
    video_whisper_model: str = "small"
    video_gemini_model: str = ""           # model that watches the footage (default: the reels / YouTube Gemini model)
    ifsc_refresh: bool = True              # v0.59 monthly IFSC branch details (razorpay/ifsc release) + online lookup
    logo_warm: bool = True                 # fetch all plugin logos once after start (cached in data/logos)
    mcp_native_tools: int = 40             # tools of the owner's MCP servers given to the avatar directly (rest via bazar_run)
    llm_retries: int = 2                    # extra tries for a busy / briefly unreachable model before falling back

    # --- low-cost chat brain: any OpenAI-compatible API (Z.ai GLM, or GLM self-hosted in India) ---
    chat_llm: str = "auto"                  # auto (OmniRoute, else GLM, else Claude) | omniroute | glm | claude
    # v0.732 PARITY PHASE 1 EK MODEL (owner: "WE WILL KEEP GLM 5.3 FLASH AS PRIMARY FOR ALL FOR NOW --- PHASE 0 + 1"): a
    # chat turn runs on ONE model from start to end, like Claude chat - the configured chat brain (GLM-5.3-Flash on her
    # server). No silent switch to Claude when GLM fails or is paused, no Haiku / Sonnet / Opus split by ask size: the
    # same model is asked again (chat_model_retries, chat_model_retry_s apart), then the turn says plainly that the model
    # is busy. The ONE exception: a PDF / picture the chat brain cannot read goes to Claude (llm.choose). Background
    # work (summaries, reviewers, Studio steps) keeps its own routes. Off = the old fallbacks.
    chat_one_model: bool = True
    chat_model_retries: int = 2
    chat_model_retry_s: float = 3.0
    # --- OmniRoute: open-source LLM gateway on this VPS (switches providers, fallback, cost routing) ---
    omniroute_url: str = ""                 # e.g. http://127.0.0.1:20128/v1
    omniroute_key: str = ""                 # an endpoint API key made in the OmniRoute dashboard
    omniroute_model: str = "santosh"        # a combo you create in OmniRoute (or "auto", or provider/model)
    omniroute_compression: str = "off"      # keep Santosh's prompts and tool results exactly as sent
    # --- Push (Firebase Cloud Messaging HTTP v1): service-account JSON from Firebase > Project settings > Service accounts
    fcm_service_account_file: str = ""
    # --- Santosh Browser: separate worker (server/browser_worker) running browser-use + headless Chromium ---
    browser_worker_url: str = ""            # e.g. http://127.0.0.1:8079 (empty = browsing off)
    browser_worker_key: str = ""            # same value as WORKER_KEY in the worker's env
    browser_llm: str = "auto"               # auto (Claude when its key is set, else OmniRoute/GLM) | claude | omniroute | glm
    browser_max_steps: int = 40
    browser_wait_seconds: int = 20          # v0.86 how long a chat turn waits before "I'll message you when done" (was 150)
    pc_wait_seconds: int = 12               # v0.86 same for the PC operator (the chat stays free for new questions)
    artifact_wait_seconds: int = 20         # v0.86 same for pages (the card opens when ready)
    chat_artifact_direct: bool = True       # parity Phase 6: the chat model writes pages itself (tool `artifact`: create /
                                            # update old->new / rewrite, a version per change, streamed into the panel);
                                            # artifact_make (the separate builder) only for a 'polish / studio quality' ask
    hoola_language: str = "en"              # v0.728 SAB ENGLISH: en = Hoola writes and speaks English; auto = her own language
    quick_lane: bool = False                # v0.86 answer new chat messages at once while a long job runs. v0.724 CLAUDE
                                            # JAISA: off - a smaller no-tools brain answered from 10 lines and the pair was
                                            # kept OUT of the history; now her message reaches the running job / waits
    chat_approval_words: bool = False       # v0.724 CLAUDE JAISA: a bare "haan" no longer approves a waiting PC / browser
                                            # card before the model reads it; the model sees the card + its own last reply
    quick_model: str = ""                   # v0.86 model for the quick lane ('' = anthropic_model; a cheap brain is used first)
    prompt_cache: bool = True               # v0.86 Anthropic prompt caching on tools + conversation (faster replies)
    console_v2: bool = True                 # v0.170 Console v2 master switch: the Night-Glass v2 shell serves /console (?legacy=1 = the old page) and turns the four chat phases on below in one go
    console_human: bool = True             # v0.743 SAAF INSAANI: the console talks like a person (same design)
    console_stream: bool = False            # v0.161 replies stream word by word (live-only delta events, /live, retry, thumbs)
    chat_sessions: bool = False             # v0.162 many chats: titles, pin / archive / delete, search, edit + branches
    side_panel: bool = False                # v0.163 finished work (pages, files, videos, sites, apps) opens beside the chat
    chat_projects: bool = False             # v0.164 projects ("Kaam ke folder"): instructions, notes, files for their chats
    projects_dir: str = "./data/projects"   # v0.164 project files (kept until she removes them, unlike pc_files)
    glm_api_key: str = ""
    glm_base_url: str = "https://api.z.ai/api/paas/v4"
    glm_model: str = "glm-4.7"
    glm_temperature: float = 0.6
    # SAB GLM (owner: "use GLM 5.3 Flash for all use - NVIDIA gives a free API"): with claude_all_glm on, EVERY Claude
    # call (chat fallback, reviewers, summaries, every engine) is answered by the GLM brain below; Claude only when GLM
    # fails (claude_all_glm_fallback) or a call carries pictures / PDFs. For NVIDIA set GLM_BASE_URL to
    # https://integrate.api.nvidia.com/v1, GLM_MODEL=z-ai/glm-5.3-flash, GLM_API_KEY=nvapi-... and CHAT_LLM=glm.
    claude_all_glm: bool = False
    api_box_enabled: bool = True             # v0.750 the free public-API box (api_box tool, /api/box)
    api_box_check_per_day: int = 300         # v0.750 free APIs whose site is re-checked a day (all ~1,400 about monthly); 0 = off
    studio_build_architect: bool = True   # v0.711 Web Studio Build mode: every ask is planned by the architect first (not the library's page set for its business type)
    architect_opus: bool = False   # v0.735 ALL GLM (owner: "MOVE EVERYTHING ON GLM 5.3 FLASH"): off = the plan on GLM too. Was True since v0.710 - v0.710: the website architect's plan always on the Website Sahayak's Opus (the GLM door + claude_one_model stand aside for that one call)
    claude_all_glm_fallback: bool = False   # v0.735 ALL GLM: a failed GLM call is NOT re-asked on Claude (was True)
    # v0.735 ALL GLM - every job on GLM, one switch per piece so the owner can test them one by one:
    glm_images: bool = True     # pictures go to GLM (OpenRouter lists z-ai/glm-5.3-flash with text + image + video input)
    glm_pause_one_model: bool = False   # v0.736 true = a paused GLM refuses chat calls again (old)
    glm_pdf: bool = True        # a PDF reaches GLM as its own text (pypdf); a scanned PDF as page pictures (pypdfium2)
    glm_pdf_max_chars: int = 60000
    glm_pdf_max_pages: int = 8  # pages rendered as pictures for a scanned PDF
    claude_all_brain: str = ""              # "" = OmniRoute when OMNIROUTE_URL is set, else GLM | "glm" | "omniroute"
    omniroute_timeout_s: float = 90.0       # one OmniRoute request (it may try two providers inside it)
    glm_reasoning_effort: str = "low"     # NVIDIA GLM-5.3-Flash: low | high | max (its default max is slow)
    glm_timeout_s: float = 45.0           # one GLM request waits at most this (her NVIDIA test hung 120 s with 0 bytes)
    glm_breaker_fails: int = 2            # GLM failures in a row before it is skipped
    glm_pause_s: float = 600.0            # how long a failing GLM is skipped (Claude answers meanwhile)
    glm_reasoning_room: int = 2048        # tokens added to max_tokens on NVIDIA (its reasoning counts inside max_tokens)
    glm_thinking: str = "disabled"          # enabled | disabled | "" (don't send) — disabled = faster, cheaper replies

    # --- realtime voice (Baat tab): Gemini Live speech-to-speech, key from aistudio.google.com ---
    gemini_api_key: str = ""
    gemini_live_model: str = "gemini-3.8-live"
    voice_default: str = "Puck"            # a male Gemini voice; the app can pick another
    gemini_search_model: str = ""          # model used for Google Search answers (empty = newest Flash)
    parallel_search: bool = True           # v0.91 Parallel web search (free MCP endpoint): quotes from real pages + links
    parallel_api_key: str = ""             # optional: higher limits (https://platform.parallel.ai); only the query is sent
    parallel_mcp_url: str = "https://search.parallel.ai/mcp"
    reach_enabled: bool = True             # v0.559 REACH MANCH: the Agent-Reach discipline layer (the `reach` tool)
    reach_per_tenant_per_min: int = 30     # v0.559 per-tenant reach budget per minute (0 = no limit); channel rate-limit
                                           # cooldowns stay GLOBAL - the egress IP is shared, so a platform pause is too
    speckit_enabled: bool = True           # v0.560 SPEC SUTRA: the spec-driven ladder (the `speckit` tool, the
                                           # github/spec-kit idea); per-tenant store data/speckit/<tenant>/speckit.db
    workspace_enabled: bool = True         # v0.586 SANDARBH MANCH: the T1 reference filesystem role (the `workspace`
                                           # tool, the modelcontextprotocol/servers idea) - per-tenant sandbox
                                           # data/workspace/<tenant>/; off stops WRITES, reads stay answerable
    kgmemory_enabled: bool = True          # v0.586 SANDARBH MANCH: the T1 reference memory role (the `kgmemory`
                                           # tool, the knowledge-graph idea) - per-tenant store
                                           # data/kgmemory/<tenant>/kg.db; off stops WRITES, reads stay answerable
    bhandar_enabled: bool = True           # v0.618 BHANDAR MANCH: the T2 local-core family (the `bhandar` tool,
                                           # the read-only SQLite/markdown/json/AST/time beds idea) - all reads
                                           # over the tenant's OWN stores; off means off (honest NEED_SETUP)
    jharokha_enabled: bool = True          # v0.665 JHAROKHA MANCH: the T3 local-browser family (the `jharokha`
                                           # tool, the zero-login playwright-mcp + Puppeteer idea) - the agent's
                                           # OWN headless Chromium per tenant, capped and reaped (RAM law);
                                           # off means off (honest NEED_SETUP)
    duniya_enabled: bool = True            # v0.667 DUNIYA MANCH: the T4 keyless-public-web family (the `duniya`
                                           # tool, the mcp/servers fetch reference + the no-key public-API rows)
                                           # - ONE GET-only lane over the no-login/no-key services; off means
                                           # off (honest NEED_SETUP)
    kala_enabled: bool = True              # v0.681 KALA MANCH: the T5 knowledge-skill catalog family (the `kala`
    kala_catalog_ttl_seconds: int = 300    # tool, the google/skills catalog) - index.json fetched byte-exact
                                           # behind this in-process TTL; documents fetched fresh every read;
                                           # off means off (honest NEED_SETUP)
    shilp_enabled: bool = True             # v0.730 SHILP MANCH: the ArtCraft generation lane (the `shilp` tool,
                                           # their Omni API api.storyteller.ai) - video + image generation and
                                           # job status; off means off (honest NEED_SETUP)
    artcraft_api_key: str = ""             # BYOK: VPS .env only (ARTCRAFT_API_KEY), never in chat or the repo -
                                           # gated per account by the ArtCraft team (app.getartcraft.com)
    artcraft_base_url: str = "https://api.storyteller.ai"  # their doc's own emphasis: NOT api.getartcraft.com
    kaam_enabled: bool = True              # v0.688 KAAM MANCH: the work-discipline layer (OWL-derived, IDEA-ONLY
                                           # from camel-ai/owl@2df367e, zero upstream code): the search/verify
                                           # tips on the system prompt + the done-needs-proof backstop + the
                                           # (Kaam: ...) ledger note - no tool, no key, no network
    kaam_ledger_enabled: bool = True       # ... the ledger note alone can go quiet without touching the rest
    chat_answer_only: bool = True          # parity Phase 5: the reply is ONLY what the model wrote - the (Kaam: ...)
                                           # ledger rides the turn's step data (event `ledger`, the console's folded
                                           # steps row), honesty checks ask the model to correct itself once instead
                                           # of stapling a note, and a correction message goes out only when a real
                                           # ACTION claim (sent / paid / booked / deleted / published) stayed false
                                           # after that retry. False = the old stapled notes.
    # v0.741 more providers for the model dropdown: each key ONLY here (.env); "<provider>:<model>" in chat_models
    gemini_chat_api_key: str = ""          # Google AI Studio key for CHAT (the voice GEMINI_API_KEY is never spent by chat)
    groq_api_key: str = ""
    mistral_api_key: str = ""
    nvidia_api_key: str = ""
    zai_api_key: str = ""
    openrouter_api_key: str = ""           # only when GLM itself is not on OpenRouter
    aihubmix_api_key: str = ""             # v0.742 AIHubMix (free "-free" models after a $1 top-up)
    chat_model_choice: bool = True         # v0.740 each user picks the chat model in the console composer (owner's list)
    chat_models: str = "nvidia/nemotron-3.5-super-vl:free,thinkingmachines/inkling-2-small:free,google/gemma-4-31b-it:free"
                                           # the owner's list beside GLM_MODEL (OpenRouter slugs, comma-separated)
    model_choice_dir: str = ""             # '' = data/model_choice
    model_profile: bool = True             # v0.739 the chat model's abilities READ from OpenRouter's model list (pictures,
                                           # reasoning, tools, window) - a new GLM_MODEL needs no code change; off = old
    model_profile_dir: str = ""            # '' = data/modelprofile
    chat_files_by_code: bool = True        # parity gap 9a (v0.738): ONE way to make a file, like Claude - pylab writes
                                           # Word / Excel / PDF / PowerPoint with Python and they land in her chat
    chat_every_message: bool = True        # parity gap 1 (v0.738): every message reaches the model - the research plan
                                           # gate never answers for it, stop words still stop the work at once but the
                                           # model writes the reply (the OTP / CAPTCHA hand-over stays before the model)
    chat_graph: bool = False               # G0 (docs/LANGGRAPH_TURN_PLAN.md): the chat turn's think -> tools loop runs
                                           # as an official LangGraph StateGraph (agent/turngraph.py) over the SAME step
                                           # functions as the old loop, checkpointed per turn; off = the old loop only
    chat_graph_dir: str = "./data/turngraph"   # the graph's SQLite checkpoints (checkpoints.db)
    chat_graph_keep_finished: bool = False   # G1: keep a finished turn's checkpoints (tests / debugging); off =
                                           # deleted at END so the checkpoint file does not grow without limit
    chat_graph_ledger_keep_h: float = 24.0   # G1: tool-ledger rows of turns that never finished are dropped after this
    chat_plain_loop: bool = True           # parity Phase 5b (the loop): the model's answer ends the turn. Kept checks
                                           # run BEFORE the answer is shown and a corrected answer REPLACES the draft
                                           # in place (one reply): a false ACTION claim (sent / paid / booked /
                                           # deleted / published with no tool), a reminder promised with none set,
                                           # and research figures with no source (a dossier turn). Dropped: the
                                           # generic pakka self-check model call and the reviewer call on ordinary
                                           # hard answers. Kept as is: the goal nudge (only with an open kaam_plan
                                           # goal) and the promise nudge (aage). False = the old checks.
    seekh_enabled: bool = True             # v0.713 SEEKH MANCH: learn a way of working from a video (the
    seekh_max_per_day: int = 20            # `seekh_video` tool): the Gemini eyes watch, Claude distills the
    seekh_file_max_mb: int = 200           # steps with [m:ss] evidence, and they land in the two memories
    seekh_live_notes: bool = True          # v0.745 notes stream onto the Video Learner page as Gemini writes them
    seekh_resume: bool = True              # v0.785 a watch a restart cut is picked up again once (off = it is only reported lost)
    seekh_keep_media: bool = True          # v0.785 the learner keeps its own copy of an uploaded video (the chat lane is swept after 24 h)
    seekh_media_max_mb: int = 1024         # v0.785 kept videos per owner; over it the oldest copies go (the learned steps stay)
    interactive_page: bool = True          # v0.747 HOOLA INTERACTIVE: the console's video studio (one line -> scenes -> HyperFrames MP4)
    vocal_page: bool = True                # v0.787 HOOLA VOCAL: the console voice studio (speech, dialogue, readings, her voices, effects)
    hoola_code_page: bool = True          # v0.748 HOOLA CODE: Developer Sahayak as a console page (sessions, live steps, plan, PR, reviews)
    design_page: bool = True              # v0.777 HOOLA DESIGN: the multiplayer design editor (/console/design, /api/design/*, app/design)
    design_dir: str = ""                  # uploaded images + thumbnails ('' = data/design/<tenant>/)
    design_max_nodes: int = 200000        # layers in one file; creates beyond it are refused
    design_room_max: int = 64             # people (open tabs) in one file at a time
    design_checkpoint_ops: int = 200      # a room stores its snapshot every this many ops ...
    design_checkpoint_idle_s: float = 20.0   # ... and after this many quiet seconds (and when the last person leaves)
    design_autoversion_min: int = 30      # an automatic version every this many minutes of editing (0 = none)
    design_autoversion_keep: int = 50     # automatic versions kept per file (named ones are never pruned)
    design_socket_idle_s: float = 60.0    # an editor that sends nothing for this long (it pings every 15 s) is let go
    design_ai: bool = True                # v0.777 HOOLA DESIGN AI: "Ask Hoola" (one line -> a designed frame, POST /api/design/files/{id}/ai) + the hoola_design tool
    design_ai_model: str = ""             # the model that designs ('' = the house's strong model, else the chat model: agent/door.model_for)
    design_ai_engine: str = "auto"        # auto = the model when one is configured, else the built-in layouts | template = built-in layouts only
    design_ai_per_hour: int = 20          # designs one tenant may ask for in an hour (per server process)
    design_ai_timeout_s: float = 120.0    # one model call may take this long; after it the request fails plainly
    prompting_page: bool = True           # HOOLA PROMPTING: /console/prompting + /api/prompting/* + the Improve button
    prompting_ledger: bool = True         # NATIJA KHATA: the outcome ledger (shape only, never her words)
    prompting_fill_model: bool = True     # the one small model call that proposes slots (off = a brief from code alone)
    flow_page: bool = True                # v0.751 HOOLA FLOW: the Kaan pack as a console page (dictate, files, live captions, words, settings)
    flow_composer_mic: bool = True        # v0.751 the chat box mic dictates through Kaan when its engine is ready (else the browser's own)
    shilp_page: bool = True               # v0.752 ARTCRAFT IN CREATE: the Create studio's ArtCraft tool over the shilp lane (/api/shilp)
    cinema_page: bool = True              # v0.807 HOOLA CINEMA: the Create studio's Cinema section (/api/cinema): motion transfer, character
                                          # swap, item swap, restyle, talking photo, lip sync, picture to video, content factory, cinema still
    kie_api_key: str = ""                 # the video engine's key: VPS .env only (KIE_API_KEY), never in chat or the repo
    cinema_daily_jobs: int = 20           # Cinema jobs one person may start in an IST day (each spends the server's video-engine credits)
    seekh_file_max_s: int = 1800           # that already ship (procedures + operator recipe drafts) - off = off
    voice_adapt: bool = True               # v0.119 her own pauses / style / words / mis-hearings shape the call
    site_model: str = "claude-opus-5-5"     # v0.121 Website Sahayak: model that designs and writes every section
    site_edit_model: str = ""              # v0.121 small website edits ('' = anthropic_model)
    site_opus: bool = True                 # v0.225 every website section / fix / change on the App Sahayak Opus path (thinking, effort, retries, no quiet fallback)
    site_live_stream: bool = True          # v0.664 ASLI SAMAY: section writing streams its words to the Web Studio live canvas (same tokens)
    site_art: bool = True                  # v0.225 Opus writes a design DNA per look before the hero (art direction)
    site_critique: str = "all"             # v0.225 Opus looks at the built screenshots: all (v0.292, every page) | home | off
    site_critique_min: float = 7.5         # v0.225 a section scoring below this (out of 10) is redrawn once with the notes
    site_parallel: int = 3                 # v0.225 sections written at the same time inside one build
    site_ai_photos: int = 6                # v0.292 pictures a site gets before its looks (her own photos first, AI fills the gap; 0 = off)
    pexels_api_key: str = ""               # v0.292 optional licensed stock photos (official Pexels API) when the image models fail
    site_look_sections: int = 3            # v0.292 sections of the home page each of the 3 looks shows (hero + the next ones)
    site_look_parallel: int = 6            # v0.324 look sections written at the same time (3 looks x hero + page top)
    site_full_looks: bool = True           # v0.649 WEB STUDIO: each of the 3 looks is the WHOLE site (every page), words written once
    site_full_looks_max: int = 40          # v0.649 above this many sections the looks stay page tops (a big site would cost too much)
    site_kit: bool = True                  # v0.330 one design kit per site (.k-* components every section uses)
    site_critique_pages: int = 6           # v0.292 pages Opus reviews from their real screenshots (site_critique=all)
    site_max_pages: int = 150              # v0.315 BADI WEBSITE: most pages one site may have (designed + list items + legal)
    site_max_ai_pages: int = 40            # v0.315 most pages with their OWN designed sections (each section = one Opus call)
    site_parallel_big: int = 8             # v0.315 sections written at the same time on a big site (v0.400: 5 -> 8)
    site_check_pages: int = 40             # v0.315 pages the browser checks open on a big site (+2 items of every list)
    site_shop_max_products: int = 20000    # v0.538 BADA CATALOGUE: products one website shop may hold (was 500)
    site_shop_day_cap: int = 300           # orders a website shop takes in a day (spam guard; a big shop raises it)
    site_shop_ip_cap: int = 12             # orders from one address in 10 minutes
    site_gates: bool = True                # v0.551 SURAKSHA GATES: every website build is checked; a FAIL blocks going live
    site_look: bool = True                 # v0.606 SAAF NAZAR: the AI-look tells on every build (warn only, never blocks)
    site_look_fix: bool = True             # v0.606 ...and the per-section ones go into the first fix round once
    site_kept: bool = True                 # v0.617 KUCHH NA CHHOOTE: a change in her words is compared with the version before
    site_turnstile_site: str = ""          # v0.551 Cloudflare Turnstile site key (public) - both keys = forms get the box
    site_turnstile_secret: str = ""        # its secret (VPS .env only): the server checks every form post with Cloudflare
    site_check_parallel: int = 3           # v0.382 browsers that check a site's pages at once (FAST: big sites only)
    site_sms_provider: str = ""            # v0.434 website phone-OTP login: "" off | msg91 (DLT registered, her account)
    msg91_authkey: str = ""                # v0.434 MSG91 auth key (VPS .env only)
    msg91_otp_template: str = ""           # v0.434 MSG91 OTP template id (DLT approved)
    site_app_link: bool = True             # v0.414 every website web app runs on App Sahayak's backend + DIMAAG (old v0.305 sites moved by the worker)
    site_journeys: bool = True             # v0.402 visitor journeys (menu / form / shop / blog / language) on every version
    site_arena_max_inr: float = 3000       # v0.307 Design Arena: rupee ceiling of one run (each site ~Rs 100-300 with Opus)
    app_model: str = "claude-opus-5-5"     # v0.140 App Sahayak: EVERY design / screen / fix / change / Kotlin call (owner: Opus 5.5)
    app_model_fallback: bool = False       # v0.140 true = when Opus can't be reached, use the chat model / cheap brain instead
    app_model_tries: int = 5               # v0.140 tries per call when Opus is busy (429 / 5xx / overloaded / timeouts)
    tool_search_native: bool = True   # v0.563 CLAUDE KA AUZAAR: every tool declared, the rest deferred + tool_reference search
    engine_thinking: str = "adaptive"      # v0.560 EK DARWAZA: adaptive | off for every specialist engine through agent/door.py
    cad_model: str = "claude-opus-5-5"      # v0.560 CAD engine's model (was written into engineering/ai.py)
    motion_model: str = ""                 # v0.560 Hoola Motion's HTML plans ('' = anthropic_model, as before)
    app_thinking: str = "adaptive"         # v0.140 adaptive | off: Opus thinks before it designs (Claude decides how much)
    app_effort: str = "high"               # v0.140 effort for screens / Kotlin (low | medium | high | xhigh | max)
    app_art_effort: str = "xhigh"          # v0.140 effort for the art direction of each look
    app_critique: str = "key"              # v0.140 Opus looks at its own screenshots: key (home + tabs) | all | off
    app_critique_min: float = 8.0          # v0.140 a screen scoring below this (out of 10) is redrawn with the notes
    app_unique: bool = True                # v0.140 every app's layout DNA must differ from earlier apps on this server
    pgdb_allow_private: bool = False       # v0.147 Postgres: allow private / local database hosts (tests, her own LAN box via VPN)
    pgdb_row_limit: int = 200              # v0.147 rows a read may return to the model
    pgdb_timeout_s: int = 15               # v0.147 statement_timeout for reads (writes get 4x)
    blender_model: str = "claude-opus-5-5"  # v0.141 3D Studio: model that writes the Blender scripts (falls back to anthropic_model)
    sites_base_domain: str = ""            # v0.122 free addresses <name>.<this> (wildcard DNS proxied to this server)
    sites_origin: str = ""                 # v0.122 Cloudflare for SaaS fallback origin hostname (points at this server)
    sites_origin_ip: str = ""              # v0.122 this server's public IP (her own Cloudflare zone proxies to it)
    sites_direct_ip: str = ""              # v0.280 DIRECT MODE (like Lovable): her domain points straight at this IP (A @ + A www,
                                           # DNS only) + a _hoola TXT proves it is hers; the edge (Caddy on-demand TLS) makes the cert
    sites_cf_token: str = ""               # v0.122 Newtika's Cloudflare token: custom hostnames on the Hoola sites zone
    sites_cf_zone_id: str = ""             # v0.122 the Hoola sites zone id (Cloudflare for SaaS)
    sites_resell: bool = False             # v0.123 Hoola (Newtika) registers domains on its own registrar account
    sites_reg_cf_token: str = ""           # v0.123 Newtika's Cloudflare Registrar token (only with sites_resell)
    sites_reg_cf_account: str = ""
    sites_porkbun_key: str = ""            # v0.123 Newtika's Porkbun API key / secret (only with sites_resell)
    sites_porkbun_secret: str = ""
    sites_domain_month_inr: float = 5000   # v0.123 ceiling per owner per month for domain purchases
    sites_uptime_key: str = ""             # v0.224 shared secret for the outside uptime checker (GitHub Actions), >= 16 chars
    sites_backup_bucket: str = ""          # v0.224 S3-compatible bucket for the daily website files backup (off = empty)
    sites_backup_endpoint: str = ""        # e.g. https://<account>.r2.cloudflarestorage.com (empty = AWS S3)
    sites_backup_region: str = "auto"
    sites_backup_key_id: str = ""
    sites_backup_secret: str = ""
    sites_backup_keep_days: int = 14
    app_build_mode: str = ""               # v0.132 native Android builds: worker | github | local | "" (project ZIP only)
    app_build_url: str = ""                # v0.132 worker: https://build.example.com (server/app_builder on a separate machine)
    app_build_secret: str = ""             # v0.132 worker shared secret (HMAC of every request)
    app_build_gh_repo: str = ""            # v0.132 github: owner/repo of a PRIVATE builds repo with .github/workflows/hoola-build.yml
    app_build_gh_token: str = ""           # v0.132 github: fine-grained token for that repo only (contents + actions read/write)
    app_build_timeout_s: int = 1500        # v0.132 one Gradle build at most
    app_build_rounds: int = 4              # v0.132 compile-fix rounds before a screen gets its simple code version
    mcp_runner_url: str = ""               # v0.154 https://mcp-run.example.com (server/mcp_runner on a SEPARATE machine)
    mcp_runner_secret: str = ""            # v0.154 shared secret (HMAC of every control call)
    mcp_runner_trust_downloads: int = 1000  # v0.154 packages this popular are trusted for one tap without the full check
    voice_silence_ms: int = 550            # v0.181 (was 700): pause that ends your turn - people reply in ~0.2 s, 700+ felt like a pause on a bad line; her own pauses raise it again (voicestyle)
    voice_end_sensitivity: str = ""        # "" = Gemini's default | low (waits longer) | high (answers sooner)
    voice_prefix_padding_ms: int = 300     # speech kept from just before the voice was detected (100-300)
    voice_start_sensitivity: str = "low"   # low = TV / far voices / clatter don't count as you starting to talk | high | ""
    voiceid_vad: bool = True               # v0.53 Awaaz Pehchaan takes only chunks Silero calls a voice
    voice_vad_need: float = 0.5            # v0.53 phone Silero VAD: speech probability needed to count as talking
    voice_vad_fast: float = 0.85           # very sure it's a voice: barge-in opens after 160 ms instead of 240 ms
    voice_vad_idle_gate: bool = True       # while nobody talks, pure noise (fan, traffic, clatter) reaches Gemini as silence
    voice_resume_after_noise_s: float = 1.5  # he was cut off but nobody spoke: carry on after this long (0 = off)
    operator_preflight: bool = True        # v0.92 check a website job's site from this server first; refused -> her PC
    scrape_respect_robots: bool = True     # v0.477 scrape tools refuse paths the site's robots.txt disallows for bots
    scrape_stealth_enabled: bool = False   # v0.477 allow scrape_stealth to launch the stealth browser (RAM-heavy; needs `scrapling install` once)
    # v0.537 CRAWL BRAIN (the crawl4ai ideas, hand-built). Every one is OFF or neutral by default.
    scrape_proxies: str = ""               # v0.537 comma list: ip:port[:user:pass] | url | DIRECT. Empty = fetch direct, as before
    scrape_proxy_max_fails: int = 3        # v0.537 failures before a proxy is rested
    scrape_proxy_rest_s: int = 300         # v0.537 how long a failing proxy rests
    scrape_clean_default: bool = False     # v0.537 prune boilerplate on EVERY scrape_page (she can also ask per call)
    scrape_crawl_question_mode: str = "best"   # v0.537 frontier mode when a crawl job carries a question: best | bfs
    scrape_cache_enabled: bool = True      # v0.481 serve repeat scrapes from the per-tenant page cache within max_age
    scrape_cache_max_age: int = 1800       # v0.481 default seconds a cached page stays fresh for the scrape tool (0 = always fresh)
    scrape_crawl_enabled: bool = True      # v0.486 background crawl jobs (crawl_start -> worker tick -> crawl_status/results)
    scrape_crawl_max_pages: int = 20       # v0.486 default page budget per crawl job (crawl_start clamps to 50)
    scrape_crawl_max_running: int = 1      # v0.486 crawl jobs running at once, globally (HTTP-only, politeness first)
    scrape_crawl_stale_s: int = 180        # v0.486 a running crawl without a heartbeat this long is resumed from its checkpoint
    scrape_crawl_tries: int = 3            # v0.486 a crawl job is started at most this many times before it is failed
    graphify_enabled: bool = True          # v0.496 Graphify code graph (graph_build / graph_ask); inert until the graphifyy package is installed
    graphify_bin: str = ""                 # v0.496 path to the graphify CLI ("" = next to the server Python, then PATH)
    graphify_build_timeout_s: int = 600    # v0.496 one repo map may run this long, then its process group is killed
    graphify_query_timeout_s: int = 60     # v0.496 one graph question
    graphify_max_repo_mb: int = 80         # v0.496 refuse a repo tarball bigger than this (unpacked cap = 4x)
    graphify_max_files: int = 8000         # v0.496 files unpacked per repo
    graphify_keep_repos: int = 5           # v0.496 mapped repos kept per tenant, oldest dropped
    scrape_crawl_keep_days: int = 7        # v0.486 finished crawl jobs (and their pages) older than this are forgotten
    dhara_enabled: bool = True             # v0.502 DHARA - her workflows (the n8n lane: save/run/schedule/webhook)
    dhara_max_steps: int = 40              # v0.502 top-level steps per workflow (dhara_save clamps)
    dhara_loop_max: int = 50               # v0.502 iterations per loop step
    dhara_run_timeout_s: int = 600         # v0.502 one run's wall clock cap
    dhara_max_running: int = 1             # v0.502 runs executing at once, per tenant (politeness first)
    dhara_stale_s: int = 180               # v0.502 a running run without a write this long is resumed from its checkpoint
    dhara_tries: int = 3                   # v0.502 a run is started at most this many times before it is failed
    dhara_keep_runs_days: int = 30         # v0.502 finished runs older than this are forgotten (at most 40 kept)
    dhara_approval_hours: int = 24         # v0.502 an approval step waiting longer than this fails honestly
    dhara_webhook_enabled: bool = True     # v0.502 POST /api/dhara/hook/{token} (token sha256-hashed at rest)
    dhara_summaries_enabled: bool = True   # v0.512 a computed summary (steps/parks/tries/wall/cost) on every finished run
    dhara_dsl_enabled: bool = True         # v0.512 dhara_dsl export/import (the Dify DSL idea: portable workflow files)
    dhara_dsl_max_kb: int = 64             # v0.512 one DSL envelope's size cap
    gyaan_annotation_enabled: bool = True  # v0.512 her approved jawabs (the Dify annotation-reply idea) served before retrieval
    gyaan_annotation_fuzzy: float = 0.92   # v0.512 difflib ratio threshold for a fuzzy annotation hit (exact always wins)
    gyaan_annotation_max: int = 200        # v0.512 approved-jawab pairs per tenant
    officehours_enabled: bool = True       # v0.495 office hours (the gstack THINK/PLAN lane: design docs + plan reviews)
    officehours_keep_docs: int = 30        # v0.495 baithak docs kept per tenant; older ones (and their reviews) are forgotten
    call_receipt: bool = True              # v0.91 after a call: a short card of what was decided and what really ran
    voice_tool_ack: bool = False           # v0.625 OFF: the "ek second" clips come from a SEPARATE TTS model (a legacy one on failure, cached forever) - a different / radio-like voice mid-call; Gemini Live says its own filler line
    voice_backchannel: bool = False        # v0.625 OFF (same TTS-clip voice problem); v0.205 KAAN KAAPI: tiny listener murmurs in her pauses + one progress sound on a long silent tool (kill switch)
    voice_prosody: bool = True             # v0.208 AWAAZ-3: her TurnMeter prosody sharpens the feeling note - vetoes a glad her voice contradicts, confirms a low, adds the thinking-pauses rider (kill switch; off = the v0.202 words-only engine)
    voice_soorat: bool = True              # v0.220 SOORAT: his energy follows her transitions - a state flip names the move, the fresh tone tints the scripted moments (acks skip the bright clips while she is heavy/tense, stall/result/reconnect notes carry the tone); off = the v0.219 engine
    # v0.264 OPENAI VOICE (Phase 1 of "two engines, she chooses"): a second call engine for "real voice" (breaths,
    # hmm, light laughs). Gemini stays the default and untouched; OpenAI is used only when the owner picks it, a key is
    # set, and the month's budget / her minutes allow - otherwise the call quietly runs on Gemini.
    openai_api_key: str = ""                          # VPS .env only (OPENAI_API_KEY), never in chat or the repo
    voice_openai_enabled: bool = False
    voice_lean_tools: bool = True    # v0.627 the call declares only LEAN_TOOLS (Gemini bills the whole tool list on every reply); the rest via santosh_kaam
    voice_brain: bool = True         # v0.630 HAIKU DIMAAG: Gemini Live is ONLY the voice (hears + speaks); every ask goes to the Hoola brain (voice_brain_model) with every chat tool
    voice_brain_model: str = "claude-haiku-5-5"
    voice_checkin_s: int = 150    # v0.652 a call ask still running: one 'abhi bhi kar raha hoon' line this often
    voice_checkin_max: int = 3    # ...at most this many times (0 = off)
    kaam_stop_words: bool = True   # v0.649 SACH MEIN ROKO: her 'roko / cancel karo' stops running work before the turn waits
    call_split: bool = True   # v0.646 ALAG CALL: a phone that asks (split=1) gets each call on its own record (Calls section)
    voice_brain_yaad: bool = False       # v0.644 diary / facts block on a call brain turn (never ready in time on her calls)
    voice_brain_memory_s: float = 2.5    # v0.638 a call brain turn waits at most this for diary / job state / coder memory
    chat_memory_s: float = 6.0          # v0.704 a chat turn reads diary / job state / card news / coder memory in parallel, at most this long
    voice_brain_result_chars: int = 1500   # v0.636 an earlier exchange's tool result cut to this on a call brain turn (0 = keep)
    voice_brain_history: int = 8      # v0.634 (12) -> v0.636 8: a call brain turn reads the summary + this many recent exchanges (0 = the whole chat)
    voice_brain_wait_s: int = 20      # v0.630 the voice waits this long for the brain's answer, then says it is working   # v0.630 the call's brain ('' = the chat model); hard / long asks still go up (Opus / Sonnet)
    voice_reminder_guard: bool = True   # v0.624 a create_reminder with no reminder ask in her words goes to santosh_kaam                # v0.622 owner: every call on Gemini; True brings the OpenAI choice back
    voice_openai_model: str = "gpt-realtime-2.1-mini"   # the mini only: the full model costs 4-10x Gemini
    voice_openai_voice_m: str = "cedar"
    voice_openai_voice_f: str = "marin"
    voice_openai_transcribe: str = "gpt-4o-mini-transcribe"
    voice_openai_month_usd: float = 10.0              # whole app, per calendar month (IST); 0 = no OpenAI calls
    voice_openai_user_min: int = 120                  # minutes per user per month on OpenAI; 0 = unlimited
    voice_openai_tenants: str = ""                    # who may pick it ("" = only the main tenant: the owner's trial; "*" = all)
    voice_openai_eagerness: str = "medium"            # v0.285 semantic VAD: medium waits at most ~4 s (low = up to 8 s, felt like not listening)
    # v0.276 COMPOSIO: one Newtika project key gives every user Slack / Notion / Jira ... through Composio's official
    # OAuth; users never make a Composio account. Each user is a separate Composio user_id fixed by the server.
    # v0.303 SAAF CONNECT (owner: "REMOVE ALL JUST KEEP COMPOSIO MCPS AND WORKING PLUG IN"): the Connect tab and
    # bazar_find show only what really works (Composio apps + working plugins); false = the old full catalogue
    connect_clean: bool = True
    # v0.319 Swiggy / Zomato accept only partner-approved apps at their sign-in (her live test: the request is refused).
    # Until Newtika is approved these stay hidden in the clean view; true = show them again.
    food_partner_approved: bool = False
    composio_api_key: str = ""                        # VPS .env only (COMPOSIO_API_KEY), never in chat or the repo
    composio_webhook_secret: str = ""                 # COMPOSIO_WEBHOOK_SECRET: signs "connection expired" events
    composio_base_url: str = "https://backend.composio.dev/api/v3.1"
    composio_toolkits: str = ""                       # comma list to replace the built-in app list ("" = the default list)
    composio_user_monthly_calls: int = 300            # per user per calendar month; 0 = unlimited
    composio_monthly_calls: int = 90000               # whole app per month (stays inside the free 1 lakh); 0 = unlimited
    voice_openai_breath: bool = False                 # v0.290 OFF: the generated breath sounded like radio static before his first word (owner)
    voice_openai_session_min: int = 50                # OpenAI sessions end at 60 min: move to a fresh one before that
    # v0.816 TEEN AWAAZEIN (owner: "LETS DEPLOY ALL --- USER WILL CHOOSE THE VOICE THEY WANT"): three more call engines
    # beside Gemini - Grok Voice 3.0 (xAI), GPT-Live-1 (OpenAI) and Phonic 1. Each needs its key in the VPS .env, has
    # its own monthly budget (whole app) and per-user minutes; out of key / budget / minutes = the call runs on Gemini
    # and the Call voice screen says why. Gemini stays the default and is never changed by any of this.
    xai_api_key: str = ""                             # VPS .env only (XAI_API_KEY)
    phonic_api_key: str = ""                          # VPS .env only (PHONIC_API_KEY)
    voice_grok_enabled: bool = True
    voice_grok_model: str = "grok-voice-3.0"
    voice_grok_voice_m: str = "rex"
    voice_grok_voice_f: str = "eve"
    voice_grok_usd_min: float = 0.08                  # xAI's list price per minute (its stream carries no usage numbers)
    voice_grok_month_usd: float = 25.0                # whole app per calendar month (IST); 0 = off
    voice_grok_user_min: int = 60                     # per user per month; 0 = unlimited
    voice_grok_tenants: str = "*"                     # who may pick it: "*" = everyone, "" = only the owner, or a list
    voice_gptlive_enabled: bool = True
    voice_gptlive_model: str = "gpt-live-1"
    voice_gptlive_voice_m: str = "stone"
    voice_gptlive_voice_f: str = "nira"               # OpenAI's Hindi voice
    voice_gptlive_usd_min: float = 0.05               # OpenAI's price for the voice layer (billed per second); Hoola's brain is counted as usual
    voice_gptlive_month_usd: float = 25.0
    voice_gptlive_user_min: int = 60
    voice_gptlive_tenants: str = "*"
    voice_phonic_enabled: bool = True
    voice_phonic_model: str = "phonic-1"
    voice_phonic_voice_m: str = "sandeep"             # Phonic's voice with an Indian accent
    voice_phonic_voice_f: str = "divya"
    voice_phonic_usd_min: float = 0.07                # Phonic Starter, one price per conversation minute
    voice_phonic_month_usd: float = 25.0
    voice_phonic_user_min: int = 60
    voice_phonic_tenants: str = "*"
    voice_ack_tts_model: str = "gemini-3.8-flash-tts"   # v0.181 (was gemini-2.5-flash-preview-tts): new TTS, far more natural delivery; legacy model is the automatic fallback
    voice_compress_trigger: int = 60000    # v0.224 Gemini Live context compression starts here (0 = Google's default near the limit)
    voice_compress_target: int = 35000     # ...and slides the window back to about this many tokens
    voice_brain_compress_trigger: int = 8000   # v0.632 KAAN CHHOTA: with voice_brain the call keeps only the last few minutes (the brain holds the memory), so each reply re-reads ~8k tokens at most
    voice_brain_compress_target: int = 4000
    voice_tool_behavior: bool = True       # v0.473 slow call tools NON_BLOCKING (he keeps talking), quick ones BLOCKING (exact answer, no guessing); false = model default for all
    voice_affective: bool = True           # v0.181 affective dialog: he answers with the emotional tone he HEARS (happy with her, gentle when she is low). If Gemini refuses the field for a model, the call retries without it and remembers (voice.py _AFFECTIVE_OK)
    # --- Awaaz Pehchaan: who is talking (owner / family) from the voice; free models, CPU (sherpa-onnx) ---
    voiceid_models_dir: str = "./data/voiceid_models"   # tools/setup_voiceid.sh downloads the two models here
    voiceid_match: float = 0.30            # similarity needed to say "this is X" (0..1)
    voiceid_margin: float = 0.06           # and this much ahead of the next closest person
    voiceid_min_speech_s: float = 1.6      # speech needed before the first guess in a call
    voice_resume_grace_s: int = 25         # a dropped phone connection can re-join the same call within this time
    voice_park: bool = True                # v0.617 HAMESHA JUDA: a quiet call leaves Gemini (billed per second, even silence) and stays connected
    voice_park_after_s: int = 90           # ...after this long with nobody speaking and nothing running
    voice_park_grace_s: int = 900          # ...and a parked call waits this long for her phone to come back (nothing billed)
    focus_user_words: int = 6              # v0.200 her newest messages kept WORD-FOR-WORD in the focus block (a human remembers what you just SAID, not a summary of it)
    focus_word_chars: int = 600            # v0.200 cap per saved message inside the focus block
    focus_max_chars: int = 4000            # v0.200 the whole focus block's cap ("focused" = small and exact, never a dump)
    voice_continuation_min: int = 60       # v0.200 a call that died within this many minutes is CONTINUED by the next call, never greeted fresh
    voice_quiet_notes: str = "auto"        # v0.150 quiet context notes mid-call: auto (by model) | client_content | queue
    voice_safe_setup: bool = True          # v0.150 Gemini refuses the call setup: retry step by step with fewer extras
    voice_side_talk: bool = True           # v0.142 talk not meant for Hoola (her phone call, people in the room) is never answered
    voice_hold_max_s: int = 900            # v0.142 side-talk hold longer than this ends the call (Gemini audio is billed)
    voice_call_hold_max_s: int = 3600      # v0.142 her other phone call longer than this ends the Hoola call
    voice_tool_wait_s: int = 12            # v0.86 (was 25) a call waits this long for a big job, then talks on and gets told when it is done
    voice_tool_timeout_s: int = 60         # any other call tool is cut off after this
    voice_stall_watch: bool = True         # v0.211 Gemini goes quiet mid-call: one nudge, then a forced reconnect - the call is never silently dead
    voice_stall_nudge_s: int = 14          # her turn open + nobody has spoken this long: the nudge note goes to Gemini
    voice_stall_reconnect_s: int = 28      # still nothing this long after the nudge: the session is closed and reconnected
    voice_followup_min: int = 720          # v0.211 a result that landed after the call closed is told on her next call within this window
    voice_auto_rescue: bool = True         # v0.211 a tool failing twice hands the work to the full agent by itself (the call never just gives up)
    voice_setup_hard_keep_s: int = 3600    # v0.211 heavy setup losses (compression / tools) self-heal after this long - memory and tools come back on their own
    voice_ring: bool = True                # v0.219 ON: the native side learned the kind (SantoshPush turns the push into the wake: path + auto-call); off = the v0.214 behaviour
    voice_ring_reminders: bool = True      # v0.621 a due reminder with no live call rings her and the call says it
    voice_ring_reminder_max_day: int = 12  # ...her own reminders: quiet hours do not apply, only this sanity cap
    voice_ring_max_day: int = 2            # v0.211 rings per tenant per day (the phone is not an alarm clock)
    push_quiet: str = ""                   # wave 13: quiet hours for pushes ("" = the ring's voice_ring_quiet)
    push_night_hold: bool = True           # wave 13: non-urgent pushes are held in her quiet hours, the newest few sent after
    voice_ring_quiet: str = "22-8"         # v0.211 quiet hours in the tenant's own timezone - no rings inside

    # --- Hoola Coder (v0.473): persistent session memory - capture -> spool -> observer -> vault ---
    coder_enabled: bool = True             # the whole surface (capture, observe, inject, routes); off = no memory is written or read
    coder_observe: bool = True             # the observer model calls; false keeps capture+search but writes nothing new
    coder_dir: str = "./data/coder"        # the vault: coder.db + spool/ + modes/
    coder_mode: str = "code"               # the observer taxonomy (modes/<name>.json overrides the builtin)
    coder_batch_max: int = 6               # tool events per observer model call (claude-mem batch discipline)
    coder_retain_days: int = 0             # 0 = keep forever (a malformed value is read as 0, never a purge)

    # --- Hoola Self-Teach (v0.474): skills + the nudge fork (Hermes's self-teaching loop) ---
    coder_skills: bool = True              # the SKILL.md store + skill_manage + primer injection (files + FTS5, zero model cost)
    coder_nudge: bool = False              # the self-teaching fork (model calls: bake on the VPS, then flip to true)
    coder_nudge_every: int = 10            # turns between reflections (Hermes nudge_interval = 10)
    coder_nudge_max_writes: int = 4        # max observations + skill ops ONE reflection may write

    # --- Hoola Skill Desk (v0.481): the skills platform - seeds, import/export, the share shelf ---
    coder_skills_seed: bool = True         # the 57-skill seed library copied into a fresh tenant once (create-if-missing)
    coder_skills_share: bool = True        # the anonymised share lane: nominations need the curator armed, publishing needs her tap
    coder_skills_share_min_reads: int = 3  # real reads (the telemetry) before a skill may be nominated
    coder_skills_share_max_pending: int = 10  # nominations waiting for the owner at once

    # --- Hoola UIUX Pro Max (v0.486): the vendored design database behind ONE local tool ---
    coder_uiux: bool = True                # uiux_design over coder/uiux/ (MIT engine, pure stdlib, zero network, zero brain calls)

    # --- Hoola Swarm (v0.475): self-spawning subagents for parallel work ---
    coder_delegate: bool = False           # the delegate_task tool (bake on the VPS, then flip to true)
    coder_delegate_max_children: int = 3   # concurrent child agents (Hermes 10; tightened for a voice box)
    coder_delegate_timeout_s: int = 120    # per-child hard timeout (Hermes None; unbounded is wrong here)

    # --- HOOLA SMART HOME (v0.479): Home Assistant REST - ghar ka control, HOME gate PC se alag hai ---
    home_control: bool = False              # the HOME gate (default OFF - bake on the VPS, then flip to true)
    home_assistant_url: str = ""            # e.g. http://192.168.1.10:8123 (the HA base URL, no trailing slash)
    home_assistant_token: str = ""          # HA long-lived access token (profile -> Security -> Tokens); never in chat
    # --- KAAN PACK v0.589 (WhisperAI Wave W0): transcription core, AUDIO gate PC/HOME se alag, default OFF ---
    kaan_audio: bool = False                # the AUDIO gate (default OFF - KAAN_AUDIO=1 on the VPS flips it)
    kaan_diarize: bool = True               # v0.610 KAAN W1: pause-turn diarization (local, CPU-light - kill switch; KAAN_DIARIZE=0 par band)
    kaan_live_dir: str = "./data/kaan_live"  # v0.618 KAAN W2: live-caption PCM spines (16k mono, sirf uske server par)
    kaan_quota_audio_min: int = 0           # v0.667 KAAN W6: per-tenant monthly audio-minutes cap (0 = no cap, default; resets on the 1st)
    kaan_retention_days: int = 0            # v0.667 KAAN W6: transcripts older than N days are swept daily (pinned survive; 0 = keep forever, default)
    kaan_voiceprint: bool = False           # v0.667 KAAN W6: voiceprint diarization at transcribe time (biometric - needs KAAN_VOICEPRINT=1 AND KAAN_RETENTION_DAYS>0)
    # --- v0.486.0 BYOX SKILL PACK: Build-Your-Own-X 31 categories, seed default on ---
    byox_enabled: bool = True               # BYOX skill pack seeds on first open (default ON)
    # --- Claude skills pilot (docs/CLAUDE_SKILLS_PILOT_PLAN.md): Apache-2.0 Anthropic skills seeded once per tenant ---
    claude_skills_enabled: bool = True      # skillpack/claude/* seeds on first open (create-if-missing, hers win)
    # --- v0.495.0 PROG PACK: the vetted-library registry + the windows script lane ---
    progpack_enabled: bool = True           # PROG pack seeds on first open (default ON)
    sp_enabled: bool = True                 # superpowers lane seeds on first open under its own stamp (default ON)
    # --- FE PACK: the HyperFrames template packs + campaign email templates + UI kit ---
    fepack_enabled: bool = True             # FE pack seeds on first open (default ON)
    # --- CS PACK: the zoo expansion radar + the operator loop's dialogue/QA patterns ---
    cspack_enabled: bool = True             # CS pack seeds on first open (default ON)
    # --- BD PACK: the public-dataset eval benchmarks + the campaign-graph analytics ---
    bdpack_enabled: bool = True             # Big Data pack seeds on first open (default ON)
    # --- Hoola Curator (the v0.480 weekly consolidation): the weekly memory consolidation ---
    coder_curator: bool = False            # scan + arbitrate + promote (bake on the VPS, then flip to true)
    coder_curator_every_hours: int = 168   # one consolidation a week (the claude-mem cadence)
    coder_curator_max_pairs: int = 20      # pending pairs the brain arbitrates per tenant per run
    coder_curator_max_merges: int = 10     # merges per run; the rest stays pending (soft merges, revivable)

    # --- Hoola SAPNE (v0.484): the NIGHTLY curator (OpenClaw's dreaming sweep ported) ---
    coder_dreams: bool = False             # the light+deep consolidation passes (bake on the VPS, then flip)
    coder_dreams_light_hours: int = 26     # the nightly window (26h catches the slow clock)
    coder_dreams_deep_days: int = 7        # the weekly window (deep subsumes light when both due)
    coder_dreams_max_writes: int = 4       # max curated rows ONE pass may write or rewrite
    coder_dedup_min_docs: int = 10         # the Tier-1 scan's corpus gate (IDF on 3 documents is astrology)

    # --- Hoola Context7 (v0.501): up-to-date library docs into the context, the upstash/context7 port ---
    coder_docs7: bool = False              # the docs7 tool (outbound network: bake on the VPS, then flip)
    context7_api_url: str = "https://context7.com/api"  # upstream default (constants.ts:14; env-overridable there)
    context7_api_key: str = ""             # optional Bearer (ctx7sk-...); empty = anonymous rate limits; never in chat
    coder_docs7_timeout_s: int = 20        # upstream ceiling 60s (p99.9 ~3.2s); a voice box drops, not waits
    coder_docs7_max_per_hour: int = 12     # the <=3-per-question law, enforceable locally (upstream 429s server-side)
    coder_docs7_ttl_hours: int = 168       # the vault IS the cache: a week before the same query re-fetches

    # --- Hoola 21st (v0.512): the 21st.dev UI catalog + hosted AI generation, the 21st-dev/magic-mcp port ---
    coder_magic21: bool = False            # the magic21 tool (outbound network: bake on the VPS, then flip)
    magic21_api_url: str = "https://21st.dev/api/mcp"   # upstream default (mcp.json:3; env MCP_URL_21ST there)
    magic21_api_key: str = ""              # x-api-key from 21st.dev/mcp (REQUIRED upstream); BYOK - keys never in chat
    coder_magic21_timeout_s: int = 20      # ONE attempt, drop-don't-wait: a live turn cannot wait on a marketplace
    coder_magic21_max_per_hour: int = 12   # per-tenant rolling-hour window over OPS (the three wire POSTs are the bridge's own business)
    magicpack_enabled: bool = True         # the mg- seed (the 21st.dev UI skill) seeds on first open under its own stamp (default ON)

    # --- Hoola Crew (v0.514): the crewAI port, role-based agent crews over the delegate machinery ---
    coder_crew: bool = False               # the crew_run tool (brain rounds, not network - but real cost: bake, then flip)
    coder_crew_max_agents: int = 6         # a voice box is not a cluster (library backstop MAX_AGENTS doubled at the door)
    coder_crew_max_tasks: int = 12         # the task-list cap (library backstop MAX_TASKS doubled at the door)
    coder_crew_task_timeout_s: int = 180   # per task/manager-round ceiling (the delegate child shape, widened for a worker)
    coder_crew_timeout_s: int = 600        # the whole-crew wall clock; partial work is not kept (honest)
    crewpack_enabled: bool = True          # the cr- seed (crew plays) seeds on first open under its own stamp (default ON)

    # --- THEORY PACK (v0.547): the vision-lane syllabus + the agent-architecture research loop ---
    thpack_enabled: bool = True            # the th- seed (the awesome Theory read) seeds on first open under its own stamp (default ON)

    # --- EDITORS PACK (v0.548): the VS Code cockpit + the Neovim cockpit - drive Hoola from inside the IDE ---
    edpack_enabled: bool = True            # the ed- seed (the awesome Editors read) seeds on first open under its own stamp (default ON)
    # --- OMNI PACK (v0.561): the 18 awesome-list lanes, each its own once-ever stamp ---
    gapack_enabled: bool = True       # the ga- seed (the awesome Gaming read) seeds on first open under its own stamp (default ON)
    devpack_enabled: bool = True      # the de- seed (the awesome Dev-Environment read) seeds on first open under its own stamp (default ON)
    enpack_enabled: bool = True       # the en- seed (the awesome Entertainment read) seeds on first open under its own stamp (default ON)
    dbpack_enabled: bool = True       # the db- seed (the awesome Databases read) seeds on first open under its own stamp (default ON)
    mepack_enabled: bool = True       # the me- seed (the awesome Media read) seeds on first open under its own stamp (default ON)
    lepack_enabled: bool = True       # the le- seed (the awesome Learn read) seeds on first open under its own stamp (default ON)
    secpack_enabled: bool = True      # the se- seed (the awesome Security read) seeds on first open under its own stamp (default ON)
    cmpack_enabled: bool = True       # the cm- seed (the awesome CMS read) seeds on first open under its own stamp (default ON)
    hapack_enabled: bool = True       # the ha- seed (the awesome Hardware read) seeds on first open under its own stamp (default ON)
    bupack_enabled: bool = True       # the bu- seed (the awesome Business read) seeds on first open under its own stamp (default ON)
    wopack_enabled: bool = True       # the wo- seed (the awesome Work read) seeds on first open under its own stamp (default ON)
    nepack_enabled: bool = True       # the ne- seed (the awesome Networking read) seeds on first open under its own stamp (default ON)
    dcpack_enabled: bool = True       # the dc- seed (the Decentralized stance: Tor/privacy only) seeds on first open under its own stamp (default ON)
    hspack_enabled: bool = True       # the hs- seed (the awesome Health read, non-core) seeds on first open under its own stamp (default ON)
    evpack_enabled: bool = True       # the ev- seed (the awesome Events read) seeds on first open under its own stamp (default ON)
    tepack_enabled: bool = True       # the te- seed (the awesome Testing read) seeds on first open under its own stamp (default ON)
    mipack_enabled: bool = True       # the mi- seed (the awesome Miscellaneous read) seeds on first open under its own stamp (default ON)
    repack_enabled: bool = True       # the re- seed (the awesome Related read) seeds on first open under its own stamp (default ON)


    # --- Hoola AEP trace (v0.520): the LangSmith layer self-hosted - tracers, run trees, astream_events ---
    aep_trace: bool = False                # run persistence (vault rows typed 'aep_run') + the /api/aep/runs explorer - bake, then flip
    aep_trace_redact: bool = True          # redaction before storage (strip_private + redact_secrets); a test seam, prod keeps True

    # --- email (Baat/Chat can read your inbox and send approved replies). App password, not your login password. ---
    email_address: str = ""
    email_password: str = ""                # app password (Gmail/Outlook/Zoho "app password")
    email_imap_host: str = ""               # auto-detected from the address when blank
    email_imap_port: int = 993
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_sender_name: str = ""             # name shown on sent mail (defaults to the address)
    # each user can also connect their own Gmail / Outlook (OAuth) or any mailbox (IMAP + app password) in the app
    ms_oauth_client_id: str = ""            # Microsoft Entra app (Outlook / Hotmail / Microsoft 365 mail)
    ms_oauth_client_secret: str = ""
    ms_oauth_tenant: str = "common"         # "common" = personal + work accounts
    mail_bulk_per_minute: int = 12          # bulk mail pace (each person gets their own mail)
    mail_bulk_daily_cap: int = 300          # per mailbox per day (Gmail allows ~500 for personal accounts)
    mail_bulk_max: int = 1000               # recipients in one bulk mail
    mail_max_attach_mb: int = 18            # total attachments per mail (Gmail/Outlook limit is ~25 MB encoded)
    # v0.701 PAKKA ATTACHMENT: a draft keeps its OWN copy of every attached file (chat uploads / Hoola-made / Drive)
    # so a Bhejo tap next day, a scheduled send (up to 60 days) or a multi-day bulk never meets a deleted file.
    mail_keep_dir: str = "./data/mail_attach"
    mail_keep_days: int = 70                # kept copies older than this are swept (schedules go up to 60 days)
    notebook_tts_model: str = "gemini-3.8-flash-tts"            # v0.155 Audio / Video Overview voices (expressive, 2 hosts, 20 Indian langs)
    notebook_tts_legacy_model: str = "gemini-2.5-flash-preview-tts"   # used when the new TTS refuses (older API path)
    notebook_model: str = "claude-opus-5-5"   # v0.155 writes Studio items (scripts, decks, reports); '' = anthropic_model
    notebook_paint: bool = True               # v0.155 slides / infographic / video frames painted by Nano Banana (else HTML)
    notebook_image_models: str = ""           # comma list; '' = paint.PRO_CHAIN (gemini-3-pro-image first)
    notebook_frame_models: str = ""           # comma list; '' = paint.FRAME_CHAIN (gemini-nano-banana-2.1 first)
    notebook_image_size: str = "2K"           # 1K | 2K | 4K (4K costs ~2x)
    youtube_api_key: str = ""               # YouTube Data API v3 key for search / public video stats (Google Cloud)
    pagespeed_api_key: str = ""             # optional: PageSpeed Insights API key (higher quota for SEO checks)
    indiamart_enabled: bool = True           # v0.280 IndiaMART's own MCP (buyer search: products, prices, suppliers)
    indiamart_mcp_url: str = "https://imgpt.indiamart.com/mcp"   # no key / sign-in; read-only tools only
    game_model: str = "claude-opus-5-5"     # v0.370 Game Desk: writes the design doc + GDScript ('' = anthropic_model)
    mospi_enabled: bool = True               # v0.348 MoSPI eSankhyiki: official Govt of India statistics, built in
    mospi_mcp_url: str = "https://mcp.mospi.gov.in/mcp"   # no login, read-only
    motion_dir: str = "./data/motion"         # Hoola Motion MP4s (kept until the owner deletes them)
    motion_keep: int = 60                      # newest videos kept per owner
    reels_gemini_model: str = ""          # Hoola Reels: understands shared reels ("" = youtube_gemini_model)
    youtube_gemini_model: str = "gemini-flash-latest"   # v0.560 Google's alias for its newest Flash (was 2.5); usage.install falls back to gemini-2.5-flash if it is refused   # watches public YouTube videos to summarise / answer (official Gemini API)
    hivision_url: str = ""                 # v0.51 e.g. http://127.0.0.1:8085 (docker linzeyi/hivision_idphotos): ID photos
    gotenberg_url: str = ""                # v0.49 e.g. http://127.0.0.1:3005 (docker gotenberg): Office files get page-1 previews
    hoola_enrich: bool = True              # avatars look at what arrives (vision / video) and suggest replies
    hoola_image_model: str = ""   # "" = app/photogen fast chain; avatars making pictures for the Hoola Network (sent only after her tap)
    photo_fast_models: str = ""   # comma list overriding photogen.FAST
    photo_best_models: str = ""   # comma list overriding photogen.BEST
    # --- App Jaanch: check an APK / EXE before installing, with REA (github.com/morluto/rea), static analysis only ---
    appcheck_enabled: bool = True           # also needs REA_BIN; off automatically when REA is not installed
    rea_bin: str = ""                       # absolute path to the pinned `rea` launcher (npm rea-agents@6.8.0)
    rea_jadx_jar: str = ""                  # jadx-headless-mcp-0.7.1-all.jar (SHA-256 checked at install) for APKs
    rea_java_home: str = ""                 # optional JDK 17+ for JADX (else java on PATH)
    rea_home: str = ""                      # REA's private HOME / work folders (default ./data/rea_home)
    rea_timeout_s: int = 300                # per REA call
    rea_node_heap_mb: int = 2048
    appcheck_max_mb: int = 400              # biggest file App Jaanch accepts
    # --- HOOLA FRAMES (v0.471): HyperFrames render worker — HTML composed by the model, deterministic MP4 out ---
    frames_enabled: bool = True             # also needs FRAMES_BIN; off automatically when the CLI is not installed
    frames_bin: str = ""                    # absolute path to the pinned `hyperframes` launcher (npm hyperframes@0.9.6)
    frames_node_dir: str = ""               # optional Node 22+ bin dir ONLY for the worker (never touches pm2's node)
    frames_root: str = ""                   # per-tenant project root (default ./data/frames)
    frames_timeout_s: int = 900             # hard wall for one render (process group killed past it)
    frames_queue_wait_s: int = 3            # how long a second render waits for the one-at-a-time lock before refusing
    frames_disk_cap_gb: float = 10.0        # janitor trims finished projects when the root passes this
    frames_keep_h: int = 6                  # finished projects older than this are swept
    frames_per_tenant: int = 6              # LRU project slots per tenant
    frames_max_mb: int = 200                # biggest single asset file accepted into a project
    # --- Hoola Network: avatars talking to avatars (on this server and, with federation, on others) ---
    hoola_domain: str = ""                  # this server's Hoola domain (default: host of PUBLIC_BASE_URL)
    hoola_federation: bool = True           # talk to Hoola avatars on other servers (public https only)
    hoola_blocked_servers: str = ""         # comma separated domains never to talk to
    hoola_servers: str = ""                 # optional JSON {domain: base_url} for servers on custom ports
    hoola_trusted_issuers: str = ""         # v0.112 other Hoola servers whose verified-business credentials we believe
    hoola_server_key_file: str = ""         # default ./data/hoola_server_ed25519.key (made on first use)
    hoola_key_file: str = ""                # avatar-key encryption when SECRET_KEY is not set (default ./data/hoola_server.key)
    # --- v0.116 hand-offs: A2A 1.0, DigiLocker requester (Meri Pehchaan OAuth), ONDC listing export ---
    a2a_inbound: bool = True                # outside A2A agents may reach PUBLIC business counters (her a2a rule decides)
    digilocker_client_id: str = ""          # requester credentials from DigiLocker / API Setu partner portal (VPS .env only)
    digilocker_client_secret: str = ""
    digilocker_redirect_uri: str = ""       # default <PUBLIC_BASE_URL>/api/digilocker/callback
    digilocker_base: str = "https://digilocker.meripehchaan.gov.in"
    gcal_caldav_url: str = ""               # override CalDAV base (for Workspace/custom); blank = Gmail legacy endpoint

    # --- Google Drive/Sheets/Docs (service account; share a folder with its email) ---
    google_sa_file: str = ""                # path to the service-account JSON key on the server
    google_sa_json: str = ""                # or the JSON inline
    google_drive_folder_id: str = ""        # the shared folder to search in and create docs in (recommended)

    # --- storage ---
    database_url: str = "sqlite:///./santosh.db"

    # --- API protection: when set, every /api call needs "Authorization: Bearer <api_key>" ---
    api_key: str = ""

    # --- multi-tenant product: Google sign-in + token encryption ---
    pc_files_dir: str = "./data/pc_files"     # PC <-> phone files, deleted after pc_file_hours
    pc_file_hours: int = 24
    ask_ttl_hours: int = 24                   # v0.179 ask cards (approvals / forms / SQL) expire after this many hours
    pc_max_file_mb: int = 50
    pc_memory_runs: int = 8                   # v0.173 PC operator: last N finished tasks she remembers per PC
    pc_memory_hours: int = 24                 # and how long an entry stays useful
    secret_key: str = ""                    # encrypts stored tokens (set a long random value in production)
    public_base_url: str = ""               # e.g. https://santosh.139-59-10-30.sslip.io (for the OAuth redirect)
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    app_redirect_scheme: str = "santosh"    # deep link back into the phone app after sign-in
    hoola_signup: str = "open"              # who can make a NEW Hoola with Google sign-in: open (anyone) | invite
    hoola_signup_allow: str = ""            # invite mode: comma list of emails and/or @domain.com allowed to sign up
    gstinapi_api_key: str = ""              # v0.765 gstinapi.in (gak_...) - PAID per lookup (Rs 0.40-0.80), ONE server key, VPS .env only
    gstin_daily_calls: int = 50             # v0.765 most paid GSTIN lookups a day for ALL users together (0 = switched off)
    # v0.807 BAHI (GST & Accounts employee, docs/ACCOUNTS_EMPLOYEE_PLAN.md): the WhiteBooks GSP. Keys ONLY in the VPS .env, never
    # in chat / the repo / any reply. Build to the OpenAPI specs in their Developer Hub (docs/research/accounts/04_whitebooks_api.md).
    bahi_enabled: bool = True               # the desk + register; off = the console page says it is switched off
    bahi_filing: bool = False               # A1+: filing calls refused while False (prepare-only); A0 never files
    whitebooks_env: str = "sandbox"         # sandbox | production
    whitebooks_email: str = ""              # the WhiteBooks developer account email (sent as `email` on every call)
    whitebooks_gst_client_id: str = ""
    whitebooks_gst_client_secret: str = ""
    whitebooks_einv_client_id: str = ""     # empty = the GST pair is used
    whitebooks_einv_client_secret: str = ""
    whitebooks_ewb_client_id: str = ""
    whitebooks_ewb_client_secret: str = ""
    whitebooks_ip_address: str = ""         # sent as the `ip_address` header (the server's public IP); blank = 127.0.0.1
    whitebooks_daily_calls: int = 300       # most WhiteBooks calls a day PER TENANT (they bill per call); 0 = no cap
    whitebooks_per_minute: int = 50         # under the sandbox's 60 / minute; a call over it is refused, never queued
    whitebooks_timeout_s: float = 30.0
    # sandbox test identities from the Hub's Credentials page (per developer account) - only `python -m app.bahi.wbcheck` reads them
    whitebooks_sandbox_gstin: str = ""                 # the e-invoice / e-way bill test GSTIN (WhiteBooks' shared PDF)
    whitebooks_sandbox_gst_gstin: str = ""             # the GST (returns) test GSTIN WhiteBooks support gives; empty = the one above
    whitebooks_sandbox_gst_username: str = ""
    whitebooks_sandbox_einv_username: str = ""
    whitebooks_sandbox_einv_password: str = ""
    whitebooks_sandbox_ewb_username: str = ""
    whitebooks_sandbox_ewb_password: str = ""
    # v0.827 API Setu (apisetu.gov.in) GSTN Tax Payer API - the government's free GSTIN lookup; her API Setu partner account's
    # app client id + API key, VPS .env ONLY (never in chat / the repo / any reply). `python -m app.bahi.apisetucheck` tests it.
    apisetu_client_id: str = ""
    apisetu_api_key: str = ""
    apisetu_gstn_base: str = "https://apisetu.gov.in/gstn/v1"
    apisetu_timeout_s: float = 20.0
    apisetu_test_gstin: str = ""            # the GSTIN apisetucheck looks up; empty = WhiteBooks' GST test GSTIN, else a known one
    ecourtsindia_api_key: str = ""          # v0.763 ecourtsindia.com (eci_live_...) - PAID per call, ONE server key, VPS .env only
    ecourts_daily_calls: int = 30           # v0.763 most paid eCourts calls a day for ALL users together (0 = switched off)
    twelvedata_api_key: str = ""            # v0.760 twelvedata.com (NSE / BSE quotes) - ONE server key, VPS .env only
    alphavantage_api_key: str = ""          # v0.760 alphavantage.co (BSE quotes, backup) - ONE server key, VPS .env only
    newsdata_api_key: str = ""              # v0.758 newsdata.io - ONE server key for every user, VPS .env only
    gnews_api_key: str = ""                 # v0.758 gnews.io - ONE server key for every user, VPS .env only
    data_gov_in_base: str = ""              # v0.755 optional relay for data.gov.in (NIC drops cloud servers): e.g. https://hoola-dg.<you>.workers.dev
    data_gov_in_api_key: str = ""           # v0.754 data.gov.in (Open Government Data India) - ONE server key for every user, VPS .env only
    google_maps_api_key: str = ""           # Maps Platform key: Places API (New), Routes API, Geocoding API
    # v0.449 PAISA PEHLE: Maps had no ceiling at all. These are the first ones.
    maps_daily_inr: float = 200.0           # per tenant per day; a call that would cross it is REFUSED, not billed. 0 = no cap
    maps_price_list: str = "india"           # india | global - Google has a SEPARATE India list (USD, ~3x cheaper, 7x free caps)
    maps_usd_inr: float = 89.0              # only to show her rupees; Google bills in the billing account's currency
    maps_unknown_sku_usd: float = 40.0      # per 1,000, used ONLY if no SKU rate could be sourced at all (cap fires early, never late)
    maps_nearby_tier: str = "pro"           # the cheap list pass for maps_nearby: pro | enterprise (phone/rating/hours cost Enterprise)
    maps_matrix_max: int = 100              # v0.463: most origins x destinations in ONE matrix call (each pair is billed; Google's own ceiling is 625)
    route_opt_project: str = ""             # v0.465 Route Optimization needs a Google Cloud PROJECT ID (URL path projects/<id>) ...
    route_opt_sa_file: str = ""             # ... and OAuth (cloud-platform scope) from a service-account JSON on the VPS, NOT the Maps API key
    maps_opt_max_stops: int = 40            # stops in one plan (each is a billed shipment); Google's own sync limit was not read
    maps_cache: bool = True                 # reuse the licence-permitted place_id + 30-day lat/lng instead of re-billing
    # v0.540.0 LEADS NEEV: the caps the leads engine refuses AT PLAN TIME (docs/LEADS_PLAN.md section 12 asked
    # once: 5,000 rows/run and 20,000 rows/day per tenant are the first numbers, changeable here, refused early)
    leads_max_rows_per_run: int = 5000      # a run planning more rows than this is REFUSED with the cap named
    leads_max_rows_per_day: int = 20000     # per tenant per UTC day, counted from the kept-rows ledger (lead_cap_days)
    # v0.541.0 OFFICIAL LANES: the Places lane buys maps.place_details (Enterprise SKU) for at most this many
    # places per run - the maps_place economics (phone/website are per-place purchases), guarded by mapsbill's cap
    leads_places_details_per_run: int = 50
    # v0.542.0 ENRICHMENT: the P2 pass reads each kept row's OWN website (site-level 1 req/s, <= 3 pages/site,
    # robots obeyed) and makes at most ONE cheap-model call per row - more eligible rows than this cap and the
    # pass REFUSES at plan time with the number named, never truncates quietly (the leads cap law)
    leads_enrich_rows_per_run: int = 100
    # v0.543.0 SCRAPE LANE: the Google Maps public-listing grid's plan-time ceilings - the cell count and the
    # pages walked per cell (6 x 20 = 120 listings/cell, the known ~120 search ceiling). The lane itself is
    # per-tenant opt-in OFF (lead_scrape_optins), the politeness cap is 1 req/s per host (leads/scrape.py),
    # and a block page aborts the run - all refused/recorded, never muscled through (docs/LEADS_PLAN.md section 5)
    leads_scrape_max_cells: int = 400
    leads_scrape_pages_per_cell: int = 6
    # v0.544.0 VENDOR LANE: one licensed lead-data vendor behind the leads_run job shape (the research R6
    # pattern, leads/vendor.py). Until SHE names the vendor (plan section 12.4) every string stays empty and
    # the lane is ABSENT from the plan card - an explicit ask is refused with exactly this config named. The
    # price makes the ceiling possible (0 = refused), the run cap refuses the estimate at PLAN time, and the
    # terms ack is HER act (she read the vendor's terms; nothing is assumed - the v0.389 SACH BOLO discipline)
    leads_vendor_name: str = ""                 # she names the vendor (e.g. "acme-leads")
    leads_vendor_base_url: str = ""             # the vendor's documented API base (e.g. "https://api.vendor.example")
    leads_vendor_api_key: str = ""              # env LEADS_VENDOR_API_KEY; rides the header only, never a log
    leads_vendor_price_per_row_inr: float = 0.0 # rupees per row the vendor charges; 0 = the lane refuses
    leads_vendor_run_cap_inr: float = 2000.0    # one vendor run's rupee ceiling, refused AT PLAN TIME
    leads_vendor_terms_ack: str = ""            # the vendor's name once SHE has read its terms (CSV)
    # v0.544.0 SCALE: the P4 fan-out enrich pass (leads/scale.py, the HOOLA GRAPH walk) keeps at most this many
    # site passes in flight (shared Semaphore; politeness stays 1 req/s per site inside enrich.site_pass)
    leads_enrich_fanout_max: int = 4
    picovoice_access_key: str = ""          # no longer used: "Hey Santosh" runs on Santosh Wake (our own model)
    wake_keyword_file: str = ""             # optional newer hey_santosh.onnx to push to phones (wakeword/train.py)
    wake_sensitivity: float = 0.25          # 0..1; higher = wakes more easily (threshold = 1.1 - sensitivity). 0.25 -> 0.85: ~95% recall, ~2 false wakes/hour on test speech
    offline_email: bool = True              # phone offline > offline_after_min: email Santosh's updates
    offline_after_min: int = 20
    owner_emails: str = ""                  # Google accounts that are the server owner (use the .env email/calendar/drive). Blank = EMAIL_ADDRESS

    # --- WhatsApp Cloud API (Meta) ---
    wa_dry_run: bool = True                 # True = simulate Meta, nothing is really sent
    wa_token: str = ""                      # permanent system-user access token
    wa_phone_number_id: str = ""            # the sending number's ID
    wa_waba_id: str = ""                    # WhatsApp Business Account ID
    wa_graph_version: str = "v21.0"
    wa_verify_token: str = "change-me"      # must match the webhook "Verify token" in Meta
    wa_app_secret: str = ""                 # Meta app secret, used to check webhook signatures
    wa_inbox_tenant: str = ""               # Hoola Employee inbox: the owner whose business answers on WA_PHONE_NUMBER_ID

    # --- sending limits ---
    max_daily_sends: int = 250              # match your number's Meta messaging tier
    send_rate_per_sec: float = 8.0
    template_poll_seconds: int = 60

    # --- dry-run behaviour ---
    dry_run_approval_seconds: int = 20      # simulated time Meta takes to approve a template
    dry_run_read_ratio: float = 0.45
    dry_run_reply_ratio: float = 0.08

    worker_tick_seconds: float = 2.0
    worker_slot_timeout_s: float = 300.0   # wave 13: a worker slot that hangs longer is cut, the rest run
    tenant_id: str = "default"

    # --- v0.134 Gyaan: knowledge base (agentic RAG) over her files, Drive, mail, notes, chats ---
    gyaan_on: bool = True
    gyaan_dir: str = "data/gyaan"           # one SQLite file per owner
    gyaan_embed: str = "auto"               # auto | hash | fastembed[:model] | voyage | gemini
    gyaan_embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    gyaan_gemini_model: str = "gemini-embedding-001"
    voyage_api_key: str = ""                # optional: Voyage embeddings + rerank (cheap API, better Indic quality)
    gyaan_voyage_model: str = "voyage-4-lite"
    gyaan_rerank: bool = True               # API rerank on text chat when VOYAGE_API_KEY is set (never in calls)
    gyaan_rerank_model: str = "rerank-2.5-lite"
    gyaan_min_cover: float = 0.5            # share of the question's words a source must contain to count as found
    gyaan_min_cos: float = 0.55             # or this meaning score (real embedding models only)
    gyaan_min_rerank: float = 0.3
    gyaan_mail_days: int = 60
    gyaan_sync: bool = False                # tests: index + embed inline
    gyaan_ground: bool = True               # v0.135 cheap model checks each cited sentence against its sources
    gyaan_ground_timeout_s: float = 8.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
