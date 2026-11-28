"""VISION DESK: the Computer Vision Engineer's own section, built like the finance desks - its own chat (kind 'vision') with the desk
block + the vision tool in view; detectors scored exactly as the official COCO evaluation scores them (pinned to pycocotools' own
numbers on generated sets with crowd regions and empty images); classifiers scored (AUC against the brute-force pair count, the
Wilson interval, kappa by hand); YOLO and COCO labels checked (bad boxes, duplicates, a class clash, unknown ids, a leak between
splits); camera and lens answers by hand; pipeline speed; the CI model check really fails a pull request whose mAP drops; walked
in a browser."""
from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"


def make(seed, CR=0.03):
    R = random.Random(seed)
    imgs = [{"id": i, "file_name": f"im{i}.jpg", "width": 640, "height": 480} for i in range(1, 31)]
    cats = [{"id": c, "name": f"c{c}"} for c in (1, 2, 3)]
    anns, dets, aid = [], [], 1
    for im in imgs:
        for _ in range(R.randint(0, 6)):
            w = R.choice([R.uniform(8, 30), R.uniform(35, 90), R.uniform(100, 300)])
            h = w * R.uniform(.5, 1.5)
            x = R.uniform(0, 640 - w)
            y = R.uniform(0, max(1, 480 - h))
            c = R.choice((1, 2, 3))
            crowd = 1 if R.random() < CR else 0
            anns.append({"id": aid, "image_id": im["id"], "category_id": c, "bbox": [x, y, w, h], "area": w * h, "iscrowd": crowd})
            aid += 1
            if R.random() < 0.8:
                dets.append({"image_id": im["id"], "category_id": c if R.random() < .85 else R.choice((1, 2, 3)),
                             "bbox": [x + R.gauss(0, w * .08), y + R.gauss(0, h * .08), w * R.uniform(.85, 1.15), h * R.uniform(.85, 1.15)], "score": R.random()})
        for _ in range(R.randint(0, 3)):
            dets.append({"image_id": im["id"], "category_id": R.choice((1, 2, 3)), "bbox": [R.uniform(0, 500), R.uniform(0, 400), R.uniform(10, 120), R.uniform(10, 120)],
                         "score": R.random() * .6})
    return {"images": imgs, "annotations": anns, "categories": cats}, dets


# pycocotools 2.0.8 COCOeval('bbox').stats[:6] on make(seed): mAP, AP50, AP75, small, medium, large
COCO_REF = {0: [0.29278, 0.651504, 0.229241, 0.314041, 0.282519, 0.331166], 3: [0.249702, 0.523738, 0.184161, 0.315605, 0.202545, 0.346707]}

GT_LINES = "img1.jpg person 10 10 110 210\nimg1.jpg car 200 50 400 150\nimg2.jpg person 30 30 80 130\nimg3.jpg\n"
PR_LINES = "img1.jpg person 0.9 12 8 112 208\nimg1.jpg car 0.8 205 55 395 148\nimg2.jpg car 0.7 30 30 80 130\nimg3.jpg person 0.6 5 5 50 50\n"
YOLO = """## train/labels/img001.txt
0 0.5 0.5 0.2 0.3
0 0.5 0.5 0.2 0.3
1 0.3 0.3 0.1 0.1
## train/labels/img002.txt
0 0.95 0.5 0.2 0.2
2 0.5 0.5 0.001 0.002
## train/labels/img003.txt
## val/labels/img001.txt
0 0.4 0.4 0.1 0.1
## val/labels/img004.txt
0 0.4 0.4 0.1 0.1
1 0.4 0.4 0.1 0.1
## test/labels/img005.txt
0 0.2 0.2 0 0.1
1 0.6 0.6 0.2 0.2
## classes.txt
person
car
"""
CAMERA = ("sensor pixel=2.9um res=1920x1080 lens=6mm\ndistance 10m\nobject 0.2m at 30m\nneed 30px on 0.2m at 40m\ncover 4m at 10m\n"
          "motion 10m/s exposure 1ms at 5m\ndof f/2 at 3m\nstereo baseline=0.12m at 5m disparity 0.25px")
CALIB = """image_width: 1280
image_height: 720
camera_name: cam
camera_matrix:
  rows: 3
  cols: 3
  data: [912.3, 0, 655.1, 0, 910.8, 361.4, 0, 0, 1]
distortion_model: plumb_bob
distortion_coefficients:
  rows: 1
  cols: 5
  data: [-0.38, 0.15, 0.0004, -0.0002, -0.03]
"""
PIPE = "camera 3840x2160 30fps\ndecode 6ms\npreprocess 4ms\ninference 28ms gpu\nnms 2ms\ntracking 3ms\nmodel input=640 object=40px"


def classify_text(seed=3, n=500):
    R = random.Random(seed)
    rows = ["image,true,predicted,score"]
    for i in range(n):
        t = R.choice(["ok", "defect"]) if R.random() < .5 else "ok"
        p_def = min(.999, max(.001, R.gauss(.7 if t == "defect" else .3, .2)))
        pred = "defect" if p_def >= .5 else "ok"
        rows.append(f"img{i},{t},{pred},{p_def if pred == 'defect' else 1 - p_def:.4f}")
    return "\n".join(rows)


@pytest.fixture
def cvc(env):
    from app import cvchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "cv_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_detection_matches_coco():
    from app.cvdesk import detect as D
    for seed, ref in COCO_REF.items():
        gt, dt = make(seed)
        r = D.evaluate(json.dumps(gt), json.dumps(dt))
        mine = [r["map"], r["map50"], r["map75"], r["small"], r["medium"], r["large"]]
        assert all(abs(a - b) < 2e-6 for a, b in zip(mine, ref)), (seed, mine, ref)
    r = D.evaluate(GT_LINES, PR_LINES)
    cls = {c["name"]: c for c in r["classes"]}
    assert abs(cls["person"]["ap50"] - 51 / 101) < 1e-12 and cls["car"]["ap50"] == 1.0 and r["images"] == 3
    assert r["confusion"] == [{"truth": "person", "said": "car", "n": 1}] and r["errors"]["background"] == 1 and r["errors"]["wrong class"] == 1
    assert r["at"]["tp"] == 2 and r["at"]["fp"] == 2 and r["at"]["fn"] == 1
    x = D.evaluate("a 0 10 10 50 50", "a 0 0.9 10 10 48 48", fmt="xywh")      # IoU 0.9216
    assert x["map50"] == 1.0 and x["classes"][0]["ap75"] == 1.0
    for bad in (("", PR_LINES), (GT_LINES, ""), ("a b c", PR_LINES), ("{oops", PR_LINES)):
        with pytest.raises(D.DetectError):
            D.evaluate(*bad)
    with pytest.raises(D.DetectError):
        D.evaluate(GT_LINES, PR_LINES, fmt="cxcy")


def test_classify_dataset():
    from app.cvdesk import classify as C, dataset as DS
    txt = classify_text()
    r = C.evaluate(txt, need="precision 90%")
    rows = [l.split(",") for l in txt.splitlines()[1:]]
    pos = [(float(s) if p == "defect" else 1 - float(s)) for _, t, p, s in rows if t == "defect"]
    neg = [(float(s) if p == "defect" else 1 - float(s)) for _, t, p, s in rows if t == "ok"]
    brute = sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))
    assert abs(r["binary"]["auc"] - brute) < 1e-9 and r["binary"]["positive"] == "defect"
    right = sum(t == p for _, t, p, _ in rows)
    lo, hi = C.wilson(right, len(rows))
    z = 1.96
    ph = right / len(rows)
    assert abs((lo + hi) / 2 - (ph + z * z / (2 * len(rows))) / (1 + z * z / len(rows))) < 1e-12 and r["acc_ci"] == [lo, hi]
    po = right / len(rows)
    pe = sum(sum(t == c for _, t, _, _ in rows) * sum(p == c for _, _, p, _ in rows) for c in ("ok", "defect")) / len(rows) ** 2
    assert abs(r["kappa"] - (po - pe) / (1 - pe)) < 1e-12
    need = r["binary"]["need"]
    assert need["p"] >= 0.9 and need["thr"] is not None and r["calibration"]["ece"] >= 0
    three = C.evaluate("\n".join(f"i{i},{'abc'[i % 3]},{'abc'[(i % 3) if i % 5 else (i + 1) % 3]}" for i in range(60)))
    assert three["matrix"] and len(three["labels"]) == 3 and three["pairs"][0]["n"] == 4
    lop = C.evaluate("\n".join(f"i{i},{'ok' if i < 95 else 'bad'},ok" for i in range(100)))
    assert any(i["sev"] == "bad" and "majority" in i["fix"] for i in lop["issues"])
    for bad in ("", "a,b", "a,b,c,7\n" * 6):
        with pytest.raises(C.ClassifyError):
            C.evaluate(bad)
    d = DS.check(YOLO, "", "1920x1080")
    bad = [i["text"] for i in d["issues"] if i["sev"] == "bad"]
    assert any("not in the class list" in t and "class 2" in t for t in bad) and any("no width or height" in t for t in bad)
    assert any("outside the image" in t for t in bad) and any("two different classes" in t for t in bad) and any("more than one split" in t and "img001" in t for t in bad)
    assert any("labelled twice" in i["text"] for i in d["issues"]) and any("smaller than 8 pixels" in i["text"] for i in d["issues"])
    assert {c["name"] for c in d["classes"]} >= {"person", "car"} and d["splits"] == {"train": 3, "val": 2, "test": 1} and d["empty"] == 1
    coco, _ = make(0)
    coco["annotations"].append({"id": 999, "image_id": 77, "category_id": 1, "bbox": [0, 0, 5, 5]})
    coco["annotations"].append({"id": 1000, "image_id": 1, "category_id": 9, "bbox": [600, 400, 100, 100]})
    c = DS.check(json.dumps(coco))
    texts = " ".join(i["text"] for i in c["issues"])
    assert "not in the images list" in texts and "category id that is not in categories" in texts and "outside the image" in texts and c["format"] == "COCO JSON"
    for bad in ("", "{x", "## a.txt\n0 0.5 0.5"):
        with pytest.raises(DS.DatasetError):
            DS.check(bad)


def test_camera_pipeline_ci(tmp_path):
    from app.cvdesk import camera as CA, ci as CI, pipeline as PL
    r = CA.analyse(CAMERA)
    cam = r["camera"]
    f = 0.006 / 2.9e-6
    assert abs(cam["fpx"] - f) < 1e-6 and abs(cam["hfov"] - 2 * math.degrees(math.atan(1920 / 2 / f))) < 1e-9
    ans = {a["title"]: dict(a["rows"]) for a in r["answers"]}
    assert ans["At 10 m"]["Pixels per metre"] == f"{f / 10:.4g}" and ans["A 20 cm object at 30 m"]["Pixels across it"] == f"{0.2 * f / 30:.1f}"
    assert ans["30 px on 20 cm at 40 m"]["Lens needed"] == f"{30 * 2.9e-6 * 40 / 0.2 * 1000:.3g} mm or longer"
    assert ans["10 m/s at 5 m, 1 ms exposure"]["Motion blur"] == f"{10 * 0.001 * f / 5:.2f} px"
    hyper = 0.006 ** 2 / (2 * 2 * 2.9e-6) + 0.006
    assert ans["Focused at 3 m, f/2"]["Hyperfocal distance"] == f"{hyper:.3g} m"
    assert ans["Stereo, 12 cm baseline, at 5 m"]["Depth error"].startswith(f"±{25 * 0.25 / (f * 0.12) * 100:.3g} cm")
    assert any(i["area"] == "Resolution" and i["sev"] == "bad" for i in r["issues"]) and any(i["area"] == "Motion blur" for i in r["issues"])
    c = CA.analyse(CALIB, ask="object 0.3m at 15m")
    assert c["calib"]["fx"] == 912.3 and c["calib"]["W"] == 1280 and c["calib"]["corner_px"] > 100 and abs(c["camera"]["hfov"] - 2 * math.degrees(math.atan(640 / 912.3))) < 1e-9
    bad_rms = CA.analyse(CALIB + "avg_reprojection_error: 1.6\n")
    assert any(i["sev"] == "bad" and "1.6" in i["text"] for i in bad_rms["issues"])
    for bad in ("", "distance 5m", "sensor res=1920x1080 lens=4mm\nfly to the moon"):
        with pytest.raises(CA.CameraError):
            CA.analyse(bad)
    p = PL.analyse(PIPE, 30)
    assert abs(p["latency"] - 43) < 1e-9 and abs(p["par_fps"] - 1000 / 28) < 1e-9 and abs(p["seq_fps"] - 1000 / 43) < 1e-9 and p["slowest"] == "inference"
    assert abs(p["resolution"]["obj_after"] - 40 * 640 / 3840) < 1e-9 and any(i["area"] == "Resolution" and i["sev"] == "bad" for i in p["issues"])
    s = PL.analyse("\n".join(str(x) for x in [10] * 95 + [50] * 5), 30)
    assert s["samples"]["p50"] == 10 and s["samples"]["late"] == 5 and any(i["area"] == "Latency" for i in s["issues"])
    with pytest.raises(PL.PipelineError):
        PL.analyse("make it fast please")
    w = CI.workflow("python eval.py --out eval/metrics.json", max_drop=1, max_rise=10, setup_cmd="pip install -r requirements.txt")
    y = yaml.safe_load(w["yaml"])
    assert y["permissions"] == {"contents": "read"} and [s_.get("name") for s_ in y["jobs"]["evaluate"]["steps"]][3:5] == ["Evaluate", "Compare with the baseline"]
    for bad in (dict(eval_cmd=""), dict(eval_cmd="x ${{ secrets.K }}"), dict(eval_cmd="x", metrics="../m.json"), dict(eval_cmd="x", metrics="a.json", baseline="a.json"), dict(eval_cmd="x", python="2")):
        with pytest.raises(CI.CiError):
            CI.workflow(**bad)
    code = w["compare"].replace("\n          ", "\n").strip()
    (tmp_path / "base.json").write_text(json.dumps({"map": 0.412, "map50": 0.63, "latency_ms": 18.0}))
    run = lambda: subprocess.run([sys.executable, "-I", "-c", code, str(tmp_path / "head.json"), str(tmp_path / "base.json")], capture_output=True, text=True,   # noqa: E731
                                 env={"PATH": os.environ.get("PATH", ""), "GITHUB_STEP_SUMMARY": str(tmp_path / "s.md")})
    (tmp_path / "head.json").write_text(json.dumps({"map": 0.405, "map50": 0.64, "latency_ms": 19.0}))
    assert run().returncode == 0
    (tmp_path / "head.json").write_text(json.dumps({"map": 0.39, "map50": 0.64, "latency_ms": 22.0}))
    out = run()
    assert out.returncode == 1 and "map: 0.412 -> 0.39" in out.stdout and "latency_ms: 18 -> 22" in out.stdout and "| map | 0.412 | 0.39 | FAIL |" in (tmp_path / "s.md").read_text()


def test_hire_chat_wiring_store_and_guards(cvc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert cvc.summary(T)["hired"] is False and "Hire me from AI Employees" in cvc.greeting(T)
    with pytest.raises(PermissionError):
        cvc.do(T, "add", {"kind": "camera", "text": CAMERA})
    _hire()
    d = cvc.summary(T)
    assert d["hired"] and "runs nothing on your cameras" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"detect", "settings"}
    chat = cvc.current(T)
    assert cvc.is_vision(chat["id"]) and cvc.owns(T, chat["id"]) and "<vision_desk>" in cvc.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_cvc.is_vision(conversation_id)" in s_ and "adm.admit_families(_cvc.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"vision"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/vision")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "cvdesk.js" in r.text
    html = (root / "server/app/static/console/cvdesk.html").read_text()
    for x in ("chatkit.js", "cvdesk.css", "cvdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/vision')" in (root / "server/app/static/console/v2.js").read_text()
    assert "cv_eng: 'cvdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["cv_eng"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["vision_desk"] in cvc.FAMILIES and "vision_desk" in HANDLERS
    gt, dt = make(0)
    d1 = cvc.do(T, "add", {"kind": "detect", "text": json.dumps(gt), "inputs": {"pred": json.dumps(dt)}})
    assert d1["number"] == "D-0001" and abs(d1["brief"]["map"] - COCO_REF[0][0]) < 2e-6 and d1["title"] == "Detection: mAP 29.3, AP50 65.2"
    json.dumps(d1)
    with pytest.raises(cvc.CvDeskError):
        cvc.do(T, "add", {"kind": "detect", "text": json.dumps(gt)})
    c1 = cvc.do(T, "add", {"kind": "classify", "text": classify_text(), "inputs": {"need": "recall 80%"}})
    assert c1["number"] == "C-0001" and c1["brief"]["auc"] > 0.85 and c1["result"]["binary"]["need"]["kind"] == "recall"
    l1 = cvc.do(T, "add", {"kind": "dataset", "text": YOLO, "inputs": {"img_size": "1920x1080"}})
    assert l1["number"] == "L-0001" and l1["brief"]["bad"] and any(n["go"] == "dataset/" + l1["id"] for n in cvc.summary(T)["desk"]["needs"])
    k1 = cvc.do(T, "add", {"kind": "camera", "text": CAMERA})
    assert k1["number"] == "K-0001" and k1["brief"]["answers"] == 7 and round(k1["brief"]["hfov"]) == 50
    p1 = cvc.do(T, "add", {"kind": "pipeline", "text": PIPE, "inputs": {"target_fps": 30}})
    assert p1["number"] == "P-0001" and abs(p1["brief"]["fps"] - 1000 / 28) < 1e-9 and p1["brief"]["bad"]
    assert cvc.do(T, "ci", {})["missing"] is True
    st = cvc.do(T, "settings", {"class_names": "person\ncar", "score_thr": 0.4, "eval_cmd": "python eval.py --out eval/metrics.json", "max_drop": 2, "min_px": 16, "img_size": "1920x1080"})
    assert st["class_names"] == "person, car" and st["score_thr"] == 0.4 and st["min_px"] == 16
    w = cvc.do(T, "ci", {})
    assert w["file"] == ".github/workflows/model-check.yml" and yaml.safe_load(w["yaml"])
    cvc.forget(T)
    assert "classes person, car" in cvc.block(T) and "score threshold 0.4" in cvc.block(T)
    l2 = cvc.do(T, "add", {"kind": "dataset", "text": "## train/a.txt\n0 0.5 0.5 0.2 0.2\n1 0.3 0.3 0.1 0.1\n2 0.6 0.6 0.1 0.1"})
    assert any("class 2" in i["text"] for i in l2["result"]["issues"])
    mk = cvc.do(T, "mark", {"id": l1["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "dataset/" + l1["id"] for n in cvc.summary(T)["desk"]["needs"])
    import asyncio
    from app.agent import vision_tools as VT
    from app.agent.tools import Ctx
    out = asyncio.run(VT.vision_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="detect", text=GT_LINES, inputs={"pred": PR_LINES}))
    assert abs(out["map50"] - (51 / 101 + 1) / 2) < 1e-12 and out["confusion"][0]["said"] == "car"
    out = asyncio.run(VT.vision_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="camera", text=CALIB, inputs={"ask": "distance 5m"}))
    assert out["calib"]["fx"] == 912.3 and out["answers"]
    out = asyncio.run(VT.vision_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/model-check.yml"
    with pytest.raises(PermissionError):
        cvc.do(T, "settings", {"eval_cmd": "my password is hunter2"})
    assert cvc.do(T, "add", {"kind": "pipeline", "text": PIPE.replace("nms 2ms", "nms 2ms # password = hunter2")})["kind"] == "pipeline"
    for bad in ({"box_fmt": "cxcy"}, {"score_thr": 2}, {"img_size": "big"}, {"metrics_path": "../x"}, {"max_drop": -1}):
        with pytest.raises((cvc.CvDeskError, PermissionError)):
            cvc.do(T, "settings", bad)
    with pytest.raises(cvc.CvDeskError):
        cvc.do(T, "add", {"kind": "camera", "text": ""})
    with pytest.raises(cvc.CvDeskError):
        cvc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "cv_eng")
    assert cvc.do(T, "get", {"id": d1["id"]})["id"] == d1["id"] and cvc.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        cvc.do(T, "add", {"kind": "camera", "text": CAMERA})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def cv_server(cvc, monkeypatch):
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


def test_desk_in_a_real_browser(cvc, cv_server):
    base, browser, key = cv_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    def put(pg, form, name, text):
        pg.eval_on_selector(f"form[data-form={form}] [name={name}]", "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); }", text)

    def submit(pg, form, text, sel):
        put(pg, form, "text", text)
        pg.click(f"form[data-form={form}] [type=submit]")
        pg.wait_for_selector(sel, timeout=60000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/vision")
    pg.wait_for_selector(".cvk-path", timeout=20000)
    snap(pg, "cv-today-empty-1440")
    gt, dt = make(0)
    go(pg, "#/detect", "form[data-form=detect]")
    put(pg, "detect", "pred", json.dumps(dt))
    submit(pg, "detect", json.dumps(gt), ".cvk-chart svg")
    assert "29.3" in pg.inner_text(".cs-hero") and pg.locator(".cvk-chart polyline").count() >= 6
    snap(pg, "cv-detect-1440")
    go(pg, "#/classify", "form[data-form=classify]")
    put(pg, "classify", "need", "precision 90%")
    submit(pg, "classify", classify_text(), "table.cvk-cm")
    assert "ROC AUC" in pg.inner_text(".cs-hero") and "call it defect when its score is" in pg.inner_text("#cvPage")
    snap(pg, "cv-classify-1440")
    go(pg, "#/dataset", "form[data-form=dataset]")
    put(pg, "dataset", "img_size", "1920x1080")
    submit(pg, "dataset", YOLO, "text=more than one split")
    assert "person" in pg.inner_text("#cvPage") and "two different classes" in pg.inner_text("#cvPage")
    snap(pg, "cv-dataset-1440")
    go(pg, "#/camera", "form[data-form=camera]")
    submit(pg, "camera", CAMERA, ".cvk-wedge svg")
    assert pg.locator(".cvk-ans").count() == 7 and "Lens needed" in pg.inner_text("#cvPage")
    snap(pg, "cv-camera-1440")
    go(pg, "#/camera", "form[data-form=camera]")
    put(pg, "camera", "ask", "object 0.3m at 15m")
    submit(pg, "camera", CALIB, "text=The calibration")
    go(pg, "#/speed", "form[data-form=pipeline]")
    put(pg, "pipeline", "target_fps", "30")
    submit(pg, "pipeline", PIPE, ".cvk-stack")
    assert "Resolution at the model" in pg.inner_text("#cvPage")
    snap(pg, "cv-speed-1440")
    go(pg, "#/speed", "form[data-form=pipeline]")
    submit(pg, "pipeline", "\n".join(str(10 + (i % 7) * 0.5 + (30 if i % 50 == 0 else 0)) for i in range(300)), ".cvk-chart svg")
    assert "p99" in pg.inner_text("#cvPage")
    go(pg, "#/ci", "text=Set the evaluation command")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=eval_cmd]", "python eval.py --out eval/metrics.json")
    pg.fill("form[data-form=settings] [name=class_names]", "person, car")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=model-check.yml")
    snap(pg, "cv-ci-1440")
    go(pg, "#/today", ".cvk-list")
    assert "29.3" in pg.inner_text(".cs-hero")
    snap(pg, "cv-today-1440")
    for route, sel in (("#/today", ".cvk-list"), ("#/detect", ".cvk-item"), ("#/classify", ".cvk-item"), ("#/dataset", ".cvk-item"), ("#/camera", ".cvk-item"),
                       ("#/speed", ".cvk-item"), ("#/ci", "text=model-check.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#cvPage *')].filter(e => !e.closest('pre,textarea,table,svg') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/detect", "#/classify", "#/dataset", "#/camera", "#/speed"):
        go(pg, route, ".cvk-item")
        pg.locator(".cvk-item").first.click()
        pg.wait_for_selector(".cvk-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
        snap(pg, "cv-" + route[2:] + "-390")
    assert not errs, errs
