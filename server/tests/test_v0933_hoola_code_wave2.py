"""v0.933 HOOLA CODE WAVE 2 (owner: "GO WAVE 2" on the deep check): the repo's libraries installed in the box, sessions
with an open pull request never cut off it, fix-vs-explain words, Windows line endings kept, the push tap in the
background and a push retry that reuses its branch."""
import pathlib
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- fix vs explain
def test_fix_words_beat_read_words_and_thanks_is_not_work():
    from app.devsahayak import service as S
    assert S.guess_kind("login page dekho aur theek karo") == "fix"
    assert S.guess_kind("checkout 500 error deta hai, dekho") == "fix"
    assert S.guess_kind("read all fnw ai node project first properly") == "explain"
    assert S.guess_kind("go through the repo and summarise it") == "explain"
    assert not S.wants_change("thanks!") and not S.wants_change("what about the tests?")
    assert S.wants_change("yes, fix it") and S.wants_change("haan") and S.wants_change("add a dark mode")
    src = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert 'if t.kind == "explain" and wants_change(clean):' in src


# ---------------------------------------------------------------- line endings
def _tools(d):
    from app.devsahayak import engine as EN

    class S:
        pass
    s = S()
    s.repo, s.meta = d, {}
    s.real = lambda rel: d / rel
    s.save_meta = lambda: None
    t = EN.Tools.__new__(EN.Tools)
    t.s, t.read, t.hidden, t.trail = s, set(), set(), []
    t._rel = lambda p: p
    t._guard_write = lambda rel: ""
    return t


def test_a_windows_file_keeps_its_line_endings():
    from app.devsahayak import engine as EN
    d = pathlib.Path(tempfile.mkdtemp())
    t = _tools(d)
    (d / "a.txt").write_bytes(b"one\r\ntwo\r\nthree\r\n")
    t.read.add("a.txt")
    assert t.t_edit("a.txt", "two", "TWO").startswith("Edited")
    assert (d / "a.txt").read_bytes() == b"one\r\nTWO\r\nthree\r\n"           # one line changed, not the whole file
    assert t.t_edit("a.txt", "one\r\nTWO", "1\r\n2").startswith("Edited")
    assert (d / "a.txt").read_bytes() == b"1\r\n2\r\nthree\r\n"
    t.t_write("a.txt", "x\ny\n")
    assert (d / "a.txt").read_bytes() == b"x\r\ny\r\n"
    (d / "u.txt").write_bytes(b"a\nb\n")
    t.read.add("u.txt")
    t.t_edit("u.txt", "b", "c")
    assert (d / "u.txt").read_bytes() == b"a\nc\n"                          # a Unix file stays Unix
    assert EN._lines("p\x0cq\nr\n") == ["p\x0cq", "r"]                       # a form feed is not a new line
    long = "x" * 2500
    (d / "l.txt").write_text(long + "\n")
    assert "line cut: 2500 chars" in t.t_read("l.txt")


# ---------------------------------------------------------------- the box
def test_setup_runs_by_itself_and_node_modules_reach_a_new_copy(monkeypatch):
    from app.devlab import box
    from app.devlab import service as LS
    from app.devsahayak import engine as EN
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "package.json").write_text("{}")
    t = _tools(d)
    t.image, t.hers, t.spec = "", {}, {"setup": "npm ci", "confirm": True, "deps_key": "k1"}
    monkeypatch.setattr(box, "available", lambda: {"ok": True, "base_built": True, "base_stale": False})
    monkeypatch.setattr(LS, "snapshot", lambda *a, **k: {"ok": True, "image": "hoola-devlab:r-k1", "cached": True})
    ran = []
    monkeypatch.setattr(box, "run_in", lambda img, wd, cmd, **k: ran.append((img, cmd, k.get("network"))) or {"rc": 0})
    img, note = t._image()
    assert img == "hoola-devlab:r-k1" and "installed" in note
    assert ran and "npm ci" in ran[0][1] and ran[0][2] is True              # installed into THIS working copy
    # her own switch off + a setup only read from the repo = nothing installed, said
    monkeypatch.setenv("DEV_AUTO_SETUP", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    t.image = ""
    img, note = t._image()
    assert img == box.BASE_IMAGE and "NOT installed" in note
    get_settings.cache_clear()


def test_a_missing_base_image_is_built_and_a_failed_build_is_said(monkeypatch):
    from app.devlab import box
    d = pathlib.Path(tempfile.mkdtemp())
    t = _tools(d)
    t.image, t.hers, t.spec = "", {}, {}
    monkeypatch.setattr(box, "available", lambda: {"ok": True, "base_built": False, "base_stale": False})
    monkeypatch.setattr(box, "build_base", lambda nocache=False: {"ok": False, "why": "no disk"})
    img, note = t._image()
    assert img == "" and "could not be built" in note
    built = []
    monkeypatch.setattr(box, "build_base", lambda nocache=False: built.append(nocache) or {"ok": True})
    img, _ = t._image()
    assert img == box.BASE_IMAGE and built == [False]
    t.image = "hoola-devlab:gone"                                          # a pruned snapshot is rebuilt, not run
    monkeypatch.setattr(box, "has_image", lambda tag: False)
    monkeypatch.setattr(box, "available", lambda: {"ok": True, "base_built": True, "base_stale": False})
    img, _ = t._image()
    assert img == box.BASE_IMAGE


def test_default_setups_no_longer_hide_a_failed_install():
    from app.devlab import spec
    for lang in ("python", "go", "rust"):
        assert "|| true" not in spec.LANGS[lang]["setup"], lang


# ---------------------------------------------------------------- sessions on a PR
def test_a_failed_round_keeps_the_session_on_its_open_pr(env):
    from app.db import session
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    with session() as s:
        a = DevTask(tenant_id="t1", repo="o/r", text="x", status="ci_running", kind="fix", pr_number=7)
        b = DevTask(tenant_id="t1", repo="o/r", text="y", status="new", kind="fix")
        s.add(a)
        s.add(b)
        s.flush()
        aid, bid = a.id, b.id
    S._fail(aid, "push was refused")
    S._fail(bid, "Qwen refused the request")
    with session() as s:
        assert s.get(DevTask, aid).status == "ci_running" and "refused" in s.get(DevTask, aid).error
        assert s.get(DevTask, bid).status == "failed"
    src = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert '"ci_running", "ready", "refused"):   # v0.933 + while CI runs' in src      # follow-ups while CI runs
    assert src.count("raise DevError(str(e)) from e  # v0.933") >= 3                    # a start never stuck at 'new'
    assert 'if t.pr_number else "cancelled"' in src


# ---------------------------------------------------------------- the push tap
def test_the_push_tap_runs_in_the_background_and_a_retry_reuses_its_branch():
    api = (ROOT / "server/app/devsahayak/api.py").read_text()
    assert 'run(S.in_background, tenant, tid, "push", hash_=' in api
    src = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert '"push": push}[what]' in src and '{"what": "push"} if what == "push"' in src
    assert "on_top = g.branch_sha(t.repo, t.branch)" in src
    assert "g.commit_files(t.repo, t.branch, on_top," in src
    assert "PR #%s already open for %s" in src


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.161"' in main
    assert "version: 0.999.161+1156" in (ROOT / "pubspec.yaml").read_text()
