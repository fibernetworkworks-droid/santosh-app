"""v0.131 Login and security plan for an app: which ways to sign in, second step, unlock, company SSO, sessions, and the
rules the native build and its server must follow. Store rules: Sign in with Apple when other social logins are offered
(App Store Guideline 4.8 asks for an equivalent privacy-focused option; Apple's own is the usual choice), in-app account
deletion on both stores, no password / OTP / PIN ever typed into chat or sent to Hoola."""
from __future__ import annotations

from typing import Any

METHODS: dict[str, dict[str, Any]] = {
    "phone_otp": {"label": "Mobile number + OTP", "hi": "mobile + OTP", "kind": "primary",
                  "android": "SMS Retriever / User Consent API (OTP filled without SMS permission)", "ios": "oneTimeCode autofill",
                  "server": "OTP via a DLT-registered SMS template (TRAI) from her SMS provider; 6 digits, 5 min, hashed",
                  "screens": ["login"], "cost": "per SMS", "note": "Most familiar in India."},
    "whatsapp_otp": {"label": "WhatsApp OTP", "hi": "WhatsApp OTP", "kind": "primary",
                     "android": "copy-code / one-tap button (official WhatsApp authentication template)", "ios": "copy code",
                     "server": "WhatsApp Cloud API authentication template from her own business number",
                     "screens": ["login"], "cost": "per message (Meta)", "note": "Official Cloud API only."},
    "employee_otp": {"label": "Employee ID / mobile + OTP", "hi": "employee ID + OTP", "kind": "primary",
                     "android": "SMS Retriever", "ios": "oneTimeCode", "server": "only numbers the admin added can get an OTP",
                     "screens": ["login_staff"], "cost": "per SMS", "note": "Staff can't sign up themselves; the admin invites."},
    "email_password": {"label": "Email + password", "hi": "email + password", "kind": "primary",
                       "android": "Credential Manager password save / autofill", "ios": "Password AutoFill",
                       "server": "argon2id hash, min 10 characters, known-breached passwords refused, reset by email link",
                       "screens": ["login_email"], "cost": "free", "note": ""},
    "magic_link": {"label": "Email link (no password)", "hi": "email link", "kind": "primary",
                   "android": "App Links open the app", "ios": "Universal Links", "server": "one-time link, 15 min, single use",
                   "screens": ["login_email"], "cost": "free", "note": "Needs her domain for app links."},
    "google": {"label": "Sign in with Google", "hi": "Google se login", "kind": "social",
               "android": "Credential Manager + Sign in with Google", "ios": "Google Sign-In SDK",
               "server": "verify the ID token (audience = her OAuth client)", "screens": ["login_email"], "cost": "free",
               "note": "Her own Google Cloud OAuth client."},
    "apple": {"label": "Sign in with Apple", "hi": "Apple se login", "kind": "social",
              "android": "web flow (rarely used on Android)", "ios": "AuthenticationServices",
              "server": "verify the identity token; handle private relay email", "screens": ["login_email"], "cost": "free",
              "note": "Needed on iPhone whenever Google / other social login is offered (Guideline 4.8)."},
    "passkey": {"label": "Passkey", "hi": "passkey", "kind": "strong",
                "android": "Credential Manager passkeys", "ios": "ASAuthorization passkeys",
                "server": "WebAuthn relying party on her domain (assetlinks.json + apple-app-site-association)",
                "screens": ["passkey_setup"], "cost": "free", "note": "Phishing-proof; replaces OTP after the first login."},
    "biometric_unlock": {"label": "Fingerprint / Face unlock", "hi": "fingerprint se kholo", "kind": "unlock",
                         "android": "BiometricPrompt unlocks a Keystore key", "ios": "LocalAuthentication + Keychain",
                         "server": "-", "screens": ["app_lock"], "cost": "free",
                         "note": "Unlocks the saved session on this phone; not a login by itself."},
    "app_pin": {"label": "App PIN", "hi": "app PIN", "kind": "unlock", "android": "PIN checked against a Keystore-wrapped hash",
                "ios": "Keychain", "server": "-", "screens": ["app_lock"], "cost": "free",
                "note": "For shared / basic phones; 5 wrong tries -> OTP again."},
    "totp_mfa": {"label": "Authenticator app code (2nd step)", "hi": "authenticator code", "kind": "mfa",
                 "android": "-", "ios": "-", "server": "RFC 6238 TOTP, 30 s, +-1 step; 8 backup codes shown once",
                 "screens": ["mfa_verify"], "cost": "free", "note": "Required for admins and risky actions."},
    "sms_mfa": {"label": "SMS code (2nd step)", "hi": "SMS code", "kind": "mfa", "android": "SMS Retriever", "ios": "oneTimeCode",
                "server": "as phone OTP", "screens": ["mfa_verify"], "cost": "per SMS", "note": "Weaker than an authenticator."},
    "sso_oidc": {"label": "Company login (OIDC SSO)", "hi": "company login", "kind": "sso",
                 "android": "AppAuth (Custom Tabs, PKCE)", "ios": "ASWebAuthenticationSession (PKCE)",
                 "server": "OpenID Connect with Microsoft Entra / Google Workspace / Okta / Keycloak; groups -> roles",
                 "screens": ["login_sso"], "cost": "free", "note": "For companies that already have an identity provider."},
    "sso_saml": {"label": "Company login (SAML)", "hi": "SAML login", "kind": "sso",
                 "android": "browser flow via the server", "ios": "browser flow via the server",
                 "server": "SAML 2.0 at the server, then the app gets its own session", "screens": ["login_sso"], "cost": "free",
                 "note": "Older corporate setups."},
    "qr_login": {"label": "Scan QR to log in (shared tablets)", "hi": "QR se login", "kind": "primary",
                 "android": "ML Kit barcode", "ios": "VisionKit", "server": "short-lived code shown on the admin's screen",
                 "screens": ["login_staff"], "cost": "free", "note": "For kiosks / counters."},
    "device_binding": {"label": "Approved phones only", "hi": "sirf manzoor phone", "kind": "policy",
                       "android": "Play Integrity + Keystore key per device", "ios": "App Attest", "server": "new device -> admin approval",
                       "screens": ["security_settings"], "cost": "free", "note": "For payroll / patient data apps."},
}

POLICY = {"otp_digits": 6, "otp_minutes": 5, "otp_tries": 3, "otp_sends_per_hour": 5, "lockout_after": 5, "lockout_minutes": 15,
          "access_token_minutes": 15, "refresh_days": 30, "refresh_rotation": True, "idle_lock_minutes": 5, "password_min": 10,
          "max_devices": 3}


def plan(methods: list[str], money: bool, staff: bool, sensitive: bool) -> dict[str, Any]:
    """Her chosen methods -> a complete, store-safe login plan."""
    ms = [m for m in methods if m in METHODS]
    if not any(METHODS[m]["kind"] in ("primary", "social", "sso") for m in ms):
        ms.insert(0, "employee_otp" if staff else "phone_otp")
    warnings: list[str] = []
    if "google" in ms and "apple" not in ms:
        ms.append("apple")
        warnings.append("Google login hai, isliye iPhone par 'Sign in with Apple' bhi joda (App Store 4.8).")
    if (staff or money or sensitive) and not any(METHODS[m]["kind"] == "unlock" for m in ms):
        ms.append("biometric_unlock")
    admin_mfa = staff or money or sensitive
    if admin_mfa and not any(METHODS[m]["kind"] == "mfa" for m in ms):
        ms.append("totp_mfa")
    if sensitive and "device_binding" not in ms:
        ms.append("device_binding")
    if "magic_link" in ms or "passkey" in ms:
        warnings.append("Passkey / email link ke liye business ka apna domain chahiye (app link files).")
    if any(m in ms for m in ("phone_otp", "employee_otp", "sms_mfa")):
        warnings.append("SMS OTP: DLT par registered template aur SMS provider chahiye (TRAI).")
    screens: list[str] = []
    for m in ms:
        for s in METHODS[m]["screens"]:
            if s not in screens:
                screens.append(s)
    rules = [
        f"OTP {POLICY['otp_digits']} digits, {POLICY['otp_minutes']} min, {POLICY['otp_tries']} tries, max {POLICY['otp_sends_per_hour']} per hour per number; stored hashed.",
        f"{POLICY['lockout_after']} wrong tries -> {POLICY['lockout_minutes']} min lock; the account owner is told.",
        f"Access token {POLICY['access_token_minutes']} min, refresh {POLICY['refresh_days']} days rotating; sign-out ends every token on the server.",
        "Passwords / OTP / PIN never logged, never sent to Hoola or any chat; tokens only in Keystore / Keychain.",
        "In-app 'Delete account' on both stores (data erased or anonymised within 30 days, legal records kept as the law says).",
        "New phone / role change / export / payroll and payment settings ask for the second step." if admin_mfa else
        "Second step for admins.",
    ]
    if staff:
        rules.append("Staff cannot sign up: the admin invites by number / email to a branch and role; leaving staff are switched off at once.")
    return {"methods": [{"id": m, **{k: METHODS[m][k] for k in ("label", "hi", "kind", "android", "ios", "server", "note", "cost")}}
                        for m in ms],
            "ids": ms, "admin_mfa": admin_mfa, "screens": screens, "rules": rules, "warnings": warnings, "policy": dict(POLICY)}


def counts() -> dict[str, int]:
    return {"login_methods": len(METHODS)}
