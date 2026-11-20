"""v0.920 CAMERA ALIVE (owner: "use this and deploy for now" on the 'Camera moves alive' design canvas): every camera
move tile on the phone plays the design's moving chai-stall scene, drawn in four layers by CrCamScene."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COL = (ROOT / "lib/ui/create/create_colour.dart").read_text()
THEME = (ROOT / "lib/ui/hoola_theme.dart").read_text()
FILM = (ROOT / "lib/ui/create/create_film.dart").read_text()
HOME = (ROOT / "lib/ui/create/create_home.dart").read_text()

MOVES = ["Auto", "Static", "Dolly in", "Dolly out", "Crash zoom", "Orbit", "Crane up", "Tracking", "Pan", "Drone",
         "Handheld", "Low angle"]


def test_scene_widget_and_painter():
    assert "class CrCamScene extends StatefulWidget" in COL and "class _CamScenePainter extends CustomPainter" in COL
    assert "HoolaMotion.reduced(context)" in COL.split("class CrCamScene")[1].split("class _CamScenePainter")[0]
    for layer in ("layer(bg,", "layer(mid,", "layer(subj,", "layer(fg,", "layer(rig,"):
        assert layer in COL
    body = COL.split("class _CamScenePainter")[1]
    for m in MOVES:
        if m != "Static":
            assert f"'{m}'" in body, m


def test_palette_per_move_in_theme():
    assert "class CreateCamScene" in THEME
    block = THEME.split("class CreateCamScene")[1].split("static const all")[1]
    for m in MOVES:
        assert f"'{m}': CreateCamScene(" in block, m
    # colours live in the theme, never raw in the Create files
    assert "Color(0x" not in COL.split("class CrCamScene")[1].split("// ----")[0]


def test_tiles_use_it_and_real_clip_stays_on_top():
    assert "fallback: CrCamScene(move: x.$1)" in FILM
    assert "fallback: CrCamScene(move: _moves[i].$1)" in HOME
    assert "CrCamArt(store: store" in FILM and "CrCamArt(store: _store" in HOME
    for f in (COL, FILM, HOME):
        assert "BackdropFilter" not in f and "glass.dart'" not in f


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.49"' in main  # the newest story now leads; v0.920 lives in CLAUDE.md + HISTORY
    assert "version: 0.999.49+1047" in (ROOT / "pubspec.yaml").read_text()
