"""v0.231.0 VOICE PHASE 4: call-quality numbers that survive restarts, a grade per call, the real-phone checklist
and the ear test.

Before this, every call scorecard lived only in `voice.STATS` (a deque in memory): each deploy / pm2 restart wiped
them, so "is the call better after this version?" could not be answered. Now each finished call writes ONE compact
line to `data/voice_calls/<tenant>.jsonl` (last 300 kept). Numbers and labels only - never words, never audio.

`grade()` turns a scorecard into good / ok / bad + plain Hinglish problems. `quality()` rolls the saved calls up
(per version too, so a release can be compared with the one before). The ear test and the phone checklist are fixed
scenarios she plays on her own phone; her pass / fail is saved per app version.

v0.234.0 VOICE PHASE 5 (the plan's leftovers): the slowest 1% (p99) of reply starts, dead-air seconds, how often he
talked over her or said the same thing twice, a once-a-day alert when the slow tail or broken calls get bad, and the
ear test compared with the previous version scenario by scenario ("before and after").
"""
from __future__ import annotations

import json
import re
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

DIR = Path("data") / "voice_calls"
EAR_DIR = Path("data") / "voice_eartest"
KEEP = 300
_LOCK = threading.Lock()

# what a call scorecard keeps on disk: numbers / labels only (never words, transcripts or audio)
NUM_KEYS = ("turns", "interruptions", "tools", "silent_tools", "acks", "false_stops", "backchannels", "progress",
            "blocked_tools", "otp_filled", "lang_switches", "lang_drifts", "lang_unclear", "asked_again",
            "her_corrections", "fixes_heard", "repair_escalations", "holds", "held_turns", "dropped_replies",
            "hold_refused_tools", "hold_s", "stall_nudges", "stall_reconnects", "auto_rescues", "orphan_notes",
            "affect_notes", "affect_vetoed", "affect_confirmed", "affect_pauses_rider", "affect_transitions",
            "tone_soft_acks", "goaway", "goaway_graceful", "goaway_forced", "prebuilt", "gap_audio_kept_s",
            "missed_replayed_s", "news_deduped", "news_merged", "voice_approvals", "setup_refusals", "breaker",
            "question_endings", "assistantisms", "silence_ms", "cost_usd",
            # v0.234 Phase 5
            "talk_over", "repeats", "stall_noise_skips", "level_matched",
            # v0.265 real voice: delivery cues sent, replies that opened with a thinking sound
            "delivery_cues", "filler_starts", "oa_replies")

END_WORDS = {"hung_up": "aapne kaata", "dropped": "line toot gayi", "error": "connection error",
             "stall": "Gemini chup ho gaya", "server_restart": "server update", "hold_timeout": "hold bahut lamba"}

# good reply start for a phone call: under ~1.2 s feels like a person, past ~2.5 s feels broken
LAT_GOOD_MS, LAT_BAD_MS = 1200, 2500
# v0.234 the slow tail: one reply in a hundred starting after ~4 s is the "is he even there?" moment she remembers
P99_ALERT_MS = 4000
ALERT_LAST = 30            # the alert looks at the newest 30 saved calls
ALERT_EVERY_S = 86400      # ... and speaks at most once a day


def _slug(tenant: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", tenant or "main")[:80] or "main"


def _version() -> str:
    import sys
    m = sys.modules.get(__package__ + ".main") if __package__ else None
    return str(getattr(m, "APP_VERSION", "") or "")


def _pct(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


def _p99(xs: list[float]) -> float | None:
    """The slowest 1% by nearest rank (rounds UP: with few turns the single slowest one still shows)."""
    if not xs:
        return None
    import math
    xs = sorted(xs)
    return xs[max(0, math.ceil(.99 * len(xs)) - 1)]


def dead_air_s(lat: list) -> float:
    """Seconds she waited beyond a person-like reply start (LAT_GOOD_MS), summed over the turns."""
    return round(sum(max(0, x - LAT_GOOD_MS) for x in lat if isinstance(x, (int, float))) / 1000, 1)


def compact(stats: dict[str, Any]) -> dict[str, Any]:
    """The on-disk form of one call (numbers and labels only)."""
    lat = [int(x) for x in (stats.get("latency_ms") or []) if isinstance(x, (int, float))]
    words = [int(x) for x in (stats.get("words") or []) if isinstance(x, (int, float))]
    out: dict[str, Any] = {
        "call_id": str(stats.get("call_id") or ""), "tenant": str(stats.get("tenant") or ""),
        "started": stats.get("started"), "ended": stats.get("ended"),
        "seconds": round((stats.get("ended") or 0) - (stats.get("started") or 0), 1) if stats.get("ended") else None,
        "end": stats.get("end") or "", "lang": stats.get("lang") or "", "version": _version(),
        "engine": stats.get("engine") or "gemini",   # v0.264 which engine spoke this call
        "latency_ms": lat[-120:], "words": words[-120:],   # v0.234 120: a long call's slow tail stays
        "gate": {k: int(v) for k, v in (stats.get("gate") or {}).items() if isinstance(v, (int, float))},
    }
    for k in NUM_KEYS:
        v = stats.get(k)
        if isinstance(v, bool):
            v = int(v)
        if isinstance(v, (int, float)):
            out[k] = v
    return out


def record(stats: dict[str, Any]) -> None:
    """One finished call -> one line in its tenant's file (last KEEP kept). Never raises into the call."""
    c = compact(stats)
    if not c["call_id"]:
        return
    DIR.mkdir(parents=True, exist_ok=True)
    p = DIR / f"{_slug(c['tenant'])}.jsonl"
    line = json.dumps(c, ensure_ascii=False)
    with _LOCK:
        lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
        lines = [ln for ln in lines if ln.strip()]
        lines.append(line)
        tmp = p.with_suffix(".tmp")
        tmp.write_text("\n".join(lines[-KEEP:]) + "\n", encoding="utf-8")
        tmp.replace(p)
    try:
        maybe_alert(c["tenant"])
    except Exception:
        import logging
        logging.getLogger(__name__).exception("voice quality alert failed")


def load(tenant: str) -> list[dict[str, Any]]:
    p = DIR / f"{_slug(tenant)}.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if isinstance(d, dict) and d.get("call_id"):
            out.append(d)
    return out


def calls(tenant: str, live: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Saved calls + calls still only in memory (this process), one per call_id, oldest first."""
    seen: dict[str, dict] = {c["call_id"]: c for c in load(tenant)}
    for s in live or []:
        if s.get("tenant") == tenant and s.get("call_id") and s["call_id"] not in seen:
            seen[s["call_id"]] = compact(s)
    return sorted(seen.values(), key=lambda c: c.get("started") or 0)


def grade(c: dict[str, Any]) -> dict[str, Any]:
    """good / ok / bad for one call, with the problems in plain words (what she would have felt)."""
    bad: list[str] = []
    meh: list[str] = []
    lat = c.get("latency_ms") or []
    p90 = _pct(lat, .9)
    turns = c.get("turns") or 0
    end = c.get("end") or ""
    if end in ("error", "stall"):
        bad.append(f"call beech mein tooti ({END_WORDS[end]})")
    elif end == "dropped" and (c.get("seconds") or 0) > 5:
        meh.append("call bina 'kaato' ke khatam hui (line toot gayi)")
    if p90 is not None:
        if p90 > LAT_BAD_MS:
            bad.append(f"jawab der se shuru hua (p90 {int(p90)} ms)")
        elif p90 > LAT_GOOD_MS * 1.6:
            meh.append(f"jawab thoda der se (p90 {int(p90)} ms)")
    if c.get("stall_reconnects"):
        bad.append(f"Gemini chup ho gaya, {c['stall_reconnects']} baar dobara jodna pada")
    elif c.get("stall_nudges"):
        meh.append("ek baar chup hua, yaad dilana pada")
    if c.get("goaway_forced"):
        meh.append(f"{c['goaway_forced']} baar connection-badli mein baat kati")
    if c.get("dropped_replies"):
        meh.append("hold mein jawab chhoda gaya")
    if turns and (c.get("lang_drifts") or 0) / turns > .1:
        meh.append("bhasha beech mein badli")
    if turns and (c.get("asked_again") or 0) / turns > .25:
        meh.append("baar baar dobara poochha")
    if c.get("false_stops") and c["false_stops"] >= 3:
        meh.append("shor se baar baar ruka")
    if (c.get("talk_over") or 0) >= 2:
        meh.append(f"{c['talk_over']} baar aapke bolte hue bol pada")
    if (c.get("repeats") or 0) >= 2:
        meh.append(f"{c['repeats']} baar ek hi baat dobara boli")
    if lat and dead_air_s(lat) >= 20:
        meh.append(f"kul {int(dead_air_s(lat))} second khamoshi mein intezaar")
    if c.get("rating") is False:
        bad.append("aapne 👎 diya")
    level = "bad" if bad else ("ok" if meh else "good")
    return {"grade": level, "problems": bad + meh}


def _ratings(tenant: str) -> dict[str, bool]:
    try:
        from .callrating import CallRating
        from .db import session
        with session() as s:
            return {r.call_id: bool(r.good) for r in s.query(CallRating).filter(CallRating.tenant_id == tenant).all()}
    except Exception:
        return {}


def _sum(cs: list[dict], k: str) -> float:
    return sum((c.get(k) or 0) for c in cs)


def _roll(cs: list[dict]) -> dict[str, Any]:
    lat = [x for c in cs for x in (c.get("latency_ms") or [])]
    turns = int(_sum(cs, "turns"))
    tools = int(_sum(cs, "tools"))
    goaway = int(_sum(cs, "goaway"))
    grades = Counter(c["_g"]["grade"] for c in cs)
    n = len(cs)
    return {
        "calls": n, "turns": turns,
        "minutes": round(sum((c.get("seconds") or 0) for c in cs) / 60, 1),
        "reply_start_ms_p50": _pct(lat, .5), "reply_start_ms_p90": _pct(lat, .9),
        "reply_start_ms_p99": _p99(lat),
        "dead_air_s": dead_air_s(lat),
        "dead_air_s_per_call": round(dead_air_s(lat) / n, 1) if n else None,
        "grades": {"good": grades.get("good", 0), "ok": grades.get("ok", 0), "bad": grades.get("bad", 0)},
        "good_pct": round(100 * grades.get("good", 0) / n, 1) if n else None,
        "ends": dict(Counter(c.get("end") or "?" for c in cs)),
        "broken_calls": sum(1 for c in cs if c.get("end") in ("error", "stall")),
        # Phase 2: long calls - GoAway moves, how many were graceful, pre-built briefs, gap audio, his missed voice
        "goaway": goaway, "goaway_graceful": int(_sum(cs, "goaway_graceful")),
        "goaway_forced": int(_sum(cs, "goaway_forced")), "prebuilt": int(_sum(cs, "prebuilt")),
        "goaway_graceful_pct": round(100 * _sum(cs, "goaway_graceful") / goaway, 1) if goaway else None,
        "gap_audio_kept_s": round(_sum(cs, "gap_audio_kept_s"), 1),
        "missed_replayed_s": round(_sum(cs, "missed_replayed_s"), 1),
        # Phase 3: news told at a pause, merged, never twice; murmurs
        "news_merged": int(_sum(cs, "news_merged")), "news_deduped": int(_sum(cs, "news_deduped")),
        "backchannels": int(_sum(cs, "backchannels")), "acks": int(_sum(cs, "acks")),
        "orphan_notes": int(_sum(cs, "orphan_notes")),
        # reliability
        "stall_nudges": int(_sum(cs, "stall_nudges")), "stall_reconnects": int(_sum(cs, "stall_reconnects")),
        "auto_rescues": int(_sum(cs, "auto_rescues")), "setup_refusals": int(_sum(cs, "setup_refusals")),
        # talk
        "interruptions_per_call": round(_sum(cs, "interruptions") / n, 2) if n else None,
        "false_stops_per_call": round(_sum(cs, "false_stops") / n, 2) if n else None,
        "lang_drifts_per_100": round(100 * _sum(cs, "lang_drifts") / turns, 1) if turns else None,
        "asked_again_per_100": round(100 * _sum(cs, "asked_again") / turns, 1) if turns else None,
        "silent_tools_pct": round(100 * _sum(cs, "silent_tools") / tools, 1) if tools else None,
        "voice_approvals": int(_sum(cs, "voice_approvals")),
        # Phase 5: he talked over her / said the same thing twice; noise the stall watchdog ignored
        "talk_over_per_100": round(100 * _sum(cs, "talk_over") / turns, 1) if turns else None,
        "repeats_per_100": round(100 * _sum(cs, "repeats") / turns, 1) if turns else None,
        "stall_noise_skips": int(_sum(cs, "stall_noise_skips")),
        "cost_usd": round(_sum(cs, "cost_usd"), 3),
    }


def _say(r: dict[str, Any]) -> str:
    if not r["calls"]:
        return "Abhi koi call record nahi hui. Ek-do call kijiye, phir yahan numbers aayenge."
    parts = [f"{r['calls']} calls mein {r['grades']['good']} achhi, {r['grades']['ok']} theek, {r['grades']['bad']} kharab."]
    if r["reply_start_ms_p50"] is not None:
        parts.append(f"Jawab aam taur par {int(r['reply_start_ms_p50'])} ms mein shuru hota hai.")
    if r["broken_calls"]:
        parts.append(f"{r['broken_calls']} call beech mein tooti.")
    if r.get("reply_start_ms_p99") is not None and r["reply_start_ms_p99"] > P99_ALERT_MS:
        parts.append(f"Sabse dheema 1% jawab {round(r['reply_start_ms_p99'] / 1000, 1)} second mein - yeh sudharna hai.")
    if r["goaway"]:
        parts.append(f"Connection {r['goaway']} baar badla, {r['goaway_graceful']} baar baat kate bina.")
    return " ".join(parts)


def quality(tenant: str, days: int = 30, live: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """The call-quality page: overall roll-up, per app version (newest first), recent calls with a grade."""
    since = time.time() - max(1, days) * 86400
    rated = _ratings(tenant)
    cs = [c for c in calls(tenant, live) if (c.get("started") or 0) >= since]
    for c in cs:
        if c["call_id"] in rated:
            c["rating"] = rated[c["call_id"]]
        c["_g"] = grade(c)
    overall = _roll(cs)
    by_v: dict[str, list] = {}
    for c in cs:
        by_v.setdefault(c.get("version") or "?", []).append(c)
    versions = [{"version": v, **_roll(x)} for v, x in by_v.items()]
    versions.sort(key=lambda r: [int(p) if p.isdigit() else 0 for p in str(r["version"]).split(".")], reverse=True)
    recent = []
    for c in reversed(cs[-15:]):
        lat = c.get("latency_ms") or []
        recent.append({"call_id": c["call_id"], "started": c.get("started"), "seconds": c.get("seconds"),
                       "turns": c.get("turns") or 0, "end": c.get("end") or "", "end_say": END_WORDS.get(c.get("end") or "", ""),
                       "version": c.get("version") or "", "reply_start_ms_p50": _pct(lat, .5),
                       "rating": c.get("rating"), **c["_g"]})
    return {"days": days, "version": _version(), "overall": overall, "versions": versions[:6], "recent": recent,
            "targets": {"reply_start_ms_p50": LAT_GOOD_MS, "reply_start_ms_p90": LAT_BAD_MS,
                        "reply_start_ms_p99": P99_ALERT_MS, "good_pct": 80},
            "say": _say(overall), "eartest": eartest_summary(tenant), "alert": alert_state(tenant, live)}


# ---- v0.234 the alert: the slow tail or broken calls got bad -> one push a day, never more ----
def _alert_file(tenant: str) -> Path:
    return DIR / f"{_slug(tenant)}.alert.json"


def alert_state(tenant: str, live: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """What the newest ALERT_LAST calls say right now: {on, why[], p99, broken, calls, last_sent}."""
    cs = calls(tenant, live)[-ALERT_LAST:]
    lat = [x for c in cs for x in (c.get("latency_ms") or [])]
    p99 = _p99(lat) if len(lat) >= 20 else None
    broken = sum(1 for c in cs[-10:] if c.get("end") in ("error", "stall"))
    why = []
    if p99 is not None and p99 > P99_ALERT_MS:
        why.append(f"sabse dheema 1% jawab {round(p99 / 1000, 1)} second mein shuru hua (had {P99_ALERT_MS // 1000} s)")
    if broken >= 3:
        why.append(f"pichhli 10 mein se {broken} call beech mein tooti")
    try:
        last = float(json.loads(_alert_file(tenant).read_text(encoding="utf-8")).get("at") or 0)
    except Exception:
        last = 0.0
    return {"on": bool(why), "why": why, "p99": p99, "broken": broken, "calls": len(cs), "last_sent": last or None}


def maybe_alert(tenant: str) -> bool:
    """After a call is saved: if the alert is on and none went out in the last day, tell her once (push + feed)."""
    if len(load(tenant)) < 5:
        return False
    a = alert_state(tenant)
    if not a["on"] or (a["last_sent"] and time.time() - a["last_sent"] < ALERT_EVERY_S):
        return False
    text = "Call ki jaanch: " + "; ".join(a["why"]) + ". Profile > Call ki jaanch mein dekhiye."
    try:
        from .events import bus
        from .net.service import home_conv
        bus.publish(home_conv(tenant), "voice_alert", {"text": text, "why": a["why"]})
    except Exception:
        import logging
        logging.getLogger(__name__).exception("voice alert publish failed")
        return False
    DIR.mkdir(parents=True, exist_ok=True)
    _alert_file(tenant).write_text(json.dumps({"at": time.time(), "why": a["why"]}), encoding="utf-8")
    return True


# ---- the ear test + real-phone checklist (she plays each one on her own phone, then marks it) ----
EAR_TESTS: list[dict[str, str]] = [
    {"id": "hello_speed", "kind": "ear", "title": "Pehli awaaz kitni jaldi",
     "do": "Call shuru kijiye aur 'Hello, kaise ho?' boliye.",
     "good": "Ek second ke andar jawab, ek chhoti line, robot jaisa nahi."},
    {"id": "long_story", "kind": "ear", "title": "Lambi baat beech mein na kaate",
     "do": "Ek lambi baat boliye (20-30 second) beech mein ruk ruk ke.",
     "good": "Woh beech mein jawab nahi deta; bas kabhi 'haan...' / 'achha...' bolta hai; aapke khatam karne par jawab."},
    {"id": "interrupt", "kind": "ear", "title": "Beech mein rokna",
     "do": "Jab woh lamba bol raha ho tab 'ruko ruko' boliye.",
     "good": "Turant ruk jaata hai aur aapki sunta hai; aapke shabd khote nahi."},
    {"id": "list_pace", "kind": "ear", "title": "List aaram se",
     "do": "Kahiye 'aaj ke 3 kaam batao' (ya koi list).",
     "good": "Ek ek karke, saans le ke; jaldi-jaldi ek saans mein nahi."},
    {"id": "feeling_low", "kind": "ear", "title": "Udaas baat par awaaz",
     "do": "Kahiye 'aaj din bahut kharab gaya'.",
     "good": "Dheemi, narm awaaz; 'wah!' jaisi khushi nahi."},
    {"id": "feeling_glad", "kind": "ear", "title": "Khushi par awaaz",
     "do": "Kahiye 'mera order aa gaya, bahut khush hoon!'",
     "good": "Awaaz mein khushi; ek normal line, over-acting nahi."},
    {"id": "tool_wait", "kind": "ear", "title": "Kaam karte waqt chup na rahe",
     "do": "Kahiye 'aaj ka mausam batao' ya koi search.",
     "good": "Turant 'ek second' jaisa kuch, phir sahi jawab; lambi khamoshi nahi."},
    {"id": "job_news", "kind": "ear", "title": "Kaam ki khabar sahi waqt",
     "do": "Call mein ek lamba kaam dijiye (jaise ek document banana), phir baat karte rahiye.",
     "good": "Kaam hone par aapke rukne pe EK baar batata hai; aapki baat beech mein nahi kaat-ta, do baar nahi batata."},
    {"id": "hinglish", "kind": "ear", "title": "Bhasha pakki",
     "do": "Poori call Hinglish mein kijiye, ek-do English shabd daal ke.",
     "good": "Woh poori call Hinglish mein rehta hai; achanak English / doosri bhasha nahi."},
    {"id": "yes_approve", "kind": "ear", "title": "Bol kar haan",
     "do": "Ek kaam dijiye jisme card aaye (jaise PC par kuch kholna), phir 'haan karo' boliye.",
     "good": "Card bina tap ke aage badhta hai; paise wala card kabhi bol kar nahi."},
    {"id": "net_switch", "kind": "phone", "title": "Wi-Fi se mobile data",
     "do": "Call ke beech Wi-Fi band kar dijiye.",
     "good": "Kuch second 'jud raha hoon', phir wahi baat aage; call khatam nahi hoti."},
    {"id": "gsm_call", "kind": "phone", "title": "Beech mein phone call",
     "do": "Hoola call ke beech kisi se apne number par call karwaiye, uthaiye, phir kaatiye.",
     "good": "Phone call ke waqt Hoola chup (hold); kaatne par wapas wahi baat."},
    {"id": "whatsapp_call", "kind": "phone", "title": "WhatsApp call aaye",
     "do": "Hoola call ke beech WhatsApp call aane dijiye.",
     "good": "Hoola chup ho jaata hai, awaaz nahi lena; baad mein wapas."},
    {"id": "headset", "kind": "phone", "title": "Earphone / Bluetooth lagana",
     "do": "Call ke beech earphone ya Bluetooth headset lagaiye aur nikaliye.",
     "good": "Awaaz turant headset mein jaati hai, nikalne par speaker par; call chalti rehti hai."},
    {"id": "song", "kind": "phone", "title": "Gaana chalte waqt",
     "do": "Call mein 'Spotify pe koi gaana lagao' kahiye, phir baat kijiye.",
     "good": "Gaana chalta hai, call bhi; woh gaane ke bol ko aapki baat nahi samajhta."},
    {"id": "lock_screen", "kind": "phone", "title": "Screen lock",
     "do": "Call ke beech phone lock kar dijiye, 1 minute baat kijiye.",
     "good": "Call chalti rehti hai, dono taraf awaaz."},
    {"id": "long_call", "kind": "phone", "title": "15 minute ki call",
     "do": "15 minute se lambi call kijiye (connection beech mein badalta hai).",
     "good": "Koi kat-ti hui line nahi; pehle ki baat yaad rehti hai."},
    {"id": "server_restart", "kind": "phone", "title": "Call katne ke baad yaad",
     "do": "Call ke beech net band karke 1 minute baad nayi call kijiye.",
     "good": "Nayi call 'wahi kaam pe chalte hain' se shuru; naya hello nahi."},
]
RESULTS = ("pass", "fail", "skip")


def _ear_file(tenant: str) -> Path:
    return EAR_DIR / f"{_slug(tenant)}.json"


def _ear_load(tenant: str) -> dict[str, Any]:
    p = _ear_file(tenant)
    try:
        d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        d = {}
    return d if isinstance(d, dict) else {}


def eartest(tenant: str, version: str | None = None) -> dict[str, Any]:
    """The scenarios with HER marks for this app version (each version starts fresh; older ones kept)."""
    v = version or _version()
    saved = (_ear_load(tenant).get(v) or {})
    items = [{**t, **({"result": saved[t["id"]]["result"], "note": saved[t["id"]].get("note", ""),
                       "at": saved[t["id"]].get("at")} if t["id"] in saved else {"result": None, "note": ""})}
             for t in EAR_TESTS]
    return {"version": v, "items": items, **_count(saved), "compare": eartest_compare(tenant, v)}


def _vkey(v: str) -> list[int]:
    return [int(p) if p.isdigit() else 0 for p in str(v).split(".")]


def eartest_compare(tenant: str, version: str | None = None) -> dict[str, Any]:
    """v0.234 before / after: this version's marks against the newest OLDER version she marked, per scenario.
    better = fail -> pass, worse = pass -> fail, same = both marked alike; new / not_yet when one side is missing."""
    v = version or _version()
    d = _ear_load(tenant)
    older = sorted((x for x in d if isinstance(d.get(x), dict) and d[x] and _vkey(x) < _vkey(v)), key=_vkey)
    if not older:
        return {"against": None, "better": [], "worse": [], "same": 0, "rows": {}}
    prev, now_, before = older[-1], d.get(v) or {}, d[older[-1]]
    rows: dict[str, str] = {}
    for t in EAR_TESTS:
        a, b = (before.get(t["id"]) or {}).get("result"), (now_.get(t["id"]) or {}).get("result")
        if a not in ("pass", "fail"):
            rows[t["id"]] = "new" if b else ""
        elif b not in ("pass", "fail"):
            rows[t["id"]] = "not_yet"
        else:
            rows[t["id"]] = "same" if a == b else ("better" if b == "pass" else "worse")
    return {"against": prev, "better": [k for k, x in rows.items() if x == "better"],
            "worse": [k for k, x in rows.items() if x == "worse"],
            "same": sum(1 for x in rows.values() if x == "same"), "rows": {k: x for k, x in rows.items() if x}}


def _count(saved: dict) -> dict[str, Any]:
    c = Counter(x.get("result") for x in saved.values())
    total = len(EAR_TESTS)
    return {"total": total, "done": sum(c.get(r, 0) for r in RESULTS), "passed": c.get("pass", 0),
            "failed": c.get("fail", 0), "skipped": c.get("skip", 0)}


def eartest_mark(tenant: str, test_id: str, result: str, note: str = "", version: str | None = None) -> dict[str, Any]:
    if test_id not in {t["id"] for t in EAR_TESTS}:
        raise KeyError(test_id)
    if result not in (*RESULTS, "clear"):
        raise ValueError("result must be pass, fail, skip or clear")
    v = version or _version()
    with _LOCK:
        d = _ear_load(tenant)
        cur = d.setdefault(v, {})
        if result == "clear":
            cur.pop(test_id, None)
        else:
            cur[test_id] = {"result": result, "note": (note or "").strip()[:300], "at": time.time()}
        EAR_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _ear_file(tenant).with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_ear_file(tenant))
    return eartest(tenant, v)


def eartest_summary(tenant: str) -> list[dict[str, Any]]:
    """Per app version: how many scenarios she passed / failed (newest first) - the 'did this release sound better' line."""
    d = _ear_load(tenant)
    rows = [{"version": v, **_count(x)} for v, x in d.items() if isinstance(x, dict)]
    rows.sort(key=lambda r: _vkey(r["version"]), reverse=True)
    return rows[:6]
