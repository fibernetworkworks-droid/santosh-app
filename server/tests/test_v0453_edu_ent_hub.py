"""v0.453 EDUCATION, RESEARCH & LAB + ENTERPRISE in the AI Employees hub (owner: "YES INCLUDE ALL -- EVEN LAB PUT IT
UNDER EDUCATION & RESEARCH & LAB").

The Shiksha suite (tutor, school office, curriculum, research, register) and Prayogshala were live on the server and the
phone but missing from the hub; so were the ten Enterprise Systems & ERP jobs. They join as two departments. Hiring one
adds its desk - it must NEVER start gating the tools, which every user already had."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
EMP = (CON / "employees.js").read_text(encoding="utf-8")
V2 = (CON / "v2.js").read_text(encoding="utf-8")
HTML = (CON / "v2.html").read_text(encoding="utf-8")
CSS = (CON / "v2.css").read_text(encoding="utf-8")
PHONE = (ROOT / "lib" / "ui" / "employees_screen.dart").read_text(encoding="utf-8")

EDU = {"tutor", "school_office", "curriculum", "research", "school_register", "lab"}


def _cat():
    from app.employee import hire
    return hire


def test_two_new_departments_all_live_and_complete():
    hire = _cat()
    from app.enterprise import rules as R
    edu = {k for k, v in hire.CATALOG.items() if v.get("group") == hire.EDU_GROUP}
    ent = {k for k, v in hire.CATALOG.items() if v.get("group") == hire.ENT_GROUP}
    assert hire.EDU_GROUP == "Education, Research & Lab" and edu == EDU
    assert ent == set(R.ROLES)                                     # the hub follows the enterprise engine's own table
    for k in edu | ent:
        c = hire.CATALOG[k]
        assert c["live"] is True and c["name"] and c["pitch"], k
        for f in ("does", "needs", "never"):
            assert isinstance(c[f], list) and c[f] and all(isinstance(x, str) and x for x in c[f]), (k, f)
    assert "Prayogshala" in hire.CATALOG["lab"]["name"]              # the lab sits under Education, Research & Lab


def test_hub_text_is_english():
    hire = _cat()
    hinglish = re.compile(r"\b(aapki|aapke|nahi|kaam|sirf|bachche|haan|karta|hai)\b", re.I)
    for k, c in hire.CATALOG.items():
        if c.get("group") in (hire.EDU_GROUP, hire.ENT_GROUP):
            text = " ".join([c["name"], c["pitch"], *c["does"], *c["needs"], *c["never"]])
            assert not hinglish.search(text), (k, hinglish.search(text).group(0))


def test_capped_roles_say_their_cap_in_never():
    hire = _cat()
    assert any("money" in x.lower() for x in hire.CATALOG["bank_int"]["never"])
    assert any("patient" in x.lower() for x in hire.CATALOG["health_int"]["never"])
    assert any("you file" in x.lower() for x in hire.CATALOG["regtech"]["never"])


def test_hire_pause_leave_through_the_api(env):
    from app.main import app
    c = TestClient(app)
    for key in ("tutor", "lab", "erp"):
        assert c.post(f"/api/employees/{key}/hire", json={"trust": "seekh"}).status_code == 200
    hired = c.get("/api/employees").json()["hired"]
    assert hired.get("tutor") == "hired" and hired.get("lab") == "hired" and hired.get("erp") == "hired"
    assert c.post("/api/employees/tutor/pause").status_code == 200
    assert c.post("/api/employees/erp/leave").status_code == 200
    groups = {e["group"] for e in c.get("/api/employees").json()["employees"]}
    assert {"Education, Research & Lab", "Enterprise Systems & ERP"} <= groups


def test_tools_stay_open_without_a_hire(env):
    """Every user had these before v0.453; hiring adds the desk only."""
    hire = _cat()
    assert hire.EDU_OPEN is True
    agent = ROOT / "server" / "app" / "agent"
    for f in ("guru_tools.py", "daftar_tools.py", "shiksha_tools.py", "shodh_tools.py", "prayog_tools.py", "enterprise_tools.py"):
        assert "is_hired" not in (agent / f).read_text(encoding="utf-8"), f
    from app.main import app
    c = TestClient(app)
    for p in ("/api/guru", "/api/daftar", "/api/pathyakram", "/api/shodh", "/api/shiksha", "/api/prayog/labs"):
        assert c.get(p).status_code == 200, p


def test_console_hub_departments_and_desks():
    assert "{g: 'Education, Research & Lab', id: 'edu'" in EMP and "{g: 'Enterprise Systems & ERP', id: 'ent'" in EMP
    assert "    edu: '<path" in EMP and "    ent: '<rect" in EMP
    for k in EDU:
        assert f"{k}: 'edudesk'" in EMP, k
    from app.enterprise import rules as R
    for k in R.ROLES:
        assert f"{k}: 'systems'" in EMP, k
    assert "openView(v, v === 'systems' ? key : '')" in EMP              # Open desk lands on that enterprise role
    for d in ("edu", "ent"):
        assert CSS.count(f"#hire .ae-d-{d}{{") == 3, d                    # light + both dark selectors


def test_console_education_desk():
    assert "return {hub, desk, social, cad, game, arch, edu, leads};" in EMP
    for route in ("/api/guru", "/api/daftar", "/api/pathyakram", "/api/shodh", "/api/shiksha", "/api/prayog/labs"):
        assert f"get('{route}')" in EMP, route
    assert "/shares/${encodeURIComponent(b.dataset.id)}/decide`, {yes, hash: b.dataset.hash}" in EMP   # her tap, card hash
    assert "openView('lab', b.dataset.edlab)" in EMP and "say(b.dataset.edask)" in EMP
    assert "const EDU_KEYS = ['tutor', 'school_office', 'curriculum', 'research', 'school_register', 'lab'];" in V2
    assert "['edu', 'edudesk', 'Education Desk']" in V2 and "if (v === 'edudesk') EMP?.edu($('#edudesk'));" in V2
    assert "ENT?.open($('#systems'), arg || 'erp')" in V2 and "'/static/prayog/lab.html?id=' + encodeURIComponent(arg)" in V2
    assert 'id="v-edudesk"' in HTML and 'id="edudesk"' in HTML
    blk = CSS[CSS.index("v0.453 EDUCATION DESK"):]
    assert "grid-auto-rows:1fr" in blk                                   # equal tiles, like the hub
    assert not re.search(r"font-weight:\s*(700|800|900)|font:\s*(700|800|900)\s", blk)
    assert not re.search(r"font(-size)?:[^;}]*\b(9|10|11)(\.\d+)?px", blk)
    assert "infinite" not in blk and not re.search(r"animation:[^;}]*\b(both|forwards)\b", blk)
    assert not re.search(r"font:[^;}]*var\(--fs\)", blk)   # --fs is a SIZE; as a family it voids the whole font line


def test_education_desk_escapes_server_text():
    i = EMP.index("async function edu(el)")
    body = EMP[i:EMP.index("\n  }\n", i)]
    for raw in ("${x.title}", "${x.question}", "${w.what}", "${x.aim}", "${x.link}"):
        assert raw not in body, raw


def test_phone_opens_each_employee_on_its_own_screen():
    hire = _cat()
    i = PHONE.index("Widget _deskFor(String key)")
    fn = PHONE[i:PHONE.index("\n  }\n", i)]
    for k in EDU:
        assert f"'{k}'" in fn, k
    games = set(re.findall(r"'([a-z_]+)'", PHONE[PHONE.index("_gameKeys = {"):PHONE.index("};", PHONE.index("_gameKeys = {"))]))
    ents = set(re.findall(r"'([a-z_]+)'", PHONE[PHONE.index("_entKeys = {"):PHONE.index("};", PHONE.index("_entKeys = {"))]))
    assert games == {k for k, v in hire.CATALOG.items() if v.get("group") == hire.GAME_GROUP}
    assert ents == {k for k, v in hire.CATALOG.items() if v.get("group") == hire.ENT_GROUP}
    assert "EnterpriseScreen(app: app, role: key)" in fn
    for imp in ("guru_screen.dart", "daftar_screen.dart", "shiksha_screen.dart", "shodh_screen.dart", "prayog_screen.dart",
                "enterprise_screen.dart"):
        assert f"import '{imp}';" in PHONE, imp
