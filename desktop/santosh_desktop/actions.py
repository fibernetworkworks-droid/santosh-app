"""What Hoola can ask this PC to do. Every action is checked against the shared folders and logged on screen."""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from . import __version__, extract
from .config import Config
from .index import Index
from .safety import Denied, allowed, roots, unique
from .control import Control, ControlError
from .tally import Tally, TallyError

MAX_SEND = 50 * 1024 * 1024


class ActionError(Exception):
    pass


class Actions:
    def __init__(self, cfg: Config, index: Index, log: Callable[[str], None] = print,
                 http: httpx.Client | None = None, tally: Tally | None = None):
        self.cfg, self.index, self.log = cfg, index, log
        self.http = http or httpx.Client(timeout=httpx.Timeout(300, connect=20))
        self.tally = tally or Tally(cfg.tally_host, cfg.tally_port)
        self._tally_cache: tuple[float, dict[str, Any]] = (0.0, {})
        self.control = Control()

    # ---------------- info ----------------
    def tally_status(self) -> dict[str, Any]:
        t, v = self._tally_cache
        if time.time() - t < 120:
            return v
        st = self.tally.status()
        self._tally_cache = (time.time(), st)
        return st

    def info(self) -> dict[str, Any]:
        return {"type": "info", "name": self.cfg.name, "os": f"{platform.system()} {platform.release()}",
                "version": __version__, "folders": [{"path": str(r), "label": r.name or str(r)} for r in roots(self.cfg.folders)],
                "tally": self.tally_status(), "indexed": self.index.count(), "inbox": self.cfg.inbox, "paused": self.cfg.paused,
                "control": bool(self.cfg.control_enabled)}

    # ---------------- dispatcher ----------------
    def handle(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        if self.cfg.paused:
            raise ActionError("Hoola Desktop is paused on this PC.")
        fn = getattr(self, "do_" + action, None)
        if fn is None:
            raise ActionError(f"Unknown action {action}")
        try:
            return fn(**(args or {}))
        except Denied as e:
            raise ActionError(str(e))
        except ControlError as e:
            raise ActionError(str(e))
        except TallyError as e:
            raise ActionError(str(e))
        except TypeError as e:
            raise ActionError(f"Bad request: {e}")

    def _file(self, path: str) -> Path:
        p = allowed(path, self.cfg.folders, self.cfg.inbox)
        if not p.is_file():
            raise ActionError("File nahi mili (shayad hata di ya naam badal gaya). Dobara search kariye.")
        return p

    # ---------------- actions ----------------
    # ---------------- using the PC (screen, mouse, keyboard, apps) ----------------
    def _control_on(self) -> None:
        if not self.cfg.control_enabled:
            raise ActionError("PC chalane ki permission band hai. PC par Hoola Desktop > Settings > "
                              "'Hoola ko PC chalane dein' on kijiye.")

    def do_screen(self, max_width: int = 1280, **_) -> dict[str, Any]:
        self._control_on()
        return self.control.screen(int(max_width or 1280))

    def do_control(self, op: str = "", x: Any = None, y: Any = None, text: str = "", keys: str = "", amount: int = 0,
                   to_x: Any = None, to_y: Any = None, **_) -> dict[str, Any]:
        self._control_on()
        self.log(f"PC control: {op} {keys or ''}".strip())
        return self.control.act(op, x, y, text, keys, amount, to_x, to_y)

    def do_apps(self, **_) -> dict[str, Any]:
        self._control_on()
        return self.control.apps()

    def do_open_app(self, name: str = "", **_) -> dict[str, Any]:
        self._control_on()
        self.log(f"App khol raha hoon: {name}")
        return self.control.open_app(name)

    def do_focus(self, title: str = "", **_) -> dict[str, Any]:
        self._control_on()
        return self.control.focus(title)

    def do_status(self, **_) -> dict[str, Any]:
        i = self.info()
        i.pop("type", None)
        return i

    def do_search(self, query: str = "", kind: str = "any", limit: int = 20, **_) -> dict[str, Any]:
        res = self.index.search(query, kind or "any", int(limit or 20), self.cfg.folders)
        self.log(f"Search: {query} ({len(res)} mili)")
        return {"query": query, "results": res, "count": len(res), "indexed": self.index.count()}

    def do_list(self, path: str = "", **_) -> dict[str, Any]:
        if not path:
            return {"folders": [{"path": str(r), "name": r.name or str(r)} for r in roots(self.cfg.folders)]}
        p = allowed(path, self.cfg.folders, self.cfg.inbox)
        if not p.is_dir():
            raise ActionError("Yeh folder nahi hai")
        entries = []
        for c in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower()))[:300]:
            if c.name.startswith("."):
                continue
            try:
                st = c.stat()
            except OSError:
                continue
            entries.append({"name": c.name, "path": str(c), "dir": c.is_dir(), "size": st.st_size if c.is_file() else None,
                            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))})
        self.log(f"Folder dekha: {p.name}")
        return {"path": str(p), "entries": entries}

    def do_read(self, path: str = "", max_chars: int = 12000, **_) -> dict[str, Any]:
        p = self._file(path)
        text = extract.text_of(p, max(500, min(int(max_chars or 12000), 40000)))
        self.log(f"Padha: {p.name}")
        if not text:
            return {"path": str(p), "name": p.name, "text": "", "note": "No readable text (scanned image or unsupported type). "
                                                                        "Send it to the phone instead."}
        return {"path": str(p), "name": p.name, "category": extract.category(p.name, text), "text": text}

    def do_send_file(self, path: str = "", **_) -> dict[str, Any]:
        p = self._file(path)
        size = p.stat().st_size
        if size > MAX_SEND:
            raise ActionError(f"{p.name} is {size // (1024 * 1024)} MB; the limit is 50 MB.")
        with p.open("rb") as fh:
            r = self.http.post(self.cfg.server.rstrip("/") + "/api/pc/files", headers={"Authorization": f"Bearer {self.cfg.token}"},
                               files={"file": (p.name, fh, "application/octet-stream")}, data={"path": str(p)})
        if r.status_code >= 400:
            raise ActionError(f"Upload failed ({r.status_code}): {r.text[:160]}")
        self.log(f"Phone par bheja: {p.name}")
        return r.json()

    def do_save_file(self, file_id: str = "", name: str = "", url: str = "", **_) -> dict[str, Any]:
        inbox = Path(self.cfg.inbox)
        dest = unique(inbox, name or file_id)
        tmp = dest.with_name(dest.name + ".part")
        with self.http.stream("GET", self.cfg.server.rstrip("/") + (url or f"/api/pc/fetch/{file_id}"),
                              headers={"Authorization": f"Bearer {self.cfg.token}"}) as r:
            if r.status_code >= 400:
                raise ActionError(f"Download failed ({r.status_code})")
            n = 0
            with tmp.open("wb") as out:
                for chunk in r.iter_bytes():
                    n += len(chunk)
                    if n > MAX_SEND:
                        raise ActionError("File too big")
                    out.write(chunk)
        tmp.replace(dest)
        self.log(f"Phone se aayi file: {dest.name} (Santosh Inbox)")
        return {"saved_path": str(dest), "name": dest.name, "message": f"{dest.name} PC ke 'Santosh Inbox' folder mein save ho gayi."}

    def do_print(self, path: str = "", copies: int = 1, **_) -> dict[str, Any]:
        p = self._file(path)
        copies = max(1, min(int(copies or 1), 20))
        for _ in range(copies):
            if sys.platform == "win32":
                os.startfile(str(p), "print")  # type: ignore[attr-defined]
            else:
                subprocess.run(["lp", str(p)], check=True, capture_output=True, timeout=60)
        self.log(f"Print bheja: {p.name} × {copies}")
        return {"printed": p.name, "copies": copies, "message": f"{p.name} print ho raha hai ({copies})."}

    def do_tally_report(self, report: str = "", from_date: str = "", to_date: str = "", party: str = "",
                        company: str = "", **_) -> dict[str, Any]:
        out = self.tally.report(report, from_date, to_date, party, company)
        self.log(f"Tally: {report}" + (f" ({party})" if party else ""))
        return out

    def do_tally_voucher(self, voucher_type: str = "", party: str = "", amount: float = 0, ledger: str = "", date: str = "",
                         narration: str = "", company: str = "", **_) -> dict[str, Any]:
        out = self.tally.create_voucher(voucher_type, party, float(amount), ledger, date, narration, company)
        self.log(f"Tally entry (approved on phone): {voucher_type} {party} {out['amount_text']}")
        return out
