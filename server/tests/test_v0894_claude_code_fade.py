"""v0.894 CLAUDE KA CODE + FADE: a `term` in a reply looks like Claude's (claude.ai .ReactMarkdown code - 0.9 of the
text, muted red --danger-000, a 5 % ink tint, a hairline border, 1px 4px room) instead of a blue chip that read as a
link, and the reply fades into the page where it meets the composer instead of being cut through a line."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def test_console_term_and_fade():
    css = (CON / "v2.css").read_text()
    blk = css[css.index("v0.894 CLAUDE KA CODE + FADE"):]
    assert "--codeterm:hsl(0 58.6% 34.1%)" in blk and "--codeterm:hsl(0 98.4% 75.1%)" in blk
    rule = blk[blk.index("#app .mh .txt code:not(pre code)"):]
    rule = rule[:rule.index("}")]
    for part in ("color:var(--codeterm)", "font-size:.9em", "padding:1px 4px", "border-radius:.3rem", ".05)"):
        assert part in rule, part
    assert "#composer::before" in blk and "linear-gradient(to top,var(--chat-paper),transparent)" in blk
    assert "pointer-events:none" in blk[blk.index("#composer::before"):]


def test_phone_term_and_fade():
    theme = (ROOT / "lib/ui/hoola_theme.dart").read_text()
    assert "codeTerm: Color(0xFF8A2424)" in theme and "codeTerm: Color(0xFFFE8181)" in theme
    assert "(codeTerm, bg, 'codeTerm/bg')" in theme       # held to 4.5:1 by the palette test
    md = (ROOT / "lib/ui/chat/hoola_md.dart").read_text()
    assert "color: c.codeTerm" in md and "size: compact ? 12.5 : 13.5" in md
    inline = (ROOT / "lib/ui/md_text.dart").read_text()
    assert "InlineSpan _codeSpan(" in inline and "codeStyle != null" in inline   # room only in the new chat
    chat = (ROOT / "lib/ui/chat/hoola_chat.dart").read_text()
    assert "class _Fade extends StatelessWidget" in chat
    assert "bottom: 0, height: 32" in chat and "top: 0, height: 14" in chat
    assert "IgnorePointer(child: _Fade(" in chat
