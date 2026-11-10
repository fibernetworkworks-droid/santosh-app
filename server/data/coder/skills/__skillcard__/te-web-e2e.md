---
name: te-web-e2e
description: Web E2E plan - Playwright, k6 load, frame diff
---
GOAL: Hoola ke web E2E ka upgrade PLAN likhna hai - filhaal Hoola ka apna
E2E sirf the pytest suite hai (server tests, module lane path se);
browser E2E, load test, visual regression abhi nahi hain. Ye skill ek
plan banati hai teen UPGRADES ka. Syllabus: mxschmitt/awesome-playwright
(Playwright patterns/tools ka curated catalog), k6 ke official docs
(load scenarios, thresholds), aur visual-regression catalogs -
generically koi bhi snapshot/pixel-diff reference chalega. Har naya
cheez pehle LAB (prayog/devlab) me, repo me tab jab owner bole.

ABHI KA SETUP (ye doors asli hain, use karo): qa, qa_dekho, jaanch,
hoola_jaanch, browser_check, consent_jaanch, hoola_frames, pylab,
prayog, devlab. Server-side testing the pytest suite me chalti hai.
browser_check ek light smoke hai - poora user-flow E2E nahi. Jo abhi
mila hai usi se kaam karo; jo nahi mila wo plan me likha jaayega.

UPGRADE 1 - PLAYWRIGHT UI E2E: Hoola ke apne web UI ke flows automate
karo: login -> desk -> skills. Pehle prayog/devlab me ek dummy page ke
against script likho; awesome-playwright se uthao - role/name wale
selectors pehle, fixtures, tracing, web-first assertions. Coordinates
wala pixel-click kabhi nahi. Install = ask_approval (browser binaries
bhi dependency hai); repo me entry sirf owner ke boalne pe. Plan me
likho: kaunse flows, selectors ki priority, traces/videos kahan
save honge, CI me kaunsa door chalega (abhi browser_check).

UPGRADE 2 - K6 LOAD FOR THE VPS: campaign peaks se pehle VPS ki
capacity jaanna zaroori hai. k6 docs ke scenarios follow karo -
smoke, ramping-vus, stress. Chalega SIRF off-peak window me, operator
se slot lekar; prod ko peak me load test karna kabhi nahi. Pehle
devlab me chhota dry-run, phir real VPS pe staged run. Har run ke
numbers PRINT karwao: p95 latency, RPS, error rate, saturation.
Printed output hi evidence hai - yaad-dasht nahi. Plan me thresholds
bhi likho: kya red hai (error>1% jaise), kya green, aur kis ko
report hoga.

UPGRADE 3 - VISUAL REGRESSION FOR HYPERFRAMES: same HTML do baar
render karo hoola_frames se; dono frames ko pylab me pixel-diff
karo; approved baselines ek golden frames folder me rakho. Diff
threshold set karo (anti-aliasing noise ke liye) aur har diff ka
printed report rakho - naya frame vs golden, pixel count, region.
Golden update sirf written reason ke saath hoga ("copy ne change
manga", "font fix hua") - "bas thoda alag lag raha tha" reason nahi
hai.

PLAN FORMAT: teen upgrades ek jagah - har ek pe label: ABHI USE KARO
(qa/jaanch/browser_check + the pytest suite), LAB ME (prayog/devlab
pilot), ya PLAN ME (repo + owner approval pending). Har upgrade ke
saath acceptance criteria aur rollback likho. Yaad rakho: ye PLAN
skill hai - mojooda doors se mojooda kaam, kal ke tools plan me.

NEVER: bina ask_approval repo me naya dependency (Playwright, k6,
kuch bhi); prod VPS pe load test peak hours me; flaky test ko
'chalta hai' keh ke re-roll - flaky red bhi red hai, use fix karo
ya plan me quarantine likho; golden frames bina update reason ke
overwrite; bina printed diff ke 'UI same hai' bolna - pixels ka
sach pylab ka diff output hai, aankh ka andaaz nahi.
