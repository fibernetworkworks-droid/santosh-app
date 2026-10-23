# WIRING for fleet
summary: Fleet Sahayak (fleet manager: vehicles with RC / insurance / fitness / PUC / permit / tax / AIS-140 papers and reminders once per window, fuel km/l with theft / leak signals + fuel-card import, service by km / months, tyres, breakdowns, challans she found, trips with load fit / split / papers / estimate from her own rates, cost per km, idle days; any spend only on her tap, Hoola never pays)
db: app.fleet.models
router: app.fleet.api            (make_router(require_key, current_tenant); all routes under /api/fleet, key-protected; no public routes)
tools: app.agent.fleet_tools     (FLEET_TOOLS / FLEET_LABELS / FLEET_HANDLERS) ; voice: yes (fleet, fleet_dekho)
employee: duty fleet_work = [fleet, fleet_dekho, file_read] {label "Fleet / gaadiyan", say "gaadiyon ke kaagaz aur reminder, diesel aur average, service, tyre, trip aur load plan (har kharcha aapki haan se)"} ; role fleet_manager {label "Fleet manager", duties [fleet_work, reminders, records]} ; preset fleet {label "Transport / fleet owner", role fleet_manager, rules ["Har kharcha (service, tyre, permit, challan) sirf owner ki haan ke card se", "Capacity se zyada maal kabhi nahi", "Khatam insurance / fitness / permit wali gaadi trip par nahi"]} ; READ tools: [fleet_dekho]
  - staff (staff:<id>) may log fuel / service done / tyre / breakdown / challan / expense, plan trips, ask for a spend card. Owner-only (enforced in the tool): settings, vehicle add / change, service_set, spend_done, register. Customer actors are refused. No tool ever approves a spend: only POST /api/fleet/spends/{id}/decide (her app tap, card hash; fingerprint once a phone key is active, approvekey kind "fleet").
push: fleet_spend -> ("Fleet: kharche ki haan chahiye", "{say}")
push: fleet_alert -> ("Fleet", "{say}")
push: fleet_day -> ("Aaj ka fleet note", "{say}")
  (fleet_trip: no push, the card updates on the screen; publish only)
worker: app.fleet.service.tick   (call every minute, e.g. `await asyncio.to_thread(fleet.tick)`; document reminders once per window per expiry date, service due / late once per state, morning note once a day at her morning_time when there is something)
prompt: FLEET: gaadi / kaagaz / diesel / service / tyre / trip / load ki baat -> `fleet` (and `fleet_dekho` to read). Expiry dates only from her paper (photo -> file_read -> `fleet action=doc`), never guessed; Vahan / eChallan / Parivahan are never scraped: give her the official steps (`fleet_dekho what=steps`). ANY spend (service, tyre, permit fee, tax, insurance, challan, repair) = `fleet action=spend` card with HER amount: say "aapki haan ka card bheja hai", never that it is approved or paid; Hoola never pays. Never plan an overloaded trip; distance / toll / diesel rate only from Google Maps or her numbers.
persona: Gaadi ke kharche par "aapki haan ka card bheja hai" kaho, khud kabhi paise nahi; kaagaz ki taarikh unke kaagaz se lo; capacity se zyada maal kabhi plan mat karo.
flutter: FleetScreen in lib/ui/fleet_screen.dart ; profile tile title "<name> · Fleet manager" subtitle "Gaadiyan, kaagaz, diesel, service, trip aur load" icon Icons.local_shipping_rounded ; cards: fleet_spend -> FleetSpendCard (also in calls: yes; one card per data['spend']['id'], updated in place; takes optional onDone) ; fleet_trip -> FleetTripCard (also in calls: yes; key by data['trip']['id']) ; fleet_alert -> FleetAlertCard (also in calls: yes) ; fleet_day -> FleetDayCard (also in calls: no). All widgets take (app:, data:) and use `app.api!.call(...)`, `app.api!.uploadFile(...)` (fuel statement), `Native.approveKeySign`, `Native.openExternal`, `pickAttachmentsOfType` (attach.dart).
features: fleet
env: none (Google Maps distance uses the existing GOOGLE_MAPS_API_KEY when set; without it Hoola asks her km)
requirements: none (openpyxl already present)
android: none
claude_md: |
  ## v0.1xx Fleet Sahayak: Hoola as a fleet manager ("Fleet manager" on the Employee page; Safar suite)
  - Owner's spec: plans routes and loads -> tracks fuel and service -> keeps permits up to date -> waits for her Haan on ANY SPEND
    (service, tyres, permit fee, tax, insurance, challan, repair). Hoola never pays a challan or buys anything.
  - Server `server/app/fleet/{rules,models,service,api}.py`, tools `fleet` / `fleet_dekho` (`agent/fleet_tools.py`, chat + calls), duty
    `fleet_work`, role `fleet_manager`, preset `fleet`, API `/api/fleet/*`, app Profile > "<name> · Fleet manager" (`lib/ui/fleet_screen.dart`:
    Aaj / Gaadiyan / Trips / Kharcha / Niyam, `FleetVehiclePage`), cards FleetSpendCard (`fleet_spend`), FleetTripCard (`fleet_trip`),
    FleetAlertCard (`fleet_alert`), FleetDayCard (`fleet_day`). Tests `server/tests/test_logi_fleet.py` (7).
  - Vehicles: registration number checked (state code, RTO, series, number; BH series), type truck / trailer / tanker / tempo / pickup /
    van / bus / taxi / car / two-wheeler, make / model, fuel, BS norm, registration date, payload tonnes, body cbm + l / w / h, axles,
    tank, RC owner + own / attached / leased, national permit yes / no, usual driver (name only), odometer (never backwards without
    odo_reset), status active / workshop / sold. A new vehicle gets its usual paper list (dates blank) and a STARTER service schedule
    (labelled starter; maker's manual decides).
  - Papers: RC, insurance (MV Act s.146), fitness (CMVR Rule 62: 2 years up to 8 years old, then yearly; ATS per G.S.R. 272(E) 5 Apr
    2022, dates extended, her RTO decides), PUC (Rule 115 by BS norm; the July 2026 3-year proposal is a DRAFT), national permit (5-year
    permit, yearly authorisation on vahan.parivahan.gov.in/npermit), state permit, road tax, AIS-140 VLTD + panic button (Rule 125H
    public service vehicles; goods by state), speed governor, FASTag note (no cash at NH plazas from 1 Apr 2026, UPI without FASTag
    1.25x). Expiry only from her paper; an issue date alone gives a marked "andaaza". Reminder windows per paper (her own days allowed),
    one reminder per window per expiry (`fleet_alerts`). Expired insurance / fitness / permit / RC block a trip; PUC / tax warn.
  - Official routes only: Vahan / mParivahan / eChallan / Parivahan are never scraped; `fleet_dekho what=steps` gives her the steps (she
    looks, she pays, OTP hers); the challan she finds is logged (`action=challan`, duplicates by number) and paying it is a spend card.
  - Fuel: litres / rupees / odometer / full tank -> km/l tank-to-tank per vehicle; signals (never verdicts): km/l more than her % (25)
    below the vehicle's median of 10, more litres than the tank, odometer backwards, rupees per litre 10% off her usual, very high km/l
    (half-logged fill). Fuel-card CSV / Excel import (IOCL / BPCL / HPCL style or any sheet): header found by column families, lubes / DEF
    skipped, deduped by txn id or vehicle + day + litres + amount.
  - Service by km / months (due 1,000 km / 10 days ahead, late after), service done resets lines; tyres by position with km run vs her
    life km; breakdowns (vehicle -> workshop; 3 in 90 days = repair-or-replace note); expenses; cost per km (fuel + service + tyre +
    breakdown + expense + paid challans over the odometer span) and idle days; vehicles idle for her `idle_days`.
  - Trips TR-0001: origin, stops, destination, day, items (weight / cbm / count / dims). Load fit = weight vs payload, volume vs body x her
    fill %, longest sides vs body; overload is a blocker (never assigned); the smallest free vehicle with valid papers is suggested, or a
    first-fit-decreasing split across vehicles. Distance = her km, else Google Maps Routes (server key) leg by leg; fuel = km / the
    vehicle's own km/l x HER rate, toll = her number or her per-km rate; missing ones listed, never guessed. Inter-state goods trip without
    a national permit warns; a drive over 8 hours for one driver warns (Motor Transport Workers Act 1961, now in the OSH Code 2020 from
    21 Nov 2025; duty / hours belong to the drivers Sahayak). Same vehicle twice on a day = blocked. Start needs no blocker; done records
    the odometer and flags a trip much longer than planned.
  - Spends FS-0001 (service / tyre / permit / tax / insurance / fitness / puc / challan / repair / fastag / gps / other): amount from her bill
    or portal (required, never invented), checks (30% above this vehicle's usual service / tyre cost, renewal while the paper is valid 60+
    days, challan amount differs from the logged one, vehicle sold), where she pays. ONLY `POST /api/fleet/spends/{id}/decide {yes, hash,
    proof}` (by_tap) decides; card hash must match; fingerprint once a phone key is active (428 -> `/challenge`, approvekey message kind
    "fleet"); the same waiting spend is never asked twice; "Maine de diya" only after approval turns it into a cost entry (a linked challan
    becomes paid).
  - Morning note (`fleet_day`, her time): today's trips + blockers, expired / due papers, service due, tyres, diesel signals (3 days),
    open challans, spends waiting / approved, idle and workshop vehicles. Excel register (vehicles, papers, cost per km, trips).
  - Never: paying or buying anything, scraping government / carrier sites, inventing expiry dates / distances / tolls / rates, planning an
    overloaded trip. Driver salary = payroll; driver duties = drivers Sahayak; LR / e-way bill / customer updates = logistics Sahayak.
  - Sources (checked 23 Oct 2026): morth.gov.in G.S.R. 272(E) 5 Apr 2022 (ATS, fitness 2 years / 1 year); vikaspedia.in (ATS date
    extended to 1 Oct 2024); thehitavada.com 8 Apr 2026 (Nagpur RTO: fitness every 2 years for the first 8 years, ATS opening);
    angelone.in 29 Jul 2026 (PUC validity by BS norm, 3-year BS-VI proposal is a draft); paybima.com 2026 (national permit 5 years, yearly
    authorisation, documents, portal; fees approximate); blog.fleetx.ai May 2026 (AIS-140 VLTD, GSR 979(E) 28 Sep 2018, hard-wired panic
    button, state enforcement; vendor guide); trucksbuses.com 30 Jan 2026 (FASTag: no cash from 1 Apr 2026, UPI 1.25x, KYV dropped 1 Feb
    2026); echallan.parivahan.gov.in (official check / pay). Service intervals, reminder windows and the 25% km/l signal are starters, not rules.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI annotations for lib/ui/fleet_screen.dart (uses Icons.tire_repair_rounded / Icons.car_crash_rounded, Dart 3 records and switch expressions). Google Maps distance tested only with a fake (`_maps_distance` monkeypatched); real Routes calls follow app/maps.py. Real fuel-card exports (IOCL XTRAPOWER, BPCL SmartFleet, HPCL DriveTrack) not seen: columns matched by common header words, check one real file. Fingerprint path tested with approvekey patched (same flow as Shikayat). ATS / PUC / AIS-140 applicability differs by state and changes often: shown as notes with dates, not enforced. Neighbours in the Safar suite: drivers (driver duties / hours / trip sheets: trips here keep only a driver name + phone), logistics (LR / e-way bill / customer updates: trip `ref` holds her LR / order number), warehouse, courier, travel, customs.
