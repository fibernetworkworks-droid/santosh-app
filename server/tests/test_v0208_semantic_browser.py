"""v0.208 SEMANTIC BROWSER - AI browser ops by REF, not pixels (owner: "WHY HOOLA AI IN BOTH MERA PC
AND OWN PC, NOT ABLE TO PERFORM BROWSER OPERATION SMOOTHLY AND PERFECTLY --- FIND THE ROOT CAUSE").

THE ROOT CAUSE (proved in code): both PCs ran browser steps as computer-use-by-pixels - the operator loop
is "screenshot -> vision model picks ONE action -> PC does it -> repeat"; every click was an X,Y GUESS on a
lossy 1280px JPEG with no DOM knowledge, no hit feedback, no wait-for-element, and each micro-step cost a
full vision round trip. CDP/UIA were used only for READING, never for ACTING.

THE FIX: one shared action contract on BOTH PCs - page_elements (real buttons/links/fields as numbered
refs), page_click / page_type / page_select BY REF, page_fill_form (whole form in ONE step), wait_for.
Two native engines: CDP Runtime.evaluate on the Hoola PC (desktop-linux/agent.py 1.3.0), UIA patterns on
her Windows PC (desktop/santosh_desktop 1.5.0). The server (operator.py) gains the 6 tools, dispatch,
narration, the upgrade hint for old desktops and the SEMANTIC-FIRST prompts.

Tests here pin the SERVER side: tool wiring (both TOOLS and HOOLA_TOOLS), the _do dispatch through a fake
_pc (element list formatting, privacy: typed text never echoed, fill-form pass-through and failure lines,
wait_for clamp, idvault untouched path), the _say narration, the old-desktop upgrade hint for every new
action, the semantic-first prompt pins, and the privacy contract on both device engines (the value never
leaves the PC - only length + matches).
"""
import asyncio
import sys
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

from app.pc import operator as op_mod  # noqa: E402

NEW_ACTIONS = ("page_elements", "page_click", "page_type", "page_select", "page_fill_form", "wait_for")


# ---------------- wiring: the model gets the new tools on BOTH PCs ----------------
def test_tools_carry_all_six_actions():
    names = [t["name"] for t in op_mod.TOOLS]
    for n in NEW_ACTIONS:
        assert n in names, n


def test_hoola_tools_carry_the_same_plus_the_vm_surface():
    names = [t["name"] for t in op_mod.HOOLA_TOOLS]
    for n in NEW_ACTIONS + ("install", "run", "user_pc_pull", "user_pc_push"):
        assert n in names, n


def test_schemas_are_well_formed():
    for t in op_mod.TOOLS:
        if t["name"] not in NEW_ACTIONS:
            continue
        sch = t["input_schema"]
        assert sch.get("type") == "object"
        assert isinstance(sch.get("properties"), dict)
        req = sch.get("required", [])
        assert set(req) <= set(sch["properties"]), t["name"]
    reqs = {t["name"]: set(t["input_schema"].get("required", [])) for t in op_mod.TOOLS}
    assert reqs["page_click"] == {"ref"}
    assert reqs["page_type"] == {"ref", "text"}
    assert reqs["page_fill_form"] == {"entries"}


# ---------------- the _do dispatch (fake _pc) ----------------
class FakePC:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, op, action, args, timeout=30, log=True):
        self.calls.append((action, args, timeout))
        return self.result


def test_page_elements_formats_refs():
    fake = FakePC({"title": "Example Domain", "url": "https://example.com",
                   "elements": [{"ref": 1, "role": "link", "name": "More information..."},
                                {"ref": 2, "role": "input", "name": "", "placeholder": "Search"}]})
    out = asyncio.run(_do_with(op_mod, "page_elements", {"max_items": 25}, fake))
    assert "1. link 'More information...'" in out
    assert "placeholder:'Search'" in out
    assert fake.calls[0][0] == "page_elements" and fake.calls[0][1]["max_items"] == 25


async def _do_with(op_mod, name, a, fake):
    real = op_mod._pc

    async def patched(op, action, args, timeout=30, log=True):
        return await fake(op, action, args, timeout, log)

    op_mod._pc = patched
    try:
        return await op_mod._do(op_mod.Op(id="t1", tenant="ten1", conv="c1", task="website kholo"), name, a)
    finally:
        op_mod._pc = real


def test_page_type_never_echoes_the_text_privacy():
    fake = FakePC({"typed": True, "length": 14, "matches": True})
    out = asyncio.run(_do_with(op_mod, "page_type", {"ref": 3, "text": "Aadhaar 1234 5678 9012"}, fake))
    assert "typed into #3" in out and "verified" in out
    assert "1234" not in out, "the value itself must never come back to the model"


def test_page_type_mismatch_tells_the_model_to_retry():
    fake = FakePC({"typed": True, "length": 3, "matches": False})
    out = asyncio.run(_do_with(op_mod, "page_type", {"ref": 3, "text": "Santosh"}, fake))
    assert "does NOT match" in out and "page_elements" in out


def test_page_fill_form_passes_entries_and_reports_failures():
    fake = FakePC({"filled": 1, "total": 2,
                   "results": [{"ref": 2, "ok": True, "length": 7, "matches": True},
                               {"ref": 5, "ok": False, "err": "gone"}]})
    out = asyncio.run(_do_with(op_mod, "page_fill_form",
                               {"entries": [{"ref": 2, "text": "Santosh"}, {"ref": 5, "text": "x"}]}, fake))
    assert "filled 1/2 fields in one step" in out
    assert "#5 (gone)" in out and "re-list with page_elements" in out
    sent = fake.calls[0][1]["entries"]
    assert sent == [{"ref": 2, "text": "Santosh"}, {"ref": 5, "text": "x"}]


def test_page_fill_form_refuses_garbage():
    out = asyncio.run(_do_with(op_mod, "page_fill_form", {"entries": "lol"}, FakePC({})))
    assert out.startswith("REFUSED")


def test_page_select_reports_options_on_a_miss():
    fake = FakePC({"selected": "", "options": ["Male", "Female"]})
    out = asyncio.run(_do_with(op_mod, "page_select", {"ref": 4, "value": "other"}, fake))
    assert "not found" in out and "Male" in out and "Female" in out


def test_wait_for_clamps_seconds():
    fake = FakePC({"found": True, "title": "Done"})
    asyncio.run(_do_with(op_mod, "wait_for", {"text": "Payment success", "seconds": 999}, fake))
    action, args, timeout = fake.calls[0]
    assert args["seconds"] == 20 and timeout >= 20


def test_page_click_reports_navigation():
    fake = FakePC({"clicked": True, "title": "IANA-managed reserved domains", "navigated": True})
    out = asyncio.run(_do_with(op_mod, "page_click", {"ref": 1}, fake))
    assert "clicked element #1" in out and "navigated" in out


def test_bad_ref_is_refused_not_crashed():
    out = asyncio.run(_do_with(op_mod, "page_click", {"ref": "abc"}, FakePC({})))
    assert out.startswith("REFUSED")


# ---------------- old desktop / old agent upgrade hint ----------------
def test_upgrade_hint_for_every_new_action():
    for n in NEW_ACTIONS:
        line = op_mod._desktop_says(Exception(f"Unknown action {n}"), n)
        assert line is not None and "SantoshDesktop.exe" in line, n


# ---------------- narration (the live card) ----------------
def test_say_lines_privacy_safe():
    assert "exact mode" in op_mod._say("page_elements", {})
    assert "#3" in op_mod._say("page_click", {"ref": 3})
    assert op_mod._say("page_type", {"ref": 2, "text": "SECRET VALUE"}) == "field #2 bhar raha hoon"
    assert "ek saath" in op_mod._say("page_fill_form", {})


# ---------------- semantic-first prompts ----------------
def test_system_prompt_teaches_semantic_first():
    s = op_mod.SYSTEM
    assert "SEMANTIC FIRST" in s and "page_elements" in s
    assert "page_fill_form" in s and "ONE step" in s
    assert "ONLY when page_elements shows nothing usable" in s  # pixels stay for image-only UI


def test_hoola_addendum_says_semantic_is_native():
    a = op_mod.HOOLA_PC_ADDENDUM
    assert "SEMANTIC MODE IS NATIVE HERE" in a and "page_fill_form" in a


# ---------------- the device engines keep the privacy contract ----------------
def test_hoola_agent_returns_only_length_and_matches():
    # imported by source (importing agent mkdirs /data - container-only), same pin shape as the desktop test
    src = (Path(__file__).resolve().parents[2] / "desktop-linux/agent.py").read_text()
    assert "def do_page_elements" in src and "def do_page_click" in src
    assert "def do_page_type" in src and "def do_page_fill_form" in src and "def do_wait_for" in src
    # the type JS returns length + matches - the raw value never leaves the page
    assert "length:v.length, matches: v === TXT || v.endsWith(TXT)" in src
    assert "self._els" in src and 'ref {ref} gaya' in src  # refs resolve through the page_elements map


def test_desktop_page_type_returns_only_length_and_matches():
    src = (Path(__file__).resolve().parents[2] / "desktop/santosh_desktop/browser.py").read_text()
    # the return dict of page_type carries typed/length/matches - never the value itself
    assert '"typed": ok, "length": len(val), "matches"' in src


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.303.0"
