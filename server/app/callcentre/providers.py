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
            raise ProviderError("Plivo Auth ID / Auth Token app mein daalne hain.")
        return f"{self.API}/{aid}/Call/{call}/"

    def transfer(self, provider_call, transfer_url):
        with _client(auth=(str(self.creds.get("auth_id")), str(self.creds.get("auth_token")))) as c:
            r = c.post(self._url(provider_call), json={"legs": "aleg", "aleg_url": transfer_url, "aleg_method": "POST"})
        if r.status_code >= 300:
            raise ProviderError(f"Plivo transfer nahi hua ({r.status_code}).")
        return {"ok": True, "via": "plivo"}

    def hangup(self, provider_call):
        with _client(auth=(str(self.creds.get("auth_id")), str(self.creds.get("auth_token")))) as c:
            r = c.delete(self._url(provider_call))
        if r.status_code >= 300 and r.status_code != 404:
            raise ProviderError(f"Plivo hang-up nahi hua ({r.status_code}).")
        return {"ok": True}


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


KINDS = {"plivo": Plivo, "exotel": Exotel, "fake": Fake}


def get(name: str, creds: dict[str, Any] | None = None) -> Provider:
    cls = KINDS.get(name)
    if cls is None:
        raise ProviderError("Provider: plivo, exotel ya fake.")
    return cls(creds)
