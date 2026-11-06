# WIRING for leads (v0.540.0 LEADS NEEV: the lead generation engine's foundation, plan first)
summary: lead_runs + lead_contacts + lead_outreach (one business one row, key_type/key_value: kgmid > cid > place_id
> name+address hash > phone_e164; provenance is row columns - source_lane/source_url/parser_version/fetched_at, a row
without it is never stored and an export that finds one REFUSES), leadscap refuses AT PLAN TIME (per-run 5,000 rows,
per-day 20,000 rows/tenant from the lead_cap_days ledger, the number named in the refusal), P0 runs L0 only (her own
data via run_her_data; REGISTRY/OFFICIAL_API arrive P1, SCRAPE P3 owner opt-in OFF, VENDOR P4 - unbuilt lanes refused
BY NAME with the phase), campaign-list hand-off copies ONLY rows with a phone into a LeadList consent=False + writes
the LeadOutreach ledger (the engine NEVER sends; outreach is a desk act behind her tap), forget() deletes rows/runs
(DPO duty) but the day's cap ledger survives, opt_out flag per row the campaign desk honours.
db: app.leads.models (lead_runs, lead_contacts, lead_outreach, lead_cap_days, lead_list_refs) + app.leads.importer
(the old app/leads.py moved INSIDE the package, same names re-exported; lead_lists/leads tables unchanged)
router: app.leads.api (/api/leads/*; her taps: POST /runs/her-data, /export, /campaign-list, /forget, /opt-out)
enrich: app.leads.enrich (v0.542.0 P2) - ONE bounded crawl-brain pass per kept row's OWN website through the
EXISTING scrape stack (scrape_tools._guard_url/_robots_allowed/_fetch: SSRF guard, robots gate, curl_cffi, proxy
policy), text via crawl.prune, block pages via crawl.blocked; emails = mailto + regex over pruned text, socials
by hostname of HER site's links (platforms NOT fetched), email_grade = DNS -> MX -> disposable ->
pakka/sadak_tak/galat (NO SMTP probe), best email = ONE cheap-brain call per row caught by usage.run_meter
(research/bill pattern; no model -> the deterministic rank answers, labelled 'rule'). Cap
LEADS_ENRICH_ROWS_PER_RUN=100 refuses at plan time; dead site = a recorded galat, never a crash; new email
only fills an EMPTY slot. POST /api/leads/enrich + the leads_enrich tool.
tools: app.agent.leads_tools (leads_run, leads_status, leads_list, leads_export, leads_forget, leads_enrich; family "leads" in
admit.EXTRA_KEYS) ; voice via santosh_kaam
employee: duty leads_work ; role leads_sahayak ; preset leads_desk
cap: app.leadscap (mapsbill pattern: LeadsCapped at plan time, would_exceed for the card, record after the run)
card: app.quality.leadscard + lead_asks (free card: tools registered + reachable, guards in code - provenance gate,
plan-time cap, unbuilt lanes refused, consent=False hand-off, ledger; CI runs it offline)
not_verified: no live run yet - the store, caps, dedup, exports, lanes and the P2 enrich pass are tested offline
against fixtures; her first real her-data run, her first live IndiaMART/Places sweep and her first live enrich
pass (a real website read) are what confirm the flows.
