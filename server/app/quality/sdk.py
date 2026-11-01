"""v0.378 MOBILE CARD - the toolchains the Dart / Kotlin coding jobs are checked with (owner: "GO 4").

Found in CODECARD_SDK (default ~/apps/codecard-sdk), else on PATH:
  dart-sdk/bin/dart   Dart SDK (Google's official archive)
  kotlinc/bin/kotlinc Kotlin compiler (JetBrains' GitHub release)
  jre/bin/java        a Java runtime for kotlinc, only fetched when the machine has no java (Eclipse Temurin via Adoptium)
`python -m app.quality sdk` shows what is there; `python -m app.quality sdk --setup` downloads what is missing (official
sources only, ~330 MB, once). Nothing here runs on its own: the card uses a toolchain only when it is present, and a job whose
toolchain is missing is SKIPPED, never failed."""
from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

DART_VERSION = "3.13.7"
KOTLIN_VERSION = "2.2.20"
DART_URL = (f"https://storage.googleapis.com/dart-archive/channels/stable/release/{DART_VERSION}/sdk/"
            "dartsdk-linux-x64-release.zip")
KOTLIN_URL = f"https://github.com/JetBrains/kotlin/releases/download/v{KOTLIN_VERSION}/kotlin-compiler-{KOTLIN_VERSION}.zip"
JRE_URL = "https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jre/hotspot/normal/eclipse"


def root() -> Path:
    return Path(os.environ.get("CODECARD_SDK") or Path.home() / "apps" / "codecard-sdk")


def _exe(rel: str, name: str) -> str:
    p = root() / rel
    if p.is_file() and os.access(p, os.X_OK):
        return str(p)
    return shutil.which(name) or ""


def dart() -> str:
    return _exe("dart-sdk/bin/dart", "dart")


def kotlinc() -> str:
    return _exe("kotlinc/bin/kotlinc", "kotlinc")


def java() -> str:
    return _exe("jre/bin/java", "java")


def kotlin_stdlib() -> str:
    """kotlin-stdlib.jar next to the compiler (the compiled checks / tests run on it)."""
    k = kotlinc()
    if not k:
        return ""
    lib = Path(os.path.realpath(k)).parent.parent / "lib" / "kotlin-stdlib.jar"
    return str(lib) if lib.is_file() else ""


def env_extra() -> dict[str, str]:
    """JAVA_HOME + PATH for a child that runs kotlinc / java (the SDK's own JRE first when it has one)."""
    j = java()
    if not j:
        return {}
    home = str(Path(os.path.realpath(j)).parent.parent)
    return {"JAVA_HOME": home, "PATH": f"{Path(home) / 'bin'}:{os.environ.get('PATH', '/usr/bin:/bin')}"}


def have(lang: str) -> bool:
    if lang == "dart":
        return bool(dart())
    if lang == "kotlin":
        return bool(kotlinc() and java() and kotlin_stdlib())
    return True


def status() -> list[str]:
    def ver(cmd: list[str]) -> str:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env={**os.environ, **env_extra()})
            return ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-1][:90]
        except Exception as e:  # noqa: BLE001
            return f"error: {e}"[:90]
    out = [f"SDK folder: {root()}"]
    out.append(f"  dart:    {dart() or 'missing'}" + (f"  ({ver([dart(), '--version'])})" if dart() else ""))
    out.append(f"  java:    {java() or 'missing'}" + (f"  ({ver([java(), '-version'])})" if java() else ""))
    out.append(f"  kotlinc: {kotlinc() or 'missing'}" + (f"  ({ver([kotlinc(), '-version'])})" if kotlinc() else ""))
    out.append(f"  Dart jobs: {'ready' if have('dart') else 'will be SKIPPED'} · Kotlin jobs: "
               f"{'ready' if have('kotlin') else 'will be SKIPPED'}")
    return out


def _fetch(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Hoola-codecard/1.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:  # noqa: S310 - fixed official URLs
        shutil.copyfileobj(r, f, 1 << 20)


def _unzip(zpath: Path, into: Path) -> None:
    with zipfile.ZipFile(zpath) as z:
        for m in z.infolist():
            target = (into / m.filename).resolve()
            if not str(target).startswith(str(into.resolve()) + os.sep):
                continue                                   # never outside the SDK folder
            if m.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(m) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            mode = (m.external_attr >> 16) & 0o777
            if mode:
                os.chmod(target, mode)


def setup() -> list[str]:
    """Download what is missing into root(). Idempotent."""
    r = root()
    r.mkdir(parents=True, exist_ok=True)
    said = []
    with tempfile.TemporaryDirectory(dir=str(r)) as tmp:
        t = Path(tmp)
        if not (r / "dart-sdk/bin/dart").is_file():
            _fetch(DART_URL, t / "dart.zip")
            _unzip(t / "dart.zip", r)
            said.append(f"Dart {DART_VERSION} installed")
        if not (r / "kotlinc/bin/kotlinc").is_file():
            _fetch(KOTLIN_URL, t / "kotlin.zip")
            _unzip(t / "kotlin.zip", r)
            said.append(f"Kotlin {KOTLIN_VERSION} installed")
        if not java():
            _fetch(JRE_URL, t / "jre.tgz")
            with tarfile.open(t / "jre.tgz") as tf:
                top = tf.getnames()[0].split("/")[0]
                tf.extractall(t, filter="data")
            shutil.move(str(t / top), str(r / "jre"))
            said.append("Java runtime (Temurin 21) installed")
    return said or ["Everything was already installed."]
