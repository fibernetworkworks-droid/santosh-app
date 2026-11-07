"""v0.376 MAALKIN PHONE (App Sahayak Phase 40): her phone's app screen gets the money tools - the month's hisaab line, who owes
(her own WhatsApp link + "paise mile"), stock running low, live coupon codes - through the same owner routes as the console."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phone_panel():
    d = (ROOT / "lib/ui/app_money.dart").read_text()
    for route in ("'hisaab'", "'khata-yaad'", "'stock'", "'coupons'", "/khata/${_s(c['member'])}/pay"):
        assert route in d, route
    assert "LaunchMode.externalApplication" in d and "WhatsApp mein kholo" in d
    screen = (ROOT / "lib/ui/app_design_screen.dart").read_text()
    assert "import 'app_money.dart';" in screen and "AppMoneyPanel(app: app, id: widget.id)" in screen
