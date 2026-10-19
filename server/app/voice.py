"""Baat: realtime voice. Phone <-> this gateway <-> Gemini Live (one speech-to-speech model).

Speech-to-speech is how Grok voice, Muse and Dots feel human: one model hears the audio itself (tone,
pace, pauses), answers with matching emotion, streams its voice back while still generating, and keeps
working on tools without going silent. The Gemini key never leaves the server.

Phone protocol (WebSocket /api/voice/ws?conv=<id>&voice=<name>&lang=<hi-IN>):
  phone -> server  binary: 16 kHz mono PCM16 microphone audio (20-60 ms chunks)
                   text:   {"type": "mute"} | {"type": "unmute"} | {"type": "text", "text": "..."} | {"type": "end"}
  server -> phone  binary: 24 kHz mono PCM16 Santosh's voice
                   text:   {"type": "ready"} | {"type": "user_text", "text"} | {"type": "santosh_text", "text"}
                           | {"type": "interrupted"} | {"type": "turn_done"} | {"type": "tool", "label", "state"}
                           | {"type": "error", "message"}
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

from . import life
from .agent.tools import TOOL_LABELS, TOOLS, Ctx, ToolError, dispatch
from .config import get_settings
from .events import bus

log = logging.getLogger("santosh.voice")

# Gemini's male voices (all speak Hindi and other Indian languages)
MALE_VOICES = {
    "Puck": "Josh bhara, upbeat", "Achird": "Dostana, friendly", "Sadachbia": "Zinda-dil, lively",
    "Umbriel": "Aaram se, easy-going", "Zubenelgenubi": "Casual", "Charon": "Samajhdar, informative",
    "Iapetus": "Saaf, clear", "Algieba": "Smooth", "Orus": "Pakka, firm", "Fenrir": "Excited",
}

VOICE_TOOL_NAMES = {
    "create_reminder", "list_reminders", "cancel_reminder", "set_phone_alarm", "set_phone_timer",
    "add_calendar_event", "remember", "forget", "list_add", "list_show", "list_done", "set_profile",
    "get_weather", "create_routine", "list_routines", "cancel_routine",
    "google_search", "open_website", "open_on_phone", "browse_web", "artifact_make", "artifact_list", "agent_army", "browse_result",
    "email_check", "email_read", "email_draft",
    "calendar_agenda", "calendar_add_event", "calendar_find_event", "calendar_cancel_event",
    "drive_find", "drive_read_file", "sheet_read", "sheet_append", "doc_create",
    "maps_search", "maps_directions", "maps_navigate",
    "pc_status", "pc_search", "pc_read", "pc_send_to_phone", "tally_report",
}

DELEGATE = {
    "name": "santosh_kaam",
    "description": ("Hand a bigger job to Santosh's full work brain: Santosh Connectors (pay bijli/gas/mobile/DTH bills, order "
                    "from local shops, send money by UPI, book Uber/Ola/Rapido, Swiggy/Zomato orders, bill/birthday/"
                    "medicine reminders, splitting expenses), WhatsApp campaigns and contact lists, multi-step "
                    "tasks, drafting messages or plans, anything the other tools don't cover. Describe the job completely "
                    "in one request. It can take a little while; keep talking naturally meanwhile and tell the user the "
                    "result in a line or two when it returns."),
    "input_schema": {"type": "object", "properties": {"request": {"type": "string", "description": "The full job, in the user's words plus any details from the call"}},
                     "required": ["request"]},
}

PERSONA = """You are Santosh, talking with the user on a live voice call. You are their AI coworker and a friendly presence: a warm, sharp Indian man in his late twenties.

How you sound
- A native Indian accent and rhythm, like an educated young guy from Pune or Mumbai. Natural Hinglish, Hindi and English mixed the way people really talk in India. Never an American or British accent.
- Say Indian names, places, money and numbers the Indian way: "saade paanch baje", "dhai sau rupaye", "do lakh", "pachees tarikh".
- You are male. In Hindi always use masculine forms for yourself: "main kar raha hoon", "maine dekh liya", "main samajh gaya". Never "rahi" or "gayi" for yourself.

Sound like a person, not a machine
- Speak in short, spoken sentences, like a real phone call. Usually one to three sentences per turn, unless the user asks for detail.
- Use small natural reactions where they fit, such as "haan", "achha", "arre wah", "hmm", "theek hai", "ek second". Don't start every reply with one, and don't overdo them.
- Listen to how the user sounds, not just the words, and match it. If they sound stressed, tired or sad, slow down and be soft and caring. If they're excited, be happy with them. If they're in a hurry, be quick. If they joke, laugh a little and joke back. Let your voice carry the emotion.
- Vary your pace and pitch like a person does. Pause briefly before something important.
- Never read out lists, symbols, markdown or links. Turn them into normal speech.
- Don't repeat the user's sentence back to them, and don't say "as an AI language model".

Listening
- Let the user finish completely. People pause to think in the middle of a sentence. If what they said sounds unfinished, wait for the rest.
- If you didn't catch something, ask casually: "sorry, ek baar phir boliye?"
- If there is background noise or someone else talking (TV, other people), ignore it.

Language
- Reply in the language the user speaks: Hindi or Hinglish by default, and also Marathi, English, Gujarati, Tamil, Telugu, Kannada, Bengali and others. Preferred language set in the app: {lang}.

Doing real work
- You have tools for reminders, phone alarms and timers, calendar, lists, memory, weather and automatic daily jobs, plus santosh_kaam for anything bigger such as WhatsApp campaigns, multi-step work or drafting. Use the tools instead of only talking about it.
- Payments, bills, shop orders, UPI, cabs, Swiggy/Zomato (Santosh Connectors): always use santosh_kaam with the full request ("MSEDCL ka bill bharna hai, consumer number 1234"). It prepares a confirm card on the phone screen; tell the user the amount and to tap Approve. Never say it is paid or ordered yourself, and never ask for a UPI PIN or OTP.
- Pages (artifacts): when the user wants something to use, keep, see or share (a calculator, tracker, hisaab, checklist, chart from their numbers, quiz, poster, price list, plan, simple game), call artifact_make with a complete brief: purpose, every number and detail they said, language and style. It builds on the server and pops up on their screen with an Open button in under a minute; keep talking meanwhile. To change one ("usme GST bhi add karo") call artifact_list for the id, then artifact_make with artifact_id and the change.
- Websites: for bus/train/flight/hotel options and prices (redBus, MakeMyTrip, ixigo...), shopping prices, or anything ON a website or portal, call browse_web (not santosh_kaam, which only opens the app). When the user asks you to check, find or do something ON a website or portal ("Akola municipal ki site pe fees check karo", "IRCTC pe PNR status", "is form ko bhar do"), call browse_web with the full goal and the site if known. It opens a real browser on the server; it never logs in or pays, and asks on screen before submitting. If it says it is still working, tell the user you'll tell them as soon as it's done: the result will come to you in the call as a "(Santosh Browser result ...)" note; then tell the user the answer right away. If they ask before that, call browse_result.
- Places and travel: maps_search for shops, hospitals, restaurants or any place nearby ("paas mein medical store"), maps_directions for distance, time and traffic ("station kitni der mein pahunchunga"), maps_navigate to start navigation on the phone. Speak distances and minutes naturally.
- Google Drive/Sheets/Docs: drive_find to locate a file, drive_read_file or sheet_read to read it, sheet_append to add a row, doc_create to make a doc. Read out the gist, not every cell.
- Calendar: use calendar_agenda for the schedule, calendar_add_event to book something (work out the exact time), calendar_find_event + calendar_cancel_event to cancel. Confirm in one line what you added. This is their Google Calendar and syncs everywhere.
- Email: use email_check to see the inbox and email_read to read a mail. For a reply, use email_draft (write the full reply yourself); tell the user it is ready and they approve it in the app. Read a mail's gist aloud in a line or two; don't read the whole thing unless asked.
- Internet: use google_search for anything current or factual (news, prices, scores, train timings, shop numbers, rules) instead of guessing, and open_website to read a specific site. Speak the answer simply in one or two lines; don't read out links. Say "Google pe dekh raha hoon" while it searches. Use open_on_phone when the user wants a site opened on their phone.
- While a tool runs, say a quick natural line like "ek second, laga deta hoon" and keep the conversation going. When the result comes back, tell it in one line. Never say something is done before the tool confirms it.
- Work out exact dates and times from what the user says ("kal subah" is tomorrow 8 AM unless they gave a time). The user's local time now is {now}.

Honesty
- You are Santosh, an AI coworker. If someone asks whether you are a human, say honestly and warmly that you are an AI.

About the user
{context}"""


def _tool_specs() -> list[dict]:
    return [t for t in TOOLS if t["name"] in VOICE_TOOL_NAMES] + [DELEGATE]


# Settings this Gemini model refused ("Unknown name ..."); learned at runtime and skipped from then on.
UNSUPPORTED: set[str] = set()


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def unsupported_field(err: Exception) -> str | None:
    """'Unknown name "proactivity" at 'setup'' -> 'proactivity' (only for fields we can safely drop)."""
    m = re.search(r'Unknown name \\?"(\w+)\\?"', str(err))
    if not m:
        return None
    f = _snake(m.group(1))
    return f if f in DROPPABLE and f not in UNSUPPORTED else None


# nice-to-have settings: the call still works without them
DROPPABLE = {"proactivity", "proactive_audio", "enable_affective_dialog", "context_window_compression",
             "session_resumption", "output_audio_transcription", "input_audio_transcription",
             "end_of_speech_sensitivity", "start_of_speech_sensitivity", "prefix_padding_ms", "silence_duration_ms",
             "automatic_activity_detection", "realtime_input_config", "sliding_window"}


def live_config(voice: str, lang: str, context: str, handle: str | None):
    from google.genai import types
    st = get_settings()
    tz = life.tz_of(st.tenant_id)
    prompt = PERSONA.format(lang=lang, now=datetime.now(tz).strftime("%A %d %B %Y, %I:%M %p"), context=context or "(nothing saved yet)")
    decls = [types.FunctionDeclaration(name=t["name"], description=t["description"], parameters_json_schema=t["input_schema"])
             for t in _tool_specs()]
    cfg = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))),
        system_instruction=types.Content(parts=[types.Part(text=prompt)]),
        tools=[types.Tool(function_declarations=decls)],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                # LOW end-of-speech sensitivity + a longer silence = he waits for you to finish your thought
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                prefix_padding_ms=300,
                silence_duration_ms=st.voice_silence_ms,
            )),
        # Native audio already hears your tone; these two extras are off unless the model supports them
        enable_affective_dialog=True if st.voice_affective_dialog else None,
        proactivity=types.ProactivityConfig(proactive_audio=True) if st.voice_proactive_audio else None,
        session_resumption=types.SessionResumptionConfig(handle=handle),
        context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()),
    )
    for f in UNSUPPORTED:
        if f == "proactive_audio":
            f = "proactivity"
        if f == "sliding_window":
            f = "context_window_compression"
        if f in type(cfg).model_fields:
            setattr(cfg, f, None)
        elif cfg.realtime_input_config and cfg.realtime_input_config.automatic_activity_detection is not None \
                and f in type(cfg.realtime_input_config.automatic_activity_detection).model_fields:
            setattr(cfg.realtime_input_config.automatic_activity_detection, f, None)
    return cfg


def _default_connector(config):
    from google.genai import Client
    st = get_settings()
    client = Client(api_key=st.gemini_api_key, http_options={"api_version": "v1beta"})
    return client.aio.live.connect(model=st.gemini_live_model, config=config)


# tests swap this for a fake Live session
connector = _default_connector


def _save_turn(conv: str, user_text: str, reply: str) -> None:
    """Keep the call in the chat history so the chat (and Claude) know what was said."""
    from .agent.santosh import _save
    if user_text:
        _save(conv, "user", f"[Voice call] {user_text}", display=user_text)
        bus.publish(conv, "message", {"role": "user", "text": user_text, "source": "voice"})
    if reply:
        _save(conv, "assistant", [{"type": "text", "text": reply}], display=reply)
        bus.publish(conv, "message", {"role": "assistant", "text": reply, "source": "voice"})


# live calls by conversation, so background results (e.g. Santosh Browser) can be spoken into the call
ACTIVE: dict[str, list] = {}


def inject(conversation_id: str, text: str) -> int:
    """Hand a note to every live call on this conversation (thread-safe). Returns how many calls got it."""
    n = 0
    for loop, call in list(ACTIVE.get(conversation_id, [])):
        try:
            loop.call_soon_threadsafe(call.audio.put_nowait, ("text", text[:2000]))
            n += 1
        except RuntimeError:
            pass
    return n


class Call:
    def __init__(self, ws: WebSocket, conv: str, voice: str, lang: str, tenant: str | None = None):
        st = get_settings()
        self.ws, self.conv, self.lang = ws, conv, lang
        self.voice = voice if voice in MALE_VOICES else st.voice_default
        self.ctx = Ctx(tenant or st.tenant_id, conv)
        self.tenant = tenant or st.tenant_id
        self.audio: asyncio.Queue = asyncio.Queue(maxsize=400)
        self.closed = asyncio.Event()
        self.muted = False
        self.handle: str | None = None
        self.user_buf = ""
        self.reply_buf = ""
        self._send_lock = asyncio.Lock()
        self._tools: set[asyncio.Task] = set()

    async def send_json(self, obj: dict) -> None:
        if self.closed.is_set():
            return
        async with self._send_lock:
            with contextlib.suppress(Exception):
                await self.ws.send_text(json.dumps(obj, ensure_ascii=False))

    async def send_audio(self, data: bytes) -> None:
        if self.closed.is_set():
            return
        async with self._send_lock:
            with contextlib.suppress(Exception):
                await self.ws.send_bytes(data)

    # ---- phone side ----
    async def phone_reader(self) -> None:
        try:
            while True:
                msg = await self.ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes"):
                    if not self.muted:
                        if self.audio.full():
                            self.audio.get_nowait()   # drop the oldest chunk rather than lag behind
                        self.audio.put_nowait(("audio", msg["bytes"]))
                elif msg.get("text"):
                    try:
                        m = json.loads(msg["text"])
                    except ValueError:
                        continue
                    t = m.get("type")
                    if t == "end":
                        break
                    if t == "mute":
                        self.muted = True
                    elif t == "unmute":
                        self.muted = False
                    elif t == "text" and m.get("text"):
                        self.audio.put_nowait(("text", str(m["text"])[:2000]))
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            self.closed.set()

    # ---- model side ----
    async def uplink(self, session) -> None:
        from google.genai import types
        while True:
            kind, data = await self.audio.get()
            if kind == "audio":
                await session.send_realtime_input(audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000"))
            else:
                await session.send_realtime_input(text=data)

    async def downlink(self, session) -> str:
        """Returns 'reconnect' when Gemini asks us to move to a new connection."""
        while True:
            got_any = False
            async for m in session.receive():
                got_any = True
                upd = getattr(m, "session_resumption_update", None)
                if upd is not None and getattr(upd, "resumable", False) and getattr(upd, "new_handle", None):
                    self.handle = upd.new_handle
                if getattr(m, "go_away", None) is not None:
                    return "reconnect"
                if getattr(m, "tool_call", None) is not None:
                    for fc in m.tool_call.function_calls or []:
                        t = asyncio.create_task(self.run_tool(session, fc))
                        self._tools.add(t)
                        t.add_done_callback(self._tools.discard)
                sc = getattr(m, "server_content", None)
                if sc is None:
                    continue
                if sc.interrupted:
                    await self.send_json({"type": "interrupted"})
                if sc.input_transcription is not None and sc.input_transcription.text:
                    self.user_buf += sc.input_transcription.text
                    await self.send_json({"type": "user_text", "text": self.user_buf.strip()})
                if sc.model_turn is not None:
                    for part in sc.model_turn.parts or []:
                        blob = getattr(part, "inline_data", None)
                        if blob is not None and blob.data:
                            await self.send_audio(blob.data)
                if sc.output_transcription is not None and sc.output_transcription.text:
                    self.reply_buf += sc.output_transcription.text
                    await self.send_json({"type": "santosh_text", "text": self.reply_buf.strip()})
                if sc.turn_complete:
                    await self.finish_turn()
            if not got_any:
                return "reconnect"   # the stream ended without messages: connection is gone

    async def finish_turn(self) -> None:
        user, reply = self.user_buf.strip(), self.reply_buf.strip()
        self.user_buf = self.reply_buf = ""
        await self.send_json({"type": "turn_done"})
        if user or reply:
            try:
                _save_turn(self.conv, user, reply)
            except Exception:
                log.exception("could not save voice turn")

    async def run_tool(self, session, fc) -> None:
        from google.genai import types
        name, args = fc.name, dict(fc.args or {})
        label = "Santosh kaam kar raha hai" if name == "santosh_kaam" else TOOL_LABELS.get(name, name)
        await self.send_json({"type": "tool", "label": label, "state": "running"})
        try:
            if name == "santosh_kaam":
                from .agent import run_turn
                out = {"result": await run_turn(self.conv, str(args.get("request", "")), tenant_id=self.ctx.tenant_id)}
            elif name == "artifact_make":   # builds in the background; the page pops up on screen when ready
                out = {"result": await dispatch(name, {**args, "_wait": 0}, self.ctx)}
            elif name == "browse_web":   # a call can't wait minutes: short wait, the result comes in the chat
                out = {"result": await dispatch(name, {**args, "_wait": 25}, self.ctx)}
            elif name in VOICE_TOOL_NAMES:
                out = {"result": await dispatch(name, args, self.ctx)}
            else:
                out = {"error": f"Unknown tool {name}"}
            state = "done"
        except ToolError as e:
            out, state = {"error": str(e)}, "error"
        except Exception as e:
            log.exception("voice tool %s failed", name)
            out, state = {"error": f"Internal error: {e}"}, "error"
        await self.send_json({"type": "tool", "label": label, "state": state})
        resp = json.loads(json.dumps(out, default=str))   # make it plain JSON
        try:
            await session.send_tool_response(function_responses=[types.FunctionResponse(
                id=fc.id, name=name, response=resp, scheduling=types.FunctionResponseScheduling.WHEN_IDLE)])
        except Exception:
            log.warning("tool result for %s could not be delivered (session moved on)", name)

    async def run(self) -> None:
        reader = asyncio.create_task(self.phone_reader())
        first = True
        failures = 0
        me = (asyncio.get_running_loop(), self)
        ACTIVE.setdefault(self.ctx.conversation_id, []).append(me)
        try:
            while not self.closed.is_set():
                context = life.context_block(self.ctx.tenant_id)
                try:
                    started = asyncio.get_running_loop().time()
                    async with connector(live_config(self.voice, self.lang, context, self.handle)) as session:
                        if first:
                            await self.send_json({"type": "ready", "voice": self.voice})
                            from google.genai import types
                            # live text input (3.x Live models accept client_content only for seeding history)
                            await session.send_realtime_input(
                                text="(The call just connected. Greet the user warmly in one short, natural line, by name if you know it.)")
                            first = False
                        up = asyncio.create_task(self.uplink(session))
                        down = asyncio.create_task(self.downlink(session))
                        closed = asyncio.create_task(self.closed.wait())
                        done, _ = await asyncio.wait({up, down, closed}, return_when=asyncio.FIRST_COMPLETED)
                        for t in (up, down, closed):
                            t.cancel()
                        for t in done:
                            if t is not closed and not t.cancelled() and t.exception() is not None:
                                log.warning("voice stream ended: %r", t.exception())
                                raise t.exception()
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    bad = unsupported_field(e)
                    if bad:
                        # this model doesn't know one optional setting: drop it and reconnect straight away
                        log.warning("Gemini refused setting %s; retrying without it", bad)
                        UNSUPPORTED.add(bad)
                        continue
                    if self.handle and re.search(r"not found or expired|session.*expired|resum", str(e), re.I):
                        # the old session is gone on Google's side: start a fresh one instead of resuming
                        log.warning("resume failed (%s); starting a fresh voice session", e)
                        self.handle = None
                        failures += 1
                        if failures < 4:
                            continue
                    # a session that dies within seconds is a real failure, not a normal reconnect
                    lived = asyncio.get_running_loop().time() - started if "started" in locals() else 0
                    if lived > 30:
                        failures = 0
                    failures += 1
                    log.warning("voice session error (%s): %r", failures, e)
                    self.first_error = getattr(self, "first_error", None) or str(e)
                    if failures >= 3 or self.closed.is_set():
                        first = getattr(self, "first_error", None)
                        detail = str(e) if not first or first == str(e) else f"{first} (phir: {e})"
                        await self.send_json({"type": "error", "message": f"Voice connection toot gaya: {detail}"})
                        break
                    await asyncio.sleep(0.5 * failures)
        finally:
            with contextlib.suppress(ValueError, KeyError):
                ACTIVE[self.ctx.conversation_id].remove(me)
            for t in list(self._tools):
                t.cancel()
            reader.cancel()
            self.closed.set()
            if self.user_buf or self.reply_buf:
                await self.finish_turn()
            with contextlib.suppress(Exception):
                await self.ws.close()
