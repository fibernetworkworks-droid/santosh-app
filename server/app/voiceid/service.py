"""Awaaz Pehchaan: enrol the voices of the owner and the household, and tell them apart in calls.

Consent: every person enrols by reading a one-time script with a random code IN THEIR OWN VOICE ("Main Asha, apni
marzi se Hoola ko ijaazat deti hoon..."). Gemini listens and the code and the permission line must be there, so
nobody can be enrolled from a clip of them. Only a fingerprint is kept, encrypted; the recording is not stored.
Deleting a person removes the fingerprint at once.

A voice is a convenience and a safety net, not a password: recordings and voice clones can fool any voice check,
so payments still need the owner's tap on an unlocked phone (that rule does not change).
"""
from __future__ import annotations

import io
import json
import logging
import re
import secrets
import wave
from array import array
from datetime import timedelta
from typing import Any

from ..config import get_settings
from ..db import now, session
from . import engine
from .models import VoiceEnrol, VoiceLock, VoiceMember
from .permissions import LEVELS

log = logging.getLogger("santosh.voiceid")

ENROL_MINUTES = 20
MIN_SPEECH_S = 8.0
DIGITS = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
RELATIONS = {
    "self": ("Myself", None), "maa": ("Mother", "f"), "papa": ("Father", "m"), "behen": ("Sister", "f"),
    "bhai": ("Brother", "m"), "patni": ("Wife", "f"), "pati": ("Husband", "m"), "beta": ("Son", "m"),
    "beti": ("Daughter", "f"), "dadi": ("Grandmother", "f"), "dada": ("Grandfather", "m"), "dost": ("Friend", None),
    "staff": ("Staff", None), "aur": ("Someone else", None),
}
MODES = ("off", "on", "strict")


class VoiceIdError(Exception):
    pass


# ----------------------------------------------------------------------------- audio
def pcm16k(data: bytes) -> bytes:
    """A 16-bit WAV (any rate, mono or stereo) -> 16 kHz mono PCM16."""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            if w.getsampwidth() != 2:
                raise VoiceIdError("The recording must be a 16-bit WAV.")
            rate, ch, frames = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    except (wave.Error, EOFError):
        raise VoiceIdError("The recording could not be read.")
    a = array("h")
    a.frombytes(frames[: len(frames) // 2 * 2])
    if ch > 1:
        a = a[::ch]
    if rate != engine.RATE and len(a):
        step = rate / engine.RATE
        a = array("h", (a[int(i * step)] for i in range(int(len(a) / step))))
    return a.tobytes()


# ----------------------------------------------------------------------------- lock mode
def get_mode(tenant: str) -> str:
    with session() as s:
        r = s.get(VoiceLock, tenant)
        return r.mode if r is not None and r.mode in MODES else "on"


def set_mode(tenant: str, mode: str) -> str:
    if mode not in MODES:
        raise VoiceIdError("mode: off, on or strict")
    with session() as s:
        r = s.get(VoiceLock, tenant) or VoiceLock(tenant_id=tenant)
        r.mode = mode
        s.merge(r)
        s.commit()
    return mode


# ----------------------------------------------------------------------------- people
def _view(m: VoiceMember) -> dict:
    return {"id": m.id, "name": m.name, "relation": m.relation, "relation_label": RELATIONS.get(m.relation, (m.relation,))[0],
            "gender": m.gender, "level": m.level, "owner": m.relation == "self",
            "created_at": m.created_at.isoformat() if m.created_at else None}


def members(tenant: str) -> list[dict]:
    with session() as s:
        return [_view(m) for m in s.query(VoiceMember).filter_by(tenant_id=tenant).order_by(VoiceMember.created_at)]


def overview(tenant: str) -> dict:
    from .permissions import LEVEL_LABEL
    ms = members(tenant)
    return {"available": engine.available(), "mode": get_mode(tenant), "members": ms,
            "owner_enrolled": any(m["owner"] for m in ms),
            "relations": [{"id": k, "label": v[0], "gender": v[1]} for k, v in RELATIONS.items()],
            "levels": [{"id": k, "label": v} for k, v in LEVEL_LABEL.items()]}


def update(tenant: str, mid: str, level: str | None = None, name: str | None = None) -> dict:
    with session() as s:
        m = s.get(VoiceMember, mid)
        if m is None or m.tenant_id != tenant:
            raise VoiceIdError("This person was not found.")
        if level is not None:
            if level not in LEVELS or (m.relation == "self") != (level == "owner"):
                raise VoiceIdError("This level is not possible for this person.")
            m.level = level
        if name is not None and name.strip():
            m.name = name.strip()[:40]
        s.commit()
        return _view(m)


def delete(tenant: str, mid: str) -> bool:
    with session() as s:
        m = s.get(VoiceMember, mid)
        if m is None or m.tenant_id != tenant:
            return False
        s.delete(m)
        s.commit()
    return True


# ----------------------------------------------------------------------------- enrolment
def start_enrol(tenant: str, name: str, relation: str, gender: str | None = None, level: str | None = None) -> dict:
    from ..avatar.service import gendered
    if not engine.available():
        raise VoiceIdError("Voice recognition is not switched on on this server yet.")
    name = re.sub(r"\s+", " ", name or "").strip()[:40]
    if not name:
        raise VoiceIdError("Please give the name.")
    if relation not in RELATIONS:
        raise VoiceIdError("Please choose the relation.")
    g = gender if gender in ("m", "f") else (RELATIONS[relation][1] or "m")
    lv = "owner" if relation == "self" else (level if level in ("trusted", "family") else "family")
    code = "".join(secrets.choice("123456789") for _ in range(4))
    words = ", ".join(DIGITS[d] for d in code)
    script = gendered(
        f"I am {name}. Of my own free will, I give Hoola permission to recognize my voice. "
        f"My code is: {words}.\n\n"
        "The weather is very nice today. In the morning I had tea and read the newspaper. In the afternoon I did some work, then "
        "bought vegetables and milk from the market. In the evening we all sat together, talked and watched TV.", g)
    eid = secrets.token_urlsafe(9)
    with session() as s:
        s.add(VoiceEnrol(id=eid, tenant_id=tenant, name=name, relation=relation, gender=g, level=lv, code=code, script=script))
        s.commit()
    return {"enrol_id": eid, "script": script, "code": code, "minutes": ENROL_MINUTES}


def _listen(data: bytes, script: str) -> dict:
    """Gemini listens to the enrolment: what was said, the code digits, and whether one live person said it."""
    from google import genai
    from google.genai import types
    st = get_settings()
    if not st.gemini_api_key:
        raise VoiceIdError("GEMINI_API_KEY is not set on the server (needed to check the recording).")
    prompt = (
        "You check a consent recording for a voice-recognition feature. The speaker was asked to read:\n"
        f"---\n{script}\n---\n"
        "Answer ONLY with JSON: {\"transcript\": what was actually said (in Roman letters), \"code_digits\": the "
        "code digits the speaker said, in order, as digits (e.g. \"4729\") or \"\", \"gave_permission\": true only if "
        "the speaker clearly says they give permission for their own voice to be recognised, \"single_speaker\": true "
        "if one person speaks, \"live_voice\": false if it sounds like playback from a TV, video or another phone}.")
    r = genai.Client(api_key=st.gemini_api_key).models.generate_content(
        model=st.youtube_gemini_model or "gemini-2.5-flash",
        contents=[types.Part.from_bytes(data=data, mime_type="audio/wav"), prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0))
    try:
        out = json.loads(r.text or "{}")
    except ValueError:
        raise VoiceIdError("The recording could not be checked. Please try again.")
    return out if isinstance(out, dict) else {}


def _wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(engine.RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def finish_enrol(tenant: str, enrol_id: str, data: bytes) -> dict:
    from ..accounts import AuthError, encrypt
    with session() as s:
        e = s.get(VoiceEnrol, enrol_id)
        if e is None or e.tenant_id != tenant:
            raise VoiceIdError("This script has expired. Get a new script.")
        if e.used:
            raise VoiceIdError("This script has already been used once. Get a new script.")
        created = e.created_at if e.created_at.tzinfo else e.created_at.replace(tzinfo=now().tzinfo)
        if now() - created > timedelta(minutes=ENROL_MINUTES):
            raise VoiceIdError("The script's time has run out. Get a new script.")
        s.expunge(e)
    pcm = pcm16k(data)
    speech_s = len(engine.speech_only(pcm)) / 2 / engine.RATE
    if speech_s < MIN_SPEECH_S:
        raise VoiceIdError(f"Too little speech was heard ({speech_s:.0f} sec). Read the whole script slowly and clearly.")
    heard = _listen(_wav(pcm), e.script)
    if re.sub(r"\D", "", str(heard.get("code_digits", ""))) != e.code:
        raise VoiceIdError("The code was not heard clearly in the recording. Read the whole script again, with the code.")
    if not heard.get("gave_permission"):
        raise VoiceIdError("The permission line was not heard. Be sure to read the first line of the script.")
    if heard.get("single_speaker") is False:
        raise VoiceIdError("More than one person is speaking in the recording. Only the person whose voice is being added should read.")
    if heard.get("live_voice") is False:
        raise VoiceIdError("This does not sound like a live voice. The person must speak into the phone themselves.")
    fp = engine.enrol_print(pcm)
    try:
        sealed = encrypt(json.dumps(fp))
    except AuthError:
        raise VoiceIdError("SECRET_KEY is not set on the server; voice prints are not saved without encryption.")
    # the same voice must not be two people (and the owner must not be enrolled again as someone else)
    for other in _prints(tenant):
        if other["relation"] != e.relation or other["name"] != e.name:
            if engine.score(fp, other["print"]) > 0.75:
                raise VoiceIdError(f"This voice sounds the same as {other['name']}, who is already added.")
    with session() as s:
        s.get(VoiceEnrol, enrol_id).used = True
        old = s.query(VoiceMember).filter_by(tenant_id=tenant)
        old = old.filter_by(relation="self") if e.relation == "self" else old.filter_by(name=e.name, relation=e.relation)
        for m in old:
            s.delete(m)
        m = VoiceMember(id=secrets.token_urlsafe(9), tenant_id=tenant, name=e.name, relation=e.relation, gender=e.gender,
                        level=e.level, prints=sealed,
                        consent={"code": e.code, "transcript": str(heard.get("transcript", ""))[:1500],
                                 "at": now().isoformat(), "speech_s": round(speech_s, 1)})
        s.add(m)
        s.commit()
        return _view(m)


# ----------------------------------------------------------------------------- recognising
def _prints(tenant: str) -> list[dict]:
    from ..accounts import decrypt
    out = []
    with session() as s:
        for m in s.query(VoiceMember).filter_by(tenant_id=tenant):
            try:
                out.append({**_view(m), "print": json.loads(decrypt(m.prints) or "{}")})
            except Exception:
                log.warning("voice print of %s could not be read", m.id)
    return out


def identify(people: list[dict], pcm: bytes) -> dict[str, Any]:
    """Who is speaking in this 16 kHz PCM16 speech? {member, score, margin, sure}."""
    if not people:
        return {"member": None, "score": 0.0, "margin": 0.0, "sure": False}
    st = get_settings()
    fp = engine.embed(pcm)
    ranked = sorted(((engine.score(fp, p["print"]), p) for p in people), key=lambda t: -t[0])
    best, who = ranked[0]
    second = ranked[1][0] if len(ranked) > 1 else 0.0
    sure = best >= st.voiceid_match and best - second >= st.voiceid_margin
    return {"member": {k: who[k] for k in ("id", "name", "relation", "relation_label", "gender", "level", "owner")} if sure else None,
            "score": round(best, 3), "margin": round(best - second, 3), "sure": sure,
            "closest": who["name"]}


def call_people(tenant: str) -> list[dict] | None:
    """Fingerprints for a call, or None when Awaaz Pehchaan is off / not set up for this account."""
    if get_mode(tenant) == "off" or not engine.available():
        return None
    people = _prints(tenant)
    return people or None
