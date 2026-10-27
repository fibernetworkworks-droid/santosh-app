"""Hoola App Builder (v0.132): a small build machine for native Android apps, run on a SEPARATE server, never the Hoola VPS.

The Hoola server sends a finished Gradle project (zip, HMAC-signed with APP_BUILD_SECRET); this runs `./gradlew
assembleRelease` in a per-app folder (kept, so the next build of the same app is incremental), one build at a time, and
hands back the APK + the log. Standard library only.

    HOOLA_BUILD_SECRET=... HOOLA_BUILD_HOME=/srv/hoola-build python3 worker.py --port 8090      (behind nginx with TLS)
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SECRET = os.environ.get("HOOLA_BUILD_SECRET", "")
HOME = Path(os.environ.get("HOOLA_BUILD_HOME", "/srv/hoola-build"))
TIMEOUT = int(os.environ.get("HOOLA_BUILD_TIMEOUT", "1500"))
MAX_ZIP = 60 * 1024 * 1024
MAX_FILES = 3000
KEEP_JOBS_S = 24 * 3600
JOBS: dict[str, dict] = {}
Q: "queue.Queue[str]" = queue.Queue()
LOCK = threading.Lock()


def sign(method: str, path: str, ts: str, body: bytes) -> str:
    msg = f"{method}\n{path}\n{ts}\n".encode() + hashlib.sha256(body).hexdigest().encode()
    return hmac.new(SECRET.encode(), msg, hashlib.sha256).hexdigest()


def safe_extract(data: bytes, dest: Path) -> None:
    """Only regular files inside dest; sizes limited; the per-app source is replaced, Gradle's caches are kept."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > 4 * MAX_ZIP:
            raise ValueError("project too big")
        names = set()
        for i in infos:
            n = i.filename
            if i.is_dir():
                continue
            if n.startswith("/") or ".." in Path(n).parts or "\\" in n or not re.fullmatch(r"[\w./@+-]+", n):
                raise ValueError(f"bad path {n}")
            if (i.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("links not allowed")
            names.add(n)
        for sub in ("app/src", "gradle", "keys"):
            shutil.rmtree(dest / sub, ignore_errors=True)
        for i in infos:
            if i.is_dir():
                continue
            out = dest / i.filename
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(i))
            out.chmod(0o755 if i.filename == "gradlew" else 0o644)


def build(job: str) -> None:
    j = JOBS[job]
    work = HOME / "apps" / j["app"]
    logf = HOME / "jobs" / f"{job}.log"
    j.update(status="running", stage="compiling", started=time.time())
    env = {k: v for k, v in os.environ.items() if not re.search(r"(?i)secret|token|key|pass", k)}
    env["GRADLE_USER_HOME"] = str(HOME / "gradle")
    env["GRADLE_OPTS"] = "-Dorg.gradle.daemon=false"
    try:
        with open(logf, "w") as lf:
            p = subprocess.run(["./gradlew", "--no-daemon", "--console=plain", "assembleRelease"], cwd=work, env=env,
                               stdout=lf, stderr=subprocess.STDOUT, timeout=TIMEOUT)
        apks = sorted((work / "app/build/outputs/apk/release").glob("*.apk")) if p.returncode == 0 else []
        if apks:
            shutil.copy(apks[0], HOME / "jobs" / f"{job}.apk")
            j.update(status="ok", stage="done")
        else:
            j.update(status="failed", stage="failed")
    except subprocess.TimeoutExpired:
        with open(logf, "a") as lf:
            lf.write("\nbuild timed out\n")
        j.update(status="failed", stage="timeout")
    except Exception as e:                       # noqa: BLE001
        with open(logf, "a") as lf:
            lf.write(f"\nbuilder error: {e}\n")
        j.update(status="failed", stage="error")
    j["ended"] = time.time()
    try:
        j["tail"] = logf.read_text(errors="replace")[-4000:]
    except OSError:
        j["tail"] = ""


def runner() -> None:
    while True:
        job = Q.get()
        try:
            build(job)
        finally:
            Q.task_done()
        now = time.time()
        for k, v in list(JOBS.items()):
            if now - v.get("ended", now) > KEEP_JOBS_S:
                for ext in (".log", ".apk"):
                    (HOME / "jobs" / f"{k}{ext}").unlink(missing_ok=True)
                JOBS.pop(k, None)


class H(BaseHTTPRequestHandler):
    server_version = "HoolaBuild/1"

    def _ok(self, body: bytes) -> bool:
        ts = self.headers.get("X-Hoola-Time", "")
        try:
            fresh = abs(time.time() - int(ts)) < 300
        except ValueError:
            fresh = False
        good = hmac.compare_digest(self.headers.get("X-Hoola-Sign", ""), sign(self.command, self.path, ts, body))
        if not (SECRET and fresh and good):
            self._send(401, b'{"error":"unauthorized"}')
            return False
        return True

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):            # noqa: N802 - quiet
        pass

    def do_POST(self):                            # noqa: N802
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_ZIP:
            return self._send(413, b'{"error":"too big"}')
        body = self.rfile.read(n)
        if not self._ok(body):
            return
        if u.path != "/build":
            return self._send(404, b"{}")
        app = (parse_qs(u.query).get("app") or [""])[0]
        if not re.fullmatch(r"[a-z0-9_-]{4,64}", app):
            return self._send(400, b'{"error":"bad app"}')
        work = HOME / "apps" / app
        work.mkdir(parents=True, exist_ok=True)
        try:
            with LOCK:
                safe_extract(body, work)
        except (ValueError, zipfile.BadZipFile) as e:
            return self._send(400, json.dumps({"error": str(e)}).encode())
        job = uuid.uuid4().hex[:16]
        JOBS[job] = {"app": app, "status": "queued", "stage": "queued", "queued": time.time(), "ahead": Q.qsize()}
        Q.put(job)
        self._send(200, json.dumps({"job": job, "ahead": Q.qsize() - 1}).encode())

    def do_GET(self):                             # noqa: N802
        if not self._ok(b""):
            return
        m = re.fullmatch(r"/jobs/([0-9a-f]{16})(/apk|/log)?", urlparse(self.path).path)
        if urlparse(self.path).path == "/health":
            return self._send(200, json.dumps({"ok": True, "queued": Q.qsize()}).encode())
        if not m or m.group(1) not in JOBS:
            return self._send(404, b"{}")
        job, what = m.group(1), m.group(2)
        if what == "/apk":
            f = HOME / "jobs" / f"{job}.apk"
            return self._send(200, f.read_bytes(), "application/vnd.android.package-archive") if f.exists() else self._send(404, b"{}")
        if what == "/log":
            f = HOME / "jobs" / f"{job}.log"
            return self._send(200, f.read_bytes() if f.exists() else b"", "text/plain")
        j = {k: v for k, v in JOBS[job].items() if k != "tail"}
        self._send(200, json.dumps(j).encode())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8090)
    a = ap.parse_args()
    if len(SECRET) < 24:
        raise SystemExit("set HOOLA_BUILD_SECRET (24+ characters, the same as APP_BUILD_SECRET on the Hoola server)")
    (HOME / "jobs").mkdir(parents=True, exist_ok=True)
    (HOME / "apps").mkdir(parents=True, exist_ok=True)
    threading.Thread(target=runner, daemon=True).start()
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()


if __name__ == "__main__":
    main()
