"""v0.540.0 LEADS NEEV - the lead generation engine's foundation (the owner asked for it, plan first:
docs/LEADS_PLAN.md, then "P0 BUILD").

THE RULE BOUNDARY, SAID OUT LOUD FIRST. CLAUDE.md's NON-NEGOTIABLE RULES said "Official routes only: no scraping".
On 5 Nov 2026 the owner explicitly asked for a lead generation engine with a scraper in the backend - that ask IS the
owner decision the rules require, and the walls below are the scoped amendment the plan proposes (they get written
into CLAUDE.md in the P3 commit that adds the scrape lane itself). Until then THIS package is the boundary:

- THE ENGINE GATHERS; IT NEVER CONTACTS ANYONE. No message, no email, no call leaves this code. Outreach stays
  behind her tap on the campaign / email desks (LeadOutreach below is the ledger of taps, never an act).
- P0 RUNS L0 ONLY: her own data (her past campaign lists, her files). The official lanes (IndiaMART MCP, the
  existing Places tools) come in P1, the scrape lane in P3 behind a per-tenant opt-in that is OFF by default,
  the vendor lane in P4. A lane that is not built yet is REFUSED by name ("P1 mein aayega") - no stub, no pretending.
- EVERY ROW CARRIES ITS PROVENANCE or it is not stored: source_lane + source_url + fetched_at. An export that
  finds a row without provenance REFUSES rather than ships an unexplained row (verify gate).
- BUSINESS FACTS ONLY. No review text at scale, no photos, no popular times, no consumer individuals
  (DPDP purpose limitation). What the scrape lane may store is named in rules.STORE_BOUNDARY so a later session
  cannot "complete" the store by accident (the v0.389 trap law).
- DELIBERATELY NOT BUILT, recorded so no session completes them by accident: social-platform scraping
  (platform ToS + real person-data), consumer B2C individuals from scraping, SMTP RCPT deliverability probing
  (spam infrastructure), bulk CAPTCHA solving / anti-bot muscle, residential-proxy minting, auto-outreach,
  review-text / photo / popular-times hoarding, a second Google API client (Places lanes go through the existing
  maps tools only).
"""
from __future__ import annotations

from .importer import (CONSENT_KEYS, ImportResult, NAME_KEYS, PHONE_KEYS, SAMPLE_PREFIX, YES, import_leads,
                       normalize_phone)

__all__ = ["CONSENT_KEYS", "ImportResult", "NAME_KEYS", "PHONE_KEYS", "SAMPLE_PREFIX", "YES", "import_leads",
           "normalize_phone"]
