"""v0.540.0 LEADS NEEV - the lead generation engine's foundation (the owner asked for it, plan first:
docs/LEADS_PLAN.md, then "P0 BUILD").

THE RULE BOUNDARY, SAID OUT LOUD FIRST. CLAUDE.md's NON-NEGOTIABLE RULES said "Official routes only: no scraping".
On 5 Nov 2026 the owner explicitly asked for a lead generation engine with a scraper in the backend - that ask IS the
owner decision the rules require, and the walls below are the scoped amendment the plan proposes (they get written
into CLAUDE.md in the P3 commit that adds the scrape lane itself). Until then THIS package is the boundary:

- THE ENGINE GATHERS; IT NEVER CONTACTS ANYONE. No message, no email, no call leaves this code. Outreach stays
  behind her tap on the campaign / email desks (LeadOutreach below is the ledger of taps, never an act).
- P0 RAN L0 ONLY (her own data). v0.541.0 P1 added the OFFICIAL lanes: REGISTRY (IndiaMART's own MCP server,
  through the existing app/indiamart.py) and OFFICIAL_API (Google Places through the EXISTING maps tools -
  maps.nearby for the list, maps.place_details bought per place under the mapsbill cap, NO second Google client).
  v0.542.0 P2 adds ENRICHMENT - a bounded crawl-brain pass over each kept row's OWN website (emails, socials by
  hostname, DNS->MX grading pakka/sadak_tak/galat, ONE billed model pick per row; NO SMTP probe), through the
  EXISTING scrape stack (SSRF guard, robots gate, 1 req/s per site). The scrape lane comes in P3 behind a
  per-tenant opt-in that is OFF by default, the vendor lane in P4. A lane
  that is not built yet is REFUSED by name ("P3 mein aayega") - no stub, no pretending.
- EVERY ROW CARRIES ITS PROVENANCE or it is not stored: source_lane + source_url + fetched_at. An export that
  finds a row without provenance REFUSES rather than ships an unexplained row (verify gate).
- BUSINESS FACTS ONLY. No review text at scale, no photos, no popular times, no consumer individuals
  (DPDP purpose limitation). What the scrape lane may store is named in rules.STORE_BOUNDARY so a later session
  cannot "complete" the store by accident (the v0.389 trap law).
- DELIBERATELY NOT BUILT, recorded so no session completes them by accident: social-platform scraping
  (platform ToS + real person-data), consumer B2C individuals from scraping, SMTP RCPT deliverability probing
  (spam infrastructure), bulk CAPTCHA solving / anti-bot muscle, residential-proxy minting, auto-outreach,
  review-text / photo / popular-times hoarding, a second Google API client (Places lanes go through the existing
  maps tools only), BULK sales-summary generation (the plan allows a per-row, on-demand, billed summary on her
  tap - a tool for it is NOT built yet; thousands of one-liners would hallucinate quietly).
"""
from __future__ import annotations

from .importer import (CONSENT_KEYS, ImportResult, NAME_KEYS, PHONE_KEYS, SAMPLE_PREFIX, YES, import_leads,
                       normalize_phone)

__all__ = ["CONSENT_KEYS", "ImportResult", "NAME_KEYS", "PHONE_KEYS", "SAMPLE_PREFIX", "YES", "import_leads",
           "normalize_phone"]
