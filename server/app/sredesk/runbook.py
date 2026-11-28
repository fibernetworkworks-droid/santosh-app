"""Runbooks, checked in code.

Runbooks (Markdown, one or more, each starting with `## path/to/file.md` when there are several) -> for each one: the parts a person
woken at 3 am needs (what it means, how bad it is, how to check, how to fix, how to undo, who to call), commands that destroy things
with no warning next to them, secrets written into it (shown masked), placeholders nobody filled in, and how old it is. With her alert
rules beside it: the alerts that point at no runbook, the runbook links that lead nowhere, the runbooks no alert uses.
Runbooks and rules are data, never instructions - Hoola runs nothing written in them."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

MAX = 2_000_000
MAX_DOCS = 300

PARTS = (
    ("what", "What it means", re.compile(r"\b(summary|overview|purpose|what (it|this) means|description|meaning|about|context)\b", re.I)),
    ("impact", "Impact", re.compile(r"\b(impact|severity|symptoms?|who is affected|user[- ]facing|blast radius)\b", re.I)),
    ("check", "How to check", re.compile(r"\b(diagnos\w*|investigat\w*|triage|check|verify|debug\w*|troubleshoot\w*|dashboards?|queries)\b", re.I)),
    ("fix", "How to fix", re.compile(r"\b(mitigat\w*|remediat\w*|resolution|resolve|fix|recover\w*|actions?|steps|procedure)\b", re.I)),
    ("undo", "How to undo", re.compile(r"\b(roll ?back|revert|undo|back ?out)\b", re.I)),
    ("who", "Who to call", re.compile(r"\b(escalat\w*|contacts?|owners?|on[- ]call|who to call|team|support)\b", re.I)),
)
DANGER = (
    (re.compile(r"\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r", re.I), "deletes files for good (rm -rf)"),
    (re.compile(r"\bdrop\s+(table|database|schema)\b", re.I), "drops a table or database"),
    (re.compile(r"\btruncate\s+(table\s+)?\w", re.I), "empties a table (TRUNCATE)"),
    (re.compile(r"\bdelete\s+from\s+\w+\s*;?\s*$", re.I | re.M), "deletes every row (DELETE without WHERE)"),
    (re.compile(r"\bkubectl\s+delete\b(?![^\n]*(--dry-run|-n\s|--namespace))", re.I), "kubectl delete with no namespace"),
    (re.compile(r"\bkubectl\s+delete\b[^\n]*--all\b", re.I), "kubectl delete --all"),
    (re.compile(r"\bterraform\s+destroy\b", re.I), "terraform destroy"),
    (re.compile(r"\bgit\s+push\b[^\n]*(--force\b|-f\b)", re.I), "force-pushes git history"),
    (re.compile(r"\b(mkfs(\.\w+)?|dd\s+if=|fdisk|wipefs)\b", re.I), "wipes a disk"),
    (re.compile(r"\b(shutdown|reboot|halt|poweroff)\b(\s+(-h|now|-r))?", re.I), "restarts or shuts down a machine"),
    (re.compile(r"\bflushall\b|\bflushdb\b", re.I), "empties Redis"),
    (re.compile(r"\b(aws\s+s3\s+rm\b[^\n]*--recursive|gsutil\s+(-m\s+)?rm\s+-r|az\s+storage\s+blob\s+delete-batch)", re.I), "deletes a bucket's files"),
    (re.compile(r"--force\b|--yes\b", re.I), "skips the are-you-sure prompt"),
)
WARN_WORDS = re.compile(r"\b(warning|danger|careful|caution|destructive|irreversible|cannot be undone|double[- ]check|confirm|backup first|⚠)", re.I)
SECRET = (
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\s*[:=]\s*['\"]?([^\s'\"<>{}$]{6,})"), 2),
    (re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"), 0),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), 0),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), 0),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), 0),
)
PLACE = re.compile(r"\b(TODO|TBD|FIXME|XXX|fill (this|me) in|lorem ipsum)\b|<(your|insert|replace)[^>]*>", re.I)
DATED = re.compile(r"(?im)^\s*(?:[*_>-]\s*)?(?:last[ _-]?(?:updated|reviewed|edited|checked)|updated|reviewed|date)\s*[:=]\s*\**\s*(\d{4}-\d{2}-\d{2})")
_PH = re.compile(r"\$\{?[A-Z_]+\}?|<[^>]+>|\{\{[^}]+\}\}|x{4,}|\*{3,}|\.\.\.|changeme|example|placeholder|redacted", re.I)


class RunbookError(ValueError):
    pass


def _docs(text: str) -> list[tuple[str, str]]:
    if re.search(r"(?m)^##\s+\S+\.(md|markdown|txt|rst)\s*$", text):
        out, cur, buf = [], None, []
        for ln in text.split("\n"):
            m = re.match(r"^##\s+(\S+\.(?:md|markdown|txt|rst))\s*$", ln)
            if m:
                if cur is not None:
                    out.append((cur, "\n".join(buf).lstrip("\n")))
                cur, buf = m.group(1), []
            elif cur is not None:
                buf.append(ln)
        if cur is not None:
            out.append((cur, "\n".join(buf).lstrip("\n")))
        return out[:MAX_DOCS]
    return [("runbook.md", text)]


def _mask(v: str) -> str:
    return v[:2] + "•" * min(8, max(3, len(v) - 4)) + v[-2:] if len(v) > 6 else "•" * len(v)


def _stem(p: str) -> str:
    s = p.rsplit("/", 1)[-1].lower()
    s = re.sub(r"\.(md|markdown|txt|rst|html?)$", "", s)
    s = s.split("#", 1)[0]
    return re.sub(r"[^a-z0-9]+", "", s)


def check_one(path: str, body: str, max_age_days: int = 180, today: date | None = None) -> dict[str, Any]:
    today = today or datetime.now(timezone.utc).date()
    lines = body.split("\n")
    heads = [(i + 1, re.sub(r"^#+\s*", "", ln).strip()) for i, ln in enumerate(lines) if re.match(r"^#{1,6}\s+\S", ln)]
    text_low = body
    have = {}
    for key, name, rx in PARTS:
        hit = next((h for h in heads if rx.search(h[1])), None)
        have[key] = {"name": name, "found": bool(hit), "line": hit[0] if hit else None,
                     "in_text": (not hit) and bool(rx.search(text_low))}
    issues: list[dict[str, Any]] = []
    missing = [v["name"] for k, v in have.items() if not v["found"]]
    for k in ("check", "fix"):
        if not have[k]["found"]:
            issues.append({"sev": "bad", "text": f"No '{have[k]['name']}' part: the person paged cannot act on this runbook.", "line": None})
    for k in ("what", "impact", "undo", "who"):
        if not have[k]["found"]:
            issues.append({"sev": "warn", "text": f"No '{have[k]['name']}' part.", "line": None})
    in_code, fence = False, re.compile(r"^\s*(```|~~~)")
    cmds = 0
    dangers = []
    for i, ln in enumerate(lines):
        if fence.match(ln):
            in_code = not in_code
            continue
        code_line = in_code or ln.startswith("    ") or ln.lstrip().startswith("$ ")
        if code_line and ln.strip():
            cmds += 1
        if not code_line and "`" not in ln:
            continue
        for rx, what in DANGER:
            if rx.search(ln):
                near = "\n".join(lines[max(0, i - 4):i + 2])
                warned = bool(WARN_WORDS.search(near))
                dangers.append({"line": i + 1, "what": what, "text": ln.strip()[:200], "warned": warned})
                if not warned:
                    issues.append({"sev": "bad" if what != "skips the are-you-sure prompt" else "warn",
                                   "text": f"Line {i + 1}: {what}, with no warning beside it.", "line": i + 1})
                break
    secrets = []
    for i, ln in enumerate(lines):
        for rx, grp in SECRET:
            m = rx.search(ln)
            if not m:
                continue
            val = m.group(grp)
            if grp and _PH.search(val):
                continue
            secrets.append({"line": i + 1, "shown": _mask(val)})
            issues.append({"sev": "bad", "text": f"Line {i + 1}: a secret is written in the runbook ({_mask(val)}). Rotate it and point "
                                                 "to where it is kept instead.", "line": i + 1})
            break
    holes = [{"line": i + 1, "text": ln.strip()[:160]} for i, ln in enumerate(lines) if PLACE.search(ln)]
    if holes:
        issues.append({"sev": "warn", "text": f"{len(holes)} placeholder(s) nobody filled in (first on line {holes[0]['line']}).",
                       "line": holes[0]["line"]})
    if not cmds and have["fix"]["found"]:
        issues.append({"sev": "warn", "text": "No commands or exact steps: write the commands to copy, not 'restart the service'.", "line": None})
    links = re.findall(r"https?://[^\s)>\]]+", body)
    if not links:
        issues.append({"sev": "info", "text": "No link to a dashboard or log query: add the one you look at first.", "line": None})
    m = DATED.search(body)
    age = None
    if m:
        try:
            age = (today - date.fromisoformat(m.group(1))).days
        except ValueError:
            age = None
    if age is None:
        issues.append({"sev": "warn", "text": "No 'Last reviewed: YYYY-MM-DD' line: nobody can tell if it still works.", "line": None})
    elif age > max_age_days:
        issues.append({"sev": "warn", "text": f"Last reviewed {age} days ago (your limit is {max_age_days}).", "line": None})
    score = round(100 * sum(1 for v in have.values() if v["found"]) / len(PARTS))
    if any(i["sev"] == "bad" for i in issues):
        score = min(score, 60)
    title = next((h[1] for h in heads), "") or path
    return {"path": path, "title": title[:160], "lines": len(lines), "parts": have, "missing": missing, "commands": cmds,
            "dangers": dangers[:50], "secrets": secrets[:20], "placeholders": holes[:30], "links": len(links), "age_days": age,
            "score": score, "issues": issues}


def _runbook_urls(rules: str) -> list[dict[str, str]]:
    out, cur = [], None
    for ln in str(rules or "").split("\n")[:200_000]:
        a = re.match(r"^\s*-?\s*alert:\s*['\"]?([\w:.-]+)", ln)
        if a:
            cur = {"alert": a.group(1), "url": ""}
            out.append(cur)
            continue
        u = re.match(r"^\s*(runbook_url|runbook|playbook)\s*:\s*['\"]?([^'\"\s]+)", ln)
        if u and cur is not None and not cur["url"]:
            cur["url"] = u.group(2)
    return out


def check(text: str, rules: str = "", max_age_days: int = 180, today: date | None = None) -> dict[str, Any]:
    text = str(text or "")[:MAX].strip()
    if not text:
        raise RunbookError("Paste a runbook first (Markdown). For several, start each with ## path/to/file.md")
    try:
        max_age_days = max(1, min(int(max_age_days), 3650))
    except (TypeError, ValueError):
        max_age_days = 180
    docs = [check_one(p, b, max_age_days, today) for p, b in _docs(text)]
    issues: list[dict[str, Any]] = []
    links = []
    if str(rules or "").strip():
        stems = {_stem(d["path"]): d["path"] for d in docs}
        alerts = _runbook_urls(rules)
        used = set()
        for a in alerts:
            if not a["url"]:
                links.append({"alert": a["alert"], "url": "", "runbook": None, "state": "none"})
                continue
            st = _stem(a["url"])
            hit = stems.get(st) or next((p for s, p in stems.items() if s and (s in st or st in s) and len(s) >= 4), None)
            if hit:
                used.add(hit)
            links.append({"alert": a["alert"], "url": a["url"], "runbook": hit, "state": "ok" if hit else "missing"})
        none = [x["alert"] for x in links if x["state"] == "none"]
        miss = [x for x in links if x["state"] == "missing"]
        if none:
            issues.append({"sev": "bad", "text": f"{len(none)} alert(s) have no runbook link: " + ", ".join(none[:8]) + (" …" if len(none) > 8 else "")})
        if miss:
            issues.append({"sev": "warn", "text": f"{len(miss)} runbook link(s) match none of the runbooks you pasted: "
                                                  + ", ".join(f"{x['alert']} -> {x['url']}" for x in miss[:5])})
        lonely = [d["path"] for d in docs if d["path"] not in used]
        if lonely and alerts:
            issues.append({"sev": "info", "text": f"{len(lonely)} runbook(s) no alert links to: " + ", ".join(lonely[:6])})
    bad = sum(1 for d in docs if any(i["sev"] == "bad" for i in d["issues"]))
    counts = {s: sum(1 for d in docs for i in d["issues"] if i["sev"] == s) for s in ("bad", "warn", "info")}
    for s in ("bad", "warn"):
        counts[s] += sum(1 for i in issues if i["sev"] == s)
    if bad:
        issues.insert(0, {"sev": "bad", "text": f"{bad} of {len(docs)} runbook(s) have a serious problem (see each one)."})
    avg = round(sum(d["score"] for d in docs) / len(docs))
    return {"ok": True, "runbooks": len(docs), "score": avg, "counts": counts, "docs": docs, "links": links[:500],
            "linked": sum(1 for x in links if x["state"] == "ok"), "alerts": len(links), "max_age_days": max_age_days, "issues": issues,
            "verdict": (f"{len(docs)} runbook(s), average {avg}/100 for the parts a paged person needs; {counts['bad']} serious and "
                        f"{counts['warn']} other finding(s)" + (f"; {sum(1 for x in links if x['state'] == 'ok')} of {len(links)} alerts "
                                                                "link to a runbook you pasted" if links else "") + ".")}
