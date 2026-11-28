"""v0.999.170 HOOLA INTERACTIVE REBUILD - live agents (R4) and B-roll shots (R3).

A LIVE AGENT = a brain (her facts, in her words) + Hoola's voice (a Vocal voice, any language) + a face engine she picks
(Simli, Anam, HeyGen LiveAvatar, Tavus, the GPU lab, or voice only). The brain answers ONLY from her facts; a number in
an answer that is not in her facts (or the visitor's question) is never said - the answer becomes "I don't know".

    agent_save / agent_remove / agents     her agents (up to 10), kept in her studio.json
    ask(tenant, aid, text)                 one answer: words + the spoken WAV (base64) - the Try it panel
    session(tenant, aid)                   a short-lived pass for the chosen face engine (the vendor key stays here)
    publish(tenant, aid, on, sites)        a public agent pass for her website (shown once); only the sites she lists
    public_info / public_ask / public_session   what her website's widget calls (a minute cap a day, per-visitor rate)

A B-ROLL SHOT = a 4-8 s video without a person (the shop, the product), made by a broll engine after her tap on its price.

Rules: FACTS-ONLY answers, numbers checked by code; CAP minutes a day per agent (default 30) and 20 questions per visitor
in 10 minutes; KEYS never leave the server, a browser only gets the vendor's short-lived token; SITES - a published
agent answers only on the hosts she listed (when she listed any); a person is never asked to be shown in B-roll.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import secrets
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from . import engines as EN
from . import studio as S
from . import voice as VO

log = logging.getLogger("santosh.interactive.live")
MAX_AGENTS = 10
MAX_Q = 400
VISITOR_RATE = (20, 600)            # questions per visitor per 10 minutes
_RLOCK = threading.Lock()
_VISITS: dict[str, list[float]] = {}
_PEOPLE = re.compile(r"\b(person|people|man|woman|girl|boy|child|kid|face|selfie|actor|actress|celebrity|model|"
                     r"politician|minister|influencer|baby|crowd)\b", re.I)


class LiveError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def _clip(v: Any, n: int) -> str:
    return " ".join(str(v or "").split())[:n]


def _agents(d: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(d.get("agents"), list):
        d["agents"] = []
        for b in d.get("brains") or []:                  # the older "brains" become agents once, voice-only
            d["agents"].append({"id": "la_" + uuid.uuid4().hex[:8], "name": b.get("name") or "Agent",
                                "knows": b.get("knows") or "", "opening": b.get("opening") or "",
                                "lang": b.get("lang") or "hi", "voice": "", "face": "voice_only", "avatar_id": "",
                                "minutes_day": 30, "sites": [], "public": None, "used": {}, "created": S._now_iso()})
    return d["agents"]


def _public_agent(a: dict[str, Any]) -> dict[str, Any]:
    pub = a.get("public") or {}
    today = time.strftime("%Y-%m-%d")
    week = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 7 * 86400))
    log = [x for x in (a.get("log") or []) if isinstance(x, dict)]
    recent = [x for x in log if str(x.get("at") or "") >= week]
    return {**{k: v for k, v in a.items() if k not in ("public", "used", "log")},
            "published": bool(pub.get("sha")), "pass_last4": pub.get("last4", ""),
            "used_today_s": round(float((a.get("used") or {}).get(today, 0.0)), 1),
            # v0.999.202 what it was asked this week, and the questions its facts could not answer (open ones, newest first)
            "asked_week": len(recent), "missed_week": sum(1 for x in recent if not x.get("known")),
            "misses": [{k: x.get(k) for k in ("id", "q", "at", "src")} for x in log if not x.get("known") and not x.get("resolved")][:8]}


def agents(tenant: str) -> dict[str, Any]:
    with S._LOCK:
        d = S._load(tenant)
        rows = _agents(d)
        S._store(tenant, d)
    return {"agents": [_public_agent(a) for a in rows], "broll": list(d.get("broll") or [])[:30],
            "faces": [e for e in EN.view(tenant)["engines"] if e["job"] == "live"]}


def _find(d: dict[str, Any], aid: str) -> dict[str, Any]:
    for a in _agents(d):
        if a["id"] == aid:
            return a
    raise LiveError("This agent was not found.", 404)


def agent_save(tenant: str, body: dict[str, Any]) -> dict[str, Any]:
    name, knows = _clip(body.get("name"), 40), str(body.get("knows") or "").strip()[:6000]
    if not name:
        raise LiveError("Give the agent a name.")
    if len(knows) < 20:
        raise LiveError("Write what it should know: your timings, products, prices, address.")
    face = str(body.get("face") or "voice_only")
    if face not in EN.BY_ID or EN.BY_ID[face]["job"] != "live":
        raise LiveError("Pick a face engine from the list.")
    with S._LOCK:
        d = S._load(tenant)
        rows = _agents(d)
        aid = str(body.get("id") or "")
        row = next((a for a in rows if a["id"] == aid), None)
        if row is None:
            if len(rows) >= MAX_AGENTS:
                raise LiveError(f"You have {MAX_AGENTS} agents - remove one first.")
            row = {"id": "la_" + uuid.uuid4().hex[:8], "created": S._now_iso(), "public": None, "used": {}, "sites": []}
            rows.insert(0, row)
        av = str(body.get("avatar_id") or "")
        if av and not any(x["id"] == av for x in d.get("avatars") or []):
            raise LiveError("That face was not found. Add it on the Avatars page first.")
        try:
            mins = max(1, min(int(body.get("minutes_day") or row.get("minutes_day") or 30), 600))
        except (TypeError, ValueError):
            mins = 30
        row.update(name=name, knows=knows, opening=_clip(body.get("opening"), 160), lang=S.lang_of(body.get("lang") or "hi"),
                   voice=_clip(body.get("voice"), 60), face=face, avatar_id=av, minutes_day=mins,
                   face_ref=_clip(body.get("face_ref"), 80), updated=S._now_iso())
        S._store(tenant, d)
        return _public_agent(row)


def agent_remove(tenant: str, aid: str) -> bool:
    with S._LOCK:
        d = S._load(tenant)
        a = _find(d, aid)
        d["agents"] = [x for x in _agents(d) if x["id"] != aid]
        S._store(tenant, d)
    if (a.get("public") or {}).get("sha"):
        _pub_index_drop(a["public"]["sha"])
    return True


# ------------------------------------------------------------------ the brain: facts only ---
def _digits(s: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", str(s or "").replace(",", "")))


_DONT_KNOW = {"hi": "Mujhe iski jaankari nahi hai. Aap dukaan se seedhe pooch lijiye.",
              "en": "I don't have that information. Please ask the shop directly."}


def _think(system: str, prompt: str) -> dict[str, Any]:
    from ..videoedit import brain
    return brain.think(system, prompt, max_tokens=600)


def answer(a: dict[str, Any], question: str, think: Any = None) -> str:
    return answer_known(a, question, think)[0]


def answer_known(a: dict[str, Any], question: str, think: Any = None) -> tuple[str, bool]:
    """v0.999.202 the answer, and whether her facts held it (a refused number or the model's own "not in the facts" = False)."""
    q = _clip(question, MAX_Q)
    if len(q) < 2:
        raise LiveError("Ask something.")
    lang = a.get("lang") or "hi"
    system = (f"You are {a['name']}, a helpful assistant for a business, speaking out loud to a customer. Answer ONLY "
              "from the facts below - never from memory. If the facts do not hold the answer, say you do not know and "
              "offer that the business will help. Never invent a price, time, date, number, name or promise. One to "
              f"three short spoken sentences in {VO.lang_name(lang)} (for Hindi use Roman script unless the customer "
              "wrote Devanagari). Return ONLY JSON {\"answer\": \"...\", \"known\": true} - known is false when the "
              "facts did not hold the answer.\nFacts:\n" + a["knows"])
    try:
        out = (think or _think)(system, f"Customer: {q}")
    except Exception as e:   # noqa: BLE001
        raise LiveError(f"The brain did not answer just now ({type(e).__name__}). Try again.", 502) from None
    text = _clip((out or {}).get("answer") if isinstance(out, dict) else "", 600)
    if not text or not _digits(text) <= (_digits(a["knows"]) | _digits(q)):
        return _DONT_KNOW.get(lang, _DONT_KNOW["en"]), False     # a number she never wrote is never said
    return text, (out.get("known") is not False)


def _spend(tenant: str, aid: str, seconds: float) -> None:
    with S._LOCK:
        d = S._load(tenant)
        try:
            a = _find(d, aid)
        except LiveError:
            return
        today = time.strftime("%Y-%m-%d")
        used = {k: v for k, v in (a.get("used") or {}).items() if k >= time.strftime("%Y-%m-%d", time.localtime(time.time() - 7 * 86400))}
        used[today] = float(used.get(today, 0.0)) + float(seconds)
        a["used"] = used
        S._store(tenant, d)


def _room(a: dict[str, Any]) -> None:
    today = time.strftime("%Y-%m-%d")
    if float((a.get("used") or {}).get(today, 0.0)) >= 60 * int(a.get("minutes_day") or 30):
        raise LiveError("This agent has used its minutes for today. It answers again tomorrow.", 429)


LOG_KEEP = 300


def _note(tenant: str, aid: str, q: str, words: str, known: bool, src: str) -> None:
    """v0.999.202 every question kept on its agent (newest first, 300 at most) so she sees what it could not answer."""
    with S._LOCK:
        d = S._load(tenant)
        try:
            a = _find(d, aid)
        except LiveError:
            return
        row = {"id": "lq_" + uuid.uuid4().hex[:8], "q": _clip(q, MAX_Q), "a": _clip(words, 600), "known": bool(known),
               "src": "web" if src == "web" else "try", "at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())}
        a["log"] = [row] + [x for x in (a.get("log") or []) if isinstance(x, dict)][:LOG_KEEP - 1]
        S._store(tenant, d)


def questions(tenant: str, aid: str) -> dict[str, Any]:
    a = _find(S._load(tenant), aid)
    return {"questions": [x for x in (a.get("log") or []) if isinstance(x, dict)][:150]}


def learn(tenant: str, aid: str, qid: str, text: str) -> dict[str, Any]:
    """Her answer to a question it could not answer, added to its facts (the facts are what it answers from)."""
    ans = " ".join(str(text or "").split())[:600]
    if len(ans) < 2:
        raise LiveError("Write the answer.")
    with S._LOCK:
        d = S._load(tenant)
        a = _find(d, aid)
        row = next((x for x in (a.get("log") or []) if isinstance(x, dict) and x.get("id") == qid), None)
        if row is None:
            raise LiveError("That question was not found.", 404)
        add = f"\nQ: {row['q']}\nA: {ans}"
        if len(a.get("knows") or "") + len(add) > 6000:
            raise LiveError("Its facts are full (6,000 characters). Shorten them first.")
        a["knows"] = (a.get("knows") or "").rstrip() + add
        row["resolved"] = True
        a["updated"] = S._now_iso()
        S._store(tenant, d)
        return _public_agent(a)


def dismiss(tenant: str, aid: str, qid: str) -> dict[str, Any]:
    with S._LOCK:
        d = S._load(tenant)
        a = _find(d, aid)
        row = next((x for x in (a.get("log") or []) if isinstance(x, dict) and x.get("id") == qid), None)
        if row is None:
            raise LiveError("That question was not found.", 404)
        row["resolved"] = True
        S._store(tenant, d)
        return _public_agent(a)


def ask(tenant: str, aid: str, text: str, think: Any = None, speak: Any = None, src: str = "try") -> dict[str, Any]:
    d = S._load(tenant)
    a = _find(d, aid)
    _room(a)
    words, known = answer_known(a, text, think)
    _note(tenant, aid, text, words, known, src)
    audio, secs = "", VO.seconds_of(words)
    try:
        wav = (speak or VO.speaker(tenant, a.get("voice") or "", a.get("lang") or "hi"))(words, a.get("lang") or "hi")
        from ..vocal import service as V
        try:
            secs = V.wav_seconds(wav) or secs
        except Exception:   # noqa: BLE001 - the length is only for the minute meter
            pass
        audio = base64.b64encode(wav).decode()
    except VO.VoiceError as e:
        _spend(tenant, aid, secs)
        return {"answer": words, "known": known, "audio": "", "voice_error": str(e), "seconds": secs}
    _spend(tenant, aid, secs)
    return {"answer": words, "known": known, "audio": audio, "mime": "audio/wav", "seconds": round(secs, 1)}


def session(tenant: str, aid: str) -> dict[str, Any]:
    a = _find(S._load(tenant), aid)
    _room(a)
    try:
        out = EN.live_session(tenant, a.get("face") or "voice_only", a)
    except EN.EngineError as e:
        raise LiveError(str(e), e.status) from None
    return {**out, "opening": a.get("opening") or "", "name": a["name"], "lang": a.get("lang")}


# ------------------------------------------------------------------ her website ---
def _pub_path() -> Path:
    p = Path("data") / "interactive" / "_pubagents.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _pub_index() -> dict[str, Any]:
    try:
        d = json.loads(_pub_path().read_text("utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:   # noqa: BLE001
        return {}


def _pub_save(d: dict[str, Any]) -> None:
    tmp = _pub_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(d), "utf-8")
    tmp.replace(_pub_path())


def _pub_index_drop(sha: str) -> None:
    with _RLOCK:
        idx = _pub_index()
        idx.pop(sha, None)
        _pub_save(idx)


def _host(s: str) -> str:
    s = str(s or "").strip().lower()
    s = re.sub(r"^https?://", "", s).split("/")[0].split(":")[0]
    return s if re.fullmatch(r"[a-z0-9.-]{3,120}", s) else ""


def publish(tenant: str, aid: str, on: bool = True, sites: list[Any] | None = None) -> dict[str, Any]:
    with S._LOCK:
        d = S._load(tenant)
        a = _find(d, aid)
        old = (a.get("public") or {}).get("sha")
        if not on:
            a["public"] = None
            S._store(tenant, d)
            if old:
                _pub_index_drop(old)
            return {"published": False}
        hosts = [h for h in (_host(x) for x in (sites or [])) if h][:5]
        if not hosts:
            raise LiveError("Write the website address it will be on (for example myshop.in). It answers only there.")
        token = "ia_pub_" + secrets.token_urlsafe(18)
        sha = hashlib.sha256(token.encode()).hexdigest()
        a["public"] = {"sha": sha, "last4": token[-4:], "made": S._now_iso()}
        a["sites"] = hosts
        S._store(tenant, d)
    with _RLOCK:
        idx = _pub_index()
        if old:
            idx.pop(old, None)
        idx[sha] = {"tenant": tenant, "aid": aid}
        _pub_save(idx)
    from ..config import get_settings
    base = (getattr(get_settings(), "public_base_url", "") or "").rstrip("/")
    return {"published": True, "token": token, "sites": hosts,
            "embed": f'<script src="{base}/static/interactive/agent.js" data-agent="{token}" defer></script>',
            "note": "Copy this line into your website now. The pass is shown only once."}


def _pub(token: str, origin: str) -> tuple[str, dict[str, Any]]:
    hit = _pub_index().get(hashlib.sha256(str(token or "").encode()).hexdigest())
    if not hit:
        raise LiveError("This agent is not published.", 404)
    a = _find(S._load(hit["tenant"]), hit["aid"])
    if not (a.get("public") or {}).get("sha"):
        raise LiveError("This agent is not published.", 404)
    sites = a.get("sites") or []
    if sites and _host(origin) not in sites and not any(_host(origin).endswith("." + s) for s in sites):
        raise LiveError("This agent answers only on its own website.", 403)
    return hit["tenant"], a


def _visitor(token: str, ip: str) -> None:
    n, window = VISITOR_RATE
    k = hashlib.sha256(f"{token}|{ip}".encode()).hexdigest()[:24]
    now = time.time()
    with _RLOCK:
        seen = [t for t in _VISITS.get(k, []) if now - t < window]
        if len(seen) >= n:
            _VISITS[k] = seen
            raise LiveError("Too many questions just now. Wait a few minutes.", 429)
        seen.append(now)
        _VISITS[k] = seen


def public_info(token: str, origin: str) -> dict[str, Any]:
    _tenant, a = _pub(token, origin)
    e = EN.BY_ID.get(a.get("face") or "voice_only") or EN.BY_ID["voice_only"]
    return {"name": a["name"], "opening": a.get("opening") or "", "lang": a.get("lang"), "face": e["id"],
            "face_label": e["label"], "ai": "You are talking to an AI assistant."}


def public_ask(token: str, text: str, origin: str, ip: str) -> dict[str, Any]:
    tenant, a = _pub(token, origin)
    _visitor(token, ip)
    return {**ask(tenant, a["id"], text, src="web"), "ai": "You are talking to an AI assistant."}


def public_session(token: str, origin: str, ip: str) -> dict[str, Any]:
    tenant, a = _pub(token, origin)
    _visitor(token, ip)
    return session(tenant, a["id"])


# ------------------------------------------------------------------ B-roll shots ---
def broll_path(tenant: str, bid: str) -> Path | None:
    f = S._home(tenant) / "broll" / f"{re.sub(r'[^A-Za-z0-9_-]', '', bid)}.mp4"
    return f if f.is_file() else None


def _broll_set(tenant: str, bid: str, **kw: Any) -> None:
    with S._LOCK:
        d = S._load(tenant)
        for r in d.get("broll") or []:
            if r["id"] == bid:
                r.update(kw)
        S._store(tenant, d)


def broll_make(tenant: str, prompt: str, seconds: int = 6, aspect: str = "16:9", engine: str = "gemini_broll",
               quote_key: str = "", runner: Any = None) -> dict[str, Any]:
    prompt = _clip(prompt, 800)
    if len(prompt) < 8:
        raise LiveError("Describe the shot: what is seen, where, the light.")
    if _PEOPLE.search(prompt):
        raise LiveError("A B-roll shot is made without people. Describe the place or the product only; your face "
                        "comes from the talking-face engines.")
    seconds = max(4, min(int(seconds or 6), 8))
    aspect = aspect if aspect in ("16:9", "9:16") else "16:9"
    try:
        q = EN.quote(engine, float(seconds))
        EN.check_quote(q, quote_key)
        if not EN.connected(engine) and runner is None:
            raise EN.EngineError(f"{EN.BY_ID[engine]['label']} is not connected on this server: {EN.status_of(engine)}.", 409)
    except KeyError:
        raise LiveError("Pick a B-roll engine.") from None
    except EN.EngineError as e:
        raise LiveError(str(e), e.status) from None
    bid = "br_" + uuid.uuid4().hex[:10]
    row = {"id": bid, "prompt": prompt, "seconds": seconds, "aspect": aspect, "engine": engine, "status": "making",
           "error": "", "made": "", "credits": q["credits"], "created": S._now_iso()}
    with S._LOCK:
        d = S._load(tenant)
        d["broll"] = ([row] + list(d.get("broll") or []))[:30]
        S._store(tenant, d)

    def run() -> None:
        try:
            data = (runner or EN.broll)(tenant, engine, prompt, seconds, aspect)
            folder = S._home(tenant) / "broll"
            folder.mkdir(exist_ok=True)
            (folder / f"{bid}.mp4").write_bytes(data)
            EN.ai_mark(str(folder / f"{bid}.mp4"))
            EN.charge(tenant, q)
            _broll_set(tenant, bid, status="ready", made=S._now_iso())
        except Exception as e:   # noqa: BLE001
            _broll_set(tenant, bid, status="failed", error=str(e)[:300])

    threading.Thread(target=run, name=f"broll-{bid}", daemon=True).start()
    return row
