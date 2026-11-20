"""v0.999.57 HOOLA CRED, PREMIUM + NATIVE (owner: "MAKE HOOLA CRED MORE PREMIUM ... KEEP SIDE BAR ... NATIVE", design
claude.ai/artifact/H71Uojvg4ha8RzvtSTqevz, "GO BUILD ALL"): Hoola Cred is a view inside the console (sidebar kept), the
page knows when Hoola last used each login, and the phone opens its own native screen whose crypto is Android's own."""
import base64
import os
import re
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"


def test_old_address_lands_inside_the_console(env):
    from app.main import app
    r = TestClient(app).get("/console/cred", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/console/?v=cred"
    assert not (CON / "cred.html").exists()


def test_console_mounts_the_view_and_keeps_the_sidebar():
    html = (CON / "v2.html").read_text()
    assert 'id="v-cred"' in html and 'id="credview"' in html
    assert re.search(r'cred\.js\?v=', html) and re.search(r'cred\.css\?v=', html) and "JetBrains+Mono" in html
    js = (CON / "v2.js").read_text()
    assert "CRED = HoolaCred(" in js and "CRED?.open($('#credview'))" in js
    assert "location.assign('/console/cred')" not in js                     # no longer a separate page
    assert "'webdev', 'cred']" not in js
    cred = (CON / "cred.js").read_text()
    assert "window.HoolaCred = function" in cred and "/api/cred/hoola-uses" in cred
    for page in ("drawCreate", "drawUnlock", "drawAll", "drawEdit", "drawHoola", "drawCodes", "drawSafety", "drawGen", "drawImport", "drawSettings"):
        assert f"function {page}" in cred
    assert "'say'" in cred and "'pin'" in cred and "pref('lock'" in cred and "pref('clip'" in cred
    assert 'data-v=' not in cred                                             # the console's global [data-v] click handler
    css = (CON / "cred.css").read_text()
    assert ".hcv{" in css and not re.search(r"\.hc[\s{,]", css)              # .hc is the console's own (italic) class


def test_hoola_uses_lists_sites_and_last_use(env):
    from app import cred
    from app.pc import vault as pcv
    from app.main import app
    k = lambda n: base64.b64encode(os.urandom(n)).decode()  # noqa: E731
    cred.create_vault("default", k(16), 100_000, {"iv": k(12), "ct": k(48)})
    iid = cred.add_item("default", k(12), k(64))["id"]
    cred.set_hoola("default", iid, True, "GST portal", "me", "pw-123456", urls=["gst.gov.in"], totp="GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ")
    c = TestClient(app)
    u = c.get("/api/cred/hoola-uses").json()["uses"][iid]
    assert u["sites"] == ["gst.gov.in"] and u["two_step"] is True and u["used"] == ""
    pcv.open_("default", pcv.find("default", "gst.gov.in")["id"])               # Hoola types it once
    assert c.get("/api/cred/hoola-uses").json()["uses"][iid]["used"]
    assert "pw-123456" not in c.get("/api/cred/hoola-uses").text


def test_phone_screen_is_native_with_android_crypto():
    kt = (ROOT / "tool" / "android" / "kotlin" / "CredCrypto.kt").read_text()
    for need in ("PBKDF2WithHmacSHA256", "AES/GCM/NoPadding", "GCMParameterSpec(128", "HmacSHA1", "fun unwrap", "fun create", "fun openMany"):
        assert need in kt
    main = (ROOT / "tool" / "android" / "kotlin" / "MainActivity.kt").read_text()
    assert '"credUnwrap", "credCreate"' in main and "Thread {" in main
    dart = (ROOT / "lib" / "ui" / "cred" / "hoola_cred.dart").read_text()
    for need in ("class HoolaCredScreen", "credUnwrap", "credOpenMany", "/api/cred/hoola-uses", "didChangeAppLifecycleState", "Clipboard.setData"):
        assert need in dart
    assert "Color(0x" not in dart                                            # the design ratchet
    tools = (ROOT / "lib" / "ui" / "shell" / "hoola_tools.dart").read_text()
    assert "HoolaCredScreen(app: app)" in tools


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION >= "0.999.62"
