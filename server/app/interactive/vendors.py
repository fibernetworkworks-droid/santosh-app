"""v0.999.170 HOOLA INTERACTIVE REBUILD - the outside engines, each from its vendor's own spec read on 23 Nov 2026
(docs/research/interactive/03_vendor_shapes.md). One network seam: `_http` (tests replace exactly it).

Video makers (her photo + the spoken track -> a talking MP4 URL or bytes):
  runway_face   POST /v1/avatars (custom avatar from one image, kept per photo) -> POST /v1/avatar_videos -> GET /v1/tasks
  heygen_face   POST /v3/assets (photo, voice) -> POST /v3/videos type image, engine heygen-avatar-6 -> GET /v3/videos/{id}
  hedra_face    POST /v3/files (photo, voice) -> POST /v3/models/hedra-character-3 -> GET /v3/jobs/{id}/status, /jobs/{id}
B-roll:
  gemini_video  POST /v1beta/interactions, model gemini-omni-1.2-flash, response_format video (no people, no audio in)
Live faces (a short-lived pass for the browser; the vendor key never leaves the server):
  simli_session      POST /compose/token {faceId}           -> session_token (browser sends PCM16 16 kHz)
  anam_session       POST /v1/auth/session-token passthrough -> sessionToken (browser sends PCM16 24 kHz)
  liveavatar_session POST /v1/sessions/token LITE + /start  -> LiveKit url + client token (+ ws_url for 24 kHz PCM16)
  tavus_session      POST /v2/conversations {pal_id}        -> conversation_url (Tavus's own room; its PAL holds the brain)

NOT VERIFIED against a live account (no key on the build machine). Every refusal is the vendor's own words, scrubbed.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Callable

from .engines import EngineError

RUNWAY = "https://api.dev.runwayml.com"
RUNWAY_VERSION = "2024-11-06"
HEYGEN = "https://api.heygen.com"
HEDRA = "https://api.hedra.com/v3"
GEMINI = "https://generativelanguage.googleapis.com/v1beta"
OMNI_MODEL = "gemini-omni-1.2-flash"
SIMLI = "https://api.simli.ai"
ANAM = "https://api.anam.ai"
LIVEAVATAR = "https://api.liveavatar.com"
TAVUS = "https://tavusapi.com"


def _http(method: str, url: str, *, headers: dict[str, str], json_body: Any = None, files: Any = None,
          data: Any = None, timeout: float = 120) -> tuple[int, Any]:
    """The ONE network seam. Returns (status, parsed JSON or {})."""
    import httpx
    try:
        r = httpx.request(method, url, headers=headers, json=json_body, files=files, data=data, timeout=timeout)
    except httpx.HTTPError as e:
        raise EngineError(f"The engine could not be reached ({type(e).__name__}).", 502) from None
    try:
        body = r.json()
    except ValueError:
        body = {}
    return r.status_code, body


def _scrub(text: Any, key: str) -> str:
    t = str(text or "")
    if key:
        t = t.replace(key, "[key]")
    return re.sub(r"(Bearer|Key)\s+\S+", r"\1 [key]", t)[:300]


def _err(label: str, status: int, body: Any, key: str) -> EngineError:
    msg = ""
    if isinstance(body, dict):
        e = body.get("error")
        if isinstance(e, dict):
            msg = e.get("message") or e.get("code") or ""
        else:
            msg = e or body.get("message") or body.get("detail") or body.get("failure") or ""
    msg = _scrub(msg, key)
    if status in (401, 403):
        return EngineError(f"{label} refused the key{': ' + msg if msg else ''}. The owner checks it in the server settings.", 502)
    if status == 402:
        return EngineError(f"{label} has no credit left on this account{': ' + msg if msg else ''}. Nothing was made.", 402)
    if status == 429:
        return EngineError(f"{label} is rate-limiting this account. Try again in a minute.", 429)
    return EngineError(f"{label} answered {status}{': ' + msg if msg else ''}.", 502)


def _ok(label: str, status: int, body: Any, key: str) -> dict[str, Any]:
    if status // 100 != 2:
        raise _err(label, status, body, key)
    return body if isinstance(body, dict) else {}


def _data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def _img_mime(name: str) -> str:
    n = name.lower()
    return "image/png" if n.endswith(".png") else "image/webp" if n.endswith(".webp") else "image/jpeg"


# ------------------------------------------------------------------ Runway ---
def _runway_h(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "X-Runway-Version": RUNWAY_VERSION}


def _cache() -> Path:
    p = Path("data") / "interactive" / "_vendor_faces.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _cache_get(k: str) -> str:
    try:
        return str(json.loads(_cache().read_text("utf-8")).get(k) or "")
    except Exception:   # noqa: BLE001
        return ""


def _cache_put(k: str, v: str) -> None:
    try:
        d = json.loads(_cache().read_text("utf-8"))
    except Exception:   # noqa: BLE001
        d = {}
    d[k] = v
    _cache().write_text(json.dumps(d), "utf-8")


def runway_face(key: str, photo: bytes, name: str, wav: bytes, seconds: float, cancel: Any,
                on_wait: Callable[[str], None] | None, wait: Callable[..., dict[str, Any]]) -> str:
    if len(photo) > 5 * 1024 * 1024 or len(wav) > 5 * 1024 * 1024:
        raise EngineError("Runway takes the photo and the voice up to 5 MB each here. Use a smaller photo or a shorter video.")
    h = _runway_h(key)
    ck = "runway:" + hashlib.sha256(photo).hexdigest()[:24]
    avatar = _cache_get(ck)
    if not avatar:
        st, body = _http("POST", f"{RUNWAY}/v1/avatars", headers=h, json_body={
            "name": "Hoola face", "referenceImage": _data_uri(photo, _img_mime(name)),
            "personality": "A friendly presenter who speaks clearly to the camera.",
            "voice": {"type": "runway-live-preset", "presetId": "clara"}})
        avatar = str(_ok("Runway", st, body, key).get("id") or "")
        if not avatar:
            raise EngineError("Runway made no avatar from the photo.", 502)

        def poll_avatar() -> dict[str, Any]:
            s2, b2 = _http("GET", f"{RUNWAY}/v1/avatars/{avatar}", headers=h, timeout=30)
            b2 = _ok("Runway", s2, b2, key)
            stt = str(b2.get("status") or "").upper()
            return {"state": "success" if stt == "READY" else "fail" if stt == "FAILED" else "making the face",
                    "error": b2.get("failureReason") or ""}
        wait(poll_avatar, cancel, on_wait, "Runway", limit_s=900, every=5.0)
        _cache_put(ck, avatar)
    st, body = _http("POST", f"{RUNWAY}/v1/avatar_videos", headers=h, json_body={
        "model": "gwm1_avatars", "avatar": {"type": "custom", "avatarId": avatar},
        "speech": {"type": "audio", "audio": _data_uri(wav, "audio/wav")}})
    task = str(_ok("Runway", st, body, key).get("id") or "")
    if not task:
        raise EngineError("Runway started nothing (no task id came back).", 502)
    out: dict[str, Any] = {}

    def poll() -> dict[str, Any]:
        s2, b2 = _http("GET", f"{RUNWAY}/v1/tasks/{task}", headers=h, timeout=30)
        b2 = _ok("Runway", s2, b2, key)
        stt = str(b2.get("status") or "").upper()
        if stt == "SUCCEEDED":
            out["url"] = (b2.get("output") or [""])[0]
            return {"state": "success"}
        if stt in ("FAILED", "CANCELLED"):
            return {"state": "fail", "error": b2.get("failure") or stt.lower()}
        return {"state": stt.lower() or "pending"}
    wait(poll, cancel, on_wait, "Runway", every=6.0)
    if not out.get("url"):
        raise EngineError("Runway finished but returned no file.", 502)
    return out["url"]


# ------------------------------------------------------------------ HeyGen ---
def _heygen_asset(key: str, data: bytes, fname: str, mime: str) -> str:
    st, body = _http("POST", f"{HEYGEN}/v3/assets", headers={"x-api-key": key}, files={"file": (fname, data, mime)},
                     timeout=300)
    aid = str((_ok("HeyGen", st, body, key).get("data") or {}).get("asset_id") or "")
    if not aid:
        raise EngineError("HeyGen took the file but gave no asset id.", 502)
    return aid


def heygen_face(key: str, photo: bytes, name: str, wav: bytes, seconds: float, cancel: Any,
                on_wait: Callable[[str], None] | None, wait: Callable[..., dict[str, Any]]) -> str:
    if len(photo) > 32 * 1024 * 1024 or len(wav) > 50 * 1024 * 1024:
        raise EngineError("HeyGen takes a photo up to 32 MB and a voice file up to 50 MB.")
    img = _heygen_asset(key, photo, "face." + (name.rsplit(".", 1)[-1] if "." in name else "jpg"), _img_mime(name))
    aud = _heygen_asset(key, wav, "voice.wav", "audio/wav")
    st, body = _http("POST", f"{HEYGEN}/v3/videos", headers={"x-api-key": key, "Content-Type": "application/json",
                                                             "Idempotency-Key": f"hoola-{hashlib.sha256(photo + wav).hexdigest()[:40]}"},
                     json_body={"type": "image", "image": {"type": "asset_id", "asset_id": img}, "audio_asset_id": aud,
                                "engine": {"type": "heygen-avatar-6"}, "resolution": "720p", "title": "Hoola Interactive"})
    vid = str((_ok("HeyGen", st, body, key).get("data") or {}).get("video_id") or "")
    if not vid:
        raise EngineError("HeyGen started nothing (no video id came back).", 502)
    out: dict[str, Any] = {}

    def poll() -> dict[str, Any]:
        s2, b2 = _http("GET", f"{HEYGEN}/v3/videos/{vid}", headers={"x-api-key": key}, timeout=30)
        d = _ok("HeyGen", s2, b2, key).get("data") or {}
        stt = str(d.get("status") or "")
        if stt == "completed":
            out["url"] = d.get("video_url") or ""
            return {"state": "success"}
        if stt == "failed":
            return {"state": "fail", "error": d.get("failure_message") or d.get("failure_code") or ""}
        return {"state": stt or "pending"}
    wait(poll, cancel, on_wait, "HeyGen", every=8.0)
    if not out.get("url"):
        raise EngineError("HeyGen finished but returned no file.", 502)
    return out["url"]


# ------------------------------------------------------------------ Hedra ---
def _hedra_h(key: str) -> dict[str, str]:
    return {"Authorization": f"Key {key}"}


def _hedra_file(key: str, data: bytes, fname: str, mime: str) -> str:
    st, body = _http("POST", f"{HEDRA}/files", headers=_hedra_h(key), files={"file": (fname, data, mime)}, timeout=300)
    url = str(_ok("Hedra", st, body, key).get("url") or "")
    if not url:
        raise EngineError("Hedra took the file but gave no link for it.", 502)
    return url


def hedra_face(key: str, photo: bytes, name: str, wav: bytes, seconds: float, cancel: Any,
               on_wait: Callable[[str], None] | None, wait: Callable[..., dict[str, Any]]) -> str:
    if len(photo) > int(10.4 * 1024 * 1024):
        raise EngineError("Hedra takes a photo up to 10 MB.")
    if seconds > 600:
        raise EngineError("Hedra takes up to 10 minutes of speech.")
    img = _hedra_file(key, photo, "face." + (name.rsplit(".", 1)[-1] if "." in name else "jpg"), _img_mime(name))
    aud = _hedra_file(key, wav, "voice.wav", "audio/wav")
    st, body = _http("POST", f"{HEDRA}/models/hedra-character-3", headers={**_hedra_h(key), "Content-Type": "application/json"},
                     json_body={"input": {"prompt": "A friendly person speaks clearly to the camera.", "aspect_ratio": "16:9",
                                          "resolution": "720p", "start_image": {"source": "url", "url": img},
                                          "audio": {"source": "url", "url": aud}},
                                "idempotency_key": f"hoola-{hashlib.sha256(photo + wav).hexdigest()[:40]}"})
    job = str(_ok("Hedra", st, body, key).get("job_id") or "")
    if not job:
        raise EngineError("Hedra started nothing (no job id came back).", 502)

    def poll() -> dict[str, Any]:
        s2, b2 = _http("GET", f"{HEDRA}/jobs/{job}/status", headers=_hedra_h(key), timeout=30)
        stt = str(_ok("Hedra", s2, b2, key).get("status") or "")
        return {"state": "success" if stt == "COMPLETED" else "fail" if stt == "FAILED" else stt.lower() or "queued"}
    wait(poll, cancel, on_wait, "Hedra", every=6.0)
    st, body = _http("GET", f"{HEDRA}/jobs/{job}", headers=_hedra_h(key), timeout=30)
    outs = _ok("Hedra", st, body, key).get("outputs") or []
    url = next((o.get("url") for o in outs if isinstance(o, dict) and o.get("url")), "")
    if not url:
        raise EngineError("Hedra finished but returned no file.", 502)
    return str(url)


# ------------------------------------------------------------------ Gemini Omni (B-roll) ---
def gemini_video(key: str, prompt: str, seconds: int, aspect: str, cancel: Any,
                 on_wait: Callable[[str], None] | None, wait: Callable[..., dict[str, Any]]) -> bytes | str:
    if on_wait:
        on_wait("Gemini is making the shot")
    st, body = _http("POST", f"{GEMINI}/interactions", headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                     json_body={"model": OMNI_MODEL, "input": prompt,
                                "response_format": {"type": "video", "aspect_ratio": aspect if aspect in ("16:9", "9:16") else "16:9",
                                                    "resolution": "720p", "duration": f"{max(3, min(int(seconds), 15))}s"},
                                "generation_config": {"video_config": {"task": "text_to_video"}},
                                "background": False, "store": False, "stream": False}, timeout=600)
    body = _ok("Gemini", st, body, key)
    for step in body.get("steps") or []:
        for c in (step.get("content") or []) if isinstance(step, dict) else []:
            if isinstance(c, dict) and c.get("type") == "video":
                if c.get("data"):
                    return base64.b64decode(c["data"])
                if c.get("uri"):
                    return _gemini_file(key, str(c["uri"]), cancel, on_wait, wait)
    uri = ((body.get("output_video") or {}) if isinstance(body.get("output_video"), dict) else {}).get("uri")
    if uri:
        return _gemini_file(key, str(uri), cancel, on_wait, wait)
    raise EngineError("Gemini answered without a video.", 502)


def _gemini_file(key: str, uri: str, cancel: Any, on_wait: Any, wait: Callable[..., dict[str, Any]]) -> bytes:
    name = uri.split("/v1beta/")[-1] if "/v1beta/" in uri else uri
    if not re.fullmatch(r"files/[A-Za-z0-9_-]+", name):
        raise EngineError("Gemini gave a file address Hoola does not open.", 502)

    def poll() -> dict[str, Any]:
        s2, b2 = _http("GET", f"{GEMINI}/{name}", headers={"x-goog-api-key": key}, timeout=30)
        stt = str(_ok("Gemini", s2, b2, key).get("state") or "")
        return {"state": "success" if stt == "ACTIVE" else "fail" if stt == "FAILED" else "processing"}
    wait(poll, cancel, on_wait, "Gemini", limit_s=600, every=4.0)
    import httpx
    r = httpx.get(f"{GEMINI}/{name}:download", params={"alt": "media"}, headers={"x-goog-api-key": key},
                  timeout=300, follow_redirects=True)
    if r.status_code != 200:
        raise EngineError(f"Gemini's file could not be fetched ({r.status_code}).", 502)
    return r.content


# ------------------------------------------------------------------ live faces ---
def _need_ref(agent: dict[str, Any], what: str) -> str:
    ref = str(agent.get("face_ref") or "").strip()
    if not ref:
        raise EngineError(f"Write this agent's {what} (made in the engine's own dashboard) on the agent first.")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{3,80}", ref):
        raise EngineError(f"That {what} does not look right.")
    return ref


def simli_session(key: str, agent: dict[str, Any]) -> dict[str, Any]:
    face = _need_ref(agent, "Simli face id")
    st, body = _http("POST", f"{SIMLI}/compose/token", headers={"x-simli-api-key": key, "Content-Type": "application/json"},
                     json_body={"faceId": face, "maxSessionLength": 600, "maxIdleTime": 120}, timeout=30)
    b = _ok("Simli", st, body, key)
    tok = str(b.get("session_token") or "")
    if not tok or tok == "FAIL TOKEN":
        raise EngineError(f"Simli gave no pass: {_scrub(b.get('detail'), key) or 'no reason given'}.", 502)
    return {"kind": "simli", "token": tok, "sample_rate": 16000,
            "sdk": "https://cdn.jsdelivr.net/npm/simli-client@3.2.0/+esm"}


def anam_session(key: str, agent: dict[str, Any]) -> dict[str, Any]:
    avatar = _need_ref(agent, "Anam avatar id")
    st, body = _http("POST", f"{ANAM}/v1/auth/session-token",
                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                     json_body={"personaConfig": {"avatarId": avatar, "enableAudioPassthrough": True,
                                                  "maxSessionLengthSeconds": 600},
                                "expiresInSeconds": 600, "clientLabel": "hoola-interactive"}, timeout=30)
    tok = str(_ok("Anam", st, body, key).get("sessionToken") or "")
    if not tok:
        raise EngineError("Anam gave no pass.", 502)
    return {"kind": "anam", "token": tok, "sample_rate": 24000,
            "sdk": "https://cdn.jsdelivr.net/npm/@anam-ai/js-sdk@4.29.3/+esm"}


def liveavatar_session(key: str, agent: dict[str, Any]) -> dict[str, Any]:
    avatar = _need_ref(agent, "LiveAvatar avatar id")
    st, body = _http("POST", f"{LIVEAVATAR}/v1/sessions/token", headers={"X-API-KEY": key, "Content-Type": "application/json"},
                     json_body={"mode": "LITE", "avatar_id": avatar, "max_session_duration": 600}, timeout=30)
    tok = str((_ok("LiveAvatar", st, body, key).get("data") or {}).get("session_token") or "")
    if not tok:
        raise EngineError("LiveAvatar gave no pass.", 502)
    st, body = _http("POST", f"{LIVEAVATAR}/v1/sessions/start", headers={"Authorization": f"Bearer {tok}"}, timeout=60)
    d = _ok("LiveAvatar", st, body, "") .get("data") or {}
    if not d.get("livekit_url"):
        raise EngineError("LiveAvatar started no room.", 502)
    return {"kind": "liveavatar", "livekit_url": d["livekit_url"], "token": d.get("livekit_client_token") or "",
            "ws_url": d.get("ws_url") or "", "session_id": d.get("session_id") or "", "sample_rate": 24000,
            "sdk": "https://cdn.jsdelivr.net/npm/livekit-client@2.25.0/+esm"}


def tavus_session(key: str, agent: dict[str, Any]) -> dict[str, Any]:
    pal = _need_ref(agent, "Tavus PAL id")
    st, body = _http("POST", f"{TAVUS}/v2/conversations", headers={"x-api-key": key, "Content-Type": "application/json"},
                     json_body={"pal_id": pal, "conversation_name": str(agent.get("name") or "Hoola agent")[:60],
                                "conversational_context": str(agent.get("knows") or "")[:4000],
                                "custom_greeting": str(agent.get("opening") or "")[:300] or None,
                                "properties": {"max_call_duration": 600}}, timeout=30)
    b = _ok("Tavus", st, body, key)
    url = str(b.get("conversation_url") or "")
    if not url.startswith("https://"):
        raise EngineError("Tavus started no room.", 502)
    return {"kind": "tavus", "url": url, "id": b.get("conversation_id") or "",
            "note": "Tavus answers in its own room with the PAL set up in your Tavus account."}
