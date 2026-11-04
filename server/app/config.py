from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings come from environment variables or a .env file (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Santosh brain (Claude API) ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    usage_month_usd: float = 0.0           # v0.98 server ceiling of AI spend per owner per month (0 = none)
    usage_usd_inr: float = 88.0            # v0.98 rupees per dollar for the Kharcha screen
    agent_max_steps: int = 24              # v0.78: more room to finish (the circuit breaker still stops loops)
    agent_max_tokens: int = 2000
    chat_heal_ai: bool = True              # v0.158 after a call, a cheap model judges if its cards were relevant
    agent_self_check: bool = True          # v0.78 Pakka kaam: check the real results before saying done
    draft_check: bool = True               # v0.223 Draft jaanch: the last look at a reply (free in code + one
    draft_check_max_hour: int = 4          #   small check after the words are out); notes per chat per hour
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
    dev_lab: bool = False                   # v0.456 PRAYOGSHALA: Hoola may run her declared checks in the Docker box. OFF until `python -m app.devlab check` passes on the VPS
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
    agent_aage: bool = True                 # v0.311 AAGE BADHO: a text-only reply that only promises more work gets one 'do it now' nudge
    agent_progress_window_s: int = 300      # v0.311 a turn that finished a tool this recently gets the long-job deadline (0 = off)
    agent_ack_after_s: float = 5.0          # v0.187 a turn silent this long first says "ek second, dekh raha hoon…" (0 = off)
    agent_parallel_tools: bool = True       # v0.189 a step asking several pure look-ups (search/weather/status) runs them together; everything else stays serial
    # v0.191 HARNESS-2: step-admitted tool subsets (dsh / Claude Code pattern) - the model of one turn sees only the
    # tool families her words (and any open goal) actually need; the rest stay one tool_search away. Stable for the
    # WHOLE turn, so the Anthropic prompt cache holds; a family admitted mid-turn re-caches once, by design.
    agent_tool_admission: bool = True
    prompt_slim: bool = True               # v0.473 PATLA PROMPT: only the admitted families' guides ride in the system prompt (false = the full ~130 KB guide, as before)
    # v0.237 FULL CLAUDE MODE Phase 1 (agent/context.py): the whole chat word for word while it fits the model's window
    chat_context: str = "claude"           # claude = whole chat, gauge + safety net | hoola = the v0.108 40-49 exchange window (instant rollback)
    chat_context_limit_glm: int = 200000   # GLM's context window in tokens (check your Z.ai plan)
    chat_context_limit_claude: int = 200000
    chat_context_limit_omniroute: int = 128000   # the smallest window your OmniRoute combo can land on
    chat_context_full_at: float = 0.75     # the request may fill this share of the window; above it the safety net runs
    chat_context_max_tokens: int = 0       # v0.244 cost cap: compact at this many tokens whatever the model's window (0 = off)
    # v0.242 FULL CLAUDE MODE Phase 2 (agent/compact.py): Claude-style compaction at the full_at line
    about_me: bool = True                  # v0.250 "Mere baare mein" page rebuilt daily for active owners (false = never rebuilt)
    memory_fence: bool = True              # v0.246 PHASE 3C: Hoola's own memory stays inside its Session (fence.py); false = all chats share
    chat_compact: bool = True              # false = Phase 1 only (the safety net shortens instead of a summary)
    chat_compact_prepare_at: float = 0.6   # past this share a draft summary is written in the background
    chat_compact_keep: int = 4             # newest exchanges that always stay word for word
    chat_compact_max_chars: int = 8000     # the checkpoint summary's size
    tool_admit_cap: int = 220               # admitted specs above this = router over-matched: send the FULL set instead
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
    team_bg_max_running: int = 2            # running background crews per tenant
    team_bg_timeout_s: int = 1200           # a whole background crew's wall clock
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
    quick_lane: bool = True                 # v0.86 answer new chat messages at once while a long job runs
    quick_model: str = ""                   # v0.86 model for the quick lane ('' = anthropic_model; a cheap brain is used first)
    prompt_cache: bool = True               # v0.86 Anthropic prompt caching on tools + conversation (faster replies)
    console_v2: bool = True                 # v0.170 Console v2 master switch: the Night-Glass v2 shell serves /console (?legacy=1 = the old page) and turns the four chat phases on below in one go
    console_stream: bool = False            # v0.161 replies stream word by word (live-only delta events, /live, retry, thumbs)
    chat_sessions: bool = False             # v0.162 many chats: titles, pin / archive / delete, search, edit + branches
    side_panel: bool = False                # v0.163 finished work (pages, files, videos, sites, apps) opens beside the chat
    chat_projects: bool = False             # v0.164 projects ("Kaam ke folder"): instructions, notes, files for their chats
    projects_dir: str = "./data/projects"   # v0.164 project files (kept until she removes them, unlike pc_files)
    glm_api_key: str = ""
    glm_base_url: str = "https://api.z.ai/api/paas/v4"
    glm_model: str = "glm-4.7"
    glm_temperature: float = 0.6
    glm_thinking: str = "disabled"          # enabled | disabled | "" (don't send) — disabled = faster, cheaper replies

    # --- realtime voice (Baat tab): Gemini Live speech-to-speech, key from aistudio.google.com ---
    gemini_api_key: str = ""
    gemini_live_model: str = "gemini-3.8-live"
    voice_default: str = "Puck"            # a male Gemini voice; the app can pick another
    gemini_search_model: str = ""          # model used for Google Search answers (empty = newest Flash)
    parallel_search: bool = True           # v0.91 Parallel web search (free MCP endpoint): quotes from real pages + links
    parallel_api_key: str = ""             # optional: higher limits (https://platform.parallel.ai); only the query is sent
    parallel_mcp_url: str = "https://search.parallel.ai/mcp"
    voice_adapt: bool = True               # v0.119 her own pauses / style / words / mis-hearings shape the call
    site_model: str = "claude-opus-5-5"     # v0.121 Website Sahayak: model that designs and writes every section
    site_edit_model: str = ""              # v0.121 small website edits ('' = anthropic_model)
    site_opus: bool = True                 # v0.225 every website section / fix / change on the App Sahayak Opus path (thinking, effort, retries, no quiet fallback)
    site_art: bool = True                  # v0.225 Opus writes a design DNA per look before the hero (art direction)
    site_critique: str = "all"             # v0.225 Opus looks at the built screenshots: all (v0.292, every page) | home | off
    site_critique_min: float = 7.5         # v0.225 a section scoring below this (out of 10) is redrawn once with the notes
    site_parallel: int = 3                 # v0.225 sections written at the same time inside one build
    site_ai_photos: int = 6                # v0.292 pictures a site gets before its looks (her own photos first, AI fills the gap; 0 = off)
    pexels_api_key: str = ""               # v0.292 optional licensed stock photos (official Pexels API) when the image models fail
    site_look_sections: int = 3            # v0.292 sections of the home page each of the 3 looks shows (hero + the next ones)
    site_look_parallel: int = 6            # v0.324 look sections written at the same time (3 looks x hero + page top)
    site_kit: bool = True                  # v0.330 one design kit per site (.k-* components every section uses)
    site_critique_pages: int = 6           # v0.292 pages Opus reviews from their real screenshots (site_critique=all)
    site_max_pages: int = 150              # v0.315 BADI WEBSITE: most pages one site may have (designed + list items + legal)
    site_max_ai_pages: int = 40            # v0.315 most pages with their OWN designed sections (each section = one Opus call)
    site_parallel_big: int = 8             # v0.315 sections written at the same time on a big site (v0.400: 5 -> 8)
    site_check_pages: int = 40             # v0.315 pages the browser checks open on a big site (+2 items of every list)
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
    officehours_enabled: bool = True       # v0.495 office hours (the gstack THINK/PLAN lane: design docs + plan reviews)
    officehours_keep_docs: int = 30        # v0.495 baithak docs kept per tenant; older ones (and their reviews) are forgotten
    call_receipt: bool = True              # v0.91 after a call: a short card of what was decided and what really ran
    voice_tool_ack: bool = True            # a tool runs and he is silent: say a quick "ek second" in his own voice
    voice_backchannel: bool = True         # v0.205 KAAN KAAPI: tiny listener murmurs in her pauses + one progress sound on a long silent tool (kill switch)
    voice_prosody: bool = True             # v0.208 AWAAZ-3: her TurnMeter prosody sharpens the feeling note - vetoes a glad her voice contradicts, confirms a low, adds the thinking-pauses rider (kill switch; off = the v0.202 words-only engine)
    voice_soorat: bool = True              # v0.220 SOORAT: his energy follows her transitions - a state flip names the move, the fresh tone tints the scripted moments (acks skip the bright clips while she is heavy/tense, stall/result/reconnect notes carry the tone); off = the v0.219 engine
    # v0.264 OPENAI VOICE (Phase 1 of "two engines, she chooses"): a second call engine for "real voice" (breaths,
    # hmm, light laughs). Gemini stays the default and untouched; OpenAI is used only when the owner picks it, a key is
    # set, and the month's budget / her minutes allow - otherwise the call quietly runs on Gemini.
    openai_api_key: str = ""                          # VPS .env only (OPENAI_API_KEY), never in chat or the repo
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
    voice_ack_tts_model: str = "gemini-3.8-flash-tts"   # v0.181 (was gemini-2.5-flash-preview-tts): new TTS, far more natural delivery; legacy model is the automatic fallback
    voice_compress_trigger: int = 60000    # v0.224 Gemini Live context compression starts here (0 = Google's default near the limit)
    voice_compress_target: int = 35000     # ...and slides the window back to about this many tokens
    voice_tool_behavior: bool = True       # v0.473 slow call tools NON_BLOCKING (he keeps talking), quick ones BLOCKING (exact answer, no guessing); false = model default for all
    voice_affective: bool = True           # v0.181 affective dialog: he answers with the emotional tone he HEARS (happy with her, gentle when she is low). If Gemini refuses the field for a model, the call retries without it and remembers (voice.py _AFFECTIVE_OK)
    # --- Awaaz Pehchaan: who is talking (owner / family) from the voice; free models, CPU (sherpa-onnx) ---
    voiceid_models_dir: str = "./data/voiceid_models"   # tools/setup_voiceid.sh downloads the two models here
    voiceid_match: float = 0.30            # similarity needed to say "this is X" (0..1)
    voiceid_margin: float = 0.06           # and this much ahead of the next closest person
    voiceid_min_speech_s: float = 1.6      # speech needed before the first guess in a call
    voice_resume_grace_s: int = 25         # a dropped phone connection can re-join the same call within this time
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
    voice_ring_max_day: int = 2            # v0.211 rings per tenant per day (the phone is not an alarm clock)
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
    # --- v0.486.0 BYOX SKILL PACK: Build-Your-Own-X 31 categories, seed default on ---
    byox_enabled: bool = True               # BYOX skill pack seeds on first open (default ON)
    # --- Claude skills pilot (docs/CLAUDE_SKILLS_PILOT_PLAN.md): Apache-2.0 Anthropic skills seeded once per tenant ---
    claude_skills_enabled: bool = True      # skillpack/claude/* seeds on first open (create-if-missing, hers win)
    # --- v0.495.0 PROG PACK: the vetted-library registry + the windows script lane ---
    progpack_enabled: bool = True           # PROG pack seeds on first open (default ON)
    sp_enabled: bool = True                 # superpowers lane seeds on first open under its own stamp (default ON)
    # --- FE PACK: the HyperFrames template packs + campaign email templates + UI kit ---
    fepack_enabled: bool = True             # FE pack seeds on first open (default ON)
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
    youtube_gemini_model: str = "gemini-2.5-flash"   # watches public YouTube videos to summarise / answer (official Gemini API)
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
