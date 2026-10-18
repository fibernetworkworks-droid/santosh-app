"""Drive/Sheets/Docs tools against fake Google API services."""
import asyncio

import pytest

from app import gdrive
from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_life import conv_ctx


class Exec:
    def __init__(self, result):
        self._r = result
    def execute(self):
        return self._r


class FakeFiles:
    def __init__(self, store):
        self.store = store
    def list(self, **k):
        self.store["list_q"] = k.get("q")
        return Exec({"files": [
            {"id": "f1", "name": "Leads Oct", "mimeType": "application/vnd.google-apps.spreadsheet", "modifiedTime": "2026-10-18T05:00:00Z", "webViewLink": "https://docs.google.com/s/f1"},
            {"id": "f2", "name": "Proposal", "mimeType": "application/vnd.google-apps.document", "modifiedTime": "2026-10-17T05:00:00Z", "webViewLink": "https://docs.google.com/d/f2"},
        ]})
    def get(self, fileId=None, fields=None, supportsAllDrives=None):
        meta = {"f2": {"id": "f2", "name": "Proposal", "mimeType": "application/vnd.google-apps.document", "webViewLink": "https://docs.google.com/d/f2", "parents": ["old"]}}
        return Exec(meta.get(fileId, {"id": fileId, "name": "x", "mimeType": "text/plain", "webViewLink": "l", "parents": []}))
    def export_media(self, fileId=None, mimeType=None):
        return ("export", fileId)
    def get_media(self, fileId=None, supportsAllDrives=None):
        return ("media", fileId)
    def update(self, **k):
        self.store["moved"] = k
        return Exec({})


class FakeValues:
    def __init__(self, store):
        self.store = store
    def get(self, spreadsheetId=None, range=None, valueRenderOption=None):
        return Exec({"range": range or "Sheet1!A1:Z200", "values": [["Name", "Phone"], ["Ramesh", "98900"], ["Sita", "98901"]]})
    def append(self, spreadsheetId=None, range=None, valueInputOption=None, insertDataOption=None, body=None):
        self.store["appended"] = body
        return Exec({"updates": {"updatedRows": len(body["values"]), "updatedRange": "Sheet1!A4"}})


def fake_svc(store):
    def build(name, version):
        if name == "drive":
            return type("D", (), {"files": lambda self: FakeFiles(store)})()
        if name == "sheets":
            return type("S", (), {"spreadsheets": lambda self: type("SS", (), {"values": lambda s2: FakeValues(store)})()})()
        if name == "docs":
            class Docs:
                def documents(self):
                    return type("DD", (), {
                        "create": lambda s, body=None: Exec({"documentId": "newdoc"}),
                        "batchUpdate": lambda s, documentId=None, body=None: Exec({}) or store.update({"doc_text": body})})()
            return Docs()
    return build


@pytest.fixture
def g(monkeypatch):
    store = {}
    monkeypatch.setattr(gdrive, "configured", lambda tenant_id=None: True)
    monkeypatch.setattr(gdrive, "_svc", lambda name, version, tenant_id=None: fake_svc(store)(name, version))
    monkeypatch.setattr(gdrive, "_folder", lambda: "FOLDER1")

    class FakeDL:
        def __init__(self, buf, req): self.buf = buf; self.n = 0
        def next_chunk(self):
            if self.n == 0:
                self.buf.write(b"Proposal body text for FNW."); self.n = 1
                return (None, False)
            return (None, True)
    import app.gdrive as gd
    monkeypatch.setattr("googleapiclient.http.MediaIoBaseDownload", FakeDL, raising=False)
    # patch the symbol used inside _read_file
    import sys, types
    http_mod = types.ModuleType("googleapiclient.http"); http_mod.MediaIoBaseDownload = FakeDL
    sys.modules["googleapiclient.http"] = http_mod
    return store


def test_find_scopes_to_folder(g):
    ctx = conv_ctx()
    out = asyncio.run(dispatch("drive_find", {"query": "Leads"}, ctx))
    assert out["count"] == 2 and out["files"][0]["type"] == "Google Sheet"
    assert "FOLDER1" in g["list_q"] and "name contains 'Leads'" in g["list_q"]


def test_read_google_doc_text(g):
    ctx = conv_ctx()
    out = asyncio.run(dispatch("drive_read_file", {"file_id": "f2"}, ctx))
    assert out["type"] == "text" and "Proposal body text" in out["text"]


def test_sheet_read_and_append(g):
    ctx = conv_ctx()
    r = asyncio.run(dispatch("sheet_read", {"spreadsheet_id": "f1"}, ctx))
    assert r["header"] == ["Name", "Phone"] and r["row_count"] == 3
    a = asyncio.run(dispatch("sheet_append", {"spreadsheet_id": "f1", "values": ["Mohan", "98902"]}, ctx))
    assert a["added_rows"] == 1 and g["appended"]["values"] == [["Mohan", "98902"]]


def test_doc_create_moves_to_folder(g):
    ctx = conv_ctx()
    out = asyncio.run(dispatch("doc_create", {"title": "FNW Plan", "content": "Hello"}, ctx))
    assert out["id"] == "newdoc" and out["link"] == "l"
    assert g["moved"]["addParents"] == "FOLDER1"


def test_not_configured(monkeypatch):
    monkeypatch.setattr(gdrive, "configured", lambda tenant_id=None: False)
    with pytest.raises(ToolError, match="connect nahi"):
        asyncio.run(dispatch("drive_find", {}, Ctx("default", "c")))
