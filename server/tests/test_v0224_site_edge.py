"""v0.224 Website Phase 2: hosted sites are served by nginx from an 'enabled' folder (a Hoola restart no longer takes them
down), visits come from nginx's own log, an outside checker (GitHub Actions) reports what it sees, the website files are
backed up off the server every day, and the Python fallback answers 304 to repeat visits."""
import http.server
import io
import json
import os
import shutil
import socket
import subprocess
import tarfile
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_v122_hosting import _ready_site, host_env  # noqa: F401  (fixture)

T = "default"
HOST = "sharma-sweets.hoolasites.in"
KEY = "uptime-key-0123456789abcdef"


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


def _launch(c, g):
    card = c.post(f"/api/sites/{g['id']}/launch-request", json={}).json()
    assert c.post(f"/api/sites/{g['id']}/launch", json={"hash": card["hash"]}).status_code == 200


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ---------------------------------------------------------------- 1. the enabled folder follows every launch / take-down
def test_enabled_folder_follows_launch_and_takedown(host_env):
    from app.main import app
    from app.site import edge
    from app.site import hosting as H
    c = TestClient(app)
    g, _ = _ready_site()
    _launch(c, g)
    link = edge.enabled_root() / HOST
    assert link.is_symlink() and (link / "index.html").exists()
    assert 'content="Hoola"' in (link / "index.html").read_text()
    # an apex address is never in the folder (nginx sends it to www); junk names are refused
    hosts = {HOST: {"site": g["id"], "role": "main", "main": HOST}, "her.in": {"site": g["id"], "role": "apex", "main": HOST},
             "../etc": {"site": "x", "role": "main", "main": "../etc"}}
    edge.sync(hosts)
    assert sorted(p.name for p in edge.enabled_root().iterdir()) == [HOST]
    H.take_down(T, g["id"])
    assert not (edge.enabled_root() / HOST).exists()


# ---------------------------------------------------------------- 2. visits from nginx's log
def test_visits_come_from_nginx_log_without_bots(host_env):
    from app.main import app
    from app.site import care, edge
    c = TestClient(app)
    g, _ = _ready_site()
    _launch(c, g)
    lines = [
        (HOST, 200, "GET", "/", "text/html", "Mozilla/5.0 (Android 14)"),
        (HOST, 200, "GET", "/contact/", "text/html", "Mozilla/5.0 (iPhone)"),
        (HOST, 200, "GET", "/assets/site.css", "text/css", "Mozilla/5.0"),          # not a page
        (HOST, 200, "GET", "/", "text/html", "HoolaUptime/1.0 (outside)"),         # the checker
        (HOST, 200, "GET", "/", "text/html", "Googlebot/2.1"),
        (HOST, 404, "GET", "/old/", "text/html", "Mozilla/5.0"),                   # missing page
        (HOST, 200, "POST", "/", "text/html", "Mozilla/5.0"),
        ("unknown.example", 200, "GET", "/", "text/html", "Mozilla/5.0"),
    ]
    p = edge.access_log()
    p.write_text("".join("\t".join(map(str, x)) + "\n" for x in lines) + "partial\tline-no-newline")
    assert edge.ingest_log() == 3
    assert edge.ingest_log() == 0                              # read once
    with p.open("a") as f:
        f.write(f"\n{HOST}\t200\tGET\t/\ttext/html\tMozilla/5.0\n")
    assert edge.ingest_log() == 1
    p.write_text(f"{HOST}\t200\tGET\t/\ttext/html\tMozilla/5.0\n")   # rotated (smaller): starts again
    assert edge.ingest_log() == 1
    care.flush()
    rep = care.report(T, g["id"])
    assert rep["views"] == 4 and rep["missing_hits"] == 1


# ---------------------------------------------------------------- 3. the outside checker
def test_outside_checker_endpoints_and_cards(host_env):
    from app.config import get_settings
    from app.main import app
    c = TestClient(app)
    g, _ = _ready_site()
    _launch(c, g)
    assert c.get("/api/sites-uptime").status_code == 404           # no key set: the endpoint does not exist
    host_env["monkeypatch"].setenv("SITES_UPTIME_KEY", KEY)
    get_settings.cache_clear()
    assert c.get("/api/sites-uptime", headers={"x-uptime-key": "wrong"}).status_code == 404
    lst = c.get("/api/sites-uptime", headers={"x-uptime-key": KEY}).json()
    assert lst == {"hosts": [HOST]}
    bad = {"results": [{"host": HOST, "ok": False, "status": "000", "error": "no answer (DNS / TLS / timeout)"},
                       {"host": "not-ours.example", "ok": False}]}
    assert c.post("/api/sites-uptime", headers={"x-uptime-key": KEY}, json=bad).json()["recorded"] == 1
    assert not [e for e in _events("site_down") if not e.get("ok")]           # one miss = no alarm yet
    c.post("/api/sites-uptime", headers={"x-uptime-key": KEY}, json=bad)
    down = [e for e in _events("site_down") if not e.get("ok")]
    assert len(down) == 1 and "bahar se" in down[0]["say"] and down[0]["push"]
    c.post("/api/sites-uptime", headers={"x-uptime-key": KEY}, json=bad)      # told once
    assert len([e for e in _events("site_down") if not e.get("ok")]) == 1
    c.post("/api/sites-uptime", headers={"x-uptime-key": KEY}, json={"results": [{"host": HOST, "ok": True}]})
    assert _events("site_down")[-1].get("ok") is True
    assert c.post("/api/sites-uptime", headers={"x-uptime-key": KEY}, json={"results": "x"}).status_code == 400


# ---------------------------------------------------------------- 4. python fallback: 304 for repeat visits
def test_python_fallback_answers_304(host_env):
    from app.main import app
    c = TestClient(app)
    g, _ = _ready_site()
    _launch(c, g)
    r = c.get("/", headers={"host": HOST})
    etag = r.headers["etag"]
    r2 = c.get("/", headers={"host": HOST, "if-none-match": etag})
    assert r2.status_code == 304 and r2.content == b""
    assert c.get("/assets/site.css", headers={"host": HOST, "if-none-match": etag}).status_code == 200


# ---------------------------------------------------------------- 5. daily backup off the server
class FakeS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.auth = []

    def handler(self, req: httpx.Request) -> httpx.Response:
        u = urlparse(str(req.url))
        self.auth.append(req.headers.get("authorization", ""))
        assert req.headers.get("x-amz-content-sha256") == "UNSIGNED-PAYLOAD"
        path = u.path.split("/", 2)
        assert path[1] == "hoola-bk"
        key = path[2] if len(path) > 2 else ""
        if req.method == "PUT":
            self.objects[key] = req.read()
            return httpx.Response(200)
        if req.method == "DELETE":
            self.objects.pop(key, None)
            return httpx.Response(204)
        if req.method == "GET" and not key:
            pre = parse_qs(u.query).get("prefix", [""])[0]
            ks = "".join(f"<Contents><Key>{k}</Key></Contents>" for k in sorted(self.objects) if k.startswith(pre))
            return httpx.Response(200, text=f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">{ks}'
                                             "<IsTruncated>false</IsTruncated></ListBucketResult>")
        if req.method == "GET":
            return httpx.Response(200, content=self.objects[key])
        return httpx.Response(400)


def test_daily_backup_prune_and_safe_restore(host_env, tmp_path):
    from datetime import datetime, timedelta, timezone
    from app.config import get_settings
    from app.main import app
    from app.site import backup
    c = TestClient(app)
    g, _ = _ready_site()
    _launch(c, g)
    assert backup.daily() is None                                  # off until the bucket is set
    mp = host_env["monkeypatch"]
    for k, v in {"SITES_BACKUP_BUCKET": "hoola-bk", "SITES_BACKUP_ENDPOINT": "https://acct.r2.example",
                 "SITES_BACKUP_KEY_ID": "AKIDEXAMPLE", "SITES_BACKUP_SECRET": "secret-0123456789", "SITES_BACKUP_KEEP_DAYS": "7"}.items():
        mp.setenv(k, v)
    get_settings.cache_clear()
    s3 = FakeS3()
    backup.set_transport(httpx.MockTransport(s3.handler))
    try:
        s3.objects["hoola/sites/2020-01-01.tar.gz"] = b"old"
        ist = timezone(timedelta(hours=5, minutes=30))
        assert backup.daily(datetime(2026, 10, 29, 2, tzinfo=ist)) is None          # before 03:00
        out = backup.daily(datetime(2026, 10, 29, 4, tzinfo=ist))
        assert out["ok"] and out["pruned"] == 1 and out["files"] > 3
        assert "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/" in s3.auth[0]
        assert "secret-0123456789" not in "".join(s3.auth)
        assert backup.daily(datetime(2026, 10, 29, 9, tzinfo=ist)) is None          # once a day
        day = out["key"].rsplit("/", 1)[1][:10]
        names = tarfile.open(fileobj=io.BytesIO(s3.objects[out["key"]])).getnames()
        assert f"hosted/{HOST}/index.html" in names and any("/src/sections/" in n for n in names)
        # a hostile archive member never lands outside the restore folder
        evil = io.BytesIO()
        with tarfile.open(fileobj=evil, mode="w:gz") as t:
            for name, data in (("../escape.txt", b"x"), ("hosted/ok.txt", b"y")):
                ti = tarfile.TarInfo(name)
                ti.size = len(data)
                t.addfile(ti, io.BytesIO(data))
            ln = tarfile.TarInfo("hosted/bad-link")
            ln.type, ln.linkname = tarfile.SYMTYPE, "/etc"
            t.addfile(ln)
        s3.objects["hoola/sites/2026-10-30.tar.gz"] = evil.getvalue()
        dest = tmp_path / "restore"
        backup.restore("2026-10-30", dest)
        assert (dest / "hosted" / "ok.txt").exists() and not (tmp_path / "escape.txt").exists()
        assert not (dest / "hosted" / "bad-link").exists()
        backup.restore(day, tmp_path / "real")
        assert (tmp_path / "real" / "hosted" / HOST / "index.html").exists()
        assert backup.status()["last"]["day"] == day
    finally:
        backup.set_transport(None)


def test_signature_matches_the_aws_reference():
    """AWS SigV4 (GET, UNSIGNED-PAYLOAD, path-style) pinned after cross-checking with botocore."""
    from datetime import datetime, timezone
    from app.site import backup
    c = {"bucket": "examplebucket", "endpoint": "https://s3.amazonaws.com", "region": "us-east-1",
         "key_id": "AKIAIOSFODNN7EXAMPLE", "secret": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "keep": 7}
    h = backup._sign(c, "GET", "https://s3.amazonaws.com/examplebucket/test.txt",
                     datetime(2013, 5, 24, 0, 0, 0, tzinfo=timezone.utc))
    assert h["Authorization"] == SIG_REF


# Hoola's _sign matched botocore's S3SigV4Auth (payload UNSIGNED-PAYLOAD) on GET / PUT / list / list with a continuation
# token / DELETE with an escaped key (checked 29 Oct 2026, botocore not a dependency); this pins the result at a fixed time.
SIG_REF = ("AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request, "
           "SignedHeaders=host;x-amz-content-sha256;x-amz-date, "
           "Signature=dd6bf78def945b44c04f28e30ba18d259fcb7734a611befa566c63d374a79d5c")


# ---------------------------------------------------------------- 6. real nginx with the generated server block
@pytest.mark.skipif(not shutil.which("nginx"), reason="nginx not installed")
def test_real_nginx_serves_sites_and_survives_hoola_down(tmp_path, monkeypatch):
    from app.site import edge
    hosted, enabled = tmp_path / "hosted", tmp_path / "enabled"
    site = hosted / HOST
    (site / "contact").mkdir(parents=True)
    (site / "assets").mkdir()
    (site / "index.html").write_text('<html><head><meta name="generator" content="Hoola"></head><body>home</body></html>')
    (site / "contact" / "index.html").write_text("<html>contact</html>")
    (site / "assets" / "site.css").write_text("body{color:red}" * 50)
    (site / "404.html").write_text("<html>apna 404</html>")
    (site / "_headers").write_text("secret")
    (hosted / "www.her.in").symlink_to(HOST)
    monkeypatch.setenv("SITE_HOSTED_DIR", str(hosted))
    monkeypatch.setenv("SITE_ENABLED_DIR", str(enabled))
    monkeypatch.setenv("SITE_ACCESS_LOG", str(tmp_path / "access.log"))
    edge.sync({HOST: {"site": "s", "role": "main", "main": HOST}, "www.her.in": {"site": "s", "role": "main", "main": "www.her.in"},
               "her.in": {"site": "s", "role": "apex", "main": "www.her.in"}})
    app_port, port = _free_port(), _free_port()

    class App(http.server.BaseHTTPRequestHandler):
        def _ok(self):
            body = f"HOOLA-APP {self.command} {self.path}".encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        do_GET = do_POST = _ok

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", app_port), App)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    conf = edge.nginx_conf(base_url="https://api.hoola.example", app=f"http://127.0.0.1:{app_port}", ssl=False,
                           listen_http=f"127.0.0.1:{port}")
    run = tmp_path / "run"
    run.mkdir()
    (tmp_path / "nginx.conf").write_text(
        f"user root; worker_processes 1; daemon off; pid {run}/nginx.pid; error_log {run}/error.log;\n"
        f"events {{ worker_connections 64; }}\nhttp {{\n include /etc/nginx/mime.types;\n"
        f" client_body_temp_path {run}/b; proxy_temp_path {run}/p; fastcgi_temp_path {run}/f; uwsgi_temp_path {run}/u;"
        f" scgi_temp_path {run}/s;\n{conf}\n}}\n")
    chk = subprocess.run(["nginx", "-t", "-p", str(tmp_path), "-c", str(tmp_path / "nginx.conf")], capture_output=True, text=True)
    assert chk.returncode == 0, chk.stderr
    ng = subprocess.Popen(["nginx", "-p", str(tmp_path), "-c", str(tmp_path / "nginx.conf")], stderr=subprocess.PIPE)
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                httpx.get(base, timeout=0.5)
                break
            except httpx.HTTPError:
                time.sleep(0.1)

        def get(path, host=HOST, **kw):
            return httpx.get(base + path, headers={"host": host, "user-agent": "Mozilla/5.0", **kw}, follow_redirects=False)
        r = get("/")
        assert r.status_code == 200 and "home" in r.text
        assert "script-src 'self'" in r.headers["content-security-policy"] and "https://api.hoola.example" in r.headers["content-security-policy"]
        assert r.headers["strict-transport-security"] == "max-age=31536000" and "max-age=300" in r.headers["cache-control"]
        assert get("/contact").status_code == 301 and get("/contact").headers["location"].endswith("/contact/")
        assert "contact" in get("/contact/").text
        css = get("/assets/site.css", **{"accept-encoding": "gzip"})
        assert css.status_code == 200 and "max-age=604800" in css.headers["cache-control"] and css.headers.get("content-encoding") == "gzip"
        nf = get("/nope/")
        assert nf.status_code == 404 and "apna 404" in nf.text
        assert get("/_headers").status_code == 404 and get("/../../etc/passwd").status_code in (400, 404)
        # only her form reaches Hoola; every other /api/ on a site address is 404
        assert get("/api/console/login").status_code == 404
        form = httpx.post(base + "/api/site-forms/site_1", headers={"host": HOST}, json={"x": 1})
        assert form.status_code == 200 and "HOOLA-APP POST /api/site-forms/site_1" in form.text
        # her bare domain goes to www; www (a link to the same folder) is served
        apex = get("/menu/?a=1", host="her.in")
        assert apex.status_code == 301 and apex.headers["location"] == "https://www.her.in/menu/?a=1"
        assert "home" in get("/", host="www.her.in").text
        # an address nginx doesn't know goes to Hoola (the Python fallback)
        assert get("/x", host="other.example").text == "HOOLA-APP GET /x"
        # Hoola itself down: the live sites still open
        srv.shutdown()
        srv.server_close()
        assert get("/").status_code == 200 and "home" in get("/").text
        assert get("/x", host="other.example").status_code == 502
        # visits: only what nginx served itself is logged, and it is counted the normal way
        ng.terminate()
        ng.wait(5)
        rows = [ln.split("\t") for ln in (tmp_path / "access.log").read_text().splitlines()]
        assert rows and {r[0] for r in rows} <= {HOST, "www.her.in"}
        assert ["sharma-sweets.hoolasites.in", "200", "GET", "/"] == rows[0][:4] and rows[0][4].startswith("text/html")
    finally:
        if ng.poll() is None:
            ng.terminate()
            ng.wait(5)
        try:
            srv.shutdown()
        except Exception:
            pass


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.302.0"
    assert "0.302.0+342" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
