# WIRING for cosec
summary: Cosec Sahayak (company secretary: company / LLP master with DIN-only directors, MCA21 V3 forms calendar computed from her FY / AGM / event dates with additional-fee starters, Board / AGM / EGM notices with SS-1 / s.101 clear days checked, attendance + quorum, resolutions register, minutes, statutory registers Excel, event filings DIR-12 / PAS-3 / INC-22 / CHG-1 / MGT-14 from her words; notice, minutes sign-off and "file karo" only on her tap, filings with her fingerprint once a phone key is active; she logs in / DSC / pays on MCA herself)
db: app.cosec.models
router: app.cosec.api            (make_router(require_key, current_tenant); all routes under /api/cosec, key-protected; no public routes)
tools: app.agent.cosec_tools     (COSEC_TOOLS / COSEC_LABELS / COSEC_HANDLERS) ; voice: yes (cosec, cosec_dekho) - or put both in voice.VOICE_VIA_KAAM (business Sahayak: v0.149 rule), cosec_dekho may stay declared for "kab tak?" questions
employee: duty cosec_work = [cosec, cosec_dekho, file_read] {label "Company secretary", say "company / LLP ke MCA forms ki tareekhein, Board / AGM notice aur minutes, registers, director / share / office badlav ki filing (notice, minutes aur filing aapki haan se; MCA par login / DSC / fee aap khud)"} ; role company_secretary {label "Company secretary", duties [cosec_work, records, reminders]} ; preset cs_practice {label "CS firm / company secretarial", role company_secretary, rules ["Koi notice / minutes / MCA filing owner ki haan ke card ke bina nahi", "Director ka sirf DIN; Aadhaar / PAN sirf Pehchaan Locker reference", "Ek client company ki baat doosre client ko kabhi nahi", "Har output draft: CS / vakil / CA se pakka"]} ; READ tools: [cosec_dekho]
  - staff (staff:<id>) may add companies / people, run the calendar, note events, make meetings, notice / minutes / filing CARDS; owner-only: settings, filed (SRN), skip, forget, entity status closed / struck_off. Customers (customer:*) refused. Cards are decided ONLY by POST /api/cosec/meetings/{id}/notice/decide, /meetings/{id}/minutes/decide, /filings/{id}/decide (her app tap; by_tap=True only there).
push: cosec_filing -> ("MCA filing: aapki haan chahiye", "{say}")    (only when data['filing']['status'] == 'waiting')
push: cosec_notice -> ("Meeting notice: aapki haan chahiye", "{say}")    (only when data['meeting']['status'] == 'notice_waiting')
push: cosec_minutes -> ("Minutes: aapki haan chahiye", "{say}")    (only when data['meeting']['status'] == 'minutes_waiting')
push: cosec_alert -> ("Company filing yaad", "{say}")
push: cosec_day -> ("Aaj ka company secretary note", "{say}")
  (cosec_event: no push, info card only)
worker: app.cosec.service.tick   (call every minute, e.g. `await asyncio.to_thread(cosec.service.tick)`; reminders once per window of her days (default 30/15/7/1/0) and once a week while overdue; at her morning time it refreshes this + next FY's calendars (`ensure`) and posts the morning note when there is something)
prompt: COMPANY SECRETARY: for a client company / LLP use `cosec` (entity master by CIN / LLPIN, directors by DIN only - never take Aadhaar / PAN, only a Pehchaan Locker {id:...}). Her words like "naya director", "istifa", "shares allot", "office shift", "bank loan" -> `cosec action=event words=<her words> on=<date>`; due dates are worked out by code (say "andaaza" when it says est). Meeting notice / minutes / MCA filing = a card she taps: say "aapki haan ka card bheja hai", never "notice gaya" or "file ho gaya"; MCA login, DSC, OTP and fee are hers. Everything is draft / jaankari - CS / vakil / CA se pakka; never invent a date, fee or section.
persona: Company ke kaam mein tareekh sirf unki batayi tareekh se; notice / minutes / MCA filing ke liye "aapki haan ka card bheja hai" kaho, kabhi "file ho gaya" nahi; director ka sirf DIN.
flutter: CosecScreen in lib/ui/cosec_screen.dart ; profile tile title "<name> · Company secretary" subtitle "MCA forms ki tareekhein, Board / AGM notice + minutes, registers" icon Icons.apartment_rounded ; cards: cosec_filing -> CosecFilingCard (also in calls: yes; one card per data['filing']['id'], updated in place) ; cosec_notice -> CosecMeetingCard (also in calls: yes; key by data['meeting']['id']) ; cosec_minutes -> CosecMeetingCard (also in calls: yes; same key as cosec_notice, replaces it) ; cosec_alert / cosec_day / cosec_event -> CosecNoteCard (also in calls: no). All widgets take (app:, data:) (Filing / Meeting cards also an optional onDone) and use only `app.api!.call(...)`, `Native.openExternal(url:)` and `Native.approveKeySign` (fingerprint, like ArchInvoiceCard).
features: cosec
env: none
requirements: none (openpyxl + python-docx via app.officegen, already present)
android: none
claude_md: |
  ## v0.1xx Cosec Sahayak: Hoola as a company secretary's desk ("Company secretary" on the Employee page; Kanoon suite)
  - Owner's spec: company / LLP master (CIN / LLPIN, FY, directors with DIN only, auditor, class private / OPC / small / public /
    listed / Section 8 / LLP) -> MCA21 V3 forms calendar computed by code from AGM / FY / event dates with additional-fee starters ->
    Board meeting / AGM: notice drafts with SS-1 / SS-2 notice periods checked, agenda, attendance + quorum, minutes drafts,
    resolutions register -> statutory registers (members MGT-1 style, directors & KMP, charges) as Excel -> event filings from her
    words (DIR-12, PAS-3, INC-22, CHG-1, MGT-14 ...). Filing on MCA = card on her tap + steps; she logs in / DSC / pays.
  - Server `server/app/cosec/{rules,models,service,api}.py`, tools `cosec` / `cosec_dekho` (`agent/cosec_tools.py`, chat + calls),
    duty `cosec_work`, role `company_secretary`, preset `cs_practice`, API `/api/cosec/*`, app Profile > "<name> · Company secretary"
    (`lib/ui/cosec_screen.dart`: Aaj / Companies / Filings / Niyam; `CosecEntityPage`: Jaankari / Log / Filings / Meetings), cards
    CosecFilingCard (`cosec_filing`, fingerprint), CosecMeetingCard (`cosec_notice` / `cosec_minutes`), CosecNoteCard
    (`cosec_alert` / `cosec_day` / `cosec_event`). Tests `server/tests/test_law_cosec.py` (7).
  - Master: E-001, kind, CIN (21-char pattern) / LLPIN (AAA-1234), ROC, incorporation, paid-up / turnover in her words ("25 lakh",
    "3 crore") -> small company worked out (private only, not holding / subsidiary / Section 8: <= Rs 10 crore AND <= Rs 100 crore
    from 1 Dec 2025; unknown = asked), auditor (name, FRN, term to which FY's AGM), flags deposits (DPT-3, default on), msme_dues
    (MSME-1), dormant / startup (light board rule), first_fy. People: director / partner / KMP by DIN / DPIN (8 digits) only, KYC
    date; Aadhaar / PAN refused, only a Pehchaan Locker {id:...}; members with folio, shares, class, movement history.
  - Calendar (`rules.annual`, upserted per entity + form + period, her status kept): AGM by FY end + 6 months (first AGM 9
    months, never more than 15 months after the last; OPC none); AOC-4 = AGM + 30 (OPC: FY end + 180), MGT-7 / MGT-7A (small / OPC)
    = AGM + 60, both "andaaza" until the AGM is recorded as held (then real dates), MGT-8 note above Rs 10 crore / Rs 50 crore /
    listed; ADT-1 = AGM + 15 when the auditor's term ends at that AGM; DPT-3 30 June; MSME-1 30 April / 31 October; DIR-3 KYC per
    director (filed before 31 Mar 2026 -> 30 June 2028; later = 30 June after the third FY, marked andaaza); LLP Form 11 30 May,
    Form 8 30 October. A flag turned off makes its pending rows "not needed". Additional fee: AOC-4 / MGT-7 / 7A Rs 100 a day (no
    cap), other forms the slab multiple of the normal fee (1x / 2x / 4x / 6x / 10x / 12x; rupees only when she gives the normal
    fee), LLP Rs 100 a day, KYC: DIN deactivated + Rs 5,000; s.164(2) warning after a year of non-filing.
  - Events (`event`, words guessed in Hinglish: naya director, istifa, shares allot, office shift, bank loan, BEN-1 ...):
    director_appoint / resign -> DIR-12 30 days (+ minimum-directors warning), allotment -> PAS-3 30 days + members register
    (folios), transfer -> register only + SH-4 stamp note, registered office same city -> INC-22, other city -> MGT-14 + INC-22,
    other state -> INC-23 (RD, vakil / CS), charge -> CHG-1 / CHG-4 + charges register, BEN-2, ADT-1 / ADT-3, special resolution ->
    MGT-14, incorporation -> INC-20A 180 days + first auditor + first Board meeting 30 days, LLP partner -> Form 4. A due date already
    passed is said with the fee.
  - Meetings BM / AGM / EGM / CM-001: starter agenda (her items replace it), notice text by code (formal English, proxy / s.102
    notes for general meetings, VC wording) -> `cosec_notice` card: SS-1 board 7 / s.101 general meeting 21 CLEAR days (post /
    courier +2 days, Rule 35(6)), latest send date shown, shorter notice only with her consent flag, blanks ([samay] / [jagah] /
    CIN / registered office) block; her tap -> Word notice + email / WhatsApp drafts she sends. Attendance only after the notice went
    -> quorum (board 1/3 or 2, interested directors excluded except private; general meeting private 2 / public 5-15-30 by members);
    AGM held -> last_agm + real calendar dates. Resolutions R-YYYY/001 only in a held meeting with quorum (board in Board, ordinary
    / special in general meetings, circular without a meeting); special needs for >= 3x against (s.114(2)) -> MGT-14; Board ones on
    her mgt14 flag. Minutes draft from attendance + agenda + resolutions with [..] blanks, SS-1 deadlines (draft 15 days, comments 7,
    sign 30) -> `cosec_minutes` card (blanks block) -> her tap -> Word minutes, locked. Board frequency (4 a year, gap <= 120 days;
    OPC / small / dormant / startup one each half with >= 90 days; single-director OPC exempt) shown with the next Board-by date.
  - Filing card (`cosec_filing`, hash of everything shown; stale -> back to todo): blockers (CIN / LLPIN, a signer's DIN, AGM not
    held for AOC-4 / MGT-7, auditor missing, new director's DIN, allottees, meeting-only items, INC-23) + checks (days late + fee,
    s.164(2), MGT-8, andaaza basis) + generic MCA V3 steps (login, form, prefill, attachments, DSC, submit, pay, SRN). ONLY `POST
    /api/cosec/filings/{id}/decide {yes, hash, proof}` approves; fingerprint once a phone key is active (approvekey message kind
    "cosec", own `/challenge` route); then "Ho gaya" (owner) with SRN, date, fee -> late days + fee said. "Zaroori nahi" needs a reason.
  - Registers Excel (Members MGT-1 style, Directors & KMP, Charges, Resolutions, Meetings, Filings) as her file. DPDP `forget`
    (owner) only after the entity is closed / struck off: names / contacts / DINs / locker refs blanked, notice / minutes texts and
    attendance dropped, dates kept. Morning note: overdue, her cards, 30 days, notices to send in 3 days, minutes to sign, next Board.
  - Never: logging in to MCA V3, DSC, paying a fee, sending a notice / minutes, inventing a date / fee / section, Aadhaar / PAN, one
    client's data to another. Listed companies: SEBI LODR filings are not built (Hoola says so; CS's own calendar).
  - Sources (checked 23 Oct 2026): taxguru.in "DIN KYC for Directors: New Due Dates After March 2026" (G.S.R. 943(E) 31 Dec 2025,
    from 31 Mar 2026, once in 3 FYs by 30 June, next 30 June 2028, change within 30 days, Rs 5,000 to restore a DIN);
    icai.org CLCGC note 2 Jan 2026 (same amendment); taxguru.in ROC calendar (7 Sep 2026: AOC-4 30 / MGT-7 60 days of AGM, ADT-1 15
    days, DPT-3 30 June, MSME-1 30 Apr / 31 Oct, Rs 100 a day, small company Rs 10 crore / Rs 100 crore from 1 Dec 2025, MGT-8
    Rs 10 crore / Rs 50 crore); taxmann.com compliance calendars (upd. 21 Nov 2024: INC-20A 180 days s.10A, INC-22 s.12, BEN-2 s.90(4),
    DIR-12 30 days, MGT-14 s.117, ADT-3 s.140, first auditor s.139(6), MSME-1 order 22 Jan 2019); calcguru.in ROC late fee (Aug 2026:
    slab multiples 1/2/4/6/10/12, Rs 100 a day for AOC-4 / MGT-7 no cap, s.164(2)); tallysolutions.com LLP Form 11 guide (7 Apr 2026:
    30 May / 30 Oct, Rs 100 a day); taxguru.in SS-1 notes (7 days notice, quorum 1/3 or 2, 4 meetings / 120 days, draft minutes 15 days,
    comments 7, entry 30 days); mondaq.com 12 Mar 2024 + ICSI announcement 13 Feb 2024 (revised SS-1 / SS-2 from 1 Apr 2024: startups
    one meeting each half / 90 days, private interested director in quorum, 95% shorter-notice consent); Companies Act 2013 ss.96,
    101, 103, 114, 118, 137, 173, 174 (India Code). Reminder windows and the 3-day notice warning are starters, not rules.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/cosec_screen.dart (Dart 3 records in `for (final (k, _) in fields)`, `.indexed`, switch expressions). No MCA V3 call exists or was attempted (no public API; she files herself); the steps text is generic and MCA screens change. The OPC MGT-7A due date (30 Sep + 60 days) and the DIR-3 KYC due date for directors who file after 31 Mar 2026 are marked "andaaza" because the sources were not explicit. Additional-fee slabs come from a secondary source (calcguru.in, Aug 2026), not the gazette text; the normal fee table (by nominal capital) is not built, so rupees show only when she gives the normal fee. LLP Form 8 Rs 100 a day assumed same as Form 11 (LLP (Amendment) Rules 2022). Shorter-notice consent thresholds are stated in plain words, not checked against shareholding. Fingerprint path tested with approvekey patched (same as Archassist), not on a real phone. Push titles are suggestions for push.PUSH_KINDS.
  neighbours (Kanoon suite): compliance (statutory calendar across labour / GST / TDS / licences — cosec owns only MCA / ROC), contracts (agreements), notary (SH-4 / affidavits stamping), legalres, vakil, dpo (DPDP), pidesk; existing: lekhak (letters), docdesk, gyaan, idvault, approvekey, officegen, gstp / payroll / audit (CA side), operator (Computer Operator could open the MCA form under her control — not wired here on purpose).
