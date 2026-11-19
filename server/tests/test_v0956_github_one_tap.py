"""v0.956 GITHUB ONE TAP (owner: "GITHUB STILL NOT REDIRECTING TO APP"): three reasons it never came back -
(1) the phone opened github.com with a plain link, so the GitHub app could swallow it, (2) an App already installed
never sends the signed state, so Hoola could not tell whose install it was, (3) a page script jumping to santosh:// on
a timer is blocked by Chrome. Now: the browser is opened, Connect signs her in on GitHub and binds only an install
GitHub lists as hers (no install = straight to the install page and back), and Android goes back with an intent link
inside the same redirect."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANDROID = {"user-agent": "Mozilla/5.0 (Linux; Android 14) Chrome/140 Mobile"}


def _oauth(monkeypatch):
    from app.devsahayak import ghapp
    from app.config import get_settings
    st = get_settings()
    for k, v in (("github_app_id", "123"), ("github_app_slug", "hoola-code"), ("github_app_client_id", "Iv1.abc"),
                 ("github_app_client_secret", "s3cret"), ("public_base_url", "https://hoola.example")):
        monkeypatch.setattr(st, k, v, raising=False)
    monkeypatch.setattr(ghapp, "_private_key", lambda: "-----BEGIN KEY-----")
    return ghapp


def test_connect_starts_with_github_sign_in(env, monkeypatch):
    ghapp = _oauth(monkeypatch)
    from app.devsahayak import service as S
    out = S.github_connect_url("t1")
    assert out["mode"] == "signin" and out["url"].startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=Iv1.abc" in out["url"] and "redirect_uri=https%3A%2F%2Fhoola.example%2Fapi%2Fdevsahayak%2Fgithub%2Finstalled" in out["url"]
    assert ghapp.read_state(out["url"].split("state=")[1].split("&")[0]) == "t1"


def test_only_her_own_install_is_bound(env, monkeypatch):
    ghapp = _oauth(monkeypatch)
    from app.devsahayak import service as S
    state = ghapp.make_state("t1")
    monkeypatch.setattr(ghapp, "user_token", lambda code: "utok")
    monkeypatch.setattr(ghapp, "user_login", lambda tok: "meghana")
    monkeypatch.setattr(ghapp, "user_installations", lambda tok: [
        {"id": 55, "app_id": 123, "account": {"login": "newtika"}},
        {"id": 77, "app_id": 123, "account": {"login": "meghana"}}])
    # someone else's installation id in the URL is ignored: only an install on HER list is bound
    out = S.github_installed(999, state, "install", "code1")
    assert out == {"ok": True, "account": "meghana"}
    assert S.settings("t1").get("app_connected") is True
    # the one GitHub just sent wins when it is on her list
    assert S.github_installed(55, state, "install", "code2")["account"] == "newtika"


def test_no_install_yet_goes_to_install_page_and_setup_url_goes_through_sign_in(env, monkeypatch):
    ghapp = _oauth(monkeypatch)
    from app.devsahayak import service as S
    state = ghapp.make_state("t1")
    monkeypatch.setattr(ghapp, "user_token", lambda code: "utok")
    monkeypatch.setattr(ghapp, "user_login", lambda tok: "meghana")
    monkeypatch.setattr(ghapp, "user_installations", lambda tok: [])
    out = S.github_installed(0, state, "", "code1")
    assert out["redirect"].startswith("https://github.com/apps/hoola-code/installations/new?state=")
    back = S.github_installed(42, state, "install", "")        # the Setup URL: prove it with the sign-in first
    assert back["redirect"].startswith("https://github.com/login/oauth/authorize?")


def test_android_goes_straight_back_with_an_intent_link(env, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.devsahayak import service as S
    monkeypatch.setattr(S, "github_installed", lambda i, st, a="", c="": {"ok": True, "account": "meghana"})
    c = TestClient(app)
    r = c.get("/api/devsahayak/github/installed?state=x&code=y", headers=ANDROID, follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("intent://github?ok=1#Intent;scheme=santosh;package=com.newtika.santosh;")
    assert "S.browser_fallback_url=" in loc and "github%2Fdone" in loc
    d = c.get("/api/devsahayak/github/done?ok=1&acc=meghana", headers=ANDROID)
    assert d.status_code == 200 and "GitHub connected" in d.text and "intent://github?ok=1" in d.text
    monkeypatch.setattr(S, "github_installed", lambda i, st, a="", c="": {"ok": False, "redirect": "https://github.com/x"})
    r2 = c.get("/api/devsahayak/github/installed?state=x", headers=ANDROID, follow_redirects=False)
    assert r2.status_code == 302 and r2.headers["location"] == "https://github.com/x"


def test_phone_opens_the_browser_not_the_github_app():
    dart = (ROOT / "lib/ui/code/code_more.dart").read_text()
    assert "Native.openExternal(url: url, package: 'browser')" in dart
    kt = (ROOT / "tool/android/kotlin/MainActivity.kt").read_text()
    assert 'if (pkg == "browser")' in kt and "private fun browserPackage()" in kt and '!it.contains("github")' in kt


def test_vps_ops_writes_the_client_id_and_secret():
    y = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    assert "secrets.HOOLA_GITHUB_APP_CLIENT_ID" in y and "secrets.HOOLA_GITHUB_APP_CLIENT_SECRET" in y
    assert "setv GITHUB_APP_CLIENT_SECRET" in y and "ghapp.oauth_ready()" in y


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.10"' in main
    assert "version: 0.999.10+1008" in (ROOT / "pubspec.yaml").read_text()
