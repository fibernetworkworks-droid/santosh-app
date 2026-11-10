"""v0.735 ALL GLM (owner: "WE WILL TEST ONE BY ONE MOVE EVERY THINH ON GLM 5.3 FLASH"): pictures, PDFs, the website
architect and the outage path all stay on GLM-5.3-Flash, each behind its own switch so she can try them one by one."""
from __future__ import annotations

import base64
import io
import json

import pytest


@pytest.fixture()
def glm(env, monkeypatch):
    from app.config import get_settings
    for k, v in {"GLM_API_KEY": "test-glm", "ANTHROPIC_API_KEY": "test-claude", "CHAT_LLM": "glm",
                 "GLM_BASE_URL": "https://openrouter.ai/api/v1", "GLM_MODEL": "z-ai/glm-5.3-flash",
                 "GLM_IMAGES": "true", "GLM_PDF": "true", "ARCHITECT_OPUS": "false",
                 "CLAUDE_ALL_GLM_FALLBACK": "false"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def _flip(monkeypatch, k, v):
    from app.config import get_settings
    monkeypatch.setenv(k, v)
    get_settings.cache_clear()


PNG = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()


def _img_msg():
    return [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                                      "data": PNG}},
                                         {"type": "text", "text": "what is in this picture"}]}]


def _pdf(text_pages: list[str]) -> str:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for t in text_pages:
        if t:
            y = 800
            for line in t.split("\n"):
                c.drawString(40, y, line)
                y -= 14
        c.showPage()
    c.save()
    return base64.b64encode(buf.getvalue()).decode()


def _pdf_msg(data):
    return [{"role": "user", "content": [{"type": "document", "source": {"type": "base64",
                                                                         "media_type": "application/pdf", "data": data}},
                                         {"type": "text", "text": "summarise"}]}]


def test_defaults_are_all_glm(env):
    from app.config import Settings
    f = Settings.model_fields
    assert f["glm_images"].default is True and f["glm_pdf"].default is True
    assert f["architect_opus"].default is False and f["claude_all_glm_fallback"].default is False


def test_a_picture_stays_on_glm_and_is_sent_as_a_picture(glm):
    from app.agent import llm
    assert llm.choose(_img_msg()) == "glm"
    msgs, _ = llm.to_openai("sys", [], _img_msg())
    body = json.dumps(msgs)
    assert "image_url" in body and PNG in body


def test_picture_switch_off_gives_the_old_routing(glm, monkeypatch):
    from app.agent import llm
    _flip(monkeypatch, "GLM_IMAGES", "false")
    assert llm.choose(_img_msg()) == "claude"
    msgs, _ = llm.to_openai("sys", [], _img_msg())
    assert "image_url" not in json.dumps(msgs)


def test_a_text_pdf_becomes_its_text(glm):
    from app.agent import llm
    words = " ".join(f"word{i}" for i in range(40))
    data = _pdf([f"Invoice total Rs 4,250 due 12 Nov\n{words}"])
    assert llm.choose(_pdf_msg(data)) == "glm"
    msgs, _ = llm.to_openai("sys", [], _pdf_msg(data))
    body = json.dumps(msgs)
    assert "4,250" in body and "image_url" not in body


def test_a_scanned_pdf_becomes_page_pictures(glm):
    from app.agent import llm
    parts = llm.pdf_parts(_pdf_msg(_pdf(["", ""]))[0]["content"][0])
    assert "scanned PDF" in parts[0]["text"]
    pics = [p for p in parts if p["type"] == "image_url"]
    assert len(pics) == 2 and pics[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_a_broken_pdf_never_raises(glm):
    from app.agent import llm
    out = llm.pdf_parts({"type": "document", "source": {"type": "base64", "data": "!!!notbase64"}})
    assert out and out[0]["type"] == "text"


def test_pdf_switch_off_gives_the_old_routing(glm, monkeypatch):
    from app.agent import llm
    _flip(monkeypatch, "GLM_PDF", "false")
    assert llm.choose(_pdf_msg(_pdf(["hello"]))) == "claude"


def test_the_sdk_door_keeps_pictures_and_pdfs(glm, monkeypatch):
    from app import glmdoor
    monkeypatch.setattr(glmdoor, "brain", lambda: "glm")
    assert glmdoor.has_media(_img_msg()) is False
    assert glmdoor.has_media(_pdf_msg("x")) is False
    _flip(monkeypatch, "GLM_PDF", "false")
    assert glmdoor.has_media(_pdf_msg("x")) is True and glmdoor.has_media(_img_msg()) is False


def test_the_architect_is_not_forced_onto_claude(glm, monkeypatch):
    from app import glmdoor
    from app.site import architect
    seen = []
    monkeypatch.setattr(architect.AI, "ask_json", lambda *a, **k: seen.append(glmdoor.CLAUDE_ONLY.get()) or {})
    architect._ask("s", "p", 100, "site_art")
    _flip(monkeypatch, "ARCHITECT_OPUS", "true")
    architect._ask("s", "p", 100, "site_art")
    assert seen == [False, True]


def test_no_claude_fallback_at_the_door(glm, monkeypatch):
    from app import glmdoor
    assert glmdoor._claude_ok() is False          # a GLM failure is said, never answered by Claude
    _flip(monkeypatch, "CLAUDE_ALL_GLM_FALLBACK", "true")
    assert glmdoor._claude_ok() is True


# ---------------------------------------------------------------- v0.736 a paused GLM is still the chat's model

def _pause(monkeypatch):
    import time
    from app.agent import llm
    monkeypatch.setitem(llm.BREAKERS, "glm", {"fails": 2, "until": time.time() + 600, "paused": 1})


def test_a_paused_glm_is_still_asked_while_it_is_the_only_model(glm, monkeypatch):
    import asyncio
    from app.agent import llm
    _flip(monkeypatch, "CHAT_ONE_MODEL", "true")
    _pause(monkeypatch)
    seen = []

    async def fake(*a, **k):
        seen.append(a[0])
        return [{"type": "text", "text": "ok"}], "end_turn", {}
    monkeypatch.setattr(llm, "_openai_create", fake)
    blocks, _, _ = asyncio.run(llm.openai_create("glm", "s", [], [{"role": "user", "content": "hi"}], 50))
    assert seen == ["glm"] and blocks[0]["text"] == "ok"
    assert llm.describe().endswith("(paused)") and llm.describe().startswith("glm:")
    _flip(monkeypatch, "GLM_PAUSE_ONE_MODEL", "true")
    with pytest.raises(llm.LLMError, match="paused"):
        asyncio.run(llm.openai_create("glm", "s", [], [{"role": "user", "content": "hi"}], 50))


def test_a_paused_glm_never_sends_door_calls_to_claude_without_the_fallback(glm, monkeypatch):
    from app import glmdoor
    _flip(monkeypatch, "CLAUDE_ALL_GLM", "true")
    _pause(monkeypatch)
    assert glmdoor.active() is True              # the picture / background call stays on GLM
    _flip(monkeypatch, "CLAUDE_ALL_GLM_FALLBACK", "true")
    assert glmdoor.active() is False             # old: Claude answers while GLM is paused


def test_a_pause_reads_as_busy_not_something_went_wrong(glm):
    from app.agent import santosh
    line = santosh._friendly_error(RuntimeError("glm paused after repeated failures - another brain answers"))
    assert "busy or unreachable" in line


def test_an_openrouter_key_limit_is_said_plainly(glm, monkeypatch):
    from app.agent import santosh
    monkeypatch.setattr(santosh, "_operator", lambda t: True)
    e = RuntimeError('GLM (OpenRouter) error 403: {"error":{"message":"Key limit exceeded (total limit)."}}')
    line = santosh._friendly_error(e, tenant_id="default")
    assert "spending limit" in line and "openrouter.ai" in line and "something went wrong" not in line
