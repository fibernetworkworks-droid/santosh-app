"""Run Santosh Desktop.

  SantoshDesktop.exe                       open the window (pair, folders, activity)
  SantoshDesktop.exe --background          start minimised (used at Windows sign-in)
  SantoshDesktop.exe --ask "sawaal"        send a quick-ask into the Hoola conversation (W3 text
                                           lane) - a running window receives it and sends; else
                                           the window starts, sends, and stays out of the way
  python -m santosh_desktop --headless --server https://... --code 123456 --folder D:\\Accounts
                                           no window (servers, testing)
"""
from __future__ import annotations

import argparse
import platform
import signal
import sys
import threading

from . import __version__


def headless(args) -> int:
    from .actions import Actions
    from .bridge import Bridge, Reindexer, pair
    from .config import app_dir, load, save
    from .index import Index
    cfg = load()
    if args.server:
        cfg.server = args.server.rstrip("/")
    if args.folder:
        cfg.folders = list(dict.fromkeys(cfg.folders + args.folder))
    if args.inbox:
        cfg.inbox = args.inbox
    if args.tally_port:
        cfg.tally_port = args.tally_port
    if args.code:
        dev, tok = pair(cfg.server, args.code, args.name or cfg.name, f"{platform.system()} {platform.release()}")
        cfg.device_id, cfg.token = dev, tok
    save(cfg)
    if not cfg.paired:
        print("Not paired. Run with --code 123456 (code from the Hoola app > Mera PC).")
        return 2
    idx = Index(app_dir() / "index.db")
    acts = Actions(cfg, idx, log=lambda m: print("[santosh]", m, flush=True))
    br = Bridge(cfg, acts, on_status=lambda s: print("[status]", s, flush=True))
    Reindexer(acts, on_done=lambda n: (print(f"[index] {n} files", flush=True), br.push_info())).start()
    done = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: done.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: done.set())
    br.start()
    done.wait()
    br.stop()
    return 0


def _single_instance():
    """Two copies would fight over the same connection; the second one exits quietly."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 47321))
        s.listen(4)
        return s
    except OSError:
        s.close()
        return None


def _forward_ask(text: str) -> bool:
    """A second instance has no lock: hand the ask to the RUNNING window over the lock port
    (the W3 doors - PowerToys Run 'hoola <sawaal>' - land here when the desktop already runs).
    True = handed over; False = nobody is listening (we are the first instance)."""
    import socket
    try:
        c = socket.create_connection(("127.0.0.1", 47321), timeout=2)
        c.sendall(("ASK:" + text.replace("\n", " ")).encode("utf-8"))
        c.shutdown(socket.SHUT_WR)
        c.close()
        return True
    except OSError:
        return False


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="santosh-desktop", description="Connect this PC to Hoola")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--background", action="store_true")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--server")
    p.add_argument("--code")
    p.add_argument("--name")
    p.add_argument("--folder", action="append")
    p.add_argument("--inbox")
    p.add_argument("--tally-port", type=int)
    p.add_argument("--ask")
    a = p.parse_args(argv)
    if a.headless:
        if a.ask:
            from .config import load
            from . import quickask
            out = quickask.send(load(), text=a.ask)
            print("[ask]", "bhej diya" if out.get("ok") else out.get("message", "nahi bheja"), flush=True)
            return 0 if out.get("ok") else 1
        return headless(a)
    if a.ask and _forward_ask(a.ask):
        return 0                      # the running window took it (the doors feel instant)
    lock = _single_instance()
    if lock is None:   # already running but the handover failed: nothing to do (the open window stays)
        return 1 if a.ask else 0
    from .app import App
    App(background=a.background, ask=a.ask, lock=lock).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
