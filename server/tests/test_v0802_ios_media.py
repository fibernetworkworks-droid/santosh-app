"""v0.802 MEDIA: iPhone parity with the Android kit - in-app camera beside the photo picker, the share sheet, and one
in-memory cache for photos downloaded from the app's server. No Swift compiler here: string checks on the kit + the
generated Info.plist; the real compile happens on the macOS CI (ios-check.yml builds every kit file)."""
import json
import plistlib
from pathlib import Path

from app.appmaker.ios import gen as IG
from app.appmaker.ios import prompts as PR

KIT = Path(__file__).resolve().parents[1] / "app" / "appmaker" / "ios" / "template" / "Sources" / "Kit"
FIX2 = Path(__file__).resolve().parents[1] / "app" / "appmaker" / "android" / "fixture2" / "spec.json"


def _spec(*types):
    return {"app": {"name": "Shop"}, "seed": {"backend": {"collections": [
        {"key": "jobs", "fields": [{"key": f"f{i}", "type": t} for i, t in enumerate(types)]}]}}}


def test_media_swift_has_camera_share_and_cache():
    m = (KIT / "Media.swift").read_text()
    assert "UIImagePickerController" in m and "UIViewControllerRepresentable" in m
    assert m.count("UIImagePickerController.isSourceTypeAvailable(.camera)") >= 2   # button hidden + picker guarded
    assert "vc.sourceType = .camera" in m and ".originalImage" in m and "imagePickerControllerDidCancel" in m
    assert "struct CameraButton: View" in m and "struct CameraPicker: UIViewControllerRepresentable" in m
    assert "func localJpeg(_ img: UIImage) -> String?" in m and '"local:" + url.path' in m
    assert "struct ShareButton: View" in m and "ShareLink(item: u" in m and "ShareLink(item: text)" in m
    assert "func shareText(_ text: String, url: String = \"\")" in m and "UIActivityViewController" in m
    assert "popoverPresentationController" in m                                   # iPad needs a source view
    assert "NSCache<NSString, UIImage>" in m and "countLimit" in m and "totalCostLimit" in m
    assert "enum Media " not in m and "enum Media{" not in m                       # Rich.swift already owns `Media`


def test_photo_fields_offer_the_camera():
    acc = (KIT / "Accounts.swift").read_text()
    row = acc[acc.index("struct PhotoRow: View"):acc.index("struct LocationRow: View")]
    assert "PhotosPicker(" in row and "CameraButton { v in state.form[key] = v }" in row
    rich = (KIT / "Rich.swift").read_text()
    rows = rich[rich.index("struct PhotosRow: View"):rich.index("struct PhotosStripView: View")]
    assert "PhotosPicker(" in rows and "CameraButton {" in rows and ".prefix(max)" in rows


def test_server_photo_uses_the_cache_and_keeps_the_token():
    rich = (KIT / "Rich.swift").read_text()
    sp = rich[rich.index("struct ServerPhoto: View"):rich.index("struct RichRowParts: View")]
    assert "ImageCache.shared.get(src)" in sp and "ImageCache.shared.put(got, src)" in sp
    assert 'Cloud.bytes("/files/\\(src)", token: Auth.shared.token)' in sp
    # no other remote image load in the kit bypasses the cache
    for f in KIT.glob("*.swift"):
        t = f.read_text()
        assert "AsyncImage" not in t, f.name
        if f.name != "Rich.swift":
            assert "UIImage(data: d)" not in t, f.name


def test_plist_camera_key_for_photo_fields():
    for types in (("photo",), ("photos",), ("text", "photos")):
        pl = plistlib.loads(IG.info_plist(_spec(*types)).encode())
        assert "Take photo" in pl["NSCameraUsageDescription"]
    both = plistlib.loads(IG.info_plist(_spec("scan", "photo")).encode())["NSCameraUsageDescription"]
    assert "Scan" in both and "Take photo" in both
    assert "Take photo" not in plistlib.loads(IG.info_plist(_spec("scan")).encode())["NSCameraUsageDescription"]
    assert "NSCameraUsageDescription" not in plistlib.loads(IG.info_plist(_spec("text", "location")).encode())


def test_fixture2_project_ships_media_kit_and_camera_key(tmp_path):
    out = tmp_path / "i"
    IG.write_project(json.loads(FIX2.read_text()), out)
    assert (out / "Sources/Kit/Media.swift").exists()                     # compiled with the kit on the macOS CI
    assert "NSCameraUsageDescription" in (out / "Info.plist").read_text()


def test_prompts_tell_the_model_about_share_and_camera():
    src = Path(PR.__file__).read_text()
    assert "ShareButton(text: text, url: link)" in src and "shareText(text)" in src
    assert 'struct ShareButton: View { init(text: String, url: String = "", label: String = "") }' in src
    assert "struct CameraButton: View" in src


def test_kit_words_reach_the_translation_table(tmp_path):
    from app.appmaker import i18n
    proj = tmp_path / "p"
    (proj / "Sources" / "Kit").mkdir(parents=True)
    (proj / "Sources" / "Kit" / "Media.swift").write_text((KIT / "Media.swift").read_text())
    words = i18n.collect(proj, swift=True)
    assert "Take photo" in words and "Share" in words
