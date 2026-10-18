#!/usr/bin/env python3
"""Run once after `flutter create`: installs Santosh's AndroidManifest and turns on the
Gradle settings the plugins need (Java 8+ library desugaring for notifications, minSdk 23)."""
import re
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = root / "android" / "app"
if not app.exists():
    sys.exit("android/app not found. Run: flutter create --org com.newtika --project-name santosh --platforms android .")

shutil.copy(root / "tool" / "AndroidManifest.xml", app / "src" / "main" / "AndroidManifest.xml")

kts = app / "build.gradle.kts"
groovy = app / "build.gradle"
if kts.exists():
    g = kts.read_text()
    if "isCoreLibraryDesugaringEnabled" not in g:
        g = g.replace("compileOptions {", "compileOptions {\n        isCoreLibraryDesugaringEnabled = true", 1)
    g = re.sub(r"minSdk\s*=\s*flutter\.minSdkVersion", "minSdk = 23", g)
    if "desugar_jdk_libs" not in g:
        g += '\ndependencies {\n    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")\n}\n'
    kts.write_text(g)
elif groovy.exists():
    g = groovy.read_text()
    if "coreLibraryDesugaringEnabled" not in g:
        g = g.replace("compileOptions {", "compileOptions {\n        coreLibraryDesugaringEnabled true", 1)
    g = re.sub(r"minSdk(Version)?\s*=?\s*flutter\.minSdkVersion", "minSdk = 23", g)
    if "desugar_jdk_libs" not in g:
        g += "\ndependencies {\n    coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.4'\n}\n"
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
