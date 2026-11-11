"""v0.811 GAME TOOL HUB wave 1: free 3D models and textures from three CC0 libraries - Kenney (on Hoola's disk),
Poly Haven and ambientCG (their public APIs) - added as DRAFT assets that enter a game only after her OK.

The network is faked here (`library._fetch`), except one test that reaches the real libraries only when
HOOLA_LIVE_LIBRARY=1. The Kenney files, the GLB packer, the asset pipeline and (where installed) Godot are real."""
from __future__ import annotations

import io
import json
import os
import struct
import zipfile
from pathlib import Path

import pytest

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)

from app.gamedesk import glbpack
from app.gamedesk import library as L

SERVER = Path(__file__).resolve().parents[1]
LIB = SERVER / "app" / "gamedesk" / "library" / "kenney"


def _png(color=(120, 80, 40), size=64) -> bytes:
    from PIL import Image
    im = Image.new("RGB", (size, size), color)
    for x in range(0, size, 8):
        for y in range(0, size, 8):
            if (x + y) // 8 % 2:
                im.putpixel((x, y), (200, 170, 120))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _jpg(size=256) -> bytes:
    from PIL import Image
    im = Image.new("RGB", (size, size), (150, 60, 40))
    for i in range(0, size, 16):
        for j in range(size):
            im.putpixel((i, j), (90, 40, 30))
    buf = io.BytesIO()
    im.save(buf, "JPEG")
    return buf.getvalue()


def _gltf() -> tuple[bytes, bytes]:
    """The smallest real model: one triangle, one outside .bin, one outside picture."""
    pos = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
    idx = struct.pack("<3H", 0, 1, 2) + b"\x00\x00"
    blob = pos + idx
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}]}],
           "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}],
           "textures": [{"source": 0}], "images": [{"uri": "textures/wood_diff_1k.jpg"}],
           "buffers": [{"uri": "model.bin", "byteLength": len(blob)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36, "target": 34962},
                           {"buffer": 0, "byteOffset": 36, "byteLength": 6, "target": 34963}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 0]},
                         {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"}]}
    return json.dumps(doc).encode(), blob


# ================================================================ the packer
def test_a_gltf_with_outside_files_becomes_one_glb():
    doc, blob = _gltf()
    pic = _jpg(32)
    glb = glbpack.pack(doc, {"model.bin": blob, "textures/wood_diff_1k.jpg": pic}.get)
    fx = glbpack.facts(glb)
    assert fx["outside"] == [] and fx["meshes"] == 1 and fx["triangles"] == 1 and fx["images"] == 1
    d, b = glbpack.split(glb)
    v = d["bufferViews"][d["images"][0]["bufferView"]]
    assert b[v["byteOffset"]: v["byteOffset"] + v["byteLength"]] == pic and d["images"][0]["mimeType"] == "image/jpeg"
    assert b[:36] == blob[:36], "the geometry bytes are untouched"


def test_the_packer_never_reaches_for_a_file_it_was_not_given():
    doc, blob = _gltf()
    with pytest.raises(glbpack.PackError, match="was not given"):
        glbpack.pack(doc, {"model.bin": blob}.get)
    with pytest.raises(glbpack.PackError):
        glbpack.split(b"not a glb at all, just words")
    with pytest.raises(glbpack.PackError):
        glbpack.pack(b"{not json", {}.get)


# ================================================================ Kenney, on disk
def test_the_kenney_models_on_disk_are_whole_and_licensed():
    rows = L.kenney_index()
    assert len(rows) == 53
    for r in rows:
        data = (LIB / f"{r['id']}.glb").read_bytes()
        fx = glbpack.facts(data)
        assert fx["outside"] == [], r["id"]              # the shared colour map is inside every file
        assert fx["meshes"] >= 1 and len(data) < 400 * 1024, r["id"]
    lic = (LIB / "LICENSE-KENNEY.md").read_text(encoding="utf-8")
    assert "CC0" in lic and "github.com/KenneyNL" in lic
    assert L.SOURCES["kenney"]["licence"] == "CC0 1.0"


def test_search_finds_kenney_without_any_network(monkeypatch):
    monkeypatch.setattr(L, "_fetch", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network for Kenney")))
    got = L.search("coin", "model", "kenney")
    assert got["items"] and all(i["source"] == "kenney" and i["free"] and i["licence"] == "CC0 1.0" for i in got["items"])
    assert any("coin" in i["id"] for i in got["items"])
    assert L.search("truck", "model", "kenney")["items"][0]["name"].startswith("vehicle truck")
    assert L.search("coin", "texture", "kenney")["items"] == [], "Kenney has models only"
    with pytest.raises(L.LibraryError):
        L.search("x", "sound")


def _fake_net(monkeypatch, extra: dict | None = None):
    doc, blob = _gltf()
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        z.writestr("Bricks001_1K-JPG_Color.jpg", _jpg())
        z.writestr("Bricks001_1K-JPG_NormalGL.jpg", b"x" * 10)
    table = {
        "https://api.polyhaven.com/assets?t=models": json.dumps({"wooden_stool": {"name": "Wooden Stool", "tags": ["stool", "wood"], "categories": ["furniture"]},
                                                                  "rock_01": {"name": "Rock 01", "tags": ["rock"], "categories": ["nature"]}}).encode(),
        "https://api.polyhaven.com/assets?t=textures": json.dumps({"brick_wall_001": {"name": "Brick Wall 001", "tags": ["brick", "wall"], "categories": ["brick"]}}).encode(),
        "https://api.polyhaven.com/files/wooden_stool": json.dumps({"gltf": {"1k": {"gltf": {
            "url": "https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/wooden_stool/wooden_stool_1k.gltf", "size": len(doc),
            "include": {"model.bin": {"url": "https://dl.polyhaven.org/file/x/model.bin", "size": len(blob)},
                        "textures/wood_diff_1k.jpg": {"url": "https://dl.polyhaven.org/file/x/wood.jpg", "size": 900}}}}}}).encode(),
        "https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/wooden_stool/wooden_stool_1k.gltf": doc,
        "https://dl.polyhaven.org/file/x/model.bin": blob,
        "https://dl.polyhaven.org/file/x/wood.jpg": _jpg(32),
        "https://api.polyhaven.com/files/brick_wall_001": json.dumps({"Diffuse": {"1k": {"jpg": {"url": "https://dl.polyhaven.org/file/x/brick.jpg", "size": 5000}}}}).encode(),
        "https://dl.polyhaven.org/file/x/brick.jpg": _jpg(),
        "https://ambientcg.com/api/v2/full_json?type=Material&limit=30&include=tagData&q=brick": json.dumps(
            {"foundAssets": [{"assetId": "Bricks001", "displayName": "Bricks 001", "tags": ["brick", "wall"]}]}).encode(),
        "https://ambientcg.com/api/v2/full_json?type=Material&include=downloadData&id=Bricks001": json.dumps({"foundAssets": [{
            "assetId": "Bricks001", "downloadFolders": {"default": {"downloadFiletypeCategories": {"zip": {"downloads": [
                {"attribute": "1K-JPG", "size": 9000, "downloadLink": "https://ambientcg.com/get?file=Bricks001_1K-JPG.zip"}]}}}}}]}).encode(),
        "https://ambientcg.com/get?file=Bricks001_1K-JPG.zip": zbuf.getvalue(),
    }
    table.update(extra or {})
    seen = []

    def fetch(url, limit, timeout=40.0):
        seen.append(url)
        if url not in table:
            raise L.LibraryError("the library answered 404")
        if len(table[url]) > limit:
            raise L.LibraryError("too big")
        return table[url]
    monkeypatch.setattr(L, "_fetch", fetch)
    L._CACHE.clear()
    return seen


def test_search_reads_all_three_and_says_which_one_is_down(monkeypatch):
    _fake_net(monkeypatch)
    got = L.search("brick", "texture")
    assert {i["source"] for i in got["items"]} == {"polyhaven", "ambientcg"} and got["down"] == []
    assert L.search("stool", "model")["items"][0]["id"] == "wooden_stool"
    monkeypatch.setattr(L, "_fetch", lambda *a, **k: (_ for _ in ()).throw(L.LibraryError("the library answered 503")))
    L._CACHE.pop("ph:models", None)
    got = L.search("coin", "model")
    assert any(i["source"] == "kenney" for i in got["items"]), "a library that is down never hides the others"
    assert got["down"] and "Poly Haven" in got["down"][0]


def test_only_library_addresses_are_ever_fetched():
    for bad in ("https://evil.example/x.glb", "http://api.polyhaven.com/assets", "https://169.254.169.254/latest", "file:///etc/passwd"):
        with pytest.raises(L.LibraryError, match="not a library address"):
            L._fetch(bad, 1000)
    for bad_id in ("../../etc/passwd", "a b", "x" * 90, ""):
        with pytest.raises(L.LibraryError):
            L.get("kenney", bad_id, "model")
    with pytest.raises(L.LibraryError):
        L.get("ambientcg", "Bricks001", "model")       # ambientCG has textures only


# ================================================================ into her project
def test_a_kenney_model_is_a_draft_until_her_ok_and_is_never_called_ai(st):  # noqa: F811
    from app.gamedesk import assets as A
    from app.gamedesk import provenance as P
    a = L.add("default", st["sid"], "kenney", "platformer_coin", "model")
    assert a["key"] == "coin" and a["kind"] == "model" and a["status"] == "draft" and a["cost_inr"] == 0
    with A.session() as s:
        row = s.get(A.GameAsset, a["id"])
        h = row.history[-1]
    assert h["source"] == "library:kenney" and h["meta"]["licence"] == "CC0 1.0" and h["meta"]["credit"].startswith("Kenney")
    assert h["meta"]["triangles"] > 0 and h["cost_inr"] == 0
    assert A.for_game("default", st["gid"]) is None, "a draft is not in the game"
    A.approve("default", st["sid"], "coin")
    text, files = A.for_game("default", st["gid"])
    assert "assets/coin.glb" in files and 'const CREDITS := ""' in text, "a library asset does not trigger the AI credit line"
    rec = P.assets_record("default", st["sid"])
    assert rec["counts"]["unknown"] == 0 and len(rec["library"]) == 1 and rec["library"][0]["licence"] == "CC0 1.0"
    assert "made by a person, not by AI" in rec["library"][0]["how"]


def test_a_poly_haven_model_is_packed_into_one_file_and_big_ones_are_refused(st, monkeypatch):  # noqa: F811
    from app.gamedesk import assets as A
    seen = _fake_net(monkeypatch)
    a = L.add("default", st["sid"], "polyhaven", "wooden_stool", "model", key="stool")
    assert a["status"] == "draft" and a["key"] == "stool"
    with A.session() as s:
        row = s.get(A.GameAsset, a["id"])
        h = row.history[-1]
    glb = (A._dir("default", st["sid"], "stool") / h["file"]).read_bytes()
    assert glbpack.facts(glb)["outside"] == [] and h["source"] == "library:polyhaven"
    assert all(u.startswith(("https://api.polyhaven.com/", "https://dl.polyhaven.org/")) for u in seen)
    big = json.dumps({"gltf": {"1k": {"gltf": {"url": "https://dl.polyhaven.org/file/big.gltf", "size": 10,
                                               "include": {"a.bin": {"url": "https://dl.polyhaven.org/file/a.bin", "size": 40 * 1024 * 1024}}}}}}).encode()
    _fake_net(monkeypatch, {"https://api.polyhaven.com/files/huge_statue": big})
    with pytest.raises(A.AssetError, match="too big for a web game"):
        L.add("default", st["sid"], "polyhaven", "huge_statue", "model")


def test_textures_come_as_512_pictures_and_cannot_be_generated(st, monkeypatch):  # noqa: F811
    from app.gamedesk import assets as A
    _fake_net(monkeypatch)
    a = L.add("default", st["sid"], "ambientcg", "Bricks001", "texture", key="brick")
    b = L.add("default", st["sid"], "polyhaven", "brick_wall_001", "texture", key="wall")
    for x in (a, b):
        assert x["kind"] == "texture" and x["status"] == "draft", x
        assert (x["meta"]["w"], x["meta"]["h"]) == (512, 512)
    with pytest.raises(A.AssetError, match="not generated"):
        A.request("default", st["sid"], "texture", "grass", "green grass")
    assert A.KINDS["texture"]["cost_inr"] == 0 and "texture" not in A.PAID
    with pytest.raises(A.AssetError):
        L.add("default", st["sid"], "kenney", "platformer_coin", "model", key="brick")   # 'brick' is already a texture


def test_the_tool_the_routes_and_the_page_know_the_library(gd):  # noqa: F811
    from app.agent import tools
    t = next(x for x in tools.TOOLS if x["name"] == "game_assets")
    assert {"library", "library_add"} <= set(t["input_schema"]["properties"]["action"]["enum"])
    assert "texture" in t["input_schema"]["properties"]["kind"]["enum"]
    assert "FREE library" in t["description"] and len(t["description"]) <= 1200
    api = (SERVER / "app" / "gamedesk" / "api.py").read_text(encoding="utf-8")
    assert '@r.get("/api/gamestudio/{sid}/library"' in api and '@r.post("/api/gamestudio/{sid}/library"' in api
    js = (SERVER / "app" / "static" / "console" / "employees.js").read_text(encoding="utf-8")
    assert "Free library" in js and "data-ga-lib" in js and "/library?kind=" in js
    kit = (SERVER / "app" / "gamedesk" / "kit" / "hoola_3d.gd").read_text(encoding="utf-8")
    assert "func paint(" in kit and "uv1_triplanar" in kit


def test_the_routes_search_and_add(st):  # noqa: F811
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get(f"/api/gamestudio/{st['sid']}/library?q=flag&kind=model&source=kenney")
    assert r.status_code == 200 and r.json()["items"][0]["id"] == "platformer_flag"
    r = c.post(f"/api/gamestudio/{st['sid']}/library", json={"source": "kenney", "id": "platformer_flag", "kind": "model"})
    assert r.status_code == 200 and any(a["key"] == "flag" and a["status"] == "draft" for a in r.json()["assets"])
    assert c.get(f"/api/gamestudio/{st['sid']}/library?q=x&kind=sound").status_code == 400
    assert c.get("/api/gamestudio/S-9999/library?q=flag").status_code in (400, 404)


# ================================================================ the real engine
def _godot() -> str:
    from app.gamedesk import engine
    return engine.find() or ""


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_a_library_model_and_texture_load_through_the_kit(tmp_path):
    from app.gamedesk import assets as A
    from app.gamedesk import engine, kit3d, template
    main = ('extends Node\n\nfunc _count(n: Node) -> int:\n\tvar c := 1 if n is MeshInstance3D else 0\n'
            '\tfor k in n.get_children():\n\t\tc += _count(k)\n\treturn c\n\n'
            'func _ready() -> void:\n\tvar level := Hoola3D.world(self)\n\tvar g := Hoola3D.ground(level)\n'
            '\tHoola3D.paint(g, "brick", 2.0)\n\tvar m := Hoola3D.model(level, "truck", Vector3(0, 0, 0), 1.0)\n'
            '\tvar none := Hoola3D.model(level, "nope", Vector3.ZERO)\n\tvar mi: MeshInstance3D = g.get_child(0)\n'
            '\tvar mat := mi.material_override as StandardMaterial3D\n'
            '\tprint("LIBGAME " + JSON.stringify({"model_meshes": _count(m) if m != null else -1, "missing_is_null": none == null,'
            ' "textured": mat.albedo_texture != null, "triplanar": mat.uv1_triplanar}))\n\tget_tree().quit()\n')
    entries = {"truck": {"kind": "model", "path": "res://assets/truck.glb", "v": 1},
               "brick": {"kind": "texture", "path": "res://assets/brick.png", "v": 1}}
    files = {"main.gd": main, kit3d.FILE: kit3d.kit(), "hoola_assets.gd": A.gd(entries, False)}
    job = tmp_path / "job"
    (job / "proj" / "assets").mkdir(parents=True)
    for name, txt in template.files("lib game", "landscape", files).items():
        (job / "proj" / name).write_text(txt, encoding="utf-8")
    (job / "proj" / "assets" / "truck.glb").write_bytes((LIB / "racing_vehicle_truck_red.glb").read_bytes())
    (job / "proj" / "assets" / "brick.png").write_bytes(_png(size=512))
    engine._run(job, ["--path", "proj", "--import"], "import.log", 180)
    _c, log, _to = engine._run(job, ["--path", "proj", "--quit-after", "300"], "run.log", 120)
    line = next((ln for ln in log.splitlines() if ln.startswith("LIBGAME ")), "")
    assert line, log[-600:]
    got = json.loads(line[8:])
    assert got == {"model_meshes": got["model_meshes"], "missing_is_null": True, "textured": True, "triplanar": True}
    assert got["model_meshes"] >= 1 and engine.errors_in(log) == []


@pytest.mark.skipif(os.environ.get("HOOLA_LIVE_LIBRARY") != "1", reason="reaches the real libraries only when HOOLA_LIVE_LIBRARY=1")
def test_live_the_real_libraries_answer():
    L._CACHE.clear()
    assert L.search("chair", "model", "polyhaven")["items"]
    assert L.search("brick", "texture", "ambientcg")["items"]
    glb, facts = L.get("polyhaven", "ArmChair_01", "model")
    assert glbpack.facts(glb)["outside"] == [] and facts["resolution"] == "1k"
    pic, _f = L.get("polyhaven", "brick_wall_001", "texture")
    assert pic[:2] == b"\xff\xd8"
    pic2, _f2 = L.get("ambientcg", "Bricks001", "texture")
    assert pic2[:2] == b"\xff\xd8" or pic2[:4] == b"\x89PNG"
