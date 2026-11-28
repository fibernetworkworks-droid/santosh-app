"""HOOLA DIAGRAM D1 (docs/DIAGRAM_TOOL_PLAN.md): the three engines are vendored whole and UNCHANGED, Hoola's runners
call each engine's own checks, the draw.io editor setup is sha-checked, and nothing phones home."""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from app.diagram import drawio as DR
from app.diagram import runners as R
from app.diagram import vendor as V

ROOT = Path(__file__).resolve().parents[2]


def test_every_engine_is_vendored_whole_with_its_licence():
    st = V.status()
    for e in V.ENGINES:
        assert st[e]["whole"], (e, st[e]["missing"])
        assert st[e]["commit"]
    assert "Apache" in (V.ARCHIFY / "LICENSE").read_text() and "MIT" in (V.ARCHIFY / "LICENSE-MIT").read_text()
    assert "MIT" in (V.DD / "LICENSE").read_text() and "Apache" in (V.DRAWIO_AI / "LICENSE").read_text()
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text()
    for name in ("archify", "diagram-design", "next-ai-draw-io", "jgraph/drawio", "eraser-diagrams"):
        assert name in notices


def test_vendored_files_are_never_edited():
    # the fingerprint taken when the copy was made; a hand edit to a vendored file changes it
    m = json.loads((V.ROOT / "VENDOR.json").read_text())
    for e in V.ENGINES:
        assert V.tree_hash(e) == m[e]["tree_sha256"], f"{e}: a vendored file changed - make Hoola changes in app/diagram/*.py"
        assert len(V._files(e)) == m[e]["files"]


def test_types_are_read_from_each_engines_own_skill_file():
    a = V.archify_types()
    assert [t["type"] for t in a] == ["architecture", "workflow", "sequence", "dataflow", "lifecycle", "erd", "tree",
                                      "class", "timeline", "waterfall"]
    for t in a:
        assert (V.ARCHIFY / t["schema"]).is_file() and (V.ARCHIFY / t["example"]).is_file()
    d = V.dd_types()
    assert len(d) == 52
    assert all((V.DD / t["reference"]).is_file() for t in d)
    assert {"flowchart", "pyramid", "journey", "gantt", "sankey", "org-chart"} <= {t["type"] for t in d}
    assert len(V.dd_examples()) >= 200 and len(V.archify_examples()) >= 30


def test_archify_never_phones_home_and_uses_the_servers_browser(monkeypatch):
    monkeypatch.setenv("SECRET_KEY_SHOULD_NOT_LEAK", "x")
    env = R._env()
    assert env["ARCHIFY_UPDATE_CHECK_DISABLED"] == "1"
    assert "SECRET_KEY_SHOULD_NOT_LEAK" not in env          # only a small allow-list of variables reaches the engine


def test_archify_refuses_an_unknown_type(tmp_path):
    r = R.archify_finalize("spaceship", {"meta": {}}, tmp_path)
    assert not r["ok"] and "spaceship" in r["problems"][0]


def test_receipt_reader_takes_the_last_json():
    assert R._last_json('log line\n{"ok": true, "gates": {"validate": "pass"}}') == {"ok": True, "gates": {"validate": "pass"}}
    assert R._last_json("no json") is None


@pytest.mark.skipif(not R.node_bin() or not R.chrome_path(), reason="needs node >= 18 and a Chrome / Chromium")
def test_archify_example_passes_its_four_gates(tmp_path):
    r = R.archify_finalize("architecture", V.ARCHIFY / "examples" / "web-app.architecture.json", tmp_path, slug="web-app")
    assert r["ok"], r["problems"]
    assert r["gates"] == {"validate": "pass", "deliver": "pass", "check": "pass", "browser-check": "pass"}
    assert Path(r["html"]).is_file()
    assert (r["receipt"].get("update") or {}).get("source") != "network"     # the update check did not go out


def test_diagram_design_checkers_pass_its_examples_and_catch_a_broken_one(tmp_path):
    good = [V.DD / "assets" / "example-flowchart.html", V.DD / "assets" / "example-architecture.html"]
    assert R.dd_check(good)["ok"]
    broken = tmp_path / "broken.html"
    broken.write_text(good[0].read_text().replace('role="img"', ""), "utf-8")
    r = R.dd_check([broken])
    assert not r["ok"] and r["failed"]


def test_drawio_file_list_and_patterns():
    pats = DR.patterns()
    assert "index.html" in pats and "js/app.min.js" in pats
    rx = [DR._rx(p) for p in pats]
    assert DR.wanted("index.html", rx) and DR.wanted("img/lib/aws4/compute.png", rx)
    assert DR.wanted("styles/a/b/c.css", rx)                    # ** crosses folders
    assert not DR.wanted("WEB-INF/web.xml", rx) and not DR.wanted("js/unknown.js", rx)
    assert DR._rx("resources/dia*.txt").match("resources/dia_de.txt")
    assert not DR._rx("resources/dia*.txt").match("resources/x/dia.txt")   # * stays inside one folder


def _fake_war() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("index.html", "<html>draw.io</html>")
        z.writestr("js/app.min.js", "/*app*/")
        z.writestr("WEB-INF/web.xml", "<web/>")                # not in the list: never unpacked
        z.writestr("../evil.txt", "x")                         # a path that climbs out: never unpacked
        z.writestr("LICENSE", "Apache License 2.0")
    return buf.getvalue()


def test_drawio_setup_refuses_a_download_that_is_not_the_pinned_release(tmp_path, monkeypatch):
    monkeypatch.setattr(DR, "base_dir", lambda: tmp_path / "drawio")
    war = tmp_path / "draw.war"
    war.write_bytes(_fake_war())
    r = DR.setup(war_path=str(war), force=True)
    assert not r["ok"] and "not draw.io" in r["said"]
    assert not DR.ready()


def test_drawio_setup_unpacks_only_the_listed_files(tmp_path, monkeypatch):
    data = _fake_war()
    pin = {"version": "vTEST", "sha256": hashlib.sha256(data).hexdigest(),
           "downloadUrl": "https://github.com/jgraph/drawio/releases/download/vTEST/draw.war"}
    monkeypatch.setattr(V, "drawio_pin", lambda: pin)
    monkeypatch.setattr(DR, "base_dir", lambda: tmp_path / "drawio")
    war = tmp_path / "draw.war"
    war.write_bytes(data)
    r = DR.setup(war_path=str(war), force=True)
    assert r["ok"] and r["files"] == 2
    d = tmp_path / "drawio" / "vTEST"
    assert (d / "index.html").is_file() and (d / "js" / "app.min.js").is_file()
    assert not (d / "WEB-INF").exists() and not (tmp_path / "drawio" / "evil.txt").exists()
    assert "JGraph" in (d / "LICENSE").read_text() and DR.ready()


def test_drawio_setup_only_trusts_jgraphs_release_address(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "drawio_pin", lambda: {"version": "v1", "sha256": "0" * 64,
                                                  "downloadUrl": "https://example.com/draw.war"})
    monkeypatch.setattr(DR, "base_dir", lambda: tmp_path / "drawio")
    r = DR.setup(force=True)
    assert not r["ok"] and "refused" in r["said"]


@pytest.mark.skipif(not DR.ready() or not R.chrome_path(), reason="needs the draw.io editor (python -m app.diagram setup)")
def test_drawio_editor_loads_a_diagram_and_exports_a_png(tmp_path):
    from app.diagram.__main__ import SAMPLE_DRAWIO
    r = R.drawio_png(SAMPLE_DRAWIO, tmp_path / "c.png")
    assert r["ok"], r
    assert (tmp_path / "c.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_settings_setup_job_and_plan():
    from app.config import Settings
    s = Settings()
    assert s.diagram_enabled is True and s.diagram_drawio_dir == "" and s.diagram_chrome_no_sandbox is False
    ops = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert "diagram_setup)" in ops and "diagram_check)" in ops and "python -m app.diagram setup" in ops
    assert (ROOT / "server" / "tools" / "diagram_sync.py").is_file()
    plan = (ROOT / "docs" / "DIAGRAM_TOOL_PLAN.md").read_text()
    assert "§7a" in plan or "7a. Global" in plan


def test_status_reads_only(tmp_path, monkeypatch):
    from app.diagram.__main__ import status
    st = status()
    assert set(st["engines"]) == set(V.ENGINES) and st["types"] == {"archify": 10, "diagram-design": 52}
