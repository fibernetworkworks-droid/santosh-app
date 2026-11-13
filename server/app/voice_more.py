"""v0.816 TEEN AWAAZEIN - three more call engines she can pick (owner: "LETS DEPLOY ALL --- USER WILL CHOOSE THE VOICE
THEY WANT"): Grok Voice 3.0 (xAI), GPT-Live-1 (OpenAI) and Phonic 1.

Gemini Live stays the default and is NOT touched: main.py reaches these only through voiceengine.pick(), exactly like
the v0.264 OpenAI engine. Each engine is a `voice_openai.OpenAICall` (itself a `voice.Call`), so everything that is not
the wire is INHERITED unchanged: the phone protocol (the same APK works), her memory and context, the Haiku brain
behind santosh_kaam, hold / side talk on her words, OTP by voice, bol-kar-haan approvals, job news, the stall watchdog,
the turn saver, captions in time with his voice, the scorecard, drop notes and resume.

Each engine swaps only its wire, written from the vendor's own documentation (read 11 Nov 2026):
- GrokCall     wss://api.x.ai/v1/realtime - the OpenAI Realtime event names; xAI's session.update shape (voice,
               server_vad, audio/pcm 24 kHz, reasoning). Its stream carries no usage numbers: cost = minutes x the
               list price ($0.08 / min).
- GptLiveCall  wss://api.openai.com/v1/live/sessions - session.start / session.input_audio.append /
               session.output_audio.delta; full-duplex. Client delegation: when GPT-Live wants work done it opens a
               delegation, HOOLA's brain (santosh_kaam, the same Haiku path) does it, and the answer goes back as
               session.commentary.append for that delegation. Cost = usage.seconds x $0.05 / min (+ the brain as usual).
- PhonicCall   wss://api.phonic.ai/v1/sts/ws - config / audio_chunk (16 kHz in, 24 kHz out) / tool_call ->
               tool_call_output; Phonic does its own turn-taking. Cost = minutes x $0.07.

NOT VERIFIED: no live call has run on any of the three (no keys on the server when this was built). Details the docs
left open are marked "UNVERIFIED" below; the first real call of each engine is the test.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from types import SimpleNamespace

from . import voice as v
from . import voice_openai as vo
from .config import get_settings

log = logging.getLogger("santosh.voice.more")

GROK_URL = "wss://api.x.ai/v1/realtime?model={model}"
GPTLIVE_URL = "wss://api.openai.com/v1/live/sessions"
PHONIC_URL = "wss://api.phonic.ai/v1/sts/ws"

# Phonic's published language ids (docs.phonic.ai supported_languages, 11 Nov 2026)
PHONIC_LANGS = {"ar", "az", "bg", "bn", "cs", "da", "de", "el", "en", "es", "fa", "fi", "fil", "fr", "gu", "he", "hi",
                "hu", "id", "it", "ja", "ka", "km", "kn", "ko", "lt", "lv", "ml", "mr", "ms", "ne", "nl", "no", "pa",
                "pl", "pt", "ro", "ru", "si", "sk", "sq", "sv", "sw", "ta", "te", "th", "tr", "uk", "ur", "vi", "yue",
                "zh"}
PHONIC_CHUNK = 16000 * 2 * 40 // 1000   # Phonic takes at most 40 ms per audio_chunk: 1,280 bytes of 16 kHz PCM16


async def _ws_connect(url: str, key: str):
    import websockets
    headers = {"Authorization": f"Bearer {key}"}
    try:
        ws = await websockets.connect(url, additional_headers=headers, max_size=None, open_timeout=20)
    except TypeError:   # websockets < 14
        ws = await websockets.connect(url, extra_headers=headers, max_size=None, open_timeout=20)
    return vo._Session(ws)


async def _grok_connect():
    st = get_settings()
    return await _ws_connect(GROK_URL.format(model=st.voice_grok_model), st.xai_api_key)


async def _gptlive_connect():
    return await _ws_connect(GPTLIVE_URL, get_settings().openai_api_key)


async def _phonic_connect():
    return await _ws_connect(PHONIC_URL, get_settings().phonic_api_key)


# tests swap these for scripted fakes
grok_connect = _grok_connect
gptlive_connect = _gptlive_connect
phonic_connect = _phonic_connect


class _PerMinute(vo.OpenAICall):
    """Shared by the three: no pre-rendered clips (one voice), cost counted by the minute at the call's end."""
    engine = "more"
    USD_MIN = "voice_grok_usd_min"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.stats["engine"] = self.engine
        self._billed_s: float | None = None    # the engine's own seconds count, when it sends one

    def _count(self, usage: dict) -> None:     # no token numbers on these wires
        return

    def _record_usage(self) -> None:
        from . import voiceengine
        secs = self._billed_s
        if secs is None:
            secs = (self.stats.get("ended") or time.time()) - (self.stats.get("started") or time.time())
        secs = max(0.0, float(secs))
        usd = secs / 60 * float(getattr(get_settings(), self.USD_MIN) or 0)
        self.stats["cost_usd"] = round(usd, 6)
        voiceengine.add_usage(self.tenant, usd=usd, seconds=secs, engine=self.engine)

    def _voice_name(self, field: str) -> str:
        st = get_settings()
        return getattr(st, f"{field}_f" if self.gender == "f" else f"{field}_m")


# ------------------------------------------------------------------------------------------------ Grok Voice 3.0
class GrokCall(_PerMinute):
    """xAI speaks the OpenAI Realtime event names, so the OpenAI downlink / uplink / cut-in / tool path is reused as is;
    only the connection and the session.update body differ."""
    engine = "grok"
    USD_MIN = "voice_grok_usd_min"

    async def _open(self):
        return await grok_connect()

    async def _configure(self, session, context: str, mcp_defs) -> None:
        base = vo.session_config(self, context, mcp_defs)
        body = {"instructions": base["instructions"], "voice": self._voice_name("voice_grok_voice"),
                "turn_detection": {"type": "server_vad"},
                "audio": {"input": {"format": {"type": "audio/pcm", "rate": vo.OUT_RATE}},
                          "output": {"format": {"type": "audio/pcm", "rate": vo.OUT_RATE}}},
                # Hoola's brain does the thinking behind santosh_kaam; the voice answers small talk at once
                "reasoning": {"effort": "none"},
                "tools": base["tools"]}
        await session.send({"type": "session.update", "session": body})


# ------------------------------------------------------------------------------------------------ GPT-Live-1
DELEGATE_BLOCK = (
    "HOW WORK GETS DONE ON THIS CALL: you have no tools. Wherever these instructions say 'call santosh_kaam', do this "
    "instead: Generate <|SpawnThinking|>. Hoola's brain then does the work with her exact words, and its answer comes "
    "back to you as commentary - say it in your own voice, same meaning, nothing added. Never say a thing is done "
    "before that answer says so.\n\n")


class GptLiveCall(_PerMinute):
    """OpenAI's full-duplex voice layer with Hoola's own brain behind it (client delegation)."""
    engine = "gptlive"
    USD_MIN = "voice_gptlive_usd_min"
    AUDIO_IDLE_END_S = 1.0     # his audio stopped this long and her phone has played it: his turn is over
    CUT_IN_CHARS = 6           # her words while he is still audible = she cut in (UNVERIFIED: Live sends no event)

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._started = asyncio.Event()
        self._her_since = ""        # her words since the last delegation (the ask the brain gets)
        self._deleg_seen: set[str] = set()
        self._done_s = 0.0          # seconds billed by this call's earlier Live sessions
        self._cur_s = 0.0           # ...and by the current one (usage.seconds is a running total per session)

    async def _open(self):
        self._started = asyncio.Event()
        return await gptlive_connect()

    async def _configure(self, session, context: str, mcp_defs) -> None:
        st = get_settings()
        base = vo.session_config(self, context, mcp_defs)
        await session.send({"type": "session.start", "session": {
            "model": st.voice_gptlive_model,
            "instructions": DELEGATE_BLOCK + base["instructions"],
            "audio": {"format": {"type": "audio/pcm", "rate": vo.OUT_RATE},
                      "output": {"voice": self._voice_name("voice_gptlive_voice")}},
            "delegation": {"type": "client"}}})

    async def uplink(self, session) -> None:
        try:
            await asyncio.wait_for(self._started.wait(), timeout=15)   # the docs: no audio before session.started
        except asyncio.TimeoutError:
            raise RuntimeError("GPT-Live did not start the session")
        while True:
            kind, data = await self.audio.get()
            if kind == "audio":
                self.audio_in_bytes = getattr(self, "audio_in_bytes", 0) + len(data)
                pcm, self._up_last = vo.up16to24(data, self._up_last)
                if pcm:
                    await session.send({"type": "session.input_audio.append", "audio": base64.b64encode(pcm).decode()})
            else:
                if self._quiet_pending:
                    data = "\n".join(self._quiet_pending) + "\n" + str(data)
                    self._quiet_pending.clear()
                # news / a greeting cue to SAY: commentary for the whole session (GPT-Live may say it in its own words)
                await session.send({"type": "session.commentary.append", "content": str(data)[:1500],
                                    "delegation_id": None})

    async def _tell_quietly(self, note: str, live: bool = False) -> None:
        s = self._session
        if s is None or not self._started.is_set():
            self._quiet_pending.append(note)
            del self._quiet_pending[:-6]
            return
        try:
            await s.send({"type": "session.thinking.append", "content": note[:1500], "delegation_id": None})
            v.QUIET["sent"] += 1
        except Exception:
            self._quiet_pending.append(note)
            del self._quiet_pending[:-6]

    async def _reply(self, session) -> None:      # GPT-Live decides by itself when to speak
        return

    async def _answer_tool(self, session, fc, name: str, out: dict, state: str) -> None:
        r = out.get("result") if isinstance(out, dict) else None
        if isinstance(r, dict):
            r = r.get("say") or r.get("result") or json.dumps(r, ensure_ascii=False)
        text = str(r or (out.get("note") if isinstance(out, dict) else "") or out.get("error") or "")
        if not text and isinstance(out, dict) and out.get("status") == "working":
            text = "It is still being done; I will tell her when it is finished."
        try:
            await session.send({"type": "session.commentary.append", "content": text[:1500], "delegation_id": fc.id})
        except Exception:
            log.warning("gpt-live: the brain's answer could not be delivered (session moved on)")
            self._note_result(name, out)

    async def _audio_turn_watch(self) -> None:
        """Live has no 'turn done' event: his turn ends when his audio stopped and her phone has played it."""
        while not self.closed.is_set():
            await asyncio.sleep(0.25)
            now = time.monotonic()
            if (self._turn_audio and now - self._last_model_audio >= self.AUDIO_IDLE_END_S and now >= self._play_until
                    and (self.reply_buf.strip() or self.user_buf.strip())):
                await self.finish_turn()

    async def downlink(self, session) -> str:
        watch = asyncio.create_task(self._audio_turn_watch())
        try:
            async for ev in session.events():
                t = ev.get("type") or ""
                if t == "session.started":
                    self._started.set()
                    for note in list(self._quiet_pending):
                        self._quiet_pending.remove(note)
                        await self._tell_quietly(note)
                elif t == "session.output_audio.delta":
                    data = base64.b64decode(ev.get("delta") or "")
                    if not data:
                        continue
                    self.audio_out_bytes = getattr(self, "audio_out_bytes", 0) + len(data)
                    if self.hold:
                        self._hold_turn_reply = True
                        continue
                    if not self._turn_audio:
                        self._reply_t0 = time.monotonic()
                    self._mark_audio()
                    self._hear_him(data)
                    await self.send_audio(data)
                elif t == "session.output_transcript.delta":
                    self.reply_buf += ev.get("delta") or ""
                    if not self.hold:
                        await self._caption({"type": "santosh_text", "text": self.reply_buf.strip()})
                elif t == "session.input_transcript.delta":
                    piece = ev.get("delta") or ""
                    self._her_since += piece
                    audible = self._turn_audio or time.monotonic() < self._play_until
                    if audible and len(piece.strip()) >= self.CUT_IN_CHARS and not self.hold:
                        await self._cut_in()
                    await self._heard_her(piece)
                elif t == "session.delegation.created":
                    d = ev.get("delegation") or {}
                    did = str(d.get("id") or "")
                    if not did or did in self._deleg_seen:
                        continue
                    self._deleg_seen.add(did)
                    ask = (self._her_since or self.user_buf).strip()
                    self._her_since = ""
                    fc = SimpleNamespace(name="santosh_kaam", args={"request": ask or "(she asked something - "
                                                                    "ask her again in one line)"}, id=did)
                    task = asyncio.create_task(self.run_tool(session, fc))
                    self._tools.add(task)
                    task.add_done_callback(self._tools.discard)
                elif t in ("session.usage.updated", "session.closed"):
                    secs = (ev.get("usage") or {}).get("seconds")   # this session's running total (not a step)
                    if isinstance(secs, (int, float)):
                        self._cur_s = float(secs)
                        self._billed_s = self._done_s + self._cur_s
                    if t == "session.closed":
                        log.info("call %s: gpt-live session closed (%s)", self.call_id, ev.get("reason"))
                        break
                elif t == "error":
                    err = ev.get("error") or {}
                    log.warning("call %s: GPT-Live error %s: %s", self.call_id, err.get("code"),
                                str(err.get("message"))[:200])
                    if str(err.get("code") or "") in ("invalid_api_key", "insufficient_quota", "model_not_found"):
                        raise RuntimeError(f"GPT-Live: {err.get('code')}")
        finally:
            watch.cancel()
            self._done_s += self._cur_s     # a reconnect starts a new count: keep what this session billed
            self._cur_s = 0.0
        return "reconnect"

    async def _cut_in(self) -> None:
        self.stats["interruptions"] += 1
        await self._cap_flush()
        await self.send_json({"type": "interrupted"})
        if self.reply_buf.strip():
            self._watch_false_stop(self.reply_buf.strip())
        self._play_until = 0.0
        if self.reply_buf:
            await self.finish_turn(interrupted=True)


# ------------------------------------------------------------------------------------------------ Phonic 1
KAAM_TOOL = {
    "type": "custom_websocket",
    "tool_schema": {"type": "function", "function": {
        "name": "santosh_kaam",
        "description": v.BRAIN_DELEGATE["description"],
        "parameters": {"type": "object", "properties": {"request": {"type": "string", "description": "Her exact words"}},
                       "required": ["request"], "additionalProperties": False},
        "strict": True}},
    "execution_mode": "sync",
    "tool_call_output_timeout_ms": 30000,   # Hoola's brain answers within voice_brain_wait_s (20 s) or says "working"
}


class PhonicCall(_PerMinute):
    """Phonic 1: its own turn-taking and its own tool call; Hoola's brain answers santosh_kaam."""
    engine = "phonic"
    USD_MIN = "voice_phonic_usd_min"

    def _langs(self) -> tuple[str, list[str]]:
        from . import lang as _lang
        mine = (self.lang or "en").split("-")[0].lower()
        if _lang.call_english():
            return "en", [x for x in {mine, "hi"} if x != "en" and x in PHONIC_LANGS]
        first = mine if mine in PHONIC_LANGS else "en"
        return first, ["en"] if first != "en" else ["hi"]

    async def _open(self):
        return await phonic_connect()

    async def _configure(self, session, context: str, mcp_defs) -> None:
        st = get_settings()
        base = vo.session_config(self, context, mcp_defs)
        first, more = self._langs()
        await session.send({"type": "config", "model": st.voice_phonic_model,
                            "system_prompt": base["instructions"], "voice_id": self._voice_name("voice_phonic_voice"),
                            "input_format": "pcm_16000", "output_format": "pcm_24000",
                            "default_language": first, "additional_languages": more, "multilingual_mode": "auto",
                            "turn_taking": "standard",
                            # Hoola keeps the call open until SHE hangs up (Phonic's default ends it after 3 min quiet)
                            "no_input_end_conversation_sec": 3600,
                            "tools": [KAAM_TOOL]})

    async def uplink(self, session) -> None:
        while True:
            kind, data = await self.audio.get()
            if kind == "audio":
                self.audio_in_bytes = getattr(self, "audio_in_bytes", 0) + len(data)
                pcm = data[: len(data) // 2 * 2]       # her mic is already 16 kHz: no resampling
                for i in range(0, len(pcm), PHONIC_CHUNK):
                    await session.send({"type": "audio_chunk",
                                        "audio": base64.b64encode(pcm[i:i + PHONIC_CHUNK]).decode()})
            else:
                if self._quiet_pending:
                    data = "\n".join(self._quiet_pending) + "\n" + str(data)
                    self._quiet_pending.clear()
                await session.send({"type": "generate_reply", "system_message": str(data)[:4000]})

    async def _tell_quietly(self, note: str, live: bool = False) -> None:
        s = self._session
        if s is None:
            self._quiet_pending.append(note)
            del self._quiet_pending[:-6]
            return
        try:
            await s.send({"type": "add_system_message", "system_message": note[:4000]})
            v.QUIET["sent"] += 1
        except Exception:
            self._quiet_pending.append(note)
            del self._quiet_pending[:-6]

    async def _reply(self, session) -> None:      # Phonic answers by itself after a tool output
        return

    async def _answer_tool(self, session, fc, name: str, out: dict, state: str) -> None:
        resp = json.loads(json.dumps(out, default=str))
        if self._quiet_pending and isinstance(resp, dict):
            resp["note_for_you"] = " ".join(self._quiet_pending)[:2000]
            self._quiet_pending.clear()
        try:
            await session.send({"type": "tool_call_output", "tool_call_id": fc.id,
                                "output": json.dumps(resp, ensure_ascii=False)[:20000]})
        except Exception:
            log.warning("phonic: tool result for %s could not be delivered (session moved on)", name)
            self._note_result(name, out)

    async def downlink(self, session) -> str:
        async for ev in session.events():
            t = ev.get("type") or ""
            if t == "audio_chunk":
                data = base64.b64decode(ev.get("audio") or "")
                if ev.get("text"):
                    self.reply_buf += ev["text"]
                    if not self.hold:
                        await self._caption({"type": "santosh_text", "text": self.reply_buf.strip()})
                if not data:
                    continue
                self.audio_out_bytes = getattr(self, "audio_out_bytes", 0) + len(data)
                if self.hold:
                    self._hold_turn_reply = True
                    continue
                if not self._turn_audio:
                    self._reply_t0 = time.monotonic()
                self._mark_audio()
                self._hear_him(data)
                await self.send_audio(data)
            elif t == "input_text":
                await self._heard_her((ev.get("text") or "") + " ")
            elif t == "user_started_speaking":
                self._her_t0, self._she_speaking = time.monotonic(), True
                await self._she_cut_in(session)       # no truncate on Phonic (self._item stays empty)
            elif t == "user_finished_speaking":
                self._she_speaking = False
            elif t in ("assistant_finished_speaking", "assistant_chose_not_to_respond"):
                if self.hold and (self._hold_turn_reply or self.reply_buf):
                    await self._held_turn_done()
                elif self.reply_buf.strip() or self.user_buf.strip():
                    await self.finish_turn()
            elif t == "tool_call":
                cid = str(ev.get("tool_call_id") or "")
                if cid and cid in self._seen_calls:
                    continue
                if cid:
                    self._seen_calls.add(cid)
                args = ev.get("parameters") or {}
                fc = SimpleNamespace(name=ev.get("tool_name") or "", args=args if isinstance(args, dict) else {}, id=cid)
                task = asyncio.create_task(self.run_tool(session, fc))
                self._tools.add(task)
                task.add_done_callback(self._tools.discard)
            elif t == "conversation_created":
                self.stats["phonic_conversation"] = str(ev.get("conversation_id") or "")
            elif t == "warning":
                log.info("call %s: Phonic warning %s", self.call_id, str(ev.get("warning"))[:200])
            elif t == "error":
                err = ev.get("error") or {}
                log.warning("call %s: Phonic error %s: %s", self.call_id, err.get("code"),
                            str(err.get("message"))[:200])
                if str(err.get("code") or "") in ("unauthorized", "invalid_api_key", "insufficient_credits"):
                    raise RuntimeError(f"Phonic: {err.get('code')}")
        return "reconnect"


CLASSES = {"grok": GrokCall, "gptlive": GptLiveCall, "phonic": PhonicCall}
