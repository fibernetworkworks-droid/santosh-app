"""v0.132 App Sahayak part 4: the native Android build of an approved design (Kotlin + Jetpack Compose). Generator, house
rules for model-written screens, compile-error parser, the fix loop on a fake build machine (fix round, same-error stop,
code-made screen), APK link + project ZIP, public content, tools. The real Gradle compile is checked in CI
(.github/workflows/appgen-check.yml) on the fixture project."""
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v128_appdesign import FakeAI, T

GOOD = """package hoola.app.screens

import androidx.compose.runtime.Composable
import hoola.kit.*

@Composable
fun {FN}() {{
    val nav = LocalNav.current
    Page("{SID}", back = {BACK}) {{
        block {{ Title("Hello {SID}") }}
        AppData.list("products").forEach {{ p -> block {{ HCard(onClick = {{ nav.go("{GO}") }}) {{ Title(p.name); Price(p.price) }} }} }}
    }}
}}
"""


def fn_of(system):
    return re.search(r"@Composable fun (Screen\w+)\(\)", system).group(1)


class FakeKotlin:
    """Opus stand-in: good screens, a cart that needs one fix round, orders that keep breaking a house rule, profile that
    keeps the same compile error (-> code-made screen)."""
    def __init__(self):
        self.calls = []

    def __call__(self, system, prompt):
        fn = fn_of(system)
        sid = re.sub(r"(?<!^)([A-Z])", r"_\1", fn[6:]).lower()
        fix = system.startswith("You fix ONE")
        self.calls.append(("fix" if fix else "screen", sid))
        back = "false" if "back = false" in system else "true"
        src = GOOD.format(FN=fn, SID=sid, BACK=back, GO="home")
        if sid == "orders":
            return src.replace('Title("Hello orders")', 'TextField(value = "", onValueChange = {}, visualTransformation = PasswordVisualTransformation())')
        if sid == "cart" and not fix:
            return src.replace('Title("Hello cart")', 'Title(BROKEN_cart)')
        if sid == "profile":
            return src.replace('Title("Hello profile")', 'Title(BROKEN_profile)')
        return src


class FakeBuild:
    """Build machine stand-in: Kotlin errors for screens that still contain BROKEN, else an APK."""
    def __init__(self):
        self.builds = 0

    def __call__(self, src: Path, key: str, progress):
        self.builds += 1
        progress("compiling")
        errs = []
        for f in sorted((src / "app/src/main/java/hoola/app/screens").glob("*.kt")):
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if "BROKEN_" in line:
                    errs.append(f"e: file://{f}:{i}:{line.index('BROKEN_') + 1} Unresolved reference 'BROKEN_x'.")
        assert (src / "keys/preview.p12").exists() and (src / "app/src/main/assets/seed.json").exists()
        if errs:
            return {"ok": False, "log": "\n".join(errs) + "\nFAILURE: Build failed with an exception.\n", "apk": None, "seconds": 3,
                    "where": "fake"}
        apk = BytesIO()
        with zipfile.ZipFile(apk, "w") as z:
            z.writestr("AndroidManifest.xml", "fake")
            z.writestr("classes.dex", "dex")
        return {"ok": True, "log": "BUILD SUCCESSFUL in 41s", "apk": apk.getvalue(), "seconds": 41, "where": "fake"}


@pytest.fixture
def droid_env(env, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DIR", str(tmp_path / "apps"))
    monkeypatch.setenv("APP_WORKER", "false")
    monkeypatch.setenv("APP_FONTS_FETCH", "false")
    monkeypatch.setenv("APP_FONTS_DIR", str(tmp_path / "fonts"))
    from app.appmaker import ai as AI
    fake = FakeAI()
    monkeypatch.setattr(AI, "ask_json", fake)
    monkeypatch.setattr(AI, "ask_edit", fake)
    from app.appmaker.android import service as AN
    kt = FakeKotlin()
    monkeypatch.setattr(AN, "_ask", kt)
    yield fake, kt
    from app.appmaker.android import runners as RN
    RN.set_runner(None)


def _approved_app(fake):
    from app.appmaker import service as S
    ctx = conv_ctx()
    v = S.new(T, "Sharma Sweets ki app, ghar pe delivery", ctx.conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main road, Akot", "upi_id": "sharma@okicici"})
    S.approve_plan(T, v["id"], ctx.conversation_id)
    S.choose_look(T, v["id"], 1, 0, ctx.conversation_id)
    v = S.get(T, v["id"])
    assert v["status"] == "ready", v.get("error")
    S.approve(T, v["id"], v["hash"])
    return v["id"], ctx.conversation_id


# ---------------------------------------------------------------- 1. generator, icons, rules, errors (no server state)
def test_generator_rules_and_errors(tmp_path):
    from app.appmaker import kit as K
    from app.appmaker.android import errors as ER
    from app.appmaker.android import gen as G
    from app.appmaker.android import prompts as PR
    from app.appmaker.android import spec as SP
    # icons: every design icon becomes Compose path data; circles + rounded rects as paths
    ic = SP.icon_paths()
    assert set(ic) == set(K.ICONS) and all(ic[n] for n in ic)
    assert SP.svg_to_paths('<circle cx="12" cy="12" r="3"/>') == ["M9 12a3 3 0 1 0 6 0a3 3 0 1 0 -6 0z"]
    assert SP.svg_to_paths('<rect x="3" y="5" width="18" height="16" rx="2"/>')[0].startswith("M5 5h14a2 2")
    # the fixture project (what CI compiles) generates every file; hand-written screens kept, others code-made
    spec = json.loads((Path(G.__file__).parent / "fixture/spec.json").read_text())
    res = G.write_project(spec, tmp_path / "proj")
    p = tmp_path / "proj"
    assert res["screens"]["home"] == "model" and res["screens"]["orders"] == "code" and res["app_id"] == "in.hoola.preview.fixture"
    for f in ("settings.gradle.kts", "gradlew", "gradle/wrapper/gradle-wrapper.jar", "app/build.gradle.kts", "app/src/main/AndroidManifest.xml",
              "app/src/main/java/hoola/app/MainActivity.kt", "app/src/main/java/hoola/app/AppScreens.kt", "app/src/main/java/hoola/kit/Icons.kt",
              "app/src/main/assets/seed.json", "app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml"):
        assert (p / f).exists(), f
    assert (p / "gradlew").stat().st_mode & 0o111
    bg = (p / "app/build.gradle.kts").read_text()
    assert 'applicationId = "in.hoola.preview.fixture"' in bg and "@@" not in bg
    man = (p / "app/src/main/AndroidManifest.xml").read_text()
    assert "android.permission.INTERNET" in man and "READ_SMS" not in man and "cleartext" not in man.lower()
    assert 'cleartextTrafficPermitted="false"' in (p / "app/src/main/res/xml/network_security_config.xml").read_text()
    reg = (p / "app/src/main/java/hoola/app/AppScreens.kt").read_text()
    for sid in ("home", "cart", "orders", "seller_info", "privacy", "delete_account"):
        assert f'"{sid}" ->' in reg
    seed = json.loads((p / "app/src/main/assets/seed.json").read_text())
    assert seed["facts"]["upi_id"] == "sharmakirana@okicici" and seed["facts"]["privacy"] and "orders" in seed["demo_lists"]
    with pytest.raises(ValueError):
        G.write_project({**spec, "app": {**spec["app"], "app_id": "bad id"}}, tmp_path / "x")
    # house rules on a model-written screen
    ids = ["home", "cart"]
    ok = GOOD.format(FN="ScreenHome", SID="home", BACK="false", GO="cart")
    assert G.scan_screen(ok, "home", ids) == []
    bad = (ok.replace("import hoola.kit.*", "import hoola.kit.*\nimport java.net.URL\nimport androidx.compose.material.Button")
              .replace('nav.go("cart")', 'nav.go("nowhere")') + "\nval x = PasswordVisualTransformation()\nval n = rememberNavController()\n")
    probs = " | ".join(G.scan_screen(bad, "home", ids))
    for w in ("java.net.URL", "Material 2", "password", "nowhere", "NavHost"):
        assert w in probs, w
    assert G.scan_screen(ok.replace("fun ScreenHome()", "fun ScreenHome(x: Int)"), "home", ids)
    # the code-made screen always follows the contract
    fb = G.fallback_screen({"id": "orders", "label": "Orders", "lists": ["orders"], "actions": [{"label": "Cart", "go": "cart"}]}, ids + ["orders"], ["home"])
    assert G.scan_screen(fb, "orders", ids + ["orders"]) == []
    # the kit sheet the model gets = the kit's real signatures
    sheet = PR.kit_sheet()
    for w in ("@Composable Page(", "@Composable Btn(", "AppData.list(name: String)", "Nav.open(id: String", "Act.payUpi("):
        assert w in sheet, w
    assert "DemoNote" not in sheet and "private" not in sheet
    assert PR.code_of("ok\n```kotlin\npackage hoola.app.screens\nfun a() {}\n```\nthanks").startswith("package hoola.app.screens")
    # Kotlin errors -> per screen / ours
    log = ("e: file:///w/app/src/main/java/hoola/app/screens/ScreenCart.kt:12:5 Unresolved reference 'Foo'.\n"
           "e: file:///w/app/src/main/java/hoola/app/screens/ScreenCart.kt:20:9 Type mismatch.\n"
           "e: /w/app/src/main/java/hoola/kit/Kit.kt: (3, 1): Something\nFAILURE: Build failed\n* What went wrong:\n")
    e = ER.parse(log)
    assert [x["line"] for x in e["screens"]["ScreenCart"]] == [12, 20] and e["project"] and not e["ok"]
    assert "line 12:5: Unresolved reference" in ER.for_model(e["screens"]["ScreenCart"], "\n" * 11 + "Foo()\n")
    assert ER.signature(e["screens"]["ScreenCart"]) == ER.signature([{"msg": "Type mismatch."}, {"msg": "Unresolved reference 'Foo'."}])


# ---------------------------------------------------------------- 2. approved design -> screens -> fix loop -> APK -> phone
def test_build_flow_fix_loop_apk_and_content(droid_env):
    fake, kt = droid_env
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.main import app
    c = TestClient(app)
    aid, conv = _approved_app(fake)
    # not approved -> refused; approved + no build machine -> the project ZIP only
    v = c.get(f"/api/apps/{aid}/android").json()
    assert v["status"] == "" and v["runner"]["ready"] is False and v["approved"] is True
    out = c.post(f"/api/apps/{aid}/android", json={"conversation_id": conv}).json()
    assert out["status"] == "zip", out
    v = c.get(f"/api/apps/{aid}/android").json()
    assert v["zip"] and v["zip_url"] and not v["apk"]
    r = c.get(v["zip_url"].replace("http://testserver", ""))
    assert r.status_code == 200
    with zipfile.ZipFile(BytesIO(r.content)) as z:
        names = z.namelist()
        assert "gradlew" in names and "app/src/main/java/hoola/app/screens/ScreenHome.kt" in names
        assert not any(n.startswith("keys/") for n in names)                   # her download never carries the signing key
        assert re.search(r'\?: "[A-Za-z0-9]{8,}"', z.read("app/build.gradle.kts").decode()) is None
    assert c.get(f"/api/apps/{aid}/android/zip").status_code == 200
    # with a build machine: cart fixed in one round, profile keeps failing -> code-made, orders broke a rule -> code-made
    fb = FakeBuild()
    RN.set_runner(fb)
    n0 = len(kt.calls)
    out = AN.build(T, aid, conv)
    v = AN.get(T, aid)
    assert v["status"] == "ready", v
    st = {s["id"]: s["state"] for s in v["screens"]}
    assert st["cart"] == "done" and st["profile"] == "code" and st["orders"] == "code" and st["home"] == "done"
    calls = kt.calls[n0:]
    assert ("fix", "cart") in calls and ("fix", "orders") in calls                # house-rule fix asked once
    assert calls.count(("fix", "profile")) == 1                                  # same error again -> no more rounds
    assert fb.builds == 3 and v["rounds"] == 2 and v["stats"]["code"] == 2
    apk = v["apk"]
    assert apk["package"].startswith("in.hoola.preview.a") and len(apk["sha256"]) == 64 and apk["size"] > 0
    # the phone's installer link: public by token, exact file, nothing else
    path = v["apk_url"].replace("http://testserver", "")
    r = c.get(path)
    assert r.status_code == 200 and r.headers["content-type"] == "application/vnd.android.package-archive"
    import hashlib
    assert hashlib.sha256(r.content).hexdigest() == apk["sha256"]
    assert c.get(path.replace(apk["file"], "other.apk")).status_code == 404
    assert c.get("/api/app-apk/short/x.apk").status_code == 404
    assert c.get(f"/api/apps/{aid}/android/apk").status_code == 200
    # the same preview key every build (installs over the old one); sealed on disk, not plain
    from app.appmaker import kit as K
    from app.appmaker import service as S
    with __import__("app.db", fromlist=["session"]).session() as s:
        from app.appmaker.models import AppProject
        row = s.get(AppProject, aid)
        sealed = (K.app_dir(row.tenant_id, aid) / "android" / "preview.key.sealed").read_text()
        key = json.loads(row.android)["app_key"]
    assert "p12_b64" not in sealed
    # cached screens: a second build doesn't ask the model again for the good ones
    n1 = len(kt.calls)
    AN.build(T, aid, conv)
    again = [x for x in kt.calls[n1:] if x[0] == "screen"]
    assert ("screen", "home") not in again and AN.get(T, aid)["build"] == 3
    # public content for the installed app: her public facts + products, samples marked; nothing private
    d = c.get(f"/api/app-content/{key}").json()
    assert d["facts"]["name"] == "Sharma Sweets" and d["facts"]["upi_id"] == "sharma@okicici" and d["facts"]["privacy"]
    assert "orders" in d["demo_lists"] or d["lists"]
    assert c.get("/api/app-content/akwrong").status_code == 404
    # events + push line
    from tests.test_v128_appdesign import _events
    ev = _events("app_android")
    assert ev and ev[-1]["status"] == "ready" and ev[-1]["push"] is True
    from app.push import render
    assert "Android app" in render("app_android", ev[-1], "Santosh")[0]


def test_tools_and_guards(droid_env):
    fake, kt = droid_env
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.appmaker import service as S
    from app.appmaker.android import service as AN
    import asyncio
    ctx = conv_ctx()
    v = S.new(T, "chai ki dukaan ki app", ctx.conversation_id, name="Chai Point")
    with pytest.raises(S.AppError):                                              # only an approved design is built
        AN.build(T, v["id"], ctx.conversation_id)
    aid, conv = _approved_app(fake)
    c2 = Ctx(tenant_id=T, conversation_id=conv, actor="owner")
    out = asyncio.run(dispatch("app_banao", {"action": "android", "app": aid}, c2))
    assert out["status"] in ("zip", "ready") and "poll" in out["say"]
    r = asyncio.run(dispatch("app_dekho", {"what": "android", "app": aid}, c2))
    assert r["zip"] is True and r["screens"]


def test_build_worker_signing_and_safe_extract(tmp_path, monkeypatch):
    """The build machine (server/app_builder/worker.py): HMAC like the server's runner, zips only into its folder."""
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("hoola_worker", Path(__file__).resolve().parents[1] / "app_builder/worker.py")
    W = importlib.util.module_from_spec(spec)
    sys.modules["hoola_worker"] = W
    spec.loader.exec_module(W)
    from app.appmaker.android import runners as RN
    W.SECRET = "s" * 30
    body = b"zipbytes"
    assert W.sign("POST", "/build?app=abcd", "1700000000", body) == RN.sign("s" * 30, "POST", "/build?app=abcd", "1700000000", body)
    def mk(entries):
        b = BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            for n, d in entries:
                z.writestr(n, d)
        return b.getvalue()
    dest = tmp_path / "app1"
    (dest / "app/src/old").mkdir(parents=True)
    (dest / "app/src/old/Stale.kt").write_text("x")
    (dest / ".gradle").mkdir()
    W.safe_extract(mk([("gradlew", "#!/bin/sh"), ("app/src/main/A.kt", "package a")]), dest)
    assert (dest / "app/src/main/A.kt").exists() and not (dest / "app/src/old/Stale.kt").exists() and (dest / ".gradle").exists()
    assert (dest / "gradlew").stat().st_mode & 0o111
    for bad in ("../evil.kt", "/etc/x", "a/../../b"):
        with pytest.raises(ValueError):
            W.safe_extract(mk([(bad, "x")]), dest)
    # the server's export zip never carries the signing key; the build zip does
    proj = tmp_path / "p"
    (proj / "keys").mkdir(parents=True)
    (proj / "keys/preview.p12").write_bytes(b"k")
    (proj / "app").mkdir()
    (proj / "app/build.gradle.kts").write_text('storePassword = System.getenv("X") ?: "abc123def456"')
    full = zipfile.ZipFile(BytesIO(RN.zip_project(proj)))
    exp = zipfile.ZipFile(BytesIO(RN.zip_project(proj, export=True)))
    assert "keys/preview.p12" in full.namelist() and "keys/preview.p12" not in exp.namelist()
    assert b"abc123def456" not in exp.read("app/build.gradle.kts")
