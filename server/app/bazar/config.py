"""Bazar (159 MVP packs) settings. Pack-specific values use the BAZAR_ prefix; WhatsApp and the
encryption key come from Santosh's main settings so nothing is configured twice."""
from __future__ import annotations

import base64
import hashlib

from pydantic_settings import BaseSettings, SettingsConfigDict

from ..config import get_settings as core_settings

PLACEHOLDER_VPAS = {"", "newtika.collect@upi"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="BAZAR_", extra="ignore")

    env: str = "prod"

    # Spend defaults (paise). 0 = every spend needs a tap.
    default_cap_per_order_paise: int = 0
    default_cap_per_day_paise: int = 0
    upi_max_amount_paise: int = 10_000_000  # ₹1,00,000 per UPI transaction

    # Bill payments (BBPS). "sandbox" = demo bills, no real money moves. "http" = your BBPS partner gateway.
    bbps_mode: str = "sandbox"
    bbps_base_url: str = ""
    bbps_api_key: str = ""
    # Collection VPA of your payment aggregator / BBPS partner (user pays here, partner pays the biller).
    collection_vpa: str = ""
    collection_name: str = "Santosh Bill Pay"
    webhook_secret: str = ""  # HMAC-SHA256 secret your payment aggregator signs webhooks with

    # Official agent endpoints (MCP). Empty = pack shows as "not configured".
    mcp_swiggy_food_url: str = "https://mcp.swiggy.com/food"
    mcp_swiggy_instamart_url: str = "https://mcp.swiggy.com/instamart"
    mcp_swiggy_dineout_url: str = "https://mcp.swiggy.com/dineout"
    mcp_zomato_url: str = "https://mcp-server.zomato.com/mcp"
    mcp_zepto_url: str = ""
    mcp_district_url: str = ""

    # Approved WhatsApp UTILITY template for new-order alerts to shops (free text only works inside 24 h).
    # Body must have 4 variables: {{1}} order id, {{2}} items, {{3}} total, {{4}} slot/address.
    shop_order_template: str = ""
    shop_order_template_lang: str = "hi"

    files_dir: str = "./data/bazar_files"  # generated PDFs (invoices, slips, receipts, resumes)

    # Home devices (v0.3). "sandbox" = offline stand-ins of the official clouds; "live" = real APIs.
    device_cloud_mode: str = "sandbox"
    smartthings_client_id: str = ""
    smartthings_client_secret: str = ""
    home_connect_client_id: str = ""
    home_connect_client_secret: str = ""
    lg_thinq_client_id: str = ""        # any stable id for your app, sent as x-client-id
    lg_thinq_country: str = "IN"
    lg_thinq_region: str = "kic"        # ThinQ Connect region host (api-<region>.lgthinq.com); confirm for India

    # E-commerce (v0.4)
    commerce_max_order_paise: int = 2_000_000       # ₹20,000 per order through Santosh
    commerce_quote_ttl_seconds: int = 600           # a price quote is valid for 10 minutes
    commerce_mcp_rate_per_minute: int = 120         # Commerce MCP (/mcp/commerce) requests per token per minute
    # ONDC buyer app. "sandbox" = in-process mock seller network + registry; "preprod"/"prod" = real network.
    ondc_mode: str = "sandbox"
    ondc_subscriber_id: str = "santosh.ainewtika.com"
    ondc_subscriber_uri: str = "https://santosh.ainewtika.com/ondc"
    ondc_unique_key_id: str = "santosh-k1"
    ondc_signing_private_key: str = ""   # base64 ed25519 (scripts/ondc_keys.py)
    ondc_signing_public_key: str = ""
    ondc_encryption_private_key: str = ""  # base64 DER X25519
    ondc_encryption_public_key: str = ""
    ondc_gateway_url: str = "https://preprod.gateway.ondc.org/search"
    ondc_registry_url: str = "https://preprod.registry.ondc.org/v2.0/lookup"
    ondc_registry_public_key: str = ""   # ONDC's encryption public key for the /on_subscribe challenge
    ondc_request_id: str = ""            # request_id from the ONDC portal, signed into ondc-site-verification.html
    ondc_city_code: str = "std:0724"     # Akola
    ondc_core_version: str = "1.2.0"
    ondc_finder_fee_percent: str = "3"
    ondc_wait_seconds: float = 6.0       # how long to collect on_search / wait for on_* callbacks
    # Shopify Storefront MCP stores the user can shop (comma-separated myshopify or custom domains)
    shopify_stores: str = ""
    # Flipkart Affiliate API (search + prices + deep link; checkout happens in Flipkart)
    flipkart_affiliate_id: str = ""
    flipkart_affiliate_token: str = ""
    commerce_sandbox_feeds: bool = True  # sandbox stand-ins for Shopify/Flipkart when no keys are set

    # ---- mapped from Santosh core settings ----
    @property
    def secret_key(self) -> str:
        raw = core_settings().secret_key or ""
        if not raw:
            return ""
        return base64.urlsafe_b64encode(hashlib.sha256(("bazar:" + raw).encode()).digest()).decode()

    @property
    def wa_token(self) -> str:
        return core_settings().wa_token

    @property
    def wa_phone_number_id(self) -> str:
        return core_settings().wa_phone_number_id

    @property
    def wa_business_account_id(self) -> str:
        return core_settings().wa_waba_id

    @property
    def wa_api_version(self) -> str:
        return core_settings().wa_graph_version

    @property
    def wa_dry_run(self) -> bool:
        return core_settings().wa_dry_run

    @property
    def public_base_url(self) -> str:
        return (core_settings().public_base_url or "http://127.0.0.1:8000").rstrip("/")

    @property
    def bills_live(self) -> bool:
        """Real bill payments need a partner gateway AND a real collection VPA."""
        return self.bbps_mode == "http" and bool(self.bbps_base_url) and self.collection_vpa.strip() not in PLACEHOLDER_VPAS


_s: Settings | None = None


def get_settings() -> Settings:
    global _s
    if _s is None:
        _s = Settings()
    return _s


def reset_settings() -> None:
    global _s
    _s = None
