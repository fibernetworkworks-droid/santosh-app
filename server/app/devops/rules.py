"""DevOps Sahayak rules by code (no model needed): CI failure pattern library, log parsing + error clustering, secret masking,
script safety check, DORA metrics, checklists and runbooks.

Research behind it (23 Oct 2026):
- GitHub REST API: workflow runs / jobs / job logs (302 to a 1-minute download link), re-run failed jobs, workflow_dispatch
  (`return_run_details` returns 200 + workflow_run_id / run_url / html_url since 19 Feb 2026; Actions: write), pending deployments
  review for environments with required reviewers - docs.github.com/en/rest/actions/{workflows,workflow-runs,workflow-jobs},
  github.blog/changelog/2026-02-19-workflow-dispatch-api-now-returns-run-ids.
- Flaky builds: a job that changes outcome on rerun of the SAME commit; 67.7% of rerun builds on GitHub Actions were flaky;
  causes: flaky tests 65%, network 15.8%, dependency resolution 6.3%, environment 4.7%, API down 1.2%, memory 0.5%
  (arXiv 2602.02307, Feb 2026, "Understanding and Detecting Flaky Builds in GitHub Actions").
- DORA five metrics: deployment frequency, lead time for changes, change failure rate, failed deployment recovery time,
  rework rate (= unplanned deploys / all deploys) - cd.foundation/blog/2025/10/16/dora-5-metrics.
- CERT-In Directions 28 Apr 2022: ICT logs kept 180 days within India, clocks synced to NTP (helpdesk module has the 6-hour
  incident clock; DevOps points there).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

SOURCES = [
    ("GitHub REST API: workflow runs, jobs, logs, re-run, pending deployments", "https://docs.github.com/en/rest/actions/workflow-runs", "2026-10-23"),
    ("GitHub REST API: workflow dispatch (200 + workflow_run_id with return_run_details)", "https://docs.github.com/en/rest/actions/workflows", "2026-10-23"),
    ("GitHub changelog: workflow dispatch API now returns run IDs", "https://github.blog/changelog/2026-02-19-workflow-dispatch-api-now-returns-run-ids", "2026-02-19"),
    ("Understanding and Detecting Flaky Builds in GitHub Actions (arXiv 2602.02307)", "https://arxiv.org/html/2602.02307v1", "2026-02"),
    ("CD Foundation: DORA's five software delivery metrics", "https://cd.foundation/blog/2025/10/16/dora-5-metrics/", "2025-10-16"),
    ("CERT-In Directions 28 Apr 2022 (180-day logs, NTP)", "https://www.cert-in.org.in/Directions70B.jsp", "2022-04-28"),
]

# ---------------------------------------------------------------- masking (logs are DATA; secrets never stored)
_MASKS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[private key hataya]"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"), "[token hataya]"),
    (re.compile(r"\b(sk-(ant-)?[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{30,}|AKIA[0-9A-Z]{16}|xox[abpr]-[A-Za-z0-9-]{10,}|rzp_(live|test)_[A-Za-z0-9]{8,})\b"), "[key hataya]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}\b"), "[jwt hataya]"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{16,}"), r"\1 [hataya]"),
    (re.compile(r"(?i)(\b[a-z][a-z0-9+.-]{1,15}://[^:/\s@]+:)([^@\s]+)(@)"), r"\1[hataya]\3"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)(\s*[=:]\s*|\"\s*:\s*\")([^\s\"',;&]{3,})"),
     r"\1\2[hataya]"),
    (re.compile(r"\b\d{12,19}\b"), "[number hataya]"),
]


def mask(text: str) -> str:
    out = text or ""
    for rx, rep in _MASKS:
        out = rx.sub(rep, out)
    try:
        from ..scrub import text as scrub_text
        out = scrub_text(out)
    except Exception:
        pass
    return out


SECRET_SHAPE = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-ant-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|"
                          r"-----BEGIN [A-Z ]*PRIVATE KEY-----)")


def has_secret(text: str) -> bool:
    return bool(SECRET_SHAPE.search(text or ""))


# ---------------------------------------------------------------- CI failure library
# id: (label, regexes, why, fix, flaky_likely). Checked in this order; the first strong match wins (later ones become "also").
CI_PATTERNS: list[tuple[str, str, list[str], str, str, bool]] = [
    ("disk_full", "Disk bhar gaya", [r"No space left on device", r"\bENOSPC\b", r"not enough space on the disk"],
     "Runner ki disk bhar gayi (bade Docker images / caches / build output).",
     "Workflow ke shuru mein purane Docker images / tool caches hatao (docker system prune -af), artifacts chhote karo, ya bada runner lo.", False),
    ("oom", "Memory khatam (OOM)", [r"JavaScript heap out of memory", r"java\.lang\.OutOfMemoryError", r"\bMemoryError\b",
                                    r"exit code 137", r"Killed\s+signal terminated program", r"Gradle build daemon disappeared unexpectedly",
                                    r"The runner has received a shutdown signal", r"Metaspace"],
     "Build ko runner ki RAM kam padi (Node / Gradle / Java ne zyada memory maangi).",
     "Node: NODE_OPTIONS=--max-old-space-size=4096; Gradle: org.gradle.jvmargs=-Xmx3g aur workers kam; tests ko parallel kam karo; ya bada runner.", False),
    ("timeout", "Samay khatam", [r"has exceeded the maximum execution time", r"The job running on runner .* has exceeded",
                                 r"timed out after \d+", r"Timeout of \d+ms exceeded", r"context deadline exceeded", r"timeout-minutes"],
     "Job ya test tay samay se lamba chala (atka hua test, dheema network, ya bahut bada kaam).",
     "Atke test ka naam dekho (aakhri chalne wali line), test ka timeout lagao, cache use karo; timeout-minutes zaroorat se zyada mat badhao.", True),
    ("rate_limit", "Rate limit", [r"API rate limit exceeded", r"429 Too Many Requests", r"toomanyrequests", r"secondary rate limit"],
     "Kisi service (GitHub API / Docker Hub / npm) ne zyada requests par roka.",
     "Docker Hub mein login karke pull karo (limit badhti hai), cache use karo, GITHUB_TOKEN se API call karo; thodi der baad dobara chalao.", True),
    ("network", "Network ki dikkat", [r"\bECONNRESET\b", r"\bETIMEDOUT\b", r"\bEAI_AGAIN\b", r"Could not resolve host", r"Temporary failure in name resolution",
                                      r"Connection reset by peer", r"TLS handshake timeout", r"Read timed out", r"503 Service Unavailable",
                                      r"502 Bad Gateway", r"socket hang up", r"Connection timed out", r"unable to access 'https://"],
     "Download ya API call beech mein toot gaya (package registry / GitHub / bahar ki service).",
     "Aksar dobara chalane se theek; baar baar ho to retry lagao (npm ci --fetch-retries, pip --retries, Gradle --offline cache) aur dependency cache use karo.", True),
    ("secret_missing", "Secret / env missing", [r"Input required and not supplied", r"secret\s+\S+\s+(is\s+)?not\s+(set|found|defined)",
                                                r"environment variable\s+\S+\s+(is\s+)?(not set|missing|undefined)", r"Missing required (env|environment)",
                                                r"KeyError: '[A-Z_]{3,}'", r"must be set|is not set\b",
                                                r"Keystore file .* not found", r"keystore password was incorrect"],
     "Workflow ko koi secret / environment variable nahi mila (naam galat, environment ka secret, ya fork se PR jahan secrets nahi milte).",
     "Repo > Settings > Secrets and variables > Actions mein naam milaao (bade-chhote akshar), environment ka secret ho to job mein environment: likho. Secret ki value chat mein kabhi mat daalo.", False),
    ("auth", "Login / ijazat", [r"Bad credentials", r"401 Unauthorized", r"\b403 Forbidden\b", r"Resource not accessible by integration",
                                r"Permission to .* denied", r"denied: requested access to the resource is denied", r"authentication required",
                                r"Host key verification failed", r"Permission denied \(publickey"],
     "Token / key ke paas ye kaam karne ki ijazat nahi, ya token expire ho gaya.",
     "GITHUB_TOKEN ke liye workflow mein permissions: block (jaise contents: write / packages: write) do; deploy key / token naya banao; SSH host key known_hosts mein daalo.", False),
    ("lockfile", "Lockfile mel nahi khaata", [r"npm ci can only install packages when your package\.json and package-lock\.json",
                                             r"lockfile .* (out of date|needs to be updated)", r"--frozen-lockfile", r"poetry\.lock is not consistent",
                                             r"Your lockfile needs to be updated", r"pubspec\.lock .* out of date"],
     "package.json / pyproject badla par lockfile commit nahi hua.",
     "Laptop par npm install (ya poetry lock / pnpm install) chalao aur lockfile commit karo.", False),
    ("version", "Version mel nahi khaata", [r"The engine \"node\" is incompatible", r"Unsupported engine", r"requires Java \d+",
                                            r"Unsupported class file major version", r"Android Gradle plugin requires Java \d+",
                                            r"The current Dart SDK version is", r"requires Python\s*[<>=]", r"python_requires",
                                            r"node: bad option", r"Requires: Python"],
     "Runner par tool ka version project se alag hai (Node / Java / Dart / Python).",
     "setup-node / setup-java / setup-python / flutter-action mein wahi version likho jo project maangta hai (.nvmrc, java 17, pubspec environment).", False),
    ("dependency", "Dependency nahi mili", [r"\bERESOLVE\b", r"npm ERR! code E404", r"No matching distribution found", r"ResolutionImpossible",
                                           r"Could not resolve dependencies", r"Could not resolve [\w.\-]+:[\w.\-]+", r"Could not find [\w.\-]+:[\w.\-]+",
                                           r"version solving failed", r"ModuleNotFoundError", r"Cannot find module '", r"Duplicate class",
                                           r"error: package .* does not exist", r"Unable to find a matching variant",
                                           r"ImportError: cannot import name"],
     "Koi package / library nahi mili ya versions aapas mein takra rahe hain.",
     "Error mein package ka naam dekho: requirements / package.json / build.gradle mein sahi version pin karo; nayi library add hui to lockfile bhi commit karo.", False),
    ("lint", "Lint / format", [r"\d+ problems? \(\d+ errors?", r"\beslint\b.*error", r"would reformat", r"Found \d+ errors?\.", r"\bflake8\b",
                               r"\d+ issues? found", r"Code style issues found", r"lintVitalRelease", r"\bruff\b.*\berror", r"error • .* • \w+",
                               r"Lint found errors"],
     "Code style / lint ke niyam toote (build theek hai, par checker ne roka).",
     "Laptop par wahi lint chalao (npm run lint -- --fix / ruff --fix / dart fix --apply / black .) aur commit karo.", False),
    ("test_failure", "Test fail", [r"^FAILED \S+::\S+", r"=+ \d+ failed", r"Tests?:\s+\d+ failed", r"Test Suites: \d+ failed", r"--- FAIL: ",
                                   r"There were failing tests", r"AssertionError", r"\bexpect\(.*\)\.", r"Tests failed", r"\d+ tests? completed, \d+ failed",
                                   r"Some tests failed", r"FAIL\s+\S+\.(test|spec)\.", r"Expected: .*\n.*Actual:"],
     "Code build hua par kuch tests fail hue.",
     "Fail hone wale test ka naam aur pehli assert line dekho; laptop par sirf wahi test chalao. Agar wahi commit dobara chalane par paas ho jaye to test flaky hai.", True),
    ("compile", "Code compile nahi hua", [r"error TS\d+", r"SyntaxError", r"error: cannot find symbol", r"^e: (file://|/)\S+\.kt",
                                         r"Compilation failed", r"error\[E\d+\]", r"undefined reference to", r"\.dart:\d+:\d+: Error",
                                         r"error CS\d+", r"Build failed with an exception", r"cannot find package", r"IndentationError", r"NameError"],
     "Code mein syntax / type ki galti hai, isliye build nahi bana.",
     "Error wali file aur line kholo (log mein file:line hai), wahi theek karke commit karo; laptop par build chala ke dekho.", False),
    ("docker", "Docker build", [r"failed to solve", r"pull access denied", r"manifest unknown", r"COPY failed", r"failed to compute cache key",
                                r"executor failed running"],
     "Docker image banana fail hua (base image / COPY ka path / RUN ka command).",
     "Base image ka naam-tag check karo, COPY ka path build context ke andar ho, RUN wala command laptop par docker build se chala ke dekho.", False),
    ("permission", "File permission", [r"Permission denied", r"\bEACCES\b", r"Operation not permitted"],
     "Script ya file chalane ki ijazat nahi (aksar ./gradlew ya .sh executable nahi).",
     "git update-index --chmod=+x gradlew (ya script) karke commit karo; ya workflow mein chmod +x likho.", False),
    ("runner", "Runner nahi mila / ruk gaya", [r"No runner matching the specified labels", r"lost communication with the server",
                                              r"The operation was canceled", r"waiting for a runner"],
     "Job ko runner nahi mila ya runner beech mein band hua (self-hosted machine off / label galat).",
     "runs-on ka label dekho; self-hosted runner chalu hai? GitHub status bhi dekho. Dobara chalao.", True),
]
CI_LABEL = {p[0]: p[1] for p in CI_PATTERNS} | {"cancelled": "Rok diya gaya", "unknown": "Pehchaan nahi paya"}
_CI_RX = [(p[0], [re.compile(r, re.M | re.I if p[0] not in ("compile",) else re.M) for r in p[2]]) for p in CI_PATTERNS]
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z\s?")


def strip_ts(line: str) -> str:
    return _TS.sub("", line)


def classify_ci(text: str) -> dict[str, Any]:
    """Category of a failed CI log, with the evidence lines."""
    body = "\n".join(strip_ts(x) for x in (text or "").splitlines())
    hits = []
    for cid, rxs in _CI_RX:
        for rx in rxs:
            m = rx.search(body)
            if m:
                hits.append((cid, m))
                break
    if not hits:
        return {"category": "unknown", "label": CI_LABEL["unknown"], "evidence": [], "also": [], "flaky_likely": False,
                "why": "Log mein jaani-pehchaani galti nahi mili.", "fix": "Neeche di gayi error lines dekhiye; zaroorat ho to log ka hissa Hoola ko bhejiye."}
    # a 'Process completed with exit code' only test failure + network hit = network wins (flaky); otherwise order above wins
    cid, m = hits[0]
    p = next(x for x in CI_PATTERNS if x[0] == cid)
    line = _line_at(body, m.start())
    return {"category": cid, "label": p[1], "why": p[3], "fix": p[4], "flaky_likely": p[5],
            "evidence": [mask(line)[:300]], "also": [h[0] for h in hits[1:4]]}


def _line_at(body: str, pos: int) -> str:
    a = body.rfind("\n", 0, pos) + 1
    b = body.find("\n", pos)
    return body[a: b if b >= 0 else len(body)].strip()


_ERR_LINE = re.compile(r"(##\[error\]|\berror\b|\bERR!|\bFAILED\b|\bFAIL\b|Exception|Traceback|fatal:|^E\s{2,}|^e: )", re.I)


def error_lines(text: str, limit: int = 12) -> list[str]:
    """The lines that matter in a long CI log (masked): GitHub's ##[error] lines first, then other error lines near the end."""
    lines = [strip_ts(x).rstrip() for x in (text or "").splitlines()]
    gh = [x.replace("##[error]", "").strip() for x in lines if x.startswith("##[error]")]
    gh = [x for x in gh if not re.match(r"Process completed with exit code \d+\.?$", x)] or gh
    other = [x.strip() for x in lines if _ERR_LINE.search(x) and not x.startswith(("##[group]", "##[endgroup]", "##[error]"))]
    seen, out = set(), []
    for x in other[-limit:] + gh:
        k = x[:160]
        if x and k not in seen:
            seen.add(k)
            out.append(mask(x)[:300])
    return out[-limit:]


_TESTS = [
    re.compile(r"^FAILED (\S+::\S+)", re.M),                        # pytest
    re.compile(r"^--- FAIL: (\S+)", re.M),                          # go
    re.compile(r"^\s*● (.+?) › (.+)$", re.M),                        # jest
    re.compile(r"^(\S+ > \S+.*) FAILED$", re.M),                    # gradle
    re.compile(r"^\s*\d{2}:\d{2} \+\d+ -\d+: (.+) \[E\]$", re.M),     # flutter test
]


def failed_tests(text: str) -> list[str]:
    body = "\n".join(strip_ts(x) for x in (text or "").splitlines())
    out: list[str] = []
    for rx in _TESTS:
        for m in rx.finditer(body):
            name = " › ".join(g for g in m.groups() if g).strip()
            if name and name not in out:
                out.append(name[:280])
    return out[:40]


# ---------------------------------------------------------------- server logs: formats, entries, signatures
_NGINX_ERR = re.compile(r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} \[(\w+)\] \d+#\d+: (.*)$")
_NGINX_ACC = re.compile(r'^\S+ \S+ \S+ \[[^\]]+\] "(\w+) (\S+)[^"]*" (\d{3}) ')
_SYSTEMD = re.compile(r"^(\w{3} [ \d]\d \d{2}:\d{2}:\d{2}|\d{4}-\d{2}-\d{2}T\S+) \S+ ([\w@.\-]+)(\[\d+\])?: (.*)$")
_PM2 = re.compile(r"^(\d+\|[\w.\-]+\s*\||PM2\s+\|)\s*(.*)$")
_DOCKER = re.compile(r"^([\w.\-]+)\s+\|\s(.*)$")
_LEVEL = re.compile(r"\b(EMERG|ALERT|CRIT(ICAL)?|FATAL|ERROR|ERR|SEVERE|PANIC|WARN(ING)?)\b", re.I)
_TRACE_START = re.compile(r"^(Traceback \(most recent call last\):|Exception in thread|\w+(\.\w+)*(Exception|Error)\b.*|\s*at \S+\(.*\)$|panic: )")
_TRACE_CONT = re.compile(r"^(\s+File \"|\s+at |\s{2,}\S|Caused by:|\.\.\. \d+ more|goroutine \d+ )")
_PY_EXC = re.compile(r"^([A-Za-z_][\w.]*(Error|Exception|Exit|Interrupt|Warning)):\s?(.*)$")

LOG_PATTERNS: list[tuple[str, str, list[str], str, str, str]] = [
    # id, label, regexes, why, fix, runbook id
    ("upstream_down", "App band hai (nginx ko jawab nahi)", [r"connect\(\) failed \(111: Connection refused\) while connecting to upstream",
                                                           r"no live upstreams", r"\b502\b.*(Bad Gateway)?", r"upstream prematurely closed"],
     "nginx aage app tak pahunchna chahta hai par app chal nahi rahi / port par sun nahi rahi.",
     "pm2 status / systemctl status dekho; app ka port nginx ke proxy_pass se milao; app ke apne log ki pehli error dekho.", "app_down"),
    ("upstream_slow", "App dheemi (504 / timeout)", [r"upstream timed out", r"\b504\b", r"Gateway Time-?out"],
     "App ne nginx ke tay samay mein jawab nahi diya (dheemi query / atka kaam).",
     "Dheemi request dhoondho (access log mein URL), DB query / bahar ki API dekho; proxy_read_timeout tabhi badhao jab kaam sach mein lamba ho.", "slow_app"),
    ("db_down", "Database se connection nahi", [r"(ECONNREFUSED|Connection refused).*(5432|3306|27017|6379)", r"could not connect to server",
                                               r"SQLSTATE\[HY000\] \[2002\]", r"OperationalError", r"too many connections",
                                               r"MongoNetworkError", r"Redis connection .* failed", r"remaining connection slots are reserved"],
     "App database (Postgres / MySQL / Mongo / Redis) se jud nahi pa rahi ya connections khatam.",
     "Database service chalu hai? (systemctl status postgresql); connection pool chhota karo; password / host .env mein sahi hai?", "db_down"),
    ("oom_kill", "Memory khatam, process maara gaya", [r"Out of memory: Killed process", r"oom-kill", r"OOMKilled", r"JavaScript heap out of memory",
                                                     r"java\.lang\.OutOfMemoryError", r"\bMemoryError\b", r"Cannot allocate memory"],
     "Server ki RAM khatam hui, Linux ne process band kar diya.",
     "free -m aur pm2 monit se dekho kaun zyada memory le raha; swap jodo, pm2 max_memory_restart lagao, memory leak dhoondho.", "oom"),
    ("disk_full", "Disk bhar gayi", [r"No space left on device", r"\bENOSPC\b", r"disk full", r"Disk quota exceeded"],
     "Server ki disk bhar gayi (logs / backups / docker images).",
     "df -h aur du -sh /var/log/* dekho; logrotate lagao, purane backup / docker images hatao (dhyaan se).", "disk_full"),
    ("port_in_use", "Port pehle se laga hai", [r"EADDRINUSE", r"Address already in use", r"bind\(\) to \S+ failed \(98"],
     "Do process ek hi port lena chahte hain (purani copy chal rahi hai).",
     "sudo ss -ltnp | grep <port> se dekho kaun hai; purana process band karo, pm2 mein ek hi copy rakho.", "port_in_use"),
    ("crash_loop", "App baar baar restart", [r"restarting too often|too many unstable restarts", r"Start request repeated too quickly",
                                             r"exited with code [1-9]", r"Main process exited, code=exited, status=[1-9]", r"errored",
                                             r"Back-off restarting failed container", r"CrashLoopBackOff"],
     "App chalte hi band ho rahi hai; restart ka chakkar.",
     "Restart se pehle ki pehli error line dekho (yahi asli wajah hai); .env / config / migration check karo.", "crash_loop"),
    ("ssl", "SSL / certificate", [r"certificate (has )?expired", r"SSL_ERROR|ssl_error", r"SSL_do_handshake\(\) failed", r"unable to verify the first certificate",
                                  r"CERT_HAS_EXPIRED", r"self[- ]signed certificate"],
     "Certificate expire / galat hai ya chain poori nahi.",
     "certbot renew --dry-run chalao; nginx mein fullchain.pem use karo; system ki ghadi (NTP) sahi hai?", "ssl"),
    ("permission", "Permission", [r"Permission denied", r"\bEACCES\b", r"\(13: Permission denied\)"],
     "Process ko file / folder padhne-likhne ki ijazat nahi.",
     "ls -l se owner dekho; app jis user se chalti hai usko hi folder do (chown); 777 kabhi mat do.", "permission"),
    ("too_many_files", "Bahut saari files khuli", [r"Too many open files", r"\bEMFILE\b", r"worker_connections are not enough"],
     "Process ki open files / connections ki seema puri ho gayi.",
     "ulimit -n badhao (systemd: LimitNOFILE), nginx worker_connections badhao, connections band na hone wali jagah dhoondho.", "limits"),
    ("dns", "DNS / host nahi mila", [r"getaddrinfo (ENOTFOUND|EAI_AGAIN)", r"Name or service not known", r"Temporary failure in name resolution",
                                     r"could not resolve host"],
     "Server bahar ka host naam nahi dhoondh paya.",
     "/etc/resolv.conf aur internet dekho; host ka naam .env mein sahi hai?", "network"),
    ("timeout", "Bahar ki service ka timeout", [r"\bETIMEDOUT\b", r"timed out", r"Read timed out", r"deadline exceeded"],
     "Kisi bahar ki service / API ne samay par jawab nahi diya.",
     "Kaun si service hai dekho (URL / host), timeout + retry lagao, uska status page dekho.", "network"),
    ("auth", "Login / token fail", [r"jwt expired", r"invalid token", r"401 Unauthorized", r"authentication failed", r"Access denied for user"],
     "Kisi token / password ki jaanch fail hui (expire / galat / badla gaya).",
     "Token / password ki tarikh dekho; .env mein naya secret daalo (chat mein kabhi nahi) aur app restart karo.", "auth"),
    ("module", "Code / package nahi mila", [r"Cannot find module", r"ModuleNotFoundError", r"ImportError", r"ClassNotFoundException",
                                             r"undefined is not a function", r"is not defined"],
     "Deploy ke baad koi package / file nahi mili (install nahi hua ya galat build).",
     "Server par npm ci / pip install -r requirements.txt chalao, build folder poora upload hua? Pichhla version chal raha tha to rollback.", "bad_deploy"),
    ("segfault", "Process crash (segfault)", [r"segfault at", r"Segmentation fault", r"SIGSEGV", r"core dumped"],
     "Native code / library mein crash.",
     "Kis package ke update ke baad shuru hua dekho; pichhle version par wapas jao; core dump developer ko do.", "crash_loop"),
    ("exception", "Code mein error (exception)", [r"Traceback \(most recent call last\)", r"Unhandled(Promise)?Rejection", r"uncaughtException",
                                                 r"\w+Exception\b", r"\w+Error:", r"panic:"],
     "App ke code mein ek error aaya jo pakda nahi gaya.",
     "Stack trace ki sabse neeche wali apni file:line dekho (library ki nahi); developer ko yahi trace dijiye.", "exception"),
    ("http_5xx", "Server error (5xx)", [r'" 5\d\d '],
     "Requests par server 5xx de raha hai.", "Usi samay ka app log dekho; ek hi URL par ho to wahi route jaancho.", "slow_app"),
]
LOG_LABEL = {p[0]: p[1] for p in LOG_PATTERNS} | {"other": "Doosri error"}
_LOG_RX = [(p[0], [re.compile(r, re.I) for r in p[2]]) for p in LOG_PATTERNS]

RUNBOOKS: dict[str, dict[str, Any]] = {
    "app_down": {"title": "App band hai / 502", "steps": [
        "pm2 status (ya systemctl status <app>) - app online hai?", "pm2 logs <app> --lines 100 - band hone se pehle ki pehli error",
        "nginx proxy_pass ka port = app ka port? (ss -ltnp)", "App chalu karo: pm2 restart <app> (aapka kaam, Hoola server par kuch nahi chalata)",
        "Phir bhi band: pichhle deploy par rollback (DevOps > Deploy > Rollback card)"]},
    "slow_app": {"title": "App dheemi / 504", "steps": [
        "Access log mein dheemi URL dhoondho ($request_time agar log format mein ho)", "Usi samay DB par dheemi query (slow query log)",
        "Bahar ki API ka timeout kitna hai?", "CPU / RAM: top, free -m", "Kaam lamba hi hai to background job banao; proxy timeout sirf tab badhao"]},
    "db_down": {"title": "Database se connection nahi", "steps": [
        "systemctl status postgresql (ya mysql / redis)", "Disk bhar to nahi gayi? df -h", "Connections: max_connections vs app ka pool size",
        ".env mein host / port / user sahi? (password chat mein mat bhejo)", "Restart se pehle backup ki tarikh dekho"]},
    "oom": {"title": "Memory khatam (OOM)", "steps": [
        "dmesg -T | grep -i 'killed process' - kaun maara gaya", "free -m, pm2 monit", "Swap jodo (2-4 GB) agar nahi hai",
        "pm2: max_memory_restart: '500M' (ecosystem file)", "Memory leak: kis deploy ke baad shuru hua?"]},
    "disk_full": {"title": "Disk bhar gayi", "steps": [
        "df -h aur du -xh / --max-depth=2 | sort -h | tail", "Logs: logrotate lagao (CERT-In: logs 180 din rakhne hain, to compress karo, delete nahi)",
        "docker system df / purane images (dhyaan se)", "Purane backups kahin aur bhejo (off-server)", "85% par Hoola alert deta hai"]},
    "port_in_use": {"title": "Port pehle se laga", "steps": ["sudo ss -ltnp | grep :<port>", "Purani copy band karo", "pm2 delete <purana naam>", "Ek hi process rakho"]},
    "crash_loop": {"title": "Baar baar restart", "steps": [
        "Restart se pehle ki PEHLI error line (baaki uske nateeje hain)", ".env / config badla tha?", "Migration chali?", "Pichhla version theek tha to rollback"]},
    "ssl": {"title": "SSL / certificate", "steps": ["sudo certbot certificates", "sudo certbot renew --dry-run", "nginx: ssl_certificate = fullchain.pem",
                                                    "timedatectl - ghadi NTP se mili hai (CERT-In bhi kehta hai)"]},
    "permission": {"title": "Permission denied", "steps": ["ls -l <file>", "App kis user se chalti hai (ps -o user= -p <pid>)", "chown <user> <folder>; 777 kabhi nahi"]},
    "limits": {"title": "Too many open files", "steps": ["ulimit -n", "systemd unit: LimitNOFILE=65535", "nginx: worker_connections", "Connections band ho rahe hain? (leak)"]},
    "network": {"title": "Bahar ki service / DNS", "steps": ["dig <host> / curl -I https://<host>", "Uska status page", "Timeout + retry code mein", "Server ka DNS (/etc/resolv.conf)"]},
    "auth": {"title": "Token / login fail", "steps": ["Token ki expiry", "Naya secret .env mein (chat mein kabhi nahi)", "App restart", "Purana key rotate / revoke"]},
    "bad_deploy": {"title": "Deploy ke baad toot gaya", "steps": ["Kaunsa commit gaya (DevOps > Deploy)", "npm ci / pip install chala?", "Build folder poora?",
                                                                  "Rollback card bhejo aur us par aap tap karein"]},
    "exception": {"title": "Code ka exception", "steps": ["Stack trace ki apni file:line", "Kis request / input par aaya", "Developer ko trace + samay do", "Baar baar ho to us feature ko band karo (flag)"]},
}

_NORM = [
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<uuid>"),
    (re.compile(r"\b\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?\b"), "<time>"),
    (re.compile(r"\b\d{2}:\d{2}:\d{2}(\.\d+)?\b"), "<time>"),
    (re.compile(r"\b\d{1,3}(\.\d{1,3}){3}(:\d+)?\b"), "<ip>"),
    (re.compile(r"\b0x[0-9a-f]+\b", re.I), "<hex>"),
    (re.compile(r"\b[0-9a-f]{16,}\b", re.I), "<hex>"),
    (re.compile(r"(?<=[/=])[\w.%-]*\d[\w.%-]*"), "<id>"),
    (re.compile(r"\b\d+\b"), "<n>"),
    (re.compile(r"\s+"), " "),
]


def normalize(line: str) -> str:
    x = line.strip()
    x = re.sub(r"^(\S+\s+)?\[?\d{4}-\d{2}-\d{2}[T ][\d:.,]+\]?\s*(Z|[+-]\d{2}:?\d{2})?\s*", "", x)
    for rx, rep in _NORM:
        x = rx.sub(rep, x)
    return x[:240]


def signature(source: str, norm: str) -> str:
    return hashlib.sha256(f"{source}|{norm}".encode()).hexdigest()[:24]


def detect_format(lines: list[str]) -> str:
    score = {"nginx": 0, "systemd": 0, "pm2": 0, "docker": 0, "python": 0, "node": 0, "java": 0}
    for x in lines[:400]:
        if _NGINX_ERR.match(x) or _NGINX_ACC.match(x):
            score["nginx"] += 1
        elif _PM2.match(x):
            score["pm2"] += 1
        elif _SYSTEMD.match(x):
            score["systemd"] += 1
        elif _DOCKER.match(x):
            score["docker"] += 1
        if x.startswith("Traceback") or _PY_EXC.match(x):
            score["python"] += 1
        if re.search(r"^\s+at .*\.(js|ts|mjs):\d+", x) or "UnhandledPromiseRejection" in x:
            score["node"] += 1
        if re.search(r"^\s+at [\w.$]+\([\w]+\.java:\d+\)", x):
            score["java"] += 1
    best = max(score, key=lambda k: score[k])
    return best if score[best] else "text"


def _body(line: str) -> tuple[str, str]:
    """(level, message) with the format prefix removed."""
    m = _NGINX_ERR.match(line)
    if m:
        return m.group(1).lower(), m.group(2)
    m = _NGINX_ACC.match(line)
    if m:
        st = int(m.group(3))
        return ("error" if st >= 500 else "info"), line
    m = _PM2.match(line)
    if m:
        line = m.group(2)
    else:
        m = _SYSTEMD.match(line)
        if m:
            line = f"{m.group(2)}: {m.group(4)}"
        else:
            m = _DOCKER.match(line)
            if m and not line.startswith((" ", "\t")):
                line = f"{m.group(1)}: {m.group(2)}"
    lv = _LEVEL.search(line)
    level = (lv.group(1).lower() if lv else "")
    if level.startswith("warn"):
        level = "warn"
    elif level in ("emerg", "alert", "crit", "critical", "fatal", "panic", "severe"):
        level = "crit"
    elif level in ("err", "error"):
        level = "error"
    return level, line


def entries(text: str) -> list[dict[str, Any]]:
    """Error-ish entries from a raw log: one entry per error line, a whole stack trace = one entry (signature = its last
    exception line + the first own frame)."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    out: list[dict[str, Any]] = []
    i, n = 0, len(lines)
    while i < n:
        raw = lines[i].rstrip()
        if not raw.strip():
            i += 1
            continue
        level, msg = _body(raw)
        stripped = _PM2.sub(r"\2", raw)
        if _TRACE_START.match(stripped.strip()) and (stripped.startswith("Traceback") or "Exception" in stripped or "Error" in stripped or stripped.startswith("panic")):
            block = [stripped]
            j = i + 1
            while j < n and (_TRACE_CONT.match(_PM2.sub(r"\2", lines[j])) or _PY_EXC.match(_PM2.sub(r"\2", lines[j]).strip())
                             or _PM2.sub(r"\2", lines[j]).strip().startswith(("^", "~"))) and j - i < 80:
                block.append(_PM2.sub(r"\2", lines[j]).rstrip())
                j += 1
            exc = next((b.strip() for b in reversed(block) if _PY_EXC.match(b.strip())), "") or block[0].strip()
            frame = next((b.strip() for b in block if re.match(r"\s*(File \"(?!.*site-packages)|at (?!.*node_modules))", b)), "")
            out.append({"level": "error", "text": "\n".join(block)[:1500], "key": f"{exc} @ {frame}"[:400], "trace": True})
            i = j
            continue
        if level in ("error", "crit") or any(rx.search(msg) for _, rxs in _LOG_RX[:12] for rx in rxs):
            out.append({"level": level or "error", "text": raw[:1000], "key": msg[:400], "trace": False})
        i += 1
    return out


def classify_log(text: str) -> str:
    for cid, rxs in _LOG_RX:
        if any(rx.search(text) for rx in rxs):
            return cid
    return "other"


def explain_log(cat: str) -> dict[str, Any]:
    p = next((x for x in LOG_PATTERNS if x[0] == cat), None)
    if not p:
        return {"label": LOG_LABEL["other"], "why": "Pehchaani hui error nahi; sample dekhiye.", "fix": "Pehli baar kab aayi (first seen) ke aas-paas kya badla, dekhiye.",
                "runbook": ""}
    return {"label": p[1], "why": p[3], "fix": p[4], "runbook": p[5]}


# ---------------------------------------------------------------- script safety check (Hoola never runs these)
KNOWN_HOSTS = ("get.docker.com", "sh.rustup.rs", "deb.nodesource.com", "raw.githubusercontent.com/nvm-sh/", "install.python-poetry.org",
               "get.pnpm.io", "bun.sh", "fnm.vercel.app", "astral.sh/uv")


def _f(level: str, line: int, rule: str, why: str, fix: str) -> dict[str, Any]:
    return {"level": level, "line": line, "rule": rule, "why": why, "fix": fix}


def lang_of(name: str, content: str) -> str:
    n = (name or "").lower()
    if n.endswith((".ps1", ".psm1")):
        return "powershell"
    if n.endswith((".yml", ".yaml")):
        return "yaml"
    if n == "dockerfile" or n.endswith(".dockerfile") or re.match(r"^\s*FROM\s+\S+", content or "", re.I | re.M) and "RUN" in (content or ""):
        return "dockerfile"
    if n.endswith(".conf") and ("server {" in content or "location " in content):
        return "nginx"
    if n.endswith((".js", ".cjs")):
        return "js"
    if n.endswith((".service", ".timer")):
        return "ini"
    if "server {" in (content or "") and "listen" in (content or ""):
        return "nginx"
    if re.search(r"^\s*(on:|jobs:)", content or "", re.M):
        return "yaml"
    if re.search(r"\$ErrorActionPreference|Write-Host|Get-ChildItem|Remove-Item", content or ""):
        return "powershell"
    return "bash"


_INLINE_SECRET = re.compile(r"(?i)(?<![A-Za-z0-9])\w*?(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\w*\s*[:=]\s*['\"]?(?!\$|\{\{|<|\[|\s|['\"]?\s*$)"
                            r"([^\s'\"#]{6,})")


def check_script(content: str, lang: str) -> list[dict[str, Any]]:
    """Static safety findings: block = must change before running, warn = should change, info = good to know."""
    out: list[dict[str, Any]] = []
    lines = (content or "").split("\n")
    for i, raw in enumerate(lines, 1):
        x = raw.strip()
        if not x or x.startswith(("#", "//")) and lang not in ("yaml",):
            continue
        if has_secret(x) or (_INLINE_SECRET.search(x) and "secrets." not in x and "${" not in x and "$env:" not in x.lower()
                             and "getenv" not in x.lower() and "process.env" not in x):
            out.append(_f("block", i, "inline_secret", "Script ke andar seedha password / token likha hai.",
                          "Value environment variable / secret store (GitHub Secrets, .env jo repo mein nahi) se lo; jo token dikh gaya use rotate karo."))
        m = re.search(r"\b(curl|wget|iwr|Invoke-WebRequest)\b[^|;]*?(https?://([^/\s'\"]+)[^\s'\"|]*)[^|;]*\|\s*(sudo\s+)?(ba|z|)sh\b", x, re.I)
        m2 = re.search(r"\b(iwr|Invoke-WebRequest|irm|Invoke-RestMethod)\b.*\|\s*(iex|Invoke-Expression)\b", x, re.I)
        if m or m2:
            url = (m.group(2) if m else "")
            known = any(h in url for h in KNOWN_HOSTS)
            out.append(_f("warn" if known else "block", i, "pipe_to_shell", f"Internet se script utha kar seedha chala raha hai ({url or 'iex'}).",
                          "Pehle file download karo, checksum / signature milao, padho, phir chalao; ya package manager use karo."))
        if lang in ("bash", "dockerfile", "yaml"):
            if re.search(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|-r\s+-f|-f\s+-r)\b", x):
                tgt = x.split("rm", 1)[1]
                if re.search(r"(\s|^)/(\s|$|\*)", tgt) or re.search(r"\s(~|\$HOME)/?(\s|$)", tgt):
                    out.append(_f("block", i, "rm_root", "rm -rf poore system / home par chalega.", "Exact folder ka naam likho; kabhi / ya ~ par nahi."))
                elif re.search(r"\$\{?\w+\}?", tgt) and not re.search(r"\$\{\w+:\?", tgt):
                    out.append(_f("block", i, "rm_unguarded_var", "rm -rf ek variable par, bina jaanch ke: variable khaali hua to galat jagah mit jayegi.",
                                  'Use "${VAR:?VAR khaali hai}" (bash khaali par ruk jayega) aur path ke aage-peeche quotes.'))
            if re.search(r"\b(mkfs(\.\w+)?|fdisk|wipefs)\b|\bdd\b.*\bof=/dev/", x):
                out.append(_f("block", i, "disk_wipe", "Disk format / overwrite command.", "Ye script mein mat rakho; haath se, sahi disk dekh kar."))
            if re.search(r":\(\)\s*\{\s*:\|:&\s*\};:", x):
                out.append(_f("block", i, "fork_bomb", "Fork bomb.", "Hatao."))
            if re.search(r"\bchmod\s+(-R\s+)?0?777\b", x):
                out.append(_f("warn", i, "chmod_777", "777 = sabko likhne ki ijazat.", "Owner badlo (chown) aur 750 / 640 do."))
            if re.search(r"\bsshpass\s+-p\b", x):
                out.append(_f("block", i, "sshpass", "Password command line par.", "SSH key use karo."))
            if re.search(r"\bcrontab\s+-r\b", x):
                out.append(_f("block", i, "crontab_r", "Saare cron jobs mita deta hai.", "crontab -e se ek line badlo."))
            if re.search(r"\b(curl)\b.*\s(-k|--insecure)\b|\bwget\b.*--no-check-certificate", x):
                out.append(_f("warn", i, "tls_off", "HTTPS certificate ki jaanch band.", "-k hatao; certificate theek karo."))
            if re.search(r"\beval\s+[\"']?\$", x):
                out.append(_f("warn", i, "eval_var", "Variable ko code ki tarah chala raha hai.", "eval hatao; seedha command likho."))
            if re.search(r"\bgit\s+push\b.*(--force\b|-f\b)", x) and "--force-with-lease" not in x:
                out.append(_f("warn", i, "force_push", "Force push doosron ka kaam mita sakta hai.", "--force-with-lease use karo, main par kabhi nahi."))
            if re.search(r"(?i)\b(drop\s+database|drop\s+table|truncate\s+table)\b", x):
                out.append(_f("warn", i, "sql_drop", "Data mitane wala SQL.", "Pehle backup; script mein confirm step; production par haath se."))
            if re.search(r">\s*/etc/\S+", x) and ">>" not in x:
                out.append(_f("warn", i, "overwrite_etc", "System config file poori overwrite ho rahi hai.", "Pehle backup copy (cp file file.bak) ya sirf ek line badlo."))
        if lang == "powershell":
            if re.search(r"Remove-Item\b.*-Recurse\b.*\$\w+", x, re.I) and not re.search(r"Test-Path|-WhatIf", x, re.I):
                out.append(_f("block", i, "ps_rm_var", "Remove-Item -Recurse ek variable par bina jaanch.", "Pehle if (-not $Path) { throw }; Test-Path; pehli baar -WhatIf."))
            if re.search(r"Set-ExecutionPolicy\s+(Unrestricted|Bypass)", x, re.I):
                out.append(_f("warn", i, "ps_policy", "Poore system ki script policy dheeli.", "-Scope Process use karo, ya script sign karo."))
            if re.search(r"ConvertTo-SecureString\s+.*-AsPlainText", x, re.I) and re.search(r"['\"][^'\"$]{4,}['\"]", x):
                out.append(_f("block", i, "ps_plain_password", "Password script mein likha hai.", "Get-Credential / Windows Credential Manager / env variable."))
            if re.search(r"Format-Volume|Clear-Disk", x, re.I):
                out.append(_f("block", i, "disk_wipe", "Disk format command.", "Script mein mat rakho."))
        if lang == "yaml":
            if re.search(r"\$\{\{\s*github\.event\.(issue|pull_request|comment|review|head_commit|discussion)\.(title|body|head\.ref|message|label)", x):
                out.append(_f("block", i, "gha_injection", "PR / issue ka text seedha run: script mein - koi bhi command ghusa sakta hai.",
                              "Pehle env: mein daalo (TITLE: ${{ github.event.pull_request.title }}) aur script mein \"$TITLE\" likho."))
            if re.search(r"permissions:\s*write-all", x):
                out.append(_f("warn", i, "gha_write_all", "Token ko saari ijazat.", "Sirf jo chahiye: permissions: { contents: read }."))
            m3 = re.search(r"uses:\s*([\w.-]+)/([\w.-]+)(/[\w./-]+)?@([\w.-]+)", x)
            if m3 and m3.group(1) not in ("actions", "github", "docker") and not re.fullmatch(r"[0-9a-f]{40}", m3.group(4)):
                out.append(_f("info", i, "gha_unpinned", f"Bahar ka action {m3.group(1)}/{m3.group(2)} tag se (@{m3.group(4)}), commit SHA se nahi.",
                              "Bharose ke liye poore 40-akshar SHA par pin karo (tag badla ja sakta hai)."))
        if lang == "dockerfile":
            if re.match(r"(?i)FROM\s+[\w./-]+(:latest)?\s*($|\s+AS)", x) and ":" not in x.split()[1]:
                out.append(_f("warn", i, "docker_latest", "Base image ka version tay nahi (latest).", "Tag pin karo, jaise node:20-slim / python:3.12-slim."))
            if re.match(r"(?i)(ENV|ARG)\s+\w*(PASS|SECRET|TOKEN|KEY)\w*\s*[= ]\s*\S+", x):
                out.append(_f("block", i, "docker_secret", "Secret image ke andar baked.", "Runtime par env / docker secret se do; BuildKit --secret."))
            if re.match(r"(?i)ADD\s+https?://", x):
                out.append(_f("warn", i, "docker_add_url", "ADD URL se file bina checksum.", "RUN curl + sha256sum -c, ya COPY."))
        if lang == "nginx":
            if re.search(r"ssl_protocols[^;]*\bTLSv1(\.1)?\b(?!\.[23])", x):
                out.append(_f("warn", i, "nginx_old_tls", "Purana TLS 1.0 / 1.1 chalu.", "ssl_protocols TLSv1.2 TLSv1.3;"))
            if re.search(r"\bautoindex\s+on\b", x):
                out.append(_f("warn", i, "nginx_autoindex", "Folder ki saari files ki list sabko dikhegi.", "autoindex off;"))
    if lang == "bash" and content.strip() and not re.search(r"^\s*set\s+-[a-z]*e[a-z]*u[a-z]*o\s+pipefail|^\s*set\s+-euo\s+pipefail", content, re.M):
        out.append(_f("warn", 1, "no_strict", "set -euo pipefail nahi: beech mein error aaye to bhi script aage chalta rahega.",
                      "Shebang ke neeche set -euo pipefail likho."))
    if lang == "powershell" and content.strip() and "$ErrorActionPreference" not in content:
        out.append(_f("warn", 1, "ps_no_stop", "Error par script nahi rukta.", "Upar $ErrorActionPreference = 'Stop' likho."))
    if lang == "yaml" and re.search(r"^on:", content, re.M):
        if "pull_request_target" in content and re.search(r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head\.(sha|ref)", content):
            out.append(_f("block", 1, "gha_prt_checkout", "pull_request_target ke saath PR ka code checkout: fork ka code aapke secrets ke saath chalega.",
                          "pull_request use karo, ya PR code ko secrets ke bina alag job mein."))
        if not re.search(r"^\s*permissions:", content, re.M):
            out.append(_f("info", 1, "gha_no_permissions", "permissions: block nahi (token ko default ijazat).", "Upar permissions: { contents: read } likho."))
        if re.search(r"(deploy|production|prod)", content, re.I) and not re.search(r"^\s*environment:", content, re.M):
            out.append(_f("warn", 1, "gha_no_environment", "Deploy job bina environment: (koi approval / protection nahi).",
                          "environment: production likho aur GitHub mein us environment par required reviewer lagao."))
        if re.search(r"(deploy|production)", content, re.I) and "concurrency" not in content:
            out.append(_f("info", 1, "gha_no_concurrency", "Do deploy saath chal sakte hain.", "concurrency: { group: deploy-production, cancel-in-progress: false }"))
    if lang == "dockerfile" and content.strip() and not re.search(r"^\s*USER\s+\S+", content, re.M | re.I):
        out.append(_f("warn", 1, "docker_root", "Container root user se chalega.", "Aakhir mein USER node / USER 1000 likho."))
    order = {"block": 0, "warn": 1, "info": 2}
    return sorted(out, key=lambda f: (order[f["level"]], f["line"]))


def verdict(findings: list[dict[str, Any]]) -> str:
    if any(f["level"] == "block" for f in findings):
        return "block"
    if any(f["level"] == "warn" for f in findings):
        return "warn"
    return "ok"


# ---------------------------------------------------------------- checklists
CHECKLISTS: dict[str, dict[str, Any]] = {
    "deploy": {"title": "Production deploy checklist", "sections": [
        ("Pehle", ["CI ke saare checks hare (green)", "Kya badla hai padh liya (commits / PR)", "Database migration hai? Pehle backup liya + migration padhi",
                   "Naye env variables / secrets production mein daale (chat mein nahi)", "Rollback plan: pichhla accha commit pata hai",
                   "Bheed kam wala samay (raat / Sunday subah nahi jab aap so rahe ho)", "Team / support ko bataya"]),
        ("Deploy ke waqt", ["Hoola ke Deploy card par aapka tap", "Workflow chalte hue dekhna (Hoola dikhata hai)", "Health URL hara"]),
        ("Baad mein (15 min)", ["Error logs (Hoola ke clusters) mein naya kuch?", "Main kaam haath se ek baar (login / order / payment page)",
                                "Response time theek", "Release tag / note likha"]),
    ]},
    "release": {"title": "App release checklist", "sections": [
        ("Pehle", ["Version + build number badhaya", "Changelog likha", "Saare tests + lint hare", "Signing key repo mein nahi (secret mein)",
                   "Privacy policy / data safety form badla agar naya data liya"]),
        ("Release", ["Pehle internal / beta track", "Crash rate dekho 24 ghante", "Phir sab users"]),
    ]},
    "server_setup": {"title": "Naya server (hardening)", "sections": [
        ("Login", ["SSH sirf key se (PasswordAuthentication no)", "root login band (PermitRootLogin no)", "Apna sudo user", "fail2ban"]),
        ("Network", ["ufw: sirf 22 / 80 / 443", "Database port bahar band", "Admin panels VPN / IP se"]),
        ("Updates + ghadi", ["unattended-upgrades", "timedatectl: NTP chalu (CERT-In: ghadi NTP se mili ho)"]),
        ("Logs + backup", ["Logs 180 din rakhne ka intezaam, India mein (CERT-In) - logrotate + compress", "Roz backup, server se bahar copy",
                           "Mahine mein ek baar restore karke dekho"]),
        ("App", ["App root se nahi, apne user se", ".env 600 permission", "pm2 startup / systemd se reboot par chalu", "HTTPS + auto renew (certbot)"]),
    ]},
    "incident": {"title": "Production toot gaya (incident)", "sections": [
        ("Turant", ["Kya toota, kab se (Hoola uptime / logs)", "Pichhla deploy kab hua? Shak ho to rollback card", "Users / team ko ek line ka update"]),
        ("Data / hacking ka shak", ["IT Helpdesk > Suraksha: CERT-In 6 ghante wala niyam dekho", "Saboot (logs) mat mitao", "Passwords / keys rotate"]),
        ("Baad mein", ["Asli wajah (blameless)", "Kya badlenge taaki dobara na ho", "Runbook update"]),
    ]},
    "backup_restore": {"title": "Backup restore test", "sections": [
        ("Test", ["Naya khaali server / folder", "Aakhri backup se restore", "App chala kar data dekho", "Kitna samay laga likho (RTO)",
                  "Kitna purana data tha (RPO)"])]},
}


def checklist_items(kind: str, extra: list[str] | None = None) -> tuple[str, list[dict[str, Any]]]:
    c = CHECKLISTS.get(kind) or CHECKLISTS["deploy"]
    items, n = [], 0
    for sec, rows in c["sections"]:
        for t in rows:
            n += 1
            items.append({"id": f"c{n}", "section": sec, "text": t, "done": False, "by": ""})
    for t in extra or []:
        n += 1
        items.append({"id": f"c{n}", "section": "Aapke niyam", "text": t[:200], "done": False, "by": ""})
    return c["title"], items


# ---------------------------------------------------------------- DORA
def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


REWORK = re.compile(r"(?i)\b(hotfix|hot-fix|revert|rollback|fix prod|urgent fix|emergency)\b")


def dora(deploys: list[dict[str, Any]], days: int, when: datetime) -> dict[str, Any]:
    """deploys: [{at, ok, commit_at, rollback, title, branch}] (production deploy runs, any source). Plain-words DORA five."""
    since = when - timedelta(days=days)
    ds = sorted((d for d in deploys if _aware(d["at"]) and _aware(d["at"]) >= since), key=lambda d: _aware(d["at"]))
    ok = [d for d in ds if d["ok"] and not d.get("rollback")]
    total = len(ds)
    lead = [(_aware(d["at"]) - _aware(d["commit_at"])).total_seconds() / 3600 for d in ok if d.get("commit_at")]
    failed = [d for d in ds if not d["ok"] or d.get("rollback")]
    # a 'change failure' = a failed deploy, or a good deploy rolled back within 24 h
    cf = 0
    rec: list[float] = []
    for i, d in enumerate(ds):
        nxt = ds[i + 1] if i + 1 < len(ds) else None
        bad = not d["ok"] or (nxt is not None and nxt.get("rollback") and
                              (_aware(nxt["at"]) - _aware(d["at"])) <= timedelta(hours=24) and d["ok"] and not d.get("rollback"))
        if bad and not d.get("rollback"):
            cf += 1
        if not d["ok"] or d.get("rollback"):
            after = next((x for x in ds[i + 1:] if x["ok"]), None)
            if after:
                rec.append((_aware(after["at"]) - _aware(d["at"])).total_seconds() / 3600)
    changes = [d for d in ds if not d.get("rollback")]
    rework = [d for d in changes if REWORK.search(f"{d.get('title', '')} {d.get('branch', '')}")]
    per_week = round(len(ok) / max(days / 7, 1), 2)

    def band_freq(x: float) -> str:
        return "elite" if x >= 7 else "high" if x >= 1 else "medium" if x >= 0.25 else "low"
    out = {"days": days, "deploys": total, "successful": len(ok), "failed": len(failed), "per_week": per_week,
           "frequency_band": band_freq(per_week) if total else "",
           "lead_time_h": round(median(lead), 1) if lead else None,
           "change_failure_pct": round(100 * cf / len(changes), 1) if changes else None,
           "recovery_h": round(median(rec), 1) if rec else None,
           "rework_pct": round(100 * len(rework) / len(changes), 1) if changes else None}
    lines = []
    if not total:
        lines.append(f"Pichhle {days} din mein koi production deploy nahi dikha.")
    else:
        lines.append(f"{days} din: {len(ok)} safal deploy (hafte mein {per_week}), {len(failed)} fail / rollback.")
        if out["lead_time_h"] is not None:
            lines.append(f"Commit se production tak beech ka samay ~{out['lead_time_h']} ghante.")
        if out["change_failure_pct"] is not None:
            lines.append(f"Har 100 badlav mein ~{out['change_failure_pct']:.0f} ne kuch toda.")
        if out["recovery_h"] is not None:
            lines.append(f"Toote deploy ke baad theek hone mein ~{out['recovery_h']} ghante.")
        if out["rework_pct"]:
            lines.append(f"{out['rework_pct']:.0f}% deploy bina plan ke (hotfix / revert) the.")
    out["say"] = " ".join(lines)
    return out


def trend(durations: list[int]) -> dict[str, Any]:
    """durations newest first (seconds). Median of the last 10 vs the 10 before."""
    a, b = durations[:10], durations[10:20]
    if len(a) < 3:
        return {"median_s": int(median(a)) if a else None, "before_s": None, "change_pct": None, "slower": False}
    ma = median(a)
    mb = median(b) if len(b) >= 3 else None
    ch = round(100 * (ma - mb) / mb, 1) if mb else None
    srt = sorted(a)
    p90 = srt[min(len(srt) - 1, int(round(0.9 * (len(srt) - 1))))]
    return {"median_s": int(ma), "before_s": int(mb) if mb else None, "change_pct": ch, "p90_s": int(p90),
            "slower": bool(ch is not None and ch >= 30 and ma - (mb or 0) >= 60)}


def mins(sec: int | float | None) -> str:
    if sec is None:
        return "-"
    sec = int(sec)
    return f"{sec // 60} min {sec % 60} s" if sec >= 60 else f"{sec} s"
