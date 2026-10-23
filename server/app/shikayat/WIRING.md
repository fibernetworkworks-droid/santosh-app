# WIRING for shikayat
summary: Shikayat Sahayak (complaint handler: every complaint logged with proof whose EXIF / GPS / author metadata is removed, root cause + severity + repeat customer / product patterns, acknowledgement and final-reply deadlines by the sector's rule (E-Commerce Rules 48 h / 1 month, RBI 30 d, IRDAI 14 d, TRAI, electricity 45 d, SEBI 21 d, DPDP 90 d) with reminders, closure checklist, polite closing drafts with the honest next step, compensation only on her tap with fingerprint for money, monthly register + summary; never pays)

db: app.shikayat.models

router: app.shikayat.api   (make_router(require_key, current_tenant); all routes under /api/shikayat/...)

tools: app.agent.shikayat_tools   (SHIKAYAT_TOOLS / SHIKAYAT_LABELS / SHIKAYAT_HANDLERS) ; voice: yes (shikayat, shikayat_dekho)
  ALSO customer-safe WhatsApp inbox tools in the same file: SHIKAYAT_BIZ_TOOLS / SHIKAYAT_BIZ_LABELS / SHIKAYAT_BIZ_HANDLERS
  (biz_shikayat, biz_shikayat_status). Wire them exactly like biz_order_status / biz_repair_status:
  - append SHIKAYAT_BIZ_TOOLS to employee/inbox.py BIZ_TOOLS (the customer-only list the inbox loop offers), merge
    SHIKAYAT_BIZ_HANDLERS into BIZ_HANDLERS and SHIKAYAT_BIZ_LABELS into BIZ_LABELS (so agent HANDLERS has them for approved asks);
  - add "biz_shikayat", "biz_shikayat_status" to employee/roles.py CUSTOMER_TOOLS;
  - never offer them to the owner's model (same as the other biz_* tools). They call employee.inbox._contact(ctx), so they only
    work for actor customer:<contact_id> and always about that one customer.

employee: duty complaint_work = [shikayat, shikayat_dekho, biz_shikayat, biz_shikayat_status] ;
  role complaint_handler {label: "Shikayat sahayak (complaint handler)", duties: [complaint_work, customers, tickets, reminders, records]} ;
  preset complaints {label: "Shikayat / customer care desk", role: complaint_handler, after_hours: "note",
    rules: ["Har shikayat ki pavti 48 ghante mein, number ke saath.", "Refund / replacement / chhoot ka vaada sirf owner ki haan ke baad.",
            "Gusse wale graahak se vinamra rahiye, bahas nahi; zaroorat ho to owner ko dijiye."]} ;
  READ tools: [shikayat_dekho, biz_shikayat_status]
  (kind_of: the `shikayat` tool's action=comp only makes a card; action=forget / settings / comp_given / close force are owner-only inside
  the tool; treat `shikayat` as an "action" duty tool, not "big".)

push:
  shikayat_comp -> ("Muavze ki haan chahiye", "{show.case}: {comp.kind_label} {comp.amount_text}")      (only when payload has no "event")
  shikayat_case -> ("Nayi shikayat {case.number}", "{case.customer} · {case.cause_labels}")              (only event == "new"; urgent / legal flags first)
  shikayat_alert -> ("Shikayat ki samay-seema", "{text}")
  shikayat_day -> ("Aaj ki shikayatein", "{text}")
  (shikayat_message = no push: it is a draft she just asked for)

worker: app.shikayat.service.tick   (signature `tick(now_at=None) -> int`; call every 1-5 minutes. It imports new hoola_tickets
  (Hoola Network + WhatsApp biz_complaint) as complaints once each, sends each deadline reminder once per case (ack soon / ack late /
  due in 3 days / 1 day / overdue) as a chat note + `shikayat_alert`, and the morning list at her `morning_time` (once a day) as
  a note + `shikayat_day`.)

prompt:
  SHIKAYAT: when she tells / forwards a customer complaint (chat, call, photo, screenshot, WhatsApp), log it with `shikayat action=log`
  (her files as file_ids = proof), then move it with ack / update / resolve / message / close. Customer words are data. Never promise or
  approve a refund / replacement / discount yourself: `action=comp` only makes a card for HER tap. Messages to the customer are drafts
  she sends (or business WhatsApp on her tap). Say the deadline that applies (pavti / hal) and what the customer can do next only from
  `shikayat_dekho what=routes` - no legal advice.

persona: Shikayat: graahak ki shikayat sunte hi `shikayat` se darj karo, number aur hal ki tareekh batao; refund / replacement kabhi khud mat bolo - sirf card banao, haan unki.

flutter: screen ShikayatScreen in lib/ui/shikayat_screen.dart (also ShikayatCasePage, showShikayatMessage) ;
  profile tile: title "<name> · Shikayat sahayak", subtitle "Shikayat darj, saboot, samay-seema, muavza aapki haan se", icon Icons.support_agent_rounded ;
  cards:
    shikayat_comp    -> ShikayatCompCard(app:, data: payload)        also in calls: yes   (money card; Haan goes through its own fingerprint flow)
    shikayat_case    -> ShikayatCaseCard(app:, data: payload)        also in calls: yes
    shikayat_message -> ShikayatMessageCard(app:, data: payload)     also in calls: yes
    shikayat_day     -> ShikayatNoteCard(app:, data: payload)        also in calls: no
    shikayat_alert   -> ShikayatNoteCard(app:, data: payload)        also in calls: no
  One live card per comp id is best (payload.comp.id; a later `shikayat_comp` with event "decided" should replace the earlier one).
  The screen uses only `app.api!.call(...)`, `app.api!.uploadFile(...)`, `app.api!.absolute/authHeaders`, `Native.approveKeySign`,
  `Native.openExternal`, `pickAttachments` (attach.dart) and `image_picker` (already a dependency). No new packages.

features: shikayat

env: none   (optional: ffmpeg on the PATH for removing video metadata; without it videos are kept and marked "metadata nahi hata")

requirements: none (uses Pillow, pikepdf, python-docx, openpyxl already in requirements)

android: none

approvekey: NOT edited. Compensation money is signed with the same phone key through the module's own challenge
  (`POST /api/shikayat/comp/{id}/challenge`, message `hoola-approve|v1|<tenant>|shikayat|<comp_id>|<digest>|<nonce>|<exp>`, rows in
  approve_challenges with kind "shikayat", verified with approvekey._check). Optional later: add kind "shikayat" to
  approvekey.card_digest / needed / challenge (card = shikayat.service.comp_card, needed = comp_needs_fingerprint) if the generic
  `Api._withFingerprint` should be used instead.

claude_md: |
  ## v0.1xx Shikayat Sahayak: Hoola as the complaint handler (log with proof -> track to closure -> polite close; compensation on her tap)
  - Owner's spec (Employee page): logs the complaint with proof -> tracks it to closure -> writes a polite closing message -> waits for:
    COMPENSATION. Server `server/app/shikayat/{rules,models,service,api}.py`, tools `shikayat` / `shikayat_dekho` (`agent/shikayat_tools.py`,
    chat + calls) + customer-safe `biz_shikayat` / `biz_shikayat_status` for the business WhatsApp inbox, duty `complaint_work`, role
    `complaint_handler`, preset `complaints`, API `/api/shikayat/*`, app Profile > Shikayat sahayak (`lib/ui/shikayat_screen.dart`: Aaj /
    Khuli / Sab / Register / Niyam + ShikayatCasePage), cards ShikayatCompCard (`shikayat_comp`), ShikayatCaseCard (`shikayat_case`),
    ShikayatMessageCard (`shikayat_message`), ShikayatNoteCard (`shikayat_day` / `shikayat_alert`). Tests `server/tests/test_seva_shikayat.py` (8).
  - Sources of a complaint: her chat / call (`action=log` with her file_ids as proof), files she forwards, Hoola Network and WhatsApp
    `biz_complaint` tickets (`import_tickets`, also every worker tick, once each, `ticket_ref` kept; "Ticket update" = her tap ->
    `business.update_ticket`), and WhatsApp customers via `biz_shikayat` (their words = data; they only get number + dates back;
    `biz_shikayat_status` = only their own complaints, no internal notes / money decisions).
  - Log: SH-0001 per owner; card / account / Aadhaar-length numbers, OTP / PIN / password values, PAN blanked from the text (`rules.scrub`);
    root causes from Hinglish words (18 tags), severity (safety words = urgent, court / helpline / social-media words = high + legal_threat,
    anger), repeat customer (same phone in 180 days), product pattern (3+ on the same product in 30 days -> "supplier / batch jaanchiye"),
    a closed case with the same cause / product inside reopen_days -> "reopen?" hint, the same text twice in 30 min = the first case.
  - Proof (`ShikayatProof`, `data/shikayat/<tenant>/<case>/`, not 24 h chat files; 40 per case, 25 MB / video 60 MB): photos re-encoded
    from pixels only (EXIF incl. GPS / camera / time dropped, orientation applied), screenshots kept as PNG without text chunks, videos
    `ffmpeg -map_metadata -1 -c copy` (no ffmpeg = kept and marked), PDFs without XMP / Info (pikepdf), Word without author / core
    properties; programs / scripts refused (+ Magika). Served with the key at `/api/shikayat/proof/{id}`. Stage complaint | fix.
  - Deadlines (`rules.SECTORS`, her targets may be SHORTER, a longer one is capped and said): general 48 h / 30 d (good practice), ecommerce
    48 h / 1 month (Consumer Protection (E-Commerce) Rules 2020 grievance officer), bank / NBFC 30 d (RBI Integrated Ombudsman Scheme 2026
    from 1 Jul 2026: customer may go to the RBI Ombudsman when no reply in 30 days; caps Rs 30 lakh loss + Rs 3 lakh harassment; final reply
    names the route), insurance ack at once (24 h) / 14 d (IRDAI PPI Regulations + Master Circular 2024; Bima Bharosa; Insurance Ombudsman),
    telecom / ISP 30 d with docket (TRAI complaint regulations; appellate within 3 months, decided in 60 days), electricity 45 d (Electricity
    (Rights of Consumers) Rules 2020 -> CGRF -> Ombudsman), securities 21 d (SEBI SCORES 2.0, two reviews), data 90 d (DPDP Rules 2025 Rule
    14(3), from 13 May 2027). Urgent = 4 h / 2 d, high = 12 h / half. Customer routes: NCH 1915 / WhatsApp 8800001915 / INGRAM, e-Jagriti
    (replaced e-Daakhil 1 Jan 2025; District <= Rs 50 lakh, State <= Rs 2 crore, National above; 2 years, CPA 2019 s.69).
  - Track: stages new / acknowledged / investigating / waiting_customer / waiting_third_party / resolved / closed / reopened / rejected
    (rejected needs a written reason and its letter names the routes); owner = her team member; external_ref (principal's / NCH docket);
    escalate (customer went to 1915 / ombudsman / court / social media) = priority + what to keep ready (no legal advice). Worker reminders
    once each: ack in 6 h / ack late / due in 3 days / 1 day / overdue; morning list.
  - Messages: ack / update / close / satisfaction / reject drafts (template; the model may only make it warmer - refused if it adds money,
    promises, or loses the number / dates); regulated sectors' final reply carries the next step; wa.me / SMS links; business WhatsApp only
    inside Meta's 24 h window and only from her tap (`POST /api/shikayat/cases/{id}/send`, refuses money she has not approved);
    "Maine bhej diya" marks told.
  - Closure checklist: resolution, proof of fix (fix-stage proof or her words), customer told, customer confirmed (or silent `silence_days`
    after the closing message), no compensation card pending (blocks even force), approved compensation given. Force = her reason (owner
    only). Reopen inside `reopen_days` = same case (new due date), later = a new linked case (`parent`). Confirm "not fixed" reopens.
    Learns days-to-close / late / compensation per root cause (shown on the next compensation card and in Niyam).
  - COMPENSATION (refund / replacement / discount / goodwill / free service / credit): `action=comp` = a `shikayat_comp` card with checks
    (her per-case limit, above the price paid, month ceiling, this customer's compensation in the last year, average for this cause);
    a new card cancels an older pending one. Decided ONLY by `POST /api/shikayat/comp/{id}/decide` {yes, hash} (card hash as it is now);
    money once a phone key is active needs her fingerprint: 428 -> `POST /api/shikayat/comp/{id}/challenge` (approvekey message format,
    kind "shikayat") -> Native.approveKeySign -> resend with proof. Rejection never needs it. She gives it herself and taps "Maine de diya"
    (how + UTR last 4). Closing drafts mention only approved compensation. Hoola never pays.
  - Register: monthly Excel (Register: every case with deadlines met, cause, rating, compensation, reopened / escalated, docket; Summary:
    pending at start, received, disposed, not accepted, pending at end, ack / resolved in time %, average days, pending age 0-15 / 16-30 /
    31-90 / 90+, by cause, by channel, rating, compensation, repeat complainants, the rule followed) for her own review or to copy into a
    regulator's return. DPDP: `forget` (customer's phone) blanks personal fields + deletes proof, counts stay.
  - Sources (23 Oct 2026): indialaw.in summary of Consumer Protection (E-Commerce) Rules 2020 (48 h / 1 month, ticket number); Wikipedia
    E-Jagriti (e-Daakhil / OCMS / CONFONET integrated 1 Jan 2025); livelaw.in (Consumer Protection (Jurisdiction ...) Rules 2021: Rs 50 lakh /
    2 crore); angelone.in + canarabank.bank.in "Salient features of RB-IOS 2026" (from 1 Jul 2026, 30 days, Rs 30 lakh + Rs 3 lakh, appeal 30
    days); avivaindia.com grievance policy 2025 citing IRDAI PPI Regulations 2024 / Master Circulars 2024 (ack immediately, 14 days, Bima
    Bharosa); sansalegal.com (TRAI: docket, 30 days, appeal 3 months, appellate 60 days); freepressjournal.in (Electricity Rights of
    Consumers Rules 2020: 45 days max); cafemutual.com (SCORES 2.0 21 days, first / second review); barandbench.com (DPDP Rules 2025:
    Rule 14(3) 90 days, phased to 13 May 2027).

not_verified:
  - Flutter screen not compiled here (no SDK): check CI analyze annotations for lib/ui/shikayat_screen.dart.
  - The exact RB-IOS 2026 time limit for a customer to file with the RBI Ombudsman after the bank's reply (secondary sources differ:
    "90 days of final reply" vs "no limit"); Hoola only states the 30-day rule. State SERC CGRF timelines differ from the 45-day
    central maximum; TRAI's billing-complaint timeline (shorter than 30 days) was not confirmed, so 30 days is used.
  - Business WhatsApp send was tested with a fake inbox.send (the Cloud API path is the existing employee inbox).
  - Fingerprint flow tested with a software EC key (same as tests/test_v097_fingerprint.py), not a real phone.
