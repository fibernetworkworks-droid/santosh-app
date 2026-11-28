"""Small shared pieces of the Data Engineer desk: the findings list, durations and sizes written the way people write them, and
the closing counts every reader returns."""
from __future__ import annotations

import re
from typing import Any, Callable


class DeInputError(ValueError):
    pass


def finder() -> tuple[list[dict[str, Any]], Callable[..., None]]:
    issues: list[dict[str, Any]] = []

    def add(sev: str, area: str, text: str, fix: str = "", fn: str = "") -> None:
        issues.append({"sev": sev, "area": area, "text": text, "fix": fix, "fn": fn})
    return issues, add


def finish(res: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, Any]:
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order.get(i["sev"], 3))
    res["issues"] = issues
    res["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    return res


_DUR = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(ms|s|sec|secs|seconds?|m|min|mins|minutes?|h|hr|hrs|hours?)?\s*$", re.I)


def minutes(v: str, default_unit: str = "m") -> float | None:
    """'12m', '90s', '1.5h', '45' (minutes) or 'HH:MM:SS' -> minutes."""
    v = str(v or "").strip()
    if not v:
        return None
    if re.fullmatch(r"\d{1,3}:\d{2}(:\d{2}(\.\d+)?)?", v):
        p = [float(x) for x in v.split(":")]
        return p[0] * 60 + p[1] + (p[2] / 60 if len(p) > 2 else 0) if len(p) == 3 else p[0] + p[1] / 60
    m = _DUR.match(v)
    if not m:
        return None
    x, u = float(m.group(1)), (m.group(2) or default_unit).lower()
    if u == "ms":
        return x / 60000
    if u.startswith("s"):
        return x / 60
    if u.startswith("h"):
        return x * 60
    return x


_SIZE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(b|bytes?|k|kb|kib|m|mb|mib|g|gb|gib|t|tb|tib)?\s*$", re.I)
_MUL = {"b": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3, "t": 1024 ** 4}


def size_bytes(v: str) -> float | None:
    m = _SIZE.match(str(v or "").replace(",", ""))
    if not m:
        return None
    u = (m.group(2) or "b").lower()
    return float(m.group(1)) * _MUL[u[0]]


def human(b: float) -> str:
    for u, d in (("TB", 1024 ** 4), ("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if b >= d:
            return f"{b / d:.3g} {u}"
    return f"{b:.0f} B"


def mins(x: float) -> str:
    if x is None:
        return "-"
    if x < 1:
        return f"{x * 60:.0f}s"
    if x < 120:
        return f"{x:.3g} min"
    return f"{x / 60:.3g} h"


def pct(a: list[float], q: float) -> float:
    s = sorted(a)
    if not s:
        return float("nan")
    k = (len(s) - 1) * q
    f = int(k)
    return s[f] + (s[min(f + 1, len(s) - 1)] - s[f]) * (k - f)
