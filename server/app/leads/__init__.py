"""v0.540.0 LEADS NEEV - the lead generation engine's foundation (the owner asked for it, plan first:
docs/LEADS_PLAN.md, then "P0 BUILD").

THE RULE BOUNDARY, SAID OUT LOUD FIRST. CLAUDE.md's NON-NEGOTIABLE RULES said "Official routes only: no scraping".
On 5 Nov 2026 the owner explicitly asked for a lead generation engine with a scraper in the backend - that ask IS the
owner decision the rules require. The scoped amendment the plan proposed IS NOW THE RULE TEXT: it was written into
CLAUDE.md's NON-NEGOTIABLE RULES in the v0.543.0 commit that built the scrape lane itself (the plan's
non-negotiable: the amendment rides the lane's own commit). The walls, restated here so the package stays the
boundary even if a later session loses the plot:

- THE ENGINE GATHERS; IT NEVER CONTACTS ANYONE. No message, no email, no call leaves this code. Outreach stays
  behind her tap on the campaign / email desks (LeadOutreach below is the ledger of taps, never an act).
- P0 RAN L0 ONLY (her own data). v0.541.0 P1 added the OFFICIAL lanes: REGISTRY (IndiaMART's own MCP server,
  through the existing app/indiamart.py) and OFFICIAL_API (Google Places through the EXISTING maps tools -
  maps.nearby for the list, maps.place_details bought per place under the mapsbill cap, NO second Google client).
  v0.542.0 P2 adds ENRICHMENT - a bounded crawl-brain pass over each kept row's OWN website (emails, socials by
  hostname, DNS->MX grading pakka/sadak_tak/galat, ONE billed model pick per row; NO SMTP probe), through the
  EXISTING scrape stack (SSRF guard, robots gate, 1 req/s per site).
- v0.543.0 P3 adds THE SCRAPE LANE - the Google Maps PUBLIC LISTING grid (app/leads/gmaps_parse.py + grid.py +
  scrape.py, run_scrape in service.py), behind a PER-TENANT OPT-IN THAT IS OFF BY DEFAULT (lead_scrape_optins;
  the flip is HER act and is recorded with the walls quoted - rules.SCRAPE_WALLS). The CLAUDE.md rule text was
  AMENDED IN THE SAME COMMIT that built this lane (the plan's non-negotiable): "Official routes only: no
  scraping" became the scoped rule - communications and accounts stay official-routes-only; a LEADS scrape lane
  for PUBLIC BUSINESS LISTING DATA is allowed BY THE OWNER'S EXPLICIT ASK of 5 Nov 2026 under walls no session
  may move (opt-in per tenant and OFF by default, never login-walled, never consumer individuals, robots.txt
  obeyed on every non-Google host, politeness caps refused before the run, provenance on every row, the engine
  NEVER contacts anyone; anything outside business-listing data stays NOT BUILT).
- v0.544.0 P4 adds THE VENDOR LANE + SCALE. VENDOR (app/leads/vendor.py + run_vendor): ONE licensed lead-data
  vendor behind the same leads_run job shape (the research R6 pattern), CONFIG-GATED the way SCRAPE is opt-in
  gated - plan 12.4 (she names the vendor and the budget) is HER decision, so until the config exists the lane
  is ABSENT from the plan card and an explicit ask refuses with the exact config named (no stub, no pretending).
  The run is priced on the plan card BEFORE it starts (rows x LEADS_VENDOR_PRICE_PER_ROW_INR; estimate over
  LEADS_VENDOR_RUN_CAP_INR = a REFUSED card, the numbers are the receipt); ONE vendor call per run, never
  retried; every vendor row must carry its OWN source_url (the provenance law extends to vendor rows); the bill
  says whether its number is the vendor's own reported cost or the estimate. SCALE (app/leads/scale.py):
  store_backend() names the engine the store is really on (country-scale = Postgres via DATABASE_URL/dbmove,
  never claimed when the engine is SQLite), and enrich(fanout=True) runs the SAME per-row body across the HOOLA
  GRAPH (dispatch -> static chunk fan-out -> join barrier, bounded in-flight, store writes applied after the
  barrier one writer at a time). An unknown lane name is still refused by name - no stub, no pretending.
- EVERY ROW CARRIES ITS PROVENANCE or it is not stored: source_lane + source_url + fetched_at. An export that
  finds a row without provenance REFUSES rather than ships an unexplained row (verify gate).
- BUSINESS FACTS ONLY. No review text at scale, no photos, no popular times, no consumer individuals
  (DPDP purpose limitation). What the scrape lane may store is named in rules.STORE_BOUNDARY so a later session
  cannot "complete" the store by accident (the v0.389 trap law).
- DELIBERATELY NOT BUILT, recorded so no session completes them by accident: social-platform scraping
  (platform ToS + real person-data), consumer B2C individuals from scraping, SMTP RCPT deliverability probing
  (spam infrastructure), bulk CAPTCHA solving / anti-bot muscle, residential-proxy minting, auto-outreach,
  review-text / photo / popular-times hoarding, a second Google API client (Places lanes go through the existing
  maps tools only; the scrape lane is the ONE new Google-facing code and it faces the PUBLIC website, never the
  API - the leadscard's scrape_faces_public_site guard proves it), non-Google public directories
  (JustDial/TradeIndia-style: named in the plan's L2 but NOT built in P3 - a directory ask is refused with that
  reason; they arrive later, behind robots.txt), BULK sales-summary generation (the plan allows a per-row,
  on-demand, billed summary on her tap - a tool for it is NOT built yet; thousands of one-liners would
  hallucinate quietly).
"""
from __future__ import annotations

from .importer import (CONSENT_KEYS, ImportResult, NAME_KEYS, PHONE_KEYS, SAMPLE_PREFIX, YES, import_leads,
                       normalize_phone)

__all__ = ["CONSENT_KEYS", "ImportResult", "NAME_KEYS", "PHONE_KEYS", "SAMPLE_PREFIX", "YES", "import_leads",
           "normalize_phone"]
