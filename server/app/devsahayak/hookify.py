"""v0.999 REPO RULES IN PLAIN MARKDOWN, from ECC's Hookify (affaan-m/ECC, MIT; the rule-file format is ECC's, the code
is Hoola's own).

A repo can say "never do X" without writing a hook program: one Markdown file per rule, in `.claude/` or `.hoola/`,
named `hookify.<name>.md` (or `hookify.<name>.local.md`, ECC's own name):

    ---
    name: no-force-push
    enabled: true
    event: bash            # bash | file | prompt | stop | all
    action: block          # block (refuse the step) | warn (let it run, tell the coder)
    pattern: git push .*--force
    ---
    Never force-push here. Push a new commit instead.

Instead of one `pattern`, `conditions:` lists `- field: / operator: / pattern:` entries that must ALL match. Fields:
bash -> command; file -> file_path, new_text, old_text, content; prompt -> user_prompt; stop -> diff (the lines the round
added), files. Operators: regex_match, contains, equals, not_contains, starts_with, ends_with.

Enforced in code: a bash rule before the command runs, a file rule before the edit is written, a prompt rule on her
message, a stop rule once when the coder says done. A rule's words are the repo's data, shown to the coder as data. A
regular expression that could hang (nested quantifiers, back-references) is refused and the rule is reported as broken -
the same safety ECC uses. Rules only refuse or warn; they never run anything. Switch: `dev_hookify` (default on).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

CREDIT = "(adapted from ECC's Hookify)"
DIRS = (".claude", ".hoola")
NAME = re.compile(r"^hookify\.[\w.-]+?(\.local)?\.md$")
EVENTS = ("bash", "file", "prompt", "stop", "all")
ACTIONS = ("warn", "block")
OPS = ("regex_match", "contains", "equals", "not_contains", "starts_with", "ends_with")
FIELDS = {"bash": ("command",), "file": ("file_path", "new_text", "old_text", "content", "new_string", "old_string"),
          "prompt": ("user_prompt", "prompt"), "stop": ("diff", "files", "last_assistant_message")}
DEFAULT_FIELD = {"bash": "command", "file": "new_text", "prompt": "user_prompt", "stop": "diff"}
MAX_RULES, MAX_BYTES, MAX_PATTERN, MAX_MSG, MAX_FIELD = 60, 64 * 1024, 512, 4000, 400000
_Q = r"(?:\*|\+|\{\d+(?:,\d*)?\})"


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def on() -> bool:
    return bool(_set("dev_hookify", True))


def safe_pattern(p: str) -> bool:
    """ECC's isSafeRegexSource, in Python: no back-references / lookbehind, no quantified group holding a quantifier
    or an alternation, no two .* runs close together."""
    if not p or len(p) > MAX_PATTERN:
        return False
    if re.search(r"\\[1-9]|\(\?<[=!]", p):
        return False
    if re.search(r"(?:\([^()]*" + _Q + r"[^()]*\)|\[[^\]]*\]" + _Q + r")\s*" + _Q, p):
        return False
    if re.search(r"\([^()]*\|[^()]*\)\s*" + _Q, p):
        return False
    if re.search(r"(?:\.\*|\.\+)[^|)]{0,32}(?:\.\*|\.\+)", p):
        return False
    for m in re.finditer(r"\)\s*" + _Q, p):
        depth, i = 1, m.start() - 1
        while i >= 0:
            if p[i] == ")" and (i == 0 or p[i - 1] != "\\"):
                depth += 1
            elif p[i] == "(" and (i == 0 or p[i - 1] != "\\"):
                depth -= 1
                if depth == 0:
                    break
            i -= 1
        if i >= 0 and re.search(r"(?:^|[^\\])" + _Q, p[i + 1:m.start()]):
            return False
    try:
        re.compile(p)
    except re.error:
        return False
    return True


def _val(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
        if s and "\\\\" in s:
            s = s.replace("\\\\", "\\")
    return s


def parse(text: str, fname: str = "") -> dict[str, Any]:
    """One rule file -> {name, enabled, event, action, conditions, message, error}. A broken rule keeps `error`."""
    m = re.match(r"^\ufeff?---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text or "", re.S)
    rule: dict[str, Any] = {"name": re.sub(r"^hookify\.|(\.local)?\.md$", "", fname) or "rule", "enabled": True,
                            "event": "all", "action": "warn", "conditions": [], "message": "", "error": "", "file": fname}
    if not m:
        rule["error"] = "no --- front matter at the top"
        return rule
    head, body = m.group(1), m.group(2).strip()
    pattern, cur = "", None
    for raw in head.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        ln = re.sub(r"\s+#.*$", "", raw) if not re.search(r"['\"]", raw) else raw
        item = re.match(r"^\s*-\s*(\w+)\s*:\s*(.*)$", ln)
        kv = re.match(r"^\s*(\w+)\s*:\s*(.*)$", ln)
        if item:
            cur = {item.group(1): _val(item.group(2))}
            rule["conditions"].append(cur)
        elif kv and raw.startswith((" ", "\t")) and cur is not None:
            cur[kv.group(1)] = _val(kv.group(2))
        elif kv:
            cur = None
            k, v = kv.group(1).lower(), _val(kv.group(2))
            if k == "name" and v:
                rule["name"] = v[:80]
            elif k == "enabled":
                rule["enabled"] = v.lower() not in ("false", "no", "off", "0")
            elif k == "event":
                rule["event"] = v.lower()
            elif k == "action":
                rule["action"] = v.lower()
            elif k == "pattern":
                pattern = v
    rule["message"] = body[:MAX_MSG]
    if rule["event"] not in EVENTS:
        rule["error"] = f"event must be one of {', '.join(EVENTS)}"
    elif rule["action"] not in ACTIONS:
        rule["error"] = "action must be warn or block"
    if pattern and not rule["conditions"]:
        rule["conditions"] = [{"field": "", "operator": "regex_match", "pattern": pattern}]
    if not rule["error"] and not rule["conditions"]:
        rule["error"] = "it needs a pattern or conditions"
    for c in rule["conditions"][:8]:
        if rule["error"]:
            break
        c.setdefault("operator", "regex_match")
        c.setdefault("field", "")
        if c["operator"] not in OPS:
            rule["error"] = f"operator {c['operator']!r} is not one of {', '.join(OPS)}"
        elif c["operator"] == "regex_match" and not safe_pattern(str(c.get("pattern") or "")):
            rule["error"] = "the pattern is not a safe regular expression (nested quantifiers or too long)"
        elif not str(c.get("pattern") or ""):
            rule["error"] = "a condition has no pattern"
    rule["conditions"] = rule["conditions"][:8]
    return rule


def files(repo: Path) -> list[Path]:
    out: list[Path] = []
    for d in DIRS:
        base = Path(repo) / d
        if base.is_dir():
            out += sorted(p for p in base.iterdir() if p.is_file() and NAME.match(p.name))
    return out[:MAX_RULES]


def rules(repo: Path) -> list[dict[str, Any]]:
    got = []
    for p in files(repo):
        try:
            if p.is_symlink() or p.stat().st_size > MAX_BYTES:
                continue
            r = parse(p.read_text("utf-8", errors="replace"), p.name)
        except OSError:
            continue
        r["file"] = f"{p.parent.name}/{p.name}"
        got.append(r)
    return got


def _match(c: dict[str, Any], event: str, fields: dict[str, Any]) -> bool:
    name = str(c.get("field") or "") or DEFAULT_FIELD.get(event, "")
    alias = {"new_string": "new_text", "old_string": "old_text", "prompt": "user_prompt"}
    val = fields.get(name, fields.get(alias.get(name, ""), None))
    if val is None:
        return False
    v = (" ".join(val) if isinstance(val, list) else str(val))[:MAX_FIELD]
    p, op = str(c.get("pattern") or ""), c.get("operator", "regex_match")
    if op == "regex_match":
        try:
            return bool(re.search(p, v))
        except re.error:
            return False
    return {"contains": p in v, "not_contains": p not in v, "equals": v == p, "starts_with": v.startswith(p),
            "ends_with": v.endswith(p)}.get(op, False)


def check(repo: Path, event: str, fields: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """{block: [...], warn: [...]} - the enabled, valid rules for this event whose conditions all match."""
    out: dict[str, list[dict[str, Any]]] = {"block": [], "warn": []}
    if not on():
        return out
    for r in rules(repo):
        if r["error"] or not r["enabled"] or r["event"] not in (event, "all"):
            continue
        if all(_match(c, event, fields) for c in r["conditions"]):
            out[r["action"]].append(r)
    return out


def _quote(r: dict[str, Any]) -> str:
    return f'<repo_rule name="{r["name"]}" file="{r["file"]}">\n{r["message"] or "(the rule gives no message)"}\n</repo_rule>'


def refusal(hits: list[dict[str, Any]], what: str) -> str:
    return (f"Refused: this repo's own rule says no to {what} {CREDIT}. The rule's words (data from the repo):\n"
            + "\n".join(_quote(r) for r in hits[:4]) + "\nDo it another way that keeps the rule, or ask her ONE question in done "
            "if the rule really must be broken for her request.")


def warning(hits: list[dict[str, Any]]) -> str:
    return ("\n\n[A rule of this repo matched this step " + CREDIT + " - read it and follow it:\n"
            + "\n".join(_quote(r) for r in hits[:4]) + "]")


def bash(repo: Path, cmd: str) -> tuple[str, str]:
    """(refusal, warning) for a command."""
    got = check(repo, "bash", {"command": cmd})
    return (refusal(got["block"], "this command") if got["block"] else "", warning(got["warn"]) if got["warn"] else "")


def file(repo: Path, rel: str, old: str, new: str) -> tuple[str, str]:
    """(refusal, warning) for an edit or write; new_text = only the lines it adds."""
    added = _added(old, new)
    got = check(repo, "file", {"file_path": rel, "new_text": added, "old_text": old, "content": new})
    return (refusal(got["block"], f"this change to {rel}") if got["block"] else "", warning(got["warn"]) if got["warn"] else "")


def _added(old: str, new: str) -> str:
    import difflib
    out = [ln[1:] for ln in difflib.unified_diff((old or "").splitlines(), (new or "").splitlines(), lineterm="", n=0)
           if ln.startswith("+") and not ln.startswith("+++")]
    return "\n".join(out)


def prompt(repo: Path, words: str) -> dict[str, list[dict[str, Any]]]:
    return check(repo, "prompt", {"user_prompt": words})


def stop(repo: Path, diff: str, files_: list[str], said: str) -> dict[str, list[dict[str, Any]]]:
    added = "\n".join(ln[1:] for ln in (diff or "").splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    return check(repo, "stop", {"diff": added, "files": files_, "last_assistant_message": said})


def listing(repo: Path) -> str:
    rs = rules(repo)
    if not rs:
        return ("<hookify_rules>\nThis repo has no rule files yet. A rule is one Markdown file: .claude/hookify.<name>.md "
                "(see /hookify).\n</hookify_rules>")
    rows = []
    for r in rs:
        state = ("BROKEN: " + r["error"]) if r["error"] else ("on" if r["enabled"] else "off")
        conds = "; ".join(f"{c.get('field') or DEFAULT_FIELD.get(r['event'], 'any')} {c.get('operator')} {c.get('pattern')!r}"
                          for c in r["conditions"][:3])
        rows.append(f"- {r['name']} ({r['file']}): {r['event']} / {r['action']} / {state} - {conds}")
    return "<hookify_rules>\n" + "\n".join(rows) + "\n</hookify_rules>"


WRITE = """<her_command>/hookify</her_command>
She wants a RULE for this repo """ + CREDIT + """: something Hoola (and anyone using these files) must not do. Her words:
<her_rule>{words}</her_rule>
{conv}Write it as ONE Markdown file per rule at .claude/hookify.<short-name>.md, exactly in this shape:

---
name: <short-name>
enabled: true
event: bash | file | prompt | stop | all
action: block | warn
pattern: <a regular expression>
---
<one or two plain sentences: what not to do, and what to do instead>

Pick the event by what the rule is about: a command -> bash (matched against the command), a code change -> file
(matched against the lines the change ADDS; use conditions with field: file_path to limit it to some files), her messages
-> prompt, "before finishing" -> stop (matched against the lines the round added). Use `action: block` only when the thing
must never happen; `warn` when it is usually wrong. For two things at once use conditions (all must match):
conditions:
  - field: file_path
    operator: regex_match
    pattern: \\.py$
  - field: new_text
    operator: contains
    pattern: print(
Keep the pattern simple: no nested repeats like (a+)+ - Hoola refuses those as unsafe. Change nothing else. In done, show
each rule's name, event, action and pattern in one line each, and say /hookify-list shows them all."""


def write_text(words: str, recent: str) -> str:
    conv = ("No rule was named, so first look at this session's conversation for what she corrected or pushed back on "
            "(below) and propose rules for that:\n<recent_conversation>\n" + recent[:6000] + "\n</recent_conversation>\n"
            if not words.strip() else "")
    return WRITE.format(words=words.strip()[:2000] or "(none - see below)", conv=conv)
