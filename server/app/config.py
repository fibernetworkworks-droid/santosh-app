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
    agent_self_check: bool = True          # v0.78 Pakka kaam: check the real results before saying done
    memory_auto: bool = True               # v0.108 lasting facts picked after her turns ("yaad rakha" chip)
    agent_fix_search: bool = True          # v0.78: a failed step with no known fix -> search the web for the solution
    agent_tool_timeout_s: int = 300         # a tool that hangs never blocks a chat turn longer than this (browser waits go up to 270 s)
    agent_turn_timeout_s: int = 900         # a whole turn never holds the chat lock longer than this
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
    studio_on: bool = True                 # v0.68 Hoola Video Studio (AI-generated shots: Seedance / Veo / Kling / Wan / Omni)
    openrouter_api_key: str = ""           # one key for Seedance 2.0 / 2.5, Veo 3.1, Kling 3.0, Wan 3.0 (recommended)
    fal_key: str = ""                      # backup: Seedance via fal
    ark_api_key: str = ""                  # backup: Seedance direct from BytePlus ModelArk
    studio_month_usd: float = 10.0         # most one owner may spend on AI video in a calendar month (every spend is her tap too)
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
    sites_cf_token: str = ""               # v0.122 Newtika's Cloudflare token: custom hostnames on the Hoola sites zone
    sites_cf_zone_id: str = ""             # v0.122 the Hoola sites zone id (Cloudflare for SaaS)
    sites_resell: bool = False             # v0.123 Hoola (Newtika) registers domains on its own registrar account
    sites_reg_cf_token: str = ""           # v0.123 Newtika's Cloudflare Registrar token (only with sites_resell)
    sites_reg_cf_account: str = ""
    sites_porkbun_key: str = ""            # v0.123 Newtika's Porkbun API key / secret (only with sites_resell)
    sites_porkbun_secret: str = ""
    sites_domain_month_inr: float = 5000   # v0.123 ceiling per owner per month for domain purchases
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
    voice_silence_ms: int = 700            # pause that ends your turn: Google recommends 500-800 (people reply in ~0.2 s)
    voice_end_sensitivity: str = ""        # "" = Gemini's default | low (waits longer) | high (answers sooner)
    voice_prefix_padding_ms: int = 300     # speech kept from just before the voice was detected (100-300)
    voice_start_sensitivity: str = "low"   # low = TV / far voices / clatter don't count as you starting to talk | high | ""
    voiceid_vad: bool = True               # v0.53 Awaaz Pehchaan takes only chunks Silero calls a voice
    voice_vad_need: float = 0.5            # v0.53 phone Silero VAD: speech probability needed to count as talking
    voice_vad_fast: float = 0.85           # very sure it's a voice: barge-in opens after 160 ms instead of 240 ms
    voice_vad_idle_gate: bool = True       # while nobody talks, pure noise (fan, traffic, clatter) reaches Gemini as silence
    voice_resume_after_noise_s: float = 1.5  # he was cut off but nobody spoke: carry on after this long (0 = off)
    operator_preflight: bool = True        # v0.92 check a website job's site from this server first; refused -> her PC
    call_receipt: bool = True              # v0.91 after a call: a short card of what was decided and what really ran
    voice_tool_ack: bool = True            # a tool runs and he is silent: say a quick "ek second" in his own voice
    voice_ack_tts_model: str = "gemini-2.5-flash-preview-tts"   # makes those short clips once per voice
    # (affective dialog and proactive audio are gone: gemini-3.8-live removed the first and always has the second on)
    # --- Awaaz Pehchaan: who is talking (owner / family) from the voice; free models, CPU (sherpa-onnx) ---
    voiceid_models_dir: str = "./data/voiceid_models"   # tools/setup_voiceid.sh downloads the two models here
    voiceid_match: float = 0.30            # similarity needed to say "this is X" (0..1)
    voiceid_margin: float = 0.06           # and this much ahead of the next closest person
    voiceid_min_speech_s: float = 1.6      # speech needed before the first guess in a call
    voice_resume_grace_s: int = 25         # a dropped phone connection can re-join the same call within this time
    voice_quiet_notes: str = "auto"        # v0.150 quiet context notes mid-call: auto (by model) | client_content | queue
    voice_safe_setup: bool = True          # v0.150 Gemini refuses the call setup: retry step by step with fewer extras
    voice_side_talk: bool = True           # v0.142 talk not meant for Hoola (her phone call, people in the room) is never answered
    voice_hold_max_s: int = 900            # v0.142 side-talk hold longer than this ends the call (Gemini audio is billed)
    voice_call_hold_max_s: int = 3600      # v0.142 her other phone call longer than this ends the Hoola call
    voice_tool_wait_s: int = 12            # v0.86 (was 25) a call waits this long for a big job, then talks on and gets told when it is done
    voice_tool_timeout_s: int = 60         # any other call tool is cut off after this

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
    rea_bin: str = ""                       # absolute path to the pinned `rea` launcher (npm rea-agents@6.7.0)
    rea_jadx_jar: str = ""                  # jadx-headless-mcp-0.7.1-all.jar (SHA-256 checked at install) for APKs
    rea_java_home: str = ""                 # optional JDK 17+ for JADX (else java on PATH)
    rea_home: str = ""                      # REA's private HOME / work folders (default ./data/rea_home)
    rea_timeout_s: int = 300                # per REA call
    rea_node_heap_mb: int = 2048
    appcheck_max_mb: int = 400              # biggest file App Jaanch accepts
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
    pc_max_file_mb: int = 50
    secret_key: str = ""                    # encrypts stored tokens (set a long random value in production)
    public_base_url: str = ""               # e.g. https://santosh.139-59-10-30.sslip.io (for the OAuth redirect)
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    app_redirect_scheme: str = "santosh"    # deep link back into the phone app after sign-in
    hoola_signup: str = "open"              # who can make a NEW Hoola with Google sign-in: open (anyone) | invite
    hoola_signup_allow: str = ""            # invite mode: comma list of emails and/or @domain.com allowed to sign up
    google_maps_api_key: str = ""           # Maps Platform key: Places API (New), Routes API, Geocoding API
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
