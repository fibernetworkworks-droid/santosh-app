"""v0.230 VOICE PHASE 3 - natural conversation (owner: 'START PHASE 3 IN PARALLEL WITH TEST').

1. One quiet-aware news queue (Call.push_news): a job's result / kaamwatch line / auto-rescue waits for a real
   pause (both quiet), several go as ONE note, the same news is never told twice, and it never waits forever.
2. Diet: the call persona drops every line about tools that are not in the call (41.7k -> ~22k chars), and the
   document / admin tools go through santosh_kaam (152 -> ~103 declared tools, 82k -> ~54k chars of JSON).
3. Murmurs ("haan... achha...") only in a breath INSIDE her long sentence - never at the end of her turn, where they
   used to land on top of his answer.
"""
import asyncio
import json
import re
import time

from app import voice


def _call(env):
    return voice.Call(None, "conv-p3", "Puck", "hi-IN", env["settings"].tenant_id)


def _texts(c):
    return [d for k, d in list(c.audio._queue) if k == "text"]


def test_news_waits_for_a_pause_then_goes(env):
    async def go():
        c = _call(env)
        c.NEWS_QUIET_S = 0.2
        c._last_voice_at = time.monotonic()            # she is talking right now
        c.user_buf = "aur phir maine socha ki"
        c.push_news("(Woh bada kaam ho gaya: GST return ka draft taiyar hai)")
        await asyncio.sleep(0.45)
        during = _texts(c)
        c.user_buf = ""                                # her turn ended
        c._last_voice_at = time.monotonic() - 1
        c._last_user_text_at = time.monotonic() - 1
        await asyncio.sleep(0.5)
        return during, _texts(c)
    during, after = asyncio.run(go())
    assert during == []                                 # never over her sentence
    assert len(after) == 1 and "GST return" in after[0]


def test_news_is_merged_and_never_told_twice(env):
    async def go():
        c = _call(env)
        c._last_voice_at = time.monotonic()            # busy: both wait
        c.push_news("(Woh bada kaam ho gaya: Riya ka blouse order D-0012 save ho gaya)")
        c.push_news("[Kaam update, tell her briefly] Darzi: Riya ka blouse order D-0012 save ho gaya")   # same news
        c.push_news("(Woh bada kaam ho gaya: bijli bill ka card bhej diya, 1240 rupaye)")
        c.NEWS_QUIET_S = 0.1
        c._last_voice_at = c._last_user_text_at = time.monotonic() - 1
        await asyncio.sleep(0.5)
        c.push_news("Riya ka blouse order D-0012 save ho gaya")                                        # told already
        await asyncio.sleep(0.4)
        return c, _texts(c)
    c, texts = asyncio.run(go())
    assert len(texts) == 1 and "blouse" in texts[0] and "bijli" in texts[0] and "ek-ek karke" in texts[0]
    assert c.stats["news_deduped"] == 2 and c.stats["news_merged"] == 1


def test_news_never_waits_forever(env):
    async def go():
        c = _call(env)
        c.NEWS_MAX_WAIT_S = 0.3
        c._last_voice_at = time.monotonic() + 60       # she talks and talks
        c.push_news("(kaam ho gaya: ticket book)")
        await asyncio.sleep(0.7)
        return _texts(c)
    assert len(asyncio.run(go())) == 1


def test_inject_routes_job_news_through_the_queue(env):
    async def go():
        c = _call(env)
        loop = asyncio.get_running_loop()
        voice.ACTIVE.setdefault("conv-p3", []).append((loop, c))
        try:
            c._last_voice_at = time.monotonic()        # she is talking: nothing may go out yet
            assert voice.inject("conv-p3", "[Kaam update] video taiyar hai") == 1
            await asyncio.sleep(0.1)
            return c
        finally:
            voice.ACTIVE.pop("conv-p3", None)
    c = asyncio.run(go())
    assert c._news and _texts(c) == []


def test_news_left_at_the_end_is_kept_for_the_next_call(env):
    from app import yaad
    c = _call(env)
    c.closed.set()
    c.push_news("(Woh bada kaam ho gaya: website live hai)")
    assert "website live" in yaad.take_call_followup(c.conv, 720)


def test_persona_diet(env):
    p = voice.PERSONA
    assert len(p) < 26000                               # was 41.7k
    declared = {t["name"] for t in voice._tool_specs()}
    via = voice.VOICE_VIA_KAAM | {n + "_dekho" for n in voice.VOICE_VIA_KAAM}
    for ln in p.split("\n"):
        if not ln.startswith("- ") or ln.startswith(("- Slow tools", "- Business work in a call", "- Running jobs")):
            continue
        names = set(re.findall(r"\b([a-z][a-z0-9_]{2,})\b", ln))
        assert not ((names & via) and not ((names & declared) - {"santosh_kaam"})), ln[:80]
    assert "santosh_kaam" in p and "wedding" in p      # the routing line names the moved work
    voice.persona_prompt("Santosh", "m").format(lang="Hinglish", now="x", context="y")


def test_tool_diet(env):
    specs = voice._tool_specs()
    assert len(specs) <= 110 and sum(len(json.dumps(t)) for t in specs) < 60000
    names = {t["name"] for t in specs}
    for moved in ("form_create", "slides_add", "make_document", "pdf_tools", "email_accounts"):
        assert moved not in names and voice.via_kaam(moved)
    for kept in ("create_reminder", "email_check", "email_draft", "calendar_add_event", "browse_web", "pc_do",
                 "youtube_play", "music_control", "haan_karo", "santosh_kaam", "side_talk"):
        assert kept in names, kept


class _Fake:
    BC_AFTER_S, BC_MIN_WORDS, BC_WINDOW_S, BC_END_MARGIN_S = 0.05, 4, 0.6, 0.15

    def __init__(self, quiet_s):
        now = time.monotonic()
        self.closed, self.hold = __import__("threading").Event(), ""
        self.stats = {"backchannels": 0}
        self._last_voice_at = now - quiet_s
        self._last_user_text_at = now - quiet_s
        self._last_model_audio = 0.0
        self._turn_audio = False
        self.user_buf = "suno na kal maine dukaan pe ek naya kaam shuru kiya tha aur"
        self._bc_this_turn, self._bc_at, self._last_ack, self._last_bc_i = 0, 0.0, 0.0, -1
        self.voice, self.gender, self.sent = "Puck", "m", []

    def _bc_end_s(self):
        return 0.55

    async def send_audio(self, data):
        self.sent.append(data)


def _pool(monkeypatch):
    monkeypatch.setattr(voice, "pool_clips", lambda kind, v, g: [b"m"])
    monkeypatch.setenv("VOICE_BACKCHANNEL", "true")


def test_murmur_in_a_breath_inside_her_sentence(env, monkeypatch):
    _pool(monkeypatch)
    c = _Fake(0.0)                                     # she just spoke: the watch waits for her breath
    c._last_user_text_at = time.monotonic() - 0.3      # her last words were already transcribed
    asyncio.run(voice.Call._bc_watch(c))
    assert c.sent == [b"m"]


def test_no_murmur_at_the_end_of_her_turn(env, monkeypatch):
    _pool(monkeypatch)
    c = _Fake(0.9)                                     # her pause is already past her end-of-turn wait
    asyncio.run(voice.Call._bc_watch(c))
    assert c.sent == []


def test_no_murmur_on_a_short_turn(env, monkeypatch):
    _pool(monkeypatch)
    c = _Fake(0.0)
    c.user_buf = "haan theek hai"
    asyncio.run(voice.Call._bc_watch(c))
    assert c.sent == []
    assert voice.Call.BC_MIN_WORDS == 10 and voice.Call.BC_AFTER_S < 0.55


def test_version():
    from app import main
    assert main.APP_VERSION == "0.250.0"
