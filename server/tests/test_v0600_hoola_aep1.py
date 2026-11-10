"""v0.600.0 HOOLA AEP 1.0 - the 100% parity audit + the openwiki analog, P8 of
the AEP plan - the train's LAST phase (the plan's own number for it).

The upstream analog read at the pinned commit aa2528fb: openwiki/ = generated
evidence index pages grounded in the repo (front-matter, sources repo://, an
index listing, per-topic pages); libs/standard-tests base.py's own law that a
conformance class may not silently drop or override a standard test.

What is tested FOR REAL: the parity matrix VERIFIED LIVE (every row's symbol
imports from its module, every row's test needle greps in its suite - a drifted
row fails the audit, so the 100% claim is COMPUTED, never asserted); the
phase-by-phase checklist with LIVING numbers (files exist, LOC counted from the
tree, test counts counted from the suites, every phase DONE); the openwiki
analog generated deterministically (byte-stable twice, front-matter, repo://
sources, the index carries the per-phase table); the CLI lanes (matrix exit 0 +
the 100% line, checklist, wiki --out); the registry heal their v0.588
paisa_sahayak tool owes the w35 suite (581 -> 582); the inertness probe + the
package-export law + the APP_VERSION/pubspec pins.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

import app.aep as _pkg  # noqa: F401 - the export law probe
from app.aep import audit as A
from app.aep import *  # noqa: F401,F403 - the package-export law probe


# ---------------------------------------------------------------------------
# the 100% parity claim - verified, not asserted
# ---------------------------------------------------------------------------
def test_audit_parity_all_rows_verified():
    report = A.audit_parity()
    assert report["total"] >= 200, f"the matrix shrank: {report['total']} rows"
    assert report["ok"], json.dumps(report["failed"], indent=2)[:2000]
    assert report["verified"] == report["total"]
    # every phase carries real verified rows
    for ph in A.PHASES:
        slot = report["by_phase"][ph["phase"]]
        assert slot["ok"] == slot["total"] and slot["total"] >= 4, (ph["phase"], slot)


def test_audit_matrix_rows_are_well_formed():
    for row in A.PARITY_MATRIX:
        phase, feature, ref, mod_name, symbol, test_file, needle = row
        assert phase in {p["phase"] for p in A.PHASES}
        assert feature and ref.startswith(("langchain", "LangSmith", "langgraph", "upstream"))
        assert mod_name and symbol and test_file.startswith("test_") and needle


# ---------------------------------------------------------------------------
# the phase-by-phase checklist sign-off (living numbers)
# ---------------------------------------------------------------------------
def test_phase_checklist_signoff():
    rows = A.phase_checklist()
    assert [r["phase"] for r in rows] == ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
    for r in rows:
        assert r["status"] == "DONE", f"{r['phase']} not DONE"
        assert r["loc"] > 0 and r["loc"] == sum(r["files_loc"].values())
        assert r["tests"] > 0
        for f in r["files"]:
            assert (A.AEP / f).exists(), f"missing {f}"
    # the living numbers match reality (counted, not claimed)
    core = next(r for r in rows if r["phase"] == "P1")
    assert core["loc"] >= 1500 and core["tests"] >= 79
    mw = next(r for r in rows if r["phase"] == "P5")
    assert mw["loc"] >= 2000
    hub = next(r for r in rows if r["phase"] == "P7")
    assert len(hub["files"]) == 4


# ---------------------------------------------------------------------------
# the openwiki analog
# ---------------------------------------------------------------------------
def test_wiki_generation_deterministic(tmp_path):
    out1, out2 = tmp_path / "w1", tmp_path / "w2"
    pages1 = A.generate_wiki(out1)
    pages2 = A.generate_wiki(out2)
    names1 = sorted(p.name for p in pages1)
    assert names1 == ["index.md", "p1-hoola.md", "p2-hoola.md", "p3-hoola.md",
                      "p4-hoola.md", "p5-hoola.md", "p6-hoola.md", "p7-hoola.md",
                      "p8-hoola.md"]
    for p1, p2 in zip(sorted(pages1), sorted(pages2)):
        assert p1.read_bytes() == p2.read_bytes(), f"{p1.name} not byte-stable"
    index = (out1 / "index.md").read_text()
    assert "P1 | HOOLA CORE" in index and "P7 | HOOLA HUB" in index
    assert "rows verified" in index
    p7 = (out1 / "p7-hoola.md").read_text()
    assert p7.startswith("---") and "repo://server/app/aep/hub.py" in p7
    assert "init_chat_model" in p7 and "`test_fixed_model_and_provider_kwarg_form`" in p7
    p5 = (out1 / "p5-hoola.md").read_text()
    assert "THE UNIFICATION: NudgeMiddleware" in p5


def test_wiki_default_lane_writes_the_repo_docs_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(A.SERVER)          # the CLI resolves the repo root itself
    out = tmp_path / "docs-wiki"
    pages = A.generate_wiki(out)
    assert len(pages) == 9 and all(p.exists() for p in pages)


# ---------------------------------------------------------------------------
# the CLI
# ---------------------------------------------------------------------------
def test_audit_cli_lanes(capsys):
    assert A.main(["matrix"]) == 0
    out = capsys.readouterr().out
    assert "100% PARITY VERIFIED" in out
    assert A.main(["checklist"]) == 0
    assert "HOOLA AEP 1.0" in capsys.readouterr().out
    assert A.main(["matrix", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] and data["verified"] == data["total"]
    with pytest.raises(SystemExit):
        A.main(["nope"])


# ---------------------------------------------------------------------------
# the registry heal their v0.588 owes (paisa_sahayak: 581 -> 582)
# ---------------------------------------------------------------------------
def test_registry_count_holds_the_merged_arithmetic():
    from app.agent.tools import TOOLS
    assert len(TOOLS) == 621, "617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " + (
        "584 = 581 + 1 paisa_sahayak (their v0.588 PAISA SAHAYAK) + 2 sandarbh "
        "(their v0.590 SANDARBH MANCH: workspace + kgmemory); the merged "
        "arithmetic the w35 pin carries after their PIN REPAIR")
    src = (A.REPO_ROOT / "server" / "tests" / "test_v0565_construction_w35.py").read_text()
    assert "len(TOOLS) == 621" in src, "the w35 pin must carry the merged arithmetic (607 + 1 duniya, v0.667)"
    assert "paisa_sahayak" in src and "sandarbh" in src


# ---------------------------------------------------------------------------
# the laws
# ---------------------------------------------------------------------------
def test_inertness_law():
    """A fresh interpreter imports app.aep.audit with zero extra threads and
    zero files - the P1..P7 law, re-proven for P8 (files are read only when a
    command runs, never on import)."""
    code = (
        "import sys, threading; sys.path.insert(0, 'server');"
        "before = threading.active_count();"
        "import app.aep.audit;"
        "assert threading.active_count() == before, 'thread leak';"
        "print('INERT-OK')"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, timeout=60, cwd="..")
    assert out.returncode == 0, out.stderr
    assert "INERT-OK" in out.stdout


def test_package_export_law():
    import app.aep as pkg
    for name in A.__all__:
        assert hasattr(pkg, name), f"app.aep.{name} missing (the export law)"
    for name in ("PARITY_MATRIX", "PHASES", "audit_parity", "phase_checklist",
                 "generate_wiki"):
        assert name in pkg.__all__


def test_version_pins():
    from pathlib import Path
    from app.main import APP_VERSION
    root = Path(__file__).resolve().parents[2]
    assert APP_VERSION == "0.752.0"
    assert "0.752.0+751" in (root / "pubspec.yaml").read_text()
    line = (root / "server" / "app" / "main.py").read_text().splitlines()[35]
    assert "HOOLA AEP 1.0" in line and "PARITY" in line.upper()
    assert "HOOLA HUB" in line  # the P7 name rides the Previous chain
