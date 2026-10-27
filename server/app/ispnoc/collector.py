#!/usr/bin/env python3
"""Hoola NOC collector: a small script SHE runs on HER own network (POP / office PC / Linux box / FNW AI Node), never on the
Hoola server. Standard library only (Python 3.9+), plus the system `ssh` client if she wants read-only command pulls.

What it does
  * Listens for syslog from her OLTs / switches (UDP, default port 5514; point the OLT's syslog server at this machine).
  * Every N minutes runs ONLY read-only commands she lists ("show ...", "display ...") on her OLTs over SSH with HER key
    (BatchMode: key login only, no passwords typed or stored here; the key never leaves this machine).
  * Pushes the lines to Hoola, every request signed with HMAC-SHA256 (method, path, time, sha256(body)) using the secret
    the Hoola app showed her once.
  * Changes on live equipment: OFF unless `allow_changes` is true in this config AND she allowed this collector in the app.
    Then it fetches only jobs she approved with a tap, checks each job's own signature, refuses any line with password /
    erase / reload / firmware / copy words, runs exactly those lines and reports the output.

Config (JSON):
  {"server": "https://your-hoola-host", "collector_id": "ncol_...",
   "olts": [{"name": "OLT-AKOT-1", "ip": "10.10.1.2", "ssh": "admin@10.10.1.2", "ssh_key": "/home/noc/.ssh/olt_ed25519",
             "read_commands": ["show onu optical-info all"], "every_min": 15}],
   "syslog_port": 5514, "push_every_s": 30, "allow_changes": false}
Secret: environment variable HOOLA_COLLECTOR_SECRET (not in the file).

  HOOLA_COLLECTOR_SECRET=... python3 collector.py --config noc.json
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

VERSION = "1.0"
READ_ONLY = re.compile(r"^\s*(show|display|get|ping|traceroute)\b", re.I)
FORBIDDEN = re.compile(r"(?i)\b(password|passwd|username|enable secret|community|erase|format|delete|reload|reboot system|"
                       r"write erase|factory|reset saved|upgrade|load|copy)\b")
FORBIDDEN_OK_LINE = re.compile(r"(?i)^\s*(onu reboot \d+|ont reset \d+ \d+|reboot)\s*$")
MAX_LINES = 5000


def sign(secret: str, method: str, path: str, ts: str, body: bytes, nonce: str = "") -> str:
    msg = f"{method.upper()}\n{path}\n{ts}\n{nonce}\n".encode() + hashlib.sha256(body or b"").hexdigest().encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def job_sig(secret: str, job_id: str, hash_: str, commands: list) -> str:
    blob = json.dumps(commands, ensure_ascii=False, default=str)
    return hmac.new(secret.encode(), f"{job_id}|{hash_}|{blob}".encode(), hashlib.sha256).hexdigest()


def verify_job(secret: str, job: dict) -> str:
    """'' when the job may run, else the reason it must not."""
    cmds = job.get("commands") or []
    if not isinstance(cmds, list) or not cmds:
        return "no commands"
    want = job_sig(secret, str(job.get("id", "")), str(job.get("hash", "")), cmds)
    if not hmac.compare_digest(want, str(job.get("sig", ""))):
        return "bad job signature"
    for c in cmds + list(job.get("rollback") or []):
        if FORBIDDEN.search(str(c)) and not FORBIDDEN_OK_LINE.match(str(c)):
            return f"forbidden line: {str(c)[:60]}"
    return ""


def headers(secret: str, cid: str, method: str, path: str, body: bytes) -> dict:
    ts = str(int(time.time()))
    nonce = os.urandom(12).hex()
    return {"X-Hoola-Collector": cid, "X-Hoola-Ts": ts, "X-Hoola-Nonce": nonce, "X-Hoola-Sig": sign(secret, method, path, ts, body, nonce),
            "Content-Type": "application/json", "User-Agent": f"HoolaNocCollector/{VERSION}"}


class Collector:
    def __init__(self, cfg: dict, secret: str, transport=None):
        self.cfg = cfg
        self.secret = secret
        self.cid = cfg["collector_id"]
        self.server = cfg["server"].rstrip("/")
        self.buf: list[tuple[str, str]] = []              # (olt name, line)
        self.lock = threading.Lock()
        self.by_ip = {o.get("ip"): o.get("name", "") for o in cfg.get("olts", []) if o.get("ip")}
        self.last_pull: dict[str, float] = {}
        self.transport = transport or self._http

    # ---- HTTP
    def _http(self, method: str, path: str, body: bytes, hdrs: dict) -> tuple[int, dict]:
        req = urllib.request.Request(self.server + path, data=body if method != "GET" else None, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, {}
        except (urllib.error.URLError, OSError, ValueError):
            return 0, {}

    def call(self, method: str, path: str, data: dict | None = None) -> tuple[int, dict]:
        body = b"" if method == "GET" else json.dumps(data or {}).encode()
        return self.transport(method, path, body, headers(self.secret, self.cid, method, path, body))

    # ---- syslog in
    def syslog(self, port: int) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", port))
        while True:
            data, (ip, _p) = sock.recvfrom(8192)
            name = self.by_ip.get(ip)
            if name is None:
                continue                                  # only her listed devices
            self.add(name, data.decode("utf-8", errors="replace").strip())

    def add(self, olt: str, line: str) -> None:
        with self.lock:
            if len(self.buf) < 50_000:
                self.buf.append((olt, line[:600]))

    # ---- read-only pulls
    def pull(self) -> list[dict]:
        out = []
        for o in self.cfg.get("olts", []):
            every = max(5, int(o.get("every_min", 15))) * 60
            if time.time() - self.last_pull.get(o["name"], 0) < every or not o.get("ssh"):
                continue
            self.last_pull[o["name"]] = time.time()
            for cmd in o.get("read_commands", [])[:10]:
                if not READ_ONLY.match(cmd):
                    print(f"skip (not read-only): {cmd}", file=sys.stderr)
                    continue
                text = self.ssh(o, [cmd])
                if text:
                    out.append({"olt": o["name"], "command": cmd, "text": text[:500_000]})
        return out

    def ssh(self, o: dict, lines: list[str], timeout: int = 60) -> str:
        args = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=yes"]
        if o.get("ssh_key"):
            args += ["-i", os.path.expanduser(o["ssh_key"])]
        args.append(o["ssh"])
        try:
            p = subprocess.run(args, input="\n".join(lines + ["exit"]) + "\n", capture_output=True, text=True, timeout=timeout)
            return (p.stdout or "") + (("\n" + p.stderr) if p.returncode else "")
        except (OSError, subprocess.TimeoutExpired) as e:
            return f"ssh failed: {e}"

    # ---- push + jobs
    def push_once(self) -> dict:
        with self.lock:
            items, self.buf = self.buf[:MAX_LINES], self.buf[MAX_LINES:]
        batches: dict[str, list[str]] = {}
        for olt, line in items:
            batches.setdefault(olt, []).append(line)
        body = {"info": {"version": VERSION, "olts": ",".join(self.by_ip.values()), "host": socket.gethostname()},
                "batches": [{"olt": k, "lines": v, "source": "syslog"} for k, v in batches.items()], "outputs": self.pull()}
        code, res = self.call("POST", "/api/ispnoc/collector/push", body)
        if code != 200:
            with self.lock:
                self.buf = items + self.buf                # keep for the next try
        return res

    def jobs_once(self) -> int:
        if not self.cfg.get("allow_changes"):
            return 0
        code, res = self.call("GET", "/api/ispnoc/collector/jobs")
        if code != 200:
            return 0
        ran = 0
        for job in res.get("jobs", []):
            why = verify_job(self.secret, job)
            olt = next((o for o in self.cfg.get("olts", []) if o.get("name") == job.get("olt") or o.get("ip") == job.get("ip")), None)
            if not why and (olt is None or not olt.get("ssh")):
                why = "this collector has no SSH entry for that OLT"
            if why:
                self.call("POST", f"/api/ispnoc/collector/jobs/{job.get('id')}/result", {"ok": False, "output": f"not run: {why}"})
                continue
            out = self.ssh(olt, list(job["commands"]))
            ok = "ssh failed" not in out and not re.search(r"(?i)\b(error|invalid|unknown command|%\s*unrecognized)\b", out)
            self.call("POST", f"/api/ispnoc/collector/jobs/{job['id']}/result", {"ok": ok, "output": out[-4000:]})
            ran += 1
        return ran

    def run(self) -> None:
        port = int(self.cfg.get("syslog_port", 5514))
        threading.Thread(target=self.syslog, args=(port,), daemon=True).start()
        every = max(10, int(self.cfg.get("push_every_s", 30)))
        while True:
            try:
                self.push_once()
                self.jobs_once()
            except Exception as e:                       # never die: the NOC needs it running
                print(f"collector error: {e}", file=sys.stderr)
            time.sleep(every)


def main() -> None:
    ap = argparse.ArgumentParser(description="Hoola NOC collector (runs on your own network)")
    ap.add_argument("--config", required=True)
    ap.add_argument("--once", action="store_true", help="push what is buffered + pull once, then exit")
    a = ap.parse_args()
    secret = os.environ.get("HOOLA_COLLECTOR_SECRET", "")
    if not secret:
        sys.exit("Set HOOLA_COLLECTOR_SECRET (the secret the Hoola app showed when you made this collector).")
    with open(a.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    if any(re.search(r"(?i)pass", k) for o in cfg.get("olts", []) for k in o):
        sys.exit("Do not put passwords in the config: use an SSH key (ssh_key).")
    c = Collector(cfg, secret)
    if a.once:
        print(json.dumps(c.push_once()))
        print(f"jobs run: {c.jobs_once()}")
        return
    c.run()


if __name__ == "__main__":
    main()
