"""v0.953 GITHUB BACK TO APP (owner, after installing the Hoola Code GitHub App: "But why not redirecting to hoola app"
... "need one tap GitHub access connection"): the page GitHub's Setup URL lands on now sends the phone straight back
into the Hoola app (santosh://github?ok=1, the shared sign-in done page), and an install made on GitHub itself says
to tap Connect GitHub in the app instead of 'link expired'."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_installed_page_goes_back_into_the_app(env, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.devsahayak import service as S
    monkeypatch.setattr(S, "github_installed", lambda i, st, a="", c="": {"ok": True, "account": "meghana"})
    r = TestClient(app).get("/api/devsahayak/github/installed?installation_id=7&state=x&setup_action=install")
    assert r.status_code == 200 and "GitHub connected" in r.text
    assert "santosh://github?ok=1" in r.text and "location.href" in r.text


def test_failed_page_says_why_and_still_offers_the_way_back(env, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    r = TestClient(app).get("/api/devsahayak/github/installed?installation_id=7&setup_action=install")
    assert "Could not connect" in r.text and "tap Connect GitHub" in r.text and "santosh://github?ok=0" in r.text


def test_phone_handles_the_github_link():
    man = (ROOT / "tool/AndroidManifest.xml").read_text()
    assert 'android:scheme="santosh" android:host="github"' in man
    kt = (ROOT / "tool/android/kotlin/MainActivity.kt").read_text()
    assert 'data.host == "github" -> "github:ok="' in kt
    dart = (ROOT / "lib/main.dart").read_text()
    # the github: link must be handled before the fallback that treats any other text as a session token
    assert dart.index("t.startsWith('github:')") < dart.index("await widget.app.applySession(t);")


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.994.0"' in main
    assert "version: 0.994.0+993" in (ROOT / "pubspec.yaml").read_text()
