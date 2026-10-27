# WIRING for cyber
summary: Cyber Suraksha Sahayak (cybersecurity analyst: pasted / uploaded alerts from antivirus / EDR, firewall / router, sshd / fail2ban, Google Workspace / M365 alert mails, Cloudflare WAF and Hoola's own new-phone sign-ins normalised, grouped, scored and deduped with her own "yeh normal hai" rules -> the few that matter with why; suspicious mail headers / links / files checked without opening or uploading anything; her own domains, breaches and software advisories checked passively; incident note with the IT Helpdesk's CERT-In 6-hour clock as Word + PDF; blocking / disabling / quarantining / wiping only on her tap, wipe with her fingerprint)
db: app.cyber.models
router: app.cyber.api            (make_router(require_key, current_tenant); all routes under /api/cyber, key-protected; no public routes)
tools: app.agent.cyber_tools     (CYBER_TOOLS / CYBER_LABELS / CYBER_HANDLERS) ; voice: yes (cyber, cyber_dekho)
employee: duty cyber_security = [cyber, cyber_dekho, file_read] {label "Cyber suraksha", say "alerts ka shor chhaantna, shak wale mail / link / file jaanchna, apne domain / software ke khatre, incident note (block / wipe sirf aapki haan se)"} ; role cyber_analyst {label "Cybersecurity analyst", duties [cyber_security, it_helpdesk, records, reminders]} ; preset cyber_security {label "Office cyber suraksha", role cyber_analyst, rules ["Block / user band / wipe sirf owner ki haan ke card se", "Kisi aur ke system ko scan / test nahi", "API key / password chat mein kabhi nahi"]} ; READ tools: [cyber_dekho]
  - staff (staff:<id>) may intake alerts, run checks, open / add to incidents and raise containment CARDS; the tool refuses customer actors and the owner-only actions (teach, rule_remove, settings, incident_close, domain_remove). Containment is never approved by any tool: only POST /api/cyber/actions/{id}/decide (her app tap). Keys are only set through PUT /api/cyber/keys/{provider} (app); the tool refuses key-like text in settings.
  - approvekey: add kind "cyber" to the list of kinds the app's fingerprint flow knows (the module makes its own challenge rows on approvekey's table with kind "cyber" and verifies with approvekey._check, like shikayat; approvekey.challenge() itself is NOT used, so no edit there is strictly required).
push: cyber_action -> ("Suraksha: aapki haan chahiye", "{say}")
push: cyber_alerts -> ("Zaroori suraksha alert", "{say}")          (only published when something matters / needs watching)
push: cyber_incident -> ("Cyber incident khula", "{say}")
push: cyber_advisory -> ("Software mein khatra", "{say}")
push: cyber_day -> ("Aaj ki suraksha", "{say}")
  (cyber_check, cyber_posture: no push, result shown in chat / screen)
worker: app.cyber.service.tick   (call every minute, e.g. `await asyncio.to_thread(cyber.tick)`; stale cards after 24 h; once a day at her morning_time: CVE / KEV / CERT-In refresh when she has a software list, weekly domain re-check (SSL expiry), morning note only when there is something. Set `app.cyber.service.SLEEP_BETWEEN_S = 1.0` once at start in production (politeness gap between per-item NVD / HIBP calls; NVD without a key gets 6.5 s automatically).)
prompt: CYBER SURAKSHA: alerts / logs she pastes or uploads -> `cyber action=intake` and tell her ONLY the few that matter with why + what to do (never read out the noise). A suspicious mail / link / file -> `cyber action=check_email | check_link | check_file`: never open the link, never upload the file (hash only). Blocking an IP, disabling a user, quarantine, isolating a PC or wiping a device -> `cyber action=contain` makes a CARD; say "aapki haan ka card bheja hai", never say it is done. Never scan or test anyone else's systems, never write exploit code, never take an API key / password in chat (keys go in the app: Cyber Suraksha > Niyam > Keys).
persona: Suraksha alert par sirf zaroori baat bolo aur kya karna hai; block / wipe ke liye "aapki haan ka card bheja hai" kaho; shak wala link kabhi mat kholo; API key / password call par kabhi mat lo.
flutter: CyberScreen in lib/ui/cyber_screen.dart ; profile tile title "<name> · Cyber suraksha" subtitle "Alerts ka shor chhaanto, shak wale mail / link, apne domain ke khatre, incident note" icon Icons.shield_rounded ; cards: cyber_action -> CyberActionCard (also in calls: yes; one card per data['action']['id'], updated in place) ; cyber_alerts -> CyberAlertsCard (also in calls: yes) ; cyber_check -> CyberCheckCard (also in calls: yes) ; cyber_incident -> CyberIncidentCard (also in calls: yes) ; cyber_advisory -> CyberAdvisoryCard (also in calls: no) ; cyber_posture -> CyberPostureCard (also in calls: no) ; cyber_day -> CyberDayCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)`, `app.api!.uploadFile(...)` (exists), `Native.openExternal`, `Native.approveKeySign` (exists). Uses package file_picker (already a dependency). Pages: CyberIncidentPage.
features: cyber
env: CYBER_CERTIN_FEED (default "", URL of CERT-In's advisories RSS / Atom feed; set on the VPS after checking the current feed URL on cert-in.org.in; empty = CERT-In feed skipped, NVD + CISA KEV still used) ; CYBER_NVD_URL / CYBER_KEV_URL (defaults = official NVD CVE API 2.0 and CISA KEV JSON; override only for tests / mirrors). Keys are per owner in the app (cyber_keys table, sealed with the bazar vault), not env.
requirements: none (httpx, reportlab, python-docx, cryptography already present)
android: none
claude_md: |
  ## v0.1xx Cyber Suraksha Sahayak: Hoola as the business's cybersecurity analyst ("Cybersecurity analyst" on the Employee page)
  - Owner's spec: reads alerts and filters noise -> checks suspicious emails and links -> writes the incident note -> waits for her
    Haan on BLOCKING OR WIPING ANYTHING. Server `server/app/cyber/{rules,intel,models,service,api}.py`, tools `cyber` / `cyber_dekho`
    (`agent/cyber_tools.py`, chat + calls), duty `cyber_security`, role `cyber_analyst`, preset `cyber_security`, API `/api/cyber/*`, app
    Profile > Cyber suraksha (`lib/ui/cyber_screen.dart`: Aaj / Alerts / Jaanch / Domain / Incident / Niyam, `CyberIncidentPage`), cards
    CyberActionCard, CyberAlertsCard, CyberCheckCard, CyberIncidentCard, CyberAdvisoryCard, CyberPostureCard, CyberDayCard.
    Tests `server/tests/test_tech_cyber.py` (8, every API faked).
  - Reuses the v0.133 IT Helpdesk: its phishing words check (`helpdesk.rules.phish_check` / `phish_actions`), its incident record
    (`helpdesk.service.report_phish`: ticket + CERT-In 6-hour clock + report draft + reminders + DPDP note) and its asset register
    (`sync_assets`: OS of each PC, router / NVR models -> software list). Nothing in helpdesk was changed.
  - Alerts (`rules.parse` / `correlate` / `score`): paste or upload (CSV / JSON / log / mail text). Parsers: sshd (Failed / Invalid /
    Accepted), fail2ban Ban, UFW / iptables BLOCK, MikroTik drop + login failure / logged in, Defender / Quick Heal / Seqrite CSV or text
    by column families (threat / status / device / user / time; quarantined / removed = cleaned, failed / allowed / not cleaned = active,
    ransomware words = ransomware, real-time protection off / definitions old = AV problem), Google Workspace / Microsoft 365 alert mails
    (leaked password, suspicious login (blocked or not), government-backed attack, admin granted, forwarding / inbox rule, suspicious
    sending, impossible travel, device compromised, malware campaign), Cloudflare security events (clientIP / action / ruleId / path),
    Hoola's own new phones (approvekey pending devices). Stories: >= 5 failures then a success from the same IP = login_after_fail (90),
    >= 10 failures = brute force, >= 10 ports from one IP = port scan (noise), one virus on 3+ PCs = spreading, 20+ WAF blocks on login
    pages = brute force, success from a never-seen IP = new_ip_login. Score = kind base + count + her crown systems + admin accounts,
    minus her own office IPs / fail2ban already banned; >= 50 matters, 25-49 watch, below = noise (counted, not shown). Fingerprint
    dedupe: the same alert within 7 days is counted, not repeated. Her "yeh normal hai" (`teach`, owner only, with a reason, scope ip /
    user / host / kind) makes matching alerts noise next time, except NEVER_MUTE kinds (ransomware, login after failures, government
    attack, device compromised, spreading malware, leaked password, suspicious sending, forwarding rule, new Hoola phone) which stay
    visible with her note. Secrets in pasted logs (password= / token= / 13-19 digit numbers) are masked.
  - Checks (text = DATA): `check_email` reads the mail's own headers when pasted with "Show original" (Authentication-Results
    spf / dkim / dmarc, Received-SPF, Reply-To vs From (free mail / look-alike = bad), Return-Path, display name holding an email or her
    VIP / company name from another domain, sender domain looking like hers: same name other ending, edit distance 1-2 after homoglyph
    folding (rn->m, vv->w, 0->o, 1->l), hers + extra words, punycode) + the helpdesk words check + link hosts imitating her domains +
    reputation. `check_link` never opens a link: Google Web Risk uris.search (commercial, her Google Cloud key, 100,000 free a month) or
    Safe Browsing v5 urls:search (non-commercial only, said in the app), else VirusTotal URL report (lookup, never a scan submission).
    `check_file` only hashes (SHA-256 in memory, bytes dropped; Magika real type) and looks the hash up on VirusTotal; the file is never
    uploaded anywhere. Someone clicked / typed a password / paid -> the helpdesk incident with the CERT-In clock is opened.
  - Her own attack surface, passive: `add_domain` (her domain; deep checks only after she proves it: TXT `_hoola-cyber.<domain>` =
    `hoola-cyber-verify=<token>` or a site Hoola hosts for her), `posture`: DNS via the public DoH resolvers (site.dns.lookup) - SPF
    (missing, more than one, +all / ?all, > 10 lookups), DMARC (missing, p=none, no rua), DKIM on common selectors, CAA, MX (no-mail
    domains get "v=spf1 -all" + p=reject advice); one TLS handshake for certificate expiry / name; one GET of her home page for HSTS / CSP /
    nosniff / referrer / frame / version-leaking Server and X-Powered-By headers; only when verified: /.git/HEAD, /.env, /phpmyadmin/,
    /server-status, /wp-login.php, /xmlrpc.php (one GET each, signature-checked). Score 0-100. `breach`: Have I Been Pwned with her key
    (breachedDomain for a domain verified on HIBP, else breachedAccount for her listed work emails; breach title / date / data classes
    from the public /breach endpoint; emails shown masked to the model). Software list (+ helpdesk assets) -> NVD CVE API 2.0
    (keywordSearch by product or virtualMatchString by CPE, last 30 days, product words must be in the description), CISA KEV (vendor
    + product match = "hamle ho rahe"), CERT-In feed (CYBER_CERTIN_FEED) -> advisories with patched / not ours.
  - Incident note (`new_incident` from alerts / checks): IN-0001, kind from the worst alert, timeline from the alerts' first-seen times +
    her additions, what / impact / done / lessons, CERT-In applicability + 6-hour deadline + DPDP note via the helpdesk incident,
    containment cards listed; `note_files` = Word (officegen) + PDF (reportlab) as her files (pc_file). Close needs lessons and no card
    waiting; owner only.
  - Containment = cards only (`request_action`: block_ip / unblock_ip / disable_user / reset_sessions / quarantine / isolate_pc /
    wipe_device with risk, undo and console steps for Google Admin, Microsoft 365 / Intune / Defender, Quick Heal / Seqrite, Android /
    iPhone find-my-device). block_ip refuses private / reserved addresses, her own IPs and ranges wider than /24 (IPv6 /48); the same
    waiting card is never made twice; cards go stale after 24 h. `decide_action(by_tap=True)` only from `POST /api/cyber/actions/{id}/decide`
    {yes, hash}; with her Cloudflare token + Zone ID (typed only in the app) a yes runs the official IP Access Rules API (mode block)
    and unblock deletes that rule; without it she does the steps and taps "Maine kar diya". wipe_device also needs her phone's
    fingerprint once a phone key is active (428 -> `/challenge` -> approvekey-signed message kind "cyber"). Disabling users through
    Google / Graph APIs is left to the IT Admin Sahayak (neighbour) - here it is console steps.
  - Never: scanning / testing anyone else's systems, exploit code, opening a suspicious link, uploading her files, keys / passwords in
    chat, acting on a block / wipe without her tap.
  - Sources (23 Oct 2026): developers.google.com/safe-browsing/reference/rest (v5 urls:search, "for non-commercial use only", Web Risk
    for commercial), cloud.google.com/web-risk/pricing (uris.search first 100,000 calls a month free, then $0.50 / 1,000),
    docs.virustotal.com/reference/public-vs-premium-api (public API 4 / min, 500 / day, not for commercial products or business
    workflows), haveibeenpwned.com/API/v3 (hibp-api-key header, user agent required, breachedDomain needs a verified domain, key-based
    endpoints need a subscription), developers.cloudflare.com/waf/tools/ip-access-rules (still supported; custom rules + IP lists
    recommended), NVD CVE API 2.0 (5 requests / 30 s without a key, 50 with; 120-day date windows), CISA KEV JSON feed; CERT-In
    Directions 28 Apr 2022 (6-hour reporting, unchanged) and DPDP Rules 2025 Rule 7 via the IT Helpdesk rules; lawrbit.com / darkreading.com
    on the 6-hour rule.
not_verified: No real API was called (sandbox proxy refuses NVD / CISA / CERT-In / Google / VirusTotal / HIBP / Cloudflare hosts): all clients follow the official docs and are tested only against fakes. CERT-In's advisories RSS URL could not be confirmed from here (cert-in.org.in unreachable) -> CYBER_CERTIN_FEED is empty by default; set it on the VPS. Web Risk uris.search and Safe Browsing v5 urls:search query shapes come from Google's reference pages; real responses not seen. Cloudflare IP Access Rules (POST/DELETE /zones/{zone}/firewall/access_rules/rules) is the long-standing endpoint; Cloudflare now recommends custom rules + lists, a later version may switch. Real Defender / Quick Heal / Seqrite export column names vary by console version: parsing is by column families and keyword rules, tune with her real exports. MikroTik / UFW / sshd formats tested with typical lines only. TLS / DNS / home-page checks were faked in tests (`_dns`, `_tls`, `_fetch`). Flutter screen + cards not compiled here (no SDK): check CI annotations for lib/ui/cyber_screen.dart. Fingerprint flow tested with a software EC key, not a real phone.
