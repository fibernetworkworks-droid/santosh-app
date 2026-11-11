"""KAAN W5 (v0.670.0, owner: "W5 - MCP + API + extension audio" - Wave W5 of the kaan plan).

One brain, three doors: the HTTP API (/api/kaan/*), the MCP stdio server
(python -m app.kaan.mcp_server), and the browser extension's tab audio - all three
reach the SAME KS functions the `kaan` tool serves, with the SAME gates (audio ingest
rides kaan_audio; reads gate-free by the W1 law). REGISTRY 606 UNCHANGED - W5 adds
transport doors, zero new actions (enum stays 18). Zero network, zero torch; the
engine is scripted, the extension is pinned by source.
"""
import ast
import asyncio
import inspect
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent.kaan_tools import KAAN_TOOLS, _ACTIONS
from app.kaan import mcp_server as MC
from app.kaan import service as KS
from tests.test_v0618_kaan_w2 import CHUNK_S, fake_decoder, pcm, window_engine, SCRIPT
from tests.test_v0656_kaan_w4 import capture_engine

EXT = Path(__file__).resolve().parents[2] / "desktop" / "ext" / "hoola-extension"
H = {"Authorization": "Bearer k5"}


@pytest.fixture()
def w5_env(env, tmp_path, monkeypatch):
    """Fresh DB (env) + AUDIO gate ON + engine ready + gyaan sync/hash + the API key for HTTP."""
    monkeypatch.setenv("KAAN_AUDIO", "true")
    monkeypatch.setenv("KAAN_MODEL", "small")
    monkeypatch.setenv("KAAN_LIVE_DIR", str(tmp_path / "kaan_live"))
    monkeypatch.setenv("GYAAN_SYNC", "true")
    monkeypatch.setenv("GYAAN_EMBED", "hash")
    monkeypatch.setenv("API_KEY", "k5")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.kaan import engine as EN
    from app.kaan import service as KS
    EN._AVAIL.clear()
    KS.EN._AVAIL.clear()                                    # service's OWN binding (laziness tests pop sys.modules)
    monkeypatch.setitem(EN._AVAIL, "ok", (True, "engine ready"))
    monkeypatch.setitem(KS.EN._AVAIL, "ok", (True, "engine ready"))
    from app.gyaan import embed
    embed.reset()
    yield monkeypatch
    get_settings.cache_clear()
    EN._AVAIL.clear()
    KS.EN._AVAIL.clear()
    embed.reset()


def client():
    from app.main import app
    return TestClient(app)


def seed_row(env_m, name="t.wav", text="namaste gupta ji. kal milan hoga."):
    """One stored transcript through the REAL service, engine scripted."""
    return KS.transcribe_file("default", name=name, data=b"x", fn=capture_engine({}, text=text))


# ---------------------------------------------------------------- (1) the HTTP door
def test_api_needs_a_key(w5_env):
    with client() as c:
        assert c.get("/api/kaan/status").status_code == 401
        assert c.post("/api/kaan/transcribe", files={"file": ("t.wav", b"x", "audio/wav")}).status_code == 401


def test_transcribe_end_to_end_over_http(w5_env):
    store: dict = {}
    from app.kaan import engine as EN
    from app.kaan import service as KS
    w5_env.setattr(KS.EN, "transcribe", capture_engine(store))    # the binding the route dispatches through
    w5_env.setattr(EN, "transcribe", capture_engine(store))       # and the sys.modules object (they split after laziness pops)
    with client() as c:
        r = c.post("/api/kaan/transcribe", headers=H, files={"file": ("t.wav", b"x", "audio/wav")})
        assert r.status_code == 200
        d = r.json()
        assert d["id"].startswith("kn_") and "namaste gupta ji." in d["text"] and d["task"] == "transcribe"
        assert store["prompt"] is not None                        # vocab prompt rode the door too
        row = c.get(f"/api/kaan/{d['id']}", headers=H).json()
        assert row["id"] == d["id"] and row["file_name"] == "t.wav"


def test_transcribe_gate_off_is_an_honest_400(w5_env):
    w5_env.setenv("KAAN_AUDIO", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    with client() as c:
        r = c.post("/api/kaan/transcribe", headers=H, files={"file": ("t.wav", b"x", "audio/wav")})
        assert r.status_code == 400 and "kaan_audio" in r.json()["detail"]


def test_list_search_over_http(w5_env):
    tid = seed_row(w5_env)["id"]
    with client() as c:
        lst = c.get("/api/kaan/list", headers=H).json()["items"]
        assert tid in [x["id"] for x in lst]
        s = c.get("/api/kaan/search", headers=H, params={"q": "milan"}).json()
        assert s["q"] == "milan" and tid in [x["id"] for x in s["items"]]


def test_export_over_http_download_and_dict(w5_env):
    tid = seed_row(w5_env)["id"]
    with client() as c:
        raw = c.get(f"/api/kaan/{tid}/export", headers=H, params={"fmt": "srt", "download": 1})
        assert raw.status_code == 200 and raw.headers["content-disposition"] == f'attachment; filename="{tid}.srt"'
        assert raw.text == KS.export_transcript("default", tid, "srt")["text"]   # the SAME bytes the service renders
        d = c.get(f"/api/kaan/{tid}/export", headers=H, params={"fmt": "json"}).json()
        assert d["fmt"] == "json" and d["tid"] == tid and "sort_keys" in d["note"]


def test_style_minutes_diarize_to_gyaan_over_http(w5_env):
    tid = seed_row(w5_env)["id"]
    with client() as c:
        st = c.post(f"/api/kaan/{tid}/style", headers=H, json={"style": "subtitles"}).json()
        assert st["style"] == "subtitles" and st == KS.style_render("default", tid, "subtitles")
        m = c.get(f"/api/kaan/{tid}/minutes", headers=H).json()
        assert m["tid"] == tid and m["turns"] and m["keywords"]      # the W1 skeleton, over HTTP
        dz = c.post(f"/api/kaan/{tid}/diarize", headers=H, json={"names": {"1": "Gupta ji"}}).json()
        assert dz["n_turns"] >= 1 and dz["id"] == tid
        g = c.post(f"/api/kaan/{tid}/to_gyaan", headers=H).json()
        assert g["gyaan"]["status"] in ("added", "updated")
        again = c.post(f"/api/kaan/{tid}/to_gyaan", headers=H).json()
        assert again["gyaan"]["status"] == "same"                 # the content-hash idempotency rides the door too


def test_vocab_crud_over_http(w5_env):
    with client() as c:
        assert c.post("/api/kaan/vocab", headers=H, json={"term": "Gupta", "fix_to": "Gupta ji"}).json()["id"].startswith("kv_")
        lst = c.get("/api/kaan/vocab", headers=H).json()
        assert lst["n"] == 1 and lst["items"][0]["term"] == "Gupta"
        gone = c.delete("/api/kaan/vocab/Gupta", headers=H).json()
        assert gone["removed"] == "Gupta" and gone["ok"] is True
        assert c.get("/api/kaan/vocab", headers=H).json()["n"] == 0
        bad = c.delete("/api/kaan/vocab/Absent", headers=H)
        assert bad.status_code == 400 and "Absent" in bad.json()["detail"]


def test_live_over_http_start_chunk_stop(w5_env, monkeypatch):
    from app.kaan import service as KS
    LV = KS.LV                                              # the module object the routes REALLY dispatch through
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    monkeypatch.setattr(LV.EN, "transcribe", window_engine(SCRIPT))
    with client() as c:
        sess = c.post("/api/kaan/live/start", headers=H, json={}).json()
        assert sess["id"].startswith("kl_") and sess["status"] == "live"
        sid = sess["id"]
        ch = c.post(f"/api/kaan/live/{sid}/chunk", headers=H, content=pcm(CHUNK_S)).json()
        assert ch["n_phrases"] >= 1 and ch["ran"] is True
        stopped = c.post(f"/api/kaan/live/{sid}/stop", headers=H, json={}).json()
        assert stopped["status"] == "done" and stopped["transcript_id"].startswith("kn_")
        row = c.get(f"/api/kaan/{stopped['transcript_id']}", headers=H).json()
        assert row["file_name"] == f"live:{sid}" and row["model"] == "base"   # the W2 row shape, over HTTP
        got = c.get(f"/api/kaan/live/{sid}", headers=H).json()
        assert got["status"] == "done" and got["captions_tail"]
        assert sid in [x["id"] for x in c.get("/api/kaan/live", headers=H).json()["items"]]


def test_tenant_isolation_over_http(w5_env):
    tid = seed_row(w5_env)["id"]
    with client() as c:
        r = c.get(f"/api/kaan/{tid}/export", headers={"Authorization": "Bearer k5"}, params={"fmt": "srt"})
        # the SAME tenant here; now prove the isolation at the service law: a foreign tid is an honest 400
        assert r.status_code == 200
        r2 = c.get("/api/kaan/kn_missing_row/export", headers=H, params={"fmt": "srt"})
        assert r2.status_code == 400 and "not found" in r2.json()["detail"]


def test_status_route_carries_the_doors_block(w5_env):
    with client() as c:
        d = c.get("/api/kaan/status", headers=H).json()
        assert d["doors"]["api"] == "/api/kaan (HTTP, W5)"
        assert "mcp_server" in d["doors"]["mcp"] and "tabCapture" in d["doors"]["ext"]
        assert "SAME KS functions" in d["doors"]["note"]


# ---------------------------------------------------------------- (2) the MCP door
def test_mcp_initialize_handshake(w5_env):
    out = MC.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, "default")
    assert out["result"]["protocolVersion"] == MC.PROTOCOL_VERSION == "2025-06-18"
    assert out["result"]["serverInfo"]["name"] == "hoola-kaan"
    assert out["result"]["capabilities"]["tools"] == {}


def test_mcp_tools_list_one_tool_18_actions(w5_env):
    out = MC.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, "default")
    tools = out["result"]["tools"]
    assert len(tools) == 1 and tools[0]["name"] == "kaan"      # the house law travels with the door
    assert tools[0]["input_schema"]["properties"]["action"]["enum"] == _ACTIONS and len(_ACTIONS) == 18


def test_mcp_tools_call_status_export_gyaan(w5_env):
    tid = seed_row(w5_env)["id"]
    call = lambda **a: MC.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                  "params": {"name": "kaan", "arguments": a}}, "default")["result"]
    s = call(action="status")
    assert s["isError"] is False and s["structuredContent"]["doors"]["api"].startswith("/api/kaan")
    e = call(action="export", id=tid, fmt="srt")
    assert e["structuredContent"]["fmt"] == "srt" and "namaste gupta ji." in e["structuredContent"]["text"]
    assert json.loads(e["content"][0]["text"])["tid"] == tid
    g = call(action="to_gyaan", id=tid)
    assert g["structuredContent"]["gyaan"]["status"] in ("added", "updated")
    g2 = call(action="to_gyaan", id=tid)
    assert g2["structuredContent"]["gyaan"]["status"] == "same"


def test_mcp_honest_refusal_is_error_content(w5_env):
    call = lambda **a: MC.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                                  "params": {"name": "kaan", "arguments": a}}, "default")["result"]
    bad = call(action="flying")
    assert bad["isError"] is True and "flying" in bad["content"][0]["text"]
    wrong_tool = MC.handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                            "params": {"name": "other", "arguments": {}}}, "default")["result"]
    assert wrong_tool["isError"] is True and "exactly one tool" in wrong_tool["content"][0]["text"]
    missing = call(action="get", id="kn_absent_row")
    assert missing["isError"] is True and "kn_absent_row" in missing["content"][0]["text"]   # the honest house line names the row


def test_mcp_gate_rides_the_door(w5_env):
    w5_env.setenv("KAAN_AUDIO", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    call = lambda **a: MC.handle({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                                  "params": {"name": "kaan", "arguments": a}}, "default")["result"]
    out = call(action="transcribe", name="t.wav")                # the gate fires before any data check
    assert out["isError"] is True and "kaan_audio" in out["content"][0]["text"]
    get_settings.cache_clear()


def test_mcp_unknown_method_parse_error_notifications(w5_env):
    bad = MC.respond("garbage {", "default")
    assert bad["error"]["code"] == -32700
    unk = MC.handle({"jsonrpc": "2.0", "id": 7, "method": "prompts/list"}, "default")
    assert unk["error"]["code"] == -32601 and "initialize" in unk["error"]["message"]
    assert MC.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}, "default") is None


def test_mcp_dispatch_is_the_tool_dispatch(w5_env):
    src = inspect.getsource(MC._dispatch)
    assert "_sync" in src and "Ctx(" in src                    # ONE dispatch path with the agent tool
    assert "owner" not in inspect.getsource(MC.handle)         # actor = the Ctx default, by construction


# ---------------------------------------------------------------- (3) purity + registry + pins
def test_api_and_mcp_purity(w5_env):
    for name in ("api.py", "mcp_server.py"):
        tree = ast.parse((Path(__file__).resolve().parents[1] / "app" / "kaan" / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and node.col_offset == 0:
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                for m in mods:
                    assert not any(x in (m or "") for x in ("httpx", "requests", "openai", "whisper", "fastapi" if name == "mcp_server.py" else "___never___")), \
                        f"{name} top-level import {m} breaks the purity law"


def test_importing_mcp_server_loads_no_engine(w5_env):
    """The inertness law, proven in a FRESH interpreter: module load pulls no engine, no gyaan."""
    import subprocess
    import sys
    code = ("import sys; import app.kaan.mcp_server; "
            "print('engine' if 'app.kaan.engine' in sys.modules else 'clean', "
            "'gyaan' if 'app.gyaan' in sys.modules else 'clean')")
    root = Path(__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-400:]
    assert out.stdout.strip() == "clean clean"


def test_registry_607_enum_18(w5_env):
    from app.agent.tools import TOOLS
    assert len(TOOLS) == 627                                   # +1 app_engine (v0.824); +1 seekh_video (v0.713 SEEKH MANCH); W5 adds doors, not tools (609 = 608 + 1 kala + 607 + 1 duniya, v0.667 DUNIYA MANCH)
    assert len(_ACTIONS) == 18 and "export" in _ACTIONS and "to_gyaan" in _ACTIONS
    assert KAAN_TOOLS[0]["input_schema"]["properties"]["action"]["enum"] == _ACTIONS


def test_extension_source_pins():
    manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.9.0"                   # the extension version rides the desktop (house coupling law)
    assert "tabCapture" in manifest["permissions"] and "offscreen" in manifest["permissions"]   # the W5 ears
    bg = (EXT / "background.js").read_text(encoding="utf-8")
    assert "captions-start" in bg and "captions-stop" in bg and "captions-halt" in bg
    assert "getMediaStreamId" in bg and "USER_MEDIA" in bg and "/api/kaan/live" in bg
    off = (EXT / "offscreen.js").read_text(encoding="utf-8")
    assert "MediaRecorder" in off and "chromeMediaSource" in off and "/api/kaan/live/" in off and "Bearer" in off
    assert "rec.start(2000)" in off
    pop = (EXT / "popup.js").read_text(encoding="utf-8")
    assert "captions_tail" in pop and "setInterval(pollCaptions, 3000)" in pop and "captions-start" in pop
    html = (EXT / "popup.html").read_text(encoding="utf-8")
    assert 'id="capstart"' in html and 'id="caps"' in html
    assert (EXT / "offscreen.html").exists()


def test_status_function_doors(w5_env):
    d = KS.status("default")["doors"]
    assert d["api"] == "/api/kaan (HTTP, W5)" and "stdio" in d["mcp"] and "tabCapture" in d["ext"]


def test_app_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.832.0"
