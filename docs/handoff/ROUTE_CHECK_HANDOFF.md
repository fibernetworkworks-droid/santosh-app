# Handoff: Hoola Route check (v0.999.144)

Date: 27 Nov 2026. Status: merged to `main` (commit `c7a3d3bfe`), **not yet deployed**.

## 1. What this is

Hoola Route is the automation page at `/console/route`, built on the DHARA workflow engine.
It shipped as v0.999.92. The owner then asked:

> "Check every section and find the design and misplaced text, button etc. flaws. Also any
> backend functioning found missed, also fix this."

This release is that check. Every Route page was walked in a real browser (Chromium) at
computer width (1440 px) and phone width (390 px), in light and dark, against realistic
seeded routes. Every endpoint was read against the engine. Every flaw found was fixed.

It was built as 0.999.128. Other work took 0.999.128 to 0.999.143 on `main` first, so it was
re-numbered **0.999.144** on merge (pubspec `0.999.144+1139`). Both lines of work are kept.

## 2. Where it lives

| Part | File |
|---|---|
| Engine (step results, run list) | `server/app/agent/dhara_tools.py` |
| Route API (`/api/route/*`) | `server/app/route/api.py` |
| Page script | `server/app/static/console/route.js` |
| Page styles (block "v0.999.128 ROUTE CHECK") | `server/app/static/console/route.css` |
| Page shell | `server/app/static/console/route.html` |
| New tests | `server/tests/test_v0999_128_route_check.py` |
| Older Route tests | `server/tests/test_v0999_87_hoola_route.py` |
| Release notes | `docs/HISTORY.md`, section "v0.999.144 ROUTE CHECK" |

## 3. Backend faults fixed

1. **A failed code step counted as done.** When the Python sandbox returned `ok: False`, the
   step still passed, the run said "done" and the route said "Working". Now the step fails with
   the sandbox's error, and a timeout says so.
2. **A failed web request counted as done.** A 4xx / 5xx answer now fails the step
   ("the site answered 503").
3. **Runs filter lost rows.** The Runs page filtered by status *after* the 60-row limit, so
   older failed or waiting runs disappeared. `list_runs(status=)` now filters in SQL.
4. **Approve / Retry / Stop always said "done".** The engine can refuse (approval expired, run
   not waiting, already finished), but the page showed success anyway. Now only the state the
   tap asked for counts as success; anything else returns **409** with the engine's own reason.
5. **Wrong approval question in Needs you.** It showed the route's last approval step, not the
   one the run is parked on. It now reads the run's cursor step.
6. **Old failures stayed in Needs you.** A failure now leaves the list once a later run of the
   same route exists (only each route's latest run counts).
7. **Never-run routes showed "Working".** They now say "Waiting for data" (webhook), "Waiting
   for its time" (schedule) or "Not run yet" (manual); a stopped last run says "Last run stopped".

### New endpoints

- `POST /api/route/routes/{id}/address`: makes a new webhook address for a webhook route and
  shows it **once**, because only its hash is stored. The old address stops working, so the
  page asks before making one. Non-webhook routes get 400.
- `DELETE /api/route/routes/{id}`: deletes a route and its runs. The body's `confirm` must equal
  the route's name (otherwise 400). Refused with 409 while a run is queued, running, sleeping or
  waiting for approval.

## 4. Page faults fixed

- **Phone:** tables become one card per row with labelled cells; the sidebar becomes a compact
  sticky top bar; the flow reads top to bottom; no page scrolls sideways at 390 px (tested).
- **Flow drawing:** if / else now shows both branches ("If yes" / "If no") with the test on the
  node; loops show the steps they repeat ("For each item"). Both were invisible before.
- **Step details:** plain labelled rows (kind, question, message, address, value, what happens
  if it fails); only arguments, request body and code appear as code blocks.
- **Route header:** title, status and description stacked; On / Off with its word; "Change it"
  opens a box on the page (no browser prompt); "Delete route" at the foot with an on-page
  "Yes, delete" / "Keep it".
- **Lists:** search box on All routes; "Switch back on" in Needs you for a route switched off
  after errors; KPI bars only where they show a share; the "need you" card opens Runs.
- **Run log:** approved / retried rows are named; outputs are folded behind "What it gave back"
  and pretty-printed.
- **Tap targets:** the On / Off switch has a 48 px tap area with the same look.

## 5. Tests and checks

- `server/tests/test_v0999_128_route_check.py`: 6 tests. They cover a failing code step, a
  503 web step, the SQL filter, the API end to end (statuses, waiting question, 409, stale needs,
  address, delete), page source pins, and a Chromium walk at 390 and 1440 px.
- After the merge with `main`: **84 passed** across the route check, Hoola Route, DHARA, console
  version pins, routines and the newest Firm Mode (F7) suite.
- The browser walk needs `HOOLA_CHROMIUM=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome`.
- Already red on untouched `main`, not from this work: crawl jobs (x10), officehours, magic21
  and crew version pins.

Run them with:

```bash
cd server && HOOLA_CHROMIUM=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome python -m pytest -q tests/test_v0999_128_route_check.py tests/test_v0999_87_hoola_route.py tests/test_v0502_dhara.py
```

## 6. What is not done / not verified

- **Not deployed.** This session cannot start GitHub Actions (403). The owner must run
  **Actions > VPS ops > deploy**. No new Python packages are needed.
- **Not verified on her server** or in her own browser.
- The phone's nav row in the top bar scrolls sideways *inside itself* by design; the audit
  lists it as "past the right edge", which is expected.
- Not built (unchanged from v0.999.92): drag-and-drop editing on the canvas, sub-routes,
  form / chat triggers, MCP.

## 7. Notes for the next session

- Test runs write runtime files under `server/data/` (`modelprofile/`, `pipeline/`,
  `pc_lessons.json`). Delete them; never commit them.
- Version ritual: `server/app/main.py` APP_VERSION + story, `pubspec.yaml`, the pin sweep across
  tests and `?v=` stamps in console HTML, the story pin in `test_v0475_console_frames.py`,
  then CLAUDE.md, `docs/HISTORY.md`, `docs/WORKLOG.md`.
- If `main` has taken your number, re-number on merge and keep both works (REBASE PROTOCOL).
- The audit script used for the walk was a scratch file; to repeat the walk, seed routes with
  `dhara_tools.dhara_save` (router + approval, if/else + loop + failing web request, a webhook
  route, a failing code step, a long name) and photograph each page at 1440 and 390 px.
