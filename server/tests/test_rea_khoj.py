"""REA Khoj: the avatar reverse-engineers an app / program / file it has, statically, on user call.

A fake `rea mcp` stands in for the real one; it records every call so the allowlist rule
(static, read-only only; runtime tools refused before REA) is tested, plus the routing
from the model's tool call to REA's tool + the per-tenant LRU file cache that keeps one
investigation stable across turns.
"""
import asyncio
import json
import os
import stat
import sys
import zipfile

import pytest

from app.agent import rea_tools as rt
from app.agent.tools import HANDLERS, TOOLS, TOOL_LABELS, ToolError, dispatch
from app.appcheck import khoj, runner
from tests.test_appcheck import _apk, _file   # reuse the mailbox-store + fake-apk helpers
from tests.test_life import conv_ctx

KHOJ_FAKE = r'''#!PY
import json, os, sys
HERE = os.path.dirname(__file__)
def fixture(n, d=""):
    p = os.path.join(HERE, n)
    return open(p).read() if os.path.exists(p) else d
MAN = fixture("manifest.xml", "<manifest/>")
for line in sys.stdin:
    try: m = json.loads(line)
    except Exception: continue
    if "id" not in m: continue
    if m["method"] == "initialize":
        r = {"protocolVersion": "2025-06-18", "serverInfo": {"name": "rea", "version": "6.8.0"}, "capabilities": {}}
    else:
        name = m["params"]["name"]
        if name == "inspect_android_package":
            nr = {"package_name": "com.example.notes", "version_name": "1.2", "min_sdk": "21", "target_sdk": "34",
                  "permissions": ["android.permission.INTERNET", "android.permission.READ_SMS"],
                  "class_count": 7, "manifest": {"text": MAN}}
        elif name == "inspect_android_method":
            nr = {"source": "x" * 9000, "representation": "java", "prototype": "void onCreate()"}
        elif name == "search_android_classes":
            nr = {"classes": ["com.example.notes.MainActivity", "com.example.notes.NoteAdapter"]}
        elif name == "inspect_android_class":
            nr = {"methods": [{"name": "onCreate"}, {"name": "onClick", "overload_count": 1}], "fields": [], "inner_classes": []}
        elif name == "trace_android_references":
            nr = {"incoming": ["com.example.notes.MainActivity$1", "com.example.App"]}
        elif name == "inspect_apk_signature":
            nr = {"signers": [{"subject": "CN=Test"}]}
        elif name == "identify_flutter_build":
            nr = {"flutter_detected": False}
        elif name == "inspect_il2cpp_metadata":
            nr = {}
        elif name == "inspect_byte_entropy":
            nr = {"file_entropy": 7.10}
        else:
            nr = {}
        sc = {"evidence_id": "ev", "normalized_result": nr}
        r = {"content": [{"type": "text", "text": json.dumps(sc)}], "structuredContent": sc}
    print(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": r}), flush=True)
'''

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.example.notes">
  <application android:label="Notes"><activity android:name=".Main"><intent-filter>
    <action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/>
  </intent-filter></activity></application>
</manifest>"""


@pytest.fixture
def rea(env, tmp_path, monkeypatch):
    d = tmp_path / "rea"
    d.mkdir()
    exe = d / "rea"
    exe.write_text(KHOJ_FAKE.replace("#!PY", "#!" + sys.executable))
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    (d / "manifest.xml").write_text(MANIFEST)
    jar = d / "jadx.jar"
    jar.write_bytes(b"jar")
    monkeypatch.setenv("REA_BIN", str(exe))
    monkeypatch.setenv("REA_JADX_JAR", str(jar))
    monkeypatch.setenv("REA_HOME", str(tmp_path / "rea_home"))
    monkeypatch.setenv("PC_FILES_DIR", str(tmp_path / "pc_files"))
    from app.config import get_settings
    get_settings.cache_clear()
    return d


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


# ---------------------------------------------------------------- unit: version + registry
def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.281.0"


def test_rea_khoj_registry():
    assert len(rt.REA_TOOLS) == 1
    t = rt.REA_TOOLS[0]
    assert t["name"] == "rea_khoj"
    assert set(t["input_schema"]["properties"]) >= {"action", "file_id", "email_id", "attachment_id", "drive",
                                                     "query", "class_name", "method_name", "overload_index"}
    assert t["input_schema"]["properties"]["action"]["enum"] == ["overview", "classes", "class", "method", "refs",
                                                                  "signature", "status", "endpoints"]   # v0.257
    assert set(rt.REA_HANDLERS) == {"rea_khoj"}
    assert set(rt.REA_LABELS) == {"rea_khoj"}


def test_global_registry_reach():
    reg = {t["name"] for t in TOOLS}
    assert "rea_khoj" in reg and "rea_khoj" in HANDLERS and "rea_khoj" in TOOL_LABELS


# ---------------------------------------------------------------- allowlist: 31 static tools, refuse runtime
NEW_TOOLS = {"search_android_classes", "inspect_android_class", "inspect_android_method", "trace_android_references",
             "inspect_apk_signature", "inspect_dart_aot", "inspect_il2cpp_metadata", "inspect_pe_imports",
             "inspect_pe_certificates", "inspect_pe_load_config", "inspect_managed_members", "inspect_native_exports",
             "inspect_elf_notes", "inspect_kernel_module", "inspect_apple_ips", "inspect_erlang_beam",
             "inspect_python_pyc", "inspect_model_artifact", "inspect_gpu_code_objects", "inspect_devicetree",
             "inspect_evm_interface", "inspect_sqlite_database", "inspect_desktop_application", "inspect_byte_entropy"}
DANGEROUS = {"execute_rizin_command", "list_frida_processes", "start_frida_session", "load_frida_script",
             "start_gdb_session", "start_rizin_debug_session", "list_cutter_sessions", "cutter_command",
             "observe_web_session", "observe_web_execution", "capture_web_screenshot", "install_adb_package",
             "list_adb_devices", "start_adb_app", "instrument_with_frida", "capture_electron_scenario",
             "capture_process_scenario", "list_browser_targets", "inspect_web_page", "analyze_web_bundle",
             "extract_firmware", "recover_javascript_sources", "decompile_jeb_item", "open_jeb_project"}


def test_allowlist_size_and_static_only():
    assert len(runner.ALLOWED) == 31, f"want 31, got {len(runner.ALLOWED)}"
    for t in NEW_TOOLS:
        assert t in runner.ALLOWED, f"missing {t}"
    for t in DANGEROUS:
        assert t not in runner.ALLOWED, f"dangerous tool in allowlist: {t}"


def test_session_call_refuses_unlisted_before_ipc(monkeypatch):
    """The refusal must happen BEFORE any stdio write (no leak of a forbidden tool name to REA)."""
    class Boom:
        server_info = {}
        work = None
        def _rpc(self, *a, **k):
            raise AssertionError("ALLOWED refusal must short-circuit before _rpc")
    monkeypatch.setattr(runner, "ALLOWED", runner.ALLOWED | {"__safe_probe__"})
    boom = Boom()
    # a tool NOT in ALLOWED -> ReaError before _rpc
    with pytest.raises(runner.ReaError):
        runner.Session.call(boom, "execute_rizin_command", {"command": "px 16"})
    monkeypatch.setattr(runner, "ALLOWED", runner.ALLOWED - {"__safe_probe__"})


# ---------------------------------------------------------------- status + guards (no REA needed)
def test_status_unconfigured(monkeypatch):
    monkeypatch.delenv("REA_BIN", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    st = khoj.status()
    assert st["enabled"] is False and st["apk"] is False and st["max_mb"] == 400 and st["tools"] == 31
    assert {"apk", "exe", "elf", "electron", "sqlite"} <= set(st["kinds"])


def test_handler_status_action_no_src(env):
    ctx = conv_ctx()
    out = run("rea_khoj", {"action": "status"}, ctx)
    assert out["tools"] == 31 and out["max_mb"] == 400


def test_handler_missing_src(env):
    ctx = conv_ctx()
    with pytest.raises(ToolError) as ei:
        run("rea_khoj", {"action": "overview"}, ctx)
    assert "Kaunsi file" in str(ei.value)


def test_handler_bad_action(env):
    ctx = conv_ctx()
    with pytest.raises(ToolError):
        run("rea_khoj", {"action": "crack_it", "file_id": "x"}, ctx)


# ---------------------------------------------------------------- evidence shaping
def test_compact_bounds():
    c = khoj._compact({"s": "x" * 1000, "lst": list(range(50)), "deep": {"d": {"e": {"f": {"g": "h"}}}}})
    assert len(c["s"]) <= 320 + 30
    assert c["lst"][-1].startswith("+20") or c["lst"][-1] == 49 or isinstance(c["lst"][-1], str)
    # values nested at depth >= 5 are clipped ("<…>") so a runaway REA result never floods a turn
    assert "deep" in c and c["deep"]["d"]["e"]["f"]["g"] == "<…>"
    assert khoj._compact({"x": {"y": {"z": {"w": {"v": "bottom"}}}}})["x"]["y"]["z"]["w"]["v"] == "<…>"


def test_longest_text_finds_nested():
    src = khoj._longest_text({"a": "short", "b": {"c": "x" * 9000}}, n=6000)
    assert len(src) <= 6100 and src.startswith("x")
    assert "aur chars" in src   # the clip note


# ---------------------------------------------------------------- end-to-end routing on the fake rea
def test_routing_apk_overview(rea):
    ctx = conv_ctx()
    fid = _file("notes.apk", _apk())
    out = run("rea_khoj", {"action": "overview", "file_id": fid}, ctx)
    assert out["kind"] == "apk"
    f = out["facts"]
    assert f["package"] == "com.example.notes" and f["version"] == "1.2"
    assert f["uses_internet"] is True and "android.permission.READ_SMS" in f["permissions"]
    assert f["classes"] == 7 and f["signed_by"] in ("", None)
    assert "classes" in " ".join(out["next"])   # the model is told the next probe


def test_routing_method_source_clip(rea):
    ctx = conv_ctx()
    fid = _file("notes.apk", _apk())
    out = run("rea_khoj", {"action": "method", "file_id": fid, "class_name": "com.example.notes.Main",
                           "method_name": "onCreate"}, ctx)
    # REA returned a 9000-char source; the tool MUST clip it before it lands in the model's turn
    assert len(out["source"]) <= 6100 and out["source"].startswith("x") and "aur chars" in out["source"]
    assert out["representation"] == "java" and out["class"] == "com.example.notes.Main" and out["method"] == "onCreate"


def test_routing_classes_search(rea):
    ctx = conv_ctx()
    fid = _file("notes.apk", _apk())
    out = run("rea_khoj", {"action": "classes", "file_id": fid, "query": "Activity"}, ctx)
    assert out["count"] == 2 and out["classes"][0] == "com.example.notes.MainActivity"
    assert "method" in " ".join(out["next"])


def test_routing_refs_and_class(rea):
    ctx = conv_ctx()
    fid = _file("notes.apk", _apk())
    r = run("rea_khoj", {"action": "refs", "file_id": fid, "class_name": "com.example.notes.Main"}, ctx)
    assert r["used_by"][0] == "com.example.notes.MainActivity$1"
    c = run("rea_khoj", {"action": "class", "file_id": fid, "class_name": "com.example.notes.Main"}, ctx)
    assert any(m["name"] == "onCreate" for m in c["methods"]) and len(c["methods"]) == 2


def test_routing_signature(rea):
    ctx = conv_ctx()
    fid = _file("notes.apk", _apk())
    out = run("rea_khoj", {"action": "signature", "file_id": fid}, ctx)
    assert out["kind"] == "apk" and out["rea_signature"]["signers"][0]["subject"] == "CN=Test"


# ---------------------------------------------------------------- per-tenant LRU cache reuse
def test_stage_cache_reuse_across_calls(rea, tmp_path):
    fid = _file("notes.apk", _apk())
    n1, p1, _ = khoj._stage("default", {"file_id": fid})
    n2, p2, _ = khoj._stage("default", {"file_id": fid})
    assert n1 == n2 and p1 == p2, "second stage call MUST reuse the cached copy, not copy again"
    # cross-tenant isolation: a file stored under a different tenant gets its own cache dir
    from app.mailbox import service as ms
    fid_other = ms.store_bytes("other", "notes.apk", _apk(), "mail").id
    n3, p3, _ = khoj._stage("other", {"file_id": fid_other})
    from pathlib import Path
    assert Path(p3).parent.parent != Path(p1).parent.parent
