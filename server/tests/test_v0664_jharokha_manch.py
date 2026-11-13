"""v0.670.0 JHAROKHA MANCH - the T3 local-browser family, backend-only (built as 0.664.0 - their ASLI SAMAY took 0.664.0 while JHAROKHA sat built - REBASE PROTOCOL #12, both kept; owner: "T3 Local Browser ---
CONTINUE"; the T3 tier of download/HOOLA_MCP_FEED.json - the zero-login / zero-key browser rows,
catalog-description-verified and ported IDEA-ONLY: microsoft/playwright-mcp "browser automation ...
through structured accessibility snapshots" + the modelcontextprotocol/servers Puppeteer reference
"Browser automation and web scraping"; zero upstream code, zero new pip - the browser is the
house's own playwright + chromium stack, zero new keys).

ONE tool `jharokha`, actions open | snapshot | click | type | press | console | tabs | screenshot |
close, every answer one envelope. What is tested FOR REAL - a real headless Chromium, all pages are
data:text/html scratch pages so the whole suite is offline (zero network):

the open + snapshot shape (tree with refs, visible text, honest title/url), a click through a ref
that really changes the page (and the auto-snapshot that rides the answer), the stale-ref law
(unknown ref, and a ref from page A after opening page B = NOT_FOUND with the fresh-snapshot hint),
type into a textbox with value echoed back + submit pressing Enter through a form's onsubmit,
type on a click-target refused, the press allowlist (named keys pass, chords and F-keys refused),
the console tail (page log + uncaught pageerror captured, clear=true empties), the tabs lifecycle
(list / new / select / close, the last tab closing the browser, the 4-tab RAM cap honest), the
screenshot landing in data/jharokha/<tenant>/ with real bytes, the SSRF / scheme guard (loopback,
link-local metadata, file://, ftp://, non-html data:, an over-cap data: page, an empty url), the
no-page honesty (every action on a fresh tenant is NOT_FOUND, close says nothing was open), the
kill switch (off means off - every action NEED_SETUP), the idle reaper (a stale browser is closed
and the next open relaunches clean), the global browser cap (a second tenant is an honest BUSY),
tenant isolation (one tenant's browser is invisible to another), the envelope shape, the walk cap
(250 refs max on a 300-button page), registry 607 pin, the enum pin, APP_VERSION pin.
"""
import asyncio
import shutil
from pathlib import Path

import pytest

from app.agent import jharokha_tools as J
from app.agent.tools import Ctx, TOOLS

CTX = Ctx(tenant_id="jh-test-tenant", conversation_id="c1")
CTX2 = Ctx(tenant_id="jh-other-tenant", conversation_id="c2")

SHOP = ("data:text/html,<html><head><title>jh shop</title></head><body>"
        "<h1>jh todos</h1>"
        "<input placeholder='What needs to be done?'>"
        "<button onclick=\"document.getElementById('o').textContent='clicked'\">Add</button>"
        "<a href='about:blank'>next page</a>"
        "<select aria-label='Colour' onchange=\"document.getElementById('o').textContent='pick '+this.value\">"
        "<option value='red'>red</option><option value='blue'>blue</option></select>"
        "<input type='checkbox' aria-label='Urgent'>"
        "<output id='o'>idle</output>"
        "</body></html>")

FORM = ("data:text/html,<html><head><title>jh form</title></head><body>"
        "<form onsubmit=\"document.getElementById('o').textContent='sent '+document.getElementById('t').value;return false\">"
        "<input id='t' placeholder='Name here'>"
        "<button type='submit'>Send</button></form>"
        "<output id='o'>waiting</output>"
        "</body></html>")

NOISY = ("data:text/html,<html><head><title>jh noisy</title></head><body>"
        "<button onclick=\"console.log('jh-log-marker')\">Speak</button>"
        "<button onclick=\"throw new Error('jh-boom')\">Break</button>"
        "</body></html>")

TALL = "data:text/html,<html><body><h1>jh tall</h1>" + ("<p>row</p>" * 500) + "</body></html>"

WIDE = "data:text/html,<html><body>" + "".join(f"<button>b{i}</button>" for i in range(300)) + "</body></html>"


def jh(action="snapshot", ctx=None, **kw):
    return asyncio.run(J.jharokha(ctx or CTX, action, **kw))


def _wipe(tenants):
    for t in tenants:
        shutil.rmtree(Path("data") / "jharokha" / t, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_state():
    yield
    if J._OWNER.get("loop") is not None:                 # close every browser, keep the owner loop warm
        try:
            fut = asyncio.run_coroutine_threadsafe(J._aclose_all(), J._OWNER["loop"])
            fut.result(timeout=30)
        except Exception:
            pass
    _wipe((CTX.tenant_id, CTX2.tenant_id))


def teardown_module():
    J._shutdown_owner()


def _ref_of(tree: str, role: str, name: str) -> str:
    for line in tree.splitlines():
        if f'- {role} "{name}"' in line and "[ref=" in line:
            return line.split("[ref=")[1].split("]")[0]
    raise AssertionError(f"no {role} '{name}' in the tree:\n{tree[:600]}")


# ---------------------------------------------------------------- the shape

def test_open_and_snapshot_shape():
    out = jh("open", url=SHOP)
    assert out["ok"] and out["action"] == "open" and out["error"] is None
    assert out["title"] == "jh shop" and out["url"].startswith("data:text/html")
    assert out["refs"] > 0 and out["tree"].count("[ref=") == out["refs"]
    assert "jh todos" in out["text"] and "idle" in out["text"]
    assert out["meta"]["elapsed_ms"] >= 0
    for ref_line in ("- button ", "- textbox ", "- link ", "- heading "):
        assert any(line.lstrip().startswith(ref_line) for line in out["tree"].splitlines()), ref_line


def test_snapshot_rides_every_answer():
    out = jh("open", url=SHOP)
    assert "tree" in out and out["refs"] > 0
    out2 = jh("snapshot")
    assert out2["ok"] and out2["tree"] == out["tree"]     # nothing changed -> the same honest tree


def test_envelope_shape_always():
    for out in (jh("nope"), jh("open", url=""), jh("snapshot")):
        assert out["schema_version"] == 1 and out["tool"] == "jharokha"
        assert set(out) >= {"ok", "action", "error", "meta"}
        assert isinstance(out["meta"]["elapsed_ms"], int)
        assert out["error"] is None or set(out["error"]) == {"code", "message", "hint"}


# ---------------------------------------------------------------- click / type / press

def test_click_through_a_ref_really_clicks():
    out = jh("open", url=SHOP)
    ref = _ref_of(out["tree"], "button", "Add")
    out2 = jh("click", ref=ref)
    assert out2["ok"] and "clicked" in out2 and "Add" in out2["clicked"]
    assert "clicked" in out2["text"] and "idle" not in out2["text"]      # the auto-snapshot saw it


def test_click_unknown_ref_is_honest():
    jh("open", url=SHOP)
    out = jh("click", ref="e999")
    assert out["ok"] is False and out["error"]["code"] == "NOT_FOUND"
    assert "snapshot" in out["error"]["hint"].lower()


def test_stale_ref_after_navigation():
    out = jh("open", url=SHOP)
    ref = _ref_of(out["tree"], "button", "Add")
    jh("open", url=FORM)                                  # a different page entirely
    out2 = jh("click", ref=ref)
    assert out2["ok"] is False and out2["error"]["code"] == "NOT_FOUND"


def test_type_fills_and_submit_presses_enter():
    out = jh("open", url=FORM)
    ref = _ref_of(out["tree"], "textbox", "Name here")
    out2 = jh("type", ref=ref, text="sunita", submit=True)
    assert out2["ok"] and out2["typed"] == {"ref": ref, "chars": 6, "submit": True}
    assert "sent sunita" in out2["text"]                  # the form's onsubmit really ran


def test_type_on_a_click_target_is_refused():
    out = jh("open", url=SHOP)
    ref = _ref_of(out["tree"], "button", "Add")
    out2 = jh("type", ref=ref, text="nope")
    assert out2["ok"] is False and out2["error"]["code"] == "BAD_INPUT"


def test_type_select_takes_the_option():
    out = jh("open", url=SHOP)
    ref = _ref_of(out["tree"], "combobox", "Colour")
    out2 = jh("type", ref=ref, text="blue")
    assert out2["ok"] and "pick blue" in out2["text"]


def test_press_allowlist():
    jh("open", url=SHOP)
    out = jh("press", key="Enter")
    assert out["ok"] and out["pressed"] == "Enter"
    for bad in ("Control+A", "F12", "Enter+Tab", ""):
        out2 = jh("press", key=bad)
        assert out2["ok"] is False and out2["error"]["code"] == "BAD_INPUT", bad


# ---------------------------------------------------------------- console

def test_console_tail_and_clear():
    out = jh("open", url=NOISY)
    jh("click", ref=_ref_of(out["tree"], "button", "Speak"))
    jh("click", ref=_ref_of(out["tree"], "button", "Break"))
    cons = jh("console")
    assert cons["ok"] and cons["shown"] >= 2
    kinds = {r["type"] for r in cons["rows"]}
    assert "log" in kinds and "pageerror" in kinds
    joined = " | ".join(r["text"] for r in cons["rows"])
    assert "jh-log-marker" in joined and "jh-boom" in joined
    cleared = jh("console", clear=True)
    assert cleared["ok"] and cleared["cleared"]
    after = jh("console")
    assert after["shown"] == 0 and after["rows"] == []


# ---------------------------------------------------------------- tabs

def test_tabs_lifecycle_and_last_tab_closes_the_browser():
    out = jh("open", url=SHOP)
    assert out["new_tab"] is True and out["tab"] == 0
    lst = jh("tabs", op="list")
    assert lst["count"] == 1 and lst["tabs"][0]["current"] is True
    out2 = jh("tabs", op="new", url=FORM)
    assert out2["op"] == "new" and out2["tab"] == 1 and out2["title"] == "jh form"
    lst = jh("tabs", op="list")
    assert lst["count"] == 2 and [t["current"] for t in lst["tabs"]] == [False, True]
    sel = jh("tabs", op="select", index=0)
    assert sel["op"] == "select" and sel["tab"] == 0 and "jh todos" in sel["text"]
    closed = jh("tabs", op="close", index=1)
    assert closed["op"] == "close" and closed["count"] == 1
    gone = jh("tabs", op="close", index=0)
    assert "the browser is shut" in gone["closed"]
    after = jh("snapshot")
    assert after["ok"] is False and after["error"]["code"] == "NOT_FOUND"


def test_tab_cap_is_honest():
    jh("open", url=SHOP)
    for _ in range(3):
        assert jh("tabs", op="new", url="about:blank")["ok"]
    out = jh("tabs", op="new", url="about:blank")
    assert out["ok"] is False and out["error"]["code"] == "TOO_BIG"


# ---------------------------------------------------------------- screenshot

def test_screenshot_lands_in_the_tenant_dir():
    jh("open", url=SHOP)
    out = jh("screenshot")
    assert out["ok"] and out["bytes"] > 0 and out["full"] is False
    p = Path("data") / out["file"]
    assert p.exists() and p.stat().st_size == out["bytes"]
    assert str(p).startswith(str(Path("data") / "jharokha" / CTX.tenant_id))
    full = jh("screenshot", full=True)                    # a real full-page picture too
    assert full["ok"] and full["full"] is True and full["bytes"] > 0


def test_screenshot_needs_a_page():
    out = jh("screenshot")
    assert out["ok"] is False and out["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------- the guards

def test_guard_blocks_private_and_weird_urls():
    for url in ("http://127.0.0.1:9/x", "http://169.254.169.254/latest/meta-data/",
                "http://10.0.0.1/", "file:///etc/passwd", "ftp://example.com/x",
                "data:text/javascript,console.log(1)", "about:config"):
        out = jh("open", url=url)
        assert out["ok"] is False and out["error"]["code"] == "BLOCKED", url
    long_page = "data:text/html," + "x" * 17_000
    out = jh("open", url=long_page)
    assert out["ok"] is False and out["error"]["code"] == "BLOCKED"


def test_open_needs_a_url():
    out = jh("open", url="   ")
    assert out["ok"] is False and out["error"]["code"] == "BAD_INPUT"


def test_no_page_honesty_on_a_fresh_tenant():
    for call in (dict(action="snapshot"), dict(action="click", ref="e1"),
                 dict(action="type", ref="e1", text="x"), dict(action="press", key="Enter"),
                 dict(action="console")):
        out = jh(**call)
        assert out["ok"] is False and out["error"]["code"] == "NOT_FOUND", call


def test_close_is_honest_both_ways():
    out = jh("close")
    assert out["ok"] and out["closed"] is False and "nothing to close" in out["note"]
    jh("open", url=SHOP)
    out2 = jh("close")
    assert out2["ok"] and out2["closed"] is True and out2["pages_closed"] == 1
    assert jh("close")["closed"] is False


# ---------------------------------------------------------------- the lane laws

def test_kill_switch_off_means_off(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "jharokha_enabled", False, raising=False)
    for call in (dict(action="open", url="about:blank"), dict(action="snapshot"),
                 dict(action="tabs", op="list"), dict(action="close")):
        out = jh(**call)
        assert out["ok"] is False and out["error"]["code"] == "NEED_SETUP", call


def test_idle_reaper_closes_and_the_next_open_relaunches_clean():
    jh("open", url=SHOP)
    assert CTX.tenant_id in J._TENANTS
    monkey_old = J._IDLE_S
    try:
        J._IDLE_S = 0                                     # every browser is stale right now
        with J._TEN_LOCK:
            J._TENANTS[CTX.tenant_id]["used"] -= 5.0
        reaped = asyncio.run(J._owned(J._reap_once()))
        assert reaped >= 1 and CTX.tenant_id not in J._TENANTS
    finally:
        J._IDLE_S = monkey_old
    out = jh("open", url=SHOP)
    assert out["ok"] and out["new_tab"] is True           # a fresh window, honestly new


def test_global_browser_cap_is_an_honest_busy(monkeypatch):
    monkeypatch.setattr(J, "_MAX_BROWSERS", 1, raising=False)
    assert jh("open", url=SHOP)["ok"]
    out = jh("open", url=SHOP, ctx=CTX2)
    assert out["ok"] is False and out["error"]["code"] == "BUSY"
    assert "RAM" in out["error"]["hint"] or "browsers" in out["error"]["hint"]


def test_tenant_isolation():
    assert jh("open", url=SHOP)["ok"]
    other_tabs = jh("tabs", op="list", ctx=CTX2)
    assert other_tabs["ok"] and other_tabs["count"] == 0  # B sees none of A's window
    other_shot = jh("snapshot", ctx=CTX2)
    assert other_shot["ok"] is False and other_shot["error"]["code"] == "NOT_FOUND"
    mine = jh("tabs", op="list")
    assert mine["count"] == 1                             # A's window untouched


def test_walk_caps_the_refs():
    out = jh("open", url=WIDE)
    assert out["ok"] and out["refs"] <= J._MAX_NODES and out["refs"] >= 250


# ---------------------------------------------------------------- the pins

def test_registry_607():
    assert len(TOOLS) == 629, ("626 + 1 app_engine (v0.824 APP ENGINE 1: the Web Studio React app lane - one new tool). " "617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: T3 local browser, "
                               "owner 'T3 Local Browser --- CONTINUE'). Was: 606 through v0.663 "
                               "(581 + 1 paisa_sahayak + 2 sandarbh + 1 bhandar + the dev chain's desks).")


def test_enum_and_label_pins():
    from app.agent.tools import TOOL_LABELS
    spec = next(t for t in TOOLS if t["name"] == "jharokha")
    assert spec["input_schema"]["properties"]["action"]["enum"] == list(J._JH_ACTIONS)
    assert TOOL_LABELS["jharokha"] == J.JHAROKHA_LABELS["jharokha"]
    assert set(J.JHAROKHA_HANDLERS) == {"jharokha"}


def test_app_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.884.0"                       # conscious-bump guard: moves with every release
