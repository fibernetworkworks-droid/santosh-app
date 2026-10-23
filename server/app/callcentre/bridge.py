"""The live phone line: provider WebSocket (8 kHz) <-> Gemini Live (16 kHz in / 24 kHz out) with a CUSTOMER persona.

What is enforced here, in code (not just asked of the model):
- only the line's own customer-safe tools exist in the session (service.line_specs / run_line_tool); her personal tools
  are never declared, and an unknown tool name is refused;
- the script is the version this call started with (her approved one), never a draft;
- the first reply must say "AI": if it doesn't, a correction note goes in and the call note flags it;
- numbers / promises in a reply that the script and the tool results never said are flagged and corrected;
- the caller asking for a person (any language), pressing 0, sounding angry, two not-in-script questions in a row or two
  failed understandings -> hand-over: a transfer to her / staff inside her hours, else a call-back message; if the model
  doesn't do it within a few seconds, the code does;
- a caller starting to say an OTP / PIN / card / Aadhaar is stopped, and the transcript masks it;
- the call ends at `max_minutes`; Gemini failing to connect = hand-over (or a call-back message), never dead air.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from typing import Any

from . import audio as A
from . import rules as R
from . import service as S

log = logging.getLogger("santosh.callcentre")

connector = None          # tests put a fake Gemini Live here; None = the app's own (voice.connector)
STATS: list[dict[str, Any]] = []
HANDOVER_GRACE_S = 6.0    # the model was told to hand over; after this the code does it
SAY_THEN_MOVE_S = 2.5     # time for "aapko team se jod rahe hain" to play before the call moves


def _connect(cfg):
    if connector is not None:
        return connector(cfg)
    from .. import voice
    return voice.connector(cfg)


class Sock:
    """What the bridge needs from the provider's WebSocket (FastAPI WebSocket or a test double)."""

    def __init__(self, ws):
        self.ws = ws

    async def recv(self) -> str | None:
        try:
            m = await self.ws.receive()
        except Exception:
            return None
        if m.get("type") == "websocket.disconnect":
            return None
        if m.get("text") is not None:
            return m["text"]
        if m.get("bytes") is not None:
            return m["bytes"].decode("utf-8", "ignore")
        return ""

    async def send(self, text: str) -> None:
        with contextlib.suppress(Exception):
            await self.ws.send_text(text)

    async def close(self) -> None:
        with contextlib.suppress(Exception):
            await self.ws.close()


def live_config(persona: str, specs: list[dict[str, Any]], voice: str, langst, vocab: list[str]):
    from google.genai import types
    from .. import voice as V
    from .. import voicelang as VL
    decls = [types.FunctionDeclaration(name=t["name"], description=t["description"], parameters_json_schema=t["input_schema"])
             for t in specs]
    cfg = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))),
        system_instruction=types.Content(parts=[types.Part(text=persona)]),
        tools=[types.Tool(function_declarations=decls)],
        input_audio_transcription=types.AudioTranscriptionConfig(language_codes=VL.transcription_codes(langst),
                                                                 custom_vocabulary=vocab[:100] or None),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        realtime_input_config=types.RealtimeInputConfig(automatic_activity_detection=types.AutomaticActivityDetection(
            start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,   # line noise is not the caller talking
            prefix_padding_ms=300,
            silence_duration_ms=800,                                                     # phone audio arrives with jitter
        )),
    )
    for f in V.UNSUPPORTED:      # settings this Gemini model refused before: same drops as the owner's calls
        if f in types.AudioTranscriptionConfig.model_fields and f not in type(cfg).model_fields:
            if cfg.input_audio_transcription is not None:
                setattr(cfg.input_audio_transcription, f, None)
        elif f in type(cfg).model_fields:
            setattr(cfg, f, None)
        elif f in type(cfg.realtime_input_config.automatic_activity_detection).model_fields:
            setattr(cfg.realtime_input_config.automatic_activity_detection, f, None)
    return cfg


class CallBridge:
    def __init__(self, tenant: str, provider, line, sock: Sock, call_id: str, provider_call: str = ""):
        self.tenant, self.provider, self.line, self.sock = tenant, provider, line, sock
        self.call_id, self.provider_call = call_id, provider_call
        self.row = S.call_row(call_id) or {}
        self.caller = (self.row or {}).get("caller", "")
        self.closed = asyncio.Event()
        self.q: asyncio.Queue = asyncio.Queue(maxsize=600)
        self.up = A.Resampler(line.rate, 16000)
        self.down = A.Resampler(24000, line.rate)
        self.turns: list[tuple[str, str]] = []
        self.tools: list[str] = []
        self.flags: list[dict[str, Any]] = []
        self.unanswered: list[str] = []
        self.user_buf, self.reply_buf = "", ""
        self.replies = 0
        self.disclosed = False
        self._asked_again = 0
        self._last_note_turn = -5
        self._handover_due: float = 0.0
        self.transferred = False
        self.failed = False
        self.ending = False
        self._ai_until = 0.0
        self._seen_calls: set[str] = set()
        self._tasks: set[asyncio.Task] = set()
        self.bytes_in = self.bytes_out = 0
        self.t0 = time.monotonic()
        self.session = None
        self.stats = {"call_id": call_id, "turns": 0, "interruptions": 0, "dtmf": 0, "notes": 0, "gate_held": 0,
                      "handover": "", "disclosure_fixed": 0, "unscripted": 0}
        self._gate = None
        try:
            from .. import vad
            if vad.available():
                self._gate = vad.Stream()
        except Exception:
            self._gate = None
        self._noise = 0.004       # learned line background (RMS)

    # ---------------------------------------------------------------- set-up
    def _load(self):
        sc = None
        sid = (self.row or {}).get("script_id")
        with S.session() as s:
            from .models import CcScript
            r = s.get(CcScript, sid) if sid else None
            if r is not None and r.tenant_id == self.tenant and r.status in ("approved", "retired") \
                    and r.hash == R.script_hash(S._j(r.content, {})):
                sc = S._script_view(r)
        sc = sc or S.approved(self.tenant)
        return sc

    def _spawn(self, coro) -> asyncio.Task:
        t = asyncio.create_task(coro)
        self._tasks.add(t)
        t.add_done_callback(self._tasks.discard)
        return t

    def note(self, text: str) -> None:
        self.stats["notes"] += 1
        self._push(("text", text))

    def _push(self, item) -> None:
        if self.q.full():
            with contextlib.suppress(Exception):
                self.q.get_nowait()
        self.q.put_nowait(item)

    # ---------------------------------------------------------------- the call
    async def run(self) -> dict[str, Any]:
        from .. import voicelang as VL
        from ..avatar import service as av
        self.script = await asyncio.to_thread(self._load)
        if not self.script:
            await self._fallback("ai_down")
            return await self._finish()
        lang = (self.row or {}).get("lang") or self.script["content"].get("default_lang") or "hi-IN"
        self.langst = VL.LangState(lang, "caller")
        self.cc = S.CallCtx(self.tenant, self.call_id, self.caller, self.script | {"lang": lang})
        with S.session() as s:
            r = S._row(s, self.tenant)
            voice, self.recorded, self.max_s = r.voice, r.record, r.max_minutes * 60
        a = av.get(self.tenant)
        voice = voice or a["voice"]
        self.gender = a["gender"]
        persona = await asyncio.to_thread(S.persona, self.tenant, self.script, self.langst, self.caller, self.recorded)
        persona += ("\nYou are female: use feminine Hindi / Marathi verb forms for yourself (kar rahi hoon, bolte aahe)."
                    if self.gender == "f" else "\nYou are male: use masculine Hindi / Marathi verb forms for yourself (kar raha hoon).")
        self.allowed = " ".join([json.dumps(self.script["content"], ensure_ascii=False)])
        reader = self._spawn(self.line_reader())
        try:
            for attempt in range(3):
                cfg = live_config(persona, S.line_specs(self.script), voice, self.langst, S.vocab(self.script))
                try:
                    async with contextlib.AsyncExitStack() as stack:
                        self.session = await asyncio.wait_for(stack.enter_async_context(_connect(cfg)), timeout=15)
                        await self.session.send_realtime_input(text=(
                            "(System: the phone call just connected. Say the FIRST LINE from your instructions now, in the "
                            "caller's language, then ask how you can help.)"))
                        ups = self._spawn(self.uplink())
                        downs = self._spawn(self.downlink())
                        watch = self._spawn(self.watchdog())
                        ended = self._spawn(self.closed.wait())
                        done, _ = await asyncio.wait({ups, downs, ended}, return_when=asyncio.FIRST_COMPLETED)
                        for t in (ups, downs, watch, ended):
                            t.cancel()
                        for t in done:
                            if t is not ended and not t.cancelled() and t.exception() is not None:
                                raise t.exception()
                    break
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    from .. import voice as V
                    bad = V.unsupported_field(e)
                    if bad and attempt < 2:
                        V.UNSUPPORTED.add(bad)
                        continue
                    log.warning("callcentre: Gemini line failed: %r", e)
                    self.failed = True
                    if not self.closed.is_set():
                        await self._fallback("ai_down")
                    break
        finally:
            reader.cancel()
            for t in list(self._tasks):
                t.cancel()
        return await self._finish()

    async def line_reader(self) -> None:
        while not self.closed.is_set():
            text = await self.sock.recv()
            if text is None:
                break
            for ev in self.line.parse(text):
                k = ev["type"]
                if k == "audio":
                    self._caller_audio(ev["pcm"])
                elif k == "dtmf":
                    self.stats["dtmf"] += 1
                    if ev.get("digit") == "0":
                        self._spawn(self.handover("dtmf", force=True))
                elif k == "stop":
                    self.closed.set()
                    return
                elif k == "start" and ev.get("call"):
                    self.provider_call = self.provider_call or ev["call"]
        self.closed.set()

    def _caller_audio(self, pcm: bytes) -> None:
        if not pcm:
            return
        x = self.up(pcm)
        level = A.rms(x)
        speaking = time.monotonic() < self._ai_until
        if not speaking:
            self._noise = 0.95 * self._noise + 0.05 * min(level, 0.05)
        elif S._st() and getattr(S._st(), "callcentre_noise_gate", True):
            # while Hoola talks, line noise / echo must not cut him off: pass only clearly-voiced, loud-enough audio
            voiced = True
            if self._gate is not None:
                try:
                    p = self._gate.prob(x)
                    voiced = p is None or p >= 0.5
                except Exception:
                    voiced = True
            if not voiced or level < max(0.015, self._noise * 3):
                self.stats["gate_held"] += 1
                x = b"\x00" * len(x)
        self._push(("audio", x))

    async def uplink(self) -> None:
        from google.genai import types
        while True:
            kind, data = await self.q.get()
            if kind == "audio":
                self.bytes_in += len(data)
                await self.session.send_realtime_input(audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000"))
            else:
                await self.session.send_realtime_input(text=data)

    async def downlink(self) -> None:
        while not self.closed.is_set():
            got = False
            async for m in self.session.receive():
                got = True
                tc = getattr(m, "tool_call", None)
                if tc is not None:
                    for fc in tc.function_calls or []:
                        fid = getattr(fc, "id", None) or ""
                        if fid and fid in self._seen_calls:
                            continue
                        if fid:
                            self._seen_calls.add(fid)
                        self._spawn(self.run_tool(fc))
                sc = getattr(m, "server_content", None)
                if sc is None:
                    continue
                if sc.interrupted:
                    self.stats["interruptions"] += 1
                    clr = self.line.clear()
                    if clr:
                        await self.sock.send(clr)
                    self._ai_until = 0.0
                    if self.user_buf or self.reply_buf:
                        await self.finish_turn()
                if sc.input_transcription is not None and sc.input_transcription.text:
                    self.user_buf += sc.input_transcription.text
                if sc.model_turn is not None:
                    for part in sc.model_turn.parts or []:
                        blob = getattr(part, "inline_data", None)
                        if blob is not None and blob.data:
                            self.bytes_out += len(blob.data)
                            pcm = self.down(blob.data)
                            dur = len(pcm) / 2 / self.line.rate
                            self._ai_until = max(self._ai_until, time.monotonic()) + dur
                            for frame in self.line.out_audio(pcm):
                                await self.sock.send(frame)
                if sc.output_transcription is not None and sc.output_transcription.text:
                    self.reply_buf += sc.output_transcription.text
                if sc.turn_complete:
                    for frame in self.line.flush():
                        await self.sock.send(frame)
                    await self.finish_turn()
            if not got:
                return

    # ---------------------------------------------------------------- turns: language, hand-over, script checks
    async def finish_turn(self) -> None:
        user, reply = self.user_buf.strip(), self.reply_buf.strip()
        self.user_buf = self.reply_buf = ""
        if user:
            self.turns.append(("caller", user))
            await self._heard(user)
        if reply:
            self.turns.append(("hoola", reply))
            self.stats["turns"] += 1
            self.replies += 1
            await self._said(reply, user)

    async def _heard(self, user: str) -> None:
        h = self.langst.hear(user)
        if h.get("switched"):
            self.note(self.langst.switched_note())
        sec = R.secret_in(user)
        if sec:
            self.flags.append({"kind": "secret", "text": R.REASON_SAY["secret"]})
            self.note("(System: the caller is saying a secret number (OTP / PIN / card / Aadhaar / bank). Stop them kindly "
                      "at once: this line never needs it. Do not repeat any digits.)")
        reason = R.handover_reason(user)
        words = (self.script["content"].get("handover_words") or [])
        if not reason and any(w and w.lower() in user.lower() for w in words):
            reason = "asked_human"
        if reason:
            await self.handover(reason)

    async def _said(self, reply: str, user: str) -> None:
        if not self.disclosed:
            if R.DISCLOSE_HEARD.search(reply):
                self.disclosed = True
            elif self.replies == 1:
                self.stats["disclosure_fixed"] += 1
                self.flags.append({"kind": "disclosure", "text": "pehli line mein AI nahi bola; system ne turant bulwaya"})
                self.note("(System: you did not tell the caller you are an AI assistant. Say it now in one short sentence, "
                          "then continue.)")
        allowed = self.allowed + " " + self.cc.seen_text + " " + " ".join(t for w, t in self.turns if w == "caller")
        bad = R.unscripted(reply, allowed)
        if bad:
            self.stats["unscripted"] += 1
            self.flags.append({"kind": "unscripted", "text": ", ".join(bad), "said": R.mask_text(reply)[:200]})
            if self.stats["turns"] - self._last_note_turn >= 2:
                self._last_note_turn = self.stats["turns"]
                self.note("(System: you just said something that is NOT in her approved script (" + ", ".join(bad) + "). "
                          "Correct yourself in one line: the team will confirm it, and offer to take a message. Never add "
                          "facts.)")
        drift = self.langst.check_reply(reply)
        if drift:
            self.note(drift)
        from .. import voicelang as VL
        sig = VL.repair_signals(user, reply)
        self._asked_again = self._asked_again + 1 if (sig["asked_again"] or sig["her_corrections"]) else 0
        if self._asked_again >= 2:
            self._asked_again = 0
            await self.handover("low_confidence")
        if self.cc.misses >= 2 and not self.cc.handover:
            self.cc.misses = 0
            self.note("(System: two questions in a row were outside her script. Offer the caller a person now (transfer_human "
                      "reason=out_of_script) or to take a message. Don't guess.)")

    async def handover(self, reason: str, force: bool = False) -> None:
        if self.cc.handover is not None and not force:
            return
        plan = await asyncio.to_thread(S.plan_handover, self.cc, reason)
        self.stats["handover"] = reason
        if plan["mode"] == "transfer":
            self.note(f"(System: {R.REASON_SAY.get(reason, reason)}. Say ONE short line in the caller's language that you "
                      f"are connecting them to the team, then call transfer_human reason={reason}.)")
            self._handover_due = time.monotonic() + (SAY_THEN_MOVE_S if force else HANDOVER_GRACE_S)
        else:
            self.note(f"(System: {R.REASON_SAY.get(reason, reason)}, but nobody can take the call right now. Tell them the "
                      "team will call back, ask what it is about and their name, then take_message.)")

    async def watchdog(self) -> None:
        warned = False
        while not self.closed.is_set():
            await asyncio.sleep(0.25)
            t = time.monotonic()
            if self._handover_due and t >= self._handover_due and not self.transferred:
                self._handover_due = 0.0
                await self._transfer()
            if not warned and t - self.t0 > self.max_s - 60:
                warned = True
                self.note("(System: one minute left on this call. Wrap up: offer to take a message for anything left.)")
            if t - self.t0 > self.max_s:
                self.flags.append({"kind": "time_up", "text": R.REASON_SAY["time_up"]})
                await self._end()
                return

    # ---------------------------------------------------------------- tools on the line
    async def run_tool(self, fc) -> None:
        from google.genai import types
        name, args = fc.name, dict(fc.args or {})
        self.tools.append(name)
        out = await asyncio.to_thread(S.run_line_tool, self.cc, name, args)
        if name == "faq_answer" and out.get("not_in_script"):
            self.unanswered.append(R.mask_text(str(args.get("question") or ""))[:160])
        try:
            await self.session.send_tool_response(function_responses=[types.FunctionResponse(
                id=fc.id, name=name, response=json.loads(json.dumps(out, default=str)))])
        except Exception:
            log.info("callcentre tool answer not delivered (%s)", name)
        if name == "transfer_human" and out.get("transferring"):
            self._handover_due = time.monotonic() + SAY_THEN_MOVE_S
        if name == "end_call":
            self._spawn(self._end())

    async def _transfer(self) -> None:
        plan = self.cc.handover or await asyncio.to_thread(S.plan_handover, self.cc, "asked_human")
        if plan.get("mode") != "transfer" or self.transferred:
            return
        try:
            url = await asyncio.to_thread(self._transfer_url)
            await asyncio.to_thread(self.provider.transfer, self.provider_call, url)
            self.transferred = True
        except Exception as e:
            log.warning("callcentre transfer failed: %s", e)
            self.flags.append({"kind": "transfer_failed", "text": str(e)[:160]})
            self.cc.handover = {"mode": "callback", "reason": plan.get("reason", "")}
            self.note("(System: the transfer did not go through. Apologise in one line, take a message for a call-back.)")
            return
        if self.provider.closes_stream_to_transfer:
            await asyncio.sleep(0.3)
            self.closed.set()

    def _transfer_url(self) -> str:
        with S.session() as s:
            r = S._row(s, self.tenant)
            urls = S._urls(self.tenant, r)
        base = urls.get("answer", "").rsplit("/answer", 1)[0]
        return f"{base}/transfer/{self.call_id}?t={S.ticket(self.call_id, 10)}"

    async def _end(self) -> None:
        if self.ending:
            return
        self.ending = True
        wait = max(0.0, min(8.0, self._ai_until - time.monotonic())) + 0.8   # let the closing line finish playing
        await asyncio.sleep(wait)
        with contextlib.suppress(Exception):
            await asyncio.to_thread(self.provider.hangup, self.provider_call)
        self.closed.set()

    async def _fallback(self, reason: str) -> None:
        """No AI on this call: hand to a person if possible, else a call-back message and hang up."""
        cc = getattr(self, "cc", None) or S.CallCtx(self.tenant, self.call_id, self.caller, self.script or {"content": {}})
        self.cc = cc
        plan = await asyncio.to_thread(S.plan_handover, cc, reason)
        self.stats["handover"] = reason
        if plan["mode"] == "transfer":
            await self._transfer()
        if not self.transferred:
            await asyncio.to_thread(S._missed, self.tenant, self.call_id, self.caller, "callback",
                                    "AI line nahi chal payi; caller ko call back karein")
            with contextlib.suppress(Exception):
                await asyncio.to_thread(self.provider.hangup, self.provider_call)
        self.closed.set()

    async def _finish(self) -> dict[str, Any]:
        if self.user_buf or self.reply_buf:
            await self.finish_turn()
        self.closed.set()
        await self.sock.close()
        secs = time.monotonic() - self.t0
        self.stats["lang"] = getattr(self, "langst", None).summary() if getattr(self, "langst", None) else {}
        STATS.append(self.stats)
        del STATS[:-200]
        data = {"turns": self.turns, "tools": self.tools, "flags": self.flags, "seconds": secs,
                "lang": getattr(getattr(self, "langst", None), "base", ""), "disclosed": self.disclosed,
                "handover": getattr(getattr(self, "cc", None), "handover", None) or {}, "transferred": self.transferred,
                "failed": self.failed, "stats": self.stats, "unanswered": self.unanswered,
                "sec_in": self.bytes_in / 32000, "sec_out": self.bytes_out / 48000}
        from ..config import get_settings
        try:
            from .. import usage
            data["ai_usd"] = usage.cost(get_settings().gemini_live_model, sec_in=data["sec_in"], sec_out=data["sec_out"])
        except Exception:
            data["ai_usd"] = 0.0
        return await asyncio.to_thread(S.finish, self.call_id, data)
