#!/usr/bin/env python3
"""Hoola log collector: runs on HER server (not on Hoola's), READ-ONLY, python3 stdlib only.

What it does every run (cron, e.g. every 5 minutes):
  1. reads only the NEW lines of the log files you list (remembers where it stopped in a small state file),
     optionally `journalctl -u <unit>` for systemd units and `pm2` log files,
  2. keeps only error-ish lines (+ a few lines of context for stack traces), masks secrets / long numbers on THIS machine,
  3. reads disk use (df) and load average,
  4. sends one signed batch (HMAC-SHA256 with your collector secret) to Hoola over HTTPS.
It never runs commands sent by Hoola, never writes anywhere except its own state file, never opens a port.

Setup:
  export HOOLA_URL=https://<your hoola server>  HOOLA_COLLECTOR=<id from the app>  HOOLA_SECRET=<secret shown once>
  python3 hoola_log_agent.py --files /var/log/nginx/error.log ~/.pm2/logs/app-error.log --units myapp --once
  cron:  */5 * * * * HOOLA_URL=... HOOLA_COLLECTOR=... HOOLA_SECRET=... /usr/bin/python3 /opt/hoola/hoola_log_agent.py --files ... --once
  (put the variables in a root-only file, e.g. /etc/hoola-agent.env, chmod 600)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

MAX_BATCH = 400_000
ERR = re.compile(r"(\b(error|err|crit|critical|fatal|emerg|alert|panic|exception|traceback|killed process|oom|segfault|refused|denied|"
                 r"timed out|timeout|no space left|failed|errored|unhandled)\b|\" 5\d\d )", re.I)
CONT = re.compile(r"^(\s+(File \"|at )|Caused by:|\s{2,}\S|[A-Za-z_.]+(Error|Exception):)")
MASKS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[private key hataya]"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16})\b"), "[key hataya]"),
    (re.compile(r"\beyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{6,}\b"), "[jwt hataya]"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[\w.~+/=-]{16,}"), r"\1 [hataya]"),
    (re.compile(r"(?i)(\w+://[^:/\s@]+:)([^@\s]+)@"), r"\1[hataya]@"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)(\s*[=:]\s*)([^\s\"',;&]{3,})"), r"\1\2[hataya]"),
    (re.compile(r"\b\d{12,19}\b"), "[number hataya]"),
]


def mask(s: str) -> str:
    for rx, rep in MASKS:
        s = rx.sub(rep, s)
    return s


def load_state(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(path: str, st: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, path)


def new_lines(path: str, st: dict) -> list[str]:
    try:
        ino = os.stat(path).st_ino
        size = os.path.getsize(path)
    except OSError:
        return []
    key = os.path.abspath(path)
    prev = st.get(key, {})
    pos = prev.get("pos", max(0, size - 200_000)) if prev.get("ino") == ino else max(0, size - 200_000)
    if pos > size:
        pos = 0                                           # rotated / truncated
    with open(path, "rb") as f:
        f.seek(pos)
        data = f.read(5_000_000)
        st[key] = {"ino": ino, "pos": pos + len(data)}
    return data.decode("utf-8", "replace").splitlines()


def journal(unit: str, st: dict) -> list[str]:
    if not shutil.which("journalctl"):
        return []
    since = st.get("journal:" + unit, "-15min")
    try:
        out = subprocess.run(["journalctl", "-u", unit, "--since", since, "-o", "short-iso", "--no-pager", "-q"],
                             capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    st["journal:" + unit] = time.strftime("%Y-%m-%d %H:%M:%S")
    return out.splitlines()


def pick(lines: list[str]) -> list[str]:
    out, keep = [], 0
    for x in lines:
        if ERR.search(x):
            out.append(mask(x[:2000]))
            keep = 40
        elif keep and (CONT.match(x) or x.startswith((" ", "\t"))):
            out.append(mask(x[:2000]))
            keep -= 1
        else:
            keep = 0
    return out


def disk() -> list[dict]:
    rows = []
    for m in ("/", "/var", "/home", "/srv", "/data"):
        if os.path.ismount(m):
            u = shutil.disk_usage(m)
            rows.append({"mount": m, "used_pct": round(100 * u.used / u.total, 1), "free_gb": round(u.free / 1e9, 1)})
    return rows


def send(url: str, cid: str, secret: str, body: dict) -> int:
    raw = json.dumps(body).encode()
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), f"{cid}\n{ts}\n{hashlib.sha256(raw).hexdigest()}".encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(f"{url.rstrip('/')}/api/devops/collect/{cid}", data=raw, method="POST",
                                 headers={"Content-Type": "application/json", "X-Hoola-Time": ts, "X-Hoola-Sign": sig,
                                          "User-Agent": "hoola-log-agent/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def main() -> int:
    ap = argparse.ArgumentParser(description="Hoola read-only log collector")
    ap.add_argument("--files", nargs="*", default=[], help="log files / globs (e.g. ~/.pm2/logs/*-error.log)")
    ap.add_argument("--units", nargs="*", default=[], help="systemd units for journalctl")
    ap.add_argument("--source", default=os.uname().nodename)
    ap.add_argument("--state", default=os.path.expanduser("~/.hoola_agent_state.json"))
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--every", type=int, default=300)
    a = ap.parse_args()
    url, cid, secret = os.environ.get("HOOLA_URL", ""), os.environ.get("HOOLA_COLLECTOR", ""), os.environ.get("HOOLA_SECRET", "")
    if not (url.startswith("https://") and cid and secret):
        print("HOOLA_URL (https), HOOLA_COLLECTOR and HOOLA_SECRET are needed", file=sys.stderr)
        return 2
    while True:
        st = load_state(a.state)
        lines: list[str] = []
        for pat in a.files:
            for p in sorted(glob.glob(os.path.expanduser(pat))):
                lines += pick(new_lines(p, st))
        for u in a.units:
            lines += pick(journal(u, st))
        body = {"source": a.source[:120], "host": os.uname().nodename[:120], "lines": [], "disk": disk(),
                "load": dict(zip(("1m", "5m", "15m"), os.getloadavg()))}
        size = 0
        for x in lines[-5000:]:
            size += len(x)
            if size > MAX_BATCH:
                break
            body["lines"].append(x)
        try:
            send(url, cid, secret, body)
            save_state(a.state, st)
        except Exception as e:                                # keep the old offsets; next run sends again
            print(f"send failed: {e}", file=sys.stderr)
        if a.once:
            return 0
        time.sleep(max(60, a.every))


if __name__ == "__main__":
    sys.exit(main())
