"""v0.999.117 ULTIMATE PC PLAN P7 - portals for every country: a site that refuses cloud computers is said at once on
Hoola PC and the job pointed at her PC (starter list + what Hoola PC learns); a national login is always hers."""
from __future__ import annotations

import pytest

from app.pc import portals as P
from tests.test_v0999_93_ultimate_p1 import _do, _Fake


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("PC_PORTALS_FILE", str(tmp_path / "portals.json"))
    return P


def test_starter_list_and_learning(store):
    assert store.blocked_for_cloud("https://parivahan.gov.in/parivahan/") and store.blocked_for_cloud("www.bizfile.gov.sg")
    assert not store.blocked_for_cloud("https://www.gst.gov.in")
    assert store.looks_blocked("", "ERROR: The request could not be satisfied 403 ERROR") and store.looks_blocked("no_page", "")
    assert not store.looks_blocked("", "Welcome to the portal")
    store.learn("https://services.example.gov.uk/x", "blocked page")
    assert store.blocked_for_cloud("https://www.example.gov.uk/other")          # learned by its registrable part


def test_national_logins_of_many_countries():
    for url, name in (("https://secure.login.gov/", "Login.gov"), ("https://signin.account.gov.uk/", "GOV.UK One Login"),
                      ("https://id.uaepass.ae/x", "UAE Pass"), ("https://id.singpass.gov.sg/", "Singpass"),
                      ("https://accounts.digilocker.gov.in/", "DigiLocker"), ("https://www.digid.nl/", "DigiD"),
                      ("https://app.franceconnect.gouv.fr/", "FranceConnect"), ("https://myid.gov.au/", "myID")):
        assert P.national_login(url)[0] == name, url
        assert "this sign-in is HERS" in P.login_note(url)
    assert P.national_login("https://www.amazon.com") is None and P.login_note("https://bbc.co.uk") == ""


def test_hoola_pc_refuses_a_cloud_blocked_site_at_once_and_learns_new_ones(store):
    from app.pc import operator as O
    f = _Fake({"opened": "x"})
    out = _do("open_url", {"url": "https://parivahan.gov.in"}, f, kind=O.HOOLA_PC_KIND)
    assert out.startswith("NOT OPENED on Hoola PC") and "pc_do" in out and f.calls == []
    f = _Fake({"opened": "https://www.newportal.go.ke/", "title": "ERROR: The request could not be satisfied", "problem": "blocked",
               "loaded": False})
    out = _do("open_url", {"url": "https://www.newportal.go.ke/"}, f, kind=O.HOOLA_PC_KIND)
    assert "refusing a CLOUD computer" in out
    assert store.blocked_for_cloud("https://newportal.go.ke/again")
    # on her own PC nothing is refused (she is on a home / office connection)
    out = _do("open_url", {"url": "https://parivahan.gov.in"}, _Fake({"opened": "x", "in": "Chrome"}), kind="")
    assert not out.startswith("NOT OPENED")


def test_a_national_login_after_a_click_is_handed_to_her():
    out = _do("page_click", {"ref": 2}, _Fake({"clicked": True, "title": "Sign in", "url": "https://secure.login.gov/"}))
    assert "NATIONAL LOGIN (Login.gov, US)" in out and "Take control" in out
