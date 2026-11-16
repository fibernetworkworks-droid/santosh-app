"""v0.960 HOOLA CODE GLIDE (built as 0.958; their v0.960 + v0.959 took the numbers, both kept) (owner, after v0.957: "STILL NEED LOT OF WORK --- NEED MORE SMOOTH LANDING OF TEXT --- FIND
THE FLAW"). The flaws found in how a reply lands on the phone:
(1) the fade of the newest words moved only when the NEXT word landed (four fixed shades, ~11 changes a second), so each
    word stepped darker instead of rising;
(2) the fade switched OFF for the whole tail whenever a `code name`, a bracket or a bold mark was among the newest four
    words - in Hoola Code that is most lines, so words popped in at full ink half the time;
(3) each wrapped line pushed everything under it (the working row) down a whole line in one frame;
(4) when the words being written became a saved message the landing widget was rebuilt from scratch (its key changed):
    the newest words flashed to full ink and the size reset.
Phone code (Dart, compiled on CI): these pins hold each fix in the source."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORDS = (ROOT / "lib/ui/code/code_words.dart").read_text()
SESSION = (ROOT / "lib/ui/code/code_session.dart").read_text()
MD = (ROOT / "lib/ui/chat/hoola_md.dart").read_text()


def test_fade_is_timed_per_word_every_frame():
    land = WORDS[WORDS.index("class _CodeLandingState"):WORDS.index("/// v0.935 the working row's words")]
    assert "final Map<int, double> _born" in land and "_born[k] = now;" in land
    assert "static const fadeMs = 280.0;" in WORDS and "static List<double> tailInk(" in WORDS
    # setState every frame while words land or still rise, not only when a word count changes
    assert land.count("setState(() {});") >= 2 and "_fading" in land


def test_marks_near_the_end_no_longer_switch_the_fade_off():
    assert "List<InlineSpan> _inkTail(" in MD and "if (fade && ink != null) return _inkTail(s, ink, c, code);" in MD
    tail = MD[MD.index("List<InlineSpan> _inkTail("):]
    assert "mdInline(w, streaming: true" in tail                      # a word with its own marks still rises
    assert "codeStyle: st" in tail and "withOpacity" in tail           # inline code fades with it


def test_lines_grow_in_and_the_widget_carries_on():
    land = SESSION[SESSION.index("Widget _land("):SESSION.index("final Map<String, String> _keyOf")]
    assert "AnimatedSize(" in land and "tail: tail," in land
    assert "key: ValueKey('land${_keyOf[i] ?? i}')" in land
    assert "_keyOf[key] = _keyOf.remove('live') ?? 'live';" in SESSION   # v0.964 the message carrying the words
    assert "_keyOf['live'] = 'live${++_liveSeq}';" in SESSION


def test_reply_passes_the_ink_through():
    assert "this.tail});" in WORDS and "fade: true, tail: tail" in WORDS
    assert "final Widget Function(String shown, bool streaming, List<double> tail) builder;" in WORDS
