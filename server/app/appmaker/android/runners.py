"""v0.132: where a native Android build runs. NEVER on the Hoola server itself (a Gradle build needs ~3 GB RAM and minutes of
CPU): a separate build machine running server/app_builder ('worker'), a private GitHub repo's Actions runner ('github'), or this
machine only when it has an Android SDK ('local', used by developers). Nothing configured -> the project ZIP alone.

Every runner takes a finished project folder and returns {ok, log, apk (bytes) | None, seconds, where}."""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import logging
import os
import shutil
import subprocess
import time
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("santosh.appmaker.android")
Progress = Callable[[str], None]


class BuildUnavailable(Exception):
    """No build machine is set up (the owner still gets the project ZIP)."""


def zip_project(src: Path, export: bool = False) -> bytes:
    """The project as a zip. export=True (her download) leaves out the preview signing key and its password; the build
    machine gets them (it signs the APK)."""
    import re
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src).as_posix()
            if p.is_dir() or rel.startswith((".gradle/", "build/", "app/build/")) or (export and rel.startswith("keys/")):
                continue
            data = p.read_bytes()
            if export and rel == "app/build.gradle.kts":
                data = re.sub(rb'\?: "[A-Za-z0-9]*"', b'?: ""', data)
            info = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 if rel == "gradlew" else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return buf.getvalue()


def _settings():
    from ...config import get_settings
    return get_settings()


def mode() -> str:
    s = _settings()
    m = (s.app_build_mode or "").strip().lower()
    if m == "worker" and s.app_build_url and s.app_build_secret:
        return "worker"
    if m == "github" and s.app_build_gh_repo and s.app_build_gh_token:
        return "github"
    if m == "local" and (os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")):
        return "local"
    return ""


def describe() -> dict[str, Any]:
    m = mode()
    return {"mode": m, "ready": bool(m), "where": {"worker": "Hoola build machine", "github": "GitHub Actions (private repo)",
                                                   "local": "this machine", "": "not set up"}[m]}


# ---------------------------------------------------------------- worker (server/app_builder)
def sign(secret: str, method: str, path: str, ts: str, body: bytes) -> str:
    msg = f"{method}\n{path}\n{ts}\n".encode() + hashlib.sha256(body).hexdigest().encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def _w(method: str, path: str, body: bytes = b"", timeout: int = 60) -> tuple[int, bytes, dict[str, str]]:
    s = _settings()
    base = s.app_build_url.rstrip("/")
    if not base.startswith("https://") and not base.startswith("http://127.0.0.1") and not base.startswith("http://localhost"):
        raise BuildUnavailable("APP_BUILD_URL must be https")
    ts = str(int(time.time()))
    req = urllib.request.Request(base + path, data=body if method == "POST" else None, method=method,
                                 headers={"X-Hoola-Time": ts, "X-Hoola-Sign": sign(s.app_build_secret, method, path, ts, body),
                                          "Content-Type": "application/zip" if body else "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})


def run_worker(src: Path, key: str, progress: Progress, kind: str = "apk") -> dict[str, Any]:
    t0 = time.time()
    data = zip_project(src)
    st, body, _h = _w("POST", f"/build?app={urllib.parse.quote(key)}" + ("&kind=aab" if kind == "aab" else ""), data, timeout=120)
    if st != 200:
        raise BuildUnavailable(f"build machine said {st}: {body[:200].decode(errors='replace')}")
    job = json.loads(body)["job"]
    limit = _settings().app_build_timeout_s
    last = ""
    while time.time() - t0 < limit + 60:
        time.sleep(4)
        st, body, _h = _w("GET", f"/jobs/{job}")
        if st != 200:
            continue
        j = json.loads(body)
        if j.get("stage") and j["stage"] != last:
            last = j["stage"]
            progress(last)
        if j.get("status") in ("ok", "failed"):
            apk = None
            if j["status"] == "ok":
                st2, apk, _ = _w("GET", f"/jobs/{job}/apk", timeout=300)
                apk = apk if st2 == 200 else None
            st3, logb, _ = _w("GET", f"/jobs/{job}/log", timeout=60)
            qa = None
            if apk and kind != "aab":              # v0.325 the device check, when that machine has an emulator
                st4, qb, _ = _w("GET", f"/jobs/{job}/qa", timeout=120)
                qa = qa_from_zip(qb) if st4 == 200 else None
            return {"ok": bool(apk), "log": logb.decode(errors="replace") if st3 == 200 else j.get("tail", ""), "apk": apk,
                    "seconds": round(time.time() - t0), "where": "worker", "qa": qa}
    return {"ok": False, "log": "build timed out", "apk": None, "seconds": round(time.time() - t0), "where": "worker"}


def qa_from_zip(zb: bytes) -> dict[str, Any] | None:
    """v0.325 HOOLA QA: {report, shots{screen id: png}} from a zip holding report.json + screens/*.png (any folder)."""
    try:
        with zipfile.ZipFile(io.BytesIO(zb)) as z:
            names = z.namelist()
            rep = next((n for n in names if n.endswith("report.json")), None)
            if not rep:
                return None
            report = json.loads(z.read(rep))
            shots = {}
            for n in names:
                m = re.search(r"screens/([a-z][a-z0-9_]{0,48})\.png$", n)
                if m and z.getinfo(n).file_size < 6_000_000:
                    shots[m.group(1)] = z.read(n)
            return {"report": report, "shots": shots}
    except (zipfile.BadZipFile, ValueError, KeyError):
        return None


# ---------------------------------------------------------------- github (private builds repo, workflow hoola-build.yml)
GH = "https://api.github.com"


def _gh(method: str, path: str, payload: Any = None, raw: bool = False, timeout: int = 60) -> Any:
    s = _settings()
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(GH + path, data=data, method=method,
                                 headers={"Authorization": f"Bearer {s.app_build_gh_token}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Hoola-AppBuild"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read()
            return b if raw else (json.loads(b) if b else {})
    except urllib.error.HTTPError as e:
        if e.code == 404 and method == "GET" and not raw:
            return None
        raise BuildUnavailable(f"GitHub {method} {path.split('?')[0]}: {e.code} {e.read()[:160].decode(errors='replace')}")


class _NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    """Artifact downloads redirect to blob storage: follow WITHOUT our token."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return urllib.request.Request(newurl, headers={"User-Agent": "Hoola-AppBuild"})


def run_github(src: Path, key: str, progress: Progress, kind: str = "apk") -> dict[str, Any]:
    s = _settings()
    repo = s.app_build_gh_repo.strip()
    t0 = time.time()
    branch = f"build/{key}"
    head = _gh("GET", f"/repos/{repo}/git/ref/heads/main") or _gh("GET", f"/repos/{repo}/git/ref/heads/master")
    if not head:
        raise BuildUnavailable(f"{repo}: no main branch")
    base_sha = head["object"]["sha"]
    base_tree = _gh("GET", f"/repos/{repo}/git/commits/{base_sha}")["tree"]["sha"]
    progress("uploading")
    tree = []
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src).as_posix()
        if p.is_dir() or rel.startswith((".gradle/", "build/", "app/build/")):
            continue
        b = _gh("POST", f"/repos/{repo}/git/blobs", {"content": base64.b64encode(p.read_bytes()).decode(), "encoding": "base64"})
        tree.append({"path": f"app/{rel}", "mode": "100755" if rel == "gradlew" else "100644", "type": "blob", "sha": b["sha"]})
    t = _gh("POST", f"/repos/{repo}/git/trees", {"base_tree": base_tree, "tree": tree})
    c = _gh("POST", f"/repos/{repo}/git/commits", {"message": f"build {key}", "tree": t["sha"], "parents": [base_sha]})
    if _gh("GET", f"/repos/{repo}/git/ref/heads/{branch}"):
        _gh("PATCH", f"/repos/{repo}/git/refs/heads/{branch}", {"sha": c["sha"], "force": True})
    else:
        _gh("POST", f"/repos/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": c["sha"]})
    job = hashlib.sha256(f"{key}{c['sha']}{time.time()}".encode()).hexdigest()[:16]
    inputs = {"job": job, **({"kind": "aab"} if kind == "aab" else {})}     # v0.330 a Play Store bundle (new hoola-build.yml)
    _gh("POST", f"/repos/{repo}/actions/workflows/hoola-build.yml/dispatches", {"ref": branch, "inputs": inputs})
    progress("queued")
    run = None
    limit = s.app_build_timeout_s
    while time.time() - t0 < limit + 300:
        time.sleep(10)
        runs = _gh("GET", f"/repos/{repo}/actions/runs?branch={urllib.parse.quote(branch)}&event=workflow_dispatch&per_page=5") or {}
        for r in runs.get("workflow_runs", []):
            if r.get("head_sha") == c["sha"]:
                run = r
                break
        if not run:
            continue
        if run.get("status") == "in_progress":
            progress("compiling")
        if run.get("status") == "completed":
            break
    if not run or run.get("status") != "completed":
        return {"ok": False, "log": "GitHub build timed out", "apk": None, "seconds": round(time.time() - t0), "where": "github"}
    arts = _gh("GET", f"/repos/{repo}/actions/runs/{run['id']}/artifacts") or {}
    apk, text, qa = None, "", None
    for a in arts.get("artifacts", []):
        if a.get("name") != f"hoola-{job}" and a.get("name") != "hoola-build":
            continue
        req = urllib.request.Request(f"{GH}/repos/{repo}/actions/artifacts/{a['id']}/zip",
                                     headers={"Authorization": f"Bearer {s.app_build_gh_token}", "User-Agent": "Hoola-AppBuild"})
        with urllib.request.build_opener(_NoAuthRedirect).open(req, timeout=300) as r:
            zb = r.read()
        with zipfile.ZipFile(io.BytesIO(zb)) as z:
            for n in z.namelist():
                if n.endswith(".aab" if kind == "aab" else ".apk"):
                    apk = z.read(n)
                elif n.endswith("build.log"):
                    text = z.read(n).decode(errors="replace")
        qa = qa_from_zip(zb)                       # v0.325 the device check's report + pictures (folder qa/)
    ok = run.get("conclusion") == "success" and bool(apk)
    return {"ok": ok, "log": text or f"GitHub run {run.get('conclusion')}", "apk": apk if ok else None,
            "seconds": round(time.time() - t0), "where": "github", "qa": qa if ok else None}


# ---------------------------------------------------------------- local (a developer machine with the Android SDK)
def run_local(src: Path, key: str, progress: Progress, kind: str = "apk") -> dict[str, Any]:
    t0 = time.time()
    progress("compiling")
    env = {k: v for k, v in os.environ.items() if not any(w in k.upper() for w in ("KEY", "TOKEN", "SECRET", "PASS"))}
    env["HOOLA_PREVIEW_KEY_PASS"] = os.environ.get("HOOLA_PREVIEW_KEY_PASS", "")
    if not env["HOOLA_PREVIEW_KEY_PASS"]:
        env.pop("HOOLA_PREVIEW_KEY_PASS")
    try:
        p = subprocess.run(["./gradlew", "--no-daemon", "--console=plain", "bundleRelease" if kind == "aab" else "assembleRelease"], cwd=src, env=env,
                           capture_output=True, text=True, timeout=_settings().app_build_timeout_s)
        out = (p.stdout or "") + "\n" + (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else str(e.stdout or "")
        return {"ok": False, "log": out + "\nbuild timed out", "apk": None, "seconds": round(time.time() - t0), "where": "local"}
    od = src / ("app/build/outputs/bundle/release" if kind == "aab" else "app/build/outputs/apk/release")
    apk_p = next(iter(sorted(od.glob("*.aab" if kind == "aab" else "*.apk"))), None) if od.exists() else None
    apk = apk_p.read_bytes() if (p.returncode == 0 and apk_p) else None
    return {"ok": bool(apk), "log": out, "apk": apk, "seconds": round(time.time() - t0), "where": "local"}


RUNNERS: dict[str, Callable[[Path, str, Progress], dict[str, Any]]] = {"worker": run_worker, "github": run_github, "local": run_local}
_override: Callable[[Path, str, Progress], dict[str, Any]] | None = None


def set_runner(fn: Callable[[Path, str, Progress], dict[str, Any]] | None) -> None:
    """Tests: a fake build machine."""
    global _override
    _override = fn


def build(src: Path, key: str, progress: Progress, kind: str = "apk") -> dict[str, Any]:
    """kind 'apk' = the preview build (+ device check); 'aab' = v0.330 the Play Store bundle (result['apk'] holds its bytes)."""
    if _override:
        return _override(src, key, progress, kind) if kind != "apk" else _override(src, key, progress)
    m = mode()
    if not m:
        raise BuildUnavailable("no build machine set up")
    work = src.with_name(src.name + "-run")
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(src, work)
    try:
        return RUNNERS[m](work, key, progress, kind)
    finally:
        shutil.rmtree(work, ignore_errors=True)
