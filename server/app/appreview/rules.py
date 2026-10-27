"""What the App Review Sahayak checks, why it matters (plain Hinglish), and how to fix it. Pure data + small helpers.

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
SEV_LABEL = {"critical": "Bahut gambhir", "high": "Gambhir", "medium": "Dhyaan dein", "low": "Chhota", "info": "Jaankari"}
SEV_WEIGHT = {"critical": 25, "high": 12, "medium": 5, "low": 2, "info": 0}
AREAS = {"security": "Suraksha (code / data)", "privacy": "Privacy", "play": "Google Play policy", "apple": "Apple App Store",
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
        title="App debug mode mein bani hai", area="security", sev="high", masvs="MASVS-RESILIENCE-4",
        explain="android:debuggable=true ho to koi bhi USB se app ke andar jhaank sakta hai, data padh sakta hai. Play Store aisa "
                "build lega bhi nahi.",
        fix="Release build banaiye (debuggable hata dijiye; Gradle release buildType khud false rakhta hai).",
        snippet=_sn(android="buildTypes {\n    release {\n        isDebuggable = false\n        isMinifyEnabled = true\n    }\n}",
                    flutter="flutter build appbundle --release"), refs=["masvs"]),
    "test_only": dict(
        title="Sirf test ke liye bana build (testOnly)", area="play", sev="high", masvs="MASVS-CODE-1",
        explain="android:testOnly=true wala APK Play par upload hi nahi hota aur aam phone par install nahi hota.",
        fix="Android Studio ke 'Run' wale APK ki jagah release AAB banaiye.", snippet={}, refs=["masvs"]),
    "allow_backup": dict(
        title="Phone backup mein app ka data chala jata hai", area="security", sev="medium", masvs="MASVS-STORAGE-2",
        explain="allowBackup chalu hai (ya likha hi nahi, to default chalu). Login token / customer data Google backup ya 'adb backup' "
                "se doosre phone par pahunch sakta hai.",
        fix="allowBackup=false kijiye, ya dataExtractionRules / fullBackupContent se sirf zaroori files backup mein rakhiye.",
        snippet=_sn(android='<application\n    android:allowBackup="false"\n    android:dataExtractionRules="@xml/data_extraction_rules"\n    ...>'),
        refs=["masvs"]),
    "cleartext": dict(
        title="Bina HTTPS (http://) traffic chalu hai", area="security", sev="high", masvs="MASVS-NETWORK-1",
        explain="App plain http par baat kar sakti hai. Wi-Fi / network wala login, OTP, payment details beech mein padh ya badal "
                "sakta hai.",
        fix="usesCleartextTraffic=false rakhiye aur har API URL https kijiye. Kisi purane server ke liye network security config mein "
            "sirf us ek domain ki chhoot dijiye.",
        snippet=_sn(android='<!-- AndroidManifest.xml -->\n<application android:usesCleartextTraffic="false"\n    '
                            'android:networkSecurityConfig="@xml/network_security_config" ...>',
                    flutter="// sab URLs https:// rakhiye\nfinal uri = Uri.https('api.example.in', '/v1/orders');"),
        refs=["masvs"]),
    "nsc_cleartext": dict(
        title="Network security config sab jagah http ki chhoot deta hai", area="security", sev="high", masvs="MASVS-NETWORK-1",
        explain="network_security_config mein base-config / domain par cleartextTrafficPermitted=\"true\" hai: {detail}.",
        fix="cleartextTrafficPermitted false kijiye; zaroorat ho to sirf ek purane domain ke liye <domain-config> mein.",
        snippet=_sn(android='<network-security-config>\n  <base-config cleartextTrafficPermitted="false">\n    <trust-anchors>'
                            '<certificates src="system"/></trust-anchors>\n  </base-config>\n</network-security-config>'),
        refs=["masvs"]),
    "nsc_user_certs": dict(
        title="App user ke daale hue certificates par bharosa karti hai", area="security", sev="high", masvs="MASVS-NETWORK-1",
        explain="trust-anchors mein <certificates src=\"user\"/> release build mein hai. Koi bhi phone mein apna certificate daal kar "
                "app ka encrypted traffic padh sakta hai.",
        fix="user certificates ko sirf <debug-overrides> ke andar rakhiye.",
        snippet=_sn(android='<debug-overrides>\n  <trust-anchors><certificates src="user"/></trust-anchors>\n</debug-overrides>'),
        refs=["masvs"]),
    "exported_component": dict(
        title="Doosre apps aapki screen / service ko seedhe chala sakte hain", area="security", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="{detail} exported hai aur koi permission nahi maangta. Phone ka koi bhi app ise khol / bhej sakta hai; andar login ke "
                "bina wala data ya action ho to khatra hai.",
        fix="Jo bahar se nahi khulna chahiye usme android:exported=\"false\" likhiye; zaroori ho to signature-level permission lagaiye.",
        snippet=_sn(android='<activity android:name=".OrderDetailActivity" android:exported="false" />\n'
                            '<!-- ya -->\n<service android:name=".SyncService" android:exported="true"\n'
                            '    android:permission="com.example.permission.SYNC" />'),
        refs=["masvs"]),
    "exported_provider": dict(
        title="Content provider sabke liye khula hai", area="security", sev="high", masvs="MASVS-PLATFORM-1",
        explain="{detail} exported provider hai bina read/write permission ke. Doosre apps aapki app ka database / files padh sakte hain.",
        fix="exported=false rakhiye, ya readPermission / writePermission (signature) lagaiye; files share karni ho to FileProvider.",
        snippet=_sn(android='<provider android:name="androidx.core.content.FileProvider"\n    android:authorities="${applicationId}.files"\n'
                            '    android:exported="false" android:grantUriPermissions="true" />'), refs=["masvs"]),
    "missing_exported": dict(
        title="android:exported likha nahi hai (Android 12+)", area="play", sev="high", masvs="MASVS-PLATFORM-1",
        explain="{detail} mein intent-filter hai par android:exported nahi likha. Android 12 / targetSdk 31+ par aisi app install nahi "
                "hoti aur build fail hota hai.",
        fix="Har intent-filter wali activity / service / receiver par android:exported=\"true\" ya \"false\" saaf likhiye.", snippet={},
        refs=["masvs"]),
    "target_sdk": dict(
        title="Target API purana hai: Play update nahi lega", area="play", sev="critical", masvs="MASVS-CODE-1",
        explain="targetSdk {detail}. 31 Aug 2026 se Play par naye apps aur har update ko Android 16 (API 36) target karna zaroori hai; "
                "35 se neeche wale purane apps naye Android phones par naye logon ko dikhne band ho jaate hain (extension 1 Nov 2026 tak "
                "maangi ja sakti thi).",
        fix="compileSdk + targetSdk 36 kijiye, Android 16 ke behaviour changes (edge-to-edge, predictive back, foreground service "
            "types) test kijiye.",
        snippet=_sn(android="android {\n    compileSdk = 36\n    defaultConfig {\n        targetSdk = 36\n    }\n}",
                    flutter="// android/app/build.gradle(.kts)\ndefaultConfig {\n    targetSdk = 36\n}"),
        refs=["play_target"]),
    "target_sdk_soon": dict(
        title="Target API 36 se neeche: agle update se pehle badhaiye", area="play", sev="medium", masvs="MASVS-CODE-1",
        explain="targetSdk {detail}. Abhi listing chalti rahegi, par agla update tabhi jayega jab 36 target ho.",
        fix="Agle release mein targetSdk 36 kijiye.", snippet=_sn(android="defaultConfig { targetSdk = 36 }"), refs=["play_target"]),
    "min_sdk_old": dict(
        title="Bahut purane Android tak support", area="security", sev="low", masvs="MASVS-CODE-1",
        explain="minSdk {detail}: itne purane Android par security updates nahi aate aur kai suraksha features (scoped storage, TLS 1.3) "
                "nahi hote.",
        fix="minSdk kam se kam 24 (Android 7) rakhne par vichaar kijiye; payment / login wale apps ke liye 26+.", snippet={}, refs=["masvs"]),
    "unsigned": dict(
        title="APK par signature nahi", area="play", sev="critical", masvs="MASVS-CODE-1",
        explain="Bina signature ke APK install hi nahi hota aur Play upload nahi hota.",
        fix="Release keystore se sign kijiye (Play App Signing chalu rakhiye).", snippet={}, refs=["masvs"]),
    "debug_cert": dict(
        title="Android Debug key se sign hai", area="play", sev="high", masvs="MASVS-CODE-1",
        explain="Debug key har developer ke computer par same hoti hai; aisa APK release nahi hai aur Play nahi leta.",
        fix="Apni release key (ya Play App Signing ki upload key) se sign kijiye.",
        snippet=_sn(android="signingConfigs {\n    create(\"release\") { storeFile = file(System.getenv(\"KEYSTORE\")) ... }\n}"),
        refs=["masvs"]),
    "v1_only": dict(
        title="Sirf purana v1 signature", area="security", sev="medium", masvs="MASVS-CODE-1",
        explain="Sirf JAR (v1) signature hai. targetSdk 30+ par v2 zaroori hai; v1 mein file ke kuch hisse bina pakde badle ja sakte hain.",
        fix="apksigner / Gradle se v2 + v3 signature chalu kijiye (Gradle default).", snippet={}, refs=["masvs"]),
    "no_arm64": dict(
        title="64-bit (arm64) native library nahi", area="play", sev="high", masvs="MASVS-CODE-1",
        explain="Native code hai par arm64-v8a version nahi: {detail}. Play 64-bit maangta hai.",
        fix="abiFilters mein arm64-v8a jodiye / library ka 64-bit build daaliye.", snippet={}, refs=["play_16kb"]),
    "page_16kb": dict(
        title="Native library 16 KB page size ke liye taiyaar nahi", area="play", sev="high", masvs="MASVS-CODE-1",
        explain="{detail} ka LOAD alignment 16 KB se kam hai. 1 Nov 2025 se Android 15+ target karne wale naye apps / updates ko 16 KB "
                "page size support karna zaroori hai; aise phones par app crash ho sakti hai.",
        fix="NDK r28+ / AGP 8.5.1+ se dobara build kijiye (ya -Wl,-z,max-page-size=16384); third-party .so ka naya version lijiye.",
        snippet=_sn(android="# CMake / ndk-build\ntarget_link_options(mylib PRIVATE \"-Wl,-z,max-page-size=16384\")",
                    flutter="# Flutter 3.32+ / AGP 8.5.1+ par dobara build kijiye"), refs=["play_16kb"]),
    "zip_align_16kb": dict(
        title="APK mein .so 16 KB par aligned nahi", area="play", sev="medium", masvs="MASVS-CODE-1",
        explain="{detail} bina compress ke rakhi hai par 16 KB boundary par nahi. 16 KB phones par yeh library load nahi hogi.",
        fix="AGP 8.5.1+ se build kijiye (zipalign -P 16) ya useLegacyPackaging.", snippet={}, refs=["play_16kb"]),
    # ---- permissions / Play restricted
    "perm_sms": dict(
        title="SMS permission: Play mein sirf default SMS app ko milti hai", area="play", sev="critical", masvs="MASVS-PLATFORM-1",
        explain="{detail} maanga hai. Play SMS / Call log permissions sirf default SMS / phone app ke kaam ke liye deta hai; OTP padhne "
                "ke liye nahi. App reject / remove ho sakti hai.",
        fix="OTP ke liye SMS Retriever API ya SMS User Consent API lagaiye (koi permission nahi chahiye).",
        snippet=_sn(android="SmsRetriever.getClient(context).startSmsRetriever()\n// SMS mein app ka 11-character hash hona chahiye",
                    flutter="// package: smart_auth / sms_autofill (SMS Retriever par chalte hain, READ_SMS nahi)"),
        refs=["play_perms"]),
    "perm_call_log": dict(
        title="Call log permission", area="play", sev="critical", masvs="MASVS-PLATFORM-1",
        explain="{detail} maanga hai. Play sirf default dialer ke liye deta hai; July 2026 se 'call karke account verify' bhi isme mana hai.",
        fix="Number verify ke liye SMS Retriever / Digital Credentials API; call log ki zaroorat hatayiye.", snippet={},
        refs=["play_perms", "play_jul26"]),
    "perm_all_files": dict(
        title="Saari files ki permission (MANAGE_EXTERNAL_STORAGE)", area="play", sev="high", masvs="MASVS-STORAGE-1",
        explain="'All files access' sirf file manager / backup / antivirus jaise apps ko milta hai. Photo / PDF chun-ne ke liye nahi.",
        fix="Photo Picker / Storage Access Framework (ACTION_OPEN_DOCUMENT) lagaiye.",
        snippet=_sn(android="val pick = registerForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri -> }\n"
                            "pick.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))",
                    flutter="// image_picker / file_picker: Photo Picker + SAF use karte hain, permission nahi"),
        refs=["play_perms"]),
    "perm_query_all": dict(
        title="Phone ke saare apps ki list (QUERY_ALL_PACKAGES)", area="play", sev="high", masvs="MASVS-PRIVACY-1",
        explain="Play ise sirf antivirus / launcher / device-search jaise apps ko deta hai, declaration form ke saath.",
        fix="Manifest mein <queries> ke andar sirf woh packages / intents likhiye jinki zaroorat hai (jaise UPI apps).",
        snippet=_sn(android='<queries>\n  <intent><action android:name="android.intent.action.VIEW"/>\n'
                            '    <data android:scheme="upi"/></intent>\n</queries>'), refs=["play_perms"]),
    "perm_bg_location": dict(
        title="App band hone par bhi location (background location)", area="play", sev="high", masvs="MASVS-PRIVACY-1",
        explain="Background location ke liye Play declaration + video aur app ke andar saaf 'prominent disclosure' maangta hai; core "
                "kaam na ho to reject.",
        fix="Ho sake to sirf app khuli ho tab location (foreground) lijiye; delivery tracking jaisa kaam ho to foreground service "
            "type location + disclosure screen.", snippet={}, refs=["play_perms", "play_datasafety"]),
    "perm_install": dict(
        title="Doosre apps install karwane ki permission", area="play", sev="high", masvs="MASVS-PLATFORM-1",
        explain="REQUEST_INSTALL_PACKAGES sirf app stores / file managers / device management jaise core kaam ke liye milti hai.",
        fix="Apni app ka update Play In-App Updates API se kijiye.", snippet={}, refs=["play_perms"]),
    "perm_exact_alarm": dict(
        title="Exact alarm permission", area="play", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="{detail}: USE_EXACT_ALARM sirf alarm clock / calendar apps ko; SCHEDULE_EXACT_ALARM Android 14 par default band hai.",
        fix="Reminder ke liye WorkManager / inexact AlarmManager.setWindow; sach mein alarm app ho to hi exact alarm.", snippet={},
        refs=["play_perms"]),
    "perm_fullscreen": dict(
        title="Full-screen intent (lock screen par poori screen)", area="play", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="Android 14 se USE_FULL_SCREEN_INTENT sirf calling / alarm apps ko default milta hai; baaki ko Play declaration.",
        fix="Normal high-priority notification use kijiye.", snippet={}, refs=["play_perms"]),
    "perm_media": dict(
        title="Photos / videos padhne ki permission", area="play", sev="medium", masvs="MASVS-PRIVACY-1",
        explain="Play ki Photo & Video Permissions policy: READ_MEDIA_IMAGES / VIDEO sirf un apps ko jinka core kaam hi gallery hai; "
                "ek-do photo chun-ne ke liye Photo Picker.",
        fix="Android Photo Picker lagaiye aur permission hata dijiye.",
        snippet=_sn(android="ActivityResultContracts.PickVisualMedia()", flutter="ImagePicker().pickImage(source: ImageSource.gallery)"),
        refs=["play_perms"]),
    "perm_accessibility": dict(
        title="Accessibility service", area="play", sev="critical", masvs="MASVS-PLATFORM-1",
        explain="Accessibility service screen padh kar tap kar sakti hai. Play ise sirf disability-support (ya declared core) kaam ke "
                "liye deta hai; assistant / automation ke liye mana hai.",
        fix="Accessibility service hatayiye; kaam Android ke public APIs se kijiye.", snippet={}, refs=["play_perms"]),
    "perm_vpn": dict(
        title="VPN service", area="play", sev="medium", masvs="MASVS-NETWORK-1",
        explain="VpnService wali apps ko Play declaration chahiye aur traffic ka data ads ke liye use nahi kar sakte.",
        fix="Play Console mein VpnService declaration bhariye.", snippet={}, refs=["play_perms"]),
    "perm_device_admin": dict(
        title="Device admin", area="play", sev="high", masvs="MASVS-PLATFORM-1",
        explain="Device admin phone lock / wipe kar sakta hai aur uninstall rok sakta hai; Play ise bahut seemit kaam ke liye deta hai.",
        fix="Ho sake to hatayiye; enterprise ke liye Android Enterprise APIs.", snippet={}, refs=["play_perms"]),
    "perm_battery": dict(
        title="Battery optimisation se chhoot maangna", area="play", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="REQUEST_IGNORE_BATTERY_OPTIMIZATIONS Play mein sirf us app ko jiska core kaam bina iske tootta ho.",
        fix="FCM high-priority message / WorkManager se kaam chalayiye.", snippet={}, refs=["play_perms"]),
    "perm_overlay": dict(
        title="Doosre apps ke upar screen (SYSTEM_ALERT_WINDOW)", area="security", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="Overlay se nakli screen dikhayi ja sakti hai; users ko dar lagta hai aur Play review dhyaan se dekhta hai.",
        fix="Notification / bubble API use kijiye.", snippet={}, refs=["play_perms"]),
    "perm_sensitive": dict(
        title="Personal data wali permission", area="privacy", sev="info", masvs="MASVS-PRIVACY-1",
        explain="{detail}: Data safety form mein yeh data likhna hoga, permission maangne se pehle user ko kyon chahiye bataiye.",
        fix="Permission tabhi maangiye jab woh feature khule; Data safety form mein sahi jaankari.", snippet={}, refs=["play_datasafety"]),
    "fgs_types": dict(
        title="Foreground service ka type / declaration", area="play", sev="medium", masvs="MASVS-PLATFORM-1",
        explain="{detail}. Android 14 (target 34+) par har foreground service ka type likhna aur Play Console mein declare karna hota hai.",
        fix="<service android:foregroundServiceType=\"...\"> + FOREGROUND_SERVICE_<TYPE> permission + Play Console declaration.",
        snippet=_sn(android='<service android:name=".TrackService" android:foregroundServiceType="location" />\n'
                            '<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />'),
        refs=["play_perms"]),
    # ---- secrets / code
    "secret": dict(
        title="App ke andar secret key chhupi hai", area="security", sev="critical", masvs="MASVS-STORAGE-1",
        explain="{detail}. App ki file koi bhi khol kar yeh key nikaal sakta hai aur aapke khate / server ka galat use kar sakta hai "
                "(bill aapke naam par).",
        fix="Is key ko TURANT badaliye (rotate / revoke), phir secret ko sirf apne server par rakhiye; app server se baat kare, server "
            "provider se.",
        snippet=_sn(android="// app -> aapka server (login token ke saath) -> provider API (secret sirf server ke .env mein)\n"
                            "val res = api.post(\"https://api.aapka-server.in/pay/order\", body)",
                    flutter="// --dart-define bhi APK mein dikh jaata hai: secret kabhi app mein nahi\n"
                            "final r = await http.post(Uri.https('api.aapka-server.in', '/pay/order'), headers: {'Authorization': 'Bearer $userToken'});",
                    web="# .env (server only, git mein nahi)\nRAZORPAY_KEY_SECRET=...\n# .gitignore\n.env"),
        refs=["masvs"]),
    "public_key": dict(
        title="Public / client key app mein hai (theek, par bandish lagaiye)", area="security", sev="low", masvs="MASVS-STORAGE-1",
        explain="{detail}. Yeh key app mein hona aam hai, par Google Cloud / provider console mein package name + SHA-1 aur sirf "
                "zaroori APIs ki bandish na ho to koi bhi ise apne kaam mein laga kar aapka bill badha sakta hai.",
        fix="Console mein key restriction lagaiye (Android app: package + SHA-1; sirf zaroori APIs).", snippet={}, refs=["masvs"]),
    "weak_tls": dict(
        title="HTTPS certificate jaanch band ki gayi hai", area="security", sev="critical", masvs="MASVS-NETWORK-1",
        explain="{detail}: code har certificate maan leta hai. Beech wala koi bhi nakli server ban kar login / payment data le sakta hai.",
        fix="Yeh custom TrustManager / HostnameVerifier / badCertificateCallback hata dijiye; system ki default jaanch rehne dijiye.",
        snippet=_sn(android="// hatayiye: object : X509TrustManager { override fun checkServerTrusted(...) {} }\n"
                            "val client = OkHttpClient.Builder().build()   // default jaanch",
                    flutter="// hatayiye: client.badCertificateCallback = (cert, host, port) => true;"),
        refs=["masvs"]),
    "webview_js_bridge": dict(
        title="WebView mein JavaScript bridge", area="security", sev="medium", masvs="MASVS-PLATFORM-2",
        explain="{detail}: WebView mein koi bahar ka page khula to woh aapke app ke Java/Kotlin functions chala sakta hai.",
        fix="Sirf apne https pages kholiye (URL allow-list), addJavascriptInterface sirf zaroorat par; file access band.",
        snippet=_sn(android="webView.settings.allowFileAccess = false\nwebView.webViewClient = object : WebViewClient() {\n"
                            "  override fun shouldOverrideUrlLoading(v: WebView, r: WebResourceRequest) = r.url.host != \"app.aapka.in\"\n}"),
        refs=["masvs"]),
    "weak_crypto": dict(
        title="Kamzor encryption", area="security", sev="medium", masvs="MASVS-CRYPTO-1",
        explain="{detail}: MD5 / SHA-1 / DES / AES-ECB jaise tareeke aaj aasaani se tootte hain.",
        fix="AES-GCM (Android Keystore key) aur SHA-256 use kijiye; password ke liye server par argon2 / bcrypt.",
        snippet=_sn(android='val c = Cipher.getInstance("AES/GCM/NoPadding")   // key Android Keystore se'), refs=["masvs"]),
    "insecure_random": dict(
        title="Token / OTP ke liye kamzor random", area="security", sev="medium", masvs="MASVS-CRYPTO-1",
        explain="{detail}: java.util.Random / Math.random se bana number andaaza lagaya ja sakta hai.",
        fix="SecureRandom (Android) / Random.secure() (Dart) / crypto.getRandomValues (JS).",
        snippet=_sn(android="val bytes = ByteArray(16).also { java.security.SecureRandom().nextBytes(it) }",
                    flutter="final r = Random.secure();"), refs=["masvs"]),
    "plain_storage": dict(
        title="Token / password khule storage mein", area="security", sev="medium", masvs="MASVS-STORAGE-1",
        explain="{detail}: SharedPreferences / localStorage mein khula token root ya backup se nikal sakta hai.",
        fix="Android Keystore se encrypt karke rakhiye (EncryptedSharedPreferences / flutter_secure_storage); password kabhi mat rakhiye.",
        snippet=_sn(android="// androidx.security:security-crypto ya DataStore + Keystore AES-GCM",
                    flutter="const storage = FlutterSecureStorage();\nawait storage.write(key: 'token', value: token);"),
        refs=["masvs"]),
    "log_secret": dict(
        title="Log mein password / token likha ja raha hai", area="security", sev="medium", masvs="MASVS-STORAGE-2",
        explain="{detail}: logcat doosre tools / bug reports mein chala jata hai.",
        fix="Release build mein logs hatayiye (R8 -assumenosideeffects) aur secret kabhi log mat kijiye.", snippet={}, refs=["masvs"]),
    "sql_concat": dict(
        title="SQL mein user ka text seedha joda gaya", area="security", sev="medium", masvs="MASVS-CODE-4",
        explain="{detail}: SQL injection se doosre users ka data padha / mitaya ja sakta hai.",
        fix="Hamesha ? placeholders / bind arguments.",
        snippet=_sn(android='db.rawQuery("SELECT * FROM orders WHERE phone = ?", arrayOf(phone))',
                    web="db.query('SELECT * FROM orders WHERE phone = $1', [phone])"), refs=["masvs"]),
    "http_url": dict(
        title="Code mein http:// (bina HTTPS) address", area="security", sev="low", masvs="MASVS-NETWORK-1",
        explain="{detail}", fix="In addresses ko https:// kijiye.", snippet={}, refs=["masvs"]),
    "env_committed": dict(
        title=".env / keystore file code ke saath rakhi hai", area="security", sev="high", masvs="MASVS-STORAGE-1",
        explain="{detail} repo / ZIP mein hai. Jisko bhi code mila, usko saari keys / signing key mil gayi.",
        fix="File hatayiye, .gitignore mein daaliye, aur andar ki har key badaliye; git history se bhi hatani hogi.",
        snippet=_sn(web=".env\n*.jks\n*.keystore\nkey.properties\ngoogle-services.json   # agar public repo hai"), refs=["masvs"]),
    "eval_js": dict(
        title="JavaScript eval / innerHTML", area="security", sev="low", masvs="MASVS-CODE-4",
        explain="{detail}: bahar ka text code ban kar chal sakta hai (XSS).", fix="eval hatayiye; text ko textContent se dikhaiye.",
        snippet={}, refs=["masvs"]),
    # ---- SDKs / policy
    "trackers": dict(
        title="Tracking / analytics SDK mile", area="privacy", sev="info", masvs="MASVS-PRIVACY-1",
        explain="{detail}. Inka data (device id, usage, location...) Data safety form mein 'collected / shared' likhna hoga aur privacy "
                "policy mein naam se batana hoga.",
        fix="Har SDK ki apni 'Data safety' guide dekh kar form bhariye; jo SDK kaam ka nahi, hataiye.", snippet={},
        refs=["exodus", "play_datasafety"]),
    "ads_id": dict(
        title="Advertising ID", area="privacy", sev="low", masvs="MASVS-PRIVACY-1",
        explain="{detail}. Data safety mein 'Device or other IDs' aur ads ka maksad likhiye; bachchon ke apps mein AD_ID mana hai.",
        fix="Ads nahi dikhate to <uses-permission ... AD_ID tools:node=\"remove\"/>.",
        snippet=_sn(android='<uses-permission android:name="com.google.android.gms.permission.AD_ID" tools:node="remove"/>'),
        refs=["play_datasafety", "play_families"]),
    "ai_sdk": dict(
        title="Bahar ki AI service ko user ka data jaata hai", area="play", sev="medium", masvs="MASVS-PRIVACY-1",
        explain="{detail}. Play July 2026 update: third-party AI integration par bhi User Data policy lagti hai: privacy policy + Data "
                "safety mein batana, data bhejne se pehle user ki manzoori, aur sirf bataye maksad ke liye use.",
        fix="AI ko bhejne se pehle ek saaf consent screen; privacy policy mein provider ka naam; key app mein nahi, server par.",
        snippet={}, refs=["play_jul26"]),
    "account_deletion": dict(
        title="Account delete karne ka raasta (Play + App Store)", area="play", sev="medium", masvs="MASVS-PRIVACY-4",
        explain="App mein login / sign-up dikhta hai ({detail}). Play: app ke andar aur ek web link se account + data delete karne ki "
                "suvidha zaroori; Apple 5.1.1(v) bhi app ke andar delete maangta hai.",
        fix="Settings > 'Account delete karein' screen + website par delete request page; link Play Console Data safety mein daaliye.",
        snippet={}, refs=["play_delete", "apple"]),
    "families": dict(
        title="Bachchon ke liye app: Families policy", area="play", sev="high", masvs="MASVS-PRIVACY-1",
        explain="Aapne bataya app bachchon ke liye hai. {detail}. Families policy mein sirf Families-certified ads SDK, AD_ID / location "
                "jaisi cheezein mana, aur bachchon ka data ads ke liye nahi.",
        fix="Non-certified SDK hatayiye, AD_ID remove, Teacher Approved / target audience form sahi bhariye.", snippet={},
        refs=["play_families"]),
    "data_safety": dict(
        title="Data safety form: kya bharna hai", area="play", sev="info", masvs="MASVS-PRIVACY-1",
        explain="App mein mila: {detail}. Form mein jo bharein woh app ke asli kaam se mel khana chahiye, warna Play update rokta hai.",
        fix="Is report ki 'Data safety draft' sheet se form bhariye aur har SDK ki guide se milayiye.", snippet={},
        refs=["play_datasafety"]),
    "content_rating": dict(
        title="Content rating aur Play Console registration", area="play", sev="info", masvs="MASVS-CODE-1",
        explain="July 2026 policy: bina content rating wali apps non-compliant hain aur har Play app Play Console mein registered "
                "honi chahiye.", fix="Play Console > Policy > App content mein rating questionnaire poora kijiye.", snippet={},
        refs=["play_jul26"]),
    "apple_basics": dict(
        title="iPhone (App Store) ke liye bhi", area="apple", sev="info", masvs="MASVS-PRIVACY-1",
        explain="{detail}", fix="Xcode mein PrivacyInfo.xcprivacy + App Privacy labels bhariye; third-party login ho to Sign in with Apple.",
        snippet={}, refs=["apple"]),
    "dpdp_notice": dict(
        title="DPDP: personal data se pehle notice + consent", area="dpdp", sev="medium", masvs="MASVS-PRIVACY-3",
        explain="App personal data leti hai ({detail}). DPDP Act 2023 + Rules 2025: saaf notice (kya, kyon, kaise hatwayein), alag "
                "consent, consent wapas lene ka utna hi aasaan raasta, aur grievance contact. Zyadatar duties 13 May 2027 se lagu.",
        fix="Pehli baar data lene se pehle Hindi / English notice screen + consent ka record; Settings mein 'consent wapas lo' aur "
            "grievance officer ka contact.", snippet={}, refs=["dpdp"]),
    "dpdp_children": dict(
        title="DPDP: bachchon (18 se kam) ka data", area="dpdp", sev="high", masvs="MASVS-PRIVACY-3",
        explain="Aapne bataya app bachchon ke liye hai. DPDP mein 18 se kam umar ke data ke liye maa-baap ki verifiable consent zaroori, "
                "aur tracking / behaviour monitoring / unke liye targeted ads mana.",
        fix="Parent consent flow (age gate + parent verification), tracking / ads SDK hatayiye.", snippet={}, refs=["dpdp"]),
    "rbi_payment": dict(
        title="Payment SDK mila: RBI niyam", area="rbi", sev="info", masvs="MASVS-STORAGE-1",
        explain="{detail}. Payment aggregator RBI-authorised hona chahiye; card number / CVV app ya server mein kabhi mat rakhiye "
                "(card-on-file tokenisation, 1 Oct 2022 se); payment data sirf India mein store (RBI 6 Apr 2018).",
        fix="Payment sirf SDK ke checkout se; order ka amount aur status apne SERVER par payment gateway se verify kijiye (signature), "
            "app ki baat par nahi.", snippet=_sn(web="# server: Razorpay webhook / payment signature verify\n"
                                                      "hmac_sha256(order_id + '|' + payment_id, KEY_SECRET) == signature"),
        refs=["rbi_pa", "rbi_local"]),
    "rbi_card_fields": dict(
        title="App card number / CVV khud le rahi hai", area="rbi", sev="high", masvs="MASVS-STORAGE-1",
        explain="{detail}: card details apni screen par lena aur rakhna RBI tokenisation niyam aur PCI-DSS ke khilaf ho sakta hai.",
        fix="Card sirf payment gateway ke SDK / hosted checkout mein; apne paas sirf token.", snippet={}, refs=["rbi_pa"]),
    "sms_and_payment": dict(
        title="SMS padhna + payment ek saath", area="security", sev="high", masvs="MASVS-PLATFORM-1",
        explain="App SMS padhti hai aur payment bhi karti hai: fraud apps yahi jodi rakhte hain; Play aur user dono shak karenge.",
        fix="SMS permission hatayiye (SMS Retriever).", snippet={}, refs=["play_perms"]),
    # ---- website
    "web_https": dict(title="Website HTTPS par nahi / http se https par nahi jaati", area="web", sev="high", masvs="MASVS-NETWORK-1",
                      explain="{detail}", fix="SSL certificate (Let's Encrypt / Cloudflare) lagaiye aur http -> https 301 redirect.",
                      snippet=_sn(web="server { listen 80; server_name aapka.in; return 301 https://$host$request_uri; }"),
                      refs=["owasp_headers"]),
    "web_cert": dict(title="SSL certificate jaldi khatam", area="web", sev="medium", masvs="MASVS-NETWORK-1", explain="{detail}",
                     fix="Auto-renew (certbot timer / hosting panel) chalu kijiye.", snippet={}, refs=["owasp_headers"]),
    "web_hsts": dict(title="HSTS header nahi", area="web", sev="low", masvs="MASVS-NETWORK-1",
                     explain="Browser ko 'hamesha https' nahi bataya; pehli http request beech mein pakdi ja sakti hai.",
                     fix="Strict-Transport-Security header.", snippet=_sn(web='add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'),
                     refs=["owasp_headers"]),
    "web_csp": dict(title="Content-Security-Policy nahi", area="web", sev="low", masvs="MASVS-CODE-4",
                    explain="CSP na hone se koi ghus aaya script (XSS) aaram se chal jaata hai.",
                    fix="Pehle Content-Security-Policy-Report-Only se shuru kijiye, phir lagu.",
                    snippet=_sn(web="add_header Content-Security-Policy \"default-src 'self'; img-src 'self' data: https:; frame-ancestors 'self'\" always;"),
                    refs=["owasp_headers"]),
    "web_frame": dict(title="Website doosri site ke frame mein khul sakti hai", area="web", sev="low", masvs="MASVS-PLATFORM-1",
                      explain="X-Frame-Options / frame-ancestors nahi: clickjacking (nakli button ke neeche aapki site).",
                      fix="X-Frame-Options: SAMEORIGIN (ya CSP frame-ancestors).", snippet=_sn(web='add_header X-Frame-Options "SAMEORIGIN" always;'),
                      refs=["owasp_headers"]),
    "web_nosniff": dict(title="X-Content-Type-Options nahi", area="web", sev="low", masvs="MASVS-CODE-4",
                        explain="Browser file ka type andaaze se badal sakta hai.", fix="X-Content-Type-Options: nosniff.",
                        snippet=_sn(web='add_header X-Content-Type-Options "nosniff" always;'), refs=["owasp_headers"]),
    "web_referrer": dict(title="Referrer-Policy nahi", area="web", sev="info", masvs="MASVS-PRIVACY-1",
                         explain="Poora page address (kabhi kabhi token ke saath) doosri sites ko jaata hai.",
                         fix="Referrer-Policy: strict-origin-when-cross-origin.", snippet={}, refs=["owasp_headers"]),
    "web_server_leak": dict(title="Server ka software version dikhta hai", area="web", sev="low", masvs="MASVS-CODE-3",
                            explain="{detail}: hamlavar ko pata chal jaata hai kaunsa purana version hai.",
                            fix="server_tokens off / X-Powered-By hatayiye; software update rakhiye.", snippet=_sn(web="server_tokens off;"),
                            refs=["owasp_headers"]),
    "web_cookie": dict(title="Cookie bina Secure / HttpOnly / SameSite", area="web", sev="medium", masvs="MASVS-AUTH-2",
                       explain="{detail}: login cookie script ya http se chori ho sakti hai.",
                       fix="Set-Cookie: ...; Secure; HttpOnly; SameSite=Lax.", snippet={}, refs=["owasp_headers"]),
    "web_mixed": dict(title="HTTPS page par http:// cheezein (mixed content)", area="web", sev="medium", masvs="MASVS-NETWORK-1",
                      explain="{detail}: browser inhe rok deta hai ya page 'Not secure' dikhata hai.", fix="Sab src / href https:// kijiye.",
                      snippet={}, refs=["owasp_headers"]),
    "web_exposed": dict(title="Website par andar ki file khuli hai", area="web", sev="critical", masvs="MASVS-STORAGE-1",
                        explain="{detail} internet par koi bhi padh sakta hai (code, passwords, database ka pata).",
                        fix="File server se hatayiye / nginx mein deny kijiye, aur andar ki har key / password badaliye.",
                        snippet=_sn(web="location ~ /\\.(git|env|svn|hg) { deny all; return 404; }"), refs=["owasp_headers"]),
    "web_security_txt": dict(title="security.txt nahi", area="web", sev="info", masvs="MASVS-CODE-3",
                             explain="Koi bug bataana chahe to kahan bataye, yeh likha nahi.",
                             fix="/.well-known/security.txt mein Contact: aur Expires:.", snippet={}, refs=["owasp_headers"]),
}

MASVS_TITLES = {"MASVS-STORAGE": "Data ka safe rakhna", "MASVS-CRYPTO": "Encryption", "MASVS-AUTH": "Login / session",
                "MASVS-NETWORK": "Network (HTTPS)", "MASVS-PLATFORM": "Android ke saath baat", "MASVS-CODE": "Code / build",
                "MASVS-RESILIENCE": "Chhed-chhaad se bachav", "MASVS-PRIVACY": "Privacy"}

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
    ("weak_tls", re.compile(r"checkServerTrusted\s*\([^)]*\)\s*(?::\s*Unit\s*)?\{\s*\}"), "khaali checkServerTrusted"),
    ("weak_tls", re.compile(r"ALLOW_ALL_HOSTNAME_VERIFIER|HostnameVerifier\s*\{\s*_?\s*,\s*_?\s*->\s*true|verify\s*\([^)]*\)\s*(?::\s*Boolean)?\s*(?:=\s*true|\{\s*return\s+true)"),
     "har hostname maanne wala verifier"),
    ("weak_tls", re.compile(r"badCertificateCallback\s*=\s*\([^)]*\)\s*(?:=>\s*true|\{\s*return\s+true)"), "Dart badCertificateCallback true"),
    ("weak_tls", re.compile(r"rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0"), "Node TLS jaanch band"),
    ("webview_js_bridge", re.compile(r"addJavascriptInterface\s*\("), "addJavascriptInterface"),
    ("webview_js_bridge", re.compile(r"setAllowUniversalAccessFromFileURLs\s*\(\s*true|allowUniversalAccessFromFileURLs\s*=\s*true"),
     "file URL se har jagah access"),
    ("weak_crypto", re.compile(r"Cipher\.getInstance\(\s*\"(?:AES|DES|DESede|AES/ECB[^\"]*)\"\s*\)|MessageDigest\.getInstance\(\s*\"(?:MD5|SHA-?1)\"\)"),
     "AES/ECB, DES, MD5 ya SHA-1"),
    ("weak_crypto", re.compile(r"\bmd5\s*\(|createHash\(\s*['\"](?:md5|sha1)['\"]"), "MD5 / SHA-1 hash"),
    ("insecure_random", re.compile(r"(?i)(?:otp|token|password|secret|nonce)\w*\s*=.*(?:java\.util\.Random\(|\bRandom\(\)\.next|Math\.random\(\))"),
     "OTP / token ke liye Random"),
    ("plain_storage", re.compile(r"(?i)(?:putString|setString|localStorage\.setItem|AsyncStorage\.setItem)\s*\(\s*['\"][^'\"]*(?:token|password|pin|secret)[^'\"]*['\"]"),
     "token / password khule storage mein"),
    ("log_secret", re.compile(r"(?i)(?:Log\.[dviwe]|print|debugPrint|console\.log)\s*\(.*\b(?:password|otp|token|pin|cvv)\b"),
     "log mein password / OTP / token"),
    ("sql_concat", re.compile(r"(?:rawQuery|execSQL|rawInsert|query)\s*\(\s*[\"'`][^\"'`]*(?:WHERE|where)[^\"'`]*[\"'`]\s*\+"),
     "SQL mein + se joda text"),
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
