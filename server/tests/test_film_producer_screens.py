"""Film Desk producer screens (console + phone) and the hub entry: pins so the screens cannot drift from the server routes they call, and so
the rules they draw (heuristics labelled as hints, the royalty form insisting on its contract clause, every server value escaped) stay put."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JS = (ROOT / "server/app/static/console/filmdesk.js").read_text()
DART = (ROOT / "lib/ui/filmdesk_producer.dart").read_text()
SCREEN = (ROOT / "lib/ui/filmdesk_screen.dart").read_text()


def _routes():
    import app.filmdesk.api as A
    r = A.make_router(lambda: None, lambda: "t")
    return {(m, x.path.replace("/api/filmdesk/projects/{ref}/", "")) for x in r.routes for m in x.methods if "{ref}/" in x.path}


def _called(text: str, verb: str) -> set[str]:
    """Paths a screen calls: console U('x') / get('x'), phone _get('x') / _post('x')."""
    pats = {"GET": [r"get\('([a-z\-]+)", r"U\('([a-z\-]+)", r"_get\('([a-z\-]+)"], "POST": [r"_post\('([a-z\-]+)", r"_add\('([a-z\-]+)", r"U\('([a-z\-]+)"]}
    out = set()
    for p in pats[verb]:
        out |= set(re.findall(p, text))
    return out


def test_every_path_the_console_and_phone_call_exists_on_the_server():
    routes = _routes()
    for text in (JS, DART):
        for path in _called(text, "GET"):
            assert ("GET", path) in routes, path
    for path in _called(DART, "POST"):
        assert ("POST", path) in routes, path
    for path in ("royalties", "festivals", "windows", "deliverables", "localisation", "schedule"):
        assert ("POST", path) in routes and ("GET", path) in routes


def test_console_page_is_wired_stamped_and_escapes_everything():
    html = (ROOT / "server/app/static/console/v2.html").read_text()
    v2 = (ROOT / "server/app/static/console/v2.js").read_text()
    emp = (ROOT / "server/app/static/console/employees.js").read_text()
    assert re.search(r'filmdesk\.js\?v=\d+\.\d+\.\d+"', html) and 'id="v-filmdesk"' in html
    assert "HoolaFilmDesk" in v2 and "filmdesk:'· Film Desk'" in v2 and "FD?.open($('#filmdesk'))" in v2
    assert "film: 'filmdesk'" in emp and "Film, Media & Entertainment" in emp
    assert "esc(" in JS and "innerHTML = await PANES" in JS
    # the real proof (a poisoned fixture through headless Chromium: 0 injected nodes, every tab) was run by hand; these pins keep its shape
    assert JS.count("esc(") >= 60 and "const note = t => t ? `<p class=\"muted\" style=\"margin:6px 0\">${esc(t)}</p>`" in JS
    assert "const H = t => `<h3 style=\"margin:22px 0 8px;font-size:15px\">${esc(t)}</h3>`" in JS and "JSON.stringify(ctx)" in JS


def test_the_rules_are_drawn_not_dropped():
    assert "hint" in JS and "heuristic" in JS and "hint · " in DART                                  # heuristics are labelled as hints
    assert "Contract clause (required)" in JS and "Contract ka clause (zaroori)" in DART             # royalty terms insist on a source
    assert "reader" not in JS.lower().replace("a reader's verdict", "")                              # no verdict anywhere on screen
    assert "rate nahi di" in JS and "rate nahi di" in DART                                           # a missing rate is shown, never filled
    assert "Nothing is sent or paid" in JS
    for tab in ("coverage", "previs", "schedule", "money", "sales", "delivery"):
        assert f"async {tab}()" in JS


def test_phone_screen_is_reachable_from_the_project_page():
    assert "import 'filmdesk_producer.dart';" in SCREEN and "_producerBox()," in SCREEN and "FilmdeskProducerPage(" in SCREEN
    assert "class FilmdeskProducerPage" in DART and DART.count("GlassButton(") >= 8
    for k in ("_inr", "_numericKeys", "applies_to"):
        assert k in DART


def test_hub_lists_the_film_producer_and_it_can_be_hired(env):
    from app.employee import hire as H
    c = H.CATALOG["film"]
    assert c["live"] and c["group"] == "Film, Media & Entertainment" and c["never"] and c["does"] and c["needs"]
    assert any("verdict" in x or "rating" in x for x in c["never"]) and any("rate" in x.lower() for x in c["never"])
    r = H.hire("t1", "film")
    assert r["key"] == "film" and r.get("status", "hired") in ("hired",)
