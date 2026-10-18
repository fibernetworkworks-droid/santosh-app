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
