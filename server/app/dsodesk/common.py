"""Small shared pieces of the DevSecOps Engineer desk: the findings list, table columns found by name,
and the closing counts every reader returns."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Callable


class DsoInputError(ValueError):
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


def norm(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(h).lower())


def col(head: list[str], *pats: str) -> int | None:
    """The first column whose normalised name fully matches one of the patterns (tried in order)."""
    low = [norm(h) for h in head]
    for p in pats:
        for i, h in enumerate(low):
            if re.fullmatch(p, h):
                return i
    return None


def money(v: Any) -> float | None:
    """'1,234.50', '$12', '12 EUR', '(5.00)' -> a number; blank -> None."""
    s = str(v if v is not None else "").strip()
    if not s or s.lower() in ("-", "na", "n/a", "null", "none"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^\d.\-eE]", "", s.replace(",", ""))
    if not s or s in ("-", "."):
        return None
    try:
        x = float(s)
    except ValueError:
        raise DsoInputError(f"'{v}' is not an amount.")
    return -abs(x) if neg else x


def num(v: Any) -> float | None:
    s = str(v if v is not None else "").strip().replace(",", "").rstrip("%")
    if not s or s.lower() in ("-", "na", "n/a", "null", "none"):
        return None
    try:
        return float(s)
    except ValueError:
        raise DsoInputError(f"'{v}' is not a number.")


def day(v: Any) -> date | None:
    """A date or timestamp in the usual export shapes -> a date."""
    s = str(v or "").strip()
    if not s:
        return None
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            raise DsoInputError(f"'{v}' is not a date.")
    m = re.match(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m:   # day first unless it cannot be (the export's own order is unknown; 13+ settles it)
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        d_, mo = (a, b) if a > 12 else (b, a) if b > 12 else (a, b)
        try:
            return date(y, mo, d_)
        except ValueError:
            raise DsoInputError(f"'{v}' is not a date.")
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        raise DsoInputError(f"'{v}' is not a date (use 2026-11-28).")


def amt(x: float | None, cur: str = "") -> str:
    if x is None:
        return "-"
    c = (cur or "").strip()
    s = f"{x:,.2f}" if abs(x) < 1000 else f"{x:,.0f}"
    return f"{s} {c}".strip()


def pct(x: float | None) -> str:
    return "-" if x is None else f"{x * 100:.0f}%"


def median(a: list[float]) -> float:
    s = sorted(a)
    n = len(s)
    if not n:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quantile(a: list[float], q: float) -> float:
    s = sorted(a)
    if not s:
        return float("nan")
    k = (len(s) - 1) * q
    f = int(k)
    return s[f] + (s[min(f + 1, len(s) - 1)] - s[f]) * (k - f)
