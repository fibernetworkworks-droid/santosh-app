"""Keeps this PC connected to the Santosh server (outbound WebSocket, reconnects by itself)."""
from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any, Callable

import httpx

from .actions import ActionError, Actions
from .config import Config, save


def pair(server: str, code: str, name: str, os_name: str, http: httpx.Client | None = None) -> tuple[str, str]:
    """Exchange the 6-digit code shown on the phone for this PC's own token."""
    server = server.strip().rstrip("/")
    if not server.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise ValueError("Server address must start with https://")
    c = http or httpx.Client(timeout=20)
    r = c.post(server + "/api/pc/pair", json={"code": code.strip(), "name": name, "os": os_name})
    if r.status_code >= 400:
        try:
            msg = r.json().get("detail") or r.text
        except ValueError:
            msg = r.text
        raise ValueError(str(msg)[:200])
    d = r.json()
    return d["device_id"], d["token"]


def _ws_url(server: str) -> str:
    s = server.rstrip("/")
    return ("wss://" + s[8:] if s.startswith("https://") else "ws://" + s[7:]) + "/api/pc/ws"


async def _connect(url: str, token: str):
    import websockets
    headers = {"Authorization": f"Bearer {token}"}
    try:
        from websockets.asyncio.client import connect  # websockets >= 13
        return await connect(url, additional_headers=headers, max_size=8 * 1024 * 1024, ping_interval=30, open_timeout=20)
    except ImportError:
        return await websockets.connect(url, extra_headers=headers, max_size=8 * 1024 * 1024, ping_interval=30)


class Bridge:
    def __init__(self, cfg: Config, actions: Actions, on_status: Callable[[str], None] = print,
                 on_unpaired: Callable[[], None] | None = None):
        self.cfg, self.actions = cfg, actions
        self.on_status, self.on_unpaired = on_status, on_unpaired
        self.loop: asyncio.AbstractEventLoop | None = None
        self.ws = None
        self.stopping = False
        self.connected = False
        self._thread: threading.Thread | None = None

    # ---------------- lifecycle ----------------
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="santosh-bridge", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        asyncio.run(self.run_forever())

    def stop(self) -> None:
        self.stopping = True
        if self.loop and self.ws:
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)

    def push_info(self) -> None:
        if self.loop and self.ws and self.connected:
            asyncio.run_coroutine_threadsafe(self._send(self.actions.info()), self.loop)

    async def _send(self, msg: dict[str, Any]) -> None:
        if self.ws is not None:
            await self.ws.send(json.dumps(msg, ensure_ascii=False, default=str))

    async def run_forever(self) -> None:
        self.loop = asyncio.get_running_loop()
        delay = 1.0
        while not self.stopping:
            if not self.cfg.paired:
                self.on_status("Pair nahi hai")
                await asyncio.sleep(2)
                continue
            try:
                self.on_status("Jud raha hai…")
                self.ws = await _connect(_ws_url(self.cfg.server), self.cfg.token)
                self.connected = True
                delay = 1.0
                self.on_status("Juda hua: phone se Santosh ko boliye")
                await self._session()
            except Exception as e:  # network down, server restarting, sleep/wake
                code = getattr(getattr(e, "rcvd", None), "code", None) or getattr(e, "code", None)
                if code in (4401, 4403):
                    self.on_status("Is PC ko phone se hata diya gaya. Dobara pair kijiye.")
                    self.cfg.device_id, self.cfg.token_sealed = "", ""
                    save(self.cfg)
                    if self.on_unpaired:
                        self.on_unpaired()
                    continue
                self.on_status(f"Server se connection toota, {int(delay)}s mein dobara…")
            finally:
                self.connected = False
                self.ws = None
            if self.stopping:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)

    async def _session(self) -> None:
        ws = self.ws
        info_task = asyncio.create_task(self._info_loop())
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                t = msg.get("type")
                if t == "hello":
                    await self._send(await asyncio.to_thread(self.actions.info))
                elif t == "ping":
                    await self._send({"type": "pong"})
                elif t == "job":
                    asyncio.create_task(self._job(msg))
        finally:
            info_task.cancel()
        close_code = getattr(ws, "close_code", None)
        if close_code in (4401, 4403):
            err = Exception("unpaired")
            err.code = close_code  # type: ignore[attr-defined]
            raise err

    async def _info_loop(self) -> None:
        while True:
            await asyncio.sleep(300)
            try:
                await self._send(await asyncio.to_thread(self.actions.info))
            except Exception:
                return

    async def _job(self, msg: dict[str, Any]) -> None:
        jid, action, args = msg.get("id"), str(msg.get("action") or ""), msg.get("args") or {}
        try:
            data = await asyncio.to_thread(self.actions.handle, action, args)
            reply = {"type": "result", "id": jid, "ok": True, "data": data}
        except ActionError as e:
            reply = {"type": "result", "id": jid, "ok": False, "error": str(e)}
        except Exception as e:
            reply = {"type": "result", "id": jid, "ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
        try:
            await self._send(reply)
        except Exception:
            pass


class Reindexer:
    """Keeps the local search index fresh (first run right away, then every 15 minutes)."""

    def __init__(self, actions: Actions, on_done: Callable[[int], None] | None = None, every: int = 900):
        self.actions, self.on_done, self.every = actions, on_done, every
        self._wake = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._run, name="santosh-index", daemon=True).start()

    def now(self) -> None:
        self._wake.set()

    def _run(self) -> None:
        while True:
            try:
                n = self.actions.index.rebuild(self.actions.cfg.folders)
                if self.on_done:
                    self.on_done(n)
            except Exception:
                pass
            self._wake.wait(self.every)
            self._wake.clear()
            time.sleep(0.2)
