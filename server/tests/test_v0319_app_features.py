"""v0.319 APP FEATURES (App Sahayak Phase 2): photos, location, background updates, the UPI "I paid" claim, search /
filters - server side, plus the generated project and the model's guide. The Kotlin is compiled and driven against a
real Hoola server on the CI emulator (kit E2e: photo upload + fetch, the paid claim, the updates check)."""
import io
import json

from fastapi.testclient import TestClient
from PIL import Image

from tests.test_v0314_app_backend import _built
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def _jpeg(w=2400, h=1800, gps=True):
    im = Image.new("RGB", (w, h), (200, 80, 40))
    out = io.BytesIO()
    exif = Image.Exif()
    if gps:
        exif[0x8825] = {2: (18.0, 31.0, 0.0), 4: (73.0, 51.0, 0.0)}     # a GPS block a phone camera writes
        exif[0x010F] = "PhoneMaker"
    im.save(out, "JPEG", exif=exif)
    return out.getvalue()


def _member(c, api, email):
    t = c.post(f"{api}/signup", json={"email": email, "password": "pass-word-1", "name": email.split("@")[0]}).json()["token"]
    return {"Authorization": "Bearer " + t}


def test_schema_v2_fields_and_upgrade_of_an_old_backend(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker.models import AppProject
    from app.db import session
    aid, _conv, _key, be = _built(droid_env)
    f = {x["key"]: x for x in be["schema"]["collections"][0]["fields"]}
    assert f["pin"]["type"] == "location" and f["paid"]["admin_only"] and f["utr"]["admin_only"]
    assert be["v"] == BE.SCHEMA_V
    # an app built before v0.319 (v1 backend without the new fields) is upgraded in place on first use
    old = json.loads(json.dumps(be))
    old["v"] = 1
    old["schema"]["collections"][0]["fields"] = [x for x in old["schema"]["collections"][0]["fields"]
                                                 if x["key"] not in ("pin", "paid", "utr")]
    with session() as s:
        s.get(AppProject, aid).backend = json.dumps(old)
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    sch = BE.schema(r)
    assert {"pin", "paid", "utr"} <= {x["key"] for x in sch["collections"][0]["fields"]}
    with session() as s:
        assert json.loads(s.get(AppProject, aid).backend)["upgraded"]

    class R:
        def __init__(self, goal):
            self.goal, self.plan = goal, "{}"
    req = {x["key"]: x["type"] for x in BE.schema_for(R("service_request"))["collections"][0]["fields"]}
    assert req["photo"] == "photo" and req["pin"] == "location"


def test_photos_location_paid_updates_and_search(droid_env):
    from app.main import app
    c = TestClient(app)
    aid, conv, key, _be = _built(droid_env)
    api = f"/api/app-api/{key}"
    ha, hb = _member(c, api, "asha@example.com"), _member(c, api, "ravi@example.com")
    # photos: re-encoded JPEG, at most 1600 px, the GPS / camera EXIF gone; only the sender / staff / her can fetch it
    assert c.post(f"{api}/files", content=_jpeg()).status_code == 401
    up = c.post(f"{api}/files", content=_jpeg(), headers={**ha, "Content-Type": "image/jpeg"}).json()
    assert up["id"].startswith("f_") and max(up["w"], up["h"]) == 1600
    got = c.get(f"{api}/files/{up['id']}", headers=ha)
    assert got.status_code == 200 and got.headers["content-type"] == "image/jpeg"
    im = Image.open(io.BytesIO(got.content))
    assert im.size == (1600, 1200) and 0x8825 not in im.getexif() and 0x010F not in im.getexif()
    assert c.get(f"{api}/files/{up['id']}", headers=hb).status_code == 404       # another customer: nothing
    assert c.get(f"{api}/files/{up['id']}").status_code == 404
    assert c.get(f"/api/apps/{aid}/files/{up['id']}").status_code == 200          # she sees it in Hoola
    assert c.post(f"{api}/files", content=b"not an image", headers=ha).status_code == 415
    assert c.post(f"{api}/files", content=b"x" * (6 * 1024 * 1024 + 1), headers=ha).status_code == 413
    # location: a real lat,lng, normalised
    pid = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]["id"]
    base = {"name": "Asha", "phone": "9876543210", "cart": [{"id": pid, "qty": 1}]}
    assert c.post(f"{api}/c/orders", json={**base, "pin": "somewhere"}, headers=ha).status_code == 400
    assert c.post(f"{api}/c/orders", json={**base, "pin": "123.4,73.8"}, headers=ha).status_code == 400
    row = c.post(f"{api}/c/orders", json={**base, "pin": " 18.5204, 73.8567 ", "pay": "UPI"}, headers=ha).json()
    assert row["pin"] == "18.520400,73.856700" and row["paid"] == "No"
    # "I paid": the customer's word + her UPI reference; only for her own order; she gets a note to check her bank
    assert c.post(f"{api}/c/orders/{row['id']}/paid", json={"utr": "12"}, headers=ha).status_code == 400
    assert c.post(f"{api}/c/orders/{row['id']}/paid", json={"utr": "412345678901"}, headers=hb).status_code == 404
    paid = c.post(f"{api}/c/orders/{row['id']}/paid", json={"utr": "4123 4567 8901"}, headers=ha).json()
    assert paid["paid"] == "Customer says paid" and paid["utr"] == "412345678901"
    assert c.post(f"{api}/c/orders/{row['id']}", json={"paid": "Verified"}, headers=ha).status_code == 403   # never herself
    from app.db import Message, session
    with session() as s:
        notes = [m.content for m in s.query(Message).filter(Message.conversation_id == conv).all() if "UTR" in str(m.content)]
    assert notes and "678901" in notes[0] and "check" in notes[0]
    v = c.patch(f"/api/apps/{aid}/data/orders/{row['id']}", json={"paid": "Verified", "status": "Packed"}).json()
    assert v["paid"] == "Verified" and v["status"] == "Packed"
    assert c.post(f"{api}/c/orders/{row['id']}/paid", json={"utr": "412345678901"}, headers=ha).status_code == 409
    # background updates: Asha hears her order moved; Ravi (customer) hears nothing of hers
    upd = c.get(f"{api}/updates", headers=ha).json()
    mine = [x for x in upd["items"] if x["id"] == row["id"]]
    assert mine and mine[-1]["kind"] == "status" and mine[-1]["status"] == "Packed" and upd["now"]
    assert c.get(f"{api}/updates", params={"since": upd["now"]}, headers=ha).json()["items"] == []
    assert c.get(f"{api}/updates", headers=hb).json()["items"] == []
    assert c.get(f"{api}/updates").status_code == 401
    # a staff account hears about NEW orders since its last check
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    hb = {"Authorization": "Bearer " + c.post(f"{api}/login", json={"email": "ravi@example.com", "password": "pass-word-1"}).json()["token"]}
    mark = c.get(f"{api}/updates", headers=hb).json()["now"]
    c.post(f"{api}/c/orders", json={**base, "name": "Meena"}, headers=ha)
    new = c.get(f"{api}/updates", params={"since": mark}, headers=hb).json()["items"]
    assert [x["kind"] for x in new] == ["new"] and "Meena" in new[0]["title"]
    # search + status filter + paging
    rows = c.get(f"{api}/c/orders", params={"q": "meena"}, headers=hb).json()["rows"]
    assert len(rows) == 1 and rows[0]["name"] == "Meena"
    assert [x["status"] for x in c.get(f"{api}/c/orders", params={"status": "Packed"}, headers=hb).json()["rows"]] == ["Packed"]
    assert len(c.get(f"{api}/c/orders", params={"limit": 1, "offset": 1}, headers=hb).json()["rows"]) == 1


def test_photo_fields_check_ownership(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker.models import AppProject
    from app.db import session
    from app.main import app
    c = TestClient(app)
    aid, _conv, key, _be = _built(droid_env)
    # give the app a list with a photo field (a service-request app has one)
    with session() as s:
        row = s.get(AppProject, aid)
        row.goal, row.backend = "service_request", None
    api = f"/api/app-api/{key}"
    ha, hb = _member(c, api, "asha@example.com"), _member(c, api, "ravi@example.com")
    up = c.post(f"{api}/files", content=_jpeg(800, 600, gps=False), headers=ha).json()
    body = {"service": "AC repair", "problem": "Not cooling", "name": "Asha", "phone": "9876543210", "photo": up["id"]}
    assert c.post(f"{api}/c/requests", json={**body, "photo": "f_0000000000000000"}, headers=ha).status_code == 403
    assert c.post(f"{api}/c/requests", json=body, headers=hb).status_code == 403      # Ravi can't attach Asha's photo
    r = c.post(f"{api}/c/requests", json=body, headers=ha).json()
    assert r["photo"] == up["id"]
    assert BE.STATS["uploads"] >= 1


def test_generated_project_has_the_features(droid_env):
    from app.appmaker import kit as K
    from app.appmaker.android import gen as G
    from app.appmaker.android import prompts as PR
    from app.appmaker.models import AppProject
    from app.db import session
    aid, _conv, _key, be = _built(droid_env)
    with session() as s:
        row = s.get(AppProject, aid)
        proj = K.app_dir(row.tenant_id, aid) / "android" / "project"
    kit = proj / "app/src/main/java/hoola/kit"
    for f in ("Features.kt", "Updates.kt"):
        assert (kit / f).exists(), f
    man = (proj / "app/src/main/AndroidManifest.xml").read_text()
    assert "POST_NOTIFICATIONS" in man and "hoola.kit.UpdatesJob" in man and "BIND_JOB_SERVICE" in man
    assert "ACCESS_COARSE_LOCATION" in man            # the shop app has a delivery-location field
    assert "READ_MEDIA_IMAGES" not in man and "CAMERA" not in man and "ACCESS_BACKGROUND_LOCATION" not in man
    # no location field -> no location permission
    spec = {"seed": {"backend": {"collections": [{"key": "bookings", "fields": [{"key": "date", "type": "date"}]}]}}}
    m2 = G.manifest_xml(spec)
    assert "LOCATION" not in m2 and "POST_NOTIFICATIONS" in m2
    # fallback forms use the new fields
    bk = {"order": "", "collections": [{"key": "requests", "rules": {"create": "member"}, "fields": [
        {"key": "problem", "label": "Problem", "type": "long_text", "required": True},
        {"key": "photo", "label": "Photo", "type": "photo"}, {"key": "pin", "label": "Location", "type": "location"}]}]}
    form = G.fallback_screen({"id": "new_request", "label": "New request"}, ["new_request"], [], bk)
    assert 'PhotoField("Photo", "photo")' in form and 'LocationField("Location", "pin")' in form
    sheet = PR.kit_sheet()
    for k in ("PhotoField(", "LocationField(", "RemotePhoto("):
        assert k in sheet, k
    assert "photo" in PR.backend_line(bk) and "[photo]" in PR.backend_line(bk)
