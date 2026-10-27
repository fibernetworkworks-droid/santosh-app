"""v0.132: read a Gradle / Kotlin build log -> errors per screen file (the model fixes those) or in the fixed project (ours)."""
from __future__ import annotations

import re
from typing import Any

KT_ERR = re.compile(r"^e: (?:file://)?(?P<path>/?[^\s:]+\.kt):(?P<line>\d+):(?P<col>\d+):? (?P<msg>.+)$", re.M)
KT_ERR_OLD = re.compile(r"^e: (?P<path>/?[^\s:]+\.kt): \((?P<line>\d+), (?P<col>\d+)\): (?P<msg>.+)$", re.M)
SCREEN_FILE = re.compile(r"hoola/app/screens/(Screen\w+)\.kt$")


def parse(log: str) -> dict[str, Any]:
    """{screens: {ScreenName: [{line, col, msg}]}, project: [lines], other: [lines], ok}"""
    screens: dict[str, list[dict[str, Any]]] = {}
    project: list[str] = []
    for rx in (KT_ERR, KT_ERR_OLD):
        for m in rx.finditer(log or ""):
            path, msg = m.group("path"), m.group("msg").strip()
            sm = SCREEN_FILE.search(path)
            if sm:
                lst = screens.setdefault(sm.group(1), [])
                e = {"line": int(m.group("line")), "col": int(m.group("col")), "msg": msg[:300]}
                if e not in lst and len(lst) < 25:
                    lst.append(e)
            else:
                short = re.sub(r"^.*?/app/src/main/java/", "", path)
                line = f"{short}:{m.group('line')} {msg[:240]}"
                if line not in project and len(project) < 30:
                    project.append(line)
    other: list[str] = []
    for ln in (log or "").splitlines():
        s = ln.strip()
        if re.match(r"^(ERROR|FAILURE|What went wrong|> |AAPT|error:|Execution failed|Could not|R8:|Missing class)", s) and s not in other:
            other.append(s[:240])
    ok = "BUILD SUCCESSFUL" in (log or "")
    return {"screens": screens, "project": project, "other": other[-25:], "ok": ok}


def for_model(errs: list[dict[str, Any]], src: str) -> str:
    """The errors with the line they point at, for the fix prompt."""
    lines = src.splitlines()
    out = []
    for e in errs[:20]:
        code = lines[e["line"] - 1].strip() if 0 < e["line"] <= len(lines) else ""
        out.append(f"line {e['line']}:{e['col']}: {e['msg']}" + (f"\n    > {code[:200]}" if code else ""))
    return "\n".join(out)


def signature(errs: list[dict[str, Any]]) -> str:
    """Same errors again after a fix = the model is going round in circles."""
    return "|".join(sorted(re.sub(r"\d+", "#", e["msg"])[:80] for e in errs))
