"""v0.286 EK HI DOM - a live reply and a reloaded one are the same page (owner sent a screenshot of a live reply
whose four paragraphs were fused into one wall: "CHECK NO PARAGRAPH IN CHAT SPACE IN HOOLA").

The console had TWO rendering paths, and only the one she never looks at was correct.

    HoolaMD.Live     a reply while it ARRIVES      wrapped every block in <div class="mdb">
    HoolaMD.render   a reply after a RELOAD        no wrapper

That wrapper broke the chat's whole measured layout, because two rules depend on a block being a direct child of
the message:

    .textmd p:last-child{margin-bottom:0}      v0.274, to trim dead space under the LAST block of a reply.
                                               A <p> alone in a wrapper IS a :last-child -> EVERY paragraph gap 0.
    #app .mh .txt>p{max-width:680px}           v0.276, the reading width. A CHILD rule, so a wrapped <p> stopped
                                               matching -> the full 880px column, about 118 characters a line.

Measured in a real browser, before:

                        gap between paragraphs      prose width
    live path                    0px                   880px        <- what she reads
    reload path                 16px                   680px        <- what every probe measured

So v0.274 / v0.276 / v0.278 / v0.281 / v0.284 were all real and all correct, and all invisible to her, because
every probe page went through render(). After: both paths 16px at 680px, and feeding the text one character at a
time leaves markup byte-identical to render() with 0 wrappers.

THE LESSON, now twice over: test the path the USER takes. v0.284 found the probes were using text no model emits;
v0.286 found them using a renderer she never sees.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def _md() -> str:
    return (CON / "md.js").read_text()


def _code() -> str:
    """md.js with its comments stripped - the version's own comment names the markup it removed, so an assertion
    about what the CODE does must not be able to pass on the prose that explains it."""
    import re
    js = _md()
    js = re.sub(r"/\*[\s\S]*?\*/", "", js)
    return "\n".join(re.sub(r"(^|\s)//.*$", "", ln) for ln in js.splitlines())


def test_the_live_path_no_longer_wraps_a_block():
    code = _code()
    assert "mdb" not in code                                   # nothing creates the wrapper any more
    assert "function nodesOf(html)" in code
    assert "this.el.appendChild(n)" in code


def test_the_streaming_block_is_tracked_by_its_nodes():
    js = _code()
    assert "this.tailNodes = []" in js
    assert "for (const n of this.tailNodes) n.remove();" in js
    assert "this.done.push({src: bs[i], nodes});" in js
    assert "for (const d of this.done.splice(i)) for (const n of d.nodes) n.remove();" in js
    assert "this.tail " not in js and "this.tail;" not in js and "this.tail)" not in js   # the old single wrapper is gone


def test_the_two_rules_the_wrapper_broke_are_the_ones_left_in_place():
    """They were right all along - this version stopped the DOM from hiding them, it did not change them."""
    css = (CON / "v2.css").read_text()
    assert ".textmd p:last-child{margin-bottom:0}" in css                     # v0.274
    assert "#app .mh .txt>p,#app .mh .txt>ul,#app .mh .txt>ol," in css        # v0.276, still a child rule
    assert ".textmd p{margin:0 0 16px}" in css
    assert "max-width:680px" in css


def test_the_dead_wrapper_styles_went_with_it():
    css = (CON / "v2.css").read_text()
    assert ".mdb{min-width:0}" not in css and ".mdb.tail" not in css


def test_v0284_and_v0283_are_untouched():
    js = _md()
    assert "a single newline inside a paragraph is a SOFT break" in js        # v0.284
    assert "hard ? '<br>' : ' '" in js
    css = (CON / "v2.css").read_text()
    assert ".textmd h3.mdh{font-size:22px}" in css
    assert "#app .textmd .mdh{font-family:var(--fr);letter-spacing:normal}" in css
    stream = (CON / "stream.js").read_text()                                   # v0.283
    assert "Math.min(2, Math.floor(this.queue.length / 80))" in stream


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.338.0"
    assert "0.338.0+378" in (ROOT / "pubspec.yaml").read_text()
