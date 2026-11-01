"""v0.343 DESIGN SE MILAAN (App Sahayak Phase 10): every real app screen (device check screenshot) vs her approved design's
screenshot of that screen: a free 0-100 score after each build; on her ask Opus looks at the low ones and lists the
differences; fix rebuilds only those screens with the differences as notes (Android and iPhone)."""
import io

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from tests.test_v0314_app_backend import _shop_app
from tests.test_v128_appdesign import T
from tests.test_v132_android import FakeBuild, droid_env  # noqa: F401  (fixture)


def _screen(bg, blocks, w=390, h=844, status=False):
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    if status:                                            # a phone status bar on top of the native screenshot
        d.rectangle((0, 0, w, int(h * 0.045)), fill=(10, 10, 10))
    for (x0, y0, x1, y1, c) in blocks:
        d.rectangle((x0, y0, x1, y1), fill=c)
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


DESIGN = [(20, 80, 370, 300, (90, 60, 220)), (20, 330, 180, 520, (250, 140, 30)), (200, 330, 370, 520, (250, 140, 30)),
          (20, 560, 370, 620, (30, 30, 30))]


def test_score_tells_close_from_far():
    from app.appmaker import match as M
    design = _screen((250, 248, 245), DESIGN)
    # the native screen: same layout a little lower (status bar on top)
    native_ok = _screen((250, 248, 245), [(a, b + 38, c, d + 38, col) for a, b, c, d, col in DESIGN], status=True)
    native_bad = _screen((20, 20, 24), [(20, 600, 370, 820, (200, 200, 200))], status=True)
    good, bad = M.score(design, native_ok), M.score(design, native_bad)
    assert good["score"] >= 75 and bad["score"] < 45 and good["layout"] > bad["layout"] and bad["light"] < 50


def _setup(droid_env, monkeypatch, tmp_path):
    fake, _kt = droid_env
    from app.appmaker import kit as K
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    aid, conv = _shop_app(fake)
    RN.set_runner(FakeBuild())
    AN.build(T, aid, conv)
    r = AN.AS._load(aid)
    ids = AN.AS._j(r.plan, {})["screens"]
    shots = K.app_dir(T, aid) / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    qa = AN._dir(r) / "qa" / "b1"
    qa.mkdir(parents=True, exist_ok=True)
    good, bad = ids[0], ids[1]
    for sid in ids:
        (shots / f"{sid}-android.jpg").write_bytes(_screen((250, 248, 245), DESIGN))
        native = [(a, b + 38, c, d + 38, col) for a, b, c, d, col in DESIGN] if sid != bad else [(20, 600, 370, 820, (200, 200, 200))]
        (qa / f"{sid}.png").write_bytes(_screen((250, 248, 245) if sid != bad else (20, 20, 24), native, status=True))
    AN._put(aid, qa={"ran": True, "build": 1, "passed": True})
    return aid, conv, good, bad, ids


def test_check_lists_differences_and_fix_rebuilds_only_those(droid_env, monkeypatch, tmp_path):
    from app.appmaker import match as M
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.main import app
    from app.site import ai as SA
    aid, conv, good, bad, ids = _setup(droid_env, monkeypatch, tmp_path)
    try:
        seen = []

        def fake_json(system, prompt, max_tokens=0, kind="", images=None, effort=None):
            seen.append((prompt, len(images or [])))
            return {"score": 3, "differences": ["Use the light cream background of the design", "Put the violet banner at the top"]}
        monkeypatch.setattr(SA, "ask_json", fake_json)
        calls = []
        monkeypatch.setattr(AN, "build", lambda tenant, ref, conv="", only=None, notes=None, crashes=None: calls.append((only, notes)) or {})
        c = TestClient(app)
        v = c.post(f"/api/apps/{aid}/match", json={"platform": "android"}).json()
        rows = {x["id"]: x for x in v["match"]["android"]["screens"]}
        assert rows[bad]["score"] < M.MATCH_MIN <= rows[good]["score"]
        assert rows[bad]["differences"] == ["Use the light cream background of the design", "Put the violet banner at the top"]
        assert "differences" not in rows[good] and len(seen) == 1 and seen[0][1] == 2      # only the low one, both pictures
        assert v["rebuilt"] == [] and calls == []                                       # no fix unless she asks
        v = c.post(f"/api/apps/{aid}/match", json={"platform": "android", "fix": True}).json()
        assert v["rebuilt"] == [bad] and calls[0][0] == [bad]
        assert "MAKE THIS SCREEN LOOK LIKE ITS APPROVED DESIGN" in calls[0][1][bad] and "violet banner" in calls[0][1][bad]
        got = c.get(f"/api/apps/{aid}/match").json()["match"]["android"]
        assert got["screens"][0]["id"] == bad and got["screens"][0]["design"] == f"{bad}-android.jpg"
        assert c.post(f"/api/apps/{aid}/match", json={"platform": "ios"}).status_code == 400     # no iPhone shots yet
    finally:
        RN.set_runner(None)


def test_after_build_scores_for_free(droid_env, monkeypatch, tmp_path):
    from app.appmaker import match as M
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.site import ai as SA
    aid, conv, good, bad, ids = _setup(droid_env, monkeypatch, tmp_path)
    try:
        monkeypatch.setattr(SA, "ask_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no model after a build")))
        M.after_build(AN.AS._load(aid), "android")
        m = AN.state(AN.AS._load(aid))["match"]["android"]
        assert m["build"] == 1 and set(m["screens"]) == set(ids) and 0 < m["avg"] < 100
    finally:
        RN.set_runner(None)


def test_tool_match(droid_env, monkeypatch, tmp_path):
    from app.agent.app_tools import APP_TOOLS, _act
    from app.agent.tools import Ctx
    from app.appmaker.android import runners as RN
    from app.site import ai as SA
    aid, conv, good, bad, ids = _setup(droid_env, monkeypatch, tmp_path)
    try:
        monkeypatch.setattr(SA, "ask_json", lambda *a, **k: {"score": 4, "differences": ["Match the design's header"]})
        tool = next(t for t in APP_TOOLS if t["name"] == "app_banao")
        assert "match" in tool["input_schema"]["properties"]["action"]["enum"]
        out = _act(Ctx(tenant_id=T, conversation_id=conv), "match", {"app": aid})
        assert out["screens"][0]["id"] == bad and out["rebuilt"] == [] and "design" in out["say"]
    finally:
        RN.set_runner(None)
