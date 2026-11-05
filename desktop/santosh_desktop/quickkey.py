"""Ctrl+Alt+H - global hotkey jo Hoola Desktop window laata hai (PowerToys na hone par ka fallback door).

W2b of the Platforms plan: PowerToys Run ho to 'hoola' keyword wahi dwar hai; PowerToys NA ho
to yeh hotkey wahi dwar deta hai - USER khud daba kar desktop window laata hai. Win32
RegisterHotKey (user32, ctypes) ek chhote message-loop thread par: koi nayi dependency nahi,
current-user scope (global hotkey OS-wide hotkey hai, par sirf tab jab Hoola Desktop chal
raha ho - Quit par unregister). Hoola khud kabhi keys nahi dabaati - win+r BLOCKED_KEYS ki
tarah, yeh shortcut sirf USER ke liye ka rasta hai.
"""
from __future__ import annotations

import ctypes
import sys
import threading

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x0001, 0x0002, 0x0004, 0x0008
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
VK_H = 0x48
MODIFIERS = MOD_CONTROL | MOD_ALT          # Ctrl+Alt+H - H for Hoola
HOTKEY_ID = 0x484F                          # 'HO'

KEY_NAME = "Ctrl+Alt+H"


def supported() -> bool:
    return sys.platform == "win32"


class _MSG(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint),
                ("wParam", ctypes.c_void_p), ("lParam", ctypes.c_void_p),
                ("time", ctypes.c_uint), ("pt_x", ctypes.c_long), ("pt_y", ctypes.c_long)]


class QuickKey:
    """RegisterHotKey on a message-loop thread; WM_HOTKEY -> on_fired.

    on_fired runs on the HOTKEY thread - the window app routes it through its events queue
    (thread-safe) instead of touching Tk directly. start() polls briefly so the caller gets
    an honest registered/error answer (the hotkey may belong to another app)."""

    def __init__(self, on_fired) -> None:
        self.on_fired = on_fired
        self.registered = False
        self.error = ""
        self._thread: threading.Thread | None = None
        self._thread_id = 0

    def start(self) -> bool:
        if not supported():
            return False
        if self._thread is not None:
            return self.registered
        self._thread = threading.Thread(target=self._run, name="santosh-quickkey", daemon=True)
        self._thread.start()
        for _ in range(50):                    # the answer lands within the first ~1s
            if self.registered or self.error:
                break
            self._thread.join(0.02)
        return self.registered

    def stop(self) -> None:
        tid, self._thread = self._thread_id, None
        if tid and sys.platform == "win32":
            try:
                ctypes.windll.user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)
            except Exception:
                pass

    def _run(self) -> None:
        user32 = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, HOTKEY_ID, MODIFIERS, VK_H):
            self.error = f"{KEY_NAME} doosre app ke paas hai - wahi shortcut pehle se chal raha hai."
            return
        self.registered = True
        msg = _MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                try:
                    self.on_fired()
                except Exception:
                    pass
        user32.UnregisterHotKey(None, HOTKEY_ID)
