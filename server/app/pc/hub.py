"""Live connections from paired PCs (Santosh Desktop) and the jobs sent to them.

The PC dials out to the server over a WebSocket, so it works behind any office router with no port forwarding.

Protocol (JSON text frames):
  server -> pc   {"type": "hello", "device_id", "server_time"}
  pc -> server   {"type": "info", "name", "os", "version", "folders": [...], "tally": {...}, "indexed": n}
  server -> pc   {"type": "job", "id", "action", "args"}
  pc -> server   {"type": "result", "id", "ok": true, "data": {...}}  |  {"type": "result", "id", "ok": false, "error": "..."}
  server -> pc   {"type": "ping"}            pc -> server  {"type": "pong"}
"""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("santosh.pc")

JOB_TIMEOUT = {"search": 30, "list": 20, "read": 45, "send_file": 180, "save_file": 180, "print": 30,
               "tally_report": 60, "tally_voucher": 60, "status": 15}


class PcOffline(Exception):
    pass


class PcError(Exception):
    pass


@dataclass
class Conn:
    ws: Any
    device_id: str
    tenant_id: str
    info: dict[str, Any] = field(default_factory=dict)
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def send(self, msg: dict[str, Any]) -> None:
        async with self.send_lock:
            await self.ws.send_text(json.dumps(msg, ensure_ascii=False, default=str))


def _summary(action: str, args: dict[str, Any]) -> str:
    keys = ("query", "path", "report", "party", "name", "type", "amount")
    bits = [f"{k}={args[k]}" for k in keys if args.get(k) not in (None, "")]
    return (action + (" " + ", ".join(bits) if bits else ""))[:300]


class Hub:
    def __init__(self) -> None:
        self.conns: dict[str, dict[str, Conn]] = {}           # tenant -> device_id -> conn
        self.pending: dict[str, tuple[asyncio.Future, str]] = {}   # job id -> (future, device id)
        self.loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    # ---------------- connections ----------------
    def online(self, tenant_id: str) -> list[Conn]:
        with self._lock:
            return list((self.conns.get(tenant_id) or {}).values())

    def is_online(self, tenant_id: str, device_id: str | None = None) -> bool:
        return any(device_id in (None, c.device_id) for c in self.online(tenant_id))

    def info_of(self, tenant_id: str, device_id: str) -> dict[str, Any] | None:
        for c in self.online(tenant_id):
            if c.device_id == device_id:
                return c.info
        return None

    async def serve(self, ws, device_id: str, tenant_id: str) -> None:
        """Runs for the life of one PC connection."""
        self.loop = asyncio.get_running_loop()
        conn = Conn(ws=ws, device_id=device_id, tenant_id=tenant_id)
        with self._lock:
            old = self.conns.setdefault(tenant_id, {}).get(device_id)
            self.conns[tenant_id][device_id] = conn
        if old is not None:   # the same PC reconnected: drop the stale socket
            try:
                await old.ws.close(code=4000)
            except Exception:
                pass
        from . import service
        service.touch_device(device_id)
        pinger = asyncio.create_task(self._ping(conn))
        try:
            await conn.send({"type": "hello", "device_id": device_id, "server_time": datetime.now(timezone.utc).isoformat()})
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                t = msg.get("type")
                if t == "result":
                    item = self.pending.pop(str(msg.get("id")), None)
                    if item is not None and item[1] == device_id and not item[0].done():
                        item[0].set_result(msg)
                elif t == "info":
                    conn.info = {k: msg.get(k) for k in ("name", "os", "version", "folders", "tally", "indexed", "inbox", "paused", "control")}
                    service.save_info(device_id, conn.info)
                elif t == "pong":
                    service.touch_device(device_id)
        finally:
            pinger.cancel()
            for jid, (fut, dev) in list(self.pending.items()):
                if dev == device_id and not fut.done():
                    fut.set_exception(PcOffline("PC_OFFLINE"))
            with self._lock:
                if (self.conns.get(tenant_id) or {}).get(device_id) is conn:
                    del self.conns[tenant_id][device_id]
            service.touch_device(device_id)

    async def _ping(self, conn: Conn) -> None:
        try:
            while True:
                await asyncio.sleep(25)
                await conn.send({"type": "ping"})
        except Exception:
            return

    async def kick(self, tenant_id: str, device_id: str) -> None:
        for c in self.online(tenant_id):
            if c.device_id == device_id:
                try:
                    await c.ws.close(code=4403)
                except Exception:
                    pass

    # ---------------- jobs ----------------
    async def call(self, tenant_id: str, action: str, args: dict[str, Any] | None = None,
                   device_id: str | None = None, timeout: float | None = None, log: bool = True) -> dict[str, Any]:
        args = args or {}
        conns = [c for c in self.online(tenant_id) if device_id in (None, c.device_id)]
        if not conns:
            raise PcOffline("PC_OFFLINE")
        conn = conns[-1]
        if (conn.info or {}).get("paused"):
            raise PcError("Santosh Desktop is paused on the PC. Ask the user to press Resume there.")
        from . import service
        if log:
            job_id = service.log_job(tenant_id, conn.device_id, action, _summary(action, args))
        else:   # v0.86 live-view frames: not written to the PC job log (one every second while Hoola thinks)
            import secrets as _s
            job_id = "live_" + _s.token_hex(6)
            service = _NoLog()
        fut = asyncio.get_running_loop().create_future()
        self.pending[job_id] = (fut, conn.device_id)
        try:
            await conn.send({"type": "job", "id": job_id, "action": action, "args": args})
            msg = await asyncio.wait_for(fut, timeout or JOB_TIMEOUT.get(action, 40))
        except asyncio.TimeoutError:
            service.finish_job(job_id, "timeout", "PC did not answer in time")
            raise PcError("The PC did not answer in time (it may be busy or the network is slow).")
        except (PcError, PcOffline):
            service.finish_job(job_id, "error", "PC went offline")
            raise PcOffline("PC_OFFLINE")
        except Exception as e:
            service.finish_job(job_id, "error", str(e)[:300])
            raise PcOffline("PC_OFFLINE")
        finally:
            self.pending.pop(job_id, None)
        if not msg.get("ok"):
            err = str(msg.get("error") or "failed")[:300]
            service.finish_job(job_id, "error", err)
            raise PcError(err)
        service.finish_job(job_id, "done")
        data = msg.get("data")
        return data if isinstance(data, dict) else {"data": data}

    def call_sync(self, tenant_id: str, action: str, args: dict[str, Any] | None = None,
                  device_id: str | None = None, timeout: float | None = None) -> dict[str, Any]:
        """For worker threads (Connectors run in a thread). Never call from the event loop itself."""
        loop = self.loop
        if loop is None or not self.is_online(tenant_id, device_id):
            raise PcOffline("PC_OFFLINE")
        try:
            if asyncio.get_running_loop() is loop:
                raise RuntimeError("call_sync used inside the event loop; use await hub.call")
        except RuntimeError as e:
            if "call_sync" in str(e):
                raise
        t = timeout or JOB_TIMEOUT.get(action, 40)
        fut = asyncio.run_coroutine_threadsafe(self.call(tenant_id, action, args, device_id, t), loop)
        return fut.result(t + 10)


hub = Hub()


class _NoLog:
    @staticmethod
    def finish_job(*_a, **_k) -> None:
        return None


def new_token() -> str:
    return "spc_" + secrets.token_urlsafe(32)
