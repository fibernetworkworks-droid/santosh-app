"""v0.282 ATTACHMENTS LIKE CLAUDE ON THE PHONE: tiles in the typing box with an upload bar, tiles above her sent
bubble, a full-screen viewer. Flutter is not in the sandbox, so the wiring is pinned here and CI analyze checks the Dart."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "lib"


def test_module_parts():
    d = (LIB / "ui" / "chat_attach.dart").read_text()
    for part in ("class TrayFile", "class AttachTray", "class SentFiles", "void openAttachment(", "class AttachViewer",
                 "InteractiveViewer", "VideoPlayerController.networkUrl", "const fileOnlyText = 'Ye file dekho'",
                 "bool filesOnlyText(", "LinearProgressIndicator"):
        assert part in d, part


def test_flutter_324_safe():
    d = (LIB / "ui" / "chat_attach.dart").read_text()
    assert "withValues(" not in d and "FontFeature" not in d     # CI builds on Flutter 3.24.5


def test_chat_screen_uses_tiles():
    s = (LIB / "ui" / "chat_screen.dart").read_text()
    assert "import 'chat_attach.dart';" in s
    assert "final List<TrayFile> _files = [];" in s and "AttachTray(" in s and "SentFiles(files:" in s
    assert "t = fileOnlyText;" in s and "_uploading" not in s
    assert "if (_files.any((f) => f.uploading))" in s


def test_upload_reports_progress():
    a = (LIB / "api.dart").read_text()
    assert "static Stream<List<int>> _pieces(" in a and "onProgress: onProgress" in a
    st = (LIB / "state.dart").read_text()
    assert "attachChatFile(String name, List<int> bytes, {void Function(double)? onProgress})" in st
