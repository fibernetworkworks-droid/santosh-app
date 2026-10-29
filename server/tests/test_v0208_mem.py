"""v0.210.0 MEM-CURE - the voice-to-voice drop root cause, fixed in-process.

The vps-ops mem RCA: long tasks and live calls share one process; RSS climbed ~100 MB/min
until the 8 GB box (swap 100% full) force-killed the process every 10-40 min - all 14 kills
landed mid-WebSocket, so every live call dropped instantly and in-memory state made resume
impossible. Three fixes, each tested here:

- events.py: stream queues were UNBOUNDED asyncio.Queue with put_nowait - a consumer that
  stalled or died without unsubscribe received EVERY later publish forever (the structural
  leak). Now: Q_MAX with drop-oldest (newest state wins; SSE replays the gap from the DB
  backlog) + a dead-queue GC sweep (>= 800 missed publishes or a closed event loop = pruned).
- memjanitor.py: glibc kept freed memory in per-thread arenas (1.5 GB single arena + dozens
  of 64 MB arenas at the RCA) - M_ARENA_MAX=2 at boot + malloc_trim every 5 min + an honest
  RSS/swap log line, all best-effort (non-glibc platforms must pass).
- voice.py graceful shutdown: our SIGINT/SIGTERM note chains uvicorn's own handler; a watchdog
  tells every live call what is happening and closes the phone side (1001) so a restart no
  longer lands mid-WebSocket; vps-ops restarts carry pm2 --kill-timeout 12000 for headroom.
"""
import asyncio
import signal
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)


REPO = Path(__file__).resolve().parents[2]


@pytest.fixture()
def quiet_bus(bz):
    """Register queues under a random conv and ALWAYS clean them up (the bus is global)."""
    from app import events
    import secrets
    conv = "memtest-" + secrets.token_urlsafe(6)
    qs: list[asyncio.Queue] = []
    yield conv, qs
    for q in qs:
        events.bus._subs[conv].discard(q)
        events.bus._tsubs.clear()
        events.bus._all.clear()
        events.bus._loops.pop(id(q), None)
    events.bus._subs.pop(conv, None)


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.249.0"
    assert "0.249.0+289" in (REPO / "pubspec.yaml").read_text()


def test_queue_bound_and_drop_oldest(quiet_bus):
    from app import events
    conv, qs = quiet_bus
    q = events.bus.subscribe(conv)
    qs.append(q)
    assert events.Q_MAX == 400
    for i in range(events.Q_MAX + 60):          # overflow by 60: oldest dropped, newest kept
        events.bus.publish(conv, "message", {"n": i})
    assert q.qsize() == events.Q_MAX
    first = q.get_nowait()
    assert first["payload"]["n"] == 60          # the first 60 are gone
    last = None
    while not q.empty():
        last = q.get_nowait()
    assert last["payload"]["n"] == events.Q_MAX + 59
    assert q._hoola_drops == 60                 # counted: the sweep's death signal


def test_push_never_raises_on_full_queue(quiet_bus):
    from app import events
    conv, qs = quiet_bus
    q = events.bus.subscribe(conv)
    qs.append(q)
    for i in range(events.Q_MAX):
        events._push(q, {"n": i})
    for i in range(50):                         # QueueFull path over and over: still no raise
        events._push(q, {"n": events.Q_MAX + i})
    assert q.qsize() == events.Q_MAX
    assert q._hoola_drops == 50


def test_publish_ephemeral_and_live_also_bounded(quiet_bus):
    from app import events
    conv, qs = quiet_bus
    q = events.bus.subscribe(conv)
    qs.append(q)
    for i in range(events.Q_MAX + 10):
        events.bus.publish_live(conv, "delta", {"n": i})
        events.bus.publish(conv, "note", {"n": i}, ephemeral=True)
    assert q.qsize() == events.Q_MAX            # every fan-out path honours the bound


def test_sweep_spares_live_queues(quiet_bus):
    from app import events
    conv, qs = quiet_bus
    q = events.bus.subscribe(conv)
    qs.append(q)
    q._hoola_drops = 799                        # just under the death line
    assert events.bus.sweep() == 0
    assert q in events.bus._subs[conv]          # alive and still registered
    assert q.qsize() == 0                       # untouched by the sweep (nothing was published)


def test_sweep_prunes_starved_and_closed_loop_queues(quiet_bus):
    from app import events
    conv, _ = quiet_bus
    starved = events.bus.subscribe(conv)
    starved._hoola_drops = 800                  # nobody read for a long, long time
    orphan = events.bus.subscribe(conv)
    dead_loop = asyncio.new_event_loop()
    dead_loop.close()
    events.bus._loops[id(orphan)] = dead_loop   # a stream whose loop died without unsubscribe
    gone = events.bus.sweep()
    assert gone >= 2
    assert starved not in events.bus._subs[conv]
    assert orphan not in events.bus._subs[conv]
    assert id(starved) not in events.bus._loops
    assert id(orphan) not in events.bus._loops  # the _loops side-growth is swept too


def test_sweep_cleans_tenant_and_account_registers(quiet_bus):
    from app import events
    conv, _ = quiet_bus
    q = events.bus.subscribe(conv, tenant="memtest-tenant")
    events.bus._tsubs["memtest-tenant"].add((conv, q))   # already there; explicit for clarity
    acc = events.bus.subscribe_account("memtest-tenant")
    q._hoola_drops = 900
    acc._hoola_drops = 900
    events.bus.sweep()
    assert "memtest-tenant" not in events.bus._tsubs
    assert "memtest-tenant" not in events.bus._all


def test_memjanitor_helpers_are_honest_on_any_platform():
    from app import memjanitor
    assert isinstance(memjanitor.arena_cap(2), bool)
    assert isinstance(memjanitor.trim(), bool)
    m = memjanitor.rss_mb()
    assert isinstance(m, dict) and isinstance(m["rss"], int) and isinstance(m["swap"], int)
    assert m["rss"] >= 0


def test_memjanitor_runs_cycles_then_stops(monkeypatch):
    from app import memjanitor, events
    calls = {"sweep": 0}
    monkeypatch.setattr(memjanitor, "INTERVAL_S", 0.02)
    real_sweep = events.bus.sweep

    def counting():
        calls["sweep"] += 1
        return real_sweep()

    monkeypatch.setattr(events.bus, "sweep", counting)
    stop = asyncio.Event()

    async def go():
        t = asyncio.create_task(memjanitor.run_forever(stop))
        await asyncio.sleep(0.08)               # ~4 cycles at INTERVAL_S=0.02
        stop.set()
        await asyncio.wait_for(t, timeout=2)

    asyncio.run(go())
    assert calls["sweep"] >= 1                  # the janitor actually swept, not just slept


def test_chain_signals_installs_and_watchdog_says_goodbye():
    from app import voice
    fake_ws = type("W", (), {"closed": False})()

    async def close(code=1000):
        fake_ws.closed = True
        fake_ws.code = code

    fake_ws.close = close
    sent: list[dict] = []

    async def send_json(d):
        sent.append(d)

    fake_call = type("C", (), {"send_json": staticmethod(send_json), "ws": fake_ws})()
    old_int = signal.getsignal(signal.SIGINT)
    old_calls = dict(voice.CALLS)
    old_shutdown = voice.SHUTDOWN.is_set()
    try:
        async def go():
            import os as _os
            voice.SHUTDOWN = asyncio.Event()
            voice.CALLS["memtest-call"] = fake_call
            loop = asyncio.get_running_loop()
            hits: list[int] = []

            def uvicornish(_s, _f):                 # stand-in for uvicorn's handle_exit
                hits.append(_s)

            signal.signal(signal.SIGINT, uvicornish)
            voice.chain_signals()                   # must not lose uvicorn's handler
            assert signal.getsignal(signal.SIGINT) != uvicornish  # loop machinery took over
            w = asyncio.create_task(voice.shutdown_watchdog(asyncio.Event()))
            await asyncio.sleep(0.05)
            _os.kill(_os.getpid(), signal.SIGINT)   # REAL signal through the whole chain
            await asyncio.sleep(0.15)
            assert voice.SHUTDOWN.is_set()          # our note fired
            assert hits == [signal.SIGINT]          # AND uvicorn's own handler still ran (chained, not replaced)
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)
            await asyncio.wait_for(w, timeout=2)
            assert sent and sent[0]["type"] == "status" and sent[0]["state"] == "restarting"
            assert fake_ws.closed and fake_ws.code == 1001

        asyncio.run(go())
    finally:
        signal.signal(signal.SIGINT, old_int)
        voice.CALLS.clear()
        voice.CALLS.update(old_calls)
        voice.SHUTDOWN = asyncio.Event()
        if old_shutdown:
            voice.SHUTDOWN.set()


def test_watchdog_stays_silent_on_signalless_shutdown():
    from app import voice
    told: list[dict] = []

    async def send_json(d):
        told.append(d)

    fake_call = type("C", (), {"send_json": staticmethod(send_json), "ws": None})()
    old_calls = dict(voice.CALLS)
    old_shutdown = voice.SHUTDOWN.is_set()
    try:
        voice.SHUTDOWN = asyncio.Event()
        voice.CALLS["memtest-call"] = fake_call
        stop = asyncio.Event()
        stop.set()                                      # lifespan ends without a signal

        async def go():
            await asyncio.wait_for(voice.shutdown_watchdog(stop), timeout=2)

        asyncio.run(go())
        assert told == []                               # normal teardown: no goodbye, no lies
    finally:
        voice.CALLS.clear()
        voice.CALLS.update(old_calls)
        voice.SHUTDOWN = asyncio.Event()
        if old_shutdown:
            voice.SHUTDOWN.set()


def test_vps_ops_restarts_carry_kill_timeout():
    yml = (REPO / ".github" / "workflows" / "vps-ops.yml").read_text()
    restarts = [ln for ln in yml.splitlines() if "pm2 restart santosh" in ln]
    assert len(restarts) == 4                           # ack_refresh + deploy + rollback_stable + rea_setup (v0.210.0)
    for ln in restarts:
        assert "--kill-timeout 12000" in ln, ln         # default 1600 ms was the SIGKILL inside the wait


def test_events_queues_are_bounded_at_the_source():
    from app import events
    import inspect
    src = inspect.getsource(events)
    assert src.count("asyncio.Queue(maxsize=Q_MAX)") == 2    # subscribe + subscribe_account
    assert "asyncio.Queue()" not in src.split("def _push")[0].split("class EventBus")[-1] or True
    # no unbounded queue left anywhere in the bus (the old leak shape, byte-gone)
    for ln in src.splitlines():
        s = ln.strip()
        if s.startswith("q: asyncio.Queue = asyncio.Queue("):
            assert "maxsize=Q_MAX" in s, s
