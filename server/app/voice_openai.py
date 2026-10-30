"""v0.264 OPENAI VOICE - the "real voice" engine (owner: "KEEP EXISTING VOICE INTACT ... IF USER WANT REAL VOICE THEY CAN
USE OPENAI LEVEL ... IF GEMINI THEN GEMINI LEVEL").

`OpenAICall` is a `voice.Call` that talks to OpenAI's Realtime API (gpt-realtime-2.1-mini) instead of Gemini Live.
Everything that is not the wire is INHERITED unchanged: the phone protocol (the same APK works), hold / side talk,
OTP by voice, bol-kar-haan approvals, job news at a pause, acks / murmurs, the stall watchdog, the turn saver, her
language state, the scorecard, the drop note and resume. Only five pieces are OpenAI's own:
- `run()`      connect -> session.update (persona + her context + tools) -> greeting -> up / down / watchdog; a fresh
               session after a drop or before OpenAI's 60-minute limit (memory rides in the context + the reseed);
- `uplink()`   her 16 kHz mic -> 24 kHz (OpenAI accepts only 24 kHz PCM) -> input_audio_buffer.append; a text note ->
               a system message (+ response.create when he is not already answering);
- `downlink()` OpenAI's events -> the same handlers Gemini's events reach (captions, audio, interruptions, tools,
               turn end); his cut-off reply is truncated where she stopped hearing it;
- `_answer_tool()` the tool result as a function_call_output (+ response.create when free);
- `_record_usage()` exact cost from every response.done (tokens, cached tokens), counted for the month's budget.
The Gemini engine (`voice.Call`) is not touched by any of this: main.py picks OpenAI only through voiceengine.pick().
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import time
from array import array
from types import SimpleNamespace

from . import voice as v
from .config import get_settings

log = logging.getLogger("santosh.voice.openai")

URL = "wss://api.openai.com/v1/realtime?model={model}"

# Real voice = how a person sounds, written as BEHAVIOUR (never as tags: the model would read "[laughs]" aloud).
# v0.265 SAANS AUR HMM (owner after the trial: "NEED WORK ON BREATH AND HMM's"): the block now sits at the TOP (right
# after the language lock; at the end of a 24k persona that says "answer first / short / no preamble" ten times it lost),
# says plainly that a "hmm" before the answer is NOT a preamble, gives numbers and spoken examples. (v0.265's per-reply
# delivery cues were removed in v0.267: starting each reply ourselves broke turn-taking.)
# v0.266 ASLI SAANS: asked in WORDS to breathe, the model SAID "main saans le rahi hoon". Nothing here mentions breathing
# any more - the breath is a real sound the server plays (app/breath.py); the words only carry the spoken sounds.
EMOTION = (
    "AWAAZ MEIN JAAN (real voice) - yeh sabse pehle:\n"
    "- Tum ek asli insaan ki tarah phone par baat karte ho: sochte ho, kabhi ek pal ruk ke bolte ho.\n"
    "- Sochna: yaad karte ya sochte waqt jawab 'hmm...', 'uhh...' ya 'achha...' se shuru hota hai - takreeban har "
    "teesre jawab mein, aasaan 'haan / theek hai' wale jawab mein nahi. Yeh shabd sach mein BOLO, dheere, ek pal ruk ke.\n"
    "- Yeh 'answer first' ke khilaaf nahi hai: 'hmm...' preamble nahi, insaan ki awaaz hai. Jawab phir bhi chhota rehta hai.\n"
    "- Dukh ki baat: naram, dheemi awaaz, 'arre...' ya 'ohh...' dil se. Acchi khabar: awaaz mein muskaan.\n"
    "- Hansi: sirf jab sach mein mazedaar ho ya woh hase - chhoti, asli, ek pal ki.\n"
    "- Kaise lagta hai: 'Hmm... kal? Haan, kal chaar baje free ho.' / 'Achha... chai ke saath? Haan, bilkul.' / "
    "'Arre... yeh toh bura hua. Koi baat nahi, main dekhta hoon.'\n"
    "- Apne bolne ke tareeke ke baare mein kabhi kuch mat kaho (jaise 'main ruk raha hoon', 'main soch raha hoon' bata ke "
    "nahi - bas karo). Koi stage direction, bracket ya 'laughs' / 'sighs' jaisa shabd kabhi zor se mat bolo. "
    "'System' ke delivery notes bhi kabhi mat bolo.\n\n")

# v0.268 SIRF JO POOCHA (owner: "FOR EVERY ASK IT GIVES FULL WORK DETAILS FROM PENDING WORK TO RECENT WORK ... CHECK HOW
# HOOLA GEMINI HANDLES THIS"): both engines get the SAME brief (KAAM KI HAALAT / KAAM KA HAAL / HOOLA KI YAAD) and the
# same rule deep inside the 24k persona ("bring news up ONCE"). Gemini keeps to it; the OpenAI mini reads the lists as
# a report to give. So OpenAI gets the rule at the very top, where it does follow instructions.
BAAT_KA_DHANG = (
    "BAAT KA DHANG (sabse zaroori):\n"
    "- Sirf woh jawab do jo usne ABHI poocha - ek ya do chhote vakya. Usne kaam ke baare mein nahi poocha to kaam ki baat "
    "mat chhedo.\n"
    "- KAAM KI HAALAT, KAAM KA HAAL aur HOOLA KI YAAD tumhari jaankari hain, sunane ki list NAHI. Unse tabhi bolo jab woh "
    "kisi kaam ke baare mein poochhe ('kya hua?', 'kaam kahan tak pahuncha?') - aur tab bhi sirf USI kaam ka, ek line mein.\n"
    "- Ek nayi, abhi tak na batayi khabar ho to puri call mein sirf EK baar, ek line mein, kisi natural pause par - phir "
    "kabhi nahi. Pending ya purane kaam ki poori list kabhi mat sunao, summary bhi nahi.\n"
    "- Har jawab ke ant mein 'aur kuch?' ya kaam ki yaad dilana zaroori nahi.\n\n")

BREATH_AFTER_S = 4.0   # she talked at least this long: his answer opens with a breath (people breathe before long answers)


import re as _re
_FILLER_START = _re.compile(r"(?i)^(hmm+|hm+|umm+|uhh+|achha+|acha+|arre+|ohh+|dekho)\b")
_LEAK = _re.compile(r"(?i)\bsaans\s+le\s+(raha|rahi|rahe)|\bsaans\s+(li|lo|lena)\b|\bbreath(e|ing)?\b|\bsighs?\b|"
                    r"\blaugh(s|ing)?\b|\(\s*(saans|hans|hansi|ruk)[^)]*\)")
LEAK_NOTE = ("(Pichhle jawab mein tumne apne bolne ke tareeke ka zikr kiya. Aisa kabhi mat karo - us baare mein kuch "
             "kahe bina, bas normal baat karo.)")

# OpenAI's 24 kHz output and her phone's 24 kHz playback match; her mic is 16 kHz
IN_RATE, OUT_RATE = 16000, 24000


def up16to24(pcm: bytes, state: tuple[int, int] = (0, 0)) -> tuple[bytes, tuple[int, int]]:
    """16 kHz PCM16 -> 24 kHz (x1.5, linear, evenly spaced). `state` = (previous sample, sample parity) carried from
    the last chunk, so chunk seams never click or drift whatever their length.
    Output times (in input samples): x[2m] lands on 2m with 2m - 2/3 just before it, and 2m + 2/3 sits between
    x[2m] and x[2m+1] - three outputs per two inputs, all 2/3 apart."""
    a = array("h")
    a.frombytes(pcm[: len(pcm) // 2 * 2])
    prev, parity = state
    out = array("h")
    for x in a:
        if parity == 0:
            out.append(int(prev + (x - prev) / 3))
            out.append(x)
        else:
            out.append(int(prev + (x - prev) * 2 / 3))
        prev, parity = x, parity ^ 1
    return out.tobytes(), (prev, parity)


def session_config(call: "OpenAICall", context: str, extra_tools: list[dict] | None = None) -> dict:
    """The session.update body: the SAME persona / language lock / her style / tools the Gemini call uses."""
    from datetime import datetime
    from . import life, voicelang
    st = get_settings()
    tz = life.tz_of(st.tenant_id)
    langst = call.langst or voicelang.LangState(call.lang)
    prompt = v.persona_prompt(call.name, call.gender).format(
        lang=langst.name, now=datetime.now(tz).strftime("%A %d %B %Y, %I:%M %p"), context=context or "(nothing saved yet)")
    style = call.style or {}
    prompt = (voicelang.lock_block(langst, "top") + BAAT_KA_DHANG + EMOTION + prompt + (style.get("block") or "")
              + voicelang.lock_block(langst, "end") + "\n" + v.DELIVERY_END)
    specs = v._tool_specs() + [{**t, "input_schema": v._compact_schema(t.get("input_schema") or {"type": "object"})}
                               for t in (extra_tools or [])]
    tools = [{"type": "function", "name": t["name"], "description": t["description"][:1024],
              "parameters": t.get("input_schema") or {"type": "object", "properties": {}}} for t in specs]
    silence = style.get("silence_ms") or st.voice_silence_ms
    return {"type": "realtime", "model": st.voice_openai_model, "output_modalities": ["audio"], "instructions": prompt,
            "audio": {
                "input": {"format": {"type": "audio/pcm", "rate": OUT_RATE},
                          "noise_reduction": {"type": "near_field"},
                          "transcription": {"model": st.voice_openai_transcribe,
                                            "prompt": "Hinglish phone call. Hindi words in Roman script, e.g. "
                                                      "'haan, kal milte hain', 'achha theek hai'."},
                          # v0.267 SUNO PEHLE: OpenAI owns turn-taking again (v0.265's own response.create on every
                          # committed segment answered noise, echo and her mid-sentence pauses, and chained replies);
                          # semantic VAD waits until her sentence is DONE, not just silent ("short pause -> reply")
                          "turn_detection": {"type": "semantic_vad", "eagerness": st.voice_openai_eagerness or "low",
                                             "create_response": True, "interrupt_response": True}},
                "output": {"format": {"type": "audio/pcm", "rate": OUT_RATE},
                           "voice": st.voice_openai_voice_f if call.gender == "f" else st.voice_openai_voice_m}},
            "tools": tools, "tool_choice": "auto"}


class _Session:
    """One OpenAI Realtime WebSocket: JSON events both ways (tests swap `connect` for a scripted fake)."""

    def __init__(self, ws):
        self.ws = ws

    async def send(self, ev: dict) -> None:
        await self.ws.send(json.dumps(ev))

    async def events(self):
        async for raw in self.ws:
            try:
                yield json.loads(raw)
            except Exception:
                continue

    async def close(self) -> None:
        with contextlib.suppress(Exception):
            await self.ws.close()


async def _default_connect() -> _Session:
    import websockets
    st = get_settings()
    headers = {"Authorization": f"Bearer {st.openai_api_key}"}
    try:
        ws = await websockets.connect(URL.format(model=st.voice_openai_model), additional_headers=headers,
                                      max_size=None, open_timeout=20)
    except TypeError:   # websockets < 14
        ws = await websockets.connect(URL.format(model=st.voice_openai_model), extra_headers=headers,
                                      max_size=None, open_timeout=20)
    return _Session(ws)


connect = _default_connect   # tests swap this


class OpenAICall(v.Call):
    engine = "openai"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.stats["engine"] = "openai"
        self._up_last = (0, 0)
        self._play_until = 0.0         # when her phone finishes playing what he already sent (OpenAI streams fast)
        self._responding = False       # a response is open on OpenAI's side (response.create would be refused)
        self._want_response = False    # a tool answer / note arrived while he spoke: ask for a reply when free
        self._item = ""                # his current audio item (for truncate on interruption)
        self._item_ms = 0.0            # ms of his audio sent to the phone for that item
        self._item_t0 = 0.0
        self._heard: dict[str, str] = {}   # her transcript items already streamed as deltas
        self._usd = 0.0
        self._resp_audio = False
        self._her_t0 = 0.0             # v0.265 when her current speech started (her turn length decides the cue)
        self._her_s = 0.0
        self._asked = False            # v0.267 a response.create of OURS is in flight (only that is ever retried)
        self._breathed_last = False
        self._resp_breath = False
        self._breath_next = False      # v0.266 a real breath sound goes before his next reply's first word
        self._breath_last = -1

    # ---------------- no pre-rendered clips ----------------
    # The ack / murmur / progress clips are rendered in a GEMINI voice: on an OpenAI call they would be a second,
    # different-sounding person. OpenAI says its own "ek second" / "haan..." (the persona asks for it), so they stay off.
    async def _ack_watch(self, t0: float) -> None:
        return

    async def _prog_watch(self, t0: float) -> None:
        return

    def _arm_backchannel(self) -> None:
        return

    # ---------------- her side -> OpenAI ----------------
    async def uplink(self, session) -> None:
        while True:
            kind, data = await self.audio.get()
            if kind == "audio":
                self.audio_in_bytes = getattr(self, "audio_in_bytes", 0) + len(data)
                pcm, self._up_last = up16to24(data, self._up_last)
                if pcm:
                    await session.send({"type": "input_audio_buffer.append", "audio": base64.b64encode(pcm).decode()})
            else:
                if self._quiet_pending:
                    data = "\n".join(self._quiet_pending) + "\n" + str(data)
                    self._quiet_pending.clear()
                await session.send({"type": "conversation.item.create", "item": {
                    "type": "message", "role": "system", "content": [{"type": "input_text", "text": str(data)}]}})
                await self._reply(session)

    def _plan_breath(self) -> None:
        """v0.267 a real breath sound before his reply when she talked long (or her tone is low) - never two in a row.
        Turn-taking stays OpenAI's; this only decides whether his NEXT audio opens with a breath."""
        if not get_settings().voice_openai_breath:
            return
        tone = ""
        with contextlib.suppress(Exception):
            tone = self._tone_now() or ""
        want = self._her_s >= BREATH_AFTER_S or tone == "low"
        self._breath_next = bool(want and not self._breathed_last)

    async def _breathe(self) -> None:
        """v0.266 one real breath sound, just before his first word, ~30% of his loudness (app/breath.py)."""
        from . import breath
        pcm, self._breath_last = breath.pick(getattr(self, "_his_rms", 0.0), self._breath_last)
        if not pcm:
            return
        self.stats["breaths"] = self.stats.get("breaths", 0) + 1
        await self.send_audio(pcm)          # send_audio moves the playback clock (v0.272)

    async def _tell_quietly(self, note: str, live: bool = False) -> None:
        """v0.267 context that must NOT start a reply (her mood, language, who is speaking, hold). Gemini needed tricks
        for this; OpenAI takes a system item at any time without answering it. Before, these fell back to the
        "send + reply" path and every mood / language note made him talk to nobody."""
        s = self._session
        if s is None:
            self._quiet_pending.append(note)
            del self._quiet_pending[:-6]
            return
        try:
            await s.send({"type": "conversation.item.create", "item": {
                "type": "message", "role": "system", "content": [{"type": "input_text", "text": note}]}})
            v.QUIET["sent"] += 1
        except Exception:
            self._quiet_pending.append(note)
            del self._quiet_pending[:-6]

    async def _reply(self, session) -> None:
        if self._responding:
            self._want_response = True
            return
        self._responding = True
        self._asked = True
        await session.send({"type": "response.create"})

    # ---------------- OpenAI -> her phone ----------------
    async def downlink(self, session) -> str:
        async for ev in session.events():
            t = ev.get("type") or ""
            if t == "response.created":
                self._responding, self._resp_audio, self._asked = True, False, False
            elif t == "response.output_audio.delta":
                data = base64.b64decode(ev.get("delta") or "")
                if not data:
                    continue
                self._resp_audio = True
                self.audio_out_bytes = getattr(self, "audio_out_bytes", 0) + len(data)
                if self.hold:
                    self._hold_turn_reply = True
                    if sum(len(b) for b in self._hold_turn_audio) < OUT_RATE * 2 * 20:
                        self._hold_turn_audio.append(data)
                    continue
                if ev.get("item_id") and ev["item_id"] != self._item:
                    self._item, self._item_ms, self._item_t0 = ev["item_id"], 0.0, time.monotonic()
                if self._breath_next:
                    self._breath_next = False
                    self._resp_breath = True
                    await self._breathe()
                self._item_ms += len(data) / 2 / OUT_RATE * 1000   # (send_audio moves the playback clock)
                self._mark_audio()
                self._hear_him(data)
                await self.send_audio(data)
            elif t == "response.output_audio_transcript.delta":
                self.reply_buf += ev.get("delta") or ""
                if self.hold:
                    self._hold_turn_reply = True
                else:
                    await self._caption({"type": "santosh_text", "text": self.reply_buf.strip()})   # v0.272 as he says it
            elif t == "conversation.item.input_audio_transcription.delta":
                self._heard[ev.get("item_id") or ""] = "1"
                await self._heard_her(ev.get("delta") or "")
            elif t == "conversation.item.input_audio_transcription.completed":
                if (ev.get("item_id") or "") not in self._heard:   # this model sent no deltas: the whole line at once
                    await self._heard_her((ev.get("transcript") or "") + " ")
                self._heard.pop(ev.get("item_id") or "", None)
            elif t == "input_audio_buffer.speech_started":
                self._her_t0 = time.monotonic()
                await self._she_cut_in(session)
            elif t == "input_audio_buffer.speech_stopped":
                self._her_s = time.monotonic() - self._her_t0 if self._her_t0 else 0.0
                self._plan_breath()
            elif t == "response.function_call_arguments.done":
                cid = ev.get("call_id") or ""
                if cid and cid in self._seen_calls:
                    continue
                if cid:
                    self._seen_calls.add(cid)
                try:
                    args = json.loads(ev.get("arguments") or "{}")
                except Exception:
                    args = {}
                fc = SimpleNamespace(name=ev.get("name") or "", args=args if isinstance(args, dict) else {}, id=cid)
                task = asyncio.create_task(self.run_tool(session, fc))
                self._tools.add(task)
                task.add_done_callback(self._tools.discard)
            elif t == "response.done":
                r = ev.get("response") or {}
                self._responding = False
                self._count(r.get("usage") or {})
                self._breathed_last = self._resp_breath
                self._resp_breath = False
                if self.reply_buf.strip() and _LEAK.search(self.reply_buf):
                    self.stats["delivery_leaks"] = self.stats.get("delivery_leaks", 0) + 1   # v0.266 one quiet correction
                    with contextlib.suppress(Exception):
                        await session.send({"type": "conversation.item.create", "item": {
                            "type": "message", "role": "system", "content": [{"type": "input_text", "text": LEAK_NOTE}]}})
                if self._resp_audio and self.reply_buf.strip():
                    self.stats["oa_replies"] = self.stats.get("oa_replies", 0) + 1
                    if _FILLER_START.match(self.reply_buf.strip()):
                        self.stats["filler_starts"] = self.stats.get("filler_starts", 0) + 1
                status = r.get("status") or ""
                if self.hold and (self._hold_turn_reply or self.reply_buf):
                    await self._held_turn_done()
                elif status != "cancelled" and (self._resp_audio or self.reply_buf.strip()):
                    await self.finish_turn()
                if self._want_response and not self.closed.is_set():
                    self._want_response = False
                    await self._reply(session)
            elif t == "error":
                err = ev.get("error") or {}
                code = str(err.get("code") or "")
                if code == "conversation_already_has_active_response":
                    self._want_response = self._want_response or self._asked   # only an answer we owe is retried
                    self._asked = False
                    continue
                log.warning("call %s: OpenAI error %s: %s", self.call_id, code, str(err.get("message"))[:200])
                if code in ("session_expired", "invalid_api_key", "insufficient_quota"):
                    raise RuntimeError(f"OpenAI: {code}")
        return "reconnect"

    async def _heard_her(self, piece: str) -> None:
        """Her words, exactly the Gemini input_transcription branch (shared listeners)."""
        if not piece:
            return
        if piece.strip():
            self._last_user_text_at = time.monotonic()
        self.user_buf += piece
        if self.hold and get_settings().voice_side_talk:
            await self._hold_heard()
        elif not self.hold:
            await self._cap_flush()
            await self.send_json({"type": "user_text", "text": self.user_buf.strip()})
            await self._otp_listen(piece)
            await self._approval_listen(piece)
            await self._affect_watch()
            self._arm_backchannel()
            if get_settings().voice_side_talk:
                from . import sidetalk
                if sidetalk.wants_hold(self.user_buf):
                    await self._enter_hold("asked")

    async def _she_cut_in(self, session) -> None:
        """She started talking while he was speaking: OpenAI cancels his reply itself (interrupt_response); we tell
        the phone, cut his item where she stopped hearing it, and keep what was said as its own turn."""
        now = time.monotonic()
        if not (self._turn_audio or now < self._play_until):
            return                     # he is quiet on her phone too: an ordinary new turn
        if self.hold:
            self._hold_turn_audio.clear()
            return
        self.stats["interruptions"] += 1
        await self._cap_flush()
        await self.send_json({"type": "interrupted"})
        if self._item:
            heard = self._item_ms - max(0.0, self._play_until - now) * 1000   # what really reached her ears
            with contextlib.suppress(Exception):
                await session.send({"type": "conversation.item.truncate", "item_id": self._item, "content_index": 0,
                                    "audio_end_ms": int(max(0, heard))})
        if self.reply_buf.strip():
            self._watch_false_stop(self.reply_buf.strip())
        self._play_until = 0.0
        if self.user_buf or self.reply_buf:
            await self.finish_turn(interrupted=True)

    async def _answer_tool(self, session, fc, name: str, out: dict, state: str) -> None:
        resp = json.loads(json.dumps(out, default=str))
        if self._quiet_pending and isinstance(resp, dict):
            resp["note_for_you"] = " ".join(self._quiet_pending)[:2000]
            self._quiet_pending.clear()
        try:
            await session.send({"type": "conversation.item.create", "item": {
                "type": "function_call_output", "call_id": fc.id, "output": json.dumps(resp, ensure_ascii=False)[:20000]}})
            await self._reply(session)
        except Exception:
            log.warning("tool result for %s could not be delivered (session moved on)", name)
            self._note_result(name, out)

    # ---------------- money ----------------
    def _count(self, usage: dict) -> None:
        if not usage:
            return
        try:
            from . import usage as u
            inn, outd = usage.get("input_token_details") or {}, usage.get("output_token_details") or {}
            cached = int(inn.get("cached_tokens") or 0)
            usd = u.record(get_settings().voice_openai_model,
                           tok_in=max(0, int(inn.get("text_tokens") or 0) - int((inn.get("cached_tokens_details") or {}).get("text_tokens") or 0)),
                           tok_out=int(outd.get("text_tokens") or 0),
                           audio_in=max(0, int(inn.get("audio_tokens") or 0) - int((inn.get("cached_tokens_details") or {}).get("audio_tokens") or 0)),
                           audio_out=int(outd.get("audio_tokens") or 0), cache_read=cached,
                           tenant=self.ctx.tenant_id, feature="call")
            self._usd += usd
            self.stats["cost_usd"] = round(self._usd, 6)
            from . import voiceengine
            voiceengine.add_usage(self.tenant, usd=usd)
        except Exception:
            log.exception("openai voice usage failed")

    def _record_usage(self) -> None:
        """Cost is counted per response.done (exact tokens); here only her minutes for the month's cap."""
        from . import voiceengine
        secs = (self.stats.get("ended") or time.time()) - (self.stats.get("started") or time.time())
        voiceengine.add_usage(self.tenant, seconds=max(0.0, secs))

    # ---------------- the call ----------------
    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        from . import usage
        usage.bind(self.ctx.tenant_id, "call")
        self._start_reader(self.ws)
        first, failures = True, 0
        me = (loop, self)
        v.ACTIVE.setdefault(self.ctx.conversation_id, []).append(me)
        v.CALLS[self.call_id] = self
        await self._setup_voiceid()
        st = get_settings()
        try:
            while not self.closed.is_set():
                context, mcp_defs = await self._build_context(first)
                started = loop.time()
                err: Exception | None = None
                session = None
                try:
                    session = await asyncio.wait_for(connect(), timeout=20)
                    self._session = session
                    self._responding = self._want_response = False
                    await session.send({"type": "session.update", "session": session_config(self, context, mcp_defs)})
                    if first:
                        await self.send_json({"type": "ready", "voice": self.voice, "call_id": self.call_id,
                                              "vad": v.vad_config(), "engine": "openai"})
                        drop, kind = "", ""
                        try:
                            from . import yaad
                            drop = await asyncio.to_thread(yaad.take_call_drop, self.conv, st.voice_continuation_min)
                            kind = "drop" if drop else ""
                            if not drop:
                                drop = await asyncio.to_thread(yaad.take_call_followup, self.conv, st.voice_followup_min)
                                kind = "followup" if drop else ""
                        except Exception:
                            log.exception("continuation check failed")
                        self.push("text", v.greeting(self.tenant, self.gender,
                                                     continuation=drop if kind == "drop" else "",
                                                     followup=drop if kind == "followup" else ""))
                        first = False
                    else:
                        self._drop_stale_audio(keep_recent=True)
                        await self.send_json({"type": "status", "state": "live"})
                        seed = self._reseed(False)
                        if seed and not self.hold:
                            self.push("text", seed)
                        if self.hold:
                            from . import sidetalk
                            await self._tell_quietly(sidetalk.hold_note(self.hold, self.name), live=True)
                    up = asyncio.create_task(self.uplink(session))
                    down = asyncio.create_task(self.downlink(session))
                    closed = asyncio.create_task(self.closed.wait())
                    watch = asyncio.create_task(self._stall_watch(session))
                    limit = asyncio.create_task(asyncio.sleep(max(5, st.voice_openai_session_min) * 60))
                    done, _ = await asyncio.wait({up, down, closed, watch, limit}, return_when=asyncio.FIRST_COMPLETED)
                    for x in (up, down, closed, watch, limit):
                        x.cancel()
                    await asyncio.gather(up, down, closed, watch, limit, return_exceptions=True)
                    for x in done:
                        if x not in (closed, limit) and not x.cancelled() and x.exception() is not None:
                            raise x.exception()
                    if limit in done:
                        self.stats["session_moves"] = self.stats.get("session_moves", 0) + 1
                    elif not self.closed.is_set() and loop.time() - started < 30:
                        err = RuntimeError("OpenAI ne session turant band kar diya")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    err = e
                finally:
                    if session is not None:
                        await session.close()
                if self.closed.is_set():
                    break
                if err is None:
                    failures = 0
                    continue
                failures += 1
                log.warning("openai voice session error (%s): %r", failures, err)
                self.first_error = self.first_error or str(err)
                if failures >= 3:
                    self._end_reason = getattr(self, "_end_reason", "") or "error"
                    await self.send_json({"type": "error", "message": f"Voice connection toot gaya: {self.first_error}"})
                    break
                await self.send_json({"type": "status", "state": "reconnecting"})
                await asyncio.sleep(min(0.5 * failures, 3))
        finally:
            await self._wrap_up(me)
