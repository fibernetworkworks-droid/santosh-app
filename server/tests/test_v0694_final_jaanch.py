"""FINAL JAANCH (owner: "NOW GO AGAIN DEEP CHECK THE HOOLA ALL PARAMETERS FUNCTIONING GOOD OR NOT AND MAKE IT READY FOR
FINAL PERFECT TESTING").

1 the AI video studio keeps its own family (the construction Studio desk's names overwrote it)
2 a skill pack whose installs crashed is NOT stamped done for ever - the next open retries
3 the Leads free card counts only asks that name a tool
"""
from __future__ import annotations


def test_video_studio_has_its_own_family():
    from app.agent.tools import FAMILY_OF, TOOLS
    from app.agent import admit
    from app.config import get_settings
    assert FAMILY_OF["video_studio"] == "studio" and FAMILY_OF["const_studio"] == "cstudio"
    assert [t["name"] for t in TOOLS if FAMILY_OF.get(t["name"]) is None] == ["haan_karo"]
    view = {t["name"] for t in admit.plan_for("ai video banao diwali ka", get_settings()).specs()}
    assert "video_studio" in view and "const_studio" not in view
    calm = {t["name"] for t in admit.plan_for("namaste kaise ho", get_settings()).specs()}
    assert "video_studio" not in calm
    assert "cstudio" in admit.route("site visualisation ka shot brief banao")


def test_a_failed_pack_install_is_retried(env, monkeypatch):
    from app.coder import skill_packs, skills_store, store
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "coder_enabled", True)
    tenant = "t-retry"
    store.ensure()
    real = skills_store.install
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise RuntimeError("disk hiccup")
    monkeypatch.setattr(skills_store, "install", boom)
    skill_packs.seed_claude(tenant)
    stamp = skill_packs.CLAUDE_STAMP.format(tenant)
    assert calls["n"] > 0 and not store.is_consumed(stamp)          # left open
    monkeypatch.setattr(skills_store, "install", real)
    out = skill_packs.seed_claude(tenant)
    assert out["claude_seeded"] > 0 and store.is_consumed(stamp)     # the retry installs and stamps


def test_leads_card_counts_only_tool_asks():
    from app.quality import leadscard as LC
    card = LC.free_card()
    line = LC.lines(card)[0]
    assert f"{card['right_in_view']}/{card['tool_asks']}" in line and "rule asks" in line
