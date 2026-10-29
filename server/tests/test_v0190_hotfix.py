"""v0.190.1 P0 hotfix - the four wounds found LIVE on the VPS on 2026-10-26 (load 147, healthz silent,
santosh flapping) and what each now does about it:

1. the kaam_followups table NEVER existed on the live DB: the model had only lazy imports (worker.tick and
   kaamwatch.enqueue both import it inside the function), so init_db's create_all() never saw it - every tick
   since v0.187 went live died 'no such table: kaam_followups' and finished jobs never reported; the owner's
   'jab result aaye to batana' was a broken promise in production. Fix: init_db registers the model AND
   kaam_followup.ensure_table() self-heals on the first tick / enqueue (old DBs repair themselves at deploy).
2. the TV catalog refresh ran on the first loop of EVERY process start - a restart-y server re-fetched every
   iptv-org list and re-probed every stream with 24 workers each boot (thousands of httpx GETs). Fix:
   catalog._needs_refresh() skips while channels.json is under 23h old.
3. the browser live/frame endpoints were polled ~90 rps during the spiral - a 1 s per-(tenant, session) memo
   caps the pile-up without changing what she sees (phone polls every 4 s, it never notices).
4. httpx/httpcore INFO logging silenced - every probe was a stderr line; the error log and the disk drowned.
"""
import asyncio
import logging
import os
import time

from sqlalchemy import text

import app.kaam_followup as kf
from app.tv import catalog as tv

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0187_realtime import fu  # noqa: F401


def _drop_table() -> None:
    """Make the DB look exactly like the live VPS: born before the model was registered."""
    from app.db import _engine
    with _engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS kaam_followups"))


def _table_exists() -> bool:
    from app.db import _engine
    with _engine.connect() as c:
        return bool(c.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='kaam_followups'")).first())


# ---------------- 1. the table that never was ----------------

def test_tick_survives_missing_table_and_self_heals(fu, monkeypatch):
    """The live wound: tick() every 10 s against a DB without the table. Now the first tick creates it."""
    _drop_table()
    monkeypatch.setattr(kf, "_table_ready", False)
    assert not _table_exists()
    assert asyncio.run(kf.tick()) == 0          # no 'no such table', the loop keeps its slot
    assert _table_exists()                      # self-healed in place


def test_enqueue_self_heals_and_the_report_flows(fu, monkeypatch):
    """The promise: kaamwatch.enqueue must now actually QUEUE the news on an old DB (before, the INSERT died
    silently in its try/except and the job's result never reached her)."""
    _drop_table()
    monkeypatch.setattr(kf, "_table_ready", False)
    ok = kf.enqueue("default", fu["conv"], {"key": "yt:job1", "kind": "youtube", "label": "reel",
                                            "title": "Diwali reel", "state": "done", "detail": "taiyaar"})
    assert ok is True
    from app.db import session
    with session() as s:
        row = s.query(kf.KaamFollowup).filter(kf.KaamFollowup.key == "yt:job1").one()
        assert row.status == "pending"


def test_init_db_creates_the_table_on_restart(env):
    """What actually happens at deploy: the service restarts, init_db() runs create_all with the model NOW
    registered - the missing table appears without any manual SQL."""
    _drop_table()
    from app.db import init_db
    init_db()
    assert _table_exists()


def test_ensure_table_is_idempotent(fu):
    """Second touch is a no-op (the flag) - the tick every 10 s must not re-run DDL."""
    kf.ensure_table()
    from app.db import _engine
    with _engine.begin() as c:
        c.execute(text("DROP TABLE kaam_followups"))     # flag says ready: nothing re-creates it...
    kf.ensure_table()
    assert not _table_exists()                           # ...which is fine: init_db made it at boot
    monkey_free = kf._table_ready
    assert monkey_free is True


# ---------------- 2. the TV refresh that ran at every boot ----------------

def test_needs_refresh_fresh_list_skips(tmp_path, monkeypatch):
    """A fresh channels.json (under 23 h old) means NO refresh at boot - the restart-y server stops
    re-probing the world's TV."""
    f = tmp_path / "channels.json"
    f.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(tv, "_file", lambda: f)
    assert tv._needs_refresh(24 * 3600) is False                     # fresh: skip

    os.utime(f, (time.time() - 25 * 3600,) * 2)                      # 25 h old: genuinely stale
    assert tv._needs_refresh(24 * 3600) is True

    f.unlink()                                                       # missing: first boot refreshes once
    assert tv._needs_refresh(24 * 3600) is True


def test_refresh_in_background_guards_reentry(monkeypatch):
    """The old daemon guard stays: when a thread is already running, a second call starts nothing."""
    monkeypatch.setattr(tv, "_bg", True)     # pretend the daemon is alive
    tv.refresh_in_background()               # must return early, quietly
    assert tv._bg is True


# ---------------- 3. the browser memo that caps the ~90 rps pile-up ----------------

def test_browser_memo_ttl_and_eviction():
    from app import main as M
    M._browser_memo.clear()
    M._browser_memo_put(("live", "t1", "pcop_1"), {"url": "https://x"})
    assert M._browser_memo_get(("live", "t1", "pcop_1")) == {"url": "https://x"}
    assert M._browser_memo_get(("live", "t1", "pcop_2")) is None     # a different session never shares

    key = ("frame", "t1", "pcop_1")
    M._browser_memo[key] = (time.time() - 5, b"old-jpeg")            # older than the 1 s TTL
    assert M._browser_memo_get(key) is None                          # expired -> the handler runs again

    for i in range(M._BROWSER_MEMO_MAX + 10):                        # the cap: the oldest entries fall off
        M._browser_memo_put(("live", f"t{i}", f"s{i}"), i)
    assert len(M._browser_memo) == M._BROWSER_MEMO_MAX
    assert M._browser_memo_get(("live", "t0", "s0")) is None         # evicted
    M._browser_memo.clear()


# ---------------- 4. the httpx log flood ----------------

def test_quiet_http_logs():
    """Every TV probe logged an INFO line to stderr; now httpx speaks only at WARNING and above."""
    from app import main as M
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    M._quiet_http_logs()
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.221.0"
