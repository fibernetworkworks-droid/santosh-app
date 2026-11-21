"""Telephony adapters behind one interface. Official, documented routes only.

Primary: Plivo (India number for an India-registered business after KYC; bidirectional <Stream>; every webhook and the
WebSocket upgrade signed with X-Plivo-Signature-V3 = base64(HMAC-SHA256(auth_token, url[+sorted params] + "." + nonce)),
the algorithm copied from plivo-python 4.63.0 utils/signature_v3.py; transfer = Call update aleg_url -> our Dial XML;
hang-up = DELETE Call). Also: Exotel Voicebot applet (slin PCM, Basic Auth on the stream URL; transfer / hang-up are the
flow's next applets after the stream closes) and a fake line for tests and for trying the script.

Each adapter turns provider WebSocket frames into plain events for the bridge:
  {"type": "start", "call": provider call id, "stream": id, "from": "+91..", "to": "+91..", "params": {...}}
  {"type": "audio", "pcm": 16-bit PCM at `line.rate`} | {"type": "dtmf", "digit"} | {"type": "mark", "name"} | {"type": "stop"}
and the bridge's audio back into frames (`out_audio`), plus `clear()` to cut off what is queued (caller spoke over him).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from typing import Any
from urllib.parse import parse_qsl, urlparse, urlunparse
from xml.sax.saxutils import escape, quoteattr

import httpx

from . import audio as A
from . import rules as R

log = logging.getLogger("santosh.callcentre")

_TRANSPORT: httpx.BaseTransport | None = None
FAKE_ACTIONS: list[dict[str, Any]] = []        # what the fake provider was asked to do (tests read it)


def set_transport(t: httpx.BaseTransport | None) -> None:
    """Tests route provider REST calls to a fake server."""
    global _TRANSPORT
    _TRANSPORT = t


def _client(**kw) -> httpx.Client:
    return httpx.Client(timeout=12, transport=_TRANSPORT, **kw)


class ProviderError(Exception):
    pass


# ---------------------------------------------------------------- Plivo V3 signature (exactly as the official SDK)
def _sorted_query(params: dict[str, Any]) -> str:
    out = []
    for k in sorted(params):
        v = params[k]
        if isinstance(v, list):
            out.append("&".join(f"{k}={x}" for x in sorted(str(y) for y in v)))
        else:
            out.append(f"{k}={v}")
    return "&".join(out)


def _sorted_params(params: dict[str, Any]) -> str:
    out = []
    for k in sorted(params):
        v = params[k]
        if isinstance(v, list):
            out.append("".join(f"{k}{x}" for x in sorted(str(y) for y in v)))
        elif isinstance(v, dict):
            out.append(f"{k}{_sorted_params(v)}")
        else:
            out.append(f"{k}{v}")
    return "".join(out)


def _get_url(uri: str, params: dict[str, Any], empty_post_params: bool = True) -> str:
    p = urlparse(uri)
    base = urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
    allp = dict(params)
    allp.update(dict(parse_qsl(p.query, keep_blank_values=True)))
    q = _sorted_query(allp)
    if q or not empty_post_params:
        base += "?" + q
    if q and not empty_post_params:
        base += "."
    return base


def plivo_base(method: str, uri: str, params: dict[str, Any] | None = None) -> str:
    params = dict(params or {})
    if method.upper() == "GET":
        return _get_url(uri, params)
    return _get_url(uri, {}, len(params) == 0) + _sorted_params(params)


def plivo_signature(auth_token: str, method: str, uri: str, nonce: str, params: dict[str, Any] | None = None) -> str:
    base = f"{plivo_base(method, uri, params)}.{nonce}".encode()
    return base64.b64encode(hmac.new(auth_token.encode(), base, hashlib.sha256).digest()).decode().strip()


def plivo_valid(auth_token: str, method: str, uri: str, nonce: str, signature: str, params: dict[str, Any] | None = None) -> bool:
    if not (auth_token and nonce and signature):
        return False
    mine = plivo_signature(auth_token, method, uri, nonce, params)
    return any(hmac.compare_digest(mine, s.strip()) for s in signature.split(","))


# ---------------------------------------------------------------- lines (one per call WebSocket)
class Line:
    rate = 8000
    stream = ""

    def parse(self, text: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def out_audio(self, pcm: bytes) -> list[str]:
        raise NotImplementedError

    def clear(self) -> str | None:
        return None

    def flush(self) -> list[str]:
        return []


class PlivoLine(Line):
    def __init__(self, content_type: str = "audio/x-mulaw;rate=8000"):
        self.mulaw = "mulaw" in content_type
        self.rate = 16000 if "16000" in content_type else 8000

    def parse(self, text: str) -> list[dict[str, Any]]:
        try:
            m = json.loads(text)
        except ValueError:
            return []
        ev = str(m.get("event") or "")
        if ev == "start":
            st = m.get("start") or {}
            self.stream = str(st.get("streamId") or m.get("streamId") or "")
            fmt = st.get("mediaFormat") or {}
            if fmt:
                self.mulaw = "mulaw" in str(fmt.get("encoding", "audio/x-mulaw"))
                self.rate = int(fmt.get("sampleRate") or self.rate)
            extra = m.get("extra_headers") or st.get("extra_headers") or ""
            params = dict(x.split("=", 1) for x in str(extra).split(";") if "=" in x) if isinstance(extra, str) else dict(extra)
            return [{"type": "start", "call": str(st.get("callId") or ""), "stream": self.stream, "params": params}]
        if ev == "media":
            raw = base64.b64decode((m.get("media") or {}).get("payload") or "")
            return [{"type": "audio", "pcm": A.ulaw_to_pcm(raw) if self.mulaw else raw}]
        if ev == "dtmf":
            return [{"type": "dtmf", "digit": str((m.get("dtmf") or {}).get("digit") or "")}]
        if ev == "playedStream":
            return [{"type": "mark", "name": str(m.get("name") or "")}]
        if ev == "stop":
            return [{"type": "stop"}]
        return []

    def out_audio(self, pcm: bytes) -> list[str]:
        if not pcm:
            return []
        payload = A.pcm_to_ulaw(pcm) if self.mulaw else pcm
        return [json.dumps({"event": "playAudio", "media": {
            "contentType": "audio/x-mulaw" if self.mulaw else "audio/x-l16", "sampleRate": self.rate,
            "payload": base64.b64encode(payload).decode()}})]

    def clear(self) -> str | None:
        return json.dumps({"event": "clearAudio", "streamId": self.stream})


class ExotelLine(Line):
    def __init__(self, rate: int = 8000):
        self.rate = rate
        self.chunk = A.Chunker(max(3200, (rate // 10) * 2 // 320 * 320))   # >= 100 ms, a multiple of 320 bytes

    def parse(self, text: str) -> list[dict[str, Any]]:
        try:
            m = json.loads(text)
        except ValueError:
            return []
        ev = str(m.get("event") or "")
        if ev == "start":
            st = m.get("start") or {}
            self.stream = str(m.get("stream_sid") or st.get("stream_sid") or "")
            fmt = st.get("media_format") or {}
            if fmt.get("sample_rate"):
                self.rate = int(fmt["sample_rate"])
            return [{"type": "start", "call": str(st.get("call_sid") or ""), "stream": self.stream,
                     "from": str(st.get("from") or ""), "to": str(st.get("to") or ""),
                     "params": dict(st.get("custom_parameters") or {})}]
        if ev == "media":
            return [{"type": "audio", "pcm": base64.b64decode((m.get("media") or {}).get("payload") or "")}]
        if ev == "dtmf":
            return [{"type": "dtmf", "digit": str((m.get("dtmf") or {}).get("digit") or "")}]
        if ev == "mark":
            return [{"type": "mark", "name": str((m.get("mark") or {}).get("name") or "")}]
        if ev == "stop":
            return [{"type": "stop"}]
        return []

    def _frame(self, b: bytes) -> str:
        return json.dumps({"event": "media", "stream_sid": self.stream, "media": {"payload": base64.b64encode(b).decode()}})

    def out_audio(self, pcm: bytes) -> list[str]:
        return [self._frame(b) for b in self.chunk.add(pcm)]

    def flush(self) -> list[str]:
        b = self.chunk.flush(320)
        return [self._frame(b)] if b else []

    def clear(self) -> str | None:
        self.chunk.buf = b""
        return json.dumps({"event": "clear", "stream_sid": self.stream})


class FakeLine(Line):
    rate = 8000

    def parse(self, text: str) -> list[dict[str, Any]]:
        try:
            m = json.loads(text)
        except ValueError:
            return []
        ev = m.get("event")
        if ev == "start":
            self.stream = str(m.get("stream") or "fs1")
            return [{"type": "start", "call": str(m.get("call") or ""), "stream": self.stream,
                     "from": str(m.get("from") or ""), "to": str(m.get("to") or ""), "params": dict(m.get("params") or {})}]
        if ev == "media":
            return [{"type": "audio", "pcm": base64.b64decode(m.get("payload") or "")}]
        if ev == "dtmf":
            return [{"type": "dtmf", "digit": str(m.get("digit") or "")}]
        if ev == "stop":
            return [{"type": "stop"}]
        return []

    def out_audio(self, pcm: bytes) -> list[str]:
        return [json.dumps({"event": "media", "payload": base64.b64encode(pcm).decode()})] if pcm else []

    def clear(self) -> str | None:
        return json.dumps({"event": "clear"})


# ---------------------------------------------------------------- providers
def _speak_lang(lang: str) -> str:
    return "en-IN" if lang == "en-IN" else "hi-IN"     # Marathi lines are written in Roman letters: read with the Indian voice


class Provider:
    name = ""
    xml = True

    def __init__(self, creds: dict[str, Any] | None = None):
        self.creds = dict(creds or {})

    # webhooks
    def verify(self, method: str, url: str, params: dict[str, Any], headers: dict[str, str], secret: str = "") -> bool:
        raise NotImplementedError

    def call_info(self, params: dict[str, Any]) -> dict[str, str]:
        raise NotImplementedError

    # answers to the call webhook
    def stream(self, ws_url: str, record: bool, extra: dict[str, str]) -> tuple[str, str]:
        raise NotImplementedError

    def say(self, text: str, lang: str, dial: str = "", caller_id: str = "") -> tuple[str, str]:
        raise NotImplementedError

    def hold(self, text: str, lang: str, redirect: str, wait_s: int = 15) -> tuple[str, str]:
        raise NotImplementedError

    def line(self) -> Line:
        raise NotImplementedError

    # during the call
    def transfer(self, provider_call: str, transfer_url: str) -> dict[str, Any]:
        raise NotImplementedError

    def hangup(self, provider_call: str) -> dict[str, Any]:
        raise NotImplementedError

    closes_stream_to_transfer = False   # Exotel: the flow's Connect applet runs after the stream ends
    outbound = False                    # v0.999.67: can place calls (AI calls out)
    machine_check = False               # tells a person from an answering machine

    def dial(self, to: str, caller_id: str, answer_url: str, hangup_url: str, machine_url: str = "",
             ring_s: int = 30) -> dict[str, Any]:
        """Place one call (v0.999.67 AI calls out). -> {"call": provider id (may be a request id)}."""
        raise ProviderError(f"{self.name} cannot place calls from Hoola.")

    def answered_by(self, params: dict[str, Any]) -> str:
        """human | machine | unknown, from the provider's own answering-machine check (if it has one)."""
        return "unknown"

    # v0.999.68 every provider: one webhook can carry several kinds of event (Vonage / Sinch / Bandwidth / jambonz)
    def event(self, params: dict[str, Any], hook: str) -> str:
        """What a webhook means: answer | end | machine | other. By default the hook's own name says it."""
        return {"answer": "answer", "hangup": "end", "machine": "machine"}.get(hook, "other")

    def end_status(self, params: dict[str, Any]) -> str:
        return str(params.get("HangupCause") or params.get("CallStatus") or params.get("Status") or params.get("status") or "")

    def seconds(self, params: dict[str, Any]) -> float | None:
        dur = (params.get("Duration") or params.get("BillDuration") or params.get("CallDuration") or params.get("seconds")
               or params.get("duration"))
        try:
            return float(dur) if dur not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def ack(self) -> tuple[str, str]:
        """The answer to a webhook that needs nothing done."""
        return "", "text/plain"


class Plivo(Provider):
    name = "plivo"
    API = "https://api.plivo.com/v1/Account"

    def verify(self, method, url, params, headers, secret=""):
        h = {k.lower(): v for k, v in headers.items()}
        return plivo_valid(str(self.creds.get("auth_token") or ""), method, url, h.get("x-plivo-signature-v3-nonce", ""),
                           h.get("x-plivo-signature-v3", ""), params if method.upper() == "POST" else None)

    def call_info(self, params):
        return {"call": str(params.get("CallUUID") or ""), "from": R.phone_e164(params.get("From")) or str(params.get("From") or ""),
                "to": R.phone_e164(params.get("To")) or str(params.get("To") or ""), "direction": str(params.get("Direction") or "")}

    def stream(self, ws_url, record, extra):
        rec = '<Record recordSession="true" redirect="false" maxLength="3600" />' if record else ""
        eh = ";".join(f"{k}={v}" for k, v in extra.items() if k and v)
        return ("<Response>" + rec +
                f'<Stream bidirectional="true" keepCallAlive="true" contentType="audio/x-mulaw;rate=8000"'
                f' extraHeaders={quoteattr(eh)}>{escape(ws_url)}</Stream></Response>', "application/xml")

    def say(self, text, lang, dial="", caller_id=""):
        body = f'<Speak language="{_speak_lang(lang)}">{escape(text)}</Speak>'
        if dial:
            cid = f' callerId={quoteattr(caller_id)}' if caller_id else ""
            body += f'<Dial{cid} timeout="30"><Number>{escape(dial)}</Number></Dial>'
        else:
            body += "<Hangup />"
        return f"<Response>{body}</Response>", "application/xml"

    def hold(self, text, lang, redirect, wait_s=15):
        return (f'<Response><Speak language="{_speak_lang(lang)}">{escape(text)}</Speak><Wait length="{int(wait_s)}" />'
                f"<Redirect>{escape(redirect)}</Redirect></Response>", "application/xml")

    def line(self):
        return PlivoLine()

    def _url(self, call: str) -> str:
        aid = str(self.creds.get("auth_id") or "")
        if not aid or not self.creds.get("auth_token"):
            raise ProviderError("Enter the Plivo Auth ID / Auth Token in the app.")
        return f"{self.API}/{aid}/Call/{call}/"

    def transfer(self, provider_call, transfer_url):
        with _client(auth=(str(self.creds.get("auth_id")), str(self.creds.get("auth_token")))) as c:
            r = c.post(self._url(provider_call), json={"legs": "aleg", "aleg_url": transfer_url, "aleg_method": "POST"})
        if r.status_code >= 300:
            raise ProviderError(f"Plivo transfer failed ({r.status_code}).")
        return {"ok": True, "via": "plivo"}

    def hangup(self, provider_call):
        with _client(auth=(str(self.creds.get("auth_id")), str(self.creds.get("auth_token")))) as c:
            r = c.delete(self._url(provider_call))
        if r.status_code >= 300 and r.status_code != 404:
            raise ProviderError(f"Plivo hang-up failed ({r.status_code}).")
        return {"ok": True}

    outbound = True
    machine_check = True

    def dial(self, to, caller_id, answer_url, hangup_url, machine_url="", ring_s=30):
        aid = str(self.creds.get("auth_id") or "")
        if not aid or not self.creds.get("auth_token"):
            raise ProviderError("Enter the Plivo Auth ID / Auth Token in the app.")
        body = {"from": caller_id.lstrip("+"), "to": to.lstrip("+"), "answer_url": answer_url, "answer_method": "POST",
                "hangup_url": hangup_url, "hangup_method": "POST", "ring_timeout": int(ring_s)}
        if machine_url:
            body |= {"machine_detection": "true", "machine_detection_url": machine_url, "machine_detection_method": "POST"}
        with _client(auth=(aid, str(self.creds.get("auth_token")))) as c:
            r = c.post(f"{self.API}/{aid}/Call/", json=body)
        if r.status_code >= 300:
            raise ProviderError(f"Plivo did not place the call ({r.status_code}).")
        j = r.json() if r.content else {}
        rid = j.get("request_uuid")
        return {"call": str(rid[0] if isinstance(rid, list) else rid or "")}

    def answered_by(self, params):
        m = str(params.get("Machine") or "").lower()
        return "machine" if m == "true" else ("human" if m == "false" else "unknown")


class Exotel(Provider):
    """Exotel flow: Voicebot (our stream URL) -> Passthru (our /after URL: 200 = a transfer is wanted, 302 = no) ->
    Connect (dynamic URL: our /connect, gives the number) | Hangup. Requests carry no signature: the route token in the
    URL + Basic Auth on the stream (and IP whitelisting via Exotel support) are the protection."""
    name = "exotel"
    xml = False
    closes_stream_to_transfer = True

    def verify(self, method, url, params, headers, secret=""):
        return True     # the route token was already checked; Exotel has no request signatures

    def call_info(self, params):
        return {"call": str(params.get("CallSid") or ""), "from": R.phone_e164(params.get("CallFrom") or params.get("From")) or "",
                "to": R.phone_e164(params.get("CallTo") or params.get("To")) or "", "direction": str(params.get("Direction") or "")}

    def stream(self, ws_url, record, extra):
        return json.dumps({"url": ws_url}), "application/json"

    def say(self, text, lang, dial="", caller_id=""):
        return json.dumps({"say": text, "dial": dial}), "application/json"

    def hold(self, text, lang, redirect, wait_s=15):
        return json.dumps({"say": text}), "application/json"

    def line(self):
        return ExotelLine(int(self.creds.get("sample_rate") or 8000))

    def transfer(self, provider_call, transfer_url):
        return {"ok": True, "via": "exotel_flow"}     # the bridge closes the stream; the flow's Connect applet dials

    def hangup(self, provider_call):
        return {"ok": True, "via": "exotel_flow"}

    outbound = True

    def dial(self, to, caller_id, answer_url, hangup_url, machine_url="", ring_s=30):
        """Exotel connects the person to HER flow (Voicebot applet -> our stream). The flow id is set in the app."""
        sid, key, tok = (str(self.creds.get(k) or "") for k in ("sid", "api_key", "api_token"))
        flow = str(self.creds.get("flow_id") or "")
        sub = str(self.creds.get("subdomain") or "api.exotel.com")
        if not (sid and key and tok and flow):
            raise ProviderError("Enter the Exotel SID, API key, API token and the Voicebot flow id in the app.")
        data = {"From": to, "CallerId": caller_id, "Url": f"http://my.exotel.com/{sid}/exoml/start_voice/{flow}",
                "StatusCallback": hangup_url, "TimeLimit": 3600, "TimeOut": int(ring_s)}
        with _client(auth=(key, tok)) as c:
            r = c.post(f"https://{sub}/v1/Accounts/{sid}/Calls/connect.json", data=data)
        if r.status_code >= 300:
            raise ProviderError(f"Exotel did not place the call ({r.status_code}).")
        j = r.json() if r.content else {}
        return {"call": str(((j.get("Call") or {}).get("Sid")) or "")}


class Fake(Provider):
    """A test line: requests are signed with HMAC-SHA256(secret, METHOD + url + sorted params) in X-Fake-Signature."""
    name = "fake"

    @staticmethod
    def sign(secret: str, method: str, url: str, params: dict[str, Any]) -> str:
        base = method.upper() + url + _sorted_params(params)
        return hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()

    def verify(self, method, url, params, headers, secret=""):
        h = {k.lower(): v for k, v in headers.items()}
        return bool(secret) and hmac.compare_digest(self.sign(secret, method, url, params), h.get("x-fake-signature", ""))

    def call_info(self, params):
        return {"call": str(params.get("call") or ""), "from": R.phone_e164(params.get("from")) or str(params.get("from") or ""),
                "to": R.phone_e164(params.get("to")) or "", "direction": "inbound"}

    def stream(self, ws_url, record, extra):
        return json.dumps({"action": "stream", "url": ws_url, "record": record, "extra": extra}), "application/json"

    def say(self, text, lang, dial="", caller_id=""):
        return json.dumps({"action": "dial" if dial else "say", "text": text, "dial": dial, "caller_id": caller_id}), "application/json"

    def hold(self, text, lang, redirect, wait_s=15):
        return json.dumps({"action": "hold", "text": text, "redirect": redirect, "wait": wait_s}), "application/json"

    def line(self):
        return FakeLine()

    def transfer(self, provider_call, transfer_url):
        FAKE_ACTIONS.append({"do": "transfer", "call": provider_call, "url": transfer_url})
        return {"ok": True, "via": "fake"}

    def hangup(self, provider_call):
        FAKE_ACTIONS.append({"do": "hangup", "call": provider_call})
        return {"ok": True}

    outbound = True
    machine_check = True

    def dial(self, to, caller_id, answer_url, hangup_url, machine_url="", ring_s=30):
        n = len([a for a in FAKE_ACTIONS if a["do"] == "dial"]) + 1
        FAKE_ACTIONS.append({"do": "dial", "to": to, "from": caller_id, "answer": answer_url, "hangup": hangup_url,
                             "machine": machine_url})
        return {"call": f"fake-out-{n}"}

    def answered_by(self, params):
        return str(params.get("answered_by") or "unknown")


# ---------------------------------------------------------------- Twilio (worldwide numbers; v0.999.67 global)
def twilio_signature(auth_token: str, url: str, params: dict[str, Any] | None = None) -> str:
    """Twilio's documented webhook signature: base64(HMAC-SHA1(auth token, url + every POST param name+value, sorted))."""
    base = url + "".join(f"{k}{v}" for k, v in sorted((params or {}).items()))
    return base64.b64encode(hmac.new(auth_token.encode(), base.encode(), hashlib.sha1).digest()).decode()


class TwilioLine(Line):
    """Twilio Media Streams: mulaw 8 kHz JSON frames; media / mark / clear go back with the streamSid."""

    def parse(self, text: str) -> list[dict[str, Any]]:
        try:
            m = json.loads(text)
        except ValueError:
            return []
        ev = str(m.get("event") or "")
        if ev == "start":
            st = m.get("start") or {}
            self.stream = str(st.get("streamSid") or m.get("streamSid") or "")
            return [{"type": "start", "call": str(st.get("callSid") or ""), "stream": self.stream,
                     "params": dict(st.get("customParameters") or {})}]
        if ev == "media":
            return [{"type": "audio", "pcm": A.ulaw_to_pcm(base64.b64decode((m.get("media") or {}).get("payload") or ""))}]
        if ev == "dtmf":
            return [{"type": "dtmf", "digit": str((m.get("dtmf") or {}).get("digit") or "")}]
        if ev == "mark":
            return [{"type": "mark", "name": str((m.get("mark") or {}).get("name") or "")}]
        if ev == "stop":
            return [{"type": "stop"}]
        return []

    def out_audio(self, pcm: bytes) -> list[str]:
        if not pcm:
            return []
        return [json.dumps({"event": "media", "streamSid": self.stream,
                            "media": {"payload": base64.b64encode(A.pcm_to_ulaw(pcm)).decode()}})]

    def clear(self) -> str | None:
        return json.dumps({"event": "clear", "streamSid": self.stream})


class Twilio(Provider):
    """Twilio Programmable Voice: numbers in most countries. Webhooks signed with X-Twilio-Signature; the stream is a
    <Connect><Stream> (bidirectional Media Streams); calls placed with the Calls API, the answering-machine check is
    Twilio's own MachineDetection=DetectMessageEnd (the answer request then says AnsweredBy)."""
    name = "twilio"
    API = "https://api.twilio.com/2010-04-01/Accounts"
    outbound = True
    machine_check = True

    def _auth(self) -> tuple[str, str]:
        sid, tok = str(self.creds.get("account_sid") or ""), str(self.creds.get("auth_token") or "")
        if not (sid and tok):
            raise ProviderError("Enter the Twilio Account SID / Auth Token in the app.")
        return sid, tok

    def _base(self) -> str:
        return self.API

    def verify(self, method, url, params, headers, secret=""):
        tok = str(self.creds.get("auth_token") or "")
        sig = {k.lower(): v for k, v in headers.items()}.get("x-twilio-signature", "")
        return bool(tok and sig) and hmac.compare_digest(twilio_signature(tok, url, params if method.upper() == "POST" else {}), sig)

    def call_info(self, params):
        return {"call": str(params.get("CallSid") or ""), "from": str(params.get("From") or ""),
                "to": str(params.get("To") or ""), "direction": str(params.get("Direction") or "")}

    def answered_by(self, params):
        a = str(params.get("AnsweredBy") or "").lower()
        if a.startswith("machine") or a == "fax":
            return "machine"
        return "human" if a == "human" else "unknown"

    def stream(self, ws_url, record, extra):
        p = "".join(f"<Parameter name={quoteattr(k)} value={quoteattr(v)} />" for k, v in extra.items() if k and v)
        rec = '<Start><Recording recordingChannels="dual" /></Start>' if record else ""
        return f"<Response>{rec}<Connect><Stream url={quoteattr(ws_url)}>{p}</Stream></Connect></Response>", "application/xml"

    def say(self, text, lang, dial="", caller_id=""):
        body = f"<Say language={quoteattr(lang or 'en-US')}>{escape(text)}</Say>"
        if dial:
            cid = f" callerId={quoteattr(caller_id)}" if caller_id else ""
            body += f'<Dial{cid} timeout="30"><Number>{escape(dial)}</Number></Dial>'
        else:
            body += "<Hangup />"
        return f"<Response>{body}</Response>", "application/xml"

    def hold(self, text, lang, redirect, wait_s=15):
        return (f"<Response><Say language={quoteattr(lang or 'en-US')}>{escape(text)}</Say><Pause length=\"{int(wait_s)}\" />"
                f"<Redirect method=\"POST\">{escape(redirect)}</Redirect></Response>", "application/xml")

    def line(self):
        return TwilioLine()

    def transfer(self, provider_call, transfer_url):
        sid, tok = self._auth()
        with _client(auth=(sid, tok)) as c:
            r = c.post(f"{self._base()}/{sid}/Calls/{provider_call}.json", data={"Url": transfer_url, "Method": "POST"})
        if r.status_code >= 300:
            raise ProviderError(f"{self.name} transfer failed ({r.status_code}).")
        return {"ok": True, "via": "twilio"}

    def hangup(self, provider_call):
        sid, tok = self._auth()
        with _client(auth=(sid, tok)) as c:
            r = c.post(f"{self._base()}/{sid}/Calls/{provider_call}.json", data={"Status": "completed"})
        if r.status_code >= 300 and r.status_code != 404:
            raise ProviderError(f"{self.name} hang-up failed ({r.status_code}).")
        return {"ok": True}

    def dial(self, to, caller_id, answer_url, hangup_url, machine_url="", ring_s=30):
        sid, tok = self._auth()
        data = {"To": to, "From": caller_id, "Url": answer_url, "Method": "POST", "StatusCallback": hangup_url,
                "StatusCallbackMethod": "POST", "StatusCallbackEvent": "completed", "Timeout": int(ring_s)}
        if machine_url:
            data["MachineDetection"] = "DetectMessageEnd"
        with _client(auth=(sid, tok)) as c:
            r = c.post(f"{self._base()}/{sid}/Calls.json", data=data)
        if r.status_code >= 300:
            raise ProviderError(f"{self.name} did not place the call ({r.status_code}).")
        return {"call": str((r.json() if r.content else {}).get("sid") or "")}


# ---------------------------------------------------------------- v0.999.68 EVERY PROVIDER: the rest of the world
# Built from each company's public docs (Telnyx TeXML + Media Streaming, SignalWire cXML, Vonage Voice API + WebSockets,
# Bandwidth BXML StartStream, Sinch Voice SVAML connectStream, jambonz listen). NOT VERIFIED with a live call on any.
def _num(v: Any) -> str:
    """Any phone number a provider sends -> +E.164 ('' when there is none)."""
    s = str(v or "").strip()
    if isinstance(v, dict):
        s = str(v.get("endpoint") or v.get("number") or "")
    d = "".join(ch for ch in s if ch.isdigit())
    if not d:
        return ""
    if s.startswith("+") or len(d) > 10:
        return "+" + d.lstrip("0") if not s.startswith("+") and d.startswith("00") else "+" + d
    return R.phone_e164(d) or ("+" + d)


def _raw(headers: dict[str, str]) -> str:
    return {k.lower(): v for k, v in headers.items()}.get("x-hoola-raw", "")


def _locale(lang: str, sep: str = "-") -> str:
    lang = (lang or "en-US").replace("_", "-")
    return lang.replace("-", sep)


class BinaryLine(Line):
    """Raw 16-bit PCM in binary WebSocket frames (Vonage, Sinch, jambonz); JSON in text frames."""
    frame = 320

    def __init__(self, rate: int = 8000):
        self.rate = rate
        self.chunk = A.Chunker(self.frame)

    def text_event(self, m: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    def parse(self, data: str | bytes) -> list[dict[str, Any]]:
        if isinstance(data, (bytes, bytearray)):
            return [{"type": "audio", "pcm": bytes(data)}] if data else []
        try:
            m = json.loads(data)
        except (TypeError, ValueError):
            return []
        return self.text_event(m) if isinstance(m, dict) else []

    def out_audio(self, pcm: bytes) -> list[bytes]:
        return self.chunk.add(pcm)

    def flush(self) -> list[bytes]:
        b = self.chunk.flush(2)
        return [b] if b else []


# ---- Telnyx (numbers in 140+ countries; TeXML = Twilio-style XML; webhooks signed with Ed25519)
class TelnyxLine(Line):
    def parse(self, text: str) -> list[dict[str, Any]]:
        try:
            m = json.loads(text)
        except (TypeError, ValueError):
            return []
        ev = str(m.get("event") or "")
        if ev == "start":
            st = m.get("start") or {}
            self.stream = str(m.get("stream_id") or "")
            return [{"type": "start", "call": str(st.get("call_control_id") or st.get("call_sid") or ""), "stream": self.stream,
                     "params": dict(st.get("custom_parameters") or {})}]
        if ev == "media":
            md = m.get("media") or {}
            if str(md.get("track") or "inbound") != "inbound":
                return []
            return [{"type": "audio", "pcm": A.ulaw_to_pcm(base64.b64decode(md.get("payload") or ""))}]
        if ev == "dtmf":
            return [{"type": "dtmf", "digit": str((m.get("dtmf") or {}).get("digit") or "")}]
        if ev == "mark":
            return [{"type": "mark", "name": str((m.get("mark") or {}).get("name") or "")}]
        if ev == "stop":
            return [{"type": "stop"}]
        return []

    def out_audio(self, pcm: bytes) -> list[str]:
        if not pcm:
            return []
        return [json.dumps({"event": "media", "media": {"payload": base64.b64encode(A.pcm_to_ulaw(pcm)).decode()}})]

    def clear(self) -> str | None:
        return json.dumps({"event": "clear"})


def telnyx_valid(public_key: str, timestamp: str, signature: str, body: str, max_age_s: int = 300) -> bool:
    """Telnyx signs every webhook: Ed25519 over f"{telnyx-timestamp}|{raw body}" with its key (Portal > Keys > Public key)."""
    import time as _t
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if not (public_key and timestamp and signature):
        return False
    try:
        if abs(_t.time() - int(timestamp)) > max_age_s:
            return False
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key)).verify(
            base64.b64decode(signature), f"{timestamp}|{body}".encode())
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


class Telnyx(Twilio):
    name = "telnyx"
    API = "https://api.telnyx.com/v2/texml"

    def _key(self) -> str:
        k = str(self.creds.get("api_key") or "")
        if not k:
            raise ProviderError("Enter the Telnyx API key in the app.")
        return k

    def verify(self, method, url, params, headers, secret=""):
        h = {k.lower(): v for k, v in headers.items()}
        return telnyx_valid(str(self.creds.get("public_key") or ""), h.get("telnyx-timestamp", ""),
                            h.get("telnyx-signature-ed25519", ""), _raw(headers))

    def call_info(self, params):
        i = super().call_info(params)
        return i | {"from": _num(i["from"]) or i["from"], "to": _num(i["to"]) or i["to"]}

    def stream(self, ws_url, record, extra):
        return (f'<Response><Start><Stream url={quoteattr(ws_url)} track="inbound_track" bidirectionalMode="rtp" '
                f'bidirectionalCodec="PCMU" /></Start><Pause length="3600" /></Response>', "application/xml")

    def line(self):
        return TelnyxLine()

    def _update(self, provider_call: str, data: dict[str, Any], what: str) -> None:
        acc = str(self.creds.get("account_sid") or "")
        if not acc:
            raise ProviderError("Enter the Telnyx TeXML account SID in the app.")
        with _client(headers={"Authorization": f"Bearer {self._key()}"}) as c:
            r = c.post(f"{self.API}/Accounts/{acc}/Calls/{provider_call}", json=data)
        if r.status_code >= 300 and not (what == "hang-up" and r.status_code == 404):
            raise ProviderError(f"Telnyx {what} failed ({r.status_code}).")

    def transfer(self, provider_call, transfer_url):
        self._update(provider_call, {"Url": transfer_url, "Method": "POST"}, "transfer")
        return {"ok": True, "via": "telnyx"}

    def hangup(self, provider_call):
        self._update(provider_call, {"Status": "completed"}, "hang-up")
        return {"ok": True}

    def dial(self, to, caller_id, answer_url, hangup_url, machine_url="", ring_s=30):
        app = str(self.creds.get("application_id") or "")
        if not app:
            raise ProviderError("Enter the Telnyx TeXML application id in the app.")
        body = {"To": to, "From": caller_id, "Url": answer_url, "UrlMethod": "POST", "StatusCallback": hangup_url,
                "StatusCallbackMethod": "POST", "Timeout": int(ring_s)}
        if machine_url:
            body["MachineDetection"] = "DetectMessageEnd"
        with _client(headers={"Authorization": f"Bearer {self._key()}"}) as c:
            r = c.post(f"{self.API}/calls/{app}", json=body)
        if r.status_code >= 300:
            raise ProviderError(f"Telnyx did not place the call ({r.status_code}).")
        j = r.json() if r.content else {}
        j = j.get("data") or j
        return {"call": str(j.get("call_sid") or j.get("sid") or j.get("call_control_id") or "")}


# ---- SignalWire (cXML / LaML: the same XML and Media Streams as Twilio, on her SignalWire space)
class SignalWire(Twilio):
    name = "signalwire"

    def _base(self) -> str:
        space = str(self.creds.get("space") or "").strip().replace("https://", "").rstrip("/")
        if not space:
            raise ProviderError("Enter the SignalWire space (example.signalwire.com) in the app.")
        return f"https://{space}/api/laml/2010-04-01/Accounts"

    def _auth(self) -> tuple[str, str]:
        pid, tok = str(self.creds.get("project_id") or ""), str(self.creds.get("api_token") or "")
        if not (pid and tok):
            raise ProviderError("Enter the SignalWire Project ID / API token in the app.")
        return pid, tok

    def verify(self, method, url, params, headers, secret=""):
        key = str(self.creds.get("signing_key") or self.creds.get("api_token") or "")
        h = {k.lower(): v for k, v in headers.items()}
        sig = h.get("x-signalwire-signature") or h.get("x-twilio-signature") or ""
        return bool(key and sig) and hmac.compare_digest(twilio_signature(key, url, params if method.upper() == "POST" else {}), sig)

    def call_info(self, params):
        i = super().call_info(params)
        return i | {"from": _num(i["from"]) or i["from"], "to": _num(i["to"]) or i["to"]}


# ---- Vonage (Nexmo): NCCO JSON, raw L16 16 kHz over a WebSocket, signed webhooks (JWT with her signature secret)
class VonageLine(BinaryLine):
    frame = 640           # 20 ms at 16 kHz, what Vonage sends and takes

    def __init__(self):
        super().__init__(16000)

    def text_event(self, m):
        ev = str(m.get("event") or "")
        if ev == "websocket:connected":
            return [{"type": "start", "call": "", "stream": "", "params": {k: str(v) for k, v in m.items()
                                                                           if k not in ("event", "content-type")}}]
        if ev == "websocket:dtmf":
            return [{"type": "dtmf", "digit": str(m.get("digit") or (m.get("dtmf") or {}).get("digit") or "")}]
        return []

    def clear(self) -> str | None:
        self.chunk.buf = b""
        return json.dumps({"action": "clear"})


VONAGE_END = {"completed", "busy", "failed", "timeout", "unanswered", "rejected", "cancelled"}


class Vonage(Provider):
    name = "vonage"
    xml = False
    API = "https://api.nexmo.com/v1/calls"
    outbound = True
    machine_check = True

    def verify(self, method, url, params, headers, secret=""):
        import jwt as _jwt
        sec = str(self.creds.get("signature_secret") or "")
        auth = {k.lower(): v for k, v in headers.items()}.get("authorization", "")
        if not (sec and auth.lower().startswith("bearer ")):
            return False
        try:
            claims = _jwt.decode(auth[7:], sec, algorithms=["HS256"], options={"verify_aud": False})
        except Exception:   # noqa: BLE001
            return False
        ph = claims.get("payload_hash")
        if ph:
            return hmac.compare_digest(str(ph), hashlib.sha256(_raw(headers).encode()).hexdigest())
        return True

    def call_info(self, params):
        return {"call": str(params.get("uuid") or ""), "from": _num(params.get("from")), "to": _num(params.get("to")),
                "direction": str(params.get("direction") or "")}

    def event(self, params, hook):
        st = str(params.get("status") or "").lower()
        if hook == "answer":
            return "answer"
        if st in VONAGE_END:
            return "end"
        if st == "machine":
            return "machine"
        return "other"

    def answered_by(self, params):
        st = str(params.get("status") or "").lower()
        return "machine" if st == "machine" else ("human" if st == "human" else "unknown")

    def end_status(self, params):
        return str(params.get("status") or "")

    def ack(self):
        return "", "application/json"

    def _jwt(self) -> str:
        import time as _t
        import uuid as _u
        import jwt as _jwt
        aid, key = str(self.creds.get("application_id") or ""), str(self.creds.get("private_key") or "")
        if not (aid and key):
            raise ProviderError("Enter the Vonage Application ID and its private key in the app.")
        now = int(_t.time())
        return _jwt.encode({"application_id": aid, "iat": now, "exp": now + 300, "jti": str(_u.uuid4())}, key, algorithm="RS256")

    def stream(self, ws_url, record, extra):
        ncco: list[dict[str, Any]] = []
        if record:
            ncco.append({"action": "record", "split": "conversation", "channels": 2})
        ncco.append({"action": "connect", "endpoint": [{"type": "websocket", "uri": ws_url, "content-type": "audio/l16;rate=16000",
                                                        "headers": {k: v for k, v in extra.items() if k and v}}]})
        return json.dumps(ncco), "application/json"

    def say(self, text, lang, dial="", caller_id=""):
        ncco: list[dict[str, Any]] = []
        if text:
            ncco.append({"action": "talk", "text": text, "language": _locale(lang)})
        if dial:
            c: dict[str, Any] = {"action": "connect", "endpoint": [{"type": "phone", "number": dial.lstrip("+")}], "timeout": 30}
            if caller_id:
                c["from"] = caller_id.lstrip("+")
            ncco.append(c)
        return json.dumps(ncco), "application/json"

    def hold(self, text, lang, redirect, wait_s=15):
        return json.dumps([{"action": "talk", "text": text, "language": _locale(lang)},
                           {"action": "notify", "payload": {"hold": True}, "eventUrl": [redirect], "eventMethod": "POST"}]), \
            "application/json"

    def line(self):
        return VonageLine()

    def _put(self, provider_call: str, body: dict[str, Any], what: str) -> None:
        with _client(headers={"Authorization": f"Bearer {self._jwt()}"}) as c:
            r = c.put(f"{self.API}/{provider_call}", json=body)
        if r.status_code >= 300 and not (what == "hang-up" and r.status_code == 404):
            raise ProviderError(f"Vonage {what} failed ({r.status_code}).")

    def transfer(self, provider_call, transfer_url):
        self._put(provider_call, {"action": "transfer", "destination": {"type": "ncco", "url": [transfer_url]}}, "transfer")
        return {"ok": True, "via": "vonage"}

    def hangup(self, provider_call):
        self._put(provider_call, {"action": "hangup"}, "hang-up")
        return {"ok": True}

    def dial(self, to, caller_id, answer_url, hangup_url, machine_url="", ring_s=30):
        body: dict[str, Any] = {"to": [{"type": "phone", "number": to.lstrip("+")}],
                                "from": {"type": "phone", "number": caller_id.lstrip("+")},
                                "answer_url": [answer_url], "answer_method": "POST",
                                "event_url": [hangup_url], "event_method": "POST", "ringing_timer": int(ring_s)}
        if machine_url:
            body["machine_detection"] = "continue"
        with _client(headers={"Authorization": f"Bearer {self._jwt()}"}) as c:
            r = c.post(self.API, json=body)
        if r.status_code >= 300:
            raise ProviderError(f"Vonage did not place the call ({r.status_code}).")
        return {"call": str((r.json() if r.content else {}).get("uuid") or "")}


# ---- Bandwidth (US, Canada, Europe): BXML, a bidirectional <StartStream>, Basic Auth on her callbacks
class BandwidthLine(Line):
    def parse(self, text):
        try:
            m = json.loads(text)
        except (TypeError, ValueError):
            return []
        ev = str(m.get("eventType") or "")
        if ev == "start":
            md = m.get("metadata") or {}
            self.stream = str(md.get("streamId") or "")
            return [{"type": "start", "call": str(md.get("callId") or ""), "stream": self.stream,
                     "params": dict(md.get("streamParams") or {})}]
        if ev == "media":
            if str(m.get("track") or "inbound") != "inbound":
                return []
            return [{"type": "audio", "pcm": A.ulaw_to_pcm(base64.b64decode(m.get("payload") or ""))}]
        if ev == "stop":
            return [{"type": "stop"}]
        return []

    def out_audio(self, pcm):
        if not pcm:
            return []
        return [json.dumps({"eventType": "playAudio", "media": {"contentType": "audio/PCMU",
                                                                "payload": base64.b64encode(A.pcm_to_ulaw(pcm)).decode()}})]

    def clear(self):
        return json.dumps({"eventType": "clear"})


class Bandwidth(Provider):
    name = "bandwidth"
    API = "https://voice.bandwidth.com/api/v2/accounts"
    outbound = True
    machine_check = True

    def _auth(self) -> tuple[str, str, str]:
        acc, u, p = (str(self.creds.get(k) or "") for k in ("account_id", "username", "password"))
        if not (acc and u and p):
            raise ProviderError("Enter the Bandwidth account id, API user name and password in the app.")
        return acc, u, p

    def verify(self, method, url, params, headers, secret=""):
        u, p = str(self.creds.get("callback_user") or ""), str(self.creds.get("callback_password") or "")
        auth = {k.lower(): v for k, v in headers.items()}.get("authorization", "")
        if not (u and p and auth.lower().startswith("basic ")):
            return False
        try:
            gu, _, gp = base64.b64decode(auth[6:]).decode().partition(":")
        except (ValueError, UnicodeDecodeError):
            return False
        return hmac.compare_digest(gu, u) and hmac.compare_digest(gp, p)

    def call_info(self, params):
        return {"call": str(params.get("callId") or ""), "from": _num(params.get("from")), "to": _num(params.get("to")),
                "direction": str(params.get("direction") or "")}

    def event(self, params, hook):
        ev = str(params.get("eventType") or "")
        if ev in ("initiate", "answer"):
            return "answer"
        if ev == "disconnect":
            return "end"
        if ev == "machineDetectionComplete":
            return "machine" if self.answered_by(params) == "machine" else "other"
        return super().event(params, hook) if not ev else "other"

    def answered_by(self, params):
        v = str(((params.get("machineDetectionResult") or {}).get("value")) or "").lower()
        return "machine" if "machine" in v else ("human" if v == "human" else "unknown")

    def end_status(self, params):
        return str(params.get("cause") or params.get("errorMessage") or "")

    def stream(self, ws_url, record, extra):
        p = "".join(f"<StreamParam name={quoteattr(k)} value={quoteattr(v)} />" for k, v in extra.items() if k and v)
        rec = "<StartRecording />" if record else ""
        return (f'<Response>{rec}<StartStream name="hoola" mode="bidirectional" destination={quoteattr(ws_url)}>{p}</StartStream>'
                f'<Pause duration="3600" /></Response>', "application/xml")

    def say(self, text, lang, dial="", caller_id=""):
        body = f"<SpeakSentence>{escape(text)}</SpeakSentence>" if text else ""
        if dial:
            cid = f" transferCallerId={quoteattr(caller_id)}" if caller_id else ""
            body += f'<Transfer{cid} callTimeout="30"><PhoneNumber>{escape(dial)}</PhoneNumber></Transfer>'
        else:
            body += "<Hangup />"
        return f"<Response>{body}</Response>", "application/xml"

    def hold(self, text, lang, redirect, wait_s=15):
        return (f'<Response><SpeakSentence>{escape(text)}</SpeakSentence><Pause duration="{int(wait_s)}" />'
                f'<Redirect redirectUrl={quoteattr(redirect)} redirectMethod="POST" /></Response>', "application/xml")

    def line(self):
        return BandwidthLine()

    def _post(self, path: str, body: dict[str, Any], what: str) -> dict[str, Any]:
        acc, u, p = self._auth()
        with _client(auth=(u, p)) as c:
            r = c.post(f"{self.API}/{acc}/calls{path}", json=body)
        if r.status_code >= 300 and not (what == "hang-up" and r.status_code == 404):
            raise ProviderError(f"Bandwidth {what} failed ({r.status_code}).")
        return r.json() if r.content else {}

    def transfer(self, provider_call, transfer_url):
        self._post(f"/{provider_call}", {"redirectUrl": transfer_url, "redirectMethod": "POST"}, "transfer")
        return {"ok": True, "via": "bandwidth"}

    def hangup(self, provider_call):
        self._post(f"/{provider_call}", {"state": "completed"}, "hang-up")
        return {"ok": True}

    def dial(self, to, caller_id, answer_url, hangup_url, machine_url="", ring_s=30):
        app = str(self.creds.get("application_id") or "")
        if not app:
            raise ProviderError("Enter the Bandwidth voice application id in the app.")
        body: dict[str, Any] = {"from": caller_id, "to": to, "applicationId": app, "answerUrl": answer_url, "answerMethod": "POST",
                                "disconnectUrl": hangup_url, "disconnectMethod": "POST", "callTimeout": int(ring_s),
                                "username": str(self.creds.get("callback_user") or ""),
                                "password": str(self.creds.get("callback_password") or "")}
        if machine_url:
            body["machineDetection"] = {"mode": "async", "callbackUrl": machine_url, "callbackMethod": "POST",
                                        "username": body["username"], "password": body["password"]}
        return {"call": str(self._post("", body, "call").get("callId") or "")}


# ---- Sinch (a carrier in 60+ countries): SVAML, connectStream to our WebSocket, signed callbacks
class SinchLine(BinaryLine):
    def text_event(self, m):
        return [{"type": "start", "call": str(m.get("callId") or m.get("callid") or ""), "stream": "",
                 "params": {str(h.get("key")): str(h.get("value")) for h in (m.get("callHeaders") or []) if isinstance(h, dict)}}]


def sinch_signature(secret_b64: str, method: str, path: str, content_type: str, timestamp: str, body: str) -> str:
    md5 = base64.b64encode(hashlib.md5(body.encode()).digest()).decode() if body else ""
    to_sign = "\n".join([method.upper(), md5, content_type, f"x-timestamp:{timestamp}", path])
    return base64.b64encode(hmac.new(base64.b64decode(secret_b64), to_sign.encode(), hashlib.sha256).digest()).decode()


class Sinch(Provider):
    name = "sinch"
    xml = False
    API = "https://calling.api.sinch.com/calling/v1"
    outbound = True
    machine_check = True

    def _auth(self) -> tuple[str, str]:
        k, s = str(self.creds.get("app_key") or ""), str(self.creds.get("app_secret") or "")
        if not (k and s):
            raise ProviderError("Enter the Sinch application key and secret in the app.")
        return k, s

    def verify(self, method, url, params, headers, secret=""):
        k, sec = str(self.creds.get("app_key") or ""), str(self.creds.get("app_secret") or "")
        h = {x.lower(): v for x, v in headers.items()}
        auth = h.get("authorization", "")
        if not (k and sec and auth.startswith("Application ")):
            return False
        gk, _, sig = auth[len("Application "):].partition(":")
        try:
            mine = sinch_signature(sec, method, urlparse(url).path, h.get("content-type", ""), h.get("x-timestamp", ""),
                                   _raw(headers))
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(gk, k) and hmac.compare_digest(mine, sig)

    def call_info(self, params):
        to = params.get("to")
        return {"call": str(params.get("callid") or params.get("callId") or ""), "from": _num(params.get("cli")),
                "to": _num(to.get("endpoint") if isinstance(to, dict) else to), "direction": ""}

    def event(self, params, hook):
        ev = str(params.get("event") or "").lower()
        if ev in ("ice", "ace"):
            return "answer"
        if ev == "dice":
            return "end"
        return "other" if ev else super().event(params, hook)

    def answered_by(self, params):
        st = str(((params.get("amd") or {}).get("status")) or "").lower()
        return "machine" if st == "machine" else ("human" if st == "human" else "unknown")

    def end_status(self, params):
        return str(params.get("reason") or params.get("result") or "")

    def seconds(self, params):
        try:
            return float(params["duration"]) if params.get("duration") not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def ack(self):
        return json.dumps({"action": {"name": "continue"}}), "application/json"

    def stream(self, ws_url, record, extra):
        ins = [{"name": "startRecording"}] if record else []
        return json.dumps({"instructions": ins, "action": {
            "name": "connectStream", "destination": {"type": "websocket", "endpoint": ws_url},
            "streamingOptions": {"version": 1, "sampleRate": 8000}, "maxDuration": 3600,
            "callHeaders": [{"key": k, "value": v} for k, v in extra.items() if k and v]}}), "application/json"

    def _svaml(self, text: str, lang: str, dial: str = "", caller_id: str = "") -> dict[str, Any]:
        ins = [{"name": "say", "text": text, "locale": _locale(lang)}] if text else []
        act: dict[str, Any] = {"name": "hangup"}
        if dial:
            act = {"name": "connectPstn", "number": dial}
            if caller_id:
                act["cli"] = caller_id
        return {"instructions": ins, "action": act}

    def say(self, text, lang, dial="", caller_id=""):
        return json.dumps(self._svaml(text, lang, dial, caller_id)), "application/json"

    def hold(self, text, lang, redirect, wait_s=15):
        # SVAML cannot fetch a new answer by itself: say the line and end; the caller is told to call back
        return self.say(text, lang)

    def line(self):
        return SinchLine(8000)

    def _patch(self, provider_call: str, svaml: dict[str, Any], what: str) -> None:
        with _client(auth=self._auth()) as c:
            r = c.patch(f"{self.API}/calls/id/{provider_call}", json=svaml)
        if r.status_code >= 300 and not (what == "hang-up" and r.status_code == 404):
            raise ProviderError(f"Sinch {what} failed ({r.status_code}).")

    def transfer(self, provider_call, transfer_url):
        """SVAML takes no URL: read where the call goes (our own transfer / voicemail line) and send that SVAML."""
        from . import service as S
        q = dict(parse_qsl(urlparse(transfer_url).query))
        path = urlparse(transfer_url).path
        if "/voicemail" in path:
            from . import outbound as O
            row = S.call_row(q.get("out", ""))
            d = O.voicemail_line(row["tenant"], q.get("out", ""), q.get("ot", "")) if row else {"text": "", "lang": "en-US"}
            svaml = self._svaml(d.get("text") or "", d.get("lang") or "en-US")
        else:
            row = S.call_row(path.rsplit("/", 1)[-1]) or {}
            if not row.get("transfer_to"):
                raise ProviderError("No person to connect the call to.")
            with S.session() as s:
                num = S._row(s, row["tenant"]).number
            lang = row.get("lang") or R.default_lang()
            svaml = self._svaml(R.CONNECTING[R.lang3(lang)], lang, row["transfer_to"], num)
        self._patch(provider_call, svaml, "transfer")
        return {"ok": True, "via": "sinch"}

    def hangup(self, provider_call):
        self._patch(provider_call, {"instructions": [], "action": {"name": "hangup"}}, "hang-up")
        return {"ok": True}

    def dial(self, to, caller_id, answer_url, hangup_url, machine_url="", ring_s=30):
        ice = {"action": {"name": "connectPstn", "number": to, "cli": caller_id, "maxDuration": 3600,
                          "amd": {"enabled": bool(machine_url)}}}
        body = {"method": "customCallout", "customCallout": {"cli": caller_id, "destination": {"type": "number", "endpoint": to},
                                                             "ice": json.dumps(ice), "ace": answer_url, "dice": hangup_url}}
        with _client(auth=self._auth()) as c:
            r = c.post(f"{self.API}/callouts", json=body)
        if r.status_code >= 300:
            raise ProviderError(f"Sinch did not place the call ({r.status_code}).")
        return {"call": str((r.json() if r.content else {}).get("callId") or "")}


# ---- jambonz: open-source voice gateway in front of ANY SIP carrier in ANY country (her own trunk); listen verb
class JambonzLine(BinaryLine):
    def text_event(self, m):
        if m.get("type") == "killAudio":
            return []
        if "callSid" in m or "call_sid" in m or m.get("event") == "start":
            return [{"type": "start", "call": str(m.get("callSid") or m.get("call_sid") or ""), "stream": "",
                     "params": {k: str(v) for k, v in (m.get("metadata") or m.get("customParameters") or {}).items()}}]
        if m.get("event") == "dtmf":
            return [{"type": "dtmf", "digit": str(m.get("dtmf") or m.get("digit") or "")}]
        return []

    def clear(self) -> str | None:
        self.chunk.buf = b""
        return json.dumps({"type": "killAudio"})


JAMBONZ_END = {"completed", "failed", "busy", "no-answer", "noanswer"}


class Jambonz(Provider):
    name = "jambonz"
    xml = False
    outbound = True
    machine_check = True
    subprotocols = ("audio.jambonz.org",)

    def _api(self) -> tuple[str, str, str]:
        base = str(self.creds.get("base_url") or "https://api.jambonz.cloud").rstrip("/")
        key, acc = str(self.creds.get("api_key") or ""), str(self.creds.get("account_sid") or "")
        if not (key and acc):
            raise ProviderError("Enter the jambonz API key and account SID in the app.")
        return base, key, acc

    def verify(self, method, url, params, headers, secret=""):
        sec = str(self.creds.get("webhook_secret") or "")
        sig = {k.lower(): v for k, v in headers.items()}.get("jambonz-signature", "")
        if not (sec and sig):
            return False
        parts = dict(x.split("=", 1) for x in sig.split(",") if "=" in x)
        t, v1 = parts.get("t", ""), parts.get("v1", "")
        if not (t and v1):
            return False
        mine = hmac.new(sec.encode(), f"{t}.{_raw(headers)}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(mine, v1)

    def call_info(self, params):
        return {"call": str(params.get("call_sid") or ""), "from": _num(params.get("from")), "to": _num(params.get("to")),
                "direction": str(params.get("direction") or "")}

    def event(self, params, hook):
        if hook == "answer":
            return "answer"
        t = str(params.get("type") or "")
        if t.startswith("amd_"):
            return "machine" if "machine" in t else "other"
        st = str(params.get("call_status") or "").lower()
        if st in JAMBONZ_END:
            return "end"
        return "other"

    def answered_by(self, params):
        t = str(params.get("type") or "")
        return "machine" if "machine" in t else ("human" if "human" in t else "unknown")

    def end_status(self, params):
        return str(params.get("call_status") or params.get("sip_status") or "")

    def ack(self):
        return "[]", "application/json"

    def stream(self, ws_url, record, extra):
        return json.dumps([{"verb": "listen", "url": ws_url, "sampleRate": 8000, "mixType": "mono", "passDtmf": True,
                            "metadata": {k: v for k, v in extra.items() if k and v},
                            "bidirectionalAudio": {"enabled": True, "streaming": True, "sampleRate": 8000}}]), "application/json"

    def say(self, text, lang, dial="", caller_id=""):
        verbs: list[dict[str, Any]] = []
        if text:
            verbs.append({"verb": "say", "text": text, "synthesizer": {"language": _locale(lang)}})
        if dial:
            d: dict[str, Any] = {"verb": "dial", "target": [{"type": "phone", "number": dial}], "timeout": 30}
            if caller_id:
                d["callerId"] = caller_id
            verbs.append(d)
        else:
            verbs.append({"verb": "hangup"})
        return json.dumps(verbs), "application/json"

    def hold(self, text, lang, redirect, wait_s=15):
        return json.dumps([{"verb": "say", "text": text, "synthesizer": {"language": _locale(lang)}},
                           {"verb": "pause", "length": int(wait_s)},
                           {"verb": "redirect", "actionHook": {"url": redirect, "method": "POST"}}]), "application/json"

    def line(self):
        return JambonzLine(8000)

    def _put(self, provider_call: str, body: dict[str, Any], what: str) -> None:
        base, key, acc = self._api()
        with _client(headers={"Authorization": f"Bearer {key}"}) as c:
            r = c.put(f"{base}/v1/Accounts/{acc}/Calls/{provider_call}", json=body)
        if r.status_code >= 300 and not (what == "hang-up" and r.status_code == 404):
            raise ProviderError(f"jambonz {what} failed ({r.status_code}).")

    def transfer(self, provider_call, transfer_url):
        self._put(provider_call, {"call_hook": {"url": transfer_url, "method": "POST"}}, "transfer")
        return {"ok": True, "via": "jambonz"}

    def hangup(self, provider_call):
        self._put(provider_call, {"call_status": "completed"}, "hang-up")
        return {"ok": True}

    def dial(self, to, caller_id, answer_url, hangup_url, machine_url="", ring_s=30):
        base, key, acc = self._api()
        body: dict[str, Any] = {"from": caller_id, "to": {"type": "phone", "number": to}, "timeout": int(ring_s),
                                "call_hook": {"url": answer_url, "method": "POST"},
                                "call_status_hook": {"url": hangup_url, "method": "POST"}}
        if self.creds.get("application_sid"):
            body["application_sid"] = str(self.creds["application_sid"])
        if machine_url:
            body["amd"] = {"actionHook": {"url": machine_url, "method": "POST"}}
        with _client(headers={"Authorization": f"Bearer {key}"}) as c:
            r = c.post(f"{base}/v1/Accounts/{acc}/Calls", json=body)
        if r.status_code >= 300:
            raise ProviderError(f"jambonz did not place the call ({r.status_code}).")
        return {"call": str((r.json() if r.content else {}).get("sid") or "")}


KINDS = {"plivo": Plivo, "exotel": Exotel, "twilio": Twilio, "telnyx": Telnyx, "vonage": Vonage, "signalwire": SignalWire,
         "bandwidth": Bandwidth, "sinch": Sinch, "jambonz": Jambonz, "fake": Fake}

# what each provider needs from her (typed in the app only, sealed; `multiline` keys are pasted PEM files)
KEYS: dict[str, list[tuple[str, str]]] = {
    "plivo": [("auth_id", "Auth ID"), ("auth_token", "Auth Token")],
    "exotel": [("sid", "Account SID"), ("api_key", "API key"), ("api_token", "API token"), ("subdomain", "Subdomain"),
               ("flow_id", "Voicebot flow id"), ("sample_rate", "Sample rate (8000 / 16000)")],
    "twilio": [("account_sid", "Account SID"), ("auth_token", "Auth Token")],
    "telnyx": [("api_key", "API key"), ("public_key", "Webhook public key"), ("application_id", "TeXML application id"),
               ("account_sid", "TeXML account SID")],
    "vonage": [("application_id", "Application ID"), ("private_key", "Private key (paste the whole file)"),
               ("signature_secret", "Signature secret")],
    "signalwire": [("space", "Space (example.signalwire.com)"), ("project_id", "Project ID"), ("api_token", "API token"),
                   ("signing_key", "Signing key")],
    "bandwidth": [("account_id", "Account ID"), ("username", "API user name"), ("password", "API password"),
                  ("application_id", "Voice application id"), ("callback_user", "Callback user name (you choose)"),
                  ("callback_password", "Callback password (you choose)")],
    "sinch": [("app_key", "Application key"), ("app_secret", "Application secret")],
    "jambonz": [("base_url", "API address (https://api.jambonz.cloud or your own)"), ("account_sid", "Account SID"),
                ("api_key", "API key"), ("webhook_secret", "Webhook secret"), ("application_sid", "Application SID (optional)")],
    "fake": [("secret", "Test secret")],
}
REQUIRED: dict[str, tuple[str, ...]] = {
    "plivo": ("auth_id", "auth_token"), "twilio": ("account_sid", "auth_token"),
    "telnyx": ("api_key", "public_key"), "vonage": ("application_id", "private_key", "signature_secret"),
    "signalwire": ("space", "project_id", "api_token"), "bandwidth": ("account_id", "username", "password", "callback_user",
                                                                      "callback_password"),
    "sinch": ("app_key", "app_secret"), "jambonz": ("account_sid", "api_key", "webhook_secret"),
}
MULTILINE = {"private_key"}


def names() -> str:
    return ", ".join(k for k in KINDS)


def get(name: str, creds: dict[str, Any] | None = None) -> Provider:
    cls = KINDS.get(name)
    if cls is None:
        raise ProviderError(f"Provider: {names()}.")
    return cls(creds)
