"""Vocabulary and walls of the LEADS engine - one place, so a later session cannot quietly stretch them.

LANES are the sources ladder of docs/LEADS_PLAN.md section 4, in the order a plan picks them. LANE_BUILT names
what THIS version can actually run: everything else is refused BY NAME with the phase that will build it
("no stub, no pretending" - a lane that pretends to run is worse than one that refuses)."""
from __future__ import annotations

LANES = ("HER_DATA", "REGISTRY", "OFFICIAL_API", "SCRAPE", "VENDOR")

# v0.540.0 P0: L0 only. v0.541.0 P1 adds REGISTRY (IndiaMART's own MCP server, the app/indiamart.py lane) and
# OFFICIAL_API (Places through the EXISTING maps tools - maps.nearby for the list, maps.place_details bought per
# place under the mapsbill cap, NO second Google client). P2 enrichment, P3 SCRAPE (owner opt-in, OFF by default),
# P4 VENDOR. The phase names are the plan's, so a refusal can say exactly when it arrives.
LANE_BUILT: dict[str, str] = {"HER_DATA": "P0", "REGISTRY": "P1", "OFFICIAL_API": "P1"}
LANE_ARRIVES = {"SCRAPE": "P3 (uski haan chahiye, per-tenant opt-in, OFF)", "VENDOR": "P4"}

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

# where the cap module lives (leadscap mirrors mapsbill: refuse BEFORE the spend, never after)
CAP = "app.leadscap"
