"""Santosh Desktop window: pair, choose shared folders, see everything Santosh did on this PC."""
from __future__ import annotations

import platform
import queue
import time
from pathlib import Path

from . import __version__, autostart
from .actions import Actions
from .bridge import Bridge, Reindexer, pair
from .config import Config, app_dir, load, save
from .index import Index

INK, MUTED, BG, PANEL, ACCENT, OK, BAD = "#1B1030", "#5B5675", "#F6F4FF", "#FFFFFF", "#FF9A3C", "#0E9F6E", "#D93C3C"


class App:
    def __init__(self, background: bool = False):
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

        self.root = tk.Tk()
        self.root.title("Santosh Desktop")
        self.root.geometry("560x640")
        self.root.minsize(480, 520)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.root.iconify)  # keep running; Quit button exits
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=6)
        self.status = tk.StringVar(value="Shuru ho raha hai…")
        self.indexed = tk.StringVar(value="")
        self._build()
        self.bridge.start()
        self.reindex.start()
        self.root.after(200, self._pump)
        if background and self.cfg.paired:
            self.root.after(300, self.root.iconify)

    # ---------------- UI ----------------
    def _build(self) -> None:
        tk = self.tk
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=18, pady=(16, 6))
        tk.Label(head, text="Santosh Desktop", font=("Segoe UI", 18, "bold"), bg=BG, fg=INK).pack(anchor="w")
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
        f = self._card("Phone se jodiye")
        tk.Label(f, text="1. Phone par Santosh app kholiye > Main > Mera PC > 'PC jodiye'.\n"
                         "2. Wahan dikha 6 ank ka code yahan daaliye.", bg=PANEL, fg=MUTED, justify="left").pack(anchor="w", padx=12)
        server = tk.StringVar(value=self.cfg.server or "https://")
        code = tk.StringVar()
        name = tk.StringVar(value=self.cfg.name)
        for label, var in (("Santosh server ka pata", server), ("6 ank ka code", code), ("Is PC ka naam", name)):
            tk.Label(f, text=label, bg=PANEL, fg=INK).pack(anchor="w", padx=12, pady=(8, 0))
            ttk.Entry(f, textvariable=var, width=48).pack(anchor="w", padx=12)
        msg = tk.StringVar()
        tk.Label(f, textvariable=msg, bg=PANEL, fg=BAD, wraplength=480, justify="left").pack(anchor="w", padx=12, pady=4)

        def go() -> None:
            try:
                dev, tok = pair(server.get(), code.get(), name.get() or "PC", f"{platform.system()} {platform.release()}")
            except Exception as e:
                msg.set(str(e))
                return
            self.cfg.server, self.cfg.device_id, self.cfg.name = server.get().strip().rstrip("/"), dev, name.get() or "PC"
            self.cfg.token = tok
            if not self.cfg.folders:
                docs = Path.home() / "Documents"
                self.cfg.folders = [str(docs)] if docs.exists() else []
            save(self.cfg)
            if autostart.supported():
                autostart.set_enabled(True)
            self.reindex.now()
            self._render()
        ttk.Button(f, text="Jodiye", command=go).pack(anchor="w", padx=12, pady=(0, 12))

    def _main(self) -> None:
        tk, ttk = self.tk, self.ttk
        from tkinter import filedialog
        f = self._card("Santosh kaun se folder dekh sakta hai")
        tk.Label(f, text="Sirf yahi folder. Baaki PC Santosh ko nahi dikhta. Phone se aayi files 'Santosh Inbox' mein aati hain.",
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
        ttk.Button(row, text="Folder jodiye", command=add).pack(side="left")
        ttk.Button(row, text="Hataiye", command=remove).pack(side="left", padx=6)
        tk.Label(row, textvariable=self.indexed, bg=PANEL, fg=MUTED).pack(side="left", padx=8)

        s = self._card("Settings")
        paused = tk.BooleanVar(value=self.cfg.paused)
        auto = tk.BooleanVar(value=autostart.enabled())

        def toggle_pause() -> None:
            self.cfg.paused = paused.get()
            save(self.cfg)
            self.bridge.push_info()
        ttk.Checkbutton(s, text="Rokiye (Santosh is PC par kuch nahi karega)", variable=paused, command=toggle_pause).pack(anchor="w", padx=12)
        if autostart.supported():
            ttk.Checkbutton(s, text="Windows ke saath shuru karein", variable=auto,
                            command=lambda: autostart.set_enabled(auto.get())).pack(anchor="w", padx=12)
        tally = self.actions.tally_status()
        tk.Label(s, text=("TallyPrime: juda hua (" + ", ".join(tally.get("companies") or [])[:80] + ")") if tally.get("available")
                 else "TallyPrime: nahi mila. Tally kholiye aur Help > Settings > Connectivity > 'TallyPrime acts as Server' on kijiye (port 9000).",
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
        ttk.Button(b, text="Is PC ko alag karein", command=unpair).pack(side="left")
        ttk.Button(b, text="Band karein (Quit)", command=self.quit).pack(side="left", padx=6)

        a = self._card("Santosh ne is PC par kya kiya")
        self.logbox = tk.Text(a, height=10, relief="flat", bg="#FBFAFF", fg=INK, state="disabled", wrap="word")
        self.logbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))

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
        except queue.Empty:
            pass
        self.root.after(250, self._pump)

    def quit(self) -> None:
        self.bridge.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
