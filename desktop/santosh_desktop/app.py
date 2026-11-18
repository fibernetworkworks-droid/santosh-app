"""Hoola Desktop window: pair, choose shared folders, see everything Hoola did on this PC."""
from __future__ import annotations

import platform
import queue
import threading
import time
from pathlib import Path

from . import __version__, autostart, ext_install, pt_run, quickask, quickkey
from .actions import Actions
from .bridge import Bridge, Reindexer, pair
from .config import Config, app_dir, load, save
from .index import Index

INK, MUTED, BG, PANEL, ACCENT, OK, BAD = "#1B1030", "#5B5675", "#F6F4FF", "#FFFFFF", "#FF9A3C", "#0E9F6E", "#D93C3C"


class App:
    def __init__(self, background: bool = False, ask: str | None = None, lock=None):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.cfg: Config = load()
        self.events: queue.Queue = queue.Queue()
        self.index = Index(app_dir() / "index.db")
        self.actions = Actions(self.cfg, self.index, log=lambda m: self.events.put(("log", m)))
        self.bridge = Bridge(self.cfg, self.actions, on_status=lambda s: self.events.put(("status", s)),
                             on_unpaired=lambda: self.events.put(("unpaired", "")))
        self.reindex = Reindexer(self.actions, on_done=lambda n: self.events.put(("indexed", n)))
        self.actions.control.on_activity = lambda what: self.events.put(("control", what))
        self._banner = None
        self._banner_at = 0.0
        # v1.8.0 W2b: the Ctrl+Alt+H fallback door lives with the window (its events queue is the
        # thread-safe bridge from the hotkey thread to the Tk main loop); do_pt_run can start/stop it
        self.quickkey: quickkey.QuickKey | None = None
        self.actions.set_hotkey = self._set_quickkey
        # v1.9.0 W3: the lock port also RECEIVES quick-asks from the second instance (the
        # PowerToys Run 'hoola <sawaal>' door lands here when the desktop already runs)
        self._lock = lock
        if lock is not None:
            threading.Thread(target=self._accept_asks, name="santosh-askport", daemon=True).start()

        self.root = tk.Tk()
        self.root.title("Hoola Desktop")
        self.root.geometry("560x680")
        self.root.minsize(480, 560)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.root.iconify)  # keep running; Quit button exits
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=6)
        self.status = tk.StringVar(value="Starting…")
        self.indexed = tk.StringVar(value="")
        self._build()
        self.bridge.start()
        self.reindex.start()
        self.root.after(200, self._pump)
        self._start_quickkey_silently()
        if ask:
            self.events.put(("ask", ask))     # the door that started us: send once the loop breathes
        if background and self.cfg.paired:
            self.root.after(300, self.root.iconify)

    def _accept_asks(self) -> None:
        """The lock port's second job: ASK:<text> lines from second instances (the --ask doors).
        Socket reads stay on this daemon thread; the Tk main loop only ever sees queue items."""
        import socket
        while True:
            try:
                c, _ = self._lock.accept()
            except OSError:
                return
            try:
                c.settimeout(2)
                buf = b""
                while len(buf) < 8200:
                    part = c.recv(4096)
                    if not part:
                        break
                    buf += part
                c.close()
            except OSError:
                continue
            line = buf.decode("utf-8", "ignore").strip()
            if line.startswith("ASK:") and len(line) > 4:
                self.events.put(("ask", line[4:].strip()[:8000]))

    # ---------------- UI ----------------
    def _build(self) -> None:
        tk = self.tk
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=18, pady=(16, 6))
        tk.Label(head, text="Hoola Desktop", font=("Segoe UI", 18, "bold"), bg=BG, fg=INK).pack(anchor="w")
        tk.Label(head, textvariable=self.status, font=("Segoe UI", 10), bg=BG, fg=MUTED, wraplength=500, justify="left").pack(anchor="w")
        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", expand=True, padx=18, pady=6)
        self._render()

    def _clear(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()

    def _render(self) -> None:
        self._clear()
        if self.cfg.paired:
            self._main()
        else:
            self._pair_view()

    def _card(self, title: str):
        tk = self.tk
        f = tk.Frame(self.body, bg=PANEL, highlightbackground="#E4E0F5", highlightthickness=1)
        f.pack(fill="x", pady=6)
        tk.Label(f, text=title, font=("Segoe UI", 11, "bold"), bg=PANEL, fg=INK).pack(anchor="w", padx=12, pady=(10, 4))
        return f

    def _pair_view(self) -> None:
        tk, ttk = self.tk, self.ttk
        f = self._card("Connect to your phone")
        tk.Label(f, text="1. On your phone, open the Hoola app > Main > My PC > 'Connect a PC'.\n"
                         "2. Enter the 6-digit code shown there.", bg=PANEL, fg=MUTED, justify="left").pack(anchor="w", padx=12)
        code = tk.StringVar()
        name = tk.StringVar(value=self.cfg.name)
        for label, var in (("6-digit code", code), ("Name of this PC", name)):
            tk.Label(f, text=label, bg=PANEL, fg=INK).pack(anchor="w", padx=12, pady=(8, 0))
            ttk.Entry(f, textvariable=var, width=48).pack(anchor="w", padx=12)
        msg = tk.StringVar()
        tk.Label(f, textvariable=msg, bg=PANEL, fg=BAD, wraplength=480, justify="left").pack(anchor="w", padx=12, pady=4)

        def go() -> None:
            try:
                dev, tok = pair(self.cfg.server, code.get(), name.get() or "PC", f"{platform.system()} {platform.release()}")
            except Exception as e:
                msg.set(str(e))
                return
            self.cfg.device_id, self.cfg.name = dev, name.get() or "PC"
            self.cfg.token = tok
            if not self.cfg.folders:
                docs = Path.home() / "Documents"
                self.cfg.folders = [str(docs)] if docs.exists() else []
            save(self.cfg)
            if autostart.supported():
                autostart.set_enabled(True)
            self.reindex.now()
            self._render()
        ttk.Button(f, text="Connect", command=go).pack(anchor="w", padx=12, pady=(0, 12))

    def _main(self) -> None:
        tk, ttk = self.tk, self.ttk
        from tkinter import filedialog
        self._ask_card()
        f = self._card("Which folders Hoola can see")
        tk.Label(f, text="Only these folders. The rest of the PC stays hidden from Hoola. Files from your phone arrive in 'Santosh Inbox'.",
                 bg=PANEL, fg=MUTED, wraplength=490, justify="left").pack(anchor="w", padx=12)
        lb = tk.Listbox(f, height=5, activestyle="none", relief="flat", bg="#FBFAFF")
        lb.pack(fill="x", padx=12, pady=6)
        for p in self.cfg.folders:
            lb.insert("end", p)
        row = tk.Frame(f, bg=PANEL)
        row.pack(anchor="w", padx=12, pady=(0, 10))

        def add() -> None:
            d = filedialog.askdirectory(title="Folder chuniye")
            if d and d not in self.cfg.folders:
                self.cfg.folders.append(d)
                save(self.cfg)
                lb.insert("end", d)
                self.reindex.now()
                self.bridge.push_info()

        def remove() -> None:
            sel = lb.curselection()
            if sel:
                p = lb.get(sel[0])
                self.cfg.folders = [x for x in self.cfg.folders if x != p]
                save(self.cfg)
                lb.delete(sel[0])
                self.reindex.now()
                self.bridge.push_info()
        ttk.Button(row, text="Add folder", command=add).pack(side="left")
        ttk.Button(row, text="Remove", command=remove).pack(side="left", padx=6)
        tk.Label(row, textvariable=self.indexed, bg=PANEL, fg=MUTED).pack(side="left", padx=8)

        s = self._card("Settings")
        paused = tk.BooleanVar(value=self.cfg.paused)
        auto = tk.BooleanVar(value=autostart.enabled())

        def toggle_pause() -> None:
            self.cfg.paused = paused.get()
            save(self.cfg)
            self.bridge.push_info()
        ttk.Checkbutton(s, text="Pause (Hoola will do nothing on this PC)", variable=paused, command=toggle_pause).pack(anchor="w", padx=12)
        control = tk.BooleanVar(value=self.cfg.control_enabled)

        def toggle_control() -> None:
            self.cfg.control_enabled = control.get()
            save(self.cfg)
            self.bridge.push_info()
            self._log("PC control: " + ("ON (Hoola can see the screen and run apps)" if control.get() else "OFF"))
        ttk.Checkbutton(s, text="Let Hoola control the PC (screen, mouse, keyboard, apps)", variable=control,
                        command=toggle_control).pack(anchor="w", padx=12)
        tk.Label(s, text="An orange bar shows at the top while it works; press 'Stop' or move the mouse to the top-left corner of the screen.",
                 bg=PANEL, fg=MUTED, wraplength=490, justify="left", font=("Segoe UI", 8)).pack(anchor="w", padx=12)
        if autostart.supported():
            ttk.Checkbutton(s, text="Start with Windows", variable=auto,
                            command=lambda: autostart.set_enabled(auto.get())).pack(anchor="w", padx=12)
        self._ext_card()
        tally = self.actions.tally_status()
        tk.Label(s, text=("TallyPrime: connected (" + ", ".join(tally.get("companies") or [])[:80] + ")") if tally.get("available")
                 else "TallyPrime: not found. Open Tally and turn on Help > Settings > Connectivity > 'TallyPrime acts as Server' (port 9000).",
                 bg=PANEL, fg=OK if tally.get("available") else MUTED, wraplength=490, justify="left").pack(anchor="w", padx=12, pady=(6, 4))
        b = tk.Frame(s, bg=PANEL)
        b.pack(anchor="w", padx=12, pady=(4, 10))

        def unpair() -> None:
            self.cfg.device_id, self.cfg.token_sealed = "", ""
            save(self.cfg)
            self.bridge.stop()
            self.bridge = Bridge(self.cfg, self.actions, on_status=lambda st: self.events.put(("status", st)),
                                 on_unpaired=lambda: self.events.put(("unpaired", "")))
            self.bridge.start()
            self._render()
        ttk.Button(b, text="Unpair this PC", command=unpair).pack(side="left")
        ttk.Button(b, text="Quit", command=self.quit).pack(side="left", padx=6)

        a = self._card("What Hoola did on this PC")
        self.logbox = tk.Text(a, height=10, relief="flat", bg="#FBFAFF", fg=INK, state="disabled", wrap="word")
        self.logbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ---------------- v1.8.0 W2b: the Ctrl+Alt+H fallback door (PowerToys absent) ----------------
    def _start_quickkey_silently(self) -> None:
        """PowerToys na ho to Ctrl+Alt+H khud on - ek chupchaap log line, koi popup nahi."""
        if not quickkey.supported() or pt_run.power_toys_present():
            return
        out = self._set_quickkey(True)
        if out.get("registered"):
            self.events.put(("log", "Ctrl+Alt+H: bring Hoola Desktop here (PowerToys is not here, so the hotkey door is on)."))
        elif out.get("message"):
            self.events.put(("log", out["message"]))

    def _set_quickkey(self, on: bool) -> dict:
        """Runs on the Tk main loop or the bridge/worker threads via do_pt_run - QuickKey is thread-safe
        (RegisterHotKey on its own thread), so only the handle bookkeeping happens here."""
        if on:
            if self.quickkey is not None and self.quickkey.registered:
                return {"on": True, "registered": True, "message": f"{quickkey.KEY_NAME} is already running."}
            qk = quickkey.QuickKey(lambda: self.events.put(("focus", "")))
            if qk.start():
                self.quickkey = qk
                return {"on": True, "registered": True, "message": f"Press {quickkey.KEY_NAME} - Hoola Desktop will open."}
            return {"on": False, "registered": False, "message": qk.error or f"{quickkey.KEY_NAME} could not be registered."}
        if self.quickkey is not None:
            self.quickkey.stop()
            self.quickkey = None
            return {"on": False, "registered": False, "message": f"{quickkey.KEY_NAME} hotkey removed."}
        return {"on": False, "registered": False, "message": f"{quickkey.KEY_NAME} is already off."}

    # ---------------- v1.9.0 W3: the PC -> Hoola text lane (the doors' quick-ask) ----------------
    def _send_ask(self, text: str) -> None:
        """One honest send on a worker thread (the Tk loop never blocks on the network); the
        answer lives in her conversation - the log names it, the extension popup reads it back."""
        self.root.deiconify()
        self.root.lift()
        text = (text or "").strip()
        if not text:
            return
        self._log(f"Sending your question to Hoola: {text[:80]}")

        def work() -> None:
            out = quickask.send(self.cfg, text=text)
            if out.get("ok"):
                self.events.put(("log", "Sent - Hoola answers in the conversation "
                                         "(it shows on the phone / console)."))
            else:
                self.events.put(("log", "Question not sent: " + str(out.get("message", ""))))
        threading.Thread(target=work, name="santosh-ask", daemon=True).start()

    def _ask_card(self) -> None:
        """The window's own door: type here, Enter ya Bhejiye - the same lane as PowerToys Run."""
        tk, ttk = self.tk, self.ttk
        f = self._card("Ask Hoola (from this PC)")
        var = tk.StringVar()
        ent = ttk.Entry(f, textvariable=var, width=52)
        ent.pack(anchor="w", padx=12, pady=(6, 2))

        def go() -> None:
            t = var.get().strip()
            if t:
                var.set("")
                self._send_ask(t)
        ent.bind("<Return>", lambda _e: go())
        row = tk.Frame(f, bg=PANEL)
        row.pack(anchor="w", padx=12, pady=(0, 10))
        ttk.Button(row, text="Send", command=go).pack(side="left")
        tk.Label(row, text="The same question from PowerToys Run: Alt+Space, 'hoola <question>'",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=8)

    def _ext_card(self) -> None:
        """The browser extension card: the W3 'send page to Hoola' door for her browser.
        Nothing installs by itself - the install runs on her click (the pt_run discipline)."""
        tk, ttk = self.tk, self.ttk
        f = self._card("Browser extension (send a page to Hoola)")
        if ext_install.installed():
            tk.Label(f, text="Installed in Chrome/Edge: right-click a page > 'Send to Hoola', "
                             "or use the extension shortcut. Pairing is done in the extension's Options "
                             "(the phone's 6-digit code).",
                     bg=PANEL, fg=OK, wraplength=490, justify="left").pack(anchor="w", padx=12, pady=(4, 6))
            row = tk.Frame(f, bg=PANEL)
            row.pack(anchor="w", padx=12, pady=(0, 10))
            ttk.Button(row, text="Open folder", command=lambda: ext_install.open_folder()).pack(side="left")
            ttk.Button(row, text="Remove", command=lambda: (ext_install.set_enabled(False), self._render())).pack(side="left", padx=6)
        else:
            tk.Label(f, text="Send any page from Chrome/Edge to the Hoola conversation - "
                             "right-click or the extension shortcut. Hoola reads the page with its own scrape tools.",
                     bg=PANEL, fg=MUTED, wraplength=490, justify="left").pack(anchor="w", padx=12, pady=(4, 6))

            def install() -> None:
                out = ext_install.set_enabled(True)
                self._log(out.get("message", ""))
                self._render()
            ttk.Button(f, text="Install files (for Load unpacked)", command=install).pack(anchor="w", padx=12, pady=(0, 10))

    def _log(self, m: str) -> None:
        box = getattr(self, "logbox", None)
        if box is None or not box.winfo_exists():
            return
        box.configure(state="normal")
        box.insert("1.0", time.strftime("%H:%M  ") + m + "\n")
        box.delete("200.0", "end")
        box.configure(state="disabled")

    def _pump(self) -> None:
        try:
            while True:
                kind, v = self.events.get_nowait()
                if kind == "status":
                    self.status.set(v)
                elif kind == "log":
                    self._log(v)
                elif kind == "indexed":
                    self.indexed.set(f"{v:,} files")
                    self.bridge.push_info()
                elif kind == "unpaired":
                    self._render()
                elif kind == "focus":
                    # W2b hotkey door: the QuickKey thread asks, the Tk main loop obeys
                    self.root.deiconify()
                    self.root.lift()
                    self.root.focus_force()
                elif kind == "ask":
                    # W3 text lane: a door (PowerToys Run 'hoola <sawaal>', the second-instance
                    # handover, the window's own box) sends her words into the conversation
                    self._send_ask(v)
                elif kind == "control":
                    self._show_banner(v)
        except queue.Empty:
            pass
        import time as _t
        if self._banner is not None and _t.time() - self._banner_at > 10:
            self._banner.destroy()
            self._banner = None
        self.root.after(250, self._pump)

    def _show_banner(self, what: str) -> None:
        """Always-on-top strip while Hoola uses the PC, with a stop button."""
        import time as _t
        tk = self.tk
        self._banner_at = _t.time()
        if self._banner is None:
            b = tk.Toplevel(self.root)
            b.overrideredirect(True)
            b.attributes("-topmost", True)
            try:
                b.attributes("-alpha", 0.92)
            except tk.TclError:
                pass
            b.configure(bg=ACCENT)
            sw = self.root.winfo_screenwidth()
            b.geometry(f"520x40+{max(0, sw // 2 - 260)}+6")
            self._banner_lbl = tk.Label(b, text="", bg=ACCENT, fg=INK, font=("Segoe UI", 10, "bold"))
            self._banner_lbl.pack(side="left", padx=10)

            def stop() -> None:
                self.cfg.paused = True
                save(self.cfg)
                self.bridge.push_info()
                self._log("You stopped Hoola (to resume, untick 'Pause' in Settings).")
                b.destroy()
                self._banner = None
                self._render()
            tk.Button(b, text="Stop", command=stop, bg=INK, fg="white", relief="flat").pack(side="right", padx=8, pady=6)
            self._banner = b
        self._banner_lbl.configure(text=f"🤖 Hoola is controlling this PC · {what[:40]}")

    def quit(self) -> None:
        if self.quickkey is not None:
            self.quickkey.stop()
            self.quickkey = None
        self.bridge.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
