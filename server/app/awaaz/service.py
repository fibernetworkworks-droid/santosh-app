"""Hoola Awaaz: the owner's own voice (with recorded consent) and designed voices, made and spoken by our GPU worker.

Safety rules, enforced here:
  * An "own" voice can only be made from a recording of a one-time script read aloud in the app. The script says the
    speaker gives permission for THEIR OWN voice and contains a random code; Gemini listens to the recording and the
    code and the permission sentence must be in it. A file someone else recorded (a celebrity, a relative, a TV clip)
    cannot pass, because it would not contain this code.
  * A voice belongs to one Hoola account and is used only for that account's own avatar (its calls with the owner).
  * The recording is stored encrypted (SECRET_KEY) and deleting the voice deletes it here and on the worker.
"""
from __future__ import annotations

import io
import json
import logging
import re
import secrets
import time
import wave
from array import array
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx

from ..config import get_settings
from ..db import now, session
from .models import VoiceConsent, VoiceProfile

log = logging.getLogger("santosh.awaaz")

DATA_DIR = Path("data") / "awaaz"
CONSENT_MINUTES = 20
DIGITS = {"1": "ek", "2": "do", "3": "teen", "4": "chaar", "5": "paanch", "6": "chhe", "7": "saat", "8": "aath", "9": "nau"}
PREVIEW_TEXT = {"m": "Namaste! Main aapka Hoola hoon. Aaj ka kya plan hai? Bataiye, main sab sambhal leta hoon.",
                "f": "Namaste! Main aapki Hoola hoon. Aaj ka kya plan hai? Bataiye, main sab sambhal leti hoon."}


class AwaazError(Exception):
    pass


def enabled() -> bool:
    st = get_settings()
    return bool(st.awaaz_worker_url and st.awaaz_worker_key)


# ----------------------------------------------------------------------------- worker
def _worker(method: str, path: str, timeout: float = 60, **kw) -> httpx.Response:
    st = get_settings()
    if not enabled():
        raise AwaazError("Hoola Awaaz abhi server par chalu nahi hai (AWAAZ_WORKER_URL).")
    try:
        r = httpx.request(method, st.awaaz_worker_url.rstrip("/") + path, headers={"x-worker-key": st.awaaz_worker_key},
                          timeout=timeout, **kw)
    except httpx.HTTPError as e:
        raise AwaazError(f"Awaaz server se baat nahi ho paayi: {type(e).__name__}")
    if r.status_code >= 400:
        try:
            msg = r.json().get("detail") or r.text
        except ValueError:
            msg = r.text
        raise AwaazError(f"Awaaz server: {str(msg)[:200]}")
    return r


_health: dict[str, Any] = {"at": 0.0, "ok": False, "info": {}}


def health(max_age: float = 30) -> dict:
    """Worker status, cached for a short while (calls ask this before choosing the voice)."""
    if not enabled():
        return {"ok": False, "reason": "off"}
    if time.time() - _health["at"] < max_age:
        return _health["info"]
    try:
        info = _worker("GET", "/healthz", timeout=5).json()
        info["ok"] = bool(info.get("ready"))
    except AwaazError as e:
        info = {"ok": False, "reason": str(e)}
    _health.update(at=time.time(), info=info)
    return info


def stream_url(p: VoiceProfile) -> tuple[str, dict]:
    st = get_settings()
    base = st.awaaz_worker_url.rstrip("/")
    base = "wss://" + base[8:] if base.startswith("https://") else "ws://" + base.removeprefix("http://")
    return f"{base}/v1/stream?voice_id={p.worker_voice_id}&lang={p.lang}", {"x-worker-key": st.awaaz_worker_key}


def tts(p: VoiceProfile, text: str) -> bytes:
    """A short line in this voice, 24 kHz mono PCM16."""
    return _worker("POST", "/v1/tts", json={"voice_id": p.worker_voice_id, "text": text, "lang": p.lang}).content


# ----------------------------------------------------------------------------- audio checks (no numpy on core)
def wav_facts(data: bytes) -> dict:
    """Length and loudness of a 16-bit WAV recording."""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            if w.getsampwidth() != 2:
                raise AwaazError("Recording 16-bit WAV honi chahiye.")
            rate, ch, frames = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    except (wave.Error, EOFError):
        raise AwaazError("Recording padhi nahi ja saki (WAV nahi hai).")
    a = array("h")
    a.frombytes(frames[: len(frames) // 2 * 2])
    if ch > 1:
        a = a[::ch]
    n = len(a)
    if not n:
        raise AwaazError("Recording khaali hai.")
    step = max(1, n // 200000)
    xs = a[::step]
    rms = (sum(x * x for x in xs) / len(xs)) ** 0.5 / 32768
    clipped = sum(1 for x in xs if abs(x) >= 32000) / len(xs)
    # speech is loud in some parts and quiet in others; a flat level means noise or silence
    win = max(1, rate // 10 // step)
    levels = sorted((sum(x * x for x in xs[i:i + win]) / win) ** 0.5 for i in range(0, len(xs) - win + 1, win))
    lo, hi = (levels[len(levels) // 10], levels[len(levels) * 9 // 10]) if levels else (0, 0)
    return {"seconds": round(n / rate, 1), "rate": rate, "rms": round(rms, 4), "clipped": round(clipped, 4),
            "dynamics": round((hi + 1) / (lo + 1), 1)}


def check_recording(data: bytes) -> dict:
    f = wav_facts(data)
    if f["seconds"] < 10:
        raise AwaazError("Recording bahut chhoti hai. Poora paragraph aaram se padhiye (kam se kam 10 second).")
    if f["seconds"] > 60:
        raise AwaazError("Recording 1 minute se lambi hai. Sirf diya hua paragraph padhiye.")
    if f["rms"] < 0.01:
        raise AwaazError("Awaaz bahut dheemi aayi. Phone ko munh ke thoda paas rakhiye aur dobara padhiye.")
    if f["clipped"] > 0.02:
        raise AwaazError("Awaaz phat rahi hai (bahut zor se). Thoda door se, normal awaaz mein padhiye.")
    if f["dynamics"] < 3:
        raise AwaazError("Recording mein shor zyada hai. Kisi shaant jagah se dobara padhiye.")
    return f


# ----------------------------------------------------------------------------- consent
def consent_script(tenant: str, gender: str = "m") -> dict:
    from ..avatar.service import gendered
    code = "".join(secrets.choice("123456789") for _ in range(4))
    words = ", ".join(DIGITS[d] for d in code)
    script = gendered(
        "Yeh meri apni awaaz hai. Main apni marzi se Hoola ko ijaazat deta hoon ki mere avatar ke liye meri awaaz "
        f"banaye. Mera code hai: {words}.\n\n"
        "Aaj subah main jaldi utha, chai pi aur office ke liye nikla. Raste mein thoda traffic tha, par meeting "
        "time pe shuru ho gayi. Dopahar ko humne naye project ka plan banaya: budget, deadline aur team, sab kuch. "
        "Shaam ko ghar aakar maine mummy se baat ki, aur kal ka kaam ek list mein likh liya.", gender)
    cid = secrets.token_urlsafe(9)
    with session() as s:
        s.add(VoiceConsent(id=cid, tenant_id=tenant, code=code, script=script, gender=gender))
        s.commit()
    return {"consent_id": cid, "script": script, "code": code, "minutes": CONSENT_MINUTES}


def _listen(data: bytes, script: str) -> dict:
    """Gemini listens to the recording: what was said, which code digits, and whether it is one live speaker."""
    from google import genai
    from google.genai import types
    st = get_settings()
    if not st.gemini_api_key:
        raise AwaazError("Server par GEMINI_API_KEY set nahi hai (recording jaanchne ke liye zaroori).")
    prompt = (
        "You check a voice-consent recording for a voice cloning feature. The speaker was asked to read this script:\n"
        f"---\n{script}\n---\n"
        "Listen to the audio and answer ONLY with JSON: {\"transcript\": what was actually said (Hindi in Roman "
        "letters), \"code_digits\": the code digits the speaker said, in order, as digits (e.g. \"4729\"), or \"\", "
        "\"gave_permission\": true only if the speaker clearly says it is their own voice and they give permission, "
        "\"single_speaker\": true if one person speaks, \"live_voice\": false if it sounds like a playback of a TV, "
        "video, phone speaker or a recording of a recording}.")
    client = genai.Client(api_key=st.gemini_api_key)
    r = client.models.generate_content(
        model=st.youtube_gemini_model or "gemini-2.5-flash",
        contents=[types.Part.from_bytes(data=data, mime_type="audio/wav"), prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0))
    try:
        out = json.loads(r.text or "{}")
    except ValueError:
        raise AwaazError("Recording jaanchi nahi ja saki. Dobara try kijiye.")
    return out if isinstance(out, dict) else {}


def verify_consent(tenant: str, consent_id: str, data: bytes) -> tuple[VoiceConsent, dict]:
    with session() as s:
        c = s.get(VoiceConsent, consent_id)
        if c is None or c.tenant_id != tenant:
            raise AwaazError("Yeh script purani ho gayi. Naya script lijiye.")
        if c.used:
            raise AwaazError("Yeh script ek baar use ho chuki hai. Naya script lijiye.")
        created = c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=now().tzinfo)
        if now() - created > timedelta(minutes=CONSENT_MINUTES):
            raise AwaazError("Script ka samay nikal gaya. Naya script lijiye.")
        s.expunge(c)
    heard = _listen(data, c.script)
    digits = re.sub(r"\D", "", str(heard.get("code_digits", "")))
    if digits != c.code:
        raise AwaazError("Recording mein script ka code saaf sunai nahi diya. Poora script, code ke saath, dobara padhiye.")
    if not heard.get("gave_permission"):
        raise AwaazError("Recording mein ijaazat wali line nahi suni. Script ki pehli line zaroor padhiye.")
    if heard.get("single_speaker") is False:
        raise AwaazError("Recording mein ek se zyada log bol rahe hain. Akele, shaant jagah se padhiye.")
    if heard.get("live_voice") is False:
        raise AwaazError("Yeh live awaaz nahi lag rahi (speaker ya video se chalayi hui). Khud bolkar record kijiye.")
    with session() as s:
        s.get(VoiceConsent, consent_id).used = True
        s.commit()
    return c, heard


# ----------------------------------------------------------------------------- profiles
def _tag(tenant: str) -> str:
    import hashlib
    return hashlib.sha256(tenant.encode()).hexdigest()[:10]


def _store_sample(tenant: str, pid: str, data: bytes) -> str:
    from ..accounts import AuthError, _fernet
    try:
        blob = _fernet().encrypt(data)
    except AuthError:
        raise AwaazError("Server par SECRET_KEY set nahi hai; awaaz ki recording bina encryption ke save nahi karte.")
    d = DATA_DIR / _tag(tenant)
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{pid}.bin"
    f.write_bytes(blob)
    return str(f)


def _view(p: VoiceProfile) -> dict:
    return {"id": p.id, "voice": f"awaaz:{p.id}", "kind": p.kind, "name": p.name, "gender": p.gender,
            "status": p.status, "seconds": p.seconds, "description": p.description, "error": p.error,
            "created_at": p.created_at.isoformat() if p.created_at else None}


def list_voices(tenant: str) -> dict:
    with session() as s:
        ps = s.query(VoiceProfile).filter(VoiceProfile.tenant_id == tenant, VoiceProfile.status != "deleted") \
            .order_by(VoiceProfile.created_at).all()
        out = [_view(p) for p in ps]
    h = health() if enabled() else {"ok": False}
    return {"enabled": enabled(), "worker_ok": bool(h.get("ok")), "can_design": bool(h.get("can_design")),
            "voices": out}


def ready_voices(tenant: str) -> list[dict]:
    """Voices this account can pick for its avatar (database only, no network)."""
    with session() as s:
        return [_view(p) for p in s.query(VoiceProfile).filter_by(tenant_id=tenant, status="ready")
                .order_by(VoiceProfile.created_at)]


def ready_profile(tenant: str, voice: str) -> VoiceProfile | None:
    """The profile behind avatar voice 'awaaz:<id>', if it belongs to this tenant and is ready."""
    if not voice or not voice.startswith("awaaz:"):
        return None
    with session() as s:
        p = s.get(VoiceProfile, voice.split(":", 1)[1])
        if p is None or p.tenant_id != tenant or p.status != "ready":
            return None
        s.expunge(p)
        return p


def _register(tenant: str, kind: str, name: str, gender: str, data: bytes, ref_text: str, **extra) -> dict:
    pid = secrets.token_urlsafe(9).replace("-", "a").replace("_", "b")
    wid = f"{_tag(tenant)}_{pid}"
    sample = _store_sample(tenant, pid, data)
    try:
        r = _worker("POST", "/v1/voices", timeout=180, data={"voice_id": wid, "lang": "hi", "ref_text": ref_text},
                    files={"file": ("ref.wav", data, "audio/wav")}).json()
    except AwaazError:
        Path(sample).unlink(missing_ok=True)
        raise
    with session() as s:
        p = VoiceProfile(id=pid, tenant_id=tenant, kind=kind, name=name[:60], gender=gender, worker_voice_id=wid,
                         seconds=float(r.get("seconds") or 0), sample_file=sample, status="ready", **extra)
        s.add(p)
        s.commit()
        return _view(p)


def make_own(tenant: str, consent_id: str, data: bytes, name: str = "Meri awaaz") -> dict:
    """The owner read the consent script aloud: check it, then make their voice. Replaces an earlier own voice."""
    facts = check_recording(data)
    c, heard = verify_consent(tenant, consent_id, data)
    with session() as s:
        old = [p.id for p in s.query(VoiceProfile).filter_by(tenant_id=tenant, kind="own")
               .filter(VoiceProfile.status != "deleted")]
    view = _register(tenant, "own", name, c.gender, data, str(heard.get("transcript", ""))[:2000],
                     consent={"consent_id": c.id, "code": c.code, "transcript": str(heard.get("transcript", ""))[:2000],
                              "at": now().isoformat(), "recording": facts})
    for pid in old:
        delete(tenant, pid, _keep_avatar=view["voice"])
    return view


def design_preview(tenant: str, description: str, gender: str = "m") -> bytes:
    """A brand-new voice from a description: returns a WAV sample to listen to before saving it."""
    from ..avatar.service import gendered
    description = description.strip()
    if len(description) < 3:
        raise AwaazError("Awaaz kaisi chahiye, thoda bataiye (jaise 'Pune ki jawan ladki, garam aur saaf awaaz').")
    who = "woman" if gender == "f" else "man"
    desc = f"An Indian {who}. {description}"
    text = gendered(PREVIEW_TEXT["f" if gender == "f" else "m"], gender)
    return _worker("POST", "/v1/design", timeout=180, json={"description": desc, "text": text, "lang": "hi"}).content


def save_design(tenant: str, name: str, description: str, gender: str, data: bytes) -> dict:
    st = get_settings()
    with session() as s:
        n = s.query(VoiceProfile).filter_by(tenant_id=tenant, kind="design").filter(VoiceProfile.status != "deleted").count()
    if n >= st.awaaz_max_designs:
        raise AwaazError(f"Zyada se zyada {st.awaaz_max_designs} banayi hui awaazein rakh sakte hain. Pehle koi purani hataiye.")
    wav_facts(data)
    return _register(tenant, "design", name or "Nayi awaaz", gender, data, "", description=description[:400])


def delete(tenant: str, pid: str, _keep_avatar: str | None = None) -> bool:
    with session() as s:
        p = s.get(VoiceProfile, pid)
        if p is None or p.tenant_id != tenant or p.status == "deleted":
            return False
        wid, sample = p.worker_voice_id, p.sample_file
        p.status = "deleted"
        p.sample_file = ""
        s.commit()
    if sample:
        Path(sample).unlink(missing_ok=True)
    try:
        _worker("DELETE", f"/v1/voices/{wid}", timeout=20)
    except AwaazError as e:
        log.warning("worker delete of %s failed: %s", wid, e)
    from .. import voice as v
    v.forget_acks(f"awaaz:{pid}")
    from ..avatar.models import Avatar
    with session() as s:
        a = s.get(Avatar, tenant)
        if a is not None and a.voice == f"awaaz:{pid}":
            a.voice = _keep_avatar or ""
            s.commit()
    return True
