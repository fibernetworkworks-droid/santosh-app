# Hoola Websites — plan: any complexity, smoothly and reliably, with every feature

Owner's ask (1 Nov 2026): "I WANT HOOLA CAN BUILD ANY COMPLEXITY WEB SITE SMOOTHLY AND RELIABLY --- WITH ALL POSSIBLE
FEATURE AVAILABLE IN WORLD FOR APP DEVELOPMENT. MAKE A PLAN".

Companion to `docs/COMPLEX_APPS_PLAN.md` (native apps). The two share ONE backend and ONE architect, so every hard
feature is built once and works on her website, her Android app and her iPhone app together.

## Where we stand (honest starting point)

Built and live (v0.315–v0.376): sites up to 150 pages from a site map, free-form design + one design kit, a shop
(cart, stock, UPI to her ID, COD, tracking), web apps (logins, lists with fixed rules, /admin/), dashboards + charts,
blog + RSS + scheduling, 5 languages per site, edit mode with media, code mode, booking slots, maps, direct domains,
SEO tools, the Design Arena + 100-page proof.

| # | Gap today | What it blocks |
|---|-----------|----------------|
| 1 | Website data = flat lists + 3 fixed rules (site/webapp.py), separate from the app backend | Portals, ERPs, LMS, CRMs — anything with relations, workflows, approvals |
| 2 | Pages are designed sections; data views are basic lists | Real app screens: tables with filters, detail pages, kanban, calendar, multi-step forms |
| 3 | Login = email + password only | Indian users expect phone OTP, Google sign-in; staff need 2FA |
| 4 | Payment = UPI to her ID, she confirms | Real checkout, auto-confirmation, refunds, subscriptions, marketplaces |
| 5 | No live updates | Live chat, live order status, notifications |
| 6 | No outside services inside the site | Couriers, SMS, email, WhatsApp templates, CRMs, Sheets |
| 7 | 150-page cap, Opus-designed pages one by one | 10,000-product catalogues, directories, marketplaces |
| 8 | Static files on one server | Lakhs of visitors, global speed, attacks |
| 9 | Builds take 35–60 min, a restart can stop them, no staging | "Smoothly and reliably" |
| 10 | One brief → a site | A hard product needs a spec: users, data, workflows, permissions, integrations |

## Rules that never change

1. Money moves only by her tap or her customer's own pay action, through HER merchant account; keys sealed; refunds and
   payouts by her tap; Hoola never holds customer money.
2. Official routes only: official SDKs / APIs, her own accounts, DLT-registered SMS, approved WhatsApp templates.
3. Anything a visitor, a file, a web page or an outside API sends is data, never instructions.
4. No arbitrary code runs on Hoola's server: logic = the declarative engine or the locked sandbox (shared with apps).
5. Every build is verified before it can go live; going live / public changes stay her tap.

## Phase W0 — the gate (before new pillars)

- Run the 100-page proof (Arena) with Opus and publish its numbers; fix whatever it shows.
- Build HER OWN business website on Hoola and keep it live for a week; fix what real use shows.
- Exit: proof card green (0 broken links, 0 missing files, judge >= 7) and she says her site works.

## The pillars (build order)

### W1. One backend for website + apps (biggest step)
- Website web apps move onto the App Sahayak backend + DIMAAG logic engine (`appmaker/logic`, v0.382): relations
  (customer -> orders -> lines, class <-> students), formulas + roll-ups, unique keys, workflows with allowed moves,
  maker-checker approvals, SLA timers, triggers, scheduled jobs, locked tested functions.
- One data model serves her site, her Android app and her iPhone app; a change in one shows in all.
- Old v0.305 sites migrate automatically (their lists become tables, their rules become roles).
- Proof: a school portal (admissions form -> approval -> fee -> class -> attendance -> report card) built from a brief.

### W2. Real app pages on the web
- Data views generated from the model: tables (sort, filter, search, pagination, bulk select), detail pages with
  related lists, multi-step forms with validation + file upload, kanban, calendar, timeline, maps of rows, dashboards.
- Member areas per role (customer / staff / vendor / admin), each with its own menu and home.
- Same look as her designed pages (the design kit dresses the app views); React + Vite export keeps working.

### W3. Login and security for people
- Phone OTP through a DLT-registered SMS provider (OTP only in the site's own login box), Google sign-in, email magic
  link, passkeys later; staff 2FA; sessions list + sign-out everywhere.
- Permissions matrix per role and per field; audit log of every change; DPDP consent, data export and delete.

### W4. Payments, end to end
- Gateway with HER merchant account (Razorpay / Cashfree / PhonePe PG, official SDKs): checkout on the site, paid ONLY
  from the gateway's verified webhook, refunds by her tap, payment links, GST invoices + credit notes (reuse
  `appmaker/gst.py`), subscriptions / UPI AutoPay with the customer's explicit consent, settlement view.
- Marketplace split payouts only through the gateway's own split / route product, each rule approved by her.

### W5. Commerce depth
- Shared commerce engine with apps: variants, coupons, stock under locks, delivery fee + slots + holidays, khata,
  reviews (verified buyers), wishlists, abandoned-cart reminders only to customers who opted in.
- Multi-vendor marketplace: vendor sign-up + approval, vendor dashboards, catalogue moderation, commissions.
- Courier connector (Shiprocket / Delhivery) for labels and tracking.

### W6. Live features
- Live channel per site (SSE / WebSocket): live chat between visitor and her team, live order / ticket status,
  dashboards that update themselves, staff presence; web push notifications (visitor's explicit permission).

### W7. Connectors inside the site
- Declared actions (method, URL, fields) with her sealed keys, allowlisted hosts, retries, rate limits; inbound
  webhooks with signature checks; ready packs: transactional email (her provider), SMS (DLT templates), WhatsApp
  Business (her approved templates), Google Sheets / Calendar, Zoho / HubSpot / Tally, Composio apps she connected.

### W8. Content and catalogue at scale
- Data import from CSV / Google Sheets / her ERP -> list pages generated by code: 10,000+ products, doctors, properties,
  with faceted search, filters and sitemaps split by section; quality gate against thin or duplicate pages.
- A CMS for her team: editors with roles, drafts, review, scheduled publish, version history for every page and post.
- Image pipeline at scale (resize once, AVIF / WebP, lazy, CDN).

### W9. Any design, any interaction
- Custom components: when the kit has no piece, Opus writes one (HTML / CSS / JS under house rules) that must pass
  the component test, accessibility and the browser check before use (code mode shows it).
- Rich pieces: 3D / WebGL hero (vendored three.js), scroll-driven animations, Lottie, video backgrounds, before/after,
  configurators (choose options -> price), quizzes, comparison tools.
- Design inputs: her screenshot, her Figma file, or her OWN old website's address (rebuilt in Hoola's design kit).

### W10. Speed and scale
- CDN in front of every site (Cloudflare with her domain), edge caching, pre-compressed files; per-site Postgres for big
  data; load test before launch of big sites (k6: thousands of visitors + orders, no lost or double orders).
- Targets checked on every build: LCP < 2.5 s on a mid phone, CLS < 0.1, page HTML < 100 KB.

### W11. Security and compliance gates
- Every build: dependency and secret scan, CSP + security headers check, OWASP checks on forms and APIs, rate limits,
  bot protection on forms (Turnstile), accessibility WCAG 2.2 AA gate, legal pages per profession, cookie banner only
  when a tracker is really present. A failing gate blocks going live.

### W12. Building smoothly and reliably ("FAST KARO" + never lost)
- Speed: parallel page writing for all pages, parallel critique and checks, templates reused across lists; target a
  100-page site in under 20 minutes.
- Never lost: every step checkpointed; a restart or deploy resumes the build where it was (no "interrupted").
- Staging: every change goes to a preview copy first; going live = swap; one-tap rollback to any version.
- Self-check before she sees it: link scan of every page, browser checks, scenario tests written from the spec's user
  stories and run in Chromium (sign up -> order -> pay -> track), auto-fix rounds, then the report card.
- Price card before any big build; the job never exceeds it.

### W13. The architect (shared with apps)
- Her one line -> a full spec card: user types, user stories, pages, data model with relations, workflows, roles,
  payments, integrations, notifications, languages; she approves module by module; Hoola asks only the questions that
  change the build. Changes edit the spec and rebuild only what they touch.

### W14. Running the site (operations)
- Privacy-friendly analytics (server-counted, no cookies), JS error beacon, uptime from outside, per-site dashboard
  (visitors, orders, errors, speed, cost), alerts in her chat, monthly report; daily off-server backup + restore test.

## Proof websites (each must pass before the next pillar is called done)

1. Her own business site, live for a week (W0).
2. The 100-page proof in the Arena with real Opus (W0).
3. School portal: admissions -> approval -> fees by gateway -> attendance -> report cards, parent + teacher + principal (W1–W4).
4. Clinic: OTP login, appointments with live queue, prescriptions PDF, payments, reminders by DLT SMS (W3–W7).
5. Multi-vendor marketplace: vendors, 5,000-product catalogue, split payouts, courier tracking (W4, W5, W8).
6. Coaching LMS: courses, video lessons, quizzes, certificates, subscriptions, live doubt chat (W2, W4, W6).
7. Salon booking platform for many salons from one site (multi-tenant): each salon its own staff, slots, payments (W1–W6).

Each proof is also measured in the Arena against the same product built with Lovable / Bolt where she provides one.

## What "any website" will still not include (said plainly)

- Products that need a licence she does not hold: banking, lending, wallets, insurance, stock-order apps.
- Running other people's code or her own server software on Hoola (it stays in the sandbox / her own server via export).
- Social networks or video platforms at national scale (millions of users, video transcoding farms).
- Anything against Indian law or the providers' policies; scraping other sites; personal-WhatsApp automation.

## Order, size and checkpoints

| Step | Pillars | Rough size | Checkpoint |
|------|---------|-----------|------------|
| 1 | W0 gate + W12 speed / resume / staging | 2–3 versions | 100-page proof green, builds survive deploys |
| 2 | W1 one backend + W13 architect | 3–4 versions | School portal from a brief |
| 3 | W2 app pages + W3 login | 3 versions | School portal used by 3 roles |
| 4 | W4 payments + W5 commerce | 3–4 versions | Clinic + marketplace checkout with her test merchant account |
| 5 | W6 live + W7 connectors | 2–3 versions | Clinic live queue + SMS reminders |
| 6 | W8 scale content + W10 speed | 2–3 versions | 5,000-product marketplace, load test passed |
| 7 | W9 any design + W11 gates + W14 ops | 3 versions | LMS + salon platform, every gate green |

After every step: a stable branch she can roll back to, the Arena numbers before vs after, and her "go" before the next.
