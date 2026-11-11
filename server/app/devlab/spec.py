"""v0.456 WHICH command - declared, never invented.

Every product that runs a repo's tests gets the command from a declared place, never from a guess: Aider's
`--test-cmd`, Devin's blueprint items literally named `lint` / `test` / `build` ("which Devin uses when verifying its
work"), Jules's setup script ("always include commands to install packages, run linters, or execute tests"), Codex via
AGENTS.md ("the agent will try to run the relevant checks and fix failures before finishing a task").

So the order here is: HER word first, then the repo's own declarations, then the repo's CI, and only then a language
default - and every answer carries WHERE it came from plus whether she has confirmed it. A command Hoola worked out
for itself runs only after one tap; her own never asks again. If nothing is found we say so and stop: no command is
invented from the file tree."""
from __future__ import annotations

import json
import re
from typing import Any

MAX_CMD = 400

# a command line we refuse to run at all, whoever declared it (these are not "dangerous shell" filters - the box has no
# network and no secrets - they are the ones that would waste her VPS or lie about the result)
REFUSE = re.compile(r"(?i)(^|[;&|]\s*)(sudo|su\b|docker\b|systemctl|shutdown|reboot|mkfs|mount\b|chpasswd|"
                    r"crontab|nohup|while\s+true|yes\s*\||:\(\)\s*\{)")
SECRETY = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|aws_|private[_-]key)\s*=")

LANGS = {
    "python": {"files": ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile", "tox.ini"),
               "setup": "python3 -m pip install --user -r requirements.txt || python3 -m pip install --user -e . || true",
               "test": "python3 -m pytest -q", "one": "python3 -m pytest -q {path}"},
    "node": {"files": ("package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json"),
             "setup": "npm ci || npm install", "test": "npm test --silent", "one": "npm test --silent -- {path}"},
    "go": {"files": ("go.mod",), "setup": "go mod download || true", "test": "go test ./...", "one": "go test {path}"},
    "rust": {"files": ("Cargo.toml",), "setup": "cargo fetch || true", "test": "cargo test", "one": "cargo test {path}"},
}
LOCKS = ("requirements.txt", "pyproject.toml", "poetry.lock", "Pipfile.lock", "package.json", "package-lock.json",
         "pnpm-lock.yaml", "yarn.lock", "go.mod", "go.sum", "Cargo.toml", "Cargo.lock", "setup.py", "setup.cfg",
         "Makefile", ".hoola/lab.json")

_RULES = ("AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "README.md")
_TEST_WORDS = re.compile(r"(?i)\b(test|tests|testing|check|checks|lint|typecheck|type-check|build|verify)\b")
_INSTALLISH = re.compile(r"(?i)\b(install|setup|set up|deps|dependencies|bootstrap|prepare)\b")
_CMDISH = re.compile(r"(?i)^(npm|pnpm|yarn|bun|npx|python3?|py|pip3?|pytest|poetry|uv|tox|nox|make|go|cargo|"
                     r"gradlew?|\./gradlew|mvn|dotnet|dart|flutter|ruff|mypy|tsc|jest|vitest|eslint|rake|bundle)\b")


def _clean(cmd: str) -> str:
    c = " ".join((cmd or "").strip().split())
    c = c.removeprefix("$ ").removeprefix("> ").strip("`")
    return c[:MAX_CMD]


def refuse_reason(cmd: str) -> str:
    """'' = runnable. Anything else is said to her as the reason, not swallowed."""
    c = _clean(cmd)
    if not c:
        return "the command is empty"
    if len(c) >= MAX_CMD:
        return "the command is too long"
    if REFUSE.search(c):
        return "this command has a part like sudo / docker / service - it will not run in the lab"
    if SECRETY.search(c):
        return "the command has text that looks like a key / password - never in the lab"
    if "\n" in (cmd or ""):
        return "give a single-line command"
    return ""


def lang_of(paths: list[str]) -> str:
    """The repo's language family, from the files that actually exist at its root."""
    root = {p for p in paths if "/" not in p}
    for name, d in LANGS.items():
        if root & set(d["files"]):
            return name
    for name, d in LANGS.items():                      # a monorepo: the marker may sit one level down
        if any(p.count("/") == 1 and p.split("/")[-1] in d["files"] for p in paths):
            return name
    return ""


def _from_hoola_file(text: str) -> dict[str, Any]:
    """`.hoola/lab.json` in her repo - the only place a repo can state this itself without ambiguity."""
    try:
        d = json.loads(text or "{}")
    except ValueError:
        return {}
    if not isinstance(d, dict):
        return {}
    out = {}
    for key in ("setup", "test", "lint", "build"):
        v = d.get(key)
        if isinstance(v, str) and _clean(v):
            out[key] = _clean(v)
    if isinstance(d.get("timeout"), int):
        out["timeout"] = max(30, min(int(d["timeout"]), 1800))
    return out


def _from_rules(text: str) -> dict[str, Any]:
    """Commands written in the repo's own rules / README. Three shapes are read, and nothing else:
    a labelled list item ("- Run one test file: pnpm vitest run x"), a bare command line under a test-ish heading, and
    a fenced block under one. A label decides what the command IS, which is how AGENTS.md's own examples are written."""
    tests: list[str] = []
    setup = ""
    near = False
    for raw in (text or "").splitlines()[:400]:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            near = bool(_TEST_WORDS.search(line))
            continue
        label, _, after = line.lstrip("-*> ").partition(":")
        tail = _clean(after)
        if tail and (_CMDISH.match(tail) or REFUSE.search(tail)) and len(label) <= 60:
            if _TEST_WORDS.search(label):
                tests.append(tail)
            elif _INSTALLISH.search(label) and not setup:
                setup = tail
            continue
        if line.endswith(":"):
            near = bool(_TEST_WORDS.search(line))
            continue
        body = _clean(line.lstrip("-*> ").strip("`"))
        if _CMDISH.match(body) and (near or _TEST_WORDS.search(raw)):
            tests.append(body)
    seen, uniq, refused = set(), [], []
    for c in tests:
        if c in seen:
            continue
        seen.add(c)
        why = refuse_reason(c)
        (refused if why else uniq).append({"cmd": c, "why": why} if why else c)
    return {"tests": uniq[:6], "setup": "" if refuse_reason(setup) else setup, "refused": refused[:3]}


def _from_ci(text: str) -> list[str]:
    """`run:` steps of her CI workflow - what her own pipeline really does, which is the strongest evidence there is."""
    out: list[str] = []
    for m in re.finditer(r"(?m)^\s*(?:-\s*)?run:\s*(?:\|[-+]?\s*)?(.*)$", text or ""):
        first = _clean(m.group(1))
        if first and _CMDISH.match(first) and not refuse_reason(first):
            out.append(first)
    tests = [c for c in out if re.search(r"(?i)\b(test|pytest|jest|vitest|check|lint|tsc|mypy|ruff)\b", c)]
    seen, uniq = set(), []
    for c in tests + out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq[:8]


def discover(paths: list[str], files: dict[str, str], hers: dict[str, str] | None = None) -> dict[str, Any]:
    """What to run, and where it came from.

    `paths` = the repo's file list; `files` = the text of the few files we read (rules, CI, .hoola/lab.json);
    `hers` = what she typed for this repo (settings), which always wins and never needs a tap.
    Returns {setup, test, source, confirm, lang, candidates, why}. `confirm=True` = it is Hoola's reading of HER repo
    and needs one tap before it ever runs."""
    hers = {k: _clean(v) for k, v in (hers or {}).items() if _clean(v)}
    lang = lang_of(paths)
    cand: list[dict[str, str]] = []
    hoola_file = _from_hoola_file(files.get(".hoola/lab.json", ""))
    rules_setup, refused = "", []
    for name in _RULES:
        r = _from_rules(files.get(name, ""))
        for c in r["tests"]:
            cand.append({"cmd": c, "source": name})
        for x in r["refused"]:
            refused.append({**x, "source": name})
        rules_setup = rules_setup or r["setup"]
    for name, text in files.items():
        if name.startswith(".github/workflows/"):
            for c in _from_ci(text):
                cand.append({"cmd": c, "source": name})
    if lang:
        cand.append({"cmd": LANGS[lang]["test"], "source": f"{lang} default"})

    if hers.get("test"):
        test, source, confirm = hers["test"], "given by you", False
    elif hoola_file.get("test"):
        test, source, confirm = hoola_file["test"], ".hoola/lab.json", False
    elif cand:
        test, source, confirm = cand[0]["cmd"], cand[0]["source"], True
    else:
        test, source, confirm = "", "", True

    setup = (hers.get("setup") or hoola_file.get("setup") or rules_setup
             or (LANGS[lang]["setup"] if lang else ""))
    why = ""
    if not test:
        why = ("This repo does not say anywhere how to run its tests (AGENTS.md / CLAUDE.md / CI / .hoola/lab.json). "
               "Tell Hoola the command - Hoola will not make up a command and run it.")
    bad = refuse_reason(test) if test else ""
    if bad:
        test, why = "", f"The command that was found ({source}) cannot be run: {bad}"
    if refused:                      # her repo declared something we will not run: she is TOLD, never silently swapped
        r0 = refused[0]
        why = (f"The command written in {r0['source']}, `{r0['cmd']}`, cannot be run ({r0['why']}). "
               + (f"Instead `{test}` ({source}) can be run - say yes to approve." if test else "")).strip()
    return {"setup": setup, "test": test, "source": source, "confirm": bool(test) and confirm, "lang": lang,
            "candidates": cand[:8], "refused": refused[:3], "why": why, "timeout": hoola_file.get("timeout", 0)}


def one_file(cmd: str, lang: str, path: str) -> str:
    """The declared command narrowed to ONE test file, when that can be done honestly. '' = it cannot, and the caller
    says so instead of guessing: appending a path to an arbitrary command is how a check silently tests nothing."""
    raw = (path or "").strip()
    c, p = _clean(cmd), raw.removeprefix("./")
    if not c or not p or refuse_reason(c) or " " in p or ".." in raw or raw.startswith("/"):
        return ""
    if lang in LANGS and c == LANGS[lang]["test"]:
        return _clean(LANGS[lang]["one"].format(path=p))
    if re.search(r"(?i)\b(pytest|vitest|jest|go test|cargo test|dart test|flutter test)\b", c) and "{" not in c:
        return _clean(f"{c} {p}")                      # these all take a path as the last argument
    return ""


def deps_key(files: dict[str, str]) -> str:
    """The snapshot's cache key: the hash of the files that decide what gets installed (Codex keys its cached container
    on the setup script + env; we key on the lock files, so a dependency change rebuilds and nothing else does)."""
    import hashlib
    h = hashlib.sha256()
    for name in LOCKS:
        v = files.get(name)
        if v is not None:
            h.update(name.encode())
            h.update(b"\0")
            h.update(v.encode("utf-8", "replace"))
            h.update(b"\0")
    return h.hexdigest()[:16]
