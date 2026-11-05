"""v0.559 CHALTI WEBSITE (web Step 7 part 2 = W14 of docs/WEB_PLATFORM_PLAN.md): running her website, measured.

What already existed and is NOT repeated here: page views counted by the server (care.py, no cookies, no IP kept), uptime
from inside + outside with a `site_down` card after two misses (hosting.py), the dashboard (dash.py), the monthly care
note (care.py) and the daily off-server backup (backup.py).

What this adds:
- ERRORS from her visitors' browsers: a few lines in hoola-site.js send a page's JavaScript errors (message, file name,
  line - never the visitor, never a query string, long numbers / emails masked) to /api/site-ops/<site>/beacon with
  `navigator.sendBeacon` (allowed by the site's own CSP: the same host her forms already post to). At most 5 per page view.
- SPEED from real visits: time to first byte, first paint, largest paint (LCP) and layout shift (CLS), once per page
  view, counted into fixed BANDS (never raw timings, never per-visitor rows); p75 is read from the bands and SAID as a
  band ("LCP p75 at most 2.5 s"). INP is not measured and is said to be not measured.
- COST per site: what building + changing it cost in AI calls (Site.cost_usd, list price x the server's rate) - said as
  model cost only; hosting is shared and not split per site.
- ALERTS in her chat (`site_ops` card), one line per kind per site per IST day: an ERROR spike (>= 25 errors today and
  >= 3x her own 7-day daily median), SLOW pages (LCP p75 over 4 s with >= 30 visits measured, and worse than her own
  last 7 days when those exist), and a BACKUP that did not restore cleanly (see below). Downtime keeps its own card.
- RESTORE TEST: after each daily backup, the archive is DOWNLOADED back, unpacked into a temp folder and compared with
  the live files: every published site folder must be there with its index.html, and every live file that has not
  changed since the backup must come back byte-identical (sha256). A site whose files fail = an alert to its owner.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import statistics
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, session

log = logging.getLogger("santosh.site.ops")
IST = timezone(timedelta(hours=5, minutes=30))

# band edges (upper bounds). A value lands in the first band whose edge it does not exceed; the last band is "more".
MS_EDGES = [100, 200, 300, 500, 800, 1200, 1800, 2500, 3000, 4000, 6000, 10000]
CLS_EDGES = [0.01, 0.025, 0.05, 0.1, 0.15, 0.25, 0.4]
METRICS = {"ttfb": MS_EDGES, "fcp": MS_EDGES, "lcp": MS_EDGES, "cls": CLS_EDGES}
GOOD = {"lcp": 2500, "fcp": 1800, "ttfb": 800, "cls": 0.1}       # Google's published "good" lines (web.dev Core Web Vitals)
POOR = {"lcp": 4000, "fcp": 3000, "ttfb": 1800, "cls": 0.25}

MAX_BODY = 8192
MAX_ERRORS_PER_VIEW = 5
TOP_ERRORS = 30
IP_CAP, IP_WINDOW = 120, 600            # beacons per visitor address per 10 minutes (memory only, hashed)
SITE_DAY_CAP = 50000                    # events per site per day, then counted as dropped
ERR_SPIKE_MIN, ERR_SPIKE_X = 25, 3.0
SLOW_LCP_MS, SLOW_MIN_SAMPLES, SLOW_WORSE_X = 4000, 30, 1.5


class SiteOpsDay(Base):
    __tablename__ = "site_ops_days"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sod"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)                 # IST yyyy-mm-dd
    errors: Mapped[int] = mapped_column(Integer, default=0)
    err_top: Mapped[str] = mapped_column(Text, default="{}")                 # "message | file:line" -> count (top 30)
    err_pages: Mapped[str] = mapped_column(Text, default="{}")               # path -> errors
    speed: Mapped[str] = mapped_column(Text, default="{}")                   # metric -> band counts
    samples: Mapped[int] = mapped_column(Integer, default=0)                 # page views that sent timings
    dropped: Mapped[int] = mapped_column(Integer, default=0)
    alerts: Mapped[str] = mapped_column(Text, default="[]")                  # alert kinds already said today


_OK = False
_LOCK = threading.Lock()
_BUF: dict[tuple[str, str, str], dict[str, Any]] = {}
_IP: dict[str, list[float]] = {}
_SITES: dict[str, Any] = {"at": 0.0, "map": {}}


def ensure_tables() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        SiteOpsDay.__table__.create(_db._engine, checkfirst=True)
        try:
            _db.add_missing_columns_for(_db._engine, SiteOpsDay.__table__)
        except Exception:                                   # noqa: BLE001
            log.exception("site ops columns")
        try:                                                # one row per site per day, even with 4 workers flushing
            from sqlalchemy import text as _t
            with _db._engine.begin() as c:
                c.execute(_t("CREATE UNIQUE INDEX IF NOT EXISTS ux_site_ops_day ON site_ops_days (site_id, day)"))
        except Exception:                                   # noqa: BLE001
            log.warning("site ops unique index not made")
        _OK = True


def _today(t: datetime | None = None) -> str:
    return (t or datetime.now(timezone.utc)).astimezone(IST).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- what a beacon may carry
_MASK = [(re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"), (re.compile(r"\d{6,}"), "[n]"),
         (re.compile(r"https?://[^\s'\"]+"), lambda m: re.sub(r"[?#].*", "", m.group(0)))]


def clean_message(m: Any) -> str:
    s = re.sub(r"\s+", " ", str(m or "")).strip()[:200]
    for rx, rep in _MASK:
        s = rx.sub(rep, s)
    return s or "(no message)"


def clean_file(f: Any) -> str:
    s = re.sub(r"[?#].*", "", str(f or ""))
    return (s.rsplit("/", 1)[-1] or "")[:60]


def clean_path(p: Any) -> str:
    s = re.sub(r"[?#].*", "", str(p or "/"))[:120]
    return s if s.startswith("/") else "/" + s


def band(metric: str, v: float) -> int:
    edges = METRICS[metric]
    for i, e in enumerate(edges):
        if v <= e:
            return i
    return len(edges)


def band_label(metric: str, i: int) -> str:
    edges = METRICS[metric]
    if i >= len(edges):
        return f"over {_fmt(metric, edges[-1])}"
    return f"at most {_fmt(metric, edges[i])}"


def _fmt(metric: str, v: float) -> str:
    if metric == "cls":
        return f"{v:g}"
    return f"{v / 1000:g} s" if v >= 1000 else f"{int(v)} ms"


def p75(bins: list[int]) -> int | None:
    """The band index holding the 75th percentile of counted values (None = nothing counted)."""
    total = sum(bins)
    if not total:
        return None
    need, run = 0.75 * total, 0
    for i, n in enumerate(bins):
        run += n
        if run >= need:
            return i
    return len(bins) - 1


def p75_value(metric: str, bins: list[int]) -> float | None:
    """The band's UPPER edge as a number (a band, not a measurement: 'at most'). Over the last edge = that edge x 1.5."""
    i = p75(bins)
    if i is None:
        return None
    edges = METRICS[metric]
    return edges[i] if i < len(edges) else edges[-1] * 1.5


# ---------------------------------------------------------------- the beacon
def _site_tenant(site_id: str) -> str | None:
    """Only real websites (cached a minute); an unknown id is ignored, never stored."""
    now_ = time.time()
    if now_ - _SITES["at"] > 60:
        from .models import Site
        with session() as s:
            _SITES["map"] = {i: t for i, t in s.execute(select(Site.id, Site.tenant_id)).all()}
        _SITES["at"] = now_
    return _SITES["map"].get(site_id)


def _ip_ok(ip: str) -> bool:
    k = hashlib.sha256(f"ops|{ip}".encode()).hexdigest()[:20]
    t = time.time()
    hits = [x for x in _IP.get(k, []) if t - x < IP_WINDOW]
    if len(hits) >= IP_CAP:
        _IP[k] = hits
        return False
    _IP[k] = hits + [t]
    if len(_IP) > 20000:
        for kk in [kk for kk, v in _IP.items() if not v or t - v[-1] > IP_WINDOW]:
            _IP.pop(kk, None)
    return True


def _slot(site: str, tenant: str, day: str) -> dict[str, Any]:
    return _BUF.setdefault((site, tenant, day), {"errors": 0, "top": {}, "pages": {}, "samples": 0, "dropped": 0,
                                                 "speed": {m: [0] * (len(e) + 1) for m, e in METRICS.items()}})


def record(site_id: str, raw: bytes | str, ip: str = "") -> bool:
    """One beacon from a visitor's browser. Returns whether anything was counted. Never raises on bad input."""
    if not re.fullmatch(r"[\w-]{3,40}", site_id or ""):
        return False
    if isinstance(raw, bytes):
        if len(raw) > MAX_BODY:
            return False
        raw = raw.decode("utf-8", "replace")
    if len(raw or "") > MAX_BODY:
        return False
    try:
        b = json.loads(raw or "{}")
    except ValueError:
        return False
    if not isinstance(b, dict):
        return False
    tenant = _site_tenant(site_id)
    if not tenant or not _ip_ok(ip):
        return False
    day, path = _today(), clean_path(b.get("p"))
    errs = b.get("e") if isinstance(b.get("e"), list) else []
    sp = b.get("s") if isinstance(b.get("s"), dict) else {}
    with _LOCK:
        x = _slot(site_id, tenant, day)
        if x["errors"] + x["samples"] >= SITE_DAY_CAP:
            x["dropped"] += 1
            return False
        n = 0
        for e in errs[:MAX_ERRORS_PER_VIEW]:
            if not isinstance(e, dict):
                continue
            line = e.get("l")
            line = int(line) if isinstance(line, (int, float)) and 0 <= line < 10 ** 7 else 0
            key = clean_message(e.get("m")) + (f" | {clean_file(e.get('f'))}:{line}" if e.get("f") else "")
            x["top"][key] = x["top"].get(key, 0) + 1
            x["pages"][path] = x["pages"].get(path, 0) + 1
            x["errors"] += 1
            n += 1
        got = False
        for m in METRICS:
            v = sp.get(m)
            if isinstance(v, (int, float)) and v >= 0 and (v < 120000 if m != "cls" else v < 50):
                x["speed"][m][band(m, float(v))] += 1
                got = True
        if got:
            x["samples"] += 1
    return bool(n or got)


def flush() -> None:
    with _LOCK:
        items = list(_BUF.items())
        _BUF.clear()
    if not items:
        return
    ensure_tables()
    from sqlalchemy.exc import IntegrityError
    for key, b in items:
        for _ in range(2):                                  # a twin worker created today's row first: add to that one
            try:
                _flush_one(key, b)
                break
            except IntegrityError:
                continue
            except Exception:
                log.exception("site ops flush failed")
                break


def _flush_one(key: tuple[str, str, str], b: dict[str, Any]) -> None:
    site, tenant, day = key
    with session() as s:
        row = s.scalars(select(SiteOpsDay).where(SiteOpsDay.site_id == site, SiteOpsDay.day == day)
                        .with_for_update()).first()
        if row is None:
            row = SiteOpsDay(site_id=site, tenant_id=tenant, day=day)
            s.add(row)
            s.flush()
        row.errors = (row.errors or 0) + b["errors"]
        row.samples = (row.samples or 0) + b["samples"]
        row.dropped = (row.dropped or 0) + b["dropped"]
        top = json.loads(row.err_top or "{}")
        for k, n in b["top"].items():
            top[k] = top.get(k, 0) + n
        row.err_top = json.dumps(dict(sorted(top.items(), key=lambda kv: -kv[1])[:TOP_ERRORS]), ensure_ascii=False)
        pages = json.loads(row.err_pages or "{}")
        for k, n in b["pages"].items():
            pages[k] = pages.get(k, 0) + n
        row.err_pages = json.dumps(dict(sorted(pages.items(), key=lambda kv: -kv[1])[:TOP_ERRORS]))
        sp = json.loads(row.speed or "{}")
        for m, bins in b["speed"].items():
            have = sp.get(m) or [0] * len(bins)
            sp[m] = [a + c for a, c in zip(have, bins)]
        row.speed = json.dumps(sp)


# ---------------------------------------------------------------- reading it back
def _rows(site_id: str, a: str, b: str) -> list[SiteOpsDay]:
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(SiteOpsDay).where(SiteOpsDay.site_id == site_id, SiteOpsDay.day >= a,
                                                  SiteOpsDay.day <= b).order_by(SiteOpsDay.day)).all()
        for r in rows:
            s.expunge(r)
    return rows


def _merge_speed(rows: list[SiteOpsDay]) -> dict[str, list[int]]:
    out = {m: [0] * (len(e) + 1) for m, e in METRICS.items()}
    for r in rows:
        for m, bins in json.loads(r.speed or "{}").items():
            if m in out:
                out[m] = [a + c for a, c in zip(out[m], bins)]
    return out


def speed_view(bins: dict[str, list[int]], samples: int) -> dict[str, Any]:
    out: dict[str, Any] = {"samples": samples, "inp": "not measured"}
    for m in METRICS:
        i = p75(bins.get(m) or [])
        if i is None:
            out[m] = None
            continue
        v = p75_value(m, bins[m])
        grade = "good" if v <= GOOD[m] else ("poor" if v > POOR[m] else "needs work")
        out[m] = {"p75": band_label(m, i), "p75_max": v, "grade": grade}
    return out


def cost_view(site) -> dict[str, Any]:
    from ..config import get_settings
    usd = float(getattr(site, "cost_usd", 0) or 0)
    rate = float(getattr(get_settings(), "usd_inr", 0) or 0) or 84.0
    return {"ai_usd": round(usd, 4), "ai_inr": round(usd * rate, 2), "rate": rate,
            "note": "AI cost of building and changing this site (list price x the server's rate). Hosting is shared "
                    "across sites and not split per site."}


def summary(site_id: str, days: int = 30, end: datetime | None = None) -> dict[str, Any]:
    """Errors + speed for a site over `days` IST days ending today, with the same window before it for comparison."""
    flush()
    t = (end or datetime.now(timezone.utc)).astimezone(IST)
    b = t.strftime("%Y-%m-%d")
    a = (t - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    pa = (t - timedelta(days=2 * days - 1)).strftime("%Y-%m-%d")
    pb = (t - timedelta(days=days)).strftime("%Y-%m-%d")
    cur, prev = _rows(site_id, a, b), _rows(site_id, pa, pb)
    top: dict[str, int] = {}
    pages: dict[str, int] = {}
    for r in cur:
        for k, n in json.loads(r.err_top or "{}").items():
            top[k] = top.get(k, 0) + n
        for k, n in json.loads(r.err_pages or "{}").items():
            pages[k] = pages.get(k, 0) + n
    samples = sum(r.samples or 0 for r in cur)
    return {"from": a, "to": b, "errors": sum(r.errors or 0 for r in cur), "errors_prev": sum(r.errors or 0 for r in prev),
            "error_days": {r.day: r.errors or 0 for r in cur},
            "top_errors": sorted(top.items(), key=lambda kv: -kv[1])[:10],
            "error_pages": sorted(pages.items(), key=lambda kv: -kv[1])[:10],
            "speed": speed_view(_merge_speed(cur), samples),
            "speed_prev": speed_view(_merge_speed(prev), sum(r.samples or 0 for r in prev)),
            "dropped": sum(r.dropped or 0 for r in cur)}


# ---------------------------------------------------------------- alerts in her chat
def _said(row: SiteOpsDay, kind: str) -> bool:
    return kind in json.loads(row.alerts or "[]")


def _mark(site_id: str, day: str, kind: str) -> bool:
    """Atomically claim today's line for this kind; False = another worker already said it."""
    with session() as s:
        row = s.scalars(select(SiteOpsDay).where(SiteOpsDay.site_id == site_id, SiteOpsDay.day == day)
                        .with_for_update()).first()
        if row is None:
            return False
        said = json.loads(row.alerts or "[]")
        if kind in said:
            return False
        row.alerts = json.dumps(said + [kind])
    return True


def _tell(site, kind: str, say: str, extra: dict[str, Any] | None = None) -> None:
    from . import service as S
    S._publish(site.tenant_id, "site_ops", {"site": site.id, "name": site.name, "kind": kind, "say": say,
                                            "push": True, **(extra or {})}, site.conv)


def check_alerts(now_: datetime | None = None) -> list[dict[str, Any]]:
    """Worker: today's rows against each site's OWN last 7 days. Returns what was said (for tests and the log)."""
    flush()
    ensure_tables()
    t = (now_ or datetime.now(timezone.utc)).astimezone(IST)
    day = t.strftime("%Y-%m-%d")
    week = [(t - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 8)]
    from .models import Site
    with session() as s:
        today = s.scalars(select(SiteOpsDay).where(SiteOpsDay.day == day)).all()
        for r in today:
            s.expunge(r)
    said: list[dict[str, Any]] = []
    for row in today:
        hist = _rows(row.site_id, week[-1], week[0])
        with session() as s:
            site = s.get(Site, row.site_id)
            if site is None:
                continue
            s.expunge(site)
        # errors: >= 25 today AND >= 3x her own median day (a site that always has 40 is not "spiking" at 45)
        med = statistics.median([h.errors or 0 for h in hist]) if hist else 0
        if (row.errors or 0) >= max(ERR_SPIKE_MIN, ERR_SPIKE_X * med) and not _said(row, "errors"):
            top = sorted(json.loads(row.err_top or "{}").items(), key=lambda kv: -kv[1])[:1]
            if _mark(row.site_id, day, "errors"):
                say = (f"{site.name or 'Website'}: aaj visitors ke browser mein {row.errors} JavaScript galtiyan"
                       + (f" (aam din ~{int(med)})" if hist else "")
                       + (f"; sabse zyada: \"{top[0][0][:90]}\" ({top[0][1]} baar)" if top else "")
                       + ". 'website ki galti dekho' kahiye.")
                _tell(site, "errors", say, {"errors": row.errors, "median": med})
                said.append({"site": row.site_id, "kind": "errors"})
        # slow: LCP p75 over 4 s on >= 30 measured visits, and worse than her own week when the week was measured
        sp = json.loads(row.speed or "{}").get("lcp") or []
        if (row.samples or 0) >= SLOW_MIN_SAMPLES and sp and not _said(row, "slow"):
            v = p75_value("lcp", sp) or 0
            wk = _merge_speed(hist)["lcp"]
            wv = p75_value("lcp", wk) if sum(wk) >= SLOW_MIN_SAMPLES else None
            if v > SLOW_LCP_MS and (wv is None or v >= SLOW_WORSE_X * wv):
                if _mark(row.site_id, day, "slow"):
                    say = (f"{site.name or 'Website'} aaj dheemi khul rahi hai: {row.samples} visits mein main hissa "
                           f"dikhne mein {band_label('lcp', p75(sp))} laga (75% visits)"
                           + (f"; pichhle hafte {band_label('lcp', p75(wk))}" if wv else "")
                           + ". 'website tez karo' kahiye.")
                    _tell(site, "slow", say, {"lcp_p75_max": v})
                    said.append({"site": row.site_id, "kind": "slow"})
    return said


# ---------------------------------------------------------------- the restore test
def _state() -> Path:
    from . import backup as BK
    return BK._state().parent / "sites_restore_test.json"


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compare(restored: Path, hosted: Path, taken_at: float, cap: int = 4000) -> dict[str, Any]:
    """The restored copy against the live published sites. Per site folder: present + index.html; every live file
    that did NOT change after the backup was taken must come back byte-identical. Files changed after `taken_at` are
    skipped (a backup cannot hold the future); files deleted since are fine."""
    rh = restored / "hosted"
    sites: dict[str, dict[str, Any]] = {}
    checked = 0
    if hosted.exists():
        for live in sorted(hosted.iterdir()):
            if live.name.startswith(".") or live.is_symlink() or not live.is_dir():
                continue
            if live.stat().st_mtime > taken_at and not (rh / live.name).exists():
                continue                                      # a site published after the backup: next night's job
            res = {"missing": [], "changed": [], "checked": 0}
            back = rh / live.name
            if not back.is_dir():
                res["missing"].append("(the whole site)")
            elif not (back / "index.html").is_file():
                res["missing"].append("index.html")
            else:
                for f in sorted(live.rglob("*")):
                    if checked >= cap:
                        break
                    if not f.is_file() or f.is_symlink() or f.stat().st_mtime > taken_at:
                        continue
                    rel = f.relative_to(live)
                    b = back / rel
                    if not b.is_file():
                        res["missing"].append(rel.as_posix())
                    elif _sha(b) != _sha(f):
                        res["changed"].append(rel.as_posix())
                    res["checked"] += 1
                    checked += 1
            res["ok"] = not res["missing"] and not res["changed"]
            res["missing"], res["changed"] = res["missing"][:10], res["changed"][:10]
            sites[live.name] = res
    bad = [k for k, v in sites.items() if not v["ok"]]
    return {"sites": len(sites), "files_checked": checked, "bad": bad, "detail": {k: sites[k] for k in bad},
            "ok": not bad, "capped": checked >= cap}


def restore_test(day: str = "") -> dict[str, Any]:
    """Download the backup back, unpack it into a temp folder, compare it with what is live. The result is kept."""
    from . import backup as BK
    if not BK.enabled():
        return {"ok": None, "why": "backup is off (SITES_BACKUP_BUCKET / keys not set)"}
    st = BK.status().get("last") or {}
    day = day or st.get("day") or ""
    taken = float(st.get("at") or 0) or time.time()
    started = time.time()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            info = BK.restore(day, Path(tmp))
            hosted, _ = BK._roots()
            res = compare(Path(tmp), hosted, taken)
        res |= {"day": day, "restored_files": info.get("restored", 0)}
    except Exception as e:                                  # noqa: BLE001 - a backup that cannot come back IS the finding
        res = {"ok": False, "day": day, "error": str(e)[:300], "sites": 0, "files_checked": 0, "bad": ["(download)"]}
    res |= {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seconds": round(time.time() - started, 1)}
    try:
        _state().write_text(json.dumps(res))
    except OSError:
        log.warning("restore test result not saved")
    log.info("website restore test: ok=%s sites=%s files=%s bad=%s", res.get("ok"), res.get("sites"),
             res.get("files_checked"), res.get("bad"))
    if res.get("ok") is False:
        _tell_restore(res)
    return res


def _tell_restore(res: dict[str, Any]) -> None:
    """Each live site whose files did not come back -> its owner hears it once that day (a failed download -> every
    owner with a live site, because none of them is covered)."""
    from .hosting import SiteHost
    from .models import Site
    whole = "(download)" in (res.get("bad") or [])
    with session() as s:
        hosts = s.scalars(select(SiteHost).where(SiteHost.status == "active")).all()
        bad = set(res.get("bad") or [])                       # hosted folders are named by hostname
        pick = [(h.site_id, h.hostname) for h in hosts if whole or h.hostname in bad]
    seen: set[str] = set()
    day = _today()
    for site_id, host in pick:
        if site_id in seen:
            continue
        seen.add(site_id)
        with session() as s:
            site = s.get(Site, site_id)
            if site is None:
                continue
            s.expunge(site)
            if s.scalars(select(SiteOpsDay).where(SiteOpsDay.site_id == site_id, SiteOpsDay.day == day)).first() is None:
                s.add(SiteOpsDay(site_id=site_id, tenant_id=site.tenant_id, day=day))
        if not _mark(site_id, day, "backup"):
            continue
        why = res.get("error") or "kuch files waapas waisi nahi aayin"
        _tell(site, "backup", f"{site.name or host}: kal raat ka backup waapas laane ki jaanch fail hui ({why[:120]}). "
                              "Website abhi theek chal rahi hai; backup ko theek karwana zaroori hai.", {"day": res.get("day")})


def restore_status() -> dict[str, Any]:
    try:
        return json.loads(_state().read_text())
    except (OSError, ValueError):
        return {}


def daily_restore_test(now_: datetime | None = None) -> dict[str, Any] | None:
    """Worker: once a day, after that day's backup is done (and after 04:00 IST so the backup had its hour)."""
    from . import backup as BK
    if not BK.enabled():
        return None
    t = (now_ or datetime.now(timezone.utc)).astimezone(IST)
    if t.hour < 4:
        return None
    last = BK.status().get("last") or {}
    if not last.get("ok") or last.get("day") != t.strftime("%Y-%m-%d"):
        return None
    if restore_status().get("day") == last.get("day"):
        return None
    return restore_test(last["day"])


_TICK = {"at": 0.0}
TICK_EVERY_S = 300


def tick(force: bool = False) -> None:
    """Worker slot (at most every 5 minutes): flush the beacons, say what needs saying, run the night's restore test."""
    if not force and time.time() - _TICK["at"] < TICK_EVERY_S:
        return
    _TICK["at"] = time.time()
    try:
        flush()
        check_alerts()
    except Exception:
        log.exception("site ops alerts failed")
    try:
        daily_restore_test()
    except Exception:
        log.exception("site restore test failed")


def owner_view(tenant: str, ref: str = "", days: int = 30) -> dict[str, Any]:
    """Her site's running health: visitors' errors, real-visit speed, AI cost, last backup + restore test."""
    from . import backup as BK
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    days = max(1, min(int(days or 30), 90))
    out = summary(r.id, days)
    rs = restore_status()
    bk = BK.status()
    host_ok = True
    if rs.get("ok") is False:
        from .hosting import SiteHost
        with session() as s:
            mine = {h.hostname for h in s.scalars(select(SiteHost).where(SiteHost.site_id == r.id)).all()}
        host_ok = not ("(download)" in (rs.get("bad") or []) or mine & set(rs.get("bad") or []))
    out |= {"site": {"id": r.id, "name": r.name}, "days": days, "cost": cost_view(r),
            "backup": {"enabled": bk.get("enabled"), "last_day": (bk.get("last") or {}).get("day"),
                       "restore_test": {"day": rs.get("day"), "ok": (rs.get("ok") if rs.get("ok") is not False else host_ok),
                                        "at": rs.get("at"), "files_checked": rs.get("files_checked")} if rs else None}}
    lcp = (out["speed"].get("lcp") or {})
    out["say"] = (f"{r.name}: {days} din mein visitors ke browser mein {out['errors']} galtiyan"
                  + (f" (pichhle {days} din {out['errors_prev']})" if out["errors_prev"] else "")
                  + (f"; main hissa dikhne mein {lcp['p75']} (75% visits, {out['speed']['samples']} visits naape)" if lcp else
                     "; speed abhi naapi nahi gayi (koi visit nahi aayi)")
                  + f"; banane ka AI kharcha ~₹{out['cost']['ai_inr']:,.0f}."
                  + (" Backup waapas laane ki jaanch: theek." if out["backup"]["restore_test"] and out["backup"]["restore_test"]["ok"]
                     else (" Backup waapas laane ki jaanch FAIL." if out["backup"]["restore_test"] else "")))
    return out
