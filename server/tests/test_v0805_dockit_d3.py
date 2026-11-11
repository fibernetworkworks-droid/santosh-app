"""v0.805 HOOLA DOCUMENT KIT D3 (docs/DOCUMENT_KIT_PLAN.md): protect / unlock / true redaction, and the one-time
pages that keep every password out of the chat and away from the model."""
import asyncio
import io
import json
from types import SimpleNamespace

import pikepdf
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent import pdfkit_tools as T
from app.agent import toolsearch, tools
from app.dockit import api, convert, secure, vault
from app.dockit.core import DocError
from app.quality import pdfcard as F


def run(c):
    return asyncio.run(c)


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("PC_FILES_DIR", str(tmp_path / "pc_files"))
    from app.config import get_settings
    get_settings.cache_clear()
    vault._MEM.clear()
    locked = secure.protect(F.text_pdf(2), "Her-Own-Pass9", ["print"])
    files = {"ids": ("Statement.pdf", F.id_pdf()), "r": ("Report.pdf", F.text_pdf(3)), "lock": ("Bank.pdf", locked),
             "restr": ("Restricted.pdf", secure.protect(F.text_pdf(1), "", ["print"], open_lock=False))}
    out = []

    def get(ctx, fid):
        if fid not in files:
            raise T.ToolError("not found")
        return files[fid]

    def put(ctx, name, data):
        out.append((name, data))
        return {"file_id": f"o{len(out)}", "name": name}
    monkeypatch.setattr(T, "_get", get)
    monkeypatch.setattr(T, "_put", put)
    monkeypatch.setattr(api, "_file", lambda row: files[row["payload"]["file_id"]])
    monkeypatch.setattr(api, "_deliver", lambda row, name, data: out.append((name, data)) or {"file_id": "x"})
    app = FastAPI()
    app.include_router(api.router)
    yield SimpleNamespace(ctx=SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="owner"), out=out,
                          web=TestClient(app), files=files)
    get_settings.cache_clear()


def token_of(link: str) -> str:
    return link.rsplit("/", 1)[1]


def test_schema_cannot_even_carry_a_password():
    spec = next(t for t in tools.TOOLS if t["name"] == "pdf_kit")
    props = spec["input_schema"]["properties"]
    assert props["password"]["enum"] == ["hoola", "mine"]
    for a in ("protect", "unlock", "redact", "redact_apply"):
        assert a in props["action"]["enum"]
    assert toolsearch.schema_ok(spec)
    assert "never" in T.GUIDE.lower() and "one-time" in T.GUIDE


def test_protect_hoola_password_never_reaches_the_model_or_the_chat(env, monkeypatch):
    monkeypatch.setattr(secure, "make_password", lambda: "Zq7K-mW4p-Tn8R")
    r = run(T.pdf_kit(env.ctx, action="protect", file_id="r"))
    assert "Zq7K-mW4p-Tn8R" not in json.dumps(r)                   # not in what the model reads
    name, locked = env.out[-1]
    assert b"Zq7K-mW4p-Tn8R" not in locked
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(io.BytesIO(locked))
    with pikepdf.open(io.BytesIO(locked), password="Zq7K-mW4p-Tn8R") as p:
        assert len(p.pages) == 3
    tok = token_of(r["password_link"])
    g = env.web.get(f"/pdf/key/{tok}")
    assert g.status_code == 200 and "Zq7K" not in g.text and "Show the password" in g.text   # a GET never reveals
    assert g.headers["cache-control"] == "no-store" and g.headers["referrer-policy"] == "no-referrer"
    p = env.web.post(f"/pdf/key/{tok}")
    assert "Zq7K-mW4p-Tn8R" in p.text
    assert env.web.post(f"/pdf/key/{tok}").status_code == 410                                  # once only
    assert env.web.get(f"/pdf/key/{tok}").status_code == 410


def test_protect_with_her_own_password_typed_on_the_page(env):
    r = run(T.pdf_kit(env.ctx, action="protect", file_id="r", password="mine", allow=["print"]))
    assert "link" in r and not env.out
    tok = token_of(r["link"])
    assert env.web.post(f"/pdf/key/{tok}", data={"p1": "Abcdefg1x", "p2": "Abcdefg1y"}).status_code == 400
    assert env.web.post(f"/pdf/key/{tok}", data={"p1": "short", "p2": "short"}).status_code == 400
    ok = env.web.post(f"/pdf/key/{tok}", data={"p1": "Meri-Dukaan-2026", "p2": "Meri-Dukaan-2026"})
    assert ok.status_code == 200 and "is locked" in ok.text and "Meri-Dukaan" not in ok.text
    name, locked = env.out[-1]
    with pikepdf.open(io.BytesIO(locked), password="Meri-Dukaan-2026") as p:
        assert p.allow.print_highres and not p.allow.extract
    assert env.web.post(f"/pdf/key/{tok}", data={"p1": "Meri-Dukaan-2026", "p2": "Meri-Dukaan-2026"}).status_code == 410


def test_restrictions_only_lock_and_unlock_at_once(env):
    r = run(T.pdf_kit(env.ctx, action="protect", file_id="r", open_lock=False, allow=["print"]))
    assert "not a real lock" in r["say"]
    u = run(T.pdf_kit(env.ctx, action="unlock", file_id="restr"))
    assert "restrictions" in u["removed"]
    with pikepdf.open(io.BytesIO(env.out[-1][1])) as p:
        assert not p.is_encrypted


def test_unlock_open_password_only_on_the_page_with_five_tries(env):
    r = run(T.pdf_kit(env.ctx, action="unlock", file_id="lock"))
    assert "never" in r["say"] and not env.out
    tok = token_of(r["link"])
    for left in (4, 3, 2, 1):
        w = env.web.post(f"/pdf/key/{tok}", data={"p1": "wrong-Guess-1"})
        assert w.status_code == 400 and f"{left} tries" in w.text
    assert env.web.post(f"/pdf/key/{tok}", data={"p1": "wrong-Guess-1"}).status_code == 403
    assert env.web.post(f"/pdf/key/{tok}", data={"p1": "Her-Own-Pass9"}).status_code == 410   # closed for good
    r2 = run(T.pdf_kit(env.ctx, action="unlock", file_id="lock"))
    ok = env.web.post(f"/pdf/key/{token_of(r2['link'])}", data={"p1": "Her-Own-Pass9"})
    assert ok.status_code == 200 and "unlocked" in ok.text
    with pikepdf.open(io.BytesIO(env.out[-1][1])) as p:
        assert len(p.pages) == 2 and not p.is_encrypted


def test_redact_preview_then_apply(env):
    pv = run(T.pdf_kit(env.ctx, action="redact", file_id="ids", find=["Ramesh Kumar"],
                       presets=["aadhaar", "pan", "card", "account", "phone", "email"]))
    assert pv["total"] >= 7 and pv["scanned_pages"] == [3] and "NOT mean nothing" in pv["warning"]
    flat = json.dumps(pv)
    assert "ABCPE1234F" not in flat and "98765 43210" not in flat and "4111 1111 1111 1111" not in flat  # masked only
    assert "ABCPE1234F" in convert.page_texts(env.out[-1][1])[0]                                       # preview keeps
    done = run(T.pdf_kit(env.ctx, action="redact_apply", redact_id=pv["redact_id"]))
    text = " ".join(convert.page_texts(env.out[-1][1]))
    assert "ABCPE1234F" not in text and "Ramesh" not in text and "nothing private" in text
    assert done["pages_redrawn"] == [1] and "none left" in done["checked"]
    with pytest.raises(T.ToolError, match="expired"):
        run(T.pdf_kit(env.ctx, action="redact_apply", redact_id=pv["redact_id"]))


def test_redact_apply_refuses_another_tenant(env):
    pv = run(T.pdf_kit(env.ctx, action="redact", file_id="ids", presets=["pan"]))
    other = SimpleNamespace(tenant_id="t2", conversation_id="c9", actor="owner")
    with pytest.raises(T.ToolError, match="not hers"):
        run(T.pdf_kit(other, action="redact_apply", redact_id=pv["redact_id"]))


def test_redact_areas_and_nothing_found(env):
    pv = run(T.pdf_kit(env.ctx, action="redact", file_id="r", areas=[{"page": 1, "x": 20, "y": 20, "w": 120, "h": 15}]))
    assert pv["total"] == 1
    none = run(T.pdf_kit(env.ctx, action="redact", file_id="r", presets=["aadhaar"]))
    assert none["total"] == 0 and "Nothing" in none["say"]


def test_redaction_refuses_to_deliver_if_anything_is_left(monkeypatch):
    pdf = F.id_pdf()
    f = secure.find(pdf, ["pan"])
    monkeypatch.setattr(secure, "verify", lambda data, found, presets: ["ABCPE1234F"])
    with pytest.raises(DocError, match="nothing was delivered"):
        secure.redact(pdf, f["hits"])


def test_vault_seals_on_disk_with_a_secret_key(monkeypatch, tmp_path):
    monkeypatch.setenv("PC_FILES_DIR", str(tmp_path / "pc"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-the-vault")
    from app.config import get_settings
    get_settings.cache_clear()
    vault._MEM.clear()
    try:
        tok = vault.put("show_password", "t", "c", {"password": "Plain-Text-77", "meta": {"name": "x"}})
        disk = (tmp_path / "dockit_vault" / f"{tok}.json").read_text()
        assert "Plain-Text-77" not in disk and "sealed" in disk
        assert vault.take(tok)["payload"]["password"] == "Plain-Text-77"
        assert vault.take(tok) is None and not (tmp_path / "dockit_vault" / f"{tok}.json").exists()
        assert vault.peek("../../etc/passwd") is None
    finally:
        get_settings.cache_clear()


def test_password_rules_and_generated_passwords():
    pw = {secure.make_password() for _ in range(50)}
    assert len(pw) == 50 and all(secure.password_problem(p) == "" and len(p) == 14 for p in pw)
    assert secure.password_problem("abc") and secure.password_problem("alllowercase")
    with pytest.raises(DocError):
        secure.protect(F.text_pdf(1), "weak", ["print"])


def test_router_is_mounted_in_main():
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "app" / "main.py").read_text()
    assert "from .dockit.api import router as dockit_router" in src and "app.include_router(dockit_router)" in src
