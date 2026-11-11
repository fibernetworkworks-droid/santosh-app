"""v0.821 HOOLA DOCUMENT KIT D7 (docs/DOCUMENT_KIT_PLAN.md D7): workflows (a chain of pdf_kit steps as one job, saved
under her name, run on one file or a batch), the Documents desk (/api/dockit/* + /console/documents) and the phone
screen's file. Real PDFs made in code; the PDF work itself is never mocked."""
import asyncio
import io
import os
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pikepdf
import pytest
from fastapi.testclient import TestClient

from app.agent import admit, tools
from app.agent import pdfkit_tools as T
from app.dockit import desk, flows
from app.dockit.core import DocError
from app.quality import pdfcard as F
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

REPO = Path(__file__).resolve().parents[2]
KEY = "test-key-documents"
H = {"Authorization": f"Bearer {KEY}"}


def run(c):
    return asyncio.run(c)


def pages_of(b: bytes) -> int:
    with pikepdf.open(io.BytesIO(b)) as p:
        return len(p.pages)


@pytest.fixture
def tool_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PC_FILES_DIR", str(tmp_path / "files"))
    from app.config import get_settings
    get_settings.cache_clear()
    files = {"a": ("Bill A.pdf", F.text_pdf(3, "A")), "b": ("Bill B.pdf", F.text_pdf(2, "B")),
             "c": ("Bill C.pdf", F.text_pdf(4, "C")), "bad": ("x.pdf", b"%PDF-1.4 nothing here"),
             "j1": ("p1.jpg", F.noisy_photo(800, 600)), "j2": ("p2.jpg", F.noisy_photo(600, 800, 2))}
    out = []

    def get(ctx, fid):
        if fid not in files:
            raise T.ToolError("not found")
        return files[fid]

    def put(ctx, name, data):
        out.append((name, data))
        return {"file_id": f"o{len(out)}", "name": name}
    monkeypatch.setattr(T, "_get", get)
    monkeypatch.setattr(T, "_put", put)
    yield SimpleNamespace(ctx=SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="owner"), out=out, files=files)
    get_settings.cache_clear()


# ------------------------------------------------------------------------------------------ the rules
def test_chain_rules_refuse_before_anything_runs():
    for bad, word in (([{"action": "redact"}], "preview"), ([{"action": "unlock"}], "own one-time page"),
                      ([{"action": "compress"}, {"action": "merge"}], "only be step 1"),
                      ([{"action": "protect"}, {"action": "compress"}], "only be the last"),
                      ([{"action": "protect", "password": "mine"}], "password Hoola makes"),
                      ([{"action": "translate"}], "AI steps"), ([{"action": "sign", "mode": "digital"}], "place"),
                      ([{"action": "frobnicate"}], "not a workflow step"), ([], "needs steps"),
                      ([{"action": "rotate"}] * (flows.MAX_STEPS + 1), "up to")):
        with pytest.raises(DocError) as e:
            flows.check(bad)
        assert word in str(e.value), (bad, str(e.value))
    good = flows.check(["merge", {"action": "compress", "target_kb": 900, "file_ids": ["x"], "file_id": "y"}])
    assert good == [{"action": "merge"}, {"action": "compress", "target_kb": 900}]    # a step never names its own input
    assert flows.describe(good) == "merge -> compress (target_kb=900)"
    assert set(flows.STEPS) <= set(T.ACTIONS) and not set(flows.NEVER) & set(flows.STEPS)


def test_saved_workflows_are_hers_and_survive(tool_env):
    r = flows.save("t1", "CA ke liye", [{"action": "merge"}, {"action": "page_numbers"}, {"action": "protect"}])
    assert r["key"] == "ca-ke-liye" and not r["replaced"]
    assert flows.save("t1", "ca ke LIYE", ["merge", "protect"])["replaced"]           # same name = replaced, not a twin
    assert [m["name"] for m in flows.listing("t1")["mine"]] == ["ca ke LIYE"]
    assert flows.listing("t2")["mine"] == []                                           # another account sees nothing
    assert {x["key"] for x in flows.listing("t2")["ready_made"]} == set(flows.PRESETS)
    assert flows.find("t1", "CA ke liye")[1] == [{"action": "merge"}, {"action": "protect"}]
    assert flows.find("t1", "ca")[0] == "For the CA"                                  # a ready-made one by its key
    with pytest.raises(DocError):
        flows.find("t2", "CA ke liye")
    assert flows.delete("t1", "CA ke liye") == {"deleted": "ca ke LIYE"}
    with pytest.raises(DocError):
        flows.delete("t1", "CA ke liye")
    assert "/" not in flows._safe_tenant("../../etc")                                  # no path out of her folder
    with pytest.raises(DocError):
        flows._safe_tenant("")


# ------------------------------------------------------------------------------------------ the tool
def test_ca_chain_delivers_one_locked_file_and_no_in_between_files(tool_env):
    r = run(T.pdf_kit(tool_env.ctx, "flow", file_ids=["a", "b"], workflow="ca"))
    assert len(tool_env.out) == 1                                       # merged / numbered / compressed stayed in memory
    name, blob = tool_env.out[0]
    assert name == "Bill A (For the CA).pdf" and r["name"] == name
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(io.BytesIO(blob))
    assert r["password_links"][0]["file"] == name and r["password_links"][0]["link"].startswith("/pdf/key/")
    from app.dockit import vault
    pw = vault.get(r["password_links"][0]["link"].rsplit("/", 1)[1])["payload"]["password"]
    assert pw and pw not in str(r)                                                  # the password never rides the result
    assert r["steps"].startswith("merge -> page_numbers") and "kept_for" in r


def test_a_custom_chain_is_saved_and_run_again(tool_env):
    steps = [{"action": "rotate", "degrees": 90}, {"action": "page_numbers", "digits": "devanagari"}]
    r = run(T.pdf_kit(tool_env.ctx, "flow", file_id="c", steps=steps, save_as="Ghuma ke number"))
    assert r["saved_as"] == "Ghuma ke number" and len(tool_env.out) == 1 and pages_of(tool_env.out[0][1]) == 4
    with pikepdf.open(io.BytesIO(tool_env.out[0][1])) as p:
        assert int(p.pages[0].get("/Rotate", 0)) == 90
    r2 = run(T.pdf_kit(tool_env.ctx, "flow", file_ids=["a"], workflow="ghuma ke number"))
    assert r2["workflow"] == "Ghuma ke number" and flows.listing("t1")["mine"][0]["runs"] == 1


def test_batch_runs_each_file_and_one_bad_file_never_stops_the_rest(tool_env):
    r = run(T.pdf_kit(tool_env.ctx, "flow", file_ids=["a", "bad", "b", "c"], batch=True,
                      steps=[{"action": "rotate", "degrees": 180}]))
    assert r["ran_on"] == 3 and len(r["failed"]) == 1 and r["failed"][0]["file_id"] == "bad"
    assert "Step 1 (rotate)" in r["failed"][0]["why"]
    assert "zip" not in r and sorted(pages_of(b) for _, b in tool_env.out) == [2, 3, 4]
    tool_env.out.clear()
    many = {f"f{i}": (f"Doc {i}.pdf", F.text_pdf(1, str(i))) for i in range(5)}
    tool_env.files.update(many)
    r = run(T.pdf_kit(tool_env.ctx, "flow", file_ids=list(many), steps=["grayscale"]))   # many files, no merge = a batch
    assert r["zip"] and len(tool_env.out) == 1 and tool_env.out[0][0].endswith(".zip")
    assert len(zipfile.ZipFile(io.BytesIO(tool_env.out[0][1])).namelist()) == 5


def test_photos_portal_chain_and_split_last(tool_env):
    r = run(T.pdf_kit(tool_env.ctx, "flow", file_ids=["j1", "j2"], workflow="portal"))
    assert r["ran_on"] == 1 and pages_of(tool_env.out[-1][1]) == 2 and len(tool_env.out[-1][1]) <= 200 * 1024 + 10
    tool_env.out.clear()
    r = run(T.pdf_kit(tool_env.ctx, "flow", file_ids=["a", "c"], steps=["merge", {"action": "split", "mode": "each"}]))
    assert r["count"] == 7 and [pages_of(b) for _, b in tool_env.out] == [1] * 7     # split last: every page delivered


def test_flow_refusals_name_the_fix(tool_env):
    with pytest.raises(T.ToolError) as e:
        run(T.pdf_kit(tool_env.ctx, "flow", file_ids=["a", "b"], workflow="ca", batch=True))
    assert "cannot start with merge" in str(e.value)
    with pytest.raises(T.ToolError) as e:
        run(T.pdf_kit(tool_env.ctx, "flow", file_ids=["a"]))
    assert "steps=" in str(e.value)
    with pytest.raises(T.ToolError) as e:
        run(T.pdf_kit(tool_env.ctx, "flow", file_ids=["a"], steps=["redact"]))
    assert "preview" in str(e.value) and tool_env.out == []
    with pytest.raises(T.ToolError) as e:
        run(T.pdf_kit(tool_env.ctx, "flow", file_ids=["bad"], steps=["rotate"]))   # one file: its failure is the answer
    assert "Step 1 (rotate)" in str(e.value)
    assert getattr(T._MEM, "files", None) is None                                                     # memory mode never leaks out


def test_drive_file_as_an_input(tool_env, monkeypatch):
    from app.drive import service as dsv
    seen = {}

    def fetch(tenant, ref, fmt=None):
        seen["ref"] = ref
        return "Big scan.pdf", "application/pdf", F.text_pdf(2, "D"), None, {}
    monkeypatch.setattr(dsv, "fetch", fetch)
    r = run(T.pdf_kit(tool_env.ctx, "compress", file_id="drive:acc1~XYZ", level="extreme"))
    assert seen["ref"] == "acc1~XYZ" and (r.get("file_id") or r.get("changed") is False)


def test_every_card_says_how_long_the_file_stays(tool_env):
    r = run(T.pdf_kit(tool_env.ctx, "rotate", file_id="a", degrees=90))
    assert r["kept_for"].startswith("24 hours") and "Drive" in r["kept_for"]
    assert "kept_for" not in run(T.pdf_kit(tool_env.ctx, "info", file_ids=["a"]))     # a read makes no file


def test_reached_from_her_words():
    from tests.test_v0794_dockit import _in_view
    for ask in ("scan to pdf kar do", "in sab pdf pe page number aur compress dono karo", "ilovepdf jaisa kaam"):
        assert "pdf_kit" in _in_view(ask), ask
    assert "flow" in T.PDF_KIT_TOOLS[0]["description"] and "workflow" in T.PDF_KIT_TOOLS[0]["input_schema"]["properties"]
    assert set(T.ACTIONS) >= {"flow", "flow_save", "flow_list", "flow_delete"}


# ------------------------------------------------------------------------------------------ the desk
def test_the_grid_only_offers_real_pdf_kit_actions():
    cat = desk.catalogue()
    ids = [t["id"] for g in cat["groups"] for t in g["items"]]
    assert len(ids) == len(set(ids)) >= 40 and set(ids) <= set(T.ACTIONS)
    assert desk.RUNNABLE <= set(T.ACTIONS) and "guide" not in desk.RUNNABLE
    for g in cat["groups"]:
        for t in g["items"]:
            assert t["input"] in ("pdf", "pdfs", "two", "files", "url") and t["title"] and t["line"]
            for o in t["opts"]:
                assert len(o) == 5 and o[2] in ("text", "number", "select", "bool", "pages")
                if o[2] == "select":
                    assert str(o[3]) in [str(c) for c in o[4]], (t["id"], o)
    assert desk.clean_args({"every": "3", "ranges": "1-2, 5-", "opacity": "0.4", "x": "", "action": "evil"}) == \
        {"every": 3, "ranges": ["1-2", "5-"], "opacity": 0.4}


@pytest.fixture
def dk(env, monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY", KEY)
    monkeypatch.setenv("PC_FILES_DIR", str(tmp_path / "pcfiles"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app.main import app
    yield TestClient(app)
    get_settings.cache_clear()


def test_desk_routes_end_to_end(dk):
    assert dk.get("/api/dockit/tools").status_code == 401                         # her key, always
    assert dk.get("/api/dockit/tools", headers=H).json()["groups"]
    up = []
    for name, data in (("A.pdf", F.text_pdf(3, "A")), ("B.pdf", F.text_pdf(2, "B"))):
        r = dk.post("/api/dockit/upload", headers=H, files={"file": (name, data, "application/pdf")})
        assert r.status_code == 200, r.text
        up.append(r.json()["file_id"])
    r = dk.post("/api/dockit/run", headers=H, json={"action": "merge", "args": {"file_ids": up}})
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert res["pages"] == 5 and res["url"].startswith("/api/pc/files/") and "kept_for" in res
    got = dk.get(res["url"])                                                       # the signed link opens without her key
    assert got.status_code == 200 and pages_of(got.content) == 5
    r = dk.post("/api/dockit/run", headers=H, json={"action": "flow", "args": {"file_ids": up, "workflow": "ca"}})
    assert r.status_code == 200 and r.json()["result"]["password_links"]
    assert dk.post("/api/dockit/run", headers=H, json={"action": "guide"}).status_code == 400
    bad = dk.post("/api/dockit/run", headers=H, json={"action": "rotate", "args": {"file_id": "file_nope"}})
    assert bad.status_code == 400 and bad.json()["detail"]
    s = dk.post("/api/dockit/flows", headers=H, json={"name": "Office copy 2", "steps": ["page_numbers", "grayscale"]})
    assert s.status_code == 200 and s.json()["key"] == "office-copy-2"
    assert dk.post("/api/dockit/flows", headers=H, json={"name": "x", "steps": ["protect", "merge"]}).status_code == 400
    assert [f["key"] for f in dk.get("/api/dockit/flows", headers=H).json()["mine"]] == ["office-copy-2"]
    assert dk.delete("/api/dockit/flows/office-copy-2", headers=H).status_code == 200
    assert dk.delete("/api/dockit/flows/office-copy-2", headers=H).status_code == 404
    page = dk.get("/console/documents")
    assert page.status_code == 200 and "documents.js" in page.text and "Content-Security-Policy" in page.headers
    assert dk.get("/api/console/config").json().get("documents") is True


def test_switched_off_means_gone(dk, monkeypatch):
    monkeypatch.setenv("DOCUMENTS_PAGE", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert dk.get("/api/dockit/tools", headers=H).status_code == 404
    assert dk.get("/console/documents", follow_redirects=False).status_code == 307


def test_console_row_and_phone_screen_are_wired():
    con = REPO / "server" / "app" / "static" / "console"
    v2 = (con / "v2.js").read_text()
    assert "'/console/documents'" in v2 and "['documents', 'Documents']" in v2 and "IC.documents" in v2
    js = (con / "documents.js").read_text()
    assert "/api/dockit/run" in js and "/api/dockit/upload" in js and 'type="password"' not in js   # never typed here
    dart = (REPO / "lib" / "ui" / "documents_screen.dart").read_text()
    assert "ScanToPdfPage" in dart and "ImageSource.camera" in dart and "/api/dockit/run" in dart
    assert "DocumentsScreen(app: app)" in (REPO / "lib" / "ui" / "profile_screen.dart").read_text()


# ------------------------------------------------------------------------------------------ the page, in a real browser
def test_the_page_in_a_real_browser(arena_server, tmp_path):  # noqa: F811
    """Grid -> search -> Compress: upload two PDFs, batch, result links -> Workflows: build + save + run the CA chain."""
    base, browser, key = arena_server
    one, two = tmp_path / "Bill A.pdf", tmp_path / "Bill B.pdf"
    one.write_bytes(F.text_pdf(3, "A"))
    two.write_bytes(F.text_pdf(2, "B"))
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(f"{e} @ {pg.url}"))
    shots = os.environ.get("HOOLA_SHOTS")
    snap = (lambda n: (pg.wait_for_timeout(300), pg.screenshot(path=f"{shots}/documents_{n}.png"))) if shots else (lambda n: None)

    pg.goto(base + "/console/documents")
    pg.wait_for_selector(".hd-card")
    assert pg.locator(".hd-card").count() >= 40
    snap("1_grid")
    pg.fill("#q", "compress")
    assert pg.locator(".hd-card").count() == 1
    pg.click(".hd-card")
    pg.wait_for_selector("#pick", state="attached")
    pg.set_input_files("#pick", [str(one)])
    pg.wait_for_selector(".hd-files li")
    pg.click("#go")
    pg.wait_for_selector(".hd-res")
    assert "Done" in pg.inner_text(".hd-res") or "Not done" not in pg.inner_text(".hd-res")
    snap("2_compress")

    pg.goto(base + "/console/documents#/t/merge")
    pg.wait_for_selector("#pick", state="attached")
    pg.set_input_files("#pick", [str(one), str(two)])
    pg.wait_for_selector(".hd-files li >> nth=1")
    pg.click("[data-down='0']")                                      # her order: B first
    assert pg.inner_text(".hd-files li >> nth=0").find("Bill B") >= 0
    pg.click("#go")
    pg.wait_for_selector(".hd-out a")
    href = pg.get_attribute(".hd-out a", "href")
    assert href.startswith("/api/pc/files/")
    snap("3_merge")

    pg.goto(base + "/console/documents#/flows")
    pg.wait_for_selector("#addStep")
    for step in ("page_numbers", "grayscale"):
        pg.select_option("#addStep", step)
        pg.click("#addBtn")
    pg.fill("[data-sopt='0']", "digits=devanagari")
    pg.fill("#fname", "Ghar ke kaagaz")
    pg.click("#saveFlow")
    pg.wait_for_selector("text=Ghar ke kaagaz")
    pg.click("[data-run='ca']")
    pg.wait_for_selector("#runBox #pick", state="attached")
    pg.set_input_files("#runBox #pick", [str(one), str(two)])
    pg.wait_for_selector("#runBox .hd-files li >> nth=1")
    pg.click("#runBox #go")
    pg.wait_for_selector("#runBox .hd-res")
    txt = pg.inner_text("#runBox .hd-res")
    assert "See the password once" in txt, txt
    snap("4_workflow")
    wide = pg.evaluate("(() => { const m = document.querySelector('#hdMain'); return m.scrollWidth <= m.clientWidth + 1; })()")
    assert wide, "the page overflows sideways"
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.goto(base + "/console/documents")
    pg.wait_for_selector(".hd-card")
    assert pg.evaluate("document.documentElement.scrollWidth <= 391"), "phone width overflows"
    snap("5_phone")
    assert not errs, errs
    ctx.close()
