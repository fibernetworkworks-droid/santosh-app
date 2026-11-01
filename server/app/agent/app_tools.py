"""v0.128 App Sahayak tools. `app_banao` designs her native app (every screen, tap-through prototype) before any app is
built; `app_dekho` only reads. Plan, look and 'Design pakka' are HER choices on the cards (the tool can do them only when
the owner herself clearly says so)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

APP_TOOLS = [
    {"name": "app_banao", "description": (
        "Design a premium NATIVE mobile app (Android + iPhone look) - her business's app, a client's app, or a PRODUCT app of "
        "its own (music, OTT, short video, social, chat, news, fitness, games, rides, food delivery, quick commerce, "
        "marketplace, tickets, jobs, courses, doctor consults, payments...: 33 product kinds) - and show her EVERY "
        "screen as a tap-through prototype BEFORE anything is built. Built apps: action=data|role|fix_crash|rollback|data_change|store (paid=Verified only when she saw the money; Play production only by her tap); read: app_dekho data / members / crashes / store. brief = HER EXACT WORDS, never your summary and never her "
        "own business added in (her business details go in by themselves only when the app is for her business). Don't pass "
        "goal unless she named the kind of app; a goal that doesn't fit her words is ignored. If it answers 'Pakka karne ke "
        "liye ek sawaal', ask her exactly that and call again with her answer in brief (or answers {sure: true} if she says "
        "'pehla wala hi'). A brand she names is only a reference: the app gets its own name and design. A few words are enough: the 1 lakh app brief library knows 1,000 kinds of "
        "business x 10 app goals x 10 premium styles, and the 1 CRORE APP IDEA library (app_dekho what=ideas) adds WHO the "
        "app is for (customers / owner / staff / delivery partner / dealers / members / managers), the ONE special thing "
        "(WhatsApp-first, daily subscription, voice in Hindi, offline, QR pickup, live tracking, udhaar reminders, parents' "
        "view, route plan, photo proof...), scale (one shop / branches / city network), market (town, metro, all-India, NRI) "
        "and positioning. When her ask is vague, first show 2-3 precise ideas (app_dekho what=ideas q=her words) and start "
        "the one she picks with idea=<its id>; when she was specific, start straight away (the best idea is picked from her "
        "words). action=new: idea (id from the idea list, optional), brief (her words, e.g. 'kirana dukaan ki app, ghar pe "
        "delivery'), name, goal (shop|food_order|booking|learning|membership|service_request|khata|catalogue|events|"
        "community; or a COMPLEX staff / admin app archetype: crm, field_sales, field_service, helpdesk, hrms, field_force, "
        "inventory, pos_retail, distribution, manufacturing_erp, procurement, logistics_tms, delivery_driver, fleet, isp_ops, "
        "telecom_tower, gis_survey, asset_utility, construction_pm, project_mgmt, hospital_his, clinic_emr, lab_lims, school_erp, "
        "coaching_admin, hotel_pms, restaurant_ops, real_estate_crm, society_mgmt, security_guard, facility_mgmt, iot_monitor, "
        "agri_fpo, dairy_collection, ngo_field, audit_inspection, collections, accounts_erp, intranet, events_ops, warehouse_wms, "
        "multi_branch, gym_admin; guessed from her words), style (optional), answers {name, phone, whatsapp, address, hours, upi_id}. Returns the PLAN "
        "card (screens, tabs, main flow, legal screens made by code; complex apps also get the BLUEPRINT: data tables, org levels, "
        "roles + permission matrix, approval chain, login plan, phone features with Play / App Store status - features the stores "
        "don't allow (reading SMS / call log, all files, accessibility, exact alarms) are NEVER promised: say what is used instead) "
        "+ up to 3 questions: ask them in ONE message (or "
        "ask_form). action=answer: app + answers. action=plan_ok: ONLY when she clearly said haan to the plan (+ drop: "
        "screens she doesn't want) -> Home screen in 3 looks (a few minutes; cards update by themselves, don't poll). "
        "action=look: app + index (0-2) she chose (+ colors_from) -> every screen is designed while she watches the board. "
        "action=change: app + instruction (her words: 'cart mein coupon hatao', 'rang halka', 'booking screen add karo', "
        "'tabs mein offers', 'store keeper role add karo', 'region ke neeche zone bhi', 'passkey login bhi', 'vendor table mein "
        "GST number') -> only those screens redesign; roles / levels / login / data / phone-feature changes redraw nothing. action=approve: ONLY when she herself says 'design pakka' "
        "(+ hash from the card) - freezes the design for the real app build. action=android: on an APPROVED design, builds the REAL "
        "native Android app (Kotlin + Jetpack Compose): every screen written from its approved design, compiled on Hoola's build "
        "machine (not this server; a few minutes, compile errors fixed by itself, a screen that won't compile gets a simple "
        "version), signed with the app's own preview key -> an APK card with 'Phone pe install karo' (Android's own Install screen) "
        "+ the project ZIP (opens in Android Studio). redo (screen ids) rewrites only those screens. No build machine set up -> "
        "only the ZIP (say so). Nothing goes to Play Store here. action=stop / resume / delete*. "
        "Never invent prices, phone numbers or reviews ([blank] instead); never card / CVV / UPI PIN / password fields; payments = "
        "UPI to her own UPI ID. (* owner only) v0.332 IPHONE: action=ios on an APPROVED design builds the REAL iPhone app (Swift + "
        "SwiftUI, same design, same backend / accounts / orders as Android): screens written by Opus, compiled on a Mac (her "
        "GitHub builds repo, workflow hoola-ios.yml), every screen opened in an iPhone simulator; kind=testflight (ONLY when she "
        "asks) also uploads it to TestFlight with HER App Store Connect key (a secret in her builds repo, never in chat). App "
        "Store review / release = her tap in App Store Connect, never here. No Mac set up -> the Xcode project ZIP (say so). "
        "v0.338 action=appstore (owner only) step=listing (App Store name / subtitle / keywords / description by Opus within "
        "Apple's limits) | push (that listing + 6.9-inch screenshots + the TestFlight build onto App Store Connect, via her "
        "builds repo; needs a TestFlight build first). Submit for Review is ONLY her tap in the app, never from chat. "
        "v0.342 action=github (owner only; repo optional, private default true): her app's whole code (android/ + ios/ + "
        "README + CHANGELOG, never a signing key) to HER GitHub as one new commit per build - makes a card, ONLY her tap "
        "on it pushes (her GitHub token is linked once in the app: Website > Hosting). "
        "v0.343 action=match (platform android|ios, fix): every real app screen vs her approved design (0-100); Opus looks at "
        "the ones under 70 and lists the visible differences; fix=true (only when she asks to fix) rebuilds those screens with "
        "the differences as notes. v0.347 action=bhasha langs [en, hi, mr, gu, bn, ta, te, kn, ml, pa, or, ur, hinglish] (max 6, "
        "the first = what the app starts in): the app's own words in those languages from the next build (customers pick on "
        "My account); her business data is never translated." "v0.314 ASLI APP: a built Android app has its OWN backend (accounts, real orders / bookings / requests, staff lists). "
        "action=data (app, coll, row, set) changes a row for her, e.g. an order's status (\"order accept karo\" -> set {status: Accepted}); "
        "v0.319: a customer's UPI \"I have paid\" claim reads paid=\"Customer says paid\" + utr; ONLY when she says she saw the money in "
        "her own bank set {paid: Verified} (never on the customer's word, never by yourself). Photos / locations her app's users sent are "
        "fields of the rows (a photo = a file id she sees in the app data view); "
        "v0.352 KAAM BAANTO: set {assign: <staff member id or name>} gives that row to one staff member (\"yeh job Ravi ko do\"), "
        "set {assign: \"\"} takes it back; only staff / admin accounts can be given work; that person's app shows it under My work "
        "and tells them. "
        "v0.355 action=gst (owner only; gst = {gstin, legal_name, rate 0|0.25|3|5|12|18|28, hsn, items {product id: {hsn, rate}}}): her GST "
        "details - finished rows then get a TAX INVOICE (GST-inclusive prices, consecutive INV/<FY>/0001 numbers) instead of a receipt; "
        "no gst = show them; gstin \"\" = plain receipts again. Returns / credit notes / e-invoicing stay with her CA. "
        "v0.382 DIMAAG - the app's BRAIN (any complex business logic): action=logic (owner only; instruction = her words, e.g. "
        "\"har order ke items alag list mein, total apne aap\", \"50,000 se upar ka quote manager phir director manzoor kare\", "
        "\"har din 9 baje unpaid invoices par reminder\"; empty instruction + no logic yet = the full logic from the app brief; "
        "empty instruction with logic = show it): Opus writes linked lists (customer -> orders -> items), formulas + totals, "
        "rules / unique keys, workflows with approval chains (maker-checker) + SLA, automatic triggers, timed jobs and locked "
        "custom functions; the checker proves it; it is only a DRAFT - she applies it with her tap on the app's Logic card "
        "(console app page / phone app screen), never you. action=logic_switch (owner only, on true|false ONLY on her ask): the "
        "whole logic on / off (nothing deleted). action=approval (owner only; approval = id from app_dekho what=logic, decision "
        "approve|reject, note) = HER decision on a waiting approval, only when she says it. action=logic_run (owner only; job = "
        "schedule name) = run a timed job now. "
        "v0.396 APNA DATABASE - an app's data in HER OWN database - PostgreSQL (Supabase, Neon, AWS RDS / Aurora, "
        "Google Cloud SQL, Azure, DigitalOcean...), v0.397 MySQL family (PlanetScale, TiDB, MariaDB, Aurora MySQL...), MongoDB "
        "(Atlas, Cosmos DB, DocumentDB) and Firebase (Cloud Firestore) - 41 kinds: "
        "action=own_db (owner only) = is it linked, where (label, schema), mode (primary = the data lives there and every entry is "
        "saved there first, her edits there come back; mirror = a live copy), sync lag, last problem, the counts compared, "
        "and where to find each provider's connection string. Connecting a database = HER connection string / Firebase key typed ONLY in the "
        "app (the app's 'Own database' card on the phone or console) - NEVER in chat (if she pastes one, do not use it; tell "
        "her to change that password). Moving the data / disconnecting = HER tap on the app's 'Own database' card, never you. "
        "v0.390 PAKKI NEEV - her app's data safety: action=data_safety (owner only; at = \"YYYY-MM-DDTHH:MM\" IST optional): "
        "usage (entries / files / writes today vs limits), the backups, and with `at` a PREVIEW of bringing the data back "
        "to that minute (what comes back / goes / changes) - the RESTORE itself is only HER tap on the app's Data safety "
        "card (console app page / phone), never you. action=backup_now (owner only) = a backup this moment. action=limits "
        "(owner only, ONLY when she asks; limits = {rows, files_mb, writes_day}) = her app's limits. "
        "v0.367 action=turant (owner only; show, or on=true / false ONLY when she asks): instant notifications for her Android app's phones "
        "(order moved, new order for staff, job given) through Hoola's Firebase - from the next build. v0.368 iPhones too once SHE puts her "
        "Apple push key into the app / console (Key ID, Team ID, .p8 - NEVER in chat; if she pastes one, do not use it and tell her to "
        "revoke it in Apple Developer). "
        "v0.362 action=variants (owner only; product = id or name, variants = [{name, price}], [] removes; no product = list): sizes / "
        "weights of a product, each with its own price and stock - every app screen shows them as chips. "
        "v0.361 action=hisaab (owner only; month YYYY-MM, default this / last month): her month's orders, sales, GST, credit notes and "
        "udhaar in one line; the CSV files for her CA download from the app data page (Accounts). Nothing is filed. "
        "v0.360 action=delivery (owner only; delivery = {fee, free_above, pins \"411001, 411002\", hours {open HH:MM, close HH:MM, days [0=Mon..6]}, "
        "off}; none = show): her shop app's delivery charge (added by the server), area and hours - an order outside them is still taken with a note. "
        "v0.359 action=khata (owner only): no member = who owes how much; member (id or name) = that customer's entries; with amount "
        "(+ mode cash|upi|card|bank|other, note) = record a payment SHE says she received (never on a customer's word, money never moves). "
        "v0.358 action=coupon (owner only; coupon = {code, kind percent|flat, value, cap, min, until YYYY-MM-DD, uses, once, on} or {code, "
        "delete: true}; no coupon = list): her discount codes - the server applies them to orders from its own prices; a failing code never "
        "loses an order. "
        "v0.357 action=stock (owner only; items = {product id or name: {qty: n or null = unlimited, low: warn level}}; no items = show): "
        "her shop app's stock - orders take it at once, more than is left is refused, a cancelled order puts it back, the app shows Sold out. "
        "v0.356 action=credit_note (app, coll, row, reason; owner only, ONLY when she asks - a return / wrong bill): a GST credit note "
        "(CN/<FY>/0001) for an invoiced row's full value; a cancelled invoiced row already gets one by itself. Money never moves: a refund is hers. "
        "v0.353 RAAY: a finished row carries the customer's own rating (rating 1-5 + rating_note); only that customer gives it, once - "
        "never set or change a rating yourself; a 1-2 star rating already reached her chat. "
        "action=role (app, member, role staff|admin|member) makes an account staff (a staff app's new account sees nothing until then). "
        "Read them with app_dekho what=data / members."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "answer", "plan_ok", "look", "change", "approve", "android", "stop", "resume", "delete",
                                                 "data", "role", "fix_crash", "rollback", "data_change", "store", "ios", "appstore", "github", "match", "bhasha", "gst", "credit_note", "stock", "coupon", "khata", "delivery", "hisaab", "variants", "turant",
                                                 "logic", "logic_switch", "approval", "logic_run",
                                                 "data_safety", "backup_now", "limits", "own_db"]},
         "app": {"type": "string", "description": "app number (A-0001) or name; empty = the latest"},
         "brief": {"type": "string"}, "name": {"type": "string"}, "goal": {"type": "string"}, "style": {"type": "string"},
         "answers": {"type": "object"}, "index": {"type": "integer"}, "colors_from": {"type": "integer"},
         "instruction": {"type": "string"}, "drop": {"type": "array", "items": {"type": "string"}}, "hash": {"type": "string"},
         "redo": {"type": "array", "items": {"type": "string"}}, "idea": {"type": "string"},
         "coll": {"type": "string", "description": "action=data: the app's list (orders, bookings, requests, ... or a staff list)"},
         "row": {"type": "string", "description": "action=data: the row id (from app_dekho what=data)"},
         "set": {"type": "object", "description": "action=data: fields to change, e.g. {\"status\": \"Accepted\"}"},
         "gst": {"type": "object", "description": "action=gst: {gstin, legal_name, rate, hsn, items}"},
         "reason": {"type": "string", "description": "action=credit_note: why (return, wrong bill...)"},
         "items": {"type": "object", "description": "action=stock: {product id or name: {qty, low}}"},
         "amount": {"type": "string", "description": "action=khata: payment received"},
         "mode": {"type": "string", "description": "action=khata: cash|upi|card|bank|other"},
         "month": {"type": "string", "description": "action=hisaab: YYYY-MM"},
         "product": {"type": "string", "description": "action=variants: product id or name"},
         "on": {"type": "boolean", "description": "action=turant: switch instant notifications on / off; action=logic_switch: logic on / off"},
         "approval": {"type": "string", "description": "action=approval: the approval id"},
         "decision": {"type": "string", "enum": ["approve", "reject"], "description": "action=approval: her decision"},
         "job": {"type": "string", "description": "action=logic_run: the timed job (schedule) name"},
         "at": {"type": "string", "description": "action=data_safety: a moment YYYY-MM-DDTHH:MM (IST) to preview a restore to"},
         "limits": {"type": "object", "description": "action=limits: {rows, files_mb, writes_day}"},
         "variants": {"type": "array", "items": {"type": "object"}, "description": "action=variants: [{name, price}]"},
         "delivery": {"type": "object", "description": "action=delivery: {fee, free_above, pins, hours, off}"},
         "coupon": {"type": "object", "description": "action=coupon: {code, kind, value, cap, min, until, uses, once, on, delete}"},
         "member": {"type": "string", "description": "action=role: the account id (app_dekho what=members); action=khata: customer id or name"},
         "note": {"type": "string", "description": "action=khata: payment note"},
         "crash": {"type": "string", "description": "action=fix_crash: the crash id (app_dekho what=crashes); empty = the newest unfixed one"},
         "build": {"type": "integer", "description": "action=rollback: the build number to bring back (app_dekho what=android history); 0 = the one before"},
         "step": {"type": "string", "enum": ["setup", "listing", "bundle", "internal"], "description": "action=store: Play Store launch step (production = only her tap in the app)"},
         "package": {"type": "string", "description": "action=store step=setup: the permanent package name she confirmed, e.g. com.sharmakirana.app"},
         "ops": {"type": "object", "description": "action=data_change: {add: [{coll, key, label, type, options}], hide: [{coll, key}], label: [{coll, key, label}]} - additive only, data never deleted"},
         "role": {"type": "string", "enum": ["member", "staff", "admin"]},
         "repo": {"type": "string", "description": "action=github: repo name in her GitHub (default <app>-app)"},
         "private": {"type": "boolean", "description": "action=github: private repo (default true); public only if she says so"},
         "langs": {"type": "array", "items": {"type": "string"}, "description": "action=bhasha: language codes, e.g. [\"hi\", \"en\", \"mr\"]"},
         "platform": {"type": "string", "enum": ["android", "ios"], "description": "action=match: which app's screens"},
         "fix": {"type": "boolean", "description": "action=match: rebuild the screens that do not match (only when she asks)"},
         "astep": {"type": "string", "enum": ["listing", "push"], "description": "action=appstore: the App Store step (submit for review = only her tap in the app)"},
         "kind": {"type": "string", "enum": ["sim", "testflight"], "description": "action=ios: sim = build + simulator check (default); testflight = also upload to TestFlight (only on her ask)"}},
         "required": ["action"]}},
    {"name": "app_dekho", "description": (
        "Read her app designs (nothing changes). what=data (app, coll: the real rows her app's users made) | members (app) | crashes (app: crashes on users' phones) | apps | app (app: board, screens, checks, preview link, versions) | "
        "checks (app) | spec (app: the frozen design contract: tokens, tabs, every screen's purpose / data / actions) | "
        "library (q or industry: business types with their app goal) | brief (field, goal, style: the full ready app brief) | "
        "understand (q: what a short ask means: business type, app goal, 3 looks) | design_system (the menu she can pick from: "
        "navigation types incl. side bar / floating bar / rail / top tabs, FAB types incl. speed dial, cards incl. glass, headers, "
        "buttons, textures, motion, 3D, colour schemes, fonts (q = font search, script = devanagari / tamil / ...)) | archetypes "
        "(the 43 complex app kinds with modules / roles) | capabilities (every Android / iPhone feature with Play + App Store "
        "status and the allowed alternative; q filters) | login (sign-in methods + security rules) | blueprint (app: data tables, "
        "roles matrix, levels, login plan, features, schema files + ER page) | schema (app: the PostgreSQL schema text). To change an "
        "app's structure use app_banao action=change with her words (screens are not redrawn for structure / mode / font). "
        "android (app: the native build: status, screens written / compiled / simple, rounds, APK link + size, ZIP) | ideas "
        "(q = her words -> the best precise app idea + 2 near ones + how many ideas exist for that business; field / goal / "
        "aud filter; offset pages through them; idea = one idea's full detail). Show ideas to her as 2-3 short lines (name + "
        "the special thing) and ask which one; then app_banao action=new idea=<id>." " data (app; coll = one list: its rows, newest first - the real orders / bookings / requests her app's users made, with status) | "
        "members (app: the app's accounts with their role). logic (app: v0.382 its business logic in plain lines, the draft waiting for her tap, approvals waiting, the last automatic actions). ios (app: the iPhone build: status, screens, simulator check, TestFlight). appstore (app: App Store steps, listing, App Privacy answers, one-time steps)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["apps", "app", "checks", "spec", "library", "brief", "understand", "design_system",
                                             "archetypes", "capabilities", "login", "blueprint", "schema", "android", "ideas",
                                             "data", "members", "crashes", "store", "ios", "appstore", "logic"]},
         "app": {"type": "string"}, "q": {"type": "string"}, "script": {"type": "string"}, "industry": {"type": "string"}, "field": {"type": "string"},
         "goal": {"type": "string"}, "style": {"type": "string"}, "aud": {"type": "string"}, "offset": {"type": "integer"},
         "idea": {"type": "string"}, "coll": {"type": "string"}},
         "required": ["what"]}},
]
APP_LABELS = {"app_banao": "App design bana raha hoon", "app_dekho": "App design dekh raha hoon"}
_OWNER_ONLY = {"delete"}
_TAP_LIKE = {"plan_ok", "look", "approve"}


def _owner(ctx: Ctx) -> bool:
    return ctx.actor == "owner" or str(ctx.actor).startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..appmaker import service as S
    t, ref, conv = ctx.tenant_id, str(a.get("app") or ""), ctx.conversation_id or ""
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf maalkin yeh kar sakti hain.")
    if action in _TAP_LIKE and not _owner(ctx):
        raise ToolError("Plan / look / design pakka sirf maalkin chunti hain (app ke card par).")
    if action == "new":
        v = S.new(t, str(a.get("brief") or ""), conv, str(a.get("name") or ""), "", str(a.get("goal") or ""),
                  str(a.get("style") or ""), a.get("answers") if isinstance(a.get("answers"), dict) else None,
                  idea=str(a.get("idea") or ""))
        return {k: v.get(k) for k in ("id", "number", "name", "status", "field_label", "goal_label", "plan", "questions",
                                      "understood", "idea", "other_ideas", "ideas_for_this_business", "say")}
    if action == "answer":
        return S.answer(t, ref, a.get("answers") if isinstance(a.get("answers"), dict) else {})
    if action == "plan_ok":
        v = S.approve_plan(t, ref, conv, a.get("drop") if isinstance(a.get("drop"), list) else None)
        return {"status": v["status"], "say": "Home screen ke 3 looks ban rahe hain; card par aa jayenge (poll mat kariye)."}
    if action == "look":
        cf = a.get("colors_from")
        v = S.choose_look(t, ref, int(a.get("index") or 0), int(cf) if cf is not None else None, conv)
        return {"status": v["status"], "preview": v["preview"],
                "say": "Screens banana shuru. Har screen ban-te hi board aur prototype mein dikhegi."}
    if action == "change":
        return S.change(t, ref, str(a.get("instruction") or ""), conv)
    if action == "approve":
        h = str(a.get("hash") or "") or S.get(t, ref).get("hash", "")
        v = S.approve(t, ref, h)
        return {"status": v["status"], "version": v["version"], "say": v["say"]}
    if action == "android":
        from ..appmaker.android import service as AN
        redo = [str(x) for x in a.get("redo") or []] if isinstance(a.get("redo"), list) else None
        v = AN.build(t, ref, conv, redo)
        return {"status": v["status"], "runner": v["runner"], "say": v["say"] + " Card apne aap badlega (poll mat kariye)."}
    if action == "ios":                       # v0.332 IPHONE
        from ..appmaker.ios import service as IO
        kind = str(a.get("kind") or "sim")
        if kind == "testflight" and not _owner(ctx):
            raise ToolError("Sirf maalkin TestFlight par bhej sakti hain.")
        redo = [str(x) for x in a.get("redo") or []] if isinstance(a.get("redo"), list) else None
        v = IO.build(t, ref, conv, kind, redo)
        return {"status": v["status"], "runner": v["runner"], "bundle_id": v["bundle_id"],
                "say": v["say"] + " Card apne aap badlega (poll mat kariye)."}
    if action == "bhasha":                    # v0.347
        from ..appmaker import i18n as I18
        v = I18.set_langs(t, ref, [str(x) for x in a.get("langs") or []])
        return {"langs": v["langs"], "say": "Agle build se app in bhashaon mein: " + ", ".join(I18.LANGS[x] for x in v["langs"])}
    if action == "match":                     # v0.343 design se milao
        from ..appmaker import match as MT
        v = MT.check(t, ref, str(a.get("platform") or "android"), bool(a.get("fix")), conv)
        plat = str(a.get("platform") or "android")
        rows = (v["match"].get(plat) or {}).get("screens") or []
        return {"say": v["say"], "rebuilt": v["rebuilt"], "avg": (v["match"].get(plat) or {}).get("avg"),
                "screens": [{k: x.get(k) for k in ("id", "label", "score", "differences")} for x in rows[:12]]}
    if action == "github":                    # v0.342 her app's code in HER GitHub: a card, only her tap pushes
        if not _owner(ctx):
            raise ToolError("Sirf maalkin yeh kar sakti hain.")
        from ..appmaker import code as CODE
        from ..site import github as GH
        try:
            v = CODE.request(t, ref, str(a.get("repo") or ""), a.get("private", True) is not False, conv)
        except GH.GithubError as e:
            raise ToolError(str(e))
        return {k: v.get(k) for k in ("repo", "private", "version", "files", "say")}
    if action == "appstore":                  # v0.338 App Store launch steps (submit for review = her tap, never here)
        if not _owner(ctx):
            raise ToolError("Sirf maalkin yeh kar sakti hain.")
        from ..appmaker.ios import appstore as AP
        stp = str(a.get("astep") or a.get("step") or "")
        if stp == "listing":
            v = AP.listing(t, ref, regen=True)
        elif stp == "push":
            v = AP.push(t, ref)
        else:
            raise ToolError("astep: listing / push (review ke liye bhejna sirf app ke button se)")
        return {k: v.get(k) for k in ("status", "now", "error", "steps", "listing", "bundle_id", "privacy_url", "support_url")}
    if action == "stop":
        return S.stop(t, ref)
    if action == "resume":
        return S.resume(t, ref)
    if action == "delete":
        return S.delete(t, ref)
    if action == "store":                     # v0.330 Play Store launch steps (production = her tap in the app, never here)
        if not _owner(ctx):
            raise ToolError("Sirf maalkin yeh kar sakti hain.")
        from ..appmaker.android import store as ST
        from ..appmaker import backend as BE
        r = BE.by_key_or_ref(t, ref)
        step = str(a.get("step") or "")
        if step == "setup":
            v = ST.setup(t, r.id, str(a.get("package") or ""))
        elif step == "listing":
            v = ST.listing(t, r.id, regen=True)
        elif step == "bundle":
            v = ST.build_bundle(t, r.id)
        elif step == "internal":
            v = ST.publish(t, r.id, "internal")
        else:
            raise ToolError("step: setup / listing / bundle / internal (production sirf app ke button se)")
        return {k: v.get(k) for k in ("package", "status", "now", "error", "steps", "listing", "privacy_url", "delete_url")}
    if action in ("rollback", "data_change"):     # v0.325 updates
        if not _owner(ctx):
            raise ToolError("Sirf maalkin yeh kar sakti hain.")
        from ..appmaker import backend as BE
        r = BE.by_key_or_ref(t, ref)
        if action == "rollback":
            from ..appmaker.android import service as AN
            v = AN.rollback(t, r.id, int(a.get("build") or 0), conv)
            return {"status": v["status"], "say": v.get("now") or "Purani build wapas aa rahi hai; card par dikhega."}
        return BE.change_schema(r, a.get("ops") if isinstance(a.get("ops"), dict) else {}, str(a.get("instruction") or ""))
    if action == "fix_crash":                 # v0.325 a crash from users' phones -> those screens rewritten, a new build
        if not _owner(ctx):
            raise ToolError("Sirf maalkin yeh kar sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker.android import service as AN
        r = BE.by_key_or_ref(t, ref)
        sig = str(a.get("crash") or "") or next((c["id"] for c in BE.crashes(r) if c.get("status") in ("new", "back")), "")
        if not sig:
            return {"say": "Abhi koi naya crash nahi hai."}
        x, sids = BE.crash_screens(r, sig)
        if not sids:
            BE.crash_mark(r, sig, "kit")
            return {"crash": x["exception"], "say": "Yeh crash app ki kisi screen mein nahi, Hoola ke apne hisse (kit) mein hai - "
                    "Hoola team ko bhej diya. Aapki screens theek hain."}
        note = ("THIS SCREEN CRASHED ON REAL USERS' PHONES (" + str(x.get("count")) + " times). Find the cause and fix it; keep the "
                "approved design. CRASH:\n" + str(x.get("sample") or "")[:3000])
        v = AN.build(t, r.id, conv, sids, {sid: note for sid in sids}, [sig])
        return {"crash": x["exception"], "screens": sids, "status": v["status"],
                "say": f"{', '.join(sids)} screen asli crash dekh kar dobara likh rahi hoon; nayi build ban rahi hai (card par dikhega)."}
    if action == "own_db":                                              # v0.396 APNA DATABASE (read only here)
        if not _owner(ctx):
            raise ToolError("App ka database sirf maalkin dekh sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker import owndb as OD
        r = BE.by_key_or_ref(t, ref)
        v = OD.status(r)
        out = {"linked": v["linked"], "link": {k: (v.get("link") or {}).get(k) for k in ("name", "label", "schema", "mode", "status",
                                                                                        "last_sync", "last_error")} if v["linked"] else None,
               "lag": v.get("lag"), "databases_connected": [c["name"] for c in v["connections"]],
               "providers": [p["name"] for p in v["providers"]]}
        if v["linked"]:
            try:
                out["counts"] = OD.verify(r)
            except Exception as e:                                      # noqa: BLE001
                out["counts_error"] = str(e)[:200]
            out["say"] = "App ka data aapke database mein chal raha hai."
        else:
            out["say"] = ("Database jodne ke liye: Profile > Postgres database (ya console mein app ka 'Own database' card) mein "
                          "connection string daaliye - chat mein nahi. Phir usi card par database chun kar 'Data wahan le jaao' dabaiye.")
        return out
    if action in ("data_safety", "backup_now", "limits"):               # v0.390 PAKKI NEEV
        if not _owner(ctx):
            raise ToolError("App ka data sirf maalkin dekh / badal sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker import backup as BK
        from ..appmaker import meter as MT
        from ..site import webapp as W
        r = BE.by_key_or_ref(t, ref)
        try:
            if action == "backup_now":
                return BK.snapshot(r, "asked in chat", "manual")
            if action == "limits":
                return MT.set_limits(r, a.get("limits") if isinstance(a.get("limits"), dict) else {})
            u = MT.usage(r)
            out = {"usage": {k: u[k] for k in ("lists", "rows", "files_mb", "writes_today", "limits", "percent", "full")},
                   "backups": BK.snapshots(r)[:10]}
            if a.get("at"):
                out["preview"] = BK.preview(r, str(a["at"]))
                out["say"] = ("Restore ka asar upar hai. Wapas laane ke liye app ke 'Data safety' card par woh samay chun kar "
                              "Restore dabaiye (pehle abhi ke data ki safety copy banegi).")
            return out
        except W.AppError as e:
            raise ToolError(str(e))
    if action in ("logic", "logic_switch", "approval", "logic_run"):     # v0.382 DIMAAG
        if not _owner(ctx):
            raise ToolError("App ki logic sirf maalkin badal sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker.logic import engine as LE
        from ..appmaker.logic import service as LS
        from ..site import webapp as W
        r = BE.by_key_or_ref(t, ref)
        try:
            if action == "logic_switch":
                return LS.switch(r, bool(a.get("on")))
            if action == "approval":
                return LE.decide(r, str(a.get("approval") or ""), str(a.get("decision") or ""), str(a.get("note") or ""), W.Who(owner=True))
            if action == "logic_run":
                return LE.run_schedule(r, str(a.get("job") or ""), force=True)
            words = str(a.get("instruction") or "").strip()
            v = LS.view(r)
            if not words and v["has_logic"]:
                return {k: v[k] for k in ("on", "rev", "summary", "approvals")} | {"draft": bool(v["draft"]), "say": "; ".join(v["summary"][:6])}
            return LS.draft(r, words)
        except W.AppError as e:
            raise ToolError(str(e))
    if action == "turant":                    # v0.367 TURANT
        if not _owner(ctx):
            raise ToolError("Notifications ka switch sirf maalkin ke paas hai.")
        from ..appmaker import backend as BE
        from ..appmaker import turant as TU
        r = BE.by_key_or_ref(t, ref)
        if a.get("on") is True:
            v = TU.enable(r)
        elif a.get("on") is False:
            v = TU.disable(r)
        else:
            v = TU.view(r)
        v["say"] = ("Turant notifications chalu: agli Android build se phone par usi waqt aayengi." if v["on"]
                    else "Turant notifications band; app 15 minute wali jaanch se batati hai.")
        return v
    if action == "variants":                  # v0.362 VARIANTS
        if not _owner(ctx):
            raise ToolError("Sizes sirf maalkin badal sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker import variants as VR
        r = BE.by_key_or_ref(t, ref)
        if a.get("product"):
            v = VR.save(r, str(a.get("product")), a.get("variants") if isinstance(a.get("variants"), list) else [])
        else:
            v = VR.view(r)
        withs = [p for p in v["products"] if p["variants"]]
        v["say"] = ("Sizes: " + "; ".join(p["name"] + " - " + ", ".join(f"{x['name']} Rs {x['price']:g}" for x in p["variants"]) for p in withs[:8])
                    + ".") if withs else "Kisi product ke sizes nahi."
        return v
    if action == "hisaab":                    # v0.361 HISAAB: the month's accounts
        if not _owner(ctx):
            raise ToolError("Hisaab sirf maalkin dekh sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker import hisaab as HS
        r = BE.by_key_or_ref(t, ref)
        rep = HS.build(r, str(a.get("month") or ""))
        return {k: rep[k] for k in ("month", "summary", "say", "counts")} | {
            "download": f"/api/apps/{r.id}/hisaab?month={rep['month']}&download=1",
            "gstr1": f"/api/apps/{r.id}/gstr1?month={rep['month']}",           # v0.373 the GST offline tool file
            "tally": f"/api/apps/{r.id}/tally?month={rep['month']}"}           # v0.374 Tally XML vouchers
    if action == "delivery":                  # v0.360 DELIVERY
        if not _owner(ctx):
            raise ToolError("Delivery niyam sirf maalkin badal sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker import delivery as DL
        r = BE.by_key_or_ref(t, ref)
        dv = a.get("delivery") if isinstance(a.get("delivery"), dict) else {}
        v = DL.save(r, dv) if dv else DL.view(r)
        v["say"] = (f"Delivery Rs {v['fee']:g}" + (f", Rs {v['free_above']:g} se upar free" if v.get("free_above") is not None else "")
                    + (f", {len(v['pins'])} PIN codes" if v["pins"] else "") + (", abhi khula" if v["open_now"] else ", abhi band") + ".") if v["on"] \
            else "Delivery ke koi niyam nahi (charge nahi, har jagah, har samay)."
        return v
    if action == "khata":                     # v0.359 KHATA: her customers' udhaar
        if not _owner(ctx):
            raise ToolError("Khata sirf maalkin dekh / likh sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker import khata as KH
        from ..site import webapp as W
        r = BE.by_key_or_ref(t, ref)
        mem = str(a.get("member") or "").strip()
        if mem and not KH._who_name(r, mem):                 # her words name a person
            hit = [m for m in BE.members(r) if mem.lower() in (str(m.get("name") or "").lower(), str(m.get("email") or "").lower())]
            mem = hit[0]["id"] if len(hit) == 1 else mem
        if mem and a.get("amount") not in (None, ""):
            v = KH.payment(r, mem, a.get("amount"), str(a.get("mode") or "cash"), str(a.get("note") or ""), W.Who(owner=True))
            v["say"] = f"{v['name']} ka payment likh liya. Ab baaki: Rs {v['balance']:g}."
            return v
        if mem:
            v = KH.summary(r, mem)
            v["say"] = f"{v['name']} par baaki: Rs {v['balance']:g}."
            return v
        v = KH.dues(r, W.Who(owner=True))
        v["say"] = (f"Kul udhaar baaki: Rs {v['total_due']:g} ({sum(1 for p in v['customers'] if p['balance'] > 0)} customers). "
                    "Yaad dilani ho to app ka data > Khata yaad mein har graahak ke liye 'WhatsApp mein kholo' (aap khud bhejein) "
                    "ya approved template se aapke tap par.")            # v0.375 reminders go only by her own tap
        return v
    if action == "coupon":                    # v0.358 COUPON: her discount codes
        if not _owner(ctx):
            raise ToolError("Coupon codes sirf maalkin bana sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker import coupon as CP
        r = BE.by_key_or_ref(t, ref)
        cp = a.get("coupon") if isinstance(a.get("coupon"), dict) else {}
        v = CP.save(r, cp) if cp else CP.view(r)
        live = [c["code"] for c in v["coupons"] if c["live"]]
        v["say"] = ("Chalu codes: " + ", ".join(live) + ".") if live else "Abhi koi code chalu nahi."
        return v
    if action == "stock":                     # v0.357 STOCK: her products' stock
        if not _owner(ctx):
            raise ToolError("Stock sirf maalkin badal sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker import stock as SK
        r = BE.by_key_or_ref(t, ref)
        items = a.get("items") if isinstance(a.get("items"), dict) else {}
        if items:                                   # her words name products: by id or by name
            prods = BE._products(r)
            by_name = {str(p.get("name") or "").strip().lower(): k for k, p in prods.items()}
            items = {(k if k in prods else by_name.get(str(k).strip().lower(), k)): v for k, v in items.items()}
        v = SK.set_items(r, items) if items else SK.view(r)
        v["say"] = f"Stock: {v['tracked']} products gine ja rahe hain, {v['sold_out']} khatam."
        return v
    if action == "credit_note":               # v0.356 WAPSI: her credit note for an invoiced row
        if not _owner(ctx):
            raise ToolError("Credit note sirf maalkin bana sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker import gst as G
        r = BE.by_key_or_ref(t, ref)
        v = G.credit(r, str(a.get("coll") or ""), str(a.get("row") or ""), str(a.get("reason") or ""))
        v["say"] = f"Credit note {v['credit_note']} ban gaya. Paise lautane hon to woh aap khud karein."
        return v
    if action == "gst":                       # v0.355 GST BILL: her GST details for this app's invoices
        if not _owner(ctx):
            raise ToolError("GST details sirf maalkin badal sakti hain.")
        from ..appmaker import backend as BE
        from ..appmaker import gst as G
        r = BE.by_key_or_ref(t, ref)
        g = a.get("gst") if isinstance(a.get("gst"), dict) else {}
        v = G.set_settings(r, g) if g else G.view(r)
        v["say"] = (f"GST invoice chalu: {v['gstin']} ({v['state']}), default {v['rate']}%." if v["on"]
                    else "GST invoice band hai; poore kaam par saadi raseed banti hai.")
        return v
    if action in ("data", "role"):            # v0.314 her own app's backend: she runs it from Hoola
        if not _owner(ctx):
            raise ToolError("App ka data sirf maalkin badal sakti hain.")
        from ..appmaker import backend as BE
        r = BE.by_key_or_ref(t, ref)
        if action == "role":
            return BE.set_role(r, str(a.get("member") or ""), str(a.get("role") or ""))
        sets = a.get("set") if isinstance(a.get("set"), dict) else {}
        if not sets:
            raise ToolError("Kya badalna hai? set = {status: ...}")
        return BE.owner_update(r, str(a.get("coll") or ""), str(a.get("row") or ""), sets)
    raise ToolError(f"Unknown action {action}")


async def app_banao(ctx: Ctx, action: str, **a) -> Any:
    from ..appmaker import service as S
    from ..site import webapp as W
    try:
        return await asyncio.to_thread(_act, ctx, action, a)
    except (S.AppError, W.AppError, KeyError) as e:
        raise ToolError(str(e) or "Nahi mila")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> Any:
    from ..appmaker import library as L
    from ..appmaker import service as S
    t, ref = ctx.tenant_id, str(a.get("app") or "")
    if what == "apps":
        return {"apps": S.apps(t)}
    if what == "app":
        v = S.get(t, ref)
        v.pop("facts", None)
        return v
    if what == "checks":
        return S.get(t, ref).get("checks")
    if what == "spec":
        return S.spec(t, ref)
    if what == "library":
        return L.browse(str(a.get("industry") or ""), str(a.get("q") or ""), 30)
    if what == "brief":
        b = L.brief(str(a.get("field") or ""), str(a.get("goal") or ""), str(a.get("style") or ""))
        return {k: b[k] for k in ("id", "field_label", "goal_label", "style_label", "screens", "tabs", "flow", "code_screens",
                                  "questions", "text")}
    if what == "understand":
        return L.understand(str(a.get("q") or ""))
    if what == "ideas":
        from ..appmaker import ideas as I
        if a.get("idea"):
            return I.idea(str(a["idea"]))
        q = str(a.get("q") or "")
        if q and not a.get("offset"):
            u = I.understand(q, str(a.get("field") or ""), str(a.get("goal") or ""))
            short = lambda x: {k: x[k] for k in ("id", "name", "special", "aud_label", "scale_label", "market_label",   # noqa: E731
                                                 "tier_label", "earn_label", "pitch")}
            return {"best": short(u["idea"]) if u.get("idea") else None, "near": [short(x) for x in u.get("alternatives", [])],
                    "ideas_for_this_business": u.get("count"), "all_ideas": I.total(), "ask": u.get("ask", ""),
                    "other_goals": [g for g in u.get("goals", []) if g != u.get("goal")][:8]}
        b = I.browse(q, str(a.get("field") or ""), str(a.get("goal") or ""), str(a.get("aud") or ""), int(a.get("offset") or 0), 12)
        b["items"] = [{k: x[k] for k in ("id", "name", "special")} for x in b.get("items", [])]
        return b
    if what == "design_system":
        from ..appmaker import colors as CL
        from ..appmaker import designsys as DS
        from ..appmaker import fonts as FN
        from ..appmaker import taxonomy as TX
        lab = lambda d: {k: (x.get("label") if isinstance(x, dict) else x) for k, x in d.items()}     # noqa: E731
        q, script = str(a.get("q") or ""), str(a.get("script") or "")
        return {"counts": L.counts(), "styles": {k: x["label"] for k, x in TX.STYLES.items()}, "nav": lab(DS.NAV), "fab": lab(DS.FAB),
                "cards": lab(DS.CARDS), "headers": lab(DS.HEADERS), "buttons": lab(DS.BUTTONS), "textures": DS.TEXTURES,
                "transitions": sorted({m["web"] for m in DS.MOTION.values() if m["kind"] == "transition"}),
                "three_d": list(DS.THREE_D), "colour_schemes": list(CL.SCHEMES),
                "fonts": [f["family"] for f in FN.families(script=script, q=q)][:40]}
    if what == "archetypes":
        from ..appmaker import taxonomy as TX
        return {"archetypes": [{"id": k, "label": g["label"], "modules": g["modules"], "roles": g["roles"], "screens": len(g["screens"]),
                                "brief": g["brief"]} for k, g in TX.GOALS.items() if g.get("complex")], "counts": L.counts()}
    if what == "capabilities":
        from ..appmaker import capabilities as CP
        q = str(a.get("q") or "").lower()
        rows = [c for c in CP.catalog() if not q or q in (c["label"] + " " + c["hi"] + " " + c["id"]).lower()]
        return {"capabilities": rows[:70], "legend": {"play": CP.PLAY_LABEL, "ios": CP.IOS_LABEL}}
    if what == "login":
        from ..appmaker import auth as AU
        return {"methods": AU.METHODS, "policy": AU.POLICY}
    if what == "blueprint":
        return S.blueprint(t, ref)
    if what == "android":
        from ..appmaker.android import service as AN
        return AN.get(t, ref)
    if what == "appstore":                     # v0.338 App Store launch state
        from ..appmaker.ios import appstore as AP
        return AP.get(t, ref)
    if what == "ios":                          # v0.332 the iPhone build: status, simulator check, TestFlight
        from ..appmaker.ios import service as IO
        return IO.get(t, ref)
    if what == "store":                        # v0.330 Play Store launch state
        from ..appmaker import backend as BE
        from ..appmaker.android import store as ST
        v = ST.view(BE.by_key_or_ref(t, ref))
        return {k: v.get(k) for k in ("package", "proposed", "account", "status", "now", "error", "steps", "listing", "bundle",
                                      "releases", "privacy_url", "delete_url", "console_steps")}
    if what == "logic":                                   # v0.382 DIMAAG: the app's brain, its draft, approvals, what it did
        from ..appmaker import backend as BE
        from ..appmaker.logic import service as LS
        v = LS.view(BE.by_key_or_ref(t, ref))
        d = v.get("draft") or {}
        return {"on": v["on"], "rev": v["rev"], "summary": v["summary"], "approvals": v["approvals"][:20],
                "audit": v["audit"][:15], "draft": {k: d.get(k) for k in ("summary", "lines", "errors", "questions")} if d else None}
    if what in ("data", "members", "crashes"):            # v0.314 the app's own backend
        from ..appmaker import backend as BE
        r = BE.by_key_or_ref(t, ref)
        if what == "crashes":
            return {"crashes": [{k: c.get(k) for k in ("id", "exception", "count", "screens", "versions", "devices", "status", "last")}
                                for c in BE.crashes(r)[:20]]}
        if what == "members":
            return {"members": BE.members(r)[:200]}
        if a.get("coll"):
            rows = BE.owner_rows(r, str(a["coll"]), 100)
            return {"coll": a["coll"], "rows": rows, "count": len(rows)}
        v = BE.owner_view(r)
        v["collections"] = [{"key": c["key"], "label": c["label"], "fields": [f["key"] for f in c["fields"]]} for c in v["collections"]]
        return v
    if what == "schema":
        data, _ct = S.blueprint_file(t, ref, "schema.sql")
        txt = data.decode()
        return {"schema_sql": txt[:12000], "truncated": len(txt) > 12000, "chars": len(txt)}
    raise ToolError(f"Unknown what {what}")


async def app_dekho(ctx: Ctx, what: str, **a) -> Any:
    from ..appmaker import service as S
    from ..site import webapp as W
    try:
        return await asyncio.to_thread(_read, ctx, what, a)
    except (S.AppError, W.AppError, KeyError) as e:
        raise ToolError(str(e) or "Nahi mila")


APP_HANDLERS = {"app_banao": app_banao, "app_dekho": app_dekho}
