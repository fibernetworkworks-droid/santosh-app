"""v0.814 HOOLA DOCUMENT KIT D5 (docs/DOCUMENT_KIT_PLAN.md): fillable forms + signing, through the pdf_kit tool and
the real /sign/<key> page, on PDFs made in code."""
import asyncio
import base64
import io
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent import pdfkit_tools as T
from app.agent import toolsearch, tools
from app.dockit import api, convert, forms, sign
from app.dockit.core import DocError
from app.quality import pdfcard as F


def run(c):
    return asyncio.run(c)


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("PC_FILES_DIR", str(tmp_path / "pc"))
    from app.config import get_settings
    get_settings.cache_clear()
    sign._MEM.clear()
    sheet = b"Full name,city\nAsha Rao,Pune\nBad Row,Goa\n"
    files = {"form": ("Admission.pdf", F.blank_form()), "doc": ("Lease.pdf", F.text_pdf(2)),
             "sig": ("sig.jpg", F.signature_photo()), "rows": ("students.csv", sheet)}
    out = []
    monkeypatch.setattr(T, "_get", lambda ctx, fid: files[fid])

    def put(ctx, name, data):
        out.append((name, data))
        return {"file_id": f"o{len(out)}", "name": name}
    monkeypatch.setattr(T, "_put", put)
    delivered = []
    monkeypatch.setattr(api, "_deliver", lambda row, name, data: delivered.append((row["conv"], name, data)))
    app = FastAPI()
    app.include_router(api.router)
    yield SimpleNamespace(ctx=SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="owner"), out=out,
                          files=files, web=TestClient(app), delivered=delivered)
    get_settings.cache_clear()


def test_schema_and_not_yet():
    spec = next(t for t in tools.TOOLS if t["name"] == "pdf_kit")
    for a in ("form_fields", "form_fill", "form_create", "signature_save", "sign", "sign_verify", "sign_request",
              "sign_status", "sign_cancel"):
        assert a in spec["input_schema"]["properties"]["action"]["enum"]
    assert toolsearch.schema_ok(spec)
    assert "compare" in T.NOT_YET and "Aadhaar eSign" in T.NOT_YET


def test_form_fields_fill_and_readback(env):
    f = run(T.pdf_kit(env.ctx, action="form_fields", file_id="form"))
    assert {x["name"] for x in f["fields"]} == {"Full name", "agree", "city", "Sign here"}
    r = run(T.pdf_kit(env.ctx, action="form_fill", file_id="form", values={"Full name": "Asha Rao", "agree": "haan",
                                                                         "city": "MUMBAI"}))
    assert r["filled"]["city"] == "Mumbai" and "read back" in r["checked"]
    got = {x["name"]: x["value"] for x in forms.detect(env.out[-1][1])}
    assert got["Full name"] == "Asha Rao"


def test_form_refusals_are_specific(env):
    with pytest.raises(T.ToolError, match="Did you mean: Full name"):
        run(T.pdf_kit(env.ctx, action="form_fill", file_id="form", values={"Name": "x"}))
    with pytest.raises(T.ToolError, match="Akola, Pune, Mumbai"):
        run(T.pdf_kit(env.ctx, action="form_fill", file_id="form", values={"city": "Delhi"}))
    with pytest.raises(T.ToolError, match="no fillable fields"):
        run(T.pdf_kit(env.ctx, action="form_fill", file_id="doc", values={"a": "b"}))


def test_locker_reference_is_typed_into_the_file_never_shown(env, monkeypatch):
    from app import idvault
    monkeypatch.setattr(idvault, "fill_value", lambda text, tenant: (text.replace("{id:abc123}", "2345 6789 0124"),
                                                                     ["aadhaar"]))
    r = run(T.pdf_kit(env.ctx, action="form_fill", file_id="form", values={"Full name": "{id:abc123}"}))
    assert "2345" not in json.dumps(r) and r["locker_used"] == ["aadhaar"]
    assert {x["name"]: x["value"] for x in forms.detect(env.out[-1][1])}["Full name"] == "2345 6789 0124"


def test_batch_fill_from_a_sheet(env):
    r = run(T.pdf_kit(env.ctx, action="form_fill", file_id="form", rows_file_id="rows", name_from="Full name"))
    assert r["filled"] == 1 and r["failed"][0]["row"] == "Bad Row" and "Pune" in r["failed"][0]["why"]
    assert env.out[-1][0].endswith(".zip")


def test_form_create(env):
    r = run(T.pdf_kit(env.ctx, action="form_create", file_id="doc", fields=[
        {"name": "Tenant", "type": "text", "page": 1, "x": 20, "y": 40}, {"name": "Sign", "type": "signature",
                                                                         "page": 2, "x": 120, "y": 230}]))
    assert len(r["fields_added"]) == 2
    assert {x["name"]: x["kind"] for x in forms.detect(env.out[-1][1])} == {"Tenant": "text", "Sign": "signature"}
    with pytest.raises(T.ToolError, match="same name"):
        run(T.pdf_kit(env.ctx, action="form_create", file_id="doc", fields=[{"name": "A"}, {"name": "A"}]))


def test_signature_save_then_place_and_digital(env):
    with pytest.raises(T.ToolError, match="No signature is saved"):
        run(T.pdf_kit(env.ctx, action="sign", file_id="doc"))
    s = run(T.pdf_kit(env.ctx, action="signature_save", file_id="sig"))
    assert s["saved"] == "signature" and "restart" in s["say"]           # no SECRET_KEY here: said plainly
    p = run(T.pdf_kit(env.ctx, action="sign", file_id="doc", name="Meghana"))
    assert "electronic signature" in p["what_it_is"] and "Meghana" in convert.page_texts(env.out[-1][1], "2")[0]
    d = run(T.pdf_kit(env.ctx, action="sign", file_id="doc", mode="both", name="Meghana"))
    assert "does not prove her legal identity" in d["what_it_is"] and d["certificate"]["name"].endswith("CN=Meghana")
    v = sign.verify(env.out[-1][1], "t1")["signatures"][0]
    assert v["intact"] and v["valid"] and v["her_hoola_certificate"]
    other = sign.verify(env.out[-1][1], "someone-else")["signatures"][0]
    assert other["her_hoola_certificate"] is False                     # another account's certificate is not hers


def test_sign_an_existing_box_and_refuse_twice(env):
    r = run(T.pdf_kit(env.ctx, action="sign", file_id="form", mode="digital", field="Sign here"))
    assert r["signature_field"] == "Sign here"
    env.files["signed"] = ("Signed.pdf", env.out[-1][1])
    with pytest.raises(T.ToolError, match="already signed"):
        run(T.pdf_kit(env.ctx, action="sign", file_id="signed", mode="digital", field="Sign here"))
    with pytest.raises(T.ToolError, match="No signature box named"):
        run(T.pdf_kit(env.ctx, action="sign", file_id="form", mode="digital", field="Nope"))


def test_verify_catches_a_change(env):
    d = sign.digital(F.text_pdf(1), "t1", name="X")["bytes"]
    cut = len(d) // 2
    bad = d[:cut] + bytes([d[cut] ^ 1]) + d[cut + 1:]
    env.files["bad"] = ("Bad.pdf", bad)
    try:
        r = run(T.pdf_kit(env.ctx, action="sign_verify", file_id="bad"))
        assert "changed" in r["say"] or any(not s.get("intact", True) or "error" in s for s in r["signatures"])
    except T.ToolError:
        pass


def _png() -> str:
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    ImageDraw.Draw(im).line([(10, 80), (150, 20), (290, 70)], fill=(10, 10, 80, 255), width=6)
    b = io.BytesIO()
    im.save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def test_signing_request_end_to_end_on_the_real_page(env):
    q = run(T.pdf_kit(env.ctx, action="sign_request", file_id="doc", signers=[{"name": "Ramesh"}, {"name": "Sita"}],
                      message="Please sign the lease"))
    k1, k2 = (x["link"].split("/sign/")[1] for x in q["links"])
    page = env.web.get(f"/sign/{k1}")
    assert page.status_code == 200 and "Please sign the lease" in page.text and "<canvas" in page.text
    csp = page.headers["content-security-policy"]
    assert "script-src 'nonce-" in csp and "unsafe-inline" not in csp.split("script-src")[1].split(";")[0]
    wait = env.web.get(f"/sign/{k2}")
    assert "Waiting for Ramesh" in wait.text
    assert env.web.post(f"/sign/{k1}", data={"sig": _png(), "name": "Ramesh Kumar"}).status_code == 400   # no tick
    ok = env.web.post(f"/sign/{k1}", data={"sig": _png(), "name": "Ramesh Kumar", "agree": "on"})
    assert ok.status_code == 200 and "next person" in ok.text
    assert "already" in env.web.get(f"/sign/{k1}").text or "You have signed" in env.web.get(f"/sign/{k1}").text
    done = env.web.post(f"/sign/{k2}", data={"sig": _png(), "name": "Sita Devi", "agree": "on"})
    assert "Everyone has signed" in done.text
    conv, name, blob = env.delivered[-1]
    assert conv == "c1" and name.endswith("(signed).pdf")
    record = convert.page_texts(blob)[-1]
    assert "Ramesh Kumar" in record and "Sita Devi" in record and "No OTP" in record
    assert sign.verify(blob, "t1")["signatures"][-1]["intact"]
    st = run(T.pdf_kit(env.ctx, action="sign_status", request_id=q["request_id"]))
    assert st["done"] and all(s["signed"] for s in st["signers"])


def test_request_links_are_private_and_cancellable(env):
    q = run(T.pdf_kit(env.ctx, action="sign_request", file_id="doc", signers=[{"name": "A"}]))
    key = q["links"][0]["link"].split("/sign/")[1]
    assert env.web.get("/sign/" + key[:-3] + "zzz").status_code == 404
    assert env.web.get("/sign/../../etc/passwd").status_code in (404, 405)
    other = SimpleNamespace(tenant_id="t2", conversation_id="c2", actor="owner")
    with pytest.raises(T.ToolError):
        run(T.pdf_kit(other, action="sign_status", request_id=q["request_id"]))
    run(T.pdf_kit(env.ctx, action="sign_cancel", request_id=q["request_id"]))
    assert env.web.get(f"/sign/{key}").status_code == 410


def test_signature_photo_cleaning():
    png = sign.clean_signature(F.signature_photo())
    from PIL import Image
    im = Image.open(io.BytesIO(png))
    assert im.mode == "RGBA" and im.getchannel("A").getextrema()[0] == 0     # the paper became transparent
    from PIL import Image as I
    blank = io.BytesIO()
    I.new("RGB", (200, 100), "white").save(blank, "PNG")
    with pytest.raises(DocError, match="No ink"):
        sign.clean_signature(blank.getvalue())


def test_router_mounts_sign_page():
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "app" / "dockit" / "api.py").read_text()
    assert '@router.get("/sign/{key}")' in src and '@router.post("/sign/{key}")' in src
