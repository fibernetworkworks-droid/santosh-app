"""v0.128.1 App design system: 12 navigation types, 8 FAB types, 10 card / 9 header / 6 button structures, 40 textures,
100 motion presets, 3D, light + dark for every app, colour harmony from any one colour + 200 palettes, 315 open-licence fonts,
16 styles x 1,000 fields x 10 goals = 1,60,000 briefs. Changes in her words switch structure / mode / fonts without redrawing
screens; colours redraw them. Real Chromium renders the side bar, the speed dial and the other colour mode."""
import re

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v128_appdesign import FakeAI, T

pytest.importorskip("playwright")


@pytest.fixture
def ds_env(env, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DIR", str(tmp_path / "apps"))
    monkeypatch.setenv("APP_WORKER", "false")
    monkeypatch.setenv("APP_FONTS_FETCH", "false")
    monkeypatch.setenv("APP_FONTS_DIR", str(tmp_path / "fonts"))
    from app.appmaker import ai as AI
    class NoBarHome(FakeAI):          # Home without its own action bar, so the FAB shows (a bar hides the FAB)
        def __call__(self, system, prompt, max_tokens=7000):
            out = super().__call__(system, prompt, max_tokens)
            if out.get("html") and 'id="scr-home"' in out["html"]:
                out["html"] = re.sub(r'<div class="bar">.*?</div>', "", out["html"])
            return out
    fake = NoBarHome()
    monkeypatch.setattr(AI, "ask_json", fake)
    monkeypatch.setattr(AI, "ask_edit", fake)
    return fake


def test_catalogues_colours_fonts_and_tokens(monkeypatch):
    monkeypatch.setenv("APP_FONTS_FETCH", "false")
    from app.appmaker import colors as CL
    from app.appmaker import designsys as DS
    from app.appmaker import fonts as FN
    from app.appmaker import kit as K
    from app.appmaker import taxonomy as TX
    from app.brand import rules as BR
    assert DS.check() == [] and TX.check() == []
    c = DS.counts()
    assert c["nav"] == 12 and c["fab"] == 8 and c["textures"] == 40 and c["motion"] == 100
    assert {"drawer", "drawer_bar", "floating_pill", "rail", "top_tabs", "bottom_app_bar"} <= set(DS.NAV)
    assert {"speed_dial", "menu", "docked", "extended"} <= set(DS.FAB) and "glass" in DS.CARDS and "neumorphic" in DS.CARDS
    # every motion has a native hint for Android (Compose) and iOS (SwiftUI)
    assert all(m.get("android") and m.get("ios") for m in DS.MOTION.values())
    # 200 palettes, all readable
    pals = CL.palettes()
    assert len(pals) == 200
    assert all(BR.contrast(p["bg"], p["ink"]) >= 7 for p in pals.values())
    # one colour -> a full palette, light and dark, any scheme
    for sch in CL.SCHEMES:
        for dark in (False, True):
            h = CL.harmony("#E91E63", sch, dark)
            assert BR.contrast(h["bg"], h["ink"]) >= 7 and h["dark"] is dark
    assert CL.find_colors("laal aur neela rang, #00AA88 bhi")[:3] and "#00AA88" in CL.find_colors("#00aa88")
    # fonts: 300+ open-licence families, Indian scripts, pairs
    fc = FN.counts()
    assert fc["families"] >= 300 and fc["pairs"] == 80
    assert FN.find("lexend")["family"] == "Lexend" and FN.families(script="devanagari")
    assert any(f["family"].startswith("Noto Sans Tamil") for f in FN.families(script="tamil"))
    # tokens: structure replaceable, other mode always present, dark asked = dark base
    tk = K.tokens("enterprise_pro", "paper_ink")
    assert tk["nav"] == "drawer_bar" and tk["fab"] == "menu" and tk["alt"]["bg"] and tk["dark"] is False
    tk2 = K.tokens("enterprise_pro", "paper_ink", None, {"nav": "floating_pill", "fab": "speed_dial", "card": "glass",
                                                         "mode": "dark", "font_head": "Lexend", "nav_bad": 1})
    assert (tk2["nav"], tk2["fab"], tk2["card"], tk2["dark"], tk2["head"]) == ("floating_pill", "speed_dial", "glass", True, "Lexend")
    assert K.tokens("enterprise_pro", "paper_ink", None, {"nav": "nonsense"})["nav"] == "drawer_bar"
    # the menu Hoola can read out to her
    from app.agent import app_tools as A

    class _C:
        tenant_id = "default"
    menu = A._read(_C(), "design_system", {"script": "devanagari"})
    assert menu["counts"]["briefs"] == 160000 and "drawer" in menu["nav"] and "speed_dial" in menu["fab"] and menu["fonts"]


def test_structure_change_without_redraw_and_both_modes_rendered(ds_env):
    from app.appmaker import service as S
    from app.main import app
    c = TestClient(app)
    ctx = conv_ctx()
    v = S.new(T, "Patil Traders ka office app, field staff ke kaam aur orders", ctx.conversation_id, name="Patil Traders",
              style="enterprise_pro", answers={"phone": "9876543210", "address": "MIDC, Akola"})
    S.approve_plan(T, v["id"], ctx.conversation_id)
    v = S.choose_look(T, v["id"], 0, None, ctx.conversation_id)
    v = S.get(T, v["id"])
    assert v["status"] == "ready", v.get("error")
    assert v["style"] == "enterprise_pro" and v["design"]["nav"] == "Side bar + bottom bar" and v["design"]["mode"] == "both"
    # both colour modes + the open side bar / FAB menu were rendered in real Chromium
    assert v["board"]["overview"].get("android-alt")
    ex = v["board"]["extras"]
    assert ex.get("drawer-android") and ex.get("fab-android")
    for name in ("home-android-alt.jpg", "overview-android-alt.jpg", ex["drawer-android"]):
        assert c.get(f"/api/apps/{v['id']}/shots/{name}").status_code == 200, name
    tok = v["preview"].rstrip("/").split("/")[-1]
    page = c.get(f"/api/app-preview/{tok}/").text
    assert "nav-drawer_bar" in page and "data-mode" in page and 'class="drawer' in page
    # "side bar hatao, neeche floating bar, dark mode, Lexend font" -> no screen redrawn, new version, same screens
    ds_env.change = {"say": "Theek hai", "structure": {"nav": "floating_pill", "fab": "speed_dial", "mode": "dark",
                                                       "font_head": "Lexend"}}
    n0 = len([x for x in ds_env.calls if x[0] == "screen"])
    S.change(T, v["id"], "side bar hatao, neeche floating bar, dark mode, Lexend font", ctx.conversation_id)
    v2 = S.get(T, v["id"])
    assert [x for x in ds_env.calls[n0:] if x[0] == "screen"] == []
    assert v2["version"] == 2 and v2["status"] == "ready" and v2["design"]["dark"] is True and v2["design"]["fonts"][0] == "Lexend"
    page = c.get(f"/api/app-preview/{tok}/").text
    assert "nav-floating_pill" in page and "fabk-speed_dial" in page and "nav-drawer_bar" not in page
    assert not v2["board"]["overview"].get("android-alt") or v2["design"]["mode"] == "both"
    # a colour mood redraws every screen
    ds_env.change = {"say": "Hara rang", "scheme": "analogous", "tokens": {"primary": "#2E7D32"}}
    n1 = len([x for x in ds_env.calls if x[0] == "screen"])
    S.change(T, v["id"], "hara rang karo, milte julte rang", ctx.conversation_id)
    v3 = S.get(T, v["id"])
    assert len([x for x in ds_env.calls[n1:] if x[0] == "screen"]) == len(v3["plan"]["screens"])
    assert v3["design"]["colors"][2].upper() != v2["design"]["colors"][2].upper() and v3["version"] == 3
