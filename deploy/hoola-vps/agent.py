#!/usr/bin/env python3
"""Hoola Code server helper (v0.941). Runs on HER server as the unprivileged `hoola` user.

It opens an OUTBOUND long-poll to Hoola and asks for work; Hoola never dials in, so no port is opened and no SSH key
lives here. It runs only commands Hoola marks approved (she tapped them, or they are look-only / trusted), and it
refuses the never-list ITSELF — so the refusal holds even if Hoola's own server were ever broken into.

Standard library only (urllib, subprocess, json). Config at /etc/hoola-agent/config.json: {base, token, server_id}.
Admin commands run with `sudo -n`; that works only for the exact commands granted on THIS server with
`sudo hoola-agent allow "<command>"`, which edits a narrow sudoers drop-in. Nothing else ever gets root.
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

CONFIG = "/etc/hoola-agent/config.json"
LOG = "/var/log/hoola-agent.log"
AGENT_VER = "1.1.0"

# The never-list — refused here no matter what Hoola sends. Mirrors the server; the server is not trusted to be the
# only guard.
REFUSE = [
    (r"\brm\s+-rf?\s+(/|~|\$HOME|\*)", "deletes a whole folder tree"),
    (r"\brm\b[^\n|;&]*\s-[a-z]*r[a-z]*f", "deletes a whole folder tree"),
    (r"\b(mkfs|fdisk|parted|wipefs)\b|>\s*/dev/sd", "wipes a disk"),
    (r"\bdd\b[^\n]*of=/dev/", "writes raw to a disk"),
    (r"\b(passwd|chpasswd|useradd|userdel|usermod|adduser|deluser|groupadd)\b", "changes a user or password"),
    (r"\bsshd?_config\b|/\.ssh|\bauthorized_keys\b|\bssh-keygen\b", "changes SSH or its keys"),
    (r"\b(ufw|iptables|nft|firewall-cmd)\b", "opens a firewall port"),
    (r"\b(curl|wget|fetch)\b[^\n]*\|[^\n]*\b(ba)?sh\b", "downloads and runs an outside script"),
    (r"(^|[\s/])(\.env(\.[\w-]+)?|id_rsa|id_ed25519|.*\.pem|.*\.key|credentials|secrets?\.(json|ya?ml|txt))(\s|$|['\"])",
     "reads a secret file"),
    (r"\bsudo\s+(su|-i|-s|bash|sh)\b", "gives itself a root shell"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "shuts the server down"),
]
REFUSE = [(re.compile(p, re.I), why) for p, why in REFUSE]

# 1.1.0: the access rules she set in Hoola, sent on every check-in and enforced HERE too (they used to be sent and
# ignored): "look" runs only commands that read; folders bound where "look" / "trust" may work; an admin command runs
# only if she ticked that exact command; a command never runs past her time limit.
READS = re.compile(
    r"^\s*(ls|cat|head|tail|less|wc|grep|rg|find|stat|file|df|du|free|uptime|uname|hostname|whoami|id|date|env|printenv|"
    r"ps|top|htop|pm2\s+(list|status|logs|show|describe|info|jlist|prettylist)|systemctl\s+(status|show|is-active|list-units)|"
    r"journalctl|docker\s+(ps|logs|inspect|images|stats)|git\s+(status|log|diff|show|branch|remote|rev-parse|config\s+--get)|"
    r"node\s+--version|npm\s+(ls|list|--version|run\s+(lint|typecheck|test))|python3?\s+(-m\s+pytest|--version)|"
    r"pip\s+(list|show|freeze)|cu?rl\s+-s[^|]*localhost|which|type|tree|echo)\b", re.I)
CONF = {"access": "ask", "folders": [], "admin_cmds": [], "cmd_timeout_s": 900}


def _program(cmd):
    """Same key as Hoola's server: the first two words, lower case (an admin grant is per program, not per argument)."""
    parts = re.findall(r"[\w./-]+", (cmd or "").strip().lower())
    return " ".join(parts[:2]) if parts else (cmd or "").strip().lower()[:40]


def _inside(folder, folders):
    f = os.path.realpath(folder).rstrip("/")
    for a in folders or []:
        a = os.path.realpath(_expand(a)).rstrip("/")
        if a and (f == a or f.startswith(a + "/")):
            return True
    return False


def not_allowed(job, folder):
    """The reason her own rules forbid this job on this server, or '' (checked here even if Hoola's server says yes)."""
    cmd, access = (job.get("cmd") or "").strip(), str(CONF.get("access") or "ask")
    if access == "look" and (not READS.search(cmd) or re.search(r"[;&`>]|\$\(", cmd)):
        return "your server is set to look only, and this command changes something"
    folders = CONF.get("folders") or []
    if access in ("look", "trust") and folders and not _inside(folder, folders):
        return "it is outside the folders you allowed"
    if job.get("admin") and _program(cmd) not in [_program(str(x)) for x in (CONF.get("admin_cmds") or [])]:
        return "it needs admin rights and you did not tick this command"
    return ""


def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def cfg():
    with open(CONFIG) as f:
        return json.load(f)


def refused(cmd):
    for pat, why in REFUSE:
        if pat.search(cmd or ""):
            return why
    return ""


def facts():
    out = {"agent_ver": AGENT_VER, "os": _os_name()}
    try:
        out["cpus"] = os.cpu_count() or 0
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    out["mem_mb"] = int(line.split()[1]) // 1024
                    break
    except OSError:
        pass
    try:
        st = os.statvfs("/")
        out["disk_free_gb"] = (st.f_bavail * st.f_frsize) // (1024 ** 3)
    except OSError:
        pass
    return out


def _os_name():
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')[:60]
    except OSError:
        pass
    return "Linux"


def _post(base, path, token, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(base.rstrip("/") + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode() or "{}")


def _home(user="hoola"):
    try:
        import pwd
        return pwd.getpwnam(user).pw_dir
    except Exception:
        return "/home/hoola"


def _expand(folder):
    f = (folder or "~").replace("$HOME", _home()).replace("~", _home())
    return f if os.path.isabs(f) else os.path.join(_home(), f.lstrip("./"))


def run_job(job):
    cmd = job.get("cmd") or ""
    why = refused(cmd)
    if why:
        log("REFUSED (%s): %s" % (why, cmd))
        return 126, "Refused by your server: it %s." % why
    folder = _expand(job.get("folder") or "~")
    if not os.path.isdir(folder):
        return 127, "Folder not found: %s" % folder
    rule = not_allowed(job, folder)
    if rule:
        log("REFUSED (%s): %s" % (rule, cmd))
        return 126, "Refused by your server: %s." % rule
    limit = max(10, min(int(CONF.get("cmd_timeout_s") or 900), 7200))
    full = ("sudo -n " + cmd) if job.get("admin") else cmd
    log("RUN [%s] %s" % (folder, full))
    try:
        p = subprocess.run(["/bin/bash", "-lc", full], cwd=folder, capture_output=True, text=True, timeout=limit,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        return p.returncode, out[-200000:]
    except subprocess.TimeoutExpired:
        return 124, "The command ran past the time limit and was stopped."
    except Exception as e:  # noqa: BLE001
        return 1, "Could not run it: %s" % e


def teardown():
    """Remove the helper, its config, its sudoers drop-in and the hoola user. Needs the uninstaller (root)."""
    log("Removing the helper on request.")
    os.system("/usr/local/bin/hoola-agent remove --quiet >/dev/null 2>&1 &")


def loop():
    c = cfg()
    base, token = c["base"], c["token"]
    poll = 20
    while True:
        try:
            r = _post(base, "/api/devsahayak/vps/check-in", token, {"facts": facts()})
            if r.get("remove"):
                teardown()
                return
            CONF.update({k: v for k, v in (r.get("config") or {}).items() if k in CONF})
            poll = int(r.get("config", {}).get("poll_s") or poll)
            for job in r.get("jobs", []):
                code, out = run_job(job)
                try:
                    _post(base, "/api/devsahayak/vps/report", token,
                          {"cmd_id": job.get("id"), "exit_code": code, "output": out})
                except urllib.error.URLError as e:
                    log("report failed: %s" % e)
        except urllib.error.HTTPError as e:
            log("check-in HTTP %s" % e.code)
            if e.code in (401, 403, 404):
                teardown()
                return
        except (urllib.error.URLError, socket.timeout, OSError) as e:
            log("offline: %s" % e)
        time.sleep(max(5, poll))


if __name__ == "__main__":
    if "--enroll" in sys.argv:
        # called once by the installer: agent.py --enroll BASE CODE  -> writes config.json, prints ok / err
        i = sys.argv.index("--enroll")
        base, code = sys.argv[i + 1], sys.argv[i + 2]
        try:
            req = urllib.request.Request(base.rstrip("/") + "/api/devsahayak/vps/enroll", method="POST",
                                         data=json.dumps({"code": code, "facts": facts()}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                got = json.loads(r.read().decode())
            os.makedirs("/etc/hoola-agent", exist_ok=True)
            with open(CONFIG, "w") as f:
                json.dump({"base": base, "token": got["token"], "server_id": got["server_id"]}, f)
            os.chmod(CONFIG, 0o600)
            print("ok")
        except Exception as e:  # noqa: BLE001
            print("err: %s" % e)
            sys.exit(1)
    else:
        loop()
