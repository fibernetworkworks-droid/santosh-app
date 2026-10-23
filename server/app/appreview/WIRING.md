# WIRING for appreview
summary: App Review Sahayak (static review of her own APK / AAB / source ZIP / GitHub repo / website: manifest, permissions vs Play's Oct 2026 rules (target API 36, restricted permissions, 16 KB pages, Data safety, account deletion, Families), signing, network security config, embedded keys, tracker / payment / AI SDKs, DPDP + RBI notes, website headers / TLS / exposed files on her verified domain; each risk in plain Hinglish with evidence + fix + code snippet; PDF / Excel report + fix list; re-review shows fixed / still open / new; fix list to the Developer Sahayak only on her tap)
db: app.appreview.models
router: app.appreview.api            (make_router(require_key, current_tenant); all routes under /api/appreview, key-protected; no public routes)
tools: app.agent.appreview_tools     (APPREVIEW_TOOLS / APPREVIEW_LABELS / APPREVIEW_HANDLERS) ; voice: yes (app_review_dekho only; a review of a big file can take a minute, start it from chat / the app)
employee: duty app_review = [app_review, app_review_dekho, app_check, file_read] {label "App reviewer", say "apni app / code / website ki suraksha + Play / App Store / DPDP policy jaanch, saral bhasha mein samjhana, fix list (developer ko bhejna aapki haan se)"} ; role app_reviewer {label "App reviewer", duties [app_review, records, research]} ; preset app_reviewer {label "App / website review", role app_reviewer, rules ["App ya code kabhi chalana nahi, sirf padhna", "App / code kisi third party ko upload nahi karna", "Token / password chat mein kabhi nahi", "Fix list developer / Developer Sahayak ko sirf owner ki haan se"]} ; READ tools: [app_review_dekho]
  - staff (staff:<id>) may start reviews and read; owner-only: mark, handoff, settings (tool refuses; API is the owner's app). Customers refused.
  - neighbour (devsahayak): on her tap `handoff_decide` calls `app.devsahayak.service.tasks_from_review(tenant, {review, title, target, tasks:[{n, key, title, severity, area, masvs, why, where:[file:line], do, snippet, done_when}]})` if that function exists; returns whatever it returns (e.g. created task ids). If it does not exist yet the card result says so and gives the fix list markdown. Suggest the devsahayak builder add exactly that function (each task -> one dev task with "done_when" as the acceptance check; changes to her code still follow devsahayak's own tap rules).
push: appreview_handoff -> ("App review: aapki haan chahiye", "{say}")
push: appreview_alert -> ("App review", "{say}")
  (appreview_report: push optional -> ("App review taiyaar", "{say}"); a review is usually started by her in the app, so no push needed)
worker: app.appreview.service.tick   (call once an hour or every minute; it runs its daily work once per tenant per day: removes uploads older than 7 days, one `appreview_alert` per app whose latest review targets below Play's current API (at most every 30 days per app)) — `await asyncio.to_thread(appreview.tick)`
prompt: APP REVIEW: when she asks "meri app / code / website check karo", "Play par reject kyun", "policy theek hai?" -> `app_review` (action=file with her upload / chat file_id, repo, or web). It only READS (never runs the app, never uploads it anywhere). Tell her the score, the top 2-3 risks in simple words and the fix; offer the report (`action=files`). A GitHub token is added only in the app (never ask for it in chat). Sending the fix list to the Developer Sahayak / her developer is ONLY a card for her tap. For a stranger's APK safety check use app_check (App Jaanch), not this.
persona: App review ke baad score aur sabse gambhir 2-3 baatein saral shabdon mein bolo, poori list chat / app mein; token kabhi mat maango; fix list bhejna sirf uske card tap se.
flutter: AppReviewScreen in lib/ui/appreview_screen.dart (also AppReviewPage(app:, id:) and helper startReview(context, app, 'file'|'repo'|'web')) ; profile tile title "<name> · App reviewer" subtitle "Apni app / code / website ki suraksha aur Play policy jaanch, fix list" icon Icons.verified_user_outlined ; cards: appreview_report -> AppReviewReportCard (also in calls: yes; key by data['id'], updated in place) ; appreview_handoff -> AppReviewHandoffCard (also in calls: yes; key by data['id']) ; appreview_alert -> AppReviewAlertCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)`, `app.api!.uploadFile(...)` (exists), `Native.openExternal`, `app.aName`. Uses file_picker (already a dependency). The upload uses the existing `Api.uploadFile` multipart helper on POST /api/appreview/upload (nginx client_max_body_size must allow her APK size; the server caps at APPCHECK_MAX_MB).
features: app_review (always on: pure Python; REA is optional and only used as a second manifest reader when App Jaanch is configured)
env: APPREVIEW_DIR (default "data/appreview") = where her uploads live for 7 days. Reuses APPCHECK_MAX_MB (400) as the upload cap and the bazar vault (SECRET_KEY) to seal her GitHub token.
requirements: none (httpx, openpyxl, reportlab, cryptography already present)
android: none
claude_md: |
  ## v0.1xx App Review Sahayak: Hoola reviews HER app / code / website ("App reviewer" on the Employee page; extends App Jaanch)
  - Owner's spec: (1) checks an app's code for risks, (2) explains each risk simply, (3) suggests fixes. App Jaanch (v0.26, `app/appcheck`)
    stays the "is this stranger's APK safe?" check; App Review is for HER own app before Play / App Store / customers. Reused from
    appcheck (not edited): `analyze.sniff`, `base_apk`, `apk_signer` (v1/v2/v3 block + cert) and, when REA is installed, its locked-down
    `runner.Session` as a second manifest reader.
  - Server `server/app/appreview/{binfmt,rules,scan,models,service,api}.py`, tools `app_review` / `app_review_dekho`
    (`agent/appreview_tools.py`), duty `app_review`, role + preset `app_reviewer`, API `/api/appreview/*`, app Profile > App reviewer
    (`lib/ui/appreview_screen.dart`: Aaj / Reviews / Niyam + AppReviewPage), cards AppReviewReportCard, AppReviewHandoffCard,
    AppReviewAlertCard. Tests `server/tests/test_tech_appreview.py` (7; fixtures built byte by byte: binary AXML, aapt2 protobuf
    manifest, ELF headers, fake DEX string table, fake GitHub + website).
  - Inputs, static only (nothing is run, nothing uploaded to anyone): APK / AAB / XAPK (own upload `POST /api/appreview/upload`, kept
    7 days in `data/appreview/<tenant>/uploads`, or a chat file_id), source ZIP, GitHub repo (`/repos/{o}/{r}/zipball/{ref}`; public
    without a token, private with HER fine-grained read-only token typed only in the app, sealed with the bazar vault; classic tokens with
    repo / write scopes refused; the chat tool refuses any token-shaped text), website (passive GET of the home page + http->https; .git /
    .env / .DS_Store / phpinfo / server-status / backup files probed only on a domain she verified by DNS TXT `_hoola.<host>` =
    `hoola-verify=<token>` (checked over DNS-over-HTTPS) or `/.well-known/hoola-verify.txt`; public addresses only via `web._check_url`).
  - Readers (`binfmt.py`, pure Python): Android binary XML, aapt2 protobuf XML (AAB `base/manifest`), ELF PT_LOAD alignment, DEX class
    descriptors -> SDK prefixes, printable strings -> secrets / http URLs / login words.
  - Checks (`rules.RULES`, each: title, area, severity, OWASP MASVS 2.x control, Hinglish explanation, fix, snippet per stack
    android / flutter / react_native / web, sources with dates): target API (from 31 Aug 2026 new apps + updates must target 36, below 35 =
    hidden from new users on newer Android; extension to 1 Nov 2026), min SDK, debuggable, testOnly, allowBackup (missing = true), cleartext
    (default before 28), network security config (cleartext base-config, user CAs outside debug-overrides), exported components without a
    permission (launcher skipped, system-broadcast receivers / deep links low), missing android:exported on 31+, exported providers, BIND_*
    accessibility / VPN / device admin, Play-restricted permissions (SMS, call log, all files, QUERY_ALL_PACKAGES, background location,
    REQUEST_INSTALL_PACKAGES, exact alarm, full-screen intent, photo / video, battery exemption, overlay), foreground-service types (34+),
    sensitive permissions -> Data safety types, AD_ID, signing (unsigned / debug cert / v1 only), 64-bit + 16 KB page alignment and 16 KB
    zip alignment of stored .so, embedded secrets (AWS, Stripe live, GitHub, Slack, Anthropic / OpenAI, SendGrid, FCM legacy, Twilio,
    Mapbox secret, Razorpay secret, private keys, password = "..."; masked in every output; public keys like AIza / rzp_live key id = low
    "restrict it"), 60 SDK signatures (Exodus-style class prefixes + pubspec / package.json / Gradle names): trackers, payments (Razorpay,
    PhonePe PG, Paytm, Cashfree, PayU, Juspay, Stripe, BillDesk, Easebuzz, Instamojo, Google Pay), AI SDKs (Play July 2026: third-party AI
    under User Data policy), sign-in SDKs / login words -> account deletion (Play in-app + web; Apple 5.1.1(v)); kids switch -> Families
    policy + DPDP verifiable parental consent; personal data -> DPDP notice / consent / withdrawal / grievance (most duties from 13 May
    2027); payment SDK -> RBI notes (RBI-authorised PA, no card data storage since 1 Oct 2022 tokenisation, payment data in India, verify
    payment on the server), SMS + payment together; content rating + Play Console registration; Apple basics when she has an iPhone
    version. Source code: committed .env / keystores, TLS checks switched off (Kotlin / Dart / Node), JS bridges in WebView, weak crypto,
    insecure random for OTP / tokens, tokens in plain storage, secrets in logs, SQL concatenation, eval / innerHTML, card number / CVV
    fields, iOS NSAllowsArbitraryLoads; evidence = file:line (node_modules / build / tests skipped). Website: HTTPS + redirect, HSTS, CSP,
    framing, nosniff, Referrer-Policy, version leaks, cookie flags, mixed content, certificate days left, exposed files, security.txt.
  - Report: risks sorted by severity, score 100 minus weights; card `appreview_report`; `files` = PDF (reportlab) + Excel (Risks / Fix list /
    Data safety draft / Compare / Sources) + fix list .md + .json as her files (pc_file cards). Re-review of the same target (app package /
    repo / host) compares by risk key: fixed / still open / new; her "jaan-boojh kar hai" (`mark` ignored, a critical needs a reason) is kept
    on later reviews. Hand-off: `handoff` makes only an `appreview_handoff` card (hash of the tasks); `POST /api/appreview/handoffs/{id}/decide`
    (her tap; stale hash refused, decided once) -> `devsahayak.service.tasks_from_review` (when that module provides it) or a developer
    message draft (wa.me) she sends. Worker `tick`: daily cleanup + one alert per app below Play's target API.
  - Never: running the app / its code, uploading her app or code to any third party (no VirusTotal / OSV / MobSF cloud), probing exposed
    files on a domain she has not verified, taking a token in chat, sending the fix list without her tap. Explanations are guidance, not
    legal advice.
  - Sources (checked 23 Oct 2026): developer.android.com/google/play/requirements/target-sdk (API 36 from 31 Aug 2026, existing apps 35,
    extension to 1 Nov 2026, Wear / Auto 35, TV / XR 34); ecorpit.com summary of Google Play's 15 Jul 2026 policy update (third-party AI under
    User Data, READ_CALL_LOG not for verification, Play Console registration, content rating); Play Console Help sensitive permissions,
    Data safety, account deletion, Families pages; developer.android.com 16 KB page sizes (1 Nov 2025); OWASP MASVS v2.1.0 (mas.owasp.org);
    Exodus Privacy tracker list (reports.exodus-privacy.eu.org; the API blocks automated fetching, so signatures were written from its public
    list and must be refreshed by hand); Apple App Store Review Guidelines 5.1.1 / 4.8 / privacy manifests; DPDP Act 2023 + Rules 2025
    (notified 13 Nov 2025, phased to 13 May 2027); RBI payment data localisation circular RBI/2017-18/153 (6 Apr 2018), PA / PG guidelines
    (17 Mar 2020) + card-on-file tokenisation (1 Oct 2022); OWASP Secure Headers Project.
not_verified: Flutter screen + cards not compiled here (no SDK): check CI analyze annotations for lib/ui/appreview_screen.dart (record patterns in `for`, `firstOrNull`, FilePicker withData on big APKs may use lots of memory: 400 MB cap). Not tried on real APKs / AABs from AGP 9 (fixtures are hand-built; resources.arsc-referenced labels show as the package name); the AXML parser ignores resource tables, so `@xml/...` references are matched by scanning every res/xml file for a network-security-config root. Real GitHub zipball redirect to codeload.github.com not exercised (tests use a mock transport; httpx follows the redirect and drops the Authorization header across hosts, which is correct for codeload's signed URL). Website checks use a fake fetcher; the real path needs public DNS (web._check_url) and `cert_days` uses a live TLS handshake. Exodus signatures are a hand-written subset (60 SDKs) of the public list. The 16 KB zip-alignment check reads the local header offset (APK only). REA second-route manifest reading only runs when App Jaanch is configured on the VPS. Policy dates were checked on 23 Oct 2026; Play changes policies often.
