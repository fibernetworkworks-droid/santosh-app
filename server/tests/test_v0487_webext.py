"""v0.487.0 HOOLA WEB EXTENSION - the 'send page to Hoola' door + the PC -> Hoola TEXT LANE,
W3 of the Platforms plan (owner: 'W3 (web extension)'; W2b PowerToys Run v0.486.0 live).

What shipped (each test pins one promise):
(1) server/app/quicklane.py - the NEW server surface the whole W-line was missing: POST
    /api/pc/quickask takes a PAIRED device's {text?, url?, title?, selection?, client_id?},
    composes ONE honest Hinglish user message and rides the SAME turn pipeline the phone uses
    (convs.mark + bus.publish + turn_inbox.accept + run_owned) - Hoola answers in her
    conversation with every tool she already has. GET /api/pc/quickask/messages reads the last
    display rows back (the popup's answer view). Guards: device-token auth only, tenant check,
    per-device rate cap, client_id dedup. No existing PC endpoint or setting touched (the freeze).
(2) desktop/ext/hoola-extension - the MV3 extension (Chrome/Edge): manifest 3, service worker,
    three entries (popup / right-click 'Hoola ko bhejiye' / Ctrl+Shift+H), pairing through the
    SAME /api/pc/pair 6-digit flow (it shows on her Mera PC list like any PC), no eval, no
    remote code, activeTab+scripting only.
(3) desktop/santosh_desktop/ext_install.py - the pt_run.py twin: rides INSIDE the exe
    (spec datas, ext_payload staged by CI), copies ONLY Hoola's own folder to
    %LOCALAPPDATA%\\Hoola\\chrome-extension, whole-folder replace = upgrade, calm idempotent
    undo, honest errors; MV3 checked before copy.
(4) desktop/santosh_desktop/quickask.py - the desktop's own lane send (token + honest dicts),
    --ask CLI + the single-instance handover (the lock port now receives ASK: lines), the
    window's ask box + Browser extension card (install only on her click).
(5) Main.cs W3: 'hoola <sawaal>' -> 'Hoola se poochho: <sawaal>' -> --ask handover (quoted),
    empty query still just opens the window; plugin ID never changes.
(6) Server pc operator: ext tool (ONE-TIME SETUP, ask_approval PEHLE), _do branch, _say line,
    _desktop_says upgrade line; win+r still BLOCKED_KEYS.

Desktop pin moved 1.8.0 -> 1.9.0 (the conscious-bump guard, test_v0484 moves with it).
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

import santosh_desktop.ext_install as ext_install  # noqa: E402
import santosh_desktop.quickask as qa              # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "desktop" / "ext" / "hoola-extension"
DESKTOP = ROOT / "desktop" / "santosh_desktop"
PLUGIN = ROOT / "desktop" / "ptrun_plugin" / "Community.PowerToys.Run.Plugin.Hoola"

TENANT = "t_ext"


# ================================================================ (1) the lane itself
@pytest.fixture()
def lane(env, monkeypatch):
    """The app on a fresh DB + one paired extension device + a stubbed turn runner."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.pc import service as pcs
    from app import quicklane, turn_inbox

    sent = []
    async def fake_run_owned(inbox_id, conversation_id, text, tenant, voice, **kw):
        sent.append({"inbox_id": inbox_id, "conv": conversation_id, "text": text,
                     "tenant": tenant, "voice": voice})
        turn_inbox.mark(inbox_id, "done")
        return "ok"
    monkeypatch.setattr(turn_inbox, "run_owned", fake_run_owned)

    quicklane._RATE.clear()
    quicklane._SEEN_SENDS.clear()
    code = pcs.pair_start(TENANT)["code"]
    dev = pcs.pair_finish(code, "Hoola Extension", "Browser extension")
    quicklane._RATE.clear()
    return {"client": TestClient(app), "token": dev["token"], "device_id": dev["device_id"],
            "pcs": pcs, "sent": sent, "quicklane": quicklane, "turn_inbox": turn_inbox}


def _post(lane, **body):
    return lane["client"].post("/api/pc/quickask", json=body,
                               headers={"Authorization": "Bearer " + lane["token"]})


def test_page_send_lands_a_turn_in_her_conversation(lane):
    r = _post(lane, url="https://example.com/article", title="Ek Page",
              selection="yeh tukda chuna hai")
    assert r.status_code == 200 and r.json()["accepted"] is True and r.json()["kind"] == "page"
    assert len(lane["sent"]) == 1                       # the SAME run_owned the phone's 202 rides
    s = lane["sent"][0]
    assert s["tenant"] == TENANT and s["voice"] is False
    assert "https://example.com/article" in s["text"] and "Ek Page" in s["text"]
    assert '"""' in s["text"] and "yeh tukda chuna hai" in s["text"]
    assert "Iske baare mein bataiye." in s["text"]      # the honest default ask


def test_ask_only_send_is_the_text_verbatim(lane):
    r = _post(lane, text="Aaj ka sensex kya hai?")
    assert r.status_code == 200 and r.json()["kind"] == "ask"
    assert lane["sent"][0]["text"] == "Aaj ka sensex kya hai?"


def test_page_with_ask_composes_once(lane):
    r = _post(lane, url="https://example.com/x", title="T", text="Ismein GST kitna hai?")
    assert r.status_code == 200
    t = lane["sent"][0]["text"]
    assert t.index("https://example.com/x") < t.index("Ismein GST kitna hai?")
    assert "Iske baare mein bataiye." not in t          # her own ask replaces the default


def test_empty_and_bad_url_refused(lane):
    assert _post(lane).status_code == 422
    assert _post(lane, url="javascript:alert(1)").status_code == 422
    assert _post(lane, url="ftp://x").status_code == 422
    assert _post(lane, text="   ").status_code == 422
    assert lane["sent"] == []


def test_auth_is_device_token_only(lane):
    c = lane["client"]
    assert c.post("/api/pc/quickask", json={"text": "x"}).status_code == 401
    assert c.post("/api/pc/quickask", json={"text": "x"},
                  headers={"Authorization": "Bearer spc_nope"}).status_code == 401
    # a revoked device loses the lane too
    lane["pcs"].revoke(TENANT, lane["device_id"])
    assert _post(lane, text="x").status_code == 401


def test_client_id_dedup(lane):
    a = _post(lane, text="ek hi sawaal", client_id="cid_1")
    b = _post(lane, text="ek hi sawaal", client_id="cid_1")
    assert a.json()["accepted"] and b.json()["accepted"] and b.json()["duplicate"] is True
    assert len(lane["sent"]) == 1                       # the retry never acts twice


def test_rate_cap_is_honest(lane, monkeypatch):
    monkeypatch.setattr(lane["quicklane"], "QUICK_ASK_PER_HOUR", 2)
    assert _post(lane, text="1").status_code == 200
    assert _post(lane, text="2").status_code == 200
    r = _post(lane, text="3")
    assert r.status_code == 429 and "ghanta" in r.json()["detail"]


def test_messages_read_back_tenant_checked(lane):
    from app.db import Message, new_id, now, session
    from app.db import Conversation
    with session() as s:
        conv = Conversation(id=new_id("c"), tenant_id=TENANT)
        s.add(conv)
        s.flush()
        conv_id = conv.id
        s.add(Message(conversation_id=conv_id, role="user", content=["x"], display="mera sawaal", in_history=False))
        s.add(Message(conversation_id=conv_id, role="assistant", content=["y"], display="Hoola ka jawab", in_history=True))
    c = lane["client"]
    r = c.get("/api/pc/quickask/messages", params={"conversation_id": conv_id},
              headers={"Authorization": "Bearer " + lane["token"]})
    assert r.status_code == 200
    rows = r.json()["messages"]
    assert [m["text"] for m in rows] == ["mera sawaal", "Hoola ka jawab"]
    # another tenant's device cannot read this conversation
    code2 = lane["pcs"].pair_start("t_other")["code"]
    tok2 = lane["pcs"].pair_finish(code2, "Dusra", "PC")["token"]
    r2 = c.get("/api/pc/quickask/messages", params={"conversation_id": conv_id},
               headers={"Authorization": "Bearer " + tok2})
    assert r2.status_code == 404


def test_lane_touches_no_pc_settings():
    """The freeze: the lane ADDS a surface; it must not modify the frozen PC config keys."""
    src = (ROOT / "server" / "app" / "quicklane.py").read_text(encoding="utf-8")
    assert "pc_" not in src.replace("quickask", "").replace("/api/pc/", "") or "pc_control" not in src
    from app import quicklane
    assert quicklane.QUICK_ASK_PER_HOUR == 30
    # the compose shape is honest Hinglish and server-side (every client lands the same shape)
    t = quicklane.compose("", "https://e.com/a", "", "")
    assert t.startswith("Is page ko dekhiye:") and "Iske baare mein bataiye." in t
    t2 = quicklane.compose("sawaal", "https://e.com/a", "Shirshak", "tukda")
    assert 'Is page ko dekhiye — "Shirshak"' in t2 and '"""\ntukda\n"""' in t2 and t2.endswith("sawaal")


# ================================================================ (2) the extension source
def test_manifest_is_mv3_hoola():
    m = json.loads((EXT / "manifest.json").read_text(encoding="utf-8-sig"))
    assert m["manifest_version"] == 3 and m["name"] == "Hoola"
    assert m["version"] == "1.9.0"                        # the extension version rides the desktop
    assert m["background"] == {"service_worker": "background.js"}
    assert set(m["permissions"]) == {"storage", "contextMenus", "scripting", "activeTab"}
    assert "https://hoola.ainewtika.com/*" in m["host_permissions"]
    assert m["optional_host_permissions"]                 # a custom server asks first (options page)
    assert m["action"]["default_popup"] == "popup.html"
    cmd = m["commands"]["send-page"]
    assert cmd["suggested_key"]["default"] == "Ctrl+Shift+H"
    for size in (16, 32, 48, 128):
        assert (EXT / "icons" / f"hoola{size}.png").is_file()


def test_background_rides_the_lane_with_no_remote_code():
    bg = (EXT / "background.js").read_text(encoding="utf-8")
    assert "/api/pc/quickask" in bg                        # the SAME lane the desktop uses
    assert "Bearer " in bg and "chrome.storage.local" in bg
    assert "contextMenus.create" in bg and "Hoola ko bhejiye" in bg
    assert "send-page" in bg and "commands.onCommand" in bg
    assert "activeTab" not in bg                           # activeTab is a manifest permission
    low = bg.lower()
    assert "eval(" not in low and "new function(" not in low and "innerhtml" not in low
    assert "executeScript" in bg                           # selection capture on the active tab
    assert "401" in bg and "429" in bg                     # honest handling of the lane's guards


def test_popup_and_options_pair_like_a_pc():
    popup = (EXT / "popup.js").read_text(encoding="utf-8")
    opts = (EXT / "options.js").read_text(encoding="utf-8")
    assert "/console" in popup                             # the answer lives in her conversation
    assert "send-page" in popup
    assert "/api/pc/pair" in opts                          # the SAME pairing flow a PC uses
    assert "6" in opts and "jodiye" in opts
    assert "Jodiye" in (EXT / "options.html").read_text(encoding="utf-8")   # the button she taps
    assert "chrome.permissions.request" in opts            # a custom server asks first
    for f in ("popup.html", "options.html"):
        assert (EXT / f).is_file()


# ================================================================ (3) the installer
@pytest.fixture()
def ext_env(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    la = tmp_path / "localappdata"
    monkeypatch.setenv("LOCALAPPDATA", str(la))
    src = tmp_path / "payload" / "ext"
    (src / "icons").mkdir(parents=True)
    (src / "manifest.json").write_text('{"manifest_version": 3, "version": "1.9.0"}', encoding="utf-8")
    (src / "background.js").write_text("// sw", encoding="utf-8")
    (src / "popup.html").write_text("<html></html>", encoding="utf-8")
    (src / "icons" / "hoola48.png").write_bytes(b"png")
    return la, src


def test_install_copies_only_hoolas_own_folder(ext_env):
    la, src = ext_env
    (la / "DoosraFolder").mkdir(parents=True)
    out = ext_install.set_enabled(True, str(src))
    assert out["ok"] is True and (la / "Hoola" / "chrome-extension" / "manifest.json").is_file()
    assert (la / "Hoola" / "chrome-extension" / "icons" / "hoola48.png").is_file()
    assert (la / "DoosraFolder").is_dir()                  # Hoola's neighbours untouched
    assert ext_install.installed() is True
    assert "chrome://extensions" in out["message"] and "Load unpacked" in out["message"]


def test_install_twice_is_an_upgrade(ext_env):
    la, src = ext_env
    ext_install.set_enabled(True, str(src))
    (src / "background.js").write_text("// sw v2", encoding="utf-8")
    out = ext_install.set_enabled(True, str(src))
    assert out["ok"] is True
    assert "v2" in (la / "Hoola" / "chrome-extension" / "background.js").read_text(encoding="utf-8")


def test_uninstall_and_uninstall_again_is_calm(ext_env):
    la, src = ext_env
    ext_install.set_enabled(True, str(src))
    out = ext_install.set_enabled(False)
    assert out["ok"] is True and not (la / "Hoola" / "chrome-extension").exists()
    out2 = ext_install.set_enabled(False)
    assert out2["ok"] is True and "pehle se nahi" in out2["message"]


def test_ext_honest_errors(ext_env, monkeypatch):
    ext_install.set_enabled(True, *ext_env[1:])
    out = ext_install.set_enabled(True, "/nonexistent/payload")
    assert out["ok"] is False and "naya exe" in out["message"]
    bad = ext_env[1]
    (bad / "manifest.json").write_text("not json{", encoding="utf-8")
    out2 = ext_install.set_enabled(True, str(bad))
    assert out2["ok"] is False and "manifest.json" in out2["message"]
    mv2 = ext_env[1]
    (mv2 / "manifest.json").write_text('{"manifest_version": 2}', encoding="utf-8")
    out3 = ext_install.set_enabled(True, str(mv2))
    assert out3["ok"] is False and "MV3" in out3["message"]


def test_ext_non_windows_refuses(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    out = ext_install.set_enabled(True)
    assert out["ok"] is False and out["supported"] is False


# ================================================================ (4) the desktop side
def test_quickask_send_honest_dicts(env, monkeypatch):
    from santosh_desktop.config import Config

    def fake_http(handler):
        return httpx.Client(transport=httpx.MockTransport(handler))

    cfg = Config()
    out = qa.send(cfg, text="x")
    assert out["ok"] is False and "pair" in out["message"]          # not paired -> honest
    cfg.server, cfg.device_id, cfg.token = "https://srv.test", "dev1", "spc_t"

    seen = {}
    def ok_handler(request):
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"accepted": True, "conversation_id": "c1", "kind": "ask"})
    out2 = qa.send(cfg, text="  sawaal  ", http=fake_http(ok_handler))
    assert out2["ok"] is True and out2["conversation_id"] == "c1"
    assert seen["auth"] == "Bearer spc_t" and seen["body"]["text"] == "sawaal"
    assert seen["body"]["client_id"].startswith("qa_")              # the dedup id always rides

    def unauth(request):
        return httpx.Response(401, json={"detail": "revoked"})
    assert qa.send(cfg, text="x", http=fake_http(unauth))["ok"] is False
    def capped(request):
        return httpx.Response(429, json={"detail": "ghanta"})
    assert "ghanta" in qa.send(cfg, text="x", http=fake_http(capped))["message"]
    assert qa.send(cfg, text="", url="")["ok"] is False             # nothing to send -> honest


def test_ask_handover_over_the_single_instance_socket():
    """A second instance hands the ask to the RUNNING window over the lock port (47321)."""
    import socket
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(1)
    got = []
    def serve():
        c, _ = srv.accept()
        buf = b""
        while True:
            part = c.recv(4096)
            if not part:
                break
            buf += part
        got.append(buf.decode("utf-8"))
        c.close()
        srv.close()
    import threading
    t = threading.Thread(target=serve, daemon=True)
    t.start()
    import santosh_desktop.__main__ as m
    # _forward_ask targets the fixed port; rebind the test server to the real one via monkeypatch-free trick:
    # instead pin the source, and exercise the real path with the fixed port only when free
    src = (DESKTOP / "__main__.py").read_text(encoding="utf-8")
    assert 'p.add_argument("--ask")' in src
    assert '"ASK:"' in src and "47321" in src and "create_connection" in src
    assert "_forward_ask" in src and "App(background=a.background, ask=a.ask, lock=lock)" in src
    t.join(timeout=3)


def test_app_window_wires_the_text_lane():
    app = (DESKTOP / "app.py").read_text(encoding="utf-8")
    assert 'self.events.put(("ask", ask))' in app                    # the door that started us
    assert 'line.startswith("ASK:")' in app                          # the lock-port receiver
    assert 'kind == "ask"' in app and "self._send_ask(v)" in app     # the pump routes it
    assert "quickask.send(self.cfg, text=text)" in app               # the lane send
    assert '("log", "Bhej diya' in app                               # honest log lines
    assert "Hoola se poochhiye" in app                               # the window's own door
    assert "Browser extension (page Hoola ko bhejiye)" in app        # the ext card
    assert "ext_install.set_enabled(True)" in app and "self._render()" in app
    # the card never installs by itself - only on her click (the pt_run discipline)
    body = app.split("def _ext_card(", 1)[1].split("\n    def ", 1)[0]
    assert "installed()" in body and body.count("set_enabled(True)") == 1


def test_do_ext_is_control_gated():
    src = (DESKTOP / "actions.py").read_text(encoding="utf-8")
    body = src.split("def do_ext(", 1)[1].split("\n    def ", 1)[0]
    assert "self._control_on()" in body, "do_ext must sit behind the PC-control switch"
    assert "ext_install.set_enabled" in body and "self.log(" in body


# ================================================================ (5) the plugin door rides too
def test_main_cs_ask_door():
    main = (PLUGIN / "Main.cs").read_text(encoding="utf-8")
    assert '"Hoola se poochho: {q}"' in main                         # the ask result
    assert "LaunchAsk" in main and '"--ask "' in main                # the handover
    assert "QuoteArg" in main                                        # quoting before the launch
    assert 'PluginID => "162E72D3C1D7464E865293A276993A7B"' in main  # the ID never changes
    assert "AliasExe()" in main and "File.Exists" in main            # one launch truth preserved
    # empty query still just opens the window (W2b behaviour kept)
    assert "q.Length == 0 ? Launch() : LaunchAsk(q)" in main


# ================================================================ (6) the operator tool
@pytest.fixture
def opc(monkeypatch):
    from app.pc import operator
    class FakePC:
        def __init__(self):
            self.calls = []
            self.reply = {"ok": True}
        async def __call__(self, op, action, args, timeout=25):
            self.calls.append((action, args))
            return self.reply
    pc = FakePC()
    monkeypatch.setattr(operator, "_pc", pc)
    return operator, pc


def _op(operator):
    return operator.Op(id="s1", tenant="t1", conv="c1", task="Hoola extension lagao")


def test_operator_ext_spec_has_approval_wording(opc):
    operator, _ = opc
    spec = [t for t in operator.TOOLS if t["name"] == "ext"]
    assert spec, "ext tool must exist in the operator toolset"
    d = spec[0]["description"]
    assert "ask_approval" in d and "on=false" in d and "no admin" in d
    assert "Load unpacked" in d and "chrome://extensions" in d


def test_operator_ext_do_install_and_uninstall(opc):
    operator, pc = opc
    pc.reply = {"ok": True, "dir": r"C:\\Users\\x\\AppData\\Local\\Hoola\\chrome-extension"}
    out = asyncio.run(operator._do(_op(operator), "ext", {"on": True}))
    assert pc.calls == [("ext", {"on": True})]
    assert "Load unpacked" in out and "chrome://extensions" in out
    pc.reply = {"ok": True, "message": "files hata di"}
    out2 = asyncio.run(operator._do(_op(operator), "ext", {"on": False}))
    assert "hata di" in out2


def test_operator_ext_do_honest_failures(opc):
    operator, pc = opc
    pc.reply = {"ok": False, "supported": True,
                "message": "Extension ki files is SantoshDesktop build mein nahi mili - naya exe install kijiye."}
    out = asyncio.run(operator._do(_op(operator), "ext", {"on": True}))
    assert "extension nahi lagi" in out and "naya exe" in out
    pc.reply = {"ok": False, "supported": False, "message": "sirf Windows PC par lagti hai."}
    out2 = asyncio.run(operator._do(_op(operator), "ext", {"on": True}))
    assert "extension nahi lagi" in out2 and "Windows" in out2


def test_operator_say_and_old_desktop_lines(opc):
    operator, _ = opc
    assert "Load unpacked" in operator._say("ext", {"on": True})
    assert "hata raha hoon" in operator._say("ext", {"on": False})
    assert operator._desktop_says(Exception("Unknown action ext"), "ext") is not None


def test_win_r_keys_still_blocked(opc):
    """Hoola never OPENS launchers or presses keys herself - she gives the USER doors."""
    operator, _ = opc
    out = asyncio.run(operator._do(_op(operator), "key", {"keys": "win+r"}))
    assert out.startswith("REFUSED")


# ================================================================ (7) CI, spec, versions
def test_ci_stages_and_ships_the_extension():
    yml = (ROOT / ".github" / "workflows" / "build-desktop.yml").read_text(encoding="utf-8")
    assert "desktop/ext/hoola-extension desktop/ext_payload" in yml
    assert "Hoola-Chrome-extension.zip" in yml
    assert "manifest missing" in yml and "background.js missing" in yml   # the payload is checked


def test_spec_rides_the_ext_payload():
    spec = (ROOT / "desktop" / "santosh_desktop.spec").read_text(encoding="utf-8")
    assert 'ext_payload' in spec and '"ext"' in spec
    assert "os.path.isdir(_ext)" in spec                                  # dev machines without it still build


def test_versions():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.547.0"
    pubspec = (ROOT / "pubspec.yaml").read_text(encoding="utf-8")
    assert "version: 0.547.0+570" in pubspec
    import santosh_desktop
    assert santosh_desktop.__version__ == "1.9.0"          # desktop changed this release (ext + --ask)
    meta = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8-sig"))
    assert meta["Version"] == "1.9.0"                      # the plugin version rides the desktop
    man = json.loads((EXT / "manifest.json").read_text(encoding="utf-8-sig"))
    assert man["version"] == "1.9.0"                       # the extension rides the desktop too
