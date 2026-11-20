"""v0.999.28 HOOLA CODE BOTTOM ROW ON THE PHONE (owner: "DEPLOY SAME FOR PHONE HOOLA CODE ALSO" after v0.999.27 changed the
console's): the phone's New session screen keeps its environment + repository chips and sheets, the "Model" picker
(model + how hard it thinks) leaves the + sheet, and the chat's quality tier + her credits sit beside the repository.
A new session sends no model: her tier decides."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "lib/ui/code/code_start.dart").read_text()


def test_the_model_picker_is_gone():
    assert "_pickModel" not in SRC and "'Model'" not in SRC and "How hard it thinks" not in SRC
    assert "'model': ''," in SRC and "'effort': ''," in SRC


def test_the_row_has_the_chats_quality_tier_and_credits():
    assert "showHoolaTierSheet(context, widget.app)" in SRC and "hoolaTierName(v)" in SRC
    assert "HoolaCreditsPage(app: widget.app)" in SRC and "api.credits(hoolaCountry())" in SRC
    assert "' credits'" not in SRC and "credits' :" in SRC and "free today'" in SRC
    assert "_wallet!['exempt'] != true" in SRC          # nothing shows when credits are off or she is never charged


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.53"
