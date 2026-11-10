"""v0.369 KHUD TAZA (App Sahayak Phase 33): before a build is pushed, the builds repo's workflow files are compared with
the server's own copies (server/app_builder/) and updated on main when different; same files are left alone; a token
without the Workflows permission is said plainly once and the build still goes; checked at most every 10 minutes."""
import base64

import pytest


@pytest.fixture()
def gh(monkeypatch):
    from app.appmaker.android import runners as RN
    calls, files = [], {}

    def fake(method, path, payload=None, raw=False, timeout=60):
        calls.append((method, path.split("?")[0], payload))
        name = path.split("/contents/")[-1].split("?")[0] if "/contents/" in path else ""
        if method == "GET" and name:
            if name in files:
                return {"content": base64.b64encode(files[name]).decode(), "sha": "s-" + name}
            return None
        if method == "PUT" and name:
            if files.get("__deny__"):
                raise RN.BuildUnavailable(f"GitHub PUT /repos/x/contents/{name}: 403 Resource not accessible by integration")
            files[name] = base64.b64decode(payload["content"])
            return {"content": {"sha": "new"}}
        return {}
    monkeypatch.setattr(RN, "_gh", fake)
    RN.SYNC["checked_at"] = 0.0
    return RN, calls, files


def test_updates_old_and_missing_leaves_same(gh):
    RN, calls, files = gh
    build = (RN._builder_dir() / "hoola-build.yml").read_bytes()
    files[".github/workflows/hoola-build.yml"] = build                      # already current
    files[".github/workflows/hoola-ios.yml"] = b"name: old\n"               # an old copy
    out = RN.sync_workflows("me/builds", force=True)
    assert out["same"] == ["hoola-build.yml"] and out["updated"] == ["hoola-ios.yml"] and not out["error"]
    put = [c for c in calls if c[0] == "PUT"]
    assert len(put) == 1 and put[0][2]["sha"] == "s-.github/workflows/hoola-ios.yml" and put[0][2]["branch"] == "main"
    assert files[".github/workflows/hoola-ios.yml"] == (RN._builder_dir() / "hoola-ios.yml").read_bytes()
    # within 10 minutes nothing is asked again
    n = len(calls)
    RN.sync_workflows("me/builds")
    assert len(calls) == n


def test_no_workflow_permission_is_said_and_build_goes_on(gh):
    RN, calls, files = gh
    files["__deny__"] = True
    out = RN.sync_workflows("me/builds", force=True)
    assert "Workflows: Read and write" in out["error"] and out["updated"] == []


def test_push_tree_syncs_first(gh, monkeypatch, tmp_path):
    RN, calls, files = gh
    from app.appmaker.android import runners
    monkeypatch.setattr(runners, "_settings", lambda: type("S", (), {"app_build_gh_repo": "me/builds", "app_build_gh_token": "t"})())
    seen = []
    monkeypatch.setattr(runners, "sync_workflows", lambda repo, force=False: seen.append(repo) or RN.SYNC)
    (tmp_path / "a.txt").write_text("x")
    try:
        runners.push_tree(tmp_path, "k1", lambda s: None)
    except Exception:
        pass
    assert seen == ["me/builds"]
