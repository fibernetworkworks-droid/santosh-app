"""v0.341 TERMS OF SERVICE (owner: "Terms of Service --- HOOLA"): a public /terms page beside /privacy, saying only what
Hoola really does (her tap before sending / publishing / paid work, never moves money, price card first, failed items not
charged, AI results are not professional advice) plus the IT Act grievance officer and Indian law."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_terms_page(env):
    from app import main
    with TestClient(main.app) as c:
        r = c.get("/terms")
        assert r.status_code == 200 and "text/html" in r.headers["content-type"]
        t = r.text
        for k in ("Hoola terms of service", "Newtika Private Limited", 'href="/privacy"', "Hoola never moves money",
                  "not professional advice", "Grievance Officer", "within 24 hours", "15 days", "laws of India",
                  "price card first", "Pictures or clips that fail are not charged", "at least 18 years old"):
            assert k in t, k
        assert c.get("/privacy").status_code == 200
