"""Small shared pieces of the Platform Engineer desk: the findings list, durations and sizes written the way people write them, and
the closing counts every reader returns."""
from __future__ import annotations

import re
from typing import Any, Callable


class PfInputError(ValueError):
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


_MEMU = {"": 1, "k": 1e3, "m": 1e6, "g": 1e9, "t": 1e12, "p": 1e15, "e": 1e18, "ki": 1024, "mi": 1024 ** 2, "gi": 1024 ** 3, "ti": 1024 ** 4, "pi": 1024 ** 5}


def cpu(v: Any) -> float | None:
    """A Kubernetes CPU quantity -> cores: '500m', '0.5', '2', '250000000n', '1500u'."""
    s = str(v if v is not None else "").strip().lower()
    if not s or s in ("-", "none", "null", "<none>", "na", "n/a"):
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(n|u|m|cores?|vcpus?|cpus?)?", s)
    if not m:
        raise PfInputError(f"'{v}' is not a CPU amount (500m, 0.5, 2).")
    x, u = float(m.group(1)), m.group(2) or ""
    return x / 1e9 if u == "n" else x / 1e6 if u == "u" else x / 1000 if u == "m" else x


def mem(v: Any) -> float | None:
    """A Kubernetes memory quantity -> GiB: '512Mi', '1Gi', '1G', '1.5e9', '134217728'."""
    s = str(v if v is not None else "").strip()
    if not s or s.lower() in ("-", "none", "null", "<none>", "na", "n/a"):
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?(?:e\d+)?)\s*([kKmMgGtTpPeE]i?)?[bB]?", s)
    if not m:
        raise PfInputError(f"'{v}' is not a memory amount (512Mi, 1Gi, 2G).")
    u = (m.group(2) or "").lower()
    return float(m.group(1)) * _MEMU[u] / 1024 ** 3


def cores(x: float | None) -> str:
    if x is None:
        return "-"
    return f"{x * 1000:.0f}m" if x < 1 else f"{x:.3g}"


def gib(x: float | None) -> str:
    if x is None:
        return "-"
    return f"{x * 1024:.0f}Mi" if x < 1 else f"{x:.3g}Gi"
