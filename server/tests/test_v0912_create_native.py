"""v0.912 CREATE NATIVE: the Tools tab's Create is the app's own studio - every console Create page as a native screen,
on the console's own routes (the routes are unchanged; this pins the app wiring and the one console change)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CREATE = ROOT / "lib/ui/create"


def test_every_console_create_page_has_a_native_screen():
    src = "\n".join(p.read_text() for p in CREATE.glob("*.dart"))
    for cls in ("HoolaCreate", "CreateImage", "CreateVideo", "CreateDirector", "CreateFilm", "CreateMusic", "CreateVoice",
                "CreateDub", "CreateEditor", "CreateScript", "CreateCasting", "CreateLibrary", "CreateBrand", "CreateCinema",
                "CreateGuides"):
        assert f"class {cls} extends" in src, cls


def test_the_same_routes_as_the_console():
    src = "\n".join(p.read_text() for p in CREATE.glob("*.dart"))
    for route in ("/api/create/jobs", "/api/create/items", "/api/create/write", "/api/create'", "/api/studio'",
                  "/api/studio/price", "/api/studio/improve", "/api/brand/kit", "/api/brand/logo", "/api/cinema"):
        assert route in src, route
    # money: a paid studio step only through the price card and her Haan (with the fingerprint proof the api adds)
    assert "studioDecide(" in src and "Waiting for your Haan" in src
    assert "Nothing is spent until you tap Haan" in src
    # delete asks first
    assert "Delete this creation?" in src


def test_tools_tab_opens_native_create_and_console_opens_a_tool():
    tools = (ROOT / "lib/ui/shell/hoola_tools.dart").read_text()
    assert "t.title == 'Create'" in tools and "HoolaCreate(app: app)" in tools
    v2 = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "if (v === 'creative' && CREATE) { CREATE.open(arg); return; }" in v2
    studio = (ROOT / "server/app/static/console/studio.js").read_text()
    assert "if (!V[v] || (v === 'cinema' && !ctx.cinema?.())) v = 'studio';" in studio, "an unknown ?a= falls back to the studio home"


def test_design_rules_and_ci():
    for p in CREATE.glob("*.dart"):
        s = p.read_text()
        assert "Color(0x" not in s and "BackdropFilter" not in s and "glass.dart" not in s, p.name
    wf = (ROOT / ".github/workflows/app-screens.yml").read_text()
    assert "test/create_native_test.dart" in wf
    shots = (ROOT / "test/goldens/screens_test.dart").read_text()
    for n in ("65_create_home", "66_create_image", "67_create_film"):
        assert n in shots


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.912.0"
    assert "version: 0.912.0+911" in (ROOT / "pubspec.yaml").read_text()
