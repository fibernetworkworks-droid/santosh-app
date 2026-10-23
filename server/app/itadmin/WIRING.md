# WIRING for itadmin
summary: IT Admin Sahayak (licences / subscriptions with seats bought vs used, renewal windows and rupees saved on free seats; people & access register without secrets; joiner / mover / leaver checklists; quarterly access review; Google Workspace Admin SDK + Microsoft Graph read with her consent; staff how-to guides with her screenshots and versions; staff IT questions answered from guides, else an IT Helpdesk ticket; every access / settings change only on her tap, sent by the official admin API only in manage mode)
db: app.itadmin.models
router: app.itadmin.api            (make_router(require_key, current_tenant); all routes under /api/itadmin, key-protected; no public routes)
  - ALSO in main.py /auth/google/callback, BEFORE the plain sign-in branch (next to the feedback `fbk_` branch):
    `from .itadmin.connectors import is_link_state as is_ita_state`
    `if is_ita_state(request.query_params.get("state", "")):  from .itadmin.api import finish_page as ita_finish; return await ita_finish(request)`
    (states start with "ita_r_" / "ita_m_"; MailLinkState provider "itadmin"). The page deep-links `<scheme>://itadmin?ok=1|0`.
tools: app.agent.itadmin_tools    (ITADMIN_TOOLS / ITADMIN_LABELS / ITADMIN_HANDLERS) ; voice: yes (it_admin, it_admin_dekho)
employee: duty it_admin_work = [it_admin, it_admin_dekho, helpdesk, helpdesk_dekho, file_read] {label "IT admin", say "licence / renewal, kiske paas kaun sa access, joiner-leaver checklist, staff ke liye guide, staff ke IT sawaal (access / setting badlav aapki haan se)"} ; role it_admin {label "IT Administrator", duties [it_admin_work, it_helpdesk, records, reminders]} ; preset it_admin {label "Office IT administrator", role it_admin, rules ["Access / setting ka badlaav sirf owner ki haan ke card se", "Password / OTP / PIN kabhi mat maango, mat likho", "Chhodne wale ka access aakhri din hi band"]} ; READ tools: [it_admin_dekho]
  - staff (staff:<id>) may add licences / people / access records, start checklists, ask for a change (card), write guide drafts and use action=ask. Owner-only in the tool: renewed, licence_remove, change_done, review_item, review_close, guide_publish, sync, forget_person, settings. Customers refused in both tools. No tool can approve: only POST /api/itadmin/changes/{id}/decide (her tap, card hash must match).
  - neighbour: helpdesk (v0.133) owns the asset register (devices) and tickets; this module reads / writes devices only through `helpdesk.service.assets / save_asset` and opens tickets through `helpdesk.service.new_ticket`. Neighbour builders in this suite: cyber (security), devops, ispnoc.
push: itadmin_change -> ("IT: aapki haan chahiye", "{say}")
push: itadmin_renewal -> ("Renewal aa raha hai", "{say}")
push: itadmin_checklist -> ("Joiner / leaver checklist", "{say}")
push: itadmin_review -> ("Access review ka samay", "{say}")
push: itadmin_day -> ("Aaj ka IT admin note", "{say}")
  (itadmin_guide: no push; publish only)
worker: app.itadmin.service.tick   (call every minute, e.g. `await asyncio.to_thread(itadmin.tick)`; renewal reminder once per window (tightest window that applies, + once when overdue), leaver last-day alert once, morning note once a day at her morning_time (only when there is something), access review started when review_months passed since the last one, read-only sync of her connected consoles once a day with the morning note)
prompt: IT ADMIN: licences / renewals / seats -> `it_admin action=licence` (her numbers only, never guess a price or date); who has which access -> `action=access` (only THAT access exists; never write or repeat a password / PIN / OTP); new / moving / leaving staff -> `action=joiner|mover|leaver`; staff IT questions -> `action=ask` with their exact words; how-to -> `action=guide` from HER setup words only. Any change of access or settings (disable / enable account, licence, admin rights, password reset, shared password change) is only a card for her tap: say "aapki haan ka card bheja hai", never say it is done, never do it yourself (not with pc_do either). Users are never created and passwords never reset by API: she does those in the console.
persona: IT admin mein access ya setting badalna ho to "aapki haan ka card bheja hai" kaho; password / OTP kabhi mat maango; staff ke sawaal ka jawab guide se do, na mile to IT ticket.
flutter: ItadminScreen in lib/ui/itadmin_screen.dart ; profile tile title "<name> · IT Admin" subtitle "Licence, renewal, access, joiner-leaver, staff guides" icon Icons.admin_panel_settings_rounded ; cards: itadmin_change -> ItadminChangeCard (also in calls: yes; one card per data['change']['id'], updated in place) ; itadmin_checklist -> ItadminChecklistCard (also in calls: yes; key data['checklist']['id']) ; itadmin_renewal -> ItadminRenewalCard (also in calls: no) ; itadmin_review -> ItadminReviewCard (also in calls: no) ; itadmin_guide -> ItadminGuideCard (also in calls: no; key data['guide']['id']) ; itadmin_day -> ItadminDayCard (also in calls: no). All widgets take (app:, data:) and use `app.api!.call(...)`, `app.api!.uploadFile(...)` (guide screenshots, field n), `app.api!.authHeaders` + `baseUrl` (screenshots via GET /api/itadmin/shots/{id}), `Native.openExternal` (Google consent / Microsoft adminconsent links) and image_picker (already a dependency).
  - deep link `santosh://itadmin?ok=` (after Google consent) -> open ItadminScreen (optional; the screen reloads on open anyway).
features: itadmin
env: none new (Google Workspace link uses the existing GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET / PUBLIC_BASE_URL; her Google Cloud OAuth client must list the Admin SDK scopes on its consent screen; Microsoft uses HER own Entra app typed in the app)
requirements: none (httpx, openpyxl, Pillow, python-docx already present)
android: none
claude_md: |
  ## v0.1xx IT Admin Sahayak: Hoola as a small office's IT administrator ("IT administrator" on the Employee page)
  - Owner's spec: tracks devices, licences and renewals -> writes how-to guides -> answers staff IT questions -> waits for her
    Haan on CHANGING ACCESS OR SETTINGS. Server `server/app/itadmin/{rules,models,connectors,service,api}.py`, tools `it_admin` /
    `it_admin_dekho` (`agent/itadmin_tools.py`, chat + calls), duty `it_admin_work`, role + preset `it_admin`, API `/api/itadmin/*`,
    app Profile > IT Admin (`lib/ui/itadmin_screen.dart`: Aaj / Licence / Log / Guides / Admin; ItadminPersonPage, ItadminGuidePage),
    cards ItadminChangeCard, ItadminChecklistCard, ItadminRenewalCard, ItadminReviewCard, ItadminGuideCard, ItadminDayCard.
    Tests `server/tests/test_tech_itadmin.py` (7, fake Google + Microsoft transports).
  - Devices are NOT copied: the IT Helpdesk (v0.133) asset register is the one register (`helpdesk.service.assets / save_asset`);
    Workspace mobile / ChromeOS and Intune devices sync into it by serial. Unknown staff questions become helpdesk tickets.
  - Licences (L-001): kind m365 / workspace / tally / antivirus / domain / ssl / cloud / backup / software / saas / isp, vendor, plan,
    seats bought vs used, her cost (month / year / once, per seat or total), renews_on, auto-renew (asked when not known), owner,
    "login_with" (which account manages it, never a password). Reminders at her windows (default 60/30/15/7/1/0 days, one per
    window: the tightest that applies, + once when overdue), free seats -> rupees a year (only from her cost), renewal history
    with price rise >= 10% pointed out. Hoola never pays or renews.
  - People (P-001) and the access register: that an access EXISTS (system, account, user / admin / owner, shared login, 2-step
    yes / no, last login); a password / PIN / OTP in any field is refused. Joiner (accounts to make from her standard systems,
    licence, 2-step, device, guides, rules) / mover (review old access, admin rights) / leaver (disable every active account on the
    last day, sign-out, free the licence, mail / file handover, collect the devices assigned in the helpdesk register, rotate every
    shared password they knew, groups). Change-type items make cards at once and tick only when the card's change is done.
    `forget_person` (DPDP s.8(7)) only after they left and every access is closed.
  - Access review (R-2026-Q4, every `review_months`, default 3): every active access with flags (not linked to anyone, person
    left, admin, admin without 2-step, shared login, no login 90 days); her keep / remove per line; remove = a change card.
  - Admin consoles, official APIs, her consent: Google Workspace = OAuth with her admin account (states "ita_r_" read /
    "ita_m_" manage; scopes admin.directory.user.readonly, admin.directory.device.mobile.readonly,
    admin.directory.device.chromeos.readonly, apps.licensing; manage adds admin.directory.user); Directory API users (suspended,
    isAdmin / isDelegatedAdmin, isEnrolledIn2Sv, lastLoginTime), devices, Licensing API listForProduct "Google-Apps" (seats USED;
    bought is hers to type). Microsoft 365 = HER Entra app (directory id + client id + client secret typed only in the app, sealed
    with the bazar vault, verified by a client-credentials token, adminconsent link) -> /subscribedSkus (consumedUnits used,
    prepaidUnits.enabled bought), /users (accountEnabled, assignedLicenses; #EXT# guests skipped), /deviceManagement/managedDevices,
    /directoryRoles members (admins). Sync never writes; missing permissions / plans are named, not fatal.
  - Changes (AC-0001): user_create / user_disable / user_enable / user_signout / licence_assign / licence_remove / admin_grant /
    admin_remove / password_reset / password_rotate / access_add / access_remove / setting. Each card carries the EXACT call
    (Google PATCH users/{key} {"suspended": true}, POST users/{key}/signOut, POST users/{key}/makeAdmin, Licensing insert / delete;
    Graph PATCH /users/{id} {"accountEnabled": false}, POST /users/{id}/revokeSignInSessions, POST /users/{id}/assignLicense) or the
    console steps. ONLY `POST /api/itadmin/changes/{id}/decide {yes, hash}` (her tap) approves; in manage mode that one call is sent
    (URL allow-list), in read mode / manual systems she does it in the console and taps "Maine kar diya". Creating users and
    resetting / rotating passwords are NEVER done by API (they need a password): always her console steps. Same pending change is
    never asked twice. Staff can ask, never approve.
  - Guides (G-001): her setup words -> Hinglish steps (cheap brain / Claude via pakka._ask; a model answer with any URL / email /
    domain / 2+ digit number not in her words is thrown away; no model = her sentences split into steps); passwords in her words
    are removed; [?] where she left a fact out (publish refused until filled); screenshots per step re-encoded to PNG from pixels
    only (EXIF / GPS / camera / text chunks dropped) in data/itadmin/<tenant>/guides; versions (20) + restore; publish = owner;
    Word file; helped / not helped.
  - Staff questions (`ask`): "password batao" refused; access / account / password-reset / admin / licence requests = her change
    card; published guide match (title / tags weighted) -> the steps; else an IT Helpdesk ticket (playbooks walk them through);
    every question logged masked; `gaps` = questions no guide answered, grouped (morning note suggests a guide at 3+).
  - Good practice checklist (Admin tab): admins on 2-step, no shared logins, leaver same day, quarterly review (ISO/IEC 27001:2022
    A.5.15-5.18, 6.5, 5.11, 8.2, 8.5), logs 180 days in India, NTP from NIC / NPL, a CERT-In Point of Contact (CERT-In Directions
    28 Apr 2022), staff data only for employment (DPDP s.7(i), s.8(7)).
  - Sources (23 Oct 2026): learn.microsoft.com/graph/api/subscribedsku-list (GET /subscribedSkus, consumedUnits / prepaidUnits,
    least privilege LicenseAssignment.Read.All); graphpermissions.merill.net User.EnableDisableAccount.All (enable / disable users,
    admin consent); office365itpros.com (revoke access: disable + revokeSignInSessions); developers.google.com/admin-sdk/licensing/v1/
    reference (insert / delete / listForProduct paths); Admin SDK Directory API users / mobiledevices / chromeosdevices and scope
    names (developers.google.com/admin-sdk/directory); tcsa.in + upguard.com ISO 27001:2022 controls 5.11, 5.18, 6.5; taxguru.in
    "CERT-In issues directions relating to information security practices" (No. 20(3)/2022-CERT-In, 28 Apr 2022: 180-day logs in
    India, NIC / NPL NTP, Point of Contact); DPDP Act 2023 s.7(i), s.8(5), s.8(7); tallysolutions.com/renew-tss (TSS is a yearly
    renewal). Renewal windows and the 90-day no-login flag are starter numbers, not rules.
not_verified: No real Google Workspace or Microsoft 365 tenant was called (all tests use httpx MockTransport fakes shaped from the documented responses). Google: the Cloud OAuth consent screen must allow the Admin SDK / Licensing scopes and the signer must be a super admin (else Directory returns 403: shown as last_error); `customerId=my_customer` for the Licensing API is assumed to work like Directory (docs say a customer id or domain; if refused, store the domain). Microsoft: `directoryRoles?$expand=members` and Intune `managedDevices` need extra permissions / an Intune plan, tolerated as "missing". Admin-role grants are console steps for Microsoft (no API card) by design. Flutter screen not compiled here (no SDK): check CI annotations for lib/ui/itadmin_screen.dart. The main.py Google-callback branch must be added by the coordinator, else Google linking ends on the plain sign-in page.
