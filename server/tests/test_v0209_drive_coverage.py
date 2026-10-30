"""v0.210.0 - Google Drive 100% coverage: the tool registry grew 12 -> 21 tools (details, access management, trash
list, delete-forever / empty-trash, comments, revisions, shared drives, changes, biggest files), find gained
in_trash / modified_hours / order=size, organize gained describe / restrict_copying / allow_copying / shortcut, and
export gained odt / rtf / html / epub / md (Docs), ods / tsv (Sheets), jpeg / svg (Drawings). The old five-tool
service-account path (gdrive_tools) registers NOTHING any more - every one of its names is owned by the modern
SHEETS / DRIVE toolsets. Outward or hard-to-undo actions (unshare, role, ownership transfer, delete forever,
empty-trash, comment, reply, comment-delete - beside the existing share / public / trash) wait for the user's tap
on a confirm card, and comment text passes the same PII guard as uploads."""
from __future__ import annotations

from app.agent import drive_tools as dt
from app.agent import gdrive_tools as gt
from app.agent import sheets_tools as st
from app.agent.tools import TOOLS, TOOL_LABELS, HANDLERS
from app.bazar.connectors.drive import TITLES

NEW = ["drive_details", "drive_access", "drive_trash_list", "drive_delete", "drive_comments", "drive_revisions",
       "drive_shared_drives", "drive_changes", "drive_biggest"]


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.266.0"    # conscious-bump guard: moves with every release (bump with pubspec)


def test_registry_has_21_tools():
    names = [t["name"] for t in dt.DRIVE_TOOLS]
    assert len(names) == 21 and len(set(names)) == 21
    for n in NEW:
        assert n in names and n in dt.DRIVE_HANDLERS and n in dt.DRIVE_LABELS
    assert set(dt.DRIVE_HANDLERS) == set(names) and set(dt.DRIVE_LABELS) == set(names)


def test_new_tools_reach_the_global_registry():
    reg = {t["name"] for t in TOOLS}
    for n in NEW:
        assert n in reg and n in HANDLERS and n in TOOL_LABELS


def test_old_gdrive_path_registers_nothing():
    modern = set(st.SHEETS_HANDLERS) | set(dt.DRIVE_HANDLERS)
    leaked = [t["name"] for t in gt.GDRIVE_TOOLS if t["name"] not in modern]
    assert leaked == [], "the legacy service-account tools must all be shadowed by the modern toolsets"
    # every name shared between the legacy and modern toolsets is registered exactly once
    names = [t["name"] for t in TOOLS]
    for n in {t["name"] for t in gt.GDRIVE_TOOLS} & modern:
        assert names.count(n) == 1, f"{n} registered more than once"


def test_card_backed_actions_have_bazar_copy():
    for act, title in {"unshare": "Sharing hata dein?", "role": "Role badlein?", "transfer": "Ownership de dein?",
                       "delete": "Hamesha ke liye delete?", "empty_trash": "Poora Trash khaalein?",
                       "comment": "Comment daalein?", "reply": "Reply daalein?",
                       "comment_delete": "Comment hatayein?"}.items():
        assert TITLES.get(act) == title


def test_schemas_carry_the_new_surface():
    spec = {t["name"]: t for t in dt.DRIVE_TOOLS}
    acc = spec["drive_access"]["input_schema"]["properties"]
    assert acc["action"]["enum"] == ["remove", "stop", "role", "owner"] and "person" in acc and "role" in acc
    assert "empty" in spec["drive_delete"]["input_schema"]["properties"]
    assert spec["drive_comments"]["input_schema"]["properties"]["action"]["enum"] == \
        ["list", "add", "reply", "resolve", "reopen", "delete"]
    find = spec["drive_find"]["input_schema"]["properties"]
    assert find["in_trash"]["type"] == "boolean" and find["order"]["enum"] == ["size"]
    org = spec["drive_organize"]["input_schema"]["properties"]["action"]["enum"]
    for a in ("describe", "restrict_copying", "allow_copying", "shortcut"):
        assert a in org
