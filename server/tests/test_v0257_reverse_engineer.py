"""v0.257 REVERSE-ENGINEER ANYTHING with REA (owner: "I TOLD HOOLA TO READ THIS EXE FILE END TO END AND EXTRACT
ENDPOINTS BUT AGAIN HOOLA OPENS ITS OWN PC INSTEAD OF USING REA", "REVERSE ENGINEER ANYTHING", "REA ALREADY DEVELOPED
FOR HOOLA").

Root cause: no word in her ask loaded REA (rea_khoj's only keys were 'rea khoj' / 'khoj'), its description was dieted
to one sentence, and REA's allowed tools had no way to list endpoints - so Hoola reached for the cloud PC. Fixes:
the REVERSE-ENGINEER intent loads REA for any program / app / package / model / firmware file; rea_khoj gains
action=endpoints (static, in Python, never runs the file, works without the REA engine, secrets masked, full list as a
data-desk dataset); a PC call for such a job is refused with the REA route; TOOL CHOOSER + the REA guide say so.
"""
import asyncio
import io
import zipfile

import pytest

from tests.test_appcheck import _file
from tests.test_life import conv_ctx


def _st():
    from app.config import get_settings
    return get_settings()


EXE = (b"MZ\x90\x00" + b"\x00" * 60 + b"This program cannot be run in DOS mode\x00\x00" +
       b"https://api.acme-corp.com/v2/orders?id=1\x00\x00" +
       "https://telemetry.acme-corp.com/collect?api_key=AIzaSyA1234567890abcdefghijklmnopqrstu".encode("utf-16le") +
       b"\x00\x00/api/v1/login\x00\x00wss://push.acme-corp.com:8443/socket\x00\x00update.acmecdn.net\x00" +
       b"\x00ftp://user:hunter22@files.acme-corp.com/pub\x00\x00 10.20.30.40:8080 \x00 999.1.1.1 \x00" +
       b"KERNEL32.dll\x00System.Net.Http\x00 https://api.acme-corp.com/v2/orders?id=1 \x00")


@pytest.fixture
def ds(env, tmp_path, monkeypatch):
    monkeypatch.setenv("DATASETS_DIR", str(tmp_path / "ds"))
    monkeypatch.setenv("REA_HOME", str(tmp_path / "rea_home"))
    from app.config import get_settings
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


# ---------------------------------------------------------------- the extractor (pure, static)
def test_extract_finds_urls_paths_hosts_ips_and_masks_secrets(tmp_path):
    from app.appcheck import endpoints as ep
    p = tmp_path / "acme.exe"
    p.write_bytes(EXE)
    res = ep.extract(p, "acme.exe", "exe")
    f = res["found"]
    urls = set(f["url"])
    assert "https://api.acme-corp.com/v2/orders?id=1" in urls and f["url"]["https://api.acme-corp.com/v2/orders?id=1"]["count"] == 2
    assert "wss://push.acme-corp.com:8443/socket" in urls
    tele = next(u for u in urls if "telemetry" in u)                  # a UTF-16 string (.NET / Windows) is read too
    assert tele.endswith("api_key=***") and "AIza" not in tele        # a key inside a URL never leaves masked
    assert any(u.startswith("ftp://***:***@files.acme-corp.com") for u in urls)   # user:password masked
    assert "/api/v1/login" in f["api_path"]
    assert "update.acmecdn.net" in f["host"]
    assert "api.acme-corp.com" not in f["host"]                       # already inside a URL: not listed twice
    assert "KERNEL32.dll" not in f["host"] and "System.Net.Http" not in f["host"]
    assert "10.20.30.40:8080" in f["ip"] and not any(i.startswith("999") for i in f["ip"])
    assert any("never run" in x for x in res["limits"])


def test_extract_reads_inside_an_apk_and_names_the_member(tmp_path):
    from app.appcheck import endpoints as ep
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("AndroidManifest.xml", b"x")
        z.writestr("classes.dex", b"dex\n035\x00https://api.notes.example.com/v1/sync\x00")
        z.writestr("assets/config.json", b'{"base": "https://cdn.notes.example.com/assets"}')
        z.writestr("res/icon.png", b"https://never.read.example.com/x")
    p = tmp_path / "notes.apk"
    p.write_bytes(b.getvalue())
    res = ep.extract(p, "notes.apk", "apk")
    assert res["found"]["url"]["https://api.notes.example.com/v1/sync"]["where"] == "classes.dex"
    assert "https://cdn.notes.example.com/assets" in res["found"]["url"]
    assert not any("never.read" in u for u in res["found"]["url"])    # pictures / fonts are skipped
    rows = ep.rows_of(res["found"])
    assert {"kind", "value", "host", "count", "found_in"} <= set(rows[0])


# ---------------------------------------------------------------- rea_khoj action=endpoints
def test_rea_khoj_endpoints_saves_a_dataset_without_the_rea_engine(ds):
    from app import datasets
    from app.agent.tools import dispatch
    from app.appcheck import khoj
    assert not khoj.configured()                                      # no REA binary here: endpoints still works
    ctx = conv_ctx()
    fid = _file("acme.exe", EXE)
    out = asyncio.run(dispatch("rea_khoj", {"action": "endpoints", "file_id": fid}, ctx))
    assert out["kind"] == "exe" and out["counts"]["url"] >= 4 and out["counts"]["api_path"] >= 1
    assert "api.acme-corp.com" in out["top_hosts"]
    assert out["dataset"].startswith("ds_") and "doc_studio data=" in out["next"]
    doc = datasets.load("default", out["dataset"])
    assert doc["columns"][:3] == ["kind", "value", "host"] and doc["count"] == sum(out["counts"].values())
    assert "AIza" not in str(doc)                                     # the saved file is masked too


def test_rea_khoj_endpoints_says_so_when_nothing_is_written_in_plain_text(ds):
    from app.agent.tools import dispatch
    ctx = conv_ctx()
    fid = _file("packed.exe", b"MZ" + bytes(range(256)) * 40)
    out = asyncio.run(dispatch("rea_khoj", {"action": "endpoints", "file_id": fid}, ctx))
    assert sum(out["counts"].values()) == 0 and "dataset" not in out and "plainly" in out["next"]


def test_rea_tool_tells_the_model_about_endpoints_in_its_first_sentence():
    from app.agent import tools as reg
    t = next(x for x in reg.TOOLS if x["name"] == "rea_khoj")
    assert "endpoints" in t["description"] and ".exe" in t["description"]       # survives the 140-char diet
    assert "endpoints" in t["input_schema"]["properties"]["action"]["enum"]


# ---------------------------------------------------------------- routing: REA for anything to reverse-engineer
@pytest.mark.parametrize("text", [
    "Read this exe file end to end and extract endpoints",
    "IS EXE FILE KO END TO END PADHO AUR ENDPOINTS NIKALO",
    "REVERSE ENGINEER this app",
    "Is APK ke andar kaun se API hain",
    "yeh app ka login feature kaise kaam karta hai",
    "decompile this dll",
    "yeh model.gguf kya karta hai",
    "is firmware.bin ke endpoints nikalo",
    "Is wasm file ko decompile karo",
    "yeh .deb package kya install karta hai",
])
def test_reverse_engineering_asks_load_rea_and_never_the_pc(text):
    from app.agent import admit
    plan = admit.plan_for(text, _st())
    names = {t["name"] for t in plan.specs()}
    assert "rea_khoj" in names and "data_read" in names
    assert "hoola_pc_do" not in names and "pc_do" not in names


@pytest.mark.parametrize("text", ["Swiggy se biryani mangwa do", "Mera resume PDF banao", "Kal ki train kaun si hai",
                                  "Google Sheet mein row add karo", "Rent agreement padh ke batao"])
def test_everyday_asks_do_not_load_rea(text):
    from app.agent import admit
    assert "rea" not in admit.plan_for(text, _st()).families


def test_tool_chooser_and_rea_guide_point_reverse_engineering_to_rea():
    from app.agent import prompts
    slim = prompts.system_text(["core"])
    assert "REVERSE-ENGINEER ANYTHING" in slim and "never the cloud PC" in slim
    rea = prompts.system_text(["rea"])
    assert "action=endpoints when she wants" in rea


# ---------------------------------------------------------------- the pick check
class _Ctx:
    tenant_id, conversation_id, user_id, actor = "t1", "c-rea", "u1", "owner"

    def __init__(self, place=""):
        self.place = place
        self.admit = None


def test_a_program_file_sent_to_the_cloud_pc_is_refused_with_the_rea_route(env):
    from app.agent import pick, where
    from app.agent.tools import ToolError
    where.forget("c-rea")
    for task in ("Install binutils and run strings on acme.exe to extract endpoints",
                 "decompile notes.apk with jadx", "reverse engineer this firmware image"):
        with pytest.raises(ToolError) as e:
            pick.check("hoola_pc_do", {"task": task}, _Ctx())
        assert "rea_khoj" in str(e.value) and "action=endpoints" in str(e.value)
    where._WORK["c-rea"] = ("hoolapc", __import__("time").time())    # an old cloud-PC lock in the chat is not her word
    with pytest.raises(ToolError):
        pick.check("hoola_pc_do", {"task": "extract endpoints from the exe"}, _Ctx())
    pick.check("hoola_pc_do", {"task": "run this exe on your PC and screenshot it"}, _Ctx(place="hoolapc"))  # she said so
    where.forget("c-rea")


def test_tool_set_has_reverse_engineering_asks():
    from app.quality import tool_asks as T, toolchoice as C
    rea = [a for a in T.ASKS if a["id"].startswith("rea_")]
    assert len(rea) >= 6 and all(a["ok"] == ["rea_khoj"] for a in rea)
    card = C.router_card(rea)
    assert card["right_in_view"] == len(rea) and card["wrong_loaded"] == 0


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.271.0"
