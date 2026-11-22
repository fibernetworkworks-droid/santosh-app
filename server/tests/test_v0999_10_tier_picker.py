"""v0.999.10 TIER PICKER (owner: "ADD TIER PICKER IN PHONE APP ALSO"): the console's Quality tier on the phone."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_phone_page_reads_and_saves_the_tier_and_asks_before_ultra():
    api = (ROOT / "lib/api.dart").read_text()
    assert "'/api/model/tier'" in api and "'confirm_ultra': confirmUltra" in api
    page = (ROOT / "lib/ui/shell/hoola_tier.dart").read_text()
    assert "class HoolaTierPage" in page and "modelTier()" in page and "modelTierSet(tier, confirmUltra: yes)" in page
    assert "if (tier == 'ultra')" in page and "_askUltra()" in page and "ultra_warning" in page
    assert "Hoola\\'s normal setup" in page and "_pick('')" in page          # back to the normal setup
    for k in ("reply", "employee_job", "call_minute", "reel_30s"):            # the costs the server sends
        assert f"'{k}'" in page
    assert "'note'" in page                                                     # her own model still wins


def test_both_settings_pages_open_it():
    new = (ROOT / "lib/ui/shell/hoola_settings.dart").read_text()
    assert "import 'hoola_tier.dart';" in new and "HoolaTierPage(app: app)" in new and "'Quality tier'" in new
    old = (ROOT / "lib/ui/profile_screen.dart").read_text()
    assert "import 'shell/hoola_tier.dart';" in old and "HoolaTierPage(app: app)" in old


def test_the_page_stays_inside_the_design_rules():
    page = (ROOT / "lib/ui/shell/hoola_tier.dart").read_text()
    assert "Color(0x" not in page and "FontWeight.w800" not in page and "FontWeight.w900" not in page
    assert "glass.dart" not in page and "fontSize:" not in page


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.155"
    assert "version: 0.999.155+1150" in (ROOT / "pubspec.yaml").read_text()
