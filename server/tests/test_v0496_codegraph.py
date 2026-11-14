"""v0.496.0 CODE GRAPH: Graphify as a read-only lane. A fake GitHub (httpx.MockTransport) and a fake `graphify` script
stand in, so no outside code runs; the parts that matter are ours: safe unpack, whitelist env, kill on timeout,
tenant isolation, argv safety, the optional binary, admission and registration."""
from __future__ import annotations

import io
import json
import os
import stat
import tarfile
import textwrap

import httpx
import pytest

FAKE_GRAPHIFY = textwrap.dedent('''\
    #!%(py)s
    import json, os, sys, time
    a = sys.argv[1:]
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        print("LEAK: api key visible", file=sys.stderr); sys.exit(9)
    if a[0] == "extract":
        src = a[1]; out = a[a.index("--out") + 1]
        assert "--code-only" in a
        names = sorted(os.listdir(src))
        if "SLEEP" in names: time.sleep(30)
        os.makedirs(os.path.join(out, "graphify-out"), exist_ok=True)
        json.dump({"nodes": [{"id": n} for n in names], "links": [{"source": names[0], "target": names[-1]}] if names else []},
                  open(os.path.join(out, "graphify-out", "graph.json"), "w"))
    elif a[0] == "query":
        print("QUERY " + a[1]); sys.exit(0)
    elif a[0] == "path":
        if a[1] == "nomatch": print("no node"); sys.exit(4)
        if a[1] == "ambig": print("candidates: x, y"); sys.exit(3)
        print("PATH " + a[1] + " -> " + a[2])
    elif a[0] == "explain":
        print("EXPLAIN " + a[1] + " PAN ABCPE1234F")
    elif a[0] == "affected":
        print("AFFECTED " + a[1])
    elif a[0] == "god-nodes":
        print("GOD " + a[a.index("--top") + 1])
''')


def _tar(files: dict[str, bytes], extra=()):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in files.items():
            ti = tarfile.TarInfo("repo-abc/" + name)
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
        for ti in extra:
            tf.addfile(ti)
    return buf.getvalue()


def _github(tarball: bytes, calls: list):
    def handler(req: httpx.Request) -> httpx.Response:
        calls.append((req.url.host, req.headers.get("authorization", "")))
        if req.url.host == "api.github.com":
            if "private/nope" in str(req.url) or "ghost/ghost" in str(req.url):
                return httpx.Response(404)
            return httpx.Response(302, headers={"location": "https://codeload.github.com/legacy.tar.gz/abc"})
        if req.url.host == "codeload.github.com":
            return httpx.Response(200, content=tarball)
        return httpx.Response(500)
    return httpx.MockTransport(handler)


@pytest.fixture()
def lane(env, tmp_path, monkeypatch):
    exe = tmp_path / "graphify"
    import sys
    exe.write_text(FAKE_GRAPHIFY % {"py": sys.executable})
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("GRAPHIFY_BIN", str(exe))
    from app.config import get_settings
    get_settings.cache_clear()
    from app import codegraph as cg
    calls: list = []
    cg.set_transport(_github(_tar({"a.py": b"def f(): pass\n", "b.py": b"import a\n"}), calls))
    yield cg, calls, monkeypatch
    cg.set_transport(None)
    get_settings.cache_clear()


def test_parse_repo_forms_and_refusals():
    from app import codegraph as cg
    assert cg.parse_repo("foo/bar") == ("foo/bar", "")
    assert cg.parse_repo("https://github.com/foo/bar.git", "v1") == ("foo/bar", "v1")
    for bad in ("", "foo", "../etc/passwd", "foo/bar/baz", "https://evil.com/foo/bar", "foo/../bar"):
        with pytest.raises(cg.GraphError):
            cg.parse_repo(bad)
    with pytest.raises(cg.GraphError):
        cg.parse_repo("foo/bar", "x;rm -rf")


def test_build_then_ask_roundtrip(lane):
    cg, calls, _ = lane
    r = cg.build("t1", "foo/bar")
    assert r["ok"] and r["nodes"] == 2 and r["edges"] == 1 and r["files"] == 2
    assert [h for h, _ in calls] == ["api.github.com", "codeload.github.com"]
    assert calls[1][1] == ""                                   # no Authorization header goes to codeload
    assert cg.ask("t1", "foo/bar", "query", question="how does a reach b")["answer"] == "QUERY how does a reach b"
    assert cg.ask("t1", "foo/bar", "path", a="a", b="b")["answer"] == "PATH a -> b"
    assert cg.ask("t1", "foo/bar", "affected", a="a", depth=3)["answer"] == "AFFECTED a"
    assert cg.ask("t1", "foo/bar", "god_nodes", top=5)["answer"] == "GOD 5"
    assert [g["repo"] for g in cg.list_graphs("t1")] == ["foo/bar"]


def test_source_is_deleted_only_graph_and_meta_stay(lane):
    cg, _, _ = lane
    cg.build("t1", "foo/bar")
    d = cg._graph_dir("t1", "foo/bar")
    assert sorted(p.name for p in d.iterdir()) == ["graphify-out", "meta.json"]
    assert not any(p.name.startswith(".work-") for p in cg._root("t1").iterdir())


def test_tenants_are_isolated(lane):
    cg, _, _ = lane
    cg.build("t1", "foo/bar")
    assert cg.list_graphs("t2") == []
    with pytest.raises(cg.GraphError, match="graph_build"):
        cg.ask("t2", "foo/bar", "query", question="x")


def test_exit_codes_map_to_status(lane):
    cg, _, _ = lane
    cg.build("t1", "foo/bar")
    assert cg.ask("t1", "foo/bar", "path", a="nomatch", b="z")["status"] == "no_match"
    amb = cg.ask("t1", "foo/bar", "path", a="ambig", b="z")
    assert amb["status"] == "ambiguous" and "candidates" in amb["answer"]


def test_flag_like_arguments_are_refused(lane):
    cg, _, _ = lane
    cg.build("t1", "foo/bar")
    for kw in ({"kind": "query", "question": "--graph /etc/passwd"}, {"kind": "explain", "a": "-x"},
               {"kind": "path", "a": "ok", "b": "--force"}):
        with pytest.raises(cg.GraphError):
            cg.ask("t1", "foo/bar", **kw)
    with pytest.raises(cg.GraphError):
        cg.ask("t1", "foo/bar", "query", question="")


def test_child_never_sees_api_keys(lane):
    cg, _, mp = lane
    mp.setenv("ANTHROPIC_API_KEY", "sk-secret")
    mp.setenv("OPENAI_API_KEY", "sk-secret2")
    assert cg.build("t1", "foo/bar")["ok"]                      # the fake exits 9 if it can see either key


def test_timeout_kills_the_child_and_frees_the_lock(lane):
    cg, _, mp = lane
    cg.set_transport(_github(_tar({"SLEEP": b"x", "a.py": b"x"}), []))
    mp.setenv("GRAPHIFY_BUILD_TIMEOUT_S", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(cg.GraphError, match="rok diya"):
        cg.build("t1", "foo/bar")
    assert cg._BUILD_LOCK.acquire(blocking=False)               # lock released after the failure
    cg._BUILD_LOCK.release()
    assert cg.list_graphs("t1") == []


def test_one_build_at_a_time(lane):
    cg, _, _ = lane
    assert cg._BUILD_LOCK.acquire(blocking=False)
    try:
        with pytest.raises(cg.GraphError, match="ban raha"):
            cg.build("t1", "foo/bar")
    finally:
        cg._BUILD_LOCK.release()


def test_safe_unpack_skips_links_traversal_git_and_big_files(tmp_path):
    from app import codegraph as cg
    sym = tarfile.TarInfo("repo-abc/link"); sym.type = tarfile.SYMTYPE; sym.linkname = "/etc/passwd"
    evil = tarfile.TarInfo("repo-abc/../escape.txt"); evil.size = 1
    blob = io.BytesIO()
    with tarfile.open(fileobj=blob, mode="w:gz") as tf:
        tf.addfile(sym)
        tf.addfile(evil, io.BytesIO(b"x"))
        for name, data in (("repo-abc/.git/config", b"x"), ("repo-abc/ok.py", b"print(1)\n"),
                           ("repo-abc/big.bin", b"0" * (cg.MAX_FILE_BYTES + 1))):
            ti = tarfile.TarInfo(name); ti.size = len(data); tf.addfile(ti, io.BytesIO(data))
    tarp = tmp_path / "r.tar.gz"; tarp.write_bytes(blob.getvalue())
    dest = tmp_path / "src"; dest.mkdir()
    r = cg._safe_unpack(tarp, dest, 100, 10 ** 8)
    assert sorted(p.name for p in dest.rglob("*") if p.is_file()) == ["ok.py"]
    assert not (tmp_path / "escape.txt").exists() and r["skipped"] == 1


def test_file_and_size_caps(tmp_path):
    from app import codegraph as cg
    tarp = tmp_path / "r.tar.gz"
    tarp.write_bytes(_tar({f"f{i}.py": b"x" * 10 for i in range(10)}))
    dest = tmp_path / "src"; dest.mkdir()
    r = cg._safe_unpack(tarp, dest, 3, 10 ** 8)
    assert r["files"] == 3 and r["skipped"] == 7


def test_github_404_and_private_message(lane):
    cg, _, _ = lane
    with pytest.raises(cg.GraphError, match="Developer Sahayak"):
        cg.build("t1", "ghost/ghost")


def test_download_cap(lane):
    cg, _, mp = lane
    cg.set_transport(_github(b"0" * (2 * 1024 * 1024), []))
    mp.setenv("GRAPHIFY_MAX_REPO_MB", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(cg.GraphError, match="MB se bada"):
        cg.build("t1", "foo/bar")


def test_private_repo_uses_her_developer_token_only_toward_api_github(lane):
    cg, calls, mp = lane
    mp.setattr(cg, "_token", lambda tenant: "ghp_hertoken")
    cg.build("t1", "foo/bar")
    assert calls[0] == ("api.github.com", "Bearer ghp_hertoken") and calls[1][1] == ""


def test_keep_five_repos_oldest_dropped(lane):
    cg, _, mp = lane
    mp.setenv("GRAPHIFY_KEEP_REPOS", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    import time
    for n in ("a/one", "a/two", "a/three"):
        cg.build("t1", n)
        time.sleep(0.05)
    assert [g["repo"] for g in cg.list_graphs("t1")] == ["a/three", "a/two"]


def test_missing_binary_is_a_calm_message(env, monkeypatch, tmp_path):
    monkeypatch.setenv("GRAPHIFY_BIN", str(tmp_path / "nope"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app import codegraph as cg
    with pytest.raises(cg.GraphError, match="pip install graphifyy"):
        cg.build("t1", "foo/bar")
    with pytest.raises(cg.GraphError, match="pip install graphifyy"):
        cg.ask("t1", "foo/bar", "query", question="x")
    get_settings.cache_clear()


def test_kill_switch(lane):
    cg, _, mp = lane
    mp.setenv("GRAPHIFY_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(cg.GraphError, match="band"):
        cg.build("t1", "foo/bar")


def test_tools_registered_and_family():
    from app.agent.tools import FAMILY_OF, HANDLERS, TOOL_LABELS, TOOLS
    names = {"graph_build", "graph_ask", "graph_list"}
    assert names <= {t["name"] for t in TOOLS} and names <= set(HANDLERS) and names <= set(TOOL_LABELS)
    assert {FAMILY_OF[n] for n in names} == {"graph"}


def test_handlers_end_to_end_and_toolerror(lane):
    import asyncio
    from app.agent.tools import Ctx, ToolError
    from app.agent import graph_tools as gt
    ctx = Ctx(tenant_id="t9", conversation_id="c")
    r = asyncio.run(gt.graph_build(ctx, repo="foo/bar"))
    assert r["ok"]
    a = asyncio.run(gt.graph_ask(ctx, repo="foo/bar", kind="explain", a="a"))
    assert "ABCPE1234F" not in a["answer"]                      # id numbers masked like every tool
    assert asyncio.run(gt.graph_list(ctx))["count"] == 1
    with pytest.raises(ToolError):
        asyncio.run(gt.graph_ask(ctx, repo="foo/bar", kind="query", question="--force"))


def test_admission_phrases_and_no_chart_false_positive():
    from app.agent import admit
    for t in ("Map this repo github.com/foo/bar", "who calls the login function", "what depends on the payment module",
              "is repo ka naksha banao", "show me the knowledge graph", "graphify the codebase"):
        assert "graph" in admit._match(t.lower()), t
    for t in ("make a bar graph of my sales", "dashboard graph banao", "build a website for my shop", "hello"):
        assert "graph" not in admit._match(t.lower()), t


def test_card_has_graph_asks():
    from app.quality import tool_asks as T
    assert T.check() == [] and len([a for a in T.ASKS if a["id"].startswith("graph_")]) >= 5


def test_config_defaults():
    from app.config import get_settings
    s = get_settings()
    assert s.graphify_enabled is True and s.graphify_max_repo_mb == 80 and s.graphify_keep_repos == 5


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.912.0"
