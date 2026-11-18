"""v0.884 CHROME SAAF: Hoola's own PC Chrome set up for portals and saying why a page did not open."""
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _agent(tmp_path):
    os.environ["HOOLA_DATA"] = str(tmp_path)
    sys.path.insert(0, str(ROOT / "desktop-linux"))
    spec = importlib.util.spec_from_file_location("hoola_agent_v0884", ROOT / "desktop-linux" / "agent.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_classify_names_every_stop(tmp_path):
    a = _agent(tmp_path)
    c = a.classify
    assert c({"ready": "complete", "href": "https://x.gov.in/", "title": "Home", "text": "Welcome"}) == ""
    assert c({"ready": "loading", "href": "https://x.gov.in/", "title": "", "text": ""}) == "slow"
    assert c({"error": "TimeoutError"}) == "no_answer"
    assert c({"ready": "complete", "href": "chrome-error://chromewebdata/", "title": "parivahan.gov.in",
              "text": "This site can't be reached\nERR_CONNECTION_TIMED_OUT"}) == "net:ERR_CONNECTION_TIMED_OUT"
    assert c({"ready": "complete", "href": "chrome-error://chromewebdata/", "title": "Privacy error",
              "text": "Your connection is not private NET::ERR_CERT_DATE_INVALID"}) == "certificate"
    assert c({"ready": "complete", "href": "https://a.gov.in/", "title": "Access Denied",
              "text": "You don't have permission to access"}) == "blocked"
    assert c({"ready": "complete", "href": "https://a.in/", "title": "Just a moment...", "text": ""}) == "bot_check"
    # a long real page that merely mentions 'forbidden' is NOT a block page
    assert c({"ready": "complete", "href": "https://a.in/", "title": "Rules",
              "text": "Smoking is forbidden in the office. " * 60}) == ""


def test_hints_never_click_past_a_certificate(tmp_path):
    a = _agent(tmp_path)
    assert "HER PC" in a.hint_for("blocked") and "Retrying will not help" in a.hint_for("blocked")
    assert "does not click past" in a.hint_for("certificate")
    assert "ERR_CONNECTION_TIMED_OUT" in a.hint_for("net:ERR_CONNECTION_TIMED_OUT")
    assert "do NOT open" in a.hint_for("slow")
    src = (ROOT / "desktop-linux" / "agent.py").read_text()
    assert "ignore-certificate-errors" not in src and "setIgnoreCertificateErrors" not in src


def test_chrome_is_indian_and_portal_ready(tmp_path):
    a = _agent(tmp_path)
    assert a.TZ_NAME == "Asia/Kolkata" and a.LANG == "en-IN"
    assert "HER PC" in a.hint_for("no_page")
    assert a.POLICY["DefaultPopupsSetting"] == 1 and a.POLICY["PromptForDownloadLocation"] is False
    assert a.POLICY["DownloadDirectory"].endswith("Downloads") and a.POLICY["PasswordManagerEnabled"] is False
    src = (ROOT / "desktop-linux" / "agent.py").read_text()
    for flag in ("--lang={LANG}", "--accept-lang={ACCEPT_LANG}", "--disable-popup-blocking",
                 "--disable-background-timer-throttling"):
        assert flag in src
    assert '"TZ": TZ_NAME' in src and a.VERSION >= "1.5.1"
    dk = (ROOT / "desktop-linux" / "Dockerfile").read_text()
    assert "ENV TZ=Asia/Kolkata" in dk and "tzdata" in dk


def test_policy_written(tmp_path, monkeypatch):
    a = _agent(tmp_path)
    monkeypatch.setattr(a, "POLICY_DIRS", (str(tmp_path / "pol"),))
    a._write_policy()
    import json
    assert json.loads((tmp_path / "pol" / "hoola.json").read_text())["DefaultPopupsSetting"] == 1


def test_open_url_waits_reuses_and_caps_tabs(tmp_path):
    a = _agent(tmp_path)
    assert a.OPEN_WAIT == 30 and a.TAB_CAP == 6
    src = (ROOT / "desktop-linux" / "agent.py").read_text()
    assert '"Page.navigate"' in src and "_trim_tabs(tid)" in src and "retried once" in src
    assert 'sys.argv[1] == "check"' in src


def test_operator_passes_the_problem_on():
    src = (ROOT / "server" / "app" / "pc" / "operator.py").read_text()
    assert "PROBLEM: {r.get('problem')}" in src
    assert "PORTALS (v0.884)" in src and "never click past the warning" in src
    ops = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert "python /app/agent.py check" in ops


def test_blank_tab_at_deadline_is_no_page(tmp_path, monkeypatch):
    a = _agent(tmp_path)
    acts = a.Actions()
    monkeypatch.setattr(acts, "_target", lambda tid: {"id": tid})
    monkeypatch.setattr(a, "_state", lambda t: {"ready": "complete", "href": "about:blank", "title": "", "text": ""})
    monkeypatch.setattr(a.time, "sleep", lambda s: None)
    st, problem = acts._settle("x", a.time.time() + 0.05)
    assert problem == "no_page"
