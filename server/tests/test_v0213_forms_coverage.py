"""v0.213.0 - Google Forms 100% coverage: the tool registry grew 9 -> 13 tools (form_move / form_media /
form_delete / form_copy), the question types grew 11 -> 15 (page = pageBreakItem, grid / checkbox_grid =
questionGroupItem rowQuestion, upload = fileUploadQuestion; time gained duration), quiz questions gained
feedback (generalFeedback / whenRight / whenWrong), form_settings gained published (unpublish / republish via
publishState) and emails (emailCollectionType off / collect / verify), form_responses gained response_id
(forms.responses.get), and the confirm-card family grew from 2 to 3 actions (added delete_form - Drive Trash,
recoverable). forms.watches (pubsub push) stays an honest gap: it needs a pubsub topic on the user's project;
the 10-minute polling alert already covers the user need, so polling it is.

This pin sits next to the Drive (v0.209) / Sheets (v0.210/v0.212) coverage pins so the Forms toolset never
silently shrinks."""
from __future__ import annotations

from app.agent import forms_tools as ft
from app.agent import gdrive_tools as gt
from app.agent import sheets_tools as st
from app.agent import drive_tools as dt
from app.agent.tools import TOOLS, TOOL_LABELS, HANDLERS
from app.bazar.connectors.forms import TITLES
from app.forms import service as fs

NEW = ["form_move", "form_media", "form_delete", "form_copy"]
NEW_TYPES = ["page", "grid", "checkbox_grid", "upload"]


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.227.2"    # conscious-bump guard: moves with every release (bump with pubspec)


def test_registry_has_13_tools():
    names = [t["name"] for t in ft.FORMS_TOOLS]
    assert len(names) == 13 and len(set(names)) == 13
    for n in NEW:
        assert n in names and n in ft.FORMS_HANDLERS and n in ft.FORMS_LABELS
    assert set(ft.FORMS_HANDLERS) == set(names) and set(ft.FORMS_LABELS) == set(names)


def test_new_tools_reach_the_global_registry():
    reg = {t["name"] for t in TOOLS}
    for n in NEW:
        assert n in reg and n in HANDLERS and n in TOOL_LABELS


def test_old_gdrive_path_still_registers_nothing():
    """The Drive/Sheets legacy shadow must stay zero-leak now that Forms tools also own names."""
    modern = set(st.SHEETS_HANDLERS) | set(dt.DRIVE_HANDLERS) | set(ft.FORMS_HANDLERS)
    leaked = [t["name"] for t in gt.GDRIVE_TOOLS if t["name"] not in modern]
    assert leaked == [], "the legacy service-account tools must all be shadowed by the modern toolsets"
    names = [t["name"] for t in TOOLS]
    for n in {t["name"] for t in gt.GDRIVE_TOOLS} & modern:
        assert names.count(n) == 1, f"{n} registered more than once"


def test_card_backed_actions_have_bazar_copy():
    """The Bazar santosh-forms pack grew from 2 to 3 confirm-card actions (added delete_form)."""
    for act, title in {"share": "Form share karein?", "delete_questions": "Jawab wale sawaal hatayein?",
                       "delete_form": "Form delete karein?"}.items():
        assert TITLES.get(act) == title


def test_schemas_carry_the_new_surface():
    spec = {t["name"]: t for t in ft.FORMS_TOOLS}
    # question types grew
    assert set(NEW_TYPES) <= set(spec["form_create"]["input_schema"]["properties"]["questions"]["items"]["properties"]["type"]["enum"])
    q = spec["form_create"]["input_schema"]["properties"]["questions"]["items"]["properties"]
    for k in ("rows", "columns", "max_files", "max_file_mb", "file_types", "folder_id",
              "feedback", "feedback_right", "feedback_wrong", "duration"):
        assert k in q, f"QUESTION schema missing {k}"
    # form_move requires question + new_index
    assert set(spec["form_move"]["input_schema"]["required"]) == {"form", "question", "new_index"}
    # form_media kind enum
    assert spec["form_media"]["input_schema"]["properties"]["kind"]["enum"] == ["image", "video"]
    # form_settings carries published + emails
    st_props = spec["form_settings"]["input_schema"]["properties"]
    assert "published" in st_props and st_props["emails"]["enum"] == ["off", "collect", "verify"]
    # form_responses carries response_id
    assert "response_id" in spec["form_responses"]["input_schema"]["properties"]
    # form_copy carries new_title
    assert "new_title" in spec["form_copy"]["input_schema"]["properties"]


def test_run_pending_dispatches_delete_form():
    import inspect
    from app.forms import service as fss
    src = inspect.getsource(fss.run_pending)
    assert '"delete_form"' in src and '"share"' in src and '"delete_questions"' in src


def test_item_shapes_for_new_types():
    """page -> pageBreakItem, grid -> questionGroupItem with rows/columns, upload -> fileUploadQuestion,
    feedback lands inside grading."""
    page = fs.item_for({"title": "Naya page", "type": "page", "description": "x"})
    assert "pageBreakItem" in page and page["description"] == "x"
    grid = fs.item_for({"title": "G", "type": "grid", "rows": ["r1", "r2"], "columns": ["c1", "c2"]})
    g = grid["questionGroupItem"]["grid"]
    assert [r["value"] for r in g["rows"]] == ["r1", "r2"] and "type" not in g
    cb = fs.item_for({"title": "G", "type": "checkbox_grid", "rows": ["r"], "columns": ["c"]})
    assert cb["questionGroupItem"]["grid"]["type"] == "CHECKBOX"
    up = fs.item_for({"title": "U", "type": "upload", "max_files": 3, "max_file_mb": 8, "file_types": ["PDF"]})
    fq = up["questionItem"]["question"]["fileUploadQuestion"]
    assert fq == {"maxFiles": 3, "maxFileSizeMb": 8, "types": ["PDF"]}
    graded = fs.item_for({"title": "Q", "type": "choice", "options": ["a", "b"], "correct": "a",
                          "feedback": "gen", "feedback_right": "right", "feedback_wrong": "wrong"})
    grading = graded["questionItem"]["question"]["grading"]
    assert grading["generalFeedback"] == {"text": "gen"} and grading["whenRight"] == {"text": "right"} \
        and grading["whenWrong"] == {"text": "wrong"}
    t = fs.item_for({"title": "T", "type": "time", "duration": True})
    assert t["questionItem"]["question"]["timeQuestion"] == {"duration": True}
