"""v0.752 ARTCRAFT IN CREATE (owner: "now lets develop a artcraft in create section in hoola --- artcraft is already developed
in backend"): the v0.730 shilp lane as a Create studio tool. /api/shilp rides the shilp tool only (its one network seam is
faked here, so nothing leaves the box); Create needs her confirm; a finished file is copied once onto her Create shelf; and
the page is walked in a real browser."""
import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

H = {"Authorization": "Bearer k752"}


@pytest.fixture()
def ac_env(env, monkeypatch):
    monkeypatch.setenv("API_KEY", "k752")
    monkeypatch.setenv("SHILP_PAGE", "true")
    monkeypatch.setenv("ARTCRAFT_API_KEY", "test-key-never-shown")
    from app.config import get_settings
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def client():
    from app.main import app
    return TestClient(app)


class Fake:
    """ArtCraft's Omni API as their doc shows it, recorded."""
    def __init__(self, gen_status=200, state="started", cdn="https://cdn.storyteller.ai/media/x.mp4"):
        self.calls, self.gen_status, self.state, self.cdn = [], gen_status, state, cdn

    def job(self, token):
        st = {"job_token": token, "status": {"status": self.state, "progress_percentage": 40}}
        if self.state == "complete_success":
            st["maybe_result"] = {"entity_token": "m_1", "media_links": {"cdn_url": self.cdn}}
        return st

    async def __call__(self, method, url, *, api_key, json_body=None):
        self.calls.append((method, url, json_body))
        if "/generate/" in url:
            if self.gen_status != 200:
                return self.gen_status, {"success": False}
            return 200, {"success": True, "inference_job_token": "jinf_abc12345", "all_job_tokens": ["jinf_abc12345"]}
        if "/job_status/batch" in url:
            return 200, {"success": True, "job_states": [self.job("jinf_abc12345")]}
        return 200, {"success": True, "state": self.job(url.rsplit("/", 1)[-1])}


def test_switch_off_and_no_key(env, monkeypatch):
    monkeypatch.setenv("API_KEY", "k752")
    from app.config import get_settings
    get_settings.cache_clear()
    with client() as c:
        assert c.get("/api/console/config").json()["artcraft"] is False              # pinned off for old suites
        assert c.get("/api/shilp", headers=H).status_code == 404
    monkeypatch.setenv("SHILP_PAGE", "true")
    get_settings.cache_clear()
    with client() as c:
        o = c.get("/api/shilp", headers=H).json()
        assert o["enabled"] is True and o["key_set"] is False and "ARTCRAFT_API_KEY" in o["setup"]
        assert o["catalog"]["video"] and o["documented_example"] == "seedance_2p0"
        r = c.post("/api/shilp/generate", headers=H, json={"kind": "video", "model": "seedance_2p0", "prompt": "chai", "confirm": True})
        assert r.status_code == 409 and "API key" in r.json()["detail"]
    get_settings.cache_clear()


def test_generate_needs_her_confirm_then_files_land_on_her_shelf(ac_env):
    from app.agent import shilp_tools as SH
    from app.shilp import api as A
    fake = Fake()
    ac_env.setattr(SH, "_http", fake)
    got = []

    async def fetch(url):
        got.append(url)
        return "video/mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 64
    ac_env.setattr(A, "_fetch", fetch)
    with client() as c:
        assert c.get("/api/console/config").json()["artcraft"] is True
        body = {"kind": "video", "model": "seedance_2p0", "prompt": "Steam over a kulhad", "duration_seconds": 5,
                "aspect_ratio": "tall_nine_by_sixteen", "resolution": "seven_twenty_p", "generate_audio": True}
        assert c.post("/api/shilp/generate", headers=H, json=body).status_code == 400 and not fake.calls   # no tap, no spend
        r = c.post("/api/shilp/generate", headers=H, json={**body, "confirm": True}).json()
        assert r["started"][0]["token"] == "jinf_abc12345"
        sent = fake.calls[0][2]
        assert sent["model"] == "seedance_2p0" and sent["duration_seconds"] == 5 and sent["idempotency_token"]
        assert "test-key-never-shown" not in str(r)
        o = c.get("/api/shilp", headers=H).json()
        j = o["jobs"][0]
        assert j["status"] == "started" and j["progress"] == 40 and not j["done"] and not got
        assert o["used_models"] == [{"kind": "video", "model": "seedance_2p0"}]
        fake.state = "complete_success"
        j = c.get("/api/shilp", headers=H).json()["jobs"][0]
        assert j["ok"] and j["item_id"] and got == [fake.cdn]
        items = c.get("/api/create/items", headers=H).json()["items"]
        it = next(i for i in items if i["id"] == j["item_id"])
        assert it["kind"] == "video" and it["meta"]["source"] == "ArtCraft" and it["mime"] == "video/mp4"
        c.get("/api/shilp", headers=H)
        assert got == [fake.cdn]                                                        # copied once, never again
        assert c.post("/api/shilp/jobs/jinf_abc12345/check", headers=H).json()["item_id"] == j["item_id"]
        assert c.delete("/api/shilp/jobs/jinf_abc12345", headers=H).json()["removed"] == "jinf_abc12345"
        assert c.get("/api/shilp", headers=H).json()["jobs"] == []
        assert any(i["id"] == j["item_id"] for i in c.get("/api/create/items", headers=H).json()["items"])   # the file stays
        assert c.post("/api/shilp/jobs/jinf_zzzz9999/check", headers=H).status_code == 404


def test_refusals_said_plainly_and_nothing_kept(ac_env):
    from app.agent import shilp_tools as SH
    fake = Fake(gen_status=402)
    ac_env.setattr(SH, "_http", fake)
    with client() as c:
        r = c.post("/api/shilp/generate", headers=H, json={"kind": "image", "model": "nano_banana", "prompt": "a diya", "confirm": True})
        assert r.status_code == 402 and "credits" in r.json()["detail"]
        assert c.get("/api/shilp", headers=H).json()["jobs"] == []
        n = len(fake.calls)
        r = c.post("/api/shilp/generate", headers=H, json={"kind": "image", "model": "nano_banana", "prompt": "a diya",
                                                           "image_urls": ["http://192.168.1.4/me.png"], "confirm": True})
        assert r.status_code == 400 and len(fake.calls) == n                           # the wall stops it before ArtCraft
        r = c.post("/api/shilp/generate", headers=H, json={"kind": "video", "model": "seedance_2p0", "prompt": " ", "confirm": True})
        assert r.status_code == 400


def test_a_private_file_link_is_never_fetched(ac_env):
    import asyncio
    from app.shilp import api as A
    called = []

    async def fetch(url):
        called.append(url)
        return "video/mp4", b"x"
    ac_env.setattr(A, "_fetch", fetch)
    A._write("default", [{"token": "jinf_abc12345", "kind": "video", "cdn_url": "https://127.0.0.1/x.mp4", "ok": True, "done": True}])
    j = asyncio.run(A._save("default", A._read("default")[0]))
    assert not called and "loopback" in j["save_error"] and not j.get("item_id")


def test_studio_wiring():
    from pathlib import Path
    st = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    js, v2 = (st / "studio.js").read_text(), (st / "v2.js").read_text()
    assert "V.artcraft = " in js and "W.artcraft = " in js and "/api/shilp/generate" in js and "confirm: true" in js
    assert "ctx.artcraft?.() ? [...TOOLS, ['artcraft'" in js and "artcraft: () => !!CONFIG?.artcraft" in v2


OV = {"enabled": True, "key_set": True, "setup": "", "lane_error": "", "documented_example": "seedance_2p0",
      "counts": {"video": 28, "image": 16}, "catalog": {"video": {"Seedance": ["Seedance 2.0"], "Kling": ["Kling 2.6 Pro"]},
                                                         "image": {"FLUX": ["FLUX 1.1 [pro]"]}},
      "used_models": [{"kind": "video", "model": "seedance_2p0"}], "refresh_error": "",
      "jobs": [{"token": "jinf_run00001", "kind": "video", "model": "seedance_2p0", "prompt": "Steam over a <b>kulhad</b>",
                "status": "started", "progress": 40, "done": False, "ok": False, "created": 1794300000},
               {"token": "jinf_bad00001", "kind": "image", "model": "flux_pro", "prompt": "A diya", "status": "complete_failure",
                "progress": None, "done": True, "ok": False, "failure": "content_policy", "created": 1794300000}]}


def test_the_artcraft_tool_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}'); sessionStorage.setItem('hoola.create.view', 'artcraft')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/api/console/config", lambda r: r.fulfill(json={"app": "Hoola", "v2": True, "stream": True, "sessions": True,
                                                                   "panel": True, "projects": True, "human": True, "artcraft": True}))
    pg.route("**/api/shilp", lambda r: r.fulfill(json=OV))
    pg.route("**/api/create/items*", lambda r: r.fulfill(json={"items": []}))
    sent = []
    pg.route("**/api/shilp/generate", lambda r: (sent.append(r.request.post_data_json), r.fulfill(json={"started": []})))
    pg.goto(base + "/console/")
    pg.wait_for_selector("#composer")
    pg.locator(".sn[data-v='creative']").click()
    pg.wait_for_selector("#cstudio button.sn[data-go='artcraft']")
    pg.locator("#cstudio button.sn[data-go='artcraft']").click()
    pg.wait_for_selector("#cstudio #acres .res")
    t = pg.locator("#cstudio .gen").text_content()
    assert "ArtCraft" in t and "Your ArtCraft credits" in t and "40%" in t and "content_policy" in t and "<b>kulhad</b>" in t
    assert pg.locator("#cstudio #acm").input_value() == "seedance_2p0"
    pg.locator("#cstudio #acq").fill("Rain on a Mumbai balcony")
    pg.locator("#cstudio [data-acasp='tall_nine_by_sixteen']").click()
    pg.on("dialog", lambda d: d.accept())
    pg.locator("#cstudio #acGo").click()
    pg.wait_for_timeout(600)
    assert sent and sent[0]["confirm"] is True and sent[0]["aspect_ratio"] == "tall_nine_by_sixteen" and sent[0]["model"] == "seedance_2p0"
    pg.locator("#cstudio [data-ackind='image']").click()
    pg.wait_for_selector("#cstudio [data-ackind='image'][aria-pressed='true']")
    assert "FLUX" in pg.locator("#cstudio .gen").text_content() and pg.locator("#cstudio #acsec").count() == 0
    assert not errs, errs
    ctx.close()
