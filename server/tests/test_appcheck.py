"""App Jaanch: REA (stdio MCP) in static-only mode. A fake `rea mcp` stands in for the real one; it records the
environment and tool calls it receives so the safety rules (allowlist, no secrets in the child) are tested too."""
import asyncio
import io
import json
import os
import stat
import sys
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import ToolError, dispatch
from tests.test_bazar import _events
from tests.test_life import conv_ctx

FAKE = r'''#!PY
import json, os, sys
HERE = os.path.dirname(__file__)
open(os.path.join(HERE, "env.json"), "w").write(json.dumps(sorted(os.environ)))
def fixture(n, d=""):
    p = os.path.join(HERE, n)
    return open(p).read() if os.path.exists(p) else d
MAN = fixture("manifest.xml")
for line in sys.stdin:
    m = json.loads(line)
    if "id" not in m:
        continue
    with open(os.path.join(os.path.dirname(__file__), "calls.log"), "a") as f:
        f.write(json.dumps([m["method"], (m.get("params") or {}).get("name")]) + "\n")
    if m["method"] == "initialize":
        r = {"protocolVersion": "2025-06-18", "serverInfo": {"name": "rea", "version": "6.7.0"}, "capabilities": {}}
    else:
        name = m["params"]["name"]; args = m["params"]["arguments"]
        if name == "inspect_android_package":
            meta = json.loads(fixture("pkg.json", "{}"))
            nr = dict(meta, manifest={"status": "complete", "text": MAN}, class_count=12)
        elif name == "identify_flutter_build":
            nr = {"flutter_detected": False}
        elif name == "inspect_pe_resources":
            nr = {"resources": []}
        elif name == "inspect_managed_artifact":
            nr = {"kind": "summary", "summary": {"classification": {"status": "not-managed"}}}
        else:
            nr = {}
        sc = {"evidence_id": "ev_1", "normalized_result": nr}
        r = {"content": [{"type": "text", "text": json.dumps(sc)}], "structuredContent": sc}
    print(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": r}), flush=True)
'''

SCAM_MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.kisan.help">
  <application android:label="PM Kisan">
    <activity android:name=".Main"/>
    <service android:name=".Acc" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"/>
    <receiver android:name=".Sms"><intent-filter><action android:name="android.provider.Telephony.SMS_RECEIVED"/></intent-filter></receiver>
  </application>
</manifest>"""

CLEAN_MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.example.notes">
  <application android:label="@string/app_name">
    <activity android:name=".Main"><intent-filter><action android:name="android.intent.action.MAIN"/>
      <category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity>
  </application>
</manifest>"""


@pytest.fixture
def rea(env, tmp_path, monkeypatch):
    d = tmp_path / "rea"
    d.mkdir()
    exe = d / "rea"
    exe.write_text(FAKE.replace("#!PY", "#!" + sys.executable))
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    jar = d / "jadx.jar"
    jar.write_bytes(b"jar")
    monkeypatch.setenv("REA_BIN", str(exe))
    monkeypatch.setenv("REA_JADX_JAR", str(jar))
    monkeypatch.setenv("REA_HOME", str(tmp_path / "rea_home"))
    monkeypatch.setenv("PC_FILES_DIR", str(tmp_path / "pc_files"))
    monkeypatch.setenv("SECRET_KEY", "do-not-leak")
    from app.config import get_settings
    get_settings.cache_clear()
    return d


def _apk(manifest_bin=b"x", signed=False) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("AndroidManifest.xml", manifest_bin)
        z.writestr("classes.dex", b"dex\n035")
        if signed:
            z.writestr("META-INF/CERT.RSA", b"not-a-real-cert")
    return b.getvalue()


def _file(name, data):
    from app.mailbox import service as ms
    return ms.store_bytes("default", name, data, "mail").id


def setup(d, manifest, pkg):
    (d / "manifest.xml").write_text(manifest)
    (d / "pkg.json").write_text(json.dumps(pkg))


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


def test_scam_apk_is_danger(rea, monkeypatch):
    setup(rea, SCAM_MANIFEST, ({"package_name": "com.kisan.help", "version_name": "1.0", "target_sdk": "26",
                                               "permissions": ["android.permission.READ_SMS", "android.permission.RECEIVE_SMS",
                                                               "android.permission.INTERNET"]}))
    ctx = conv_ctx()
    out = run("app_check", {"file_id": _file("PM Kisan Yojana.apk", _apk())}, ctx)
    assert out["verdict"] == "danger" and out["kind"] == "apk"
    text = " ".join(out["findings"])
    assert "SMS" in text and "accessibility" in text and "icon" in text and "pm kisan" in text and "signature" in text
    assert out["facts"]["package"] == "com.kisan.help"
    card = _events(ctx.conversation_id, "app_check")[-1]
    assert card["verdict"] == "danger" and card["flags"][0]["level"] == "high" and "1930" in card["advice"]
    # REA never saw Santosh's secrets, and only static tools were called
    env_keys = json.loads((rea / "env.json").read_text())
    assert "SECRET_KEY" not in env_keys and "ANTHROPIC_API_KEY" not in env_keys and "DATABASE_URL" not in env_keys
    assert "REA_JADX_MCP_JAR" in env_keys
    calls = [json.loads(x) for x in (rea / "calls.log").read_text().splitlines()]
    assert {c[1] for c in calls if c[0] == "tools/call"} <= {"inspect_android_package", "identify_flutter_build"}


def test_clean_apk_and_cache(rea, monkeypatch):
    setup(rea, CLEAN_MANIFEST, ({"package_name": "com.example.notes", "version_name": "2.1", "target_sdk": "34",
                                               "permissions": ["android.permission.INTERNET"]}))
    ctx = conv_ctx()
    data = _apk(signed=True)
    out = run("app_check", {"file_id": _file("notes-2.1.apk", data)}, ctx)
    assert out["verdict"] == "clear", out
    assert "guarantee" in out["verdict_text"]
    n = len((rea / "calls.log").read_text().splitlines())
    again = run("app_check", {"file_id": _file("copy.apk", data)}, ctx)
    assert again["verdict"] == "clear" and len((rea / "calls.log").read_text().splitlines()) == n   # same file: no new REA run


def test_exe_double_extension(rea):
    ctx = conv_ctx()
    out = run("app_check", {"file_id": _file("Electricity_Bill.pdf.exe", b"MZ" + b"\0" * 200)}, ctx)
    assert out["verdict"] == "danger" and out["kind"] == "exe"
    assert any("do extension" in f for f in out["findings"])


def test_script_and_zip_without_rea_calls(rea):
    ctx = conv_ctx()
    out = run("app_check", {"file_id": _file("kyc_update.vbs", b"WScript.Echo 1")}, ctx)
    assert out["verdict"] == "danger"
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("docs/invoice.pdf.exe", b"MZ")
    out = run("app_check", {"file_id": _file("invoice.zip", b.getvalue())}, ctx)
    assert out["verdict"] == "danger" and out["facts"]["programs_inside"] == ["docs/invoice.pdf.exe"]


def test_only_static_tools_allowed(rea):
    from app.appcheck.runner import ReaError, Session
    with Session() as s:
        for bad in ("instrument_with_frida", "gdb_console", "install_adb_package", "capture_process_scenario", "cutter_command"):
            with pytest.raises(ReaError, match="band hai"):
                s.call(bad, {})
    calls = [json.loads(x) for x in (rea / "calls.log").read_text().splitlines()]
    assert all(c[0] != "tools/call" for c in calls)


def test_not_configured(env):
    ctx = conv_ctx()
    from app.mailbox import service as ms
    fid = ms.store_bytes("default", "a.apk", _apk(), "mail").id
    with pytest.raises(ToolError, match="REA"):
        run("app_check", {"file_id": fid}, ctx)
    from app.bazar.packs.registry import registry
    assert registry().get("santosh-appcheck").executor == "appcheck"


def test_upload_api(rea, monkeypatch):
    setup(rea, CLEAN_MANIFEST, ({"package_name": "com.example.notes", "permissions": []}))
    from app import main
    with TestClient(main.app) as c:
        st = c.get("/api/appcheck").json()
        assert st["enabled"] and st["apk"]
        r = c.post("/api/appcheck/upload", files={"file": ("notes.apk", io.BytesIO(_apk(signed=True)), "application/vnd.android.package-archive")}).json()
        assert r["verdict"] == "clear" and r["facts"]["package"] == "com.example.notes"
        assert c.get("/api/appcheck").json()["history"][0]["name"] == "notes.apk"
        assert c.get(f"/api/appcheck/{r['id']}").json()["sha256"] == r["sha256"]
    _ = os
