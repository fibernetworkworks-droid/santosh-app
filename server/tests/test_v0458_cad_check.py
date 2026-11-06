"""IS THE CAD ENGINEER ALIVE ON THIS SERVER? Every other desk can be asked that from the VPS; the CAD desk could
only say whether three libraries imported, and an importable library is not a working desk. `python -m app.engineering
check` builds real parts in the box and reports each stage live / DEAD with the number it measured.

It exists because this already bit her once: every test here was green while her own server answered `fea false`.
These tests pin the things that would make the check itself lie - its own build scripts being illegal for the box
or calling an API that has moved (two of the three failures on its first run were exactly that), a soft library
being treated as fatal, and the verdict going quiet when a real stage is dead.
"""
import pytest

cq = pytest.importorskip("cadquery")


def test_every_library_the_desk_needs_is_named_with_what_dies_without_it():
    from app.engineering import selfcheck
    rows = selfcheck.libs()
    names = {r["lib"] for r in rows}
    assert {"cadquery", "skfem", "mujoco", "matplotlib", "reportlab", "pyamg", "numpy", "scipy"} <= names
    assert all(r["why"] and len(r["why"]) > 15 for r in rows)          # each says what she loses, not just a name
    soft = {r["lib"] for r in rows if r["soft"]}
    assert soft == {"pyamg", "mujoco", "matplotlib"}                   # these degrade quietly; the rest stop the build
    assert "cadquery" not in soft and "skfem" not in soft
    assert all(isinstance(r["ok"], bool) for r in rows)


def test_the_checks_own_scripts_are_legal_for_the_box():
    """The guard is what a real job's script must pass. If the check's scripts cannot pass it, the check is lying."""
    from app.engineering import guard, selfcheck
    for name in ("PART", "GEARS", "MACHINE"):
        code = getattr(selfcheck, name)
        guard.check(code)                                              # raises if the box would refuse it


def test_the_part_script_really_builds_through_the_real_sandbox(tmp_path):
    """The first run of this check reported DEAD because its own script called H.hole the wrong way. This is the
    test that catches that in CI instead of on her server."""
    from app.engineering import sandbox, selfcheck
    r = sandbox.run(tmp_path / "p", selfcheck.PART, timeout=420, material="aluminium")
    assert r.get("ok"), r.get("errors")
    bb = r.get("bbox") or {}
    assert (bb.get("x"), bb.get("y"), bb.get("z")) == (120.0, 60.0, 14.0)
    assert all(e.get("ok") for e in r.get("expect") or []), r.get("expect")   # H.expect must pass, not just answer
    assert {"part.step", "part.stl", "part.glb"} <= set(r.get("exported") or [])
    assert (r.get("dfm") or {}).get("rows") and (tmp_path / "p" / "drawing.json").exists()
    assert r.get("cam") and r["cam"][0]["ops"] == ["profile", "drill"]   # the studies are fed in separately


def test_every_hand_calculation_answers_with_its_real_key():
    """The other two false alarms on the first run were key names that had moved. These are the real ones."""
    from app.engineering import selfcheck
    rows = selfcheck._calc_rows()
    assert len(rows) == 1 and rows[0]["ok"] is True, rows
    assert "9/9 answered" in rows[0]["say"] and "FAILING" not in rows[0]["say"]


def test_the_wiring_rows_catch_an_unreachable_desk_and_a_stale_guide():
    from app.engineering import selfcheck
    rows = selfcheck._wiring_rows()
    assert len(rows) == 2 and all(r["ok"] for r in rows), rows
    assert "registered" in rows[0]["say"] and "markers present" in rows[1]["say"]


def test_the_verdict_tells_dead_from_merely_degraded():
    from app.engineering import selfcheck
    hard_dead = [{"stage": "stress", "ok": False, "soft": False, "say": "x"},
                 {"stage": "a", "ok": True, "soft": False, "say": "y"}]
    v = selfcheck.verdict(hard_dead)
    assert v["ok"] is False and v["dead"] == 1 and v["dead_stages"] == ["stress"]
    soft_only = [{"stage": "charts", "ok": False, "soft": True, "say": "x"},
                 {"stage": "a", "ok": True, "soft": False, "say": "y"},
                 {"stage": "b", "ok": None, "soft": False, "say": "skipped"}]
    v2 = selfcheck.verdict(soft_only)
    assert v2["ok"] is True and v2["degraded"] == 1 and v2["skipped"] == 1 and v2["live"] == 1
    assert v2["degraded_stages"] == ["charts"]


def test_the_report_shouts_only_when_something_real_is_dead(monkeypatch):
    from app.engineering import selfcheck
    monkeypatch.setattr(selfcheck, "check", lambda quick=False: [
        {"stage": "stress (FEA static)", "ok": False, "soft": False, "say": "scikit-fem is MISSING"}])
    out = "\n".join(selfcheck.report_lines())
    assert "[DEAD] stress (FEA static)" in out and "GADBAD" in out and "cad_setup" in out
    monkeypatch.setattr(selfcheck, "check", lambda quick=False: [
        {"stage": "charts in the report", "ok": False, "soft": True, "say": "matplotlib is MISSING"}])
    out2 = "\n".join(selfcheck.report_lines())
    assert "[WEAK]" in out2 and "GADBAD" not in out2 and "degraded" in out2
    monkeypatch.setattr(selfcheck, "check", lambda quick=False: [
        {"stage": "all of it", "ok": True, "soft": False, "say": "ran"}])
    assert "Sab live" in "\n".join(selfcheck.report_lines())


def test_health_names_every_library_and_the_quiet_losses():
    from app.engineering import service
    h = service.health()
    for k in ("cadquery", "fea", "fast_solver", "motion", "charts", "drawing", "libraries", "missing", "ok",
              "quiet_losses"):
        assert k in h, k
    assert h["cadquery"] is True and h["libraries"]["cadquery"] is True
    assert isinstance(h["missing"], list) and isinstance(h["quiet_losses"], list)
    assert all(m in h["libraries"] for m in h["missing"])


def test_the_desk_route_carries_the_health(env):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/eng/projects")
    assert r.status_code == 200
    assert "health" in r.json() and "cadquery" in r.json()["health"]


def test_the_command_line_and_the_vps_job_exist():
    import subprocess
    import sys
    from pathlib import Path
    r = subprocess.run([sys.executable, "-m", "app.engineering", "libs"], capture_output=True, text=True,
                       timeout=300, cwd=str(Path(__file__).resolve().parents[1]))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "cadquery" in r.stdout and "skfem" in r.stdout
    wf = (Path(__file__).resolve().parents[2] / ".github/workflows/vps-ops.yml").read_text(encoding="utf-8")
    assert "          - cad_check" in wf and "          - cad_setup" in wf
    assert "cad_check)" in wf and "cad_setup)" in wf
    assert "python -m app.engineering check" in wf and "scikit-fem" in wf and "mujoco" in wf
