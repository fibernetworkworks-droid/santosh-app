"""v0.999.326 the awesome-react read, built: eight libraries behind kit parts (DataTable, Guard / AppGuard, QrCode +
upiLink, Schedule, Flow, PdfButton, Prose, zustand) and tests in the box (Vitest + React Testing Library + jsdom,
app_engine action=test, the done check needs them passing once an app has tests).

The real build + test run needs the image's packages: HOOLA_APPENGINE_NODE_MODULES=<npm ci of app/appengine/image>
(the local runner); without it that one test skips, saying so."""
import asyncio
import json
import os
from pathlib import Path

import pytest

from tests.test_v0999_322_bolt_ideas import PLAN, _refused, _tool, gate_env  # noqa: F401  (fixture + helpers)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app" / "appengine"
LIBS = {"@tanstack/react-table": "9.3.1", "react-error-boundary": "6.1.6", "qrcode.react": "4.2.0",
        "react-big-calendar": "1.20.0", "@xyflow/react": "12.12.1", "@react-pdf/renderer": "4.9.0",
        "markdown-to-jsx": "9.10.6", "zustand": "5.1.0"}
TESTS = {"vitest": "5.1.0", "@testing-library/react": "16.3.3", "@testing-library/dom": "10.4.2",
         "@testing-library/user-event": "14.6.10", "jsdom": "31.0.1"}
PARTS = ["data-table.tsx", "error-guard.tsx", "qr-code.tsx", "schedule.tsx", "schedule.css", "flow.tsx", "flow.css",
         "pdf.tsx", "markdown.tsx"]


def test_the_libraries_are_vetted_pinned_and_locked():
    from app.appengine import image as IMG
    for k, v in LIBS.items():
        assert IMG.CORE[k] == v and IMG.VETTED[k] == v, k                    # in every new app, used only where imported
    for k, v in TESTS.items():
        assert IMG.DEV[k] == v and k not in IMG.CORE, k                       # build / test tools, never shipped
    assert IMG.IMAGE_REV == "3" and 'hoola.appengine.rev="3"' in IMG.DOCKERFILE_TEXT
    lock = json.loads((ROOT / "image" / "package-lock.json").read_text())["packages"]
    for k, v in {**LIBS, **TESTS}.items():
        assert lock["node_modules/" + k]["version"] == v, k
    assert lock[""]["dependencies"] == IMG.image_package()["dependencies"]


def test_every_new_kit_part_passes_the_apps_own_rules_and_parses():
    from app.appengine import image as IMG, rules as RL, syntax as SX
    for f in PARTS:
        rel = f"src/components/ui/{f}"
        code = (ROOT / "template" / rel).read_text()
        assert RL.check_file(rel, code, set(IMG.CORE)) == [], f
        assert SX.check(rel, code) in ([], None), f
    main = (ROOT / "template" / "src" / "main.tsx").read_text()
    assert "<AppGuard>" in main and "./components/ui/error-guard" in main
    md = (ROOT / "template" / "src" / "components" / "ui" / "markdown.tsx").read_text()
    assert "disableParsingRawHTML: true" in md                                 # text people type never draws HTML
    assert "vitest.config.ts" in RL.LOCKED and (ROOT / "template" / "vitest.config.ts").exists()


def test_hoola_is_told_what_each_part_is_for(gate_env):
    from app.agent.appengine_tools import APPENGINE_TOOLS
    from app.appengine import kit as KIT, service as AE
    desc = APPENGINE_TOOLS[0]["description"]
    for name in ("DataTable", "Guard", "QrCode", "upiLink", "Schedule", "Flow", "PdfButton", "Prose", "zustand", "action=test"):
        assert name in desc, name
    assert {"data-table", "qr-code", "schedule", "flow", "pdf", "markdown", "error-guard"} <= set(KIT.ui_parts())
    agents = (ROOT / "template" / "AGENTS.md").read_text()
    assert "DataTable" in agents and "action=test" in agents and len(agents) < 4000          # the whole guide reaches the model
    from app.agent import turnmode as TM
    aid = _tool(action="create", name="Shop", brief="x")["id"]
    tok = TM.APP.set(aid)
    try:
        block = AE.prompt_block(T)
    finally:
        TM.APP.reset(tok)
    assert "React parts (src/components/ui, already in every app): DataTable" in block and "no tests yet" in block
    writer = (ROOT / "writer.py").read_text()
    assert "qr-code = QrCode + upiLink" in writer and "markdown =\n  Prose" in writer


def test_test_tools_only_in_test_files():
    from app.appengine import rules as RL
    t = 'import { it } from "vitest";\nimport { render } from "@testing-library/react";\nit("x", () => {});\n'
    assert RL.check_file("src/pages/Home.test.tsx", t, set()) == []
    probs = RL.check_file("src/pages/Home.tsx", t, set())
    assert probs and all("for tests only" in p["found"] for p in probs if p["rule"] == "import")
    assert RL.is_test("src/x/a.test.ts") and not RL.is_test("src/a.tsx") and not RL.is_test("tests/a.test.ts")


def test_an_older_app_gets_the_new_parts_and_tests_are_said_when_missing(gate_env):
    from app.appengine import service as AE
    aid = _tool(action="create", name="Old app", brief="x")["id"]
    r = AE._load(T, aid)
    for f in PARTS:
        (AE.src_dir(r) / "src/components/ui" / f).unlink()
    AE._refresh_template(r)
    assert all((AE.src_dir(r) / "src/components/ui" / f).exists() for f in PARTS)
    mine = AE.src_dir(r) / "src/components/ui/qr-code.tsx"
    mine.write_text("export const Mine = 1;\n")
    AE._refresh_template(r)
    assert mine.read_text() == "export const Mine = 1;\n"                      # never over her own file
    assert "no tests yet" in _tool(action="test", app=aid)["say"]


def test_the_done_check_needs_passing_tests_once_an_app_has_them(gate_env, monkeypatch):
    from app.appengine import runner as RN, service as AE
    aid = _tool(action="create", name="Tasks", brief="x")["id"]
    _tool(action="plan", app=aid, **PLAN)
    _tool(action="write", app=aid, path="src/pages/Home.test.tsx",
          code='import { it, expect } from "vitest";\nit("adds", () => { expect(1 + 1).toBe(2); });\n')
    _tool(action="build", app=aid)
    d = _tool(action="done", app=aid, summary="x", criteria=[{"id": "heading"}, {"id": "builds"}])
    assert d["accepted"] is False and "run them now (action=test)" in d["say"]
    box = {"ok": False}
    monkeypatch.setattr(RN, "test", lambda src, wait=20.0: {"ran": True, "ok": box["ok"], "passed": 1 if box["ok"] else 0,
                                                            "failed": 0 if box["ok"] else 1, "seconds": 1, "tests": [
        {"file": "src/pages/Home.test.tsx", "name": "adds", "status": "passed" if box["ok"] else "failed", "message": "expected 3 to be 2"}]})
    t = _tool(action="test", app=aid)
    assert "FAILED" in t["say"] and "Home.test.tsx > adds" in t["say"]
    assert "tests FAILED" in _tool(action="work", app=aid)["next"]
    box["ok"] = True
    assert "1 test(s) passed" in _tool(action="test", app=aid)["say"]
    ok = _tool(action="done", app=aid, summary="x", criteria=[{"id": "heading"}, {"id": "builds"}])
    assert ok["accepted"] and "1 test(s) passed after the last change" in ok["say"]


PAGE = '''import * as React from "react";
import { DataTable } from "@/components/ui/data-table";
import { QrCode, upiLink } from "@/components/ui/qr-code";
import { Schedule } from "@/components/ui/schedule";
import { Flow } from "@/components/ui/flow";
import { PdfButton } from "@/components/ui/pdf";
import { Prose } from "@/components/ui/markdown";
import { Guard } from "@/components/ui/error-guard";
import { create } from "zustand";

type Order = { id: string; customer: string; total: number };
export const ORDERS: Order[] = [
  { id: "1", customer: "Meera", total: 250 },
  { id: "2", customer: "Arjun", total: 90 },
  { id: "3", customer: "Zoya", total: 400 },
];
export const useCart = create<{ count: number; add: () => void }>((set) => ({ count: 0, add: () => set((s) => ({ count: s.count + 1 })) }));

export default function Shop() {
  const { count, add } = useCart();
  const day = new Date(2026, 10, 28, 10);
  return (
    <main className="space-y-8 p-6">
      <DataTable rows={ORDERS} columns={[{ key: "customer", label: "Customer" }, { key: "total", label: "Total", align: "right" }]} searchLabel="Search orders" />
      <QrCode value={upiLink({ pa: "shop@upi", pn: "Sharma Sweets", am: 250 })} label="Scan to pay" />
      <Guard><Schedule events={[{ id: "a", title: "Haircut", start: day, end: new Date(2026, 10, 28, 11) }]} /></Guard>
      <Flow nodes={[{ id: "a", position: { x: 0, y: 0 }, data: { label: "Order placed" } }]} edges={[]} editable={false} />
      <PdfButton fileName="invoice.pdf" document={({ Document, Page, Text }) => <Document><Page size="A4"><Text>Invoice</Text></Page></Document>}>Download invoice</PdfButton>
      <Prose text={"## Help\\n\\nPay **on time**. <b>raw</b>"} />
      <button type="button" onClick={add}>In cart: {count}</button>
    </main>
  );
}
'''
SPEC = '''import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataTable } from "@/components/ui/data-table";
import { QrCode, upiLink } from "@/components/ui/qr-code";
import { Prose } from "@/components/ui/markdown";
import { Guard } from "@/components/ui/error-guard";
import { ORDERS, useCart } from "./Shop";

describe("orders table", () => {
  it("sorts by a heading and searches every column", async () => {
    const user = userEvent.setup();
    render(<DataTable rows={ORDERS} columns={[{ key: "customer", label: "Customer" }, { key: "total", label: "Total" }]} />);
    await user.click(screen.getByRole("button", { name: /Customer/ }));
    const names = () => screen.getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[0].textContent);
    expect(names()).toEqual(["Arjun", "Meera", "Zoya"]);
    await user.type(screen.getByPlaceholderText("Search"), "zo");
    expect(names()).toEqual(["Zoya"]);
  });
});

describe("the other parts", () => {
  it("makes a UPI link and a QR", () => {
    expect(upiLink({ pa: "shop@upi", pn: "Sharma Sweets", am: 250 })).toBe("upi://pay?pa=shop%40upi&pn=Sharma+Sweets&cu=INR&am=250.00");
    render(<QrCode value="hello" label="Scan to pay" />);
    expect(screen.getByText("Scan to pay")).toBeTruthy();
  });
  it("never draws raw HTML from text", () => {
    const { container } = render(<Prose text={"**bold** <img src=x onerror=boom()>"} />);
    expect(container.querySelector("strong")?.textContent).toBe("bold");
    expect(container.querySelector("img")).toBeNull();
  });
  it("a crash shows a box, not a blank page", () => {
    const Boom = () => { throw new Error("boom"); };
    render(<Guard><Boom /></Guard>);
    expect(screen.getByRole("alert").textContent).toContain("could not be shown");
  });
  it("shares state with zustand", () => {
    useCart.getState().add();
    expect(useCart.getState().count).toBe(1);
  });
});
'''


@pytest.mark.skipif(not os.environ.get("HOOLA_APPENGINE_NODE_MODULES"), reason="needs the image's packages (HOOLA_APPENGINE_NODE_MODULES)")
def test_a_real_app_with_every_part_builds_and_its_tests_run(site_env, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENGINE_DIR", str(tmp_path / "appengine"))
    monkeypatch.setenv("HOOLA_APPENGINE_AUTOBUILD", "0")
    monkeypatch.setenv("APP_ENGINE_RUNNER", "local")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.db import init_db
    init_db()
    from app.appengine import service as AE
    aid = AE.create(T, "Sweets", "A shop")["id"]
    AE.write(T, aid, "src/pages/Shop.tsx", PAGE)
    AE.write(T, aid, "src/pages/Shop.test.tsx", SPEC)
    d = AE.src_dir(AE._load(T, aid))
    app = (d / "src/App.tsx").read_text().replace('import { Routes, Route } from "react-router-dom";',
                                                  'import { Routes, Route } from "react-router-dom";\nimport Shop from "./pages/Shop";')
    AE.write(T, aid, "src/App.tsx", app.replace('<Route path="*"', '<Route path="/shop" element={<Shop />} />\n      <Route path="*"'))
    home = (d / "src/pages/Home.tsx").read_text()
    AE.write(T, aid, "src/pages/Home.tsx", 'import { Link } from "react-router-dom";\n' + home.replace("</main>", '<Link to="/shop">Shop</Link></main>', 1))
    b = AE.build(T, aid)
    assert b["built"], b["say"]
    lb = json.loads(AE._load(T, aid).last_build)
    assert lb["types_ok"], lb.get("types")                                       # every part type-checks for real
    assert lb["prerender"]["ok"] and lb["prerender"]["pages"] == 2 and not lb["prerender"]["failed"], lb["prerender"]
    r = AE._load(T, aid)
    html = (AE.ver_dir(r, r.version) / "dist" / "shop" / "index.html").read_text()   # rendered on the server, as finished HTML
    assert "<table" in html and "<svg" in html and "rbc-calendar" in html and "react-flow" in html and "<b>raw</b>" not in html
    t = AE.run_tests(T, aid)
    assert t["ok"] and t["passed"] == 5 and t["failed"] == 0, [x["message"][:700] for x in t["tests"] if x["status"] == "failed"]
    # a broken behaviour is caught with the test's name and the reason
    AE.write(T, aid, "src/pages/Shop.test.tsx", SPEC.replace('toEqual(["Zoya"])', 'toEqual(["Meera"])'))
    bad = AE.run_tests(T, aid)
    assert not bad["ok"] and bad["failed"] == 1 and "sorts by a heading" in bad["say"], bad["say"]
