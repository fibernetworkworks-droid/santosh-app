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

from . import __version__, browser, extract
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

    def do_screen(self, max_width: int = 1280, monitor: str = "primary", **_) -> dict[str, Any]:
        self._control_on()
        return self.control.screen(int(max_width or 1280), monitor=str(monitor or "primary"))

    def do_control(self, op: str = "", x: Any = None, y: Any = None, text: str = "", keys: str = "", amount: int = 0,
                   to_x: Any = None, to_y: Any = None, **_) -> dict[str, Any]:
        self._control_on()
        self.log(f"PC control: {op} {keys or ''}".strip())
        out = self.control.act(op, x, y, text, keys, amount, to_x, to_y)
        # v1.4 after typing, check the field itself (UIA): the server warns the model when the text did not land,
        # so a dead submit never happens. Only lengths + a true/false travel back — never the value.
        if op == "type" and text:
            v = browser.verify_typed(text)
            if v:
                out["verify"] = v
        return out

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

    def do_window(self, op: str = "", title: str = "", **_) -> dict[str, Any]:
        """v1.3 Minimise / maximise / restore / close an open window by (part of) its title."""
        self._control_on()
        self.log(f"Window: {op} {title[:60]}")
        return self.control.window_op(op, title)

    def do_open_url(self, url: str = "", **_) -> dict[str, Any]:
        """v1.4 Open a site as a new tab in the browser she already uses, and wait for the page to load."""
        self._control_on()
        self.log(f"Site khol raha hoon: {url[:80]}")
        return self.control.open_url(url)

    # ---------------- v1.4 browser intelligence (Chrome / Edge / Firefox, read-only) ----------------
    def do_page_text(self, max_chars: int = 6000, **_) -> dict[str, Any]:
        """The exact words of the page open in her browser (UIA): labels, prices, buttons, lists."""
        self._control_on()
        try:
            out = browser.page_text(max(500, min(int(max_chars or 6000), 20000)))
        except browser.BrowserUnavailable as e:
            raise ActionError(str(e))
        self.log(f"Page text padha: {out.get('title', '')[:60]}")
        return out

    # ---------------- v1.5.0 SEMANTIC BROWSER (UIA): act on elements by ref, not by pixel guesses --------
    def do_page_elements(self, max_items: int = 60, **_) -> dict[str, Any]:
        """The page's buttons / links / fields as a numbered list - refs feed page_click / page_type / etc."""
        self._control_on()
        try:
            out = browser.page_elements(max(1, min(int(max_items or 60), 200)))
        except browser.BrowserUnavailable as e:
            raise ActionError(str(e))
        self.log(f"Page elements: {out.get('count', 0)} (semantic mode)")
        return out

    def do_page_click(self, ref: int, **_) -> dict[str, Any]:
        """Click a page element BY REF (Invoke/Toggle/Expand patterns, else the control's own centre)."""
        self._control_on()
        try:
            out = browser.page_click(ref)
        except browser.BrowserUnavailable as e:
            raise ActionError(str(e))
        self.log(f"Element #{ref} par click (semantic)")
        return out

    def do_page_type(self, ref: int, text: str = "", clear: bool = True, **_) -> dict[str, Any]:
        """Type into a page field BY REF; only length + matches come back (the value never leaves the PC)."""
        self._control_on()
        try:
            out = browser.page_type(ref, str(text or "")[:4000], clear=bool(clear))
        except browser.BrowserUnavailable as e:
            raise ActionError(str(e))
        self.log(f"Element #{ref} mein likha (semantic, {out.get('length', 0)} akshar)")
        return out

    def do_page_select(self, ref: int, value: str = "", **_) -> dict[str, Any]:
        """Pick an option BY REF in a dropdown / combobox."""
        self._control_on()
        try:
            out = browser.page_select(ref, str(value or ""))
        except browser.BrowserUnavailable as e:
            raise ActionError(str(e))
        self.log(f"Dropdown #{ref}: chuna (semantic)")
        return out

    def do_page_fill_form(self, entries: list | dict | None = None, **_) -> dict[str, Any]:
        """Many fields in ONE step: entries = [{'ref': 2, 'text': '...'}, ...]."""
        self._control_on()
        items = entries.get("entries") if isinstance(entries, dict) else entries
        try:
            out = browser.page_fill_form(list(items or []))
        except browser.BrowserUnavailable as e:
            raise ActionError(str(e))
        self.log(f"Form bhara (semantic): {out.get('filled', 0)}/{out.get('total', 0)}")
        return out

    def do_wait_for(self, text: str = "", seconds: int = 15, **_) -> dict[str, Any]:
        """Wait until a text really appears in her browser (polls the UIA tree, max 20s)."""
        self._control_on()
        try:
            out = browser.wait_for(str(text or ""), min(int(seconds or 15), 20))
        except browser.BrowserUnavailable as e:
            raise ActionError(str(e))
        return out

    def do_tabs(self, **_) -> dict[str, Any]:
        """The open tabs of the browser in front (title + which is active)."""
        self._control_on()
        try:
            out = browser.tabs()
        except browser.BrowserUnavailable as e:
            raise ActionError(str(e))
        self.log(f"Tabs dekhe ({out.get('count', 0)})")
        return out

    def do_switch_tab(self, tab: str = "", index: int = 0, **_) -> dict[str, Any]:
        """Move to a tab by (part of) its title or its number from tabs()."""
        self._control_on()
        try:
            out = browser.switch_tab(tab, int(index or 0))
        except browser.BrowserUnavailable as e:
            raise ActionError(str(e))
        self.log(f"Tab par gaya: {(tab or index)!s:.60}")
        return out

    def do_downloads(self, minutes: int = 15, **_) -> dict[str, Any]:
        """Recent files in her Downloads folder (.crdownload = still downloading)."""
        self._control_on()
        out = browser.downloads(minutes=int(minutes or 15))
        self.log(f"Downloads dekhe ({out.get('count', 0)})")
        return out

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

    OPEN_EXT = {".xlsx", ".xlsm", ".xls", ".csv", ".docx", ".doc", ".pdf", ".txt", ".pptx", ".odt", ".ods", ".jpg",
                ".jpeg", ".png", ".md"}

    def do_open_file(self, path: str = "", **_) -> dict[str, Any]:
        """v1.2 Opens a document (shared folders / Santosh Inbox only) in its own app, e.g. the updated copy in Excel.
        Programs, scripts and shortcuts are never opened."""
        p = self._file(path)
        if p.suffix.lower() not in self.OPEN_EXT:
            raise ActionError(f"{p.name}: sirf documents khule jaate hain (Excel, Word, PDF, CSV, photo)")
        if sys.platform == "win32":
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        self.log(f"Khola: {p.name}")
        return {"opened": str(p), "name": p.name}

    def do_recent(self, limit: int = 30, days: int = 3, **_) -> dict[str, Any]:
        """v1.2 Newest files in the shared folders + Inbox (two levels deep), e.g. what she just downloaded."""
        cutoff = time.time() - max(1, min(int(days or 3), 60)) * 86400
        found = []
        rs = roots(self.cfg.folders) + ([Path(self.cfg.inbox)] if self.cfg.inbox and Path(self.cfg.inbox).is_dir() else [])
        seen = 0
        for r in rs:
            for depth_dir in [r] + [c for c in r.iterdir() if c.is_dir() and not c.name.startswith(".")][:200]:
                try:
                    for c in depth_dir.iterdir():
                        seen += 1
                        if seen > 20000:
                            break
                        if c.is_file() and not c.name.startswith((".", "~$")) and not c.name.endswith((".part", ".crdownload", ".tmp")):
                            st = c.stat()
                            if st.st_mtime >= cutoff:
                                found.append((st.st_mtime, c, st.st_size))
                except OSError:
                    continue
        found.sort(key=lambda x: -x[0])
        out = [{"name": c.name, "path": str(c), "size": size, "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(m))}
               for m, c, size in found[:max(1, min(int(limit or 30), 100))]]
        self.log(f"Nayi files dekhi ({len(out)})")
        return {"files": out, "count": len(out)}

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
