"""v0.144 Makaan suite wiring: tools / inbox biz tools / roles / push conditions / routes / worker ticks, the propagent rent
deal -> rentdesk draft tenancy link, and Devanagari-safe PDFs (indicpdf)."""
import io

import pytest

import app.propagent.models  # noqa: F401
import app.rentdesk.models  # noqa: F401

T = "default"
MODS = ("propagent", "rentdesk", "sitesup", "interior", "archassist", "society")


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    return "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)


def test_tools_inbox_roles_push_registered(env):
    from app.agent import tools
    from app.employee import inbox, roles
    from app import push, voice
    names = [t["name"] for t in tools.TOOLS]
    assert len(names) == len(set(names))
    for m in MODS:
        assert m in names and f"{m}_dekho" in names and m in tools.HANDLERS
        assert m in voice.VOICE_TOOL_NAMES and f"{m}_dekho" in roles.READ
    biz = {t["name"] for t in inbox.BIZ_TOOLS}
    assert {"biz_rent_status", "biz_rent_repair"} <= biz and {"biz_rent_status", "biz_rent_repair"} <= roles.CUSTOMER_TOOLS
    assert "biz_rent_status" not in names                      # never offered to her model
    for role in ("real_estate_agent", "property_manager", "site_supervisor", "interior_designer", "architect_assistant", "society_manager"):
        assert all(d in roles.DUTIES for d in roles.ROLES[role]["duties"])
    for pr in ("real_estate", "rentdesk", "site_supervisor", "interior", "architect", "society"):
        assert roles.PRESETS[pr]["role"] in roles.ROLES
    # cards push only while they wait for her
    assert push.render("propagent_card", {"card": {"status": "waiting"}, "say": "x"})
    assert push.render("propagent_card", {"card": {"status": "approved"}, "say": "x"}) is None
    assert push.render("interior_payment", {"stage": {"status": "waiting"}, "say": "x"})
    assert push.render("rentdesk_message", {"message": {"status": "sent"}, "say": "x"}) is None
    assert push.render("rentdesk_alert", {"kind": "repair", "request": {"urgent": False}, "say": "x"}) is None
    assert push.render("rentdesk_alert", {"kind": "renewal", "say": "x"})
    assert push.render("society_complaint", {"complaint": {"urgent": True}, "say": "x"})
    assert push.render("society_complaint", {"complaint": {"urgent": False}, "say": "x"}) is None
    assert push.render("sitesup_day", {"say": "x"})
    for k in ("propagent_card", "rentdesk_approval", "sitesup_indent", "interior_order", "archassist_invoice", "society_card"):
        assert k in push.PUSH_KINDS


def test_routes_and_worker_ticks(env):
    from fastapi.testclient import TestClient
    from app.main import app
    paths = set(app.openapi()["paths"])
    for m in MODS:
        assert any(p.startswith(f"/api/{m}") for p in paths), m
    assert "/api/rentdesk/tenancies/from_deal" in paths
    c = TestClient(app)
    assert c.get("/api/rentdesk/units").status_code == 200                # (test env has no API key)
    r = c.get("/api/propagent/page/" + "x" * 24)                           # public page checks its own token
    assert r.status_code == 404 and r.headers["content-security-policy"].startswith("default-src 'none'")
    assert c.get("/api/propagent/page/" + "x" * 24 + "/photo/0").status_code == 404
    import importlib
    for m in MODS:
        importlib.import_module(f"app.{m}.service").tick()


def test_propagent_rent_deal_becomes_draft_tenancy(env, monkeypatch):
    from app.propagent import service as P
    from app.rentdesk import service as R
    monkeypatch.setattr(P, "_publish", lambda *a, **k: None)
    monkeypatch.setattr(R, "_publish", lambda *a, **k: None)
    monkeypatch.setattr(P, "_model_json", lambda system, prompt: {})
    P.save_listing(T, purpose="rent", kind="flat", title="2 BHK Gorakshan Road", rent="18k", deposit="60k", carpet_sqft=750,
                   city="Akola", pin="444001", owner_name="Patil", mandate={"consent": True})
    P.save_lead(T, name="रमेश पाटील", phone="9822011111", role="tenant", words="2 BHK kiraye par")
    P.deal_new(T, "L-0001", "B-0001")
    with pytest.raises(R.RentError):
        R.from_propagent_deal(T, "D-0001", "2026-11-01")                  # not agreed yet
    out = P.deal_status(T, "D-0001", "agreement")
    assert "rentdesk action=from_deal" in out["say"]
    t = R.from_propagent_deal(T, "D-0001", "2026-11-01")["tenancy"]
    assert t["rent"] == 18000 and t["deposit"] == 60000 and t["status"] == "draft" and t["tenant_name"] == "रमेश पाटील"
    with pytest.raises(R.RentError):
        R.from_propagent_deal(T, "D-0001", "2026-11-01")                  # never copied twice
    from app.agent.rentdesk_tools import RENTDESK_HANDLERS
    from app.agent.tools import ToolError
    from tests.test_life import conv_ctx
    ctx = conv_ctx()
    ctx.actor = "staff:abc"
    with pytest.raises(ToolError):
        import asyncio
        asyncio.run(RENTDESK_HANDLERS["rentdesk"](ctx, action="from_deal", deal="D-0001"))


def test_indicpdf_latin_unchanged_devanagari_readable(env, monkeypatch):
    from app import indicpdf
    from reportlab.lib.pagesizes import A5
    def draw(text):
        bio = io.BytesIO()
        c = indicpdf.Canvas(bio, pagesize=A5)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, 500, "RENT RECEIPT")
        c.setFont("Helvetica", 10)
        c.drawString(30, 480, text)
        c.drawRightString(380, 460, "Rs 5,000.00")
        c.rect(30, 100, 60, 40)
        c.showPage()
        c.save()
        return bio.getvalue()
    latin = draw("Received from Ramesh Patil")
    assert latin.startswith(b"%PDF") and "Ramesh Patil" in _pdf_text(latin)
    # Chromium missing -> ReportLab with the bundled Devanagari font: the name is there, not '?'
    monkeypatch.setattr(indicpdf, "_chromium", lambda html: None)
    fb = draw("Received from रमेश पाटील")
    t = _pdf_text(fb)
    assert fb.startswith(b"%PDF") and "RENT RECEIPT" in t and "?" not in t.replace("Rs", "")
    assert indicpdf.keep("रमेश ₹ 5") == "रमेश Rs  5" and indicpdf.keep("€") == "?"
    # Chromium path builds a page with the text positioned
    seen = {}
    monkeypatch.setattr(indicpdf, "_chromium", lambda html: seen.setdefault("h", html) and b"%PDF-fake")
    assert draw("रमेश") == b"%PDF-fake" and "रमेश" in seen["h"] and "@page{size:" in seen["h"]
    # block documents (interior / propagent)
    assert indicpdf.blocks_pdf("Quote", [("p", "Latin only")]) is None
    h = indicpdf.blocks_html("Quote", [("h1", "कोटेशन"), ("table", [["Item", "Rs"], ["अलमारी", "5,000"]])], "DRAFT")
    assert "<table>" in h and "अलमारी" in h and "DRAFT" in h


def test_module_pdfs_keep_hindi_names(env, monkeypatch):
    from app import indicpdf
    got = []
    monkeypatch.setattr(indicpdf, "_chromium", lambda html: got.append(html) or None)     # force the ReportLab fallback
    from app.propagent import service as P
    pdf = P._pdf("Token receipt", "Received from: सुरेश जोशी\nAmount: Rs 1,00,000")
    assert pdf and got and "सुरेश" in got[-1]
    from app.interior import service as I
    pdf = I._pdf("Quotation Q-0001", [("h1", "Quotation"), ("p", "Client: अनिता देशमुख"), ("table", [["Item", "Amount"], ["Wardrobe", "50,000"]])])
    assert pdf.startswith(b"%PDF") and "अनिता" in got[-1]
    from app.sitesup import service as SS
    assert "रमेश" in SS._pdf_safe("*रमेश*")
