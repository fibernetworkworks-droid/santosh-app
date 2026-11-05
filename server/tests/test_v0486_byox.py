"""v0.492.0 BYOX SKILL PACK tests.

Covers:
- Registry completeness (31 categories, TUTORIALS dict)
- guide.list_categories: unfiltered, filtered, no match, tutorial_count
- guide.get_guide: exact slug, display_name substring, fuzzy, missing
- guide.get_guide levels: quick, standard, deep
- guide.get_guide language filtering
- guide.plan_learning: basic, with background, time_weeks, tutorial_count
- byox_tools: tool registration (3 tools), labels, handlers exist, language param
- tools.py BYOX tools registered in TOOLS, HANDLERS, TOOL_LABELS
- admit.py byox family keywords
- config byox_enabled default
- /api/byox/categories and /api/byox/guide/<slug> routes
- skill seed files: 31 files exist in skillpack/
- version
"""
from __future__ import annotations

import os
import pytest

# ---------------------------------------------------------------- registry

def test_registry_has_31_categories():
    from app.byox import CATEGORIES, SLUGS
    assert len(CATEGORIES) == 31
    assert len(SLUGS) == 31


def test_every_category_has_required_fields():
    from app.byox import CATEGORIES
    required = {"slug", "display_name", "description", "core_concepts",
                "best_languages", "phases", "reference_url", "tutorial_count"}
    for slug, cat in CATEGORIES.items():
        assert required <= cat.keys(), f"{slug} missing fields"
        assert cat["slug"] == slug
        assert len(cat["phases"]) >= 4
        assert len(cat["core_concepts"]) >= 3
        assert cat["reference_url"].startswith("http")
        assert isinstance(cat["tutorial_count"], int) and cat["tutorial_count"] >= 0


def test_all_slugs_byox_prefixed():
    from app.byox import SLUGS
    for slug in SLUGS:
        assert slug.startswith("byox-"), slug


# ---------------------------------------------------------------- guide.list_categories

def test_list_all_categories():
    from app.byox.guide import list_categories
    cats = list_categories()
    assert len(cats) == 31
    for c in cats:
        assert "slug" in c and "display_name" in c
        assert "tutorial_count" in c and isinstance(c["tutorial_count"], int)


def test_list_filter_by_keyword():
    from app.byox.guide import list_categories
    cats = list_categories("web")
    slugs = [c["slug"] for c in cats]
    assert "byox-web-server" in slugs or "byox-web-browser" in slugs


def test_list_filter_no_match():
    from app.byox.guide import list_categories
    cats = list_categories("zzznomatchzz")
    assert cats == []


# ---------------------------------------------------------------- guide.get_guide

def test_get_guide_exact_slug():
    from app.byox.guide import get_guide
    g = get_guide("byox-git")
    assert g["slug"] == "byox-git"
    assert "phases" in g and len(g["phases"]) >= 4
    assert "core_concepts" in g
    assert "tutorials" in g and isinstance(g["tutorials"], list)
    assert g["tutorial_count"] > 0


def test_get_guide_tutorials_count_matches():
    from app.byox import TUTORIALS
    from app.byox.guide import get_guide
    g = get_guide("byox-web-server")
    assert len(g["tutorials"]) == len(TUTORIALS.get("byox-web-server", []))


def test_get_guide_language_filter():
    from app.byox.guide import get_guide
    g = get_guide("byox-git", language="Python")
    assert all(t["lang"] == "Python" for t in g["tutorials"])
    assert len(g["tutorials"]) > 0


def test_get_guide_language_filter_no_match_returns_all():
    from app.byox.guide import get_guide
    from app.byox import TUTORIALS
    g = get_guide("byox-git", language="COBOL")
    # falls back to all tutorials + language_note
    assert "language_note" in g
    assert len(g["tutorials"]) == len(TUTORIALS.get("byox-git", []))


def test_get_guide_display_name_substring():
    from app.byox.guide import get_guide
    g = get_guide("Git")
    assert g["slug"] == "byox-git"


def test_get_guide_without_prefix():
    from app.byox.guide import get_guide
    g = get_guide("database")
    assert g["slug"] == "byox-database"


def test_get_guide_level_quick():
    from app.byox.guide import get_guide
    g = get_guide("byox-shell", level="quick")
    assert "phases" in g
    assert "core_concepts" not in g    # quick omits them


def test_get_guide_level_deep():
    from app.byox.guide import get_guide
    g = get_guide("byox-web-server", level="deep")
    assert "deep_tips" in g
    assert len(g["deep_tips"]) >= 4


def test_get_guide_not_found_returns_error_and_suggestions():
    from app.byox.guide import get_guide
    g = get_guide("nonexistent-zzz")
    assert "error" in g
    assert "suggestions" in g


# ---------------------------------------------------------------- guide.plan_learning

def test_plan_learning_basic():
    from app.byox.guide import plan_learning
    plan = plan_learning("I want to build a web server")
    assert "projects" in plan
    assert len(plan["projects"]) >= 1
    for proj in plan["projects"]:
        assert "slug" in proj and "reference_url" in proj
        assert "tutorial_count" in proj and isinstance(proj["tutorial_count"], int)


def test_plan_learning_with_background():
    from app.byox.guide import plan_learning
    plan = plan_learning("build a database", background="Python, Go", time_weeks=8)
    assert plan["background"] == "Python, Go"
    assert plan["time_weeks"] == 8


def test_plan_learning_no_match_gives_fallback():
    from app.byox.guide import plan_learning
    plan = plan_learning("zzz no match at all zzz", time_weeks=4)
    # fallback returns default starter projects
    assert len(plan["projects"]) >= 1


# ---------------------------------------------------------------- tools registration

def test_byox_tools_exports():
    from app.agent.byox_tools import BYOX_TOOLS, BYOX_LABELS, BYOX_HANDLERS
    names = {t["name"] for t in BYOX_TOOLS}
    assert names == {"byox_list", "byox_guide", "byox_plan"}
    assert set(BYOX_LABELS.keys()) == names
    assert set(BYOX_HANDLERS.keys()) == names


def test_byox_guide_tool_has_language_param():
    from app.agent.byox_tools import BYOX_TOOLS
    guide_tool = next(t for t in BYOX_TOOLS if t["name"] == "byox_guide")
    assert "language" in guide_tool["input_schema"]["properties"]


def test_byox_tools_registered_in_tools_py():
    from app.agent.tools import TOOLS, HANDLERS, TOOL_LABELS
    tool_names = {t["name"] for t in TOOLS}
    assert "byox_list" in tool_names
    assert "byox_guide" in tool_names
    assert "byox_plan" in tool_names
    assert "byox_list" in HANDLERS
    assert "byox_plan" in TOOL_LABELS


# ---------------------------------------------------------------- admit.py

def test_admit_byox_family():
    from app.agent.admit import EXTRA_KEYS
    assert "byox" in EXTRA_KEYS
    keys = EXTRA_KEYS["byox"]
    assert "build your own" in keys
    assert "byox_guide" in keys


# ---------------------------------------------------------------- config

def test_config_byox_enabled_default_on():
    from app.config import get_settings
    assert get_settings().byox_enabled is True


# ---------------------------------------------------------------- skill seed files

def test_skillpack_byox_files_count():
    skillpack_dir = os.path.join(os.path.dirname(__file__), "..", "app", "coder", "skillpack")
    byox_files = [f for f in os.listdir(skillpack_dir) if f.startswith("byox-") and f.endswith(".md")]
    assert len(byox_files) == 31


def test_skillpack_byox_files_valid_frontmatter():
    import re
    skillpack_dir = os.path.join(os.path.dirname(__file__), "..", "app", "coder", "skillpack")
    front_re = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
    for fn in os.listdir(skillpack_dir):
        if not (fn.startswith("byox-") and fn.endswith(".md")):
            continue
        path = os.path.join(skillpack_dir, fn)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        m = front_re.match(text)
        assert m, f"{fn} has no frontmatter"
        head = m.group(1)
        assert "name:" in head, f"{fn} missing name"
        assert "description:" in head, f"{fn} missing description"
        body = text[m.end():].strip()
        desc = [l for l in head.splitlines() if l.startswith("description:")][0][len("description:"):].strip()
        assert len(desc) <= 60, f"{fn} description {len(desc)} > 60 (the store's lint refuses it)"
        assert len(body) > 50, f"{fn} body too short"
        assert len(body) <= 4000, f"{fn} body exceeds 4000 chars"


# ---------------------------------------------------------------- routes

def test_byox_routes_mounted_and_handlers_work():
    import asyncio
    from app.main import app, byox_categories
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/byox/categories" in paths and "/api/byox/guide/{slug}" in paths
    data = asyncio.run(byox_categories(""))
    assert len(data["categories"]) == 31


# ---------------------------------------------------------------- version

def test_tutorials_dict_has_31_keys():
    from app.byox import TUTORIALS, SLUGS
    # every slug that exists should be in TUTORIALS (at least the major ones)
    assert len(TUTORIALS) == 31
    for slug in SLUGS:
        assert slug in TUTORIALS, f"TUTORIALS missing {slug}"


def test_tutorials_total_count():
    from app.byox import TUTORIALS
    total = sum(len(v) for v in TUTORIALS.values())
    assert total >= 400  # 415 expected


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.547.0"
