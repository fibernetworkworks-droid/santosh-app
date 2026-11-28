"""Dependency manifests read for supply-chain risk: package.json, requirements*.txt, go.mod and Cargo.toml (paste several with
`## path` before each; a package-lock.json adds which packages run install scripts). Versions that are not pinned (ranges, *,
latest, no version at all), dependencies fetched from git, a URL or a local path, extra package indexes (the dependency-confusion
opening), names one or two letters away from a well-known package (a typosquat or a typo), and packages that run code when
installed. Read only - nothing is installed or looked up."""
from __future__ import annotations

import json
import re
import tomllib
from typing import Any

from .common import DsoInputError, finder, finish


class DepsError(DsoInputError):
    pass


POPULAR = {
    "npm": ("react", "react-dom", "lodash", "express", "axios", "chalk", "commander", "debug", "moment", "dotenv", "typescript", "webpack", "babel-core",
            "eslint", "prettier", "jest", "mocha", "request", "uuid", "async", "underscore", "jquery", "vue", "next", "colors", "minimist", "yargs",
            "body-parser", "cross-env", "nodemon", "socket.io", "mongoose", "redis", "pg", "mysql", "sequelize", "rimraf", "glob", "semver", "ws",
            "node-fetch", "classnames", "bluebird", "fs-extra", "inquirer", "cheerio", "dayjs", "zod", "vite", "rollup", "electron", "puppeteer"),
    "pypi": ("requests", "numpy", "pandas", "django", "flask", "urllib3", "boto3", "botocore", "setuptools", "six", "python-dateutil", "pyyaml", "certifi",
             "idna", "charset-normalizer", "cryptography", "jinja2", "pytest", "scipy", "matplotlib", "pillow", "sqlalchemy", "fastapi", "pydantic",
             "click", "attrs", "beautifulsoup4", "lxml", "selenium", "tensorflow", "torch", "scikit-learn", "openai", "httpx", "aiohttp", "colorama",
             "tqdm", "psycopg2", "pymongo", "redis", "celery", "gunicorn", "uvicorn", "jsonschema", "paramiko", "docutils", "rsa", "pyjwt", "markupsafe"),
}


def _dist(a: str, b: str) -> int:
    """Edit distance where swapping two neighbouring letters counts as one (optimal string alignment)."""
    if abs(len(a) - len(b)) > 2:
        return 9
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def _near(name: str, eco: str) -> str:
    n = name.lower().replace("_", "-")
    pop = POPULAR.get(eco, ())
    if n in pop or len(n) < 4:
        return ""
    best = min(pop, key=lambda p: _dist(n, p), default="")
    d = _dist(n, best) if best else 9
    return best if d == 1 or (d == 2 and len(n) >= 8) else ""


def _npm(src: str, path: str) -> list[dict[str, Any]]:
    try:
        d = json.loads(src)
    except ValueError as e:
        raise DepsError(f"{path}: the JSON could not be read - {e}")
    if "lockfileVersion" in d:
        out = []
        for k, v in (d.get("packages") or {}).items():
            if k and isinstance(v, dict) and v.get("hasInstallScript"):
                out.append({"eco": "npm", "name": k.split("node_modules/")[-1], "spec": v.get("version", ""), "dev": bool(v.get("dev")), "lock_install": True, "file": path})
        return out
    out = []
    for sec, dev in (("dependencies", False), ("devDependencies", True), ("optionalDependencies", False), ("peerDependencies", False)):
        for n, s in (d.get(sec) or {}).items():
            out.append({"eco": "npm", "name": n, "spec": str(s), "dev": dev, "file": path})
    for k in ("preinstall", "install", "postinstall", "prepare"):
        if k in (d.get("scripts") or {}):
            out.append({"eco": "npm", "name": f"(this package's {k} script)", "spec": str(d["scripts"][k])[:80], "dev": False, "own_script": True, "file": path})
    return out


def _pip(src: str, path: str) -> list[dict[str, Any]]:
    out = []
    for ln in src.split("\n"):
        s = ln.split(" #", 1)[0].strip()
        if not s or s.startswith("#"):
            continue
        if re.match(r"^(-i|--index-url|--extra-index-url)\b", s):
            out.append({"eco": "pypi", "name": "(index)", "spec": s, "index": s.split()[0], "file": path})
            continue
        if s.startswith(("-r", "--requirement", "-c", "--constraint")):
            continue
        if s.startswith(("-e", "--editable")) or re.match(r"^(git\+|https?://|file:|\./|/)", s) or " @ " in s:
            nm = re.split(r"[\s@#=]", s.replace("-e ", "").split("egg=")[-1])[0] if "egg=" in s else (s.split(" @ ")[0] if " @ " in s else s)
            out.append({"eco": "pypi", "name": nm.strip(), "spec": s, "file": path})
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(.*)$", s)
        if m:
            out.append({"eco": "pypi", "name": m.group(1), "spec": m.group(3).split(";")[0].strip(), "file": path})
    return out


def _go(src: str, path: str) -> list[dict[str, Any]]:
    out = []
    block = False
    for ln in src.split("\n"):
        s = ln.split("//")[0].strip()
        if s.startswith("require ("):
            block = True
            continue
        if block and s == ")":
            block = False
            continue
        m = re.match(r"^(?:require\s+)?([\w.\-]+\.[\w./\-~]+)\s+(v\S+)", s) if (block or s.startswith("require ")) else None
        if m:
            out.append({"eco": "go", "name": m.group(1), "spec": m.group(2), "file": path})
        m = re.match(r"^replace\s+(\S+).*=>\s*(\S+)(\s+\S+)?", s)
        if m and (m.group(2).startswith((".", "/"))):
            out.append({"eco": "go", "name": m.group(1), "spec": "replace => " + m.group(2), "file": path, "local": True})
    return out


def _cargo(src: str, path: str) -> list[dict[str, Any]]:
    try:
        d = tomllib.loads(src)
    except tomllib.TOMLDecodeError as e:
        raise DepsError(f"{path}: the TOML could not be read - {e}")
    out = []
    for sec, dev in (("dependencies", False), ("dev-dependencies", True), ("build-dependencies", True)):
        for n, v in (d.get(sec) or {}).items():
            spec = v if isinstance(v, str) else ("git " + v["git"] if isinstance(v, dict) and v.get("git") else "path " + v["path"] if isinstance(v, dict) and v.get("path") else str((v or {}).get("version", "")) if isinstance(v, dict) else "")
            out.append({"eco": "cargo", "name": n, "spec": spec, "dev": dev, "file": path})
    return out


def _kind(path: str, src: str) -> str:
    p = path.lower()
    if p.endswith("package.json") or p.endswith("package-lock.json"):
        return "npm"
    if p.endswith("go.mod"):
        return "go"
    if p.endswith("cargo.toml"):
        return "cargo"
    if p.endswith(".txt") or "requirements" in p:
        return "pypi"
    s = src.lstrip()
    if s.startswith("{"):
        return "npm"
    if s.startswith("module ") or "\nrequire" in src:
        return "go"
    if "[dependencies]" in src or "[package]" in src:
        return "cargo"
    return "pypi"


def analyse(text: str, pin_dev: bool = False) -> dict[str, Any]:
    t = str(text or "").strip()
    if not t:
        raise DepsError("Paste a manifest: package.json, requirements.txt, go.mod or Cargo.toml (several: '## path' before each).")
    parts = re.split(r"(?m)^##\s+(\S+).*$", t)
    docs = [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)] if len(parts) > 1 else [("manifest", t)]
    rows: list[dict[str, Any]] = []
    for path, src in docs:
        k = _kind(path, src)
        rows += {"npm": _npm, "pypi": _pip, "go": _go, "cargo": _cargo}[k](src.strip(), path)
    if not rows:
        raise DepsError("No dependencies found in what was pasted.")
    issues, add = finder()
    for r in rows:
        fl = []
        s = r["spec"].strip()
        if r.get("lock_install"):
            fl.append("runs an install script")
        elif r.get("own_script"):
            fl.append("own install script")
        elif r.get("index"):
            if r["index"] == "--extra-index-url":
                fl.append("extra index")
        elif r["eco"] == "npm":
            if re.match(r"^(git\+|git:|github:|gitlab:|bitbucket:|https?:|file:|link:)|^[\w-]+/[\w.-]+(#.*)?$", s):
                fl.append("from git or a URL")
            elif not re.fullmatch(r"=?v?\d+\.\d+\.\d+([-+][\w.]+)?", s) and (pin_dev or not r.get("dev")):
                fl.append("not pinned")
        elif r["eco"] == "pypi":
            if re.match(r"^(git\+|https?://|file:|\./|/|-e)", s) or " @ " in s:
                fl.append("from git or a URL")
            elif not re.match(r"^===?\s*[\w.!+*-]+$", s) or "*" in s:
                fl.append("not pinned")
        elif r["eco"] == "go":
            if r.get("local"):
                fl.append("local replace")
        elif r["eco"] == "cargo":
            if s.startswith(("git ", "path ")):
                fl.append("from git or a URL")
            elif not re.match(r"^=\s*\d+\.\d+\.\d+", s) and (pin_dev or not r.get("dev")):
                fl.append("range (Cargo.lock pins it)")
        near = _near(r["name"], r["eco"]) if r["name"] and not r["name"].startswith("(") else ""
        if near:
            fl.append(f"looks like {near}")
            r["near"] = near
        r["flags"] = fl
    def ct(f: str) -> list[dict[str, Any]]:
        return [r for r in rows if any(x.startswith(f) for x in r["flags"])]
    look = ct("looks like")
    for r in look:
        add("warn", "Looks like a well-known package", f"{r['name']} ({r['eco']}, {r['file']}) is one or two letters away from {r['near']} - a typosquat or a typo.",
            f"Check the name; if you meant {r['near']}, fix it.", r["name"])
    git = ct("from git")
    if git:
        add("warn", "From git or a URL", f"{len(git)} dependency(ies) come from git, a URL or a path, e.g. {git[0]['name']} ({git[0]['spec'][:60]}) - not from the registry, not reviewed by its checks.",
            "Pin git dependencies to a commit, or publish them to your registry.", git[0]["name"])
    ext = ct("extra index")
    if ext:
        add("bad", "Extra package index", f"{ext[0]['file']} uses --extra-index-url - pip picks the highest version from either index, so a public package with your internal name wins (dependency confusion).",
            "Use one --index-url that proxies the public index, or pin with hashes.", ext[0]["file"])
    unp = ct("not pinned")
    if unp:
        add("warn", "Not pinned", f"{len(unp)} dependency(ies) take whatever version is newest, e.g. {unp[0]['name']} {unp[0]['spec'] or '(no version)'} - a hijacked release is installed automatically.",
            "Pin exact versions (and commit the lock file); update on purpose.", unp[0]["name"])
    ins = ct("runs an install script")
    if ins:
        add("info", "Install scripts", f"{len(ins)} package(s) in the lock file run code when installed, e.g. {', '.join(r['name'] for r in ins[:4])}.",
            "Install with --ignore-scripts in CI and allow only the ones you need.", ins[0]["name"])
    own = ct("own install script")
    if own:
        add("info", "Own install script", f"{own[0]['file']} runs {own[0]['name'].strip('()')} on install.", "Keep it short and reviewed.")
    loc = ct("local replace")
    if loc:
        add("warn", "Local replace", f"go.mod replaces {loc[0]['name']} with a local path - builds elsewhere differ.", "Remove local replace directives before release.", loc[0]["name"])
    eco: dict[str, int] = {}
    for r in rows:
        if not r["name"].startswith("("):
            eco[r["eco"]] = eco.get(r["eco"], 0) + 1
    deps_n = sum(eco.values())
    rows.sort(key=lambda r: (0 if any(f.startswith("looks like") for f in r["flags"]) else 1 if r["flags"] else 2, r["eco"], r["name"]))
    res = {"files": [p for p, _ in docs], "deps": deps_n, "ecosystems": eco, "rows": rows[:1500], "unpinned": len(unp), "git": len(git), "lookalike": len(look),
           "install_scripts": len(ins), "verdict": f"{deps_n} dependency(ies), {len(unp)} not pinned, {len(git)} from git or a URL, {len(look)} lookalike name(s)"}
    res["note"] = ("Read from the files you pasted; nothing is installed or looked up. Lookalike names are checked against a short list of well-known packages - "
                   "a near miss is a reason to look, not proof of an attack." + ("" if pin_dev else " Development dependencies are not asked to be pinned."))
    return finish(res, issues)
