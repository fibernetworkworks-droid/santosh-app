"""CLAUDE SKILLS P1 - folder skills, Claude-format limits, read_file, zip import/export.

Pins: (1) frontmatter parser (block scalars, quotes); (2) imported skills live under Claude's limits
while model-written ones stay strict; (3) the imported flag + extra fields survive an update;
(4) zip import is safe (no '..', no symlink, one skill, capped) and round-trips; (5) read_file is
confined to the skill folder and text-only; (6) when_to_use makes a skill findable and
disable-model-invocation keeps it out of the shortlist; (7) injected lines stay short; (8) an
imported skill is never nominated for the shelf; (9) the old single-file skills behave as before.
"""
import io
import zipfile

import pytest

from app.coder import inject, skill_packs, skills_store, store
from app.coder.skills_store import SkillError

T = "default"
T2 = "other-tenant"

LONG_DESC = ("Guidance for building MCP servers that let LLMs use external services through well "
             "designed tools. Use when the user wants to build, extend or review an MCP server. " * 3)
LONG_BODY = "Step one. " * 900          # 9,000 chars - far over the strict 4,000


@pytest.fixture()
def desk(env, monkeypatch, tmp_path):
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_SKILLS", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    store.ensure()
    skills_store.reset_for_tests()
    yield monkeypatch
    skills_store.reset_for_tests()
    get_settings.cache_clear()


def _skill_md(name="mcp-builder", desc=None, body=None, extra=""):
    return f"---\nname: {name}\ndescription: {desc or LONG_DESC}\n{extra}---\n{body or LONG_BODY}\n"


def _zip(files: dict, symlink: str = "") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, data in files.items():
            z.writestr(n, data)
        if symlink:
            zi = zipfile.ZipInfo(symlink)
            zi.external_attr = (0o120777 << 16)
            z.writestr(zi, "/etc/passwd")
    return buf.getvalue()


# ---------------------------------------------------------------- (1) parser

def test_parse_front_block_scalars_and_quotes():
    text = ("---\nname: pdf\ndescription: >\n  Fills forms and\n  merges files.\n"
            "license: 'Apache-2.0'\nwhen_to_use: \"mentions pdf\"\n---\nbody here\n")
    front, body = skills_store.parse_front(text)
    assert front["description"] == "Fills forms and merges files."
    assert front["license"] == "Apache-2.0" and front["when_to_use"] == "mentions pdf"
    assert body == "body here"
    assert skills_store.parse_front("no frontmatter at all") == ({}, "no frontmatter at all")


# ---------------------------------------------------------------- (2)+(3) limits and flag

def test_strict_lane_unchanged_and_import_lane_relaxed(desk):
    with pytest.raises(SkillError):
        skills_store.create(T, "too-long", LONG_DESC, "body")           # model lane: 60 chars
    with pytest.raises(SkillError):
        skills_store.create(T, "big-body", "short", LONG_BODY)          # model lane: 4,000 chars
    res = skill_packs.import_skills(T, [_skill_md()], full=True)
    assert res["created"] == ["mcp-builder"], res
    r = skills_store.read(T, "mcp-builder")
    assert len(r["description"]) > 60 and len(r["body"]) > 4000
    # the OLD lane is still strict about the very same text
    res2 = skill_packs.import_skills(T, [_skill_md(name="strict-one")])
    assert res2["created"] == [] and res2["errors"], res2


def test_imported_flag_and_extras_survive_update_and_park(desk):
    skill_packs.import_skills(T, [_skill_md(extra="license: Apache-2.0\nwhen_to_use: build an MCP server\n")],
                              full=True)
    raw = open(skills_store.raw_path(T, "mcp-builder"), encoding="utf-8").read()
    assert "imported: true" in raw and "license: Apache-2.0" in raw
    skills_store.read(T, "mcp-builder")
    skills_store.update(T, "mcp-builder", body="Rewritten. " * 600)      # still over 4,000: allowed
    skills_store.set_enabled(T, "mcp-builder", False)
    skills_store.set_enabled(T, "mcp-builder", True)
    raw2 = open(skills_store.raw_path(T, "mcp-builder"), encoding="utf-8").read()
    assert "imported: true" in raw2 and "license: Apache-2.0" in raw2 and "when_to_use:" in raw2


def test_import_exists_is_skipped_never_overwritten(desk):
    skill_packs.import_skills(T, [_skill_md()], full=True)
    again = skill_packs.import_skills(T, [_skill_md(body="different")], full=True)
    assert again["created"] == [] and again["skipped"], again
    assert "Step one." in skills_store.read(T, "mcp-builder")["body"]


# ---------------------------------------------------------------- (4) zip

def test_zip_import_folder_read_file_and_delete(desk):
    z = _zip({"mcp-builder/SKILL.md": _skill_md(), "mcp-builder/reference/best.md": "# Best practices\nnaming",
              "mcp-builder/LICENSE.txt": "Apache License", "mcp-builder/fonts/a.ttf": b"\x00\x01"})
    res = skill_packs.import_zip(T, z)
    assert res["created"] == ["mcp-builder"] and res["files"] == 3, res
    assert skills_store.is_folder(T, "mcp-builder")
    assert any(s["name"] == "mcp-builder" and s.get("folder") for s in skills_store.listing(T))
    r = skills_store.read(T, "mcp-builder")
    assert "reference/best.md" in r["files"] and "LICENSE.txt" in r["files"]
    f = skills_store.read_file(T, "mcp-builder", "reference/best.md")
    assert "Best practices" in f["content"] and not f["truncated"]
    with pytest.raises(SkillError):
        skills_store.read_file(T, "mcp-builder", "fonts/a.ttf")          # binary: shipped, not readable
    skills_store.delete(T, "mcp-builder")
    assert not skills_store.is_folder(T, "mcp-builder")
    assert skills_store.listing(T) == []


def test_zip_root_layout_and_roundtrip_between_tenants(desk):
    z = _zip({"SKILL.md": _skill_md(name="theme-factory"), "themes/ocean.md": "palette"})
    assert skill_packs.import_zip(T, z)["created"] == ["theme-factory"]
    out = skill_packs.export_zip(T, "theme-factory")
    names = zipfile.ZipFile(io.BytesIO(out)).namelist()
    assert "SKILL.md" in names and "themes/ocean.md" in names
    assert skill_packs.import_zip(T2, out)["created"] == ["theme-factory"]
    assert skills_store.read_file(T2, "theme-factory", "themes/ocean.md")["content"] == "palette"
    assert skills_store.listing(T) and not any(s["name"] == "theme-factory" for s in []), "tenant T intact"
    assert skill_packs.export_zip(T, "nope-nope") is None


@pytest.mark.parametrize("files,symlink,why", [
    ({"a/SKILL.md": _skill_md(), "a/../../evil.txt": "x"}, "", "dotdot"),
    ({"/abs/SKILL.md": _skill_md()}, "", "absolute"),
    ({"a/SKILL.md": _skill_md()}, "a/link", "symlink"),
    ({"a/SKILL.md": _skill_md(), "b/SKILL.md": _skill_md(name="other-one")}, "", "two skills"),
    ({"a/readme.md": "no skill file"}, "", "no SKILL.md"),
    ({"a/b/c/SKILL.md": _skill_md()}, "", "too deep"),
])
def test_zip_refusals(desk, files, symlink, why):
    res = skill_packs.import_zip(T, _zip(files, symlink))
    assert "error" in res, why
    assert skills_store.listing(T) == [], why                            # nothing half-installed


def test_zip_not_a_zip_and_oversize_file(desk):
    assert "error" in skill_packs.import_zip(T, b"not a zip")
    assert "error" in skill_packs.import_zip(T, b"")
    big = _zip({"a/SKILL.md": _skill_md(), "a/big.md": "x" * (skill_packs.ZIP_FILE_MAX + 10)})
    assert "error" in skill_packs.import_zip(T, big)
    assert skills_store.listing(T) == []


# ---------------------------------------------------------------- (5) read_file confinement

def test_read_file_confined(desk):
    skill_packs.import_zip(T, _zip({"s/SKILL.md": _skill_md(name="confined"), "s/ok.md": "fine"}))
    for bad in ("../x.md", "/etc/passwd", "a/../../x", ".hidden", "C:/x", ""):
        with pytest.raises(SkillError):
            skills_store.read_file(T, "confined", bad)
    with pytest.raises(SkillError):
        skills_store.read_file(T, "confined", "missing.md")
    with pytest.raises(SkillError):                                     # a legacy single-file skill has none
        skills_store.create(T, "plain-one", "short", "body")
        skills_store.read_file(T, "plain-one", "ok.md")
    res = skills_store.apply(T, [{"action": "read_file", "name": "confined", "path": "ok.md"}])
    assert res["ok"] and res["results"][0]["content"] == "fine"


def test_symlink_inside_folder_cannot_escape(desk, tmp_path):
    skill_packs.import_zip(T, _zip({"s/SKILL.md": _skill_md(name="linky"), "s/ok.md": "fine"}))
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET")
    import os
    os.symlink(secret, os.path.join(skills_store._folder(T, "linky"), "leak.md"))
    with pytest.raises(SkillError):
        skills_store.read_file(T, "linky", "leak.md")


# ---------------------------------------------------------------- (6) search behaviour

def test_when_to_use_findable_and_manual_only_hidden(desk):
    skill_packs.import_skills(T, [
        _skill_md(name="alpha-skill", desc="Generic helper", body="does things",
                  extra="when_to_use: user mentions quarterly zebra reports\n"),
        _skill_md(name="manual-skill", desc="Manual quarterly helper", body="does zebra things",
                  extra="disable-model-invocation: true\n")], full=True)
    hits = [r["name"] for r in store.skills_search(T, "quarterly zebra reports")]
    assert "alpha-skill" in hits and "manual-skill" not in hits
    listed = {s["name"]: s for s in skills_store.listing(T)}
    assert listed["manual-skill"]["enabled"] is True                    # file flag untouched


# ---------------------------------------------------------------- (7) injection stays short

def test_injected_line_is_short(desk):
    skill_packs.import_skills(T, [_skill_md(name="long-desc-skill", body="quarterly body words")], full=True)
    block = inject.skills_block(T, "quarterly body words build mcp servers", compact=True)
    assert "long-desc-skill" in block
    line = [l for l in block.splitlines() if l.startswith("- long-desc-skill")][0]
    assert len(line) < 150 and line.endswith("...")


# ---------------------------------------------------------------- (8)+(9) share + legacy

def test_imported_never_nominated(desk):
    skill_packs.import_skills(T, [_skill_md()], full=True)
    for _ in range(4):
        skills_store.read(T, "mcp-builder")
    res = skill_packs.share_nominate(T, "mcp-builder")
    assert "error" in res and "imported" in res["error"]


def test_legacy_single_file_skill_unchanged(desk):
    skills_store.create(T, "deploy-flask-app", "Deploy a Flask app", "1. scp 2. restart")
    skills_store.read(T, "deploy-flask-app")
    skills_store.update(T, "deploy-flask-app", body="1. pull 2. restart")
    row = [s for s in skills_store.listing(T) if s["name"] == "deploy-flask-app"][0]
    assert "folder" not in row and row["enabled"] is True
    assert "files" not in skills_store.read(T, "deploy-flask-app")
    raw = open(skills_store.raw_path(T, "deploy-flask-app"), encoding="utf-8").read()
    assert "imported" not in raw
    ex = skill_packs.export_skills(T)
    assert ex["skills"][0]["name"] == "deploy-flask-app"


def test_routes_and_tool_schema_registered():
    import inspect

    from app.coder import service, skills_tool
    src = inspect.getsource(service)
    assert '"/skills/import-zip"' in src and '"/skills/export-zip"' in src
    enum = skills_tool.SKILL_MANAGE_SCHEMA["input_schema"]["properties"]["operations"]["items"]["properties"]["action"]["enum"]
    assert "read_file" in enum
    assert "path" in skills_tool.SKILL_MANAGE_SCHEMA["input_schema"]["properties"]["operations"]["items"]["properties"]
