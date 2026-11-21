"""v0.968 HOOLA CODE NO STARS - her screen recording (16 Nov): while a reply landed, a bold run across words showed
raw ("**15s polling** while visible") until it settled. A word that opened or closed a mark was drawn as plain text.
Now the marks open at each word are put back in front of it and closed after it, so every word lands in its style;
a code chip across words stays one chip. The pure logic is mirrored here and checked."""
import re
from pathlib import Path

MD = (Path(__file__).resolve().parents[2] / "lib/ui/chat/hoola_md.dart").read_text(encoding="utf-8")


def _after(s, op):
    st, i = list(op), 0
    while i < len(s):
        if st and st[-1] == "`":
            if s[i] == "`":
                st.pop()
            i += 1
            continue
        if s[i] == "`":
            st.append("`")
            i += 1
            continue
        for mk in ("**", "~~"):
            if s.startswith(mk, i):
                if mk in st:
                    del st[len(st) - 1 - st[::-1].index(mk)]
                else:
                    st.append(mk)
                i += 2
                break
        else:
            i += 1
    return st


def _bal(t, before):
    return "".join(before) + t + "".join(reversed(_after(t, before)))


def test_bold_across_words_never_raw():
    words = [w.rstrip() for w in re.findall(r"\S+\s*", "**15s polling** while ~~old text~~ done")]
    op, out = [], []
    for w in words:
        out.append(_bal(w, op))
        op = _after(w, op)
    assert out == ["**15s**", "**polling**", "while", "~~old~~", "~~text~~", "done"]
    assert op == []


def test_dart_balances_each_word():
    assert "static List<String> marksAfter(String s, List<String> open)" in MD
    assert "static String balanced(String text, List<String> before)" in MD
    assert "mdInline(balanced(core, open)" in MD
    assert "mdInline(balanced(head, const [])" in MD
    # the old raw path is gone
    assert "? [TextSpan(text: w)]" not in MD


def test_code_chip_and_italic_guards():
    assert "marksAfter(w.trimRight(), open).contains('`')" in MD   # code across words = one unit
    assert "if (open.contains('`')) return whole();" in MD
    assert "if (s.replaceAll('**', '').contains('*')) return whole();" in MD


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.79")
