"""Shared helpers of the Construction & Real Estate package (v0.512.0) - the theka/sitesup shape,
small and repeated on purpose: errors, locks, Hinglish number/rupee/date formatting, the event bus
publish, and the tier-C guard every service action runs first."""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
from typing import Any

from sqlalchemy import select

from ..db import session

_LOCK = threading.RLock()


class CstError(Exception):
    pass


def guard(ask: str) -> None:
    """Tier-C gate: raise with the refusal text when the ask touches a reserved act."""
    from . import gates
    refusal = gates.tier_c_check(ask)
    if refusal:
        raise CstError(refusal)


def _j(s: str, default):
    try:
        v = json.loads(s if isinstance(s, str) else (s or ""))
        return v if isinstance(v, type(default)) else default
    except (json.JSONDecodeError, TypeError):
        return default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _num(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").replace(" ", ""))
    except ValueError:
        return 0.0


def _rs(v) -> str:
    try:
        return f"Rs {float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def today(tenant: str) -> date:
    from ..life import tz_of
    return datetime.now(tz_of(tenant)).date()


def _date(v, default: date | None = None) -> date | None:
    if isinstance(v, date):
        return v
    if v in (None, ""):
        return default
    from ..analyst.service import _date as d
    return d(str(v)[:10]) or default


def add_months(d: date, n: int) -> date:
    from calendar import monthrange
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        pass


def all_rows(s, model, tenant: str):
    return s.scalars(select(model).where(model.tenant_id == tenant)).all()
