---
name: te-web-e2e
description: Web E2E plan - Playwright, k6 load, frame diff
when_to_use: end to end tests, e2e, playwright, load test, k6, website testing, visual regression, browser tests
---
GOAL: write the upgrade PLAN for Hoola's web E2E - today Hoola's own
E2E is only the pytest suite (server tests, by module path); there is
no browser E2E, load test or visual regression yet. This skill builds
a plan for three UPGRADES. Syllabus: mxschmitt/awesome-playwright (a
curated catalog of Playwright patterns / tools), the official k6 docs
(load scenarios, thresholds), and visual-regression catalogs - any
generic snapshot / pixel-diff reference will do. Every new thing goes
into the LAB (prayog / devlab) first, and into the repo only when the
owner says so.

TODAY'S SETUP (these doors are real, use them): qa, qa_dekho, jaanch,
hoola_jaanch, browser_check, consent_jaanch, hoola_frames, pylab,
prayog, devlab. Server-side testing runs in the pytest suite.
browser_check is a light smoke test - not a full user-flow E2E. Work
with what exists today; what does not exist goes into the plan.

UPGRADE 1 - PLAYWRIGHT UI E2E: automate the flows of Hoola's own web
UI: login -> desk -> skills. First write the script against a dummy
page in prayog / devlab; take from awesome-playwright - role / name
selectors first, fixtures, tracing, web-first assertions. Never a
pixel click by coordinates. Install = ask_approval (browser binaries
are a dependency too); an entry in the repo only when the owner asks.
Write in the plan: which flows, the selector priority, where traces /
videos are saved, which door runs in CI (today browser_check).

UPGRADE 2 - K6 LOAD FOR THE VPS: the VPS capacity must be known
before campaign peaks. Follow the scenarios in the k6 docs - smoke,
ramping-vus, stress. It runs ONLY in an off-peak window, in a slot
taken from the operator; never load-test prod at peak. First a small
dry run in devlab, then a staged run on the real VPS. Have every
run's numbers PRINTED: p95 latency, RPS, error rate, saturation.
Printed output is the only evidence - not memory. Write thresholds
in the plan too: what is red (such as error > 1%), what is green,
and who gets the report.

UPGRADE 3 - VISUAL REGRESSION FOR HYPERFRAMES: render the same HTML
twice with hoola_frames; pixel-diff the two frames in pylab; keep
approved baselines in a golden frames folder. Set a diff threshold
(for anti-aliasing noise) and keep a printed report of every diff -
new frame vs golden, pixel count, region. A golden is updated only
with a written reason ("the copy asked for a change", "a font was
fixed") - "it just looked a bit different" is not a reason.

PLAN FORMAT: the three upgrades in one place - each one labelled:
USE NOW (qa / jaanch / browser_check + the pytest suite), IN THE LAB
(a prayog / devlab pilot), or IN THE PLAN (repo + owner approval
pending). Write acceptance criteria and a rollback for each upgrade.
Remember: this is a PLAN skill - today's work through today's doors,
tomorrow's tools in the plan.

NEVER: add a new dependency to the repo without ask_approval
(Playwright, k6, anything); load-test the prod VPS in peak hours;
re-roll a flaky test saying "it is fine" - a flaky red is still red,
fix it or write a quarantine into the plan; overwrite golden frames
without an update reason; say "the UI is the same" without a printed
diff - the truth about pixels is pylab's diff output, not a guess by
eye.

ALSO ASKED AS (Hinglish asks this skill answers): meri website ka load test
karna hai, website test karwao, browser test likho
