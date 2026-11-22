"""v0.999.63 DEB INSTALL (owner: "ADDING .DEB IS NESESARY"; frozen-PC exception): Hoola PC installs a program it
downloaded as a Linux .deb. The PC checks the file (her folder only, a real Debian package, this PC's architecture,
1 GB at most), SHE approves on her phone (a .deb runs its own setup as root), apt installs it with its dependencies,
and a kept copy puts it back after the image is rebuilt."""
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0193_hoola_pc import KIND, FakePC, Scripted, _wire, tu

ROOT = Path(__file__).resolve().parents[2]
needs_dpkg = pytest.mark.skipif(shutil.which("dpkg-deb") is None, reason="needs dpkg-deb")


def _agent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOOLA_DATA", str(tmp_path / "data"))
    spec = importlib.util.spec_from_file_location("hoola_agent_deb", ROOT / "desktop-linux" / "agent.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _deb(where: Path, name="hello-hoola", arch="all") -> Path:
    src = where / f"build-{name}-{arch}"
    (src / "DEBIAN").mkdir(parents=True)
    (src / "usr" / "share" / name).mkdir(parents=True)
    (src / "usr" / "share" / name / "README").write_text("hi")
    (src / "DEBIAN" / "control").write_text(
        f"Package: {name}\nVersion: 1.2.3\nArchitecture: {arch}\nMaintainer: t <t@example.com>\nDescription: test\n")
    out = where / f"{name}_{arch}.deb"
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(src), str(out)], check=True, capture_output=True)
    shutil.rmtree(src)
    return out


@needs_dpkg
def test_a_real_deb_in_downloads_passes_the_check(tmp_path, monkeypatch):
    a = _agent(tmp_path, monkeypatch)
    a.DOWNLOADS.mkdir(parents=True, exist_ok=True)
    f = _deb(a.DOWNLOADS)
    d = a.check_deb(f.name)                                   # a bare name = in Downloads
    assert d["package"] == "hello-hoola" and d["version"] == "1.2.3" and d["arch"] == "all"
    assert a.Actions().do_install(file=f.name, check_only=True)["package"] == "hello-hoola"


@needs_dpkg
def test_everything_else_is_refused_with_the_reason(tmp_path, monkeypatch):
    a = _agent(tmp_path, monkeypatch)
    a.DOWNLOADS.mkdir(parents=True, exist_ok=True)
    outside = _deb(tmp_path, "outside")
    with pytest.raises(a.ActionError, match="Downloads or work"):
        a.check_deb(str(outside))
    (a.DOWNLOADS / "setup.exe").write_bytes(b"MZ\x90\x00")
    with pytest.raises(a.ActionError, match="Only a .deb"):
        a.check_deb("setup.exe")
    (a.DOWNLOADS / "fake.deb").write_text("<html>Download page</html>")
    with pytest.raises(a.ActionError, match="not a real Debian package"):
        a.check_deb("fake.deb")
    with pytest.raises(a.ActionError, match="No such file"):
        a.check_deb("missing.deb")
    arm = _deb(a.DOWNLOADS, "armonly", "arm64")
    monkeypatch.setattr(a.subprocess, "run", _arch_says("amd64", a.subprocess.run))
    with pytest.raises(a.ActionError, match="built for arm64"):
        a.check_deb(arm.name)
    link = a.DOWNLOADS / "link.deb"
    link.symlink_to(outside)
    with pytest.raises(a.ActionError, match="Downloads or work"):
        a.check_deb("link.deb")                               # a link out of her folder is followed and refused


def _arch_says(arch, real):
    def run(cmd, *k, **kw):
        if cmd[:2] == ["dpkg", "--print-architecture"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=arch + "\n", stderr="")
        return real(cmd, *k, **kw)
    return run


@needs_dpkg
def test_install_keeps_a_copy_logs_it_and_replays_it(tmp_path, monkeypatch):
    a = _agent(tmp_path, monkeypatch)
    a.DOWNLOADS.mkdir(parents=True, exist_ok=True)
    f = _deb(a.DOWNLOADS)
    real, seen = subprocess.run, []

    def run(cmd, *k, **kw):
        if cmd and cmd[0] == "apt-get":
            seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="Setting up hello-hoola (1.2.3)", stderr="")
        return real(cmd, *k, **kw)
    monkeypatch.setattr(a.subprocess, "run", run)
    r = a.Actions().do_install(file=f.name)
    assert r["installed"] == ["hello-hoola"] and r["version"] == "1.2.3"
    kept = list(a.DEB_KEEP.glob("hello-hoola_*.deb"))
    assert len(kept) == 1 and seen[-1] == ["apt-get", "install", "-y", str(kept[0])]   # a path, never a shell line
    log = (a.DATA / "installed.log").read_text()
    assert f" deb hello-hoola {kept[0]} rc=0" in log
    assert a.replay_installs(dry=True) == ["deb:hello-hoola"]
    assert a.VERSION in ("1.8.0", "1.9.0", "1.9.1", "1.9.2")


@pytest.mark.asyncio
async def test_the_operator_checks_then_asks_her_then_installs(bz, monkeypatch):  # noqa: F811
    from app.pc import operator
    from app.pc.hub import hub
    pc = FakePC(expect_kind=KIND)
    real_call = pc.call

    async def call(tenant, action, args=None, **kw):
        if action == "install" and (args or {}).get("file"):
            pc.calls.append((action, dict(args), kw.get("kind")))
            if args.get("check_only"):
                return {"package": "zoom", "version": "6.1", "path": "/data/Downloads/zoom_amd64.deb", "arch": "amd64"}
            return {"installed": ["zoom"], "version": "6.1", "file": "zoom_amd64.deb"}
        return await real_call(tenant, action, args, **kw)

    class Conn:
        info = {"control": True, "kind": KIND}
    monkeypatch.setattr(hub, "call", call)
    monkeypatch.setattr(hub, "is_online", lambda t, d=None, kind=None: True if (kind is None or kind == KIND) else False)
    monkeypatch.setattr(hub, "online", lambda t: [Conn()])
    asked = []

    async def approval(op, what):
        asked.append(what)
        return len(asked) == 1                                   # yes the first time, no the second
    monkeypatch.setattr(operator, "_approval", approval)
    cl = Scripted([tu(1, "install", file="zoom_amd64.deb"), tu(2, "install", file="zoom_amd64.deb"),
                   tu(3, "done", answer="Zoom installed")])
    _wire(monkeypatch, cl)
    try:
        r = await operator.start("t1", "c1", "install zoom on your own computer", wait=30, kind=KIND)
    finally:
        operator.OPS.clear()
    assert r["status"] == "done"
    files = [c[1] for c in pc.calls if c[0] == "install"]
    assert files == [{"file": "zoom_amd64.deb", "check_only": True}, {"file": "zoom_amd64.deb"},
                     {"file": "zoom_amd64.deb", "check_only": True}]          # the refused one is never installed
    assert "zoom 6.1" in asked[0] and "full access" in asked[0]
    tool = next(t for t in cl.seen[0]["tools"] if t["name"] == "install")
    assert "file" in tool["input_schema"]["properties"] and ".exe" in tool["description"]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.148"
    assert "version: 0.999.148+1143" in (ROOT / "pubspec.yaml").read_text()
