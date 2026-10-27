"""Santosh Browser, Santosh side: browse_web results, the confirm card for a paused submit, payment/login hand-off
and the background follower. The worker itself (browser-use + Chromium) is tested in browser_worker/test_worker.py."""
import asyncio
import time

import pytest

from tests.test_bazar import _events, _notices, bz  # noqa: F401


class FakeWorker:
    def __init__(self):
        self.state = {}
        self.calls = []

    def __call__(self, method, path, *, json=None, params=None, timeout=30):
        self.calls.append((method, path, json, params))
        if method == "POST" and path == "/tasks":
            return dict(self.state["start"])
        if method == "GET":
            sid = path.rsplit("/", 1)[1]
            if params["tenant"] != self.state.get("tenant", "default"):
                from app.browser import BrowserError
                raise BrowserError("no such browser task")
            return dict(self.state.get("get", self.state["start"]), session_id=sid)
        if path.endswith("/approve"):
            self.state["get"] = self.state["after"]
            return {"session_id": "s1", "status": "running"}
        raise AssertionError(path)


@pytest.fixture
def fw(bz, monkeypatch):  # noqa: F811
    monkeypatch.setenv("BROWSER_WORKER_URL", "http://127.0.0.1:8079")
    monkeypatch.setenv("BROWSER_WORKER_KEY", "k" * 32)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from app import browser
    from app.config import get_settings
    get_settings.cache_clear()
    w = FakeWorker()
    monkeypatch.setattr(browser, "_call", w)
    yield w, bz
    get_settings.cache_clear()


def run_tool(conv, **args):
    from app.agent.tools import Ctx
    from app.agent.web_tools import browse_web
    return asyncio.run(browse_web(Ctx("default", conv), **args))


def test_answer_comes_back(fw):
    w, bz = fw
    w.state["start"] = {"session_id": "s1", "status": "done", "summary": "Birth certificate fee is Rs 25.",
                        "url": "https://akolamc.gov.in/fees", "title": "Fees", "steps": 3}
    out = run_tool(bz["conv"], task="birth certificate fee in Akola", start_url="akolamc.gov.in")
    assert out["status"] == "done" and "Rs 25" in out["answer"]
    assert [e["status"] for e in _events(bz["conv"], "browser")] == ["running", "done"]
    sent = w.calls[0][2]
    assert sent["start_url"] == "https://akolamc.gov.in" and sent["llm"]["provider"] == "anthropic"
    assert sent["llm"]["api_key"] == "sk-test"


def test_submit_needs_tap_then_result_arrives(fw):
    w, bz = fw
    conv, svc = bz["conv"], bz["svc"]
    w.state["start"] = {"session_id": "s1", "status": "needs_confirm", "url": "https://akolamc.gov.in/apply",
                        "pending": {"id": "p1", "label": "Submit application", "url": "https://akolamc.gov.in/apply"}}
    w.state["after"] = {"status": "done", "summary": "Application received, number AKL-778.", "url": "https://akolamc.gov.in/done"}
    out = run_tool(conv, task="apply for birth certificate for Meghana")
    assert out["needs_approval"]
    card = _events(conv, "bazar_approval")[-1]
    assert card["title"] == "akolamc.gov.in: 'Submit application'" and card["amount_paise"] == 0
    assert not any(c[1].endswith("/approve") for c in w.calls)          # nothing clicked before the tap
    with pytest.raises(Exception):
        svc.decide("someone-else", card["id"], "approve")                 # only the owner can approve
    svc.decide("default", card["id"], "approve")
    assert ("POST", "/tasks/s1/approve", {"tenant": "default", "pending_id": "p1", "wait_seconds": 0}, None) in w.calls
    for _ in range(50):
        if any("AKL-778" in (n or "") for n in _notices(conv)):
            break
        time.sleep(0.1)
    assert any("AKL-778" in (n or "") for n in _notices(conv))


def test_model_cannot_fake_a_pending_step(fw):
    w, bz = fw
    w.state["start"] = {"session_id": "s1", "status": "done", "summary": "ok"}
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError):
        bz["svc"].run("default", bz["conv"], "santosh-browser", "confirm_step", {"session_id": "s1"})


def test_payment_and_login_go_to_the_phone(fw):
    w, bz = fw
    conv = bz["conv"]
    w.state["start"] = {"session_id": "s1", "status": "needs_payment", "url": "https://mahadiscom.in/pay",
                        "reason": "'Pay now' is a payment step", "summary": "Bill Rs 540 is ready to pay."}
    out = run_tool(conv, task="pay my electricity bill")
    assert out["status"] == "needs_payment" and "Open button" in out["say"]
    btn = _events(conv, "bazar_open")[-1]
    assert btn["url"] == "https://mahadiscom.in/pay" and btn["pack"] == "Santosh Browser"


def test_running_task_reports_later(fw, monkeypatch):
    w, bz = fw
    conv = bz["conv"]
    monkeypatch.setenv("BROWSER_WAIT_SECONDS", "0")
    from app.config import get_settings
    get_settings.cache_clear()
    w.state["start"] = {"session_id": "s9", "status": "running"}
    w.state["get"] = {"status": "done", "summary": "PNR 4512 is CONFIRMED, coach B2."}
    heard = []
    import app.voice as voice
    monkeypatch.setattr(voice, "inject", lambda c, text: heard.append((c, text)) or 1)
    out = run_tool(conv, task="check PNR 4512")
    assert out["status"] == "running" and "browse_result" in out["say"] and out["session_id"] == "s9"
    live = _events(conv, "browser")
    assert live and live[0]["session_id"] == "s9" and live[0]["status"] == "running"   # live card at once
    for _ in range(50):
        if any("CONFIRMED" in (n or "") for n in _notices(conv)):
            break
        time.sleep(0.1)
    assert any("CONFIRMED" in (n or "") for n in _notices(conv))
    assert heard and heard[0][0] == conv and "CONFIRMED" in heard[0][1]      # a live call hears it too
    from app.agent.tools import Ctx
    from app.agent.web_tools import browse_result
    r = asyncio.run(browse_result(Ctx("default", conv), session_id="s9"))
    assert r["status"] == "done" and "CONFIRMED" in r["answer"]


def test_off_when_not_configured(bz, monkeypatch):  # noqa: F811
    monkeypatch.delenv("BROWSER_WORKER_URL", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent.tools import ToolError
    with pytest.raises(ToolError, match="isn't switched on"):
        run_tool(bz["conv"], task="check something on a site")
