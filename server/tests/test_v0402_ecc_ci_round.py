"""v0.402 a red CI round on her draft PR gets the ECC fixer specialist (picked by language) only when dev_spec_fix is on."""
from tests.test_tech_devsahayak import T, dev  # noqa: F401
from tests.test_v0352_pehle_ci import FIX_ANSWER, _run, cidev  # noqa: F401


def _red_round(S, monkeypatch, on):
    from app.config import get_settings
    from app.devsahayak import loop as L
    v = S.start(T, "fix", "Checkout crash ho raha hai", conv="c1")
    _run(S.FAKE, S.FAKE.prs[1]["head"]["sha"], "failure")
    monkeypatch.setattr(get_settings(), "dev_loop", True, raising=False)
    monkeypatch.setattr(get_settings(), "dev_spec_fix", on, raising=False)
    seen = {}

    def run(*a, **k):
        seen.update(k)
        raise L.LoopUnavailable("scripted: fall back to the one-shot fix")
    monkeypatch.setattr(L, "run", run)
    S._ci_step(T, v["id"])
    return seen


def test_ci_fix_round_specialist_on(cidev, monkeypatch):  # noqa: F811
    seen = _red_round(cidev, monkeypatch, True)
    assert "CI FIX SPECIALIST" in seen["system_extra"] and "PYTHON fixes" in seen["system_extra"]
    assert "<ci_log>" in seen["extra"]


def test_ci_fix_round_specialist_off(cidev, monkeypatch):  # noqa: F811
    seen = _red_round(cidev, monkeypatch, False)
    assert seen["system_extra"] == ""
