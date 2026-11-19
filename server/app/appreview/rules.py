"""What the App Review Sahayak checks, why it matters (plain English), and how to fix it. Pure data + small helpers.

Every risk has: code, title, area, severity, MASVS control, explanation, fix and (where it helps) a code snippet per stack.
Policy facts carry a source id (SOURCES) with the date they were checked. They are starter facts for her review, not legal
advice; store policies change, so the report always says "checked on <date>".
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

CHECKED_ON = "2026-10-23"

SEVERITIES = ("critical", "high", "medium", "low", "info")
SEV_LABEL = {"critical": "Critical", "high": "Serious", "medium": "Needs attention", "low": "Minor", "info": "Information"}
SEV_WEIGHT = {"critical": 25, "high": 12, "medium": 5, "low": 2, "info": 0}
AREAS = {"security": "Security (code / data)", "privacy": "Privacy", "play": "Google Play policy", "apple": "Apple App Store",
         "dpdp": "DPDP Act (India)", "rbi": "RBI / NPCI (payments)", "web": "Website"}

SOURCES: dict[str, dict[str, str]] = {
    "play_target": {"title": "Android Developers: Meet Google Play's target API level requirement",
                    "url": "https://developer.android.com/google/play/requirements/target-sdk", "date": "2026-10-23"},
    "play_jul26": {"title": "Google Play July 2026 policy update (third-party AI under User Data, READ_CALL_LOG verification "
                            "use ended, Play Console registration, content rating)",
                   "url": "https://ecorpit.com/google-play-july-2026-policy-update-ai-user-data-compliance/", "date": "2026-10-23"},
    "play_perms": {"title": "Google Play Developer Policy Center: Permissions and APIs that access sensitive information (SMS / Call Log, "
                            "All files access, QUERY_ALL_PACKAGES, background location, exact alarm, full-screen intent, "
                            "photo & video, accessibility, VpnService, REQUEST_INSTALL_PACKAGES)",
                   "url": "https://play.google.com/about/privacy-security-deception/permissions/", "date": "2026-10-23"},
    "play_datasafety": {"title": "Play Console Help: Provide information for Google Play's Data safety section",
                        "url": "https://support.google.com/googleplay/android-developer/answer/10787469", "date": "2026-10-23"},
    "play_delete": {"title": "Play Console Help: Understanding Google Play's app account deletion requirements",
                    "url": "https://support.google.com/googleplay/android-developer/answer/13327111", "date": "2026-10-23"},
    "play_families": {"title": "Play Console Help: Families policies / Families Self-Certified Ads SDK Program",
                      "url": "https://support.google.com/googleplay/android-developer/answer/9893335", "date": "2026-10-23"},
    "play_16kb": {"title": "Android Developers: Support 16 KB page sizes (required on Play for apps targeting Android 15+ "
                           "from 1 Nov 2025)",
                  "url": "https://developer.android.com/guide/practices/page-sizes", "date": "2026-10-23"},
    "masvs": {"title": "OWASP MASVS v2.1.0 (STORAGE, CRYPTO, AUTH, NETWORK, PLATFORM, CODE, RESILIENCE, PRIVACY)",
              "url": "https://mas.owasp.org/MASVS/", "date": "2026-10-23"},
    "exodus": {"title": "Exodus Privacy tracker list (class-name signatures of tracker SDKs)",
               "url": "https://reports.exodus-privacy.eu.org/en/trackers/", "date": "2026-10-23"},
    "apple": {"title": "Apple App Store Review Guidelines (5.1.1 data collection + account deletion, 4.8 Sign in with Apple, "
                       "privacy manifests for listed SDKs)",
              "url": "https://developer.apple.com/app-store/review/guidelines/", "date": "2026-10-23"},
    "dpdp": {"title": "Digital Personal Data Protection Act 2023 + DPDP Rules 2025 (notified 13 Nov 2025; notice / consent / "
                      "children duties phased in by 13 May 2027)",
             "url": "https://www.meity.gov.in/data-protection-framework", "date": "2026-10-23"},
    "rbi_local": {"title": "RBI circular on Storage of Payment System Data, RBI/2017-18/153 (6 Apr 2018)",
                  "url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11244", "date": "2026-10-23"},
    "rbi_pa": {"title": "RBI Guidelines on Regulation of Payment Aggregators and Payment Gateways (17 Mar 2020) + card-on-file "
                        "tokenisation (merchants may not store card data, from 1 Oct 2022)",
               "url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11822", "date": "2026-10-23"},
    "owasp_headers": {"title": "OWASP Secure Headers Project", "url": "https://owasp.org/www-project-secure-headers/",
                      "date": "2026-10-23"},
}

# Google Play target API (phones / tablets). From 31 Aug 2026: new apps + updates must target 36; existing apps below 35
# stop being offered to new users on newer Android. Extension to 1 Nov 2026 on request.
PLAY_TARGET = {"new_and_updates": 36, "existing_min": 35, "since": date(2026, 8, 31), "extension_until": date(2026, 11, 1),
               "wear_auto": 35, "tv_xr": 34}


def _sn(**kw: str) -> dict[str, str]:
    return kw


# ---------------------------------------------------------------- the catalogue
RULES: dict[str, dict[str, Any]] = {
    # ---- build / manifest
    "debuggable": dict(
        title="The app is built in debug mode", area="security", sev="high", masvs="MASVS-RESILIENCE-4",
        explain="With android:debuggable=true anyone can look inside the app over USB and read its data. Play Store will not even "
                "accept such a build.",
        fix="Make a release build (remove debuggable; the Gradle release buildType keeps it false by itself).",
        snippet=_sn(android="buildTypes {\n    release {\n        isDebuggable = false\n        isMinifyEnabled = true\n    }\n}",
                    flutter="flutter build appbundle --release"), refs=["masvs"]),
    "test_only": dict(
        title="Build made only for testing (testOnly)", area="play", sev="high", masvs="MASVS-CODE-1",
        explain="An APK with android:testOnly=true cannot be uploaded to Play and does not install on an ordinary phone.",
        fix="Build a release AAB instead of the APK from Android Studio's 'Run'.", snippet={}, refs=["masvs"]),
    "allow_backup": dict(
        title="App data goes into the phone backup", area="security", sev="medium", masvs="MASVS-STORAGE-2",
        explain="allowBackup is on (or not written, so it is on by default). Login tokens / customer data can reach another phone through "
                "Google backup or 'adb backup'.",
        fix="Set allowBackup=false, or keep only the needed files in the backup with dataExtractionRules / fullBackupContent.",
        snippet=_sn(android='<application\n    android:allowBackup="false"\n    android:dataExtractionRules="@xml/data_extraction_rules"\n    ...>'),
        refs=["masvs"]),
    "cleartext": dict(
        title="Traffic without HTTPS (http://) is allowed", area="security", sev="high", masvs="MASVS-NETWORK-1",
        explain="The app can talk over plain http. Someone on the Wi-Fi / network can read or change login, OTP and payment details "
                "on the way.",
        fix="Keep usesCleartextTraffic=false and make every API URL https. For an old server, allow only that one domain in the "
            "network security config.",
        snippet=_sn(android='<!-- AndroidManifest.xml -->\n<application android:usesCleartextTraffic="false"\n    '
                            'android:networkSecurityConfig="@xml/network_security_config" ...>',
                    flutter="// keep every URL on https://\nfinal uri = Uri.https('api.example.in', '/v1/orders');"),
        refs=["masvs"]),
    "nsc_cleartext": dict(
        title="Network security config allows http everywhere", area="security", sev="high", masvs="MASVS-NETWORK-1",
        explain="network_security_config has cleartextTrafficPermitted=\"true\" on base-config / a domain: {detail}.",
        fix="Set cleartextTrafficPermitted to false; if needed, allow it for one old domain only inside <domain-config>.",
        snippet=_sn(android='<network-security-config>\n  <base-config cleartextTrafficPermitted="false">\n    <trust-anchors>'
                            '<certificates src="system"/></trust-anchors>\n  </base-config>\n</network-security-config>'),
        refs=["masvs"]),
    "nsc_user_certs": dict(
        title="The app trusts certificates added by the user", area="security", sev="high", masvs="MASVS-NETWORK-1",
        explain="trust-anchors has <certificates src=\"user\"/> in the release build. Anyone can add their own certificate to the phone and "
                "read the app's encrypted traffic.",
        fix="Keep user certificates only inside <debug-overrides>.",
        snippet=_sn(android='<debug-overrides>\n  <trust-anchors><certificates src="user"/></trust-anchors>\n</debug-overrides>'),
        refs=["masvs"]),
    "exported_component": dict(
        title="Other apps can start your screen / service directly", area="security", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="{detail} is exported and asks for no permission. Any app on the phone can open it / send to it; if there is data or an "
                "action inside that needs no login, that is a risk.",
        fix="Write android:exported=\"false\" on whatever should not open from outside; if it must, add a signature-level permission.",
        snippet=_sn(android='<activity android:name=".OrderDetailActivity" android:exported="false" />\n'
                            '<!-- or -->\n<service android:name=".SyncService" android:exported="true"\n'
                            '    android:permission="com.example.permission.SYNC" />'),
        refs=["masvs"]),
    "exported_provider": dict(
        title="Content provider is open to everyone", area="security", sev="high", masvs="MASVS-PLATFORM-1",
        explain="{detail} is an exported provider with no read/write permission. Other apps can read your app's database / files.",
        fix="Keep exported=false, or add readPermission / writePermission (signature); use FileProvider to share files.",
        snippet=_sn(android='<provider android:name="androidx.core.content.FileProvider"\n    android:authorities="${applicationId}.files"\n'
                            '    android:exported="false" android:grantUriPermissions="true" />'), refs=["masvs"]),
    "missing_exported": dict(
        title="android:exported is not written (Android 12+)", area="play", sev="high", masvs="MASVS-PLATFORM-1",
        explain="{detail} has an intent-filter but no android:exported. On Android 12 / targetSdk 31+ such an app does not install "
                "and the build fails.",
        fix="Write android:exported=\"true\" or \"false\" clearly on every activity / service / receiver that has an intent-filter.", snippet={},
        refs=["masvs"]),
    "target_sdk": dict(
        title="Target API is old: Play will not accept an update", area="play", sev="critical", masvs="MASVS-CODE-1",
        explain="targetSdk {detail}. From 31 Aug 2026, new apps and every update on Play must target Android 16 (API 36); "
                "old apps below 35 stop being shown to new users on newer Android phones (an extension until 1 Nov 2026 "
                "could be requested).",
        fix="Set compileSdk + targetSdk to 36 and test the Android 16 behaviour changes (edge-to-edge, predictive back, foreground service "
            "types).",
        snippet=_sn(android="android {\n    compileSdk = 36\n    defaultConfig {\n        targetSdk = 36\n    }\n}",
                    flutter="// android/app/build.gradle(.kts)\ndefaultConfig {\n    targetSdk = 36\n}"),
        refs=["play_target"]),
    "target_sdk_soon": dict(
        title="Target API below 36: raise it before the next update", area="play", sev="medium", masvs="MASVS-CODE-1",
        explain="targetSdk {detail}. The listing stays up for now, but the next update will go through only when it targets 36.",
        fix="Set targetSdk to 36 in the next release.", snippet=_sn(android="defaultConfig { targetSdk = 36 }"), refs=["play_target"]),
    "min_sdk_old": dict(
        title="Supports very old Android versions", area="security", sev="low", masvs="MASVS-CODE-1",
        explain="minSdk {detail}: Android this old gets no security updates and lacks several safety features "
                "(scoped storage, TLS 1.3).",
        fix="Consider a minSdk of at least 24 (Android 7); 26+ for apps with payments / login.", snippet={}, refs=["masvs"]),
    "unsigned": dict(
        title="The APK is not signed", area="play", sev="critical", masvs="MASVS-CODE-1",
        explain="An unsigned APK does not install and cannot be uploaded to Play.",
        fix="Sign it with the release keystore (keep Play App Signing on).", snippet={}, refs=["masvs"]),
    "debug_cert": dict(
        title="Signed with the Android Debug key", area="play", sev="high", masvs="MASVS-CODE-1",
        explain="The debug key is the same on every developer's computer; such an APK is not a release and Play does not accept it.",
        fix="Sign with your own release key (or the Play App Signing upload key).",
        snippet=_sn(android="signingConfigs {\n    create(\"release\") { storeFile = file(System.getenv(\"KEYSTORE\")) ... }\n}"),
        refs=["masvs"]),
    "v1_only": dict(
        title="Only the old v1 signature", area="security", sev="medium", masvs="MASVS-CODE-1",
        explain="Only the JAR (v1) signature is present. targetSdk 30+ needs v2; with v1, parts of the file can be changed without detection.",
        fix="Turn on v2 + v3 signatures with apksigner / Gradle (the Gradle default).", snippet={}, refs=["masvs"]),
    "no_arm64": dict(
        title="No 64-bit (arm64) native library", area="play", sev="high", masvs="MASVS-CODE-1",
        explain="There is native code but no arm64-v8a version: {detail}. Play requires 64-bit.",
        fix="Add arm64-v8a to abiFilters / add the library's 64-bit build.", snippet={}, refs=["play_16kb"]),
    "page_16kb": dict(
        title="Native library is not ready for the 16 KB page size", area="play", sev="high", masvs="MASVS-CODE-1",
        explain="The LOAD alignment of {detail} is less than 16 KB. From 1 Nov 2025, new apps / updates targeting Android 15+ must support the "
                "16 KB page size; the app can crash on such phones.",
        fix="Rebuild with NDK r28+ / AGP 8.5.1+ (or -Wl,-z,max-page-size=16384); get a new version of any third-party .so.",
        snippet=_sn(android="# CMake / ndk-build\ntarget_link_options(mylib PRIVATE \"-Wl,-z,max-page-size=16384\")",
                    flutter="# rebuild on Flutter 3.32+ / AGP 8.5.1+"), refs=["play_16kb"]),
    "zip_align_16kb": dict(
        title=".so in the APK is not aligned to 16 KB", area="play", sev="medium", masvs="MASVS-CODE-1",
        explain="{detail} is stored uncompressed but not on a 16 KB boundary. This library will not load on 16 KB phones.",
        fix="Build with AGP 8.5.1+ (zipalign -P 16) or useLegacyPackaging.", snippet={}, refs=["play_16kb"]),
    # ---- permissions / Play restricted
    "perm_sms": dict(
        title="SMS permission: Play gives it only to the default SMS app", area="play", sev="critical", masvs="MASVS-PLATFORM-1",
        explain="The app asks for {detail}. Play gives SMS / Call log permissions only for the work of a default SMS / phone app, not for "
                "reading an OTP. The app can be rejected / removed.",
        fix="For OTPs use the SMS Retriever API or the SMS User Consent API (no permission needed).",
        snippet=_sn(android="SmsRetriever.getClient(context).startSmsRetriever()\n// the SMS must carry the app's 11-character hash",
                    flutter="// package: smart_auth / sms_autofill (they run on SMS Retriever, not READ_SMS)"),
        refs=["play_perms"]),
    "perm_call_log": dict(
        title="Call log permission", area="play", sev="critical", masvs="MASVS-PLATFORM-1",
        explain="The app asks for {detail}. Play gives it only to the default dialer; from July 2026 'verify the account by a call' is also not allowed with it.",
        fix="Verify the number with the SMS Retriever / Digital Credentials API; remove the need for the call log.", snippet={},
        refs=["play_perms", "play_jul26"]),
    "perm_all_files": dict(
        title="Permission for all files (MANAGE_EXTERNAL_STORAGE)", area="play", sev="high", masvs="MASVS-STORAGE-1",
        explain="'All files access' is given only to apps like file managers / backup / antivirus. Not for picking a photo / PDF.",
        fix="Use the Photo Picker / Storage Access Framework (ACTION_OPEN_DOCUMENT).",
        snippet=_sn(android="val pick = registerForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri -> }\n"
                            "pick.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))",
                    flutter="// image_picker / file_picker: they use the Photo Picker + SAF, no permission"),
        refs=["play_perms"]),
    "perm_query_all": dict(
        title="List of all apps on the phone (QUERY_ALL_PACKAGES)", area="play", sev="high", masvs="MASVS-PRIVACY-1",
        explain="Play gives it only to apps like antivirus / launcher / device search, with a declaration form.",
        fix="Inside <queries> in the manifest, list only the packages / intents you need (such as UPI apps).",
        snippet=_sn(android='<queries>\n  <intent><action android:name="android.intent.action.VIEW"/>\n'
                            '    <data android:scheme="upi"/></intent>\n</queries>'), refs=["play_perms"]),
    "perm_bg_location": dict(
        title="Location even when the app is closed (background location)", area="play", sev="high", masvs="MASVS-PRIVACY-1",
        explain="For background location Play asks for a declaration + video and a clear 'prominent disclosure' inside the app; if it is not core "
                "to the app, it is rejected.",
        fix="Where possible take location only while the app is open (foreground); for work like delivery tracking use a foreground service of "
            "type location + a disclosure screen.", snippet={}, refs=["play_perms", "play_datasafety"]),
    "perm_install": dict(
        title="Permission to install other apps", area="play", sev="high", masvs="MASVS-PLATFORM-1",
        explain="REQUEST_INSTALL_PACKAGES is given only for core work such as app stores / file managers / device management.",
        fix="Update your own app through the Play In-App Updates API.", snippet={}, refs=["play_perms"]),
    "perm_exact_alarm": dict(
        title="Exact alarm permission", area="play", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="{detail}: USE_EXACT_ALARM is only for alarm clock / calendar apps; SCHEDULE_EXACT_ALARM is off by default on Android 14.",
        fix="For reminders use WorkManager / inexact AlarmManager.setWindow; use an exact alarm only if it really is an alarm app.", snippet={},
        refs=["play_perms"]),
    "perm_fullscreen": dict(
        title="Full-screen intent (whole screen on the lock screen)", area="play", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="From Android 14, USE_FULL_SCREEN_INTENT is granted by default only to calling / alarm apps; others need a Play declaration.",
        fix="Use a normal high-priority notification.", snippet={}, refs=["play_perms"]),
    "perm_media": dict(
        title="Permission to read photos / videos", area="play", sev="medium", masvs="MASVS-PRIVACY-1",
        explain="Play's Photo & Video Permissions policy: READ_MEDIA_IMAGES / VIDEO only for apps whose core work is a gallery; "
                "use the Photo Picker to pick one or two photos.",
        fix="Use the Android Photo Picker and remove the permission.",
        snippet=_sn(android="ActivityResultContracts.PickVisualMedia()", flutter="ImagePicker().pickImage(source: ImageSource.gallery)"),
        refs=["play_perms"]),
    "perm_accessibility": dict(
        title="Accessibility service", area="play", sev="critical", masvs="MASVS-PLATFORM-1",
        explain="An accessibility service can read the screen and tap. Play gives it only for disability-support (or declared core) work; "
                "it is not allowed for assistants / automation.",
        fix="Remove the accessibility service; do the work with Android's public APIs.", snippet={}, refs=["play_perms"]),
    "perm_vpn": dict(
        title="VPN service", area="play", sev="medium", masvs="MASVS-NETWORK-1",
        explain="Apps with VpnService need a Play declaration and cannot use traffic data for ads.",
        fix="Fill in the VpnService declaration in Play Console.", snippet={}, refs=["play_perms"]),
    "perm_device_admin": dict(
        title="Device admin", area="play", sev="high", masvs="MASVS-PLATFORM-1",
        explain="Device admin can lock / wipe the phone and block uninstall; Play gives it for very limited work.",
        fix="Remove it if you can; for enterprise use the Android Enterprise APIs.", snippet={}, refs=["play_perms"]),
    "perm_battery": dict(
        title="Asking to skip battery optimisation", area="play", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="On Play, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS is only for an app whose core work breaks without it.",
        fix="Use FCM high-priority messages / WorkManager instead.", snippet={}, refs=["play_perms"]),
    "perm_overlay": dict(
        title="Screen over other apps (SYSTEM_ALERT_WINDOW)", area="security", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="An overlay can show a fake screen; users get worried and Play review looks at it closely.",
        fix="Use the notification / bubble API.", snippet={}, refs=["play_perms"]),
    "perm_sensitive": dict(
        title="Permission for personal data", area="privacy", sev="info", masvs="MASVS-PRIVACY-1",
        explain="{detail}: this data must be listed in the Data safety form; tell the user why you need it before asking for the permission.",
        fix="Ask for the permission only when that feature opens; give correct details in the Data safety form.", snippet={}, refs=["play_datasafety"]),
    "fgs_types": dict(
        title="Foreground service type / declaration", area="play", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="{detail}. On Android 14 (target 34+) every foreground service must state its type and be declared in Play Console.",
        fix="<service android:foregroundServiceType=\"...\"> + FOREGROUND_SERVICE_<TYPE> permission + Play Console declaration.",
        snippet=_sn(android='<service android:name=".TrackService" android:foregroundServiceType="location" />\n'
                            '<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />'),
        refs=["play_perms"]),
    # ---- secrets / code
    "secret": dict(
        title="A secret key is hidden inside the app", area="security", sev="critical", masvs="MASVS-STORAGE-1",
        explain="{detail}. Anyone can open the app's file, take this key out and misuse your account / server "
                "(the bill comes to you).",
        fix="Change this key AT ONCE (rotate / revoke), then keep the secret only on your own server; the app talks to your server, the server "
            "talks to the provider.",
        snippet=_sn(android="// app -> your server (with the login token) -> provider API (the secret only in the server's .env)\n"
                            "val res = api.post(\"https://api.your-server.in/pay/order\", body)",
                    flutter="// --dart-define also shows up in the APK: never put a secret in the app\n"
                            "final r = await http.post(Uri.https('api.your-server.in', '/pay/order'), headers: {'Authorization': 'Bearer $userToken'});",
                    web="# .env (server only, not in git)\nRAZORPAY_KEY_SECRET=...\n# .gitignore\n.env"),
        refs=["masvs"]),
    "public_key": dict(
        title="Public / client key is in the app (fine, but restrict it)", area="security", sev="low", masvs="MASVS-STORAGE-1",
        explain="{detail}. It is normal for this key to be in the app, but without a package name + SHA-1 and needed-APIs-only restriction in the "
                "Google Cloud / provider console, anyone can use it for their own work and raise your bill.",
        fix="Add a key restriction in the console (Android app: package + SHA-1; only the needed APIs).", snippet={}, refs=["masvs"]),
    "weak_tls": dict(
        title="HTTPS certificate check is turned off", area="security", sev="critical", masvs="MASVS-NETWORK-1",
        explain="{detail}: the code accepts every certificate. Anyone in the middle can pose as a fake server and take login / payment data.",
        fix="Remove this custom TrustManager / HostnameVerifier / badCertificateCallback; leave the system's default check in place.",
        snippet=_sn(android="// remove: object : X509TrustManager { override fun checkServerTrusted(...) {} }\n"
                            "val client = OkHttpClient.Builder().build()   // default check",
                    flutter="// remove: client.badCertificateCallback = (cert, host, port) => true;"),
        refs=["masvs"]),
    "webview_js_bridge": dict(
        title="JavaScript bridge in a WebView", area="security", sev="medium", masvs="MASVS-PLATFORM-2",
        explain="{detail}: if an outside page opens in the WebView, it can run your app's Java/Kotlin functions.",
        fix="Open only your own https pages (URL allow-list), use addJavascriptInterface only when needed; turn file access off.",
        snippet=_sn(android="webView.settings.allowFileAccess = false\nwebView.webViewClient = object : WebViewClient() {\n"
                            "  override fun shouldOverrideUrlLoading(v: WebView, r: WebResourceRequest) = r.url.host != \"app.your-site.in\"\n}"),
        refs=["masvs"]),
    "weak_crypto": dict(
        title="Weak encryption", area="security", sev="medium", masvs="MASVS-CRYPTO-1",
        explain="{detail}: methods like MD5 / SHA-1 / DES / AES-ECB are easily broken today.",
        fix="Use AES-GCM (Android Keystore key) and SHA-256; for passwords use argon2 / bcrypt on the server.",
        snippet=_sn(android='val c = Cipher.getInstance("AES/GCM/NoPadding")   // key from the Android Keystore'), refs=["masvs"]),
    "insecure_random": dict(
        title="Weak random for a token / OTP", area="security", sev="medium", masvs="MASVS-CRYPTO-1",
        explain="{detail}: a number made with java.util.Random / Math.random can be guessed.",
        fix="SecureRandom (Android) / Random.secure() (Dart) / crypto.getRandomValues (JS).",
        snippet=_sn(android="val bytes = ByteArray(16).also { java.security.SecureRandom().nextBytes(it) }",
                    flutter="final r = Random.secure();"), refs=["masvs"]),
    "plain_storage": dict(
        title="Token / password in open storage", area="security", sev="medium", masvs="MASVS-STORAGE-1",
        explain="{detail}: a plain token in SharedPreferences / localStorage can be taken out through root or a backup.",
        fix="Encrypt it with the Android Keystore (EncryptedSharedPreferences / flutter_secure_storage); never store the password.",
        snippet=_sn(android="// androidx.security:security-crypto or DataStore + Keystore AES-GCM",
                    flutter="const storage = FlutterSecureStorage();\nawait storage.write(key: 'token', value: token);"),
        refs=["masvs"]),
    "log_secret": dict(
        title="Password / token is written to the log", area="security", sev="medium", masvs="MASVS-STORAGE-2",
        explain="{detail}: logcat ends up in other tools / bug reports.",
        fix="Remove logs from the release build (R8 -assumenosideeffects) and never log a secret.", snippet={}, refs=["masvs"]),
    "sql_concat": dict(
        title="User text joined straight into SQL", area="security", sev="medium", masvs="MASVS-CODE-4",
        explain="{detail}: SQL injection can read / delete other users' data.",
        fix="Always use ? placeholders / bind arguments.",
        snippet=_sn(android='db.rawQuery("SELECT * FROM orders WHERE phone = ?", arrayOf(phone))',
                    web="db.query('SELECT * FROM orders WHERE phone = $1', [phone])"), refs=["masvs"]),
    "http_url": dict(
        title="http:// address (no HTTPS) in the code", area="security", sev="low", masvs="MASVS-NETWORK-1",
        explain="{detail}", fix="Change these addresses to https://.", snippet={}, refs=["masvs"]),
    "env_committed": dict(
        title=".env / keystore file is kept with the code", area="security", sev="high", masvs="MASVS-STORAGE-1",
        explain="{detail} is in the repo / ZIP. Whoever got the code got every key / the signing key.",
        fix="Remove the file, add it to .gitignore, and change every key inside; it must be removed from git history too.",
        snippet=_sn(web=".env\n*.jks\n*.keystore\nkey.properties\ngoogle-services.json   # if the repo is public"), refs=["masvs"]),
    "eval_js": dict(
        title="JavaScript eval / innerHTML", area="security", sev="low", masvs="MASVS-CODE-4",
        explain="{detail}: outside text can run as code (XSS).", fix="Remove eval; show text with textContent.",
        snippet={}, refs=["masvs"]),
    # ---- SDKs / policy
    "trackers": dict(
        title="Tracking / analytics SDKs found", area="privacy", sev="info", masvs="MASVS-PRIVACY-1",
        explain="{detail}. Their data (device id, usage, location...) must be listed as 'collected / shared' in the Data safety form and named "
                "in the privacy policy.",
        fix="Fill in the form from each SDK's own 'Data safety' guide; remove any SDK you do not need.", snippet={},
        refs=["exodus", "play_datasafety"]),
    "ads_id": dict(
        title="Advertising ID", area="privacy", sev="low", masvs="MASVS-PRIVACY-1",
        explain="{detail}. In Data safety list 'Device or other IDs' and the ads purpose; AD_ID is not allowed in children's apps.",
        fix="If you show no ads, add <uses-permission ... AD_ID tools:node=\"remove\"/>.",
        snippet=_sn(android='<uses-permission android:name="com.google.android.gms.permission.AD_ID" tools:node="remove"/>'),
        refs=["play_datasafety", "play_families"]),
    "ai_sdk": dict(
        title="User data goes to an outside AI service", area="play", sev="medium", masvs="MASVS-PRIVACY-1",
        explain="{detail}. Play July 2026 update: the User Data policy also applies to third-party AI integration: say it in the privacy policy + Data "
                "safety, get the user's consent before sending data, and use it only for the stated purpose.",
        fix="A clear consent screen before sending to the AI; name the provider in the privacy policy; the key on the server, not in the app.",
        snippet={}, refs=["play_jul26"]),
    "account_deletion": dict(
        title="A way to delete the account (Play + App Store)", area="play", sev="medium", masvs="MASVS-PRIVACY-4",
        explain="The app shows login / sign-up ({detail}). Play: a way to delete the account + data inside the app and from a web link "
                "is required; Apple 5.1.1(v) also asks for delete inside the app.",
        fix="A Settings > 'Delete account' screen + a delete request page on the website; put the link in Play Console Data safety.",
        snippet={}, refs=["play_delete", "apple"]),
    "families": dict(
        title="App for children: Families policy", area="play", sev="high", masvs="MASVS-PRIVACY-1",
        explain="You said the app is for children. {detail}. The Families policy allows only Families-certified ads SDKs, bans things like AD_ID / "
                "location, and children's data may not be used for ads.",
        fix="Remove non-certified SDKs, remove AD_ID, fill in the Teacher Approved / target audience form correctly.", snippet={},
        refs=["play_families"]),
    "data_safety": dict(
        title="Data safety form: what to fill in", area="play", sev="info", masvs="MASVS-PRIVACY-1",
        explain="Found in the app: {detail}. What you fill in the form must match what the app really does, or Play blocks the update.",
        fix="Fill in the form from this report's 'Data safety draft' sheet and match it with each SDK's guide.", snippet={},
        refs=["play_datasafety"]),
    "content_rating": dict(
        title="Content rating and Play Console registration", area="play", sev="info", masvs="MASVS-CODE-1",
        explain="July 2026 policy: apps without a content rating are non-compliant and every Play app must be registered in "
                "Play Console.", fix="Complete the rating questionnaire in Play Console > Policy > App content.", snippet={},
        refs=["play_jul26"]),
    "apple_basics": dict(
        title="For iPhone (App Store) too", area="apple", sev="info", masvs="MASVS-PRIVACY-1",
        explain="{detail}", fix="Fill in PrivacyInfo.xcprivacy + App Privacy labels in Xcode; if there is a third-party login, add Sign in with Apple.",
        snippet={}, refs=["apple"]),
    "dpdp_notice": dict(
        title="DPDP: notice + consent before personal data", area="dpdp", sev="medium", masvs="MASVS-PRIVACY-3",
        explain="The app takes personal data ({detail}). DPDP Act 2023 + Rules 2025: a clear notice (what, why, how to get it removed), separate "
                "consent, an equally easy way to withdraw consent, and a grievance contact. Most duties apply from 13 May 2027.",
        fix="A Hindi / English notice screen + a record of consent before taking data the first time; in Settings 'withdraw consent' and "
            "the grievance officer's contact.", snippet={}, refs=["dpdp"]),
    "dpdp_children": dict(
        title="DPDP: data of children (under 18)", area="dpdp", sev="high", masvs="MASVS-PRIVACY-3",
        explain="You said the app is for children. Under DPDP, data of anyone under 18 needs verifiable consent from a parent, "
                "and tracking / behaviour monitoring / ads targeted at them are not allowed.",
        fix="A parent consent flow (age gate + parent verification); remove tracking / ads SDKs.", snippet={}, refs=["dpdp"]),
    "rbi_payment": dict(
        title="Payment SDK found: RBI rules", area="rbi", sev="info", masvs="MASVS-STORAGE-1",
        explain="{detail}. The payment aggregator must be RBI-authorised; never keep a card number / CVV in the app or on the server "
                "(card-on-file tokenisation, from 1 Oct 2022); store payment data only in India (RBI 6 Apr 2018).",
        fix="Take payment only through the SDK's checkout; verify the order amount and status on your own SERVER with the payment gateway (signature), "
            "not on the app's word.", snippet=_sn(web="# server: Razorpay webhook / payment signature verify\n"
                                                      "hmac_sha256(order_id + '|' + payment_id, KEY_SECRET) == signature"),
        refs=["rbi_pa", "rbi_local"]),
    "rbi_card_fields": dict(
        title="The app takes the card number / CVV itself", area="rbi", sev="high", masvs="MASVS-STORAGE-1",
        explain="{detail}: taking and keeping card details on your own screen can go against the RBI tokenisation rules and PCI-DSS.",
        fix="Cards only inside the payment gateway's SDK / hosted checkout; keep only the token yourself.", snippet={}, refs=["rbi_pa"]),
    "sms_and_payment": dict(
        title="Reading SMS + payments together", area="security", sev="high", masvs="MASVS-PLATFORM-1",
        explain="The app reads SMS and also takes payments: fraud apps carry this same pair; both Play and users will be suspicious.",
        fix="Remove the SMS permission (SMS Retriever).", snippet={}, refs=["play_perms"]),
    # ---- website
    "web_https": dict(title="Website is not on HTTPS / does not move from http to https", area="web", sev="high", masvs="MASVS-NETWORK-1",
                      explain="{detail}", fix="Add an SSL certificate (Let's Encrypt / Cloudflare) and a 301 redirect from http -> https.",
                      snippet=_sn(web="server { listen 80; server_name your-site.in; return 301 https://$host$request_uri; }"),
                      refs=["owasp_headers"]),
    "web_cert": dict(title="SSL certificate expires soon", area="web", sev="medium", masvs="MASVS-NETWORK-1", explain="{detail}",
                     fix="Turn on auto-renew (certbot timer / hosting panel).", snippet={}, refs=["owasp_headers"]),
    "web_hsts": dict(title="No HSTS header", area="web", sev="low", masvs="MASVS-NETWORK-1",
                     explain="The browser is not told 'always https'; the first http request can be intercepted on the way.",
                     fix="Strict-Transport-Security header.", snippet=_sn(web='add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'),
                     refs=["owasp_headers"]),
    "web_csp": dict(title="No Content-Security-Policy", area="web", sev="low", masvs="MASVS-CODE-4",
                    explain="Without a CSP, an injected script (XSS) runs freely.",
                    fix="Start with Content-Security-Policy-Report-Only, then enforce it.",
                    snippet=_sn(web="add_header Content-Security-Policy \"default-src 'self'; img-src 'self' data: https:; frame-ancestors 'self'\" always;"),
                    refs=["owasp_headers"]),
    "web_frame": dict(title="Website can open inside another site's frame", area="web", sev="low", masvs="MASVS-PLATFORM-1",
                      explain="No X-Frame-Options / frame-ancestors: clickjacking (your site under a fake button).",
                      fix="X-Frame-Options: SAMEORIGIN (or CSP frame-ancestors).", snippet=_sn(web='add_header X-Frame-Options "SAMEORIGIN" always;'),
                      refs=["owasp_headers"]),
    "web_nosniff": dict(title="No X-Content-Type-Options", area="web", sev="low", masvs="MASVS-CODE-4",
                        explain="The browser can guess and change the file type.", fix="X-Content-Type-Options: nosniff.",
                        snippet=_sn(web='add_header X-Content-Type-Options "nosniff" always;'), refs=["owasp_headers"]),
    "web_referrer": dict(title="No Referrer-Policy", area="web", sev="info", masvs="MASVS-PRIVACY-1",
                         explain="The full page address (sometimes with a token) goes to other sites.",
                         fix="Referrer-Policy: strict-origin-when-cross-origin.", snippet={}, refs=["owasp_headers"]),
    "web_server_leak": dict(title="Server software version is visible", area="web", sev="low", masvs="MASVS-CODE-3",
                            explain="{detail}: an attacker learns which old version it is.",
                            fix="server_tokens off / remove X-Powered-By; keep the software updated.", snippet=_sn(web="server_tokens off;"),
                            refs=["owasp_headers"]),
    "web_cookie": dict(title="Cookie without Secure / HttpOnly / SameSite", area="web", sev="medium", masvs="MASVS-AUTH-2",
                       explain="{detail}: the login cookie can be stolen by a script or over http.",
                       fix="Set-Cookie: ...; Secure; HttpOnly; SameSite=Lax.", snippet={}, refs=["owasp_headers"]),
    "web_mixed": dict(title="http:// items on an HTTPS page (mixed content)", area="web", sev="medium", masvs="MASVS-NETWORK-1",
                      explain="{detail}: the browser blocks them or shows the page as 'Not secure'.", fix="Make every src / href https://.",
                      snippet={}, refs=["owasp_headers"]),
    "web_exposed": dict(title="An internal file is open on the website", area="web", sev="critical", masvs="MASVS-STORAGE-1",
                        explain="{detail} can be read by anyone on the internet (code, passwords, database address).",
                        fix="Remove the file from the server / deny it in nginx, and change every key / password inside.",
                        snippet=_sn(web="location ~ /\\.(git|env|svn|hg) { deny all; return 404; }"), refs=["owasp_headers"]),
    "web_security_txt": dict(title="No security.txt", area="web", sev="info", masvs="MASVS-CODE-3",
                             explain="It does not say where someone should report a bug.",
                             fix="Contact: and Expires: in /.well-known/security.txt.", snippet={}, refs=["owasp_headers"]),
}

MASVS_TITLES = {"MASVS-STORAGE": "Storing data safely", "MASVS-CRYPTO": "Encryption", "MASVS-AUTH": "Login / session",
                "MASVS-NETWORK": "Network (HTTPS)", "MASVS-PLATFORM": "Working with Android", "MASVS-CODE": "Code / build",
                "MASVS-RESILIENCE": "Protection from tampering", "MASVS-PRIVACY": "Privacy"}

# ---------------------------------------------------------------- permissions
PERM_RULE = {
    "READ_SMS": "perm_sms", "RECEIVE_SMS": "perm_sms", "SEND_SMS": "perm_sms", "RECEIVE_MMS": "perm_sms", "RECEIVE_WAP_PUSH": "perm_sms",
    "READ_CALL_LOG": "perm_call_log", "WRITE_CALL_LOG": "perm_call_log", "PROCESS_OUTGOING_CALLS": "perm_call_log",
    "MANAGE_EXTERNAL_STORAGE": "perm_all_files", "QUERY_ALL_PACKAGES": "perm_query_all",
    "ACCESS_BACKGROUND_LOCATION": "perm_bg_location", "REQUEST_INSTALL_PACKAGES": "perm_install",
    "USE_EXACT_ALARM": "perm_exact_alarm", "SCHEDULE_EXACT_ALARM": "perm_exact_alarm", "USE_FULL_SCREEN_INTENT": "perm_fullscreen",
    "READ_MEDIA_IMAGES": "perm_media", "READ_MEDIA_VIDEO": "perm_media", "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS": "perm_battery",
    "SYSTEM_ALERT_WINDOW": "perm_overlay",
}
SENSITIVE_PERMS = {  # permission -> Data safety data type
    "ACCESS_FINE_LOCATION": "Location (precise)", "ACCESS_COARSE_LOCATION": "Location (approximate)",
    "READ_CONTACTS": "Contacts", "CAMERA": "Photos / videos (camera)", "RECORD_AUDIO": "Audio (voice / sound recordings)",
    "READ_PHONE_STATE": "Device or other IDs", "READ_PHONE_NUMBERS": "Phone number", "GET_ACCOUNTS": "Email / account",
    "READ_CALENDAR": "Calendar events", "BODY_SENSORS": "Health info", "ACTIVITY_RECOGNITION": "Fitness info",
    "READ_EXTERNAL_STORAGE": "Files and docs", "READ_MEDIA_IMAGES": "Photos", "READ_MEDIA_VIDEO": "Videos",
    "READ_SMS": "SMS / MMS", "READ_CALL_LOG": "Call logs", "BLUETOOTH_SCAN": "Nearby devices",
}
COMPONENT_RULE = {"android.permission.BIND_ACCESSIBILITY_SERVICE": "perm_accessibility",
                  "android.permission.BIND_VPN_SERVICE": "perm_vpn", "android.permission.BIND_DEVICE_ADMIN": "perm_device_admin"}

# ---------------------------------------------------------------- SDKs (class-name prefixes; Exodus-style signatures)
# kind: analytics | ads | attribution | crash | push | engagement | payment | ai | auth ; data = Data safety data types
SDKS: list[dict[str, Any]] = [
    {"p": "com.google.firebase.analytics", "name": "Google Firebase Analytics", "kind": "analytics", "data": ["App interactions", "Device or other IDs"]},
    {"p": "com.google.android.gms.analytics", "name": "Google Analytics", "kind": "analytics", "data": ["App interactions", "Device or other IDs"]},
    {"p": "com.google.firebase.crashlytics", "name": "Firebase Crashlytics", "kind": "crash", "data": ["Crash logs", "Diagnostics"]},
    {"p": "com.crashlytics", "name": "Crashlytics", "kind": "crash", "data": ["Crash logs", "Diagnostics"]},
    {"p": "com.google.firebase.messaging", "name": "Firebase Cloud Messaging", "kind": "push", "data": ["Device or other IDs"]},
    {"p": "com.google.android.gms.ads", "name": "Google AdMob", "kind": "ads", "data": ["Device or other IDs", "App interactions", "Approximate location"]},
    {"p": "com.facebook.appevents", "name": "Facebook Analytics (App Events)", "kind": "analytics", "data": ["App interactions", "Device or other IDs"]},
    {"p": "com.facebook.ads", "name": "Facebook Audience Network", "kind": "ads", "data": ["Device or other IDs", "App interactions"]},
    {"p": "com.appsflyer", "name": "AppsFlyer", "kind": "attribution", "data": ["Device or other IDs", "App interactions"]},
    {"p": "com.adjust.sdk", "name": "Adjust", "kind": "attribution", "data": ["Device or other IDs", "App interactions"]},
    {"p": "io.branch", "name": "Branch", "kind": "attribution", "data": ["Device or other IDs", "App interactions"]},
    {"p": "com.clevertap", "name": "CleverTap", "kind": "engagement", "data": ["App interactions", "Device or other IDs", "Personal info"]},
    {"p": "com.moengage", "name": "MoEngage", "kind": "engagement", "data": ["App interactions", "Device or other IDs", "Personal info"]},
    {"p": "com.webengage", "name": "WebEngage", "kind": "engagement", "data": ["App interactions", "Device or other IDs"]},
    {"p": "in.netcore", "name": "Netcore Smartech", "kind": "engagement", "data": ["App interactions", "Device or other IDs"]},
    {"p": "com.onesignal", "name": "OneSignal", "kind": "push", "data": ["Device or other IDs", "App interactions"]},
    {"p": "com.mixpanel", "name": "Mixpanel", "kind": "analytics", "data": ["App interactions", "Device or other IDs"]},
    {"p": "com.amplitude", "name": "Amplitude", "kind": "analytics", "data": ["App interactions", "Device or other IDs"]},
    {"p": "com.segment.analytics", "name": "Segment", "kind": "analytics", "data": ["App interactions", "Device or other IDs"]},
    {"p": "com.flurry", "name": "Flurry", "kind": "analytics", "data": ["App interactions", "Device or other IDs"]},
    {"p": "com.applovin", "name": "AppLovin", "kind": "ads", "data": ["Device or other IDs", "App interactions"]},
    {"p": "com.unity3d.ads", "name": "Unity Ads", "kind": "ads", "data": ["Device or other IDs", "App interactions"]},
    {"p": "com.ironsource", "name": "ironSource", "kind": "ads", "data": ["Device or other IDs", "App interactions"]},
    {"p": "com.inmobi", "name": "InMobi", "kind": "ads", "data": ["Device or other IDs", "Approximate location"]},
    {"p": "com.startapp", "name": "Start.io", "kind": "ads", "data": ["Device or other IDs", "Approximate location"]},
    {"p": "com.vungle", "name": "Vungle / Liftoff", "kind": "ads", "data": ["Device or other IDs"]},
    {"p": "com.chartboost", "name": "Chartboost", "kind": "ads", "data": ["Device or other IDs"]},
    {"p": "io.sentry", "name": "Sentry", "kind": "crash", "data": ["Crash logs", "Diagnostics"]},
    {"p": "com.bugsnag", "name": "Bugsnag", "kind": "crash", "data": ["Crash logs", "Diagnostics"]},
    {"p": "com.newrelic", "name": "New Relic", "kind": "crash", "data": ["Diagnostics"]},
    {"p": "com.microsoft.appcenter", "name": "App Center", "kind": "crash", "data": ["Crash logs", "Diagnostics"]},
    {"p": "com.uxcam", "name": "UXCam (screen recording)", "kind": "analytics", "data": ["App interactions", "Screen recordings"]},
    {"p": "com.smartlook", "name": "Smartlook (screen recording)", "kind": "analytics", "data": ["App interactions", "Screen recordings"]},
    {"p": "com.yandex.metrica", "name": "Yandex AppMetrica", "kind": "analytics", "data": ["App interactions", "Device or other IDs"]},
    {"p": "com.huawei.hms.analytics", "name": "Huawei Analytics", "kind": "analytics", "data": ["App interactions", "Device or other IDs"]},
    # payments (India first)
    {"p": "com.razorpay", "name": "Razorpay", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "com.phonepe.intent.sdk", "name": "PhonePe PG", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "com.paytm.pgsdk", "name": "Paytm PG", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "net.one97.paytm.nativesdk", "name": "Paytm All-in-One SDK", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "com.cashfree.pg", "name": "Cashfree", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "com.payu", "name": "PayU", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "in.juspay", "name": "Juspay HyperSDK", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "com.stripe.android", "name": "Stripe", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "com.billdesk", "name": "BillDesk", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "com.easebuzz", "name": "Easebuzz", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "com.instamojo", "name": "Instamojo", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "com.google.android.gms.wallet", "name": "Google Pay API", "kind": "payment", "data": ["Purchase history", "Financial info"]},
    {"p": "com.android.billingclient", "name": "Google Play Billing", "kind": "billing", "data": ["Purchase history"]},
    # AI
    {"p": "com.google.ai.client.generativeai", "name": "Google AI (Gemini) SDK", "kind": "ai", "data": ["User content sent to AI"]},
    {"p": "com.google.firebase.ai", "name": "Firebase AI Logic", "kind": "ai", "data": ["User content sent to AI"]},
    {"p": "com.google.firebase.vertexai", "name": "Vertex AI in Firebase", "kind": "ai", "data": ["User content sent to AI"]},
    {"p": "com.aallam.openai", "name": "OpenAI (openai-kotlin)", "kind": "ai", "data": ["User content sent to AI"]},
    {"p": "com.openai", "name": "OpenAI SDK", "kind": "ai", "data": ["User content sent to AI"]},
    {"p": "com.anthropic", "name": "Anthropic SDK", "kind": "ai", "data": ["User content sent to AI"]},
    {"p": "dev.langchain4j", "name": "LangChain4j", "kind": "ai", "data": ["User content sent to AI"]},
    # sign-in
    {"p": "com.google.firebase.auth", "name": "Firebase Auth", "kind": "auth", "data": ["Email / account", "Phone number"]},
    {"p": "com.google.android.gms.auth", "name": "Google Sign-In", "kind": "auth", "data": ["Email / account", "Name"]},
    {"p": "com.facebook.login", "name": "Facebook Login", "kind": "auth", "data": ["Email / account", "Name"]},
    {"p": "com.truecaller.android.sdk", "name": "Truecaller SDK", "kind": "auth", "data": ["Phone number", "Name"]},
]
# dependency names in pubspec.yaml / package.json / Gradle -> SDK name (for source / repo reviews)
DEPS = {
    "firebase_analytics": "Google Firebase Analytics", "@react-native-firebase/analytics": "Google Firebase Analytics",
    "firebase-analytics": "Google Firebase Analytics", "firebase_crashlytics": "Firebase Crashlytics",
    "@react-native-firebase/crashlytics": "Firebase Crashlytics", "firebase-crashlytics": "Firebase Crashlytics",
    "firebase_messaging": "Firebase Cloud Messaging", "firebase-messaging": "Firebase Cloud Messaging",
    "google_mobile_ads": "Google AdMob", "react-native-google-mobile-ads": "Google AdMob", "play-services-ads": "Google AdMob",
    "facebook_app_events": "Facebook Analytics (App Events)", "react-native-fbsdk-next": "Facebook Analytics (App Events)",
    "facebook-android-sdk": "Facebook Analytics (App Events)", "appsflyer_sdk": "AppsFlyer", "react-native-appsflyer": "AppsFlyer",
    "af-android-sdk": "AppsFlyer", "adjust_sdk": "Adjust", "react-native-adjust": "Adjust", "flutter_branch_sdk": "Branch",
    "react-native-branch": "Branch", "clevertap_plugin": "CleverTap", "clevertap-react-native": "CleverTap",
    "clevertap-android-sdk": "CleverTap", "moengage_flutter": "MoEngage", "react-native-moengage": "MoEngage",
    "onesignal_flutter": "OneSignal", "react-native-onesignal": "OneSignal", "mixpanel_flutter": "Mixpanel",
    "mixpanel-react-native": "Mixpanel", "amplitude_flutter": "Amplitude", "@amplitude/analytics-react-native": "Amplitude",
    "sentry_flutter": "Sentry", "@sentry/react-native": "Sentry", "sentry-android": "Sentry", "applovin_max": "AppLovin",
    "unity_ads_plugin": "Unity Ads", "razorpay_flutter": "Razorpay", "react-native-razorpay": "Razorpay", "checkout": "Razorpay",
    "phonepe_payment_sdk": "PhonePe PG", "react-native-phonepe-pg": "PhonePe PG", "paytm_allinonesdk": "Paytm All-in-One SDK",
    "flutter_cashfree_pg_sdk": "Cashfree", "react-native-cashfree-pg-sdk": "Cashfree", "payu_checkoutpro_flutter": "PayU",
    "flutter_stripe": "Stripe", "@stripe/stripe-react-native": "Stripe", "stripe-android": "Stripe",
    "in_app_purchase": "Google Play Billing", "react-native-iap": "Google Play Billing", "billing": "Google Play Billing",
    "google_generative_ai": "Google AI (Gemini) SDK", "firebase_ai": "Firebase AI Logic", "firebase_vertexai": "Vertex AI in Firebase",
    "dart_openai": "OpenAI SDK", "openai": "OpenAI SDK", "@anthropic-ai/sdk": "Anthropic SDK", "anthropic_sdk_dart": "Anthropic SDK",
    "firebase_auth": "Firebase Auth", "@react-native-firebase/auth": "Firebase Auth", "firebase-auth": "Firebase Auth",
    "google_sign_in": "Google Sign-In", "@react-native-google-signin/google-signin": "Google Sign-In",
    "play-services-auth": "Google Sign-In", "flutter_facebook_auth": "Facebook Login", "truecaller_sdk": "Truecaller SDK",
}
SDK_BY_NAME = {s["name"]: s for s in SDKS}
FAMILIES_CERTIFIED_HINT = {"Google AdMob"}       # AdMob can be configured for families (tag for child-directed treatment)


def sdk_for_class(prefix: str) -> dict[str, Any] | None:
    for s in SDKS:
        if prefix == s["p"] or prefix.startswith(s["p"] + "."):
            return s
    return None


# ---------------------------------------------------------------- secrets
SECRET_PATTERNS: list[tuple[str, re.Pattern, str, str]] = [   # (id, regex, severity, label)
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"), "critical", "private key"),
    ("aws", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "critical", "AWS access key"),
    ("stripe_live", re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{20,}\b"), "critical", "Stripe secret key"),
    ("github", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b"), "critical", "GitHub token"),
    ("slack", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "high", "Slack token"),
    ("anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"), "critical", "Anthropic API key"),
    ("openai", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"), "critical", "OpenAI API key"),
    ("sendgrid", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,32}\.[A-Za-z0-9_-]{20,64}\b"), "critical", "SendGrid key"),
    ("fcm_server", re.compile(r"\bAAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{100,}\b"), "critical", "FCM legacy server key"),
    ("twilio_key", re.compile(r"\bSK[0-9a-f]{32}\b"), "high", "Twilio API key"),
    ("mapbox_secret", re.compile(r"\bsk\.eyJ[A-Za-z0-9_.-]{20,}\b"), "high", "Mapbox secret token"),
    ("razorpay_secret", re.compile(r"(?i)\b(?:razorpay|rzp)[_ -]?(?:key[_ -]?)?secret\b\s*[:=]\s*[\"']?([A-Za-z0-9]{20,32})"),
     "critical", "Razorpay key secret"),
    ("generic", re.compile(r"(?i)\b(?:client_secret|secret_key|api_secret|private_key|db_password|password|passwd)\b\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']"),
     "high", "password / secret in code"),
    # public / client keys (fine in an app, but must be restricted)
    ("google_api", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "low", "Google API key"),
    ("razorpay_id", re.compile(r"\brzp_live_[A-Za-z0-9]{14}\b"), "low", "Razorpay Key ID (public)"),
    ("stripe_pk", re.compile(r"\bpk_live_[0-9A-Za-z]{20,}\b"), "low", "Stripe publishable key"),
]
_PLACEHOLDER = re.compile(r"(?i)^(?:x+|\*+|your[_-]?|changeme|example|dummy|test|sample|<.*>|\$\{.*\}|process\.env|os\.environ)")


def mask(v: str) -> str:
    v = v.strip()
    return v[:4] + "…" + v[-4:] if len(v) > 12 else v[:2] + "…"


def find_secrets(text: str) -> list[tuple[str, str, str, str]]:
    """-> [(pattern id, severity, label, masked value)] (one per distinct value)."""
    out, seen = [], set()
    for pid, rx, sev, label in SECRET_PATTERNS:
        for m in rx.finditer(text):
            val = m.group(1) if m.groups() else m.group(0)
            if not val or _PLACEHOLDER.match(val) or val in seen:
                continue
            if pid == "generic" and (len(set(val)) < 5 or val.lower() in ("password", "required", "optional")):
                continue
            seen.add(val)
            out.append((pid, sev, label, mask(val)))
    return out


# ---------------------------------------------------------------- source code patterns (file:line evidence)
CODE_PATTERNS: list[tuple[str, re.Pattern, str]] = [   # (rule code, regex, what it is)
    ("weak_tls", re.compile(r"checkServerTrusted\s*\([^)]*\)\s*(?::\s*Unit\s*)?\{\s*\}"), "empty checkServerTrusted"),
    ("weak_tls", re.compile(r"ALLOW_ALL_HOSTNAME_VERIFIER|HostnameVerifier\s*\{\s*_?\s*,\s*_?\s*->\s*true|verify\s*\([^)]*\)\s*(?::\s*Boolean)?\s*(?:=\s*true|\{\s*return\s+true)"),
     "verifier that accepts every hostname"),
    ("weak_tls", re.compile(r"badCertificateCallback\s*=\s*\([^)]*\)\s*(?:=>\s*true|\{\s*return\s+true)"), "Dart badCertificateCallback true"),
    ("weak_tls", re.compile(r"rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0"), "Node TLS check turned off"),
    ("webview_js_bridge", re.compile(r"addJavascriptInterface\s*\("), "addJavascriptInterface"),
    ("webview_js_bridge", re.compile(r"setAllowUniversalAccessFromFileURLs\s*\(\s*true|allowUniversalAccessFromFileURLs\s*=\s*true"),
     "access everywhere from a file URL"),
    ("weak_crypto", re.compile(r"Cipher\.getInstance\(\s*\"(?:AES|DES|DESede|AES/ECB[^\"]*)\"\s*\)|MessageDigest\.getInstance\(\s*\"(?:MD5|SHA-?1)\"\)"),
     "AES/ECB, DES, MD5 or SHA-1"),
    ("weak_crypto", re.compile(r"\bmd5\s*\(|createHash\(\s*['\"](?:md5|sha1)['\"]"), "MD5 / SHA-1 hash"),
    ("insecure_random", re.compile(r"(?i)(?:otp|token|password|secret|nonce)\w*\s*=.*(?:java\.util\.Random\(|\bRandom\(\)\.next|Math\.random\(\))"),
     "Random used for an OTP / token"),
    ("plain_storage", re.compile(r"(?i)(?:putString|setString|localStorage\.setItem|AsyncStorage\.setItem)\s*\(\s*['\"][^'\"]*(?:token|password|pin|secret)[^'\"]*['\"]"),
     "token / password in open storage"),
    ("log_secret", re.compile(r"(?i)(?:Log\.[dviwe]|print|debugPrint|console\.log)\s*\(.*\b(?:password|otp|token|pin|cvv)\b"),
     "password / OTP / token in the log"),
    ("sql_concat", re.compile(r"(?:rawQuery|execSQL|rawInsert|query)\s*\(\s*[\"'`][^\"'`]*(?:WHERE|where)[^\"'`]*[\"'`]\s*\+"),
     "user text joined into SQL with +"),
    ("eval_js", re.compile(r"\beval\s*\(|dangerouslySetInnerHTML|\.innerHTML\s*="), "eval / innerHTML"),
    ("rbi_card_fields", re.compile(r"(?i)['\"](?:card_?number|cardNumber|cvv|card_cvv)['\"]\s*[:,=]"), "card number / CVV field"),
]
HTTP_URL = re.compile(r"[\"'](http://(?!localhost|127\.0\.0\.1|10\.0\.2\.2|schemas\.android\.com|www\.w3\.org|ns\.adobe\.com|xmlpull\.org|"
                      r"apache\.org|json-schema\.org|example\.com)[A-Za-z0-9.-]+[^\"'\s]*)[\"']")
SKIP_DIRS = {"node_modules", ".git", "build", ".gradle", ".dart_tool", "Pods", ".idea", "dist", ".next", "vendor", "__pycache__",
             "intermediates", "generated", ".cxx", "third_party"}
TEXT_EXT = {".kt", ".java", ".dart", ".js", ".jsx", ".ts", ".tsx", ".swift", ".m", ".xml", ".gradle", ".kts", ".json", ".yaml",
            ".yml", ".properties", ".env", ".plist", ".py", ".php", ".rb", ".go", ".html", ".txt", ".toml", ".cfg", ".ini", ".sh"}
COMMITTED_SECRETS = {".env": "'.env'", ".env.production": "'.env.production'", "key.properties": "'key.properties' (signing passwords)",
                     "keystore.properties": "'keystore.properties'"}
COMMITTED_EXT = {".jks": "signing keystore (.jks)", ".keystore": "signing keystore", ".p12": "certificate + private key (.p12)",
                 ".pem": "PEM key file"}
LOGIN_WORDS = re.compile(r"(?i)\b(?:sign[ _-]?up|sign[ _-]?in|log[ _-]?in|create account|register|otp verification|forgot password)\b")


def rule(code: str) -> dict[str, Any]:
    return RULES[code]


def stack_snippet(code: str, stack: str) -> dict[str, str] | None:
    sn = RULES[code].get("snippet") or {}
    for k in (stack, "android", "web"):
        if sn.get(k):
            return {"lang": {"android": "kotlin", "flutter": "dart", "react_native": "javascript", "web": "text"}.get(k, "text"),
                    "for": k, "code": sn[k]}
    return None


def score(risks: list[dict[str, Any]]) -> int:
    return max(0, 100 - sum(SEV_WEIGHT.get(r["sev"], 0) for r in risks if r.get("status") != "ignored"))
