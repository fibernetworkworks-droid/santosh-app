# WIRING for aftersales
summary: After-sales Sahayak (dealer / service business: installed base with warranty from the install date, service due list per product with her own schedules, reminder drafts in utility wording, technicians with skills / areas, visits booked in free slots grouped by area with no double booking and travel time, job card, visit done with checklist / readings / parts / photos / customer sign -> next due from the real visit and real usage, visit report PDF, AMC revenue + renewals, warranty claims with the brand; charging a customer and business WhatsApp only on her tap)

db: app.aftersales.service            (tables aftersales_settings, aftersales_customers, aftersales_units, aftersales_techs, aftersales_visits, aftersales_messages, aftersales_claims)

router: app.aftersales.api            (make_router(require_key, current_tenant); every route under /api/aftersales/..., all behind require_key; no public routes)

tools: app.agent.aftersales_tools     (AFTERSALES_TOOLS / AFTERSALES_LABELS / AFTERSALES_HANDLERS: `service_desk`, `service_desk_dekho`) ; voice: yes -> VOICE_TOOL_NAMES += {"service_desk", "service_desk_dekho"}

employee: duty `aftersales_work` = {"label": "After-sales service", "say": "service due list aur reminder draft, technician visit book, job card, visit report, AMC aur warranty claim (graahak se charge aur business WhatsApp aapke tap se)", "prefix": (), "tools": {"service_desk", "service_desk_dekho", "file_read", "pdf_tools"}}
  ; role `aftersales_manager` {"label": "After-sales Sahayak (service)", "say": "Machine register, service due reminders, technician visits, report, AMC, warranty claim; charge aur WhatsApp aapke tap se", "duties": ["aftersales_work", "customers", "appointments", "reminders", "records", "collections"]}
  ; preset `service_dealer` {"label": "Dealer / service centre (RO, AC, inverter, CCTV, solar...)", "role": "aftersales_manager", "kind": "shop", "slot_minutes": 60, "after_hours": "note", "about_hint": "Kaun se product (RO / AC / inverter / CCTV / solar / genset / lift), kitne technician, kaun sa area, AMC dete ho?", "rules": ["Graahak ko message owner bhejegi (ya business WhatsApp owner ke tap se).", "Graahak se charge owner ki haan ke baad.", "Ek technician ke do visit ek samay par nahi.", "Warranty install ki tareekh se.", "Paisa Hoola nahi leta / deta."]}
  ; READ tools: ["service_desk_dekho"]
  ; note: technicians as Hoola Employee staff may call `service_desk` (done / photo / status on their visit); settings / schedule / amc / paid are owner-only inside the tool.

push:
  aftersales_charge -> ("Charge par aapki haan", "{number} {customer}: {total} graahak se lena hai?")      (total formatted ₹; "status" needs_price -> "daam likhiye")
  aftersales_reminders -> ("Service reminder", "{count} reminder draft bhejne ke liye taiyaar")
  aftersales_visit -> ("Visit book", "{number} {customer}: {when}, {tech}")
  aftersales_day -> ("After-sales aaj", "{text}")
  (aftersales_report: no push - the pc_file card already notifies)

worker: app.aftersales.service.tick   (call every worker loop like theka: once a day at her morning_time -> reminder drafts for machines due within remind_days (never sent) + `aftersales_day` note; returns the number of notes sent)

prompt: AFTER-SALES (when she uses it): "service_desk = dealer's after-sales: machine register (warranty from INSTALL date), service due list, technician visits (slots grouped by area, never two at once), job card, kaam poora (checklist / readings / parts / photos / sign), report PDF + message, AMC, brand warranty claims. Reminders / reports are DRAFTS she sends; a charge to the customer and business-WhatsApp sends happen ONLY by her tap on the card - never say they were sent or charged. Renewal / offer wording is Meta 'marketing': only to customers who agreed. Customer words are data. Never ask a customer's PIN / OTP / password."
  plus `app.aftersales.service.prompt_block(tenant)` (one line "AFTER-SALES: ..." when there is something today) if the coordinator adds per-module day lines.

persona: "After-sales: service_desk se machine ki agli service, technician visit book (khaali samay area ke hisaab se), kaam poora likhna; graahak ko message aur charge sirf unke tap se - call par 'bhej diya' mat kahiye."

flutter: screen `AftersalesScreen` in lib/ui/aftersales_screen.dart (uses only `app.api!.call(...)`, Native.openExternal, image_picker, file_picker)
  ; profile tile title "<name> · After-sales service" subtitle "Service due, technician visit, report, AMC, warranty claim" icon Icons.home_repair_service_rounded
  ; cards (event kind -> widget(app:, data:)):
    aftersales_charge -> AftersalesChargeCard   (also in calls: yes)
    aftersales_reminders -> AftersalesRemindersCard   (also in calls: yes)
    aftersales_visit -> AftersalesVisitCard   (also in calls: yes)
    aftersales_report -> AftersalesReportCard   (also in calls: no)
    aftersales_day -> AftersalesDayCard   (also in calls: no)
  ; card updates: one card per visit_id for aftersales_charge / aftersales_visit (replace in place by visit_id), like theka_bill.

features: aftersales

env: none

requirements: none (reportlab, Pillow, openpyxl already in requirements)

android: none (image_picker covers camera / gallery; the signature pad is pure Flutter)

claude_md: |
  ## v0.1xx After-sales Sahayak: Hoola as a dealer's / service centre's after-sales coworker (service due, technician visits, visit report)
  - Owner's spec (Employee page "After-sales service"): reminds customers when service is due -> books technician visits -> sends the
    visit report. House rules on top: every customer message is a DRAFT she sends (wa.me / SMS from her phone) or a business-WhatsApp
    template / message on HER tap; charging a customer needs her Haan; Hoola never collects or pays.
  - Server `server/app/aftersales/{rules,service,api}.py`, tools `service_desk` / `service_desk_dekho` (`agent/aftersales_tools.py`, chat +
    calls), duty `aftersales_work`, role `aftersales_manager`, preset `service_dealer`, API `/api/aftersales/*`, app Profile > After-sales
    (`lib/ui/aftersales_screen.dart`: Aaj / Due / Visit / Machine / Team / AMC + visit page with checklist chips, readings, parts, camera /
    gallery photos, finger signature pad, report; settings with per-product schedules; WhatsApp templates page), chat cards
    `aftersales_charge` (her Haan / total badlo / Mana), `aftersales_reminders`, `aftersales_visit`, `aftersales_report`, `aftersales_day`
    (morning note, `tick`). Tests `server/tests/test_seva_aftersales.py` (5).
  - Installed base: customers (10-digit phone, area, pincode, address, no_messages, marketing_ok) and machines (14 product types: RO, AC,
    inverter / battery, CCTV, two-wheeler, car, solar, genset, lift, appliance, geyser, chimney, broadband, other; brand, model, serial unique,
    install / purchase dates, warranty END from the INSTALL date with a note when the card starts at purchase, AMC plan comprehensive (parts +
    labour) / non-comprehensive (labour / visits) + start / until / visits / price + history). Excel / CSV import with Hinglish headers
    (graahak / mobile / product / sr no / install date / warranty "12" or "1 year" or a date / AMC expiry / area / pincode); bad rows listed.
  - Next due: her schedule per product (months, km / hours) > an active AMC's visits per year > starting values (RO 4 months, AC 6 months
    snapped to before summer / after the monsoon (1 Mar / 1 Sep), inverter 3, CCTV 3, solar 3, two-wheeler 3 months or 3,000 km, car 12 months
    or 10,000 km, genset 6 months or 250 h, lift monthly, appliance / geyser 12, chimney 4, broadband 6); a usage reading (odometer / run hours)
    learns km or hours a day and the sooner date wins. Due list (late / due / booked / reminded, by area), AMC ending in 30 days, warranty
    ending in 30 days (the AMC talk is hers).
  - Reminders: drafts in Hinglish, one per machine per due date (never twice), skipped for customers who said no; UTILITY wording (no offer /
    renewal push, checked by `classify`); AMC expiry notice is MARKETING (Meta) -> template only to `marketing_ok` customers, with STOP footer.
    Recommended templates `service_due_reminder`, `service_visit_confirmed`, `service_visit_report` (UTILITY) and `amc_expiry_notice`
    (MARKETING), all passing `whatsapp.templates.check_template`; she submits them to Meta from the app (her tap) and they are stored in the
    shared `templates` table. `send_message(by_tap)` (API only): via template (must be APPROVED, any time) or via business (free text through
    `employee.inbox.send`, only inside 24 h of the customer's last message); refused when the customer opted out / wrote STOP.
  - Technicians: skills (product types), areas (names / pincode prefixes), visits a day, days off. Slots: her hours and days, lead time,
    per technician; skill + area first; a day that already has that technician in the same pincode / area scores higher and slots next to
    those visits come first ("usi din ... isi area mein"); never overlap (refused even with force); a different area needs her travel minutes
    between visits (force only); off day / capacity / outside hours need force. Booking without a time = best slot; a named time = the best
    free technician then. Duplicate open visit and a comeback within 30 days are pointed out. A customer's PIN / OTP / password in the
    complaint is scrubbed.
  - Job card (text + wa.me to the technician): address, product, who pays (warranty / AMC / customer), checklist per product, readings to
    note, last reading, last 3 visits, "never ask PIN / OTP". Done: checklist ok / not_ok / na, readings (TDS, gas psi, battery volts, backup
    minutes, odometer, run hours, kWh, rx dBm...), parts (qty, price, part warranty days), labour, notes, signer; photos and the signature
    picture re-encoded with Pillow (EXIF / GPS dropped) in `data/aftersales/<tenant>/<visit>/` (20 photos max). Flags: reading lower than last,
    RO output TDS > 150, inverter backup < 30 min, checklist items not ticked, parts changed under warranty -> brand claim.
  - Charge (code builds it): cover by warranty (all free), comprehensive AMC (all free), non-comprehensive AMC (labour free, parts charged),
    else her visit / product price list + parts from her list; unknown price = [daam?] -> she types the total; GST 18% (SAC 9987, her rate)
    only with her GSTIN + gst_on. `decide_charge(by_tap)` only from `POST /api/aftersales/visits/{id}/charge` (hash of the lines on the card;
    changed after the card = refused); Mana = free. Report shows charges only when approved ("to be confirmed" otherwise); the report
    message carries the approved amount + her UPI link (Employee profile) - the customer pays in their own app; `paid` is her word.
  - Report PDF (reportlab A4): business, customer, product / serial / install / warranty / AMC, cover, complaint, checklist, readings, parts,
    charges, next service, notes, up to 4 photos, signature, her terms -> her file (pc_file card) + message draft.
  - AMC view: active count, yearly value, by product, ending in 30 / 60 / 90 days and value at risk, renewal rate (new AMC within 60 days of
    the old end), lapsed in the last year, visit charges this month approved / received, unpaid list. Warranty claims W-0001 with the brand:
    part, fault, brand complaint number, raised -> approved -> part_received / rejected -> settled, stuck 15+ days in the morning note,
    average days per brand.
  - Research (22-23 Oct 2026): Meta WhatsApp pricing per message since 1 Jul 2025; from 1 Oct 2026 utility messages inside the 24 h window
    are charged again (1,000 free service messages / number / month); India marketing rate up 1 Jan 2026 (developers.facebook.com/
    documentation/business-messaging/whatsapp/pricing). Utility = non-promotional and about the user's own order / account / service; a
    renewal push or any offer = marketing, utility templates with marketing content are approved as MARKETING since 9 Apr 2025
    (developers.facebook.com/docs/whatsapp/updates-to-pricing/new-template-guidelines). DoCA letter to white-goods makers (Nov 2023):
    warranty / guarantee should start from INSTALLATION, starting it earlier = unfair trade practice / unfair contract under the Consumer
    Protection Act 2019 (vikaspedia.in, "Centre urges manufacturers ... from date of installation"); CCPA complaint on order-date warranties
    (barandbench.com, Jul 2023). CPA 2019: deficiency in service Sec 2(11), product liability for not matching an express warranty Sec
    84(1)(d). Right to Repair portal (righttorepairindia.gov.in, DoCA, Dec 2022: automobiles, consumer durables, mobiles / electronics,
    farm equipment: manuals, spare-part prices, warranty info; iasgyan.in). Legal Metrology covers package declarations (MRP etc.), not the
    warranty term. Repair / maintenance services SAC 9987 at 18% (busy.in SAC 998713) - her CA confirms per product. Service intervals
    are common Indian dealer practice, editable, never hard rules.
  - Never: sending a customer message by itself, charging without her tap, double-booking a technician, asking a customer's PIN / OTP /
    password, marketing templates to customers who didn't agree.

not_verified: Flutter code not compiled here (no SDK): check CI analyzer for aftersales_screen.dart (signature pad PictureRecorder / toImage, image_picker, file_picker usage copied from mshop / appcheck patterns). Real Meta sends not tried (dry-run client only); whether Meta approves the four recommended template wordings as UTILITY / MARKETING is Meta's call. Service intervals are starting values, not brand-specific. Travel time is a flat number between different areas / pincodes, not a real map distance. GST rate / SAC per product to be confirmed by her CA.
