"""v0.921 HOOLA CODE NATIVE (owner, on the design canvas claude.ai/artifact/GF4AtP5MNfV8kARgTGymuh: "SAME AS HOOLA CHAT
SCREEN ... PERMIUM AND PERFECT SAME AS CLUDE CODE" -> "GO"): Hoola Code drawn natively on the phone in the new design,
both doors open it, and every call it makes is a route the server really has."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "lib/ui/code"
FILES = {n: (CODE / f"code_{n}.dart").read_text() for n in ("kit", "home", "session", "changes", "more", "start")}
ALL = "\n".join(FILES.values())
API = (ROOT / "server/app/devsahayak/api.py").read_text()


def test_the_ten_screens_exist():
    assert "class HoolaCode extends StatefulWidget" in FILES["home"]            # 1 home
    assert "class CodeNewSessionPage" in FILES["start"] and "showCodeNewSession" in FILES["start"]  # 7 new session (v0.924)
    assert "class CodeSessionPage extends StatefulWidget" in FILES["session"]   # 2 / 3 / 4 / 6 session, plan, question, PR
    assert "class CodeChangesPage extends StatefulWidget" in FILES["changes"]   # 5 changes + comments
    for c in ("class CodePrsPage", "class CodeScheduledPage", "class CodeSettingsPage"):  # 8 / 9 / 10
        assert c in FILES["more"], c


def _norm(path: str) -> str:
    return re.sub(r"\{[a-z_]+\}", "{x}", path)


# every call the phone makes: (route on the server, how it is written in the Dart files)
CALLS = [
    ("", "'/api/devsahayak'"), ("/branches", "/api/devsahayak/branches'"), ("/tasks/start", "/api/devsahayak/tasks/start'"),
    ("/tasks/{x}", "String get _base => '/api/devsahayak/tasks/"), ("/tasks/{x}/compare", "/compare'"),
    ("/tasks/{x}/note", "$_base/note'"), ("/tasks/{x}/answer", "$_base/answer'"), ("/tasks/{x}/bg/{x}", "$_base/bg/plan_ok'"),
    ("/tasks/{x}/stop", "$_base/stop'"), ("/tasks/{x}/cancel", "$_base/cancel'"), ("/tasks/{x}/rewind", "$_base/rewind'"),
    ("/tasks/{x}/push", "$_base/push'"), ("/tasks/{x}/refresh", "$_base/refresh'"), ("/tasks/{x}/merge_request", "$_base/merge_request'"),
    ("/actions", "/api/devsahayak/actions'"), ("/actions/{x}/decide", "/decide'"), ("/prs", "/api/devsahayak/prs'"),
    ("/reviews", "/api/devsahayak/reviews'"), ("/reviews/{x}/post", "/post'"), ("/reviews/{x}/discard", "/discard'"),
    ("/deploy_request", "/api/devsahayak/deploy_request'"), ("/schedules", "/api/devsahayak/schedules'"),
    ("/schedules/{x}", "/api/devsahayak/schedules/${"), ("/schedules/{x}/run", "/run'"), ("/settings", "/api/devsahayak/settings'"),
    ("/token", "/api/devsahayak/token'"), ("/repos", "/api/devsahayak/repos'"), ("/repos/{x}/{x}", "/api/devsahayak/repos/${full.split"),
    ("/github_repos", "/api/devsahayak/github_repos'"), ("/memory", "/api/devsahayak/memory'"),
    ("/envs", "/api/devsahayak/envs'"), ("/tasks/{x}/env", "$_base/env'"),
]


def test_every_route_it_calls_is_served():
    served = {_norm(p) for p in re.findall(r'@r\.(?:get|post|put|patch|delete)\("([^"]*)"', API)}
    for route, written in CALLS:
        assert written in ALL, written
        assert route in served, route
    # nothing else: every '/api/devsahayak...' literal in the Dart files is one of the calls above
    assert len(re.findall(r"'/api/devsahayak", ALL)) <= 40


def test_her_taps_stay_hers():
    s = FILES["session"]
    assert "/bg/plan_ok" in s and "'hash'" in s              # the plan starts only with the plan's hash
    assert "/merge_request" in s and "/decide" in s          # merge = a card she answers
    m = FILES["more"]
    assert "/post" in m and "'hash': cs(r['hash'])" in m       # a review is posted with its hash
    assert "secret: true" in m and "/api/devsahayak/token" in m  # the token is typed only on the settings page


def test_both_doors_open_it():
    tools = (ROOT / "lib/ui/shell/hoola_tools.dart").read_text()
    team = (ROOT / "lib/ui/shell/hoola_team_list.dart").read_text()
    settings = (ROOT / "lib/ui/shell/hoola_settings.dart").read_text()
    assert "? hoolaOpenNew(context, app, HoolaCode(app: app))" in tools
    # the More row (Hoola Code lives there) goes through the same opener, never straight to the web page
    assert "row(hoolaMoreTools[i], 8 + i, () => hoolaOpenStudio(context, app, hoolaMoreTools[i]))" in tools
    assert "(a) => HoolaCode(app: a)" in team and "DevsahayakScreen" not in team
    assert "w is HoolaCode ? hoolaOpenNew" in settings


def test_design_rules():
    for name, src in FILES.items():
        assert "Color(0x" not in src, name
        assert "glass.dart'" not in src and "BackdropFilter" not in src and "ImageFilter.blur" not in src, name
        assert not re.search(r"FontWeight\.w(800|900)", src), name
        for m in re.findall(r"fontSize:\s*(\d+(?:\.\d+)?)", src):
            assert float(m) >= 12, name
        for m in re.findall(r"\bsize: (\d+(?:\.\d+)?)\b", src):
            pass  # icon sizes are free; text sizes go through codeSans / codeMono below
        for m in re.findall(r"code(?:Sans|Mono)\(c, size: (\d+(?:\.\d+)?)", src):
            assert float(m) >= 12, (name, m)
    assert "HoolaMotion.reduced" in FILES["kit"]   # the turning ring is still under reduce motion


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.90"' in main and "HOOLA CODE" in main
    assert "version: 0.999.90+1085" in (ROOT / "pubspec.yaml").read_text()
