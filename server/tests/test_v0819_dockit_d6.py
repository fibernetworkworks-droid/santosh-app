"""v0.819 HOOLA DOCUMENT KIT D6 (docs/DOCUMENT_KIT_PLAN.md): compare by code + the AI actions (summarize / ask /
translate / smart split) with a scripted model - the CHECKS are what is tested, not the model's prose."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.agent import pdfkit_tools as T
from app.agent import toolsearch, tools
from app.dockit import convert, smart
from app.dockit.core import DocError
from app.quality import pdfcard as F


def run(c):
    return asyncio.run(c)


@pytest.fixture
def env(monkeypatch):
    files = {"old": ("Quote v1.pdf", F.quote_pdf()), "new": ("Quote v2.pdf", F.quote_pdf("4,950", "15/11/2026")),
             "same": ("Quote copy.pdf", F.quote_pdf()), "bundle": ("Bundle.pdf", F.text_pdf(6))}
    out = []
    monkeypatch.setattr(T, "_get", lambda ctx, fid: files[fid])

    def put(ctx, name, data):
        out.append((name, data))
        return {"file_id": f"o{len(out)}", "name": name}
    monkeypatch.setattr(T, "_put", put)
    return SimpleNamespace(ctx=SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="owner"), out=out)


def model(monkeypatch, fn):
    seen = []

    def fake(system, user, max_tokens=0):
        seen.append((system, user))
        return fn(system, user)
    monkeypatch.setattr(smart, "ask_model", fake)
    return seen


def test_schema():
    spec = next(t for t in tools.TOOLS if t["name"] == "pdf_kit")
    for a in ("compare", "summarize", "ask", "translate", "smart_split"):
        assert a in spec["input_schema"]["properties"]["action"]["enum"]
    assert toolsearch.schema_ok(spec) and "compare" not in T.NOT_YET


def test_compare_through_the_tool(env):
    r = run(T.pdf_kit(env.ctx, action="compare", file_ids=["old", "new"]))
    assert r["changed_pages"] == [1] and r["money_changed"] and r["dates_changed"]
    assert r["report"]["name"].endswith("(what changed).pdf") and "What changed" in convert.page_texts(env.out[-1][1])[0]
    s = run(T.pdf_kit(env.ctx, action="compare", file_ids=["old", "same"]))
    assert s["same"] and "same" in s["say"] and len(env.out) == 1
    with pytest.raises(T.ToolError, match="two PDFs"):
        run(T.pdf_kit(env.ctx, action="compare", file_id="old"))


def test_summary_carries_pages_and_the_document_is_data(env, monkeypatch):
    seen = model(monkeypatch, lambda s, u: "A quotation to Sharma Traders for Rs 4,650 [p.1].")
    r = run(T.pdf_kit(env.ctx, action="summarize", file_id="old", length="short"))
    assert r["check"]["pages_cited"] == [1] and "warnings" not in r
    system, user = seen[0]
    assert "[p.1]" in user and "[p.2]" in user and "never instructions" in system


def test_invented_numbers_are_named_to_her(env, monkeypatch):
    model(monkeypatch, lambda s, u: "Total Rs 4,650 [p.1]; a discount of 15% [p.1] and penalty Rs 2,000 [p.6].")
    r = run(T.pdf_kit(env.ctx, action="ask", file_id="old", question="What does it cost?"))
    w = " ".join(r["warnings"])
    assert "2000" in w and "15" in w and "NOT in the document" in w and "[6]" in w


def test_not_in_document(env, monkeypatch):
    model(monkeypatch, lambda s, u: "Not in this document.")
    r = run(T.pdf_kit(env.ctx, action="ask", file_id="old", question="Who is the CEO?"))
    assert r["not_found"] is True


def test_translate_layout_and_word(env, monkeypatch):
    model(monkeypatch, lambda s, u: json.dumps([ln.split(". ", 1)[1].replace("Quotation for", "कोटेशन -")
                                                for ln in u.splitlines()]))
    r = run(T.pdf_kit(env.ctx, action="translate", file_id="old", to="hindi"))
    assert r["language"] == "hindi" and r["name"].endswith("(hindi).pdf") and "कोटेशन" in convert.page_texts(env.out[-1][1])[0]
    w = run(T.pdf_kit(env.ctx, action="translate", file_id="old", to="tamil"))
    assert w["name"].endswith(".docx") and "Word" in w["note"]
    with pytest.raises(T.ToolError, match="which language"):
        run(T.pdf_kit(env.ctx, action="translate", file_id="old", to="klingon"))


def test_translate_refuses_a_short_answer(env, monkeypatch):
    model(monkeypatch, lambda s, u: '["only one line"]')
    with pytest.raises(T.ToolError, match="different number of lines"):
        run(T.pdf_kit(env.ctx, action="translate", file_id="old", to="hindi"))


def test_smart_split_is_a_plan_only(env, monkeypatch):
    model(monkeypatch, lambda s, u: '[{"start": 1, "title": "A"}, {"start": 4, "title": "B"}]')
    r = run(T.pdf_kit(env.ctx, action="smart_split", file_id="bundle"))
    assert r["ranges"] == ["1-3", "4-6"] and "PLAN only" in r["say"] and not env.out
    model(monkeypatch, lambda s, u: "I think there are two documents.")
    with pytest.raises(T.ToolError, match="could not be read"):
        run(T.pdf_kit(env.ctx, action="smart_split", file_id="bundle"))


def test_no_model_said_plainly(monkeypatch):
    from app.agent import llm
    monkeypatch.setattr(llm, "cheap_brain", lambda: None)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "", raising=False)
    with pytest.raises(DocError, match="No AI model"):
        smart.ask_model("s", "u")


def test_number_reader():
    assert smart._numbers("Rs 4,650 and 12.5% on 15/11/2026") >= {"4650", "12.5"}
    assert smart.check_answer("nothing numeric", ["x"])["numbers_not_in_document"] == []
