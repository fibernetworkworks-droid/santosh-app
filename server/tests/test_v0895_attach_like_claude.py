"""v0.895 ATTACH LIKE CLAUDE: one message carries up to 20 files of up to 30 MB each (Claude's limits; it was 6 and
25 MB), any kind (an APK too), the Add sheet's Research switch reaches the brain beside her words (her bubble stays
her words), and the upload errors speak English."""
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def test_twenty_files_any_kind_and_research(env, monkeypatch):
    from app import chatfiles, main, turn_inbox
    assert chatfiles.MAX_BYTES == 30 * 1024 * 1024 and chatfiles.MAX_FILES == 20
    seen = {}
    real_accept = turn_inbox.accept

    def accept(tenant, conv, text, voice, context="", client_id="", *a, **k):   # every message passes the inbox
        seen["text"], seen["context"] = text, context
        return real_accept(tenant, conv, text, voice, context, client_id, *a, **k)

    async def no_run(*a, **k):
        return None
    monkeypatch.setattr(turn_inbox, "accept", accept)
    monkeypatch.setattr(turn_inbox, "run_owned", no_run)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        apk = c.post(f"/api/conversations/{conv}/files",
                     files={"file": ("hoola.apk", b"PK\x03\x04" + b"\x00" * 200, "application/vnd.android.package-archive")})
        assert apk.status_code == 200, apk.text
        ids = [apk.json()["file_id"]]
        for i in range(19):
            r = c.post(f"/api/conversations/{conv}/files", files={"file": (f"note{i}.txt", f"line {i}".encode(), "text/plain")})
            ids.append(r.json()["file_id"])
        r = c.post(f"/api/conversations/{conv}/messages", json={"text": "Check these", "files": ids, "research": True})
        assert r.status_code == 202, r.text
        too_many = c.post(f"/api/conversations/{conv}/messages", json={"text": "x", "files": ids + ids[:1]})
        assert too_many.status_code == 422
        empty = c.post(f"/api/conversations/{conv}/files", files={"file": ("e.txt", b"", "text/plain")})
        assert empty.status_code == 400 and "empty" in empty.text
    assert seen["text"] == "Check these"                 # her words stay hers
    ctx = seen["context"]
    assert all(i in ctx for i in ids)                     # all 20 reach the brain (was 6)
    assert main.RESEARCH_NOTE in ctx and "cite each one" in ctx


def test_phone_and_console_carry_the_new_limits():
    shell = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
    assert "showHoolaAddSheet" in shell and "pickMultipleMedia" in shell and "ImageSource.camera" in shell
    assert "research: _research" in shell and "HoolaAttachTray(" in shell
    attach = (ROOT / "lib/ui/chat/hoola_attach.dart").read_text()
    assert "hoolaMaxFiles = 20" in attach and "hoolaMaxBytes = 30 * 1024 * 1024" in attach
    for row in ("'Camera'", "'Photos'", "'Files'", "'Research'", "'Connectors'", "'Your computers'", "'AI team'", "'Memory'"):
        assert row in attach, row
    chat = (ROOT / "lib/ui/chat/hoola_chat.dart").read_text()
    assert "HoolaSentFiles(files: files, app: app)" in chat
    api = (ROOT / "lib/api.dart").read_text()
    assert "if (research) 'research': true" in api and "Future<Map<String, dynamic>> memorySettings()" in api
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "Up to 20 files in one message." in js and "30 * 1024 * 1024" in js
