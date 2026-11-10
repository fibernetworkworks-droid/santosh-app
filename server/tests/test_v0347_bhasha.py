"""v0.347 BHASHA (App Sahayak Phase 13): her app in her customer's language - every screen word through T(); at build time
the words are collected, new ones translated once per language (cached), the table ships in the app; customers pick on My
account; her data is never translated."""
import json
from pathlib import Path

import pytest

from tests.test_v0314_app_backend import _shop_app
from tests.test_v128_appdesign import T
from tests.test_v132_android import FakeBuild, droid_env  # noqa: F401  (fixture)

FIX = Path(__file__).resolve().parents[1] / "app/appmaker/android/fixture/spec.json"


class FakeTranslate:
    def __init__(self):
        self.calls = []

    def __call__(self, system, prompt, max_tokens=0, kind="", images=None, effort=None):
        words = json.loads(prompt.split("JSON list): ", 1)[1])
        lang = "hi" if "हिन्दी" in system else "mr" if "मराठी" in system else "xx"
        self.calls.append((lang, len(words)))
        out = {w: f"[{lang}] {w}" for w in words}
        if "Book now" in out:
            out["Book now"] = "x" * 500               # a runaway answer is dropped (too long for its English)
        return out


def test_collect_skips_comments_and_reads_kit_words(tmp_path):
    from app.appmaker import i18n as I
    from app.appmaker.android import gen as G
    sp = json.loads(FIX.read_text())
    G.write_project(sp, tmp_path / "a")
    w = I.collect(tmp_path / "a")
    assert "English words" not in w                           # the example in a comment
    assert "Language" in w and "Back" in w and "Open cart" in w
    assert not any("$" in x for x in w)


def test_langs_and_table_cache(droid_env, monkeypatch):
    fake, _kt = droid_env
    from app.appmaker import i18n as I
    from app.site import ai as SA
    aid, conv = _shop_app(fake)
    r = I.AS._load(aid)
    assert I.langs_of(r)[0] == (r.language if r.language in I.LANGS else "en") and "en" in I.langs_of(r)
    with pytest.raises(I.AS.AppError):
        I.set_langs(T, aid, ["klingon"])
    v = I.set_langs(T, aid, ["mr", "hi", "en", "hi", "zz"])
    assert v["langs"][:1] == [I.langs_of(I.AS._load(aid))[0]] and set(v["langs"]) >= {"mr", "hi", "en"}
    ft = FakeTranslate()
    monkeypatch.setattr(SA, "ask_json", ft)
    r = I.AS._load(aid)
    tab = I.table(r, ["Book now", "Our menu", "Open cart"])
    assert tab["t"]["hi"]["Our menu"] == "[hi] Our menu" and "Book now" not in tab["t"]["hi"]   # runaway dropped
    n = len(ft.calls)
    tab2 = I.table(r, ["Our menu", "Open cart", "Track order"])
    assert [c for c in ft.calls[n:] if c[1] != 1] == [] and tab2["t"]["mr"]["Track order"] == "[mr] Track order"   # only the new word
    assert tab2["names"]["hi"] == "हिन्दी" and tab2["default"] == tab2["langs"][0]


def test_android_build_ships_the_table(droid_env, monkeypatch):
    fake, _kt = droid_env
    from app.appmaker import i18n as I
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.site import ai as SA
    aid, conv = _shop_app(fake)
    I.set_langs(T, aid, ["en", "hi"])
    monkeypatch.setattr(SA, "ask_json", FakeTranslate())
    RN.set_runner(FakeBuild())
    try:
        AN.build(T, aid, conv)
        r = AN.AS._load(aid)
        proj = AN._dir(r) / "project"
        tab = json.loads((proj / "app/src/main/assets/i18n.json").read_text())
        assert tab["langs"] == I.langs_of(r) and {"en", "hi"} <= set(tab["langs"]) and tab["t"]["hi"]["Language"] == "[hi] Language"
        assert tab["t"]["hi"].get("Delivered") == "[hi] Delivered"          # order statuses from the app's lists
        st = AN.state(r)["i18n"]
        assert st["words"] > 50 and 0 < st["coverage"]["hi"] <= 100
        main = (proj / "app/src/main/java/hoola/app/MainActivity.kt").read_text()
        assert "I18n.load(this, AppTokens.look.language)" in main and "key(I18n.lang.value)" in main
        assert "Text(T(t.label)" in (proj / "app/src/main/java/hoola/kit/Nav.kt").read_text()
        assert "LanguagePicker()" in (proj / "app/src/main/java/hoola/kit/Accounts.kt").read_text()
    finally:
        RN.set_runner(None)


def test_generators_wrap_words(tmp_path):
    from app.appmaker.android import gen as G
    from app.appmaker.android import prompts as AP
    from app.appmaker.ios import gen as IG
    from app.appmaker.ios import prompts as IP
    s = G.fallback_screen({"id": "home", "label": "Home", "purpose": "Fresh groceries", "actions": [{"label": "Open cart", "go": "cart"}]},
                          ["home", "cart"], ["home"], {})
    assert 'Page(T("Home")' in s and 'Small(T("Fresh groceries"))' in s and 'Btn(T("Open cart")' in s
    sw = IG.code_screen({"id": "home", "label": "Home", "purpose": "Fresh", "actions": [{"label": "Open cart", "go": "cart"}]},
                        ["home", "cart"], ["home"], {})
    assert 'Page(T("Home"))' in sw and 'MainButton(text: T("Open cart")' in sw
    assert 'T("...")' in AP.SCREEN_SYSTEM and 'T("...")' in IP.SCREEN_SYSTEM
    sp = json.loads(FIX.read_text())
    sp["i18n"] = {"default": "en", "langs": ["en", "hi"], "names": {"en": "English", "hi": "हिन्दी"}, "t": {"hi": {"Home": "होम"}}}
    IG.write_project(sp, tmp_path / "i")
    assert json.loads((tmp_path / "i/Resources/i18n.json").read_text())["t"]["hi"]["Home"] == "होम"
    app = (tmp_path / "i/Sources/App/HoolaApp.swift").read_text()
    assert "I18n.shared.load(AppTokens.language)" in app
    kit = (tmp_path / "i/Sources/Kit/Kit.swift").read_text()
    assert ".id(i18n.lang)" in kit and "Label(T(t.label)" in kit
    assert "LanguagePicker()" in (tmp_path / "i/Sources/Kit/Accounts.swift").read_text()


def test_tool_bhasha(droid_env):
    fake, _kt = droid_env
    from app.agent.app_tools import _act
    from app.agent.tools import Ctx
    aid, conv = _shop_app(fake)
    out = _act(Ctx(tenant_id=T, conversation_id=conv), "bhasha", {"app": aid, "langs": ["hi", "ta"]})
    assert "தமிழ்" in out["say"] and "ta" in out["langs"]
