"""v0.488.0 HOOLA UIUX PRO MAX - the design database fed to HOOLA (owner:
"https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git ---- READ THIS REPO ---
AND FEED THIS SKILL TO HOOLA AI").

What this suite pins, piece by piece:
(1) VENDOR: the MIT engine sits verbatim under coder/uiux/ (4 scripts, the 12 domain
    CSVs + ui-reasoning.csv, 22 stack CSVs, LICENSE + PROVENANCE) and RUNS on a bare
    subprocess: design-system mode, a domain search, a stack search, and the honest
    0-result answer (upstream's contract: never fabricated).
(2) TOOL: ONE uiux_design tool in the agent table (schema/handler/label); gated by
    coder_enabled + coder_uiux; blocking work in asyncio.to_thread; query capped at
    400 chars, output capped at 24k; unknown domain/stack refused honestly; persist
    writes ONLY under the tenant's vault dir and NEVER overwrites a MASTER.md
    (--force is not a thing the tool can pass - the owner's design decisions stay).
(3) SEED: skillpack/uiux-pro-max.md passes the store's own lint (name/desc/body
    caps), the seed library is now 59 across four lanes (11 starters + 31 byox +
    15 superpowers + 2 prog, v0.499), it feeds create-if-missing like the rest, and a design
    ask SURFACES it through the normal injection (shown marked).
(4) VERSION: APP_VERSION 0.513.0 + the story, pubspec 0.542.0+565 (re-versioned six
    times while this sat local-only: BYOX pair 0.486.0+0.487.0, CRAWL JOBS 0.488.0,
    POWERTOYS RUN + WEB EXTENSION 0.489.0+0.490.0, crawl reland + BYOX FEED + FLUTTER
    PASS 0.491.0+0.492.0+0.493.0, EQUAL POWER took 0.494.0 and our UIUX moved 0.495.0
    on their same-base rebase - the TWENTY-FIRST COLLISION, then OFFICE HOURS took
    0.495.0 + CODE GRAPH took 0.496.0 and this tree moved 0.497.0 -> 0.500.0 - the
    TWENTY-SECOND COLLISION, local-only yields).
"""
import asyncio
import os
import subprocess

import pytest

from app.coder import inject, skill_packs, skills_store, store
from app.coder.skills_store import parse_skill, validate
from app.coder import uiux_tool

T = "default"

UIUX = os.path.join(os.path.dirname(uiux_tool.__file__), "uiux")
SCRIPTS = os.path.join(UIUX, "scripts")
ENGINE = os.path.join(SCRIPTS, "search.py")


@pytest.fixture()
def desk(env, monkeypatch, tmp_path):
    """Fresh vault in a TEMP dir (skill files + persisted design systems must never land
    in the repo), skills + uiux ON."""
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_SKILLS", "true")
    monkeypatch.setenv("CODER_UIUX", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    store.ensure()
    skills_store.reset_for_tests()
    yield monkeypatch
    skills_store.reset_for_tests()
    get_settings.cache_clear()


class _Ctx:
    tenant_id = T
    conversation_id = "c1"


def _engine(*args):
    p = subprocess.run(["python3", ENGINE, *args], capture_output=True, text=True,
                       timeout=30, cwd=SCRIPTS, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert p.returncode == 0, p.stderr
    return p.stdout


# ---------------------------------------------------------------- (1) vendor

def test_vendored_engine_present():
    for f in ("search.py", "core.py", "design_system.py", "reasoning_contract.py",
              os.path.join("..", "LICENSE"), os.path.join("..", "PROVENANCE.md")):
        assert os.path.exists(os.path.join(SCRIPTS, f)), f
    data = os.path.join(UIUX, "data")
    for csv in ("styles.csv", "colors.csv", "typography.csv", "google-fonts.csv",
                "ux-guidelines.csv", "charts.csv", "landing.csv", "products.csv",
                "icons.csv", "motion.csv", "react-performance.csv", "app-interface.csv",
                "ui-reasoning.csv"):
        assert os.path.exists(os.path.join(data, csv)), csv
    stacks = os.listdir(os.path.join(data, "stacks"))
    assert len([s for s in stacks if s.endswith(".csv")]) == 22


def test_engine_design_system_runs():
    out = _engine("beauty spa wellness service", "--design-system", "-p", "Serenity Spa")
    assert "DESIGN SYSTEM" in out and "COLORS" in out and "TYPOGRAPHY" in out


def test_engine_domain_search_runs():
    out = _engine("keyboard focus modal", "--domain", "ux", "-n", "2")
    assert "Found:" in out and "focus" in out.lower()


def test_engine_stack_search_runs():
    out = _engine("list building performance", "--stack", "flutter", "-n", "1")
    assert "flutter" in out.lower() and "ListView" in out


def test_engine_zero_results_honest():
    out = _engine("zzzqqqxyzzy nonexistent nonsense", "--domain", "ux", "-n", "2")
    assert "**Found:** 0 results" in out                  # never fabricated


# ---------------------------------------------------------------- (2) tool

def test_tool_registered():
    """The wire into the agent table is a SOURCE pin (importing the full table needs the
    sandbox's heavier deps - the documented red class); the handler itself runs live."""
    tools_py = os.path.join(os.path.dirname(uiux_tool.__file__), os.pardir, "agent", "tools.py")
    src = open(os.path.abspath(tools_py), encoding="utf-8").read()
    assert "from ..coder.uiux_tool import UIUX_HANDLERS, UIUX_LABELS, UIUX_TOOLS" in src
    assert 'TOOLS.extend(t for t in UIUX_TOOLS if t["name"] not in _seen)' in src
    assert "TOOL_LABELS.update(UIUX_LABELS)" in src
    assert "HANDLERS.update(UIUX_HANDLERS)" in src
    assert uiux_tool.UIUX_TOOLS[0]["name"] == "uiux_design"
    assert uiux_tool.UIUX_HANDLERS["uiux_design"] is uiux_tool.uiux_design
    assert "uiux_design" in uiux_tool.UIUX_LABELS


def test_tool_gate_switch(desk, monkeypatch):
    monkeypatch.setenv("CODER_UIUX", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="spa"))
    assert "coder_uiux" in r["error"]
    monkeypatch.setenv("CODER_UIUX", "true")
    monkeypatch.setenv("CODER_ENABLED", "false")
    get_settings.cache_clear()
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="spa"))
    assert "error" in r
    get_settings.cache_clear()


def test_tool_design_system_happy(desk):
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="beauty spa wellness service",
                                          design_system=True, max_results=3))
    assert r["mode"] == "design-system"
    assert "DESIGN SYSTEM" in r["text"] and len(r["text"]) <= uiux_tool.OUTPUT_CAP


def test_tool_domain_and_stack(desk):
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="keyboard focus modal",
                                          domain="ux", max_results=1))
    assert r["mode"] == "domain:ux" and "Found:" in r["text"]
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="list building performance",
                                          stack="flutter", max_results=1))
    assert r["mode"] == "stack:flutter" and "ListView" in r["text"]


def test_tool_unknown_domain_honest(desk):
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="spa", domain="nope"))
    assert "unknown domain" in r["error"]
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="spa", stack="cobol"))
    assert "unknown stack" in r["error"]


def test_query_required_and_capped(desk):
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="   "))
    assert "query is required" in r["error"]
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="spa " * 400, design_system=True))
    assert r["query"] == "spa " * 79 + "spa"[:0] or len(r["query"]) <= uiux_tool.QUERY_CAP


def test_persist_writes_into_tenant_vault_only(desk, tmp_path):
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="beauty spa wellness service",
                                          design_system=True, persist=True,
                                          project="Serenity Spa"))
    assert "MASTER" in r["text"] or "design-system" in r["text"] or "Persist" in r["text"]
    vault = os.path.join(os.environ["CODER_DIR"], "uiux", T)
    master = os.path.join(vault, "design-system", "serenity-spa", "MASTER.md")
    assert os.path.exists(master)                       # inside the tenant's own vault
    assert not os.path.exists(os.path.join(SCRIPTS, "design-system"))   # never cwd-relative


def test_persist_never_overwrites_master(desk):
    asyncio.run(uiux_tool.uiux_design(_Ctx(), query="beauty spa wellness service",
                                      design_system=True, persist=True, project="Serenity Spa"))
    vault = os.path.join(os.environ["CODER_DIR"], "uiux", T)
    master = os.path.join(vault, "design-system", "serenity-spa", "MASTER.md")
    with open(master, "w", encoding="utf-8") as f:
        f.write("HER OWN DECISIONS STAY")
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="coffee shop landing page",
                                          design_system=True, persist=True,
                                          project="Serenity Spa"))
    with open(master, encoding="utf-8") as f:
        assert f.read() == "HER OWN DECISIONS STAY"     # --force is not a thing the tool can pass
    assert "skip" in r["text"].lower() or "exist" in r["text"].lower()


def test_page_override_file(desk):
    asyncio.run(uiux_tool.uiux_design(_Ctx(), query="analytics dashboard internal tool",
                                      design_system=True, persist=True, project="Ops Console",
                                      page="dashboard"))
    vault = os.path.join(os.environ["CODER_DIR"], "uiux", T)
    assert os.path.exists(os.path.join(vault, "design-system", "ops-console",
                                       "pages", "dashboard.md"))


# ---------------------------------------------------------------- (3) seed

def test_seed_skill_lints():
    path = os.path.join(os.path.dirname(uiux_tool.__file__), "skillpack", "uiux-pro-max.md")
    name, desc, body = parse_skill(open(path, encoding="utf-8").read())
    assert name == "uiux-pro-max"
    d, b = validate(desc, body)
    assert len(d) <= 60 and len(b) <= 4000


def test_all_seed_files_lint():
    seed_dir = os.path.join(os.path.dirname(uiux_tool.__file__), "skillpack")
    files = sorted(f for f in os.listdir(seed_dir) if f.endswith(".md"))
    assert len(files) == 99   # 11 starters + 61 earlier pack lanes + 27 omni skills (v0.561, the 18 omni families); upstream/ archive is a subdir, listdir never sees it
    for f in files:
        name, desc, body = parse_skill(open(os.path.join(seed_dir, f), encoding="utf-8").read())
        validate(desc, body)


def test_seed_feeds_and_matches(desk):
    r = skill_packs.seed(T)
    assert r["seeded"] == 11   # the class-level starters lane (v0.492 model: byox rides its own seed_byox lane, 31 more under the BYOX stamp)
    blk = inject.skills_block(T, "design a new landing page for my shop", surface="chat")
    assert "uiux-pro-max" in blk
    counts = store.skill_use_counts(T)
    assert counts["uiux-pro-max"]["shown"] == 1


# ---------------------------------------------------------------- (4) version

def test_version_layer():
    server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # server/
    main = open(os.path.join(server_dir, "app", "main.py"), encoding="utf-8").read()
    assert 'APP_VERSION = "0.656.0"' in main and "UIUX PRO MAX" in main
    pub = open(os.path.join(server_dir, "..", "pubspec.yaml"), encoding="utf-8").read()
    assert "version: 0.656.0+662" in pub
