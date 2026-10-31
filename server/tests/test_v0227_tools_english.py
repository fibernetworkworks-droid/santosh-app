"""v0.227.1 - the Tools category names speak English; the starter prompts (her words to Hoola) stay as they are."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _kaam():
    src = (ROOT / "server/app/static/console/kaam.js").read_text()
    return json.loads(re.search(r"window\.KAAM = (\[.*?\]);\n", src, re.S).group(1))


def test_category_names_are_english():
    names = [c[2] for c in _kaam()]
    assert names == ["Everyday", "Read & recognise", "Conversations", "Google & files", "Photos & video",
                     "Websites & computer", "Home & TV", "Phone", "Hoola Network", "Hoola Employee",
                     "Business assistants", "Memory & safety"]
    assert [c[0] for c in _kaam()][:3] == ["din", "padho", "baat"]          # ids unchanged (anchors #k-<id>)


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.318.0"
    assert "0.318.0+358" in (ROOT / "pubspec.yaml").read_text()
