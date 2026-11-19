"""Rules of the IT Admin Sahayak: licence kinds, renewal windows, seat waste, joiner / mover / leaver templates, access review
flags, staff question matching, access-request detection, change kinds with the exact admin API call each one would make.

Research (23 Oct 2026; sources also in WIRING.md):
- Microsoft Graph v1.0: GET /subscribedSkus -> consumedUnits (used) + prepaidUnits.enabled (bought); least privilege
  LicenseAssignment.Read.All (learn.microsoft.com/graph/api/subscribedsku-list). Users GET /users ($select accountEnabled,
  assignedLicenses ...), User.Read.All; disable = PATCH /users/{id} {"accountEnabled": false} (User.EnableDisableAccount.All,
  admin consent; graphpermissions.merill.net); POST /users/{id}/revokeSignInSessions; POST /users/{id}/assignLicense
  {addLicenses, removeLicenses} (LicenseAssignment.ReadWrite.All). Intune devices GET /deviceManagement/managedDevices
  (DeviceManagementManagedDevices.Read.All). Token: client credentials, scope https://graph.microsoft.com/.default.
- Google Workspace Admin SDK Directory API: GET https://admin.googleapis.com/admin/directory/v1/users?customer=my_customer
  (admin.directory.user.readonly), suspend = PATCH users/{userKey} {"suspended": true} (admin.directory.user), POST
  users/{userKey}/signOut, POST users/{userKey}/makeAdmin {"status": bool}; devices GET customer/my_customer/devices/mobile
  (admin.directory.device.mobile.readonly) and /devices/chromeos (admin.directory.device.chromeos.readonly). Enterprise
  License Manager API (licensing.googleapis.com/apps/licensing/v1): listForProduct GET product/{productId}/users?customerId=,
  insert POST product/{p}/sku/{s}/user {"userId"}, delete DELETE product/{p}/sku/{s}/user/{userId}; scope apps.licensing
  (developers.google.com/admin-sdk/licensing/v1/reference). The Licensing API does not say how many seats were BOUGHT
  (that is the reseller / billing side), so for Google she types it.
- Passwords: creating a user / resetting a password needs a password in both APIs, and Hoola never handles passwords, so
  those are always console steps she does herself.
- ISO/IEC 27001:2022 Annex A 5.15-5.18 (access control, identity, authentication, access rights: provisioned, reviewed at
  planned intervals, removed on change / termination), 6.5 (responsibilities after termination or change), 5.11 (return of
  assets), 8.2 (privileged access) - tcsa.in / upguard.com control pages.
- CERT-In Directions No. 20(3)/2022-CERT-In, 28 Apr 2022 (in force 27 Jun 2022): logs of all ICT systems for a rolling 180 days
  kept within India, clocks synced to NIC / NPL NTP, a designated Point of Contact (taxguru.in summary).
- DPDP Act 2023 s.7(i): employee data may be processed for employment purposes without consent (legitimate use); s.8(5)
  reasonable security safeguards; s.8(7) erase when the purpose is over. DPDP Rules notified Nov 2025, most duties from
  ~13 May 2027.
"""
from __future__ import annotations

import re
from datetime import date

LIC_KINDS = {
    "m365": "Microsoft 365", "workspace": "Google Workspace", "tally": "Tally (TSS)", "antivirus": "Antivirus",
    "domain": "Domain", "ssl": "SSL certificate", "cloud": "Cloud / hosting plan", "backup": "Backup plan",
    "software": "Software licence", "saas": "Online subscription", "isp": "Internet plan", "other": "Other",
}
LIC_WORDS = {
    "m365": ("microsoft 365", "office 365", "m365", "o365", "outlook business", "exchange"),
    "workspace": ("google workspace", "g suite", "gsuite", "workspace"),
    "tally": ("tally", "tss"),
    "antivirus": ("antivirus", "quick heal", "k7", "kaspersky", "eset", "norton", "mcafee", "seqrite", "bitdefender", "defender"),
    "domain": ("domain", ".in", ".com", "godaddy", "bigrock", "hostinger domain"),
    "ssl": ("ssl", "https certificate", "tls"),
    "cloud": ("aws", "azure", "gcp", "digitalocean", "hosting", "vps", "server plan", "cloud"),
    "backup": ("backup", "google one", "onedrive plan", "dropbox"),
    "isp": ("broadband", "leased line", "internet plan", "fiber plan"),
}
WINDOWS_DEFAULT = [60, 30, 15, 7, 1, 0]
LEVELS = ("user", "admin", "owner")
CHANGE_KINDS = {
    "user_create": "Create a new account", "user_disable": "Turn off account (suspend / disable)", "user_enable": "Turn account back on",
    "user_signout": "Sign out of all devices", "licence_assign": "Assign licence", "licence_remove": "Remove licence",
    "admin_grant": "Grant admin rights", "admin_remove": "Remove admin rights", "password_reset": "Password reset (yourself, in the console)",
    "password_rotate": "Change shared password", "access_add": "Grant access", "access_remove": "Remove access",
    "setting": "Change a setting", "other": "Change",
}
# kinds whose API needs a password, or that touch secrets: never run by Hoola, always her console steps
NEVER_API = {"user_create", "password_reset", "password_rotate", "setting"}

ACCESS_REQ = re.compile(
    r"(access (chahiye|do|de do|dedo|dijiye|chahie)|access nahi hai|admin (bana|rights|access)|password reset|password (bhool|bhul|change)|"
    r"naya (email|account|id)|new (email|account)|licence (chahiye|do)|license (chahiye|do)|permission (chahiye|do|de)|"
    r"account (band|lock|unlock|khol|disable|delete)|unlock (karo|kar do)|remove access|access hatao|login (do|chahiye)|"
    r"रीसेट|एक्सेस)", re.I)
SECRET_ASK = re.compile(r"(password|pin|otp)\s*(kya|batao|bata do|bhejo|share|send|de do|do\b|chahiye)", re.I)

STOP = set("""a an the is are was to of in on for and or with me mujhe mera meri mere hai hain ho kaise kese kya kar karo karna kare
karein karu karun nahi nhi na ka ki ke ko se par pe ye yeh wo woh hum ham aap apna apni please pls plz kaun kab kahan sir madam ji
how do i can my what where when why which""".split())
SYN = {"mail": "email", "e-mail": "email", "gmail": "email", "outlook": "email", "id": "account", "login": "account",
       "signin": "account", "sign-in": "account", "lagana": "setup", "jodna": "setup", "add": "setup", "connect": "setup",
       "chalu": "setup", "install": "setup", "printer": "printer", "print": "printer", "wifi": "wifi", "wi-fi": "wifi",
       "net": "internet", "phone": "mobile", "mobile": "mobile", "laptop": "pc", "computer": "pc", "pc": "pc",
       "drive": "drive", "share": "share", "bhejna": "share", "password": "password", "passwd": "password",
       "signature": "signature", "sign": "signature", "vpn": "vpn", "tally": "tally", "backup": "backup", "scan": "scan"}


def kind_of(name: str, kind: str = "") -> str:
    k = (kind or "").lower().strip()
    if k in LIC_KINDS:
        return k
    low = (name or "").lower()
    for kk, words in LIC_WORDS.items():
        if any(w in low for w in words):
            return kk
    return "software"


def windows(raw) -> list[int]:
    out = []
    for v in raw or []:
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if 0 <= n <= 365 and n not in out:
            out.append(n)
    return sorted(out, reverse=True) or list(WINDOWS_DEFAULT)


def window_due(days_left: int, wins: list[int], told: list[int]) -> int | None:
    """The tightest window that applies now and was not told yet (only one reminder at a time)."""
    hit = [w for w in wins if days_left <= w]
    if not hit:
        return None
    w = min(hit)
    return None if w in told else w


def yearly(cost: float | None, per: str) -> float | None:
    if cost is None:
        return None
    return round(cost * 12, 2) if per == "month" else (round(cost, 2) if per == "year" else None)


def seat_waste(bought: int | None, used: int | None, cost: float | None, per: str, per_seat: bool) -> dict | None:
    if bought is None or used is None or bought <= used:
        return None
    free = bought - used
    out = {"free": free, "rupees_year": None}
    y = yearly(cost, per)
    if y is not None and bought > 0:
        seat_year = y if per_seat else y / bought
        out["rupees_year"] = round(seat_year * free)
    return out


# ---------------------------------------------------------------- joiner / mover / leaver
def joiner_items(person: str, systems: list[str], has_google: bool, has_ms: bool) -> list[dict]:
    items = []
    if has_google:
        items.append({"kind": "account_create", "text": f"{person}: Google Workspace account (yourself, in the Admin console: you set the first password)", "system": "Google Workspace"})
    if has_ms:
        items.append({"kind": "account_create", "text": f"{person}: Microsoft 365 account (yourself, in the admin centre)", "system": "Microsoft 365"})
    for s in systems:
        if (has_google and "google" in s.lower()) or (has_ms and "microsoft" in s.lower()):
            continue
        items.append({"kind": "account_create", "text": f"{s}: {person} - own login (not a shared login)", "system": s})
    items += [
        {"kind": "licence", "text": "Assign the licences needed (only as much as the work needs)"},
        {"kind": "mfa", "text": "Get 2-step verification (MFA) turned on"},
        {"kind": "device_issue", "text": "Issue a device: write the user's name in the register (IT Helpdesk)"},
        {"kind": "guides", "text": "Send the welcome guides (email, printer, Wi-Fi)"},
        {"kind": "policy", "text": "Explain the IT rules / acceptable use (never share a password)"},
    ]
    return items


def mover_items(person: str, active: list[dict], new_role: str) -> list[dict]:
    items = [{"kind": "access_review", "text": f"Review the accesses of the old role ({len(active)}): remove those not needed in the new role ({new_role or 'new role'})"}]
    for a in active:
        if a.get("level") in ("admin", "owner"):
            items.append({"kind": "access_review", "text": f"{a['system']}: are admin rights still needed?", "access": a["id"]})
    items.append({"kind": "access_add", "text": "Accesses for the new role (only what is needed)"})
    return items


def leaver_items(person: str, active: list[dict], devices: list[dict], shared: list[dict]) -> list[dict]:
    items = []
    for a in active:
        items.append({"kind": "account_disable", "text": f"{a['system']}: {a.get('account') or person} - turn off (on the last day)",
                      "access": a["id"], "system": a["system"]})
    items.append({"kind": "signout", "text": "Sign out of all devices / end sessions"})
    items.append({"kind": "licence_free", "text": "Remove the licence (saves money)"})
    items.append({"kind": "data_handover", "text": "Change the owner of mail / files (to the manager); a forward rule only for a few days"})
    for d in devices:
        items.append({"kind": "device_collect", "text": f"Collect the device: {d.get('tag', '')} {d.get('name', '')}".strip(), "asset": d.get("id", "")})
    for s in shared:
        items.append({"kind": "password_rotate", "text": f"{s['system']}: change the shared password ({person} knew it)", "access": s["id"],
                      "system": s["system"]})
    items.append({"kind": "groups", "text": "Remove from office WhatsApp / Telegram groups (yourself)"})
    return items


# ---------------------------------------------------------------- access review flags
def review_flags(a: dict, person: dict | None, on: date) -> list[str]:
    f = []
    if person is None:
        f.append("not linked to any person")
    elif person.get("status") in ("left", "leaving", "forgotten"):
        f.append("person has left / is leaving the office")
    if a.get("level") in ("admin", "owner"):
        f.append("admin rights")
        if a.get("mfa") != "yes":
            f.append("admin without 2-step")
    if a.get("shared"):
        f.append("shared login")
    ll = a.get("last_login") or ""
    if ll[:10]:
        try:
            if (on - date.fromisoformat(ll[:10])).days > 90:
                f.append("no login for 90 days")
        except ValueError:
            pass
    return f


# ---------------------------------------------------------------- staff questions
def words(text: str) -> list[str]:
    t = re.sub(r"[^\w\s@.-]", " ", (text or "").lower())
    out = []
    for w in t.split():
        w = w.strip(".-")
        if not w or w in STOP or len(w) < 2:
            continue
        out.append(SYN.get(w, w))
    return out


def match_score(q: list[str], doc: list[str]) -> float:
    if not q or not doc:
        return 0.0
    ds = set(doc)
    hit = sum(1 for w in set(q) if w in ds or any(len(w) > 4 and (w in d or d in w) for d in ds if len(d) > 4))
    return hit / max(1, len(set(q)))


def quarter_of(on: date) -> str:
    return f"R-{on.year}-Q{(on.month - 1) // 3 + 1}"


def practices_list() -> list[dict]:
    return [
        {"id": "mfa_admins", "text": "2-step verification on every admin account", "why": "ISO 27001 A.8.5 / A.8.2"},
        {"id": "no_shared", "text": "As few shared logins as possible; a separate account for each person", "why": "ISO 27001 A.5.16"},
        {"id": "leaver_same_day", "text": "Close a leaver's access on the last day itself", "why": "ISO 27001 A.5.18 / A.6.5"},
        {"id": "review_quarterly", "text": "Access review every 3 months", "why": "ISO 27001 A.5.18"},
        {"id": "logs_180", "text": "Login / system logs for 180 days, inside India (check the M365 / Workspace audit log setting)",
         "why": "CERT-In Directions 28 Apr 2022 (body corporate)"},
        {"id": "ntp", "text": "PC / server / router clocks from NIC or NPL NTP (time.nplindia.org / samay1.nic.in)",
         "why": "CERT-In Directions 28 Apr 2022"},
        {"id": "poc", "text": "One Point of Contact named for CERT-In (name, email, phone)", "why": "CERT-In Directions 28 Apr 2022"},
        {"id": "dpdp_staff", "text": "Staff data only for employment purposes; after they leave, erase it once it is no longer needed",
         "why": "DPDP Act 2023 s.7(i), s.8(7)"},
    ]


def change_api(kind: str, provider: str, target: str, sku: str = "", product: str = "") -> dict:
    """The exact admin API call a change would make ({} when it is never done by API)."""
    if kind in NEVER_API or provider not in ("google", "microsoft") or not target:
        return {}
    g, gl = "https://admin.googleapis.com/admin/directory/v1/users/", "https://licensing.googleapis.com/apps/licensing/v1/product/"
    m = "https://graph.microsoft.com/v1.0/users/"
    if provider == "google":
        return {
            "user_disable": {"method": "PATCH", "url": g + target, "body": {"suspended": True}},
            "user_enable": {"method": "PATCH", "url": g + target, "body": {"suspended": False}},
            "user_signout": {"method": "POST", "url": g + target + "/signOut", "body": None},
            "admin_grant": {"method": "POST", "url": g + target + "/makeAdmin", "body": {"status": True}},
            "admin_remove": {"method": "POST", "url": g + target + "/makeAdmin", "body": {"status": False}},
            "licence_assign": {"method": "POST", "url": f"{gl}{product}/sku/{sku}/user", "body": {"userId": target}} if sku and product else {},
            "licence_remove": {"method": "DELETE", "url": f"{gl}{product}/sku/{sku}/user/{target}", "body": None} if sku and product else {},
        }.get(kind, {})
    return {
        "user_disable": {"method": "PATCH", "url": m + target, "body": {"accountEnabled": False}},
        "user_enable": {"method": "PATCH", "url": m + target, "body": {"accountEnabled": True}},
        "user_signout": {"method": "POST", "url": m + target + "/revokeSignInSessions", "body": None},
        "licence_assign": {"method": "POST", "url": m + target + "/assignLicense",
                           "body": {"addLicenses": [{"skuId": sku, "disabledPlans": []}], "removeLicenses": []}} if sku else {},
        "licence_remove": {"method": "POST", "url": m + target + "/assignLicense", "body": {"addLicenses": [], "removeLicenses": [sku]}} if sku else {},
    }.get(kind, {})


def console_steps(kind: str, provider: str, target: str, system: str = "") -> list[str]:
    who = target or "that person"
    if provider == "google":
        base = ["Open admin.google.com (with your admin account)", "Directory > Users > " + who]
        more = {"user_disable": ["Tap 'Suspend user'"], "user_enable": ["Tap 'Reactivate'"],
                "user_signout": ["Security > 'Sign-in cookies' > Reset"], "admin_grant": ["Admin roles > role assign"],
                "admin_remove": ["Admin roles > remove the role"], "licence_assign": ["Licenses > Edit > assign"],
                "licence_remove": ["Licenses > Edit > unassign"], "password_reset": ["'Reset password' > set a new password yourself; 'change at next sign-in' on"],
                "user_create": ["Directory > Users > 'Add new user' > name + email; set the password yourself"]}
        return base + more.get(kind, ["Make the needed change"])
    if provider == "microsoft":
        base = ["Open admin.microsoft.com (with your admin account)", "Users > Active users > " + who]
        more = {"user_disable": ["'Block sign-in' on"], "user_enable": ["'Block sign-in' off"], "user_signout": ["'Sign out of all sessions'"],
                "licence_assign": ["Licenses and apps > licence tick"], "licence_remove": ["Licenses and apps > licence untick"],
                "admin_grant": ["Manage roles > choose the role"], "admin_remove": ["Manage roles > 'User (no admin access)'"],
                "password_reset": ["'Reset password' > set a new password yourself"], "user_create": ["'Add a user' > name + email; set the password yourself"]}
        return base + more.get(kind, ["Make the needed change"])
    s = system or "that system"
    more = {"password_rotate": [f"{s}: log in as admin", "Set a new strong password (at least 12 characters) yourself",
                                "Tell only the people who need it, directly (not written in chat / WhatsApp)"],
            "user_disable": [f"{s}: turn off / delete the login of {who}"],
            "access_remove": [f"{s}: remove the access of {who}"], "access_add": [f"{s}: give {who} only the access that is needed"]}
    return more.get(kind, [f"{s}: make the change yourself"])
