"""v0.928 HOOLA CODE CHAT LIKE HOOLA CHAT (owner: "Make all chat feature same as hoola chat... App... Everything"): Hoola
Code's words use the Hoola chat's renderer, the newest reply has Copy / Read aloud / Share, every message has the same
long-press sheet, her whole message shows, and a Newest arrow brings her back to the end."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "lib/ui/code"
W = (CODE / "code_words.dart").read_text()
S = (CODE / "code_session.dart").read_text()


def test_the_words_render_like_a_chat_reply():
    assert "HoolaMd(text, streaming: streaming, selectable: selecting, sans: true, fade: true)" in W                 # headings, lists, tables, code blocks with Copy
    assert "final actions = si == lastSay && !running;" in S and ": _reply(text, 'say$sn', actions: actions));" in S   # v0.935 a new one lands first
    assert ": _reply(ex, 'explain', actions: true));" in S   # v0.937 a new closing answer lands first
    assert "HoolaMd(cs(t['question']))" in S
    assert "style: HoolaType.reply(c))" not in S                       # no plain-text reply left


def test_actions_and_long_press_like_the_chat():
    for s in ("'Copy'", "'Read aloud'", "'Share'", "app.readAloud(plain)", "Native.shareFile"):
        assert s in W, s
    for s in ("'Quote in my reply'", "'Edit and send again'", "'Select text'"):
        assert s in W, s
    assert "onLongPress: () => _herMenu(text, key)" in S and "SelectableText(text" in S
    assert "CodeChip('Done selecting'" in S
    assert "maxLines: small ? 6 : 16" not in S                         # her whole message, like the chat


def test_newest_arrow_and_follow():
    assert "class CodeNewestButton" in W and "CodeNewestButton(onTap: () => _toEnd())" in S
    assert "if (n != _seen && (first || !_away)) _toEnd(animate: !first);" in S


def test_design_rules():
    for src in (W, S):
        assert "Color(0x" not in src and "BackdropFilter" not in src
        assert not re.search(r"FontWeight\.w(800|900)", src)


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.978.0"' in main
    assert "version: 0.978.0+977" in (ROOT / "pubspec.yaml").read_text()
