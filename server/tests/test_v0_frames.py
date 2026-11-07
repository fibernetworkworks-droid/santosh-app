"""HOOLA FRAMES (v0.471): the avatar composes and renders a real MP4 from chat.

A fake `hyperframes` CLI stands in for the real engine; it records the contract the
worker must honour: check gates render (errors block, warnings surface), one render at
a time on the whole box, hard timeout kills the whole process group, per-tenant project
isolation with an LRU + disk janitor, owner-checked assets only, and the voice wiring
(never declared to Gemini Live - santosh_kaam runs it, the call hears progress).
"""
import asyncio
import json
import os
import stat
import sys
import time

import pytest

from app.agent import frames_tools as ft
from app.agent.tools import HANDLERS, TOOLS, TOOL_LABELS, ToolError, dispatch
from app.studio import frames
from tests.test_life import conv_ctx

FAKE_HF = r'''#!/usr/bin/env bash
# FAKE hyperframes: contract stand-in for tests (never downloads anything)
cmd="${1:-}"
case "$cmd" in
  --version) echo "0.9.6";;
  check)
    if grep -q FORCE_CHECK_FAIL index.html 2>/dev/null; then
      echo '{"ok":false,"strict":false,"lint":{"errors":[{"rule":"determinism_fetch","message":"mid-render fetch at index.html:12"}]},"runtime":{"errors":[]}}'
    else
      echo '{"ok":true,"lint":{"errors":[]},"runtime":{"errors":[]}}'
    fi;;
  render)
    if grep -q FORCE_RENDER_SLOW index.html 2>/dev/null; then sleep 30; fi
    if grep -q FORCE_RENDER_FAIL index.html 2>/dev/null; then echo "encoder boom" >&2; exit 3; fi
    printf 'FAKE-MP4-BYTES-0001' > out.mp4
    echo "render complete";;
  timeline) echo "main: #title 0.5-4.5 | #price 1.0-4.0";;
  snapshot)
    mkdir -p .hyperframes/artifacts/snapshots
    printf 'PNGDATA' > .hyperframes/artifacts/snapshots/at-1.00s.png
    printf 'PNGDATA' > .hyperframes/artifacts/snapshots/at-2.00s.png
    echo '{"ok":true}';;
  add)
    name="${2:-block}"
    case "$name" in *[!a-z0-9-]*) echo "bad name" >&2; exit 4;; esac
    mkdir -p compositions
    printf '<div id="root" data-composition-id="%s" data-duration="1"></div>' "$name" > "compositions/$name.html"
    echo "added $name";;
  *) echo "unknown $cmd" >&2; exit 9;;
esac
'''

GOOD_HTML = """<!doctype html><html><head><meta charset="UTF-8"/></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="3"
     data-width="1920" data-height="1080" data-fps="30">
  <h1 id="title" class="clip" data-start="0.5" data-duration="2">Namaste</h1>
  <script>
    const tl = gsap.timeline({ paused: true });
    tl.from("#title", { opacity: 0, duration: 0.5 }, 0.5);
    window.__timelines = window.__timelines || {};
    window.__timelines.main = tl;
  </script>
</div></body></html>"""


@pytest.fixture
def hf(env, tmp_path, monkeypatch):
    d = tmp_path / "hf"
    d.mkdir()
    exe = d / "hyperframes"
    exe.write_text(FAKE_HF)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("FRAMES_BIN", str(exe))
    monkeypatch.setenv("FRAMES_ROOT", str(tmp_path / "frames_root"))
    monkeypatch.setenv("FRAMES_TIMEOUT_S", "30")
    monkeypatch.setenv("FRAMES_QUEUE_WAIT_S", "1")
    monkeypatch.setenv("FRAMES_KEEP_H", "6")
    monkeypatch.setenv("FRAMES_DISK_CAP_GB", "10")
    monkeypatch.setenv("PC_FILES_DIR", str(tmp_path / "pc_files"))
    from app.config import get_settings
    get_settings.cache_clear()
    return d


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


# ---------------------------------------------------------------- registry + version
def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.654.0"


def test_registry_one_tool_seven_actions():
    assert len(ft.FRAMES_TOOLS) == 1
    spec = ft.FRAMES_TOOLS[0]
    assert spec["name"] == "hoola_frames"
    assert set(spec["input_schema"]["properties"]["action"]["enum"]) == \
        {"render", "check", "timeline", "snapshot", "add", "status", "avatar_film"}
    names = [t["name"] for t in TOOLS]
    assert names.count("hoola_frames") == 1, "registered exactly once in the global registry"
    assert "hoola_frames" in HANDLERS and "hoola_frames" in TOOL_LABELS
    assert callable(ft.FRAMES_HANDLERS["hoola_frames"])


def test_status_unconfigured(env, monkeypatch):
    monkeypatch.delenv("FRAMES_BIN", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    st = frames.status()
    assert st["enabled"] is False and st["bin"] == "" and st["pin"] == "hyperframes@0.9.6"
    assert set(st["actions"]) == {"render", "check", "timeline", "snapshot", "add", "status", "avatar_film"}
    assert "FRAMES_BIN" in st["note"]
    ctx = conv_ctx()
    out = run("hoola_frames", {"action": "status"}, ctx)   # handler answers honestly, no raise
    assert out["enabled"] is False


# ---------------------------------------------------------------- guards (before any spawn)
def test_bad_action_refused_before_spawn(hf, monkeypatch):
    calls = []
    monkeypatch.setattr(frames, "_run", lambda *a, **k: calls.append(a) or (0, ""))
    with pytest.raises(frames.FramesError) as ei:
        frames.run("t1", "explode")
    assert "render" in str(ei.value) and "status" in str(ei.value)
    assert calls == [], "a bad action must never reach the CLI"


def test_render_requires_html(hf):
    ctx = conv_ctx()
    with pytest.raises(ToolError) as ei:
        run("hoola_frames", {"action": "render"}, ctx)
    assert "html" in str(ei.value).lower() or "composition" in str(ei.value).lower()


def test_add_requires_block(hf):
    ctx = conv_ctx()
    with pytest.raises(ToolError):
        run("hoola_frames", {"action": "add"}, ctx)


def test_spec_paths_sanitised(hf):
    for bad in ("../evil.png", "/etc/passwd", "assets/../../x", "outside.html", ""):
        with pytest.raises(frames.FramesError):
            frames.write_project("t1", GOOD_HTML, [{"name": bad, "text": "x"}])
    p = frames.write_project("t1", GOOD_HTML, [
        {"name": "assets/copy.txt", "text": "sasti sari"},
        {"name": "compositions/scene.html", "text": "<div/>"},
    ])
    assert (p / "assets" / "copy.txt").is_file() and (p / "compositions" / "scene.html").is_file()


def test_asset_size_cap(hf, monkeypatch):
    monkeypatch.setenv("FRAMES_MAX_MB", "0")
    from app.config import get_settings
    get_settings.cache_clear()
    big = hf.parent / "big.bin"
    big.write_bytes(b"x" * 64)
    with pytest.raises(frames.FramesError) as ei:
        frames.write_project("t1", GOOD_HTML, [{"name": "assets/big.bin", "path": str(big)}])
    assert "MB" in str(ei.value)


def test_missing_asset_source_refused(hf):
    with pytest.raises(frames.FramesError):
        frames.write_project("t1", GOOD_HTML, [{"name": "assets/gone.png", "path": "/nonexistent/gone.png"}])


# ---------------------------------------------------------------- the one-at-a-time lock + kill
def test_worker_lock_second_render_refused(hf, monkeypatch):
    ok = frames._render_lock.acquire(timeout=1)
    assert ok
    try:
        with pytest.raises(frames.FramesError) as ei:
            frames.run("t1", "render", html=GOOD_HTML)
        assert "Ek render" in str(ei.value) or "chal raha" in str(ei.value)
    finally:
        frames._render_lock.release()


def test_timeout_kills_process_group(hf, tmp_path):
    t0 = time.time()
    with pytest.raises(frames.FramesError) as ei:
        frames._run(["/bin/sleep", "30"], cwd=tmp_path, timeout=1)
    assert time.time() - t0 < 10, "the kill must be immediate, not a 30 s wait"
    assert "killed" in str(ei.value)


# ---------------------------------------------------------------- fake end-to-end
def test_check_fail_blocks_render(hf):
    res = frames.run("t1", "render", html=GOOD_HTML.replace("</body>", "FORCE_CHECK_FAIL</body>"))
    assert res["ok"] is False and res["stage"] == "check"
    assert res["errors"] and "determinism_fetch" in res["errors"][0]
    assert not (frames.tenant_dir("t1") / "out.mp4").exists()


def test_render_fail_surfaces_cli_error(hf):
    with pytest.raises(frames.FramesError) as ei:
        frames.run("t1", "render", html=GOOD_HTML.replace("</body>", "FORCE_RENDER_FAIL</body>"))
    assert "rc=3" in str(ei.value) and "encoder boom" in str(ei.value)


def test_render_ok_delivers_file_card(hf):
    ctx = conv_ctx()
    out = run("hoola_frames", {"action": "render", "html": GOOD_HTML, "name": "Diwali offer film"}, ctx)
    assert out.get("made") == "mp4"
    assert out.get("name") == "Diwali offer film.mp4"
    assert out.get("size") == len("FAKE-MP4-BYTES-0001"), "the card carries the real rendered bytes"
    assert out.get("url"), "the card carries a download url"
    assert "file card" in out.get("note", "")
    assert "file_id" in out
    # the project really rendered into the tenant's own dir
    td = frames.tenant_dir("default")
    assert any((p / "out.mp4").is_file() for p in td.glob("p-*"))


def test_check_and_snapshot_and_timeline_actions(hf):
    ctx = conv_ctx()
    chk = run("hoola_frames", {"action": "check", "html": GOOD_HTML}, ctx)
    assert chk["ok"] is True and "taiyaar" in chk["note"]
    snap = run("hoola_frames", {"action": "snapshot", "html": GOOD_HTML, "times": [1.0, 2.0]}, ctx)
    assert len(snap["pngs"]) == 2 and snap["pngs"][0].endswith(".png")
    tl = run("hoola_frames", {"action": "timeline", "html": GOOD_HTML}, ctx)
    assert "#title" in tl["timeline"]


def test_add_block_end_to_end(hf):
    ctx = conv_ctx()
    out = run("hoola_frames", {"action": "add", "block": "flash-through-white"}, ctx)
    assert out["ok"] is True and "compositions/flash-through-white.html" in out["files"]
    with pytest.raises(ToolError):
        run("hoola_frames", {"action": "add", "block": "../escape"}, ctx)


# ---------------------------------------------------------------- tenants, LRU, janitor
def test_cross_tenant_isolation(hf):
    a, b = frames.tenant_dir("tenant-a"), frames.tenant_dir("tenant-b")
    assert a != b and a.parent == b.parent
    frames.write_project("tenant-a", GOOD_HTML, [])
    assert not any(b.glob("p-*")), "tenant-b sees none of tenant-a's projects"


def test_lru_evicts_oldest(hf, monkeypatch):
    monkeypatch.setenv("FRAMES_PER_TENANT", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    p1 = frames.new_project("t1")
    time.sleep(0.02)
    p2 = frames.new_project("t1")
    time.sleep(0.02)
    p3 = frames.new_project("t1")
    assert p1.exists() is False and p2.exists() and p3.exists(), "oldest project is swept"


def test_janitor_age_and_disk_cap(hf, monkeypatch, tmp_path):
    old = frames.new_project("t1")
    (old / "assets" / "f.bin").write_bytes(b"x" * 1024)
    (old / ".frames_lru").write_text(str(time.time() - 10 * 3600))       # 10 h old
    fat = frames.new_project("t1")
    (fat / "assets" / "fat.bin").write_bytes(b"y" * 700_000)             # weight for the cap sweep
    monkeypatch.setenv("FRAMES_KEEP_H", "2")
    monkeypatch.setenv("FRAMES_DISK_CAP_GB", "0.5")
    from app.config import get_settings
    get_settings.cache_clear()
    res = frames.sweep()
    assert not old.exists(), "a project older than keep_h is swept"
    assert res["removed"] >= 1


# ---------------------------------------------------------------- voice wiring (the v0.213 rule)
def test_voice_wiring():
    from app import voice
    assert "hoola_frames" in voice.VOICE_TOOL_NAMES
    assert "hoola_frames" in voice.VOICE_VIA_KAAM
    assert voice.via_kaam("hoola_frames") is True
    declared = {t["name"] for t in voice._tool_specs()}
    assert "hoola_frames" not in declared, "a minutes-deep render must never be declared to Gemini Live"


# ---------------------------------------------------------------- install + deploy surface
def test_install_script_and_workflow_pins():
    from pathlib import Path
    sh = Path(__file__).resolve().parents[1] / "deploy" / "install_hyperframes.sh"
    assert "hyperframes@0.9.6" in sh.read_text(), "the engine stays PINNED"
    yml = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "vps-ops.yml"
    text = yml.read_text()
    assert "hf_setup" in text and "install_hyperframes.sh" in text
    assert "--kill-timeout 12000" in text, "the pm2 restart keeps the graceful-shutdown headroom"


def test_prompt_contract_and_system_guidance_present():
    from pathlib import Path
    contract = Path(frames.__file__).resolve().parent / "frames_contract.md"
    text = contract.read_text()
    for needle in ("window.__timelines", "data-duration", "No `Date.now()", "action-safe"):
        assert needle in text
    from app.agent import prompts
    assert "hoola_frames" in prompts.SYSTEM, "SYSTEM carries the FRAMES bullet"
