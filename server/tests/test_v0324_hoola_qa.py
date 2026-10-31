"""v0.324 HOOLA QA (App Sahayak Phase 3): the device check after every build (every screen opened on an emulator,
crash -> back to Opus with the real crash, accessibility, cold start / scrolling / APK size budget), crash reports from
real users' phones (grouped, a chat note, "crash theek karo" rewrites those screens), and the views. device_check.sh
itself runs on a real emulator in CI (appgen-check.yml) on the fixture app; here its report parser is fed real-shaped
output and the build loop gets a fake device check."""
import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _shop_app
from tests.test_v128_appdesign import T
from tests.test_v132_android import FakeBuild, droid_env  # noqa: F401  (fixture)

UI = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><hierarchy rotation="0">
<node index="0" text="" class="android.widget.FrameLayout" clickable="false" enabled="true" bounds="[0,0][1080,2400]">
 <node index="1" text="Place order" content-desc="" class="android.widget.Button" clickable="true" enabled="true" bounds="[40,2100][1040,2247]"/>
 <node index="2" text="" content-desc="" class="android.view.View" clickable="true" enabled="true" bounds="[900,120][1040,260]"/>
 <node index="3" text="" content-desc="Cart" class="android.view.View" clickable="true" enabled="true" bounds="[960,300][1040,360]"/>
 <node index="4" text="" content-desc="" class="android.view.View" clickable="true" enabled="true" bounds="[40,400][1040,560]">
   <node index="0" text="Atta 5 kg" class="android.widget.TextView" clickable="false" enabled="true" bounds="[60,420][600,480]"/>
 </node>
</node></hierarchy>"""
CRASH = """--------- beginning of crash
10-31 09:12:01.123  4321  4321 E AndroidRuntime: FATAL EXCEPTION: main
10-31 09:12:01.123  4321  4321 E AndroidRuntime: Process: in.hoola.preview.fixture, PID: 4321
10-31 09:12:01.123  4321  4321 E AndroidRuntime: java.lang.IndexOutOfBoundsException: Index 0 out of bounds for length 0
10-31 09:12:01.123  4321  4321 E AndroidRuntime: \tat java.util.ArrayList.get(ArrayList.java:437)
10-31 09:12:01.123  4321  4321 E AndroidRuntime: \tat hoola.app.screens.ScreenCartKt.ScreenCart(ScreenCart.kt:42)
10-31 09:12:01.123  4321  4321 E AndroidRuntime: \tat hoola.kit.KitKt.Page(Kit.kt:120)
"""
GFX = "Stats since: 1s\nTotal frames rendered: 240\nJanky frames: 30 (12.50%)\n50th percentile: 9ms\n"


def _device_dir(tmp_path: Path, crash_on: str = "") -> Path:
    out = tmp_path / "qa"
    (out / "screens").mkdir(parents=True)
    (out / "density.txt").write_text("420\n")
    lines = []
    for sid in ("home", "cart", "hoola_account"):
        (out / "screens" / f"{sid}.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 2000)
        (out / "screens" / f"{sid}.xml").write_text(UI)
        (out / "screens" / f"{sid}.crash.txt").write_text(CRASH if sid == crash_on else "")
        lines.append(f"{sid} {0 if sid == crash_on else 1}")
    (out / "opened.txt").write_text("\n".join(lines) + "\n")
    (out / "cold.txt").write_text("812\n640\n655\n")
    (out / "gfxinfo.txt").write_text(GFX)
    (out / "apk_bytes.txt").write_text(str(int(4.2 * 1048576)))
    return out


def test_report_parser_crash_a11y_budget(tmp_path):
    from app.appmaker.android import qa as Q
    rep = Q.report(_device_dir(tmp_path))
    assert rep["passed"] and rep["opened"] == 3 and rep["crashed"] == []
    assert rep["perf"] == {"cold_ms": 655, "cold_all": [812, 640, 655], "jank_pct": 12.5, "frames": 240, "apk_mb": 4.2}
    assert rep["budget"] == {"cold_ms": "ok", "apk_mb": "ok", "jank_pct": "ok"}
    f = rep["screens"]["home"]["a11y"]
    kinds = sorted((x["kind"], x["text"][:24]) for x in f)
    # node 2: no words at all -> unlabelled; node 3: 80x60 px at 420 dpi = 30x23 dp -> small; node 1 / 4 are fine
    # (node 4 gets its words from its child text)
    assert [k for k, _ in kinds].count("unlabelled") == 1 and [k for k, _ in kinds].count("small_target") == 1
    assert "Cart" in next(x["text"] for x in f if x["kind"] == "small_target")
    assert (tmp_path / "qa" / "report.json").exists() and "PASS" in Q.summary(rep)
    # a crash: the exception, the app frames, the screen class; the build is not passed
    bad = Q.report(_device_dir(tmp_path / "b", crash_on="cart"))
    c = bad["screens"]["cart"]["crash"]
    assert not bad["passed"] and bad["crashed"] == ["cart"]
    assert c["exception"].startswith("java.lang.IndexOutOfBoundsException") and c["screen_class"] == "ScreenCart"
    assert c["frames"][0].startswith("at hoola.app.screens.ScreenCartKt") and "FAIL" in Q.summary(bad)
    # over budget
    (tmp_path / "qa" / "cold.txt").write_text("2400\n2600\n2500\n")
    assert Q.report(tmp_path / "qa")["budget"]["cold_ms"] == "over"
    # the script and the parser travel with every generated project
    from app.appmaker.android import gen as G
    spec = json.loads((Path(G.__file__).parent / "fixture" / "spec.json").read_text())
    proj = tmp_path / "proj"
    G.write_project(spec, proj)
    assert (proj / "hoola_qa/device_check.sh").stat().st_mode & 0o111 and (proj / "hoola_qa/qa.py").exists()
    assert (proj / "hoola_qa/package.txt").read_text().strip() == "in.hoola.preview.fixture"
    shots = (proj / "hoola_qa/screens.txt").read_text().split()
    assert "home" in shots and "hoola_account" in shots and "login" not in shots
    main = (proj / "app/src/main/java/hoola/app/MainActivity.kt").read_text()
    assert "CrashGuard.install(this, BuildConfig.VERSION_NAME)" in main and "CrashGuard.sendPending(this)" in main
    assert "CrashGuard.screen = id" in main


class QaBuild(FakeBuild):
    """A build machine with an emulator: the cart screen crashes on the device until its code changes."""
    def __init__(self, tmp: Path, crash_rounds: int = 1):
        super().__init__()
        self.tmp, self.crash_rounds, self.good = tmp, crash_rounds, 0

    def __call__(self, src: Path, key: str, progress):
        res = super().__call__(src, key, progress)
        if not res.get("ok"):
            return res
        self.good += 1                                   # only builds that compiled reach the device
        crash = "cart" if self.good <= self.crash_rounds else ""
        d = _device_dir(self.tmp / f"b{self.builds}", crash_on=crash)
        from app.appmaker.android import qa as Q
        Q.report(d)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.write(d / "report.json", "qa/report.json")
            for p in (d / "screens").glob("*.png"):
                z.write(p, f"qa/screens/{p.name}")
        from app.appmaker.android import runners as RN
        res["qa"] = RN.qa_from_zip(buf.getvalue())
        return res


def test_build_device_check_fix_loop_and_views(droid_env, tmp_path):
    fake, kt = droid_env
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.main import app
    c = TestClient(app)
    aid, conv = _shop_app(fake)
    qb = QaBuild(tmp_path, crash_rounds=1)
    RN.set_runner(qb)
    n0 = len(kt.calls)
    AN.build(T, aid, conv)
    v = AN.get(T, aid)
    assert v["status"] == "ready", v
    calls = kt.calls[n0:]
    assert calls.count(("fix", "cart")) >= 2            # the compile fix + the CRASH fix (with the real crash in the ask)
    qa = v["qa"]
    assert qa["ran"] and qa["passed"] and qa["opened"] == 3 and qa["crashed"] == []
    assert qa["perf"]["cold_ms"] == 655 and qa["a11y_count"] > 0 and "home" in qa["shots"]
    shot = c.get(f"/api/apps/{aid}/android/qa/home")
    assert shot.status_code == 200 and shot.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert c.get(f"/api/apps/{aid}/android/qa/Bad.Name").status_code == 404
    assert c.get(f"/api/apps/{aid}/android/qa/nosuchscreen").status_code == 404
    from app.db import Message, session
    with session() as s:
        ready = [m.content for m in s.query(Message).filter(Message.conversation_id == conv).all() if "Android app taiyaar" in str(m.content)]
    assert ready and "Device check: 3/3" in ready[-1]
    # a build machine without an emulator: said plainly
    RN.set_runner(FakeBuild())
    AN.build(T, aid, conv)
    q2 = AN.get(T, aid)["qa"]
    assert q2["ran"] is False and "emulator" in q2["why"]
    # a screen that keeps crashing ships as its simple version
    RN.set_runner(QaBuild(tmp_path / "x", crash_rounds=99))
    AN.build(T, aid, conv, ["cart"])
    v3 = AN.get(T, aid)
    assert {s["id"]: s["state"] for s in v3["screens"]}["cart"] == "code"


def test_crash_reports_grouped_noted_and_fixed(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.main import app
    import asyncio
    from app.agent.tools import Ctx, dispatch
    c = TestClient(app)
    fake, kt = droid_env
    aid, conv = _shop_app(fake)
    RN.set_runner(FakeBuild())
    AN.build(T, aid, conv)
    from app.appmaker.models import AppProject
    from app.db import Message, session
    with session() as s:
        key = json.loads(s.get(AppProject, aid).android)["app_key"]
    trace = ("java.lang.IndexOutOfBoundsException: Index 0 out of bounds for length 0\n\tat java.util.ArrayList.get(ArrayList.java:437)\n"
             "\tat hoola.app.screens.ScreenCartKt.ScreenCart(ScreenCart.kt:42)\n\tat hoola.kit.KitKt.Page(Kit.kt:120)")
    body = {"trace": trace, "screen": "cart", "ver": "1.2", "android": 34, "model": "Xiaomi Redmi 13"}
    a = c.post(f"/api/app-api/{key}/crash", json=body).json()
    b = c.post(f"/api/app-api/{key}/crash", json={**body, "trace": trace.replace("ScreenCart.kt:42", "ScreenCart.kt:57"),
                                                  "model": "Samsung A15"}).json()
    assert a["new"] is True and b["new"] is False and a["id"] == b["id"]          # line numbers move; same crash
    assert c.post(f"/api/app-api/{key}/crash", json={"trace": ""}).status_code == 400
    cr = c.get(f"/api/apps/{aid}/crashes").json()["crashes"]
    assert len(cr) == 1 and cr[0]["count"] == 2 and cr[0]["screens"] == ["cart"] and len(cr[0]["devices"]) == 2
    assert cr[0]["exception"].startswith("java.lang.IndexOutOfBoundsException")
    with session() as s:
        notes = [m.content for m in s.query(Message).filter(Message.conversation_id == conv).all() if "band ho gayi" in str(m.content)]
    assert len(notes) == 1 and "crash theek karo" in notes[0]
    # tools: she reads them and says "crash theek karo": the cart screen is rewritten with the crash in the ask
    owner = Ctx(tenant_id=T, conversation_id=conv)
    seen = asyncio.run(dispatch("app_dekho", {"what": "crashes", "app": aid}, owner))
    assert seen["crashes"][0]["count"] == 2
    n0 = len(kt.calls)
    out = asyncio.run(dispatch("app_banao", {"action": "fix_crash", "app": aid}, owner))
    assert out["screens"] == ["cart"] and "cart" in out["say"]
    assert ("screen", "cart") in kt.calls[n0:] and ("screen", "home") not in kt.calls[n0:]
    st = BE.crashes(BE.by_key_or_ref(T, aid))[0]
    assert st["status"] == "fixing" and st["fix_build"] >= 2 and st["fix_version"]
    # the same crash in the build meant to fix it: "back", and she hears it once more
    c.post(f"/api/app-api/{key}/crash", json={**body, "ver": st["fix_version"]})
    assert BE.crashes(BE.by_key_or_ref(T, aid))[0]["status"] == "back"
    with session() as s:
        notes = [m.content for m in s.query(Message).filter(Message.conversation_id == conv).all() if "band ho gayi" in str(m.content)]
    assert len(notes) == 2 and "fix wali build" in notes[-1]
    # a crash inside Hoola's own kit (no app screen in it) is not hers to fix
    kit_trace = "java.lang.IllegalStateException: boom\n\tat hoola.kit.Db.sync(Backend.kt:300)"
    k = c.post(f"/api/app-api/{key}/crash", json={"trace": kit_trace, "screen": ""}).json()
    r = asyncio.run(dispatch("app_banao", {"action": "fix_crash", "app": aid, "crash": k["id"]}, owner))
    assert "kit" in r["say"]
    # the phone / console tap goes through the same path
    assert c.post(f"/api/apps/{aid}/fix_crash", json={"crash": "c_000000000000"}).status_code == 400
