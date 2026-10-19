"""Hoola avatar: owner names their AI coworker, picks male / female and a voice, and sets Mere Niyam."""
import asyncio

import pytest
from fastapi.testclient import TestClient


def test_defaults_and_save(env):
    from app.avatar import service as av
    a = av.get("default")
    assert a["app"] == "Hoola" and a["name"] == "Santosh" and a["gender"] == "m" and a["voice"] == "Puck"
    assert a["setup_done"] is False and a["rules"]["accept"]["payment_request"] == "ask"
    a = av.save("default", name="  Priya ", gender="f", setup_done=True)
    assert a["name"] == "Priya" and a["voice"] == "Kore" and a["setup_done"]
    assert av.save("default", voice="Aoede")["voice"] == "Aoede"
    with pytest.raises(av.AvatarError):
        av.save("default", voice="Puck")                    # a male voice for a female avatar
    assert av.save("default", name="सखी")["name"] == "सखी"     # any Indian script


@pytest.mark.parametrize("bad", ["SBI", "Cyber Cell", "x", "R2D2", "Police Help", "a" * 21, "Hoola"])
def test_bad_names(env, bad):
    from app.avatar import service as av
    with pytest.raises(av.AvatarError):
        av.save("default", name=bad)


def test_rules_safety_limits(env):
    from app.avatar import service as av
    a = av.save("default", rules={"knock": "anyone", "accept": {"payment_request": "auto", "app_file": "auto", "file": "auto"},
                                   "share": {"phone": True}, "quiet": {"from": "23:00", "to": "7am"}, "vip": "Mummy, Swati",
                                   "language": "Marathi", "junk": 1})
    r = a["rules"]
    assert r["knock"] == "anyone" and r["accept"]["file"] == "auto"
    assert r["accept"]["payment_request"] == "ask" and r["accept"]["app_file"] == "ask"   # never automatic
    assert r["share"]["phone"] is True and r["quiet"]["from"] == "23:00" and r["quiet"]["to"] == "08:00"
    assert r["vip"] == ["Mummy", "Swati"] and r["language"] == "marathi" and "junk" not in r
    assert any("paise sirf mere tap se" in line for line in a["rules_summary"])


def test_gendered_and_prompts(env):
    from app.avatar import service as av
    assert av.gendered("Video dekh raha hoon, main samajh gaya", "f") == "Video dekh rahi hoon, main samajh gayi"
    assert av.gendered("Video dekh raha hoon", "m") == "Video dekh raha hoon"
    av.save("default", name="Meera", gender="f")
    from app.agent.prompts import system_prompt
    p = system_prompt(True, "", "default")
    assert p.startswith("You are Meera,") and "Hoola Notebook" in p and "kar rahi hoon" in p
    assert "[Santosh worker update]" in p
    from app.voice import persona_prompt
    vp = persona_prompt("Meera", "f").format(lang="hi-IN", now="now", context="ctx")
    assert "You are Meera" in vp and "Indian woman" in vp and "You are female" in vp and vp.rstrip().endswith("ctx")


def test_api_and_parse(env, monkeypatch):
    from app import artifacts
    async def fake(system, prompt, max_tokens=1500):
        assert "data from the user" in system
        return '{"vip": ["Family"], "quiet": {"on": true, "from": "23:00", "to": "07:30"}, "accept": {"payment_request": "auto"}}'
    monkeypatch.setattr(artifacts, "_llm", fake)
    from app import main
    with TestClient(main.app) as c:
        assert c.get("/healthz").json()["app"] == "Hoola"
        assert c.put("/api/avatar", json={"name": "Raju", "gender": "m", "setup_done": True}).json()["name"] == "Raju"
        assert c.put("/api/avatar", json={"name": "RBI"}).status_code == 400
        p = c.post("/api/avatar/rules/parse", json={"text": "family VIP, raat 11 se subah 7:30 tak shaanti"}).json()
        assert p["rules"]["vip"] == ["Family"] and p["rules"]["quiet"]["to"] == "07:30"
        assert p["rules"]["accept"]["payment_request"] == "ask"
        assert c.get("/api/avatar").json()["rules"]["vip"] == []           # parse never saves
        saved = c.put("/api/avatar", json={"rules": p["rules"]}).json()
        assert saved["rules"]["vip"] == ["Family"]
    _ = asyncio
