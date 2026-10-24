# Hoola Console: Google sign-in for any real user

- Console "Continue with Google" asks only `openid email profile` (`accounts.SIGNIN_SCOPES`, `prompt=select_account`, no
  refresh token). These are not sensitive scopes, so Google lets any Google account sign in without app verification once
  the OAuth consent screen is published ("In production").
- Gmail / Calendar / Drive / Docs / Sheets are a separate step: Main > Google apps > "Google apps jodiye"
  (`/auth/google/start?web=1&apps=1`, state `cw_g.`, `access_type=offline`, `prompt=consent`, `include_granted_scopes`).
  The callback returns to `/console/?code=...&google=apps`. `/api/console/me` has `google_apps` {gmail, calendar, drive,
  docs, sheets}. Those scopes are sensitive / restricted: for strangers at scale they need Google's app verification
  (and the security assessment for Gmail and full Drive); until then Google shows its "unverified app" screen and caps
  them at 100 users. The phone app keeps its single consent for everything.
- Cancel on Google's screen (console) goes back to `/console/?error=...` instead of a bare page.
- Who can make a NEW Hoola: `HOOLA_SIGNUP=open` (default, anyone) or `invite` with `HOOLA_SIGNUP_ALLOW` = comma list of
  emails and/or `@domain.com`. Existing accounts and `OWNER_EMAILS` always get in. A refused sign-up creates nothing.
- Tests: `server/tests/test_console_google.py`.

# One address everywhere: https://hoola.ainewtika.com

- Phone app: `Santosh.hoolaServer` (lib/state.dart) is fixed to https://hoola.ainewtika.com (`--dart-define=HOOLA_SERVER=...`
  only for test builds); the old saved `server` preference is ignored, so phones set up on the sslip address move here by
  themselves with the same key / session (same server). `configured` = a key is saved. No server box in setup, no server
  line in Profile / Mera PC / Hoola Network; Profile > Account has Logout (`Santosh.signOut`: POST /api/logout, stops the
  background service, back to setup).
- Santosh Desktop: `config.HOOLA_SERVER` (env HOOLA_SERVER or --server for testing); `load()` always uses it, so a PC
  paired on the old address keeps its device token; the pair screen asks only for the code and the PC name.
- Server `.env`: PUBLIC_BASE_URL=https://hoola.ainewtika.com (every Google / Microsoft / DigiLocker return link) and
  HOOLA_DOMAIN=santosh.139-59-10-30.sslip.io kept for Hoola Network avatar addresses until a separate migration.
  Caddy serves both names (the sslip block stays for old app builds).

# Build studio: website / app / Android builds, live (static/console/build.js)

- The console now understands the builders' live events `site_board`, `app_board`, `app_android` (before: a plain generic
  card). `window.HoolaBuild(ctx)` (build.js, loaded before app.js) renders them; app.js hands it `api / esc / toast / narrow /
  conv / say` and sends these kinds to `B.card()` (cards keep updating in place, `live` = arrived on the stream, not replayed).
- Chat card: stages strip, Abhi line + progress, plan list / 3 look pictures / scores, and the real buttons (Haan looks banao,
  Rokiye, Aage badhao, Design pakka, Android app banao, APK download).
- Studio = right-hand panel (`#app.st`, ~50% width; side sheet at <=1100 px; bottom sheet at <=820 px); one per project
  (`site:<id>` / `app:<id>`, picker when there are several). Opens by itself when a build event arrives live (not if she
  closed it for that project). Tabs: website Plan / Looks / Preview / Board / Kadam / Jaanch; app Plan / Looks / Screens /
  Prototype / Dhaancha / Android / Kadam. Badlav box -> `/change`, answers -> `/answers`, look -> `/look` {index, colors_from},
  plan -> `/plan`, approve -> `/approve` {hash} (confirm), Android -> `/android` (`redo` for code-made screens).
- Live preview: the public-by-token `/api/site-preview/<t>/` and `/api/app-preview/<t>/` in iframes with
  `sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"` (no allow-same-origin: the preview can
  never read the console's token). A finished part reloads it (at most every 3 s) into a second frame that replaces the old
  one after it has drawn. Opaque-origin frames need CORS for their fonts: both preview routes add `Access-Control-Allow-Origin: *`.
- Pictures (look shots, screen thumbs, screenshots, scroll video) are behind the login: fetched with the Bearer token into
  blob: URLs (CSP img-src / media-src blob: already allowed). APK QR = vendor/qrcode.js (qrcode-generator 1.4.4, MIT).
- Kadam = the real "now" lines as they arrive (with time and seconds per part); opened later = what the board shows done.
- Domain / live: buttons put the request in chat; buying a domain or going live still needs her Haan card.
- Tests: `server/tests/test_console_build.py`.
