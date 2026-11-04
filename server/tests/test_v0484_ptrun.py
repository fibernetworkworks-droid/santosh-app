"""v0.484.0 HOOLA POWERTOYS RUN - the 'hoola' door inside PowerToys Run, W2b of the Platforms
plan (owner: 'W2b - PowerToys Run plugin'; W2a Win+R alias v0.481.0 live).

What shipped (each test pins one promise):
(1) desktop/ptrun_plugin/Community.PowerToys.Run.Plugin.Hoola - the .NET 9 class library:
    Main : IPlugin (static PluginID 162E72D3C1D7464E865293A276993A7B = plugin.json ID, never
    changes), ActionKeyword 'hoola', Launch() through the SAME W2a App Paths alias (one launch
    truth) with an honest ShowMsg when the alias is off, dark/light theme icons. plugin.json in
    Microsoft's documented shape (ID/ActionKeyword/IsGlobal/Name/Author/Version/Language/
    Website/ExecuteFileName/IcoPathDark/IcoPathLight/DynamicLoading).
(2) build-desktop.yml: dotnet publish -p:Platform=x64 against Community.PowerToys.Run.Plugin.
    Dependencies 0.97.0, payload staged to ptrun_payload/ and ridden INSIDE SantoshDesktop.exe
    (spec datas) + shipped as Hoola-PowerToysRun-plugin.zip on the desktop release.
(3) desktop/santosh_desktop/pt_run.py - the installer twin of app_paths.py: copies ONLY Hoola's
    own folder into %LOCALAPPDATA%\\Microsoft\\PowerToys\\PowerToys Run\\Plugins\\Hoola
    (user-level, no admin), whole-folder replace = upgrade, calm idempotent undo, honest errors
    (no payload -> 'naya exe chahiye'), power_toys_present() across per-user/machine/plugins-root.
(4) desktop/santosh_desktop/quickkey.py - PowerToys absent ka fallback door: Ctrl+Alt+H via
    user32 RegisterHotKey on its own message-loop thread (Hoola never presses keys - the USER
    does; win+r BLOCKED_KEYS discipline), events-queue -> Tk main loop, Quit unregisters.
(5) Desktop 1.8.0 do_pt_run - the SAME _control_on() gate; PowerToys absent -> wires the hotkey
    door through actions.set_hotkey (the control.on_activity injection pattern); on=false undoes
    both doors.
(6) Server pc operator: pt_run tool (ONE-TIME SETUP, ask_approval PEHLE), _do() branch (plugin
    ready / hotkey door / honest failures), _say() line, _desktop_says() upgrade line.

Desktop version pin moved 1.7.0 -> 1.8.0 in test_v0185 (the conscious-bump guard).
"""
import asyncio
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

import santosh_desktop.pt_run as pr  # noqa: E402
import santosh_desktop.quickkey as qk  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "desktop" / "ptrun_plugin" / "Community.PowerToys.Run.Plugin.Hoola"
DESKTOP = ROOT / "desktop" / "santosh_desktop"

ID = "162E72D3C1D7464E865293A276993A7B"


# ================================================================ (1) the plugin source itself
def test_plugin_json_microsoft_shape():
    meta = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8-sig"))
    assert meta["ID"] == ID and len(ID) == 32 and all(c in "0123456789ABCDEF" for c in ID)
    assert meta["ActionKeyword"] == "hoola"
    assert meta["IsGlobal"] is False
    assert meta["Name"] == "Hoola"
    assert meta["Language"] == "csharp"                       # the only supported language
    assert meta["Website"].startswith("https://")
    assert meta["ExecuteFileName"] == "Community.PowerToys.Run.Plugin.Hoola.dll"
    assert meta["DynamicLoading"] is False                    # only Wox.Plugin + BCL, no extra dlls
    for k in ("IcoPathDark", "IcoPathLight"):
        # plugin.json carries Windows separators (PowerToys parses it on Windows); the repo files
        # behind them must exist whatever OS the tests run on
        assert (PLUGIN / meta[k].replace("\\", "/")).is_file(), f"{k} -> {meta[k]} must exist"


def test_plugin_json_id_matches_main_cs():
    main = (PLUGIN / "Main.cs").read_text(encoding="utf-8")
    assert f'PluginID => "{ID}"' in main
    assert 'Name => "Hoola"' in main


def test_main_cs_launches_through_the_w2a_alias():
    main = (PLUGIN / "Main.cs").read_text(encoding="utf-8")
    # one launch truth: the HKCU App Paths alias W2a writes, read back here
    assert r"App Paths\hoola.exe" in main
    assert "Registry.CurrentUser.OpenSubKey" in main
    assert "Process.Start" in main and "UseShellExecute = true" in main
    # no alias -> an honest message, never a path guess
    assert "ShowMsg" in main and "alias" in main
    # the standard IPlugin shape
    assert "IPlugin" in main and "List<Result> Query(Query query)" in main
    assert "Init(PluginInitContext context)" in main
    assert "ThemeChanged += OnThemeChanged" in main and "ThemeChanged -= OnThemeChanged" in main


def test_csproj_pinned_to_the_community_reference_stack():
    csproj = (PLUGIN / "Community.PowerToys.Run.Plugin.Hoola.csproj").read_text(encoding="utf-8")
    assert "net9.0-windows10.0.26100.0" in csproj          # loads on .NET 9 and .NET 10 hosts
    assert "Community.PowerToys.Run.Plugin.Dependencies" in csproj and 'Version="0.97.0"' in csproj
    assert "<UseWPF>true</UseWPF>" in csproj
    assert "plugin.json" in csproj and "CopyToOutputDirectory" in csproj
    assert "<Platforms>x64</Platforms>" in csproj          # CI passes -p:Platform=x64


def test_plugin_version_tracks_the_desktop_version():
    meta = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8-sig"))
    import santosh_desktop
    assert meta["Version"] == santosh_desktop.__version__


# ================================================================ (2) the CI pipeline
def test_build_desktop_builds_and_bundles_the_plugin():
    wf = (ROOT / ".github" / "workflows" / "build-desktop.yml").read_text(encoding="utf-8")
    assert "dotnet-version: \"9.0.x\"" in wf
    assert "dotnet publish desktop/ptrun_plugin/Community.PowerToys.Run.Plugin.Hoola" in wf
    assert "-p:Platform=x64" in wf
    assert "ptrun_payload" in wf and "Community.PowerToys.Run.Plugin.Hoola.dll" in wf
    assert "Hoola-PowerToysRun-plugin.zip" in wf           # also shipped standalone


def test_spec_rides_the_payload_inside_the_exe():
    spec = (ROOT / "desktop" / "santosh_desktop.spec").read_text(encoding="utf-8")
    assert "ptrun_payload" in spec and '"ptrun"' in spec
    assert 'if os.path.isdir' in spec                      # dev machines without the payload still build


# ================================================================ (3) pt_run.py - the installer
@pytest.fixture
def pt_env(monkeypatch, tmp_path):
    """A fake Windows machine: LOCALAPPDATA + win32 + frozen, payload in a tmp source dir."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    la = tmp_path / "locallow"
    (la / "PowerToys").mkdir(parents=True)                 # per-user PowerToys.exe lives here
    (la / "PowerToys" / "PowerToys.exe").write_bytes(b"MZ")
    monkeypatch.setenv("LOCALAPPDATA", str(la))
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "pf"))
    src = tmp_path / "payload" / "ptrun"
    (src / "Images").mkdir(parents=True)
    (src / "plugin.json").write_text('{"ExecuteFileName": "Community.PowerToys.Run.Plugin.Hoola.dll"}',
                                     encoding="utf-8")
    (src / "Community.PowerToys.Run.Plugin.Hoola.dll").write_bytes(b"MZ plugin")
    (src / "Images" / "hoola.dark.png").write_bytes(b"png")
    return la, src


def test_install_copies_only_hoolas_own_folder(pt_env):
    la, src = pt_env
    out = pr.set_enabled(True, source_dir=str(src))
    assert out["ok"] and out["plugin"] is True and out["pt_present"] is True
    dest = la / "Microsoft" / "PowerToys" / "PowerToys Run" / "Plugins" / "Hoola"
    assert (dest / "plugin.json").is_file() and (dest / "Community.PowerToys.Run.Plugin.Hoola.dll").is_file()
    assert (dest / "Images" / "hoola.dark.png").is_file()
    assert pr.installed() is True
    assert "restart kijiye" in out["message"]              # PowerToys must reload to see it
    # the plugins root neighbours stay untouched (no other folder created)
    assert [p.name for p in (dest.parent).iterdir()] == ["Hoola"]


def test_install_twice_is_an_upgrade(pt_env):
    la, src = pt_env
    pr.set_enabled(True, source_dir=str(src))
    (src / "Community.PowerToys.Run.Plugin.Hoola.dll").write_bytes(b"MZ plugin v2")
    out = pr.set_enabled(True, source_dir=str(src))
    assert out["ok"] and out["plugin"] is True
    dll = la / "Microsoft" / "PowerToys" / "PowerToys Run" / "Plugins" / "Hoola" / "Community.PowerToys.Run.Plugin.Hoola.dll"
    assert dll.read_bytes() == b"MZ plugin v2"             # whole-folder replace, no stale copy


def test_uninstall_and_uninstall_again_is_calm(pt_env):
    la, src = pt_env
    pr.set_enabled(True, source_dir=str(src))
    out = pr.set_enabled(False)
    assert out["ok"] and out["plugin"] is False and "hata diya" in out["message"]
    assert pr.installed() is False
    out2 = pr.set_enabled(False)
    assert out2["ok"] and "pehle se nahi" in out2["message"]


def test_pt_absent_points_to_the_hotkey_door(pt_env, monkeypatch):
    la, src = pt_env
    (la / "PowerToys" / "PowerToys.exe").unlink()          # no PowerToys anywhere
    out = pr.set_enabled(True, source_dir=str(src))
    assert out["ok"] is True and out["plugin"] is False and out["pt_present"] is False
    assert "Ctrl+Alt+H" in out["message"]
    assert pr.installed() is False                         # nothing installed without PowerToys


def test_power_toys_present_three_ways(pt_env, monkeypatch):
    la, _ = pt_env
    assert pr.power_toys_present() is True                 # per-user exe
    (la / "PowerToys" / "PowerToys.exe").unlink()
    assert pr.power_toys_present() is False
    (la / "Microsoft" / "PowerToys" / "PowerToys Run" / "Plugins").mkdir(parents=True)
    assert pr.power_toys_present() is True                 # the Run plugins root (PT ran once)
    pf = la.parent / "pf"
    pf.mkdir()
    (pf / "PowerToys").mkdir()
    (pf / "PowerToys" / "PowerToys.exe").write_bytes(b"MZ")
    monkeypatch.setenv("ProgramFiles", str(pf))
    assert pr.power_toys_present() is True                 # machine-wide install


def test_missing_payload_is_honest(pt_env, monkeypatch):
    la, src = pt_env
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(pr, "_payload", lambda source_dir=None: None)
    out = pr.set_enabled(True)
    assert out["ok"] is False and out["plugin"] is False
    assert "naya exe" in out["message"]


def test_bad_payload_json_is_honest(pt_env):
    la, src = pt_env
    (src / "plugin.json").write_text("not json", encoding="utf-8")
    out = pr.set_enabled(True, source_dir=str(src))
    assert out["ok"] is False and "plugin.json" in out["message"]


def test_payload_without_dll_is_honest(pt_env):
    la, src = pt_env
    (src / "Community.PowerToys.Run.Plugin.Hoola.dll").unlink()
    out = pr.set_enabled(True, source_dir=str(src))
    assert out["ok"] is False and "DLL" in out["message"]


def test_non_windows_refuses(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    out = pr.set_enabled(True)
    assert out["ok"] is False and out["supported"] is False
    assert "Windows" in out["message"]
    assert pr.power_toys_present() is False
    assert qk.supported() is False


# ================================================================ (4) quickkey.py - the fallback door
def test_quickkey_non_windows_never_starts_thread(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    fired = []
    ok = qk.QuickKey(lambda: fired.append(1)).start()
    assert ok is False and fired == []


def test_quickkey_source_pins_win32_shape():
    src = (DESKTOP / "quickkey.py").read_text(encoding="utf-8")
    assert "RegisterHotKey" in src and "UnregisterHotKey" in src
    assert "0x0312" in src and "WM_HOTKEY" in src          # the hotkey message
    assert "MOD_CONTROL | MOD_ALT" in src and "0x48" in src  # Ctrl+Alt+H
    assert "PostThreadMessageW" in src and "WM_QUIT" in src  # clean shutdown on Quit
    assert "GetMessageW" in src                            # the message loop
    assert "KEY_NAME = \"Ctrl+Alt+H\"" in src


def test_app_wires_the_hotkey_through_the_events_queue():
    app = (DESKTOP / "app.py").read_text(encoding="utf-8")
    assert "self.actions.set_hotkey = self._set_quickkey" in app
    assert 'lambda: self.events.put(("focus", ""))' in app  # hotkey thread -> queue (thread-safe)
    assert "deiconify" in app and "focus_force" in app      # the Tk main loop obeys
    assert "pt_run.power_toys_present()" in app             # only when PowerToys is absent
    assert "self.quickkey.stop()" in app                    # Quit unregisters


def test_do_pt_run_is_control_gated_with_both_doors():
    src = (DESKTOP / "actions.py").read_text(encoding="utf-8")
    body = src.split("def do_pt_run(", 1)[1].split("\n    def ", 1)[0]
    assert "self._control_on()" in body, "do_pt_run must sit behind the PC-control switch"
    assert "pt_run.set_enabled" in body
    assert "self.set_hotkey(True)" in body and "self.set_hotkey(False)" in body
    assert "self.log(" in body


def test_actions_init_carries_the_hotkey_hook():
    src = (DESKTOP / "actions.py").read_text(encoding="utf-8")
    init = src.split("class Actions:", 1)[1].split("def __init__", 1)[1].split("def ", 1)[0]
    assert "self.set_hotkey: Callable[[bool], dict] | None = None" in init
    assert "control.on_activity pattern" in src            # the injection precedent it follows


# ================================================================ (5) the server side (FakePC, v0481 style)
class FakePC:
    def __init__(self):
        self.calls = []
        self.reply = {"ok": True, "plugin": True, "pt_present": True, "supported": True,
                      "dir": r"C:\Users\me\AppData\Local\Microsoft\PowerToys\PowerToys Run\Plugins\Hoola",
                      "keyword": "hoola",
                      "message": "PowerToys Run mein 'hoola' lag gaya - Alt+Space dabakar 'hoola' likhiye "
                                 "(PowerToys ko ek baar restart kijiye taaki wo naya plugin dekhe)."}
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
    return operator.Op(id="s1", tenant="t1", conv="c1", task="Hoola ko PowerToys Run se khulwao")


def test_operator_tool_spec_has_approval_wording(opc):
    operator, _ = opc
    spec = [t for t in operator.TOOLS if t["name"] == "pt_run"]
    assert spec, "pt_run tool must exist in the operator toolset"
    d = spec[0]["description"]
    assert "ask_approval" in d and "on=false" in d and "no admin" in d and "Ctrl+Alt+H" in d


def test_operator_do_installs_plugin(opc):
    operator, pc = opc
    out = asyncio.run(operator._do(_op(operator), "pt_run", {"on": True}))
    assert pc.calls == [("pt_run", {"on": True})]
    assert "PowerToys Run plugin ready" in out and "Alt+Space" in out and "restart kijiye" in out


def test_operator_do_falls_back_to_hotkey_when_pt_absent(opc):
    operator, pc = opc
    pc.reply = {"ok": True, "plugin": False, "pt_present": False, "supported": True,
                "message": "PowerToys is PC par nahi hai - Hoola wahi kaam Ctrl+Alt+H hotkey se karti hai.",
                "hotkey": {"on": True, "registered": True,
                           "message": "Ctrl+Alt+H dabaiye - Hoola Desktop khul jaayega."}}
    out = asyncio.run(operator._do(_op(operator), "pt_run", {"on": True}))
    assert pc.calls == [("pt_run", {"on": True})]
    assert "hotkey door on kar diya" in out and "Ctrl+Alt+H" in out


def test_operator_do_honest_when_hotkey_too_fails(opc):
    operator, pc = opc
    pc.reply = {"ok": True, "plugin": False, "pt_present": False, "supported": True,
                "message": "PowerToys is PC par nahi hai - Hoola wahi kaam Ctrl+Alt+H hotkey se karti hai.",
                "hotkey": {"on": False, "registered": False, "message": "Ctrl+Alt+H doosre app ke paas hai."}}
    out = asyncio.run(operator._do(_op(operator), "pt_run", {"on": True}))
    assert "hotkey bhi nahi bana" in out and "doosre app ke paas hai" in out


def test_operator_do_unsupported(opc):
    operator, pc = opc
    pc.reply = {"ok": False, "plugin": False, "pt_present": False, "supported": False,
                "message": "PowerToys Run plugin sirf Windows PC par lagta hai."}
    out = asyncio.run(operator._do(_op(operator), "pt_run", {"on": True}))
    assert "plugin nahi laga" in out and "Windows" in out


def test_operator_do_missing_payload(opc):
    operator, pc = opc
    pc.reply = {"ok": False, "plugin": False, "supported": True,
                "message": "Plugin ki files is SantoshDesktop build mein nahi mili - naya exe install kijiye."}
    out = asyncio.run(operator._do(_op(operator), "pt_run", {"on": True}))
    assert "plugin nahi laga" in out and "naya exe" in out


def test_operator_do_removes_plugin(opc):
    operator, pc = opc
    pc.reply = {"ok": True, "plugin": False, "pt_present": True, "supported": True,
                "message": "PowerToys Run wala 'hoola' plugin hata diya."}
    out = asyncio.run(operator._do(_op(operator), "pt_run", {"on": False}))
    assert pc.calls == [("pt_run", {"on": False})]
    assert "Done:" in out and "hata diya" in out


def test_operator_do_old_desktop_gets_upgrade_line(opc):
    operator, pc = opc
    pc.err = RuntimeError("Unknown action pt_run")
    out = asyncio.run(operator._do(_op(operator), "pt_run", {"on": True}))
    assert "naya SantoshDesktop.exe" in out        # the _OLD_DESKTOP upgrade line, nothing broke


def test_say_lines(opc):
    operator, _ = opc
    assert "plugin jod" in operator._say("pt_run", {"on": True})
    assert "hata" in operator._say("pt_run", {"on": False})


def test_desktop_says_covers_pt_run(opc):
    operator, _ = opc
    e = RuntimeError("Unknown action pt_run")
    assert operator._desktop_says(e, "pt_run") is not None
    assert operator._desktop_says(RuntimeError("x"), "open_app") is None


# ================================================================ safety: the same frozen lanes
def test_win_r_keys_still_blocked(opc):
    """Hoola never OPENS launchers or presses keys herself - she gives the USER doors."""
    operator, _ = opc
    out = asyncio.run(operator._do(_op(operator), "key", {"keys": "win+r"}))
    assert out.startswith("REFUSED")


# ================================================================ version layer
def test_versions(opc):
    operator, _ = opc
    from app.main import APP_VERSION
    assert APP_VERSION == "0.520.0"
    pubspec = (ROOT / "pubspec.yaml").read_text(encoding="utf-8")
    assert "version: 0.520.0+549" in pubspec
    import santosh_desktop
    assert santosh_desktop.__version__ == "1.9.0"          # desktop changed this release (do_pt_run)
    meta = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8-sig"))
    assert meta["Version"] == "1.9.0"                      # plugin version rides the desktop
