from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings come from environment variables or a .env file (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Santosh brain (Claude API) ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    agent_max_steps: int = 14
    agent_max_tokens: int = 2000

    # --- realtime voice (Baat tab): Gemini Live speech-to-speech, key from aistudio.google.com ---
    gemini_api_key: str = ""
    gemini_live_model: str = "gemini-3.8-live"
    voice_default: str = "Puck"            # a male Gemini voice; the app can pick another
    gemini_search_model: str = ""          # model used for Google Search answers (empty = newest Flash)
    voice_silence_ms: int = 1100           # pause that ends your turn (higher = never cut off mid-thought)
    # Optional Gemini extras; gemini-3.8-live rejects both today, so they are off until Google enables them
    voice_affective_dialog: bool = False
    voice_proactive_audio: bool = False

    # --- email (Baat/Chat can read your inbox and send approved replies). App password, not your login password. ---
    email_address: str = ""
    email_password: str = ""                # app password (Gmail/Outlook/Zoho "app password")
    email_imap_host: str = ""               # auto-detected from the address when blank
    email_imap_port: int = 993
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_sender_name: str = ""             # name shown on sent mail (defaults to the address)
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
    secret_key: str = ""                    # encrypts stored tokens (set a long random value in production)
    public_base_url: str = ""               # e.g. https://santosh.139-59-10-30.sslip.io (for the OAuth redirect)
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    app_redirect_scheme: str = "santosh"    # deep link back into the phone app after sign-in

    # --- WhatsApp Cloud API (Meta) ---
    wa_dry_run: bool = True                 # True = simulate Meta, nothing is really sent
    wa_token: str = ""                      # permanent system-user access token
    wa_phone_number_id: str = ""            # the sending number's ID
    wa_waba_id: str = ""                    # WhatsApp Business Account ID
    wa_graph_version: str = "v21.0"
    wa_verify_token: str = "change-me"      # must match the webhook "Verify token" in Meta
    wa_app_secret: str = ""                 # Meta app secret, used to check webhook signatures

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
