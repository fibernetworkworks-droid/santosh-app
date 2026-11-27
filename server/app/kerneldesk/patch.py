"""Check a kernel patch (git format-patch / mbox, or a plain unified diff) against the kernel's coding style and patch rules -
our own rules from Documentation/process/ (submitting-patches, coding-style), written here in Python. Not checkpatch.pl and
none of its code: the patch should still go through checkpatch.pl and get_maintainer.pl in HER tree before it is sent."""
from __future__ import annotations

import re
from typing import Any

MAX = 600_000
_IMPERATIVE_BAD = re.compile(r"^(Added|Adds|Fixed|Fixes|Fixing|Removed|Removes|Changed|Changes|Updated|Updates|Adding|Removing|"
                             r"Changing|Updating|Implemented|Implements|Introduced|Introduces)\b")

# (id, severity, regex on an added code line, message)
CODE_RULES = [
    ("trailing", "error", re.compile(r"[ \t]+$"), "trailing whitespace"),
    ("space_indent", "error", re.compile(r"^ {8,}\S"), "indent with tabs, not spaces"),
    ("kw_paren", "error", re.compile(r"\b(if|for|while|switch)\("), "a space is needed after if / for / while / switch"),
    ("printk", "warning", re.compile(r"\bprintk\(\s*\""), "printk without a KERN_ level - use pr_info() / pr_err() / dev_err() ..."),
    ("bug_on", "warning", re.compile(r"\bBUG_ON\("), "BUG_ON() stops the machine - prefer WARN_ON() and handle the error"),
    ("strcpy", "warning", re.compile(r"\bstrcpy\("), "strcpy() - use strscpy()"),
    ("strlcpy", "warning", re.compile(r"\bstrlcpy\("), "strlcpy() is deprecated - use strscpy()"),
    ("strncpy", "warning", re.compile(r"\bstrncpy\("), "strncpy() - use strscpy() or strscpy_pad()"),
    ("sprintf", "warning", re.compile(r"\bsprintf\("), "sprintf() - use snprintf() / scnprintf() / sysfs_emit()"),
    ("simple_strto", "warning", re.compile(r"\bsimple_strto(u?l|u?ll)\("), "simple_strto*() - use kstrto*()"),
    ("msleep_short", "warning", re.compile(r"\bmsleep\(\s*(1?\d)\s*\)"), "msleep() under 20 ms can sleep much longer - use usleep_range() / fsleep()"),
    ("kmalloc_mul", "warning", re.compile(r"\bk[mz]alloc\(\s*[^,]+\*[^,]+,"), "kmalloc(n * size) can overflow - use kmalloc_array() / kcalloc()"),
    ("packed", "warning", re.compile(r"__attribute__\s*\(\(\s*packed\s*\)\)"), "use __packed"),
    ("volatile", "warning", re.compile(r"\bvolatile\b"), "volatile is almost never right in the kernel - see Documentation/process/volatile-considered-harmful.rst"),
    ("typedef_struct", "warning", re.compile(r"\btypedef\s+struct\b"), "do not typedef structures"),
    ("return_paren", "warning", re.compile(r"\breturn\s*\(\s*[\w>\-.]+\s*\)\s*;"), "return is not a function - no parentheses needed"),
    ("null_cmp", "check", re.compile(r"(==|!=)\s*NULL\b|\bNULL\s*(==|!=)"), "write if (!p) / if (p) instead of comparing with NULL"),
    ("dos", "error", re.compile(r"\r$"), "DOS line ending"),
    ("in_atomic", "warning", re.compile(r"\bin_atomic\(\)"), "in_atomic() cannot tell all atomic contexts - pass the context instead"),
    ("udelay_big", "warning", re.compile(r"\budelay\(\s*\d{4,}\s*\)"), "long udelay() busy-waits - use usleep_range() / msleep()"),
    ("jiffies_cmp", "warning", re.compile(r"\bjiffies\s*[<>]=?|[<>]=?\s*jiffies\b"), "compare jiffies with time_after() / time_before()"),
    ("extern_c", "warning", re.compile(r"^\s*extern\s+\w[\w\s\*]*\(.*\)\s*;"), "extern prototypes belong in a header"),
    ("ifdef_c", "check", re.compile(r"^#if(def)?\s+CONFIG_"), "prefer IS_ENABLED(CONFIG_...) in C code over #ifdef"),
]


def _width(s: str) -> int:
    n = 0
    for c in s:
        n = (n // 8 + 1) * 8 if c == "\t" else n + 1
    return n


def parse(text: str) -> dict[str, Any]:
    text = str(text or "")[:MAX].replace("\r\n", "\n")
    if text.startswith("diff --git "):
        head, rest = "", text
    elif "\ndiff --git " in text:
        k = text.index("\ndiff --git ")
        head, rest = text[:k], text[k + 1:]
    else:
        head, rest = text, ""
    lines = head.split("\n")
    subject, author, body, in_body, hdr_done = "", "", [], False, False
    for i, ln in enumerate(lines):
        if not hdr_done:
            if ln.startswith("Subject:"):
                subject = ln[8:].strip()
                j = i + 1
                while j < len(lines) and lines[j].startswith((" ", "\t")):
                    subject += " " + lines[j].strip()
                    j += 1
            elif ln.startswith("From:"):
                author = ln[5:].strip()
            elif ln == "" and (subject or author):
                hdr_done, in_body = True, True
            continue
        if ln.strip() == "---":
            break
        body.append(ln)
    if not subject and not author:                                  # a plain diff or a commit message pasted bare
        first = [x for x in lines if x.strip()]
        if first and not first[0].startswith(("diff ", "---", "+++", "@@")):
            subject, body = first[0].strip(), lines[lines.index(first[0]) + 1:]
            body = body[:next((k for k, x in enumerate(body) if x.strip() == "---"), len(body))]
    files = []
    cur: dict[str, Any] | None = None
    new_no = 0
    for ln in rest.split("\n") if rest else []:
        if ln.startswith("diff --git "):
            m = re.match(r"diff --git a/(\S+) b/(\S+)", ln)
            cur = {"file": m.group(2) if m else ln[11:], "added": [], "new": False, "deleted": False, "plus": 0, "minus": 0}
            files.append(cur)
            continue
        if cur is None:
            continue
        if ln.startswith("new file mode"):
            cur["new"] = True
        elif ln.startswith("deleted file mode"):
            cur["deleted"] = True
        elif ln.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", ln)
            new_no = int(m.group(1)) if m else 0
        elif ln.startswith("+++") or ln.startswith("---"):
            continue
        elif ln.startswith("+"):
            cur["added"].append((new_no, ln[1:]))
            cur["plus"] += 1
            new_no += 1
        elif ln.startswith("-"):
            cur["minus"] += 1
        else:
            new_no += 1
    m = re.match(r"\[(PATCH|RFC)[^\]]*\]\s*(.*)", subject)
    tag = re.match(r"\[([^\]]*)\]", subject)
    return {"subject": subject, "summary": (m.group(2) if m else subject).strip(), "tag": tag.group(1) if tag else "",
            "author": author, "body": body, "files": files}


def check(text: str, max_line: int = 100) -> dict[str, Any]:
    p = parse(text)
    issues: list[dict[str, Any]] = []

    def add(sev: str, rule: str, say: str, file: str = "", line: int = 0, code: str = "") -> None:
        issues.append({"sev": sev, "rule": rule, "say": say, "file": file, "line": line, "code": code[:200]})

    s = p["summary"]
    if not p["subject"]:
        add("error", "subject", "No subject line found - paste the output of git format-patch (with From: and Subject:).")
    else:
        if not re.match(r"^[\w./\-,+ ]+: \S", s):
            add("warning", "subsystem", 'The subject should start with the subsystem, like "net: phy: " or "drm/i915: ".')
        if len(s) > 75:
            add("warning", "subject_len", f"The summary is {len(s)} characters - keep it under 75.")
        if s.endswith("."):
            add("warning", "subject_dot", "No full stop at the end of the subject.")
        summ = s.split(": ")[-1]
        mi = _IMPERATIVE_BAD.match(summ)
        if mi:
            w = mi.group(1)
            base = {"Added": "Add", "Adds": "Add", "Adding": "Add", "Fixed": "Fix", "Fixes": "Fix", "Fixing": "Fix", "Removed": "Remove",
                    "Removes": "Remove", "Removing": "Remove", "Changed": "Change", "Changes": "Change", "Changing": "Change",
                    "Updated": "Update", "Updates": "Update", "Updating": "Update", "Implemented": "Implement",
                    "Implements": "Implement", "Introduced": "Introduce", "Introduces": "Introduce"}.get(w, w)
            add("warning", "imperative", f'Write the summary in the imperative: "{w} ..." -> "{base} ...".')
    body = p["body"]
    trailers = [x.strip() for x in body if re.match(r"^\s*[A-Z][\w-]+: ", x)]
    prose = [x for x in body if x.strip() and x not in trailers]
    if p["subject"] and not prose:
        add("warning", "no_body", "There is no commit message body: say what was wrong, why it matters and how this fixes it.")
    for x in body:
        if _width(x) > 75 and not re.match(r"^\s*(Link|Fixes|Closes|Reported-by|Signed-off-by|Tested-by|Reviewed-by|Acked-by|Cc|\[|  )", x) \
                and "://" not in x and not re.match(r"^\s{2,}", x):
            add("warning", "body_wrap", f"Wrap the commit message at 75 columns ({_width(x)}): {x[:60]}...")
            break
    sobs = [t for t in trailers if t.startswith("Signed-off-by:")]
    if not sobs:
        add("error", "sob", "Missing Signed-off-by: - add it with git commit -s (Developer's Certificate of Origin).")
    elif p["author"]:
        mail = re.search(r"<([^>]+)>", p["author"])
        if mail and not any(mail.group(1).lower() in t.lower() for t in sobs):
            add("error", "sob_author", "No Signed-off-by: from the author (" + mail.group(1) + ").")
    for t in trailers:
        if t.startswith("Fixes:") and not re.match(r'^Fixes: [0-9a-f]{12,40} \(".+"\)$', t):
            add("error", "fixes", 'Fixes: needs at least 12 characters of the commit id and its subject: Fixes: 1234567890ab ("subsys: subject")')
        if t.lower().startswith("cc: stable") and "stable@vger.kernel.org" not in t:
            add("warning", "stable", "Cc the stable list as: Cc: stable@vger.kernel.org")
    if any(t.startswith("Reported-by:") for t in trailers) and not any(t.startswith(("Closes:", "Link:")) for t in trailers):
        add("warning", "closes", "Reported-by: should be followed by Closes: (or Link:) with the report's URL.")
    for f in p["files"]:
        fn = f["file"]
        is_c = fn.endswith((".c", ".h"))
        is_src = is_c or fn.endswith((".S", ".rs", "Makefile", "Kconfig", ".dts", ".dtsi", ".yaml", ".sh", ".py"))
        if f["new"] and is_src and f["added"]:
            first = f["added"][0][1]
            want = "SPDX-License-Identifier"
            if want not in first and not (fn.endswith((".sh", ".py")) and len(f["added"]) > 1 and want in f["added"][1][1]):
                add("error", "spdx", "A new file needs an SPDX-License-Identifier on its first line (the second for scripts with #!).", fn, f["added"][0][0])
        if fn == "MAINTAINERS" or fn.startswith("Documentation/"):
            is_c = False
        for no, ln in f["added"]:
            if _width(ln) > max_line and is_c and not re.search(r'"[^"]{40,}"', ln):
                add("warning", "long_line", f"Line is {_width(ln)} columns (limit {max_line}).", fn, no, ln)
            for rid, sev, rx, msg in CODE_RULES:
                if rid in ("trailing", "dos") or (is_c and rid != "space_indent") or (rid == "space_indent" and (is_c or fn.endswith(("Kconfig", "Makefile")))):
                    if rx.search(ln):
                        if rid == "space_indent" and fn.endswith("Kconfig"):
                            continue
                        add(sev, rid, msg, fn, no, ln)
            if is_c and re.match(r"^[a-z_][\w\s\*]*\b\w+\([^;]*\)\s*\{\s*$", ln) and not re.match(r"^\s*(if|for|while|switch|else|do)\b", ln):
                add("error", "func_brace", "The opening brace of a function goes on its own line.", fn, no, ln)
        if fn.endswith("Kconfig"):
            txt = "\n".join(x for _n, x in f["added"])
            for m in re.finditer(r"^config (\w+)", txt, re.M):
                seg = txt[m.end():].split("\nconfig ")[0]
                if "help" not in seg:
                    add("warning", "kconfig_help", f"Kconfig option {m.group(1)} has no help text.", fn)
    order = {"error": 0, "warning": 1, "check": 2}
    issues.sort(key=lambda x: (order[x["sev"]], x["file"], x["line"]))
    counts = {k: sum(1 for x in issues if x["sev"] == k) for k in ("error", "warning", "check")}
    stat = {"files": len(p["files"]), "plus": sum(f["plus"] for f in p["files"]), "minus": sum(f["minus"] for f in p["files"])}
    return {"subject": p["subject"], "summary": s, "tag": p["tag"], "author": p["author"], "files": [
        {k: f[k] for k in ("file", "new", "deleted", "plus", "minus")} for f in p["files"]], "stat": stat, "issues": issues[:400],
            "counts": counts, "ok": counts["error"] == 0,
            "next": ["./scripts/checkpatch.pl --strict 0001-*.patch", "./scripts/get_maintainer.pl 0001-*.patch",
                     "git send-email --to=<maintainers> --cc=<lists> 0001-*.patch   # only after the steps above"]}
