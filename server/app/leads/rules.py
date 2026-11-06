"""Vocabulary and walls of the LEADS engine - one place, so a later session cannot quietly stretch them.

LANES are the sources ladder of docs/LEADS_PLAN.md section 4, in the order a plan picks them. LANE_BUILT names
what THIS version can actually run: everything else is refused BY NAME with the phase that will build it
("no stub, no pretending" - a lane that pretends to run is worse than one that refuses)."""
from __future__ import annotations

LANES = ("HER_DATA", "REGISTRY", "OFFICIAL_API", "SCRAPE", "VENDOR")

# v0.540.0 P0: L0 only. v0.541.0 P1 adds REGISTRY (IndiaMART's own MCP server, the app/indiamart.py lane) and
# OFFICIAL_API (Places through the EXISTING maps tools - maps.nearby for the list, maps.place_details bought per
# place under the mapsbill cap, NO second Google client). v0.542.0 P2 adds ENRICHMENT (not a source lane - the
# pass over kept rows' own websites). v0.543.0 P3 adds SCRAPE - the Google Maps PUBLIC LISTING lane behind the
# per-tenant opt-in that is OFF by default (rules.SCRAPE_OFF / SCRAPE_WALLS; the CLAUDE.md rule text was amended
# in the same commit that built this lane). P4 VENDOR. The phase names are the plan's, so a refusal can say
# exactly when it arrives.
LANE_BUILT: dict[str, str] = {"HER_DATA": "P0", "REGISTRY": "P1", "OFFICIAL_API": "P1", "SCRAPE": "P3"}
LANE_ARRIVES = {"VENDOR": "P4"}

# the amended rule, said where a later session would look for it (CLAUDE.md NON-NEGOTIABLE RULES carries the
# same text since the v0.543.0 commit - the amendment the plan proposed, word for word)
SCRAPE_RULE_TEXT = (
    "Communications and accounts stay official-routes-only (no personal WhatsApp automation, no "
    "consumer-subscription OAuth, no unofficial MCP for messaging). A LEADS scrape lane for PUBLIC BUSINESS "
    "LISTING DATA is allowed BY THE OWNER'S EXPLICIT ASK of 5 Nov 2026, under these walls, which no session may "
    "move: opt-in per tenant and OFF by default, never behind a login wall, never consumer individuals "
    "(businesses only), robots.txt obeyed on every non-Google host, politeness caps refused before the run, "
    "provenance recorded for every row, the engine NEVER contacts anyone - outreach stays behind her tap on the "
    "campaign / email desks. Anything outside business-listing data (reviews text at scale, social-platform "
    "profiles, consumer lists) stays NOT BUILT.")

# the refusal when the lane is asked for while the tenant's opt-in is OFF (the default state - which no session
# may flip silently; the flip is HER act, recorded in lead_scrape_optins with the walls quoted)
SCRAPE_OFF = ("SCRAPE lane aapke tenant ke liye OFF hai - per-tenant opt-in, default band. CLAUDE.md ka amended "
              "rule: 'opt-in per tenant and OFF by default'. Aapki haan se on hota hai: leads_run "
              "action=scrape_optin on=true (ya POST /api/leads/scrape-optin).")

STATUSES = ("PLANNED", "RUNNING", "PAUSED", "DONE", "REFUSED", "ABORTED")

# The identity key, strongest first (the plan, section 5.4). kgmid never nulls where it exists, place_id can.
KEY_TYPES = ("kgmid", "cid", "place_id", "name_address", "phone_e164")

# P2's email grading vocabulary, named NOW so the store never grows a second one later
# (maps_address_check's pakka / sadak_tak / galat, reused as-is).
EMAIL_GRADES = ("pakka", "sadak_tak", "galat")

# The one-question rule (v0.371 law): a vague ask gets ONE question, everything else has a house default.
ONE_QUESTION = "Kaunsa business dhandhe ka hai, aur kis sheher / area mein? (jaise: dentists, Pune)"

STORE_BOUNDARY = (
    "Business-listing FACTS only: name, category, address, phone, website, rating, review COUNT, hours, "
    "coordinates, key ids. NOT stored: review TEXT at scale (copyright-adjacent; omkarcloud-style field hoarding "
    "is how a leads store becomes a Google clone), photos, popular times, owner PII beyond the public business "
    "contact. Reviews are summarised on demand by a billed model call and not persisted beyond the chat.",
)

NEVER = (
    "Yeh engine kabhi kisi ko message / email / call nahi bhejta - outreach sirf aapke tap par, campaign / email "
    "desk se (official routes).",
    "Koi OTP / PIN / CVV / card / password nahi, koi login-walled page nahi, koi consumer (vyakti) list nahi - "
    "sirf dhandhe ke businesses ka public data.",
    "Har row ke saath uska source: source_lane, source_url, fetched_at. Bina provenance ki row store nahi hoti, "
    "export nahi hoti.",
    "Cap plan-time par hi refuse karta hai (per-run " + "5,000 rows, per-day 20,000 rows by default) - run ke "
    "beech nahi, chupke se truncate nahi.",
    "Social-platform scraping (LinkedIn waghera), review-text hoarding, photos, popular times: NOT BUILT.",
    "Koi bulk CAPTCHA solver, koi residential-proxy minting, koi SMTP probe: NOT BUILT (block hua to run ruk "
    "jaata hai aur batata hai - Hoola muscle nahi karta).",
)

# the walls quoted at flip time (the note column of lead_scrape_optins keeps them, so the permission slip
# always carries what it permits). P3 runs the Google Maps PUBLIC listings lane only - non-Google directories
# (JustDial/TradeIndia-style) stay unbuilt behind robots.txt until a later phase names them.
SCRAPE_WALLS = (
    SCRAPE_RULE_TEXT,
    "P3 Google Maps PUBLIC listings only - JustDial/TradeIndia-style directories aur koi bhi doosra host abhi "
    "built nahi (aage, robots.txt ke neeche).",
    " ".join(STORE_BOUNDARY),            # STORE_BOUNDARY is a 1-tuple (the card joins it the same way)
    NEVER[0],
    NEVER[5],
)

# where the cap module lives (leadscap mirrors mapsbill: refuse BEFORE the spend, never after)
CAP = "app.leadscap"
