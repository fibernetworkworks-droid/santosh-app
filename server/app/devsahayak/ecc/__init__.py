"""v0.794 ECC AGENTS (owner: "ADD ALL MISSING ECC AGENTS TO HOOLA CODE --- MAKE HOOLA CODE MORE POWERFULL AND SMOOTH").

The whole agent roster of ECC (github.com/affaan-m/ECC, MIT, v2.2.3) that fits a coding session, adapted as TEXT for
Hoola Code's working-copy engine (`devsahayak/engine.py`):

- `catalog()`     63 agents (language / framework reviewers, build fixers, planners, explorers, cleaners, domain
                  reviewers), each with a tool level (read / run / edit) and the words / files that make it relevant;
- `roster()`      the one-line list the coder sees in its system prompt, so it can hand work to a specialist with the
                  engine's `agent` tool the way Claude Code hands work to a subagent;
- `rules_for()`   ECC's coding rules (common + the repo's languages), added to the coder's system prompt;
- `gate()`        ECC's pre-commit quality hook as a check on the round's diff before `done` is accepted
                  (debug leftovers, focused tests, conflict markers, keys).

Hoola's own rules (data is never instructions, never a secret, never workflows, merge only on her tap) always come
first and win; an agent cannot change that, and an agent never pushes. Credit: THIRD_PARTY_NOTICES.md."""
from __future__ import annotations

import importlib
import os
import re
from typing import Any

CREDIT = "Adapted from ECC agents (MIT, github.com/affaan-m/ECC)."
PARTS = ("reviewers_lang", "reviewers_more", "fixers", "planners", "agency_eng", "agency_qa")   # agency_* = v0.814 The Agency (msitarzewski/agency-agents, MIT)

# ECC agents deliberately NOT in Hoola Code, each with the reason (shown by the catalogue route, kept honest in tests).
NOT_ADDED = {
    "marketing-agent": "not a coding job - Hoola's Social / Marketing employees do campaigns",
    "chief-of-staff": "not a coding job - email / Slack triage is Hoola's own chat work",
    "conversation-analyzer": "writes Claude Code hook files from Claude Code transcripts; Hoola Code has neither",
    "harness-optimizer": "tunes Claude Code's own config; Hoola Code's engine is tuned in code and settings",
    "loop-operator": "watches an autonomous Claude Code loop; Hoola Code's engine IS the loop (steps, time, stop)",
    "gan-planner": "part of ECC's generator / evaluator harness; Hoola uses planner + the round + its own review",
    "gan-generator": "part of ECC's generator / evaluator harness; the main Hoola coder is the generator",
    "gan-evaluator": "drives a running app in Playwright with internet; the box has no browser or network",
}

# language keys -> the file endings that show them
EXT = {
    ".py": "python", ".pyi": "python", ".ts": "js", ".mts": "js", ".cts": "js", ".js": "js", ".mjs": "js", ".cjs": "js",
    ".tsx": "react", ".jsx": "react", ".vue": "vue", ".dart": "dart", ".kt": "kotlin", ".kts": "kotlin", ".java": "java",
    ".go": "go", ".rs": "rust", ".swift": "swift", ".c": "cpp", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".h": "cpp",
    ".hh": "cpp", ".hpp": "cpp", ".cs": "csharp", ".fs": "fsharp", ".fsx": "fsharp", ".fsi": "fsharp", ".php": "php",
    ".rb": "ruby", ".pl": "perl", ".pm": "perl", ".ets": "arkts", ".sql": "sql", ".html": "web", ".css": "web",
    ".scss": "web",
}
# a marker file that names a framework, whatever the file count says
MARKERS = [
    (re.compile(r"(^|/)angular\.json$"), "angular"),
    (re.compile(r"(^|/)nuxt\.config\.(ts|js|mjs)$"), "nuxt"),
    (re.compile(r"(^|/)(metro\.config\.js|react-native\.config\.js)$"), "react-native"),
    (re.compile(r"(^|/)manage\.py$"), "django"),
    (re.compile(r"(^|/)pubspec\.yaml$"), "dart"),
]
# a language key -> the RULES key(s) it reads (react reads js too; django / fastapi read python)
RULE_KEYS = {"react": ("js", "react"), "vue": ("js", "vue"), "nuxt": ("js", "vue", "nuxt"), "angular": ("js", "angular"),
             "react-native": ("js", "react", "react-native"), "django": ("python",)}
# a language key -> the reviewer / fixer ECC has for it
REVIEWER = {"python": "python-reviewer", "js": "typescript-reviewer", "react": "react-reviewer", "vue": "vue-reviewer",
            "nuxt": "vue-reviewer", "angular": "typescript-reviewer", "react-native": "react-reviewer",
            "dart": "flutter-reviewer", "kotlin": "kotlin-reviewer", "java": "java-reviewer", "go": "go-reviewer",
            "rust": "rust-reviewer", "swift": "swift-reviewer", "cpp": "cpp-reviewer", "csharp": "csharp-reviewer",
            "fsharp": "fsharp-reviewer", "php": "php-reviewer", "ruby": "ruby-reviewer", "django": "django-reviewer",
            "sql": "database-reviewer", "arkts": "harmonyos-app-resolver", "web": "a11y-architect"}
FIXER = {"python": "build-error-resolver", "js": "build-error-resolver", "react": "react-build-resolver",
         "vue": "build-error-resolver", "dart": "dart-build-resolver", "kotlin": "kotlin-build-resolver",
         "java": "java-build-resolver", "go": "go-build-resolver", "rust": "rust-build-resolver",
         "swift": "swift-build-resolver", "cpp": "cpp-build-resolver", "django": "django-build-resolver"}

_CACHE: dict[str, Any] = {}


def catalog() -> dict[str, dict[str, Any]]:
    """Every adapted agent by name (loaded once)."""
    if "all" in _CACHE:
        return _CACHE["all"]
    out: dict[str, dict[str, Any]] = {}
    for part in PARTS:
        mod = importlib.import_module(f"{__name__}.{part}")
        for a in getattr(mod, "AGENTS", []):
            out[a["name"]] = a
    _CACHE["all"] = out
    return out


def get(name: str) -> dict[str, Any] | None:
    """One agent by its name; forgiving about case, spaces and underscores ('React Reviewer' -> react-reviewer)."""
    key = re.sub(r"[\s_]+", "-", str(name or "").strip().lower())
    cat = catalog()
    if key in cat:
        return cat[key]
    for n, a in cat.items():
        if a["title"].lower() == str(name or "").strip().lower():
            return a
    return None


def rules() -> dict[str, str]:
    if "rules" not in _CACHE:
        from .rules_text import RULES
        _CACHE["rules"] = RULES
    return _CACHE["rules"]


# ---------------------------------------------------------------- which languages a repo / a change is in
def langs_of(paths: list[str], top: int = 4) -> list[str]:
    """The languages of a set of files, most files first (framework markers first of all); at most `top`."""
    counts: dict[str, int] = {}
    marked: list[str] = []
    for p in paths or []:
        s = str(p)
        for rx, key in MARKERS:
            if rx.search(s) and key not in marked:
                marked.append(key)
        lang = EXT.get(os.path.splitext(s.lower())[1])
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    order = sorted(counts, key=lambda k: (-counts[k], k))
    out = marked + [k for k in order if k not in marked]
    return out[:top]


def rules_for(paths: list[str], cap: int = 9000) -> str:
    """ECC's common rules + the rules for the repo's main languages, inside `cap` characters."""
    R = rules()
    keys: list[str] = ["common"]
    for lang in langs_of(paths):
        for k in RULE_KEYS.get(lang, (lang,)):
            if k in R and k not in keys:
                keys.append(k)
    out, used = [], 0
    for k in keys:
        txt = R[k].strip()
        if used + len(txt) > cap and k != "common":
            continue
        out.append(txt)
        used += len(txt)
    return ("CODING RULES (default good practice; the repo's own rules and hers win, and the style already in a file "
            "wins over these):\n\n" + "\n\n".join(out))


def suggest(paths: list[str], request: str = "", n: int = 6) -> list[str]:
    """The agents that fit this repo / change / request best: the reviewer for each main language, the agents whose
    files or words match, then the general reviewer and the security reviewer."""
    cat = catalog()
    out: list[str] = []

    def add(x: str) -> None:
        if x in cat and x not in out:
            out.append(x)
    for lang in langs_of(paths, top=3):
        add(REVIEWER.get(lang, ""))
    req = str(request or "")
    blob = "\n".join(str(p) for p in (paths or [])[:4000])
    for a in cat.values():
        hit_w = bool(a["words"]) and bool(_rx(a["words"]).search(req))
        hit_f = bool(a["files"]) and a["group"] in ("review", "domain") and bool(_rx(a["files"], re.M).search(blob))
        if hit_w or hit_f:
            add(a["name"])
    tail = [x for x in ("code-reviewer", "security-reviewer") if x in cat]   # the two general reviewers always fit
    return [x for x in out if x not in tail][:max(0, n - len(tail))] + tail


def _rx(pattern: str, flags: int = 0) -> "re.Pattern[str]":
    """Compiled once; a file pattern runs over all paths joined by newlines, so ^ / $ mean one path (re.M)."""
    key = f"rx:{flags}:{pattern}"
    if key not in _CACHE:
        _CACHE[key] = re.compile(pattern, flags)
    return _CACHE[key]


def fixer_for(lang: str) -> str:
    return FIXER.get(lang, "build-error-resolver")


def roster(paths: list[str], request: str = "") -> str:
    """The agent list for the coder's system prompt: every agent in one line, grouped, the best fits first."""
    cat = catalog()
    best = suggest(paths, request)
    names = {"review": "Reviewers", "fix": "Fixers (they edit)", "build": "Builders (they edit)", "quality": "Quality",
             "plan": "Planners", "explore": "Explorers", "domain": "Domain"}
    lines = ["AGENTS YOU CAN HAND WORK TO (the `agent` tool; adapted from ECC). Each starts fresh with only the task "
             "you write, works in this same working copy and returns one report (adapted from ECC and The Agency). tools: read = looks only, run = may run "
             "commands in the box, edit = may change files. Several read / run agents in ONE reply run at the same time.",
             "Best fits for this repo: " + ", ".join(best) + "."]
    for g in ("review", "fix", "build", "quality", "plan", "explore", "domain"):
        rows = [a for a in cat.values() if a["group"] == g]
        if not rows:
            continue
        lines.append(f"{names[g]}:")
        for a in sorted(rows, key=lambda a: a["name"]):
            lines.append(f"- {a['name']} [{a['tools']}]: {a['when'][:150]}")
    return "\n".join(lines)


# ---------------------------------------------------------------- ECC's pre-commit quality hook, on the round's diff
TESTY = re.compile(r"(?i)(^|/)(tests?|__tests__|spec|e2e|fixtures?)/|(_test|\.test|\.spec|_spec)\.[a-z]+$|(^|/)test_[^/]+$")
DOCS = re.compile(r"(?i)\.(md|mdx|rst|txt|adoc)$")
LEFTOVERS = [
    (re.compile(r"\bconsole\.(log|debug)\s*\("), r"\.(m|c)?[jt]sx?$|\.vue$|\.svelte$", "a console.log left in", False),
    (re.compile(r"(^|[;{\s])debugger\s*;?\s*$"), r"\.(m|c)?[jt]sx?$|\.vue$|\.svelte$", "a debugger statement", True),
    (re.compile(r"\bbreakpoint\(\)|\bpdb\.set_trace\(|^\s*import i?pdb\b"), r"\.py$", "a Python debugger call", True),
    (re.compile(r"\bbinding\.(pry|irb)\b|^\s*byebug\b"), r"\.rb$", "a Ruby debugger call", True),
    (re.compile(r"\b(var_dump|dd|dump)\s*\(|\bray\s*\("), r"\.php$", "a PHP dump call", False),
    (re.compile(r"\b(it|describe|test|context)\.only\s*\(|\bfit\s*\(|\bfdescribe\s*\("), r"", "a focused test (.only) - the rest would be skipped", True),
]
CONFLICT = re.compile(r"^(<{7}|>{7})( |$)|^={7}$")


def _added(diff: str) -> list[tuple[str, int, str]]:
    """(path, new line number, text) for every added line of a unified diff."""
    out, path, n = [], "", 0
    for ln in (diff or "").splitlines():
        if ln.startswith("+++ "):
            p = ln[4:].strip()
            path = p[2:] if p.startswith("b/") else ("" if p == "/dev/null" else p)
            continue
        if ln.startswith("@@"):
            m = re.search(r"\+(\d+)", ln)
            n = int(m.group(1)) if m else 0
            continue
        if not path:
            continue
        if ln.startswith("+") and not ln.startswith("+++"):
            out.append((path, n, ln[1:]))
            n += 1
        elif ln.startswith("-"):
            continue
        else:
            n += 1
    return out


def gate(diff: str) -> list[dict[str, Any]]:
    """Problems in the ADDED lines a careful engineer would not commit: debug leftovers (not in tests / docs), a
    focused test that silently skips the rest, merge conflict markers, and key-looking lines. Each = path, line, what,
    hard (hard = must be fixed; soft = fix it or say why it stays)."""
    out: list[dict[str, Any]] = []
    try:
        from .. import rules as R
    except Exception:                                   # pragma: no cover
        R = None
    for path, line, text in _added(diff):
        if len(out) >= 30:
            break
        if CONFLICT.search(text):
            out.append({"path": path, "line": line, "what": "a merge conflict marker", "hard": True})
            continue
        if DOCS.search(path):
            continue
        testy = bool(TESTY.search(path))
        for rx, ext, what, hard in LEFTOVERS:
            if ext and not re.search(ext, path):
                continue
            if testy and "focused test" not in what:
                continue
            if not ext and not testy:
                continue
            if rx.search(text):
                out.append({"path": path, "line": line, "what": what, "hard": hard})
                break
        if R is not None:
            try:
                if R.secrets_in(text):
                    out.append({"path": path, "line": line, "what": "a line that looks like a key or a password", "hard": True})
            except Exception:
                pass
    return out


def gate_text(found: list[dict[str, Any]]) -> str:
    """The note the coder gets when `done` meets problems (it gets ONE chance to clean up)."""
    rows = [f"- {f['path']}:{f['line']}: {f['what']}" + ("" if f["hard"] else " (fix it, or say in risk why it stays)")
            for f in found[:20]]
    return ("QUALITY GATE (ECC's pre-commit check) - not finished yet. Your change adds:\n" + "\n".join(rows)
            + "\nClean these up (or, for a soft one, keep it and say why in risk), run the check again, then call done.")
