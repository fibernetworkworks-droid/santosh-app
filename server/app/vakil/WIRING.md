# WIRING for vakil
summary: Vakil Sahayak (lawyer's junior: case diary with CNR / case number / stage / next date, case status + cause list read from text she pastes from the official eCourts app / court site, limitation last dates from her dates by Limitation Act ss.4 / 12 (always andaaza), drafts for the advocate (adjournment, vakalatnama checklist, list of dates & events, synopsis, notice reply via Lekhak), document checklist per matter, fee ledger; filing / any message to a client or the other side / fee request only on her tap, fee with her fingerprint)
db: app.vakil.models
router: app.vakil.api            (make_router(require_key, current_tenant); all routes under /api/vakil, key-protected; no public routes)
tools: app.agent.vakil_tools     (VAKIL_TOOLS / VAKIL_LABELS / VAKIL_HANDLERS) ; voice: yes (vakil, vakil_dekho)   [if the voice tool budget is tight (v0.149), put both in VOICE_VIA_KAAM too]
employee: duty legal_junior = [vakil, vakil_dekho, file_read, lekhak, lekhak_dekho] {label "Lawyer's junior", say "court diary, tareekhein, cause list, limitation (andaaza), drafts vakil sahab ke liye, client update drafts, fee hisaab (filing / message / fee maangna aapke tap se)"} ; role lawyer_junior {label "Lawyer's junior", duties [legal_junior, reminders, records]} ; preset law_office {label "Vakil ka office / law chamber", role lawyer_junior, rules ["Hoola salah nahi deta: har draft / tareekh vakil se pakka", "Filing, client / doosre paksh ko message, fee maangna sirf owner ki haan se", "Ek client ki baat doosre client ko kabhi nahi"]} ; READ tools: [vakil_dekho]
  - staff (staff:<id>, e.g. a clerk / junior) may add matters, hearings, events, docs, paste case status / cause list, compute limitation, make drafts and make cards; owner-only actions in the tool: settings, fee (ledger entries incl. 'received'), forget, matter status closed / disposed. Customer actors are refused (privileged). No tool can decide a card: only POST /api/vakil/cards/{id}/decide (her app tap).
push: vakil_card -> ("Vakil: aapki haan chahiye", "{say}")      (push only while data.card.status == "waiting"; the same kind is re-published after her decision: no push then)
push: vakil_alert -> ("Court diary", "{say}")
push: vakil_day -> ("Aaj ki court diary", "{say}")
  (vakil_draft: no push, publish only)
worker: app.vakil.service.tick   (call every minute, e.g. `await asyncio.to_thread(vakil.service.tick)`; limitation reminders once per window of her remind_days (default 30/15/7/3/1/0 + once after the last date), a matter whose next date passed without an update once, morning note once a day at her morning_time when there is something)
prompt: VAKIL (lawyer's junior): case diary / tareekh / cause list / limitation / drafts -> `vakil` (`vakil_dekho` to read). Case status or cause list text she copied from the eCourts app / court site -> `vakil action=status|cause_list` with her exact text (never scrape, never guess a next date). Limitation is "andaaza, vakil se pakka": only the starter table or the period her advocate gave. Never invent sections, case law, dates or fees ("[citation chahiye]"). Filing, any message / notice to a client or the other side, and fee requests become a card for her tap: say "card bheja hai", never "file kar diya / bhej diya". Hoola is not a lawyer and gives no legal advice.
persona: Court ki tareekh / limitation bolte waqt "andaaza hai, vakil sahab se pakka kijiye" kaho; filing, client ko message ya fee maangne ke liye "aapki haan ka card bheja hai" kaho; kabhi kanooni salah mat do.
flutter: VakilScreen in lib/ui/vakil_screen.dart ; profile tile title "<name> · Lawyer's junior" subtitle "Court diary, tareekhein, cause list, limitation, drafts, fee hisaab" icon Icons.gavel_rounded ; cards: vakil_card -> VakilCardCard (also in calls: yes; one card per data['card']['id'], updated in place; widget takes data {'card': {...}}) ; vakil_draft -> VakilDraftCard (also in calls: no; key data['draft']['id']) ; vakil_alert -> VakilNoteCard (also in calls: no) ; vakil_day -> VakilNoteCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)`, `Native.openExternal`, `Native.approveKeySign`, `ApiException`.
features: vakil
env: none
requirements: none (uses openpyxl, python-docx, reportlab already present)
android: none
neighbours: legalres (statutes / judgments research with citations: vakil never cites; a synopsis's case-law words become "[citation chahiye]"), contracts (clause review / redlines), notary (affidavits, stamp duty from her rates), compliance, cosec, dpo, pidesk; existing lekhak (notice reply drafts + signing on her tap), operator (Computer Operator opens efiling.ecourts.gov.in after her filing tap; she does login / OTP / court fee / eSign / Submit), approvekey (fee cards: kind "vakil" on approvekey's own table via POST /api/vakil/cards/{id}/challenge, verified with approvekey._check; no allow-list change needed), idvault (client IDs only as {id:...}), chatfiles / officegen / indicpdf.
claude_md: |
  ## v0.1xx Vakil Sahayak: Hoola as a lawyer's junior ("Lawyer's junior" on the Employee page; Kanoon suite)
  - Owner's spec: keeps the case diary (clients, matters, court, CNR, next date, stage), tracks hearing dates and cause lists,
    computes limitation / appeal deadlines (Limitation Act 1963 with her inputs, always "andaaza, vakil se pakka"), prepares
    drafts for the advocate (adjournment application, vakalatnama checklist, list of dates & events, synopsis, notice reply via
    Lekhak), document checklist per matter, client update message drafts, fees ledger (never collects money). Waits for her Haan
    on: any filing, any letter / notice / message to a client or the opposite party, any fee request.
  - Server `server/app/vakil/{rules,models,service,api}.py`, tools `vakil` / `vakil_dekho` (`agent/vakil_tools.py`, chat + calls),
    duty `legal_junior`, role `lawyer_junior`, preset `law_office`, API `/api/vakil/*`, app Profile > "<name> · Lawyer's junior"
    (`lib/ui/vakil_screen.dart`: Aaj / Matters / Limitation / eCourts / Niyam + `VakilMatterPage`), cards VakilCardCard
    (`vakil_card`, also in calls), VakilDraftCard (`vakil_draft`), VakilNoteCard (`vakil_alert`, `vakil_day`). Tests
    `server/tests/test_law_vakil.py` (6).
  - Diary: clients C-001 (phone, email, address, kind; ID only as a Pehchaan Locker {id:...}; no_messages), matters M-0001 (title
    "X vs Y", 14 kinds, side, opposite + their advocate / contact, court, court hall, case "RCS 123/2024" -> type / no / year +
    case key, CNR checked as 16 chars = state 2 letters + district 2 letters + establishment 2 digits + case 6 + year 4, one CNR per
    matter, filing no, acts as SHE gives them, stage, next date + purpose, status draft / pending / disposed / closed), hearings
    (what she / the clerk says happened; a next date only when given, never before the hearing), list of dates & events, per-kind
    document checklist (common: vakalatnama, client ID reference, address for service, brief; + plaint / court-fee valuation /
    notice for suits, FIR / chargesheet / BSA 63 certificate for criminal, cheque + return memo + notice for NI 138, judgment
    certified copy + its dates for appeals ...) with have / missing / na + her file.
  - eCourts, official routes only: no public API exists for third parties; the "eCourts APIs" sold by private firms (Surepass,
    Attestr, Apify) scrape the site and are not used. She opens the eCourts Services app 4.0 / services.ecourts.gov.in / her High
    Court site (or SMS "ECOURTS <CNR>" to 9766899899), copies the Case Status or the cause list and pastes it; `status_paste` reads
    the key: value lines (CNR, case type, filing / registration no, next hearing date "15th November 2026", stage, court number and
    judge, decision date, status, history rows) and updates the diary with exactly what it says (CNR mismatch = refused, history
    not doubled, decided -> disposed + offer to compute appeal limitation). `cause_list` reads item no + case no/year + parties,
    matches her matters by case key, number+year with the party names, sets the listed date, and names her matters that the diary
    had on that date but the list doesn't show (other court hall?).
  - Limitation (`rules.limitation`): starter table of 19 Schedule articles read from the bare text (19, 21, 54, 55, 58, 65, 113,
    114(a), 115(b)(i)/(ii), 116(a)/(b), 117, 118, 123, 124, 131, 136, 137) + her advocate's own period (n + unit) for anything else;
    NI Act 138 / Consumer / Arbitration s.34 / SLP / written statement periods are NOT built in (asked). Arithmetic: s.12(1) start
    day excluded; months / years to the same calendar day (clipped to month end); s.12(2) certified-copy time (applied -> ready)
    excluded for appeals / applications only when applied within limitation; s.4 a last date on a day the court is closed (her
    closed weekdays, default Sunday, + her court holidays / vacation dates) moves to the next open day; s.5 note (condonation is
    the court's discretion, not for suits). Saved per matter, reminders at her windows.
  - Drafts (Word via officegen, every one "DRAFT, vakil se pakka", blanks "[... chahiye]"): adjournment application (court, case,
    CNR, listed date + purpose, her reason, prayer, place, advocate + enrolment no), vakalatnama checklist (welfare stamp / court
    fee amounts are hers; company = board resolution), list of dates & events (refused when nothing is written), synopsis (model
    from the matter's facts only; any number / date not in the facts becomes [?], AIR / SCC / SCR / INSC citations become
    "[citation chahiye]"; no model = a plain template), notice reply through Lekhak (`write_letter` kind reply; signing stays on
    Lekhak's own tap), brief note.
  - Her tap, in code: cards VK-0001 (filing / message / fee) with a sha256 hash of the body + what it depends on (client phone,
    no_messages, documents, matter title / case); the same pending ask is never made twice; a change after the card = stale. ONLY
    `POST /api/vakil/cards/{id}/decide {yes, hash, proof}` (by_tap) decides. Message: client update made from the diary (last
    hearing, next date) or her text; to the opposite party only her / the advocate's text; blanks refuse; another client's name or
    matter number in the text = refused (privilege); yes -> wa.me / SMS / mailto links she sends, "Bhej diya" logs it. Filing:
    what, files, missing documents, open limitation dates, eFiling steps (efiling.ecourts.gov.in: her login / OTP, court fee via
    ePay / e-stamp by her, eSign by her, Submit by her); optional Computer Operator opens the portal after her yes with "do NOT
    pay / eSign / Submit"; "File ho gaya" + efiling number into the diary. Fee: her amount only; yes needs her fingerprint once a
    phone key is active (428 -> `/cards/{id}/challenge`, approvekey kind "vakil") -> fee note PDF (not a tax invoice; GST for
    advocates' services to business clients is reverse charge: CA confirms) + WhatsApp / UPI link to her UPI ID she sends; fee
    received only by her word (owner-only ledger entry). Hoola never collects or pays.
  - Morning note at her time: today's and tomorrow's dates, limitation within 15 days, matters whose date passed without an update,
    cards waiting. DPDP `forget` of a client only after all their matters are closed / disposed (name -> "Purana client C-001",
    contact / ID ref / events / documents / card bodies cleared, fee numbers kept). Diary Excel (matters, limitation, fees).
  - Never: legal advice, inventing sections / citations / dates / fees, scraping eCourts or bypassing its CAPTCHA, filing or sending
    without her tap, sharing one client's data with another, storing Aadhaar / PAN / OTP.
  - Research (23 Oct 2026): Limitation Act 1963 Schedule as printed at advocatetanmoy.com/period-of-limitation-under-the-limitation-act-1963/
    (Art. 115 still says "Code of Criminal Procedure 1898"; India Code PDF indiacode.nic.in a1963-36 is robots-blocked for us);
    eCourts Services Mobile App 4.0 manual (tshc.gov.in/documents/admin_2026_05_25T13_31_22.pdf: CNR search, case status by
    case / filing / party / advocate / FIR, cause list, orders); MP High Court eCourts page (mphc.gov.in/php/hc/front/ECOURTS.html:
    SMS "ECOURTS <CNR>" to 9766899899, SMS / email alerts at every stage, e-filing, digitally signed certified copies); private
    "eCourts CNR APIs" (surepass.io/ecourt-cnr-search-api, attestr.developerhub.io, apify.com parseforge) checked and rejected as
    unofficial. BNS / BNSS / BSA (in force 1 Jul 2024) are only "acts" text she types; section mapping belongs to the legal
    researcher Sahayak.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/vakil_screen.dart (Dart 3 records in `for (final (k, l) in const [...])` and `.indexed`). Real eCourts app / High Court case-status and cause-list text varies by court (only the common key: value layout and "N. TYPE/NO/YEAR parties" lines were tested); court-specific layouts may need more patterns. The Limitation Act table comes from a secondary print of the bare act (India Code PDF blocked by robots), not the official gazette text; Article 115/114 still name the 1898 / 1973 CrPC (BNSS 2023 now). Court holidays / vacations are not known to Hoola (her closed_dates; second / fourth Saturdays only if she sets them). Lekhak notice-reply path tested with a stub only. Computer Operator start after a filing tap tested with a stub; the eFiling portal's own steps (advocate registration, OTP, eSign) were not tried. Fingerprint flow tested with approvekey patched, not a real phone. Push titles are suggestions for push.PUSH_KINDS.
