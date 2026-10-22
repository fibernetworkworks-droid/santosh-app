"""v0.131 Complex apps: 43 archetypes (CRM, HRMS, field service, inventory, POS, logistics, ISP / FTTH ops, hospital, school
ERP, GIS survey, IoT ...), 115 pro screen types, the blueprint under the screens (data model with RLS + sync columns,
org levels, roles x permission matrix, approval chain, login plan, phone features with Play / App Store status), schema files
checked in SQLite (the phone) and PostgreSQL (real server when installed), ER page, changes in her words without redrawing."""
import os
import re
import shutil
import sqlite3
import subprocess
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v128_appdesign import FakeAI, T


def test_catalogue_blueprint_rules():
    from app.appmaker import auth as AU
    from app.appmaker import blueprint as BP
    from app.appmaker import capabilities as CP
    from app.appmaker import library as L
    from app.appmaker import orgmodel as OM
    from app.appmaker import taxonomy as TX
    assert TX.check() == [] and BP.check() == []
    c = L.counts()
    assert c["archetypes"] == 43 and c["pro_screen_types"] == 115 and c["screen_types"] == 172 and c["briefs"] == 160000
    assert c["pro_briefs"] > 50000 and c["all_briefs"] == c["briefs"] + c["pro_briefs"]
    assert c["capabilities"] >= 60 and c["play_restricted"] >= 8 and c["login_methods"] >= 15 and c["entities"] >= 140
    # her words -> the right archetype and a trade that fits it
    for q, goal in [("CRM app banao", "crm"), ("school ERP chahiye", "school_erp"), ("ftth isp app for my fiber network", "isp_ops"),
                    ("delivery boy app for my courier", "delivery_driver"), ("security guard patrol app", "security_guard"),
                    ("GIS survey app with offline maps", "gis_survey"), ("kirana ki app ghar pe delivery", "shop")]:
        u = L.understand(q)
        assert u["goal"] == goal and u["field"], q
        if goal in TX.COMPLEX_GOALS:
            assert TX.GOALS[goal]["industries"] and u["styles"][0] in TX.GOALS[goal]["styles"]
    # restricted phone features are flagged with the allowed alternative, never promised
    asked = CP.from_words("sms padhna chahiye, call log, saari files, background location, fingerprint")
    assert {"sms_read", "call_log", "all_files", "location_background", "biometrics"} <= set(asked)
    chk = CP.check(asked)
    bad = {p["id"]: p["alt"] for p in chk["problems"]}
    assert bad == {"sms_read": "sms_retriever", "call_log": "call_dialer", "all_files": "files_saf"}
    assert "READ_SMS" not in chk["permissions"] and "READ_CALL_LOG" not in chk["permissions"]
    assert any(n["id"] == "location_background" for n in chk["notes"])          # Play declaration, said plainly
    use = CP.usable(asked)
    assert "sms_read" not in use and "sms_retriever" in use and "files_saf" in use
    assert CP.CAPS["exact_alarm"]["play"] == "hoola_never" and CP.CAPS["battery_exempt"]["play"] == "hoola_never"
    # login: Google needs Apple on iPhone; staff / money apps get unlock + admin second step
    lp = AU.plan(["google"], money=True, staff=False, sensitive=False)
    assert "apple" in lp["ids"] and "biometric_unlock" in lp["ids"] and "totp_mfa" in lp["ids"] and lp["warnings"]
    assert any("Delete account" in r for r in lp["rules"]) and lp["policy"]["otp_minutes"] == 5
    # org: levels <= 8, customers see only their own, auditors only read, maker-checker rule
    org = OM.build("isp", ["admin", "noc", "manager", "field", "customer", "auditor"], ["isp", "service", "sales"], True)
    assert org["problems"] == [] and org["levels"][0] == "Company" and len(org["levels"]) <= 8
    m = org["matrix"]
    assert m["customer"]["service"]["read"] == "own" and m["customer"]["isp"]["read"] == "none"
    assert all(m["auditor"][mod][a] == "none" for mod in ("isp", "service", "sales") for a in ("create", "update", "delete", "approve"))
    assert m["noc"]["isp"]["read"] == "all" and m["field"]["sales"]["approve"] == "none"
    assert org["approvals"][0]["upto"] == 10000 and any("Maker-checker" in r for r in org["rules"])
    o2, done = OM.change(org, {"levels": ["Company", "Circle", "Zone", "POP", "Cluster", "Street", "Building", "Floor", "Flat"],
                               "add_roles": [{"name": "Store keeper", "like": "staff"}], "remove_roles": ["super_admin", "noc"],
                               "matrix": [{"role": "field", "module": "sales", "action": "export", "scope": "own"}]})
    assert len(o2["levels"]) == 8 and "store_keeper" in o2["roles"] and "super_admin" in o2["roles"] and "noc" not in o2["roles"]
    assert o2["matrix"]["field"]["sales"]["export"] == "own" and o2["problems"] == [] and "store_keeper" not in OM.ROLES
    # a blueprint for every archetype validates; simple apps get one too
    bp = BP.make("isp_ops", TX.GOALS["isp_ops"]["screens"], "sms padhna bhi chahiye")
    v = BP.view(bp)
    assert v["data"]["tables"] > 50 and "subscriber" in v["tables"]["isp"] and "ont" in v["tables"]["isp"]
    assert any(p["id"] == "sms_read" for p in v["cap_problems"]) and "Store nahi dete" in BP.say(bp)
    assert BP.make("shop", TX.GOALS["shop"]["screens"])["data"]["tables"] > 20


def test_datamodel_sqlite_postgres(tmp_path):
    from app.appmaker import datamodel as DM
    m = DM.build(list(DM.MODULES))
    assert m["problems"] == [] and len(m["tables"]) >= 140
    t = m["tables"]
    cols = {c["name"] for c in t["ticket"]["columns"]}
    assert {"id", "tenant_id", "org_unit_id", "created_at", "updated_at", "deleted_at", "version", "customer_id"} <= cols
    assert t["audit_log"]["append_only"] and "updated_at" not in {c["name"] for c in t["audit_log"]["columns"]}
    emp = {c["name"] for c in t["employee"]["columns"]}
    assert "pan_enc" in emp and "pan_last4" in emp and "pan" not in emp and t["employee"]["sensitive"]
    # the phone's database: SQLite runs it, FKs hold
    db = sqlite3.connect(":memory:")
    db.executescript(DM.ddl_sqlite(m))
    ten = str(uuid.uuid4())
    db.execute("INSERT INTO org_unit (id, tenant_id, name, level) VALUES ('u1', ?, 'HQ', 0)", (ten,))
    db.execute("INSERT INTO app_user (id, tenant_id, name, org_unit_id, status) VALUES ('a1', ?, 'Asha', 'u1', 'active')", (ten,))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO app_user (id, tenant_id, name, org_unit_id, status) VALUES ('a2', ?, 'X', 'nope', 'active')", (ten,))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO app_user (id, tenant_id, name, org_unit_id, status) VALUES ('a3', ?, 'X', 'u1', 'bogus')", (ten,))
    # Room entities + Mermaid + ER page
    kt = DM.room_kotlin(m)
    assert '@Entity(tableName = "ticket"' in kt and "data class WorkOrder(" in kt
    mm = DM.mermaid(m)
    assert mm.startswith("erDiagram") and "customer ||--o{ ticket : customer_id" in mm
    er = DM.er_html(m, "Test")
    assert "<script" not in er and "subscriber" in er
    # custom table + field in her words
    x, done = DM.change({}, {"add_entities": [{"name": "fiber_closure", "label": "Joint closure",
                                               "fields": "code text!*, feature ref(feature), cores int, photo file"}],
                             "add_fields": [{"entity": "supplier", "fields": "pan_no text"}]})
    m2 = DM.build(["isp", "gis", "purchase"], x)
    assert m2["problems"] == [] and "fiber_closure" in m2["tables"] and "pan_no" in {c["name"] for c in m2["tables"]["supplier"]["columns"]}
    # PostgreSQL: the PostGIS schema parses; without PostGIS it runs in a real server with RLS + triggers working
    pg_sql = DM.ddl_postgres(m, "postgis")
    assert "ENABLE ROW LEVEL SECURITY" in pg_sql and "geography(Point,4326)" in pg_sql and "gen_random_uuid()" in pg_sql
    try:
        import pglast
        assert len(pglast.parse_sql(pg_sql)) > 1000
    except ImportError:
        pass
    _real_postgres(tmp_path, DM.ddl_postgres(m, "plain"))


def _real_postgres(tmp_path, sql):
    bindir = next((p for p in sorted(Path("/usr/lib/postgresql").glob("*/bin"), reverse=True)), None) if Path("/usr/lib/postgresql").exists() else None
    if not bindir or not shutil.which("psql") or not shutil.which("runuser"):
        return
    base = Path(f"/tmp/hoola_pg_{uuid.uuid4().hex[:8]}")
    try:
        (base / "data").mkdir(parents=True)
        shutil.chown(base, "postgres")
        shutil.chown(base / "data", "postgres")
        run = lambda *a: subprocess.run(["runuser", "-u", "postgres", "--", *a], capture_output=True, text=True, timeout=120)  # noqa: E731
        if run(str(bindir / "initdb"), "-D", str(base / "data"), "-A", "trust", "-U", "pg").returncode:
            return
        port = str(56000 + int(uuid.uuid4().int % 900))
        if run(str(bindir / "pg_ctl"), "-D", str(base / "data"), "-o", f"-k {base} -p {port} -c listen_addresses=", "-l",
               str(base / "log"), "-w", "start").returncode:
            return
        (base / "s.sql").write_text(sql)
        (base / "t.sql").write_text("""CREATE ROLE app_api LOGIN;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_api;
SET ROLE app_api;
BEGIN; SET LOCAL app.tenant = '11111111-1111-1111-1111-111111111111'; SET LOCAL app.all_units = 'on';
INSERT INTO org_unit (id, tenant_id, name, level) VALUES ('aaaaaaaa-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'HQ', 0);
INSERT INTO app_user (tenant_id, name, org_unit_id, status) VALUES ('11111111-1111-1111-1111-111111111111', 'Asha', 'aaaaaaaa-0000-0000-0000-000000000001', 'active');
UPDATE app_user SET name = 'Asha P';
SELECT 'v=' || version FROM app_user; COMMIT;
BEGIN; SET LOCAL app.tenant = '22222222-2222-2222-2222-222222222222'; SELECT 'other=' || count(*) FROM app_user; COMMIT;
BEGIN; SET LOCAL app.tenant = '11111111-1111-1111-1111-111111111111'; SET LOCAL app.units = '33333333-3333-3333-3333-333333333333';
SELECT 'unit=' || count(*) FROM app_user; COMMIT;
""")
        for f in ("s.sql", "t.sql"):
            os.chmod(base / f, 0o644)
        r = subprocess.run(["psql", "-h", str(base), "-p", port, "-U", "pg", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-q",
                            "-f", str(base / "s.sql")], capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr[-2000:]
        r = subprocess.run(["psql", "-h", str(base), "-p", port, "-U", "pg", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-At",
                            "-f", str(base / "t.sql")], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr[-2000:]
        out = r.stdout
        assert "v=2" in out and "other=0" in out and "unit=0" in out, out          # version trigger + tenant + unit isolation
        r = subprocess.run(["psql", "-h", str(base), "-p", port, "-U", "pg", "-d", "postgres", "-c",
                            "INSERT INTO audit_log (tenant_id, action, entity) VALUES (gen_random_uuid(), 'a', 'b'); "
                            "UPDATE audit_log SET action = 'z';"], capture_output=True, text=True, timeout=60)
        assert "append-only" in r.stderr
    finally:
        subprocess.run(["runuser", "-u", "postgres", "--", str(bindir / "pg_ctl"), "-D", str(base / "data"), "-m", "immediate", "stop"],
                       capture_output=True, timeout=60)
        shutil.rmtree(base, ignore_errors=True)


class ProFake(FakeAI):
    """Real screens without a cart link (staff apps have no cart)."""
    def __call__(self, system, prompt, max_tokens=7000):
        out = super().__call__(system, prompt, max_tokens)
        if out.get("html"):
            ids = re.search(r"SCREEN IDS you may link(?: with data-go)?: ([^\n]+?)\.?\n", prompt)
            ids = [x.strip() for x in ids.group(1).split(",")] if ids else []
            if "cart" not in ids and ids:
                out["html"] = out["html"].replace('data-go="cart"', f'data-go="{ids[0]}"')
            self.prompts = getattr(self, "prompts", []) + [prompt]
        return out


@pytest.fixture
def pro_env(env, monkeypatch, tmp_path):
    pytest.importorskip("playwright")
    monkeypatch.setenv("APP_DIR", str(tmp_path / "apps"))
    monkeypatch.setenv("APP_WORKER", "false")
    monkeypatch.setenv("APP_FONTS_FETCH", "false")
    monkeypatch.setenv("APP_FONTS_DIR", str(tmp_path / "fonts"))
    from app.appmaker import ai as AI
    fake = ProFake()
    monkeypatch.setattr(AI, "ask_json", fake)
    monkeypatch.setattr(AI, "ask_edit", fake)
    return fake


def test_complex_app_end_to_end(pro_env):
    from app.agent import app_tools as A
    from app.appmaker import service as S
    from app.main import app
    c = TestClient(app)
    ctx = conv_ctx()
    v = S.new(T, "delivery boy app for my courier, riders ko sms padhne ki permission bhi chahiye", ctx.conversation_id,
              name="Speedy Couriers", answers={"phone": "9876543210", "address": "Wakad, Pune", "upi_id": "speedy@upi"})
    assert v["goal"] == "delivery_driver" and v["plan"]["complex"]
    bpv = v["plan"]["blueprint"]
    assert bpv["archetype"] == "Delivery driver app" and bpv["data"]["tables"] > 20 and "trip" in bpv["tables"]["logistics"]
    assert any(p["id"] == "sms_read" for p in bpv["cap_problems"]) and "sms_retriever" not in [c["id"] for c in bpv["cap_problems"]]
    assert [r["id"] for r in bpv["roles"]][:1] == ["super_admin"] and "Store nahi dete" in v["say"]
    assert "seller_info" not in [x["id"] for x in v["plan"]["code_screens"]]          # staff app: no e-commerce seller page
    S.approve_plan(T, v["id"], ctx.conversation_id, drop=["fuel_log"])
    v = S.choose_look(T, v["id"], 0, None, ctx.conversation_id)
    v = S.get(T, v["id"])
    assert v["status"] == "ready", v.get("error")
    assert v["checks"]["passed"], v["checks"]["blocking"][:4]
    assert any("STAFF / ADMIN APP" in p and "Roles:" in p for p in pro_env.prompts)
    # blueprint files in the prototype + ER picture + API
    tok = v["preview"].rstrip("/").split("/")[-1]
    er = c.get(f"/api/app-preview/{tok}/blueprint/er.html")
    assert er.status_code == 200 and "trip" in er.text
    assert v["board"]["er"] == "er.jpg" and c.get(f"/api/apps/{v['id']}/shots/er.jpg").status_code == 200
    b = c.get(f"/api/apps/{v['id']}/blueprint").json()
    assert b["blueprint"]["data"]["tables"] > 20 and b["files"]["schema.sql"].endswith("schema.sql")
    sql = c.get(f"/api/apps/{v['id']}/blueprint/schema.sql")
    assert sql.status_code == 200 and "CREATE TABLE trip" in sql.text
    assert c.get(f"/api/apps/{v['id']}/blueprint/passwd").status_code == 404
    spec = S.spec(T, v["id"])
    assert spec["blueprint"]["login"] and spec["blueprint"]["files"]
    h1 = v["hash"]
    # roles / login / data in her words: nothing redrawn, new version, new hash
    pro_env.change = {"say": "Store keeper role aur passkey login jod diya",
                      "blueprint": {"add_roles": [{"name": "Store keeper", "like": "staff"}], "login": {"add": ["passkey"]},
                                    "add_fields": [{"entity": "delivery", "fields": "cod_mode enum(cash,upi)"}]}}
    n0 = len([x for x in pro_env.calls if x[0] == "screen"])
    S.change(T, v["id"], "store keeper role add karo, passkey se login bhi, delivery mein COD mode", ctx.conversation_id)
    v2 = S.get(T, v["id"])
    assert [x for x in pro_env.calls[n0:] if x[0] == "screen"] == []
    bp2 = v2["plan"]["blueprint"]
    assert v2["version"] == 2 and "store_keeper" in [r["id"] for r in bp2["roles"]] and "passkey" in [m["id"] for m in bp2["login"]]
    assert v2["hash"] != h1
    sql2 = c.get(f"/api/apps/{v['id']}/blueprint/schema.sql").text
    assert "cod_mode" in sql2
    # approve freezes screens + blueprint together
    ok = S.approve(T, v["id"], v2["hash"])
    assert ok["status"] == "approved"
    # catalogue API + agent reads
    assert len(c.get("/api/apps-catalog/archetypes").json()["archetypes"]) == 43
    caps = c.get("/api/apps-catalog/capabilities?q=sms").json()["capabilities"]
    assert {x["id"] for x in caps} >= {"sms_read", "sms_retriever"}
    assert c.get("/api/apps-catalog/nope").status_code == 404

    class _C:
        tenant_id = T
        actor = "owner"
    assert A._read(_C(), "blueprint", {"app": v["id"]})["blueprint"]["data"]["tables"] > 20
    assert "CREATE TABLE" in A._read(_C(), "schema", {"app": v["id"]})["schema_sql"]
    assert len(A._read(_C(), "archetypes", {})["archetypes"]) == 43
