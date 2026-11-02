"""v0.425 RANG (App Sahayak Pillar G): rich native pieces + the custom component escape hatch.
Server: signature / photos / video / audio / richtext fields - each file checked for what it really is (an MP4 / M4A container
by its ftyp box, not by its name), owned by the person, the right kind for the field, at most 6 photos, formatted text kept
long and stripped of HTML; a 15-minute signed address for the phone's own players (tampering / expiry / someone else = 404).
Kits: every piece in Kotlin and Swift, forms + rows draw them, microphone asked only in apps with a voice-note field.
Custom components: house rules checked in CODE on both sources, literal-only samples, her tap bound to a hash, approved ones
written into both builds with a check screen, a compile failure takes the component out (never the app)."""
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from tests.test_v0407_live import _shop
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app" / "appmaker"


def _jpeg():
    b = io.BytesIO()
    Image.new("RGB", (300, 200), (10, 120, 200)).save(b, "JPEG")
    return b.getvalue()


def _mp4(brand=b"mp42", size=4000):
    return (b"\x00\x00\x00\x18ftyp" + brand + b"\x00\x00\x00\x00mp42isom") + b"\x00" * size


def _up(c, api, h, raw, ctype):
    return c.post(f"{api}/files", content=raw, headers={**h, "Content-Type": ctype})


def test_rich_fields_and_media(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker.models import AppProject
    from app.db import session
    c, aid, api, hs, p1, ids = _shop(droid_env)
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    BE.change_schema(r, {"add_list": [{"key": "visits", "label": "Visits", "rules": {"create": "member", "read": "own", "update": "admin",
                                                                                      "delete": "admin"},
                                       "fields": [{"key": "note", "type": "text"}, {"key": "sig", "type": "signature"},
                                                  {"key": "pics", "type": "photos"}, {"key": "clip", "type": "video"},
                                                  {"key": "voice", "type": "audio"}, {"key": "body", "type": "richtext"}]}]})
    types = {f["key"]: f["type"] for c_ in c.get(f"{api}/schema").json()["collections"] if c_["key"] == "visits" for f in c_["fields"]}
    assert types == {"note": "text", "sig": "signature", "pics": "photos", "clip": "video", "voice": "audio", "body": "richtext"}
    A, N = hs["Asha"], hs["Neha"]
    p_a1, p_a2 = (_up(c, api, A, _jpeg(), "image/jpeg").json()["id"] for _ in range(2))
    p_n = _up(c, api, N, _jpeg(), "image/jpeg").json()["id"]
    vid = _up(c, api, A, _mp4(), "video/mp4").json()
    assert vid["kind"] == "video"
    aud = _up(c, api, A, _mp4(b"M4A "), "audio/mp4").json()
    assert aud["kind"] == "audio"
    assert _up(c, api, A, b"\x00\x00\x00\x18ftypevil" + b"\x00" * 100, "video/mp4").status_code == 415   # not a real container brand
    assert _up(c, api, A, b"not a picture at all" * 10, "video/mp4").status_code == 415                  # no ftyp: treated as a photo, refused
    assert _up(c, api, A, _mp4(b"M4A ", 11 * 1024 * 1024), "audio/mp4").status_code == 413
    long = "**Visit report** " + "x" * 3000 + " <script>alert(1)</script>"
    ok = c.post(f"{api}/c/visits", json={"note": "first", "sig": p_a1, "pics": f"{p_a1},{p_a2}", "clip": vid["id"], "voice": aud["id"],
                                         "body": long}, headers=A)
    assert ok.status_code == 200, ok.text
    row = ok.json()
    assert row["pics"] == f"{p_a1},{p_a2}" and row["clip"] == vid["id"] and "<script>" not in row["body"] and len(row["body"]) > 3000
    # wrong kind for the field / someone else's photo / too many
    for bad, code in (({"clip": p_a1}, 400), ({"voice": vid["id"]}, 400), ({"sig": vid["id"]}, 400),
                      ({"pics": f"{p_a1},{p_n}"}, 403), ({"pics": ",".join([p_a1] * 7)}, 400)):
        got = c.post(f"{api}/c/visits", json={"note": "x", **bad}, headers=A)
        assert got.status_code == code, (bad, got.text)
    # the phone's player: a signed address, no token in it
    link = c.post(f"{api}/files/{vid['id']}/link", headers=A).json()
    assert "/media/" in link["path"] and "Bearer" not in link["path"]
    got = c.get(link["path"])
    assert got.status_code == 200 and got.headers["content-type"] == "video/mp4" and got.content[4:8] == b"ftyp"
    assert got.headers["content-security-policy"] == "sandbox"
    assert c.get(link["path"][:-3] + "abc").status_code == 404                                           # tampered
    assert c.post(f"{api}/files/{vid['id']}/link", headers=N).status_code == 404                       # not hers
    a = c.get(f"{api}/files/{aud['id']}", headers=A)
    assert a.status_code == 200 and a.headers["content-type"] == "audio/mp4"


def test_kits_and_builds_carry_the_rich_pieces():
    kt = (ROOT / "android/template/app/src/main/java/hoola/kit/Rich.kt").read_text()
    sw = (ROOT / "ios/template/Sources/Kit/Rich.swift").read_text()
    for n in ("SignatureField", "PhotosField", "VideoField", "AudioField", "RichTextField", "RichText", "PhotosStrip", "VideoPlayer",
              "AudioPlayer", "PdfViewer", "CalendarBlock", "KanbanBlock", "GanttBlock", "LineChart", "PieChart", "Carousel", "OnboardingPager"):
        assert f"fun {n}(" in kt, n
    for n in ("SignatureRow", "PhotosRow", "VideoRow", "AudioRow", "RichTextRow", "RichTextView", "PhotosStripView", "VideoPlayerView",
              "AudioPlayerView", "PdfViewerView", "CalendarBlock", "KanbanBlock", "GanttBlock", "LineChartView", "PieChartView",
              "CarouselView", "OnboardingPager", "RichRowParts"):
        assert f"struct {n}" in sw, n
    for src in (kt, sw):
        assert "WebView" not in src.replace("no web views", "").replace("Never a WebView", "") and "/files/" in src and "/link" in src
    from app.appmaker.android import gen as AG
    from app.appmaker.ios import gen as IG
    spec = {"seed": {"backend": {"collections": [{"key": "v", "fields": [{"key": "voice", "type": "audio"}]}]}}}
    assert "RECORD_AUDIO" in AG.manifest_xml(spec) and "RECORD_AUDIO" not in AG.manifest_xml({})
    import plistlib
    assert "NSMicrophoneUsageDescription" in plistlib.loads(IG.info_plist(spec).encode())
    rows = "\n".join(AG._form_rows("v", [{"key": k, "label": k, "type": t} for k, t in
                                         (("s", "signature"), ("p", "photos"), ("v", "video"), ("a", "audio"), ("b", "richtext"))], False))
    for n in ("SignatureField", "PhotosField", "VideoField", "AudioField", "RichTextField"):
        assert n in rows
    assert 'case "richtext": RichTextRow' in (ROOT / "ios/template/Sources/Kit/Logic.swift").read_text()
    assert '"richtext" -> RichTextField(label, k)' in (ROOT / "android/template/app/src/main/java/hoola/kit/Logic.kt").read_text()


GOOD = {
    "name": "CustomRatingBars", "purpose": "Stars per level", "params": "counts: List<Int> (5 numbers)",
    "kotlin": """package hoola.kit

import androidx.compose.foundation.layout.Column
import androidx.compose.runtime.Composable

@Composable
fun CustomRatingBars(counts: List<Int>) {
    Column {
        counts.forEachIndexed { i, n -> Small("${5 - i} stars: $n") }
    }
}
""",
    "swift": """import SwiftUI

struct CustomRatingBars: View {
    let counts: [Int]
    init(counts: [Int]) { self.counts = counts }
    var body: some View {
        VStack(alignment: .leading) {
            ForEach(Array(counts.enumerated()), id: \\.offset) { i, n in Text("\\(5 - i) stars: \\(n)") }
        }
    }
}
""",
    "sample_kt": "CustomRatingBars(counts = listOf(5, 3, 1, 0, 2))", "sample_swift": "CustomRatingBars(counts: [5, 3, 1, 0, 2])",
}


def test_custom_component_rules_approval_and_build(droid_env, monkeypatch):
    from app.appmaker import ai as AI
    from app.appmaker import custom as CU
    from app.appmaker.android import gen as AG
    from app.appmaker.ios import gen as IG
    from app.appmaker.models import AppProject
    from app.db import session
    assert CU.problems(GOOD) == []
    bads = {"web": dict(GOOD, kotlin=GOOD["kotlin"].replace("Column {", "android.webkit.WebView(null)\n    Column {")),
            "net": dict(GOOD, kotlin=GOOD["kotlin"].replace("import androidx.compose.runtime.Composable", "import java.net.URL\nimport androidx.compose.runtime.Composable")),
            "urlsession": dict(GOOD, swift=GOOD["swift"].replace("var body", "let s = URLSession.shared\n    var body")),
            "import": dict(GOOD, swift="import WebKit\n" + GOOD["swift"]),
            "data": dict(GOOD, kotlin=GOOD["kotlin"].replace("Column {", "val t = Auth.token()\n    Column {")),
            "name": dict(GOOD, name="RatingBars"),
            "sample": dict(GOOD, sample_kt="CustomRatingBars(counts = loadFromServer())"),
            "braces": dict(GOOD, kotlin=GOOD["kotlin"] + "{")}
    for why, b in bads.items():
        assert CU.problems(b), why
    c, aid, api, hs, p1, ids = _shop(droid_env)
    calls = []

    def fake(system, prompt, max_tokens=7000):
        calls.append(prompt)
        return dict(GOOD) if len(calls) > 1 else bads["web"]          # the first try breaks a rule; the repair round fixes it
    monkeypatch.setattr(AI, "ask_json", fake)
    base = f"/api/apps/{aid}/components"
    got = c.post(f"{base}/draft", json={"words": "a bar per star level showing how many ratings"}).json()
    assert got["name"] == "CustomRatingBars" and got["status"] == "draft" and got["approved"] is False and len(calls) == 2
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    assert CU.for_build(r) == []                                           # nothing before her tap
    assert c.post(f"{base}/CustomRatingBars/approve", json={}).status_code == 403
    assert c.post(f"{base}/CustomRatingBars/approve", json={"her_tap": True}).json()["approved"] is True
    built = CU.for_build(r)
    assert [x["name"] for x in built] == ["CustomRatingBars"]
    spec = {"custom": built}
    files = CU.android_files(built)
    assert "custom/CustomRatingBars.kt" in files and "CustomRatingBars(counts = listOf(5, 3, 1, 0, 2))" in files["custom/ComponentsGallery.kt"]
    assert "ComponentsGallery()" in CU.swift_files(built)["Custom/ComponentsGallery.swift"] or "struct ComponentsGallery" in CU.swift_files(built)["Custom/ComponentsGallery.swift"]
    assert '"hoola_components" -> ComponentsGallery()' in AG.screens_kt({**spec, "screens": [{"id": "home", "label": "Home"}]}, {"home"})
    assert 'case "hoola_components"' in IG.screens_swift({**spec, "screens": [{"id": "home", "label": "Home"}]})
    # a changed file needs her tap again; a compile failure takes it out of the build
    import app.appmaker.custom as CM
    cdir = CM._dir(r)
    data = json.loads((cdir / "CustomRatingBars.json").read_text())
    data["kotlin"] = data["kotlin"].replace("stars", "taare")
    (cdir / "CustomRatingBars.json").write_text(json.dumps(data))
    assert CU.for_build(r) == []
    c.post(f"{base}/CustomRatingBars/approve", json={"her_tap": True})
    log = "e: file:///w/app/src/main/java/hoola/kit/custom/CustomRatingBars.kt:9:5 Unresolved reference: Smal"
    assert CU.failed_in(log, CU.for_build(r)) == ["CustomRatingBars"]
    CU.mark(r, "CustomRatingBars", "failed", log)
    assert CU.for_build(r) == [] and c.get(base).json()["components"][0]["status"] == "failed"
    assert c.delete(f"{base}/CustomRatingBars").json()["components"] == []


def test_generators_run_as_plain_scripts_in_ci(tmp_path):
    """CI runs `python3 gen.py spec out` (no package): v0.425 broke that with `from .. import custom`."""
    import json, subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app/appmaker"
    sp = json.loads((root / "android/fixture/spec.json").read_text())
    sp["custom"] = [{"name": "StarBadge", "kotlin": "package hoola.kit\n", "swift": "import SwiftUI\n",
                     "sample_kt": "StarBadge()", "sample_swift": "StarBadge()"}]
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(sp))
    for plat, want in (("android", "app/src/main/java/hoola/kit/custom/StarBadge.kt"), ("ios", "Sources/Kit/Custom/StarBadge.swift")):
        out = tmp_path / plat
        r = subprocess.run([sys.executable, str(root / plat / "gen.py"), str(spec), str(out)], capture_output=True, text=True, cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr[-800:]
        assert (out / want).exists()
