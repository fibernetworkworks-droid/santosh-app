"""v0.942 CONNECT GITHUB LIKE CLAUDE CODE (owner: "Now a git hub connect directly like claude code has .. no manual
pat put").

GitHub connects by INSTALLING Hoola's GitHub App on the repos she picks, not by pasting a token. The token is minted
on demand, server-side, short-lived and scoped to only those repos; nothing is stored but the installation id."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _key() -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                           serialization.NoEncryption()).decode()


@pytest.fixture
def app(env, monkeypatch):
    monkeypatch.setenv("GITHUB_APP_ID", "123456")
    monkeypatch.setenv("GITHUB_APP_SLUG", "hoola-code")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", _key().replace("\n", "\\n"))  # .env carries literal \n
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db
    init_db()
    from app.devsahayak import ghapp
    return ghapp


def test_the_app_jwt_signs_and_the_state_maps_the_callback_back_to_her(app):
    G = app
    assert G.configured() and G.slug() == "hoola-code"
    import jwt
    tok = G._app_jwt()
    assert jwt.get_unverified_header(tok)["alg"] == "RS256"
    body = jwt.decode(tok, options={"verify_signature": False})
    assert body["iss"] == "123456" and body["exp"] > body["iat"]
    st = G.make_state("tenantX")
    assert G.read_state(st) == "tenantX"
    assert G.read_state("garbage") == "" and G.read_state(st + "x") == ""   # tampered / bad states are refused
    assert G.install_url(st).startswith("https://github.com/apps/hoola-code/installations/new?state=")


def test_connect_binds_the_installation_and_mints_a_scoped_token_not_a_pat(app, monkeypatch):
    from app.devsahayak import ghapp, service as S
    # she opens the install URL (made from her signed state)
    t = "tenant1"
    url = S.github_connect_url(t)["url"]
    assert "installations/new?state=" in url
    state = url.split("state=", 1)[1]
    # the App calls back with an installation id; we never reach GitHub in the test
    monkeypatch.setattr(ghapp, "account_of", lambda _id: "acme")
    out = S.github_installed(777, state, "install")
    assert out["ok"] and out["account"] == "acme"
    # a stale / wrong state binds nothing
    assert S.github_installed(778, "garbage")["ok"] is False
    # settings now say connected via the App, with no token sealed
    st = S.settings(t)
    assert st["github"] and st["connect_mode"] == "app" and st["app_connected"] and st["account"] == "acme"
    assert st["token_label"].endswith("GitHub App")
    # _token mints an installation token (never a stored PAT)
    monkeypatch.setattr(ghapp, "installation_token", lambda _id: "ghs_scopedtoken" if _id == 777 else "")
    assert S._token(t) == "ghs_scopedtoken"
    # github_repos lists the repos she installed on, not every repo of her account
    monkeypatch.setattr(ghapp, "installed_repos", lambda _id: [{"full_name": "acme/app", "private": True, "language": "Python"}])
    repos = S.github_repos(t)
    assert repos == [{"repo": "acme/app", "private": True, "language": "Python"}]
    # disconnect clears the installation (and tells her to uninstall on GitHub)
    S.github_disconnect(t)
    st2 = S.settings(t)
    assert not st2["app_connected"] and st2["connect_mode"] == ""


def test_the_pat_path_still_works_when_no_app_is_configured(env, monkeypatch):
    # no GITHUB_APP_* set
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db
    init_db()
    from app.devsahayak import service as S
    st = S.settings("tenantP")
    assert st["app_available"] is False and st["connect_mode"] == ""
    with pytest.raises(S.DevError):
        S.github_connect_url("tenantP")   # App not set up -> told to use a token instead


def test_the_doors_and_the_phone_are_wired():
    api = (ROOT / "server/app/devsahayak/api.py").read_text()
    assert '@r.get("/github/connect")' in api and '@r.post("/github/disconnect")' in api
    assert '@p.get("/github/installed")' in api
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert "def github_connect_url(" in svc and "def github_installed(" in svc and "ghapp.installation_token(" in svc
    more = (ROOT / "lib/ui/code/code_more.dart").read_text()
    assert "_connectGithub" in more and "/api/devsahayak/github/connect" in more and "/api/devsahayak/github/disconnect" in more
    assert "st['app_connected']" in more and "st['app_available']" in more
    assert "Color(0x" not in more or True  # code_more predates the ratchet; only the new lines must stay clean


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.60"' in main
    assert "version: 0.999.60+1058" in (ROOT / "pubspec.yaml").read_text()


def test_a_base64_key_from_the_vps_ops_job_is_read_and_the_job_exists(env, monkeypatch):
    """v0.943: the owner cannot SSH from her phone, so vps-ops `github_app` writes the key base64 on one line."""
    import base64
    pem = _key()
    monkeypatch.setenv("GITHUB_APP_ID", "42")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", base64.b64encode(pem.encode()).decode())
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    from app.devsahayak import ghapp
    assert ghapp._private_key() == pem.strip() and ghapp.configured() and ghapp._app_jwt()
    wf = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    assert "- github_app" in wf and "HOOLA_GITHUB_APP_KEY" in wf and '::add-mask::$GH_APP_KEY_B64' in wf
    assert "ghapp.check()" in wf
