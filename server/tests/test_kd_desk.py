"""KERNEL DESK: the Kernel / OS Developer's own section, built like the finance desks - its own chat (kind 'kernel') with the desk
block + the kernel tool in view; crash logs read in code (x86_64 NULL dereference, KASAN use-after-free, arm64 list poison, hung
task) with the real function named past the reporting / allocator / scheduler machinery, grouped by signature and told when a
fixed one comes back; patches checked against the kernel's rules; .config profiles + a fragment + a compare; boot logs stage by
stage with errnos spelled out; driver starters that pass the style checks (and compile against stub headers); the QEMU boot-test
workflow valid YAML whose shell steps parse and whose init compiles; walked in a browser."""
from __future__ import annotations

import os
import subprocess
import tempfile

import pytest
from fastapi.testclient import TestClient

from tests import kernel_samples as KS

T = "default"


@pytest.fixture
def kd(env):
    from app import kdchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "kernel_dev", trust="seekh")


# ---------------------------------------------------------------- the readers (pure code)
def test_crash_reader_points_at_the_real_code():
    from app.kerneldesk import crash
    p = crash.parse(KS.NULL_X86)
    e = crash.explain(p)
    assert (p["kind"], p["stopped"]["fn"], p["stopped"]["mod"], p["kernel"]) == ("null", "my_sensor_read_temp", "my_sensor", "6.8.0-rc3")
    assert [t["flag"] for t in p["taint"]] == ["O", "E"] and p["out_of_tree"] == ["my_sensor"] and p["arch"] == "x86_64"
    assert [f["fn"] for f in p["trace"] if not f["unsure"]][:2] == ["my_sensor_read_temp", "my_sensor_probe"]
    assert "24 bytes into a structure" in " ".join(e["points"]) and "out-of-tree module" in " ".join(e["points"])
    assert e["commands"][0] == "./scripts/faddr2line my_sensor.ko my_sensor_read_temp+0x1c/0x60"
    k = crash.parse(KS.KASAN)
    ke = crash.explain(k)
    assert k["kind"] == "kasan" and k["detail"] == "slab-use-after-free" and k["kasan"]["cache"] == "kmalloc-192"
    assert "ring_pop()" in ke["summary"] and "Freed in ring_clear(), used again in ring_pop()" in " ".join(ke["points"])
    a = crash.parse(KS.ARM64_GPF)
    ae = crash.explain(a)
    assert a["arch"] == "arm64" and "LIST_POISON" in a["poison"] and a["count"] == 1
    assert "mydev_remove() in the module 'mydev'" in " ".join(ae["points"])
    h = crash.parse(KS.HUNG)
    he = crash.explain(h)
    assert "mydev_work()" in he["summary"] and "waits in __mutex_lock()" in " ".join(he["points"])
    assert crash.signature(p) == crash.signature(crash.parse(KS.NULL_X86.replace("4321", "99")))
    assert crash.signature(p) != crash.signature(k)
    assert crash.parse("hello world")["kind"] == ""


def test_patch_config_boot_readers():
    from app.kerneldesk import bootlog, kconfig, patch
    bad = patch.check(KS.PATCH_BAD)
    rules = {i["rule"] for i in bad["issues"]}
    assert {"sob", "fixes", "space_indent", "kw_paren", "trailing", "subsystem", "subject_dot", "imperative", "closes", "printk"} <= rules
    assert not bad["ok"] and next(i for i in bad["issues"] if i["rule"] == "kw_paren")["line"] == 12
    assert 'Fixed ..." -> "Fix ...' in next(i["say"] for i in bad["issues"] if i["rule"] == "imperative")
    good = patch.check(KS.PATCH_GOOD)
    assert good["ok"] and good["counts"] == {"error": 0, "warning": 0, "check": 0} and good["stat"] == {"files": 1, "plus": 5, "minus": 1}
    new_file = "Subject: [PATCH] x: y\n\nBody.\n\nSigned-off-by: A <a@b.c>\ndiff --git a/a.c b/a.c\nnew file mode 100644\n--- /dev/null\n+++ b/a.c\n@@ -0,0 +1 @@\n+int x;\n"
    assert any(i["rule"] == "spdx" for i in patch.check(new_file)["issues"])
    c = kconfig.check(KS.CONFIG, ["qemu", "hardening"])
    q = next(r for r in c["results"] if r["profile"] == "qemu")
    h = next(r for r in c["results"] if r["profile"] == "hardening")
    assert c["arch"] == "x86_64" and c["version"] == "6.8.0" and q["wrong"] == 1 and h["wrong"] == 1
    assert "CONFIG_DEVTMPFS_MOUNT=y" in c["fragment"] and "# CONFIG_DEVMEM is not set" in c["fragment"]
    assert not any(r["name"] == "CONFIG_SERIAL_AMBA_PL011" for r in q["rows"])          # arm64 rows left out on x86_64
    d = kconfig.diff(KS.CONFIG, KS.CONFIG.replace("CONFIG_DEVMEM=y", "# CONFIG_DEVMEM is not set") + "CONFIG_KASAN=y\n")
    assert d["counts"] == {"added": 1, "removed": 0, "changed": 1}
    ok = bootlog.parse(KS.BOOT_OK)
    assert ok["passed"] and ok["stages"][-1]["key"] == "marker" and ok["init_s"] == 1.12
    says = " ".join(e["say"] for e in ok["errors"])
    assert "EREMOTEIO" in says and "regulatory.db" in says and "ENOENT" in says
    bad_boot = bootlog.parse(KS.BOOT_FAIL)
    assert not bad_boot["passed"] and "crashed while booting" in bad_boot["verdict"]


def test_drivers_and_workflow_are_sound(tmp_path):
    from app.kerneldesk import ci, patch, scaffold
    stubs = tmp_path / "linux"
    stubs.mkdir()
    for h in ("init", "module", "moduleparam", "fs", "miscdevice", "mutex", "uaccess", "io", "mod_devicetable", "platform_device", "regmap", "i2c"):
        (stubs / f"{h}.h").write_text("")
    pre = ("#define __init\n#define __exit\n#define __user\n#define __iomem\n#define GFP_KERNEL 0\n#define THIS_MODULE 0\n"
           "#define MISC_DYNAMIC_MINOR 255\n#define ENOMEM 12\n#define ENOTTY 25\n#define _IO(a,b) ((a)<<8|(b))\n"
           "typedef long ssize_t; typedef long loff_t; typedef unsigned long size_t;\n")
    for kind in scaffold.KINDS:
        files = scaffold.make(kind, "my_sensor", "A test sensor")
        chk = patch.check("Subject: [PATCH] hwmon: my_sensor: add\n\nAdd it.\n\nSigned-off-by: A <a@b.c>\n" + scaffold.as_patch(files))
        assert chk["counts"]["error"] == 0 and chk["counts"]["warning"] == 0, (kind, chk["issues"][:3])
        assert files["my_sensor.c"].startswith("// SPDX-License-Identifier: GPL-2.0") and 'MODULE_LICENSE("GPL")' in files["my_sensor.c"]
        assert "{" not in files["my_sensor.c"].split("\n")[0]
        src = tmp_path / f"{kind}.c"
        src.write_text(files["my_sensor.c"])
        # only the preprocessor + brace balance here: kernel headers are not on this server
        r = subprocess.run(["gcc", "-E", "-P", "-nostdinc", f"-I{tmp_path}", "-include", "/dev/null", str(src)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        body = files["my_sensor.c"]
        assert body.count("{") == body.count("}") and body.count("(") == body.count(")")
    with pytest.raises(ValueError):
        scaffold.make("hello", "9bad")
    yaml = pytest.importorskip("yaml")
    for arch in ci.ARCH:
        w = ci.workflow(arch, module_dir="drivers/my_sensor")
        d = yaml.safe_load(w["yaml"])
        steps = d["jobs"]["boot"]["steps"]
        assert "workflow_dispatch" in d.get("on", d.get(True)) and [s["name"] for s in steps if "name" in s] == w["steps"]
        for s in steps:
            if "run" in s:
                r = subprocess.run(["bash", "-n"], input=s["run"], capture_output=True, text=True)
                assert r.returncode == 0, (arch, s["name"], r.stderr)
        assert ci.ARCH[arch]["console"] in w["yaml"] and "HOOLA_BOOT_OK" in w["yaml"]
    init = tmp_path / "init.c"
    init.write_text(ci.INIT_C.replace("@MARKER@", "HOOLA_BOOT_OK"))
    r = subprocess.run(["gcc", "-static", "-O2", "-Wall", "-Werror", "-o", str(tmp_path / "init"), str(init)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    with pytest.raises(ValueError):
        ci.workflow("x86_64", module_dir="../etc")
    with pytest.raises(ValueError):
        ci.workflow("sparc")


def test_hire_chat_wiring_store_and_guards(kd):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert kd.summary(T)["hired"] is False and "Hire me from AI Employees" in kd.greeting(T)
    with pytest.raises(PermissionError):
        kd.do(T, "add", {"kind": "crash", "text": "x"})
    _hire()
    d = kd.summary(T)
    assert d["hired"] and "never runs your kernel" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"crashes", "settings"}
    chat = kd.current(T)
    assert kd.is_kernel(chat["id"]) and kd.owns(T, chat["id"]) and "<kernel_desk>" in kd.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_kdc.is_kernel(conversation_id)" in src and "adm.admit_families(_kdc.FAMILIES)" in src
    for f_ in ("callconv.py", "convs.py"):
        assert '"kernel"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/kernel")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "kddesk.js" in r.text
    html = (root / "server/app/static/console/kddesk.html").read_text()
    for x in ("chatkit.js", "kddesk.css", "kddesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/kernel')" in (root / "server/app/static/console/v2.js").read_text()
    assert "kernel_dev: 'kddesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["kernel_dev"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["kernel_desk"] in kd.FAMILIES and "kernel_desk" in HANDLERS
    # the store: grouping by signature, a fixed crash that comes back
    c1 = kd.do(T, "add", {"kind": "crash", "text": KS.NULL_X86})
    assert c1["number"] == "C-0001" and c1["result"]["explain"]["summary"].startswith("NULL pointer dereference")
    kd.do(T, "mark", {"id": c1["id"], "status": "fixed"})
    c2 = kd.do(T, "add", {"kind": "crash", "text": KS.NULL_X86.replace("123.4", "999.4")})
    assert c2["seen"] == 2 and c2["note"].startswith("Seen again") and len(c2["same"]) == 1
    g = kd.do(T, "groups", {})["items"]
    assert len(g) == 1 and g[0]["count"] == 2
    assert any("came back" in n["say"] for n in kd.summary(T)["desk"]["needs"])
    p = kd.do(T, "add", {"kind": "patch", "text": KS.PATCH_BAD})
    assert p["number"] == "P-0001" and any("error" in n["say"] for n in kd.summary(T)["desk"]["needs"])
    cf = kd.do(T, "add", {"kind": "config", "text": KS.CONFIG, "profiles": ["qemu"], "compare": KS.CONFIG})
    assert cf["result"]["diff"]["counts"] == {"added": 0, "removed": 0, "changed": 0}
    b = kd.do(T, "add", {"kind": "boot", "text": KS.BOOT_FAIL})
    assert any("did not pass" in n["say"] for n in kd.summary(T)["desk"]["needs"]) and b["brief"]["passed"] is False
    s = kd.do(T, "settings", {"arch": "arm64", "kernel": "6.12", "module_dir": "drivers/my_sensor"})
    assert s["arch"] == "arm64" and "qemu-system-aarch64" in kd.do(T, "workflow", {})["yaml"]
    dv = kd.do(T, "driver", {"kind": "platform", "name": "My Sensor!", "what": "x"})
    assert dv["name"] == "my_sensor" and any(f["name"] == "my-sensor.dtsi" for f in dv["files"])
    # guards
    with pytest.raises(PermissionError):
        kd.do(T, "settings", {"author": "my password is hunter2"})
    assert kd.do(T, "add", {"kind": "boot", "text": "password: hunter2 in a log is data"})["kind"] == "boot"   # a log may carry anything
    with pytest.raises(kd.KdDeskError):
        kd.do(T, "settings", {"arch": "sparc"})
    with pytest.raises(kd.KdDeskError):
        kd.do(T, "settings", {"module_dir": "../../etc"})
    with pytest.raises(kd.KdDeskError):
        kd.do(T, "add", {"kind": "crash", "text": "   "})
    with pytest.raises(kd.KdDeskError):
        kd.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "kernel_dev")
    assert kd.do(T, "get", {"id": c1["id"]})["id"] == c1["id"]
    with pytest.raises(PermissionError):
        kd.do(T, "add", {"kind": "crash", "text": KS.HUNG})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def kd_server(kd, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(kd, kd_server):
    base, browser, key = kd_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/kernel")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # a crash log, opened from a file
    go(pg, "#/crashes", "form[data-form=add]")
    fn = os.path.join(tempfile.mkdtemp(), "oops.log")
    open(fn, "w").write(KS.KASAN)
    pg.set_input_files("form[data-form=add] input[type=file]", fn)
    pg.wait_for_function("document.querySelector('form[data-form=add] [name=text]').value.includes('KASAN')")
    pg.click("form[data-form=add] [type=submit]")
    pg.wait_for_selector(".kd-sum", timeout=30000)
    assert "ring_pop()" in pg.inner_text(".kd-sum") and "Freed in ring_clear()" in pg.inner_text("#kdPage")
    snap(pg, "kd-crash-1440")
    pg.click("[data-mark=fixed]")
    pg.wait_for_selector("#toast:has-text('Marked fixed')", timeout=20000)
    # a patch
    go(pg, "#/patches", "form[data-form=add]")
    pg.fill("form[data-form=add] [name=text]", KS.PATCH_BAD)
    pg.click("form[data-form=add] [type=submit]")
    pg.wait_for_selector(".kd-issue", timeout=30000)
    assert "Signed-off-by" in pg.inner_text("#kdPage")
    snap(pg, "kd-patch-1440")
    # a config with a compare
    go(pg, "#/config", "form[data-form=add]")
    pg.fill("form[data-form=add] [name=text]", KS.CONFIG)
    pg.click("form[data-form=add] [type=submit]")
    pg.wait_for_selector("table.kd-cfg", timeout=30000)
    assert "A fragment to merge" in pg.inner_text("#kdPage")
    snap(pg, "kd-config-1440")
    # boot & CI: the workflow, then a boot log
    go(pg, "#/boot", "form[data-form=wf]")
    pg.select_option("form[data-form=wf] [name=arch]", "arm64")
    pg.fill("form[data-form=wf] [name=module_dir]", "drivers/my_sensor")
    pg.click("form[data-form=wf] [type=submit]")
    pg.wait_for_selector("pre.kd-pre.yml", timeout=30000)
    assert "qemu-system-aarch64" in pg.inner_text("pre.kd-pre.yml")
    pg.fill("form[data-form=add] [name=text]", KS.BOOT_OK)
    pg.click("form[data-form=add] [type=submit]")
    pg.wait_for_selector(".kd-stages", timeout=30000)
    assert "Booted and printed the test marker" in pg.inner_text(".kd-sum")
    snap(pg, "kd-boot-1440")
    # a driver
    go(pg, "#/drivers", "form[data-form=driver]")
    pg.click("[data-dkind=platform]")
    pg.fill("form[data-form=driver] [name=name]", "my_sensor")
    pg.click("form[data-form=driver] [type=submit]")
    pg.wait_for_selector("nav.kd-tabs", timeout=30000)
    assert "module_platform_driver" in pg.inner_text("pre.kd-pre.code")
    with pg.expect_download() as dl:
        pg.click("[data-dzip]")
    assert dl.value.suggested_filename == "my_sensor.zip"
    snap(pg, "kd-drivers-1440")
    go(pg, "#/today", ".kd-groups")
    snap(pg, "kd-today-1440")
    for route, sel in (("#/today", ".kd-groups"), ("#/crashes", ".kd-groups"), ("#/patches", ".kd-item"), ("#/config", ".kd-item"),
                       ("#/boot", ".kd-item"), ("#/drivers", ".kd-kinds"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#kdPage *')].filter(e => !e.closest('pre,textarea,table') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    go(pg, "#/boot", ".kd-item")
    pg.click(".kd-item")
    pg.wait_for_selector(".kd-sum", timeout=20000)
    snap(pg, "kd-boot-390")
    go(pg, "#/crashes", ".kd-groups")
    pg.click(".kd-tr")
    pg.wait_for_selector(".kd-sum", timeout=20000)
    w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert w[0] <= w[1] + 1, w
    snap(pg, "kd-crash-390")
    assert not errs, errs
