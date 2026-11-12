"""v0.390 PAKKI NEEV: how much each app uses, and its limits - counted from the database (right across every worker).

  rows per list, data size, accounts, files on disk, backups, writes per day (from the journal) and the last 14 days.
  Limits (her app's quota): rows (enforced: at 100% a new row is refused with a plain message, her data is never
  touched), files MB and writes a day (watched: the daily check tells her). Defaults below; she may raise them up to
  the hard ceiling. At 80% and 95% her chat gets ONE note per level per month."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from ..db import now, session
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
DEFAULT = {"rows": 50_000, "files_mb": 2_048, "writes_day": 50_000}
CEILING = {"rows": 2_000_000, "files_mb": 51_200, "writes_day": 2_000_000}
LEVELS = (80, 95, 100)


def _site(r: AppProject) -> str:
    return "app:" + r.id


def limits(r: AppProject) -> dict[str, int]:
    be = json.loads(r.backend or "{}")
    q = be.get("quota") if isinstance(be.get("quota"), dict) else {}
    return {k: int(min(CEILING[k], max(1, int(q.get(k) or v)))) for k, v in DEFAULT.items()}


def _dir_mb(p: Path) -> float:
    if not p.exists():
        return 0.0
    return round(sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1_048_576, 2)


def usage(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    from . import backup as BK
    from . import kit as K
    BK.ensure_table()
    site = _site(r)
    with session() as s:
        per = dict(s.execute(select(W.SiteAppRow.coll, func.count()).where(W.SiteAppRow.site_id == site)
                             .group_by(W.SiteAppRow.coll)).all())
        size = s.scalar(select(func.sum(func.length(W.SiteAppRow.data))).where(W.SiteAppRow.site_id == site)) or 0
        mem = s.scalar(select(func.count()).select_from(W.SiteAppMember).where(W.SiteAppMember.site_id == site)) or 0
        since = datetime.now(timezone.utc) - timedelta(days=14)
        days: dict[str, int] = {}
        for (at,) in s.execute(select(BK.AppJournal.at).where(BK.AppJournal.site_id == site, BK.AppJournal.at >= since)).all():
            if at is None:
                continue
            d = (at if at.tzinfo else at.replace(tzinfo=timezone.utc)).astimezone(timezone(timedelta(hours=5, minutes=30))).date().isoformat()
            days[d] = days.get(d, 0) + 1
    base = K.app_dir(r.tenant_id, r.id) / "backend"
    lists = {k: int(v) for k, v in per.items() if not k.startswith("_")}
    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date().isoformat()
    lim = limits(r)
    use = {"rows": sum(lists.values()), "files_mb": _dir_mb(base / "files"), "writes_day": days.get(today, 0)}
    pct = {k: round(100 * use[k] / lim[k], 1) for k in lim}
    del BE
    return {"lists": lists, "rows": use["rows"], "data_kb": round(int(size) / 1024, 1), "accounts": int(mem),
            "files_mb": use["files_mb"], "backups_mb": _dir_mb(base / "backups"), "writes_today": use["writes_day"],
            "writes_14d": dict(sorted(days.items())), "approvals_waiting": int(per.get("_approval", 0)),
            "limits": lim, "ceiling": CEILING, "percent": pct, "full": [k for k, v in pct.items() if v >= 100]}


def check_write(r: AppProject) -> None:
    """Before a new row: refuse only at 100% of rows / writes a day (with the reason); warn her at 80 / 95 once."""
    lim = limits(r)
    site = _site(r)
    with session() as s:
        rows = s.scalar(select(func.count()).select_from(W.SiteAppRow).where(W.SiteAppRow.site_id == site,
                                                                            ~W.SiteAppRow.coll.startswith("_", autoescape=True))) or 0
    pct = 100 * rows / lim["rows"]
    _warn(r, "rows", pct, rows, lim["rows"])
    if rows >= lim["rows"]:
        raise W.AppError("This app has reached its data limit; please talk to the shop.", 507)


def _warn(r: AppProject, what: str, pct: float, used: float, cap: float) -> None:
    lvl = max((x for x in LEVELS if pct >= x), default=0)
    if not lvl:
        return
    month = now().strftime("%Y-%m")
    be = json.loads(r.backend or "{}")
    told = (be.get("quota_told") or {}).get(f"{what}:{month}", 0)
    if told >= lvl:
        return
    from . import backend as BE

    def put(b):
        t = dict(b.get("quota_told") or {})
        t[f"{what}:{month}"] = lvl
        b["quota_told"] = t
    BE.patch_backend(r, fn=put)
    try:
        from .android.service import _note
        name = {"rows": "entries", "files_mb": "files (MB)", "writes_day": "writes today"}[what]
        _note(r, f"{r.name or 'Your app'} ({r.number}): {name} {used:,.0f} / {cap:,.0f} ({lvl}%). "
                 + ("New entries are stopped now - to raise the limit, see 'Limits' on the app's Data card." if lvl >= 100
                    else "To raise the limit, see 'Limits' on the app's Data card."))
    except Exception:                                # noqa: BLE001
        log.debug("quota note", exc_info=True)


def set_limits(r: AppProject, body: dict[str, Any]) -> dict[str, Any]:
    """HER choice: raise / lower her app's limits (never above the ceiling, never below what is already used)."""
    from . import backend as BE
    u = usage(r)
    q: dict[str, int] = {}
    for k in DEFAULT:
        if k not in (body or {}):
            continue
        try:
            v = int(float(str(body[k]).replace(",", "")))
        except (TypeError, ValueError):
            raise W.AppError(f"{k}: a number is needed.")
        if not 1 <= v <= CEILING[k]:
            raise W.AppError(f"{k}: from 1 to {CEILING[k]:,}.")
        used = {"rows": u["rows"], "files_mb": u["files_mb"], "writes_day": u["writes_today"]}[k]
        if v < used:
            raise W.AppError(f"{k}: {used:,.0f} is already used; the limit cannot be lower than that.")
        q[k] = v
    if not q:
        raise W.AppError("Which limit? rows / files_mb / writes_day")
    BE.patch_backend(r, fn=lambda b: b.__setitem__("quota", {**(b.get("quota") or {}), **q}))
    return {"limits": limits(r), "say": "Limit changed."}


def daily_watch(r: AppProject) -> None:
    """The daily check (with the snapshot): files + writes against her limits -> one note per level per month."""
    u = usage(r)
    for k, used in (("files_mb", u["files_mb"]), ("writes_day", max(u["writes_14d"].values(), default=0))):
        _warn(r, k, 100 * used / u["limits"][k], used, u["limits"][k])
