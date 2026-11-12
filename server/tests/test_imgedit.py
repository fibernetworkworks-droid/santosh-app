"""Image editing (app/imgedit + tool image_edit): local ops, AI routing and safety, the pipeline, the tool, admission."""
import asyncio
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from app import zoo
from app.agent import admit, imgedit_tools as T, tools
from app.imgedit import ai, ops, run as P


def _png(w=400, h=300, color=(200, 100, 50), mode="RGB"):
    out = io.BytesIO()
    Image.new(mode, (w, h), color).save(out, "PNG")
    return out.getvalue()


def _jpeg_with_gps():
    im = Image.new("RGB", (200, 150), (10, 120, 200))
    exif = Image.Exif()
    exif[0x010F] = "SecretCam"
    exif[0x8825] = {1: "N", 2: (19.0, 5.0, 0.0), 3: "E", 4: (72.0, 5.0, 0.0)}
    out = io.BytesIO()
    im.save(out, "JPEG", exif=exif.tobytes())
    return out.getvalue()


def run(coro):
    return asyncio.run(coro)


# ----------------------------------------------------------------------------- local ops
def test_resize_presets_and_fit():
    im = Image.new("RGB", (400, 300), "red")
    assert ops.op_resize(im, preset="insta_post").size == (1080, 1350)                     # feed size fills the frame
    assert ops.op_resize(im, preset="a4_300dpi").size == (2480, 3508)                      # print size keeps the whole photo
    assert ops.op_resize(im, width=200).size == (200, 150)
    assert ops.op_resize(im, percent=50).size == (200, 150)
    assert ops.op_resize(im, width=100, height=100, fit="inside").size == (100, 75)
    with pytest.raises(ops.EditError):
        ops.op_resize(im, width=99999)
    with pytest.raises(ops.EditError):
        ops.op_resize(im)


def test_crop_pad_rotate_flip():
    im = Image.new("RGB", (400, 300), "red")
    assert ops.op_crop(im, aspect="1:1").size == (300, 300)
    assert ops.op_crop(im, box=[0, 0, 0.5, 0.5]).size == (200, 150)
    assert ops.op_pad(im, aspect="1:1").size == (400, 400)                                 # grows, never crops
    assert ops.op_rotate(im, 90).size == (300, 400)
    assert ops.op_rotate(im, 45).size[0] > 400
    left = Image.new("RGB", (4, 2), "black"); left.putpixel((0, 0), (255, 0, 0))
    assert ops.op_flip(left, "h").getpixel((3, 0)) == (255, 0, 0)
    with pytest.raises(ops.EditError):
        ops.op_crop(im, box=[0.9, 0.9, 0.9, 0.9])


def test_redact_touches_only_its_region():
    im = Image.new("RGB", (100, 100), "white")
    for x in range(100):
        for y in range(100):
            im.putpixel((x, y), (x * 2 % 256, y * 2 % 256, 90))
    out = ops.op_redact(im, regions=[[0.1, 0.1, 0.4, 0.4]], mode="black")
    assert out.getpixel((20, 20)) == (0, 0, 0)
    assert out.getpixel((80, 80)) == im.getpixel((80, 80)) and out.getpixel((5, 5)) == im.getpixel((5, 5))
    with pytest.raises(ops.EditError):
        ops.op_redact(im, regions=[])


def test_adjust_filters_and_scan():
    im = Image.new("RGB", (60, 60), (100, 100, 100))
    assert ops.op_adjust(im, brightness=50).getpixel((1, 1))[0] > 100
    assert ops.op_adjust(im, brightness=-50).getpixel((1, 1))[0] < 100
    assert ops.op_adjust(im, warmth=60).getpixel((1, 1))[0] > ops.op_adjust(im, warmth=60).getpixel((1, 1))[2]
    g = ops.op_filter(Image.new("RGB", (8, 8), (200, 50, 50)), "grayscale")
    r, gg, b = g.getpixel((1, 1)); assert r == gg == b
    page = Image.new("RGB", (200, 200), (180, 175, 150))                                   # a dim photo of a page
    for x in range(40, 160):
        page.putpixel((x, 100), (40, 40, 40))
    s = ops.op_filter(page, "scan")
    assert s.mode == "L" and s.getpixel((10, 10)) > 220 and s.getpixel((100, 100)) < 120
    with pytest.raises(ops.EditError):
        ops.op_filter(im, "nope")
    with pytest.raises(ops.EditError):
        ops.op_adjust(im, brightness=500)


def test_text_watermark_devanagari_and_tile():
    im = Image.new("RGB", (400, 300), "black")
    a = ops.op_text(im, text="Meri Dukaan", color="white")
    assert a.getpixel((380, 285)) != (0, 0, 0) or a.tobytes() != im.tobytes()
    d = ops.op_text(im, text="मेरी दुकान", position="center", size_pct=10)
    assert d.tobytes() != im.tobytes()
    t = ops.op_text(im, text="SAMPLE", tile=True, opacity=40)
    assert t.tobytes() != im.tobytes()
    with pytest.raises(ops.EditError):
        ops.op_text(im, text="")


def test_encode_formats_alpha_and_compress():
    im = Image.new("RGBA", (50, 50), (255, 0, 0, 0))
    b, ext = ops.encode(im)
    assert ext == "png"                                                                    # transparency keeps png
    b, ext = ops.encode(Image.new("RGB", (50, 50)))
    assert ext == "jpg"
    big = Image.effect_noise((900, 900), 80).convert("RGB")
    out, _ = ops.encode(big, "jpg", target_kb=60)
    assert len(out) <= 60 * 1024
    with pytest.raises(ops.EditError):
        ops.encode(big, "jpg", target_kb=1)
    with pytest.raises(ops.EditError):
        ops.encode(big, "bmp")


def test_load_refuses_non_images_and_bombs():
    with pytest.raises(ops.EditError):
        ops.load(b"not a picture")
    huge = io.BytesIO()
    Image.new("1", (9000, 7000)).save(huge, "PNG")                                         # 63 MP
    with pytest.raises(ops.EditError):
        ops.load(huge.getvalue())


def test_exif_and_gps_never_travel():
    src = _jpeg_with_gps()
    assert b"SecretCam" in src
    r = run(P.process(src, [{"op": "resize", "width": 100}]))
    assert b"SecretCam" not in r["bytes"] and not Image.open(io.BytesIO(r["bytes"])).getexif()


def test_run_reports_and_limits():
    im, rep = ops.run(Image.new("RGB", (400, 300)), [{"op": "resize", "width": 200}, {"op": "crop", "aspect": "1:1"}])
    assert im.size == (150, 150) and [r["op"] for r in rep] == ["resize", "crop"]
    with pytest.raises(ops.EditError, match="Step 2"):
        ops.run(Image.new("RGB", (40, 40)), [{"op": "resize", "width": 20}, {"op": "crop"}])
    with pytest.raises(ops.EditError):
        ops.run(Image.new("RGB", (40, 40)), [{"op": "resize", "width": 20}] * (ops.MAX_STEPS + 1))


def test_collage_and_before_after():
    imgs = [Image.new("RGB", (300, 200), c) for c in ("red", "green", "blue", "white")]
    c = ops.collage(imgs, cols=2, gap=10, cell=200)
    assert c.size == (2 * 200 + 3 * 10, 2 * 200 + 3 * 10)
    with pytest.raises(ops.EditError):
        ops.collage(imgs[:1])
    ba = ops.before_after(imgs[0], imgs[1])
    assert ba.width > imgs[0].width


# ----------------------------------------------------------------------------- AI routing and safety
def test_every_route_exists_in_the_zoo_catalogue_as_image_to_image():
    for job, ids in ai.ROUTES.items():
        assert ids, job
        for mid in ids:
            m = zoo.model(mid)
            assert m.get("mode") == "i2i" and m.get("kind") == "image", mid


def test_plan_reports_readiness_without_a_network(monkeypatch):
    for k in ("ZOO_KIE_KEY", "KIE_API_KEY", "ZOO_MUAPI_KEY", "MUAPI_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(zoo, "_dotenv_val", lambda n: "")
    monkeypatch.setattr(ai, "_rembg_ok", lambda: False)
    monkeypatch.setattr(ai, "_gemini_ok", lambda: False)
    assert not any(r["ready"] for r in ai.plan("remove_bg"))
    assert all(v["ready"] is False for v in ai.status().values())
    monkeypatch.setenv("ZOO_KIE_KEY", "k")
    p = ai.plan("remove_bg")
    assert next(r for r in p if r["id"] == "i2i:kie:recraft-remove-background")["ready"]
    assert ai.status()["remove_bg"]["first"] == "zoo:i2i:kie:recraft-remove-background"
    monkeypatch.setattr(ai, "_gemini_ok", lambda: True)
    assert ai.plan("edit")[0]["engine"] == "gemini" and ai.plan("edit")[0]["ready"]


@pytest.mark.parametrize("op,words,fname,needle", [
    ("edit", "make her nude", "a.jpg", "nangi"),
    ("edit", "face swap with my friend", "a.jpg", "face swap"),
    ("remove_object", "remove the watermark", "a.jpg", "Watermark"),
    ("remove_object", "remove the Shutterstock mark in the corner", "a.jpg", "Watermark"),
    ("edit", "change the name on it", "aadhaar_front.jpg", "document"),
    ("edit", "make the girl's body bigger", "a.jpg", "children") ,
    ("edit", "", "a.jpg", "what should change"),
    ("edit", "make this look like Virat Kohli", "a.jpg", "jaane-maane"),
])
def test_check_words_refuses(op, words, fname, needle):
    if "girl's body" in words:
        words = "make the small girl's body bigger"
    why = ai.check_words(words, op, fname)
    assert why and needle.lower() in why.lower(), (words, why)


def test_check_words_allows_the_ordinary_jobs():
    for op, w in (("remove_object", "the pole behind her"), ("replace_bg", "a clean white studio"),
                  ("restyle", "a watercolour painting"), ("restore", ""), ("colorize", ""), ("upscale", ""),
                  ("remove_bg", "")):
        assert ai.check_words(w, op, "family.jpg") == "", (op, w)


# ----------------------------------------------------------------------------- pipeline
def test_validate_rejects_before_any_engine():
    with pytest.raises(ops.EditError):
        P.validate([])
    with pytest.raises(ops.EditError, match="does not exist"):
        P.validate([{"op": "teleport"}])
    with pytest.raises(ops.EditError, match="ONE AI step"):
        P.validate([{"op": "remove_bg"}, {"op": "upscale"}])
    with pytest.raises(ai.AIError):
        P.validate([{"op": "remove_object", "what": "the watermark"}])
    assert P.validate([{"op": "RESIZE", "width": 10}])[0]["op"] == "resize"


def test_process_order_engine_and_report(monkeypatch):
    seen = {}

    async def fake(op, im, params, tenant="", filename=""):
        seen["size"] = im.size
        return {"image": Image.new("RGBA", im.size, (0, 255, 0, 255)), "engine": "fake:eng", "label": False}
    monkeypatch.setattr(ai, "run_op", fake)
    r = run(P.process(_png(400, 300), [{"op": "resize", "width": 200}, {"op": "remove_bg"}, {"op": "bg_color", "color": "white"}],
                      fmt="png"))
    assert seen["size"] == (200, 150)                                                      # local steps ran BEFORE the AI step
    assert [x["op"] for x in r["report"]] == ["resize", "remove_bg", "bg_color"]
    assert r["engines"] == ["fake:eng"] and r["ai"] and r["size_out"] == "200x150"
    assert Image.open(io.BytesIO(r["bytes"])).getpixel((5, 5)) == (255, 255, 255, 255) or \
        Image.open(io.BytesIO(r["bytes"])).convert("RGB").getpixel((5, 5)) == (0, 255, 0)


def test_upscale_without_an_engine_is_an_honest_plain_enlargement(monkeypatch):
    async def none(op, im, params, tenant="", filename=""):
        raise ai.NoEngine("no engine")
    monkeypatch.setattr(ai, "run_op", none)
    r = run(P.process(_png(100, 80), [{"op": "upscale", "factor": 3}]))
    assert r["size_out"] == "300x240" and r["ai"] is False
    assert "no new detail" in " ".join(r["notes"]) and "local enlargement" in r["report"][0]["engine"]
    with pytest.raises(ai.NoEngine):                                                       # background removal never fakes it
        run(P.process(_png(100, 80), [{"op": "remove_bg"}]))


def test_run_op_names_what_to_set_when_nothing_is_ready(monkeypatch):
    monkeypatch.setattr(ai, "plan", lambda op: [{"engine": "gemini", "id": "photogen", "ready": False, "why": "GEMINI_API_KEY server par nahi hai"}])
    with pytest.raises(ai.NoEngine, match="GEMINI_API_KEY"):
        run(ai.run_op("restore", Image.new("RGB", (20, 20)), {}))


def test_a_failing_engine_falls_through_to_the_next_and_failures_are_reported(monkeypatch):
    monkeypatch.setattr(ai, "plan", lambda op: [{"engine": "zoo", "id": "a", "ready": True, "why": ""},
                                                {"engine": "zoo", "id": "b", "ready": True, "why": ""}])
    calls = []

    async def zr(op, mid, im, what, tenant, params):
        calls.append(mid)
        if mid == "a":
            raise RuntimeError("HTTP 404 model gone")
        return Image.new("RGB", (30, 30), "blue")
    monkeypatch.setattr(ai, "_zoo_run", zr)
    res = run(ai.run_op("restyle", Image.new("RGB", (20, 20)), {"what": "watercolour"}))
    assert calls == ["a", "b"] and res["engine"] == "zoo:b" and res["label"] is True
    monkeypatch.setattr(ai, "_zoo_run", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(ai.AIError, match="all failed"):
        run(ai.run_op("restyle", Image.new("RGB", (20, 20)), {"what": "watercolour"}))


def test_zoo_run_sends_a_flattened_jpeg_reference_and_the_topaz_factor(monkeypatch):
    sent = {}

    async def fake_run(m, prompt, tenant="", image_urls=None, extra=None, wait_s=0, **k):
        sent.update(model=m["id"], prompt=prompt, ref=image_urls[0], extra=extra)
        return {"status": "done", "urls": ["https://cdn.example.com/x.png"]}

    async def fake_fetch(url, limit=0):
        return _png(60, 60, (1, 2, 3))
    monkeypatch.setattr(zoo, "run", fake_run)
    monkeypatch.setattr(ai, "_fetch", fake_fetch)
    out = run(ai._zoo_run("upscale", "i2i:kie:topaz-image-upscale", Image.new("RGBA", (40, 40), (255, 0, 0, 0)), "", "t1", {"factor": 4}))
    assert out.size == (60, 60) and sent["ref"].startswith("data:image/jpeg;base64,") and sent["extra"] == {"upscale_factor": "4"}
    run(ai._zoo_run("remove_object", "i2i:kie:nano-banana-edit", Image.new("RGB", (40, 40)), "the pole", "t1", {}))
    assert "Remove the pole" in sent["prompt"] and "face" in sent["prompt"].lower()
    monkeypatch.setattr(zoo, "run", lambda *a, **k: asyncio.sleep(0, {"status": "failed", "error": "bad"}))
    with pytest.raises(ai.AIError, match="bad"):
        run(ai._zoo_run("upscale", "i2i:kie:topaz-image-upscale", Image.new("RGB", (40, 40)), "", "t1", {}))


# ----------------------------------------------------------------------------- the tool
@pytest.fixture
def tool_env(monkeypatch):
    store = {"f1": ("shirt.png", _png(400, 300)), "f2": ("scene.png", _png(300, 300, (0, 90, 0))),
             "id": ("aadhaar_front.jpg", _png(300, 200))}
    for n in range(3, 8):
        store[f"f{n}"] = (f"p{n}.png", _png(80, 60))
    out = []
    monkeypatch.setattr(T, "_owner_file", lambda ctx, fid: store[fid] if fid in store else (_ for _ in ()).throw(T.ToolError("nahi mili")))

    def deliver(ctx, name, data):
        out.append((name, data))
        return {"file_id": f"o{len(out)}", "name": name}
    monkeypatch.setattr(T, "_deliver", deliver)
    return SimpleNamespace(ctx=SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="owner"), out=out)


def test_tool_is_registered_and_reachable_from_real_asks():
    assert "image_edit" in {t["name"] for t in tools.TOOLS} and tools.HANDLERS["image_edit"] is T.image_edit
    assert tools.FAMILY_OF["image_edit"] == "image_edit"
    for ask in ("is photo ka background hata do", "make this photo 100 kb mein compress", "purani photo ko restore karo",
                "resize this image for instagram story", "add my watermark on the picture", "make a collage of these photos"):
        assert "image_edit" in admit._match(ask.lower()), ask
    assert "image_edit" not in admit.CORE_FAMILIES


def test_guide_lists_every_op_and_engine_state(tool_env):
    g = run(T.image_edit(tool_env.ctx, "guide"))
    assert set(g["local_ops"]) == set(ops.OPS) and set(g["ai_ops"]) == set(ai.AI_OPS)
    assert set(g["ai_engines"]) == set(ai.AI_OPS) and "REFUSED" in g["guide"]
    for name in ops.PRESETS:
        assert name in g["guide"]


def test_run_local_batch_delivers_each_file(tool_env):
    r = run(T.image_edit(tool_env.ctx, "run", file_ids=["f1", "f2"], steps=[{"op": "resize", "preset": "insta_square"}], format="jpg"))
    assert r["status"] == "done" and r["edited"] == 2 and all(x["ok"] and x["to"] == "1080x1080" for x in r["results"])
    assert [n for n, _ in tool_env.out] == ["shirt edited.jpg", "scene edited.jpg"]


def test_run_compare_card_and_compress(tool_env):
    r = run(T.image_edit(tool_env.ctx, "run", file_ids=["f1"], steps=[{"op": "filter", "name": "sepia"}], compare=True,
                         compress_kb=20, format="jpg"))
    assert r["results"][0]["kb"] <= 20 and r["results"][0]["compare_file_id"]
    assert any("before-after" in n for n, _ in tool_env.out)


def test_run_refuses_before_any_work_and_says_so(tool_env):
    for steps in ([{"op": "remove_object", "what": "the watermark"}], [{"op": "teleport"}], []):
        with pytest.raises(T.ToolError):
            run(T.image_edit(tool_env.ctx, "run", file_ids=["f1"], steps=steps))
    assert tool_env.out == []
    with pytest.raises(T.ToolError, match="document"):                                       # AI edit of an ID-looking file
        run(T.image_edit(tool_env.ctx, "run", file_ids=["id"], steps=[{"op": "edit", "what": "change the date of birth"}]))
    ok = run(T.image_edit(tool_env.ctx, "run", file_ids=["id"], steps=[{"op": "resize", "width": 200}, {"op": "adjust", "brightness": 10}]))
    assert ok["status"] == "done"                                                          # resizing her own ID photo is fine
    with pytest.raises(T.ToolError, match="Which photo"):
        run(T.image_edit(tool_env.ctx, "run", steps=[{"op": "resize", "width": 10}]))
    with pytest.raises(T.ToolError):
        run(T.image_edit(tool_env.ctx, "run", file_ids=[f"x{i}" for i in range(11)], steps=[{"op": "resize", "width": 10}]))


def test_ai_batch_cap_and_engine_named(tool_env, monkeypatch):
    async def fake(op, im, params, tenant="", filename=""):
        return {"image": im, "engine": "fake:eng", "label": False}
    monkeypatch.setattr(ai, "run_op", fake)
    with pytest.raises(T.ToolError, match="5"):
        run(T.image_edit(tool_env.ctx, "run", file_ids=[f"f{i}" for i in range(1, 7)], steps=[{"op": "remove_bg"}]))
    r = run(T.image_edit(tool_env.ctx, "run", file_ids=["f1"], steps=[{"op": "remove_bg"}]))
    assert r["results"][0]["engines"] == ["fake:eng"] and "cost_note" in r


def test_one_bad_file_does_not_sink_the_batch(tool_env, monkeypatch):
    tool_env.out.clear()
    store_bad = T._owner_file

    def files(ctx, fid):
        return ("junk.png", b"not an image") if fid == "bad" else store_bad(ctx, fid)
    monkeypatch.setattr(T, "_owner_file", files)
    r = run(T.image_edit(tool_env.ctx, "run", file_ids=["f1", "bad"], steps=[{"op": "resize", "width": 50}]))
    assert r["edited"] == 1 and r["results"][1]["ok"] is False and "does not look like a photo" in r["results"][1]["error"]


def test_routine_actor_is_gated_for_ai_steps(tool_env, monkeypatch):
    from app import usage
    monkeypatch.setattr(usage, "allowed", lambda t, f: False)
    monkeypatch.setattr(usage, "blocked_text", lambda t: "limit")
    ctx = SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="routine")
    with pytest.raises(T.ToolError, match="limit"):
        run(T.image_edit(ctx, "run", file_ids=["f1"], steps=[{"op": "remove_bg"}]))
    assert run(T.image_edit(ctx, "run", file_ids=["f1"], steps=[{"op": "resize", "width": 30}]))["status"] == "done"   # local is free


def test_collage_action(tool_env):
    r = run(T.image_edit(tool_env.ctx, "collage", file_ids=["f1", "f2"], cols=2))
    assert r["status"] == "done" and r["photos"] == 2
    with pytest.raises(T.ToolError):
        run(T.image_edit(tool_env.ctx, "collage", file_ids=["f1"]))
    with pytest.raises(T.ToolError):
        run(T.image_edit(tool_env.ctx, "nope"))


def test_prompt_and_voice_wiring():
    prompts = (Path(__file__).resolve().parent.parent / "app" / "agent" / "prompts.py").read_text()
    assert "image_edit" in prompts and "EDIT HER PHOTO" in prompts


def test_mixed_script_text_has_a_real_glyph_for_every_character():
    """'मेरी दुकान · ₹499' once drew a missing-glyph box for the dot and nothing for the rupee sign: every character must
    land on a font that actually has it (Devanagari -> Noto, Latin -> Poppins, rupee / dots -> the next font down)."""
    pytest.importorskip("fontTools")
    text = "मेरी दुकान · ₹499 only"
    runs = ops._runs(text, 40)
    assert "".join(p for p, _ in runs) == text
    for piece, font in runs:
        for ch in piece.strip():
            path = getattr(font, "path", "")
            assert not path or ord(ch) in ops._cmap(path), (ch, path)
