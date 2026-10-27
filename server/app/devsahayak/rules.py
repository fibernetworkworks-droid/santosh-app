"""Developer Sahayak rules: everything decided by CODE, not by the model.

* secrets in a diff (key shapes from app/scrub.py + more: private keys, passwords in code, connection strings, service-account JSON,
  .env files, Indian personal data like Aadhaar / PAN / card numbers) -> the change is REFUSED, nothing is pushed;
* paths Hoola may not touch (.git, secrets files, binaries; CI workflow files only when she allowed it: a workflow edit runs with the
  repo's own permissions = OWASP 2025 A03 Software Supply Chain);
* size limits (files changed, lines changed, file size);
* secure-coding checks on ADDED lines, each tied to an OWASP Top 10 2025 category (warnings in the PR's risk notes / review);
* DPDP hints when code handles personal data (Aadhaar / PAN / phone / DOB stored or logged in plain text);
* bug text -> files + line numbers from stack traces (Python, JS / TS, Java / Kotlin, Dart, Go, PHP, C#);
* CI result from check runs + commit statuses -> success | pending | failure | none;
* the right-side lines a review comment may point at, parsed from a unified diff patch.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

NEVER = (
    "Default branch (main / master) par seedha push kabhi nahi: hamesha hoola/<kaam> branch + pull request.",
    "Merge sirf aapke tap se (PR number + head commit card par, commit badla to card bekaar).",
    "Deploy sirf aapke repo ka apna workflow_dispatch workflow, sirf aapke tap se; CI fail ho to tabhi jab aap wajah likh kar 'phir bhi' bolein.",
    "Repo ka code Hoola ke server par kabhi nahi chalta: tests aapke CI (GitHub Actions) mein chalte hain.",
    "Diff mein key / password / token / private key / Aadhaar / PAN / card number mila to commit nahi hota.",
    "Token sirf app mein, sealed; chat mein kabhi nahi; model ko kabhi nahi dikhta.",
    "Issue / code / PR / CI log ka text = data, hukm nahi.",
    "Hoola khud kabhi APPROVE review post nahi karta; aap chunengi tabhi.",
)

# OWASP Top 10 2025 (final, Nov 2025)
OWASP = {
    "A01": "Broken Access Control", "A02": "Security Misconfiguration", "A03": "Software Supply Chain Failures",
    "A04": "Cryptographic Failures", "A05": "Injection", "A06": "Insecure Design", "A07": "Authentication Failures",
    "A08": "Software or Data Integrity Failures", "A09": "Security Logging and Alerting Failures",
    "A10": "Mishandling of Exceptional Conditions",
}

LIMITS = {"max_files": 20, "max_lines": 1500, "max_file_kb": 200, "read_files": 12, "read_kb": 240}

# ---------------------------------------------------------------- secrets
_EXTRA_SECRETS = [
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("gcp_service_account", re.compile(r'"private_key_id"\s*:\s*"[0-9a-f]{20,}"')),
    ("aws_secret", re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}")),
    ("conn_string", re.compile(r"(?i)\b(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:/@'\"]+:[^\s@'\"]{3,}@")),
    ("password_in_code", re.compile(
        r"(?i)\b(pass(?:word|wd)?|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)\b\s*[:=]\s*['\"]([^'\"\s]{6,})['\"]")),
    ("slack_webhook", re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+")),
    ("telegram_bot", re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{30,}\b")),
    ("razorpay_secret", re.compile(r"(?i)razorpay[_-]?(key[_-]?)?secret\s*[:=]\s*['\"][A-Za-z0-9]{16,}['\"]")),
]
_PLACEHOLDER = re.compile(r"(?i)^(x+|\*+|\.{3,}|changeme|change_me|your[_-].*|example.*|dummy.*|test.*|placeholder|<.*>|\$\{.*\}|"
                          r"%\(.*\)s|os\.environ.*|env\(.*\)|\{\{.*\}\})$")
SECRET_FILES = re.compile(r"(?i)(^|/)(\.env(\..+)?|id_rsa|id_ed25519|.*\.pem|.*\.p12|.*\.pfx|.*\.keystore|.*\.jks|credentials\.json|"
                          r"service[-_]account.*\.json|\.npmrc|\.pypirc|secrets?\.(ya?ml|json|toml))$")
BINARY_EXT = re.compile(r"(?i)\.(png|jpe?g|gif|webp|ico|pdf|zip|gz|tgz|jar|apk|aab|so|dll|exe|bin|class|pyc|woff2?|ttf|otf|mp[34]|mov)$")


def secrets_in(text: str) -> list[dict[str, Any]]:
    """Every secret-looking thing in the text (kind + line). Placeholders like 'xxx' / ${VAR} / os.environ are not secrets."""
    from .. import scrub
    out: list[dict[str, Any]] = []
    for i, line in enumerate((text or "").splitlines(), 1):
        if len(line) > 4000:
            line = line[:4000]
        hit = ""
        for p in scrub.PATTERNS:
            if p.search(line):
                hit = "key"
                break
        if not hit:
            for name, p in _EXTRA_SECRETS:
                m = p.search(line)
                if not m:
                    continue
                if name == "password_in_code" and _PLACEHOLDER.match(m.group(2) or ""):
                    continue
                hit = name
                break
        if not hit:
            try:
                from .. import pii
                kinds = [k for k in pii.find(line) if k in ("aadhaar", "pan", "card", "cvv", "bank_account")]
            except Exception:
                kinds = []
            if kinds:
                hit = "personal_data:" + kinds[0]
        if hit:
            out.append({"line": i, "kind": hit})
    return out


def path_problem(path: str, allow_workflows: bool = False) -> str:
    p = (path or "").strip()
    if not p or p.startswith("/") or "\\" in p or any(part in ("..", ".git") for part in p.split("/")) or "\x00" in p:
        return "galat path"
    if len(p) > 300:
        return "path bahut lamba"
    if SECRET_FILES.search(p):
        return "secret / key file: Hoola isse kabhi nahi chhoota"
    if BINARY_EXT.search(p):
        return "binary file: Hoola sirf text code badalta hai"
    if p.startswith(".github/workflows/") and not allow_workflows:
        return "CI workflow file: Niyam mein 'workflow badal sakta hai' on kijiye (supply chain risk, OWASP A03)"
    return ""


# ---------------------------------------------------------------- secure coding (added lines)
_CHECKS: list[tuple[str, str, str, re.Pattern]] = [
    ("sql_concat", "A05", "SQL string jod kar ban raha hai: parameter / placeholder use kijiye",
     re.compile(r"(?i)(execute|executemany|raw|query|rawQuery|prepare)\s*\(\s*(f['\"]|['\"][^'\"]*\b(select|insert|update|delete)\b[^'\"]*['\"]\s*(\+|%|\.format))")),
    ("eval", "A05", "eval / exec: bahar ka text code ban sakta hai",
     re.compile(r"(?<![\w.])(eval|exec)\s*\(|new Function\s*\(")),
    ("shell", "A05", "shell=True / os.system: command injection ka khatra",
     re.compile(r"shell\s*=\s*True|os\.system\s*\(|child_process\.exec\s*\(|Runtime\.getRuntime\(\)\.exec")),
    ("deserialize", "A08", "pickle / unsafe YAML / ObjectInputStream: bharose ke bina data load mat kijiye",
     re.compile(r"pickle\.loads?\s*\(|yaml\.load\s*\((?![^)]*SafeLoader)|ObjectInputStream|marshal\.loads")),
    ("tls_off", "A04", "TLS check band (verify=False / trustAll): beech mein koi padh sakta hai",
     re.compile(r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|InsecureSkipVerify\s*:\s*true|TrustAll|ALLOW_ALL_HOSTNAME|badCertificateCallback")),
    ("weak_hash", "A04", "MD5 / SHA1 password ya token ke liye kamzor: bcrypt / argon2 / scrypt",
     re.compile(r"(?i)(md5|sha1)\s*\(.*(pass|pwd|token|secret)|hashlib\.(md5|sha1)\s*\(")),
    ("weak_random", "A04", "token / OTP ke liye random() kamzor: secrets / SecureRandom",
     re.compile(r"(?i)(token|otp|secret|session|nonce)\w*\s*=\s*.*\b(Math\.random|random\.(random|randint|choice)|new Random\()")),
    ("cors_any", "A02", "CORS '*' sab ke liye khula (cookie / login ke saath khatarnak)",
     re.compile(r"(?i)(allow_origins\s*=\s*\[\s*['\"]\*['\"]|Access-Control-Allow-Origin['\"]?\s*[:,]\s*['\"]\*|cors\(\s*\)|origin\s*:\s*['\"]\*['\"])")),
    ("debug_on", "A02", "DEBUG on: production mein error ke saath andar ki jaankari dikhti hai",
     re.compile(r"(?i)\bDEBUG\s*=\s*True\b|app\.run\([^)]*debug\s*=\s*True|android:debuggable\s*=\s*\"true\"")),
    ("cleartext", "A04", "http:// (bina TLS) ya cleartext traffic on",
     re.compile(r"usesCleartextTraffic\s*=\s*\"true\"|['\"]http://(?!localhost|127\.0\.0\.1|10\.0\.2\.2|schemas\.|www\.w3\.org)[\w.-]+")),
    ("html_inject", "A05", "innerHTML / dangerouslySetInnerHTML / v-html / |safe: XSS ka khatra",
     re.compile(r"\.innerHTML\s*=|dangerouslySetInnerHTML|v-html=|\|\s*safe\b|mark_safe\s*\(|Html\.fromHtml")),
    ("webview_js", "A05", "WebView mein JavaScript interface: sirf apne pages ke liye",
     re.compile(r"addJavascriptInterface|setJavaScriptEnabled\s*\(\s*true")),
    ("jwt_none", "A07", "JWT bina verify / 'none' algorithm",
     re.compile(r"(?i)verify_signature['\"]?\s*:\s*False|algorithms\s*=\s*\[\s*['\"]none['\"]|jwt\.decode\([^)]*verify\s*=\s*False")),
    ("auth_off", "A01", "login / permission check hata diya lagta hai",
     re.compile(r"(?i)#\s*@?(login_required|permission_required|requires_auth)|//\s*@?(PreAuthorize|Secured|authorize)|AllowAnonymous|permitAll\(\)")),
    ("swallow", "A10", "except / catch jo galti chupa deta hai (khaali ya sirf pass)",
     re.compile(r"except\s*(Exception)?\s*:\s*pass\b|catch\s*\([^)]*\)\s*\{\s*\}|except\s*:\s*$")),
    ("log_secret", "A09", "log / print mein password / token / OTP / Aadhaar",
     re.compile(r"(?i)(log(ger)?\.\w+|print|console\.log|Log\.[dievw]|println)\s*\(.*\b(password|passwd|token|otp|secret|aadhaar|aadhar|pan_?no|cvv)\b")),
    ("world_readable", "A01", "MODE_WORLD_READABLE / chmod 777: sab padh / likh sakte hain",
     re.compile(r"MODE_WORLD_(READABLE|WRITEABLE)|chmod\s+(-R\s+)?777|0o?777\b")),
]
_DPDP = re.compile(r"(?i)\b(aadhaar|aadhar|pan_?(no|number|card)|date_?of_?birth|dob|mobile|phone|email|address|bank_?account|ifsc|"
                   r"health|diagnosis|caste|religion)\w*\s*(=|:)\s*")
_ENC = re.compile(r"(?i)(encrypt|hash|mask|seal|fernet|aes|kms|tokeni[sz]e|redact|bcrypt|argon)")


def code_checks(added: str, path: str = "") -> list[dict[str, Any]]:
    """Secure-coding warnings on ADDED lines only. Warnings, not verdicts: the PR's risk notes / review tell her and her team."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    is_test = bool(re.search(r"(?i)(^|/)(tests?|__tests__|spec)/|_test\.|\.test\.|\.spec\.|test_", path or ""))
    for i, line in enumerate((added or "").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith(("#!", "* ")):
            continue
        for cid, owasp, say, p in _CHECKS:
            if is_test and cid in ("cleartext", "weak_random", "debug_on", "tls_off"):
                continue
            if p.search(line) and (cid, i) not in seen:
                seen.add((cid, i))
                out.append({"id": cid, "owasp": owasp, "owasp_name": OWASP[owasp], "line": i, "say": say, "path": path})
        if _DPDP.search(line) and not _ENC.search(line) and re.search(r"(?i)(save|insert|store|column|Column|log|print|write|db\.|\.create\()", line):
            out.append({"id": "dpdp_plain", "owasp": "A04", "owasp_name": OWASP["A04"], "line": i, "path": path,
                        "say": "Personal data (Aadhaar / PAN / phone / DOB...) plain mein save / log ho raha lagta hai: DPDP Rules 2025 Rule 6 "
                               "(encryption / masking, access control, 1 saal logs; mid-May 2027 se lagoo) ke hisaab se mask / encrypt kijiye"})
    return out


# ---------------------------------------------------------------- diffs
def changed_lines(old: str, new: str) -> tuple[int, int, str]:
    """(added, removed, added_text) by a line diff."""
    import difflib
    add, rem, added = 0, 0, []
    for ln in difflib.unified_diff((old or "").splitlines(), (new or "").splitlines(), lineterm="", n=0):
        if ln.startswith("+++") or ln.startswith("---") or ln.startswith("@@"):
            continue
        if ln.startswith("+"):
            add += 1
            added.append(ln[1:])
        elif ln.startswith("-"):
            rem += 1
    return add, rem, "\n".join(added)


def unified(path: str, old: str, new: str, context: int = 2) -> str:
    import difflib
    return "\n".join(difflib.unified_diff((old or "").splitlines(), (new or "").splitlines(), f"a/{path}", f"b/{path}",
                                          lineterm="", n=context))


def patch_added(patch: str) -> list[tuple[int, str]]:
    """(right-side line number, text) for every '+' line of a GitHub file patch."""
    out: list[tuple[int, str]] = []
    right = 0
    for ln in (patch or "").splitlines():
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", ln)
        if m:
            right = int(m.group(1))
            continue
        if ln.startswith("+") and not ln.startswith("+++"):
            out.append((right, ln[1:]))
            right += 1
        elif ln.startswith("-") and not ln.startswith("---"):
            continue
        elif ln.startswith("\\"):
            continue
        else:
            right += 1
    return out


def patch_lines(patch: str) -> set[int]:
    """Right-side lines that exist in the diff (added + context): a review comment may only point at these."""
    ok: set[int] = set()
    right = 0
    for ln in (patch or "").splitlines():
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", ln)
        if m:
            right = int(m.group(1))
            continue
        if ln.startswith("-") or ln.startswith("\\"):
            continue
        if right:
            ok.add(right)
            right += 1
    return ok


# ---------------------------------------------------------------- bug text
_TRACE = [
    re.compile(r'File "(?P<f>[^"]+)", line (?P<l>\d+)'),                                     # Python
    re.compile(r"at (?:[\w$.<>\[\] ]+ )?\(?(?P<f>[\w@./~-]+\.(?:m?[jt]sx?|vue|svelte)):(?P<l>\d+)(?::\d+)?\)?"),  # JS / TS
    re.compile(r"at [\w$.<>]+\((?P<f>[\w$-]+\.(?:java|kt|scala)):(?P<l>\d+)\)"),              # Java / Kotlin
    re.compile(r"\((?:package:[\w_]+/|file://)?(?P<f>[\w./-]+\.dart):(?P<l>\d+)(?::\d+)?\)"),  # Dart / Flutter
    re.compile(r"(?P<f>[\w./-]+\.(?:go|rs|php|rb|cs|cpp|c|h|swift|py)):(?P<l>\d+)"),          # Go / Rust / PHP / Ruby / C# ...
    re.compile(r"(?P<f>[\w./-]+\.php) on line (?P<l>\d+)"),
]
_ERR = re.compile(r"\b([A-Z][A-Za-z]*(?:Error|Exception|Exit|Fault|Panic))\b|\b(panic|segfault|undefined is not|cannot read propert\w*|"
                  r"null ?pointer|NoneType|KeyError|IndexError|TypeError|ValueError|404|500|502|timeout)\b", re.I)
_SKIP_TRACE = re.compile(r"(site-packages|node_modules|/usr/lib|<frozen|dart:|flutter/packages|java\.base|kotlin\.|android\.os|"
                         r"internal/|webpack|/lib/python)")
_STOP = set("the a an and or to of in on at is are was were be it this that for with from by not no yes kya hai nahi ho raha "
            "rahi rahe tha thi ka ki ke ko se mein me par aur bhi ek do jab tab error bug issue fix please kar karo karna "
            "app page code file line".split())


def trace(text: str) -> dict[str, Any]:
    """Files + lines from a stack trace / log, the error type, and search words (data only; links never opened)."""
    files: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for p in _TRACE:
        for m in p.finditer(text or ""):
            f, ln = m.group("f"), int(m.group("l"))
            if _SKIP_TRACE.search(f):
                continue
            f = re.sub(r"^(\./|/app/|/srv/[^/]+/|/home/[^/]+/[^/]+/|/workspace/|webpack:///|file:///)", "", f)
            if (f, ln) in seen:
                continue
            seen.add((f, ln))
            files.append({"file": f, "line": ln})
    errs = []
    for m in _ERR.finditer(text or ""):
        e = m.group(0)
        if e not in errs:
            errs.append(e)
    words = []
    for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", text or ""):
        lw = w.lower()
        if lw in _STOP or w in errs or len(words) >= 8 or lw in (x.lower() for x in words):
            continue
        if "_" in w or re.search(r"[a-z][A-Z]", w):          # identifiers first
            words.insert(0, w)
        else:
            words.append(w)
    return {"files": files[:15], "errors": errs[:5], "words": words[:8]}


def match_path(tree_paths: list[str], f: str) -> str:
    """A trace's file name -> the real path in the repo (longest matching suffix)."""
    f = f.strip("/")
    if f in tree_paths:
        return f
    parts = f.split("/")
    for k in range(len(parts) - 1, -1, -1):
        suf = "/".join(parts[k:])
        hits = [p for p in tree_paths if p == suf or p.endswith("/" + suf)]
        if len(hits) == 1:
            return hits[0]
        if hits and k == 0:
            return sorted(hits, key=len)[0]
    return ""


# ---------------------------------------------------------------- CI
def ci_state(check_runs: list[dict[str, Any]], statuses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    failed, pending, passed, rows = [], [], [], []
    for c in check_runs or []:
        name = str(c.get("name") or "check")
        st, con = str(c.get("status") or ""), str(c.get("conclusion") or "")
        if st != "completed":
            pending.append(name)
            state = "pending"
        elif con in ("success", "neutral", "skipped"):
            passed.append(name)
            state = "success"
        else:
            failed.append(name)
            state = "failure"
        rows.append({"name": name, "state": state, "conclusion": con, "id": c.get("id"), "url": c.get("html_url") or "",
                     "title": str(((c.get("output") or {}).get("title")) or "")[:200]})
    for s in statuses or []:
        name = str(s.get("context") or "status")
        st = str(s.get("state") or "")
        state = {"success": "success", "pending": "pending"}.get(st, "failure")
        (passed if state == "success" else pending if state == "pending" else failed).append(name)
        rows.append({"name": name, "state": state, "conclusion": st, "id": None, "url": s.get("target_url") or "",
                     "title": str(s.get("description") or "")[:200]})
    if failed:
        state = "failure"
    elif pending:
        state = "pending"
    elif passed:
        state = "success"
    else:
        state = "none"
    say = {"failure": f"CI fail: {', '.join(failed[:4])}", "pending": f"CI chal raha hai ({len(pending)} baaki)",
           "success": f"CI pass ({len(passed)} checks)", "none": "Is commit par koi CI check nahi mila"}[state]
    return {"state": state, "failed": failed, "pending": pending, "passed": passed, "rows": rows[:40], "say": say}


# ---------------------------------------------------------------- names, hashes
def slug(text: str, n: int = 32) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:n].strip("-") or "kaam")


def card_hash(*parts: Any) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:24]


def has_dispatch(workflow_yaml: str) -> bool:
    """The workflow file can be started by hand (on: workflow_dispatch)."""
    t = workflow_yaml or ""
    return bool(re.search(r"(?m)^\s*workflow_dispatch\s*:|on\s*:\s*\[?[^\n]*\bworkflow_dispatch\b|^\s*-\s*workflow_dispatch\s*$", t))


def dispatch_inputs(workflow_yaml: str) -> list[str]:
    m = re.search(r"(?ms)workflow_dispatch\s*:\s*\n(\s+)inputs\s*:\s*\n(.*?)(?=^\S|^\1\S|\Z)", workflow_yaml or "")
    if not m:
        return []
    return re.findall(r"(?m)^\s{%d,}([A-Za-z_][\w-]*)\s*:\s*$" % (len(m.group(1)) + 1), m.group(2))[:25]


def looks_token(text: str) -> bool:
    return bool(re.search(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b", text or ""))
