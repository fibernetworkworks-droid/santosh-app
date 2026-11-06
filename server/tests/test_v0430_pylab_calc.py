"""v0.430 SOCH KE JAWAB step 3 - every worked-out number comes from real code (owner: "GO STEP 3").

The check: no calculator in chat. pylab (the locked Python sandbox of the Shiksha suite: pandas, numpy, scipy, statsmodels,
matplotlib, openpyxl; no network, no secrets, no server files, CPU / memory / time limits) already existed but lived in the
Shiksha family - in view for 1 of 50 hard asks - so EMIs, CAGRs, break-evens and forecasts were mental maths. Now
admit.calc_needed puts pylab in view for every hard ask, data job and calculation ask (adm.extra, not the whole Shiksha
family); a hard ask found by the judge gets it too; its description opens with CALCULATOR + ANALYSIS and the pinned TOOL
CHOOSER says "a number you work out = pylab, never mental maths".
"""
import asyncio

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, txt  # noqa: F401


def _st():
    from app.config import get_settings
    return get_settings()


def _names(text):
    from app.agent import admit
    return {t["name"] for t in admit.plan_for(text, _st()).specs()}


def test_every_hard_ask_sees_pylab_and_no_everyday_ask_does():
    from app.quality.hard_asks import EASY, HARD, HOLDOUT_EASY
    assert all("pylab" in _names(a["text"]) for a in HARD)
    assert not [t for t in EASY + HOLDOUT_EASY if "pylab" in _names(t)]


@pytest.mark.parametrize("text", ["In numbers ka average aur median nikalo", "Sales ka growth rate calculate karo",
                                  "Is data ka chart bana do", "18% GST jod ke total kitna hoga 4,500 pe",
                                  "GitHub ke top 50 repos ki list do"])
def test_calculation_and_data_asks_see_pylab(text):
    assert "pylab" in _names(text)


def test_only_pylab_comes_not_the_whole_school_suite():
    names = _names("20 lakh ke home loan ki EMI kitni banegi 9% pe 20 saal")
    assert "pylab" in names and "pathyakram" not in names and "shiksha" not in names


def test_a_hard_turn_hands_pylab_to_the_model(gz, monkeypatch):  # noqa: F811
    brain = _set_brain(monkeypatch, FakeBrain([([txt("EMI ...")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(gz["conv"], "Calculate the ROI if I invest 5 lakh in a solar plant that saves 9,000 a month",
                         tenant_id="default"))
    assert "pylab" in {t["name"] for t in brain.seen[-1]["tools"]}
    assert "never mental maths" in str(brain.seen[-1]["system"])


def test_a_judge_found_hard_ask_gets_pylab(gz, monkeypatch):  # noqa: F811
    from app.agent import hard
    text = "Hamare employees jaldi naukri chhod rahe hain, HR data dekh ke pattern samjhao zara"

    async def decide(t, st):
        return {"hard": True, "by": "judge", "why": []}
    monkeypatch.setattr(hard, "decide", decide)
    assert "pylab" not in _names(text)                         # the rules alone would not load it
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Pattern ...")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(gz["conv"], text, tenant_id="default"))
    assert "pylab" in {t["name"] for t in brain.seen[-1]["tools"]}


def test_pylab_computes_her_csv_in_the_sandbox(env):
    from app.agent.tools import Ctx, dispatch
    from app.mailbox import service as ms
    fid = ms.store_bytes("default", "sales.csv", b"month,sales\nJan,100\nFeb,120\nMar,90\nApr,150\n", "mail").id
    code = ("import pandas as pd\nd = pd.read_csv('sales.csv')\n"
            "print(d.sales.sum(), round(d.sales.mean(), 2), d.loc[d.sales.idxmax(), 'month'])")
    out = asyncio.run(dispatch("pylab", {"code": code, "file_ids": [fid], "purpose": "sales summary"},
                               Ctx("default", "c-pl")))
    assert out["ok"] and out["stdout"].split() == ["460", "115.0", "Apr"]


def test_pylab_gets_the_emi_right(env):
    from app.agent.tools import Ctx, dispatch
    code = ("P = 2000000; r = 0.09 / 12; n = 240\nemi = P * r * (1 + r) ** n / ((1 + r) ** n - 1)\n"
            "print(round(emi, 2), round(emi * n - P, 2))")
    out = asyncio.run(dispatch("pylab", {"code": code, "purpose": "EMI"}, Ctx("default", "c-pl")))
    assert out["ok"] and out["stdout"].split() == ["17994.52", "2318684.59"]


def test_the_sandbox_has_no_network(env):
    from app.agent.tools import Ctx, dispatch
    code = "import socket\ns = socket.socket()\ns.connect(('1.1.1.1', 80))\nprint('LEAK')"
    out = asyncio.run(dispatch("pylab", {"code": code, "purpose": "net check"}, Ctx("default", "c-pl")))
    assert not out["ok"] and "LEAK" not in out.get("stdout", "")


def test_what_the_model_reads():
    from app.agent import prompts, tools as reg
    d = next(t for t in reg.TOOLS if t["name"] == "pylab")["description"]
    assert d.startswith("CALCULATOR + ANALYSIS") and "never mental maths" in d
    assert "A number you WORK OUT" in prompts.system_text(["core"])


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.639.0"
