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
