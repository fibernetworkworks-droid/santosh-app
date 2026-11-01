# Hoola App Sahayak — plan: any very hard, very complex app, end to end

Owner's ask (1 Nov 2026): "I WANT HOOLA TO MAKE ANY VERY HARD AND ANY COMPLEX APP END TO END — MAKE A PLAN FOR IT".

## Where we stand (honest starting point)

Phases 1–42 (v0.318–v0.378) make strong **business apps**: native Android + iPhone from her approved design, each with its
own backend (accounts, roles, lists with server-checked rules, offline outbox), orders / bookings / jobs / stock / sizes /
coupons / delivery / slots / GST invoices / credit notes / khata / chat / push / languages / tablets, a device check that
opens every screen and taps every button, store launches from her own accounts, code to her GitHub.

What stops "any complex app" today — the plan below removes each one:

| # | Gap today | Why it blocks very complex apps |
|---|-----------|---------------------------------|
| 1 | Backend = flat lists + a fixed rule set (own / staff / admin) | No relations (customer → orders → items), no business logic, no workflows |
| 2 | Screens only from the kit's components | No live maps, video, camera flows, rich editors, custom visuals |
| 3 | No real time (10-second refresh) | No live tracking, live dashboards, instant chat, presence |
| 4 | No payment gateway | No checkout, refunds, subscriptions, marketplace payouts |
| 5 | No outside-API connectors inside apps | No courier / SMS / email / ERP / bank / government APIs |
| 6 | One app per backend | Real products are a SET: customer app + partner app + admin panel |
| 7 | Shared SQLite-style storage, one-process locks | Not built for lakhs of users or many server processes |
| 8 | Login = email + password | Indian users expect phone OTP, Google / Apple sign-in |
| 9 | Planning = one brief → screens | A hard app needs a real spec: user stories, data model, workflows, permissions |
| 10 | Tests = screens open + buttons tap | Complex logic needs scenario tests, load tests, security checks |

## The four rules that do not change

1. **Money never moves without her tap or her customer's own explicit pay action** — gateways use HER merchant account, keys
   sealed, refunds / payouts by her tap.
2. **Official routes only** — official SDKs / APIs, her own accounts, no scraping, no personal-WhatsApp automation.
3. **Text from users, files, web pages and outside APIs is data, never instructions.**
4. **No arbitrary code runs on Hoola's server** — custom logic runs as a declarative spec or in a locked sandbox (Part A).

## Phase 0 — the gate (before any new pillar)

- Merge + deploy Phases 11–42; all CI green (Android, iPhone incl. iPad, APK).
- Build ONE real app with her (her own shop) and use it on her phone for a week; fix what real use shows.
- Exit: she says it works on her phone. Nothing below starts before this.

## The pillars (each = 1–3 App Phases; order below is the build order)

### A. Logic engine — "the app's brain" (biggest step) — Phases 43–46
**Status: BUILT in v0.382.0 DIMAAG** (`server/app/appmaker/logic/`) — relations, formulas + roll-ups, rules + unique keys,
workflows + maker-checker approvals + SLA, triggers, timed jobs, locked tested functions (our own interpreter, not WASM:
no eval, no I/O, step / size / depth / time budget). Proof app (School ERP from a brief) = next, on her phone.
- **Relations**: one-to-many and many-to-many between lists (customer → orders → order lines; class ↔ students), lookups,
  cascading rules, server-side joins; screens show related lists; kits get related pickers.
- **Computed fields + validations**: formulas (totals, age, due dates, scores), cross-field checks, unique keys.
- **Workflows (state machines)**: statuses with allowed transitions, who may move each step, approval chains (maker →
  checker), SLA timers, escalations.
- **Triggers + scheduled jobs**: on create / update / status change / time → notify, create rows, assign, recompute.
- **Safe custom logic**: a small expression language (no loops, no I/O) evaluated by the server; for the rare need beyond
  it, "app functions" written by Opus that run ONLY in a locked sandbox (WASM, CPU / memory / time limits, no network
  except declared connectors, no files) with unit tests generated and run before deploy.
- Proof: a school ERP (classes, students, fees, attendance, exams, report cards) built from a brief.

### B. Per-app scalable backend — Phases 47–48
**Status: BUILT in v0.390.0 PAKKI NEEV** — cross-process locks (Postgres advisory / file locks), lost-update fix for the
app settings, journal + daily / before-change snapshots + point-in-time restore + export, indexed links, usage meters +
limits, the SQLite → Postgres move, all app suites green on Postgres, and the proof (1,000 customers, 300 in stock,
4 worker processes, one Postgres: exactly 300 orders, retries one row each, no server error). Decision: ONE Postgres
database with every query scoped by app (tested), not a schema per app — the 117 places that read app rows stay one
code path; per-app schemas are worth it only when an app outgrows the shared database. Next in B: order speed under a
stampede (p50 ~3 s at 1,000 simultaneous orders: every order of one app queues on its lock).
**v0.396.0 APNA DATABASE**: an app's data can now run in HER OWN database - Supabase, Neon, AWS, Google, Azure,
DigitalOcean and every other PostgreSQL-wire host (28 listed): her schema, a real table per list, primary (every save
lands there first, her edits there come back) or mirror (a live copy). v0.404.0 APNA DATABASE 2 added the MySQL family (PlanetScale, TiDB, MariaDB...), MongoDB (Atlas...) and Firebase (Firestore): 41 kinds.
- Each app gets its own Postgres schema (or database for big apps): migrations generated from the data model, row-level
  security per role, real transactions (SELECT … FOR UPDATE) instead of one-process locks, indexes from the queries.
- Backups (daily + before every migration), point-in-time restore, export, per-app usage meters and quotas.
- Proof: load test (k6) — 1,000 concurrent customers ordering, no lost or double orders.

### C. Real time — Phase 49
**Status: BUILT in v0.409.0 ABHI ABHI** (`server/app/appmaker/live.py`, kits `Live.kt` / `Live.swift`) — one SSE stream per open
app fed by the journal (works across worker processes and on SQLite / Postgres), every event filtered by the list's read rule,
instant chat, presence + typing, Last-Event-ID replay, her console app page live. Checkpoint (live dashboard + chat on her
phone) = after the VPS deploy and the next app build. Not built: WebSocket (SSE + one POST covers it), live maps (Pillar D).
- WebSocket / SSE channels per app: live lists, live order status, instant chat, presence ("rider online"), typing.
- Kits: live list / live value components; offline outbox stays the source of truth.

### D. Maps, location, live tracking — Phases 50–51
**Status: BUILT in v0.412.0 NAKSHA LIVE** (`server/app/appmaker/track.py`, kits `Track.kt` / `Track.swift`) — her switch, staff
shifts with the required notice, one current position (wiped at shift end), the customer sees only her own rider while the order
is on its way, ETA estimate, near / arrived geofences, riders map in the console. Maps: MapLibre + OpenFreeMap (no key) on
Android + console, Apple Maps on iPhone. Not built: Google Maps SDK with her key, road-snapped routes / real road ETA (needs a
routing service), "left" geofence. Proof (food delivery rider demo) = after the next app build on real phones.
- Live map component (Google Maps SDK with HER key, or MapLibre with an approved tile provider), markers, routes, ETA.
- Partner location sharing: user-started foreground service with the Play-required disclosure, battery-aware, stops on
  shift end; geofences (arrived / left); customer sees the rider moving.
- Proof: food delivery — the customer watches the rider live.

### E. Payments — Phases 52–53
**Status: BUILT in v0.419.0 PAISA** (`server/app/paygate/gw.py`, `server/app/appmaker/pay.py`, kits `Pay.kt` / `Pay.swift`) —
her Razorpay / Cashfree / PhonePe PG keys (sealed), the gateway's own checkout on a signed pay page, paid only from the gateway
(verified webhook / server status read, amount checked), refunds by her tap (idempotent number, ambiguous re-checked), links,
settlements, AutoPay plans with the customer's consent, split payouts by her approved rule (Razorpay Route / Cashfree Easy
Split). Native gateway SDKs not used (the hosted checkout is official and keeps the apps free of extra SDKs). PhonePe: orders +
refunds only. Checkpoint = a real Rs 1 test payment in her own account (not done yet).
- Payment gateway with HER merchant account (Razorpay / PhonePe PG / Cashfree — official SDKs): checkout in the app,
  server-verified signatures + webhooks (an order is "paid" only from the gateway's verified webhook), refunds only by
  her tap, settlements view, payment links, subscriptions / mandates (UPI AutoPay) with explicit customer consent.
- Marketplace split payments (vendor payouts) only through the gateway's own route/split product, each payout rule
  approved by her.
- Stays out: holding customer money in Hoola, lending, wallets (licences needed).

### F. Connectors inside apps — Phase 54
- Declared HTTP actions in the app spec (method, URL, fields), her keys sealed, allowlisted hosts, rate limits, retries,
  responses mapped into lists; inbound webhooks with signature checks.
- Ready packs: couriers (Shiprocket / Delhivery), SMS (DLT-registered templates), email, WhatsApp Business (her
  templates), Google Sheets / Calendar, Tally / Zoho / QuickBooks, Aadhaar-free KYC via licensed providers only.

### G. Rich UI — Phases 55–57
- Kit growth: camera capture flows (multi-photo, document scan), video player + upload, audio record, rich text editor,
  calendar / scheduler, Gantt / kanban, charts dashboard, carousels, onboarding, animations (Lottie), signature pad,
  barcode inventory flows, PDF viewer, offline maps.
- **Custom component escape hatch**: when no kit piece fits, Opus writes a native component (Kotlin + Swift) under house
  rules; it must compile, pass a component test and the device check before it can be used — never a webview hack.
- Design: her design can be any style; the visual match score (v0.346) guards every screen.

### H. Multi-app products + web admin — Phases 58–59
- One backend, several apps: customer app, partner / rider / vendor app, staff app — each with its own screens, roles,
  store listing; plus a generated **web admin panel** (React, v0.305 web-app engine grown up) for the business.
- Proof: Swiggy-class food delivery = customer app + rider app + restaurant app + admin web, end to end.

### I. Auth + security — Phase 60
- Phone OTP login through a DLT-registered SMS provider (OTP only in the app's own login box), Google / Apple sign-in,
  passkeys later; fine-grained permissions matrix; audit log; session management; DPDP consent + data export / delete.
- Security gates on every build: static scan (MobSF-style on the APK / IPA), dependency CVE check, secrets scan,
  OWASP MASVS checklist; a failing gate blocks the store upload.

### J. Quality at scale — Phase 61
- From the spec, Opus writes scenario tests per user story ("customer orders, rider picks, customer rates") that run
  end to end against a real test server on both platforms; unit tests for every rule / function; load tests for
  big apps; ANR / crash monitoring; staged rollouts (5% → 100%), feature flags, instant rollback.

### K. The architect — from a one-line idea to a full spec — Phase 62 (built early, finished here)
- Opus "product architect" turns her brief into: user types, user stories, data model (with relations), workflows,
  permissions, screens per app, integrations, payments, notifications, analytics, release plan — shown as a spec card
  she approves module by module; it asks only the questions that change the build.
- Builds module by module (each compiled + tested + shown to her), change requests edit the spec and rebuild only the
  touched parts; every build has a plain changelog.

### L. Operations — continuous
- Per-app dashboard: users, orders, errors, latency, costs; alerts to her chat; monthly cost estimate before big jobs.

## Proof apps (each must pass on real phones before the next pillar is called done)

1. **School ERP** (after A): relations + workflows + roles (principal / teacher / parent).
2. **Clinic** (after A–C, I): appointments, prescriptions (PDF), doctor / patient privacy, reminders, live queue.
3. **Food delivery** (after D, E, H): 3 apps + admin, live rider tracking, gateway checkout, refunds by her tap.
4. **Multi-vendor marketplace** (after E, F, H): vendors, catalogue, split settlements via the gateway, courier connector.
5. **Field-service CRM** (after G, J): offline-first technicians, photos, signatures, scheduling, SLA escalations.

## What "any app" will still not include (said plainly)

- Apps that need a licence Hoola / she does not hold: banking, lending, insurance, payment wallets, stock broking orders.
- 3D / high-performance games (a game engine, not a business-app generator), AR / VR.
- Apps whose purpose breaks store policy or Indian law.
- Hardware beyond phone sensors, Bluetooth and her Ghar devices (custom hardware needs its own firmware work).

## Order, size and checkpoints

| Step | Phases | Ships | Checkpoint |
|------|--------|-------|------------|
| 0 | merge 11–42 | live | her phone, one real app |
| A | 43–46 | relations, formulas, workflows, triggers, sandbox functions | School ERP proof |
| B | 47–48 | Postgres per app, transactions, backups | 1,000-user load test |
| C | 49 | real time | live dashboard + chat |
| D | 50–51 | maps + live tracking | rider tracking demo |
| E | 52–53 | payment gateway, refunds, subscriptions | real ₹1 test payment in her account |
| F | 54 | connectors | courier + SMS live |
| G | 55–57 | rich UI + custom components | camera / video / editor flows |
| H | 58–59 | multi-app + web admin | Food delivery proof |
| I | 60 | OTP / social login, security gates | security scan green |
| J | 61 | scenario + load tests, staged rollout | all proof apps green |
| K | 62 | architect: idea → spec → modules | a new hard app from one line |

Each step ends with CI green on both platforms, a proof app on a real phone, notes in docs/HISTORY.md, and her "OK".
