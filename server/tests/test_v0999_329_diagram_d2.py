"""HOOLA DIAGRAM D2 (docs/DIAGRAM_TOOL_PLAN.md): the `diagram` tool in Hoola chat - code routes the type to its engine
(archify / diagram-design), the engine's own checks gate it, a failing check goes back with the exact problems (same
diagram id, 3 rounds), a passing diagram is saved as a page (versions) and its picture is handed to the model."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.diagram import runners as R
from app.diagram import service as S
from app.diagram import vendor as V

NEEDS_ENGINES = pytest.mark.skipif(not R.node_bin() or not R.chrome_path(), reason="needs node >= 18 + Chrome")
ARCH = json.loads((V.ARCHIFY / "examples" / "web-app.architecture.json").read_text())
DD_PAGE = (V.DD / "assets" / "example-pyramid.html").read_text()


@pytest.fixture()
def cards(env, monkeypatch):
    from app.events import bus
    seen: list = []
    monkeypatch.setattr(bus, "publish", lambda c, k, p: seen.append((c, k, dict(p))))
    return seen


# ------------------------------------------------------------------ routing: code decides the engine
def test_router_sends_systems_to_archify_and_the_rest_to_diagram_design():
    assert S.route("architecture")[:2] == ("archify", "architecture")
    assert S.route("Sequence Diagram")[:2] == ("archify", "sequence")
    assert S.route("state machine")[:2] == ("archify", "lifecycle")
    assert S.route("er")[:2] == ("archify", "erd")                         # diagram-design's id, archify's job
    assert S.route("funnel")[:2] == ("diagram-design", "pyramid")
    assert S.route("org chart")[:2] == ("diagram-design", "org-chart")
    assert S.route("flowchart")[:2] == ("diagram-design", "flowchart")
    assert S.route("budget bridge")[:2] == ("diagram-design", "waterfall")   # the money bridge, not archify's spans
    assert S.route("waterfall")[:2] == ("archify", "waterfall")
    eng, t, note = S.route("journey", engine="archify")
    assert (eng, t) == ("diagram-design", "journey") and "archify does not draw" in note
    assert S.route("spaceship")[0] == "" and "No engine draws" in S.route("spaceship")[2]


def test_catalogue_lists_each_type_once_with_its_engine():
    cat = S.catalogue()
    names = [c["type"] for c in cat]
    assert len(names) == len(set(names))
    assert {"architecture", "workflow", "sequence"} <= {c["type"] for c in cat if c["engine"] == "archify"}
    assert {"pyramid", "org-chart", "journey", "gantt"} <= {c["type"] for c in cat if c["engine"] == "diagram-design"}
    assert "er" not in names and "state" not in names                   # archify's job, not listed twice


def test_guides_are_the_engines_own_words_plus_hoola_rules():
    a = S.guide("architecture")
    assert a["ok"] and a["engine"] == "archify" and "architecture.schema.json" in a["guide"]
    assert "authoring defaults" in a["guide"] and "web-app.architecture.json" in a["guide"]
    assert "NO coordinates" in a["guide"] and "HER language" in a["guide"]
    b = S.guide("funnel")
    assert b["ok"] and b["engine"] == "diagram-design" and "type-pyramid.md" in b["guide"]
    assert "assets/template.html" in b["guide"] and "Philosophy" in b["guide"] and "right-to-left" in b["guide"]
    assert len(a["guide"]) < 70000 and len(b["guide"]) < 70000          # fits the tool result limit, read whole


# ------------------------------------------------------------------ draw -> check -> show
@NEEDS_ENGINES
def test_archify_diagram_passes_its_gates_is_saved_as_a_page_and_the_model_sees_it(cards):
    from app import artifacts
    r = S.draw("t1", "c1", "architecture", "My web app", ARCH)
    assert r["ok"] and r["engine"] == "archify" and r["shown"], r
    assert r["checks"] == {"validate": "pass", "deliver": "pass", "check": "pass", "browser-check": "pass"}
    look = Path(r["_look"])
    assert look.is_file() and look.read_bytes()[:2] == b"\xff\xd8"          # a JPEG picture for the model
    a = artifacts.get("t1", r["artifact_id"])
    assert a is not None and a.version == 1 and a.summary.startswith("Diagram")
    ver, kind, src = artifacts.current_source(r["artifact_id"])
    assert kind == "diagram" and json.loads(src)["meta"]["title"]          # the description is kept, not the page
    assert any(k == "artifact" for _c, k, _p in cards)                      # the page card / workspace hears it
    # a change = the same page, a new version, re-checked
    old = ARCH["meta"]["title"]
    u = S.update("t1", "c1", r["diagram_id"], edits=[{"old_str": f'"title": "{old}"', "new_str": '"title": "Shop app"'}])
    assert u["ok"] and u["artifact_id"] == r["artifact_id"] and u["version"] == 2, u
    assert "Shop app" in artifacts.current_source(r["artifact_id"])[2]


@NEEDS_ENGINES
def test_a_failing_check_goes_back_with_its_problems_then_the_fix_is_shown(env):
    broken = DD_PAGE.replace('role="img"', "")
    r = S.draw("t1", "c1", "funnel", "Hiring funnel", broken)
    assert r["ok"] is False and r["round"] == 1 and r["rounds_left"] == 2 and r["problems"]
    assert "artifact_id" not in r and r["diagram_id"].startswith("dg-")
    f = S.draw("t1", "c1", "", "", DD_PAGE, diagram_id=r["diagram_id"])
    assert f["ok"] and f["shown"] and f["engine"] == "diagram-design" and Path(f["_look"]).is_file(), f


@NEEDS_ENGINES
def test_still_failing_after_three_rounds_is_shown_with_its_problems_named(env):
    broken = DD_PAGE.replace('role="img"', "")
    r = S.draw("t1", "c1", "funnel", "Funnel", broken)
    r = S.draw("t1", "c1", "", "", broken, diagram_id=r["diagram_id"])
    r = S.draw("t1", "c1", "", "", broken, diagram_id=r["diagram_id"])
    assert r["ok"] and r["shown"] and r["open_problems"] and "do not call it done" in r["said"]


def test_bad_descriptions_are_refused_before_any_engine_runs(env):
    r = S.draw("t1", "c1", "architecture", "x", "{not json")
    assert r["ok"] is False and "not valid JSON" in r["problems"][0]
    r = S.draw("t1", "c1", "funnel", "x", "<svg></svg>")
    assert r["ok"] is False and "WHOLE page" in r["problems"][0]
    assert S.draw("t1", "c1", "spaceship", "x", "{}")["ok"] is False


def test_the_page_tool_never_edits_a_diagram_by_hand(env, cards):
    from app import artifacts
    row = artifacts.save_built("t1", "c1", title="D", page="<!doctype html><html><body><svg></svg></body></html>",
                               source="{}", kind="diagram", summary="Diagram · Architecture")
    with pytest.raises(artifacts.EditError, match="diagram tool"):
        artifacts.write("t1", "c1", "update", artifact_id=row["id"], edits=[{"old_str": "svg", "new_str": "x"}])


# ------------------------------------------------------------------ the picture the model sees
def test_look_becomes_an_image_block_and_never_text(env, tmp_path):
    from app.agent import santosh
    Path("data/diagram").mkdir(parents=True, exist_ok=True)
    pic = Path("data/diagram/look.jpg")
    pic.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 64)
    out = {"ok": True, "_look": str(pic)}
    blk = santosh._look_block(out)
    assert blk["type"] == "image" and blk["source"]["media_type"] == "image/jpeg" and "_look" not in out
    outside = tmp_path.parent / "elsewhere.jpg"
    outside.write_bytes(b"\xff\xd8")
    assert santosh._look_block({"_look": str(outside)}) is None           # only files under data/
    assert santosh._look_block({"ok": True}) is None


# ------------------------------------------------------------------ the tool in Hoola chat
def test_tool_is_registered_found_by_her_words_and_never_web_searches_a_failed_check():
    from app.agent import admit, pakka
    from app.agent.tools import FAMILY_OF, HANDLERS, TOOLS
    spec = next(t for t in TOOLS if t["name"] == "diagram")
    assert {"types", "guide", "draw", "update", "list"} <= set(spec["input_schema"]["properties"]["action"]["enum"])
    assert "diagram" in HANDLERS and FAMILY_OF["diagram"] == "diagram"
    for ask in ("draw an org chart of my team", "make a flowchart for refunds", "user journey for checkout",
                "un diagrama de la arquitectura", "zeichne ein Flussdiagramm"):
        assert "diagram" in admit._match(ask.lower()), ask
    assert "diagram" not in admit._match("what is the weather today")
    assert "diagram" in pakka.SKIP


def test_tool_handler_lists_types_and_guides(env):
    from app.agent.diagram_tools import diagram
    from app.agent.tools import Ctx, ToolError
    ctx = Ctx(tenant_id="t1", conversation_id="c1")
    r = asyncio.run(diagram(ctx, action="types"))
    assert r["ok"] and any(x.startswith("architecture (archify)") for x in r["types"])
    g = asyncio.run(diagram(ctx, action="guide", type="gantt"))
    assert g["engine"] == "diagram-design"
    with pytest.raises(ToolError):
        asyncio.run(diagram(ctx, action="draw", type="gantt"))           # no content
    with pytest.raises(ToolError):
        asyncio.run(diagram(ctx, action="fly"))


@NEEDS_ENGINES
def test_a_drawn_diagram_opens_in_the_console_panel_sandboxed(env, monkeypatch):
    from fastapi.testclient import TestClient

    from tests.test_v161_stream import KEY
    h = {"Authorization": f"Bearer {KEY}"}
    for k, v in (("SIDE_PANEL", "true"), ("API_KEY", KEY), ("PUBLIC_BASE_URL", "https://hoola.example.in"),
                 ("SECRET_KEY", "a-very-long-random-secret-for-tests-0123456789")):
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations", headers=h).json()["id"]
        r = S.draw("default", conv, "funnel", "Hiring funnel", DD_PAGE)
        assert r["ok"], r
        v = c.get(f"/api/panel/pages/{r['artifact_id']}/view", headers=h).json()
        page = c.get(v["url"] + "&panel=1")
        assert page.status_code == 200 and "<svg" in page.text and "PANEL=1" in page.text
        csp = page.headers["content-security-policy"]
        assert "sandbox" in csp and "allow-same-origin" not in csp            # its own opaque origin, never her sign-in
        lib = c.get("/api/panel/library?kind=pages", headers=h).json()["items"]
        assert any(i["ref"] == r["artifact_id"] for i in lib)                  # listed in Creations like every page


@pytest.mark.parametrize("graph", [True, False])
def test_in_a_real_chat_turn_the_model_sees_the_picture(env, monkeypatch, graph):
    """A scripted turn: the model calls diagram, the tool's picture reaches the NEXT model call as an image block inside
    the tool result (both turn engines), and never as base64 text."""
    from tests.test_g3_turngraph import _go
    from tests.test_g0_turngraph import tu, txt
    Path("data/diagram").mkdir(parents=True, exist_ok=True)
    Path("data/diagram/look.jpg").write_bytes(b"\xff\xd8\xff\xe0HOOLAPIC")
    answer = {"ok": True, "diagram_id": "dg-abc", "engine": "archify", "shown": True,
              "said": "Drawn and checked.", "_look": "data/diagram/look.jpg"}
    r = _go(monkeypatch, graph, [([tu(1, "diagram", action="draw", type="architecture", title="App", content="{}")],
                                  "tool_use"), (txt("Your architecture diagram is ready."), "end_turn")],
            "draw my app architecture", answers={"diagram": answer})
    second = r["sent"][1]
    assert '"type": "image"' in second and '"media_type": "image/jpeg"' in second
    assert "_look" not in second and "Drawn and checked." in second
