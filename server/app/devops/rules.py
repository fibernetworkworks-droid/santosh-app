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
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[private key removed]"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"), "[token removed]"),
    (re.compile(r"\b(sk-(ant-)?[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{30,}|AKIA[0-9A-Z]{16}|xox[abpr]-[A-Za-z0-9-]{10,}|rzp_(live|test)_[A-Za-z0-9]{8,})\b"), "[key removed]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}\b"), "[jwt removed]"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{16,}"), r"\1 [hataya]"),
    (re.compile(r"(?i)(\b[a-z][a-z0-9+.-]{1,15}://[^:/\s@]+:)([^@\s]+)(@)"), r"\1[hataya]\3"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)(\s*[=:]\s*|\"\s*:\s*\")([^\s\"',;&]{3,})"),
     r"\1\2[hataya]"),
    (re.compile(r"\b\d{12,19}\b"), "[number removed]"),
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
    ("disk_full", "Disk full", [r"No space left on device", r"\bENOSPC\b", r"not enough space on the disk"],
     "The runner's disk is full (large Docker images / caches / build output).",
     "Remove old Docker images / tool caches at the start of the workflow (docker system prune -af), make the artifacts smaller, or use a bigger runner.", False),
    ("oom", "Out of memory (OOM)", [r"JavaScript heap out of memory", r"java\.lang\.OutOfMemoryError", r"\bMemoryError\b",
                                    r"exit code 137", r"Killed\s+signal terminated program", r"Gradle build daemon disappeared unexpectedly",
                                    r"The runner has received a shutdown signal", r"Metaspace"],
     "The runner did not have enough RAM for the build (Node / Gradle / Java asked for more memory).",
     "Node: NODE_OPTIONS=--max-old-space-size=4096; Gradle: org.gradle.jvmargs=-Xmx3g and fewer workers; run fewer tests in parallel; or use a bigger runner.", False),
    ("timeout", "Timed out", [r"has exceeded the maximum execution time", r"The job running on runner .* has exceeded",
                                 r"timed out after \d+", r"Timeout of \d+ms exceeded", r"context deadline exceeded", r"timeout-minutes"],
     "The job or a test ran longer than its time limit (a stuck test, a slow network, or a very large job).",
     "Find the stuck test (the last line that ran), give the test a timeout, use a cache; do not raise timeout-minutes more than needed.", True),
    ("rate_limit", "Rate limit", [r"API rate limit exceeded", r"429 Too Many Requests", r"toomanyrequests", r"secondary rate limit"],
     "A service (GitHub API / Docker Hub / npm) blocked the run for too many requests.",
     "Log in to Docker Hub before pulling (the limit goes up), use a cache, call the API with GITHUB_TOKEN; run it again after a while.", True),
    ("network", "Network problem", [r"\bECONNRESET\b", r"\bETIMEDOUT\b", r"\bEAI_AGAIN\b", r"Could not resolve host", r"Temporary failure in name resolution",
                                      r"Connection reset by peer", r"TLS handshake timeout", r"Read timed out", r"503 Service Unavailable",
                                      r"502 Bad Gateway", r"socket hang up", r"Connection timed out", r"unable to access 'https://"],
     "A download or API call broke midway (package registry / GitHub / an outside service).",
     "Running it again usually fixes it; if it keeps happening, add retries (npm ci --fetch-retries, pip --retries, Gradle --offline cache) and use a dependency cache.", True),
    ("secret_missing", "Secret / env missing", [r"Input required and not supplied", r"secret\s+\S+\s+(is\s+)?not\s+(set|found|defined)",
                                                r"environment variable\s+\S+\s+(is\s+)?(not set|missing|undefined)", r"Missing required (env|environment)",
                                                r"KeyError: '[A-Z_]{3,}'", r"must be set|is not set\b",
                                                r"Keystore file .* not found", r"keystore password was incorrect"],
     "The workflow did not get a secret / environment variable (wrong name, a secret that belongs to an environment, or a PR from a fork, which gets no secrets).",
     "Check the name in Repo > Settings > Secrets and variables > Actions (upper / lower case matters); for an environment secret, add environment: to the job. Never put a secret's value in chat.", False),
    ("auth", "Login / permission", [r"Bad credentials", r"401 Unauthorized", r"\b403 Forbidden\b", r"Resource not accessible by integration",
                                r"Permission to .* denied", r"denied: requested access to the resource is denied", r"authentication required",
                                r"Host key verification failed", r"Permission denied \(publickey"],
     "The token / key is not allowed to do this, or the token has expired.",
     "For GITHUB_TOKEN, add a permissions: block to the workflow (such as contents: write / packages: write); create a new deploy key / token; add the SSH host key to known_hosts.", False),
    ("lockfile", "Lockfile does not match", [r"npm ci can only install packages when your package\.json and package-lock\.json",
                                             r"lockfile .* (out of date|needs to be updated)", r"--frozen-lockfile", r"poetry\.lock is not consistent",
                                             r"Your lockfile needs to be updated", r"pubspec\.lock .* out of date"],
     "package.json / pyproject changed but the lockfile was not committed.",
     "Run npm install (or poetry lock / pnpm install) on your laptop and commit the lockfile.", False),
    ("version", "Version mismatch", [r"The engine \"node\" is incompatible", r"Unsupported engine", r"requires Java \d+",
                                            r"Unsupported class file major version", r"Android Gradle plugin requires Java \d+",
                                            r"The current Dart SDK version is", r"requires Python\s*[<>=]", r"python_requires",
                                            r"node: bad option", r"Requires: Python"],
     "The tool version on the runner is different from the project's (Node / Java / Dart / Python).",
     "In setup-node / setup-java / setup-python / flutter-action, set the version the project asks for (.nvmrc, java 17, pubspec environment).", False),
    ("dependency", "Dependency not found", [r"\bERESOLVE\b", r"npm ERR! code E404", r"No matching distribution found", r"ResolutionImpossible",
                                           r"Could not resolve dependencies", r"Could not resolve [\w.\-]+:[\w.\-]+", r"Could not find [\w.\-]+:[\w.\-]+",
                                           r"version solving failed", r"ModuleNotFoundError", r"Cannot find module '", r"Duplicate class",
                                           r"error: package .* does not exist", r"Unable to find a matching variant",
                                           r"ImportError: cannot import name"],
     "A package / library was not found, or versions conflict with each other.",
     "Find the package name in the error: pin the right version in requirements / package.json / build.gradle; if a new library was added, commit the lockfile too.", False),
    ("lint", "Lint / format", [r"\d+ problems? \(\d+ errors?", r"\beslint\b.*error", r"would reformat", r"Found \d+ errors?\.", r"\bflake8\b",
                               r"\d+ issues? found", r"Code style issues found", r"lintVitalRelease", r"\bruff\b.*\berror", r"error • .* • \w+",
                               r"Lint found errors"],
     "Code style / lint rules were broken (the build is fine, but the checker stopped it).",
     "Run the same lint on your laptop (npm run lint -- --fix / ruff --fix / dart fix --apply / black .) and commit.", False),
    ("test_failure", "Tests failed", [r"^FAILED \S+::\S+", r"=+ \d+ failed", r"Tests?:\s+\d+ failed", r"Test Suites: \d+ failed", r"--- FAIL: ",
                                   r"There were failing tests", r"AssertionError", r"\bexpect\(.*\)\.", r"Tests failed", r"\d+ tests? completed, \d+ failed",
                                   r"Some tests failed", r"FAIL\s+\S+\.(test|spec)\.", r"Expected: .*\n.*Actual:"],
     "The code built but some tests failed.",
     "Find the failing test's name and its first assert line; run only that test on your laptop. If the same commit passes when run again, the test is flaky.", True),
    ("compile", "Code did not compile", [r"error TS\d+", r"SyntaxError", r"error: cannot find symbol", r"^e: (file://|/)\S+\.kt",
                                         r"Compilation failed", r"error\[E\d+\]", r"undefined reference to", r"\.dart:\d+:\d+: Error",
                                         r"error CS\d+", r"Build failed with an exception", r"cannot find package", r"IndentationError", r"NameError"],
     "The code has a syntax / type error, so the build failed.",
     "Open the file and line with the error (the log shows file:line), fix it and commit; try the build on your laptop.", False),
    ("docker", "Docker build", [r"failed to solve", r"pull access denied", r"manifest unknown", r"COPY failed", r"failed to compute cache key",
                                r"executor failed running"],
     "Building the Docker image failed (base image / COPY path / RUN command).",
     "Check the base image name and tag, keep the COPY path inside the build context, and try the RUN command with docker build on your laptop.", False),
    ("permission", "File permission", [r"Permission denied", r"\bEACCES\b", r"Operation not permitted"],
     "No permission to run the script or file (often ./gradlew or a .sh file is not executable).",
     "Run git update-index --chmod=+x gradlew (or the script) and commit; or add chmod +x in the workflow.", False),
    ("runner", "No runner / runner stopped", [r"No runner matching the specified labels", r"lost communication with the server",
                                              r"The operation was canceled", r"waiting for a runner"],
     "The job got no runner, or the runner stopped midway (self-hosted machine off / wrong label).",
     "Check the runs-on label; is the self-hosted runner on? Check GitHub status too. Run it again.", True),
]
CI_LABEL = {p[0]: p[1] for p in CI_PATTERNS} | {"cancelled": "Cancelled", "unknown": "Not recognized"}
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
                "why": "No known error was found in the log.", "fix": "Look at the error lines below; if needed, send that part of the log to Hoola."}
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
    ("upstream_down", "App is down (no answer to nginx)", [r"connect\(\) failed \(111: Connection refused\) while connecting to upstream",
                                                           r"no live upstreams", r"\b502\b.*(Bad Gateway)?", r"upstream prematurely closed"],
     "nginx is trying to reach the app, but the app is not running / not listening on the port.",
     "Check pm2 status / systemctl status; match the app's port with nginx's proxy_pass; look at the first error in the app's own log.", "app_down"),
    ("upstream_slow", "App is slow (504 / timeout)", [r"upstream timed out", r"\b504\b", r"Gateway Time-?out"],
     "The app did not answer within nginx's time limit (slow query / stuck job).",
     "Find the slow request (the URL in the access log), check the DB query / outside API; raise proxy_read_timeout only when the work really is long.", "slow_app"),
    ("db_down", "No connection to the database", [r"(ECONNREFUSED|Connection refused).*(5432|3306|27017|6379)", r"could not connect to server",
                                               r"SQLSTATE\[HY000\] \[2002\]", r"OperationalError", r"too many connections",
                                               r"MongoNetworkError", r"Redis connection .* failed", r"remaining connection slots are reserved"],
     "The app cannot connect to the database (Postgres / MySQL / Mongo / Redis), or it has run out of connections.",
     "Is the database service running? (systemctl status postgresql); make the connection pool smaller; are the password / host in .env right?", "db_down"),
    ("oom_kill", "Out of memory, process killed", [r"Out of memory: Killed process", r"oom-kill", r"OOMKilled", r"JavaScript heap out of memory",
                                                     r"java\.lang\.OutOfMemoryError", r"\bMemoryError\b", r"Cannot allocate memory"],
     "The server ran out of RAM and Linux killed the process.",
     "Use free -m and pm2 monit to see what is using the most memory; add swap, set pm2 max_memory_restart, look for a memory leak.", "oom"),
    ("disk_full", "Disk full", [r"No space left on device", r"\bENOSPC\b", r"disk full", r"Disk quota exceeded"],
     "The server's disk is full (logs / backups / docker images).",
     "Check df -h and du -sh /var/log/*; set up logrotate, remove old backups / docker images (carefully).", "disk_full"),
    ("port_in_use", "Port already in use", [r"EADDRINUSE", r"Address already in use", r"bind\(\) to \S+ failed \(98"],
     "Two processes want the same port (an old copy is still running).",
     "Use sudo ss -ltnp | grep <port> to see what holds it; stop the old process, keep only one copy in pm2.", "port_in_use"),
    ("crash_loop", "App keeps restarting", [r"restarting too often|too many unstable restarts", r"Start request repeated too quickly",
                                             r"exited with code [1-9]", r"Main process exited, code=exited, status=[1-9]", r"errored",
                                             r"Back-off restarting failed container", r"CrashLoopBackOff"],
     "The app stops as soon as it starts; it is in a restart loop.",
     "Look at the first error line before the restart (that is the real cause); check .env / config / migration.", "crash_loop"),
    ("ssl", "SSL / certificate", [r"certificate (has )?expired", r"SSL_ERROR|ssl_error", r"SSL_do_handshake\(\) failed", r"unable to verify the first certificate",
                                  r"CERT_HAS_EXPIRED", r"self[- ]signed certificate"],
     "The certificate is expired / wrong, or the chain is incomplete.",
     "Run certbot renew --dry-run; use fullchain.pem in nginx; is the system clock (NTP) right?", "ssl"),
    ("permission", "Permission", [r"Permission denied", r"\bEACCES\b", r"\(13: Permission denied\)"],
     "The process is not allowed to read / write the file or folder.",
     "Check the owner with ls -l; give the folder to the user the app runs as (chown); never use 777.", "permission"),
    ("too_many_files", "Too many open files", [r"Too many open files", r"\bEMFILE\b", r"worker_connections are not enough"],
     "The process hit its limit of open files / connections.",
     "Raise ulimit -n (systemd: LimitNOFILE), raise nginx worker_connections, and find where connections are not being closed.", "limits"),
    ("dns", "DNS / host not found", [r"getaddrinfo (ENOTFOUND|EAI_AGAIN)", r"Name or service not known", r"Temporary failure in name resolution",
                                     r"could not resolve host"],
     "The server could not resolve an outside host name.",
     "Check /etc/resolv.conf and the internet connection; is the host name in .env right?", "network"),
    ("timeout", "Outside service timed out", [r"\bETIMEDOUT\b", r"timed out", r"Read timed out", r"deadline exceeded"],
     "An outside service / API did not answer in time.",
     "Find which service it is (URL / host), add a timeout + retry, check its status page.", "network"),
    ("auth", "Login / token failed", [r"jwt expired", r"invalid token", r"401 Unauthorized", r"authentication failed", r"Access denied for user"],
     "A token / password check failed (expired / wrong / changed).",
     "Check the token / password date; put the new secret in .env (never in chat) and restart the app.", "auth"),
    ("module", "Code / package not found", [r"Cannot find module", r"ModuleNotFoundError", r"ImportError", r"ClassNotFoundException",
                                             r"undefined is not a function", r"is not defined"],
     "A package / file was not found after the deploy (not installed, or a wrong build).",
     "Run npm ci / pip install -r requirements.txt on the server; was the whole build folder uploaded? If the previous version worked, roll back.", "bad_deploy"),
    ("segfault", "Process crash (segfault)", [r"segfault at", r"Segmentation fault", r"SIGSEGV", r"core dumped"],
     "A crash in native code / a library.",
     "Find which package update it started after; go back to the previous version; give the core dump to the developer.", "crash_loop"),
    ("exception", "Error in the code (exception)", [r"Traceback \(most recent call last\)", r"Unhandled(Promise)?Rejection", r"uncaughtException",
                                                 r"\w+Exception\b", r"\w+Error:", r"panic:"],
     "The app's code raised an error that was not caught.",
     "Look at the lowest file:line in the stack trace that is your own code (not a library's); give this trace to the developer.", "exception"),
    ("http_5xx", "Server error (5xx)", [r'" 5\d\d '],
     "The server is answering requests with 5xx.", "Look at the app log for the same time; if it is always one URL, check that route.", "slow_app"),
]
LOG_LABEL = {p[0]: p[1] for p in LOG_PATTERNS} | {"other": "Other error"}
_LOG_RX = [(p[0], [re.compile(r, re.I) for r in p[2]]) for p in LOG_PATTERNS]

RUNBOOKS: dict[str, dict[str, Any]] = {
    "app_down": {"title": "App is down / 502", "steps": [
        "pm2 status (or systemctl status <app>) - is the app online?", "pm2 logs <app> --lines 100 - the first error before it went down",
        "nginx proxy_pass port = the app's port? (ss -ltnp)", "Start the app: pm2 restart <app> (you do this; Hoola runs nothing on the server)",
        "Still down: roll back to the previous deploy (DevOps > Deploy > Rollback card)"]},
    "slow_app": {"title": "App is slow / 504", "steps": [
        "Find the slow URL in the access log ($request_time, if the log format has it)", "A slow DB query at the same time (slow query log)",
        "What is the outside API's timeout?", "CPU / RAM: top, free -m", "If the work really is long, make it a background job; raise the proxy timeout only then"]},
    "db_down": {"title": "No connection to the database", "steps": [
        "systemctl status postgresql (or mysql / redis)", "Is the disk full? df -h", "Connections: max_connections vs the app's pool size",
        "Are host / port / user in .env right? (do not send the password in chat)", "Check the backup date before a restart"]},
    "oom": {"title": "Out of memory (OOM)", "steps": [
        "dmesg -T | grep -i 'killed process' - what was killed", "free -m, pm2 monit", "Add swap (2-4 GB) if there is none",
        "pm2: max_memory_restart: '500M' (ecosystem file)", "Memory leak: which deploy did it start after?"]},
    "disk_full": {"title": "Disk full", "steps": [
        "df -h and du -xh / --max-depth=2 | sort -h | tail", "Logs: set up logrotate (CERT-In: logs must be kept 180 days, so compress, do not delete)",
        "docker system df / old images (carefully)", "Move old backups somewhere else (off-server)", "Hoola alerts you at 85%"]},
    "port_in_use": {"title": "Port already in use", "steps": ["sudo ss -ltnp | grep :<port>", "Stop the old copy", "pm2 delete <old name>", "Keep only one process"]},
    "crash_loop": {"title": "Keeps restarting", "steps": [
        "The FIRST error line before the restart (the rest follow from it)", "Did .env / config change?", "Did the migration run?", "If the previous version was fine, roll back"]},
    "ssl": {"title": "SSL / certificate", "steps": ["sudo certbot certificates", "sudo certbot renew --dry-run", "nginx: ssl_certificate = fullchain.pem",
                                                    "timedatectl - the clock is synced with NTP (CERT-In requires it too)"]},
    "permission": {"title": "Permission denied", "steps": ["ls -l <file>", "Which user the app runs as (ps -o user= -p <pid>)", "chown <user> <folder>; never 777"]},
    "limits": {"title": "Too many open files", "steps": ["ulimit -n", "systemd unit: LimitNOFILE=65535", "nginx: worker_connections", "Are connections being closed? (leak)"]},
    "network": {"title": "Outside service / DNS", "steps": ["dig <host> / curl -I https://<host>", "Its status page", "Timeout + retry in the code", "The server's DNS (/etc/resolv.conf)"]},
    "auth": {"title": "Token / login failed", "steps": ["Token expiry", "New secret in .env (never in chat)", "App restart", "Rotate / revoke the old key"]},
    "bad_deploy": {"title": "Broke after a deploy", "steps": ["Which commit went out (DevOps > Deploy)", "Did npm ci / pip install run?", "Is the build folder complete?",
                                                                  "Send a rollback card; you tap it"]},
    "exception": {"title": "Exception in the code", "steps": ["Your own file:line in the stack trace", "Which request / input caused it", "Give the developer the trace + the time", "If it keeps happening, turn that feature off (flag)"]},
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
        return {"label": LOG_LABEL["other"], "why": "Not a recognized error; look at the sample.", "fix": "Check what changed around the time it first appeared (first seen).",
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
            out.append(_f("block", i, "inline_secret", "A password / token is written directly in the script.",
                          "Take the value from an environment variable / secret store (GitHub Secrets, a .env that is not in the repo); rotate the token that was exposed."))
        m = re.search(r"\b(curl|wget|iwr|Invoke-WebRequest)\b[^|;]*?(https?://([^/\s'\"]+)[^\s'\"|]*)[^|;]*\|\s*(sudo\s+)?(ba|z|)sh\b", x, re.I)
        m2 = re.search(r"\b(iwr|Invoke-WebRequest|irm|Invoke-RestMethod)\b.*\|\s*(iex|Invoke-Expression)\b", x, re.I)
        if m or m2:
            url = (m.group(2) if m else "")
            known = any(h in url for h in KNOWN_HOSTS)
            out.append(_f("warn" if known else "block", i, "pipe_to_shell", f"Downloads a script from the internet and runs it directly ({url or 'iex'}).",
                          "Download the file first, check its checksum / signature, read it, then run it; or use a package manager."))
        if lang in ("bash", "dockerfile", "yaml"):
            if re.search(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|-r\s+-f|-f\s+-r)\b", x):
                tgt = x.split("rm", 1)[1]
                if re.search(r"(\s|^)/(\s|$|\*)", tgt) or re.search(r"\s(~|\$HOME)/?(\s|$)", tgt):
                    out.append(_f("block", i, "rm_root", "rm -rf will run on the whole system / home.", "Name the exact folder; never / or ~."))
                elif re.search(r"\$\{?\w+\}?", tgt) and not re.search(r"\$\{\w+:\?", tgt):
                    out.append(_f("block", i, "rm_unguarded_var", "rm -rf on a variable with no check: if the variable is empty, the wrong place gets deleted.",
                                  'Use "${VAR:?VAR is empty}" (bash stops when it is empty) and put quotes around the path.'))
            if re.search(r"\b(mkfs(\.\w+)?|fdisk|wipefs)\b|\bdd\b.*\bof=/dev/", x):
                out.append(_f("block", i, "disk_wipe", "Disk format / overwrite command.", "Do not keep this in a script; do it by hand, after checking it is the right disk."))
            if re.search(r":\(\)\s*\{\s*:\|:&\s*\};:", x):
                out.append(_f("block", i, "fork_bomb", "Fork bomb.", "Remove it."))
            if re.search(r"\bchmod\s+(-R\s+)?0?777\b", x):
                out.append(_f("warn", i, "chmod_777", "777 = everyone can write.", "Change the owner (chown) and use 750 / 640."))
            if re.search(r"\bsshpass\s+-p\b", x):
                out.append(_f("block", i, "sshpass", "Password on the command line.", "Use an SSH key."))
            if re.search(r"\bcrontab\s+-r\b", x):
                out.append(_f("block", i, "crontab_r", "Deletes all cron jobs.", "Change one line with crontab -e."))
            if re.search(r"\b(curl)\b.*\s(-k|--insecure)\b|\bwget\b.*--no-check-certificate", x):
                out.append(_f("warn", i, "tls_off", "HTTPS certificate check is off.", "Remove -k; fix the certificate."))
            if re.search(r"\beval\s+[\"']?\$", x):
                out.append(_f("warn", i, "eval_var", "Runs a variable as code.", "Remove eval; write the command directly."))
            if re.search(r"\bgit\s+push\b.*(--force\b|-f\b)", x) and "--force-with-lease" not in x:
                out.append(_f("warn", i, "force_push", "A force push can erase other people's work.", "Use --force-with-lease, never on main."))
            if re.search(r"(?i)\b(drop\s+database|drop\s+table|truncate\s+table)\b", x):
                out.append(_f("warn", i, "sql_drop", "SQL that deletes data.", "Back up first; add a confirm step to the script; on production, do it by hand."))
            if re.search(r">\s*/etc/\S+", x) and ">>" not in x:
                out.append(_f("warn", i, "overwrite_etc", "A system config file is being overwritten completely.", "Make a backup copy first (cp file file.bak), or change only one line."))
        if lang == "powershell":
            if re.search(r"Remove-Item\b.*-Recurse\b.*\$\w+", x, re.I) and not re.search(r"Test-Path|-WhatIf", x, re.I):
                out.append(_f("block", i, "ps_rm_var", "Remove-Item -Recurse on a variable with no check.", "First if (-not $Path) { throw }; Test-Path; use -WhatIf the first time."))
            if re.search(r"Set-ExecutionPolicy\s+(Unrestricted|Bypass)", x, re.I):
                out.append(_f("warn", i, "ps_policy", "Loosens the script policy for the whole system.", "Use -Scope Process, or sign the script."))
            if re.search(r"ConvertTo-SecureString\s+.*-AsPlainText", x, re.I) and re.search(r"['\"][^'\"$]{4,}['\"]", x):
                out.append(_f("block", i, "ps_plain_password", "The password is written in the script.", "Get-Credential / Windows Credential Manager / env variable."))
            if re.search(r"Format-Volume|Clear-Disk", x, re.I):
                out.append(_f("block", i, "disk_wipe", "Disk format command.", "Do not keep it in a script."))
        if lang == "yaml":
            if re.search(r"\$\{\{\s*github\.event\.(issue|pull_request|comment|review|head_commit|discussion)\.(title|body|head\.ref|message|label)", x):
                out.append(_f("block", i, "gha_injection", "PR / issue text goes straight into a run: script - anyone can inject a command.",
                              "Put it in env: first (TITLE: ${{ github.event.pull_request.title }}) and write \"$TITLE\" in the script."))
            if re.search(r"permissions:\s*write-all", x):
                out.append(_f("warn", i, "gha_write_all", "The token gets every permission.", "Only what is needed: permissions: { contents: read }."))
            m3 = re.search(r"uses:\s*([\w.-]+)/([\w.-]+)(/[\w./-]+)?@([\w.-]+)", x)
            if m3 and m3.group(1) not in ("actions", "github", "docker") and not re.fullmatch(r"[0-9a-f]{40}", m3.group(4)):
                out.append(_f("info", i, "gha_unpinned", f"Outside action {m3.group(1)}/{m3.group(2)} is pinned by tag (@{m3.group(4)}), not by commit SHA.",
                              "To be safe, pin it to the full 40-character SHA (a tag can be moved)."))
        if lang == "dockerfile":
            if re.match(r"(?i)FROM\s+[\w./-]+(:latest)?\s*($|\s+AS)", x) and ":" not in x.split()[1]:
                out.append(_f("warn", i, "docker_latest", "The base image version is not fixed (latest).", "Pin a tag, such as node:20-slim / python:3.12-slim."))
            if re.match(r"(?i)(ENV|ARG)\s+\w*(PASS|SECRET|TOKEN|KEY)\w*\s*[= ]\s*\S+", x):
                out.append(_f("block", i, "docker_secret", "A secret is baked into the image.", "Pass it at runtime through env / a docker secret; BuildKit --secret."))
            if re.match(r"(?i)ADD\s+https?://", x):
                out.append(_f("warn", i, "docker_add_url", "ADD from a URL, with no checksum.", "RUN curl + sha256sum -c, or COPY."))
        if lang == "nginx":
            if re.search(r"ssl_protocols[^;]*\bTLSv1(\.1)?\b(?!\.[23])", x):
                out.append(_f("warn", i, "nginx_old_tls", "Old TLS 1.0 / 1.1 is on.", "ssl_protocols TLSv1.2 TLSv1.3;"))
            if re.search(r"\bautoindex\s+on\b", x):
                out.append(_f("warn", i, "nginx_autoindex", "Everyone will see the list of all files in the folder.", "autoindex off;"))
    if lang == "bash" and content.strip() and not re.search(r"^\s*set\s+-[a-z]*e[a-z]*u[a-z]*o\s+pipefail|^\s*set\s+-euo\s+pipefail", content, re.M):
        out.append(_f("warn", 1, "no_strict", "No set -euo pipefail: the script keeps going even after an error midway.",
                      "Add set -euo pipefail below the shebang."))
    if lang == "powershell" and content.strip() and "$ErrorActionPreference" not in content:
        out.append(_f("warn", 1, "ps_no_stop", "The script does not stop on an error.", "Add $ErrorActionPreference = 'Stop' at the top."))
    if lang == "yaml" and re.search(r"^on:", content, re.M):
        if "pull_request_target" in content and re.search(r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head\.(sha|ref)", content):
            out.append(_f("block", 1, "gha_prt_checkout", "pull_request_target with a checkout of the PR's code: a fork's code will run with your secrets.",
                          "Use pull_request, or run the PR code in a separate job without secrets."))
        if not re.search(r"^\s*permissions:", content, re.M):
            out.append(_f("info", 1, "gha_no_permissions", "No permissions: block (the token gets the default permissions).", "Add permissions: { contents: read } at the top."))
        if re.search(r"(deploy|production|prod)", content, re.I) and not re.search(r"^\s*environment:", content, re.M):
            out.append(_f("warn", 1, "gha_no_environment", "Deploy job without environment: (no approval / protection).",
                          "Add environment: production and set a required reviewer on that environment in GitHub."))
        if re.search(r"(deploy|production)", content, re.I) and "concurrency" not in content:
            out.append(_f("info", 1, "gha_no_concurrency", "Two deploys can run at the same time.", "concurrency: { group: deploy-production, cancel-in-progress: false }"))
    if lang == "dockerfile" and content.strip() and not re.search(r"^\s*USER\s+\S+", content, re.M | re.I):
        out.append(_f("warn", 1, "docker_root", "The container will run as the root user.", "Add USER node / USER 1000 at the end."))
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
        ("Before", ["All CI checks are green", "Read what changed (commits / PR)", "Is there a database migration? Backup taken first + migration read",
                   "New env variables / secrets added to production (not in chat)", "Rollback plan: the last good commit is known",
                   "A low-traffic time (not at night / Sunday morning when you are asleep)", "Team / support told"]),
        ("During the deploy", ["Your tap on Hoola's Deploy card", "Watch the workflow run (Hoola shows it)", "Health URL is green"]),
        ("After (15 min)", ["Anything new in the error logs (Hoola's clusters)?", "The main flows once by hand (login / order / payment page)",
                                "Response time is fine", "Release tag / note written"]),
    ]},
    "release": {"title": "App release checklist", "sections": [
        ("Before", ["Version + build number raised", "Changelog written", "All tests + lint are green", "Signing key is not in the repo (in a secret)",
                   "Privacy policy / data safety form updated if new data is collected"]),
        ("Release", ["Internal / beta track first", "Watch the crash rate for 24 hours", "Then all users"]),
    ]},
    "server_setup": {"title": "New server (hardening)", "sections": [
        ("Login", ["SSH by key only (PasswordAuthentication no)", "root login off (PermitRootLogin no)", "Your own sudo user", "fail2ban"]),
        ("Network", ["ufw: only 22 / 80 / 443", "Database port closed to the outside", "Admin panels through VPN / IP only"]),
        ("Updates + clock", ["unattended-upgrades", "timedatectl: NTP on (CERT-In: the clock must be synced with NTP)"]),
        ("Logs + backup", ["Logs kept 180 days, in India (CERT-In) - logrotate + compress", "Daily backup, with a copy off the server",
                           "Test a restore once a month"]),
        ("App", ["App runs as its own user, not root", ".env 600 permission", "Starts on reboot through pm2 startup / systemd", "HTTPS + auto renew (certbot)"]),
    ]},
    "incident": {"title": "Production is down (incident)", "sections": [
        ("Right now", ["What broke, since when (Hoola uptime / logs)", "When was the last deploy? If in doubt, use the rollback card", "A one-line update to users / the team"]),
        ("Data leak / hacking suspected", ["IT Helpdesk > Security: check the CERT-In 6-hour rule", "Do not delete the evidence (logs)", "Rotate passwords / keys"]),
        ("After", ["Root cause (blameless)", "What will change so it does not happen again", "Runbook update"]),
    ]},
    "backup_restore": {"title": "Backup restore test", "sections": [
        ("Test", ["A new empty server / folder", "Restore from the latest backup", "Start the app and check the data", "Write down how long it took (RTO)",
                  "How old the data was (RPO)"])]},
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
        items.append({"id": f"c{n}", "section": "Your rules", "text": t[:200], "done": False, "by": ""})
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
        lines.append(f"No production deploy seen in the last {days} days.")
    else:
        lines.append(f"{days} days: {len(ok)} successful deploys ({per_week} a week), {len(failed)} failed / rolled back.")
        if out["lead_time_h"] is not None:
            lines.append(f"Median time from commit to production: ~{out['lead_time_h']} hours.")
        if out["change_failure_pct"] is not None:
            lines.append(f"About {out['change_failure_pct']:.0f} in every 100 changes broke something.")
        if out["recovery_h"] is not None:
            lines.append(f"Time to recover after a broken deploy: ~{out['recovery_h']} hours.")
        if out["rework_pct"]:
            lines.append(f"{out['rework_pct']:.0f}% of deploys were unplanned (hotfix / revert).")
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
