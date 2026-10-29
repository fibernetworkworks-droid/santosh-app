"""v0.222 CONSOLE R2 - new sidebar + home. The sidebar is Claude-style (New chat with its shortcut, Search, the places,
sessions + recents, an AI spend card, the user card); the home is the ringed avatar, the greeting with her name in the
brand gradient, the composer with one-message chips (Deep research / Hoola PC) and Call, action pills, and an
"In progress" row of her live jobs from /api/kaam."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "server" / "app" / "static" / "console"


def _read(name: str) -> str:
    return (CONSOLE / name).read_text()


def test_sidebar_markup():
    html = _read("v2.html")
    assert 'data-v="chat"' in html and 'class="mk"' in html            # the brand mark is home (Chat)
    assert "Ctrl ⇧ O" in html and 'id="newChat"' in html
    assert 'id="spend"' in html and 'id="spAmt"' in html and 'class="spbar"' in html
    assert 'id="uini"' in html
    js = _read("v2.js")
    nav = re.search(r"const NAV = (\[.*?\]);", js).group(1)
    for label in ("'Create'", "'Today'", "'Tools'", "'Voice call'"):
        assert label in nav, label
    assert "'chat'" not in nav and "'main'" not in nav                  # chat = brand mark, account = user card
    assert "NAV.splice(1, 0, ['bana', 'Library'])" in js
    assert "Pinned" in _read("chatlist.js") and "Pin kiye hue" not in _read("chatlist.js")


def test_home_markup():
    html = _read("v2.html")
    for needle in ('class="ring"', 'id="pcPill"', 'class="pills"', 'data-create="image"', 'data-create="video"',
                   'data-create="research"', 'data-create="document"', 'data-fill=', 'data-v="kaam"',
                   'id="liveJobs"', 'id="jobGrid"', 'id="qDeep"', 'id="qPc"', 'id="callBtn"'):
        assert needle in html, needle
    assert 'id="cats"' not in html and 'id="sugs"' not in html          # ideas live in the Tools view now
    js = _read("v2.js")
    assert "workflow-entry" not in js
    assert 'class="gname"' in js and "esc(first)" in js                 # her name is escaped before it lands in HTML


def test_hints_ride_the_message_but_never_the_bubble():
    js = _read("v2.js")
    assert "hints: takeHints()" in js
    assert "[Web console " in js and "delete body.hints" in js
    assert js.count("p.text = stripHints(p.text)") == 2                 # live echo + history both strip them
    # the place hint is one where.py understands as Hoola's own cloud computer
    from app.agent import where
    hint = re.search(r"h\.push\('(place: [^']+)'\)", js).group(1)
    assert where.place(hint) == "hoolapc"


def test_live_jobs_open_their_chat():
    from app import kaamwatch
    from app.kaamwatch import KaamJob
    row = KaamJob(tenant_id="t", conversation_id="conv-9", key="k", kind="site_board", label="Website",
                  title="Sharma Dental", state="working", status="", pct=40, detail="{}")
    assert kaamwatch._row_view(row)["conversation_id"] == "conv-9"
    js = _read("v2.js")
    assert "/api/kaam" in js and "j.state === 'working' || j.state === 'waiting'" in js
    assert "openConv(b.dataset.job)" in js


def test_styles_live_in_the_one_stylesheet():
    css = _read("v2.css")
    tail = css[css.index("v0.222 R2: new sidebar + home"):]
    for rule in ("#app .spend{", "#app .halo .ring{", "#app .gname{", "#app .pill{", "#app .job{", "#app .qc{",
                 "justify-content:safe center"):
        assert rule in tail, rule
    assert "@media(prefers-reduced-motion:reduce){#app .halo .ring" in tail
    assert "var(--sidew)" not in css                                    # the resizable --sidebar-width stays in charge
    assert css.count("{") == css.count("}")


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.247.0"
    assert "0.247.0+287" in (ROOT / "pubspec.yaml").read_text()
