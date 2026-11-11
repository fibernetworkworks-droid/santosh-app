"""v0.600.0 SANDARBH MANCH - the T1 reference family, backend-only (owner: "T1 Reference -- deploye
it for hoola --- only in backend for hoola ai"; built as 0.586.0, re-versioned twice onto the dev
chain - their PAISA chain took 0.586-0.588 (COLLISION #8) and their P7 HOOLA HUB took 0.589
(COLLISION #9), REBASE PROTOCOL both rounds, both kept; the file name keeps the first-build
number, the v0.566 middleware precedent).

modelcontextprotocol/servers (MIT, the T1 item of download/HOOLA_MCP_FEED.json) ported IDEA-ONLY
onto house rails as TWO ONE-tool lanes, zero upstream code: `workspace` (the filesystem role: one
confined per-tenant directory - list/read/write/edit/tree/search/info, the root is the law, edit is
exact, binary refused, symlink escapes refused) and `kgmemory` (the memory role: entities, typed
relations, text observations in per-tenant SQLite - create/relate/observe/forget/read/search/open,
no ghost refs, exact cascade-honest forgets). What is tested FOR REAL (all offline, per-tenant
stores wiped per test): the whole workspace action surface; the root law (escape, absolute path,
symlink in, symlink out, symlink at write); the exact-edit law (once / ambiguous / replace_all /
missing); the caps (read truncation, write TOO_BIG); binary refusal; kill switches stop WRITES
with reads answerable; the kg graph end to end (create dedup, relate dedup + ghost refusal,
observe dedup + cap, read with counts, search by name/type/fact, open with honest missing, forget
cascade + exact triples); tenant isolation on both lanes; unknown actions; registry 583 pin;
APP_VERSION pin.
"""
import asyncio
import shutil
from pathlib import Path

import pytest

from app.agent import sandarbh_tools as S
from app.agent.tools import Ctx, TOOLS

CTX = Ctx(tenant_id="sm-test-tenant", conversation_id="c1")
CTX2 = Ctx(tenant_id="sm-other-tenant", conversation_id="c2")


def _wipe(tenant):
    shutil.rmtree(Path("data") / "workspace" / tenant, ignore_errors=True)
    shutil.rmtree(Path("data") / "kgmemory" / tenant, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_state():
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)
    yield
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)


def ws(action="list", ctx=None, **kw):
    return asyncio.run(S.workspace(ctx or CTX, action, **kw))


def kg(action="read", ctx=None, **kw):
    return asyncio.run(S.kgmemory(ctx or CTX, action, **kw))


def seed_file(rel="notes/draft.md", text="hello sandarbh\nline two\n"):
    out = ws("write", path=rel, content=text)
    assert out["ok"], out
    return out


# ================================================================ workspace: the root law + the surface

def test_empty_list_names_the_root():
    out = ws("list")
    assert out["ok"] and out["entries"] == []
    assert out["meta"]["root"] == f"data/workspace/{CTX.tenant_id}"
    assert out["meta"]["elapsed_ms"] >= 0


def test_write_creates_parents_and_read_round_trips():
    seed_file()
    out = ws("read", path="notes/draft.md")
    assert out["ok"] and out["content"] == "hello sandarbh\nline two\n"
    assert out["meta"]["bytes"] > 0 and out["meta"]["truncated"] is False


def test_write_accepts_nonstring_content_as_json():
    out = ws("write", path="cfg.json", content={"a": 1, "b": [2, 3]})
    assert out["ok"]
    back = ws("read", path="cfg.json")
    assert back["ok"] and '"a": 1' in back["content"]


def test_read_missing_and_read_directory_are_honest():
    assert ws("read", path="nope.md")["error"]["code"] == "NOT_FOUND"
    seed_file()
    assert ws("read", path="notes")["error"]["code"] == "BAD_INPUT"


def test_read_refuses_binary_instead_of_garbling():
    p = Path("data") / "workspace" / CTX.tenant_id / "blob.bin"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"ok\x00\x01\x02binary")
    out = ws("read", path="blob.bin")
    assert out["error"]["code"] == "BAD_INPUT" and "text" in out["error"]["message"].lower()


def test_read_truncates_past_the_cap():
    # the file arrives bigger than the read cap (placed by hand or by an older lane, not by the
    # capped write action) - read serves the head and says truncated
    p = Path("data") / "workspace" / CTX.tenant_id / "big.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("a" * (S._MAX_READ_BYTES + 50), encoding="utf-8")
    out = ws("read", path="big.txt")
    assert out["meta"]["truncated"] is True and len(out["content"]) == S._MAX_READ_BYTES


def test_write_past_the_cap_is_TOO_BIG_and_writes_nothing():
    out = ws("write", path="huge.txt", content="a" * (S._MAX_WRITE_BYTES + 1))
    assert out["error"]["code"] == "TOO_BIG"
    assert not (Path("data") / "workspace" / CTX.tenant_id / "huge.txt").exists()


def test_edit_replaces_exactly_once():
    seed_file(text="alpha beta gamma")
    out = ws("edit", path="notes/draft.md", old_string="beta", new_string="BETA")
    assert out["ok"] and out["meta"]["replacements"] == 1
    assert ws("read", path="notes/draft.md")["content"] == "alpha BETA gamma"


def test_edit_ambiguous_string_is_refused_unless_replace_all():
    seed_file(text="x y x z")
    out = ws("edit", path="notes/draft.md", old_string="x", new_string="X")
    assert out["error"]["code"] == "CONFLICT" and "2" in out["error"]["message"]
    out2 = ws("edit", path="notes/draft.md", old_string="x", new_string="X", replace_all=True)
    assert out2["ok"] and out2["meta"]["replacements"] == 2


def test_edit_missing_string_and_missing_file():
    seed_file()
    assert ws("edit", path="notes/draft.md", old_string="absent", new_string="x")["error"]["code"] == "NOT_FOUND"
    assert ws("edit", path="ghost.md", old_string="a", new_string="b")["error"]["code"] == "NOT_FOUND"


def test_dotdot_escape_is_refused_and_writes_nothing_outside():
    out = ws("write", path="../escaped.txt", content="no")
    assert out["error"]["code"] == "BAD_INPUT"
    assert not (Path("data") / "workspace" / "escaped.txt").exists()
    assert ws("read", path="../secrets.txt")["error"]["code"] == "BAD_INPUT"


def test_absolute_path_is_refused():
    out = ws("read", path="/etc/passwd")
    assert out["error"]["code"] == "BAD_INPUT"


def test_symlink_escape_is_refused():
    root = Path("data") / "workspace" / CTX.tenant_id
    outside = Path("data") / "workspace" / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    link = root / "leak.txt"
    link.parent.mkdir(parents=True, exist_ok=True)
    inside = root / "real.txt"
    inside.write_text("inside text", encoding="utf-8")
    link2 = root / "alias.txt"
    try:
        link.symlink_to(outside.resolve())
        out = ws("read", path="leak.txt")
        assert out["error"]["code"] == "BAD_INPUT" and "secret" not in str(out.get("content", ""))
        # a symlink whose escape leaves the root: refused before anything is touched
        out2 = ws("write", path="leak.txt", content="smuggle")
        assert out2["error"]["code"] == "BAD_INPUT"
        # a symlink that stays inside the root: write through it still refused (CONFLICT)
        link2.symlink_to(inside)
        out3 = ws("write", path="alias.txt", content="overwrite via link")
        assert out3["error"]["code"] == "CONFLICT"
        assert inside.read_text(encoding="utf-8") == "inside text"
    finally:
        link.unlink(missing_ok=True)
        link2.unlink(missing_ok=True)
        outside.unlink(missing_ok=True)


def test_search_matches_names_case_insensitively():
    seed_file("reports/Q4 notes.md", "data")
    ws("write", path="reports/summary.md", content="x")
    out = ws("search", pattern="q4")
    assert out["ok"] and any(m["path"] == "reports/Q4 notes.md" for m in out["matches"])
    assert all("reports/summary" != m["path"] or "q4" in m["path"] for m in out["matches"])


def test_tree_walks_and_types():
    seed_file("a/b/c/deep.txt", "d")
    out = ws("tree")
    paths = {n["path"]: n["type"] for n in out["nodes"]}
    assert paths.get("a") == "dir" and paths.get("a/b/c/deep.txt") == "file"


def test_info_describes_and_missing_is_not_found():
    seed_file()
    out = ws("info", path="notes/draft.md")
    assert out["ok"] and out["info"]["type"] == "file" and out["info"]["size"] > 0
    assert out["info"]["modified_at"]
    assert ws("info", path="nope")["error"]["code"] == "NOT_FOUND"
    root_info = ws("info", path="")
    assert root_info["ok"] and root_info["info"]["type"] == "dir"


def test_list_missing_dir_and_list_of_file():
    assert ws("list", path="ghost-dir")["error"]["code"] == "NOT_FOUND"
    seed_file()
    assert ws("list", path="notes/draft.md")["error"]["code"] == "BAD_INPUT"


def test_workspace_kill_switch_stops_writes_reads_stay_answerable(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "workspace_enabled", False, raising=False)
    assert ws("write", path="x.txt", content="y")["error"]["code"] == "NEED_SETUP"
    assert ws("edit", path="x.txt", old_string="a", new_string="b")["error"]["code"] == "NEED_SETUP"
    assert ws("list")["ok"] and ws("search", pattern="x")["ok"]


def test_tenant_isolation_workspace():
    seed_file("private.md", "tenant one secret")
    out = asyncio.run(S.workspace(CTX2, "read", path="private.md"))
    assert out["error"]["code"] == "NOT_FOUND"


def test_unknown_workspace_action():
    out = ws("delete")
    assert out["error"]["code"] == "BAD_INPUT" and "list" in out["error"]["message"]


# ================================================================ kgmemory: the knowledge graph

def _create_two():
    out = kg("create", entities=[{"name": "Sharma Traders", "type": "client"},
                                  {"name": "GST filing", "type": "task"}])
    assert out["ok"] and out["meta"]["created"] == 2
    return out


def test_create_entities_and_dedup():
    out = _create_two()
    assert {e["name"] for e in out["entities"]} == {"GST filing", "Sharma Traders"}
    again = kg("create", entities=[{"name": "Sharma Traders", "type": "client"}])
    assert again["ok"] and again["meta"]["created"] == 0 and again["meta"]["kept"] == 1


def test_create_bad_input():
    assert kg("create", entities=[])["error"]["code"] == "BAD_INPUT"
    assert kg("create", entities=[{"type": "no name"}])["error"]["code"] == "BAD_INPUT"
    assert kg("create", entities=[{"name": "x"}] * (S._MAX_ENTITIES_CALL + 1))["error"]["code"] == "BAD_INPUT"


def test_relate_refuses_ghost_refs():
    kg("create", entities=[{"name": "A", "type": "t"}])
    out = kg("relate", relations=[{"from": "A", "to": "GHOST", "kind": "knows"}])
    assert out["error"]["code"] == "NOT_FOUND" and "create" in out["error"]["hint"]


def test_relate_adds_and_dedups():
    _create_two()
    out = kg("relate", relations=[{"from": "Sharma Traders", "to": "GST filing", "kind": "needs"}])
    assert out["ok"] and out["meta"]["added"] == 1 and out["added"][0]["kind"] == "needs"
    again = kg("relate", relations=[{"from": "Sharma Traders", "to": "GST filing", "kind": "needs"}])
    assert again["ok"] and again["meta"]["added"] == 0 and again["meta"]["kept"] == 1


def test_relate_bad_and_missing_fields():
    _create_two()
    assert kg("relate", relations=[{"from": "Sharma Traders", "to": "GST filing"}])["error"]["code"] == "BAD_INPUT"
    assert kg("relate", relations=[{"from": "Nobody", "to": "GST filing", "kind": "x"}])["error"]["code"] == "NOT_FOUND"


def test_observe_requires_existing_entity_and_dedups():
    out = kg("observe", observations=[{"entity": "GHOST", "contents": ["fact"]}])
    assert out["error"]["code"] == "NOT_FOUND"
    _create_two()
    ok = kg("observe", observations=[{"entity": "Sharma Traders", "contents": ["Uses Tally", "Uses Tally", "Pays on 5th"]}])
    assert ok["ok"] and ok["meta"]["added"] == 2 and ok["meta"]["kept"] == 1


def test_observe_cap_and_empty():
    _create_two()
    long = "x" * (S._MAX_OBS_TEXT + 1)
    assert kg("observe", observations=[{"entity": "Sharma Traders", "contents": [long]}])["error"]["code"] == "BAD_INPUT"
    assert kg("observe", observations=[{"entity": "Sharma Traders", "contents": ["", "  "]}])["error"]["code"] == "BAD_INPUT"


def test_read_shows_the_whole_graph_with_counts():
    _create_two()
    kg("relate", relations=[{"from": "Sharma Traders", "to": "GST filing", "kind": "needs"}])
    kg("observe", observations=[{"entity": "Sharma Traders", "contents": ["Uses Tally"]}])
    out = kg("read")
    assert out["ok"] and out["meta"]["entities"] == 2 and out["meta"]["relations"] == 1
    sharma = next(e for e in out["entities"] if e["name"] == "Sharma Traders")
    assert sharma["observations"] == ["Uses Tally"]
    assert out["relations"] == [{"from": "Sharma Traders", "to": "GST filing", "kind": "needs"}]


def test_search_finds_by_name_type_and_fact():
    _create_two()
    kg("observe", observations=[{"entity": "Sharma Traders", "contents": ["Uses Tally for books"]}])
    by_name = kg("search", query="sharma")
    assert by_name["meta"]["matches"] == 1
    by_type = kg("search", query="task")
    assert [e["name"] for e in by_type["entities"]] == ["GST filing"]
    by_fact = kg("search", query="tally")
    assert by_fact["meta"]["matches"] == 1


def test_open_exact_with_honest_missing():
    _create_two()
    out = kg("open", names=["Sharma Traders", "NOPE"])
    assert out["ok"] and out["meta"]["found"] == 1 and out["meta"]["missing"] == ["NOPE"]
    assert kg("open", names=[])["error"]["code"] == "BAD_INPUT"


def test_forget_entity_cascades_and_says_so():
    _create_two()
    kg("relate", relations=[{"from": "Sharma Traders", "to": "GST filing", "kind": "needs"}])
    kg("observe", observations=[{"entity": "Sharma Traders", "contents": ["Uses Tally"]}])
    out = kg("forget", entities=["Sharma Traders"])
    assert out["ok"] and out["deleted"]["entities"] == ["Sharma Traders"]
    assert out["meta"]["cascade"] and "relations" in out["meta"]["cascade"]
    after = kg("read")
    assert after["meta"]["entities"] == 1 and after["meta"]["relations"] == 0
    assert after["meta"]["observations"] == 0


def test_forget_exact_triples_and_facts():
    _create_two()
    kg("relate", relations=[{"from": "Sharma Traders", "to": "GST filing", "kind": "needs"},
                            {"from": "Sharma Traders", "to": "GST filing", "kind": "pays"}])
    kg("observe", observations=[{"entity": "Sharma Traders", "contents": ["F1", "F2"]}])
    out = kg("forget", relations=[{"from": "Sharma Traders", "to": "GST filing", "kind": "pays"}])
    assert out["deleted"]["relations"] == 1
    out2 = kg("forget", observations=[{"entity": "Sharma Traders", "contents": ["F1"]}])
    assert out2["deleted"]["observations"] == 1
    left = kg("read")
    assert left["meta"]["relations"] == 1 and left["meta"]["observations"] == 1
    assert next(e for e in left["entities"] if e["name"] == "Sharma Traders")["observations"] == ["F2"]


def test_kgmemory_kill_switch_stops_writes_reads_stay_answerable(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "kgmemory_enabled", False, raising=False)
    for act, kw in (("create", {"entities": [{"name": "X", "type": "t"}]}),
                    ("relate", {"relations": [{"from": "X", "to": "Y", "kind": "k"}]}),
                    ("observe", {"observations": [{"entity": "X", "contents": ["f"]}]}),
                    ("forget", {"entities": ["X"]})):
        out = kg(act, **kw)
        assert out["error"]["code"] == "NEED_SETUP", act
    assert kg("read")["ok"] and kg("search", query="x")["ok"] and kg("open", names=["X"])["ok"]


def test_tenant_isolation_kg():
    _create_two()
    other = asyncio.run(S.kgmemory(CTX2, "read"))
    assert other["ok"] and other["meta"]["entities"] == 0


def test_unknown_kg_action():
    assert kg("wipe")["error"]["code"] == "BAD_INPUT"


# ================================================================ registry + version pins

def test_registry_583():
    names = [t["name"] for t in TOOLS]
    assert len(TOOLS) == 622, "617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " + ("581 (the v0.585 base incl. reach + speckit) + 2 sandarbh "
                               "(v0.586 SANDARBH MANCH: workspace + kgmemory, the T1 reference family)")
    assert names.count("workspace") == 1 and names.count("kgmemory") == 1


def test_tools_are_registered_with_families_and_handlers():
    from app.agent import tools as T
    assert T.FAMILY_OF.get("workspace") == "workspace"
    assert T.FAMILY_OF.get("kgmemory") == "kgmemory"
    assert T.HANDLERS["workspace"] is S.workspace and T.HANDLERS["kgmemory"] is S.kgmemory
    for tool in (T.TOOLS[[t["name"] for t in T.TOOLS].index("workspace")],
                 T.TOOLS[[t["name"] for t in T.TOOLS].index("kgmemory")]):
        assert tool["input_schema"]["properties"]["action"]["type"] == "string"
        assert isinstance(tool["input_schema"]["properties"]["action"]["enum"], list)


def test_app_version_pin():
    import app.main as M
    assert M.APP_VERSION == "0.768.0"
