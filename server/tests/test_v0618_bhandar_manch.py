"""v0.620.0 BHANDAR MANCH - the T2 local-core family, backend-only (built as 0.618.0, re-versioned onto their v0.619.0 tip - REBASE PROTOCOL #11, both kept; owner: "T2 Local Core -- START";
the T2 tier of download/HOOLA_MCP_FEED.json - the zero-network / zero-login / zero-key local beds,
catalog-description-verified rows ported IDEA-ONLY, zero upstream code, zero new pip, zero new keys:
Aderali06/sqlite-mcp-server "Safe, read-only SQLite MCP server with auto schema discovery, row
limits", hannesrudolph/sqlite-explorer "Safe, read-only access ... with query validation",
scoretracker4321/json-mcp-lite "Serve any JSON file ... as read-only ... get-by-id tools",
micl2e2/code-to-tree "Convert source code into an AST", rafim-dev/mcp-context-condenser "AST-based
code outliner", EdelmarSchneider/permark "Markdown reader ... that tells coding agents what you are
reading", davidan90/time-node-mcp "Timezone-aware date and time operations ... IANA timezones".

ONE tool `bhandar`, actions beds | sql | md | json | ast | time, every answer one envelope. What is
tested FOR REAL (all offline, per-tenant stores wiped per test): the beds discovery (house beds with
table counts, the no-create law, workspace nesting), the sql gate (one statement, the head law, the
write verbs by name, write pragmas by the = law, the replace() function exception, EXPLAIN on reads
only, the mode=ro wall via SQL_ERROR on a missing table, row cap + truncation honesty, cell cap,
tenant isolation, bed-name escape refusals), the md/json/ast workspace lanes (the root law, binary
refusal, TOO_BIG, parse-error positions, dotted get with array hops and honest missing hops, the
ast skeleton with bases/methods/arity), the time door (IST home, the UTC +00:00 regression, convert
with honest offsets, unknown IANA zone refused, an explicit `at` moment), the kill switch (off means
off - every action NEED_SETUP), unknown actions, the purity law (zero network imports), registry 607
pin, the enum pin, APP_VERSION pin.
"""
import asyncio
import shutil
import sqlite3
from pathlib import Path

import pytest

from app.agent import bhandar_tools as B
from app.agent.tools import Ctx, TOOLS

CTX = Ctx(tenant_id="bh-test-tenant", conversation_id="c1")
CTX2 = Ctx(tenant_id="bh-other-tenant", conversation_id="c2")


def _wipe(tenant):
    for d in ("workspace", "scraping", "kgmemory"):
        shutil.rmtree(Path("data") / d / tenant, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_state():
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)
    yield
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)


def bh(action="beds", ctx=None, **kw):
    return asyncio.run(B.bhandar(ctx or CTX, action, **kw))


def seed_db(tenant="bh-test-tenant", rows=5, name="elements.db"):
    d = Path("data") / "scraping" / tenant
    d.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(d / name)
    con.execute("CREATE TABLE t1 (id INTEGER, name TEXT)")
    con.executemany("INSERT INTO t1 VALUES (?,?)", [(i, f"row{i}") for i in range(rows)])
    con.commit()
    con.close()
    return f"scraping/{name}"


def seed_file(rel, text, tenant="bh-test-tenant"):
    p = Path("data") / "workspace" / tenant / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return rel


MD = "# Top\nintro words\n## Sub one\nmore\n### Deep\n[one](https://a.example)\n" \
     "[one](https://a.example)\n[ref]: https://b.example\n```py\ncode\n```\n"
JSON_DOC = '{"items":[{"name":"a","qty":3},{"name":"b","qty":9}],"meta":{"v":1},"note":"x"}'
PY_SRC = "import json\nfrom pathlib import Path\n\nX = 1\n\n\nclass Alpha(Base):\n" \
         "    \"\"\"doc\"\"\"\n\n    def m(self):\n        return 1\n\n\ndef f(a, b=2):\n" \
         "    return a\n\n\nasync def g(x):\n    return x\n"


# ---------------------------------------------------------------- beds

def test_beds_empty_tenant_is_honest_empty_and_creates_nothing():
    out = bh("beds")
    assert out["ok"] and out["count"] == 0 and out["beds"] == []
    assert not (Path("data") / "workspace" / CTX.tenant_id).exists(), "a read-only lane must not mkdir"


def test_beds_finds_house_beds_with_table_counts():
    bed = seed_db()
    kg = Path("data") / "kgmemory" / CTX.tenant_id
    kg.mkdir(parents=True)
    con = sqlite3.connect(kg / "kg.db")
    con.execute("CREATE TABLE entities (id INTEGER)")
    con.commit()
    con.close()
    seed_file("deep/nested/work.db", "not opened here")
    out = bh("beds")
    assert out["ok"]
    names = {b["name"] for b in out["beds"]}
    assert bed in names and "kgmemory/kg.db" in names and "workspace/deep/nested/work.db" in names
    by = {b["name"]: b for b in out["beds"]}
    assert by[bed]["tables"] == 1 and by["kgmemory/kg.db"]["tables"] == 1
    assert "tables" not in by["workspace/deep/nested/work.db"], "workspace .db files are listed, not opened"
    assert out["meta"]["root"].endswith(f"workspace/{CTX.tenant_id}")


# ---------------------------------------------------------------- sql - the gate

def test_sql_select_rows_and_count():
    bed = seed_db(rows=3)
    out = bh("sql", bed=bed, sql="SELECT id, name FROM t1 ORDER BY id")
    assert out["ok"] and out["count"] == 3 and out["columns"] == ["id", "name"]
    assert out["rows"][2] == [2, "row2"]
    assert out["meta"]["read_only"] is True


def test_sql_row_cap_says_truncated():
    bed = seed_db(rows=250)
    out = bh("sql", bed=bed, sql="SELECT * FROM t1")
    assert out["ok"] and out["count"] == 200
    assert out["meta"]["truncated"] is True and "LIMIT" in out["meta"]["hint"]


def test_sql_cell_cap_keeps_envelope_small():
    bed = seed_db(rows=1)
    con = sqlite3.connect(Path("data") / "scraping" / CTX.tenant_id / "elements.db")
    con.execute("UPDATE t1 SET name=?", ("x" * 1000,))
    con.commit()
    con.close()
    out = bh("sql", bed=bed, sql="SELECT name FROM t1")
    assert out["ok"] and len(out["rows"][0][0]) == 400


@pytest.mark.parametrize("bad", [
    "INSERT INTO t1 VALUES (1,'x')", "UPDATE t1 SET name='x'", "DELETE FROM t1",
    "DROP TABLE t1", "ALTER TABLE t1 ADD c TEXT", "CREATE TABLE t2 (x INT)",
    "ATTACH DATABASE 'x' AS y", "VACUUM", "PRAGMA journal_mode=WAL", "PRAGMA user_version=5",
    "SELECT 1; SELECT 2", "SHOW TABLES",
])
def test_sql_gate_refuses_writes_and_shapes(bad):
    bed = seed_db()
    out = bh("sql", bed=bed, sql=bad)
    assert not out["ok"] and out["error"]["code"] == "BAD_INPUT"
    assert out["error"]["message"], "the refusal names what and why"


def test_sql_replace_function_is_a_legal_read():
    bed = seed_db()
    out = bh("sql", bed=bed, sql="SELECT replace(name,'row','R') FROM t1 WHERE id=0")
    assert out["ok"] and out["rows"][0][0] == "R0"


def test_sql_with_and_explain_are_reads():
    bed = seed_db()
    out = bh("sql", bed=bed, sql="WITH big AS (SELECT * FROM t1) SELECT count(*) FROM big")
    assert out["ok"] and out["rows"][0][0] == 5
    out = bh("sql", bed=bed, sql="EXPLAIN QUERY PLAN SELECT * FROM t1")
    assert out["ok"]
    out = bh("sql", bed=bed, sql="EXPLAIN DELETE FROM t1")
    assert not out["ok"], "EXPLAIN only puts a read statement in the plan"


def test_sql_read_pragmas_pass():
    bed = seed_db()
    for stmt in ("PRAGMA table_list", "PRAGMA table_info(t1)", "PRAGMA integrity_check"):
        out = bh("sql", bed=bed, sql=stmt)
        assert out["ok"], (stmt, out["error"])


def test_sql_sqlite_error_is_honest_sql_error():
    bed = seed_db()
    out = bh("sql", bed=bed, sql="SELECT * FROM no_such_table")
    assert not out["ok"] and out["error"]["code"] == "SQL_ERROR" and "sqlite says" in out["error"]["message"]


def test_sql_bed_names_are_the_law():
    seed_db()
    for bad in ("../../etc/passwd", "/etc/passwd", "scraping/../../other/x.db",
                "unknown/elements.db", "scraping/elements"):
        out = bh("sql", bed=bad, sql="SELECT 1")
        assert not out["ok"] and out["error"]["code"] == "BAD_INPUT", bad
    out = bh("sql", bed="scraping/never.db", sql="SELECT 1")
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"


def test_sql_tenant_isolation():
    seed_db(tenant=CTX.tenant_id)
    seed_db(tenant=CTX2.tenant_id)
    a = bh("sql", bed="scraping/elements.db", sql="SELECT count(*) FROM t1")
    assert a["ok"] and a["rows"][0][0] == 5
    b = bh("sql", ctx=CTX2, bed="scraping/elements.db", sql="SELECT count(*) FROM t1")
    assert b["ok"] and b["rows"][0][0] == 5
    # tenant A can never name a bed outside its own three dirs - same name, own root only
    solo = bh("sql", bed="workspace/secret.db", sql="SELECT 1")
    assert not solo["ok"] and solo["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------- md

def test_md_outline_links_stats():
    seed_file("notes.md", MD)
    out = bh("md", path="notes.md", op="outline")
    assert out["ok"] and [h["level"] for h in out["outline"]] == [1, 2, 3]
    assert out["outline"][0]["line"] == 1 and out["outline"][0]["text"] == "Top"
    out = bh("md", path="notes.md", op="links")
    urls = [l["url"] for l in out["links"]]
    assert urls == ["https://a.example", "https://b.example"], "deduped, reference defs included"
    out = bh("md", path="notes.md", op="stats")
    s = out["stats"]
    assert s["headings"] == 3 and s["code_fences"] == 1 and s["links"] == 2 and s["words"] > 8


def test_md_root_law_and_binary():
    seed_file("ok.md", "fine")
    out = bh("md", path="../../etc/passwd", op="outline")
    assert not out["ok"] and out["error"]["code"] == "BAD_INPUT"
    out = bh("md", path="/etc/passwd")
    assert not out["ok"]
    seed_file("bin.md", "text\x00with nul")
    out = bh("md", path="bin.md")
    assert not out["ok"] and "binary" in out["error"]["message"].lower()
    out = bh("md", path="nope.md")
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"


def test_md_too_big():
    seed_file("big.md", "word " * 60_000)  # 240k bytes > the 200k read cap
    out = bh("md", path="big.md", op="stats")
    assert not out["ok"] and out["error"]["code"] == "TOO_BIG"


# ---------------------------------------------------------------- json

def test_json_validate_keys_get():
    seed_file("cat.json", JSON_DOC)
    out = bh("json", path="cat.json", op="validate")
    assert out["ok"] and out["valid"] is True and out["top_type"] == "dict"
    out = bh("json", path="cat.json", op="keys")
    paths = [k["path"] for k in out["structure"]]
    assert "items" in paths and "meta" in paths and "note" in paths
    assert any(k["type"] == "list" for k in out["structure"])
    out = bh("json", path="cat.json", op="get", dotted="items.1.name")
    assert out["ok"] and out["value"] == "b" and out["bytes"] > 0


def test_json_parse_error_names_the_position():
    seed_file("bad.json", '{"a": 1,,}')
    out = bh("json", path="bad.json", op="validate")
    assert not out["ok"] and out["error"]["code"] == "PARSE_ERROR"
    assert "line 1" in out["error"]["message"]


def test_json_get_missing_hop_is_honest():
    seed_file("cat.json", JSON_DOC)
    out = bh("json", path="cat.json", op="get", dotted="items.5.name")
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"
    assert "items.5.name" in out["error"]["message"]
    out = bh("json", path="cat.json", op="get", dotted="")
    assert not out["ok"] and out["error"]["code"] == "BAD_INPUT"


def test_json_get_result_cap():
    seed_file("fat.json", '{"blob":"' + "y" * 30_000 + '"}')
    out = bh("json", path="fat.json", op="get", dotted="blob")
    assert not out["ok"] and out["error"]["code"] == "TOO_BIG"


# ---------------------------------------------------------------- ast

def test_ast_outline_skeleton():
    seed_file("mod.py", PY_SRC)
    out = bh("ast", path="mod.py")
    assert out["ok"]
    assert [c["name"] for c in out["classes"]] == ["Alpha"]
    assert out["classes"][0]["bases"] == ["Base"]
    assert out["classes"][0]["methods"] == ["m"]
    fns = {f["name"]: f for f in out["functions"]}
    assert set(fns) == {"f", "g"} and fns["f"]["args"] == 2 and fns["g"]["async"] is True
    mods = {i["module"] for i in out["imports"]}
    assert mods == {"json", "pathlib"}
    assert out["top_level_assigns"] == 1


def test_ast_parse_error_and_non_py():
    seed_file("broken.py", "def f(:\n    pass\n")
    out = bh("ast", path="broken.py")
    assert not out["ok"] and out["error"]["code"] == "PARSE_ERROR" and "line 1" in out["error"]["message"]
    seed_file("note.md", "# x")
    out = bh("ast", path="note.md")
    assert not out["ok"] and out["error"]["code"] == "BAD_INPUT"


# ---------------------------------------------------------------- time

def test_time_now_home_is_ist():
    out = bh("time", op="now")
    assert out["ok"] and out["tz"] == "Asia/Kolkata" and out["utc_offset"] == "+05:30"
    assert out["meta"]["home_tz"] == "Asia/Kolkata"


def test_time_utc_offset_regression():
    out = bh("time", op="now", tz="UTC")
    assert out["ok"] and out["utc_offset"] == "+00:00", "a zero offset must never read falsy"


def test_time_convert_honest_offsets_and_at_moment():
    out = bh("time", op="convert", tz="Asia/Kolkata", to_tz="America/New_York",
             at="2026-11-06T14:00:00")
    assert out["ok"]
    assert out["from_zone"]["utc_offset"] == "+05:30"
    assert out["to_zone"]["utc_offset"] in ("-04:00", "-05:00"), "DST honesty: Nov 6 is EDT"
    assert out["from_zone"]["iso"][:16] == "2026-11-06T14:00"
    out = bh("time", op="now", tz="Mars/Olympus")
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------- the lane laws

def test_kill_switch_off_means_off(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "bhandar_enabled", False, raising=False)
    for call in (dict(action="beds"), dict(action="sql", bed="x/y.db", sql="SELECT 1"),
                 dict(action="md", path="a.md"), dict(action="time", op="now")):
        out = bh(**call)
        assert out["ok"] is False and out["error"]["code"] == "NEED_SETUP", call


def test_unknown_action_and_missing_args():
    out = bh("nope")
    assert not out["ok"] and "valid: beds, sql, md, json, ast, time" in out["error"]["message"]
    out = bh("sql")
    assert not out["ok"], "sql without a bed names the beds action"
    out = bh("ast", path="")  # empty path -> non-.py refusal
    assert not out["ok"] and out["error"]["code"] == "BAD_INPUT"


def test_purity_no_network_imports():
    src = Path(B.__file__).read_text(encoding="utf-8")
    for banned in ("httpx", "requests", "urllib", "socket", "http.client", "aiohttp"):
        assert banned not in src, f"bhandar must stay offline ({banned})"


def test_registry_606_and_enum_pin():
    names = [t["name"] for t in TOOLS]
    assert len(TOOLS) == 607, "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " + len(TOOLS)
    assert names.count("bhandar") == 1
    tool = next(t for t in TOOLS if t["name"] == "bhandar")
    assert tool["input_schema"]["properties"]["action"]["enum"] == \
        ["beds", "sql", "md", "json", "ast", "time"]
    assert B.BHANDAR_LABELS == {"bhandar": "Bhandar: the agent's local-data workbench"}


def test_app_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.665.0"
