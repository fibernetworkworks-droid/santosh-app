from app.leads import import_leads, normalize_phone
from app.whatsapp.templates import check_template, render_body

from .conftest import SAMPLE


def test_phone_normalisation():
    assert normalize_phone("9876543210") == "919876543210"
    assert normalize_phone("+91 98765 43210") == "919876543210"
    assert normalize_phone("098765-43210") == "919876543210"
    assert normalize_phone("919876543210") == "919876543210"
    assert normalize_phone(9876543210.0) == "919876543210"
    assert normalize_phone("+44 7911 123456") == "447911123456"
    assert normalize_phone("12345") is None
    assert normalize_phone("5876543210") is None          # Indian mobiles start 6-9
    assert normalize_phone("9.87654E+09") is None          # Excel lost the digits
    assert normalize_phone("") is None and normalize_phone(None) is None


def test_import_sample_csv(env):
    res = import_leads(SAMPLE.name, SAMPLE.read_bytes(), "default")
    assert res.total_rows == 13
    assert res.valid == 11
    assert res.duplicates == 1
    assert res.invalid == 1
    assert res.phone_column == "Mobile" and res.name_column == "Name"
    assert res.has_consent_column is False


def test_import_xlsx_with_consent(env, tmp_path):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append(["Customer Name", "WhatsApp Number", "Opt In"])
    ws.append(["Ravi", 9811111111, "Yes"])
    ws.append(["Seema", "9822222222", "no"])
    p = tmp_path / "l.xlsx"; wb.save(p)
    res = import_leads("l.xlsx", p.read_bytes(), "default")
    assert res.valid == 2 and res.has_consent_column and res.opted_in == 1


def test_template_rules():
    good = check_template("diwali_offer_2026", "hi", "MARKETING",
                          "Namaste {{1}}, Diwali par sabhi products par 30% chhoot. Offer 2 November tak.",
                          ["Rahul"], footer="STOP likhkar band karein")
    assert good["ok"], good
    assert good["warnings"] == []
    bad = check_template("Diwali Offer", "xx", "PROMO", "{{1}} {{3}}", ["a"])
    assert not bad["ok"]
    joined = " ".join(bad["errors"])
    for frag in ("lowercase", "Language", "MARKETING", "order", "start or end", "example"):
        assert frag in joined, frag
    assert render_body("Hi {{1}}, {{2}} off", ["Rahul", "30%"]) == "Hi Rahul, 30% off"
