"""v0.484.0 HOOLA LAUNCHER - Win+R se 'hoola', the W2a MVP of the Platforms plan (owner:
'W2 - LAUNCHER --- START A WORK'; W1 smart home v0.479.0 already live).

What shipped (each test pins one promise):
(1) desktop/santosh_desktop/app_paths.py - Windows ka apna App Paths alias: HKCU App Paths\\hoola.exe
    ka default value SantoshDesktop.exe point karta hai -> Win+R 'hoola' (aur Start menu search) Hoola
    Desktop kholta hai. USER-LEVEL: no admin, kisi doosre user ko chhoot nahi, Run-key nahi, kuch
    auto-start nahi hota - sirf ek alias; on=false undo. autostart.py ka twin (lazy winreg).
(2) Desktop 1.7.0 do_app_paths action - the SAME _control_on() gate as every control action
    ("Hoola ko PC chalane dein"), jaise v0.471 ke ax_* actions (source-pin, v0472 style).
(3) Server pc operator: app_paths tool (ONE-TIME SETUP, ask_approval PEHLE - settings change),
    _do() branch, _say() line, _desktop_says() upgrade line for old desktops.
(4) SAFETY: 'win+r' STAYS in BLOCKED_KEYS - Hoola khud kabhi Run dialog nahi kholta; wo alias DETA
    hai taaki USER khud Win+R daba sake. The alias is the safe substitute, not a new door.

Desktop version pin moved 1.6.0 -> 1.7.0 in test_v0185 (the conscious-bump guard).
"""
import asyncio
import errno
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

import santosh_desktop.app_paths as ap  # noqa: E402

DESKTOP = Path(__file__).resolve().parents[2] / "desktop" / "santosh_desktop"


# ---------------------------------------------------------------- fake winreg (dict-backed)
def _fake_winreg(monkeypatch) -> dict:
    m = types.ModuleType("winreg")
    m.HKEY_CURRENT_USER = object()
    m.REG_SZ = 1
    store: dict[str, dict] = {}

    class Handle:
        def __init__(self, path: str):
            self.path = path
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def _norm(path) -> str:
        return str(path).replace("/", "\\").strip("\\").lower()

    def OpenKey(root, path, reserved=0, access=0):
        k = _norm(path)
        if k not in store:
            raise OSError(errno.ENOENT, "no such key")
        return Handle(k)

    def CreateKey(root, path):
        k = _norm(path)
        store.setdefault(k, {})
        return Handle(k)

    def QueryValueEx(handle, name):
        vals = store[handle.path]
        if (name or "") not in vals:
            raise OSError(errno.ENOENT, "no such value")
        return vals[name or ""], m.REG_SZ

    def SetValueEx(handle, name, reserved, typ, value):
        store[handle.path][name or ""] = value

    def DeleteKey(root, path):
        k = _norm(path)
        if k not in store:
            raise OSError(errno.ENOENT, "no such key")
        del store[k]

    m.OpenKey, m.CreateKey, m.QueryValueEx, m.SetValueEx, m.DeleteKey = (
        OpenKey, CreateKey, QueryValueEx, SetValueEx, DeleteKey)
    m._store = store
    monkeypatch.setitem(sys.modules, "winreg", m)
    return store


def _win_frozen(monkeypatch, exe=r"C:\Apps\Hoola\SantoshDesktop.exe") -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", exe)


# ---------------------------------------------------------------- the module's own promises
def test_alias_round_trip_add_find_remove(monkeypatch):
    store = _fake_winreg(monkeypatch)
    _win_frozen(monkeypatch)
    out = ap.set_enabled(True)
    assert out["ok"] and out["on"] is True and out["command"] == "hoola"
    assert "SantoshDesktop.exe" in out["exe"]
    assert ap.enabled() is True
    # the real registry shape: default value = the exe (quoted), Path = its folder
    key = r"software\microsoft\windows\currentversion\app paths\hoola.exe"
    assert store[key][""] == f'"{out["exe"]}"'
    assert store[key]["Path"] == r"C:\Apps\Hoola"
    # remove, then remove again - the second one must still be ok (idempotent undo)
    out2 = ap.set_enabled(False)
    assert out2["ok"] and out2["on"] is False and "hata diya" in out2["message"]
    assert key not in store and ap.enabled() is False
    out3 = ap.set_enabled(False)
    assert out3["ok"] and "pehle se nahi" in out3["message"]


def test_non_windows_refuses(monkeypatch):
    _fake_winreg(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    out = ap.set_enabled(True)
    assert out["ok"] is False and out["supported"] is False
    assert "Windows" in out["message"]


def test_dev_mode_refuses(monkeypatch):
    _fake_winreg(monkeypatch)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    out = ap.set_enabled(True)
    assert out["ok"] is False and out["supported"] is False
    assert "installed" in out["message"]


def test_supported_needs_frozen_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert ap.supported() is False
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert ap.supported() is False
    _win_frozen(monkeypatch)
    assert ap.supported() is True


def test_enabled_silent_on_non_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert ap.enabled() is False


# ---------------------------------------------------------------- the desktop action (source pins, v0472 style)
def test_do_app_paths_is_control_gated():
    src = (DESKTOP / "actions.py").read_text()
    body = src.split("def do_app_paths(", 1)[1].split("\n    def ", 1)[0]
    assert "self._control_on()" in body, "do_app_paths must sit behind the PC-control switch"
    assert "app_paths.set_enabled" in body and "self.log(" in body


def test_desktop_version_bumped():
    import santosh_desktop
    assert santosh_desktop.__version__ == "1.9.0"


# ---------------------------------------------------------------- the server side (FakePC, v0185 style)
class FakePC:
    def __init__(self):
        self.calls = []
        self.reply = {"ok": True, "on": True, "command": "hoola",
                      "exe": r"C:\Apps\Hoola\SantoshDesktop.exe",
                      "message": "Ab Win+R dabakar 'hoola' likhne se Hoola Desktop khul jaayega."}
        self.err = None

    async def __call__(self, op, action, args=None, timeout=40, log=True):
        self.calls.append((action, dict(args or {})))
        if self.err:
            raise self.err
        return dict(self.reply)


@pytest.fixture
def opc(monkeypatch):
    from app.pc import operator
    pc = FakePC()
    monkeypatch.setattr(operator, "_pc", pc)
    return operator, pc


def _op(operator):
    return operator.Op(id="s1", tenant="t1", conv="c1", task="Win+R se hoola khulwao")


def test_operator_tool_spec_has_approval_wording(opc):
    operator, _ = opc
    spec = [t for t in operator.TOOLS if t["name"] == "app_paths"]
    assert spec, "app_paths tool must exist in the operator toolset"
    d = spec[0]["description"]
    assert "ask_approval" in d and "on=false" in d and "no admin" in d


def test_operator_do_adds_alias(opc):
    operator, pc = opc
    out = asyncio.run(operator._do(_op(operator), "app_paths", {"on": True}))
    assert pc.calls == [("app_paths", {"on": True})]
    assert "Win+R alias ready" in out and "SantoshDesktop.exe" in out


def test_operator_do_removes_alias(opc):
    operator, pc = opc
    pc.reply = {"ok": True, "on": False, "message": "Win+R wala 'hoola' alias hata diya."}
    out = asyncio.run(operator._do(_op(operator), "app_paths", {"on": False}))
    assert pc.calls == [("app_paths", {"on": False})]
    assert "Done:" in out and "hata diya" in out


def test_operator_do_unsupported(opc):
    operator, pc = opc
    pc.reply = {"ok": False, "on": False, "supported": False, "message": "Yeh alias sirf Windows PC par banta hai."}
    out = asyncio.run(operator._do(_op(operator), "app_paths", {"on": True}))
    assert "alias nahi laga" in out and "Windows" in out


def test_operator_do_old_desktop_gets_upgrade_line(opc):
    operator, pc = opc
    pc.err = RuntimeError("Unknown action app_paths")
    out = asyncio.run(operator._do(_op(operator), "app_paths", {"on": True}))
    assert "naya SantoshDesktop.exe" in out        # the _OLD_DESKTOP upgrade line, nothing broke


def test_say_lines(opc):
    operator, _ = opc
    assert "alias jod" in operator._say("app_paths", {"on": True})
    assert "hata" in operator._say("app_paths", {"on": False})


def test_desktop_says_covers_app_paths(opc):
    operator, _ = opc
    e = RuntimeError("Unknown action app_paths")
    assert operator._desktop_says(e, "app_paths") is not None
    assert operator._desktop_says(RuntimeError("x"), "open_app") is None


# ---------------------------------------------------------------- safety: the alias, not the dialog
def test_win_r_keys_still_blocked(opc):
    """Hoola never OPENS the Run dialog itself - the alias exists so SHE can press Win+R."""
    operator, _ = opc
    out = asyncio.run(operator._do(_op(operator), "key", {"keys": "win+r"}))
    assert out.startswith("REFUSED")


def test_versions(opc):
    operator, _ = opc
    from app.main import APP_VERSION
    assert APP_VERSION == "0.557.0"
    pubspec = (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
    assert "version: 0.557.0+580" in pubspec
