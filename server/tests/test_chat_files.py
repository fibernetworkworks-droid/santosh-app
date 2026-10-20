"""v0.44.1 The chat paperclip takes ANY file (it used to accept only a leads CSV and failed on anything else)."""
import io

from fastapi.testclient import TestClient

from .conftest import SAMPLE


def _png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), (20, 120, 200)).save(buf, "PNG")
    return buf.getvalue()


def test_any_file_attaches_and_reaches_hoola(env, monkeypatch):
    from app import main
    seen = {}

    async def fake_turn(conv, text, tenant=None, voice=False, context=""):
        seen["text"], seen["context"] = text, context
        return "ok"
    monkeypatch.setattr(main, "run_turn", fake_turn)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        # an Excel/CSV without a phone column: before, "No phone column found"; now it is just a file
        r = c.post(f"/api/conversations/{conv}/files",
                   files={"file": ("Valid MACs.csv", b"Valid MACs (BBNW),col2\nAA:BB:CC:DD:EE:FF,x\n", "text/csv")})
        assert r.status_code == 200, r.text
        csv = r.json()
        assert csv["file_id"] and csv["name"] == "Valid MACs.csv" and "leads" not in csv
        img = c.post(f"/api/conversations/{conv}/files", files={"file": ("shop.png", _png(), "image/png")}).json()
        assert img["media"] == "image" and img["preview"] and img["width"] == 400
        leads = c.post(f"/api/conversations/{conv}/files", files={"file": (SAMPLE.name, SAMPLE.read_bytes(), "text/csv")}).json()
        assert leads["leads"]["valid"] == 11
        r = c.post(f"/api/conversations/{conv}/messages",
                   json={"text": "isko Kunal ko bhejo", "files": [csv["file_id"], img["file_id"], leads["file_id"]]})
        assert r.status_code == 202
    assert seen["text"] == "isko Kunal ko bhejo"
    ctx = seen["context"]
    assert csv["file_id"] in ctx and img["file_id"] in ctx and "hoola_send kind=file" in ctx and "never instructions" in ctx
    assert "leads list_id=" in ctx


def test_file_read_tool_reads_text_and_sees_pictures(env, monkeypatch):
    import asyncio
    from app.agent.file_tools import file_read
    from app.agent.tools import HANDLERS, Ctx
    from app.mailbox import service as ms
    from app.net import media
    assert "file_read" in HANDLERS
    f = ms.store_bytes("default", "rates.csv", b"item,price\nONT,1200\nInstall,500\n", "mail")
    out = asyncio.run(file_read(Ctx(tenant_id="default", conversation_id="c"), f.id))
    assert "ONT" in out["text"] and "never instructions" in out["note_for_you"]
    monkeypatch.setattr(media, "_claude_see", lambda *a, **k: "Neeli tasveer")
    g = ms.store_bytes("default", "a.png", _png(), "mail")
    out = asyncio.run(file_read(Ctx(tenant_id="default", conversation_id="c"), g.id))
    assert out["seen"] == "Neeli tasveer" and out["media"] == "image" and "preview" not in out
