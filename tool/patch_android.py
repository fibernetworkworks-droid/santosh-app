#!/usr/bin/env python3
"""Run once after `flutter create`: installs Santosh's AndroidManifest and turns on the
Gradle settings the plugins need (Java 8+ library desugaring for notifications, minSdk 23)."""
import os
import re
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = root / "android" / "app"
if not app.exists():
    sys.exit("android/app not found. Run: flutter create --org com.newtika --project-name santosh --platforms android .")

shutil.copy(root / "tool" / "AndroidManifest.xml", app / "src" / "main" / "AndroidManifest.xml")
# v0.72 keep rules for the release shrinker (ONNX Runtime JNI, flutter_local_notifications' Gson). Flutter's Gradle
# plugin adds app/proguard-rules.pro to the release build automatically.
_pg = app / "proguard-rules.pro"
_rules = (root / "tool" / "android" / "proguard-rules.pro").read_text()
if not _pg.exists() or "ai.onnxruntime" not in _pg.read_text():
    _pg.write_text((_pg.read_text() + "\n" if _pg.exists() else "") + _rules)
# v0.62 Play Store build (HOOLA_CHANNEL=play): no self-update permission, the in-app updater turns itself off
if os.environ.get("HOOLA_CHANNEL", "github").strip().lower() == "play":
    mf = app / "src" / "main" / "AndroidManifest.xml"
    t = re.sub(r"\s*<uses-permission android:name=\"android\.permission\.REQUEST_INSTALL_PACKAGES\" />", "", mf.read_text())
    t = t.replace('android:name="hoola.channel" android:value="github"', 'android:name="hoola.channel" android:value="play"')
    mf.write_text(t)
    print("Channel: play (no REQUEST_INSTALL_PACKAGES, updater off)")

kts = app / "build.gradle.kts"
groovy = app / "build.gradle"
if kts.exists():
    g = kts.read_text()
    if "isCoreLibraryDesugaringEnabled" not in g:
        g = g.replace("compileOptions {", "compileOptions {\n        isCoreLibraryDesugaringEnabled = true", 1)
    g = re.sub(r"minSdk\s*=\s*flutter\.minSdkVersion", "minSdk = 23", g)
    if "desugar_jdk_libs" not in g:
        g += '\ndependencies {\n    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")\n}\n'
    if "onnxruntime-android" not in g:
        g += '\ndependencies {\n    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.20.0")\n}\n'
    if "media3-transformer" not in g:   # v0.49 VideoShrink.kt (Jetpack Media3, Apache-2.0)
        g += ('\ndependencies {\n    implementation("androidx.media3:media3-transformer:1.4.1")\n'
              '    implementation("androidx.media3:media3-effect:1.4.1")\n    implementation("androidx.media3:media3-common:1.4.1")\n}\n')
    if "androidx.core:core" not in g:   # v0.63 FileProvider for sharing Hoola Motion videos
        g += '\ndependencies {\n    implementation("androidx.core:core:1.13.1")\n}\n'
    if "play-services-auth-api-phone" not in g:   # v0.83 OtpConsent.kt (SMS User Consent: one-tap Allow, no SMS permission)
        g += '\ndependencies {\n    implementation("com.google.android.gms:play-services-auth-api-phone:18.1.0")\n}\n'
    kts.write_text(g)
elif groovy.exists():
    g = groovy.read_text()
    if "coreLibraryDesugaringEnabled" not in g:
        g = g.replace("compileOptions {", "compileOptions {\n        coreLibraryDesugaringEnabled true", 1)
    g = re.sub(r"minSdk(Version)?\s*=?\s*flutter\.minSdkVersion", "minSdk = 23", g)
    if "desugar_jdk_libs" not in g:
        g += "\ndependencies {\n    coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.4'\n}\n"
    if "onnxruntime-android" not in g:
        g += "\ndependencies {\n    implementation 'com.microsoft.onnxruntime:onnxruntime-android:1.20.0'\n}\n"
    if "media3-transformer" not in g:
        g += ("\ndependencies {\n    implementation 'androidx.media3:media3-transformer:1.4.1'\n"
              "    implementation 'androidx.media3:media3-effect:1.4.1'\n    implementation 'androidx.media3:media3-common:1.4.1'\n}\n")
    if "androidx.core:core" not in g:
        g += "\ndependencies {\n    implementation 'androidx.core:core:1.13.1'\n}\n"
    if "play-services-auth-api-phone" not in g:
        g += "\ndependencies {\n    implementation 'com.google.android.gms:play-services-auth-api-phone:18.1.0'\n}\n"
    groovy.write_text(g)
else:
    sys.exit("No app build.gradle(.kts) found")

# Santosh's native side: background service, own alarms, calendar, boot restart
pkg = app / "src" / "main" / "kotlin" / "com" / "newtika" / "santosh"
pkg.mkdir(parents=True, exist_ok=True)
for f in (root / "tool" / "android" / "kotlin").glob("*.kt"):
    shutil.copy(f, pkg / f.name)
for f in (root / "tool" / "android" / "res").rglob("*"):
    if f.is_file():
        dest = app / "src" / "main" / "res" / f.relative_to(root / "tool" / "android" / "res")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, dest)
# Santosh Wake models (on-device "Hey Santosh")
for f in (root / "tool" / "android" / "assets").rglob("*.onnx"):
    dest = app / "src" / "main" / "assets" / f.relative_to(root / "tool" / "android" / "assets")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(f, dest)
# flutter create may have put a Java or differently named MainActivity elsewhere; ours replaces it
for old in (app / "src" / "main").rglob("MainActivity.*"):
    if old.parent != pkg:
        old.unlink()

# Release signing with your own permanent key (GitHub secrets ANDROID_KEYSTORE_B64 + ANDROID_KEY_PASSWORD).
# Same key every build = phone updates install over the old app. Without the secrets: debug signing.
import base64, os
ks_b64, ks_pw = os.environ.get("ANDROID_KEYSTORE_B64", "").strip(), os.environ.get("ANDROID_KEY_PASSWORD", "").strip()
if ks_b64 and ks_pw:
    (app / "santosh.p12").write_bytes(base64.b64decode(ks_b64))
    pw = ks_pw.replace("\\", "\\\\").replace('"', '\\"')
    if kts.exists():
        g = kts.read_text()
        block = ('    signingConfigs {\n        create("release") {\n            storeFile = file("santosh.p12")\n'
                 f'            storePassword = "{pw}"\n            keyAlias = "santosh"\n            keyPassword = "{pw}"\n'
                 '            storeType = "pkcs12"\n        }\n    }\n')
        g = g.replace("    buildTypes {", block + "    buildTypes {", 1)
        g = g.replace("signingConfig = signingConfigs.getByName(\"debug\")", "signingConfig = signingConfigs.getByName(\"release\")")
        kts.write_text(g)
    else:
        g = groovy.read_text()
        block = ("    signingConfigs {\n        release {\n            storeFile file('santosh.p12')\n"
                 f'            storePassword "{pw}"\n            keyAlias "santosh"\n            keyPassword "{pw}"\n'
                 "            storeType 'pkcs12'\n        }\n    }\n")
        g = g.replace("    buildTypes {", block + "    buildTypes {", 1)
        g = re.sub(r"signingConfig\s*=?\s*signingConfigs\.debug", "signingConfig = signingConfigs.release", g)
        groovy.write_text(g)
    print("Release signing: your permanent key")
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write("SIGNED=yes\n")
else:
    print("Release signing: debug key (add the ANDROID_KEYSTORE_B64 and ANDROID_KEY_PASSWORD secrets for updates that install over the old app)")

# Firebase Cloud Messaging (push when the app is closed): google-services.json + Gradle plugin + messaging library
gs = root / "tool" / "android" / "google-services.json"
if gs.exists():
    shutil.copy(gs, app / "google-services.json")
    for name in ("settings.gradle.kts", "settings.gradle"):
        f = root / "android" / name
        if f.exists():
            s = f.read_text()
            if "com.google.gms.google-services" not in s:
                line = ('    id("com.google.gms.google-services") version "4.4.2" apply false\n' if name.endswith(".kts")
                        else '    id "com.google.gms.google-services" version "4.4.2" apply false\n')
                s = re.sub(r"(plugins\s*\{\n)", lambda m: m.group(1) + line, s, count=1)
                f.write_text(s)
    if kts.exists():
        g = kts.read_text()
        if "com.google.gms.google-services" not in g:
            g = re.sub(r"(plugins\s*\{[^}]*?)(\n\})", lambda m: m.group(1) + '\n    id("com.google.gms.google-services")' + m.group(2), g, count=1)
            g += ('\ndependencies {\n    implementation(platform("com.google.firebase:firebase-bom:33.5.1"))\n'
                  '    implementation("com.google.firebase:firebase-messaging")\n}\n')
        kts.write_text(g)
    else:
        g = groovy.read_text()
        if "com.google.gms.google-services" not in g:
            g = re.sub(r"(plugins\s*\{[^}]*?)(\n\})", lambda m: m.group(1) + '\n    id "com.google.gms.google-services"' + m.group(2), g, count=1)
            g += ("\ndependencies {\n    implementation platform('com.google.firebase:firebase-bom:33.5.1')\n"
                  "    implementation 'com.google.firebase:firebase-messaging'\n}\n")
        groovy.write_text(g)
    print("Firebase messaging: on")
else:
    (pkg / "SantoshPush.kt").unlink(missing_ok=True)
    m = app / "src" / "main" / "AndroidManifest.xml"
    m.write_text(re.sub(r"\s*<service\s+android:name=\"\.SantoshPush\".*?</service>", "", m.read_text(), flags=re.S))
    print("Firebase messaging: off (no tool/android/google-services.json)")

# flutter create adds a sample test that refers to a MyApp class we don't have
t = root / "test" / "widget_test.dart"
if t.exists() and "MyApp" in t.read_text():
    t.unlink()

print("Android project patched for Santosh.")

# Kotlin Gradle plugin new enough for current AndroidX / plugin libraries
for name in ("settings.gradle", "settings.gradle.kts"):
    f = root / "android" / name
    if f.exists():
        s = f.read_text()
        s2 = re.sub(r'(id[ (]+"org\.jetbrains\.kotlin\.android"\)?\s+version\s+")[^"]+(")', r'\g<1>2.2.20\g<2>', s)
        f.write_text(s2)
        print("Kotlin plugin set to 2.2.20 in", name, "(changed)" if s2 != s else "(pattern not found!)")
