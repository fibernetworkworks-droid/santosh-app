"""v0.141 3D Studio: Blender driven by Hoola in a locked box. The guard refuses anything that touches files / network /
settings / internals; jobs write -> check -> run -> fix from real errors -> deliver; changes make new versions; the signed
file route; and (when Blender is installed here) a real Blender run with network isolation."""
import asyncio
import os
from pathlib import Path

import pytest

from tests.test_bazar import _events
from tests.test_life import conv_ctx

GOOD = """
gold = H.mat("Gold", "#d4a017", metal=1, rough=0.25)
H.cyl("Cup", r=0.05, depth=0.12, loc=(0, 0, 0.06), mat=H.mat("Clay", "#c0582f"))
H.torus("Handle", major=0.03, minor=0.007, loc=(0.055, 0, 0.065), rot=(90, 0, 0), mat=gold)
bpy.ops.mesh.primitive_cube_add(size=0.02, location=(0, 0, 0.13))
cube = bpy.context.active_object
cube.modifiers.new("B", "BEVEL")
import math
for i in range(3):
    H.sphere(f"Bead {i}", r=0.004, loc=(math.cos(i) * 0.06, math.sin(i) * 0.06, 0.004))
H.floor()
"""

BAD = {
    "open('/etc/passwd').read()": "open",
    "import os\nos.system('id')": "import os",
    "import subprocess": "import subprocess",
    "bpy.ops.wm.save_as_mainfile()": "bpy.ops.wm",
    "o = bpy.ops\no.wm.quit_blender()": "variable",
    "x = getattr(bpy.ops, 'wm')": "variable",
    "bpy.ops.node.add_file(filepath='/root/x.png')": "filepath",
    "print(H.__class__)": "_",
    "t = bpy.data.texts.new('x')": "texts",
    "bpy.app.handlers.load_post.append(print)": "bpy.app",
    "bpy.context.scene.render.filepath = '/tmp/x'": "filepath",
    "while True:\n    pass": "while True",
    "s = '__class__'": "__",
    "img = bpy.data.images.load('/x.png')": "load",
    "b = bpy\nb.ops.wm.quit_blender()": "bpy",
    "exec('1')": "exec",
    "f = bpy.utils.register_class": "utils",
    "bpy.context.preferences.filepaths.use_scripts_auto_execute = True": "preferences",
    "from os import path": "from os",
    "import bpy as b": "as",
}


def test_guard_allows_scene_code_and_refuses_everything_else():
    from app.blender3d import guard
    assert guard.problems(GOOD) == []
    for code, word in BAD.items():
        p = guard.problems(code)
        assert p, f"not refused: {code!r}"
        assert any(word in x for x in p), (code, p)
    assert guard.problems("")[0].startswith("script khaali")
    assert "SyntaxError" in guard.problems("def (:")[0]
    assert guard.summary(GOOD)["ops"] == ["mesh"]


class FakeAI:
    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.calls = []

    def write(self, brief, names, refs, pr, style=""):
        self.calls.append(("write", brief, tuple(names), pr))
        return {"code": self.scripts.pop(0), "title": "Chai cup", "notes": "Mitti ka cup, sone ka handle."}

    def fix(self, brief, code, problems, names, pr):
        self.calls.append(("fix", tuple(problems)))
        return {"code": self.scripts.pop(0), "title": "", "notes": ""}

    def change(self, brief, code, words, names, pr, look_fix=""):
        self.calls.append(("change", code, words))
        return {"code": self.scripts.pop(0), "title": "", "notes": "Handle bada kiya."}

    def look(self, brief, png):
        return {"score": 8, "ok": True, "seen": "cup", "fix": ""}


PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00"
       b"\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


@pytest.fixture()
def fake(env, monkeypatch):
    from app.blender3d import ai, sandbox, service
    runs = []

    def run(job_dir, job, timeout=None, holder=None):
        code = Path(job["script"]).read_text()
        runs.append({"code": code, "job": job})
        if "boom" in code:
            return {"ok": False, "errors": ["NameError: name 'boom' is not defined (line 1: boom())"]}
        for v in job["render"]["views"]:
            (job_dir / f"view_{v}.png").write_bytes(PNG)
        ex = {}
        for f in job["exports"]:
            (job_dir / f"{job['base']}.{f}").write_bytes(b"solid x\nendsolid\n" if f == "stl" else b"glTF")
            ex[f] = f"{job['base']}.{f}"
        return {"ok": True, "errors": [], "warnings": [], "renders": [{"view": v, "file": f"view_{v}.png"}
                                                                     for v in job["render"]["views"]],
                "exports": ex, "frames": [], "isolated": True, "wall_s": 1.2, "blender": "5.2.3 LTS",
                "stats": {"count": 3, "tris": 900, "size_m": [0.14, 0.1, 0.12], "materials": 2,
                          "objects": [{"name": "Cup", "type": "MESH", "tris": 400, "open_edges": 0}]}}

    monkeypatch.setattr(sandbox, "run", run)
    monkeypatch.setattr(sandbox, "find", lambda: {"kind": "py", "path": "/fake"})
    fa = FakeAI(["open('/x')", "boom()", GOOD, GOOD.replace("0.03", "0.04")])
    for name in ("write", "fix", "change", "look"):
        monkeypatch.setattr(ai, name, getattr(fa, name))
    return fa, runs, service


def test_job_fixes_from_real_problems_and_delivers(fake):
    fa, runs, service = fake
    ctx = conv_ctx()
    v = service.start("default", ctx.conversation_id, "Chai ka cup, 12 cm, mitti ka rang, sone ka handle",
                      {"exports": ["glb", "stl"], "views": ["three_quarter", "front"], "print": True})
    assert v["number"] == "B3-0001" and v["status"] == "queued"
    service.run_job(v["id"])
    p = service.get("default", v["id"])
    assert p["status"] == "done", p
    # 1st script refused by the guard (never ran), 2nd failed in Blender, 3rd worked
    assert [c[0] for c in fa.calls] == ["write", "fix", "fix"]
    assert "open" in fa.calls[1][1][0] and "boom" in fa.calls[2][1][0]
    assert len(runs) == 2 and "open(" not in "".join(r["code"] for r in runs)
    assert set(p["exports"]) == {"glb", "stl"} and all(x.get("file_id") for x in p["exports"].values())
    assert [r["view"] for r in p["renders"]] == ["three_quarter", "front"]
    assert p["print_check"]["closed"] is True and p["print_check"]["size_mm"] == [140.0, 100.0, 120.0]
    assert p["title"] == "Chai cup" and p["script"].strip().startswith('gold = H.mat')
    cards = _events(ctx.conversation_id, "blender3d")
    assert {c["status"] for c in cards} >= {"queued", "writing", "building", "done"}
    assert cards[-1]["push"] is True and "B3-0001 taiyaar" in cards[-1]["say"]
    # the job job.json passes her inputs / fonts / print flag; nothing from the server's env
    assert runs[-1]["job"]["print"] is True and "devanagari" in runs[-1]["job"]["fonts"]


def test_change_makes_a_new_version_from_the_current_script(fake):
    fa, runs, service = fake
    fa.scripts = [GOOD, GOOD.replace("0.03", "0.05")]
    ctx = conv_ctx()
    v = service.start("default", ctx.conversation_id, "Chai cup", {})
    service.run_job(v["id"])
    service.change("default", v["id"], "handle bada karo")
    service.run_job(v["id"])
    p = service.get("default", v["id"])
    assert p["version"] == 2 and p["versions"] == 2 and "0.05" in p["script"]
    assert fa.calls[-1][0] == "change" and fa.calls[-1][2] == "handle bada karo" and "0.03" in fa.calls[-1][1]
    # same model, new files: no model call
    n = len(fa.calls)
    service.change("default", v["id"], "", {"exports": ["obj"], "quality": "final"})
    service.run_job(v["id"])
    p = service.get("default", v["id"])
    assert len(fa.calls) == n and p["version"] == 3 and "obj" in p["exports"] and p["options"]["quality"] == "final"


def test_tool_and_refusals(fake):
    fa, runs, service = fake
    from app.agent.tools import ToolError, dispatch
    fa.scripts = [GOOD]
    ctx = conv_ctx()
    out = asyncio.run(dispatch("blender_3d", {"action": "make", "brief": "Ek trophy, 20 cm, sunehri"}, ctx))
    assert out["status"] == "started"
    service.run_job(out["id"])
    lst = asyncio.run(dispatch("blender_3d", {"action": "list"}, ctx))
    assert lst["projects"][0]["status"] == "done"
    st = asyncio.run(dispatch("blender_3d", {"action": "status", "id": out["number"]}, ctx))
    assert st["number"] == "B3-0001" and "script" not in st
    with pytest.raises(ToolError) as e:
        asyncio.run(dispatch("blender_3d", {"action": "run_code", "code": "import os"}, ctx))
    assert "suraksha" in str(e.value) and "import os" in str(e.value)
    with pytest.raises(ToolError):
        asyncio.run(dispatch("blender_3d", {"action": "make", "brief": "working pistol frame print karne ke liye stl"}, ctx))
    r = asyncio.run(dispatch("blender_3d", {"action": "run_code", "code": GOOD, "title": "Mera cup"}, ctx))
    service.run_job(r["id"])
    assert service.get("default", r["id"])["status"] == "done"


def test_limits_and_signed_files(fake):
    fa, runs, service = fake
    from fastapi.testclient import TestClient
    from app.main import app
    fa.scripts = [GOOD]
    ctx = conv_ctx()
    v = service.start("default", ctx.conversation_id, "Cup", {})
    service.start("default", ctx.conversation_id, "Cup 2", {})
    service.start("default", ctx.conversation_id, "Cup 3", {})
    with pytest.raises(service.B3Error):
        service.start("default", ctx.conversation_id, "Cup 4", {})
    service.run_job(v["id"])
    p = service.get("default", v["id"])
    cl = TestClient(app)
    url = p["renders"][0]["url"]
    r = cl.get(url)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert cl.get(url.replace("sig=", "sig=0")).status_code == 404
    assert cl.get(url.replace("view_three_quarter.png", "..%2Fjob.json")).status_code == 404
    home = cl.get("/api/blender3d").json()
    assert home["health"]["installed"] is True and len(home["projects"]) == 3
    assert cl.post("/api/blender3d", json={"brief": ""}).status_code == 400
    assert cl.post(f"/api/blender3d/{v['id']}/cancel").json()["status"] == "done"   # finished jobs stay finished
    assert cl.delete(f"/api/blender3d/{v['id']}").json()["ok"] is True


def _real_blender():
    from app.blender3d import sandbox
    return sandbox.find()


@pytest.mark.skipif(not (os.environ.get("BLENDER_PY") or os.environ.get("BLENDER_BIN") or Path("/opt/blender/blender").exists()),
                    reason="Blender not installed here")
def test_real_blender_in_the_box(env, tmp_path):
    from app.blender3d import sandbox
    assert _real_blender()
    d = tmp_path / "job"
    d.mkdir()
    (d / "s.py").write_text(GOOD + "\nbpy.ops.mesh.primitive_monkey_add(location=(0.2, 0, 0.05), size=0.05)\n")
    res = sandbox.run(d, {"script": str(d / "s.py"), "render": {"samples": 4, "width": 160, "height": 160,
                                                                  "views": ["three_quarter"]},
                          "exports": ["glb", "stl"], "print": True, "base": "cup", "fonts": {}})
    assert res["ok"], res
    assert res["auto_camera"] and res["auto_lights"] and (d / "view_three_quarter.png").stat().st_size > 1000
    assert (d / "cup.glb").exists() and (d / "cup.stl").exists()
    names = {o["name"]: o for o in res["stats"]["objects"]}
    assert names["Cup"]["open_edges"] == 0 and "Hoola floor" in names
    if sandbox.net_isolation():
        assert res["isolated"] is True
    # the runtime gate catches what the guard would also refuse (defence in depth)
    (d / "s2.py").write_text("__import__('os')")
    r2 = sandbox.run(d, {"script": str(d / "s2.py"), "render": {"render": False}, "exports": [], "base": "x"})
    assert not r2["ok"] and "ImportError" in r2["errors"][0]
    (d / "s3.py").write_text("boom()")
    r3 = sandbox.run(d, {"script": str(d / "s3.py"), "render": {"render": False}, "exports": [], "base": "x"})
    assert "NameError" in r3["errors"][0] and "line 1" in r3["errors"][0]
