"""v0.129 photo_banao: make / edit pictures with Gemini image models (model chain with fallback), AI label, refusals,
her own photos only, cost prices, Hoola Network make_image on the live chain."""
import asyncio
import io

import pytest
from PIL import Image

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_bazar import _events
from tests.test_life import conv_ctx


def _png(color=(200, 30, 30), size=(64, 64)):
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "PNG")
    return b.getvalue()


class _Inline:
    def __init__(self, data):
        self.data = data


class _Part:
    def __init__(self, data=None, text=None):
        self.inline_data = _Inline(data) if data else None
        self.text = text


class _Resp:
    def __init__(self, data=None, text=None):
        self.candidates = [type("C", (), {"content": type("X", (), {"parts": [_Part(data, text)]})()})()]
        self.prompt_feedback = None


class FakeModels:
    def __init__(self, dead=(), refuse_aspect=()):
        self.calls, self.dead, self.refuse_aspect = [], set(dead), set(refuse_aspect)

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "aspect": getattr(config, "image_config", None)})
        if model in self.dead:
            raise RuntimeError(f"404 models/{model} is not found for API version v1beta")
        if model in self.refuse_aspect and getattr(config, "image_config", None) is not None:
            raise RuntimeError("400 Invalid argument: image_config.aspect_ratio")
        return _Resp(_png((10, 120, 200), (128, 96)))


@pytest.fixture()
def fake(env, monkeypatch):
    from app import photogen
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key", raising=False)
    photogen._GOOD.clear()
    m = FakeModels()
    monkeypatch.setattr(photogen, "_client", lambda: type("Cl", (), {"models": m})())
    return m


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


def test_make_delivers_labelled_png_and_card(fake):
    from PIL import PngImagePlugin  # noqa: F401
    ctx = conv_ctx()
    out = run("photo_banao", {"action": "make", "prompt": "Diwali greeting with diyas, warm colours, for Insta post"}, ctx)
    assert out["status"] == "done" and out["file_id"] and out["aspect"] == "4:5" and out["quality"] == "fast"
    card = _events(ctx.conversation_id, "photo_made")[-1]
    assert card["file_id"] == out["file_id"] and card["model"] == "gemini-3.1-flash-lite-image" and not card["edit"]
    assert card["url"].startswith("/api/pc/files/")
    from app.mailbox import service as ms
    from pathlib import Path
    data = Path(ms._file_row("default", out["file_id"]).stored_path).read_bytes()
    im = Image.open(io.BytesIO(data))
    assert im.format == "PNG" and im.info.get("ai_generated") == "true"
    assert fake.calls[0]["aspect"] is not None


def test_dead_model_falls_back_and_is_remembered(fake):
    from app import photogen
    fake.dead.add("gemini-3.1-flash-lite-image")
    fake.refuse_aspect.add("gemini-nano-banana-2.1")
    ctx = conv_ctx()
    run("photo_banao", {"action": "make", "prompt": "a cute cartoon chai cup"}, ctx)
    used = [c["model"] for c in fake.calls]
    assert used == ["gemini-3.1-flash-lite-image", "gemini-nano-banana-2.1", "gemini-nano-banana-2.1"]
    assert fake.calls[-1]["aspect"] is None                 # second try without the aspect setting
    assert photogen._GOOD["fast"] == "gemini-nano-banana-2.1"
    fake.calls.clear()
    run("photo_banao", {"action": "make", "prompt": "a red bicycle", "quality": "fast"}, ctx)
    assert fake.calls[0]["model"] == "gemini-nano-banana-2.1"
    fake.calls.clear()
    run("photo_banao", {"action": "make", "prompt": "a red bicycle", "quality": "best"}, ctx)
    assert fake.calls[0]["model"] == "gemini-3-pro-image"          # v0.155: Nano Banana Pro GA id first


def test_edit_uses_her_photo_without_exif(fake):
    from app.mailbox import service as ms
    ctx = conv_ctx()
    with pytest.raises(ToolError):
        run("photo_banao", {"action": "edit", "prompt": "background white karo"}, ctx)
    fid = ms.store_bytes("default", "saree.png", _png((40, 160, 40), (2400, 1800)), "mail").id
    out = run("photo_banao", {"action": "edit", "prompt": "background white karo", "file_ids": [fid]}, ctx)
    assert out["status"] == "done"
    sent = fake.calls[-1]["contents"]
    img = Image.open(io.BytesIO(sent[0].inline_data.data))
    assert img.format == "JPEG" and max(img.size) == 1600 and "Edit the attached photo" in sent[-1]
    assert _events(ctx.conversation_id, "photo_made")[-1]["edit"] is True


def test_refusals_never_reach_the_model(fake):
    ctx = conv_ctx()
    for p in ["mera aadhaar card bana do", "500 ka note banao", "fake bill jaisa asli banao", "nude photo",
              "iska chehra uske upar lagao", "Shah Rukh Khan ke saath meri photo", "Ashoka chakra wala poster"]:
        with pytest.raises(ToolError):
            run("photo_banao", {"action": "make", "prompt": p}, ctx)
    assert fake.calls == []
    from app.photogen import problem
    assert problem("staff ke liye appreciation certificate design") == ""
    assert problem("shop opening poster, sale 5 pm tak") == ""


def test_no_key_and_empty_answer(env, monkeypatch):
    from app import photogen
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "gemini_api_key", "", raising=False)
    with pytest.raises(ToolError) as e:
        run("photo_banao", {"action": "make", "prompt": "a lotus"}, conv_ctx())
    assert "GEMINI_API_KEY" in str(e.value)
    monkeypatch.setattr(get_settings(), "gemini_api_key", "k", raising=False)

    class Talky(FakeModels):
        def generate_content(self, model, contents, config):
            return _Resp(None, "I can't draw that")
    monkeypatch.setattr(photogen, "_client", lambda: type("Cl", (), {"models": Talky()})())
    with pytest.raises(ToolError) as e:
        run("photo_banao", {"action": "make", "prompt": "a lotus"}, conv_ctx())
    assert "can't draw" in str(e.value)


def test_network_make_image_and_prices(fake):
    from app import usage
    from app.net import media
    data = media.make_image("Happy birthday card with balloons")
    assert data[:4] == b"\x89PNG"
    assert media.make_image("bg texture", labelled=False)[:4] == b"\x89PNG"
    assert media.make_image("mera pan card banao") == b""
    p, known = usage.price_of("gemini-3.1-flash-lite-image")
    assert known and p["out"] == 30.0
    assert usage.price_of("gemini-3-pro-image-preview")[0]["out"] == 120.0
    from app.voice import VOICE_TOOL_NAMES
    from app.voiceid.permissions import FAMILY
    assert "photo_banao" in VOICE_TOOL_NAMES and "photo_banao" in FAMILY
