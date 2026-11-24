"""v0.999.185 SHEETS COMPLETE: copy / cut cells, a full copy of a spreadsheet, changing charts and pivot tables,
listing colour rules, reading how cells look, grouping rows / columns and slicers, the sheet's language and time zone,
Google Tables, older versions, Apps Script inside a sheet, BigQuery in a sheet, waiting when Google says 'too many
requests' and splitting big writes into parts. What writes over cells, removes something or saves code waits for her tap."""
from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError
from tests.test_bazar import _events, bz  # noqa: F401
from tests.test_life import conv_ctx
from tests.test_sheets import SID, run
from tests.test_v0999_184_sheets_full import FullFake

NEW = {"copyPaste", "cutPaste", "updateChartSpec", "updateEmbeddedObjectPosition", "addSlicer", "addDimensionGroup",
       "deleteDimensionGroup", "updateDimensionGroup", "addTable", "updateTable", "deleteTable", "addDataSource",
       "refreshDataSource", "deleteDataSource", "addConditionalFormatRule"}


class Fake(FullFake):
    def __init__(self):
        super().__init__()
        self.log = []                  # every new-kind request, as sent
        self.tables, self.slicers, self.groups, self.sources, self.cf = [], [], [], [], []
        self.copies, self.uploads, self.scripts, self.revs = [], [], {}, []
        self.busy = 0                  # answer 429 this many times first
        self.appends = 0

    def _new(self, sid, r):
        k = next(iter(r))
        v = r[k]
        self.log.append(r)
        tabs = self.books[sid]["tabs"]
        if k == "copyPaste":
            s_, d_ = v["source"], v["destination"]
            _, st = self._tab(sid, s_["sheetId"])
            _, dt = self._tab(sid, d_["sheetId"])
            block = [row[s_["startColumnIndex"]:s_["endColumnIndex"]] for row in st["grid"][s_["startRowIndex"]:s_["endRowIndex"]]]
            if v.get("pasteOrientation") == "TRANSPOSE":
                block = [list(x) for x in zip(*block)]
            for i, row in enumerate(block):
                while len(dt["grid"]) <= d_["startRowIndex"] + i:
                    dt["grid"].append([])
                g = dt["grid"][d_["startRowIndex"] + i]
                for j, x in enumerate(row):
                    while len(g) <= d_["startColumnIndex"] + j:
                        g.append("")
                    g[d_["startColumnIndex"] + j] = x
            return {}
        if k == "addTable":
            t = dict(v["table"], tableId=str(900 + len(self.tables)))
            self.tables.append(t)
            return {"addTable": {"table": {"tableId": t["tableId"]}}}
        if k == "deleteTable":
            self.tables = [t for t in self.tables if t["tableId"] != v["tableId"]]
        if k == "updateTable":
            for t in self.tables:
                if t["tableId"] == v["table"]["tableId"]:
                    t.update({f: v["table"][f] for f in v["fields"].split(",")})
        if k == "addSlicer":
            self.slicers.append(dict(v["slicer"], slicerId=300 + len(self.slicers)))
            return {"addSlicer": {"slicer": {"slicerId": self.slicers[-1]["slicerId"]}}}
        if k == "addDimensionGroup":
            self.groups.append({"range": v["range"], "depth": 1, "collapsed": False})
        if k == "updateDimensionGroup":
            for gp in self.groups:
                if gp["range"] == v["dimensionGroup"]["range"]:
                    gp["collapsed"] = v["dimensionGroup"]["collapsed"]
        if k == "addDataSource":
            ds = dict(v["dataSource"], dataSourceId=f"ds{len(self.sources) + 1}")
            self.sources.append(ds)
            return {"addDataSource": {"dataSource": {"dataSourceId": ds["dataSourceId"]},
                                      "dataExecutionStatus": {"state": "RUNNING"}}}
        if k == "deleteDataSource":
            self.sources = [d for d in self.sources if d["dataSourceId"] != v["dataSourceId"]]
        if k == "updateChartSpec":
            for ch in self.charts:
                if ch["chartId"] == v["chartId"]:
                    ch["spec"] = v["spec"]
        if k == "addConditionalFormatRule":
            self.cf.append(v["rule"])
            self.cf_rules.setdefault(sid, []).append(v)
        return {}

    def __call__(self, req: httpx.Request):
        url = req.url
        try:
            body = json.loads(req.content) if req.content else None
        except ValueError:
            body = None
        if self.busy and url.host == "sheets.googleapis.com":
            self.busy -= 1
            return httpx.Response(429, json={"error": {"message": "Quota exceeded"}})
        if url.host == "script.googleapis.com":
            parts = url.path.strip("/").split("/")
            if url.path == "/v1/projects" and req.method == "POST":
                sid_ = f"script{len(self.scripts) + 1}"
                self.scripts[sid_] = {"parent": body["parentId"], "files": []}
                return httpx.Response(200, json={"scriptId": sid_})
            sid_ = parts[2]
            if req.method == "GET":
                return httpx.Response(200, json={"files": self.scripts[sid_]["files"]})
            self.scripts[sid_]["files"] = body["files"]
            return httpx.Response(200, json={"scriptId": sid_})
        if url.host == "www.googleapis.com" and url.path.startswith("/upload/drive"):
            self.uploads.append(req.content)
            nid = "UP" + "0" * 38
            self.book(nid, "old version", {"Customers": [["Name", "City"], ["Old Shop", "Goa"]]})
            return httpx.Response(200, json={"id": nid, "name": "old version", "webViewLink": "https://x/up"})
        if url.host == "www.googleapis.com" and url.path.endswith("/copy"):
            self.copies.append(body)
            return httpx.Response(200, json={"id": "COPY1", "name": body["name"], "webViewLink": "https://x/copy"})
        if url.host == "www.googleapis.com" and url.path.endswith("/revisions"):
            return httpx.Response(200, json={"revisions": self.revs})
        if url.host == "export.example":
            return httpx.Response(200, content=b"PK-fake-xlsx")
        if url.host == "sheets.googleapis.com":
            path = url.path.removeprefix("/v4/spreadsheets").lstrip("/")
            sid, _, rest = path.partition("/")
            action = sid.split(":", 1)[1] if ":" in sid else ""
            sid = sid.split(":", 1)[0]
            if action == "batchUpdate":
                new = [r for r in body["requests"] if next(iter(r)) in NEW]
                if new:
                    old = [r for r in body["requests"] if next(iter(r)) not in NEW]
                    reps = {id(r): self._new(sid, r) for r in new}
                    rest_rep = []
                    if old:
                        sub = httpx.Request(req.method, req.url, headers=req.headers, json={"requests": old})
                        rest_rep = super().__call__(sub).json().get("replies", [])
                    it = iter(rest_rep)
                    return httpx.Response(200, json={"replies": [reps[id(r)] if id(r) in reps else next(it, {})
                                                                 for r in body["requests"]]})
            if sid in self.books and not rest and not action and req.method == "GET":
                resp = super().__call__(req).json()
                for sh in resp.get("sheets", []):
                    tid = sh["properties"]["sheetId"]
                    sh["tables"] = [t for t in self.tables if t["range"]["sheetId"] == tid]
                    sh["slicers"] = [x for x in self.slicers] if tid == 0 else []
                    sh["rowGroups"] = [g for g in self.groups if g["range"]["sheetId"] == tid and g["range"]["dimension"] == "ROWS"]
                    sh["columnGroups"] = [g for g in self.groups if g["range"]["sheetId"] == tid and g["range"]["dimension"] == "COLUMNS"]
                    sh["conditionalFormats"] = [r for r in self.cf if r["ranges"][0]["sheetId"] == tid]
                    if url.params.get("includeGridData") == "true":
                        sh["data"] = self._grid_data(sid, sh["properties"]["title"], url)
                resp["dataSources"] = self.sources
                return httpx.Response(200, json=resp)
            if rest.startswith("values/") and rest.endswith(":append"):
                self.appends += 1
            if sid in self.books and rest.startswith("values/") and req.method == "GET":
                # the v0.210 fake reads every range from column A; this one reads the columns asked
                import re as _re
                from tests.test_sheets import _cell_ref
                tab, cells = self._split(rest[len("values/"):], sid)
                m = _re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", cells or "")
                if m:
                    g = self.books[sid]["tabs"][tab]["grid"]
                    r0, c0 = _cell_ref(m.group(1) + m.group(2))
                    r1, c1 = _cell_ref(m.group(3) + m.group(4))
                    rows = [r[c0:c1 + 1] for r in g[r0:r1 + 1]]
                    while rows and not rows[-1]:
                        rows.pop()
                    return httpx.Response(200, json={"values": rows})
        return super().__call__(req)

    def _grid_data(self, sid, title, url):
        out = []
        for rng in url.params.get_list("ranges"):
            if not rng.startswith(("'" + title + "'", title)):
                continue
            grid = self.books[sid]["tabs"][title]["grid"]
            rows = []
            for ri, row in enumerate(grid[:10]):
                vals = []
                for ci, x in enumerate(row[:6]):
                    cell = {"formattedValue": str(x)}
                    if ri == 0:
                        cell["effectiveFormat"] = {"textFormat": {"bold": True, "fontFamily": "Arial", "fontSize": 10},
                                                   "backgroundColorStyle": {"rgbColor": {"red": 1, "green": 1, "blue": 0}}}
                    if (ri, ci) == (2, 0) and "pivotTable" in url.params.get("fields", ""):
                        cell = {"pivotTable": {"source": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 5,
                                                          "startColumnIndex": 0, "endColumnIndex": 5},
                                               "rows": [{"sourceColumnOffset": 4}],
                                               "values": [{"summarizeFunction": "SUM", "sourceColumnOffset": 2, "name": "Sum of Due"}]}}
                    vals.append(cell)
                rows.append({"values": vals})
            out.append({"startRow": 0, "startColumn": 0, "rowData": rows})
        return out


@pytest.fixture
def gs(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.mailbox import accounts as ma
    from app.sheets import client as sc
    monkeypatch.setattr(sc, "RETRY_WAIT", 0.0)
    fake = Fake()
    fake.book(SID, "Sales Oct 2026", {"Customers": [
        ["Name", "City", "Due", "Status", "Salesman"],
        ["Sharma Traders", "Pune", 1500, "Pending", "Swati"],
        ["Patil Stores", "Akola", 800, "Pending", "Sandesh"],
        ["Gupta & Sons", "Pune", 2200, "Paid", "Swati"],
        ["Rao Electricals", "Nashik", 1200, "Pending", "Ankita"],
    ], "Notes": [["Note"], ["call back"]]})
    ma.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    from app import main
    with TestClient(main.app) as c:
        url = c.get("/api/sheets/link").json()["url"]
        c.get("/auth/google/callback", params={"code": "c", "state": httpx.URL(url).params["state"]})
    yield fake
    ma.set_http(None)


def grid(fake, tab="Customers"):
    return fake.books[SID]["tabs"][tab]["grid"]


def approve(bz, title):  # noqa: F811
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == title, card["title"]
    bz["svc"].decide("default", card["id"], "approve")
    return card


def test_copy_cells_and_paste_over_asks(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("sheet_cells", {"spreadsheet": "Sales Oct 2026", "action": "copy", "source": "A1:B3", "to": "H1"}, ctx)
    assert out["done"] and grid(gs)[1][7:9] == ["Sharma Traders", "Pune"]
    out = run("sheet_cells", {"spreadsheet": "Sales Oct 2026", "action": "copy", "source": "C1:C3", "to": "A1",
                              "paste": "values"}, ctx)
    assert out["needs_approval"] and out["would_overwrite"] == 3 and grid(gs)[0][0] == "Name"
    approve(bz, "Paste over these cells?")
    assert grid(gs)[0][0] == "Due" and gs.log[-1]["copyPaste"]["pasteType"] == "PASTE_VALUES"
    run("sheet_cells", {"spreadsheet": "Sales Oct 2026", "action": "cut", "source": "A1:A2", "to": "Notes!D5"}, ctx)
    cut = next(r for r in gs.log if "cutPaste" in r)["cutPaste"]
    assert cut["destination"] == {"sheetId": 1, "rowIndex": 4, "columnIndex": 3}
    with pytest.raises(ToolError):
        run("sheet_cells", {"spreadsheet": "Sales Oct 2026", "action": "copy", "source": "A:A", "to": "Z1"}, ctx)


def test_full_copy_and_settings(gs):
    ctx = conv_ctx()
    out = run("sheet_structure", {"spreadsheet": "Sales Oct 2026", "action": "copy_file", "new_name": "Sales backup"}, ctx)
    assert out["id"] == "COPY1" and gs.copies == [{"name": "Sales backup"}]
    run("sheet_structure", {"spreadsheet": "Sales Oct 2026", "action": "settings", "locale": "en_IN",
                            "time_zone": "Asia/Kolkata", "recalc": "every_minute"}, ctx)
    sp = next(r for sid, reqs in gs.batch_log for r in reqs if "updateSpreadsheetProperties" in r)["updateSpreadsheetProperties"]
    assert sp == {"properties": {"locale": "en_IN", "timeZone": "Asia/Kolkata", "autoRecalc": "MINUTE"},
                  "fields": "locale,timeZone,autoRecalc"}
    with pytest.raises(ToolError):
        run("sheet_structure", {"spreadsheet": "Sales Oct 2026", "action": "settings", "time_zone": "Mars/Base"}, ctx)


def test_change_and_move_a_chart(gs):
    ctx = conv_ctx()
    cid = run("sheet_chart", {"spreadsheet": "Sales Oct 2026", "x_column": "Name", "y_columns": ["Due"]}, ctx)["chart_id"]
    out = run("sheet_chart", {"spreadsheet": "Sales Oct 2026", "action": "update", "chart_id": cid, "title": "Dues by shop",
                              "type": "line", "y_title": "Rs"}, ctx)
    assert out["changed"] == ["axis title", "title", "type"]
    spec = gs.charts[0]["spec"]
    assert spec["title"] == "Dues by shop" and spec["basicChart"]["chartType"] == "LINE"
    assert {"position": "LEFT_AXIS", "title": "Rs"} in spec["basicChart"]["axis"]
    run("sheet_chart", {"spreadsheet": "Sales Oct 2026", "action": "update", "chart_id": cid, "type": "pie"}, ctx)
    assert "pieChart" in gs.charts[0]["spec"] and "basicChart" not in gs.charts[0]["spec"]
    run("sheet_chart", {"spreadsheet": "Sales Oct 2026", "action": "move", "chart_id": cid, "place": "Notes!B2", "width": 500}, ctx)
    mv = next(r for r in gs.log if "updateEmbeddedObjectPosition" in r)["updateEmbeddedObjectPosition"]
    assert mv["newPosition"]["overlayPosition"]["anchorCell"] == {"sheetId": 1, "rowIndex": 1, "columnIndex": 1}


def test_pivots_list_change_remove(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("sheet_pivot", {"spreadsheet": "Sales Oct 2026", "action": "list"}, ctx)
    assert {"place": "Customers!A3", "groups_by": [4], "values": ["Sum of Due"], "source": "A1:E5"} in out["pivots"]
    run("sheet_pivot", {"spreadsheet": "Sales Oct 2026", "action": "update", "place": "Customers!A3",
                        "values": [{"column": "Due", "function": "average"}]}, ctx)
    up = gs.pivots[-1]["rows"][0]["values"][0]["pivotTable"]
    assert up["values"][0]["summarizeFunction"] == "AVERAGE" and up["rows"] == [{"sourceColumnOffset": 4}]
    run("sheet_pivot", {"spreadsheet": "Sales Oct 2026", "action": "delete", "place": "Customers!A3"}, ctx)
    approve(bz, "Remove pivot table?")
    assert gs.pivots[-1]["rows"] == [{"values": [{}]}] and gs.pivots[-1]["start"] == {"sheetId": 0, "rowIndex": 2, "columnIndex": 0}
    with pytest.raises(ToolError):
        run("sheet_pivot", {"spreadsheet": "Sales Oct 2026", "action": "delete", "place": "Customers!F9"}, ctx)


def test_colour_rules_list_and_range_inside_rule(gs):
    ctx = conv_ctx()
    run("sheet_conditional_format", {"spreadsheet": "Sales Oct 2026", "range": "C2:C9",
                                     "rule": {"type": "cell_is", "operator": "GREATER_THAN", "values": [1000],
                                              "format": {"bg_color": "red"}}}, ctx)
    req = gs.cf_rules[SID][-1]
    assert "range" not in req and req["rule"]["ranges"][0]["startColumnIndex"] == 2
    out = run("sheet_conditional_format", {"spreadsheet": "Sales Oct 2026", "action": "list"}, ctx)
    assert out["rules"] == [{"rule_index": 0, "ranges": ["C2:C9"], "kind": "cell_is", "condition": "NUMBER_GREATER",
                             "values": ["1000"], "bg_color": "#ff0000"}]
    run("sheet_conditional_format", {"spreadsheet": "Sales Oct 2026", "action": "update", "rule_index": 0, "range": "C2:C9",
                                     "rule": {"type": "cell_is", "operator": "LESS_THAN", "values": [100]}}, ctx)
    upd = next(r for sid, reqs in gs.batch_log for r in reqs if "updateConditionalFormatRule" in r)["updateConditionalFormatRule"]
    assert upd["index"] == 0 and "rule_index" not in upd and upd["rule"]["ranges"]


def test_read_how_cells_look(gs):
    out = run("sheet_read", {"spreadsheet": "Sales Oct 2026", "range": "A1:C2", "show": "look"}, conv_ctx())
    assert out["cells"][0] == {"cell": "A1", "value": "Name", "bg_color": "#ffff00", "bold": True}
    assert all(c["cell"].endswith("1") for c in out["cells"])          # plain cells are left out
    with pytest.raises(ToolError):
        run("sheet_read", {"spreadsheet": "Sales Oct 2026", "range": "A:A", "show": "look"}, conv_ctx())


def test_groups_and_slicers(gs):
    ctx = conv_ctx()
    run("sheet_structure", {"spreadsheet": "Sales Oct 2026", "action": "group_rows", "rows": "2:4"}, ctx)
    run("sheet_structure", {"spreadsheet": "Sales Oct 2026", "action": "collapse_rows", "rows": "2:4"}, ctx)
    out = run("sheet_structure", {"spreadsheet": "Sales Oct 2026", "action": "list_groups"}, ctx)
    assert out["rows"] == [{"span": "2:4", "depth": 1, "folded": True}]
    run("sheet_structure", {"spreadsheet": "Sales Oct 2026", "action": "group_cols", "columns": "C:D"}, ctx)
    assert run("sheet_structure", {"spreadsheet": "Sales Oct 2026", "action": "list_groups"}, ctx)["columns"][0]["span"] == "C:D"
    out = run("sheet_sort_filter", {"spreadsheet": "Sales Oct 2026", "action": "slicer_add", "column": "City"}, ctx)
    assert out["slicer_id"] == 300 and gs.slicers[0]["spec"]["columnIndex"] == 1
    assert run("sheet_sort_filter", {"spreadsheet": "Sales Oct 2026", "action": "slicer_list"}, ctx)["slicers"][0]["column"] == "B"
    run("sheet_sort_filter", {"spreadsheet": "Sales Oct 2026", "action": "slicer_delete", "slicer_id": 300}, ctx)


def test_google_tables(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("sheet_table", {"spreadsheet": "Sales Oct 2026", "action": "add", "name": "Dues",
                              "types": {"Due": "currency"}, "dropdowns": {"Status": ["Pending", "Paid"]}}, ctx)
    t = gs.tables[0]
    assert out["table_id"] == "900" and t["range"]["endRowIndex"] == 5 and len(t["columnProperties"]) == 5
    cp = {p["columnName"]: p for p in t["columnProperties"]}
    assert cp["Due"]["columnType"] == "CURRENCY" and cp["Status"]["columnType"] == "DROPDOWN"
    assert [v["userEnteredValue"] for v in cp["Status"]["dataValidationRule"]["condition"]["values"]] == ["Pending", "Paid"]
    assert "columnType" not in cp["Name"]
    with pytest.raises(ToolError):
        run("sheet_table", {"spreadsheet": "Sales Oct 2026", "action": "add", "name": "x", "types": {"City": "dropdown"}}, ctx)
    run("sheet_table", {"spreadsheet": "Sales Oct 2026", "action": "update", "table_id": "Dues", "new_name": "Dues 2026"}, ctx)
    assert run("sheet_table", {"spreadsheet": "Sales Oct 2026"}, ctx)["tables"][0]["name"] == "Dues 2026"
    run("sheet_table", {"spreadsheet": "Sales Oct 2026", "action": "delete", "table_id": "900"}, ctx)
    assert gs.tables
    approve(bz, "Delete table?")
    assert gs.tables == []


def test_older_versions_copy_and_restore(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    gs.revs = [{"id": "11", "modifiedTime": "2026-11-20T10:00:00Z", "lastModifyingUser": {"displayName": "Asha"},
                "exportLinks": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "https://export.example/x"}}]
    out = run("sheet_versions", {"spreadsheet": "Sales Oct 2026"}, ctx)
    assert out["versions"] == [{"version_id": "11", "saved": "2026-11-20T10:00:00Z", "by": "Asha"}]
    out = run("sheet_versions", {"spreadsheet": "Sales Oct 2026", "action": "copy", "version_id": "11"}, ctx)
    assert out["version_copy"]["id"].startswith("UP") and b"PK-fake-xlsx" in gs.uploads[0]
    assert b"application/vnd.google-apps.spreadsheet" in gs.uploads[0]
    run("sheet_versions", {"spreadsheet": "Sales Oct 2026", "action": "restore", "version_id": "11", "tab": "Customers"}, ctx)
    assert grid(gs)[1][0] == "Sharma Traders"
    approve(bz, "Put the old version back?")
    assert grid(gs)[1][:2] == ["Old Shop", "Goa"]
    with pytest.raises(ToolError):
        run("sheet_versions", {"spreadsheet": "Sales Oct 2026", "action": "copy", "version_id": "99"}, ctx)


def test_apps_script_saved_after_the_card(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    assert run("sheet_script", {"spreadsheet": "Sales Oct 2026"}, ctx)["files"] == []
    code = 'function onOpen() { SpreadsheetApp.getUi().createMenu("Hoola").addItem("Mail", "go").addToUi(); }\n' \
           'function go() { MailApp.sendEmail("a@b.c", "x", "y"); }'
    out = run("sheet_script", {"spreadsheet": "Sales Oct 2026", "action": "write", "code": code}, ctx)
    assert out["needs_approval"] and out["can"] == ["send or read email"] and not gs.scripts
    card = approve(bz, "Save this Apps Script?")
    assert "send or read email" in json.dumps(card)
    files = gs.scripts["script1"]["files"]
    assert {f["name"]: f["type"] for f in files} == {"appsscript": "JSON", "Code": "SERVER_JS"}
    assert gs.scripts["script1"]["parent"] == SID
    out = run("sheet_script", {"spreadsheet": "Sales Oct 2026"}, ctx)
    assert out["script_id"] == "script1" and "onOpen" in next(f for f in out["files"] if f["name"] == "Code")["source"]
    run("sheet_script", {"spreadsheet": "Sales Oct 2026", "action": "write", "code": "function b(){}", "file": "Extra"}, ctx)
    approve(bz, "Save this Apps Script?")
    assert {f["name"] for f in gs.scripts["script1"]["files"]} == {"appsscript", "Code", "Extra"}   # nothing else lost


def test_bigquery_connect_list_remove(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("sheet_bigquery", {"spreadsheet": "Sales Oct 2026", "action": "connect", "project_id": "my-proj",
                                 "table": "bigquery-public-data.samples.shakespeare"}, ctx)
    assert out["source_id"] == "ds1" and out["state"] == "RUNNING"
    assert gs.sources[0]["spec"]["bigQuery"] == {"projectId": "my-proj", "tableSpec": {
        "tableProjectId": "bigquery-public-data", "datasetId": "samples", "tableId": "shakespeare"}}
    with pytest.raises(ToolError):
        run("sheet_bigquery", {"spreadsheet": "Sales Oct 2026", "action": "connect", "project_id": "p",
                               "query": "DELETE FROM x WHERE 1=1"}, ctx)
    assert run("sheet_bigquery", {"spreadsheet": "Sales Oct 2026"}, ctx)["bigquery"][0]["table"] == \
        "bigquery-public-data.samples.shakespeare"
    run("sheet_bigquery", {"spreadsheet": "Sales Oct 2026", "action": "delete", "source_id": "ds1"}, ctx)
    approve(bz, "Remove BigQuery link?")
    assert gs.sources == []


def test_waits_when_google_is_busy(gs):
    gs.busy = 3
    out = run("sheet_query", {"spreadsheet": "Sales Oct 2026", "totals": ["Due"]}, conv_ctx())
    assert out["totals"]["Due"]["sum"] == 5700
    gs.busy = 20
    with pytest.raises(ToolError) as e:
        run("sheet_info", {"spreadsheet": "Sales Oct 2026"}, conv_ctx())
    assert "60 changes a minute" in str(e.value)


def test_big_writes_go_in_parts(gs, monkeypatch):
    from app.sheets import service as ss
    monkeypatch.setattr(ss, "CHUNK_ROWS", 100)
    monkeypatch.setattr(ss, "CHUNK_CELLS", 50)
    ctx = conv_ctx()
    out = run("sheet_append", {"spreadsheet": "Sales Oct 2026", "rows": [[f"S{i}", "Pune", i, "Pending", "Swati"] for i in range(250)]}, ctx)
    assert out["added_rows"] == 250 and out["parts"] == 3 and len(grid(gs)) == 255
    out = run("sheet_write_range", {"spreadsheet": "Sales Oct 2026", "tab": "Notes", "range": "B2",
                                    "values": [[i, i * 2] for i in range(60)]}, ctx)
    assert out["updated_cells"] == 120 and out["parts"] == 3
    notes = gs.books[SID]["tabs"]["Notes"]["grid"]
    assert notes[1][1:3] == [0, 0] and notes[60][1:3] == [59, 118]


def test_registry_cards_and_connectors():
    from app import googlehub, voice
    from app.agent import sheets_tools as st
    from app.agent.tools import FAMILY_OF, HANDLERS, TOOLS
    from app.bazar.connectors.sheets import TITLES
    names = {t["name"] for t in TOOLS}
    for n in ("sheet_cells", "sheet_table", "sheet_versions", "sheet_script", "sheet_bigquery"):
        assert n in names and n in HANDLERS and n in st.SHEETS_LABELS and FAMILY_OF.get(n) == "sheets"
        assert voice.call_route(n) == "kaam"
    for a in ("cells", "pivot_delete", "table_delete", "bq_delete", "version_restore", "script_write"):
        assert a in TITLES
    assert googlehub.BY_KEY["appsscript"]["primary"].endswith("script.projects")
    assert googlehub.BY_KEY["bigquery"]["primary"].endswith("bigquery.readonly")
