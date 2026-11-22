"""v0.999.121 ULTIMATE PC PLAN P9 - Hoola Desktop for Mac and Linux: the same app built for both, apps found and opened
there, and the AI told which kind of computer it is working on."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "desktop"))


def test_linux_apps_are_listed_and_opened_by_their_name(tmp_path, monkeypatch):
    from santosh_desktop import control as C
    apps = tmp_path / ".local/share/applications"
    apps.mkdir(parents=True)
    (apps / "org.gnome.TextEditor.desktop").write_text("[Desktop Entry]\nName=Text Editor\nExec=gnome-text-editor %U\n")
    (apps / "hidden.desktop").write_text("[Desktop Entry]\nName=Secret Tool\nNoDisplay=true\nExec=secret\n")
    (apps / "term.desktop").write_text("[Desktop Entry]\nName=XTerm\nExec=xterm\n")
    monkeypatch.setattr(C.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(C.sys, "platform", "linux")
    found = C.Control._other_apps()
    assert "Text Editor" in found and "Secret Tool" not in found
    started = []
    monkeypatch.setattr(C.subprocess, "Popen", lambda cmd, *a, **k: started.append(cmd))
    import shutil
    monkeypatch.setattr(shutil, "which", lambda n: None)
    monkeypatch.setattr(C.time, "sleep", lambda s: None)
    ctl = C.Control.__new__(C.Control)
    monkeypatch.setattr(ctl, "_touch", lambda *a: None, raising=False)
    monkeypatch.setattr(C.Control, "_start_menu", staticmethod(lambda: []))
    assert ctl.open_app("text editor") == {"opened": "Text Editor"} and started == [["gnome-text-editor"]]
    try:
        ctl.open_app("xterm")
        raise AssertionError("a terminal must never open")
    except C.ControlError as e:
        assert "command-line" in str(e)


def test_the_ai_is_told_a_mac_or_linux_pc():
    from app.pc import hub as H
    from app.pc import operator as O
    op = O.Op(id="m1", tenant="t9", conv="c", task="x")
    op.device_id = "dev9"
    real = H.hub.info_of
    try:
        for osname, want in (("Darwin 24.1.0", "IS A MAC"), ("Linux 6.8.0", "RUNS LINUX"), ("Windows 11", "")):
            H.hub.info_of = lambda t, d, _o=osname: {"os": _o}
            note = O.os_note(op)
            assert (want in note) if want else note == ""
    finally:
        H.hub.info_of = real


def test_mac_and_linux_builds_in_ci():
    wf = yaml.safe_load((ROOT / ".github/workflows/build-desktop.yml").read_text())
    job = wf["jobs"]["mac-linux"]
    plats = {m["plat"]: m for m in job["strategy"]["matrix"]["include"]}
    assert set(plats) == {"mac", "linux"} and "apple-darwin" in plats["mac"]["ad"] and "linux-gnu" in plats["linux"]["ad"]
    text = (ROOT / ".github/workflows/build-desktop.yml").read_text()
    assert "shasum -a 256 -c" in text and "desktop-${{ matrix.plat }}-latest" in text and "codesign --force --deep -s -" in text
    spec = (ROOT / "desktop/santosh_desktop.spec").read_text()
    assert 'BUNDLE(' in spec and "NSScreenCaptureUsageDescription" in spec and '_sys.platform == "darwin"' in spec
    assert "gh release create desktop-latest" in text        # the Windows release is untouched
