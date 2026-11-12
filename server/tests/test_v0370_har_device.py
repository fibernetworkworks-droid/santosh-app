"""v0.370 HAR DEVICE JAANCH (App Sahayak Phase 34): her real builds (the builds repo, kept current by v0.369) also open
every screen on a tablet (Android) and on a 13-inch iPad (iPhone builds); the results come back in the artifact, never fail
the build, are read separately from the phone report (the iPad pictures never replace the phone ones) and reach the check line."""
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _zip(files: dict[str, bytes]) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for k, v in files.items():
            z.writestr(k, v)
    return b.getvalue()


def test_builds_repo_runs_both():
    a = (ROOT / "app_builder/hoola-build.yml").read_text()
    assert "hoola_qa/tablet_check.sh" in a and "|| true" in a and "qa/tablet.txt" in a
    i = (ROOT / "app_builder/hoola-ios.yml").read_text()
    assert "SIM_KIND=ipad bash ios/hoola_qa/sim_check.sh" in i and "qa-ipad/report.json" in i


def test_reader_keeps_phone_pictures_and_reads_tablet_ipad():
    from app.appmaker.android import runners as RN
    phone = {"opened": 5, "total": 5, "crashed": [], "passed": True}
    ipad = {"opened": 4, "total": 5, "crashed": ["cart"]}
    q = RN.qa_from_zip(_zip({"qa/report.json": json.dumps(phone).encode(), "qa/screens/home.png": b"PHONE",
                             "qa-ipad/report.json": json.dumps(ipad).encode(), "qa-ipad/screens/home.png": b"IPAD",
                             "qa/tablet.txt": b"home 1\ncart 0\norders 1\n"}))
    assert q["shots"]["home"] == b"PHONE" and q["report"]["opened"] == 5
    assert q["report"]["tablet"] == {"opened": 2, "total": 3, "crashed": ["cart"]}
    assert q["report"]["ipad"]["crashed"] == ["cart"] and q["report"]["ipad"]["total"] == 5


def test_check_lines():
    from app.appmaker.android import service as AN
    from app.appmaker.ios import service as IS
    a = AN.qa_line({"ran": True, "opened": 5, "total": 5, "tablet": {"opened": 2, "total": 3, "crashed": ["cart"]}})
    assert "on a tablet 2/3 screens (1 crash: cart)" in a
    i = IS.qa_line({"ran": True, "opened": 5, "total": 5, "ipad": {"opened": 5, "total": 5, "crashed": []}})
    assert "iPad par 5/5 screens" in i and "crash" not in i.split("iPad")[1]
