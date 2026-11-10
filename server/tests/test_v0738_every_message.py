"""v0.738 PARITY GAP 1 (owner: "TILL I TOPUP -- CONTINUE OUR THIS WORK"): every message reaches the model, like Claude
chat. The research-plan gate no longer answers for it, and stop words still stop the work at once, but the model writes
the reply. (The OTP / CAPTCHA hand-over stays before the model: a secret never reaches it.)"""
from __future__ import annotations

import asyncio
import json

from app.db import Message, session
from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, txt  # noqa: F401
from tests.test_v0649_sach_mein_roko import T, _chat, _job, _row


def _on(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("CHAT_EVERY_MESSAGE", "true")
    get_settings.cache_clear()


def test_switch_default_on(env):
    from app.config import Settings
    assert Settings.model_fields["chat_every_message"].default is True


def test_a_big_research_ask_goes_straight_to_the_model(gz, monkeypatch):  # noqa: F811
    from app.agent import research_plan, santosh
    _on(monkeypatch)
    called = []

    async def gate(*a, **k):
        called.append(1)
        return {"action": "say", "text": "PLAN CARD"}
    monkeypatch.setattr(research_plan, "gate", gate)
    _set_brain(monkeypatch, FakeBrain([([txt("Here is the research.")], "end_turn")]))
    out = asyncio.run(santosh.run_turn(gz["conv"], "Do deep research on solar subsidies in Maharashtra with official sources",
                                       tenant_id="default"))
    assert not called and "Here is the research." in out and "PLAN CARD" not in out


def test_the_gate_still_answers_with_the_switch_off(gz, monkeypatch):  # noqa: F811
    from app.agent import research_plan, santosh

    async def gate(*a, **k):
        return {"action": "say", "text": "PLAN CARD"}
    monkeypatch.setattr(research_plan, "gate", gate)
    out = asyncio.run(santosh.run_turn(gz["conv"], "Do deep research on solar subsidies", tenant_id="default"))
    assert out == "PLAN CARD"


def test_stop_words_stop_the_job_and_the_model_writes_the_reply(env, monkeypatch):
    from app.agent import santosh
    from app.site import service as S
    _on(monkeypatch)
    monkeypatch.setattr(S, "stop", lambda tenant, ref: {"ok": True})
    _chat("c8")
    _job("c8", "site_board:b8", "Bakery site")
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Done - I stopped the Bakery site build.")], "end_turn")]))
    out = asyncio.run(santosh.run_turn("c8", "isko cancel kar do", T, True))
    santosh._stopped.discard("c8")
    assert _row("site_board:b8") == ("stopped", "cancelled")           # stopped at once, before the model
    assert "stopped the Bakery site" in out
    sent = json.dumps(brain.seen[0]["messages"], ensure_ascii=False)
    assert "isko cancel kar do" in sent and "because she asked to stop" in sent and "Bakery site" in sent
    with session() as s:
        shown = [m.display for m in s.query(Message).filter_by(conversation_id="c8").order_by(Message.id)]
    assert shown[0] == "isko cancel kar do" and "[Done by the system" not in shown[0]


# ---------------------------------------------------------------- gap 9a: one way to make a file (code)

CODE = r'''
from docx import Document
d = Document(); d.add_heading("Quotation", 1); d.add_paragraph("Total Rs 4,250"); d.save("quote.docx")
from pptx import Presentation
p = Presentation(); s = p.slides.add_slide(p.slide_layouts[1]); s.shapes.title.text = "Plan"; p.save("plan.pptx")
from reportlab.pdfgen import canvas
c = canvas.Canvas("bill.pdf"); c.drawString(72, 720, "Bill Rs 4,250"); c.save()
print("made")
'''


def _run(monkeypatch, on: bool):
    from app.config import get_settings
    from app.pylab import service as PL
    monkeypatch.setenv("CHAT_FILES_BY_CODE", "true" if on else "false")
    get_settings.cache_clear()
    return PL.run("default", CODE, conv="", purpose="files", timeout_s=120)


def test_pylab_makes_word_slides_and_pdf_into_the_chat(env, monkeypatch):
    out = _run(monkeypatch, True)
    assert out["ok"], out.get("error")
    kept = {o["name"]: o["kept"] for o in out["outputs"]}
    assert kept == {"quote.docx": True, "plan.pptx": True, "bill.pdf": True}
    assert all(o.get("file_id") for o in out["outputs"])


def test_switch_off_keeps_only_the_old_file_kinds(env, monkeypatch):
    out = _run(monkeypatch, False)
    assert out["ok"] and not any(o["kept"] for o in out["outputs"])


def test_the_prompt_says_files_are_made_with_code(env, monkeypatch):
    from app.agent import core_prompt
    from app.config import get_settings
    monkeypatch.setenv("CHAT_FILES_BY_CODE", "true")
    get_settings.cache_clear()
    on = core_prompt.core_prompt("default", True)
    assert "write them with pylab" in on and "python-docx" in on
    monkeypatch.setenv("CHAT_FILES_BY_CODE", "false")
    get_settings.cache_clear()
    assert "come from the file tools" in core_prompt.core_prompt("default", True)
