# WIRING for notary
summary: Notary Sahayak (notary public / documentation desk: affidavits, declarations, POA, indemnity, NOC, rent summary drafted by code in English / Hindi / Marathi from the party's facts with [blanks] for anything missing, stamp value only from her state rate table, executants' IDs only as Pehchaan Locker references, final print only on her tap, Form XV notarial register + fee receipts with Rule 10 caps, Excel register + annual-return counts, renewal reminders, apostille / MEA attestation steps; notarising / signing / sealing / e-stamping are hers)
db: app.notary.models
router: app.notary.api            (make_router(require_key, current_tenant); all routes under /api/notary, key-protected; no public routes)
tools: app.agent.notary_tools     (NOTARY_TOOLS / NOTARY_LABELS / NOTARY_HANDLERS) ; voice: yes (notary, notary_dekho)
employee: duty notary_work = [notary, notary_dekho, file_read, id_locker] {label "Notary & documentation", say "affidavit / declaration / POA / indemnity / NOC ke draft party ke facts se, stamp sirf aapki rate table se, register + receipt, apostille steps (final print aapki haan se; notarise aapka kaam)"} ; role notary_desk {label "Notary & documentation", duties [notary_work, records, reminders, customers]} ; preset notary {label "Notary / documentation / typing centre", role notary_desk, rules ["Final print sirf owner ke tap se", "Stamp ki rakam sirf owner ki rate table se, warna khaali", "Aadhaar / PAN sirf Pehchaan Locker reference", "Register line sirf jab notary ne khud notarise kar diya"]} ; READ tools: [notary_dekho]
  - staff (staff:<id>) may draft / update / copy / translate / stamp ref / print REQUEST / apostille. Owner only (tool refuses others): notarise, correct, receipt, register_file, settings, stamp_rate, fee, forget, and notary_dekho what=register. Customer actors refused entirely. The final print is never decided by any tool: only POST /api/notary/docs/{id}/decide (her app tap, hash-checked).
push: notary_print -> ("Notary: final print ke liye aapki haan", "{say}")   (only while doc.status == "waiting")
push: notary_alert -> ("Notary: yaad dilana", "{say}")
push: notary_day -> ("Aaj ka notary desk", "{say}")
  (notary_doc and notary_entry: no push; notary_doc updates in place per doc id, notary_entry is a record)
worker: app.notary.service.tick   (call every minute, e.g. `await asyncio.to_thread(notary.service.tick)`; renewal of the certificate of practice at 210 / 180 / 90 / 30 / 0 days once each, annual return (Form XIV, Rule 14) once in the first week of January, morning note once a day at her morning_time when there is something)
prompt: NOTARY: affidavit / declaration / power of attorney / indemnity / NOC / rent summary -> `notary action=draft` with the party's facts (or her exact words); never invent a fact, date, fee or stamp amount (missing = [blank], stamp only from her rate table). Aadhaar / PAN only as id_ref / id_number (goes into the locker). Final print = `action=print` makes a card: say "aapki haan ka card bheja hai", never "print ho gaya". Register line (`action=notarise`) only after SHE says she notarised it. Everything is a draft, not legal advice.
persona: Notary ke kaagaz par: facts poochho, khaali cheez kabhi khud mat bharo, stamp ki rakam sirf unki table se; final print ke liye "aapki haan ka card bheja hai"; notarise / sign / seal unka kaam.
flutter: NotaryScreen in lib/ui/notary_screen.dart ; profile tile title "<name> · Notary desk" subtitle "Affidavit, POA, NOC ke draft, stamp, register, receipt, apostille" icon Icons.gavel_rounded ; cards: notary_print -> NotaryPrintCard (also in calls: yes; key by data['doc']['id'], updated in place) ; notary_doc -> NotaryDocCard (also in calls: no; key by data['doc']['id'], updated in place; a later notary_print for the same doc id replaces it) ; notary_entry -> NotaryEntryCard (also in calls: no) ; notary_alert -> NotaryNoteCard (also in calls: yes) ; notary_day -> NotaryNoteCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)`.
features: notary
env: none
requirements: none (reportlab, python-docx, openpyxl already present)
android: none
claude_md: |
  ## v0.1xx Notary Sahayak: Hoola as a notary public's / documentation desk's coworker ("Notary & documentation" on the Employee page)
  - Owner's spec: documents drafted from the party's facts (affidavits: name change, address, gap year, income, lost document,
    general; declarations; self-declarations; rent / leave & licence summary from Rentdesk; general / special power of attorney;
    indemnity bond; NOC) in English / Hindi / Marathi -> stamp value only from HER state rate table (blank if missing) + e-stamp
    steps -> executants' identity only as Pehchaan Locker references -> notarial register (Form XV) as Excel -> fee receipts (she
    collects; Hoola never moves money) -> apostille / MEA attestation checklist. Notarising / signing / sealing is HER act; final
    print = her tap. Nothing is legal advice ("Draft / jaankari, vakil se pakka karwaiye" on every document).
  - Server `server/app/notary/{rules,models,service,api}.py`, tools `notary` / `notary_dekho` (`agent/notary_tools.py`, chat +
    calls), duty `notary_work`, role `notary_desk`, preset `notary`, API `/api/notary/*`, app Profile > "<name> · Notary desk"
    (`lib/ui/notary_screen.dart`: Aaj / Documents / Register / Apostille / Niyam + `NotaryDocPage`), cards NotaryPrintCard
    (`notary_print`, her tap), NotaryDocCard (`notary_doc`), NotaryEntryCard (`notary_entry`), NotaryNoteCard (`notary_alert`,
    `notary_day`). Tests `server/tests/test_law_notary.py` (8).
  - Documents ND-0001 (`rules.KINDS`, 13 kinds): fixed templates written by CODE per language (intro "I, ..., S/o / D/o / W/o ...,
    aged ..., residing at ... solemnly affirm" / "मैं ... सत्यनिष्ठा से प्रतिज्ञान करता/करती हूँ" / "मी ... सत्यप्रतिज्ञेवर लिहून
    देतो/देते", numbered paragraphs, verification with place / date left for hand-filling, deponent / declarant / principal +
    witnesses); Hindi / Marathi verbs follow the party's gender; money in figures + words (en / hi; Marathi figures only).
    A missing required fact = "[____ label]" and listed; optional lines with no fact are left out. Her words can fill the form:
    the model (net.ai.llm, optional) may only copy values that appear in her words (an invented value is dropped). Aadhaar / PAN
    in her words or the party form go straight into the Pehchaan Locker (`idvault.save` / `capture`, person "party"); the
    document keeps only {id:...} + masked. Her own text (`text`) replaces the template; `copy` (other en/hi/mr version),
    `translate` (other languages via Lekhak, "Draft translation - not certified"; verifying a translation is her Rule 10(1)(j) act).
    Rent summary from a Rentdesk tenancy (`rentdesk` action; the agreement itself stays in Rentdesk).
  - Stamp: `stamp_rates` {state: {kind: amount | {amount, mode}}} typed by her from her state's official schedule; no row =
    amount None = "[stamp ₹ ?]" and the print is blocked; 0 = plain paper. Modes e-stamp (SHCIL), e-SBTR / GRAS (Maharashtra),
    Kaveri (Karnataka), franking, paper; steps for her / the party (names must match the document; verify UIN on
    shcilestamp.com); the UIN / e-SBTR / franking number she gives goes into the register's "stamp affixed" column.
  - Final print = her tap, in code: `print_request` (blocks: blanks, stamp unknown, no party) -> `notary_print` card with
    sha256 of text + parties (masked) + stamp; ONLY `POST /api/notary/docs/{id}/decide {yes, hash}` (by_tap) makes the final PDF +
    Word without the DRAFT mark; any change after the card (facts, party, stamp no., text) puts it back to draft and the old hash
    does nothing. Drafts always carry a DRAFT watermark. Final documents are locked (copy to change). Hindi / Marathi PDFs go
    through `indicpdf.blocks_pdf` (Chromium, shaped), ReportLab fallback.
  - Register (notary mode): `notarise` (owner only, after SHE notarised it; doc must be final) writes a Form XV line (serial per
    year 2026/0001, date + time, act, executants' names + full address (required), contents, stamp affixed, fee, receipt no.;
    masked IDs as an extra column) and a fee receipt NR/2627/0001 (Rule 11(9)) with notarial fee + desk charges (typing / xerox /
    drafting, her rates) as separate lines. Notarial fee above the Rule 10(1) cap is refused (affidavit / attest Rs 35, outside-India
    Rs 200, translation Rs 100, true copy Rs 10 a page min Rs 20; 2014 table; she can update caps after a new notification).
    Lines are never edited: `correct` = a new line "Correction of 2026/0001". Excel (Form XV, fee register, yearly counts for the
    Form XIV annual return, about sheet). Desk mode (typing / documentation centre): no register; `executed` notes which notary did it;
    receipts only for desk charges.
  - Apostille / attestation A-001: steps by document type (notarise for affidavit / POA, State / UT designated authority (RAC) or
    Chamber of Commerce first, Hague member? -> MEA apostille via MEA's outsourced agencies (MEA fee Rs 50 / sticker + agency Rs 84 /
    document + Rs 3 / page, as on MEA's page) or MEA attestation + embassy legalisation), ticked by her; "Hague member?" is asked,
    never guessed.
  - Reminders (`tick`): certificate of practice renewal (5 years, Form XVI 6 months before expiry) at 210 / 180 / 90 / 30 / 0 days;
    annual return Form XIV in the first week of January with last year's count; morning note (print cards waiting, drafts with
    blanks, final docs not notarised 7+ days, open apostille cases). DPDP `forget` (doc): party details + its locker IDs erased;
    register lines stay (Rule 11 requires the register).
  - Never: notarising / signing / sealing / e-stamping for her, inventing facts / stamp / fee / dates, keeping an ID number outside the
    locker, taking or paying money, legal advice.
  - Research (23 Oct 2026): Notaries Act 1952 + Notaries Rules 1956 as published by the Department of Legal Affairs
    (legalaffairs.gov.in/sites/default/files/notaries-rules-1956.pdf): Rule 10(1) fee table (2014) + Rule 10(2) display of rates,
    Rule 11(2) Notarial Register Form XV (serial, date, act, executant with full address, contents, stamp affixed, fee, receipt
    book serial, signatures), 11(4) title page with page count, 11(5) inspection, 11(6) entries in the instrument's language or
    English, 11(9) fee receipt + fee register, Rule 12 seal, Rule 14 annual return Form XIV in the first week of January (online),
    Rule 8(4) certificate valid 5 years, Rule 8B renewal Form XVI before six months of expiry; compass.rauias.com (5 Sep 2024): the
    Ministry's Notary Portal (renewal / annual returns "in due course"); mea.gov.in/apostille-menu: Hague Convention since 2005,
    RAC / Chamber of Commerce first, fees, outsourced agencies, no photocopies, no direct submission; sansalegal.com (9 Aug 2026):
    SHCIL e-stamp in ~25 states / UTs, Maharashtra e-SBTR, Karnataka Kaveri, UIN / QR verification, execution within 6 months
    (state rules differ). Stamp duty itself differs by state and changes (e.g. Maharashtra amendments): only her table is used.
  - Neighbours (Kanoon suite): vakil (case drafts), contracts (contract review, e-sign / stamping steps for agreements), legalres,
    cosec, compliance, pidesk, dpo; reuses rentdesk (tenancy facts), lekhak (other-language translation), idvault, chatfiles,
    officegen, indicpdf, india.money.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/notary_screen.dart (Dart 3 records in `_form` field lists and collection-for, switch expressions). Hindi / Marathi PDFs were tested only through the ReportLab fallback (tests stub indicpdf._chromium); the Chromium path is the shared indicpdf one. Template wording (especially Hindi / Marathi legal phrasing) was written here, not reviewed by an advocate: it is labelled draft everywhere. The Rule 10 fee table is the 2014 table as published on legalaffairs.gov.in; a newer notification may exist (caps are editable in Niyam). The model-based fact extraction was tested only with a stub. MEA agency names / fees are as shown on MEA's page on 23 Oct 2026 and must be re-checked there. Rentdesk link tested with a stubbed tenancy_view. No portal (SHCIL / GRAS / Notary Portal / MEA) is called: steps only.
