# Hoola Lead Generation Engine — the plan (the owner asked, plan first)

Owner ask (5 Nov 2026): "NOW A LEAD GENERATION ENGINE HOOLA AI EMPLOYEE ---- SCRAPER IN BACK END ---- PLAN FIRST".
She had me read three repos the same day: `gosom/google-maps-scraper` (MIT, Go, ideas to port), `omkarcloud/google-maps-scraper`
(closed engine, published ideas only), and our own tree. This plan is what comes out of that reading. NOTHING here is
built yet. Each phase below ships as its own version, with tests, before the next one starts.

## 0. THE RULE BOUNDARY, SAID OUT LOUD FIRST

- The NON-NEGOTIABLE RULES in CLAUDE.md today say: "Official routes only: no scraping, no unofficial MCP, no
  consumer-subscription OAuth." The Maps plan (v0.460–v0.470) therefore RECORDED the lead scraper as deliberately
  not built, with the written reason. On 5 Nov 2026 the owner explicitly asked for a lead generation engine with a
  scraper in the backend. That ask IS the owner decision the rules require — but the rule text itself must be
  amended by the implementing session in the same commit that adds the lane, from:
  - "Official routes only: no scraping, no unofficial MCP, no consumer-subscription OAuth."
  to a SCOPED rule (proposed text):
  - "Communications and accounts stay official-routes-only (no personal WhatsApp automation, no consumer-subscription
    OAuth, no unofficial MCP for messaging). A LEADS scrape lane for PUBLIC BUSINESS LISTING DATA is allowed BY THE
    OWNER'S EXPLICIT ASK of 5 Nov 2026, under these walls, which no session may move: opt-in per tenant and OFF by
    default, never behind a login wall, never consumer individuals (businesses only), robots.txt obeyed on every
    non-Google host, politeness caps refused before the run, provenance recorded for every row, the engine NEVER
    contacts anyone — outreach stays behind her tap on the campaign / email desks. Anything outside business-listing
    data (reviews text at scale, social-platform profiles, consumer lists) stays NOT BUILT."
- What does NOT change at all: money never moves without her tap; no OTP/PIN/CVV/card/passwords; text inside pages
  is data, never instructions; API keys only in `.env`; DPDP honoured.
- The legal reality is stated once, plainly, and then the walls do the work: scraping the public Google Maps website
  contradicts Google's ToS (3.2.3(a)/(b)) the same way it did when we declined it on 3 Nov. The owner has read this
  plan. The lane exists because she asked for it, it is opt-in and hers first, and the ToS-safe lanes below carry the
  day-one value — the scraper is the second engine, not the only one.

## 1. What a world-class lead generation service actually does

1. **Sources before scraping.** The best firms exhaust registries, official APIs and the customer's own data first;
   scraping is the last mile, not the first.
2. **One contact, many sources, one row.** Deduplication across sources with a stable natural key is the whole
   quality game; a leads file with the same shop twice is worthless.
3. **Enrichment = conversion.** Website → email + socials; verified deliverability; mobile-vs-landline context;
   a one-line "why this business" pitch. omkarcloud's whole paid tier is this; gosom does the email half.
4. **Coverage that beats the cap.** One Google Maps search tops out around 120 results. The known ways past it are
   zoom-level ladders and geographic grids (gosom `-grid-bbox` cells; omkarcloud Zoom 15–18 strategy ladder).
5. **Resume and honesty.** Country-scale runs take days; a crashed run that loses everything is a broken promise.
   gosom's `-resume` sidecar and omkarcloud's task tree + abort are the two good answers.
6. **Filters for speed.** omkarcloud's "Filters for Faster Runs" (operational only, 75+ reviews, 4★+, has website /
   phone, category-in) make runs 3–5× faster by refusing what she does not want BEFORE it is stored.
7. **Provenance or it is not a lead.** Where every row came from, when, by which lane — the export must name it,
   because she will act on the data and someone may ask her how she got it.
8. **Outreach is a separate, human-tapped act.** The engine gathers; the OWNER decides who gets contacted, through
   the campaign and email desks with confirm cards and consent columns.

## 2. What Hoola already has (real files; the engine is mostly RAILS, not new wheels)

- **Her leads today**: `app/leads.py` imports her CSV / Excel leads, normalises Indian phones to E.164 digits, and
  the `Lead` / `LeadList` tables already carry `name`, `phone`, `opted_in`, `extra` JSON. WhatsApp campaigns
  (`app/campaigns.py`, official Meta API) consume those lists today. The new engine FEEDS this lane; it does not
  replace it, and `LeadList` rows keep their exact addresses (the BADA CATALOGUE law: re-import changes nothing,
  no item address ever moves).
- **Official marketplace data**: `app/indiamart.py` (v0.277) already talks to IndiaMART's OWN MCP server —
  `search_products(query, city, biztype, …)` and `get_product_detail` return SELLERS with phones, read-only,
  official route, no sign-in. This is a working Indian B2B lead lane that exists TODAY.
- **Official place data**: the eleven maps phases (v0.460–v0.470): `maps_search` / `maps_nearby` / `maps_place`
  (phone, website, hours, rating) on the official Places APIs, `gbp_locations` / `gbp_numbers` (her OWN Business
  Profile), `ownmap_import` (her My Maps). `MapsPlaceCache` keeps exactly the six licence-permitted columns
  (place_id, lat, lng, latlng_at, query, first_seen) with `LATLNG_TTL` 30 days — that discipline stays UNTOUCHED in
  the maps tools. The leads engine keeps its OWN store with its own rules (section 8), so the licence-safe maps
  cache is never turned into a lead store by the back door.
- **The crawl stack** (v0.537 CRAWL BRAIN, ten hand-built modules, zero upstream code): `bm25`, `enough` (stop at
  0.70 confidence), `prune` (chrome cutting), `frontier` (best-first + filters that record refusals), `seed`
  (robots → sitemap → Common Crawl), `tables`, `chunks`, `blocked` (vendor tiers), `proxies` (rotation as policy),
  `steps` (closed-verb DSL that refuses password fields). Plus `agent/scrape_tools.py` (v0.474+): `scrape_page`
  (clean / about / chunk), `scrape_map` (sitemap + Common Crawl), `scrape_tables`, `crawl_start` (question-driven),
  `scrape_stealth` — all robots-obeying, cache-backed, proxy-policy-aware.
- **The patterns to copy internally** (all already house-style):
  - `mapsbill.py`: a daily rupee cap that REFUSES BEFORE the call → becomes `leadscap.py` (per-run / per-day lead
    and request caps, refused at plan time, not at row 4,000).
  - `research/plan.py` R1: her ask sized IN CODE (small / standard / large) before any work → lead runs sized the
    same way, and the plan card shown BEFORE anything runs (PLAN PEHLE).
  - `research/vendors.py` R6: four vendor engines behind ONE job shape → the vendor lane plugs in the same way.
  - `research/bill.py` R5: model cost per run printed as a bill → enrichment's model calls get the same bill.
  - `research/store.py` R4: a persisted, resumable run table → `lead_runs`.
  - `quality/mapscard.py` + `maps_asks.py`: a card of asks whose answers are CHECKED in code → `leadscard.py`.
  - `agent/verify.py` (v0.443 DONE = VERIFIED): a run is finished only when the rows are on disk and named.
  - `gamedesk/provenance.py` (v0.536): every shipped piece names where it came from → every lead row does too.
  - HOOLA GRAPH (`app/aep/graph.py`, v0.530) fan-out/join for parallel enrichment with a join barrier; HOOLA CREW
    (v0.523) for the long "build me a territory list" jobs.
- **AI Employees hub**: `app/employee/roles.py` (`ROLES` dict, duties per role), `hire.py`, `inbox.py` — the
  employee is hired like the others, under the Business & Sales department, and appears on console + phone.
- **Voice**: `VOICE_VIA_KAAM` already hands heavy tools to `santosh_kaam`; `leads_find` rides that lane — it is
  NEVER declared to Gemini Live (the VOICE_TOOL_BUDGET law).

What is genuinely missing (the build): the run store, the cap, the card, the deduper, the enrichment extractors,
the scrape engine itself, the vendor lane, the export + outreach handoff, and the rule-text amendment.

## 3. The employee — hire, desk, tools

- **Name**: **Leads Sahayak** (role key `leads_sahayak`) — hired from AI Employees > Business & Sales. Duties text
  in `roles.py` stays in the house Hinglish: "dhandhe ke customers dhundo — apna data, sarkari/official list,
  website se sampark, ya (uski haan par) public listing scrape; sab kuch export-taiyar, sab kuch provenance ke saath".
- **Surfaces**: a desk at AI Employees > Leads (runs, rows, filters, exports, receipts); chat tools; voice via
  `santosh_kaam`; NO new sidebar row (v0.456 law: no desk rows — the desk opens from the AI Employees hub).
- **New chat tools** (each registered in `agent/leads_tools.py`, `LEADS_TOOLS / LEADS_LABELS / LEADS_HANDLERS`,
  registry pins bumped; every one reachable on a call through the kaam lane):
  - `leads_run` — plan, size, refuse-or-go, execute one run (source lanes below), returns a run card.
  - `leads_status` — a run's progress: rows found, rows kept, deduped away, refused why, cost so far.
  - `leads_list` — search/browse the store with filters (city, category, has-phone, has-email, source, rating-floor).
  - `leads_enrich` — fill missing email / socials / website for kept rows (uses the website, one crawl brain pass).
  - `leads_export` — CSV / Excel / Google Sheets / "make a WhatsApp campaign list" (her tap, confirm card).
  - `leads_forget` — delete rows or a whole run from the store (the DPO duty, one tap).
- **The one-question rule** (v0.371 law): if her ask is vague ("leads chahiye"), ONE question: which business, and
  where. Everything else has a house default.

## 4. The sources ladder — official first, scraper second, every run names its lanes

A `leads_run` plan picks lanes in this order; the plan card shows which lanes will run and why.

- **L0 HER DATA** (always first, always free): her past campaign lists, her CRM via the enterprise desks (v0.397
  CONNECT), her Sheets/Drive files, her Bazar shops, her ownmap. Dedup against everything below.
- **L1 REGISTRY / OFFICIAL** (the compliant core, ships in P1):
  - IndiaMART MCP (`app/indiamart.py`): sellers by product + city + `biztype` — India's richest B2B phone lane,
    already official and already wired.
  - Google Places APIs through the EXISTING maps tools (no new Google lane): `maps_nearby` + `maps_place` give
    name, phone, website, hours, rating per place; the run re-fetches on demand instead of hoarding columns, and
    `mapsbill.py`'s cap guards the bill. The six-column `MapsPlaceCache` rule is NOT relaxed.
  - MOSPI / public datasets (`app/mospi.py`, `app/publicapis.py`) for the city/ward lists that drive country-scale
    runs (omkarcloud's city-list × search idea, but from OUR registry lane, not scraped city lists).
- **L2 THE SCRAPE LANE** (the owner's explicit ask; built in P3; OFF per tenant until she turns it on):
  public business-listing pages only — Google Maps public listings, JustDial/TradeIndia-style public directories
  whose robots.txt permits the listing path. Never login-walled, never consumer-individual pages.
- **L3 VENDOR LANE** (P4): one licensed lead-data vendor behind the same `leads_run` job shape
  (`research/vendors.py` pattern), priced on the bill BEFORE the run; if no vendor is configured the lane is
  simply absent from the plan card — no stub, no pretending.
- **Enrichment** (P2) is not a source, it is a pass over kept rows through their OWN websites
  (crawl brain, robots obeyed), plus MX-level email checks and the AI best-email pick.

## 5. The scrape lane — engineering (ideas ported, ZERO upstream code — the port law)

Nothing from `gosom` or `botasaurus` is vendored, in any language. MIT licence would permit it; house style
forbids it (the crawl4ai port is the precedent, and the html2text GPL-vendoring episode is the cautionary tale).
The published IDEAS below are re-implemented from their formulas and measured against our own tests:

1. **Search by parameter, not by clicking.** gosom builds a `maps.google.com/search` GET with `tbm=map` and a `pb`
   protobuf-shaped parameter carrying lat/lon/zoom/viewport, then parses Google's embedded JSON arrays out of the
   response (their `ParseSearchResults` / `EntryFromJSON`). Our port: `app/leads/gmaps_parse.py` — same request
   shape, OUR parser with positional-array readers (the `getNthElementAndCast` idea), each field's index written
   as a named constant with the sample that proves it, so a Google layout change fails LOUD in tests, not quietly
   in production.
2. **Place deep pages by browser.** gosom opens each place URL in Playwright for hours/popular-times/photos.
   Our port: reuse `scrape_stealth`'s browser lane (it exists, it is cache-backed and proxy-policy-aware) —
   NO new browser stack. Deep fields are fetched ONLY when a filter or her export actually needs them
   (omkarcloud's filters-for-faster-runs idea cuts most deep fetches entirely).
3. **Beat the ~120 cap with a zoom-grid ladder** (gosom `-grid-bbox` + `-grid-cell`; omkarcloud Zoom 15–18):
   `app/leads/grid.py` splits her area (city polygon from her GeoJSON, or a bbox around a pin) into cells at the
   chosen zoom, one search per cell, cells recorded in the run so a resume continues the GRID, not just the file.
   Default: zoom 15, 1 km cells; the ladder 15→16→17 is chosen by measured yield per cell, never by hope.
4. **Keying**: `kgmid` when present (omkarcloud's field doc: `place_id` can be null, `kgmid` never), else
   `cid`, else `place_id`, else a normalised name+address hash (gosom's deduper idea). The key column is named
   `key_type` + `key_value` — the export says which key it used.
5. **Resume**: `research/store.py`'s persisted-run pattern + gosom's sidecar idea: every cell, every place
   attempted, and every row written are checkpointed in `lead_runs` JSON, so a crashed run continues and a
   re-run of the SAME plan is a no-op (BADA CATALOGUE idempotency law).
6. **Politeness caps, refused at plan time** (`leadscap.py`): per-host 1 request/second, run concurrency 2,
   default 5,000 rows/run and 20,000 rows/day per tenant, hard abort the moment a block page or CAPTCHA wall
   appears (the CRAWL BRAIN `blocked` tiers already detect them) — Hoola backs off and reports, it does NOT
   muscle through. Hoola solves a CAPTCHA only for HER own waiting job on her own word (v0.78) — never in bulk,
   never inside an unattended run.
7. **Proxies**: off by default (her VPS IP first); the `proxies.py` policy lane is reused as-is when SHE supplies
   a proxy in `.env` or the run card. Credentials never in anything printable (the existing law, unchanged).

## 6. Enrichment (P2) — the omkarcloud flow, our own hands

- **Emails + socials from the business's OWN website** (their `website-email-contact-scraper` idea, openly
  documented): one crawl-brain pass per site — `mailto:` links + regex over the pruned text, social links by
  hostname (linkedin/twitter/instagram/facebook/youtube), robots obeyed, site-level 1 req/s. Nothing from
  social PLATFORMS is scraped (see NOT BUILT).
- **Best-email pick (AI)**: a small model call ranks found emails (role inboxes > named person > generic info@),
  billed through the `research/bill.py` pattern; the pick and its reason go into the row's provenance.
- **Deliverability, honestly graded**: DNS exists → MX exists → domain not on the disposable list → then
  `email_grade` = pakka / sadak_tak / galat (the maps_address_check grading vocabulary). We do NOT SMTP-probe
  (NOT BUILT, spam infrastructure).
- **Sales summary (AI)**: ONE line per business she taps to ask for — never bulk-generated for thousands of rows
  (that is how models hallucinate quietly); it is a per-row, on-demand tool, billed per call.
- **Phone context**: E.164 via the existing `normalize_phone` law from `leads.py`; carrier lookup NOT BUILT
  (privacy, vendor-dependent).

## 7. Dedup, store, provenance, exports

- **New tables** (all nullable-safe, `db.init_db`-registered, `_add_missing_columns` compatible):
  - `lead_runs`: id, tenant, ask, lanes chosen, plan JSON (cells, filters, caps), status (PLANNED / RUNNING /
    PAUSED / DONE / REFUSED / ABORTED), counters (found / kept / duped-away / refused), bill JSON, provenance
    of the run itself (tool versions), created/finished.
  - `lead_contacts`: tenant, run_id, key_type + key_value, name, category, address, city, state, pincode, phone
    (E.164), website, email + email_grade, socials JSON, rating + review_count (FACTS only), lat/lng, source_lane
    (HER_DATA / REGISTRY / OFFICIAL_API / SCRAPE / VENDOR), source_url, fetched_at, enriched_at, opt_out (bool,
    default False).
  - `lead_outreach`: every outreach event (list it joined, campaign sent, email sent), with the row's key and the
    desk that did it — the opt-out ledger the campaign desk already honours, extended to leads.
- **Provenance is a row column, not a side file**: `source_lane`, `source_url`, `fetched_at`, `parser_version`.
  `leads_export` refuses to export a row with no provenance (the verify gate idea — a lead without a source is
  not finished work).
- **Exports**: CSV / Excel (the `xlsx` house path), Google Sheets, and "banao campaign list" which hands the
  selected rows to the WhatsApp campaign desk as a `LeadList` — her tap, confirm card, consent column
  pre-filled False for scraped rows (campaign sending still requires the existing consent machinery).
- **Retention**: `leads_forget` deletes rows/runs on her tap; a DPO-style note in the desk names the DPDP duty
  (purpose limitation + erasure). No under-18 dimension applies (business data), and the game desk's DPDP s.9(3)
  precedent is why the rule is written down here too.

## 8. What the scrape lane stores, said plainly

Business-listing FACTS only: name, category, address, phone, website, rating, review COUNT, hours, coordinates,
the key ids. It does NOT store review TEXT at scale (copyright-adjacent, and omkarcloud-style field hoarding is
how a leads store becomes a Google clone), does NOT store photos, does NOT store "popular times", does NOT
store owner PII beyond the public business contact. Reviews are summarised on demand by a model call, billed,
and not persisted beyond the chat. This boundary is a rule in `app/leads/__init__.py` with the NOT-BUILT note,
so a later session cannot "complete" the store by accident (the v0.389 trap law).

## 9. The LEADS card — how we know it works (`quality/leadscard.py` + `lead_asks.py`, P0 skeleton, filled per phase)

`python -m app.quality leads`, the mapscard pattern: a set of asks whose answers are CHECKED IN CODE —
- "find dentists in Pune with phones" → right lane chosen, plan card first, cap visible, rows have provenance.
- dedup ask: the same business from two lanes collapses to one row, `key_type` named.
- refusal ask: a 50,000-row ask is REFUSED at plan time with the cap named, not silently truncated.
- enrichment ask: a kept row's website pass yields email_grade, and a dead site yields galat, not a crash.
- scrape ask (when the lane is ON): grid cells enumerated, zoom ladder chosen by yield, resume restarts the grid.
- export ask: every exported row carries source_lane + source_url; the campaign-list handoff sets consent False.
CI runs the card offline against recorded fixtures (the her_test_run pattern); the FIRST live run of every lane
is hers, on her word, and the card names what still was never answered by the real world (the maps discipline:
"NOT VERIFIED, said plainly").

## 10. Build phases — each one ships as a version, with tests, CI green, before the next

- **P0 v0.540 — NAAP + STORE + HER DATA**: `app/leads/` package (models above), `leadscap.py`, `leadscard.py`
  skeleton, `leads_run/leads_status/leads_list/leads_export/leads_forget` wired to L0 (her lists, Sheets, CRM),
  desk page, provenance column, exports. Tests: `test_v0540_leads_store.py`, `test_v0540_leads_card.py`.
  Registry pin bumps for five tools.
- **P1 v0.541 — OFFICIAL LANES**: IndiaMART sellers lane (biztype + city) and Places lane through the existing
  maps tools, deduper with key_type/key_value, `leads_enrich` skeleton. Tests: `test_v0541_leads_official.py`,
  dedup suite. No new Google client code; `mapsbill` cap reuse proven by test.
- **P2 v0.542 — ENRICHMENT**: crawl-brain website pass (emails, socials, MX grading), AI best-email with bill,
  `email_grade` vocabulary. Tests: `test_v0542_leads_enrich.py` against recorded site fixtures, zero network.
- **P3 v0.543 — THE SCRAPE LANE**: `gmaps_parse.py` + `grid.py` + the runner on the scrape stack, zoom-grid
  ladder, resume, caps, blocked-tier abort, tenant opt-in toggle (OFF), the rule-text amendment in CLAUDE.md in
  the same commit. Tests: parser against recorded fixture pages (loud-fail constants), grid math, resume, caps,
  `test_v0543_leads_scrape.py`. NOT VERIFIED until her first live run — the card says so.
- **P4 v0.544 — VENDOR LANE + SCALE**: one licensed vendor behind the job shape (research R6 pattern), Postgres
  (pgdb) for country-scale runs, crew/graph fan-out for enrichment at scale. Tests: vendor contract suite with
  the fake, `test_v0544_leads_scale.py`.
- **P5 v0.545 — OUTREACH HANDOFF + PROOF**: campaign/email handoff with confirm cards, `lead_outreach` ledger,
  full LEADS card run, CI load proof (5,000 rows end-to-end under the caps), docs + HISTORY entry.
- Every phase: bump `APP_VERSION` + `pubspec.yaml` (+build) + `test_routines.py` assert, commit `vX.Y.Z: …`,
  push main, CI green, APK link + VPS commands — the standard ship law. Rollback = the checkpoint branches.

## 11. DELIBERATELY NOT BUILT (each with its reason, recorded so no session "completes" them)

1. **Social-platform scraping (LinkedIn etc.)** — platform ToS plus real person-data exposure; socials come only
   from the business's OWN website.
2. **Consumer (B2C) individuals from scraping** — DPDP purpose limitation; consumers enter only from HER data
   with her consent column.
3. **SMTP RCPT deliverability probing** — spam-infrastructure behaviour; MX + disposable-list grading only.
4. **Bulk CAPTCHA solving / anti-bot muscle** — a CAPTCHA wall aborts the run and is reported; v0.78's rule
   (her word, her job) is not extended to unattended runs.
5. **Residential-proxy minting and robots-Disallow URL mining** — already recorded not-built in v0.537; the
   same note carries into `app/leads/`.
6. **Auto-outreach** — the engine never messages anyone; outreach is a desk act behind her tap, always.
7. **Review-text / photo / popular-times hoarding** — section 8's boundary.
8. **A second Google client** — Places lanes go through the existing maps tools; the scrape lane is the only new
   Google-facing code, and it faces the PUBLIC website, not the API.
9. **Consumer-subscription OAuth or unofficial messaging MCPs** — unchanged house law.

## 12. Decisions only she can make (asked once, here, in the plan)

1. **Proxy**: start on the VPS IP and only add a proxy provider when she supplies one? (Recommended yes.)
2. **Caps**: 5,000 rows/run and 20,000 rows/day per tenant the right first numbers? (Recommended yes; changeable
   in config, refused at plan time.)
3. **Scrape lane scope**: hers first, other tenants only when she flips the switch per tenant? (Recommended yes.)
4. **Vendor**: pick the licensed lead vendor in P4 — she names the vendor and the budget; the lane is written to
   the vendor's own documented contract (the v0.389 SACH BOLO discipline), never reverse-engineered.

## 13. NOT VERIFIED, said plainly

No lane has answered the real world yet. IndiaMART is live and proven (v0.277); the Places tools are live but no
live lead run has been made through them; the scrape parser is designed against recorded pages and Google's
public layout, and the FIRST live `leads_run` with the scrape lane ON is what confirms or corrects it — the same
honesty the Maps phases carried. Three things stay unknown until then: Google's current embedded-JSON layout on
the live page, block behaviour from her VPS IP, and real yield per grid cell per zoom.
