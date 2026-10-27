# WIRING for drivers
summary: Driver Sahayak (driver coordinator: drivers with the licence in the Pehchaan Locker and dated papers, leave, duty roster checked against the law's hours (OSH Code 8 h / 48 h, spread-over, 30 min after 5 h, 9 h rest, 6 days) and her stricter rules, licence class vs vehicle weight, overlaps never saved; trip sheets from words / driver messages / photo OCR with km continuity, km-per-litre and overtime checks; duty / licence / missing-sheet message drafts sent only on her tap; attendance + OT for payroll)
db: app.drivers.models
router: app.drivers.api            (make_router(require_key, current_tenant); all routes under /api/drivers, key-protected; no public routes)
tools: app.agent.drivers_tools     (DRIVERS_TOOLS / DRIVERS_LABELS / DRIVERS_HANDLERS) ; voice: yes (drivers, drivers_dekho)
employee: duty driver_coord = [drivers, drivers_dekho, file_read] {label "Driver coordinator", say "driver ki duty lagana (kaanoon ki ghante ki seema ke saath), trip sheet, licence / medical yaad, hazri payroll ke liye (message aapke tap se, paisa kabhi nahi)"} ; role driver_coordinator {label "Driver coordinator", duties [driver_coord, reminders, records]} ; preset drivers {label "Transport / gaadiyan / driver", role driver_coordinator, rules ["Driver ko message sirf owner ke tap se", "Driver ko paise / advance Hoola nahi deta", "Licence khatam = duty nahi"]} ; READ tools: [drivers_dekho]
  - staff (staff:<id>) who are linked drivers (driver.member_id = their TeamMember id) may only: `drivers action=trip` for THEIR OWN sheet (saved as a draft) and `drivers_dekho what=duties` (their own upcoming duties). The tool refuses customer actors everywhere and every other action for staff; owner-only: driver, leave, settings, vehicle, forget, to_payroll, trip_ok, and `force` on a duty that breaks a law / her rule (service checks the actor). Messages are never sent by any tool: only POST /api/drivers/messages/{id}/send (her app tap, with the card hash).
push: drivers_alert -> ("Driver ke kaagaz", "{say}")
push: drivers_plan -> ("Driver duty: bhejne ke liye taiyaar", "{say}")
push: drivers_day -> ("Aaj ke driver", "{say}")
  (drivers_message: no push, it is the reply to her own request in chat)
worker: app.drivers.service.tick   (call every minute, e.g. `await asyncio.to_thread(drivers.service.tick)`; once a day at her morning_time: document reminders (once per window 30/15/7/1/0, overdue once + after 7 and 30 days) -> drivers_alert, morning note -> drivers_day when there is something; once a day at her evening_time: tomorrow's duty DRAFTS -> drivers_plan)
prompt: DRIVERS: duty / trip sheet / driver licence work -> `drivers` (her exact words for trip sheets in `text`; a driver's forwarded message with from_driver=true; a photo of the paper sheet with action=trip_photo). A duty that breaks the hours law / her rule is NOT saved: tell her the reason; only if she clearly accepts, call again with force=true and her reason. Overlaps, leave, an expired licence or a wrong licence class can never be forced. Messages to drivers are drafts: say "card par tap karke bhejiye", never claim they were sent. Never move money / advances (payroll / her job). Licence numbers go into the Pehchaan Locker; repeat only the last 4.
persona: Driver ki duty lagate waqt ghante aur aaraam ki seema bolo; driver ko message "aapke tap se jayega" kaho; driver ko paise kabhi mat bhejo.
flutter: DriversScreen in lib/ui/drivers_screen.dart ; profile tile title "<name> · Driver coordinator" subtitle "Duty, trip sheet, licence yaad, hazri" icon Icons.local_shipping_rounded ; cards: drivers_plan -> DriversPlanCard (also in calls: yes; key by data['day'] + data['title']) ; drivers_message -> DriversMessageCard (also in calls: yes; key by data['id']) ; drivers_alert -> DriversAlertCard (also in calls: no) ; drivers_day -> DriversDayCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)`, `app.api!.uploadFile(...)` (trip photo) + `Native.openExternal`; image_picker (already a dependency).
features: drivers
env: none
requirements: none (openpyxl via officegen; OCR via the existing app/ocr.py when Tesseract is installed)
android: none
neighbours: fleet (vehicles: `service.vehicle_info` calls `app.fleet.service.find_vehicle(tenant, ref)` or `vehicle_brief(tenant, ref)` if that module exists and returns {id, number|reg_no, gvw_kg|gvw, kind, kmpl}; otherwise the light vehicle list here), payroll (attendance: `to_payroll` -> payroll.service.set_attendance with lop_days / ot_hours; salaries / advances stay in payroll on her Haan), employee (team members over Hoola Network: net.service.send kind message; business WhatsApp: employee.inbox.send inside Meta's 24 h window), idvault (licence numbers), ocr / chatfiles / officegen. Other Safar builders: logistics, warehouse, courier, travel, customs.
claude_md: |
  ## v0.1xx Driver Sahayak: Hoola as the driver coordinator ("Driver coordinator" on the Employee page)
  - Owner's spec: plans duties -> tracks trip sheets -> sends reminders. Messages to drivers are drafts she sends (wa.me / SMS from her
    phone) or go on HER tap through her business WhatsApp (Meta 24 h window) or Hoola Network (drivers who are her team members);
    advances / salaries are payroll's / hers, Hoola never moves money.
  - Server `server/app/drivers/{rules,models,service,api}.py`, tools `drivers` / `drivers_dekho` (`agent/drivers_tools.py`, chat + calls),
    duty `driver_coord`, role `driver_coordinator`, preset `drivers`, API `/api/drivers/*`, app Profile > Driver coordinator
    (`lib/ui/drivers_screen.dart`: Aaj / Duty / Trip sheet / Driver / Hazri / Niyam), cards DriversPlanCard (`drivers_plan`),
    DriversMessageCard (`drivers_message`), DriversAlertCard (`drivers_alert`), DriversDayCard (`drivers_day`). Tests
    `server/tests/test_logi_drivers.py` (7).
  - Drivers D-001: phone, licence number straight into the Pehchaan Locker (kind dl, sealed; only {id:...} + last 4 kept / shown;
    format SS RR YYYY NNNNNNN checked), licence classes (LMV / LMV-TR / MGV / HGV / HTV / MPV / HPV / TRANS / hazardous), licence,
    medical (Form 1A), badge, hazardous-training dates, police verification date (+ her recheck months, starter 24), usual vehicle,
    payroll name, Hoola Employee team member link, no-messages switch. Leave (leave / sick / off / unpaid): planned duties that clash
    are named. DPDP: `forget` after a driver left erases phone, licence (locker row too), notes; duty / trip numbers stay.
  - Duties DU-0001 (day, start / end HH:MM, past midnight ok, break minutes, vehicle (fleet module by id / number if present, else her
    light vehicle list: gross weight, kind, km per litre), route, hazardous). `rules.check_duty`: NEVER saved = same driver overlap,
    same vehicle with another driver, leave, left, licence expired before the duty ends (MV Act s.3 / s.181), LMV-only on a vehicle
    over 7,500 kg GVW (Supreme Court, Rambha Devi, 6 Nov 2024), hazardous load without the endorsement (CMV Rules r.9). LAW / her-rule
    flags (saved only when the OWNER says force + a reason, logged on the duty and in the Excel): day's work over 8 h (same-day duties
    add up = split duty) = overtime, spread-over over 12 h, under 9 h rest from the previous / to the next day's duty, week (Mon-Sun)
    over 48 h, more than 6 days in a row, medical expired. Tip: 30 min rest after 5 h. Her limits can only be stricter than the law's
    (a looser value is said and ignored). `plan` = who can take each need (free, rest, week hours, class, usual vehicle), best first,
    nothing saved; drivers already given a need in the same plan count.
  - Trip sheets TS-0001: from her words / app form (ok), a driver's message or a photo / PDF of the paper sheet via OCR (draft until
    "sahi hai"). `rules.parse_sheet` reads only what is written (start / end km or "km a - b", times with subah / shaam / baje / am / pm,
    diesel / petrol litres + rupees, toll / FASTag, parking / khana / puncture / hamali / challan / repair, "X se Y tak" route); an optional
    model pass may fill a missing field only with a number that appears in the text. Linked to that day's duty (planned -> done; vehicle
    from the duty). Checks: end below start, > 1,200 km, start != the vehicle's previous end (km not on any sheet / meter went back),
    km per litre vs her figure or the vehicle's own last 30 sheets (>= 3 with fuel; tolerance 20 %), trip hours over the day limit /
    spread-over, rupees without litres, no vehicle. Missing sheets = past duties without one -> reminder drafts. Licence numbers / phones
    in OCR text are masked before anything keeps them.
  - Messages M-0001 (duty plan for a day, licence / paper reminders, missing sheet, her own): DRAFT + hash; wa.me / SMS links; ONLY
    `POST /api/drivers/messages/{id}/send {via self|business|hoola, hash}` sends (self = she sent it from her phone); a changed message
    voids the card; business only if the driver has written to her business number (and not STOP); hoola only for active team members
    with a Hoola ID; a driver who said no to messages only from her own phone; OTP / PIN / card / Aadhaar text refused. Sent duty
    messages mark the duties "bata diya".
  - Worker `tick`: at her morning time the paper reminders (once per window 30 / 15 / 7 / 1 / 0 days; overdue once, again after 7 and 30
    days; a draft for the driver with each) + the morning note; at her evening time tomorrow's duty drafts card.
  - Attendance (month): days worked (duty done or a sheet), paid leave, LOP (unpaid leave + absent), hours, OT = daily excess over 8 or
    weekly over 48, whichever is more (OSH Code), nights, trips, km, expenses claimed, sheets missing -> Excel (Attendance with payroll's
    own headers "LOP days" / "OT hours", Trips, Duties, Note) as her file; `to_payroll` (owner) writes LOP / OT into the v0.94 payroll
    register by payroll name, unmatched names listed; the salary run still waits for her Haan there.
  - Never: paying / advancing money, sending a message without her tap, keeping a full licence number outside the locker, a duty on an
    expired licence or overlapping duties, inventing km / fuel / times.
  - Research (23 Oct 2026): MV Act 1988 s.91 (drivers' hours follow the MTW Act, now the OSH Code); OSH Code 2020 in force 21 Nov 2025
    (s.143 repeals the MTW Act 1961; s.25 8 h a day incl. running time, subsidiary work and terminal attendance < 15 min for motor
    transport workers; s.27 overtime double wages with consent) and OSH Central Rules 2026 G.S.R. 345(E) 8 May 2026 Rule 64 (48 h a
    week; spread-over / intervals left to the appropriate (state) Government) - taxclue.in/blog/rule-64-osh-central-rules-2026-working-hours;
    MTW Act values used as starters (spread-over 12 h, 30 min after 5 h, 9 h rest between duties, 10 h only on notified long routes) -
    factohr.com/?p=48986; licence renewal: transport licence 5 years, renew up to 1 year before (MV Act s.14 / s.15), driving on an
    expired licence = s.3 / s.181 Rs 5,000 - advocategandhi.com; Supreme Court Bajaj Allianz v Rambha Devi (6 Nov 2024): LMV licence
    covers transport vehicles up to 7,500 kg - scobserver.in; Motor Vehicle Aggregator Guidelines 2025 (1 Jul 2025: medical fitness,
    no offence in 3 years, 40 h induction training) - scconline.com/blog/?p=352371. Hazardous-licence 3-year validity and police
    re-verification periods vary by rule / state: shown as her settings, not law.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI annotations for lib/ui/drivers_screen.dart (Dart 3 records in collection-for, image_picker, api.uploadFile). OCR on a real paper trip sheet not tried (Tesseract not in the sandbox; tests fake ocr.read); handwritten sheets will often read badly and stay drafts. The model pass for messy sheets is tested only with a stub. Fleet-module lookup is by an assumed function name (find_vehicle / vehicle_brief) since that module is built in parallel: the coordinator should match it. State-specific spread-over / rest rules under the OSH Code are not encoded (MTW starters, labelled). Business WhatsApp send tested with a fake inbox.send; Hoola Network send with a fake net send. Push titles are suggestions.
