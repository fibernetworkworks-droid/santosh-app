# Lovable's backend vs Hoola Web Studio's backend (17 Nov 2026)

Owner ask (17 Nov 2026): "NOW DO RESEARCH HOW LOVABLE BACKEND HANDLE PROPERLY", right after v0.988 PROMPT FIRST (her
"Build the ISP portal" got a marketing page).

Sources: `01_backend_data.md` (database, rules, sign-in, storage, test vs live, backups) and `02_backend_server.md`
(server functions, secrets, jobs, payments, AI gateway, emails, checks, lock-in) - both from ~40 docs.lovable.dev pages
fetched as `.md` on 17 Nov 2026, tagged line by line. The Hoola side below was read from our own code (file:line in the
mapping, not repeated here). Nothing here was run against a live Lovable app or a live Hoola site.

---

## 1. How Lovable's backend works, in one page

1. **One switch, three services.** "Enable Cloud" (now the "built-in backend", Supabase underneath) creates the database,
   user accounts and file storage together, in a region fixed for good. On by default.
2. **A real database per project.** Real Postgres tables with real columns. Tables come from her words; the agent writes
   the migration. Migrations are files (SQL until Oct 2026, Drizzle since 7 Oct 2026) with a journal and a hash per
   applied file.
3. **Migrations are careful.** Breaking changes (drop, rename, type change, required column with no default) are refused;
   the same result is reached by adding and copying. All pending files apply as ONE run (one failure = nothing applied),
   runs never overlap.
4. **Access = row-level security written by the agent.** Policies live in the database; the Policies view is read-only,
   changes go through chat. Form tables let visitors insert but not read.
5. **Checks.** A quick scan (seconds) every time Publish opens: tables without RLS, everyone-allowed policies,
   leaked-password check off, critical package advisories, open MCP servers. A deep scan (an AI code review, 3-15 min) on
   demand. The agent writes and runs a small test for every rule it changes before it says "done".
6. **Sign-in.** Email + password, Google and "Sign in with Lovable" by default; phone, Apple, Microsoft, SAML; password
   rules + Have-I-Been-Pwned check; redirect URLs updated on publish; built-in sign-in emails.
7. **Server code inside the app.** New apps: TanStack Start server functions (Cloudflare Workers per Lovable's blog);
   old apps: Supabase edge functions. Every server function is PUBLIC by address, so each must check its caller.
8. **Secrets** only through a secure form; a pasted key is detected and saved as a secret; values are never shown again.
   Scheduled jobs = pg_cron calling a route guarded by a cron secret.
9. **Connectors and payments.** Third-party calls go through Lovable's connector gateway (tokens never in code);
   built-in Stripe / Paddle where Lovable creates and holds the account; test mode = preview, live mode = published.
10. **AI gateway.** One `LOVABLE_API_KEY` per project, billed in credits; 429 = rate limit, 402 = no credits.
11. **Data separation.** Test / Live databases were WITHDRAWN (removed for new projects Mar 2026, retired for all Oct 2026,
    deleted 1 Dec 2026): preview and published app share ONE database. Drafts (16 Nov 2026) get their own example
    database with demo accounts - but use LIVE secrets and connectors.
12. **Backups.** Daily, ~14 days, self-serve restore; no point-in-time; restore also rolls back user accounts.

### Where Lovable is weak (do NOT copy)
- Agent permissions default to "Always allow", including "Modify database" and "Change data"; only breaking migrations
  default to Never. Nobody reviews a migration on Lovable's own backend by default.
- Publish is NOT blocked by critical findings by default (a skippable dialog; the hard block is a workspace setting).
- RLS "that exists but is wrong" is the class behind CVE-2025-48757 (~170 of 1,645 showcase apps exposed).
- One database for preview and production; a draft runs on live secrets.
- Built-in payments: Lovable owns the Stripe / Paddle account and keys.
- "Try to fix" covers build errors only; a runtime backend error gets no button.
- No direct database connection on the built-in backend; secrets are not exported.

---

## 2. How Hoola Web Studio's backend works today

- **Three backend paths share two tables** (`site_app_members`, `site_app_rows`; each row one JSON blob, 8 KB):
  A = the v0.305 site engine (retired by the worker's `migrate_all`), B = a linked website on App Sahayak's backend +
  DIMAAG logic (the live path for Studio sites, id `app:<project>`), C = Hoola Cloud for React App Engine apps
  (`ae:<app>:p` / `:l`).
- **Rules are a fixed vocabulary enforced in code on every call** (create public | member | admin; read public | members |
  own | admin | gated; update / delete own | admin; field flags admin_only / private). A model cannot write a wrong
  policy because it cannot write a policy at all.
- **Schema changes are additive** (B: add list / field, hide, relabel, snapshot first; C: one numbered run, drop / rename /
  type change refused, data loss only by her tap).
- **Logic (B only):** relations, formulas, rules, unique keys, workflows with SLAs and maker-checker approvals, triggers,
  schedules (worker tick every minute), tested functions - in our own interpreter, no eval.
- **Sign-in (B):** email + password (PBKDF2), MSG91 phone OTP, sessions with sign-out everywhere, staff TOTP 2FA, DPDP
  consent / export / delete. Google / Apple exist only for native apps.
- **Outgoing calls (B):** declared actions with her approval bound to a hash, sealed secrets, inbound signed webhooks -
  but managed only under `/api/apps/{ref}/connect/*`; the Studio's Integrations pane only sends chat asks.
- **Backups (B):** a journal of every write + daily snapshots + point-in-time restore by her tap + ZIP export.

### Where Hoola is already stronger than Lovable (keep)
- Rules that cannot be written wrong (fixed words, enforced server-side) - the CVE-2025-48757 class cannot happen.
- Point-in-time restore from a write journal (Lovable: daily backups only).
- Data-loss migrations and outgoing actions need HER tap, bound to a hash (Lovable: Always allow by default).
- Maker-checker workflows, SLAs, formulas, OTP, staff 2FA, sessions, DPDP in the box.

---

## 3. The gaps that matter, worst first

1. **The designed screens are never wired to data.** A portal's `screen_dashboard` / `screen_table` / form sections are
   static HTML with invented `data-sample` rows and dead buttons; nothing in `hoola-app.js` replaces them with live
   data. The only real data screens are the generic `/account/` and `/admin/` shells, and launch is blocked while a sample
   screen remains. This is why "Build the ISP portal" still does not give a working portal with its data. (Lovable: the
   agent writes components that query the real tables; sample data only until she connects the backend.)
2. **Drafts write into the LIVE site's data.** `drafts.create` copies the site's `app` column including `link`, and
   `applink.project()` resolves the data project from that link - so a draft of a linked site reads and writes the same
   `app:<pid>` rows, while the draft tells her "It has its own data". (Read from `site/drafts.py:87-104` and
   `site/applink.py:36-52`; not run.)
3. **No preview dataset for websites.** The Studio preview writes real rows and creates real members (only React apps on
   path C have preview / live keys).
4. **No rule tests for websites.** Path C plays every list's rules as visitor / owner / other member / admin
   (`saboot.rule_tests`); path B - the live path - has none, and no publish scan of its rules.
5. **Three backends, two schema systems.** B (`backend._apply_ops`) and C (`cloud.apply_changes`) use different op names
   and type sets; C lacks OTP, 2FA, sessions, consent, files, refs, logic, schedules, connectors, secrets and backups
   (Cloud rows are not journaled at all).
6. **The owner cannot run her backend from the Studio.** The Cloud pane is a read-only table + members; backups,
   connectors, secrets, limits and logic live under `/api/apps/*` with no Studio screen.
7. **Websites have no Google sign-in, no file storage buckets, no transactional email** beyond OTP SMS.
8. **Two gates live in prompts, not code:** her own chat agent can apply logic / architect drafts (only non-owner actors
   are refused), and Cloud's `confirm_public` is set by the model.
9. **Two shops.** The website shop keeps its own tables and payment flow beside the app lists' orders / payments / stock.
10. **The ISP archetype is unused.** `appmaker/archetypes.py` has a rich `isp_ops` model (plans, connections, tickets,
    bills); the website path never reads archetypes, so an ISP portal's lists come only from the plan's `app_words`.

---

## 4. Plan (status 18 Nov 2026 below the table)

| Phase | What it does | Lovable lesson | Size |
|---|---|---|---|
| **B1 Live screens** | `hoola-app.js` renders every `screen_*` section from the real list the plan names (table, dashboard numbers, form, detail, board, calendar, approvals, sign-in); the AI writes the screen's design + which list / fields it shows, not fake rows; sample rows only in preview when the list is empty | components query real tables | large - fixes the ISP portal |
| **B2 Draft + preview data** | a draft gets its own `app:<pid>:d<n>` dataset; the Studio preview gets `app:<pid>:p` with marked sample rows and demo accounts; publish never copies rows; Accept moves structure, not data | drafts with example data; do NOT share live secrets | medium - fixes a live-data bug |
| **B3 Prove the rules** | path C's rule tests run for websites after every rule / list change and before publish; a FAIL blocks publish (unlike Lovable's skippable dialog) | test per rule change, scan on publish | medium |
| **B4 One backend** | path C moves onto B's engine (one schema log, one type set, one journal + backups, OTP / 2FA / sessions / logic for React apps too); path A code removed | one switch, one database | large |
| **B5 Backend tab in the Studio** | lists + rows editor, members, logs, backups / restore, secrets form, connectors, usage - on the existing `/api/apps/*` routes | the Cloud screen + secure secret form | medium |
| **B6 Sign-in, files, email** | Google sign-in for websites (`appmaker/sign.py` already verifies tokens), private-by-default file buckets, sign-in + transactional emails | default providers, private buckets, built-in emails | medium |
| **B7 Gates in code** | owner-applied logic / architect drafts and `confirm_public` require her tap token, not the prompt | (Lovable's weakness - stay stricter) | small |

Suggested order: **B1 + B2 first** (the portal she asked for, and the draft data bug), then B3, then B5, B6, B4, B7.

### Status (18 Nov 2026)
- B1 + B2 built as v0.989, B3 as v0.990, B5 as v0.992, B6 as v0.995.
- B4 built as v0.999.7: every App Engine (React) app has ONE App Sahayak project behind it (status `engine`, hidden from the
  app lists) and that project's preview twin for the Studio; `appengine/cloud.py` keeps the schema record (numbered runs,
  refusals, her data-loss tap) and writes each run into the project's lists; the app's calls go through
  `appmaker/backend.py` (journal + daily backups + restore, logic / approvals / functions, phone OTP, staff 2FA, sessions);
  rows and members under the old `ae:<app>:p|l` keys move on first touch and logins made before keep working. Path A:
  the v0.305 site engine no longer serves anything - an unlinked site joins the backend on its first public call
  (`applink._join_now`). Not merged: the two schema op vocabularies stay (Cloud's run ops on top, written into B's lists);
  the website shop's own tables (gap 9) and the ISP archetype (gap 10) are untouched.
- B7 built as v0.999.12 (gap 8 closed): the chat agent can no longer build an architect plan or put a website logic
  draft live, even as the owner after a haan in words - `architect_ok` puts the plan card (with 'Haan, build it') back
  in her chat (`architect.ask_tap`), `logic_ok` says where the draft waits (`applink.logic_ask_tap`); only the routes
  her buttons call build / apply. Hoola Cloud's `confirm_public` is dropped from the tool's changes and refused in
  `apply_changes(from_model=True)`; the change set waits as a 'Let anyone read this' card in the Studio's Cloud tab
  (`queue_public` / `public_run`, POST .../cloud/changes {public_ok, confirm}). A test reads every agent module and fails
  if one calls a her-tap function. Still following her words in chat (not part of gap 8): plan / look picks, App
  Sahayak design approve, old-address redirects (moves_ok), enterprise run approve, approval decisions.
  Every B phase (B1-B7) is now built.
- B8 built as v0.999.13 (gap 10 closed): a website plan whose words name a business App Sahayak already models (ISP / FTTH,
  CRM, school ERP, HRMS ... 43 archetypes) drafts its data from that model (`site/basemodel.py` match / lists / missing): the
  data draft reads it as `starting_model` (the ISP model = internet plans, subscribers, customers, OLT / PON / ONT, fiber
  routes, tickets, work orders, sales orders, invoices, payments ...), keeps its keys and types, renames to her words, drops
  what the site does not need; the plan card's Data part says "Started from Hoola's ISP / FTTH operations model" and names
  the model's own tables the draft left out (a note, never forced). Matching is whole words from each archetype's own word
  list, in code; a plan with no known business is drafted as before.
- Gap 9 (two shops), her pick "Full merge, in steps". Step 1 built as v0.999.19: a website joined to its project shares
  ONE product list and ONE stock count with the app (`site/shopjoin.py`): the website's products are the app's products
  (`backend._base_products`, the phone app's content), the stock column moves once into the project's stock table and is
  not read again, every website checkout reserves from that count under the app's lock, cancels and failed checkouts give
  it back. Step 2 = website orders as rows of the app's Orders list; step 3 = old website orders moved once (their
  tracking links kept).
