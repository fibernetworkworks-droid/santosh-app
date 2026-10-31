"""v0.210.0 - Google Sheets 100% coverage: the tool registry grew 12 -> 24 tools (sheet_clear / sheet_copy_tab /
sheet_duplicate_tab / sheet_delete_tab / sheet_format / sheet_protect / sheet_named_range /
sheet_conditional_format / sheet_data_validation / sheet_merge / sheet_notes / sheet_find_replace), every
Sheets API v4 surface the API offers is now reachable through per-user OAuth (with the server-owner service account
as fallback). Outward or hard-to-undo actions (clear ranges, delete tab, lock range) wait for the user's tap on a
confirm card; cell-note text and find-replace replacement text pass the same Aadhaar/OTP/password/CVV PII guard as
uploads. This pin sits next to the v0.209 Drive pin and the v0.189 docstudio pin so the toolset never silently
shrinks."""
from __future__ import annotations

from app.agent import gdrive_tools as gt
from app.agent import sheets_tools as st
from app.agent import drive_tools as dt
from app.agent.tools import TOOLS, TOOL_LABELS, HANDLERS
from app.bazar.connectors.sheets import TITLES

NEW = ["sheet_clear", "sheet_copy_tab", "sheet_duplicate_tab", "sheet_delete_tab", "sheet_format",
       "sheet_protect", "sheet_named_range", "sheet_conditional_format", "sheet_data_validation",
       "sheet_merge", "sheet_notes", "sheet_find_replace"]


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.331.0"    # conscious-bump guard: moves with every release (bump with pubspec)


def test_registry_has_24_tools():
    names = [t["name"] for t in st.SHEETS_TOOLS]
    assert len(names) == 24 and len(set(names)) == 24
    for n in NEW:
        assert n in names and n in st.SHEETS_HANDLERS and n in st.SHEETS_LABELS
    assert set(st.SHEETS_HANDLERS) == set(names) and set(st.SHEETS_LABELS) == set(names)


def test_new_tools_reach_the_global_registry():
    reg = {t["name"] for t in TOOLS}
    for n in NEW:
        assert n in reg and n in HANDLERS and n in TOOL_LABELS


def test_old_gdrive_path_registers_nothing():
    """The legacy five-tool service-account path (gdrive_tools) still registers nothing — every name is shadowed."""
    modern = set(st.SHEETS_HANDLERS) | set(dt.DRIVE_HANDLERS)
    leaked = [t["name"] for t in gt.GDRIVE_TOOLS if t["name"] not in modern]
    assert leaked == [], "the legacy service-account tools must all be shadowed by the modern toolsets"
    # every name shared between the legacy and modern toolsets is registered exactly once
    names = [t["name"] for t in TOOLS]
    for n in {t["name"] for t in gt.GDRIVE_TOOLS} & modern:
        assert names.count(n) == 1, f"{n} registered more than once"


def test_card_backed_actions_have_bazar_copy():
    """The Bazar santosh-sheets pack grew from 3 confirm-card actions (update/delete/share) to 6 (added clear /
    delete_tab / protect). Every title is hand-written Hinglish, never model text."""
    for act, title in {"update": "Itni rows badlein?", "delete": "Rows hatayein?",
                       "share": "Sheet share karein?", "clear": "Values saaf karein?",
                       "delete_tab": "Tab hatayein?", "protect": "Lock kar dein?"}.items():
        assert TITLES.get(act) == title


def test_schemas_carry_the_new_surface():
    """Spot-check that the new tool schemas actually expose their enums and required fields."""
    spec = {t["name"]: t for t in st.SHEETS_TOOLS}
    # sheet_clear requires spreadsheet + ranges
    assert "ranges" in spec["sheet_clear"]["input_schema"]["properties"]
    assert "ranges" in spec["sheet_clear"]["input_schema"].get("required", [])
    # sheet_delete_tab takes a tab
    assert "tab" in spec["sheet_delete_tab"]["input_schema"]["properties"]
    # sheet_format exposes the format sub-keys
    fmt = spec["sheet_format"]["input_schema"]["properties"]["format"]["properties"]
    for k in ("bold", "italic", "font_size", "font_color", "bg_color", "number_format",
              "horizontal_alignment", "vertical_alignment", "wrap_strategy", "freeze_rows", "freeze_cols"):
        assert k in fmt
    # sheet_protect exposes editors list
    assert "editors" in spec["sheet_protect"]["input_schema"]["properties"]
    # sheet_named_range action enum
    assert spec["sheet_named_range"]["input_schema"]["properties"]["action"]["enum"] == \
        ["add", "update", "delete", "list"]
    # sheet_conditional_format rule.type enum
    assert spec["sheet_conditional_format"]["input_schema"]["properties"]["rule"]["properties"]["type"]["enum"] == \
        ["color_scale", "data_bar", "cell_is", "expression"]
    # sheet_data_validation rule.type enum
    assert spec["sheet_data_validation"]["input_schema"]["properties"]["rule"]["properties"]["type"]["enum"] == \
        ["list", "number", "whole", "date", "text_length", "custom_formula"]
    # sheet_merge merge_type enum
    assert spec["sheet_merge"]["input_schema"]["properties"]["merge_type"]["enum"] == \
        ["MERGE_ALL", "MERGE_COLUMNS", "MERGE_ROWS"]
    assert spec["sheet_merge"]["input_schema"]["properties"]["action"]["enum"] == ["merge", "unmerge"]
    # sheet_notes is PII-guarded (description mentions it)
    assert "PII" in spec["sheet_notes"]["description"] or "Aadhaar" in spec["sheet_notes"]["description"]
    # sheet_find_replace is PII-guarded too
    assert "PII" in spec["sheet_find_replace"]["description"] or "Aadhaar" in spec["sheet_find_replace"]["description"]


def test_run_pending_dispatches_new_actions():
    """The run_pending dispatcher in service.py knows about clear / delete_tab / protect — proven by source
    inspection (the actions live in the dispatch table)."""
    import inspect
    from app.sheets import service as ss
    src = inspect.getsource(ss.run_pending)
    for act in ('"clear"', '"delete_tab"', '"protect"'):
        assert act in src, f"run_pending must dispatch {act}"
