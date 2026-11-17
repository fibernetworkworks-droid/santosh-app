# Lovable Cloud - the DATA side of the backend (read 17 Nov 2026)

Research ask: exactly HOW Lovable's built-in backend ("Cloud") handles data - database, migrations, access rules,
auth, storage, test vs live, backups, logs, limits, price. Lovable's own docs first. Companion to `00_INDEX.md` s.6,
which this file deepens. Read-only research; nothing in Hoola changed.

Source tags:
- **[docs]** docs.lovable.dev pages, fetched as `.md` on 17 Nov 2026 (index: docs.lovable.dev/llms.txt), and the
  docs changelog (docs.lovable.dev/changelog.md). Lovable's own words.
- **[leak]** the leaked agent prompt (github.com/x1xhlol/system-prompts-and-models-of-ai-tools, Lovable/). Not official.
- **[3rd]** blogs, CVE databases, vendor write-ups. Directional only.
- **[inferred]** my reasoning; no source says it.
- lovable.dev (home, pricing, blog) sits behind a Cloudflare challenge. It was NOT fetched and not worked around.

Naming: the docs now call it the **"built-in backend"**; the product still says **Cloud** in places ("Cloud credit
usage", the **Enable Cloud** permission) and "Lovable backend services" in workspace settings [docs]. It "utilizes
Supabase's open-source foundation" [docs] - i.e. a managed Supabase stack (Postgres + GoTrue auth + Storage + Realtime +
Deno edge functions) that the user never sees as a Supabase project [inferred from env names `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY` listed in the Secrets page, docs].

---

## 1. Enabling Cloud

- Cloud is **on by default for the workspace** [docs]. The user does not switch it on in advance. When an ask needs a
  backend (accounts, saved data, uploads, emails, payments, schedules, AI), Lovable "enables the backend automatically or
  asks for your approval in the project chat first", depending on the **Enable Cloud** permission [docs].
- **One switch provisions three things.** "The database, user accounts, and file storage run together on one backend.
  Enabling any one of them provisions all three." Pausing the database pauses all three; removing it deletes all three
  [docs]. The Database view shows an **Enable** card until then [docs].
- **Not from a draft.** "Lovable can't enable the backend from inside a draft" - only from the main version [docs].
- **Region**: three choices - Americas, Europe, Asia Pacific [docs]. Order of choice: (1) a workspace default region
  (Business / Enterprise admins; members cannot override); (2) the user's own "Where project data is stored" setting
  (default "Closest to me") [docs]. With **Enable Cloud = Ask each time** the region is shown on the approval card and
  can be changed there; with **Always allow** it is used silently [docs]. **Locked for ever**: "You cannot change a
  project's region after the backend is enabled" [docs]. Country regions (Germany, Japan, US-East) = Enterprise on
  request [docs]. The settings row shows the region in the host's words (e.g. "Europe (Frankfurt)") plus the Postgres
  version [docs].
- **What the user sees afterwards**: a **More** menu with Database, Users, Storage, Edge functions, Jobs, Secrets,
  Logs, Usage (+ AI) [docs].
- Remix copies structure only (no rows, no users, secret names without values) [docs]. No one-step move between
  Cloud and own Supabase in either direction [docs].

### Agent permissions (the Always / Ask / Never list) [docs]

Each permission has **Always allow / Ask each time / Never allow** ("does not perform the action and says so in the
project chat"). Defaults:

| Permission | What it covers | Default |
|---|---|---|
| Enable Cloud | create the backend (DB + auth + storage); required before the rest | Always |
| Read database | read data | Always |
| Read analytics | query logs to investigate | Always |
| Run security checks | automated DB checks, "Not a full audit" | Always |
| Modify database | "schema and policy changes via SQL migrations. Updates generated types." | Always |
| Execute backward incompatible database migrations | drop / rename table or column etc. With Ask: "shows you the SQL and asks for your approval" | **Never** |
| Change data | add / update / delete rows | Always |
| Read project info | config + environment | Always |
| Configure auth | e.g. signup policies | Always |
| Read backend logs | backend service logs | Always |

- Set in **Account settings -> Preferences -> Agent permissions** (per user, all connectors in one list) [docs].
- Enterprise policy **Restrict Lovable backend services** overrides Enable Cloud: an approval card, a request to admins
  [docs].
- Contrast worth noting: with the user's OWN Supabase project, "Schema changes run as reviewed migrations: Lovable
  writes the SQL, shows it to you, and asks for your approval ... before running it" [docs]. On Cloud the default is
  Always allow - no per-migration review unless the user changes the permission [docs + inferred].

Sources: https://docs.lovable.dev/features/cloud.md · https://docs.lovable.dev/features/database.md ·
https://docs.lovable.dev/integrations/supabase.md · https://docs.lovable.dev/features/secrets.md

---

## 2. Database

### Tables from plain words
- Managed **PostgreSQL**. "Describe the data your app needs in the project chat, and Lovable creates the tables and
  their structure" (docs example: clients + deals with stage and close date) [docs].
- Form asks (contact / booking / quote) create a table where "visitors can submit the form but cannot read, change, or
  delete a submission"; project editors read it in More -> Database [docs]. A form that delivers to a CRM gets no table,
  but Lovable "offers to store a copy as well, so a failed delivery does not lose the submission" [docs].
- CSV import: no import button; attach the file in chat and ask Lovable to add rows [docs].

### Migrations - format and tool
- Since **7 Oct 2026** [docs changelog] each structure change is a **Drizzle** migration file under
  `drizzle/migrations/` (one SQL file per change), with `drizzle/schema.ts`, `drizzle.config.ts` and the journal
  `drizzle/migrations/meta/_journal.json`. "Leave them as they are" [docs].
- Older projects: SQL files under `supabase/migrations/`; on that setup Lovable "applies only the change you asked
  for"; old files are left in place after a project moves to Drizzle [docs].
- Lovable also "updates the type definitions in your app's code, so the code matches the database" [docs]. File name
  not stated on the Cloud pages; on Supabase-style projects it is conventionally
  `src/integrations/supabase/types.ts` [inferred - not confirmed in these docs].
- Rules a migration must obey [docs]: no `BEGIN` / `COMMIT` / `ROLLBACK` ("Lovable rejects migrations that contain
  them"); some statements can't run in a transaction (e.g. `CREATE INDEX CONCURRENTLY`); no published size limit.

### How a run works (Drizzle projects) [docs]
- **All pending migrations in ONE run, all-or-nothing**: "If one statement fails, Lovable discards every change from
  that run and applies nothing."
- **Runs never overlap**: "When two runs overlap, Lovable starts the second run only after the first one finishes."
  The app stays up, but a migration that changes a table "does lock it until the whole run finishes".
- **A run may include more than you asked**: earlier pending files - including ones pushed from Git weeks ago - go in
  the same run. "Your approval covers the SQL shown in that request, not the whole run." "A merged pull request is a
  code review, not an approval to change your database."
- **Journal + date gate**: a Git-added file is applied only if `_journal.json` lists it, with a date AFTER the last
  applied migration; an earlier-dated file is skipped "with no error and no second attempt". A raw SQL file copied in
  without a journal entry is never applied.
- **Timeout != failure**: "Lovable can still apply the change afterwards" - check ("Was my last database change
  applied?") before asking again, so it is not applied twice. Some paths auto-retry after a server error or timeout.
- **Record kept in the DB**, separate from the files: a Drizzle table storing a SHA-256 of each file as run; editing a
  file later does not change what was applied. Old setup: Supabase migrations table, version + name, no hash.
- Migrations run on a privileged connection that may also create policies on `storage.objects`; app code uses other
  connections.

### Breaking changes [docs]
- Refused by default: **dropping or renaming a table or column, changing a column's type, adding a required column
  without a default**. Instead Lovable "reaches the same result by adding to your database, for example by adding a new
  column and copying the data over. The old column stays in place." (expand-only by default)
- To allow them: set **Execute backward incompatible database migrations** to Ask (SQL shown, user approves) or Always.
- Undo: often possible with a new migration, but it "does not recover deleted data"; "Do not assume that each migration
  leaves a restore point behind" [docs].

### The table / row editor (More -> Database) [docs]
- Table list with approximate row counts; database views listed read-only.
- Double-click to edit a cell; column filters by type; **Add row** form (DB-filled columns like id / timestamps left
  out); **Edit row** only with a single primary key; multi-select **Delete** with a count + confirm ("cannot be
  undone"); **Export CSV** of all rows matching the filters; **Refresh** (not live); 10 / 25 / 50 / 100 rows a page.
- Warning on the page: "Edits apply directly to your project's database, the same database your published app uses."
- **SQL editor** (Manage -> SQL editor): autocomplete; destructive statements (`DELETE`, `DROP`, `TRUNCATE`, `ALTER`,
  `UPDATE`) need a confirm; SQL run here is NOT recorded as a migration; several statements are "not guaranteed to run
  in one transaction"; Cancel only stops the browser wait.
- **Extensions**: fixed allow-list (pg_cron, pg_net, pg_trgm, vector, postgis, pgmq, ...); any other `CREATE
  EXTENSION` refused before it runs (API: 403 `unsupported_extension`); plain-SQL substitutes (citext -> unique index
  on `lower()`, hstore -> jsonb).

Sources: https://docs.lovable.dev/features/database.md · https://docs.lovable.dev/changelog.md (Oct 7, 2026)

---

## 3. Access rules (RLS) and the security scans

### How policies are written and seen [docs]
- Lovable writes **Postgres Row Level Security** policies itself "when it builds features that store user data". RLS
  covers tables, storage and realtime.
- **Policies view** (Manage -> Policies) is **read-only**: name, command (SELECT / INSERT / UPDATE / DELETE), applies
  to (role), rule expression (the SQL condition, expandable); filters All / Tables / Storage / Realtime. To change one,
  ask in chat ("Only allow users to see their own invoices.").
- Three DB roles: `anon` (not signed in), `authenticated`, `service_role` (server code; **RLS does not apply**). The
  publishable key in the browser is fine by design; RLS, not secrecy, protects data. Docs warn plainly: "A role shows
  only whether someone is signed in, not who the person is or whether they are an admin of your app. If a policy checks
  only for `authenticated`, every signed-in user gets the same access to every row" - owner comparison is needed.
- Server code on `service_role` "must check permissions itself"; "Lovable does not offer a separate, restricted
  database login for server code".
- DB password managed, never shown; rotation on request after a confirm [docs].

### App roles (admin etc.) - how they are stored
- **Not found in Lovable's current docs.** No page names a `user_roles` table or a `has_role()` function.
- The leaked agent prompt fetched today does not mention roles either [leak].
- Third-party guides describe the common Lovable-generated pattern: roles in a SEPARATE `user_roles` table (never a
  column on `profiles` the user can edit), checked by a `SECURITY DEFINER` function such as `has_role(uid, role)` with a
  fixed `search_path`, used inside RLS to avoid recursive policy checks [3rd: witscode, rapidevelopers]. Known failure
  modes they report: role on a `profiles` row the user can update (self-promote to admin), roles read from
  `user_metadata` in the JWT (user-editable), client-only role checks [3rd].
- What Lovable's docs DO say instead: the Deep scan checks "that privileged actions check the caller's role rather
  than only that they signed in", and that server code honours the DB ownership rules [docs]. Drafts create demo
  accounts "with the profile and role details your app expects, which can include an admin role" [docs] - so a
  profile + role structure is the norm [inferred].

### Quick scan vs Deep scan [docs]
- **Quick scan** - fixed checks "in seconds", runs **automatically on every publish** (when the publish dialog opens)
  and on demand: database review (tables without RLS, "access rules that let everyone through", leaked-password
  protection off, storage rules), npm dependency audit (only critical advisories become findings, EPSS-filtered), an
  MCP server exposed without auth; plus Wiz if connected.
- **Deep scan** - reviews ALL app code (usually 3-13 min, max 15): access control incl. server code that bypasses RLS,
  unauthenticated / abusable endpoints, injection (query, command, path, browser, email, AI prompt, spreadsheet),
  leaked secrets, payments / billing tampering, auth bypass, exposed personal data. Does NOT run automatically (except
  when publishing an MCP app that allows no-sign-in access). Free.
- Findings Critical / Warning / Info; **Ignore** needs a recorded reason; a per-project **security memory** (since
  18 May 2026) tells the scanner the access model and accepted risks [docs changelog].
- **What blocks publishing**: by default nothing - "Findings do not block publishing by default". On Cloud projects
  with unresolved critical findings, **Publish** opens a **Review security findings** dialog (up to 3 shown; Try to fix
  / publish anyway). Only the workspace setting **Block publishing with critical issues** makes it a hard block -
  default OFF, except new Enterprise workspaces Lovable creates [docs].
- **Auto-fix** (when enabled): a few Critical quick-scan findings ride along with each build request [docs].

### The CVE-2025-48757 lesson
- CVE-2025-48757: "insufficient database Row-Level Security (RLS) policy in Lovable through 2025-04-15 allows remote
  unauthenticated attackers to read or write to arbitrary database tables of generated sites" [3rd: NVD-derived
  listings]. Researcher Matt Palmer's scan: ~170 of 1,645 showcase apps, 303 endpoints; policies missing or effectively
  `USING (true)`; data read through the public anon key [3rd]. CVSS 9.3 per listings [3rd]. Framing disputed (platform
  flaw vs user-built config gap) [3rd].
- What changed after it (dates from Lovable's changelog): Apr 25 2025 - "Security Scan: Lovable now checks for
  vulnerabilities when you publish (if you're connected to Supabase)" [docs]; later the Basic / Deep scan profiles,
  auto-fix, publish-blocking workspace controls, Wiz + Aikido, security memory, and today's check for "access rules
  that let everyone through" (not just "a policy exists") [docs]. 00_INDEX notes the original scanner only checked
  that a policy existed [3rd, via 00_INDEX].
- Lovable has not published a full post-mortem [3rd]. Lovable's blog was not readable here (Cloudflare).

### Public forms that insert but cannot read [docs]
- Explicitly documented: form tables let visitors "submit the form but cannot read, change, or delete a submission";
  editors read them in the Database view. In RLS terms: an INSERT policy for `anon`, no SELECT / UPDATE / DELETE for
  `anon` [inferred from the docs wording + the role model].

Sources: https://docs.lovable.dev/features/database-access.md · https://docs.lovable.dev/features/security.md ·
https://docs.lovable.dev/features/security-view.md · https://docs.lovable.dev/features/publish.md ·
https://docs.lovable.dev/features/privacy-and-security-settings.md ·
https://docs.lovable.dev/tips-tricks/security-best-practices.md · https://docs.lovable.dev/features/drafts.md ·
https://www.superblocks.com/blog/lovable-vulnerabilities · https://cvefeed.io/vuln/detail/CVE-2025-48757 ·
https://dbugs.ptsecurity.com/vulnerability/PT-2025-23236 · https://witscode.com/blogs/lovable-rbac ·
https://www.rapidevelopers.com/md/how-to-build-lovable/user-permission-management

---

## 4. Auth [docs]

- "Add login" -> signup / login pages wired to the backend + RLS. Default methods when none are named: **email +
  password, Google, and "Sign in with Lovable"**.
- Providers: email, phone (SMS OTP via HER provider: Twilio, Twilio Verify, TextLocal, Vonage, MessageBird), Google,
  Apple, Microsoft (each "Managed by Lovable" with no setup, or own credentials), Lovable account, SAML SSO, OIDC
  (Auth0, Okta, Entra, Keycloak). Business / Enterprise admins can block methods workspace-wide.
- **Users view** (More -> Users): signups chart, searchable list, Raw JSON per user; Add user = invite or create
  with password (auto-confirmed), no hash import; Delete user (irreversible).
- Sign-up controls: **Disable sign-up**; **Enable anonymous users** (guest flows).
- **Email confirmation**: setting **Auto-confirm email** (off = must verify before sign-in) and **Secure email
  change** (both addresses confirm). Docs advise keeping confirmation on for real apps. The default value of
  auto-confirm is NOT stated in the docs [not found].
- **Password rules**: min length (floor 6, 8+ recommended); required character classes (default "No required
  characters"); **Password HIBP check** (Have I Been Pwned - the docs call it "the highest-value setting"); require
  re-authentication for password change. HIBP being off is a Quick scan finding.
- OTP / magic links 60 s - 24 h, 6-8 digits; auth email cap 1,000 / h default (max 32,767).
- **Redirect URLs on publish**: on Cloud, Lovable keeps Site URL + redirect list updated - Site URL set to the
  published address on publish (unless already her own domain), custom domains added when connected. Up to 50 redirect
  URLs, `/**` wildcards, custom schemes for mobile; `localhost` rejected (use 127.0.0.1); other Lovable-domain addresses
  are removed on each update. Own-Supabase projects: Site URL is hers to set.
- **Profiles table pattern**: not documented as such on the Cloud pages [not found]; drafts seed demo accounts "with
  the profile and role details your app expects" [docs], so a per-user profile row is the usual generated shape
  [inferred].
- **Sessions**: access token (short, fixed - no setting) + refresh token, both stored on the device. No setting for
  session length or idle timeout. Sign-out / delete ends the session but an issued access token "can keep working until
  it expires"; for sensitive actions ask for a server-side **session check**.
- Signing keys HS256 or ES256 (switched to ES256 for MCP / OAuth-server use, after a confirm).

Sources: https://docs.lovable.dev/features/authentication.md · https://docs.lovable.dev/features/email-auth.md

---

## 5. Storage and Realtime

### Storage [docs]
- Buckets, **Private by default** (access by RLS policies on `storage.objects`) or Public (anyone with the URL).
- **Public buckets are blocked by default on ALL plans** by the workspace setting **Block public storage buckets**
  (default Enabled; all new buckets forced private); an owner / admin can lift it. Docs recommend private + signed URLs.
- Bucket names: lowercase, digits, hyphens, 3-63 chars, not renameable; delete only when empty; irreversible.
- File browser (upload, folders, rename, delete, zip download); **Copy URL** = permanent URL (public) or a **1-hour**
  signed URL (private).
- Upload limit **2 GB default, max 5 GB**, per-bucket lower limits on request; changing it needs project-settings
  permission and Lovable asks approval.
- Storage is NOT in database backups or exports; it keeps billing while paused.

### Realtime [docs]
- Listed as part of the backend ("live updates such as chat messages or notifications"); RLS policies cover realtime
  (a Realtime filter in the Policies view); Realtime logs (WebSocket connections and subscriptions); billed as its own
  usage category.
- **No dedicated Realtime page exists** in the docs index; channel / presence / broadcast mechanics are not
  documented [not found]. Underneath it is Supabase Realtime [inferred].

Sources: https://docs.lovable.dev/features/storage.md · https://docs.lovable.dev/features/database-access.md ·
https://docs.lovable.dev/features/logs.md

---

## 6. Test vs Live, preview vs production data

- **Today (Nov 2026) every Cloud project runs on ONE database**: "the data you work with while building is the data
  your published app runs on" [docs]. The editor preview and the published app read and write the same rows
  [docs: "the same database your published app uses"].
- **History of Test / Live** [docs changelog + migration guide]:
  - **Feb 5, 2026**: "Test and Live environments (Beta)" - separate isolated databases, free in beta; publish once to
    create Live; Test = build workspace; **Live = production, "read-only for Lovable"**; publish pushed code +
    structure to Live, "Test data stays in Test. Live data never gets overwritten."
  - **Mar 24, 2026**: removed for new projects ("no longer available for new Lovable Cloud projects ... cannot be
    re-enabled once disabled").
  - **Sep 14, 2026** owners emailed; **Oct 23, 2026** split retired - Test DB detached, project on a single DB;
    **Dec 1, 2026** Test DBs deleted for good. Publishing carried structure (schema, bucket definitions incl.
    public / private, RLS policies, edge functions) but never data, users, files or auth settings, so owners had to move
    Test data to Live themselves (export + upload, or CSV per table).
- **The replacement = drafts** (changelog Nov 16, 2026: "Test database changes in a draft") [docs]:
  - A draft on Cloud "usually has a backend of its own, filled with example data"; a fixed banner says so. Rolling out
    gradually; some drafts still share the live backend (own-Supabase projects, unsupported extensions, paused DB,
    structure copy failed) - then data changes hit live at once.
  - Own-backend draft: live structure copied; example rows or `db/seed.sql`; two **demo accounts** (one may be
    admin), auto sign-in; no files; own function copies; **secrets and services use LIVE values** (real API calls).
  - Real records copied in only on request (asks before personal data; never user accounts).
  - **Accept** = structure changes (tables, columns, policies, storage settings, functions) applied to the LIVE
    database immediately, before publish; data is never copied; the draft's rows, accounts and files are deleted. Pages
    reach visitors only on publish, while the old pages already run on the new structure.

Sources: https://docs.lovable.dev/features/environments.md · https://docs.lovable.dev/features/drafts.md ·
https://docs.lovable.dev/changelog.md (Feb 5, Apr 2 [notes the Mar 24 removal], Nov 16 2026)

---

## 7. Backups, restore, logs, limits, price

### Backups and restore [docs]
- **One automatic backup per day, kept ~14 days**; listed in UTC under Manage -> Backups. Self-serve restore since
  **May 18, 2026** (before: via support) [docs changelog].
- **No point-in-time recovery**: "You can restore any listed daily backup, but not a moment between two of them";
  **no on-demand backup** from that page.
- Restore = schema AND data back, irreversible, DB down "a few minutes", any editor can do it. It rolls back user
  accounts and storage *records* too (newer files vanish from the app); jobs and email sending "not reliably" restored.
- **Export**: full DB incl. auth users + password hashes as a Postgres `.backup` (`pg_restore`, PG 16+); not files,
  functions, secrets or keys; DB <= 15 GB, file <= 5 GB, one per 24 h. No user import of a `pg_dump`; no direct DB
  connection.

### Logs the user can read [docs]
- More -> Settings -> Logs: Edge logs (default), Function edge logs, Function logs, Authentication logs, PostgreSQL
  logs, Realtime logs, Storage logs, and Server logs (TanStack Start projects).
- Search, ranges up to **5 days** (or absolute), status filter, **not live**, JSON download. Retention not stated;
  "not audit evidence" on their own.

### Capacity, pausing, limits [docs]
- Instance sizes Tiny ... X-Large (**Free = Tiny only**); resize = brief restart, estimated monthly cost shown;
  high-load notices send her to "fix slow queries first".
- **Auto-pause after about 7 days without activity**; opening the project wakes it; jobs keep a project "active"; a
  self-paused or credit-paused backend needs **Wake up**; traffic does not wake it. Free workspaces: a published app
  with no visits / owner login for 12 months may be unpublished.
- Out of credits: the published site's pages keep serving, but backend services (DB, storage, auth) pause and AI stops
  [docs].

### Price [docs]
- One credit balance for building, hosting, backend and in-app AI. Backend + AI = **Run credits**, broken down into
  Database server, Database storage, AI, Compute, Network, Storage, Realtime (More -> Usage, 30 / 90 days).
- Monthly grants ("temporary offering, subject to change"): **20 credits Cloud + 4 credits AI + 1 credit connectors**
  on Free / Pro / Business; no rollover; Free resets on the 1st at 00:00 UTC, paid plans on the billing cycle.
  Enterprise does not see the coverage total.
- **No per-unit price** (per GB, per hour, per credit in currency) is published on these pages [not found]. Earlier
  (Oct 2025 - 2026) third parties quoted "$25 / month free Cloud + $1 / month free AI", usage-based beyond that
  [3rd: zite, nocode.mba]; not current per the docs.

Sources: https://docs.lovable.dev/features/database-backups.md · https://docs.lovable.dev/features/logs.md ·
https://docs.lovable.dev/features/database-performance.md · https://docs.lovable.dev/features/database-pause-remove.md
· https://docs.lovable.dev/features/project-usage.md · https://docs.lovable.dev/introduction/credits-and-usage.md ·
https://docs.lovable.dev/introduction/out-of-credits.md · https://www.zite.com/blog/lovable-pricing

---

## 8. What could not be found or verified

- The `user_roles` / `has_role()` SECURITY DEFINER pattern - only in third-party guides, not in Lovable's docs or the
  leaked prompt read today.
- Whether **auto-confirm email** is on or off by default.
- The exact path of the generated types file on Cloud.
- Realtime mechanics (channels, presence, broadcast) - no page.
- Log retention period; any currency price per credit / per resource.
- Lovable's own account of the CVE-2025-48757 fix (blog behind Cloudflare; no post-mortem per third parties).
